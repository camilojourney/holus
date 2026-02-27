"""Publish all approved social media content via Late API."""

import asyncio
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from holus.integrations.late_api import LateAPIClient, PostRequest
from .content_queue import list_approved, mark_published

console = Console()


async def publish_all() -> None:
    """Publish all approved content pieces."""
    # Check for API key
    api_key = os.getenv("LATE_API_KEY")
    if not api_key:
        console.print("[red]ERROR: LATE_API_KEY not set in environment[/red]")
        console.print("[dim]Set it in .env or export LATE_API_KEY=your_key[/dim]")
        sys.exit(1)

    # Get approved content
    approved = list_approved()
    if not approved:
        console.print("[yellow]No approved content to publish.[/yellow]")
        return

    console.print(f"[cyan]Found {len(approved)} approved content pieces[/cyan]\n")

    # Initialize Late API client
    async with LateAPIClient(api_key) as client:
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
                    # Create post request
                    request = PostRequest(
                        text=content.text,
                        platforms=[content.platform],
                        media_urls=[],
                        schedule_time=None,  # Immediate posting
                    )

                    # Publish
                    result = await client.publish(request)

                    # Check for failures
                    if result.failed_platforms:
                        console.print(
                            f"[red]✗ Failed to publish {content.piece_id} to "
                            f"{', '.join(result.failed_platforms)}[/red]"
                        )
                        for platform, error in result.error_details.items():
                            console.print(f"  [dim]{platform}: {error}[/dim]")
                    else:
                        console.print(
                            f"[green]✓ Published {content.piece_id} to "
                            f"{content.platform} (post_id: {result.post_id})[/green]"
                        )
                        mark_published(content.piece_id, result.post_id)

                except Exception as e:
                    console.print(
                        f"[red]✗ Error publishing {content.piece_id}: {e}[/red]"
                    )

                progress.remove_task(task)

    console.print("\n[cyan]Publishing complete![/cyan]")


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(publish_all())
    except KeyboardInterrupt:
        console.print("\n[yellow]Publishing cancelled by user.[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
