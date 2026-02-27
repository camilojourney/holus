# Spec 015: Pilaster Integration

## Feature: AI image generation memory layer integration for informed content creation

### Overview

Pilaster is Holus's memory layer for AI image generation experiments. It tracks ComfyUI workflows, compares versions, and warns when repeating failed experiments. This spec defines how the marketing agent discovers and uses Pilaster's capabilities through an MCP server, enabling data-informed image generation decisions. The integration follows the federated MCP pattern: Pilaster runs as an independent Next.js app with its own database, and the MCP server translates marketing agent intentions into Pilaster API calls.

### User Stories

- As the marketing agent, I want to query past image generation experiments so that I learn what prompts and settings work.
- As the marketing agent, I want to store new experiments with outcomes so that the knowledge base grows.
- As the marketing agent, I want to retrieve successful parameter sets for reuse so that I don't reinvent the wheel.
- As a founder, I want a memory of what visual styles performed best so that brand consistency improves over time.

---

### Core Specifications

**SPEC-001: Pilaster MCP Server**

| Field | Value |
|-------|-------|
| Description | Local MCP server that exposes Pilaster's experiment memory as tools the marketing agent can discover and call |
| Trigger | Marketing agent connects to the MCP server at startup |
| Input | Tool calls from the marketing agent (query experiments, store outcomes, get suggestions) |
| Output | Tool results (experiment history, parameter recommendations, AI suggestions) |
| Validation | All inputs validated before passing to Pilaster API |
| Auth Required | `PILASTER_API_KEY` (server-side) |

```python
# src/holus/mcp_servers/pilaster.py

from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("pilaster")

PILASTER_API = "http://localhost:3000"
PILASTER_API_KEY = os.environ["PILASTER_API_KEY"]


@mcp.tool()
async def query_experiments(
    query: str,
    outcome_filter: str = "",
    limit: int = 10,
) -> str:
    """Search past image generation experiments by topic, style, or outcome.

    Args:
        query: Search query (e.g., "product screenshots", "abstract backgrounds")
        outcome_filter: Filter by outcome: "worked", "mixed", "failed", or "" for all
        limit: Maximum results to return (default 10)

    Returns:
        JSON array of matching experiments with prompts, outcomes, and quality scores
    """
    async with httpx.AsyncClient() as client:
        params = {"q": query, "limit": limit}
        if outcome_filter:
            params["outcome"] = outcome_filter
        
        response = await client.get(
            f"{PILASTER_API}/api/snapshots",
            params=params,
            headers={"Authorization": f"Bearer {PILASTER_API_KEY}"},
        )
        response.raise_for_status()
        return response.text


@mcp.tool()
async def get_successful_prompts(style: str = "default", limit: int = 5) -> str:
    """Get prompts that generated high-quality images in the past.

    Args:
        style: Image style filter (e.g., "product", "abstract", "technical")
        limit: Maximum prompts to return (default 5)

    Returns:
        JSON array of successful prompts with quality scores and settings
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PILASTER_API}/api/snapshots",
            params={"outcome": "worked", "style": style, "limit": limit},
            headers={"Authorization": f"Bearer {PILASTER_API_KEY}"},
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract prompts and scores
        prompts = []
        for snapshot in data:
            workflow = snapshot.get("workflow", {})
            # Parse ComfyUI workflow for prompt nodes
            for node_id, node in workflow.get("nodes", {}).items():
                if node.get("class_type") == "CLIPTextEncode":
                    prompts.append({
                        "prompt": node["inputs"]["text"],
                        "quality_score": snapshot.get("quality_score", "N/A"),
                        "settings": {
                            "steps": workflow.get("steps", 20),
                            "cfg": workflow.get("cfg_scale", 7.0),
                            "sampler": workflow.get("sampler_name", "euler"),
                        },
                    })
        
        import json
        return json.dumps(prompts[:limit])


@mcp.tool()
async def store_experiment(
    intent: str,
    prompt: str,
    negative_prompt: str = "",
    outcome: str = "worked",
    quality_score: float = 0.0,
    settings: str = "{}",
) -> str:
    """Store a new image generation experiment with outcome.

    Args:
        intent: What you were trying to create
        prompt: The generation prompt used
        negative_prompt: Negative prompt (optional)
        outcome: Result: "worked", "mixed", or "failed"
        quality_score: Quality assessment score (0-10)
        settings: JSON string with generation parameters

    Returns:
        snapshot_id for the stored experiment
    """
    import json
    
    # Build minimal ComfyUI workflow structure
    workflow = {
        "nodes": {
            "1": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt},
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt},
            },
        },
        "settings": json.loads(settings),
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PILASTER_API}/api/snapshots",
            json={
                "intent": intent,
                "outcome": outcome,
                "workflow": workflow,
                "quality_score": quality_score,
            },
            headers={"Authorization": f"Bearer {PILASTER_API_KEY}"},
        )
        response.raise_for_status()
        data = response.json()
        return data["snapshot_id"]


@mcp.tool()
async def get_ai_suggestions(topic: str, context: str = "") -> str:
    """Get AI-powered suggestions for image generation based on past experiments.

    Args:
        topic: What you want to create
        context: Additional context (platform, purpose, etc.)

    Returns:
        AI suggestions with prompt recommendations
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PILASTER_API}/api/snapshots/suggestions",
            json={"topic": topic, "context": context},
            headers={"Authorization": f"Bearer {PILASTER_API_KEY}"},
        )
        response.raise_for_status()
        return response.text


@mcp.tool()
async def get_gallery_images(
    limit: int = 20,
    quality_min: float = 7.0,
) -> str:
    """Get recent high-quality generated images from the gallery.

    Args:
        limit: Maximum images to return (default 20)
        quality_min: Minimum quality score (default 7.0)

    Returns:
        JSON array of image URLs with metadata
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PILASTER_API}/api/gallery",
            params={"limit": limit, "min_quality": quality_min},
            headers={"Authorization": f"Bearer {PILASTER_API_KEY}"},
        )
        response.raise_for_status()
        return response.text


if __name__ == "__main__":
    mcp.run()
```

MCP server configuration for marketing agent:

```json
{
  "mcpServers": {
    "pilaster": {
      "command": "python",
      "args": ["-m", "holus.mcp_servers.pilaster"],
      "cwd": "/Users/mini/.openclaw/workspace/github/holus",
      "env": {
        "PILASTER_API_KEY": "${PILASTER_API_KEY}"
      }
    }
  }
}
```

Acceptance Criteria:
- [ ] MCP server starts and responds to `tools/list`
- [ ] `query_experiments` tool searches past experiments by topic/style
- [ ] `get_successful_prompts` tool returns prompts that worked well
- [ ] `store_experiment` tool saves new experiments with outcomes
- [ ] `get_ai_suggestions` tool provides AI-powered recommendations
- [ ] `get_gallery_images` tool retrieves high-quality generated images
- [ ] All tools have clear descriptions and typed arguments

---

**SPEC-002: Marketing Agent Integration**

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

Acceptance Criteria:
- [ ] Marketing agent discovers Pilaster tools via MCP
- [ ] Agent queries successful prompts before generating images
- [ ] Agent uses successful patterns to inform new prompts
- [ ] Agent stores every generation outcome in Pilaster
- [ ] Agent learns from past failures (avoids repeating failed experiments)
- [ ] Prompt quality improves over time as memory grows

---

**SPEC-003: Content Types Supported**

| Content Type | Available Now | Needs Tooling |
|--------------|---------------|---------------|
| **Product screenshots** (UI captures) | ✅ YES | None (query "product screenshots") |
| **Abstract backgrounds** (social headers) | ✅ YES | None (query "abstract backgrounds") |
| **Technical diagrams** (architecture visuals) | ✅ YES | None (query "technical diagrams") |
| **AI-generated scenes** (Flux Schnell via Replicate) | ✅ YES | Replicate integration (Spec 003) |
| **ComfyUI custom workflows** (advanced generation) | ⚠️ PARTIAL | ComfyUI integration (Spec 003) |
| **Template-based graphics** (quote cards, announcements) | ❌ NO | Image template engine (new tool) |
| **Photo editing** (adjustments, filters) | ❌ NO | Image editing pipeline |
| **Multi-image compositions** (collages, comparisons) | ❌ NO | Composition engine |

---

**SPEC-004: Memory-Driven Optimization**

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

Acceptance Criteria:
- [ ] Monthly optimization runs when 20+ experiments exist
- [ ] Analysis identifies successful prompt patterns
- [ ] Analysis identifies failed patterns to avoid
- [ ] Insights written to `.self-improvement/knowledge/current/image-generation.md`
- [ ] Success rate trends tracked over time

---

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

---

### File Locations

| File | Change Type | Description |
|------|-------------|-------------|
| `src/holus/mcp_servers/__init__.py` | Modified | Export pilaster server |
| `src/holus/mcp_servers/pilaster.py` | New | Pilaster MCP server |
| `src/holus/agents/marketing/image_workflow.py` | New | Image creation workflow |
| `src/holus/agents/marketing/image_optimization.py` | New | Monthly image strategy optimization |
| `.self-improvement/knowledge/current/image-generation.md` | New | Image generation best practices |
| `tests/unit/mcp/test_pilaster.py` | New | Pilaster MCP server tests |

---

### Edge Cases & Error Handling

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

---

### Performance Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Query experiments | < 3s | MCP call latency |
| Get successful prompts | < 3s | MCP call latency |
| Store experiment | < 2s | MCP call latency |
| AI suggestions | < 10s | Pilaster API (Anthropic call) |
| Gallery retrieval | < 5s | MCP call latency |
| Monthly optimization | < 2 min | Analysis runtime |

---

### Security Considerations

- `PILASTER_API_KEY` stored in `.env` only, never in code
- Pilaster API key provides access to all experiments — protect it
- Experiment data may contain brand-sensitive prompts — encrypted in DB
- Generated image URLs are public (R2 hosted) — no sensitive content in images

---

### Out of Scope

- Direct ComfyUI workflow editing (Pilaster stores workflows, doesn't edit them)
- Real-time collaboration on experiments (single-user for now)
- Experiment forking/branching (linear history only)
- Public sharing of experiments (private workspace only)

---

### Related Specs

- [010-marketing-agent.md](./010-marketing-agent.md) — the agent that calls Pilaster tools
- [003-content-pipeline.md](./003-content-pipeline.md) — full image generation pipeline
- [011-social-media-integration.md](./011-social-media-integration.md) — social media distribution

---

**Last Updated:** 2026-02-27  
**Status:** Draft  
**Owner:** Camilo Martinez
