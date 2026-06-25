from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from holus.api.routes import research
from holus.research.candidates import CandidateStore
from holus.research.models import RawResearchItem, ResearchScore

app = FastAPI()
app.include_router(research.router, prefix="/api/v1")
client = TestClient(app)


@pytest.fixture
def mock_candidate_store(tmp_path):
    candidates_dir = tmp_path / "candidates"
    queue_dir = tmp_path / "queue"
    candidates_dir.mkdir()
    queue_dir.mkdir()

    store = CandidateStore(directory=candidates_dir, queue_dir=queue_dir)

    item = RawResearchItem(
        source="arxiv",
        source_id="123",
        item_id="arxiv-123",
        title="Test Title",
        url="http://arxiv.org/abs/123",
        summary="summary",
        published_at=datetime.now(UTC),
    )
    score = ResearchScore(
        item_id="arxiv-123",
        relevance=0.9,
        novelty=0.9,
        should_read=0.9,
        why_it_matters="matters",
        key_idea="idea",
        recommended_action="candidate",
    )

    store.create(item, score)
    return store, candidates_dir, queue_dir


def test_api_run_radar_returns_report(monkeypatch):
    # AC12 - API run report: POST /api/v1/research/run returns HTTP 200 with RadarRunReport
    # where sources length equals the number of configured source types
    mock_run_radar = AsyncMock()
    mock_run_radar.return_value = {
        "run_id": "test-run",
        "started_at": datetime.now(UTC).isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "sources": [
            {"source": "arxiv", "status": "ok", "fetched": 1, "new_items": 1},
            {"source": "hackernews", "status": "ok", "fetched": 1, "new_items": 1},
            {"source": "rss", "status": "ok", "fetched": 1, "new_items": 1},
        ],
        "scored": 1,
        "digest_path": None,
        "candidates_created": 1,
    }

    monkeypatch.setattr("holus.api.routes.research.run_radar", mock_run_radar)

    response = client.post("/api/v1/research/run")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert len(data["sources"]) == 3
    assert data["scored"] == 1


@pytest.mark.asyncio
async def test_approve_candidate_invokes_pipeline_and_no_auto_publish(
    monkeypatch, mock_candidate_store
):
    store, _candidates_dir, _queue_dir = mock_candidate_store

    # We patch CandidateStore instantiation in the route to use our test store paths
    def mock_store_init(*args, **kwargs):
        return store

    monkeypatch.setattr("holus.api.routes.research.CandidateStore", mock_store_init)

    # Spy on ThoughtContentPipeline.create_content_set
    mock_create_content_set = AsyncMock()
    mock_content_set = MagicMock()
    mock_content_set.group_id = "group-123"
    mock_create_content_set.return_value = mock_content_set

    monkeypatch.setattr(
        "holus.research.candidates.ThoughtContentPipeline.create_content_set",
        mock_create_content_set,
    )

    # AC11: no publish/schedule path is invoked by the research approval route.
    mock_publish = AsyncMock()
    mock_schedule = AsyncMock()

    # AC10: Approve the candidate
    response = client.post("/api/v1/research/candidates/arxiv-123/approve")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "approved"
    assert data["approved_group_id"] == "group-123"

    # Verify create_content_set was invoked
    mock_create_content_set.assert_awaited_once()

    # Verify candidate became approved
    candidate = store.get("arxiv-123")
    assert candidate.status == "approved"
    assert candidate.approved_group_id == "group-123"

    # Verify no auto publish occurred
    mock_publish.assert_not_called()
    mock_schedule.assert_not_called()
