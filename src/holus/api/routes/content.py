"""Content pipeline routes — GET/PATCH /api/v1/content."""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from holus.agents.marketing.thought_pipeline import (
    CHANNEL_TARGET as THOUGHT_CHANNEL_TARGET,
)
from holus.agents.marketing.thought_pipeline import (
    DEFAULT_CHANNELS,
    ThoughtContentPipeline,
    build_posting_destination,
)
from holus.api.models import (
    AgentTraceStep,
    CalendarDay,
    ContentCalendarResponse,
    ContentCreateRequest,
    ContentCreateResponse,
    ContentDetail,
    ContentItem,
    ContentPatchRequest,
    ContentPublishRequest,
    ContentPublishResponse,
    ContentQuality,
    ContentResponse,
    ContentScheduleRequest,
    ContentStatusCounts,
    PostingDestination,
)
from holus.core.config import HolusConfig
from holus.core.storage import atomic_write_text
from holus.integrations.holus_social_api import (
    HolusSocialAPIClient,
    PublishRequest,
    ScheduleRequest,
)
from holus.lineage.models import ArtifactType, stable_hash
from holus.lineage.outbox import DispatchOutbox
from holus.lineage.recorder import LineageRecorder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
CONTENT_QUEUE_DIR = REPO_ROOT / "data" / "content-queue"


def _lineage_recorder() -> LineageRecorder:
    """Keep lineage next to the queue owner, including isolated test queues."""
    default_queue = REPO_ROOT / "data" / "content-queue"
    if CONTENT_QUEUE_DIR != default_queue:
        return LineageRecorder(CONTENT_QUEUE_DIR.parent / "lineage")
    configured = HolusConfig.load().lineage_dir
    return LineageRecorder(configured if configured.is_absolute() else REPO_ROOT / configured)


def _dispatch_outbox() -> DispatchOutbox:
    default_queue = REPO_ROOT / "data" / "content-queue"
    if CONTENT_QUEUE_DIR != default_queue:
        lineage_dir = CONTENT_QUEUE_DIR.parent / "lineage"
    else:
        configured = HolusConfig.load().lineage_dir
        lineage_dir = configured if configured.is_absolute() else REPO_ROOT / configured
    return DispatchOutbox(lineage_dir / "outbox")


def _content_revision(raw: dict[str, Any]) -> str:
    """Hash publish-relevant mutable fields to make stale dispatches fail closed."""
    return stable_hash(
        {
            "piece_id": raw.get("piece_id"),
            "text": _effective_content_text(raw),
            "platform": raw.get("platform"),
            "rendered_image_path": raw.get("rendered_image_path"),
            "rendered_pdf_path": raw.get("rendered_pdf_path"),
            "visual_spec": raw.get("visual_spec"),
        }
    )


def _effective_content_text(raw: dict[str, Any]) -> str:
    return str(raw.get("humanized_text") or raw.get("text") or "")


def _require_approved_dispatch(raw: dict[str, Any], expected_revision: str | None) -> str:
    if raw.get("status") not in {"approved", "published", "scheduled"} or not raw.get(
        "review_decision_id"
    ):
        raise HTTPException(status_code=409, detail="APPROVAL_REQUIRED")
    revision = _content_revision(raw)
    if not expected_revision or expected_revision != revision:
        raise HTTPException(status_code=409, detail="REVISION_CONFLICT")
    if not str(raw["review_decision_id"]).endswith(revision[:16]):
        raise HTTPException(status_code=409, detail="REVISION_CONFLICT")
    return revision


def _record_lineage_outcome(raw: dict[str, Any], outcome: ArtifactType, status: str) -> None:
    try:
        _lineage_recorder().record_outcome(raw, outcome=outcome, status=status)
    except Exception:
        logger.exception("lineage_emission_failed", extra={"piece_id": raw.get("piece_id")})


def _media_path(value: Any) -> Path | None:
    """Resolve media only inside Holus-managed rendered roots, never arbitrary files."""
    if not value or not isinstance(value, str):
        return None
    candidate = Path(value)
    path = (candidate if candidate.is_absolute() else REPO_ROOT / candidate).resolve()
    allowed_roots = (
        CONTENT_QUEUE_DIR.parent / "rendered-content",
        CONTENT_QUEUE_DIR.parent / "rendered",
    )
    if path.is_symlink() or not path.is_file():
        return None
    if not any(path.is_relative_to(root.resolve()) for root in allowed_roots):
        logger.warning("Rejected media path outside rendered roots")
        return None
    return path


def _load_raw_files() -> list[tuple[Path, dict[str, Any]]]:
    """Load all YAML and JSON files from data/content-queue/."""
    if not CONTENT_QUEUE_DIR.exists():
        return []

    results: list[tuple[Path, dict[str, Any]]] = []
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


def _parse_quality(raw: dict[str, Any]) -> ContentQuality | None:
    q = raw.get("quality")
    if not q or not isinstance(q, dict):
        return None
    return ContentQuality(
        hook_score=str(q.get("hook_score", "")) or None,
        voice_check=q.get("voice_check"),
        quality_score=q.get("quality_score"),
        violations=q.get("violations", []),
    )


def _parse_posting_destination(raw: dict[str, Any]) -> PostingDestination | None:
    destination = raw.get("posting_destination")
    if isinstance(destination, dict):
        with contextlib.suppress(Exception):
            return PostingDestination(**destination)

    platform = raw.get("platform")
    if not platform:
        return None
    thought = (
        raw.get("source_raw_input")
        or raw.get("idea_source")
        or raw.get("text")
        or raw.get("topic")
        or ""
    )
    return PostingDestination(
        **build_posting_destination(platform=str(platform), thought=str(thought))
    )


def _parse_agent_trace(raw: dict[str, Any]) -> list[AgentTraceStep]:
    trace = raw.get("agent_trace", [])
    if not isinstance(trace, list):
        return []
    steps = []
    for step in trace:
        if not isinstance(step, dict):
            continue
        steps.append(
            AgentTraceStep(
                agent_id=step.get("agent_id", "unknown"),
                model=step.get("model"),
                role=step.get("role"),
                at=_parse_dt(step.get("at")),
                quality_score=str(step.get("quality_score", "")) or None,
                verdict=step.get("verdict"),
            )
        )
    return steps


def _raw_to_item(raw: dict[str, Any], file_stem: str) -> ContentItem:
    piece_id = str(raw.get("piece_id", raw.get("id", file_stem)))
    title = raw.get("topic") or raw.get("title") or raw.get("headline")
    status = str(raw.get("status", "draft"))
    # Normalize legacy status values
    if status == "review":
        status = "pending_review"

    return ContentItem(
        id=piece_id,
        group_id=raw.get("group_id"),
        title=title,
        content_type=str(raw.get("content_type", "text_post")),
        platform=raw.get("platform"),
        content_pillar=raw.get("content_pillar"),
        status=status,
        created_at=_parse_dt(raw.get("generated_at") or raw.get("created_at")),
        scheduled_for=_parse_dt(raw.get("scheduled_at") or raw.get("scheduled_for")),
        agent_id=raw.get("agent_id"),
        idea_source=raw.get("idea_source"),
        source_type=raw.get("source_type"),
        source_url=raw.get("source_url"),
        revision=raw.get("content_revision") or _content_revision(raw),
        review_decision_id=raw.get("review_decision_id"),
        quality=_parse_quality(raw),
        posting_destination=_parse_posting_destination(raw),
    )


def _raw_to_detail(raw: dict[str, Any], file_stem: str) -> ContentDetail:
    item = _raw_to_item(raw, file_stem)
    piece_id = str(raw.get("piece_id", raw.get("id", file_stem)))

    # Build image URLs if rendered images exist
    image_url = None
    image_b_url = None
    pdf_url = None
    if raw.get("rendered_image_path"):
        image_url = f"/api/v1/content/{piece_id}/image"
    if raw.get("rendered_image_b_path"):
        image_b_url = f"/api/v1/content/{piece_id}/image?variant=b"
    if raw.get("rendered_pdf_path") or raw.get("pdf_path"):
        pdf_url = f"/api/v1/content/{piece_id}/pdf"

    return ContentDetail(
        **item.model_dump(),
        text=_effective_content_text(raw),
        hashtags=raw.get("hashtags", []),
        char_count=raw.get("char_count"),
        agent_trace=_parse_agent_trace(raw),
        image_url=image_url,
        image_b_url=image_b_url,
        pdf_url=pdf_url,
        visual_spec=raw.get("visual_spec"),
        visual_spec_b=raw.get("visual_spec_b"),
        thought_essence=raw.get("thought_essence"),
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
            raw_items = (
                raw.get("items", [raw]) if not raw.get("piece_id") and not raw.get("id") else [raw]
            )
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
        elif s in ("published", "approved", "scheduled"):
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

    calendar = [CalendarDay(date=d, items=day_items) for d, day_items in sorted(date_range.items())]
    return ContentCalendarResponse(calendar=calendar)


@router.post("/from-thought", response_model=ContentCreateResponse)
async def create_content_from_thought(body: ContentCreateRequest) -> ContentCreateResponse:
    """Create pending-review platform drafts from one source thought."""
    requested = body.platforms or list(DEFAULT_CHANNELS)
    unsupported = [channel for channel in requested if channel not in THOUGHT_CHANNEL_TARGET]
    if unsupported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform channel(s): {', '.join(unsupported)}",
        )

    pipeline = ThoughtContentPipeline(queue_dir=CONTENT_QUEUE_DIR)
    try:
        content_set = await pipeline.create_content_set(
            thought=body.thought,
            channels=list(requested),
            source_type=body.source_type,
            source_url=body.source_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Thought source fetch failed: {exc}") from exc

    return ContentCreateResponse(
        group_id=content_set.group_id,
        items=[_raw_to_item(record, record["piece_id"]) for record in content_set.records],
    )


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
    files = _load_raw_files()
    for path, raw in files:
        raw_id = str(raw.get("piece_id", raw.get("id", path.stem)))
        if raw_id == piece_id or path.stem == piece_id:
            key = "rendered_image_b_path" if variant == "b" else "rendered_image_path"
            image_path = _media_path(raw.get(key))
            if image_path is None:
                raise HTTPException(status_code=404, detail="No visual for this piece")
            if not image_path.exists():
                raise HTTPException(status_code=404, detail="Image file not found on disk")
            return FileResponse(image_path, media_type="image/png")
    raise HTTPException(status_code=404, detail=f"Content piece {piece_id!r} not found")


@router.get("/{piece_id}/pdf")
async def get_content_pdf(piece_id: str) -> Any:
    """Serve the rendered carousel PDF for a content piece."""
    files = _load_raw_files()
    for path, raw in files:
        raw_id = str(raw.get("piece_id", raw.get("id", path.stem)))
        if raw_id == piece_id or path.stem == piece_id:
            pdf_path = _media_path(raw.get("rendered_pdf_path") or raw.get("pdf_path"))
            if pdf_path is None:
                raise HTTPException(status_code=404, detail="No carousel PDF for this piece")
            if not pdf_path.exists():
                raise HTTPException(status_code=404, detail="PDF file not found on disk")
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"{piece_id}.pdf",
                content_disposition_type="inline",
            )
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
            atomic_write_text(path, json.dumps(raw, indent=2))
        else:
            atomic_write_text(path, yaml.dump(raw, default_flow_style=False))

        return _raw_to_detail(raw, path.stem)

    raise HTTPException(status_code=404, detail=f"Content piece {piece_id!r} not found")


@router.patch("/{piece_id}", response_model=ContentDetail)
async def update_content_status(piece_id: str, body: ContentPatchRequest) -> ContentDetail:
    """Approve, reject, or reschedule a content piece.

    Updates the YAML/JSON file directly. Posting and scheduling through Holus
    Social API are explicit endpoints so review actions never publish silently.
    """
    files = _load_raw_files()
    target_path: Path | None = None
    raw: dict[str, Any] = {}

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
        current_status = str(raw.get("status", "pending_review"))
        allowed_transitions = {
            "draft": {"pending_review", "approved", "rejected"},
            "pending_review": {"approved", "rejected"},
            "approved": {"rejected"},
            "rejected": {"pending_review"},
        }
        if body.status != current_status and body.status not in allowed_transitions.get(
            current_status, set()
        ):
            raise HTTPException(status_code=409, detail="INVALID_STATUS_TRANSITION")
        raw["status"] = body.status
    if body.scheduled_at is not None:
        raw["scheduled_at"] = body.scheduled_at
    raw["lineage_updated_at"] = datetime.now(tz=UTC).isoformat()
    raw["content_revision"] = _content_revision(raw)
    if raw.get("status") == "approved":
        raw["review_decision_id"] = f"review-{raw['piece_id']}-{raw['content_revision'][:16]}"

    # Write back
    _write_raw_content(target_path, raw)
    _record_lineage_outcome(raw, ArtifactType.REVIEW_DECISION, str(raw.get("status", "updated")))
    return _raw_to_detail(raw, target_path.stem)


@router.post("/{piece_id}/publish", response_model=ContentPublishResponse)
async def publish_content(
    piece_id: str,
    body: ContentPublishRequest | None = None,
) -> ContentPublishResponse:
    """Explicitly publish one approved piece through Holus Social API."""
    request_body = body or ContentPublishRequest()
    target_path, raw = _find_content_raw(piece_id)
    payload = _publish_payload(raw)

    if request_body.dry_run:
        return ContentPublishResponse(
            piece=_raw_to_detail(raw, target_path.stem),
            dry_run=True,
            payload=payload,
            status="dry_run",
        )

    revision = _require_approved_dispatch(raw, request_body.expected_revision)
    if raw.get("status") != "approved" and _dispatch_outbox().find(
        operation="publish", piece_id=piece_id, revision=revision, payload=payload
    ) is None:
        raise HTTPException(status_code=409, detail="DISPATCH_RECONCILIATION_REQUIRED")
    intent, _created = _dispatch_outbox().reserve(
        operation="publish", piece_id=piece_id, revision=revision, payload=payload
    )
    if raw.get("status") != "approved" and _created:
        raise HTTPException(status_code=409, detail="DISPATCH_RECONCILIATION_REQUIRED")
    raw["dispatch_request_id"] = intent.request_id
    _record_lineage_outcome(raw, ArtifactType.PUBLICATION_REQUEST, "intent_recorded")
    if intent.status == "accepted":
        raw["status"] = "published"
        raw["post_id"] = intent.external_id
        publish_id = intent.external_id
    else:
        async with HolusSocialAPIClient() as client:
            result = await client.publish(
                PublishRequest(**payload, idempotency_key=intent.request_id)
            )
        _dispatch_outbox().mark_result(
            intent,
            status="accepted" if result.succeeded else "failed",
            external_id=result.publish_id,
        )
        raw["status"] = "published" if result.succeeded else raw.get("status", "approved")
        raw["post_id"] = result.publish_id
        publish_id = result.publish_id
        raw["publish_status"] = "accepted" if result.succeeded else "failed"
    if raw["status"] == "published":
        raw["published_at"] = datetime.now(tz=UTC).isoformat()
    else:
        raw.pop("published_at", None)
    _write_raw_content(target_path, raw)
    _record_lineage_outcome(raw, ArtifactType.PUBLISH_OUTCOME, str(raw["status"]))

    return ContentPublishResponse(
        piece=_raw_to_detail(raw, target_path.stem),
        payload=payload,
        publish_id=publish_id,
        status=raw["status"],
    )


@router.post("/{piece_id}/schedule", response_model=ContentPublishResponse)
async def schedule_content(
    piece_id: str,
    body: ContentScheduleRequest,
) -> ContentPublishResponse:
    """Explicitly schedule one piece through Holus Social API."""
    target_path, raw = _find_content_raw(piece_id)
    payload = _schedule_payload(raw, body.scheduled_at)

    if body.dry_run:
        return ContentPublishResponse(
            piece=_raw_to_detail(raw, target_path.stem),
            dry_run=True,
            payload=payload,
            status="dry_run",
        )

    revision = _require_approved_dispatch(raw, body.expected_revision)
    if raw.get("status") != "approved" and _dispatch_outbox().find(
        operation="schedule", piece_id=piece_id, revision=revision, payload=payload
    ) is None:
        raise HTTPException(status_code=409, detail="DISPATCH_RECONCILIATION_REQUIRED")
    intent, _created = _dispatch_outbox().reserve(
        operation="schedule", piece_id=piece_id, revision=revision, payload=payload
    )
    if raw.get("status") != "approved" and _created:
        raise HTTPException(status_code=409, detail="DISPATCH_RECONCILIATION_REQUIRED")
    raw["scheduled_at"] = body.scheduled_at
    raw["dispatch_request_id"] = intent.request_id
    _record_lineage_outcome(raw, ArtifactType.PUBLICATION_REQUEST, "intent_recorded")
    if intent.status == "accepted":
        raw["status"] = "scheduled"
        raw["schedule_id"] = intent.external_id
        raw["schedule_status"] = intent.external_status or "accepted"
        schedule_id = intent.external_id
        schedule_status = raw["schedule_status"]
    else:
        async with HolusSocialAPIClient() as client:
            result = await client.schedule_post(
                ScheduleRequest(**payload, idempotency_key=intent.request_id)
            )
        _dispatch_outbox().mark_result(
            intent,
            status="accepted",
            external_id=result.schedule_id,
            external_status=result.status,
        )
        raw["status"] = "scheduled"
        raw["schedule_id"] = result.schedule_id
        raw["schedule_status"] = result.status
        schedule_id = result.schedule_id
        schedule_status = result.status
    raw["lineage_updated_at"] = datetime.now(tz=UTC).isoformat()
    _write_raw_content(target_path, raw)
    _record_lineage_outcome(raw, ArtifactType.SCHEDULE_OUTCOME, str(raw["schedule_status"]))

    return ContentPublishResponse(
        piece=_raw_to_detail(raw, target_path.stem),
        payload=payload,
        schedule_id=schedule_id,
        status=schedule_status,
    )


def _find_content_raw(piece_id: str) -> tuple[Path, dict[str, Any]]:
    files = _load_raw_files()
    for path, data in files:
        raw_id = str(data.get("piece_id", data.get("id", path.stem)))
        if raw_id == piece_id or path.stem == piece_id:
            return path, dict(data)
    raise HTTPException(status_code=404, detail=f"Content piece {piece_id!r} not found")


def _write_raw_content(path: Path, raw: dict[str, Any]) -> None:
    try:
        if path.suffix == ".json":
            atomic_write_text(path, json.dumps(raw, indent=2))
        else:
            atomic_write_text(path, yaml.dump(raw, default_flow_style=False))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {exc}") from exc


def _media_payload(raw: dict[str, Any]) -> dict[str, str]:
    if raw.get("rendered_pdf_path"):
        path = _media_path(raw["rendered_pdf_path"])
        if path is None:
            raise HTTPException(status_code=400, detail="INVALID_RENDERED_MEDIA_PATH")
        return {"media_url": str(path), "media_type": "document"}
    if raw.get("rendered_image_path"):
        path = _media_path(raw["rendered_image_path"])
        if path is None:
            raise HTTPException(status_code=400, detail="INVALID_RENDERED_MEDIA_PATH")
        return {"media_url": str(path), "media_type": "image"}
    return {}


def _publish_payload(raw: dict[str, Any]) -> dict[str, Any]:
    text = _effective_content_text(raw)
    platform = str(raw.get("platform", "linkedin"))
    if not text:
        raise HTTPException(status_code=400, detail="Content piece has no text to publish")
    return {
        "content": text,
        "platforms": [platform],
        "style": "raw",
        **_media_payload(raw),
    }


def _schedule_payload(raw: dict[str, Any], scheduled_at: str) -> dict[str, Any]:
    text = _effective_content_text(raw)
    platform = str(raw.get("platform", "linkedin"))
    if not text:
        raise HTTPException(status_code=400, detail="Content piece has no text to schedule")
    return {
        "content": text,
        "platforms": [platform],
        "approval_required": True,
        "scheduled_at": scheduled_at,
        **_media_payload(raw),
    }
