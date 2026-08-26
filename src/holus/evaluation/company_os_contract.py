"""Deterministic offline evaluator for the Holus Company OS contract."""

from __future__ import annotations

import argparse
import copy
import errno
import hashlib
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

TRACE_SCHEMA: Literal["holus.company_os_contract.trace.v1"] = "holus.company_os_contract.trace.v1"
SCORECARD_SCHEMA: Literal["holus.company_os_contract.scorecard.v1"] = (
    "holus.company_os_contract.scorecard.v1"
)
EXPECTED_EVAL_SCHEMA = "fleet.repo_evals.v1"
EXPECTED_REPO: Literal["holus"] = "holus"
EXPECTED_SUITES = {
    "company-os-trigger-and-contract": "uv run pytest tests/unit/agentic/test_company_os_skill_contracts.py -q",
    "company-os-hard-safety": "uv run pytest tests/unit/agentic/test_company_os_skill_contracts.py -q",
}
EXPECTED_SUITE_INPUTS = {
    "company-os-trigger-and-contract": ".agents/skills/company-*/evals/evals.json",
    "company-os-hard-safety": ".agents/skills/_shared/company_os.py",
}
EXPECTED_SCORE_DIMENSIONS = {
    "cost_efficiency": "optional",
    "domain_score": "repo_defined",
    "safety": "required",
    "task_completion": "required",
    "tool_accuracy": "required",
    "trajectory_quality": "required",
}
EXPECTED_SCORECARD_SCHEMA = "fleet.eval_scorecard.v1"
EXPECTED_GATE_DECISIONS = ("pass", "fail", "hold")
EXPECTED_PRIVACY_POLICY = {
    "export_only": "hashes, scorecards, and non-sensitive summaries",
    "never_export": "credentials, raw content drafts, queue contents, or runtime JSONL rows",
}
DEFAULT_OUTPUT_DIR = Path(".eval-artifacts") / "company-os-contract"
EVAL_MANIFEST_PATH = Path("agentic") / "evals.yaml"
EXPECTED_EVAL_NORMALIZED_SHA256 = "0660fc9db5ba257f9893610e21b34c44988f5aba2eb909f4b001c87cbc29ec23"
EXPECTED_FIXTURE_SET_ID = "company-os-v1"
EXPECTED_FIXTURE_SET_VERSION = "v1"
EXPECTED_FIXTURE_MANIFEST_PATH = "agentic/evaluation-fixtures/company-os/v1/manifest.json"
EXPECTED_FIXTURE_MANIFEST_SHA256 = (
    "bf9656aa5d1568d7a1e7e378a5a1c6a1ff275e63150f3851e98582c85ad20022"
)
EXPECTED_CONFIG_PATHS = (
    "agentic/manifest.yaml",
    "agentic/permissions.yaml",
    "agentic/tools.yaml",
    "agentic/memory.yaml",
    "uv.lock",
)
EXPECTED_FROZEN_SOURCE_PATTERNS = (
    ".agents/skills/_shared/company_os.py",
    ".agents/skills/company-*/SKILL.md",
    ".agents/skills/company-*/references/output-contract.md",
    ".agents/skills/company-*/evals/evals.json",
    "tests/unit/agentic/test_company_os_skill_contracts.py",
)
EXPECTED_FROZEN_ENVIRONMENT = {
    "python_requires": ">=3.12",
    "dependency_lock": "uv.lock",
}
EXPECTED_EXPORT = {
    "event_stream": ".self-improvement/hub/skill_runs.jsonl",
    "trace_dir": ".self-improvement/traces/",
    "summary_only": True,
}
EXPECTED_PUBLIC_FIXTURE_PATH = "agentic/evaluation-fixtures/company-os/v1/cases.json"
EXPECTED_PUBLIC_FIXTURE_SHA256 = "050188fb7d32455a640ac48b5375b896229cfa88ec76a794e8ae303f8d0f9f51"
EXPECTED_HOLDOUT_PATH = "agentic/evaluation-fixtures/company-os/v1/holdout/cases.json"
EXPECTED_HOLDOUT_SHA256 = "b7ff1e7a444bbdfbd8ce4c913ea702b4a39163f06e36900b960fd1b69e219762"
EXPECTED_HOLDOUT_MIN_CASES = 1
EXPECTED_PUBLIC_CASE_SUITES = {
    "brand-positive-trigger": ("company-os-trigger-and-contract",),
    "marketing-hard-safety": ("company-os-hard-safety",),
    "non-company-skill-negative": ("company-os-trigger-and-contract",),
}
EXPECTED_HOLDOUT_CASE_SUITES = {
    "supervisor-publish-approval-boundary": ("company-os-hard-safety",),
}
PROHIBITED_PATH_PREFIXES = (
    ".self-improvement",
    "data/content-queue",
    "data/lineage",
    "data/runtime",
)
SENSITIVE_ENV_MARKERS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "CREDENTIAL",
    "COOKIE",
    "AUTH",
)
OFFLINE_ENV = {
    "COMPANY_OS_EVALUATION": "1",
    "DRY_RUN": "1",
    "NO_PROXY": "*",
    "PIP_NO_INDEX": "1",
    "UV_OFFLINE": "1",
}
SCORE_BY_OUTCOME: dict[str, float | None] = {"pass": 1.0, "fail": 0.0, "unknown": None}
SHA256_LENGTH = 64


Outcome = Literal["pass", "fail", "unknown"]
SuiteStatus = Literal["pass", "fail", "unknown"]


class StrictModel(BaseModel):
    """Pydantic base for immutable, extra-forbid contract models."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def validate_sha256_value(value: str) -> str:
    if len(value) != SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("value must be a lowercase SHA-256 hex digest")
    return value


def validate_optional_sha256_value(value: str | None) -> str | None:
    if value is None:
        return value
    return validate_sha256_value(value)


def validate_sha256_hash_map(value: dict[str, str]) -> dict[str, str]:
    for digest in value.values():
        validate_sha256_value(digest)
    return value


def validate_utc_timestamp_value(value: str) -> str:
    if not value.endswith("Z"):
        raise ValueError("timestamp must be UTC with Z suffix")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601 UTC") from exc
    if parsed.tzinfo != UTC:
        raise ValueError("timestamp must be UTC")
    return value


class FrozenInputsConfig(StrictModel):
    source_paths: tuple[str, ...]
    environment: dict[str, str]
    privacy: dict[str, str]


class SuiteConfig(StrictModel):
    name: str
    command: str
    inputs: str
    network: Literal["prohibited"]
    required: bool


class CompanyOSContractConfig(StrictModel):
    schema_id: Literal["holus.company_os_contract_config.v1"] = Field(alias="schema")
    fixture_manifest: str
    fixture_manifest_sha256: str
    config_paths: tuple[str, ...]
    evals_yaml_sha256: str

    _fixture_manifest_sha256 = field_validator("fixture_manifest_sha256")(validate_sha256_value)
    _evals_yaml_sha256 = field_validator("evals_yaml_sha256")(validate_sha256_value)


class EvalManifestConfig(StrictModel):
    schema_id: Literal["fleet.repo_evals.v1"] = Field(alias="schema")
    repo: Literal["holus"]
    scorecard_schema: str
    default_scores: dict[str, str]
    gate_decisions: list[str]
    frozen_inputs: FrozenInputsConfig
    suites: tuple[SuiteConfig, ...]
    export: dict[str, Any]
    company_os_contract: CompanyOSContractConfig


class FixtureFileConfig(StrictModel):
    id: str
    path: str
    sha256: str

    _sha256 = field_validator("sha256")(validate_sha256_value)


class HoldoutConfig(StrictModel):
    id: str
    path: str
    sha256: str
    min_cases: int = Field(ge=1)

    _sha256 = field_validator("sha256")(validate_sha256_value)


class FixtureManifestConfig(StrictModel):
    schema_id: Literal["holus.company_os_fixture_manifest.v1"] = Field(alias="schema")
    fixture_set_id: str
    version: str
    immutable: bool
    created_at_utc: str
    evaluation_manifest_sha256: str
    config_files: tuple[FixtureFileConfig, ...]
    frozen_inputs: tuple[FixtureFileConfig, ...]
    fixtures: tuple[FixtureFileConfig, ...]
    holdout: HoldoutConfig

    _created_at_utc = field_validator("created_at_utc")(validate_utc_timestamp_value)
    _evaluation_manifest_sha256 = field_validator("evaluation_manifest_sha256")(
        validate_sha256_value
    )


class PublicFixtureExpected(StrictModel):
    should_trigger: bool
    mode: Literal["defense", "hard_safety_gate"] | None = None


class PublicFixtureCase(StrictModel):
    id: str
    query: str
    skill: str
    suites: tuple[str, ...]
    expected: PublicFixtureExpected

    @field_validator("suites")
    @classmethod
    def suites_must_be_nonempty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("case must declare at least one suite")
        return value


class PublicFixturePayload(StrictModel):
    schema_id: Literal["holus.company_os_eval_cases.v1"] = Field(alias="schema")
    fixture_set_id: str
    cases: tuple[PublicFixtureCase, ...]


class HoldoutExpected(StrictModel):
    approval_boundary: Literal["human_ic_required"]
    mutates_external_system: Literal[False]


class HoldoutCase(StrictModel):
    id: str
    query: str
    suites: tuple[str, ...]
    expected: HoldoutExpected

    @field_validator("suites")
    @classmethod
    def suites_must_be_nonempty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("holdout case must declare at least one suite")
        return value


class HoldoutPayload(StrictModel):
    schema_id: Literal["holus.company_os_holdout.v1"] = Field(alias="schema")
    fixture_set_id: str
    holdout: tuple[HoldoutCase, ...]


class FixtureSetIdentity(StrictModel):
    id: str
    version: str
    manifest_path: str
    manifest_sha256: str | None

    _manifest_sha256 = field_validator("manifest_sha256")(validate_optional_sha256_value)


class HashSet(StrictModel):
    evaluation_manifest_sha256: str | None
    config: dict[str, str]
    inputs: dict[str, str]
    fixtures: dict[str, str]
    holdout: dict[str, str]

    _evaluation_manifest_sha256 = field_validator("evaluation_manifest_sha256")(
        validate_optional_sha256_value
    )
    _hash_maps = field_validator("config", "inputs", "fixtures", "holdout")(
        validate_sha256_hash_map
    )


class SuiteOutcome(StrictModel):
    name: str
    command_sha256: str
    inputs: str
    network: Literal["prohibited"]
    required: bool
    status: SuiteStatus
    exit_code: int | None
    error_code: str | None
    fixture_case_ids: tuple[str, ...]
    fixture_case_count: int
    holdout_case_ids: tuple[str, ...]
    holdout_case_count: int


class IsolationSummary(StrictModel):
    network: Literal["prohibited"]
    environment: Literal["scrubbed"]
    raw_suite_output_captured: Literal[False]
    prohibited_boundaries: tuple[str, ...]
    privacy_policy: dict[str, str]


class TraceArtifact(StrictModel):
    schema_id: Literal["holus.company_os_contract.trace.v1"] = Field(alias="schema")
    generated_at_utc: str
    repo: Literal["holus"]
    evaluator: Literal["company-os-contract"]
    outcome: Outcome
    fixture_set: FixtureSetIdentity
    hashes: HashSet
    score_dimensions: dict[str, str]
    suite_outcomes: tuple[SuiteOutcome, ...]
    isolation: IsolationSummary
    unknown_reasons: tuple[str, ...]

    @field_validator("generated_at_utc")
    @classmethod
    def generated_at_must_be_utc(cls, value: str) -> str:
        return validate_utc_timestamp_value(value)


class ScoreDimension(StrictModel):
    name: str
    requirement: str
    score: float | None


class ScorecardArtifact(StrictModel):
    schema_id: Literal["holus.company_os_contract.scorecard.v1"] = Field(alias="schema")
    generated_at_utc: str
    repo: Literal["holus"]
    evaluator: Literal["company-os-contract"]
    outcome: Outcome
    fixture_set: FixtureSetIdentity
    hashes: HashSet
    score_dimensions: tuple[ScoreDimension, ...]
    suite_outcomes: tuple[SuiteOutcome, ...]
    isolation: IsolationSummary
    unknown_reasons: tuple[str, ...]

    @field_validator("generated_at_utc")
    @classmethod
    def generated_at_must_be_utc(cls, value: str) -> str:
        return validate_utc_timestamp_value(value)


@dataclass(frozen=True)
class SuiteExecution:
    exit_code: int | None
    error_code: str | None = None


SuiteRunner = Callable[[SuiteConfig, Path, Mapping[str, str]], SuiteExecution]


@dataclass(frozen=True)
class EvaluationRun:
    outcome: Outcome
    trace_path: Path
    scorecard_path: Path
    trace: TraceArtifact
    scorecard: ScorecardArtifact


@dataclass(frozen=True)
class FixtureValidation:
    fixture_hashes: dict[str, str]
    holdout_hashes: dict[str, str]
    suite_fixture_case_ids: dict[str, tuple[str, ...]]
    suite_holdout_case_ids: dict[str, tuple[str, ...]]


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_no_follow_primitives() -> None:
    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise RuntimeError("fd-based no-follow file primitives are unavailable")


def directory_open_flags() -> int:
    return os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW


def open_no_follow_directory_fd(path: Path) -> int:
    require_no_follow_primitives()
    if not path.is_absolute():
        raise ValueError(f"directory path must be absolute: {path}")
    root = Path(path.anchor)
    root_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    directory_fds = [root_fd]
    try:
        current_fd = root_fd
        for component in path.parts[1:]:
            next_fd = os.open(component, directory_open_flags(), dir_fd=current_fd)
            mode = os.fstat(next_fd).st_mode
            if not stat.S_ISDIR(mode):
                os.close(next_fd)
                raise ValueError(f"path component is not a directory: {path}")
            directory_fds.append(next_fd)
            current_fd = next_fd
        keep_fd = directory_fds.pop()
        return keep_fd
    finally:
        for fd in reversed(directory_fds):
            os.close(fd)


def open_repo_file_descriptor(repo_root: Path, value: str | Path) -> tuple[Path, int]:
    require_no_follow_primitives()
    rel_path = ensure_allowed_repo_path(value)
    if not rel_path.parts:
        raise ValueError("repository file path is empty")
    root_fd = os.open(repo_root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    directory_fds = [root_fd]
    file_fd: int | None = None
    success = False
    try:
        current_fd = root_fd
        for component in rel_path.parts[:-1]:
            next_fd = os.open(component, directory_open_flags(), dir_fd=current_fd)
            mode = os.fstat(next_fd).st_mode
            if not stat.S_ISDIR(mode):
                os.close(next_fd)
                raise ValueError(f"path component is not a directory: {rel_path.as_posix()}")
            directory_fds.append(next_fd)
            current_fd = next_fd
        file_fd = os.open(rel_path.parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current_fd)
        mode = os.fstat(file_fd).st_mode
        if not stat.S_ISREG(mode):
            os.close(file_fd)
            file_fd = None
            raise FileNotFoundError(rel_path.as_posix())
        success = True
        return rel_path, file_fd
    finally:
        for fd in reversed(directory_fds):
            os.close(fd)
        if file_fd is not None and not success:
            os.close(file_fd)


def read_fd_bytes(fd: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def read_repo_bytes(repo_root: Path, value: str | Path) -> bytes:
    _rel_path, fd = open_repo_file_descriptor(repo_root, value)
    try:
        return read_fd_bytes(fd)
    finally:
        os.close(fd)


def normalized_json(payload: BaseModel) -> str:
    return (
        json.dumps(payload.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True) + "\n"
    )


def write_normalized_json(path: Path, payload: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parent_fd = open_no_follow_directory_fd(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(path.name, flags, 0o600, dir_fd=parent_fd)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(f"artifact path is not a regular file: {path}")
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EMLINK}:
            raise ValueError(f"refusing to write symlinked artifact path: {path}") from exc
        raise
    except Exception:
        if fd is not None:
            os.close(fd)
            fd = None
        raise
    finally:
        os.close(parent_fd)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            handle.write(normalized_json(payload))
    finally:
        if fd is not None:
            os.close(fd)


def relative_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"path must stay inside repository: {value}")
    return path


def ensure_allowed_repo_path(value: str | Path) -> Path:
    path = relative_path(value)
    normalized = path.as_posix()
    if any(
        normalized == prefix or normalized.startswith(f"{prefix}/")
        for prefix in PROHIBITED_PATH_PREFIXES
    ):
        raise ValueError(f"runtime path is prohibited for evaluation inputs: {normalized}")
    return path


def reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor) if path.is_absolute() else Path()
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink path components are prohibited: {path}")


def require_repo_file(repo_root: Path, value: str | Path) -> tuple[Path, Path]:
    rel_path = ensure_allowed_repo_path(value)
    _verified_rel_path, fd = open_repo_file_descriptor(repo_root, rel_path)
    os.close(fd)
    return rel_path, repo_root / rel_path


def read_repo_text(repo_root: Path, value: str | Path) -> str:
    return read_repo_bytes(repo_root, value).decode("utf-8")


def sha256_repo_file(repo_root: Path, value: str | Path) -> str:
    return sha256_bytes(read_repo_bytes(repo_root, value))


def resolve_declared_files(repo_root: Path, patterns: Sequence[str]) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for pattern in patterns:
        ensure_allowed_repo_path(pattern)
        matches = sorted(path for path in repo_root.glob(pattern) if path.is_file())
        if not matches:
            raise FileNotFoundError(f"declared input did not match any files: {pattern}")
        for path in matches:
            rel_path = path.relative_to(repo_root).as_posix()
            _safe_rel_path, safe_path = require_repo_file(repo_root, rel_path)
            resolved[rel_path] = safe_path
    return resolved


def hash_declared_files(repo_root: Path, patterns: Sequence[str]) -> dict[str, str]:
    return {
        rel_path: sha256_repo_file(repo_root, rel_path)
        for rel_path in resolve_declared_files(repo_root, patterns)
    }


def load_yaml_mapping_from_repo(repo_root: Path, value: str | Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(read_repo_text(repo_root, value))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"malformed or unreadable YAML: {value}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {value}")
    return payload


def normalized_eval_manifest_hash(manifest_data: Mapping[str, Any]) -> str:
    clone = copy.deepcopy(dict(manifest_data))
    contract = clone.get("company_os_contract")
    if isinstance(contract, dict):
        contract["evals_yaml_sha256"] = ""
        contract["fixture_manifest_sha256"] = ""
    return sha256_text(json.dumps(clone, sort_keys=True, separators=(",", ":"), default=str))


def load_eval_manifest(repo_root: Path) -> tuple[EvalManifestConfig, dict[str, Any], str]:
    manifest_data = load_yaml_mapping_from_repo(repo_root, EVAL_MANIFEST_PATH)
    try:
        manifest = EvalManifestConfig.model_validate(manifest_data)
    except ValidationError as exc:
        raise ValueError(
            "agentic/evals.yaml does not match the Company OS evaluator contract"
        ) from exc
    actual_hash = normalized_eval_manifest_hash(manifest_data)
    if manifest.company_os_contract.evals_yaml_sha256 != actual_hash:
        raise ValueError("agentic/evals.yaml hash does not match the pinned evaluator config hash")
    return manifest, manifest_data, sha256_repo_file(repo_root, EVAL_MANIFEST_PATH)


def validate_manifest_contract(manifest: EvalManifestConfig) -> None:
    if manifest.scorecard_schema != EXPECTED_SCORECARD_SCHEMA:
        raise ValueError("scorecard schema does not match the Company OS contract")
    if dict(manifest.default_scores) != EXPECTED_SCORE_DIMENSIONS:
        raise ValueError("default score dimensions do not match the Company OS contract")
    if tuple(manifest.gate_decisions) != EXPECTED_GATE_DECISIONS:
        raise ValueError("gate decisions do not match the Company OS contract")
    if tuple(manifest.frozen_inputs.source_paths) != EXPECTED_FROZEN_SOURCE_PATTERNS:
        raise ValueError("frozen source paths do not match the Company OS contract")
    if dict(manifest.frozen_inputs.environment) != EXPECTED_FROZEN_ENVIRONMENT:
        raise ValueError("frozen environment does not match the Company OS contract")
    if manifest.frozen_inputs.privacy != EXPECTED_PRIVACY_POLICY:
        raise ValueError("privacy policy does not match the Company OS contract")
    if dict(manifest.export) != EXPECTED_EXPORT:
        raise ValueError("export declarations do not match the Company OS contract")
    contract = manifest.company_os_contract
    if contract.fixture_manifest != EXPECTED_FIXTURE_MANIFEST_PATH:
        raise ValueError("fixture manifest path does not match the Company OS contract")
    if contract.fixture_manifest_sha256 != EXPECTED_FIXTURE_MANIFEST_SHA256:
        raise ValueError("fixture manifest SHA-256 does not match the immutable v1 pin")
    if tuple(contract.config_paths) != EXPECTED_CONFIG_PATHS:
        raise ValueError("config paths do not match the Company OS contract")
    if contract.evals_yaml_sha256 != EXPECTED_EVAL_NORMALIZED_SHA256:
        raise ValueError("eval manifest SHA-256 does not match the immutable v1 pin")
    validate_declared_suites(manifest.suites)


def validate_declared_suites(suites: Sequence[SuiteConfig]) -> None:
    if len(suites) != len(EXPECTED_SUITES):
        raise ValueError("Company OS evaluator requires exactly the two declared suites")
    for suite in suites:
        expected_command = EXPECTED_SUITES.get(suite.name)
        if expected_command is None:
            raise ValueError(f"unexpected Company OS suite: {suite.name}")
        if suite.command != expected_command:
            raise ValueError(f"unexpected command for suite: {suite.name}")
        if suite.inputs != EXPECTED_SUITE_INPUTS[suite.name]:
            raise ValueError(f"unexpected inputs for suite: {suite.name}")
        if suite.network != "prohibited":
            raise ValueError(f"network must be prohibited for suite: {suite.name}")
        if not suite.required:
            raise ValueError(f"Company OS suite must be required: {suite.name}")


def load_fixture_manifest(
    repo_root: Path,
    manifest: EvalManifestConfig,
    normalized_manifest_hash: str,
) -> FixtureManifestConfig:
    fixture_manifest_path = ensure_allowed_repo_path(EXPECTED_FIXTURE_MANIFEST_PATH)
    if sha256_repo_file(repo_root, fixture_manifest_path) != EXPECTED_FIXTURE_MANIFEST_SHA256:
        raise ValueError("fixture manifest hash does not match agentic/evals.yaml")
    payload = load_json_mapping_from_repo(repo_root, fixture_manifest_path)
    fixture_manifest = FixtureManifestConfig.model_validate(payload)
    validate_fixture_manifest_contract(fixture_manifest, normalized_manifest_hash)
    return fixture_manifest


def validate_fixture_manifest_contract(
    fixture_manifest: FixtureManifestConfig,
    normalized_manifest_hash: str,
) -> None:
    if fixture_manifest.fixture_set_id != EXPECTED_FIXTURE_SET_ID:
        raise ValueError("fixture set id does not match immutable v1")
    if fixture_manifest.version != EXPECTED_FIXTURE_SET_VERSION:
        raise ValueError("fixture set version does not match immutable v1")
    if not fixture_manifest.immutable:
        raise ValueError("fixture manifest must be immutable")
    if fixture_manifest.evaluation_manifest_sha256 != EXPECTED_EVAL_NORMALIZED_SHA256:
        raise ValueError("fixture manifest does not pin the immutable v1 eval manifest")
    if fixture_manifest.evaluation_manifest_sha256 != normalized_manifest_hash:
        raise ValueError("fixture manifest does not pin the current evaluation manifest")
    if len(fixture_manifest.fixtures) != 1:
        raise ValueError("immutable v1 requires exactly one public fixture file")
    fixture = fixture_manifest.fixtures[0]
    if fixture.path != EXPECTED_PUBLIC_FIXTURE_PATH:
        raise ValueError("public fixture path does not match immutable v1")
    if fixture.sha256 != EXPECTED_PUBLIC_FIXTURE_SHA256:
        raise ValueError("public fixture SHA-256 does not match immutable v1")
    if fixture_manifest.holdout.path != EXPECTED_HOLDOUT_PATH:
        raise ValueError("holdout path does not match immutable v1")
    if fixture_manifest.holdout.sha256 != EXPECTED_HOLDOUT_SHA256:
        raise ValueError("holdout SHA-256 does not match immutable v1")
    if fixture_manifest.holdout.min_cases != EXPECTED_HOLDOUT_MIN_CASES:
        raise ValueError("holdout min_cases does not match immutable v1")


def load_json_mapping_from_repo(repo_root: Path, value: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(read_repo_text(repo_root, value))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"malformed or unreadable JSON: {value}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be a mapping: {value}")
    return payload


def validate_holdout_payload(
    payload: Mapping[str, Any],
    holdout: HoldoutConfig,
    fixture_set_id: str | None = None,
) -> HoldoutPayload:
    try:
        holdout_payload = HoldoutPayload.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("holdout set does not match the Company OS contract") from exc
    if fixture_set_id is not None and holdout_payload.fixture_set_id != fixture_set_id:
        raise ValueError("holdout fixture_set_id does not match fixture manifest")
    if len(holdout_payload.holdout) < holdout.min_cases:
        raise ValueError("holdout set must be nonempty and meet min_cases")
    return holdout_payload


def validate_fixtures(
    repo_root: Path, fixture_manifest: FixtureManifestConfig
) -> FixtureValidation:
    fixture_hashes: dict[str, str] = {}
    suite_fixture_case_ids: dict[str, list[str]] = {name: [] for name in EXPECTED_SUITES}
    suite_holdout_case_ids: dict[str, list[str]] = {name: [] for name in EXPECTED_SUITES}
    fixture_case_ids: set[str] = set()
    for fixture in fixture_manifest.fixtures:
        rel_path = ensure_allowed_repo_path(fixture.path)
        actual_hash = sha256_repo_file(repo_root, rel_path)
        if actual_hash != fixture.sha256:
            raise ValueError(f"fixture hash mismatch: {fixture.path}")
        try:
            payload = PublicFixturePayload.model_validate(
                load_json_mapping_from_repo(repo_root, rel_path)
            )
        except ValidationError as exc:
            raise ValueError(f"fixture payload does not match contract: {fixture.path}") from exc
        if payload.fixture_set_id != fixture_manifest.fixture_set_id:
            raise ValueError(f"fixture_set_id mismatch: {fixture.path}")
        case_suites = {public_case.id: tuple(public_case.suites) for public_case in payload.cases}
        if case_suites != EXPECTED_PUBLIC_CASE_SUITES:
            raise ValueError("public fixture case ids or suite associations changed under v1")
        for public_case in payload.cases:
            if public_case.id in fixture_case_ids:
                raise ValueError(f"duplicate fixture case id: {public_case.id}")
            fixture_case_ids.add(public_case.id)
            for suite_name in public_case.suites:
                if suite_name not in EXPECTED_SUITES:
                    raise ValueError(f"unexpected fixture suite association: {suite_name}")
                suite_fixture_case_ids[suite_name].append(public_case.id)
        fixture_hashes[rel_path.as_posix()] = actual_hash

    holdout_path = ensure_allowed_repo_path(fixture_manifest.holdout.path)
    actual_holdout_hash = sha256_repo_file(repo_root, holdout_path)
    if actual_holdout_hash != fixture_manifest.holdout.sha256:
        raise ValueError(f"holdout hash mismatch: {fixture_manifest.holdout.path}")
    holdout_payload = validate_holdout_payload(
        load_json_mapping_from_repo(repo_root, holdout_path),
        fixture_manifest.holdout,
        fixture_manifest.fixture_set_id,
    )
    holdout_case_suites = {
        holdout_case.id: tuple(holdout_case.suites) for holdout_case in holdout_payload.holdout
    }
    if holdout_case_suites != EXPECTED_HOLDOUT_CASE_SUITES:
        raise ValueError("holdout case ids or suite associations changed under v1")
    for holdout_case in holdout_payload.holdout:
        if holdout_case.id in fixture_case_ids:
            raise ValueError(f"holdout case id overlaps fixture cases: {holdout_case.id}")
        fixture_case_ids.add(holdout_case.id)
        for suite_name in holdout_case.suites:
            if suite_name not in EXPECTED_SUITES:
                raise ValueError(f"unexpected holdout suite association: {suite_name}")
            suite_holdout_case_ids[suite_name].append(holdout_case.id)

    for suite_name in EXPECTED_SUITES:
        if not suite_fixture_case_ids[suite_name] and not suite_holdout_case_ids[suite_name]:
            raise ValueError(f"suite has no associated fixture or holdout cases: {suite_name}")

    return FixtureValidation(
        fixture_hashes=fixture_hashes,
        holdout_hashes={holdout_path.as_posix(): actual_holdout_hash},
        suite_fixture_case_ids={
            name: tuple(sorted(case_ids)) for name, case_ids in suite_fixture_case_ids.items()
        },
        suite_holdout_case_ids={
            name: tuple(sorted(case_ids)) for name, case_ids in suite_holdout_case_ids.items()
        },
    )


def validate_hashes(
    actual_hashes: Mapping[str, str],
    expected_files: Sequence[FixtureFileConfig],
    label: str,
) -> None:
    expected_hashes = {
        ensure_allowed_repo_path(item.path).as_posix(): item.sha256 for item in expected_files
    }
    if set(actual_hashes) != set(expected_hashes):
        raise ValueError(f"{label} hash manifest paths do not match declared files")
    for rel_path, actual_hash in actual_hashes.items():
        if expected_hashes[rel_path] != actual_hash:
            raise ValueError(f"{label} hash mismatch: {rel_path}")


def validate_pinned_hashes(
    repo_root: Path,
    manifest: EvalManifestConfig,
    fixture_manifest: FixtureManifestConfig,
) -> tuple[HashSet, FixtureValidation]:
    config_hashes = hash_declared_files(repo_root, EXPECTED_CONFIG_PATHS)
    validate_hashes(config_hashes, fixture_manifest.config_files, "config")

    input_patterns = list(EXPECTED_FROZEN_SOURCE_PATTERNS)
    input_patterns.extend(EXPECTED_SUITE_INPUTS.values())
    input_hashes = hash_declared_files(repo_root, input_patterns)
    validate_hashes(input_hashes, fixture_manifest.frozen_inputs, "frozen input")

    fixture_validation = validate_fixtures(repo_root, fixture_manifest)
    return HashSet(
        evaluation_manifest_sha256=sha256_repo_file(repo_root, EVAL_MANIFEST_PATH),
        config=config_hashes,
        inputs=input_hashes,
        fixtures=fixture_validation.fixture_hashes,
        holdout=fixture_validation.holdout_hashes,
    ), fixture_validation


def network_guard_source() -> str:
    return """
import ctypes
import os
import _socket
import socket
import socketserver
import subprocess

try:
    import _ctypes
except ImportError:
    _ctypes = None

try:
    import _posixsubprocess
except ImportError:
    _posixsubprocess = None


class CompanyOSEvaluationNetworkBlocked(RuntimeError):
    pass


class CompanyOSEvaluationSubprocessBlocked(RuntimeError):
    pass


def _network_blocked(*args, **kwargs):
    raise CompanyOSEvaluationNetworkBlocked("network access is prohibited during Company OS evaluation")


def _subprocess_blocked(*args, **kwargs):
    raise CompanyOSEvaluationSubprocessBlocked("child process spawning is prohibited during Company OS evaluation")


def _deny_network_attribute(module, name):
    if hasattr(module, name):
        try:
            setattr(module, name, _network_blocked)
        except (AttributeError, TypeError):
            pass


socket.create_connection = _network_blocked
socket.create_server = _network_blocked
socket.fromfd = _network_blocked
socket.getaddrinfo = _network_blocked
socket.gethostbyaddr = _network_blocked
socket.gethostbyname = _network_blocked
socket.gethostbyname_ex = _network_blocked
socket.gethostname = _network_blocked
socket.getnameinfo = _network_blocked
socket.socket.connect = _network_blocked
socket.socket.connect_ex = _network_blocked
socket.socket.bind = _network_blocked
socket.socket.listen = _network_blocked
socket.socket.accept = _network_blocked
socket.socket.send = _network_blocked
socket.socket.sendall = _network_blocked
socket.socket.sendto = _network_blocked
socket.socket.recvfrom = _network_blocked
socket.socket.recvfrom_into = _network_blocked
if hasattr(socket.socket, "sendmsg"):
    socket.socket.sendmsg = _network_blocked
if hasattr(socket.socket, "recvmsg"):
    socket.socket.recvmsg = _network_blocked
if hasattr(socket, "socketpair"):
    socket.socketpair = _network_blocked
if hasattr(socket, "SocketType"):
    socket.SocketType = _network_blocked
for _name in (
    "getaddrinfo",
    "gethostbyaddr",
    "gethostbyname",
    "gethostbyname_ex",
    "gethostname",
    "getnameinfo",
    "fromfd",
    "socket",
    "SocketType",
    "socketpair",
):
    _deny_network_attribute(_socket, _name)
socketserver.TCPServer.server_bind = _network_blocked
socketserver.UDPServer.server_bind = _network_blocked
subprocess.Popen = _subprocess_blocked
subprocess.call = _subprocess_blocked
subprocess.check_call = _subprocess_blocked
subprocess.check_output = _subprocess_blocked
subprocess.run = _subprocess_blocked
os.system = _subprocess_blocked
os.popen = _subprocess_blocked
ctypes.CDLL = _subprocess_blocked
ctypes.PyDLL = _subprocess_blocked
if hasattr(ctypes, "_dlopen"):
    ctypes._dlopen = _subprocess_blocked
if _ctypes is not None and hasattr(_ctypes, "dlopen"):
    _ctypes.dlopen = _subprocess_blocked
if _posixsubprocess is not None and hasattr(_posixsubprocess, "fork_exec"):
    _posixsubprocess.fork_exec = _subprocess_blocked
for _name in (
    "fork",
    "forkpty",
    "posix_spawn",
    "posix_spawnp",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
):
    if hasattr(os, _name):
        setattr(os, _name, _subprocess_blocked)
""".lstrip()


def create_network_guard(directory: Path) -> Path:
    guard_path = directory / "sitecustomize.py"
    guard_path.write_text(network_guard_source(), encoding="utf-8")
    return guard_path


def build_suite_environment(
    repo_root: Path,
    network_guard_dir: Path,
    isolated_home: Path,
    isolated_tmp: Path,
) -> dict[str, str]:
    keep_names = {"LANG", "LC_ALL"}
    env: dict[str, str] = {}
    for name, value in os.environ.items():
        if name not in keep_names:
            continue
        if any(marker in name.upper() for marker in SENSITIVE_ENV_MARKERS):
            continue
        env[name] = value
    pythonpath_parts = [str(network_guard_dir), str(repo_root / "src")]
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env["HOME"] = str(isolated_home)
    env["TMPDIR"] = str(isolated_tmp)
    env["USER"] = "company-os-evaluator"
    env["PATH"] = os.pathsep.join(("/usr/bin", "/bin"))
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONSAFEPATH"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env.update(OFFLINE_ENV)
    return env


def pytest_argv_for_suite(suite: SuiteConfig) -> list[str]:
    expected_parts = shlex.split(EXPECTED_SUITES[suite.name])
    suite_parts = shlex.split(suite.command)
    if suite_parts != expected_parts or suite_parts[:3] != ["uv", "run", "pytest"]:
        raise ValueError(f"unexpected pytest suite command: {suite.name}")
    return [sys.executable, "-m", "pytest", *suite_parts[3:]]


def run_pytest_suite(suite: SuiteConfig, repo_root: Path, env: Mapping[str, str]) -> SuiteExecution:
    try:
        completed = subprocess.run(
            pytest_argv_for_suite(suite),
            cwd=repo_root,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return SuiteExecution(exit_code=None, error_code="suite_execution_error")
    return SuiteExecution(exit_code=completed.returncode)


def suite_outcome_from_execution(
    suite: SuiteConfig,
    execution: SuiteExecution,
    fixture_validation: FixtureValidation,
) -> SuiteOutcome:
    if execution.error_code or execution.exit_code is None:
        status: SuiteStatus = "unknown"
    elif execution.exit_code == 0:
        status = "pass"
    else:
        status = "fail"
    fixture_case_ids = fixture_validation.suite_fixture_case_ids[suite.name]
    holdout_case_ids = fixture_validation.suite_holdout_case_ids[suite.name]
    return SuiteOutcome(
        name=suite.name,
        command_sha256=sha256_text(suite.command),
        inputs=suite.inputs,
        network=suite.network,
        required=suite.required,
        status=status,
        exit_code=execution.exit_code,
        error_code=execution.error_code,
        fixture_case_ids=fixture_case_ids,
        fixture_case_count=len(fixture_case_ids),
        holdout_case_ids=holdout_case_ids,
        holdout_case_count=len(holdout_case_ids),
    )


def overall_outcome(
    suite_outcomes: Sequence[SuiteOutcome], unknown_reasons: Sequence[str]
) -> Outcome:
    if unknown_reasons or any(suite.status == "unknown" for suite in suite_outcomes):
        return "unknown"
    if any(suite.required and suite.status == "fail" for suite in suite_outcomes):
        return "fail"
    if suite_outcomes and all(suite.status == "pass" for suite in suite_outcomes):
        return "pass"
    return "unknown"


def score_dimensions(
    default_scores: Mapping[str, str], outcome: Outcome
) -> tuple[ScoreDimension, ...]:
    score = SCORE_BY_OUTCOME[outcome]
    return tuple(
        ScoreDimension(name=name, requirement=requirement, score=score)
        for name, requirement in sorted(default_scores.items())
    )


def best_effort_hash_declared_paths(repo_root: Path, paths: Sequence[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in paths:
        try:
            rel_path = ensure_allowed_repo_path(path)
            hashes[rel_path.as_posix()] = sha256_repo_file(repo_root, rel_path)
        except (FileNotFoundError, OSError, RuntimeError, ValueError):
            continue
    return hashes


def best_effort_hash_declared_patterns(repo_root: Path, patterns: Sequence[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for pattern in patterns:
        try:
            for rel_path in resolve_declared_files(repo_root, [pattern]):
                hashes[rel_path] = sha256_repo_file(repo_root, rel_path)
        except (FileNotFoundError, OSError, RuntimeError, ValueError):
            continue
    return hashes


def best_effort_hash_evidence(repo_root: Path) -> HashSet:
    evaluation_manifest_sha256: str | None = None
    try:
        evaluation_manifest_sha256 = sha256_repo_file(repo_root, EVAL_MANIFEST_PATH)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        evaluation_manifest_sha256 = None

    return HashSet(
        evaluation_manifest_sha256=evaluation_manifest_sha256,
        config=best_effort_hash_declared_paths(repo_root, EXPECTED_CONFIG_PATHS),
        inputs=best_effort_hash_declared_patterns(
            repo_root,
            (*EXPECTED_FROZEN_SOURCE_PATTERNS, *EXPECTED_SUITE_INPUTS.values()),
        ),
        fixtures=best_effort_hash_declared_paths(repo_root, (EXPECTED_PUBLIC_FIXTURE_PATH,)),
        holdout=best_effort_hash_declared_paths(repo_root, (EXPECTED_HOLDOUT_PATH,)),
    )


def fixture_identity(
    manifest: EvalManifestConfig,
    fixture_manifest: FixtureManifestConfig,
) -> FixtureSetIdentity:
    return FixtureSetIdentity(
        id=fixture_manifest.fixture_set_id,
        version=fixture_manifest.version,
        manifest_path=manifest.company_os_contract.fixture_manifest,
        manifest_sha256=manifest.company_os_contract.fixture_manifest_sha256,
    )


def isolation_summary(privacy_policy: Mapping[str, str] | None = None) -> IsolationSummary:
    return IsolationSummary(
        network="prohibited",
        environment="scrubbed",
        raw_suite_output_captured=False,
        prohibited_boundaries=(
            ".self-improvement runtime JSONL",
            "data/content-queue",
            "promotion",
            "publish",
            "schedule",
            "external integrations",
        ),
        privacy_policy=dict(privacy_policy or EXPECTED_PRIVACY_POLICY),
    )


def unknown_artifacts(
    repo_root: Path,
    output_dir: Path,
    generated_at_utc: str,
    reason: str,
) -> EvaluationRun:
    fixture_set = FixtureSetIdentity(
        id="unknown",
        version="unknown",
        manifest_path=EXPECTED_FIXTURE_MANIFEST_PATH,
        manifest_sha256=None,
    )
    hashes = best_effort_hash_evidence(repo_root)
    suite_outcomes = tuple(
        SuiteOutcome(
            name=name,
            command_sha256=sha256_text(command),
            inputs="unknown",
            network="prohibited",
            required=True,
            status="unknown",
            exit_code=None,
            error_code="preflight_unknown",
            fixture_case_ids=(),
            fixture_case_count=0,
            holdout_case_ids=(),
            holdout_case_count=0,
        )
        for name, command in sorted(EXPECTED_SUITES.items())
    )
    trace = TraceArtifact(
        schema=TRACE_SCHEMA,
        generated_at_utc=generated_at_utc,
        repo=EXPECTED_REPO,
        evaluator="company-os-contract",
        outcome="unknown",
        fixture_set=fixture_set,
        hashes=hashes,
        score_dimensions=EXPECTED_SCORE_DIMENSIONS,
        suite_outcomes=suite_outcomes,
        isolation=isolation_summary(),
        unknown_reasons=(reason,),
    )
    scorecard = ScorecardArtifact(
        schema=SCORECARD_SCHEMA,
        generated_at_utc=generated_at_utc,
        repo=EXPECTED_REPO,
        evaluator="company-os-contract",
        outcome="unknown",
        fixture_set=fixture_set,
        hashes=hashes,
        score_dimensions=score_dimensions(EXPECTED_SCORE_DIMENSIONS, "unknown"),
        suite_outcomes=suite_outcomes,
        isolation=isolation_summary(),
        unknown_reasons=(reason,),
    )
    return write_artifacts(output_dir, trace, scorecard)


def validate_output_dir(repo_root: Path, output_dir: Path | None) -> Path:
    requested = output_dir or DEFAULT_OUTPUT_DIR
    if requested.is_absolute():
        candidate = requested.resolve(strict=False)
    else:
        rel_path = relative_path(requested)
        normalized = rel_path.as_posix()
        if any(
            normalized == prefix or normalized.startswith(f"{prefix}/")
            for prefix in PROHIBITED_PATH_PREFIXES
        ):
            raise ValueError(f"runtime path is prohibited for evaluation outputs: {normalized}")
        candidate = repo_root / rel_path

    reject_symlink_components(candidate)
    resolved = candidate.resolve(strict=False)
    repo_artifact_root = (repo_root / ".eval-artifacts").resolve(strict=False)
    temp_roots = (
        Path(tempfile.gettempdir()).resolve(strict=True),
        Path("/tmp").resolve(strict=True),
    )
    if resolved.is_relative_to(repo_root):
        if not resolved.is_relative_to(repo_artifact_root):
            raise ValueError("repository output directories must stay under .eval-artifacts")
    elif not requested.is_absolute() or not any(
        resolved.is_relative_to(temp_root) for temp_root in temp_roots
    ):
        raise ValueError("external output directories are limited to the OS temporary root")

    candidate.mkdir(parents=True, exist_ok=True)
    reject_symlink_components(candidate)
    resolved_after_create = candidate.resolve(strict=True)
    if resolved_after_create != resolved and not resolved_after_create.is_relative_to(repo_root):
        raise ValueError("output directory resolves outside its approved root")
    return candidate


def write_artifacts(
    output_dir: Path, trace: TraceArtifact, scorecard: ScorecardArtifact
) -> EvaluationRun:
    trace_path = output_dir / "trace.json"
    scorecard_path = output_dir / "scorecard.json"
    write_normalized_json(trace_path, trace)
    write_normalized_json(scorecard_path, scorecard)
    return EvaluationRun(
        outcome=trace.outcome,
        trace_path=trace_path,
        scorecard_path=scorecard_path,
        trace=trace,
        scorecard=scorecard,
    )


def evaluate_company_os_contract(
    repo_root: Path,
    output_dir: Path | None = None,
    generated_at_utc: str | None = None,
    suite_runner: SuiteRunner | None = None,
) -> EvaluationRun:
    repo_root = repo_root.resolve(strict=False)
    output_dir = validate_output_dir(repo_root, output_dir)
    timestamp = generated_at_utc or now_utc()
    runner = suite_runner or run_pytest_suite

    try:
        manifest, _manifest_data, _manifest_hash = load_eval_manifest(repo_root)
        validate_manifest_contract(manifest)
        normalized_manifest_hash = normalized_eval_manifest_hash(_manifest_data)
        fixture_manifest = load_fixture_manifest(repo_root, manifest, normalized_manifest_hash)
        hashes, fixture_validation = validate_pinned_hashes(repo_root, manifest, fixture_manifest)
    except (
        FileNotFoundError,
        OSError,
        RuntimeError,
        ValueError,
        ValidationError,
        json.JSONDecodeError,
    ) as exc:
        return unknown_artifacts(repo_root, output_dir, timestamp, type(exc).__name__)

    suite_results: list[SuiteOutcome] = []
    with tempfile.TemporaryDirectory(prefix="company-os-eval-") as guard_dir_name:
        guard_dir = Path(guard_dir_name)
        create_network_guard(guard_dir)
        isolated_home = guard_dir / "home"
        isolated_tmp = guard_dir / "tmp"
        isolated_home.mkdir()
        isolated_tmp.mkdir()
        env = build_suite_environment(repo_root, guard_dir, isolated_home, isolated_tmp)
        for suite in manifest.suites:
            execution = runner(suite, repo_root, env)
            suite_results.append(suite_outcome_from_execution(suite, execution, fixture_validation))

    unknown_reasons = tuple(
        f"{suite.name}:{suite.error_code}" for suite in suite_results if suite.status == "unknown"
    )
    outcome = overall_outcome(suite_results, unknown_reasons)
    fixture_set = fixture_identity(manifest, fixture_manifest)
    trace = TraceArtifact(
        schema=TRACE_SCHEMA,
        generated_at_utc=timestamp,
        repo=EXPECTED_REPO,
        evaluator="company-os-contract",
        outcome=outcome,
        fixture_set=fixture_set,
        hashes=hashes,
        score_dimensions=dict(sorted(manifest.default_scores.items())),
        suite_outcomes=tuple(suite_results),
        isolation=isolation_summary(manifest.frozen_inputs.privacy),
        unknown_reasons=unknown_reasons,
    )
    scorecard = ScorecardArtifact(
        schema=SCORECARD_SCHEMA,
        generated_at_utc=timestamp,
        repo=EXPECTED_REPO,
        evaluator="company-os-contract",
        outcome=outcome,
        fixture_set=fixture_set,
        hashes=hashes,
        score_dimensions=score_dimensions(manifest.default_scores, outcome),
        suite_outcomes=tuple(suite_results),
        isolation=isolation_summary(manifest.frozen_inputs.privacy),
        unknown_reasons=unknown_reasons,
    )
    return write_artifacts(output_dir, trace, scorecard)


def exit_code_for_outcome(outcome: Outcome) -> int:
    return {"pass": 0, "fail": 1, "unknown": 2}[outcome]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the offline Company OS contract evaluator.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timestamp", help="Fixed UTC timestamp for reproducible artifacts.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run = evaluate_company_os_contract(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        generated_at_utc=args.timestamp,
    )
    print(
        json.dumps(
            {
                "outcome": run.outcome,
                "trace": str(run.trace_path),
                "scorecard": str(run.scorecard_path),
            },
            sort_keys=True,
        )
    )
    return exit_code_for_outcome(run.outcome)


if __name__ == "__main__":
    raise SystemExit(main())
