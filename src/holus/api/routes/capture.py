"""Capture → suggest → preview → confirm routes for personal share loop."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from holus.agents.marketing.thought_pipeline import (
    CHANNEL_TARGET as THOUGHT_CHANNEL_TARGET,
)
from holus.agents.marketing.thought_pipeline import ThoughtContentPipeline
from holus.api.models import (
    CaptureConfirmRequest,
    CaptureConfirmResponse,
    CaptureConfirmResult,
    CapturePreviewRequest,
    CapturePreviewResponse,
    CaptureRouteSuggestion,
    CaptureSuggestRequest,
    CaptureSuggestResponse,
    ContentPatchRequest,
    ContentPublishRequest,
)
from holus.api.routes import content as content_routes
from holus.capture.suggest import detect_attachment_kind, suggest_routes
from holus.integrations.holus_social_api import HolusSocialAPIClient, personal_delivery_granted

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capture", tags=["capture"])


def _connected_platforms_from_payload(data: Any) -> list[str]:
    """Normalize Holus Social API connection listings into platform labels."""
    platforms: list[str] = []
    if isinstance(data, dict):
        items = (
            data.get("connections")
            or data.get("data")
            or data.get("items")
            or data.get("platforms")
        )
        if items is None and "platform" in data:
            items = [data]
        if isinstance(items, dict):
            items = list(items.values())
    elif isinstance(data, list):
        items = data
    else:
        items = []

    if not isinstance(items, list):
        return []

    for item in items:
        if isinstance(item, str):
            platforms.append(item.lower())
            continue
        if not isinstance(item, dict):
            continue
        platform = item.get("platform") or item.get("name") or item.get("id")
        status = str(item.get("status") or item.get("state") or "connected").lower()
        if platform and status in {"connected", "active", "ok", "healthy", "ready", ""}:
            platforms.append(str(platform).lower())
    # de-dupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for platform in platforms:
        normalized = "twitter" if platform in {"twitter_x", "x"} else platform
        if normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


async def _probe_social_connections() -> tuple[bool | None, list[str]]:
    """Best-effort Social API probe; never fails the suggest path."""
    client = HolusSocialAPIClient()
    try:
        await client.health()
        try:
            connections = await client.list_connections()
            return True, _connected_platforms_from_payload(connections)
        except Exception:
            logger.info("Social API health ok but connections listing unavailable")
            return True, []
    except Exception as exc:
        logger.info("Social API probe failed: %s", exc)
        return False, []
    finally:
        await client.close()


@router.post("/suggest", response_model=CaptureSuggestResponse)
async def capture_suggest(body: CaptureSuggestRequest) -> CaptureSuggestResponse:
    """Inspect a capture and suggest platforms, formats, and light edits."""
    kind = detect_attachment_kind(
        attachment_url=body.attachment_url,
        filename=body.attachment_filename,
        content_type=body.attachment_content_type,
    )
    has_attachment_metadata = any(
        value is not None
        for value in (
            body.attachment_url,
            body.attachment_filename,
            body.attachment_content_type,
        )
    )
    if has_attachment_metadata and kind == "none":
        raise HTTPException(status_code=400, detail="Unsupported attachment")
    if not body.text.strip() and kind == "none":
        raise HTTPException(status_code=400, detail="Provide text and/or an attachment")

    reachable, discovered = await _probe_social_connections()
    connected = body.connected_platforms or discovered or None
    suggestions = suggest_routes(
        text=body.text,
        attachment_kind=kind,
        attachment_url=body.attachment_url,
        connected_platforms=connected,
    )
    return CaptureSuggestResponse(
        attachment_kind=kind,
        suggestions=[
            CaptureRouteSuggestion(
                platform=item.platform,
                channel=item.channel,
                format_hint=item.format_hint,
                edit_notes=item.edit_notes,
                confidence=item.confidence,
                preview_text=item.preview_text,
                selected=True,
            )
            for item in suggestions
        ],
        personal_delivery_granted=personal_delivery_granted(),
        social_api_reachable=reachable,
        connected_platforms=list(connected or []),
    )


@router.post("/preview", response_model=CapturePreviewResponse)
async def capture_preview(body: CapturePreviewRequest) -> CapturePreviewResponse:
    """Generate reviewable drafts for the selected channels (no publish)."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    if not body.channels:
        raise HTTPException(status_code=400, detail="Select at least one channel")

    unsupported = [channel for channel in body.channels if channel not in THOUGHT_CHANNEL_TARGET]
    if unsupported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported channel(s): {', '.join(unsupported)}",
        )

    source_type = "url" if body.source_url else "text"
    pipeline = ThoughtContentPipeline(queue_dir=content_routes.CONTENT_QUEUE_DIR)
    try:
        content_set = await pipeline.create_content_set(
            thought=body.text,
            channels=list(body.channels),
            source_type=source_type,
            source_url=body.source_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Thought source fetch failed: {exc}") from exc

    items = [
        content_routes._raw_to_item(record, record["piece_id"]) for record in content_set.records
    ]
    previews = [
        content_routes._raw_to_detail(record, record["piece_id"]) for record in content_set.records
    ]
    return CapturePreviewResponse(
        group_id=content_set.group_id,
        items=items,
        previews=previews,
    )


@router.post("/confirm", response_model=CaptureConfirmResponse)
async def capture_confirm(body: CaptureConfirmRequest) -> CaptureConfirmResponse:
    """Approve selected pieces and publish (or record contained intent)."""
    if not body.piece_ids:
        raise HTTPException(status_code=400, detail="piece_ids required")

    results: list[CaptureConfirmResult] = []
    for piece_id in body.piece_ids:
        try:
            approved = await content_routes.update_content_status(
                piece_id,
                ContentPatchRequest(status="approved"),
            )
        except HTTPException as exc:
            results.append(
                CaptureConfirmResult(
                    piece_id=piece_id,
                    status="error",
                    detail=str(exc.detail),
                )
            )
            continue

        revision = approved.revision
        try:
            published = await content_routes.publish_content(
                piece_id,
                ContentPublishRequest(
                    dry_run=body.dry_run,
                    expected_revision=revision,
                ),
            )
            results.append(
                CaptureConfirmResult(
                    piece_id=piece_id,
                    status=published.status,
                    publish_id=published.publish_id,
                )
            )
        except HTTPException as exc:
            results.append(
                CaptureConfirmResult(
                    piece_id=piece_id,
                    status="error",
                    detail=str(exc.detail),
                )
            )

    return CaptureConfirmResponse(
        results=results,
        personal_delivery_granted=personal_delivery_granted(),
    )
