"""System Diagnostician - SPEC-036.

Watches the content pipeline from outside.  Reads trajectory patterns,
actual code, agent prompts, and content output to trace quality failures
back to root causes (code bugs, prompt gaps, missing agents/tools).

Produces actionable tasks for the human to implement.

Usage:
    uv run python -m holus.self_improvement.diagnostician
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parents[3]
TRAJECTORY_PATH = REPO_ROOT / ".self-improvement" / "memory" / "trajectory.jsonl"
CONTENT_QUEUE = REPO_ROOT / "data" / "content-queue"
REPORT_DIR = REPO_ROOT / ".self-improvement" / "reports" / "diagnostic"
AGENTS_YAML = REPO_ROOT / "agents" / "AGENTS.yaml"
KNOWLEDGE_DIR = REPO_ROOT / ".self-improvement" / "knowledge" / "current"
NEXT_MD_PATH = REPO_ROOT / ".self-improvement" / "NEXT.md"

# Dimension score thresholds
DIMENSION_FAIL_THRESHOLD = 0.6
SYSTEMIC_FAILURE_MIN = 3  # N failures on same dimension = systemic


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class DiagnosticTask:
    """A single finding with actionable fix."""

    category: str  # CODE_BUG | PROMPT_GAP | MISSING_AGENT | MISSING_TOOL | CONFIG_ISSUE
    description: str
    root_cause: str
    evidence: str
    suggested_fix: str
    priority: str  # P0 | P1 | P2 | P3
    file_ref: str = ""  # file:line reference


@dataclass
class DiagnosticReport:
    """Full diagnostic output."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    entries_analyzed: int = 0
    critical: list[DiagnosticTask] = field(default_factory=list)
    high: list[DiagnosticTask] = field(default_factory=list)
    medium: list[DiagnosticTask] = field(default_factory=list)
    suggestions: list[DiagnosticTask] = field(default_factory=list)

    # Health metrics
    judge_coverage: float = 0.0
    avg_score: float = 0.0
    top_failing_dimension: str = ""
    failure_patterns: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Trajectory reader
# ---------------------------------------------------------------------------


def _load_trajectory(days: int = 30) -> list[dict[str, Any]]:
    """Load trajectory entries from the last N days."""
    if not TRAJECTORY_PATH.exists():
        return []
    cutoff = datetime.now(UTC) - timedelta(days=days)
    entries: list[dict[str, Any]] = []
    for line in TRAJECTORY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Filter to content entries (skip state transitions, builder cycles)
        if "event" in entry and entry["event"] == "transition":
            continue
        ts = entry.get("timestamp", "")
        if not ts:
            continue
        try:
            entry_dt = datetime.fromisoformat(ts)
            if entry_dt.tzinfo is None:
                continue
            if entry_dt < cutoff:
                continue
        except (ValueError, TypeError):
            continue
        entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------


def _check_judge_coverage(entries: list[dict[str, Any]]) -> tuple[float, list[DiagnosticTask]]:
    """Check what % of content pieces actually got evaluated by domain judges."""
    tasks: list[DiagnosticTask] = []
    content_entries = [
        e
        for e in entries
        if e.get("task_type")
        in (
            "content_creation",
            "text_post",
            "carousel_outline",
            "thread",
            "video_script",
            "instagram_caption",
        )
    ]
    if not content_entries:
        return 1.0, tasks

    null_verdicts = [e for e in content_entries if e.get("judge_verdict") is None]
    zero_scores = [
        e
        for e in content_entries
        if e.get("judge_score") == 0.0
        and e.get("judge_feedback", "").startswith("Judge evaluation failed")
    ]

    coverage = 1.0 - (len(null_verdicts) / len(content_entries)) if content_entries else 1.0

    if null_verdicts:
        tasks.append(
            DiagnosticTask(
                category="CODE_BUG",
                description=f"Judge returned null verdict on {len(null_verdicts)}/{len(content_entries)} pieces",
                root_cause="evaluate_with_routing() may have failed silently or wasn't called",
                evidence=f"Pieces with null verdict: {[e.get('metadata', {}).get('piece_id', '?')[:16] for e in null_verdicts[:5]]}",
                suggested_fix="Check that judge.evaluate_with_routing() is called in the content pipeline and registry loads correctly",
                priority="P0" if len(null_verdicts) == len(content_entries) else "P1",
                file_ref="src/holus/self_improvement/judge.py:evaluate_with_routing()",
            )
        )

    if zero_scores:
        tasks.append(
            DiagnosticTask(
                category="CODE_BUG",
                description=f"Judge evaluation failed with JSON parse error on {len(zero_scores)} pieces",
                root_cause="LLM response wasn't valid JSON - _parse_response() failed",
                evidence=f"Sample feedback: {zero_scores[0].get('judge_feedback', '')[:200]}",
                suggested_fix="Check judge prompt instructs JSON-only output; increase retry count or add markdown fence stripping",
                priority="P1",
                file_ref="src/holus/self_improvement/judge.py:_parse_response()",
            )
        )

    return coverage, tasks


def _check_dimension_failures(entries: list[dict[str, Any]]) -> tuple[str, list[DiagnosticTask]]:
    """Find dimensions that consistently score low."""
    tasks: list[DiagnosticTask] = []
    dim_scores: dict[str, list[float]] = {}

    for entry in entries:
        dims = entry.get("metadata", {}).get("dimension_scores", {})
        for dim, score in dims.items():
            if isinstance(score, (int, float)):
                dim_scores.setdefault(dim, []).append(score)

    if not dim_scores:
        return "", tasks

    # Find worst-performing dimensions
    dim_avgs = {
        dim: sum(scores) / len(scores) for dim, scores in dim_scores.items() if len(scores) >= 2
    }

    top_failing = ""
    for dim, avg in sorted(dim_avgs.items(), key=lambda x: x[1]):
        if avg < DIMENSION_FAIL_THRESHOLD:
            fail_count = sum(1 for s in dim_scores[dim] if s < DIMENSION_FAIL_THRESHOLD)
            total = len(dim_scores[dim])

            if fail_count >= SYSTEMIC_FAILURE_MIN:
                tasks.append(
                    DiagnosticTask(
                        category="PROMPT_GAP",
                        description=f"Dimension '{dim}' consistently fails: {fail_count}/{total} below {DIMENSION_FAIL_THRESHOLD}",
                        root_cause=f"Avg score {avg:.2f}. The producing agent's prompt likely doesn't emphasize {dim}",
                        evidence=f"Scores: {[round(s, 2) for s in dim_scores[dim][-10:]]}",
                        suggested_fix=f"Find which agent prompt controls '{dim}' and add explicit instructions for it",
                        priority="P1",
                    )
                )
        if not top_failing:
            top_failing = dim

    if not top_failing and dim_avgs:
        top_failing = min(dim_avgs, key=lambda k: dim_avgs[k])
    return top_failing, tasks


def _check_platform_failures(entries: list[dict[str, Any]]) -> list[DiagnosticTask]:
    """Check if specific platforms consistently fail."""
    tasks: list[DiagnosticTask] = []
    platform_results: dict[str, list[str]] = {}

    for entry in entries:
        platform = entry.get("metadata", {}).get("platform", "")
        verdict = entry.get("judge_verdict")
        if platform and verdict:
            platform_results.setdefault(platform, []).append(verdict)

    for platform, verdicts in platform_results.items():
        fail_count = sum(1 for v in verdicts if v in ("FAIL", "PARTIAL"))
        total = len(verdicts)
        if total >= 3 and fail_count / total > 0.5:
            tasks.append(
                DiagnosticTask(
                    category="PROMPT_GAP",
                    description=f"{platform} content fails {fail_count}/{total} times ({fail_count / total:.0%})",
                    root_cause="Platform-specific repurpose prompt or format instructions may be inadequate",
                    evidence=f"Verdicts: {verdicts[-10:]}",
                    suggested_fix=f"Review repurpose.py PLATFORM_RULES for {platform} and the platform-adapter prompt",
                    priority="P1",
                    file_ref="src/holus/agents/marketing/repurpose.py",
                )
            )

    return tasks


def _check_feedback_loop(entries: list[dict[str, Any]]) -> list[DiagnosticTask]:
    """Check if judge feedback is being used by generators."""
    tasks: list[DiagnosticTask] = []

    # Check if any content entry references prior feedback
    has_feedback_injection = False
    for entry in entries:
        reasoning = entry.get("metadata", {}).get("reasoning", "")
        if "last cycle" in reasoning.lower() or "previous feedback" in reasoning.lower():
            has_feedback_injection = True
            break

    if not has_feedback_injection and len(entries) > 10:
        tasks.append(
            DiagnosticTask(
                category="MISSING_TOOL",
                description="Judge feedback is not fed back to content generators",
                root_cause="No code path loads previous judge feedback during observe/reason phase",
                evidence=f"Checked {len(entries)} entries - none reference prior feedback in reasoning",
                suggested_fix="In marketing agent observe(), load last cycle's judge feedback from trajectory and inject into prompts",
                priority="P1",
                file_ref="src/holus/agents/marketing/agent.py",
            )
        )

    return tasks


def _check_failure_streaks(entries: list[dict[str, Any]]) -> list[DiagnosticTask]:
    """Check for 3+ consecutive failures per agent."""
    tasks: list[DiagnosticTask] = []
    agent_entries: dict[str, list[dict[str, Any]]] = {}

    for entry in entries:
        agent = entry.get("agent_id", "")
        if agent:
            agent_entries.setdefault(agent, []).append(entry)

    for agent, agent_list in agent_entries.items():
        # Sort by timestamp
        agent_list.sort(key=lambda e: e.get("timestamp", ""))
        streak = 0
        max_streak = 0
        for e in agent_list:
            verdict = e.get("judge_verdict", "")
            if verdict in ("FAIL", "PARTIAL"):
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

        if max_streak >= 3:
            tasks.append(
                DiagnosticTask(
                    category="PROMPT_GAP",
                    description=f"Agent '{agent}' has {max_streak}-failure streak",
                    root_cause="Prompt optimizer should auto-trigger but isn't connected to orchestrator",
                    evidence=f"Max consecutive FAIL/PARTIAL: {max_streak}",
                    suggested_fix=f"Auto-trigger PromptOptimizer for agent '{agent}' in improvement_cycle()",
                    priority="P2",
                    file_ref="src/holus/agents/marketing/orchestrator.py",
                )
            )

    return tasks


def _check_content_quality_signals(entries: list[dict[str, Any]]) -> list[DiagnosticTask]:
    """Check for content-level quality patterns from judge feedback."""
    tasks: list[DiagnosticTask] = []
    feedback_themes: Counter[str] = Counter()

    keywords_to_issues = {
        "not formatted as": "FORMAT_MISMATCH",
        "truncat": "TRUNCATION",
        "too long": "LENGTH",
        "generic": "GENERIC_CONTENT",
        "doesn't sound like": "VOICE_DRIFT",
        "no evidence": "MISSING_AUTHORITY",
        "no specific": "MISSING_SPECIFICS",
        "anti-pattern": "AI_SLOP",
    }

    for entry in entries:
        feedback = (entry.get("judge_feedback") or "").lower()
        for keyword, issue in keywords_to_issues.items():
            if keyword in feedback:
                feedback_themes[issue] += 1

    for issue, count in feedback_themes.most_common(5):
        if count >= 2:
            tasks.append(
                DiagnosticTask(
                    category="PROMPT_GAP" if issue != "FORMAT_MISMATCH" else "CODE_BUG",
                    description=f"Recurring feedback theme: {issue} ({count} occurrences)",
                    root_cause=f"Judge feedback mentions '{issue}' pattern across {count} pieces",
                    evidence=f"Frequency: {count} in last 30 days",
                    suggested_fix=f"Search judge_feedback in trajectory for '{issue}' examples, then fix the producing agent/code",
                    priority="P2",
                )
            )

    return tasks


# ---------------------------------------------------------------------------
# Main diagnostic runner
# ---------------------------------------------------------------------------


def run_diagnostic(days: int = 30) -> DiagnosticReport:
    """Run all diagnostic checks and produce a report."""
    entries = _load_trajectory(days)
    report = DiagnosticReport(entries_analyzed=len(entries))

    if not entries:
        logger.warning("No trajectory entries found for diagnostic")
        return report

    # 1. Judge coverage
    coverage, coverage_tasks = _check_judge_coverage(entries)
    report.judge_coverage = coverage
    for t in coverage_tasks:
        if t.priority == "P0":
            report.critical.append(t)
        else:
            report.high.append(t)

    # 2. Dimension failures
    top_failing, dim_tasks = _check_dimension_failures(entries)
    report.top_failing_dimension = top_failing
    report.high.extend(dim_tasks)

    # 3. Platform failures
    report.high.extend(_check_platform_failures(entries))

    # 4. Feedback loop status
    report.medium.extend(_check_feedback_loop(entries))

    # 5. Failure streaks
    report.medium.extend(_check_failure_streaks(entries))

    # 6. Content quality signals
    report.medium.extend(_check_content_quality_signals(entries))

    # 7. Avg score
    scored = [
        e
        for e in entries
        if isinstance(e.get("judge_score"), (int, float)) and e["judge_score"] > 0
    ]
    if scored:
        report.avg_score = sum(e["judge_score"] for e in scored) / len(scored)

    # Collect patterns
    for task_list in (report.critical, report.high, report.medium, report.suggestions):
        for t in task_list:
            report.failure_patterns.append(t.description)

    return report


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------


def format_report(report: DiagnosticReport) -> str:
    """Format diagnostic report as markdown."""
    lines = [
        f"# System Diagnostic - {report.timestamp[:10]}",
        "",
        "## Health",
        f"- Entries analyzed: {report.entries_analyzed}",
        f"- Judge coverage: {report.judge_coverage:.0%}",
        f"- Avg judge score: {report.avg_score:.2f}"
        if report.avg_score > 0
        else "- Avg judge score: N/A",
        f"- Top failing dimension: {report.top_failing_dimension or 'N/A'}",
        "",
    ]

    def _fmt_tasks(tasks: list[DiagnosticTask], header: str) -> list[str]:
        if not tasks:
            return [f"## {header}", "", "No issues found.", ""]
        result = [f"## {header}", ""]
        for t in tasks:
            result.append(f"- **[{t.category}]** {t.description}")
            if t.file_ref:
                result.append(f"  File: `{t.file_ref}`")
            result.append(f"  Root cause: {t.root_cause}")
            result.append(f"  Evidence: {t.evidence}")
            result.append(f"  Fix: {t.suggested_fix}")
            result.append("")
        return result

    lines.extend(_fmt_tasks(report.critical, "P0 - Critical"))
    lines.extend(_fmt_tasks(report.high, "P1 - High"))
    lines.extend(_fmt_tasks(report.medium, "P2 - Medium"))
    lines.extend(_fmt_tasks(report.suggestions, "P3 - Suggestions"))

    return "\n".join(lines)


def save_report(report: DiagnosticReport) -> Path:
    """Save report to reports directory and append tasks to NEXT.md."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = report.timestamp[:10]
    path = REPORT_DIR / f"{date_str}.md"
    path.write_text(format_report(report))
    logger.info("Diagnostic report saved to %s", path)
    append_to_next_md(report)
    return path


def append_to_next_md(report: DiagnosticReport) -> int:
    """Append P0/P1 findings to agentic/memory/NEXT.md.

    Creates a '## System Diagnostic Tasks' section if missing.
    Skips tasks whose first 50 chars of description already appear in the section.

    Returns the count of tasks appended.
    """
    section_header = "## System Diagnostic Tasks"

    # Gather P0 and P1 tasks
    tasks_to_add: list[DiagnosticTask] = []
    for task in report.critical:
        if task.priority in ("P0", "P1"):
            tasks_to_add.append(task)
    for task in report.high:
        if task.priority in ("P0", "P1"):
            tasks_to_add.append(task)

    if not tasks_to_add:
        return 0

    # Read current NEXT.md
    content = NEXT_MD_PATH.read_text() if NEXT_MD_PATH.exists() else ""

    # Find or create the section
    if section_header in content:
        # Extract existing section text for dedup checking
        section_start = content.index(section_header)
        # Find the next ## heading after our section (or EOF)
        rest = content[section_start + len(section_header) :]
        next_heading = rest.find("\n## ")
        section_text = rest if next_heading == -1 else rest[:next_heading]
    else:
        # Append the section header at the end
        content = content.rstrip() + "\n\n---\n\n" + section_header + "\n"
        section_text = ""

    # Append non-duplicate tasks
    appended = 0
    new_lines: list[str] = []
    for task in tasks_to_add:
        # Fuzzy match: check if first 50 chars of description already in section
        prefix = task.description[:50]
        if prefix in section_text:
            continue
        line = (
            f"- [ ] [{task.category}] {task.description}"
            f" - File: `{task.file_ref}`."
            f" Fix: {task.suggested_fix}"
        )
        new_lines.append(line)
        appended += 1

    if not new_lines:
        return 0

    # Write back
    if section_header in content:
        # Insert new lines at the end of the section
        section_start = content.index(section_header)
        rest = content[section_start + len(section_header) :]
        next_heading = rest.find("\n## ")
        if next_heading == -1:
            # Section is at the end - just append
            content = content.rstrip() + "\n" + "\n".join(new_lines) + "\n"
        else:
            # Insert before the next heading
            insert_pos = section_start + len(section_header) + next_heading
            content = (
                content[:insert_pos].rstrip()
                + "\n"
                + "\n".join(new_lines)
                + "\n"
                + content[insert_pos:]
            )
    else:
        # Header was just added above, append tasks
        content = content.rstrip() + "\n" + "\n".join(new_lines) + "\n"

    NEXT_MD_PATH.write_text(content)
    logger.info("Appended %d diagnostic tasks to %s", appended, NEXT_MD_PATH)
    return appended


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Run diagnostic and print report."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  SYSTEM DIAGNOSTIC")
    print("=" * 60)
    print()

    report = run_diagnostic(days=30)
    text = format_report(report)
    print(text)

    path = save_report(report)
    print(f"\nReport saved to: {path}")

    appended = append_to_next_md(report)
    print(f"Tasks appended to NEXT.md: {appended}")

    # Summary counts
    print(
        f"\nFindings: {len(report.critical)} critical, {len(report.high)} high, "
        f"{len(report.medium)} medium, {len(report.suggestions)} suggestions"
    )
    if report.critical:
        print("\n⚠ CRITICAL ISSUES FOUND - address before next content cycle")


if __name__ == "__main__":
    main()
