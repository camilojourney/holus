"""LinkedIn Voice Pipeline — SPEC-035.

Orchestrates the full flow:
  raw idea → idea-injector → context-builder → voice-writer → VoicePipelineResult

Single Opus call for voice writing (hook-architect + storyteller + cta-strategist
+ voice-guardian inline). PromptLoader resolves all agent prompts from .md files.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from holus.core.llm_proxy import get_proxy_headers, get_proxy_url
from holus.core.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)

# Models
_MODEL_INJECT = "anthropic/claude-sonnet-4-6"   # idea-injector + context-builder
_MODEL_WRITE = "anthropic/claude-sonnet-4-6"    # voice-writer (Opus-quality via proxy)
_MAX_RETRIES = 1                                 # retry once on VOICE_CHECK FAIL


@dataclass
class IdeaMetadata:
    raw_idea: str
    core_idea: str
    content_pillar: str
    product_angle: str | None
    suggested_hook: str
    confidence: str


@dataclass
class EnrichedContext:
    enriched_idea: str
    supporting_data: list[str]
    product_connection: str | None
    angle: str
    anti_pattern_flags: list[str]


@dataclass
class CardVariant:
    arm_id: str
    path: str
    variant: str  # "A", "B", "C"


@dataclass
class VoicePipelineResult:
    hook: str
    body: str
    cta: str
    voice_check: str          # "PASS" or "FAIL: <reason>"
    full_post: str            # hook + body + cta assembled
    metadata: IdeaMetadata
    context: EnrichedContext
    retried: bool = False
    error: str | None = None
    cards: list[CardVariant] = field(default_factory=list)


def _call_llm(
    system: str,
    user: str,
    model: str = _MODEL_INJECT,
    temperature: float = 0.7,
) -> str:
    """Single LLM call via local proxy."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": 2048,
    }
    resp = httpx.post(
        get_proxy_url(),
        json=payload,
        headers=get_proxy_headers(),
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _parse_json_response(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response — handles markdown code fences."""
    # Strip ```json ... ``` fences
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1)
    return json.loads(text.strip())


def _parse_voice_sections(text: str) -> tuple[str, str, str, str]:
    """Parse [HOOK], [BODY], [CTA], [VOICE_CHECK] from voice-writer output."""
    def extract(tag: str) -> str:
        pattern = rf"\[{tag}\]\s*(.*?)(?=\[(?:HOOK|BODY|CTA|VOICE_CHECK)\]|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    return (
        extract("HOOK"),
        extract("BODY"),
        extract("CTA"),
        extract("VOICE_CHECK"),
    )


class VoicePipeline:
    """LinkedIn voice writing pipeline (SPEC-035)."""

    def __init__(self, loader: PromptLoader | None = None, generate_cards: bool = True) -> None:
        self._loader = loader or PromptLoader()
        self._generate_cards = generate_cards

    def run(self, raw_idea: str) -> VoicePipelineResult:
        """Run the full pipeline from raw idea to post."""
        # Step 1: Idea injector
        metadata = self._inject(raw_idea)
        logger.info("idea-injector: pillar=%s product=%s", metadata.content_pillar, metadata.product_angle)

        # Step 2: Context builder
        context = self._enrich(metadata)
        logger.info("context-builder: angle=%s flags=%s", context.angle, context.anti_pattern_flags)

        # Step 3: Voice writer (with optional retry)
        result = self._write(metadata, context, anti_pattern_constraint=None)
        retried = False

        if result.voice_check.startswith("FAIL"):
            logger.warning("voice-guardian FAIL: %s — retrying", result.voice_check)
            constraint = result.voice_check.replace("FAIL:", "").strip()
            result = self._write(metadata, context, anti_pattern_constraint=constraint)
            retried = True

        result.retried = retried
        result.metadata = metadata
        result.context = context

        # Generate visual variants via bandit
        if self._generate_cards:
            try:
                from holus.agents.marketing.bandit import Bandit
                from holus.agents.marketing.card_generator import generate_cards

                bandit = Bandit()
                arms = bandit.select_arms(n=2)
                raw_cards = generate_cards(
                    hook=result.hook,
                    body=result.body,
                    arms=arms,
                )
                result.cards = [
                    CardVariant(arm_id=c["arm_id"], path=c["path"], variant=c["variant"])
                    for c in raw_cards
                ]
                logger.info("generated %d card variants: %s", len(result.cards), [c.variant for c in result.cards])
            except Exception as exc:
                logger.warning("card generation failed (non-fatal): %s", exc)

        return result

    def _inject(self, raw_idea: str) -> IdeaMetadata:
        system = self._loader.get_prompt(
            "idea-injector",
            fallback="Extract content_pillar and product_angle from the raw idea. Return JSON.",
        )
        user = f"Raw idea: {raw_idea}"
        text = _call_llm(system, user, model=_MODEL_INJECT)
        try:
            data = _parse_json_response(text)
            return IdeaMetadata(
                raw_idea=raw_idea,
                core_idea=data.get("core_idea", raw_idea),
                content_pillar=data.get("content_pillar", "ai_engineering"),
                product_angle=data.get("product_angle"),
                suggested_hook=data.get("suggested_hook", "observation"),
                confidence=data.get("confidence", "medium"),
            )
        except Exception as exc:
            logger.warning("idea-injector parse error: %s", exc)
            return IdeaMetadata(
                raw_idea=raw_idea,
                core_idea=raw_idea,
                content_pillar="ai_engineering",
                product_angle=None,
                suggested_hook="observation",
                confidence="low",
            )

    def _enrich(self, meta: IdeaMetadata) -> EnrichedContext:
        system = self._loader.get_prompt(
            "context-builder",
            fallback="Enrich the idea with data points and context. Return JSON.",
        )
        user = (
            f"Raw idea: {meta.raw_idea}\n"
            f"Content pillar: {meta.content_pillar}\n"
            f"Product angle: {meta.product_angle or 'none'}\n"
            f"Suggested hook: {meta.suggested_hook}"
        )
        text = _call_llm(system, user, model=_MODEL_INJECT)
        try:
            data = _parse_json_response(text)
            return EnrichedContext(
                enriched_idea=data.get("enriched_idea", meta.core_idea),
                supporting_data=data.get("supporting_data", []),
                product_connection=data.get("product_connection"),
                angle=data.get("angle", ""),
                anti_pattern_flags=data.get("anti_pattern_flags", []),
            )
        except Exception as exc:
            logger.warning("context-builder parse error: %s", exc)
            return EnrichedContext(
                enriched_idea=meta.core_idea,
                supporting_data=[],
                product_connection=None,
                angle="",
                anti_pattern_flags=[],
            )

    def _write(
        self,
        meta: IdeaMetadata,
        context: EnrichedContext,
        anti_pattern_constraint: str | None,
    ) -> VoicePipelineResult:
        system = self._loader.get_prompt(
            "voice-writer",
            fallback="Write a LinkedIn post in Juan's voice. Output [HOOK], [BODY], [CTA], [VOICE_CHECK].",
        )
        user_parts = [
            f"raw_idea: {meta.raw_idea}",
            f"enriched_context: {context.enriched_idea}",
            f"supporting_data: {', '.join(context.supporting_data)}",
            f"content_pillar: {meta.content_pillar}",
            f"suggested_hook: {meta.suggested_hook}",
            f"angle: {context.angle}",
        ]
        if anti_pattern_constraint:
            user_parts.append(f"anti_pattern_constraint: DO NOT use '{anti_pattern_constraint}' or anything similar")

        text = _call_llm("\n".join([system]), "\n".join(user_parts), model=_MODEL_WRITE)
        hook, body, cta, voice_check = _parse_voice_sections(text)

        full_post = f"{hook}\n\n{body}\n\n{cta}".strip()

        return VoicePipelineResult(
            hook=hook,
            body=body,
            cta=cta,
            voice_check=voice_check or "PASS",
            full_post=full_post,
            metadata=meta,
            context=context,
        )
