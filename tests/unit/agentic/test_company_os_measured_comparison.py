"""Measured evidence tests for the canonical Company OS evaluator replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from holus.evaluation import company_os_contract as contract
from holus.evaluation import company_os_regression as regression

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[3]
COMPARISON_DIR = ROOT / "agentic" / "evaluation-comparisons" / "company-os" / "canonical-replay-v1"
FIXED_TS = "2026-08-26T18:00:00Z"
CANDIDATE_NAME = "canonical-replay-v1"
BASELINE_NAME = "canonical-company-os-evaluator-v1-d40d89a"

CASE_IDS = [
    "normal-success-replay",
    "safety-score-regression",
    "required-score-regression",
    "required-suite-and-holdout-regression",
    "malformed-candidate-evidence",
    "immutable-evidence-mismatch",
    "disconfirming-trace-scorecard",
    "candidate-evidence-unknown",
]
EXPECTED_RESULTS = [
    {
        "id": "normal-success-replay",
        "outcome": "pass",
        "regressions": [],
        "unknown_reasons": [],
    },
    {
        "id": "safety-score-regression",
        "outcome": "fail",
        "regressions": [{"category": "safety", "subject": "safety"}],
        "unknown_reasons": [],
    },
    {
        "id": "required-score-regression",
        "outcome": "fail",
        "regressions": [{"category": "required_score", "subject": "task_completion"}],
        "unknown_reasons": [],
    },
    {
        "id": "required-suite-and-holdout-regression",
        "outcome": "fail",
        "regressions": [
            {"category": "holdout", "subject": "company-os-hard-safety"},
            {"category": "required_suite", "subject": "company-os-hard-safety"},
        ],
        "unknown_reasons": [],
    },
    {
        "id": "malformed-candidate-evidence",
        "outcome": "unknown",
        "regressions": [],
        "unknown_reasons": ["candidate_malformed"],
    },
    {
        "id": "immutable-evidence-mismatch",
        "outcome": "unknown",
        "regressions": [],
        "unknown_reasons": ["immutable_evidence_mismatch"],
    },
    {
        "id": "disconfirming-trace-scorecard",
        "outcome": "fail",
        "regressions": [{"category": "output", "subject": "trace_scorecard_consistency"}],
        "unknown_reasons": [],
    },
    {
        "id": "candidate-evidence-unknown",
        "outcome": "unknown",
        "regressions": [],
        "unknown_reasons": ["candidate_evidence_unknown"],
    },
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assert_normalized_json(path: Path) -> None:
    payload = read_json(path)
    assert path.read_text(encoding="utf-8") == json.dumps(payload, indent=2, sort_keys=True) + "\n"


def runner_for(exit_codes: dict[str, int]) -> contract.SuiteRunner:
    def run(suite: contract.SuiteConfig, _repo_root: Path, _env: object) -> contract.SuiteExecution:
        return contract.SuiteExecution(exit_code=exit_codes.get(suite.name, 0))

    return run


def load_baseline() -> regression.BaselineArtifact:
    return regression.BaselineArtifact.model_validate(read_json(COMPARISON_DIR / "baseline.json"))


def canonical_candidate(baseline: regression.BaselineArtifact) -> regression.CandidateArtifacts:
    return regression.CandidateArtifacts(
        trace=baseline.trace,
        scorecard=baseline.scorecard,
        evidence=regression._evidence_identity(ROOT, baseline.trace, baseline.scorecard),
    )


def candidate_from(
    trace: contract.TraceArtifact,
    scorecard: contract.ScorecardArtifact,
) -> regression.CandidateArtifacts:
    return regression.CandidateArtifacts(
        trace=trace,
        scorecard=scorecard,
        evidence=regression._evidence_identity(ROOT, trace, scorecard),
    )


def replace_score(
    scorecard: contract.ScorecardArtifact,
    dimension_name: str,
    score: float | None,
) -> contract.ScorecardArtifact:
    dimensions = tuple(
        dimension.model_copy(update={"score": score})
        if dimension.name == dimension_name
        else dimension
        for dimension in scorecard.score_dimensions
    )
    return scorecard.model_copy(update={"score_dimensions": dimensions})


def replace_suite_status(
    trace: contract.TraceArtifact,
    scorecard: contract.ScorecardArtifact,
    suite_name: str,
    status: str,
    exit_code: int | None,
) -> tuple[contract.TraceArtifact, contract.ScorecardArtifact]:
    suites = tuple(
        suite.model_copy(update={"status": status, "exit_code": exit_code})
        if suite.name == suite_name
        else suite
        for suite in trace.suite_outcomes
    )
    return (
        trace.model_copy(update={"suite_outcomes": suites, "outcome": "fail"}),
        scorecard.model_copy(update={"suite_outcomes": suites, "outcome": "fail"}),
    )


def result_summary(
    case_id: str,
    result: regression.ComparisonScorecard,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "outcome": result.outcome,
        "regressions": [item.model_dump(mode="json") for item in result.regressions],
        "unknown_reasons": list(result.unknown_reasons),
    }


def measure_case(
    case: dict[str, Any],
    baseline: regression.BaselineArtifact,
    scratch_dir: Path,
) -> dict[str, Any]:
    canonical = canonical_candidate(baseline)
    mutation = case["mutation"]
    mutation_type = mutation["type"]
    if mutation_type == "none":
        result = regression.compare_baseline_to_candidate(
            baseline, canonical, CANDIDATE_NAME, FIXED_TS
        )
    elif mutation_type == "score_dimension":
        candidate = candidate_from(
            canonical.trace,
            replace_score(canonical.scorecard, mutation["dimension"], mutation["score"]),
        )
        result = regression.compare_baseline_to_candidate(
            baseline, candidate, CANDIDATE_NAME, FIXED_TS
        )
    elif mutation_type == "suite_status":
        trace, scorecard = replace_suite_status(
            canonical.trace,
            canonical.scorecard,
            mutation["suite"],
            mutation["status"],
            mutation["exit_code"],
        )
        result = regression.compare_baseline_to_candidate(
            baseline, candidate_from(trace, scorecard), CANDIDATE_NAME, FIXED_TS
        )
    elif mutation_type == "malformed_candidate_artifact":
        case_dir = scratch_dir / case["id"]
        case_dir.mkdir()
        baseline_path = case_dir / "baseline.json"
        trace_path = case_dir / "trace.json"
        scorecard_path = case_dir / "scorecard.json"
        contract.write_normalized_json(baseline_path, baseline)
        contract.write_normalized_json(trace_path, canonical.trace)
        contract.write_normalized_json(scorecard_path, canonical.scorecard)
        trace_payload = read_json(trace_path)
        trace_payload[mutation["field"]] = mutation["value"]
        write_json(trace_path, trace_payload)
        result = regression.compare_files(
            ROOT,
            baseline_path,
            trace_path,
            scorecard_path,
            CANDIDATE_NAME,
            case_dir / "comparison.json",
            FIXED_TS,
        )
    elif mutation_type == "evidence_identity":
        evidence = canonical.evidence.model_copy(update={mutation["field"]: mutation["value"]})
        candidate = regression.CandidateArtifacts(canonical.trace, canonical.scorecard, evidence)
        result = regression.compare_baseline_to_candidate(
            baseline, candidate, CANDIDATE_NAME, FIXED_TS
        )
    elif mutation_type == "scorecard_outcome_only":
        candidate = candidate_from(
            canonical.trace,
            canonical.scorecard.model_copy(update={"outcome": mutation["outcome"]}),
        )
        result = regression.compare_baseline_to_candidate(
            baseline, candidate, CANDIDATE_NAME, FIXED_TS
        )
    elif mutation_type == "candidate_outcome_unknown":
        trace = canonical.trace.model_copy(
            update={
                "outcome": "unknown",
                "unknown_reasons": tuple(mutation["unknown_reasons"]),
            }
        )
        scorecard = canonical.scorecard.model_copy(
            update={
                "outcome": "unknown",
                "unknown_reasons": tuple(mutation["unknown_reasons"]),
            }
        )
        result = regression.compare_baseline_to_candidate(
            baseline, candidate_from(trace, scorecard), CANDIDATE_NAME, FIXED_TS
        )
    else:
        raise AssertionError(f"unhandled mutation type: {mutation_type}")
    return result_summary(case["id"], result)


def test_versioned_json_artifacts_are_normalized_and_manifest_hashes_are_current() -> None:
    artifact_names = {
        "baseline.json",
        "candidate.json",
        "case-results.json",
        "case-set.json",
        "comparison-scorecard.json",
        "evidence-manifest.json",
    }
    for artifact_name in artifact_names:
        path = COMPARISON_DIR / artifact_name
        assert_normalized_json(path)
        assert b"\xe2\x80\x94" not in path.read_bytes()

    manifest = read_json(COMPARISON_DIR / "evidence-manifest.json")
    assert manifest["schema"] == "holus.company_os_evaluation_comparison.evidence_manifest.v1"
    assert manifest["comparison"] == CANDIDATE_NAME
    assert manifest["decision"] == "baseline_preserved"
    assert set(manifest["artifacts"]) == artifact_names - {"evidence-manifest.json"}
    assert "evidence-manifest.json" not in manifest["artifacts"]
    assert manifest["artifacts"] == {
        name: contract.sha256_file(COMPARISON_DIR / name) for name in manifest["artifacts"]
    }


def test_case_set_and_results_preserve_expected_order_and_adverse_outcomes() -> None:
    case_set = read_json(COMPARISON_DIR / "case-set.json")
    case_results = read_json(COMPARISON_DIR / "case-results.json")

    assert case_set["version"] == "v1"
    assert [case["id"] for case in case_set["cases"]] == CASE_IDS
    assert [result["id"] for result in case_results["results"]] == CASE_IDS
    assert len(case_set["cases"]) == 8
    assert len(case_results["results"]) == 8
    assert case_results["summary"] == {"fail": 4, "pass": 1, "unknown": 3}
    assert case_results["results"] == EXPECTED_RESULTS
    assert {result["id"] for result in case_results["results"] if result["outcome"] == "fail"} == {
        "safety-score-regression",
        "required-score-regression",
        "required-suite-and-holdout-regression",
        "disconfirming-trace-scorecard",
    }
    assert {
        result["id"] for result in case_results["results"] if result["outcome"] == "unknown"
    } == {
        "malformed-candidate-evidence",
        "immutable-evidence-mismatch",
        "candidate-evidence-unknown",
    }
    assert [case["expected"] for case in case_set["cases"]] == [
        {key: value for key, value in result.items() if key != "id"} for result in EXPECTED_RESULTS
    ]


def test_candidate_descriptor_and_main_scorecard_bind_canonical_evidence() -> None:
    baseline = read_json(COMPARISON_DIR / "baseline.json")
    candidate = read_json(COMPARISON_DIR / "candidate.json")
    comparison = read_json(COMPARISON_DIR / "comparison-scorecard.json")

    assert candidate["name"] == CANDIDATE_NAME
    assert candidate["generated_at_utc"] == FIXED_TS
    assert candidate["decision"] == "baseline_preserved"
    assert candidate["scope"] == {
        "external_apis": "forbidden",
        "network": "prohibited",
        "production_configuration_change": False,
        "runtime_data_access": "forbidden",
        "type": "local_offline_no_change",
    }
    assert candidate["evaluator"] == {
        "name": "company-os-contract",
        "path": regression.EVALUATOR_PATH.as_posix(),
        "sha256": contract.sha256_repo_file(ROOT, regression.EVALUATOR_PATH),
    }
    assert candidate["canonical_config"]["paths"] == sorted(
        baseline["scorecard"]["hashes"]["config"]
    )
    assert candidate["canonical_config"]["sha256"] == baseline["scorecard"]["hashes"]["config"]
    assert comparison["outcome"] == "pass"
    assert comparison["candidate_name"] == CANDIDATE_NAME
    assert comparison["regressions"] == []
    assert comparison["unknown_reasons"] == []
    assert comparison["privacy"] == "summary_only"
    assert comparison["baseline_evidence"] == baseline["evidence"]
    assert comparison["candidate_evidence"] == candidate["evidence"]
    assert comparison["candidate_evidence"] == comparison["baseline_evidence"]


def test_regenerates_committed_baseline_and_main_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_evaluate = contract.evaluate_company_os_contract

    def fake_evaluate(
        repo_root: Path,
        output_dir: Path,
        generated_at_utc: str | None = None,
    ) -> contract.EvaluationRun:
        return original_evaluate(repo_root, output_dir, generated_at_utc, runner_for({}))

    monkeypatch.setattr(regression.contract, "evaluate_company_os_contract", fake_evaluate)
    output_root = tmp_path.resolve(strict=True)
    baseline = regression.capture_baseline(ROOT, output_root / "baseline", BASELINE_NAME, FIXED_TS)
    candidate_run = fake_evaluate(ROOT, output_root / "candidate", FIXED_TS)
    comparison = regression.compare_files(
        ROOT,
        output_root / "baseline" / "baseline.json",
        candidate_run.trace_path,
        candidate_run.scorecard_path,
        CANDIDATE_NAME,
        output_root / "comparison-scorecard.json",
        FIXED_TS,
    )

    assert baseline.name == BASELINE_NAME
    assert comparison.outcome == "pass"
    assert (output_root / "baseline" / "baseline.json").read_text(encoding="utf-8") == (
        COMPARISON_DIR / "baseline.json"
    ).read_text(encoding="utf-8")
    assert (output_root / "comparison-scorecard.json").read_text(encoding="utf-8") == (
        COMPARISON_DIR / "comparison-scorecard.json"
    ).read_text(encoding="utf-8")


def test_reproduces_each_case_result_through_shipped_regression_api(tmp_path: Path) -> None:
    case_set = read_json(COMPARISON_DIR / "case-set.json")
    committed_results = read_json(COMPARISON_DIR / "case-results.json")
    baseline = load_baseline()
    scratch_dir = tmp_path.resolve(strict=True) / "case-replay"
    scratch_dir.mkdir()

    measured_results = [measure_case(case, baseline, scratch_dir) for case in case_set["cases"]]

    assert measured_results == committed_results["results"]
    assert measured_results == EXPECTED_RESULTS
