"""Offline baseline comparison and regression gate for the Company OS evaluator.

This module deliberately consumes the canonical v1 trace and scorecard models from
``company_os_contract``.  It never imports publishing, scheduling, queue, or
integration code.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

from pydantic import Field, ValidationError, field_validator

from holus.evaluation import company_os_contract as contract

BASELINE_SCHEMA: Literal["holus.company_os_regression.baseline.v1"] = (
    "holus.company_os_regression.baseline.v1"
)
COMPARISON_SCHEMA: Literal["holus.company_os_regression.comparison.v1"] = (
    "holus.company_os_regression.comparison.v1"
)
EVALUATOR_PATH = Path("src/holus/evaluation/company_os_contract.py")

ComparisonOutcome = Literal["pass", "fail", "unknown"]
RegressionCategory = Literal[
    "safety", "required_score", "required_suite", "holdout", "schema", "output"
]


class RegressionModel(contract.StrictModel):
    """Immutable, extra-forbid model base for regression artifacts."""


class EvidenceIdentity(RegressionModel):
    """Hashes needed to prove two canonical evaluations are comparable."""

    trace_sha256: str
    scorecard_sha256: str
    trace_schema: str
    scorecard_schema: str
    evaluator: str
    evaluator_sha256: str
    evaluation_manifest_sha256: str
    fixture_manifest_sha256: str
    holdout_sha256: dict[str, str]
    suite_command_sha256: dict[str, str]

    _digests = field_validator(
        "trace_sha256",
        "scorecard_sha256",
        "evaluator_sha256",
        "evaluation_manifest_sha256",
        "fixture_manifest_sha256",
    )(contract.validate_sha256_value)
    _hash_maps = field_validator("holdout_sha256", "suite_command_sha256")(
        contract.validate_sha256_hash_map
    )


class BaselineArtifact(RegressionModel):
    """A local, immutable baseline with canonical foundation artifacts embedded."""

    schema_id: Literal["holus.company_os_regression.baseline.v1"] = Field(alias="schema")
    captured_at_utc: str
    name: str = Field(min_length=1, max_length=128)
    evidence: EvidenceIdentity
    trace: contract.TraceArtifact
    scorecard: contract.ScorecardArtifact

    _captured_at_utc = field_validator("captured_at_utc")(contract.validate_utc_timestamp_value)


class Regression(RegressionModel):
    category: RegressionCategory
    subject: str


class ComparisonScorecard(RegressionModel):
    """Privacy-safe result of comparing a baseline to one named candidate."""

    schema_id: Literal["holus.company_os_regression.comparison.v1"] = Field(alias="schema")
    generated_at_utc: str
    baseline_name: str
    candidate_name: str
    outcome: ComparisonOutcome
    baseline_evidence: EvidenceIdentity | None
    candidate_evidence: EvidenceIdentity | None
    regressions: tuple[Regression, ...]
    unknown_reasons: tuple[str, ...]
    privacy: Literal["summary_only"] = "summary_only"

    _generated_at_utc = field_validator("generated_at_utc")(contract.validate_utc_timestamp_value)


@dataclass(frozen=True)
class CandidateArtifacts:
    trace: contract.TraceArtifact
    scorecard: contract.ScorecardArtifact
    evidence: EvidenceIdentity


def _canonical_hash(payload: contract.StrictModel) -> str:
    return contract.sha256_text(contract.normalized_json(payload))


def _suite_hashes(trace: contract.TraceArtifact) -> dict[str, str]:
    return {
        suite.name: suite.command_sha256
        for suite in sorted(trace.suite_outcomes, key=lambda item: item.name)
    }


def _evidence_identity(
    repo_root: Path,
    trace: contract.TraceArtifact,
    scorecard: contract.ScorecardArtifact,
) -> EvidenceIdentity:
    """Return only the comparison-safe subset of canonical evaluator evidence."""
    manifest_hash = trace.hashes.evaluation_manifest_sha256
    fixture_hash = trace.fixture_set.manifest_sha256
    if manifest_hash is None or fixture_hash is None:
        raise ValueError("incomplete_hash_evidence")
    return EvidenceIdentity(
        trace_sha256=_canonical_hash(trace),
        scorecard_sha256=_canonical_hash(scorecard),
        trace_schema=trace.schema_id,
        scorecard_schema=scorecard.schema_id,
        evaluator=trace.evaluator,
        evaluator_sha256=contract.sha256_repo_file(repo_root, EVALUATOR_PATH),
        evaluation_manifest_sha256=manifest_hash,
        fixture_manifest_sha256=fixture_hash,
        holdout_sha256=dict(sorted(trace.hashes.holdout.items())),
        suite_command_sha256=_suite_hashes(trace),
    )


def _evidence_matches_artifacts(
    evidence: EvidenceIdentity,
    trace: contract.TraceArtifact,
    scorecard: contract.ScorecardArtifact,
) -> bool:
    """Check the local baseline did not detach its hashes from embedded evidence."""
    return (
        evidence.trace_sha256 == _canonical_hash(trace)
        and evidence.scorecard_sha256 == _canonical_hash(scorecard)
        and evidence.trace_schema == trace.schema_id
        and evidence.scorecard_schema == scorecard.schema_id
        and evidence.evaluator == trace.evaluator
        and evidence.evaluation_manifest_sha256 == trace.hashes.evaluation_manifest_sha256
        and evidence.fixture_manifest_sha256 == trace.fixture_set.manifest_sha256
        and evidence.holdout_sha256 == dict(sorted(trace.hashes.holdout.items()))
        and evidence.suite_command_sha256 == _suite_hashes(trace)
    )


def _artifacts_agree(trace: contract.TraceArtifact, scorecard: contract.ScorecardArtifact) -> bool:
    return (
        trace.schema_id == contract.TRACE_SCHEMA
        and scorecard.schema_id == contract.SCORECARD_SCHEMA
        and trace.repo == scorecard.repo
        and trace.evaluator == scorecard.evaluator
        and trace.outcome == scorecard.outcome
        and trace.fixture_set == scorecard.fixture_set
        and trace.hashes == scorecard.hashes
        and trace.score_dimensions
        == {dimension.name: dimension.requirement for dimension in scorecard.score_dimensions}
        and trace.suite_outcomes == scorecard.suite_outcomes
    )


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_candidate_artifacts(
    repo_root: Path, trace_path: Path, scorecard_path: Path
) -> CandidateArtifacts:
    trace = contract.TraceArtifact.model_validate(_load_json(trace_path))
    scorecard = contract.ScorecardArtifact.model_validate(_load_json(scorecard_path))
    if trace_path.read_text(encoding="utf-8") != contract.normalized_json(trace):
        raise ValueError("candidate_trace_not_normalized")
    if scorecard_path.read_text(encoding="utf-8") != contract.normalized_json(scorecard):
        raise ValueError("candidate_scorecard_not_normalized")
    # A structurally valid trace/scorecard disagreement is a known output
    # regression, not malformed evidence. The comparison classifies it below.
    return CandidateArtifacts(
        trace=trace, scorecard=scorecard, evidence=_evidence_identity(repo_root, trace, scorecard)
    )


def capture_baseline(
    repo_root: Path,
    output_dir: Path,
    name: str,
    generated_at_utc: str | None = None,
) -> BaselineArtifact:
    """Run the canonical evaluator and capture a pass-only local baseline."""
    timestamp = generated_at_utc or contract.now_utc()
    evaluation_dir = output_dir / "evaluation"
    run = contract.evaluate_company_os_contract(repo_root, evaluation_dir, timestamp)
    if run.outcome != "pass":
        raise ValueError("baseline_must_pass")
    baseline = BaselineArtifact(
        schema=BASELINE_SCHEMA,
        captured_at_utc=timestamp,
        name=name,
        evidence=_evidence_identity(repo_root, run.trace, run.scorecard),
        trace=run.trace,
        scorecard=run.scorecard,
    )
    # The foundation resolves temporary directories before its no-follow writer
    # uses them. Reuse that canonical directory so /tmp symlinks are not followed.
    contract.write_normalized_json(run.trace_path.parent.parent / "baseline.json", baseline)
    return baseline


def _load_baseline(path: Path) -> BaselineArtifact:
    baseline = BaselineArtifact.model_validate(_load_json(path))
    if path.read_text(encoding="utf-8") != contract.normalized_json(baseline):
        raise ValueError("baseline_not_normalized")
    if not _artifacts_agree(baseline.trace, baseline.scorecard) or not _evidence_matches_artifacts(
        baseline.evidence, baseline.trace, baseline.scorecard
    ):
        raise ValueError("baseline_artifacts_disagree")
    return baseline


def _unknown_scorecard(
    timestamp: str,
    baseline_name: str,
    candidate_name: str,
    reason: str,
    baseline_evidence: EvidenceIdentity | None = None,
    candidate_evidence: EvidenceIdentity | None = None,
) -> ComparisonScorecard:
    return ComparisonScorecard(
        schema=COMPARISON_SCHEMA,
        generated_at_utc=timestamp,
        baseline_name=baseline_name,
        candidate_name=candidate_name,
        outcome="unknown",
        baseline_evidence=baseline_evidence,
        candidate_evidence=candidate_evidence,
        regressions=(),
        unknown_reasons=(reason,),
    )


def _comparison_identity_matches(baseline: EvidenceIdentity, candidate: EvidenceIdentity) -> bool:
    """Only immutable suite, holdout, manifest, and evaluator evidence may differ never."""
    return (
        baseline.trace_schema == candidate.trace_schema
        and baseline.scorecard_schema == candidate.scorecard_schema
        and baseline.evaluator == candidate.evaluator
        and baseline.evaluator_sha256 == candidate.evaluator_sha256
        and baseline.evaluation_manifest_sha256 == candidate.evaluation_manifest_sha256
        and baseline.fixture_manifest_sha256 == candidate.fixture_manifest_sha256
        and baseline.holdout_sha256 == candidate.holdout_sha256
        and baseline.suite_command_sha256 == candidate.suite_command_sha256
    )


def _scores(scorecard: contract.ScorecardArtifact) -> dict[str, tuple[str, float | None]]:
    return {
        dimension.name: (dimension.requirement, dimension.score)
        for dimension in scorecard.score_dimensions
    }


def _append_regression(
    regressions: list[Regression], category: RegressionCategory, subject: str
) -> None:
    regression = Regression(category=category, subject=subject)
    if regression not in regressions:
        regressions.append(regression)


def compare_baseline_to_candidate(
    baseline: BaselineArtifact,
    candidate: CandidateArtifacts,
    candidate_name: str,
    generated_at_utc: str | None = None,
) -> ComparisonScorecard:
    """Compare trusted artifacts, treating incompatible evidence as unknown, never pass."""
    timestamp = generated_at_utc or contract.now_utc()
    if baseline.trace.outcome != "pass" or baseline.scorecard.outcome != "pass":
        return _unknown_scorecard(
            timestamp,
            baseline.name,
            candidate_name,
            "baseline_not_pass",
            baseline.evidence,
            candidate.evidence,
        )
    if not _comparison_identity_matches(baseline.evidence, candidate.evidence):
        return _unknown_scorecard(
            timestamp,
            baseline.name,
            candidate_name,
            "immutable_evidence_mismatch",
            baseline.evidence,
            candidate.evidence,
        )
    if candidate.trace.outcome == "unknown" or candidate.scorecard.outcome == "unknown":
        return _unknown_scorecard(
            timestamp,
            baseline.name,
            candidate_name,
            "candidate_evidence_unknown",
            baseline.evidence,
            candidate.evidence,
        )

    regressions: list[Regression] = []
    baseline_scores = _scores(baseline.scorecard)
    candidate_scores = _scores(candidate.scorecard)
    if baseline_scores.keys() != candidate_scores.keys() or any(
        baseline_scores[name][0] != candidate_scores[name][0]
        for name in baseline_scores.keys() & candidate_scores.keys()
    ):
        _append_regression(regressions, "schema", "score_dimensions")
    else:
        for name, (requirement, baseline_score) in baseline_scores.items():
            candidate_score = candidate_scores[name][1]
            if (
                requirement == "required"
                and baseline_score is not None
                and (candidate_score is None or candidate_score < baseline_score)
            ):
                _append_regression(
                    regressions, "safety" if name == "safety" else "required_score", name
                )

    baseline_suites = {suite.name: suite for suite in baseline.trace.suite_outcomes}
    candidate_suites = {suite.name: suite for suite in candidate.trace.suite_outcomes}
    if baseline_suites.keys() != candidate_suites.keys():
        _append_regression(regressions, "schema", "suite_outcomes")
    else:
        for name in sorted(baseline_suites):
            previous, current = baseline_suites[name], candidate_suites[name]
            if previous.required and previous.status == "pass" and current.status != "pass":
                _append_regression(regressions, "required_suite", name)
            if (
                previous.holdout_case_count
                and previous.status == "pass"
                and current.status != "pass"
            ):
                _append_regression(regressions, "holdout", name)

    if (
        baseline.trace.isolation != candidate.trace.isolation
        or baseline.scorecard.isolation != candidate.scorecard.isolation
    ):
        _append_regression(regressions, "output", "privacy_safe_output")
    if not _artifacts_agree(candidate.trace, candidate.scorecard):
        _append_regression(regressions, "output", "trace_scorecard_consistency")

    return ComparisonScorecard(
        schema=COMPARISON_SCHEMA,
        generated_at_utc=timestamp,
        baseline_name=baseline.name,
        candidate_name=candidate_name,
        outcome="fail" if regressions else "pass",
        baseline_evidence=baseline.evidence,
        candidate_evidence=candidate.evidence,
        regressions=tuple(sorted(regressions, key=lambda item: (item.category, item.subject))),
        unknown_reasons=(),
    )


def compare_files(
    repo_root: Path,
    baseline_path: Path,
    trace_path: Path,
    scorecard_path: Path,
    candidate_name: str,
    output_path: Path,
    generated_at_utc: str | None = None,
) -> ComparisonScorecard:
    """Read local artifacts and always write a normalized comparison scorecard."""
    timestamp = generated_at_utc or contract.now_utc()
    baseline_name = baseline_path.stem
    try:
        baseline = _load_baseline(baseline_path)
        baseline_name = baseline.name
    except (OSError, ValueError, ValidationError, json.JSONDecodeError):
        result = _unknown_scorecard(timestamp, baseline_name, candidate_name, "baseline_malformed")
    else:
        try:
            candidate = _load_candidate_artifacts(repo_root, trace_path, scorecard_path)
        except (OSError, ValueError, ValidationError, json.JSONDecodeError):
            result = _unknown_scorecard(
                timestamp, baseline_name, candidate_name, "candidate_malformed", baseline.evidence
            )
        else:
            result = compare_baseline_to_candidate(baseline, candidate, candidate_name, timestamp)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_output = output_path.parent.resolve(strict=True) / output_path.name
    contract.write_normalized_json(canonical_output, result)
    return result


def _gate_output_dir(repo_root: Path, output_dir: Path) -> Path:
    """Regression gates write artifacts outside candidates, never mutate their checkout."""
    resolved_root = repo_root.resolve(strict=False)
    resolved_output = output_dir.resolve(strict=False)
    temp_roots = (
        Path(tempfile.gettempdir()).resolve(strict=True),
        Path("/tmp").resolve(strict=True),
    )
    if not any(
        resolved_output.is_relative_to(temp_root) for temp_root in temp_roots
    ) or resolved_output.is_relative_to(resolved_root):
        raise ValueError("regression_gate_output_must_be_outside_candidate_under_tmp")
    resolved_output.mkdir(parents=True, exist_ok=True)
    return resolved_output


def run_regression_gate(
    repo_root: Path,
    baseline_path: Path,
    candidate_name: str,
    output_dir: Path,
    generated_at_utc: str | None = None,
) -> ComparisonScorecard:
    """Offline CI/local gate. It evaluates frozen inputs and writes only external artifacts."""
    timestamp = generated_at_utc or contract.now_utc()
    destination = _gate_output_dir(repo_root, output_dir)
    run = contract.evaluate_company_os_contract(repo_root, destination / "candidate", timestamp)
    return compare_files(
        repo_root,
        baseline_path,
        run.trace_path,
        run.scorecard_path,
        candidate_name,
        destination / "comparison-scorecard.json",
        timestamp,
    )


def exit_code_for_outcome(outcome: ComparisonOutcome) -> int:
    return {"pass": 0, "fail": 1, "unknown": 2}[outcome]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare offline Company OS evaluator artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture-baseline")
    capture.add_argument("--repo-root", type=Path, default=Path.cwd())
    capture.add_argument("--output-dir", type=Path, required=True)
    capture.add_argument("--name", required=True)
    capture.add_argument("--timestamp")

    compare = subparsers.add_parser("compare")
    compare.add_argument("--repo-root", type=Path, default=Path.cwd())
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--candidate-trace", type=Path, required=True)
    compare.add_argument("--candidate-scorecard", type=Path, required=True)
    compare.add_argument("--candidate-name", required=True)
    compare.add_argument("--output", type=Path, required=True)
    compare.add_argument("--timestamp")

    gate = subparsers.add_parser("regression-gate")
    gate.add_argument("--repo-root", type=Path, default=Path.cwd())
    gate.add_argument("--baseline", type=Path, required=True)
    gate.add_argument("--candidate-name", required=True)
    gate.add_argument("--output-dir", type=Path, required=True)
    gate.add_argument("--timestamp")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "capture-baseline":
        baseline = capture_baseline(args.repo_root, args.output_dir, args.name, args.timestamp)
        print(
            json.dumps(
                {"baseline": str(args.output_dir / "baseline.json"), "name": baseline.name},
                sort_keys=True,
            )
        )
        return 0
    if args.command == "compare":
        result = compare_files(
            args.repo_root,
            args.baseline,
            args.candidate_trace,
            args.candidate_scorecard,
            args.candidate_name,
            args.output,
            args.timestamp,
        )
    else:
        result = run_regression_gate(
            args.repo_root,
            args.baseline,
            args.candidate_name,
            args.output_dir,
            args.timestamp,
        )
    scorecard_path = (
        args.output if args.command == "compare" else args.output_dir / "comparison-scorecard.json"
    )
    print(
        json.dumps(
            {"outcome": result.outcome, "scorecard": str(scorecard_path)},
            sort_keys=True,
        )
    )
    return exit_code_for_outcome(result.outcome)


if __name__ == "__main__":
    raise SystemExit(main())
