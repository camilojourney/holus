"""Hacker News Algolia adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from holus.research.models import RawResearchItem
from holus.research.sources.base import clean_text, parse_http_url, stable_item_id

HN_API_URL = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNewsAdapter:
    source = "hackernews"

    def __init__(
        self,
        *,
        query: str = "artificial intelligence OR machine learning OR LLM",
        max_results: int = 25,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.query = query
        self.max_results = max_results
        self._client = client

    async def fetch(self, window_days: int) -> list[RawResearchItem]:
        created_after = int((datetime.now(UTC) - timedelta(days=window_days)).timestamp())
        params = {
            "query": self.query,
            "tags": "story",
            "hitsPerPage": str(self.max_results),
            "numericFilters": f"created_at_i>{created_after}",
        }
        if self._client is None:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(HN_API_URL, params=params)
        else:
            response = await self._client.get(HN_API_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        hits = payload.get("hits", []) if isinstance(payload, dict) else []
        return [item for hit in hits if (item := self._hit_to_item(hit)) is not None]

    def _hit_to_item(self, hit: Any) -> RawResearchItem | None:
        if not isinstance(hit, dict):
            return None
        source_id = str(hit.get("objectID") or "")
        title = str(hit.get("title") or hit.get("story_title") or "").strip()
        url = str(hit.get("url") or "")
        created_at_i = hit.get("created_at_i")
        if not source_id or not title or not url:
            return None
        published_at = (
            datetime.fromtimestamp(created_at_i, tz=UTC)
            if isinstance(created_at_i, int)
            else datetime.now(UTC)
        )
        summary = clean_text(
            str(hit.get("story_text") or hit.get("comment_text") or title),
        )
        return RawResearchItem(
            source="hackernews",
            source_id=source_id,
            item_id=stable_item_id("hackernews", source_id),
            title=clean_text(title, limit=240),
            url=parse_http_url(url),
            summary=summary,
            author=str(hit.get("author") or "") or None,
            published_at=published_at,
            raw_meta={
                "points": hit.get("points"),
                "num_comments": hit.get("num_comments"),
                "hn_url": f"https://news.ycombinator.com/item?id={source_id}",
            },
        )
