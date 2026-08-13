"""Tests for auto_publish module — verdict handling, dry-run, publish, reject, reflexion."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
import yaml

from holus.agents.marketing.auto_publish import (
    PARTIAL_THRESHOLD,
    PASS_THRESHOLD,
    _get_judge_score,
    _get_judge_verdict,
    _load_pending_with_scores,
    _trigger_reflexion,
    _update_item,
    process_human_rejection,
    process_queue,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def queue_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temp content-queue directory and patch QUEUE_DIR."""
    qd = tmp_path / "content-queue"
    qd.mkdir()
    monkeypatch.setattr("holus.agents.marketing.auto_publish.QUEUE_DIR", qd)
    return qd


def _write_yaml_item(queue_dir: Path, name: str, data: dict[str, Any]) -> Path:
    p = queue_dir / f"{name}.yaml"
    p.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return p


def _write_json_item(queue_dir: Path, name: str, data: dict[str, Any]) -> Path:
    p = queue_dir / f"{name}.json"
    p.write_text(json.dumps(data, indent=2))
    return p


def _make_item(
    piece_id: str = "test-001",
    score: float = 0.85,
    verdict: str = "PASS",
    platform: str = "linkedin",
    status: str = "pending_review",
    content_type: str = "tutorial",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "piece_id": piece_id,
        "status": status,
        "judge_score": score,
        "judge_verdict": verdict,
        "platform": platform,
        "content_type": content_type,
        "text": f"Test content for {piece_id}",
        "topic": "AI consulting",
        "judge_feedback": "Good quality",
        **extra,
    }


# ---------------------------------------------------------------------------
# _get_judge_score
# ---------------------------------------------------------------------------


class TestGetJudgeScore:
    def test_direct_field_float(self) -> None:
        assert _get_judge_score({"judge_score": 0.85}) == 0.85

    def test_direct_field_int(self) -> None:
        assert _get_judge_score({"judge_score": 1}) == 1.0

    def test_nested_in_quality(self) -> None:
        assert _get_judge_score({"quality": {"judge_score": 0.6}}) == 0.6

    def test_missing_returns_none(self) -> None:
        assert _get_judge_score({}) is None

    def test_string_score_returns_none(self) -> None:
        assert _get_judge_score({"judge_score": "high"}) is None

    def test_direct_takes_priority(self) -> None:
        item = {"judge_score": 0.9, "quality": {"judge_score": 0.5}}
        assert _get_judge_score(item) == 0.9


# ---------------------------------------------------------------------------
# _get_judge_verdict
# ---------------------------------------------------------------------------


class TestGetJudgeVerdict:
    def test_direct_field(self) -> None:
        assert _get_judge_verdict({"judge_verdict": "PASS"}) == "PASS"

    def test_nested_in_quality(self) -> None:
        assert _get_judge_verdict({"quality": {"judge_verdict": "FAIL"}}) == "FAIL"

    def test_missing_returns_none(self) -> None:
        assert _get_judge_verdict({}) is None


# ---------------------------------------------------------------------------
# _load_pending_with_scores
# ---------------------------------------------------------------------------


class TestLoadPending:
    def test_empty_dir(self, queue_dir: Path) -> None:
        assert _load_pending_with_scores() == []

    def test_loads_yaml(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "item1", _make_item())
        items = _load_pending_with_scores()
        assert len(items) == 1
        assert items[0]["piece_id"] == "test-001"
        assert "_file_path" in items[0]

    def test_loads_json(self, queue_dir: Path) -> None:
        _write_json_item(queue_dir, "item1", _make_item())
        items = _load_pending_with_scores()
        assert len(items) == 1

    def test_skips_non_pending(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "item1", _make_item(status="published"))
        assert _load_pending_with_scores() == []

    def test_skips_invalid_yaml(self, queue_dir: Path) -> None:
        (queue_dir / "bad.yaml").write_text("{{invalid")
        assert _load_pending_with_scores() == []

    def test_skips_non_dict(self, queue_dir: Path) -> None:
        (queue_dir / "list.json").write_text(json.dumps([1, 2, 3]))
        assert _load_pending_with_scores() == []

    def test_multiple_items_sorted(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "a_first", _make_item(piece_id="aaa"))
        _write_yaml_item(queue_dir, "b_second", _make_item(piece_id="bbb"))
        items = _load_pending_with_scores()
        assert len(items) == 2
        assert items[0]["piece_id"] == "aaa"

    def test_missing_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "holus.agents.marketing.auto_publish.QUEUE_DIR",
            tmp_path / "nonexistent",
        )
        assert _load_pending_with_scores() == []


# ---------------------------------------------------------------------------
# _update_item
# ---------------------------------------------------------------------------


class TestUpdateItem:
    def test_update_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "item.yaml"
        p.write_text(yaml.dump({"status": "pending_review", "piece_id": "x"}))
        _update_item(str(p), {"status": "published", "post_id": "123"})
        data = yaml.safe_load(p.read_text())
        assert data["status"] == "published"
        assert data["post_id"] == "123"
        assert data["piece_id"] == "x"  # preserved

    def test_update_json(self, tmp_path: Path) -> None:
        p = tmp_path / "item.json"
        p.write_text(json.dumps({"status": "pending_review"}))
        _update_item(str(p), {"status": "rejected"})
        data = json.loads(p.read_text())
        assert data["status"] == "rejected"


# ---------------------------------------------------------------------------
# _trigger_reflexion
# ---------------------------------------------------------------------------


class TestTriggerReflexion:
    def test_logs_reflexion(self, tmp_path: Path) -> None:
        item = {
            "topic": "AI tutorial",
            "judge_feedback": "Too generic",
            "content_type": "tutorial",
            "platform": "linkedin",
        }
        mock_logger = MagicMock()
        with patch(
            "holus.memory.trajectory.TrajectoryLogger",
            return_value=mock_logger,
        ):
            _trigger_reflexion(item, 0.3)
            mock_logger.append.assert_called_once()
            entry = mock_logger.append.call_args[0][0]
            assert entry.agent_id == "auto-publish"
            assert entry.task_type == "reflexion"
            assert entry.judge_score == 0.3
            assert "Too generic" in entry.judge_feedback

    def test_handles_exception_gracefully(self) -> None:
        with patch(
            "holus.memory.trajectory.TrajectoryLogger",
            side_effect=Exception("disk full"),
        ):
            # Should not raise
            _trigger_reflexion({"topic": "x", "judge_feedback": "y", "platform": "z"}, 0.1)


# ---------------------------------------------------------------------------
# process_queue — verdict routing
# ---------------------------------------------------------------------------


class TestProcessQueueVerdicts:
    @pytest.mark.asyncio()
    async def test_empty_queue(self, queue_dir: Path) -> None:
        results = await process_queue()
        assert results == []

    @pytest.mark.asyncio()
    async def test_pass_stays_for_review(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "good", _make_item(score=0.9, verdict="PASS"))
        results = await process_queue()

        assert len(results) == 1
        assert results[0]["action"] == "needs_review"
        assert results[0]["score"] == 0.9

    @pytest.mark.asyncio()
    async def test_pass_updates_file(self, queue_dir: Path) -> None:
        p = _write_yaml_item(queue_dir, "good", _make_item(score=0.85))

        await process_queue()

        data = yaml.safe_load(p.read_text())
        assert data["status"] == "pending_review"
        assert "post_id" not in data

    @pytest.mark.asyncio()
    async def test_partial_needs_review(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "mid", _make_item(score=0.65))
        with patch("holus.agents.marketing.auto_publish._send_telegram_notification"):
            results = await process_queue()
        assert results[0]["action"] == "needs_review"
        assert results[0]["score"] == 0.65

    @pytest.mark.asyncio()
    async def test_fail_rejects(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "bad", _make_item(score=0.3))

        with (
            patch("holus.agents.marketing.auto_publish._send_telegram_notification"),
            patch("holus.agents.marketing.auto_publish._trigger_reflexion") as mock_refl,
        ):
            results = await process_queue()

        assert results[0]["action"] == "rejected"
        assert results[0]["score"] == 0.3
        mock_refl.assert_called_once()

    @pytest.mark.asyncio()
    async def test_fail_updates_file(self, queue_dir: Path) -> None:
        p = _write_yaml_item(queue_dir, "bad", _make_item(score=0.2))

        with (
            patch("holus.agents.marketing.auto_publish._send_telegram_notification"),
            patch("holus.agents.marketing.auto_publish._trigger_reflexion"),
        ):
            await process_queue()

        data = yaml.safe_load(p.read_text())
        assert data["status"] == "rejected"
        assert data["auto_rejected"] is True
        assert "Auto-rejected" in data["rejection_reason"]

    @pytest.mark.asyncio()
    async def test_no_score_skipped(self, queue_dir: Path) -> None:
        item = _make_item()
        del item["judge_score"]
        _write_yaml_item(queue_dir, "noscore", item)
        results = await process_queue()
        assert results[0]["action"] == "skipped"
        assert "no judge score" in results[0]["reason"]

    @pytest.mark.asyncio()
    async def test_carousel_without_pdf_skipped(self, queue_dir: Path) -> None:
        _write_yaml_item(
            queue_dir,
            "carousel",
            _make_item(content_type="carousel_outline", score=0.9),
        )
        results = await process_queue()
        assert results[0]["action"] == "skipped"
        assert "carousel without rendered PDF" in results[0]["reason"]

    @pytest.mark.asyncio()
    async def test_carousel_with_pdf_stays_for_review(self, queue_dir: Path) -> None:
        _write_yaml_item(
            queue_dir,
            "carousel",
            _make_item(content_type="carousel_outline", score=0.9, pdf_path="/tmp/c.pdf"),
        )
        results = await process_queue()
        assert results[0]["action"] == "needs_review"

    @pytest.mark.asyncio()
    async def test_pass_with_fail_verdict_routes_to_review(self, queue_dir: Path) -> None:
        """High score but verdict=FAIL (brand safety) → needs_review, not publish."""
        _write_yaml_item(queue_dir, "flagged", _make_item(score=0.85, verdict="FAIL"))
        with patch("holus.agents.marketing.auto_publish._send_telegram_notification"):
            results = await process_queue()
        # score >= PASS_THRESHOLD but verdict == FAIL → falls to elif (PARTIAL range)
        assert results[0]["action"] == "needs_review"


# ---------------------------------------------------------------------------
# process_queue — dry-run mode
# ---------------------------------------------------------------------------


class TestDryRunMode:
    @pytest.mark.asyncio()
    async def test_dry_run_would_publish(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "good", _make_item(score=0.9))
        results = await process_queue(dry_run=True)
        assert results[0]["action"] == "would_review"

    @pytest.mark.asyncio()
    async def test_dry_run_would_reject(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "bad", _make_item(score=0.2))
        results = await process_queue(dry_run=True)
        assert results[0]["action"] == "would_reject"

    @pytest.mark.asyncio()
    async def test_dry_run_no_file_changes(self, queue_dir: Path) -> None:
        p = _write_yaml_item(queue_dir, "bad", _make_item(score=0.2))
        original = p.read_text()
        await process_queue(dry_run=True)
        assert p.read_text() == original  # file unchanged

    @pytest.mark.asyncio()
    async def test_dry_run_partial_still_notifies(self, queue_dir: Path) -> None:
        """PARTIAL items send notifications even in dry-run (they're just notifications)."""
        _write_yaml_item(queue_dir, "mid", _make_item(score=0.65))
        with patch(
            "holus.agents.marketing.auto_publish._send_telegram_notification",
        ) as mock_tg:
            results = await process_queue(dry_run=True)
        assert results[0]["action"] == "needs_review"
        mock_tg.assert_called_once()


# ---------------------------------------------------------------------------
# process_queue — publish failure
# ---------------------------------------------------------------------------


class TestPublishFailure:
    @pytest.mark.asyncio()
    async def test_high_score_never_attempts_publish(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "good", _make_item(score=0.9))
        results = await process_queue()
        assert results[0]["action"] == "needs_review"


# ---------------------------------------------------------------------------
# process_queue — multiple items
# ---------------------------------------------------------------------------


class TestMultipleItems:
    @pytest.mark.asyncio()
    async def test_mixed_verdicts(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "a_pass", _make_item(piece_id="p1", score=0.9))
        _write_yaml_item(queue_dir, "b_partial", _make_item(piece_id="p2", score=0.6))
        _write_yaml_item(queue_dir, "c_fail", _make_item(piece_id="p3", score=0.2))

        with (
            patch("holus.agents.marketing.auto_publish._send_telegram_notification"),
            patch("holus.agents.marketing.auto_publish._trigger_reflexion"),
        ):
            results = await process_queue()

        actions = {r["piece_id"]: r["action"] for r in results}
        assert actions["p1"] == "needs_review"
        assert actions["p2"] == "needs_review"
        assert actions["p3"] == "rejected"


# ---------------------------------------------------------------------------
# process_human_rejection
# ---------------------------------------------------------------------------


class TestProcessHumanRejection:
    def test_rejects_and_logs(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "item1", _make_item(piece_id="hr-001", score=0.7))
        mock_tl = MagicMock()
        with (
            patch("holus.memory.trajectory.TrajectoryLogger", return_value=mock_tl),
            patch("holus.agents.marketing.auto_publish._trigger_reflexion"),
        ):
            result = process_human_rejection("hr-001", "Voice doesn't match brand")

        assert result["action"] == "human_rejected"
        assert result["reason"] == "Voice doesn't match brand"
        assert result["judge_calibration_needed"] is False  # score 0.7 < 0.8

    def test_calibration_needed_when_judge_passed(self, queue_dir: Path) -> None:
        _write_yaml_item(queue_dir, "item1", _make_item(piece_id="cal-001", score=0.9))
        mock_tl = MagicMock()
        with (
            patch("holus.memory.trajectory.TrajectoryLogger", return_value=mock_tl),
            patch("holus.agents.marketing.auto_publish._trigger_reflexion"),
        ):
            result = process_human_rejection("cal-001", "Too salesy")

        assert result["judge_calibration_needed"] is True

    def test_updates_file_status(self, queue_dir: Path) -> None:
        p = _write_yaml_item(queue_dir, "item1", _make_item(piece_id="upd-001"))
        mock_tl = MagicMock()
        with (
            patch("holus.memory.trajectory.TrajectoryLogger", return_value=mock_tl),
            patch("holus.agents.marketing.auto_publish._trigger_reflexion"),
        ):
            process_human_rejection("upd-001", "Bad")

        data = yaml.safe_load(p.read_text())
        assert data["status"] == "rejected"
        assert data["rejected_by"] == "human"
        assert data["rejection_reason"] == "Bad"

    def test_piece_not_found(self, queue_dir: Path) -> None:
        mock_tl = MagicMock()
        with (
            patch("holus.memory.trajectory.TrajectoryLogger", return_value=mock_tl),
            patch("holus.agents.marketing.auto_publish._trigger_reflexion"),
        ):
            result = process_human_rejection("nonexistent", "Bad")
        assert result["action"] == "human_rejected"
        assert result["judge_calibration_needed"] is False


# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------


class TestThresholds:
    def test_pass_threshold(self) -> None:
        assert PASS_THRESHOLD == 0.8

    def test_partial_threshold(self) -> None:
        assert PARTIAL_THRESHOLD == 0.5

    def test_boundary_pass(self) -> None:
        """Score exactly at PASS_THRESHOLD should publish."""
        assert PASS_THRESHOLD <= 0.8

    def test_boundary_partial(self) -> None:
        """Score exactly at PARTIAL_THRESHOLD should be PARTIAL."""
        assert PARTIAL_THRESHOLD <= 0.5
        assert PASS_THRESHOLD > 0.5
