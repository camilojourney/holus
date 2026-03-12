import yaml
from pathlib import Path
from typing import Any, List

class CapabilityRegistry:
    """Registry of current Holus capabilities.
    
    Loads from config/capabilities.yaml and provides methods to check if
    a capability (platform, content type, silo, specialist, reviewer) is supported.
    """
    
    def __init__(self, config_path: Path = Path("config/capabilities.yaml")):
        self.config_path = config_path
        self._capabilities: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load capabilities from the YAML file."""
        if not self.config_path.exists():
            # Fallback to empty if not found (though it should be created)
            self._capabilities = {
                "platforms": [],
                "content_types": [],
                "silos": [],
                "specialists": [],
                "reviewers": []
            }
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                self._capabilities = data
            else:
                self._capabilities = {}

    def is_supported(self, category: str, item: str) -> bool:
        """Check if an item is supported in a given category."""
        items = self._capabilities.get(category, [])
        if not isinstance(items, list):
            return False
        return item.lower() in [i.lower() for i in items if isinstance(i, str)]

    @property
    def platforms(self) -> List[str]:
        return self._capabilities.get("platforms", [])

    @property
    def content_types(self) -> List[str]:
        return self._capabilities.get("content_types", [])

    @property
    def silos(self) -> List[str]:
        return self._capabilities.get("silos", [])

    @property
    def specialists(self) -> List[str]:
        return self._capabilities.get("specialists", [])

    @property
    def reviewers(self) -> List[str]:
        return self._capabilities.get("reviewers", [])
