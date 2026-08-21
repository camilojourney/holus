"""Contract tests for the Holus-owned lineage JSONL boundary."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from holus.lineage.models import ArtifactType, LineageEdge, LineageNode, stable_edge_id, stable_hash
from holus.lineage.store import LineageStore


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 8, 12, tzinfo=UTC)


def _node(node_id: str, kind: ArtifactType, timestamp: datetime) -> LineageNode:
    return LineageNode(
        node_id=node_id,
        artifact_type=kind,
        artifact_id=node_id,
        producer="test",
        created_at=timestamp,
        run_id="run-1",
        correlation_id="run-1",
        status="generated",
    )


def test_contract_stable_ids_hashes_and_redacts_metadata(timestamp: datetime) -> None:
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})
    assert stable_edge_id("a", "b", "derived_from") == stable_edge_id("a", "b", "derived_from")
    raw = _node("source:1", ArtifactType.SOURCE_THOUGHT, timestamp).model_dump()
    raw["metadata"] = {"api_key": "nope", "note": "Bearer private-token", "safe": "only this"}
    node = LineageNode(**raw)
    assert node.metadata == {"safe": "only this"}
    with pytest.raises(ValueError, match="relative"):
        LineageNode(
            **(
                _node("x", ArtifactType.CONTENT_VARIANT, timestamp).model_dump()
                | {"artifact_ref": "/tmp/x"}
            )
        )


def test_duplicate_and_concurrent_writes_are_idempotent(
    tmp_path: Path, timestamp: datetime
) -> None:
    store = LineageStore(tmp_path)
    node = _node("source:1", ArtifactType.SOURCE_THOUGHT, timestamp)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: store.record(node), range(16)))
    assert sum(results) == 1
    assert store.validate().node_count == 1


def test_manifest_is_deterministic_and_traverses_parent_child(
    tmp_path: Path, timestamp: datetime
) -> None:
    store = LineageStore(tmp_path)
    source = _node("source:1", ArtifactType.SOURCE_THOUGHT, timestamp)
    content_set = _node("content-set:1", ArtifactType.CONTENT_SET, timestamp)
    variant = _node("content:1", ArtifactType.CONTENT_VARIANT, timestamp)
    source_edge = LineageEdge(
        edge_id=stable_edge_id(source.node_id, content_set.node_id, "planned_into"),
        from_node_id=source.node_id,
        to_node_id=content_set.node_id,
        relation="planned_into",
        created_at=timestamp,
        run_id="run-1",
    )
    variant_edge = LineageEdge(
        edge_id=stable_edge_id(content_set.node_id, variant.node_id, "contains"),
        from_node_id=content_set.node_id,
        to_node_id=variant.node_id,
        relation="contains",
        created_at=timestamp,
        run_id="run-1",
    )
    store.record(source, [source_edge])
    store.record(content_set, [variant_edge])
    store.record(variant)
    first = store.manifest()
    second = store.manifest()
    assert first == second
    assert [node["node_id"] for node in first["nodes"]] == [
        "content-set:1",
        "content:1",
        "source:1",
    ]
    assert {edge["from_node_id"] for edge in first["edges"]} == {"source:1", "content-set:1"}
    report = store.validate()
    assert report.valid is True
    assert report.complete is True


def test_validator_rejects_tampered_event_chain(tmp_path: Path, timestamp: datetime) -> None:
    store = LineageStore(tmp_path)
    store.record(_node("source:1", ArtifactType.SOURCE_THOUGHT, timestamp))
    event = json.loads(store.path.read_text(encoding="utf-8"))
    event["event_hash"] = "tampered"
    store.path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    report = store.validate()

    assert report.valid is False
    assert report.complete is False
    assert report.malformed_lines == []
    assert report.node_count == 1


def test_validator_reports_orphans_broken_and_malformed_old_versions(
    tmp_path: Path, timestamp: datetime
) -> None:
    store = LineageStore(tmp_path)
    orphan = _node("content:orphan", ArtifactType.CONTENT_VARIANT, timestamp)
    broken = LineageEdge(
        edge_id="edge-broken",
        from_node_id="source:missing",
        to_node_id=orphan.node_id,
        relation="derived_from",
        created_at=timestamp,
        run_id="run-1",
    )
    store.record(orphan, [broken])
    with store.path.open("a", encoding="utf-8") as handle:
        handle.write('{"schema_version":"0.9"}\n')
        handle.write("not-json\n")
    report = store.validate()
    assert report.valid is False
    assert report.complete is False
    assert report.orphan_node_ids == ["content:orphan"]
    assert report.broken_edge_ids == ["edge-broken"]
    assert report.malformed_lines == [2, 3]
