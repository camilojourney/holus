"""End-to-end publish pipeline tests.

Tests the full flow: queue file with judge score → auto-publish gate → routing.
Uses temp queue directories and mocked social media client.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

from holus.agents.marketing.auto_publish import (
    PASS_THRESHOLD,
    process_queue,
)
from holus.api.app import create_app
from holus.integrations.holus_social_api import HolusSocialAPIClient

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def temp_queue(tmp_path: Path):
    """Create a temp content-queue directory and patch QUEUE_DIR to use it."""
    queue_dir = tmp_path / "content-queue"
    queue_dir.mkdir()
    with patch("holus.agents.marketing.auto_publish.QUEUE_DIR", queue_dir):
        yield queue_dir


@pytest.fixture()
def api_client() -> TestClient:
    """Exercise the shipped Observatory HTTP entrypoints in-process."""
    return TestClient(create_app())


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


def _mocked_social_boundary() -> tuple[HolusSocialAPIClient, AsyncMock]:
    """Build the real Social API client around a deterministic HTTP mock."""
    mock_http = AsyncMock()
    mock_http.post = AsyncMock(side_effect=AssertionError("outbound POST attempted"))
    with patch(
        "holus.integrations.holus_social_api.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        social_client = HolusSocialAPIClient(
            base_url="http://social-api.invalid",
            api_key="test-key",
        )
    return social_client, mock_http


# ---------------------------------------------------------------------------
# Shipped publish and schedule safety boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["pending_review", "rejected"])
@pytest.mark.parametrize(
    ("action", "payload"),
    [
        ("publish", {"expected_revision": "premature"}),
        (
            "schedule",
            {
                "scheduled_at": "2026-04-01T12:00:00Z",
                "expected_revision": "premature",
            },
        ),
    ],
)
def test_unapproved_dispatch_never_reaches_social_api_http_boundary(
    api_client: TestClient,
    temp_queue: Path,
    status: str,
    action: str,
    payload: dict[str, object],
) -> None:
    """Pending or rejected content cannot cross the Social API client boundary."""
    path = _write_queue_item(temp_queue, f"guard-{status}-{action}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["status"] = status
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    social_client, mock_http = _mocked_social_boundary()

    with (
        patch("holus.api.routes.content.CONTENT_QUEUE_DIR", temp_queue),
        patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            return_value=social_client,
        ) as social_client_factory,
    ):
        response = api_client.post(
            f"/api/v1/content/{raw['piece_id']}/{action}",
            json=payload,
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "APPROVAL_REQUIRED"
    social_client_factory.assert_not_called()
    mock_http.post.assert_not_awaited()
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["status"] == status
    assert "dispatch_request_id" not in persisted
    assert "post_id" not in persisted
    assert "schedule_id" not in persisted


@pytest.mark.parametrize(
    ("action", "payload", "external_id_field", "local_status_field"),
    [
        ("publish", {}, "publish_id", "publish_status"),
        (
            "schedule",
            {"scheduled_at": "2026-04-01T12:00:00Z"},
            "schedule_id",
            "schedule_status",
        ),
    ],
)
def test_approved_dispatch_is_observably_contained_and_never_reported_successful(
    api_client: TestClient,
    temp_queue: Path,
    action: str,
    payload: dict[str, object],
    external_id_field: str,
    local_status_field: str,
) -> None:
    """A contained attempt stays visible without claiming external delivery."""
    path = _write_queue_item(temp_queue, f"contained-{action}")
    social_client, mock_http = _mocked_social_boundary()

    with (
        patch("holus.api.routes.content.CONTENT_QUEUE_DIR", temp_queue),
        patch(
            "holus.api.routes.content.HolusSocialAPIClient",
            return_value=social_client,
        ) as social_client_factory,
    ):
        approval = api_client.patch(
            f"/api/v1/content/contained-{action}",
            json={"status": "approved"},
        )
        assert approval.status_code == 200
        response = api_client.post(
            f"/api/v1/content/contained-{action}/{action}",
            json={**payload, "expected_revision": approval.json()["revision"]},
        )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "contained"
    assert result[external_id_field] is None
    assert result.get("success") is not True
    social_client_factory.assert_not_called()
    mock_http.post.assert_not_awaited()

    persisted = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert persisted["status"] == "approved"
    assert persisted[local_status_field] == "contained"
    assert persisted["dispatch_request_id"]
    assert "post_id" not in persisted
    assert "published_at" not in persisted
    assert "schedule_id" not in persisted


# ---------------------------------------------------------------------------
# Dry-run routing tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dry_run_high_score_stays_for_review(temp_queue: Path):
    """Score >= 0.8 with PASS verdict still requires human review."""
    _write_queue_item(temp_queue, "high-001", judge_score=0.92, judge_verdict="PASS")

    results = await process_queue(dry_run=True)

    assert len(results) == 1
    assert results[0]["action"] == "would_review"
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
    assert actions["a"] == "would_review"
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
async def test_full_publish_requires_review_and_does_not_call_social_api(temp_queue: Path):
    """A high-scoring item cannot publish without an immutable review decision."""
    path = _write_queue_item(temp_queue, "pub-001", judge_score=0.90, judge_verdict="PASS")

    mock_publish = AsyncMock(return_value="post-12345")

    with (
        patch("holus.agents.marketing.auto_publish._publish_piece", mock_publish),
        patch("holus.agents.marketing.auto_publish._send_telegram_notification"),
    ):
        results = await process_queue(dry_run=False)

    assert len(results) == 1
    assert results[0]["action"] == "needs_review"
    mock_publish.assert_not_awaited()

    # Verify the queue file was updated
    updated = json.loads(path.read_text())
    assert updated["status"] == "pending_review"
    assert "post_id" not in updated
    assert "auto_published" not in updated


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
async def test_threshold_boundary_at_pass_stays_for_review(temp_queue: Path):
    """Score exactly at PASS_THRESHOLD still requires human review."""
    _write_queue_item(temp_queue, "boundary-001", judge_score=PASS_THRESHOLD, judge_verdict="PASS")

    results = await process_queue(dry_run=True)

    assert results[0]["action"] == "would_review"


@pytest.mark.asyncio
async def test_threshold_boundary_below_pass(temp_queue: Path):
    """Score just below PASS_THRESHOLD should go to needs_review."""
    _write_queue_item(
        temp_queue,
        "below-001",
        judge_score=PASS_THRESHOLD - 0.01,
        judge_verdict="PARTIAL",
    )

    results = await process_queue(dry_run=True)

    assert results[0]["action"] == "needs_review"
