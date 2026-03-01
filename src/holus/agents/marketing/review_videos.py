"""CLI for reviewing and approving processed videos."""

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .video_queue import approve_video, list_pending_videos, reject_video

console = Console()


def display_pending() -> None:
    """Display all pending videos in a formatted table."""
    pending = list_pending_videos()

    if not pending:
        console.print("[yellow]No pending videos to review.[/yellow]")
        return

    table = Table(title="Pending Videos for Review", show_lines=True)
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Product", style="magenta")
    table.add_column("Platform", style="blue")
    table.add_column("Type", style="green")
    table.add_column("Topic", style="yellow")
    table.add_column("Preview URL", style="underline blue", max_width=50)
    table.add_column("Generated", style="dim")

    for video in pending:
        table.add_row(
            video.piece_id,
            video.product,
            video.platform,
            video.content_type,
            video.topic,
            video.preview_url,
            video.generated_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
    console.print("\n[dim]Use --show <id> to see full video details[/dim]")
    console.print("[dim]Use --approve <id> to approve for delivery[/dim]")
    console.print("[dim]Use --reject <id> to reject[/dim]")


def show_video(piece_id: str) -> None:
    """Display full details for a specific video.

    Args:
        piece_id: ID of the video piece to show.
    """
    pending = list_pending_videos()
    video = next((v for v in pending if v.piece_id == piece_id), None)

    if not video:
        console.print(f"[red]Video piece {piece_id} not found or not pending.[/red]")
        sys.exit(1)

    header = f"""\
Product: {video.product}
Platform: {video.platform}
Type: {video.content_type}
Topic: {video.topic}
Job ID: {video.job_id}
Generated: {video.generated_at.strftime("%Y-%m-%d %H:%M")}"""

    panel = Panel(
        video.preview_url,
        title=f"[cyan]Video: {piece_id}[/cyan]",
        subtitle="[dim]Preview URL[/dim]",
        border_style="blue",
    )

    console.print(header)
    console.print(panel)
    console.print(f"\n[yellow]Reasoning:[/yellow] {video.reasoning}\n")

    console.print("[dim]Actions:[/dim]")
    console.print(f"  just approve-video {piece_id}")
    console.print(f'  just reject-video {piece_id} "reason here"')


def approve_video_cli(piece_id: str) -> None:
    """Approve a video for Genpeli delivery.

    Args:
        piece_id: ID of the video piece to approve.
    """
    try:
        approve_video(piece_id)
        console.print(f"[green]✓ Approved video {piece_id}[/green]")
        console.print("[dim]Video will be delivered via Genpeli pipeline[/dim]")
    except FileNotFoundError:
        console.print(f"[red]Video piece {piece_id} not found.[/red]")
        sys.exit(1)


def reject_video_cli(piece_id: str, reason: str) -> None:
    """Reject a video.

    Args:
        piece_id: ID of the video piece to reject.
        reason: Reason for rejection.
    """
    try:
        reject_video(piece_id, reason)
        console.print(f"[red]✗ Rejected video {piece_id}[/red]")
        if reason:
            console.print(f"[dim]Reason: {reason}[/dim]")
    except FileNotFoundError:
        console.print(f"[red]Video piece {piece_id} not found.[/red]")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Review processed videos")
    parser.add_argument("--show", metavar="ID", help="Show full details for a video")
    parser.add_argument("--approve", metavar="ID", help="Approve a video for delivery")
    parser.add_argument("--reject", metavar="ID", help="Reject a video")
    parser.add_argument("--reason", default="", help="Reason for rejection")

    args = parser.parse_args()

    if args.show:
        show_video(args.show)
    elif args.approve:
        approve_video_cli(args.approve)
    elif args.reject:
        reject_video_cli(args.reject, args.reason)
    else:
        display_pending()


if __name__ == "__main__":
    main()
