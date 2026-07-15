"""Run one Research Radar cycle from the command line."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from holus.research.radar import run_radar


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Run the Holus Research Radar once.")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    args = parser.parse_args()
    report = await run_radar(repo_root=Path(args.repo_root))
    print(json.dumps(report.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
