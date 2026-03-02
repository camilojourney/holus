"""CLI for reviewing and approving social media content."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .content_queue import QueuedContent, approve, list_pending, reject
from .models import ContentDecision, ContentType, GeneratedPiece, Platform
from .quality_score import PLATFORM_CHAR_LIMITS, QualityResult, score_content

console = Console()


def _queued_to_generated(content: QueuedContent) -> GeneratedPiece:
    """Convert a QueuedContent to GeneratedPiece for quality scoring."""
    try:
        platform = Platform(content.platform)
    except ValueError:
        platform = Platform.LINKEDIN

    try:
        content_type = ContentType(content.content_type)
    except ValueError:
        content_type = ContentType.TUTORIAL

    decision = ContentDecision(
        product=content.product,
        platform=platform,
        content_type=content_type,
        topic=content.topic,
        reasoning=content.reasoning,
    )
    return GeneratedPiece(
        piece_id=content.piece_id,
        decision=decision,
        text=content.text,
        platform=platform,
        generated_at=content.generated_at,
        model_used="unknown",
        status=content.status,
    )


def _score_color(score: int) -> str:
    """Return rich color tag for a quality score."""
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    return "red"


def _render_quality_panel(result: QualityResult, text: str, platform: Platform) -> Panel:
    """Build a rich Panel showing quality score breakdown."""
    color = _score_color(result.score)
    badge = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"

    lines: list[str] = []
    lines.append(f"Score: [{color}]{result.score}/100[/{color}]  {badge}")
    lines.append("")

    # Character count vs limit
    char_limit = PLATFORM_CHAR_LIMITS.get(platform)
    char_count = len(text)
    if char_limit:
        ratio = min(char_count / char_limit, 1.0)
        bar_width = 20
        filled = int(ratio * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        status = "OK" if char_count <= char_limit else "OVER"
        bar_color = "green" if char_count <= char_limit else "red"
        lines.append(
            f"Chars: [{bar_color}]{bar}[/{bar_color}] {char_count}/{char_limit} ({status})"
        )
    else:
        lines.append(f"Chars: {char_count} (no limit for {platform.value})")

    # Violations
    if result.violations:
        lines.append("")
        lines.append(f"[yellow]Violations ({len(result.violations)}):[/yellow]")
        for v in result.violations:
            lines.append(f"  -{v.penalty}  {v.message}")
    else:
        lines.append("")
        lines.append("[green]No violations found.[/green]")

    return Panel(
        "\n".join(lines),
        title="[cyan]Quality Score[/cyan]",
        border_style="dim",
    )


def display_pending() -> None:
    """Display all pending content pieces in a formatted table."""
    pending = list_pending()

    if not pending:
        console.print("[yellow]No pending content to review.[/yellow]")
        return

    table = Table(title="Pending Content for Review", show_lines=True)
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Product", style="magenta")
    table.add_column("Platform", style="blue")
    table.add_column("Type", style="green")
    table.add_column("Score", justify="right")
    table.add_column("Topic", style="yellow")
    table.add_column("Generated", style="dim")

    for content in pending:
        piece = _queued_to_generated(content)
        result = score_content(piece)
        color = _score_color(result.score)
        score_str = f"[{color}]{result.score}[/{color}]"

        table.add_row(
            content.piece_id,
            content.product,
            content.platform,
            content.content_type,
            score_str,
            content.topic,
            content.generated_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
    console.print("\n[dim]Use --show <id> to see full content[/dim]")
    console.print("[dim]Use --approve <id> to approve for publishing[/dim]")
    console.print("[dim]Use --reject <id> to reject[/dim]")


def show_content(piece_id: str) -> None:
    """Display full content for a specific piece.

    Args:
        piece_id: ID of the content piece to show
    """
    pending = list_pending()
    content = next((c for c in pending if c.piece_id == piece_id), None)

    if not content:
        console.print(f"[red]Content piece {piece_id} not found or not pending.[/red]")
        sys.exit(1)

    # Header
    header = f"""
Product: {content.product}
Platform: {content.platform}
Type: {content.content_type}
Topic: {content.topic}
Generated: {content.generated_at.strftime("%Y-%m-%d %H:%M")}
"""

    panel = Panel(
        content.text,
        title=f"[cyan]Content: {piece_id}[/cyan]",
        subtitle=f"[dim]{len(content.text)} characters[/dim]",
        border_style="blue",
    )

    console.print(header.strip())
    console.print(panel)

    # Quality score
    piece = _queued_to_generated(content)
    result = score_content(piece)
    console.print(_render_quality_panel(result, content.text, piece.platform))

    console.print(f"\n[yellow]Reasoning:[/yellow] {content.reasoning}\n")

    # Actions
    console.print("[dim]Actions:[/dim]")
    console.print(f"  just approve-content {piece_id}")
    console.print(f'  just reject-content {piece_id} "reason here"')


def approve_content(piece_id: str) -> None:
    """Approve a content piece for publishing.

    Args:
        piece_id: ID of the content piece to approve
    """
    try:
        approve(piece_id)
        console.print(f"[green]✓ Approved content {piece_id}[/green]")
        console.print("[dim]Run 'just publish-approved' to publish all approved content[/dim]")
    except FileNotFoundError:
        console.print(f"[red]Content piece {piece_id} not found.[/red]")
        sys.exit(1)


def reject_content(piece_id: str, reason: str) -> None:
    """Reject a content piece.

    Args:
        piece_id: ID of the content piece to reject
        reason: Reason for rejection
    """
    try:
        reject(piece_id, reason)
        console.print(f"[red]✗ Rejected content {piece_id}[/red]")
        if reason:
            console.print(f"[dim]Reason: {reason}[/dim]")
    except FileNotFoundError:
        console.print(f"[red]Content piece {piece_id} not found.[/red]")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Review social media content")
    parser.add_argument("--show", metavar="ID", help="Show full content for a piece")
    parser.add_argument("--approve", metavar="ID", help="Approve a content piece")
    parser.add_argument("--reject", metavar="ID", help="Reject a content piece")
    parser.add_argument("--reason", default="", help="Reason for rejection")

    args = parser.parse_args()

    if args.show:
        show_content(args.show)
    elif args.approve:
        approve_content(args.approve)
    elif args.reject:
        reject_content(args.reject, args.reason)
    else:
        display_pending()


if __name__ == "__main__":
    main()
