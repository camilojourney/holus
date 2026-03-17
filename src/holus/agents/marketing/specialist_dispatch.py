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


class SpecialistDispatcher:
    """Dispatch content generation to specialist agents.

    Each specialist receives:
    1. The original idea
    2. Prior specialist outputs (chain context)
    3. Platform + format constraints
    4. Its specific task description

    Specialists are called sequentially (each builds on prior output).
    voice-guardian is a gate — if FAIL, the piece is flagged.
    """

    def __init__(self, proxy_url: str = "http://localhost:8080/v1/chat/completions") -> None:
        self._proxy_url = proxy_url

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
        return self._assemble(outputs, content_type)

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
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Specialist %s failed: %s", specialist_id, exc)
            return f"[{specialist_id} unavailable: {exc}]"

    def _assemble(
        self,
        outputs: list[SpecialistOutput],
        content_type: str,
    ) -> AssembledContent:
        """Assemble specialist outputs into final content."""
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

        return AssembledContent(
            text=full_text,
            hook=hook,
            body=body,
            cta=cta,
            specialist_outputs=outputs,
            voice_check=voice_check,
        )
