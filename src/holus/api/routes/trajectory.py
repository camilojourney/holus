"""Trajectory routes — GET /api/v1/trajectory, /trajectory/stream (SSE)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from holus.api.models import TrajectoryEntry, TrajectoryPage

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trajectory", tags=["trajectory"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
TRAJECTORY_PATH = REPO_ROOT / ".self-improvement" / "memory" / "trajectory.jsonl"


def _load_trajectory(path: Path | None = None) -> list[dict[str, Any]]:
    """Load all entries from trajectory.jsonl; skip malformed lines."""
    target = path or TRAJECTORY_PATH
    if not target.exists():
        return []
    entries: list[dict[str, Any]] = []
    for lineno, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Malformed JSONL at line %d: %.200s", lineno, line)
    return entries


def _parse_entry(raw: dict[str, Any]) -> TrajectoryEntry | None:
    """Parse a raw dict into a TrajectoryEntry; return None on failure."""
    try:
        raw_ts = raw.get("timestamp")
        if raw_ts is None:
            return None
        if isinstance(raw_ts, str):
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        else:
            return None

        return TrajectoryEntry(
            timestamp=ts,
            agent_id=raw.get("agent_id", "unknown"),
            content_type=raw.get("content_type"),
            action=raw.get("action", "unknown"),
            outcome=raw.get("outcome"),
            quality_score=raw.get("quality_score"),
            cost_usd=raw.get("cost_usd"),
            tokens_used=raw.get("tokens_used"),
            notes=raw.get("notes"),
        )
    except Exception as exc:
        logger.warning("Failed to parse trajectory entry: %s — %s", raw, exc)
        return None


@router.get("", response_model=TrajectoryPage)
async def get_trajectory(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    agent_id: str | None = Query(default=None),
    content_type: str | None = Query(default=None),
    date_from: date | None = Query(default=None),  # noqa: B008
    date_to: date | None = Query(default=None),  # noqa: B008
) -> TrajectoryPage:
    """Return paginated trajectory entries with optional filters."""
    raw_entries = _load_trajectory()

    entries: list[TrajectoryEntry] = []
    for raw in raw_entries:
        entry = _parse_entry(raw)
        if entry is None:
            continue

        # Apply filters
        if agent_id and entry.agent_id != agent_id:
            continue
        if content_type and entry.content_type != content_type:
            continue
        if date_from and entry.timestamp.date() < date_from:
            continue
        if date_to and entry.timestamp.date() > date_to:
            continue

        entries.append(entry)

    # Sort newest first
    entries.sort(key=lambda e: e.timestamp, reverse=True)

    total = len(entries)
    offset = (page - 1) * page_size
    page_entries = entries[offset : offset + page_size]

    return TrajectoryPage(
        entries=page_entries,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


async def _tail_trajectory() -> AsyncGenerator[dict[str, str], None]:
    """Async generator that tails trajectory.jsonl and yields new lines."""
    last_size = 0
    if TRAJECTORY_PATH.exists():
        last_size = TRAJECTORY_PATH.stat().st_size

    while True:
        await asyncio.sleep(2)
        if not TRAJECTORY_PATH.exists():
            continue
        current_size = TRAJECTORY_PATH.stat().st_size
        if current_size > last_size:
            with TRAJECTORY_PATH.open(encoding="utf-8") as f:
                f.seek(last_size)
                new_lines = f.read()
            last_size = current_size
            for line in new_lines.splitlines():
                line = line.strip()
                if line:
                    yield {"event": "trajectory_entry", "data": line}


@router.get("/stream")
async def stream_trajectory() -> EventSourceResponse:
    """SSE endpoint — tail trajectory.jsonl and emit new entries."""
    return EventSourceResponse(_tail_trajectory())


# Re-export _load_trajectory so other modules can import it
__all__ = ["_load_trajectory", "router"]
