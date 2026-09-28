"""API tests for capture suggest → preview → confirm loop."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from holus.api.app import create_app
from holus.integrations.holus_social_api.containment import PERSONAL_DELIVERY_GRANT_ENV

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    queue = tmp_path / "content-queue"
    queue.mkdir()
    monkeypatch.setattr("holus.api.routes.content.CONTENT_QUEUE_DIR", queue)
    monkeypatch.delenv(PERSONAL_DELIVERY_GRANT_ENV, raising=False)
    test_client = TestClient(create_app())
    test_client._holus_queue = queue  # type: ignore[attr-defined]
    return test_client


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


@pytest.mark.parametrize(
    ("filename", "content_type", "expected_kind"),
    [
        ("diagram.png", "image/png", "image"),
        ("brief.pdf", "application/pdf", "pdf"),
    ],
)
def test_capture_suggest_accepts_supported_attachment_metadata(
    client: TestClient,
    filename: str,
    content_type: str,
    expected_kind: str,
) -> None:
    with patch(
        "holus.api.routes.capture._probe_social_connections",
        new=AsyncMock(return_value=(False, [])),
    ):
        response = client.post(
            "/api/v1/capture/suggest",
            json={
                "text": "A useful takeaway from this artifact.",
                "attachment_filename": filename,
                "attachment_content_type": content_type,
            },
        )
    assert response.status_code == 200
    assert response.json()["attachment_kind"] == expected_kind
    assert response.json()["suggestions"]


def test_capture_suggest_rejects_unsupported_attachment(client: TestClient) -> None:
    response = client.post(
        "/api/v1/capture/suggest",
        json={"text": "Keep the note, reject the binary.", "attachment_filename": "data.zip"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported attachment"


def test_capture_suggest_rejects_malformed_empty_request(client: TestClient) -> None:
    response = client.post("/api/v1/capture/suggest", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Provide text and/or an attachment"


def test_capture_suggest_retries_as_contained_when_social_api_fails(client: TestClient) -> None:
    with patch(
        "holus.api.routes.capture.HolusSocialAPIClient.health",
        new=AsyncMock(side_effect=RuntimeError("temporary outage")),
    ):
        response = client.post(
            "/api/v1/capture/suggest",
            json={"text": "Retry later if the social boundary is unavailable."},
        )
    assert response.status_code == 200
    assert response.json()["social_api_reachable"] is False


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
    assert all(
        result["status"] in {"contained", "approved", "published"} for result in body["results"]
    )

    # A retry is idempotent: it reconciles the same local intent rather than
    # creating another delivery attempt. This is the background-safe dry-run
    # contract for the capture -> approval -> queue -> publish lifecycle.
    retry = client.post(
        "/api/v1/capture/confirm",
        json={"piece_ids": piece_ids, "dry_run": False},
    )
    assert retry.status_code == 200
    assert [result["status"] for result in retry.json()["results"]] == ["contained"] * len(
        piece_ids
    )

    queue_dir = client._holus_queue  # type: ignore[attr-defined]
    outbox_files = list((queue_dir.parent / "lineage" / "outbox").glob("*.json"))
    assert len(outbox_files) == len(piece_ids)
    outbox_records = [json.loads(path.read_text(encoding="utf-8")) for path in outbox_files]
    assert {record["status"] for record in outbox_records} == {"contained"}
    assert all(record["external_id"] is None for record in outbox_records)
