"""Integration client tests for SocialMediaClient.

Focused tests for HTTP interactions: publish, analytics, top-posts,
schedule, health, retry behavior, and async context manager lifecycle.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from holus.integrations.social_media import (
    HOLUS_SOCIAL_API_BASE_URL_ENV,
    HOLUS_SOCIAL_API_KEY_ENV,
    HolusSocialAPIClient,
    PublishRequest,
    PublishResult,
    ScheduleRequest,
    ScheduleResult,
    SocialMediaClient,
)


@pytest.fixture
def client():
    """Create a test client with a fake API key."""
    return SocialMediaClient(base_url="http://test:8000", api_key="test-key-123")


@pytest.fixture
def mock_http():
    """Mock httpx.AsyncClient with async get/post."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    return mock


def _ok_response(data: dict, *, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response that returns the given JSON."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(
    status_code: int, method: str = "GET", url: str = "http://test:8000"
) -> httpx.HTTPStatusError:
    """Build an HTTPStatusError for the given status code."""
    return httpx.HTTPStatusError(
        f"HTTP {status_code}",
        request=httpx.Request(method, url),
        response=httpx.Response(status_code),
    )


class TestPublishContent:
    """test_publish_content -- mock httpx, verify POST to /api/v1/publish with correct payload."""

    @pytest.mark.asyncio
    async def test_publish_content(self, client, mock_http):
        """POST /api/v1/publish is called with correct payload and result is parsed."""
        mock_http.post.return_value = _ok_response(
            {
                "publish_id": "pub_100",
                "targets": [
                    {
                        "platform": "linkedin",
                        "account": "main",
                        "language": "en",
                        "status": "queued",
                    },
                ],
                "warnings": [],
            }
        )

        with patch.object(client, "client", mock_http):
            request = PublishRequest(
                content="New feature launched!",
                platforms=["linkedin"],
                media_url="https://cdn.example.com/hero.png",
                media_type="image",
            )
            result = await client.publish(request)

        # Verify correct endpoint
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/api/v1/publish"

        # Verify payload
        payload = call_args[1]["json"]
        assert payload["content"] == "New feature launched!"
        assert payload["platforms"] == ["linkedin"]
        assert payload["media_url"] == "https://cdn.example.com/hero.png"
        assert payload["media_type"] == "image"

        # Verify parsed result
        assert isinstance(result, PublishResult)
        assert result.publish_id == "pub_100"
        assert result.targets[0].platform == "linkedin"
        assert result.succeeded is True


class TestHolusSocialAPIEnv:
    """Environment resolution for the renamed client."""

    @pytest.mark.asyncio
    async def test_new_env_vars_are_preferred_over_legacy_aliases(self):
        with patch.dict(
            "os.environ",
            {
                HOLUS_SOCIAL_API_BASE_URL_ENV: "http://new-holus-social.test/",
                HOLUS_SOCIAL_API_KEY_ENV: "new-key",
                "SOCIAL_MEDIA_API_BASE_URL": "http://legacy-social.test",
                "POSTING_API_KEY": "legacy-key",
            },
            clear=False,
        ):
            client = HolusSocialAPIClient()
            try:
                assert client.base_url == "http://new-holus-social.test"
                assert client.api_key == "new-key"
            finally:
                await client.close()

    @pytest.mark.asyncio
    async def test_legacy_env_aliases_still_work(self):
        with patch.dict(
            "os.environ",
            {
                "SOCIAL_MEDIA_API_BASE_URL": "http://legacy-social.test",
                "POSTING_API_KEY": "legacy-key",
            },
            clear=True,
        ):
            client = HolusSocialAPIClient()
            try:
                assert client.base_url == "http://legacy-social.test"
                assert client.api_key == "legacy-key"
            finally:
                await client.close()


class TestPublishValidatesCharLimit:
    """test_publish_validates_char_limit -- content exceeding platform limit raises ValueError."""

    @pytest.mark.asyncio
    async def test_publish_validates_char_limit_twitter(self, client):
        """Content over Twitter's 280-char limit raises ValueError before any HTTP call."""
        request = PublishRequest(content="x" * 281, platforms=["twitter"])
        with pytest.raises(ValueError, match="Content validation failed"):
            await client.publish(request)

    @pytest.mark.asyncio
    async def test_publish_validates_char_limit_threads(self, client):
        """Content over Threads' 500-char limit raises ValueError."""
        request = PublishRequest(content="y" * 501, platforms=["threads"])
        with pytest.raises(ValueError, match="Content validation failed"):
            await client.publish(request)

    @pytest.mark.asyncio
    async def test_publish_validates_char_limit_no_http_call(self, client, mock_http):
        """Validation failure prevents any HTTP request from being made."""
        with patch.object(client, "client", mock_http):
            request = PublishRequest(content="z" * 3001, platforms=["linkedin"])
            with pytest.raises(ValueError):
                await client.publish(request)
        mock_http.post.assert_not_called()


class TestGetAnalytics:
    """test_get_analytics -- mock httpx, verify GET /api/v1/analytics with date params."""

    @pytest.mark.asyncio
    async def test_get_analytics_default_params(self, client, mock_http):
        """GET /api/v1/analytics sends days=7 by default."""
        mock_http.get.return_value = _ok_response(
            {
                "total_posts": 10,
                "success_rate": 0.9,
                "platforms": {"linkedin": {"posts": 10}},
            }
        )

        with patch.object(client, "client", mock_http):
            result = await client.get_analytics()

        mock_http.get.assert_called_once_with("/api/v1/analytics", params={"days": 7})
        assert result["total_posts"] == 10

    @pytest.mark.asyncio
    async def test_get_analytics_custom_params(self, client, mock_http):
        """GET /api/v1/analytics passes custom days and platform filter."""
        mock_http.get.return_value = _ok_response({"total_posts": 5})

        with patch.object(client, "client", mock_http):
            result = await client.get_analytics(days=30, platform="twitter")

        mock_http.get.assert_called_once_with(
            "/api/v1/analytics",
            params={"days": 30, "platform": "twitter"},
        )
        assert result["total_posts"] == 5


class TestGetTopPosts:
    """test_get_top_posts -- mock httpx, verify GET /api/v1/analytics/top-posts."""

    @pytest.mark.asyncio
    async def test_get_top_posts_default(self, client, mock_http):
        """GET /api/v1/analytics/top-posts sends default limit/days/metric."""
        mock_http.get.return_value = _ok_response(
            {
                "posts": [{"id": 1, "content": "Top post"}],
            }
        )

        with patch.object(client, "client", mock_http):
            result = await client.get_top_posts()

        mock_http.get.assert_called_once_with(
            "/api/v1/analytics/top-posts",
            params={"limit": 10, "days": 30, "metric": "recent"},
        )
        assert len(result["posts"]) == 1

    @pytest.mark.asyncio
    async def test_get_top_posts_custom(self, client, mock_http):
        """GET /api/v1/analytics/top-posts respects custom params."""
        mock_http.get.return_value = _ok_response({"posts": []})

        with patch.object(client, "client", mock_http):
            await client.get_top_posts(limit=3, days=7, metric="engagement")

        mock_http.get.assert_called_once_with(
            "/api/v1/analytics/top-posts",
            params={"limit": 3, "days": 7, "metric": "engagement"},
        )


class TestSchedulePost:
    """test_schedule_post -- mock httpx, verify POST /api/v1/schedule."""

    @pytest.mark.asyncio
    async def test_schedule_post(self, client, mock_http):
        """POST /api/v1/schedule is called with correct payload and result is parsed."""
        mock_http.post.return_value = _ok_response(
            {
                "schedule_id": "sched_10",
                "status": "pending_approval",
                "platform": "linkedin",
                "approval_required": True,
            }
        )

        with patch.object(client, "client", mock_http):
            request = ScheduleRequest(
                content="Scheduled insight",
                platform="linkedin",
                approval_required=True,
                scheduled_at="2026-04-01T09:00:00Z",
            )
            result = await client.schedule_post(request)

        # Verify endpoint
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/api/v1/schedule"

        # Verify payload
        payload = call_args[1]["json"]
        assert payload["content"] == "Scheduled insight"
        assert payload["platforms"] == ["linkedin"]
        assert "platform" not in payload
        assert payload["approval_required"] is True
        assert payload["scheduled_at"] == "2026-04-01T09:00:00Z"

        # Verify parsed result
        assert isinstance(result, ScheduleResult)
        assert result.schedule_id == "sched_10"
        assert result.status == "pending_approval"

    @pytest.mark.asyncio
    async def test_schedule_post_validates_char_limit(self, client):
        """Schedule validates platform char limit before HTTP call."""
        request = ScheduleRequest(content="x" * 281, platform="twitter")
        with pytest.raises(ValueError, match="Content validation failed"):
            await client.schedule_post(request)


class TestHealthCheck:
    """test_health_check -- mock httpx, verify GET /api/v1/health."""

    @pytest.mark.asyncio
    async def test_health_check(self, client, mock_http):
        """GET /api/v1/health returns platform connection status."""
        mock_http.get.return_value = _ok_response(
            {
                "platforms": {
                    "linkedin": {"connected": True, "token_valid": True},
                    "twitter": {"connected": False, "token_valid": False},
                },
                "checked_at": "2026-03-26T12:00:00Z",
            }
        )

        with patch.object(client, "client", mock_http):
            result = await client.health()

        mock_http.get.assert_called_once_with("/api/v1/health")
        assert result["platforms"]["linkedin"]["connected"] is True
        assert result["platforms"]["twitter"]["connected"] is False


class TestRetryOnFailure:
    """test_retry_on_failure -- verify tenacity retry on 500 errors."""

    @pytest.mark.asyncio
    async def test_retry_publish_on_500_eventually_succeeds(self, client, mock_http):
        """Publish retries on HTTPStatusError and succeeds on third attempt."""
        error = _error_response(500, "POST", "http://test:8000/api/v1/publish")
        success = _ok_response({"publish_id": "pub_retry", "targets": [], "warnings": []})

        # Fail twice, succeed on third
        mock_http.post.side_effect = [error, error, success]

        with patch.object(client, "client", mock_http):
            # Patch tenacity wait to avoid real delays
            original_publish = client.publish
            with patch.object(original_publish.retry, "wait", return_value=0):
                request = PublishRequest(content="Retry me", platforms=["linkedin"])
                result = await client.publish(request)

        assert result.publish_id == "pub_retry"
        assert mock_http.post.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_publish_exhausted_reraises(self, client, mock_http):
        """Publish reraises after exhausting all 3 retry attempts."""
        error = _error_response(500, "POST", "http://test:8000/api/v1/publish")
        mock_http.post.side_effect = [error, error, error]

        with (
            patch.object(client, "client", mock_http),
            patch.object(client.publish.retry, "wait", return_value=0),
        ):
            request = PublishRequest(content="Will fail", platforms=["linkedin"])
            with pytest.raises(httpx.HTTPStatusError):
                await client.publish(request)

        assert mock_http.post.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_schedule_on_500(self, client, mock_http):
        """schedule_post also retries on HTTPStatusError."""
        error = _error_response(503, "POST", "http://test:8000/api/v1/schedule")
        success = _ok_response({"schedule_id": "sched_retry", "status": "pending_approval"})

        mock_http.post.side_effect = [error, success]

        with (
            patch.object(client, "client", mock_http),
            patch.object(client.schedule_post.retry, "wait", return_value=0),
        ):
            request = ScheduleRequest(content="Retry schedule", platform="linkedin")
            result = await client.schedule_post(request)

        assert result.schedule_id == "sched_retry"
        assert mock_http.post.call_count == 2


class TestContextManager:
    """test_context_manager -- verify async context manager opens/closes client."""

    @pytest.mark.asyncio
    async def test_context_manager_returns_client(self):
        """async with SocialMediaClient(...) yields the client instance."""
        async with SocialMediaClient(api_key="ctx-key") as c:
            assert isinstance(c, SocialMediaClient)
            assert c.client is not None
            assert c.api_key == "ctx-key"

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exit(self):
        """Exiting the context manager closes the underlying httpx client."""
        client = SocialMediaClient(api_key="ctx-key-2")
        mock_aclose = AsyncMock()
        client.client.aclose = mock_aclose

        async with client:
            pass

        mock_aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self):
        """Context manager still closes the client even if an exception occurs."""
        client = SocialMediaClient(api_key="ctx-key-3")
        mock_aclose = AsyncMock()
        client.client.aclose = mock_aclose

        with pytest.raises(RuntimeError, match="boom"):
            async with client:
                raise RuntimeError("boom")

        mock_aclose.assert_awaited_once()
