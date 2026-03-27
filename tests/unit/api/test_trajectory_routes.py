"""Tests for GET /api/v1/trajectory routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _make_entry(
    agent_id: str = "test-agent",
    action: str = "generate",
    outcome: str = "success",
    content_type: str | None = "linkedin_post",
    quality_score: float | None = None,
    cost_usd: float | None = None,
    ts_offset_hours: float = 0,
) -> dict:
    ts = datetime.now(UTC) - timedelta(hours=ts_offset_hours)
    entry: dict = {
        "timestamp": ts.isoformat(),
        "agent_id": agent_id,
        "action": action,
        "outcome": outcome,
    }
    if content_type is not None:
        entry["content_type"] = content_type
    if quality_score is not None:
        entry["quality_score"] = quality_score
    if cost_usd is not None:
        entry["cost_usd"] = cost_usd
    return entry


def _setup(tmp_path, monkeypatch):
    trajectory_jsonl = tmp_path / "trajectory.jsonl"

    import holus.api.routes.trajectory as traj_mod

    monkeypatch.setattr(traj_mod, "TRAJECTORY_PATH", trajectory_jsonl)
    return trajectory_jsonl


def test_list_trajectory_empty(tmp_path, monkeypatch):
    traj = _setup(tmp_path, monkeypatch)
    traj.write_text("")

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trajectory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entries"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["has_more"] is False


def test_list_trajectory_missing_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    # Don't create the file

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trajectory")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_trajectory_with_entries(tmp_path, monkeypatch):
    traj = _setup(tmp_path, monkeypatch)

    entries = [
        _make_entry(agent_id="agent-a", action="generate", ts_offset_hours=1),
        _make_entry(agent_id="agent-b", action="evaluate", ts_offset_hours=2),
        _make_entry(agent_id="agent-a", action="publish", outcome="error", ts_offset_hours=3),
    ]
    traj.write_text("\n".join(json.dumps(e) for e in entries))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trajectory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["entries"]) == 3
    # Newest first
    assert data["entries"][0]["agent_id"] == "agent-a"
    assert data["entries"][0]["action"] == "generate"


def test_trajectory_filtering_by_agent_id(tmp_path, monkeypatch):
    traj = _setup(tmp_path, monkeypatch)

    entries = [
        _make_entry(agent_id="agent-a", ts_offset_hours=1),
        _make_entry(agent_id="agent-b", ts_offset_hours=2),
        _make_entry(agent_id="agent-a", ts_offset_hours=3),
    ]
    traj.write_text("\n".join(json.dumps(e) for e in entries))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trajectory?agent_id=agent-a")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(e["agent_id"] == "agent-a" for e in data["entries"])


def test_trajectory_filtering_by_content_type(tmp_path, monkeypatch):
    traj = _setup(tmp_path, monkeypatch)

    entries = [
        _make_entry(content_type="linkedin_post", ts_offset_hours=1),
        _make_entry(content_type="tutorial", ts_offset_hours=2),
        _make_entry(content_type="linkedin_post", ts_offset_hours=3),
    ]
    traj.write_text("\n".join(json.dumps(e) for e in entries))

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trajectory?content_type=tutorial")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["entries"][0]["content_type"] == "tutorial"


def test_trajectory_filtering_by_date_range(tmp_path, monkeypatch):
    traj = _setup(tmp_path, monkeypatch)

    now = datetime.now(UTC)
    entries = [
        {
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "agent_id": "a",
            "action": "gen",
            "outcome": "success",
        },
        {
            "timestamp": (now - timedelta(days=5)).isoformat(),
            "agent_id": "a",
            "action": "gen",
            "outcome": "success",
        },
        {
            "timestamp": (now - timedelta(days=10)).isoformat(),
            "agent_id": "a",
            "action": "gen",
            "outcome": "success",
        },
    ]
    traj.write_text("\n".join(json.dumps(e) for e in entries))

    from holus.api.app import create_app

    client = TestClient(create_app())
    date_from = (now - timedelta(days=6)).strftime("%Y-%m-%d")
    date_to = (now - timedelta(days=0)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/v1/trajectory?date_from={date_from}&date_to={date_to}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_trajectory_pagination(tmp_path, monkeypatch):
    traj = _setup(tmp_path, monkeypatch)

    entries = [_make_entry(ts_offset_hours=i) for i in range(5)]
    traj.write_text("\n".join(json.dumps(e) for e in entries))

    from holus.api.app import create_app

    client = TestClient(create_app())

    # Page 1, size 2
    resp = client.get("/api/v1/trajectory?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) == 2
    assert data["total"] == 5
    assert data["has_more"] is True

    # Page 3, size 2 — last page with 1 entry
    resp = client.get("/api/v1/trajectory?page=3&page_size=2")
    data = resp.json()
    assert len(data["entries"]) == 1
    assert data["has_more"] is False


def test_trajectory_malformed_lines_skipped(tmp_path, monkeypatch):
    traj = _setup(tmp_path, monkeypatch)

    good_entry = json.dumps(_make_entry())
    traj.write_text(f"{good_entry}\nNOT VALID JSON\n{good_entry}\n")

    from holus.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trajectory")
    assert resp.status_code == 200
    # Only 2 valid entries parsed
    assert resp.json()["total"] == 2
