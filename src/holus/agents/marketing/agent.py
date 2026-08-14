"""Marketing agent LangGraph workflow.

ReAct loop:
  1. observe  -- read products config, knowledge files, and memory.
  2. reason   -- produce structured content decisions.
  3. act      -- generate platform-specific text and queue for review.
  4. render   -- produce visual attachments for pieces with visual intent.
  5. evaluate -- append decision/execution metadata to trajectory log.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, TypedDict
from uuid import uuid4

import yaml
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from holus.agents.base import BaseAgent
from holus.agents.marketing.models import (
    BrandIdentity,
    ContentDecision,
    ContentType,
    GeneratedPiece,
    NicheInsight,
    NicheResearchResult,
    Platform,
)
from holus.agents.marketing.prompts import (
    NICHE_EXTRACTION_PROMPT,
    OPUS_STRATEGY_PROMPT,
    SONNET_CONTENT_PROMPT,
    format_anti_patterns,
    format_brand_identity,
    format_content_pillars,
    format_positioning,
    format_product_info,
    format_voice,
)
from holus.agents.marketing.quality_score import score_content
from holus.agents.marketing.repurpose import repurpose_content
from holus.core.cycle_state import CycleContext, CycleState, write_trajectory_entry
from holus.core.health import run_preflight_checks
from holus.core.watchdog import consecutive_failure_check
from holus.integrations.claude_api.client import CachedPrompt
from holus.integrations.social_media import SocialMediaClient
from holus.memory.trajectory import TrajectoryEntry, TrajectoryLogger

logger = logging.getLogger(__name__)


class MarketingState(TypedDict):
    """State for one marketing cycle."""

    cycle_id: str
    started_at: str

    # Observe
    analytics: dict[str, Any]
    product_updates: dict[str, Any]
    knowledge: dict[str, str]
    memory_context: str
    queue_size_before: int
    brand_identity: dict[str, Any]
    niche_research: dict[str, Any]

    # Reason
    content_decisions: list[dict[str, Any]]
    strategy_reasoning: str

    # Act
    generated_content: list[dict[str, Any]]
    post_results: list[dict[str, Any]]

    # Evaluate
    evaluation: dict[str, Any]
    error: str | None
    capability_gaps: list[str]


class MarketingAgent(BaseAgent):
    """Primary marketing strategist agent."""

    agent_name = "marketing-agent"

    _PRODUCTS_PATH = Path("config/products.yaml")
    _BRAND_PATH = Path("config/brand.yaml")
    _KNOWLEDGE_DIR = Path("agentic/memory/knowledge/current")
    _MEMORY_PATH = Path("agentic/memory/MEMORY.md")
    _QUEUE_DIR = Path("data/content-queue")
    _TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")

    _PLATFORM_ALIASES: ClassVar[dict[str, Platform]] = {
        "linkedin": Platform.LINKEDIN,
        "twitter": Platform.TWITTER,
        "x": Platform.TWITTER,
        "tiktok": Platform.TIKTOK,
        "instagram": Platform.INSTAGRAM,
        "facebook": Platform.FACEBOOK,
        "threads": Platform.THREADS,
        "youtube": Platform.YOUTUBE,
        "youtube_shorts": Platform.YOUTUBE,
        "yt_shorts": Platform.YOUTUBE,
    }

    _CONTENT_TYPE_ALIASES: ClassVar[dict[str, ContentType]] = {
        "tutorial": ContentType.TUTORIAL,
        "demo": ContentType.DEMO,
        "tips": ContentType.TIPS,
        "thread": ContentType.THREAD,
        "case_study": ContentType.CASE_STUDY,
        "carousel": ContentType.CAROUSEL,
        "video_reel": ContentType.VIDEO_REEL,
        "announcement": ContentType.ANNOUNCEMENT,
        "educational": ContentType.EDUCATIONAL,
        "technical_post": ContentType.EDUCATIONAL,
        "before_after": ContentType.DEMO,
    }

    _PLATFORM_CHAR_LIMITS: ClassVar[dict[Platform, int]] = {
        Platform.TWITTER: 280,
        Platform.LINKEDIN: 3000,
        Platform.INSTAGRAM: 2200,
        Platform.THREADS: 500,
        Platform.FACEBOOK: 63206,
    }

    def build_graph(self) -> StateGraph[MarketingState]:
        """Construct the marketing observe -> reason -> act -> render -> evaluate graph."""
        graph = StateGraph(MarketingState)

        graph.add_node("observe", self.observe)
        graph.add_node("reason", self.reason)
        graph.add_node("act", self.act)
        graph.add_node("render", self.render)
        graph.add_node("evaluate", self.evaluate)

        graph.add_edge(START, "observe")
        graph.add_edge("observe", "reason")
        graph.add_edge("reason", "act")
        graph.add_edge("act", "render")
        graph.add_edge("render", "evaluate")
        graph.add_edge("evaluate", END)

        return graph

    def default_state(self) -> dict[str, Any]:
        """Initial state for a marketing cycle."""
        return {
            "cycle_id": uuid4().hex,
            "started_at": datetime.now(UTC).isoformat(),
            "analytics": {},
            "product_updates": {},
            "knowledge": {},
            "memory_context": "",
            "queue_size_before": 0,
            "brand_identity": {},
            "niche_research": {},
            "content_decisions": [],
            "strategy_reasoning": "",
            "generated_content": [],
            "post_results": [],
            "evaluation": {},
            "error": None,
            "capability_gaps": [],
        }

    async def run(
        self,
        state: dict[str, Any] | None = None,
        *,
        thread_id: str | None = None,
        checkpointer: Any = None,
    ) -> dict[str, Any]:
        """Run one marketing cycle wrapped in the CycleState machine.

        Every phase transition is logged to trajectory.jsonl.  If a blocking
        preflight check fails, the cycle is aborted before any work starts.
        A trajectory entry is always written - even on hard failures - so the
        watchdog and self-improvement system have complete data.

        After the trajectory entry is written, ``consecutive_failure_check``
        is called. If the last 3 cycles all failed the marketing-agent kill
        switch is activated and a MARKETING_AGENT_PAUSED alert is logged.
        """
        ctx = CycleContext.new(trajectory_path=self._TRAJECTORY_PATH)
        final_state: dict[str, Any] = {}
        current_phase = "initializing"

        try:
            # ------------------------------------------------------------------
            # HEALTH_CHECK phase
            # ------------------------------------------------------------------
            current_phase = "health_check"
            ctx.transition(CycleState.HEALTH_CHECK)
            health = run_preflight_checks(
                skip_run_lock_check=True,  # run-lock already held by caller
            )
            ctx.health_result = health

            if not health.blocking_ok:
                ctx.transition(CycleState.FAILED)
                ctx.error = f"Preflight blocked: {'; '.join(health.warnings)}"
                logger.warning(
                    "Marketing cycle blocked by preflight: %s",
                    "; ".join(health.warnings),
                )
                return {}

            if health.warnings:
                logger.warning(
                    "Marketing cycle starting with preflight warnings: %s",
                    "; ".join(health.warnings),
                )

            # ------------------------------------------------------------------
            # LOADING_STATE phase - compile graph and prepare initial state
            # ------------------------------------------------------------------
            current_phase = "loading_state"
            ctx.transition(CycleState.LOADING_STATE)
            app = self.compile(checkpointer=checkpointer)  # type: ignore[no-untyped-call]
            initial = state or self.default_state()

            run_config: dict[str, Any] = {}
            if thread_id:
                run_config["configurable"] = {"thread_id": thread_id}

            # ------------------------------------------------------------------
            # OBSERVING phase
            # ------------------------------------------------------------------
            current_phase = "observing"
            ctx.transition(CycleState.OBSERVING)

            # ------------------------------------------------------------------
            # REASONING phase
            # ------------------------------------------------------------------
            current_phase = "reasoning"
            ctx.transition(CycleState.REASONING)

            # ------------------------------------------------------------------
            # CREATING phase
            # ------------------------------------------------------------------
            current_phase = "creating"
            ctx.transition(CycleState.CREATING)

            # Run the full LangGraph workflow (observe → reason → act → evaluate)
            final_state = await app.ainvoke(initial, config=run_config)
            ctx.capability_gaps.extend(final_state.get("capability_gaps", []))

            # ------------------------------------------------------------------
            # QUALITY_CHECK phase - already performed inside act(), record result
            # ------------------------------------------------------------------
            current_phase = "quality_check"
            ctx.transition(CycleState.QUALITY_CHECK)
            post_results: list[dict[str, Any]] = final_state.get("post_results", [])
            generated: list[dict[str, Any]] = final_state.get("generated_content", [])

            ctx.content_created = len(generated)
            ctx.content_posted = sum(1 for r in post_results if r.get("status") == "pending_review")
            ctx.content_failed = sum(
                1 for r in post_results if r.get("status") in ("failed", "auto_rejected")
            )

            # ------------------------------------------------------------------
            # POSTING phase
            # ------------------------------------------------------------------
            current_phase = "posting"
            ctx.transition(CycleState.POSTING)

            # ------------------------------------------------------------------
            # IMPROVING phase
            # ------------------------------------------------------------------
            current_phase = "improving"
            ctx.transition(CycleState.IMPROVING)

            # Run judge evaluation on generated content
            if generated and getattr(getattr(self, "config", None), "anthropic_api_key", None):
                try:
                    from holus.self_improvement.judge import JudgeAgent

                    judge = JudgeAgent(api_key=self.config.anthropic_api_key)

                    for content_item in generated:
                        decision_data = content_item.get("decision", {})
                        content_type = decision_data.get("content_type", "TUTORIAL")
                        text = content_item.get("text", "")
                        topic = decision_data.get("topic", "unknown")

                        if not text:
                            continue

                        evaluation = judge.evaluate_with_routing(
                            task=f"Create {content_type} content about {topic}",
                            content_type=content_type,
                            output=text,
                        )

                        content_item["judge_evaluation"] = evaluation.to_dict()

                        logger.info(
                            "Judge evaluation for %s [%s]: %s (%.2f)",
                            topic,
                            content_type,
                            evaluation.verdict.value,
                            evaluation.score,
                        )
                except Exception:
                    logger.warning(
                        "Judge evaluation failed; continuing without scores",
                        exc_info=True,
                    )
                    ctx.capability_gaps.append("judge_evaluation_unavailable")

            # ------------------------------------------------------------------
            # SAVING_STATE phase → DONE
            # ------------------------------------------------------------------
            current_phase = "saving_state"
            ctx.transition(CycleState.SAVING_STATE)
            ctx.transition(CycleState.DONE)

        except Exception as exc:
            ctx.transition(CycleState.FAILED)
            ctx.error = f"Failed during {current_phase}: {exc}"
            logger.exception(
                "Marketing cycle failed with unhandled exception [cycle_id=%s, phase=%s]: %s",
                ctx.cycle_id,
                current_phase,
                exc,
            )
            if final_state:
                self._save_partial_state(final_state, ctx.cycle_id)

        finally:
            # ------------------------------------------------------------------
            # Trajectory entry - always written (DONE or FAILED)
            # ------------------------------------------------------------------
            ctx.finish()
            write_trajectory_entry(ctx)

            # ------------------------------------------------------------------
            # Consecutive-failure guard - 3 failures → MARKETING_AGENT_PAUSED alert
            # ------------------------------------------------------------------
            if consecutive_failure_check(ctx.trajectory_path, threshold=3):
                logger.error(
                    "MARKETING_AGENT_PAUSED: 3 consecutive marketing cycle failures - "
                    "operator review required [cycle_id=%s, trajectory=%s]",
                    ctx.cycle_id,
                    str(ctx.trajectory_path),
                )
                try:
                    self.kill_switch.activate(
                        scope=self.agent_name,
                        reason="3 consecutive cycle failures",
                        activated_by="circuit_breaker",
                    )
                except Exception:
                    logger.warning(
                        "Failed to activate kill switch after consecutive failures",
                        exc_info=True,
                    )

        return final_state

    def _save_partial_state(self, state: dict[str, Any], cycle_id: str) -> None:
        """Save partial state to a recovery file when a cycle fails mid-execution.

        Uses atomic write (temp file + rename) to prevent corrupted recovery files.
        Falls back to logging the state if disk writes fail entirely.
        """
        recovery_data = {
            "cycle_id": cycle_id,
            "saved_at": datetime.now(UTC).isoformat(),
            "generated_content": state.get("generated_content", []),
            "content_decisions": state.get("content_decisions", []),
            "strategy_reasoning": state.get("strategy_reasoning", ""),
        }

        try:
            recovery_dir = Path("data/recovery")
            recovery_dir.mkdir(parents=True, exist_ok=True)
            safe_id = cycle_id.replace(":", "-").replace("+", "p")
            recovery_file = recovery_dir / f"{safe_id}.json"
            tmp_file = recovery_dir / f".{safe_id}.tmp"

            # Atomic write: write to temp file, then rename
            with tmp_file.open("w", encoding="utf-8") as fh:
                json.dump(recovery_data, fh, ensure_ascii=False, indent=2)
            tmp_file.rename(recovery_file)
            logger.info("Partial state saved for recovery: %s", recovery_file)
        except OSError as exc:
            logger.warning("Failed to save partial state to file: %s", exc)
            # Fallback: log the data so it's not silently lost
            import sys

            try:
                print(
                    json.dumps(recovery_data, ensure_ascii=False),
                    file=sys.stderr,
                )
                logger.info("Partial state written to stderr as fallback")
            except Exception:
                logger.error("Failed to save partial state entirely")

    async def observe(self, state: MarketingState) -> dict[str, Any]:
        """Observe phase: load config, knowledge, memory, brand, analytics, and niche research."""
        self.check_kill_switch()

        products = self._read_yaml(self._PRODUCTS_PATH)
        knowledge = self._read_knowledge_files(self._KNOWLEDGE_DIR)
        memory_context = self._read_text(self._MEMORY_PATH)
        brand_identity = self._load_brand_identity()

        # Analytics from Holus Social API (graceful degradation)
        analytics: dict[str, Any] = {}
        observe_gaps: list[str] = []
        try:
            analytics = await self._fetch_analytics()
        except Exception:
            logger.warning("Analytics fetch failed; continuing without it", exc_info=True)
            observe_gaps.append("analytics_unavailable")

        # Niche research (graceful degradation)
        niche_research: dict[str, Any] = {}
        try:
            niche_research = await self._niche_research()
        except Exception:
            logger.warning("Niche research failed; continuing without it", exc_info=True)
            observe_gaps.append("niche_research_unavailable")

        # Load judge feedback from last cycle (feedback loop)
        prior_feedback = self._load_prior_judge_feedback()

        return {
            "product_updates": products,
            "knowledge": knowledge,
            "memory_context": memory_context,
            "analytics": analytics,
            "queue_size_before": len(self._queue_files()),
            "brand_identity": brand_identity,
            "niche_research": niche_research,
            "capability_gaps": observe_gaps,
            "prior_judge_feedback": prior_feedback,
        }

    def _load_prior_judge_feedback(self) -> str:
        """Load judge feedback from last content cycle to inject into next generation.

        Reads the last 20 trajectory entries, extracts judge feedback
        from content pieces, and formats as a concise summary for the
        generation prompt.
        """
        traj_path = Path(".self-improvement/memory/trajectory.jsonl")
        if not traj_path.exists():
            return ""

        try:
            lines = traj_path.read_text().splitlines()
            # Read last 50 lines, filter to content entries with judge feedback
            recent = []
            for line in lines[-50:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                feedback = entry.get("judge_feedback")
                verdict = entry.get("judge_verdict")
                if feedback and verdict and verdict in ("FAIL", "PARTIAL"):
                    dims = entry.get("metadata", {}).get("dimension_scores", {})
                    platform = entry.get("metadata", {}).get("platform", "")
                    recent.append(
                        {
                            "platform": platform,
                            "verdict": verdict,
                            "feedback": feedback[:300],
                            "weak_dims": {
                                k: v
                                for k, v in dims.items()
                                if isinstance(v, (int, float)) and v < 0.6
                            },
                        }
                    )

            if not recent:
                return ""

            parts = ["## Prior Cycle Feedback (learn from these mistakes)\n"]
            for r in recent[-5:]:  # Last 5 failures max
                parts.append(f"- [{r['platform'].upper()} - {r['verdict']}] {r['feedback'][:200]}")
                if r["weak_dims"]:
                    weak = ", ".join(f"{k}={v:.2f}" for k, v in r["weak_dims"].items())
                    parts.append(f"  Weak dimensions: {weak}")
            return "\n".join(parts)
        except Exception:
            logger.warning("Failed to load prior judge feedback", exc_info=True)
            return ""

    def _format_generation_feedback(self, platform: str, *, prior_feedback: str = "") -> str:
        """Extract platform-specific generation feedback from prior judge results.

        Filters the full prior_judge_feedback (loaded in observe) to entries
        matching the target platform. Returns concise writing guidance - what
        to avoid, which dimensions were weak.

        Parameters
        ----------
        platform:
            Target platform name (e.g. "linkedin", "threads", "twitter").
        prior_feedback:
            The full prior_judge_feedback string from observe phase.

        Returns
        -------
        str
            Formatted feedback for injection into generation prompts, or
            "No prior feedback for this platform." if nothing relevant.
        """
        if not prior_feedback:
            return "No prior feedback for this platform."

        platform_upper = platform.upper()
        relevant_lines: list[str] = []
        for line in prior_feedback.splitlines():
            # Match lines like "- [THREADS - PARTIAL] ..."
            if platform_upper in line.upper() or line.startswith("  Weak"):
                relevant_lines.append(line)

        if not relevant_lines:
            return "No prior feedback for this platform."

        return "\n".join(relevant_lines)

    def _load_brand_identity(self) -> dict[str, Any]:
        """Load and validate config/brand.yaml.

        Returns a validated dict (via BrandIdentity Pydantic model) or an
        empty dict if the file is missing or invalid.
        """
        raw = self._read_yaml(self._BRAND_PATH)
        if not raw:
            logger.warning("brand.yaml not found or empty; using empty brand identity")
            return {}
        try:
            brand = BrandIdentity(**raw)
            return brand.model_dump(mode="json")
        except ValidationError:
            logger.warning("brand.yaml validation failed; using raw dict", exc_info=True)
            return raw

    # -- Analytics fetch --------------------------------------------------------

    _ANALYTICS_LOOKBACK_DAYS = 7
    _TOP_POSTS_LIMIT = 5
    _TOP_POSTS_LOOKBACK_DAYS = 30

    async def _fetch_analytics(self) -> dict[str, Any]:
        """Fetch recent analytics from Holus Social API.

        Returns a dict with ``summary`` (aggregate stats) and ``top_posts``
        (best performing recent posts).  Returns empty dict if the API is
        unreachable or credentials are missing - the agent continues without
        analytics (cold start behavior).
        """
        api_key = getattr(self.config, "holus_social_api_key", "") or getattr(
            self.config, "posting_api_key", ""
        )
        base_url = getattr(self.config, "holus_social_api_base_url", "") or getattr(
            self.config,
            "social_media_api_base_url",
            "http://localhost:8000",
        )
        if not api_key:
            logger.info("Analytics fetch skipped: no HOLUS_SOCIAL_API_KEY configured")
            return {}

        async with SocialMediaClient(
            base_url=base_url,
            api_key=api_key,
        ) as client:
            summary = await client.get_analytics(days=self._ANALYTICS_LOOKBACK_DAYS)
            top_posts = await client.get_top_posts(
                limit=self._TOP_POSTS_LIMIT,
                days=self._TOP_POSTS_LOOKBACK_DAYS,
            )
            return {
                "summary": summary,
                "top_posts": top_posts,
            }

    # -- Schedule for approval --------------------------------------------------

    async def _schedule_for_approval(self, piece: GeneratedPiece) -> str | None:
        """Refuse pre-review scheduling; the reviewed API owns dispatch.

        Returns the schedule_id from the API, or None if scheduling fails.
        The local content queue remains the source of truth - this is a
        secondary registration so Holus Social API can track pending posts.
        """
        logger.info("Deferred scheduling for %s until human review", piece.piece_id)
        return None

    # -- Niche research sub-step -----------------------------------------------

    _NICHE_QUERIES_PATH = Path("agentic/memory/knowledge/current/niche-research-queries.md")
    _NICHE_STATE_PATH = Path("data/.niche-research-state.json")
    _NICHE_MAX_QUERIES = 5
    _NICHE_TIMEOUT_SECONDS = 30

    async def _niche_research(self) -> dict[str, Any]:
        """Run niche research: select queries, search web, extract insights.

        Gracefully degrades: returns empty dict if anything fails.
        Respects ``_NICHE_TIMEOUT_SECONDS`` total timeout.
        """
        if not self.config.anthropic_api_key:
            logger.info("Niche research skipped: no API key")
            return {}

        start_ms = int(time.monotonic() * 1000)
        deadline = time.monotonic() + self._NICHE_TIMEOUT_SECONDS

        query_config = self._parse_research_queries()
        if not query_config:
            logger.warning("No niche research queries found")
            return {}

        queries = self._select_queries(query_config, max_queries=self._NICHE_MAX_QUERIES)
        if not queries:
            logger.info("No queries eligible this cycle (all recently run)")
            return {}

        # Execute searches
        all_results: list[str] = []
        for query in queries:
            if time.monotonic() >= deadline:
                logger.warning(
                    "Niche research timeout; stopping with %d results",
                    len(all_results),
                )
                break
            try:
                result = self._web_search_single(query)
                if result:
                    all_results.append(f"## Query: {query}\n\n{result}")
            except Exception:
                logger.warning("Web search failed for query: %s", query, exc_info=True)

        if not all_results:
            logger.info("No search results obtained")
            return NicheResearchResult(queries_run=queries).model_dump(mode="json")

        # Extract insights
        try:
            insights = self._extract_insights("\n\n---\n\n".join(all_results))
        except Exception:
            logger.warning("Insight extraction failed", exc_info=True)
            insights = []

        elapsed_ms = int(time.monotonic() * 1000) - start_ms

        trending = [i.topic for i in insights if i.topic][:5]
        angles = [i.relevance_to_camilo for i in insights if i.relevance_to_camilo][:5]

        research_result = NicheResearchResult(
            queries_run=queries,
            insights=insights,
            trending_topics=trending,
            recommended_angles=angles,
            research_duration_ms=elapsed_ms,
        )
        return research_result.model_dump(mode="json")

    def _parse_research_queries(self) -> dict[str, Any]:
        """Parse the YAML block from niche-research-queries.md."""
        if not self._NICHE_QUERIES_PATH.exists():
            return {}

        try:
            content = self._NICHE_QUERIES_PATH.read_text(encoding="utf-8")
        except Exception:
            logger.warning("Failed to read niche research queries file", exc_info=True)
            return {}

        yaml_match = re.search(r"```yaml\s*\n(.*?)```", content, re.DOTALL)
        if not yaml_match:
            return {}

        try:
            parsed = yaml.safe_load(yaml_match.group(1))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            logger.warning("Failed to parse YAML from niche queries file", exc_info=True)
            return {}

    def _select_queries(self, query_config: dict[str, Any], *, max_queries: int = 5) -> list[str]:
        """Pick queries for this cycle, rotating across categories.

        Categories are sorted by staleness (least recently used first).
        Each query respects its rotation cooldown (daily=24h, weekly=168h).
        State is persisted to ``_NICHE_STATE_PATH``.
        """
        state = self._read_niche_state()
        query_history: dict[str, str] = state.get("query_history", {})
        category_last_used: dict[str, str] = state.get("category_last_used", {})
        now = datetime.now(UTC)

        queries_section = query_config.get("queries", {})
        if not isinstance(queries_section, dict):
            return []

        categories = list(queries_section.keys())
        categories.sort(key=lambda c: category_last_used.get(c, ""))

        selected: list[str] = []
        used_categories: set[str] = set()

        for category in categories:
            cat_data = queries_section.get(category, {})
            if not isinstance(cat_data, dict):
                continue

            rotation = cat_data.get("rotation", "daily")
            cooldown_hours = 24 if rotation == "daily" else 168

            cat_queries = cat_data.get("queries", [])
            if not isinstance(cat_queries, list):
                continue

            for q_item in cat_queries:
                query_text = q_item.get("query", "") if isinstance(q_item, dict) else str(q_item)
                if not query_text:
                    continue

                last_run = query_history.get(query_text, "")
                if last_run:
                    try:
                        elapsed_hours = (
                            now - datetime.fromisoformat(last_run)
                        ).total_seconds() / 3600
                        if elapsed_hours < cooldown_hours:
                            continue
                    except (ValueError, TypeError):
                        pass

                selected.append(query_text)
                used_categories.add(category)
                if len(selected) >= max_queries:
                    break

            if len(selected) >= max_queries:
                break

        for q in selected:
            query_history[q] = now.isoformat()
        for cat in used_categories:
            category_last_used[cat] = now.isoformat()

        state["query_history"] = query_history
        state["category_last_used"] = category_last_used
        state["last_run"] = now.isoformat()
        self._write_niche_state(state)

        return selected

    def _read_niche_state(self) -> dict[str, Any]:
        """Read niche research rotation state from disk."""
        if not self._NICHE_STATE_PATH.exists():
            return {}
        try:
            data = json.loads(self._NICHE_STATE_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_niche_state(self, state: dict[str, Any]) -> None:
        """Write niche research rotation state to disk."""
        self._NICHE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._NICHE_STATE_PATH.write_text(
                json.dumps(state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.warning("Failed to write niche research state", exc_info=True)

    def _web_search_single(self, query: str) -> str:
        """Execute a single web search via Claude with the web_search tool."""
        response = self.claude.call(
            cached_prompt=CachedPrompt(
                system_prompt=(
                    "You are a research assistant. Search the web for the "
                    "given query and return a summary of the most relevant "
                    "results. Focus on: AI consulting, LinkedIn thought "
                    "leadership, enterprise AI implementation, and "
                    "builder/practitioner content. For each result, include "
                    "the URL, title, and a brief summary of why it is "
                    "relevant."
                ),
                tools=[{"type": "web_search_20250305"}],
            ),
            messages=[{"role": "user", "content": f"Search for: {query}"}],
            tier="operational",
            max_tokens=2048,
            agent_id=self.agent_name,
        )
        return self._extract_response_text(response)

    def _extract_insights(self, aggregated_results: str) -> list[NicheInsight]:
        """Extract structured NicheInsight objects from search results."""
        prompt = NICHE_EXTRACTION_PROMPT.format(search_results=aggregated_results)
        response = self.claude.call(
            cached_prompt=CachedPrompt(system_prompt=prompt),
            messages=[
                {
                    "role": "user",
                    "content": "Extract insights now. Return a JSON array.",
                }
            ],
            tier="operational",
            max_tokens=2048,
            temperature=0.1,
            agent_id=self.agent_name,
        )

        text = self._extract_response_text(response)
        payload = self._decode_json_payload(text)
        if not isinstance(payload, list):
            return []

        insights: list[NicheInsight] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                insights.append(NicheInsight(**item))
            except (ValidationError, TypeError):
                logger.debug("Skipping invalid insight: %s", item)

        return insights

    async def reason(self, state: MarketingState) -> dict[str, Any]:
        """Reason phase: produce validated ContentDecision objects.

        Uses authority-building framing - decides ONE LinkedIn-first post that
        maps to a content pillar, targets consulting prospects, and uses
        Camilo's builder-philosopher voice.
        """
        self.check_kill_switch()

        products = state.get("product_updates", {})
        knowledge = state.get("knowledge", {})
        memory_context = state.get("memory_context", "")
        analytics = state.get("analytics", {})
        brand = state.get("brand_identity", {})

        decisions: list[ContentDecision] = []
        reasoning = ""

        if self.config.anthropic_api_key:
            strategy_prompt = OPUS_STRATEGY_PROMPT.format(
                brand_identity=format_brand_identity(brand),
                content_pillars=format_content_pillars(brand),
                platform_knowledge=knowledge.get("platforms", "No platform knowledge available."),
                audience_knowledge=knowledge.get(
                    "audience-profiles",
                    "No audience profiles available.",
                ),
                niche_research=self._format_niche_research(state.get("niche_research", {})),
                content_formats=knowledge.get(
                    "content-formats",
                    "No content format guidance available.",
                ),
                viral_frameworks=knowledge.get(
                    "viral-frameworks",
                    "No viral frameworks documented yet.",
                ),
                memory=memory_context or "No memory context available.",
                analytics=(
                    json.dumps(analytics, indent=2, ensure_ascii=True)
                    if analytics
                    else "No analytics yet (cold start)."
                ),
                anti_patterns=format_anti_patterns(brand),
                prior_feedback=state.get("prior_judge_feedback", ""),
            )

            try:
                response = self.claude.call(
                    cached_prompt=CachedPrompt(system_prompt=strategy_prompt),
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Return ONE content decision as a JSON object. "
                                "Include product, platform, content_type, content_pillar, "
                                "topic, hook, framework, reasoning, priority, "
                                "estimated_engagement, and repurpose_notes."
                            ),
                        }
                    ],
                    tier="strategic",
                    max_tokens=2048,
                    temperature=0.2,
                    agent_id=self.agent_name,
                )
                reasoning = self._extract_response_text(response)
                decisions = self._parse_content_decisions(reasoning)
            except Exception:
                logger.exception("Reason stage failed with Claude; using fallback decisions")

        if not decisions:
            decisions = self._fallback_decisions(products)
            if not reasoning:
                reasoning = (
                    "Fallback strategy used because model output was unavailable or invalid."
                )

        decisions = sorted(decisions, key=lambda decision: decision.priority)[:3]

        return {
            "content_decisions": [decision.model_dump(mode="json") for decision in decisions],
            "strategy_reasoning": reasoning,
        }

    def _format_niche_research(self, niche: dict[str, Any]) -> str:
        """Format niche research results for the strategy prompt."""
        if not niche:
            return "No niche research available this cycle."

        parts: list[str] = []
        trending = niche.get("trending_topics", [])
        if trending:
            parts.append("**Trending topics:**")
            for topic in trending[:5]:
                parts.append(f"  - {topic}")

        angles = niche.get("recommended_angles", [])
        if angles:
            parts.append("**Recommended angles:**")
            for angle in angles[:5]:
                parts.append(f"  - {angle}")

        insights = niche.get("insights", [])
        if insights:
            parts.append(f"**{len(insights)} insights extracted from niche research.**")

        return "\n".join(parts) if parts else "No niche research available this cycle."

    async def act(self, state: MarketingState) -> dict[str, Any]:
        """Act phase: generate text per platform and queue for human review."""
        self.check_kill_switch()

        generated_content: list[dict[str, Any]] = []
        post_results: list[dict[str, Any]] = []

        queue_dir = self._ensure_queue_dir()
        knowledge = state.get("knowledge", {})
        products = state.get("product_updates", {})
        brand = state.get("brand_identity", {})
        prior_feedback: str = str(state.get("prior_judge_feedback", ""))

        for index, raw_decision in enumerate(state.get("content_decisions", []), start=1):
            self.check_kill_switch()

            decision = self._coerce_decision(raw_decision)
            if decision is None:
                post_results.append(
                    {
                        "status": "failed",
                        "error": "Invalid content decision payload",
                        "decision": raw_decision,
                    }
                )
                continue

            try:
                generated_text, model_used = self._generate_text_for_decision(
                    decision=decision,
                    knowledge=knowledge,
                    products=products,
                    brand=brand,
                    prior_feedback=self._format_generation_feedback(
                        decision.platform.value, prior_feedback=prior_feedback
                    ),
                )
                piece = GeneratedPiece(
                    piece_id=f"{state.get('cycle_id', 'cycle')}-{index}-{uuid4().hex[:8]}",
                    decision=decision,
                    text=generated_text,
                    platform=decision.platform,
                    model_used=model_used,
                )

                # Quality gate - score before queuing
                brand_anti_phrases = brand.get("anti_patterns", {}).get("language", [])
                quality = score_content(piece, brand_anti_patterns=brand_anti_phrases)

                if not quality.passed:
                    logger.warning(
                        "Content auto-rejected by quality gate: %s (score=%d)",
                        piece.piece_id,
                        quality.score,
                    )
                    post_results.append(
                        {
                            "piece_id": piece.piece_id,
                            "status": "auto_rejected",
                            "quality_score": quality.score,
                            "violations": [v.to_dict() for v in quality.violations],
                            "platform": decision.platform.value,
                            "product": decision.product,
                        }
                    )
                    continue

                queue_path = self._write_queue_item(piece, queue_dir)
                generated_content.append(piece.model_dump(mode="json"))

                # Register with Holus Social API for approval tracking
                schedule_id = None
                has_social_api_key = bool(
                    getattr(self.config, "holus_social_api_key", "")
                    or getattr(self.config, "posting_api_key", "")
                )
                if has_social_api_key:
                    try:
                        schedule_id = await self._schedule_for_approval(piece)
                    except Exception as sched_exc:
                        logger.warning(
                            "schedule_post failed for %s (local queue still valid): %s",
                            piece.piece_id,
                            sched_exc,
                        )

                post_results.append(
                    {
                        "piece_id": piece.piece_id,
                        "status": "pending_review",
                        "quality_score": quality.score,
                        "queue_path": str(queue_path),
                        "schedule_id": schedule_id,
                        "platform": decision.platform.value,
                        "product": decision.product,
                    }
                )

                # Repurpose LinkedIn post to secondary platforms
                try:
                    repurposed = await repurpose_content(
                        original_text=generated_text,
                        decision=decision,
                        claude_client=self.claude,
                        brand=brand,
                        cycle_id=state.get("cycle_id", "cycle"),
                        piece_index=index,
                        agent_id=self.agent_name,
                        prior_feedback=prior_feedback,
                        format_feedback_fn=self._format_generation_feedback,
                    )
                    for rp in repurposed:
                        rp_quality = score_content(rp, brand_anti_patterns=brand_anti_phrases)
                        if not rp_quality.passed:
                            logger.warning(
                                "Repurposed content auto-rejected: %s (%s, score=%d)",
                                rp.piece_id,
                                rp.platform.value,
                                rp_quality.score,
                            )
                            continue
                        rp_queue_path = self._write_queue_item(rp, queue_dir)
                        generated_content.append(rp.model_dump(mode="json"))
                        post_results.append(
                            {
                                "piece_id": rp.piece_id,
                                "status": "pending_review",
                                "quality_score": rp_quality.score,
                                "queue_path": str(rp_queue_path),
                                "platform": rp.platform.value,
                                "product": decision.product,
                            }
                        )
                except Exception as repurpose_exc:
                    logger.warning(
                        "Repurposing failed for decision %d: %s",
                        index,
                        repurpose_exc,
                    )
                    post_results.append(
                        {
                            "status": "failed",
                            "error": f"Repurposing failed: {repurpose_exc}",
                            "decision": decision.model_dump(mode="json"),
                            "phase": "repurposing",
                        }
                    )

            except Exception as exc:
                logger.exception(
                    "Act stage failed for decision %s", decision.model_dump(mode="json")
                )
                post_results.append(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "decision": decision.model_dump(mode="json"),
                    }
                )

        if generated_content:
            try:
                from holus.lineage.recorder import LineageRecorder

                LineageRecorder(queue_dir.parent / "lineage").record_generated_set(
                    str(
                        state.get("strategy_reasoning") or state.get("cycle_id", "marketing-cycle")
                    ),
                    generated_content,
                    group_id=str(state.get("cycle_id", "marketing-cycle")),
                    package={"channel_plan": state.get("content_decisions", [])},
                )
            except Exception:
                logger.exception(
                    "lineage_emission_failed",
                    extra={"group_id": state.get("cycle_id")},
                )

        return {
            "generated_content": generated_content,
            "post_results": post_results,
        }

    async def render(self, state: MarketingState) -> dict[str, Any]:
        """Render phase: produce visual attachments for pieces with visual intent.

        Checks each generated piece for visual content_type (CAROUSEL, VIDEO_REEL)
        or content_pillar suggesting visuals (ai_frameworks, results_proof).
        Renders matching pieces via the visual pipeline and updates their
        visual_attachment_path and visual_format fields. Text-only pieces pass
        through unchanged. Errors are logged and the piece stays text-only.
        """
        self.check_kill_switch()

        generated_content: list[dict[str, Any]] = list(state.get("generated_content", []))
        if not generated_content:
            return {"generated_content": generated_content}

        rendered_dir = Path("data/rendered")
        rendered_dir.mkdir(parents=True, exist_ok=True)

        for piece_data in generated_content:
            decision = piece_data.get("decision", {})
            content_type = str(decision.get("content_type", "")).lower()
            content_pillar = str(decision.get("content_pillar", "")).lower()
            piece_id = piece_data.get("piece_id", "unknown")
            text = piece_data.get("text", "")

            # Determine if this piece needs visual rendering
            # video_reel is excluded - video rendering is not yet built
            is_carousel = content_type == "carousel"
            is_visual_pillar = content_pillar in ("ai_frameworks", "results_proof")

            if not (is_carousel or is_visual_pillar):
                continue

            try:
                from holus.visual import (
                    BrandVisualIdentityLoader,
                    render_carousel_visual,
                    render_visual,
                )
                from holus.visual.spec_converter import (
                    carousel_spec_to_slides,
                    insight_to_spec,
                )

                loader = BrandVisualIdentityLoader()
                brand_config = loader.load()

                if is_carousel:
                    # Build a carousel spec from the content
                    carousel_data = {
                        "slides": [
                            {
                                "type": "hook",
                                "variables": {
                                    "headline": decision.get("hook", decision.get("topic", "")),
                                },
                            },
                            {
                                "type": "body",
                                "variables": {
                                    "body": text[:500],
                                },
                            },
                            {
                                "type": "cta",
                                "variables": {
                                    "headline": "Follow for more",
                                },
                            },
                        ],
                    }
                    carousel_spec = carousel_spec_to_slides(carousel_data)
                    output_bytes = await render_carousel_visual(
                        carousel_spec, brand_config=brand_config
                    )
                    ext = "pdf"
                    output_path = rendered_dir / f"{piece_id}.pdf"
                else:
                    # Single image for visual pillar content (quote/stat graphic)
                    hook = decision.get("hook", "")
                    spec = insight_to_spec(
                        text=text[:300],
                        quote=hook if hook else None,
                    )
                    output_bytes = await render_visual(spec, brand_config=brand_config)
                    ext = "png"
                    output_path = rendered_dir / f"{piece_id}.png"

                output_path.write_bytes(output_bytes)
                piece_data["visual_attachment_path"] = str(output_path)
                piece_data["visual_format"] = ext

                # Update queue file on disk (act already wrote it without visual data)
                queue_file = Path("data/content-queue") / f"{piece_id}.yaml"
                if not queue_file.exists():
                    queue_file = Path("data/content-queue") / f"{piece_id}.json"
                if queue_file.exists():
                    import json as _json

                    import yaml

                    _text = queue_file.read_text(encoding="utf-8")
                    queue_data = (
                        _json.loads(_text)
                        if queue_file.suffix == ".json"
                        else yaml.safe_load(_text)
                    ) or {}
                    if ext == "pdf":
                        queue_data["rendered_pdf_path"] = str(output_path)
                        queue_data["media_type"] = "document"
                    else:
                        queue_data["rendered_image_path"] = str(output_path)
                        queue_data["media_type"] = "image"
                    queue_data["visual_format"] = ext
                    queue_file.write_text(
                        yaml.dump(queue_data, default_flow_style=False, sort_keys=False)
                    )

                logger.info(
                    "Rendered visual for piece %s: %s (%s)",
                    piece_id,
                    output_path,
                    ext,
                )

            except Exception:
                logger.warning(
                    "Visual rendering failed for piece %s; piece stays text-only",
                    piece_id,
                    exc_info=True,
                )

        return {"generated_content": generated_content}

    async def evaluate(self, state: MarketingState) -> dict[str, Any]:
        """Evaluate phase: append cycle entries to trajectory.jsonl."""
        self.check_kill_switch()

        trajectory = TrajectoryLogger(self._TRAJECTORY_PATH)
        cycle_id = state.get("cycle_id", "")
        strategy_reasoning = state.get("strategy_reasoning", "")

        logged_entries = 0

        for content in state.get("generated_content", []):
            self.check_kill_switch()

            decision_data = content.get("decision", {})
            task_summary = (
                f"{decision_data.get('content_type', 'content')} about "
                f"{decision_data.get('topic', 'unknown topic')} for "
                f"{decision_data.get('platform', 'unknown platform')}"
            )

            trajectory.append(
                TrajectoryEntry(
                    agent_id=self.agent_name,
                    task_type="content_creation",
                    task_summary=task_summary,
                    status="success",
                    model_used=str(content.get("model_used", "")),
                    metadata={
                        "cycle_id": cycle_id,
                        "product": decision_data.get("product"),
                        "platform": decision_data.get("platform"),
                        "content_type": decision_data.get("content_type"),
                        "reasoning": decision_data.get("reasoning"),
                        "strategy_context": strategy_reasoning,
                        "piece_id": content.get("piece_id"),
                        "status": content.get("status"),
                    },
                )
            )
            logged_entries += 1

        for result in state.get("post_results", []):
            self.check_kill_switch()
            if result.get("status") != "failed":
                continue

            decision_data = result.get("decision", {})
            trajectory.append(
                TrajectoryEntry(
                    agent_id=self.agent_name,
                    task_type="content_creation",
                    task_summary=(
                        f"failed content generation for "
                        f"{decision_data.get('platform', 'unknown platform')}"
                    ),
                    status="error",
                    error_message=str(result.get("error", "unknown error")),
                    metadata={
                        "cycle_id": cycle_id,
                        "decision": decision_data,
                        "strategy_context": strategy_reasoning,
                    },
                )
            )
            logged_entries += 1

        evaluation = {
            "logged": True,
            "entries_written": logged_entries,
            "pieces_created": len(state.get("generated_content", [])),
            "queue_size_before": state.get("queue_size_before", 0),
            "queue_size_after": len(self._queue_files()),
            "cycle_id": cycle_id,
        }

        return {"evaluation": evaluation}

    def _read_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            logger.warning("YAML file not found: %s", path)
            return {}
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed reading YAML file: %s", path)
            return {}
        return data if isinstance(data, dict) else {}

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            logger.warning("Text file not found: %s", path)
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            logger.exception("Failed reading text file: %s", path)
            return ""

    def _read_knowledge_files(self, directory: Path) -> dict[str, str]:
        if not directory.exists():
            logger.warning("Knowledge directory not found: %s", directory)
            return {}

        knowledge: dict[str, str] = {}
        for file_path in sorted(directory.glob("*.md")):
            try:
                knowledge[file_path.stem] = file_path.read_text(encoding="utf-8")
            except Exception:
                logger.exception("Failed reading knowledge file: %s", file_path)
        return knowledge

    def _queue_files(self) -> list[Path]:
        if not self._QUEUE_DIR.exists():
            return []
        files = list(self._QUEUE_DIR.glob("*.yaml")) + list(self._QUEUE_DIR.glob("*.json"))
        return sorted(files)

    def _ensure_queue_dir(self) -> Path:
        self._QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        return self._QUEUE_DIR

    def _write_queue_item(self, piece: GeneratedPiece, queue_dir: Path) -> Path:
        """Write a content piece to the queue as YAML (matches content_queue.py)."""
        path = queue_dir / f"{piece.piece_id}.yaml"
        data: dict[str, Any] = {
            "piece_id": piece.piece_id,
            "product": piece.decision.product,
            "platform": piece.platform.value,
            "content_type": piece.decision.content_type.value,
            "topic": piece.decision.topic,
            "text": piece.text,
            "reasoning": piece.decision.reasoning,
            "model_used": piece.model_used,
            "generated_at": piece.generated_at.isoformat(),
            "status": "pending_review",
        }

        # Pass through visual rendering fields if present
        if piece.visual_attachment_path:
            visual_path = piece.visual_attachment_path
            if visual_path.endswith(".pdf"):
                data["rendered_pdf_path"] = visual_path
                data["media_type"] = "document"
            elif visual_path.endswith(".png"):
                data["rendered_image_path"] = visual_path
                data["media_type"] = "image"
            data["visual_format"] = piece.visual_format

        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        return path

    def _parse_content_decisions(self, response_text: str) -> list[ContentDecision]:
        payload = self._decode_json_payload(response_text)
        if payload is None:
            return []

        items: list[dict[str, Any]]
        if isinstance(payload, list):
            items = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            items = [payload]
        else:
            return []

        decisions: list[ContentDecision] = []
        for item in items:
            decision = self._coerce_decision(item)
            if decision is not None:
                decisions.append(decision)
        return decisions

    def _coerce_decision(self, payload: Any) -> ContentDecision | None:
        if not isinstance(payload, dict):
            return None

        platform_raw = str(payload.get("platform", "linkedin")).strip().lower()
        content_type_raw = str(payload.get("content_type", "tutorial")).strip().lower()

        platform = self._PLATFORM_ALIASES.get(platform_raw, Platform.LINKEDIN)
        content_type = self._CONTENT_TYPE_ALIASES.get(content_type_raw, ContentType.TUTORIAL)

        priority_value = 1
        try:
            priority_value = int(payload.get("priority", 1) or 1)
        except (TypeError, ValueError):
            priority_value = 1

        estimated_engagement = str(payload.get("estimated_engagement", "medium")).strip()

        try:
            return ContentDecision(
                product=str(payload.get("product", "pilaster")).strip().lower(),
                platform=platform,
                content_type=content_type,
                content_pillar=str(payload.get("content_pillar", "builder_stories")).strip(),
                topic=str(payload.get("topic", "Product tutorial")).strip(),
                hook=str(payload.get("hook", "")).strip(),
                framework=str(payload.get("framework", "original")).strip(),
                reasoning=str(payload.get("reasoning", "Value-first educational content")).strip(),
                priority=priority_value,
                estimated_engagement=estimated_engagement,
                repurpose_notes=str(payload.get("repurpose_notes", "")).strip(),
            )
        except (ValidationError, ValueError, TypeError):
            logger.warning("Skipping invalid content decision: %s", payload)
            return None

    def _fallback_decisions(self, products_data: dict[str, Any]) -> list[ContentDecision]:
        """Generate fallback decisions with authority-building framing.

        Products are used as proof points for consulting expertise,
        not as the primary pitch.
        """
        products = products_data.get("products", {})
        if not isinstance(products, dict):
            products = {}

        # Authority-framing fallback: one LinkedIn builder story per product
        decisions: list[ContentDecision] = []
        for index, (product_key, _product_data) in enumerate(products.items(), start=1):
            decisions.append(
                ContentDecision(
                    product=product_key,
                    platform=Platform.LINKEDIN,
                    content_type=ContentType.TUTORIAL,
                    content_pillar="builder_stories",
                    topic=f"What I learned building {product_key.capitalize()} - lessons for AI teams",
                    hook=f"I built {product_key.capitalize()} from scratch. Here's what surprised me.",
                    framework="original",
                    reasoning="Fallback strategy: builder stories demonstrate consulting expertise.",
                    priority=min(index, 3),
                    estimated_engagement="medium",
                )
            )
            if len(decisions) == 3:
                break

        if decisions:
            return decisions

        return [
            ContentDecision(
                product="pilaster",
                platform=Platform.LINKEDIN,
                content_type=ContentType.TUTORIAL,
                content_pillar="builder_stories",
                topic="What I learned building 3 AI products - patterns every team should know",
                hook="I built 3 AI products in production. Here's what I wish someone told me.",
                framework="original",
                reasoning="Cold-start fallback: builder story as consulting proof point.",
                priority=1,
                estimated_engagement="medium",
            )
        ]

    def _generate_text_for_decision(
        self,
        *,
        decision: ContentDecision,
        knowledge: dict[str, str],
        products: dict[str, Any],
        brand: dict[str, Any] | None = None,
        prior_feedback: str = "",
    ) -> tuple[str, str]:
        """Generate content text for a decision using authority-building prompts.

        For LinkedIn posts, uses the specialist chain (hook-architect → storyteller
        → voice-guardian → cta-strategist) for higher quality output.
        Falls back to monolithic Sonnet prompt if any specialist fails.
        Falls back to template text when API key is unavailable.
        """
        brand = brand or {}
        products_dict = products.get("products", {})

        if not self.config.anthropic_api_key:
            fallback_text = self._fallback_content_text(decision)
            return self._enforce_platform_limit(
                fallback_text, decision.platform
            ), "template-fallback"

        # Try specialist chain for text-heavy platforms
        chain_platforms = {Platform.LINKEDIN, Platform.INSTAGRAM, Platform.THREADS}
        if decision.platform in chain_platforms:
            try:
                text = self._specialist_chain(
                    decision=decision, brand=brand, prior_feedback=prior_feedback
                )
                if text and len(text) > 50:
                    return self._enforce_platform_limit(
                        text, decision.platform
                    ), f"specialist-chain/{self.config.sonnet_model}"
            except Exception as exc:
                logger.warning(
                    "Specialist chain failed, falling back to monolithic prompt: %s", exc
                )

        # Monolithic prompt fallback
        product_info = format_product_info(decision.product, products_dict)
        system_prompt = SONNET_CONTENT_PROMPT.format(
            topic=decision.topic,
            content_pillar=decision.content_pillar,
            hook=decision.hook or "(generate an engaging hook)",
            framework=decision.framework,
            reasoning=decision.reasoning,
            voice=format_voice(brand),
            positioning=format_positioning(brand),
            product_info=product_info,
            anti_patterns=format_anti_patterns(brand),
            prior_feedback=prior_feedback or "No prior feedback for this platform.",
        )

        response = self.claude.call(
            cached_prompt=CachedPrompt(system_prompt=system_prompt),
            messages=[{"role": "user", "content": "Generate the final content now."}],
            tier="operational",
            max_tokens=1536,
            temperature=0.4,
            agent_id=self.agent_name,
        )

        text = self._extract_response_text(response).strip()
        if not text:
            text = self._fallback_content_text(decision)

        return self._enforce_platform_limit(text, decision.platform), self.config.sonnet_model

    # ------------------------------------------------------------------
    # Specialist chain (hook → storyteller → voice-guardian → CTA)
    # ------------------------------------------------------------------

    _GENERATION_PREFIX = (
        "IMPORTANT: You are in GENERATION MODE. Do NOT search for, read, or access "
        "any files. Do NOT use any tools. Generate content directly based on the brief "
        "provided and the instructions in your system prompt. Respond with text only.\n\n"
    )

    _PLATFORM_STORY_HINTS: ClassVar[dict[str, str]] = {
        "linkedin": "Write a professional narrative (800-1500 chars). Use arrow bullets, standalone pivot lines, builder-philosopher tone.",
        "instagram": "Write a conversational caption (600-1200 chars). More personal, visual language. End with 10-15 relevant hashtags on a separate line. Use line breaks for readability.",
        "threads": "Write a punchy, casual take (300-500 chars). Conversational tone, no hashtags. Think Twitter energy but with more room.",
    }

    _PLATFORM_CTA_HINTS: ClassVar[dict[str, str]] = {
        "linkedin": "Professional CTAs: questions that invite discussion, polls, or direct profile visits.",
        "instagram": 'Instagram CTAs: "Link in bio", save/share prompts, comment triggers. Never direct URLs in captions.',
        "threads": "Threads CTAs: short engagement hooks, repost prompts, casual questions.",
    }

    def _specialist_chain(
        self,
        *,
        decision: ContentDecision,
        brand: dict[str, Any],
        prior_feedback: str = "",
    ) -> str:
        """Run the specialist chain: hook → storyteller → voice-guardian → CTA.

        Returns the assembled post text or raises on failure.
        """
        from holus.core.prompt_loader import PromptLoader

        loader = PromptLoader()

        # Step 1: Hook Architect
        hook_prompt = loader.get_prompt("hook-architect")
        hook_input = (
            f"{self._GENERATION_PREFIX}"
            f"Content brief:\n"
            f"- Content pillar: {decision.content_pillar}\n"
            f"- Core claim: {decision.topic}\n"
            f"- Product: {decision.product}\n"
            f"- Platform: {decision.platform.value}\n"
        )
        hook_resp = self.claude.call(
            cached_prompt=CachedPrompt(system_prompt=hook_prompt),
            messages=[{"role": "user", "content": hook_input}],
            tier="operational",
            max_tokens=1000,
            temperature=0.4,
            agent_id=f"{self.agent_name}/hook-architect",
        )
        hook_output = self._extract_response_text(hook_resp).strip()
        best_hook = self._extract_hook_from_output(hook_output, decision)
        logger.info("Specialist chain: hook selected (%d chars)", len(best_hook))

        # Step 2: Storyteller
        story_prompt = loader.get_prompt("storyteller")
        feedback_section = ""
        if prior_feedback and prior_feedback != "No prior feedback for this platform.":
            feedback_section = f"\n\nPrior judge feedback (avoid these mistakes):\n{prior_feedback}"
        story_input = (
            f"{self._GENERATION_PREFIX}"
            f"Content brief:\n"
            f"- Content pillar: {decision.content_pillar}\n"
            f"- Core claim: {decision.topic}\n"
            f"- Product: {decision.product}\n"
            f"- Platform: {decision.platform.value}\n"
            f"- Hook (from hook-architect): {best_hook}\n\n"
            f"Write the narrative body. Do NOT include the hook itself.\n\n"
            f"Platform guidance: {self._PLATFORM_STORY_HINTS.get(decision.platform.value, '')}"
            f"{feedback_section}"
        )
        story_resp = self.claude.call(
            cached_prompt=CachedPrompt(system_prompt=story_prompt),
            messages=[{"role": "user", "content": story_input}],
            tier="operational",
            max_tokens=1500,
            temperature=0.4,
            agent_id=f"{self.agent_name}/storyteller",
        )
        story_output = self._extract_response_text(story_resp).strip()
        body = self._extract_body_from_output(story_output)
        if not body:
            raise ValueError("Storyteller returned empty body")
        logger.info("Specialist chain: body generated (%d chars)", len(body))

        # Step 3: Voice Guardian (GATE)
        guardian_prompt = loader.get_prompt("voice-guardian")
        full_draft = f"{best_hook}\n\n{body}"
        guardian_input = (
            f"{self._GENERATION_PREFIX}"
            f"Review the following {decision.platform.value} post for brand consistency:\n\n"
            f"---\n{full_draft}\n---\n\n"
            f"Apply all checks from brand.yaml anti_patterns and voice-profile.md."
        )
        guardian_resp = self.claude.call(
            cached_prompt=CachedPrompt(system_prompt=guardian_prompt),
            messages=[{"role": "user", "content": guardian_input}],
            tier="classification",
            max_tokens=800,
            temperature=0.0,
            agent_id=f"{self.agent_name}/voice-guardian",
        )
        guardian_output = self._extract_response_text(guardian_resp).strip()
        upper = guardian_output.upper()
        gate_passed = "PASS" in upper
        if "FAIL" in upper:
            gate_passed = False
        logger.info("Specialist chain: voice guardian %s", "PASS" if gate_passed else "FAIL")

        if not gate_passed:
            # If voice guardian fails, fall back to monolithic prompt
            raise ValueError(f"Voice guardian FAIL: {guardian_output[:200]}")

        # Step 4: CTA Strategist
        cta_prompt = loader.get_prompt("cta-strategist")
        cta_input = (
            f"{self._GENERATION_PREFIX}"
            f"Content brief:\n"
            f"- Content pillar: {decision.content_pillar}\n"
            f"- Hook: {best_hook}\n"
            f"- Body (first 400 chars): {body[:400]}\n\n"
            f"Design 2-3 CTA options for this {decision.platform.value} post.\n\n"
            f"Platform guidance: {self._PLATFORM_CTA_HINTS.get(decision.platform.value, '')}"
        )
        cta_resp = self.claude.call(
            cached_prompt=CachedPrompt(system_prompt=cta_prompt),
            messages=[{"role": "user", "content": cta_input}],
            tier="operational",
            max_tokens=800,
            temperature=0.4,
            agent_id=f"{self.agent_name}/cta-strategist",
        )
        cta_output = self._extract_response_text(cta_resp).strip()
        cta_text = self._extract_cta_from_output(cta_output)

        # Assemble: hook + body + CTA
        assembled = f"{best_hook}\n\n{body}"
        if cta_text:
            assembled += f"\n\n{cta_text}"

        logger.info("Specialist chain: assembled post (%d chars)", len(assembled))
        return assembled

    def _extract_hook_from_output(self, output: str, decision: ContentDecision) -> str:
        """Extract the best hook from hook-architect JSON output."""
        clean = self._strip_code_fences(output)
        try:
            data = json.loads(clean)
            rec_idx = data["recommended"]["index"]
            hook_text: str = data["hooks"][rec_idx]["text"]
            return hook_text
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            pass
        # Regex fallback: find first "text" value
        match = re.search(r'"text":\s*"([^"]+)"', output)
        if match:
            return match.group(1)
        # Use the decision hook or topic
        return decision.hook or decision.topic

    def _extract_body_from_output(self, output: str) -> str:
        """Extract the narrative body from storyteller JSON or plain text."""
        clean = self._strip_code_fences(output)
        try:
            data = json.loads(clean)
            body: str = data.get("body", clean)
            return body
        except (json.JSONDecodeError, TypeError):
            return output

    def _extract_cta_from_output(self, output: str) -> str:
        """Extract the first CTA text from cta-strategist JSON output."""
        clean = self._strip_code_fences(output)
        try:
            data = json.loads(clean)
            options = data.get("options", [])
            if options and isinstance(options[0], dict):
                cta_text: str = options[0].get("text", "")
                return cta_text
        except (json.JSONDecodeError, TypeError):
            pass
        return ""

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove markdown code fences from JSON output."""
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            return "\n".join(lines)
        return stripped

    def _fallback_content_text(self, decision: ContentDecision) -> str:
        """Generate fallback content with authority-building voice."""
        hook = decision.hook or decision.topic

        if decision.platform is Platform.TWITTER:
            return (
                f"{hook}\n\n"
                f"I learned this building {decision.product}. "
                "One pattern that transfers to any AI team."
            )

        if decision.platform is Platform.LINKEDIN:
            return (
                f"{hook}\n\n"
                f"I built {decision.product} from scratch. "
                "Here's the framework that actually worked:\n\n"
                "1) Start with the smallest testable workflow\n"
                "2) Measure the baseline before optimizing\n"
                "3) Change one variable per iteration\n\n"
                "Most teams skip step 2. That's where the expensive mistakes happen.\n\n"
                "What's the biggest bottleneck in your AI implementation?"
            )

        return (
            f"{hook}\n\n"
            f"Building {decision.product} taught me this: focus on one repeatable pattern "
            "and get it right before scaling.\n\n"
            "What are you building?"
        )

    def _enforce_platform_limit(self, text: str, platform: Platform) -> str:
        limit = self._PLATFORM_CHAR_LIMITS.get(platform)
        if limit is None or len(text) <= limit:
            return text

        trimmed = text[: max(limit - 3, 0)].rstrip()
        return f"{trimmed}..."

    def _extract_response_text(self, response: Any) -> str:
        blocks = getattr(response, "content", [])
        parts: list[str] = []
        for block in blocks:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts).strip()

    def _decode_json_payload(self, text: str) -> Any | None:
        stripped = text.strip()
        if not stripped:
            return None

        direct = self._try_json_loads(stripped)
        if direct is not None:
            return direct

        fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL)
        for block in fenced_blocks:
            parsed = self._try_json_loads(block.strip())
            if parsed is not None:
                return parsed

        left = stripped.find("[")
        right = stripped.rfind("]")
        if left != -1 and right != -1 and right > left:
            parsed = self._try_json_loads(stripped[left : right + 1])
            if parsed is not None:
                return parsed

        left = stripped.find("{")
        right = stripped.rfind("}")
        if left != -1 and right != -1 and right > left:
            parsed = self._try_json_loads(stripped[left : right + 1])
            if parsed is not None:
                return parsed

        return None

    def _try_json_loads(self, text: str) -> Any | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
