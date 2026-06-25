"""Research curator scoring wrapper."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from holus.research.models import RawResearchItem, RecommendedAction, ResearchScore

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

    async def score(self, item: RawResearchItem) -> ResearchScore:
        if self._scorer is not None:
            result = self._scorer(item, self.interests, self.products)
            if inspect.isawaitable(result):
                result = await result
            return ResearchScore.model_validate(result)
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
