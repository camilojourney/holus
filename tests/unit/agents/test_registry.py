"""Tests for AgentRegistry (Spec 030).

Verifies:
- Registry loads all 32 agents from AGENTS.yaml
- list_agents filters by type, status, category
- get_agent returns correct AgentInfo
- get_active_agents excludes planned/deprecated agents
- get_evaluators returns all evaluators
- get_evaluator_for returns correct evaluators per content type
- get_evaluator_for falls back to written-content-judge for unknown types
- get_agent raises KeyError for unknown agents
- reload() re-reads YAML (useful for tests)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from holus.agents.registry import AgentRegistry

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def registry() -> AgentRegistry:
    """Load the real AGENTS.yaml — tests verify the actual file content."""
    return AgentRegistry()


@pytest.fixture
def tmp_agents_yaml(tmp_path: Path) -> Path:
    """Create a minimal AGENTS.yaml for isolated unit tests."""
    data = {
        "agents": {
            "alpha-agent": {
                "role": "Alpha role",
                "type": "specialist",
                "category": "written-authority",
                "model_tier": "operational",
                "status": "active",
                "version": "1.0.0",
                "prompt": "specialists/written-authority/alpha-agent.md",
                "evaluated_by": "written-content-judge",
            },
            "beta-agent": {
                "role": "Beta role",
                "type": "evaluator",
                "category": "visual",
                "model_tier": "classification",
                "status": "planned",
                "version": "0.1.0",
                "prompt": "evaluators/beta-agent.md",
                "rubric": ["score_a", "score_b"],
            },
            "gamma-manager": {
                "role": "Gamma manager",
                "type": "manager",
                "model_tier": "strategic",
                "status": "active",
                "version": "2.0.0",
                "prompt": "managers/gamma-manager.md",
                "evaluates_with": ["written-content-judge", "brand-safety-judge"],
            },
            "delta-gate": {
                "role": "Delta gate",
                "type": "specialist",
                "category": "written-authority",
                "model_tier": "classification",
                "status": "active",
                "version": "1.0.0",
                "prompt": "specialists/written-authority/delta-gate.md",
                "evaluated_by": "brand-safety-judge",
                "gate": True,
            },
        }
    }
    yaml_path = tmp_path / "AGENTS.yaml"
    yaml_path.write_text(yaml.dump(data), encoding="utf-8")
    return yaml_path


@pytest.fixture
def small_registry(tmp_agents_yaml: Path) -> AgentRegistry:
    return AgentRegistry(yaml_path=tmp_agents_yaml)


# ---------------------------------------------------------------------------
# Tests: loading from real AGENTS.yaml
# ---------------------------------------------------------------------------


class TestRegistryLoad:
    def test_loads_32_agents(self, registry: AgentRegistry) -> None:
        """AGENTS.yaml must contain exactly 32 agents."""
        assert len(registry.list_agents()) == 32

    def test_list_evaluators_returns_7(self, registry: AgentRegistry) -> None:
        evaluators = registry.list_agents(type="evaluator")
        assert len(evaluators) == 7

    def test_list_active_excludes_planned(self, registry: AgentRegistry) -> None:
        active = registry.list_agents(status="active")
        planned = registry.list_agents(status="planned")
        assert all(a.status == "active" for a in active)
        assert all(a.status == "planned" for a in planned)
        # Active + planned should not overlap
        active_ids = {a.agent_id for a in active}
        planned_ids = {a.agent_id for a in planned}
        assert active_ids.isdisjoint(planned_ids)

    def test_list_by_category(self, registry: AgentRegistry) -> None:
        written = registry.list_agents(category="written-authority")
        assert len(written) > 0
        assert all(a.category == "written-authority" for a in written)

    def test_get_agent_returns_correct_info(self, registry: AgentRegistry) -> None:
        info = registry.get_agent("hook-architect")
        assert info.agent_id == "hook-architect"
        assert info.type == "specialist"
        assert info.category == "written-authority"
        assert info.status == "active"

    def test_get_agent_raises_keyerror_for_unknown(self, registry: AgentRegistry) -> None:
        with pytest.raises(KeyError, match="does-not-exist"):
            registry.get_agent("does-not-exist")

    def test_get_active_agents(self, registry: AgentRegistry) -> None:
        active = registry.get_active_agents()
        assert all(a.status == "active" for a in active)

    def test_get_evaluators(self, registry: AgentRegistry) -> None:
        evaluators = registry.get_evaluators()
        assert all(a.type == "evaluator" for a in evaluators)
        assert len(evaluators) == 7


# ---------------------------------------------------------------------------
# Tests: filtering on small registry
# ---------------------------------------------------------------------------


class TestRegistryFiltering:
    def test_filter_by_type(self, small_registry: AgentRegistry) -> None:
        specialists = small_registry.list_agents(type="specialist")
        assert len(specialists) == 2
        assert all(a.type == "specialist" for a in specialists)

    def test_filter_by_status(self, small_registry: AgentRegistry) -> None:
        planned = small_registry.list_agents(status="planned")
        assert len(planned) == 1
        assert planned[0].agent_id == "beta-agent"

    def test_filter_by_category(self, small_registry: AgentRegistry) -> None:
        written = small_registry.list_agents(category="written-authority")
        assert len(written) == 2

    def test_combined_filter(self, small_registry: AgentRegistry) -> None:
        active_specialists = small_registry.list_agents(type="specialist", status="active")
        assert len(active_specialists) == 2

    def test_no_results_filter(self, small_registry: AgentRegistry) -> None:
        result = small_registry.list_agents(type="ops")
        assert result == []

    def test_evaluated_by_normalised_to_list(self, small_registry: AgentRegistry) -> None:
        """A single string evaluated_by must be stored as a list."""
        info = small_registry.get_agent("alpha-agent")
        assert isinstance(info.evaluated_by, list)
        assert info.evaluated_by == ["written-content-judge"]

    def test_evaluates_with_normalised_to_list(self, small_registry: AgentRegistry) -> None:
        info = small_registry.get_agent("gamma-manager")
        assert isinstance(info.evaluates_with, list)
        assert len(info.evaluates_with) == 2

    def test_rubric_is_list(self, small_registry: AgentRegistry) -> None:
        info = small_registry.get_agent("beta-agent")
        assert isinstance(info.rubric, list)
        assert info.rubric == ["score_a", "score_b"]

    def test_gate_flag(self, small_registry: AgentRegistry) -> None:
        gate = small_registry.get_agent("delta-gate")
        non_gate = small_registry.get_agent("alpha-agent")
        assert gate.is_gate is True
        assert non_gate.is_gate is False


# ---------------------------------------------------------------------------
# Tests: evaluator routing
# ---------------------------------------------------------------------------


class TestEvaluatorRouting:
    @pytest.mark.parametrize(
        "content_type, expected",
        [
            ("TUTORIAL", ["written-content-judge", "brand-safety-judge"]),
            ("CAROUSEL", ["visual-content-judge", "brand-safety-judge"]),
            ("VIDEO_REEL", ["video-content-judge", "brand-safety-judge"]),
            ("THREAD", ["written-content-judge", "platform-fit-judge"]),
            ("DEMO", ["video-content-judge", "brand-safety-judge"]),
            ("TIPS", ["written-content-judge", "brand-safety-judge"]),
            ("CASE_STUDY", ["written-content-judge", "brand-safety-judge"]),
            ("ANNOUNCEMENT", ["written-content-judge", "brand-safety-judge"]),
            ("EDUCATIONAL", ["written-content-judge", "seo-judge"]),
        ],
    )
    def test_known_content_types(
        self,
        registry: AgentRegistry,
        content_type: str,
        expected: list[str],
    ) -> None:
        result = registry.get_evaluator_for(content_type)
        assert result == expected

    def test_unknown_type_falls_back(self, registry: AgentRegistry) -> None:
        result = registry.get_evaluator_for("UNKNOWN_TYPE")
        assert result == ["written-content-judge"]

    def test_unknown_type_does_not_raise(self, registry: AgentRegistry) -> None:
        # Must never raise, regardless of input
        for bad in ["", "RANDOM", "tutorial", "123"]:
            result = registry.get_evaluator_for(bad)
            assert isinstance(result, list)
            assert len(result) >= 1

    def test_case_insensitive_routing(self, registry: AgentRegistry) -> None:
        """Routing must handle lower-case input by upper-casing internally."""
        upper = registry.get_evaluator_for("TUTORIAL")
        lower = registry.get_evaluator_for("tutorial")
        assert upper == lower


# ---------------------------------------------------------------------------
# Tests: reload
# ---------------------------------------------------------------------------


class TestRegistryReload:
    def test_reload_rereads_yaml(self, tmp_agents_yaml: Path) -> None:
        reg = AgentRegistry(yaml_path=tmp_agents_yaml)
        assert len(reg.list_agents()) == 4

        # Add a new agent to the YAML
        existing = yaml.safe_load(tmp_agents_yaml.read_text())
        existing["agents"]["new-agent"] = {
            "role": "New",
            "type": "ops",
            "model_tier": "operational",
            "status": "planned",
            "version": "0.1.0",
            "prompt": "ops/new-agent.md",
        }
        tmp_agents_yaml.write_text(yaml.dump(existing), encoding="utf-8")

        reg.reload()
        assert len(reg.list_agents()) == 5
        assert reg.get_agent("new-agent").type == "ops"
