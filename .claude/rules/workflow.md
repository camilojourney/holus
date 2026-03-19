# Workflow

## Core Principle

**When the user says do something, do it.** No asking "should I proceed?", no confirmation prompts. Report results, not intentions.

## Skills-First Execution

**ALWAYS use skills for repo work. NEVER bypass with raw agents.**

| Task | Skill |
|------|-------|
| Implement features, fix bugs, add API | `/code` (modes: default, fix, api) |
| Write specs (+ vision if missing) | `/specs` (includes Phase 0 vision) |
| Research options or challenge assumptions | `/research` (2 modes: options, adversary) |
| UX/UI audit + fix | `/ux` |
| Acceptance testing (Playwright) | `/verify` |
| Health check, deps, lint | `/maintenance` |
| Process video | `/genpeli` |
| Technical AI decision | `/consult-engineering` |
| Business/strategy decision | `/consult-business` |
| Career/life decision | `/consult-personal` |
| Interview practice + scoring | `/interview-prep` |
| Project tracking, priorities, journal | `/notion` |
| Update Obsidian dashboard + project pages | `/obsidian` |

**When skills are NOT needed:** Quick file reads/edits, exploration, memory updates, project status, one-line fixes.

## Agent Dispatch

| Agent | Tool | Job |
|-------|------|-----|
| **Claude subagents** | `Agent(...)` tool | Research, analysis, deliberation, consultation |
| **Codex** | `codex exec` | Code implementation, test writing, lint fixes |
| **Gemini** | `gemini --yolo` | Cross-model code review + fix |

**Never use `claude -p` (CLI).** No tools, no file access, stalls with 0 bytes. The Agent tool replaced it.

## Behavior Rules

1. **Just do it** — no confirmation between cycles
2. **Stay responsive** — never block-wait on background tasks
3. **Report after each cycle** — what changed, what's next
4. **Backend first, frontend last** within cycles
5. **Commit style:** `feat:`, `fix:`, `chore:` prefixes + Co-Author-By trailer
6. **If a skill fails, fix the skill** — don't work around it with raw agents
