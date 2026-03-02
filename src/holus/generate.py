"""Generate content — run ONE marketing agent cycle without publishing.

Preflight checks run first to validate the environment.
The agent executes: observe → reason → act → evaluate.
Output goes to data/content-queue/ for human review.

Usage:
    uv run python -m holus.generate
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from holus.preflight import check_api_key, run_preflight

QUEUE_DIR = Path("data/content-queue")


def _list_queue_files() -> list[Path]:
    """Return sorted YAML files in the content queue."""
    if not QUEUE_DIR.exists():
        return []
    return sorted(QUEUE_DIR.glob("*.yaml"))


def _print_summary(before_count: int) -> None:
    """Print a summary of newly generated content."""
    files = _list_queue_files()
    new_files = files[before_count:]

    print("\n" + "=" * 60)
    print("  GENERATION COMPLETE")
    print("=" * 60)

    if not new_files:
        print("\n  No new content generated.")
        print("  Check logs above for errors.\n")
        return

    print(f"\n  {len(new_files)} new piece(s) in data/content-queue/\n")

    for path in new_files:
        try:
            data = yaml.safe_load(path.read_text())
            platform = data.get("platform", "?")
            topic = data.get("topic", "?")
            text = data.get("text", "")
            char_count = len(text)
            piece_id = data.get("piece_id", path.stem)

            print(f"  [{platform.upper()}] {topic}")
            print(f"    ID: {piece_id}")
            print(f"    Length: {char_count} chars")

            # Show first line of content as preview
            first_line = text.split("\n")[0][:80] if text else ""
            if first_line:
                print(f'    Preview: "{first_line}..."')
            print()
        except Exception:
            print(f"  [?] {path.name} (could not parse)")
            print()

    print("  Next steps:")
    print("    just review-content        # Review generated content")
    print("    just approve-content <id>   # Approve a piece for publishing")
    print("    just publish-approved       # Publish approved content")
    print()


async def _run_agent() -> dict[str, Any]:
    """Import and run one marketing agent cycle."""
    from holus.agents.marketing.agent import MarketingAgent
    from holus.core.run_lock import acquire_run_lock

    with acquire_run_lock("holus-generate"):
        agent = MarketingAgent()
        try:
            result = await agent.run()
        finally:
            agent.close()
    return result


def main() -> None:
    """CLI entry point: preflight → generate → summary."""
    # -- Preflight (require API key) ------------------------------------------
    api_check = check_api_key()
    if not api_check.passed:
        print("\n  [FAIL] ANTHROPIC_API_KEY is required for content generation.")
        if api_check.fix:
            print(f"  Fix: {api_check.fix}")
        print()
        sys.exit(1)

    # Run full preflight (informational — only API key is blocking)
    results = run_preflight()
    print("\n=== Holus Preflight ===\n")
    has_failures = False
    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        print(f"  [{icon}] {r.name}: {r.detail}")
        if not r.passed and r.fix:
            print(f"         Fix: {r.fix}")
            has_failures = True

    if has_failures:
        print("\n  Some checks failed (non-blocking). Proceeding with generation.\n")
    else:
        print("\n  All checks passed.\n")

    # -- Generate -------------------------------------------------------------
    before_count = len(_list_queue_files())

    print("=" * 60)
    print("  GENERATING CONTENT")
    print("=" * 60)
    print()
    print("  Running marketing agent cycle...")
    print("  observe → reason → act → evaluate")
    print()

    start = time.monotonic()

    try:
        result = asyncio.run(_run_agent())
    except KeyboardInterrupt:
        print("\n  Interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n  [ERROR] Agent failed: {exc}")
        sys.exit(1)

    elapsed = time.monotonic() - start

    # -- Evaluation summary ---------------------------------------------------
    evaluation = result.get("evaluation", {})
    pieces = evaluation.get("pieces_created", 0)
    reasoning = result.get("strategy_reasoning", "")

    print(f"  Cycle finished in {elapsed:.1f}s")
    print(f"  Pieces created: {pieces}")

    if reasoning:
        # Show first 200 chars of strategy reasoning
        preview = reasoning[:200].replace("\n", " ")
        if len(reasoning) > 200:
            preview += "..."
        print(f"  Strategy: {preview}")

    # -- Content summary ------------------------------------------------------
    _print_summary(before_count)


if __name__ == "__main__":
    main()
