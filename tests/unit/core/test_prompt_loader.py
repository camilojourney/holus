"""Tests for PromptLoader (Spec 030).

Verifies:
- Layer 1 (config/prompts/{id}/current.md) wins when present
- Layer 2 (agents/{path}.md from AGENTS.yaml) is used when Layer 1 absent
- Layer 3 (fallback string) is used when no .md file exists, emits WARNING
- get_ab_split returns None when no ab_test.yaml exists
- get_ab_split returns (control, challenger, ratio) when configured
- get_ab_split returns None when variant files referenced in yaml are missing
- list_optimizer_variants returns empty list when no variants exist
- list_optimizer_variants returns sorted .md paths when variants exist
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
import yaml

from holus.core.prompt_loader import PromptLoader

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_agents_yaml(tmp_path: Path, prompt_rel: str = "specialists/test/my-agent.md") -> Path:
    """Write a minimal AGENTS.yaml that maps my-agent to prompt_rel."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "agents": {
            "my-agent": {
                "role": "Test agent",
                "type": "specialist",
                "model_tier": "operational",
                "status": "active",
                "version": "1.0.0",
                "prompt": prompt_rel,
            }
        }
    }
    yaml_path = agents_dir / "AGENTS.yaml"
    yaml_path.write_text(yaml.dump(data), encoding="utf-8")
    return yaml_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Minimal repo layout:
      tmp_path/
        agents/
          AGENTS.yaml
          specialists/test/my-agent.md   (layer 2)
        config/
          prompts/                       (empty — no layer 1 by default)
    """
    # Create agents/AGENTS.yaml
    _write_agents_yaml(tmp_path, prompt_rel="specialists/test/my-agent.md")

    # Create canonical .md (layer 2)
    canonical_dir = tmp_path / "agents" / "specialists" / "test"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "my-agent.md").write_text("# Layer 2 prompt", encoding="utf-8")

    # Create config/prompts/ dir (empty)
    (tmp_path / "config" / "prompts").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def loader(repo_root: Path) -> PromptLoader:
    return PromptLoader(repo_root=repo_root)


# ---------------------------------------------------------------------------
# Layer 1 tests
# ---------------------------------------------------------------------------


class TestLayer1:
    def test_layer1_wins_when_present(self, loader: PromptLoader, repo_root: Path) -> None:
        """config/prompts/{id}/current.md takes priority over canonical .md."""
        variant_dir = repo_root / "config" / "prompts" / "my-agent"
        variant_dir.mkdir(parents=True, exist_ok=True)
        (variant_dir / "current.md").write_text("# Layer 1 optimizer variant", encoding="utf-8")

        result = loader.get_prompt("my-agent")
        assert result == "# Layer 1 optimizer variant"

    def test_layer1_wins_over_layer2_and_fallback(
        self, loader: PromptLoader, repo_root: Path
    ) -> None:
        variant_dir = repo_root / "config" / "prompts" / "my-agent"
        variant_dir.mkdir(parents=True, exist_ok=True)
        (variant_dir / "current.md").write_text("Optimizer says hello", encoding="utf-8")

        result = loader.get_prompt("my-agent", fallback="Python fallback")
        assert result == "Optimizer says hello"


# ---------------------------------------------------------------------------
# Layer 2 tests
# ---------------------------------------------------------------------------


class TestLayer2:
    def test_layer2_used_when_no_layer1(self, loader: PromptLoader) -> None:
        """agents/{path}.md is used when no optimizer variant exists."""
        result = loader.get_prompt("my-agent")
        assert result == "# Layer 2 prompt"

    def test_layer2_wins_over_fallback(self, loader: PromptLoader) -> None:
        result = loader.get_prompt("my-agent", fallback="Python fallback")
        assert result == "# Layer 2 prompt"

    def test_layer2_logs_resolution(
        self, loader: PromptLoader, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="holus.core.prompt_loader"):
            loader.get_prompt("my-agent")
        assert "layer 2" in caplog.text
        assert "my-agent" in caplog.text


# ---------------------------------------------------------------------------
# Layer 3 tests
# ---------------------------------------------------------------------------


class TestLayer3:
    def test_layer3_used_when_no_md_file(self, loader: PromptLoader, repo_root: Path) -> None:
        """Fallback string is returned and WARNING is emitted when no .md exists."""
        # Register an agent with a non-existent .md path
        agents_yaml = repo_root / "agents" / "AGENTS.yaml"
        data = yaml.safe_load(agents_yaml.read_text())
        data["agents"]["no-file-agent"] = {
            "role": "Ghost",
            "type": "specialist",
            "model_tier": "operational",
            "status": "planned",
            "version": "0.1.0",
            "prompt": "specialists/ghost/no-file-agent.md",  # does not exist
        }
        agents_yaml.write_text(yaml.dump(data), encoding="utf-8")

        fresh_loader = PromptLoader(repo_root=repo_root)
        result = fresh_loader.get_prompt("no-file-agent", fallback="Python fallback string")
        assert result == "Python fallback string"

    def test_layer3_emits_warning(
        self, loader: PromptLoader, repo_root: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        agents_yaml = repo_root / "agents" / "AGENTS.yaml"
        data = yaml.safe_load(agents_yaml.read_text())
        data["agents"]["ghost-agent"] = {
            "role": "Ghost",
            "type": "ops",
            "model_tier": "operational",
            "status": "planned",
            "version": "0.1.0",
            "prompt": "ops/ghost-agent.md",
        }
        agents_yaml.write_text(yaml.dump(data), encoding="utf-8")

        fresh_loader = PromptLoader(repo_root=repo_root)
        with caplog.at_level(logging.WARNING, logger="holus.core.prompt_loader"):
            fresh_loader.get_prompt("ghost-agent", fallback="fallback")
        assert "layer 3" in caplog.text
        assert "ghost-agent" in caplog.text

    def test_layer3_empty_fallback_returns_empty(self, loader: PromptLoader, repo_root: Path) -> None:
        agents_yaml = repo_root / "agents" / "AGENTS.yaml"
        data = yaml.safe_load(agents_yaml.read_text())
        data["agents"]["empty-agent"] = {
            "role": "Empty",
            "type": "ops",
            "model_tier": "operational",
            "status": "planned",
            "version": "0.1.0",
            "prompt": "ops/empty-agent.md",
        }
        agents_yaml.write_text(yaml.dump(data), encoding="utf-8")

        fresh_loader = PromptLoader(repo_root=repo_root)
        result = fresh_loader.get_prompt("empty-agent")
        assert result == ""

    def test_unknown_agent_falls_through_to_layer3(
        self, loader: PromptLoader
    ) -> None:
        """An agent ID not in AGENTS.yaml has no canonical path — falls to layer 3."""
        result = loader.get_prompt("completely-unknown-agent", fallback="safe fallback")
        assert result == "safe fallback"


# ---------------------------------------------------------------------------
# A/B split tests
# ---------------------------------------------------------------------------


class TestAbSplit:
    def test_returns_none_when_no_ab_config(self, loader: PromptLoader) -> None:
        result = loader.get_ab_split("my-agent")
        assert result is None

    def test_returns_split_when_configured(self, loader: PromptLoader, repo_root: Path) -> None:
        variant_dir = repo_root / "config" / "prompts" / "my-agent"
        variant_dir.mkdir(parents=True, exist_ok=True)

        (variant_dir / "control.md").write_text("Control prompt", encoding="utf-8")
        (variant_dir / "challenger.md").write_text("Challenger prompt", encoding="utf-8")

        ab_config = {
            "control": "control.md",
            "challenger": "challenger.md",
            "split_ratio": 0.3,
        }
        (variant_dir / "ab_test.yaml").write_text(yaml.dump(ab_config), encoding="utf-8")

        result = loader.get_ab_split("my-agent")
        assert result is not None
        control, challenger, ratio = result
        assert control == "Control prompt"
        assert challenger == "Challenger prompt"
        assert ratio == pytest.approx(0.3)

    def test_ab_split_returns_none_when_files_missing(
        self, loader: PromptLoader, repo_root: Path
    ) -> None:
        variant_dir = repo_root / "config" / "prompts" / "my-agent"
        variant_dir.mkdir(parents=True, exist_ok=True)

        # ab_test.yaml references files that don't exist
        ab_config = {
            "control": "missing-control.md",
            "challenger": "missing-challenger.md",
            "split_ratio": 0.5,
        }
        (variant_dir / "ab_test.yaml").write_text(yaml.dump(ab_config), encoding="utf-8")

        result = loader.get_ab_split("my-agent")
        assert result is None

    def test_ab_split_default_ratio(self, loader: PromptLoader, repo_root: Path) -> None:
        """When split_ratio is absent from ab_test.yaml, defaults to 0.5."""
        variant_dir = repo_root / "config" / "prompts" / "my-agent"
        variant_dir.mkdir(parents=True, exist_ok=True)

        (variant_dir / "control.md").write_text("Control", encoding="utf-8")
        (variant_dir / "challenger.md").write_text("Challenger", encoding="utf-8")

        ab_config = {"control": "control.md", "challenger": "challenger.md"}
        (variant_dir / "ab_test.yaml").write_text(yaml.dump(ab_config), encoding="utf-8")

        result = loader.get_ab_split("my-agent")
        assert result is not None
        _, _, ratio = result
        assert ratio == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Optimizer variants tests
# ---------------------------------------------------------------------------


class TestOptimizerVariants:
    def test_empty_when_no_variants_dir(self, loader: PromptLoader) -> None:
        result = loader.list_optimizer_variants("my-agent")
        assert result == []

    def test_returns_md_files(self, loader: PromptLoader, repo_root: Path) -> None:
        variant_dir = repo_root / "config" / "prompts" / "my-agent"
        variant_dir.mkdir(parents=True, exist_ok=True)

        (variant_dir / "current.md").write_text("current", encoding="utf-8")
        (variant_dir / "v1.md").write_text("v1", encoding="utf-8")
        (variant_dir / "v2.md").write_text("v2", encoding="utf-8")
        # Non-.md file should not appear
        (variant_dir / "ab_test.yaml").write_text("yaml", encoding="utf-8")

        result = loader.list_optimizer_variants("my-agent")
        names = [p.name for p in result]
        assert "current.md" in names
        assert "v1.md" in names
        assert "v2.md" in names
        assert "ab_test.yaml" not in names

    def test_returns_sorted_paths(self, loader: PromptLoader, repo_root: Path) -> None:
        variant_dir = repo_root / "config" / "prompts" / "my-agent"
        variant_dir.mkdir(parents=True, exist_ok=True)

        (variant_dir / "z.md").write_text("z", encoding="utf-8")
        (variant_dir / "a.md").write_text("a", encoding="utf-8")
        (variant_dir / "m.md").write_text("m", encoding="utf-8")

        result = loader.list_optimizer_variants("my-agent")
        names = [p.name for p in result]
        assert names == sorted(names)
