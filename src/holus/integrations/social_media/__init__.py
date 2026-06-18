"""Compatibility imports for the renamed Holus Social API client."""

from .client import (
    HOLUS_SOCIAL_API_BASE_URL_ENV,
    HOLUS_SOCIAL_API_KEY_ENV,
    PLATFORM_CHAR_LIMITS,
    HolusSocialAPIClient,
    PublishRequest,
    PublishResult,
    PublishTarget,
    ScheduleRequest,
    ScheduleResult,
    SocialMediaClient,
)

__all__ = [
    "HOLUS_SOCIAL_API_BASE_URL_ENV",
    "HOLUS_SOCIAL_API_KEY_ENV",
    "PLATFORM_CHAR_LIMITS",
    "HolusSocialAPIClient",
    "PublishRequest",
    "PublishResult",
    "PublishTarget",
    "ScheduleRequest",
    "ScheduleResult",
    "SocialMediaClient",
]
