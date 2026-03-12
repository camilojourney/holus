"""Central catalog of all Holus agents. Reads agents/AGENTS.yaml."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default path: relative to this source file → repo_root/agents/AGENTS.yaml
# registry.py lives at src/holus/agents/registry.py
# parents[0] = src/holus/agents, [1] = src/holus, [2] = src, [3] = repo_root
_DEFAULT_AGENTS_YAML = Path(__file__).parents[3] / "agents" / "AGENTS.yaml"

# ---------------------------------------------------------------------------
# Evaluator routing — owned by the registry, not by judge.py
# ---------------------------------------------------------------------------

EVALUATOR_ROUTING: dict[str, list[str]] = {
    "TUTORIAL": ["written-content-judge", "brand-safety-judge"],
    "CAROUSEL": ["visual-content-judge", "brand-safety-judge"],
    "VIDEO_REEL": ["video-content-judge", "brand-safety-judge"],
    "THREAD": ["written-content-judge", "platform-fit-judge"],
    "DEMO": ["video-content-judge", "brand-safety-judge"],
    "TIPS": ["written-content-judge", "brand-safety-judge"],
    "CASE_STUDY": ["written-content-judge", "brand-safety-judge"],
    "ANNOUNCEMENT": ["written-content-judge", "brand-safety-judge"],
    "EDUCATIONAL": ["written-content-judge", "seo-judge"],
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class AgentInfo:
    """Structured representation of one agent from AGENTS.yaml."""

    agent_id: str
    role: str
    type: str  # manager | specialist | evaluator | ops
    model_tier: str
    status: str  # active | planned | deprecated
    version: str
    prompt_path: str
    category: str | None = None
    evaluated_by: list[str] = field(default_factory=list)
    evaluates_with: list[str] = field(default_factory=list)
    rubric: list[str] = field(default_factory=list)
    is_gate: bool = False


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class AgentRegistry:
    """In-memory catalog of all Holus agents.

    Reads ``agents/AGENTS.yaml`` once at construction time.  Call
    :meth:`reload` to refresh after the YAML has been edited (requires a
    running process — file changes are not watched automatically).

    Usage::

        registry = AgentRegistry()
        all_active = registry.get_active_agents()
        hook_info  = registry.get_agent("hook-architect")
        prompt_md  = registry.get_agent_prompt("hook-architect")
    """

    def __init__(self, yaml_path: Path | None = None) -> None:
        self._yaml_path = yaml_path or _DEFAULT_AGENTS_YAML
        self._agents: dict[str, AgentInfo] = {}
        self._repo_root: Path = self._yaml_path.parent.parent
        self._load()

    # -- Loading -----------------------------------------------------------

    def _load(self) -> None:
        """Parse AGENTS.yaml and populate the internal dict.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            yaml.YAMLError: If the file cannot be parsed.
        """
        raw = self._yaml_path.read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(raw)

        agents_section: dict[str, Any] = data.get("agents", {})
        self._agents = {}

        for agent_id, attrs in agents_section.items():
            if not isinstance(attrs, dict):
                continue

            # Normalise evaluated_by / evaluates_with to list[str]
            evaluated_by = attrs.get("evaluated_by", [])
            if isinstance(evaluated_by, str):
                evaluated_by = [evaluated_by]
            elif evaluated_by is None:
                evaluated_by = []

            evaluates_with = attrs.get("evaluates_with", [])
            if isinstance(evaluates_with, str):
                evaluates_with = [evaluates_with]
            elif evaluates_with is None:
                evaluates_with = []

            rubric = attrs.get("rubric", [])
            if rubric is None:
                rubric = []

            self._agents[agent_id] = AgentInfo(
                agent_id=agent_id,
                role=attrs.get("role", ""),
                type=attrs.get("type", ""),
                category=attrs.get("category"),
                model_tier=attrs.get("model_tier", "operational"),
                status=attrs.get("status", "planned"),
                version=attrs.get("version", "0.1.0"),
                prompt_path=attrs.get("prompt", ""),
                evaluated_by=evaluated_by,
                evaluates_with=evaluates_with,
                rubric=list(rubric),
                is_gate=bool(attrs.get("gate", False)),
            )

        logger.info("registry: loaded %d agents from %s", len(self._agents), self._yaml_path)

    def reload(self) -> None:
        """Re-read AGENTS.yaml from disk.  Useful for tests and long-running processes."""
        self._load()

    # -- Queries -----------------------------------------------------------

    def list_agents(
        self,
        *,
        type: str | None = None,  # noqa: A002  (shadows builtin intentionally for clean API)
        status: str | None = None,
        category: str | None = None,
    ) -> list[AgentInfo]:
        """Return agents, optionally filtered.

        Args:
            type: Filter by agent type (``"manager"``, ``"specialist"``,
                ``"evaluator"``, ``"ops"``).
            status: Filter by status (``"active"``, ``"planned"``,
                ``"deprecated"``).
            category: Filter by category (e.g. ``"written-authority"``).

        Returns:
            List of matching :class:`AgentInfo` objects.
        """
        results = list(self._agents.values())
        if type is not None:
            results = [a for a in results if a.type == type]
        if status is not None:
            results = [a for a in results if a.status == status]
        if category is not None:
            results = [a for a in results if a.category == category]
        return results

    def get_agent(self, agent_id: str) -> AgentInfo:
        """Return the :class:`AgentInfo` for *agent_id*.

        Raises:
            KeyError: If the agent is not in the registry.
        """
        try:
            return self._agents[agent_id]
        except KeyError:
            raise KeyError(f"Agent '{agent_id}' not found in registry") from None

    def get_active_agents(self) -> list[AgentInfo]:
        """Return all agents with ``status == "active"``."""
        return self.list_agents(status="active")

    def get_evaluators(self) -> list[AgentInfo]:
        """Return all agents with ``type == "evaluator"``."""
        return self.list_agents(type="evaluator")

    def get_evaluator_for(self, content_type: str) -> list[str]:
        """Return the evaluator IDs for *content_type*.

        Falls back to ``["written-content-judge"]`` for unknown content types.
        Logs at DEBUG level on fallback.

        Args:
            content_type: Upper-case content type string (e.g. ``"TUTORIAL"``).

        Returns:
            List of evaluator agent IDs.
        """
        key = content_type.upper()
        if key not in EVALUATOR_ROUTING:
            logger.debug(
                "registry: unknown content_type '%s' — falling back to written-content-judge",
                content_type,
            )
            return ["written-content-judge"]
        return list(EVALUATOR_ROUTING[key])

    def get_agent_prompt(self, agent_id: str) -> str:
        """Read the .md prompt file for *agent_id*.

        Resolves through PromptLoader layers:
          1. ``config/prompts/{agent_id}/current.md`` (optimizer variant)
          2. ``agents/{prompt_path}`` (canonical .md file)
          3. Empty string fallback (PromptLoader emits WARNING)

        Returns:
            The resolved prompt text.
        """
        from holus.core.prompt_loader import PromptLoader

        self.get_agent(agent_id)  # raises KeyError if unknown
        loader = PromptLoader(repo_root=self._repo_root)
        return loader.get_prompt(agent_id, fallback=f"You are the {agent_id} agent for Holus.")
