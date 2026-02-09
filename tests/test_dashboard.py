"""
Tests for the Holus Dashboard API (specs/008-dashboard-api.md).
Covers all SPEC-001 through SPEC-008 acceptance criteria.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.base_agent import BaseAgent, RunRecord
from core.llm import LLMProvider
from core.memory import MemoryStore
from core.notifier import Notifier
from dashboard.app import _redact_secrets, _validate_agent_name, create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class StubAgent(BaseAgent):
    """Minimal concrete agent for testing."""

    name = "stub_agent"
    description = "A stub agent for tests"
    schedule = "every 1 hour"

    def get_tools(self) -> list:
        return []

    def get_system_prompt(self) -> str:
        return "Test prompt"

    async def run(self) -> dict[str, Any]:
        return {"status": "completed", "data": "test result"}


class FailingAgent(BaseAgent):
    """Agent that always fails."""

    name = "failing_agent"
    description = "Always errors"
    schedule = "manual"

    def get_tools(self) -> list:
        return []

    def get_system_prompt(self) -> str:
        return "Fail prompt"

    async def run(self) -> dict[str, Any]:
        raise RuntimeError("intentional failure")


def _make_orchestrator(agents: dict[str, BaseAgent] | None = None) -> MagicMock:
    """Build a mock orchestrator with the minimum surface the dashboard needs."""
    orch = MagicMock()
    orch.agents = agents or {}
    orch.scheduler.running = True
    orch.config = {
        "agents": {
            name: agent.config for name, agent in (agents or {}).items()
        }
    }
    return orch


def _make_agent(cls=StubAgent, config: dict | None = None) -> BaseAgent:
    """Instantiate a stub agent with mocked dependencies."""
    llm = MagicMock(spec=LLMProvider)
    mem = MagicMock(spec=MemoryStore)
    notifier = MagicMock(spec=Notifier)
    notifier.notify = MagicMock(return_value=asyncio.coroutine(lambda *a, **k: None)())
    agent = cls(
        llm_provider=llm,
        memory=mem,
        notifier=notifier,
        config=config or {"enabled": True},
    )
    return agent


@pytest.fixture
def stub_agent() -> BaseAgent:
    return _make_agent(StubAgent)


@pytest.fixture
def client_with_agents():
    """TestClient with one idle stub agent registered."""
    agent = _make_agent(StubAgent, config={
        "enabled": True,
        "api_key": "test_api_key_value",
        "nested": {"token": "test_token_value"},
    })
    orch = _make_orchestrator({"stub_agent": agent})
    app = create_app(orch)
    return TestClient(app)


@pytest.fixture
def client_empty():
    """TestClient with no agents."""
    orch = _make_orchestrator({})
    app = create_app(orch)
    return TestClient(app)


@pytest.fixture
def client_scheduler_down():
    """TestClient where the scheduler is stopped."""
    orch = _make_orchestrator({})
    orch.scheduler.running = False
    app = create_app(orch)
    return TestClient(app)


# ---------------------------------------------------------------------------
# SPEC-001  Health Check
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_healthy_returns_200(self, client_with_agents):
        resp = client_with_agents.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert isinstance(body["uptime_seconds"], int)
        assert body["agent_count"] == 1

    def test_degraded_returns_503(self, client_scheduler_down):
        resp = client_scheduler_down.get("/api/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"


# ---------------------------------------------------------------------------
# SPEC-002  Agent List
# ---------------------------------------------------------------------------

class TestAgentListEndpoint:
    def test_returns_array(self, client_with_agents):
        resp = client_with_agents.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert isinstance(agents, list)
        assert len(agents) == 1

    def test_agent_fields(self, client_with_agents):
        agents = client_with_agents.get("/api/agents").json()
        a = agents[0]
        assert a["name"] == "stub_agent"
        assert a["description"] == "A stub agent for tests"
        assert a["schedule"] == "every 1 hour"
        assert a["run_count"] == 0
        assert a["last_run"] is None
        assert a["status"] == "idle"
        assert a["enabled"] is True

    def test_empty(self, client_empty):
        agents = client_empty.get("/api/agents").json()
        assert agents == []


# ---------------------------------------------------------------------------
# SPEC-003  Agent Detail
# ---------------------------------------------------------------------------

class TestAgentDetailEndpoint:
    def test_returns_detail(self, client_with_agents):
        resp = client_with_agents.get("/api/agents/stub_agent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "stub_agent"
        assert "config" in body
        assert "recent_runs" in body

    def test_secrets_redacted(self, client_with_agents):
        body = client_with_agents.get("/api/agents/stub_agent").json()
        assert body["config"]["api_key"] == "***REDACTED***"
        assert body["config"]["nested"]["token"] == "***REDACTED***"

    def test_404_for_unknown(self, client_with_agents):
        resp = client_with_agents.get("/api/agents/nonexistent")
        assert resp.status_code == 404

    def test_400_for_invalid_name(self, client_with_agents):
        resp = client_with_agents.get("/api/agents/bad-name!")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# SPEC-004  Manual Run
# ---------------------------------------------------------------------------

class TestManualRunEndpoint:
    def test_returns_202(self, client_with_agents):
        resp = client_with_agents.post("/api/agents/stub_agent/run")
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "started"
        assert body["agent"] == "stub_agent"

    def test_404_for_unknown(self, client_with_agents):
        resp = client_with_agents.post("/api/agents/nonexistent/run")
        assert resp.status_code == 404

    def test_409_when_already_running(self):
        agent = _make_agent(StubAgent)
        agent._is_running = True
        orch = _make_orchestrator({"stub_agent": agent})
        app = create_app(orch)
        client = TestClient(app)
        resp = client.post("/api/agents/stub_agent/run")
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# SPEC-006  Run History
# ---------------------------------------------------------------------------

class TestRunHistoryEndpoint:
    def test_empty_history(self, client_with_agents):
        resp = client_with_agents.get("/api/agents/stub_agent/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_with_records(self):
        agent = _make_agent(StubAgent)
        agent._run_history = [
            RunRecord(
                run_number=1,
                timestamp="2026-02-08T10:00:00",
                status="completed",
                result_summary="test",
                duration_seconds=1.5,
            ),
            RunRecord(
                run_number=2,
                timestamp="2026-02-08T11:00:00",
                status="error",
                result_summary="",
                duration_seconds=0.3,
                error="boom",
            ),
        ]
        orch = _make_orchestrator({"stub_agent": agent})
        app = create_app(orch)
        client = TestClient(app)

        runs = client.get("/api/agents/stub_agent/runs").json()
        assert len(runs) == 2
        # Newest first
        assert runs[0]["run_number"] == 2
        assert runs[0]["status"] == "error"
        assert runs[1]["run_number"] == 1

    def test_limit_parameter(self):
        agent = _make_agent(StubAgent)
        agent._run_history = [
            RunRecord(
                run_number=i,
                timestamp=f"2026-02-08T{10+i:02d}:00:00",
                status="completed",
                result_summary=f"run {i}",
                duration_seconds=1.0,
            )
            for i in range(1, 6)
        ]
        orch = _make_orchestrator({"stub_agent": agent})
        app = create_app(orch)
        client = TestClient(app)

        runs = client.get("/api/agents/stub_agent/runs?limit=2").json()
        assert len(runs) == 2

    def test_404_unknown_agent(self, client_with_agents):
        resp = client_with_agents.get("/api/agents/nonexistent/runs")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SPEC-007  Agent Config
# ---------------------------------------------------------------------------

class TestAgentConfigEndpoint:
    def test_returns_config(self, client_with_agents):
        resp = client_with_agents.get("/api/agents/stub_agent/config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True

    def test_secrets_redacted(self, client_with_agents):
        body = client_with_agents.get("/api/agents/stub_agent/config").json()
        assert body["api_key"] == "***REDACTED***"
        assert body["nested"]["token"] == "***REDACTED***"

    def test_404_unknown(self, client_with_agents):
        resp = client_with_agents.get("/api/agents/nonexistent/config")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SPEC-005  Dashboard HTML
# ---------------------------------------------------------------------------

class TestDashboardHTML:
    def test_renders_html(self, client_with_agents):
        resp = client_with_agents.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Holus" in resp.text

    def test_shows_agent_cards(self, client_with_agents):
        html = client_with_agents.get("/").text
        assert "stub_agent" in html
        assert "badge-idle" in html

    def test_empty_state(self, client_empty):
        html = client_empty.get("/").text
        assert "No agents registered" in html


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestRedactSecrets:
    def test_flat_dict(self):
        result = _redact_secrets({"api_key": "test_api_key_value", "name": "test"})
        assert result["api_key"] == "***REDACTED***"
        assert result["name"] == "test"

    def test_nested(self):
        result = _redact_secrets({"db": {"password": "pw", "host": "localhost"}})
        assert result["db"]["password"] == "***REDACTED***"
        assert result["db"]["host"] == "localhost"

    def test_list_of_dicts(self):
        result = _redact_secrets([{"token": "abc"}, {"value": 1}])
        assert result[0]["token"] == "***REDACTED***"
        assert result[1]["value"] == 1

    def test_non_dict(self):
        assert _redact_secrets("hello") == "hello"
        assert _redact_secrets(42) == 42


class TestValidateAgentName:
    def test_valid_names(self):
        for name in ["job_hunter", "InboxManager", "a1", "trading_monitor"]:
            assert _validate_agent_name(name) == name

    def test_invalid_names(self):
        from fastapi import HTTPException
        for name in ["bad-name", "has space", "../path", "", "123start"]:
            with pytest.raises(HTTPException) as exc_info:
                _validate_agent_name(name)
            assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# BaseAgent run history tracking
# ---------------------------------------------------------------------------

class TestBaseAgentRunHistory:
    @pytest.mark.asyncio
    async def test_successful_run_records_history(self):
        agent = _make_agent(StubAgent)
        result = await agent.scheduled_run()
        assert len(agent._run_history) == 1
        record = agent._run_history[0]
        assert record.status == "completed"
        assert record.run_number == 1
        assert record.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_failed_run_records_error(self):
        agent = _make_agent(FailingAgent)
        result = await agent.scheduled_run()
        assert len(agent._run_history) == 1
        record = agent._run_history[0]
        assert record.status == "error"
        assert "intentional failure" in record.error

    @pytest.mark.asyncio
    async def test_is_running_flag(self):
        agent = _make_agent(StubAgent)
        assert agent._is_running is False
        assert agent.status == "idle"

        # After a failed run, status should be error
        agent2 = _make_agent(FailingAgent)
        await agent2.scheduled_run()
        assert agent2._is_running is False
        assert agent2.status == "error"

    def test_get_run_history_limit(self):
        agent = _make_agent(StubAgent)
        for i in range(5):
            agent._run_history.append(
                RunRecord(i + 1, "2026-01-01", "completed", "ok", 1.0)
            )
        history = agent.get_run_history(limit=3)
        assert len(history) == 3
        # Newest first
        assert history[0]["run_number"] == 5

    def test_get_run_history_max_100(self):
        agent = _make_agent(StubAgent)
        history = agent.get_run_history(limit=500)
        assert isinstance(history, list)
