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
import time
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
        model: str = "anthropic/claude-haiku-4-5-20251001",
        *,
        use_proxy: bool = True,
        proxy_url: str = "http://localhost:8080/v1/chat/completions",
    ) -> None:
        self._model = model
        self._use_proxy = use_proxy
        self._proxy_url = proxy_url

        if not use_proxy:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
        else:
            self._client = None

    # Exceptions worth retrying — transient network / LLM issues.
    # Includes both built-in and requests-specific exception types.
    try:
        import requests as _req_exc
        _TRANSIENT_EXCEPTIONS: tuple[type[Exception], ...] = (
            ConnectionError,
            TimeoutError,
            json.JSONDecodeError,
            _req_exc.exceptions.Timeout,
            _req_exc.exceptions.ConnectionError,
        )
    except ImportError:
        _TRANSIENT_EXCEPTIONS: tuple[type[Exception], ...] = (  # type: ignore[no-redef]
            ConnectionError,
            TimeoutError,
            json.JSONDecodeError,
        )

    def evaluate(
        self,
        task: str,
        task_type: str,
        output: str,
        *,
        custom_rubric: str | None = None,
        max_retries: int = 2,
        retry_delay: float = 2.0,
    ) -> JudgeEvaluation:
        """Evaluate an agent's output, retrying on transient failures.

        Args:
            task: The original task description.
            task_type: Category (``"trade_signal"``, ``"content"``, etc.).
            output: The agent's output to evaluate.
            custom_rubric: Override the default rubric for this task type.
            max_retries: Total attempts (default 2 = 1 initial + 1 retry).
            retry_delay: Base delay in seconds before retry (doubles each time).

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

        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                response_text = self._call_llm(user_message)
                return self._parse_response(response_text)

            except self._TRANSIENT_EXCEPTIONS as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(
                        "Judge transient error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, max_retries, delay, exc,
                    )
                    time.sleep(delay)
                else:
                    logger.warning(
                        "Judge failed after %d attempts: %s", max_retries, exc,
                    )

            except Exception as exc:
                # Non-transient errors (e.g. auth failures) — don't retry
                logger.exception("Judge evaluation error (non-transient)")
                return JudgeEvaluation(
                    verdict=JudgeVerdict.FAIL,
                    score=0.0,
                    dimension_scores={},
                    feedback=f"Judge evaluation error: {exc}",
                    pass_threshold_met=False,
                )

        # All retries exhausted
        feedback = f"Judge evaluation failed after {max_retries} attempts: {last_exc}"
        return JudgeEvaluation(
            verdict=JudgeVerdict.FAIL,
            score=0.0,
            dimension_scores={},
            feedback=feedback,
            pass_threshold_met=False,
        )

    def _call_llm(self, user_message: str) -> str:
        """Make the LLM call for judge evaluation. Raises on network/HTTP errors."""
        if self._use_proxy:
            import requests as _requests

            payload = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 1024,
                "temperature": 0.0,
            }
            resp = _requests.post(
                self._proxy_url,
                json=payload,
                headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
                timeout=120,
            )
            # Treat HTTP 5xx as transient (raises ConnectionError via raise_for_status)
            if resp.status_code >= 500:
                raise ConnectionError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        else:
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
            return response_text

    @staticmethod
    def _parse_response(response_text: str) -> JudgeEvaluation:
        """Parse LLM response into JudgeEvaluation. Raises JSONDecodeError on bad JSON."""
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
