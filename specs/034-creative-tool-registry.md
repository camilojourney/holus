# Spec 034: Creative Tool Registry

**Status:** draft
**Phase:** v0.4 (Phase 1 — One Working Loop)
**Research deps:** [research/stack.md "Design System Parameterization", research/architecture.md "Deterministic Creativity Architecture" + "Creative Tool Registry Architecture", research/domain/carousel.md, research/domain/image.md]
**Depends on:** [Spec 031 (LinkedIn Content Pipeline — provides the content types this registry serves)]
**Blocks:** None (standalone enhancement to existing visual pipeline)
**Created:** 2026-03-20
**Updated:** 2026-03-20

## Problem

Holus generates visual content (carousels, image posts) using a brand-visual.yaml file and 15 Jinja2 templates rendered via Playwright. The system works end-to-end but lacks three capabilities required by the architecture's Deterministic Creativity model (research/architecture.md):

1. **No formal registry** — templates, palettes, typography, and content-type rules are scattered across `config/brand-visual.yaml`, `src/holus/visual/templates/`, and hardcoded selections in `idea_runner.py`. There is no unified interface for the agent to query "what visual tools are available for this content type?"

2. **No tone-to-style mapping** — the marketing-strategist agent decides what content to create but has no structured way to map content intent (educational, provocative, storytelling, data-driven) to specific visual treatments. Selection is implicit in prompt instructions rather than explicit in a queryable registry.

3. **No variant tracking** — when the system creates content, there is no record of which visual treatment was applied, making it impossible to correlate visual choices with engagement outcomes. The weekly learning loop (Spec 012) cannot optimize what it cannot measure.

## Goals

- G1: Provide a single registry interface (`ToolRegistry`) that returns available visual treatments for a given content type and intent signal (research/architecture.md "Selection Engine") [VERIFIED]
- G2: Migrate `config/brand-visual.yaml` to a token-driven format where visual variants are defined as token sets applied to a shared base template (research/stack.md "Design Token Standards") [VERIFIED]
- G3: Track which visual treatment was applied to each content piece in `trajectory.jsonl`, enabling the weekly learning loop to correlate visual choices with engagement (research/architecture.md "Feedback Loop") [VERIFIED]
- G4: Support 5 intent categories — educational, storytelling, data-driven, provocative, minimal — each with a default token set (research/architecture.md "Toolset Design") [VERIFIED]

## Non-Goals

- NG1: A/B testing infrastructure (Mode 2) — deferred until Mode 1 generates 20+ samples per variant per intent category, per vision.md Phase 2 gating
- NG2: Learned selection weights (Mode 3) — requires statistically significant performance data that does not exist yet
- NG3: Satori rendering engine — the 2-1 specialist vote favored adding Satori for static images, but the security dissent (SVG injection surface) warrants deferring until the registry itself is proven; Playwright renders all current output types (carousel PDF, single image PNG)
- NG4: Animated infographic integration — Spec 033 covers this independently
- NG5: Video rendering — genpeli owns video per ADR-0001

## Solution

Formalize the existing visual pipeline into a 3-layer Creative Tool Registry:

```
Layer 1: Token Sets (data)
  config/tokens/{intent}.json — 5 files, one per intent category
  Each defines: colors, typography, spacing overrides applied as CSS custom properties

Layer 2: Base Templates (structure)
  src/holus/visual/templates/ — existing Jinja2 templates (unchanged)
  Templates consume token values via CSS custom properties (already true for brand-visual.yaml)

Layer 3: Registry API (logic)
  src/holus/visual/registry.py — ToolRegistry class
  Loads token sets at startup, exposes query interface for agent selection
```

The marketing-strategist agent calls `registry.get_treatment(content_type, intent)` and receives a `VisualTreatment` object containing the token set, recommended template, and metadata. This treatment is logged to `trajectory.jsonl` alongside the content piece.

## Core Specifications

**SPEC-001: Token Set Format**

| Field | Value |
|-------|-------|
| Description | Define a JSON schema for visual token sets following W3C Design Token vocabulary |
| Trigger | System startup: `ToolRegistry.__init__()` loads all `config/tokens/*.json` files |
| Input | JSON files in `config/tokens/` directory, each containing color, typography, and spacing tokens |
| Output | Parsed and validated `TokenSet` Pydantic model in memory |
| Validation | JSON Schema validation at load time; all color values must be valid hex (#RRGGBB or #RRGGBBAA); all size values must be positive integers in pixels; font names must match fonts installed in `src/holus/visual/fonts/` |
| Auth Required | No (internal system, no user-facing endpoint) |

Token set schema:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["name", "intent", "colors", "typography", "spacing"],
  "properties": {
    "name": { "type": "string" },
    "intent": { "enum": ["educational", "storytelling", "data_driven", "provocative", "minimal"] },
    "colors": {
      "type": "object",
      "required": ["primary", "text", "background", "surface", "accent"],
      "properties": {
        "primary": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6,8}$" },
        "text": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6,8}$" },
        "background": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6,8}$" },
        "surface": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6,8}$" },
        "accent": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6,8}$" },
        "muted": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6,8}$" },
        "success": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6,8}$" },
        "danger": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6,8}$" }
      }
    },
    "typography": {
      "type": "object",
      "required": ["headline_font", "headline_weight", "body_font", "body_weight"],
      "properties": {
        "headline_font": { "type": "string" },
        "headline_weight": { "type": "integer", "minimum": 100, "maximum": 900 },
        "body_font": { "type": "string" },
        "body_weight": { "type": "integer", "minimum": 100, "maximum": 900 }
      }
    },
    "spacing": {
      "type": "object",
      "properties": {
        "margin": { "type": "integer", "minimum": 0 },
        "padding": { "type": "integer", "minimum": 0 },
        "gap": { "type": "integer", "minimum": 0 }
      }
    }
  }
}
```

Acceptance Criteria:
- [ ] 5 token set JSON files exist in `config/tokens/`: `educational.json`, `storytelling.json`, `data_driven.json`, `provocative.json`, `minimal.json`
- [ ] Each file passes JSON Schema validation at `ToolRegistry` startup
- [ ] Invalid token files (missing required fields, malformed hex colors, negative sizes) cause `ToolRegistry.__init__()` to raise `RegistryValidationError` with the file name and specific validation failure
- [ ] Token values from existing `config/brand-visual.yaml` themes are preserved: dark theme maps to `minimal`, warm maps to `storytelling`, cool maps to `educational`, bold maps to `provocative`, light maps to `data_driven`

**SPEC-002: ToolRegistry API**

| Field | Value |
|-------|-------|
| Description | Python class that loads token sets and provides a query interface for the marketing-strategist agent |
| Trigger | Agent calls `registry.get_treatment(content_type, intent)` during content creation |
| Input | `content_type: str` (one of: carousel, single_image, text_post), `intent: str` (one of 5 intent categories) |
| Output | `VisualTreatment` Pydantic model containing: token_set, recommended_templates (list of template names), metadata (intent, content_type, timestamp) |
| Validation | `content_type` must be in `["carousel", "single_image", "text_post"]`; `intent` must be in `["educational", "storytelling", "data_driven", "provocative", "minimal"]`; raises `ValueError` with exact invalid value on mismatch |
| Auth Required | No |

```python
class VisualTreatment(BaseModel):
    token_set_name: str
    intent: str
    content_type: str
    colors: TokenColors
    typography: TokenTypography
    spacing: TokenSpacing
    recommended_templates: list[str]
    created_at: datetime

class ToolRegistry:
    def __init__(self, tokens_dir: Path = Path("config/tokens")) -> None: ...
    def get_treatment(self, content_type: str, intent: str) -> VisualTreatment: ...
    def list_intents(self) -> list[str]: ...
    def list_content_types(self) -> list[str]: ...
```

Template recommendation rules (Mode 1 — deterministic):

| Content Type | Intent | Recommended Templates |
|---|---|---|
| carousel | educational | hook_slide, body_slide, data_slide, summary_slide, cta_slide |
| carousel | storytelling | hook_slide, centered_slide, quote_slide, split_left_slide, cta_slide |
| carousel | data_driven | hook_slide, data_slide, stat_slide, comparison_slide, cta_slide |
| carousel | provocative | hook_slide, centered_slide, stat_slide, body_slide, cta_slide |
| carousel | minimal | hook_slide, body_slide, body_slide, body_slide, cta_slide |
| single_image | educational | insight |
| single_image | data_driven | data_viz |
| single_image | storytelling | insight |
| single_image | provocative | poll |
| single_image | minimal | insight |
| text_post | * | (empty list — text posts have no visual template) |

Acceptance Criteria:
- [ ] `ToolRegistry()` loads all 5 token sets from `config/tokens/` and is importable from `holus.visual.registry`
- [ ] `get_treatment("carousel", "educational")` returns a `VisualTreatment` with `token_set_name="educational"`, `recommended_templates` containing exactly `["hook_slide", "body_slide", "data_slide", "summary_slide", "cta_slide"]`
- [ ] `get_treatment("invalid_type", "educational")` raises `ValueError` with message containing "invalid_type"
- [ ] `get_treatment("carousel", "invalid_intent")` raises `ValueError` with message containing "invalid_intent"
- [ ] `list_intents()` returns `["data_driven", "educational", "minimal", "provocative", "storytelling"]` (sorted alphabetically)

**SPEC-003: TemplateEngine Token Integration**

| Field | Value |
|-------|-------|
| Description | Extend `TemplateEngine.render()` to accept a `VisualTreatment` and inject its token values as CSS custom properties, overriding the default brand-visual.yaml values |
| Trigger | `TemplateEngine.render(template_name, variables, treatment=treatment)` |
| Input | Existing `template_name` and `variables` parameters, plus optional `treatment: VisualTreatment` |
| Output | Rendered HTML with CSS custom properties from the treatment's token set injected into `<head>` |
| Validation | If `treatment` is provided, its token values take precedence over `brand-visual.yaml` defaults; if `treatment` is `None`, existing behavior is preserved (backward compatible) |
| Auth Required | No |

Acceptance Criteria:
- [ ] `render("carousel/hook_slide", vars)` without `treatment` parameter produces identical output to current behavior (backward compatible)
- [ ] `render("carousel/hook_slide", vars, treatment=educational_treatment)` produces HTML where `--color-primary` CSS variable matches the educational token set's primary color, not brand-visual.yaml's default
- [ ] All 8 color tokens, 4 typography tokens, and 3 spacing tokens from the treatment are injected as CSS custom properties
- [ ] Existing templates require zero modifications — token injection happens at the CSS variable level

**SPEC-004: Treatment Logging to Trajectory**

| Field | Value |
|-------|-------|
| Description | Log the visual treatment applied to each content piece in `trajectory.jsonl` so the weekly learning loop can correlate visual choices with engagement |
| Trigger | Content piece is created using a `VisualTreatment` |
| Input | `VisualTreatment` metadata (token_set_name, intent, content_type, recommended_templates) |
| Output | Additional fields appended to the trajectory entry for this content piece |
| Validation | Treatment fields are added to existing trajectory schema; entries without visual content (text_post with no image) have `visual_treatment: null` |
| Auth Required | No |

Trajectory entry additions:
```json
{
  "visual_treatment": {
    "token_set": "educational",
    "intent": "educational",
    "content_type": "carousel",
    "templates_used": ["hook_slide", "body_slide", "data_slide", "summary_slide", "cta_slide"],
    "theme_override": null
  }
}
```

Acceptance Criteria:
- [ ] Every carousel and single_image content piece logged to `trajectory.jsonl` includes a `visual_treatment` object with all 4 fields
- [ ] Text-only content pieces have `"visual_treatment": null`
- [ ] The weekly learning loop (`WeeklyLearningLoop`) can group trajectory entries by `visual_treatment.token_set` and compute per-token-set engagement averages
- [ ] Treatment logging adds no more than 200 bytes per trajectory entry

**SPEC-005: Migration from brand-visual.yaml**

| Field | Value |
|-------|-------|
| Description | Create the 5 token set JSON files from existing `config/brand-visual.yaml` theme definitions, preserving all current visual behavior |
| Trigger | One-time migration script: `scripts/migrate_brand_to_tokens.py` |
| Input | `config/brand-visual.yaml` (themes section + font_pairings section) |
| Output | 5 JSON files in `config/tokens/` |
| Validation | Script runs idempotently; re-running overwrites existing token files with the same content |
| Auth Required | No |

Migration mapping:

| brand-visual.yaml theme | Token set | Font pairing |
|---|---|---|
| dark | minimal | tech |
| light | data_driven | modern |
| warm | storytelling | editorial |
| cool | educational | tech |
| bold | provocative | bold |

Acceptance Criteria:
- [ ] `scripts/migrate_brand_to_tokens.py` reads `config/brand-visual.yaml` and writes 5 JSON files to `config/tokens/`
- [ ] Each generated JSON file passes the schema validation defined in SPEC-001
- [ ] `config/brand-visual.yaml` is NOT deleted — it remains as the backward-compatible default for `TemplateEngine` when no treatment is provided
- [ ] Color values in generated token files match the corresponding theme values exactly (no rounding or transformation)
- [ ] A carousel rendered with the `minimal` token set produces visually identical output to a carousel rendered with the current dark theme defaults

## Edge Cases & Failure Modes

**EDGE-001: Missing token file**
- Scenario: A token JSON file referenced by the registry is deleted or corrupted after startup
- Expected behavior: `ToolRegistry.__init__()` fails at startup with `RegistryValidationError` listing the missing or invalid file. The system does not start with a partial registry.
- Error message: "RegistryValidationError: Failed to load token set from config/tokens/{name}.json: {specific error}"
- Recovery: Fix or restore the missing file, restart the system

**EDGE-002: Unknown intent from agent**
- Scenario: The marketing-strategist agent passes an intent string not in the 5 defined categories
- Expected behavior: `get_treatment()` raises `ValueError` with the invalid intent and the list of valid intents
- Error message: "ValueError: Unknown intent 'comparison'. Valid intents: data_driven, educational, minimal, provocative, storytelling"
- Recovery: Agent retries with a valid intent from the list

**EDGE-003: Empty token directory**
- Scenario: `config/tokens/` directory exists but contains no JSON files
- Expected behavior: `ToolRegistry.__init__()` raises `RegistryValidationError`
- Error message: "RegistryValidationError: No token sets found in config/tokens/. Run scripts/migrate_brand_to_tokens.py to generate initial token sets."
- Recovery: Run the migration script

**EDGE-004: Concurrent registry access**
- Scenario: Multiple agent threads call `get_treatment()` simultaneously
- Expected behavior: Thread-safe read access. Token sets are loaded once at `__init__()` and stored as frozen Pydantic models. No write operations occur during `get_treatment()`.
- N/A for single-agent execution; documented for future multi-agent scenarios.

Standard edge cases:
- [x] Empty states — EDGE-003 covers empty token directory
- [x] Invalid input — EDGE-002 covers unknown intent/content_type
- [ ] Boundary values — N/A (no numeric user input)
- [ ] Network failure — N/A (registry is file-based, no network calls)
- [ ] Concurrent actions — EDGE-004 covers thread safety
- [ ] Permission denied — N/A (internal system, no auth)
- [ ] State transitions — N/A (registry is read-only after startup)

## Implementation Notes

- `ToolRegistry` lives in `src/holus/visual/registry.py` — new file
- Token sets live in `config/tokens/` — new directory
- `TemplateEngine` in `src/holus/visual/templates.py` gains an optional `treatment` parameter — backward-compatible change
- The migration script `scripts/migrate_brand_to_tokens.py` is a one-time utility
- `brand-visual.yaml` is preserved; `ToolRegistry` reads from `config/tokens/`, not from `brand-visual.yaml`

File changes:
- NEW: `src/holus/visual/registry.py` (~150 lines)
- NEW: `config/tokens/educational.json` (~40 lines)
- NEW: `config/tokens/storytelling.json` (~40 lines)
- NEW: `config/tokens/data_driven.json` (~40 lines)
- NEW: `config/tokens/provocative.json` (~40 lines)
- NEW: `config/tokens/minimal.json` (~40 lines)
- NEW: `scripts/migrate_brand_to_tokens.py` (~80 lines)
- MODIFIED: `src/holus/visual/templates.py` (~20 lines changed — add `treatment` parameter)
- MODIFIED: trajectory logging in marketing agent (~10 lines — add `visual_treatment` field)

## Decisions

### Registry Storage Format
**Chosen:** JSON following W3C Design Token vocabulary (Option C)
**Vote:** arch: B (Pydantic+YAML) | perf: C (JSON) | sec: C (JSON) — 2-1
**Rationale:** JSON has no execution semantics (`json.loads()` cannot run code), parses 2-5x faster than YAML in Python, and the W3C Design Token vocabulary provides a standardized schema for visual tokens. Pydantic validation is still applied after loading — the format is JSON, the runtime model is Pydantic.
**Dissent (arch):** Pydantic dataclasses with YAML serialization would match the existing Pydantic-at-boundaries mandate and keep human authoring ergonomic. Mitigated: JSON is still human-readable and Pydantic validation is preserved at load time.

### Rendering Engine
**Chosen:** Playwright only (Option A — defer Satori)
**Vote:** arch: B (Satori+Playwright) | perf: B (Satori+Playwright) | sec: A (Playwright only) — 2-1 for B
**Rationale:** While arch and perf favored adding Satori for its 5-10x faster static image rendering (10-30ms vs 150ms), the security concern about SVG injection vectors is valid, and the current throughput (30 pieces/month, 150ms per render) does not create a bottleneck. Deferring Satori to a follow-up spec after the registry proves its value is the lower-risk path. Satori can be added as a transparent rendering backend swap without changing the registry or template architecture.
**Dissent (arch + perf):** Satori would deliver significant rendering speedup and is production-proven (Vercel OG). Accepted risk: deferred, not rejected. When rendering volume exceeds 100 pieces/month or render latency becomes a pipeline bottleneck, revisit this decision.

### Template Variant Architecture
**Chosen:** Token-driven templates (Option C)
**Vote:** arch: C | perf: C | sec: C — Unanimous
**Rationale:** A single base template parameterized by token sets means adding a new visual variant is creating a JSON file, not writing HTML. This eliminates file-path resolution at render time (sec), keeps memory flat at O(1) regardless of variant count (perf), and extends the existing `brand-visual.yaml` CSS custom property pattern naturally (arch).

### Selection Engine Initial Mode
**Chosen:** Rule-based only — Mode 1 (Option A)
**Vote:** arch: A | perf: A | sec: A — Unanimous
**Rationale:** Deterministic mapping of intent→token_set+templates is fully testable, auditable against `guardrails.yaml`, and generates the labeled performance data needed before A/B testing (Mode 2) can produce statistically significant results. Vision.md explicitly gates Phase 2 infrastructure on Phase 1 producing content worth measuring.

### Feedback Loop Integration
**Chosen:** Batch weekly cron (Option A)
**Vote:** arch: A | perf: A | sec: A — Unanimous
**Rationale:** Weekly batch weight updates match the marketing-strategist's own weekly ReAct cycle (ADR-0001), keep analytics ownership in social-media-automatization, and bound the attack window for poisoned analytics payloads to one ingest per week aligned with human review.

## Alternatives Considered

1. **Unified brand-visual.yaml expansion** — add intent categories directly to the existing YAML file instead of creating a separate token system. Rejected: the file is already 140 lines and mixing "default brand identity" with "intent-specific variations" conflates two concerns. The registry separates static brand identity (brand-visual.yaml) from dynamic intent-driven variations (config/tokens/).

2. **Database-backed registry** — store token sets in Supabase for dynamic updates. Rejected: adds a network dependency to the rendering hot path. Token sets change infrequently (weekly at most); file-based storage with startup loading is sufficient and keeps the system operational offline.

3. **Full W3C Design Token toolchain** (Style Dictionary build step) — use Style Dictionary to transform W3C JSON into CSS variables. Rejected: over-engineering for 5 token sets. Direct JSON→Pydantic→CSS property injection is simpler and avoids adding a Node.js build step to a Python project.

## Observability

- `ToolRegistry.__init__()` logs: number of token sets loaded, validation time, any warnings
- `get_treatment()` logs at DEBUG level: content_type, intent, selected token_set, recommended_templates
- Treatment selection is recorded in `trajectory.jsonl` per SPEC-004 — the weekly learning loop reads this to report per-intent engagement trends
- The Observatory API (Spec 028) can serve `/api/v1/registry/intents` to expose available treatments in the dashboard

## Out of Scope

- Visual judge integration (content-evaluation.md Tier 2b) — separate spec, depends on rendered PNG availability
- Satori rendering engine — deferred per Rendering Engine decision above
- A/B testing (Mode 2) and learned weights (Mode 3) — deferred per Selection Engine decision
- Platform-specific token overrides (different palettes per LinkedIn vs Instagram) — revisit after cross-platform engagement data proves the need
- Animated infographic tokens — Spec 033 covers animation parameters independently

## Acceptance Criteria

- [ ] `ToolRegistry` class is importable from `holus.visual.registry` and loads 5 token sets from `config/tokens/` at initialization
- [ ] `get_treatment(content_type, intent)` returns a `VisualTreatment` Pydantic model for all 10 valid (content_type, intent) combinations that have templates (carousel × 5 + single_image × 5)
- [ ] `TemplateEngine.render()` accepts an optional `treatment` parameter and injects token values as CSS custom properties
- [ ] Rendering a carousel without a treatment produces identical output to the current system (zero visual regression)
- [ ] Rendering a carousel with each of the 5 token sets produces visually distinct output (different colors, fonts)
- [ ] Every carousel and single_image content piece logged to `trajectory.jsonl` includes a `visual_treatment` object
- [ ] `scripts/migrate_brand_to_tokens.py` generates 5 valid JSON token files from the current `brand-visual.yaml`
- [ ] All existing tests pass without modification (`just check` passes)
- [ ] `ToolRegistry` raises `RegistryValidationError` on startup if any token file is missing or invalid
