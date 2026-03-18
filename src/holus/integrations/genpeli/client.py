"""Client for the genpeli video processing local API.

Calls the FastAPI server at http://localhost:8100 (or GENPELI_API_BASE_URL).
Handles video processing, status checking, preview, approval, and rejection.

The server accepts POST /api/v1/process and returns 202 Accepted with a
job_id and status. Processing is async on the server side.
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


class ProcessVideoRequest(BaseModel):
    """Request to process video via genpeli."""

    video_urls: list[str]
    instruction: str


class VideoJob(BaseModel):
    """Result from submitting a video processing job."""

    job_id: str
    status: str = "queued"  # queued|processing|completed|failed
    message: str | None = None


class VideoStatus(BaseModel):
    """Status of a video processing job."""

    job_id: str
    status: str  # queued|processing|completed|failed
    progress: float = 0.0  # 0.0-1.0
    output_url: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """True if the job has finished (success or failure)."""
        return self.status in ("completed", "failed")

    @property
    def succeeded(self) -> bool:
        """True if the job completed successfully."""
        return self.status == "completed"


class PreviewResult(BaseModel):
    """Preview of a processed video before approval."""

    job_id: str
    preview_url: str
    duration_seconds: float = 0.0
    resolution: str | None = None
    thumbnail_url: str | None = None


class ApprovalResult(BaseModel):
    """Result of approving a processed video."""

    job_id: str
    status: str  # approved
    final_url: str
    message: str | None = None


class RejectionResult(BaseModel):
    """Result of rejecting a processed video."""

    job_id: str
    status: str  # rejected
    reason: str
    message: str | None = None


class GenpeliClient:
    """Async client for the genpeli video processing API."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8100",
        api_key: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": api_key},
            timeout=30.0,
        )

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def process_video(
        self,
        video_urls: list[str],
        instruction: str,
    ) -> VideoJob:
        """Submit a video processing job.

        Calls POST /api/v1/process on the genpeli server.
        Returns a VideoJob with the job_id and initial status.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        payload: dict[str, Any] = {
            "video_urls": video_urls,
            "instruction": instruction,
        }
        response = await self.client.post("/api/v1/process", json=payload)
        response.raise_for_status()
        data = response.json()
        return VideoJob.model_validate(data)

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def check_status(self, job_id: str) -> VideoStatus:
        """Check the status of a video processing job.

        Calls GET /api/v1/jobs/{job_id}/status.
        """
        response = await self.client.get(f"/api/v1/jobs/{job_id}/status")
        response.raise_for_status()
        data = response.json()
        return VideoStatus.model_validate(data)

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def get_preview(self, job_id: str) -> PreviewResult:
        """Get the preview of a processed video.

        Calls GET /api/v1/jobs/{job_id}/preview.
        """
        response = await self.client.get(f"/api/v1/jobs/{job_id}/preview")
        response.raise_for_status()
        data = response.json()
        return PreviewResult.model_validate(data)

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def approve(self, job_id: str) -> ApprovalResult:
        """Approve a processed video for final delivery.

        Calls POST /api/v1/jobs/{job_id}/approve.
        """
        response = await self.client.post(f"/api/v1/jobs/{job_id}/approve")
        response.raise_for_status()
        data = response.json()
        return ApprovalResult.model_validate(data)

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def reject(self, job_id: str, reason: str) -> RejectionResult:
        """Reject a processed video with a reason.

        Calls POST /api/v1/jobs/{job_id}/reject.
        """
        payload: dict[str, Any] = {"reason": reason}
        response = await self.client.post(
            f"/api/v1/jobs/{job_id}/reject", json=payload
        )
        response.raise_for_status()
        data = response.json()
        return RejectionResult.model_validate(data)

    async def health(self) -> dict[str, Any]:
        """Check genpeli API health.

        Calls GET /api/v1/health.
        """
        response = await self.client.get("/api/v1/health")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> GenpeliClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
