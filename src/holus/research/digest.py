"""Markdown digest rendering for Research Radar."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from holus.research.models import RawResearchItem, ResearchScore


def render_digest(entries: list[tuple[RawResearchItem, ResearchScore]], digest_date: date) -> str:
    lines = [
        f"# Research Radar Digest — {digest_date.isoformat()}",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "No new research items crossed the reading threshold.",
                "",
            ]
        )
        return "\n".join(lines)

    for index, (item, score) in enumerate(entries, start=1):
        products = ", ".join(score.matched_products) if score.matched_products else "portfolio"
        topics = ", ".join(score.topics) if score.topics else "general AI"
        lines.extend(
            [
                f"## {index}. [{item.title}]({item.url})",
                "",
                f"- Source: {item.source}",
                f"- Products: {products}",
                f"- Topics: {topics}",
                f"- Read priority: {score.should_read:.2f}",
                f"- Why it matters: {score.why_it_matters}",
                f"- Key idea: {score.key_idea}",
                "",
            ]
        )
    return "\n".join(lines)


def write_digest(
    entries: list[tuple[RawResearchItem, ResearchScore]],
    *,
    research_dir: Path,
    digest_date: date,
) -> Path:
    research_dir.mkdir(parents=True, exist_ok=True)
    path = research_dir / f"digest-{digest_date.isoformat()}.md"
    path.write_text(render_digest(entries, digest_date), encoding="utf-8")
    return path
