from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from holus.research.sources.arxiv import ArxivAdapter
from holus.research.sources.base import canonical_url, parse_datetime, safe_get, stable_item_id
from holus.research.sources.hackernews import HackerNewsAdapter
from holus.research.sources.rss import RssAdapter


@pytest.mark.asyncio
async def test_arxiv_adapter_parses_stubbed_atom_response() -> None:
    published = datetime.now(UTC) - timedelta(days=1)
    entries = "".join(
        f"""
        <entry>
          <id>http://arxiv.org/abs/2401.0000{i}</id>
          <updated>{published.isoformat()}</updated>
          <published>{published.isoformat()}</published>
          <title>AI Paper {i}</title>
          <summary>Paper summary {i}</summary>
          <author><name>Author {i}</name></author>
        </entry>
        """
        for i in range(3)
    )
    payload = f"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>"""
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, text=payload))
    )
    try:
        items = await ArxivAdapter(client=client).fetch(window_days=7)
    finally:
        await client.aclose()

    assert len(items) == 3
    assert {item.source for item in items} == {"arxiv"}
    assert items[0].title == "AI Paper 0"
    assert str(items[0].url) == "http://arxiv.org/abs/2401.00000"
    assert items[0].published_at.tzinfo is not None
    assert items[0].item_id == stable_item_id("arxiv", "2401.00000")


@pytest.mark.asyncio
async def test_hackernews_adapter_uses_object_id_as_source_id() -> None:
    payload = {
        "hits": [
            {
                "objectID": "123",
                "title": "AI agents in production",
                "url": "https://example.com/agents",
                "created_at_i": int(datetime(2026, 6, 25, tzinfo=UTC).timestamp()),
                "author": "pg",
            }
        ]
    }
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    )
    try:
        items = await HackerNewsAdapter(client=client).fetch(window_days=7)
    finally:
        await client.aclose()

    assert len(items) == 1
    assert items[0].source == "hackernews"
    assert items[0].source_id == "123"
    assert items[0].item_id == stable_item_id("hackernews", "123")


@pytest.mark.asyncio
async def test_rss_adapter_parses_atom_and_defaults_missing_published_date() -> None:
    payload = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>one</id>
        <title>First AI item</title>
        <link href="https://example.com/one" />
        <summary>First summary</summary>
      </entry>
      <entry>
        <id>two</id>
        <title>Second AI item</title>
        <link href="https://example.com/two" />
        <summary>Second summary</summary>
      </entry>
    </feed>"""
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, text=payload))
    )
    try:
        items = await RssAdapter(feeds=["https://example.com/feed"], client=client).fetch(
            window_days=7
        )
    finally:
        await client.aclose()

    assert len(items) == 2
    assert {item.source for item in items} == {"rss"}
    assert all(item.published_at.tzinfo is not None for item in items)


def test_parse_datetime_accepts_rfc_2822_rss_dates() -> None:
    parsed = parse_datetime("Wed, 25 Jun 2026 12:34:56 GMT")

    assert parsed == datetime(2026, 6, 25, 12, 34, 56, tzinfo=UTC)


def test_canonical_url_preserves_identity_query_and_removes_tracking_noise() -> None:
    first = canonical_url("https://EXAMPLE.com/watch?v=1&utm_source=newsletter")
    second = canonical_url("https://example.com/watch?v=2&utm_source=newsletter")

    assert first == "https://example.com/watch?v=1"
    assert second == "https://example.com/watch?v=2"
    assert first != second


@pytest.mark.asyncio
async def test_safe_get_rejects_loopback_before_request() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("loopback URL should not be requested")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ValueError, match="non-public"):
            await safe_get("http://127.0.0.1/admin", client=client)
    finally:
        await client.aclose()
