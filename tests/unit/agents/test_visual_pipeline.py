"""Tests for visual pipeline renderer variables."""

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
    assert seen["metadata"]["source"] == "visual_pipeline"
    assert seen["metadata"]["visual_type"] == "insight"
