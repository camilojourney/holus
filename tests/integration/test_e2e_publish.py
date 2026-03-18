"""End-to-end publish pipeline tests.

Tests the full flow: queue file with judge score → auto-publish gate → routing.
Uses temp queue directories and mocked social media client.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from holus.agents.marketing.auto_publish import (
    PASS_THRESHOLD,
    process_queue,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def temp_queue(tmp_path: Path):
    """Create a temp content-queue directory and patch QUEUE_DIR to use it."""
    queue_dir = tmp_path / "content-queue"
    queue_dir.mkdir()
    with patch("holus.agents.marketing.auto_publish.QUEUE_DIR", queue_dir):
        yield queue_dir


def _write_queue_item(
    queue_dir: Path,
    piece_id: str,
    *,
    judge_score: float | None = None,
    judge_verdict: str | None = None,
    platform: str = "linkedin",
    text: str = "Test content for publishing.",
) -> Path:
    """Helper: write a queue JSON file with given fields."""
    data = {
        "piece_id": piece_id,
        "platform": platform,
        "content_type": "text_post",
        "topic": "Test topic",
        "text": text,
        "status": "pending_review",
        "generated_at": "2026-03-17T15:00:00+00:00",
        "quality": {"hook_score": "8", "voice_check": "PASS"},
    }
    if judge_score is not None:
        data["judge_score"] = judge_score
    if judge_verdict is not None:
        data["judge_verdict"] = judge_verdict

    path = queue_dir / f"linkedin-text_post-{piece_id}.json"
    path.write_text(json.dumps(data, indent=2))
    return path


# ---------------------------------------------------------------------------
# Dry-run routing tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dry_run_high_score_would_publish(temp_queue: Path):
    """Score >= 0.8 with PASS verdict → would_publish."""
    _write_queue_item(temp_queue, "high-001", judge_score=0.92, judge_verdict="PASS")

    results = await process_queue(dry_run=True)

    assert len(results) == 1
    assert results[0]["action"] == "would_publish"
    assert results[0]["score"] == 0.92


@pytest.mark.asyncio
async def test_dry_run_partial_score_needs_review(temp_queue: Path):
    """Score 0.5-0.8 → needs_review."""
    _write_queue_item(temp_queue, "mid-001", judge_score=0.65, judge_verdict="PARTIAL")

    results = await process_queue(dry_run=True)

    assert len(results) == 1
    assert results[0]["action"] == "needs_review"
    assert results[0]["score"] == 0.65


@pytest.mark.asyncio
async def test_dry_run_low_score_would_reject(temp_queue: Path):
    """Score < 0.5 → would_reject."""
    _write_queue_item(temp_queue, "low-001", judge_score=0.30, judge_verdict="FAIL")

    results = await process_queue(dry_run=True)

    assert len(results) == 1
    assert results[0]["action"] == "would_reject"
    assert results[0]["score"] == 0.30


@pytest.mark.asyncio
async def test_dry_run_no_score_skipped(temp_queue: Path):
    """Missing judge_score → skipped."""
    _write_queue_item(temp_queue, "noscore-001")

    results = await process_queue(dry_run=True)

    assert len(results) == 1
    assert results[0]["action"] == "skipped"


@pytest.mark.asyncio
async def test_dry_run_multiple_items_routes_correctly(temp_queue: Path):
    """Multiple items with different scores route to correct actions."""
    _write_queue_item(temp_queue, "a", judge_score=0.95, judge_verdict="PASS")
    _write_queue_item(temp_queue, "b", judge_score=0.60, judge_verdict="PARTIAL")
    _write_queue_item(temp_queue, "c", judge_score=0.25, judge_verdict="FAIL")
    _write_queue_item(temp_queue, "d")  # no score

    results = await process_queue(dry_run=True)

    actions = {r["piece_id"]: r["action"] for r in results}
    assert actions["a"] == "would_publish"
    assert actions["b"] == "needs_review"
    assert actions["c"] == "would_reject"
    assert actions["d"] == "skipped"


@pytest.mark.asyncio
async def test_dry_run_pass_score_but_fail_verdict_not_published(temp_queue: Path):
    """High score but FAIL verdict (safety flag) → should NOT auto-publish."""
    _write_queue_item(temp_queue, "flagged-001", judge_score=0.85, judge_verdict="FAIL")

    results = await process_queue(dry_run=True)

    # FAIL verdict blocks auto-publish even with high score
    assert len(results) == 1
    assert results[0]["action"] != "would_publish"


# ---------------------------------------------------------------------------
# Full publish with mock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_publish_updates_queue_file(temp_queue: Path):
    """Actual publish (non-dry-run) updates the queue file status."""
    path = _write_queue_item(temp_queue, "pub-001", judge_score=0.90, judge_verdict="PASS")

    mock_publish = AsyncMock(return_value="post-12345")

    with (
        patch("holus.agents.marketing.auto_publish._publish_piece", mock_publish),
        patch("holus.agents.marketing.auto_publish._send_telegram_notification"),
    ):
        results = await process_queue(dry_run=False)

    assert len(results) == 1
    assert results[0]["action"] == "published"
    assert results[0]["publish_id"] == "post-12345"

    # Verify the queue file was updated
    updated = json.loads(path.read_text())
    assert updated["status"] == "published"
    assert updated["post_id"] == "post-12345"
    assert updated["auto_published"] is True
    assert "published_at" in updated


@pytest.mark.asyncio
async def test_full_reject_updates_queue_file(temp_queue: Path):
    """Auto-reject updates the queue file with rejection info."""
    path = _write_queue_item(temp_queue, "rej-001", judge_score=0.20, judge_verdict="FAIL")

    with (
        patch("holus.agents.marketing.auto_publish._send_telegram_notification"),
        patch("holus.agents.marketing.auto_publish._trigger_reflexion"),
    ):
        results = await process_queue(dry_run=False)

    assert len(results) == 1
    assert results[0]["action"] == "rejected"

    updated = json.loads(path.read_text())
    assert updated["status"] == "rejected"
    assert updated["auto_rejected"] is True
    assert "rejected_at" in updated


@pytest.mark.asyncio
async def test_empty_queue_returns_empty(temp_queue: Path):
    """Empty queue directory returns no results."""
    results = await process_queue(dry_run=True)
    assert results == []


@pytest.mark.asyncio
async def test_threshold_boundary_at_pass(temp_queue: Path):
    """Score exactly at PASS_THRESHOLD should auto-publish."""
    _write_queue_item(temp_queue, "boundary-001", judge_score=PASS_THRESHOLD, judge_verdict="PASS")

    results = await process_queue(dry_run=True)

    assert results[0]["action"] == "would_publish"


@pytest.mark.asyncio
async def test_threshold_boundary_below_pass(temp_queue: Path):
    """Score just below PASS_THRESHOLD should go to needs_review."""
    _write_queue_item(
        temp_queue, "below-001",
        judge_score=PASS_THRESHOLD - 0.01,
        judge_verdict="PARTIAL",
    )

    results = await process_queue(dry_run=True)

    assert results[0]["action"] == "needs_review"
