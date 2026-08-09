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
    """Publish endpoint contract — mocked HTTP only."""

    @pytest.mark.asyncio
    async def test_publish_posts_to_v1_endpoint(self, mock_http: AsyncMock) -> None:
        """POST /api/v1/publish with content and platforms payload."""
        mock_http.post.return_value = _ok_response(
            {
                "publish_id": "contract-pub-1",
                "targets": [{"platform": "linkedin", "status": "queued"}],
            }
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            result = await client.publish(
                PublishRequest(content="Contract post", platforms=["linkedin"], style="raw")
            )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/api/v1/publish"
        payload = call_args[1]["json"]
        assert payload["content"] == "Contract post"
        assert payload["platforms"] == ["linkedin"]
        assert result.publish_id == "contract-pub-1"

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
        """Char-limit validation runs before any HTTP request."""
        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            with pytest.raises(ValueError, match="Content validation failed"):
                await client.publish(PublishRequest(content="x" * 300, platforms=["twitter"]))

        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_normalizes_twitter_x_platform(self, mock_http: AsyncMock) -> None:
        """twitter_x platform label is normalized to twitter in the API payload."""
        mock_http.post.return_value = _ok_response({"publish_id": "contract-pub-2", "targets": []})

        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            await client.publish(
                PublishRequest(content="Short tweet", platforms=["twitter_x"]),
            )

        payload = mock_http.post.call_args[1]["json"]
        assert payload["platforms"] == ["twitter"]

    @pytest.mark.asyncio
    async def test_no_extra_httpx_calls_during_publish(self, mock_http: AsyncMock) -> None:
        """Contract: one AsyncClient at init; publish uses it without extra constructors."""
        mock_http.post.return_value = _ok_response(
            {"publish_id": "contract-pub-3", "targets": [{"platform": "linkedin", "status": "queued"}]}
        )

        with patch("httpx.AsyncClient", return_value=mock_http) as live_ctor:
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            await client.publish(PublishRequest(content="ok", platforms=["linkedin"]))

        live_ctor.assert_called_once()
        mock_http.post.assert_called_once()


class TestScheduleApprovalContract:
    """Schedule endpoint enforces approval gate by default."""

    @pytest.mark.asyncio
    async def test_schedule_defaults_approval_required(self, mock_http: AsyncMock) -> None:
        """Schedule posts with approval_required=True unless explicitly disabled."""
        mock_http.post.return_value = _ok_response(
            {
                "schedule_id": "contract-sched-1",
                "status": "pending_approval",
                "approval_required": True,
            }
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            result = await client.schedule_post(
                ScheduleRequest(content="Needs review", platform="linkedin"),
            )

        assert mock_http.post.call_args[0][0] == "/api/v1/schedule"
        payload = mock_http.post.call_args[1]["json"]
        assert payload["approval_required"] is True
        assert payload["platforms"] == ["linkedin"]
        assert result.approval_required is True
        assert result.status == "pending_approval"

    @pytest.mark.asyncio
    async def test_schedule_validation_blocks_http(self, mock_http: AsyncMock) -> None:
        """Schedule validates content before any HTTP request."""
        with patch("httpx.AsyncClient", return_value=mock_http):
            client = HolusSocialAPIClient(base_url="http://contract.test", api_key="contract-key")
            with pytest.raises(ValueError, match="Content validation failed"):
                await client.schedule_post(
                    ScheduleRequest(content="x" * 300, platform="twitter"),
                )

        mock_http.post.assert_not_called()
