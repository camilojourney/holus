"""Shared LLM proxy configuration.

Single source of truth for the proxy URL and headers used to call
the local LLM proxy (litellm / OpenAI-compatible endpoint).

All modules that make raw HTTP calls to the proxy should import from here
instead of hardcoding ``http://localhost:8080/v1/chat/completions``.
"""

from __future__ import annotations

import os


def get_proxy_url() -> str:
    """Return the full chat-completions URL for the LLM proxy.

    Reads ``ANTHROPIC_BASE_URL`` (default ``http://localhost:8080``)
    and appends ``/v1/chat/completions``.
    """
    base = os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:8080")
    return f"{base.rstrip('/')}/v1/chat/completions"


def get_proxy_headers() -> dict[str, str]:
    """Return HTTP headers for the LLM proxy.

    Reads ``LLM_PROXY_AUTH_TOKEN`` (default ``Bearer local``).
    """
    token = os.environ.get("LLM_PROXY_AUTH_TOKEN", "Bearer local")
    return {
        "Content-Type": "application/json",
        "Authorization": token,
    }


def get_proxy_api_base() -> str:
    """Return the ``/v1`` base URL (for SDKs like DSPy that want a base, not a full path)."""
    base = os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:8080")
    return f"{base.rstrip('/')}/v1"


def get_proxy_api_key() -> str:
    """Return the bare API key token (without ``Bearer `` prefix) for SDK auth."""
    token = os.environ.get("LLM_PROXY_AUTH_TOKEN", "Bearer local")
    if token.startswith("Bearer "):
        return token[7:]
    return token


# Module-level constants for simple import-and-use.
# These are evaluated at import time; use the functions above
# if you need runtime re-evaluation (e.g. in tests).
PROXY_URL: str = get_proxy_url()
PROXY_HEADERS: dict[str, str] = get_proxy_headers()
