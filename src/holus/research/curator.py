"""Research curator scoring wrapper."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import yaml

from holus.core.config import HolusConfig
from holus.core.prompt_loader import PromptLoader
from holus.integrations.claude_api.client import CachedPrompt, HolusClaudeClient
from holus.research.models import RawResearchItem, RecommendedAction, ResearchScore

if TYPE_CHECKING:
    from pathlib import Path

PRODUCT_KEYWORDS: dict[str, set[str]] = {
    "pilaster": {"image", "diffusion", "comfyui", "lora", "generation", "visual"},
    "genpeli": {"video", "editing", "caption", "transcription", "shorts", "whisper"},
    "invoz": {"audio", "speech", "voice", "transcription", "api", "ml"},
}
AI_KEYWORDS = {
    "agent",
    "agents",
    "ai",
    "artificial intelligence",
    "benchmark",
    "evaluation",
    "llm",
    "machine learning",
    "model",
    "multimodal",
    "rag",
    "research",
}

ScoreCallable = Callable[[RawResearchItem, str, dict[str, Any]], ResearchScore]
AsyncScoreCallable = Callable[[RawResearchItem, str, dict[str, Any]], Awaitable[ResearchScore]]


class ResearchCurator:
    """Scores research items, with an injectable scorer for tests or LLM wiring."""

    def __init__(
        self,
        *,
        interests: str = "",
        products: dict[str, Any] | None = None,
        scorer: ScoreCallable | AsyncScoreCallable | None = None,
    ) -> None:
        self.interests = interests
        self.products = products or {}
        self._scorer = scorer
        self._fallback_on_scorer_error = bool(getattr(scorer, "uses_heuristic_fallback", False))
        self.fallback_count = 0
        self.fallback_reasons: list[str] = []
        self.scorer_mode = "injected" if scorer is not None else "heuristic"

    async def score(self, item: RawResearchItem) -> ResearchScore:
        if self._scorer is not None:
            try:
                call = self._scorer
                is_async = inspect.iscoroutinefunction(call) or inspect.iscoroutinefunction(
                    type(call).__call__
                )
                if is_async:
                    result = await cast(
                        "Awaitable[ResearchScore]", call(item, self.interests, self.products)
                    )
                else:
                    sync_call = cast("ScoreCallable", call)
                    result = await asyncio.to_thread(sync_call, item, self.interests, self.products)
                    if inspect.isawaitable(result):
                        result = await result
                return ResearchScore.model_validate(result)
            except Exception as exc:
                if not self._fallback_on_scorer_error:
                    raise
                self.fallback_count += 1
                self.fallback_reasons.append(f"{item.item_id}: {exc}")
                return self._heuristic_score(item)
        return self._heuristic_score(item)

    def _heuristic_score(self, item: RawResearchItem) -> ResearchScore:
        text = f"{item.title} {item.summary}".lower()
        matched_products = [
            product
            for product, keywords in PRODUCT_KEYWORDS.items()
            if any(keyword in text for keyword in keywords)
        ]
        topics = sorted(keyword for keyword in AI_KEYWORDS if keyword in text)[:6]
        product_signal = min(1.0, 0.35 * len(matched_products))
        topic_signal = min(0.45, 0.08 * len(topics))
        relevance = min(1.0, product_signal + topic_signal + 0.2)
        novelty = (
            0.7 if any(term in text for term in {"new", "novel", "launch", "released"}) else 0.55
        )
        should_read = min(1.0, relevance * 0.7 + novelty * 0.3)
        recommended_action: RecommendedAction = "candidate" if relevance >= 0.65 else "read_only"
        if relevance < 0.25 and should_read < 0.5:
            recommended_action = "skip"
        key_idea = item.summary or item.title
        why = (
            f"This is relevant to {', '.join(matched_products) or 'the AI portfolio'} "
            f"because it touches {', '.join(topics[:3]) or 'current AI practice'}."
        )
        return ResearchScore(
            item_id=item.item_id,
            relevance=round(relevance, 3),
            novelty=round(novelty, 3),
            should_read=round(should_read, 3),
            matched_products=matched_products,
            topics=topics,
            why_it_matters=why,
            key_idea=key_idea[:500],
            recommended_action=recommended_action,
        )


@dataclass
class AgentBackedResearchScorer:
    """Research scorer backed by the registered research-curator prompt."""

    repo_root: Path
    config: HolusConfig
    uses_heuristic_fallback: bool = True

    def __post_init__(self) -> None:
        self._prompt = PromptLoader(repo_root=self.repo_root).get_prompt(
            "research-curator",
            fallback="Score the research item and return only a ResearchScore object.",
        )
        self._client = HolusClaudeClient(
            api_key=self.config.anthropic_api_key or None,
            base_url=self.config.anthropic_base_url or None,
            model_map={
                "strategic": self.config.opus_model,
                "operational": self.config.sonnet_model,
                "classification": self.config.haiku_model,
            },
        )

    def __call__(
        self,
        item: RawResearchItem,
        interests: str,
        products: dict[str, Any],
    ) -> ResearchScore:
        response = self._client.call(
            CachedPrompt(system_prompt=self._prompt),
            [
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "item": item.model_dump(mode="json"),
                            "interests": interests,
                            "products": products,
                        },
                        sort_keys=True,
                    ),
                }
            ],
            tier="operational",
            max_tokens=1200,
            temperature=0.0,
            agent_id="research-curator",
        )
        text = _message_text(response)
        payload = yaml.safe_load(text)
        return ResearchScore.model_validate(payload)


def default_agent_scorer(repo_root: Path) -> AgentBackedResearchScorer | None:
    """Return an agent scorer when credentials are configured, else deterministic fallback."""
    config = HolusConfig.load(agent_name="research-curator")
    if not config.anthropic_api_key:
        return None
    return AgentBackedResearchScorer(repo_root=repo_root, config=config)


def _message_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    return "\n".join(parts).strip()
