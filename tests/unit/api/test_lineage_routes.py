"""Read-only API boundary tests for external lineage consumers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from pathlib import Path

from holus.api.app import create_app
from holus.lineage.models import ArtifactType, LineageNode
from holus.lineage.store import LineageStore


def test_lineage_api_is_read_only_and_exports_manifest(tmp_path: Path, monkeypatch) -> None:
    import holus.api.routes.lineage as route

    lineage_dir = tmp_path / "lineage"
    monkeypatch.setattr(route, "LINEAGE_DIR", lineage_dir)
    LineageStore(lineage_dir).record(
        LineageNode(
            node_id="source:api",
            artifact_type=ArtifactType.SOURCE_THOUGHT,
            artifact_id="api",
            producer="test",
            created_at=datetime(2026, 8, 12, tzinfo=UTC),
            run_id="api",
            correlation_id="api",
            status="normalized",
        )
    )
    client = TestClient(create_app())
    manifest = client.get("/api/v1/lineage/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["schema_version"] == "1.0"
    assert manifest.json()["nodes"][0]["node_id"] == "source:api"
    exported = client.get("/api/v1/lineage/export?after_seq=0&limit=10")
    assert exported.status_code == 200
    assert exported.json()["records"][0]["seq"] == 1
    assert client.get("/api/v1/lineage/validate").json()["complete"] is False
    assert client.post("/api/v1/lineage/manifest").status_code == 405
