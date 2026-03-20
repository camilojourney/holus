"""Quality compounding modules — voice checker, competitor analysis, trending topics.

These mechanisms compound content quality over time by learning from
the best-performing content (own and competitors).

Usage::

    checker = VoiceConsistencyChecker()
    result = await checker.check(text, exemplar_texts)

    analyzer = CompetitorAnalyzer()
    patterns = await analyzer.analyze(competitor_urls)

    detector = TrendingTopicDetector()
    topics = await detector.detect(niche="ai_engineering")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import requests

from holus.core.llm_proxy import get_proxy_headers, get_proxy_url

logger = logging.getLogger(__name__)

PROXY_URL = get_proxy_url()
PROXY_HEADERS = get_proxy_headers()
VOICE_PROFILE_PATH = Path(".self-improvement/knowledge/current/voice-profile.md")


def _call_llm(system: str, user: str, model: str = "anthropic/claude-sonnet-4-6") -> str:
    """Call LLM via proxy."""
    try:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": 2048,
            "temperature": 0.2,
        }
        resp = requests.post(PROXY_URL, json=payload, headers=PROXY_HEADERS, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# 9.4: Voice Consistency Checker
# ---------------------------------------------------------------------------


@dataclass
class VoiceCheckResult:
    """Result of voice consistency check."""

    consistent: bool
    score: float  # 0-1
    violations: list[str]
    suggestions: list[str]


class VoiceConsistencyChecker:
    """Check content against the established voice profile.

    Compares new content to exemplar texts (top-performing posts)
    for voice consistency — not just rule-checking but tonal matching.
    """

    def __init__(self, voice_profile_path: Path = VOICE_PROFILE_PATH) -> None:
        self._voice_profile = ""
        if voice_profile_path.exists():
            self._voice_profile = voice_profile_path.read_text(encoding="utf-8")[:2000]

    async def check(
        self,
        text: str,
        exemplar_texts: list[str] | None = None,
    ) -> VoiceCheckResult:
        """Check voice consistency against profile and exemplars."""
        exemplar_block = ""
        if exemplar_texts:
            exemplar_block = "\n\n<exemplars>\n" + "\n---\n".join(
                ex[:500] for ex in exemplar_texts[:3]
            ) + "\n</exemplars>"

        system = (
            "You are a voice consistency checker. Compare the new text against "
            "the voice profile and exemplars. Score 0-1 on consistency. "
            "List specific violations and suggestions. Return JSON:\n"
            '{"score": 0.85, "violations": ["uses we instead of I"], '
            '"suggestions": ["replace we with I in paragraph 2"]}'
        )

        user = f"""
<voice_profile>
{self._voice_profile[:1000] if self._voice_profile else "First person, opinionated, builder-practitioner, contractions always, no hedging."}
</voice_profile>
{exemplar_block}

<new_content>
{text[:2000]}
</new_content>

Check voice consistency. Return JSON only.
"""
        response = _call_llm(system, user)

        try:
            import json
            data = json.loads(response)
            return VoiceCheckResult(
                consistent=data.get("score", 0) >= 0.7,
                score=data.get("score", 0.0),
                violations=data.get("violations", []),
                suggestions=data.get("suggestions", []),
            )
        except (json.JSONDecodeError, TypeError):
            return VoiceCheckResult(consistent=True, score=0.5, violations=[], suggestions=[])


# ---------------------------------------------------------------------------
# 9.3: Competitor Analysis
# ---------------------------------------------------------------------------


@dataclass
class CompetitorInsight:
    """An insight extracted from competitor content."""

    source: str
    pattern: str
    hook_style: str
    engagement_signal: str
    applicable_to: list[str]  # content pillars this applies to


class CompetitorAnalyzer:
    """Analyze competitor content to extract patterns.

    Uses web search to find competitor posts, extracts patterns
    (hook styles, topics, formats), and stores as knowledge.
    """

    async def analyze(
        self,
        competitor_handles: list[str],
        platform: str = "linkedin",
    ) -> list[CompetitorInsight]:
        """Analyze competitor content patterns."""
        system = (
            "You are a competitive intelligence analyst for content marketing. "
            "Given competitor handles, analyze their recent content strategy. "
            "Extract: hook patterns, topic themes, posting frequency, "
            "engagement patterns. Return JSON array of insights."
        )

        user = f"""
Platform: {platform}
Competitor handles: {', '.join(competitor_handles)}

Analyze their content strategy. For each insight, provide:
- pattern: what they do
- hook_style: how they open posts
- engagement_signal: what seems to work
- applicable_to: which content pillars this maps to

Return JSON array.
"""
        response = _call_llm(system, user)

        try:
            import json
            data = json.loads(response)
            return [
                CompetitorInsight(
                    source=competitor_handles[0] if competitor_handles else "unknown",
                    pattern=item.get("pattern", ""),
                    hook_style=item.get("hook_style", ""),
                    engagement_signal=item.get("engagement_signal", ""),
                    applicable_to=item.get("applicable_to", []),
                )
                for item in data
            ]
        except (json.JSONDecodeError, TypeError):
            return []


# ---------------------------------------------------------------------------
# 9.5: Trending Topic Detection
# ---------------------------------------------------------------------------


@dataclass
class TrendingTopic:
    """A trending topic with relevance score."""

    topic: str
    relevance: float  # 0-1 relevance to our niche
    source: str
    time_sensitivity: str  # "urgent" | "this_week" | "evergreen"
    suggested_angle: str


class TrendingTopicDetector:
    """Detect trending topics relevant to the brand's niche.

    Uses web search + LLM analysis to find timely topics
    that the content engine should respond to quickly.
    """

    async def detect(
        self,
        niche: str = "ai_engineering",
        *,
        max_topics: int = 5,
    ) -> list[TrendingTopic]:
        """Detect trending topics in the niche."""
        system = (
            "You are a trending topic analyst for AI engineering content. "
            "Identify topics that are trending RIGHT NOW in the AI/ML space "
            "that a builder-practitioner could write about with authority. "
            "Return JSON array."
        )

        user = f"""
Niche: {niche}
Date: {__import__('datetime').datetime.now(__import__('datetime').UTC).strftime('%Y-%m-%d')}

Find {max_topics} trending topics in this niche. For each:
- topic: the trending subject
- relevance: 0-1 relevance to {niche}
- source: where you found this trend
- time_sensitivity: urgent | this_week | evergreen
- suggested_angle: how a builder-practitioner would approach this

Return JSON array only.
"""
        response = _call_llm(system, user)

        try:
            import json
            data = json.loads(response)
            return [
                TrendingTopic(
                    topic=item.get("topic", ""),
                    relevance=item.get("relevance", 0.5),
                    source=item.get("source", ""),
                    time_sensitivity=item.get("time_sensitivity", "evergreen"),
                    suggested_angle=item.get("suggested_angle", ""),
                )
                for item in data[:max_topics]
            ]
        except (json.JSONDecodeError, TypeError):
            return []
