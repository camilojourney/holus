# SPEC-033: Animated Infographic Content Generation

**Status:** Not Started
**Priority:** P1 — LinkedIn carousels get 6.6-7.0% engagement; animated content stops the scroll
**Dependencies:** SPEC-031 (LinkedIn Pipeline), SPEC-032 (Humanization Gate)
**Research:** `docs/research/domain/linkedin-posting-frequency.md`
**Spec CID:** holus-SPECS-20260319-d1ecfc56
**Specialist input:** arch (A), perf (B), sec (B) — see `.pipeline-state/` artifacts

---

## Problem

Holus currently generates text-only LinkedIn posts. The research shows:
- PDF carousels get **6.6-7.0% engagement rate** (highest of any format)
- Animated/video content autoplays in feed, stopping the scroll
- Static infographics (like the "AI Agent System Guide" grid) are shared heavily
- But animated versions where elements appear sequentially (lines draw, icons pop in, text fades) perform even better

Holus needs to generate structured visual content — animated infographics as short MP4s — not just text.

## Solution

Add an **animated infographic pipeline** to Holus. The LLM generates a structured JSON spec (grid layout, categories, items, icons). Pre-built HTML/CSS templates with `@keyframes` animations render the visual. Puppeteer captures frames. ffmpeg encodes to MP4.

This lives **in Holus** (not Pilaster or Genpeli) because it's programmatic rendering of structured data, not AI image generation or video editing.

## Pipeline

```
Holus REASON step decides: "this topic needs an infographic"
  │
  ▼
LLM generates structured JSON:
  { "title": "AI Agent System Guide",
    "categories": [
      { "name": "Foundation Models", "items": ["Phi-4", "DeepSeek", "Claude", "Gemini"] },
      { "name": "Agent Frameworks", "items": ["LangGraph", "CrewAI", "AutoGen"] },
      ...
    ],
    "style": "grid",
    "animation": "sequential-reveal"
  }
  │
  ▼
Template engine renders HTML/CSS with @keyframes animations
  │
  ▼
Puppeteer captures frames (30fps × 5-10 seconds = 150-300 frames)
  │
  ▼
ffmpeg encodes to MP4 (H.264, 1080x1080 or 1080x1350)
  │
  ▼
Content queued with media_type="video" + platform="linkedin"
```

## Decisions

### DECISION 1: Generation Approach
**Options:** A) HTML/CSS + Puppeteer B) Python animation (manim) C) Pilaster static + Genpeli animate D) New service
**Decision:** **A — HTML/CSS + Puppeteer frame capture**
**Rationale (arch):** Reuses existing carousel rendering pipeline (`BrandVisualIdentity.to_css_variables()`). HTML/CSS animations are declarative and easy to template. Puppeteer is already a dependency (Observatory frontend). No new silo needed.

### DECISION 2: Output Format
**Options:** A) Animated GIF B) Short MP4 C) Both
**Decision:** **B — Short MP4**
**Rationale (perf):** MP4 is 5-20x smaller than GIF for same quality. LinkedIn autoplays MP4 in feed. No 256-color limitation. Better algorithmic distribution. Store individual frames as PNG for debugging and static fallback.

### DECISION 3: Template System
**Options:** A) Hardcoded Python B) HTML/CSS with Jinja2 autoescape C) LLM generates SVG directly
**Decision:** **B — HTML/CSS templates with sanitized injection**
**Rationale (sec):** LLM fills template slots with text content; never controls HTML/CSS structure. Brand colors/fonts/spacing from existing config. Icon names validated against whitelist. Jinja2 autoescape prevents injection.

## Implementation

### 1. New ContentType

Add `ANIMATED_INFOGRAPHIC` to the `ContentType` enum in `models.py`.

### 2. Infographic JSON Schema

```python
class InfographicItem(BaseModel):
    name: str
    icon: str | None = None  # validated against icon whitelist
    color: str | None = None  # defaults to brand color

class InfographicCategory(BaseModel):
    name: str
    items: list[InfographicItem]

class InfographicSpec(BaseModel):
    title: str
    subtitle: str | None = None
    categories: list[InfographicCategory]
    style: Literal["grid", "timeline", "comparison", "hierarchy"] = "grid"
    animation: Literal["sequential-reveal", "fade-in", "slide-in", "draw-lines"] = "sequential-reveal"
    dimensions: tuple[int, int] = (1080, 1350)  # LinkedIn portrait
    duration_seconds: float = 8.0
    fps: int = 30
```

### 3. Template Engine (`src/holus/visual/infographic_engine.py`)

```python
async def render_infographic(spec: InfographicSpec, brand: BrandVisualIdentity) -> Path:
    """Render animated infographic to MP4.

    1. Load HTML template for spec.style
    2. Inject brand CSS variables
    3. Inject category/item data via Jinja2 (autoescaped)
    4. Launch Puppeteer, set viewport to spec.dimensions
    5. Capture frames at spec.fps for spec.duration_seconds
    6. Encode to MP4 via ffmpeg (H.264, CRF 23)
    7. Return path to output MP4
    """
```

### 4. HTML Templates (`src/holus/visual/templates/`)

```
templates/
  grid.html          — icon grid (like "AI Agent System Guide")
  timeline.html      — horizontal timeline with milestones
  comparison.html    — side-by-side (like "Claude vs Gemini")
  hierarchy.html     — tree/org-chart structure
  _base.html         — shared: brand vars, fonts, animation keyframes
  _animations.css    — @keyframes: reveal, fade, slide, draw-line
```

Each template:
- Receives `categories`, `title`, `brand_css` via Jinja2
- Uses CSS `@keyframes` with `animation-delay` for sequential reveal
- Responsive within the fixed viewport (no media queries needed)

### 5. Icon Whitelist

Validate icon names against a known set (Lucide icons, already used in Observatory). Reject unknown icons to prevent template injection.

### 6. Integration with Marketing Agent

In the REASON step, when Holus decides content type:
```python
if topic_needs_visual and data_is_structured:
    decision.content_type = ContentType.ANIMATED_INFOGRAPHIC
    decision.infographic_spec = InfographicSpec(
        title="...",
        categories=[...],
        style="grid",
    )
```

In the ACT step:
```python
if decision.content_type == ContentType.ANIMATED_INFOGRAPHIC:
    mp4_path = await render_infographic(decision.infographic_spec, brand)
    # Upload to R2, get URL
    # Queue with media_url and media_type="video"
```

## Acceptance Criteria

### AC-033-001: Infographic renders to MP4
**Priority:** P0
**Given** an InfographicSpec with 5 categories and 20 items
**When** `render_infographic()` is called
**Then** an MP4 file is produced at the specified dimensions, under 5MB, duration within 1s of spec

### AC-033-002: Sequential reveal animation works
**Priority:** P0
**Given** an InfographicSpec with `animation="sequential-reveal"`
**When** rendered
**Then** frame 1 shows only the title, frame 60 shows first category, frame 120 shows second category (items appear sequentially)

### AC-033-003: Grid template renders correctly
**Priority:** P0
**Given** 8 categories with 4-6 items each
**When** rendered with `style="grid"`
**Then** items are arranged in a grid matching the icon/label layout, no overlapping text, all items visible

### AC-033-004: Brand colors applied
**Priority:** P1
**Given** a BrandVisualIdentity with custom colors
**When** infographic is rendered
**Then** background, text, and accent colors match the brand config (not hardcoded)

### AC-033-005: Icon whitelist enforced
**Priority:** P1
**Given** an InfographicSpec with `icon="<script>alert(1)</script>"`
**When** validated
**Then** validation rejects the spec with a clear error

### AC-033-006: Static fallback generated
**Priority:** P2
**Given** a rendered infographic
**When** MP4 encoding completes
**Then** the final frame is also saved as a PNG for platforms that don't support video

### AC-033-007: Content queued with correct media_type
**Priority:** P0
**Given** a rendered infographic MP4
**When** queued via content_queue
**Then** `media_type="video"` and `media_url` points to the uploaded file

## Out of Scope

- Interactive infographics (HTML embeds) — LinkedIn doesn't support them
- User-designed templates (custom HTML) — security risk, use pre-built templates only
- Real-time data infographics (live metrics) — future iteration
- Carousel PDF generation — already handled by existing carousel pipeline
- Audio/narration on infographics — use Genpeli for video with audio

## Dependencies

- **Puppeteer** (or Playwright) — frame capture. Already available (Observatory frontend uses it).
- **ffmpeg** — MP4 encoding. Already available (Genpeli uses it).
- **Jinja2** — template rendering. Already a dependency.
- **Lucide icons** — icon set. Already used in Observatory.
