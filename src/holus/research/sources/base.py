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
    """Validate scheme and host before DNS and public-address checks."""
    split = urlsplit(value)
    if split.scheme.lower() not in {"http", "https"}:
        msg = f"unsupported URL scheme: {split.scheme or '<missing>'}"
        raise ValueError(msg)
    if not split.hostname:
        msg = "URL host is required"
        raise ValueError(msg)
    return value


async def safe_get(
    url: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Fetch a public URL while validating every redirect target."""
    current_url = validate_public_http_url(url)
    test_client = (
        httpx.AsyncClient(transport=transport, timeout=timeout, trust_env=False)
        if transport is not None
        else None
    )
    try:
        for _ in range(MAX_SAFE_REDIRECTS + 1):
            pinned_url, host_header, sni_hostname = _pin_public_url(current_url)
            request_headers = dict(headers or {})
            request_headers["host"] = host_header
            if test_client is not None:
                response = await test_client.get(
                    pinned_url,
                    follow_redirects=False,
                    headers=request_headers,
                    extensions={"sni_hostname": sni_hostname},
                )
            else:
                async with httpx.AsyncClient(
                    transport=httpx.AsyncHTTPTransport(),
                    timeout=timeout,
                    trust_env=False,
                ) as active_client:
                    response = await active_client.get(
                        pinned_url,
                        follow_redirects=False,
                        headers=request_headers,
                        extensions={"sni_hostname": sni_hostname},
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
        if test_client is not None:
            await test_client.aclose()


def _pin_public_url(value: str) -> tuple[str, str, bytes]:
    split = urlsplit(value)
    hostname = split.hostname
    if hostname is None:
        raise ValueError("URL host is required")
    address = _resolve_public_addresses(hostname)[0]
    address_text = f"[{address}]" if address.version == 6 else str(address)
    port = split.port
    netloc = f"{address_text}:{port}" if port is not None else address_text
    default_port = 443 if split.scheme.lower() == "https" else 80
    host_header = hostname if port in {None, default_port} else f"{hostname}:{port}"
    pinned_url = urlunsplit((split.scheme, netloc, split.path, split.query, split.fragment))
    return pinned_url, host_header, hostname.encode("ascii")


def _resolve_public_addresses(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
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
    return addresses
