# Quick Fix for Test Dependencies

## The Problem

You're running pytest outside the Poetry environment where dependencies are installed. The test dependencies (pytest, bleach, sqlmodel, hydra-core) need to be installed.

## Solution 1: Use Poetry (Recommended)

Since you have Poetry installed, use it to manage dependencies:

```bash
# Install all dependencies including test deps
poetry install --with dev

# Run tests through Poetry
poetry run pytest -m e2e -v

# Or activate Poetry shell first
poetry shell
pytest -m e2e -v
```

## Solution 2: Use the Test Runner Script

I've created a unified test runner that handles the environment automatically:

```bash
# Run all E2E tests
./run_tests.sh -m e2e -v

# Run all tests
./run_tests.sh -v

# Run specific test
./run_tests.sh tests/test_e2e_autopilot.py -v
```

## Solution 3: Manual venv

If you prefer not to use Poetry:

```bash
# Create and activate venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-test.txt

# Run tests
pytest -m e2e -v
```

## What I Fixed

1. **Updated pyproject.toml** - Added missing test dependencies to `[tool.poetry.group.dev.dependencies]`:
   - pytest, pytest-asyncio, pytest-cov, pytest-mock
   - bleach, python-dotenv

2. **Created run_tests.sh** - Unified test runner that:
   - Detects Poetry or venv
   - Installs dependencies automatically
   - Runs pytest in correct environment

3. **Updated requirements-test.txt** - Already had all dependencies listed

## Recommended Command

```bash
poetry install --with dev && poetry run pytest -m e2e -v
```

This ensures all dependencies are installed and tests run in the correct environment.

## Why This Happened

The error occurred because you were using the system Python (`/opt/homebrew/opt/python@3.10/bin/python3.10`) which doesn't have the project dependencies installed. Poetry manages a separate virtual environment with all dependencies isolated.
