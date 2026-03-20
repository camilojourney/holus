"""Tests for the social-media-automatization API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from holus.integrations.social_media import (
    PLATFORM_CHAR_LIMITS,
    PublishRequest,
    PublishResult,
    PublishTarget,
    ScheduleRequest,
    ScheduleResult,
    SocialMediaClient,
)


@pytest.fixture
def client():
    """Create a test client."""
    return SocialMediaClient(base_url="http://localhost:8000", api_key="test-key")


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    return mock


class TestContentValidation:
    """Test content validation logic."""

    def test_validate_within_limits(self, client):
        """Content within limits passes."""
        violations = client.validate_content("Hello world!", ["linkedin", "twitter"])
        assert violations == []

    def test_validate_exceeds_twitter(self, client):
        """Content exceeding Twitter 280 limit is caught."""
        long_text = "x" * 300
        violations = client.validate_content(long_text, ["twitter"])
        assert len(violations) == 1
        assert "twitter" in violations[0].lower()
        assert "280" in violations[0]

    def test_validate_multiple_violations(self, client):
        """Multiple platforms can violate limits."""
        long_text = "x" * 3500
        violations = client.validate_content(long_text, ["twitter", "linkedin", "threads"])
        assert len(violations) == 3

    def test_validate_case_insensitive(self, client):
        """Platform names are case-insensitive."""
        violations = client.validate_content("x" * 300, ["Twitter", "LINKEDIN"])
        assert len(violations) == 1  # Only twitter exceeds


class TestPublish:
    """Test publishing."""

    @pytest.mark.asyncio
    async def test_publish_validates_content(self, client):
        """Publishing validates content before API call."""
        request = PublishRequest(
            content="x" * 300,
            platforms=["twitter"],
        )
        with pytest.raises(ValueError, match="Content validation failed"):
            await client.publish(request)

    @pytest.mark.asyncio
    async def test_publish_successful(self, client, mock_httpx_client):
        """Successful publish returns PublishResult."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "publish_id": "pub_42",
            "targets": [
                {
                    "platform": "linkedin",
                    "account": "experience",
                    "language": "en",
                    "status": "queued",
                    "error": None,
                    "job_id": 42,
                }
            ],
            "warnings": [],
            "en_content": "Enhanced content here",
            "es_content": None,
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = PublishRequest(
                content="Hello world!",
                platforms=["linkedin"],
            )
            result = await client.publish(request)

            assert isinstance(result, PublishResult)
            assert result.publish_id == "pub_42"
            assert len(result.targets) == 1
            assert result.targets[0].platform == "linkedin"
            assert result.succeeded is True

    @pytest.mark.asyncio
    async def test_publish_with_failed_targets(self, client, mock_httpx_client):
        """Failed targets are reported correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "publish_id": "pub_43",
            "targets": [
                {
                    "platform": "linkedin",
                    "account": "experience",
                    "language": "en",
                    "status": "queued",
                },
                {
                    "platform": "twitter",
                    "account": "main",
                    "language": "en",
                    "status": "failed",
                    "error": "Rate limit exceeded",
                },
            ],
            "warnings": [],
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = PublishRequest(
                content="Test post",
                platforms=["linkedin", "twitter"],
            )
            result = await client.publish(request)

            assert result.succeeded is False
            assert len(result.failed_targets) == 1
            assert result.failed_targets[0].platform == "twitter"
            assert result.failed_targets[0].error == "Rate limit exceeded"

    @pytest.mark.asyncio
    async def test_publish_sends_correct_payload(self, client, mock_httpx_client):
        """Publish sends the right payload to the API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "publish_id": "pub_44",
            "targets": [],
            "warnings": [],
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = PublishRequest(
                content="Test content",
                platforms=["linkedin"],
                style="raw",
                media_url="https://example.com/image.jpg",
                media_type="image",
            )
            await client.publish(request)

            mock_httpx_client.post.assert_called_once()
            call_args = mock_httpx_client.post.call_args
            assert call_args[0][0] == "/api/v1/publish"
            payload = call_args[1]["json"]
            assert payload["content"] == "Test content"
            assert payload["platforms"] == ["linkedin"]
            assert payload["media_url"] == "https://example.com/image.jpg"
            assert payload["media_type"] == "image"

    @pytest.mark.asyncio
    async def test_publish_bilingual(self, client, mock_httpx_client):
        """Bilingual publish sets correct payload fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "publish_id": "pub_45_46",
            "targets": [],
            "warnings": [],
            "en_content": "English",
            "es_content": "Spanish",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = PublishRequest(
                content="Test content",
                platforms=["instagram", "facebook"],
                bilingual=True,
                source_language="en",
            )
            result = await client.publish(request)

            # bilingual/source_language not sent to API (not in API schema yet)
            # but the response may contain bilingual content
            assert result.en_content == "English"
            assert result.es_content == "Spanish"


class TestGetStatus:
    """Test status checking."""

    @pytest.mark.asyncio
    async def test_get_status(self, client, mock_httpx_client):
        """Status check returns updated PublishResult."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "publish_id": "pub_42",
            "targets": [
                {
                    "platform": "linkedin",
                    "account": "experience",
                    "language": "en",
                    "status": "published",
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_status("pub_42")

            assert result.publish_id == "pub_42"
            assert result.targets[0].status == "published"
            mock_httpx_client.get.assert_called_once_with("/api/publish/pub_42")


class TestHealth:
    """Test health check."""

    @pytest.mark.asyncio
    async def test_health_check(self, client, mock_httpx_client):
        """Health endpoint returns platform status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "platforms": {
                "linkedin": {"connected": True, "token_valid": True},
            },
            "checked_at": "2026-03-02T10:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.health()

            assert "platforms" in result
            assert result["platforms"]["linkedin"]["connected"] is True


class TestClientLifecycle:
    """Test client lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client works as async context manager."""
        async with SocialMediaClient(api_key="test-key") as c:
            assert c.client is not None

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Client can be closed manually."""
        await client.close()


class TestModels:
    """Test Pydantic models."""

    def test_publish_result_succeeded(self):
        """succeeded property works correctly."""
        result = PublishResult(
            publish_id="pub_1",
            targets=[
                PublishTarget(platform="linkedin", status="queued"),
                PublishTarget(platform="twitter", status="queued"),
            ],
        )
        assert result.succeeded is True

    def test_publish_result_failed(self):
        """failed_targets property returns failed targets."""
        result = PublishResult(
            publish_id="pub_1",
            targets=[
                PublishTarget(platform="linkedin", status="published"),
                PublishTarget(platform="twitter", status="failed", error="Rate limit"),
            ],
        )
        assert result.succeeded is False
        assert len(result.failed_targets) == 1
        assert result.failed_targets[0].platform == "twitter"

    def test_platform_limits_defined(self):
        """All expected platforms have character limits."""
        for platform in ("twitter", "linkedin", "instagram", "facebook", "threads"):
            assert platform in PLATFORM_CHAR_LIMITS
            assert PLATFORM_CHAR_LIMITS[platform] > 0

    def test_publish_request_defaults(self):
        """PublishRequest has sensible defaults."""
        req = PublishRequest(content="Hello", platforms=["linkedin"])
        assert req.style == "raw"
        assert req.bilingual is False
        assert req.media_url is None


class TestGetAnalytics:
    """Test analytics fetching."""

    @pytest.mark.asyncio
    async def test_get_analytics_default(self, client, mock_httpx_client):
        """Analytics returns summary data with default params."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "total_posts": 15,
            "success_rate": 0.93,
            "platforms": {
                "linkedin": {"posts": 8, "success_rate": 1.0},
                "twitter": {"posts": 7, "success_rate": 0.86},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_analytics()

            assert result["total_posts"] == 15
            assert "platforms" in result
            mock_httpx_client.get.assert_called_once_with("/api/v1/analytics", params={"days": 7})

    @pytest.mark.asyncio
    async def test_get_analytics_with_platform_filter(self, client, mock_httpx_client):
        """Analytics can filter by platform."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "total_posts": 8,
            "success_rate": 1.0,
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_analytics(days=14, platform="linkedin")

            assert result["total_posts"] == 8
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/analytics", params={"days": 14, "platform": "linkedin"}
            )

    @pytest.mark.asyncio
    async def test_get_analytics_empty(self, client, mock_httpx_client):
        """Analytics returns empty when no posts exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"total_posts": 0, "platforms": {}}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_analytics()

            assert result["total_posts"] == 0


class TestGetTopPosts:
    """Test top posts fetching."""

    @pytest.mark.asyncio
    async def test_get_top_posts_default(self, client, mock_httpx_client):
        """Top posts returns list with default params."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "posts": [
                {"id": 1, "content": "Great post", "platform": "linkedin"},
                {"id": 2, "content": "Another post", "platform": "twitter"},
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_top_posts()

            assert len(result["posts"]) == 2
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/analytics/top-posts",
                params={"limit": 10, "days": 30, "metric": "recent"},
            )

    @pytest.mark.asyncio
    async def test_get_top_posts_custom_params(self, client, mock_httpx_client):
        """Top posts respects custom params."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"posts": []}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            await client.get_top_posts(limit=5, days=7, metric="success_rate")

            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/analytics/top-posts",
                params={"limit": 5, "days": 7, "metric": "success_rate"},
            )


class TestSchedulePost:
    """Test schedule_post method."""

    @pytest.mark.asyncio
    async def test_schedule_post_successful(self, client, mock_httpx_client):
        """Successful schedule returns ScheduleResult."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "schedule_id": "sched_1",
            "status": "pending_approval",
            "platform": "linkedin",
            "approval_required": True,
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = ScheduleRequest(
                content="Test scheduled content",
                platform="linkedin",
            )
            result = await client.schedule_post(request)

            assert isinstance(result, ScheduleResult)
            assert result.schedule_id == "sched_1"
            assert result.status == "pending_approval"
            assert result.approval_required is True

    @pytest.mark.asyncio
    async def test_schedule_post_validates_content(self, client):
        """Schedule validates content before sending."""
        request = ScheduleRequest(
            content="x" * 300,
            platform="twitter",
        )
        with pytest.raises(ValueError, match="Content validation failed"):
            await client.schedule_post(request)

    @pytest.mark.asyncio
    async def test_schedule_post_sends_correct_payload(self, client, mock_httpx_client):
        """Schedule sends the right payload to the API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "schedule_id": "sched_2",
            "status": "scheduled",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = ScheduleRequest(
                content="Scheduled post",
                platform="linkedin",
                approval_required=False,
                scheduled_at="2026-03-25T10:00:00Z",
            )
            await client.schedule_post(request)

            mock_httpx_client.post.assert_called_once()
            call_args = mock_httpx_client.post.call_args
            assert call_args[0][0] == "/api/v1/schedule"
            payload = call_args[1]["json"]
            assert payload["content"] == "Scheduled post"
            assert payload["platform"] == "linkedin"
            assert payload["approval_required"] is False
            assert payload["scheduled_at"] == "2026-03-25T10:00:00Z"

    @pytest.mark.asyncio
    async def test_schedule_post_with_media(self, client, mock_httpx_client):
        """Schedule includes media fields when provided."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "schedule_id": "sched_3",
            "status": "pending_approval",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = ScheduleRequest(
                content="Post with image",
                platform="instagram",
                media_url="https://example.com/photo.jpg",
                media_type="image",
            )
            await client.schedule_post(request)

            payload = mock_httpx_client.post.call_args[1]["json"]
            assert payload["media_url"] == "https://example.com/photo.jpg"
            assert payload["media_type"] == "image"

    @pytest.mark.asyncio
    async def test_schedule_post_unwraps_data_envelope(self, client, mock_httpx_client):
        """Schedule unwraps {"status": "ok", "data": {...}} envelope."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "schedule_id": "sched_4",
                "status": "pending_approval",
                "platform": "linkedin",
                "approval_required": True,
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = ScheduleRequest(content="Envelope test", platform="linkedin")
            result = await client.schedule_post(request)

            assert result.schedule_id == "sched_4"


class TestGetPostAnalytics:
    """Test get_post_analytics method."""

    @pytest.mark.asyncio
    async def test_get_post_analytics_successful(self, client, mock_httpx_client):
        """Post analytics returns engagement data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "views": 1200,
            "likes": 45,
            "comments": 12,
            "shares": 8,
            "saves": 3,
            "engagement_rate": 0.057,
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            result = await client.get_post_analytics("post_42")

            assert result["views"] == 1200
            assert result["engagement_rate"] == 0.057
            mock_httpx_client.get.assert_called_once_with(
                "/api/v1/analytics/posts/post_42/latest"
            )

    @pytest.mark.asyncio
    async def test_get_post_analytics_not_found(self, client, mock_httpx_client):
        """Post analytics raises on 404."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=httpx.Request("GET", "http://localhost:8000/api/v1/analytics/posts/missing/latest"),
            response=httpx.Response(404),
        )
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.HTTPStatusError):
            await client.get_post_analytics("missing")


class TestErrorHandling:
    """Test HTTP error handling across methods."""

    @pytest.mark.asyncio
    async def test_publish_raises_on_5xx(self, client, mock_httpx_client):
        """Publish raises HTTPStatusError on 5xx."""
        mock_httpx_client.post.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=httpx.Request("POST", "http://localhost:8000/api/v1/publish"),
            response=httpx.Response(500),
        )

        with patch.object(client, "client", mock_httpx_client):
            request = PublishRequest(content="Test", platforms=["linkedin"])
            with pytest.raises(httpx.HTTPStatusError):
                # Call underlying function directly to skip tenacity retry waits
                await SocialMediaClient.publish.__wrapped__(client, request)

    @pytest.mark.asyncio
    async def test_get_analytics_raises_on_timeout(self, client, mock_httpx_client):
        """get_analytics raises on connection timeout."""
        mock_httpx_client.get.side_effect = httpx.TimeoutException("Connection timed out")

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.TimeoutException):
            await client.get_analytics()

    @pytest.mark.asyncio
    async def test_get_top_posts_raises_on_4xx(self, client, mock_httpx_client):
        """get_top_posts raises on 4xx client error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=httpx.Request("GET", "http://localhost:8000/api/v1/analytics/top-posts"),
            response=httpx.Response(400),
        )
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.HTTPStatusError):
            await client.get_top_posts()

    @pytest.mark.asyncio
    async def test_health_raises_on_connection_error(self, client, mock_httpx_client):
        """Health check raises on connection error."""
        mock_httpx_client.get.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.ConnectError):
            await client.health()

    @pytest.mark.asyncio
    async def test_get_status_raises_on_404(self, client, mock_httpx_client):
        """get_status raises on 404 Not Found."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=httpx.Request("GET", "http://localhost:8000/api/publish/missing_id"),
            response=httpx.Response(404),
        )
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client), pytest.raises(httpx.HTTPStatusError):
            await client.get_status("missing_id")

    @pytest.mark.asyncio
    async def test_schedule_post_raises_on_5xx(self, client, mock_httpx_client):
        """schedule_post raises on server error."""
        mock_httpx_client.post.side_effect = httpx.HTTPStatusError(
            "Service Unavailable",
            request=httpx.Request("POST", "http://localhost:8000/api/v1/schedule"),
            response=httpx.Response(503),
        )

        with patch.object(client, "client", mock_httpx_client):
            request = ScheduleRequest(content="Test", platform="linkedin")
            with pytest.raises(httpx.HTTPStatusError):
                # Call underlying function directly to skip tenacity retry waits
                await SocialMediaClient.schedule_post.__wrapped__(client, request)

    @pytest.mark.asyncio
    async def test_publish_unwraps_data_envelope(self, client, mock_httpx_client):
        """Publish correctly unwraps {"status": "ok", "data": {...}} envelope."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "publish_id": "pub_99",
                "targets": [
                    {
                        "platform": "linkedin",
                        "status": "queued",
                    }
                ],
                "warnings": [],
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = PublishRequest(content="Envelope test", platforms=["linkedin"])
            result = await client.publish(request)

            assert result.publish_id == "pub_99"
            assert len(result.targets) == 1


class TestScheduleModels:
    """Test ScheduleRequest and ScheduleResult models."""

    def test_schedule_request_defaults(self):
        """ScheduleRequest has sensible defaults."""
        req = ScheduleRequest(content="Hello", platform="linkedin")
        assert req.approval_required is True
        assert req.scheduled_at is None
        assert req.media_url is None

    def test_schedule_result_defaults(self):
        """ScheduleResult has sensible defaults."""
        result = ScheduleResult(schedule_id="sched_1")
        assert result.status == "pending_approval"
        assert result.approval_required is True
        assert result.platform == ""
