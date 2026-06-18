---
title: Agent Rendering Capabilities for Holus Content
domain: visual-content
owner: holus-research
last_updated: 2026-06-18
review_cadence: 45d
next_review: 2026-08-02
---

# Research: Agent Rendering Capabilities For Holus

## Mode

TECHNICAL_OPTIONS

## Question

How should Holus plan and generate charts, PDFs, HTML previews, deterministic
images, and AI-generated images without forcing every content idea into a bad
image?

## Evidence

- [VERIFIED] Claude Code skills are reusable workflow packages. A skill is a
  `SKILL.md` file plus optional supporting files, and the body loads only when
  used. Source: https://code.claude.com/docs/en/skills
- [VERIFIED] Claude Code can share session output as artifacts. Source:
  https://code.claude.com/docs/en/artifacts
- [VERIFIED] Claude API code execution can run Python/bash in a sandbox and
  create files and visualizations. Source:
  https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool
- [VERIFIED] Claude Files API supports PDFs and images as file blocks; datasets
  and other files can be used with code execution for visualization workflows.
  Source: https://platform.claude.com/docs/en/build-with-claude/files
- [VERIFIED] Claude PDF support can analyze text, pictures, charts, and tables
  in PDFs. Source: https://platform.claude.com/docs/en/build-with-claude/pdf-support
- [VERIFIED] Codex skills package instructions, scripts, references, and assets
  for repeatable workflows and use progressive disclosure. Source:
  https://developers.openai.com/codex/skills
- [VERIFIED] Codex reads `AGENTS.md` instruction files from global and project
  scopes, with nearer files overriding broader guidance. Source:
  https://developers.openai.com/codex/guides/agents-md
- [VERIFIED] Codex use cases include dataset analysis with visualizations,
  slide decks with visuals, and learning reports with diagrams. Sources:
  https://developers.openai.com/codex/use-cases/datasets-and-reports,
  https://developers.openai.com/codex/use-cases/generate-slide-decks,
  https://developers.openai.com/codex/use-cases/learn-a-new-concept
- [VERIFIED] OpenAI image APIs can generate and edit images using GPT Image
  models including `gpt-image-2`. Sources:
  https://developers.openai.com/api/docs/guides/image-generation,
  https://developers.openai.com/api/docs/guides/images-vision
- [VERIFIED] OpenAI file inputs process PDFs by extracting text and page images
  for vision-capable models. Source:
  https://developers.openai.com/api/docs/guides/file-inputs
- [VERIFIED] Cursor official docs expose rules, agent skills, MCP, browser
  tooling, plan mode, and subagents. Sources:
  https://cursor.com/docs/rules, https://cursor.com/docs/skills,
  https://cursor.com/docs/mcp, https://cursor.com/docs/agent/tools/browser,
  https://cursor.com/docs/agent/plan-mode, https://cursor.com/docs/subagents
- [VERIFIED] Holus already renders deterministic PNG/PDF assets through
  Playwright/HTML/CSS/SVG. Source: `src/holus/visual/engine.py`,
  `src/holus/visual/spec_converter.py`, `src/holus/visual/carousel_builder.py`.
- [VERIFIED] Holus already has a route/plan/provider dispatcher layer for
  visuals. Source: `src/holus/visual/proximity_router.py`,
  `src/holus/visual/production_plan.py`,
  `src/holus/visual/generation_strategy.py`,
  `src/holus/visual/dispatcher.py`.
- [CORRECTED] AGY Gemini models are available locally as text/agent models, but
  the current AGY CLI image-provider experiment did not create PNG outputs.
  Source: `data/test-runs/visual-method-examples/ai-method-examples/cycle-report.json`.

## What The Other Systems Teach Us

### Claude Pattern

Claude separates repeatable procedures into skills, generated/shareable outputs
into artifacts, and data/file work into tool or code-execution flows.

Holus implication: chart/PDF/image creation should be a workflow with strict
inputs and observable outputs, not a vague prompt to "make an image."

### Codex Pattern

Codex uses durable instructions, skills for repeatable workflows, and artifacts
or reports generated through code and tools. The strongest pattern is not "ask a
model to draw"; it is "let the agent write/run code, inspect outputs, repair,
and package the artifact."

Holus implication: deterministic rendering and verification should be the
default for charts, diagrams, carousels, PDFs, and HTML previews. AI image
generation should sit behind a provider contract and be used only when the
content job requires a scene, metaphor, or product/story artifact.

### Cursor Pattern

Cursor separates rules, skills, plan mode, MCP, browser tooling, and subagents.
Rules are persistent context; skills are reusable procedures; subagents provide
specialized context isolation; browser tools verify visual/UI behavior.

Holus implication: use smaller specialist agents and a plan-first gate before
any renderer runs.

## Content Types Holus Should Support

| Content type | Primary job | Best renderer | AI image allowed? |
|---|---|---|---|
| Text-only post | opinion, lesson, quick insight | none | no |
| Text + chart | prove numeric claim | deterministic HTML/SVG -> PNG | no |
| Text + workflow diagram | explain process/handoff | deterministic HTML/SVG -> PNG | rarely |
| Text + architecture diagram | explain system structure | deterministic HTML/SVG -> PNG | no |
| Comparison card | contrast options | deterministic HTML/SVG -> PNG | no |
| LinkedIn PDF carousel | framework, tutorial, sequence | deterministic HTML -> PDF | no |
| Instagram carousel | visual sequence | deterministic HTML -> PNG set | rare |
| Product scene | show interface behavior | deterministic if exact UI; AI if illustrative | conditional |
| Founder/story artifact | human decision around artifact | AI image or hybrid | yes |
| Object metaphor | make abstract idea memorable | AI image | yes |
| Video/reel | demo, walkthrough, motion | Genpeli/future video path | no image-only fallback except thumbnail |

## Current Holus Files And Owners

### Planning

- `agents/specialists/content/idea-planner.md` decides candidate formats.
- `src/holus/agents/marketing/thought_pipeline.py` turns thoughts into
  channel-specific records.
- `src/holus/agents/marketing/format_planner.py` and `idea_runner.py` support
  older format planning paths.

Gap: no hard visual-necessity gate that can say "do not create an image."

### Deterministic Rendering

- `src/holus/visual/spec_converter.py` converts structured visual specs to
  render specs.
- `src/holus/visual/templates/` contains HTML/Jinja templates.
- `src/holus/visual/engine.py` renders HTML/CSS/SVG to PNG/PDF with Playwright.
- `src/holus/visual/carousel_builder.py` renders carousel PDFs.
- `config/brand-visual.yaml` defines visual identity tokens.

Gap: templates exist, but the planner does not reliably select the right
artifact type before visual generation.

### AI Image Path

- `src/holus/visual/proximity_router.py` chooses visual mode.
- `src/holus/visual/production_plan.py` builds a provider-facing plan.
- `src/holus/visual/generation_strategy.py` chooses deterministic vs AI.
- `src/holus/visual/dispatcher.py` routes to providers.
- `scripts/visual_provider_cycle.py` runs provider/model comparison cycles.

Gap: provider capability checks are too shallow. AGY models can run but have not
proven file-producing image generation.

### Evaluation

- `src/holus/visual/visual_judge.py` checks file readability, dimensions, route,
  and plan presence.
- `agents/evaluators/visual-content-judge.md` defines a richer visual rubric.
- `docs/research/domain/content-evaluation.md` says rendered PNGs need a
  multimodal visual judge.

Gap: current deterministic judge is not a semantic visual judge. It cannot
reliably say "this image makes sense."

## Recommended Agent Additions

### 1. `content-job-classifier`

Classifies refined thoughts into jobs such as `opinion`, `lesson`, `framework`,
`workflow_explanation`, `data_claim`, `product_update`, `founder_story`,
`metaphor`, or `case_study`.

### 2. `format-router`

Chooses `text_only`, `text_plus_visual`, `pdf_carousel`, `image_post`, or
`video_brief`, and returns forbidden formats.

### 3. `visual-necessity-gate`

Decides whether a visual is needed at all. This gate must be allowed to return
`needs_visual=false`.

Hard rules:

- opinion or lesson -> default text-only
- data claim -> chart or carousel, never AI image
- workflow explanation -> diagram or carousel
- product update -> screenshot/UI artifact first
- metaphor/story -> AI image allowed only when concrete

### 4. `deterministic-artifact-planner`

Owns chart, workflow, architecture, comparison, HTML preview, and PDF carousel
specs. It should output structured data only, never prose image prompts.

### 5. `ai-image-director`

Runs only after the necessity gate allows AI. It must require route mode,
concrete subject, viewer test, required elements, forbidden elements, text
policy, and exact output dimensions.

### 6. `semantic-visual-judge`

Needs a real vision-capable model. It should inspect PNG/PDF renderings and
answer whether the artifact makes sense without the caption, whether the output
is the right artifact type, whether labels are legible, and whether the visual
is useful rather than decorative.

## Recommendation

Build the planner refactor before adding more image models:

1. Content job classifier.
2. Format router with forbidden-format rules.
3. Visual necessity gate.
4. Deterministic artifact planner.
5. Semantic visual judge hook.

Only then should the provider cycle compare Codex, OpenAI image API, Pilaster,
or AGY-like providers.

## Confidence

High confidence that poor outputs came from weak planning, not only model
quality.

High confidence that deterministic rendering is the correct default for charts,
PDFs, HTML previews, diagrams, and comparison cards.

Medium confidence that AI images can be useful for story/metaphor/product-scene
content after the new planning gates exist.
