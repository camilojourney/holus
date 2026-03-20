"""Constitutional AI revision loop — generate → critique → revise.

Before publishing, content goes through a self-critique cycle:
1. Generate content (already done by idea_runner)
2. Critique: an independent LLM call identifies weaknesses
3. Revise: the generator rewrites addressing the critique

This is NOT the same as reflexion (which happens AFTER failure).
This is proactive quality improvement BEFORE the judge scores.

Based on Anthropic's Constitutional AI: the critique is guided by
a "constitution" of content principles.

Usage::

    loop = RevisionLoop()
    revised = await loop.revise(original_text, content_type, platform)
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from holus.core.llm_proxy import get_proxy_headers, get_proxy_url

logger = logging.getLogger(__name__)

PROXY_URL = get_proxy_url()
PROXY_HEADERS = get_proxy_headers()

# The content constitution — principles for self-critique
CONTENT_CONSTITUTION = """
1. HOOK POWER: The first sentence must stop someone mid-scroll. If it's generic ("Let's talk about X"), it fails.
2. ONE THESIS: The post must defend exactly one claim. No second thesis, even if related.
3. SPECIFICITY: Every claim must have a specific example, number, or experience. No vague assertions.
4. VOICE: First person singular. Contractions. Opinionated. No hedging ("I think", "maybe", "perhaps").
5. BREVITY: Every sentence must earn its place. If a sentence can be deleted without losing meaning, delete it.
6. CTA WEIGHT: The closing question must be lightweight. No "follow me". No "share this". Just a genuine question.
7. NO FILLER: Remove "In today's world", "It's worth noting", "Let me explain", "Here's the thing".
8. AUTHORITY: The post must establish the author as someone who BUILT the thing, not someone who READ about it.
"""

CRITIQUE_PROMPT = f"""You are a ruthless content editor. Your job is to find EVERY weakness in this content.

CONSTITUTION (rules the content must follow):
{CONTENT_CONSTITUTION}

For each rule violated, cite the specific text that violates it and explain why.
For rules that are followed well, say "PASS" with a brief note.

Be specific. Quote the problematic text. Don't be nice.
End with a numbered list of SPECIFIC changes to make (max 5)."""

REVISE_PROMPT = """You are the content author. A ruthless editor just critiqued your work.
Apply EVERY suggested change. Keep the same voice and structure.
Do NOT add new content — only fix what was flagged.
Return the complete revised text only, no commentary."""


async def critique(text: str, content_type: str, platform: str) -> str:
    """Critique content against the constitution. Returns critique text."""
    user_msg = f"""
<content_type>{content_type}</content_type>
<platform>{platform}</platform>

<content>
{text}
</content>

Critique this content against the constitution. Be specific.
"""
    return _call("anthropic/claude-sonnet-4-6", CRITIQUE_PROMPT, user_msg)


async def revise(text: str, critique_text: str) -> str:
    """Revise content based on critique. Returns revised text."""
    user_msg = f"""
<original>
{text}
</original>

<critique>
{critique_text}
</critique>

Apply all suggested changes. Return the complete revised text only.
"""
    return _call("anthropic/claude-sonnet-4-6", REVISE_PROMPT, user_msg)


def _call(model: str, system: str, user: str) -> str:
    """Call LLM via proxy."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
    }
    try:
        resp = requests.post(PROXY_URL, json=payload, headers=PROXY_HEADERS, timeout=120)
        resp.raise_for_status()
        result: str = resp.json()["choices"][0]["message"]["content"]
        return result
    except Exception as exc:
        logger.warning("Revision loop LLM call failed: %s", exc)
        return ""


def _call_sync(system: str, user: str) -> str:
    """Synchronous LLM call for use in sync contexts."""
    return _call("anthropic/claude-sonnet-4-6", system, user)


class RevisionLoop:
    """Generate → Critique → Revise loop for content quality."""

    def __init__(self, max_rounds: int = 1) -> None:
        self.max_rounds = max_rounds

    def _call_sync(self, text: str, content_type: str, platform: str) -> str:
        """Synchronous critique for use in sync contexts (idea_runner)."""
        user_msg = f"<content_type>{content_type}</content_type>\n<platform>{platform}</platform>\n<content>\n{text}\n</content>\nCritique this content against the constitution. Be specific."
        return _call("anthropic/claude-sonnet-4-6", CRITIQUE_PROMPT, user_msg)

    def _revise_sync(self, text: str, critique_text: str) -> str:
        """Synchronous revision for use in sync contexts."""
        user_msg = f"<original>\n{text}\n</original>\n<critique>\n{critique_text}\n</critique>\nApply all suggested changes. Return the complete revised text only."
        return _call("anthropic/claude-sonnet-4-6", REVISE_PROMPT, user_msg)

    async def improve(
        self,
        text: str,
        content_type: str,
        platform: str,
    ) -> dict[str, Any]:
        """Run the revision loop on content.

        Returns {revised_text, critique, rounds, improved}.
        """
        current = text
        all_critiques: list[str] = []

        for round_num in range(self.max_rounds):
            # Critique
            critique_text = await critique(current, content_type, platform)
            if not critique_text:
                break
            all_critiques.append(critique_text)

            # Check if critique finds significant issues
            if "PASS" in critique_text and critique_text.count("PASS") >= 6:
                # Most rules passed — content is good enough
                logger.info("Revision round %d: content passes most rules", round_num + 1)
                break

            # Revise
            revised = await revise(current, critique_text)
            if not revised or revised == current:
                break

            current = revised
            logger.info("Revision round %d complete", round_num + 1)

        return {
            "revised_text": current,
            "original_text": text,
            "critiques": all_critiques,
            "rounds": len(all_critiques),
            "improved": current != text,
        }
