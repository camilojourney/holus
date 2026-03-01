"""Tests for the Late API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holus.integrations.late_api import (
    PLATFORM_LIMITS,
    AnalyticsData,
    LateAPIClient,
    PostRequest,
    PostResult,
)


@pytest.fixture
def client():
    """Create a test client."""
    return LateAPIClient(api_key="test_key_12345")


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    return mock


class TestContentValidation:
    """Test content validation logic."""

    def test_validate_content_within_limits(self, client):
        """Content within limits passes validation."""
        violations = client.validate_content("Hello world!", ["twitter", "linkedin"])
        assert violations == []

    def test_validate_content_exceeds_twitter_limit(self, client):
        """Content exceeding Twitter's 280 char limit is caught."""
        long_text = "x" * 300
        violations = client.validate_content(long_text, ["twitter"])
        assert len(violations) == 1
        assert "twitter" in violations[0].lower()
        assert "280" in violations[0]

    def test_validate_content_multiple_platform_violations(self, client):
        """Multiple platforms can have violations."""
        long_text = "x" * 5500
        violations = client.validate_content(long_text, ["twitter", "linkedin", "youtube"])
        # Twitter (280), LinkedIn (3000) should fail; YouTube (5000) passes
        assert len(violations) == 3
        assert any("twitter" in v.lower() for v in violations)
        assert any("linkedin" in v.lower() for v in violations)
        assert any("youtube" in v.lower() for v in violations)

    def test_validate_content_case_insensitive(self, client):
        """Platform names are case-insensitive."""
        violations = client.validate_content("x" * 300, ["Twitter", "LINKEDIN"])
        assert len(violations) == 1
        assert "twitter" in violations[0].lower() or "Twitter" in violations[0]


class TestAccountCaching:
    """Test account ID caching."""

    @pytest.mark.asyncio
    async def test_get_accounts_caches_results(self, client, mock_httpx_client):
        """Account IDs are cached after first fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"platform": "twitter", "_id": "acc_twitter_123"},
            {"platform": "linkedin", "_id": "acc_linkedin_456"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            # First call
            accounts = await client.get_accounts()
            assert accounts == {
                "twitter": "acc_twitter_123",
                "linkedin": "acc_linkedin_456",
            }
            assert mock_httpx_client.get.call_count == 1

            # Second call (should use cache)
            accounts2 = await client.get_accounts()
            assert accounts2 == accounts
            assert mock_httpx_client.get.call_count == 1  # Still 1!


class TestPublish:
    """Test post publishing."""

    @pytest.mark.asyncio
    async def test_publish_validates_content_length(self, client):
        """Publishing validates content length before API call."""
        request = PostRequest(
            text="x" * 300,  # Exceeds Twitter's 280 limit
            platforms=["twitter"],
        )

        with pytest.raises(ValueError, match="Content validation failed"):
            await client.publish(request)

    @pytest.mark.asyncio
    async def test_publish_checks_connected_accounts(self, client, mock_httpx_client):
        """Publishing checks if accounts are connected."""
        # Mock get_accounts to return only twitter
        client._account_cache = {"twitter": "acc_twitter_123"}

        request = PostRequest(
            text="Valid post",
            platforms=["twitter", "linkedin"],  # linkedin not connected
        )

        with pytest.raises(ValueError, match="No connected accounts"):
            await client.publish(request)

    @pytest.mark.asyncio
    async def test_publish_successful(self, client, mock_httpx_client):
        """Successful publish returns PostResult."""
        client._account_cache = {
            "twitter": "acc_twitter_123",
            "linkedin": "acc_linkedin_456",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "_id": "post_abc123",
            "platformResults": {
                "twitter": {"status": "success", "url": "https://twitter.com/..."},
                "linkedin": {"status": "success", "url": "https://linkedin.com/..."},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = PostRequest(
                text="Hello world!",
                platforms=["twitter", "linkedin"],
            )
            result = await client.publish(request)

            assert isinstance(result, PostResult)
            assert result.post_id == "post_abc123"
            assert result.failed_platforms == []
            assert result.scheduled is False

    @pytest.mark.asyncio
    async def test_publish_partial_failure(self, client, mock_httpx_client):
        """Partial failures are reported correctly."""
        client._account_cache = {
            "twitter": "acc_twitter_123",
            "linkedin": "acc_linkedin_456",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "_id": "post_abc123",
            "platformResults": {
                "twitter": {"status": "success", "url": "https://twitter.com/..."},
                "linkedin": {"status": "failed", "error": "Rate limit exceeded"},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = PostRequest(
                text="Hello world!",
                platforms=["twitter", "linkedin"],
            )
            result = await client.publish(request)

            assert result.failed_platforms == ["linkedin"]
            assert "linkedin" in result.error_details
            assert "Rate limit" in result.error_details["linkedin"]

    @pytest.mark.asyncio
    async def test_publish_with_scheduling(self, client, mock_httpx_client):
        """Scheduled posts set the scheduled flag."""
        client._account_cache = {"twitter": "acc_twitter_123"}

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "_id": "post_abc123",
            "platformResults": {
                "twitter": {"status": "scheduled"},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            request = PostRequest(
                text="Hello world!",
                platforms=["twitter"],
                schedule_time="2024-12-01T10:00:00Z",
            )
            result = await client.publish(request)

            assert result.scheduled is True


class TestAnalytics:
    """Test analytics retrieval."""

    @pytest.mark.asyncio
    async def test_get_analytics_single_post(self, client, mock_httpx_client):
        """Get analytics for a single post."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "post_id": "post_123",
                "platform": "twitter",
                "impressions": 1500,
                "engagement_rate": 0.045,
                "clicks": 67,
                "shares": 12,
                "comments": 5,
                "follower_delta": 3,
                "collected_at": "2024-11-01T12:00:00Z",
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            analytics = await client.get_analytics("post_123")

            assert len(analytics) == 1
            assert isinstance(analytics[0], AnalyticsData)
            assert analytics[0].impressions == 1500
            assert analytics[0].platform == "twitter"

    @pytest.mark.asyncio
    async def test_get_all_analytics(self, client, mock_httpx_client):
        """Get analytics for all posts in a time period."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "post_id": "post_1",
                "platform": "twitter",
                "impressions": 1500,
                "engagement_rate": 0.045,
                "clicks": 67,
                "shares": 12,
                "comments": 5,
                "follower_delta": 3,
                "collected_at": "2024-11-01T12:00:00Z",
            },
            {
                "post_id": "post_2",
                "platform": "linkedin",
                "impressions": 2300,
                "engagement_rate": 0.067,
                "clicks": 154,
                "shares": 25,
                "comments": 12,
                "follower_delta": 8,
                "collected_at": "2024-11-02T12:00:00Z",
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        with patch.object(client, "client", mock_httpx_client):
            analytics = await client.get_all_analytics(days=7)

            assert len(analytics) == 2
            assert all(isinstance(a, AnalyticsData) for a in analytics)


class TestClientLifecycle:
    """Test client lifecycle management."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client works as async context manager."""
        async with LateAPIClient("test_key") as client:
            assert client.client is not None

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Client can be closed manually."""
        await client.close()
        # Should not raise


class TestPlatformLimits:
    """Test platform character limits are correct."""

    def test_all_platforms_have_limits(self):
        """All major platforms have defined limits."""
        expected_platforms = [
            "twitter",
            "linkedin",
            "instagram",
            "tiktok",
            "youtube",
            "bluesky",
            "threads",
            "facebook",
            "pinterest",
            "telegram",
            "reddit",
        ]

        for platform in expected_platforms:
            assert platform in PLATFORM_LIMITS
            assert PLATFORM_LIMITS[platform] > 0
