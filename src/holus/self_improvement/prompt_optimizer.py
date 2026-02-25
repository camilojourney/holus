"""Prompt Optimizer: targeted prompt rewriting triggered by failure streaks.

When the trajectory logger detects 3+ consecutive failures for an agent/task
combination, the Prompt Optimizer rewrites the failing prompt using Opus.

Architecture:
  - Triggered by: ``TrajectoryLogger.needs_optimization()`` returning ``True``.
  - Uses Opus for the rewrite (strategic reasoning).
  - Stores prompt versions with timestamps for rollback.
  - Supports A/B testing: 20% new prompt, 80% old prompt for 1 week.

The Prompt Optimizer sits between Reflexion (per-task) and DSPy (monthly):
  - Reflexion handles individual failures via reflection.
  - Prompt Optimizer handles failure streaks via targeted rewriting.
  - DSPy handles systematic optimization over large datasets.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt version management
# ---------------------------------------------------------------------------

@dataclass
class PromptVersion:
    """A versioned prompt with metadata."""

    version_id: str
    agent_id: str
    prompt_text: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    source: str = "manual"  # "manual" | "optimizer" | "dspy"
    parent_version: str | None = None
    performance_score: float | None = None
    is_active: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "agent_id": self.agent_id,
            "prompt_text": self.prompt_text,
            "created_at": self.created_at,
            "source": self.source,
            "parent_version": self.parent_version,
            "performance_score": self.performance_score,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


class PromptVersionStore:
    """File-backed prompt version store.

    Prompts are stored as JSON files in a versioned directory:
      ``config/prompts/{agent_id}/v{N}.json``
    """

    def __init__(self, base_dir: Path = Path("config/prompts")) -> None:
        self.base_dir = base_dir

    def save(self, version: PromptVersion) -> Path:
        """Save a prompt version to disk."""
        agent_dir = self.base_dir / version.agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        filepath = agent_dir / f"{version.version_id}.json"
        filepath.write_text(json.dumps(version.to_dict(), indent=2))
        logger.info("Saved prompt version %s for %s", version.version_id, version.agent_id)
        return filepath

    def load(self, agent_id: str, version_id: str) -> PromptVersion | None:
        """Load a specific prompt version."""
        filepath = self.base_dir / agent_id / f"{version_id}.json"
        if not filepath.exists():
            return None
        data = json.loads(filepath.read_text())
        return PromptVersion(**data)

    def load_active(self, agent_id: str) -> PromptVersion | None:
        """Load the currently active prompt version for an agent."""
        agent_dir = self.base_dir / agent_id
        if not agent_dir.exists():
            return None

        for filepath in sorted(agent_dir.glob("*.json"), reverse=True):
            data = json.loads(filepath.read_text())
            if data.get("is_active"):
                return PromptVersion(**data)

        # Fall back to most recent
        files = sorted(agent_dir.glob("*.json"), reverse=True)
        if files:
            data = json.loads(files[0].read_text())
            return PromptVersion(**data)

        return None

    def list_versions(self, agent_id: str) -> list[PromptVersion]:
        """List all prompt versions for an agent, newest first."""
        agent_dir = self.base_dir / agent_id
        if not agent_dir.exists():
            return []

        versions: list[PromptVersion] = []
        for filepath in sorted(agent_dir.glob("*.json"), reverse=True):
            data = json.loads(filepath.read_text())
            versions.append(PromptVersion(**data))
        return versions

    def activate(self, agent_id: str, version_id: str) -> None:
        """Set a specific version as active, deactivating all others."""
        agent_dir = self.base_dir / agent_id
        if not agent_dir.exists():
            return

        for filepath in agent_dir.glob("*.json"):
            data = json.loads(filepath.read_text())
            data["is_active"] = (data["version_id"] == version_id)
            filepath.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Prompt Optimizer
# ---------------------------------------------------------------------------

OPTIMIZER_PROMPT = """You are the Prompt Optimizer for Holus.
An agent has been failing repeatedly on a specific task type.
Your job: rewrite the agent's system prompt to fix the failure pattern.

## Current Prompt
{current_prompt}

## Failure Analysis
Agent: {agent_id}
Task type: {task_type}
Failure streak: {failure_count} consecutive failures
Recent failures:
{failure_details}

## Instructions
1. Identify the specific weakness in the current prompt that caused failures.
2. Rewrite the prompt to address EXACTLY those failure modes.
3. Keep the prompt's core identity and guardrails intact.
4. Do NOT make the prompt longer just for the sake of it.
5. Focus on PRECISION -- add specific instructions where the prompt was vague.

## Output Format (JSON only)
{
    "analysis": "What went wrong and why",
    "changes_made": ["List of specific changes"],
    "new_prompt": "The complete rewritten prompt"
}
"""


class PromptOptimizer:
    """Targeted prompt rewriting triggered by failure streaks.

    Usage::

        optimizer = PromptOptimizer(api_key="sk-...")
        result = optimizer.optimize(
            agent_id="trading-agent",
            task_type="trade_signal",
            current_prompt="You are the Signal Generator...",
            failure_details=[
                {"task": "...", "output": "...", "feedback": "..."},
            ],
        )
        # result contains the new prompt and analysis
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-opus-4-20250514",
        version_store: PromptVersionStore | None = None,
    ) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._store = version_store or PromptVersionStore()

    def optimize(
        self,
        agent_id: str,
        task_type: str,
        current_prompt: str,
        failure_details: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Rewrite a prompt based on failure analysis.

        Args:
            agent_id: The failing agent.
            task_type: The task type with failures.
            current_prompt: The current system prompt.
            failure_details: Recent failures with task, output, feedback.

        Returns:
            Dict with ``analysis``, ``changes_made``, ``new_prompt``,
            and ``version_id``.
        """
        failure_text = ""
        for i, f in enumerate(failure_details[:5], 1):  # Max 5 failures
            failure_text += (
                f"\n### Failure {i}\n"
                f"Task: {f.get('task', '')[:300]}\n"
                f"Output: {f.get('output', '')[:300]}\n"
                f"Judge Feedback: {f.get('feedback', '')[:300]}\n"
            )

        user_message = OPTIMIZER_PROMPT.format(
            current_prompt=current_prompt,
            agent_id=agent_id,
            task_type=task_type,
            failure_count=len(failure_details),
            failure_details=failure_text,
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=8192,
                temperature=0.1,  # Slight creativity for rewriting
                messages=[{"role": "user", "content": user_message}],
            )

            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            result = json.loads(response_text)

        except (json.JSONDecodeError, Exception) as exc:
            logger.exception("Prompt optimization failed")
            return {
                "analysis": f"Optimization failed: {exc}",
                "changes_made": [],
                "new_prompt": current_prompt,
                "version_id": None,
            }

        # Save the new version
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version_id = f"v_{timestamp}_{task_type}"

        current_version = self._store.load_active(agent_id)
        parent_id = current_version.version_id if current_version else None

        new_version = PromptVersion(
            version_id=version_id,
            agent_id=agent_id,
            prompt_text=result.get("new_prompt", current_prompt),
            source="optimizer",
            parent_version=parent_id,
            is_active=False,  # Not active until A/B test passes
            metadata={
                "task_type": task_type,
                "failure_count": len(failure_details),
                "analysis": result.get("analysis", ""),
                "changes": result.get("changes_made", []),
            },
        )

        self._store.save(new_version)

        return {
            "analysis": result.get("analysis", ""),
            "changes_made": result.get("changes_made", []),
            "new_prompt": result.get("new_prompt", current_prompt),
            "version_id": version_id,
        }

    def should_use_new_prompt(
        self,
        agent_id: str,
        ab_test_ratio: float = 0.2,
    ) -> tuple[bool, PromptVersion | None]:
        """Determine whether to use the new (A/B test) or old prompt.

        Returns:
            Tuple of (use_new, version).  If ``use_new`` is True, use the
            latest non-active version.  Otherwise, use the active version.
        """
        import random

        versions = self._store.list_versions(agent_id)
        if len(versions) < 2:
            return False, versions[0] if versions else None

        active = next((v for v in versions if v.is_active), versions[-1])
        candidate = next((v for v in versions if not v.is_active and v.source == "optimizer"), None)

        if candidate and random.random() < ab_test_ratio:
            return True, candidate

        return False, active

    def promote_version(self, agent_id: str, version_id: str) -> None:
        """Promote a prompt version to active after successful A/B test."""
        self._store.activate(agent_id, version_id)
        logger.info("Promoted prompt version %s for %s", version_id, agent_id)

    def rollback(self, agent_id: str) -> PromptVersion | None:
        """Rollback to the previous active version."""
        versions = self._store.list_versions(agent_id)
        if len(versions) < 2:
            return None

        # Find the second-newest version and activate it
        for v in versions:
            if not v.is_active:
                self._store.activate(agent_id, v.version_id)
                logger.info("Rolled back %s to version %s", agent_id, v.version_id)
                return v

        return None
