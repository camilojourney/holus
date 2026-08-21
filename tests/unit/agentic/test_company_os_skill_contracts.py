"""Offline contracts for Holus-owned Company OS skills.

The suite deliberately imports only the local helper and writes all runtime
artifacts to pytest's temporary directory. It must never contact an external
service or use a Fleet runtime path.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    from types import ModuleType


ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = ROOT / ".agents" / "skills"
SKILL_NAMES = (
    "company-brand-desk",
    "company-content-desk",
    "company-marketing-desk",
    "company-sales-desk",
    "company-evolve",
    "company-supervisor",
)
HELPER_PATH = SKILLS_ROOT / "_shared" / "company_os.py"


def load_helper() -> ModuleType:
    spec = importlib.util.spec_from_file_location("holus_company_os", HELPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def company_os() -> ModuleType:
    return load_helper()


def test_company_os_skills_are_complete_local_packages() -> None:
    for name in SKILL_NAMES:
        skill_root = SKILLS_ROOT / name
        skill = skill_root / "SKILL.md"
        assert skill.is_file()
        assert f"name: {name}" in skill.read_text(encoding="utf-8")
        assert (skill_root / "references" / "output-contract.md").is_file()
        assert (skill_root / "evals" / "evals.json").is_file()
        assert len(list((skill_root / "agents").glob("*.md"))) >= 2


def test_trigger_contracts_include_positive_negative_and_hard_safety_cases() -> None:
    for name in SKILL_NAMES:
        cases = json.loads(
            (SKILLS_ROOT / name / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        assert any(case["should_trigger"] for case in cases)
        assert any(not case["should_trigger"] for case in cases)
        assert any(case.get("mode") == "hard_safety_gate" for case in cases)
        assert all(f"/{name}" in case["query"] for case in cases if case["should_trigger"])


def test_local_skill_sources_do_not_embed_fleet_runtime_or_eval_machinery() -> None:
    prohibited = (
        "/Users/mini/",
        "skill_telemetry.py",
        "eval_gate.py",
        "fleet_brain",
        "subprocess.run",
    )
    source_paths = [HELPER_PATH]
    for name in SKILL_NAMES:
        source_paths.extend((SKILLS_ROOT / name).rglob("*"))
    for path in source_paths:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert not any(value in text for value in prohibited), path


def test_evaluation_manifest_is_adapter_ready_and_path_portable() -> None:
    manifest_path = ROOT / "agentic" / "evals.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    registry = yaml.safe_load((ROOT / "agentic" / "manifest.yaml").read_text(encoding="utf-8"))
    assert registry["schema"] == "fleet.repo_agent_manifest.v1"
    assert {item["name"] for item in registry["skills"]} >= set(SKILL_NAMES)
    assert all((ROOT / item["path"]).is_file() for item in registry["skills"])
    assert (ROOT / registry["memory"]).is_file()
    assert (ROOT / registry["permissions"]).is_file()
    assert (ROOT / registry["tools"]).is_file()

    assert manifest["schema"] == "fleet.repo_evals.v1"
    assert manifest["repo"] == "holus"
    assert manifest["default_scores"]["safety"] == "required"
    assert {suite["name"] for suite in manifest["suites"]} == {
        "company-os-trigger-and-contract",
        "company-os-hard-safety",
    }
    assert all(suite["network"] == "prohibited" for suite in manifest["suites"])
    assert "/Users/" not in manifest_path.read_text(encoding="utf-8")

    migration = yaml.safe_load(
        (ROOT / "agentic" / "company-os-migration.yaml").read_text(encoding="utf-8")
    )
    assert migration["migration_mode"] == "additive"
    assert migration["fleet_cleanup_gate"]["fleet_sources_retained"] is True
    assert migration["fleet_cleanup_gate"]["removal_is_out_of_scope"] is True
    assert set(migration["canonical_skills"]) == set(SKILL_NAMES)

    parity = yaml.safe_load((ROOT / migration["parity_manifest"]).read_text(encoding="utf-8"))
    consumers = yaml.safe_load((ROOT / migration["consumer_manifest"]).read_text(encoding="utf-8"))
    assert set(parity["skills"]) == set(SKILL_NAMES)
    assert consumers["fleet_cleanup_precondition"]
    assert len(consumers["consumers"]) >= 5
    for skill in parity["skills"].values():
        assert all((ROOT / path).is_file() for path in skill.values())


def test_kill_switch_halts_content_desk_and_writes_only_local_artifacts(
    company_os: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRY_RUN", "1")
    kill_file = tmp_path / ".self-improvement" / "COMPANY_KILL"
    kill_file.parent.mkdir(parents=True)
    kill_file.write_text("HALT\n", encoding="utf-8")

    context = company_os.build_desk_context("content", tmp_path)
    row = company_os.render_desk_outputs("content", context, tmp_path)

    assert row["status"] == "HALT"
    assert row["silo_handoff"]["mode"] == "DRY_RUN"
    assert row["silo_handoff"]["mutates_external_system"] is False
    assert not list(tmp_path.rglob("*.tmp"))
    assert (
        tmp_path / ".self-improvement" / "automations" / "brand-content" / "events.jsonl"
    ).is_file()
    assert (tmp_path / ".self-improvement" / "hub" / "skill_runs.jsonl").is_file()


def test_publish_approval_never_turns_a_marketing_handoff_into_external_action(
    company_os: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRY_RUN", "1")
    automation = tmp_path / ".self-improvement" / "automations" / "brand-marketing"
    hub = tmp_path / ".self-improvement" / "hub"
    automation.mkdir(parents=True)
    hub.mkdir(parents=True)
    (automation / "events.jsonl").write_text(
        json.dumps(
            {
                "source": "campaign-request",
                "requested_action": "publish",
                "kpis": {
                    "reach": 10,
                    "content_shipped": 1,
                    "ctr": 0.1,
                    "top_of_funnel_leads": 1,
                    "channel_cac": 2,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (hub / "ic_decisions.jsonl").write_text(
        json.dumps({"status": "APPROVED", "action": "publish"}) + "\n",
        encoding="utf-8",
    )

    context = company_os.build_desk_context("marketing", tmp_path)
    row = company_os.render_desk_outputs("marketing", context, tmp_path)
    handoff = row["silo_handoff"]["holus_queue_review"]

    assert row["human_ic_required"] is False
    assert handoff["live_api_call"] is False
    assert row["silo_handoff"]["mutates_external_system"] is False
    assert handoff["route"] == "holus_queue_review_only"


def test_supervisor_keeps_human_actions_out_of_ready_for_code(
    company_os: ModuleType, tmp_path: Path
) -> None:
    event_path = tmp_path / ".self-improvement" / "automations" / "brand-sales" / "events.jsonl"
    event_path.parent.mkdir(parents=True)
    event_path.write_text(
        json.dumps(
            {
                "source": "company-sales-desk",
                "status": "PASS",
                "human_ic_required": True,
                "summary": "Outbound follow-up needs explicit approval.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    context = company_os.build_company_context(tmp_path)
    result = company_os.render_supervisor_outputs(context, tmp_path)

    queues = result["docket"]["queues"]
    assert len(queues["human_ic_required"]) == 1
    assert queues["ready_for_code"] == []
    assert result["event"]["status"] == "WARNING"
