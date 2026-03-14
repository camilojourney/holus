"""Visual rendering package for branded social media content.

Provides Playwright-based rendering of Jinja2 templates into PNG/PDF,
with brand identity injection from config/brand-visual.yaml.
"""

from holus.visual.brand import BrandVisualIdentityLoader
from holus.visual.engine import PlaywrightEngine
from holus.visual.models import CarouselSpec, RenderResult, RenderSpec, SlideSpec
from holus.visual.templates import TemplateEngine

__all__ = [
    "BrandVisualIdentityLoader",
    "CarouselSpec",
    "PlaywrightEngine",
    "RenderResult",
    "RenderSpec",
    "SlideSpec",
    "TemplateEngine",
]
