# SPEC-032: Content Humanization Gate

**Status:** Not Started
**Priority:** P0 — LinkedIn penalizes AI-generated content 47% in reach
**Dependencies:** SPEC-031 (LinkedIn Content Pipeline)
**Research:** `docs/research/domain/linkedin-posting-frequency.md`
**Spec CID:** holus-SPECS-20260319-e5f3f48f
**Specialist input:** arch (B), perf (B), sec (C+B) — see `.pipeline-state/` artifacts

---

## Problem

LinkedIn's algorithm detects and penalizes AI-generated content with a **47% organic reach reduction** (Algorithm Insights Report 2025, 1.8M posts analyzed). The current pipeline (SPEC-031) generates content via Claude and schedules it with an `approval_required=true` gate — but approval only means "yes, post this." It does not include a step where the human edits the content to sound natural.

Without humanization, every Holus-generated post starts at half reach regardless of quality.

## Solution

Add a **humanization step** between the quality gate (JudgeAgent) and scheduling. Content that passes the quality gate enters a `pending_humanization` status. The human edits it in the Observatory UI to remove AI tells (formulaic transitions, passive voice, overly structured formatting). Only after humanization can content be approved and scheduled.

## Status Machine

```
generated → judged → pending_humanization → humanized → approved → published
                ↓                                          ↓
             rejected                                   expired (72h)
```

**New states:**
- `pending_humanization` — passed quality gate, waiting for human edit
- `humanized` — human has edited the content, ready for approval

**Transition rules:**
- `judged → pending_humanization`: automatic when JudgeAgent score >= threshold
- `pending_humanization → humanized`: requires human edit via Observatory UI
- `humanized → approved`: human clicks approve (or auto-approve if edit distance > 10%)
- `pending_humanization → expired`: 72 hours without humanization → content expires

## Decisions (from specialist deliberation)

### DECISION 1: Humanization Placement
**Options:** A) Before quality gate B) After quality gate, before scheduling C) Replace quality gate
**Decision:** **B — After quality gate, before scheduling**
**Rationale (arch):** The judge evaluates AI-generated structural quality (tone, factual accuracy, brand safety). The human removes AI tells from content that already passes quality checks. Judging after humanization would waste judge calls on content the human might rewrite significantly.

### DECISION 2: Queue Strategy
**Options:** A) In-memory queue B) YAML/JSON file queue C) SQLite queue
**Decision:** **B — File-based queue (existing `data/content-queue/*.json`)**
**Rationale (perf):** At 3 posts/week throughput, no database is justified. The existing file-based queue handles this volume. Add a `status` field to the existing queue JSON format.

### DECISION 3: Approval Channel
**Options:** A) CLI only B) Telegram bot C) Observatory web UI D) All three
**Decision:** **C primary (Observatory UI for editing) + B for notification (Telegram ping when content is ready)**
**Rationale (sec):** Humanization requires a text editor — Telegram is too limited. Observatory already has ContentDetailPanel. Add an edit mode. Telegram sends a notification: "New content ready for humanization" with a link to Observatory.

## Implementation

### 1. Queue format update (`data/content-queue/*.json`)

Add `status` field to existing `QueuedContent` model:

```python
class QueuedContent(BaseModel):
    # ... existing fields ...
    status: Literal["pending_humanization", "humanized", "approved", "published", "expired", "rejected"]
    humanized_text: str | None = None  # edited version
    humanized_at: datetime | None = None
    edit_distance: float | None = None  # Levenshtein ratio vs original
```

### 2. Observatory ContentDetailPanel edit mode

Add to existing `ContentDetailPanel.tsx`:
- "Edit" button (visible when status = `pending_humanization`)
- Textarea with original text pre-filled
- "Save Humanized" button → PATCH `/api/v1/content/{id}/humanize`
- Show diff between original and humanized text
- "Approve" button (visible when status = `humanized`)

### 3. API endpoints

```
PATCH /api/v1/content/{id}/humanize
  Body: { "humanized_text": "..." }
  Validation: edit_distance(original, humanized) < 0.40 (Levenshtein ratio — sec requirement)
  Returns: updated QueuedContent with status="humanized"

POST /api/v1/content/{id}/approve
  Validation: status must be "humanized" (rejects pending_humanization or other states)
  Returns: updated QueuedContent with status="approved"
```

### 4. Expiry cron

Existing `marketing-plist` (30min interval) checks queue for items where:
- `status == "pending_humanization"` AND `created_at < now - 72h`
- Set status to `expired`

### 5. Telegram notification

When content enters `pending_humanization`:
```python
send_telegram(f"New content ready for humanization: {title}\n{observatory_url}/content/{id}")
```
No content body in Telegram message (sec requirement).

### 6. Disable auto-publish for un-humanized content

Current `auto_publish.py` (score >= 0.8 auto-approves) must check:
```python
if piece.status != "humanized":
    return  # never auto-publish un-humanized content
```

## Acceptance Criteria

### AC-032-001: Content enters pending_humanization after quality gate
**Priority:** P0
**Given** a ContentDecision that passes JudgeAgent with score >= threshold
**When** the ACT step queues it
**Then** the queue entry has `status: "pending_humanization"`

### AC-032-002: Observatory shows edit mode for pending content
**Priority:** P0
**Given** content with status `pending_humanization`
**When** user opens ContentDetailPanel
**Then** an "Edit" button is visible and clicking it shows a textarea with the original text

### AC-032-003: Humanized content can be approved
**Priority:** P0
**Given** content with status `humanized` (human has edited it)
**When** user clicks "Approve"
**Then** status transitions to `approved` and content is scheduled for posting

### AC-032-004: Un-humanized content cannot be approved
**Priority:** P0
**Given** content with status `pending_humanization`
**When** approve endpoint is called
**Then** request is rejected with 422 status

### AC-032-005: Edit distance bounded
**Priority:** P1
**Given** original text of 500 characters
**When** user submits humanized text with >40% edit distance (Levenshtein)
**Then** request is rejected with 422 "Edit distance exceeds 40% — this is a rewrite, not a humanization"

### AC-032-006: Content expires after 72 hours
**Priority:** P1
**Given** content in `pending_humanization` for 72+ hours
**When** the marketing cron runs
**Then** status transitions to `expired`

### AC-032-007: Telegram notification sent
**Priority:** P2
**Given** content enters `pending_humanization`
**When** the transition completes
**Then** a Telegram message is sent with the content title and Observatory URL (no content body)

## Out of Scope

- Batch humanization (edit multiple pieces at once) — not needed at 3/week
- AI-assisted humanization suggestions — future iteration
- A/B testing humanized vs raw — need baseline data first
- Mobile Observatory UI — desktop-first for editing

## Security

- Approve endpoint rejects any piece not in `humanized` status (state machine enforcement)
- Edit distance bounded at 40% Levenshtein to prevent content injection bypassing the judge
- Telegram messages contain no content body (only title + URL)
- Observatory edit mode requires authenticated session
