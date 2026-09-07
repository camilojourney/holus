"""Execution facts for local stages, shared by queue traces and the read API.

Registry associations describe definitions, never workers that ran. Legacy traces
have no schema_version/execution_kind and remain unverified historical labels.
No prompts, content payloads, hashes, external clients, or trajectory writes here.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from holus.agents.registry import AgentInfo, AgentRegistry

T = TypeVar("T")


class StageExecution(BaseModel):
    """One completed span; optional new fields allow old records to read unchanged."""

    model_config = ConfigDict(frozen=True)

    agent_id: str
    model: str | None = None
    role: str | None = None
    at: datetime | None = None
    quality_score: str | None = None
    verdict: str | None = None
    schema_version: Literal[1] | None = None
    run_id: str | None = None
    group_id: str | None = None
    piece_id: str | None = None
    stage_id: str | None = None
    execution_id: str | None = None
    executor_id: str | None = None
    execution_kind: Literal["deterministic"] | None = None
    registered_agent_id: str | None = None
    registry_status: str | None = None
    agent_version: str | None = None
    prompt_path: str | None = None
    prompt_version: str | None = None
    prompt_sha: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    latency_ms: float | None = None
    status: Literal["success", "error"] | None = None
    error_code: str | None = None


class StageWiringError(ValueError):
    """A required registry association is missing or not active."""


def check_stage_agents(registry: AgentRegistry, agent_ids: set[str]) -> dict[str, AgentInfo]:
    """Metadata-only preflight. Do not resolve prompts or evaluator routing."""
    agents = {}
    for agent_id in sorted(agent_ids):
        try:
            agent = registry.get_agent(agent_id)
        except KeyError:
            raise StageWiringError(f"missing_stage_agent:{agent_id}") from None
        if agent.status != "active":
            raise StageWiringError(f"inactive_stage_agent:{agent_id}")
        agents[agent_id] = agent
    return agents


class StageExecutionRecorder:
    """Request-local, append-only completed spans, optionally observable on failure."""

    def __init__(
        self,
        run_id: str,
        group_id: str,
        sink: list[StageExecution] | None = None,
    ) -> None:
        self.run_id = run_id
        self.group_id = group_id
        self.records: list[StageExecution] = []
        self._sink = sink

    @contextmanager
    def stage(
        self,
        stage_id: str,
        executor: Callable[..., Any],
        *,
        piece_id: str | None = None,
        registered_agent: AgentInfo | None = None,
    ) -> Iterator[None]:
        if not callable(executor):
            raise StageWiringError(f"non_callable_stage:{stage_id}")
        module = getattr(executor, "__module__", None)
        name = getattr(executor, "__qualname__", None)
        if not isinstance(module, str) or not isinstance(name, str):
            raise StageWiringError(f"unidentified_stage_executor:{stage_id}")
        executor_id = f"{module}.{name}"
        started_at = datetime.now(UTC)
        started = perf_counter()
        status: Literal["success", "error"] = "success"
        error_code = None
        try:
            yield
        except BaseException as exc:
            status = "error"
            # Only the type, not a potentially private exception message.
            error_code = type(exc).__name__
            raise
        finally:
            finished_at = datetime.now(UTC)
            record = StageExecution(
                schema_version=1,
                run_id=self.run_id,
                group_id=self.group_id,
                piece_id=piece_id,
                stage_id=stage_id,
                execution_id=f"{self.run_id}:{len(self.records) + 1}",
                agent_id=executor_id,
                executor_id=executor_id,
                execution_kind="deterministic",
                role=stage_id,
                at=started_at,
                registered_agent_id=registered_agent.agent_id if registered_agent else None,
                registry_status=registered_agent.status if registered_agent else None,
                agent_version=registered_agent.version if registered_agent else None,
                prompt_path=registered_agent.prompt_path if registered_agent else None,
                started_at=started_at,
                finished_at=finished_at,
                latency_ms=(perf_counter() - started) * 1000,
                status=status,
                error_code=error_code,
            )
            self.records.append(record)
            if self._sink is not None:
                self._sink.append(record)

    def run(
        self,
        stage_id: str,
        executor: Callable[..., T],
        *args: Any,
        piece_id: str | None = None,
        registered_agent: AgentInfo | None = None,
        **kwargs: Any,
    ) -> T:
        with self.stage(
            stage_id,
            executor,
            piece_id=piece_id,
            registered_agent=registered_agent,
        ):
            return executor(*args, **kwargs)

    def for_piece(self, piece_id: str) -> list[dict[str, Any]]:
        """Shared spans retain the same IDs when projected into multiple pieces."""
        return [
            record.model_dump(mode="json")
            for record in self.records
            if record.piece_id in (None, piece_id)
        ]
