"""Tests for the weekly content calendar view."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import yaml
from rich.console import Console

from holus.agents.marketing.calendar_view import (
    _parse_datetime,
    _show_summary,
    display_calendar,
    list_all,
)


class TestListAll:
    """Test list_all function."""

    def test_empty_dir(self, tmp_path):
        """Returns empty list when directory does not exist."""
        result = list_all(tmp_path / "nonexistent")
        assert result == []

    def test_empty_existing_dir(self, tmp_path):
        """Returns empty list when directory exists but has no YAML files."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        result = list_all(queue_dir)
        assert result == []

    def test_loads_yaml_files(self, tmp_path):
        """Loads all YAML files from directory."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()

        (queue_dir / "abc.yaml").write_text(
            yaml.dump(
                {
                    "piece_id": "abc12345",
                    "product": "pilaster",
                    "platform": "linkedin",
                    "status": "pending_review",
                    "topic": "Test topic",
                }
            )
        )
        (queue_dir / "def.yaml").write_text(
            yaml.dump(
                {
                    "piece_id": "def67890",
                    "product": "genpeli",
                    "platform": "twitter",
                    "status": "approved",
                    "topic": "Another topic",
                }
            )
        )

        result = list_all(queue_dir)
        assert len(result) == 2
        assert result[0]["piece_id"] == "abc12345"
        assert result[1]["piece_id"] == "def67890"

    def test_skips_invalid_yaml(self, tmp_path):
        """Skips files with invalid YAML."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()

        (queue_dir / "good.yaml").write_text(
            yaml.dump({"piece_id": "good1234", "status": "approved"})
        )
        (queue_dir / "bad.yaml").write_text("{{invalid yaml content")

        result = list_all(queue_dir)
        assert len(result) == 1
        assert result[0]["piece_id"] == "good1234"

    def test_skips_empty_yaml(self, tmp_path):
        """Skips YAML files that parse to None."""
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()

        (queue_dir / "empty.yaml").write_text("")
        (queue_dir / "valid.yaml").write_text(
            yaml.dump({"piece_id": "val12345", "status": "pending_review"})
        )

        result = list_all(queue_dir)
        assert len(result) == 1


class TestParseDatetime:
    """Test _parse_datetime helper."""

    def test_iso_string(self):
        result = _parse_datetime("2026-03-02T12:00:00+00:00")
        assert result is not None
        assert result.year == 2026
        assert result.tzinfo is not None

    def test_naive_string_gets_utc(self):
        result = _parse_datetime("2026-03-02T12:00:00")
        assert result is not None
        assert result.tzinfo == UTC

    def test_datetime_object(self):
        dt = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)
        result = _parse_datetime(dt)
        assert result == dt

    def test_naive_datetime_gets_utc(self):
        dt = datetime(2026, 3, 2, 12, 0)  # noqa: DTZ001
        result = _parse_datetime(dt)
        assert result is not None
        assert result.tzinfo == UTC

    def test_empty_string(self):
        assert _parse_datetime("") is None

    def test_invalid_string(self):
        assert _parse_datetime("not-a-date") is None


class TestDisplayCalendar:
    """Test display_calendar function."""

    def test_no_content_shows_empty_message(self, tmp_path, capsys):
        """Shows empty message when no content exists."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        video_dir = tmp_path / "video"

        display_calendar(
            weeks=1,
            console=Console(width=200, no_color=True),
            content_dir=content_dir,
            video_dir=video_dir,
        )

        captured = capsys.readouterr()
        assert "No content" in captured.out
        assert "just generate" in captured.out

    def test_shows_content_table(self, tmp_path, capsys):
        """Shows table with content items."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        video_dir = tmp_path / "video"

        now = datetime.now(tz=UTC)
        (content_dir / "piece1.yaml").write_text(
            yaml.dump(
                {
                    "piece_id": "abc12345",
                    "product": "pilaster",
                    "platform": "linkedin",
                    "content_type": "tutorial",
                    "topic": "Test tutorial post",
                    "status": "pending_review",
                    "generated_at": now.isoformat(),
                }
            )
        )

        display_calendar(
            weeks=1,
            console=Console(width=200, no_color=True),
            content_dir=content_dir,
            video_dir=video_dir,
        )

        captured = capsys.readouterr()
        assert "abc12345" in captured.out
        assert "pilaster" in captured.out
        assert "linkedin" in captured.out
        assert "tutorial" in captured.out

    def test_mixed_statuses(self, tmp_path, capsys):
        """Shows items with different statuses."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        video_dir = tmp_path / "video"

        now = datetime.now(tz=UTC)
        for i, status in enumerate(["pending_review", "approved", "published", "rejected"]):
            (content_dir / f"piece{i}.yaml").write_text(
                yaml.dump(
                    {
                        "piece_id": f"id{i:06d}",
                        "product": "pilaster",
                        "platform": "linkedin",
                        "content_type": "tutorial",
                        "topic": f"Topic {status}",
                        "status": status,
                        "generated_at": now.isoformat(),
                    }
                )
            )

        display_calendar(
            weeks=1,
            console=Console(width=200, no_color=True),
            content_dir=content_dir,
            video_dir=video_dir,
        )

        captured = capsys.readouterr()
        assert "pending_review" in captured.out
        assert "approved" in captured.out
        assert "published" in captured.out
        assert "rejected" in captured.out
        assert "Pipeline Summary" in captured.out

    def test_filters_old_content(self, tmp_path, capsys):
        """Content older than the time window is excluded from table."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        video_dir = tmp_path / "video"

        old_date = datetime.now(tz=UTC) - timedelta(weeks=3)
        (content_dir / "old.yaml").write_text(
            yaml.dump(
                {
                    "piece_id": "old12345",
                    "product": "pilaster",
                    "platform": "linkedin",
                    "content_type": "tutorial",
                    "topic": "Old topic",
                    "status": "published",
                    "generated_at": old_date.isoformat(),
                }
            )
        )

        display_calendar(
            weeks=1,
            console=Console(width=200, no_color=True),
            content_dir=content_dir,
            video_dir=video_dir,
        )

        captured = capsys.readouterr()
        assert "No content in the past 1 week" in captured.out

    def test_includes_video_queue(self, tmp_path, capsys):
        """Includes items from video queue."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        video_dir = tmp_path / "video"
        video_dir.mkdir()

        now = datetime.now(tz=UTC)
        (video_dir / "vid1.yaml").write_text(
            yaml.dump(
                {
                    "piece_id": "vid12345",
                    "product": "genpeli",
                    "platform": "tiktok",
                    "content_type": "video_reel",
                    "topic": "Video demo",
                    "status": "pending_review",
                    "generated_at": now.isoformat(),
                }
            )
        )

        display_calendar(
            weeks=1,
            console=Console(width=200, no_color=True),
            content_dir=content_dir,
            video_dir=video_dir,
        )

        captured = capsys.readouterr()
        assert "vid12345" in captured.out
        assert "video" in captured.out


class TestShowSummary:
    """Test _show_summary function."""

    def test_empty_pipeline(self, capsys):
        console = Console(no_color=True)
        _show_summary(console, [])
        captured = capsys.readouterr()
        assert "Pipeline empty" in captured.out

    def test_counts_statuses(self, capsys):
        console = Console(no_color=True)
        items = [
            {"status": "pending_review"},
            {"status": "pending_review"},
            {"status": "approved"},
            {"status": "published"},
            {"status": "published"},
            {"status": "published"},
            {"status": "rejected"},
        ]
        _show_summary(console, items)
        captured = capsys.readouterr()
        assert "Pending review: 2" in captured.out
        assert "Approved:       1" in captured.out
        assert "Published:      3" in captured.out
        assert "Rejected:       1" in captured.out
        assert "Total:             7" in captured.out

    def test_ignores_unknown_status(self, capsys):
        console = Console(no_color=True)
        items = [
            {"status": "pending_review"},
            {"status": "unknown_status"},
        ]
        _show_summary(console, items)
        captured = capsys.readouterr()
        assert "Pending review: 1" in captured.out
        assert "Total:             1" in captured.out


class TestMain:
    """Test CLI entry point."""

    def test_default_weeks(self):
        with patch("holus.agents.marketing.calendar_view.display_calendar") as mock_display:
            with patch("sys.argv", ["calendar_view"]):
                from holus.agents.marketing.calendar_view import main

                main()
            mock_display.assert_called_once_with(weeks=1)

    def test_custom_weeks(self):
        with patch("holus.agents.marketing.calendar_view.display_calendar") as mock_display:
            with patch("sys.argv", ["calendar_view", "--weeks", "4"]):
                from holus.agents.marketing.calendar_view import main

                main()
            mock_display.assert_called_once_with(weeks=4)

    def test_all_flag(self):
        with patch("holus.agents.marketing.calendar_view.display_calendar") as mock_display:
            with patch("sys.argv", ["calendar_view", "--all"]):
                from holus.agents.marketing.calendar_view import main

                main()
            mock_display.assert_called_once_with(weeks=520)
