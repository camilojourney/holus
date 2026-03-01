"""Image content workflow using Pilaster REST API.

Orchestrates image content creation for the marketing agent:
  1. Search past experiments for the content style
  2. Build an informed prompt using successful patterns
  3. Submit a generation job to Pilaster
  4. Poll for completion
  5. Return result for the content review queue

Pilaster runs as an independent silo (Next.js app + Supabase).
This module calls its REST API directly -- no wrapper code in Holus.
The MCP server (built in pilaster repo) is for Claude-level tool calls;
this module is for programmatic agent usage.
"""

from __future__ import annotations

import asyncio
import logging
import os
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

PILASTER_BASE_URL = "http://localhost:3000"
MAX_GENERATION_WAIT = 120  # 2 minutes
POLL_INTERVAL = 5  # seconds
DEFAULT_QUALITY_THRESHOLD = 7.0

# Map content types to search queries for finding relevant experiments.
CONTENT_TYPE_QUERIES: dict[str, str] = {
    "tutorial": "tutorial screenshot walkthrough",
    "demo": "demo product preview",
    "tips": "tip illustration graphic",
    "case_study": "case study comparison",
    "carousel": "carousel slide graphic",
    "announcement": "announcement banner graphic",
    "educational": "educational diagram infographic",
}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ExperimentMatch(BaseModel):
    """A past experiment returned by Pilaster search."""

    snapshot_id: str = Field(description="Pilaster snapshot identifier")
    project_name: str = Field(default="")
    version_name: str = Field(default="")
    intent: str = Field(default="", description="What the experiment was trying to achieve")
    outcome: str | None = Field(default=None, description="worked | mixed | failed | null")
    outcome_note: str | None = Field(default=None)
    image_url: str | None = Field(default=None, description="URL to generated image if available")
    rank: float = Field(default=0.0, description="Search relevance score")


class RenderJob(BaseModel):
    """Status of a Pilaster render/generation job."""

    run_id: str = Field(description="Pilaster run identifier")
    status: str = Field(description="pending | processing | succeeded | failed | cancelled")
    result_url: str | None = Field(default=None, description="URL to generated image")


class ImageResult(BaseModel):
    """Completed image ready for human review."""

    image_url: str = Field(description="URL to the generated image")
    prompt_used: str = Field(default="", description="The prompt that produced this image")
    run_id: str = Field(default="", description="Pilaster run identifier")
    status: str = Field(default="pending_review")
    learned_from: int = Field(
        default=0, description="Number of past experiments used to inform prompt"
    )
    decision: dict[str, Any] = Field(
        default_factory=dict,
        description="Serialised ContentDecision that triggered the image",
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PilasterUnavailableError(Exception):
    """Raised when the Pilaster service cannot be reached."""


class GenerationFailedError(Exception):
    """Raised when image generation fails."""


# ---------------------------------------------------------------------------
# Pilaster HTTP client
# ---------------------------------------------------------------------------


class PilasterClient:
    """Async HTTP client for the Pilaster REST API.

    Follows the same context-manager pattern as GenpeliClient.
    """

    def __init__(
        self,
        base_url: str = PILASTER_BASE_URL,
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

    # -- Search experiments ---------------------------------------------------

    async def search_experiments(
        self,
        query: str = "",
        outcome: str | None = None,
        limit: int = 10,
    ) -> list[ExperimentMatch]:
        """Search past generation experiments in Pilaster.

        Args:
            query: Free text search (searches intent + version_name).
            outcome: Filter by outcome: worked | mixed | failed.
            limit: Maximum results to return.

        Returns:
            List of matching experiments, sorted by relevance.

        Raises:
            PilasterUnavailableError: If the API is unreachable.
        """
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["query"] = query
        if outcome:
            params["outcome"] = outcome

        try:
            response = await self._client.get("/api/search", params=params)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise PilasterUnavailableError(
                f"Cannot connect to Pilaster at {self._client.base_url}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise PilasterUnavailableError(
                f"Pilaster API error: {exc.response.status_code} {exc.response.text}"
            ) from exc

        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        return [
            ExperimentMatch(
                snapshot_id=r.get("id", r.get("snapshot_id", "")),
                project_name=r.get("project_name", ""),
                version_name=r.get("version_name", ""),
                intent=r.get("intent", ""),
                outcome=r.get("outcome"),
                outcome_note=r.get("outcome_note"),
                image_url=r.get("run_image_url", r.get("image_url")),
                rank=r.get("rank", 0.0),
            )
            for r in results
        ]

    # -- Image generation -----------------------------------------------------

    async def generate_image(self, snapshot_id: str) -> RenderJob:
        """Submit a generation job for a saved snapshot.

        Args:
            snapshot_id: Pilaster snapshot to use as the workflow source.

        Returns:
            RenderJob with the new job's ID and initial status.

        Raises:
            PilasterUnavailableError: If the API is unreachable or returns an error.
        """
        payload = {"snapshot_id": snapshot_id}
        try:
            response = await self._client.post("/api/render", json=payload)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise PilasterUnavailableError(
                f"Cannot connect to Pilaster at {self._client.base_url}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise PilasterUnavailableError(
                f"Pilaster render error: {exc.response.status_code} {exc.response.text}"
            ) from exc

        data = response.json()
        return RenderJob(
            run_id=data.get("run_id", data.get("id", "")),
            status=data.get("status", "pending"),
            result_url=data.get("result_url"),
        )

    # -- Status polling -------------------------------------------------------

    async def check_render_status(self, run_id: str) -> RenderJob:
        """Check render job status.

        Args:
            run_id: Pilaster render job identifier.

        Returns:
            Updated RenderJob.
        """
        response = await self._client.get(f"/api/render/{run_id}")
        response.raise_for_status()
        data = response.json()
        return RenderJob(
            run_id=run_id,
            status=data.get("status", "processing"),
            result_url=data.get("result_url"),
        )

    async def poll_until_complete(
        self,
        run_id: str,
        *,
        max_wait: int = MAX_GENERATION_WAIT,
        poll_interval: int = POLL_INTERVAL,
    ) -> RenderJob:
        """Poll until the render job succeeds, fails, or times out.

        Args:
            run_id: Pilaster render job identifier.
            max_wait: Maximum seconds to wait.
            poll_interval: Seconds between status checks.

        Returns:
            RenderJob with terminal status.

        Raises:
            TimeoutError: If generation exceeds *max_wait*.
            GenerationFailedError: If the job fails or is cancelled.
        """
        elapsed = 0
        while elapsed < max_wait:
            try:
                job = await self.check_render_status(run_id)
            except httpx.HTTPError as exc:
                logger.warning("Status check failed for render %s: %s", run_id, exc)
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                continue

            logger.info("Render %s: %s", run_id, job.status)

            if job.status == "succeeded":
                return job

            if job.status in ("failed", "cancelled"):
                raise GenerationFailedError(f"Pilaster generation {job.status} for render {run_id}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Image generation timed out after {max_wait}s for render {run_id}")

    # -- List projects --------------------------------------------------------

    async def list_projects(self, limit: int = 20) -> list[dict[str, Any]]:
        """List available characters/projects.

        Args:
            limit: Maximum projects to return.

        Returns:
            List of project dicts with id, name, description, snapshot_count.
        """
        try:
            response = await self._client.get("/api/projects", params={"limit": limit})
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise PilasterUnavailableError(
                f"Cannot connect to Pilaster at {self._client.base_url}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise PilasterUnavailableError(
                f"Pilaster API error: {exc.response.status_code} {exc.response.text}"
            ) from exc

        data = response.json()
        projects: list[dict[str, Any]] = (
            data.get("projects", data) if isinstance(data, dict) else data
        )
        return projects

    # -- Context manager ------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> PilasterClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def extract_common_elements(experiments: list[ExperimentMatch]) -> list[str]:
    """Extract common keywords from successful experiment intents.

    Args:
        experiments: List of past experiments (ideally outcome=worked).

    Returns:
        Deduplicated list of common keywords found across intents.
    """
    if not experiments:
        return []

    # Collect all intent words, filter noise
    noise = frozenset(
        {
            "the",
            "a",
            "an",
            "and",
            "or",
            "for",
            "to",
            "in",
            "of",
            "with",
            "on",
            "is",
            "it",
            "this",
            "that",
            "from",
            "as",
            "at",
            "by",
            "be",
            "was",
        }
    )
    word_counts: dict[str, int] = {}
    for exp in experiments:
        words = {w.lower().strip(".,!?") for w in exp.intent.split() if len(w) > 2}
        for word in words - noise:
            word_counts[word] = word_counts.get(word, 0) + 1

    # Return words that appear in at least 2 experiments, sorted by frequency
    threshold = min(2, len(experiments))
    common = sorted(
        (w for w, c in word_counts.items() if c >= threshold),
        key=lambda w: word_counts[w],
        reverse=True,
    )
    return common[:10]


def build_image_prompt(
    decision: ContentDecision,
    successful_experiments: list[ExperimentMatch],
) -> str:
    """Build an image generation prompt informed by past successes.

    Args:
        decision: Content decision with topic and style context.
        successful_experiments: Past experiments that worked well.

    Returns:
        Prompt string for image generation.
    """
    parts: list[str] = [decision.topic]

    # Add patterns learned from successful experiments
    common = extract_common_elements(successful_experiments)
    if common:
        parts.append(", ".join(common[:3]))

    # Add platform-specific guidance
    if decision.platform.value in ("instagram", "tiktok"):
        parts.append("vibrant colors, eye-catching, social media optimized")
    elif decision.platform.value == "linkedin":
        parts.append("professional, clean layout, business-appropriate")
    elif decision.platform.value == "twitter":
        parts.append("bold, high contrast, attention-grabbing")

    # Add content type guidance
    if decision.content_type in (ContentType.TUTORIAL, ContentType.EDUCATIONAL):
        parts.append("informative, clear visual hierarchy, step-by-step")
    elif decision.content_type is ContentType.DEMO:
        parts.append("product showcase, modern UI, polished")
    elif decision.content_type is ContentType.ANNOUNCEMENT:
        parts.append("announcement, celebratory, branded")

    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Main workflow orchestrator
# ---------------------------------------------------------------------------


async def create_image_content(
    decision: ContentDecision,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    max_wait: int = MAX_GENERATION_WAIT,
    poll_interval: int = POLL_INTERVAL,
) -> ImageResult:
    """End-to-end image content creation workflow.

    Steps:
      1. Search past experiments for the content style.
      2. Build an informed prompt using successful patterns.
      3. Find a suitable snapshot to generate from.
      4. Submit generation job to Pilaster.
      5. Poll until the image is ready.

    If Pilaster is unavailable or has no experiments, the workflow still
    builds a prompt but cannot generate. In that case, it returns a result
    with status="pilaster_unavailable" or "no_snapshot" so the caller
    can decide on a fallback.

    Args:
        decision: Content decision specifying product, topic, platform, etc.
        base_url: Override Pilaster API URL (default from env or constant).
        api_key: Override API key (default from PILASTER_API_KEY env var).
        max_wait: Maximum seconds to wait for generation.
        poll_interval: Seconds between status polls.

    Returns:
        ImageResult with image_url, prompt_used, and decision context.

    Raises:
        PilasterUnavailableError: If Pilaster is unreachable (when not in fallback).
        GenerationFailedError: If generation fails.
        TimeoutError: If generation exceeds *max_wait*.
    """
    resolved_url = base_url or os.environ.get("PILASTER_BASE_URL", PILASTER_BASE_URL)
    resolved_key = api_key or os.environ.get("PILASTER_API_KEY")

    async with PilasterClient(
        base_url=resolved_url,
        api_key=resolved_key,
    ) as client:
        # Step 1: search for successful past experiments
        search_query = CONTENT_TYPE_QUERIES.get(decision.content_type.value, decision.topic)
        successful: list[ExperimentMatch] = []
        try:
            successful = await client.search_experiments(
                query=search_query,
                outcome="worked",
                limit=5,
            )
            logger.info(
                "Found %d successful experiments for style=%s",
                len(successful),
                decision.content_type.value,
            )
        except PilasterUnavailableError:
            logger.warning("Pilaster unavailable for experiment search, using default prompt")

        # Step 2: build an informed prompt
        prompt = build_image_prompt(decision, successful)
        logger.info("Built image prompt: %s", prompt[:100])

        # Step 3: find a snapshot to generate from
        # Prefer successful experiments; if none, search without outcome filter
        snapshot_id: str | None = None
        if successful:
            snapshot_id = successful[0].snapshot_id
        else:
            try:
                all_experiments = await client.search_experiments(
                    query=search_query,
                    limit=1,
                )
                if all_experiments:
                    snapshot_id = all_experiments[0].snapshot_id
            except PilasterUnavailableError:
                logger.warning("Pilaster unavailable for fallback search")

        if not snapshot_id:
            logger.warning("No snapshot available for generation; returning prompt-only result")
            return ImageResult(
                image_url="",
                prompt_used=prompt,
                status="no_snapshot",
                learned_from=len(successful),
                decision=decision.model_dump(mode="json"),
            )

        # Step 4: submit generation job
        job = await client.generate_image(snapshot_id)
        logger.info("Submitted Pilaster render %s from snapshot %s", job.run_id, snapshot_id)

        # Step 5: poll until complete
        job = await client.poll_until_complete(
            job.run_id,
            max_wait=max_wait,
            poll_interval=poll_interval,
        )

    image_url = job.result_url or ""
    return ImageResult(
        image_url=image_url,
        prompt_used=prompt,
        run_id=job.run_id,
        status="pending_review",
        learned_from=len(successful),
        decision=decision.model_dump(mode="json"),
    )
