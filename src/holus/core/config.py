"""Holus configuration management.

Layered configuration strategy:
  1. config/base.yaml       -- shared defaults (committed to git)
  2. config/{agent}.yaml    -- agent-specific overrides (committed)
  3. Environment variables   -- secrets and runtime overrides (never committed)

Environment variables ALWAYS win.  YAML files contain no secrets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Per-agent configuration
# ---------------------------------------------------------------------------


class AgentConfig(BaseSettings):
    """Configuration for a single Holus agent."""

    model_config = SettingsConfigDict(extra="ignore")

    name: str = "unnamed-agent"
    enabled: bool = True

    # Model routing
    default_model_tier: Literal["strategic", "operational", "classification"] = "operational"

    # Guardrails
    max_retries: int = 3
    max_concurrent_tasks: int = 1
    timeout_seconds: int = 300

    # Memory
    mem0_scope: str = ""  # Defaults to agent name if blank

    # Observability
    langfuse_enabled: bool = True

    @model_validator(mode="after")
    def _default_mem0_scope(self) -> AgentConfig:
        if not self.mem0_scope:
            self.mem0_scope = self.name
        return self


# ---------------------------------------------------------------------------
# Global configuration
# ---------------------------------------------------------------------------


class HolusConfig(BaseSettings):
    """Root configuration for the entire Holus system.

    Secrets come exclusively from environment variables or ``.env``.
    Non-secret settings come from YAML files and can be overridden by env.
    """

    model_config = SettingsConfigDict(
        env_prefix="HOLUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Secrets (env-only) ------------------------------------------------
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    late_api_key: str = Field(default="", alias="LATE_API_KEY")

    # ---- Infrastructure (env or YAML) --------------------------------------
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    postgres_url: str = Field(
        default="postgresql://holus:holus@localhost:5432/holus",
        alias="DATABASE_URL",
    )
    langfuse_host: str = Field(default="http://localhost:3100", alias="LANGFUSE_HOST")
    mem0_api_url: str = Field(default="http://localhost:8050", alias="MEM0_API_URL")
    n8n_base_url: str = Field(default="http://localhost:5678", alias="N8N_BASE_URL")
    comfyui_base_url: str = Field(
        default="http://127.0.0.1:8188",
        alias="COMFYUI_BASE_URL",
    )

    # ---- Runtime settings --------------------------------------------------
    log_level: str = "INFO"
    agent_name: str = Field(default="holus", alias="HOLUS_AGENT_NAME")
    config_dir: Path = Field(default=Path("config"))
    data_dir: Path = Field(default=Path("data"))

    # ---- Model identifiers -------------------------------------------------
    opus_model: str = "claude-opus-4-20250514"
    sonnet_model: str = "claude-sonnet-4-5-20250514"
    haiku_model: str = "claude-haiku-3-5-20241022"

    # ---- Sub-configs (populated by load) -----------------------------------
    agents: dict[str, AgentConfig] = Field(default_factory=dict)

    # ---- Validators --------------------------------------------------------
    @field_validator("config_dir", "data_dir", mode="before")
    @classmethod
    def _coerce_path(cls, v: Any) -> Path:
        return Path(v)

    # ---- Loaders -----------------------------------------------------------
    @classmethod
    def load(cls, agent_name: str | None = None) -> HolusConfig:
        """Build a ``HolusConfig`` from YAML files + environment.

        Resolution order (later wins):
          1. ``config/base.yaml``
          2. ``config/{agent_name}.yaml``
          3. Environment variables / ``.env``
        """
        config_dir = Path("config")
        merged: dict[str, Any] = {}

        # -- Layer 1: base defaults -----------------------------------------
        base_path = config_dir / "base.yaml"
        if base_path.exists():
            with open(base_path) as fh:
                base_data = yaml.safe_load(fh)
            if base_data:
                merged.update(base_data)

        # -- Layer 2: agent-specific overlay --------------------------------
        if agent_name:
            agent_path = config_dir / f"{agent_name}.yaml"
            if agent_path.exists():
                with open(agent_path) as fh:
                    agent_data = yaml.safe_load(fh)
                if agent_data:
                    merged.update(agent_data)
            merged["agent_name"] = agent_name

        # -- Layer 3: env vars win (handled by pydantic-settings) -----------
        return cls(**merged)

    def get_agent_config(self, name: str) -> AgentConfig:
        """Return the ``AgentConfig`` for *name*, falling back to defaults."""
        return self.agents.get(name, AgentConfig(name=name))

    def model_for_tier(
        self,
        tier: Literal["strategic", "operational", "classification"],
    ) -> str:
        """Map a semantic tier to a concrete model identifier."""
        mapping = {
            "strategic": self.opus_model,
            "operational": self.sonnet_model,
            "classification": self.haiku_model,
        }
        return mapping[tier]
