"""RSS/Atom feed adapter."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from holus.research.models import RawResearchItem
from holus.research.sources.base import clean_text, parse_datetime, parse_http_url, stable_item_id

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class RssAdapter:
    source = "rss"

    def __init__(
        self,
        *,
        feeds: list[str],
        per_feed_limit: int = 10,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.feeds = feeds
        self.per_feed_limit = per_feed_limit
        self._client = client

    async def fetch(self, window_days: int) -> list[RawResearchItem]:
        items: list[RawResearchItem] = []
        errors: list[str] = []
        for feed_url in self.feeds:
            try:
                if self._client is None:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(feed_url)
                else:
                    response = await self._client.get(feed_url)
                response.raise_for_status()
                items.extend(self._parse_feed(response.text, feed_url, window_days))
            except Exception as exc:
                errors.append(f"{feed_url}: {exc}")
        if errors and not items:
            raise RuntimeError("; ".join(errors))
        return items

    def _parse_feed(self, xml_text: str, feed_url: str, window_days: int) -> list[RawResearchItem]:
        root = ET.fromstring(xml_text)
        fetch_time = datetime.now(UTC)
        cutoff = fetch_time - timedelta(days=window_days)
        entries = self._atom_entries(root) or self._rss_entries(root)
        items: list[RawResearchItem] = []
        for entry in entries[: self.per_feed_limit]:
            source_id = self._entry_id(entry, feed_url)
            published_at = self._entry_datetime(entry, fetch_time)
            if published_at < cutoff:
                continue
            url = self._entry_link(entry)
            title = self._entry_title(entry)
            if not source_id or not url or not title:
                continue
            items.append(
                RawResearchItem(
                    source="rss",
                    source_id=source_id,
                    item_id=stable_item_id("rss", source_id),
                    title=clean_text(title, limit=240),
                    url=parse_http_url(url),
                    summary=clean_text(self._entry_summary(entry) or title),
                    author=self._entry_author(entry),
                    published_at=published_at,
                    raw_meta={"feed_url": feed_url},
                )
            )
        return items

    @staticmethod
    def _atom_entries(root: ET.Element) -> list[ET.Element]:
        return root.findall("atom:entry", ATOM_NS)

    @staticmethod
    def _rss_entries(root: ET.Element) -> list[ET.Element]:
        return root.findall("./channel/item")

    @staticmethod
    def _text(entry: ET.Element, path: str, namespaces: dict[str, str] | None = None) -> str:
        found = entry.find(path, namespaces or {})
        return found.text.strip() if found is not None and found.text else ""

    def _entry_id(self, entry: ET.Element, feed_url: str) -> str:
        return (
            self._text(entry, "atom:id", ATOM_NS)
            or self._text(entry, "guid")
            or self._entry_link(entry)
            or f"{feed_url}:{self._entry_title(entry)}"
        )

    def _entry_link(self, entry: ET.Element) -> str:
        atom_link = entry.find("atom:link", ATOM_NS)
        if atom_link is not None:
            href = atom_link.attrib.get("href")
            if href:
                return href
        return self._text(entry, "link")

    def _entry_title(self, entry: ET.Element) -> str:
        return self._text(entry, "atom:title", ATOM_NS) or self._text(entry, "title")

    def _entry_summary(self, entry: ET.Element) -> str:
        return (
            self._text(entry, "atom:summary", ATOM_NS)
            or self._text(entry, "atom:content", ATOM_NS)
            or self._text(entry, "description")
        )

    def _entry_author(self, entry: ET.Element) -> str | None:
        value = self._text(entry, "atom:author/atom:name", ATOM_NS) or self._text(entry, "author")
        return value or None

    def _entry_datetime(self, entry: ET.Element, fetch_time: datetime) -> datetime:
        raw: Any = (
            self._text(entry, "atom:published", ATOM_NS)
            or self._text(entry, "atom:updated", ATOM_NS)
            or self._text(entry, "pubDate")
        )
        return parse_datetime(str(raw) if raw else None, fallback=fetch_time)
