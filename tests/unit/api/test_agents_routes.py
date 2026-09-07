"""Tests for GET /api/v1/agents routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("7.5", 7.5),
        (6.0, 6.0),
        ("0", 0.0),
        (-1.0, -1.0),
        (None, None),
        ("invalid", None),
        ({}, None),
        ([], None),
        (True, None),
        (float("nan"), None),
        (float("inf"), None),
        (float("-inf"), None),
        ("NaN", None),
        ("Infinity", None),
        ("-Infinity", None),
        (10**400, None),
    ],
)
def test_numeric_resilience_across_routes(legacy_api, value, expected):
    client, path = legacy_api
    now = datetime.now(UTC)
    older = {
        "timestamp": (now - timedelta(minutes=20)).isoformat(),
        "agent_id": "alpha",
        "action": "publish",
        "outcome": "success",
        "quality_score": 6.0,
        "cost_usd": 0.1,
        "dimension_scores": {"hook": 6.0},
    }
    damaged = dict(
        older,
        timestamp=(now - timedelta(minutes=10)).isoformat(),
        outcome="error",
        quality_score=value,
        cost_usd=value,
        dimension_scores={"hook": value},
    )
    newer = dict(
        older,
        timestamp=now.isoformat(),
        quality_score=8.0,
        cost_usd=0.3,
        dimension_scores={"hook": 8.0},
    )
    path.write_text(_make_trajectory_jsonl([older, damaged, newer]))
    responses = {
        route: client.get(f"/api/v1/{route}")
        for route in (
            "trajectory",
            "agents",
            "agents/alpha",
            "agents/alpha/metrics",
            "health",
            "metrics",
        )
    }
    assert {route: response.status_code for route, response in responses.items()} == dict.fromkeys(
        responses, 200
    )
    count = 2 if expected is None else 3
    quality = (14.0 + (expected or 0.0)) / count
    cost = 0.4 + (expected or 0.0)
    detail = responses["agents/alpha"].json()
    assert detail["dimension_averages"] == {"hook": round(quality, 2)}
    assert detail["run_count_7d"] == 3
    assert detail["last_status"] == "success"
    agent_metrics = responses["agents/alpha/metrics"].json()
    assert agent_metrics["total_runs"] == 3
    assert agent_metrics["success_rate"] == pytest.approx(2 / 3)
    assert agent_metrics["avg_quality_score"] == pytest.approx(quality)
    assert agent_metrics["avg_cost_usd"] == pytest.approx(cost / count)
    metrics = responses["metrics"].json()
    assert metrics["avg_quality_score"] == pytest.approx(quality)
    assert metrics["total_cost_usd"] == pytest.approx(cost)
    assert metrics["cost_per_approved_asset"] == pytest.approx(cost / 3)
    assert metrics["active_agents_24h"] == 1
    assert metrics["content_published_7d"] == 2
    assert responses["health"].json()["error_rate_1h"] == pytest.approx(1 / 3)
    # Valid neighbors remain in the projection even if the damaged row cannot parse.
    projected_scores = [row["quality_score"] for row in responses["trajectory"].json()["entries"]]
    assert projected_scores[0] == 8.0
    assert projected_scores[-1] == 6.0
    expected_rows = 3 if expected is not None or value is None or isinstance(value, bool) else 2
    assert responses["trajectory"].json()["total"] == expected_rows


def test_numeric_fields_are_independent(legacy_api):
    client, path = legacy_api
    row = {
        "timestamp": datetime.now(UTC).isoformat(),
        "agent_id": "alpha",
        "quality_score": "bad",
        "cost_usd": "0.1",
        "dimension_scores": {"hook": "bad", "clarity": "8"},
    }
    path.write_text(
        _make_trajectory_jsonl(
            [row, dict(row, quality_score="8", cost_usd="bad", dimension_scores={"hook": "6"})]
        )
    )
    for route in ("agents/alpha/metrics", "metrics"):
        response = client.get(f"/api/v1/{route}")
        assert response.status_code == 200
        metrics = response.json()
        assert metrics["avg_quality_score"] == 8.0
        cost_field = "total_cost_usd" if route == "metrics" else "avg_cost_usd"
        assert metrics[cost_field] == 0.1
    response = client.get("/api/v1/agents/alpha")
    assert response.status_code == 200
    assert response.json()["dimension_averages"] == {"clarity": 8.0, "hook": 6.0}


def test_dimension_window_and_agent_filter_are_unchanged(legacy_api):
    client, path = legacy_api
    now = datetime.now(UTC)
    entries = [
        {
            "agent_id": "alpha",
            "timestamp": (now - timedelta(minutes=i)).isoformat(),
            "dimension_scores": {"hook": "bad" if i == 0 else "8"},
        }
        for i in range(30)
    ]
    entries += [
        dict(
            entries[-1],
            timestamp=(now - timedelta(days=1)).isoformat(),
            dimension_scores={"hook": 100},
        ),
        dict(entries[0], agent_id="other", dimension_scores={"hook": 100}),
    ]
    path.write_text(_make_trajectory_jsonl(list(reversed(entries))))
    response = client.get("/api/v1/agents/alpha")
    assert response.status_code == 200
    assert response.json()["dimension_averages"] == {"hook": 8.0}
