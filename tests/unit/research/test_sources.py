from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from holus.research.sources.arxiv import ArxivAdapter
from holus.research.sources.base import stable_item_id
from holus.research.sources.hackernews import HackerNewsAdapter
from holus.research.sources.rss import RssAdapter


@pytest.mark.asyncio
async def test_arxiv_adapter_parses_stubbed_atom_response() -> None:
    entries = "".join(
        f"""
        <entry>
          <id>http://arxiv.org/abs/2401.0000{i}</id>
          <updated>2026-06-25T00:00:00Z</updated>
          <published>2026-06-25T00:00:00Z</published>
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
