"""Tests for AgentRegistry (Spec 030).

Verifies:
- Registry loads all agents from agentic/agents/AGENTS.yaml
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

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import yaml

from holus.agents.registry import AgentInfo, AgentRegistry

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
    def test_loads_45_agents(self, registry: AgentRegistry) -> None:
        """AGENTS.yaml agent count (update when adding new agents)."""
        assert len(registry.list_agents()) == 45

    def test_list_evaluators_returns_8(self, registry: AgentRegistry) -> None:
        evaluators = registry.list_agents(type="evaluator")
        assert len(evaluators) == 8

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
        assert len(evaluators) == 8


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

    def test_late_rubric_failure_preserves_snapshot(self, tmp_agents_yaml: Path) -> None:
        tmp_agents_yaml.write_text("agents: {alpha: {role: test}}", encoding="utf-8")
        reg = AgentRegistry(tmp_agents_yaml)
        alpha = reg.get_agent("alpha")
        tmp_agents_yaml.write_text(
            "agents:\n  new: {role: new}\n  broken: {rubric: 123}\n", encoding="utf-8"
        )

        with pytest.raises(TypeError):
            reg.reload()

        assert reg.list_agents() == [alpha]
        assert reg.get_agent("alpha") is alpha
        with pytest.raises(KeyError, match="new"):
            reg.get_agent("new")

        tmp_agents_yaml.write_text("agents: {recovered: {status: active}}", encoding="utf-8")
        reg.reload()
        assert [a.agent_id for a in reg.get_active_agents()] == ["recovered"]
        with pytest.raises(KeyError, match="alpha"):
            reg.get_agent("alpha")

    @pytest.mark.parametrize(
        "contents, error, diagnostic",
        [
            ("agents: [", yaml.YAMLError, None),
            ("", TypeError, "root must be a mapping"),
            ("null", TypeError, "root must be a mapping"),
            ("[]", TypeError, "root must be a mapping"),
            ("123", TypeError, "root must be a mapping"),
            ("false", TypeError, "root must be a mapping"),
            ("catalog", TypeError, "root must be a mapping"),
            ("agents: null", TypeError, "agents must be a mapping"),
            ("agents: []", TypeError, "agents must be a mapping"),
            ("agents: 123", TypeError, "agents must be a mapping"),
            ("agents: false", TypeError, "agents must be a mapping"),
            ("agents: catalog", TypeError, "agents must be a mapping"),
            ("agents: {new: {}, broken: null}", TypeError, "agent 'broken' must be a mapping"),
            ("agents: {new: {}, broken: []}", TypeError, "agent 'broken' must be a mapping"),
            ("agents: {new: {}, broken: 123}", TypeError, "agent 'broken' must be a mapping"),
            ("agents: {new: {}, broken: false}", TypeError, "agent 'broken' must be a mapping"),
            ("agents: {new: {}, broken: row}", TypeError, "agent 'broken' must be a mapping"),
            ("agents: {new: {}, broken: {rubric: 123}}", TypeError, "agent 'broken' rubric"),
        ],
    )
    def test_invalid_reload_preserves_all_agents(
        self,
        tmp_agents_yaml: Path,
        contents: str,
        error: type[Exception],
        diagnostic: str | None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        reg = AgentRegistry(tmp_agents_yaml)
        before = reg.list_agents()
        tmp_agents_yaml.write_text(contents, encoding="utf-8")

        with caplog.at_level("INFO"), pytest.raises(error, match=diagnostic):
            reg.reload()

        assert "registry: loaded" not in caplog.text
        assert reg.list_agents() == before
        assert all(reg.get_agent(a.agent_id) is a for a in before)
        assert reg.get_active_agents() == [a for a in before if a.status == "active"]
        assert reg.get_evaluators() == [a for a in before if a.type == "evaluator"]

    @pytest.mark.parametrize("contents", ["{}", "agents: {}"])
    def test_valid_empty_reload_replaces_snapshot(
        self, tmp_agents_yaml: Path, contents: str
    ) -> None:
        reg = AgentRegistry(tmp_agents_yaml)
        tmp_agents_yaml.write_text(contents, encoding="utf-8")
        reg.reload()
        assert reg.list_agents() == []

    def test_consumers_see_old_snapshot_until_all_rows_are_built(
        self, tmp_agents_yaml: Path
    ) -> None:
        reg = AgentRegistry(tmp_agents_yaml)
        before = reg.list_agents()
        tmp_agents_yaml.write_text("agents: {new: {}, last: {}}", encoding="utf-8")
        observed: list[str] = []

        def observe_construction(**kwargs: Any) -> AgentInfo:
            assert reg.list_agents() == before
            assert all(reg.get_agent(a.agent_id) is a for a in before)
            observed.append(kwargs["agent_id"])
            return AgentInfo(**kwargs)

        with patch("holus.agents.registry.AgentInfo", side_effect=observe_construction):
            reg.reload()

        assert observed == ["new", "last"]
        assert [a.agent_id for a in reg.list_agents()] == ["new", "last"]

    @pytest.mark.parametrize(
        "rubric, expected",
        [
            (None, []),
            ([], []),
            (["a", "b"], ["a", "b"]),
            ({"a": 1}, ["a"]),
            ("ab", ["a", "b"]),
            ({"a"}, ["a"]),
        ],
    )
    @pytest.mark.parametrize("evaluators", [None, "judge", ["judge"]])
    def test_reload_preserves_supported_normalization(
        self, tmp_agents_yaml: Path, rubric: Any, expected: list[str], evaluators: Any
    ) -> None:
        reg = AgentRegistry(tmp_agents_yaml)
        tmp_agents_yaml.write_text(
            yaml.safe_dump(
                {
                    "agents": {
                        "new": {
                            "rubric": rubric,
                            "evaluated_by": evaluators,
                            "evaluates_with": evaluators,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        reg.reload()
        info = reg.get_agent("new")
        assert info.rubric == expected
        assert info.evaluated_by == ([] if evaluators is None else ["judge"])
        assert info.evaluates_with == info.evaluated_by
        assert info.status == "planned"
        assert reg.get_active_agents() == []
