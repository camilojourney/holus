"""Tests for GET /api/v1/agents routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import yaml
from fastapi.testclient import TestClient


def _make_agents_yaml(agents: dict) -> str:
    return yaml.dump({"agents": agents})


def _make_trajectory_jsonl(entries: list[dict]) -> str:
    return "\n".join(json.dumps(e) for e in entries)


def _setup(tmp_path, monkeypatch):
    """Create temp files and monkeypatch module-level paths."""
    agents_yaml = tmp_path / "agents" / "AGENTS.yaml"
    agents_yaml.parent.mkdir(parents=True)
    trajectory_jsonl = tmp_path / ".self-improvement" / "memory" / "trajectory.jsonl"
    trajectory_jsonl.parent.mkdir(parents=True)

    import holus.api.routes.agents as agents_mod
    import holus.api.routes.trajectory as traj_mod

    monkeypatch.setattr(agents_mod, "AGENTS_YAML", agents_yaml)
    monkeypatch.setattr(traj_mod, "TRAJECTORY_PATH", trajectory_jsonl)

    return agents_yaml, trajectory_jsonl


def test_list_agents(tmp_path, monkeypatch):
    agents_yaml, trajectory_jsonl = _setup(tmp_path, monkeypatch)

    agents_yaml.write_text(
        _make_agents_yaml(
            {
                "marketing-strategist": {
                    "name": "Marketing Strategist",
                    "model_tier": "strategic",
                    "role": "Strategy decisions",
                },
                "code-improver": {
                    "name": "Code Improver",
                    "model_tier": "operational",
                    "role": "Code quality",
                },
            }
        )
    )
    trajectory_jsonl.write_text("")

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    ids = {a["id"] for a in data}
    assert ids == {"marketing-strategist", "code-improver"}
    # Check model resolution
    strat = next(a for a in data if a["id"] == "marketing-strategist")
    assert strat["model"] == "claude-opus-4-6"
    assert strat["role"] == "Strategy decisions"


def test_list_agents_with_trajectory(tmp_path, monkeypatch):
    agents_yaml, trajectory_jsonl = _setup(tmp_path, monkeypatch)

    agents_yaml.write_text(
        _make_agents_yaml(
            {
                "test-agent": {
                    "name": "Test Agent",
                    "model_tier": "operational",
                    "role": "Testing",
                },
            }
        )
    )
    now = datetime.now(UTC)
    entries = [
        {
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "agent_id": "test-agent",
            "action": "generate",
            "outcome": "success",
        },
        {
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "agent_id": "test-agent",
            "action": "evaluate",
            "outcome": "error",
        },
    ]
    trajectory_jsonl.write_text(_make_trajectory_jsonl(entries))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 200
    data = resp.json()
    agent = data[0]
    assert agent["run_count_7d"] == 2
    assert agent["last_status"] == "success"


def test_get_agent_detail(tmp_path, monkeypatch):
    agents_yaml, trajectory_jsonl = _setup(tmp_path, monkeypatch)

    agents_yaml.write_text(
        _make_agents_yaml(
            {
                "my-agent": {
                    "name": "My Agent",
                    "model_tier": "strategic",
                    "role": "Testing detail",
                },
            }
        )
    )
    now = datetime.now(UTC)
    entries = [
        {
            "timestamp": now.isoformat(),
            "agent_id": "my-agent",
            "action": "generate",
            "outcome": "success",
            "dimension_scores": {"hook_strength": 8.0, "authority_signal": 7.0},
        },
        {
            "timestamp": (now - timedelta(hours=1)).isoformat(),
            "agent_id": "my-agent",
            "action": "evaluate",
            "outcome": "success",
            "dimension_scores": {"hook_strength": 6.0, "authority_signal": 9.0},
        },
    ]
    trajectory_jsonl.write_text(_make_trajectory_jsonl(entries))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/agents/my-agent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "my-agent"
    assert data["name"] == "My Agent"
    assert data["dimension_averages"]["hook_strength"] == 7.0
    assert data["dimension_averages"]["authority_signal"] == 8.0


def test_agent_not_found(tmp_path, monkeypatch):
    agents_yaml, trajectory_jsonl = _setup(tmp_path, monkeypatch)

    agents_yaml.write_text(
        _make_agents_yaml({"existing-agent": {"name": "Exists", "role": "test"}})
    )
    trajectory_jsonl.write_text("")

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/agents/nonexistent")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_agents_yaml_missing(tmp_path, monkeypatch):
    """When AGENTS.yaml does not exist, return 503."""
    import holus.api.routes.agents as agents_mod
    import holus.api.routes.trajectory as traj_mod

    monkeypatch.setattr(agents_mod, "AGENTS_YAML", tmp_path / "missing" / "AGENTS.yaml")
    traj_path = tmp_path / "trajectory.jsonl"
    traj_path.write_text("")
    monkeypatch.setattr(traj_mod, "TRAJECTORY_PATH", traj_path)

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 503
