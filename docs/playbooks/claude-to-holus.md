# Claude Code → Holus Transition Roadmap

**What this is:** A running tracker of every workflow we test manually with Claude Code that will eventually run autonomously inside Holus. Each row is a capability. We test it manually first, verify it works, then migrate it to a Holus agent.

**The pattern:**
```
1. Do it manually with Claude Code (me + Claude = 1 brain)
2. It works reliably for 2–4 weeks
3. Write the Holus agent spec
4. Agent takes it over
5. I review outputs, don't produce them
```

---

## Content Distribution Pipeline

The core workflow: thought → content → distribution across 8 accounts.

### Progression

| Phase | What | Input | Who Does It | Status |
|---|---|---|---|---|
| 1 | Text distribution | Typed thought | Claude Code + social-poster skill | **ACTIVE** |
| 2 | Text + image | Thought + local image | Claude Code + social-poster skill | Pending |
| 3 | Processed video | Raw video file | Genpeli → Claude Code distributes | Pending |
| 4 | Recorded video | Raw recording → Telegram | Gemini transcribes → Genpeli → Claude distributes | Pending |
| 5 | Autonomous | Any input | Holus content-orchestrator agent | Target |

### What "it works" means before migrating to Holus
- [ ] 30 posts through the pipeline with zero manual intervention mid-flow
- [ ] All 5 active platforms return 200 (IG, FB, Threads, LI, X)
- [ ] Tone is consistently right per platform without editing
- [ ] No token expiry surprises during the 30 days
- [ ] Scheduling works (at least 5 scheduled posts delivered on time)

---

## Platform Status (Live Testing Log)

Track each platform canary post here. Update when tested.

| Platform | Account | Last tested | Result | Notes |
|---|---|---|---|---|
| X/Twitter | @camilomartinezc | 2026-03-06 | ✓ Pass | Pay Per Use — $0.01/post |
| Instagram | @camiloexperience | 2026-03-06 | ✓ Pass | Story posted (PNG screenshot, landscape). Post ID: 17877020097511442 |
| Instagram | @camilojourney | — | Untested | Needs canary post |
| Facebook | Camilo Experience | — | Untested | Same token as IG |
| Facebook | Camilo Journey | — | Untested | Same token as IG |
| Threads | @camiloexperience | — | Untested | Needs canary post |
| Threads | @camilojourney | — | Untested | Needs canary post |
| LinkedIn | Camilo Martinez | — | Untested | Legacy API — needs migration first |

---

## Workflow Checklist (Manual → Holus)

### Workflow 1: Thought → Text Post
**Manual version:** `/social-poster` skill. Give Claude a thought, get preview, confirm, post.

- [ ] Test: EN thought → Facebook + Threads + X + LinkedIn (4 platforms)
- [ ] Test: ES thought → Facebook + Threads (2 platforms)
- [ ] Test: Both EN+ES → all accounts
- [ ] Works 10× in a row without issues
- [ ] **Ready to spec Holus agent?** No — need 10 successful manual runs first

**Holus agent:** `content-orchestrator` — receives thought via Holus event bus, calls social-media-automatization API, logs result.

---

### Workflow 2: Thought → Image Post
**Manual version:** User provides image path → Claude uploads to R2 → posts with captions.

- [x] Upload flow working (R2 URL returned correctly) — tested 2026-03-06
- [x] Instagram receives image (PNG accepted for Stories, JPEG for feed) — tested 2026-03-06
- [ ] Threads receives image (JPEG only, PNG = text fallback)
- [ ] Facebook receives image
- [ ] X receives image
- [ ] LinkedIn receives image
- [ ] **Ready to spec Holus agent?** No — test manually first

---

### Workflow 3: Video → Social Posts
**Manual version:** User sends video → Genpeli processes → Claude distributes.

- [ ] Genpeli pipeline tested end-to-end (cuts, captions, normalize)
- [ ] IG Reels format confirmed (9:16 vertical, ≤60s for Reels)
- [ ] FB video upload working
- [ ] X video upload working
- [ ] LinkedIn video upload working
- [ ] **Ready to spec Holus agent?** No — Genpeli must be stable first

---

### Workflow 4: Raw Recording → Full Distribution
**Manual version:** Record video → send to Claude → Gemini transcribes → Genpeli processes → Claude distributes.

- [ ] Workflow 3 complete and stable
- [ ] Gemini transcription tested on a real recording
- [ ] Gemini edit suggestions are usable without heavy correction
- [ ] End-to-end time: recording → live post in < 30 min
- [ ] **Ready to spec Holus agent?** No — requires Workflows 1–3 stable first

---

## What Holus Needs to Own This

These are the Holus components that don't exist yet but will be needed:

| Component | Purpose | Depends On |
|---|---|---|
| `content-orchestrator` agent | Receives thought/content, calls social-media API, logs results | social-media-automatization deployed + stable |
| `genpeli-bridge` | Triggers Genpeli pipeline for videos, gets back processed URL | Genpeli pipeline stable |
| `tone-adapter` | Per-platform content adaptation (currently Claude Code does this) | 30+ successful manual adaptations to learn from |
| `schedule-agent` | Determines optimal posting time per platform, fires schedule calls | Platform analytics (Stage 3) |
| Telegram intake | Receives raw thoughts/recordings from Camilo via Telegram | Telegram bot token |
| Event bus routing | Routes `content.received` event to the right agent | Redis pub/sub (already in Holus) |

---

## Decision: When to Move a Workflow to Holus

A workflow is ready to migrate when:
1. It has run successfully **10+ times manually** without needing correction
2. The **API it depends on is deployed** (not just localhost)
3. The **content quality is right** — tone feels like Camilo without editing
4. There's a **clear rollback** if the agent fails (the manual workflow still works)

Never migrate a workflow to Holus "to fix it." Fix it manually first, then automate the fixed version.

---

## Parallel Track: Building Holus While Using Claude Code

The strategy: Claude Code = Holus in slow motion.

Every time I work with Claude Code to distribute content:
- I'm **testing the workflow** that Holus will eventually run
- I'm **discovering edge cases** that the Holus agent spec needs to handle
- I'm **building the account map, tone guide, and routing logic** that becomes Holus config
- I'm **generating training examples** (thought → adapted posts per platform) that inform agent prompts

When Holus eventually runs `content-orchestrator`, it uses:
- The same API (`social-media-automatization`)
- The same routing table (documented in `social-poster/skill.md`)
- The same tone guidelines (documented in `social-poster/skill.md`)
- The same connection IDs and account map

The only difference: Holus does it without me in the loop.

---

## Milestone: Holus Handles Content Autonomously

**Target:** Camilo sends a Telegram message → Holus distributes to all accounts → Camilo reviews the posts in his feed.

**Prerequisite checklist:**
- [ ] social-media-automatization deployed on Railway (live URL)
- [ ] All 7 platform connections tested and returning 200
- [ ] LinkedIn API migrated to /rest/posts
- [ ] Bluesky connected (optional but good)
- [ ] YouTube connected (optional but good)
- [ ] 30-day dog-food complete (240+ posts through the system)
- [ ] Meta App Review approved (for multi-tenant, not needed for own accounts)
- [ ] Holus content-orchestrator agent spec written and reviewed
- [ ] Holus Telegram intake working
- [ ] First autonomous test: send thought via Telegram → verify post lands without manual step

**Estimated timeline:** 8–12 weeks from 2026-03-06 if we work the manual phase consistently.

---

## Discovered Features

Features and routing variables we discover by using the skill. Every time we
post and something new comes up — a platform fit decision, an enhancement
preference, a content type edge case — it gets logged here. These become
Holus agent configuration when the time comes.

### Content Enhancement Prompts

The per-platform writer prompts. Start with base authenticity for all, then
refine each as Camilo gives feedback.

| Platform | Prompt version | Status | Last updated | Notes |
|---|---|---|---|---|
| X/Twitter | base authenticity | not built | — | Needs: compression to 280, hook-first |
| Threads EN | base authenticity | not built | — | Needs: conversational, 500 char max |
| Threads ES | base authenticity | not built | — | Needs: warmer, journey tone |
| Facebook EN | base authenticity | not built | — | Needs: shareable framing |
| Facebook ES | base authenticity | not built | — | Needs: community feel |
| Instagram EN | base authenticity | not built | — | Needs: visual-first caption, hashtags |
| Instagram ES | base authenticity | not built | — | Needs: journal entry vibe |
| LinkedIn | base authenticity | not built | — | Needs: professional lens, longer |

> When a prompt is refined: update version to `v1`, status to `active`, add
> the date and what changed. The actual prompt text lives in
> `/Users/mini/.claude/skills/social-poster/skill.md` under "Per-Platform Writer Prompts".

### Routing Variables Discovered

Variables that affect where content goes. We discover these by posting and
seeing what works vs what doesn't fit.

| Variable | Values | Discovered | Affects routing? |
|---|---|---|---|
| content_tone | serious / casual / personal / technical | — | Yes — serious may skip IG, technical → LinkedIn |
| has_media | yes / no | built-in | Yes — no media = skip Instagram |
| language | EN / ES | built-in | Yes — ES skips X and LinkedIn |
| content_length | short / medium / long | — | Yes — long content bad for X |
| post_type | feed / story / reel | 2026-03-06 | Yes — determines which IG API call (publish_image vs post_story vs publish_video) |
| enhancement_mode | raw / minimal / authentic / structured / full | built-in | No — applies to all platforms |

> Add rows here every time we discover a new variable. Example: if we find
> that "motivational" content performs better on IG than LinkedIn, add
> `content_mood: motivational/analytical/reflective` as a new variable.

### Feature Requests (discovered during use)

Things Camilo asks for while posting that aren't built yet.

| Feature | Discovered | Status | Notes |
|---|---|---|---|
| Instagram worker dispatch | 2026-03-06 | FIXED | IG publisher existed but was never wired into worker — added `if platform == "instagram":` block with feed/reels/stories dispatch |
| Story format routing | 2026-03-06 | FIXED | `format: "story"` existed in schema but worker never checked it — now routes to `post_story()` |
| Account targeting via account_id | 2026-03-06 | discovered | `platforms: ["instagram"]` picks default account. Use `account_id` field to target specific account (e.g., `17841452746940353` for @camiloexperience) |

> Add rows here whenever Camilo asks for something new during a posting session.
> Example: "Can you also suggest the best time to post this?" → add as a feature.

---

## Session Log

Every posting session gets a row. This is how we track what's been tested.

| Date | Platforms posted | Enhancement | Prompts used | Corrections | Notes |
|---|---|---|---|---|---|
| 2026-03-06 | IG Story (@camiloexperience) | raw (screenshot) | none (image post) | Wrong account routed first (journey→experience), needed `account_id` field | First IG post. Discovered worker dispatch was missing. Fixed live. PNG landscape accepted as Story. |

> After each posting session, add a row. "Corrections" = what Camilo changed
> after seeing the preview. These corrections are gold — they teach us the
> routing variables and prompt refinements.

---

> Last updated: 2026-03-06
> Owner: Camilo Martinez
> Status: Phase 1 active — testing manual content distribution

---

## Session Log — 2026-03-09

| Date | Platforms posted | Enhancement | Prompts used | Notes |
|------|-----------------|-------------|--------------|-------|
| 2026-03-09 | IG EN ✓, IG ES ✓ 🆕, FB EN ✓ 🆕, FB ES ✓ 🆕, X ✓, LinkedIn ✓ 🆕, Threads EN ✓ 🆕, Threads ES ✓ 🆕, MCM Adapt IG+FB ✓, Camilo Nation IG+FB ✓ | authentic | how_i_live specialist + platform writers v1.0 | First video post across all accounts. Threads video API not implemented → text fallback. Feature being built. |

### Platform Status Updates
- Instagram @camilojourney: ✓ first test passed
- Facebook Experience: ✓ first test passed
- Facebook Journey: ✓ first test passed
- Threads @camiloexperience: ✓ first test passed (text)
- Threads @camilojourney: ✓ first test passed (text)
- LinkedIn: ✓ first test passed (video)

### Feature Requests Discovered
- Threads video publishing not implemented (falls back to text) → `feat/threads-video-support` branch building now
