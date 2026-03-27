"""Humanization pipeline — make AI content sound like Camilo.

Personal context injection: select relevant anecdotes/metrics for prompt injection.

Usage::

    from holus.agents.marketing.humanize import (
        select_personal_context,
        format_personal_context,
    )
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PERSONAL_CONTEXT_PATH = Path("data/personal-context.json")

# ---------------------------------------------------------------------------
# Layer 2 — Personal context injection
# ---------------------------------------------------------------------------


def load_personal_context() -> dict[str, list[dict[str, Any]]]:
    """Load personal-context.json.

    Returns dict with keys like ``anecdotes``, ``metrics``, ``opinions``,
    ``project_facts`` — each mapping to a list of entry dicts.

    Returns empty dict if file is missing or malformed.
    """
    try:
        raw = PERSONAL_CONTEXT_PATH.read_text(encoding="utf-8")
        data: dict[str, list[dict[str, Any]]] = json.loads(raw)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load personal context: %s", exc)
        return {}


def select_personal_context(
    product: str = "",
    topics: list[str] | None = None,
    count: int = 3,
) -> list[dict[str, Any]]:
    """Select 2-3 relevant personal context entries.

    Filters by *product* match and *topic* overlap across all categories
    (anecdotes, metrics, opinions, project_facts).  Random within the
    filtered set so consecutive calls return different entries.

    Returns list of context entry dicts, each containing at least ``text``.
    """
    ctx = load_personal_context()
    if not ctx:
        return []

    # Flatten all categories into a single pool
    pool: list[dict[str, Any]] = []
    for entries in ctx.values():
        if isinstance(entries, list):
            pool.extend(entries)

    if not pool:
        return []

    # --- Filter by product ---
    if product:
        product_lower = product.lower()
        product_filtered = [
            e for e in pool if product_lower in [p.lower() for p in e.get("products", [])]
        ]
        # Fall back to full pool if no product match
        if product_filtered:
            pool = product_filtered

    # --- Filter by topic overlap ---
    if topics:
        topics_lower = {t.lower() for t in topics}
        topic_scored: list[tuple[int, dict[str, Any]]] = []
        for entry in pool:
            entry_topics = {t.lower() for t in entry.get("topics", [])}
            overlap = len(topics_lower & entry_topics)
            if overlap > 0:
                topic_scored.append((overlap, entry))
        if topic_scored:
            # Sort by overlap descending, then shuffle ties
            topic_scored.sort(key=lambda x: x[0], reverse=True)
            pool = [e for _, e in topic_scored]

    # Shuffle and take up to *count*
    selected = list(pool)
    random.shuffle(selected)
    return selected[:count]


def format_personal_context(entries: list[dict[str, Any]]) -> str:
    """Format selected entries for prompt injection.

    Returns a string block that can be inserted into a system prompt, e.g.::

        ## Your Real Experiences (reference these — they're TRUE)

        - You built genpeli's pipeline. One command replaces 4 hours of manual editing.
        - The judge evaluator was broken for 2 months because of a one-line path bug.

        Use at least ONE of these real facts in your post. They make it authentic.
    """
    if not entries:
        return ""

    lines = ["## Your Real Experiences (reference these — they're TRUE)", ""]
    for entry in entries:
        text = entry.get("text", "").strip()
        if text:
            # Truncate to first sentence or 200 chars for brevity in prompts
            short = text[:200].rstrip(".")
            if len(text) > 200:
                short += "..."
            lines.append(f"- {short}")

    lines.append("")
    lines.append("Use at least ONE of these real facts in your post. They make it authentic.")
    return "\n".join(lines)
