# Spec 037: Research Radar — AI Content Feed into the Thought Studio

**Status:** ready
**Phase:** Phase 1 (on-demand) → Phase 2 (scheduled)
**Author:** Juan
**Created:** 2026-06-25
**Updated:** 2026-06-25

## Background

The thought studio only accepts thoughts that a human supplies by hand. Intake is
`POST /api/v1/content/from-thought` → `ThoughtContentPipeline.create_content_set`
(`src/holus/agents/marketing/thought_pipeline.py`), which takes a thought as
`text` or `url` and fans out per-platform pending-review records into
`data/content-queue/*.yaml`.

There is no system that watches the AI landscape and surfaces what is worth
reading or worth posting about. The registry already declares research
specialists (`niche-researcher` active; `competitive-intel`, `seo-strategist`,
`audience-analyst` planned) but none of them are wired to a real source feed.

The Research Radar adds an automated **thought-source** that sits upstream of
Ingest. It watches AI sources, scores each item against the product portfolio and
the operator's interests, and produces two outputs: a **reading digest** the
operator studies, and **thought candidates** that — on explicit approval — enter
the existing `/from-thought` pipeline unchanged.

This is a feeder in front of the studio, not a second pipeline. The radar never
publishes and never bypasses human review.

## Problem

1. No mechanism brings new AI papers, launches, and discussion into Holus.
2. The operator has no curated "what to read and understand this week" surface.
3. Content ideas are bottlenecked on the operator manually noticing things.

## Goals

- Pull items from arXiv (cs.AI, cs.CL, cs.LG), Hacker News, and a configurable
  list of newsletter/blog RSS/Atom feeds.
- Deduplicate against previously seen items so re-runs cost nothing extra.
- Score each new item for portfolio relevance, novelty, and read priority via a
  new `research-curator` agent registered in `agentic/agents/AGENTS.yaml`.
- Emit a human-readable markdown reading digest at
  `data/research/digest-YYYY-MM-DD.md`.
- Emit thought-candidate YAML at `data/research/candidates/*.yaml`.
- Expose `/api/v1/research/*` routes to run the radar, read the digest, and
  list/approve/reject candidates. Approving a candidate calls the existing
  from-thought intake — no pipeline logic is duplicated.
- Run on demand now; be structured so a launchd schedule can trigger it later
  (Phase 2).
- Provide a hook so well-performing research-sourced posts can later tune the
  curator's relevance weighting (full tuning is a later phase).

## Non-Goals

- No auto-publishing or auto-approval. Candidates are pending until a human acts.
- No new analytics storage — performance still lives in Holus Social API.
- No full reinforcement loop now; only the trajectory hook is specified.
- No Twitter/X or paywalled-source scraping in this spec.
- No change to `ThoughtContentPipeline` behavior or content-queue schema.

## Solution

```
SOURCES                FETCH+DEDUPE            SCORE                  OUTPUTS
arXiv (API)   ─┐
Hacker News ──┼─► SourceAdapter.fetch ─► seen-store skip ─► research-curator ─┬─► reading digest (read)
RSS feeds   ──┘     (RawResearchItem)      (stable id)      (ResearchScore)   └─► thought candidates
                                                                                      │ approve
                                                                                      ▼
                                                                       existing /from-thought intake
```

### Module layout (`src/holus/research/`)

| File | Responsibility |
|------|----------------|
| `models.py` | Pydantic boundary models (below) |
| `sources/base.py` | `SourceAdapter` protocol + `fetch(window) -> list[RawResearchItem]` |
| `sources/arxiv.py` | arXiv export API adapter (cs.AI/CL/LG) |
| `sources/hackernews.py` | HN Algolia API adapter |
| `sources/rss.py` | RSS/Atom adapter over the configured feed list |
| `seen_store.py` | Append-only seen ledger keyed by stable item id |
| `curator.py` | `ResearchCurator` wrapping the scoring agent; accepts an injectable scorer for tests |
| `radar.py` | `run_radar()` orchestrator → `RadarRunReport` |
| `digest.py` | Renders the markdown reading digest |
| `candidates.py` | Candidate store + `approve()` bridge to `ThoughtContentPipeline` |

API route: `src/holus/api/routes/research.py` (registered in `app.py`).
Config: `config/research.yaml` (feeds, thresholds, windows, caps).
Interests: `config/research-interests.md` (operator-editable free text fed to the curator).

### Pydantic boundary models (`src/holus/research/models.py`)

```python
class RawResearchItem(BaseModel):
    source: Literal["arxiv", "hackernews", "rss"]
    source_id: str            # adapter-native id (arxiv id, HN objectID, rss guid)
    item_id: str              # stable global id = sha256(source + ":" + source_id)[:16]
    title: str
    url: HttpUrl
    summary: str              # capped, HTML-stripped
    author: str | None = None
    published_at: datetime
    raw_meta: dict[str, Any] = {}

class ResearchScore(BaseModel):
    item_id: str
    relevance: float          # 0..1 to the product portfolio
    novelty: float            # 0..1
    should_read: float        # 0..1 operator read-priority
    matched_products: list[str]   # subset of {pilaster, genpeli, invoz}; [] = none
    topics: list[str]
    why_it_matters: str       # 2-3 lines, shown in digest
    key_idea: str
    recommended_action: Literal["read_only", "candidate", "skip"]

class ResearchCandidate(BaseModel):
    candidate_id: str         # == item_id
    item: RawResearchItem
    score: ResearchScore
    status: Literal["pending", "approved", "rejected", "failed"] = "pending"
    created_at: datetime
    approved_group_id: str | None = None   # set when approved into from-thought

class RadarSourceResult(BaseModel):
    source: str
    status: Literal["ok", "failed"]
    fetched: int
    new_items: int
    error: str | None = None

class RadarRunReport(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime
    sources: list[RadarSourceResult]
    scored: int
    digest_path: str | None
    candidates_created: int
```

### Scoring → output routing

- `should_read >= digest_threshold` (default `0.5`) → item appears in the reading digest.
- `relevance >= candidate_threshold` (default `0.65`) **and**
  `recommended_action == "candidate"` → a `ResearchCandidate` YAML is written.
- `recommended_action == "skip"` → recorded as seen, no output.
- Thresholds live in `config/research.yaml` and are read at run time.

### Candidate approval (reuse, do not duplicate)

`candidates.approve(candidate_id)` loads the candidate and calls the **existing**
`ThoughtContentPipeline.create_content_set`:
- if the item URL is reachable → `source_type="url", source_url=item.url`;
- the curator's `key_idea` + `why_it_matters` is also stored so approval can fall
  back to `source_type="text"` when the URL fetch fails.
On success it sets `status="approved"` and records `approved_group_id`. No
content-queue writing logic is reimplemented in the research module.

### API routes (`/api/v1/research`)

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/run` | Run the radar; returns `RadarRunReport`. |
| `GET`  | `/digest` | Latest digest (optional `?date=YYYY-MM-DD`) as markdown/JSON. |
| `GET`  | `/candidates` | List candidates (filter `?status=`). |
| `POST` | `/candidates/{id}/approve` | Approve → calls from-thought intake; returns created content group. |
| `POST` | `/candidates/{id}/reject` | Mark rejected. |

### Run entrypoint

`run_radar()` is callable from `POST /api/v1/research/run` and from a thin
`scripts/research_radar_cycle.py` CLI so a launchd job (Phase 2) can trigger the
same code path. Both return/serialize a `RadarRunReport`.

### Learning hook

When a content piece sourced from a candidate is published and later shows strong
performance, `radar.py` exposes `record_outcome(item_id, signal)` that appends to
the existing `.self-improvement/memory/trajectory.jsonl`. Consuming that signal to
re-weight relevance is explicitly deferred to a later spec; this spec only
guarantees the signal is written with the originating `item_id`.

### Registry + config changes

- Add `research-curator` to `agentic/agents/AGENTS.yaml` (type: specialist,
  category: research, model_tier: operational, evaluated_by: seo-judge) with a
  prompt at `agentic/agents/specialists/research/research-curator.md`.
- Add `config/research.yaml` (feeds list seeded with Import AI, Latent Space, and
  2-3 lab blogs; arXiv categories; HN query; per-source caps; window days;
  digest/candidate thresholds).
- Add `config/research-interests.md` seeded from the operator's stated interests.
- Update `specs/README.md` index with row 037.

## Acceptance Criteria

- [ ] **AC1 — arXiv adapter:** Given a stubbed arXiv API response containing 3
  entries, when `ArxivAdapter.fetch(window)` runs, then it returns 3
  `RawResearchItem` objects with `source == "arxiv"`, populated `title`, `url`,
  `published_at`, and a deterministic `item_id`.
- [ ] **AC2 — HN adapter:** Given a stubbed HN Algolia response, when
  `HackerNewsAdapter.fetch(window)` runs, then it returns `RawResearchItem`
  objects with `source == "hackernews"` and `source_id` equal to the HN
  `objectID`.
- [ ] **AC3 — RSS adapter:** Given a stubbed Atom feed with 2 entries, when
  `RssAdapter.fetch(window)` runs over a configured feed, then it returns 2 items;
  entries missing a published date use the fetch time as `published_at`.
- [ ] **AC4 — Stable id + dedupe:** Given the same source item fetched twice
  across two runs, when the second run executes, then the item is recognized via
  the seen-store and is **not** re-scored and **not** re-emitted as a candidate.
- [ ] **AC5 — Cross-source dedupe:** Given the same paper appears in both arXiv
  and HN with the same canonical URL, when a run scores them, then exactly one
  candidate is produced.
- [ ] **AC6 — Partial source failure:** Given one source adapter raises an
  exception, when `run_radar()` executes, then the run completes, the
  `RadarRunReport` marks that source `status == "failed"` with an `error`, and
  items from healthy sources are still scored.
- [ ] **AC7 — Scoring contract:** When the curator scores an item, then it returns
  a `ResearchScore` with `relevance`, `novelty`, `should_read` each in `[0, 1]`,
  `recommended_action in {read_only, candidate, skip}`, and non-empty
  `why_it_matters` and `key_idea`.
- [ ] **AC8 — Digest generation:** Given items scored above the digest threshold,
  when a run completes, then `data/research/digest-YYYY-MM-DD.md` exists and each
  listed item shows title, why-it-matters, key idea, and a clickable link.
- [ ] **AC9 — Candidate routing:** Given an item with `relevance >=
  candidate_threshold` and `recommended_action == "candidate"`, when a run
  completes, then a `ResearchCandidate` YAML exists in `data/research/candidates/`
  with `status == "pending"`.
- [ ] **AC10 — Approval reuses from-thought:** Given a pending candidate, when
  `POST /api/v1/research/candidates/{id}/approve` is called, then
  `ThoughtContentPipeline.create_content_set` is invoked (asserted via spy), the
  candidate becomes `approved` with a recorded `approved_group_id`, and new
  pending-review records appear in `data/content-queue/`.
- [ ] **AC11 — No auto-publish:** When any radar run or approval executes, then no
  call to `HolusSocialAPIClient.publish` or `.schedule_post` occurs.
- [ ] **AC12 — API run report:** When `POST /api/v1/research/run` is called, then
  it returns HTTP 200 with a `RadarRunReport` body whose `sources` length equals
  the number of configured source types.
- [ ] **AC13 — Registry + config present:** `research-curator` exists in
  `AGENTS.yaml` with a prompt file, and `config/research.yaml` plus
  `config/research-interests.md` exist and load without error.
- [ ] **AC14 — Idempotent same-day run:** Given the radar runs twice on the same
  date with no new source items, when the second run completes, then no duplicate
  candidates are created and the digest file content is unchanged.

## Edge Cases

| Scenario | Expected behavior | User-facing result | Recovery |
|----------|-------------------|--------------------|----------|
| All sources fail/unreachable | Run completes; each source marked `failed`; empty digest noting "no new items"; zero candidates | `RadarRunReport` with all sources `failed`, HTTP 200 | Re-run later; nothing is lost |
| Item already seen in prior run | Skipped before scoring (no LLM cost) | Item absent from new digest/candidates | n/a — intended |
| Same item from two sources | Deduped to one canonical item (prefer arXiv URL) | Single digest entry, single candidate | n/a |
| arXiv returns malformed/empty Atom | Adapter logs warning, yields `[]`, run continues | Source marked `failed` or `fetched: 0` | Other sources still processed |
| RSS feed in config is dead/4xx | That feed isolated; other feeds still fetched | `rss` source still `ok` if any feed succeeds | Operator fixes feed URL in config |
| Approved candidate URL now dead | from-thought URL fetch raises (existing 502 path); approval falls back to stored `text` summary; if that also fails, candidate set to `failed` | Clear error; candidate retained, not deleted | Operator retries or edits |
| Candidate approved twice | Idempotent: second approval is a no-op returning the existing `approved_group_id` | Same content group returned | n/a |
| Fetched URL resolves to private IP / non-http scheme | Rejected before fetch (SSRF guard); item dropped with logged reason | Item not fetched/scored | Operator removes the feed |
| Curator returns out-of-range score | Validation rejects; item logged and skipped, run continues | Item absent from outputs | Fix curator prompt/model |

## Security & Safety

- **SSRF:** Only operator-configured feeds and official keyless APIs are fetched.
  Validate scheme is `http`/`https` and block private/loopback IP ranges before
  any outbound article fetch.
- **Sanitization:** Reuse the existing HTML-strip + length cap behavior used by
  `_extract_from_url` when pulling article bodies.
- **No silent publishing:** The radar produces only pending candidates and a
  digest; publishing remains an explicit, separately gated human action.
- **Secrets:** All three source types are keyless; if a future feed needs auth,
  it is read from `.env` only, never committed.
- **ToS/politeness:** Use the arXiv export API with request spacing, HN Algolia
  with paging, a descriptive `User-Agent`, and per-source item caps from config.

## Testability Notes

- The curator takes an **injectable scorer**; unit tests pass a stub returning
  fixed `ResearchScore` objects so no LLM call is made.
- Source adapters take an injectable HTTP client; tests stub API/RSS payloads.
- The approval bridge is tested with a spy/fake `ThoughtContentPipeline` to assert
  reuse (AC10) without writing real network calls.
