"""
Notifier — Sends alerts and updates to you via Telegram (primary) or SMS.
This is how your agents "talk" to you.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger


class TelegramNotifier:
    """Send notifications via Telegram bot."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._bot = None

    async def _get_bot(self):
        if self._bot is None:
            from telegram import Bot
            self._bot = Bot(token=self.bot_token)
        return self._bot

    async def send(self, message: str, parse_mode: str = "Markdown"):
        """Send a message via Telegram."""
        try:
            bot = await self._get_bot()
            # Telegram has a 4096 char limit
            if len(message) > 4000:
                chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for chunk in chunks:
                    await bot.send_message(
                        chat_id=self.chat_id,
                        text=chunk,
                        parse_mode=parse_mode,
                    )
            else:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=parse_mode,
                )
            logger.info(f"Telegram notification sent: {message[:80]}...")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    async def send_approval_request(
        self,
        agent_name: str,
        action: str,
        details: str,
    ) -> bool:
        """
        Send an approval request and wait for response.
        Returns True if approved, False if rejected.
        """
        msg = (
            f"🔔 *Approval Needed — {agent_name}*\n\n"
            f"**Action:** {action}\n\n"
            f"{details}\n\n"
            f"Reply with ✅ to approve or ❌ to reject."
        )
        await self.send(msg)
        # TODO: Implement response listener via Telegram webhook/polling
        # For MVP, we'll use a simple polling approach or manual check
        logger.info(f"Approval request sent for {agent_name}: {action}")
        return True  # Placeholder — auto-approve for now


class Notifier:
    """Unified notification interface."""

    def __init__(self, config: dict):
        self.config = config
        self._telegram: Optional[TelegramNotifier] = None

    @property
    def telegram(self) -> Optional[TelegramNotifier]:
        if self._telegram is None:
            tg_cfg = self.config.get("telegram", {})
            if tg_cfg.get("enabled") and tg_cfg.get("bot_token") and tg_cfg.get("chat_id"):
                self._telegram = TelegramNotifier(
                    bot_token=tg_cfg["bot_token"],
                    chat_id=tg_cfg["chat_id"],
                )
        return self._telegram

    async def notify(self, message: str, agent_name: str = "holus"):
        """Send notification through all enabled channels."""
        prefix = f"*[{agent_name}]*\n" if agent_name else ""
        full_message = f"{prefix}{message}"

        if self.telegram:
            await self.telegram.send(full_message)
        else:
            logger.warning(f"No notification channel configured. Message: {message[:100]}")

    async def request_approval(self, agent_name: str, action: str, details: str) -> bool:
        """Request human approval for a high-stakes action."""
        if self.telegram:
            return await self.telegram.send_approval_request(agent_name, action, details)
        logger.warning(f"No notification channel for approval. Auto-approving: {action}")
        return True
