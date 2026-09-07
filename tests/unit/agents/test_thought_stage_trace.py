"""Local user-path evidence for deterministic Thought Studio stage execution."""

from functools import update_wrapper
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
import yaml
from fastapi.testclient import TestClient

from holus.agents.marketing import thought_pipeline
from holus.agents.registry import AgentRegistry
from holus.agents.stage_execution import StageExecution, StageWiringError
from holus.api.app import create_app
from holus.api.routes import content
from holus.visual import dispatcher, generation_strategy, production_plan, proximity_router

THOUGHT = "A useful content workflow starts with a clear thought and human review."
TEXT_STAGES = [
    "normalize_source",
    "extract_essence",
    "platform_copy",
    "voice_check",
    "refine_visual_source",
    "visual_route",
    "visual_plan",
    "visual_strategy",
    "build_package",
]


@pytest.fixture
def local_only(tmp_path: Path, monkeypatch):
    queue = tmp_path / "queue"
    monkeypatch.setattr(content, "CONTENT_QUEUE_DIR", queue)
    client = TestClient(create_app())
    denied = Mock(side_effect=AssertionError("external client/network/prompt forbidden"))
    for target in (
        "httpx.Client.__init__",
        "httpx.AsyncClient.__init__",
        "socket.socket.connect",
        "socket.create_connection",
        "anthropic.Anthropic.__init__",
        "anthropic.AsyncAnthropic.__init__",
        "openai.OpenAI.__init__",
        "openai.AsyncOpenAI.__init__",
        "holus.integrations.holus_social_api.HolusSocialAPIClient.__init__",
        "holus.integrations.claude_api.client.HolusClaudeClient.__init__",
        "holus.core.prompt_loader.PromptLoader.__init__",
        "holus.agents.registry.AgentRegistry.get_agent_prompt",
        "holus.agents.registry.AgentRegistry.get_evaluator_for",
    ):
        monkeypatch.setattr(target, denied)
    # Exercise the real local PIL fallback, without starting a browser renderer.
    monkeypatch.setattr("holus.agents.marketing.visual_pipeline._render_visual", lambda *a: False)
    yield queue, client
    denied.assert_not_called()
    client.close()


def spy_on(monkeypatch, owner, name, *, async_method=False):
    original = getattr(owner, name)
    spy = (AsyncMock if async_method else Mock)(wraps=original)
    update_wrapper(spy, original)
    monkeypatch.setattr(owner, name, spy)
    return spy


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["linkedin_text", "instagram_image"])
async def test_truthful_trace_through_read_only_api(local_only, monkeypatch, channel) -> None:
    queue, client = local_only
    pipeline = thought_pipeline.ThoughtContentPipeline(queue_dir=queue)
    specs = [
        (pipeline, "normalize_source"),
        (thought_pipeline, "_extract_thought_essence"),
        (thought_pipeline, "_build_platform_text"),
        (thought_pipeline, "_local_voice_check"),
        (dispatcher.RefinedVisualSource, "from_queue_record"),
        (proximity_router, "choose_visual_concept_route"),
        (production_plan, "build_visual_production_plan"),
        (generation_strategy, "choose_visual_generation_strategy"),
        (pipeline, "_build_package"),
    ]
    if channel == "instagram_image":
        specs[-1:-1] = [
            (thought_pipeline, "_select_visual_brief"),
            (pipeline, "_render_visual_asset"),
        ]
    spies = [
        spy_on(monkeypatch, owner, name, async_method=name == "normalize_source")
        for owner, name in specs
    ]
    result = await pipeline.create_content_set(thought=THOUGHT, channels=[channel])
    [record] = result.records
    response = client.get(f"/api/v1/content/{record['piece_id']}")
    assert response.status_code == 200
    trace = response.json()["agent_trace"]
    assert all(spy.call_count == 1 for spy in spies)
    assert all(step.get("execution_kind") == "deterministic" for step in trace)
    assert [step["executor_id"] for step in trace] == [
        f"{spy.__module__}.{spy.__qualname__}" for spy in spies
    ]
    for step in trace:
        assert step["agent_id"] == step["executor_id"]
        assert step["status"] == "success"
        assert step["error_code"] is None
        assert step["group_id"] == result.group_id
        assert step["piece_id"] in (None, record["piece_id"])
        assert step["at"] == step["started_at"] <= step["finished_at"]
        assert step["latency_ms"] >= 0
        assert all(
            step[field] is None
            for field in (
                "model",
                "prompt_version",
                "prompt_sha",
                "input_tokens",
                "output_tokens",
                "cost_usd",
            )
        )
    assert len({s["run_id"] for s in trace}) == 1
    assert len({s["execution_id"] for s in trace}) == len(trace)
    copy = next(s for s in trace if s["stage_id"] == "platform_copy")
    assert copy["registered_agent_id"] == thought_pipeline.CHANNEL_AGENT[channel][0]
    assert copy["registry_status"] == "active"
    assert copy["agent_version"] and copy["prompt_path"]
    persisted = yaml.safe_load((queue / f"{record['piece_id']}.yaml").read_text())
    assert trace == persisted["agent_trace"] == record["agent_trace"]
    assert record["status"] == "pending_review"
    if channel == "linkedin_text":
        assert [s["stage_id"] for s in trace] == TEXT_STAGES
        assert "judge_score" not in record
        assert not pipeline.rendered_dir.exists()
    else:
        assert Path(record["rendered_image_path"]).is_relative_to(queue.parent)
        assert Path(record["rendered_image_path"]).is_file()


@pytest.mark.asyncio
async def test_shared_correlation_is_request_local(local_only) -> None:
    queue, _ = local_only
    runs: list[StageExecution] = []
    pipeline = thought_pipeline.ThoughtContentPipeline(queue_dir=queue, execution_records=runs)
    first = await pipeline.create_content_set(
        thought=THOUGHT,
        channels=["linkedin_text", "threads_text"],
        write_records=False,
    )
    second = await pipeline.create_content_set(
        thought=THOUGHT,
        channels=["linkedin_text"],
        write_records=False,
    )
    left, right = [r["agent_trace"] for r in first.records]
    assert left[0] == right[0] and left[-1] == right[-1]
    assert {s["execution_id"] for s in left[1:-1]}.isdisjoint(
        s["execution_id"] for s in right[1:-1]
    )
    assert first.group_id != second.group_id
    assert left[0]["run_id"] != second.records[0]["agent_trace"][0]["run_id"]
    assert len(runs) == 16 + 9
    assert {s.execution_id for s in runs} == {
        s["execution_id"]
        for result in (first, second)
        for record in result.records
        for s in record["agent_trace"]
    }
    assert not queue.exists()
    assert not (queue.parent / "lineage").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["missing", "planned", "deprecated"])
async def test_missing_or_inactive_association_fails_before_work(local_only, monkeypatch, status):
    queue, _ = local_only
    path = queue.parent / "fixture" / "agents" / "AGENTS.yaml"
    path.parent.mkdir(parents=True)
    agents = {
        name: {"status": "active"}
        for name in (
            "idea-injector",
            "voice-guardian",
            "voice-writer",
        )
    }
    if status == "missing":
        agents.pop("voice-writer")
    else:
        agents["voice-writer"]["status"] = status
    path.write_text(yaml.safe_dump({"agents": agents}))
    runs: list[StageExecution] = []
    pipeline = thought_pipeline.ThoughtContentPipeline(
        queue_dir=queue,
        registry=AgentRegistry(path),
        execution_records=runs,
    )
    normalize = spy_on(monkeypatch, pipeline, "normalize_source", async_method=True)
    with pytest.raises(StageWiringError, match="stage_agent:voice-writer"):
        await pipeline.create_content_set(thought=THOUGHT, channels=["linkedin_text"])
    normalize.assert_not_called()
    assert runs == []
    assert not queue.exists()
    assert not pipeline.rendered_dir.exists()
    assert not (queue.parent / "lineage").exists()


@pytest.mark.asyncio
async def test_stage_failure_records_only_entered_functions(local_only, monkeypatch):
    queue, _ = local_only
    runs: list[StageExecution] = []
    failure = RuntimeError("synthetic content must not leak to trace")

    def fail_copy(*args):
        raise failure

    monkeypatch.setattr(thought_pipeline, "_build_platform_text", fail_copy)
    voice = spy_on(monkeypatch, thought_pipeline, "_local_voice_check")
    pipeline = thought_pipeline.ThoughtContentPipeline(queue_dir=queue, execution_records=runs)
    with pytest.raises(RuntimeError) as error:
        await pipeline.create_content_set(thought=THOUGHT, channels=["linkedin_text"])
    assert error.value is failure
    assert [s.stage_id for s in runs] == ["normalize_source", "extract_essence", "platform_copy"]
    assert runs[-1].status == "error" and runs[-1].error_code == "RuntimeError"
    assert runs[-1].executor_id.endswith("fail_copy")
    assert runs[-1].finished_at and runs[-1].latency_ms >= 0
    assert "synthetic content" not in runs[-1].model_dump_json()
    voice.assert_not_called()
    assert not queue.exists()
    assert not (queue.parent / "lineage").exists()


@pytest.mark.asyncio
async def test_visual_not_selected_does_not_claim_render(local_only, monkeypatch):
    queue, _ = local_only
    original = generation_strategy.choose_visual_generation_strategy

    def no_visual(*args):
        strategy = original(*args)
        return strategy.model_copy(
            update={"rendering_path": type(strategy.rendering_path)("no_visual")}
        )

    monkeypatch.setattr(generation_strategy, "choose_visual_generation_strategy", no_visual)
    pipeline = thought_pipeline.ThoughtContentPipeline(queue_dir=queue)
    render = spy_on(monkeypatch, pipeline, "_render_visual_asset")
    result = await pipeline.create_content_set(thought=THOUGHT, channels=["instagram_image"])
    render.assert_not_called()
    assert [s["stage_id"] for s in result.records[0]["agent_trace"]] == TEXT_STAGES
    assert not pipeline.rendered_dir.exists()


@pytest.mark.asyncio
async def test_api_preserves_scored_execution_and_unverified_legacy(local_only):
    queue, client = local_only
    pipeline = thought_pipeline.ThoughtContentPipeline(queue_dir=queue)
    result = await pipeline.create_content_set(thought=THOUGHT, channels=["linkedin_text"])
    [record] = result.records
    scored = next(s for s in record["agent_trace"] if s["stage_id"] == "voice_check")
    # Synthetic observed local score fixture, not a model-backed judge claim.
    scored.update(quality_score="8", verdict="PASS")
    pipeline.write_queue_record(record)
    detail = client.get(f"/api/v1/content/{record['piece_id']}").json()
    assert detail["agent_trace"] == record["agent_trace"]
    legacy = {
        "piece_id": "legacy",
        "text": "Historical synthetic fixture",
        "agent_trace": [
            None,
            {
                "agent_id": "voice-writer",
                "model": "legacy-model",
                "role": "draft",
                "at": "2026-01-01T00:00:00Z",
                "quality_score": 8,
                "verdict": "PASS",
            },
            {"role": "legacy unknown", "at": "invalid"},
        ],
    }
    pipeline.write_queue_record(legacy)
    response = client.get("/api/v1/content/legacy")
    assert response.status_code == 200
    old, unknown = response.json()["agent_trace"]
    assert old["agent_id"] == "voice-writer" and old["model"] == "legacy-model"
    assert old["quality_score"] == "8" and old["verdict"] == "PASS"
    assert old["at"] == "2026-01-01T00:00:00Z"
    assert all(
        old[field] is None
        for field in (
            "schema_version",
            "executor_id",
            "execution_kind",
            "status",
            "run_id",
            "prompt_sha",
        )
    )
    assert unknown["agent_id"] == "unknown" and unknown["at"] is None


@pytest.mark.asyncio
async def test_supplied_url_evidence_remains_local(local_only, monkeypatch):
    queue, _ = local_only
    pipeline = thought_pipeline.ThoughtContentPipeline(queue_dir=queue)
    fetch = AsyncMock(side_effect=AssertionError("must use supplied source text"))
    monkeypatch.setattr(pipeline, "_extract_from_url", fetch)
    result = await pipeline.create_content_set(
        thought=THOUGHT,
        channels=["linkedin_text"],
        source_type="url",
        source_url="https://example.invalid/synthetic",
        fetch_source_url=False,
    )
    fetch.assert_not_called()
    assert [s["stage_id"] for s in result.records[0]["agent_trace"]] == TEXT_STAGES
    assert result.records[0]["source_type"] == "url"


@pytest.mark.asyncio
async def test_url_retrieval_is_not_claimed_as_deterministic(local_only, monkeypatch):
    queue, _ = local_only
    pipeline = thought_pipeline.ThoughtContentPipeline(queue_dir=queue)
    fetch = AsyncMock(return_value=THOUGHT)
    monkeypatch.setattr(pipeline, "_extract_from_url", fetch)
    result = await pipeline.create_content_set(
        thought="",
        channels=["linkedin_text"],
        source_type="url",
        source_url="https://example.invalid/synthetic",
    )
    fetch.assert_awaited_once()
    assert [s["stage_id"] for s in result.records[0]["agent_trace"]] == TEXT_STAGES[1:]
