# .codex Directory

This directory provides compatibility with Codex-based AI tools (if you use them).

## Current Structure

```
.codex/
├── README.md     (this file)
├── prompts/      → symlink to ../.ai/workflows/
└── skills/       → symlink to ../.ai/agents/
```

## Symlink Strategy

Rather than duplicating content, we use symlinks to point to the single source of truth:

- **`prompts/`** → Points to `.ai/workflows/` (ship-feature, investigate-bug, etc.)
- **`skills/`** → Points to `.ai/agents/` (builder, operator, communicator, strategist)

## Single Source of Truth

All edits should be made in the `.ai/` folder:

| .codex/ path | Actual location |
| --- | --- |
| `prompts/*` | `.ai/workflows/*.md` |
| `skills/*` | `.ai/agents/*.md` |

## Why Symlinks?

Different AI tools look in different locations. Rather than maintaining separate copies, we:

1. Keep everything in `.ai/` (single source of truth)
2. Create symlinks from tool-specific folders
3. Edit once, applies everywhere

## Verification

To verify symlinks are working:

```bash
ls -la .codex/
# Should show symlinks (marked with ->)
```

## If You Don't Use Codex

If you don't use Codex-based tools, you can safely delete this directory:

```bash
rm -rf .codex/
```

The framework will work perfectly without it.
