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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, TypedDict
from uuid import uuid4

import yaml
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from holus.agents.base import BaseAgent
from holus.agents.marketing.models import ContentDecision, ContentType, GeneratedPiece, Platform
from holus.agents.marketing.prompts import OPUS_STRATEGY_PROMPT, SONNET_CONTENT_PROMPT
from holus.integrations.claude_api.client import CachedPrompt
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
            "content_decisions": [],
            "strategy_reasoning": "",
            "generated_content": [],
            "post_results": [],
            "evaluation": {},
            "error": None,
        }

    async def observe(self, state: MarketingState) -> dict[str, Any]:
        """Observe phase: load products config, knowledge base, and memory."""
        self.check_kill_switch()

        products = self._read_yaml(self._PRODUCTS_PATH)
        knowledge = self._read_knowledge_files(self._KNOWLEDGE_DIR)
        memory_context = self._read_text(self._MEMORY_PATH)

        return {
            "product_updates": products,
            "knowledge": knowledge,
            "memory_context": memory_context,
            "analytics": state.get("analytics", {}),
            "queue_size_before": len(self._queue_files()),
        }

    async def reason(self, state: MarketingState) -> dict[str, Any]:
        """Reason phase: produce validated ContentDecision objects."""
        self.check_kill_switch()

        products = state.get("product_updates", {})
        knowledge = state.get("knowledge", {})
        memory_context = state.get("memory_context", "")
        analytics = state.get("analytics", {})

        decisions: list[ContentDecision] = []
        reasoning = ""

        if self.config.anthropic_api_key:
            strategy_prompt = OPUS_STRATEGY_PROMPT.format(
                products=json.dumps(products, indent=2, ensure_ascii=True),
                platform_knowledge=knowledge.get("platforms", "No platform knowledge available."),
                audience_knowledge=knowledge.get(
                    "audience-profiles",
                    "No audience profiles available.",
                ),
                content_formats=knowledge.get(
                    "content-formats",
                    "No content format guidance available.",
                ),
                memory=memory_context or "No memory context available.",
                analytics=(
                    json.dumps(analytics, indent=2, ensure_ascii=True)
                    if analytics
                    else "No analytics yet (cold start)."
                ),
            )

            try:
                response = self.claude.call(
                    cached_prompt=CachedPrompt(system_prompt=strategy_prompt),
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Return 1-3 prioritized content decisions as a JSON array. "
                                "Include product, platform, content_type, topic, reasoning, "
                                "priority, and estimated_engagement."
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

    async def act(self, state: MarketingState) -> dict[str, Any]:
        """Act phase: generate text per platform and queue for human review."""
        self.check_kill_switch()

        generated_content: list[dict[str, Any]] = []
        post_results: list[dict[str, Any]] = []

        queue_dir = self._ensure_queue_dir()
        knowledge = state.get("knowledge", {})
        products = state.get("product_updates", {})

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
                )
                piece = GeneratedPiece(
                    piece_id=f"{state.get('cycle_id', 'cycle')}-{index}-{uuid4().hex[:8]}",
                    decision=decision,
                    text=generated_text,
                    platform=decision.platform,
                    model_used=model_used,
                )
                queue_path = self._write_queue_item(piece, queue_dir)
                generated_content.append(piece.model_dump(mode="json"))
                post_results.append(
                    {
                        "piece_id": piece.piece_id,
                        "status": "pending_review",
                        "queue_path": str(queue_path),
                        "platform": decision.platform.value,
                        "product": decision.product,
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
        import yaml

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
                topic=str(payload.get("topic", "Product tutorial")).strip(),
                reasoning=str(payload.get("reasoning", "Value-first educational content")).strip(),
                priority=priority_value,
                estimated_engagement=estimated_engagement,
            )
        except (ValidationError, ValueError, TypeError):
            logger.warning("Skipping invalid content decision: %s", payload)
            return None

    def _fallback_decisions(self, products_data: dict[str, Any]) -> list[ContentDecision]:
        products = products_data.get("products", {})
        if not isinstance(products, dict):
            products = {}

        decisions: list[ContentDecision] = []
        for index, (product_key, product_data) in enumerate(products.items(), start=1):
            platform = Platform.LINKEDIN
            if isinstance(product_data, dict):
                platforms_raw = product_data.get("platforms", [])
                if isinstance(platforms_raw, list) and platforms_raw:
                    candidate = str(platforms_raw[0]).strip().lower()
                    platform = self._PLATFORM_ALIASES.get(candidate, Platform.LINKEDIN)

            decisions.append(
                ContentDecision(
                    product=product_key,
                    platform=platform,
                    content_type=ContentType.TUTORIAL,
                    topic=f"{product_key.capitalize()} quick-start tutorial",
                    reasoning="Fallback strategy prioritizes evergreen educational content.",
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
                topic="How to start with Pilaster in 10 minutes",
                reasoning="Cold-start fallback when config/model output is unavailable.",
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
    ) -> tuple[str, str]:
        platform_guidelines = knowledge.get(
            "platforms",
            "Use concise, value-first content with a clear CTA.",
        )
        product_info = self._product_info(decision.product, products)

        if not self.config.anthropic_api_key:
            fallback_text = self._fallback_content_text(decision)
            return self._enforce_platform_limit(
                fallback_text, decision.platform
            ), "template-fallback"

        system_prompt = SONNET_CONTENT_PROMPT.format(
            product=decision.product,
            platform=decision.platform.value,
            content_type=decision.content_type.value,
            topic=decision.topic,
            reasoning=decision.reasoning,
            platform_guidelines=platform_guidelines,
            product_info=product_info,
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

    def _product_info(self, product_key: str, products_data: dict[str, Any]) -> str:
        products = products_data.get("products", {})
        if not isinstance(products, dict):
            return "No product details available."

        product = products.get(product_key, {})
        if not isinstance(product, dict):
            return "No product details available."

        name = str(product.get("name", product_key)).strip()
        tagline = str(product.get("tagline", "")).strip()
        description = str(product.get("description", "")).strip()
        audience = str(product.get("audience", "")).strip()
        pain_point = str(product.get("pain_point", "")).strip()

        return "\n".join(
            [
                f"Name: {name}",
                f"Tagline: {tagline or 'N/A'}",
                f"Description: {description or 'N/A'}",
                f"Audience: {audience or 'N/A'}",
                f"Pain point: {pain_point or 'N/A'}",
            ]
        )

    def _fallback_content_text(self, decision: ContentDecision) -> str:
        if decision.platform is Platform.TWITTER:
            return (
                f"{decision.topic}\n\n"
                f"Built for {decision.product} users: one practical step you can apply today.\n"
                "Reply with your biggest blocker and I will share a tailored walkthrough."
            )

        if decision.platform is Platform.LINKEDIN:
            return (
                f"Most teams overcomplicate {decision.topic.lower()}.\n\n"
                f"Here is a practical framework we use in {decision.product}:\n"
                "1) Start with the fastest testable workflow\n"
                "2) Capture the baseline result\n"
                "3) Improve one variable per iteration\n\n"
                "Which step slows your team down the most?"
            )

        return (
            f"{decision.topic}\n\n"
            f"Practical insight for {decision.product}: focus on one repeatable action "
            "you can apply this week.\n"
            "Save this and try it today."
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
