"""Representative no-network source-to-review lineage chain."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from holus.agents.marketing.thought_pipeline import ThoughtContentPipeline
from holus.lineage.models import ArtifactType
from holus.lineage.recorder import LineageRecorder
from holus.lineage.store import LineageStore


@pytest.mark.asyncio
async def test_thought_pipeline_emits_source_plan_variant_visual_and_review(tmp_path: Path) -> None:
    queue = tmp_path / "data" / "content-queue"
    pipeline = ThoughtContentPipeline(
        queue_dir=queue, rendered_dir=tmp_path / "data" / "rendered-content"
    )
    content_set = await pipeline.create_content_set(
        thought="Holus should turn one honest founder thought into native social content.",
        channels=["linkedin_text", "instagram_image"],
    )
    store = LineageStore(tmp_path / "data" / "lineage")
    initial = store.manifest()
    kinds = {node["artifact_type"] for node in initial["nodes"]}
    assert {"source_thought", "content_set", "content_variant", "visual_asset"}.issubset(kinds)
    assert all(
        "One honest founder thought" not in str(node) and "raw_input" not in str(node)
        for node in initial["nodes"]
    )

    record = content_set.records[0] | {"lineage_updated_at": content_set.records[0]["generated_at"]}
    LineageRecorder(tmp_path / "data" / "lineage").record_outcome(
        record, outcome=ArtifactType.REVIEW_DECISION, status="approved"
    )
    report = store.validate()
    assert report.valid is True
    assert report.complete is True
    manifest = store.manifest()
    assert any(node["artifact_type"] == "review_decision" for node in manifest["nodes"])
    assert any(edge["relation"] == "resulted_in" for edge in manifest["edges"])
