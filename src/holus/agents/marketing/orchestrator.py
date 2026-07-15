"""Orchestrator - ties all self-improvement mechanisms into 3 cron cycles.

Three entry points, each a single Python function:

1. content_cycle()  - every 6h: generate → judge → auto-publish
2. analytics_cycle() - daily: fetch engagement → compute rewards
3. improvement_cycle() - weekly: learn → evolve → evaluate A/B tests

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
from typing import Any

logger = logging.getLogger(__name__)


async def content_cycle(idea: str | None = None) -> dict[str, Any]:
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


async def analytics_cycle() -> dict[str, Any]:
    """Fetch engagement data for published content, then update bandit weights."""
    from holus.agents.marketing.analytics_collector import collect_analytics

    logger.info("=== ANALYTICS CYCLE START (%s) ===", datetime.now(UTC).isoformat())

    results = await collect_analytics()

    # Close the feedback loop: update bandit weights from engagement data
    bandit_updates = 0
    if results:
        bandit_updates = _update_bandit_weights(results)

    summary = {
        "pieces_collected": len(results),
        "avg_engagement": (
            sum(r.get("engagement_signal", 0) for r in results) / len(results) if results else 0
        ),
        "avg_reward": (
            sum(r.get("blended_reward", 0) for r in results) / len(results) if results else 0
        ),
        "bandit_updates": bandit_updates,
    }

    logger.info("Analytics cycle complete: %s", summary)
    return summary


def _update_bandit_weights(results: list[dict[str, Any]]) -> int:
    """Update strategy bandit and visual bandit from analytics results.

    Returns the number of arms successfully updated.
    """
    updated = 0

    # Strategy bandit: continuous reward per product:content_type:platform arm
    try:
        from holus.agents.marketing.strategy_bandit import StrategyBandit

        strategy_bandit = StrategyBandit()
        for r in results:
            product = r.get("product", "unknown")
            content_type = r.get("content_type", "unknown")
            platform = r.get("platform", "unknown")
            reward = r.get("blended_reward", 0)

            if product == "unknown" or content_type == "unknown":
                continue

            arm_id = f"{product}:{content_type}:{platform}"
            strategy_bandit.update(arm_id, reward)
            updated += 1
            logger.info(
                "Strategy bandit updated: arm=%s reward=%.4f",
                arm_id,
                reward,
            )
    except Exception as exc:
        logger.warning("Strategy bandit update failed (non-blocking): %s", exc)

    # Visual bandit: binary win/loss per visual treatment arm
    try:
        from holus.agents.marketing.performance_loop import PerformanceLoop

        perf_loop = PerformanceLoop()
        for r in results:
            visual_arm = r.get("arm_id")
            post_id = r.get("post_id")
            if not visual_arm or not post_id:
                continue

            perf_loop.process(
                post_id=post_id,
                arm_id=visual_arm,
                engagement_data={
                    "impressions": r.get("views", 0),
                    "reactions": r.get("likes", 0),
                    "comments": r.get("comments", 0),
                    "shares": r.get("shares", 0),
                },
            )
    except Exception as exc:
        logger.warning("Visual bandit update failed (non-blocking): %s", exc)

    return updated


async def improvement_cycle() -> dict[str, Any]:
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
        if total_entries >= 100:
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
                "Prompt evolution gate: %d/%d entries (need 100)",
                total_entries,
                100,
            )

    # 3. Log gap summary
    gap_dir = Path(".self-improvement/capability-requests")
    knowledge_gap_dir = Path("agentic/memory/knowledge/requests")
    capability_gaps = len(list(gap_dir.glob("*.md"))) if gap_dir.exists() else 0
    knowledge_gaps = (
        len(list(knowledge_gap_dir.glob("*.md"))) - 1 if knowledge_gap_dir.exists() else 0
    )  # -1 for README

    # 4. System diagnostic (SPEC-036)
    diagnostic_findings = 0
    try:
        from holus.self_improvement.diagnostician import run_diagnostic
        from holus.self_improvement.diagnostician import save_report as save_diagnostic

        diag_report = run_diagnostic(days=30)
        diagnostic_findings = (
            len(diag_report.critical)
            + len(diag_report.high)
            + len(diag_report.medium)
            + len(diag_report.suggestions)
        )
        if diagnostic_findings > 0:
            save_diagnostic(diag_report)
            logger.info(
                "Diagnostic: %d critical, %d high, %d medium findings",
                len(diag_report.critical),
                len(diag_report.high),
                len(diag_report.medium),
            )
    except Exception as exc:
        logger.warning("System diagnostic failed (non-blocking): %s", exc)

    # 5. Detect failure streaks (log for diagnostician - auto-optimization is future work)
    try:
        traj_entries = _load_recent_trajectory()
        streaks = _detect_failure_streaks(traj_entries)
        for agent_id, streak_len in streaks.items():
            logger.warning(
                "Failure streak: agent '%s' has %d consecutive FAIL/PARTIAL",
                agent_id,
                streak_len,
            )
    except Exception as exc:
        logger.warning("Failure streak detection failed (non-blocking): %s", exc)

    summary = {
        "entries_analyzed": report.trajectory_entries_analyzed,
        "insights": len(report.insights),
        "memory_updated": report.memory_updated,
        "files_updated": report.knowledge_files_updated,
        "gaps_detected": report.gaps_processed,
        "open_capability_gaps": max(0, capability_gaps),
        "open_knowledge_gaps": max(0, knowledge_gaps),
        "evolution_ran": evolution_report is not None,
        "diagnostic_findings": diagnostic_findings,
        "skipped_reason": report.skipped_reason,
    }

    logger.info("Improvement cycle complete: %s", summary)
    return summary


def _load_recent_trajectory() -> list[dict[str, Any]]:
    """Load recent trajectory entries for failure streak detection."""
    import json

    path = Path(".self-improvement/memory/trajectory.jsonl")
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines()[-100:]:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _detect_failure_streaks(entries: list[dict[str, Any]]) -> dict[str, int]:
    """Detect consecutive failure streaks per agent. Returns {agent_id: max_streak}."""
    agent_streaks: dict[str, int] = {}
    agent_current: dict[str, int] = {}

    for entry in entries:
        agent = entry.get("agent_id", "")
        verdict = entry.get("judge_verdict")
        if not agent or not verdict:
            continue
        if verdict in ("FAIL", "PARTIAL"):
            agent_current[agent] = agent_current.get(agent, 0) + 1
            agent_streaks[agent] = max(agent_streaks.get(agent, 0), agent_current[agent])
        else:
            agent_current[agent] = 0

    return {a: s for a, s in agent_streaks.items() if s >= 3}


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
