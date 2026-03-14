"""Jinja2 template engine with brand CSS injection.

Loads templates from the ``templates/`` directory within this package,
renders them with variables, and injects brand CSS custom properties
into the HTML ``<head>``.
"""

from __future__ import annotations

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

        brand = self._brand_loader.load()
        brand_css = brand.to_css_variables()

        # Load style files
        base_css = self._load_style("base.css")
        # Determine which supplementary CSS to load based on template path
        supplementary_css = ""
        if template_name.startswith("carousel/"):
            supplementary_css = self._load_style("slide.css") + "\n" + self._load_style("carousel.css")
        elif template_name.startswith("single_image/"):
            supplementary_css = self._load_style("single.css")

        context: dict[str, str | int | float | bool | list[str]] = {
            "brand_css": brand_css,
            "base_css": base_css,
            "supplementary_css": supplementary_css,
            **(variables or {}),
        }

        return template.render(context)

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
