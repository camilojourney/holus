---
name: post
version: 2.0.0
description: "Run Holus raw-thought to LinkedIn review workflow with preview links, trace audit, quality gates, and explicit publish approval."
compatibility: [python>=3.11]
prompt_version: 2
agentic_eval: default-7-pillars
---

# Post Skill - Thought To Review, Taste, Targeted Rerun, Then Publish Gate

## Memory Contract

| Memory type | Reads | Writes | Forbidden |
|---|---|---|---|
| Working | User raw thought, Holus repo context, `agentic/memory.yaml`, current run state | Workflow state, preview metadata, trace artifacts named by this skill | Secrets, credentials, silent publish/schedule state |
| Episodic | Prior content traces, generated artifacts, taste/review results | Trace audit, quality verdicts, targeted rerun notes | Hidden state outside Holus or Fleet telemetry |
| Semantic | Holus docs, brand/content rules, approved examples, repo memory | Durable content lessons only when explicitly documented | Copying Holus product truth back into Fleet |
| Procedural | This `SKILL.md`, local `references/`, local `scripts/`, Fleet dispatcher contracts | Versioned skill/eval updates only through skill-creator/doctor workflows | Publishing without explicit human approval |

**Role:** Turn one raw thought into a reviewable LinkedIn content set through
Holus, show the user phone-openable preview links, audit the trace, run the
artifact through taste/review gates, and rerun only the failed workflow layer
when the output fails.

`/post` is the front door for Juan's thought-to-delivery loop. It does **not**
mean "publish immediately." Publishing remains a separate explicit approval.

## Default Contract

When the user gives raw text, treat it as a thought, not final copy.

Default platform: `linkedin`.

Default LinkedIn outputs:

- `linkedin_text`
- `linkedin_carousel`
- `linkedin_image` when the route supports image assets

If the user asks for only PDF, only image, or only text, narrow the requested
channels. If the user says `all`, use all Thought Studio channels.

Never publish, schedule, or approve silently. Show review links first.

## Workflow Skeleton

`/post` is a traceable loop, not a one-shot generator:

1. **Raw thought intake** - save the user's unpolished thought as the source of
   truth.
2. **Content set generation** - produce the requested LinkedIn draft, carousel,
   and/or image assets.
3. **Preview and trace** - expose Content Studio, direct PDF/image links, detail
   JSON, dispatch sidecars, and rendered screenshots/previews.
4. **Taste and quality gate** - judge the real artifact, not only the planned
   spec or JSON score.
5. **Targeted rerun** - if taste rejects a layer, freeze the approved upstream
   decisions and rerun only the failed layer:
   - intake failure -> redo essence/thesis extraction only
   - copy failure -> redo platform copy only
   - visual failure -> redo renderer/template/visual strategy only
   - trace failure -> redo observability/linkage only
   - publish failure -> redo social API boundary only
6. **Human approval** - publish/schedule only after explicit approval.

Do not restart the whole workflow when the failing layer is local and the
upstream decisions are already correct.

## What Success Looks Like

The final answer must include:

- Content Studio link.
- Direct preview links for every generated PDF/image asset.
- Detail/trace JSON link for every generated item.
- Generated `group_id` and `piece_id`s.
- The LinkedIn text draft.
- Trace summary: essence, agents, model/tool, visual route, plan, strategy, judge,
  dispatch, storage path, and posting destination.
- Quality verdict: publishable or not publishable.
- Taste verdict and targeted rerun decision.
- Harness improvements made or proposed.
- Publish status: `not published` unless explicit approval happened.

## Arguments

```text
/post [platform] <raw thought>
/post approve <piece_id>
/post publish <piece_id>
/post queue
```

Platforms: `linkedin`, `instagram`, `facebook`, `threads`, `twitter`, `all`.

If no raw thought is provided, list pending review items and ask which one to
inspect. Do not publish by default.

## Step 1: Start Or Check Holus

Use the existing app/API whenever possible.

```bash
cd "$(git rev-parse --show-toplevel)"
curl -s http://127.0.0.1:8003/api/v1/health >/dev/null || \
  uv run uvicorn holus.api.app:app --host 127.0.0.1 --port 8003
```

For the frontend, prefer an already-running Content Studio. If port `3000` is
busy, use `3001` or the next open port.

```bash
cd "$(git rev-parse --show-toplevel)/observatory/frontend"
npm run dev -- -p 3001
```

Use the frontend host for user-facing asset links because it proxies `/api/v1/*`
to the backend:

```text
http://localhost:3001/content
http://localhost:3001/api/v1/content/{piece_id}
http://localhost:3001/api/v1/content/{piece_id}/pdf
http://localhost:3001/api/v1/content/{piece_id}/image
```

If the client exposes a proxy URL, use that URL instead of `localhost` in the
final answer. Do not create a public tunnel unless the user explicitly approves.

## Step 2: Submit The Raw Thought

For LinkedIn-first runs:

```bash
cd "$(git rev-parse --show-toplevel)"
curl -sS -X POST http://127.0.0.1:8003/api/v1/content/from-thought \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "thought": "RAW_THOUGHT_HERE",
  "platforms": ["linkedin_text", "linkedin_carousel", "linkedin_image"],
  "source_type": "text"
}
JSON
```

If `linkedin_image` fails because the current UI or route does not expose it,
fall back to `["linkedin_text", "linkedin_carousel"]` and report the limitation.

For `all`, use:

```json
[
  "linkedin_text",
  "linkedin_carousel",
  "instagram_image",
  "instagram_carousel",
  "threads_text",
  "twitter_x_thread",
  "facebook_text"
]
```

Capture:

- `group_id`
- every `item.id`
- created status
- API errors
- generated files under `data/content-queue/`
- rendered assets under `data/rendered-content/`

## Step 3: Fetch Details And Build Links

For each generated item:

```bash
curl -sS http://127.0.0.1:8003/api/v1/content/{piece_id}
```

Then build:

- Content Studio: `http://localhost:3001/content`
- Trace JSON: `http://localhost:3001/api/v1/content/{piece_id}`
- PDF: `http://localhost:3001/api/v1/content/{piece_id}/pdf` if `pdf_url` exists
- Image: `http://localhost:3001/api/v1/content/{piece_id}/image` if `image_url` exists
- Image B: `http://localhost:3001/api/v1/content/{piece_id}/image?variant=b` if `image_b_url` exists

Verify every link with `curl -s -o /dev/null -w '%{http_code}'`.

## Step 4: Inspect The Actual Artifact

Do not trust JSON scores. Render or screenshot the real artifact.

For PDFs:

```bash
mkdir -p .tmp-screenshots/post-preview/{piece_id}
pdfinfo data/rendered-content/{piece_id}.pdf
pdftoppm -png data/rendered-content/{piece_id}.pdf .tmp-screenshots/post-preview/{piece_id}/page
```

For images:

```bash
file data/rendered-content/{piece_id}.png
```

Show at least the PDF cover or generated image in the chat. Inspect all pages
for obvious quality failures before calling the result publishable.

## Step 5: Trace Audit

Read the detail JSON and summarize the workflow:

- raw thought
- `thought_essence.thesis`
- `thought_essence.role_map`
- `posting_destination`
- `agent_trace`
- `model_used`
- `quality`
- `visual_spec.renderer`
- `visual_spec.visual_route`
- `visual_spec.visual_plan`
- `visual_spec.visual_strategy`
- `visual_spec.deterministic_agent_run`
- `visual_spec.visual_judge`
- `visual_spec.visual_dispatch`
- `visual_spec.variable_rationale`
- asset paths and sidecar paths

Call out missing trace fields. A run is not fully observable if any of these are
hidden or absent:

- prompt version or prompt hash
- model selection rationale
- cost and latency
- rendered-artifact quality result
- redo reason and prior failed draft
- screenshot or pixel-level artifact check
- evaluator disagreement
- final approval state

## Step 6: Quality And Taste Gate

Use direct language. Do not protect the system.

If the artifact represents Juan publicly, use `/taste holus` or an equivalent
taste verdict. The deterministic visual judge can prove that a file exists,
renders, and avoids known hard failures; it cannot prove that the artifact is
portfolio-grade. Treat deterministic `PASS` as a preflight pass, not a final
taste pass.

Mark **not publishable** if any of these are true:

- artifact looks cheap, generic, ugly, or off-brand
- PDF/image has poor contrast, bad typography, bad crop, unreadable text, or
  inconsistent palette
- visual judge only checked semantics, not the rendered artifact
- text does not preserve Juan's thesis or voice
- current factual claims need verification
- trace is insufficient to explain why the system made its decisions
- publishing destination is ambiguous

If not publishable:

1. Say exactly why.
2. Classify failing layer: intake, generation, visual, platform, review,
   publishing, memory, lineage, scale, app_ux, or agents_harness.
3. Decide the minimal rerun scope:
   - keep the raw thought frozen
   - keep thesis/role map frozen if taste accepted the content premise
   - keep copy frozen if taste rejected only the PDF/image craft
   - keep rendered artifact frozen if taste rejected only trace/observability
   - never regenerate unrelated channels just because one artifact failed
4. Update Holus Thought Evolution Memory:
   `agentic/memory/thoughts/change-log.jsonl`
   and, when relevant, `update-backlog.yaml` or `creative-diversity-ledger.yaml`.
5. If the failure is code/prompt/harness behavior, use `/code holus` or patch the
   repo directly when the change is small and local.
6. Rerun only the failed layer when the system exposes that seam. If no partial
   rerun seam exists yet, log the gap as a harness defect, then rerun the
   smallest available endpoint and report that limitation.

## Step 7: Approval And Publishing

Approval and publishing are explicit modes.

`/post approve <piece_id>` may mark a piece approved only after showing the
current preview and trace.

`/post publish <piece_id>` may call the publish endpoint only after explicit
user confirmation in the current turn.

Dry-run first:

```bash
curl -sS -X POST http://127.0.0.1:8003/api/v1/content/{piece_id}/publish \
  -H 'Content-Type: application/json' \
  --data '{"dry_run": true}'
```

Only after explicit approval:

```bash
curl -sS -X POST http://127.0.0.1:8003/api/v1/content/{piece_id}/publish \
  -H 'Content-Type: application/json' \
  --data '{"dry_run": false}'
```

If publish fails, diagnose the Holus Social API boundary. Use `/code holus` for
Holus-side payload/review-state bugs, or the Holus Social API playbook for
account, token, queue, or platform API failures.

## Step 8: Report Format

Use this format:

```text
What happened
- group_id:
- generated:
- publish status: not published

Review links
- Content Studio:
- LinkedIn post trace:
- PDF preview:
- Image preview:

LinkedIn draft
...

Trace
- Essence:
- Agents:
- Renderer/tool:
- Judge:
- Dispatch:
- Storage:
- Missing observability:

Quality verdict
- Publishable: yes/no
- Why:
- Failed layer:
- Taste verdict:
- Rerun scope:

Harness changes
- Fixed:
- Logged:
- Next:
```

## Degradation

| Issue | Action |
|-------|--------|
| Holus API down | Start `uvicorn holus.api.app:app --port 8003` |
| Frontend down | Start Next on `3001` or next open port |
| Asset link 404 | Inspect queue record and `data/rendered-content/` path |
| PDF/image ugly | Mark not publishable, classify visual/review failure, rerun visual layer only when possible |
| Taste reviewer rejects artifact | Freeze accepted upstream decisions, apply PATH_TO_10 fixes, rerun only failed layer |
| Trace missing | Mark observability failure and log backlog item |
| User wants to publish | Show preview + dry-run payload, ask explicit approval |
| Social API/token failure | Use the Holus Social API playbook or token refresh playbook |
