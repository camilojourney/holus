---
title: Carousel/PDF Design Variables
domain: visual-content
owner: holus-research
last_updated: 2026-03-16
review_cadence: 60
next_review: 2026-05-15
---

## Content Type Variables — Carousel

### Carousel/PDF Design Variables

LinkedIn carousels are uploaded as multi-page PDF documents. Native image-based carousels were removed in late 2023. [VERIFIED]

**Cross-platform note:** Instagram carousels use image-based slides (up to 20 images per post), not PDFs. However, the **design tooling is the same** — the same Playwright HTML-to-image render pipeline produces both:
- **LinkedIn:** Render all slides → combine into one multi-page PDF → upload as document post.
- **Instagram:** Render each slide → export as individual PNGs → upload as multi-image post.

The slide templates, typography, color system, and layout variables are shared. Only the **output format** and **safe zones** differ (Instagram has no page counter overlay, but has a swipe indicator at the bottom). The `PlaywrightEngine` already supports both `render_carousel_pdf()` (LinkedIn) and `render_carousel()` → individual PNGs (Instagram). [VERIFIED — implemented in holus visual pipeline]

### 1. Canvas & Dimensions

| Variable | Options | Notes |
|----------|---------|-------|
| **Aspect ratio** | 1:1 (1080x1080), 4:5 (1080x1350), 16:9 (1920x1080) | 4:5 maximizes mobile screen real estate [VERIFIED] |
| **Max file size** | 100 MB | LinkedIn hard limit [VERIFIED] |
| **Max pages** | 300 | LinkedIn hard limit [VERIFIED] |
| **Optimal slide count** | 6-12 slides | Best practice for engagement [VERIFIED, MEDIUM confidence] |
| **Safe zone** | ~60-80px from edges | Avoids LinkedIn UI overlap [UNVERIFIED -- principle sound, exact pixels lack primary source] |

Source: expandi.io (2024-02-27), ligosocial.com (2024-01-10), carouselli.com (2024-03-05), postiv.ai (2024-05-15)

### 2. Color Palette Variables

| Variable | Options | Source |
|----------|---------|--------|
| **Palette scheme** | Monochromatic, Analogous, Complementary, Triadic, Split-complementary | Color theory fundamentals [VERIFIED] |
| **Distribution rule** | 60% primary/background, 30% secondary, 10% accent | 60-30-10 rule [VERIFIED] |
| **Background type** | Solid, gradient (linear/radial/angular), texture, pattern, image | Standard design options |
| **Gradient direction** | Top-to-bottom, left-to-right, diagonal, radial center | CSS/SVG gradient parameters |
| **Brand color lock** | Primary brand color always used; accent varies per slide | Brand consistency principle |

Source: canva.com/learn (2023-08-29), interaction-design.org (2024-03-01), adobe.com (2023-09-12)

### 3. Typography Variables

| Variable | Options | Source |
|----------|---------|--------|
| **Heading font classification** | Serif (Old Style, Transitional, Modern, Slab), Sans-Serif (Grotesque, Geometric, Humanist), Display | Standard taxonomy [VERIFIED] |
| **Body font classification** | Sans-Serif (readability on screens), Serif (authority feel) | Pairing principles [VERIFIED] |
| **Pairing strategy** | Contrast (Serif head + Sans body), Superfamily (e.g., IBM Plex), Weight contrast (same family, bold+light) | Typography best practices [VERIFIED] |
| **Type scale ratio** | Perfect Fourth (1.333), Major Third (1.250), Minor Third (1.200), Golden Ratio (1.618) | type-scale.com [VERIFIED] |
| **Minimum body size** | 24pt on 1080px canvas | Readability guideline [VERIFIED, MEDIUM] |
| **Text alignment** | Left, Center, Right | Per-element control |
| **Letter spacing** | Tight (-2%), Normal (0%), Wide (+5%), Extra-wide (+10%) | Design token variable |
| **Line height** | Tight (1.2), Normal (1.5), Relaxed (1.8) | Design token variable |

Source: type-scale.com, Google Fonts classification, Typewolf pairings

### 4. Layout & Composition Variables

| Variable | Options | Source |
|----------|---------|--------|
| **Grid system** | Rule of Thirds (3x3), Modular (4x4, 6x6), Golden Ratio, Asymmetric | Composition fundamentals [VERIFIED] |
| **Reading pattern** | Z-Pattern (simple layouts), F-Pattern (text-heavy), Gutenberg Diagram | UX scanning patterns [VERIFIED] |
| **Content zones** | Header (top 20%), Body (middle 60%), Footer/CTA (bottom 20%) | Standard slide structure |
| **Whitespace strategy** | Minimal (10% padding), Standard (15%), Generous (25%), Extreme (35%+) | Design density options |
| **Element alignment** | Grid-snapped, Free-form, Center-weighted | Layout discipline |

### 5. Slide Structure Patterns

| Pattern | Structure | Use Case |
|---------|-----------|----------|
| **Cover + Content + CTA** | Slide 1: hook title. Slides 2-N: content. Last slide: CTA | Standard educational carousel |
| **Numbered List** | Each slide = one numbered point with supporting visual | Listicle-style content |
| **Before/After** | Alternating slides showing transformation | Case studies, tutorials |
| **Story Arc** | Setup -> Conflict -> Resolution -> Takeaway -> CTA | Narrative carousels |
| **Data Walk** | Each slide reveals one metric/chart with context | Data-driven authority content |
| **Quote Spotlight** | Large quote + attribution per slide | Thought leadership |

### 6. Visual Elements

| Variable | Options | Source |
|----------|---------|--------|
| **Dividers** | Line (solid, dashed, dotted), Gradient bar, Icon divider, Whitespace only | Layout elements |
| **Icons** | Google Material Symbols (4 axes: Fill, Weight, Grade, Optical Size), Lucide (stroke width/color), Phosphor, Heroicons | [VERIFIED] -- parameterizable icon systems |
| **Illustrations** | Blush.design (parameterizable pose/color/background), unDraw, Storyset | [VERIFIED] -- Blush PRIMARY source |
| **Shapes** | Rectangles (border-radius: 0 to full-round), Circles, Blobs, Custom SVG | Standard shape parameters |
| **Borders** | None, Thin (1px), Medium (2px), Thick (4px); Solid, Dashed | Border token variables |
| **Shadows** | None, Subtle (2px blur), Medium (8px), Dramatic (16px+) | Elevation system |
| **Textures/Overlays** | Noise (grain), Halftone, Paper, Geometric patterns, None | Background treatment |

### 7. Brand Element Positioning

| Variable | Options |
|----------|---------|
| **Logo position** | Top-left, Top-right, Bottom-left, Bottom-right, Center-footer |
| **Logo size** | Small (5% canvas), Medium (8%), Large (12%) |
| **Handle/URL** | Included on every slide, first+last only, last slide only |
| **Slide numbering** | Visible (corner dots, fraction "3/10"), Hidden |
| **CTA placement** | Bottom-center (Z-pattern terminal), Bottom-right, Full-slide CTA |
| **CTA style** | Button (pill, rectangle, ghost), Text-only, Arrow+text |

### 8. Programmatic Generation Tools

| Tool | Approach | Variables Exposed | Source |
|------|----------|-------------------|--------|
| **Satori** (Vercel) | JSX/HTML+CSS -> SVG | Every CSS property = a variable | github.com/vercel/satori [VERIFIED] |
| **react-pdf** | React components -> PDF | Component props = variables | React ecosystem [VERIFIED] |
| **Canva Bulk Create** | CSV data -> design elements | Tagged text/image slots | canva.com [VERIFIED] |
| **Canva Connect API** | Autofill tagged templates | text, image (asset_id), chart data | canva.com/developers [VERIFIED] |
| **Adobe Doc Gen API** | JSON -> tagged Word/PDF template | JSON key-value pairs | developer.adobe.com [VERIFIED] |
| **Polotno.js** | Canvas as JSON object | Every element property (x, y, fill, fontSize, opacity, etc.) | polotno.com [VERIFIED] |

### 9. Cross-Platform Rendering

The design variables above (color, typography, layout, visual elements, slide structure) are **platform-agnostic**. The same Tool Registry serves every platform that uses swipeable multi-slide content -- the only thing that changes is how the final artifact is rendered and delivered.

| Platform | Delivery Format | Dimensions | Rendering Difference |
|----------|----------------|------------|---------------------|
| **LinkedIn** | PDF upload (document post) | 1080x1350 (4:5) or 1080x1080 (1:1) | Each PDF page = one slide. Playwright renders HTML -> multi-page PDF. LinkedIn's viewer adds page counter. |
| **Instagram** | Image carousel (up to 20 images) | 1080x1350 (4:5) or 1080x1080 (1:1) | Each slide = separate PNG/JPEG. Same HTML templates, rendered as individual screenshots instead of combined PDF. |
| **Instagram Stories/Reels** | Image sequence or video | 1080x1920 (9:16) | Same slide content, different aspect ratio + safe zones for story UI elements. |
| **Twitter/X** | Image carousel (up to 4 images) | 1200x675 (16:9) or 1080x1080 (1:1) | Max 4 slides -- condense content. Same templates, different page count constraint. |

**What stays the same across platforms:**
- Slide content (headlines, body text, bullets, takeaways)
- Color palettes, typography pairings, visual elements
- Slide structure patterns (hook -> body -> summary -> CTA)
- Brand positioning (logo, handles, CTA style)

**What changes per platform:**
- Output format: PDF (LinkedIn) vs PNG sequence (Instagram) vs JPEG (Twitter)
- Aspect ratio and safe zones
- Max slide count (LinkedIn: 300, Instagram: 20, Twitter: 4)
- Platform-specific UI overlays to avoid (LinkedIn page counter, IG story UI, Twitter crop zones)

The Playwright engine already supports both `render_carousel_pdf()` (LinkedIn) and `render_carousel()` -> individual PNGs (Instagram/Twitter). The same `CarouselSpec` feeds both renderers -- only the output method differs.

### Total Controllable Variables: Carousel

**Minimum (template-based):** ~25 variables (palette, fonts, content slots, logo position, CTA)
**Maximum (programmatic):** 60+ independent design axes across color (6), typography (8), layout (5), slide structure (6 patterns), visual elements (7 categories x 4+ options each), brand positioning (6), plus per-slide content variables.

**Combinatorial space** (conservative): 6 palettes x 4 type scales x 3 grids x 6 structures x 4 whitespace x 5 icon styles x 4 CTA styles x 5 logo positions = **~86,400 unique combinations** from just 8 axes.

### Carousel Sources

1. https://expandi.io/blog/linkedin-carousel-posts/ -- 2024-02-27
2. https://www.ligosocial.com/blog/linkedin-carousel-post-complete-guide -- 2024-01-10
3. https://carouselli.com/linkedin-carousel-post-guide-examples/ -- 2024-03-05
4. https://postiv.ai/linkedin-carousel-dimensions/ -- 2024-05-15
5. https://postnitro.ai/blog/linkedin-carousel-design -- 2024-04-22
6. https://www.canva.com/learn/60-30-10-rule/ -- 2023-08-29
7. https://type-scale.com -- 2024
8. https://github.com/vercel/satori -- 2024
9. https://developer.adobe.com/document-services/docs/overview/document-generation-api/ -- 2024-03-12
10. https://www.canva.com/developers/docs/connect-api/autofill/ -- 2024
11. https://polotno.com/docs/store-overview -- 2024

---
