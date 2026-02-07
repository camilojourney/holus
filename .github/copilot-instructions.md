# GitHub Copilot Instructions

## Agent System

Load from `.ai/agents/`:
- Feature work: `@.ai/agents/builder.md`
- Deployment: `@.ai/agents/operator.md`
- Documentation: `@.ai/agents/communicator.md`
- Prioritization: `@.ai/agents/strategist.md`

## Standards

Apply these to all code:
- Python: `@.ai/standards/code/python.md`
- Python + LangChain/LangGraph: `@.ai/standards/code/langchain.md`
- Testing: `@.ai/standards/code/testing.md`
- API Design: `@.ai/standards/api/design.md`
- Security: `@.ai/standards/security/baseline.md`

## Core Rules

### Always
- Keep docs, specs, and context files aligned with shipped code

### Ask First
- Changes to production credentials, billing, or automation schedules

### Never
- Never bypass auth, rate limits, or audit logging controls

## Commands

- Install: `pip install -r requirements.txt`
- Dev: `python -m holus.main`
- Test: `python -m pytest tests/`
- Build: `No build step (runtime Python app)`
- Lint: `flake8 core/ agents/ tools/`

## More Context

See `AGENTS.md` for full agent definitions and `CLAUDE.md` for quick reference.
