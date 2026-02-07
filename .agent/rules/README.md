# .agent Directory

This directory provides compatibility with AI tools that support the `.agent/` folder structure (e.g., Google Antigravity, Windsurf, other agent-based tools).

## Structure

```
.agent/
├── rules/          # Code and security rules
│   ├── README.md    (this file)
│   ├── security.md  → References .ai/standards/security/
│   └── style.md     → References .ai/standards/code/
├── workflows/      # Process workflows
│   └── deploy.md    → References .ai/workflows/
└── skills/         # Custom agent skills
    └── (custom)     → References .claude/skills/ or .ai/
```

## Single Source of Truth: `.ai/` Folder

**All files in `.agent/` are references** to the main `.ai/` folder where everything is controlled:

| .agent/ file | Points to |
|--------------|-----------|
| `rules/security.md` | `.ai/standards/security/baseline.md` |
| `rules/style.md` | `.ai/standards/code/` |
| `workflows/deploy.md` | `.ai/workflows/` + `.ai/agents/operator.md` |
| `skills/*` | `.claude/skills/` or custom implementations |

## Why This Structure?

Different AI tools look in different locations:
- **Claude Code** → `.claude/`, `CLAUDE.md`
- **GitHub Copilot** → `.github/copilot-instructions.md`, `.github/instructions/`
- **Antigravity/Windsurf** → `.agent/`
- **Universal** → `AGENTS.md`, `.ai/`

Rather than duplicating content, we maintain one source (`.ai/`) and create lightweight reference files in tool-specific locations.

## Editing Rules

✅ **DO:** Edit files in `.ai/` folder
❌ **DON'T:** Edit files in `.agent/` (they're just pointers)

## Custom Skills

If you create custom agent skills for tools that use `.agent/skills/`, create them in `.claude/skills/` first, then reference them here.
