"""Universal ingest endpoint — SPEC-035 extension.

POST /api/holus/ingest

Accepts any input type, converts to text, feeds the voice pipeline.
Everything becomes text before entering Holus — audio, video, images,
raw text. Single entry point, no multi-modal complexity inside the agent.

Input types:
  text   — raw idea string (pass-through)
  audio  — file upload → Whisper → transcript
  video  — file upload → Genpeli MCP → transcript
  url    — web page → fetch → extracted text
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/holus", tags=["ingest"])

# Pending approvals dir
_DATA_DIR = Path(__file__).parents[4] / "data"
_PENDING_PATH = _DATA_DIR / "pending-approvals.json"

# Whisper server (invoz)
_WHISPER_URL = "http://localhost:5001/transcribe"
# Invoz API
_INVOZ_URL = "http://127.0.0.1:8001/api/v1/analyze/upload"


# -- Response model --------------------------------------------------------

class IngestResponse(BaseModel):
    post_id: str
    input_type: str
    extracted_text: str
    status: Literal["queued", "error"]
    message: str


# -- Text extraction helpers -----------------------------------------------

async def _extract_from_audio(file: UploadFile) -> str:
    """Audio file → transcript via Invoz/Whisper."""
    audio_bytes = await file.read()
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            _INVOZ_URL,
            files={"audio": (file.filename or "audio.ogg", audio_bytes, file.content_type or "audio/ogg")},
        )
        resp.raise_for_status()
        data = resp.json()
        transcript = data.get("transcript", "")
        if not transcript:
            raise ValueError("Whisper returned empty transcript")
        return transcript


async def _extract_from_video(file: UploadFile) -> str:
    """Video file → transcript via Genpeli MCP (stub — wire when MCP live)."""
    # TODO: wire to genpeli-mcp.transcribe when MCP connection confirmed
    # For now: attempt audio track extraction via ffmpeg + Whisper
    raise NotImplementedError(
        "Video transcription requires Genpeli MCP — not yet connected. "
        "Convert to audio first and use input_type=audio."
    )


async def _extract_from_url(url: str) -> str:
    """URL → readable text via simple fetch + strip."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, follow_redirects=True, headers={"User-Agent": "HolusIngest/1.0"})
        resp.raise_for_status()
        text = resp.text
        # Very basic HTML strip — good enough for raw idea extraction
        import re
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000]  # cap at 4k chars


def _queue_for_pipeline(post_id: str, text: str, input_type: str) -> None:
    """Save to pending-approvals.json with status=pipeline_queued."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    pending: dict[str, Any] = {}
    if _PENDING_PATH.exists():
        try:
            pending = json.loads(_PENDING_PATH.read_text())
        except Exception:
            pass

    pending[post_id] = {
        "post_id": post_id,
        "status": "pipeline_queued",
        "input_type": input_type,
        "raw_text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _PENDING_PATH.write_text(json.dumps(pending, indent=2))


# -- Route -----------------------------------------------------------------

@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    # Text input
    text: Annotated[str | None, Form()] = None,
    # URL input
    url: Annotated[str | None, Form()] = None,
    # File input (audio or video)
    file: Annotated[UploadFile | None, File()] = None,
    # Explicit type override (optional — auto-detected if not provided)
    input_type: Annotated[str | None, Form()] = None,
) -> IngestResponse:
    """Universal ingest — any input type → text → voice pipeline.

    Everything becomes text before entering Holus.

    Examples:
      - text idea:  POST form with text="I built an agent that..."
      - audio note: POST form with file=<audio.ogg>
      - article:    POST form with url="https://..."
      - video clip: POST form with file=<clip.mp4> (requires Genpeli MCP)
    """
    post_id = str(uuid.uuid4())[:8]
    extracted_text = ""
    detected_type = input_type or "unknown"

    try:
        if text:
            # Text pass-through — most common case
            detected_type = "text"
            extracted_text = text.strip()

        elif url:
            detected_type = "url"
            extracted_text = await _extract_from_url(url)

        elif file:
            ct = (file.content_type or "").lower()
            filename = (file.filename or "").lower()

            if "audio" in ct or filename.endswith((".ogg", ".mp3", ".wav", ".m4a", ".flac")):
                detected_type = "audio"
                extracted_text = await _extract_from_audio(file)

            elif "video" in ct or filename.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                detected_type = "video"
                extracted_text = await _extract_from_video(file)

            else:
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported file type: {file.content_type}. Use text, audio, or video.",
                )
        else:
            raise HTTPException(
                status_code=422,
                detail="Provide one of: text (form field), url (form field), or file (upload).",
            )

        if not extracted_text:
            raise HTTPException(status_code=422, detail="Extracted text is empty.")

        # Queue for voice pipeline
        _queue_for_pipeline(post_id, extracted_text, detected_type)

        logger.info("ingest: post_id=%s type=%s chars=%d", post_id, detected_type, len(extracted_text))

        return IngestResponse(
            post_id=post_id,
            input_type=detected_type,
            extracted_text=extracted_text[:500],  # preview only in response
            status="queued",
            message=f"Queued for voice pipeline. post_id={post_id}",
        )

    except HTTPException:
        raise
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ingest error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}") from exc
