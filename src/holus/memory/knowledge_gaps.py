"""Knowledge gap detection: agents file requests when information is missing.

When an agent encounters a decision where knowledge is insufficient, it files
a "knowledge gap request" as a markdown file in
``.self-improvement/knowledge/requests/``.  The manager agent reads these
during the weekly learning cycle, prioritizes them, and either researches
the answer or delegates to a research agent.

Spec reference: 012-knowledge-learning.md SPEC-004
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_REQUESTS_DIR = Path(".self-improvement/knowledge/requests")


@dataclass(frozen=True)
class KnowledgeGap:
    """A parsed knowledge gap request."""

    path: Path
    filed_by: str
    priority: str
    related_topic: str
    filed_on: str
    what_i_need: str
    why_i_need_it: str
    is_resolved: bool


def _slugify(text: str, max_len: int = 50) -> str:
    """Turn a short description into a filename-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len]


def file_knowledge_gap(
    filed_by: str,
    what_i_need: str,
    why_i_need_it: str,
    *,
    priority: str = "medium",
    related_topic: str = "",
    requests_dir: Path = DEFAULT_REQUESTS_DIR,
) -> Path:
    """File a knowledge gap request for expert agents to resolve.

    Creates a markdown file in the requests directory that the manager agent
    will pick up during the weekly learning cycle.

    Args:
        filed_by: Agent or person filing the request.
        what_i_need: Description of the missing knowledge.
        why_i_need_it: Why this knowledge is needed (decision context).
        priority: ``"low"`` | ``"medium"`` | ``"high"`` | ``"critical"``.
        related_topic: Knowledge topic this relates to (e.g. ``"platforms"``).
        requests_dir: Override for the requests directory (useful in tests).

    Returns:
        Path to the created request file.
    """
    requests_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(what_i_need)
    today = datetime.now(UTC).date().isoformat()
    filename = f"{today}-{slug}.md"
    path = requests_dir / filename

    # Handle duplicate slugs on the same day
    counter = 2
    while path.exists():
        filename = f"{today}-{slug}-{counter}.md"
        path = requests_dir / filename
        counter += 1

    content = f"""# Knowledge Gap Request

**Filed by:** {filed_by}
**Priority:** {priority}
**Related topic:** {related_topic}
**Filed on:** {today}

## What I Need to Know

{what_i_need}

## Why I Need It

{why_i_need_it}

## Status

- [ ] Researched
- [ ] Written to knowledge file
- [ ] Request closed
"""
    path.write_text(content)
    logger.info(
        "Knowledge gap filed: %s (priority=%s, by=%s)",
        path.name,
        priority,
        filed_by,
    )
    return path


def _parse_gap_file(path: Path) -> KnowledgeGap | None:
    """Parse a knowledge gap markdown file into a KnowledgeGap."""
    try:
        text = path.read_text()
    except OSError:
        logger.warning("Cannot read knowledge gap file: %s", path)
        return None

    def _extract(label: str) -> str:
        match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", text)
        return match.group(1).strip() if match else ""

    # Extract sections
    what_match = re.search(
        r"## What I Need to Know\s*\n(.*?)(?=\n## |\Z)",
        text,
        re.DOTALL,
    )
    why_match = re.search(
        r"## Why I Need It\s*\n(.*?)(?=\n## |\Z)",
        text,
        re.DOTALL,
    )

    # Check if all three status checkboxes are checked
    is_resolved = text.count("[x]") >= 3

    return KnowledgeGap(
        path=path,
        filed_by=_extract("Filed by"),
        priority=_extract("Priority"),
        related_topic=_extract("Related topic"),
        filed_on=_extract("Filed on"),
        what_i_need=what_match.group(1).strip() if what_match else "",
        why_i_need_it=why_match.group(1).strip() if why_match else "",
        is_resolved=is_resolved,
    )


def list_open_gaps(
    *,
    requests_dir: Path = DEFAULT_REQUESTS_DIR,
    priority: str | None = None,
) -> list[KnowledgeGap]:
    """List all unresolved knowledge gap requests.

    Args:
        requests_dir: Override for the requests directory.
        priority: Filter by priority level (optional).

    Returns:
        List of open (unresolved) knowledge gaps, sorted by priority then date.
    """
    if not requests_dir.exists():
        return []

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps: list[KnowledgeGap] = []

    for path in sorted(requests_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        gap = _parse_gap_file(path)
        if gap is None:
            continue
        if gap.is_resolved:
            continue
        if priority and gap.priority != priority:
            continue
        gaps.append(gap)

    gaps.sort(key=lambda g: (priority_order.get(g.priority, 99), g.filed_on))
    return gaps


def resolve_gap(
    path: Path,
) -> bool:
    """Mark a knowledge gap as resolved by checking all status boxes.

    Args:
        path: Path to the knowledge gap request file.

    Returns:
        True if the file was updated, False if the file doesn't exist.
    """
    if not path.exists():
        logger.warning("Cannot resolve gap — file not found: %s", path)
        return False

    text = path.read_text()
    updated = text.replace("- [ ] Researched", "- [x] Researched")
    updated = updated.replace("- [ ] Written to knowledge file", "- [x] Written to knowledge file")
    updated = updated.replace("- [ ] Request closed", "- [x] Request closed")
    path.write_text(updated)

    logger.info("Knowledge gap resolved: %s", path.name)
    return True
