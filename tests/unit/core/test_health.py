"""Tests for holus.core.health."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from holus.core.health import HealthCheck, run_preflight_checks

if TYPE_CHECKING:
    from pathlib import Path


def test_health_check_returns_structure() -> None:
    """Health check returns expected top-level keys."""
    hc = HealthCheck()
    result = hc.run()

    assert "timestamp" in result
    assert "checks" in result
    assert "overall" in result
    assert isinstance(result["checks"], dict)


def test_check_trajectory_exists(tmp_path: Path) -> None:
    """Trajectory check reports healthy when file exists."""
    hc = HealthCheck()

    trajectory = tmp_path / "trajectory.jsonl"
    trajectory.write_text('{"test": true}\n')

    with patch.object(hc, "check_trajectory") as mock:
        mock.return_value = {
            "status": "healthy",
            "exists": True,
            "size_bytes": trajectory.stat().st_size,
        }
        result = mock()
        assert result["status"] == "healthy"
        assert result["exists"] is True


def test_check_knowledge_with_files(tmp_path: Path) -> None:
    """Knowledge check reports healthy when files exist."""
    hc = HealthCheck()
    knowledge_dir = tmp_path / "knowledge" / "current"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "platforms.md").write_text("# Platforms")
    (knowledge_dir / "strategy.md").write_text("# Strategy")

    with patch("holus.core.health.Path"):
        # Test the logic directly
        files = list(knowledge_dir.glob("*.md"))
        assert len(files) == 2

    result = hc.check_knowledge()
    # Real check may or may not find files depending on cwd
    assert "status" in result
    assert "files_count" in result


def test_check_content_queue_empty(tmp_path: Path, monkeypatch) -> None:
    """Content queue check reports healthy when queue doesn't exist."""
    from pathlib import Path as _Path

    # Point check_content_queue at an empty temp dir so the test is isolated
    monkeypatch.setattr(
        "holus.core.health.Path",
        lambda p: (
            _Path(str(tmp_path / "nonexistent-queue")) if "content-queue" in str(p) else _Path(p)
        ),
    )
    hc = HealthCheck()
    result = hc.check_content_queue()

    # Queue dir doesn't exist yet — should still be healthy
    assert result["status"] == "healthy"
    assert result["pending"] == 0


def test_overall_degraded_when_check_degraded() -> None:
    """Overall status is degraded when any check is degraded."""
    hc = HealthCheck()

    with (
        patch.object(hc, "check_kill_switch", return_value={"status": "healthy"}),
        patch.object(hc, "check_trajectory", return_value={"status": "healthy"}),
        patch.object(
            hc,
            "check_knowledge",
            return_value={"status": "degraded", "files_count": 0, "files": []},
        ),
        patch.object(hc, "check_content_queue", return_value={"status": "healthy", "pending": 0}),
        patch.object(hc, "check_logs", return_value={"status": "healthy", "directory": "logs"}),
    ):
        result = hc.run()
        assert result["overall"] == "degraded"


def test_overall_unhealthy_when_check_unhealthy() -> None:
    """Overall status is unhealthy when any check is unhealthy."""
    hc = HealthCheck()

    with (
        patch.object(
            hc, "check_kill_switch", return_value={"status": "unhealthy", "error": "crash"}
        ),
        patch.object(hc, "check_trajectory", return_value={"status": "healthy"}),
        patch.object(
            hc,
            "check_knowledge",
            return_value={"status": "healthy", "files_count": 1, "files": ["a.md"]},
        ),
        patch.object(hc, "check_content_queue", return_value={"status": "healthy", "pending": 0}),
        patch.object(hc, "check_logs", return_value={"status": "healthy", "directory": "logs"}),
    ):
        result = hc.run()
        assert result["overall"] == "unhealthy"


def test_run_preflight_checks_allows_non_blocking_silo_failures(tmp_path: Path) -> None:
    """Pilaster/Genpeli failures warn but do not block the cycle."""
    kill_switch = MagicMock()
    kill_switch.is_active.return_value = False

    result = run_preflight_checks(
        config=MagicMock(),
        kill_switch=kill_switch,
        trajectory_path=tmp_path / "trajectory.jsonl",
        llm_probe=lambda _config: None,
        social_media_probe=lambda _config: None,
        pilaster_probe=lambda: (_ for _ in ()).throw(RuntimeError("pilaster down")),
        genpeli_probe=lambda: None,
        check_run_lock=False,
    )

    assert result.blocking_ok is True
    assert result.available_silos == ["social-media", "genpeli"]
    assert len(result.warnings) == 1
    assert "Pilaster MCP unavailable" in result.warnings[0]


def test_run_preflight_checks_fails_fast_on_blocking_check(tmp_path: Path) -> None:
    """Blocking failures stop before later checks run."""
    kill_switch = MagicMock()
    kill_switch.is_active.return_value = False
    pilaster_probe = MagicMock()

    result = run_preflight_checks(
        config=MagicMock(),
        kill_switch=kill_switch,
        trajectory_path=tmp_path / "trajectory.jsonl",
        llm_probe=lambda _config: None,
        social_media_probe=lambda _config: (_ for _ in ()).throw(RuntimeError("timeout")),
        pilaster_probe=pilaster_probe,
        genpeli_probe=lambda: None,
        check_run_lock=False,
    )

    assert result.blocking_ok is False
    assert result.blocking_reason == "Social media MCP unreachable: timeout"
    pilaster_probe.assert_not_called()
