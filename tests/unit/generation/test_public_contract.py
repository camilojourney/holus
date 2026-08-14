"""Tests for the Holus-owned public generation contract."""

from __future__ import annotations

from holus.generation.public_contract import (
    CONTRACT_VERSION,
    FORBIDDEN_PUBLIC_FIELDS,
    CreateGenerationRequest,
    CreateGenerationResponse,
    GenerationJobStatus,
    PreviewReference,
)


def test_contract_version_is_stable() -> None:
    assert CONTRACT_VERSION == "holus.generation.v1"


def test_create_request_rejects_empty_instruction() -> None:
    try:
        CreateGenerationRequest(instruction="")
    except Exception:
        return
    raise AssertionError("empty instruction must be rejected")


def test_status_model_excludes_operator_and_cost_fields() -> None:
    status = GenerationJobStatus(
        request_id="holus-demo-test",
        job_id="holus-mapped-test",
        status="queued",
        stage="queued",
        progress=0.0,
        user_message="Demo only",
        preview=PreviewReference(availability="unavailable", label="Preview unavailable"),
        source="demo",
    )
    payload = status.model_dump()
    assert payload["contract_version"] == CONTRACT_VERSION
    assert FORBIDDEN_PUBLIC_FIELDS.isdisjoint(payload)
    assert "url" not in payload["preview"]
    assert set(CreateGenerationResponse.model_fields) <= {
        "contract_version",
        "request_id",
        "job_id",
        "status",
        "source",
    }
