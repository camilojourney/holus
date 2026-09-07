"""Isolated legacy Observatory routes, with no application lifespan or runtime data."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def legacy_api(tmp_path, monkeypatch):
    from holus.api.routes import agents, health, trajectory

    path = tmp_path / "trajectory.jsonl"
    monkeypatch.setattr(trajectory, "TRAJECTORY_PATH", path)
    monkeypatch.setattr(health, "TRAJECTORY_PATH", path)
    for name in (
        "EVAL_HISTORY_PATH",
        "AGENTS_YAML",
        "GUARDRAILS_YAML",
        "CONTENT_QUEUE_DIR",
        "LINEAGE_DIR",
    ):
        monkeypatch.setattr(health, name, tmp_path / name)
    monkeypatch.setattr(agents, "_load_agents_yaml", lambda: {"alpha": {"role": "test"}})

    app = FastAPI()
    for module in (trajectory, agents, health):
        app.include_router(module.router, prefix="/api/v1")
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, path
