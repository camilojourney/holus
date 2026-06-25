"""Research Radar orchestration."""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence  # noqa: TC003 - used in public runtime signature.
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from holus.research.candidates import CandidateStore
from holus.research.curator import AsyncScoreCallable, ResearchCurator, ScoreCallable
from holus.research.digest import write_digest
from holus.research.models import RadarRunReport, RadarSourceResult, RawResearchItem, ResearchScore
from holus.research.seen_store import SeenStore
from holus.research.sources import ArxivAdapter, HackerNewsAdapter, RssAdapter
from holus.research.sources.base import SourceAdapter, canonical_url

SOURCE_PRIORITY = {"arxiv": 0, "hackernews": 1, "rss": 2}


@dataclass(frozen=True)
class ResearchRadarConfig:
    repo_root: Path
    window_days: int
    digest_threshold: float
    candidate_threshold: float
    research_dir: Path
    candidates_dir: Path
    seen_path: Path
    interests_path: Path
    arxiv_categories: list[str]
    arxiv_max_results: int
    hn_query: str
    hn_max_results: int
    rss_feeds: list[str]
    rss_per_feed_limit: int


def load_config(repo_root: Path) -> ResearchRadarConfig:
    config_path = repo_root / "config" / "research.yaml"
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    raw = _string_keyed_dict(loaded)
    sources = _dict_section(raw, "sources")
    arxiv = _dict_section(sources, "arxiv")
    hn = _dict_section(sources, "hackernews")
    rss = _dict_section(sources, "rss")
    paths = _dict_section(raw, "paths")
    thresholds = _dict_section(raw, "thresholds")
    return ResearchRadarConfig(
        repo_root=repo_root,
        window_days=int(raw.get("window_days", 7)),
        digest_threshold=float(thresholds.get("digest", 0.5)),
        candidate_threshold=float(thresholds.get("candidate", 0.65)),
        research_dir=repo_root / str(paths.get("research_dir", "data/research")),
        candidates_dir=repo_root / str(paths.get("candidates_dir", "data/research/candidates")),
        seen_path=repo_root / str(paths.get("seen_store", "data/research/seen.jsonl")),
        interests_path=repo_root / str(paths.get("interests", "config/research-interests.md")),
        arxiv_categories=[
            str(item) for item in arxiv.get("categories", ["cs.AI", "cs.CL", "cs.LG"])
        ],
        arxiv_max_results=int(arxiv.get("max_results", 25)),
        hn_query=str(hn.get("query", "artificial intelligence OR machine learning OR LLM")),
        hn_max_results=int(hn.get("max_results", 25)),
        rss_feeds=[str(item) for item in rss.get("feeds", [])],
        rss_per_feed_limit=int(rss.get("per_feed_limit", 10)),
    )


async def run_radar(
    *,
    repo_root: Path | str = ".",
    source_adapters: Sequence[SourceAdapter] | None = None,
    scorer: ScoreCallable | AsyncScoreCallable | None = None,
    run_date: date | None = None,
) -> RadarRunReport:
    """Fetch, dedupe, score, and emit research outputs."""
    root = Path(repo_root)
    config = load_config(root)
    started_at = datetime.now(UTC)
    digest_date = run_date or started_at.date()
    adapters = list(source_adapters) if source_adapters is not None else _default_adapters(config)
    seen_store = SeenStore(config.seen_path)
    candidate_store = CandidateStore(
        config.candidates_dir, queue_dir=root / "data" / "content-queue"
    )
    curator = ResearchCurator(
        interests=_read_text(config.interests_path),
        products=_read_products(root),
        scorer=scorer,
    )

    fetched_by_source: dict[str, list[RawResearchItem]] = {}
    source_errors: dict[str, str] = {}
    for adapter in adapters:
        try:
            fetched_by_source[adapter.source] = await adapter.fetch(config.window_days)
        except Exception as exc:
            fetched_by_source[adapter.source] = []
            source_errors[adapter.source] = str(exc)

    new_items_by_source: dict[str, int] = {adapter.source: 0 for adapter in adapters}
    new_items = _dedupe_new_items(fetched_by_source, seen_store, new_items_by_source)
    digest_entries: list[tuple[RawResearchItem, ResearchScore]] = []
    candidates_created = 0
    scored = 0

    for item in new_items:
        try:
            score = await curator.score(item)
        except Exception:
            continue
        scored += 1
        if score.should_read >= config.digest_threshold:
            digest_entries.append((item, score))
        if (
            score.relevance >= config.candidate_threshold
            and score.recommended_action == "candidate"
        ):
            candidate_store.create(item, score)
            candidates_created += 1
        seen_store.mark_seen(item)

    digest_path = _write_or_preserve_digest(config.research_dir, digest_date, digest_entries)
    source_results = [
        RadarSourceResult(
            source=adapter.source,
            status="failed" if adapter.source in source_errors else "ok",
            fetched=len(fetched_by_source.get(adapter.source, [])),
            new_items=new_items_by_source.get(adapter.source, 0),
            error=source_errors.get(adapter.source),
        )
        for adapter in adapters
    ]
    return RadarRunReport(
        run_id=uuid.uuid4().hex,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        sources=source_results,
        scored=scored,
        digest_path=str(digest_path) if digest_path else None,
        candidates_created=candidates_created,
    )


def record_outcome(
    item_id: str,
    signal: dict[str, Any],
    *,
    trajectory_path: Path | str = ".self-improvement/memory/trajectory.jsonl",
) -> Path:
    """Append research-origin outcome signal for later curator tuning."""
    path = Path(trajectory_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "agent_id": "research-radar",
        "action": "record_research_outcome",
        "outcome": "success",
        "item_id": item_id,
        "signal": signal,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return path


def _default_adapters(config: ResearchRadarConfig) -> list[SourceAdapter]:
    adapters: list[SourceAdapter] = [
        ArxivAdapter(categories=config.arxiv_categories, max_results=config.arxiv_max_results),
        HackerNewsAdapter(query=config.hn_query, max_results=config.hn_max_results),
    ]
    if config.rss_feeds:
        adapters.append(
            RssAdapter(feeds=config.rss_feeds, per_feed_limit=config.rss_per_feed_limit)
        )
    return adapters


def _dict_section(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    return _string_keyed_dict(mapping.get(key))


def _string_keyed_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(item_key): item_value for item_key, item_value in value.items()}


def _dedupe_new_items(
    fetched_by_source: dict[str, list[RawResearchItem]],
    seen_store: SeenStore,
    new_items_by_source: dict[str, int],
) -> list[RawResearchItem]:
    all_items = [
        item
        for items in fetched_by_source.values()
        for item in items
        if not seen_store.has_seen(item)
    ]
    all_items.sort(key=lambda item: (SOURCE_PRIORITY.get(item.source, 99), str(item.published_at)))
    seen_urls: set[str] = set()
    deduped: list[RawResearchItem] = []
    for item in all_items:
        item_url = canonical_url(str(item.url))
        if item_url in seen_urls:
            continue
        seen_urls.add(item_url)
        deduped.append(item)
        new_items_by_source[item.source] = new_items_by_source.get(item.source, 0) + 1
    return deduped


def _write_or_preserve_digest(
    research_dir: Path,
    digest_date: date,
    digest_entries: list[tuple[RawResearchItem, ResearchScore]],
) -> Path:
    path = research_dir / f"digest-{digest_date.isoformat()}.md"
    if not digest_entries and path.exists():
        return path
    return write_digest(digest_entries, research_dir=research_dir, digest_date=digest_date)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_products(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "config" / "products.yaml"
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}
