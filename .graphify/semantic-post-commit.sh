#!/usr/bin/env bash
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 0
mkdir -p graphify-out

BRANCH="$(git branch --show-current 2>/dev/null || true)"
COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
CHANGED="$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null || true)"

python3 - "$BRANCH" "$COMMIT" "$CHANGED" <<'PY' >/dev/null 2>&1 || true
import json, sys
from datetime import datetime, timezone
from pathlib import Path
branch, commit, changed = sys.argv[1], sys.argv[2], sys.argv[3].splitlines()
Path("graphify-out/hook-status.json").write_text(json.dumps({
    "branch": branch,
    "commit": commit,
    "changed_files": changed,
    "runner": "agy",
    "primary_runner": "agy",
    "primary_model": "Gemini 3.5 Flash (Medium)",
    "fallback_runner": "codex",
    "fallback_model": "gpt-5.3-codex-spark",
    "checked_at": datetime.now(timezone.utc).isoformat(),
}, indent=2), encoding="utf-8")
PY

if [ -z "$CHANGED" ]; then
  exit 0
fi

SEMANTIC_CHANGED="$(printf '%s
' "$CHANGED" | awk '
  /(^|\/)AGENTS\.md$/ {print; next}
  /(^|\/)CLAUDE\.md$/ {print; next}
  /^ai-instructions\// {print; next}
  /^docs\// {print; next}
  /\.(md|mdx|rst|txt|pdf|png|jpg|jpeg|webp)$/ {print; next}
')"

if [ -z "$SEMANTIC_CHANGED" ]; then
  exit 0
fi

if [ -f graphify-out/.semantic-update.lock ]; then
  exit 0
fi

python3 - "$BRANCH" "$COMMIT" "$SEMANTIC_CHANGED" <<'PY' >/dev/null 2>&1 || true
import json, sys
from datetime import datetime, timezone
from pathlib import Path
branch, commit, changed = sys.argv[1], sys.argv[2], sys.argv[3].splitlines()
Path("graphify-out/semantic-status.json").write_text(json.dumps({
    "branch": branch,
    "commit": commit,
    "trigger": "post-commit",
    "semantic_files_changed": changed,
    "runner": "agy",
    "primary_runner": "agy",
    "primary_model": "Gemini 3.5 Flash (Medium)",
    "fallback_runner": "codex",
    "fallback_model": "gpt-5.3-codex-spark",
    "status": "queued",
    "logs": ["graphify-out/agy-update.log", "graphify-out/codex-update.log"],
    "queued_at": datetime.now(timezone.utc).isoformat(),
}, indent=2), encoding="utf-8")
PY

(
  touch graphify-out/.semantic-update.lock
  python3 - "$BRANCH" "$COMMIT" <<'PY' >/dev/null 2>&1 || true
import json, sys
from datetime import datetime, timezone
from pathlib import Path
path = Path("graphify-out/semantic-status.json")
data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
data.update({"status": "running", "runner_used": None, "started_at": datetime.now(timezone.utc).isoformat()})
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
  RUNNER_USED=""
  if command -v agy >/dev/null 2>&1; then
    agy --print --model "Gemini 3.5 Flash (Medium)" "Use graphify for this repo. Run python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py . --update, then python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py cluster-only ., and report whether graphify-out is current." > graphify-out/agy-update.log 2>&1
    RC=$?
    if [ "$RC" -eq 0 ]; then
      RUNNER_USED="agy"
    else
      echo "agy failed with exit $RC; trying codex fallback" >> graphify-out/codex-update.log
    fi
  else
    echo "agy not found; trying codex fallback" > graphify-out/agy-update.log
    RC=127
  fi

  if [ "$RC" -ne 0 ]; then
    if command -v codex >/dev/null 2>&1; then
      codex exec --model "gpt-5.3-codex-spark" "Use the graphify skill. Run python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py . --update, then python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py cluster-only ., and report whether graphify-out is current." >> graphify-out/codex-update.log 2>&1
      RC=$?
      if [ "$RC" -eq 0 ]; then
        RUNNER_USED="codex"
      fi
    else
      echo "codex not found" >> graphify-out/codex-update.log
      RC=127
    fi
  fi

  python3 - "$RC" "$RUNNER_USED" <<'PY' >/dev/null 2>&1 || true
import json, sys
from datetime import datetime, timezone
from pathlib import Path
rc = int(sys.argv[1])
runner_used = sys.argv[2] or None
path = Path("graphify-out/semantic-status.json")
data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
data.update({
    "status": "success" if rc == 0 else "failed",
    "exit_code": rc,
    "runner_used": runner_used,
    "finished_at": datetime.now(timezone.utc).isoformat(),
})
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
  rm -f graphify-out/.semantic-update.lock
) >/dev/null 2>&1 &
