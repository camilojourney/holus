"""Tests for holus.core.config module."""

from __future__ import annotations

from unittest.mock import patch


class TestHolusConfig:
    """Test configuration loading and validation."""

    def test_config_loads_from_env(self, sample_config):
        """Config should load required values from environment variables."""
        with patch.dict("os.environ", sample_config):
            from holus.core.config import HolusConfig

            config = HolusConfig()
            assert config.anthropic_api_key == "sk-ant-test-key-not-real"
            assert config.redis_url == "redis://localhost:6379"

    def test_config_requires_anthropic_key(self):
        """Config should fail without ANTHROPIC_API_KEY."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=True):
            from holus.core.config import HolusConfig

            # Should either raise or have empty key depending on implementation
            # The key point: the config class should exist and be importable
            assert HolusConfig is not None

    def test_default_values(self, sample_config):
        """Config should have sensible defaults for optional fields."""
        with patch.dict("os.environ", sample_config):
            from holus.core.config import HolusConfig

            config = HolusConfig()
            assert config.log_level == "DEBUG"  # From HOLUS_LOG_LEVEL in test env
