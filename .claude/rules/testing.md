# Testing Rules

## Framework
- pytest with pytest-asyncio for async tests
- pytest-cov for coverage reporting

## Structure
```
tests/
├── conftest.py          ← Shared fixtures
├── unit/
│   ├── core/            ← Tests for src/holus/core/
│   ├── agents/          ← Tests for src/holus/agents/
│   └── memory/          ← Tests for src/holus/memory/
├── integration/         ← Tests requiring Docker services
└── fixtures/            ← Test data files
```

## Rules
- Every module in src/ needs a corresponding test file
- Test file naming: `test_{module_name}.py`
- Test function naming: `test_{behavior_being_tested}`
- Use descriptive names: `test_kill_switch_blocks_agent_when_active` not `test_kill_switch_1`

## Mocking
- ALWAYS mock external services (Claude API, Redis, PostgreSQL, Alpaca, etc.)
- Use `pytest.fixture` for reusable mocks
- Mock at the boundary (e.g., mock `HolusClaudeClient`, not `anthropic.Anthropic`)
- Never mock the code under test — only its dependencies

## Assertions
- One logical assertion per test (multiple `assert` calls are fine if testing one behavior)
- Use `pytest.raises` for expected exceptions
- Include assertion messages for non-obvious checks

## Fixtures
- Shared fixtures live in `tests/conftest.py`
- Module-specific fixtures live in the test file
- Use `@pytest.fixture` with appropriate scope (function, module, session)

## Coverage
- Target: 80% coverage on core/ and memory/ modules
- Agents have lower coverage targets (60%) — integration testing matters more
- Never add tests just for coverage — test behaviors, not lines

## Running Tests
```bash
pytest tests/ -x -v              # All tests, stop on first failure
pytest tests/unit/ -v            # Unit tests only
pytest tests/integration/ -v     # Integration tests (requires Docker)
pytest --cov=holus tests/        # With coverage
```
