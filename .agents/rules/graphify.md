---
trigger: always_on
description: Consult graphify-out/ for codebase, architecture, and cross-file edit safety.
---

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- When `graphify-out/graph.json` exists and the user asks how code is structured, wired, called, or where behavior lives, first run `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py query "<question>"`. Use `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py path "<A>" "<B>"` for relationships and `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py explain "<concept>"` for focused concepts. Answer from query output; read at most one source file only if the query is thin or missing a named symbol.
- Before editing a source file, run the traceable `fleet_graphify.py query` or `fleet_graphify.py path` wrapper to surface dependents/callers/importers. Include connected files in the change set or explicitly call out what else must change.
- Do not re-read multiple source files after a good query unless the user asks for line-level proof.
- Skip graphify for trivial one-line edits already in context, pure shell/commit/run tasks, and external/non-repo research.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw file browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code files in this session, run `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py update .` to keep the graph current (AST-only, no API cost).
- After modifying docs, notes, images, `AGENTS.md`, `CLAUDE.md`, or `ai-instructions/`, use `python3 /Users/mini/.openclaw/workspace/github/~fleet-system/system/shared/scripts/fleet_graphify.py . --update` or the installed AGY semantic hook wrapper. Fleet default semantic runner is `agy --model "Gemini 3.5 Flash (Medium)"`.
- In worktrees, use the worktree-local `graphify-out/`; do not share or symlink one graph across active branches.
