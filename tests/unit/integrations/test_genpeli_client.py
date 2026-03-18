"""Tests for the genpeli video processing API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from holus.integrations.genpeli import (
    ApprovalResult,
    GenpeliClient,
    PreviewResult,
    ProcessVideoRequest,
    RejectionResult,
    VideoJob,
    VideoStatus,
)


@pytest.fixture
def client():
    """Create a test client."""
    return GenpeliClient(base_url="http://localhost:8100", api_key="test-key")


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    return mock


class TestProcessVideo:
    """Test video processing submission."""

    @pytest.mark.asyncio
    async def test_process_video_success(self, client, mock_httpx_client):
        """Successful process_video returns VideoJob."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "job_id": "job_001",
            "status": "queued",
            "message": "Video processing queued",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.process_video(
                video_urls=["https://example.com/video.mp4"],
                instruction="Remove silences and add captions",
            )

            assert isinstance(result, VideoJob)
            assert result.job_id == "job_001"
            assert result.status == "queued"
            assert result.message == "Video processing queued"

    @pytest.mark.asyncio
    async def test_process_video_sends_correct_payload(
        self, client, mock_httpx_client
    ):
        """process_video sends the right payload to the API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "job_id": "job_002",
            "status": "queued",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            await client.process_video(
                video_urls=[
                    "https://example.com/v1.mp4",
                    "https://example.com/v2.mp4",
                ],
                instruction="Merge and trim",
            )

            mock_httpx_client.post.assert_called_once()
            call_args = mock_httpx_client.post.call_args
            assert call_args[0][0] == "/api/v1/process"
            payload = call_args[1]["json"]
            assert payload["video_urls"] == [
                "https://example.com/v1.mp4",
                "https://example.com/v2.mp4",
            ]
            assert payload["instruction"] == "Merge and trim"

    @pytest.mark.asyncio
    async def test_process_video_http_error(self, client, mock_httpx_client):
        """process_video raises on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            with pytest.raises(httpx.HTTPStatusError):
                await client.process_video(
                    video_urls=["https://example.com/video.mp4"],
                    instruction="Edit",
                )


class TestCheckStatus:
    """Test job status checking."""

    @pytest.mark.asyncio
    async def test_check_status_processing(self, client, mock_httpx_client):
        """check_status returns in-progress status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "job_id": "job_001",
            "status": "processing",
            "progress": 0.45,
            "output_url": None,
            "error": None,
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.check_status("job_001")

            assert isinstance(result, VideoStatus)
            assert result.job_id == "job_001"
            assert result.status == "processing"
            assert result.progress == 0.45
            assert result.is_complete is False
            assert result.succeeded is False
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/jobs/job_001/status"
            )

    @pytest.mark.asyncio
    async def test_check_status_completed(self, client, mock_httpx_client):
        """check_status returns completed status with output URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "job_id": "job_001",
            "status": "completed",
            "progress": 1.0,
            "output_url": "https://r2.example.com/output.mp4",
            "error": None,
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.check_status("job_001")

            assert result.is_complete is True
            assert result.succeeded is True
            assert result.output_url == "https://r2.example.com/output.mp4"

    @pytest.mark.asyncio
    async def test_check_status_failed(self, client, mock_httpx_client):
        """check_status returns failed status with error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "job_id": "job_001",
            "status": "failed",
            "progress": 0.2,
            "output_url": None,
            "error": "FFmpeg encoding failed",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.check_status("job_001")

            assert result.is_complete is True
            assert result.succeeded is False
            assert result.error == "FFmpeg encoding failed"


class TestGetPreview:
    """Test video preview retrieval."""

    @pytest.mark.asyncio
    async def test_get_preview_success(self, client, mock_httpx_client):
        """get_preview returns preview data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "job_id": "job_001",
            "preview_url": "https://r2.example.com/preview.mp4",
            "duration_seconds": 45.2,
            "resolution": "1080x1920",
            "thumbnail_url": "https://r2.example.com/thumb.jpg",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_preview("job_001")

            assert isinstance(result, PreviewResult)
            assert result.preview_url == "https://r2.example.com/preview.mp4"
            assert result.duration_seconds == 45.2
            assert result.resolution == "1080x1920"
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/jobs/job_001/preview"
            )


class TestApproveReject:
    """Test approval and rejection workflows."""

    @pytest.mark.asyncio
    async def test_approve_success(self, client, mock_httpx_client):
        """approve returns final URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "job_id": "job_001",
            "status": "approved",
            "final_url": "https://r2.example.com/final.mp4",
            "message": "Video approved and finalized",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.approve("job_001")

            assert isinstance(result, ApprovalResult)
            assert result.status == "approved"
            assert result.final_url == "https://r2.example.com/final.mp4"
            mock_httpx_client.post.assert_called_once_with(
                "/api/v1/jobs/job_001/approve"
            )

    @pytest.mark.asyncio
    async def test_reject_success(self, client, mock_httpx_client):
        """reject sends reason and returns result."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "job_id": "job_001",
            "status": "rejected",
            "reason": "Audio quality too low",
            "message": "Video rejected, re-processing available",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.reject("job_001", reason="Audio quality too low")

            assert isinstance(result, RejectionResult)
            assert result.status == "rejected"
            assert result.reason == "Audio quality too low"
            call_args = mock_httpx_client.post.call_args
            assert call_args[0][0] == "/api/v1/jobs/job_001/reject"
            assert call_args[1]["json"]["reason"] == "Audio quality too low"


class TestHealth:
    """Test health check."""

    @pytest.mark.asyncio
    async def test_health_check(self, client, mock_httpx_client):
        """Health endpoint returns service status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "healthy",
            "version": "1.2.0",
            "ffmpeg": True,
            "whisper": True,
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.health()

            assert result["status"] == "healthy"
            assert result["ffmpeg"] is True
            mock_httpx_client.get.assert_called_once_with("/api/v1/health")


class TestRetryBehavior:
    """Test tenacity retry on transient errors."""

    @pytest.mark.asyncio
    async def test_retries_on_http_status_error(self, client, mock_httpx_client):
        """Client retries on HTTPStatusError then succeeds."""
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=503),
        )

        success_response = MagicMock()
        success_response.json.return_value = {
            "job_id": "job_retry",
            "status": "completed",
            "progress": 1.0,
            "output_url": "https://r2.example.com/out.mp4",
            "error": None,
        }
        success_response.raise_for_status = MagicMock()

        mock_httpx_client.get.side_effect = [error_response, success_response]

        with patch.object(client, "client", mock_httpx_client):
            result = await client.check_status("job_retry")

            assert result.succeeded is True
            assert mock_httpx_client.get.call_count == 2


class TestClientLifecycle:
    """Test client lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client works as async context manager."""
        async with GenpeliClient(api_key="test-key") as c:
            assert c.client is not None

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Client can be closed manually."""
        await client.close()


class TestModels:
    """Test Pydantic models."""

    def test_video_status_is_complete(self):
        """is_complete property works for completed and failed."""
        completed = VideoStatus(job_id="j1", status="completed", progress=1.0)
        failed = VideoStatus(job_id="j2", status="failed", progress=0.5)
        processing = VideoStatus(job_id="j3", status="processing", progress=0.3)

        assert completed.is_complete is True
        assert failed.is_complete is True
        assert processing.is_complete is False

    def test_video_status_succeeded(self):
        """succeeded is True only for completed status."""
        completed = VideoStatus(job_id="j1", status="completed")
        failed = VideoStatus(job_id="j2", status="failed")

        assert completed.succeeded is True
        assert failed.succeeded is False

    def test_process_video_request_defaults(self):
        """ProcessVideoRequest validates correctly."""
        req = ProcessVideoRequest(
            video_urls=["https://example.com/v.mp4"],
            instruction="Edit video",
        )
        assert len(req.video_urls) == 1
        assert req.instruction == "Edit video"

    def test_video_job_defaults(self):
        """VideoJob has sensible defaults."""
        job = VideoJob(job_id="j1")
        assert job.status == "queued"
        assert job.message is None
