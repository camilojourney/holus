# Changelog

All notable changes to the AI development framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-07

### Added
- Initial framework structure with `.ai/` folder
- 4 consolidated agents: Builder, Operator, Communicator, Strategist
- Comprehensive failure modes & recovery for each agent
- Decision boundaries matrix with concrete examples
- Standards for code, API, security, and communications
- Workflows for ship-feature, investigate-bug, customer-feedback, weekly-ops
- Progressive context loading system
- Output templates for consistent artifacts
- 7-phase playbook system (0-bootstrap through 6-fix-iterate)
- Version tracking (`.version` + `CHANGELOG.md`)

### Framework Philosophy
- 80/20 rule: 80% effort on tasks, 20% on agents
- Single source of truth in `.ai/` folder
- Standards = lintable, Agents = judgment
- Progressive disclosure to respect 150-200 instruction ceiling
- Tool-agnostic via AGENTS.md universal standard

---

## How to Update

When rules change:

1. **Update the file** (e.g., `.ai/agents/builder.md`)
2. **Bump version** in `.ai/.version`:
   - MAJOR: Breaking changes (agent responsibilities rewritten)
   - MINOR: New agents, standards, or workflows
   - PATCH: Typo fixes, clarifications
3. **Document change** in this CHANGELOG
4. **Commit with message**: `chore(ai): bump to v1.1.0 - add context hygiene rules`

---

## Version History Template

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature or file added

### Changed
- Existing functionality modified

### Deprecated
- Soon-to-be removed features

### Removed
- Deleted features or files

### Fixed
- Bug fixes in rules or templates

### Security
- Security-related changes
```

---

## Future Planned Changes

Track planned improvements here:

- [ ] Add example workflows for common frameworks (Django, Rails, Express)
- [ ] Add specialized agents for data science projects
- [ ] Add integration examples for popular MCP servers
- [ ] Add automated validation scripts
