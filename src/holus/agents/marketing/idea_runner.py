"""Idea-injection pipeline for Holus.

Given a raw idea from the user, uses Opus to plan formats and Sonnet to
generate each piece. Saves results to data/content-queue/ with agent traces
and staggered scheduled_at dates.

Usage:
    python -m holus idea "MCP vs SKILLS — two paradigms for extending AI agents"

No Redis or PostgreSQL required — runs via the local LLM proxy.

This module is a thin orchestrator that delegates to:
  - format_planner — Opus plans which formats to create
  - content_generator — Sonnet generates each piece
  - visual_pipeline — Sonnet designs + renders companion visuals
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-export everything for backward compatibility.
# Any code that does `from holus.agents.marketing.idea_runner import X`
# must continue to work.
# ---------------------------------------------------------------------------
from holus.agents.marketing.content_generator import (  # noqa: F401, E402
    FORMAT_INSTRUCTIONS,
    GENERATOR_SYSTEM,
    _get_format_instructions,
    generate_piece,
)
from holus.agents.marketing.format_planner import (  # noqa: F401, E402
    PLANNER_SYSTEM,
    plan_formats,
)
from holus.agents.marketing.idea_utils import (  # noqa: F401, E402
    PROXY_HEADERS,
    PROXY_URL,
    _call,
    _load_prompt,
    _strip_fences,
    _strip_markdown,
)
from holus.agents.marketing.visual_pipeline import (  # noqa: F401, E402
    VISUAL_DESIGNER_SYSTEM,
    _generate_visual_spec,
    _render_visual,
)
from holus.lineage.recorder import LineageRecorder

# ---------------------------------------------------------------------------
# Step 2.5: Judge evaluation
# ---------------------------------------------------------------------------


def _evaluate_piece(
    raw_idea: str, fmt: str, platform: str, generated: dict[str, Any]
) -> dict[str, Any] | None:
    """Evaluate a generated piece with JudgeAgent. Non-blocking on failure."""
    try:
        from holus.self_improvement.judge import JudgeAgent

        judge = JudgeAgent()

        # Build evaluable text from the generated output
        if fmt == "carousel_outline":
            # For carousels, evaluate the slide content + caption
            slides_text = json.dumps(generated.get("slides", []), indent=2)
            caption = generated.get("caption", "")
            output_text = f"Caption: {caption}\n\nSlides:\n{slides_text}"
            content_type = "CAROUSEL"
        elif fmt == "thread":
            output_text = generated.get("text", "")
            content_type = "THREAD"
        else:
            output_text = generated.get("text", "")
            content_type = "TEXT_POST"

        # Use platform-specific rubric if available
        platform_rubric = None
        try:
            from holus.agents.marketing.platform_config import get_judge_rubric

            platform_rubric = get_judge_rubric(platform)
        except Exception:
            pass

        if platform_rubric:
            evaluation = judge.evaluate(
                task=f"Generate {fmt} for {platform}: {raw_idea[:200]}",
                task_type=content_type.lower(),
                output=output_text[:4000],
                custom_rubric=platform_rubric,
            )
        else:
            evaluation = judge.evaluate_with_routing(
                task=f"Generate {fmt} for {platform}: {raw_idea[:200]}",
                content_type=content_type,
                output=output_text[:4000],
            )

        # Log to trajectory
        from holus.memory.trajectory import TrajectoryEntry, TrajectoryLogger

        tl = TrajectoryLogger(Path(".self-improvement/memory/trajectory.jsonl"))
        tl.append(
            TrajectoryEntry(
                agent_id="idea-runner",
                task_type=fmt,
                task_summary=f"{fmt} for {platform}: {raw_idea[:100]}",
                status="success",
                judge_verdict=evaluation.verdict.value,
                judge_score=evaluation.score,
                judge_feedback=evaluation.feedback,
                model_used="anthropic/claude-sonnet-4-6",
                metadata={
                    "schema_version": 2,
                    "platform": platform,
                    "content_type": content_type,
                    "format": fmt,
                    "idea": raw_idea[:200],
                    "dimension_scores": evaluation.dimension_scores,
                },
            )
        )

        return evaluation.to_dict()

    except Exception as exc:
        print(f"  ⚠ Judge evaluation failed (non-blocking): {exc}")
        return None


# ---------------------------------------------------------------------------
# Step 3: Save to content-queue
# ---------------------------------------------------------------------------


def save_piece(
    raw_idea: str,
    decision: dict[str, Any],
    generated: dict[str, Any],
    queue_dir: Path,
    *,
    group_id: str | None = None,
) -> Path:
    piece_id = uuid.uuid4().hex[:16]
    now = datetime.now(UTC)
    offset_days = decision.get("scheduled_offset_days", 0)
    scheduled_at = (now + timedelta(days=offset_days)).isoformat()

    fmt = decision.get("format", "text_post")

    # Carousel: text = caption, slides stored separately, PDF rendered
    if fmt == "carousel_outline":
        text = generated.get("caption", generated.get("text", ""))
        hashtags = generated.get("hashtags", [])
        full_text = text
    else:
        text = generated.get("text", "")
        hashtags = generated.get("hashtags", [])
        if hashtags and not any(h in text for h in hashtags):
            full_text = f"{text}\n\n{' '.join(hashtags)}"
        else:
            full_text = text

    data: dict[str, Any] = {
        "piece_id": piece_id,
        "group_id": group_id or piece_id,
        "platform": decision.get("platform", "linkedin"),
        "content_type": decision.get("format", "text_post"),
        "content_pillar": decision.get("pillar", "ai_engineering"),
        "topic": generated.get("headline", raw_idea[:80]),
        "text": full_text,
        "hashtags": hashtags,
        "char_count": len(full_text),
        "status": "pending_review",
        "generated_at": now.isoformat(),
        "scheduled_at": scheduled_at,
        "idea_source": raw_idea,
        "agent_trace": [
            {
                "agent_id": "idea-planner",
                "model": "anthropic/claude-opus-4-6",
                "role": "planned formats from raw idea",
                "at": now.isoformat(),
            },
            {
                "agent_id": "idea-generator",
                "model": "anthropic/claude-sonnet-4-6",
                "role": f"generated {decision.get('format', 'text_post')} for {decision.get('platform', 'linkedin')}",
                "at": now.isoformat(),
            },
        ],
        "quality": {
            "hook_score": generated.get("hook_score", "?"),
            "voice_check": generated.get("voice_check", "?"),
        },
    }

    # Write judge scores to queue file so auto-publish can read them
    if generated.get("judge_score") is not None:
        data["judge_score"] = generated["judge_score"]
        data["judge_verdict"] = generated.get("judge_verdict")
        data["judge_feedback"] = generated.get("judge_feedback", "")

    # For carousels: store slide definitions and render PDF
    if fmt == "carousel_outline" and generated.get("slides"):
        data["slides"] = generated["slides"]
        pdf_filename = f"{decision.get('platform', 'linkedin')}-carousel-{piece_id}.pdf"
        pdf_path = queue_dir / pdf_filename
        try:
            from holus.visual.carousel_builder import build_carousel_pdf

            build_carousel_pdf(generated, pdf_path)
            data["pdf_path"] = str(pdf_path)
            print(f"  → PDF rendered: {pdf_path.name}")
        except Exception as exc:
            print(f"  ⚠ PDF render failed (outline saved): {exc}")

    # For text posts: generate A/B visual variants, judge picks the winner
    if fmt in ("text_post", "thread", "instagram_caption"):
        platform = decision.get("platform", "linkedin")

        # Variant A
        spec_a = _generate_visual_spec(full_text, fmt, platform)
        if spec_a:
            png_a = queue_dir / f"{platform}-{fmt}-{piece_id}-a.png"
            if _render_visual(spec_a, png_a):
                data["rendered_image_path"] = str(png_a)
                data["visual_spec"] = spec_a
                print(f"  → Visual A rendered: {png_a.name}")

        # Variant B (higher temperature for creative variety)
        spec_b = _generate_visual_spec(full_text, fmt, platform, temperature=0.8)
        if spec_b and spec_b != spec_a:
            png_b = queue_dir / f"{platform}-{fmt}-{piece_id}-b.png"
            if _render_visual(spec_b, png_b):
                data["rendered_image_b_path"] = str(png_b)
                data["visual_spec_b"] = spec_b
                print(f"  → Visual B rendered: {png_b.name}")

        # Judge picks the better visual (auto-select, user can override in dashboard)
        if data.get("rendered_image_path") and data.get("rendered_image_b_path"):
            data["visual_chosen"] = "a"  # default; judge or user overrides

    # Store chosen visual type for recency tracking
    final_visual_spec = data.get("visual_spec")
    if final_visual_spec:
        data["visual_type"] = final_visual_spec.get("type", "unknown")

    filename = (
        f"{decision.get('platform', 'linkedin')}-{decision.get('format', 'post')}-{piece_id}.json"
    )
    path = queue_dir / filename
    path.write_text(json.dumps(data, indent=2))
    return path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_from_idea(raw_idea: str) -> list[dict[str, Any]]:
    """Process a raw idea into multiple content formats.

    Returns a list of results with piece_id, platform, format, and queue_path.
    """
    queue_dir = Path("data/content-queue")
    group_id = uuid.uuid4().hex
    queue_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nIdea: {raw_idea}\n")
    print("Step 1/2: Planning formats with Opus...")
    decisions = plan_formats(raw_idea)
    print(f"  → {len(decisions)} format(s) planned")
    for d in decisions:
        print(f"    • {d['format']} for {d['platform']} (Day {d.get('scheduled_offset_days', 0)})")

    results = []
    for _i, decision in enumerate(decisions, 1):
        fmt = decision.get("format", "text_post")
        platform = decision.get("platform", "linkedin")
        print(f"\nStep 2/{len(decisions) + 1}: Generating {fmt} for {platform}...")
        generated = generate_piece(raw_idea, decision)

        # Step 2.5: Judge evaluates the generated content
        judge_result = _evaluate_piece(raw_idea, fmt, platform, generated)
        if judge_result:
            generated["judge_verdict"] = judge_result["verdict"]
            generated["judge_score"] = judge_result["score"]
            generated["judge_feedback"] = judge_result["feedback"]
            generated["judge_dimensions"] = judge_result.get("dimension_scores", {})
            print(f"  → Judge: {judge_result['verdict']} ({judge_result['score']:.2f})")

        path = save_piece(raw_idea, decision, generated, queue_dir, group_id=group_id)
        hook = generated.get("hook_score", "?")
        voice = generated.get("voice_check", "?")
        char = len(generated.get("text", ""))

        print(f"  → Hook: {hook}/10  Voice: {voice}  Chars: {char}")
        print(f"  → Saved: {path}")

        results.append(
            {
                "piece_id": path.stem,
                "platform": platform,
                "format": fmt,
                "queue_path": str(path),
                "hook_score": hook,
                "voice_check": voice,
                "judge_verdict": judge_result["verdict"] if judge_result else None,
                "judge_score": judge_result["score"] if judge_result else None,
            }
        )

    records: list[dict[str, Any]] = []
    for result in results:
        try:
            record = json.loads(Path(result["queue_path"]).read_text(encoding="utf-8"))
            if isinstance(record, dict):
                record["queue_path"] = str(
                    Path(result["queue_path"]).relative_to(queue_dir.parent)
                )
                records.append(record)
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not load generated record for lineage: %s", result["queue_path"])
    if records:
        try:
            LineageRecorder(queue_dir.parent / "lineage").record_generated_set(
                raw_idea,
                records,
                group_id=group_id,
                package={"channel_plan": [{"piece_id": r["piece_id"]} for r in records]},
            )
        except Exception:
            logger.exception("lineage_emission_failed", extra={"group_id": group_id})

    print(f"\nDone. {len(results)} piece(s) in data/content-queue/")
    print("Review in Observatory → localhost:3000/content\n")
    return results


def run_from_bandit(raw_idea: str, *, platform: str | None = None) -> list[dict[str, Any]]:
    """Like run_from_idea but uses Thompson Sampling to guide strategy.

    The bandit suggests which (product, content_type, platform) to create.
    Opus still writes the content — TS just biases the format decisions.
    After publishing + analytics collection, call bandit.update() with reward.
    """
    try:
        from holus.agents.marketing.strategy_bandit import StrategyBandit

        bandit = StrategyBandit()
        suggestion = bandit.suggest(platform=platform)

        if suggestion:
            print(
                f"\n🎰 Bandit suggests: {suggestion.arm.arm_id} "
                f"(θ={suggestion.sampled_theta:.2f}, "
                f"{'exploration' if suggestion.is_exploration else 'exploitation'})"
            )

            # Inject bandit suggestion into the idea as a hint
            bandit_hint = (
                f"\nBANDIT SUGGESTION: Create a {suggestion.arm.content_type} "
                f"for {suggestion.arm.platform} featuring {suggestion.arm.product}. "
                f"This combination has {'high' if not suggestion.is_exploration else 'unknown'} "
                f"historical performance."
            )
            enhanced_idea = raw_idea + bandit_hint
        else:
            enhanced_idea = raw_idea
            print("\n🎰 Bandit: no suggestion (no arms registered)")

    except Exception as exc:
        print(f"\n⚠ Bandit unavailable: {exc}")
        enhanced_idea = raw_idea

    return run_from_idea(enhanced_idea)
