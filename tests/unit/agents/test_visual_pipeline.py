"""Tests for visual pipeline renderer variables."""

import pytest

from holus.agents.marketing.visual_pipeline import _render_visual, _visual_author_context
from holus.visual.dispatcher import VisualDispatchResult, VisualDispatchStatus, VisualProvider


def test_visual_author_context_omits_handle_by_default() -> None:
    author = _visual_author_context({})

    assert author["author_name"] == "Juan Camilo Martinez"
    assert author["brand_handle"] == ""


def test_visual_author_context_uses_opted_in_brand_identity_handle() -> None:
    author = _visual_author_context(
        {
            "brand_identity": {
                "author_name": "Juan Camilo Martinez",
                "language": "en",
                "brand_handle": "@camiloexperience",
            }
        }
    )

    assert author["brand_handle"] == "@camiloexperience"


def test_visual_author_context_direct_handle_overrides_identity() -> None:
    author = _visual_author_context(
        {
            "brand_handle": "@camilojourney",
            "brand_identity": {"brand_handle": "@camiloexperience"},
        }
    )

    assert author["brand_handle"] == "@camilojourney"


def test_render_visual_routes_through_dispatcher(tmp_path, monkeypatch) -> None:
    seen: dict[str, object] = {}

    async def fake_dispatch(self, request):
        seen["provider"] = request.provider
        seen["template"] = request.render_spec.template
        seen["metadata"] = request.metadata
        request.output_path.write_bytes(b"PNG_BYTES")
        return VisualDispatchResult(
            request_id=request.request_id,
            provider=VisualProvider.HTML_RENDERER,
            status=VisualDispatchStatus.SUCCEEDED,
            output_path=request.output_path,
            log_path=request.log_path,
            model_or_tool="test_dispatcher",
            duration_ms=1,
        )

    monkeypatch.setattr("holus.visual.dispatcher.VisualDispatcher.dispatch", fake_dispatch)

    output_path = tmp_path / "visual.png"
    ok = _render_visual({"type": "insight", "headline": "Dispatcher test"}, output_path)

    assert ok is True
    assert output_path.read_bytes() == b"PNG_BYTES"
    assert seen["provider"] == VisualProvider.HTML_RENDERER
    assert seen["template"] == "single_image/insight"
    assert seen["metadata"]["source"] == "visual_pipeline"
    assert seen["metadata"]["visual_type"] == "insight"


def test_render_visual_bridges_claim_chart_strategy_to_data_viz(tmp_path, monkeypatch) -> None:
    seen: dict[str, object] = {}

    async def fake_dispatch(self, request):
        seen["template"] = request.render_spec.template
        seen["variables"] = request.render_spec.variables
        seen["metadata"] = request.metadata
        request.output_path.write_bytes(b"PNG_BYTES")
        return VisualDispatchResult(
            request_id=request.request_id,
            provider=VisualProvider.HTML_RENDERER,
            status=VisualDispatchStatus.SUCCEEDED,
            output_path=request.output_path,
            log_path=request.log_path,
            model_or_tool="test_dispatcher",
            duration_ms=1,
        )

    monkeypatch.setattr("holus.visual.dispatcher.VisualDispatcher.dispatch", fake_dispatch)

    ok = _render_visual(
        {
            "type": "instagram_editorial_card",
            "hook": "Carousel format wins",
            "refined_visual_source": {
                "piece_id": "chart",
                "platform": "linkedin",
                "content_type": "image_post",
                "refined_text": "Image posts get 2.4%, video gets 5.1%, carousels get 8.7%.",
                "topic": "LinkedIn formats",
                "intended_takeaway": "Carousels outperform static posts.",
            },
            "visual_strategy": {
                "template_kind": "claim_chart",
                "design_system": {"accent": "#0f766e"},
            },
        },
        tmp_path / "chart.png",
    )

    assert ok is True
    assert seen["template"] == "single_image/data_viz"
    assert seen["metadata"]["visual_type"] == "data_viz"
    assert seen["variables"]["chart_type"] == "bar"
    assert seen["variables"]["highlight_index"] == 2


def test_render_visual_bridges_operating_map_strategy_to_flowchart(tmp_path, monkeypatch) -> None:
    seen: dict[str, object] = {}

    async def fake_dispatch(self, request):
        seen["template"] = request.render_spec.template
        seen["metadata"] = request.metadata
        request.output_path.write_bytes(b"PNG_BYTES")
        return VisualDispatchResult(
            request_id=request.request_id,
            provider=VisualProvider.HTML_RENDERER,
            status=VisualDispatchStatus.SUCCEEDED,
            output_path=request.output_path,
            log_path=request.log_path,
            model_or_tool="test_dispatcher",
            duration_ms=1,
        )

    monkeypatch.setattr("holus.visual.dispatcher.VisualDispatcher.dispatch", fake_dispatch)

    ok = _render_visual(
        {
            "type": "instagram_editorial_card",
            "hook": "Capture to publish",
            "visual_plan": {
                "plan_id": "workflow__v1",
                "route_mode": "workflow",
                "concept": "Thought workflow",
                "viewer_test": "Viewer can name the sequence.",
                "scene_script": "A clean operating board.",
                "composition_script": "Four stages in one direction.",
                "required_elements": ["Capture", "Refine", "Route", "Publish"],
                "text_policy": "Use stage labels only.",
            },
            "visual_strategy": {"template_kind": "operating_map"},
        },
        tmp_path / "workflow.png",
    )

    assert ok is True
    assert seen["template"] == "single_image/flowchart"
    assert seen["metadata"]["visual_type"] == "flowchart"


def test_render_visual_bridges_decision_surface_strategy_to_comparison(
    tmp_path, monkeypatch
) -> None:
    seen: dict[str, object] = {}

    async def fake_dispatch(self, request):
        seen["template"] = request.render_spec.template
        seen["metadata"] = request.metadata
        request.output_path.write_bytes(b"PNG_BYTES")
        return VisualDispatchResult(
            request_id=request.request_id,
            provider=VisualProvider.HTML_RENDERER,
            status=VisualDispatchStatus.SUCCEEDED,
            output_path=request.output_path,
            log_path=request.log_path,
            model_or_tool="test_dispatcher",
            duration_ms=1,
        )

    monkeypatch.setattr("holus.visual.dispatcher.VisualDispatcher.dispatch", fake_dispatch)

    ok = _render_visual(
        {
            "type": "instagram_editorial_card",
            "hook": "Rank the next move",
            "visual_plan": {
                "plan_id": "decision__v1",
                "route_mode": "product_scene",
                "concept": "Decision screen",
                "viewer_test": "Viewer can see what changed.",
                "scene_script": "A focused decision surface.",
                "composition_script": "Before and after columns.",
                "required_elements": ["Inputs", "Evidence", "Choice"],
                "text_policy": "Use short labels only.",
            },
            "visual_strategy": {"template_kind": "decision_surface"},
        },
        tmp_path / "decision.png",
    )

    assert ok is True
    assert seen["template"] == "single_image/comparison"
    assert seen["metadata"]["visual_type"] == "comparison"


@pytest.mark.asyncio
async def test_render_visual_works_inside_running_event_loop(tmp_path, monkeypatch) -> None:
    async def fake_dispatch(self, request):
        request.output_path.write_bytes(b"PNG_BYTES")
        return VisualDispatchResult(
            request_id=request.request_id,
            provider=VisualProvider.HTML_RENDERER,
            status=VisualDispatchStatus.SUCCEEDED,
            output_path=request.output_path,
            log_path=request.log_path,
            model_or_tool="test_dispatcher",
            duration_ms=1,
        )

    monkeypatch.setattr("holus.visual.dispatcher.VisualDispatcher.dispatch", fake_dispatch)

    output_path = tmp_path / "visual.png"
    ok = _render_visual({"type": "insight", "headline": "Async dispatcher test"}, output_path)

    assert ok is True
    assert output_path.read_bytes() == b"PNG_BYTES"
