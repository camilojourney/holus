"""Telegram approval sender — SPEC-035.

Sends post + visual variants to Juan via Telegram for approval.
Inline buttons: ✅ Post A / ✅ Post B / ✏️ Edit / ❌ Reject

Callback data: {"post_id": "...", "action": "approve", "variant": "A"}
Never contains post content — only post_id + action + variant.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}"


class TelegramSender:
    """Sends LinkedIn post approval requests to Telegram."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        self._token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "8419106275")
        self._base = f"https://api.telegram.org/bot{self._token}"

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        resp = httpx.post(f"{self._base}/{method}", json=payload, timeout=30.0)
        resp.raise_for_status()
        raw: Any = resp.json()
        return dict(raw)

    def send_approval_request(
        self,
        post_id: str,
        full_post: str,
        cards: list[dict[str, Any]],  # [{arm_id, path, variant}]
    ) -> None:
        """Send post text + card images with approval buttons.

        Flow:
        1. Send post text as preview
        2. Send each card image with variant label
        3. Send approval buttons as separate message
        """
        if not self._token:
            logger.warning("TELEGRAM_BOT_TOKEN not set — skipping Telegram send")
            return

        # 1. Send text preview
        preview = f"📝 *New LinkedIn Post*\n\n{self._escape(full_post[:800])}"
        if len(full_post) > 800:
            preview += f"\n\n_...{len(full_post) - 800} more chars_"

        self._post("sendMessage", {
            "chat_id": self._chat_id,
            "text": preview,
            "parse_mode": "MarkdownV2",
        })

        # 2. Send card images
        for card in cards:
            path = Path(card["path"])
            if not path.exists():
                logger.warning("card image not found: %s", path)
                continue

            with open(path, "rb") as f:
                httpx.post(
                    f"{self._base}/sendPhoto",
                    data={
                        "chat_id": self._chat_id,
                        "caption": f"Variant {card['variant']} — {card['arm_id'].replace('_', ' ')}",
                    },
                    files={"photo": (path.name, f, "image/png")},
                    timeout=30.0,
                ).raise_for_status()

        # 3. Send approval buttons
        buttons = []
        for card in cards:
            buttons.append({
                "text": f"✅ Post {card['variant']}",
                "callback_data": json.dumps({
                    "post_id": post_id,
                    "action": "approve",
                    "variant": card["variant"],
                }),
            })

        buttons.append({
            "text": "✏️ Edit",
            "callback_data": json.dumps({"post_id": post_id, "action": "edit"}),
        })
        buttons.append({
            "text": "❌ Reject",
            "callback_data": json.dumps({"post_id": post_id, "action": "reject"}),
        })

        self._post("sendMessage", {
            "chat_id": self._chat_id,
            "text": f"Choose an option for post `{post_id}`:",
            "parse_mode": "MarkdownV2",
            "reply_markup": {
                "inline_keyboard": [
                    buttons[:2],   # approve buttons on first row
                    buttons[2:],   # edit + reject on second row
                ],
            },
        })

        logger.info("telegram_sender: sent approval request for post_id=%s", post_id)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape special chars for MarkdownV2."""
        for ch in r"_*[]()~`>#+-=|{}.!":
            text = text.replace(ch, f"\\{ch}")
        return text
