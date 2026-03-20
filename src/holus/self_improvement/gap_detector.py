"""Gap detection — identify missing capabilities and knowledge from failure patterns.

Two levels of detection:
1. Per-failure classification (in reflexion): Opus classifies each failure as
   PROMPT_ISSUE / CAPABILITY_GAP / DATA_GAP / QUALITY_ISSUE
2. Pattern aggregation (in learning loop): statistical detection from trajectory

Gap requests are written to:
- capability-requests/  → missing tools (human resolves via /code)
- knowledge/requests/   → missing data (expert agent auto-resolves)

Usage::

    from holus.self_improvement.gap_detector import detect_gaps, classify_failure

    # Per-failure classification
    failure_class = classify_failure(task, output, judge_feedback)
    # → "capability_gap" | "data_gap" | "prompt_issue" | "quality_issue"

    # Pattern aggregation (weekly, from learning loop)
    gaps = detect_gaps(trajectory_entries)
    # → [{"type": "capability_gap", "name": "video_rendering", "evidence": 5, ...}]
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CAPABILITY_REQUESTS_DIR = Path(".self-improvement/capability-requests")
KNOWLEDGE_REQUESTS_DIR = Path(".self-improvement/knowledge/requests")

# Keywords that indicate capability gaps (not prompt quality issues)
CAPABILITY_KEYWORDS = [
    "no tool", "cannot", "unable to", "not supported", "missing",
    "no api", "not implemented", "no integration", "no mcp",
    "not available", "blocked", "no access",
]

# Keywords that indicate data/knowledge gaps
DATA_KEYWORDS = [
    "don't know", "no data", "no information", "unclear",
    "need context", "missing knowledge", "no profile",
    "no examples", "no benchmark", "no reference",
]


def classify_failure(
    task: str,
    output: str,
    judge_feedback: str,
) -> str:
    """Classify a failure into one of 4 categories based on judge feedback.

    Returns: "capability_gap" | "data_gap" | "prompt_issue" | "quality_issue"
    """
    feedback_lower = (judge_feedback or "").lower()
    output_lower = (output or "").lower()
    combined = feedback_lower + " " + output_lower

    # Check for capability gaps first (most specific)
    if any(kw in combined for kw in CAPABILITY_KEYWORDS):
        return "capability_gap"

    # Check for data/knowledge gaps
    if any(kw in combined for kw in DATA_KEYWORDS):
        return "data_gap"

    # Check for prompt issues (instructions were wrong/unclear)
    prompt_indicators = ["off-topic", "wrong format", "didn't follow", "ignored instruction"]
    if any(kw in combined for kw in prompt_indicators):
        return "prompt_issue"

    # Default: quality issue (output was produced but scored poorly)
    return "quality_issue"


def detect_gaps(
    trajectory_entries: list[dict[str, Any]],
    *,
    min_failures: int = 3,
) -> list[dict[str, Any]]:
    """Detect capability and data gaps from trajectory patterns.

    Aggregates failures by (platform, content_type) and identifies
    combinations with high failure rates and consistent failure classes.

    Returns list of gap descriptors with evidence counts.
    """
    # Group failures by (platform, content_type, failure_class)
    failure_groups: dict[str, list[dict[str, Any]]] = {}

    for entry in trajectory_entries:
        if entry.get("status") not in ("failure", "error"):
            # Also check for low judge scores as implicit failures
            score = entry.get("judge_score")
            if score is not None and score >= 0.5:
                continue

        metadata = entry.get("metadata", {})
        platform = metadata.get("platform", "unknown")
        content_type = metadata.get("content_type", entry.get("task_type", "unknown"))
        failure_class = metadata.get("failure_class", "quality_issue")

        key = f"{platform}:{content_type}:{failure_class}"
        if key not in failure_groups:
            failure_groups[key] = []
        failure_groups[key].append(entry)

    # Find gaps that exceed the threshold
    gaps: list[dict[str, Any]] = []
    for key, entries in failure_groups.items():
        if len(entries) < min_failures:
            continue

        platform, content_type, failure_class = key.split(":", 2)

        # Extract common feedback themes
        feedbacks = [e.get("judge_feedback", "") for e in entries if e.get("judge_feedback")]
        common_words: Counter[str] = Counter()
        for fb in feedbacks:
            common_words.update(fb.lower().split())
        top_words = [w for w, _ in common_words.most_common(5) if len(w) > 3]

        gaps.append({
            "type": failure_class,
            "platform": platform,
            "content_type": content_type,
            "evidence_count": len(entries),
            "common_feedback": top_words,
            "first_seen": min(e.get("timestamp", "") for e in entries),
            "last_seen": max(e.get("timestamp", "") for e in entries),
        })

    return sorted(gaps, key=lambda g: g["evidence_count"], reverse=True)


def write_gap_request(gap: dict[str, Any]) -> Path:
    """Write a gap request file to the appropriate directory.

    capability_gap → .self-improvement/capability-requests/
    data_gap → .self-improvement/knowledge/requests/
    """
    gap_type = gap["type"]
    platform = gap["platform"]
    content_type = gap["content_type"]
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    slug = f"{platform}-{content_type}".replace("_", "-")

    if gap_type == "capability_gap":
        target_dir = CAPABILITY_REQUESTS_DIR
    elif gap_type == "data_gap":
        target_dir = KNOWLEDGE_REQUESTS_DIR
    else:
        # prompt_issue and quality_issue don't get gap files
        return Path("/dev/null")

    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{date}-{slug}.md"
    path = target_dir / filename

    # Don't overwrite existing gap requests
    if path.exists():
        logger.info("Gap request already exists: %s", path)
        return path

    content = f"""---
status: open
priority: {"high" if gap["evidence_count"] >= 5 else "medium"}
detected_at: {date}
evidence_count: {gap["evidence_count"]}
type: {gap_type}
platform: {platform}
content_type: {content_type}
---

# Gap: {platform.title()} {content_type.replace("_", " ").title()}

**Type:** {gap_type}
**Evidence:** {gap["evidence_count"]} failures between {gap.get("first_seen", "?")[:10]} and {gap.get("last_seen", "?")[:10]}
**Common feedback themes:** {", ".join(gap.get("common_feedback", []))}

## What's Missing

{"A tool or integration is needed to handle this content type on this platform." if gap_type == "capability_gap" else "Knowledge or reference data is needed for this content type."}

## Blocked Content

This gap prevents generating {content_type} content for {platform}.
"""

    path.write_text(content)
    logger.info("Gap request written: %s", path)
    return path
