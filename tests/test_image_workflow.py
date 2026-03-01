"""Tests for holus.agents.marketing.image_workflow.

Tests cover:
  - Experiment search via PilasterClient
  - Render job submission and polling
  - Common element extraction from experiments
  - Prompt building from decisions + past experiments
  - End-to-end create_image_content orchestrator
  - Error paths (unavailable, generation failed, timeout, no snapshot)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from holus.agents.marketing.image_workflow import (
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

_DUMMY_REQUEST = httpx.Request("GET", "http://test:3000")


def _resp(status_code: int = 200, *, json: dict[str, Any] | None = None) -> httpx.Response:
    """Create an httpx.Response with a request set (needed for raise_for_status)."""
    return httpx.Response(status_code, json=json, request=_DUMMY_REQUEST)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tutorial_decision() -> ContentDecision:
    """A tutorial content decision for LinkedIn."""
    return ContentDecision(
        product="pilaster",
        platform=Platform.LINKEDIN,
        content_type=ContentType.TUTORIAL,
        topic="How to use Pilaster workflow versioning",
        reasoning="Tutorial posts get 4x engagement on LinkedIn",
        priority=1,
        estimated_engagement="high",
    )


@pytest.fixture
def demo_decision() -> ContentDecision:
    """A demo content decision for Instagram."""
    return ContentDecision(
        product="pilaster",
        platform=Platform.INSTAGRAM,
        content_type=ContentType.DEMO,
        topic="Pilaster AI image generation demo",
        reasoning="Visual demos perform well on Instagram",
        priority=2,
        estimated_engagement="medium",
    )


@pytest.fixture
def announcement_decision() -> ContentDecision:
    """An announcement content decision for Twitter."""
    return ContentDecision(
        product="genpeli",
        platform=Platform.TWITTER,
        content_type=ContentType.ANNOUNCEMENT,
        topic="Genpeli v2 launch",
        reasoning="New version launch announcement",
        priority=1,
        estimated_engagement="high",
    )


@pytest.fixture
def successful_experiments() -> list[ExperimentMatch]:
    """A list of successful past experiments."""
    return [
        ExperimentMatch(
            snapshot_id="snap-001",
            project_name="pilaster-marketing",
            version_name="v3",
            intent="Create clean product screenshot with modern UI design",
            outcome="worked",
            image_url="https://r2.pilaster.ai/snap-001.png",
            rank=0.9,
        ),
        ExperimentMatch(
            snapshot_id="snap-002",
            project_name="pilaster-marketing",
            version_name="v5",
            intent="Generate clean tutorial screenshot with step indicators",
            outcome="worked",
            image_url="https://r2.pilaster.ai/snap-002.png",
            rank=0.85,
        ),
        ExperimentMatch(
            snapshot_id="snap-003",
            project_name="pilaster-marketing",
            version_name="v1",
            intent="Create modern product showcase with clean design",
            outcome="worked",
            image_url="https://r2.pilaster.ai/snap-003.png",
            rank=0.8,
        ),
    ]


# ---------------------------------------------------------------------------
# extract_common_elements
# ---------------------------------------------------------------------------


class TestExtractCommonElements:
    def test_finds_common_words(self, successful_experiments: list[ExperimentMatch]) -> None:
        common = extract_common_elements(successful_experiments)
        assert "clean" in common  # appears in 3/3 experiments
        assert "product" in common  # appears in 2/3

    def test_empty_experiments_returns_empty(self) -> None:
        assert extract_common_elements([]) == []

    def test_single_experiment(self) -> None:
        exps = [
            ExperimentMatch(
                snapshot_id="s1",
                intent="vibrant colorful abstract background",
            )
        ]
        # With only 1 experiment, threshold becomes 1
        result = extract_common_elements(exps)
        assert len(result) > 0

    def test_filters_noise_words(self, successful_experiments: list[ExperimentMatch]) -> None:
        common = extract_common_elements(successful_experiments)
        noise = {"the", "a", "an", "and", "or", "for", "to", "in", "of", "with"}
        assert not any(w in noise for w in common)

    def test_limits_to_ten(self) -> None:
        exps = [
            ExperimentMatch(
                snapshot_id=f"s{i}",
                intent=f"word{j} " * 20,
            )
            for i in range(10)
            for j in range(20)
        ]
        common = extract_common_elements(exps)
        assert len(common) <= 10


# ---------------------------------------------------------------------------
# build_image_prompt
# ---------------------------------------------------------------------------


class TestBuildImagePrompt:
    def test_includes_topic(self, tutorial_decision: ContentDecision) -> None:
        prompt = build_image_prompt(tutorial_decision, [])
        assert "Pilaster workflow versioning" in prompt

    def test_linkedin_gets_professional(self, tutorial_decision: ContentDecision) -> None:
        prompt = build_image_prompt(tutorial_decision, [])
        assert "professional" in prompt

    def test_instagram_gets_vibrant(self, demo_decision: ContentDecision) -> None:
        prompt = build_image_prompt(demo_decision, [])
        assert "vibrant" in prompt

    def test_twitter_gets_bold(self, announcement_decision: ContentDecision) -> None:
        prompt = build_image_prompt(announcement_decision, [])
        assert "bold" in prompt

    def test_tutorial_gets_informative(self, tutorial_decision: ContentDecision) -> None:
        prompt = build_image_prompt(tutorial_decision, [])
        assert "informative" in prompt

    def test_demo_gets_showcase(self, demo_decision: ContentDecision) -> None:
        prompt = build_image_prompt(demo_decision, [])
        assert "product showcase" in prompt

    def test_announcement_gets_celebratory(self, announcement_decision: ContentDecision) -> None:
        prompt = build_image_prompt(announcement_decision, [])
        assert "celebratory" in prompt

    def test_incorporates_experiment_patterns(
        self,
        tutorial_decision: ContentDecision,
        successful_experiments: list[ExperimentMatch],
    ) -> None:
        prompt_without = build_image_prompt(tutorial_decision, [])
        prompt_with = build_image_prompt(tutorial_decision, successful_experiments)
        # Prompt with experiments should be longer (includes learned patterns)
        assert len(prompt_with) > len(prompt_without)

    def test_no_experiments_still_produces_prompt(self, tutorial_decision: ContentDecision) -> None:
        prompt = build_image_prompt(tutorial_decision, [])
        assert len(prompt) > 0


# ---------------------------------------------------------------------------
# PilasterClient
# ---------------------------------------------------------------------------


class TestPilasterClient:
    @pytest.mark.asyncio
    async def test_search_experiments_success(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(
                    json={
                        "results": [
                            {
                                "id": "snap-001",
                                "project_name": "test-project",
                                "version_name": "v1",
                                "intent": "test image",
                                "outcome": "worked",
                                "run_image_url": "https://example.com/img.png",
                                "rank": 0.95,
                            }
                        ],
                        "count": 1,
                    }
                )
            )

            results = await client.search_experiments(query="test", outcome="worked", limit=5)
            assert len(results) == 1
            assert results[0].snapshot_id == "snap-001"
            assert results[0].outcome == "worked"
            assert results[0].image_url == "https://example.com/img.png"

    @pytest.mark.asyncio
    async def test_search_experiments_connect_error(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with pytest.raises(PilasterUnavailableError, match="Cannot connect"):
                await client.search_experiments(query="test")

    @pytest.mark.asyncio
    async def test_search_experiments_http_error(self) -> None:
        mock_request = httpx.Request("GET", "http://test:3000/api/search")
        mock_response = httpx.Response(500, text="Internal Server Error", request=mock_request)

        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server error", request=mock_request, response=mock_response
                )
            )

            with pytest.raises(PilasterUnavailableError, match="API error"):
                await client.search_experiments(query="test")

    @pytest.mark.asyncio
    async def test_generate_image_success(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.post = AsyncMock(
                return_value=_resp(
                    json={
                        "run_id": "run-abc",
                        "status": "pending",
                    }
                )
            )

            job = await client.generate_image("snap-001")
            assert job.run_id == "run-abc"
            assert job.status == "pending"

    @pytest.mark.asyncio
    async def test_generate_image_connect_error(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with pytest.raises(PilasterUnavailableError, match="Cannot connect"):
                await client.generate_image("snap-001")

    @pytest.mark.asyncio
    async def test_check_render_status(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(
                    json={
                        "status": "succeeded",
                        "result_url": "https://r2.pilaster.ai/output.png",
                    }
                )
            )

            job = await client.check_render_status("run-abc")
            assert job.status == "succeeded"
            assert job.result_url == "https://r2.pilaster.ai/output.png"

    @pytest.mark.asyncio
    async def test_poll_until_complete_immediate(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(
                    json={
                        "status": "succeeded",
                        "result_url": "https://r2.pilaster.ai/output.png",
                    }
                )
            )

            job = await client.poll_until_complete("run-abc", max_wait=10, poll_interval=1)
            assert job.status == "succeeded"

    @pytest.mark.asyncio
    async def test_poll_until_complete_after_processing(self) -> None:
        responses = [
            _resp(json={"status": "processing"}),
            _resp(json={"status": "processing"}),
            _resp(json={"status": "succeeded", "result_url": "https://r2.pilaster.ai/out.png"}),
        ]

        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(side_effect=responses)

            with patch(
                "holus.agents.marketing.image_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                job = await client.poll_until_complete("run-abc", max_wait=60, poll_interval=1)
                assert job.status == "succeeded"

    @pytest.mark.asyncio
    async def test_poll_until_complete_failed(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(return_value=_resp(json={"status": "failed"}))

            with pytest.raises(GenerationFailedError, match="failed"):
                await client.poll_until_complete("run-abc", max_wait=10, poll_interval=1)

    @pytest.mark.asyncio
    async def test_poll_until_complete_cancelled(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(return_value=_resp(json={"status": "cancelled"}))

            with pytest.raises(GenerationFailedError, match="cancelled"):
                await client.poll_until_complete("run-abc", max_wait=10, poll_interval=1)

    @pytest.mark.asyncio
    async def test_poll_until_complete_timeout(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(return_value=_resp(json={"status": "processing"}))

            with (
                patch(
                    "holus.agents.marketing.image_workflow.asyncio.sleep",
                    new_callable=AsyncMock,
                ),
                pytest.raises(TimeoutError, match="timed out"),
            ):
                await client.poll_until_complete("run-abc", max_wait=2, poll_interval=1)

    @pytest.mark.asyncio
    async def test_poll_until_complete_transient_error(self) -> None:
        """Transient HTTP errors during polling are retried, not fatal."""
        responses: list[httpx.Response | httpx.HTTPError] = [
            httpx.HTTPError("Network blip"),
            _resp(json={"status": "succeeded", "result_url": "https://r2.pilaster.ai/out.png"}),
        ]
        call_count = 0

        async def mock_get(url: str) -> httpx.Response:
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            if isinstance(resp, Exception):
                raise resp
            return resp

        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = mock_get

            with patch(
                "holus.agents.marketing.image_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                job = await client.poll_until_complete("run-abc", max_wait=30, poll_interval=1)
                assert job.status == "succeeded"

    @pytest.mark.asyncio
    async def test_list_projects_success(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(
                return_value=_resp(
                    json={
                        "projects": [
                            {"id": "proj-1", "name": "marketing", "snapshot_count": 5},
                            {"id": "proj-2", "name": "characters", "snapshot_count": 12},
                        ],
                        "count": 2,
                    }
                )
            )

            projects = await client.list_projects()
            assert len(projects) == 2
            assert projects[0]["name"] == "marketing"

    @pytest.mark.asyncio
    async def test_list_projects_connect_error(self) -> None:
        async with PilasterClient(base_url="http://test:3000") as client:
            client._client = AsyncMock()
            client._client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with pytest.raises(PilasterUnavailableError, match="Cannot connect"):
                await client.list_projects()

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        client = PilasterClient(base_url="http://test:3000")
        async with client as c:
            assert c is client


# ---------------------------------------------------------------------------
# create_image_content (end-to-end orchestrator)
# ---------------------------------------------------------------------------


class TestCreateImageContent:
    @pytest.mark.asyncio
    async def test_full_workflow(self, tutorial_decision: ContentDecision) -> None:
        """Happy path: experiments found, snapshot selected, image generated."""
        with (
            patch("holus.agents.marketing.image_workflow.PilasterClient") as mock_cls,
            patch(
                "holus.agents.marketing.image_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_instance = AsyncMock()
            mock_instance.search_experiments = AsyncMock(
                return_value=[
                    ExperimentMatch(
                        snapshot_id="snap-best",
                        intent="tutorial screenshot",
                        outcome="worked",
                        rank=0.9,
                    )
                ]
            )
            mock_instance.generate_image = AsyncMock(
                return_value=RenderJob(run_id="run-123", status="pending")
            )
            mock_instance.poll_until_complete = AsyncMock(
                return_value=RenderJob(
                    run_id="run-123",
                    status="succeeded",
                    result_url="https://r2.pilaster.ai/final.png",
                )
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            result = await create_image_content(
                tutorial_decision,
                base_url="http://test:3000",
            )

            assert isinstance(result, ImageResult)
            assert result.image_url == "https://r2.pilaster.ai/final.png"
            assert result.status == "pending_review"
            assert result.run_id == "run-123"
            assert result.learned_from == 1
            assert result.decision["product"] == "pilaster"
            assert len(result.prompt_used) > 0

    @pytest.mark.asyncio
    async def test_no_experiments_uses_fallback_search(
        self, tutorial_decision: ContentDecision
    ) -> None:
        """When no successful experiments, searches without outcome filter."""
        with (
            patch("holus.agents.marketing.image_workflow.PilasterClient") as mock_cls,
            patch(
                "holus.agents.marketing.image_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_instance = AsyncMock()
            # First search (outcome=worked) returns nothing
            # Second search (no outcome filter) returns a snapshot
            mock_instance.search_experiments = AsyncMock(
                side_effect=[
                    [],  # no successful experiments
                    [ExperimentMatch(snapshot_id="snap-any", intent="some image")],
                ]
            )
            mock_instance.generate_image = AsyncMock(
                return_value=RenderJob(run_id="run-456", status="pending")
            )
            mock_instance.poll_until_complete = AsyncMock(
                return_value=RenderJob(
                    run_id="run-456",
                    status="succeeded",
                    result_url="https://r2.pilaster.ai/fallback.png",
                )
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            result = await create_image_content(
                tutorial_decision,
                base_url="http://test:3000",
            )

            assert result.image_url == "https://r2.pilaster.ai/fallback.png"
            assert result.learned_from == 0  # no successful experiments used

    @pytest.mark.asyncio
    async def test_no_snapshot_returns_prompt_only(
        self, tutorial_decision: ContentDecision
    ) -> None:
        """When no snapshots exist at all, return prompt-only result."""
        with patch("holus.agents.marketing.image_workflow.PilasterClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.search_experiments = AsyncMock(return_value=[])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            result = await create_image_content(
                tutorial_decision,
                base_url="http://test:3000",
            )

            assert result.status == "no_snapshot"
            assert result.image_url == ""
            assert len(result.prompt_used) > 0

    @pytest.mark.asyncio
    async def test_pilaster_unavailable_for_search(
        self, tutorial_decision: ContentDecision
    ) -> None:
        """When Pilaster is unavailable for search, returns prompt-only result."""
        with patch("holus.agents.marketing.image_workflow.PilasterClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.search_experiments = AsyncMock(
                side_effect=PilasterUnavailableError("Cannot connect")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            result = await create_image_content(
                tutorial_decision,
                base_url="http://test:3000",
            )

            assert result.status == "no_snapshot"
            assert result.image_url == ""
            assert len(result.prompt_used) > 0

    @pytest.mark.asyncio
    async def test_generation_failed(self, tutorial_decision: ContentDecision) -> None:
        """When generation fails, propagates the error."""
        with (
            patch("holus.agents.marketing.image_workflow.PilasterClient") as mock_cls,
            patch(
                "holus.agents.marketing.image_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_instance = AsyncMock()
            mock_instance.search_experiments = AsyncMock(
                return_value=[
                    ExperimentMatch(snapshot_id="snap-001", intent="test", outcome="worked")
                ]
            )
            mock_instance.generate_image = AsyncMock(
                return_value=RenderJob(run_id="run-bad", status="pending")
            )
            mock_instance.poll_until_complete = AsyncMock(
                side_effect=GenerationFailedError("generation failed")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            with pytest.raises(GenerationFailedError):
                await create_image_content(
                    tutorial_decision,
                    base_url="http://test:3000",
                )

    @pytest.mark.asyncio
    async def test_generation_timeout(self, tutorial_decision: ContentDecision) -> None:
        """When generation times out, propagates the error."""
        with (
            patch("holus.agents.marketing.image_workflow.PilasterClient") as mock_cls,
            patch(
                "holus.agents.marketing.image_workflow.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_instance = AsyncMock()
            mock_instance.search_experiments = AsyncMock(
                return_value=[
                    ExperimentMatch(snapshot_id="snap-001", intent="test", outcome="worked")
                ]
            )
            mock_instance.generate_image = AsyncMock(
                return_value=RenderJob(run_id="run-slow", status="pending")
            )
            mock_instance.poll_until_complete = AsyncMock(side_effect=TimeoutError("timed out"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            with pytest.raises(TimeoutError):
                await create_image_content(
                    tutorial_decision,
                    base_url="http://test:3000",
                    max_wait=5,
                )

    @pytest.mark.asyncio
    async def test_pilaster_unavailable_for_generation(
        self, tutorial_decision: ContentDecision
    ) -> None:
        """When Pilaster is unavailable for render submission, propagates."""
        with patch("holus.agents.marketing.image_workflow.PilasterClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.search_experiments = AsyncMock(
                return_value=[
                    ExperimentMatch(snapshot_id="snap-001", intent="test", outcome="worked")
                ]
            )
            mock_instance.generate_image = AsyncMock(
                side_effect=PilasterUnavailableError("Cannot connect for render")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            with pytest.raises(PilasterUnavailableError):
                await create_image_content(
                    tutorial_decision,
                    base_url="http://test:3000",
                )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_experiment_match_defaults(self) -> None:
        exp = ExperimentMatch(snapshot_id="s1")
        assert exp.outcome is None
        assert exp.image_url is None
        assert exp.rank == 0.0

    def test_render_job_defaults(self) -> None:
        job = RenderJob(run_id="r1", status="pending")
        assert job.result_url is None

    def test_image_result_defaults(self) -> None:
        result = ImageResult(image_url="https://example.com/img.png")
        assert result.status == "pending_review"
        assert result.learned_from == 0
        assert result.decision == {}

    def test_image_result_with_decision(self, tutorial_decision: ContentDecision) -> None:
        result = ImageResult(
            image_url="https://example.com/img.png",
            prompt_used="test prompt",
            run_id="run-1",
            decision=tutorial_decision.model_dump(mode="json"),
        )
        assert result.decision["product"] == "pilaster"
        assert result.decision["platform"] == "linkedin"
