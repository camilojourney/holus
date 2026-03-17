"""DSPy bridge — bootstrap few-shot examples from trajectory data.

Converts top-scoring trajectory entries into DSPy-compatible training
examples, then uses BootstrapFewShot to auto-select the best examples
for each agent's prompt.

Activation gate: n >= 500 total trajectory entries (per consultation).

The bridge does NOT run DSPy optimization directly (that requires
dspy library). Instead, it prepares the dataset and few-shot examples
that can be injected into prompts via PromptLoader Layer 1.

Usage::

    bridge = DSPyBridge()
    dataset = bridge.build_dataset(agent_id="idea-generator", min_score=0.8)
    few_shot = bridge.select_few_shot(dataset, k=5)
    bridge.save_to_prompt(agent_id="idea-generator", examples=few_shot)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")
PROMPTS_DIR = Path("config/prompts")
MIN_ENTRIES_FOR_DSPY = 500
MIN_SCORE_FOR_EXAMPLE = 0.75


@dataclass
class DSPyExample:
    """A single training example for DSPy optimization."""

    task: str  # The input task/idea
    output: str  # The agent's output
    score: float  # Judge score (0-1)
    agent_id: str
    content_type: str
    platform: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "output": self.output,
            "score": self.score,
            "agent_id": self.agent_id,
            "content_type": self.content_type,
            "platform": self.platform,
        }

    def to_few_shot_format(self) -> str:
        """Format as a few-shot example for prompt injection."""
        return (
            f"<example>\n"
            f"<task>{self.task}</task>\n"
            f"<output>{self.output[:500]}</output>\n"
            f"<score>{self.score:.2f}</score>\n"
            f"</example>"
        )


class DSPyBridge:
    """Bridge between Holus trajectory data and DSPy optimization.

    Extracts high-scoring examples from trajectory, formats them
    for few-shot prompting, and saves to PromptLoader Layer 1.
    """

    def __init__(
        self,
        trajectory_path: Path = TRAJECTORY_PATH,
        prompts_dir: Path = PROMPTS_DIR,
    ) -> None:
        self._trajectory_path = trajectory_path
        self._prompts_dir = prompts_dir

    def count_entries(self) -> int:
        """Count total trajectory entries."""
        if not self._trajectory_path.exists():
            return 0
        with open(self._trajectory_path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())

    def is_activated(self) -> bool:
        """Check if DSPy bridge should be active (n >= 500)."""
        return self.count_entries() >= MIN_ENTRIES_FOR_DSPY

    def build_dataset(
        self,
        agent_id: str,
        *,
        min_score: float = MIN_SCORE_FOR_EXAMPLE,
        max_examples: int = 100,
    ) -> list[DSPyExample]:
        """Extract high-scoring examples from trajectory for an agent.

        Filters to entries with judge_score >= min_score and valid output.
        Returns sorted by score (highest first), capped at max_examples.
        """
        if not self._trajectory_path.exists():
            return []

        examples: list[DSPyExample] = []

        with open(self._trajectory_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    entry = json.loads(line.strip())
                except (json.JSONDecodeError, AttributeError):
                    continue

                if entry.get("agent_id") != agent_id:
                    continue

                score = entry.get("judge_score")
                if score is None or score < min_score:
                    continue

                task = entry.get("task_summary", "")
                # Try to reconstruct output from metadata
                meta = entry.get("metadata", {})
                output = meta.get("output", meta.get("generated_text", ""))

                if not task or not output:
                    continue

                examples.append(DSPyExample(
                    task=task,
                    output=output,
                    score=score,
                    agent_id=agent_id,
                    content_type=meta.get("content_type", "unknown"),
                    platform=meta.get("platform", "unknown"),
                    metadata=meta,
                ))

        # Sort by score descending, take top N
        examples.sort(key=lambda e: e.score, reverse=True)
        return examples[:max_examples]

    def select_few_shot(
        self,
        dataset: list[DSPyExample],
        k: int = 5,
        *,
        diverse: bool = True,
    ) -> list[DSPyExample]:
        """Select k few-shot examples from the dataset.

        If diverse=True, tries to pick examples from different
        content_types and platforms (diversity > pure score).
        """
        if len(dataset) <= k:
            return dataset

        if not diverse:
            return dataset[:k]

        # Greedy diversity selection
        selected: list[DSPyExample] = []
        seen_keys: set[str] = set()

        # First pass: one per (content_type, platform) combo
        for ex in dataset:
            key = f"{ex.content_type}:{ex.platform}"
            if key not in seen_keys and len(selected) < k:
                selected.append(ex)
                seen_keys.add(key)

        # Fill remaining with highest-scoring
        for ex in dataset:
            if len(selected) >= k:
                break
            if ex not in selected:
                selected.append(ex)

        return selected

    def format_few_shot_block(self, examples: list[DSPyExample]) -> str:
        """Format examples as a few-shot block for prompt injection."""
        if not examples:
            return ""

        lines = [
            "<few_shot_examples>",
            "These are examples of high-scoring outputs. Use them as reference for quality and style.",
            "",
        ]
        for ex in examples:
            lines.append(ex.to_few_shot_format())
            lines.append("")

        lines.append("</few_shot_examples>")
        return "\n".join(lines)

    def save_to_prompt(
        self,
        agent_id: str,
        examples: list[DSPyExample],
    ) -> Path | None:
        """Save few-shot examples as a prompt supplement for PromptLoader.

        Writes to config/prompts/{agent_id}/few_shot.md which can be
        loaded alongside the main prompt.
        """
        if not examples:
            return None

        agent_dir = self._prompts_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        few_shot_path = agent_dir / "few_shot.md"
        content = self.format_few_shot_block(examples)
        few_shot_path.write_text(content, encoding="utf-8")

        logger.info(
            "Saved %d few-shot examples for %s to %s",
            len(examples), agent_id, few_shot_path,
        )
        return few_shot_path

    def save_dataset(
        self,
        agent_id: str,
        dataset: list[DSPyExample],
    ) -> Path:
        """Save the full dataset as JSONL for DSPy training."""
        agent_dir = self._prompts_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        dataset_path = agent_dir / "dspy_dataset.jsonl"
        with open(dataset_path, "w", encoding="utf-8") as fh:
            for ex in dataset:
                fh.write(json.dumps(ex.to_dict()) + "\n")

        logger.info(
            "Saved %d training examples for %s to %s",
            len(dataset), agent_id, dataset_path,
        )
        return dataset_path
