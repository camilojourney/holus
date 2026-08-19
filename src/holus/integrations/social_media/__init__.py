"""Compatibility imports for the renamed Holus Social API client."""

from .client import (
    EXTERNAL_DELIVERY_CONTAINED_CODE,
    EXTERNAL_DELIVERY_CONTAINED_MESSAGE,
    EXTERNAL_DELIVERY_CONTAINED_STATUS,
    HOLUS_SOCIAL_API_BASE_URL_ENV,
    HOLUS_SOCIAL_API_KEY_ENV,
    PLATFORM_CHAR_LIMITS,
    ExternalDeliveryContainedError,
    HolusSocialAPIClient,
    PublishRequest,
    PublishResult,
    PublishTarget,
    ScheduleRequest,
    ScheduleResult,
    SocialMediaClient,
    raise_external_delivery_contained,
)

__all__ = [
    "EXTERNAL_DELIVERY_CONTAINED_CODE",
    "EXTERNAL_DELIVERY_CONTAINED_MESSAGE",
    "EXTERNAL_DELIVERY_CONTAINED_STATUS",
    "HOLUS_SOCIAL_API_BASE_URL_ENV",
    "HOLUS_SOCIAL_API_KEY_ENV",
    "PLATFORM_CHAR_LIMITS",
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
