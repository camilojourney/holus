---
title: Content Type Variables — Domain Research
domain: visual-content
owner: holus-research
last_updated: 2026-03-15
review_cadence: 60
next_review: 2026-05-14
---

# Domain Research — Content Type Variables

Domain-specific research for Holus's content creation pipeline. Covers design variables, specifications, and combinatorial spaces for each content type.

---

## Content Type Variables — Carousel

### Carousel/PDF Design Variables for LinkedIn

LinkedIn carousels are uploaded as multi-page PDF documents. Native image-based carousels were removed in late 2023. [VERIFIED]

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

## Content Type Variables — Image

### Image Post Design Variables for LinkedIn

### 1. Dimensions & Format

| Variable | Options | Notes |
|----------|---------|-------|
| **Aspect ratio** | 1:1 (1080-1200px square), 4:5 (1080x1350), 1.91:1 (1200x627 link preview), 16:9 (1920x1080 landscape) | 4:5 maximizes mobile; 1.91:1 for Open Graph link cards [VERIFIED] |
| **Image count** | 1 (single), 2-9 (multi-image carousel/gallery), 20 (max) | Consistent aspect ratio across multi-image is critical [VERIFIED] |
| **File format** | PNG (graphics/text), JPEG (photos), WebP | PNG for sharp text, JPEG for photos |
| **Resolution** | 1x (1080px), 2x (2160px for retina) | Higher res for quality on high-DPI screens |

Source: Multiple marketing guides (2024), LinkedIn help center

### 2. Color Palette Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Scheme type** | Monochromatic, Analogous, Complementary, Split-complementary, Triadic | 5 scheme types [VERIFIED] |
| **Temperature** | Warm (reds/oranges/yellows), Cool (blues/greens/purples), Neutral (grays/beiges) | 3 temperature families |
| **Saturation level** | Muted (30-50%), Standard (50-70%), Vibrant (70-90%), Neon (90%+) | 4 saturation tiers |
| **Contrast mode** | Low contrast (subtle), Medium, High contrast (bold), Dark mode (light on dark) | 4 contrast levels |
| **Background** | Solid color, Linear gradient, Radial gradient, Mesh gradient, Photo with overlay, Texture | 6 background types |
| **Overlay opacity** | 0% (none), 20% (subtle), 40% (medium), 60% (strong), 80% (near-solid) | 5 opacity levels |

Source: interaction-design.org (2024-03-01), adobe.com/color-psychology (2023-09-12), coolors.co (2023-05-15)

### 3. Typography Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Heading class** | Geometric Sans (Poppins, Montserrat), Humanist Sans (Open Sans, Lato), Modern Serif (Playfair), Slab Serif (Roboto Slab), Display (Impact, Bebas Neue) | 5 heading classes |
| **Body class** | Humanist Sans (Open Sans, Source Sans), Geometric Sans (Inter, DM Sans), Serif (Merriweather, Lora) | 3 body classes |
| **Pairing method** | Contrast (Serif+Sans), Superfamily (IBM Plex Serif+Sans), Weight (Bold+Light same family) | 3 methods [VERIFIED] |
| **Heading weight** | Medium (500), SemiBold (600), Bold (700), ExtraBold (800), Black (900) | 5 weight options |
| **Text color on background** | Auto-contrast (WCAG AA: 4.5:1 ratio), White on dark, Dark on light, Brand accent | 4 color modes |
| **Case** | Sentence case, Title Case, UPPERCASE, lowercase | 4 case options |

### 4. Layout & Composition Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Composition** | Centered (symmetrical), Rule of Thirds, Golden Ratio, Asymmetric left-heavy, Asymmetric right-heavy | 5 compositions [VERIFIED] |
| **Content density** | Minimal (1-2 elements), Standard (3-4), Dense (5+) | 3 density levels |
| **Text position** | Top, Center, Bottom, Left sidebar, Right sidebar, Overlay on image | 6 positions |
| **Visual hierarchy** | Text-dominant, Image-dominant, Balanced, Data-dominant | 4 hierarchy modes |
| **Padding/margins** | Tight (4%), Standard (8%), Generous (12%), Ultra-wide (16%+) | 4 spacing levels |

### 5. Visual Elements

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Icon style** | Outlined (Lucide, Phosphor), Filled (Material Symbols fill=1), Duotone (Phosphor), Flat color (Iconify sets) | 4 icon styles [VERIFIED] |
| **Icon size** | Small (24px), Medium (32px), Large (48px), XL (64px) | 4 sizes |
| **Shape accents** | None, Rounded rectangles, Circles, Blobs/organic, Geometric (triangles, hexagons) | 5 shape types |
| **Border radius** | Sharp (0), Slight (4px), Rounded (8px), Pill (16px+), Full circle | 5 radius values |
| **Shadow depth** | None, Subtle (sm), Medium (md), Strong (lg), Dramatic (xl) | 5 levels |
| **Decorative elements** | None, Dots/particles, Lines/stripes, Abstract shapes, Photo cutouts | 5 decoration types |

### 6. CTA & Brand Positioning

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **CTA position** | Bottom-right (Z-pattern terminal), Bottom-center, Overlay center, Inline with text | 4 positions [VERIFIED] |
| **CTA style** | Pill button, Rectangle button, Ghost button (outline), Text+arrow, No CTA | 5 styles |
| **CTA color** | Brand accent, Complementary to background, White, Dark | 4 color options |
| **Logo position** | Top-left, Top-right, Bottom-left, Bottom-right, Watermark center | 5 positions |
| **Logo treatment** | Full color, Monochrome, White, Outlined | 4 treatments |
| **Branding weight** | Subtle (logo only), Standard (logo+handle), Strong (logo+handle+tagline) | 3 levels |

### Total Controllable Variables: Image Posts

**Summary:** 42 independent design variables across 6 categories.

**Combinatorial space** (conservative, 1 option per variable axis):
5 schemes x 4 saturations x 6 backgrounds x 5 heading classes x 3 pairings x 5 compositions x 4 icon styles x 5 CTA styles x 5 logo positions = **~2,250,000 unique combinations**.

Even selecting just 8 axes with 4 options each yields 4^8 = **65,536 distinct designs**.

### Image Sources

1. https://www.linkedin.com/help/linkedin/answer/a1405567 -- 2024
2. https://www.interaction-design.org/literature/topics/color-theory -- 2024-03-01
3. https://www.adobe.com/creativecloud/design/discover/color-psychology.html -- 2023-09-12
4. https://www.coolors.co/blog/color-theory-basics-and-terminology -- 2023-05-15
5. https://fonts.google.com/icons -- 2023-10-18
6. https://blush.design -- 2024

---

## Content Type Variables — Video

### Video Design Variables for LinkedIn

### 1. Video Specifications

| Variable | Options | Notes |
|----------|---------|-------|
| **Aspect ratio** | 16:9 (landscape), 1:1 (square), 4:5 (vertical), 9:16 (full vertical/stories) | All supported [VERIFIED] |
| **Resolution** | 720p (1280x720), 1080p (1920x1080), 4K (3840x2160); min 256x144, max 4096x2304 | 1080p recommended [VERIFIED] |
| **Frame rate** | 24fps (cinematic), 30fps (standard), 60fps (smooth) | 30fps recommended, 10-60 supported [VERIFIED] |
| **Duration** | 15s (hook), 30s (short), 60s (standard), 90s (extended), 3-10min (long-form) | Organic max: 10min [VERIFIED] |
| **File format** | MP4 (universal), MOV, AVI, WebM | MP4 recommended [VERIFIED] |
| **Max file size** | 5 GB (organic), 200 MB (ads) | LinkedIn hard limits [VERIFIED] |

Source: LinkedIn help center, strikesocial.com (2024-01-23), socialrails.com (2024-03-05)

### 2. Color & Visual Treatment

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Color grading** | Natural (no grade), Warm (golden hour), Cool (blue tint), Teal & Orange (cinematic), High contrast, Desaturated/muted | 6 grade presets |
| **LUT application** | None, Subtle (25% intensity), Standard (50%), Full (100%) | 4 intensity levels |
| **Background** | Solid color, Gradient, B-roll footage, Abstract motion, Blurred photo, None (transparent for overlays) | 6 background types |
| **Overall brightness** | Dark/moody, Standard, Bright/airy, High-key | 4 brightness levels |

### 3. Text Overlay & Caption Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Caption style** | Sentence (full sentence), Word-by-word (highlighted), Karaoke (progressive highlight), None | 4 styles [VERIFIED] |
| **Caption font** | Sans-Serif bold (Montserrat, Bebas Neue), Sans-Serif clean (Inter, Open Sans), Handwritten/script | 3 font classes |
| **Caption size** | Small (3% frame height), Medium (5%), Large (7%), XL (10%) | 4 sizes |
| **Caption position** | Bottom-center (standard), Center, Top, Bottom-left, Custom coordinates | 5 positions |
| **Caption background** | None, Solid box (black/white), Semi-transparent box, Blur behind, Outline/stroke only | 5 bg treatments [VERIFIED] |
| **Active word highlight** | Color change (accent color), Scale up (1.2x), Bold weight, Underline, Background box | 5 highlight methods [VERIFIED] |
| **Max lines** | 1 line, 2 lines (recommended max) | 2 options [VERIFIED] |
| **Chars per line** | ~25 (vertical), ~40 (landscape) | Per aspect ratio [VERIFIED] |

Source: subtitlesfast.com (2024-02-20), Hormozi-style caption analysis

### 4. Animation & Motion Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Text entry animation** | Fade in, Slide up/down/left/right, Scale up (pop), Typewriter, Bounce, Glitch, Wipe/reveal | 7 entry types [VERIFIED] |
| **Text exit animation** | Fade out, Slide out, Scale down, None (cut) | 4 exit types |
| **Animation timing** | Fast (0.2s), Standard (0.4s), Slow (0.8s), Dramatic (1.2s+) | 4 timing presets |
| **Easing curve** | Linear, Ease-in, Ease-out, Ease-in-out, Spring/bounce, Overshoot | 6 easing functions |
| **Element stagger** | None (all at once), 0.1s stagger, 0.2s stagger, 0.4s stagger | 4 stagger options |

Source: magicui.design (2024-03-14), standard motion design principles

### 5. Transition Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Scene transition** | Cut (instant), Dissolve/crossfade, Wipe (directional), Zoom in/out, Slide push, Glitch, Match cut | 7 transition types [VERIFIED] |
| **Transition duration** | Fast (0.3s), Standard (0.5s), Slow (1.0s) | 3 durations |
| **Audio transition** | Hard cut, Crossfade, J-cut (audio before video), L-cut (audio after video) | 4 audio transitions [VERIFIED] |

Source: premiumbeat.com (2023-08-07)

### 6. Lower-Third & Overlay Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Lower-third shape** | Rectangle, Pill/rounded, L-shaped, Underline bar, Custom SVG | 5 shapes [VERIFIED] |
| **Lower-third animation** | Slide in from left, Slide in from bottom, Fade+slide, Build-out (elements appear sequentially), Pop in | 5 animation types |
| **Lower-third position** | Bottom-left (standard), Bottom-center, Bottom-right | 3 positions |
| **Progress indicator** | None, Top bar, Bottom bar, Dot pagination, Timer countdown | 5 indicator types |
| **Watermark/logo** | Corner static, Corner with intro animation, None | 3 options |

### 7. Thumbnail Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Text amount** | None, 1-2 words (minimal), 3-4 words (standard), 5+ words (descriptive) | 4 levels [VERIFIED] |
| **Text position** | Top, Center, Bottom, Side panel | 4 positions |
| **Subject treatment** | Full frame, Isolated with background removal, Split screen, Collage | 4 treatments |
| **Color strategy** | Complementary contrast, Brand colors, High saturation, Monochrome | 4 strategies |
| **Dead zone awareness** | Avoid bottom-right (platform timestamp overlay) | Constraint [VERIFIED] |

Source: dominatetools.com (2024-01-15), clickyapps.com (2023-12-05)

### 8. Programmatic Video Generation Tools

| Tool | Approach | Key Variables | Source |
|------|----------|---------------|--------|
| **Remotion** | React components -> video frames | All React props: text, images, animations, styles, timing | remotion.dev [VERIFIED] |
| **Shotstack** | JSON timeline -> rendered video | Clip asset, length, fit, position, transitions, effects | shotstack.io [VERIFIED] |
| **Creatomate** | Template + API overrides | Text, images, colors, responsive aspect ratio adaptation | creatomate.com [VERIFIED] |
| **FFmpeg** | Filter graph pipeline | Every filter parameter: overlay coords, xfade duration, drawtext font/size/color | ffmpeg.org [VERIFIED] |
| **Synthesia** | AI avatar + script | scriptText, avatar ID, background URL, avatar position/scale | synthesia.io [VERIFIED] |
| **Lottie** | JSON animation + dynamic properties | Layer targeting by name, slot-based variable injection | lottiefiles.com [VERIFIED] |
| **After Effects MOGRTs** | Template with exposed controls | Text, color pickers, sliders (position/scale), boolean toggles | Adobe [VERIFIED] |

### Total Controllable Variables: Video

**Summary:** 55+ independent design variables across 8 categories.

**Combinatorial space** (conservative, selecting from 8 key axes):
6 grades x 4 caption styles x 5 highlights x 7 entry animations x 6 easings x 7 transitions x 5 lower-thirds x 4 thumbnail strategies = **~705,600 unique combinations**.

With timing, duration, and per-scene variation, the space expands to millions.

### Video Sources

- LinkedIn help center (2024)
- strikesocial.com/blog/linkedin-video-ad-specs-cheat-sheet/ (2024-01-23)
- linkboost.co/linkedin-video-length/ (2024-02-15)
- socialrails.com/linkedin-video-specs/ (2024-03-05)
1. https://www.linkedin.com/help/linkedin/answer/a1342323 -- 2024
2. https://strikesocial.com/blog/linkedin-video-ad-specs-cheat-sheet/ -- 2024-01-23
3. https://linkboost.co/linkedin-video-length/ -- 2024-02-15
4. https://socialrails.com/linkedin-video-specs/ -- 2024-03-05
5. https://www.remotion.dev/docs/ -- 2024
6. https://shotstack.io/docs/api/ -- 2024
7. https://creatomate.com/docs/api/ -- 2024
8. https://ffmpeg.org/ffmpeg-filters.html -- 2024
9. https://docs.synthesia.io/reference/createvideo -- 2024-02-01
10. https://lottiefiles.com/supported-features -- 2024-01-10
11. https://helpx.adobe.com/premiere-pro/using/motion-graphics-templates.html -- 2023-05-22
12. https://subtitlesfast.com/blog/video-subtitles-best-practices/ -- 2024-02-20
13. https://www.premiumbeat.com/blog/12-common-video-transitions/ -- 2023-08-07
14. https://dominatetools.com/youtube-thumbnail-guide/ -- 2024-01-15
