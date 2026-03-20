"""Idea-injection pipeline for Holus.

Given a raw idea from the user, uses Opus to plan formats and Sonnet to
generate each piece. Saves results to data/content-queue/ with agent traces
and staggered scheduled_at dates.

Usage:
    python -m holus idea "MCP vs SKILLS — two paradigms for extending AI agents"

No Redis or PostgreSQL required — runs via the local LLM proxy.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from holus.core.llm_proxy import get_proxy_headers, get_proxy_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Proxy config
# ---------------------------------------------------------------------------
PROXY_URL = get_proxy_url()
PROXY_HEADERS = get_proxy_headers()


def _call(model: str, system: str, user: str, temperature: float = 0.3) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 4096,
        "temperature": temperature,
    }
    resp = requests.post(PROXY_URL, json=payload, headers=PROXY_HEADERS, timeout=120)
    resp.raise_for_status()
    result: str = resp.json()["choices"][0]["message"]["content"]
    return result


def _strip_fences(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        s = "\n".join(lines[1:end])
    return s


# ---------------------------------------------------------------------------
# Step 1: Opus plans the formats
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """
<role>
You are a content strategist for Juan, a bilingual AI engineer.
Juan's LinkedIn goal: thought leader in AI engineering — NOT app promoter.
Apps (Pilaster, genpeli, invoz) are proof points only.
</role>

<task>
Given a raw idea, decide which content formats to create and for which platforms.
Return 2-4 format decisions — each is a different way to express the same idea.
Choose only formats where the idea naturally fits the platform culture.
</task>

<platform_rules>
linkedin: AI Engineering, Building in Public, Systems Thinking — thought leader content
twitter_x: Quick takes, threads — only if idea is tight and punchy enough
instagram: Bilingual/human side, behind-the-scenes — only if idea has personal/visual angle
threads: Conversational, first-person — only if idea has casual angle
</platform_rules>

<format_options>
text_post: Written post (LinkedIn primary, Twitter secondary)
thread: Multi-tweet thread (Twitter only)
carousel_outline: Slide-by-slide plan for a carousel (LinkedIn)
video_script: Script for Juan to record (any platform — Juan records, not AI-generated)
instagram_caption: Short caption with visual description (Instagram/Threads)
</format_options>

<output_format>
Return a JSON array. Each item:
{
  "format": "text_post|thread|carousel_outline|video_script|instagram_caption",
  "platform": "linkedin|twitter_x|instagram|threads",
  "pillar": "ai_engineering|building_in_public|bilingual_ai|systems_thinking",
  "scheduled_offset_days": 0,
  "angle": "one sentence: what angle this format takes on the idea",
  "skip_reason": null  // or "why this format was skipped"
}
scheduled_offset_days: 0 for first piece (LinkedIn text), then 3, 7, 14 for subsequent ones.
Only include decisions where the idea genuinely fits — omit platforms where it doesn't.
</output_format>
"""


def _load_prompt(agent_id: str, fallback: str) -> tuple[str, str]:
    """Load prompt via 3-layer PromptLoader. Returns (prompt, variant_id)."""
    try:
        from holus.core.prompt_loader import PromptLoader

        loader = PromptLoader()
        prompt = loader.get_prompt(agent_id, fallback=fallback)
        # Determine which layer resolved
        if (Path("config/prompts") / agent_id / "current.md").exists():
            return prompt, f"layer1:{agent_id}"
        return prompt, "layer2:canonical" if prompt != fallback else "layer3:fallback"
    except Exception:
        return fallback, "layer3:fallback"


def plan_formats(raw_idea: str) -> list[dict[str, Any]]:
    # Inject recently published topics to prevent repetition
    from holus.agents.marketing.topic_index import TopicIndex
    topic_context = TopicIndex().as_prompt_context(days=30)

    # Load planner prompt via PromptLoader (falls back to PLANNER_SYSTEM constant)
    planner_prompt, _variant = _load_prompt("idea-planner", PLANNER_SYSTEM)

    user_msg = f"""
{topic_context}

<idea>
{raw_idea}
</idea>

Plan 2-4 content formats for this idea. Return only the JSON array.
"""
    raw = _call("anthropic/claude-opus-4-6", planner_prompt, user_msg, temperature=0.2)
    cleaned = _strip_fences(raw)
    try:
        decisions = json.loads(cleaned)
        return [d for d in decisions if not d.get("skip_reason")]
    except (json.JSONDecodeError, TypeError, AttributeError):
        # Fallback: just LinkedIn text post
        return [
            {
                "format": "text_post",
                "platform": "linkedin",
                "pillar": "ai_engineering",
                "scheduled_offset_days": 0,
                "angle": raw_idea,
            }
        ]


# ---------------------------------------------------------------------------
# Step 2: Sonnet generates each piece
# ---------------------------------------------------------------------------

GENERATOR_SYSTEM = """
<role>
You are Juan's content writer. Juan is a bilingual AI engineer targeting the
600M Spanish/English market Silicon Valley keeps ignoring. Builder-practitioner.
Ships real systems. Posts about what he's actually built and learned.
LinkedIn goal: thought leader in AI engineering — not app promoter.
</role>

<voice_rules>
Person: First person singular. "I built", "I learned". Never "we".
Contractions: Always. "it's", "don't", "you're".
Tone: Opinionated. Takes a clear position. Doesn't hedge.
Sentences: Short. One idea per sentence. Line breaks for emphasis.
Opening: NEVER start with "I" as the first word (LinkedIn algorithm).
Emojis: None on LinkedIn. Clean text only.
Exclamation marks: ZERO. Not one. None. Confidence doesn't shout.
Formatting: NEVER use markdown (**bold**, *italic*, __underline__, #heading).
            LinkedIn/Twitter/Instagram do NOT render markdown — asterisks show as literal text.
            Use ALL CAPS sparingly for emphasis. Use line breaks for structure. That's it.
Anti-patterns: No "follow me for more", no "in today's world", no "Let's dive in!",
               no "In this post I will", no bullet walls, no markdown formatting.
</voice_rules>

<content_fidelity>
Your source is the idea provided. Elaborate — do not invent.
You may add up to 2 supporting claims ONLY if both conditions are true:
  (a) The claim is the direct logical consequence of something already stated in the idea.
  (b) The claim is an unambiguous technical fact — not a market observation, trend statement,
      or historical framing (e.g. "X was born because of Y", "now that Z exists, the game has changed").
If a claim requires the reader to agree with a separate premise not in the idea, cut it.
The post must defend one thesis. Do not introduce a second thesis, even a related one.
</content_fidelity>

<contrastive_examples>
WRONG hook: "I want to share some thoughts on MCP vs Skills today."
RIGHT hook: "Most agent architectures are just API wrappers disguised as intelligence."

WRONG close: "Follow me for more AI engineering content!"
RIGHT close: "How are you drawing the line between tools and cognitive logic in your stack?"

WRONG: "There are many factors to consider when choosing between these approaches."
RIGHT: "You need both. Access without intent is a well-equipped agent that can't think."
</contrastive_examples>

<output_format>
Return JSON:
{
  "text": "the full post text",
  "headline": "short internal reference label",
  "hashtags": ["#Tag1", "#Tag2"],
  "hook_score": "1-10 — how strong is the opening?",
  "voice_check": "PASS or FAIL"
}
</output_format>
"""

FORMAT_INSTRUCTIONS = {
    "text_post": """
<format_instructions>
LinkedIn text post. 900-1200 characters.
Structure: Hook → Setup → Insight → Failure mode → Takeaway → CTA (question only)
No bullet walls. Short paragraphs. Line breaks for emphasis.
</format_instructions>
""",
    "thread": """
<format_instructions>
Twitter/X thread. 5-8 tweets. Each tweet max 280 chars.
Tweet 1: The hook (standalone, makes people click "see more")
Tweets 2-6: One idea per tweet. Build the argument.
Tweet 7: The takeaway (could stand alone)
Tweet 8 (optional): CTA — lightweight question
Separate tweets with "---" on its own line.
</format_instructions>
""",
    "carousel_outline": """
<format_instructions>
LinkedIn carousel (PDF). 7-8 slides. Portrait 1080x1350px.

CRITICAL DENSITY RULES (research-backed — single-sentence slides drop engagement 30%):
- Every slide MUST have 25-50 words of substantive content.
- No slide should have fewer than 20 words (except hook headline).
- Body slides need a heading + 3-4 bullet points OR heading + 2-3 sentences.
- MINIMUM 3 bullet points per body slide. Two bullets looks empty.
- Never repeat the same point across multiple slides. Each slide adds NEW information.
- If a slide can be removed without losing information, remove it.
- Do NOT use more than 2 body slides in a row. Alternate with stat, comparison, or other types.
- Bullet text must NOT start with "→" — the template adds arrows automatically.

Return JSON with this exact structure — no prose, no markdown fences:
{
  "slides": [
    {"type": "hook", "variables": {"headline": "max 8 words — the scroll stopper", "subheadline": "1-2 sentences that set up the story (15-25 words)"}},
    {"type": "body", "variables": {"title": "max 6 words", "body": "2-3 sentences (25-40 words)", "bullet_points": ["Substantive point with detail", "Another point with specifics", "Third point — minimum 3 bullets always"]}},
    {"type": "stat", "variables": {"stat_value": "73%", "stat_label": "label", "context": "2-3 sentences explaining what this number means and why it matters (25-40 words)", "trend": "up (green=good) or down (red=bad) — trend means sentiment, not direction. '0 errors' = up/green because 0 is good."}},
    {"type": "comparison", "variables": {"left_title": "Before", "left_items": ["descriptive point (5-10 words each)", "..."], "right_title": "After", "right_items": ["descriptive point (5-10 words each)", "..."]}},
    {"type": "body", "variables": {"title": "The takeaway", "body": "2-3 sentences with actionable insight (25-40 words)", "bullet_points": ["Specific action or lesson", "Second takeaway point", "Third actionable insight"]}},
    {"type": "cta",  "variables": {"headline": "the closing question — specific, not generic (10-20 words)"}}
  ],
  "design": {
    "theme": "dark",
    "font_pairing": "tech",
    "gradient": "dark_navy",
    "effect": "none"
  },
  "caption": "150-char companion post caption. Teases the carousel. Ends with Swipe →",
  "hook_score": "1-10",
  "voice_check": "PASS or FAIL"
}
Slide types (pick the right mix — use 5-6 types max, not all):
- hook (slide 1 only): headline ≤8 words. Subheadline 15-25 words that set up the story.
- body: title + body (25-40 words) + optional bullets. Each bullet is a real point, not a label.
- stat: big number + 2-3 sentence context explaining significance. Never a number alone.
- comparison: two columns, 4-5 items each. Each item is a descriptive phrase (5-10 words), not a single word.
- cta (last slide): specific question (10-20 words). No "follow me". No generic "what do you think?"

DO NOT USE these filler slide types:
- "centered" with a single quote — this is a wasted slide
- "summary" that just repeats earlier slides
- "quote" unless it's from a named authority with real attribution

Design block — pick one of each:
- theme: dark | light | warm | cool | bold
- font_pairing: tech (dev content) | editorial (thought leadership) | modern (SaaS) | bold (punchy stats)
- gradient: dark_navy | indigo_mesh | warm_sunset | cool_ocean | bold_fire | frosted_glass | aurora | minimal_light
- effect: none | glass | neubrutalism | depth | glow | grain
</format_instructions>
""",
    "video_script": """
<format_instructions>
Video script for Juan to record. 60-90 seconds spoken.
Sections: HOOK (0-5s), SETUP (5-20s), BODY (20-75s), CTA (last 10s)
Write as spoken word — conversational, natural, how Juan actually talks.
Include [on-screen text] cues in brackets for key phrases.
Juan records this himself. Holus does NOT generate the video.
</format_instructions>
""",
    "instagram_caption": """
<format_instructions>
Instagram caption. 800-1500 characters (front-load value, use line breaks for readability).
Include a concrete insight, stat, or takeaway worth bookmarking (save-worthy content).
Structure: hook line → core insight with specifics → personal angle or lesson → closing question or CTA.
End with a separate hashtag block of 5-15 relevant hashtags (mix of broad and niche).
Can be in English, Spanish, or bilingual (your call based on the idea).
</format_instructions>
""",
}


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting that social platforms render as literal characters."""
    import re
    # **bold** or __bold__ → just the text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # *italic* → just the text (but not bullet points like "* item")
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    # # headings → just the text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    return text


def _get_format_instructions(fmt: str, platform: str) -> str:
    """Get format instructions, with platform-specific enrichment.

    Instagram/TikTok video_scripts need hashtag and caption blocks that
    the base format instructions don't include. This patches the gap so
    the generated output satisfies the platform-fit-judge rubric.
    """
    base = FORMAT_INSTRUCTIONS.get(fmt, FORMAT_INSTRUCTIONS["text_post"])

    if fmt == "video_script" and platform in ("instagram", "tiktok", "facebook"):
        from holus.agents.marketing.platform_config import get_platform_config
        config = get_platform_config(platform)
        base += f"""
<platform_enrichment>
This video script targets {config.display_name}.
After the CTA section, add:

CAPTION: A short, engaging caption (100-200 chars) summarizing the video's value.

HASHTAGS: {config.hashtag_limit} relevant hashtags in a single line, mixing broad
and niche tags. Example: #AI #BuildInPublic #AgentArchitecture #TechFounder
</platform_enrichment>
"""
    return base


def generate_piece(raw_idea: str, decision: dict[str, Any]) -> dict[str, Any]:
    fmt = decision.get("format", "text_post")
    platform = decision.get("platform", "linkedin")
    angle = decision.get("angle", raw_idea)
    fmt_instructions = _get_format_instructions(fmt, platform)

    # Load generator prompt via PromptLoader (falls back to GENERATOR_SYSTEM constant)
    generator_prompt, _variant = _load_prompt("idea-generator", GENERATOR_SYSTEM)

    user_msg = f"""
<idea>
{raw_idea}
</idea>

<angle>
{angle}
</angle>

<platform>{platform}</platform>

{fmt_instructions}

Write the {fmt} for this idea. Return JSON only.
"""
    raw = _call("anthropic/claude-sonnet-4-6", generator_prompt, user_msg, temperature=0.4)
    cleaned = _strip_fences(raw)
    try:
        result = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        result = {"text": raw, "headline": raw_idea[:60], "hashtags": [], "hook_score": "?", "voice_check": "?"}

    # Strip word count annotations the LLM sometimes includes (e.g., "(24 words)")
    import re
    def _strip_word_counts(obj: Any) -> Any:
        if isinstance(obj, str):
            return re.sub(r'\s*\(\d+\s*words?\)', '', obj).strip()
        if isinstance(obj, list):
            return [_strip_word_counts(item) for item in obj]
        if isinstance(obj, dict):
            return {k: _strip_word_counts(v) for k, v in obj.items()}
        return obj
    result = _strip_word_counts(result)
    assert isinstance(result, dict)

    # Optional: Constitutional AI revision for text content
    if fmt in ("text_post", "thread", "instagram_caption") and result.get("text"):
        try:
            from holus.agents.marketing.revision_loop import RevisionLoop

            loop = RevisionLoop(max_rounds=1)
            # revision_loop functions are async but we're in sync context
            # Call the underlying sync _call directly for critique + revise
            critique_text = loop._call_sync(result["text"], fmt, platform)
            if critique_text and "PASS" not in critique_text[:50]:
                revised = loop._revise_sync(result["text"], critique_text)
                if revised and revised != result["text"]:
                    result["text"] = revised
                    result["revised"] = True
                    print("  → Revised: 1 round of critique")
        except Exception as exc:
            # Non-blocking — if revision fails, use original
            logger.debug("Revision loop skipped: %s", exc)

    # Strip markdown formatting — social platforms render it as literal asterisks
    if result.get("text"):
        result["text"] = _strip_markdown(result["text"])

    return result


# ---------------------------------------------------------------------------
# Step 2.3: Generate companion visual for the post
# ---------------------------------------------------------------------------

VISUAL_DESIGNER_SYSTEM = """You design data visualizations for social media posts.
Given a post's text, extract the key concepts and design a visual that explains
the core idea at a glance. Return JSON only.

You have two visual types available:

1. "insight" — a branded card with a headline, optional stat, optional body text.
   Good for: key takeaways, bold statements, single metrics.
   JSON: {"type": "insight", "headline": "max 8 words", "body": "optional 1-2 sentences",
          "stat_value": "optional e.g. 3x or 73%", "stat_label": "optional label for stat"}

2. "data_viz" — a chart with data points.
   Good for: comparisons, before/after metrics, ranked lists.
   JSON: {"type": "data_viz", "chart_type": "bar|line|metric",
          "title": "chart title max 6 words",
          "data_points": [{"label": "X", "value": 85}, ...],
          "highlight_index": 0, "source_label": "optional attribution"}

Pick the type that best represents the post's core argument visually.
The visual should be understandable WITHOUT reading the post — it's a scroll-stopper.
STRONGLY prefer data_viz — charts grab attention on LinkedIn. Invent plausible
percentages or rankings if the post doesn't have exact numbers. A bar chart showing
"73% of agent failures are from X" is more engaging than a quote card.
Only use insight for posts that are purely philosophical with no comparisons at all.
Keep labels SHORT (max 3 words per label) so they don't overlap in the chart.

Return ONLY the JSON object. No markdown fences, no explanation."""


def _generate_visual_spec(
    post_text: str, fmt: str, platform: str, *, temperature: float = 0.3,
) -> dict[str, Any] | None:
    """Have Sonnet design a visual spec for the post. Returns spec dict or None."""
    if fmt not in ("text_post", "thread", "instagram_caption"):
        return None  # Carousels and video scripts don't need companion images

    try:
        user_msg = f"""Design a visual for this {platform} {fmt}:

{post_text[:2000]}

Return JSON only."""
        raw = _call("anthropic/claude-sonnet-4-6", VISUAL_DESIGNER_SYSTEM, user_msg, temperature=temperature)
        cleaned = _strip_fences(raw)
        spec: dict[str, Any] = json.loads(cleaned)
        return spec
    except Exception as exc:
        logger.debug("Visual spec generation failed: %s", exc)
        return None


def _render_visual(visual_spec: dict[str, Any], output_path: Path) -> bool:
    """Render a visual spec to PNG using PlaywrightEngine. Returns True on success."""
    import asyncio

    async def _do_render() -> bytes:
        from holus.visual import render_visual
        from holus.visual.spec_converter import data_viz_to_spec, insight_to_spec

        spec_type = visual_spec.get("type", "insight")

        if spec_type == "data_viz":
            render_spec = data_viz_to_spec(visual_spec)
        else:
            # insight type
            render_spec = insight_to_spec(
                text=visual_spec.get("body", visual_spec.get("headline", "")),
                stat=visual_spec.get("stat_value"),
            )
            # Override template variables with richer data
            if visual_spec.get("headline"):
                render_spec.variables["headline"] = visual_spec["headline"]
            if visual_spec.get("stat_label"):
                render_spec.variables["stat_label"] = visual_spec["stat_label"]
            render_spec.variables["author_name"] = "Juan Camilo Martinez"
            render_spec.variables["brand_handle"] = "@juancamilomartinez"

        return await render_visual(render_spec)

    try:
        # Handle both sync and async contexts
        try:
            asyncio.get_running_loop()
            # We're in an async context — use nest_asyncio or thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                png_bytes = pool.submit(asyncio.run, _do_render()).result(timeout=30)
        except RuntimeError:
            # No running loop — safe to use asyncio.run
            png_bytes = asyncio.run(_do_render())

        output_path.write_bytes(png_bytes)
        return True
    except Exception as exc:
        logger.debug("Visual render failed: %s", exc)
        print(f"  ⚠ Visual render failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Step 2.5: Judge evaluation
# ---------------------------------------------------------------------------


def _evaluate_piece(raw_idea: str, fmt: str, platform: str, generated: dict[str, Any]) -> dict[str, Any] | None:
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
        tl.append(TrajectoryEntry(
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
        ))

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

    filename = f"{decision.get('platform', 'linkedin')}-{decision.get('format', 'post')}-{piece_id}.json"
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
        print(f"\nStep 2/{len(decisions)+1}: Generating {fmt} for {platform}...")
        generated = generate_piece(raw_idea, decision)

        # Step 2.5: Judge evaluates the generated content
        judge_result = _evaluate_piece(raw_idea, fmt, platform, generated)
        if judge_result:
            generated["judge_verdict"] = judge_result["verdict"]
            generated["judge_score"] = judge_result["score"]
            generated["judge_feedback"] = judge_result["feedback"]
            generated["judge_dimensions"] = judge_result.get("dimension_scores", {})
            print(f"  → Judge: {judge_result['verdict']} ({judge_result['score']:.2f})")

        path = save_piece(raw_idea, decision, generated, queue_dir)
        hook = generated.get("hook_score", "?")
        voice = generated.get("voice_check", "?")
        char = len(generated.get("text", ""))

        print(f"  → Hook: {hook}/10  Voice: {voice}  Chars: {char}")
        print(f"  → Saved: {path}")

        results.append({
            "piece_id": path.stem,
            "platform": platform,
            "format": fmt,
            "queue_path": str(path),
            "hook_score": hook,
            "voice_check": voice,
            "judge_verdict": judge_result["verdict"] if judge_result else None,
            "judge_score": judge_result["score"] if judge_result else None,
        })

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
            print(f"\n🎰 Bandit suggests: {suggestion.arm.arm_id} "
                  f"(θ={suggestion.sampled_theta:.2f}, "
                  f"{'exploration' if suggestion.is_exploration else 'exploitation'})")

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
