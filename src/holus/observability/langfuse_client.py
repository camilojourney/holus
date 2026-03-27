"""Langfuse integration for tracing Holus agent operations.

Self-hosted on the Mac Mini for zero cost and full data ownership.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def create_langfuse_client(
    public_key: str | None = None,
    secret_key: str | None = None,
    host: str = "http://localhost:3100",
):
    """Create a Langfuse client pointing to the self-hosted instance.

    Keys come from environment variables or explicit params:
      - ``LANGFUSE_PUBLIC_KEY``
      - ``LANGFUSE_SECRET_KEY``
      - ``LANGFUSE_HOST``
    """
    from langfuse import Langfuse

    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )
