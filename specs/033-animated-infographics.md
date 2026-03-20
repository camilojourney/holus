# Spec 033: Animated Infographic GIFs

**Status:** planned
**Phase:** Phase 2
**Author:** Juan (specialist deliberation + research)
**Created:** 2026-03-19
**Updated:** 2026-03-19
**Dependencies:** SPEC-010 (Marketing Agent), SPEC-031 (LinkedIn Pipeline)
**Research:** `docs/research/domain/animated-gif-generation.md`

## Problem

LinkedIn content that uses animated visuals (grid infographics, architecture diagrams, taxonomy charts) gets significantly higher engagement than static images. The "AI Agent System Guide" style — icons appearing sequentially, lines drawing in, text fading in — is a proven viral format. Holus currently produces text posts and static carousels. Adding animated GIF generation gives Holus a content type that very few competitors produce programmatically (most use Canva/After Effects manually).

Research finding: AI-generated text content gets 47% reach penalty on LinkedIn [VERIFIED]. Visual content, especially carousels (6.6-7.0% engagement rate) and animated infographics, is the highest-performing format.

## Goals

- Generate animated infographic GIFs from structured data (categories, items, icons, labels)
- Output: 1080x1080px, <5MB, <400 frames, auto-loops on LinkedIn
- Reuse Holus brand config (`brand-visual.yaml`) for colors, fonts, spacing
- New `ContentType.ANIMATED_INFOGRAPHIC` in the marketing agent's decision space
- End-to-end: strategist decides → layout generated → GIF rendered → queued for review → published
- Render time: <30 seconds per infographic on Mac Mini

## Non-Goals

- Video generation — Genpeli handles video. GIFs are image-class content, not video.
- Interactive infographics — GIF is non-interactive by design.
- AI image generation — no Pilaster/diffusion models. These are programmatic renders from structured data.
- Complex 3D animations — flat 2D design only (matches LinkedIn aesthetic).
- Custom icon creation — use existing icon libraries (Font Awesome, Lucide, or bundled SVG set).

## Solution

### Pipeline

```
Strategist REASON stage
  │  "This topic decomposes into 6+ categories → ANIMATED_INFOGRAPHIC"
  ▼
Layout Agent generates structured JSON:
  {
    "title": "AI Agent System Guide",
    "subtitle": "Open vs Closed",
    "rows": [
      {"category": "Foundation Models", "items": [
        {"name": "Llama 4", "icon": "llama"},
        {"name": "Claude", "icon": "brain"}
      ]},
      ...
    ],
    "style": "grid",
    "animation": "sequential"
  }
  │
  ▼
Infographic Renderer (Python/Pillow):
  1. Load brand config → colors, fonts, spacing
  2. Calculate grid layout → positions for each cell
  3. For each frame (10fps × 8-10 seconds):
     - Draw background
     - Draw elements visible at this timestamp
     - Apply easing (elements fade/slide/scale in)
  4. Save frames as PIL Images
  │
  ▼
GIF Encoder:
  - gifski stitches frames into high-quality GIF
  - gifsicle --lossy=80 -O3 compresses to <5MB
  - If >5MB after compression: reduce frame count or dimensions
  │
  ▼
Content Queue:
  - Queued as QueuedContent with media_type="gif"
  - Humanization step (SPEC-032) reviews text overlay
  - Published via social-media-automatization API
```

### Why Pillow, Not HTML/CSS + Puppeteer

Research found CSS animations don't capture reliably in headless Puppeteer (the `timecut` library only intercepts JS-driven animations, not CSS `@keyframes`). Pillow gives deterministic, frame-by-frame control with no browser dependency. Brand consistency is maintained by reading `brand-visual.yaml` directly in Python.

### Why GIF, Not MP4

- GIF uploaded as image: plays inline, loops forever, no player controls, no sound
- MP4 uploaded as video: shows video player, counts as "video post" (different algorithm)
- For infographics, the looping image format is more natural and less intrusive
- 5MB GIF limit is sufficient for 80-150 frames at 1080x1080 with flat colors
- No ffmpeg dependency needed

### Animation Types

| Style | What Animates | Use Case |
|-------|--------------|----------|
| `sequential` | Each item appears one at a time (left-to-right, top-to-bottom) | Taxonomy grids, tool lists |
| `row-by-row` | Each row appears together, rows appear sequentially | Category comparisons |
| `fade-all` | All items fade in simultaneously, then labels appear | Simple showcases |
| `build-up` | Bottom rows first, building upward | Stack/layer diagrams |

### Layout Styles

| Style | Description | Use Case |
|-------|------------|----------|
| `grid` | N×M uniform cells with icons + labels | Tool/technology lists |
| `comparison` | 2 columns (Open vs Closed, Before vs After) | Side-by-side |
| `flow` | Connected boxes with arrows | Process/pipeline diagrams |
| `timeline` | Horizontal or vertical timeline with nodes | Roadmaps, history |

## Technical Design

### New Files

```
src/holus/visual/
  infographic.py          # InfographicRenderer class
  infographic_layout.py   # Grid calculation, animation timing
  icon_registry.py        # Icon name → PIL Image mapping
  gif_encoder.py          # Frame stitching with gifski/gifsicle

assets/icons/             # Bundled SVG/PNG icon set (50-100 common icons)

tests/unit/visual/
  test_infographic.py
  test_gif_encoder.py
```

### ContentType Addition

```python
class ContentType(str, Enum):
    # existing...
    ANIMATED_INFOGRAPHIC = "animated_infographic"
```

### Specialist Pipeline

```python
PIPELINES["animated_infographic"] = [
    "hook-architect",
    "infographic-layout-architect",
    "brand-designer",
]
```

### Dependencies

```
gifski    # brew install gifski (Rust-based, highest quality GIF encoding)
gifsicle  # brew install gifsicle (C-based, GIF optimization/compression)
Pillow    # Already a dependency
cairosvg  # pip install cairosvg (SVG icon → PIL Image conversion)
```

### InfographicRenderer Interface

```python
class InfographicRenderer:
    def __init__(self, brand_config: BrandVisualIdentity):
        self.colors = brand_config.to_css_variables()
        self.icon_registry = IconRegistry()

    def render(self, layout: InfographicLayout) -> list[Image.Image]:
        """Generate list of PIL frames for the animation."""
        frames = []
        total_frames = int(layout.duration_sec * layout.fps)
        for frame_idx in range(total_frames):
            t = frame_idx / total_frames
            frame = self._draw_frame(layout, t)
            frames.append(frame)
        return frames

    def _draw_frame(self, layout: InfographicLayout, t: float) -> Image.Image:
        """Draw a single frame at normalized time t (0-1)."""
        img = Image.new("RGBA", (1080, 1080), layout.background_color)
        draw = ImageDraw.Draw(img)
        draw.text((540, 40), layout.title, font=self.title_font, anchor="mt")
        for item in layout.items:
            if t >= item.appear_at:
                alpha = min(1.0, (t - item.appear_at) / 0.05)
                self._draw_item(draw, item, alpha)
        return img
```

### LinkedIn Constraints

- Max file size: 5MB
- Max frames: 400 (posts), 500 (articles)
- Dimensions: 1080x1080px (square, best engagement)
- At 10fps: 400 frames = 40 seconds max
- GIFs auto-loop on LinkedIn feed
- LinkedIn may re-encode in some contexts — keep quality high

## Acceptance Criteria

- AC-033-001: Given a valid `InfographicLayout` JSON, when `InfographicRenderer.render()` is called, then it produces 80-150 PIL Image frames at 1080x1080
- AC-033-002: Given rendered frames, when `gif_encoder.encode()` is called, then the output GIF is <5MB and <400 frames
- AC-033-003: Given a topic that decomposes into 4+ categories, when the marketing strategist reasons, then it can choose `ANIMATED_INFOGRAPHIC` as content type
- AC-033-004: Given a generated GIF, when it is uploaded to LinkedIn via social-media API, then it plays inline and loops
- AC-033-005: Given the brand config, when an infographic is rendered, then colors/fonts match `brand-visual.yaml`
- AC-033-006: Given an icon name from the layout JSON, when the renderer draws it, then it loads from the bundled icon set (no external fetch)
- AC-033-007: Given a GIF >5MB before optimization, when gifsicle runs, then the output is <5MB (or dimensions are reduced as fallback)

## Out of Scope

- Carousel PDF generation (existing system handles this)
- Video with audio (Genpeli territory)
- Real-time preview in Observatory (future spec)
- Custom icon upload (use bundled set for now)

## Decisions

| Decision Point | Decision | Rationale | Vote |
|---------------|----------|-----------|------|
| `generation_approach` | Pillow frame-by-frame | CSS animations don't capture in Puppeteer. Pillow is deterministic. | Arch: A, Research: confirms |
| `output_format` | GIF (not MP4) | Loops inline as image. No video player UI. Better for infographics. | Perf: revised from B to GIF per user input |
| `icon_system` | Bundled SVG set + cairosvg | No runtime icon fetching. Deterministic. 50-100 common icons. | Sec: B (sanitized templates) |
| `encoding_pipeline` | gifski → gifsicle | gifski for quality (per-frame palettes), gifsicle for compression (30-50% reduction). No ffmpeg. | Research: confirmed best pipeline |
| `template_system` | Python layout + Pillow drawing | Not HTML. No browser dependency. Brand config loaded directly from YAML. | Arch: A adapted |
