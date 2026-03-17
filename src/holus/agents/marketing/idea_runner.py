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
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Proxy config
# ---------------------------------------------------------------------------
PROXY_URL = "http://localhost:8080/v1/chat/completions"
PROXY_HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer local"}


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
    return resp.json()["choices"][0]["message"]["content"]


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


def plan_formats(raw_idea: str) -> list[dict]:
    user_msg = f"""
<idea>
{raw_idea}
</idea>

Plan 2-4 content formats for this idea. Return only the JSON array.
"""
    raw = _call("anthropic/claude-opus-4-6", PLANNER_SYSTEM, user_msg, temperature=0.2)
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
Anti-patterns: No "follow me for more", no "in today's world", no "Let's dive in!",
               no "In this post I will", no bullet walls.
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
LinkedIn carousel (PDF). 8-10 slides. Portrait 1080x1350px.
Return JSON with this exact structure — no prose, no markdown fences:
{
  "slides": [
    {"type": "hook", "variables": {"headline": "max 8 words — the scroll stopper", "subheadline": "optional, max 12 words"}},
    {"type": "body", "variables": {"title": "max 6 words", "body": "max 20 words", "bullet_points": ["→ point one", "→ point two"]}},
    {"type": "stat", "variables": {"stat_value": "73%", "stat_label": "label", "context": "one sentence", "trend": "up"}},
    {"type": "quote", "variables": {"quote_text": "the quote", "attribution": "Author Name"}},
    {"type": "comparison", "variables": {"left_title": "Before", "left_items": ["..."], "right_title": "After", "right_items": ["..."]}},
    {"type": "summary", "variables": {"title": "The takeaway", "items": ["one-sentence key insight"]}},
    {"type": "cta",  "variables": {"headline": "the closing question — lightweight, no 'follow me'"}}
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
Slide types (pick the right mix — not all types needed):
- hook (slide 1 only): headline ≤8 words. Optional subheadline ≤12 words. No bullets.
- body (slides 2+): title + body OR bullets — max 30 words total per slide. One idea only.
- stat: big number with label and context. Use for data-driven claims.
- quote: quote text + attribution. Use for authority/social proof.
- comparison: two columns with items. Use for before/after, old/new, X vs Y.
- split_left / split_right: text on one side, graphic_svg placeholder on the other.
- centered: single bold statement, no title bar.
- data: title + chart_svg placeholder + source_label.
- summary (second-to-last): title + items list (2-4 key takeaways).
- cta (last slide): headline = the CTA question. No buttons. No "follow me".

Design block — pick one of each:
- theme: dark | light | warm | cool | bold
- font_pairing: tech (dev content) | editorial (thought leadership) | modern (SaaS) | bold (punchy stats)
- gradient: dark_navy | indigo_mesh | warm_sunset | cool_ocean | bold_fire | frosted_glass | aurora | minimal_light
- effect: none | glass | neubrutalism | depth | glow | grain
Match design to content tone. Data-heavy → tech+dark_navy. Thought leadership → editorial+aurora. Punchy → bold+bold_fire+neubrutalism.
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
Instagram/Threads caption. 150-300 characters.
The core insight only — no setup needed. Must work without context.
Close with a simple question or statement.
Can be in English, Spanish, or bilingual (your call based on the idea).
</format_instructions>
""",
}


def generate_piece(raw_idea: str, decision: dict) -> dict:
    fmt = decision.get("format", "text_post")
    platform = decision.get("platform", "linkedin")
    angle = decision.get("angle", raw_idea)
    fmt_instructions = FORMAT_INSTRUCTIONS.get(fmt, FORMAT_INSTRUCTIONS["text_post"])

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
    raw = _call("anthropic/claude-sonnet-4-6", GENERATOR_SYSTEM, user_msg, temperature=0.4)
    cleaned = _strip_fences(raw)
    try:
        result = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        result = {"text": raw, "headline": raw_idea[:60], "hashtags": [], "hook_score": "?", "voice_check": "?"}
    return result


# ---------------------------------------------------------------------------
# Step 3: Save to content-queue
# ---------------------------------------------------------------------------


def save_piece(
    raw_idea: str,
    decision: dict,
    generated: dict,
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

    data: dict = {
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

    filename = f"{decision.get('platform', 'linkedin')}-{decision.get('format', 'post')}-{piece_id}.json"
    path = queue_dir / filename
    path.write_text(json.dumps(data, indent=2))
    return path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_from_idea(raw_idea: str) -> list[dict]:
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
        })

    print(f"\nDone. {len(results)} piece(s) in data/content-queue/")
    print("Review in Observatory → localhost:3000/content\n")
    return results
