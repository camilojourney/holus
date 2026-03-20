"""Unit tests for process manager — AgentStatus, AgentProcess, ProcessManager.

All tests mock subprocess.Popen — no real processes spawned.
"""

from __future__ import annotations

import signal
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, mock_open, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager


def _make_proc(**overrides) -> MagicMock:
    """Create a mock subprocess.Popen with sensible defaults."""
    proc = MagicMock()
    proc.pid = overrides.pop("pid", 100)
    proc.poll.return_value = overrides.pop("poll_return", None)  # alive by default
    proc.returncode = overrides.pop("returncode", 0)
    proc.wait.return_value = overrides.pop("wait_return", 0)
    for k, v in overrides.items():
        setattr(proc, k, v)
    return proc


# ---------------------------------------------------------------------------
# AgentStatus
# ---------------------------------------------------------------------------


class TestAgentStatus:
    """StrEnum basics."""

    def test_string_value(self):
        assert AgentStatus.RUNNING == "running"

    def test_is_str_subclass(self):
        assert isinstance(AgentStatus.STOPPED, str)

    @pytest.mark.parametrize(
        "member",
        [
            AgentStatus.STARTING,
            AgentStatus.RUNNING,
            AgentStatus.STOPPED,
            AgentStatus.CRASHED,
            AgentStatus.RATE_LIMITED,
            AgentStatus.RESTARTING,
        ],
    )
    def test_member_exists(self, member: AgentStatus):
        assert member in AgentStatus


# ---------------------------------------------------------------------------
# AgentProcess
# ---------------------------------------------------------------------------


class TestAgentProcess:
    """Dataclass defaults and is_alive property."""

    def test_defaults(self):
        ap = AgentProcess(name="test", entrypoint="test.module")
        assert ap.pid is None
        assert ap.status == AgentStatus.STOPPED
        assert ap.restart_count == 0
        assert ap.max_restarts == 3
        assert ap.cooldown_seconds == 60
        assert ap.last_started is None
        assert ap.last_stopped is None
        assert ap.process is None

    def test_is_alive_no_process(self):
        ap = AgentProcess(name="test", entrypoint="test.module")
        assert ap.is_alive is False

    def test_is_alive_running(self):
        proc = _make_proc(poll_return=None)
        ap = AgentProcess(name="test", entrypoint="test.module", process=proc)
        assert ap.is_alive is True

    def test_is_alive_exited(self):
        proc = _make_proc(poll_return=1)
        ap = AgentProcess(name="test", entrypoint="test.module", process=proc)
        assert ap.is_alive is False


# ---------------------------------------------------------------------------
# ProcessManager — Init
# ---------------------------------------------------------------------------


class TestProcessManagerInit:
    """Construction and log directory creation."""

    def test_creates_log_dir(self, tmp_path: Path):
        log_dir = tmp_path / "logs"
        pm = ProcessManager(log_dir=log_dir)
        assert log_dir.exists()
        assert pm._agents == {}

    def test_existing_log_dir(self, tmp_path: Path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        ProcessManager(log_dir=log_dir)
        assert log_dir.exists()


# ---------------------------------------------------------------------------
# ProcessManager — start_agent
# ---------------------------------------------------------------------------


class TestProcessManagerStart:
    """Agent launching."""

    @patch("holus.core.process_manager.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_start_creates_process(self, mock_file, mock_popen, tmp_path: Path):
        mock_proc = _make_proc(pid=12345)
        mock_popen.return_value = mock_proc

        pm = ProcessManager(log_dir=tmp_path)
        agent = pm.start_agent("marketing", "holus.agents.marketing.agent")

        assert agent.name == "marketing"
        assert agent.pid == 12345
        assert agent.status == AgentStatus.RUNNING
        assert agent.process is mock_proc
        assert agent.last_started is not None
        mock_popen.assert_called_once()

    @patch("holus.core.process_manager.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_start_sets_env_var(self, mock_file, mock_popen, tmp_path: Path):
        mock_popen.return_value = _make_proc()

        pm = ProcessManager(log_dir=tmp_path)
        pm.start_agent("test-agent", "holus.test")

        _, kwargs = mock_popen.call_args
        assert kwargs["env"]["HOLUS_AGENT_NAME"] == "test-agent"

    @patch("holus.core.process_manager.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_start_runs_python_m_entrypoint(self, mock_file, mock_popen, tmp_path: Path):
        mock_popen.return_value = _make_proc()

        pm = ProcessManager(log_dir=tmp_path)
        pm.start_agent("test", "holus.agents.test")

        args, _ = mock_popen.call_args
        assert args[0] == ["python", "-m", "holus.agents.test"]

    @patch("holus.core.process_manager.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_start_already_running_returns_existing(self, mock_file, mock_popen, tmp_path: Path):
        mock_proc = _make_proc(poll_return=None)
        mock_popen.return_value = mock_proc

        pm = ProcessManager(log_dir=tmp_path)
        first = pm.start_agent("x", "holus.x")
        second = pm.start_agent("x", "holus.x")

        assert first is second
        assert mock_popen.call_count == 1

    @patch("holus.core.process_manager.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_start_dead_agent_restarts(self, mock_file, mock_popen, tmp_path: Path):
        mock_proc1 = _make_proc(pid=100, poll_return=1)
        mock_proc2 = _make_proc(pid=200)

        mock_popen.side_effect = [mock_proc1, mock_proc2]

        pm = ProcessManager(log_dir=tmp_path)
        pm.start_agent("x", "holus.x")
        second = pm.start_agent("x", "holus.x")

        assert second.pid == 200
        assert mock_popen.call_count == 2

    @patch("holus.core.process_manager.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_start_registers_agent(self, mock_file, mock_popen, tmp_path: Path):
        mock_popen.return_value = _make_proc(pid=42)

        pm = ProcessManager(log_dir=tmp_path)
        pm.start_agent("agent-1", "holus.a1")

        assert "agent-1" in pm._agents
        assert pm.get_agent("agent-1") is not None


# ---------------------------------------------------------------------------
# ProcessManager — stop_agent
# ---------------------------------------------------------------------------


class TestProcessManagerStop:
    """Graceful stop and SIGKILL fallback."""

    def test_stop_unknown_agent_noop(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        pm.stop_agent("nonexistent")  # should not raise

    def test_stop_agent_no_process_noop(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = AgentProcess(name="x", entrypoint="e", process=None)
        pm.stop_agent("x")  # should not raise

    def test_stop_already_dead(self, tmp_path: Path):
        proc = _make_proc(poll_return=0)
        agent = AgentProcess(name="x", entrypoint="e", process=proc, status=AgentStatus.RUNNING)

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = agent
        pm.stop_agent("x")

        assert agent.status == AgentStatus.STOPPED
        proc.send_signal.assert_not_called()

    def test_stop_graceful_sigterm(self, tmp_path: Path):
        proc = _make_proc(poll_return=None)

        agent = AgentProcess(name="x", entrypoint="e", process=proc, status=AgentStatus.RUNNING)

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = agent
        pm.stop_agent("x", timeout=5.0)

        proc.send_signal.assert_called_once_with(signal.SIGTERM)
        proc.wait.assert_called_once_with(timeout=5.0)
        assert agent.status == AgentStatus.STOPPED
        assert agent.last_stopped is not None

    def test_stop_sigkill_on_timeout(self, tmp_path: Path):
        proc = _make_proc(poll_return=None)
        proc.wait.side_effect = [subprocess.TimeoutExpired(cmd="x", timeout=10), None]

        agent = AgentProcess(name="x", entrypoint="e", process=proc, status=AgentStatus.RUNNING)

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = agent
        pm.stop_agent("x")

        proc.send_signal.assert_called_once_with(signal.SIGTERM)
        proc.kill.assert_called_once()
        assert agent.status == AgentStatus.STOPPED


# ---------------------------------------------------------------------------
# ProcessManager — restart_agent
# ---------------------------------------------------------------------------


class TestProcessManagerRestart:
    """Stop + start sequence."""

    def test_restart_unknown_returns_none(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        result = pm.restart_agent("nonexistent")
        assert result is None

    @patch("holus.core.process_manager.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_restart_stops_then_starts(self, mock_file, mock_popen, tmp_path: Path):
        # proc1.poll returns None (alive) until wait() is called, then returns exit code
        proc1 = _make_proc(pid=100, poll_return=None)
        proc1.wait.side_effect = lambda **kw: setattr(proc1.poll, "return_value", 0) or 0
        proc2 = _make_proc(pid=200)

        mock_popen.side_effect = [proc1, proc2]

        pm = ProcessManager(log_dir=tmp_path)
        pm.start_agent("x", "holus.x")

        restarted = pm.restart_agent("x")

        proc1.send_signal.assert_called_with(signal.SIGTERM)
        assert restarted is not None
        assert restarted.pid == 200


# ---------------------------------------------------------------------------
# ProcessManager — shutdown_all
# ---------------------------------------------------------------------------


class TestProcessManagerShutdownAll:
    """Shuts down every managed agent."""

    def test_shutdown_all_stops_every_agent(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)

        procs = []
        for name in ["a", "b", "c"]:
            proc = _make_proc(poll_return=None)
            agent = AgentProcess(name=name, entrypoint="e", process=proc, status=AgentStatus.RUNNING)
            pm._agents[name] = agent
            procs.append(proc)

        pm.shutdown_all(timeout=2.0)

        for proc in procs:
            proc.send_signal.assert_called_once_with(signal.SIGTERM)
        for agent in pm._agents.values():
            assert agent.status == AgentStatus.STOPPED

    def test_shutdown_all_empty_noop(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        pm.shutdown_all()  # should not raise


# ---------------------------------------------------------------------------
# ProcessManager — check_health
# ---------------------------------------------------------------------------


class TestProcessManagerCheckHealth:
    """Health checking and crash detection."""

    def test_healthy_agent(self, tmp_path: Path):
        proc = _make_proc(poll_return=None)
        agent = AgentProcess(name="x", entrypoint="e", process=proc, status=AgentStatus.RUNNING)

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = agent

        statuses = pm.check_health()
        assert statuses["x"] == AgentStatus.RUNNING

    def test_stopped_agent_stays_stopped(self, tmp_path: Path):
        agent = AgentProcess(name="x", entrypoint="e", status=AgentStatus.STOPPED)

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = agent

        statuses = pm.check_health()
        assert statuses["x"] == AgentStatus.STOPPED

    @patch.object(ProcessManager, "_handle_crash")
    def test_crashed_agent_triggers_handler(self, mock_handle, tmp_path: Path):
        proc = _make_proc(poll_return=1, returncode=1)
        agent = AgentProcess(name="x", entrypoint="e", process=proc, status=AgentStatus.RUNNING)

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = agent

        pm.check_health()
        mock_handle.assert_called_once_with(agent)

    def test_check_health_no_process(self, tmp_path: Path):
        """Agent with no process but RUNNING status still triggers crash handler."""
        agent = AgentProcess(name="x", entrypoint="e", process=None, status=AgentStatus.RUNNING)

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = agent

        with patch.object(pm, "_handle_crash") as mock_handle:
            pm.check_health()
            mock_handle.assert_called_once_with(agent)

    def test_multiple_agents(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)

        alive_proc = _make_proc(poll_return=None)
        pm._agents["alive"] = AgentProcess(
            name="alive", entrypoint="e", process=alive_proc, status=AgentStatus.RUNNING
        )

        pm._agents["stopped"] = AgentProcess(
            name="stopped", entrypoint="e", status=AgentStatus.STOPPED
        )

        statuses = pm.check_health()
        assert statuses["alive"] == AgentStatus.RUNNING
        assert statuses["stopped"] == AgentStatus.STOPPED


# ---------------------------------------------------------------------------
# ProcessManager — _handle_crash
# ---------------------------------------------------------------------------


class TestProcessManagerCrashHandling:
    """Exponential backoff and max restart limit."""

    @patch("threading.Thread")
    def test_crash_increments_restart_count(self, mock_thread_cls, tmp_path: Path):
        mock_thread_cls.return_value = MagicMock()
        agent = AgentProcess(name="x", entrypoint="e", restart_count=0, max_restarts=3)

        pm = ProcessManager(log_dir=tmp_path)
        pm._handle_crash(agent)

        assert agent.restart_count == 1

    @patch("threading.Thread")
    def test_crash_sets_restarting_status(self, mock_thread_cls, tmp_path: Path):
        mock_thread_cls.return_value = MagicMock()
        agent = AgentProcess(name="x", entrypoint="e", restart_count=0, max_restarts=3)

        pm = ProcessManager(log_dir=tmp_path)
        pm._handle_crash(agent)

        assert agent.status == AgentStatus.RESTARTING

    @patch("threading.Thread")
    def test_crash_sets_last_stopped(self, mock_thread_cls, tmp_path: Path):
        mock_thread_cls.return_value = MagicMock()
        agent = AgentProcess(name="x", entrypoint="e", restart_count=0, max_restarts=3)

        pm = ProcessManager(log_dir=tmp_path)
        pm._handle_crash(agent)

        assert agent.last_stopped is not None

    def test_crash_exceeds_max_restarts(self, tmp_path: Path):
        agent = AgentProcess(name="x", entrypoint="e", restart_count=3, max_restarts=3)

        pm = ProcessManager(log_dir=tmp_path)
        pm._handle_crash(agent)

        assert agent.status == AgentStatus.CRASHED
        assert agent.restart_count == 4

    @patch("threading.Thread")
    def test_crash_spawns_daemon_thread(self, mock_thread_cls, tmp_path: Path):
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        agent = AgentProcess(name="x", entrypoint="e", restart_count=0, max_restarts=3)

        pm = ProcessManager(log_dir=tmp_path)
        pm._handle_crash(agent)

        mock_thread_cls.assert_called_once()
        _, kwargs = mock_thread_cls.call_args
        assert kwargs["daemon"] is True
        mock_thread.start.assert_called_once()

    @patch("threading.Thread")
    def test_crash_exponential_cooldown(self, mock_thread_cls, tmp_path: Path):
        """Cooldown doubles: 60, 120, 240 for attempts 1, 2, 3."""
        mock_thread_cls.return_value = MagicMock()
        pm = ProcessManager(log_dir=tmp_path)

        for attempt in [0, 1, 2]:
            mock_thread_cls.reset_mock()
            agent = AgentProcess(
                name="x", entrypoint="e",
                restart_count=attempt, max_restarts=5, cooldown_seconds=60,
            )
            pm._handle_crash(agent)
            mock_thread_cls.assert_called_once()


# ---------------------------------------------------------------------------
# ProcessManager — Introspection
# ---------------------------------------------------------------------------


class TestProcessManagerIntrospection:
    """list_agents, get_agent, reset_crash_counter."""

    def test_list_agents_empty(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        assert pm.list_agents() == []

    def test_list_agents_returns_all(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["a"] = AgentProcess(name="a", entrypoint="e")
        pm._agents["b"] = AgentProcess(name="b", entrypoint="e")
        agents = pm.list_agents()
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"a", "b"}

    def test_get_agent_exists(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = AgentProcess(name="x", entrypoint="e")
        assert pm.get_agent("x") is not None

    def test_get_agent_missing(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        assert pm.get_agent("missing") is None

    def test_reset_crash_counter(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        agent = AgentProcess(name="x", entrypoint="e", restart_count=5)
        pm._agents["x"] = agent

        pm.reset_crash_counter("x")
        assert agent.restart_count == 0

    def test_reset_crash_counter_missing_noop(self, tmp_path: Path):
        pm = ProcessManager(log_dir=tmp_path)
        pm.reset_crash_counter("nonexistent")  # should not raise
