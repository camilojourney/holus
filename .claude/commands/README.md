# Claude Commands

This directory is for custom Claude Code commands (optional).

Commands are reusable prompt templates that can be invoked with `/command-name`.

## Example Command

Create a file like `review.md`:

```markdown
# Code Review

Review the following code for:
- Security issues
- Performance problems
- Code quality
- Best practices

Follow the standards in `.ai/standards/`
```

Then invoke with: `/review`

## Using Workflows Instead

For multi-step processes, use workflows in `.ai/workflows/` instead.
These are accessible via AGENTS.md and don't require Claude-specific setup.
