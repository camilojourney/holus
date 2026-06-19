"""Visual generation stage of the idea-injection pipeline.

Generates companion visual specs (flowcharts, architecture diagrams,
comparisons, etc.) for text posts and renders them to PNG using
the Playwright-based visual engine. Includes visual variety routing
to prevent repetitive visual types across consecutive posts.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from holus.agents.marketing.idea_utils import _call, _strip_fences

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Visual designer system prompt (Layer 3 fallback)
# ---------------------------------------------------------------------------

VISUAL_DESIGNER_SYSTEM = """You design deterministic visuals for social media posts only after
the content job router and visual necessity gate have confirmed that a visual is needed.
Given a routed post's text, extract the key concepts and design a visual that TEACHES
the core idea independently — someone should understand your visual WITHOUT reading the post.

If the routing context says needs_visual=false, return {"type": "none", "reason": "visual gate rejected companion visual"}.
If AI images are forbidden, do not describe a generated scene. Use a deterministic visual type.

You have 7 visual types. Pick the one that best fits the post's structure:

1. "flowchart" — process diagrams, decision trees, pipelines.
   USE WHEN: post describes a sequential process, workflow, or pipeline.
   JSON: {"type": "flowchart", "title": "max 8 words",
          "nodes": [{"id": "1", "label": "Step Name", "description": "optional 5-10 words"}],
          "connections": [{"from_id": "1", "to_id": "2", "label": "optional"}],
          "layout": "vertical"}

2. "architecture" — system component diagrams, layered architectures.
   USE WHEN: post describes system components, tech stacks, or how parts connect.
   JSON: {"type": "architecture", "title": "max 8 words",
          "layers": [{"name": "Layer Name", "components": [{"name": "Component", "description": "3-5 words"}]}],
          "connections": [{"from_layer": 0, "from_comp": 0, "to_layer": 1, "to_comp": 0}]}

3. "comparison" — side-by-side comparison tables.
   USE WHEN: post compares two approaches, tools, or before/after.
   JSON: {"type": "comparison", "title": "max 8 words",
          "left_label": "Option A", "right_label": "Option B",
          "items": [{"dimension": "Speed", "left": "Slow", "right": "Fast", "winner": "right"}]}

4. "data_viz" — charts with data points.
   USE WHEN: post has numbers, stats, rankings, or quantifiable comparisons.
   JSON: {"type": "data_viz", "chart_type": "bar|line|metric",
          "title": "max 6 words",
          "data_points": [{"label": "X", "value": 85}],
          "highlight_index": 0, "source_label": "optional"}

5. "code_card" — code snippet showcase.
   USE WHEN: post discusses specific code, APIs, or implementation patterns.
   JSON: {"type": "code_card", "title": "max 8 words",
          "code": "actual code snippet (10-20 lines max)",
          "language": "python", "annotation": "what this code demonstrates"}

6. "research_card" — hero stat + chart + source citation.
   USE WHEN: post cites research, studies, or has a striking headline number.
   JSON: {"type": "research_card", "title": "max 8 words",
          "key_stat": "73%", "key_stat_label": "of agents fail in production",
          "chart_type": "bar", "data_points": [{"label": "X", "value": 85}],
          "callout_text": "key insight sentence", "source_citation": "Author 2024"}

7. "insight" — branded card with headline + stat (fallback).
   USE WHEN: post is purely philosophical, no process/comparison/data.
   JSON: {"type": "insight", "headline": "max 8 words",
          "body": "optional 1-2 sentences",
          "stat_value": "optional e.g. 3x", "stat_label": "optional label"}

DECISION PRIORITY: flowchart > architecture > comparison > data_viz > code_card > research_card > insight.
If the post has ANY sequential process, use flowchart.
If the post has ANY system components, use architecture.
If the post compares two things, use comparison.
Only fall back to insight if nothing else fits.

The visual MUST teach independently — it's a scroll-stopper, not decoration.
Keep labels SHORT (max 3 words) so they don't overlap.

Return ONLY the JSON object. No markdown fences, no explanation."""


# ---------------------------------------------------------------------------
# Visual variety routing
# ---------------------------------------------------------------------------

_visual_variety_cache: dict[str, Any] = {}


def _load_visual_variety_config() -> dict[str, Any]:
    """Load config/visual-variety.yaml with module-level caching."""
    if "config" not in _visual_variety_cache:
        config_path = Path("config/visual-variety.yaml")
        if config_path.exists():
            _visual_variety_cache["config"] = yaml.safe_load(config_path.read_text())
        else:
            logger.warning("visual-variety.yaml not found, using defaults")
            _visual_variety_cache["config"] = {
                "weights": {
                    "flowchart": 1.0,
                    "architecture": 1.0,
                    "comparison": 1.0,
                    "data_viz": 1.0,
                    "code_card": 0.8,
                    "research_card": 0.8,
                    "insight": 0.5,
                },
                "recency_penalty": 0.5,
                "recency_window_days": 3,
                "topic_signals": {},
            }
    result: dict[str, Any] = _visual_variety_cache["config"]
    return result


def _pick_visual_type(post_text: str, *, override: str | None = None) -> str:
    """Select a visual type using weighted random sampling with topic signals and recency penalty."""
    config = _load_visual_variety_config()
    valid_types = list(config["weights"].keys())

    # 1. If override is provided and valid, return it immediately
    if override and override in valid_types:
        return override

    # 2. Start with base weights
    weights: dict[str, float] = dict(config["weights"])

    # 3. Apply topic signal boosting
    post_lower = post_text.lower()
    for vtype, keywords in config.get("topic_signals", {}).items():
        if vtype not in weights:
            continue
        for kw in keywords:
            if kw.lower() in post_lower:
                weights[vtype] *= 1.5
                break  # one match per type is enough

    # 4. Apply recency penalty from content-queue files
    recency_window = config.get("recency_window_days", 3)
    recency_penalty = config.get("recency_penalty", 0.5)
    queue_dir = Path("data/content-queue")
    if queue_dir.exists():
        cutoff = datetime.now(UTC) - timedelta(days=recency_window)
        for json_file in queue_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text())
                created_str = data.get("generated_at", "")
                if not created_str:
                    continue
                created = datetime.fromisoformat(created_str)
                if created >= cutoff:
                    # Check visual_type field first, then fall back to visual_spec.type
                    vtype = data.get("visual_type") or (data.get("visual_spec", {}) or {}).get(
                        "type"
                    )
                    if vtype and vtype in weights:
                        weights[vtype] *= recency_penalty
            except Exception:
                continue

    # 5. Normalize weights to probabilities
    types = list(weights.keys())
    vals = [weights[t] for t in types]
    total = sum(vals)
    if total == 0:
        return random.choice(types)
    probs = [v / total for v in vals]

    # 6. Sample one type
    chosen = random.choices(types, weights=probs, k=1)[0]
    return chosen


def _generate_visual_spec(
    post_text: str,
    fmt: str,
    platform: str,
    *,
    temperature: float = 0.3,
    visual_type: str | None = None,
) -> dict[str, Any] | None:
    """Have Sonnet design a visual spec for the post. Returns spec dict or None."""
    if fmt not in ("text_post", "thread", "instagram_caption"):
        return None  # Carousels and video scripts don't need companion images

    try:
        chosen_type = _pick_visual_type(post_text, override=visual_type)
        user_msg = f"""Design a visual for this {platform} {fmt}:

{post_text[:2000]}

You MUST use visual type: {chosen_type}. Design the best possible {chosen_type} for this content.

Return JSON only."""
        raw = _call(
            "anthropic/claude-sonnet-4-6", VISUAL_DESIGNER_SYSTEM, user_msg, temperature=temperature
        )
        cleaned = _strip_fences(raw)
        spec: dict[str, Any] = json.loads(cleaned)
        return spec
    except Exception as exc:
        logger.debug("Visual spec generation failed: %s", exc)
        return None


def _apply_style_controls(variables: dict[str, Any], visual_spec: dict[str, Any]) -> None:
    """Carry Thought Studio style profiles through spec conversion."""
    style_profile = visual_spec.get("style_profile")
    if not isinstance(style_profile, dict):
        return

    control_map = {
        "theme": "theme",
        "font_pairing": "font_pairing",
        "gradient": "background_gradient",
        "effect": "visual_effect",
    }
    for source_key, target_key in control_map.items():
        value = style_profile.get(source_key)
        if isinstance(value, str) and value and value != "none":
            variables.setdefault(target_key, value)


def _render_visual(visual_spec: dict[str, Any], output_path: Path) -> bool:
    """Render a visual spec to PNG using PlaywrightEngine. Returns True on success."""
    import asyncio

    async def _do_render() -> bytes:
        from holus.visual.dispatcher import (
            RefinedVisualSource,
            VisualAssetKind,
            VisualDispatcher,
            VisualDispatchRequest,
            VisualDispatchStatus,
            VisualProvider,
        )
        from holus.visual.models import OutputFormat, RenderSpec
        from holus.visual.spec_converter import (
            architecture_to_spec,
            code_card_to_spec,
            comparison_to_spec,
            data_viz_to_spec,
            flowchart_to_spec,
            insight_to_spec,
            research_card_to_spec,
        )

        spec_type = visual_spec.get("type", "insight")
        author = _visual_author_context(visual_spec)

        if spec_type == "flowchart":
            render_spec = flowchart_to_spec({**visual_spec, **author})
        elif spec_type == "architecture":
            render_spec = architecture_to_spec({**visual_spec, **author})
        elif spec_type == "comparison":
            render_spec = comparison_to_spec({**visual_spec, **author})
        elif spec_type == "code_card":
            render_spec = code_card_to_spec({**visual_spec, **author})
        elif spec_type == "research_card":
            render_spec = research_card_to_spec({**visual_spec, **author})
        elif spec_type == "data_viz":
            render_spec = data_viz_to_spec(visual_spec)
            render_spec.variables["author_name"] = author["author_name"]
        elif spec_type == "instagram_editorial_card":
            creative_contract = visual_spec.get("creative_contract", {})
            if not isinstance(creative_contract, dict):
                creative_contract = {}
            render_spec = RenderSpec(
                template="single_image/editorial_poster",
                variables={
                    "label": str(visual_spec.get("label", "Prompt craft")),
                    "hook": str(visual_spec.get("hook", visual_spec.get("headline", ""))),
                    "subhook": str(visual_spec.get("subhook", visual_spec.get("body", ""))),
                    "emphasis_word": str(visual_spec.get("emphasis_word", "Focus")),
                    "proof_points": [
                        str(point) for point in visual_spec.get("proof_points", [])
                    ],
                    "punchline": str(visual_spec.get("punchline", "")),
                    "save_cue": str(visual_spec.get("save_cue", "Save this")),
                    "composition_axis": str(
                        creative_contract.get("composition_axis", "left_anchor")
                    ),
                    "density": str(creative_contract.get("density", "low")),
                    "novelty_device": str(creative_contract.get("novelty_device", "rule label")),
                    "visual_metaphor": str(
                        creative_contract.get("visual_metaphor", "signal separated from noise")
                    ),
                    **author,
                },
                output_format=OutputFormat.PNG,
                viewport_width=1080,
                viewport_height=1350,
            )
        else:
            # insight fallback
            body_text = visual_spec.get("body", visual_spec.get("headline", ""))
            render_spec = insight_to_spec(
                text=body_text,
                stat=visual_spec.get("stat_value"),
            )
            if visual_spec.get("headline"):
                render_spec.variables["headline"] = visual_spec["headline"]
            if body_text:
                render_spec.variables["body"] = body_text
            if visual_spec.get("stat_value"):
                render_spec.variables["stat_value"] = visual_spec["stat_value"]
            if visual_spec.get("stat_label"):
                render_spec.variables["stat_label"] = visual_spec["stat_label"]
            render_spec.variables.update(author)

        _apply_style_controls(render_spec.variables, visual_spec)
        source_payload = visual_spec.get("refined_visual_source")
        refined_source = (
            RefinedVisualSource.model_validate(source_payload)
            if isinstance(source_payload, dict)
            else None
        )
        from holus.visual.proximity_router import VisualConceptRoute

        route_payload = visual_spec.get("visual_route")
        visual_route = (
            VisualConceptRoute.model_validate(route_payload)
            if isinstance(route_payload, dict)
            else None
        )
        from holus.visual.production_plan import VisualProductionPlan

        plan_payload = visual_spec.get("visual_plan")
        visual_plan = (
            VisualProductionPlan.model_validate(plan_payload)
            if isinstance(plan_payload, dict)
            else None
        )
        request_id = str(
            visual_spec.get("request_id")
            or f"visual_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        )
        result = await VisualDispatcher().dispatch(
            VisualDispatchRequest(
                request_id=request_id,
                platform=str(visual_spec.get("platform", "linkedin")),
                asset_kind=VisualAssetKind.SINGLE_IMAGE,
                provider=VisualProvider.HTML_RENDERER,
                render_spec=render_spec,
                output_path=output_path,
                log_path=Path(
                    str(visual_spec.get("visual_dispatch_log_path", "data/logs/image-dispatch.jsonl"))
                ),
                refined_source=refined_source,
                visual_route=visual_route,
                visual_plan=visual_plan,
                metadata={
                    "source": "visual_pipeline",
                    "visual_type": spec_type,
                    "template": render_spec.template,
                    "visual_strategy": visual_spec.get("visual_strategy"),
                },
            )
        )
        if result.status != VisualDispatchStatus.SUCCEEDED or result.output_path is None:
            msg = result.error or "Visual dispatcher failed without an error message"
            raise RuntimeError(msg)
        visual_spec["visual_dispatch"] = {
            "request_id": result.request_id,
            "provider": result.provider.value,
            "status": result.status.value,
            "log_path": str(result.log_path),
            "sidecar_path": str(
                result.output_path.with_suffix(result.output_path.suffix + ".dispatch.json")
            ),
            "model_or_tool": result.model_or_tool,
        }
        return result.output_path.read_bytes()

    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            png_bytes = asyncio.run(_do_render())
        else:
            # The public helper is sync, but API tests call it from an active
            # event loop. Run the async dispatcher in a worker thread.
            import concurrent.futures

            def _run_render_in_thread() -> bytes:
                return asyncio.run(_do_render())

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                png_bytes = pool.submit(_run_render_in_thread).result(timeout=30)

        output_path.write_bytes(png_bytes)
        return True
    except Exception as exc:
        logger.debug("Visual render failed: %s", exc)
        print(f"  ⚠ Visual render failed: {exc}")
        return False


def _visual_author_context(visual_spec: dict[str, Any]) -> dict[str, str]:
    """Return author variables without forcing a social handle."""
    brand_identity = visual_spec.get("brand_identity")
    if not isinstance(brand_identity, dict):
        brand_identity = {}

    author_name = visual_spec.get("author_name", brand_identity.get("author_name", "Juan Camilo Martinez"))
    brand_handle = visual_spec.get("brand_handle", brand_identity.get("brand_handle", ""))
    return {
        "author_name": str(author_name) if author_name else "",
        "brand_handle": str(brand_handle) if brand_handle else "",
    }
