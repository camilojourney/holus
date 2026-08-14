"""Versioned public generation contract owned by Holus.

Limited to a safe create request, mapped job status, and preview reference.
Explicitly excludes costs, raw traces, artifacts, review, rejection, delivery,
publishing, credentials, and operator controls.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CONTRACT_VERSION: Literal["holus.generation.v1"] = "holus.generation.v1"

PublicGenerationStatus = Literal["queued", "generating", "ready", "error"]
GenerationSource = Literal["demo", "connection_required", "bff"]
PreviewAvailability = Literal["unavailable", "local_placeholder"]
GenerationMode = Literal["preview"]

FORBIDDEN_PUBLIC_FIELDS = frozenset(
    {
        "cost",
        "costs",
        "cost_usd",
        "trace",
        "traces",
        "raw_trace",
        "artifact",
        "artifacts",
        "artifact_url",
        "review",
        "rejection",
        "reject",
        "delivery",
        "publish",
        "publishing",
        "credentials",
        "api_key",
        "operator",
        "operator_controls",
    }
)


class CreateGenerationRequest(BaseModel):
    """Constrained create payload the future Holus BFF may forward."""

    instruction: str = Field(min_length=1, max_length=4000)
    niche: str | None = Field(default=None, max_length=200)
    target_platform: str | None = Field(default=None, max_length=80)
    mode: GenerationMode = "preview"


class PreviewReference(BaseModel):
    """Preview handle. Never an artifact URL or storage path."""

    availability: PreviewAvailability
    label: str


class CreateGenerationResponse(BaseModel):
    contract_version: Literal["holus.generation.v1"] = CONTRACT_VERSION
    request_id: str
    job_id: str
    status: PublicGenerationStatus
    source: GenerationSource


class GenerationJobStatus(BaseModel):
    """User-safe mapped job status for Holus UI."""

    contract_version: Literal["holus.generation.v1"] = CONTRACT_VERSION
    request_id: str
    job_id: str
    status: PublicGenerationStatus
    stage: str | None = None
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
    user_message: str | None = None
    preview: PreviewReference
    source: GenerationSource

    def public_field_names(self) -> set[str]:
        return set(self.model_dump().keys())
