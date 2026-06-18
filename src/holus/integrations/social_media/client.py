"""Compatibility shim for the renamed Holus Social API client."""

from __future__ import annotations

from holus.integrations.holus_social_api.client import (
    HOLUS_SOCIAL_API_BASE_URL_ENV,
    HOLUS_SOCIAL_API_KEY_ENV,
    PLATFORM_CHAR_LIMITS,
    VALID_PLATFORMS,
    HolusSocialAPIClient,
    PublishRequest,
    PublishResult,
    PublishTarget,
    ScheduleRequest,
    ScheduleResult,
)

SocialMediaClient = HolusSocialAPIClient

__all__ = [
    "HOLUS_SOCIAL_API_BASE_URL_ENV",
    "HOLUS_SOCIAL_API_KEY_ENV",
    "PLATFORM_CHAR_LIMITS",
    "VALID_PLATFORMS",
    "HolusSocialAPIClient",
    "PublishRequest",
    "PublishResult",
    "PublishTarget",
    "ScheduleRequest",
    "ScheduleResult",
    "SocialMediaClient",
]
