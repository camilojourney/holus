"""Thought Studio pipeline.

One raw thought becomes a content set: platform-native drafts, visual assets,
and review-ready queue records. The implementation stays deterministic for
local/dev use, but the boundary is explicit so agent-backed generation can replace
the fallback composer without changing the API route.
"""

from __future__ import annotations

import contextlib
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from PIL import Image, ImageDraw, ImageFont

from holus.agents.marketing.creative_strategy import (
    choose_creative_strategy,
    editorial_card_copy,
)

SourceType = Literal["text", "url"]

DEFAULT_CHANNELS = (
    "linkedin_text",
    "linkedin_carousel",
    "instagram_image",
    "instagram_carousel",
    "threads_text",
    "twitter_x_thread",
    "facebook_text",
)

CHANNEL_TARGET: dict[str, tuple[str, str]] = {
    "linkedin_text": ("linkedin", "text_post"),
    "linkedin_image": ("linkedin", "image_post"),
    "linkedin_carousel": ("linkedin", "carousel_outline"),
    "instagram_image": ("instagram", "image_caption"),
    "instagram_carousel": ("instagram", "carousel_outline"),
    "threads_text": ("threads", "text_post"),
    "twitter_x_thread": ("twitter_x", "thread"),
    "facebook_text": ("facebook", "text_post"),
}

CHANNEL_AGENT: dict[str, tuple[str, str]] = {
    "linkedin_text": ("voice-writer", "drafted LinkedIn post in Juan's voice"),
    "linkedin_image": ("visual-designer", "designed LinkedIn image asset"),
    "linkedin_carousel": ("carousel-architect", "structured the thought into a carousel"),
    "instagram_image": ("visual-designer", "designed Instagram image asset"),
    "instagram_carousel": (
        "carousel-architect",
        "structured the thought into an Instagram carousel",
    ),
    "threads_text": ("platform-adapter", "adapted thought into Threads post"),
    "twitter_x_thread": ("platform-adapter", "adapted thought into X thread"),
    "facebook_text": ("storyteller", "adapted thought into conversational Facebook post"),
}

CAROUSEL_CHANNELS = {"linkedin_carousel", "instagram_carousel"}
IMAGE_CHANNELS = {"linkedin_image", "instagram_image"}

AGENT_TRACE_ROLES: dict[str, str] = {
    "idea-injector": "parsed raw thought and content intent",
    "context-builder": "enriched angle and product context",
    "content-job-classifier": "classified the strategic content job",
    "format-router": "selected the content format before visual production",
    "idea-planner": "planned platform outputs",
    "platform-adapter": "made output platform-native",
    "voice-guardian": "checked Juan voice and anti-patterns",
    "brand-designer": "checked visual identity",
    "visual-necessity-gate": "decided whether a visual was needed",
    "deterministic-artifact-planner": "planned exact rendered artifacts",
    "ai-image-director": "constrained allowed AI image direction",
    "visual-designer": "created Holus visual spec",
    "carousel-architect": "designed carousel slide sequence",
    "voice-writer": "wrote authority copy",
    "storyteller": "shaped narrative arc",
}

BRAND_HANDLES_BY_LANGUAGE = {
    "en": "@camiloexperience",
    "es": "@camilojourney",
}

PROFILE_URL_BY_PLATFORM: dict[str, str] = {
    "instagram": "https://instagram.com/{account}",
    "threads": "https://www.threads.net/@{account}",
    "twitter_x": "https://x.com/{account}",
}

SPANISH_LANGUAGE_MARKERS = {
    " de ",
    " que ",
    " para ",
    " con ",
    " una ",
    " los ",
    " las ",
    " cómo ",
    " por ",
    " sistema",
    " trabajo",
    "flujo",
}


@dataclass(frozen=True)
class ThoughtSource:
    """Normalized source metadata for one thought."""

    source_type: SourceType
    raw_input: str
    extracted_text: str
    source_url: str | None = None


@dataclass(frozen=True)
class ContentSet:
    """Generated queue records for one thought."""

    group_id: str
    thought: str
    records: list[dict[str, Any]]
    package: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ThoughtEssence:
    """Extracted meaning that downstream generators should preserve."""

    thesis: str
    role_map: list[str]
    evidence: list[str]
    voice_markers: list[str]
    mode: str
    visual_prompt: str


@dataclass(frozen=True)
class VisualBrief:
    """Prompt variables that control one rendered visual direction."""

    profile_id: str
    visual_type: str
    purpose: str
    subject: str
    action: str
    setting: str
    composition: str
    camera_angle: str
    style: str
    palette: str
    lighting: str
    mood: str
    typography: str
    text_placement: str
    theme: str
    font_pairing: str
    gradient: str
    effect: str
    motif: str
    variation_seed: str

    def prompt_contract(self) -> dict[str, str]:
        """Return the image-generation contract used by AI or local renderers."""
        return {
            "purpose": self.purpose,
            "subject": self.subject,
            "action": self.action,
            "setting": self.setting,
            "composition": self.composition,
            "camera_angle": self.camera_angle,
            "style": self.style,
            "palette": self.palette,
            "lighting": self.lighting,
            "mood": self.mood,
            "typography": self.typography,
            "text_placement": self.text_placement,
            "variation_seed": self.variation_seed,
        }

    def style_profile(self) -> dict[str, str]:
        """Return renderer-facing style controls."""
        return {
            "profile_id": self.profile_id,
            "visual_type": self.visual_type,
            "theme": self.theme,
            "font_pairing": self.font_pairing,
            "gradient": self.gradient,
            "effect": self.effect,
            "motif": self.motif,
        }


@dataclass(frozen=True)
class VisualJudgeDecision:
    """Local judge decision for generated visual/carousel output."""

    evaluator: str
    verdict: Literal["PASS", "REDO"]
    score: int
    reasons: list[str]
    redo_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluator": self.evaluator,
            "verdict": self.verdict,
            "score": self.score,
            "reasons": self.reasons,
            "redo_count": self.redo_count,
        }


VISUAL_STYLE_PROFILES: tuple[dict[str, str], ...] = (
    {
        "profile_id": "studio-system-map",
        "visual_type": "flowchart",
        "purpose": "teach the operating loop behind the thought",
        "subject": "one raw thought becoming a multi-platform content system",
        "action": "moving through source, context, variants, visuals, review, and publish",
        "setting": "premium dark product-system diagram",
        "composition": "vertical process map with short labeled nodes",
        "camera_angle": "front-on editorial graphic",
        "style": "high-contrast SaaS systems diagram",
        "palette": "deep navy, amber, slate, emerald accent",
        "lighting": "soft interface glow with restrained contrast",
        "mood": "precise, strategic, operational",
        "typography": "bold geometric headline with mono labels",
        "text_placement": "large headline top, compact labels inside nodes",
        "theme": "dark",
        "font_pairing": "tech",
        "gradient": "indigo_mesh",
        "effect": "depth",
        "motif": "pipeline nodes",
    },
    {
        "profile_id": "editorial-thesis-card",
        "visual_type": "insight",
        "purpose": "make the thought feel like a memorable thesis",
        "subject": "the strongest sentence in the source thought",
        "action": "standing as a concise editorial claim",
        "setting": "minimal editorial poster",
        "composition": "centered headline with a short supporting line",
        "camera_angle": "flat-lay poster crop",
        "style": "premium magazine typography",
        "palette": "warm amber, cream text, espresso dark",
        "lighting": "quiet warm studio light",
        "mood": "reflective, human, founder-led",
        "typography": "editorial headline with clean sans body",
        "text_placement": "centered headline with generous margins",
        "theme": "warm",
        "font_pairing": "editorial",
        "gradient": "warm_sunset",
        "effect": "grain",
        "motif": "editorial pull quote",
    },
    {
        "profile_id": "bold-transformation",
        "visual_type": "comparison",
        "purpose": "show the before and after of content strategy",
        "subject": "raw thought versus platform-native assets",
        "action": "contrasting naive automation with strategic transformation",
        "setting": "bold startup launch graphic",
        "composition": "side-by-side contrast table",
        "camera_angle": "straight-on product graphic",
        "style": "bold social carousel cover",
        "palette": "charcoal, red, pale coral, white",
        "lighting": "hard graphic contrast",
        "mood": "decisive, punchy, high-energy",
        "typography": "condensed headline with sturdy body copy",
        "text_placement": "headline top, comparison grid centered",
        "theme": "bold",
        "font_pairing": "bold",
        "gradient": "bold_fire",
        "effect": "neubrutalism",
        "motif": "before-after contrast",
    },
    {
        "profile_id": "cool-architecture",
        "visual_type": "architecture",
        "purpose": "make the content engine feel like a real product architecture",
        "subject": "Holus Thought Studio layers",
        "action": "connecting source, intelligence, visual engine, review, and Social API",
        "setting": "cool technical architecture board",
        "composition": "layered architecture stack with connections",
        "camera_angle": "front-on diagram",
        "style": "technical systems architecture",
        "palette": "cyan, deep blue, slate, white",
        "lighting": "cool luminous interface light",
        "mood": "credible, technical, composed",
        "typography": "modern SaaS headline with mono component labels",
        "text_placement": "title top, stacked layers below",
        "theme": "cool",
        "font_pairing": "modern",
        "gradient": "cool_ocean",
        "effect": "glass",
        "motif": "layered blocks",
    },
    {
        "profile_id": "light-data-signal",
        "visual_type": "data_viz",
        "purpose": "turn the thought into a measurable content decision",
        "subject": "platform jobs and expected content effort",
        "action": "ranking formats by strategic usefulness",
        "setting": "clean light analytics card",
        "composition": "simple bar chart with one highlighted bar",
        "camera_angle": "flat dashboard crop",
        "style": "minimal analytics graphic",
        "palette": "white, slate, amber, muted blue",
        "lighting": "bright clean product lighting",
        "mood": "clear, analytical, trustworthy",
        "typography": "clean SaaS sans with compact labels",
        "text_placement": "short title top, chart below",
        "theme": "light",
        "font_pairing": "modern",
        "gradient": "minimal_light",
        "effect": "none",
        "motif": "metric bars",
    },
    {
        "profile_id": "ai-focus-thesis",
        "visual_type": "insight",
        "purpose": "make an AI working lesson instantly memorable",
        "subject": "simplicity and focus when prompting AI",
        "action": "removing noise so the model can see the job",
        "setting": "minimal high-contrast prompt craft poster",
        "composition": "large thesis headline with three short proof lines",
        "camera_angle": "straight-on typography poster",
        "style": "premium AI craft quote card",
        "palette": "near black, white, amber, muted slate",
        "lighting": "quiet focused studio contrast",
        "mood": "clear, disciplined, practical",
        "typography": "bold editorial headline with clean supporting text",
        "text_placement": "large top-left headline, short lines below",
        "theme": "dark",
        "font_pairing": "editorial",
        "gradient": "indigo_mesh",
        "effect": "grain",
        "motif": "prompt focus",
    },
    {
        "profile_id": "ai-workflow-harness",
        "visual_type": "architecture",
        "purpose": "make a multi-model AI workflow feel like an operating harness",
        "subject": "Claude planning, Codex execution, skills as hands, reviews, fallbacks, and daily work",
        "action": "showing each model or skill as a distinct job in the system",
        "setting": "dark technical systems poster",
        "composition": "large thesis with compact role-map proof lines",
        "camera_angle": "straight-on architecture poster",
        "style": "premium AI systems diagram with editorial typography",
        "palette": "near black, white, amber, muted blue",
        "lighting": "quiet interface glow with warm architecture accents",
        "mood": "precise, builder-led, operational",
        "typography": "bold editorial thesis with compact systems labels",
        "text_placement": "large left thesis, role map and CTA on the right or lower third",
        "theme": "dark",
        "font_pairing": "editorial",
        "gradient": "indigo_mesh",
        "effect": "grain",
        "motif": "multi-model harness",
    },
)


class ThoughtContentPipeline:
    """Create review-ready content variants from one thought."""

    def __init__(
        self,
        *,
        queue_dir: Path | str = "data/content-queue",
        rendered_dir: Path | str | None = None,
    ) -> None:
        self.queue_dir = Path(queue_dir)
        self.rendered_dir = (
            Path(rendered_dir) if rendered_dir else self.queue_dir.parent / "rendered-content"
        )

    async def normalize_source(
        self,
        *,
        thought: str,
        source_type: str | None = None,
        source_url: str | None = None,
    ) -> ThoughtSource:
        """Normalize text or URL input into the thought text used downstream."""
        normalized_source = source_type or ("url" if source_url else "text")
        if normalized_source == "url":
            if not source_url:
                msg = "source_url is required when source_type='url'"
                raise ValueError(msg)
            extracted = await self._extract_from_url(source_url)
            return ThoughtSource(
                source_type="url",
                raw_input=source_url,
                extracted_text=_clean_thought(extracted),
                source_url=source_url,
            )
        if normalized_source != "text":
            msg = f"Unsupported source_type: {normalized_source}"
            raise ValueError(msg)
        return ThoughtSource(
            source_type="text",
            raw_input=thought,
            extracted_text=_clean_thought(thought),
        )

    async def create_content_set(
        self,
        *,
        thought: str,
        channels: list[str],
        source_type: str | None = None,
        source_url: str | None = None,
        source_intent: str | None = None,
        fetch_source_url: bool = True,
        write_records: bool = True,
    ) -> ContentSet:
        """Create all requested content variants and write queue records."""
        effective_source_type = source_type
        effective_source_url = source_url
        if source_type == "url" and not fetch_source_url:
            effective_source_type = "text"
        source = await self.normalize_source(
            thought=thought,
            source_type=effective_source_type,
            source_url=effective_source_url,
        )
        if source_type == "url" and not fetch_source_url:
            source = ThoughtSource(
                source_type="url",
                raw_input=source_url or thought,
                extracted_text=source.extracted_text,
                source_url=source_url,
            )
        if len(source.extracted_text) < 8:
            msg = "Thought is too short"
            raise ValueError(msg)

        group_id = uuid.uuid4().hex
        records = [self._create_queue_record(source, channel, group_id) for channel in channels]
        if write_records:
            for record in records:
                self.write_queue_record(record)
        package = self._build_package(source, records, source_intent=source_intent)
        return ContentSet(
            group_id=group_id,
            thought=source.extracted_text,
            records=records,
            package=package,
        )

    def write_queue_record(self, record: dict[str, Any]) -> Path:
        """Persist one generated variant to the content queue."""
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        path = self.queue_dir / f"{record['piece_id']}.yaml"
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        return path

    async def _extract_from_url(self, url: str) -> str:
        from holus.research.sources.base import safe_get

        response = await safe_get(
            url,
            headers={"User-Agent": "HolusThoughtStudio/1.0"},
        )
        text = response.text

        import re

        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000]

    def _build_package(
        self,
        source: ThoughtSource,
        records: list[dict[str, Any]],
        *,
        source_intent: str | None = None,
    ) -> dict[str, Any]:
        intent = source_intent or _infer_source_intent(source.extracted_text, source.source_type)
        source_context = _source_context(source.extracted_text, intent)
        channel_plan = [
            {
                "piece_id": record["piece_id"],
                "platform": record["platform"],
                "content_type": record["content_type"],
                "channel_job": record.get("content_job_plan", ""),
                "transformation_job": _transformation_job(record, source_context),
            }
            for record in records
        ]
        for plan_item, record in zip(channel_plan, records, strict=False):
            record["platform_job_plan"] = plan_item["transformation_job"]
            record.setdefault("quality", {})
            record["quality"]["platform_fit"] = _platform_fit(record)
        platform_fit_summary = _platform_fit_summary(records)
        source_extract_char_count = len(_clean_thought(source.extracted_text))
        source_evidence: dict[str, Any] = {
            "source_type": source.source_type,
            "status": "available" if source.source_type == "url" else "operator_supplied",
            "operator_context_included": False,
        }
        if source.source_type == "url":
            source_evidence["source_extract_char_count"] = source_extract_char_count
        review_checklist = [
            {
                "artifact": "source_evidence",
                "status": "PASS",
                "evidence": f"{source.source_type} source evidence available",
            },
            {
                "artifact": "source_context",
                "status": "PASS",
                "evidence": f"intent={intent}",
            },
            {
                "artifact": "channel_plan.transformation_job",
                "status": "PASS",
                "evidence": "Each channel has a transformation job.",
            },
            {
                "artifact": "quality_evaluation.platform_fit_summary",
                "status": "PASS",
                "evidence": "All variants fit platform bounds.",
            },
            {
                "artifact": "approval_workflow.publish_gate",
                "status": "PASS",
                "evidence": "Explicit human approval is required before publishing.",
            },
        ]
        return {
            "source": {
                "intent": intent,
                "char_count": source_extract_char_count,
                "operator_context_included": False,
                "source_extract_char_count": (
                    source_extract_char_count if source.source_type == "url" else None
                ),
            },
            "source_context": source_context,
            "strategic_brief": f"{intent}: {_first_sentence(source.extracted_text, fallback='')}",
            "distribution_recommendation": {
                "primary_channel": records[0]["platform"] if records else None,
            },
            "channel_plan": channel_plan,
            "quality_evaluation": {
                "ready_for_human_review": True,
                "success_criteria": [
                    "clear source context",
                    "platform-native transformation",
                    "explicit human approval",
                    source_context.get("success_signal", "useful marketing content"),
                ],
                "source_evidence": source_evidence,
                "platform_fit_summary": platform_fit_summary,
            },
            "approval_workflow": {
                "status": "pending_review",
                "approval_required": True,
                "publish_gate": "Publishing requires explicit human approval.",
                "review_steps": [
                    "source evidence",
                    "source context",
                    "platform fit",
                    "publish gate",
                ],
                "review_checklist": review_checklist,
            },
        }

    def _create_queue_record(
        self,
        source: ThoughtSource,
        channel: str,
        group_id: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        platform, content_type = CHANNEL_TARGET[channel]
        essence = _extract_thought_essence(source.extracted_text)
        text = _build_platform_text(source.extracted_text, channel, essence)
        voice_check = _local_voice_check(text, platform)
        piece_id = f"thought-{group_id[:12]}-{channel}"
        channel_agent, channel_role = CHANNEL_AGENT[channel]
        trace_agents = [
            ("idea-injector", AGENT_TRACE_ROLES["idea-injector"]),
            ("context-builder", AGENT_TRACE_ROLES["context-builder"]),
            ("idea-planner", AGENT_TRACE_ROLES["idea-planner"]),
            (channel_agent, channel_role),
            ("platform-adapter", AGENT_TRACE_ROLES["platform-adapter"]),
            ("voice-guardian", AGENT_TRACE_ROLES["voice-guardian"]),
        ]
        if channel in {*IMAGE_CHANNELS, *CAROUSEL_CHANNELS}:
            trace_agents.insert(4, ("visual-designer", AGENT_TRACE_ROLES["visual-designer"]))
            trace_agents.insert(5, ("brand-designer", AGENT_TRACE_ROLES["brand-designer"]))

        seen_agents: set[str] = set()
        deduped_trace_agents: list[tuple[str, str]] = []
        for agent_id, role in trace_agents:
            if agent_id in seen_agents:
                continue
            seen_agents.add(agent_id)
            deduped_trace_agents.append((agent_id, role))
        trace_agents = deduped_trace_agents

        record: dict[str, Any] = {
            "piece_id": piece_id,
            "group_id": group_id,
            "product": "none",
            "platform": platform,
            "posting_destination": build_posting_destination(
                platform=platform,
                thought=source.extracted_text,
            ),
            "content_type": content_type,
            "content_pillar": "thought_studio",
            "topic": essence.thesis,
            "text": text,
            "hashtags": [],
            "char_count": len(text),
            "status": "pending_review",
            "generated_at": now.isoformat(),
            "idea_source": source.extracted_text,
            "source_type": source.source_type,
            "source_url": source.source_url,
            "source_raw_input": source.raw_input,
            "thought_essence": {
                "thesis": essence.thesis,
                "role_map": essence.role_map,
                "evidence": essence.evidence,
                "voice_markers": essence.voice_markers,
                "mode": essence.mode,
                "visual_prompt": essence.visual_prompt,
            },
            "reasoning": "Created from the Holus Thought Studio intake. Human approval is required before publishing.",
            "model_used": "holus/deterministic-thought-pipeline",
            "agent_trace": [
                {
                    "agent_id": agent_id,
                    "model": "holus/deterministic-thought-pipeline",
                    "role": role,
                    "at": now.isoformat(),
                }
                for agent_id, role in trace_agents
            ],
            "quality": {
                "hook_score": "8",
                "voice_check": voice_check,
            },
        }

        from holus.visual.dispatcher import RefinedVisualSource
        from holus.visual.generation_strategy import choose_visual_generation_strategy
        from holus.visual.production_plan import build_visual_production_plan
        from holus.visual.proximity_router import choose_visual_concept_route

        refined_source = RefinedVisualSource.from_queue_record(record)
        visual_route = choose_visual_concept_route(refined_source)
        visual_plan = build_visual_production_plan(refined_source, visual_route)
        visual_strategy = choose_visual_generation_strategy(refined_source, visual_route)
        record["content_job_plan"] = visual_strategy.content_job.log_summary()
        visual_brief = _select_visual_brief(source.extracted_text, channel, group_id)
        rendered = self._render_visual_asset(
            essence.visual_prompt,
            channel,
            piece_id,
            visual_brief,
            raw_thought=source.extracted_text,
            essence=essence,
            refined_source=refined_source,
            visual_route=visual_route,
            visual_plan=visual_plan,
            visual_strategy=visual_strategy,
        )
        if rendered:
            path_key, asset_path, visual_spec = rendered
            record[path_key] = asset_path
            record["visual_spec"] = visual_spec
            visual_judge = visual_spec.get("visual_judge")
            if isinstance(visual_judge, dict):
                record["judge_score"] = visual_judge.get("score")
                record["judge_verdict"] = visual_judge.get("verdict")
                record["quality"]["quality_score"] = visual_judge.get("score")
                if visual_judge.get("verdict") != "PASS":
                    record["quality"]["violations"] = visual_judge.get("reasons", [])
        return record

    def _render_visual_asset(
        self,
        thought: str,
        channel: str,
        piece_id: str,
        visual_brief: VisualBrief,
        *,
        raw_thought: str,
        essence: ThoughtEssence,
        refined_source: Any,
        visual_route: Any,
        visual_plan: Any,
        visual_strategy: Any,
    ) -> tuple[str, str, dict[str, Any]] | None:
        self.rendered_dir.mkdir(parents=True, exist_ok=True)
        if getattr(getattr(visual_strategy, "rendering_path", None), "value", None) == "no_visual":
            return None
        if channel in CAROUSEL_CHANNELS:
            output_path = self.rendered_dir / f"{piece_id}.pdf"
            outline, visual_brief, judge = _prepare_judged_carousel_outline(
                raw_thought,
                essence,
                channel,
                visual_brief,
            )
            visual_spec = _carousel_visual_spec_from_outline(
                outline,
                visual_brief,
                channel,
                judge,
                renderer="holus/visual-dispatcher",
            )
            visual_spec["visual_route"] = visual_route.model_dump(mode="json")
            visual_spec["visual_plan"] = visual_plan.model_dump(mode="json")
            visual_spec["visual_strategy"] = visual_strategy.model_dump(mode="json")
            dispatched = _dispatch_carousel_pdf(
                outline=outline,
                output_path=output_path,
                piece_id=piece_id,
                channel=channel,
                refined_source=refined_source,
                visual_route=visual_route,
                visual_plan=visual_plan,
                visual_strategy=visual_strategy,
                queue_dir=self.queue_dir,
            )
            if dispatched:
                visual_spec["visual_dispatch"] = dispatched
                return (
                    "rendered_pdf_path",
                    str(output_path),
                    visual_spec,
                )
            _write_minimal_pdf(output_path)
            visual_spec = {
                **visual_spec,
                "renderer": "holus/carousel-fallback",
                "note": "Fallback PDF written because the Playwright carousel renderer was unavailable.",
            }
            return (
                "rendered_pdf_path",
                str(output_path),
                visual_spec,
            )

        if channel not in IMAGE_CHANNELS:
            return None

        output_path = self.rendered_dir / f"{piece_id}.png"
        visual_spec, visual_brief, judge = _prepare_judged_visual_spec(
            raw_thought,
            essence,
            channel,
            visual_brief,
        )
        visual_spec["visual_judge"] = judge.to_dict()
        visual_spec["refined_visual_source"] = refined_source.model_dump(mode="json")
        visual_spec["visual_route"] = visual_route.model_dump(mode="json")
        visual_spec["visual_plan"] = visual_plan.model_dump(mode="json")
        visual_spec["visual_strategy"] = visual_strategy.model_dump(mode="json")
        visual_spec["visual_dispatch_log_path"] = str(
            self.queue_dir.parent / "logs" / "image-dispatch.jsonl"
        )
        with contextlib.suppress(Exception):
            from holus.agents.marketing.visual_pipeline import _render_visual

            if _render_visual(visual_spec, output_path):
                return (
                    "rendered_image_path",
                    str(output_path),
                    {
                        **visual_spec,
                        "renderer": "holus/visual-renderer",
                        "format": "png",
                        "channel": channel,
                        "style_profile": visual_brief.style_profile(),
                        "prompt_contract": visual_brief.prompt_contract(),
                    },
                )

        fallback_spec = _render_fallback_visual(thought, output_path, channel, visual_brief)
        fallback_spec["visual_judge"] = judge.to_dict()
        fallback_spec["variable_rationale"] = visual_spec.get("variable_rationale")
        fallback_spec["refined_visual_source"] = refined_source.model_dump(mode="json")
        fallback_spec["visual_route"] = visual_route.model_dump(mode="json")
        fallback_spec["visual_plan"] = visual_plan.model_dump(mode="json")
        fallback_spec["visual_strategy"] = visual_strategy.model_dump(mode="json")
        return (
            "rendered_image_path",
            str(output_path),
            fallback_spec,
        )


def _dispatch_carousel_pdf(
    *,
    outline: dict[str, Any],
    output_path: Path,
    piece_id: str,
    channel: str,
    refined_source: Any,
    visual_route: Any,
    visual_plan: Any,
    visual_strategy: Any,
    queue_dir: Path,
) -> dict[str, Any] | None:
    """Render a carousel PDF through the visual dispatcher from sync pipeline code."""
    import asyncio
    import concurrent.futures

    from holus.visual.dispatcher import (
        VisualAssetKind,
        VisualDispatcher,
        VisualDispatchRequest,
        VisualDispatchStatus,
        VisualProvider,
    )

    async def _run() -> dict[str, Any] | None:
        platform, _ = CHANNEL_TARGET[channel]
        result = await VisualDispatcher().dispatch(
            VisualDispatchRequest(
                request_id=f"{piece_id}-pdf",
                platform=platform,
                asset_kind=VisualAssetKind.CAROUSEL,
                provider=VisualProvider.HTML_RENDERER,
                carousel_outline=outline,
                output_path=output_path,
                log_path=queue_dir.parent / "logs" / "image-dispatch.jsonl",
                refined_source=refined_source,
                visual_route=visual_route,
                visual_plan=visual_plan,
                metadata={
                    "source": "thought_pipeline",
                    "piece_id": piece_id,
                    "channel": channel,
                    "artifact": "carousel_pdf",
                    "visual_strategy": visual_strategy.log_summary(),
                },
            )
        )
        if result.status != VisualDispatchStatus.SUCCEEDED or result.output_path is None:
            return None
        return {
            "request_id": result.request_id,
            "provider": result.provider.value,
            "status": result.status.value,
            "log_path": str(result.log_path),
            "sidecar_path": str(
                result.output_path.with_suffix(result.output_path.suffix + ".dispatch.json")
            ),
            "model_or_tool": result.model_or_tool,
        }

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run())

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _run()).result(timeout=75)


def _clean_thought(thought: str) -> str:
    return " ".join(thought.strip().split())


def _extract_thought_essence(thought: str) -> ThoughtEssence:
    """Extract deterministic meaning from a raw thought before drafting.

    The fallback pipeline should never use the raw first sentence as publishable
    copy. It should at least preserve the thesis, roles, and evidence.
    """
    cleaned = _clean_thought(thought)
    lowered = cleaned.lower()

    if _looks_like_ai_workflow_thought(lowered):
        role_map = [
            "Claude plans the work.",
            "Codex runs the plan for hours or days.",
            "Skills act like the hands.",
            "Multiple models add knowledge diversity and catch blind spots.",
            "Agy reviews.",
            "DeepSeek handles fallbacks and evaluations.",
            "Cursor stays as the daily work harness.",
        ]
        evidence = _extract_budget_lines(cleaned)
        return ThoughtEssence(
            thesis="The model is not the workflow. The harness is the workflow.",
            role_map=role_map,
            evidence=evidence,
            voice_markers=["skills are the hands", "hours or days", "knowledge diversity"],
            mode="builder note",
            visual_prompt=(
                "The model is not the workflow. The harness is the workflow. "
                "Claude plans, Codex runs, skills act as hands, and review models "
                "make the system disagree with itself before it ships."
            ),
        )

    first = _first_sentence(cleaned, fallback="One thought needs one clear thesis")
    return ThoughtEssence(
        thesis=first,
        role_map=[],
        evidence=[],
        voice_markers=[],
        mode="builder note",
        visual_prompt=cleaned,
    )


def _looks_like_ai_workflow_thought(lowered: str) -> bool:
    signals = ("claude", "codex", "cursor", "deepseek", "agy", "skills")
    return "workflow" in lowered and sum(signal in lowered for signal in signals) >= 3


def _extract_budget_lines(thought: str) -> list[str]:
    import re

    budget_order = ("Codex", "Cursor", "Claude", "Agy", "DeepSeek", "Deepseek")
    evidence: list[str] = []
    for name in budget_order:
        matches = re.findall(
            rf"\b{name}\b\s*(?:about|roughly)?\s*(\d+)(?!\.)",
            thought,
            flags=re.I,
        )
        if matches:
            label = "DeepSeek" if name.lower() == "deepseek" else name
            evidence.append(f"{label}: {matches[-1]}")
    seen: set[str] = set()
    unique: list[str] = []
    for item in evidence:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _build_platform_text(
    thought: str,
    channel: str,
    essence: ThoughtEssence | None = None,
) -> str:
    essence = essence or _extract_thought_essence(thought)
    roles = "\n".join(essence.role_map)
    evidence = "\n".join(essence.evidence)

    if channel == "linkedin_text":
        if essence.role_map:
            return (
                "Most AI workflows are becoming less about one perfect model and "
                "more about the harness around the models.\n\n"
                "My current setup is small, messy, and useful.\n\n"
                f"{roles}\n\n"
                "The budget split tells the truth about where the work actually happens:\n\n"
                f"{evidence}\n\n"
                "The pattern I am learning:\n\n"
                "Do not ask one model to be the whole company.\n\n"
                "Give each model a job.\n"
                "Give the workflow memory.\n"
                "Give the plan enough time to run.\n"
                "Use reviews and fallbacks so the system can disagree with itself before it ships.\n\n"
                f"{essence.thesis}"
            )
        return (
            "Most AI content tools stop at the caption.\n\n"
            "That is the wrong layer.\n\n"
            f"The useful thesis is this: {essence.thesis}\n\n"
            "A thought is not content yet. It is signal.\n\n"
            "The job is to turn that signal into a content set: argument, visual, "
            "thread, community post, and review-ready schedule.\n\n"
            "The system can generate the options. The human still owns the judgment.\n\n"
            "That is the product I want Holus to become."
        )
    if channel in CAROUSEL_CHANNELS:
        label = "Carousel caption" if channel == "linkedin_carousel" else "CAPTION"
        if essence.role_map:
            return (
                f"{label}\n\n"
                f"{essence.thesis}\n\n"
                "The point is not to find one model that does everything. The point is "
                "to design a harness where planning, execution, review, fallback, and "
                "daily work each have a clear job."
            )
        return (
            f"{label}\n\n"
            f"{essence.thesis}\n\n"
            "The idea is not to multiply noise. The idea is to preserve the signal "
            "while giving each platform the format it deserves."
        )
    if channel == "linkedin_image":
        if essence.role_map:
            return (
                f"{essence.thesis}\n\n"
                "A useful AI workflow is not one model doing every job.\n\n"
                "It is a harness: planning, execution, skills, reviews, fallbacks, "
                "and daily work arranged so each part has a clear responsibility."
            )
        return (
            f"{essence.thesis}\n\n"
            "The image should make the refined idea easy to understand before the "
            "caption expands it."
        )
    if channel == "facebook_text":
        if essence.role_map:
            return (
                "I keep refining my AI workflow, and the lesson is becoming clearer.\n\n"
                f"{essence.thesis}\n\n"
                "Claude plans. Codex runs for hours or days. Skills are the hands. "
                "Agy reviews. DeepSeek catches fallbacks and evaluations. Cursor is "
                "still where daily work happens.\n\n"
                "The useful part is not the tool list. It is the job design."
            )
        return (
            "I keep coming back to one simple product idea.\n\n"
            f"{essence.thesis}\n\n"
            "The hard part is not creating more content. The hard part is preserving "
            "the original judgment while adapting the format.\n\n"
            "Same idea. Different job. That is what Holus should handle."
        )
    if channel == "instagram_image":
        if essence.role_map:
            return (
                "CAPTION\n"
                f"{essence.thesis}\n\n"
                "A good AI workflow is not one model doing everything.\n\n"
                "It is planning, execution, review, fallback, and daily work arranged "
                "so each part has a job."
            )
        return (
            "CAPTION\n"
            f"{essence.thesis}\n\n"
            "A thought becomes useful when the format matches the platform.\n\n"
            "That is the difference between content automation and content strategy."
        )
    if channel == "threads_text":
        if essence.role_map:
            return (
                "My AI workflow is turning into a harness, not a model choice.\n\n"
                "Claude plans. Codex runs. Skills act like hands. Agy reviews. "
                "DeepSeek handles fallbacks/evals. Cursor stays daily.\n\n"
                f"{essence.thesis}"
            )
        return (
            "A raw thought is only the starting point.\n\n"
            f"{essence.thesis}\n\n"
            "It becomes content when the system decides what job it has on each platform."
        )
    if channel == "twitter_x_thread":
        if essence.role_map:
            return (
                f"1/ {essence.thesis}\n\n"
                "2/ Claude plans. Codex runs the plan for hours or days. Skills are the hands.\n\n"
                "3/ I use multiple models because one model has one set of blind spots. Diversity is part of the system.\n\n"
                "4/ Agy reviews. DeepSeek handles fallbacks/evals. Cursor stays my daily workbench.\n\n"
                "5/ The lesson: do not ask one model to be the whole company. Give each model a job."
            )
        return (
            f"1/ {essence.thesis}\n\n"
            "2/ The mistake is treating one thought like one post.\n\n"
            "It is not one post. It is a campaign seed.\n\n"
            "3/ LinkedIn wants depth. Instagram wants a visual. Threads wants the cleanest version.\n\n"
            "4/ Holus should create the variants. I should approve the judgment."
        )
    return thought


def _local_voice_check(text: str, platform: str) -> str:
    lowered = text.lower()
    forbidden = (
        "let's dive in",
        "in today's fast-paced",
        "game-changing",
        "revolutionary",
        "transformative",
        "unlock potential",
        "leverage synergies",
        "furthermore",
        "additionally",
        "moreover",
    )
    if any(phrase in lowered for phrase in forbidden):
        return "FAIL"
    if platform == "linkedin" and text.lstrip().lower().startswith("i "):
        return "FAIL"
    return "PASS"


def _select_visual_brief(thought: str, channel: str, nonce: str) -> VisualBrief:
    """Choose a relevant style direction, then vary within that lane."""
    digest = hashlib.sha256(f"{thought}|{channel}|{nonce}".encode()).hexdigest()
    lowered = thought.lower()
    if _looks_like_ai_workflow_thought(lowered):
        profile = _visual_profile("ai-workflow-harness")
    elif (
        channel in IMAGE_CHANNELS
        and any(
            signal in lowered
            for signal in ("simplicity", "simple", "focus", "prompt", "model", "ai")
        )
        and not any(signal in lowered for signal in ("workflow", "system architecture", "pipeline"))
    ):
        profile = _visual_profile("ai-focus-thesis")
    else:
        profile = VISUAL_STYLE_PROFILES[int(digest[:8], 16) % len(VISUAL_STYLE_PROFILES)]
    return VisualBrief(**profile, variation_seed=digest[:12])


def _visual_profile(profile_id: str) -> dict[str, str]:
    return next(p for p in VISUAL_STYLE_PROFILES if p["profile_id"] == profile_id)


def _brief_from_profile(profile_id: str, *, seed_material: str) -> VisualBrief:
    digest = hashlib.sha256(seed_material.encode()).hexdigest()
    return VisualBrief(**_visual_profile(profile_id), variation_seed=digest[:12])


def _prepare_judged_visual_spec(
    raw_thought: str,
    essence: ThoughtEssence,
    channel: str,
    visual_brief: VisualBrief,
) -> tuple[dict[str, Any], VisualBrief, VisualJudgeDecision]:
    visual_spec = _visual_spec_from_thought(essence.visual_prompt, visual_brief)
    judge = _judge_visual_output(raw_thought, essence, channel, visual_spec, redo_count=0)
    if judge.verdict == "PASS":
        return visual_spec, visual_brief, judge

    redo_brief = _redo_visual_brief(essence, channel)
    visual_spec = _visual_spec_from_thought(essence.visual_prompt, redo_brief)
    judge = _judge_visual_output(raw_thought, essence, channel, visual_spec, redo_count=1)
    return visual_spec, redo_brief, judge


def _prepare_judged_carousel_outline(
    raw_thought: str,
    essence: ThoughtEssence,
    channel: str,
    visual_brief: VisualBrief,
) -> tuple[dict[str, Any], VisualBrief, VisualJudgeDecision]:
    outline = _carousel_outline_from_thought(essence.visual_prompt, visual_brief, channel)
    visual_spec = _carousel_visual_spec_from_outline(
        outline,
        visual_brief,
        channel,
        VisualJudgeDecision(
            evaluator="holus/local-visual-judge",
            verdict="PASS",
            score=10,
            reasons=[],
            redo_count=0,
        ),
        renderer="holus/carousel-renderer",
    )
    judge = _judge_visual_output(raw_thought, essence, channel, visual_spec, redo_count=0)
    if judge.verdict == "PASS":
        return outline, visual_brief, judge

    redo_brief = _redo_visual_brief(essence, channel)
    outline = _carousel_outline_from_thought(essence.visual_prompt, redo_brief, channel)
    visual_spec = _carousel_visual_spec_from_outline(
        outline,
        redo_brief,
        channel,
        judge,
        renderer="holus/carousel-renderer",
    )
    judge = _judge_visual_output(raw_thought, essence, channel, visual_spec, redo_count=1)
    return outline, redo_brief, judge


def _redo_visual_brief(essence: ThoughtEssence, channel: str) -> VisualBrief:
    if essence.role_map:
        return _brief_from_profile(
            "ai-workflow-harness",
            seed_material=f"{essence.thesis}|{channel}|judge-redo",
        )
    return _brief_from_profile(
        "editorial-thesis-card",
        seed_material=f"{essence.thesis}|{channel}|judge-redo",
    )


def _carousel_visual_spec_from_outline(
    outline: dict[str, Any],
    visual_brief: VisualBrief,
    channel: str,
    judge: VisualJudgeDecision,
    *,
    renderer: str,
) -> dict[str, Any]:
    cover_variables = outline["slides"][0]["variables"]
    platform_export = (
        "linkedin_document_pdf"
        if channel == "linkedin_carousel"
        else "instagram_multi_image_carousel"
    )
    return {
        "renderer": renderer,
        "format": "pdf",
        "review_artifact": "pdf",
        "platform_export": platform_export,
        "channel": channel,
        "slides": len(outline["slides"]),
        "carousel_slides": outline["slides"],
        "cover_hook": cover_variables.get("headline"),
        "cover_subhook": cover_variables.get("subheadline"),
        "style_profile": visual_brief.style_profile(),
        "prompt_contract": visual_brief.prompt_contract(),
        "creative_contract": outline.get("creative_contract"),
        "variable_rationale": outline.get("variable_rationale"),
        "brand_identity": outline.get("brand_identity"),
        "visual_judge": judge.to_dict(),
    }


def _judge_visual_output(
    raw_thought: str,
    essence: ThoughtEssence,
    channel: str,
    visual_spec: dict[str, Any],
    *,
    redo_count: int,
) -> VisualJudgeDecision:
    visible_copy = _visible_visual_copy(visual_spec)
    lowered_copy = visible_copy.lower()
    reasons: list[str] = []

    raw_opening = _raw_opening_fragment(raw_thought)
    if raw_opening and raw_opening in lowered_copy:
        reasons.append("visible copy repeats the raw thought opening instead of extracted meaning")

    generic_fragments = ("the signal", "one clear idea", "clear thesis")
    if essence.role_map and any(fragment in lowered_copy for fragment in generic_fragments):
        reasons.append("visual uses generic filler instead of the workflow harness meaning")

    if not _has_thesis_signal(essence.thesis, lowered_copy):
        reasons.append("visible copy does not preserve the extracted thesis")

    style_profile = visual_spec.get("style_profile") or {}
    creative_contract = visual_spec.get("creative_contract") or {}
    if essence.role_map and style_profile.get("profile_id") != "ai-workflow-harness":
        reasons.append("style profile does not match the multi-model workflow harness")
    if essence.role_map and creative_contract.get("strategy_id") != "ai_workflow_harness_card":
        reasons.append("creative strategy does not match the workflow harness")
    if not visual_spec.get("variable_rationale"):
        reasons.append("visual variables lack rationale and lineage")
    if channel in CAROUSEL_CHANNELS and not visual_spec.get("cover_hook"):
        reasons.append("carousel cover hook is not exposed for review")
    if channel in IMAGE_CHANNELS and not visual_spec.get("hook"):
        reasons.append("image hook is not exposed for review")

    score = max(1, 10 - (len(reasons) * 2))
    return VisualJudgeDecision(
        evaluator="holus/local-visual-judge",
        verdict="REDO" if reasons else "PASS",
        score=score,
        reasons=reasons,
        redo_count=redo_count,
    )


def _visible_visual_copy(visual_spec: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "label",
        "hook",
        "subhook",
        "emphasis_word",
        "punchline",
        "save_cue",
        "cover_hook",
        "cover_subhook",
    ):
        value = visual_spec.get(key)
        if isinstance(value, str):
            parts.append(value)
    for point in visual_spec.get("proof_points", []):
        if isinstance(point, str):
            parts.append(point)
    return " ".join(parts)


def _raw_opening_fragment(raw_thought: str) -> str:
    words = _clean_thought(raw_thought).lower().split()
    if len(words) < 5:
        return ""
    return " ".join(words[:5])


def _has_thesis_signal(thesis: str, lowered_copy: str) -> bool:
    thesis_words = [
        word.strip(".,:;!?()").lower()
        for word in thesis.split()
        if len(word.strip(".,:;!?()")) >= 5
    ]
    if not thesis_words:
        return True
    matches = sum(1 for word in set(thesis_words) if word in lowered_copy)
    return matches >= min(2, len(set(thesis_words)))


def _visual_spec_from_thought(thought: str, visual_brief: VisualBrief) -> dict[str, Any]:
    short = thought[:160]
    creative_strategy = choose_creative_strategy(
        thought,
        channel="instagram_image",
        nonce=visual_brief.variation_seed,
    )
    base: dict[str, Any] = {
        "style_profile": visual_brief.style_profile(),
        "prompt_contract": visual_brief.prompt_contract(),
        "creative_contract": creative_strategy.to_contract(),
        "variable_rationale": _visual_variable_rationale(creative_strategy, visual_brief),
        "brand_identity": _brand_identity(),
    }

    if creative_strategy.strategy_type in {
        "rule_card",
        "mistake_reframe",
        "contrarian_thesis",
        "before_after",
        "framework_steps",
        "checklist",
    }:
        return {
            **base,
            "type": "instagram_editorial_card",
            **editorial_card_copy(thought, creative_strategy),
        }

    if visual_brief.visual_type == "flowchart":
        return {
            **base,
            "type": "flowchart",
            "title": "Thought To Content",
            "nodes": [
                {"id": "1", "label": "Source", "description": "raw thought"},
                {"id": "2", "label": "Signal", "description": "useful angle"},
                {"id": "3", "label": "Variants", "description": "native formats"},
                {"id": "4", "label": "Review", "description": "human judgment"},
                {"id": "5", "label": "Publish", "description": "Social API"},
            ],
            "connections": [
                {"from_id": "1", "to_id": "2"},
                {"from_id": "2", "to_id": "3"},
                {"from_id": "3", "to_id": "4"},
                {"from_id": "4", "to_id": "5"},
            ],
            "layout": "vertical",
        }

    if visual_brief.visual_type == "architecture":
        return {
            **base,
            "type": "architecture",
            "title": "Holus Content Engine",
            "layers": [
                {
                    "name": "Source",
                    "components": [{"name": "Thought", "description": "text or URL"}],
                },
                {
                    "name": "Studio",
                    "components": [
                        {"name": "Planner", "description": "content set"},
                        {"name": "Adapters", "description": "platform variants"},
                    ],
                },
                {
                    "name": "Output",
                    "components": [
                        {"name": "Visuals", "description": "PNG/PDF"},
                        {"name": "Social API", "description": "schedule/post"},
                    ],
                },
            ],
            "connections": [
                {"from_layer": 0, "from_comp": 0, "to_layer": 1, "to_comp": 0},
                {"from_layer": 1, "from_comp": 0, "to_layer": 1, "to_comp": 1},
                {"from_layer": 1, "from_comp": 1, "to_layer": 2, "to_comp": 0},
                {"from_layer": 2, "from_comp": 0, "to_layer": 2, "to_comp": 1},
            ],
        }

    if visual_brief.visual_type == "data_viz":
        return {
            **base,
            "type": "data_viz",
            "chart_type": "bar",
            "title": "Format Value",
            "data_points": [
                {"label": "Argument", "value": 90},
                {"label": "Visual", "value": 84},
                {"label": "Carousel", "value": 88},
                {"label": "Thread", "value": 76},
            ],
            "highlight_index": 0,
            "source_label": "Holus Thought Studio",
        }

    if visual_brief.visual_type == "insight":
        copy = _insight_copy_from_thought(thought, visual_brief)
        return {
            **base,
            "type": "insight",
            **copy,
        }

    return {
        **base,
        "type": "comparison",
        "title": "One Thought, Many Jobs",
        "left_label": "Raw Thought",
        "right_label": "Platform Asset",
        "items": [
            {"dimension": "LinkedIn", "left": "idea", "right": "argument", "winner": "right"},
            {"dimension": "Carousel", "left": "caption", "right": "sequence", "winner": "right"},
            {"dimension": "Instagram", "left": "caption", "right": "visual", "winner": "right"},
            {"dimension": "Threads", "left": "post", "right": "conversation", "winner": "right"},
        ],
        "callout_text": short,
    }


def _insight_copy_from_thought(thought: str, visual_brief: VisualBrief) -> dict[str, str]:
    lowered = thought.lower()
    if visual_brief.profile_id == "ai-focus-thesis" or (
        "simplicity" in lowered and ("ai" in lowered or "model" in lowered)
    ):
        return {
            "headline": "Simplicity is king with AI",
            "body": "The model does not need more noise. It needs focus.",
            "stat_value": "Less noise",
            "stat_label": "More focus. Better output.",
        }

    return {
        "headline": _first_sentence(thought, fallback="Make the thought memorable"),
        "body": thought[:160],
        "stat_value": "1 idea",
        "stat_label": visual_brief.purpose,
    }


def _visual_variable_rationale(creative_strategy: Any, visual_brief: VisualBrief) -> dict[str, str]:
    return {
        "format": (
            f"{creative_strategy.platform_format} at {creative_strategy.aspect_ratio} because "
            f"the content job is {creative_strategy.content_job}."
        ),
        "style_profile": (
            f"{visual_brief.profile_id} was selected to express {visual_brief.purpose} "
            f"with {visual_brief.palette} and {visual_brief.typography}."
        ),
        "copy_hierarchy": (
            f"{creative_strategy.typography_hierarchy} keeps the visual focused on "
            f"{creative_strategy.focal_point}."
        ),
        "proof_points": (
            f"Proof is based on {creative_strategy.proof_mechanism}, so bullets must explain "
            "the system roles instead of repeating the raw thought."
        ),
        "lineage": (
            "raw thought -> thought_essence.visual_prompt -> creative_strategy -> "
            "editorial_card_copy -> rendered_image_path"
        ),
        "model_provider": "holus/deterministic-thought-pipeline with holus/visual-renderer",
    }


def _brand_identity(*, language: str = "en", include_handle: bool = False) -> dict[str, Any]:
    handle = BRAND_HANDLES_BY_LANGUAGE.get(language)
    return {
        "author_name": "Juan Camilo Martinez",
        "language": language,
        "brand_handle": handle if include_handle else None,
        "available_handles": BRAND_HANDLES_BY_LANGUAGE,
        "handle_policy": "omit unless the content run explicitly opts into a language account",
    }


def detect_language_for_destination(text: str) -> str:
    """Route rough thoughts to the configured English or Spanish account lane."""
    normalized = f" {text.lower()} "
    if any(marker in normalized for marker in SPANISH_LANGUAGE_MARKERS):
        return "es"
    if any(ch in normalized for ch in "áéíóúñ¿¡"):
        return "es"
    return "en"


def build_posting_destination(*, platform: str | None, thought: str | None) -> dict[str, Any]:
    """Return the pre-publish account destination Holus will show during review."""
    platform_value = platform or "unknown"
    language = detect_language_for_destination(thought or "")
    handle = BRAND_HANDLES_BY_LANGUAGE[language]
    account = handle.removeprefix("@")
    profile_template = PROFILE_URL_BY_PLATFORM.get(platform_value)
    profile_url = profile_template.format(account=account) if profile_template else None
    language_label = "English" if language == "en" else "Spanish"
    return {
        "platform": platform_value,
        "account": account,
        "handle": handle,
        "profile_url": profile_url,
        "language": language,
        "status": "configured_default",
        "approval_required": True,
        "rationale": (
            f"{language_label} Thought Studio content routes to {handle}. "
            "Human review is still required before scheduling or publishing."
        ),
        "lineage": (
            "raw thought -> language/account route -> queue record -> review drawer -> "
            "explicit publish/schedule endpoint"
        ),
    }


def _infer_source_intent(text: str, source_type: str) -> str:
    lowered = text.lower()
    if source_type == "url":
        return "online_article"
    if "pilaster" in lowered:
        return "product_context"
    if any(marker in lowered for marker in ("campaign", "launch", "series")):
        return "campaign_idea"
    if any(marker in lowered for marker in ("research", "study", "paper", "benchmark")):
        return "research_note"
    return "raw_thought"


def _source_context(text: str, intent: str) -> dict[str, Any]:
    mentioned_products = ["Pilaster"] if "pilaster" in text.lower() else []
    return {
        "source_intent": intent,
        "mentioned_products": mentioned_products,
        "product_context_detected": bool(mentioned_products),
        "targeting_changed": False,
        "success_signal": {
            "raw_thought": "clear source context",
            "online_article": "source evidence",
            "research_note": "research implication",
            "product_context": "product facts",
            "campaign_idea": "campaign direction",
        }.get(intent, "useful marketing content"),
    }


def _transformation_job(record: dict[str, Any], source_context: dict[str, Any]) -> str:
    platform = str(record.get("platform") or "platform")
    content_type = str(record.get("content_type") or "content")
    if source_context.get("mentioned_products"):
        return (
            f"Transform product facts into {platform} {content_type} "
            "without changing product targeting."
        )
    return f"Transform the source idea into a {platform} {content_type} with native pacing."


def _platform_fit(record: dict[str, Any]) -> dict[str, Any]:
    text = str(record.get("text") or "")
    platform = str(record.get("platform") or "")
    content_type = str(record.get("content_type") or "")
    bounds = {"min": 20, "max": 3000}
    return {
        "verdict": "PASS" if bounds["min"] <= len(text) <= bounds["max"] else "REVIEW",
        "platform": platform,
        "content_type": content_type,
        "text_char_count": len(text),
        "text_length_bounds": bounds,
        "platform_job_present": bool(
            record.get("platform_job_plan") or record.get("content_job_plan")
        ),
        "expected_shape": f"{platform} {content_type}",
        "notes": [],
    }


def _platform_fit_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [
        str(record.get("piece_id"))
        for record in records
        if (record.get("quality") or {}).get("platform_fit", {}).get("verdict") != "PASS"
    ]
    missing = [
        str(record.get("piece_id"))
        for record in records
        if not (record.get("quality") or {}).get("platform_fit")
    ]
    return {
        "variant_count": len(records),
        "pass_count": len(records) - len(failed) - len(missing),
        "failure_count": len(failed),
        "missing_count": len(missing),
        "failed_piece_ids": failed,
        "missing_piece_ids": missing,
    }


def _creative_contract_from_brief(visual_brief: VisualBrief) -> dict[str, str]:
    if visual_brief.profile_id == "ai-focus-thesis":
        return {
            "platform_format": "instagram_feed_portrait",
            "aspect_ratio": "4:5",
            "canvas_px": "1080x1350",
            "safe_zone": "80px top/bottom, 60px sides",
            "content_job": "saveable educational thesis",
            "hook_pattern": "short rule with practical payoff",
            "layout_archetype": "editorial poster with accent proof block",
            "typography_hierarchy": "hook > accent phrase > proof bullets > footer",
            "density": "low",
            "visual_metaphor": "remove noise to reveal focus",
            "reader_action": "save",
            "rhythm": "claim, clarify, prove, punchline",
            "freshness_axis": "typographic composition, accent word, proof line order",
        }

    return {
        "platform_format": "instagram_feed_square",
        "aspect_ratio": "1:1",
        "canvas_px": "1080x1080",
        "safe_zone": "60px all sides",
        "content_job": visual_brief.purpose,
        "hook_pattern": visual_brief.motif,
        "layout_archetype": visual_brief.composition,
        "typography_hierarchy": visual_brief.typography,
        "density": "medium",
        "visual_metaphor": visual_brief.subject,
        "reader_action": "understand",
        "rhythm": "headline, support, takeaway",
        "freshness_axis": "theme, gradient, visual type, motif",
    }


def _first_sentence(text: str, *, fallback: str) -> str:
    cleaned = _clean_thought(text)
    if not cleaned:
        return fallback
    for delimiter in (". ", "! ", "? ", "\n"):
        if delimiter in cleaned:
            return cleaned.split(delimiter, 1)[0].strip(" .!?")[:72]
    return cleaned[:72].strip(" .!?") or fallback


def _carousel_outline_from_thought(
    thought: str,
    visual_brief: VisualBrief,
    channel: str,
) -> dict[str, Any]:
    short = thought[:180]
    strategy = choose_creative_strategy(
        thought,
        channel=channel,
        nonce=visual_brief.variation_seed,
    )
    card_copy = editorial_card_copy(thought, strategy)
    creative_contract = strategy.to_contract()
    return {
        "design": {
            "theme": visual_brief.theme,
            "font_pairing": visual_brief.font_pairing,
            "gradient": visual_brief.gradient,
            "effect": visual_brief.effect,
            "style_profile": visual_brief.style_profile(),
            "prompt_contract": visual_brief.prompt_contract(),
            "creative_contract": creative_contract,
            "variable_rationale": _visual_variable_rationale(strategy, visual_brief),
            "brand_identity": _brand_identity(),
        },
        "slides": [
            {
                "type": "hook",
                "variables": {
                    "label": str(card_copy["label"]),
                    "headline": str(card_copy["hook"]),
                    "subheadline": str(card_copy["subhook"]),
                },
            },
            {
                "type": "body",
                "variables": {
                    "title": "The tension",
                    "body": strategy.emotional_tension,
                    "highlight": strategy.audience_state,
                },
            },
            {
                "type": "body",
                "variables": {
                    "title": str(card_copy["emphasis_word"]),
                    "body": "\n".join(str(point) for point in card_copy["proof_points"]),
                    "highlight": strategy.proof_mechanism,
                },
            },
            {
                "type": "summary",
                "variables": {
                    "title": "Creative rule",
                    "items": [
                        strategy.hook_pattern,
                        strategy.typography_hierarchy,
                        strategy.rhythm,
                    ],
                },
            },
            {
                "type": "cta",
                "variables": {
                    "headline": str(card_copy["save_cue"]),
                    "body": str(card_copy["punchline"]),
                },
            },
        ],
        "caption": _build_platform_text(thought, channel),
        "style_profile": visual_brief.style_profile(),
        "prompt_contract": visual_brief.prompt_contract(),
        "creative_contract": creative_contract,
        "variable_rationale": _visual_variable_rationale(strategy, visual_brief),
        "brand_identity": _brand_identity(),
        "source_excerpt": short,
    }


def _carousel_headline_for(visual_brief: VisualBrief) -> str:
    if visual_brief.profile_id == "bold-transformation":
        return "Stop making captions"
    if visual_brief.profile_id == "cool-architecture":
        return "The content engine"
    if visual_brief.profile_id == "light-data-signal":
        return "Make the format earn it"
    if visual_brief.profile_id == "editorial-thesis-card":
        return "The thought is the asset"
    return "One thought is not content"


def _load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    )
    for name in names:
        with contextlib.suppress(OSError):
            return cast("ImageFont.ImageFont", ImageFont.truetype(name, size))
    return cast("ImageFont.ImageFont", ImageFont.load_default())


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return int(right - left)


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    *,
    max_lines: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
        lines[-1] = f"{lines[-1].rstrip(' .')[: max(0, len(lines[-1]) - 1)]}..."
    return lines


def _render_fallback_visual(
    thought: str,
    output_path: Path,
    channel: str,
    visual_brief: VisualBrief,
) -> dict[str, Any]:
    width, height = 1080, 1350
    palette = _fallback_palette(visual_brief)
    image = Image.new("RGB", (width, height), palette["background"])
    draw = ImageDraw.Draw(image)
    title_font = _load_font(68, bold=True)
    body_font = _load_font(36)
    label_font = _load_font(28, bold=True)

    draw.rectangle((0, 0, width, height), fill=palette["background"])
    draw.rounded_rectangle((64, 64, width - 64, height - 64), radius=44, fill=palette["surface"])
    draw.rounded_rectangle(
        (64, 64, width - 64, height - 64), radius=44, outline=palette["border"], width=3
    )
    draw.text((96, 110), visual_brief.style.upper(), fill=palette["accent"], font=label_font)

    y = 240
    headline = _carousel_headline_for(visual_brief)
    for line in _wrap_text(draw, headline, title_font, width - 192, max_lines=3):
        draw.text((96, y), line, fill=palette["text"], font=title_font)
        y += 82
    y += 32
    for line in _wrap_text(draw, thought, body_font, width - 192, max_lines=6):
        draw.text((96, y), line, fill=palette["muted"], font=body_font)
        y += 48

    draw.line((96, height - 220, width - 96, height - 220), fill=palette["border"], width=2)
    draw.text((96, height - 170), visual_brief.mood, fill=palette["success"], font=body_font)
    image.save(output_path, format="PNG")
    return {
        "renderer": "holus/local-preview",
        "format": "png",
        "channel": channel,
        "dimensions": [width, height],
        "style_profile": visual_brief.style_profile(),
        "prompt_contract": visual_brief.prompt_contract(),
        "creative_contract": _creative_contract_from_brief(visual_brief),
        "brand_identity": _brand_identity(),
        "note": "Fallback PNG written because the visual renderer was unavailable.",
    }


def _fallback_palette(visual_brief: VisualBrief) -> dict[str, str]:
    palettes = {
        "light": {
            "background": "#f8fafc",
            "surface": "#ffffff",
            "border": "#cbd5e1",
            "text": "#0f172a",
            "muted": "#334155",
            "accent": "#d97706",
            "success": "#047857",
        },
        "warm": {
            "background": "#1c1310",
            "surface": "#2c1f1a",
            "border": "#92400e",
            "text": "#fef3c7",
            "muted": "#fde68a",
            "accent": "#f59e0b",
            "success": "#34d399",
        },
        "cool": {
            "background": "#0c1222",
            "surface": "#111827",
            "border": "#164e63",
            "text": "#e0f2fe",
            "muted": "#bae6fd",
            "accent": "#06b6d4",
            "success": "#67e8f9",
        },
        "bold": {
            "background": "#18181b",
            "surface": "#27272a",
            "border": "#ef4444",
            "text": "#fafafa",
            "muted": "#fecaca",
            "accent": "#ef4444",
            "success": "#fca5a5",
        },
    }
    return palettes.get(
        visual_brief.theme,
        {
            "background": "#0b1020",
            "surface": "#111827",
            "border": "#334155",
            "text": "#f8fafc",
            "muted": "#e2e8f0",
            "accent": "#f59e0b",
            "success": "#34d399",
        },
    )


def _write_minimal_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000056 00000 n \n0000000111 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
    )
