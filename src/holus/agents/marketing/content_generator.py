"""Content generation stage of the idea-injection pipeline.

Uses Sonnet to generate content pieces (text posts, threads, carousels,
video scripts, Instagram captions) based on format decisions from the planner.
Includes an optional Constitutional AI revision loop for text content.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from holus.agents.marketing.idea_utils import (
    _call,
    _load_prompt,
    _strip_fences,
    _strip_markdown,
    _strip_word_counts,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Generator system prompt (Layer 3 fallback)
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


def _load_few_shot_context(content_type: str) -> str:
    """Load pre-materialized few-shot examples for this content type."""
    try:
        from holus.data.few_shot import FewShotMaterializer

        materializer = FewShotMaterializer()
        examples = materializer.load_examples(content_type, limit=3)
        if not examples:
            return ""
        parts = ["## Top-Performing Examples (study these — they worked on LinkedIn)\n"]
        for i, ex in enumerate(examples, 1):
            creator = ex.get("creator", "unknown")
            engagement = ex.get("engagement_total", 0)
            text = ex.get("text", "")[:500]
            why = ex.get("why_it_works", "")
            parts.append(f"### Example {i} ({engagement:,} engagement — @{creator})")
            parts.append(text)
            if why:
                parts.append(f"Why it works: {why}")
            parts.append("")
        parts.append("Now write YOUR post. Match their quality. Be specific like them.\n")
        return "\n".join(parts)
    except Exception:
        logger.debug("Few-shot examples not available", exc_info=True)
        return ""


def _load_personal_context(product: str = "") -> str:
    """Load personal context entries for prompt injection."""
    try:
        from holus.agents.marketing.humanize import format_personal_context, select_personal_context

        entries = select_personal_context(product=product, count=3)
        if entries:
            return format_personal_context(entries)
        return ""
    except Exception:
        logger.debug("Personal context not available", exc_info=True)
        return ""


def generate_piece(raw_idea: str, decision: dict[str, Any]) -> dict[str, Any]:
    fmt = decision.get("format", "text_post")
    platform = decision.get("platform", "linkedin")
    angle = decision.get("angle", raw_idea)
    product = decision.get("product", "")
    fmt_instructions = _get_format_instructions(fmt, platform)

    # Load generator prompt via PromptLoader (falls back to GENERATOR_SYSTEM constant)
    generator_prompt, _variant = _load_prompt("idea-generator", GENERATOR_SYSTEM)

    # Load few-shot examples and personal context (graceful degradation)
    few_shot = _load_few_shot_context(fmt)
    personal_ctx = _load_personal_context(product)

    user_msg = f"""
{few_shot}
{personal_ctx}
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
