import json
from pathlib import Path

import yaml

from holus.core.capability_gap import CapabilityGap, CapabilityTier
from holus.self_improvement.build_loop import BuildLoop


def test_build_loop_file_request(tmp_path):
    request_dir = tmp_path / "requests"
    history_path = tmp_path / "history.jsonl"
    loop = BuildLoop(request_dir=request_dir, history_path=history_path)

    gap = CapabilityGap(
        what="New Silo", why="Architecture change", tier=CapabilityTier.TIER_3_ARCHITECTURE
    )
    path = loop.file_request(gap)
    assert Path(path).exists()

    with open(path) as f:
        data = yaml.safe_load(f)
        assert data["status"] == "pending_human"
        assert data["tier"] == "tier_3_architecture"


def test_build_loop_budget(tmp_path):
    history_path = tmp_path / "history.jsonl"
    loop = BuildLoop(history_path=history_path)

    # Empty history
    assert loop.check_budget()

    # Add 2 entries for today
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    with open(history_path, "a") as f:
        f.write(json.dumps({"timestamp": now, "slug": "test1"}) + "\n")
        f.write(json.dumps({"timestamp": now, "slug": "test2"}) + "\n")

    assert not loop.check_budget()
