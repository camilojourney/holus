"""Shared source adapter contracts and helpers."""

from __future__ import annotations

import hashlib
import html
import ipaddress
import re
import socket
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Protocol
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from pydantic import HttpUrl, TypeAdapter

if TYPE_CHECKING:
    from holus.research.models import RawResearchItem

SUMMARY_LIMIT = 1200
HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
}
MAX_SAFE_REDIRECTS = 5


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
        try:
            parsed = parsedate_to_datetime(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except (TypeError, ValueError):
            pass
    return fallback or datetime.now(UTC)


def canonical_url(value: str) -> str:
    """Normalize transport and tracking noise without dropping source identity."""
    split = urlsplit(value)
    host = split.netloc.lower()
    path = split.path.rstrip("/") or "/"
    query = _identity_query(split.query)
    return urlunsplit((split.scheme.lower(), host, path, query, ""))


def _identity_query(query: str) -> str:
    pairs = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_QUERY_KEYS or lowered.startswith(TRACKING_QUERY_PREFIXES):
            continue
        pairs.append((key, value))
    pairs.sort()
    return urlencode(pairs, doseq=True)


def parse_http_url(value: str) -> HttpUrl:
    """Validate source URLs before creating Pydantic boundary models."""
    return HTTP_URL_ADAPTER.validate_python(value)


def validate_public_http_url(value: str) -> str:
    """Reject non-public HTTP destinations before a network request is made."""
    split = urlsplit(value)
    if split.scheme.lower() not in {"http", "https"}:
        msg = f"unsupported URL scheme: {split.scheme or '<missing>'}"
        raise ValueError(msg)
    if not split.hostname:
        msg = "URL host is required"
        raise ValueError(msg)
    _validate_public_host(split.hostname)
    return value


async def safe_get(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Fetch a public URL while validating every redirect target."""
    current_url = validate_public_http_url(url)
    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=timeout)
    try:
        for _ in range(MAX_SAFE_REDIRECTS + 1):
            response = await active_client.get(
                current_url,
                follow_redirects=False,
                headers=headers,
            )
            if response.status_code not in {301, 302, 303, 307, 308}:
                response.raise_for_status()
                return response
            location = response.headers.get("location")
            if not location:
                response.raise_for_status()
                return response
            current_url = validate_public_http_url(urljoin(current_url, location))
        msg = f"too many redirects fetching {url}"
        raise httpx.TooManyRedirects(msg)
    finally:
        if owns_client:
            await active_client.aclose()


def _validate_public_host(hostname: str) -> None:
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            msg = f"could not resolve URL host: {hostname}"
            raise ValueError(msg) from exc
        addresses = []
        for info in infos:
            address = info[4][0]
            try:
                addresses.append(ipaddress.ip_address(address))
            except ValueError:
                continue
    if not addresses:
        msg = f"could not resolve URL host: {hostname}"
        raise ValueError(msg)
    blocked = [
        address
        for address in addresses
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        )
    ]
    if blocked:
        msg = f"URL host resolves to a non-public address: {hostname}"
        raise ValueError(msg)
