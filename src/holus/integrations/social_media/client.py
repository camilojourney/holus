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
from holus.integrations.holus_social_api.containment import (
    EXTERNAL_DELIVERY_CONTAINED_CODE,
    EXTERNAL_DELIVERY_CONTAINED_MESSAGE,
    EXTERNAL_DELIVERY_CONTAINED_STATUS,
    ExternalDeliveryContainedError,
    raise_external_delivery_contained,
)

SocialMediaClient = HolusSocialAPIClient

__all__ = [
    "EXTERNAL_DELIVERY_CONTAINED_CODE",
    "EXTERNAL_DELIVERY_CONTAINED_MESSAGE",
    "EXTERNAL_DELIVERY_CONTAINED_STATUS",
    "HOLUS_SOCIAL_API_BASE_URL_ENV",
    "HOLUS_SOCIAL_API_KEY_ENV",
    "PLATFORM_CHAR_LIMITS",
    "VALID_PLATFORMS",
    "ExternalDeliveryContainedError",
    "HolusSocialAPIClient",
    "PublishRequest",
    "PublishResult",
    "PublishTarget",
    "ScheduleRequest",
    "ScheduleResult",
    "SocialMediaClient",
    "raise_external_delivery_contained",
]
