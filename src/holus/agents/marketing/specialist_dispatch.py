"""Specialist dispatch — route content generation to specialized agents.

Instead of one monolithic Sonnet call, break content generation into
components handled by specialists, each independently evaluable and
optimizable via prompt evolution.

Pipeline for text posts:
  hook-architect → storyteller → cta-strategist → voice-guardian (gate)

Pipeline for carousels:
  hook-architect → carousel-architect → cta-strategist → voice-guardian (gate)

Each specialist runs independently, receives the idea + prior outputs,
and produces its component. The synthesizer assembles the final piece.

Usage::

    dispatcher = SpecialistDispatcher()
    result = await dispatcher.generate_text_post(idea, platform)
    result = await dispatcher.generate_carousel(idea, platform)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SpecialistOutput:
    """Output from a single specialist."""

    specialist_id: str
    output: str
    score: float | None = None  # Judge score for this component
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssembledContent:
    """Final assembled content from specialist pipeline."""

    text: str
    hook: str
    body: str
    cta: str
    specialist_outputs: list[SpecialistOutput] = field(default_factory=list)
    overall_score: float | None = None
    voice_check: str = "PENDING"


# Specialist pipelines per content type
PIPELINES: dict[str, list[str]] = {
    "text_post": ["hook-architect", "storyteller", "cta-strategist", "voice-guardian"],
    "carousel_outline": ["hook-architect", "carousel-architect", "cta-strategist", "voice-guardian"],
    "thread": ["hook-architect", "storyteller", "cta-strategist", "voice-guardian"],
    "video_script": ["hook-architect", "storyteller", "cta-strategist"],
    "instagram_caption": ["hook-architect", "cta-strategist"],
}

# What each specialist produces
SPECIALIST_TASKS: dict[str, str] = {
    "hook-architect": "Write the opening hook (first 1-2 sentences). Must stop the scroll. Max 15 words for the hook line itself.",
    "storyteller": "Write the body/narrative section. Build on the hook. One idea per paragraph. 3-5 short paragraphs.",
    "carousel-architect": "Design the slide structure. For each slide: type, title, body/bullets. 8-10 slides total.",
    "cta-strategist": "Write the closing CTA. One question or call to action. No 'follow me'. Lightweight.",
    "voice-guardian": "Review the complete piece for voice consistency. Check: first person, contractions, opinionated tone, no hedging. Return PASS/FAIL with specific feedback.",
}


def _enrich_for_platform(text: str, content_type: str, platform: str) -> str:
    """Append platform-required fields missing from the specialist pipeline.

    Instagram's judge rubric evaluates ``hashtag_strategy`` and ``caption_depth``
    for *all* supported formats including ``video_script``.  The video_script
    pipeline (hook-architect → storyteller → cta-strategist) never produces
    hashtags.  This function patches the gap with a topic-derived hashtag block
    so content doesn't auto-score PARTIAL on the rubric.
    """
    platform_lower = platform.lower() if platform else ""

    # Only enrich formats that lack built-in hashtag generation
    needs_hashtags = (
        content_type == "video_script"
        and platform_lower in ("instagram", "tiktok", "facebook")
    )
    if not needs_hashtags:
        return text

    # Don't double-add if hashtags already present
    if "#" in text.split("\n")[-1]:
        return text

    from holus.agents.marketing.platform_config import get_platform_config

    config = get_platform_config(platform_lower)
    limit = config.hashtag_limit or 5

    # Extract topic keywords from the text for relevant hashtags
    hashtags = _derive_hashtags(text, limit)
    if hashtags:
        text = f"{text}\n\n{' '.join(hashtags)}"

    return text


def _derive_hashtags(text: str, limit: int) -> list[str]:
    """Derive relevant hashtags from content text.

    Uses simple keyword extraction — no LLM call needed.
    """
    import re

    # Common AI/tech hashtags that pair well with video_script content
    base_tags = ["#AI", "#ArtificialIntelligence", "#TechContent", "#AIEngineering"]

    # Extract capitalised or notable words from the text as candidate tags
    words = re.findall(r"\b[A-Z][a-z]{3,}\b", text)
    # Deduplicate, preserve order
    seen: set[str] = set()
    unique_words: list[str] = []
    for w in words:
        low = w.lower()
        if low not in seen and low not in {"this", "that", "here", "when", "what", "with", "from", "your", "they", "will", "have", "been", "just", "most", "some", "more", "than", "also", "only", "each", "does"}:
            seen.add(low)
            unique_words.append(w)

    topic_tags = [f"#{w}" for w in unique_words[:limit]]

    # Merge: topic tags first, then fill with base tags up to limit
    combined: list[str] = []
    used: set[str] = set()
    for tag in topic_tags + base_tags:
        if tag.lower() not in used and len(combined) < limit:
            combined.append(tag)
            used.add(tag.lower())

    return combined


class SpecialistDispatcher:
    """Dispatch content generation to specialist agents.

    Each specialist receives:
    1. The original idea
    2. Prior specialist outputs (chain context)
    3. Platform + format constraints
    4. Its specific task description

    Sequential by default. Parallel execution for independent specialists
    (e.g., hook-architect and data-visualizer can run concurrently).
    voice-guardian always runs last as a gate.

    Specialist-level Thompson Sampling: tracks which specialist performs
    best for which (content_type, platform) combination.
    """

    def __init__(self, proxy_url: str | None = None) -> None:
        from holus.core.llm_proxy import get_proxy_url

        self._proxy_url = proxy_url or get_proxy_url()
        self._specialist_scores: dict[str, list[float]] = {}  # specialist_id → scores

    async def dispatch_parallel(
        self,
        idea: str,
        content_type: str,
        platform: str,
        *,
        pillar: str = "ai_engineering",
    ) -> AssembledContent:
        """Run independent specialists in parallel, then sequential dependents.

        Parallel group: hook-architect + any independent specialists
        Sequential: storyteller/carousel-architect (needs hook), cta-strategist, voice-guardian
        """
        import asyncio

        pipeline = PIPELINES.get(content_type, PIPELINES["text_post"])

        # Split into parallel (first specialist) and sequential (rest)
        # hook-architect is always first and independent
        parallel_specialists = [pipeline[0]] if pipeline else []
        sequential_specialists = pipeline[1:] if len(pipeline) > 1 else []

        outputs: list[SpecialistOutput] = []
        chain_context = ""

        # Run parallel group
        if parallel_specialists:
            tasks = []
            for spec_id in parallel_specialists:
                task_desc = SPECIALIST_TASKS.get(spec_id, "Generate content.")
                prompt = self._build_specialist_prompt(
                    specialist_id=spec_id, idea=idea, platform=platform,
                    content_type=content_type, pillar=pillar, task=task_desc,
                    chain_context="",
                )
                tasks.append(self._call_specialist(spec_id, prompt))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for spec_id, result in zip(parallel_specialists, results, strict=True):
                output_text = result if isinstance(result, str) else f"[{spec_id} failed: {result}]"
                outputs.append(SpecialistOutput(specialist_id=spec_id, output=output_text))
                chain_context += f"\n\n--- {spec_id} output ---\n{output_text}"

        # Run sequential group
        for spec_id in sequential_specialists:
            task_desc = SPECIALIST_TASKS.get(spec_id, "Generate content.")
            prompt = self._build_specialist_prompt(
                specialist_id=spec_id, idea=idea, platform=platform,
                content_type=content_type, pillar=pillar, task=task_desc,
                chain_context=chain_context,
            )
            output_text = await self._call_specialist(spec_id, prompt)
            outputs.append(SpecialistOutput(specialist_id=spec_id, output=output_text))
            chain_context += f"\n\n--- {spec_id} output ---\n{output_text}"

        return self._assemble(outputs, content_type, platform)

    def record_specialist_score(self, specialist_id: str, score: float) -> None:
        """Record a judge score for a specific specialist's output.

        Enables specialist-level performance tracking for targeted
        prompt evolution (evolve the weakest specialist, not all).
        """
        if specialist_id not in self._specialist_scores:
            self._specialist_scores[specialist_id] = []
        self._specialist_scores[specialist_id].append(score)

    def get_weakest_specialist(self, min_samples: int = 5) -> str | None:
        """Find the specialist with the lowest average score.

        Used by prompt evolution to target optimization.
        Returns None if insufficient data.
        """
        candidates: list[tuple[str, float]] = []
        for spec_id, scores in self._specialist_scores.items():
            if len(scores) >= min_samples:
                avg = sum(scores) / len(scores)
                candidates.append((spec_id, avg))

        if not candidates:
            return None

        return min(candidates, key=lambda x: x[1])[0]

    def specialist_summary(self) -> dict[str, dict[str, float | int]]:
        """Return performance summary for all specialists."""
        summary = {}
        for spec_id, scores in self._specialist_scores.items():
            summary[spec_id] = {
                "n": len(scores),
                "avg_score": round(sum(scores) / len(scores), 3) if scores else 0,
                "min_score": round(min(scores), 3) if scores else 0,
                "max_score": round(max(scores), 3) if scores else 0,
            }
        return summary

    async def dispatch_pipeline(
        self,
        idea: str,
        content_type: str,
        platform: str,
        *,
        pillar: str = "ai_engineering",
    ) -> AssembledContent:
        """Run the full specialist pipeline for a content type.

        Returns AssembledContent with all specialist outputs.
        """
        pipeline = PIPELINES.get(content_type, PIPELINES["text_post"])
        outputs: list[SpecialistOutput] = []
        chain_context = ""

        for specialist_id in pipeline:
            task = SPECIALIST_TASKS.get(specialist_id, "Generate content.")

            prompt = self._build_specialist_prompt(
                specialist_id=specialist_id,
                idea=idea,
                platform=platform,
                content_type=content_type,
                pillar=pillar,
                task=task,
                chain_context=chain_context,
            )

            output_text = await self._call_specialist(specialist_id, prompt)

            specialist_output = SpecialistOutput(
                specialist_id=specialist_id,
                output=output_text,
                metadata={"platform": platform, "content_type": content_type},
            )
            outputs.append(specialist_output)

            # Build chain context for next specialist
            chain_context += f"\n\n--- {specialist_id} output ---\n{output_text}"

        # Assemble final content
        return self._assemble(outputs, content_type, platform)

    def _build_specialist_prompt(
        self,
        *,
        specialist_id: str,
        idea: str,
        platform: str,
        content_type: str,
        pillar: str,
        task: str,
        chain_context: str,
    ) -> str:
        """Build the prompt for a specialist, including chain context."""
        # Try to load from PromptLoader first
        system_prompt = self._load_specialist_prompt(specialist_id)

        prompt = f"""{system_prompt}

<task>{task}</task>
<platform>{platform}</platform>
<content_type>{content_type}</content_type>
<pillar>{pillar}</pillar>

<idea>
{idea}
</idea>
"""
        if chain_context:
            prompt += f"""
<prior_outputs>
{chain_context}
</prior_outputs>

Build on the prior outputs. Do NOT repeat what was already written.
"""
        return prompt

    def _load_specialist_prompt(self, specialist_id: str) -> str:
        """Load specialist system prompt via PromptLoader."""
        try:
            from holus.core.prompt_loader import PromptLoader

            loader = PromptLoader()
            prompt = loader.get_prompt(specialist_id)
            if prompt:
                return prompt
        except Exception:
            pass

        # Fallback: minimal specialist prompt
        return (
            f"You are {specialist_id}, a specialist in Juan's content team. "
            f"Juan is a bilingual AI engineer. Builder-practitioner. "
            f"Write in first person. Short sentences. Opinionated."
        )

    async def _call_specialist(self, specialist_id: str, prompt: str) -> str:
        """Call a specialist via the LLM proxy."""
        import requests

        try:
            payload = {
                "model": "anthropic/claude-sonnet-4-6",
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 2048,
                "temperature": 0.4,
            }
            resp = requests.post(
                self._proxy_url,
                json=payload,
                headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
                timeout=120,
            )
            resp.raise_for_status()
            result: str = resp.json()["choices"][0]["message"]["content"]
            return result
        except Exception as exc:
            logger.warning("Specialist %s failed: %s", specialist_id, exc)
            return f"[{specialist_id} unavailable: {exc}]"

    def _assemble(
        self,
        outputs: list[SpecialistOutput],
        content_type: str,
        platform: str = "",
    ) -> AssembledContent:
        """Assemble specialist outputs into final content.

        Platform-aware post-processing appends hashtag blocks and captions
        when required by the target platform's judge rubric (e.g. Instagram
        expects hashtag_strategy for video_script content).
        """
        hook = ""
        body = ""
        cta = ""
        voice_check = "PENDING"

        for out in outputs:
            if out.specialist_id == "hook-architect":
                hook = out.output
            elif out.specialist_id in ("storyteller", "carousel-architect"):
                body = out.output
            elif out.specialist_id == "cta-strategist":
                cta = out.output
            elif out.specialist_id == "voice-guardian":
                voice_check = "PASS" if "pass" in out.output.lower() else "FAIL"

        # Combine for text posts
        if content_type in ("text_post", "thread"):
            full_text = f"{hook}\n\n{body}\n\n{cta}".strip()
        elif content_type == "carousel_outline":
            full_text = body  # carousel-architect produces the full slide JSON
        else:
            full_text = f"{hook}\n\n{body}\n\n{cta}".strip()

        # Platform-aware post-processing: Instagram video_script needs
        # hashtag block + caption (platform-fit-judge evaluates hashtag_strategy)
        full_text = _enrich_for_platform(full_text, content_type, platform)

        return AssembledContent(
            text=full_text,
            hook=hook,
            body=body,
            cta=cta,
            specialist_outputs=outputs,
            voice_check=voice_check,
        )
