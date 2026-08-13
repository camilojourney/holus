"""Versioned, safe, read-only provenance contract for Holus artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "1.0"
_SECRET_KEY = re.compile(r"(?:api[_-]?key|token|secret|password|authorization)", re.I)
_SECRET_VALUE = re.compile(r"(?:sk-|bearer\s+|ghp_)[A-Za-z0-9_-]+", re.I)


def _redact_metadata(value: dict[str, Any]) -> dict[str, str | int | float | bool | None]:
    safe: dict[str, str | int | float | bool | None] = {}
    for key, item in value.items():
        if _SECRET_KEY.search(str(key)):
            continue
        if isinstance(item, str):
            if _SECRET_VALUE.search(item):
                continue
            safe[str(key)] = item[:512]
        elif isinstance(item, (int, float, bool)) or item is None:
            safe[str(key)] = item
    return safe


class ArtifactType(StrEnum):
    """Artifact classes emitted by currently implemented Holus stages."""

    SOURCE_THOUGHT = "source_thought"
    RESEARCH_CANDIDATE = "research_candidate"
    CONTENT_SET = "content_set"
    CONTENT_VARIANT = "content_variant"
    VISUAL_ASSET = "visual_asset"
    REVIEW_DECISION = "review_decision"
    PUBLICATION_REQUEST = "publication_request"
    PUBLISH_OUTCOME = "publish_outcome"
    SCHEDULE_OUTCOME = "schedule_outcome"


class LineageNode(BaseModel):
    """A privacy-safe description of one durable or logical pipeline artifact."""

    schema_version: str = SCHEMA_VERSION
    node_id: str
    artifact_type: ArtifactType
    artifact_id: str
    producer: str
    created_at: datetime
    run_id: str
    correlation_id: str
    status: str
    artifact_ref: str | None = None
    content_hash: str | None = None
    config_hash: str | None = None
    model_hash: str | None = None
    checksum: str | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _schema_is_supported(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            msg = f"Unsupported lineage schema version: {value}"
            raise ValueError(msg)
        return value

    @field_validator("artifact_ref")
    @classmethod
    def _relative_reference(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value.startswith("/") or ".." in value.split("/"):
            msg = "artifact_ref must be a stable relative path"
            raise ValueError(msg)
        return value

    @field_validator("metadata")
    @classmethod
    def _safe_metadata(cls, value: dict[str, Any]) -> dict[str, str | int | float | bool | None]:
        return _redact_metadata(value)


class LineageEdge(BaseModel):
    """A directed relationship between two lineage nodes."""

    schema_version: str = SCHEMA_VERSION
    edge_id: str
    from_node_id: str
    to_node_id: str
    relation: str
    created_at: datetime
    run_id: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _schema_is_supported(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            msg = f"Unsupported lineage schema version: {value}"
            raise ValueError(msg)
        return value

    @field_validator("metadata")
    @classmethod
    def _safe_metadata(cls, value: dict[str, Any]) -> dict[str, str | int | float | bool | None]:
        return _redact_metadata(value)


def stable_hash(value: Any) -> str:
    """Return a deterministic SHA-256 hash for a JSON-compatible value."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def stable_edge_id(from_node_id: str, to_node_id: str, relation: str) -> str:
    """Return a stable relationship ID so repeated emissions are idempotent."""
    return f"edge-{stable_hash([from_node_id, to_node_id, relation])[:24]}"


def utc_now() -> datetime:
    """Return an aware UTC timestamp, isolated for deterministic tests."""
    return datetime.now(UTC)
