"""Contract tests for HolusSocialAPIClient.

Mocks httpx only — no live Social API calls. Locks the HTTP boundary contract:
endpoints, payload shape, auth header, pre-flight validation, and schedule
approval gate defaults.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holus.integrations.holus_social_api.client import (
    HolusSocialAPIClient,
    PublishRequest,
    ScheduleRequest,
)
from holus.integrations.holus_social_api.containment import ExternalDeliveryContainedError


@pytest.fixture
def mock_http() -> AsyncMock:
    """Mock httpx.AsyncClient with async get/post."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    return mock


def _ok_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


class TestPublishHTTPContract:
    """Publish endpoint is contained before outbound HTTP."""

    @pytest.mark.asyncio
    async def test_publish_is_contained_before_v1_endpoint(self, mock_http: AsyncMock) -> None:
        """publish fails closed before POST /api/v1/publish."""
        mock_http.post.return_value = _ok_response(
            {
                "publish_id": "contract-pub-1",
                "targets": [{"platform": "linkedin", "status": "queued"}],
            }
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            with pytest.raises(ExternalDeliveryContainedError, match="contain"):
                await client.publish(
                    PublishRequest(content="Contract post", platforms=["linkedin"], style="raw")
                )

        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_sends_api_key_header(self, mock_http: AsyncMock) -> None:
        """Client is constructed with X-API-Key header for Holus Social API auth."""
        captured: dict[str, object] = {}

        def _capture_client(**kwargs: object) -> AsyncMock:
            captured.update(kwargs)
            return mock_http

        with patch("httpx.AsyncClient", side_effect=_capture_client):
            HolusSocialAPIClient(base_url="http://contract.test", api_key="secret-contract-key")

        headers = captured["headers"]
        assert isinstance(headers, dict)
        assert headers["X-API-Key"] == "secret-contract-key"

    @pytest.mark.asyncio
    async def test_publish_validation_blocks_http(self, mock_http: AsyncMock) -> None:
        """Containment runs before validation and any HTTP request."""
        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            with pytest.raises(ExternalDeliveryContainedError, match="contain"):
                await client.publish(PublishRequest(content="x" * 300, platforms=["twitter"]))

        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_normalizes_twitter_x_platform(self, mock_http: AsyncMock) -> None:
        """Containment prevents payload construction for normalized platforms."""
        mock_http.post.return_value = _ok_response({"publish_id": "contract-pub-2", "targets": []})

        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            with pytest.raises(ExternalDeliveryContainedError, match="contain"):
                await client.publish(
                    PublishRequest(content="Short tweet", platforms=["twitter_x"]),
                )

        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_extra_httpx_calls_during_publish(self, mock_http: AsyncMock) -> None:
        """Contract: one AsyncClient at init; publish performs no POST."""
        mock_http.post.return_value = _ok_response(
            {
                "publish_id": "contract-pub-3",
                "targets": [{"platform": "linkedin", "status": "queued"}],
            }
        )

        with patch("httpx.AsyncClient", return_value=mock_http) as live_ctor:
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            with pytest.raises(ExternalDeliveryContainedError, match="contain"):
                await client.publish(PublishRequest(content="ok", platforms=["linkedin"]))

        live_ctor.assert_called_once()
        mock_http.post.assert_not_called()


class TestScheduleApprovalContract:
    """Schedule endpoint is contained before outbound HTTP."""

    @pytest.mark.asyncio
    async def test_schedule_defaults_approval_required(self, mock_http: AsyncMock) -> None:
        """Schedule preserves model defaults but does not POST while contained."""
        mock_http.post.return_value = _ok_response(
            {
                "schedule_id": "contract-sched-1",
                "status": "pending_approval",
                "approval_required": True,
            }
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            request = ScheduleRequest(content="Needs review", platform="linkedin")
            assert request.approval_required is True
            with pytest.raises(ExternalDeliveryContainedError, match="contain"):
                await client.schedule_post(request)

        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_validation_blocks_http(self, mock_http: AsyncMock) -> None:
        """Containment runs before schedule validation and any HTTP request."""
        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            with pytest.raises(ExternalDeliveryContainedError, match="contain"):
                await client.schedule_post(
                    ScheduleRequest(content="x" * 300, platform="twitter"),
                )

        mock_http.post.assert_not_called()
