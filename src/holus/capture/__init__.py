"""Personal capture package: suggest routes for a shared thought/attachment."""

from holus.capture.suggest import (
    AttachmentKind,
    RouteSuggestion,
    detect_attachment_kind,
    suggest_routes,
)

__all__ = [
    "AttachmentKind",
    "RouteSuggestion",
    "detect_attachment_kind",
    "suggest_routes",
]
