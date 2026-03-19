"""Client for the social-media-automatization local API.

Calls the FastAPI server at http://localhost:8000 (or SOCIAL_MEDIA_API_BASE_URL).
Handles publishing, analytics, and top-posts queries.

The server accepts POST /api/publish and returns 202 Accepted with a
publish_id and per-target status. Publishing is async on the server side.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import TracebackType

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Character limits per platform (same as the social-media API enforces).
PLATFORM_CHAR_LIMITS: dict[str, int] = {
    "twitter": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "facebook": 63206,
    "threads": 500,
}

# Valid platforms the social-media API supports.
VALID_PLATFORMS = frozenset(PLATFORM_CHAR_LIMITS)


class PublishRequest(BaseModel):
    """Request to publish content via social-media-automatization."""

    content: str
    platforms: list[str]
    style: str = "raw"  # raw|polished|enhanced|platform_native
    media_url: str | None = None
    media_type: str | None = None  # image|video
    bilingual: bool = False
    source_language: str = "en"


class ScheduleRequest(BaseModel):
    """Request to schedule content for later publishing with approval gate."""

    content: str
    platform: str
    approval_required: bool = True
    scheduled_at: str | None = None  # ISO-8601 timestamp
    media_url: str | None = None
    media_type: str | None = None


class ScheduleResult(BaseModel):
    """Result from the schedule endpoint."""

    schedule_id: str
    status: str = "pending_approval"  # pending_approval|scheduled|published|rejected
    platform: str = ""
    approval_required: bool = True


class PublishTarget(BaseModel):
    """Per-target status returned by the publish API."""

    platform: str
    account: str = ""
    language: str = "en"
    status: str = "queued"  # queued|published|failed
    error: str | None = None
    job_id: int | None = None


class PublishResult(BaseModel):
    """Result from the social-media publish endpoint."""

    publish_id: str
    targets: list[PublishTarget] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    en_content: str | None = None
    es_content: str | None = None

    @property
    def failed_targets(self) -> list[PublishTarget]:
        """Return targets that failed to publish."""
        return [t for t in self.targets if t.status == "failed"]

    @property
    def succeeded(self) -> bool:
        """True if no targets failed."""
        return len(self.failed_targets) == 0


class SocialMediaClient:
    """Async client for the social-media-automatization API."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8000",
        api_key: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": api_key},
            timeout=30.0,
        )

    def validate_content(self, text: str, platforms: list[str]) -> list[str]:
        """Check text fits platform character limits.

        Returns list of violation messages (empty if valid).
        """
        violations = []
        for platform in platforms:
            p = platform.lower()
            limit = PLATFORM_CHAR_LIMITS.get(p)
            if limit and len(text) > limit:
                violations.append(f"{platform}: {len(text)} chars exceeds {limit} limit")
        return violations

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish content to social media platforms.

        Calls POST /api/publish on the social-media-automatization server.
        Returns a PublishResult with per-target status.

        Raises:
            ValueError: If content violates platform limits.
            httpx.HTTPError: If the API request fails.
        """
        # Validate content length
        violations = self.validate_content(request.content, request.platforms)
        if violations:
            raise ValueError(f"Content validation failed: {violations}")

        # Build payload — only include fields the API accepts
        payload: dict[str, Any] = {
            "content": request.content,
        }
        if request.platforms:
            payload["platforms"] = request.platforms
        if request.media_url:
            payload["media_url"] = request.media_url
        if request.media_type:
            payload["media_type"] = request.media_type

        response = await self.client.post("/api/v1/publish", json=payload)
        response.raise_for_status()
        data = response.json()

        # API wraps response in {"status": "ok", "data": {...}}
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        return PublishResult.model_validate(data)

    async def get_status(self, publish_id: str) -> PublishResult:
        """Check the status of a publish operation.

        Calls GET /api/publish/{publish_id}.
        """
        response = await self.client.get(f"/api/publish/{publish_id}")
        response.raise_for_status()
        data = response.json()
        return PublishResult.model_validate(data)

    async def health(self) -> dict[str, Any]:
        """Check platform health / connection status.

        Calls GET /health.
        """
        response = await self.client.get("/api/v1/health")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def get_analytics(
        self,
        *,
        days: int = 7,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Fetch publishing analytics for recent posts.

        Calls GET /api/analytics on the social-media-automatization server.
        Returns summary stats: total posts, success rates, per-platform breakdowns.
        """
        params: dict[str, Any] = {"days": days}
        if platform:
            params["platform"] = platform
        response = await self.client.get("/api/v1/analytics", params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def get_post_analytics(
        self,
        post_id: str,
    ) -> dict[str, Any]:
        """Fetch latest engagement snapshot for a specific published post.

        Calls GET /api/v1/analytics/posts/{post_id}/latest on social-media API.
        Returns: {views, likes, comments, shares, saves, engagement_rate, ...}
        """
        response = await self.client.get(f"/api/v1/analytics/posts/{post_id}/latest")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def get_top_posts(
        self,
        *,
        limit: int = 10,
        days: int = 30,
        metric: str = "recent",
    ) -> dict[str, Any]:
        """Fetch top performing published posts.

        Calls GET /api/analytics/top-posts on the social-media-automatization server.
        Returns posts sorted by the given metric.
        """
        params: dict[str, Any] = {"limit": limit, "days": days, "metric": metric}
        response = await self.client.get("/api/v1/analytics/top-posts", params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def schedule_post(
        self,
        request: ScheduleRequest,
    ) -> ScheduleResult:
        """Schedule content for publishing with an approval gate.

        Calls POST /api/v1/schedule on the social-media-automatization server.
        Posts with approval_required=True wait for human approval before publishing.

        Raises:
            ValueError: If content violates platform character limits.
            httpx.HTTPError: If the API request fails.
        """
        violations = self.validate_content(request.content, [request.platform])
        if violations:
            raise ValueError(f"Content validation failed: {violations}")

        payload: dict[str, Any] = {
            "content": request.content,
            "platform": request.platform,
            "approval_required": request.approval_required,
        }
        if request.scheduled_at:
            payload["scheduled_at"] = request.scheduled_at
        if request.media_url:
            payload["media_url"] = request.media_url
        if request.media_type:
            payload["media_type"] = request.media_type

        response = await self.client.post("/api/v1/schedule", json=payload)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        return ScheduleResult.model_validate(data)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> SocialMediaClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
