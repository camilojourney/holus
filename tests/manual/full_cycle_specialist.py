#!/usr/bin/env python3
"""Full marketing cycle with specialist chain active.

Runs: preflight → observe → reason → act (specialist chain) → evaluate
Saves all output to data/test-runs/specialist-chain/
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Setup paths
HOLUS_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HOLUS_ROOT / "src"))
os.chdir(HOLUS_ROOT)

# Ensure proxy is used
os.environ.setdefault("ANTHROPIC_BASE_URL", "http://localhost:8080")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-proxy")

OUTPUT_DIR = HOLUS_ROOT / "data" / "test-runs" / "specialist-chain"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def run_cycle():
    print(f"[{datetime.now():%H:%M:%S}] Starting full cycle with specialist chain...")

    from unittest.mock import patch

    from holus.agents.marketing.agent import MarketingAgent
    from holus.core.config import HolusConfig
    from holus.core.cycle_state import HealthResult

    # Patch preflight to always pass (silos aren't running locally)
    mock_health = HealthResult(
        blocking_ok=True,
        available_silos=["social_media"],
        warnings=["Preflight bypassed for local testing"],
    )

    # Let config auto-load from YAML + env
    config = HolusConfig.load(agent_name="marketing-strategist")

    agent = MarketingAgent(config=config)

    print(f"[{datetime.now():%H:%M:%S}] Agent created (model={config.sonnet_model}). Running...")
    print(f"[{datetime.now():%H:%M:%S}] Proxy: {config.anthropic_base_url}")
    t0 = time.time()

    try:
        with patch("holus.agents.marketing.agent.run_preflight_checks", return_value=mock_health):
            result = await agent.run()
    except Exception as e:
        print(f"[{datetime.now():%H:%M:%S}] CYCLE ERROR: {e}")
        import traceback
        traceback.print_exc()
        result = {"error": str(e)}

    elapsed = time.time() - t0
    print(f"[{datetime.now():%H:%M:%S}] Cycle finished in {elapsed:.1f}s")

    # Save result
    result_file = OUTPUT_DIR / "cycle_result.json"
    with open(result_file, "w") as f:
        json.dump(result if isinstance(result, dict) else {"raw": str(result)}, f, indent=2, default=str)
    print(f"[{datetime.now():%H:%M:%S}] Result saved to {result_file}")

    # Check content queue
    queue_dir = HOLUS_ROOT / "data" / "content-queue"
    queue_files = list(queue_dir.glob("*.yaml")) if queue_dir.exists() else []
    print(f"[{datetime.now():%H:%M:%S}] Content queue: {len(queue_files)} items")
    for qf in queue_files:
        print(f"  - {qf.name}")
        # Print first 10 lines of each queue file
        with open(qf) as f:
            for i, line in enumerate(f):
                if i >= 10:
                    print("    ...")
                    break
                print(f"    {line.rstrip()}")

    # Check trajectory
    traj_file = HOLUS_ROOT / "data" / "trajectory.jsonl"
    if traj_file.exists():
        lines = traj_file.read_text().strip().split("\n")
        print(f"[{datetime.now():%H:%M:%S}] Trajectory: {len(lines)} entries")
        if lines:
            last_entry = json.loads(lines[-1])
            model_used = last_entry.get("execution", {}).get("model", "unknown")
            print(f"  Last model: {model_used}")
            specialist = "specialist-chain" in model_used
            print(f"  Specialist chain used: {specialist}")

    # Copy queue items to output dir
    import shutil
    for qf in queue_files:
        shutil.copy2(qf, OUTPUT_DIR / qf.name)

    print(f"\n[{datetime.now():%H:%M:%S}] === DONE ===")
    print(f"Total time: {elapsed:.1f}s")
    print(f"Output dir: {OUTPUT_DIR}")

    return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_cycle())
