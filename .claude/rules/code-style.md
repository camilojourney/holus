# Code Style Rules

## Python Version
- Target: Python 3.12+
- Use modern syntax: `X | Y` unions, `match` statements, f-strings

## Type Hints
- ALWAYS use type hints on function signatures
- Use `from __future__ import annotations` for forward references
- Prefer `str | None` over `Optional[str]`
- Use TypedDict for LangGraph state, dataclass for data models, Pydantic for validation

## Data Structures
- Use `@dataclass` for internal data transfer objects
- Use Pydantic `BaseModel` for anything crossing system boundaries (API, config, events)
- Use `TypedDict` for LangGraph state definitions
- Never use plain dicts for structured data — always define a type

## Logging
- Use `structlog` exclusively (never `print()` or stdlib `logging`)
- Bind `agent_name` to every logger at agent initialization
- Log structured data (dicts), not formatted strings
- Log levels: DEBUG for internals, INFO for actions, WARNING for recoverable issues, ERROR for failures

## Error Handling
- Define specific exception classes per module (e.g., `KillSwitchActiveError`, `TradeRejectedError`)
- Never catch bare `Exception` — catch specific types
- Always include context in error messages (agent_id, task_id, relevant state)
- Never expose internal errors to external APIs — wrap them

## Imports
- Group: stdlib → third-party → local, separated by blank lines
- Use absolute imports from `holus.` prefix
- Never use wildcard imports (`from x import *`)

## Naming
- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_`

## Line Length
- Maximum: 100 characters (configured in ruff)
