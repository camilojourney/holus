"""Jinja2 template engine with brand CSS injection.

Loads templates from the ``templates/`` directory within this package,
renders them with variables, and injects brand CSS custom properties
into the HTML ``<head>``.
"""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from holus.visual.brand import BrandVisualIdentityLoader

# Template directory lives alongside this module
_TEMPLATES_DIR = Path(__file__).parent / "templates"
_STYLES_DIR = Path(__file__).parent / "styles"


class TemplateEngine:
    """Jinja2 template loader with brand CSS injection.

    Usage::

        engine = TemplateEngine()
        html = engine.render("single_image/insight", {"headline": "Hello", "body": "World"})

    Templates are resolved as ``<name>.html.j2`` within the templates directory.
    Brand CSS variables are automatically injected via the ``brand_css`` template variable.
    """

    def __init__(
        self,
        templates_dir: Path | None = None,
        styles_dir: Path | None = None,
        brand_loader: BrandVisualIdentityLoader | None = None,
    ) -> None:
        self._templates_dir = templates_dir or _TEMPLATES_DIR
        self._styles_dir = styles_dir or _STYLES_DIR
        self._brand_loader = brand_loader or BrandVisualIdentityLoader()

        self._env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(["html", "j2"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        template_name: str,
        variables: dict[str, str | int | float | bool | list[str]] | None = None,
    ) -> str:
        """Render a template with brand CSS injection.

        Args:
            template_name: Template path without extension, e.g. ``"single_image/insight"``.
            variables: Template variables to inject.

        Returns:
            Complete HTML string with brand CSS variables embedded.
        """
        template_path = f"{template_name}.html.j2"
        template = self._env.get_template(template_path)
        normalized_variables = self._normalize_variables(template_name, variables)

        brand = self._brand_loader.load()
        brand_css = brand.to_css_variables()

        # Load style files
        base_css = self._load_style("base.css")
        # Determine which supplementary CSS to load based on template path
        supplementary_css = ""
        if template_name.startswith("carousel/"):
            supplementary_css = (
                self._load_style("slide.css") + "\n" + self._load_style("carousel.css")
            )
        elif template_name.startswith("single_image/"):
            supplementary_css = self._load_style("single.css")

        context: dict[str, str | int | float | bool | list[str]] = {
            "brand_css": brand_css,
            "base_css": base_css,
            "supplementary_css": supplementary_css,
            **normalized_variables,
        }

        html = template.render(context)
        return self._post_process_html(template_name, html, normalized_variables)

    def _load_style(self, filename: str) -> str:
        """Load a CSS file from the styles directory, returning empty string if missing."""
        style_path = self._styles_dir / filename
        if not style_path.exists():
            return ""
        return style_path.read_text(encoding="utf-8")

    def list_templates(self) -> list[str]:
        """List all available template names (without .html.j2 extension)."""
        templates: list[str] = []
        for path in self._templates_dir.rglob("*.html.j2"):
            relative = path.relative_to(self._templates_dir)
            name = str(relative).removesuffix(".html.j2")
            templates.append(name)
        return sorted(templates)

    def list_available_styles(self) -> list[str]:
        """List all available style names (without .css extension)."""
        styles: list[str] = []
        for path in self._styles_dir.rglob("*.css"):
            relative = path.relative_to(self._styles_dir)
            name = str(relative).removesuffix(".css")
            styles.append(name)
        return sorted(styles)

    def _normalize_variables(
        self,
        template_name: str,
        variables: dict[str, str | int | float | bool | list[str]] | None,
    ) -> dict[str, str | int | float | bool | list[str]]:
        normalized_variables = dict(variables or {})

        if template_name == "carousel/body_slide":
            if "body" not in normalized_variables and "body_text" in normalized_variables:
                normalized_variables["body"] = normalized_variables["body_text"]
            if "bullet_points" not in normalized_variables and "bullets" in normalized_variables:
                normalized_variables["bullet_points"] = normalized_variables["bullets"]

        return normalized_variables

    def _post_process_html(
        self,
        template_name: str,
        html: str,
        variables: dict[str, str | int | float | bool | list[str]],
    ) -> str:
        if template_name in {"carousel/body_slide", "carousel/summary_slide"}:
            html = self._append_class(html, "slide-title", "slide-headline")

        if template_name.startswith("carousel/"):
            slide_number = self._coerce_positive_int(variables.get("slide_number"), default=1)
            total_slides = self._coerce_positive_int(variables.get("total_slides"), default=1)
            html = self._inject_slide_progress(
                html, slide_number=slide_number, total_slides=total_slides
            )

        return html

    def _append_class(self, html: str, existing_class: str, added_class: str) -> str:
        pattern = re.compile(rf'class="([^"]*\b{re.escape(existing_class)}\b[^"]*)"')

        def replace(match: re.Match[str]) -> str:
            classes = match.group(1).split()
            if added_class not in classes:
                classes.append(added_class)
            return f'class="{" ".join(classes)}"'

        return pattern.sub(replace, html, count=1)

    def _inject_slide_progress(self, html: str, slide_number: int, total_slides: int) -> str:
        if 'class="slide-progress"' in html:
            return html

        current_slide = min(max(slide_number, 1), total_slides)
        dots = []
        for index in range(1, total_slides + 1):
            classes = (
                "slide-progress-dot is-active" if index == current_slide else "slide-progress-dot"
            )
            dots.append(f'<span class="{classes}"></span>')

        progress_html = f'<span class="slide-progress" aria-hidden="true">{"".join(dots)}</span>'
        return html.replace(
            '<span class="slide-counter">',
            f'{progress_html}\n    <span class="slide-counter">',
            1,
        )

    def _coerce_positive_int(
        self,
        value: str | int | float | bool | list[str] | None,
        *,
        default: int,
    ) -> int:
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return default
