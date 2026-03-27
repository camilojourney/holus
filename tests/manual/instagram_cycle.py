#!/usr/bin/env python3
"""Full marketing cycle targeting Instagram with specialist chain.

Tests the platform-aware specialist chain on Instagram:
  hook-architect → storyteller (instagram hints) → voice-guardian → cta-strategist

Uses the 'experience' account set (English, @camiloexperience).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

HOLUS_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HOLUS_ROOT / "src"))
os.chdir(HOLUS_ROOT)

os.environ.setdefault("ANTHROPIC_BASE_URL", "http://localhost:8080")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-proxy")

OUTPUT_DIR = HOLUS_ROOT / "data" / "test-runs" / "instagram-chain"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def run_cycle():
    print(f"[{datetime.now(tz=UTC):%H:%M:%S}] Starting Instagram specialist chain cycle...")

    from unittest.mock import patch

    from holus.agents.marketing.agent import MarketingAgent
    from holus.agents.marketing.models import ContentDecision, ContentType, Platform
    from holus.core.config import HolusConfig
    from holus.core.cycle_state import HealthResult

    mock_health = HealthResult(
        blocking_ok=True,
        available_silos=["social_media"],
        warnings=["Preflight bypassed for local testing"],
    )

    config = HolusConfig.load(agent_name="marketing-strategist")
    agent = MarketingAgent(config=config)

    # Override _fallback_decisions to produce Instagram decisions
    instagram_decisions = [
        ContentDecision(
            product="pilaster",
            platform=Platform.INSTAGRAM,
            content_type=ContentType.TUTORIAL,
            content_pillar="builder_stories",
            topic="How I built an AI image generation platform with memory — what makes Pilaster different",
            hook="Most AI image tools forget everything between sessions.\n\nI built one that remembers.",
            framework="original",
            reasoning="Instagram test: builder story for visual platform with hashtag CTA.",
            priority=1,
            estimated_engagement="high",
        ),
        ContentDecision(
            product="genpeli",
            platform=Platform.INSTAGRAM,
            content_type=ContentType.CASE_STUDY,
            content_pillar="technical_deep_dive",
            topic="From raw footage to polished reel in 90 seconds — the Genpeli pipeline",
            hook="I recorded a 12-minute video.\n\nGenpeli turned it into a 60-second reel. Automatically.",
            framework="original",
            reasoning="Instagram test: visual storytelling about video editing pipeline.",
            priority=2,
            estimated_engagement="high",
        ),
    ]

    # Patch: skip LLM reasoning, inject Instagram decisions directly
    original_reason = agent.reason

    async def mock_reason(state):
        result = await original_reason(state)
        # Override with our Instagram decisions
        result["content_decisions"] = [d.model_dump(mode="json") for d in instagram_decisions]
        print(
            f"[{datetime.now(tz=UTC):%H:%M:%S}] Injected {len(instagram_decisions)} Instagram decisions"
        )
        return result

    agent.reason = mock_reason

    print(f"[{datetime.now(tz=UTC):%H:%M:%S}] Agent created (model={config.sonnet_model})")
    print(f"[{datetime.now(tz=UTC):%H:%M:%S}] Proxy: {config.anthropic_base_url}")
    t0 = time.time()

    try:
        with patch("holus.agents.marketing.agent.run_preflight_checks", return_value=mock_health):
            result = await agent.run()
    except Exception as e:
        print(f"[{datetime.now(tz=UTC):%H:%M:%S}] CYCLE ERROR: {e}")
        import traceback

        traceback.print_exc()
        result = {"error": str(e)}

    elapsed = time.time() - t0
    print(f"\n[{datetime.now(tz=UTC):%H:%M:%S}] Cycle finished in {elapsed:.1f}s")

    # Save result
    result_file = OUTPUT_DIR / "cycle_result.json"
    with open(result_file, "w") as f:
        json.dump(
            result if isinstance(result, dict) else {"raw": str(result)}, f, indent=2, default=str
        )

    # Check content queue for Instagram items
    queue_dir = HOLUS_ROOT / "data" / "content-queue"
    queue_files = list(queue_dir.glob("*.yaml")) if queue_dir.exists() else []
    ig_files = [f for f in queue_files if "instagram" in f.read_text().lower()]
    print(
        f"\n[{datetime.now(tz=UTC):%H:%M:%S}] Content queue: {len(queue_files)} total, {len(ig_files)} Instagram"
    )

    for qf in ig_files:
        print(f"\n--- {qf.name} ---")
        content = qf.read_text()
        print(content[:2000])
        if len(content) > 2000:
            print("... (truncated)")

        # Copy to output dir
        import shutil

        shutil.copy2(qf, OUTPUT_DIR / qf.name)

    # Verify specialist chain was used
    traj_file = HOLUS_ROOT / "data" / "trajectory.jsonl"
    if traj_file.exists():
        lines = traj_file.read_text().strip().split("\n")
        recent = [json.loads(line) for line in lines[-5:]]
        chain_used = sum(
            1 for e in recent if "specialist-chain" in e.get("execution", {}).get("model", "")
        )
        print(
            f"\n[{datetime.now(tz=UTC):%H:%M:%S}] Trajectory: {len(lines)} total, {chain_used} specialist-chain in last 5"
        )

    print(f"\n[{datetime.now(tz=UTC):%H:%M:%S}] === DONE ===")
    print(f"Total time: {elapsed:.1f}s")
    print(f"Output dir: {OUTPUT_DIR}")

    return result


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_cycle())
