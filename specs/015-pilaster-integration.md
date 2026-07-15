# Spec 015: Pilaster Integration

**Status:** partial
**Phase:** Phase 1
**Author:** Camilo Martinez
**Created:** 2026-02-27
**Updated:** 2026-02-27

## Problem

The marketing agent needs to generate images that are visually consistent across all
posts, videos, and platforms. Without access to Pilaster's character registry, generation
abstraction, and experiment memory, the agent has no way to maintain brand identity, reuse
successful prompts, or avoid repeating generation failures. Every image generation becomes
a cold start with no institutional knowledge.

## Goals

- Marketing agent can generate images with consistent character identity across all posts via Pilaster's character registry and LoRAs
- Agent picks from reusable generation presets (templates) instead of configuring settings manually each time
- Agent queries past experiments to learn which prompts and settings produced high-quality images
- Agent stores every generation outcome so the knowledge base grows with each cycle
- Agent retrieves successful parameter sets for reuse, avoiding reinvention each cycle
- Characters look the same across social posts, videos, and website without manual effort
- Generation backends (ComfyUI, Replicate, Runway) are swappable without losing characters or memory

## Non-Goals

- Direct ComfyUI workflow editing — Pilaster stores workflows but editing is done in ComfyUI itself
- Real-time collaboration on experiments — single-user system for now, no concurrent editing needed
- Experiment forking/branching — linear history only, branching adds complexity without clear benefit at this stage
- Public sharing of experiments — private workspace only, no multi-tenant requirements yet

## Solution

Pilaster is an AI image generation platform with memory. It owns three layers:
(1) **Character registry** — LoRAs, reference sheets, and metadata for consistent
characters across all generations. (2) **Generation abstraction** — a backend-agnostic
interface that delegates to ComfyUI, Replicate, Runway, or any future engine. Users
never see nodes — they pick a character, a template, and generate. (3) **Experiment
memory** — tracks every generation with outcomes and quality scores, learns what
prompts/settings work, warns before repeating failures.

The integration follows the federated MCP pattern: Pilaster runs as an independent
Next.js app with its own database, swappable generation backends, and **its own MCP
server** (already built, 8 tools). Holus connects to it — no wrapper code lives in Holus.

**Key architectural decision (ADR-0004):** Pilaster is a generation platform, not a
ComfyUI plugin. Backends are swappable. The memory, characters, and templates are the
product. See `docs/decisions/0004-pilaster-generation-platform.md`.

## Implementation Notes

### SPEC-001: Pilaster MCP Server

| Field | Value |
|-------|-------|
| Description | Pilaster's MCP server (in the pilaster repo) exposes the full platform as tools. Holus connects to it — no wrapper code in Holus. |
| Trigger | Marketing agent connects to the MCP server at startup |
| Input | Tool calls from the marketing agent (generate with character, list characters, query experiments, etc.) |
| Output | Tool results (generated images, character data, experiment history, recommendations) |
| Validation | All inputs validated by Pilaster MCP server before processing |
| Auth Required | `PILASTER_API_KEY` (server-side, in pilaster repo) |

**NOTE:** The MCP server code lives in the **pilaster repo**, not in Holus.

**Existing Pilaster MCP tools (already built):**

| Tool | Description |
|------|-------------|
| `create_character` | Register a new character with metadata and reference images |
| `update_character` | Update character LoRA, references, or metadata |
| `save_version` | Save a workflow version snapshot |
| `list_versions` | List all saved versions for a workflow |
| `load_version` | Load a specific workflow version |
| `generate_image` | Generate an image using backend-agnostic abstraction |
| `list_workflows` | List available ComfyUI workflows |
| `search_snapshots` | Search past generation snapshots by criteria |

**MCP tools to be added in pilaster repo:**

| Tool | Description |
|------|-------------|
| `get_templates` | List reusable generation presets (product-shot, anime, etc.) |
| `get_successful_prompts` | Get prompts that produced high-quality images |
| `get_ai_suggestions` | AI-powered recommendations based on past experiments |

MCP server configuration for Holus (in `.claude/settings.json`):

```json
{
  "mcpServers": {
    "pilaster": {
      "command": "node",
      "args": ["mcp-server/index.js"],
      "cwd": "/Users/mini/.openclaw/workspace/github/pilaster",
      "env": {
        "PILASTER_API_KEY": "${PILASTER_API_KEY}"
      }
    }
  }
}
```

### SPEC-002: Structured Prompt Recipe Format

When calling Pilaster's `generate_image` tool, agents MUST send a structured recipe —
never a flat prompt string. The recipe decomposes image intent into the same dimensions
that ComfyUI nodes control, making it work identically across all backends (DALL-E, Imagen,
Fal, Gemini, ComfyUI).

**Recipe fields:**

| Field | Maps to (ComfyUI) | Purpose | Example |
|-------|-------------------|---------|---------|
| `subject` | CLIPTextEncode (positive) | What's in the image | "a monitoring dashboard with agent status grid" |
| `style` | Checkpoint + LoRA | Visual aesthetic | "dark UI, glassmorphism, cyan/purple accents" |
| `composition` | ControlNet / IPAdapter | Layout and framing | "screenshot-style, centered, 16:9" |
| `lighting` | KSampler (cfg_scale) | Mood and atmosphere | "dark background, glowing elements" |
| `quality` | KSampler (steps) | Detail and rendering | "clean vector rendering, sharp edges" |
| `negative` | CLIPTextEncode (negative) | What to avoid | "no photos, no watermarks, no blur" |
| `dimensions` | EmptyLatentImage | Width × height | `{ "width": 1792, "height": 1024 }` |

**Example MCP call from Holus:**

```python
result = await self.call_mcp(
    "pilaster",
    "generate_image",
    backend="dalle3",  # or "imagen3", "fal", "comfyui"
    recipe={
        "subject": "a multi-agent orchestration system with Redis event bus",
        "style": "dark technical diagram, neon connection lines, minimal",
        "composition": "wide landscape, system architecture layout",
        "lighting": "dark background, glowing nodes and edges",
        "quality": "clean vector style, professional, portfolio-grade",
        "negative": "no stock photos, no people, no 3D renders",
    },
    dimensions={"width": 1792, "height": 1024},
)
```

Pilaster assembles the recipe into a single prompt for prompt-based backends (DALL-E,
Imagen, Fal, Gemini) or maps fields to nodes for ComfyUI. The agent never needs to
know which backend is handling the request.

**Why structured > flat prompts:**
- **Iterate one dimension** without rewriting everything (change style, keep subject)
- **Memory engine** tracks failures at the field level ("this style failed 3 times")
- **Cross-backend** — same recipe, swap backend, compare results
- **Agent-friendly** — maps directly to content strategy decisions

### SPEC-003: Marketing Agent Integration

| Field | Value |
|-------|-------|
| Description | Marketing agent discovers and uses Pilaster tools to inform image generation decisions |
| Trigger | Marketing agent reason stage decides to create image content |
| Input | Content decision with visual requirements |
| Output | Informed image generation prompts based on past successes |
| Validation | Image decisions must specify style, purpose, and platform |
| Auth Required | MCP server handles auth |

Image generation workflow with Pilaster memory:

```python
# src/holus/agents/marketing/image_workflow.py

async def create_image_content(self, decision: ContentDecision) -> dict:
    """Create image content using Pilaster memory for informed decisions."""

    # Step 1: Query Pilaster for successful prompts in this style
    successful_prompts = await self.call_mcp(
        "pilaster",
        "get_successful_prompts",
        style=decision.get("image_style", "product"),
        limit=3,
    )

    prompts_data = json.loads(successful_prompts)

    # Step 2: Get AI suggestions based on topic
    ai_suggestions = await self.call_mcp(
        "pilaster",
        "get_ai_suggestions",
        topic=decision["topic"],
        context=f"Platform: {decision['platform']}, Purpose: {decision['content_type']}",
    )

    # Step 3: Build informed prompt using successful patterns
    prompt = self.build_informed_prompt(
        decision=decision,
        successful_patterns=prompts_data,
        ai_suggestions=json.loads(ai_suggestions),
    )

    # Step 4: Generate image (via Replicate or ComfyUI)
    image_url, quality_score = await self.generate_image(
        prompt=prompt["text"],
        negative_prompt=prompt.get("negative", ""),
        settings=prompt.get("settings", {}),
    )

    # Step 5: Store experiment outcome in Pilaster
    snapshot_id = await self.call_mcp(
        "pilaster",
        "store_experiment",
        intent=f"Create {decision['content_type']} image for {decision['product']} on {decision['platform']}",
        prompt=prompt["text"],
        negative_prompt=prompt.get("negative", ""),
        outcome="worked" if quality_score >= 7.0 else "mixed",
        quality_score=quality_score,
        settings=json.dumps(prompt.get("settings", {})),
    )

    return {
        "image_url": image_url,
        "quality_score": quality_score,
        "snapshot_id": snapshot_id,
        "prompt_used": prompt["text"],
        "learned_from": len(prompts_data),
    }


def build_informed_prompt(
    self,
    decision: ContentDecision,
    successful_patterns: list[dict],
    ai_suggestions: dict,
) -> dict:
    """Build a prompt informed by past successes and AI suggestions."""

    # Extract common patterns from successful prompts
    common_elements = self.extract_common_elements(successful_patterns)

    # Combine decision intent, successful patterns, and AI suggestions
    prompt_text = f"{decision['topic']}, "
    prompt_text += ", ".join(common_elements[:3])
    prompt_text += f", {ai_suggestions.get('style_recommendation', '')}"

    # Use settings from highest-scoring successful experiment
    best_settings = {}
    if successful_patterns:
        best = max(successful_patterns, key=lambda p: p.get("quality_score", 0))
        best_settings = best.get("settings", {})

    return {
        "text": prompt_text.strip(),
        "negative": ai_suggestions.get("negative_prompt", ""),
        "settings": best_settings,
    }
```

### SPEC-003: Content Types Supported

| Content Type | Available Now | Needs Tooling |
|--------------|---------------|---------------|
| **Product screenshots** (UI captures) | YES | None (query "product screenshots") |
| **Abstract backgrounds** (social headers) | YES | None (query "abstract backgrounds") |
| **Technical diagrams** (architecture visuals) | YES | None (query "technical diagrams") |
| **AI-generated scenes** (Flux Schnell via Replicate) | YES | Replicate backend in Pilaster |
| **ComfyUI custom workflows** (advanced generation) | PARTIAL | ComfyUI backend in Pilaster |
| **Template-based graphics** (quote cards, announcements) | NO | Image template engine (new tool) |
| **Photo editing** (adjustments, filters) | NO | Image editing pipeline |
| **Multi-image compositions** (collages, comparisons) | NO | Composition engine |

### SPEC-004: Memory-Driven Optimization

| Field | Value |
|-------|-------|
| Description | As experiments accumulate, Pilaster memory improves prompt quality and success rates |
| Trigger | Monthly analysis of stored experiments |
| Input | All experiments with outcomes from the past 30 days |
| Output | Updated best practices, prompt templates, quality baselines |
| Validation | Minimum 20 experiments required for meaningful analysis |
| Auth Required | No (internal analysis) |

Memory-driven optimization workflow:

```python
# src/holus/agents/marketing/image_optimization.py

async def optimize_image_strategy(self) -> dict:
    """Monthly analysis of image generation experiments to improve prompts."""

    # Query all experiments from past 30 days
    experiments = await self.call_mcp(
        "pilaster",
        "query_experiments",
        query="*",  # All experiments
        outcome_filter="",  # All outcomes
        limit=100,
    )

    data = json.loads(experiments)

    if len(data) < 20:
        return {"status": "insufficient_data", "count": len(data)}

    # Analyze success patterns
    analysis = {
        "total_experiments": len(data),
        "success_rate": len([e for e in data if e["outcome"] == "worked"]) / len(data),
        "avg_quality": sum(e.get("quality_score", 0) for e in data) / len(data),
        "top_styles": self.extract_top_styles(data),
        "failed_patterns": self.extract_failed_patterns(data),
    }

    # Update knowledge base with findings
    await self.update_knowledge(
        section="image-generation",
        insights=analysis,
    )

    return analysis
```

### Data Structures

Pilaster experiment (what the MCP server returns):

```json
{
  "snapshot_id": "snap-20260227-001",
  "intent": "Create product screenshot for Pilaster on LinkedIn",
  "outcome": "worked",
  "quality_score": 8.5,
  "workflow": {
    "nodes": {
      "1": {
        "class_type": "CLIPTextEncode",
        "inputs": {
          "text": "modern web application interface, clean design, purple accents, screenshot style"
        }
      }
    },
    "settings": {
      "steps": 20,
      "cfg_scale": 7.0,
      "sampler_name": "euler"
    }
  },
  "created_at": "2026-02-27T10:00:00Z",
  "image_url": "https://r2.pilaster.ai/outputs/snap-20260227-001.png"
}
```

### File Locations

**In Holus repo:**

| File | Change Type | Description |
|------|-------------|-------------|
| `.claude/settings.json` | Modified | Add pilaster MCP server config |
| `src/holus/agents/marketing/image_workflow.py` | New | Image creation workflow |
| `src/holus/agents/marketing/image_optimization.py` | New | Monthly image strategy optimization |
| `agentic/memory/knowledge/current/image-generation.md` | New | Image generation best practices |

**In pilaster repo (to be added to existing MCP server):**

| Tool | Description |
|------|-------------|
| `get_templates` | List reusable generation presets |
| `get_successful_prompts` | Get prompts with high quality scores |
| `get_ai_suggestions` | AI-powered generation recommendations |

### Security Notes

- `PILASTER_API_KEY` stored in `.env` only, never in code
- Pilaster API key provides access to all experiments — protect it
- Experiment data may contain brand-sensitive prompts — encrypted in DB
- Generated image URLs are public (R2 hosted) — no sensitive content in images

### Dependencies

- Depends on: [Spec 010](./010-marketing-agent.md) — the marketing agent that calls Pilaster tools
- Depended on by: [Spec 016](./016-social-media-integration-v2.md) — social media distribution uses images from Pilaster
- Related: [Spec 014](./014-genpeli-integration.md) — video creation silo (parallel integration)

## Edge Cases & Failure Modes

**EDGE-001: Pilaster API unavailable**
- Scenario: Pilaster service is down or unreachable
- Expected behavior: Image generation continues without memory lookup. Default prompts used. Outcome storage deferred.
- Recovery: Retry outcome storage when service returns.

**EDGE-002: No successful experiments for requested style**
- Scenario: Agent requests "technical diagrams" but no successful experiments exist
- Expected behavior: Agent uses AI suggestions only. Generates image and stores as first experiment for this style.
- Recovery: Automatic — first experiment becomes reference for future generations.

**EDGE-003: All past experiments for a style failed**
- Scenario: Agent queries "abstract backgrounds" and finds only failed experiments
- Expected behavior: Agent learns what NOT to do. AI suggestions guide toward different approach.
- Recovery: Automatic — agent adjusts prompt away from failed patterns.

**EDGE-004: Quality score below threshold after memory-informed generation**
- Scenario: Image generated using successful patterns still scores < 7.0
- Expected behavior: Regenerate once with modified prompt. If still failing, store as "mixed" outcome and flag for review.
- Recovery: Human reviews and adjusts prompt template for future use.

## Observability

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Query experiments | < 3s | MCP call latency |
| Get successful prompts | < 3s | MCP call latency |
| Store experiment | < 2s | MCP call latency |
| AI suggestions | < 10s | Pilaster API (Anthropic call) |
| Gallery retrieval | < 5s | MCP call latency |
| Monthly optimization | < 2 min | Analysis runtime |

## Acceptance Criteria

- [ ] Pilaster MCP server (in pilaster repo) responds to `tools/list`
- [ ] `generate_image` tool generates images with character + template support
- [ ] `search_snapshots` tool searches past experiments by topic/style
- [ ] `get_successful_prompts` tool returns prompts that worked well (to be added)
- [ ] `get_templates` tool lists available generation presets (to be added)
- [ ] `get_ai_suggestions` tool provides AI-powered recommendations (to be added)
- [ ] Holus can connect to pilaster MCP via `.claude/settings.json` config
- [ ] All tools have clear descriptions and typed arguments
- [ ] Marketing agent discovers Pilaster tools via MCP
- [ ] Agent queries successful prompts before generating images
- [ ] Agent uses successful patterns to inform new prompts
- [ ] Agent stores every generation outcome in Pilaster
- [ ] Agent learns from past failures (avoids repeating failed experiments)
- [ ] Prompt quality improves over time as memory grows
- [ ] Monthly optimization runs when 20+ experiments exist
- [ ] Analysis identifies successful prompt patterns
- [ ] Analysis identifies failed patterns to avoid
- [ ] Insights written to `agentic/memory/knowledge/current/image-generation.md`
- [ ] Success rate trends tracked over time
