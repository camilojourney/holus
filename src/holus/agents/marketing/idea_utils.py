"""Shared utilities for the idea-injection content pipeline.

Contains the LLM proxy call function, output cleanup helpers,
and the 3-layer PromptLoader wrapper used by all pipeline stages.
"""

from __future__ import annotations

import logging
import re
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


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting that social platforms render as literal characters."""
    # **bold** or __bold__ -> just the text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    # *italic* -> just the text (but not bullet points like "* item")
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    # # headings -> just the text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    return text


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


def _strip_word_counts(obj: Any) -> Any:
    """Strip word count annotations the LLM sometimes includes (e.g., '(24 words)')."""
    if isinstance(obj, str):
        return re.sub(r"\s*\(\d+\s*words?\)", "", obj).strip()
    if isinstance(obj, list):
        return [_strip_word_counts(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _strip_word_counts(v) for k, v in obj.items()}
    return obj
