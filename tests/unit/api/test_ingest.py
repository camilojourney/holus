"""Tests for universal ingest endpoint (SPEC-035 extension)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from holus.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_ingest_text(client: TestClient, tmp_path: Path) -> None:
    with patch("holus.api.routes.ingest._PENDING_PATH", tmp_path / "pending.json"):
        resp = client.post(
            "/api/holus/ingest", data={"text": "I built a voice pipeline for LinkedIn"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["input_type"] == "text"
    assert "voice pipeline" in data["extracted_text"]
    assert data["post_id"]


def test_ingest_no_input(client: TestClient) -> None:
    resp = client.post("/api/holus/ingest")
    assert resp.status_code == 422


def test_ingest_url(client: TestClient, tmp_path: Path) -> None:
    mock_html = "<html><body><p>AI agents are the future of software.</p></body></html>"
    with (
        patch("holus.api.routes.ingest._PENDING_PATH", tmp_path / "pending.json"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_resp = AsyncMock()
        mock_resp.text = mock_html
        mock_resp.raise_for_status = lambda: None
        mock_get.return_value = mock_resp

        resp = client.post("/api/holus/ingest", data={"url": "https://example.com/article"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["input_type"] == "url"
    assert "AI agents" in data["extracted_text"]


def test_ingest_audio_empty_transcript(client: TestClient, tmp_path: Path) -> None:
    """Audio with empty Whisper transcript raises 500."""
    with (
        patch("holus.api.routes.ingest._PENDING_PATH", tmp_path / "pending.json"),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
    ):
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {"transcript": ""}
        mock_resp.raise_for_status = lambda: None
        mock_post.return_value = mock_resp

        resp = client.post(
            "/api/holus/ingest",
            files={"file": ("test.ogg", b"fake audio", "audio/ogg")},
        )
    # Empty transcript → 500 or 422
    assert resp.status_code in (500, 422)


def test_ingest_unsupported_file_type(client: TestClient) -> None:
    resp = client.post(
        "/api/holus/ingest",
        files={"file": ("doc.pdf", b"fake pdf", "application/pdf")},
    )
    assert resp.status_code == 415


def test_ingest_queues_to_pending(client: TestClient, tmp_path: Path) -> None:
    pending_path = tmp_path / "pending.json"
    with patch("holus.api.routes.ingest._PENDING_PATH", pending_path):
        client.post("/api/holus/ingest", data={"text": "Test idea for queuing"})

    assert pending_path.exists()
    data = json.loads(pending_path.read_text())
    entries = list(data.values())
    assert len(entries) == 1
    assert entries[0]["status"] == "pipeline_queued"
    assert entries[0]["input_type"] == "text"
    assert entries[0]["raw_text"] == "Test idea for queuing"
