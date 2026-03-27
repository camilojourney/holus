"""CSS gradient generation and presets for slide backgrounds."""

from __future__ import annotations


def linear_gradient(angle: int, stops: list[tuple[str, int]]) -> str:
    """Generate a CSS linear-gradient string."""
    stop_strs = [f"{color} {pct}%" for color, pct in stops]
    return f"linear-gradient({angle}deg, {', '.join(stop_strs)})"


def radial_gradient(position: str, stops: list[tuple[str, int]]) -> str:
    """Generate a CSS radial-gradient string."""
    stop_strs = [f"{color} {pct}%" for color, pct in stops]
    return f"radial-gradient(circle at {position}, {', '.join(stop_strs)})"


def mesh_gradient(blobs: list[dict[str, object]]) -> str:
    """Generate a mesh-style gradient from layered radials."""
    layers = []
    for blob in blobs:
        x, y = blob["x"], blob["y"]
        color = blob["color"]
        spread = blob.get("spread", 50)
        layers.append(f"radial-gradient(circle at {x}% {y}%, {color} 0%, transparent {spread}%)")
    return ", ".join(layers)


GRADIENT_PRESETS: dict[str, str] = {
    "dark_navy": linear_gradient(135, [("#0A0F1E", 0), ("#1e1b4b", 100)]),
    "indigo_mesh": mesh_gradient(
        [
            {"x": 20, "y": 30, "color": "rgba(99,102,241,0.3)", "spread": 60},
            {"x": 80, "y": 70, "color": "rgba(165,180,252,0.2)", "spread": 50},
        ]
    ),
    "warm_sunset": linear_gradient(135, [("#1C1310", 0), ("#78350f", 50), ("#92400E", 100)]),
    "cool_ocean": linear_gradient(180, [("#0C1222", 0), ("#164e63", 100)]),
    "bold_fire": linear_gradient(135, [("#18181B", 0), ("#7f1d1d", 100)]),
    "frosted_glass": "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)",
    "aurora": mesh_gradient(
        [
            {"x": 30, "y": 20, "color": "rgba(6,182,212,0.25)", "spread": 55},
            {"x": 70, "y": 80, "color": "rgba(168,85,247,0.2)", "spread": 50},
            {"x": 50, "y": 50, "color": "rgba(99,102,241,0.15)", "spread": 45},
        ]
    ),
    "minimal_light": linear_gradient(180, [("#FAFAFA", 0), ("#F1F5F9", 100)]),
}


def resolve_gradient(name_or_css: str) -> str:
    """Resolve a preset name to CSS, or return raw CSS if not a preset."""
    return GRADIENT_PRESETS.get(name_or_css, name_or_css)
