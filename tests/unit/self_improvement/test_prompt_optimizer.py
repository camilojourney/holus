"""Tests for holus.self_improvement.prompt_optimizer."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

from holus.self_improvement.prompt_optimizer import (
    OPTIMIZER_PROMPT,
    PromptOptimizer,
    PromptVersion,
    PromptVersionStore,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_version(**overrides: Any) -> PromptVersion:
    """Create a PromptVersion with sensible defaults."""
    defaults: dict[str, Any] = {
        "version_id": "v_20260301_120000_strategy",
        "agent_id": "test-agent",
        "prompt_text": "You are a test agent.",
        "source": "manual",
        "is_active": False,
    }
    defaults.update(overrides)
    return PromptVersion(**defaults)


def _mock_claude_response(text: str) -> MagicMock:
    """Build a mock Claude API response with a single text block."""
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


def _make_optimizer(tmp_path: Path) -> tuple[PromptOptimizer, MagicMock, PromptVersionStore]:
    """Create a PromptOptimizer with mocked Anthropic client."""
    store = PromptVersionStore(base_dir=tmp_path)
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        opt = PromptOptimizer(api_key="sk-test", version_store=store)
    return opt, mock_client, store


# ===========================================================================
# PromptVersion dataclass
# ===========================================================================


class TestPromptVersion:
    """Tests for the PromptVersion dataclass."""

    def test_defaults(self) -> None:
        pv = PromptVersion(version_id="v1", agent_id="a1", prompt_text="hello")
        assert pv.source == "manual"
        assert pv.parent_version is None
        assert pv.performance_score is None
        assert pv.is_active is False
        assert pv.metadata == {}
        # created_at should be an ISO timestamp string
        assert "T" in pv.created_at

    def test_to_dict_roundtrip(self) -> None:
        pv = _make_version(parent_version="v0", performance_score=0.85, metadata={"key": "val"})
        d = pv.to_dict()
        assert d["version_id"] == pv.version_id
        assert d["agent_id"] == pv.agent_id
        assert d["prompt_text"] == pv.prompt_text
        assert d["parent_version"] == "v0"
        assert d["performance_score"] == 0.85
        assert d["metadata"] == {"key": "val"}

    def test_to_dict_contains_all_fields(self) -> None:
        pv = _make_version()
        d = pv.to_dict()
        expected_keys = {
            "version_id",
            "agent_id",
            "prompt_text",
            "created_at",
            "source",
            "parent_version",
            "performance_score",
            "is_active",
            "metadata",
        }
        assert set(d.keys()) == expected_keys


# ===========================================================================
# PromptVersionStore
# ===========================================================================


class TestPromptVersionStoreSave:
    """Tests for PromptVersionStore.save()."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        pv = _make_version()
        filepath = store.save(pv)
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert data["version_id"] == pv.version_id

    def test_save_creates_agent_dir(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        pv = _make_version(agent_id="new-agent")
        store.save(pv)
        assert (tmp_path / "new-agent").is_dir()


class TestPromptVersionStoreLoad:
    """Tests for PromptVersionStore.load()."""

    def test_load_returns_version(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        pv = _make_version()
        store.save(pv)
        loaded = store.load(pv.agent_id, pv.version_id)
        assert loaded is not None
        assert loaded.version_id == pv.version_id
        assert loaded.prompt_text == pv.prompt_text

    def test_load_nonexistent_returns_none(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        assert store.load("no-agent", "no-version") is None


class TestPromptVersionStoreLoadActive:
    """Tests for PromptVersionStore.load_active()."""

    def test_returns_active_version(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        v1 = _make_version(version_id="v1", is_active=False)
        v2 = _make_version(version_id="v2", is_active=True)
        store.save(v1)
        store.save(v2)
        active = store.load_active("test-agent")
        assert active is not None
        assert active.version_id == "v2"
        assert active.is_active is True

    def test_falls_back_to_most_recent(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        v1 = _make_version(version_id="a_v1", is_active=False)
        v2 = _make_version(version_id="b_v2", is_active=False)
        store.save(v1)
        store.save(v2)
        # Sorted reverse by filename — b_v2 > a_v1
        active = store.load_active("test-agent")
        assert active is not None
        assert active.version_id == "b_v2"

    def test_nonexistent_agent_returns_none(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        assert store.load_active("ghost-agent") is None

    def test_empty_dir_returns_none(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        (tmp_path / "empty-agent").mkdir()
        assert store.load_active("empty-agent") is None


class TestPromptVersionStoreListVersions:
    """Tests for PromptVersionStore.list_versions()."""

    def test_lists_all_versions_newest_first(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        for vid in ["a_v1", "b_v2", "c_v3"]:
            store.save(_make_version(version_id=vid))
        versions = store.list_versions("test-agent")
        assert len(versions) == 3
        # Sorted reverse alphabetically: c_v3 > b_v2 > a_v1
        assert versions[0].version_id == "c_v3"
        assert versions[2].version_id == "a_v1"

    def test_empty_agent_returns_empty_list(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        assert store.list_versions("nonexistent") == []


class TestPromptVersionStoreActivate:
    """Tests for PromptVersionStore.activate()."""

    def test_activate_sets_one_deactivates_others(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        v1 = _make_version(version_id="v1", is_active=True)
        v2 = _make_version(version_id="v2", is_active=False)
        store.save(v1)
        store.save(v2)

        store.activate("test-agent", "v2")

        loaded_v1 = store.load("test-agent", "v1")
        loaded_v2 = store.load("test-agent", "v2")
        assert loaded_v1 is not None and loaded_v1.is_active is False
        assert loaded_v2 is not None and loaded_v2.is_active is True

    def test_activate_nonexistent_agent_noop(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        # Should not raise
        store.activate("nonexistent", "v1")


# ===========================================================================
# OPTIMIZER_PROMPT
# ===========================================================================


class TestOptimizerPrompt:
    """Tests for the OPTIMIZER_PROMPT template."""

    def test_contains_required_placeholders(self) -> None:
        for placeholder in [
            "{current_prompt}",
            "{agent_id}",
            "{task_type}",
            "{failure_count}",
            "{failure_details}",
        ]:
            assert placeholder in OPTIMIZER_PROMPT

    def test_format_succeeds(self) -> None:
        result = OPTIMIZER_PROMPT.format(
            current_prompt="test prompt",
            agent_id="test-agent",
            task_type="strategy",
            failure_count=3,
            failure_details="details here",
        )
        assert "test prompt" in result
        assert "test-agent" in result


# ===========================================================================
# PromptOptimizer
# ===========================================================================


class TestPromptOptimizerInit:
    """Tests for PromptOptimizer.__init__()."""

    def test_init_creates_client(self, tmp_path: Path) -> None:
        with patch("anthropic.Anthropic") as mock_cls:
            PromptOptimizer(api_key="sk-test")
            mock_cls.assert_called_once_with(api_key="sk-test")

    def test_init_accepts_custom_store(self, tmp_path: Path) -> None:
        store = PromptVersionStore(base_dir=tmp_path)
        with patch("anthropic.Anthropic"):
            opt = PromptOptimizer(api_key="sk-test", version_store=store)
        assert opt._store is store


class TestPromptOptimizerOptimize:
    """Tests for PromptOptimizer.optimize()."""

    def test_optimize_success(self, tmp_path: Path) -> None:
        opt, mock_client, store = _make_optimizer(tmp_path)

        response_data = {
            "analysis": "Prompt was too vague on formatting.",
            "changes_made": ["Added JSON output format"],
            "new_prompt": "You are a better agent.",
        }
        mock_client.messages.create.return_value = _mock_claude_response(json.dumps(response_data))

        result = opt.optimize(
            agent_id="test-agent",
            task_type="strategy",
            current_prompt="You are a test agent.",
            failure_details=[{"task": "t1", "output": "bad", "feedback": "wrong"}],
        )

        assert result["analysis"] == "Prompt was too vague on formatting."
        assert result["new_prompt"] == "You are a better agent."
        assert result["version_id"] is not None
        # Verify version was saved
        versions = store.list_versions("test-agent")
        assert len(versions) == 1
        assert versions[0].source == "optimizer"

    def test_optimize_truncates_failures_to_5(self, tmp_path: Path) -> None:
        opt, mock_client, _store = _make_optimizer(tmp_path)

        response_data = {"analysis": "ok", "changes_made": [], "new_prompt": "new"}
        mock_client.messages.create.return_value = _mock_claude_response(json.dumps(response_data))

        failures = [
            {"task": f"task{i}", "output": f"out{i}", "feedback": f"fb{i}"} for i in range(10)
        ]
        opt.optimize(
            agent_id="test-agent",
            task_type="batch",
            current_prompt="prompt",
            failure_details=failures,
        )

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        # Only 5 failures should appear
        assert "Failure 5" in user_msg
        assert "Failure 6" not in user_msg

    def test_optimize_api_failure_returns_original_prompt(self, tmp_path: Path) -> None:
        opt, mock_client, _store = _make_optimizer(tmp_path)
        mock_client.messages.create.side_effect = RuntimeError("API down")

        result = opt.optimize(
            agent_id="test-agent",
            task_type="strategy",
            current_prompt="original prompt",
            failure_details=[{"task": "t1", "output": "bad", "feedback": "wrong"}],
        )

        assert result["new_prompt"] == "original prompt"
        assert result["version_id"] is None
        assert "failed" in result["analysis"].lower()

    def test_optimize_json_decode_error_returns_original(self, tmp_path: Path) -> None:
        opt, mock_client, _store = _make_optimizer(tmp_path)
        mock_client.messages.create.return_value = _mock_claude_response("not json at all")

        result = opt.optimize(
            agent_id="test-agent",
            task_type="strategy",
            current_prompt="keep this",
            failure_details=[{"task": "t1"}],
        )

        assert result["new_prompt"] == "keep this"
        assert result["version_id"] is None

    def test_optimize_sets_parent_version(self, tmp_path: Path) -> None:
        opt, mock_client, store = _make_optimizer(tmp_path)

        response_data = {"analysis": "ok", "changes_made": [], "new_prompt": "new"}
        mock_client.messages.create.return_value = _mock_claude_response(json.dumps(response_data))

        # Save an existing active version
        existing = _make_version(version_id="v_existing", is_active=True)
        store.save(existing)

        opt.optimize(
            agent_id="test-agent",
            task_type="strategy",
            current_prompt="old",
            failure_details=[{"task": "t"}],
        )

        versions = store.list_versions("test-agent")
        new_version = next(v for v in versions if v.version_id != "v_existing")
        assert new_version.parent_version == "v_existing"

    def test_optimize_missing_failure_keys(self, tmp_path: Path) -> None:
        """Failures with missing keys should still format without errors."""
        opt, mock_client, _store = _make_optimizer(tmp_path)

        response_data = {"analysis": "ok", "changes_made": [], "new_prompt": "new"}
        mock_client.messages.create.return_value = _mock_claude_response(json.dumps(response_data))

        # Failures with no task/output/feedback keys
        opt.optimize(
            agent_id="test-agent",
            task_type="edge",
            current_prompt="p",
            failure_details=[{}, {"task": "only task"}],
        )

        # Should have called the API without error
        assert mock_client.messages.create.called


class TestPromptOptimizerShouldUseNewPrompt:
    """Tests for PromptOptimizer.should_use_new_prompt()."""

    def test_single_version_returns_false(self, tmp_path: Path) -> None:
        opt, _, store = _make_optimizer(tmp_path)
        store.save(_make_version(version_id="v1", is_active=True))

        use_new, version = opt.should_use_new_prompt("test-agent")
        assert use_new is False
        assert version is not None
        assert version.version_id == "v1"

    def test_no_versions_returns_none(self, tmp_path: Path) -> None:
        opt, _, _store = _make_optimizer(tmp_path)

        use_new, version = opt.should_use_new_prompt("test-agent")
        assert use_new is False
        assert version is None

    @patch("random.random", return_value=0.1)  # Below 0.2 threshold
    def test_ab_test_selects_candidate(self, _mock_random: MagicMock, tmp_path: Path) -> None:
        opt, _, store = _make_optimizer(tmp_path)
        store.save(_make_version(version_id="v1", is_active=True, source="manual"))
        store.save(_make_version(version_id="v2", is_active=False, source="optimizer"))

        use_new, version = opt.should_use_new_prompt("test-agent")
        assert use_new is True
        assert version is not None
        assert version.version_id == "v2"

    @patch("random.random", return_value=0.9)  # Above 0.2 threshold
    def test_ab_test_selects_active(self, _mock_random: MagicMock, tmp_path: Path) -> None:
        opt, _, store = _make_optimizer(tmp_path)
        store.save(_make_version(version_id="v1", is_active=True, source="manual"))
        store.save(_make_version(version_id="v2", is_active=False, source="optimizer"))

        use_new, version = opt.should_use_new_prompt("test-agent")
        assert use_new is False
        assert version is not None
        assert version.is_active is True


class TestPromptOptimizerPromoteVersion:
    """Tests for PromptOptimizer.promote_version()."""

    def test_promote_activates_version(self, tmp_path: Path) -> None:
        opt, _, store = _make_optimizer(tmp_path)
        store.save(_make_version(version_id="v1", is_active=True))
        store.save(_make_version(version_id="v2", is_active=False))

        opt.promote_version("test-agent", "v2")

        loaded = store.load("test-agent", "v2")
        assert loaded is not None and loaded.is_active is True
        loaded_old = store.load("test-agent", "v1")
        assert loaded_old is not None and loaded_old.is_active is False


class TestPromptOptimizerRollback:
    """Tests for PromptOptimizer.rollback()."""

    def test_rollback_activates_previous(self, tmp_path: Path) -> None:
        opt, _, store = _make_optimizer(tmp_path)
        store.save(_make_version(version_id="a_v1", is_active=False))
        store.save(_make_version(version_id="b_v2", is_active=True))

        rolled = opt.rollback("test-agent")
        assert rolled is not None
        assert rolled.version_id == "a_v1"

    def test_rollback_single_version_returns_none(self, tmp_path: Path) -> None:
        opt, _, store = _make_optimizer(tmp_path)
        store.save(_make_version(version_id="v1", is_active=True))

        assert opt.rollback("test-agent") is None

    def test_rollback_no_versions_returns_none(self, tmp_path: Path) -> None:
        opt, _, _store = _make_optimizer(tmp_path)
        assert opt.rollback("test-agent") is None
