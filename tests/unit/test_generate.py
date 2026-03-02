"""Tests for the generate module (just generate command)."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import yaml

from holus.generate import _list_queue_files, _print_summary, main

if TYPE_CHECKING:
    import pytest


# ---------------------------------------------------------------------------
# _list_queue_files
# ---------------------------------------------------------------------------


class TestListQueueFiles:
    def test_empty_dir(self, tmp_path: Path) -> None:
        queue = tmp_path / "queue"
        queue.mkdir()
        with patch("holus.generate.QUEUE_DIR", queue):
            assert _list_queue_files() == []

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        queue = tmp_path / "nonexistent"
        with patch("holus.generate.QUEUE_DIR", queue):
            assert _list_queue_files() == []

    def test_returns_sorted_yaml_files(self, tmp_path: Path) -> None:
        queue = tmp_path / "queue"
        queue.mkdir()
        (queue / "b-piece.yaml").write_text("text: hello")
        (queue / "a-piece.yaml").write_text("text: world")
        (queue / "not-yaml.txt").write_text("ignored")
        with patch("holus.generate.QUEUE_DIR", queue):
            files = _list_queue_files()
        assert len(files) == 2
        assert files[0].name == "a-piece.yaml"
        assert files[1].name == "b-piece.yaml"


# ---------------------------------------------------------------------------
# _print_summary
# ---------------------------------------------------------------------------


class TestPrintSummary:
    def test_no_new_content(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        queue = tmp_path / "queue"
        queue.mkdir()
        with patch("holus.generate.QUEUE_DIR", queue):
            _print_summary(before_count=0)
        out = capsys.readouterr().out
        assert "No new content generated" in out

    def test_shows_new_content(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        queue = tmp_path / "queue"
        queue.mkdir()
        data = {
            "piece_id": "test-001",
            "platform": "linkedin",
            "topic": "Building AI products",
            "text": "I built 3 AI products. Here's what I learned.",
        }
        (queue / "test-001.yaml").write_text(yaml.dump(data, default_flow_style=False))
        with patch("holus.generate.QUEUE_DIR", queue):
            _print_summary(before_count=0)
        out = capsys.readouterr().out
        assert "1 new piece(s)" in out
        assert "LINKEDIN" in out
        assert "Building AI products" in out
        assert "test-001" in out
        assert "just review-content" in out

    def test_only_counts_new_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        queue = tmp_path / "queue"
        queue.mkdir()
        # Pre-existing file
        (queue / "a-old.yaml").write_text(
            yaml.dump({"piece_id": "old", "platform": "twitter", "topic": "old", "text": "old"})
        )
        # New file
        (queue / "b-new.yaml").write_text(
            yaml.dump(
                {"piece_id": "new", "platform": "linkedin", "topic": "new stuff", "text": "new"}
            )
        )
        with patch("holus.generate.QUEUE_DIR", queue):
            _print_summary(before_count=1)
        out = capsys.readouterr().out
        assert "1 new piece(s)" in out
        assert "new stuff" in out


# ---------------------------------------------------------------------------
# main — exit on missing API key
# ---------------------------------------------------------------------------


class TestMainNoApiKey:
    def test_exits_without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch("holus.generate.QUEUE_DIR", Path("/tmp/holus-test-fake")):
            try:
                main()
                raised = False
            except SystemExit as exc:
                raised = True
                assert exc.code == 1
            assert raised, "Expected SystemExit(1) when API key is missing"


# ---------------------------------------------------------------------------
# main — successful generation
# ---------------------------------------------------------------------------


class TestMainSuccess:
    def test_runs_agent_and_prints_summary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-for-unit-test")

        queue = tmp_path / "queue"
        queue.mkdir()

        # Simulate the agent writing a queue file during run
        fake_result = {
            "evaluation": {"pieces_created": 1},
            "strategy_reasoning": "Tutorial posts work best for LinkedIn authority.",
        }

        async def mock_run_agent() -> dict:
            # Simulate agent writing to queue during execution
            data = {
                "piece_id": "gen-001",
                "platform": "linkedin",
                "topic": "AI implementation frameworks",
                "text": "I built 3 AI products in production. Here is what I learned.",
            }
            (queue / "gen-001.yaml").write_text(yaml.dump(data, default_flow_style=False))
            return fake_result

        with (
            patch("holus.generate.QUEUE_DIR", queue),
            patch("holus.generate._run_agent", side_effect=mock_run_agent),
            patch("holus.generate.run_preflight") as mock_preflight,
        ):
            mock_preflight.return_value = [
                MagicMock(name="API", passed=True, detail="OK", fix=""),
            ]
            with contextlib.suppress(SystemExit):
                main()

        out = capsys.readouterr().out
        assert "GENERATING CONTENT" in out
        assert "GENERATION COMPLETE" in out
        assert "1 new piece(s)" in out
        assert "LINKEDIN" in out


# ---------------------------------------------------------------------------
# main — agent failure
# ---------------------------------------------------------------------------


class TestMainAgentFailure:
    def test_exits_on_agent_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-for-unit-test")

        queue = tmp_path / "queue"
        queue.mkdir()

        async def mock_run_agent_fail() -> dict:
            raise RuntimeError("Redis connection refused")

        with (
            patch("holus.generate.QUEUE_DIR", queue),
            patch("holus.generate._run_agent", side_effect=mock_run_agent_fail),
            patch("holus.generate.run_preflight") as mock_preflight,
        ):
            mock_preflight.return_value = [
                MagicMock(name="API", passed=True, detail="OK", fix=""),
            ]
            try:
                main()
                raised = False
            except SystemExit as exc:
                raised = True
                assert exc.code == 1
            assert raised, "Expected SystemExit(1) on agent failure"
