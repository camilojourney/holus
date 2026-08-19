"""Record publish intents for approved content; external delivery is contained.

Supports --dry-run to preview what would be processed without recording intents.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from holus.api.models import ContentPublishRequest
from holus.api.routes.content import publish_content
from holus.integrations.holus_social_api import EXTERNAL_DELIVERY_CONTAINED_STATUS
from holus.integrations.social_media import PLATFORM_CHAR_LIMITS

from .content_queue import list_approved

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

    console.print(
        "\n[dim]External delivery is currently contained; run [bold]just publish-approved[/bold] to record local intents for review. No external posting occurs.[/dim]"
    )


async def publish_all() -> None:
    """Publish approved content through the guarded content API boundary."""
    approved = list_approved()
    if not approved:
        console.print("[yellow]No approved content to publish.[/yellow]")
        return

    console.print(f"[cyan]Found {len(approved)} approved content pieces[/cyan]\n")

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
                if not content.review_decision_id or not content.content_revision:
                    raise ValueError("APPROVAL_REQUIRED")
                result = await publish_content(
                    content.piece_id,
                    ContentPublishRequest(expected_revision=content.content_revision),
                )
                if result.status == EXTERNAL_DELIVERY_CONTAINED_STATUS:
                    console.print(
                        f"[yellow]! Contained {content.piece_id} to "
                        f"{content.platform}; no external delivery attempted[/yellow]"
                    )
                else:
                    console.print(
                        f"[green]v Published {content.piece_id} to "
                        f"{content.platform} (id: {result.publish_id})[/green]"
                    )
            except Exception as exc:
                console.print(f"[red]x Error publishing {content.piece_id}: {exc}[/red]")
            progress.remove_task(task)

    console.print(
        "\n[cyan]Contained processing complete — intents recorded locally, no external delivery.[/cyan]"
    )


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
