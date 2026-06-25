from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from holus.research.candidates import CandidateStore
from holus.research.models import RawResearchItem, ResearchScore
from holus.research.radar import load_config, record_outcome, run_radar


class StubAdapter:
    def __init__(self, source: str, items: list[RawResearchItem] | None = None) -> None:
        self.source = source
        self.items = items or []
        self.calls = 0

    async def fetch(self, _window_days: int) -> list[RawResearchItem]:
        self.calls += 1
        return self.items


class FailingAdapter:
    source = "rss"

    async def fetch(self, _window_days: int) -> list[RawResearchItem]:
        raise RuntimeError("feed down")


def _write_config(root: Path) -> None:
    (root / "config").mkdir()
    (root / "config" / "research.yaml").write_text(
        yaml.safe_dump(
            {
                "window_days": 7,
                "thresholds": {"digest": 0.5, "candidate": 0.65},
                "paths": {
                    "research_dir": "data/research",
                    "candidates_dir": "data/research/candidates",
                    "seen_store": "data/research/seen.jsonl",
                    "interests": "config/research-interests.md",
                },
                "sources": {
                    "arxiv": {"categories": ["cs.AI"], "max_results": 10},
                    "hackernews": {"query": "ai", "max_results": 10},
                    "rss": {"feeds": ["https://example.com/feed"], "per_feed_limit": 10},
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "config" / "research-interests.md").write_text("agent reliability", encoding="utf-8")
    (root / "config" / "products.yaml").write_text("products: {}\n", encoding="utf-8")


def _item(
    source: str,
    source_id: str,
    url: str,
    *,
    item_id: str | None = None,
) -> RawResearchItem:
    return RawResearchItem(
        source=source,  # type: ignore[arg-type]
        source_id=source_id,
        item_id=item_id or f"{source}-{source_id}",
        title=f"{source} title",
        url=url,
        summary="A new AI agent paper for production video and image workflows.",
        published_at=datetime(2026, 6, 25, tzinfo=UTC),
    )


def _candidate_score(
    item: RawResearchItem, _interests: str, _products: dict[str, Any]
) -> ResearchScore:
    return ResearchScore(
        item_id=item.item_id,
        relevance=0.9,
        novelty=0.8,
        should_read=0.85,
        matched_products=["genpeli"],
        topics=["agents"],
        why_it_matters="It maps a current research result to production content workflows.",
        key_idea="AI agents can improve production workflows.",
        recommended_action="candidate",
    )


@pytest.mark.asyncio
async def test_run_radar_dedupes_seen_items_and_preserves_same_day_digest(tmp_path: Path) -> None:
    _write_config(tmp_path)
    item = _item("arxiv", "2401.1", "https://arxiv.org/abs/2401.1")
    adapter = StubAdapter("arxiv", [item])

    first = await run_radar(
        repo_root=tmp_path,
        source_adapters=[adapter],
        scorer=_candidate_score,
        run_date=date(2026, 6, 25),
    )
    digest_path = Path(first.digest_path or "")
    first_digest = digest_path.read_text(encoding="utf-8")
    second = await run_radar(
        repo_root=tmp_path,
        source_adapters=[adapter],
        scorer=_candidate_score,
        run_date=date(2026, 6, 25),
    )

    assert first.scored == 1
    assert first.candidates_created == 1
    assert second.scored == 0
    assert second.candidates_created == 0
    assert digest_path.read_text(encoding="utf-8") == first_digest


@pytest.mark.asyncio
async def test_run_radar_cross_source_dedupes_by_canonical_url(tmp_path: Path) -> None:
    _write_config(tmp_path)
    arxiv_item = _item("arxiv", "2401.1", "https://example.com/paper")
    hn_item = _item("hackernews", "42", "https://example.com/paper/")

    report = await run_radar(
        repo_root=tmp_path,
        source_adapters=[StubAdapter("hackernews", [hn_item]), StubAdapter("arxiv", [arxiv_item])],
        scorer=_candidate_score,
        run_date=date(2026, 6, 25),
    )

    candidates = list((tmp_path / "data" / "research" / "candidates").glob("*.yaml"))
    assert report.scored == 1
    assert len(candidates) == 1
    assert yaml.safe_load(candidates[0].read_text(encoding="utf-8"))["item"]["source"] == "arxiv"


@pytest.mark.asyncio
async def test_run_radar_continues_when_one_source_fails(tmp_path: Path) -> None:
    _write_config(tmp_path)
    item = _item("arxiv", "2401.1", "https://arxiv.org/abs/2401.1")

    report = await run_radar(
        repo_root=tmp_path,
        source_adapters=[FailingAdapter(), StubAdapter("arxiv", [item])],
        scorer=_candidate_score,
        run_date=date(2026, 6, 25),
    )

    failed = next(source for source in report.sources if source.source == "rss")
    assert failed.status == "failed"
    assert failed.error == "feed down"
    assert report.scored == 1


def test_candidate_store_reject_and_outcome_hook(tmp_path: Path) -> None:
    _write_config(tmp_path)
    item = _item("arxiv", "2401.1", "https://arxiv.org/abs/2401.1")
    score = _candidate_score(item, "", {})
    store = CandidateStore(tmp_path / "data" / "research" / "candidates")
    store.create(item, score)

    rejected = store.reject(item.item_id)
    trajectory = record_outcome(
        item.item_id,
        {"engagement_rate": 0.1},
        trajectory_path=tmp_path / ".self-improvement" / "memory" / "trajectory.jsonl",
    )

    assert rejected.status == "rejected"
    assert "record_research_outcome" in trajectory.read_text(encoding="utf-8")


def test_repo_config_loads() -> None:
    config = load_config(Path.cwd())
    assert config.digest_threshold == 0.5
    assert config.candidate_threshold == 0.65
    assert config.arxiv_categories
    assert config.rss_feeds
