"""Tests for gradient generation and presets."""

from holus.visual.gradients import (
    GRADIENT_PRESETS,
    linear_gradient,
    mesh_gradient,
    radial_gradient,
    resolve_gradient,
)


class TestLinearGradient:
    def test_basic(self):
        result = linear_gradient(135, [("#000", 0), ("#fff", 100)])
        assert result.startswith("linear-gradient(135deg,")
        assert "#000 0%" in result
        assert "#fff 100%" in result

    def test_three_stops(self):
        result = linear_gradient(90, [("#a", 0), ("#b", 50), ("#c", 100)])
        assert result.count("%") == 3


class TestRadialGradient:
    def test_basic(self):
        result = radial_gradient("50% 50%", [("#000", 0), ("#fff", 100)])
        assert result.startswith("radial-gradient(circle at 50% 50%,")


class TestMeshGradient:
    def test_basic(self):
        blobs = [
            {"x": 20, "y": 30, "color": "rgba(0,0,0,0.5)", "spread": 60},
            {"x": 80, "y": 70, "color": "rgba(255,255,255,0.3)", "spread": 50},
        ]
        result = mesh_gradient(blobs)
        assert "radial-gradient" in result
        assert result.count("radial-gradient") == 2


class TestPresets:
    def test_all_presets_are_strings(self):
        for name, value in GRADIENT_PRESETS.items():
            assert isinstance(value, str), f"Preset '{name}' is not a string"

    def test_preset_count(self):
        assert len(GRADIENT_PRESETS) >= 8


class TestResolveGradient:
    def test_preset_name(self):
        result = resolve_gradient("warm_sunset")
        assert "linear-gradient" in result

    def test_raw_css_passthrough(self):
        raw = "linear-gradient(45deg, red, blue)"
        assert resolve_gradient(raw) == raw

    def test_unknown_name_passthrough(self):
        assert resolve_gradient("nonexistent") == "nonexistent"
