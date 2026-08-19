# Holus Lineage Contract

**Status:** Implemented (schema `1.0`)
**Owner:** Holus. Consumers, including Holusight, are read-only.

Holus records privacy-safe provenance for its persisted Thought Studio artifacts. This is a local, append-only JSONL artifact—not a tracing platform, a shared database, or a runtime dependency on Holusight or Graphify.

## Implemented flow

```text
source thought / approved research candidate
  -> normalize source (source_thought)
  -> strategy + generation plan (content_set)
  -> persisted queue variant (content_variant)
  -> optional PNG/PDF (visual_asset)
  -> explicit review decision (review_decision)
  -> explicit schedule or publish result (schedule_outcome / publish_outcome)
```

The central emission points are `ThoughtContentPipeline.create_content_set` (after queue persistence), `CandidateStore` (candidate state), and the content API after review/publish/schedule writes. External publish/schedule first reserves a local durable outbox intent keyed by piece ID, content revision, and operation. Delivery is currently contained: the intent is marked with status `contained` and no request is sent to Holus Social API (its write methods raise `ExternalDeliveryContainedError`); when an authenticated approval-grant sender exists, the same request ID will be sent as `Idempotency-Key` before the result is projected into the queue. Lineage errors are logged and never roll back or corrupt the content artifact.

## Canonical IDs and storage

| Existing ID | Lineage node ID | Owner/persistence |
|---|---|---|
| `group_id` | `source:{group_id}`, `content-set:{group_id}` | Thought Studio run and plan |
| `piece_id` | `content:{piece_id}` | `data/content-queue/{piece_id}.yaml` |
| rendered filename | `visual:{piece_id}:{image|pdf}` | `data/rendered-content/` |
| candidate ID | `research-candidate:{candidate_id}` | `data/research/candidates/` |
| review/publish state | `{outcome}:{piece_id}:{status}` | append-only lineage event |

The lineage owner is `data/lineage/events.jsonl` (override CLI path with `--directory`; configured default is `HOLUS_LINEAGE_DIR=data/lineage`). It is intentionally git-ignored runtime data.

## Versioned wire format

Each JSONL line is an event containing a schema version, deterministic event ID, one node, and zero or more edges. `schema_version` is exactly `"1.0"`. Nodes contain stable identity, artifact type, producer, timestamp, run/correlation IDs, status, optional content/config/model hashes, checksums, a stable **relative** artifact reference, and safe scalar metadata. Edges contain a deterministic ID and directed relation.

Example (content is intentionally absent):

```json
{
  "schema_version": "1.0",
  "node": {
    "node_id": "content:thought-a1b2-linkedin_text",
    "artifact_type": "content_variant",
    "artifact_ref": "content-queue/thought-a1b2-linkedin_text.yaml",
    "content_hash": "sha256...",
    "correlation_id": "a1b2",
    "status": "pending_review"
  },
  "edges": [{"relation": "contains", "from_node_id": "content-set:a1b2", "to_node_id": "content:thought-a1b2-linkedin_text"}]
}
```

### Privacy and redaction

The contract never exports full source text, generated post text, URLs, raw input, API keys, tokens, passwords, authorization values, or absolute/temp paths. Content is represented only by a SHA-256 hash. Unsafe metadata keys and secret-looking values are dropped; text metadata is capped at 512 characters. Consumer implementations must treat hashes and IDs as operational metadata, not as permission to fetch private artifacts.

## Holusight consumer boundary

Holusight must **not** import `holus` Python packages or read Holus databases/files directly. Its supported ingestion choices are:

1. `GET /api/v1/lineage/export?after_seq=0&limit=1000` — validated, sequence-cursored ledger page.
2. `holus lineage export --after-seq 0 --output /safe/export/holus-lineage.json` — a point-in-time validated export.

Both return `schema_version`, nodes, edges, checksums/references when available, and diagnostics. The lineage API has no mutation endpoints: non-GET requests receive `405`. Content publish/schedule is a separate privileged control surface: non-dry dispatch requires an immutable `review_decision_id`, status `approved`, and an exact `expected_revision`; otherwise it fails closed with `409 APPROVAL_REQUIRED` or `409 REVISION_CONFLICT`. Holus deployments must place every Observatory route behind their normal authentication/reverse proxy before exposing it outside localhost.

### Incremental consumption

`after_seq` is an exclusive committed-ledger watermark. A consumer follows `next_after_seq` until `null`, persists `snapshot_seq` and `ledger_hash`, then uses its last accepted sequence as the next `after_seq`. Records are strictly ordered by contiguous `seq` and chained by `prev_event_hash`/`event_hash`; an invalid chain is rejected with `409 LINEAGE_INVALID`, never silently partially exported. Nodes remain append-only state observations; consumers retain the newest observation per node ID by `created_at`/recorded event time.

## Operator commands

```bash
# Human-readable, deterministic export; no post body or source text is emitted.
uv run python -m holus lineage export --after-seq 0 --output /var/backups/holus-lineage.json

# Check malformed JSONL, broken references, orphan nodes, counts and freshness.
uv run python -m holus lineage validate

# Fail if any consistency issue exists; additionally require a non-partial content graph.
uv run python -m holus lineage validate --require-complete

# Same checks via the Observatory API.
curl http://localhost:8000/api/v1/lineage/validate
curl 'http://localhost:8000/api/v1/lineage/export?after_seq=0&limit=1000'
```

`validate` exits nonzero for malformed or broken lineage. `--require-complete` also exits nonzero when a source-rooted run lacks its content set or persisted variant. The health endpoint reports `lineage_valid`, `lineage_complete`, and node count; an invalid store is unhealthy, while a structurally partial store is degraded—not complete.

## Backup, restore, retention, and migration

Back up `data/lineage/events.jsonl` together with the referenced `data/content-queue/` and `data/rendered-content/` files. Use a filesystem snapshot or stop writers for a perfectly point-in-time backup; each emitted line is locked and fsynced, so a copied complete line remains valid. Restore by replacing the `data/lineage/` directory, then run `holus lineage validate --require-complete` before enabling consumers.

Retain lineage for at least 365 days (the configured policy). Before pruning, export a manifest to durable backup and retain all referenced queue/assets for the same retention window. Schema `1.0` readers reject unknown/older line versions and report them as malformed rather than silently interpreting them. Future versions must add a documented migration/export path and keep this reader behavior explicit.

## Troubleshooting

| Symptom | Action |
|---|---|
| `malformed_lines` or `broken_edge_ids` | stop external ingestion, back up the JSONL, inspect the listed lines, restore a validated backup or migrate explicitly |
| `orphan_node_ids` / `complete: false` | inspect the source run; the primary content artifact may predate lineage or the run stopped before persistence—do not label it complete |
| missing checksum/reference | asset was unavailable when emitted; content remains usable but the export truthfully marks it absent |
| no `events.jsonl` | no tracked pipeline write has run yet; this is healthy but has no lineage to ingest |

## Explicit non-goals and future work

Graphify may later consume this manifest or enrich it with a source-code graph. Holus runtime does not import or invoke Graphify, and generated Graphify output is not lineage data. Distributed tracing, a message broker, Holusight database access, full historical backfill, and direct social-platform outcome ingestion are not implemented by this slice.
