"""Shared data models for HOLUS."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ContentType(Enum):
    VIDEO = "video"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    CAROUSEL = "carousel"


class FunnelStage(Enum):
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    CONVERSION = "conversion"


class Platform(Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    DISCORD = "discord"
    REDDIT = "reddit"


@dataclass
class ContentItem:
    """Universal content representation."""
    id: str
    type: ContentType
    title: str
    body: str
    media_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    funnel_stage: FunnelStage = FunnelStage.AWARENESS
    target_platforms: list[Platform] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PublishResult:
    """Result of publishing to a platform."""
    success: bool
    platform: Platform
    content_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    published_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class Analytics:
    """Analytics data from a platform."""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_seconds: int = 0
    retention_rate: float = 0.0
    ctr: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Message for inter-agent communication."""
    from_agent: str
    to_agent: str
    action: str
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
