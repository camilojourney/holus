---
title: Technology Stack — Models, Frameworks, Rendering Tools
domain: tooling
owner: holus-research
last_updated: 2026-03-15
review_cadence: 30
next_review: 2026-04-14
---

# Stack Research — Technology Choices

Technology choices for Holus's content creation pipeline: design tools, rendering engines, enterprise platforms, and design token standards.

---

## Design System Parameterization

How professional design tools and enterprise content platforms handle visual variation programmatically -- informing the architecture of Holus's Creative Tool Registry.

### Professional Design Tool Parameterization

#### Canva

**Approach:** Template-based with tagged element injection (Autofill API).

| Capability | Variables Exposed | Limitations |
|-----------|-------------------|-------------|
| **Connect API Autofill** | Text content, image (via asset_id), chart data -- per tagged element | No global palette/font swap via API [VERIFIED] |
| **Bulk Create** | CSV-to-element mapping for batch generation | Manual element tagging required [VERIFIED] |
| **Brand Kit** | Brand colors, fonts, logos -- applied manually or via templates | Not API-accessible for dynamic injection |
| **Magic Design AI** | High-level prompt -> layout suggestions | Black box -- variables not individually controllable |

**Variable ceiling:** ~300-500 tagged elements per design. Practical limit: 10-30 data-driven variables per template. [VERIFIED]

Source: canva.com/developers/docs/connect-api/autofill/ (2024)

#### Figma

**Approach:** Component-based with programmatic property control via Plugin API.

| Capability | Variables Exposed | Limitations |
|-----------|-------------------|-------------|
| **Component Properties** | TEXT (content), BOOLEAN (visibility), INSTANCE_SWAP (nested components) | Property types are limited to 3 [VERIFIED] |
| **Variants** | Multi-dimensional variant sets (size, state, theme, etc.) | Performance degrades >1000 variants [VERIFIED] |
| **Plugin API** | Full DOM-like access: create/modify any node, apply styles, read/write properties | Requires Figma runtime environment |
| **Variables (design tokens)** | Color, number, string, boolean -- scoped to modes (light/dark, brand A/B) | Newer feature, still evolving |

**Variable ceiling:** ~10-20 explicit properties per component; 1000+ permutations via variant combinations. Effectively unlimited via Plugin API. [VERIFIED]

Source: figma.com/developers/api (2024)

#### Adobe

**Approach:** Dual-layer -- Express SDK (high-level) + Firefly API (granular generative).

| Layer | Variables Exposed | Source |
|-------|-------------------|--------|
| **Express Embed SDK** | promptText, canvasSize, templateId | High-level integration [VERIFIED] |
| **Firefly Services API** | prompt, negativePrompt, contentClass ('photo'/'art'), style (e.g., 'hyperrealistic'), seed, numVariations (1-4), photoSettings (intensity, contrast) | Granular generative control [VERIFIED] |
| **Document Generation API** | JSON data -> tagged Word/PDF template merge | Data injection into templates [VERIFIED] |

**Variable ceiling:** ~10-15 parameters per Firefly API call; unlimited for Document Generation (JSON key-value). [VERIFIED]

Source: developer.adobe.com/firefly-services (2024), developer.adobe.com/document-services (2024-03-12)

### Enterprise Content Platform Parameterization

#### Jasper

| Capability | Variables | Source |
|-----------|-----------|--------|
| **image-template/render** | Layer-specific: text.content, text.color, imageFile, background.color | Official API [VERIFIED] |
| **Image Suite** | AI-driven: Replace Background (prompt), Uncrop, Upscale (width/height), Scale (0-4) | Official API [VERIFIED] |

#### Predis.ai

| Capability | Variables | Source |
|-----------|-----------|--------|
| **Template generation** | template_ids, custom_data (text/image overrides), palette enforcement | Official API [VERIFIED] |
| **AI generation** | Text prompt -> carousel/video/image with brand palette applied | Semi-automated |

#### Copy.ai

| Capability | Variables | Source |
|-----------|-----------|--------|
| **Workflows API** | prompt, aspect_ratio, style, negative_prompt per image action | Official API [VERIFIED] |

#### Lately.ai

| Capability | Variables | Source |
|-----------|-----------|--------|
| **Style Guide** | Brand colors, fonts, logos -- pre-set, applied to extracted content | [UNVERIFIED -- API not publicly documented] |
| **Content extraction** | Extracts clips from long-form, applies style guide | Marketing-inferred |

### Design Token Standards

The design token ecosystem provides the vocabulary for parameterizing visual systems:

| Standard/Tool | Role | Variable Types |
|--------------|------|----------------|
| **W3C Design Tokens (DTCG)** | Specification -- defines the data model | $value + $type fields in JSON. Types: color, dimension, fontFamily, fontWeight, duration, cubicBezier, shadow, border, gradient, transition, typography | [VERIFIED] |
| **Tokens Studio** (ex Figma Tokens) | Authoring -- creates/manages tokens in Figma | Color, spacing, sizing, borderRadius, opacity, fontFamilies, lineHeights, letterSpacing, boxShadow, composition | [VERIFIED] |
| **Style Dictionary** | Build tool -- transforms tokens to platform code | Consumes W3C JSON -> outputs CSS variables, Swift, Android XML, Compose, etc. | [VERIFIED] |

**Key insight:** W3C Design Tokens define **17+ token types** that represent the atomic units of visual design. This is the natural vocabulary for the Tool Registry. [VERIFIED]

Source: w3.org/community/design-tokens/ (2023)

### Programmatic Design Generation Tools

For Holus, the most promising approach is HTML/CSS/SVG-to-image, which provides unlimited variable control:

| Tool | Input | Output | Variables | Maturity |
|------|-------|--------|-----------|----------|
| **Satori** (Vercel) | JSX (HTML+CSS subset) | SVG | Every CSS property | Production -- used by Vercel OG | [VERIFIED] |
| **Polotno.js** | JSON canvas definition | PNG/JPEG/PDF | Every element attribute (x, y, text, fontSize, fill, opacity, rotation, etc.) | Production | [VERIFIED] |
| **Puppeteer/Playwright** | HTML page | PNG/JPEG/PDF screenshot | Every HTML attribute + CSS property | Production | [VERIFIED] |
| **html2canvas** | HTML element | Canvas/PNG | DOM properties | Production, client-side |
| **Penpot** | Open-source design tool | SVG/PNG export | Plugin API (shapes, styles, pages) | Growing ecosystem |

**Recommendation for Holus:** Satori (for static images/carousel slides) + Remotion (for video) gives full programmatic control with React component architecture matching the existing stack.

### Maximum Controllable Variables -- Summary

| System Type | Example | Max Variables | Practical Sweet Spot |
|------------|---------|---------------|---------------------|
| **Template injection** | Canva Autofill | 10-30 per template | Swap content, keep design fixed |
| **Component variant** | Figma Components | 10-20 properties, 1000+ permutations | Predefined design options |
| **Generative AI** | Firefly API | 10-15 parameters per call | Style/mood direction, not pixel-precise |
| **Programmatic** | Satori, Polotno, Remotion | **Effectively unlimited** | 40-60 design axes for practical combinatorial control |

**Conclusion for Tool Registry:** The programmatic approach (Satori/Polotno for static, Remotion for video) provides the maximum controllable variable space. Combined with W3C Design Token vocabulary, the registry can define **60+ independent axes of variation** per content type, yielding millions of unique combinations from a finite, pre-vetted palette of options.

### Stack Sources

1. https://www.canva.com/developers/docs/connect-api/autofill/ -- 2024
2. https://www.figma.com/developers/api -- 2024
3. https://developer.adobe.com/firefly-services/docs/guides/api/image_generation/ -- 2024
4. https://developer.adobe.com/document-services/docs/overview/document-generation-api/ -- 2024-03-12
5. https://documentation.jasper.ai/creator-api/reference/render-image-from-template -- 2024
6. https://predis.ai/api-documentation/ -- 2024
7. https://docs.copy.ai/reference/run-workflow -- 2024
8. https://www.w3.org/community/design-tokens/ -- 2023
9. https://polotno.com/docs/store-overview -- 2024
10. https://github.com/vercel/satori -- 2024
11. https://www.remotion.dev/docs/ -- 2024
