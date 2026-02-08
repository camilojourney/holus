"""
Inbox Manager Agent — Email triage and automated responses.
Directly inspired by AI Jason's inbox-manager-agent:
https://github.com/JayZeeDesign/inbox-manager-agent

Categories emails, drafts responses, escalates important ones.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from shared.base_agent import BaseAgent
from shared.llm import TaskComplexity


class InboxManagerAgent(BaseAgent):
    name = "inbox_manager"
    description = "Manages email inbox — categorizes, drafts replies, escalates"
    schedule = "every 30 minutes"

    def get_tools(self) -> list:
        categories = self.config.get("categories", {})

        @tool
        def fetch_unread_emails(max_count: int = 20) -> str:
            """Fetch unread emails from Gmail."""
            # TODO: Implement with Gmail API
            return f"[Placeholder] Would fetch up to {max_count} unread emails from Gmail"

        @tool
        def categorize_email(email_subject: str, email_body: str, sender: str) -> str:
            """Categorize an email into: opportunity, action_needed, fyi, or spam."""
            cats = "\n".join([f"- {k}: {v}" for k, v in categories.items()])
            return (
                f"[Placeholder] Would categorize email from {sender}\n"
                f"Subject: {email_subject}\n"
                f"Categories:\n{cats}"
            )

        @tool
        def research_sender(email: str, name: str) -> str:
            """Research a sender — who are they, what company, LinkedIn, etc."""
            # TODO: Implement with web search
            return f"[Placeholder] Would research sender: {name} ({email})"

        @tool
        def draft_reply(original_email: str, tone: str = "professional") -> str:
            """Draft a reply to an email."""
            return f"[Placeholder] Would draft {tone} reply to email"

        @tool
        def create_gmail_draft(to: str, subject: str, body: str) -> str:
            """Create a draft in Gmail (doesn't send — user reviews first)."""
            # TODO: Implement with Gmail API
            return f"[Placeholder] Would create Gmail draft to {to}: {subject}"

        @tool
        def archive_email(email_id: str) -> str:
            """Archive an email."""
            return f"[Placeholder] Would archive email {email_id}"

        @tool
        def label_email(email_id: str, label: str) -> str:
            """Apply a label to an email."""
            return f"[Placeholder] Would label email {email_id} as '{label}'"

        return [fetch_unread_emails, categorize_email, research_sender, draft_reply, create_gmail_draft, archive_email, label_email]

    def get_system_prompt(self) -> str:
        categories = self.config.get("categories", {})
        auto_actions = self.config.get("auto_actions", {})
        return f"""You are the Inbox Manager agent for Holus.

Your mission: Keep the user's inbox clean and ensure nothing important is missed.

CATEGORIES:
{chr(10).join(f'- {k}: {v}' for k, v in categories.items())}

AUTO-ACTIONS:
{chr(10).join(f'- {k}: {v}' for k, v in auto_actions.items())}

WORKFLOW:
1. Fetch unread emails
2. For each email:
   a. Categorize it
   b. Apply the auto-action for that category
   c. For "opportunity" emails — research the sender first
   d. For "action_needed" emails — draft a response and escalate
3. Send summary to user via notification

RULES:
- NEVER send emails automatically — only create drafts
- Always research unknown senders before categorizing as "opportunity"
- Check memory for previous interactions with the same sender
- Be conservative with "spam" — when in doubt, mark as "fyi"
- Include sender research in escalation messages
"""

    async def run(self) -> dict[str, Any]:
        logger.info("📧 Inbox Manager checking emails...")

        result = await self.execute(
            "Check my inbox for unread emails. Categorize each one, "
            "apply auto-actions, draft replies where needed, "
            "and send me a summary of what needs my attention.",
            complexity=TaskComplexity.SIMPLE,
        )

        # Always send inbox summary
        await self.notify(f"📧 *Inbox Summary*\n\n{result[:500]}")

        self.remember(
            f"Inbox check: {result[:300]}",
            metadata={"type": "inbox_check"},
        )

        return {"status": "completed", "result": result}
