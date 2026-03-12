"""Pydantic response models for the Observatory API."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel


class AgentInfo(BaseModel):
    id: str
    name: str
    model: str
    role: str
    last_run: datetime | None = None
    last_status: str | None = None  # "success" | "error" | "running" | None
    run_count_7d: int = 0


class AgentMetrics(BaseModel):
    agent_id: str
    avg_quality_score: float | None = None
    total_runs: int = 0
    success_rate: float = 0.0
    avg_cost_usd: float | None = None
    p50_latency_s: float | None = None
    p95_latency_s: float | None = None


class TrajectoryEntry(BaseModel):
    timestamp: datetime
    agent_id: str
    content_type: str | None = None
    action: str
    outcome: str | None = None  # "success" | "error"
    quality_score: float | None = None
    cost_usd: float | None = None
    tokens_used: int | None = None
    notes: str | None = None


class TrajectoryPage(BaseModel):
    entries: list[TrajectoryEntry]
    total: int
    page: int
    page_size: int
    has_more: bool


class ContentItem(BaseModel):
    id: str
    title: str | None = None
    content_type: str
    status: str  # "draft" | "review" | "published" | "rejected"
    created_at: datetime | None = None
    scheduled_for: datetime | None = None
    agent_id: str | None = None


class ContentStatusCounts(BaseModel):
    draft: int = 0
    review: int = 0
    published: int = 0
    rejected: int = 0


class ContentResponse(BaseModel):
    items: list[ContentItem]
    counts: ContentStatusCounts


class CalendarDay(BaseModel):
    date: str  # ISO date string
    items: list[ContentItem]


class ContentCalendarResponse(BaseModel):
    calendar: list[CalendarDay]


class EvaluationResult(BaseModel):
    timestamp: datetime
    agent_id: str
    score: float
    max_score: float
    pass_threshold: float
    passed: bool
    notes: str | None = None


class EvaluationsResponse(BaseModel):
    evaluations: list[EvaluationResult]


class EvaluationSummary(BaseModel):
    avg_score: float
    pass_rate: float
    score_by_agent: dict[str, float]
    trend_7d: list[dict[str, Any]]  # [{date, avg_score}]


class KnowledgeFile(BaseModel):
    filename: str
    last_modified: datetime
    size_bytes: int
    content: str | None = None  # populated only on /knowledge/{filename}


class KnowledgeResponse(BaseModel):
    files: list[KnowledgeFile]


class HealthStatus(BaseModel):
    kill_switch_active: bool
    trajectory_file_exists: bool
    eval_history_file_exists: bool
    agents_yaml_exists: bool
    content_queue_count: int
    error_rate_1h: float | None = None


class KPIMetrics(BaseModel):
    total_cycles: int
    success_rate: float
    avg_quality_score: float | None = None
    total_cost_usd: float | None = None
    cost_per_approved_asset: float | None = None
    active_agents_24h: int
    content_published_7d: int
