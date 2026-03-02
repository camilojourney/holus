"""Marketing agent LangGraph workflow.

ReAct loop:
  1. observe  -- read products config, knowledge files, and memory.
  2. reason   -- produce structured content decisions.
  3. act      -- generate platform-specific text and queue for review.
  4. evaluate -- append decision/execution metadata to trajectory log.
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


class MarketingAgent(BaseAgent):
    """Primary marketing strategist agent."""

    agent_name = "marketing-agent"

    _PRODUCTS_PATH = Path("config/products.yaml")
    _BRAND_PATH = Path("config/brand.yaml")
    _KNOWLEDGE_DIR = Path(".self-improvement/knowledge/current")
    _MEMORY_PATH = Path(".self-improvement/MEMORY.md")
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
        """Construct the marketing observe -> reason -> act -> evaluate graph."""
        graph = StateGraph(MarketingState)

        graph.add_node("observe", self.observe)
        graph.add_node("reason", self.reason)
        graph.add_node("act", self.act)
        graph.add_node("evaluate", self.evaluate)

        graph.add_edge(START, "observe")
        graph.add_edge("observe", "reason")
        graph.add_edge("reason", "act")
        graph.add_edge("act", "evaluate")
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
        }

    async def observe(self, state: MarketingState) -> dict[str, Any]:
        """Observe phase: load config, knowledge, memory, brand, analytics, and niche research."""
        self.check_kill_switch()

        products = self._read_yaml(self._PRODUCTS_PATH)
        knowledge = self._read_knowledge_files(self._KNOWLEDGE_DIR)
        memory_context = self._read_text(self._MEMORY_PATH)
        brand_identity = self._load_brand_identity()

        # Analytics from social-media API (graceful degradation)
        analytics: dict[str, Any] = {}
        try:
            analytics = await self._fetch_analytics()
        except Exception:
            logger.warning("Analytics fetch failed; continuing without it", exc_info=True)

        # Niche research (graceful degradation)
        niche_research: dict[str, Any] = {}
        try:
            niche_research = await self._niche_research()
        except Exception:
            logger.warning("Niche research failed; continuing without it", exc_info=True)

        return {
            "product_updates": products,
            "knowledge": knowledge,
            "memory_context": memory_context,
            "analytics": analytics,
            "queue_size_before": len(self._queue_files()),
            "brand_identity": brand_identity,
            "niche_research": niche_research,
        }

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
        """Fetch recent analytics from social-media-automatization API.

        Returns a dict with ``summary`` (aggregate stats) and ``top_posts``
        (best performing recent posts).  Returns empty dict if the API is
        unreachable or credentials are missing — the agent continues without
        analytics (cold start behavior).
        """
        if not self.config.posting_api_key:
            logger.info("Analytics fetch skipped: no POSTING_API_KEY configured")
            return {}

        async with SocialMediaClient(
            base_url=self.config.social_media_api_base_url,
            api_key=self.config.posting_api_key,
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

    # -- Niche research sub-step -----------------------------------------------

    _NICHE_QUERIES_PATH = Path(".self-improvement/knowledge/current/niche-research-queries.md")
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

        Uses authority-building framing — decides ONE LinkedIn-first post that
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
                )
                piece = GeneratedPiece(
                    piece_id=f"{state.get('cycle_id', 'cycle')}-{index}-{uuid4().hex[:8]}",
                    decision=decision,
                    text=generated_text,
                    platform=decision.platform,
                    model_used=model_used,
                )

                # Quality gate — score before queuing
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
                post_results.append(
                    {
                        "piece_id": piece.piece_id,
                        "status": "pending_review",
                        "quality_score": quality.score,
                        "queue_path": str(queue_path),
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

        return {
            "generated_content": generated_content,
            "post_results": post_results,
        }

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
        return sorted(self._QUEUE_DIR.glob("*.yaml"))

    def _ensure_queue_dir(self) -> Path:
        self._QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        return self._QUEUE_DIR

    def _write_queue_item(self, piece: GeneratedPiece, queue_dir: Path) -> Path:
        """Write a content piece to the queue as YAML (matches content_queue.py)."""
        path = queue_dir / f"{piece.piece_id}.yaml"
        data = {
            "piece_id": piece.piece_id,
            "product": piece.decision.product,
            "platform": piece.decision.platform.value,
            "content_type": piece.decision.content_type.value,
            "topic": piece.decision.topic,
            "text": piece.text,
            "reasoning": piece.decision.reasoning,
            "generated_at": piece.generated_at.isoformat(),
            "status": "pending_review",
        }
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
                    topic=f"What I learned building {product_key.capitalize()} — lessons for AI teams",
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
                topic="What I learned building 3 AI products — patterns every team should know",
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
    ) -> tuple[str, str]:
        """Generate content text for a decision using authority-building prompts.

        Uses Camilo's voice, brand positioning, and anti-patterns from brand.yaml.
        Falls back to template text when API key is unavailable.
        """
        brand = brand or {}
        products_dict = products.get("products", {})
        product_info = format_product_info(decision.product, products_dict)

        if not self.config.anthropic_api_key:
            fallback_text = self._fallback_content_text(decision)
            return self._enforce_platform_limit(
                fallback_text, decision.platform
            ), "template-fallback"

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
