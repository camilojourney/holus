# Rules for ALL Holus Maintenance Agents

Before starting any work:
1. Read `AGENTS.md` in the repo root for project-wide rules
2. Read `.self-improvement/MEMORY.md` for system state
3. Read `.self-improvement/memory/lessons.json` to avoid past mistakes

After completing work:
1. Write a dated report to `.self-improvement/reports/<your-agent-name>/YYYY-MM-DD.md`
2. Append what you learned to `.self-improvement/memory/lessons.json`
3. If you found issues outside your scope, add them to `.self-improvement/NEXT.md`

Never:
- Push directly to main (use branches: `maint/<agent-name>-YYYY-MM-DD`)
- Use CLI tools (codex, claude, gemini) — write code directly
- Add new features (maintenance only)
- Modify files outside your declared scope
- Touch agent prompts in `src/holus/agents/*/prompts/`
- Modify config files (`config/guardrails.yaml`, `config/products.yaml`)

Note: The LangGraph domain agents (marketing, trading, content, coding, etc.) are the PRODUCT.
These maintenance agents maintain the CODEBASE. Do not confuse the two.
