"""Weekly content calendar view — shows content pipeline status."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

QUEUE_DIR = Path("data/content-queue")
VIDEO_QUEUE_DIR = Path("data/video-queue")

STATUS_STYLE: dict[str, tuple[str, str]] = {
    "pending_review": ("yellow", "\u23f3"),
    "approved": ("green", "\u2713"),
    "published": ("blue", "\U0001f4e4"),
    "rejected": ("red", "\u2717"),
}


def list_all(queue_dir: Path = QUEUE_DIR) -> list[dict[str, Any]]:
    """Load all content pieces from a queue directory regardless of status."""
    if not queue_dir.exists():
        return []

    items: list[dict[str, Any]] = []
    for file_path in sorted(queue_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(file_path.read_text())
            if data:
                items.append(data)
        except Exception:
            continue

    return items


def _parse_datetime(value: str | datetime) -> datetime | None:
    """Parse a datetime from string or datetime, returning UTC-aware datetime."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def display_calendar(
    weeks: int = 1,
    *,
    console: Console | None = None,
    content_dir: Path = QUEUE_DIR,
    video_dir: Path = VIDEO_QUEUE_DIR,
) -> None:
    """Display content calendar for the past N weeks."""
    if console is None:
        console = Console()

    now = datetime.now(tz=UTC)
    cutoff = now - timedelta(weeks=weeks)

    content = list_all(content_dir)
    videos = list_all(video_dir)

    for item in content:
        item["_source"] = "text"
    for item in videos:
        item["_source"] = "video"

    all_items = content + videos

    filtered: list[dict[str, Any]] = []
    for item in all_items:
        dt = _parse_datetime(item.get("generated_at", ""))
        if dt and dt >= cutoff:
            item["_dt"] = dt
            filtered.append(item)

    filtered.sort(key=lambda x: x.get("_dt", now), reverse=True)

    if not filtered:
        console.print(f"[yellow]No content in the past {weeks} week(s).[/yellow]")
        console.print("[dim]Run 'just generate' to create content.[/dim]")
        _show_summary(console, all_items)
        return

    table = Table(title=f"Content Calendar \u2014 Past {weeks} Week(s)", show_lines=True)
    table.add_column("Date", style="dim", width=12)
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Status", width=16)
    table.add_column("Type", style="magenta", width=10)
    table.add_column("Product", style="blue")
    table.add_column("Platform", style="green")
    table.add_column("Topic", style="yellow", max_width=40)

    for item in filtered:
        item_dt = item.get("_dt", now)
        status = item.get("status", "unknown")
        style, icon = STATUS_STYLE.get(status, ("dim", "?"))

        content_type = item.get("content_type", "")
        if item.get("_source") == "video":
            content_type = "video"

        topic = item.get("topic", "")
        if len(topic) > 40:
            topic = topic[:37] + "..."

        table.add_row(
            item_dt.strftime("%Y-%m-%d"),
            str(item.get("piece_id", "?"))[:8],
            f"[{style}]{icon} {status}[/{style}]",
            content_type,
            item.get("product", "?"),
            item.get("platform", "?"),
            topic,
        )

    console.print(table)
    _show_summary(console, all_items)


def _show_summary(console: Console, all_items: list[dict[str, Any]]) -> None:
    """Show pipeline summary counts."""
    counts: dict[str, int] = {
        "pending_review": 0,
        "approved": 0,
        "published": 0,
        "rejected": 0,
    }
    for item in all_items:
        status = item.get("status", "unknown")
        if status in counts:
            counts[status] += 1

    total = sum(counts.values())
    if total == 0:
        console.print("\n[dim]Pipeline empty. Run 'just generate' to create content.[/dim]")
        return

    console.print("\n[bold]Pipeline Summary (all time):[/bold]")
    console.print(f"  \u23f3 Pending review: {counts['pending_review']}")
    console.print(f"  \u2713 Approved:       {counts['approved']}")
    console.print(f"  \U0001f4e4 Published:      {counts['published']}")
    console.print(f"  \u2717 Rejected:       {counts['rejected']}")
    console.print(f"  Total:             {total}")


def main() -> None:
    """CLI entry point for content calendar."""
    parser = argparse.ArgumentParser(description="Content calendar view")
    parser.add_argument(
        "--weeks", type=int, default=1, help="Number of weeks to show (default: 1)"
    )
    parser.add_argument(
        "--all", action="store_true", help="Show all content regardless of date"
    )

    args = parser.parse_args()

    if args.all:
        display_calendar(weeks=520)
    else:
        display_calendar(weeks=args.weeks)


if __name__ == "__main__":
    main()
