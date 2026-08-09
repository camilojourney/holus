"""Unit tests for holus.integrations.holus_social_api (direct import path)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from holus.integrations.holus_social_api import (
    HOLUS_SOCIAL_API_BASE_URL_ENV,
    HOLUS_SOCIAL_API_KEY_ENV,
    HolusSocialAPIClient,
    PublishRequest,
    PublishResult,
    ScheduleRequest,
    ScheduleResult,
)
from holus.integrations.holus_social_api.client import (
    normalize_platform,
    resolve_api_key,
    resolve_base_url,
)


class TestHolusSocialAPIHelpers:
    def test_normalize_platform_maps_twitter_x(self):
        assert normalize_platform("twitter_x") == "twitter"
        assert normalize_platform("linkedin") == "linkedin"

    def test_resolve_base_url_prefers_explicit_value(self):
        assert resolve_base_url("http://example.test/") == "http://example.test"

    def test_resolve_api_key_prefers_explicit_value(self):
        assert resolve_api_key("explicit-key") == "explicit-key"


class TestHolusSocialAPIClient:
    @pytest.mark.asyncio
    async def test_holus_social_publish_uses_shared_post_helper(self):
        client = HolusSocialAPIClient(base_url="http://test:8000", api_key="key")
        mock_http = AsyncMock()
        response = MagicMock()
        response.json.return_value = {
            "status": "ok",
            "data": {"publish_id": "pub_1", "targets": [], "warnings": []},
        }
        response.raise_for_status = MagicMock()
        mock_http.post.return_value = response

        with patch.object(client, "client", mock_http):
            result = await client.publish(
                PublishRequest(content="Hello", platforms=["linkedin"]),
            )

        assert isinstance(result, PublishResult)
        assert result.publish_id == "pub_1"
        await client.close()

    @pytest.mark.asyncio
    async def test_holus_social_schedule_uses_shared_post_helper(self):
        client = HolusSocialAPIClient(base_url="http://test:8000", api_key="key")
        mock_http = AsyncMock()
        response = MagicMock()
        response.json.return_value = {
            "schedule_id": "sched_1",
            "status": "pending_approval",
            "platform": "linkedin",
            "approval_required": True,
        }
        response.raise_for_status = MagicMock()
        mock_http.post.return_value = response

        with patch.object(client, "client", mock_http):
            result = await client.schedule_post(
                ScheduleRequest(content="Later", platform="linkedin"),
            )

        assert isinstance(result, ScheduleResult)
        assert result.schedule_id == "sched_1"
        await client.close()

    @pytest.mark.asyncio
    async def test_holus_social_env_resolution(self):
        with patch.dict(
            "os.environ",
            {
                HOLUS_SOCIAL_API_BASE_URL_ENV: "http://new.test/",
                HOLUS_SOCIAL_API_KEY_ENV: "new-key",
            },
            clear=True,
        ):
            client = HolusSocialAPIClient()
            try:
                assert client.base_url == "http://new.test"
                assert client.api_key == "new-key"
            finally:
                await client.close()

    @pytest.mark.asyncio
    async def test_holus_social_get_analytics_uses_shared_get_helper(self):
        client = HolusSocialAPIClient(base_url="http://test:8000", api_key="key")
        mock_http = AsyncMock()
        response = MagicMock()
        response.json.return_value = {"total_posts": 3}
        response.raise_for_status = MagicMock()
        mock_http.get.return_value = response

        with patch.object(client, "client", mock_http):
            result = await client.get_analytics(days=14, platform="twitter_x")

        mock_http.get.assert_called_once_with(
            "/api/v1/analytics",
            params={"days": 14, "platform": "twitter"},
        )
        assert result["total_posts"] == 3
        await client.close()

    @pytest.mark.asyncio
    async def test_holus_social_publish_retries_on_http_error(self):
        client = HolusSocialAPIClient(base_url="http://test:8000", api_key="key")
        mock_http = AsyncMock()
        error = httpx.HTTPStatusError(
            "HTTP 500",
            request=httpx.Request("POST", "http://test:8000/api/v1/publish"),
            response=httpx.Response(500),
        )
        success = MagicMock()
        success.json.return_value = {"publish_id": "pub_retry", "targets": [], "warnings": []}
        success.raise_for_status = MagicMock()
        mock_http.post.side_effect = [error, success]

        with (
            patch.object(client, "client", mock_http),
            patch.object(client.publish.retry, "wait", return_value=0),
        ):
            result = await client.publish(PublishRequest(content="Retry", platforms=["linkedin"]))

        assert result.publish_id == "pub_retry"
        assert mock_http.post.call_count == 2
        await client.close()
