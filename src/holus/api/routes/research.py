"""Research Radar API routes."""

from __future__ import annotations

from datetime import date  # noqa: TC003 - FastAPI needs this for runtime parameter parsing.
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from holus.core.config import HolusConfig
from holus.research.candidates import CandidateStore, candidate_to_api_dict
from holus.research.models import RadarRunReport
from holus.research.radar import ResearchRadarConfig, load_config, run_radar

router = APIRouter(prefix="/research", tags=["research"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
RESEARCH_DIR: Path | None = None
CANDIDATES_DIR: Path | None = None
CONTENT_QUEUE_DIR = REPO_ROOT / "data" / "content-queue"
DIGEST_DATE_QUERY = Query(default=None, alias="date")
AS_JSON_QUERY = Query(default=True)


@router.post("/run", response_model=RadarRunReport)
async def run_research_radar() -> RadarRunReport:
    """Run the Research Radar on demand."""
    return await run_radar(repo_root=REPO_ROOT)


@router.get("/digest")
async def get_research_digest(
    digest_date: date | None = DIGEST_DATE_QUERY,
    as_json: bool = AS_JSON_QUERY,
) -> Any:
    """Return a JSON envelope, or raw Markdown when ``as_json`` is false."""
    path = _digest_path(digest_date)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Research digest not found")
    markdown = path.read_text(encoding="utf-8")
    if not as_json:
        return PlainTextResponse(markdown, media_type="text/markdown")
    return {"date": path.stem.removeprefix("digest-"), "path": str(path), "markdown": markdown}


@router.get("/candidates")
async def list_research_candidates(status: str | None = Query(default=None)) -> dict[str, Any]:
    """List research candidates, optionally filtered by status."""
    config = _research_config()
    store = CandidateStore(
        _candidates_dir(config),
        queue_dir=CONTENT_QUEUE_DIR,
        lineage_dir=HolusConfig.load().lineage_dir,
    )
    return {
        "candidates": [candidate_to_api_dict(candidate) for candidate in store.list(status=status)]
    }


@router.post("/candidates/{candidate_id}/approve")
async def approve_research_candidate(candidate_id: str) -> dict[str, Any]:
    """Idempotently approve a candidate and return its updated state."""
    config = _research_config()
    store = CandidateStore(
        _candidates_dir(config),
        queue_dir=CONTENT_QUEUE_DIR,
        lineage_dir=HolusConfig.load().lineage_dir,
    )
    try:
        candidate = await store.approve(candidate_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Candidate approval failed: {exc}") from exc
    return candidate_to_api_dict(candidate)


@router.post("/candidates/{candidate_id}/reject")
async def reject_research_candidate(candidate_id: str) -> dict[str, Any]:
    """Mark a pending candidate as rejected."""
    config = _research_config()
    store = CandidateStore(
        _candidates_dir(config),
        queue_dir=CONTENT_QUEUE_DIR,
        lineage_dir=HolusConfig.load().lineage_dir,
    )
    try:
        candidate = store.reject(candidate_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return candidate_to_api_dict(candidate)


def _digest_path(digest_date: date | None) -> Path | None:
    research_dir = _research_dir(_research_config())
    if digest_date is not None:
        candidates = list(research_dir.glob(f"digest-{digest_date.isoformat()}*.md"))
        return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None
    if not research_dir.exists():
        return None
    candidates = list(research_dir.glob("digest-*.md"))
    return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None


def _research_config() -> ResearchRadarConfig:
    return load_config(REPO_ROOT)


def _research_dir(config: ResearchRadarConfig) -> Path:
    return RESEARCH_DIR if RESEARCH_DIR is not None else config.research_dir


def _candidates_dir(config: ResearchRadarConfig) -> Path:
    return CANDIDATES_DIR if CANDIDATES_DIR is not None else config.candidates_dir
