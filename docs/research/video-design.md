---
title: Video Design Variables & Animation Patterns
domain: visual-content
owner: holus-research
last_updated: 2026-03-15
review_cadence: 60
next_review: 2026-05-14
---

# Video Design Variables for LinkedIn

## 1. Video Specifications

| Variable | Options | Notes |
|----------|---------|-------|
| **Aspect ratio** | 16:9 (landscape), 1:1 (square), 4:5 (vertical), 9:16 (full vertical/stories) | All supported [VERIFIED] |
| **Resolution** | 720p (1280×720), 1080p (1920×1080), 4K (3840×2160); min 256×144, max 4096×2304 | 1080p recommended [VERIFIED] |
| **Frame rate** | 24fps (cinematic), 30fps (standard), 60fps (smooth) | 30fps recommended, 10-60 supported [VERIFIED] |
| **Duration** | 15s (hook), 30s (short), 60s (standard), 90s (extended), 3-10min (long-form) | Organic max: 10min [VERIFIED] |
| **File format** | MP4 (universal), MOV, AVI, WebM | MP4 recommended [VERIFIED] |
| **Max file size** | 5 GB (organic), 200 MB (ads) | LinkedIn hard limits [VERIFIED] |

Source: LinkedIn help center, strikesocial.com (2024-01-23), socialrails.com (2024-03-05)

## 2. Color & Visual Treatment

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Color grading** | Natural (no grade), Warm (golden hour), Cool (blue tint), Teal & Orange (cinematic), High contrast, Desaturated/muted | 6 grade presets |
| **LUT application** | None, Subtle (25% intensity), Standard (50%), Full (100%) | 4 intensity levels |
| **Background** | Solid color, Gradient, B-roll footage, Abstract motion, Blurred photo, None (transparent for overlays) | 6 background types |
| **Overall brightness** | Dark/moody, Standard, Bright/airy, High-key | 4 brightness levels |

## 3. Text Overlay & Caption Variables

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

## 4. Animation & Motion Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Text entry animation** | Fade in, Slide up/down/left/right, Scale up (pop), Typewriter, Bounce, Glitch, Wipe/reveal | 7 entry types [VERIFIED] |
| **Text exit animation** | Fade out, Slide out, Scale down, None (cut) | 4 exit types |
| **Animation timing** | Fast (0.2s), Standard (0.4s), Slow (0.8s), Dramatic (1.2s+) | 4 timing presets |
| **Easing curve** | Linear, Ease-in, Ease-out, Ease-in-out, Spring/bounce, Overshoot | 6 easing functions |
| **Element stagger** | None (all at once), 0.1s stagger, 0.2s stagger, 0.4s stagger | 4 stagger options |

Source: magicui.design (2024-03-14), standard motion design principles

## 5. Transition Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Scene transition** | Cut (instant), Dissolve/crossfade, Wipe (directional), Zoom in/out, Slide push, Glitch, Match cut | 7 transition types [VERIFIED] |
| **Transition duration** | Fast (0.3s), Standard (0.5s), Slow (1.0s) | 3 durations |
| **Audio transition** | Hard cut, Crossfade, J-cut (audio before video), L-cut (audio after video) | 4 audio transitions [VERIFIED] |

Source: premiumbeat.com (2023-08-07)

## 6. Lower-Third & Overlay Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Lower-third shape** | Rectangle, Pill/rounded, L-shaped, Underline bar, Custom SVG | 5 shapes [VERIFIED] |
| **Lower-third animation** | Slide in from left, Slide in from bottom, Fade+slide, Build-out (elements appear sequentially), Pop in | 5 animation types |
| **Lower-third position** | Bottom-left (standard), Bottom-center, Bottom-right | 3 positions |
| **Progress indicator** | None, Top bar, Bottom bar, Dot pagination, Timer countdown | 5 indicator types |
| **Watermark/logo** | Corner static, Corner with intro animation, None | 3 options |

## 7. Thumbnail Variables

| Variable | Options | Registry Values |
|----------|---------|-----------------|
| **Text amount** | None, 1-2 words (minimal), 3-4 words (standard), 5+ words (descriptive) | 4 levels [VERIFIED] |
| **Text position** | Top, Center, Bottom, Side panel | 4 positions |
| **Subject treatment** | Full frame, Isolated with background removal, Split screen, Collage | 4 treatments |
| **Color strategy** | Complementary contrast, Brand colors, High saturation, Monochrome | 4 strategies |
| **Dead zone awareness** | Avoid bottom-right (platform timestamp overlay) | Constraint [VERIFIED] |

Source: dominatetools.com (2024-01-15), clickyapps.com (2023-12-05)

## 8. Programmatic Video Generation Tools

| Tool | Approach | Key Variables | Source |
|------|----------|---------------|--------|
| **Remotion** | React components → video frames | All React props: text, images, animations, styles, timing | remotion.dev [VERIFIED] |
| **Shotstack** | JSON timeline → rendered video | Clip asset, length, fit, position, transitions, effects | shotstack.io [VERIFIED] |
| **Creatomate** | Template + API overrides | Text, images, colors, responsive aspect ratio adaptation | creatomate.com [VERIFIED] |
| **FFmpeg** | Filter graph pipeline | Every filter parameter: overlay coords, xfade duration, drawtext font/size/color | ffmpeg.org [VERIFIED] |
| **Synthesia** | AI avatar + script | scriptText, avatar ID, background URL, avatar position/scale | synthesia.io [VERIFIED] |
| **Lottie** | JSON animation + dynamic properties | Layer targeting by name, slot-based variable injection | lottiefiles.com [VERIFIED] |
| **After Effects MOGRTs** | Template with exposed controls | Text, color pickers, sliders (position/scale), boolean toggles | Adobe [VERIFIED] |

## Total Controllable Variables: Video

**Summary:** 55+ independent design variables across 8 categories.

**Combinatorial space** (conservative, selecting from 8 key axes):
6 grades × 4 caption styles × 5 highlights × 7 entry animations × 6 easings × 7 transitions × 5 lower-thirds × 4 thumbnail strategies = **~705,600 unique combinations**.

With timing, duration, and per-scene variation, the space expands to millions.

## Sources

- LinkedIn help center (2024)
- strikesocial.com/blog/linkedin-video-ad-specs-cheat-sheet/ (2024-01-23)
- linkboost.co/linkedin-video-length/ (2024-02-15)
- socialrails.com/linkedin-video-specs/ (2024-03-05)
1. https://www.linkedin.com/help/linkedin/answer/a1342323 — 2024
2. https://strikesocial.com/blog/linkedin-video-ad-specs-cheat-sheet/ — 2024-01-23
3. https://linkboost.co/linkedin-video-length/ — 2024-02-15
4. https://socialrails.com/linkedin-video-specs/ — 2024-03-05
5. https://www.remotion.dev/docs/ — 2024
6. https://shotstack.io/docs/api/ — 2024
7. https://creatomate.com/docs/api/ — 2024
8. https://ffmpeg.org/ffmpeg-filters.html — 2024
9. https://docs.synthesia.io/reference/createvideo — 2024-02-01
10. https://lottiefiles.com/supported-features — 2024-01-10
11. https://helpx.adobe.com/premiere-pro/using/motion-graphics-templates.html — 2023-05-22
12. https://subtitlesfast.com/blog/video-subtitles-best-practices/ — 2024-02-20
13. https://www.premiumbeat.com/blog/12-common-video-transitions/ — 2023-08-07
14. https://dominatetools.com/youtube-thumbnail-guide/ — 2024-01-15
