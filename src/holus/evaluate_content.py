"""Evaluate pending content — run domain evaluators on content-queue pieces.

Loads YAML files from data/content-queue/ with status: pending_review,
runs JudgeAgent.evaluate_with_routing() on each, prints a formatted report,
and logs results to .self-improvement/memory/trajectory.jsonl.

Usage:
    uv run python -m holus.evaluate_content
    uv run python -m holus.evaluate_content --piece-id d4471adb
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QUEUE_DIR = Path("data/content-queue")
TRAJECTORY_PATH = Path(".self-improvement/memory/trajectory.jsonl")

# ANSI color codes
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

VERDICT_COLORS = {
    "PASS": GREEN,
    "PARTIAL": YELLOW,
    "FAIL": RED,
}


# ---------------------------------------------------------------------------
# Content loading
# ---------------------------------------------------------------------------


def _load_pending_pieces(piece_id: str | None = None) -> list[dict[str, Any]]:
    """Load YAML files from content-queue with status: pending_review.

    If *piece_id* is given, load only that piece (regardless of status).
    """
    if not QUEUE_DIR.exists():
        return []

    pieces: list[dict[str, Any]] = []
    for path in sorted(QUEUE_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        if piece_id is not None:
            if data.get("piece_id") == piece_id:
                pieces.append(data)
                break
        else:
            if data.get("status") == "pending_review":
                pieces.append(data)

    return pieces


# ---------------------------------------------------------------------------
# Trajectory logging
# ---------------------------------------------------------------------------


def _log_trajectory(piece: dict[str, Any], evaluation: Any) -> None:
    """Append an evaluation entry to trajectory.jsonl."""
    TRAJECTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "agent_id": "evaluate-content-cli",
        "task_type": "content_evaluation",
        "task_summary": f"Evaluate {piece.get('content_type', '?')} for {piece.get('platform', '?')}",
        "status": "success" if evaluation.verdict.value != "FAIL" else "partial",
        "duration_seconds": 0.0,
        "attempts": 1,
        "judge_verdict": evaluation.verdict.value,
        "judge_score": evaluation.score,
        "judge_feedback": evaluation.feedback,
        "model_used": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "thread_id": None,
        "correlation_id": None,
        "error_message": None,
        "metadata": {
            "piece_id": piece.get("piece_id", ""),
            "platform": piece.get("platform", ""),
            "content_type": piece.get("content_type", ""),
            "dimension_scores": evaluation.dimension_scores,
        },
    }

    with open(TRAJECTORY_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


def _print_piece_report(piece: dict[str, Any], evaluation: Any) -> None:
    """Print a formatted evaluation report for a single piece."""
    platform = piece.get("platform", "?").upper()
    piece_id = piece.get("piece_id", "?")
    text = piece.get("text", "")
    char_count = len(text)
    content_type = piece.get("content_type", "?")

    verdict = evaluation.verdict.value
    color = VERDICT_COLORS.get(verdict, RESET)

    print(f"\n  {BOLD}[{platform}]{RESET} {piece_id}")
    print(f"    Type: {content_type} | Chars: {char_count}")
    print(f"    Verdict: {color}{BOLD}{verdict}{RESET} | Score: {evaluation.score:.2f}")

    # Per-dimension scores
    if evaluation.dimension_scores:
        dims = "    Dimensions: "
        parts = []
        for dim, score in evaluation.dimension_scores.items():
            parts.append(f"{dim}={score:.2f}")
        dims += ", ".join(parts)
        print(dims)

    # Feedback (first 200 chars)
    if evaluation.feedback:
        feedback_preview = evaluation.feedback[:200].replace("\n", " ")
        if len(evaluation.feedback) > 200:
            feedback_preview += "..."
        print(f"    {DIM}Feedback: {feedback_preview}{RESET}")


def _print_summary(total: int, passed: int, partial: int, failed: int, elapsed: float) -> None:
    """Print the final summary line."""
    print("\n" + "=" * 60)
    print(f"  {BOLD}EVALUATION SUMMARY{RESET}")
    print("=" * 60)
    print(f"  Evaluated: {total} piece(s) in {elapsed:.1f}s")
    print(f"  {GREEN}PASS: {passed}{RESET}  |  {YELLOW}PARTIAL: {partial}{RESET}  |  {RED}FAIL: {failed}{RESET}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point: load pending content, evaluate, report."""
    parser = argparse.ArgumentParser(
        description="Evaluate pending content with domain-specific judges.",
    )
    parser.add_argument(
        "--piece-id",
        type=str,
        default=None,
        help="Evaluate a single piece by its piece_id (ignores status filter).",
    )
    args = parser.parse_args()

    # -- Load pieces ----------------------------------------------------------
    pieces = _load_pending_pieces(piece_id=args.piece_id)

    if not pieces:
        if args.piece_id:
            print(f"\n  No piece found with id '{args.piece_id}' in {QUEUE_DIR}/\n")
        else:
            print(f"\n  No pieces with status: pending_review in {QUEUE_DIR}/\n")
        sys.exit(0)

    print("\n" + "=" * 60)
    print(f"  {BOLD}EVALUATING CONTENT{RESET}")
    print("=" * 60)
    print(f"  Found {len(pieces)} piece(s) to evaluate.\n")

    # -- Import judge (deferred so missing deps surface clearly) --------------
    from holus.self_improvement.judge import JudgeAgent

    judge = JudgeAgent()

    # -- Evaluate each piece --------------------------------------------------
    passed = 0
    partial = 0
    failed = 0
    start = time.monotonic()

    for piece in pieces:
        content_type = piece.get("content_type", "content")
        text = piece.get("text", "")
        platform = piece.get("platform", "unknown")
        topic = piece.get("topic", "")

        task = (
            f"Create a {content_type} post for {platform}."
            + (f" Topic: {topic}" if topic else "")
        )

        try:
            evaluation = judge.evaluate_with_routing(
                task=task,
                content_type=content_type,
                output=text,
            )
        except Exception as exc:
            print(f"\n  [ERROR] Failed to evaluate {piece.get('piece_id', '?')}: {exc}")
            failed += 1
            continue

        # Tally
        if evaluation.verdict.value == "PASS":
            passed += 1
        elif evaluation.verdict.value == "PARTIAL":
            partial += 1
        else:
            failed += 1

        # Print report for this piece
        _print_piece_report(piece, evaluation)

        # Log to trajectory
        try:
            _log_trajectory(piece, evaluation)
        except Exception as exc:
            print(f"    {DIM}(trajectory log failed: {exc}){RESET}")

    elapsed = time.monotonic() - start

    # -- Summary --------------------------------------------------------------
    _print_summary(len(pieces), passed, partial, failed, elapsed)


if __name__ == "__main__":
    main()
