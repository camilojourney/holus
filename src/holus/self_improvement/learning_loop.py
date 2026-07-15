"""Weekly learning loop: extract patterns from trajectory + analytics.

Reads trajectory data and analytics, extracts patterns, and updates
MEMORY.md and knowledge files with new insights.  Runs weekly via
``just learn`` or programmatically from the manager agent.

Spec reference: 012-knowledge-learning.md SPEC-003
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from holus.memory.knowledge import archive_knowledge_file
from holus.memory.knowledge_gaps import list_open_gaps
from holus.memory.trajectory import TrajectoryEntry, TrajectoryLogger

logger = logging.getLogger(__name__)

DEFAULT_TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")
DEFAULT_MEMORY_PATH = Path("agentic/memory/MEMORY.md")
DEFAULT_KNOWLEDGE_DIR = Path("agentic/memory/knowledge/current")
DEFAULT_ARCHIVE_DIR = Path("agentic/memory/knowledge/archive")

MIN_DATA_POINTS = 5


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Insight:
    """A single insight extracted from data."""

    pattern: str
    confidence: str  # preliminary | medium | high
    sample_size: int
    source: str  # trajectory | analytics | combined


@dataclass
class LearningReport:
    """Output of a weekly learning cycle."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    trajectory_entries_analyzed: int = 0
    insights: list[Insight] = field(default_factory=list)
    memory_updated: bool = False
    knowledge_files_updated: list[str] = field(default_factory=list)
    gaps_processed: int = 0
    skipped_reason: str | None = None


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


class WeeklyLearningLoop:
    """Extracts patterns from trajectories + analytics, updates knowledge.

    The learning flywheel:

    1. Read trajectory data (last *lookback_days* days).
    2. Aggregate by content_type / platform / product.
    3. Check minimum sample size (*min_data_points*).
    4. Extract patterns (statistical, not LLM - keeps cost zero).
    5. Update ``MEMORY.md`` with new insights (append, never overwrite).
    6. Update ``performance-patterns.md`` knowledge file.
    7. Process open knowledge gap requests.
    8. Log the cycle itself to trajectory.
    """

    def __init__(
        self,
        *,
        trajectory_path: Path | str = DEFAULT_TRAJECTORY_PATH,
        memory_path: Path = DEFAULT_MEMORY_PATH,
        knowledge_dir: Path = DEFAULT_KNOWLEDGE_DIR,
        archive_dir: Path = DEFAULT_ARCHIVE_DIR,
        lookback_days: int = 7,
        min_data_points: int = MIN_DATA_POINTS,
    ) -> None:
        self.trajectory = TrajectoryLogger(trajectory_path)
        self.memory_path = memory_path
        self.knowledge_dir = knowledge_dir
        self.archive_dir = archive_dir
        self.lookback_days = lookback_days
        self.min_data_points = min_data_points

    def run(self) -> LearningReport:
        """Execute the weekly learning cycle.

        Returns a ``LearningReport`` describing what was analyzed and updated.
        """
        start = datetime.now(UTC)
        report = LearningReport()

        # 1 - Read trajectory data
        cutoff = (datetime.now(UTC) - timedelta(days=self.lookback_days)).isoformat()
        all_entries = self.trajectory.read_all()
        recent = [e for e in all_entries if e.timestamp >= cutoff]
        report.trajectory_entries_analyzed = len(recent)

        if len(recent) < self.min_data_points:
            report.skipped_reason = (
                f"Not enough data: {len(recent)} entries (minimum {self.min_data_points})"
            )
            logger.info(report.skipped_reason)
            self._log_cycle(report, start)
            return report

        # 2 - Aggregate patterns
        patterns = self._aggregate_patterns(recent)

        # 3 - Extract insights
        insights = self._extract_insights(patterns, recent)
        report.insights = insights

        # 4 - Update MEMORY.md
        if insights:
            self._update_memory(insights)
            report.memory_updated = True

        # 5 - Update performance-patterns.md
        if insights:
            updated = self._update_performance_patterns(insights, patterns)
            if updated:
                report.knowledge_files_updated.append("performance-patterns.md")

        # 6 - Detect score drift (trigger optimization if quality is declining)
        drift_agents = self._detect_drift(all_entries)
        if drift_agents:
            for agent_id in drift_agents:
                insights.append(
                    Insight(
                        pattern=f"DRIFT DETECTED: {agent_id} - 30-day avg dropped 0.1+ from peak",
                        confidence="medium",
                        sample_size=len(recent),
                        source="trajectory",
                    )
                )
            logger.warning("Drift detected for agents: %s", drift_agents)

        # 7 - Detect capability/data gaps from failure patterns
        try:
            from holus.self_improvement.gap_detector import detect_gaps, write_gap_request

            gap_entries = [e.to_dict() for e in recent]
            detected_gaps = detect_gaps(gap_entries, min_failures=3)
            for gap in detected_gaps:
                if gap["type"] in ("capability_gap", "data_gap"):
                    write_gap_request(gap)
            report.gaps_processed = len(detected_gaps)
        except Exception as exc:
            logger.debug("Gap detection failed (non-blocking): %s", exc)
            gaps = list_open_gaps()
            report.gaps_processed = len(gaps)

        # 8 - Log the cycle
        self._log_cycle(report, start)

        logger.info(
            "Learning cycle complete: %d entries, %d insights, %d files updated",
            report.trajectory_entries_analyzed,
            len(report.insights),
            len(report.knowledge_files_updated),
        )
        return report

    # -- internal helpers ---------------------------------------------------

    def _aggregate_patterns(
        self,
        entries: list[TrajectoryEntry],
    ) -> dict[str, dict[str, Any]]:
        """Group entries by product x content_type x platform."""
        patterns: dict[str, dict[str, Any]] = {}

        for entry in entries:
            meta = entry.metadata
            content_type = meta.get("content_type", "unknown")
            platform = meta.get("platform", "unknown")
            product = meta.get("product", "unknown")
            key = f"{product}_{content_type}_{platform}"

            if key not in patterns:
                patterns[key] = {
                    "product": product,
                    "content_type": content_type,
                    "platform": platform,
                    "count": 0,
                    "statuses": [],
                    "judge_scores": [],
                    "engagement_signals": [],
                    "blended_rewards": [],
                }

            patterns[key]["count"] += 1
            patterns[key]["statuses"].append(entry.status)

            # Collect scores for enriched analysis
            if entry.judge_score is not None:
                patterns[key]["judge_scores"].append(entry.judge_score)
            eng = entry.metadata.get("engagement_signal")
            if eng is not None:
                patterns[key]["engagement_signals"].append(eng)
            reward = entry.metadata.get("blended_reward")
            if reward is not None:
                patterns[key]["blended_rewards"].append(reward)

        return patterns

    def _extract_insights(
        self,
        patterns: dict[str, dict[str, Any]],
        entries: list[TrajectoryEntry],
    ) -> list[Insight]:
        """Extract statistical insights from aggregated patterns.

        This is local (zero-cost) extraction.  For deeper LLM-based analysis
        the manager agent calls Claude Opus separately.
        """
        insights: list[Insight] = []

        # -- most active content type ----------------------------------------
        type_counts: dict[str, int] = {}
        for p in patterns.values():
            ct = p["content_type"]
            type_counts[ct] = type_counts.get(ct, 0) + p["count"]

        if type_counts:
            total_pieces = sum(type_counts.values())
            most_active = max(type_counts, key=lambda k: type_counts[k])
            insights.append(
                Insight(
                    pattern=(
                        f"Most active content type: {most_active} "
                        f"({type_counts[most_active]} pieces)"
                    ),
                    confidence="preliminary" if total_pieces < 20 else "medium",
                    sample_size=total_pieces,
                    source="trajectory",
                )
            )

        # -- most active platform --------------------------------------------
        platform_counts: dict[str, int] = {}
        for p in patterns.values():
            pl = p["platform"]
            platform_counts[pl] = platform_counts.get(pl, 0) + p["count"]

        if platform_counts:
            total_pieces = sum(platform_counts.values())
            most_active_platform = max(platform_counts, key=lambda k: platform_counts[k])
            insights.append(
                Insight(
                    pattern=(
                        f"Most active platform: {most_active_platform} "
                        f"({platform_counts[most_active_platform]} pieces)"
                    ),
                    confidence="preliminary" if total_pieces < 20 else "medium",
                    sample_size=total_pieces,
                    source="trajectory",
                )
            )

        # -- overall success rate --------------------------------------------
        success_count = sum(1 for e in entries if e.status == "success")
        total = len(entries)
        if total > 0:
            rate = success_count / total
            insights.append(
                Insight(
                    pattern=f"Overall success rate: {rate:.0%} ({success_count}/{total})",
                    confidence="preliminary" if total < 20 else "medium",
                    sample_size=total,
                    source="trajectory",
                )
            )

        # -- per-product breakdown -------------------------------------------
        product_counts: dict[str, dict[str, int]] = {}
        for p in patterns.values():
            prod = p["product"]
            if prod not in product_counts:
                product_counts[prod] = {"total": 0, "success": 0}
            product_counts[prod]["total"] += p["count"]
            product_counts[prod]["success"] += sum(1 for s in p["statuses"] if s == "success")

        for prod, counts in sorted(product_counts.items()):
            if counts["total"] >= 3:
                prod_rate = counts["success"] / counts["total"] if counts["total"] > 0 else 0
                insights.append(
                    Insight(
                        pattern=(f"{prod}: {counts['total']} pieces, {prod_rate:.0%} success rate"),
                        confidence="preliminary",
                        sample_size=counts["total"],
                        source="trajectory",
                    )
                )

        return insights

    def _update_memory(self, insights: list[Insight]) -> None:
        """Append new insights to MEMORY.md (never overwrite existing)."""
        if not self.memory_path.exists():
            logger.warning("MEMORY.md not found at %s", self.memory_path)
            return

        current = self.memory_path.read_text()
        today = datetime.now(UTC).date().isoformat()

        insight_lines = [
            f"\n### Learning Loop - {today}\n",
            (f"_Auto-generated from {sum(i.sample_size for i in insights)} data points._\n"),
        ]
        for insight in insights:
            insight_lines.append(
                f"- {insight.pattern} (confidence: {insight.confidence}, source: {insight.source})"
            )
        insight_lines.append("")

        block = "\n".join(insight_lines)

        # Insert before the Analytics Source section if present
        marker = "## Content Strategy (What We've Learned)"
        next_divider = "\n---\n"

        if marker in current:
            marker_pos = current.index(marker)
            divider_pos = current.find(next_divider, marker_pos + len(marker))
            if divider_pos != -1:
                current = current[:divider_pos] + "\n" + block + current[divider_pos:]
            else:
                current = current + "\n" + block
        else:
            current = current + "\n" + block

        self.memory_path.write_text(current)
        logger.info("Appended %d insights to MEMORY.md", len(insights))

    def _update_performance_patterns(
        self,
        insights: list[Insight],
        patterns: dict[str, dict[str, Any]],
    ) -> bool:
        """Create or update ``performance-patterns.md``."""
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        path = self.knowledge_dir / "performance-patterns.md"

        # Archive previous version
        if path.exists() and path.stat().st_size > 200:
            archive_knowledge_file(path, archive_dir=self.archive_dir)

        today = datetime.now(UTC).date().isoformat()
        total_pieces = sum(p["count"] for p in patterns.values())
        confidence = "preliminary" if total_pieces < 50 else "medium"

        lines = [
            "# Knowledge: Performance Patterns",
            "",
            f"**Last updated:** {today}",
            "**Updated by:** learning-loop",
            f"**Confidence:** {confidence}",
            "**Affects:** marketing agent content decisions",
            "**Research cadence:** weekly",
            "",
            "---",
            "",
            "## Summary",
            "",
            (
                f"Data from the last {self.lookback_days} days. "
                f"{total_pieces} content pieces analyzed."
            ),
            "",
            "## Insights",
            "",
        ]
        for insight in insights:
            lines.append(
                f"- **{insight.pattern}** "
                f"(confidence: {insight.confidence}, n={insight.sample_size})"
            )
        lines.append("")

        # Breakdown table
        lines.append("## Content Type x Platform Breakdown")
        lines.append("")
        lines.append("| Product | Content Type | Platform | Count | Success Rate |")
        lines.append("|---------|-------------|----------|-------|-------------|")
        for _key, p in sorted(patterns.items()):
            success = sum(1 for s in p["statuses"] if s == "success")
            rate = f"{success / p['count']:.0%}" if p["count"] > 0 else "N/A"
            lines.append(
                f"| {p['product']} | {p['content_type']} "
                f"| {p['platform']} | {p['count']} | {rate} |"
            )
        lines.append("")

        path.write_text("\n".join(lines))
        logger.info("Updated performance-patterns.md")
        return True

    def _detect_drift(
        self,
        all_entries: list[TrajectoryEntry],
        *,
        window_days: int = 30,
        drop_threshold: float = 0.1,
    ) -> list[str]:
        """Detect score drift: agents whose 30-day avg dropped 0.1+ from peak.

        Returns list of agent_ids that need prompt optimization.
        """
        cutoff_30d = (datetime.now(UTC) - timedelta(days=window_days)).isoformat()
        recent_30d = [
            e for e in all_entries if e.timestamp >= cutoff_30d and e.judge_score is not None
        ]

        if len(recent_30d) < 10:
            return []

        # Group scores by agent_id
        agent_scores: dict[str, list[float]] = {}
        for e in recent_30d:
            if e.judge_score is not None:
                agent_scores.setdefault(e.agent_id, []).append(e.judge_score)

        drifting: list[str] = []
        for agent_id, scores in agent_scores.items():
            if len(scores) < 5:
                continue
            peak = max(scores)
            avg = sum(scores) / len(scores)
            if peak - avg >= drop_threshold:
                drifting.append(agent_id)

        return drifting

    def _log_cycle(self, report: LearningReport, start: datetime) -> None:
        """Log the learning cycle itself to trajectory."""
        duration = (datetime.now(UTC) - start).total_seconds()
        summary = (
            f"Analyzed {report.trajectory_entries_analyzed} entries, "
            f"extracted {len(report.insights)} insights"
            if not report.skipped_reason
            else f"Skipped: {report.skipped_reason}"
        )
        self.trajectory.append(
            TrajectoryEntry(
                agent_id="learning-loop",
                task_type="weekly_learning",
                task_summary=summary,
                status="success" if not report.skipped_reason else "partial",
                duration_seconds=duration,
                metadata={
                    "entries_analyzed": report.trajectory_entries_analyzed,
                    "insights_count": len(report.insights),
                    "memory_updated": report.memory_updated,
                    "knowledge_files_updated": report.knowledge_files_updated,
                    "gaps_processed": report.gaps_processed,
                    "skipped_reason": report.skipped_reason,
                },
            )
        )


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------


def run_learning_loop(
    *,
    lookback_days: int = 7,
    min_data_points: int = MIN_DATA_POINTS,
) -> LearningReport:
    """Run the weekly learning loop with default paths."""
    loop = WeeklyLearningLoop(
        lookback_days=lookback_days,
        min_data_points=min_data_points,
    )
    return loop.run()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    report = run_learning_loop()

    if report.skipped_reason:
        print(f"Learning loop skipped: {report.skipped_reason}")
        sys.exit(0)

    print("Learning loop complete!")
    print(f"  Entries analyzed: {report.trajectory_entries_analyzed}")
    print(f"  Insights extracted: {len(report.insights)}")
    for insight in report.insights:
        print(f"    - {insight.pattern} [{insight.confidence}]")
    print(f"  MEMORY.md updated: {report.memory_updated}")
    print(f"  Knowledge files updated: {report.knowledge_files_updated}")
    print(f"  Knowledge gaps processed: {report.gaps_processed}")
