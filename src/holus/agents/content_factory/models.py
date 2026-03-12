"""Pydantic models for the Content Factory v2 (Spec 024).

All models use Pydantic v2 with ``extra="forbid"`` for strict validation.
These models represent the domain objects that flow through the factory pipeline:
idea → piece → batch.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class FormatType(StrEnum):
    """Content format produced by a specialist creator."""

    CAROUSEL = "carousel"
    PDF = "pdf"
    DIAGRAM = "diagram"
    VIDEO_BRIEF = "video_brief"
    TEXT = "text"


class PlatformType(StrEnum):
    """Social media platforms supported by the Content Factory."""

    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    FACEBOOK = "facebook"


# Platforms that require media — text-only posts are blocked.
MEDIA_REQUIRED_PLATFORMS: frozenset[PlatformType] = frozenset({PlatformType.INSTAGRAM})

# Character limits per platform.
PLATFORM_CHAR_LIMITS: dict[PlatformType, int] = {
    PlatformType.LINKEDIN: 3000,
    PlatformType.TWITTER: 280,
    PlatformType.INSTAGRAM: 2200,
    PlatformType.THREADS: 500,
    PlatformType.FACEBOOK: 63206,
}


class ContentIdea(BaseModel):
    """A raw content idea submitted to the factory.

    The router uses this to decide which format(s) to produce.
    """

    model_config = {"extra": "forbid"}

    topic: str = Field(description="What the content is about")
    product: str = Field(
        default="none",
        description="Product to use as proof (pilaster | genpeli | invoz | none)",
    )
    source: str = Field(
        default="manual",
        description="Origin of the idea (manual | niche_research | analytics | strategy)",
    )
    priority: int = Field(
        default=2,
        ge=1,
        le=3,
        description="Priority level — 1 is highest, 3 is lowest",
    )
    format_hint: str | None = Field(
        default=None,
        description="Optional explicit format override (carousel | pdf | diagram | video_brief | text)",
    )
    content_pillar: str = Field(
        default="builder_stories",
        description="Authority pillar driving this idea",
    )
    notes: str = Field(
        default="",
        description="Any additional context for the specialist",
    )

    @field_validator("topic")
    @classmethod
    def _topic_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("topic must not be empty")
        return v

    @field_validator("product")
    @classmethod
    def _product_lowercase(cls, v: str) -> str:
        return v.lower().strip()


class PlatformAdaptation(BaseModel):
    """A piece of content adapted for a specific platform.

    Created by a platform framer after the specialist produces raw content.
    """

    model_config = {"extra": "forbid"}

    platform: PlatformType
    adapted_content: str = Field(description="Platform-ready text content")
    media_urls: list[str] = Field(
        default_factory=list,
        description="URLs of required media assets (images, videos, PDFs)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Platform-specific extras (e.g., slide_count, hashtags, language)",
    )
    char_count: int = Field(
        default=0,
        ge=0,
        description="Character count of adapted_content — computed on validation",
    )

    @model_validator(mode="after")
    def _compute_char_count(self) -> PlatformAdaptation:
        """Auto-compute char_count from adapted_content length."""
        if self.char_count == 0 and self.adapted_content:
            object.__setattr__(self, "char_count", len(self.adapted_content))
        return self


class ReviewResult(BaseModel):
    """Output from a single reviewer agent.

    Score is 0-100 (integer). Passed when score >= threshold (typically 70).
    """

    model_config = {"extra": "forbid"}

    reviewer_name: str = Field(
        description="Reviewer identity (brand | fact | compliance | engagement)"
    )
    score: int = Field(ge=0, le=100, description="Quality score from 0 to 100")
    passed: bool = Field(description="True when score meets the reviewer's pass threshold")
    issues: list[str] = Field(
        default_factory=list,
        description="Specific issues found during review",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Improvement suggestions from the reviewer",
    )
    reviewed_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 timestamp of when the review ran",
    )

    @field_validator("reviewer_name")
    @classmethod
    def _reviewer_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("reviewer_name must not be empty")
        return v


class ContentPiece(BaseModel):
    """A content piece produced by a specialist creator.

    ``raw_content`` holds the format-specific payload serialised as a JSON string.
    ``platform_adaptations`` holds per-platform versions of that content.
    ``review_scores`` accumulates reviewer results as the piece moves through eval.
    """

    model_config = {"extra": "forbid"}

    piece_id: str = Field(description="Unique identifier for this content piece")
    format: FormatType = Field(description="Content format produced by the specialist")
    idea: ContentIdea = Field(description="The source idea that led to this piece")
    raw_content: str = Field(
        description=(
            "Serialised JSON string containing the specialist output "
            "(slides for carousel, sections for PDF, mermaid for diagram, etc.)"
        )
    )
    platform_adaptations: list[PlatformAdaptation] = Field(
        default_factory=list,
        description="Per-platform adapted versions (populated by platform framers)",
    )
    review_scores: list[ReviewResult] = Field(
        default_factory=list,
        description="Review results from reviewer agents",
    )
    status: str = Field(
        default="draft",
        pattern="^(draft|reviewing|approved|rejected|published)$",
        description="Lifecycle status of this piece",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 timestamp of when this piece was created",
    )
    model_used: str = Field(
        default="",
        description="Claude model alias used to generate raw_content",
    )

    @field_validator("raw_content")
    @classmethod
    def _raw_content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_content must not be empty")
        return v

    @property
    def average_score(self) -> float | None:
        """Average review score across all reviewers, or None if no reviews yet."""
        if not self.review_scores:
            return None
        return sum(r.score for r in self.review_scores) / len(self.review_scores)

    @property
    def all_passed(self) -> bool:
        """True when every reviewer has passed this piece."""
        return bool(self.review_scores) and all(r.passed for r in self.review_scores)


class ContentBatch(BaseModel):
    """A batch of content pieces produced in a single factory run.

    Produced at the end of an ``act`` stage — contains all pieces created
    from a set of content ideas in one cycle.
    """

    model_config = {"extra": "forbid"}

    pieces: list[ContentPiece] = Field(description="All content pieces produced in this batch")
    strategy_reasoning: str = Field(
        description="Explanation of why these pieces were created (from the reason stage)"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 timestamp of when the batch was assembled",
    )

    @property
    def approved_pieces(self) -> list[ContentPiece]:
        """Subset of pieces that passed all reviews."""
        return [p for p in self.pieces if p.status == "approved"]

    @property
    def format_counts(self) -> dict[str, int]:
        """Count of pieces per format in this batch."""
        counts: dict[str, int] = {}
        for piece in self.pieces:
            counts[piece.format.value] = counts.get(piece.format.value, 0) + 1
        return counts
