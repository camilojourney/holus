import logging
from pathlib import Path

import yaml

from holus.core.capability_gap import CapabilityGap, CapabilityTier

logger = logging.getLogger(__name__)


class ConfigBuilder:
    """Tier 1 Self-Improvement: Creates new config files (specialists/reviewers)."""

    def __init__(self, config_root: Path = Path("config")):
        self.config_root = config_root
        self.specialists_spawned = self.config_root / "specialists" / "spawned"
        self.reviewers_spawned = self.config_root / "reviewers" / "spawned"
        self.prompts_spawned = self.config_root / "prompts" / "spawned"

        # Ensure directories exist
        self.specialists_spawned.mkdir(parents=True, exist_ok=True)
        self.reviewers_spawned.mkdir(parents=True, exist_ok=True)
        self.prompts_spawned.mkdir(parents=True, exist_ok=True)

    def build_from_gap(self, gap: CapabilityGap) -> bool:
        """Create a new config file based on the capability gap."""
        if gap.tier != CapabilityTier.TIER_1_CONFIG:
            logger.warning(f"ConfigBuilder cannot handle tier {gap.tier}")
            return False

        # Heuristic to decide where to put the new config
        # This would usually be more sophisticated or use another LLM call
        # For now, we file it based on keywords in "what"

        what_lower = gap.what.lower()
        content = {
            "name": gap.what,
            "description": gap.why,
            "gap_evidence": gap.evidence,
            "created_via": "self_improvement_tier_1",
        }

        filename = gap.what.lower().replace(" ", "_").replace("-", "_") + ".yaml"

        if "specialist" in what_lower or "creator" in what_lower:
            target_path = self.specialists_spawned / filename
        elif "reviewer" in what_lower or "judge" in what_lower or "score" in what_lower:
            target_path = self.reviewers_spawned / filename
        elif "prompt" in what_lower or "template" in what_lower:
            target_path = self.prompts_spawned / filename
        else:
            # Default to specialists if ambiguous
            target_path = self.specialists_spawned / filename

        try:
            with open(target_path, "w", encoding="utf-8") as f:
                yaml.dump(content, f, default_flow_style=False)
            logger.info(f"Successfully created Tier 1 config: {target_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write Tier 1 config: {e}")
            return False
