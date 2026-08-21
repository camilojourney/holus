"""Research Radar orchestration."""

from __future__ import annotations

import asyncio
import fcntl
import json
import uuid
from collections.abc import Sequence  # noqa: TC003 - used in public runtime signature.
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from holus.research.candidates import CandidateStore
from holus.research.curator import (
    AsyncScoreCallable,
    ResearchCurator,
    ScoreCallable,
    default_agent_scorer,
)
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


@dataclass(frozen=True)
class _SourceFetchResult:
    items_by_source: dict[str, list[RawResearchItem]]
    errors: dict[str, str]


@dataclass(frozen=True)
class _ScoringResult:
    digest_entries: list[tuple[RawResearchItem, ResearchScore]]
    candidates_created: int
    scored: int
    failures: list[dict[str, Any]]


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
    async with _radar_lock(config.research_dir):
        return await _run_radar_unlocked(
            root=root,
            config=config,
            source_adapters=source_adapters,
            scorer=scorer,
            run_date=run_date,
        )


async def _run_radar_unlocked(
    *,
    root: Path,
    config: ResearchRadarConfig,
    source_adapters: Sequence[SourceAdapter] | None,
    scorer: ScoreCallable | AsyncScoreCallable | None,
    run_date: date | None,
) -> RadarRunReport:
    started_at = datetime.now(UTC)
    run_id = uuid.uuid4().hex
    digest_date = run_date or started_at.date()
    adapters = list(source_adapters) if source_adapters is not None else _default_adapters(config)
    seen_store = SeenStore(config.seen_path)
    candidate_store = CandidateStore(
        config.candidates_dir, queue_dir=root / "data" / "content-queue"
    )
    resolved_scorer = scorer if scorer is not None else default_agent_scorer(root)
    curator = ResearchCurator(
        interests=_read_text(config.interests_path),
        products=_read_products(root),
        scorer=resolved_scorer,
    )
    if scorer is None and resolved_scorer is not None:
        curator.scorer_mode = "agent-backed"

    fetched = await _fetch_sources(adapters, config.window_days)
    new_items_by_source: dict[str, int] = {adapter.source: 0 for adapter in adapters}
    new_items, dedupe_collisions = _dedupe_new_items(
        fetched.items_by_source,
        seen_store,
        new_items_by_source,
    )
    if dedupe_collisions:
        _append_jsonl(config.research_dir / "dedupe-collisions.jsonl", dedupe_collisions)

    scored = await _score_items(
        curator,
        new_items,
        config,
        run_id,
        candidate_store,
    )
    digest_path = _write_or_preserve_digest(
        config.research_dir,
        digest_date,
        run_id,
        scored.digest_entries,
    )
    if scored.failures:
        _append_jsonl(config.research_dir / "scoring-failures.jsonl", scored.failures)
    for item in new_items:
        seen_store.mark_seen(item)

    return RadarRunReport(
        run_id=run_id,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        sources=_source_results(adapters, fetched, new_items_by_source),
        scored=scored.scored,
        digest_path=str(digest_path) if digest_path else None,
        candidates_created=scored.candidates_created,
        scoring_failures=len(scored.failures),
        degraded=bool(fetched.errors or scored.failures or curator.fallback_count),
        failure_reasons=[
            *(f"{source}: {error}" for source, error in sorted(fetched.errors.items())),
            *(f"scoring:{failure['item_id']}: {failure['error']}" for failure in scored.failures),
            *(f"heuristic-fallback:{reason}" for reason in curator.fallback_reasons),
        ],
        dedupe_collisions=len(dedupe_collisions),
        scorer_mode=curator.scorer_mode,
        heuristic_fallbacks=curator.fallback_count,
    )


async def _fetch_adapter(
    adapter: SourceAdapter,
    window_days: int,
) -> tuple[str, list[RawResearchItem], str | None]:
    try:
        return adapter.source, await adapter.fetch(window_days), None
    except Exception as exc:
        return adapter.source, [], str(exc)


async def _fetch_sources(
    adapters: Sequence[SourceAdapter],
    window_days: int,
) -> _SourceFetchResult:
    fetch_results = await asyncio.gather(
        *(_fetch_adapter(adapter, window_days) for adapter in adapters)
    )
    items_by_source: dict[str, list[RawResearchItem]] = {}
    errors: dict[str, str] = {}
    for source, items, error in fetch_results:
        items_by_source[source] = items
        if error:
            errors[source] = error
    return _SourceFetchResult(items_by_source=items_by_source, errors=errors)


async def _score_items(
    curator: ResearchCurator,
    items: Sequence[RawResearchItem],
    config: ResearchRadarConfig,
    run_id: str,
    candidate_store: CandidateStore,
) -> _ScoringResult:
    digest_entries: list[tuple[RawResearchItem, ResearchScore]] = []
    candidates_created = 0
    scored = 0
    failures: list[dict[str, Any]] = []
    for item in items:
        try:
            score = await _score_with_retries(curator, item, attempts=2)
        except Exception as exc:
            failures.append(
                {
                    "run_id": run_id,
                    "item_id": item.item_id,
                    "source": item.source,
                    "source_id": item.source_id,
                    "url": str(item.url),
                    "failed_at": datetime.now(UTC).isoformat(),
                    "error": str(exc),
                    "policy": "terminal_skip_after_bounded_retries",
                }
            )
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
    return _ScoringResult(
        digest_entries=digest_entries,
        candidates_created=candidates_created,
        scored=scored,
        failures=failures,
    )


def _source_results(
    adapters: Sequence[SourceAdapter],
    fetched: _SourceFetchResult,
    new_items_by_source: dict[str, int],
) -> list[RadarSourceResult]:
    return [
        RadarSourceResult(
            source=adapter.source,
            status="failed" if adapter.source in fetched.errors else "ok",
            fetched=len(fetched.items_by_source.get(adapter.source, [])),
            new_items=new_items_by_source.get(adapter.source, 0),
            error=fetched.errors.get(adapter.source),
        )
        for adapter in adapters
    ]


@asynccontextmanager
async def _radar_lock(research_dir: Path) -> Any:
    research_dir.mkdir(parents=True, exist_ok=True)
    lock_path = research_dir / ".radar.lock"
    with lock_path.open("w", encoding="utf-8") as lock_file:
        await asyncio.to_thread(fcntl.flock, lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


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
) -> tuple[list[RawResearchItem], list[dict[str, Any]]]:
    all_items = [
        item
        for items in fetched_by_source.values()
        for item in items
        if not seen_store.has_seen(item)
    ]
    all_items.sort(key=lambda item: (SOURCE_PRIORITY.get(item.source, 99), str(item.published_at)))
    seen_urls: set[str] = set()
    canonical_owners: dict[str, RawResearchItem] = {}
    deduped: list[RawResearchItem] = []
    collisions: list[dict[str, Any]] = []
    for item in all_items:
        item_url = canonical_url(str(item.url))
        if item_url in seen_urls:
            owner = canonical_owners[item_url]
            collisions.append(
                {
                    "canonical_url": item_url,
                    "kept_item_id": owner.item_id,
                    "kept_source": owner.source,
                    "dropped_item_id": item.item_id,
                    "dropped_source": item.source,
                    "observed_at": datetime.now(UTC).isoformat(),
                }
            )
            continue
        seen_urls.add(item_url)
        canonical_owners[item_url] = item
        deduped.append(item)
        new_items_by_source[item.source] = new_items_by_source.get(item.source, 0) + 1
    return deduped, collisions


def _write_or_preserve_digest(
    research_dir: Path,
    digest_date: date,
    run_id: str,
    digest_entries: list[tuple[RawResearchItem, ResearchScore]],
) -> Path:
    if not digest_entries:
        latest = _latest_digest_for_date(research_dir, digest_date)
        if latest is not None:
            return latest
    return write_digest(
        digest_entries,
        research_dir=research_dir,
        digest_date=digest_date,
        run_id=run_id,
    )


def _latest_digest_for_date(research_dir: Path, digest_date: date) -> Path | None:
    candidates = list(research_dir.glob(f"digest-{digest_date.isoformat()}*.md"))
    return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None


async def _score_with_retries(
    curator: ResearchCurator,
    item: RawResearchItem,
    *,
    attempts: int,
) -> ResearchScore:
    last_error: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            return await curator.score(item)
        except Exception as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_products(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "config" / "products.yaml"
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}
