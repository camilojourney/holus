from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from holus.api.routes import research
from holus.research.candidates import CandidateStore
from holus.research.models import RadarRunReport, RawResearchItem, ResearchScore


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(research.router, prefix="/api/v1")
    return TestClient(app)


def _item() -> RawResearchItem:
    return RawResearchItem(
        source="arxiv",
        source_id="2401.1",
        item_id="candidate-1",
        title="AI agents for video workflows",
        url="https://example.com/paper",
        summary="A useful AI agents paper.",
        published_at=datetime(2026, 6, 25, tzinfo=UTC),
    )


def _score() -> ResearchScore:
    return ResearchScore(
        item_id="candidate-1",
        relevance=0.9,
        novelty=0.8,
        should_read=0.9,
        matched_products=["genpeli"],
        topics=["agents"],
        why_it_matters="It connects research to production video workflows.",
        key_idea="Agents can coordinate video workflows.",
        recommended_action="candidate",
    )


@dataclass
class FakeContentSet:
    group_id: str


class FakePipeline:
    calls = 0

    def __init__(self, *, queue_dir: Path | str) -> None:
        self.queue_dir = Path(queue_dir)

    async def create_content_set(
        self,
        *,
        thought: str,
        channels: list[str],
        source_type: str | None = None,
        source_url: str | None = None,
    ) -> FakeContentSet:
        FakePipeline.calls += 1
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        (self.queue_dir / "approved.yaml").write_text(
            yaml.safe_dump(
                {
                    "piece_id": "approved",
                    "group_id": "group-1",
                    "status": "pending_review",
                    "thought": thought,
                    "channels": channels,
                    "source_type": source_type,
                    "source_url": source_url,
                }
            ),
            encoding="utf-8",
        )
        return FakeContentSet(group_id="group-1")


def test_research_run_route_returns_report(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_radar(**_kwargs: Any) -> RadarRunReport:
        return RadarRunReport(
            run_id="run-1",
            started_at=datetime(2026, 6, 25, tzinfo=UTC),
            finished_at=datetime(2026, 6, 25, tzinfo=UTC),
            sources=[
                {"source": "arxiv", "status": "ok", "fetched": 1, "new_items": 1},
                {"source": "hackernews", "status": "ok", "fetched": 1, "new_items": 1},
                {"source": "rss", "status": "ok", "fetched": 1, "new_items": 1},
            ],
            scored=3,
            digest_path="/tmp/digest.md",
            candidates_created=1,
        )

    monkeypatch.setattr("holus.api.routes.research.run_radar", fake_run_radar)
    response = client.post("/api/v1/research/run")

    assert response.status_code == 200
    assert len(response.json()["sources"]) == 3


def test_digest_route_returns_latest_digest(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    research_dir = tmp_path / "data" / "research"
    research_dir.mkdir(parents=True)
    (research_dir / "digest-2026-06-25.md").write_text("# Digest\n", encoding="utf-8")
    monkeypatch.setattr("holus.api.routes.research.RESEARCH_DIR", research_dir)

    response = client.get("/api/v1/research/digest")

    assert response.status_code == 200
    assert response.json()["markdown"] == "# Digest\n"


def test_approve_candidate_reuses_thought_pipeline_without_publish(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_dir = tmp_path / "data" / "research" / "candidates"
    queue_dir = tmp_path / "data" / "content-queue"
    store = CandidateStore(candidate_dir, queue_dir=queue_dir)
    store.create(_item(), _score())
    FakePipeline.calls = 0
    monkeypatch.setattr("holus.api.routes.research.CANDIDATES_DIR", candidate_dir)
    monkeypatch.setattr("holus.api.routes.research.CONTENT_QUEUE_DIR", queue_dir)
    monkeypatch.setattr("holus.research.candidates.ThoughtContentPipeline", FakePipeline)
    response = client.post("/api/v1/research/candidates/candidate-1/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["approved_group_id"] == "group-1"
    assert FakePipeline.calls == 1
    assert (
        yaml.safe_load((queue_dir / "approved.yaml").read_text(encoding="utf-8"))["status"]
        == "pending_review"
    )


def test_reject_candidate_route(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_dir = tmp_path / "data" / "research" / "candidates"
    store = CandidateStore(candidate_dir)
    store.create(_item(), _score())
    monkeypatch.setattr("holus.api.routes.research.CANDIDATES_DIR", candidate_dir)

    response = client.post("/api/v1/research/candidates/candidate-1/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
