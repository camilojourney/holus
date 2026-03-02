"""Publish all approved social media content via the social-media-automatization API."""

from __future__ import annotations

import asyncio
import os
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from holus.integrations.social_media import PublishRequest, SocialMediaClient

from .content_queue import list_approved, mark_published

console = Console()


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
    try:
        asyncio.run(publish_all())
    except KeyboardInterrupt:
        console.print("\n[yellow]Publishing cancelled by user.[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
