"""Content Factory v2 — multi-format content creation pipeline.

This package provides the ContentRouter, specialist creators, and supporting
models for producing structured content across multiple formats (carousel, PDF,
diagram, video brief, text) and platforms.

See specs/024-content-factory.md for the full design.
"""

from .models import (
    ContentBatch,
    ContentIdea,
    ContentPiece,
    FormatType,
    PlatformAdaptation,
    PlatformType,
    ReviewResult,
)
from .router import ContentRouter

__all__ = [
    "ContentBatch",
    "ContentIdea",
    "ContentPiece",
    "ContentRouter",
    "FormatType",
    "PlatformAdaptation",
    "PlatformType",
    "ReviewResult",
]
