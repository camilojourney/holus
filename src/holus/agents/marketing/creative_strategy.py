"""Creative strategy primitives for Thought Studio visuals.

This module names the decisions that make a visual feel designed instead of
template-filled. The renderer consumes these choices directly, and future agent
passes can score or mutate them before rendering.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Literal

CreativeStrategyType = Literal[
    "rule_card",
    "mistake_reframe",
    "before_after",
    "framework_steps",
    "contrarian_thesis",
    "checklist",
]


@dataclass(frozen=True)
class CreativeStrategy:
    strategy_id: str
    strategy_type: CreativeStrategyType
    platform_format: str
    aspect_ratio: str
    canvas_px: str
    safe_zone: str
    content_job: str
    audience_state: str
    emotional_tension: str
    hook_pattern: str
    hook_voice: str
    layout_archetype: str
    composition_axis: str
    focal_point: str
    typography_hierarchy: str
    type_scale: str
    density: str
    pacing: str
    visual_metaphor: str
    proof_mechanism: str
    reader_action: str
    cta_style: str
    rhythm: str
    novelty_device: str
    continuity_rule: str
    freshness_axis: str
    negative_space: str
    accessibility_rule: str
    variation_seed: str

    def to_contract(self) -> dict[str, str]:
        return asdict(self)


def choose_creative_strategy(thought: str, *, channel: str, nonce: str) -> CreativeStrategy:
    """Choose a content-aware visual strategy with deterministic variation."""
    lowered = thought.lower()
    digest = hashlib.sha256(f"{thought}|{channel}|{nonce}|creative".encode()).hexdigest()
    seed = digest[:12]

    if _is_ai_workflow_harness(lowered):
        return CreativeStrategy(
            strategy_id="ai_workflow_harness_card",
            strategy_type="framework_steps",
            platform_format="instagram_feed_portrait",
            aspect_ratio="4:5",
            canvas_px="1080x1350",
            safe_zone="80px top/bottom, 60px sides",
            content_job="turn a tool list into a repeatable AI operating system",
            audience_state="builder is comparing models but needs system architecture",
            emotional_tension="model choice versus harness design",
            hook_pattern="harness thesis",
            hook_voice="direct builder architecture note",
            layout_archetype="systems poster with role proof list",
            composition_axis=_pick(seed, "split_weight", "left_anchor", "center_stack"),
            focal_point="model-versus-workflow thesis",
            typography_hierarchy="harness label > thesis > system name > role proof > footer",
            type_scale="oversized thesis, large harness word, compact role proof",
            density="medium",
            pacing="thesis, role map, operating lesson",
            visual_metaphor="orchestrated harness instead of isolated model",
            proof_mechanism="role map: plan, run, hands, review, fallback, daily work",
            reader_action="save",
            cta_style="save the architecture",
            rhythm="claim, map, proof, operating rule",
            novelty_device=_pick(seed, "role map", "architecture label", "system contrast"),
            continuity_rule="repeat amber accents for architecture cues and proof bullets",
            freshness_axis="role ordering, proof language, composition axis",
            negative_space="clear right-side breathing room around the role map",
            accessibility_rule="large thesis, short proof lines, high contrast",
            variation_seed=seed,
        )

    if _is_ai_prompt_lesson(lowered):
        return CreativeStrategy(
            strategy_id="ai_prompt_rule_card",
            strategy_type="rule_card",
            platform_format="instagram_feed_portrait",
            aspect_ratio="4:5",
            canvas_px="1080x1350",
            safe_zone="80px top/bottom, 60px sides",
            content_job="saveable educational thesis",
            audience_state="builder knows AI is powerful but overcomplicates prompts",
            emotional_tension="complexity feels professional but clarity performs better",
            hook_pattern="short rule with practical payoff",
            hook_voice="direct founder lesson",
            layout_archetype="editorial poster with accent proof block",
            composition_axis=_pick(seed, "left_anchor", "center_stack", "split_weight"),
            focal_point="rule headline",
            typography_hierarchy="hook > accent phrase > proof bullets > footer",
            type_scale="oversized hook, large accent, compact proof",
            density="low",
            pacing="claim, explain, prove, close",
            visual_metaphor="remove noise to reveal focus",
            proof_mechanism="three causal proof lines",
            reader_action="save",
            cta_style="saveable rule",
            rhythm="claim, clarify, prove, punchline",
            novelty_device=_pick(seed, "hard contrast", "single accent word", "rule label"),
            continuity_rule="repeat amber accent for label, dots, and author handle",
            freshness_axis="composition axis, accent word, proof line order",
            negative_space="large top and right breathing room",
            accessibility_rule="high contrast, short lines, no text below 20px",
            variation_seed=seed,
        )

    if any(word in lowered for word in ("mistake", "wrong", "failed", "learned")):
        return CreativeStrategy(
            strategy_id="lesson_reframe_card",
            strategy_type="mistake_reframe",
            platform_format="instagram_feed_portrait",
            aspect_ratio="4:5",
            canvas_px="1080x1350",
            safe_zone="80px top/bottom, 60px sides",
            content_job="turn a mistake into a memorable lesson",
            audience_state="reader has felt the same mistake but has not named it",
            emotional_tension="old behavior versus better behavior",
            hook_pattern="mistake-to-lesson reframe",
            hook_voice="reflective but concrete",
            layout_archetype="before/after editorial split",
            composition_axis=_pick(seed, "split_weight", "left_anchor", "center_stack"),
            focal_point="lesson headline",
            typography_hierarchy="mistake label > lesson headline > contrast pair > CTA",
            type_scale="large lesson, medium contrast labels",
            density="medium",
            pacing="confession, reframe, practical takeaway",
            visual_metaphor="old path crossing into clean path",
            proof_mechanism="before/after contrast",
            reader_action="save",
            cta_style="remember this",
            rhythm="setup, tension, correction, takeaway",
            novelty_device=_pick(seed, "crossed label", "contrast block", "small confession"),
            continuity_rule="same grid, one accent color, no decorative clutter",
            freshness_axis="contrast language and visual split",
            negative_space="one quiet zone around the lesson",
            accessibility_rule="clear contrast pair, no dense paragraph",
            variation_seed=seed,
        )

    return CreativeStrategy(
        strategy_id="generic_thesis_card",
        strategy_type="contrarian_thesis",
        platform_format="instagram_feed_portrait",
        aspect_ratio="4:5",
        canvas_px="1080x1350",
        safe_zone="80px top/bottom, 60px sides",
        content_job="make one thought feel worth saving",
        audience_state="reader is scanning for a useful idea",
        emotional_tension="surface thought versus deeper implication",
        hook_pattern="clear thesis",
        hook_voice="concise operator note",
        layout_archetype="editorial thesis card",
        composition_axis=_pick(seed, "center_stack", "left_anchor", "split_weight"),
        focal_point="thesis headline",
        typography_hierarchy="thesis > support > takeaway",
        type_scale="large headline, readable body, small footer",
        density="low",
        pacing="thesis, support, takeaway",
        visual_metaphor="signal separated from noise",
        proof_mechanism="one supporting reason",
        reader_action="save",
        cta_style="save this",
        rhythm="claim, reason, takeaway",
        novelty_device=_pick(seed, "oversized word", "quiet grid", "small label"),
        continuity_rule="consistent margins and accent color",
        freshness_axis="hook framing and composition axis",
        negative_space="at least 35 percent open space",
        accessibility_rule="mobile-first type and strong contrast",
        variation_seed=seed,
    )


def editorial_card_copy(thought: str, strategy: CreativeStrategy) -> dict[str, Any]:
    """Create renderer variables from a thought and strategy."""
    lowered = thought.lower()
    if _is_ai_workflow_harness(lowered):
        return {
            "label": "Workflow harness",
            "hook": "The model is not the workflow",
            "subhook": "Claude plans. Codex runs. Skills are the hands. Reviews and fallbacks keep the system honest.",
            "emphasis_word": "The harness",
            "proof_points": [
                "Give each model a job.",
                "Let plans run for hours or days.",
                "Make the system disagree before it ships.",
            ],
            "punchline": "The workflow gets stronger when planning, execution, review, and fallback are separate jobs.",
            "save_cue": "Save the architecture",
        }

    if _is_ai_prompt_lesson(lowered):
        return {
            "label": "Prompt craft",
            "hook": "Simplicity is king with AI",
            "subhook": "The model already knows a lot. Your job is to aim it.",
            "emphasis_word": "Less noise",
            "proof_points": [
                "Simple input creates clear focus.",
                "Clear focus gives the model a job.",
                "A clear job produces better output.",
            ],
            "punchline": "The skill is not adding more. It is removing what gets in the way.",
            "save_cue": "Save the rule",
        }

    if "automate judgment" in lowered and "taste" in lowered:
        return {
            "label": "Mistake-to-lesson reframe",
            "hook": "Do not automate judgment before taste",
            "subhook": "The system can move faster only after the standard is clear.",
            "emphasis_word": "Taste first",
            "proof_points": [
                "Name what good looks like.",
                "Turn that taste into checks.",
                "Then let automation scale it.",
            ],
            "punchline": "Automation without taste only multiplies weak judgment.",
            "save_cue": "Remember this",
        }

    if "product demo" in lowered and "tour" in lowered:
        return {
            "label": "Clear thesis",
            "hook": "A demo is not a tour",
            "subhook": "It is one painful before-and-after shown clearly.",
            "emphasis_word": "Show pain",
            "proof_points": [
                "Start with the old frustration.",
                "Show the moment it changes.",
                "End with the new behavior.",
            ],
            "punchline": "The best demo makes the value obvious before the feature list starts.",
            "save_cue": "Save this",
        }

    if "creators" in lowered and "more ideas" in lowered:
        return {
            "label": "Creator system",
            "hook": "Creators need packaging, not more ideas",
            "subhook": "The idea already exists. The system has to make it usable.",
            "emphasis_word": "Package it",
            "proof_points": [
                "Find the sharpest sentence.",
                "Choose the platform job.",
                "Turn it into a repeatable format.",
            ],
            "punchline": "The win is not more raw material. It is a better creative machine.",
            "save_cue": "Save the frame",
        }

    if "ai systems" in lowered and "calm" in lowered:
        return {
            "label": "Product rule",
            "hook": "Calm AI hides the complexity",
            "subhook": "The user should only see one obvious next action.",
            "emphasis_word": "Calm wins",
            "proof_points": [
                "Absorb the hard decisions.",
                "Expose the next useful move.",
                "Keep the workflow quiet.",
            ],
            "punchline": "A great AI product feels simple because the system did the thinking.",
            "save_cue": "Save the rule",
        }

    first = _first_sentence(thought, fallback="Make the idea easier to use")
    return {
        "label": strategy.hook_pattern.title(),
        "hook": first,
        "subhook": _shorten(thought, 118),
        "emphasis_word": _emphasis_for_strategy(strategy),
        "proof_points": _proof_points_for_strategy(strategy),
        "punchline": _punchline_for_strategy(strategy),
        "save_cue": strategy.cta_style.title(),
    }


def _is_ai_prompt_lesson(lowered: str) -> bool:
    return any(signal in lowered for signal in ("simplicity", "simple", "focus", "prompt")) and (
        "ai" in lowered or "model" in lowered
    )


def _is_ai_workflow_harness(lowered: str) -> bool:
    signals = ("claude", "codex", "cursor", "deepseek", "agy", "skills")
    return (
        any(signal in lowered for signal in ("workflow", "harness"))
        and sum(signal in lowered for signal in signals) >= 3
    )


def _pick(seed: str, *values: str) -> str:
    return values[int(seed[:4], 16) % len(values)]


def _first_sentence(text: str, *, fallback: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return fallback
    for delimiter in (". ", "! ", "? ", "\n"):
        if delimiter in cleaned:
            return _shorten(cleaned.split(delimiter, 1)[0].strip(" .!?"), 72) or fallback
    return _shorten(cleaned.strip(" .!?"), 72) or fallback


def _shorten(text: str, limit: int) -> str:
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= limit:
        return cleaned
    truncated = cleaned[: max(0, limit - 1)].rstrip(" .,")
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0].rstrip(" .,")
    return f"{truncated}."


def _emphasis_for_strategy(strategy: CreativeStrategy) -> str:
    if strategy.strategy_type == "mistake_reframe":
        return "The lesson"
    if strategy.strategy_type == "framework_steps":
        return "The steps"
    if strategy.strategy_type == "checklist":
        return "Check this"
    return "The signal"


def _proof_points_for_strategy(strategy: CreativeStrategy) -> list[str]:
    if strategy.strategy_type == "mistake_reframe":
        return [
            "Name the old behavior.",
            "Show the better move.",
            "Give the reader one rule.",
        ]
    return [
        "One clear idea.",
        "One useful frame.",
        "One reason to save.",
    ]


def _punchline_for_strategy(strategy: CreativeStrategy) -> str:
    if strategy.strategy_type == "mistake_reframe":
        return "People save the lesson when the contrast is obvious."
    return "A good visual makes the idea easier to remember."
