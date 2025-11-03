---
name: pre-commit
description: Pre-commit
---
`ruff format . && ruff check . --fix && mypy src/ && pytest --cov=src --cov-fail-under=80`
Check: no debug code, no secrets, clear message
