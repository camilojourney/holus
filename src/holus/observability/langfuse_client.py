"""Langfuse integration for tracing all Holus agent operations.

Every Claude API call, tool invocation, and agent decision flows through
Langfuse.  Self-hosted on the Mac Mini for zero cost and full data ownership.

Langfuse is the data backbone of the self-improvement loop:
  1. Agents run and produce traces.
  2. Judge Agent scores traces.
  3. Scored traces become training data for DSPy optimization.
  4. Cost tracking enables budget monitoring per agent.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def create_langfuse_client(
    public_key: str | None = None,
    secret_key: str | None = None,
    host: str = "http://localhost:3100",
):
    """Create a Langfuse client pointing to the self-hosted instance.

    Keys come from environment variables or explicit params:
      - ``LANGFUSE_PUBLIC_KEY``
      - ``LANGFUSE_SECRET_KEY``
      - ``LANGFUSE_HOST``
    """
    from langfuse import Langfuse

    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


def trace_agent_call(
    agent_id: str,
    task_type: str,
    tier: str = "operational",
):
    """Decorator to trace an entire agent task execution in Langfuse.

    Creates a trace with:
      - Agent identity metadata
      - Task type classification
      - Model tier used
      - Full input/output capture
      - Timing information

    Usage::

        @trace_agent_call("trading_agent", "trade_signal", tier="strategic")
        def analyze_trade(market_data: str, portfolio: str) -> dict:
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                from langfuse.decorators import langfuse_context, observe

                @observe(name=agent_id)
                def traced_fn(*a, **kw):
                    langfuse_context.update_current_trace(
                        name=f"{agent_id}/{task_type}",
                        metadata={
                            "agent_id": agent_id,
                            "task_type": task_type,
                            "model_tier": tier,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                        tags=[agent_id, task_type, tier],
                    )
                    langfuse_context.update_current_observation(
                        input=kw if kw else {"args": str(a)[:1000]},
                    )

                    result = func(*a, **kw)

                    langfuse_context.update_current_observation(
                        output=(result if isinstance(result, (str, dict)) else str(result)[:2000]),
                    )
                    return result

                return traced_fn(*args, **kwargs)

            except ImportError:
                logger.debug("Langfuse not available; running without tracing")
                return func(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# LLM call tracing
# ---------------------------------------------------------------------------


def trace_llm_call(
    langfuse_client: Any,
    trace_id: str,
    agent_id: str,
    model: str,
    input_messages: list[dict[str, Any]],
    output_text: str,
    usage: dict[str, Any],
    cost_usd: float,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log an individual LLM call as a generation within a Langfuse trace.

    Call this from ``HolusClaudeClient`` after every API call.
    """
    try:
        langfuse_client.generation(
            trace_id=trace_id,
            name=f"{agent_id}_llm_call",
            model=model,
            input=input_messages,
            output=output_text,
            usage={
                "input": usage.get("input_tokens", 0),
                "output": usage.get("output_tokens", 0),
                "total": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                "unit": "TOKENS",
                "total_cost": cost_usd,
            },
            metadata={
                "agent_id": agent_id,
                "cache_read_tokens": usage.get("cache_read_tokens", 0),
                "cache_write_tokens": usage.get("cache_write_tokens", 0),
                **(metadata or {}),
            },
        )
    except Exception:
        logger.exception("Failed to trace LLM call for %s", agent_id)


# ---------------------------------------------------------------------------
# Tool call tracing
# ---------------------------------------------------------------------------


def trace_tool_call(
    langfuse_client: Any,
    trace_id: str,
    agent_id: str,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: Any,
    duration_ms: float,
    success: bool = True,
) -> None:
    """Log a tool invocation as a span within a Langfuse trace."""
    try:
        langfuse_client.span(
            trace_id=trace_id,
            name=f"tool:{tool_name}",
            input=tool_input,
            output=str(tool_output)[:2000] if tool_output else None,
            metadata={
                "agent_id": agent_id,
                "tool_name": tool_name,
                "success": success,
                "duration_ms": duration_ms,
            },
        )
    except Exception:
        logger.exception("Failed to trace tool call %s for %s", tool_name, agent_id)


# ---------------------------------------------------------------------------
# Judge scoring
# ---------------------------------------------------------------------------


def record_judge_score(
    langfuse_client: Any,
    trace_id: str,
    verdict: str,
    score: float,
    dimension_scores: dict[str, float] | None = None,
    feedback: str = "",
) -> None:
    """Record the Judge Agent's evaluation as Langfuse scores.

    These scores are used by DSPy to build training datasets:
      - High-scoring traces become positive examples.
      - Low-scoring traces become negative examples.
    """
    try:
        # Primary numeric score
        langfuse_client.score(
            trace_id=trace_id,
            name="judge_verdict",
            value=score,
            comment=f"{verdict}: {feedback}",
        )

        # Categorical verdict
        langfuse_client.score(
            trace_id=trace_id,
            name="verdict_category",
            value=(1.0 if verdict == "PASS" else 0.5 if verdict == "PARTIAL" else 0.0),
            comment=verdict,
        )

        # Per-dimension scores
        if dimension_scores:
            for dim_name, dim_score in dimension_scores.items():
                langfuse_client.score(
                    trace_id=trace_id,
                    name=f"dim_{dim_name}",
                    value=dim_score,
                )

    except Exception:
        logger.exception("Failed to record judge score for trace %s", trace_id)


# ---------------------------------------------------------------------------
# Dataset management (for DSPy integration)
# ---------------------------------------------------------------------------


class LangfuseDatasetManager:
    """Manages evaluation datasets created from Langfuse traces.

    Pipeline:
      1. Agents run and produce traces.
      2. Judge Agent scores traces.
      3. This manager extracts high-quality traces into datasets.
      4. DSPy uses these datasets for MIPROv2 optimization.
    """

    def __init__(self, langfuse_client: Any) -> None:
        self._lf = langfuse_client

    def create_optimization_dataset(
        self,
        agent_id: str,
        task_type: str,
        dataset_name: str | None = None,
        min_score: float = 0.7,
        max_items: int = 200,
    ) -> str:
        """Create a Langfuse dataset from scored traces for DSPy.

        Returns the dataset name.
        """
        if dataset_name is None:
            dataset_name = f"{agent_id}_{task_type}_{datetime.now(UTC).strftime('%Y%m')}"

        self._lf.create_dataset(
            name=dataset_name,
            description=(
                f"Optimization dataset for {agent_id}/{task_type}. "
                f"Min score: {min_score}. "
                f"Created: {datetime.now(UTC).isoformat()}"
            ),
        )

        # Fetch scored traces
        traces = self._lf.fetch_traces(
            name=f"{agent_id}/{task_type}",
            order_by="timestamp",
            limit=max_items * 3,
        )

        items_added = 0
        for trace in traces.data:
            if items_added >= max_items:
                break

            scores = self._lf.fetch_scores(trace_id=trace.id)
            judge_scores = [s for s in scores.data if s.name == "judge_verdict"]

            if not judge_scores or judge_scores[0].value < min_score:
                continue

            input_data = trace.input or {}
            output_data = trace.output or {}
            if not input_data or not output_data:
                continue

            self._lf.create_dataset_item(
                dataset_name=dataset_name,
                input=input_data,
                expected_output=output_data,
                metadata={
                    "trace_id": trace.id,
                    "score": judge_scores[0].value,
                    "verdict": judge_scores[0].comment,
                },
            )
            items_added += 1

        logger.info(
            "Created dataset %s with %d items for %s/%s",
            dataset_name,
            items_added,
            agent_id,
            task_type,
        )
        return dataset_name
