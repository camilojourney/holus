"""Video content workflow using Genpeli REST API.

Orchestrates video content creation for the marketing agent:
  1. Resolve source footage from the asset library
  2. Submit processing job to Genpeli (cut silences, captions, audio)
  3. Poll for completion
  4. Return result for the video review queue

Genpeli runs as an independent silo at http://localhost:8100.
This module calls its REST API directly -- no wrapper code in Holus.
The MCP server (built in genpeli repo) is for Claude-level tool calls;
this module is for programmatic agent usage.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, Field

from holus.agents.marketing.models import ContentDecision, ContentType

if TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GENPELI_BASE_URL = "http://localhost:8100"
FOOTAGE_DIR = Path("data/footage")
MAX_PROCESSING_WAIT = 300  # 5 minutes
POLL_INTERVAL = 10  # seconds
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".webm", ".mkv"})

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class VideoJob(BaseModel):
    """Result of submitting a video processing job to Genpeli."""

    job_id: str = Field(description="Genpeli job identifier")
    status: str = Field(description="Job status: processing | ready_for_review | error")
    progress_percent: int = Field(default=0, ge=0, le=100)


class VideoResult(BaseModel):
    """Completed video ready for human review."""

    job_id: str = Field(description="Genpeli job identifier")
    preview_url: str = Field(description="URL to preview the processed video")
    status: str = Field(default="pending_review")
    decision: dict[str, Any] = Field(
        default_factory=dict,
        description="Serialised ContentDecision that triggered the video",
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class GenpeliUnavailableError(Exception):
    """Raised when the Genpeli service cannot be reached."""


class NoFootageError(Exception):
    """Raised when no source footage is available for the requested content."""


# ---------------------------------------------------------------------------
# Genpeli HTTP client
# ---------------------------------------------------------------------------


class GenpeliClient:
    """Async HTTP client for the Genpeli REST API.

    Follows the same context-manager pattern as LateAPIClient.
    """

    def __init__(
        self,
        base_url: str = GENPELI_BASE_URL,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
        )

    # -- Job submission ------------------------------------------------------

    async def submit_job(
        self,
        video_urls: list[str],
        instruction: str,
    ) -> VideoJob:
        """Submit a video processing job.

        Args:
            video_urls: Paths or URLs to source video files.
            instruction: Processing instruction for Genpeli pipeline.

        Returns:
            VideoJob with the new job's ID and initial status.

        Raises:
            GenpeliUnavailableError: If the API is unreachable or returns an error.
        """
        payload = {
            "video_urls": video_urls,
            "instruction": instruction,
        }
        try:
            response = await self._client.post("/v1/jobs", json=payload)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise GenpeliUnavailableError(
                f"Cannot connect to Genpeli at {self._client.base_url}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise GenpeliUnavailableError(
                f"Genpeli API error: {exc.response.status_code} {exc.response.text}"
            ) from exc

        data = response.json()
        return VideoJob(
            job_id=data["job_id"],
            status=data.get("status", "processing"),
            progress_percent=data.get("progress_percent", 0),
        )

    # -- Status polling ------------------------------------------------------

    async def check_status(self, job_id: str) -> VideoJob:
        """Check job status.

        Args:
            job_id: Genpeli job identifier.

        Returns:
            Updated VideoJob.
        """
        response = await self._client.get(f"/v1/jobs/{job_id}")
        response.raise_for_status()
        data = response.json()
        return VideoJob(
            job_id=job_id,
            status=data.get("status", "processing"),
            progress_percent=data.get("progress_percent", 0),
        )

    async def poll_until_ready(
        self,
        job_id: str,
        *,
        max_wait: int = MAX_PROCESSING_WAIT,
        poll_interval: int = POLL_INTERVAL,
    ) -> VideoJob:
        """Poll until the job is ready_for_review, errored, or timed out.

        Args:
            job_id: Genpeli job identifier.
            max_wait: Maximum seconds to wait.
            poll_interval: Seconds between status checks.

        Returns:
            VideoJob with terminal status.

        Raises:
            TimeoutError: If processing exceeds *max_wait*.
            ValueError: If the job enters an error state.
        """
        elapsed = 0
        while elapsed < max_wait:
            try:
                job = await self.check_status(job_id)
            except httpx.HTTPError as exc:
                logger.warning("Status check failed for job %s: %s", job_id, exc)
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                continue

            logger.info("Job %s: %s (%d%%)", job_id, job.status, job.progress_percent)

            if job.status == "ready_for_review":
                return job

            if job.status == "error":
                raise ValueError(f"Genpeli processing failed for job {job_id}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Video processing timed out after {max_wait}s for job {job_id}")

    # -- Preview retrieval ---------------------------------------------------

    async def get_preview_url(self, job_id: str) -> str:
        """Get the preview URL for a completed job.

        Args:
            job_id: Genpeli job identifier.

        Returns:
            Preview URL string.
        """
        response = await self._client.get(f"/v1/jobs/{job_id}/preview")
        response.raise_for_status()
        data = response.json()
        return str(data.get("preview_url", f"{self._client.base_url}/v1/jobs/{job_id}/preview"))

    # -- Approval / rejection ------------------------------------------------

    async def approve(self, job_id: str) -> dict[str, Any]:
        """Approve a video for delivery.

        Args:
            job_id: Genpeli job identifier.

        Returns:
            API response dict.
        """
        response = await self._client.post(f"/v1/jobs/{job_id}/approve")
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def reject(self, job_id: str, reason: str = "") -> dict[str, Any]:
        """Reject a video and clean up temp files.

        Args:
            job_id: Genpeli job identifier.
            reason: Human-readable rejection reason.

        Returns:
            API response dict.
        """
        response = await self._client.post(
            f"/v1/jobs/{job_id}/reject",
            json={"reason": reason},
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    # -- Context manager -----------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> GenpeliClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# Footage discovery
# ---------------------------------------------------------------------------


def find_source_footage(
    decision: ContentDecision,
    footage_dir: Path = FOOTAGE_DIR,
) -> list[str]:
    """Find source footage files matching a content decision.

    Searches ``footage_dir/{product}/`` for video files.

    Args:
        decision: Content decision with product info.
        footage_dir: Root directory containing per-product footage.

    Returns:
        Sorted list of absolute file paths (as strings).
    """
    if not footage_dir.exists():
        logger.warning("Footage directory does not exist: %s", footage_dir)
        return []

    product_dir = footage_dir / decision.product
    if not product_dir.exists():
        logger.warning("No footage directory for product %s at %s", decision.product, product_dir)
        return []

    footage = [
        str(f.resolve())
        for f in sorted(product_dir.iterdir())
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    ]

    if not footage:
        logger.warning("No video files found in %s", product_dir)

    return footage


# ---------------------------------------------------------------------------
# Instruction builder
# ---------------------------------------------------------------------------


def build_instruction(decision: ContentDecision) -> str:
    """Build a Genpeli processing instruction from a content decision.

    Args:
        decision: Content decision with topic and format context.

    Returns:
        Instruction string for Genpeli pipeline.
    """
    parts = ["Cut silences, add animated captions, normalize audio."]

    if decision.content_type is ContentType.VIDEO_REEL:
        parts.append("Format for short-form vertical video (9:16 aspect ratio).")

    if decision.platform.value in {"tiktok", "youtube", "instagram"}:
        parts.append("Keep under 60 seconds for maximum reach.")

    if decision.topic:
        parts.append(f"Topic context: {decision.topic}")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main workflow orchestrator
# ---------------------------------------------------------------------------


async def create_video_content(
    decision: ContentDecision,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    footage_dir: Path | None = None,
    max_wait: int = MAX_PROCESSING_WAIT,
    poll_interval: int = POLL_INTERVAL,
) -> VideoResult:
    """End-to-end video content creation workflow.

    Steps:
      1. Find source footage matching the decision's product.
      2. Submit processing job to Genpeli.
      3. Poll until the video is ready for review.
      4. Retrieve the preview URL.

    Args:
        decision: Content decision specifying product, topic, platform, etc.
        base_url: Override Genpeli API URL (default from env or constant).
        api_key: Override API key (default from GENPELI_API_KEY env var).
        footage_dir: Override footage directory.
        max_wait: Maximum seconds to wait for processing.
        poll_interval: Seconds between status polls.

    Returns:
        VideoResult with job_id, preview_url, and decision context.

    Raises:
        NoFootageError: If no source footage is found.
        GenpeliUnavailableError: If Genpeli is unreachable.
        TimeoutError: If processing exceeds *max_wait*.
        ValueError: If Genpeli reports a processing error.
    """
    resolved_url = base_url or os.environ.get("GENPELI_BASE_URL", GENPELI_BASE_URL)
    resolved_key = api_key or os.environ.get("GENPELI_API_KEY")
    resolved_dir = footage_dir or FOOTAGE_DIR

    # Step 1: find source footage
    source_files = find_source_footage(decision, resolved_dir)
    if not source_files:
        raise NoFootageError(f"No source footage for product={decision.product} in {resolved_dir}")

    instruction = build_instruction(decision)

    async with GenpeliClient(
        base_url=resolved_url,
        api_key=resolved_key,
    ) as client:
        # Step 2: submit job
        job = await client.submit_job(source_files, instruction)
        logger.info("Submitted Genpeli job %s for %s", job.job_id, decision.product)

        # Step 3: poll until ready
        job = await client.poll_until_ready(
            job.job_id,
            max_wait=max_wait,
            poll_interval=poll_interval,
        )

        # Step 4: get preview URL
        preview_url = await client.get_preview_url(job.job_id)

    return VideoResult(
        job_id=job.job_id,
        preview_url=preview_url,
        status="pending_review",
        decision=decision.model_dump(mode="json"),
    )
