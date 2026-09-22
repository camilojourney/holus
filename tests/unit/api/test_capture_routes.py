"""API tests for capture suggest → preview → confirm loop."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from holus.api.app import create_app
from holus.integrations.holus_social_api.containment import PERSONAL_DELIVERY_GRANT_ENV


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    queue = tmp_path / "content-queue"
    queue.mkdir()
    monkeypatch.setattr("holus.api.routes.content.CONTENT_QUEUE_DIR", queue)
    monkeypatch.delenv(PERSONAL_DELIVERY_GRANT_ENV, raising=False)
    return TestClient(create_app())


def test_capture_suggest_returns_routes(client: TestClient) -> None:
    with patch(
        "holus.api.routes.capture._probe_social_connections",
        new=AsyncMock(return_value=(False, [])),
    ):
        response = client.post(
            "/api/v1/capture/suggest",
            json={"text": "The best systems start with a sharp content loop."},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["attachment_kind"] == "none"
    assert body["suggestions"]
    assert body["personal_delivery_granted"] is False


def test_capture_preview_and_confirm_contained(client: TestClient) -> None:
    with patch(
        "holus.api.routes.capture._probe_social_connections",
        new=AsyncMock(return_value=(False, [])),
    ):
        suggest = client.post(
            "/api/v1/capture/suggest",
            json={"text": "Ship one reliable capture loop before adding sync."},
        )
    assert suggest.status_code == 200
    channels = [item["channel"] for item in suggest.json()["suggestions"][:2]]
    assert channels

    preview = client.post(
        "/api/v1/capture/preview",
        json={
            "text": "Ship one reliable capture loop before adding sync.",
            "channels": channels,
        },
    )
    assert preview.status_code == 200
    piece_ids = [item["id"] for item in preview.json()["items"]]
    assert piece_ids

    confirm = client.post(
        "/api/v1/capture/confirm",
        json={"piece_ids": piece_ids, "dry_run": False},
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["personal_delivery_granted"] is False
    assert body["results"]
    assert all(result["status"] in {"contained", "approved", "published"} for result in body["results"])
