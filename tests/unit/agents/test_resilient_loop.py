"""Tests for Spec 027 Cycle 3 — resilient loop wired into MarketingAgent.

Tests verify that:
- CycleContext is created and transitions are logged on a successful run
- A blocking preflight failure aborts the cycle before the graph runs
- Any unhandled exception transitions to FAILED and still writes a trajectory entry
- 3 consecutive failures trigger the BUILD_PAUSED alert log
- The health CLI command includes preflight, watchdog, and last_trajectory_entry keys
"""

from __future__ import annotations

import contextlib
import importlib
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holus.core.cycle_state import CycleState, HealthResult

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_health_result(*, blocking_ok: bool, silos: list[str] | None = None) -> HealthResult:
    return HealthResult(
        blocking_ok=blocking_ok,
        available_silos=silos if silos is not None else ["social_media"],
        warnings=[] if blocking_ok else ["Kill switch active"],
    )


def _load_trajectory(path: Path) -> list[dict[str, Any]]:
    """Read all JSONL lines from the trajectory file."""
    if not path.exists():
        return []
    lines = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            with contextlib.suppress(json.JSONDecodeError):
                lines.append(json.loads(ln))
    return lines


def _summary_entries(trajectory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only summary entries (those with a 'phase' key)."""
    return [e for e in trajectory if "phase" in e]


# ---------------------------------------------------------------------------
# MarketingAgent.run() — resilient loop
# ---------------------------------------------------------------------------


class TestResilientLoopSuccess:
    """Happy-path: preflight passes, graph runs, trajectory entry written as 'done'."""

    @pytest.mark.asyncio
    async def test_run_writes_done_trajectory(self, tmp_path: Path) -> None:
        trajectory_path = tmp_path / "trajectory.jsonl"

        # Patch run_preflight_checks to return blocking_ok=True
        good_health = _make_health_result(blocking_ok=True)

        # Minimal graph output
        graph_result: dict[str, Any] = {
            "generated_content": [{"piece_id": "p1"}],
            "post_results": [{"status": "pending_review"}],
            "evaluation": {},
            "error": None,
        }

        with (
            patch(
                "holus.agents.marketing.agent.run_preflight_checks",
                return_value=good_health,
            ),
            patch(
                "holus.agents.base.BaseAgent.__init__",
                return_value=None,
            ),
        ):
            from holus.agents.marketing.agent import MarketingAgent

            agent = object.__new__(MarketingAgent)
            # Minimal attributes needed for run()
            agent._TRAJECTORY_PATH = trajectory_path  # type: ignore[attr-defined]

            # Patch compile() to return a fake app
            fake_app = MagicMock()
            fake_app.ainvoke = AsyncMock(return_value=graph_result)
            agent.compile = MagicMock(return_value=fake_app)  # type: ignore[attr-defined]
            agent.default_state = MagicMock(return_value={"cycle_id": "test-123"})  # type: ignore[attr-defined]

            result = await agent.run()

        assert result == graph_result

        entries = _load_trajectory(trajectory_path)
        summaries = _summary_entries(entries)
        assert summaries, "Expected at least one summary entry in trajectory"
        last = summaries[-1]
        assert last["phase"] == "done", f"Expected phase=done, got {last['phase']}"
        assert last["content_created"] == 1
        assert last["content_posted"] == 1
        assert last["error"] is None

    @pytest.mark.asyncio
    async def test_run_transitions_through_all_phases(self, tmp_path: Path) -> None:
        """Verify that transition events for all major states are written."""
        trajectory_path = tmp_path / "trajectory.jsonl"

        good_health = _make_health_result(blocking_ok=True)
        graph_result: dict[str, Any] = {
            "generated_content": [],
            "post_results": [],
            "evaluation": {},
            "error": None,
        }

        with (
            patch(
                "holus.agents.marketing.agent.run_preflight_checks",
                return_value=good_health,
            ),
            patch("holus.agents.base.BaseAgent.__init__", return_value=None),
        ):
            from holus.agents.marketing.agent import MarketingAgent

            agent = object.__new__(MarketingAgent)
            agent._TRAJECTORY_PATH = trajectory_path  # type: ignore[attr-defined]

            fake_app = MagicMock()
            fake_app.ainvoke = AsyncMock(return_value=graph_result)
            agent.compile = MagicMock(return_value=fake_app)  # type: ignore[attr-defined]
            agent.default_state = MagicMock(return_value={})  # type: ignore[attr-defined]

            await agent.run()

        entries = _load_trajectory(trajectory_path)
        transitions = [e for e in entries if e.get("event") == "transition"]
        to_states = [e["to_state"] for e in transitions]

        # Must hit HEALTH_CHECK, LOADING_STATE, OBSERVING, CREATING, QUALITY_CHECK, DONE
        for expected in (
            CycleState.HEALTH_CHECK,
            CycleState.LOADING_STATE,
            CycleState.OBSERVING,
            CycleState.CREATING,
            CycleState.QUALITY_CHECK,
            CycleState.DONE,
        ):
            assert str(expected) in to_states, f"Missing transition to {expected}"


class TestResilientLoopPreflightBlocked:
    """Blocking preflight failure: cycle aborts, trajectory entry written as 'failed'."""

    @pytest.mark.asyncio
    async def test_blocked_preflight_aborts_graph(self, tmp_path: Path) -> None:
        trajectory_path = tmp_path / "trajectory.jsonl"

        bad_health = _make_health_result(blocking_ok=False)

        with (
            patch(
                "holus.agents.marketing.agent.run_preflight_checks",
                return_value=bad_health,
            ),
            patch("holus.agents.base.BaseAgent.__init__", return_value=None),
        ):
            from holus.agents.marketing.agent import MarketingAgent

            agent = object.__new__(MarketingAgent)
            agent._TRAJECTORY_PATH = trajectory_path  # type: ignore[attr-defined]

            # compile should never be called if preflight blocks
            agent.compile = MagicMock(side_effect=RuntimeError("should not be called"))  # type: ignore[attr-defined]
            agent.default_state = MagicMock(return_value={})  # type: ignore[attr-defined]

            result = await agent.run()

        assert result == {}

        entries = _load_trajectory(trajectory_path)
        summaries = _summary_entries(entries)
        assert summaries, "Trajectory entry must be written even when preflight blocks"
        last = summaries[-1]
        assert last["phase"] == "failed", f"Expected phase=failed, got {last['phase']}"
        assert "Preflight blocked" in (last.get("error") or "")


class TestResilientLoopException:
    """Unhandled exception mid-cycle: trajectory entry written as 'failed'."""

    @pytest.mark.asyncio
    async def test_exception_writes_failed_trajectory(self, tmp_path: Path) -> None:
        trajectory_path = tmp_path / "trajectory.jsonl"

        good_health = _make_health_result(blocking_ok=True)

        with (
            patch(
                "holus.agents.marketing.agent.run_preflight_checks",
                return_value=good_health,
            ),
            patch("holus.agents.base.BaseAgent.__init__", return_value=None),
        ):
            from holus.agents.marketing.agent import MarketingAgent

            agent = object.__new__(MarketingAgent)
            agent._TRAJECTORY_PATH = trajectory_path  # type: ignore[attr-defined]

            # Graph raises an unexpected error
            fake_app = MagicMock()
            fake_app.ainvoke = AsyncMock(side_effect=RuntimeError("LLM timeout"))
            agent.compile = MagicMock(return_value=fake_app)  # type: ignore[attr-defined]
            agent.default_state = MagicMock(return_value={})  # type: ignore[attr-defined]

            result = await agent.run()

        # Returns empty dict (not raised)
        assert isinstance(result, dict)

        entries = _load_trajectory(trajectory_path)
        summaries = _summary_entries(entries)
        assert summaries, "Trajectory entry must be written on exception"
        last = summaries[-1]
        assert last["phase"] == "failed"
        assert "LLM timeout" in (last.get("error") or "")


class TestConsecutiveFailureAlert:
    """3 consecutive failures → BUILD_PAUSED alert logged."""

    @pytest.mark.asyncio
    async def test_three_failures_trigger_alert(self, tmp_path: Path, caplog: Any) -> None:
        import logging

        trajectory_path = tmp_path / "trajectory.jsonl"

        # Write 2 prior "failed" summary entries
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        for i in range(2):
            entry = {
                "cycle_id": f"2026-03-12T10:0{i}:00+00:00",
                "phase": "failed",
                "health": None,
                "content_created": 0,
                "content_posted": 0,
                "content_failed": 0,
                "quality_scores": [],
                "capability_gaps": [],
                "duration_seconds": 1.0,
                "error": "prior failure",
            }
            with trajectory_path.open("a") as f:
                f.write(json.dumps(entry) + "\n")

        # The 3rd failure will come from the agent run below
        good_health = _make_health_result(blocking_ok=True)

        with (
            patch(
                "holus.agents.marketing.agent.run_preflight_checks",
                return_value=good_health,
            ),
            patch("holus.agents.base.BaseAgent.__init__", return_value=None),
            caplog.at_level(logging.ERROR, logger="holus.agents.marketing.agent"),
        ):
            from holus.agents.marketing.agent import MarketingAgent

            agent = object.__new__(MarketingAgent)
            agent._TRAJECTORY_PATH = trajectory_path  # type: ignore[attr-defined]

            fake_app = MagicMock()
            fake_app.ainvoke = AsyncMock(side_effect=RuntimeError("3rd failure"))
            agent.compile = MagicMock(return_value=fake_app)  # type: ignore[attr-defined]
            agent.default_state = MagicMock(return_value={})  # type: ignore[attr-defined]

            await agent.run()

        assert any(
            "BUILD_PAUSED" in record.message
            for record in caplog.records
        ), "Expected BUILD_PAUSED alert in logs after 3 consecutive failures"


# ---------------------------------------------------------------------------
# Health CLI — _run_health_check enriched output
# ---------------------------------------------------------------------------


class TestHealthCliOutput:
    """Verify the health command returns enriched keys: preflight, watchdog, last_trajectory_entry."""

    def test_health_output_keys(self, tmp_path: Path, capsys: Any) -> None:
        """_run_health_check() must include preflight, watchdog, and last_trajectory_entry."""
        from holus.core.watchdog import WatchdogResult

        good_health_obj = _make_health_result(blocking_ok=True)
        basic_results: dict[str, Any] = {
            "timestamp": "2026-03-12T00:00:00+00:00",
            "checks": {},
            "overall": "healthy",
        }

        watchdog_result = WatchdogResult(
            alert=False,
            last_success_at=None,
            last_error=None,
            silence_hours=0.5,
        )

        with (
            patch("holus.core.health.HealthCheck.run", return_value=basic_results),
            patch("holus.core.health.run_preflight_checks", return_value=good_health_obj),
            patch("holus.core.watchdog.check_watchdog", return_value=watchdog_result),
            patch("sys.exit"),
        ):
            import holus.__main__ as main_module

            importlib.reload(main_module)
            main_module._run_health_check()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "preflight" in output, "Missing 'preflight' key in health output"
        assert "watchdog" in output, "Missing 'watchdog' key in health output"
        assert "last_trajectory_entry" in output, "Missing 'last_trajectory_entry' key in health output"

        assert "blocking_ok" in output["preflight"]
        assert "available_silos" in output["preflight"]
        assert "alert" in output["watchdog"]
        assert "silence_hours" in output["watchdog"]
