"""Judge Agent: independent quality evaluation of agent outputs.

The Judge is the ground truth for the self-improvement loop.  It scores
agent outputs as PASS / FAIL / PARTIAL with rubric-based evaluation.

Critical design constraints:
  - Uses Haiku (separate from worker models) for cost efficiency and independence.
  - NEVER optimized by DSPy (circular dependency -- you cannot optimize the grader).
  - Always a separate LLM call from the worker (no self-evaluation bias).
  - Provides specific, actionable feedback (not vague "try harder").

Scoring dimensions:
  - Correctness: Does the output answer the task correctly?
  - Completeness: Are all required elements present?
  - Reasoning quality: Is the reasoning sound and well-structured?
  - Actionability: Can the output be directly used/executed?
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class JudgeVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


@dataclass
class JudgeEvaluation:
    """Structured output from the Judge Agent."""

    verdict: JudgeVerdict
    score: float  # 0.0 - 1.0
    dimension_scores: dict[str, float]  # Per-dimension breakdown
    feedback: str  # Specific, actionable feedback
    pass_threshold_met: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "score": self.score,
            "dimension_scores": self.dimension_scores,
            "feedback": self.feedback,
            "pass_threshold_met": self.pass_threshold_met,
        }


# ---------------------------------------------------------------------------
# Judge prompt
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are the Judge Agent for Holus.
Your role: evaluate an agent's output against task requirements.
Be fair but strict.  Your evaluations determine training data quality.

## Scoring Rules
- PASS: score >= 0.8 AND no critical errors
- PARTIAL: score >= 0.5 but has issues
- FAIL: score < 0.5 OR has critical errors

## Response Format (JSON ONLY -- no other text)
{
    "verdict": "PASS" | "FAIL" | "PARTIAL",
    "score": <float 0.0-1.0>,
    "dimension_scores": {
        "correctness": <float 0.0-1.0>,
        "completeness": <float 0.0-1.0>,
        "reasoning_quality": <float 0.0-1.0>,
        "actionability": <float 0.0-1.0>
    },
    "feedback": "<specific feedback: what's wrong, what's missing, what to fix>",
    "pass_threshold_met": <boolean>
}

## Critical Requirements
- Provide SPECIFIC feedback, not generic.  Quote the problematic parts.
- Do NOT inflate scores.  A mediocre output is PARTIAL, not PASS.
- Feedback must be ACTIONABLE -- the agent should know exactly what to fix.
"""

TASK_TYPE_RUBRICS: dict[str, str] = {
    "trade_signal": (
        "For trade signals, check:\n"
        "- Signal direction is clear (BUY/SELL/HOLD)\n"
        "- Confidence is calibrated (not always 0.9+)\n"
        "- Reasoning references specific data points, not vague assertions\n"
        "- Risk assessment includes stop-loss and position sizing\n"
        "- Entry price is specified"
    ),
    "content": (
        "For content, check:\n"
        "- Matches the requested platform and format\n"
        "- SEO keywords are included naturally\n"
        "- Length is appropriate for the platform\n"
        "- Voice matches the brand guidelines\n"
        "- Has a clear call to action or value proposition"
    ),
    "code_review": (
        "For code reviews, check:\n"
        "- Identifies actual bugs, not just style issues\n"
        "- Security concerns are flagged if present\n"
        "- Suggestions are specific (line numbers, code examples)\n"
        "- Verdict matches the severity of findings\n"
        "- Does not miss obvious issues in the diff"
    ),
    "default": (
        "For general tasks, check:\n"
        "- Output directly addresses the task\n"
        "- All requested elements are present\n"
        "- Reasoning is explicit and traceable\n"
        "- Output is structured and actionable"
    ),
}


# ---------------------------------------------------------------------------
# Judge Agent
# ---------------------------------------------------------------------------


class JudgeAgent:
    """Independent quality evaluator for Holus agent outputs.

    Uses Haiku for cost efficiency -- evaluation does not require
    the same model capability as production output generation.

    Usage::

        judge = JudgeAgent(api_key="sk-...")
        evaluation = judge.evaluate(
            task="Analyze AAPL for trade signals",
            task_type="trade_signal",
            output="BUY AAPL at $185 with confidence 0.85...",
        )
        # evaluation.verdict == JudgeVerdict.PASS
        # evaluation.score == 0.87
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-3-5-20241022",
    ) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def evaluate(
        self,
        task: str,
        task_type: str,
        output: str,
        *,
        custom_rubric: str | None = None,
    ) -> JudgeEvaluation:
        """Evaluate an agent's output.

        Args:
            task: The original task description.
            task_type: Category (``"trade_signal"``, ``"content"``, etc.).
            output: The agent's output to evaluate.
            custom_rubric: Override the default rubric for this task type.

        Returns:
            A ``JudgeEvaluation`` with verdict, score, and feedback.
        """
        rubric = custom_rubric or TASK_TYPE_RUBRICS.get(task_type, TASK_TYPE_RUBRICS["default"])

        user_message = (
            f"## Task\n{task}\n\n"
            f"## Task Type\n{task_type}\n\n"
            f"## Agent Output\n{output}\n\n"
            f"## Task-Specific Rubric\n{rubric}\n\n"
            f"Evaluate this output. Respond with JSON only."
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                temperature=0.0,
                system=JUDGE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            evaluation = json.loads(response_text)

            verdict_str = evaluation.get("verdict", "FAIL").upper()
            verdict = (
                JudgeVerdict(verdict_str)
                if verdict_str in JudgeVerdict.__members__
                else JudgeVerdict.FAIL
            )

            return JudgeEvaluation(
                verdict=verdict,
                score=float(evaluation.get("score", 0.0)),
                dimension_scores=evaluation.get("dimension_scores", {}),
                feedback=evaluation.get("feedback", "No feedback provided"),
                pass_threshold_met=evaluation.get("pass_threshold_met", False),
            )

        except json.JSONDecodeError:
            logger.warning("Judge produced invalid JSON")
            return JudgeEvaluation(
                verdict=JudgeVerdict.FAIL,
                score=0.0,
                dimension_scores={},
                feedback="Judge evaluation failed: invalid JSON response",
                pass_threshold_met=False,
            )
        except Exception as exc:
            logger.exception("Judge evaluation error")
            return JudgeEvaluation(
                verdict=JudgeVerdict.FAIL,
                score=0.0,
                dimension_scores={},
                feedback=f"Judge evaluation error: {exc}",
                pass_threshold_met=False,
            )

    def batch_evaluate(
        self,
        items: list[dict[str, str]],
    ) -> list[JudgeEvaluation]:
        """Evaluate multiple outputs.

        Each item in *items* must have ``task``, ``task_type``, and ``output``.
        """
        return [
            self.evaluate(
                task=item["task"],
                task_type=item["task_type"],
                output=item["output"],
            )
            for item in items
        ]

    def evaluate_with_routing(
        self,
        task: str,
        content_type: str,
        output: str,
        *,
        repo_root: Path | None = None,
    ) -> JudgeEvaluation:
        """Evaluate with domain-specific routing based on content_type.

        Uses EVALUATOR_ROUTING from registry to find the right evaluator
        and its rubric dimensions. Falls back to generic evaluate() for
        unknown content types or if registry is unavailable.
        """
        try:
            from holus.agents.registry import AgentRegistry

            root = repo_root or Path(__file__).parents[2]
            registry = AgentRegistry(
                yaml_path=root / "agents" / "AGENTS.yaml"
            )
        except (FileNotFoundError, Exception):
            logger.warning("Could not load agent registry; falling back to generic evaluation")
            return self.evaluate(task=task, task_type=content_type.lower(), output=output)

        evaluator_ids = registry.get_evaluator_for(content_type)
        primary_evaluator_id = evaluator_ids[0] if evaluator_ids else "written-content-judge"

        try:
            evaluator_info = registry.get_agent(primary_evaluator_id)
            rubric_dimensions = evaluator_info.rubric
        except KeyError:
            rubric_dimensions = []

        if not rubric_dimensions:
            return self.evaluate(task=task, task_type=content_type.lower(), output=output)

        # Build domain-specific rubric string from evaluator dimensions
        rubric_text = f"For {content_type} content, evaluate these specific dimensions:\n"
        for dim in rubric_dimensions:
            rubric_text += f"- {dim}: Score 0.0-1.0\n"
        rubric_text += "\nReturn scores for EACH of these dimensions in dimension_scores."

        return self.evaluate(
            task=task,
            task_type=content_type.lower(),
            output=output,
            custom_rubric=rubric_text,
        )
