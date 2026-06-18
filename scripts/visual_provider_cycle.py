#!/usr/bin/env python3
"""Run one visual-provider evaluation cycle.

Each cycle turns one refined content source into a route, production plan, and
generation strategy, then asks each configured provider/model pair to create one
image. Results are written as JSON so the next improvement pass can compare
providers without relying on memory or screenshots alone.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from holus.visual.dispatcher import (  # noqa: E402
    RefinedVisualSource,
    VisualAssetKind,
    VisualDispatcher,
    VisualDispatchRequest,
    VisualDispatchStatus,
    VisualProvider,
)
from holus.visual.generation_strategy import choose_visual_generation_strategy  # noqa: E402
from holus.visual.production_plan import build_visual_production_plan  # noqa: E402
from holus.visual.proximity_router import choose_visual_concept_route  # noqa: E402

DEFAULT_PROVIDER_MODELS = (
    "codex_cli_image:default",
    "agy_cli_image:Gemini 3.5 Flash (Medium)",
)

EXAMPLE_THOUGHTS = [
    ("prompt-pile-strategy", "Prompts are not strategy", "Disconnected AI prompts", "Disconnected prompts are not an AI strategy.", "Most teams do not have an AI strategy. They have a pile of disconnected prompts."),
    ("signal-card-buried", "Specific beats generic", "Specific examples beat generic advice", "One specific example beats a pile of generic advice.", "A pile of reasonable notes can bury the one card that changes the decision."),
    ("bridge-with-missing-plank", "The missing handoff", "Agent handoff failures", "One missing handoff breaks the whole AI workflow.", "An AI workflow can look complete until one missing handoff becomes the gap everyone falls through."),
    ("compass-spinning", "No evaluation, no direction", "AI evaluation", "Without evaluation, the system cannot tell progress from motion.", "Without an evaluator, an agent system is a compass spinning on a metal desk."),
    ("blueprint-vs-tools", "Tools need architecture", "AI tooling without architecture", "More tools do not create a system.", "Buying more AI tools without architecture is like stacking expensive tools beside a blank blueprint."),
    ("founder-marked-line", "The marked sentence", "Founder story artifact", "The marked sentence reveals what the system failed to explain.", "The founder points at one awkward sentence in the draft and says: this is where the system stopped sounding human."),
    ("review-queue-pause", "The pause before approve", "Human review artifact", "Good review surfaces make the reason visible before approval.", "The reviewer pauses over one content card because the reason to approve is not visible yet."),
    ("map-with-no-legend", "Routes need labels", "Model routing clarity", "A routing system without clear ownership becomes a map with no legend.", "A multi-model system without role ownership is a map with colored routes and no legend."),
    ("lens-on-blurry-plan", "Sharper constraints", "Prompt constraints", "Better constraints make the useful part of the idea visible.", "A better prompt does not add more words. It puts a sharper lens over the one thing that matters."),
    ("factory-with-one-worker", "One model cannot be the factory", "Model specialization", "One model should not own every job in the workflow.", "Asking one model to plan, build, judge, and publish is like asking one worker to run the whole factory floor."),
]


def parse_provider_model(value: str) -> tuple[VisualProvider, str | None]:
    """Parse ``provider[:model]`` into dispatcher enum + optional model name."""
    provider_value, separator, model = value.partition(":")
    provider = VisualProvider(provider_value)
    if not separator or model == "default":
        return provider, None
    return provider, model


def slug(value: str) -> str:
    """Return a filesystem-safe label."""
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
    return cleaned.lower() or "default"


async def run_cycle(args: argparse.Namespace) -> dict[str, Any]:
    """Run one provider/model visual cycle and return a report dictionary."""
    cycle_id = args.cycle_id or datetime.now(UTC).strftime("visual-cycle-%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_dir)
    prior_reports = load_prior_reports(output_root, limit=args.history_limit)
    prior_directives = improvement_directives_from_history(prior_reports)
    output_dir = output_root / cycle_id
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "image-dispatch.jsonl"

    source = RefinedVisualSource(
        piece_id=cycle_id,
        platform=args.platform,
        content_type="image_post",
        refined_text=args.source_text,
        headline=args.headline,
        topic=args.topic,
        intended_takeaway=args.takeaway,
        raw_thought_provenance=args.raw_thought,
    )
    route = choose_visual_concept_route(source)
    plan = build_visual_production_plan(source, route)
    strategy = choose_visual_generation_strategy(source, route)
    image_direction = build_ai_image_direction(
        source,
        route=route,
        plan=plan,
        platform=args.platform,
        width=args.width,
        height=args.height,
    )

    provider_models = args.provider_model or list(DEFAULT_PROVIDER_MODELS)
    results: list[dict[str, Any]] = []
    dispatcher = VisualDispatcher()
    prompt = build_cycle_prompt(source, prior_directives, image_direction=image_direction)
    prompt_hash = prompt_digest(prompt)
    for provider_model in provider_models:
        provider, model = parse_provider_model(provider_model)
        label = slug(f"{provider.value}-{model or 'default'}")
        output_path = output_dir / f"{cycle_id}-{label}.png"
        request = VisualDispatchRequest(
            request_id=f"{cycle_id}-{label}",
            platform=args.platform,
            asset_kind=VisualAssetKind.SINGLE_IMAGE,
            provider=provider,
            prompt=prompt,
            refined_source=source,
            visual_route=route,
            visual_plan=plan,
            output_path=output_path,
            output_dir=output_dir,
            log_path=log_path,
            width=args.width,
            height=args.height,
            timeout_seconds=args.timeout_seconds,
            max_attempts=args.max_attempts,
            model=model,
            metadata={
                "cycle_id": cycle_id,
                "provider_model": provider_model,
                "visual_strategy": strategy.log_summary(),
                "ai_image_direction": image_direction,
                "structured_prompt_hash": prompt_hash,
                "prior_improvement_directives": prior_directives,
            },
        )
        result = await dispatcher.dispatch(request)
        results.append(
            {
                "provider": provider.value,
                "model": model or "default",
                "status": result.status.value,
                "output_path": str(result.output_path) if result.output_path else None,
                "model_or_tool": result.model_or_tool,
                "duration_ms": result.duration_ms,
                "error": result.error,
                "visual_judge": result.metadata.get("visual_judge"),
                "structured_prompt_hash": prompt_hash,
                "next_improvements": next_improvements(result.metadata.get("visual_judge")),
                "score": score_result(result.status.value, result.metadata.get("visual_judge")),
            }
        )

    improvement_plan = build_improvement_plan(results, prior_directives)
    report = {
        "cycle_id": cycle_id,
        "created_at": datetime.now(UTC).isoformat(),
        "source": source.model_dump(mode="json"),
        "visual_route": route.model_dump(mode="json"),
        "visual_plan": plan.model_dump(mode="json"),
        "visual_strategy": strategy.model_dump(mode="json"),
        "ai_image_direction": image_direction,
        "structured_prompt_hash": prompt_hash,
        "prior_improvement_directives": prior_directives,
        "results": results,
        "summary": summarize_results(results),
        "improvement_plan": improvement_plan,
        "log_path": str(log_path),
    }
    report_path = output_dir / "cycle-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    append_history(output_root / "cycle-history.jsonl", report)
    write_improvement_markdown(output_dir / "next-improvements.md", report)
    return report


def build_ai_image_direction(
    source: RefinedVisualSource,
    *,
    route: Any,
    plan: Any,
    platform: str,
    width: int,
    height: int,
) -> dict[str, Any]:
    """Build the AI Image Director structured brief used by all providers."""
    aspect_ratio = _aspect_ratio(width, height)
    image_class = {
        "object_metaphor": "single_metaphor",
        "person_story": "story_artifact",
        "product_scene": "product_scene",
    }.get(route.mode.value, "single_metaphor")
    viewer_takeaway = source.intended_takeaway or route.viewer_takeaway
    subject = (
        "one concrete marked artifact with a visible human decision gesture"
        if image_class == "story_artifact"
        else route.subject
    )
    text = _source_text(source).lower()
    allowed_text = "STRATEGY" if "strategy" in text else None
    prompt = (
        f"Create a {image_class.replace('_', ' ')} for Holus social content. "
        f"Viewer takeaway: {viewer_takeaway}. "
        f"Subject: {subject}. "
        f"Scene: {plan.scene_script}. "
        f"Composition: {plan.composition_script}. "
        "Use a concrete editorial image, not generic AI wallpaper. "
        f"Use {aspect_ratio} composition for {platform}. "
        f"Text policy: {plan.text_policy}"
    )
    return {
        "allowed": True,
        "blocked_reason": None,
        "image_class": image_class,
        "viewer_takeaway": viewer_takeaway,
        "metaphor_mapping": {
            "concept": source.topic or viewer_takeaway,
            "visual_object": subject,
            "why_it_maps": route.rationale,
        },
        "subject": {
            "primary": subject,
            "secondary": plan.required_elements[:3],
            "forbidden_subjects": [
                "robots",
                "glowing brains",
                "fake dashboards",
                "brand logos",
                "generic corporate team photos",
            ],
        },
        "action_or_state": plan.scene_script,
        "environment": "quiet operator workbench with restrained real-world materials",
        "composition": {
            "shot_type": "close_up" if image_class == "story_artifact" else "top_down",
            "camera_angle": "editorial angle focused on the single artifact",
            "focal_point": route.subject,
            "depth": "clear focal plane with background details subdued",
            "crop_safe_area": "leave clean margin on all sides for social crop",
        },
        "lighting_and_mood": {
            "lighting": "soft side light with natural shadows",
            "mood": "calm, editorial, operator-focused",
            "contrast": "medium",
        },
        "style": {
            "medium": "photoreal_editorial",
            "texture": "matte paper, real desk materials, restrained tactile detail",
            "palette": "warm neutral base with one teal or amber accent",
            "brand_fit": "restrained builder/operator aesthetic; not glossy SaaS stock",
        },
        "output": {
            "platform": platform,
            "aspect_ratio": aspect_ratio,
            "resolution_intent": f"{width}x{height}",
        },
        "text_policy": {
            "mode": "one_short_label" if allowed_text else "none",
            "allowed_text": allowed_text,
            "font_style": "small uppercase sans label" if allowed_text else None,
            "placement": "on the single focal artifact" if allowed_text else None,
        },
        "reference_assets": [],
        "prompt": prompt,
        "negative_prompt": [
            *plan.forbidden_elements,
            "robots",
            "glowing brain",
            "abstract neural network background",
            "fake dashboard",
            "unreadable paragraphs",
            "brand logos",
            "watermark",
            "charts",
            "workflow arrows",
        ],
        "reviewer_checklist": [
            f"Does the image communicate this takeaway: {viewer_takeaway}?",
            "Is there one focal subject?",
            "Is forbidden content absent?",
            "Is the text policy respected?",
            "Would this be more honest as a deterministic chart/diagram instead?",
        ],
    }


def build_cycle_prompt(
    source: RefinedVisualSource,
    directives: list[str],
    *,
    image_direction: dict[str, Any] | None = None,
) -> str:
    """Build provider prompt from refined source plus prior cycle lessons."""
    prompt = source.prompt_brief()
    if image_direction is not None:
        prompt = (
            f"{prompt}\n\nAI IMAGE DIRECTOR STRUCTURED BRIEF:\n"
            f"{json.dumps(image_direction, indent=2, ensure_ascii=False)}\n\n"
            "Use the `prompt` field as the provider-ready visual prompt. Obey "
            "negative_prompt, text_policy, output, and reviewer_checklist exactly."
        )
    if not directives:
        return prompt
    return f"{prompt}\n\nPrior visual-cycle lessons to apply now:\n" + "\n".join(
        f"- {directive}" for directive in directives
    )


def prompt_digest(prompt: str) -> str:
    """Return a compact hash proving providers received the same prompt."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _source_text(source: RefinedVisualSource) -> str:
    return " ".join(
        value
        for value in [
            source.refined_text,
            source.headline or "",
            source.topic or "",
            source.intended_takeaway or "",
        ]
        if value
    )


def _aspect_ratio(width: int, height: int) -> str:
    if width == height:
        return "1:1"
    if height > width:
        return "4:5" if abs((width / height) - 0.8) < 0.08 else "9:16"
    return "16:9"


def load_prior_reports(output_root: Path, *, limit: int) -> list[dict[str, Any]]:
    """Load recent cycle reports, newest first."""
    if limit <= 0 or not output_root.exists():
        return []
    reports: list[dict[str, Any]] = []
    for report_path in sorted(
        output_root.glob("*/cycle-report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(report, dict):
            reports.append(report)
        if len(reports) >= limit:
            break
    return reports


def improvement_directives_from_history(reports: list[dict[str, Any]]) -> list[str]:
    """Extract bounded prompt directives from prior cycle reports."""
    directives: list[str] = []
    seen: set[str] = set()
    for report in reports:
        plan = report.get("improvement_plan")
        candidates = plan.get("next_cycle_directives", []) if isinstance(plan, dict) else []
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            text = candidate.strip()
            if text and text not in seen:
                seen.add(text)
                directives.append(text)
            if len(directives) >= 5:
                return directives
    return directives


def next_improvements(visual_judge: object) -> list[str]:
    """Translate judge output into concrete next actions."""
    if not isinstance(visual_judge, dict):
        return [
            "Provider did not produce judge metadata; inspect provider failure before tuning prompts."
        ]
    verdict = str(visual_judge.get("verdict", ""))
    reasons = visual_judge.get("reasons")
    if verdict == "pass":
        return ["Keep this route/plan/provider combination in the candidate set for comparison."]
    if isinstance(reasons, list) and reasons:
        return [f"Tighten production plan for: {reason}" for reason in reasons[:3]]
    retry_instruction = visual_judge.get("retry_instruction")
    if retry_instruction:
        return [str(retry_instruction)]
    return ["Review image manually; judge returned no actionable reason."]


def score_result(status: str, visual_judge: object) -> int:
    """Score one provider/model result for simple cycle ranking."""
    if status != VisualDispatchStatus.SUCCEEDED.value:
        return 0
    if not isinstance(visual_judge, dict):
        return 40
    verdict = str(visual_judge.get("verdict", ""))
    if verdict == "pass":
        return 100
    if verdict == "retry":
        return 55
    if verdict == "fail":
        return 20
    return 40


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a compact cycle summary."""
    total = len(results)
    succeeded = sum(
        1 for result in results if result["status"] == VisualDispatchStatus.SUCCEEDED.value
    )
    failed = total - succeeded
    return {
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "ranked_provider_models": ranked_provider_models(results),
        "best_available": next(
            (
                {
                    "provider": result["provider"],
                    "model": result["model"],
                    "output_path": result["output_path"],
                }
                for result in results
                if result["status"] == VisualDispatchStatus.SUCCEEDED.value
            ),
            None,
        ),
    }


def ranked_provider_models(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank provider/model candidates for the next review step."""
    ranked = sorted(
        results,
        key=lambda result: (
            int(result.get("score", 0)),
            -int(result.get("duration_ms", 0) or 0),
        ),
        reverse=True,
    )
    return [
        {
            "provider": str(result.get("provider")),
            "model": str(result.get("model")),
            "score": int(result.get("score", 0)),
            "status": str(result.get("status")),
            "output_path": result.get("output_path"),
        }
        for result in ranked
    ]


def build_improvement_plan(
    results: list[dict[str, Any]],
    prior_directives: list[str],
) -> dict[str, Any]:
    """Build the deliberate improvement payload for the next cycle."""
    ranked = ranked_provider_models(results)
    failing_actions: list[str] = []
    for result in results:
        for improvement in result.get("next_improvements", []):
            if isinstance(improvement, str) and improvement not in failing_actions:
                failing_actions.append(improvement)
    next_cycle_directives = [
        action
        for action in failing_actions
        if not action.startswith("Keep this route/plan/provider")
    ][:5]
    if not next_cycle_directives and ranked:
        best = ranked[0]
        next_cycle_directives.append(
            "Preserve the current route and production plan; vary provider/model only for comparison."
        )
        next_cycle_directives.append(
            f"Use {best['provider']}:{best['model']} as the current quality reference."
        )
    return {
        "ranked_provider_models": ranked,
        "carried_forward_directives": prior_directives,
        "next_cycle_directives": next_cycle_directives,
        "manual_review_required": any(result.get("score", 0) < 100 for result in results),
    }


def append_history(path: Path, report: dict[str, Any]) -> None:
    """Append compact cycle history for future prompt directives."""
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "cycle_id": report["cycle_id"],
        "created_at": report["created_at"],
        "route_mode": report["visual_route"]["mode"],
        "template_kind": report["visual_strategy"]["template_kind"],
        "summary": report["summary"],
        "improvement_plan": report["improvement_plan"],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_improvement_markdown(path: Path, report: dict[str, Any]) -> None:
    """Write a human-readable improvement note beside cycle artifacts."""
    lines = [
        f"# {report['cycle_id']} Visual Improvements",
        "",
        "## Ranking",
    ]
    for item in report["improvement_plan"]["ranked_provider_models"]:
        lines.append(
            f"- {item['provider']}:{item['model']} score={item['score']} status={item['status']}"
        )
    lines.extend(["", "## Next Cycle Directives"])
    for directive in report["improvement_plan"]["next_cycle_directives"]:
        lines.append(f"- {directive}")
    lines.extend(["", "## Dispatch Log", str(report["log_path"])])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_example_plan_batch(args: argparse.Namespace) -> dict[str, Any]:
    """Write structured prompt packages without invoking providers."""
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    provider_models = ["codex_cli_image:default", "agy_cli_image:Gemini 3.5 Flash (Medium)"]
    items: list[dict[str, Any]] = []
    for thought_id, headline, topic, takeaway, text in EXAMPLE_THOUGHTS:
        cycle_id = f"structured-{thought_id}"
        source = RefinedVisualSource(
            piece_id=cycle_id,
            platform=args.platform,
            content_type="image_post",
            refined_text=text,
            headline=headline,
            topic=topic,
            intended_takeaway=takeaway,
        )
        route = choose_visual_concept_route(source)
        plan = build_visual_production_plan(source, route)
        strategy = choose_visual_generation_strategy(source, route)
        image_direction = build_ai_image_direction(
            source,
            route=route,
            plan=plan,
            platform=args.platform,
            width=args.width,
            height=args.height,
        )
        prompt = build_cycle_prompt(source, [], image_direction=image_direction)
        prompt_hash = prompt_digest(prompt)
        provider_prompts = []
        for provider_model in provider_models:
            provider, model = parse_provider_model(provider_model)
            provider_prompts.append(
                {
                    "provider": provider.value,
                    "model": model or "default",
                    "structured_prompt_hash": prompt_hash,
                    "status": "planned_not_dispatched",
                }
            )
        record = {
            "cycle_id": cycle_id,
            "source": source.model_dump(mode="json"),
            "visual_route": route.model_dump(mode="json"),
            "visual_plan": plan.model_dump(mode="json"),
            "visual_strategy": strategy.model_dump(mode="json"),
            "ai_image_direction": image_direction,
            "structured_prompt_hash": prompt_hash,
            "provider_prompts": provider_prompts,
            "prompt": prompt,
        }
        cycle_dir = output_root / cycle_id
        cycle_dir.mkdir(parents=True, exist_ok=True)
        (cycle_dir / "structured-prompt-package.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        items.append(record)
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "mode": "plan_only",
        "total_thoughts": len(items),
        "total_provider_versions": len(items) * len(provider_models),
        "provider_models": provider_models,
        "items": [
            {
                "cycle_id": item["cycle_id"],
                "structured_prompt_hash": item["structured_prompt_hash"],
                "route_mode": item["visual_route"]["mode"],
                "image_class": item["ai_image_direction"]["image_class"],
                "provider_prompts": item["provider_prompts"],
                "package_path": str(output_root / item["cycle_id"] / "structured-prompt-package.json"),
            }
            for item in items
        ],
    }
    (output_root / "structured-batch-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", default=None)
    parser.add_argument("--platform", default="linkedin")
    parser.add_argument("--headline", default="The workflow is the product")
    parser.add_argument("--topic", default="AI workflow routing")
    parser.add_argument(
        "--takeaway",
        default="Each model should own one job inside a reviewed workflow.",
    )
    parser.add_argument(
        "--source-text",
        default=(
            "A strong AI image workflow is not one perfect model. It is a routing "
            "loop where each model creates one candidate, a judge compares outputs, "
            "and the next cycle tightens the plan."
        ),
    )
    parser.add_argument("--raw-thought", default=None)
    parser.add_argument(
        "--provider-model",
        action="append",
        help="Provider/model pair such as agy_cli_image:Gemini 3.5 Flash (Medium). Repeatable.",
    )
    parser.add_argument("--output-dir", default="data/test-runs/visual-provider-cycles")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument(
        "--example-batch",
        action="store_true",
        help="Run the 10 built-in AI-image thoughts with Codex and AGY using the same structured prompt.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Write structured prompt packages without invoking providers.",
    )
    return parser


def main() -> None:
    """CLI entrypoint."""
    args = build_parser().parse_args()
    if args.plan_only:
        print(json.dumps(write_example_plan_batch(args), indent=2))
        return
    if args.example_batch:
        reports = []
        args.provider_model = [
            "codex_cli_image:default",
            "agy_cli_image:Gemini 3.5 Flash (Medium)",
        ]
        for thought_id, headline, topic, takeaway, text in EXAMPLE_THOUGHTS:
            cycle_args = argparse.Namespace(**vars(args))
            cycle_args.example_batch = False
            cycle_args.cycle_id = f"structured-{thought_id}"
            cycle_args.headline = headline
            cycle_args.topic = topic
            cycle_args.takeaway = takeaway
            cycle_args.source_text = text
            reports.append(asyncio.run(run_cycle(cycle_args)))
        summary = {
            "total_thoughts": len(reports),
            "total_provider_attempts": sum(len(report["results"]) for report in reports),
            "reports": [str(Path(report["log_path"]).parent / "cycle-report.json") for report in reports],
        }
        print(json.dumps(summary, indent=2))
        return
    report = asyncio.run(run_cycle(args))
    print(json.dumps(report["summary"], indent=2))
    print(report["log_path"])


if __name__ == "__main__":
    main()
