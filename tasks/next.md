# NEXT: Authority Engine Build

## The Goal

Position Camilo as the go-to AI transition consultant. In 2 months: NYC consulting
launch targeting companies that need AI transformation. LinkedIn is the primary
pipeline. Other platforms grow slowly. Products (Pilaster, genpeli, invoz) are proof
of expertise, not the pitch.

Holus becomes an authority-building engine that:
1. Researches what's working in the niche RIGHT NOW
2. Extracts viral frameworks from top performers
3. Creates content using those patterns in Camilo's voice
4. Posts LinkedIn-first, then repurposes to all other platforms
5. Tracks what converts to inbound consulting leads

---

## Layer 1: Identity — `config/brand.yaml` (NEW FILE)

**What:** The foundational "who is Camilo" file. Loaded into every agent cycle.
**Status:** Does not exist. Must be created.

Write together with Camilo. Must define:

- **Story:** Colombian AI engineer, built 3 production AI products, now helping
  companies do the same. Not a consultant who reads slides — a builder who ships.
- **Positioning:** "I build AI systems that actually work in production. I help
  companies do the same." Not an AI influencer. A practitioner.
- **The Offer:** AI transition consulting. Help companies integrate AI into their
  workflows, pick the right tools, avoid the hype, ship real results.
- **Target Client:** CTOs, VPs of Engineering, founders of mid-size companies
  considering AI transformation. NYC market initially.
- **Products as Proof:**
  - Pilaster = "I built an AI image platform with memory. Here's what I learned."
  - genpeli = "I automated my video editing pipeline. Here's the architecture."
  - invoz = "I built an audio ML API. Here's how Whisper works in production."
- **Voice:** Direct. Technical but accessible. Builder mindset. Shows real numbers.
  No fluff, no buzzwords. Bilingual (EN primary, ES for specific audiences).
- **What Camilo is NOT:** Not a guru. Not selling a course. Not "10x your revenue
  with AI." A builder who shows the work and helps companies do the same.
- **Competitor accounts to study:** (fill in with Camilo — who does he follow,
  who's doing this well, whose style resonates)

### Action
- [ ] Sit with Camilo and write `config/brand.yaml`
- [ ] Update `config/products.yaml` — reframe products as proof points
- [ ] Fill in voice profile with examples of Camilo's actual writing

---

## Layer 2: Strategy — Rewrite Knowledge Files

**What:** Shift all strategy files from "promote products" to "build authority for
consulting pipeline."
**Status:** Files exist but are product-focused, not authority-focused.

### Rewrite `.self-improvement/knowledge/current/content-marketing-strategy.md`
Current: generic research questions about content marketing.
Needed:
- LinkedIn is PRIMARY. Everything else is secondary.
- Content pillars for authority:
  1. **Builder stories** — "I built X, here's what I learned" (Pilaster, genpeli, invoz)
  2. **AI implementation frameworks** — "How to actually deploy AI in your company"
  3. **Industry analysis** — "What's working in AI right now and what's hype"
  4. **Results/proof** — Real numbers, real architectures, real outcomes
  5. **Contrarian takes** — "Everyone's doing X wrong. Here's why."
- Posting cadence: 5x/week on LinkedIn, 3x/week other platforms
- NYC consulting launch timeline: 2 months out
- Content should generate inbound DMs and discovery calls, not just likes

### Rewrite `.self-improvement/knowledge/current/audience-profiles.md`
Current: product users (AI artists, video creators, developers).
Needed: ADD a primary audience:
- **Consulting prospects:** CTOs, VPs Eng, founders at companies with 50-500
  employees considering AI. They're on LinkedIn. They want someone who's done it.
- Keep product audiences as secondary (they build brand, not consulting pipeline)

### Rewrite `.self-improvement/knowledge/current/platforms.md`
Needed: LinkedIn-first strategy with specific tactics:
- Hook patterns that work on LinkedIn (study competitors)
- Post formats: text posts, carousels, document posts, video
- Engagement tactics: comments, DMs, community participation
- Algorithm signals: dwell time, comments > likes, shares = gold
- Other platforms: repurpose LinkedIn content, don't create separate

### Action
- [ ] Rewrite content-marketing-strategy.md (authority + consulting focus)
- [ ] Rewrite audience-profiles.md (add consulting prospect audience)
- [ ] Rewrite platforms.md (LinkedIn-first playbook)
- [ ] Review and update growth-engine-vision.md (align with consulting goal)

---

## Layer 3: Niche Research — NEW CAPABILITY

**What:** Holus goes online, finds what's working in the niche, extracts patterns,
and feeds them into content creation. This is the "spy on competitors" step.
**Status:** Does not exist. Needs to be designed and built.

### How It Works

Add a **research step** to the marketing agent's observe stage:

```
OBSERVE (current)
  → read analytics from social-media MCP
  → read product state
  → read MEMORY.md

OBSERVE (new)
  → read analytics from social-media MCP
  → read product state
  → read MEMORY.md
  → NEW: research niche (web search for trending content)
  → NEW: analyze competitor posts (what's getting engagement)
  → NEW: extract viral patterns (hooks, structures, CTAs)
```

### Implementation Options

**Option A: Web search in the agent loop (simplest, do this first)**
- Marketing agent uses web search tool during observe stage
- Searches: "LinkedIn AI consulting viral posts this week"
- Searches: competitor names + "LinkedIn" + recent timeframe
- Extracts patterns from search results
- Stores findings in knowledge/current/niche-trends.md

**Option B: Dedicated research agent (Phase 2)**
- Separate agent that runs daily, focused only on niche research
- Monitors specific accounts, hashtags, topics
- Builds a library of viral frameworks with examples
- Feeds findings into the marketing agent's knowledge base

**Option C: Social media MCP enhancement (Phase 2+)**
- Add competitor monitoring tools to social-media-automatization
- Tools: `search_niche_posts`, `analyze_competitor`, `extract_patterns`
- Structured data instead of web scraping

### What the Agent Learns From Research

For each viral post found:
- **Hook:** What was the first line? Why does it stop the scroll?
- **Structure:** How is the post organized? (list, story, framework, contrarian)
- **Proof:** What evidence is shown? (numbers, screenshots, before/after)
- **CTA:** What's the call to action? (comment, DM, link)
- **Why it worked:** Algorithm signals (comments, shares, dwell time)

Store as a growing library in:
`.self-improvement/knowledge/current/viral-frameworks.md`

### Action
- [ ] Design the research step for the observe stage
- [ ] Define competitor accounts to monitor (with Camilo)
- [ ] Define search queries for niche research
- [ ] Build viral-frameworks.md with initial examples (from that LinkedIn post + others)
- [ ] Add web search capability to marketing agent spec

---

## Layer 4: Execution — Update Marketing Agent

**What:** Update the marketing agent to use all the new layers.
**Status:** Spec exists (010), code not built yet. Update spec before building.

### Changes Needed in Spec 010

The agent's reason stage should think:

> "Based on my niche research, carousel posts about AI implementation
> frameworks are getting 5x engagement this week on LinkedIn. Camilo
> just shipped a new feature in Pilaster that demonstrates workflow
> versioning. I'll create a carousel: 'How I Version-Control My AI
> Workflows (And Why Your Team Should Too)' — using the authority
> framework from brand.yaml, the viral hook pattern from research,
> and the builder-story content pillar from strategy."

Instead of:

> "Pilaster has a new feature. I'll post about it on LinkedIn."

### Content Repurposing Flow

```
LinkedIn post (primary, optimized for LinkedIn algorithm)
  → Twitter thread (condensed, more direct)
  → Instagram carousel (visual version)
  → Threads post (conversational version)
  → Facebook post (if bilingual, ES version too)
```

One piece of content, 5 platforms. The social-media MCP handles the posting.
The agent handles the adaptation per platform.

### Action
- [ ] Update spec 010 to include brand.yaml reading in observe stage
- [ ] Update spec 010 to include niche research in observe stage
- [ ] Update spec 010 reason stage to use authority framing
- [ ] Update spec 010 act stage for content repurposing across platforms
- [ ] Define the content repurposing logic (LinkedIn → all others)

---

## Priority Order (What to Do First)

### Tomorrow (Day 1)
1. Write `config/brand.yaml` with Camilo — this is the foundation
2. Rewrite strategy + audience knowledge files — align everything to consulting
3. Seed `viral-frameworks.md` with examples from research

### Day 2
4. Update spec 010 — add brand, research, and repurposing to the agent loop
5. Design the niche research capability (Option A first)

### Day 3+
6. Start building the actual marketing agent code (spec 010 execution)
7. Build the niche research step
8. First real content cycle: research → create → post → track

---

## The End State

Holus wakes up every morning and:
1. Checks what went viral in the AI consulting niche overnight
2. Reads Camilo's brand identity and current strategy
3. Picks a content pillar and viral framework
4. Creates a LinkedIn post that sounds like Camilo, uses proven patterns
5. Adapts it for all other platforms
6. Posts everything via social-media MCP
7. Tracks what converts to consulting inbound
8. Learns and improves for tomorrow

Camilo reviews once a week. Content flows non-stop. Authority builds.
By the time NYC consulting launch happens, the pipeline is warm.
