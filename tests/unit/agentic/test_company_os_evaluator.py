"""Unit tests for the repository-owned Company OS evaluator."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from holus.evaluation import company_os_contract as evaluator

if TYPE_CHECKING:
    from collections.abc import Mapping


ROOT = Path(__file__).resolve().parents[3]
FIXED_TS = "2026-08-25T12:00:00Z"


def runner_for(
    exit_codes: Mapping[str, int],
    calls: list[tuple[str, dict[str, str]]] | None = None,
) -> evaluator.SuiteRunner:
    def run(
        suite: evaluator.SuiteConfig,
        _repo_root: Path,
        env: Mapping[str, str],
    ) -> evaluator.SuiteExecution:
        if calls is not None:
            calls.append((suite.name, dict(env)))
        return evaluator.SuiteExecution(exit_code=exit_codes.get(suite.name, 0))

    return run


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_normalized(path: Path) -> None:
    payload = read_json(path)
    assert path.read_text(encoding="utf-8") == json.dumps(payload, indent=2, sort_keys=True) + "\n"


def copy_contract_repo(tmp_path: Path) -> Path:
    sandbox = tmp_path / "repo"
    (sandbox / "tests" / "unit" / "agentic").mkdir(parents=True)
    shutil.copytree(ROOT / ".agents", sandbox / ".agents")
    shutil.copytree(ROOT / "agentic", sandbox / "agentic")
    shutil.copy2(
        ROOT / "tests" / "unit" / "agentic" / "test_company_os_skill_contracts.py",
        sandbox / "tests" / "unit" / "agentic" / "test_company_os_skill_contracts.py",
    )
    shutil.copy2(ROOT / "uv.lock", sandbox / "uv.lock")
    return sandbox


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rewrite_eval_manifest_hash(manifest_path: Path) -> None:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["company_os_contract"]["evals_yaml_sha256"] = evaluator.normalized_eval_manifest_hash(
        manifest
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")


def rewrite_fixture_manifest_and_eval_hashes(sandbox: Path) -> None:
    evals_path = sandbox / "agentic" / "evals.yaml"
    manifest_path = (
        sandbox / "agentic" / "evaluation-fixtures" / "company-os" / "v1" / "manifest.json"
    )
    evals_manifest = yaml.safe_load(evals_path.read_text(encoding="utf-8"))
    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    fixture_manifest["evaluation_manifest_sha256"] = evaluator.normalized_eval_manifest_hash(
        evals_manifest
    )
    for row in fixture_manifest["fixtures"]:
        row["sha256"] = evaluator.sha256_file(sandbox / row["path"])
    fixture_manifest["holdout"]["sha256"] = evaluator.sha256_file(
        sandbox / fixture_manifest["holdout"]["path"]
    )
    write_json(manifest_path, fixture_manifest)

    evals_manifest["company_os_contract"]["fixture_manifest_sha256"] = evaluator.sha256_file(
        manifest_path
    )
    evals_manifest["company_os_contract"]["evals_yaml_sha256"] = (
        evaluator.normalized_eval_manifest_hash(evals_manifest)
    )
    evals_path.write_text(yaml.safe_dump(evals_manifest, sort_keys=True), encoding="utf-8")


def test_company_os_evaluator_writes_deterministic_normalized_artifacts(tmp_path: Path) -> None:
    output_a = tmp_path / "a"
    output_b = tmp_path / "b"

    run_a = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=output_a,
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )
    run_b = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=output_b,
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )

    assert run_a.outcome == "pass"
    assert run_b.outcome == "pass"
    assert run_a.trace_path.read_text(encoding="utf-8") == run_b.trace_path.read_text(
        encoding="utf-8"
    )
    assert run_a.scorecard_path.read_text(encoding="utf-8") == run_b.scorecard_path.read_text(
        encoding="utf-8"
    )
    assert_normalized(run_a.trace_path)
    assert_normalized(run_a.scorecard_path)

    trace = read_json(run_a.trace_path)
    scorecard = read_json(run_a.scorecard_path)
    assert trace["generated_at_utc"] == FIXED_TS
    assert trace["fixture_set"]["id"] == "company-os-v1"
    assert trace["fixture_set"]["manifest_sha256"] == evaluator.EXPECTED_FIXTURE_MANIFEST_SHA256
    assert trace["isolation"]["raw_suite_output_captured"] is False
    assert {suite["name"] for suite in trace["suite_outcomes"]} == set(evaluator.EXPECTED_SUITES)
    assert set(trace["score_dimensions"]) == set(evaluator.EXPECTED_SCORE_DIMENSIONS)
    assert {dimension["name"] for dimension in scorecard["score_dimensions"]} == set(
        evaluator.EXPECTED_SCORE_DIMENSIONS
    )
    assert trace["score_dimensions"] == dict(sorted(evaluator.EXPECTED_SCORE_DIMENSIONS.items()))
    assert [dimension["name"] for dimension in scorecard["score_dimensions"]] == sorted(
        evaluator.EXPECTED_SCORE_DIMENSIONS
    )
    assert all(dimension["score"] == 1.0 for dimension in scorecard["score_dimensions"])
    assert trace["isolation"]["prohibited_boundaries"] == [
        ".self-improvement runtime JSONL",
        "data/content-queue",
        "promotion",
        "publish",
        "schedule",
        "external integrations",
    ]


def test_company_os_evaluator_requires_exact_allowlisted_network_prohibited_suites(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=tmp_path,
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "pass"
    trace = read_json(run.trace_path)
    assert [
        (
            suite["name"],
            suite["command_sha256"],
            suite["network"],
            suite["required"],
            suite["fixture_case_count"],
            suite["fixture_case_ids"],
        )
        for suite in trace["suite_outcomes"]
    ] == [
        (
            "company-os-trigger-and-contract",
            evaluator.sha256_text(
                "uv run pytest tests/unit/agentic/test_company_os_skill_contracts.py -q"
            ),
            "prohibited",
            True,
            2,
            ["brand-positive-trigger", "non-company-skill-negative"],
        ),
        (
            "company-os-hard-safety",
            evaluator.sha256_text(
                "uv run pytest tests/unit/agentic/test_company_os_skill_contracts.py -q"
            ),
            "prohibited",
            True,
            1,
            ["marketing-hard-safety"],
        ),
    ]
    assert [name for name, _env in calls] == [
        "company-os-trigger-and-contract",
        "company-os-hard-safety",
    ]


def test_company_os_evaluator_reports_declared_hashes(tmp_path: Path) -> None:
    run = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=tmp_path,
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )

    trace = read_json(run.trace_path)
    helper = ".agents/skills/_shared/company_os.py"
    assert trace["hashes"]["inputs"][helper] == evaluator.sha256_file(ROOT / helper)
    assert trace["hashes"]["config"]["uv.lock"] == evaluator.sha256_file(ROOT / "uv.lock")
    holdout_path = "agentic/evaluation-fixtures/company-os/v1/holdout/cases.json"
    assert trace["hashes"]["holdout"][holdout_path] == evaluator.sha256_file(
        ROOT / "agentic" / "evaluation-fixtures" / "company-os" / "v1" / "holdout" / "cases.json"
    )
    assert trace["hashes"]["evaluation_manifest_sha256"] == evaluator.sha256_file(
        ROOT / "agentic" / "evals.yaml"
    )


@pytest.mark.parametrize(
    ("relative_path", "expected_reason"),
    [
        (".agents/skills/_shared/company_os.py", "ValueError"),
        ("agentic/tools.yaml", "ValueError"),
    ],
)
def test_company_os_evaluator_returns_unknown_for_altered_frozen_inputs_or_config(
    tmp_path: Path,
    relative_path: str,
    expected_reason: str,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    changed_path = sandbox / relative_path
    changed_path.write_text(changed_path.read_text(encoding="utf-8") + "\n# altered\n")
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []
    assert read_json(run.trace_path)["unknown_reasons"] == [expected_reason]
    hashes = read_json(run.trace_path)["hashes"]
    if relative_path == ".agents/skills/_shared/company_os.py":
        assert hashes["inputs"][relative_path] == evaluator.sha256_file(sandbox / relative_path)
    if relative_path == "agentic/tools.yaml":
        assert hashes["config"][relative_path] == evaluator.sha256_file(sandbox / relative_path)


@pytest.mark.parametrize(
    ("relative_path", "expected_reason"),
    [
        ("agentic/evaluation-fixtures/company-os/v1/cases.json", "ValueError"),
        ("agentic/evaluation-fixtures/company-os/v1/holdout/cases.json", "ValueError"),
    ],
)
def test_company_os_evaluator_returns_unknown_for_altered_fixture_or_holdout(
    tmp_path: Path,
    relative_path: str,
    expected_reason: str,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    changed_path = sandbox / relative_path
    payload = json.loads(changed_path.read_text(encoding="utf-8"))
    payload["altered"] = True
    changed_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []
    assert read_json(run.trace_path)["unknown_reasons"] == [expected_reason]


def test_company_os_evaluator_returns_unknown_for_strict_schema_extra_before_suites(
    tmp_path: Path,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    manifest_path = sandbox / "agentic" / "evals.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["unexpected"] = "not allowed"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []
    assert read_json(run.trace_path)["unknown_reasons"] == ["ValueError"]


@pytest.mark.parametrize(
    ("mutate", "expected_absent"),
    [
        (
            lambda manifest: manifest["company_os_contract"]["config_paths"].append(".env"),
            ".env",
        ),
        (
            lambda manifest: manifest["frozen_inputs"]["source_paths"].append(".env"),
            ".env",
        ),
        (
            lambda manifest: manifest["frozen_inputs"]["source_paths"].append("README.md"),
            "README.md",
        ),
    ],
)
def test_company_os_evaluator_unknown_hashes_only_evaluator_owned_safe_paths(
    tmp_path: Path,
    mutate: Any,
    expected_absent: str,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    (sandbox / ".env").write_text("HOLUS_API_KEY=secret\n", encoding="utf-8")
    (sandbox / "README.md").write_text("not part of frozen inputs\n", encoding="utf-8")
    manifest_path = sandbox / "agentic" / "evals.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    manifest["company_os_contract"]["evals_yaml_sha256"] = evaluator.normalized_eval_manifest_hash(
        manifest
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []
    hashes = read_json(run.trace_path)["hashes"]
    assert expected_absent not in hashes["config"]
    assert expected_absent not in hashes["inputs"]
    assert ".env" not in hashes["fixtures"]
    assert ".env" not in hashes["holdout"]


def test_company_os_evaluator_missing_eval_config_emits_null_unavailable_hash(
    tmp_path: Path,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    (sandbox / "agentic" / "evals.yaml").unlink()

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )

    trace = read_json(run.trace_path)
    assert run.outcome == "unknown"
    assert trace["hashes"]["evaluation_manifest_sha256"] is None
    assert trace["fixture_set"]["manifest_sha256"] is None
    assert "uv.lock" in trace["hashes"]["config"]
    assert evaluator.EXPECTED_PUBLIC_FIXTURE_PATH in trace["hashes"]["fixtures"]


def test_company_os_evaluator_rejects_non_hex_hash_artifact_fields() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        evaluator.HashSet(
            evaluation_manifest_sha256=None,
            config={"uv.lock": "missing"},
            inputs={},
            fixtures={},
            holdout={},
        )


@pytest.mark.parametrize(
    ("relative_path", "replacement", "expected_reason"),
    [
        ("agentic/evals.yaml", "schema: [", "ValueError"),
        ("agentic/evaluation-fixtures/company-os/v1/manifest.json", "{", "ValueError"),
        ("agentic/evaluation-fixtures/company-os/v1/cases.json", "[", "ValueError"),
        ("agentic/evaluation-fixtures/company-os/v1/holdout/cases.json", "[", "ValueError"),
    ],
)
def test_company_os_evaluator_returns_unknown_for_malformed_paths_before_suites(
    tmp_path: Path,
    relative_path: str,
    replacement: str,
    expected_reason: str,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    (sandbox / relative_path).write_text(replacement, encoding="utf-8")
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []
    assert read_json(run.trace_path)["unknown_reasons"] == [expected_reason]


@pytest.mark.parametrize(
    ("relative_path", "expected_reason"),
    [
        ("agentic/evals.yaml", "ValueError"),
        ("agentic/evaluation-fixtures/company-os/v1/manifest.json", "FileNotFoundError"),
        ("agentic/evaluation-fixtures/company-os/v1/cases.json", "FileNotFoundError"),
        ("agentic/evaluation-fixtures/company-os/v1/holdout/cases.json", "FileNotFoundError"),
    ],
)
def test_company_os_evaluator_returns_unknown_for_missing_paths_before_suites(
    tmp_path: Path,
    relative_path: str,
    expected_reason: str,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    (sandbox / relative_path).unlink()
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []
    assert read_json(run.trace_path)["unknown_reasons"] == [expected_reason]


def test_company_os_evaluator_validates_nonempty_holdout_set() -> None:
    holdout = evaluator.HoldoutConfig(
        id="holdout",
        path="agentic/evaluation-fixtures/company-os/v1/holdout/cases.json",
        sha256="a" * 64,
        min_cases=1,
    )

    with pytest.raises(ValueError, match="holdout set"):
        evaluator.validate_holdout_payload(
            {
                "fixture_set_id": "company-os-v1",
                "holdout": [],
                "schema": "holus.company_os_holdout.v1",
            },
            holdout,
            "company-os-v1",
        )


def test_company_os_evaluator_rejects_rehashed_manifest_with_missing_score_dimension(
    tmp_path: Path,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    manifest_path = sandbox / "agentic" / "evals.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    del manifest["default_scores"]["safety"]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
    rewrite_eval_manifest_hash(manifest_path)
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []


def test_company_os_evaluator_rejects_rehashed_manifest_with_privacy_policy_change(
    tmp_path: Path,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    manifest_path = sandbox / "agentic" / "evals.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["frozen_inputs"]["privacy"]["export_only"] = "raw payloads"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
    rewrite_eval_manifest_hash(manifest_path)
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda manifest: manifest["frozen_inputs"]["source_paths"].append("README.md"),
        lambda manifest: manifest["frozen_inputs"]["environment"].update(
            {"python_requires": ">=3.13"}
        ),
        lambda manifest: manifest["company_os_contract"]["config_paths"].append("README.md"),
    ],
)
def test_company_os_evaluator_rejects_rehashed_manifest_declaration_changes(
    tmp_path: Path,
    mutate: Any,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    (sandbox / "README.md").write_text("not part of the v1 contract\n", encoding="utf-8")
    manifest_path = sandbox / "agentic" / "evals.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    manifest["company_os_contract"]["evals_yaml_sha256"] = evaluator.normalized_eval_manifest_hash(
        manifest
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []


def test_company_os_evaluator_rejects_v1_fixture_case_removal_after_pin_update(
    tmp_path: Path,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    cases_path = sandbox / "agentic" / "evaluation-fixtures" / "company-os" / "v1" / "cases.json"
    payload = read_json(cases_path)
    payload["cases"] = [case for case in payload["cases"] if case["id"] != "brand-positive-trigger"]
    write_json(cases_path, payload)
    rewrite_fixture_manifest_and_eval_hashes(sandbox)
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []


def test_company_os_evaluator_rejects_malformed_rehashed_fixture_payload(
    tmp_path: Path,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    cases_path = sandbox / "agentic" / "evaluation-fixtures" / "company-os" / "v1" / "cases.json"
    write_json(
        cases_path,
        {
            "cases": [{"id": "only-id"}],
            "fixture_set_id": "company-os-v1",
            "schema": "wrong.schema",
        },
    )
    rewrite_fixture_manifest_and_eval_hashes(sandbox)
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []
    assert read_json(run.trace_path)["hashes"]["fixtures"][
        "agentic/evaluation-fixtures/company-os/v1/cases.json"
    ] == evaluator.sha256_file(cases_path)


def test_company_os_evaluator_rejects_fixture_set_mismatch_after_rehash(
    tmp_path: Path,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    cases_path = sandbox / "agentic" / "evaluation-fixtures" / "company-os" / "v1" / "cases.json"
    payload = read_json(cases_path)
    payload["fixture_set_id"] = "other-fixture-set"
    write_json(cases_path, payload)
    rewrite_fixture_manifest_and_eval_hashes(sandbox)

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )

    assert run.outcome == "unknown"


def test_company_os_evaluator_rejects_symlinked_declared_input(
    tmp_path: Path,
) -> None:
    sandbox = copy_contract_repo(tmp_path)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    target = sandbox / "agentic" / "tools.yaml"
    target.unlink()
    target.symlink_to(outside)
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        sandbox,
        output_dir=tmp_path / "artifacts",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "unknown"
    assert calls == []
    assert "agentic/tools.yaml" not in read_json(run.trace_path)["hashes"]["config"]


def test_company_os_evaluator_rejects_runtime_and_repo_output_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repository output"):
        evaluator.evaluate_company_os_contract(
            ROOT,
            output_dir=ROOT / "data" / "runtime",
            generated_at_utc=FIXED_TS,
            suite_runner=runner_for({}),
        )

    with pytest.raises(ValueError, match=r"runtime path|repository output"):
        evaluator.evaluate_company_os_contract(
            ROOT,
            output_dir=Path("data/runtime"),
            generated_at_utc=FIXED_TS,
            suite_runner=runner_for({}),
        )


def test_company_os_evaluator_rejects_symlinked_output_file(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    (output_dir / "trace.json").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        evaluator.evaluate_company_os_contract(
            ROOT,
            output_dir=output_dir,
            generated_at_utc=FIXED_TS,
            suite_runner=runner_for({}),
        )


def test_company_os_evaluator_outcome_and_exit_semantics(tmp_path: Path) -> None:
    pass_run = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=tmp_path / "pass",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )
    fail_run = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=tmp_path / "fail",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({"company-os-hard-safety": 1}),
    )
    unknown_run = evaluator.evaluate_company_os_contract(
        tmp_path / "missing",
        output_dir=tmp_path / "unknown",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )

    assert (pass_run.outcome, evaluator.exit_code_for_outcome(pass_run.outcome)) == ("pass", 0)
    assert (fail_run.outcome, evaluator.exit_code_for_outcome(fail_run.outcome)) == ("fail", 1)
    assert (unknown_run.outcome, evaluator.exit_code_for_outcome(unknown_run.outcome)) == (
        "unknown",
        2,
    )


@pytest.mark.parametrize(
    ("outcome", "expected_exit"),
    [("pass", 0), ("fail", 1), ("unknown", 2)],
)
def test_company_os_evaluator_cli_main_returns_outcome_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: evaluator.Outcome,
    expected_exit: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_evaluate_company_os_contract(**_kwargs: Any) -> Any:
        return SimpleNamespace(
            outcome=outcome,
            trace_path=tmp_path / "trace.json",
            scorecard_path=tmp_path / "scorecard.json",
        )

    monkeypatch.setattr(
        evaluator, "evaluate_company_os_contract", fake_evaluate_company_os_contract
    )

    assert (
        evaluator.main(["--repo-root", str(ROOT), "--output-dir", str(tmp_path)]) == expected_exit
    )
    assert json.loads(capsys.readouterr().out)["outcome"] == outcome


def test_company_os_evaluator_scrubs_environment_and_blocks_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOLUS_API_KEY", "secret")
    monkeypatch.setenv("COMPANY_SECRET_TOKEN", "secret")
    calls: list[tuple[str, dict[str, str]]] = []

    run = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=tmp_path,
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}, calls),
    )

    assert run.outcome == "pass"
    assert calls
    env = calls[0][1]
    assert "HOLUS_API_KEY" not in env
    assert "COMPANY_SECRET_TOKEN" not in env
    assert env["UV_OFFLINE"] == "1"
    assert env["PIP_NO_INDEX"] == "1"
    assert env["DRY_RUN"] == "1"
    assert env["USER"] == "company-os-evaluator"
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONSAFEPATH"] == "1"
    assert env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert env["PATH"] == "/usr/bin:/bin"
    assert env["HOME"] != str(Path.home())

    guard_dir = tmp_path / "guard"
    isolated_home = tmp_path / "home"
    isolated_tmp = tmp_path / "tmp"
    guard_dir.mkdir()
    isolated_home.mkdir()
    isolated_tmp.mkdir()
    evaluator.create_network_guard(guard_dir)
    live_env = evaluator.build_suite_environment(ROOT, guard_dir, isolated_home, isolated_tmp)

    check = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "import socket",
                    "for call in (lambda: socket.getaddrinfo('localhost', 80),",
                    "             lambda: socket.gethostbyname('localhost'),",
                    "             lambda: socket.create_connection(('127.0.0.1', 9), timeout=0.01),",
                    "             lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'x', ('127.0.0.1', 9))):",
                    "    try:",
                    "        call()",
                    "    except Exception:",
                    "        continue",
                    "    raise SystemExit('network call was allowed')",
                ]
            ),
        ],
        env=live_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0, check.stderr

    private_socket_check = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "import _socket",
                    "import sitecustomize",
                    "checks = (",
                    "    ('getaddrinfo', lambda: _socket.getaddrinfo('localhost', 80)),",
                    "    ('gethostbyname', lambda: _socket.gethostbyname('localhost')),",
                    "    ('socket_connect', lambda: _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM).connect(('127.0.0.1', 9))),",
                    "    ('socket_sendto', lambda: _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM).sendto(b'x', ('127.0.0.1', 9))),",
                    ")",
                    "for name, call in checks:",
                    "    try:",
                    "        call()",
                    "    except sitecustomize.CompanyOSEvaluationNetworkBlocked:",
                    "        continue",
                    "    except Exception as exc:",
                    "        raise SystemExit(f'{name} raised {type(exc).__name__}') from exc",
                    "    raise SystemExit(f'{name} was allowed')",
                ]
            ),
        ],
        env=live_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert private_socket_check.returncode == 0, private_socket_check.stderr

    child_check = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, subprocess; os.system('true'); subprocess.run(['true'])",
        ],
        env=live_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert child_check.returncode != 0

    ctypes_child_check = subprocess.run(
        [
            sys.executable,
            "-c",
            "import ctypes; ctypes.CDLL(None).system(b'true')",
        ],
        env=live_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ctypes_child_check.returncode != 0
    assert "CompanyOSEvaluationSubprocessBlocked" in ctypes_child_check.stderr


def test_company_os_evaluator_executes_suite_with_trusted_python_interpreter() -> None:
    suite = evaluator.SuiteConfig(
        name="company-os-trigger-and-contract",
        command="uv run pytest tests/unit/agentic/test_company_os_skill_contracts.py -q",
        inputs=".agents/skills/company-*/evals/evals.json",
        network="prohibited",
        required=True,
    )

    assert evaluator.pytest_argv_for_suite(suite) == [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/agentic/test_company_os_skill_contracts.py",
        "-q",
    ]


def test_company_os_evaluator_allows_repo_internal_eval_artifact_output(
    tmp_path: Path,
) -> None:
    run = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=Path(".eval-artifacts") / "company-os-contract-test",
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )

    assert run.outcome == "pass"
    assert run.trace_path.is_relative_to(ROOT / ".eval-artifacts")
    run.trace_path.unlink()
    run.scorecard_path.unlink()
    run.trace_path.parent.rmdir()


def test_company_os_evaluator_cli_actual_offline_pass(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "holus.evaluation.company_os_contract",
            "--repo-root",
            str(ROOT),
            "--timestamp",
            FIXED_TS,
            "--output-dir",
            str(tmp_path / "cli-artifacts"),
        ],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["outcome"] == "pass"


def test_company_os_evaluator_does_not_read_runtime_or_publish_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_open = Path.open

    def guarded_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        normalized = self.as_posix()
        prohibited = (
            ".self-improvement",
            "data/content-queue",
            "data/lineage",
            "data/runtime",
        )
        assert not any(value in normalized for value in prohibited), normalized
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    run = evaluator.evaluate_company_os_contract(
        ROOT,
        output_dir=tmp_path,
        generated_at_utc=FIXED_TS,
        suite_runner=runner_for({}),
    )

    assert run.outcome == "pass"
    assert read_json(run.trace_path)["isolation"]["prohibited_boundaries"] == [
        ".self-improvement runtime JSONL",
        "data/content-queue",
        "promotion",
        "publish",
        "schedule",
        "external integrations",
    ]
