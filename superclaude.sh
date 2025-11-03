#!/bin/bash
# superclaude.sh - Streamlined Claude Code Power User Setup
set -e

PROJECT_ROOT="$(pwd)"
CLAUDE_DIR="${PROJECT_ROOT}/.claude"
USER_CLAUDE_DIR="${HOME}/.claude"

mkdir -p "${CLAUDE_DIR}"/{agents,commands,hooks}
mkdir -p "${USER_CLAUDE_DIR}/agents"

# USER SETTINGS
cat > "${USER_CLAUDE_DIR}/settings.json" << 'EOF'
{"model":"claude-sonnet-4-5-20250929","permissions":{"deny":["Read(./.env)","Read(./.env.*)","Read(./secrets/**)"]}}`
EOF

# PROJECT SETTINGS
cat > "${CLAUDE_DIR}/settings.json" << 'EOF'
{"additionalContext":["tests/","docs/",".github/workflows/"]}
EOF

cat > "${CLAUDE_DIR}/settings.local.json" << 'EOF'
{"experimentalFeatures":{"parallelExecution":true}}
EOF

# CLAUDE.MD
cat > "${PROJECT_ROOT}/CLAUDE.md" << 'EOF'
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
EOF

# AGENT: pytest-expert
cat > "${USER_CLAUDE_DIR}/agents/pytest-expert.md" << 'EOF'
---
name: pytest-expert
description: Write comprehensive tests
tools: [read, write, bash]
---
AAA pattern. Fixtures for reusable data. Parametrize for scenarios. >80% coverage. Test happy + error paths.
EOF

# AGENT: git-workflow
cat > "${USER_CLAUDE_DIR}/agents/git-workflow.md" << 'EOF'
---
name: git-workflow
description: Git operations
tools: [bash, read]
---
Conventional commits: `type(scope): description`. Pre-commit: pytest, ruff, mypy, git diff.
EOF

# AGENT: code-reviewer
cat > "${USER_CLAUDE_DIR}/agents/code-reviewer.md" << 'EOF'
---
name: code-reviewer
description: Code reviews
tools: [read, bash]
---
Check: quality, types, tests >80%, security, performance, docs.
EOF

# AGENT: architect
cat > "${USER_CLAUDE_DIR}/agents/architect.md" << 'EOF'
---
name: architect
description: Architecture
tools: [read, write]
---
Layered: Routes→Services→Repositories. KISS, YAGNI, DRY.
EOF

# Set commands directory
COMMANDS_DIR="${CLAUDE_DIR}/commands"

# AGENT: debugger (project)
cat > "${CLAUDE_DIR}/agents/debugger.md" << 'EOF'
---
name: debugger
description: Debugging
tools: [read, write, bash]
---
1. Reproduce with test 2. Add logging 3. Find root cause 4. Fix 5. Regression test 6. Document
EOF

# COMMAND: test-driven
cat > "${COMMANDS_DIR}/test-driven.md" << 'EOF'
---
name: test-driven
description: TDD workflow
---
Feature: $ARGUMENTS

1. Write failing test 2. Minimal implementation 3. Pass 4. Refactor 5. `pytest -v --cov` 6. Commit
EOF

# COMMAND: fix-bug
cat > "${COMMANDS_DIR}/fix-bug.md" << 'EOF'
---
name: fix-bug
description: Bug fixing
---
Bug: $ARGUMENTS

1. Failing test 2. Root cause 3. Fix 4. Verify 5. Regression test 6. Commit
EOF

# COMMAND: review
cat > "${COMMANDS_DIR}/review.md" << 'EOF'
---
name: review
description: Code review
---
`ruff check . && mypy src/ && pytest --cov=src`
Review: quality, types, tests, security, performance, docs
EOF

# COMMAND: pre-commit
cat > "${COMMANDS_DIR}/pre-commit.md" << 'EOF'
---
name: pre-commit
description: Pre-commit
---
`ruff format . && ruff check . --fix && mypy src/ && pytest --cov=src --cov-fail-under=80`
Check: no debug code, no secrets, clear message
EOF

# COMMAND: refactor
cat > "${COMMANDS_DIR}/refactor.md" << 'EOF'
---
name: refactor
description: Refactoring
---
$ARGUMENTS

Tests exist→small changes→test each→commit. Extract methods, simplify, dedupe.
EOF

# PERMISSIONS
cat > "${CLAUDE_DIR}/PERMISSIONS.md" << 'EOF'
# Setup Permissions in Claude

```bash
/permissions allow bash(pytest *)
/permissions allow bash(python *)
/permissions allow bash(uv *)
/permissions allow bash(ruff *)
/permissions allow bash(mypy *)
/permissions allow bash(git status)
/permissions allow bash(git diff *)
/permissions allow bash(git add *)
/permissions allow bash(git commit *)
/permissions allow bash(docker *)
```

Or: `claude --dangerously-skip-permissions`
EOF

# GITIGNORE
[ ! -f "${PROJECT_ROOT}/.gitignore" ] && touch "${PROJECT_ROOT}/.gitignore"
grep -q ".claude/settings.local.json" "${PROJECT_ROOT}/.gitignore" 2>/dev/null || echo -e "\n.claude/settings.local.json\n.claude/*.log" >> "${PROJECT_ROOT}/.gitignore"

echo "✓ Complete! Run: cd ${PROJECT_ROOT} && claude"
echo "Commands: /test-driven /fix-bug /review /pre-commit /refactor"
echo "Agents: use subagent pytest-expert|git-workflow|code-reviewer|architect|debugger"
echo "See: .claude/PERMISSIONS.md"
