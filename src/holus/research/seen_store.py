"""Append-only seen ledger for Research Radar."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from holus.research.sources.base import canonical_url

if TYPE_CHECKING:
    from holus.research.models import RawResearchItem


class SeenStore:
    """Tracks fetched research items by stable item id and canonical URL."""

    def __init__(self, path: Path | str = "data/research/seen.jsonl") -> None:
        self.path = Path(path)
        self._seen_item_ids: set[str] | None = None
        self._seen_urls: set[str] | None = None

    def has_seen(self, item: RawResearchItem) -> bool:
        self._load()
        return item.item_id in self._seen_item_ids_or_empty() or (
            canonical_url(str(item.url)) in self._seen_urls_or_empty()
        )

    def mark_seen(self, item: RawResearchItem) -> None:
        self._load()
        item_url = canonical_url(str(item.url))
        if (
            item.item_id in self._seen_item_ids_or_empty()
            and item_url in self._seen_urls_or_empty()
        ):
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry: dict[str, Any] = {
            "item_id": item.item_id,
            "source": item.source,
            "source_id": item.source_id,
            "canonical_url": item_url,
            "seen_at": datetime.now(UTC).isoformat(),
            "title": item.title,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
        self._seen_item_ids_or_empty().add(item.item_id)
        self._seen_urls_or_empty().add(item_url)

    def _load(self) -> None:
        if self._seen_item_ids is not None and self._seen_urls is not None:
            return
        self._seen_item_ids = set()
        self._seen_urls = set()
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                item_id = row.get("item_id")
                item_url = row.get("canonical_url")
                if isinstance(item_id, str):
                    self._seen_item_ids.add(item_id)
                if isinstance(item_url, str):
                    self._seen_urls.add(item_url)

    def _seen_item_ids_or_empty(self) -> set[str]:
        if self._seen_item_ids is None:
            self._seen_item_ids = set()
        return self._seen_item_ids

    def _seen_urls_or_empty(self) -> set[str]:
        if self._seen_urls is None:
            self._seen_urls = set()
        return self._seen_urls
