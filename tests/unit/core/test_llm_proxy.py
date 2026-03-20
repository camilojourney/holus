"""Tests for holus.core.llm_proxy — shared LLM proxy configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from holus.core.llm_proxy import (
    get_proxy_api_base,
    get_proxy_api_key,
    get_proxy_headers,
    get_proxy_url,
)


class TestGetProxyUrl:
    """Tests for get_proxy_url()."""

    def test_default_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        assert get_proxy_url() == "http://localhost:8080/v1/chat/completions"

    def test_custom_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://my-proxy:9090")
        assert get_proxy_url() == "http://my-proxy:9090/v1/chat/completions"

    def test_trailing_slash_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://my-proxy:9090/")
        assert get_proxy_url() == "http://my-proxy:9090/v1/chat/completions"


class TestGetProxyHeaders:
    """Tests for get_proxy_headers()."""

    def test_default_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LLM_PROXY_AUTH_TOKEN", raising=False)
        headers = get_proxy_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer local"

    def test_custom_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROXY_AUTH_TOKEN", "Bearer sk-abc123")
        headers = get_proxy_headers()
        assert headers["Authorization"] == "Bearer sk-abc123"


class TestGetProxyApiBase:
    """Tests for get_proxy_api_base()."""

    def test_default_api_base(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        assert get_proxy_api_base() == "http://localhost:8080/v1"

    def test_custom_api_base(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://proxy.example.com")
        assert get_proxy_api_base() == "https://proxy.example.com/v1"

    def test_trailing_slash_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://proxy/")
        assert get_proxy_api_base() == "http://proxy/v1"


class TestGetProxyApiKey:
    """Tests for get_proxy_api_key()."""

    def test_default_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LLM_PROXY_AUTH_TOKEN", raising=False)
        assert get_proxy_api_key() == "local"

    def test_strips_bearer_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROXY_AUTH_TOKEN", "Bearer my-key")
        assert get_proxy_api_key() == "my-key"

    def test_no_bearer_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROXY_AUTH_TOKEN", "raw-token")
        assert get_proxy_api_key() == "raw-token"
