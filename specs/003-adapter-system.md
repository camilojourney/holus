# SPEC-003: Platform Adapter System

## Overview
Design and implement a pluggable adapter system that encapsulates platform-specific logic, enabling easy addition/removal of platforms without changing publisher code.

## Design Principles
1. **Single Responsibility**: Each adapter handles ONE platform
2. **Pluggable**: Add new platforms via config, no code changes to publishers
3. **Fail-Safe**: Adapter failures don't crash the publisher
4. **Testable**: Mock adapters for testing without API calls

## Base Adapter Interface

```python
# adapters/base_adapter.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class ContentType(Enum):
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"
    CAROUSEL = "carousel"

@dataclass
class Content:
    type: ContentType
    title: str
    body: str
    media_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    tags: list[str] = None
    metadata: dict = None

@dataclass
class PublishResult:
    success: bool
    platform: str
    content_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: dict = None

@dataclass
class Analytics:
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_seconds: int = 0
    retention_rate: float = 0.0
    ctr: float = 0.0
    metadata: dict = None

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
    
    # Optional hooks
    async def pre_publish(self, content: Content) -> Content:
        """Hook before publishing. Override for platform-specific prep."""
        return content
    
    async def post_publish(self, result: PublishResult) -> None:
        """Hook after publishing. Override for tracking, notifications."""
        pass
```

## Platform Adapters

### YouTube Adapter
```python
# adapters/youtube_adapter.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class YouTubeAdapter(BaseAdapter):
    platform = "youtube"
    content_types = [ContentType.VIDEO]
    
    # Platform constraints
    MAX_TITLE_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_TAGS = 500  # characters total
    ASPECT_RATIO = "16:9"
    
    async def authenticate(self) -> bool:
        creds = Credentials.from_authorized_user_file(
            self.config["credentials_path"]
        )
        self.service = build("youtube", "v3", credentials=creds)
        self._authenticated = True
        return True
    
    def adapt_content(self, content: Content) -> Content:
        # Truncate title if needed
        if len(content.title) > self.MAX_TITLE_LENGTH:
            content.title = content.title[:97] + "..."
        
        # Format description with chapters if provided
        if content.metadata and "chapters" in content.metadata:
            chapters = "\n".join(
                f"{c['time']} {c['title']}" 
                for c in content.metadata["chapters"]
            )
            content.body = f"{content.body}\n\nChapters:\n{chapters}"
        
        return content
    
    def validate_content(self, content: Content) -> tuple[bool, list[str]]:
        errors = []
        if content.type != ContentType.VIDEO:
            errors.append(f"YouTube only supports VIDEO, got {content.type}")
        if not content.media_path:
            errors.append("Video file path required")
        if len(content.title) > self.MAX_TITLE_LENGTH:
            errors.append(f"Title exceeds {self.MAX_TITLE_LENGTH} chars")
        return (len(errors) == 0, errors)
    
    async def publish(self, content: Content) -> PublishResult:
        try:
            content = await self.pre_publish(content)
            content = self.adapt_content(content)
            
            valid, errors = self.validate_content(content)
            if not valid:
                return PublishResult(
                    success=False, 
                    platform=self.platform,
                    error="; ".join(errors)
                )
            
            media = MediaFileUpload(content.media_path, resumable=True)
            request = self.service.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": content.title,
                        "description": content.body,
                        "tags": content.tags or [],
                        "categoryId": self.config.get("category_id", "28"),
                    },
                    "status": {
                        "privacyStatus": self.config.get("privacy", "public"),
                    },
                },
                media_body=media,
            )
            response = request.execute()
            
            result = PublishResult(
                success=True,
                platform=self.platform,
                content_id=response["id"],
                url=f"https://youtube.com/watch?v={response['id']}",
                metadata=response,
            )
            await self.post_publish(result)
            return result
            
        except Exception as e:
            return PublishResult(
                success=False,
                platform=self.platform,
                error=str(e),
            )
    
    async def get_analytics(self, content_id: str) -> Analytics:
        response = self.service.videos().list(
            part="statistics",
            id=content_id,
        ).execute()
        
        stats = response["items"][0]["statistics"]
        return Analytics(
            views=int(stats.get("viewCount", 0)),
            likes=int(stats.get("likeCount", 0)),
            comments=int(stats.get("commentCount", 0)),
        )
```

### TikTok Adapter
```python
# adapters/tiktok_adapter.py
class TikTokAdapter(BaseAdapter):
    platform = "tiktok"
    content_types = [ContentType.VIDEO]
    
    # Platform constraints
    MAX_DURATION_SECONDS = 600  # 10 minutes
    MAX_CAPTION_LENGTH = 2200
    ASPECT_RATIO = "9:16"
    MAX_HASHTAGS = 5
    
    def adapt_content(self, content: Content) -> Content:
        # Add trending hashtags
        if self.config.get("auto_hashtags"):
            trending = self._get_trending_hashtags(content.tags)
            content.tags = (content.tags or []) + trending[:self.MAX_HASHTAGS]
        
        # Truncate caption
        if len(content.body) > self.MAX_CAPTION_LENGTH:
            content.body = content.body[:self.MAX_CAPTION_LENGTH - 3] + "..."
        
        return content
    
    def _get_trending_hashtags(self, seed_tags: list[str]) -> list[str]:
        # TODO: Implement trending hashtag lookup
        return ["#fyp", "#viral"]
```

### Twitter/X Adapter
```python
# adapters/twitter_adapter.py
class TwitterAdapter(BaseAdapter):
    platform = "twitter"
    content_types = [ContentType.TEXT, ContentType.VIDEO, ContentType.IMAGE]
    
    MAX_TWEET_LENGTH = 280
    MAX_THREAD_LENGTH = 25
    MAX_VIDEO_DURATION = 140  # seconds
    
    def adapt_content(self, content: Content) -> Content:
        # Convert long text to thread
        if content.type == ContentType.TEXT and len(content.body) > self.MAX_TWEET_LENGTH:
            content.metadata = content.metadata or {}
            content.metadata["thread"] = self._split_into_thread(content.body)
        
        return content
    
    def _split_into_thread(self, text: str) -> list[str]:
        """Split long text into tweet-sized chunks."""
        tweets = []
        words = text.split()
        current_tweet = ""
        
        for word in words:
            if len(current_tweet) + len(word) + 1 <= self.MAX_TWEET_LENGTH - 5:  # Reserve for numbering
                current_tweet += (" " if current_tweet else "") + word
            else:
                tweets.append(current_tweet)
                current_tweet = word
        
        if current_tweet:
            tweets.append(current_tweet)
        
        # Add numbering
        total = len(tweets)
        return [f"{t} ({i+1}/{total})" for i, t in enumerate(tweets)]
```

## Adapter Registry

```python
# adapters/__init__.py
from typing import Type
from .base_adapter import BaseAdapter
from .youtube_adapter import YouTubeAdapter
from .tiktok_adapter import TikTokAdapter
from .twitter_adapter import TwitterAdapter

ADAPTER_REGISTRY: dict[str, Type[BaseAdapter]] = {
    "youtube": YouTubeAdapter,
    "tiktok": TikTokAdapter,
    "twitter": TwitterAdapter,
    # Add more as implemented
}

def get_adapter(platform: str, config: dict) -> BaseAdapter:
    """Factory function to get adapter instance."""
    if platform not in ADAPTER_REGISTRY:
        raise ValueError(f"Unknown platform: {platform}")
    return ADAPTER_REGISTRY[platform](config)

def list_adapters() -> list[str]:
    """List all available adapters."""
    return list(ADAPTER_REGISTRY.keys())
```

## Publisher Integration

```python
# publishers/video_publisher.py
class VideoPublisher(BaseAgent):
    name = "video_publisher"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adapters = self._load_adapters()
    
    def _load_adapters(self) -> dict[str, BaseAdapter]:
        """Load adapters for enabled platforms."""
        adapters = {}
        for platform, config in self.config.get("platforms", {}).items():
            if config.get("enabled", True):
                try:
                    adapters[platform] = get_adapter(platform, config)
                except Exception as e:
                    logger.warning(f"Failed to load {platform} adapter: {e}")
        return adapters
    
    async def publish_to_all(self, content: Content) -> dict[str, PublishResult]:
        """Publish content to all enabled platforms."""
        results = {}
        for platform, adapter in self.adapters.items():
            if content.type in adapter.content_types:
                results[platform] = await adapter.publish(content)
            else:
                results[platform] = PublishResult(
                    success=False,
                    platform=platform,
                    error=f"Content type {content.type} not supported",
                )
        return results
```

## Testing Strategy

```python
# adapters/mock_adapter.py
class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""
    platform = "mock"
    content_types = list(ContentType)
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.published = []
        self.should_fail = config.get("should_fail", False)
    
    async def authenticate(self) -> bool:
        return not self.should_fail
    
    async def publish(self, content: Content) -> PublishResult:
        if self.should_fail:
            return PublishResult(success=False, platform=self.platform, error="Mock failure")
        self.published.append(content)
        return PublishResult(
            success=True,
            platform=self.platform,
            content_id=f"mock-{len(self.published)}",
            url="https://mock.test/content",
        )
```

## Acceptance Criteria
- [ ] Base adapter interface defined
- [ ] YouTube adapter publishes videos
- [ ] TikTok adapter handles 9:16 conversion
- [ ] Twitter adapter creates threads
- [ ] Adapter registry works
- [ ] Mock adapter enables testing
- [ ] Publishers use adapters correctly
- [ ] Config-driven platform enable/disable

## Timeline
- Base adapter + registry: 2 hours
- YouTube adapter: 4 hours
- TikTok adapter: 4 hours
- Twitter adapter: 3 hours
- Mock adapter + tests: 2 hours
- **Total: 15 hours**
