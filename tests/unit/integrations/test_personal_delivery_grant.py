"""Personal delivery grant unlocks Holus Social API write paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from holus.integrations.holus_social_api import (
    ExternalDeliveryContainedError,
    HolusSocialAPIClient,
    PublishRequest,
    personal_delivery_granted,
)
from holus.integrations.holus_social_api.containment import PERSONAL_DELIVERY_GRANT_ENV


def test_personal_delivery_granted_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PERSONAL_DELIVERY_GRANT_ENV, raising=False)
    assert personal_delivery_granted() is False
    monkeypatch.setenv(PERSONAL_DELIVERY_GRANT_ENV, "1")
    assert personal_delivery_granted() is True


@pytest.mark.asyncio
async def test_publish_posts_when_grant_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PERSONAL_DELIVERY_GRANT_ENV, "1")
    mock_http = AsyncMock()
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {
        "publish_id": "pub-1",
        "targets": [{"platform": "linkedin", "status": "queued"}],
    }
    mock_http.post = AsyncMock(return_value=mock_response)

    with patch(
        "holus.integrations.holus_social_api.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        client = HolusSocialAPIClient(base_url="http://social.test", api_key="k")
        result = await client.publish(
            PublishRequest(content="Hello LinkedIn", platforms=["linkedin"])
        )

    assert result.publish_id == "pub-1"
    mock_http.post.assert_awaited()


@pytest.mark.asyncio
async def test_publish_still_contained_without_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PERSONAL_DELIVERY_GRANT_ENV, raising=False)
    client = HolusSocialAPIClient(base_url="http://social.test", api_key="k")
    with pytest.raises(ExternalDeliveryContainedError):
        await client.publish(PublishRequest(content="Hello", platforms=["linkedin"]))
