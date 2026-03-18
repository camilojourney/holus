#!/usr/bin/env python3
"""One-time script: archive legacy queue items that have no judge_score.

These items predate the judge wiring (Sprint 5) and will never get auto-published
because auto_publish.py skips items without judge_score. This moves them to
data/content-queue-archived/ so they don't clog the pipeline.
"""

import json
import shutil
from pathlib import Path

QUEUE_DIR = Path(__file__).resolve().parent.parent / "data" / "content-queue"
ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "data" / "content-queue-archived"


def main() -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived = 0
    kept = 0

    for path in sorted(QUEUE_DIR.iterdir()):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue

        try:
            text = path.read_text()
            if path.suffix == ".json":
                data = json.loads(text)
            else:
                import yaml
                data = yaml.safe_load(text)
        except Exception as exc:
            print(f"  SKIP (parse error): {path.name} — {exc}")
            continue

        has_score = (
            isinstance(data.get("judge_score"), (int, float))
            or isinstance(data.get("quality", {}).get("judge_score"), (int, float))
        )

        if has_score:
            kept += 1
        else:
            shutil.move(str(path), str(ARCHIVE_DIR / path.name))
            archived += 1
            print(f"  ARCHIVED: {path.name}")

    print(f"\nDone. Archived {archived}, kept {kept}.")


if __name__ == "__main__":
    main()
