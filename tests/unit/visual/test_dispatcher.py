"""Tests for the visual asset dispatcher."""

from __future__ import annotations

import json
import subprocess
from io import BytesIO

import pytest
from PIL import Image

from holus.visual.dispatcher import (
    RefinedVisualSource,
    VisualAssetKind,
    VisualDispatcher,
    VisualDispatchRequest,
    VisualDispatchStatus,
    VisualProvider,
)
from holus.visual.models import OutputFormat, RenderSpec
from holus.visual.production_plan import build_visual_production_plan
from holus.visual.proximity_router import (
    VisualConceptRoute,
    VisualProximityMode,
    choose_visual_concept_route,
)


def _png_bytes(width: int = 1024, height: int = 1024) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(242, 242, 242)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_visual_proximity_router_selects_workflow_for_harness_content() -> None:
    route = choose_visual_concept_route(
        {
            "platform": "linkedin",
            "content_type": "image_post",
            "topic": "The model is not the workflow. The harness is the workflow.",
            "refined_text": (
                "The model is not the workflow. It is a harness: planning, execution, "
                "skills, reviews, fallbacks, and daily work arranged as separate jobs."
            ),
        }
    )

    assert route.mode == VisualProximityMode.WORKFLOW
    assert route.proximity_score == 5
    assert route.use_workflow is True
    assert "role separation" in " ".join(route.visual_do)
    assert "unlabeled blank modules" in " ".join(route.visual_dont)


def test_visual_proximity_router_selects_chart_for_metric_content() -> None:
    route = choose_visual_concept_route(
        {
            "topic": "Compare the conversion rate by format",
            "refined_text": "Carousel posts convert 32% better than single images.",
        }
    )

    assert route.mode == VisualProximityMode.CHART
    assert route.use_chart is True


def test_visual_proximity_router_prefers_product_surface_over_reviewer_person() -> None:
    route = choose_visual_concept_route(
        {
            "topic": "Review is easier when the reason is visible.",
            "refined_text": (
                "A content queue should not only say approve or reject. The reviewer needs "
                "to see the fit signal beside the draft, otherwise the queue becomes a guessing surface."
            ),
        }
    )

    assert route.mode == VisualProximityMode.PRODUCT_SCENE
    assert "product job" in " ".join(route.visual_do)


def test_visual_proximity_router_does_not_treat_drafting_as_product_draft() -> None:
    route = choose_visual_concept_route(
        {
            "topic": "The handoff is where quality gets lost.",
            "refined_text": (
                "A strong AI workflow is not one perfect model. It is the handoff "
                "between framing, drafting, evidence, review, and publishing."
            ),
        }
    )

    assert route.mode == VisualProximityMode.WORKFLOW


def test_visual_proximity_router_sends_caption_dependency_to_typography() -> None:
    route = choose_visual_concept_route(
        {
            "topic": "If the image needs the caption, it is not done.",
            "refined_text": (
                "The LinkedIn image should carry the thesis before the caption expands it. "
                "If the visual only makes sense after reading the post, it is decoration."
            ),
        }
    )

    assert route.mode == VisualProximityMode.TYPOGRAPHY_CARD
    assert "thesis readable" in " ".join(route.visual_do)


def test_visual_production_plan_adds_mode_specific_script() -> None:
    source = RefinedVisualSource(
        piece_id="workflow-example",
        platform="linkedin",
        content_type="image_post",
        refined_text="Planning, execution, review, and fallback need separate handoffs.",
        topic="Separate handoffs make the work better.",
        intended_takeaway="Separate handoffs make the work better.",
    )
    route = choose_visual_concept_route(source)
    plan = build_visual_production_plan(source, route)

    assert plan.route_mode == VisualProximityMode.WORKFLOW
    assert "five distinct process stages" in plan.required_elements
    assert "Viewer test" in plan.prompt_contract()
    assert "Compliance checks" in plan.prompt_contract()
    assert "LinkedIn impact lens" in plan.prompt_contract()
    assert "one scroll-stopping top claim" in plan.required_elements


def test_visual_production_plan_adds_news_battlecard_lens() -> None:
    source = RefinedVisualSource(
        piece_id="amd-vs-nvidia",
        platform="linkedin",
        content_type="image_post",
        refined_text=(
            "AMD Ryzen AI Halo vs NVIDIA DGX Spark: same memory, same bandwidth, "
            "$700 less for local AI developers."
        ),
        topic="AMD vs NVIDIA local AI workstation comparison",
        intended_takeaway="Same memory, same bandwidth, $700 less.",
    )
    route = choose_visual_concept_route(source)
    plan = build_visual_production_plan(source, route)
    contract = plan.prompt_contract()

    assert "news comparison battlecard" in contract
    assert "one dominant numeric delta" in plan.required_elements
    assert "compact evidence grid with 3-5 rows" in plan.required_elements
    assert "invented prices, benchmarks, or specs" in plan.forbidden_elements


@pytest.mark.asyncio
async def test_html_renderer_dispatch_writes_asset_log_and_sidecar(tmp_path, monkeypatch):
    async def fake_render(spec: RenderSpec) -> bytes:
        assert spec.template == "single_image/insight"
        return _png_bytes(1200, 1500)

    monkeypatch.setattr("holus.visual.dispatcher._render_visual_bytes", fake_render)

    output_path = tmp_path / "asset.png"
    log_path = tmp_path / "image-dispatch.jsonl"
    request = VisualDispatchRequest(
        request_id="img_html_test",
        render_spec=RenderSpec(
            template="single_image/insight",
            variables={"headline": "Test"},
            output_format=OutputFormat.PNG,
        ),
        output_path=output_path,
        log_path=log_path,
        refined_source=RefinedVisualSource(
            piece_id="img_html_test",
            platform="linkedin",
            content_type="image_post",
            refined_text="The workflow is the point.",
            topic="The workflow is the point.",
        ),
        visual_route=VisualConceptRoute(
            mode=VisualProximityMode.WORKFLOW,
            proximity_score=5,
            viewer_takeaway="The workflow is the point.",
            scene="operating flow",
            subject="separate jobs",
            composition="five stages",
            use_workflow=True,
            visual_do=["show role separation"],
            visual_dont=["generic AI wallpaper"],
            rationale="test route",
        ),
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.SUCCEEDED
    assert result.provider == VisualProvider.HTML_RENDERER
    assert output_path.read_bytes().startswith(b"\x89PNG")
    assert (tmp_path / "asset.png.dispatch.json").exists()

    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [record["event"] for record in records] == [
        "visual_dispatch_started",
        "visual_judge_completed",
        "visual_dispatch_completed",
    ]
    assert records[-1]["provider"] == "html_renderer"
    assert records[-1]["status"] == "succeeded"
    assert records[-1]["visual_route"]["mode"] == "workflow"
    assert records[-1]["visual_plan"]["route_mode"] == "workflow"
    assert records[-1]["visual_judge"]["verdict"] == "pass"


@pytest.mark.asyncio
async def test_prompt_routes_to_codex_provider_but_requires_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("HOLUS_ENABLE_CODEX_IMAGE_PROVIDER", raising=False)

    request = VisualDispatchRequest(
        request_id="img_codex_disabled",
        provider=VisualProvider.CODEX_CLI_IMAGE,
        prompt="A clean LinkedIn visual about agent routing.",
        output_path=tmp_path / "asset.png",
        log_path=tmp_path / "image-dispatch.jsonl",
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.FAILED
    assert "HOLUS_ENABLE_CODEX_IMAGE_PROVIDER=1" in (result.error or "")
    records = [json.loads(line) for line in request.log_path.read_text().splitlines()]
    assert records[-1]["event"] == "visual_dispatch_failed"


@pytest.mark.asyncio
async def test_codex_provider_invokes_cli_and_verifies_output(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLUS_ENABLE_CODEX_IMAGE_PROVIDER", "1")

    output_path = tmp_path / "asset.png"
    captured: dict[str, object] = {}

    def fake_run(command, *, timeout_seconds):
        captured["command"] = command
        captured["timeout_seconds"] = timeout_seconds
        output_path.write_bytes(_png_bytes())
        return subprocess.CompletedProcess(command, 0, stdout="saved", stderr="")

    monkeypatch.setattr("holus.visual.dispatcher._run_command_with_timeout", fake_run)

    request = VisualDispatchRequest(
        request_id="img_codex_test",
        provider=VisualProvider.CODEX_CLI_IMAGE,
        asset_kind=VisualAssetKind.SINGLE_IMAGE,
        prompt="An AI marketing control room with charts, no text.",
        output_path=output_path,
        log_path=tmp_path / "image-dispatch.jsonl",
        width=1024,
        height=1024,
        timeout_seconds=30,
        model="gpt-5.5",
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.SUCCEEDED
    assert output_path.read_bytes().startswith(b"\x89PNG")
    assert result.model_or_tool == "codex_cli:gpt-5.5"

    command = captured["command"]
    assert isinstance(command, list)
    assert command[:5] == ["codex", "-a", "never", "-m", "gpt-5.5"]
    assert "exec" in command
    assert any(str(output_path) in part for part in command)
    assert captured["timeout_seconds"] == 30


@pytest.mark.asyncio
async def test_codex_provider_recovers_when_timeout_exit_still_created_image(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLUS_ENABLE_CODEX_IMAGE_PROVIDER", "1")

    output_path = tmp_path / "asset.png"

    def fake_run(command, *, timeout_seconds):
        output_path.write_bytes(_png_bytes())
        return subprocess.CompletedProcess(
            command,
            124,
            stdout="Generated and saved the image.",
            stderr="Timed out after 180 seconds.",
        )

    monkeypatch.setattr("holus.visual.dispatcher._run_command_with_timeout", fake_run)

    request = VisualDispatchRequest(
        request_id="img_codex_timeout_recovered",
        provider=VisualProvider.CODEX_CLI_IMAGE,
        asset_kind=VisualAssetKind.SINGLE_IMAGE,
        prompt="A concrete editorial image.",
        output_path=output_path,
        log_path=tmp_path / "image-dispatch.jsonl",
        timeout_seconds=30,
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.SUCCEEDED
    assert result.output_path == output_path.resolve()
    assert result.metadata["provider_exit_code"] == 124
    assert result.metadata["recovered_from_nonzero_exit"] is True


@pytest.mark.asyncio
async def test_codex_provider_builds_prompt_from_refined_source(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLUS_ENABLE_CODEX_IMAGE_PROVIDER", "1")

    output_path = tmp_path / "asset.png"
    captured: dict[str, object] = {}

    def fake_run(command, *, timeout_seconds):
        captured["command"] = command
        output_path.write_bytes(_png_bytes())
        return subprocess.CompletedProcess(command, 0, stdout="saved", stderr="")

    monkeypatch.setattr("holus.visual.dispatcher._run_command_with_timeout", fake_run)

    source = RefinedVisualSource(
        piece_id="thought-123-linkedin_image",
        platform="linkedin",
        content_type="image_post",
        refined_text="The model is not the workflow. The harness is the workflow.",
        headline="The model is not the workflow",
        topic="AI workflow harness",
        intended_takeaway="Give each model one job inside the harness.",
        raw_thought_provenance="On my AI little workflow I used Claude to plan...",
    )
    request = VisualDispatchRequest(
        request_id="img_refined_source",
        provider=VisualProvider.CODEX_CLI_IMAGE,
        refined_source=source,
        visual_route=VisualConceptRoute(
            mode=VisualProximityMode.WORKFLOW,
            proximity_score=5,
            viewer_takeaway="The workflow is job design.",
            scene="clear operating flow",
            subject="planning, execution, review, fallback",
            composition="five labeled stages",
            use_workflow=True,
            visual_do=["show role separation"],
            visual_dont=["generic AI wallpaper"],
            rationale="workflow language dominates the refined source",
        ),
        output_path=output_path,
        log_path=tmp_path / "image-dispatch.jsonl",
        timeout_seconds=30,
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.SUCCEEDED
    assert result.prompt_used is not None
    assert "SOURCE OF TRUTH: refined Holus content" in result.prompt_used
    assert "The model is not the workflow" in result.prompt_used
    assert "On my AI little workflow" not in result.prompt_used

    command = captured["command"]
    assert isinstance(command, list)
    joined_command = "\n".join(command)
    assert "Visual route: workflow" in joined_command
    assert "Production plan:" in joined_command
    assert "Compliance checks:" in joined_command
    assert "show role separation" in joined_command
    assert "no generic AI wallpaper" in joined_command

    records = [json.loads(line) for line in request.log_path.read_text().splitlines()]
    assert records[-1]["refined_source"]["piece_id"] == "thought-123-linkedin_image"
    assert records[-1]["visual_judge"]["verdict"] == "pass"


@pytest.mark.asyncio
async def test_agy_provider_requires_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("HOLUS_ENABLE_AGY_IMAGE_PROVIDER", raising=False)

    request = VisualDispatchRequest(
        request_id="img_agy_disabled",
        provider=VisualProvider.AGY_CLI_IMAGE,
        prompt="A clean LinkedIn visual about routing models.",
        output_path=tmp_path / "asset.png",
        log_path=tmp_path / "image-dispatch.jsonl",
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.FAILED
    assert "HOLUS_ENABLE_AGY_IMAGE_PROVIDER=1" in (result.error or "")
    records = [json.loads(line) for line in request.log_path.read_text().splitlines()]
    assert records[-1]["event"] == "visual_dispatch_failed"


@pytest.mark.asyncio
async def test_agy_provider_invokes_cli_and_verifies_output(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLUS_ENABLE_AGY_IMAGE_PROVIDER", "1")

    output_path = tmp_path / "asset.png"
    captured: dict[str, object] = {}

    def fake_run(command, *, timeout_seconds):
        captured["command"] = command
        captured["timeout_seconds"] = timeout_seconds
        output_path.write_bytes(_png_bytes())
        return subprocess.CompletedProcess(command, 0, stdout="saved", stderr="")

    monkeypatch.setattr("holus.visual.dispatcher._run_command_with_timeout", fake_run)

    request = VisualDispatchRequest(
        request_id="img_agy_test",
        provider=VisualProvider.AGY_CLI_IMAGE,
        asset_kind=VisualAssetKind.SINGLE_IMAGE,
        prompt="A LinkedIn image showing one model per workflow lane.",
        output_path=output_path,
        log_path=tmp_path / "image-dispatch.jsonl",
        width=1024,
        height=1024,
        timeout_seconds=30,
        model="Gemini 3.5 Flash (Medium)",
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.SUCCEEDED
    assert output_path.read_bytes().startswith(b"\x89PNG")
    assert result.model_or_tool == "agy_cli:Gemini 3.5 Flash (Medium)"

    command = captured["command"]
    assert isinstance(command, list)
    assert command[:4] == [
        "agy",
        "--dangerously-skip-permissions",
        "--model",
        "Gemini 3.5 Flash (Medium)",
    ]
    assert "--print" in command
    assert any(str(output_path) in part for part in command)
    assert captured["timeout_seconds"] == 35


@pytest.mark.asyncio
async def test_carousel_outline_dispatch_writes_pdf_log_and_sidecar(tmp_path, monkeypatch):
    def fake_build_carousel_pdf(outline, output_path):
        assert outline["slides"][0]["variables"]["headline"] == "The harness"
        output_path.write_bytes(b"%PDF-FAKE")
        return output_path

    monkeypatch.setattr(
        "holus.visual.carousel_builder.build_carousel_pdf",
        fake_build_carousel_pdf,
    )

    output_path = tmp_path / "carousel.pdf"
    log_path = tmp_path / "image-dispatch.jsonl"
    request = VisualDispatchRequest(
        request_id="pdf_dispatch_test",
        provider=VisualProvider.HTML_RENDERER,
        asset_kind=VisualAssetKind.CAROUSEL,
        carousel_outline={
            "slides": [
                {"type": "hook", "variables": {"headline": "The harness"}},
                {"type": "body", "variables": {"title": "Why", "body": "Roles matter"}},
            ]
        },
        output_path=output_path,
        log_path=log_path,
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.SUCCEEDED
    assert output_path.read_bytes() == b"%PDF-FAKE"
    assert (tmp_path / "carousel.pdf.dispatch.json").exists()
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [record["event"] for record in records] == [
        "visual_dispatch_started",
        "visual_judge_completed",
        "visual_dispatch_completed",
    ]
    assert records[-1]["asset_kind"] == "carousel"


@pytest.mark.asyncio
async def test_dispatcher_retries_with_mutated_plan_when_judge_requests_retry(tmp_path):
    class FakeImageProvider:
        provider = VisualProvider.CODEX_CLI_IMAGE

        def __init__(self) -> None:
            self.calls = 0
            self.plan_ids: list[str] = []

        async def generate(self, request: VisualDispatchRequest):
            self.calls += 1
            if request.visual_plan is not None:
                self.plan_ids.append(request.visual_plan.plan_id)
            output_path = request.resolved_output_path(".png")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if self.calls == 1:
                output_path.write_bytes(_png_bytes(200, 200))
            else:
                output_path.write_bytes(_png_bytes(1024, 1024))
            from holus.visual.dispatcher import VisualDispatchResult

            return VisualDispatchResult(
                request_id=request.request_id,
                provider=VisualProvider.CODEX_CLI_IMAGE,
                status=VisualDispatchStatus.SUCCEEDED,
                output_path=output_path,
                log_path=request.log_path,
                prompt_used=request.prompt,
                model_or_tool="fake-image-model",
                duration_ms=1,
                metadata={"call": self.calls},
            )

    source = RefinedVisualSource(
        piece_id="workflow-retry",
        platform="linkedin",
        content_type="image_post",
        refined_text="Planning, execution, review, and fallback need separate jobs.",
        topic="The harness is the workflow",
        intended_takeaway="The harness is the workflow.",
    )
    route = choose_visual_concept_route(source)
    plan = build_visual_production_plan(source, route)
    provider = FakeImageProvider()
    request = VisualDispatchRequest(
        request_id="img_retry_test",
        provider=VisualProvider.CODEX_CLI_IMAGE,
        refined_source=source,
        visual_route=route,
        visual_plan=plan,
        output_path=tmp_path / "asset.png",
        log_path=tmp_path / "image-dispatch.jsonl",
        max_attempts=2,
    )

    result = await VisualDispatcher(providers={VisualProvider.CODEX_CLI_IMAGE: provider}).dispatch(
        request
    )

    assert result.status == VisualDispatchStatus.SUCCEEDED
    assert provider.calls == 2
    assert provider.plan_ids[0] == plan.plan_id
    assert provider.plan_ids[1].endswith("__retry2")
    assert result.output_path == tmp_path / "asset.retry2.png"
    assert result.metadata["visual_judge"]["verdict"] == "pass"

    records = [json.loads(line) for line in request.log_path.read_text().splitlines()]
    assert [record["event"] for record in records] == [
        "visual_dispatch_started",
        "visual_judge_completed",
        "visual_dispatch_retrying",
        "visual_judge_completed",
        "visual_dispatch_completed",
    ]
    assert records[1]["visual_judge"]["verdict"] == "retry"
    assert records[2]["extra"]["next_attempt"] == 2


@pytest.mark.asyncio
async def test_unimplemented_provider_returns_failure(tmp_path):
    request = VisualDispatchRequest(
        request_id="img_unimplemented",
        provider=VisualProvider.PILASTER_MCP,
        prompt="Generate with future provider",
        output_path=tmp_path / "asset.png",
        log_path=tmp_path / "image-dispatch.jsonl",
    )

    result = await VisualDispatcher().dispatch(request)

    assert result.status == VisualDispatchStatus.FAILED
    assert "not implemented" in (result.error or "")
    records = [json.loads(line) for line in request.log_path.read_text().splitlines()]
    assert [record["event"] for record in records] == [
        "visual_dispatch_started",
        "visual_dispatch_failed",
    ]
