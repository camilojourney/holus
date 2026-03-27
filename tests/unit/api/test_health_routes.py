"""Tests for GET /api/v1/health and /api/v1/metrics routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import yaml
from fastapi.testclient import TestClient


def _setup(tmp_path, monkeypatch):
    """Create temp directory structure and monkeypatch all path constants."""
    trajectory_jsonl = tmp_path / "trajectory.jsonl"
    eval_history = tmp_path / "eval_history.jsonl"
    agents_yaml = tmp_path / "AGENTS.yaml"
    guardrails_yaml = tmp_path / "guardrails.yaml"
    content_queue_dir = tmp_path / "content-queue"

    import holus.api.routes.evaluations as eval_mod
    import holus.api.routes.health as health_mod
    import holus.api.routes.trajectory as traj_mod

    monkeypatch.setattr(traj_mod, "TRAJECTORY_PATH", trajectory_jsonl)
    monkeypatch.setattr(health_mod, "TRAJECTORY_PATH", trajectory_jsonl)
    monkeypatch.setattr(eval_mod, "EVAL_HISTORY_PATH", eval_history)
    monkeypatch.setattr(health_mod, "EVAL_HISTORY_PATH", eval_history)
    monkeypatch.setattr(health_mod, "AGENTS_YAML", agents_yaml)
    monkeypatch.setattr(health_mod, "GUARDRAILS_YAML", guardrails_yaml)
    monkeypatch.setattr(health_mod, "CONTENT_QUEUE_DIR", content_queue_dir)

    return {
        "trajectory": trajectory_jsonl,
        "eval_history": eval_history,
        "agents_yaml": agents_yaml,
        "guardrails": guardrails_yaml,
        "content_queue": content_queue_dir,
    }


def test_health_endpoint_all_missing(tmp_path, monkeypatch):
    """When no files exist, health reports everything missing."""
    _setup(tmp_path, monkeypatch)

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["kill_switch_active"] is False
    assert data["trajectory_file_exists"] is False
    assert data["eval_history_file_exists"] is False
    assert data["agents_yaml_exists"] is False
    assert data["content_queue_count"] == 0
    assert data["error_rate_1h"] is None


def test_health_endpoint_all_present(tmp_path, monkeypatch):
    """When all files exist, health reports them present."""
    paths = _setup(tmp_path, monkeypatch)

    paths["trajectory"].write_text("")
    paths["eval_history"].write_text("")
    paths["agents_yaml"].write_text(yaml.dump({"agents": {}}))
    paths["guardrails"].write_text(yaml.dump({"kill_switch": {"active": False}}))
    paths["content_queue"].mkdir()
    (paths["content_queue"] / "post1.yaml").write_text("title: test")
    (paths["content_queue"] / "post2.yaml").write_text("title: test2")

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trajectory_file_exists"] is True
    assert data["eval_history_file_exists"] is True
    assert data["agents_yaml_exists"] is True
    assert data["content_queue_count"] == 2
    assert data["kill_switch_active"] is False


def test_health_kill_switch_active(tmp_path, monkeypatch):
    paths = _setup(tmp_path, monkeypatch)

    paths["trajectory"].write_text("")
    paths["eval_history"].write_text("")
    paths["agents_yaml"].write_text(yaml.dump({"agents": {}}))
    paths["guardrails"].write_text(yaml.dump({"kill_switch": {"active": True}}))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["kill_switch_active"] is True


def test_health_error_rate(tmp_path, monkeypatch):
    """Error rate is computed from recent trajectory entries."""
    paths = _setup(tmp_path, monkeypatch)

    now = datetime.now(UTC)
    entries = [
        {
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "agent_id": "a",
            "action": "gen",
            "outcome": "success",
        },
        {
            "timestamp": (now - timedelta(minutes=20)).isoformat(),
            "agent_id": "a",
            "action": "gen",
            "outcome": "error",
        },
        {
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
            "agent_id": "b",
            "action": "gen",
            "outcome": "error",
        },
        # Old entry — outside 1h window
        {
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "agent_id": "b",
            "action": "gen",
            "outcome": "error",
        },
    ]
    paths["trajectory"].write_text("\n".join(json.dumps(e) for e in entries))
    paths["eval_history"].write_text("")
    paths["agents_yaml"].write_text(yaml.dump({"agents": {}}))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    data = resp.json()
    # 3 entries in last hour, 2 errors -> 2/3
    assert data["error_rate_1h"] is not None
    assert abs(data["error_rate_1h"] - 2 / 3) < 0.01


def test_metrics_endpoint_empty(tmp_path, monkeypatch):
    """Metrics with no trajectory data."""
    paths = _setup(tmp_path, monkeypatch)
    paths["trajectory"].write_text("")

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cycles"] == 0
    assert data["success_rate"] == 0.0
    assert data["avg_quality_score"] is None
    assert data["total_cost_usd"] is None
    assert data["active_agents_24h"] == 0
    assert data["content_published_7d"] == 0


def test_metrics_endpoint_with_data(tmp_path, monkeypatch):
    """Metrics aggregates trajectory data correctly."""
    paths = _setup(tmp_path, monkeypatch)

    now = datetime.now(UTC)
    entries = [
        {
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "agent_id": "agent-a",
            "action": "generate",
            "outcome": "success",
            "quality_score": 8.0,
            "cost_usd": 0.05,
        },
        {
            "timestamp": (now - timedelta(hours=5)).isoformat(),
            "agent_id": "agent-b",
            "action": "publish",
            "outcome": "success",
            "quality_score": 7.0,
            "cost_usd": 0.03,
        },
        {
            "timestamp": (now - timedelta(hours=1)).isoformat(),
            "agent_id": "agent-a",
            "action": "evaluate",
            "outcome": "error",
            "cost_usd": 0.02,
        },
    ]
    paths["trajectory"].write_text("\n".join(json.dumps(e) for e in entries))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cycles"] == 3
    assert abs(data["success_rate"] - 2 / 3) < 0.01
    assert data["avg_quality_score"] == 7.5
    assert abs(data["total_cost_usd"] - 0.10) < 0.001
    assert data["active_agents_24h"] == 2
    assert data["content_published_7d"] == 1
