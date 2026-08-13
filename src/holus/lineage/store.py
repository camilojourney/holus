"""Concurrency-safe JSONL owner for the Holus lineage contract."""

from __future__ import annotations

import fcntl
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from holus.lineage.models import SCHEMA_VERSION, LineageEdge, LineageNode, stable_hash


@dataclass(frozen=True)
class ValidationReport:
    """Consistency diagnostics; ``complete`` is never inferred from partial data."""

    valid: bool
    complete: bool
    node_count: int
    edge_count: int
    counts_by_type: dict[str, int]
    counts_by_status: dict[str, int]
    orphan_node_ids: list[str]
    broken_edge_ids: list[str]
    malformed_lines: list[int]
    newest_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "valid": self.valid,
            "complete": self.complete,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "counts_by_type": self.counts_by_type,
            "counts_by_status": self.counts_by_status,
            "orphan_node_ids": self.orphan_node_ids,
            "broken_edge_ids": self.broken_edge_ids,
            "malformed_lines": self.malformed_lines,
            "newest_at": self.newest_at,
        }


class LineageStore:
    """Append-only node/edge store with process locks and idempotent IDs.

    The sole durable format is ``events.jsonl``. Every line is a self-contained,
    versioned event. A write is fsynced under an advisory lock; a failed lineage
    write therefore cannot alter a content artifact written by another owner.
    """

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.path = self.directory / "events.jsonl"
        self.lock_path = self.directory / ".lineage.lock"

    def record(self, node: LineageNode, edges: list[LineageEdge] | None = None) -> bool:
        """Append a node event once; return false when its deterministic event exists."""
        return self.record_batch([(node, edges or [])]) > 0

    def record_batch(self, entries: list[tuple[LineageNode, list[LineageEdge]]]) -> int:
        """Append a group of events under one writer lock."""
        if not entries:
            return 0
        recorded = 0
        existing_ids: set[str] = set()
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            with self.path.open("a+", encoding="utf-8") as handle:
                handle.seek(0)
                existing = [self._decode(line) for line in handle if line.strip()]
                events = [event for event in existing if event is not None]
                existing_ids = {str(event.get("event_id")) for event in events}
                previous = events[-1] if events else None
                pending: list[str] = []
                for node, edge_list in entries:
                    event_id = stable_hash(
                        {
                            "node": node.model_dump(mode="json"),
                            "edges": [edge.model_dump(mode="json") for edge in edge_list],
                        }
                    )
                    if event_id in existing_ids:
                        continue
                    event = {
                        "schema_version": SCHEMA_VERSION,
                        "event_id": event_id,
                        "seq": int(previous.get("seq", len(events))) + 1 if previous else 1,
                        "recorded_at": datetime.now(UTC).isoformat(),
                        "node": node.model_dump(mode="json"),
                        "edges": [edge.model_dump(mode="json") for edge in edge_list],
                        "prev_event_hash": previous.get("event_hash") if previous else None,
                    }
                    event["event_hash"] = stable_hash(event)
                    pending.append(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
                    existing_ids.add(event_id)
                    previous = event
                    recorded += 1
                if pending:
                    handle.seek(0, os.SEEK_END)
                    handle.write("".join(pending))
                    handle.flush()
                    os.fsync(handle.fileno())
                return recorded
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def events(self) -> tuple[list[dict[str, Any]], list[int]]:
        """Return valid raw events and malformed line numbers without raising."""
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            try:
                if not self.path.exists():
                    return [], []
                events: list[dict[str, Any]] = []
                malformed: list[int] = []
                for line_number, line in enumerate(
                    self.path.read_text(encoding="utf-8").splitlines(), 1
                ):
                    if not line.strip():
                        continue
                    event = self._decode(line)
                    if event is None:
                        malformed.append(line_number)
                    else:
                        events.append(event)
                return events, malformed
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def manifest(self, *, cursor: int = 0, limit: int = 500) -> dict[str, Any]:
        """Return deterministic, cursor-paged JSON suitable for a read-only consumer."""
        if cursor < 0 or limit < 1:
            raise ValueError("cursor must be >= 0 and limit must be >= 1")
        events, malformed = self.events()
        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[str, dict[str, Any]] = {}
        for event in events:
            node = event.get("node")
            if isinstance(node, dict) and isinstance(node.get("node_id"), str):
                nodes[node["node_id"]] = node
            for edge in event.get("edges", []):
                if isinstance(edge, dict) and isinstance(edge.get("edge_id"), str):
                    edges[edge["edge_id"]] = edge
        ordered_nodes = [nodes[key] for key in sorted(nodes)]
        page = ordered_nodes[cursor : cursor + limit]
        page_ids = {node["node_id"] for node in page}
        page_edges = [
            edge
            for _, edge in sorted(edges.items())
            if edge["from_node_id"] in page_ids or edge["to_node_id"] in page_ids
        ]
        next_cursor = cursor + len(page)
        return {
            "schema_version": SCHEMA_VERSION,
            "cursor": cursor,
            "next_cursor": next_cursor if next_cursor < len(ordered_nodes) else None,
            "nodes": page,
            "edges": page_edges,
            "diagnostics": {"malformed_lines": malformed},
        }

    def export(self, *, after_seq: int = 0, limit: int = 1000) -> dict[str, Any]:
        """Export a validated, sequence-cursored snapshot for external consumers."""
        if after_seq < 0 or limit < 1:
            raise ValueError("after_seq must be >= 0 and limit must be >= 1")
        report = self.validate()
        if not report.valid:
            raise ValueError("LINEAGE_INVALID")
        events, _ = self.events()
        selected = [event for event in events if int(event["seq"]) > after_seq][:limit]
        snapshot_seq = int(events[-1]["seq"]) if events else 0
        next_after_seq = (
            int(selected[-1]["seq"])
            if selected and int(selected[-1]["seq"]) < snapshot_seq
            else None
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "snapshot_seq": snapshot_seq,
            "next_after_seq": next_after_seq,
            "ledger_hash": events[-1].get("event_hash") if events else None,
            "validation": report.to_dict(),
            "records": selected,
        }

    def validate(self) -> ValidationReport:
        """Report malformed, orphaned, and broken lineage without claiming completeness."""
        events, malformed = self.events()
        nodes: dict[str, LineageNode] = {}
        edges: dict[str, LineageEdge] = {}
        invalid = bool(malformed)
        previous_hash: str | None = None
        for expected_seq, event in enumerate(events, 1):
            recorded_hash = event.get("event_hash")
            hash_input = {key: value for key, value in event.items() if key != "event_hash"}
            if (
                event.get("seq") != expected_seq
                or event.get("prev_event_hash") != previous_hash
                or recorded_hash != stable_hash(hash_input)
            ):
                invalid = True
            previous_hash = recorded_hash if isinstance(recorded_hash, str) else None
        for event in events:
            try:
                node = LineageNode.model_validate(event["node"])
                nodes[node.node_id] = node
                for raw_edge in event.get("edges", []):
                    edge = LineageEdge.model_validate(raw_edge)
                    edges[edge.edge_id] = edge
            except (KeyError, ValueError, TypeError):
                invalid = True
        broken = sorted(
            edge_id
            for edge_id, edge in edges.items()
            if edge.from_node_id not in nodes or edge.to_node_id not in nodes
        )
        connected = {
            node_id
            for edge in edges.values()
            if edge.from_node_id in nodes and edge.to_node_id in nodes
            for node_id in (edge.from_node_id, edge.to_node_id)
        }
        # A source may intentionally be the root. Every non-source must be connected.
        orphans = sorted(
            node_id
            for node_id, node in nodes.items()
            if node.artifact_type.value not in {"source_thought", "research_candidate"}
            and node_id not in connected
        )
        counts_by_type: dict[str, int] = {}
        counts_by_status: dict[str, int] = {}
        for node in nodes.values():
            counts_by_type[node.artifact_type.value] = (
                counts_by_type.get(node.artifact_type.value, 0) + 1
            )
            counts_by_status[node.status] = counts_by_status.get(node.status, 0) + 1
        timestamps = [node.created_at for node in nodes.values()]
        newest = max(timestamps).isoformat() if timestamps else None
        valid = not invalid and not broken
        # "Complete" is deliberately conservative: a source-rooted content run
        # needs its plan and at least one persisted variant. Optional stages
        # (visual, review, publish) are not invented when they did not run.
        source_runs = {
            node.correlation_id
            for node in nodes.values()
            if node.artifact_type.value == "source_thought"
        }
        complete_runs = all(
            {"content_set", "content_variant"}.issubset(
                {
                    node.artifact_type.value
                    for node in nodes.values()
                    if node.correlation_id == run_id
                }
            )
            for run_id in source_runs
        )
        complete = valid and bool(source_runs) and complete_runs and not orphans
        return ValidationReport(
            valid=valid,
            complete=complete,
            node_count=len(nodes),
            edge_count=len(edges),
            counts_by_type=counts_by_type,
            counts_by_status=counts_by_status,
            orphan_node_ids=orphans,
            broken_edge_ids=broken,
            malformed_lines=malformed,
            newest_at=newest,
        )

    @staticmethod
    def _decode(line: str) -> dict[str, Any] | None:
        try:
            raw = json.loads(line)
            return (
                raw
                if isinstance(raw, dict)
                and isinstance(raw.get("schema_version"), str)
                and raw["schema_version"] == SCHEMA_VERSION
                else None
            )
        except json.JSONDecodeError:
            return None
