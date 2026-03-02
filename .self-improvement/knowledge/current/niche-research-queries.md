# Knowledge: Niche Research Queries

**Last updated:** 2026-03-01
**Updated by:** builder agent (cycle 29 — niche research capability)
**Confidence:** medium (curated from brand positioning + niche analysis; refine as we learn which queries return actionable results)
**Affects:** marketing agent observe stage (SPEC-006), niche research sub-step
**Research cadence:** monthly (add new queries, retire low-yield ones, update search operators)

---

## How This File Is Used

The marketing agent reads this file during the **observe** stage (SPEC-006).
Each cycle, it selects 3-5 queries across categories using rotation logic,
executes them via Claude tool_use with web_search, and extracts structured
insights (NicheInsight) for the reason stage.

**Query rotation rules:**
- Never repeat a query within its rotation period (daily or weekly)
- Prioritize stale categories (least recently searched)
- Always include at least 1 query from `trending_topics` or `industry_news` (freshness)
- Track execution history in `data/.niche-research-state.json`

**Query refresh process:**
- Monthly: review which queries returned actionable insights vs. noise
- Retire queries that consistently return spam, aggregator content, or off-topic results
- Add new queries based on emerging topics from reason stage recommendations
- Update temporal markers (year references) annually

---

## Query Categories

```yaml
queries:
  # ─── COMPETITOR CONTENT ──────────────────────────────────────────────────
  # What top AI consultants/builders are posting on LinkedIn.
  # Goal: extract hooks, structures, proof patterns, and CTAs from real posts.

  competitor_content:
    description: "What top AI consultants and builders are posting on LinkedIn"
    rotation: weekly
    queries:
      - query: "site:linkedin.com AI consulting thought leadership 2026"
        intent: "Find consultant-authored posts with strong positioning"
        good_signals: ["first-person narrative", "specific results", "framework sharing"]
        noise_signals: ["job postings", "company pages", "news articles"]

      - query: "site:linkedin.com AI implementation strategy CTO advice"
        intent: "Find posts targeting the same prospect persona we target"
        good_signals: ["technical depth", "decision-maker language", "ROI framing"]
        noise_signals: ["vendor marketing", "generic AI hype"]

      - query: "site:linkedin.com AI transformation consultant results case study"
        intent: "Find proof-based posts from practitioners"
        good_signals: ["concrete metrics", "before/after", "client outcomes"]
        noise_signals: ["press releases", "sales pages"]

      - query: "site:linkedin.com 'I built' AI production system"
        intent: "Find builder-reveal posts from AI practitioners"
        good_signals: ["architecture details", "lessons learned", "time/cost metrics"]
        noise_signals: ["tutorial aggregators", "course promotions"]

      - query: "site:linkedin.com AI consultant 'here is what I learned' OR 'here is the architecture'"
        intent: "Find posts using the builder-reveal framework we want to emulate"
        good_signals: ["specific technical details", "honest reflections", "consulting positioning"]
        noise_signals: ["content farms", "AI-generated listicles"]

      - query: "site:linkedin.com AI engineer turned consultant freelance"
        intent: "Find people making the same career transition — study their messaging"
        good_signals: ["personal story", "transition narrative", "service positioning"]
        noise_signals: ["recruitment posts", "job boards"]

  # ─── TRENDING TOPICS ────────────────────────────────────────────────────
  # What AI topics are getting engagement right now.
  # Goal: identify timely topics the agent can react to within 24-48 hours.

  trending_topics:
    description: "What AI topics are generating engagement and discussion right now"
    rotation: daily
    queries:
      - query: "AI deployment challenges enterprise this week"
        intent: "Find current pain points that consulting prospects are experiencing"
        good_signals: ["specific challenges", "team frustration", "budget discussions"]
        noise_signals: ["vendor solutions", "product launches"]

      - query: "AI agent framework production issues 2026"
        intent: "Find emerging concerns about AI agents in production — hot topic"
        good_signals: ["real failures", "architecture discussions", "reliability concerns"]
        noise_signals: ["tutorial content", "getting started guides"]

      - query: "AI ROI enterprise disappointing results 2026"
        intent: "Find the 'AI isn't working' narrative — contrarian content opportunity"
        good_signals: ["failed implementations", "cost overruns", "expectation gaps"]
        noise_signals: ["generic AI criticism", "Luddite content"]

      - query: "LinkedIn trending AI enterprise automation this week"
        intent: "Catch the conversation wave — what's everyone talking about right now"
        good_signals: ["high engagement posts", "debate threads", "industry reactions"]
        noise_signals: ["news aggregation", "press releases"]

      - query: "AI consulting demand growing 2026 market"
        intent: "Find market signals that validate the consulting positioning"
        good_signals: ["market reports", "hiring trends", "budget allocation data"]
        noise_signals: ["outdated reports", "predictions without data"]

      - query: "RAG vs fine-tuning enterprise debate 2026"
        intent: "Technical debates that CTOs care about — framework content opportunity"
        good_signals: ["practitioner opinions", "benchmark data", "real comparisons"]
        noise_signals: ["academic papers", "vendor benchmarks"]

      - query: "AI infrastructure costs production scaling 2026"
        intent: "Cost discussions that trigger consulting interest — 'am I overspending?'"
        good_signals: ["real cost breakdowns", "optimization strategies", "vendor comparisons"]
        noise_signals: ["pricing pages", "promotional content"]

  # ─── VIRAL PATTERNS ─────────────────────────────────────────────────────
  # High-performing post structures in the AI/tech/consulting niche.
  # Goal: discover new frameworks beyond what's in viral-frameworks.md.

  viral_patterns:
    description: "High-performing post structures and formats in the niche"
    rotation: weekly
    queries:
      - query: "site:linkedin.com viral AI post builder story 2026"
        intent: "Find posts that broke through — study their structure"
        good_signals: ["high engagement numbers", "share/save indicators", "comment threads"]
        noise_signals: ["clickbait", "engagement pods", "bot activity"]

      - query: "LinkedIn AI consultant post went viral engagement"
        intent: "Find breakout posts from consultants in our space"
        good_signals: ["specific engagement metrics", "unique angles", "strong hooks"]
        noise_signals: ["meta-content about going viral", "LinkedIn tips posts"]

      - query: "best LinkedIn posts AI implementation case study format"
        intent: "Find successful case study formats — our results_proof pillar"
        good_signals: ["structured format", "real client outcomes", "replicable pattern"]
        noise_signals: ["content marketing guides", "how-to-write posts"]

      - query: "LinkedIn carousel AI framework high engagement 2026"
        intent: "Find successful carousel/document posts — highest engagement format"
        good_signals: ["framework structures", "step-by-step content", "visual learning"]
        noise_signals: ["design tool promotions", "template sales"]

      - query: "LinkedIn contrarian take AI enterprise viral"
        intent: "Find hot takes that sparked discussion — our contrarian_takes pillar"
        good_signals: ["comment debate", "strong opinion + evidence", "counter-narrative"]
        noise_signals: ["troll content", "rage bait"]

  # ─── INDUSTRY NEWS ──────────────────────────────────────────────────────
  # Breaking AI news that consulting prospects care about.
  # Goal: find news to react to with commentary (industry_analysis pillar).

  industry_news:
    description: "Breaking AI news relevant to consulting prospects"
    rotation: daily
    queries:
      - query: "enterprise AI news this week 2026"
        intent: "Catch major developments that CTOs and VPs are reading about"
        good_signals: ["funding rounds", "product launches", "regulation changes", "enterprise deals"]
        noise_signals: ["consumer AI news", "crypto/blockchain crossover"]

      - query: "AI regulation enterprise impact compliance 2026"
        intent: "Regulatory news triggers consulting demand — 'we need help with this'"
        good_signals: ["new regulations", "compliance requirements", "industry reactions"]
        noise_signals: ["political commentary", "general AI ethics debates"]

      - query: "AI vendor landscape enterprise changes acquisitions 2026"
        intent: "Vendor ecosystem changes affect buying decisions — consulting opportunity"
        good_signals: ["acquisitions", "pivots", "pricing changes", "new entrants"]
        noise_signals: ["startup hype", "pre-revenue announcements"]

      - query: "AI adoption enterprise survey statistics 2026"
        intent: "Find data points to use in content — data_confession framework"
        good_signals: ["survey results", "adoption rates", "ROI data", "failure rates"]
        noise_signals: ["vendor-sponsored surveys", "small sample sizes"]

      - query: "AI job market engineering hiring trends enterprise 2026"
        intent: "Employment trends affect prospect decisions — 'should we hire or contract?'"
        good_signals: ["salary data", "hiring difficulty", "skill gaps", "outsourcing trends"]
        noise_signals: ["job board promotions", "bootcamp marketing"]

      - query: "OpenAI Anthropic Google AI enterprise features announcements"
        intent: "Major model/platform updates that change the conversation"
        good_signals: ["capability announcements", "pricing changes", "enterprise features"]
        noise_signals: ["consumer features", "social media reactions only"]
```

---

## Query Design Principles

### What Makes a Good Niche Research Query

1. **Specificity over breadth** — "AI consulting thought leadership 2026" > "AI news"
2. **Intent signals** — Include words prospects would search ("CTO", "enterprise", "production")
3. **Temporal markers** — Include year to get fresh results ("2026")
4. **Format signals** — "case study", "framework", "architecture" find structured content
5. **Platform signals** — `site:linkedin.com` for LinkedIn-specific research
6. **Quotation marks** — "I built" finds exact builder-reveal patterns

### What to Avoid

- Overly broad queries that return noise ("AI trends")
- Vendor-specific queries that return marketing content ("OpenAI best practices")
- Academic queries that return papers instead of practitioner content
- Queries that find our own content (we already know what we posted)

### When to Add New Queries

Add queries when the reason stage suggests topics we're not monitoring:
- New technology trend the agent notices in results (e.g., "AI agents in production")
- Prospect pain point that keeps appearing (e.g., "AI team hiring vs. contracting")
- Competitor we discover through other research
- Industry event generating conversation (e.g., major AI conference)

### When to Retire Queries

Retire queries that consistently:
- Return the same results across multiple cycles
- Return only vendor/marketing content
- Return no LinkedIn practitioner posts
- Are no longer timely (e.g., specific event-based queries after the event)

---

## Query Composition Guide

For the agent to dynamically compose new queries when it discovers emerging topics:

```yaml
composition_templates:
  competitor_hunt:
    template: 'site:linkedin.com "{person_type}" "{topic}" {year}'
    example: 'site:linkedin.com "AI consultant" "deployment strategy" 2026'

  trending_catch:
    template: '"{topic}" enterprise {outcome_word} {year}'
    example: '"AI agents" enterprise challenges 2026'

  viral_hunt:
    template: 'site:linkedin.com {topic} viral OR "high engagement" OR "went viral"'
    example: 'site:linkedin.com AI automation viral OR "high engagement"'

  news_catch:
    template: '{topic} enterprise news this week {year}'
    example: 'AI regulation enterprise news this week 2026'

  builder_find:
    template: 'site:linkedin.com "I built" OR "I automated" {topic}'
    example: 'site:linkedin.com "I built" OR "I automated" AI pipeline'
```

---

## Cross-References

- **Spec:** `specs/010-marketing-agent.md` SPEC-006 (Niche Research Step)
- **Extraction model:** `NicheInsight` in `src/holus/agents/marketing/models.py` (to be built)
- **Known frameworks:** `viral-frameworks.md` (deduplicate against this)
- **Content pillars:** `content-marketing-strategy.md` and `growth-engine-vision.md`
- **Brand positioning:** `config/brand.yaml` (queries reflect target audience language)
- **Rotation state:** `data/.niche-research-state.json` (runtime, gitignored)

---

## What Changed vs Last Version

New file. 4 categories, 24 curated queries with intent descriptions and signal
classification (good_signals / noise_signals). Includes query composition templates
for dynamic query generation and design principles for query maintenance.
