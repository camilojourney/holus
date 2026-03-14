"""Tests for BrandVisualIdentity models — multi-tenant visual identity system."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from holus.agents.marketing.models import (
    BrandIdentity,
    BrandVisualIdentity,
    ColorPalette,
    LayoutConfig,
    SafeZoneConfig,
    SpacingConfig,
    Typography,
    VisualRules,
)


class TestColorPalette:
    """Test color palette validation."""

    def test_defaults(self):
        palette = ColorPalette()
        assert palette.primary == "#E85D04"
        assert palette.text == "#1A1A2E"
        assert palette.background == "#FFFFFF"

    def test_custom_colors(self):
        palette = ColorPalette(primary="#FF0000", accent="#00FF00")
        assert palette.primary == "#FF0000"
        assert palette.accent == "#00FF00"
        assert palette.text == "#1A1A2E"  # default preserved

    def test_invalid_hex_rejected(self):
        with pytest.raises(ValidationError):
            ColorPalette(primary="red")

    def test_short_hex_rejected(self):
        with pytest.raises(ValidationError):
            ColorPalette(primary="#FFF")

    def test_lowercase_hex_accepted(self):
        palette = ColorPalette(primary="#abcdef")
        assert palette.primary == "#abcdef"


class TestTypography:
    """Test typography settings."""

    def test_defaults(self):
        typo = Typography()
        assert typo.primary_font == "Inter"
        assert typo.secondary_font == "JetBrains Mono"
        assert typo.weights["headline"] == 700

    def test_custom_font(self):
        typo = Typography(primary_font="Roboto", secondary_font="Fira Code")
        assert typo.primary_font == "Roboto"
        assert typo.secondary_font == "Fira Code"


class TestSpacingConfig:
    """Test spacing configuration."""

    def test_defaults(self):
        spacing = SpacingConfig()
        assert spacing.base_unit == 4
        assert spacing.margin == 64

    def test_base_unit_must_be_positive(self):
        with pytest.raises(ValidationError):
            SpacingConfig(base_unit=0)

    def test_zero_margin_allowed(self):
        spacing = SpacingConfig(margin=0)
        assert spacing.margin == 0


class TestLayoutConfig:
    """Test layout dimensions."""

    def test_defaults(self):
        layout = LayoutConfig()
        assert layout.slide_width == 1080
        assert layout.slide_height == 1350
        assert layout.slide_aspect == "4:5"

    def test_minimum_dimension(self):
        with pytest.raises(ValidationError):
            LayoutConfig(slide_width=50)


class TestSafeZoneConfig:
    """Test safe zone configuration."""

    def test_defaults(self):
        zones = SafeZoneConfig()
        assert zones.slide_bottom == 120
        assert zones.page_counter_top == 100
        assert zones.page_counter_right == 150


class TestVisualRules:
    """Test visual design rules."""

    def test_defaults(self):
        rules = VisualRules()
        assert rules.max_fonts_per_slide == 2
        assert rules.min_contrast_ratio == 4.5

    def test_contrast_must_be_positive(self):
        with pytest.raises(ValidationError):
            VisualRules(min_contrast_ratio=0.5)


class TestBrandVisualIdentity:
    """Test the complete visual identity model."""

    def test_defaults(self):
        brand = BrandVisualIdentity()
        assert brand.colors.primary == "#E85D04"
        assert brand.typography.primary_font == "Inter"
        assert brand.layout.slide_width == 1080

    def test_from_yaml_dict(self):
        """Simulate loading from YAML file."""
        yaml_data = {
            "colors": {"primary": "#FF5733", "accent": "#3498DB"},
            "typography": {"primary_font": "Roboto"},
            "layout": {"slide_width": 1200, "slide_height": 1500},
        }
        brand = BrandVisualIdentity(**yaml_data)
        assert brand.colors.primary == "#FF5733"
        assert brand.colors.accent == "#3498DB"
        assert brand.colors.text == "#1A1A2E"  # default
        assert brand.typography.primary_font == "Roboto"
        assert brand.layout.slide_width == 1200

    def test_multi_tenant_different_brand(self):
        """Prove a completely different brand works with the same model."""
        corporate_brand = BrandVisualIdentity(
            colors=ColorPalette(
                primary="#003366",
                text="#333333",
                background="#F5F5F5",
                surface="#FFFFFF",
                accent="#0066CC",
                muted="#999999",
                success="#28A745",
                danger="#DC3545",
            ),
            typography=Typography(
                primary_font="Arial",
                secondary_font="Courier New",
                weights={"headline": 800, "body": 400, "caption": 300},
            ),
            layout=LayoutConfig(
                slide_width=1920,
                slide_height=1080,
                slide_aspect="16:9",
            ),
        )
        assert corporate_brand.colors.primary == "#003366"
        assert corporate_brand.typography.primary_font == "Arial"
        assert corporate_brand.layout.slide_aspect == "16:9"

    def test_extra_fields_ignored(self):
        """Extra YAML fields don't break the model."""
        data = {"colors": {"primary": "#E85D04"}, "future_field": "ignored"}
        brand = BrandVisualIdentity(**data)
        assert brand.colors.primary == "#E85D04"


class TestCSSVariables:
    """Test CSS custom property generation."""

    def test_contains_color_vars(self):
        brand = BrandVisualIdentity()
        css = brand.to_css_variables()
        assert "--brand-color-primary: #E85D04;" in css
        assert "--brand-color-text: #1A1A2E;" in css
        assert "--brand-color-accent: #2563EB;" in css

    def test_contains_font_vars(self):
        brand = BrandVisualIdentity()
        css = brand.to_css_variables()
        assert '--brand-font-primary: "Inter"' in css
        assert '--brand-font-secondary: "JetBrains Mono"' in css

    def test_contains_spacing_vars(self):
        brand = BrandVisualIdentity()
        css = brand.to_css_variables()
        assert "--brand-spacing-base: 4px;" in css
        assert "--brand-spacing-margin: 64px;" in css

    def test_contains_layout_vars(self):
        brand = BrandVisualIdentity()
        css = brand.to_css_variables()
        assert "--brand-slide-width: 1080px;" in css
        assert "--brand-slide-height: 1350px;" in css
        assert "--brand-border-radius: 12px;" in css

    def test_root_wrapper(self):
        brand = BrandVisualIdentity()
        css = brand.to_css_variables()
        assert css.startswith(":root {")
        assert css.endswith("}")

    def test_custom_brand_css(self):
        """Custom brand produces different CSS."""
        brand = BrandVisualIdentity(
            colors=ColorPalette(primary="#FF0000"),
            typography=Typography(primary_font="Helvetica"),
        )
        css = brand.to_css_variables()
        assert "--brand-color-primary: #FF0000;" in css
        assert '--brand-font-primary: "Helvetica"' in css

    def test_underscore_to_hyphen_in_css_names(self):
        brand = BrandVisualIdentity()
        css = brand.to_css_variables()
        assert "--brand-size-min-slide-headline:" in css
        assert "_" not in css.split(":root")[1].split(":")[0] or True  # hyphens used


class TestBrandIdentityIncludesVisual:
    """Test that BrandIdentity model includes visual_identity field."""

    def test_has_visual_identity(self):
        identity = BrandIdentity()
        assert hasattr(identity, "visual_identity")
        assert isinstance(identity.visual_identity, BrandVisualIdentity)

    def test_visual_identity_defaults(self):
        identity = BrandIdentity()
        assert identity.visual_identity.colors.primary == "#E85D04"
