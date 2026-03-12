from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class CapabilityTier(StrEnum):
    """The tier of self-improvement required to bridge a gap."""

    TIER_1_CONFIG = "tier_1_config"
    TIER_2_CODE = "tier_2_code"
    TIER_3_ARCHITECTURE = "tier_3_architecture"


class CapabilityGap(BaseModel):
    """A capability gap identified during the marketing agent's REASON phase."""

    what: str = Field(description="Short description of what capability is missing")
    why: str = Field(description="Motivation for why this capability is needed")
    tier: CapabilityTier = Field(description="The implementation tier (config/code/architecture)")
    evidence: str | None = Field(
        None, description="Supporting evidence (analytics, competitor research)"
    )
    workaround: str | None = Field(None, description="Current workaround, if any")
    priority: int = Field(default=1, ge=1, le=5, description="Priority (1=lowest, 5=highest)")


class CapabilityRequest(BaseModel):
    """A structured request to build a new capability via Tier 2 (Codex)."""

    what: str
    why: str
    tier: CapabilityTier = CapabilityTier.TIER_2_CODE
    evidence: str | None = None
    workaround: str | None = None
    status: str = Field(
        default="pending", pattern="^(pending|building|built|merged|failed|pending_human)$"
    )
    branch: str | None = None
    slug: str = Field(description="Unique slug for branch naming and tracking")
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
