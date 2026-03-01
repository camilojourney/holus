"""Tests for holus.agents.marketing.video_workflow.

Tests cover:
  - Source footage discovery
  - Instruction building
  - GenpeliClient (submit, poll, preview, approve, reject)
  - End-to-end create_video_content orchestrator
  - Error paths (no footage, unavailable, timeout, processing error)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from holus.agents.marketing.models import ContentDecision, ContentType, Platform
from holus.agents.marketing.video_workflow import (
    GenpeliClient,
    GenpeliUnavailableError,
    NoFootageError,
    VideoJob,
    VideoResult,
    build_instruction,
    create_video_content,
    find_source_footage,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_REQUEST = httpx.Request("GET", "http://test:8100")


def _resp(status_code: int = 200, *, json: dict[str, Any] | None = None) -> httpx.Response:
    """Create an httpx.Response with a request set (needed for raise_for_status)."""
    return httpx.Response(status_code, json=json, request=_DUMMY_REQUEST)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_decision() -> ContentDecision:
    """A video_reel content decision for pilaster."""
    return ContentDecision(
        product="pilaster",
        platform=Platform.TIKTOK,
        content_type=ContentType.VIDEO_REEL,
        topic="How to generate AI images with Pilaster",
        reasoning="Video reels perform 3x better on TikTok",
        priority=1,
        estimated_engagement="high",
    )


@pytest.fixture
def linkedin_decision() -> ContentDecision:
    """A tutorial content decision for LinkedIn."""
    return ContentDecision(
        product="genpeli",
        platform=Platform.LINKEDIN,
        content_type=ContentType.TUTORIAL,
        topic="Automated video editing with Genpeli",
        reasoning="LinkedIn audience prefers tutorials",
        priority=2,
        estimated_engagement="medium",
    )


@pytest.fixture
def footage_dir(tmp_path: Path) -> Path:
    """Create a temp footage directory with sample files."""
    pilaster_dir = tmp_path / "footage" / "pilaster"
    pilaster_dir.mkdir(parents=True)

    # Create dummy video files
    (pilaster_dir / "demo-01.mp4").write_bytes(b"fake-video-1")
    (pilaster_dir / "demo-02.mov").write_bytes(b"fake-video-2")
    # Non-video file should be ignored
    (pilaster_dir / "notes.txt").write_text("not a video")

    return tmp_path / "footage"


@pytest.fixture
def empty_footage_dir(tmp_path: Path) -> Path:
    """Create an empty footage directory."""
    footage = tmp_path / "footage"
    footage.mkdir()
    return footage


# ---------------------------------------------------------------------------
# find_source_footage
# ---------------------------------------------------------------------------


class TestFindSourceFootage:
    def test_finds_video_files(self, sample_decision: ContentDecision, footage_dir: Path) -> None:
        result = find_source_footage(sample_decision, footage_dir)
        assert len(result) == 2
        assert any("demo-01.mp4" in p for p in result)
        assert any("demo-02.mov" in p for p in result)

    def test_ignores_non_video_files(
        self, sample_decision: ContentDecision, footage_dir: Path
    ) -> None:
        result = find_source_footage(sample_decision, footage_dir)
        assert not any("notes.txt" in p for p in result)

    def test_returns_empty_when_no_footage_dir(
        self, sample_decision: ContentDecision, tmp_path: Path
    ) -> None:
        result = find_source_footage(sample_decision, tmp_path / "nonexistent")
        assert result == []

    def test_returns_empty_when_no_product_dir(
        self, sample_decision: ContentDecision, empty_footage_dir: Path
    ) -> None:
        result = find_source_footage(sample_decision, empty_footage_dir)
        assert result == []

    def test_returns_empty_when_product_dir_has_no_videos(
        self, sample_decision: ContentDecision, tmp_path: Path
    ) -> None:
        product_dir = tmp_path / "footage" / "pilaster"
        product_dir.mkdir(parents=True)
        (product_dir / "readme.md").write_text("no videos here")

        result = find_source_footage(sample_decision, tmp_path / "footage")
        assert result == []

    def test_returns_sorted_paths(
        self, sample_decision: ContentDecision, footage_dir: Path
    ) -> None:
        result = find_source_footage(sample_decision, footage_dir)
        basenames = [Path(p).name for p in result]
        assert basenames == sorted(basenames)


# ---------------------------------------------------------------------------
# build_instruction
# ---------------------------------------------------------------------------


class TestBuildInstruction:
    def test_video_reel_includes_vertical_format(self, sample_decision: ContentDecision) -> None:
        instruction = build_instruction(sample_decision)
        assert "9:16" in instruction
        assert "Cut silences" in instruction

    def test_tiktok_includes_duration_limit(self, sample_decision: ContentDecision) -> None:
        instruction = build_instruction(sample_decision)
        assert "under 60 seconds" in instruction

    def test_linkedin_no_duration_limit(self, linkedin_decision: ContentDecision) -> None:
        instruction = build_instruction(linkedin_decision)
        assert "under 60 seconds" not in instruction

    def test_includes_topic(self, sample_decision: ContentDecision) -> None:
        instruction = build_instruction(sample_decision)
        assert "How to generate AI images" in instruction

    def test_non_reel_no_vertical(self, linkedin_decision: ContentDecision) -> None:
        instruction = build_instruction(linkedin_decision)
        assert "9:16" not in instruction


# ---------------------------------------------------------------------------
# GenpeliClient
# ---------------------------------------------------------------------------


class TestGenpeliClient:
    @pytest.mark.asyncio
    async def test_submit_job_success(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.post = AsyncMock(
                return_value=_resp(
                    json={
                        "job_id": "job-123",
                        "status": "processing",
                        "progress_percent": 0,
                    }
                )
            )

            job = await client.submit_job(
                ["/path/to/video.mp4"],
                "Cut silences, add captions",
            )
            assert job.job_id == "job-123"
            assert job.status == "processing"
            assert job.progress_percent == 0

    @pytest.mark.asyncio
    async def test_submit_job_connect_error(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with pytest.raises(GenpeliUnavailableError, match="Cannot connect"):
                await client.submit_job(["/path/to/video.mp4"], "instruction")

    @pytest.mark.asyncio
    async def test_submit_job_http_error(self) -> None:
        mock_request = httpx.Request("POST", "http://test:8100/v1/jobs")
        mock_response = httpx.Response(500, text="Internal Server Error", request=mock_request)

        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server error", request=mock_request, response=mock_response
                )
            )

            with pytest.raises(GenpeliUnavailableError, match="API error"):
                await client.submit_job(["/path/to/video.mp4"], "instruction")

    @pytest.mark.asyncio
    async def test_check_status(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(
                    json={
                        "job_id": "job-123",
                        "status": "ready_for_review",
                        "progress_percent": 100,
                    }
                )
            )

            job = await client.check_status("job-123")
            assert job.status == "ready_for_review"
            assert job.progress_percent == 100

    @pytest.mark.asyncio
    async def test_poll_until_ready_immediate(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(json={"status": "ready_for_review", "progress_percent": 100})
            )

            job = await client.poll_until_ready("job-123", max_wait=10, poll_interval=1)
            assert job.status == "ready_for_review"

    @pytest.mark.asyncio
    async def test_poll_until_ready_after_processing(self) -> None:
        responses = [
            _resp(json={"status": "processing", "progress_percent": 50}),
            _resp(json={"status": "processing", "progress_percent": 80}),
            _resp(json={"status": "ready_for_review", "progress_percent": 100}),
        ]

        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(side_effect=responses)

            with patch(
                "holus.agents.marketing.video_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                job = await client.poll_until_ready("job-123", max_wait=60, poll_interval=1)
                assert job.status == "ready_for_review"

    @pytest.mark.asyncio
    async def test_poll_until_ready_error_state(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(json={"status": "error", "error": "Transcription failed"})
            )

            with pytest.raises(ValueError, match="processing failed"):
                await client.poll_until_ready("job-123", max_wait=10, poll_interval=1)

    @pytest.mark.asyncio
    async def test_poll_until_ready_timeout(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(json={"status": "processing", "progress_percent": 50})
            )

            with (
                patch(
                    "holus.agents.marketing.video_workflow.asyncio.sleep",
                    new_callable=AsyncMock,
                ),
                pytest.raises(TimeoutError, match="timed out"),
            ):
                await client.poll_until_ready("job-123", max_wait=2, poll_interval=1)

    @pytest.mark.asyncio
    async def test_poll_until_ready_transient_http_error(self) -> None:
        """Transient HTTP errors during polling are retried, not fatal."""
        responses: list[httpx.Response | httpx.HTTPError] = [
            httpx.HTTPError("Network blip"),
            _resp(json={"status": "ready_for_review", "progress_percent": 100}),
        ]
        call_count = 0

        async def mock_get(url: str) -> httpx.Response:
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            if isinstance(resp, Exception):
                raise resp
            return resp

        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.get = mock_get

            with patch(
                "holus.agents.marketing.video_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                job = await client.poll_until_ready("job-123", max_wait=30, poll_interval=1)
                assert job.status == "ready_for_review"

    @pytest.mark.asyncio
    async def test_get_preview_url(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(
                    json={
                        "preview_url": "http://localhost:8100/v1/jobs/job-123/preview",
                    }
                )
            )

            url = await client.get_preview_url("job-123")
            assert url == "http://localhost:8100/v1/jobs/job-123/preview"

    @pytest.mark.asyncio
    async def test_approve(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.post = AsyncMock(return_value=_resp(json={"status": "approved"}))

            result = await client.approve("job-123")
            assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_reject(self) -> None:
        async with GenpeliClient(base_url="http://test:8100") as client:
            client._client = AsyncMock()
            client._client.post = AsyncMock(return_value=_resp(json={"status": "rejected"}))

            result = await client.reject("job-123", reason="Bad audio")
            assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        client = GenpeliClient(base_url="http://test:8100")
        async with client as c:
            assert c is client
        # Should not raise after exit


# ---------------------------------------------------------------------------
# create_video_content (end-to-end orchestrator)
# ---------------------------------------------------------------------------


class TestCreateVideoContent:
    @pytest.mark.asyncio
    async def test_full_workflow(
        self,
        sample_decision: ContentDecision,
        footage_dir: Path,
    ) -> None:
        """Happy path: footage found, job submitted, polled, preview returned."""
        with (
            patch(
                "holus.agents.marketing.video_workflow.GenpeliClient",
            ) as mock_client_cls,
            patch(
                "holus.agents.marketing.video_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_instance = AsyncMock()
            mock_instance.submit_job = AsyncMock(
                return_value=VideoJob(job_id="job-abc", status="processing", progress_percent=0)
            )
            mock_instance.poll_until_ready = AsyncMock(
                return_value=VideoJob(
                    job_id="job-abc", status="ready_for_review", progress_percent=100
                )
            )
            mock_instance.get_preview_url = AsyncMock(return_value="http://genpeli/preview/job-abc")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_instance

            result = await create_video_content(
                sample_decision,
                base_url="http://test:8100",
                footage_dir=footage_dir,
            )

            assert isinstance(result, VideoResult)
            assert result.job_id == "job-abc"
            assert result.preview_url == "http://genpeli/preview/job-abc"
            assert result.status == "pending_review"
            assert result.decision["product"] == "pilaster"

    @pytest.mark.asyncio
    async def test_no_footage_raises(
        self,
        sample_decision: ContentDecision,
        empty_footage_dir: Path,
    ) -> None:
        with pytest.raises(NoFootageError, match="No source footage"):
            await create_video_content(
                sample_decision,
                footage_dir=empty_footage_dir,
            )

    @pytest.mark.asyncio
    async def test_genpeli_unavailable(
        self,
        sample_decision: ContentDecision,
        footage_dir: Path,
    ) -> None:
        with patch(
            "holus.agents.marketing.video_workflow.GenpeliClient",
        ) as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.submit_job = AsyncMock(
                side_effect=GenpeliUnavailableError("Cannot connect")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_instance

            with pytest.raises(GenpeliUnavailableError):
                await create_video_content(
                    sample_decision,
                    base_url="http://test:8100",
                    footage_dir=footage_dir,
                )

    @pytest.mark.asyncio
    async def test_processing_timeout(
        self,
        sample_decision: ContentDecision,
        footage_dir: Path,
    ) -> None:
        with patch(
            "holus.agents.marketing.video_workflow.GenpeliClient",
        ) as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.submit_job = AsyncMock(
                return_value=VideoJob(job_id="job-slow", status="processing")
            )
            mock_instance.poll_until_ready = AsyncMock(side_effect=TimeoutError("timed out"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_instance

            with pytest.raises(TimeoutError):
                await create_video_content(
                    sample_decision,
                    base_url="http://test:8100",
                    footage_dir=footage_dir,
                    max_wait=5,
                )

    @pytest.mark.asyncio
    async def test_processing_error(
        self,
        sample_decision: ContentDecision,
        footage_dir: Path,
    ) -> None:
        with patch(
            "holus.agents.marketing.video_workflow.GenpeliClient",
        ) as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.submit_job = AsyncMock(
                return_value=VideoJob(job_id="job-bad", status="processing")
            )
            mock_instance.poll_until_ready = AsyncMock(
                side_effect=ValueError("Genpeli processing failed")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_instance

            with pytest.raises(ValueError, match="processing failed"):
                await create_video_content(
                    sample_decision,
                    base_url="http://test:8100",
                    footage_dir=footage_dir,
                )


# ---------------------------------------------------------------------------
# VideoJob / VideoResult models
# ---------------------------------------------------------------------------


class TestModels:
    def test_video_job_defaults(self) -> None:
        job = VideoJob(job_id="test", status="processing")
        assert job.progress_percent == 0

    def test_video_result_defaults(self) -> None:
        result = VideoResult(job_id="test", preview_url="http://example.com/preview")
        assert result.status == "pending_review"
        assert result.decision == {}

    def test_video_result_with_decision(self, sample_decision: ContentDecision) -> None:
        result = VideoResult(
            job_id="test",
            preview_url="http://example.com/preview",
            decision=sample_decision.model_dump(mode="json"),
        )
        assert result.decision["product"] == "pilaster"
        assert result.decision["platform"] == "tiktok"
