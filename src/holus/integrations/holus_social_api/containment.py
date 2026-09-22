"""External delivery containment for Holus Social API write paths."""

from __future__ import annotations

import os
from typing import NoReturn

EXTERNAL_DELIVERY_CONTAINED_CODE = "EXTERNAL_DELIVERY_CONTAINED"
EXTERNAL_DELIVERY_CONTAINED_STATUS = "contained"
EXTERNAL_DELIVERY_CONTAINED_MESSAGE = (
    f"{EXTERNAL_DELIVERY_CONTAINED_CODE}: External publishing and scheduling are contained "
    "pending a future authenticated approval-grant sender. Local review, outbox intent, "
    "and analytics read flows remain available."
)

# Personal-use escape hatch: captain-operated single-user delivery through the
# existing Holus Social API connectors. Default remains fail-closed.
PERSONAL_DELIVERY_GRANT_ENV = "HOLUS_PERSONAL_DELIVERY_GRANT"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


class ExternalDeliveryContainedError(RuntimeError):
    """Raised when production code attempts outbound publish/schedule delivery."""


def personal_delivery_granted() -> bool:
    """Return True when the personal approval-grant sender is explicitly enabled."""
    return os.getenv(PERSONAL_DELIVERY_GRANT_ENV, "").strip().lower() in _TRUTHY


def raise_external_delivery_contained() -> NoReturn:
    """Fail closed before any outbound publish or schedule I/O can be invoked."""
    raise ExternalDeliveryContainedError(EXTERNAL_DELIVERY_CONTAINED_MESSAGE)
