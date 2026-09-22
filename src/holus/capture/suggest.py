"""Capture-to-route suggestion helpers for personal share loop."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from holus.integrations.holus_social_api.client import PLATFORM_CHAR_LIMITS

AttachmentKind = Literal["none", "image", "link", "pdf"]

CHANNEL_BY_PLATFORM: dict[str, str] = {
    "linkedin": "linkedin_text",
    "instagram": "instagram_image",
    "threads": "threads_text",
    "twitter": "twitter_x_thread",
    "facebook": "facebook_text",
}

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


@dataclass(frozen=True)
class RouteSuggestion:
    platform: str
    channel: str
    format_hint: str
    edit_notes: str
    confidence: float
    preview_text: str


def detect_attachment_kind(
    *,
    attachment_url: str | None = None,
    filename: str | None = None,
    content_type: str | None = None,
) -> AttachmentKind:
    """Classify the capture attachment as image, link, PDF, or none."""
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    url = (attachment_url or "").strip()

    if name.endswith(".pdf") or "pdf" in ctype:
        return "pdf"
    if ctype.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return "image"
    if url and _URL_RE.match(url):
        if url.lower().endswith(".pdf"):
            return "pdf"
        if any(url.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp")):
            return "image"
        return "link"
    return "none"


def _trim_for_platform(text: str, platform: str) -> str:
    limit = PLATFORM_CHAR_LIMITS.get(platform, 3000)
    cleaned = " ".join(text.split()).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def suggest_routes(
    *,
    text: str,
    attachment_kind: AttachmentKind = "none",
    attachment_url: str | None = None,
    connected_platforms: list[str] | None = None,
) -> list[RouteSuggestion]:
    """Propose destination platforms, formats, and light edits for a capture.

    Uses deterministic heuristics so the loop works without a live model key.
    When connected_platforms is provided, only those platforms are suggested.
    """
    body = (text or "").strip()
    if not body and attachment_kind == "none":
        return []

    connected = {
        p.lower().replace("twitter_x", "twitter")
        for p in (connected_platforms or list(CHANNEL_BY_PLATFORM))
    }
    length = len(body)
    has_url = bool(_URL_RE.search(body) or attachment_kind == "link")
    suggestions: list[RouteSuggestion] = []

    def add(
        platform: str,
        *,
        channel: str | None = None,
        format_hint: str,
        edit_notes: str,
        confidence: float,
        preview: str | None = None,
    ) -> None:
        if platform not in connected:
            return
        suggestions.append(
            RouteSuggestion(
                platform=platform,
                channel=channel or CHANNEL_BY_PLATFORM[platform],
                format_hint=format_hint,
                edit_notes=edit_notes,
                confidence=confidence,
                preview_text=_trim_for_platform(preview or body, platform),
            )
        )

    if attachment_kind == "pdf":
        add(
            "linkedin",
            channel="linkedin_carousel",
            format_hint="document carousel / PDF share",
            edit_notes="Lead with a one-line takeaway, then attach the PDF.",
            confidence=0.92,
            preview=f"{body}\n\n(PDF attachment)"
            if body
            else "Share this PDF with a short takeaway.",
        )
        add(
            "facebook",
            format_hint="community post with document",
            edit_notes="Keep the caption conversational; PDF as attachment.",
            confidence=0.7,
        )
    elif attachment_kind == "image":
        add(
            "instagram",
            channel="instagram_image",
            format_hint="image post",
            edit_notes="Write a short caption; first line is the hook.",
            confidence=0.9,
            preview=body or "New visual from the build.",
        )
        add(
            "linkedin",
            channel="linkedin_image",
            format_hint="image post",
            edit_notes="Add a builder lesson under the image; avoid hashtag spam.",
            confidence=0.85,
        )
        add(
            "facebook",
            format_hint="image post",
            edit_notes="Keep the caption plain and personal.",
            confidence=0.65,
        )
    elif attachment_kind == "link" or has_url:
        body_match = _URL_RE.search(body)
        link = attachment_url or (body_match.group(0) if body_match else "")
        add(
            "linkedin",
            format_hint="text post with link",
            edit_notes="Put the opinion first; drop the URL at the end.",
            confidence=0.88,
            preview=f"{body}\n\n{link}".strip() if link and link not in body else body,
        )
        add(
            "twitter",
            format_hint="short post or thread seed",
            edit_notes="Compress to one sharp claim; link at the end if needed.",
            confidence=0.8,
        )
        add(
            "threads",
            format_hint="conversation starter",
            edit_notes="Ask one follow-up question after the link takeaway.",
            confidence=0.72,
        )
    else:
        # Text-only capture
        if length <= 280:
            add(
                "twitter",
                format_hint="single post",
                edit_notes="Keep as one punchy line; no thread needed.",
                confidence=0.86,
            )
            add(
                "threads",
                format_hint="short conversation post",
                edit_notes="Optional: add a question to invite replies.",
                confidence=0.8,
            )
        # Always offer LinkedIn when connected - it is the default authority surface.
        add(
            "linkedin",
            format_hint="authority text post",
            edit_notes="Open with the lesson, then one concrete example.",
            confidence=0.9 if length > 200 else 0.78,
        )
        if length > 400:
            add(
                "linkedin",
                channel="linkedin_carousel",
                format_hint="carousel outline",
                edit_notes="Break into 5-7 slides: hook, problem, steps, close.",
                confidence=0.78,
            )
        add(
            "facebook",
            format_hint="community post",
            edit_notes="Soften the tone; sound like a note to friends.",
            confidence=0.6,
        )

    # Stable order: confidence desc, then platform name
    suggestions.sort(key=lambda s: (-s.confidence, s.platform, s.channel))
    # Deduplicate channel
    seen: set[str] = set()
    unique: list[RouteSuggestion] = []
    for item in suggestions:
        if item.channel in seen:
            continue
        seen.add(item.channel)
        unique.append(item)
    return unique
