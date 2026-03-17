"""Orchestrator — ties all self-improvement mechanisms into 3 cron cycles.

Three entry points, each a single Python function:

1. content_cycle()  — every 6h: generate → judge → auto-publish
2. analytics_cycle() — daily: fetch engagement → compute rewards
3. improvement_cycle() — weekly: learn → evolve → evaluate A/B tests

Usage (from Justfile or launchd):

    uv run python -m holus.agents.marketing.orchestrator content
    uv run python -m holus.agents.marketing.orchestrator analytics
    uv run python -m holus.agents.marketing.orchestrator improve
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


async def content_cycle(idea: str | None = None) -> dict:
    """Generate content, evaluate with judge, auto-publish.

    If no idea provided, uses the cold-start calendar or generates
    from trending topics.
    """
    from holus.agents.marketing.auto_publish import process_queue
    from holus.agents.marketing.idea_runner import run_from_bandit, run_from_idea

    logger.info("=== CONTENT CYCLE START (%s) ===", datetime.now(UTC).isoformat())

    if idea:
        results = run_from_idea(idea)
    else:
        # Auto-mode: generate from a seed idea
        results = run_from_bandit(
            "Share an insight from building AI agents that self-improve",
        )

    # Auto-publish based on judge scores
    publish_results = await process_queue()

    summary = {
        "generated": len(results),
        "publish_actions": len(publish_results),
        "published": sum(1 for r in publish_results if r.get("action") == "published"),
        "needs_review": sum(1 for r in publish_results if r.get("action") == "needs_review"),
        "rejected": sum(1 for r in publish_results if r.get("action") == "rejected"),
    }

    logger.info("Content cycle complete: %s", summary)
    return summary


async def analytics_cycle() -> dict:
    """Fetch engagement data for published content."""
    from holus.agents.marketing.analytics_collector import collect_analytics

    logger.info("=== ANALYTICS CYCLE START (%s) ===", datetime.now(UTC).isoformat())

    results = await collect_analytics()

    summary = {
        "pieces_collected": len(results),
        "avg_engagement": (
            sum(r.get("engagement_signal", 0) for r in results) / len(results)
            if results else 0
        ),
        "avg_reward": (
            sum(r.get("blended_reward", 0) for r in results) / len(results)
            if results else 0
        ),
    }

    logger.info("Analytics cycle complete: %s", summary)
    return summary


async def improvement_cycle() -> dict:
    """Weekly learning + prompt evolution + A/B test evaluation."""
    from holus.self_improvement.learning_loop import WeeklyLearningLoop

    logger.info("=== IMPROVEMENT CYCLE START (%s) ===", datetime.now(UTC).isoformat())

    # 1. Statistical learning (zero LLM cost)
    learning_loop = WeeklyLearningLoop()
    report = learning_loop.run()

    # 2. Check if prompt evolution should activate (n >= 500)
    evolution_report = None
    trajectory_path = Path(".self-improvement/memory/trajectory.jsonl")
    if trajectory_path.exists():
        with open(trajectory_path, encoding="utf-8") as fh:
            total_entries = sum(1 for _ in fh)
        if total_entries >= 500:
            try:
                from holus.self_improvement.prompt_evolution import PromptEvolution

                for agent_id in ("idea-generator", "idea-planner"):
                    evo = PromptEvolution(agent_id)
                    if evo.population_size > 0:
                        evolution_report = await evo.evolve()
                        if evolution_report:
                            logger.info(
                                "Evolution gen %d for %s: best=%s (%.2f)",
                                evolution_report.generation,
                                agent_id,
                                evolution_report.best_variant_id,
                                evolution_report.best_avg_score,
                            )
            except Exception as exc:
                logger.warning("Prompt evolution failed (non-blocking): %s", exc)
        else:
            logger.info(
                "Prompt evolution gate: %d/%d entries (need 500)",
                total_entries, 500,
            )

    # 3. Log gap summary
    gap_dir = Path(".self-improvement/capability-requests")
    knowledge_gap_dir = Path(".self-improvement/knowledge/requests")
    capability_gaps = len(list(gap_dir.glob("*.md"))) if gap_dir.exists() else 0
    knowledge_gaps = len(list(knowledge_gap_dir.glob("*.md"))) - 1 if knowledge_gap_dir.exists() else 0  # -1 for README

    summary = {
        "entries_analyzed": report.trajectory_entries_analyzed,
        "insights": len(report.insights),
        "memory_updated": report.memory_updated,
        "files_updated": report.knowledge_files_updated,
        "gaps_detected": report.gaps_processed,
        "open_capability_gaps": max(0, capability_gaps),
        "open_knowledge_gaps": max(0, knowledge_gaps),
        "evolution_ran": evolution_report is not None,
        "skipped_reason": report.skipped_reason,
    }

    logger.info("Improvement cycle complete: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry: `python -m holus.agents.marketing.orchestrator <cycle>`."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m holus.agents.marketing.orchestrator <content|analytics|improve>")
        sys.exit(1)

    cycle = sys.argv[1]

    if cycle == "content":
        idea = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
        result = asyncio.run(content_cycle(idea))
    elif cycle == "analytics":
        result = asyncio.run(analytics_cycle())
    elif cycle == "improve":
        result = asyncio.run(improvement_cycle())
    else:
        print(f"Unknown cycle: {cycle}. Use: content, analytics, improve")
        sys.exit(1)

    print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
