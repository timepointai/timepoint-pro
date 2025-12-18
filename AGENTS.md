# Project Configuration (AI Agent Reference)

## Philosophy
- Pythonic: type hints, dataclasses, protocols
- SQLite persistence (metadata/runs.db), FastAPI backend
- TDD: pytest with mechanism markers (M1-M19)
- SynthasAIzer paradigm: templates as "patches", ADSR envelopes for entity lifecycle

## Stack
Python 3.10+, FastAPI, Pydantic, pytest, ruff, mypy

## Standards
- Type hints mandatory
- Google docstrings with examples
- Line length: 100
- Logging not print
- Use `TemplateLoader` for template access (not deprecated `SimulationConfig.example_*()`)

## Key Commands
```bash
./run.sh list                    # List all 41 templates
./run.sh run board_meeting       # Run single template
./run.sh run --category core     # Run by category
./run.sh quick                   # Quick tier tests
```

## Testing
```bash
pytest -v -m synth               # SynthasAIzer tests
pytest -v -m mechanism           # All M1-M19 tests
pytest -v -m "m1 or m7"          # Specific mechanisms
```

## Commits
`type(scope): description` - types: feat, fix, refactor, test, docs, chore
