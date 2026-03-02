"""Publish all approved social media content via the social-media-automatization API.

Supports --dry-run to preview what would be posted without actually publishing.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from holus.integrations.social_media import (
    PLATFORM_CHAR_LIMITS,
    PublishRequest,
    SocialMediaClient,
)

from .content_queue import list_approved, mark_published

console = Console()


def dry_run() -> None:
    """Show what would be published without actually posting."""
    approved = list_approved()
    if not approved:
        console.print("[yellow]No approved content to publish.[/yellow]")
        return

    console.print(f"[cyan]DRY RUN — {len(approved)} approved piece(s)[/cyan]\n")

    table = Table(title="Content Preview")
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Platform", style="green", width=12)
    table.add_column("Chars", justify="right", width=8)
    table.add_column("Limit", justify="right", width=8)
    table.add_column("Status", width=8)
    table.add_column("Preview", max_width=60)

    warnings: list[str] = []
    for content in approved:
        char_count = len(content.text)
        limit = PLATFORM_CHAR_LIMITS.get(content.platform.lower(), 0)
        over = char_count > limit if limit else False
        status = "[red]OVER[/red]" if over else "[green]OK[/green]"

        if over:
            warnings.append(
                f"{content.piece_id}: {content.platform} — {char_count} chars exceeds {limit} limit"
            )

        # Truncate preview to first 55 chars, replace newlines
        preview = content.text.replace("\n", " ")[:55]
        if len(content.text) > 55:
            preview += "..."

        table.add_row(
            content.piece_id,
            content.platform,
            str(char_count),
            str(limit) if limit else "n/a",
            status,
            preview,
        )

    console.print(table)

    if warnings:
        console.print("\n[red]Warnings:[/red]")
        for w in warnings:
            console.print(f"  [red]x {w}[/red]")
    else:
        console.print("\n[green]All content within platform limits.[/green]")

    console.print("\n[dim]Run [bold]just publish-approved[/bold] to publish for real.[/dim]")


async def publish_all() -> None:
    """Publish all approved content pieces via the social-media API."""
    api_key = os.getenv("POSTING_API_KEY", "")
    if not api_key:
        console.print("[red]ERROR: POSTING_API_KEY not set in environment[/red]")
        console.print("[dim]Set it in .env or export POSTING_API_KEY=your_key[/dim]")
        sys.exit(1)

    base_url = os.getenv("SOCIAL_MEDIA_API_BASE_URL", "http://localhost:8000")

    # Get approved content
    approved = list_approved()
    if not approved:
        console.print("[yellow]No approved content to publish.[/yellow]")
        return

    console.print(f"[cyan]Found {len(approved)} approved content pieces[/cyan]\n")

    async with SocialMediaClient(base_url=base_url, api_key=api_key) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for content in approved:
                task = progress.add_task(
                    f"Publishing {content.piece_id} to {content.platform}...",
                    total=None,
                )

                try:
                    request = PublishRequest(
                        content=content.text,
                        platforms=[content.platform],
                        style="raw",  # Content is already written by the agent
                    )

                    result = await client.publish(request)

                    if result.failed_targets:
                        for target in result.failed_targets:
                            console.print(
                                f"[red]x Failed {content.piece_id} on "
                                f"{target.platform}: {target.error}[/red]"
                            )
                    else:
                        console.print(
                            f"[green]v Published {content.piece_id} to "
                            f"{content.platform} (id: {result.publish_id})[/green]"
                        )
                        mark_published(content.piece_id, result.publish_id)

                except Exception as e:
                    console.print(f"[red]x Error publishing {content.piece_id}: {e}[/red]")

                progress.remove_task(task)

    console.print("\n[cyan]Publishing complete![/cyan]")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Publish approved content")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be published without actually posting",
    )
    args = parser.parse_args()

    try:
        if args.dry_run:
            dry_run()
        else:
            asyncio.run(publish_all())
    except KeyboardInterrupt:
        console.print("\n[yellow]Publishing cancelled by user.[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
