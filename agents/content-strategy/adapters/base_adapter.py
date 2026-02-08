"""Base adapter interface for platform integrations."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ContentType(Enum):
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"
    CAROUSEL = "carousel"


@dataclass
class Content:
    """Content to be published."""
    type: ContentType
    title: str
    body: str
    media_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class PublishResult:
    """Result of a publish operation."""
    success: bool
    platform: str
    content_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Analytics:
    """Analytics data for published content."""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_seconds: int = 0
    retention_rate: float = 0.0
    ctr: float = 0.0
    metadata: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """Base class for all platform adapters."""
    
    platform: str  # e.g., "youtube", "tiktok"
    content_types: list[ContentType]  # Supported content types
    
    def __init__(self, config: dict):
        self.config = config
        self._authenticated = False
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with platform. Returns success status."""
        ...
    
    @abstractmethod
    async def publish(self, content: Content) -> PublishResult:
        """Publish content to platform."""
        ...
    
    @abstractmethod
    async def get_analytics(self, content_id: str) -> Analytics:
        """Fetch analytics for published content."""
        ...
    
    @abstractmethod
    def adapt_content(self, content: Content) -> Content:
        """Transform content to meet platform requirements."""
        ...
    
    @abstractmethod
    def validate_content(self, content: Content) -> tuple[bool, list[str]]:
        """Validate content meets platform requirements. Returns (valid, errors)."""
        ...
    
    async def pre_publish(self, content: Content) -> Content:
        """Hook before publishing. Override for platform-specific prep."""
        return content
    
    async def post_publish(self, result: PublishResult) -> None:
        """Hook after publishing. Override for tracking, notifications."""
        pass
