# Project Configuration

## Philosophy
- Pythonic: type hints, dataclasses, protocols
- HTMX frontend, SQLite→PostgreSQL
- TDD: pytest >80% coverage
- Stub-then-fill workflow

## Stack
Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic, pytest, Playwright, ruff, mypy, Docker

## Standards
- Type hints mandatory
- Google docstrings with examples
- Line length: 100
- Logging not print
- Coverage: 80% minimum

## Workflow
1. Write signature + docstring + types
2. Write failing test
3. Implement minimal
4. Refactor
5. `pytest -v --cov=src --cov-fail-under=80`

## Commits
`type(scope): description` - types: feat, fix, refactor, test, docs, chore
