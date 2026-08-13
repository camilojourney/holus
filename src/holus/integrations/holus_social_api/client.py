"""Client for the Holus Social API.

Holus Social API is the publishing and analytics boundary for social platforms.
Legacy publishing API environment variables remain supported as compatibility
aliases while callers migrate.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, Field, model_validator
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from types import TracebackType

HOLUS_SOCIAL_API_BASE_URL_ENV = "HOLUS_SOCIAL_API_BASE_URL"
HOLUS_SOCIAL_API_KEY_ENV = "HOLUS_SOCIAL_API_KEY"
LEGACY_BASE_URL_ENV = "SOCIAL_MEDIA_API_BASE_URL"
LEGACY_API_KEY_ENV = "POSTING_API_KEY"

PLATFORM_CHAR_LIMITS: dict[str, int] = {
    "twitter": 280,
    "twitter_x": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "facebook": 63206,
    "threads": 500,
}

VALID_PLATFORMS = frozenset(PLATFORM_CHAR_LIMITS)

_RETRY_ON_HTTP_ERROR = retry(
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3),
    reraise=True,
)


def resolve_base_url(base_url: str | None = None) -> str:
    """Resolve Holus Social API base URL with legacy fallback."""
    return (
        base_url
        or os.getenv(HOLUS_SOCIAL_API_BASE_URL_ENV)
        or os.getenv(LEGACY_BASE_URL_ENV)
        or "http://localhost:8000"
    ).rstrip("/")


def resolve_api_key(api_key: str | None = None) -> str:
    """Resolve Holus Social API key with legacy fallback."""
    return api_key or os.getenv(HOLUS_SOCIAL_API_KEY_ENV) or os.getenv(LEGACY_API_KEY_ENV) or ""


def normalize_platform(platform: str) -> str:
    """Normalize Holus platform labels to the Holus Social API labels."""
    if platform == "twitter_x":
        return "twitter"
    return platform


def _unwrap_envelope(data: Any) -> Any:
    """Unwrap {"status": "ok", "data": {...}} responses when present."""
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def _with_optional_media(
    payload: dict[str, Any],
    *,
    media_url: str | None,
    media_type: str | None,
) -> dict[str, Any]:
    if media_url:
        payload["media_url"] = media_url
    if media_type:
        payload["media_type"] = media_type
    return payload


class PublishRequest(BaseModel):
    """Request to publish content via Holus Social API."""

    content: str
    platforms: list[str]
    style: str = "raw"
    media_url: str | None = None
    media_type: str | None = None
    bilingual: bool = False
    source_language: str = "en"
    idempotency_key: str | None = None


class ScheduleRequest(BaseModel):
    """Request to schedule content through Holus Social API."""

    content: str
    platforms: list[str] | None = None
    platform: str | None = None
    approval_required: bool = True
    scheduled_at: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def normalize_platforms(self) -> ScheduleRequest:
        """Support legacy platform= while preferring platforms=[...]."""
        if self.platforms:
            self.platforms = [normalize_platform(platform) for platform in self.platforms]
            self.platform = self.platform or self.platforms[0]
            return self
        if self.platform:
            normalized = normalize_platform(self.platform)
            self.platform = normalized
            self.platforms = [normalized]
            return self
        msg = "ScheduleRequest requires platform or platforms"
        raise ValueError(msg)


class ScheduleResult(BaseModel):
    """Result from the Holus Social API schedule endpoint."""

    schedule_id: str
    status: str = "pending_approval"
    platform: str = ""
    approval_required: bool = True


class PublishTarget(BaseModel):
    """Per-platform publish status returned by Holus Social API."""

    platform: str
    account: str = ""
    language: str = "en"
    status: str = "queued"
    error: str | None = None
    job_id: int | None = None


class PublishResult(BaseModel):
    """Result from the Holus Social API publish endpoint."""

    publish_id: str
    targets: list[PublishTarget] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    en_content: str | None = None
    es_content: str | None = None

    @property
    def failed_targets(self) -> list[PublishTarget]:
        return [target for target in self.targets if target.status == "failed"]

    @property
    def succeeded(self) -> bool:
        return not self.failed_targets


class HolusSocialAPIClient:
    """Async client for the Holus Social API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = resolve_base_url(base_url)
        self.api_key = resolve_api_key(api_key)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=30.0,
        )

    def validate_content(self, text: str, platforms: list[str]) -> list[str]:
        """Check text fits platform character limits."""
        violations = []
        for platform in platforms:
            normalized = normalize_platform(platform.lower())
            limit = PLATFORM_CHAR_LIMITS.get(normalized)
            if limit and len(text) > limit:
                violations.append(f"{platform}: {len(text)} chars exceeds {limit} limit")
        return violations

    def _ensure_valid_content(self, content: str, platforms: list[str]) -> None:
        violations = self.validate_content(content, platforms)
        if violations:
            raise ValueError(f"Content validation failed: {violations}")

    async def _get_json(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if params is None:
            response = await self.client.get(path)
        else:
            response = await self.client.get(path, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def _post_json(
        self, path: str, payload: dict[str, Any], *, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        response = await self.client.post(path, json=payload, headers=headers)
        response.raise_for_status()
        data = _unwrap_envelope(response.json())
        if not isinstance(data, dict):
            msg = f"Expected object response from Holus Social API {path}"
            raise ValueError(msg)
        return data

    @_RETRY_ON_HTTP_ERROR
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish content through Holus Social API."""
        platforms = [normalize_platform(platform) for platform in request.platforms]
        self._ensure_valid_content(request.content, platforms)

        payload = _with_optional_media(
            {"content": request.content, "platforms": platforms},
            media_url=request.media_url,
            media_type=request.media_type,
        )
        return PublishResult.model_validate(
            await self._post_json(
                "/api/v1/publish", payload, idempotency_key=request.idempotency_key
            )
        )

    async def get_status(self, publish_id: str) -> PublishResult:
        """Check a publish operation status."""
        response = await self.client.get(f"/api/publish/{publish_id}")
        response.raise_for_status()
        return PublishResult.model_validate(response.json())

    async def health(self) -> dict[str, Any]:
        """Check Holus Social API health."""
        return await self._get_json("/api/v1/health")

    async def get_analytics(
        self,
        *,
        days: int = 7,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Fetch publishing analytics for recent posts."""
        params: dict[str, Any] = {"days": days}
        if platform:
            params["platform"] = normalize_platform(platform)
        return await self._get_json("/api/v1/analytics", params=params)

    async def get_post_analytics(self, post_id: str) -> dict[str, Any]:
        """Fetch the latest engagement snapshot for one published post."""
        return await self._get_json(f"/api/v1/analytics/posts/{post_id}/latest")

    async def get_top_posts(
        self,
        *,
        limit: int = 10,
        days: int = 30,
        metric: str = "recent",
    ) -> dict[str, Any]:
        """Fetch top performing published posts."""
        params: dict[str, Any] = {"limit": limit, "days": days, "metric": metric}
        return await self._get_json("/api/v1/analytics/top-posts", params=params)

    @_RETRY_ON_HTTP_ERROR
    async def schedule_post(self, request: ScheduleRequest) -> ScheduleResult:
        """Schedule content through Holus Social API."""
        platforms = request.platforms or ([request.platform] if request.platform else [])
        platforms = [normalize_platform(platform) for platform in platforms]
        self._ensure_valid_content(request.content, platforms)

        payload = _with_optional_media(
            {
                "content": request.content,
                "platforms": platforms,
                "approval_required": request.approval_required,
            },
            media_url=request.media_url,
            media_type=request.media_type,
        )
        if request.scheduled_at:
            payload["scheduled_at"] = request.scheduled_at

        return ScheduleResult.model_validate(
            await self._post_json(
                "/api/v1/schedule", payload, idempotency_key=request.idempotency_key
            )
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> HolusSocialAPIClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
