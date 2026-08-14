"""Demo adapter must satisfy the public contract without I/O."""

from __future__ import annotations

import holus.generation.demo_adapter as adapter_mod
from holus.generation.demo_adapter import DemoGenerationAdapter
from holus.generation.public_contract import FORBIDDEN_PUBLIC_FIELDS, CreateGenerationRequest


def test_demo_lifecycle_ready_never_includes_artifact_url() -> None:
    adapter = DemoGenerationAdapter()
    created = adapter.create(
        CreateGenerationRequest(instruction="Demo clip", niche="demo", target_platform="linkedin"),
        outcome="ready",
    )
    assert created.status == "queued"
    assert created.source == "demo"
    frames = adapter.lifecycle(created.request_id)
    assert [frame.status for frame in frames] == ["queued", "generating", "ready"]
    terminal = frames[-1]
    assert terminal.preview.availability == "local_placeholder"
    assert "url" not in terminal.preview.model_dump()
    assert FORBIDDEN_PUBLIC_FIELDS.isdisjoint(terminal.model_dump())
    assert "No live" in frames[0].user_message or "demo" in frames[0].user_message.lower()


def test_demo_lifecycle_error_is_user_safe() -> None:
    adapter = DemoGenerationAdapter()
    created = adapter.create(
        CreateGenerationRequest(instruction="Demo error path"),
        outcome="error",
    )
    frames = adapter.lifecycle(created.request_id)
    assert [frame.status for frame in frames] == ["queued", "generating", "error"]
    assert "No live job was created" in frames[-1].user_message
    assert frames[-1].preview.availability == "unavailable"


def test_demo_adapter_does_not_perform_http(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("HTTP is not allowed from the demo adapter")

    monkeypatch.setattr(adapter_mod, "uuid4", adapter_mod.uuid4)
    try:
        import httpx
    except ImportError:
        httpx = None
    if httpx is not None:
        monkeypatch.setattr(httpx, "request", boom, raising=False)
        monkeypatch.setattr(httpx, "get", boom, raising=False)
        monkeypatch.setattr(httpx, "post", boom, raising=False)

    adapter = DemoGenerationAdapter()
    created = adapter.create(CreateGenerationRequest(instruction="No network"))
    adapter.lifecycle(created.request_id)
