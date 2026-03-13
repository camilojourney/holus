"""Results / Growth routes — GET /api/v1/results."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from holus.api.models import GrowthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
GROWTH_FILE = REPO_ROOT / "data" / "results" / "growth.json"


def _load_growth() -> dict | None:
    """Read the growth snapshot from data/results/growth.json."""
    if not GROWTH_FILE.exists():
        return None
    try:
        return json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read growth data: %s", exc)
        return None


@router.get("", response_model=GrowthResponse)
async def get_results() -> GrowthResponse | dict:
    """Return growth metrics, platform stats, top posts, and trends."""
    data = _load_growth()
    if data is None:
        return GrowthResponse(
            snapshot_date="",
            platforms={},
            daily_growth=[],
            top_posts=[],
            content_by_pillar={},
            content_by_product={},
        )
    return GrowthResponse(**data)
