"""Telegram approval gate — SPEC-035.

Handles post approval via Telegram inline button callbacks.
Callback data contains ONLY post_id + variant — never post content.

Routes:
  POST /api/telegram/approve  — approve a variant
  POST /api/telegram/reject   — reject all variants
  POST /api/telegram/regen    — request regeneration
  POST /api/telegram/edit     — approve with edited text
  GET  /api/telegram/pending  — list pending approvals
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["telegram-gate"])

# Pending approvals stored in data/pending-approvals.json
_PENDING_PATH = Path(__file__).parents[4] / "data" / "pending-approvals.json"


# -- Models ----------------------------------------------------------------


class ApproveRequest(BaseModel):
    post_id: str
    variant: Literal["A", "B", "C"]


class RejectRequest(BaseModel):
    post_id: str
    reason: str | None = None


class RegenRequest(BaseModel):
    post_id: str


class EditRequest(BaseModel):
    post_id: str
    variant: Literal["A", "B", "C"]
    edited_text: str


class ApprovalStatus(BaseModel):
    post_id: str
    status: Literal["pending", "approved", "rejected", "regenerating"]
    chosen_variant: str | None = None
    edited_text: str | None = None


# -- State helpers ---------------------------------------------------------


def _load_pending() -> dict[str, Any]:
    if _PENDING_PATH.exists():
        try:
            result: dict[str, Any] = json.loads(_PENDING_PATH.read_text())
            return result
        except Exception:
            pass
    return {}


def _save_pending(data: dict[str, Any]) -> None:
    _PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PENDING_PATH.write_text(json.dumps(data, indent=2))


# -- Routes ----------------------------------------------------------------


@router.post("/approve", response_model=ApprovalStatus)
async def approve_variant(req: ApproveRequest) -> ApprovalStatus:
    """Approve a specific variant for publishing.

    Callback data contains only post_id + variant — never post content.
    """
    pending = _load_pending()
    if req.post_id not in pending:
        raise HTTPException(
            status_code=404, detail=f"Post {req.post_id} not found in pending queue"
        )

    pending[req.post_id]["status"] = "approved"
    pending[req.post_id]["chosen_variant"] = req.variant
    _save_pending(pending)

    logger.info("telegram_gate: approved post=%s variant=%s", req.post_id, req.variant)

    # TODO: trigger publisher → social-media-mcp.schedule_post(post_id, variant)
    # This will be wired when social-media MCP connection is confirmed

    return ApprovalStatus(
        post_id=req.post_id,
        status="approved",
        chosen_variant=req.variant,
    )


@router.post("/reject", response_model=ApprovalStatus)
async def reject_post(req: RejectRequest) -> ApprovalStatus:
    """Reject all variants — send back for rewrite."""
    pending = _load_pending()
    if req.post_id not in pending:
        raise HTTPException(status_code=404, detail=f"Post {req.post_id} not found")

    pending[req.post_id]["status"] = "rejected"
    pending[req.post_id]["rejection_reason"] = req.reason
    _save_pending(pending)

    logger.info("telegram_gate: rejected post=%s reason=%s", req.post_id, req.reason)

    return ApprovalStatus(post_id=req.post_id, status="rejected")


@router.post("/regen", response_model=ApprovalStatus)
async def regenerate_post(req: RegenRequest) -> ApprovalStatus:
    """Request new visual variants with same text."""
    pending = _load_pending()
    if req.post_id not in pending:
        raise HTTPException(status_code=404, detail=f"Post {req.post_id} not found")

    pending[req.post_id]["status"] = "regenerating"
    _save_pending(pending)

    logger.info("telegram_gate: regen requested post=%s", req.post_id)

    return ApprovalStatus(post_id=req.post_id, status="regenerating")


@router.post("/edit", response_model=ApprovalStatus)
async def edit_and_approve(req: EditRequest) -> ApprovalStatus:
    """Approve with edited text — Juan's edit overrides generated text."""
    pending = _load_pending()
    if req.post_id not in pending:
        raise HTTPException(status_code=404, detail=f"Post {req.post_id} not found")

    pending[req.post_id]["status"] = "approved"
    pending[req.post_id]["chosen_variant"] = req.variant
    pending[req.post_id]["edited_text"] = req.edited_text
    _save_pending(pending)

    logger.info("telegram_gate: edit+approve post=%s variant=%s", req.post_id, req.variant)

    return ApprovalStatus(
        post_id=req.post_id,
        status="approved",
        chosen_variant=req.variant,
        edited_text=req.edited_text,
    )


@router.get("/pending", response_model=list[ApprovalStatus])
async def list_pending() -> list[ApprovalStatus]:
    """List all posts awaiting approval."""
    pending = _load_pending()
    return [
        ApprovalStatus(
            post_id=pid,
            status=data.get("status", "pending"),
            chosen_variant=data.get("chosen_variant"),
            edited_text=data.get("edited_text"),
        )
        for pid, data in pending.items()
        if data.get("status") == "pending"
    ]
