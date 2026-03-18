"""Content pipeline routes — GET/PATCH /api/v1/content."""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Query

from holus.api.models import (
    AgentTraceStep,
    CalendarDay,
    ContentCalendarResponse,
    ContentDetail,
    ContentItem,
    ContentPatchRequest,
    ContentQuality,
    ContentResponse,
    ContentStatusCounts,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
CONTENT_QUEUE_DIR = REPO_ROOT / "data" / "content-queue"


def _load_raw_files() -> list[tuple[Path, dict]]:
    """Load all YAML and JSON files from data/content-queue/."""
    if not CONTENT_QUEUE_DIR.exists():
        return []

    results: list[tuple[Path, dict]] = []
    for path in sorted(CONTENT_QUEUE_DIR.iterdir()):
        if path.suffix not in (".yaml", ".yml", ".json"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
            if isinstance(data, dict):
                results.append((path, data))
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", path.name, exc)

    return results


def _parse_dt(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


def _parse_quality(raw: dict) -> ContentQuality | None:
    q = raw.get("quality")
    if not q or not isinstance(q, dict):
        return None
    return ContentQuality(
        hook_score=str(q.get("hook_score", "")) or None,
        voice_check=q.get("voice_check"),
        quality_score=q.get("quality_score"),
        violations=q.get("violations", []),
    )


def _parse_agent_trace(raw: dict) -> list[AgentTraceStep]:
    trace = raw.get("agent_trace", [])
    if not isinstance(trace, list):
        return []
    steps = []
    for step in trace:
        if not isinstance(step, dict):
            continue
        steps.append(AgentTraceStep(
            agent_id=step.get("agent_id", "unknown"),
            model=step.get("model"),
            role=step.get("role"),
            at=_parse_dt(step.get("at")),
            quality_score=str(step.get("quality_score", "")) or None,
            verdict=step.get("verdict"),
        ))
    return steps


def _raw_to_item(raw: dict, file_stem: str) -> ContentItem:
    piece_id = str(raw.get("piece_id", raw.get("id", file_stem)))
    title = raw.get("topic") or raw.get("title") or raw.get("headline")
    status = str(raw.get("status", "draft"))
    # Normalize legacy status values
    if status == "review":
        status = "pending_review"

    return ContentItem(
        id=piece_id,
        title=title,
        content_type=str(raw.get("content_type", "text_post")),
        platform=raw.get("platform"),
        content_pillar=raw.get("content_pillar"),
        status=status,
        created_at=_parse_dt(raw.get("generated_at") or raw.get("created_at")),
        scheduled_for=_parse_dt(raw.get("scheduled_at") or raw.get("scheduled_for")),
        agent_id=raw.get("agent_id"),
        idea_source=raw.get("idea_source"),
        quality=_parse_quality(raw),
    )


def _raw_to_detail(raw: dict, file_stem: str) -> ContentDetail:
    item = _raw_to_item(raw, file_stem)
    piece_id = str(raw.get("piece_id", raw.get("id", file_stem)))

    # Build image URLs if rendered images exist
    image_url = None
    image_b_url = None
    if raw.get("rendered_image_path"):
        image_url = f"/api/v1/content/{piece_id}/image"
    if raw.get("rendered_image_b_path"):
        image_b_url = f"/api/v1/content/{piece_id}/image?variant=b"

    return ContentDetail(
        **item.model_dump(),
        text=raw.get("text"),
        hashtags=raw.get("hashtags", []),
        char_count=raw.get("char_count"),
        agent_trace=_parse_agent_trace(raw),
        image_url=image_url,
        image_b_url=image_b_url,
        visual_spec=raw.get("visual_spec"),
        visual_spec_b=raw.get("visual_spec_b"),
        judge_score=raw.get("judge_score"),
        judge_verdict=raw.get("judge_verdict"),
    )


@router.get("", response_model=ContentResponse)
async def list_content() -> ContentResponse:
    """Return all content items with status counts."""
    files = _load_raw_files()
    items: list[ContentItem] = []
    for path, raw in files:
        try:
            # Handle list-of-items YAML format (legacy)
            raw_items = raw.get("items", [raw]) if not raw.get("piece_id") and not raw.get("id") else [raw]
            for r in raw_items:
                if isinstance(r, dict):
                    items.append(_raw_to_item(r, path.stem))
        except Exception as exc:
            logger.warning("Skip %s: %s", path.name, exc)

    counts = ContentStatusCounts()
    for item in items:
        s = item.status.lower()
        if s in ("draft",):
            counts.draft += 1
        elif s in ("pending_review", "review"):
            counts.review += 1
        elif s in ("published", "approved"):
            counts.published += 1
        elif s == "rejected":
            counts.rejected += 1

    return ContentResponse(items=items, counts=counts)


@router.get("/calendar", response_model=ContentCalendarResponse)
async def get_content_calendar(
    days: int = Query(default=14, ge=1, le=90),
) -> ContentCalendarResponse:
    """Return content items grouped by scheduled date."""
    files = _load_raw_files()
    items: list[ContentItem] = []
    for path, raw in files:
        with contextlib.suppress(Exception):
            items.append(_raw_to_item(raw, path.stem))

    now = datetime.now(UTC)
    date_range: dict[str, list[ContentItem]] = {}
    for i in range(days):
        d = (now + timedelta(days=i)).date().isoformat()
        date_range[d] = []

    for item in items:
        if item.scheduled_for is None:
            continue
        d = item.scheduled_for.date().isoformat()
        if d in date_range:
            date_range[d].append(item)

    calendar = [
        CalendarDay(date=d, items=day_items)
        for d, day_items in sorted(date_range.items())
    ]
    return ContentCalendarResponse(calendar=calendar)


@router.get("/{piece_id}", response_model=ContentDetail)
async def get_content_detail(piece_id: str) -> ContentDetail:
    """Return full content piece with text, agent trace, and quality breakdown."""
    files = _load_raw_files()
    for path, raw in files:
        raw_id = str(raw.get("piece_id", raw.get("id", path.stem)))
        if raw_id == piece_id or path.stem == piece_id:
            return _raw_to_detail(raw, path.stem)
    raise HTTPException(status_code=404, detail=f"Content piece {piece_id!r} not found")


@router.get("/{piece_id}/image")
async def get_content_image(piece_id: str, variant: str = "a") -> Any:
    """Serve the rendered companion visual for a content piece."""
    from fastapi.responses import FileResponse

    files = _load_raw_files()
    for path, raw in files:
        raw_id = str(raw.get("piece_id", raw.get("id", path.stem)))
        if raw_id == piece_id or path.stem == piece_id:
            key = "rendered_image_b_path" if variant == "b" else "rendered_image_path"
            image_path_str = raw.get(key)
            if not image_path_str:
                raise HTTPException(status_code=404, detail="No visual for this piece")
            image_path = Path(image_path_str)
            if not image_path.exists():
                raise HTTPException(status_code=404, detail="Image file not found on disk")
            return FileResponse(image_path, media_type="image/png")
    raise HTTPException(status_code=404, detail=f"Content piece {piece_id!r} not found")


@router.patch("/{piece_id}/visual-choice")
async def choose_visual_variant(piece_id: str, variant: str = "a") -> ContentDetail:
    """Select which A/B visual variant to use. Copies chosen variant to rendered_image_path."""
    files = _load_raw_files()
    for path, raw in files:
        raw_id = str(raw.get("piece_id", raw.get("id", path.stem)))
        if raw_id != piece_id and path.stem != piece_id:
            continue

        if variant == "b" and raw.get("rendered_image_b_path"):
            # Swap: B becomes primary
            raw["rendered_image_path"] = raw["rendered_image_b_path"]
            raw["visual_spec"] = raw.get("visual_spec_b", raw.get("visual_spec"))
            raw["visual_chosen"] = "b"
        else:
            raw["visual_chosen"] = "a"

        if path.suffix == ".json":
            path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        else:
            path.write_text(yaml.dump(raw, default_flow_style=False), encoding="utf-8")

        return _raw_to_detail(raw, path.stem)

    raise HTTPException(status_code=404, detail=f"Content piece {piece_id!r} not found")


@router.patch("/{piece_id}", response_model=ContentDetail)
async def update_content_status(piece_id: str, body: ContentPatchRequest) -> ContentDetail:
    """Approve, reject, or reschedule a content piece.

    Updates the YAML/JSON file directly. If status is 'approved' and the
    social-media API is reachable, triggers posting via the silo.
    """
    files = _load_raw_files()
    target_path: Path | None = None
    raw: dict = {}

    for path, data in files:
        raw_id = str(data.get("piece_id", data.get("id", path.stem)))
        if raw_id == piece_id or path.stem == piece_id:
            target_path = path
            raw = dict(data)
            break

    if target_path is None:
        raise HTTPException(status_code=404, detail=f"Content piece {piece_id!r} not found")

    # Apply updates
    if body.status is not None:
        raw["status"] = body.status
    if body.scheduled_at is not None:
        raw["scheduled_at"] = body.scheduled_at

    # Write back
    try:
        if target_path.suffix == ".json":
            target_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        else:
            target_path.write_text(yaml.dump(raw, default_flow_style=False), encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {exc}") from exc

    # If approved, attempt to post via social-media-automatization
    if body.status == "approved":
        _attempt_post(raw)

    return _raw_to_detail(raw, target_path.stem)


def _attempt_post(raw: dict) -> None:
    """Fire-and-forget: try to post via social-media-automatization API."""
    try:
        import os

        import requests

        api_base = os.environ.get("SOCIAL_MEDIA_API_BASE_URL", "http://localhost:8000")
        api_key = os.environ.get("POSTING_API_KEY", "")
        text = raw.get("text", "")
        platform = raw.get("platform", "linkedin")
        if not text or not api_key:
            logger.info("Post skipped: missing text or POSTING_API_KEY not set")
            return

        resp = requests.post(
            f"{api_base}/api/v1/publish",
            json={"content": text, "targets": [platform]},
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.ok:
            logger.info("Posted piece %s to %s", raw.get("piece_id", "?"), platform)
        else:
            logger.warning("Post attempt returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Post attempt failed (non-fatal): %s", exc)
