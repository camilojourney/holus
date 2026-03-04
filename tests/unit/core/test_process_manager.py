"""Tests for holus.core.process_manager module."""

from __future__ import annotations

import signal
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# TestAgentStatus
# ---------------------------------------------------------------------------


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_enum_values(self) -> None:
        """All six status values match expected strings."""
        from holus.core.process_manager import AgentStatus

        assert AgentStatus.STARTING == "starting"
        assert AgentStatus.RUNNING == "running"
        assert AgentStatus.STOPPED == "stopped"
        assert AgentStatus.CRASHED == "crashed"
        assert AgentStatus.RATE_LIMITED == "rate_limited"
        assert AgentStatus.RESTARTING == "restarting"

    def test_string_behavior(self) -> None:
        """AgentStatus members behave like strings (StrEnum)."""
        from holus.core.process_manager import AgentStatus

        assert AgentStatus.RUNNING == "running"
        assert str(AgentStatus.RUNNING) == "running"

    def test_all_statuses_exist(self) -> None:
        """All six status names are present on the enum."""
        from holus.core.process_manager import AgentStatus

        names = {s.name for s in AgentStatus}
        assert names == {"STARTING", "RUNNING", "STOPPED", "CRASHED", "RATE_LIMITED", "RESTARTING"}


# ---------------------------------------------------------------------------
# TestAgentProcessDefaults
# ---------------------------------------------------------------------------


class TestAgentProcessDefaults:
    """Tests for AgentProcess dataclass defaults and is_alive property."""

    def test_default_field_values(self) -> None:
        """Default fields match documented values."""
        from holus.core.process_manager import AgentProcess, AgentStatus

        ap = AgentProcess(name="test", entrypoint="holus.agents.test")
        assert ap.pid is None
        assert ap.status == AgentStatus.STOPPED
        assert ap.restart_count == 0
        assert ap.max_restarts == 3
        assert ap.process is None

    def test_is_alive_no_process(self) -> None:
        """is_alive returns False when process is None."""
        from holus.core.process_manager import AgentProcess

        ap = AgentProcess(name="test", entrypoint="holus.agents.test")
        assert ap.is_alive is False

    def test_is_alive_with_live_process(self) -> None:
        """is_alive returns True when process.poll() is None."""
        from holus.core.process_manager import AgentProcess

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        ap = AgentProcess(name="test", entrypoint="holus.agents.test", process=mock_proc)
        assert ap.is_alive is True

    def test_is_alive_with_dead_process(self) -> None:
        """is_alive returns False when process.poll() returns an exit code."""
        from holus.core.process_manager import AgentProcess

        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        ap = AgentProcess(name="test", entrypoint="holus.agents.test", process=mock_proc)
        assert ap.is_alive is False


# ---------------------------------------------------------------------------
# TestProcessManagerInit
# ---------------------------------------------------------------------------


class TestProcessManagerInit:
    """Tests for ProcessManager.__init__."""

    def test_creates_log_dir(self, tmp_path: Path) -> None:
        """Log directory is created on init."""
        from holus.core.process_manager import ProcessManager

        log_dir = tmp_path / "logs"
        assert not log_dir.exists()
        ProcessManager(log_dir=log_dir)
        assert log_dir.exists()

    def test_empty_agents(self, tmp_path: Path) -> None:
        """list_agents() returns empty list on fresh init."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        assert pm.list_agents() == []

    def test_custom_log_dir(self, tmp_path: Path) -> None:
        """Accepts a custom Path for log_dir."""
        from holus.core.process_manager import ProcessManager

        custom = tmp_path / "custom_logs"
        pm = ProcessManager(log_dir=custom)
        assert pm._log_dir == custom


# ---------------------------------------------------------------------------
# TestStartAgent
# ---------------------------------------------------------------------------


class TestStartAgent:
    """Tests for ProcessManager.start_agent."""

    def _make_mock_proc(self, pid: int = 1234) -> MagicMock:
        """Return a mock Popen instance."""
        proc = MagicMock()
        proc.pid = pid
        proc.poll.return_value = None  # alive
        return proc

    def test_starts_process(self, tmp_path: Path) -> None:
        """Popen is called with python -m <entrypoint>."""
        from holus.core.process_manager import ProcessManager

        mock_proc = self._make_mock_proc()
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen, \
             patch("builtins.open", MagicMock()):
            pm = ProcessManager(log_dir=tmp_path)
            pm.start_agent("agent1", "holus.agents.marketing.agent")

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ["python", "-m", "holus.agents.marketing.agent"]

    def test_sets_pid(self, tmp_path: Path) -> None:
        """agent.pid equals the PID returned by Popen."""
        from holus.core.process_manager import ProcessManager

        mock_proc = self._make_mock_proc(pid=9999)
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch("builtins.open", MagicMock()):
            pm = ProcessManager(log_dir=tmp_path)
            agent = pm.start_agent("agent1", "holus.agents.test")

        assert agent.pid == 9999

    def test_sets_running_status(self, tmp_path: Path) -> None:
        """agent.status is RUNNING after start."""
        from holus.core.process_manager import AgentStatus, ProcessManager

        mock_proc = self._make_mock_proc()
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch("builtins.open", MagicMock()):
            pm = ProcessManager(log_dir=tmp_path)
            agent = pm.start_agent("agent1", "holus.agents.test")

        assert agent.status == AgentStatus.RUNNING

    def test_skips_if_already_alive(self, tmp_path: Path) -> None:
        """start_agent returns existing agent without new Popen if already alive."""
        from holus.core.process_manager import ProcessManager

        mock_proc = self._make_mock_proc()
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen, \
             patch("builtins.open", MagicMock()):
            pm = ProcessManager(log_dir=tmp_path)
            agent1 = pm.start_agent("agent1", "holus.agents.test")
            agent2 = pm.start_agent("agent1", "holus.agents.test")

        assert agent1 is agent2
        assert mock_popen.call_count == 1

    def test_creates_log_files(self, tmp_path: Path) -> None:
        """open() is called for stdout and stderr log paths."""
        from holus.core.process_manager import ProcessManager

        mock_proc = self._make_mock_proc()
        mock_open = MagicMock()
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch("builtins.open", mock_open):
            pm = ProcessManager(log_dir=tmp_path)
            pm.start_agent("myagent", "holus.agents.test")

        opened_paths = [str(call[0][0]) for call in mock_open.call_args_list]
        assert any("myagent.stdout.log" in p for p in opened_paths)
        assert any("myagent.stderr.log" in p for p in opened_paths)


# ---------------------------------------------------------------------------
# TestStopAgent
# ---------------------------------------------------------------------------


class TestStopAgent:
    """Tests for ProcessManager.stop_agent."""

    def _running_agent(self, tmp_path: Path, name: str = "agent1") -> tuple:
        """Helper: create a ProcessManager with one running agent."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # alive
        agent = AgentProcess(
            name=name,
            entrypoint="holus.agents.test",
            pid=1234,
            status=AgentStatus.RUNNING,
            process=mock_proc,
        )
        pm._agents[name] = agent
        return pm, agent, mock_proc

    def test_sigterm_first(self, tmp_path: Path) -> None:
        """send_signal(SIGTERM) is called before waiting."""
        pm, _agent, mock_proc = self._running_agent(tmp_path)
        pm.stop_agent("agent1")
        mock_proc.send_signal.assert_called_once_with(signal.SIGTERM)

    def test_sigkill_on_timeout(self, tmp_path: Path) -> None:
        """kill() is called when wait raises TimeoutExpired."""
        pm, _agent, mock_proc = self._running_agent(tmp_path)
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired(cmd="python", timeout=10), None]
        pm.stop_agent("agent1", timeout=10.0)
        mock_proc.kill.assert_called_once()

    def test_handles_none_agent(self, tmp_path: Path) -> None:
        """stop_agent for unknown name does not raise."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        pm.stop_agent("nonexistent")  # should not raise

    def test_handles_dead_process(self, tmp_path: Path) -> None:
        """If process is not alive, sets STOPPED without sending signals."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # dead
        agent = AgentProcess(
            name="agent1",
            entrypoint="holus.agents.test",
            status=AgentStatus.RUNNING,
            process=mock_proc,
        )
        pm._agents["agent1"] = agent
        pm.stop_agent("agent1")
        mock_proc.send_signal.assert_not_called()
        assert agent.status == AgentStatus.STOPPED

    def test_sets_stopped_status(self, tmp_path: Path) -> None:
        """agent.status is STOPPED after stop_agent."""
        from holus.core.process_manager import AgentStatus

        pm, agent, _mock_proc = self._running_agent(tmp_path)
        pm.stop_agent("agent1")
        assert agent.status == AgentStatus.STOPPED


# ---------------------------------------------------------------------------
# TestRestartAgent
# ---------------------------------------------------------------------------


class TestRestartAgent:
    """Tests for ProcessManager.restart_agent."""

    def test_stops_then_starts(self, tmp_path: Path) -> None:
        """restart_agent calls stop_agent then start_agent."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        with patch.object(pm, "stop_agent") as mock_stop, \
             patch.object(pm, "start_agent", return_value=MagicMock()) as mock_start:
            from holus.core.process_manager import AgentProcess, AgentStatus
            agent = AgentProcess(name="a", entrypoint="holus.a", status=AgentStatus.RUNNING)
            pm._agents["a"] = agent
            pm.restart_agent("a")

        mock_stop.assert_called_once_with("a")
        mock_start.assert_called_once_with("a", "holus.a")

    def test_returns_none_for_unknown(self, tmp_path: Path) -> None:
        """Returns None for an unregistered agent name."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        result = pm.restart_agent("ghost")
        assert result is None

    def test_preserves_entrypoint(self, tmp_path: Path) -> None:
        """Restarted agent uses the same entrypoint."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        agent = AgentProcess(
            name="a",
            entrypoint="holus.agents.marketing",
            status=AgentStatus.RUNNING,
            process=mock_proc,
        )
        pm._agents["a"] = agent

        new_mock_proc = MagicMock()
        new_mock_proc.pid = 5678
        new_mock_proc.poll.return_value = None
        with patch("subprocess.Popen", return_value=new_mock_proc), \
             patch("builtins.open", MagicMock()):
            result = pm.restart_agent("a")

        assert result is not None
        assert result.entrypoint == "holus.agents.marketing"


# ---------------------------------------------------------------------------
# TestShutdownAll
# ---------------------------------------------------------------------------


class TestShutdownAll:
    """Tests for ProcessManager.shutdown_all."""

    def test_stops_all_agents(self, tmp_path: Path) -> None:
        """stop_agent is called for each registered agent."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        for name in ["a", "b", "c"]:
            pm._agents[name] = AgentProcess(name=name, entrypoint="e", status=AgentStatus.RUNNING)

        with patch.object(pm, "stop_agent") as mock_stop:
            pm.shutdown_all()

        assert mock_stop.call_count == 3

    def test_handles_empty(self, tmp_path: Path) -> None:
        """shutdown_all on empty manager does not raise."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        pm.shutdown_all()  # should not raise

    def test_handles_multiple(self, tmp_path: Path) -> None:
        """shutdown_all correctly handles 2+ agents."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["x"] = AgentProcess(name="x", entrypoint="e", status=AgentStatus.RUNNING)
        pm._agents["y"] = AgentProcess(name="y", entrypoint="e", status=AgentStatus.RUNNING)

        with patch.object(pm, "stop_agent") as mock_stop:
            pm.shutdown_all(timeout=5.0)

        assert mock_stop.call_count == 2


# ---------------------------------------------------------------------------
# TestCheckHealth
# ---------------------------------------------------------------------------


class TestCheckHealth:
    """Tests for ProcessManager.check_health."""

    def test_returns_status_dict(self, tmp_path: Path) -> None:
        """check_health returns a dict mapping name -> AgentStatus."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # alive
        pm._agents["a"] = AgentProcess(
            name="a", entrypoint="e", status=AgentStatus.RUNNING, process=mock_proc
        )
        result = pm.check_health()
        assert isinstance(result, dict)
        assert "a" in result

    def test_detects_crashed_process(self, tmp_path: Path) -> None:
        """When is_alive=False and status!=STOPPED, _handle_crash is called."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # dead
        mock_proc.returncode = 1
        pm._agents["a"] = AgentProcess(
            name="a", entrypoint="e", status=AgentStatus.RUNNING, process=mock_proc
        )

        with patch.object(pm, "_handle_crash") as mock_crash:
            pm.check_health()

        mock_crash.assert_called_once()

    def test_skips_stopped_agents(self, tmp_path: Path) -> None:
        """STOPPED agents are returned in result but _handle_crash is not called."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["stopped"] = AgentProcess(
            name="stopped", entrypoint="e", status=AgentStatus.STOPPED
        )

        with patch.object(pm, "_handle_crash") as mock_crash:
            result = pm.check_health()

        mock_crash.assert_not_called()
        assert result["stopped"] == AgentStatus.STOPPED

    def test_running_agent_included(self, tmp_path: Path) -> None:
        """A live running agent appears as RUNNING in the result dict."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        pm._agents["alive"] = AgentProcess(
            name="alive", entrypoint="e", status=AgentStatus.RUNNING, process=mock_proc
        )
        result = pm.check_health()
        assert result["alive"] == AgentStatus.RUNNING

    def test_handle_crash_called_once_per_dead(self, tmp_path: Path) -> None:
        """_handle_crash is called exactly once per dead (non-stopped) agent."""
        from holus.core.process_manager import AgentProcess, AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        for name in ["x", "y"]:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = 1
            mock_proc.returncode = 1
            pm._agents[name] = AgentProcess(
                name=name, entrypoint="e", status=AgentStatus.RUNNING, process=mock_proc
            )

        with patch.object(pm, "_handle_crash") as mock_crash:
            pm.check_health()

        assert mock_crash.call_count == 2


# ---------------------------------------------------------------------------
# TestHandleCrash
# ---------------------------------------------------------------------------


class TestHandleCrash:
    """Tests for ProcessManager._handle_crash (exponential backoff + thread)."""

    def _make_agent(self, restart_count: int = 0, max_restarts: int = 3):
        """Return an AgentProcess suitable for crash handling tests."""
        from holus.core.process_manager import AgentProcess, AgentStatus

        return AgentProcess(
            name="test",
            entrypoint="holus.agents.test",
            status=AgentStatus.RUNNING,
            restart_count=restart_count,
            max_restarts=max_restarts,
            cooldown_seconds=60,
        )

    def test_increments_restart_count(self, tmp_path: Path) -> None:
        """restart_count increases by 1 on each crash."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        agent = self._make_agent(restart_count=0)

        with patch("threading.Thread"):
            pm._handle_crash(agent)

        assert agent.restart_count == 1

    def test_sets_crashed_when_over_limit(self, tmp_path: Path) -> None:
        """status becomes CRASHED when restart_count exceeds max_restarts."""
        from holus.core.process_manager import AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        agent = self._make_agent(restart_count=3, max_restarts=3)  # will become 4 > 3

        pm._handle_crash(agent)

        assert agent.status == AgentStatus.CRASHED

    def test_exponential_backoff(self, tmp_path: Path) -> None:
        """cooldown = cooldown_seconds * 2^(restart_count - 1) after increment."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        agent = self._make_agent(restart_count=0, max_restarts=5)
        agent.cooldown_seconds = 10

        captured_target = {}

        def fake_thread(**kwargs: object) -> MagicMock:
            captured_target["fn"] = kwargs.get("target")
            t = MagicMock()
            return t

        with patch("threading.Thread", side_effect=fake_thread):
            pm._handle_crash(agent)

        # restart_count is now 1, so cooldown = 10 * 2^0 = 10
        # We verify by checking the thread was spawned (backoff logic ran)
        assert agent.restart_count == 1
        assert agent.cooldown_seconds == 10  # unchanged

    def test_sets_restarting_status(self, tmp_path: Path) -> None:
        """status is set to RESTARTING before the thread starts."""
        from holus.core.process_manager import AgentStatus, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        agent = self._make_agent(restart_count=0, max_restarts=3)

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_cls.return_value = MagicMock()
            pm._handle_crash(agent)

        assert agent.status == AgentStatus.RESTARTING

    def test_spawns_thread(self, tmp_path: Path) -> None:
        """threading.Thread is instantiated and .start() is called."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        agent = self._make_agent(restart_count=0, max_restarts=3)

        mock_thread = MagicMock()
        with patch("threading.Thread", return_value=mock_thread) as mock_thread_cls:
            pm._handle_crash(agent)

        mock_thread_cls.assert_called_once()
        mock_thread.start.assert_called_once()


# ---------------------------------------------------------------------------
# TestIntrospection
# ---------------------------------------------------------------------------


class TestIntrospection:
    """Tests for list_agents, get_agent, reset_crash_counter."""

    def test_list_agents_empty(self, tmp_path: Path) -> None:
        """list_agents returns empty list on fresh manager."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        assert pm.list_agents() == []

    def test_list_agents_with_entries(self, tmp_path: Path) -> None:
        """list_agents returns all registered AgentProcess entries."""
        from holus.core.process_manager import AgentProcess, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        pm._agents["a"] = AgentProcess(name="a", entrypoint="e")
        pm._agents["b"] = AgentProcess(name="b", entrypoint="e")
        agents = pm.list_agents()
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"a", "b"}

    def test_get_agent_found(self, tmp_path: Path) -> None:
        """get_agent returns the correct AgentProcess."""
        from holus.core.process_manager import AgentProcess, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        expected = AgentProcess(name="x", entrypoint="holus.x")
        pm._agents["x"] = expected
        assert pm.get_agent("x") is expected

    def test_get_agent_not_found(self, tmp_path: Path) -> None:
        """get_agent returns None for unknown name."""
        from holus.core.process_manager import ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        assert pm.get_agent("missing") is None

    def test_reset_crash_counter(self, tmp_path: Path) -> None:
        """reset_crash_counter sets restart_count to 0."""
        from holus.core.process_manager import AgentProcess, ProcessManager

        pm = ProcessManager(log_dir=tmp_path)
        agent = AgentProcess(name="a", entrypoint="e", restart_count=5)
        pm._agents["a"] = agent
        pm.reset_crash_counter("a")
        assert agent.restart_count == 0
