"""Focused tests for the offline Company OS baseline regression gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from holus.evaluation import company_os_contract as contract
from holus.evaluation import company_os_regression as regression

ROOT = Path(__file__).resolve().parents[3]
FIXED_TS = "2026-08-25T12:00:00Z"


def runner_for(exit_codes: dict[str, int]) -> contract.SuiteRunner:
    def run(suite: contract.SuiteConfig, _repo_root: Path, _env: object) -> contract.SuiteExecution:
        return contract.SuiteExecution(exit_code=exit_codes.get(suite.name, 0))

    return run


def artifacts(tmp_path: Path) -> tuple[regression.BaselineArtifact, regression.CandidateArtifacts]:
    run = contract.evaluate_company_os_contract(
        ROOT, tmp_path / "evaluation", FIXED_TS, runner_for({})
    )
    assert run.outcome == "pass"
    evidence = regression._evidence_identity(ROOT, run.trace, run.scorecard)
    baseline = regression.BaselineArtifact(
        schema=regression.BASELINE_SCHEMA,
        captured_at_utc=FIXED_TS,
        name="main",
        evidence=evidence,
        trace=run.trace,
        scorecard=run.scorecard,
    )
    return baseline, regression.CandidateArtifacts(run.trace, run.scorecard, evidence)


def candidate_with(
    candidate: regression.CandidateArtifacts,
    trace: contract.TraceArtifact | None = None,
    scorecard: contract.ScorecardArtifact | None = None,
) -> regression.CandidateArtifacts:
    next_trace = trace or candidate.trace
    next_scorecard = scorecard or candidate.scorecard
    return regression.CandidateArtifacts(
        next_trace,
        next_scorecard,
        regression._evidence_identity(ROOT, next_trace, next_scorecard),
    )


def test_clean_improvement_passes_and_scorecard_is_deterministic(tmp_path: Path) -> None:
    baseline, candidate = artifacts(tmp_path)

    first = regression.compare_baseline_to_candidate(baseline, candidate, "candidate", FIXED_TS)
    second = regression.compare_baseline_to_candidate(baseline, candidate, "candidate", FIXED_TS)

    assert first.outcome == "pass"
    assert first.regressions == ()
    assert contract.normalized_json(first) == contract.normalized_json(second)
    assert first.privacy == "summary_only"
    assert "query" not in contract.normalized_json(first)


@pytest.mark.parametrize(
    ("category", "subject"),
    [
        ("safety", "safety"),
        ("required_score", "task_completion"),
        ("required_suite", "company-os-trigger-and-contract"),
        ("holdout", "company-os-hard-safety"),
        ("schema", "score_dimensions"),
        ("output", "privacy_safe_output"),
    ],
)
def test_each_normalized_regression_category_fails(
    tmp_path: Path, category: str, subject: str
) -> None:
    baseline, candidate = artifacts(tmp_path)
    trace, scorecard = candidate.trace, candidate.scorecard

    if category in {"safety", "required_score"}:
        changed = tuple(
            dimension.model_copy(update={"score": 0.0}) if dimension.name == subject else dimension
            for dimension in scorecard.score_dimensions
        )
        candidate = candidate_with(
            candidate, scorecard=scorecard.model_copy(update={"score_dimensions": changed})
        )
    elif category in {"required_suite", "holdout"}:
        changed_suites = tuple(
            suite.model_copy(update={"status": "fail", "exit_code": 1})
            if suite.name == subject
            else suite
            for suite in trace.suite_outcomes
        )
        trace = trace.model_copy(update={"suite_outcomes": changed_suites, "outcome": "fail"})
        scorecard = scorecard.model_copy(
            update={"suite_outcomes": changed_suites, "outcome": "fail"}
        )
        candidate = candidate_with(candidate, trace, scorecard)
    elif category == "schema":
        candidate = candidate_with(
            candidate,
            scorecard=scorecard.model_copy(
                update={"score_dimensions": scorecard.score_dimensions[:-1]}
            ),
        )
    else:
        isolation = trace.isolation.model_copy(update={"privacy_policy": {"export": "redacted"}})
        candidate = candidate_with(
            candidate,
            trace=trace.model_copy(update={"isolation": isolation}),
            scorecard=scorecard.model_copy(update={"isolation": isolation}),
        )

    result = regression.compare_baseline_to_candidate(baseline, candidate, "candidate", FIXED_TS)

    assert result.outcome == "fail"
    assert regression.Regression(category=category, subject=subject) in result.regressions


def test_hash_mismatch_is_unknown_never_pass(tmp_path: Path) -> None:
    baseline, candidate = artifacts(tmp_path)
    altered_evidence = candidate.evidence.model_copy(update={"evaluator_sha256": "0" * 64})
    altered_candidate = regression.CandidateArtifacts(
        candidate.trace, candidate.scorecard, altered_evidence
    )

    result = regression.compare_baseline_to_candidate(
        baseline, altered_candidate, "candidate", FIXED_TS
    )

    assert result.outcome == "unknown"
    assert result.unknown_reasons == ("immutable_evidence_mismatch",)


def test_schema_mismatch_is_unknown_not_pass(tmp_path: Path) -> None:
    baseline, candidate = artifacts(tmp_path)
    baseline_path = tmp_path / "baseline.json"
    trace_path = tmp_path / "trace.json"
    scorecard_path = tmp_path / "scorecard.json"
    contract.write_normalized_json(baseline_path, baseline)
    contract.write_normalized_json(trace_path, candidate.trace)
    contract.write_normalized_json(scorecard_path, candidate.scorecard)
    trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
    trace_data["schema"] = "holus.company_os_contract.trace.v0"
    trace_path.write_text(json.dumps(trace_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = regression.compare_files(
        ROOT,
        baseline_path,
        trace_path,
        scorecard_path,
        "candidate",
        tmp_path / "comparison.json",
        FIXED_TS,
    )

    assert result.outcome == "unknown"
    assert result.unknown_reasons == ("candidate_malformed",)


def test_malformed_artifacts_are_unknown_and_are_written_deterministically(tmp_path: Path) -> None:
    output = tmp_path / "comparison.json"
    result = regression.compare_files(
        ROOT,
        tmp_path / "missing-baseline.json",
        tmp_path / "missing-trace.json",
        tmp_path / "missing-scorecard.json",
        "candidate",
        output,
        FIXED_TS,
    )

    assert result.outcome == "unknown"
    assert result.unknown_reasons == ("baseline_malformed",)
    assert output.read_text(encoding="utf-8") == contract.normalized_json(result)


def test_capture_and_compare_commands_use_versioned_local_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_evaluate = contract.evaluate_company_os_contract

    def fake_evaluate(
        repo_root: Path, output_dir: Path, generated_at_utc: str | None = None
    ) -> contract.EvaluationRun:
        return original_evaluate(repo_root, output_dir, generated_at_utc, runner_for({}))

    monkeypatch.setattr(regression.contract, "evaluate_company_os_contract", fake_evaluate)
    baseline = regression.capture_baseline(ROOT, tmp_path / "baseline", "v1", FIXED_TS)
    candidate_run = fake_evaluate(ROOT, tmp_path / "candidate", FIXED_TS)
    result = regression.compare_files(
        ROOT,
        tmp_path / "baseline" / "baseline.json",
        candidate_run.trace_path,
        candidate_run.scorecard_path,
        "next",
        tmp_path / "comparison.json",
        FIXED_TS,
    )

    stored = json.loads((tmp_path / "baseline" / "baseline.json").read_text(encoding="utf-8"))
    assert stored["schema"] == regression.BASELINE_SCHEMA
    assert stored["evidence"]["holdout_sha256"]
    assert baseline.name == "v1"
    assert result.outcome == "pass"


def test_regression_gate_writes_only_outside_candidate_and_never_promotes_or_publishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline, _candidate = artifacts(tmp_path)
    baseline_path = tmp_path / "baseline.json"
    contract.write_normalized_json(baseline_path, baseline)
    source_before = (ROOT / regression.EVALUATOR_PATH).read_bytes()
    calls: list[Path] = []

    original_evaluate = contract.evaluate_company_os_contract

    def fake_evaluate(
        repo_root: Path, output_dir: Path, generated_at_utc: str | None = None
    ) -> contract.EvaluationRun:
        calls.append(output_dir)
        return original_evaluate(repo_root, output_dir, generated_at_utc, runner_for({}))

    monkeypatch.setattr(regression.contract, "evaluate_company_os_contract", fake_evaluate)
    output_dir = tmp_path / "gate"
    result = regression.run_regression_gate(ROOT, baseline_path, "candidate", output_dir, FIXED_TS)

    assert result.outcome == "pass"
    assert calls == [output_dir / "candidate"]
    assert (ROOT / regression.EVALUATOR_PATH).read_bytes() == source_before
    assert (output_dir / "comparison-scorecard.json").exists()
    source = Path(regression.__file__).read_text(encoding="utf-8")
    assert "publish_approved" not in source
    assert "promote" not in source


def test_gate_rejects_output_inside_the_candidate_checkout(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside_candidate"):
        regression._gate_output_dir(ROOT, ROOT / ".eval-artifacts" / "gate")
