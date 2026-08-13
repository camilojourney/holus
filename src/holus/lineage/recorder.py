"""Small, best-effort emission facade for central Holus persistence boundaries."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from holus.lineage.models import ArtifactType, LineageEdge, LineageNode, stable_edge_id, stable_hash
from holus.lineage.store import LineageStore

logger = logging.getLogger(__name__)


class LineageRecorder:
    """Own lineage without making content generation depend on it succeeding."""

    def __init__(self, directory: Path | str) -> None:
        self.store = LineageStore(directory)

    def record_content_set(
        self, source: Any, records: list[dict[str, Any]], package: dict[str, Any]
    ) -> None:
        """Emit source, plan, generated variants, and rendered visual relationships."""
        if not records:
            return
        group_id = str(records[0]["group_id"])
        created_at = _recorded_at(records[0].get("generated_at"))
        source_id = f"source:{group_id}"
        set_id = f"content-set:{group_id}"
        source_node = LineageNode(
            node_id=source_id,
            artifact_type=ArtifactType.SOURCE_THOUGHT,
            artifact_id=group_id,
            producer="holus/thought-normalizer",
            created_at=created_at,
            run_id=group_id,
            correlation_id=group_id,
            status="normalized",
            content_hash=stable_hash(source.extracted_text),
            metadata={"source_type": source.source_type, "has_source_url": bool(source.source_url)},
        )
        set_node = LineageNode(
            node_id=set_id,
            artifact_type=ArtifactType.CONTENT_SET,
            artifact_id=group_id,
            producer="holus/thought-content-pipeline",
            created_at=created_at,
            run_id=group_id,
            correlation_id=group_id,
            status="generated",
            config_hash=stable_hash(package.get("channel_plan", [])),
            model_hash=stable_hash("holus/deterministic-thought-pipeline"),
            metadata={"variant_count": len(records), "stage": "strategy_and_generation"},
        )
        self._record_batch(
            [
                (source_node, [self._edge(source_id, set_id, "planned_into", group_id, created_at)]),
                (set_node, []),
            ]
        )
        for record in records:
            self.record_content_variant(record, parent_node_id=set_id)

    def record_generated_set(
        self,
        source_text: str,
        records: list[dict[str, Any]],
        *,
        group_id: str,
        package: dict[str, Any] | None = None,
    ) -> None:
        if not records:
            return
        source = SimpleNamespace(
            source_type="text",
            source_url=None,
            extracted_text=source_text,
        )
        normalized_records = [
            {**record, "group_id": str(record.get("group_id", group_id))}
            for record in records
        ]
        self.record_content_set(source, normalized_records, package or {})

    def record_content_variant(
        self, record: dict[str, Any], *, parent_node_id: str | None = None
    ) -> None:
        """Emit a persisted queue record and any referenced visual asset."""
        piece_id = str(record["piece_id"])
        group_id = str(record.get("group_id", piece_id))
        created_at = _recorded_at(record.get("generated_at"))
        node_id = f"content:{piece_id}"
        queue_ref = f"content-queue/{piece_id}.yaml"
        node = LineageNode(
            node_id=node_id,
            artifact_type=ArtifactType.CONTENT_VARIANT,
            artifact_id=piece_id,
            producer="holus/thought-content-pipeline",
            created_at=created_at,
            run_id=group_id,
            correlation_id=group_id,
            status=str(record.get("status", "generated")),
            artifact_ref=queue_ref,
            content_hash=stable_hash(record.get("text", "")),
            config_hash=stable_hash(
                {key: record.get(key) for key in ("platform", "content_type", "content_job_plan")}
            ),
            model_hash=stable_hash(str(record.get("model_used", "unknown"))),
            checksum=_sha256_path(self.store.directory.parent / queue_ref),
            metadata={
                "platform": str(record.get("platform", "unknown")),
                "content_type": str(record.get("content_type", "unknown")),
            },
        )
        edges = (
            [self._edge(parent_node_id, node_id, "contains", group_id, created_at)]
            if parent_node_id
            else []
        )
        self._record(node, edges)
        for field, asset_type in (("rendered_image_path", "image"), ("rendered_pdf_path", "pdf")):
            asset_path = record.get(field)
            if isinstance(asset_path, str) and asset_path:
                asset_name = Path(asset_path).name
                asset_id = f"visual:{piece_id}:{asset_type}"
                visual = LineageNode(
                    node_id=asset_id,
                    artifact_type=ArtifactType.VISUAL_ASSET,
                    artifact_id=asset_id.removeprefix("visual:"),
                    producer=str(
                        record.get("visual_spec", {}).get("renderer", "holus/visual-renderer")
                    ),
                    created_at=created_at,
                    run_id=group_id,
                    correlation_id=group_id,
                    status="generated",
                    artifact_ref=f"rendered-content/{asset_name}",
                    config_hash=stable_hash(record.get("visual_spec", {})),
                    checksum=_sha256_path(Path(asset_path)),
                    metadata={"format": asset_type},
                )
                self._record(
                    visual, [self._edge(node_id, asset_id, "rendered_as", group_id, created_at)]
                )

    def record_outcome(self, record: dict[str, Any], *, outcome: ArtifactType, status: str) -> None:
        """Record a review, publish, or schedule state without a write-side API."""
        piece_id = str(record["piece_id"])
        group_id = str(record.get("group_id", piece_id))
        occurred_at = _recorded_at(
            record.get("published_at")
            or record.get("scheduled_at")
            or record.get("lineage_updated_at")
        )
        node_id = f"{outcome.value}:{piece_id}:{status}"
        if outcome == ArtifactType.REVIEW_DECISION and record.get("review_decision_id"):
            node_id = str(record["review_decision_id"])
        if outcome == ArtifactType.PUBLICATION_REQUEST and record.get("dispatch_request_id"):
            node_id = f"publication-request:{record['dispatch_request_id']}"
        node = LineageNode(
            node_id=node_id,
            artifact_type=outcome,
            artifact_id=piece_id,
            producer="holus/content-api",
            created_at=occurred_at,
            run_id=group_id,
            correlation_id=group_id,
            status=status,
            metadata={"piece_id": piece_id},
        )
        parent_id = f"content:{piece_id}"
        edge = self._edge(parent_id, node_id, "resulted_in", group_id, occurred_at)
        if self.store.has_node(parent_id):
            self._record(node, [edge])
            return
        parent = LineageNode(
            node_id=parent_id,
            artifact_type=ArtifactType.CONTENT_VARIANT,
            artifact_id=piece_id,
            producer="holus/legacy-queue-reconciler",
            created_at=occurred_at,
            run_id=group_id,
            correlation_id=group_id,
            status=str(record.get("status", "unknown")),
            artifact_ref=f"content-queue/{piece_id}.yaml",
            content_hash=stable_hash(record.get("humanized_text") or record.get("text", "")),
            metadata={
                "legacy_reconciled": True,
                "platform": str(record.get("platform", "unknown")),
            },
        )
        self._record_batch([(parent, []), (node, [edge])])

    def record_candidate(self, candidate: Any) -> None:
        """Emit Research Radar candidate provenance without its title, summary, or URL."""
        candidate_id = str(candidate.candidate_id)
        created_at = candidate.created_at
        node = LineageNode(
            node_id=f"research-candidate:{candidate_id}",
            artifact_type=ArtifactType.RESEARCH_CANDIDATE,
            artifact_id=candidate_id,
            producer="holus/research-radar",
            created_at=created_at,
            run_id=candidate_id,
            correlation_id=candidate_id,
            status=str(candidate.status),
            content_hash=stable_hash(
                {"source_id": candidate.item.source_id, "key_idea": candidate.score.key_idea}
            ),
            metadata={
                "source": str(candidate.item.source),
                "recommended_action": candidate.score.recommended_action,
            },
        )
        edges: list[LineageEdge] = []
        if candidate.approved_group_id:
            source_id = f"source:{candidate.approved_group_id}"
            edges.append(
                self._edge(node.node_id, source_id, "approved_into", candidate_id, created_at)
            )
        self._record(node, edges)

    def _record(self, node: LineageNode, edges: list[LineageEdge] | None = None) -> None:
        try:
            self.store.record(node, edges)
        except OSError:
            logger.exception("lineage_recording_failed", extra={"node_id": node.node_id})

    def _record_batch(self, entries: list[tuple[LineageNode, list[LineageEdge]]]) -> None:
        try:
            self.store.record_batch(entries)
        except OSError:
            logger.exception("lineage_batch_recording_failed")

    @staticmethod
    def _edge(
        from_node_id: str,
        to_node_id: str,
        relation: str,
        run_id: str,
        created_at: datetime,
    ) -> LineageEdge:
        return LineageEdge(
            edge_id=stable_edge_id(from_node_id, to_node_id, relation),
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            relation=relation,
            created_at=created_at,
            run_id=run_id,
        )


def _recorded_at(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def _sha256_path(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
