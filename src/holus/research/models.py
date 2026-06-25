"""Pydantic boundary models for Research Radar."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Pydantic resolves runtime model annotations.
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

ResearchSource = Literal["arxiv", "hackernews", "rss"]
RecommendedAction = Literal["read_only", "candidate", "skip"]
CandidateStatus = Literal["pending", "approved", "rejected", "failed"]
SourceStatus = Literal["ok", "failed"]


class RawResearchItem(BaseModel):
    source: ResearchSource
    source_id: str
    item_id: str
    title: str
    url: HttpUrl
    summary: str
    author: str | None = None
    published_at: datetime
    raw_meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "summary", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> str:
        return str(value or "").strip()


class ResearchScore(BaseModel):
    item_id: str
    relevance: float
    novelty: float
    should_read: float
    matched_products: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    why_it_matters: str
    key_idea: str
    recommended_action: RecommendedAction

    @field_validator("relevance", "novelty", "should_read")
    @classmethod
    def _validate_unit_interval(cls, value: float) -> float:
        if value < 0 or value > 1:
            msg = "score values must be in [0, 1]"
            raise ValueError(msg)
        return value

    @field_validator("why_it_matters", "key_idea")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            msg = "field must be non-empty"
            raise ValueError(msg)
        return value


class ResearchCandidate(BaseModel):
    candidate_id: str
    item: RawResearchItem
    score: ResearchScore
    status: CandidateStatus = "pending"
    created_at: datetime
    approved_group_id: str | None = None
    failure_reason: str | None = None


class RadarSourceResult(BaseModel):
    source: str
    status: SourceStatus
    fetched: int
    new_items: int
    error: str | None = None


class RadarRunReport(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime
    sources: list[RadarSourceResult]
    scored: int
    digest_path: str | None
    candidates_created: int
