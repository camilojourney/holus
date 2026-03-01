"""Kill switch system for emergency agent shutdown.

Three scopes:
  1. **Per-agent** -- stop a single agent (``holus:kill:{agent_name}``).
  2. **Per-domain** -- stop all agents in a domain (``holus:kill:domain:{domain}``).
  3. **Global** -- stop everything (``holus:kill:global``).

Kill switches are stored in Redis for instant, cross-process visibility.
Every agent action loop must call ``check_kill_switch`` before proceeding.

Activation methods:
  - CLI: ``python -m holus kill --scope marketing-agent``
  - SSH: ``redis-cli SET holus:kill:global ...``
  - n8n webhook: ``POST /webhook/kill-switch``
  - Automatic: circuit breaker conditions (crash counts)
  - Slack command: ``/holus kill marketing-agent``
"""

from __future__ import annotations

import functools
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class KillSwitchScope(StrEnum):
    GLOBAL = "global"
    MARKETING = "marketing"
    PILASTER = "pilaster"
    COORDINATOR = "coordinator"


class KillSwitchState(BaseModel):
    """Persisted state for an active kill switch."""

    activated_at: datetime
    reason: str = ""
    activated_by: str = "manual"  # "manual" | "circuit_breaker" | "coordinator"
    scope: str = "global"


class KillSwitchActive(Exception):  # noqa: N818
    """Raised when an operation is blocked by an active kill switch."""

    def __init__(self, scope: str, state: KillSwitchState) -> None:
        self.scope = scope
        self.state = state
        super().__init__(
            f"Kill switch active for '{scope}': {state.reason} "
            f"(activated {state.activated_at.isoformat()} by {state.activated_by})"
        )


# ---------------------------------------------------------------------------
# Domain-to-agent mapping
# ---------------------------------------------------------------------------

DOMAIN_AGENTS: dict[str, list[str]] = {
    "marketing": ["marketing-agent"],
    "pilaster": ["pilaster-agent"],
    "coordinator": ["holus-coordinator"],
}


# ---------------------------------------------------------------------------
# Kill Switch
# ---------------------------------------------------------------------------


class KillSwitch:
    """Redis-backed kill switch with per-agent, per-domain, and global scopes."""

    GLOBAL_KEY = "holus:kill:global"
    AGENT_PREFIX = "holus:kill:agent:"
    DOMAIN_PREFIX = "holus:kill:domain:"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    # -- Activation / deactivation -------------------------------------------

    def activate(
        self,
        scope: str = "global",
        reason: str = "",
        activated_by: str = "manual",
    ) -> None:
        """Activate a kill switch.

        Args:
            scope: ``"global"``, a domain name (``"marketing"``), or an agent
                   name (``"marketing-agent"``).
            reason: Human-readable explanation.
            activated_by: Who triggered it (``"manual"``, ``"circuit_breaker"``).
        """
        key = self._key_for(scope)
        state = KillSwitchState(
            activated_at=datetime.now(UTC),
            reason=reason,
            activated_by=activated_by,
            scope=scope,
        )
        self._redis.set(key, state.model_dump_json())
        logger.warning("Kill switch ACTIVATED: scope=%s reason=%s", scope, reason)

    def deactivate(self, scope: str = "global") -> None:
        """Deactivate a kill switch."""
        key = self._key_for(scope)
        self._redis.delete(key)
        logger.info("Kill switch DEACTIVATED: scope=%s", scope)

    # -- Checking ------------------------------------------------------------

    def is_active(self, agent_name: str) -> bool:
        """Return ``True`` if this agent should halt.

        Checks, in order:
          1. Global kill switch.
          2. Domain-level kill switch (if agent belongs to a domain).
          3. Agent-specific kill switch.
        """
        # Global
        if self._redis.exists(self.GLOBAL_KEY):
            return True

        # Domain
        for domain, agents in DOMAIN_AGENTS.items():
            if agent_name in agents:
                domain_key = f"{self.DOMAIN_PREFIX}{domain}"
                if self._redis.exists(domain_key):
                    return True

        # Agent-specific
        agent_key = f"{self.AGENT_PREFIX}{agent_name}"
        return bool(self._redis.exists(agent_key))

    def get_state(self, scope: str) -> KillSwitchState | None:
        """Return the ``KillSwitchState`` for *scope*, or ``None``."""
        key = self._key_for(scope)
        raw = self._redis.get(key)
        if raw is None:
            return None
        return KillSwitchState.model_validate_json(raw)

    def status(self) -> dict[str, KillSwitchState]:
        """Return all currently active kill switches.  Used by dashboards."""
        result: dict[str, KillSwitchState] = {}
        for key in self._redis.scan_iter(match="holus:kill:*"):
            key_str = key if isinstance(key, str) else key.decode()
            raw = self._redis.get(key)
            if raw:
                try:
                    state = KillSwitchState.model_validate_json(raw)
                    result[key_str] = state
                except Exception:
                    logger.warning("Malformed kill switch state at %s", key_str)
        return result

    # -- Auto-trigger (circuit breaker) --------------------------------------

    def auto_trigger_on_loss(
        self,
        agent_name: str,
        daily_loss_pct: float,
        threshold: float = 0.05,
    ) -> bool:
        """Automatically activate kill switch if daily drawdown exceeds threshold.

        Returns ``True`` if the kill switch was triggered.
        """
        if daily_loss_pct >= threshold:
            self.activate(
                scope=agent_name,
                reason=f"Daily loss {daily_loss_pct:.1%} exceeded threshold {threshold:.1%}",
                activated_by="circuit_breaker",
            )
            return True
        return False

    def auto_trigger_on_crash_count(
        self,
        agent_name: str,
        crash_count: int,
        max_crashes: int = 3,
    ) -> bool:
        """Automatically activate kill switch after repeated crashes.

        Returns ``True`` if the kill switch was triggered.
        """
        if crash_count >= max_crashes:
            self.activate(
                scope=agent_name,
                reason=f"Agent crashed {crash_count} times (limit {max_crashes})",
                activated_by="circuit_breaker",
            )
            return True
        return False

    # -- Internals -----------------------------------------------------------

    def _key_for(self, scope: str) -> str:
        if scope == "global":
            return self.GLOBAL_KEY
        if scope in DOMAIN_AGENTS:
            return f"{self.DOMAIN_PREFIX}{scope}"
        return f"{self.AGENT_PREFIX}{scope}"


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def check_kill_switch(kill_switch: KillSwitch, agent_name: str):
    """Decorator that checks the kill switch before executing a function.

    Raises ``KillSwitchActive`` if the agent is halted.

    Usage::

        ks = KillSwitch(redis_client)

        @check_kill_switch(ks, "marketing-agent")
        def generate_content(decision):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if kill_switch.is_active(agent_name):
                state = (
                    kill_switch.get_state(agent_name)
                    or kill_switch.get_state("global")
                    or KillSwitchState(
                        activated_at=datetime.now(UTC),
                        reason="Unknown",
                        scope=agent_name,
                    )
                )
                raise KillSwitchActive(agent_name, state)
            return func(*args, **kwargs)

        return wrapper

    return decorator
