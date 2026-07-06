from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path


def test_simulate_content_intake_cases_json_report() -> None:
    script = Path("scripts/simulate_content_intake_cases.py")

    result = subprocess.run(
        [sys.executable, str(script), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)

    assert report["version"] == 13
    assert report["passed"] is True
    assert report["write_records"] is False
    assert report["case_count"] == 5
    assert {case["expected_intent"] for case in report["cases"]} == {
        "raw_thought",
        "online_article",
        "research_note",
        "product_context",
        "campaign_idea",
    }
    assert all(case["checks"]["no_queue_writes"] for case in report["cases"])
    assert all(case["checks"]["source_diagnostics"] for case in report["cases"])
    assert all(case["checks"]["source_evidence"] for case in report["cases"])
    assert all(case["checks"]["source_context"] for case in report["cases"])
    assert all(case["checks"]["variant_differentiation"] for case in report["cases"])
    assert all(case["checks"]["approval_gate"] for case in report["cases"])
    assert all(case["checks"]["channel_fit"] for case in report["cases"])
    assert all(case["checks"]["channel_plan_transformation"] for case in report["cases"])
    assert all(case["checks"]["platform_fit"] for case in report["cases"])
    assert all(case["checks"]["package_platform_fit"] for case in report["cases"])
    assert all(case["channel_fit_diagnostics"]["variant_count"] == 2 for case in report["cases"])
    assert all(
        case["channel_fit_diagnostics"]["channel_job_count"] == 2 for case in report["cases"]
    )
    assert all(
        case["channel_fit_diagnostics"]["distinct_channel_job_count"] == 2
        for case in report["cases"]
    )
    assert all(
        case["channel_fit_diagnostics"]["missing_channel_jobs"] == [] for case in report["cases"]
    )
    assert all(
        all(variant["channel_job"] for variant in case["channel_fit_diagnostics"]["variants"])
        for case in report["cases"]
    )
    assert all(
        all(variant["visual_job"] for variant in case["channel_fit_diagnostics"]["variants"])
        for case in report["cases"]
    )
    assert all(case["channel_plan_diagnostics"]["variant_count"] == 2 for case in report["cases"])
    assert all(
        case["channel_plan_diagnostics"]["transformation_job_count"] == 2
        for case in report["cases"]
    )
    assert all(
        case["channel_plan_diagnostics"]["missing_transformation_jobs"] == []
        for case in report["cases"]
    )
    assert all(
        all(
            variant["transformation_job"]
            for variant in case["channel_plan_diagnostics"]["variants"]
        )
        for case in report["cases"]
    )
    assert all(case["platform_fit_diagnostics"]["variant_count"] == 2 for case in report["cases"])
    assert all(case["platform_fit_diagnostics"]["pass_count"] == 2 for case in report["cases"])
    assert all(
        case["platform_fit_diagnostics"]["failed_piece_ids"] == [] for case in report["cases"]
    )
    assert all(
        all(
            variant["verdict"] == "PASS"
            and variant["platform_job_present"] is True
            and variant["expected_shape"]
            and variant["text_char_count"] > 0
            and variant["text_length_bounds"]["min"]
            <= variant["text_char_count"]
            <= variant["text_length_bounds"]["max"]
            for variant in case["platform_fit_diagnostics"]["variants"]
        )
        for case in report["cases"]
    )
    assert all(
        case["package_platform_fit_summary"]["variant_count"] == 2 for case in report["cases"]
    )
    assert all(case["package_platform_fit_summary"]["pass_count"] == 2 for case in report["cases"])
    assert all(
        case["package_platform_fit_summary"]["failure_count"] == 0 for case in report["cases"]
    )
    assert all(
        case["package_platform_fit_summary"]["missing_count"] == 0 for case in report["cases"]
    )
    assert all(
        case["package_platform_fit_summary"]["failed_piece_ids"] == [] for case in report["cases"]
    )
    assert all(
        case["package_platform_fit_summary"]["missing_piece_ids"] == [] for case in report["cases"]
    )
    assert all(
        case["approval_diagnostics"]["approval_required"] is True for case in report["cases"]
    )
    assert all(
        "explicit human approval" in case["approval_diagnostics"]["publish_gate"]
        for case in report["cases"]
    )
    assert all(case["approval_diagnostics"]["review_steps_count"] >= 4 for case in report["cases"])
    required_review_artifacts = {
        "source_evidence",
        "source_context",
        "channel_plan.transformation_job",
        "quality_evaluation.platform_fit_summary",
        "approval_workflow.publish_gate",
    }
    assert all(
        required_review_artifacts.issubset(set(case["approval_diagnostics"]["review_artifacts"]))
        for case in report["cases"]
    )
    assert all(
        case["approval_diagnostics"]["review_checklist_count"] >= len(required_review_artifacts)
        for case in report["cases"]
    )
    assert all(
        case["approval_diagnostics"]["review_checklist_status_counts"]
        == {"PASS": 5, "REVIEW": 0, "BLOCKED": 0}
        for case in report["cases"]
    )
    assert all(
        case["approval_diagnostics"]["review_checklist_unknown_status_count"] == 0
        for case in report["cases"]
    )
    assert all(
        case["approval_diagnostics"]["review_checklist_missing_evidence_count"] == 0
        for case in report["cases"]
    )
    assert all(
        len(case["approval_diagnostics"]["review_checklist_items"])
        == case["approval_diagnostics"]["review_checklist_count"]
        for case in report["cases"]
    )
    assert all(
        all(
            item["artifact"] and item["status"] == "PASS" and item["evidence"]
            for item in case["approval_diagnostics"]["review_checklist_items"]
        )
        for case in report["cases"]
    )
    assert {case["source_evidence"]["status"] for case in report["cases"]} == {
        "available",
        "operator_supplied",
    }
    product_case = next(
        case for case in report["cases"] if case["id"] == "product_context_pilaster"
    )
    assert product_case["source_context"]["mentioned_products"] == ["Pilaster"]
    assert product_case["source_context"]["product_context_detected"] is True
    assert product_case["source_context"]["targeting_changed"] is False
    assert all(
        "product facts" in variant["transformation_job"]
        and "without changing product targeting" in variant["transformation_job"]
        for variant in product_case["channel_plan_diagnostics"]["variants"]
    )
    assert all(
        case["source_context"]["mentioned_products"] == []
        for case in report["cases"]
        if case["id"] != "product_context_pilaster"
    )
    assert all(
        case["variant_diagnostics"]["distinct_channel_count"] == 2 for case in report["cases"]
    )
    assert all(case["variant_diagnostics"]["distinct_text_count"] == 2 for case in report["cases"])

    url_case = next(case for case in report["cases"] if case["id"] == "pasted_url_article")
    assert url_case["source_diagnostics"]["operator_context_included"] is False
    assert url_case["source_diagnostics"]["source_extract_char_count"] > 120
    assert (
        url_case["source_diagnostics"]["char_count"]
        == url_case["source_diagnostics"]["source_extract_char_count"]
    )
    assert url_case["source_evidence"] == {
        "source_extract_char_count": url_case["source_diagnostics"]["source_extract_char_count"],
        "source_type": "url",
        "operator_context_included": False,
        "status": "available",
    }


def test_simulate_content_intake_cases_human_report() -> None:
    script = Path("scripts/simulate_content_intake_cases.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "PASS raw_thought_builder_note" in result.stdout
    assert "checks=14/14" in result.stdout
    assert "failed=-" in result.stdout
    assert "products=Pilaster" in result.stdout
    assert "checklist=5" in result.stdout
    assert "checklist_statuses=PASS:5,REVIEW:0,BLOCKED:0" in result.stdout
    assert "Summary: 5/5 cases passed" in result.stdout


def test_simulate_content_intake_cases_writes_explicit_json_snapshot(tmp_path: Path) -> None:
    script = Path("scripts/simulate_content_intake_cases.py")
    output_path = tmp_path / "reports" / "intake-simulation.json"

    result = subprocess.run(
        [sys.executable, str(script), "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Summary: 5/5 cases passed" in result.stdout
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["version"] == 13
    assert report["passed"] is True
    assert report["write_records"] is False
    assert report["case_count"] == 5


def test_cycle_61_approval_checklist_diagnostics_count_statuses_and_missing_evidence() -> None:
    namespace = runpy.run_path("scripts/simulate_content_intake_cases.py")
    diagnostics = namespace["_approval_checklist_diagnostics"](
        [
            {
                "artifact": "source_evidence",
                "status": "pass",
                "evidence": "  URL source   fetched  ",
            },
            {
                "artifact": "platform_fit",
                "status": "REVIEW",
                "evidence": "",
            },
            {
                "artifact": "publish_gate",
                "status": "blocked",
                "evidence": "Human approval missing",
            },
            {
                "artifact": "unknown_check",
                "status": "unexpected",
                "evidence": "Unexpected status retained for diagnosis",
            },
        ]
    )

    assert diagnostics["review_checklist_count"] == 4
    assert diagnostics["review_checklist_status_counts"] == {
        "PASS": 1,
        "REVIEW": 1,
        "BLOCKED": 1,
    }
    assert diagnostics["review_checklist_unknown_status_count"] == 1
    assert diagnostics["review_checklist_missing_evidence_count"] == 1
    assert diagnostics["review_checklist_items"] == [
        {
            "artifact": "source_evidence",
            "status": "PASS",
            "evidence": "URL source fetched",
        },
        {
            "artifact": "platform_fit",
            "status": "REVIEW",
            "evidence": "",
        },
        {
            "artifact": "publish_gate",
            "status": "BLOCKED",
            "evidence": "Human approval missing",
        },
        {
            "artifact": "unknown_check",
            "status": "UNEXPECTED",
            "evidence": "Unexpected status retained for diagnosis",
        },
    ]


def test_cycle_61_compare_detects_artifact_level_status_regression(tmp_path: Path) -> None:
    script = Path("scripts/simulate_content_intake_cases.py")
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(
        json.dumps(
            {
                "version": 13,
                "cases": [
                    {
                        "id": "case-a",
                        "passed": True,
                        "checks": {"approval_gate": True},
                        "approval_diagnostics": {
                            "review_checklist_items": [
                                {
                                    "artifact": "source_evidence",
                                    "status": "PASS",
                                    "evidence": "Source URL fetched",
                                }
                            ]
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            {
                "version": 13,
                "cases": [
                    {
                        "id": "case-a",
                        "passed": True,
                        "checks": {"approval_gate": True},
                        "approval_diagnostics": {
                            "review_checklist_items": [
                                {
                                    "artifact": "source_evidence",
                                    "status": "BLOCKED",
                                    "evidence": "Source URL unavailable",
                                }
                            ]
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--compare",
            str(baseline),
            str(current),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    comparison = json.loads(result.stdout)

    assert result.returncode == 1
    assert comparison["passed"] is False
    assert comparison["regressions"] == [
        {
            "artifact": "source_evidence",
            "after": "BLOCKED",
            "before": "PASS",
            "case_id": "case-a",
            "check": "approval_checklist_status",
        }
    ]


def test_cycle_61_compare_falls_back_to_status_counts_for_legacy_diagnostics(
    tmp_path: Path,
) -> None:
    script = Path("scripts/simulate_content_intake_cases.py")
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(
        json.dumps(
            {
                "version": 13,
                "cases": [
                    {
                        "id": "case-a",
                        "passed": True,
                        "checks": {"approval_gate": True},
                        "approval_diagnostics": {
                            "review_checklist_status_counts": {
                                "PASS": 5,
                                "REVIEW": 0,
                                "BLOCKED": 0,
                            }
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            {
                "version": 13,
                "cases": [
                    {
                        "id": "case-a",
                        "passed": True,
                        "checks": {"approval_gate": True},
                        "approval_diagnostics": {
                            "review_checklist_status_counts": {
                                "PASS": 4,
                                "REVIEW": 1,
                                "BLOCKED": 0,
                            }
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--compare",
            str(baseline),
            str(current),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    comparison = json.loads(result.stdout)

    assert result.returncode == 1
    assert comparison["passed"] is False
    assert comparison["regressions"] == [
        {
            "after": 4,
            "before": 5,
            "case_id": "case-a",
            "check": "approval_checklist_status_count",
            "status": "PASS",
        },
        {
            "after": 1,
            "before": 0,
            "case_id": "case-a",
            "check": "approval_checklist_status_count",
            "status": "REVIEW",
        },
    ]


def test_simulate_content_intake_cases_compare_snapshots_fails_on_regression(
    tmp_path: Path,
) -> None:
    script = Path("scripts/simulate_content_intake_cases.py")
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(
        json.dumps(
            {
                "version": 12,
                "cases": [
                    {
                        "id": "case-a",
                        "passed": True,
                        "checks": {"source_context": True, "platform_fit": True},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            {
                "version": 12,
                "cases": [
                    {
                        "id": "case-a",
                        "passed": False,
                        "checks": {"source_context": False, "platform_fit": True},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(script), "--compare", str(baseline), str(current)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "FAIL comparison" in result.stdout
    assert "REGRESSION case=case-a check=source_context before=True after=False" in result.stdout


def test_cycle_61_compare_skips_status_checks_for_mixed_version_snapshots(
    tmp_path: Path,
) -> None:
    script = Path("scripts/simulate_content_intake_cases.py")
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    legacy_report = {
        "version": 12,
        "cases": [
            {
                "id": "case-a",
                "passed": True,
                "checks": {"source_context": True, "platform_fit": True},
            }
        ],
    }
    status_aware_report = {
        "version": 13,
        "cases": [
            {
                "id": "case-a",
                "passed": True,
                "checks": {"source_context": True, "platform_fit": True},
                "approval_diagnostics": {
                    "review_checklist_status_counts": {
                        "PASS": 1,
                        "REVIEW": 0,
                        "BLOCKED": 0,
                    },
                    "review_checklist_items": [
                        {
                            "artifact": "source_evidence",
                            "status": "PASS",
                            "evidence": "Source URL fetched",
                        }
                    ],
                },
            }
        ],
    }

    for before, after in (
        (legacy_report, status_aware_report),
        (status_aware_report, legacy_report),
    ):
        baseline.write_text(json.dumps(before), encoding="utf-8")
        current.write_text(json.dumps(after), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--compare",
                str(baseline),
                str(current),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        comparison = json.loads(result.stdout)

        assert result.returncode == 0
        assert comparison["passed"] is True
        assert comparison["regressions"] == []
        assert comparison["improvements"] == []
