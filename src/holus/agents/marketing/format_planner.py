"""Format planning stage of the idea-injection pipeline.

Uses Opus to analyze a raw idea and decide which content formats
(text_post, thread, carousel, etc.) to create for which platforms.
"""

from __future__ import annotations

import json
from typing import Any

from holus.agents.marketing.idea_utils import _call, _load_prompt, _strip_fences

# ---------------------------------------------------------------------------
# Planner system prompt (Layer 3 fallback)
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
