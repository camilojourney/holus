"""Social media publishing client for social-media-automatization API."""

from .client import (
    PLATFORM_CHAR_LIMITS,
    PublishRequest,
    PublishResult,
    PublishTarget,
    ScheduleRequest,
    ScheduleResult,
    SocialMediaClient,
)

__all__ = [
    "PLATFORM_CHAR_LIMITS",
    "PublishRequest",
    "PublishResult",
    "PublishTarget",
    "ScheduleRequest",
    "ScheduleResult",
    "SocialMediaClient",
]
