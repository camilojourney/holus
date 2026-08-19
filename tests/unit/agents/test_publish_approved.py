"""Tests for publish_approved module — dry-run and publishing logic."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from holus.agents.marketing.content_queue import QueuedContent
from holus.agents.marketing.publish_approved import dry_run


def _make_content(
    piece_id: str = "abc12345",
    platform: str = "linkedin",
    text: str = "Hello world!",
) -> QueuedContent:
    return QueuedContent(
        piece_id=piece_id,
        product="pilaster",
        platform=platform,
        content_type="tutorial",
        topic="Test topic",
        text=text,
        reasoning="Test reasoning",
        generated_at=datetime(2026, 3, 2, 12, 0, tzinfo=UTC),
        status="approved",
    )


class TestDryRun:
    """Test dry-run mode."""

    def test_dry_run_no_content(self, capsys):
        """Dry run with no approved content shows message."""
        with patch("holus.agents.marketing.publish_approved.list_approved", return_value=[]):
            dry_run()
        captured = capsys.readouterr()
        assert "No approved content" in captured.out

    def test_dry_run_shows_preview(self, capsys):
        """Dry run shows content preview table."""
        content = _make_content(text="This is a test post for LinkedIn.")
        with patch(
            "holus.agents.marketing.publish_approved.list_approved",
            return_value=[content],
        ):
            dry_run()
        captured = capsys.readouterr()
        assert "abc12345" in captured.out
        assert "linkedin" in captured.out
        assert "DRY RUN" in captured.out

    def test_dry_run_shows_char_count(self, capsys):
        """Dry run shows character count and limit."""
        text = "x" * 150
        content = _make_content(platform="twitter", text=text)
        with patch(
            "holus.agents.marketing.publish_approved.list_approved",
            return_value=[content],
        ):
            dry_run()
        captured = capsys.readouterr()
        assert "150" in captured.out
        assert "280" in captured.out

    def test_dry_run_warns_over_limit(self, capsys):
        """Dry run warns when content exceeds platform limit."""
        text = "x" * 300
        content = _make_content(platform="twitter", text=text)
        with patch(
            "holus.agents.marketing.publish_approved.list_approved",
            return_value=[content],
        ):
            dry_run()
        captured = capsys.readouterr()
        assert "OVER" in captured.out
        assert "300" in captured.out
        assert "280" in captured.out

    def test_dry_run_ok_within_limit(self, capsys):
        """Dry run shows OK when within limit."""
        content = _make_content(platform="linkedin", text="Short post")
        with patch(
            "holus.agents.marketing.publish_approved.list_approved",
            return_value=[content],
        ):
            dry_run()
        captured = capsys.readouterr()
        assert "OK" in captured.out
        assert "All content within platform limits" in captured.out

    def test_dry_run_multiple_pieces(self, capsys):
        """Dry run handles multiple content pieces."""
        pieces = [
            _make_content(piece_id="piece001", platform="linkedin", text="Post 1"),
            _make_content(piece_id="piece002", platform="twitter", text="Post 2"),
            _make_content(piece_id="piece003", platform="threads", text="Post 3"),
        ]
        with patch(
            "holus.agents.marketing.publish_approved.list_approved",
            return_value=pieces,
        ):
            dry_run()
        captured = capsys.readouterr()
        assert "3 approved" in captured.out
        assert "piece001" in captured.out
        assert "piece002" in captured.out
        assert "piece003" in captured.out

    def test_dry_run_truncates_preview(self, capsys):
        """Dry run truncates long content in preview — not all chars shown."""
        long_text = "A" * 200
        content = _make_content(text=long_text)
        with patch(
            "holus.agents.marketing.publish_approved.list_approved",
            return_value=[content],
        ):
            dry_run()
        captured = capsys.readouterr()
        # Full 200-char string should NOT appear in output (preview is truncated)
        assert long_text not in captured.out
        # But the char count should be shown
        assert "200" in captured.out


class TestMainArgParsing:
    """Test CLI argument parsing."""

    def test_dry_run_flag_parsed(self):
        """--dry-run flag is recognized."""
        from holus.agents.marketing.publish_approved import main

        with (
            patch("sys.argv", ["publish_approved", "--dry-run"]),
            patch("holus.agents.marketing.publish_approved.dry_run") as mock_dry_run,
        ):
            main()
            mock_dry_run.assert_called_once()

    def test_p0_no_flag_runs_contained_publish_flow(self):
        """Non-dry-run CLI uses the guarded publish flow without exiting."""
        from holus.agents.marketing.publish_approved import main

        with (
            patch("sys.argv", ["publish_approved"]),
            patch("holus.agents.marketing.publish_approved.publish_all", return_value=object()),
            patch("holus.agents.marketing.publish_approved.asyncio.run") as mock_run,
        ):
            main()

        mock_run.assert_called_once()
