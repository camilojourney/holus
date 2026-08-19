"""External delivery containment for Holus Social API write paths."""

from __future__ import annotations

from typing import NoReturn

EXTERNAL_DELIVERY_CONTAINED_CODE = "EXTERNAL_DELIVERY_CONTAINED"
EXTERNAL_DELIVERY_CONTAINED_STATUS = "contained"
EXTERNAL_DELIVERY_CONTAINED_MESSAGE = (
    f"{EXTERNAL_DELIVERY_CONTAINED_CODE}: External publishing and scheduling are contained "
    "pending a future authenticated approval-grant sender. Local review, outbox intent, "
    "and analytics read flows remain available."
)


class ExternalDeliveryContainedError(RuntimeError):
    """Raised when production code attempts outbound publish/schedule delivery."""


def raise_external_delivery_contained() -> NoReturn:
    """Fail closed before any outbound publish or schedule I/O can be invoked."""
    raise ExternalDeliveryContainedError(EXTERNAL_DELIVERY_CONTAINED_MESSAGE)
