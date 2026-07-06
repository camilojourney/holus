#!/usr/bin/env python3
"""Simulate golden Thought Studio intake cases without publishing or queue writes."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from holus.agents.marketing.thought_pipeline import ThoughtContentPipeline

DEFAULT_FIXTURE = Path("tests/fixtures/golden_content_intake_cases.yaml")
DEFAULT_CHANNELS = ("linkedin_text", "threads_text")
REPORT_VERSION = 13
APPROVAL_CHECKLIST_STATUSES = ("PASS", "REVIEW", "BLOCKED")
APPROVAL_CHECKLIST_STATUS_RANK = {
    "BLOCKED": 0,
    "REVIEW": 1,
    "PASS": 2,
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        msg = f"Fixture has no cases list: {path}"
        raise ValueError(msg)
    return [dict(case) for case in cases if isinstance(case, dict)]


def _case_source_kwargs(case: dict[str, Any]) -> dict[str, Any]:
    source_type = str(case.get("source_type") or "text")
    expected_intent = str(case.get("expected_intent") or "")
    if source_type == "url":
        return {
            "thought": str(case.get("extracted_text") or ""),
            "source_type": "url",
            "source_url": str(case.get("source_url") or ""),
            "source_intent": expected_intent,
            "fetch_source_url": False,
        }
    return {
        "thought": str(case.get("thought") or ""),
        "source_type": "text",
        "source_intent": expected_intent,
        "fetch_source_url": False,
    }


def _contains_signal(values: list[Any], signal: str) -> bool:
    haystack = " ".join(str(value) for value in values).lower()
    return signal.lower() in haystack


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _variant_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    channel_targets = {
        (str(record.get("platform") or ""), str(record.get("content_type") or ""))
        for record in records
    }
    texts = [_clean_text(record.get("text")) for record in records]
    return {
        "channel_count": len(records),
        "distinct_channel_count": len(channel_targets),
        "distinct_text_count": len(set(texts)),
        "text_char_counts": [len(text) for text in texts],
    }


def _channel_fit_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    variants = []
    missing_channel_jobs = []
    for record in records:
        channel_job = _clean_text(record.get("platform_job_plan") or record.get("content_job_plan"))
        visual_job = _clean_text(record.get("content_job_plan"))
        piece_id = str(record.get("piece_id") or "")
        if not channel_job:
            missing_channel_jobs.append(piece_id)
        variants.append(
            {
                "piece_id": piece_id,
                "platform": record.get("platform"),
                "content_type": record.get("content_type"),
                "text_char_count": len(_clean_text(record.get("text"))),
                "channel_job": channel_job,
                "visual_job": visual_job,
            }
        )
    return {
        "variant_count": len(variants),
        "channel_job_count": len(variants) - len(missing_channel_jobs),
        "distinct_channel_job_count": len({variant["channel_job"] for variant in variants}),
        "missing_channel_jobs": missing_channel_jobs,
        "variants": variants,
    }


def _channel_plan_diagnostics(channel_plan: list[Any]) -> dict[str, Any]:
    variants = []
    missing_transformation_jobs = []
    for entry in channel_plan:
        if not isinstance(entry, dict):
            continue
        piece_id = str(entry.get("piece_id") or "")
        transformation_job = _clean_text(entry.get("transformation_job"))
        if not transformation_job:
            missing_transformation_jobs.append(piece_id)
        variants.append(
            {
                "piece_id": piece_id,
                "platform": entry.get("platform"),
                "content_type": entry.get("content_type"),
                "channel_job": _clean_text(entry.get("channel_job")),
                "transformation_job": transformation_job,
            }
        )
    return {
        "variant_count": len(variants),
        "transformation_job_count": len(variants) - len(missing_transformation_jobs),
        "missing_transformation_jobs": missing_transformation_jobs,
        "variants": variants,
    }


def _platform_fit_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    variants = []
    failed_piece_ids = []
    for record in records:
        quality = record.get("quality")
        if not isinstance(quality, dict):
            quality = {}
        platform_fit = quality.get("platform_fit")
        if not isinstance(platform_fit, dict):
            platform_fit = {}

        piece_id = str(record.get("piece_id") or "")
        verdict = str(platform_fit.get("verdict") or "MISSING")
        platform_job_present = platform_fit.get("platform_job_present") is True
        text_char_count = int(platform_fit.get("text_char_count") or 0)
        text_length_bounds = platform_fit.get("text_length_bounds")
        if not isinstance(text_length_bounds, dict):
            text_length_bounds = {}
        expected_shape = _clean_text(platform_fit.get("expected_shape"))
        notes = platform_fit.get("notes")
        if not isinstance(notes, list):
            notes = []

        if verdict != "PASS":
            failed_piece_ids.append(piece_id)
        variants.append(
            {
                "piece_id": piece_id,
                "verdict": verdict,
                "platform": platform_fit.get("platform"),
                "content_type": platform_fit.get("content_type"),
                "text_char_count": text_char_count,
                "text_length_bounds": {
                    "min": int(text_length_bounds.get("min") or 0),
                    "max": int(text_length_bounds.get("max") or 0),
                },
                "platform_job_present": platform_job_present,
                "expected_shape": expected_shape,
                "notes": [str(note) for note in notes],
            }
        )

    return {
        "variant_count": len(variants),
        "pass_count": len(variants) - len(failed_piece_ids),
        "failed_piece_ids": failed_piece_ids,
        "variants": variants,
    }


def _approval_checklist_diagnostics(review_checklist: list[Any]) -> dict[str, Any]:
    status_counts = dict.fromkeys(APPROVAL_CHECKLIST_STATUSES, 0)
    items: list[dict[str, str]] = []
    unknown_status_count = 0
    missing_evidence_count = 0
    for raw_item in review_checklist:
        if not isinstance(raw_item, dict):
            continue

        status = str(raw_item.get("status") or "UNKNOWN").upper()
        evidence = _clean_text(raw_item.get("evidence"))
        if status in status_counts:
            status_counts[status] += 1
        else:
            unknown_status_count += 1
        if not evidence:
            missing_evidence_count += 1
        items.append(
            {
                "artifact": str(raw_item.get("artifact") or ""),
                "status": status,
                "evidence": evidence,
            }
        )

    return {
        "review_checklist_count": len(items),
        "review_artifacts": [item["artifact"] for item in items],
        "review_checklist_status_counts": status_counts,
        "review_checklist_unknown_status_count": unknown_status_count,
        "review_checklist_missing_evidence_count": missing_evidence_count,
        "review_checklist_items": items,
    }


async def simulate_cases(
    cases: list[dict[str, Any]],
    *,
    channels: list[str],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="holus-intake-sim-") as tmp:
        tmp_path = Path(tmp)
        pipeline = ThoughtContentPipeline(
            queue_dir=tmp_path / "content-queue",
            rendered_dir=tmp_path / "rendered-content",
        )
        results = []
        for case in cases:
            content_set = await pipeline.create_content_set(
                channels=channels,
                write_records=False,
                **_case_source_kwargs(case),
            )
            package = content_set.package
            source = package.get("source") or {}
            source_context = dict(package.get("source_context") or {})
            channel_plan = list(package.get("channel_plan") or [])
            quality = package.get("quality_evaluation") or {}
            approval = package.get("approval_workflow") or {}
            success_criteria = list(quality.get("success_criteria") or [])
            expected_intent = str(case.get("expected_intent") or "")
            expected_brief_prefix = str(case.get("expected_brief_prefix") or "")
            expected_success_signal = str(case.get("expected_success_signal") or "")
            source_diagnostics = {
                "char_count": source.get("char_count"),
                "operator_context_included": source.get("operator_context_included"),
                "source_extract_char_count": source.get("source_extract_char_count"),
            }
            source_evidence = dict(quality.get("source_evidence") or {})
            variant_diagnostics = _variant_diagnostics(content_set.records)
            channel_fit_diagnostics = _channel_fit_diagnostics(content_set.records)
            channel_plan_diagnostics = _channel_plan_diagnostics(channel_plan)
            platform_fit_diagnostics = _platform_fit_diagnostics(content_set.records)
            package_platform_fit_summary = dict(quality.get("platform_fit_summary") or {})
            review_checklist = approval.get("review_checklist") or []
            approval_checklist_diagnostics = _approval_checklist_diagnostics(review_checklist)
            approval_diagnostics = {
                "status": approval.get("status"),
                "approval_required": approval.get("approval_required"),
                "publish_gate": approval.get("publish_gate"),
                "review_steps_count": len(approval.get("review_steps") or []),
                **approval_checklist_diagnostics,
            }
            source_diagnostics_check = True
            source_evidence_check = source_evidence.get("source_type") == case.get("source_type")
            expected_products = (
                ["Pilaster"] if case.get("expected_intent") == "product_context" else []
            )
            source_context_check = (
                source_context.get("source_intent") == expected_intent
                and source_context.get("mentioned_products") == expected_products
                and source_context.get("targeting_changed") is False
            )
            if case.get("source_type") == "url":
                expected_source_chars = len(_clean_text(case.get("extracted_text")))
                source_diagnostics_check = (
                    source.get("source_extract_char_count") == expected_source_chars
                    and source.get("operator_context_included") is False
                )
                source_evidence_check = (
                    source_evidence.get("status") == "available"
                    and source_evidence.get("source_extract_char_count") == expected_source_chars
                    and source_evidence.get("operator_context_included") is False
                )
            else:
                source_evidence_check = source_evidence.get("status") == "operator_supplied"
            checks = {
                "intent": source.get("intent") == expected_intent,
                "brief_prefix": str(package.get("strategic_brief") or "").startswith(
                    expected_brief_prefix
                ),
                "success_signal": _contains_signal(success_criteria, expected_success_signal),
                "source_diagnostics": source_diagnostics_check,
                "source_evidence": source_evidence_check,
                "source_context": source_context_check,
                "variant_differentiation": (
                    variant_diagnostics["distinct_channel_count"] == len(channels)
                    and variant_diagnostics["distinct_text_count"] == len(channels)
                ),
                "approval_gate": (
                    approval_diagnostics["status"] == "pending_review"
                    and approval_diagnostics["approval_required"] is True
                    and "explicit human approval" in str(approval_diagnostics["publish_gate"])
                    and approval_diagnostics["review_steps_count"] >= 4
                    and approval_diagnostics["review_checklist_status_counts"]["PASS"]
                    == approval_diagnostics["review_checklist_count"]
                    and approval_diagnostics["review_checklist_unknown_status_count"] == 0
                    and approval_diagnostics["review_checklist_missing_evidence_count"] == 0
                    and {
                        "source_evidence",
                        "source_context",
                        "channel_plan.transformation_job",
                        "quality_evaluation.platform_fit_summary",
                        "approval_workflow.publish_gate",
                    }.issubset(set(approval_diagnostics["review_artifacts"]))
                ),
                "channel_fit": (
                    channel_fit_diagnostics["variant_count"] == len(channels)
                    and channel_fit_diagnostics["channel_job_count"] == len(channels)
                    and channel_fit_diagnostics["distinct_channel_job_count"] == len(channels)
                    and not channel_fit_diagnostics["missing_channel_jobs"]
                ),
                "channel_plan_transformation": (
                    channel_plan_diagnostics["variant_count"] == len(channels)
                    and channel_plan_diagnostics["transformation_job_count"] == len(channels)
                    and not channel_plan_diagnostics["missing_transformation_jobs"]
                    and all(
                        variant["transformation_job"]
                        for variant in channel_plan_diagnostics["variants"]
                    )
                ),
                "platform_fit": (
                    platform_fit_diagnostics["variant_count"] == len(channels)
                    and platform_fit_diagnostics["pass_count"] == len(channels)
                    and not platform_fit_diagnostics["failed_piece_ids"]
                    and all(
                        variant["platform_job_present"]
                        and variant["expected_shape"]
                        and variant["text_char_count"] > 0
                        for variant in platform_fit_diagnostics["variants"]
                    )
                ),
                "package_platform_fit": (
                    package_platform_fit_summary.get("variant_count") == len(channels)
                    and package_platform_fit_summary.get("pass_count") == len(channels)
                    and package_platform_fit_summary.get("failure_count") == 0
                    and package_platform_fit_summary.get("missing_count") == 0
                    and package_platform_fit_summary.get("failed_piece_ids") == []
                    and package_platform_fit_summary.get("missing_piece_ids") == []
                ),
                "item_count": len(content_set.records) == len(channels),
                "no_queue_writes": not any((tmp_path / "content-queue").glob("*")),
            }
            results.append(
                {
                    "id": case.get("id"),
                    "source_type": case.get("source_type"),
                    "expected_intent": expected_intent,
                    "observed_intent": source.get("intent"),
                    "strategic_brief": package.get("strategic_brief"),
                    "primary_channel": (package.get("distribution_recommendation") or {}).get(
                        "primary_channel"
                    ),
                    "ready_for_human_review": quality.get("ready_for_human_review"),
                    "source_diagnostics": source_diagnostics,
                    "source_evidence": source_evidence,
                    "source_context": source_context,
                    "variant_diagnostics": variant_diagnostics,
                    "approval_diagnostics": approval_diagnostics,
                    "channel_fit_diagnostics": channel_fit_diagnostics,
                    "channel_plan_diagnostics": channel_plan_diagnostics,
                    "platform_fit_diagnostics": platform_fit_diagnostics,
                    "package_platform_fit_summary": package_platform_fit_summary,
                    "records": len(content_set.records),
                    "checks": checks,
                    "passed": all(checks.values()),
                }
            )

    return {
        "version": REPORT_VERSION,
        "write_records": False,
        "channels": channels,
        "case_count": len(results),
        "passed": all(result["passed"] for result in results),
        "cases": results,
    }


def _print_human(report: dict[str, Any]) -> None:
    for result in report["cases"]:
        status = "PASS" if result["passed"] else "FAIL"
        checks = result.get("checks") if isinstance(result.get("checks"), dict) else {}
        passed_checks = sum(1 for passed in checks.values() if passed)
        failed_checks = sorted(str(name) for name, passed in checks.items() if not passed)
        source_context = (
            result.get("source_context") if isinstance(result.get("source_context"), dict) else {}
        )
        mentioned_products = source_context.get("mentioned_products")
        products = ",".join(str(product) for product in mentioned_products or []) or "-"
        approval = (
            result.get("approval_diagnostics")
            if isinstance(result.get("approval_diagnostics"), dict)
            else {}
        )
        checklist_status_counts = approval.get("review_checklist_status_counts")
        if not isinstance(checklist_status_counts, dict):
            checklist_status_counts = {}
        checklist_statuses = ",".join(
            f"{status}:{checklist_status_counts.get(status, 0)}"
            for status in APPROVAL_CHECKLIST_STATUSES
        )
        print(
            f"{status} {result['id']} "
            f"intent={result['observed_intent']} "
            f"records={result['records']} "
            f"primary={result['primary_channel']} "
            f"checks={passed_checks}/{len(checks)} "
            f"failed={','.join(failed_checks) if failed_checks else '-'} "
            f"products={products} "
            f"checklist={approval.get('review_checklist_count', 0)} "
            f"checklist_statuses={checklist_statuses}"
        )
    passed = sum(1 for result in report["cases"] if result["passed"])
    print(f"Summary: {passed}/{report['case_count']} cases passed")


def _load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Report is not a JSON object: {path}"
        raise ValueError(msg)
    return payload


def _case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = report.get("cases")
    if not isinstance(cases, list):
        return {}
    mapped = {}
    for case in cases:
        if isinstance(case, dict) and case.get("id"):
            mapped[str(case["id"])] = case
    return mapped


def _approval_checklist_statuses(case: dict[str, Any]) -> dict[str, str] | None:
    approval = case.get("approval_diagnostics")
    if not isinstance(approval, dict):
        return None
    items = approval.get("review_checklist_items")
    if not isinstance(items, list):
        return None

    statuses: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict) or not item.get("artifact"):
            continue
        statuses[str(item["artifact"])] = str(item.get("status") or "UNKNOWN").upper()
    return statuses


def _approval_checklist_status_counts(case: dict[str, Any]) -> dict[str, int] | None:
    approval = case.get("approval_diagnostics")
    if not isinstance(approval, dict):
        return None
    raw_counts = approval.get("review_checklist_status_counts")
    if not isinstance(raw_counts, dict):
        return None
    return {status: int(raw_counts.get(status) or 0) for status in APPROVAL_CHECKLIST_STATUSES}


def _compare_reports(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    baseline_cases = _case_map(baseline)
    current_cases = _case_map(current)
    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    for case_id in sorted(set(baseline_cases) | set(current_cases)):
        before = baseline_cases.get(case_id)
        after = current_cases.get(case_id)
        if before is None:
            improvements.append({"case_id": case_id, "check": "case_added"})
            continue
        if after is None:
            regressions.append({"case_id": case_id, "check": "case_missing"})
            continue

        before_passed = bool(before.get("passed"))
        after_passed = bool(after.get("passed"))
        if before_passed and not after_passed:
            regressions.append(
                {"case_id": case_id, "check": "passed", "before": True, "after": False}
            )
        elif not before_passed and after_passed:
            improvements.append(
                {"case_id": case_id, "check": "passed", "before": False, "after": True}
            )

        raw_before_checks = before.get("checks")
        raw_after_checks = after.get("checks")
        before_checks: dict[str, Any] = (
            raw_before_checks if isinstance(raw_before_checks, dict) else {}
        )
        after_checks: dict[str, Any] = (
            raw_after_checks if isinstance(raw_after_checks, dict) else {}
        )
        for check_name in sorted(set(before_checks) | set(after_checks)):
            before_value = before_checks.get(check_name)
            after_value = after_checks.get(check_name)
            if before_value is True and after_value is not True:
                regressions.append(
                    {
                        "case_id": case_id,
                        "check": check_name,
                        "before": before_value,
                        "after": after_value,
                    }
                )
            elif before_value is not True and after_value is True:
                improvements.append(
                    {
                        "case_id": case_id,
                        "check": check_name,
                        "before": before_value,
                        "after": after_value,
                    }
                )

        before_statuses = _approval_checklist_statuses(before)
        after_statuses = _approval_checklist_statuses(after)
        before_status_counts = _approval_checklist_status_counts(before)
        after_status_counts = _approval_checklist_status_counts(after)
        if before_statuses is not None and after_statuses is not None:
            for artifact in sorted(set(before_statuses) | set(after_statuses)):
                before_status = before_statuses.get(artifact)
                after_status = after_statuses.get(artifact)
                change: dict[str, Any] = {
                    "case_id": case_id,
                    "check": "approval_checklist_status",
                    "artifact": artifact,
                    "before": before_status,
                    "after": after_status,
                }
                if before_status is None:
                    if after_status == "PASS":
                        improvements.append(change)
                    else:
                        regressions.append(change)
                elif after_status is None:
                    regressions.append(change)
                else:
                    before_rank = APPROVAL_CHECKLIST_STATUS_RANK.get(before_status, -1)
                    after_rank = APPROVAL_CHECKLIST_STATUS_RANK.get(after_status, -1)
                    if after_rank < before_rank:
                        regressions.append(change)
                    elif after_rank > before_rank:
                        improvements.append(change)
        elif before_status_counts is not None and after_status_counts is not None:
            for status in APPROVAL_CHECKLIST_STATUSES:
                before_count = before_status_counts[status]
                after_count = after_status_counts[status]
                if before_count == after_count:
                    continue
                change = {
                    "case_id": case_id,
                    "check": "approval_checklist_status_count",
                    "status": status,
                    "before": before_count,
                    "after": after_count,
                }
                is_regression = (
                    after_count < before_count if status == "PASS" else after_count > before_count
                )
                if is_regression:
                    regressions.append(change)
                else:
                    improvements.append(change)

    return {
        "mode": "compare",
        "baseline_version": baseline.get("version"),
        "current_version": current.get("version"),
        "baseline_case_count": len(baseline_cases),
        "current_case_count": len(current_cases),
        "regression_count": len(regressions),
        "improvement_count": len(improvements),
        "regressions": regressions,
        "improvements": improvements,
        "passed": not regressions,
    }


def _print_comparison(report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    print(
        f"{status} comparison "
        f"regressions={report['regression_count']} "
        f"improvements={report['improvement_count']} "
        f"baseline_version={report['baseline_version']} "
        f"current_version={report['current_version']}"
    )
    for regression in report["regressions"]:
        artifact = regression.get("artifact")
        checklist_status = regression.get("status")
        message = (
            "REGRESSION "
            f"case={regression['case_id']} "
            f"check={regression['check']} "
            f"before={regression.get('before', '-')} "
            f"after={regression.get('after', '-')}"
        )
        if artifact:
            message = f"{message} artifact={artifact}"
        if checklist_status:
            message = f"{message} status={checklist_status}"
        print(message)
    for improvement in report["improvements"]:
        artifact = improvement.get("artifact")
        checklist_status = improvement.get("status")
        message = (
            "IMPROVEMENT "
            f"case={improvement['case_id']} "
            f"check={improvement['check']} "
            f"before={improvement.get('before', '-')} "
            f"after={improvement.get('after', '-')}"
        )
        if artifact:
            message = f"{message} artifact={artifact}"
        if checklist_status:
            message = f"{message} status={checklist_status}"
        print(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Golden intake fixture YAML.",
    )
    parser.add_argument(
        "--channels",
        default=",".join(DEFAULT_CHANNELS),
        help="Comma-separated Thought Studio channels to simulate.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the machine-readable JSON report.",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        type=Path,
        metavar=("BASELINE", "CURRENT"),
        help="Compare two saved JSON reports and fail on regressions.",
    )
    args = parser.parse_args()

    if args.compare:
        report = _compare_reports(_load_report(args.compare[0]), _load_report(args.compare[1]))
        json_report = json.dumps(report, indent=2, sort_keys=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(f"{json_report}\n", encoding="utf-8")
        if args.json:
            print(json_report)
        else:
            _print_comparison(report)
        return 0 if report["passed"] else 1

    channels = [channel.strip() for channel in args.channels.split(",") if channel.strip()]
    report = asyncio.run(simulate_cases(load_cases(args.fixture), channels=channels))
    json_report = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{json_report}\n", encoding="utf-8")
    if args.json:
        print(json_report)
    else:
        _print_human(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
