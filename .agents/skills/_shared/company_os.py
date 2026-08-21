#!/usr/bin/env python3
"""Deterministic Company OS desk helpers.

These helpers keep the Company domain skills runnable without live API access.
External silos are represented as explicit handoff payloads and DRY_RUN-safe
approval gates; no publish, outreach, spend, or CRM mutation happens here.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOLUS_ROOT = Path(__file__).resolve().parents[3]
JSON_DUMP_KWARGS = {"sort_keys": True, "separators": (",", ":")}
HOLUS_QUEUE_LIMIT = 25
FUNNEL_STAGE_BY_DESK = {
    "brand": "attract",
    "content": "attract",
    "marketing": "capture",
    "sales": "convert",
}

DESK_CONFIGS: dict[str, dict[str, Any]] = {
    "brand": {
        "skill": "company-brand-desk",
        "automation": "brand-marketing",
        "event_path": ".self-improvement/automations/brand-marketing/events.jsonl",
        "kpi_defaults": {
            "share_of_voice": None,
            "sentiment": None,
            "follower_delta": 0,
            "voice_consistency_score": None,
        },
        "kpi_aliases": {
            "share_of_voice": ("share_of_voice", "sov"),
            "sentiment": ("sentiment", "sentiment_score"),
            "follower_delta": ("follower_delta", "followers_delta"),
            "voice_consistency_score": ("voice_consistency_score", "voice_score"),
        },
        "silo": "LinkedIn official 3-legged OAuth for follower_delta; taste/brand-strategist deep review for voice consistency.",
        "next": "Refresh official LinkedIn follower evidence and run taste brand review before any public-positioning action.",
    },
    "marketing": {
        "skill": "company-marketing-desk",
        "automation": "brand-marketing",
        "event_path": ".self-improvement/automations/brand-marketing/events.jsonl",
        "kpi_defaults": {
            "reach": 0,
            "content_shipped": 0,
            "ctr": None,
            "top_of_funnel_leads": 0,
            "channel_cac": None,
        },
        "kpi_aliases": {
            "reach": ("reach", "impressions"),
            "content_shipped": ("content_shipped", "shipped", "shipped_count"),
            "ctr": ("ctr", "click_through_rate"),
            "top_of_funnel_leads": ("top_of_funnel_leads", "leads", "captured_leads"),
            "channel_cac": ("channel_cac", "cac", "customer_acquisition_cost"),
        },
        "silo": "Beehiiv REST API/webhooks for reach and CTR; Holus/post publish intent must remain human_ic_required.",
        "next": "Sync Beehiiv metrics and route any publish or paid campaign through the supervisor IC ledger.",
    },
    "sales": {
        "skill": "company-sales-desk",
        "automation": "brand-sales",
        "event_path": ".self-improvement/automations/brand-sales/events.jsonl",
        "kpi_defaults": {
            "outreach_sent": 0,
            "reply_rate": None,
            "qualified_leads": 0,
            "meetings_booked": 0,
        },
        "kpi_aliases": {
            "outreach_sent": ("outreach_sent", "outreach"),
            "reply_rate": ("reply_rate", "reply-rate"),
            "qualified_leads": ("qualified_leads", "qualified-leads"),
            "meetings_booked": ("meetings_booked", "meetings"),
        },
        "silo": "Notion API lead capture with manual-review spam flags and 3 requests/second rate-limit awareness.",
        "next": "Review Notion lead quality and route any live outreach through human_ic_required.",
    },
    "content": {
        "skill": "company-content-desk",
        "automation": "brand-content",
        "event_path": ".self-improvement/automations/brand-content/events.jsonl",
        "kpi_defaults": {
            "pipeline_depth": 0,
            "genpeli_jobs_completed": 0,
            "queue_depth": 0,
        },
        "kpi_aliases": {
            "pipeline_depth": ("pipeline_depth", "drafts_ready"),
            "genpeli_jobs_completed": ("genpeli_jobs_completed", "jobs_completed"),
            "queue_depth": ("queue_depth", "holus_queue_depth"),
        },
        "silo": "Genpeli consult-editing handoff for content jobs; Beehiiv/Holus queue reads only in dry-run verification.",
        "next": "Prepare a consult-editing handoff and route publish intent through IC before Holus/post.",
    },
}

EVENT_AUTOMATIONS = ("brand-marketing", "brand-sales", "brand-content", "supervisor")
HUMAN_ACTION_TERMS = {
    "live_publish",
    "publish",
    "paid_campaign",
    "campaign_launch",
    "live_outreach",
    "outreach",
    "external_commitment",
    "spend",
}
BRAND_SAFETY_TERMS = {"guaranteed returns", "risk-free", "unauthorized claim"}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_path(value: str | Path | None = None) -> Path:
    """Resolve an explicit repository root, defaulting to this Holus checkout."""
    return Path(value).expanduser().resolve() if value else HOLUS_ROOT


def rel(repo: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def read_text(path: Path, limit: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def dry_run_mode() -> str:
    return "DRY_RUN" if os.environ.get("DRY_RUN", "0") == "1" else "READ_ONLY"


def read_jsonl(path: Path, limit: int = 1000) -> tuple[list[dict[str, Any]], int]:
    rows: collections.deque[dict[str, Any]] = collections.deque(maxlen=limit)
    skipped = 0
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return [], skipped
    with handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if isinstance(payload, dict):
                rows.append(payload)
            else:
                skipped += 1
    return list(rows), skipped


def parse_holus_queue_item(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {"piece_id": path.stem, "status": "unknown", "path": str(path)}
    if path.suffix == ".json":
        data = read_json(path, {})
        if isinstance(data, dict):
            payload.update(
                {
                    "piece_id": str(data.get("piece_id") or data.get("id") or path.stem),
                    "status": str(data.get("status") or "unknown"),
                    "platform": data.get("platform"),
                    "content_type": data.get("content_type"),
                }
            )
        return payload
    text = read_text(path, limit=4000)
    for raw_line in text.splitlines():
        key, sep, value = raw_line.partition(":")
        if not sep:
            continue
        normalized = key.strip().lower().replace("-", "_")
        if normalized in {"piece_id", "id", "status", "platform", "content_type"}:
            payload[normalized if normalized != "id" else "piece_id"] = value.strip().strip("'\"")
    return payload


def read_holus_content_queue(repo: Path) -> dict[str, Any]:
    """Read only the queue in the current Holus repository.

    The desk never calls a publishing API. It only reports bounded local queue
    metadata as a handoff for the explicit Holus review and approval flow.
    """
    holus_root = repo
    queue_dir = holus_root / "data" / "content-queue"
    files: list[Path] = []
    if queue_dir.exists():
        files = sorted([*queue_dir.glob("*.json"), *queue_dir.glob("*.yaml"), *queue_dir.glob("*.yml")])
    items = [parse_holus_queue_item(path) for path in files[:HOLUS_QUEUE_LIMIT]]
    statuses = collections.Counter(str(item.get("status") or "unknown") for item in items)
    return {
        "repo_path": str(holus_root),
        "queue_path": str(queue_dir),
        "exists": queue_dir.exists(),
        "total_files": len(files),
        "sample_limit": HOLUS_QUEUE_LIMIT,
        "sampled_items": items,
        "pending_review": statuses.get("pending_review", 0),
        "approved": statuses.get("approved", 0),
    }


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, **JSON_DUMP_KWARGS) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def company_kill_status(repo: Path) -> dict[str, Any]:
    kill_file = repo / ".self-improvement" / "COMPANY_KILL"
    if not kill_file.exists():
        return {"verdict": "RUN", "halted": False, "reason": "company_kill_absent", "kill_file": rel(repo, kill_file)}
    try:
        raw_value = kill_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return {"verdict": "HALT", "halted": True, "reason": "company_kill_unreadable", "detail": str(exc)}
    value = raw_value.upper()
    if value in {"CLEAR", "RUN", "OK", "0", "FALSE"}:
        return {"verdict": "RUN", "halted": False, "reason": "company_kill_clear", "kill_file": rel(repo, kill_file)}
    return {"verdict": "HALT", "halted": True, "reason": "company_kill_tripped", "raw_value": raw_value}


def event_metric(row: dict[str, Any], names: tuple[str, ...], default: Any) -> Any:
    kpis = row.get("kpis")
    if not isinstance(kpis, dict):
        kpis = {}
    for name in names:
        if name in kpis:
            return kpis[name]
        if name in row:
            return row[name]
    return default


def latest_skill_event(rows: list[dict[str, Any]], skill: str) -> dict[str, Any] | None:
    for row in reversed(rows):
        if row.get("source") == skill:
            return row
    return None


def build_company_context(repo: Path) -> dict[str, Any]:
    runtime = repo / ".self-improvement"
    automations = runtime / "automations"
    hub = runtime / "hub"
    events: dict[str, dict[str, Any]] = {}
    fix_required: dict[str, dict[str, Any]] = {}
    for automation in EVENT_AUTOMATIONS:
        event_path = automations / automation / "events.jsonl"
        fix_path = automations / automation / "fix_required.jsonl"
        event_rows, event_skipped = read_jsonl(event_path, limit=1000)
        fix_rows, fix_skipped = read_jsonl(fix_path, limit=200)
        events[automation] = {"path": rel(repo, event_path), "rows": event_rows, "skipped_rows": event_skipped}
        fix_required[automation] = {"path": rel(repo, fix_path), "rows": fix_rows, "skipped_rows": fix_skipped}
    decisions, decision_skipped = read_jsonl(hub / "ic_decisions.jsonl", limit=500)
    reports, report_skipped = read_jsonl(hub / "experiment_reports.jsonl", limit=200)
    notion_milestones, notion_skipped = read_jsonl(hub / "notion_milestones.jsonl", limit=200)
    return {
        "schema_version": 1,
        "generated_at_utc": now_utc(),
        "repo_path": str(repo),
        "kill": company_kill_status(repo),
        "runtime_root": rel(repo, runtime),
        "company_os": read_text(automations / "COMPANY_OS.md"),
        "spend_cap": read_text(runtime / "config" / "spend-cap.yaml"),
        "research": read_text(repo / "docs" / "research" / "domain" / "content-evaluation.md"),
        "events": events,
        "fix_required": fix_required,
        "ic_decisions": {
            "path": rel(repo, hub / "ic_decisions.jsonl"),
            "rows": decisions,
            "skipped_rows": decision_skipped,
        },
        "notion_milestones": {
            "path": rel(repo, hub / "notion_milestones.jsonl"),
            "rows": notion_milestones,
            "skipped_rows": notion_skipped,
        },
        "experiment_reports": {
            "path": rel(repo, hub / "experiment_reports.jsonl"),
            "rows": reports,
            "skipped_rows": report_skipped,
        },
    }


def build_desk_context(desk: str, repo: Path) -> dict[str, Any]:
    config = DESK_CONFIGS[desk]
    context = build_company_context(repo)
    context["desk"] = desk
    context["skill"] = config["skill"]
    context["automation"] = config["automation"]
    context["output_event_path"] = config["event_path"]
    return context


def desk_kpis(desk: str, context: dict[str, Any]) -> dict[str, Any]:
    config = DESK_CONFIGS[desk]
    event_block = context["events"].get(config["automation"], {})
    latest = latest_skill_event(event_block.get("rows") or [], config["skill"])
    payload: dict[str, Any] = {}
    for name, default in config["kpi_defaults"].items():
        payload[name] = event_metric(latest or {}, tuple(config["kpi_aliases"].get(name) or (name,)), default)
    return payload


def missing_metrics(kpis: dict[str, Any]) -> list[str]:
    return [name for name, value in kpis.items() if value is None]


def has_approved_ic(context: dict[str, Any], action: str) -> bool:
    required_action = action.lower()
    for row in context.get("ic_decisions", {}).get("rows") or []:
        status = str(row.get("status") or row.get("decision") or "").upper()
        row_action = str(row.get("action") or row.get("approval_for") or row.get("type") or "").lower()
        if status == "APPROVED" and row_action == required_action:
            return True
    return False


def requested_human_action(context: dict[str, Any]) -> str | None:
    for block in context.get("events", {}).values():
        for row in reversed(block.get("rows") or []):
            for field in ("requested_action", "proposed_action", "action", "event"):
                value = str(row.get(field) or "").lower()
                if value in HUMAN_ACTION_TERMS:
                    return value
            if row.get("requires_ic") or row.get("human_ic_required"):
                return str(row.get("event") or row.get("source") or "human_ic_required")
    return None


def build_silo_handoff(desk: str, context: dict[str, Any]) -> dict[str, Any]:
    config = DESK_CONFIGS[desk]
    action = requested_human_action(context)
    approved = has_approved_ic(context, action or "")
    payload: dict[str, Any] = {
        "mode": dry_run_mode(),
        "integration": config["silo"],
        "mutates_external_system": False,
        "human_ic_required": bool(action and not approved),
        "approved_ic_present": bool(action and approved),
        "ic_decisions_path": ".self-improvement/hub/ic_decisions.jsonl",
    }
    if desk == "content":
        payload["consult_editing_handoff"] = {
            "target_skill": "consult-editing",
            "invoke_path": "/consult-editing genpeli",
            "integration_owner": "genpeli",
            "content_job_type": "personal_brand_pipeline",
            "source_queue": ".self-improvement/automations/brand-content/events.jsonl",
            "publish_gate": "ic_decisions.jsonl APPROVED row required before Holus/post",
        }
    if desk == "sales":
        payload["notion_capture_validation"] = {
            "rate_limit_requests_per_second": 3,
            "manual_review_flag": True,
            "captcha_gap_mitigation": "mark suspicious submissions needs_more_evidence before outreach",
        }
    if desk == "marketing":
        payload["beehiiv_metric_source"] = "REST API/webhooks; stale API data creates fix_required, not a crash."
        holus_queue = read_holus_content_queue(Path(context.get("repo_path") or HOLUS_ROOT))
        payload["holus_queue_review"] = {
            "target_skill": "post",
            "invoke_path": "/post holus --dry-run",
            "queue": holus_queue,
            "publish_intent": action in {"publish", "live_publish", "campaign_launch"},
            "publish_gate": "matched APPROVED ic_decisions.jsonl row required",
            "route": "holus_queue_review_only" if action and approved else "human_ic_required",
            "live_api_call": False,
        }
    if desk == "brand":
        payload["taste_handoff"] = {
            "target_skill": "taste",
            "invoke_path": "/taste holus company-brand-desk --deep --agent brand-strategist",
            "mode": "deep",
            "review": "brand-strategist",
        }
    return payload


def append_notion_milestone(repo: Path, desk: str, row: dict[str, Any]) -> dict[str, Any]:
    config = DESK_CONFIGS[desk]
    output_path = repo / ".self-improvement" / "hub" / "notion_milestones.jsonl"
    milestone = {
        "schema_version": 1,
        "ts_utc": now_utc(),
        "source": config["skill"],
        "desk": desk,
        "funnel_stage": FUNNEL_STAGE_BY_DESK.get(desk, desk),
        "status": row.get("status"),
        "summary": row.get("summary"),
        "mode": dry_run_mode(),
        "target": "Notion official API journal entry",
        "invoke_path": "/notion log Company OS funnel milestone",
        "mutates_external_system": False,
        "source_event_path": config["event_path"],
    }
    append_jsonl(output_path, milestone)
    return {"path": rel(repo, output_path), "funnel_stage": milestone["funnel_stage"], "mode": milestone["mode"]}


def render_desk_outputs(desk: str, context: dict[str, Any], repo: Path) -> dict[str, Any]:
    config = DESK_CONFIGS[desk]
    output_path = repo / config["event_path"]
    kpis = desk_kpis(desk, context)
    missing = missing_metrics(kpis)
    action = requested_human_action(context)
    human_ic_required = bool(action and not has_approved_ic(context, action))
    if context["kill"].get("halted"):
        status = "HALT"
        summary = f"{config['skill']} halted by COMPANY_KILL."
    elif missing:
        status = "NEEDS_MORE_EVIDENCE"
        summary = f"{config['skill']} needs evidence for: {', '.join(missing)}."
    else:
        status = "PASS"
        summary = f"{config['skill']} read current Company OS evidence."
    row = {
        "schema_version": 1,
        "ts_utc": now_utc(),
        "source": config["skill"],
        "desk": desk,
        "event": "desk_run",
        "status": status,
        "verdict": status,
        "summary": summary,
        "message": summary,
        "kpis": kpis,
        "approval_boundary": "HUMAN_IC_REQUIRED" if human_ic_required else "NONE",
        "human_ic_required": human_ic_required,
        "requires_ic": human_ic_required,
        "requested_action": action,
        "silo_handoff": build_silo_handoff(desk, context),
        "next": "Wait for matching APPROVED ic_decisions.jsonl row." if human_ic_required else config["next"],
        "evidence_paths": [
            ".self-improvement/automations/COMPANY_OS.md",
            config["event_path"],
            ".self-improvement/hub/ic_decisions.jsonl",
            "docs/research/domain/content-evaluation.md",
        ],
    }
    if desk == "marketing":
        row["spend_cap_status"] = "HUMAN_IC_REQUIRED" if human_ic_required else "WITHIN_CAP"
    row["notion_milestone"] = append_notion_milestone(repo, desk, row)
    row["evidence_paths"].append(".self-improvement/hub/notion_milestones.jsonl")
    append_jsonl(output_path, row)
    append_hub_skill_run(repo, config["skill"], status, [config["event_path"]])
    return row


def is_closed(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or row.get("verdict") or "").lower()
    return status in {"closed", "done", "fixed", "resolved", "duplicate", "obsolete"}


def queue_item(row: dict[str, Any], source_path: str, queue: str) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or row.get("fix_id") or row.get("source") or row.get("event") or queue),
        "source": row.get("source") or row.get("desk"),
        "source_path": source_path,
        "summary": row.get("summary") or row.get("message") or row.get("next") or "Company OS queue item.",
        "status": row.get("status") or row.get("verdict") or "PENDING",
        "verify_command": row.get("verify_command"),
        "next": row.get("next"),
    }


def render_supervisor_outputs(context: dict[str, Any], repo: Path) -> dict[str, Any]:
    queues = {"human_ic_required": [], "ready_for_code": [], "needs_more_evidence": []}
    source_counts: dict[str, int] = {}
    if context["kill"].get("halted"):
        queues["needs_more_evidence"].append(
            {"id": "company-kill", "summary": "COMPANY_KILL is tripped; all Company OS routing is halted."}
        )
    for block in context.get("events", {}).values():
        source_path = block.get("path") or ""
        rows = block.get("rows") or []
        source_counts[source_path] = len(rows)
        for row in rows:
            status = str(row.get("status") or row.get("verdict") or "").upper()
            if row.get("human_ic_required") or row.get("requires_ic") or row.get("approval_boundary") == "HUMAN_IC_REQUIRED":
                queues["human_ic_required"].append(queue_item(row, source_path, "human_ic_required"))
            elif status in {"NEEDS_MORE_EVIDENCE", "WARNING", "WARN", "HALT"}:
                queues["needs_more_evidence"].append(queue_item(row, source_path, "needs_more_evidence"))
    for block in context.get("fix_required", {}).values():
        source_path = block.get("path") or ""
        rows = block.get("rows") or []
        source_counts[source_path] = len(rows)
        for row in rows:
            if is_closed(row):
                continue
            item = queue_item(row, source_path, "ready_for_code")
            if row.get("human_ic_required") or row.get("requires_ic"):
                queues["human_ic_required"].append(item)
            elif row.get("verify_command"):
                queues["ready_for_code"].append(item)
            else:
                queues["needs_more_evidence"].append(item)
    queues["ready_for_code"] = queues["ready_for_code"][:1]
    docket_path = repo / ".self-improvement" / "hub" / "company_docket.json"
    event_path = repo / ".self-improvement" / "automations" / "supervisor" / "events.jsonl"
    docket = {
        "schema_version": 1,
        "updated_at_utc": now_utc(),
        "queues": queues,
        "ready_for_code_max_lanes": 1,
        "source_counts": source_counts,
        "output_paths": [rel(repo, docket_path), rel(repo, event_path)],
    }
    write_json(docket_path, docket)
    depth = sum(len(values) for values in queues.values())
    status = "HALT" if context["kill"].get("halted") else ("WARNING" if queues["human_ic_required"] else "PASS")
    event = {
        "schema_version": 1,
        "ts_utc": now_utc(),
        "source": "company-supervisor",
        "desk": "supervisor",
        "event": "docket_route",
        "status": status,
        "verdict": status,
        "pending_human_ic": len(queues["human_ic_required"]),
        "docket_queue_depth": depth,
        "selected_ready_for_code": queues["ready_for_code"][0] if queues["ready_for_code"] else None,
        "message": f"Supervisor routed {depth} Company OS item(s).",
        "next": "Resolve human_ic_required rows before live publish/outreach." if queues["human_ic_required"] else "Run company-evolve on latest desk metrics.",
    }
    append_jsonl(event_path, event)
    append_hub_skill_run(repo, "company-supervisor", status, [rel(repo, docket_path), rel(repo, event_path)])
    return {"docket": docket, "event": event}


def all_desk_events(context: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for block in context.get("events", {}).values():
        rows.extend(block.get("rows") or [])
    return rows


def choose_improvement(context: dict[str, Any]) -> tuple[str, str, dict[str, list[str]]]:
    rows = all_desk_events(context)
    if not rows:
        return (
            "Create the first real desk metric event for brand, marketing, sales, and content before scaling the funnel.",
            "No desk metric events were available.",
            {"kill": [], "keep": ["Company OS scaffold"], "scale": []},
        )
    latest_by_source: dict[str, dict[str, Any]] = {}
    for row in rows:
        source = str(row.get("source") or row.get("desk") or "")
        if source:
            latest_by_source[source] = row
    sales = latest_by_source.get("company-sales-desk", {}).get("kpis") or {}
    marketing = latest_by_source.get("company-marketing-desk", {}).get("kpis") or {}
    content = latest_by_source.get("company-content-desk", {}).get("kpis") or {}
    if (sales.get("qualified_leads") or 0) == 0:
        return (
            "Improve Notion lead capture quality and qualification flow before increasing outreach volume.",
            "Sales desk has zero qualified_leads in the latest bounded event window.",
            {"kill": [], "keep": ["manual IC gate for outreach"], "scale": ["Notion capture validation"]},
        )
    if (marketing.get("top_of_funnel_leads") or marketing.get("leads") or 0) == 0:
        return (
            "Improve Beehiiv-to-Notion capture handoff so marketing reach converts into top-of-funnel leads.",
            "Marketing desk has reach without captured top_of_funnel_leads.",
            {"kill": [], "keep": ["Beehiiv metrics read path"], "scale": ["capture handoff instrumentation"]},
        )
    if (content.get("pipeline_depth") or 0) == 0:
        return (
            "Increase Genpeli content pipeline depth before adding new distribution commitments.",
            "Content desk has no ready pipeline depth.",
            {"kill": [], "keep": ["Holus publish IC gate"], "scale": ["Genpeli consult-editing handoffs"]},
        )
    return (
        "Scale the highest-evidence content-to-capture loop while keeping publish and outreach under IC approval.",
        "Desk KPIs show nonzero content, capture, and qualified lead signals.",
        {"kill": [], "keep": ["human approval gates"], "scale": ["best-performing funnel loop"]},
    )


def render_evolve_outputs(context: dict[str, Any], repo: Path) -> dict[str, Any]:
    report_path = repo / ".self-improvement" / "hub" / "experiment_reports.jsonl"
    recommendation, why_now, recommendations = choose_improvement(context)
    status = "HALT" if context["kill"].get("halted") else ("PASS" if all_desk_events(context) else "NEEDS_MORE_EVIDENCE")
    row = {
        "schema_version": 1,
        "ts_utc": now_utc(),
        "source": "company-evolve",
        "status": status,
        "decision": "keep",
        "recommendations": recommendations,
        "what_to_improve": recommendation,
        "why_now": why_now,
        "source_event_paths": [block["path"] for block in context.get("events", {}).values()],
        "approval_boundary": "NONE",
        "next": "Send recommendation to supervisor docket; do not mutate live campaigns automatically.",
    }
    append_jsonl(report_path, row)
    append_hub_skill_run(repo, "company-evolve", status, [rel(repo, report_path)])
    return row


def append_hub_skill_run(repo: Path, skill: str, status: str, output_paths: list[str]) -> None:
    row = {
        "schema_version": 1,
        "cid": f"{skill}-{int(time.time())}",
        "skill": skill,
        "ts_utc": now_utc(),
        "verdict": status,
        "output_paths": output_paths,
    }
    append_jsonl(repo / ".self-improvement" / "hub" / "skill_runs.jsonl", row)


def emit_or_write(payload: dict[str, Any], out: Path | None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def context_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--repo-path", type=Path, default=HOLUS_ROOT)
    parser.add_argument("--out", type=Path)
    return parser


def render_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--repo-path", type=Path, default=HOLUS_ROOT)
    parser.add_argument("--context-file", type=Path)
    parser.add_argument("--out", type=Path)
    return parser


def build_desk_context_cli(desk: str) -> int:
    args = context_parser(f"Build {DESK_CONFIGS[desk]['skill']} context.").parse_args()
    emit_or_write(build_desk_context(desk, repo_path(args.repo_path)), args.out)
    return 0


def render_desk_outputs_cli(desk: str) -> int:
    args = render_parser(f"Render {DESK_CONFIGS[desk]['skill']} outputs.").parse_args()
    repo = repo_path(args.repo_path)
    context = read_json(args.context_file, {}) if args.context_file else build_desk_context(desk, repo)
    emit_or_write(render_desk_outputs(desk, context, repo), args.out)
    return 0


def build_supervisor_context_cli() -> int:
    args = context_parser("Build Company supervisor context.").parse_args()
    context = build_company_context(repo_path(args.repo_path))
    context["skill"] = "company-supervisor"
    emit_or_write(context, args.out)
    return 0


def render_supervisor_outputs_cli() -> int:
    args = render_parser("Render Company supervisor outputs.").parse_args()
    repo = repo_path(args.repo_path)
    context = read_json(args.context_file, {}) if args.context_file else build_company_context(repo)
    emit_or_write(render_supervisor_outputs(context, repo), args.out)
    return 0


def build_evolve_context_cli() -> int:
    args = context_parser("Build Company evolve context.").parse_args()
    context = build_company_context(repo_path(args.repo_path))
    context["skill"] = "company-evolve"
    emit_or_write(context, args.out)
    return 0


def render_evolve_outputs_cli() -> int:
    args = render_parser("Render Company evolve outputs.").parse_args()
    repo = repo_path(args.repo_path)
    context = read_json(args.context_file, {}) if args.context_file else build_company_context(repo)
    emit_or_write(render_evolve_outputs(context, repo), args.out)
    return 0
