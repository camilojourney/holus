"""Three-layer prompt resolution for Holus agents.

Resolution order (first hit wins):
  1. ``config/prompts/{agent_id}/current.md`` — optimizer-promoted variant
  2. ``agents/{role}/{agent_id}.md``           — canonical .md (default)
  3. Hardcoded Python ``fallback`` constant    — safety net during bootstrapping

The canonical path for layer 2 is resolved via AGENTS.yaml so callers do not
need to know which sub-folder the agent lives in.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default repo root: relative to this file
#   src/holus/core/prompt_loader.py
#   parents[0] = src/holus/core, [1] = src/holus, [2] = src, [3] = repo_root
_DEFAULT_REPO_ROOT = Path(__file__).parents[3]


class PromptLoader:
    """Resolve agent prompts through three ordered layers.

    Usage::

        loader = PromptLoader()
        prompt = loader.get_prompt("hook-architect")

        # With a fallback if no .md file exists yet:
        prompt = loader.get_prompt("new-agent", fallback="You are new-agent.")
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or _DEFAULT_REPO_ROOT
        self._agents_yaml_path = self._repo_root / "agents" / "AGENTS.yaml"
        self._agents_data: dict[str, Any] | None = None

    # -- Internal helpers --------------------------------------------------

    def _agents_yaml(self) -> dict[str, Any]:
        """Lazy-load AGENTS.yaml (cached for the lifetime of the loader)."""
        if self._agents_data is None:
            raw = self._agents_yaml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            self._agents_data = data.get("agents", {})
        return self._agents_data

    def _canonical_path(self, agent_id: str) -> Path | None:
        """Return the Layer-2 .md path from AGENTS.yaml, or None if unknown."""
        agents = self._agents_yaml()
        info = agents.get(agent_id)
        if not info:
            return None
        prompt_rel = info.get("prompt", "")
        if not prompt_rel:
            return None
        result: Path = self._repo_root / "agents" / prompt_rel
        return result

    # -- Public API --------------------------------------------------------

    def get_prompt(self, agent_id: str, fallback: str = "") -> str:
        """Resolve a prompt through the three-layer hierarchy.

        Layer 1 — optimizer variant
            ``config/prompts/{agent_id}/current.md``

        Layer 2 — canonical .md file
            ``agents/{prompt_path}`` (from AGENTS.yaml)

        Layer 3 — hardcoded Python constant
            *fallback* parameter (emits WARNING)

        Args:
            agent_id: The agent identifier (e.g. ``"hook-architect"``).
            fallback: Hardcoded Python string to use as last resort.

        Returns:
            The resolved prompt text.
        """
        # Layer 1 — optimizer variant
        layer1 = self._repo_root / "config" / "prompts" / agent_id / "current.md"
        if layer1.exists():
            text = layer1.read_text(encoding="utf-8")
            logger.info(
                "prompt_loader: resolved %s → %s (layer 1)",
                agent_id,
                layer1.relative_to(self._repo_root),
            )
            return text

        # Layer 2 — canonical .md file
        layer2 = self._canonical_path(agent_id)
        if layer2 is not None and layer2.exists():
            text = layer2.read_text(encoding="utf-8")
            logger.info(
                "prompt_loader: resolved %s → %s (layer 2)",
                agent_id,
                layer2.relative_to(self._repo_root),
            )
            return text

        # Layer 3 — hardcoded Python fallback
        logger.warning(
            "prompt_loader: no .md file for %s — falling back to Python string (layer 3)",
            agent_id,
        )
        return fallback

    def get_ab_split(self, agent_id: str) -> tuple[str, str, float] | None:
        """Return A/B split if ``config/prompts/{agent_id}/ab_test.yaml`` exists.

        Returns:
            ``(control_prompt, challenger_prompt, split_ratio)`` or ``None``
            when no A/B variant is configured.
        """
        ab_config_path = self._repo_root / "config" / "prompts" / agent_id / "ab_test.yaml"
        if not ab_config_path.exists():
            return None

        raw = ab_config_path.read_text(encoding="utf-8")
        cfg: dict[str, Any] = yaml.safe_load(raw) or {}

        control_path = ab_config_path.parent / cfg.get("control", "control.md")
        challenger_path = ab_config_path.parent / cfg.get("challenger", "challenger.md")
        split_ratio: float = float(cfg.get("split_ratio", 0.5))

        if not control_path.exists() or not challenger_path.exists():
            logger.warning(
                "prompt_loader: ab_test.yaml found for %s but variant files missing",
                agent_id,
            )
            return None

        control = control_path.read_text(encoding="utf-8")
        challenger = challenger_path.read_text(encoding="utf-8")
        return (control, challenger, split_ratio)

    def list_optimizer_variants(self, agent_id: str) -> list[Path]:
        """Return all variant .md files under ``config/prompts/{agent_id}/``.

        Returns:
            Sorted list of Path objects (empty if no variants exist).
        """
        variants_dir = self._repo_root / "config" / "prompts" / agent_id
        if not variants_dir.is_dir():
            return []
        return sorted(variants_dir.glob("*.md"))
