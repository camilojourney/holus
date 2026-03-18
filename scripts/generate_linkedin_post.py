"""Generate a LinkedIn post via the Holus content pipeline.

Usage:
    uv run python scripts/generate_linkedin_post.py
    uv run python scripts/generate_linkedin_post.py --idea "MCP vs SKILLS"

Routes through the local LLM proxy at localhost:8080.
Saves output to data/content-queue/ for Observatory review.
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Proxy config
# ---------------------------------------------------------------------------
PROXY_URL = "http://localhost:8080/v1/chat/completions"
PROXY_MODEL = "anthropic/claude-sonnet-4-6"
PROXY_HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer local"}

# ---------------------------------------------------------------------------
# System prompt — XML-structured, Juan's voice baked in
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
<role>
You are Juan's content writer for LinkedIn. Juan is a bilingual AI engineer who builds
products for the 600M Spanish/English market Silicon Valley keeps ignoring.
His LinkedIn goal is to become a thought leader in AI engineering — not to promote his apps.
Apps (Pilaster, genpeli, invoz) are proof points, not the pitch.
</role>

<voice_rules>
Identity: Builder-practitioner. Someone who has shipped agents, not just read about them.
Person: First person singular. "I built", "Here's what I learned", never "we" or "the team".
Contractions: Always. "it's", "don't", "you're", "I've". Never formal.
Tone: Opinionated. Takes a clear position. Doesn't hedge with "it depends" or "it varies".
Sentences: Short. One idea per sentence. One sentence per line where possible.
Jargon: Only when the audience already knows it. LinkedIn audience = senior engineers.

DO NOT open with "I" as the first word. LinkedIn algorithm penalizes it.
DO NOT use emojis. Clean text only.
DO NOT pad. Say it in 900 characters. Not 1300 if 900 is enough.
DO NOT use "In this post I will..." openers.
DO NOT write bullet walls. Use prose with line breaks.
DO NOT add "Follow me for more" or "Like and share" CTAs.
DO NOT use exclamation marks more than once per post.
</voice_rules>

<linkedin_structure>
1. Hook (1 sentence ONLY): The opening line must be the sharpest sentence in the post.
   Options that work: a counterintuitive claim, a specific observation, a bold statement.
   Test: would a senior engineer pause scrolling for this? If not, rewrite it.
   The hook should NOT be a question. It should be a statement that makes people think.
   Example of weak hook: "Most teams treat MCP and Skills as interchangeable."
   Example of strong hook: "MCP gives your agent hands. Skills give it a brain. Most teams only ship the hands."

2. Setup (2-3 sentences): The concrete problem. What's broken in how people think about this?
   No throat-clearing. Get into the substance immediately.

3. The insight (3-5 sentences): The actual distinction. Make it specific.
   One real example or analogy that makes the abstract tangible.
   Write it so someone could explain this to a colleague after reading once.

4. The failure mode (2-3 sentences): What actually breaks when you get this wrong.
   Concrete. Not "it won't scale" — give the real symptom engineers will recognize.

5. Takeaway (1 sentence): The sentence that could stand alone as a tweet.
   Should work as a memorable framing device people will quote.

6. CTA (1 sentence): Opens a conversation. Not a call to action.
   Examples: "What are you seeing?" / "How are you handling this in your stack?"
</linkedin_structure>

<output_format>
Return a JSON object with exactly these fields:
{
  "text": "the full LinkedIn post text",
  "headline": "a short headline for internal reference (not posted)",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3"],
  "hook_score": "1-10: how strong is the opening? Be honest.",
  "voice_check": "PASS or FAIL — does this sound like a builder, not a content strategist?"
}
Do not include any text outside the JSON object.
</output_format>
"""


# ---------------------------------------------------------------------------
# Default brief — MCP vs SKILLS
# ---------------------------------------------------------------------------
DEFAULT_BRIEF = {
    "topic": "MCP vs SKILLS — Two Paradigms for Extending AI Agents",
    "angle": (
        "MCP and Skills are not the same thing and engineers keep confusing them. "
        "MCP = access (what your agent can reach — tools, data, APIs). "
        "Skills = capability (how your agent accomplishes complex tasks using that access). "
        "A Slack MCP tool gives you a door. "
        "A 'triage my inbox every morning' skill is the cognitive blueprint that decides "
        "when to open it, what to look for, and what to do next. "
        "The failure mode: teams build 40 MCP integrations with no skills framework, "
        "then wonder why the agent keeps asking 'what would you like me to do?' "
        "You need both — access AND cognitive blueprints. "
        "MCP without Skills = a well-equipped agent that can't think. "
        "Skills without MCP = an agent that thinks but can't act."
    ),
    "target_audience": "AI engineers, tech leads, CTOs evaluating agent architectures",
    "length_target": "900-1100 characters — punchy, not padded",
    "hashtags_hint": ["#AIEngineering", "#AgentArchitecture", "#MCP"],
}


def build_user_message(idea: str | None, brief: dict) -> str:
    if idea:
        return f"""
<idea>
{idea}
</idea>

<instructions>
Use the idea above as the raw material. Apply the voice rules and LinkedIn structure
from the system prompt. The idea may be rough — your job is to turn it into a post
that sounds like Juan wrote it after thinking about this problem for a while.
Return JSON with the fields specified in the output_format.
</instructions>
"""
    return f"""
<brief>
{json.dumps(brief, indent=2)}
</brief>

<instructions>
Write a LinkedIn post based on the brief above.
Apply the voice rules and LinkedIn structure from the system prompt exactly.
Return JSON with the fields specified in the output_format.
</instructions>
"""


def call_llm(system: str, user: str, temperature: float = 0.4) -> str:
    payload = {
        "model": PROXY_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 2048,
        "temperature": temperature,
    }
    resp = requests.post(PROXY_URL, json=payload, headers=PROXY_HEADERS, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def save_to_queue(
    topic: str,
    text: str,
    hashtags: list[str],
    headline: str,
    hook_score: str,
    voice_check: str,
    idea_source: str | None,
) -> str:
    piece_id = uuid.uuid4().hex[:16]
    now = datetime.now(UTC).isoformat()
    filename = f"linkedin-{piece_id}.json"
    output_dir = Path("data/content-queue")
    output_dir.mkdir(parents=True, exist_ok=True)

    full_text = text
    if hashtags and not any(h in text for h in hashtags):
        full_text = f"{text}\n\n{' '.join(hashtags)}"

    data = {
        "piece_id": piece_id,
        "platform": "linkedin",
        "content_type": "text_post",
        "topic": topic,
        "headline": headline,
        "text": full_text,
        "hashtags": hashtags,
        "char_count": len(full_text),
        "status": "pending_review",
        "generated_at": now,
        "idea_source": idea_source,
        "agent_trace": [
            {
                "agent_id": "generate_linkedin_post.py",
                "model": PROXY_MODEL,
                "generated_at": now,
            }
        ],
        "quality": {
            "hook_score": hook_score,
            "voice_check": voice_check,
        },
    }

    path = output_dir / filename
    path.write_text(json.dumps(data, indent=2))
    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a LinkedIn post via Holus")
    parser.add_argument("--idea", type=str, default=None, help="Raw idea to turn into a post")
    args = parser.parse_args()

    topic = args.idea or DEFAULT_BRIEF["topic"]
    print(f"\nGenerating LinkedIn post via Holus...\nTopic: {topic}\n")
    print("=" * 60)

    user_msg = build_user_message(args.idea, DEFAULT_BRIEF)
    raw = call_llm(SYSTEM_PROMPT, user_msg)

    # Strip markdown code fences if model wrapped in ```json
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        parsed = json.loads(cleaned)
        post_text = parsed.get("text", cleaned)
        headline = parsed.get("headline", topic)
        hashtags = parsed.get("hashtags", [])
        hook_score = str(parsed.get("hook_score", "?"))
        voice_check = parsed.get("voice_check", "?")
    except (json.JSONDecodeError, TypeError):
        post_text = raw
        headline = topic
        hashtags = []
        hook_score = "?"
        voice_check = "?"

    full_text = post_text
    if hashtags and not any(h in post_text for h in hashtags):
        full_text = f"{post_text}\n\n{' '.join(hashtags)}"

    print(f"HEADLINE: {headline}\n")
    print("POST TEXT:")
    print("-" * 60)
    print(post_text)
    print("-" * 60)
    if hashtags:
        print(f"\nHASHTAGS: {' '.join(hashtags)}")
    print(f"\nChar count: {len(full_text)}/3000")
    print(f"Hook score: {hook_score}/10")
    print(f"Voice check: {voice_check}")

    saved_path = save_to_queue(
        topic=topic,
        text=post_text,
        hashtags=hashtags,
        headline=headline,
        hook_score=hook_score,
        voice_check=voice_check,
        idea_source=args.idea,
    )
    print(f"\nSaved to: {saved_path}")
    print("\nReview in Observatory → localhost:3000/content")


if __name__ == "__main__":
    main()
