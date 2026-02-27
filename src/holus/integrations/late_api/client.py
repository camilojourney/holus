"""Late API client for unified social media posting and analytics."""

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


class PostRequest(BaseModel):
    """Request to create a social media post."""

    text: str
    platforms: list[str]
    media_urls: list[str] = Field(default_factory=list)
    schedule_time: str | None = None  # ISO 8601
    platform_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)


class PostResult(BaseModel):
    """Result of a post creation request."""

    post_id: str
    platform_results: dict[str, dict[str, Any]]
    scheduled: bool
    failed_platforms: list[str]
    error_details: dict[str, str]


class AnalyticsData(BaseModel):
    """Analytics data for a social media post."""

    post_id: str
    platform: str
    impressions: int
    engagement_rate: float
    clicks: int
    shares: int
    comments: int
    follower_delta: int
    collected_at: str


PLATFORM_LIMITS = {
    "twitter": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "tiktok": 2200,
    "youtube": 5000,
    "bluesky": 300,
    "threads": 500,
    "mastodon": 500,
    "facebook": 63206,
    "pinterest": 500,
    "telegram": 4096,
    "discord": 2000,
    "reddit": 40000,
}


class LateAPIClient:
    """Client for the Late API (late.so) - unified social media posting."""

    BASE_URL = "https://getlate.dev/api/v1"

    def __init__(self, api_key: str):
        """Initialize the Late API client.

        Args:
            api_key: Late API key (from LATE_API_KEY env var)
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        self._account_cache: dict[str, str] = {}

    def validate_content(self, text: str, platforms: list[str]) -> list[str]:
        """Check text fits platform character limits.

        Args:
            text: Post content
            platforms: List of platform names

        Returns:
            List of violation messages (empty if valid)
        """
        violations = []
        for platform in platforms:
            limit = PLATFORM_LIMITS.get(platform.lower())
            if limit and len(text) > limit:
                violations.append(
                    f"{platform}: {len(text)} chars exceeds {limit} limit"
                )
        return violations

    async def get_accounts(self) -> dict[str, str]:
        """Fetch connected social media accounts.

        Returns:
            Dict mapping platform name to account ID
        """
        if self._account_cache:
            return self._account_cache

        response = await self.client.get("/accounts")
        response.raise_for_status()
        accounts = response.json()

        # Cache account IDs by platform
        for account in accounts:
            platform = account.get("platform", "").lower()
            account_id = account.get("_id")
            if platform and account_id:
                self._account_cache[platform] = account_id

        return self._account_cache

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def publish(self, request: PostRequest) -> PostResult:
        """Publish a post to one or more social media platforms.

        Args:
            request: Post request with content, platforms, and options

        Returns:
            Post result with IDs and per-platform status

        Raises:
            ValueError: If content violates platform limits
            httpx.HTTPError: If API request fails
        """
        # Validate content length
        violations = self.validate_content(request.text, request.platforms)
        if violations:
            raise ValueError(f"Content validation failed: {violations}")

        # Get account IDs for platforms
        accounts = await self.get_accounts()
        account_ids = []
        missing = []

        for platform in request.platforms:
            platform_lower = platform.lower()
            if platform_lower in accounts:
                account_ids.append(accounts[platform_lower])
            else:
                missing.append(platform)

        if missing:
            raise ValueError(
                f"No connected accounts for platforms: {missing}. "
                f"Connect them at https://getlate.dev/dashboard"
            )

        # Build request payload
        payload: dict[str, Any] = {
            "content": request.text,
            "accountIds": account_ids,
        }

        if request.schedule_time:
            payload["scheduledFor"] = request.schedule_time

        if request.media_urls:
            payload["media"] = request.media_urls

        if request.platform_overrides:
            payload["platformOverrides"] = request.platform_overrides

        # Make API call
        response = await self.client.post("/posts", json=payload)
        response.raise_for_status()
        data = response.json()

        # Parse response
        post_id = data.get("_id", "unknown")
        platform_results = data.get("platformResults", {})
        failed = [
            p for p, r in platform_results.items() if r.get("status") == "failed"
        ]
        errors = {
            p: r.get("error", "Unknown error")
            for p, r in platform_results.items()
            if r.get("status") == "failed"
        }

        return PostResult(
            post_id=post_id,
            platform_results=platform_results,
            scheduled=bool(request.schedule_time),
            failed_platforms=failed,
            error_details=errors,
        )

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def get_analytics(
        self, post_id: str, platform: str | None = None
    ) -> list[AnalyticsData]:
        """Get analytics for a specific post.

        Args:
            post_id: Post ID from publish result
            platform: Optional platform filter

        Returns:
            List of analytics data (one per platform if no filter)
        """
        params = {}
        if platform:
            params["platform"] = platform

        response = await self.client.get(f"/posts/{post_id}/analytics", params=params)
        response.raise_for_status()
        data = response.json()

        # Handle both list and dict responses
        if isinstance(data, dict):
            data = [data]

        return [AnalyticsData.model_validate(d) for d in data]

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def get_all_analytics(self, days: int = 7) -> list[AnalyticsData]:
        """Get analytics for all posts in a time period.

        Args:
            days: Number of days to look back

        Returns:
            List of analytics data for all posts
        """
        response = await self.client.get("/analytics", params={"days": days})
        response.raise_for_status()
        data = response.json()

        return [AnalyticsData.model_validate(d) for d in data]

    async def get_scheduled(self) -> list[dict[str, Any]]:
        """Get list of scheduled posts waiting to be published.

        Returns:
            List of scheduled post objects
        """
        response = await self.client.get("/posts", params={"status": "scheduled"})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise TypeError("Expected list response from /posts endpoint")

        scheduled: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                scheduled.append(item)

        return scheduled

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> LateAPIClient:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()
