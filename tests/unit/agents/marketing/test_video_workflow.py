"""Tests for holus.agents.marketing.video_workflow — Genpeli integration path.

Covers:
  - Pydantic models (VideoJob, VideoResult)
  - Custom exceptions (GenpeliUnavailableError, NoFootageError)
  - Constants (GENPELI_BASE_URL, MAX_PROCESSING_WAIT, POLL_INTERVAL, VIDEO_EXTENSIONS)
  - GenpeliClient: __init__, submit_job, check_status, poll_until_ready,
    get_preview_url, approve, reject, context manager
  - find_source_footage: missing dir, missing product dir, finds/sorts video files,
    ignores non-video files
  - build_instruction: base text, VIDEO_REEL format, short-form platforms, topic
  - create_video_content: happy path, NoFootageError, env var overrides,
    GenpeliUnavailableError propagation, TimeoutError propagation
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pydantic
import pytest

from holus.agents.marketing.models import ContentDecision, ContentType, Platform
from holus.agents.marketing.video_workflow import (
    GENPELI_BASE_URL,
    MAX_PROCESSING_WAIT,
    POLL_INTERVAL,
    VIDEO_EXTENSIONS,
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


def _decision(**overrides) -> ContentDecision:
    """Create a minimal ContentDecision for testing."""
    defaults = {
        "product": "genpeli",
        "platform": Platform.INSTAGRAM,
        "content_type": ContentType.VIDEO_REEL,
        "topic": "AI video editing demo",
        "reasoning": "video performs well",
    }
    defaults.update(overrides)
    return ContentDecision(**defaults)


# ===========================================================================
# Models
# ===========================================================================


class TestVideoJob:
    def test_defaults(self):
        job = VideoJob(job_id="j1", status="processing")
        assert job.job_id == "j1"
        assert job.status == "processing"
        assert job.progress_percent == 0

    def test_progress_validation(self):
        job = VideoJob(job_id="j1", status="ready_for_review", progress_percent=75)
        assert job.progress_percent == 75

    def test_progress_at_boundaries(self):
        j0 = VideoJob(job_id="j1", status="processing", progress_percent=0)
        j100 = VideoJob(job_id="j1", status="ready_for_review", progress_percent=100)
        assert j0.progress_percent == 0
        assert j100.progress_percent == 100

    def test_progress_above_max_raises(self):
        with pytest.raises(pydantic.ValidationError):
            VideoJob(job_id="j1", status="processing", progress_percent=101)

    def test_progress_below_min_raises(self):
        with pytest.raises(pydantic.ValidationError):
            VideoJob(job_id="j1", status="processing", progress_percent=-1)


class TestVideoResult:
    def test_defaults(self):
        r = VideoResult(job_id="j1", preview_url="https://preview.test/v/j1")
        assert r.status == "pending_review"
        assert r.decision == {}

    def test_full_fields(self):
        d = _decision()
        r = VideoResult(
            job_id="j1",
            preview_url="https://preview.test/v/j1",
            status="approved",
            decision=d.model_dump(mode="json"),
        )
        assert r.status == "approved"
        assert r.decision["product"] == "genpeli"

    def test_serialization(self):
        r = VideoResult(job_id="j2", preview_url="https://test/v2")
        dumped = r.model_dump(mode="json")
        assert dumped["job_id"] == "j2"
        assert dumped["status"] == "pending_review"


# ===========================================================================
# Exceptions
# ===========================================================================


class TestExceptions:
    def test_genpeli_unavailable_is_exception(self):
        exc = GenpeliUnavailableError("Genpeli is down")
        assert isinstance(exc, Exception)
        assert str(exc) == "Genpeli is down"

    def test_no_footage_is_exception(self):
        exc = NoFootageError("No footage found")
        assert isinstance(exc, Exception)
        assert str(exc) == "No footage found"

    def test_genpeli_unavailable_can_be_raised(self):
        with pytest.raises(GenpeliUnavailableError, match="unreachable"):
            raise GenpeliUnavailableError("unreachable")

    def test_no_footage_can_be_raised(self):
        with pytest.raises(NoFootageError, match="empty"):
            raise NoFootageError("empty")


# ===========================================================================
# Constants
# ===========================================================================


class TestConstants:
    def test_genpeli_base_url(self):
        assert GENPELI_BASE_URL == "http://localhost:8100"

    def test_max_processing_wait(self):
        assert MAX_PROCESSING_WAIT == 300

    def test_poll_interval(self):
        assert POLL_INTERVAL == 10

    def test_video_extensions_is_frozenset(self):
        assert isinstance(VIDEO_EXTENSIONS, frozenset)

    def test_video_extensions_values(self):
        assert ".mp4" in VIDEO_EXTENSIONS
        assert ".mov" in VIDEO_EXTENSIONS
        assert ".webm" in VIDEO_EXTENSIONS
        assert ".mkv" in VIDEO_EXTENSIONS

    def test_video_extensions_excludes_non_video(self):
        assert ".jpg" not in VIDEO_EXTENSIONS
        assert ".png" not in VIDEO_EXTENSIONS
        assert ".txt" not in VIDEO_EXTENSIONS


# ===========================================================================
# GenpeliClient.__init__
# ===========================================================================


class TestGenpeliClientInit:
    def test_default_init(self):
        client = GenpeliClient()
        assert client._client.base_url == httpx.URL(GENPELI_BASE_URL)

    def test_custom_base_url(self):
        client = GenpeliClient(base_url="http://custom:9000")
        assert client._client.base_url == httpx.URL("http://custom:9000")

    def test_api_key_sets_auth_header(self):
        client = GenpeliClient(api_key="secret-key")
        assert client._client.headers["authorization"] == "Bearer secret-key"

    def test_no_api_key_no_auth_header(self):
        client = GenpeliClient()
        assert "authorization" not in client._client.headers

    def test_custom_timeout(self):
        client = GenpeliClient(timeout=60.0)
        # httpx stores timeout as Timeout object; just verify construction didn't raise
        assert client._client is not None


# ===========================================================================
# GenpeliClient.submit_job
# ===========================================================================


class TestSubmitJob:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_response = httpx.Response(
            200,
            json={"job_id": "job-abc", "status": "processing", "progress_percent": 0},
            request=httpx.Request("POST", "http://test/v1/jobs"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        job = await client.submit_job(["file1.mp4"], "Cut silences")
        assert job.job_id == "job-abc"
        assert job.status == "processing"
        assert job.progress_percent == 0

    @pytest.mark.asyncio
    async def test_connect_error_raises_genpeli_unavailable(self):
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client._client.base_url = httpx.URL("http://test")

        with pytest.raises(GenpeliUnavailableError, match="Cannot connect"):
            await client.submit_job(["file1.mp4"], "instruction")

    @pytest.mark.asyncio
    async def test_http_status_error_raises_genpeli_unavailable(self):
        mock_response = httpx.Response(
            500,
            text="Internal Server Error",
            request=httpx.Request("POST", "http://test/v1/jobs"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        with pytest.raises(GenpeliUnavailableError, match="API error"):
            await client.submit_job(["file1.mp4"], "instruction")

    @pytest.mark.asyncio
    async def test_default_status_when_missing(self):
        mock_response = httpx.Response(
            200,
            json={"job_id": "job-xyz"},
            request=httpx.Request("POST", "http://test/v1/jobs"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        job = await client.submit_job([], "instruction")
        assert job.status == "processing"
        assert job.progress_percent == 0


# ===========================================================================
# GenpeliClient.check_status
# ===========================================================================


class TestCheckStatus:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_response = httpx.Response(
            200,
            json={"status": "ready_for_review", "progress_percent": 100},
            request=httpx.Request("GET", "http://test/v1/jobs/job-1"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)

        job = await client.check_status("job-1")
        assert job.job_id == "job-1"
        assert job.status == "ready_for_review"
        assert job.progress_percent == 100

    @pytest.mark.asyncio
    async def test_defaults_when_fields_missing(self):
        mock_response = httpx.Response(
            200,
            json={},
            request=httpx.Request("GET", "http://test/v1/jobs/j1"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)

        job = await client.check_status("j1")
        assert job.status == "processing"
        assert job.progress_percent == 0


# ===========================================================================
# GenpeliClient.poll_until_ready
# ===========================================================================


class TestPollUntilReady:
    @pytest.mark.asyncio
    async def test_ready_for_review_returns(self):
        client = GenpeliClient()
        client.check_status = AsyncMock(
            return_value=VideoJob(
                job_id="j1", status="ready_for_review", progress_percent=100
            )
        )
        job = await client.poll_until_ready("j1", max_wait=30, poll_interval=1)
        assert job.status == "ready_for_review"

    @pytest.mark.asyncio
    async def test_error_status_raises_value_error(self):
        client = GenpeliClient()
        client.check_status = AsyncMock(
            return_value=VideoJob(job_id="j1", status="error")
        )
        with pytest.raises(ValueError, match="failed"):
            await client.poll_until_ready("j1", max_wait=30, poll_interval=1)

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        client = GenpeliClient()
        client.check_status = AsyncMock(
            return_value=VideoJob(job_id="j1", status="processing", progress_percent=50)
        )
        with (
            patch("holus.agents.marketing.video_workflow.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(TimeoutError, match="timed out"),
        ):
            await client.poll_until_ready("j1", max_wait=3, poll_interval=1)

    @pytest.mark.asyncio
    async def test_http_error_during_poll_retries(self):
        """HTTPError during status check is logged and retried."""
        client = GenpeliClient()
        client.check_status = AsyncMock(
            side_effect=[
                httpx.HTTPError("network blip"),
                VideoJob(job_id="j1", status="ready_for_review", progress_percent=100),
            ]
        )
        with patch("holus.agents.marketing.video_workflow.asyncio.sleep", new_callable=AsyncMock):
            job = await client.poll_until_ready("j1", max_wait=30, poll_interval=1)
        assert job.status == "ready_for_review"

    @pytest.mark.asyncio
    async def test_succeeds_after_processing(self):
        client = GenpeliClient()
        client.check_status = AsyncMock(
            side_effect=[
                VideoJob(job_id="j1", status="processing", progress_percent=30),
                VideoJob(job_id="j1", status="processing", progress_percent=70),
                VideoJob(job_id="j1", status="ready_for_review", progress_percent=100),
            ]
        )
        with patch("holus.agents.marketing.video_workflow.asyncio.sleep", new_callable=AsyncMock):
            job = await client.poll_until_ready("j1", max_wait=60, poll_interval=1)
        assert job.status == "ready_for_review"


# ===========================================================================
# GenpeliClient.get_preview_url
# ===========================================================================


class TestGetPreviewUrl:
    @pytest.mark.asyncio
    async def test_returns_url_from_response(self):
        mock_response = httpx.Response(
            200,
            json={"preview_url": "https://cdn.genpeli/preview/j1.mp4"},
            request=httpx.Request("GET", "http://test/v1/jobs/j1/preview"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        url = await client.get_preview_url("j1")
        assert url == "https://cdn.genpeli/preview/j1.mp4"

    @pytest.mark.asyncio
    async def test_fallback_url_when_missing(self):
        mock_response = httpx.Response(
            200,
            json={},
            request=httpx.Request("GET", "http://test/v1/jobs/j1/preview"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        url = await client.get_preview_url("j1")
        assert "j1" in url
        assert "preview" in url


# ===========================================================================
# GenpeliClient.approve
# ===========================================================================


class TestApprove:
    @pytest.mark.asyncio
    async def test_posts_and_returns_response(self):
        mock_response = httpx.Response(
            200,
            json={"status": "approved", "job_id": "j1"},
            request=httpx.Request("POST", "http://test/v1/jobs/j1/approve"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.approve("j1")
        assert result["status"] == "approved"
        client._client.post.assert_awaited_once()
        call_args = client._client.post.call_args
        assert "j1/approve" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        mock_response = httpx.Response(
            200,
            json={"ok": True},
            request=httpx.Request("POST", "http://test/v1/jobs/j2/approve"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.approve("j2")
        assert isinstance(result, dict)
        assert result["ok"] is True


# ===========================================================================
# GenpeliClient.reject
# ===========================================================================


class TestReject:
    @pytest.mark.asyncio
    async def test_posts_with_reason(self):
        mock_response = httpx.Response(
            200,
            json={"status": "rejected"},
            request=httpx.Request("POST", "http://test/v1/jobs/j1/reject"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.reject("j1", reason="Poor quality")
        assert result["status"] == "rejected"

        call_args = client._client.post.call_args
        assert "j1/reject" in call_args[0][0]
        assert call_args.kwargs["json"]["reason"] == "Poor quality"

    @pytest.mark.asyncio
    async def test_empty_reason_default(self):
        mock_response = httpx.Response(
            200,
            json={"ok": True},
            request=httpx.Request("POST", "http://test/v1/jobs/j1/reject"),
        )
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)

        await client.reject("j1")
        call_args = client._client.post.call_args
        assert call_args.kwargs["json"]["reason"] == ""


# ===========================================================================
# GenpeliClient context manager
# ===========================================================================


class TestGenpeliClientContextManager:
    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.aclose = AsyncMock()

        async with client as c:
            assert c is client

    @pytest.mark.asyncio
    async def test_aexit_calls_close(self):
        client = GenpeliClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.aclose = AsyncMock()

        async with client:
            pass

        client._client.aclose.assert_awaited_once()


# ===========================================================================
# find_source_footage
# ===========================================================================


class TestFindSourceFootage:
    def test_missing_footage_dir_returns_empty(self):
        d = _decision(product="genpeli")
        result = find_source_footage(d, Path("/nonexistent/dir"))
        assert result == []

    def test_missing_product_subdir_returns_empty(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        footage_dir.mkdir()
        # No "genpeli" subdir
        d = _decision(product="genpeli")
        result = find_source_footage(d, footage_dir)
        assert result == []

    def test_finds_video_files(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip01.mp4").write_bytes(b"fake")
        (product_dir / "clip02.mov").write_bytes(b"fake")

        d = _decision(product="genpeli")
        result = find_source_footage(d, footage_dir)
        assert len(result) == 2
        assert all(".mp4" in r or ".mov" in r for r in result)

    def test_ignores_non_video_files(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip01.mp4").write_bytes(b"fake")
        (product_dir / "notes.txt").write_bytes(b"text")
        (product_dir / "thumbnail.jpg").write_bytes(b"img")

        d = _decision(product="genpeli")
        result = find_source_footage(d, footage_dir)
        assert len(result) == 1
        assert result[0].endswith(".mp4")

    def test_returns_sorted_paths(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "c_clip.mp4").write_bytes(b"fake")
        (product_dir / "a_clip.mp4").write_bytes(b"fake")
        (product_dir / "b_clip.mp4").write_bytes(b"fake")

        d = _decision(product="genpeli")
        result = find_source_footage(d, footage_dir)
        assert result == sorted(result)

    def test_returns_absolute_paths(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "pilaster"
        product_dir.mkdir(parents=True)
        (product_dir / "reel.mp4").write_bytes(b"fake")

        d = _decision(product="pilaster")
        result = find_source_footage(d, footage_dir)
        assert all(Path(r).is_absolute() for r in result)

    def test_all_video_extensions_found(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        for ext in [".mp4", ".mov", ".webm", ".mkv"]:
            (product_dir / f"clip{ext}").write_bytes(b"fake")

        d = _decision(product="genpeli")
        result = find_source_footage(d, footage_dir)
        assert len(result) == 4

    def test_empty_product_dir_returns_empty(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)

        d = _decision(product="genpeli")
        result = find_source_footage(d, footage_dir)
        assert result == []


# ===========================================================================
# build_instruction
# ===========================================================================


class TestBuildInstruction:
    def test_base_instruction_always_present(self):
        d = _decision(content_type=ContentType.DEMO, platform=Platform.LINKEDIN)
        instr = build_instruction(d)
        assert "Cut silences" in instr
        assert "captions" in instr
        assert "audio" in instr

    def test_video_reel_adds_9_16(self):
        d = _decision(content_type=ContentType.VIDEO_REEL)
        instr = build_instruction(d)
        assert "9:16" in instr

    def test_non_video_reel_no_9_16(self):
        d = _decision(content_type=ContentType.TUTORIAL)
        instr = build_instruction(d)
        assert "9:16" not in instr

    def test_tiktok_adds_60s_limit(self):
        d = _decision(platform=Platform.TIKTOK, content_type=ContentType.DEMO)
        instr = build_instruction(d)
        assert "60 seconds" in instr

    def test_instagram_adds_60s_limit(self):
        d = _decision(platform=Platform.INSTAGRAM, content_type=ContentType.DEMO)
        instr = build_instruction(d)
        assert "60 seconds" in instr

    def test_youtube_adds_60s_limit(self):
        d = _decision(platform=Platform.YOUTUBE, content_type=ContentType.DEMO)
        instr = build_instruction(d)
        assert "60 seconds" in instr

    def test_linkedin_no_60s_limit(self):
        d = _decision(platform=Platform.LINKEDIN, content_type=ContentType.DEMO)
        instr = build_instruction(d)
        assert "60 seconds" not in instr

    def test_twitter_no_60s_limit(self):
        d = _decision(platform=Platform.TWITTER, content_type=ContentType.DEMO)
        instr = build_instruction(d)
        assert "60 seconds" not in instr

    def test_topic_appended(self):
        d = _decision(topic="AI tools for creators")
        instr = build_instruction(d)
        assert "AI tools for creators" in instr

    def test_empty_topic_not_appended(self):
        d = _decision(topic="")
        instr = build_instruction(d)
        # topic is empty so the "Topic context:" line should not appear
        assert "Topic context:" not in instr

    def test_all_parts_combined(self):
        d = _decision(
            content_type=ContentType.VIDEO_REEL,
            platform=Platform.TIKTOK,
            topic="Demo reel",
        )
        instr = build_instruction(d)
        assert "Cut silences" in instr
        assert "9:16" in instr
        assert "60 seconds" in instr
        assert "Demo reel" in instr


# ===========================================================================
# create_video_content (end-to-end orchestrator)
# ===========================================================================


class TestCreateVideoContent:
    @pytest.mark.asyncio
    async def test_happy_path(self, tmp_path: Path):
        """Full workflow: find footage → submit → poll → preview URL → result."""
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip.mp4").write_bytes(b"fake")

        d = _decision()
        mock_client = AsyncMock(spec=GenpeliClient)
        mock_client.submit_job = AsyncMock(
            return_value=VideoJob(job_id="job-1", status="processing")
        )
        mock_client.poll_until_ready = AsyncMock(
            return_value=VideoJob(job_id="job-1", status="ready_for_review", progress_percent=100)
        )
        mock_client.get_preview_url = AsyncMock(return_value="https://cdn.genpeli/preview/job-1.mp4")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.video_workflow.GenpeliClient",
            return_value=mock_client,
        ):
            result = await create_video_content(
                d,
                base_url="http://test:8100",
                api_key="test-key",
                footage_dir=footage_dir,
            )

        assert result.job_id == "job-1"
        assert result.preview_url == "https://cdn.genpeli/preview/job-1.mp4"
        assert result.status == "pending_review"
        assert result.decision["product"] == "genpeli"

    @pytest.mark.asyncio
    async def test_no_footage_raises_no_footage_error(self, tmp_path: Path):
        """NoFootageError raised when footage directory is empty."""
        footage_dir = tmp_path / "footage"
        footage_dir.mkdir()

        d = _decision()
        with pytest.raises(NoFootageError, match="genpeli"):
            await create_video_content(d, footage_dir=footage_dir)

    @pytest.mark.asyncio
    async def test_no_footage_dir_raises_no_footage_error(self, tmp_path: Path):
        """NoFootageError raised when footage directory doesn't exist."""
        d = _decision()
        with pytest.raises(NoFootageError):
            await create_video_content(d, footage_dir=tmp_path / "nonexistent")

    @pytest.mark.asyncio
    async def test_env_var_base_url_override(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip.mp4").write_bytes(b"fake")

        d = _decision()
        mock_client = AsyncMock(spec=GenpeliClient)
        mock_client.submit_job = AsyncMock(
            return_value=VideoJob(job_id="j1", status="processing")
        )
        mock_client.poll_until_ready = AsyncMock(
            return_value=VideoJob(job_id="j1", status="ready_for_review")
        )
        mock_client.get_preview_url = AsyncMock(return_value="https://env-cdn/j1")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.dict(
                "os.environ",
                {"GENPELI_BASE_URL": "http://env-host:9100", "GENPELI_API_KEY": "env-key"},
            ),
            patch(
                "holus.agents.marketing.video_workflow.GenpeliClient",
                return_value=mock_client,
            ) as mock_cls,
        ):
            await create_video_content(d, footage_dir=footage_dir)

        mock_cls.assert_called_once_with(
            base_url="http://env-host:9100",
            api_key="env-key",
        )

    @pytest.mark.asyncio
    async def test_explicit_args_override_env(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip.mp4").write_bytes(b"fake")

        d = _decision()
        mock_client = AsyncMock(spec=GenpeliClient)
        mock_client.submit_job = AsyncMock(
            return_value=VideoJob(job_id="j1", status="processing")
        )
        mock_client.poll_until_ready = AsyncMock(
            return_value=VideoJob(job_id="j1", status="ready_for_review")
        )
        mock_client.get_preview_url = AsyncMock(return_value="https://explicit/j1")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.dict(
                "os.environ",
                {"GENPELI_BASE_URL": "http://env-host:9100", "GENPELI_API_KEY": "env-key"},
            ),
            patch(
                "holus.agents.marketing.video_workflow.GenpeliClient",
                return_value=mock_client,
            ) as mock_cls,
        ):
            await create_video_content(
                d,
                base_url="http://explicit:8100",
                api_key="explicit-key",
                footage_dir=footage_dir,
            )

        mock_cls.assert_called_once_with(
            base_url="http://explicit:8100",
            api_key="explicit-key",
        )

    @pytest.mark.asyncio
    async def test_genpeli_unavailable_propagates(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip.mp4").write_bytes(b"fake")

        d = _decision()
        mock_client = AsyncMock(spec=GenpeliClient)
        mock_client.submit_job = AsyncMock(side_effect=GenpeliUnavailableError("Genpeli down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "holus.agents.marketing.video_workflow.GenpeliClient",
                return_value=mock_client,
            ),
            pytest.raises(GenpeliUnavailableError, match="Genpeli down"),
        ):
            await create_video_content(d, base_url="http://test", footage_dir=footage_dir)

    @pytest.mark.asyncio
    async def test_timeout_error_propagates(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip.mp4").write_bytes(b"fake")

        d = _decision()
        mock_client = AsyncMock(spec=GenpeliClient)
        mock_client.submit_job = AsyncMock(
            return_value=VideoJob(job_id="j1", status="processing")
        )
        mock_client.poll_until_ready = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "holus.agents.marketing.video_workflow.GenpeliClient",
                return_value=mock_client,
            ),
            pytest.raises(TimeoutError, match="timed out"),
        ):
            await create_video_content(d, base_url="http://test", footage_dir=footage_dir)

    @pytest.mark.asyncio
    async def test_value_error_propagates(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip.mp4").write_bytes(b"fake")

        d = _decision()
        mock_client = AsyncMock(spec=GenpeliClient)
        mock_client.submit_job = AsyncMock(
            return_value=VideoJob(job_id="j1", status="processing")
        )
        mock_client.poll_until_ready = AsyncMock(
            side_effect=ValueError("Genpeli processing failed")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "holus.agents.marketing.video_workflow.GenpeliClient",
                return_value=mock_client,
            ),
            pytest.raises(ValueError, match="failed"),
        ):
            await create_video_content(d, base_url="http://test", footage_dir=footage_dir)

    @pytest.mark.asyncio
    async def test_decision_serialized_in_result(self, tmp_path: Path):
        footage_dir = tmp_path / "footage"
        product_dir = footage_dir / "genpeli"
        product_dir.mkdir(parents=True)
        (product_dir / "clip.mp4").write_bytes(b"fake")

        d = _decision(topic="My topic", product="genpeli")
        mock_client = AsyncMock(spec=GenpeliClient)
        mock_client.submit_job = AsyncMock(
            return_value=VideoJob(job_id="j42", status="processing")
        )
        mock_client.poll_until_ready = AsyncMock(
            return_value=VideoJob(job_id="j42", status="ready_for_review")
        )
        mock_client.get_preview_url = AsyncMock(return_value="https://cdn/j42")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.video_workflow.GenpeliClient",
            return_value=mock_client,
        ):
            result = await create_video_content(d, base_url="http://test", footage_dir=footage_dir)

        assert result.decision["topic"] == "My topic"
        assert result.decision["product"] == "genpeli"
