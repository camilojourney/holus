"""Brand visual identity loader.

Loads config/brand-visual.yaml and converts it to a BrandVisualIdentity model
with CSS custom property generation. Delegates to the existing Pydantic models
in holus.agents.marketing.models.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from holus.agents.marketing.models import BrandVisualIdentity


class BrandVisualIdentityLoader:
    """Load and cache brand visual identity from a YAML config file.

    Usage::

        loader = BrandVisualIdentityLoader()           # uses config/brand-visual.yaml
        loader = BrandVisualIdentityLoader(Path("custom-brand.yaml"))
        brand = loader.load()
        css = brand.to_css_variables()

    The loader caches the loaded identity for the lifetime of the instance.
    Call ``reload()`` to force re-reading from disk.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or Path("config/brand-visual.yaml")
        self._cached: BrandVisualIdentity | None = None

    @property
    def config_path(self) -> Path:
        """Return the resolved config file path."""
        return self._config_path

    def load(self) -> BrandVisualIdentity:
        """Load brand identity from YAML, returning cached version if available."""
        if self._cached is not None:
            return self._cached
        return self.reload()

    def reload(self) -> BrandVisualIdentity:
        """Force reload from disk, updating the cache."""
        if not self._config_path.exists():
            self._cached = BrandVisualIdentity()
            return self._cached

        with open(self._config_path) as fh:
            data = yaml.safe_load(fh)

        if not data:
            self._cached = BrandVisualIdentity()
            return self._cached

        self._cached = BrandVisualIdentity(**data)
        return self._cached

    def to_css_variables(self) -> str:
        """Convenience: load brand and generate CSS custom properties."""
        return self.load().to_css_variables()
