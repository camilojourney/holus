---
title: Visual Design Tool Registry — Carousel & Graphic Design
domain: visual-content
owner: holus-research
last_updated: 2026-03-16
review_cadence: 60
next_review: 2026-05-15
---

# Visual Design Tool Registry

The complete catalog of creative capabilities available to the design agent. Everything here is renderable via Playwright (headless Chromium) from HTML/CSS/SVG. Output: PDF (carousel) or PNG (image post). The tools are the same regardless of output format.

This is the agent's **palette** — it picks and combines tools based on the content's intent, audience, and emotional target. Like a real artist choosing brushes.

---

## 1. Color System

### 1.1 Color Harmony Algorithms

All work in HSL space. Hue (H) is 0-360 degrees.

| Harmony | Formula | Character |
|---------|---------|-----------|
| Complementary | H, H+180 | Maximum contrast, bold | [VERIFIED]
| Analogous | H-30, H, H+30 | Harmonious, serene | [VERIFIED]
| Triadic | H, H+120, H+240 | Vibrant, balanced | [VERIFIED]
| Split-complementary | H, H+150, H+210 | High contrast, less tension | [VERIFIED]
| Tetradic | H, H+60, H+180, H+240 | Rich, complex | [VERIFIED]
| Square | H, H+90, H+180, H+270 | All 4 quadrants | [VERIFIED]

**Complete palette from one hue:**
1. Base: `hsl(H, 70%, 55%)`
2. Light: `hsl(H, 70%, 90%)`
3. Dark: `hsl(H, 70%, 25%)`
4. Accent: `hsl(H+180, 70%, 55%)`
5. Neutral: `hsl(H, 10%, 50%)`

Source: tigercolor.com, Figma color wheel, dev.to/benjaminadk

### 1.2 Material Design 3 Tonal Palette

From a single seed color, M3's HCT algorithm generates 5 tonal palettes (primary, secondary, tertiary, neutral, neutral-variant), each with 13 tones: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99, 100]. [VERIFIED]

29 color roles: primary, onPrimary, primaryContainer, onPrimaryContainer, secondary, tertiary, error, surface, onSurface, surfaceVariant, outline, inverseSurface, inversePrimary, scrim, shadow, etc.

Library: `material-color-utilities` (npm) generates all tokens from one hex.

Source: m3.material.io/styles/color/roles, github.com/material-foundation/material-color-utilities

### 1.3 CSS Gradients

| Type | Syntax | Parameters |
|------|--------|------------|
| Linear | `linear-gradient(direction, stops)` | Angle (0-360deg), color stops with positions (%) | [VERIFIED]
| Radial | `radial-gradient(shape size at position, stops)` | circle/ellipse, closest-side to farthest-corner, position (x% y%) | [VERIFIED]
| Conic | `conic-gradient(from angle at position, stops)` | Start angle, position, stops in deg/% | [VERIFIED]
| Repeating | `repeating-*-gradient()` | Same params, auto-repeating | [VERIFIED]

All variants render perfectly in Chromium headless.

**Mesh gradient alternative:** Layer 3-5 `radial-gradient()` at different positions with different colors. Add `backdrop-filter: blur(40px)` child for smooth transitions. [VERIFIED]

Parameters per blob: `{ x%, y%, hue, saturation, lightness, spread(30-70%) }`. 3-5 blobs is the sweet spot.

Source: css-tricks.com/a-complete-guide-to-css-gradients, csshero.org/mesher, joshwcomeau.com/css/make-beautiful-gradients

### 1.4 Blend Modes

`mix-blend-mode` / `background-blend-mode`: 16 modes. [VERIFIED]

| Mode | Effect | Use Case |
|------|--------|----------|
| multiply | Darkens, white disappears | Rich shadows, photo darkening |
| screen | Lightens, black disappears | Glow effects, light leaks |
| overlay | Contrast boost (multiply+screen) | Photo enhancement |
| color | Apply hue/sat to image luminance | Brand color tinting |
| luminosity | Apply brightness, keep colors | Subtle mood shifts |
| difference | Inverts where colors overlap | Artistic, psychedelic |
| soft-light | Gentle contrast like dodging/burning | Subtle photo treatment |

Source: MDN mix-blend-mode, web.dev/learn/css/blend-modes, ishadeed.com

### 1.5 Duotone Effect

```css
img { filter: grayscale(100%) contrast(1.2); }
overlay::before { background: #shadow-color; mix-blend-mode: darken; }
overlay::after { background: #highlight-color; mix-blend-mode: lighten; }
```

Parameters: shadow color (hex), highlight color (hex), contrast (1.0-2.0). [VERIFIED]

Source: cssduotone.com, dev.to/itsjp

---

## 2. Typography

### 2.1 Variable Fonts

Registered axes: [VERIFIED]
- **wght** (Weight): 1-1000, maps to `font-weight`
- **wdth** (Width): 50%-200%, maps to `font-stretch`
- **slnt** (Slant): -90 to 90 degrees
- **ital** (Italic): 0 or 1
- **opsz** (Optical Size): auto-adjusts for font-size (8-144)

Custom axes (UPPERCASE): designer-defined. Examples: CASL (casualness), CRSV (cursive), MONO (monospace).

Top variable fonts: Roboto Flex (12 axes), Inter (wght), Montserrat (wght), Recursive (5 axes), Source Sans 3 (wght+opsz).

Source: MDN variable fonts guide, web.dev/variable-fonts, variablefonts.dev

### 2.2 OpenType Features

Via `font-feature-settings` or higher-level CSS: [VERIFIED]

| Tag | Feature | CSS Equivalent |
|-----|---------|---------------|
| liga | Standard ligatures | `font-variant-ligatures: common-ligatures` |
| smcp | Small caps | `font-variant-caps: small-caps` |
| tnum | Tabular figures | `font-variant-numeric: tabular-nums` |
| onum | Old-style figures | `font-variant-numeric: oldstyle-nums` |
| frac | Fractions | `font-variant-numeric: diagonal-fractions` |
| swsh | Swash | `font-variant-alternates: swash()` |
| ss01-ss20 | Stylistic sets | `font-variant-alternates: styleset()` |
| salt | Stylistic alternates | `font-variant-alternates: stylistic()` |

Use `tnum` for data slides (number alignment). `smcp` for elegant subheadings. `swsh` for decorative quotes.

Source: Adobe OpenType syntax, MDN font-feature-settings, abcdinamo.com

### 2.3 Text Effects

| Effect | CSS | Parameters |
|--------|-----|------------|
| Gradient text | `background: linear-gradient(); -webkit-background-clip: text; -webkit-text-fill-color: transparent` | Gradient direction, color stops | [VERIFIED]
| Text stroke | `-webkit-text-stroke: 2px #000; color: transparent` | Width (0.5-5px), color | [VERIFIED]
| Neon glow | `text-shadow: 0 0 7px #fff, 0 0 10px #fff, 0 0 42px #0fa, 0 0 82px #0fa` | 4-6 shadows, increasing blur, bright color | [VERIFIED]
| Embossed | `text-shadow: 0 1px 0 #fff, 0 -1px 0 rgba(0,0,0,0.3)` | Light/dark shadow offsets | [VERIFIED]
| 3D extrusion | Stack 10+ shadows, each incrementing 1px | Number of layers, direction, color | [VERIFIED]
| Outlined (cross-browser) | 4 shadows at -1/-1, 1/-1, -1/1, 1/1 | Color, spread | [VERIFIED]

Source: frontendmasters.com, freefrontend.com, MDN text-stroke

### 2.4 Font Pairing

Top pairings (2025-2026): [VERIFIED]

| Heading | Body | Style |
|---------|------|-------|
| Playfair Display | Inter | Premium/editorial |
| Bebas Neue | Open Sans | Bold/modern |
| DM Serif Display | Inter | Refined/startup |
| Poppins | Roboto | Trendy/SaaS |
| Lora | Nunito | Warm/storytelling |
| Montserrat | Lato | Clean/corporate |

Principles: Contrast (serif+sans), harmony (similar x-height), hierarchy (one leads, one supports).

Source: Nature Scientific Reports (2024), adobe.design, medium.com/design-bootcamp

### 2.5 Spacing as Design

| Property | Range | Creative Use |
|----------|-------|-------------|
| letter-spacing | -0.05em to 0.4em | Wide (0.15-0.3em) on ALL-CAPS for editorial feel |
| word-spacing | -0.05em to 1em | Increase for sparse, airy text blocks |
| line-height | 0.85 to 1.8 | Tight (0.9) on large display text for impact |
| text-wrap: balance | auto | Prevents orphans on 2-3 line headlines (Chrome 114+) | [VERIFIED]

Source: MDN, webdesignerdepot.com, smashingmagazine.com

### 2.6 Writing Modes

`writing-mode: vertical-rl` — text flows top-to-bottom, lines right-to-left. [VERIFIED]
`text-orientation: upright` — Latin chars stand up in vertical mode.

Use: sidebar labels, decorative edge text, vertical accents.

Note: `sideways-rl`/`sideways-lr` are Firefox-only, not in Chromium/Playwright.

Source: MDN writing-mode, smashingmagazine.com/2019/08/writing-modes-layout

---

## 3. Layout Systems

### 3.1 CSS Grid

Named areas, subgrid, explicit placement: [VERIFIED]

```css
grid-template-areas:
  "header  header  header"
  "sidebar content aside"
  "footer  footer  footer";
```

Subgrid: `grid-template-columns: subgrid` — child inherits parent tracks. (Chrome 117+)

Magazine-style: overlapping items via explicit `grid-column`/`grid-row` placement + `z-index`.

Source: MDN CSS Grid, devtoolbox.dedyn.io

### 3.2 Composition Systems

| System | CSS Implementation |
|--------|-------------------|
| Golden ratio | `grid-template-columns: 1fr 1.618fr` | [VERIFIED]
| Rule of thirds | `grid-template-columns: 1fr 1fr 1fr; grid-template-rows: 1fr 1fr 1fr` |
| Modular grid | `grid-template-columns: repeat(12, 1fr)` |
| Golden typography | Each step = previous × 1.618 |

Source: uxmag.com, figma.com/resource-library/golden-ratio

### 3.3 Asymmetric Layouts

Techniques for visual tension: [VERIFIED]
- Unequal grid splits: `2fr 1fr`, `3fr 5fr`
- Overlapping items: shared grid cells + z-index
- Transform offsets: `translateX(-20px) rotate(-2deg)`
- Breaking alignment: full-width element with asymmetric margins

Source: thehypedge.com, moldstud.com, blog.hubspot.com

### 3.4 Container Queries

`container-type: inline-size` on wrapper, then `@container (min-width: 600px)`. [VERIFIED]

Container units: `cqw` (1% of container width), `cqh`, `cqi`, `cqb`, `cqmin`, `cqmax`.

Use: `font-size: 3cqw` scales text proportionally to slide width. Same template renders at different sizes.

Source: web.dev/learn/css/container-queries, MDN @container

### 3.5 Aspect Ratio

`aspect-ratio: 4 / 5` locks slide dimensions. Works on any element. [VERIFIED]

Source: MDN aspect-ratio

### 3.6 CSS Shapes

`shape-outside` + `float` for text wrapping around shapes: [VERIFIED]
- `circle(50%)`, `ellipse()`, `polygon()`, `path()`
- `shape-margin: 20px` for spacing
- `shape-image-threshold: 0.5` for image-based shapes

Use: text wrapping around profile photos, diagonal text flows.

Source: MDN shape-outside, blog.logrocket.com, css-tricks.com

### 3.7 Multi-Column Layout

`column-count: 2-3`, `column-gap: 2rem`, `column-rule: 1px solid #ccc`. [VERIFIED]
`column-span: all` for headings. `break-inside: avoid` to keep blocks intact.

Source: MDN multicol, css-tricks.com

---

## 4. Visual Effects

### 4.1 CSS Filters

| Filter | Range | Effect |
|--------|-------|--------|
| blur() | 0-100px | Gaussian blur | [VERIFIED]
| brightness() | 0-2+ | Darken/brighten |
| contrast() | 0-2+ | Reduce/increase contrast |
| saturate() | 0-3+ | Desaturate/hypersaturate |
| hue-rotate() | 0-360deg | Shift all colors |
| grayscale() | 0-1 | Remove color |
| sepia() | 0-1 | Warm brown tint |
| invert() | 0-1 | Color inversion |
| drop-shadow() | x y blur color | Alpha-aware shadow |

Chain: `filter: saturate(1.4) contrast(1.1) brightness(1.05)` for punchy photo enhancement.

Source: MDN filter, coderpad.io

### 4.2 Backdrop Filter

Same functions as `filter`, applied to area BEHIND the element. [VERIFIED]
Requires semi-transparent background. Use `-webkit-backdrop-filter` prefix.

Core glassmorphism recipe:
```
background: rgba(255,255,255,0.15);
backdrop-filter: blur(12px);
border: 1px solid rgba(255,255,255,0.2);
border-radius: 16px;
```

Source: MDN backdrop-filter, ui.glass/generator

### 4.3 Shadows

**box-shadow:** `[inset] x y blur spread color`, comma-separated for multiple. [VERIFIED]
- Layered depth: 3-5 stacked shadows with increasing offset/blur
- Neon glow: multiple same-center shadows with bright color
- Inner glow: `inset 0 0 20px rgba(255,255,255,0.5)`

**text-shadow:** Same syntax, no spread/inset. Stack for neon, emboss, 3D.

**drop-shadow():** Follows alpha contour (works on transparent PNGs/SVGs).

Source: joshwcomeau.com/css/designing-shadows, codersblock.com

### 4.4 Masks and Clipping

**clip-path:** [VERIFIED]
- `inset()`, `circle()`, `ellipse()`, `polygon()`, `path()`, `url(#svgClip)`
- Animatable between same function types

**mask-image:** [VERIFIED]
- Gradient masks for fade-outs
- Image masks (white=visible, black=hidden)
- SVG masks for complex shapes
- `mask-composite: add|subtract|intersect|exclude`

Use `-webkit-mask-image` prefix in Chromium.

Source: web.dev/clipping-masking, css-tricks.com

### 4.5 CSS Transforms

**2D:** translate, rotate, scale, skew, matrix (6 values). [VERIFIED]
**3D:** perspective, rotateX/Y/Z, translateZ, scale3d, matrix3d (16 values). [VERIFIED]

Related: `transform-origin`, `transform-style: preserve-3d`, `backface-visibility: hidden`.

Perspective range: 100px (extreme) to 2000px (subtle).

Source: MDN transforms, polypane.app

### 4.6 Design Morphisms

| Style | Key CSS | Character |
|-------|---------|-----------|
| Glassmorphism | `backdrop-filter: blur(12px); background: rgba(255,255,255,0.15)` | Frosted, premium | [VERIFIED]
| Neumorphism | Dual box-shadow (dark + light) on matching bg | Soft, embossed | [VERIFIED]
| Neubrutalism | `border: 3px solid #000; box-shadow: 4px 4px 0 #000` | Bold, punchy | [VERIFIED]
| Claymorphism | Large radius + outer + inner shadows on pastel bg | Playful, 3D-ish | [VERIFIED]

Source: ixdf.org, neumorphism.io, cccreative.design

---

## 5. SVG Capabilities

### 5.1 Path Commands

| Command | Function | Parameters |
|---------|----------|------------|
| M/m | Move to | x y |
| L/l | Line to | x y |
| H/h | Horizontal line | x |
| V/v | Vertical line | y |
| C/c | Cubic bezier | x1 y1 x2 y2 x y |
| S/s | Smooth cubic | x2 y2 x y |
| Q/q | Quadratic bezier | x1 y1 x y |
| T/t | Smooth quadratic | x y |
| A/a | Elliptical arc | rx ry rotation large-arc sweep x y |
| Z | Close path | — |

Any 2D shape is possible. [VERIFIED]

Source: MDN SVG Paths, joshwcomeau.com/svg, W3C SVG spec

### 5.2 SVG Gradients & Patterns

**linearGradient:** Direction via x1,y1,x2,y2. Stops with offset/color/opacity. [VERIFIED]
**radialGradient:** Center cx,cy, radius r, focal point fx,fy. [VERIFIED]
**Patterns:** Repeating tiles via `<pattern>` — width, height, patternTransform (rotate, scale). Nestable. [VERIFIED]

Source: MDN SVG gradients, jenkov.com, MDN patterns

### 5.3 SVG Filter Primitives (Complete)

17 filter primitives, all chainable via `in`/`result`: [VERIFIED]

| Primitive | What It Does | Key Params |
|-----------|-------------|------------|
| feGaussianBlur | Blur | stdDeviation (0-50+, x y) |
| feColorMatrix | Color transform | type: matrix(20 vals), saturate(0-1), hueRotate(0-360) |
| feTurbulence | Perlin noise | type(fractalNoise/turbulence), baseFrequency(0.01-1), numOctaves(1-5), seed |
| feDisplacementMap | Warp by image | scale(0-200+), xChannelSelector(R/G/B/A) |
| feMorphology | Erode/dilate | operator(erode/dilate), radius(0-10+) |
| feComposite | Combine images | operator(over/in/out/atop/xor/arithmetic), k1-k4 |
| feBlend | Blend two inputs | mode (same as CSS blend modes) |
| feFlood | Solid fill | flood-color, flood-opacity(0-1) |
| feOffset | Shift | dx, dy |
| feMerge | Stack layers | feMergeNode children |
| feComponentTransfer | Per-channel adjust | feFuncR/G/B/A: identity/table/discrete/linear/gamma |
| feConvolveMatrix | Convolution | kernelMatrix(3x3+), order, divisor, bias |
| feDiffuseLighting | Matte light | surfaceScale, diffuseConstant + light source |
| feSpecularLighting | Glossy light | surfaceScale, specularConstant, specularExponent(1-128) |
| feImage | External image | href |
| feTile | Tile input | — |

Light sources: feDistantLight(azimuth 0-360, elevation 0-90), fePointLight(x,y,z), feSpotLight(x,y,z + cone).

Source: W3C SVG Filter spec, MDN, tympanus.net/codrops

### 5.4 Generative Textures (feTurbulence Recipes)

| Effect | type | baseFrequency | numOctaves | Additional |
|--------|------|--------------|------------|------------|
| Paper grain | fractalNoise | 0.6-0.8 | 3-4 | feColorMatrix(saturate=0) | [VERIFIED]
| Film grain | fractalNoise | 0.9 | 1 | Low opacity overlay (0.03-0.06) | [VERIFIED]
| Clouds | fractalNoise | 0.01-0.03 | 4 | feColorMatrix (tint) |
| Marble | turbulence | 0.01-0.05 | 5 | feDisplacementMap |
| Water ripples | turbulence | 0.01 0.1 | 2 | feDisplacementMap(scale=20) |

Source: tympanus.net/codrops, freecodecamp.org, fffuel.co

### 5.5 SVG Text

- `<text>` with x, y, text-anchor(start/middle/end), dominant-baseline
- `<tspan>` for inline per-word styling
- `<textPath>` for text along curves — `startOffset`(0-100%), `text-anchor` [VERIFIED]

Source: MDN textPath, css-tricks.com/curved-text-along-path

### 5.6 Decorative Elements

**Blobs:** Perturbed circle with cubic beziers. Params: complexity(3-20 points), contrast(0-1), size, fill. [VERIFIED]
**Waves:** Sine function → SVG bezier paths. Params: amplitude, frequency, layers, color per layer.
**Geometric patterns:** Grid patterns, tessellations, dot grids — programmatic SVG loops.

Tools: blobmaker.app, haikei.app, fffuel.co

Source: smashingmagazine.com/2021/03/svg-generators

---

## 6. Data Visualization

### 6.1 Chart Types (Pure SVG)

| Chart | SVG Technique | Complexity |
|-------|---------------|------------|
| Bar | `<rect>` height proportional to data | Low | [VERIFIED]
| Stacked bar | Multiple `<rect>` stacked via y-offset | Low |
| Line | `<polyline>` or `<path>` with L commands | Low |
| Area | Closed `<path>`, filled | Low |
| Pie | `<path>` arcs (A command) | Medium |
| Donut | Circle `stroke-dasharray` + `stroke-dashoffset` | Medium |
| Radar | Polygon at `(r*cos(angle), r*sin(angle))` | Medium |
| Scatter/Bubble | `<circle>` at (x,y), variable radius | Low |
| Treemap | Nested `<rect>` with squarified algorithm | High |
| Sankey | Cubic bezier paths, width = flow | High |
| Funnel | Trapezoid `<polygon>`, decreasing widths | Medium |
| Sparkline | Minimal `<polyline>`, no axes | Low |
| Gauge | Arc with `stroke-dasharray` | Medium |
| Waffle | Grid of `<rect>`, colored by count | Low |

Source: css-tricks.com/how-to-make-charts-with-svg, heyoka.medium.com

### 6.2 Data-Driven Design Patterns

**Big Number + Context:** `[72px number] [16px context] [sparkline]` — e.g., "47% increase in retention ↗"

**Impact techniques:**
- Comparison anchor: small "before", large "after"
- Proportion: waffle chart or icon array (100 icons, X filled)
- Part-to-whole: donut with metric in center hole
- Small multiples: same chart repeated per category

Source: uxmag.medium.com, decisionfoundry.com

### 6.3 Infographic Layouts

| Pattern | Structure | Best For |
|---------|-----------|----------|
| Comparison | Side-by-side columns | A vs B |
| Timeline (vertical) | Central line + alternating cards | History, roadmap |
| Process flow | Numbered steps + arrows | How-to, workflows |
| Funnel | Decreasing-width trapezoids | Conversion pipelines |
| Cycle | Elements around a circle | Recurring processes |
| Icon array | Grid of repeated icons | Proportions (X/100) |

Source: venngage.com, dochipo.com

---

## 7. Icon Systems

| Library | Count | Styles | Key Params |
|---------|-------|--------|------------|
| Lucide | 1,500+ | Outline (stroke) | size, color, strokeWidth(1-3) | [VERIFIED]
| Phosphor | 7,000+ | 6 weights (thin→fill→duotone) | size, color, weight, mirrored | [VERIFIED]
| Material Symbols | 3,000+ | Outlined/Rounded/Sharp, variable | fill(0/1), wght(100-700), GRAD(-25 to 200), opsz(20-48) | [VERIFIED]
| Tabler | 5,400+ | Outline | size, color, stroke width |
| Heroicons | 300+ | Outline/Solid/Mini/Micro | className |

All use `currentColor` — inherit parent's CSS color. All support inline SVG.

Source: lucide.dev, hugeicons.com

---

## 8. Photo Manipulation (CSS-Only)

### Filter Chains

Vintage: `grayscale(0.14) sepia(0.3) contrast(1.1) brightness(1.05)` [VERIFIED]
Punchy: `saturate(1.4) contrast(1.1) brightness(1.05)`
Moody: `brightness(0.8) contrast(1.3) saturate(0.8)`
Dreamy: `brightness(1.1) blur(0.5px) saturate(1.2)`

### Color Overlays via Blend Modes

`mix-blend-mode: multiply` with colored overlay = photo tinting [VERIFIED]
`mix-blend-mode: screen` with light overlay = glow/light leak
`mix-blend-mode: color` = recolor while preserving luminance

### Halftone

```css
background: radial-gradient(circle, black 40%, transparent 41%);
background-size: 8px 8px;
mask-image: url(source.jpg);
filter: contrast(10);
```

Parameters: dot-size(20-50%), dot-spacing(4-12px), dot-color. [VERIFIED]

Source: frontendmasters.com/blog/pure-css-halftone-effect

---

## 9. Design Quality Criteria

### C.R.A.P. Framework (measurable) [VERIFIED]

| Principle | Professional | Amateur | Measurement |
|-----------|-------------|---------|-------------|
| **Contrast** | 3:1+ for headings, 4.5:1+ for body (WCAG AA) | Low contrast, everything same weight | Contrast ratio calculator |
| **Repetition** | ≤3 fonts, ≤5-7 colors, consistent spacing | Random fonts, inconsistent styles | Count unique fonts/colors |
| **Alignment** | Everything snaps to grid, ≤3 distinct x-positions | Mixed alignment, elements "wherever" | Overlay grid, count breaks |
| **Proximity** | Related items grouped, whitespace ≥40% | Everything equally spaced or crammed | Gap ratio: related ≤ 1/3 of unrelated |

Source: figma.com/resource-library/graphic-design-principles, vwo.com/blog/crap-design-principles

### Gestalt Principles [VERIFIED]

| Principle | Slide Application | CSS Implementation |
|-----------|------------------|-------------------|
| Proximity | Group related items, separate unrelated with 2x spacing | `gap` property |
| Similarity | Same-type items share color/size/shape | Shared CSS class |
| Closure | Partial borders the eye completes | `border-left: 4px solid` only |
| Continuity | Guide eye along path (top-left → bottom-right) | Grid flow + SVG connecting lines |
| Figure-Ground | Clear foreground on distinct background | `box-shadow`, `backdrop-filter` |
| Common Region | Items inside shared boundary = grouped | Container with bg + padding + radius |

Source: ixdf.org, toptal.com, figma.com

### Optical Alignment [VERIFIED]

Triangles: shift ~5-10% right of math center. Circles: overshoot 2%. Text without descenders: shift down 5%. Icons in circles: offset toward optical mass center. Source: rafaltomal.com/optically-perfect

---

## 10. Canvas & Platform Specs

### Dimensions

| Platform | Format | Dimensions | Max Slides | Max Size |
|----------|--------|-----------|------------|----------|
| LinkedIn | PDF document | 1080x1350 (4:5), 1080x1080 (1:1) | 300 | 100MB | [VERIFIED]
| Instagram | Image carousel | 1080x1350 (4:5), 1080x1080 (1:1) | 20 | — | [VERIFIED]
| Twitter/X | Image carousel | 1200x675 (16:9), 1080x1080 (1:1) | 4 | — |
| IG Stories | Image/video | 1080x1920 (9:16) | — | — |

### Safe Zones

LinkedIn: 96px sides, 56px top, 120px bottom (page counter overlay). [VERIFIED]
Instagram: central 1080x1080 is profile grid crop. Bottom 150px has like/save buttons.

### Cross-Platform Rendering

Same slide templates → different output:
- **LinkedIn:** HTML → multi-page PDF via `PlaywrightEngine.render_carousel_pdf()`
- **Instagram:** HTML → individual PNGs via `PlaywrightEngine.render_carousel()`
- **Twitter:** Same PNGs, max 4 slides

[VERIFIED — implemented in holus visual pipeline]

---

## 11. QR Codes & Combinatorial Space

SVG QR codes for CTAs: `qrcode-svg`, `js-qrcode`. Params: content, ecl(L/M/Q/H), padding, fg/bg color, size. Use H(30%) with logo overlay. [VERIFIED]

80+ independent variables. 10 axes × 5 options = **~9.7M unique designs**. Agent selects by content intent + audience + platform. Not random — learned from feedback. Tool comparison in `stack.md`.
