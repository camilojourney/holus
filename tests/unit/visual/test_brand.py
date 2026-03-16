"""Tests for BrandVisualIdentityLoader."""

from __future__ import annotations

from pathlib import Path

import yaml

from holus.agents.marketing.models import BrandVisualIdentity
from holus.visual.brand import BrandVisualIdentityLoader

_REPO_BRAND_CONFIG = Path("config/brand-visual.yaml")


class TestBrandVisualIdentityLoader:
    """Test brand config loading from YAML."""

    def test_defaults_when_file_missing(self):
        loader = BrandVisualIdentityLoader(Path("/nonexistent/brand.yaml"))
        brand = loader.load()
        assert isinstance(brand, BrandVisualIdentity)
        assert brand.colors.primary == "#E85D04"

    def test_load_from_yaml(self, tmp_path: Path):
        config = {
            "colors": {"primary": "#FF0000", "accent": "#00FF00"},
            "typography": {"primary_font": "Roboto"},
            "layout": {"slide_width": 1200},
        }
        config_file = tmp_path / "brand-visual.yaml"
        config_file.write_text(yaml.dump(config))

        loader = BrandVisualIdentityLoader(config_file)
        brand = loader.load()
        assert brand.colors.primary == "#FF0000"
        assert brand.colors.accent == "#00FF00"
        assert brand.typography.primary_font == "Roboto"
        assert brand.layout.slide_width == 1200
        # Defaults preserved for unspecified fields
        assert brand.colors.text == "#1A1A2E"

    def test_caching(self, tmp_path: Path):
        config_file = tmp_path / "brand.yaml"
        config_file.write_text(yaml.dump({"colors": {"primary": "#111111"}}))

        loader = BrandVisualIdentityLoader(config_file)
        brand1 = loader.load()
        brand2 = loader.load()
        assert brand1 is brand2  # same cached object

    def test_reload_clears_cache(self, tmp_path: Path):
        config_file = tmp_path / "brand.yaml"
        config_file.write_text(yaml.dump({"colors": {"primary": "#111111"}}))

        loader = BrandVisualIdentityLoader(config_file)
        brand1 = loader.load()
        assert brand1.colors.primary == "#111111"

        # Update file and reload
        config_file.write_text(yaml.dump({"colors": {"primary": "#222222"}}))
        brand2 = loader.reload()
        assert brand2.colors.primary == "#222222"
        assert brand1 is not brand2

    def test_empty_yaml_returns_defaults(self, tmp_path: Path):
        config_file = tmp_path / "brand.yaml"
        config_file.write_text("")

        loader = BrandVisualIdentityLoader(config_file)
        brand = loader.load()
        assert brand.colors.primary == "#E85D04"

    def test_to_css_variables_convenience(self, tmp_path: Path):
        config_file = tmp_path / "brand.yaml"
        config_file.write_text(yaml.dump({"colors": {"primary": "#ABCDEF"}}))

        loader = BrandVisualIdentityLoader(config_file)
        css = loader.to_css_variables()
        assert "--brand-color-primary: #ABCDEF;" in css
        assert ":root {" in css

    def test_config_path_property(self):
        path = Path("/custom/brand.yaml")
        loader = BrandVisualIdentityLoader(path)
        assert loader.config_path == path

    def test_default_config_path(self):
        loader = BrandVisualIdentityLoader()
        assert loader.config_path == Path("config/brand-visual.yaml")

    def test_load_themes_from_yaml(self):
        loader = BrandVisualIdentityLoader(_REPO_BRAND_CONFIG)
        brand = loader.load()

        assert len(brand.themes) == 5
        assert set(brand.themes) == {"dark", "light", "warm", "cool", "bold"}

    def test_load_theme_dark(self):
        loader = BrandVisualIdentityLoader(_REPO_BRAND_CONFIG)

        brand = loader.load_theme("dark")

        assert brand.colors.primary == "#6366F1"
        assert brand.colors.background == "#0A0F1E"

    def test_load_theme_warm(self):
        loader = BrandVisualIdentityLoader(_REPO_BRAND_CONFIG)

        brand = loader.load_theme("warm")

        assert brand.colors.primary == "#F59E0B"
        assert brand.colors.surface == "#2C1F1A"

    def test_load_theme_unknown(self):
        loader = BrandVisualIdentityLoader(_REPO_BRAND_CONFIG)

        brand = loader.load_theme("nonexistent")

        assert brand.colors.primary == "#6366F1"
        assert brand.colors.background == "#0A0F1E"

    def test_to_css_variables_with_theme(self):
        loader = BrandVisualIdentityLoader(_REPO_BRAND_CONFIG)

        css = loader.load().to_css_variables(theme_name="cool")

        assert "--brand-color-primary: #06B6D4;" in css
        assert "--brand-color-accent: #67E8F9;" in css

    def test_themes_inherit_typography(self):
        loader = BrandVisualIdentityLoader(_REPO_BRAND_CONFIG)

        brand = loader.load_theme("warm")

        assert brand.typography.primary_font == "Plus Jakarta Sans"
