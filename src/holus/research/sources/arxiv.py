"""arXiv export API adapter."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta

import httpx

from holus.research.models import RawResearchItem
from holus.research.sources.base import clean_text, parse_datetime, parse_http_url, stable_item_id

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
DEFAULT_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]


class ArxivAdapter:
    source = "arxiv"

    def __init__(
        self,
        *,
        categories: list[str] | None = None,
        max_results: int = 25,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.categories = categories or DEFAULT_CATEGORIES
        self.max_results = max_results
        self._client = client

    async def fetch(self, window_days: int) -> list[RawResearchItem]:
        query = " OR ".join(f"cat:{category}" for category in self.categories)
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(self.max_results),
        }
        if self._client is None:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(ARXIV_API_URL, params=params)
        else:
            response = await self._client.get(ARXIV_API_URL, params=params)
        response.raise_for_status()
        return self._parse_feed(response.text, window_days)

    def _parse_feed(self, xml_text: str, window_days: int) -> list[RawResearchItem]:
        root = ET.fromstring(xml_text)
        cutoff = datetime.now(UTC) - timedelta(days=window_days)
        items: list[RawResearchItem] = []
        for entry in root.findall("atom:entry", ATOM_NS):
            source_id = self._entry_text(entry, "atom:id").split("/")[-1]
            published_at = parse_datetime(self._entry_text(entry, "atom:published"))
            if published_at < cutoff:
                continue
            title = clean_text(self._entry_text(entry, "atom:title"), limit=240)
            summary = clean_text(self._entry_text(entry, "atom:summary"))
            url = self._entry_text(entry, "atom:id")
            author = self._entry_text(entry, "atom:author/atom:name") or None
            items.append(
                RawResearchItem(
                    source="arxiv",
                    source_id=source_id,
                    item_id=stable_item_id("arxiv", source_id),
                    title=title,
                    url=parse_http_url(url),
                    summary=summary,
                    author=author,
                    published_at=published_at,
                    raw_meta={"categories": self.categories},
                )
            )
        return items

    @staticmethod
    def _entry_text(entry: ET.Element, path: str) -> str:
        found = entry.find(path, ATOM_NS)
        return found.text.strip() if found is not None and found.text else ""
