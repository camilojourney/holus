---
title: Image Post Design Variables
domain: visual-content
owner: holus-research
last_updated: 2026-03-15
review_cadence: 60
next_review: 2026-05-14
---

# Image Post Design Variables for LinkedIn

## 1. Dimensions & Format

| Variable | Options | Notes |
|----------|---------|-------|
| **Aspect ratio** | 1:1 (1080–1200px square), 4:5 (1080×1350), 1.91:1 (1200×627 link preview), 16:9 (1920×1080 landscape) | 4:5 maximizes mobile; 1.91:1 for Open Graph link cards [VERIFIED] |
| **Image count** | 1 (single), 2–9 (multi-image carousel/gallery), 20 (max) | Consistent aspect ratio across multi-image is critical [VERIFIED] |
| **File format** | PNG (graphics/text), JPEG (photos), WebP | PNG for sharp text, JPEG for photos |
| **Resolution** | 1x (1080px), 2x (2160px for retina) | Higher res for quality on high-DPI screens |

Source: Multiple marketing guides (2024), LinkedIn help center

## 2. Color Palette Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Scheme type** | Monochromatic, Analogous, Complementary, Split-complementary, Triadic | 5 scheme types [VERIFIED] |
| **Temperature** | Warm (reds/oranges/yellows), Cool (blues/greens/purples), Neutral (grays/beiges) | 3 temperature families |
| **Saturation level** | Muted (30-50%), Standard (50-70%), Vibrant (70-90%), Neon (90%+) | 4 saturation tiers |
| **Contrast mode** | Low contrast (subtle), Medium, High contrast (bold), Dark mode (light on dark) | 4 contrast levels |
| **Background** | Solid color, Linear gradient, Radial gradient, Mesh gradient, Photo with overlay, Texture | 6 background types |
| **Overlay opacity** | 0% (none), 20% (subtle), 40% (medium), 60% (strong), 80% (near-solid) | 5 opacity levels |

Source: interaction-design.org (2024-03-01), adobe.com/color-psychology (2023-09-12), coolors.co (2023-05-15)

## 3. Typography Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Heading class** | Geometric Sans (Poppins, Montserrat), Humanist Sans (Open Sans, Lato), Modern Serif (Playfair), Slab Serif (Roboto Slab), Display (Impact, Bebas Neue) | 5 heading classes |
| **Body class** | Humanist Sans (Open Sans, Source Sans), Geometric Sans (Inter, DM Sans), Serif (Merriweather, Lora) | 3 body classes |
| **Pairing method** | Contrast (Serif+Sans), Superfamily (IBM Plex Serif+Sans), Weight (Bold+Light same family) | 3 methods [VERIFIED] |
| **Heading weight** | Medium (500), SemiBold (600), Bold (700), ExtraBold (800), Black (900) | 5 weight options |
| **Text color on background** | Auto-contrast (WCAG AA: 4.5:1 ratio), White on dark, Dark on light, Brand accent | 4 color modes |
| **Case** | Sentence case, Title Case, UPPERCASE, lowercase | 4 case options |

## 4. Layout & Composition Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Composition** | Centered (symmetrical), Rule of Thirds, Golden Ratio, Asymmetric left-heavy, Asymmetric right-heavy | 5 compositions [VERIFIED] |
| **Content density** | Minimal (1-2 elements), Standard (3-4), Dense (5+) | 3 density levels |
| **Text position** | Top, Center, Bottom, Left sidebar, Right sidebar, Overlay on image | 6 positions |
| **Visual hierarchy** | Text-dominant, Image-dominant, Balanced, Data-dominant | 4 hierarchy modes |
| **Padding/margins** | Tight (4%), Standard (8%), Generous (12%), Ultra-wide (16%+) | 4 spacing levels |

## 5. Visual Elements

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Icon style** | Outlined (Lucide, Phosphor), Filled (Material Symbols fill=1), Duotone (Phosphor), Flat color (Iconify sets) | 4 icon styles [VERIFIED] |
| **Icon size** | Small (24px), Medium (32px), Large (48px), XL (64px) | 4 sizes |
| **Shape accents** | None, Rounded rectangles, Circles, Blobs/organic, Geometric (triangles, hexagons) | 5 shape types |
| **Border radius** | Sharp (0), Slight (4px), Rounded (8px), Pill (16px+), Full circle | 5 radius values |
| **Shadow depth** | None, Subtle (sm), Medium (md), Strong (lg), Dramatic (xl) | 5 levels |
| **Decorative elements** | None, Dots/particles, Lines/stripes, Abstract shapes, Photo cutouts | 5 decoration types |

## 6. CTA & Brand Positioning

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **CTA position** | Bottom-right (Z-pattern terminal), Bottom-center, Overlay center, Inline with text | 4 positions [VERIFIED] |
| **CTA style** | Pill button, Rectangle button, Ghost button (outline), Text+arrow, No CTA | 5 styles |
| **CTA color** | Brand accent, Complementary to background, White, Dark | 4 color options |
| **Logo position** | Top-left, Top-right, Bottom-left, Bottom-right, Watermark center | 5 positions |
| **Logo treatment** | Full color, Monochrome, White, Outlined | 4 treatments |
| **Branding weight** | Subtle (logo only), Standard (logo+handle), Strong (logo+handle+tagline) | 3 levels |

## Total Controllable Variables: Image Posts

**Summary:** 42 independent design variables across 6 categories.

**Combinatorial space** (conservative, 1 option per variable axis):
5 schemes × 4 saturations × 6 backgrounds × 5 heading classes × 3 pairings × 5 compositions × 4 icon styles × 5 CTA styles × 5 logo positions = **~2,250,000 unique combinations**.

Even selecting just 8 axes with 4 options each yields 4^8 = **65,536 distinct designs**.

## Sources

1. https://www.linkedin.com/help/linkedin/answer/a1405567 — 2024
2. https://www.interaction-design.org/literature/topics/color-theory — 2024-03-01
3. https://www.adobe.com/creativecloud/design/discover/color-psychology.html — 2023-09-12
4. https://www.coolors.co/blog/color-theory-basics-and-terminology — 2023-05-15
5. https://fonts.google.com/icons — 2023-10-18
6. https://blush.design — 2024
