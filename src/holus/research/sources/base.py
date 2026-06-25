"""Shared source adapter contracts and helpers."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlsplit, urlunsplit

from pydantic import HttpUrl, TypeAdapter

if TYPE_CHECKING:
    from holus.research.models import RawResearchItem

SUMMARY_LIMIT = 1200
HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


class SourceAdapter(Protocol):
    source: str

    async def fetch(self, window_days: int) -> list[RawResearchItem]:
        """Fetch research items inside the configured lookback window."""


def stable_item_id(source: str, source_id: str) -> str:
    """Return the spec-defined stable global id."""
    return hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()[:16]


def clean_text(value: str, *, limit: int = SUMMARY_LIMIT) -> str:
    """Strip HTML tags/entities and cap long source text."""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def parse_datetime(value: str | None, *, fallback: datetime | None = None) -> datetime:
    """Parse common feed timestamps into timezone-aware datetimes."""
    if value:
        raw = value.strip()
        for candidate in (raw, raw.replace("Z", "+00:00")):
            try:
                parsed = datetime.fromisoformat(candidate)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed
            except ValueError:
                continue
    return fallback or datetime.now(UTC)


def canonical_url(value: str) -> str:
    """Normalize URLs for cross-source dedupe."""
    split = urlsplit(value)
    host = split.netloc.lower()
    path = split.path.rstrip("/") or "/"
    return urlunsplit((split.scheme.lower(), host, path, "", ""))


def parse_http_url(value: str) -> HttpUrl:
    """Validate source URLs before creating Pydantic boundary models."""
    return HTTP_URL_ADAPTER.validate_python(value)
