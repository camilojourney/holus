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


class AgentDetailResponse(BaseModel):
    """Extended agent info with dimension averages for the detail page."""

    id: str
    name: str
    model: str
    role: str
    last_run: datetime | None = None
    last_status: str | None = None
    run_count_7d: int = 0
    dimension_averages: dict[str, float] = {}


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


class AgentTraceStep(BaseModel):
    agent_id: str
    model: str | None = None
    role: str | None = None
    at: datetime | None = None
    quality_score: str | None = None
    verdict: str | None = None


class ContentQuality(BaseModel):
    hook_score: str | None = None
    voice_check: str | None = None
    quality_score: int | None = None
    violations: list[str] = []


class ContentItem(BaseModel):
    id: str
    title: str | None = None
    content_type: str
    platform: str | None = None
    content_pillar: str | None = None
    status: str  # "draft" | "pending_review" | "approved" | "scheduled" | "published" | "rejected"
    created_at: datetime | None = None
    scheduled_for: datetime | None = None
    agent_id: str | None = None
    idea_source: str | None = None
    quality: ContentQuality | None = None


class ContentDetail(ContentItem):
    """Full content piece including text and agent trace."""

    text: str | None = None
    hashtags: list[str] = []
    char_count: int | None = None
    agent_trace: list[AgentTraceStep] = []
    image_url: str | None = None
    image_b_url: str | None = None
    visual_spec: dict[str, Any] | None = None
    visual_spec_b: dict[str, Any] | None = None
    judge_score: float | None = None
    judge_verdict: str | None = None


class ContentPatchRequest(BaseModel):
    status: str | None = None  # "approved" | "rejected" | "scheduled"
    scheduled_at: str | None = None  # ISO8601


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


class MemoryResponse(BaseModel):
    """MEMORY.md content for the knowledge page."""

    content: str
    last_modified: datetime
    size_bytes: int


class LessonEntry(BaseModel):
    """A single lesson from lessons.json."""

    id: str | None = None
    date: str | None = None
    lesson: str | None = None
    source: str | None = None
    agent_id: str | None = None
    category: str | None = None
    context: str | None = None


class LessonsResponse(BaseModel):
    """Recent lessons for the knowledge page."""

    lessons: list[LessonEntry]
    total: int


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


# --- Results / Growth models ---


class PlatformStats(BaseModel):
    followers: int
    followers_30d_ago: int
    posts_30d: int
    impressions_30d: int
    engagement_rate: float
    top_content_type: str
    profile_url: str | None = None


class DailyGrowth(BaseModel):
    date: str
    total_followers: int
    posts: int
    impressions: int


class TopPost(BaseModel):
    id: str
    title: str
    platform: str
    published_at: datetime
    impressions: int
    likes: int
    comments: int
    shares: int
    engagement_rate: float
    content_type: str
    product: str


class PillarStats(BaseModel):
    count: int
    avg_engagement_rate: float
    total_impressions: int


class ProductStats(BaseModel):
    count: int
    total_impressions: int
    avg_engagement_rate: float


class GrowthResponse(BaseModel):
    snapshot_date: str
    platforms: dict[str, PlatformStats]
    daily_growth: list[DailyGrowth]
    top_posts: list[TopPost]
    content_by_pillar: dict[str, PillarStats]
    content_by_product: dict[str, ProductStats]
