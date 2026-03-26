"""Humanization pipeline — make AI content sound like Camilo.

Two layers:
- Layer 2: Personal context injection (select relevant anecdotes/metrics)
- Layer 3: Style transfer + Turing test

Usage::

    from holus.agents.marketing.humanize import (
        select_personal_context,
        humanize_text,
        turing_test,
    )
"""

from __future__ import annotations

import json
import logging
import random
import re
from pathlib import Path
from typing import Any

import requests

from holus.core.llm_proxy import get_proxy_headers, get_proxy_url

logger = logging.getLogger(__name__)

PERSONAL_CONTEXT_PATH = Path("data/personal-context.json")

# Haiku model for cost-efficient rewrites (~$0.003/call)
HAIKU_MODEL = "anthropic/claude-haiku-4-5-20251001"

PROXY_URL = get_proxy_url()
PROXY_HEADERS = get_proxy_headers()

# ---------------------------------------------------------------------------
# Layer 2 — Personal context injection
# ---------------------------------------------------------------------------


def load_personal_context() -> dict[str, list[dict[str, Any]]]:
    """Load personal-context.json.

    Returns dict with keys like ``anecdotes``, ``metrics``, ``opinions``,
    ``project_facts`` — each mapping to a list of entry dicts.

    Returns empty dict if file is missing or malformed.
    """
    try:
        raw = PERSONAL_CONTEXT_PATH.read_text(encoding="utf-8")
        data: dict[str, list[dict[str, Any]]] = json.loads(raw)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load personal context: %s", exc)
        return {}


def select_personal_context(
    product: str = "",
    topics: list[str] | None = None,
    count: int = 3,
) -> list[dict[str, Any]]:
    """Select 2-3 relevant personal context entries.

    Filters by *product* match and *topic* overlap across all categories
    (anecdotes, metrics, opinions, project_facts).  Random within the
    filtered set so consecutive calls return different entries.

    Returns list of context entry dicts, each containing at least ``text``.
    """
    ctx = load_personal_context()
    if not ctx:
        return []

    # Flatten all categories into a single pool
    pool: list[dict[str, Any]] = []
    for entries in ctx.values():
        if isinstance(entries, list):
            pool.extend(entries)

    if not pool:
        return []

    # --- Filter by product ---
    if product:
        product_lower = product.lower()
        product_filtered = [
            e for e in pool if product_lower in [p.lower() for p in e.get("products", [])]
        ]
        # Fall back to full pool if no product match
        if product_filtered:
            pool = product_filtered

    # --- Filter by topic overlap ---
    if topics:
        topics_lower = {t.lower() for t in topics}
        topic_scored: list[tuple[int, dict[str, Any]]] = []
        for entry in pool:
            entry_topics = {t.lower() for t in entry.get("topics", [])}
            overlap = len(topics_lower & entry_topics)
            if overlap > 0:
                topic_scored.append((overlap, entry))
        if topic_scored:
            # Sort by overlap descending, then shuffle ties
            topic_scored.sort(key=lambda x: x[0], reverse=True)
            pool = [e for _, e in topic_scored]

    # Shuffle and take up to *count*
    selected = list(pool)
    random.shuffle(selected)
    return selected[:count]


def format_personal_context(entries: list[dict[str, Any]]) -> str:
    """Format selected entries for prompt injection.

    Returns a string block that can be inserted into a system prompt, e.g.::

        ## Your Real Experiences (reference these — they're TRUE)

        - You built genpeli's pipeline. One command replaces 4 hours of manual editing.
        - The judge evaluator was broken for 2 months because of a one-line path bug.

        Use at least ONE of these real facts in your post. They make it authentic.
    """
    if not entries:
        return ""

    lines = ["## Your Real Experiences (reference these — they're TRUE)", ""]
    for entry in entries:
        text = entry.get("text", "").strip()
        if text:
            # Truncate to first sentence or 200 chars for brevity in prompts
            short = text[:200].rstrip(".")
            if len(text) > 200:
                short += "..."
            lines.append(f"- {short}")

    lines.append("")
    lines.append("Use at least ONE of these real facts in your post. They make it authentic.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Layer 3 — Style transfer + Turing test
# ---------------------------------------------------------------------------

HUMANIZE_SYSTEM_PROMPT = """\
You are Camilo. Rewrite the text below to match your voice.

Voice rules:
- First person singular. "I built", "I learned", "I realized". Never "we".
- Contractions always. "it's", "don't", "you're". Never formal.
- Short paragraphs (1-3 sentences). Line breaks for emphasis.
- Opinionated. Takes a position. Doesn't hedge.
- No corporate speak. No empty hype. No ChatGPT-isms.
- No exclamation marks. Confidence doesn't shout.
- Em-dashes for asides.
- Arrow bullets (→) for technical lists.

Specific changes to make:
- Break one long paragraph into shorter ones.
- Add one rough edge (an aside, a self-correction, a "look—").
- Remove one qualifier ("I think", "maybe", "perhaps", "it seems").
- Make one sentence unexpectedly short.

Keep ALL factual claims intact. Do not invent new facts.
Return ONLY the rewritten text. No commentary, no preamble."""


def humanize_text(text: str, voice_examples: list[str] | None = None) -> str:
    """Style-transfer rewrite with Haiku to match Camilo's voice.

    Calls the LLM proxy with Haiku model.
    Cost: ~$0.003 per piece.
    Falls back to original text if LLM call fails.
    """
    system = HUMANIZE_SYSTEM_PROMPT
    if voice_examples:
        examples_block = "\n\n## Voice Examples (match this style)\n\n"
        for i, ex in enumerate(voice_examples, 1):
            examples_block += f"Example {i}:\n{ex}\n\n"
        system += examples_block

    user_msg = f"Rewrite this:\n\n{text}"

    result = _call_llm(HAIKU_MODEL, system, user_msg, temperature=0.7)
    if not result:
        logger.warning("humanize_text: LLM call failed, returning original text")
        return text
    return result


TURING_SYSTEM_PROMPT = """\
You are an expert at detecting AI-generated content.

Below are {total} posts. Exactly ONE is AI-generated. The rest are written by a real person.

Read all of them carefully, then respond with ONLY a JSON object:
{{"ai_post": <number 1-{total}>, "confidence": <float 0.0 to 1.0>}}

"confidence" = how certain you are that you correctly identified the AI post.
1.0 = absolutely certain, 0.0 = pure guess.

Respond with ONLY the JSON. No explanation."""


def turing_test(candidate: str, real_posts: list[str]) -> float:
    """A/B corpus comparison — can Haiku identify the AI post?

    Shuffles ``real_posts`` + ``candidate``. Asks Haiku which is AI-generated.

    Returns confidence 0.0-1.0 (how easily the AI post was identified).
    Score > 0.8 = too obviously AI, needs more work.
    Score < 0.5 = passes the test.

    Cost: ~$0.002 per test.
    Falls back to 0.5 (uncertain) if LLM call fails.
    """
    if not real_posts:
        return 0.5

    # Build the shuffled corpus
    posts = list(real_posts)
    # Insert candidate at a random position
    candidate_idx = random.randint(0, len(posts))
    posts.insert(candidate_idx, candidate)
    # candidate is at 1-indexed position candidate_idx + 1
    candidate_pos = candidate_idx + 1
    total = len(posts)

    # Format posts for the prompt
    user_parts: list[str] = []
    for i, post in enumerate(posts, 1):
        user_parts.append(f"--- Post {i} ---\n{post}")

    user_msg = "\n\n".join(user_parts)

    system = TURING_SYSTEM_PROMPT.format(total=total)
    raw = _call_llm(HAIKU_MODEL, system, user_msg, temperature=0.0)

    if not raw:
        return 0.5

    return _parse_turing_response(raw, candidate_pos)


def _parse_turing_response(raw: str, candidate_pos: int) -> float:
    """Parse Turing test JSON response and compute final score.

    If the model correctly identified the AI post, return its confidence.
    If the model picked the wrong post, return 0.0 (undetectable).
    Falls back to 0.5 on parse failure.
    """
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        data = json.loads(cleaned)
        picked = int(data.get("ai_post", 0))
        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        if picked == candidate_pos:
            # Correctly identified — return confidence as detectability score
            return confidence
        # Wrong guess — the candidate passed
        return 0.0
    except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
        logger.warning("Failed to parse Turing test response: %s", exc)
        return 0.5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _call_llm(model: str, system: str, user: str, temperature: float = 0.3) -> str:
    """Call the LLM proxy. Returns response text or empty string on failure."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 4096,
        "temperature": temperature,
    }
    try:
        resp = requests.post(PROXY_URL, json=payload, headers=PROXY_HEADERS, timeout=120)
        resp.raise_for_status()
        result: str = resp.json()["choices"][0]["message"]["content"]
        return result
    except Exception as exc:
        logger.warning("LLM proxy call failed: %s", exc)
        return ""
