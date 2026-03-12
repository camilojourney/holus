"""Content pipeline routes — GET /api/v1/content."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Query

from holus.api.models import (
    CalendarDay,
    ContentCalendarResponse,
    ContentItem,
    ContentResponse,
    ContentStatusCounts,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
CONTENT_QUEUE_DIR = REPO_ROOT / "data" / "content-queue"


def _load_content_items() -> list[ContentItem]:
    """Read all YAML files in data/content-queue/ and return ContentItems."""
    if not CONTENT_QUEUE_DIR.exists():
        return []

    items: list[ContentItem] = []
    for yaml_file in sorted(CONTENT_QUEUE_DIR.glob("*.yaml")):
        try:
            data: Any = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue

            # Handle list-of-items format
            raw_items = data.get("items", [data])
            if not isinstance(raw_items, list):
                raw_items = [data]

            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                item = _parse_content_item(raw, yaml_file.stem)
                if item:
                    items.append(item)
        except Exception as exc:
            logger.warning("Failed to parse content file %s: %s", yaml_file.name, exc)

    return items


def _parse_content_item(raw: dict[str, Any], default_id: str) -> ContentItem | None:
    """Parse a raw dict into a ContentItem."""
    try:
        created_at = None
        raw_created = raw.get("created_at")
        if raw_created and isinstance(raw_created, str):
            created_at = datetime.fromisoformat(raw_created.replace("Z", "+00:00"))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)

        scheduled_for = None
        raw_scheduled = raw.get("scheduled_for") or raw.get("scheduled_at")
        if raw_scheduled and isinstance(raw_scheduled, str):
            scheduled_for = datetime.fromisoformat(raw_scheduled.replace("Z", "+00:00"))
            if scheduled_for.tzinfo is None:
                scheduled_for = scheduled_for.replace(tzinfo=UTC)

        return ContentItem(
            id=str(raw.get("id", default_id)),
            title=raw.get("title"),
            content_type=str(raw.get("content_type", "unknown")),
            status=str(raw.get("status", "draft")),
            created_at=created_at,
            scheduled_for=scheduled_for,
            agent_id=raw.get("agent_id"),
        )
    except Exception as exc:
        logger.warning("Failed to parse content item: %s", exc)
        return None


@router.get("", response_model=ContentResponse)
async def list_content() -> ContentResponse:
    """Return all content items with status counts."""
    items = _load_content_items()

    counts = ContentStatusCounts()
    for item in items:
        status = item.status.lower()
        if status == "draft":
            counts.draft += 1
        elif status == "review":
            counts.review += 1
        elif status == "published":
            counts.published += 1
        elif status == "rejected":
            counts.rejected += 1

    return ContentResponse(items=items, counts=counts)


@router.get("/calendar", response_model=ContentCalendarResponse)
async def get_content_calendar(
    days: int = Query(default=14, ge=1, le=90),
) -> ContentCalendarResponse:
    """Return content items grouped by scheduled date."""
    items = _load_content_items()
    now = datetime.now(UTC)

    # Build date range
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
