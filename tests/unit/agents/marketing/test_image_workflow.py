"""Tests for holus.agents.marketing.image_workflow — Pilaster integration path.

Covers:
  - Pydantic models (ExperimentMatch, RenderJob, ImageResult)
  - Custom exceptions
  - PilasterClient: search_experiments, generate_image, check_render_status,
    poll_until_complete, list_projects, context manager
  - extract_common_elements keyword extraction
  - build_image_prompt platform/content-type guidance
  - create_image_content end-to-end orchestrator (happy path, no snapshot,
    Pilaster unavailable, generation failed, timeout)
  - CONTENT_TYPE_QUERIES constant coverage
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from holus.agents.marketing.image_workflow import (
    CONTENT_TYPE_QUERIES,
    DEFAULT_QUALITY_THRESHOLD,
    MAX_GENERATION_WAIT,
    PILASTER_BASE_URL,
    POLL_INTERVAL,
    ExperimentMatch,
    GenerationFailedError,
    ImageResult,
    PilasterClient,
    PilasterUnavailableError,
    RenderJob,
    build_image_prompt,
    create_image_content,
    extract_common_elements,
)
from holus.agents.marketing.models import ContentDecision, ContentType, Platform

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decision(**overrides) -> ContentDecision:
    """Create a minimal ContentDecision for testing."""
    defaults = {
        "product": "pilaster",
        "platform": Platform.LINKEDIN,
        "content_type": ContentType.TUTORIAL,
        "topic": "ComfyUI workflow tips",
        "reasoning": "tutorials perform well",
    }
    defaults.update(overrides)
    return ContentDecision(**defaults)


def _experiment(**overrides) -> ExperimentMatch:
    defaults = {
        "snapshot_id": "snap-001",
        "project_name": "test-project",
        "version_name": "v1",
        "intent": "tutorial screenshot walkthrough guide",
        "outcome": "worked",
        "rank": 0.9,
    }
    defaults.update(overrides)
    return ExperimentMatch(**defaults)


# ===========================================================================
# Models
# ===========================================================================


class TestExperimentMatch:
    def test_defaults(self):
        m = ExperimentMatch(snapshot_id="s1")
        assert m.snapshot_id == "s1"
        assert m.project_name == ""
        assert m.outcome is None
        assert m.image_url is None
        assert m.rank == 0.0

    def test_full_fields(self):
        m = _experiment(image_url="https://img.test/1.png")
        assert m.outcome == "worked"
        assert m.image_url == "https://img.test/1.png"


class TestRenderJob:
    def test_basic(self):
        j = RenderJob(run_id="r1", status="pending")
        assert j.run_id == "r1"
        assert j.result_url is None

    def test_with_result(self):
        j = RenderJob(run_id="r1", status="succeeded", result_url="https://img/1.png")
        assert j.result_url == "https://img/1.png"


class TestImageResult:
    def test_defaults(self):
        r = ImageResult(image_url="https://img/1.png")
        assert r.status == "pending_review"
        assert r.learned_from == 0
        assert r.decision == {}

    def test_full(self):
        d = _decision()
        r = ImageResult(
            image_url="https://img/1.png",
            prompt_used="test prompt",
            run_id="r1",
            status="approved",
            learned_from=3,
            decision=d.model_dump(mode="json"),
        )
        assert r.learned_from == 3
        assert r.decision["product"] == "pilaster"


# ===========================================================================
# Exceptions
# ===========================================================================


class TestExceptions:
    def test_pilaster_unavailable(self):
        exc = PilasterUnavailableError("down")
        assert str(exc) == "down"

    def test_generation_failed(self):
        exc = GenerationFailedError("failed")
        assert str(exc) == "failed"


# ===========================================================================
# Constants
# ===========================================================================


class TestConstants:
    def test_base_url(self):
        assert PILASTER_BASE_URL == "http://localhost:3000"

    def test_max_wait(self):
        assert MAX_GENERATION_WAIT == 120

    def test_poll_interval(self):
        assert POLL_INTERVAL == 5

    def test_quality_threshold(self):
        assert DEFAULT_QUALITY_THRESHOLD == 7.0

    def test_content_type_queries_keys(self):
        expected = {
            "tutorial",
            "demo",
            "tips",
            "case_study",
            "carousel",
            "announcement",
            "educational",
        }
        assert set(CONTENT_TYPE_QUERIES.keys()) == expected

    def test_content_type_queries_values_are_strings(self):
        for v in CONTENT_TYPE_QUERIES.values():
            assert isinstance(v, str)
            assert len(v) > 0


# ===========================================================================
# PilasterClient
# ===========================================================================


class TestPilasterClientInit:
    def test_default_init(self):
        client = PilasterClient()
        assert client._client.base_url == httpx.URL(PILASTER_BASE_URL)

    def test_custom_url_and_key(self):
        client = PilasterClient(base_url="http://custom:8080", api_key="key123")
        assert client._client.base_url == httpx.URL("http://custom:8080")
        assert client._client.headers["authorization"] == "Bearer key123"

    def test_no_auth_header_without_key(self):
        client = PilasterClient()
        assert "authorization" not in client._client.headers


class TestSearchExperiments:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_response = httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "snap-1",
                        "project_name": "proj",
                        "version_name": "v1",
                        "intent": "test intent",
                        "outcome": "worked",
                        "rank": 0.8,
                    }
                ]
            },
            request=httpx.Request("GET", "http://test/api/search"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        results = await client.search_experiments(query="test", outcome="worked", limit=5)
        assert len(results) == 1
        assert results[0].snapshot_id == "snap-1"
        assert results[0].outcome == "worked"

    @pytest.mark.asyncio
    async def test_list_response_format(self):
        """Handles response that is a list directly (no 'results' key)."""
        mock_response = httpx.Response(
            200,
            json=[{"id": "snap-2", "intent": "direct list"}],
            request=httpx.Request("GET", "http://test/api/search"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        results = await client.search_experiments()
        assert len(results) == 1
        assert results[0].snapshot_id == "snap-2"

    @pytest.mark.asyncio
    async def test_connect_error(self):
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client._client.base_url = httpx.URL("http://test")

        with pytest.raises(PilasterUnavailableError, match="Cannot connect"):
            await client.search_experiments()

    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_response = httpx.Response(
            500,
            text="Internal Server Error",
            request=httpx.Request("GET", "http://test/api/search"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        with pytest.raises(PilasterUnavailableError, match="API error"):
            await client.search_experiments()

    @pytest.mark.asyncio
    async def test_snapshot_id_fallback(self):
        """Uses snapshot_id field when id is missing."""
        mock_response = httpx.Response(
            200,
            json={"results": [{"snapshot_id": "snap-fallback", "intent": "test"}]},
            request=httpx.Request("GET", "http://test/api/search"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        results = await client.search_experiments()
        assert results[0].snapshot_id == "snap-fallback"


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_response = httpx.Response(
            200,
            json={"run_id": "run-1", "status": "pending"},
            request=httpx.Request("POST", "http://test/api/render"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        job = await client.generate_image("snap-1")
        assert job.run_id == "run-1"
        assert job.status == "pending"

    @pytest.mark.asyncio
    async def test_connect_error(self):
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client._client.base_url = httpx.URL("http://test")

        with pytest.raises(PilasterUnavailableError, match="Cannot connect"):
            await client.generate_image("snap-1")

    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_response = httpx.Response(
            422,
            text="Bad snapshot",
            request=httpx.Request("POST", "http://test/api/render"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        with pytest.raises(PilasterUnavailableError, match="render error"):
            await client.generate_image("snap-1")

    @pytest.mark.asyncio
    async def test_id_fallback_field(self):
        """Uses 'id' when 'run_id' is missing."""
        mock_response = httpx.Response(
            200,
            json={"id": "run-fallback", "status": "pending"},
            request=httpx.Request("POST", "http://test/api/render"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        job = await client.generate_image("snap-1")
        assert job.run_id == "run-fallback"


class TestCheckRenderStatus:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_response = httpx.Response(
            200,
            json={"status": "succeeded", "result_url": "https://img/out.png"},
            request=httpx.Request("GET", "http://test/api/render/r1"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)

        job = await client.check_render_status("r1")
        assert job.run_id == "r1"
        assert job.status == "succeeded"
        assert job.result_url == "https://img/out.png"


class TestPollUntilComplete:
    @pytest.mark.asyncio
    async def test_immediate_success(self):
        client = PilasterClient()
        client.check_render_status = AsyncMock(
            return_value=RenderJob(run_id="r1", status="succeeded", result_url="https://img/1.png")
        )
        job = await client.poll_until_complete("r1", max_wait=10, poll_interval=1)
        assert job.status == "succeeded"

    @pytest.mark.asyncio
    async def test_succeeds_after_processing(self):
        client = PilasterClient()
        client.check_render_status = AsyncMock(
            side_effect=[
                RenderJob(run_id="r1", status="processing"),
                RenderJob(run_id="r1", status="succeeded", result_url="https://img/1.png"),
            ]
        )
        with patch("holus.agents.marketing.image_workflow.asyncio.sleep", new_callable=AsyncMock):
            job = await client.poll_until_complete("r1", max_wait=30, poll_interval=1)
        assert job.status == "succeeded"

    @pytest.mark.asyncio
    async def test_failed_raises(self):
        client = PilasterClient()
        client.check_render_status = AsyncMock(return_value=RenderJob(run_id="r1", status="failed"))
        with pytest.raises(GenerationFailedError, match="failed"):
            await client.poll_until_complete("r1", max_wait=10, poll_interval=1)

    @pytest.mark.asyncio
    async def test_cancelled_raises(self):
        client = PilasterClient()
        client.check_render_status = AsyncMock(
            return_value=RenderJob(run_id="r1", status="cancelled")
        )
        with pytest.raises(GenerationFailedError, match="cancelled"):
            await client.poll_until_complete("r1", max_wait=10, poll_interval=1)

    @pytest.mark.asyncio
    async def test_timeout(self):
        client = PilasterClient()
        client.check_render_status = AsyncMock(
            return_value=RenderJob(run_id="r1", status="processing")
        )
        with (
            patch("holus.agents.marketing.image_workflow.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(TimeoutError, match="timed out"),
        ):
            await client.poll_until_complete("r1", max_wait=3, poll_interval=1)

    @pytest.mark.asyncio
    async def test_recovers_from_http_error_during_poll(self):
        """HTTP errors during status check are logged and retried."""
        client = PilasterClient()
        client.check_render_status = AsyncMock(
            side_effect=[
                httpx.HTTPError("network blip"),
                RenderJob(run_id="r1", status="succeeded", result_url="https://img/1.png"),
            ]
        )
        with patch("holus.agents.marketing.image_workflow.asyncio.sleep", new_callable=AsyncMock):
            job = await client.poll_until_complete("r1", max_wait=30, poll_interval=1)
        assert job.status == "succeeded"


class TestListProjects:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_response = httpx.Response(
            200,
            json={"projects": [{"id": "p1", "name": "Test Project"}]},
            request=httpx.Request("GET", "http://test/api/projects"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        projects = await client.list_projects(limit=10)
        assert len(projects) == 1
        assert projects[0]["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_list_format(self):
        mock_response = httpx.Response(
            200,
            json=[{"id": "p1"}],
            request=httpx.Request("GET", "http://test/api/projects"),
        )
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(return_value=mock_response)
        client._client.base_url = httpx.URL("http://test")

        projects = await client.list_projects()
        assert len(projects) == 1

    @pytest.mark.asyncio
    async def test_connect_error(self):
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client._client.base_url = httpx.URL("http://test")

        with pytest.raises(PilasterUnavailableError):
            await client.list_projects()


class TestPilasterClientContextManager:
    @pytest.mark.asyncio
    async def test_aenter_aexit(self):
        client = PilasterClient()
        client._client = AsyncMock(spec=httpx.AsyncClient)
        client._client.aclose = AsyncMock()

        async with client as c:
            assert c is client
        client._client.aclose.assert_awaited_once()


# ===========================================================================
# extract_common_elements
# ===========================================================================


class TestExtractCommonElements:
    def test_empty_list(self):
        assert extract_common_elements([]) == []

    def test_single_experiment(self):
        """With 1 experiment, threshold is min(2,1)=1, so all words pass."""
        exps = [_experiment(intent="comfyui workflow tutorial guide")]
        result = extract_common_elements(exps)
        assert "comfyui" in result
        assert "workflow" in result

    def test_noise_words_filtered(self):
        exps = [_experiment(intent="the workflow for the user")]
        result = extract_common_elements(exps)
        assert "the" not in result
        assert "for" not in result

    def test_common_across_two(self):
        exps = [
            _experiment(intent="comfyui workflow tutorial basics"),
            _experiment(intent="comfyui rendering workflow advanced"),
        ]
        result = extract_common_elements(exps)
        assert "comfyui" in result
        assert "workflow" in result
        # 'tutorial' appears only once — should not be in result
        assert "tutorial" not in result

    def test_max_10_results(self):
        """Returns at most 10 keywords."""
        intent = " ".join(f"word{i}" for i in range(20))
        exps = [_experiment(intent=intent), _experiment(intent=intent)]
        result = extract_common_elements(exps)
        assert len(result) <= 10

    def test_short_words_excluded(self):
        """Words <= 2 chars are excluded."""
        exps = [_experiment(intent="ai ml is ok not")]
        result = extract_common_elements(exps)
        assert "ai" not in result
        assert "ml" not in result


# ===========================================================================
# build_image_prompt
# ===========================================================================


class TestBuildImagePrompt:
    def test_basic_prompt_includes_topic(self):
        d = _decision(topic="ComfyUI tips")
        prompt = build_image_prompt(d, [])
        assert "ComfyUI tips" in prompt

    def test_linkedin_guidance(self):
        d = _decision(platform=Platform.LINKEDIN)
        prompt = build_image_prompt(d, [])
        assert "professional" in prompt

    def test_instagram_guidance(self):
        d = _decision(platform=Platform.INSTAGRAM)
        prompt = build_image_prompt(d, [])
        assert "vibrant" in prompt

    def test_twitter_guidance(self):
        d = _decision(platform=Platform.TWITTER)
        prompt = build_image_prompt(d, [])
        assert "bold" in prompt

    def test_tiktok_guidance(self):
        d = _decision(platform=Platform.TIKTOK)
        prompt = build_image_prompt(d, [])
        assert "vibrant" in prompt

    def test_tutorial_content_type(self):
        d = _decision(content_type=ContentType.TUTORIAL)
        prompt = build_image_prompt(d, [])
        assert "informative" in prompt

    def test_educational_content_type(self):
        d = _decision(content_type=ContentType.EDUCATIONAL)
        prompt = build_image_prompt(d, [])
        assert "step-by-step" in prompt

    def test_demo_content_type(self):
        d = _decision(content_type=ContentType.DEMO)
        prompt = build_image_prompt(d, [])
        assert "product showcase" in prompt

    def test_announcement_content_type(self):
        d = _decision(content_type=ContentType.ANNOUNCEMENT)
        prompt = build_image_prompt(d, [])
        assert "celebratory" in prompt

    def test_includes_experiment_keywords(self):
        exps = [
            _experiment(intent="comfyui workflow tutorial basics"),
            _experiment(intent="comfyui rendering workflow advanced"),
        ]
        d = _decision()
        prompt = build_image_prompt(d, exps)
        assert "comfyui" in prompt
        assert "workflow" in prompt

    def test_no_experiment_keywords_when_none(self):
        d = _decision(topic="simple topic")
        prompt = build_image_prompt(d, [])
        # Should just have topic + platform + content type parts
        parts = prompt.split(", ")
        assert parts[0] == "simple topic"


# ===========================================================================
# create_image_content (end-to-end orchestrator)
# ===========================================================================


class TestCreateImageContent:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        """Full workflow: search → prompt → generate → poll → result."""
        d = _decision()
        mock_client = AsyncMock(spec=PilasterClient)
        mock_client.search_experiments = AsyncMock(
            return_value=[_experiment(snapshot_id="snap-best")]
        )
        mock_client.generate_image = AsyncMock(
            return_value=RenderJob(run_id="run-1", status="pending")
        )
        mock_client.poll_until_complete = AsyncMock(
            return_value=RenderJob(
                run_id="run-1", status="succeeded", result_url="https://img/out.png"
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.image_workflow.PilasterClient",
            return_value=mock_client,
        ):
            result = await create_image_content(d, base_url="http://test", api_key="key")

        assert result.image_url == "https://img/out.png"
        assert result.status == "pending_review"
        assert result.run_id == "run-1"
        assert result.learned_from == 1
        assert result.decision["product"] == "pilaster"

    @pytest.mark.asyncio
    async def test_no_snapshot_fallback(self):
        """When no experiments exist, returns no_snapshot status."""
        d = _decision()
        mock_client = AsyncMock(spec=PilasterClient)
        mock_client.search_experiments = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.image_workflow.PilasterClient",
            return_value=mock_client,
        ):
            result = await create_image_content(d, base_url="http://test")

        assert result.status == "no_snapshot"
        assert result.image_url == ""
        assert result.prompt_used != ""

    @pytest.mark.asyncio
    async def test_pilaster_unavailable_for_search(self):
        """When Pilaster is down for search, falls back to no_snapshot."""
        d = _decision()
        mock_client = AsyncMock(spec=PilasterClient)
        mock_client.search_experiments = AsyncMock(side_effect=PilasterUnavailableError("down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.image_workflow.PilasterClient",
            return_value=mock_client,
        ):
            result = await create_image_content(d, base_url="http://test")

        assert result.status == "no_snapshot"

    @pytest.mark.asyncio
    async def test_fallback_search_finds_snapshot(self):
        """When no 'worked' experiments, fallback search without outcome filter."""
        d = _decision()
        mock_client = AsyncMock(spec=PilasterClient)
        # First call (outcome=worked) returns empty, second call returns one
        mock_client.search_experiments = AsyncMock(
            side_effect=[
                [],  # no successful experiments
                [_experiment(snapshot_id="snap-fallback", outcome=None)],  # fallback search
            ]
        )
        mock_client.generate_image = AsyncMock(
            return_value=RenderJob(run_id="run-2", status="pending")
        )
        mock_client.poll_until_complete = AsyncMock(
            return_value=RenderJob(
                run_id="run-2", status="succeeded", result_url="https://img/fb.png"
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.image_workflow.PilasterClient",
            return_value=mock_client,
        ):
            result = await create_image_content(d, base_url="http://test")

        assert result.image_url == "https://img/fb.png"
        assert result.learned_from == 0  # no successful experiments used

    @pytest.mark.asyncio
    async def test_generation_failed_propagates(self):
        """GenerationFailedError from poll propagates to caller."""
        d = _decision()
        mock_client = AsyncMock(spec=PilasterClient)
        mock_client.search_experiments = AsyncMock(return_value=[_experiment(snapshot_id="snap-1")])
        mock_client.generate_image = AsyncMock(
            return_value=RenderJob(run_id="run-1", status="pending")
        )
        mock_client.poll_until_complete = AsyncMock(
            side_effect=GenerationFailedError("generation failed")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "holus.agents.marketing.image_workflow.PilasterClient",
                return_value=mock_client,
            ),
            pytest.raises(GenerationFailedError),
        ):
            await create_image_content(d, base_url="http://test")

    @pytest.mark.asyncio
    async def test_timeout_propagates(self):
        """TimeoutError from poll propagates to caller."""
        d = _decision()
        mock_client = AsyncMock(spec=PilasterClient)
        mock_client.search_experiments = AsyncMock(return_value=[_experiment(snapshot_id="snap-1")])
        mock_client.generate_image = AsyncMock(
            return_value=RenderJob(run_id="run-1", status="pending")
        )
        mock_client.poll_until_complete = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "holus.agents.marketing.image_workflow.PilasterClient",
                return_value=mock_client,
            ),
            pytest.raises(TimeoutError),
        ):
            await create_image_content(d, base_url="http://test")

    @pytest.mark.asyncio
    async def test_env_var_fallback(self):
        """Uses env vars when base_url and api_key not provided."""
        d = _decision()
        mock_client = AsyncMock(spec=PilasterClient)
        mock_client.search_experiments = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.dict(
                "os.environ",
                {"PILASTER_BASE_URL": "http://env:9000", "PILASTER_API_KEY": "env-key"},
            ),
            patch(
                "holus.agents.marketing.image_workflow.PilasterClient",
                return_value=mock_client,
            ) as mock_cls,
        ):
            await create_image_content(d)

        mock_cls.assert_called_once_with(base_url="http://env:9000", api_key="env-key")

    @pytest.mark.asyncio
    async def test_content_type_query_used(self):
        """Uses CONTENT_TYPE_QUERIES mapping for search query."""
        d = _decision(content_type=ContentType.DEMO)
        mock_client = AsyncMock(spec=PilasterClient)
        mock_client.search_experiments = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "holus.agents.marketing.image_workflow.PilasterClient",
            return_value=mock_client,
        ):
            await create_image_content(d, base_url="http://test")

        # First search call should use the mapped query for "demo"
        call_args = mock_client.search_experiments.call_args_list[0]
        assert (
            call_args.kwargs.get("query") == "demo product preview"
            or call_args[1].get("query") == "demo product preview"
        )
