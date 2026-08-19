"""Integration client tests for SocialMediaClient.

Focused tests for HTTP interactions: publish, analytics, top-posts,
schedule, health, retry behavior, and async context manager lifecycle.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holus.integrations.social_media import (
    EXTERNAL_DELIVERY_CONTAINED_MESSAGE,
    HOLUS_SOCIAL_API_BASE_URL_ENV,
    HOLUS_SOCIAL_API_KEY_ENV,
    ExternalDeliveryContainedError,
    HolusSocialAPIClient,
    PublishRequest,
    ScheduleRequest,
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


class TestPublishContent:
    """test_publish_content -- mock httpx, verify POST to /api/v1/publish with correct payload."""

    @pytest.mark.asyncio
    async def test_publish_content(self, client, mock_http):
        """Publish is contained before any POST is made."""
        with patch.object(client, "client", mock_http):
            request = PublishRequest(
                content="New feature launched!",
                platforms=["linkedin"],
                media_url="https://cdn.example.com/hero.png",
                media_type="image",
            )
            with pytest.raises(ExternalDeliveryContainedError) as exc_info:
                await client.publish(request)

        assert str(exc_info.value) == EXTERNAL_DELIVERY_CONTAINED_MESSAGE
        mock_http.post.assert_not_called()


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
    """test_publish_validates_char_limit -- direct publish is contained."""

    @pytest.mark.asyncio
    async def test_publish_validates_char_limit_twitter(self, client):
        """Content over Twitter's limit is contained before any HTTP call."""
        request = PublishRequest(content="x" * 281, platforms=["twitter"])
        with pytest.raises(ExternalDeliveryContainedError):
            await client.publish(request)

    @pytest.mark.asyncio
    async def test_publish_validates_char_limit_threads(self, client):
        """Content over Threads' limit is contained before any HTTP call."""
        request = PublishRequest(content="y" * 501, platforms=["threads"])
        with pytest.raises(ExternalDeliveryContainedError):
            await client.publish(request)

    @pytest.mark.asyncio
    async def test_publish_validates_char_limit_no_http_call(self, client, mock_http):
        """Contained direct publish prevents any HTTP request from being made."""
        with patch.object(client, "client", mock_http):
            request = PublishRequest(content="z" * 3001, platforms=["linkedin"])
            with pytest.raises(ExternalDeliveryContainedError):
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
        """Schedule is contained before any POST is made."""
        with patch.object(client, "client", mock_http):
            request = ScheduleRequest(
                content="Scheduled insight",
                platform="linkedin",
                approval_required=True,
                scheduled_at="2026-04-01T09:00:00Z",
            )
            with pytest.raises(ExternalDeliveryContainedError) as exc_info:
                await client.schedule_post(request)

        assert str(exc_info.value) == EXTERNAL_DELIVERY_CONTAINED_MESSAGE
        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_post_validates_char_limit(self, client):
        """Schedule is contained before platform char-limit validation can post."""
        request = ScheduleRequest(content="x" * 281, platform="twitter")
        with pytest.raises(ExternalDeliveryContainedError):
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
    async def test_retry_publish_is_contained_without_post_attempts(self, client, mock_http):
        """Publish containment happens before HTTP retry paths can POST."""
        with patch.object(client, "client", mock_http):
            original_publish = client.publish
            with patch.object(original_publish.retry, "wait", return_value=0):
                request = PublishRequest(content="Retry me", platforms=["linkedin"])
                with pytest.raises(ExternalDeliveryContainedError):
                    await client.publish(request)

        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_publish_exhaustion_is_contained_without_post(self, client, mock_http):
        """Publish containment raises directly instead of exhausting HTTP retries."""
        with (
            patch.object(client, "client", mock_http),
            patch.object(client.publish.retry, "wait", return_value=0),
        ):
            request = PublishRequest(content="Will fail", platforms=["linkedin"])
            with pytest.raises(ExternalDeliveryContainedError):
                await client.publish(request)

        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_schedule_is_contained_without_post_attempts(self, client, mock_http):
        """schedule_post containment happens before HTTP retry paths can POST."""
        with (
            patch.object(client, "client", mock_http),
            patch.object(client.schedule_post.retry, "wait", return_value=0),
        ):
            request = ScheduleRequest(content="Retry schedule", platform="linkedin")
            with pytest.raises(ExternalDeliveryContainedError):
                await client.schedule_post(request)

        mock_http.post.assert_not_called()


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
