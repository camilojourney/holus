"""Config routes — GET/PUT /api/v1/config.

Exposes externalized configuration for dashboard integration.
Read and update content.yaml, products.yaml, etc. without code deploys.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

CONFIG_DIR = Path("config")


class ConfigResponse(BaseModel):
    """Generic config response."""

    name: str
    data: dict[str, Any]


class ConfigUpdate(BaseModel):
    """Generic config update request."""

    data: dict[str, Any]


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Config '{name}' not found")
    return yaml.safe_load(path.read_text()) or {}


def _save_yaml(name: str, data: dict[str, Any]) -> None:
    path = CONFIG_DIR / f"{name}.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


@router.get("/content", response_model=ConfigResponse)
async def get_content_config() -> ConfigResponse:
    """Get content generation config (languages, approval, translation)."""
    return ConfigResponse(name="content", data=_load_yaml("content"))


@router.put("/content", response_model=ConfigResponse)
async def update_content_config(update: ConfigUpdate) -> ConfigResponse:
    """Update content generation config."""
    _save_yaml("content", update.data)
    logger.info("Content config updated via API")
    return ConfigResponse(name="content", data=update.data)


@router.get("/products", response_model=ConfigResponse)
async def get_products_config() -> ConfigResponse:
    """Get products config (what Holus promotes)."""
    return ConfigResponse(name="products", data=_load_yaml("products"))


@router.get("/platforms")
async def get_platforms() -> list[dict[str, Any]]:
    """Get all platform configs with effective risk tiers."""
    from holus.agents.marketing.platform_config import (
        get_effective_risk_tier,
        get_platform_config,
        list_platforms,
    )

    result = []
    for pid in list_platforms():
        cfg = get_platform_config(pid)
        result.append({
            "id": cfg.platform_id,
            "name": cfg.display_name,
            "char_limit": cfg.char_limit,
            "risk_tier": get_effective_risk_tier(pid),
            "hashtag_limit": cfg.hashtag_limit,
            "supported_formats": cfg.supported_formats,
        })
    return result
