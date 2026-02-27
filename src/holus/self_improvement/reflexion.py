"""Reflexion implementation: Execute -> Evaluate -> Reflect -> Retry.

Based on "Reflexion: Language Agents with Verbal Reinforcement Learning"
(Shinn et al., NeurIPS 2023).

Agents improve by verbally reflecting on failures, storing reflections
in episodic memory (Mem0), and using them in future attempts.
No weight updates required -- pure in-context learning.

Reflexion operates at two timescales:
  - Per-task (seconds): reflect on failure, retry with reflection in context.
  - Cross-task (days): retrieve relevant past reflections from Mem0.

The bridge to DSPy: when ``ReflectionMemoryManager.get_failure_patterns()``
detects 3+ failures of the same type, it flags for systematic optimization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from holus.integrations.claude_api.client import (
    CachedPrompt,
    HolusClaudeClient,
    ModelTier,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ReflexionState(TypedDict):
    """LangGraph state for the Reflexion loop."""

    # Task information
    task: str
    task_type: str
    agent_id: str

    # Execution state
    attempt: int
    max_attempts: int
    output: str
    evaluation: dict  # {verdict, score, feedback, dimension_scores}

    # Reflection memory
    reflections: list[str]  # Reflections from current task attempts
    episodic_memory: list[str]  # Past reflections from Mem0

    # Final result
    final_output: str
    final_verdict: str  # PASS / FAIL / PARTIAL


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

REFLECTION_PROMPT = """You are reflecting on a failed attempt at a task.
Your goal: produce a concise, actionable reflection that will help you succeed next time.

## Task
{task}

## Your Output
{output}

## Evaluation
Verdict: {verdict}
Score: {score}/1.0
Feedback: {feedback}

## Previous Reflections (if any)
{previous_reflections}

## Instructions
Write a reflection following this structure:
1. **What went wrong**: Identify the specific failure mode (be precise)
2. **Root cause**: Why did this happen? What assumption was incorrect?
3. **Corrective action**: What EXACTLY should I do differently next time?
4. **Key insight**: One sentence capturing the learning

Keep it under 150 words. Be specific, not generic."""


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def execute_node(
    state: ReflexionState,
    client: HolusClaudeClient,
    cached_prompt: CachedPrompt,
    tier: ModelTier,
) -> dict[str, Any]:
    """Execute the agent's task, incorporating reflections into context."""
    reflection_context = ""

    # Episodic memory from past similar tasks
    if state["episodic_memory"]:
        reflection_context += "## Lessons from Previous Similar Tasks\n"
        for i, mem in enumerate(state["episodic_memory"][-5:], 1):
            reflection_context += f"{i}. {mem}\n"
        reflection_context += "\n"

    # Reflections from current task's previous attempts
    if state["reflections"]:
        reflection_context += "## Reflections from Previous Attempts\n"
        for i, ref in enumerate(state["reflections"], 1):
            reflection_context += f"Attempt {i}: {ref}\n"
        reflection_context += "\n"

    message = ""
    if reflection_context:
        message += f"{reflection_context}---\n\n"
    message += f"## Task\n{state['task']}"

    response = client.call(
        cached_prompt=cached_prompt,
        messages=[{"role": "user", "content": message}],
        tier=tier,
        agent_id=state["agent_id"],
    )

    output = ""
    for block in response.content:
        if hasattr(block, "text"):
            output += block.text

    return {"output": output, "attempt": state["attempt"] + 1}


def evaluate_node(
    state: ReflexionState,
    client: HolusClaudeClient,
) -> dict[str, Any]:
    """Judge evaluates the output.  Uses Haiku for cost efficiency."""
    from holus.self_improvement.judge import JudgeAgent

    judge = JudgeAgent()
    evaluation = judge.evaluate(
        task=state["task"],
        task_type=state["task_type"],
        output=state["output"],
    )

    return {
        "evaluation": evaluation.to_dict(),
    }


def reflect_node(
    state: ReflexionState,
    client: HolusClaudeClient,
) -> dict[str, Any]:
    """Generate a verbal reflection on the failure."""
    previous = "\n".join(state["reflections"]) if state["reflections"] else "None"
    eval_data = state.get("evaluation", {})

    message = REFLECTION_PROMPT.format(
        task=state["task"],
        output=state["output"],
        verdict=eval_data.get("verdict", "FAIL"),
        score=eval_data.get("score", 0.0),
        feedback=eval_data.get("feedback", "No feedback"),
        previous_reflections=previous,
    )

    reflect_prompt = CachedPrompt(
        system_prompt="You are a reflective agent. Analyze failures honestly and produce actionable insights.",
    )

    response = client.call(
        cached_prompt=reflect_prompt,
        messages=[{"role": "user", "content": message}],
        tier="operational",
        agent_id=state["agent_id"],
        temperature=0.3,  # Slight creativity for diverse reflections
    )

    reflection = ""
    for block in response.content:
        if hasattr(block, "text"):
            reflection += block.text

    return {"reflections": state["reflections"] + [reflection]}


def should_retry(state: ReflexionState) -> Literal["reflect", "finish_pass", "finish_fail"]:
    """Routing: decide whether to reflect+retry or finish."""
    verdict = state.get("evaluation", {}).get("verdict", "FAIL")

    if verdict == "PASS":
        return "finish_pass"

    if state["attempt"] >= state["max_attempts"]:
        return "finish_fail"

    return "reflect"


def finish_pass(state: ReflexionState) -> dict[str, Any]:
    """Task completed successfully."""
    return {
        "final_output": state["output"],
        "final_verdict": "PASS",
    }


def finish_fail(state: ReflexionState) -> dict[str, Any]:
    """Task failed after all attempts."""
    return {
        "final_output": state["output"],
        "final_verdict": state.get("evaluation", {}).get("verdict", "FAIL"),
    }


# ---------------------------------------------------------------------------
# Reflexion Loop builder
# ---------------------------------------------------------------------------


class ReflexionLoop:
    """Builds and runs a LangGraph-based Reflexion loop.

    Usage::

        loop = ReflexionLoop(client, agent_prompt, tier="strategic")
        result = await loop.run(
            task="Analyze AAPL for trade signals",
            task_type="trade_signal",
            agent_id="trading-agent",
            episodic_memory=["Previous reflection 1", ...],
        )
    """

    def __init__(
        self,
        client: HolusClaudeClient,
        agent_prompt: CachedPrompt,
        tier: ModelTier = "operational",
    ) -> None:
        self._client = client
        self._agent_prompt = agent_prompt
        self._tier = tier

    def build_graph(self) -> StateGraph:
        """Construct the Reflexion loop StateGraph."""
        client = self._client
        prompt = self._agent_prompt
        tier = self._tier

        workflow = StateGraph(ReflexionState)

        workflow.add_node("execute", lambda s: execute_node(s, client, prompt, tier))
        workflow.add_node("evaluate", lambda s: evaluate_node(s, client))
        workflow.add_node("reflect", lambda s: reflect_node(s, client))
        workflow.add_node("finish_pass", finish_pass)
        workflow.add_node("finish_fail", finish_fail)

        workflow.set_entry_point("execute")
        workflow.add_edge("execute", "evaluate")
        workflow.add_conditional_edges(
            "evaluate",
            should_retry,
            {
                "reflect": "reflect",
                "finish_pass": "finish_pass",
                "finish_fail": "finish_fail",
            },
        )
        workflow.add_edge("reflect", "execute")
        workflow.add_edge("finish_pass", END)
        workflow.add_edge("finish_fail", END)

        return workflow

    async def run(
        self,
        task: str,
        task_type: str,
        agent_id: str,
        *,
        max_attempts: int = 3,
        episodic_memory: list[str] | None = None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute the Reflexion loop.

        Args:
            task: The task description.
            task_type: Task category for Judge rubric selection.
            agent_id: The agent being evaluated.
            max_attempts: Maximum retry attempts (default 3).
            episodic_memory: Past reflections from Mem0.
            thread_id: LangGraph thread ID for checkpointing.

        Returns:
            Final state with ``final_output``, ``final_verdict``,
            ``reflections``, and ``evaluation``.
        """
        from langgraph.checkpoint.memory import MemorySaver

        graph = self.build_graph()
        app = graph.compile(checkpointer=MemorySaver())

        initial_state: ReflexionState = {
            "task": task,
            "task_type": task_type,
            "agent_id": agent_id,
            "attempt": 0,
            "max_attempts": max_attempts,
            "output": "",
            "evaluation": {},
            "reflections": [],
            "episodic_memory": episodic_memory or [],
            "final_output": "",
            "final_verdict": "",
        }

        config: dict[str, Any] = {}
        if thread_id:
            config["configurable"] = {"thread_id": thread_id}
        else:
            config["configurable"] = {
                "thread_id": f"{agent_id}_{datetime.now(UTC).isoformat()}",
            }

        result = await app.ainvoke(initial_state, config=config)
        return result


# ---------------------------------------------------------------------------
# Reflection Memory Manager (bridges Reflexion <-> Mem0)
# ---------------------------------------------------------------------------


@dataclass
class ReflectionMemoryManager:
    """Manages storing and retrieving reflections from Mem0.

    Reflections are scoped by agent_id and task_type, enabling
    cross-task learning: a reflection about a failed AAPL trade
    becomes useful context when analyzing MSFT later.
    """

    mem0_client: Any  # HolusMem0Client

    def store_reflection(
        self,
        agent_id: str,
        task_type: str,
        reflection: str,
        task_summary: str,
        score: float,
    ) -> None:
        """Store a reflection in Mem0 after task completion."""
        from holus.memory.mem0_client import MemoryLevel

        memory_text = (
            f"[{task_type}] Score: {score:.2f} | "
            f"Task: {task_summary[:100]} | "
            f"Reflection: {reflection}"
        )

        self.mem0_client.add(
            memory_text,
            level=MemoryLevel.AGENT,
            metadata={
                "type": "reflection",
                "task_type": task_type,
                "score": score,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def retrieve_relevant(
        self,
        task_description: str,
        limit: int = 5,
    ) -> list[str]:
        """Retrieve relevant past reflections for a new task."""
        results = self.mem0_client.search(query=task_description, limit=limit)
        return [r.get("memory", "") for r in results if r.get("memory")]

    def get_failure_patterns(
        self,
        task_type: str,
        min_count: int = 3,
    ) -> list[dict[str, Any]]:
        """Identify recurring failure patterns.

        If the same type of failure appears 3+ times, it signals a systematic
        prompt issue that DSPy or the Prompt Optimizer should address.
        """
        from holus.memory.mem0_client import MemoryLevel

        all_memories = self.mem0_client.get_all(level=MemoryLevel.AGENT)

        # Filter to failed reflections for this task type
        failures = [
            m
            for m in all_memories
            if m.get("metadata", {}).get("task_type") == task_type
            and m.get("metadata", {}).get("type") == "reflection"
            and m.get("metadata", {}).get("score", 1.0) < 0.5
        ]

        if len(failures) >= min_count:
            return failures
        return []
