"""Tests for the orchestrator — 3 autonomous cron cycles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


@dataclass
class FakeLearningReport:
    trajectory_entries_analyzed: int = 42
    insights: list[Any] = field(default_factory=lambda: [{"pattern": "tutorials win"}])
    memory_updated: bool = True
    knowledge_files_updated: list[str] = field(default_factory=lambda: ["strategy.md"])
    gaps_processed: int = 2
    skipped_reason: str | None = None


@dataclass
class FakeEvolutionReport:
    generation: int = 3
    best_variant_id: str = "v3"
    best_avg_score: float = 0.87


@dataclass
class FakeDiagnosticReport:
    critical: list[Any] = field(default_factory=list)
    high: list[Any] = field(default_factory=lambda: [{"issue": "low judge coverage"}])
    medium: list[Any] = field(default_factory=list)
    suggestions: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# content_cycle tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_content_cycle_with_idea():
    """When an idea is provided, run_from_idea is used without auto-publishing."""
    fake_results = [{"piece_id": "p1"}, {"piece_id": "p2"}]

    with (
        patch(
            "holus.agents.marketing.idea_runner.run_from_idea",
            return_value=fake_results,
        ) as mock_idea,
        patch(
            "holus.agents.marketing.idea_runner.run_from_bandit",
        ) as mock_bandit,
    ):
        from holus.agents.marketing.orchestrator import content_cycle

        summary = await content_cycle(idea="test tutorial about AI agents")

    mock_idea.assert_called_once_with("test tutorial about AI agents")
    mock_bandit.assert_not_called()
    assert summary == {
        "generated": 2,
        "publish_actions": 0,
        "published": 0,
        "needs_review": 0,
        "rejected": 0,
    }


@pytest.mark.asyncio
async def test_content_cycle_auto_mode():
    """Without an idea, run_from_bandit is used (auto-mode)."""
    fake_results = [{"piece_id": "p1"}]

    with (
        patch(
            "holus.agents.marketing.idea_runner.run_from_idea",
        ) as mock_idea,
        patch(
            "holus.agents.marketing.idea_runner.run_from_bandit",
            return_value=fake_results,
        ) as mock_bandit,
    ):
        from holus.agents.marketing.orchestrator import content_cycle

        summary = await content_cycle()

    mock_idea.assert_not_called()
    mock_bandit.assert_called_once()
    assert summary["generated"] == 1
    assert summary["published"] == 0


@pytest.mark.asyncio
async def test_p0_content_cycle_keeps_generated_content_local_without_external_delivery():
    """Scheduled content cycle keeps generated work local for review."""
    fake_results = [
        {"piece_id": "p1", "judge_score": 0.91, "status": "pending_review"},
        {"piece_id": "p2", "judge_score": 0.62, "status": "pending_review"},
    ]

    with (
        patch(
            "holus.agents.marketing.idea_runner.run_from_bandit",
            return_value=fake_results,
        ),
        patch("holus.integrations.holus_social_api.HolusSocialAPIClient") as social_client_cls,
    ):
        from holus.agents.marketing.orchestrator import content_cycle

        summary = await content_cycle()

    assert summary == {
        "generated": 2,
        "publish_actions": 0,
        "published": 0,
        "needs_review": 0,
        "rejected": 0,
    }
    social_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_content_cycle_empty_results():
    """Edge case: no content generated and nothing to publish."""
    with patch(
        "holus.agents.marketing.idea_runner.run_from_bandit",
        return_value=[],
    ):
        from holus.agents.marketing.orchestrator import content_cycle

        summary = await content_cycle()

    assert summary == {
        "generated": 0,
        "publish_actions": 0,
        "published": 0,
        "needs_review": 0,
        "rejected": 0,
    }


# ---------------------------------------------------------------------------
# analytics_cycle tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analytics_cycle():
    """Verify analytics summary computation from mock data."""
    fake_analytics = [
        {"piece_id": "p1", "engagement_signal": 0.8, "blended_reward": 0.6},
        {"piece_id": "p2", "engagement_signal": 0.4, "blended_reward": 0.2},
    ]

    with patch(
        "holus.agents.marketing.analytics_collector.collect_analytics",
        new_callable=AsyncMock,
        return_value=fake_analytics,
    ):
        from holus.agents.marketing.orchestrator import analytics_cycle

        summary = await analytics_cycle()

    assert summary["pieces_collected"] == 2
    assert summary["avg_engagement"] == pytest.approx(0.6)
    assert summary["avg_reward"] == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_analytics_cycle_empty():
    """Empty analytics should not divide by zero."""
    with patch(
        "holus.agents.marketing.analytics_collector.collect_analytics",
        new_callable=AsyncMock,
        return_value=[],
    ):
        from holus.agents.marketing.orchestrator import analytics_cycle

        summary = await analytics_cycle()

    assert summary["pieces_collected"] == 0
    assert summary["avg_engagement"] == 0
    assert summary["avg_reward"] == 0


# ---------------------------------------------------------------------------
# improvement_cycle tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_improvement_cycle(tmp_path, monkeypatch):
    """All 3 steps run: learning loop, prompt evolution, diagnostician."""
    # Set up trajectory file with enough entries to trigger evolution
    traj_path = tmp_path / ".self-improvement" / "memory"
    traj_path.mkdir(parents=True)
    traj_file = traj_path / "trajectory.jsonl"
    entries = [
        json.dumps({"agent_id": "idea-generator", "judge_verdict": "PASS"}) + "\n"
        for _ in range(150)
    ]
    traj_file.write_text("".join(entries))

    # Patch Path references inside orchestrator to use tmp_path
    monkeypatch.chdir(tmp_path)

    fake_report = FakeLearningReport()
    mock_learning = MagicMock()
    mock_learning.return_value.run.return_value = fake_report

    fake_evo_report = FakeEvolutionReport()
    mock_evo_instance = MagicMock()
    mock_evo_instance.population_size = 5
    mock_evo_instance.evolve = AsyncMock(return_value=fake_evo_report)

    mock_evo_cls = MagicMock(return_value=mock_evo_instance)

    fake_diag = FakeDiagnosticReport()

    with (
        patch("holus.self_improvement.learning_loop.WeeklyLearningLoop", mock_learning),
        patch("holus.self_improvement.prompt_evolution.PromptEvolution", mock_evo_cls),
        patch(
            "holus.self_improvement.diagnostician.run_diagnostic",
            return_value=fake_diag,
        ),
        patch("holus.self_improvement.diagnostician.save_report") as mock_save_diag,
    ):
        from holus.agents.marketing.orchestrator import improvement_cycle

        summary = await improvement_cycle()

    # Learning loop ran
    assert summary["entries_analyzed"] == 42
    assert summary["insights"] == 1
    assert summary["memory_updated"] is True

    # Evolution ran
    assert summary["evolution_ran"] is True

    # Diagnostician ran and found 1 high finding
    assert summary["diagnostic_findings"] == 1
    mock_save_diag.assert_called_once()


@pytest.mark.asyncio
async def test_improvement_cycle_partial_failure(tmp_path, monkeypatch):
    """One step failing doesn't crash others — each is non-blocking."""
    traj_path = tmp_path / ".self-improvement" / "memory"
    traj_path.mkdir(parents=True)
    traj_file = traj_path / "trajectory.jsonl"
    entries = [
        json.dumps({"agent_id": "idea-generator", "judge_verdict": "PASS"}) + "\n"
        for _ in range(150)
    ]
    traj_file.write_text("".join(entries))

    monkeypatch.chdir(tmp_path)

    fake_report = FakeLearningReport()
    mock_learning = MagicMock()
    mock_learning.return_value.run.return_value = fake_report

    # Prompt evolution raises
    mock_evo_instance = MagicMock()
    mock_evo_instance.population_size = 5
    mock_evo_instance.evolve = AsyncMock(side_effect=RuntimeError("LLM timeout"))
    mock_evo_cls = MagicMock(return_value=mock_evo_instance)

    # Diagnostician raises
    mock_diag = MagicMock(side_effect=RuntimeError("file not found"))

    with (
        patch("holus.self_improvement.learning_loop.WeeklyLearningLoop", mock_learning),
        patch("holus.self_improvement.prompt_evolution.PromptEvolution", mock_evo_cls),
        patch("holus.self_improvement.diagnostician.run_diagnostic", mock_diag),
    ):
        from holus.agents.marketing.orchestrator import improvement_cycle

        # Should NOT raise — failures are caught
        summary = await improvement_cycle()

    # Learning loop still produced results
    assert summary["entries_analyzed"] == 42
    # Evolution failed → None
    assert summary["evolution_ran"] is False
    # Diagnostician failed → 0 findings
    assert summary["diagnostic_findings"] == 0


@pytest.mark.asyncio
async def test_improvement_cycle_below_evolution_gate(tmp_path, monkeypatch):
    """Evolution is skipped when trajectory has fewer than 100 entries."""
    traj_path = tmp_path / ".self-improvement" / "memory"
    traj_path.mkdir(parents=True)
    traj_file = traj_path / "trajectory.jsonl"
    entries = [json.dumps({"agent_id": "idea-generator"}) + "\n" for _ in range(50)]
    traj_file.write_text("".join(entries))

    monkeypatch.chdir(tmp_path)

    fake_report = FakeLearningReport()
    mock_learning = MagicMock()
    mock_learning.return_value.run.return_value = fake_report

    with (
        patch("holus.self_improvement.learning_loop.WeeklyLearningLoop", mock_learning),
        patch(
            "holus.self_improvement.diagnostician.run_diagnostic", side_effect=RuntimeError("skip")
        ),
    ):
        from holus.agents.marketing.orchestrator import improvement_cycle

        summary = await improvement_cycle()

    assert summary["evolution_ran"] is False


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestDetectFailureStreaks:
    """Unit tests for _detect_failure_streaks."""

    def test_no_streaks(self):
        from holus.agents.marketing.orchestrator import _detect_failure_streaks

        entries = [
            {"agent_id": "a", "judge_verdict": "PASS"},
            {"agent_id": "a", "judge_verdict": "FAIL"},
            {"agent_id": "a", "judge_verdict": "PASS"},
        ]
        assert _detect_failure_streaks(entries) == {}

    def test_streak_detected(self):
        from holus.agents.marketing.orchestrator import _detect_failure_streaks

        entries = [
            {"agent_id": "a", "judge_verdict": "FAIL"},
            {"agent_id": "a", "judge_verdict": "PARTIAL"},
            {"agent_id": "a", "judge_verdict": "FAIL"},
        ]
        result = _detect_failure_streaks(entries)
        assert result == {"a": 3}

    def test_multiple_agents(self):
        from holus.agents.marketing.orchestrator import _detect_failure_streaks

        entries = [
            {"agent_id": "a", "judge_verdict": "FAIL"},
            {"agent_id": "b", "judge_verdict": "FAIL"},
            {"agent_id": "a", "judge_verdict": "FAIL"},
            {"agent_id": "b", "judge_verdict": "FAIL"},
            {"agent_id": "a", "judge_verdict": "FAIL"},
            {"agent_id": "b", "judge_verdict": "FAIL"},
        ]
        result = _detect_failure_streaks(entries)
        assert result == {"a": 3, "b": 3}

    def test_streak_below_threshold(self):
        from holus.agents.marketing.orchestrator import _detect_failure_streaks

        entries = [
            {"agent_id": "a", "judge_verdict": "FAIL"},
            {"agent_id": "a", "judge_verdict": "FAIL"},
            {"agent_id": "a", "judge_verdict": "PASS"},
        ]
        # Max streak is 2, threshold is 3
        assert _detect_failure_streaks(entries) == {}

    def test_empty_entries(self):
        from holus.agents.marketing.orchestrator import _detect_failure_streaks

        assert _detect_failure_streaks([]) == {}


class TestLoadRecentTrajectory:
    """Unit tests for _load_recent_trajectory."""

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from holus.agents.marketing.orchestrator import _load_recent_trajectory

        assert _load_recent_trajectory() == []

    def test_valid_entries(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        traj_dir = tmp_path / ".self-improvement" / "memory"
        traj_dir.mkdir(parents=True)
        traj_file = traj_dir / "trajectory.jsonl"
        traj_file.write_text(
            json.dumps({"agent_id": "a", "judge_verdict": "PASS"})
            + "\n"
            + json.dumps({"agent_id": "b", "judge_verdict": "FAIL"})
            + "\n"
        )
        from holus.agents.marketing.orchestrator import _load_recent_trajectory

        entries = _load_recent_trajectory()
        assert len(entries) == 2

    def test_malformed_json_skipped(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        traj_dir = tmp_path / ".self-improvement" / "memory"
        traj_dir.mkdir(parents=True)
        traj_file = traj_dir / "trajectory.jsonl"
        traj_file.write_text("not json\n" + json.dumps({"agent_id": "a"}) + "\n")
        from holus.agents.marketing.orchestrator import _load_recent_trajectory

        entries = _load_recent_trajectory()
        assert len(entries) == 1
