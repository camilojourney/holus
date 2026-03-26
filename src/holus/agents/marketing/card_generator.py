"""LinkedIn post card generator — SPEC-035.

Renders styled text cards as PNG images using Playwright + HTML/CSS.
No external AI required — pure typography + brand colors.

Arm config maps to card styles:
  dark_gradient__large_headline__centered  → dark bg, big hook text, centered
  light_clean__body_heavy__split           → white bg, body text, left-aligned
  bold_color__minimal__asymmetric          → brand color, minimal, offset
  (any other arm)                          → default clean dark
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

# Card output dir
_CARDS_DIR = Path(__file__).parents[4] / "data" / "cards"

# Brand colors (from brand.yaml defaults)
_COLORS = {
    "dark": "#0a0a0a",
    "dark_surface": "#141414",
    "white": "#ffffff",
    "off_white": "#f0ede8",
    "accent": "#e8d5b7",      # warm gold
    "accent_2": "#c084fc",    # purple
    "text_muted": "#888888",
    "brand_blue": "#1a1a2e",
}

# Card dimensions (LinkedIn optimal: 1200x1200 for square)
_WIDTH = 1200
_HEIGHT = 1200


def _arm_to_style(arm_id: str) -> dict[str, str]:
    """Map arm id to CSS style config."""
    if "dark_gradient" in arm_id and "large_headline" in arm_id:
        return {
            "bg": f"linear-gradient(135deg, {_COLORS['dark']} 0%, {_COLORS['brand_blue']} 100%)",
            "text_color": _COLORS["white"],
            "accent_color": _COLORS["accent"],
            "font_size_hook": "52px",
            "font_size_body": "24px",
            "layout": "centered",
            "padding": "80px",
        }
    elif "light_clean" in arm_id and "body_heavy" in arm_id:
        return {
            "bg": _COLORS["off_white"],
            "text_color": _COLORS["dark"],
            "accent_color": _COLORS["brand_blue"],
            "font_size_hook": "38px",
            "font_size_body": "22px",
            "layout": "split",
            "padding": "80px",
        }
    elif "bold_color" in arm_id and "minimal" in arm_id:
        return {
            "bg": f"linear-gradient(160deg, {_COLORS['brand_blue']} 0%, #2d1b4e 100%)",
            "text_color": _COLORS["white"],
            "accent_color": _COLORS["accent_2"],
            "font_size_hook": "44px",
            "font_size_body": "22px",
            "layout": "asymmetric",
            "padding": "80px",
        }
    else:
        # Default clean dark
        return {
            "bg": _COLORS["dark_surface"],
            "text_color": _COLORS["white"],
            "accent_color": _COLORS["accent"],
            "font_size_hook": "42px",
            "font_size_body": "22px",
            "layout": "centered",
            "padding": "80px",
        }


def _render_html(hook: str, body_preview: str, arm_id: str, author: str = "Juan Martinez") -> str:
    """Generate HTML for a card."""
    style = _arm_to_style(arm_id)
    layout = style["layout"]
    pad = style["padding"]

    # Body preview — first 2 paragraphs max
    lines = [ln.strip() for ln in body_preview.split("\n") if ln.strip()][:4]
    body_html = "".join(f"<p>{ln}</p>" for ln in lines)

    # Layout-specific CSS
    if layout == "centered":
        content_css = """
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        """
        hook_css = f"font-size: {style['font_size_hook']}; text-align: center;"
    elif layout == "split":
        content_css = """
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        """
        hook_css = f"font-size: {style['font_size_hook']}; text-align: left; border-left: 6px solid {style['accent_color']}; padding-left: 32px;"
    else:  # asymmetric
        content_css = """
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
        """
        hook_css = f"font-size: {style['font_size_hook']}; text-align: left; margin-bottom: 40px;"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: {_WIDTH}px;
    height: {_HEIGHT}px;
    background: {style['bg']};
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: {style['text_color']};
    overflow: hidden;
  }}
  .card {{
    width: 100%;
    height: 100%;
    padding: {pad};
    {content_css}
  }}
  .hook {{
    {hook_css}
    font-weight: 800;
    line-height: 1.2;
    letter-spacing: -0.02em;
    color: {style['text_color']};
    margin-bottom: 40px;
  }}
  .body {{
    font-size: {style['font_size_body']};
    line-height: 1.7;
    color: {style['text_color']};
    opacity: 0.85;
    font-weight: 400;
    margin-bottom: 40px;
  }}
  .body p {{ margin-bottom: 16px; }}
  .footer {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: auto;
    padding-top: 40px;
    border-top: 1px solid rgba(255,255,255,0.15);
  }}
  .author {{
    font-size: 20px;
    font-weight: 600;
    color: {style['accent_color']};
  }}
  .dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {style['accent_color']};
  }}
  .linkedin {{
    font-size: 18px;
    opacity: 0.5;
    font-weight: 500;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="hook">{hook}</div>
  <div class="body">{body_html}</div>
  <div class="footer">
    <span class="author">{author}</span>
    <span class="dot"></span>
    <span class="linkedin">LinkedIn</span>
  </div>
</div>
</body>
</html>"""


def generate_cards(
    hook: str,
    body: str,
    arms: list[str],
    author: str = "Juan Martinez",
    output_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Generate PNG cards for each arm.

    Args:
        hook: The post hook text
        body: The post body text (first 2 paragraphs shown)
        arms: List of arm ids from bandit.select_arms()
        author: Author name for card footer
        output_dir: Where to save PNGs (default: data/cards/)

    Returns:
        List of dicts: [{arm_id, path, variant}]
    """
    from playwright.sync_api import sync_playwright

    out_dir = output_dir or _CARDS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Stable filename based on content hash
    content_hash = hashlib.md5(f"{hook}{body}".encode()).hexdigest()[:8]

    results = []
    variants = ["A", "B", "C"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": _WIDTH, "height": _HEIGHT})

        for i, arm_id in enumerate(arms):
            variant = variants[i] if i < len(variants) else f"V{i+1}"
            html = _render_html(hook, body, arm_id, author)

            # Write HTML to temp file
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
                f.write(html)
                tmp_path = f.name

            page.goto(f"file://{tmp_path}")
            page.wait_for_timeout(500)  # let fonts load

            out_path = out_dir / f"card-{content_hash}-{variant}.png"
            page.screenshot(path=str(out_path), full_page=False)

            Path(tmp_path).unlink(missing_ok=True)

            results.append({
                "arm_id": arm_id,
                "path": str(out_path),
                "variant": variant,
            })

        browser.close()

    return results
