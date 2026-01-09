# Project Configuration (AI Agent Reference)

## Philosophy
- Pythonic: type hints, dataclasses, protocols
- SQLite persistence (metadata/runs.db for runs, timepoint.db for temp), FastAPI backend
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
./run.sh run <template> --portal-simjudged-quick  # Portal mode with sim-judging
./run.sh run <template> --portal-quick           # Portal quick mode (5 steps)
```

## Testing
```bash
pytest -v -m synth               # SynthasAIzer tests
pytest -v -m mechanism           # All M1-M19 tests
pytest -v -m "m1 or m7"          # Specific mechanisms
```

## Recent Fixes (January 2026)

### Portal Mode Enhancements
- **Preserve All Paths**: `preserve_all_paths=True` returns ALL generated paths (not just top N) for full analysis
- **Divergence Detection**: Identifies where paths diverge with clustering analysis (`high_coherence`, `medium`, `low`)
- **Quick Mode**: `--portal-quick` reduces backward_steps to 5 for fast demos (~15 min vs 1+ hour)
- **Fidelity Scaling**: Templates now scale proportionally with backward_steps (no longer hardcoded)

**Files:** `workflows/portal_strategy.py`, `workflows/temporal_agent.py`, `run_all_mechanism_tests.py`, `run.sh`

### Entity Inference in Portal Mode
Portal mode now infers `entities_present` for each timepoint using LLM-based entity identification instead of blind copying from consequent timepoints.

**Files:** `workflows/temporal_agent.py:_infer_entities_for_timepoint()`, `workflows/portal_strategy.py:_infer_entities_from_description()`

### Data Quality Validation
Added `_run_data_quality_check()` in e2e_runner.py that validates:
- All timepoints have non-empty `entities_present`
- All entity references point to existing entities
- No duplicate entity IDs

### Entity Persistence to Shared DB
Entities now sync to metadata/runs.db alongside timepoints for convergence analysis.

**Files:** `e2e_workflows/e2e_runner.py:_persist_entity_for_convergence()`, `_persist_all_entities_for_convergence()`

### Timepoint Validation Warning
`schemas.py:Timepoint.__init__()` now emits `UserWarning` when `entities_present` is empty.

### Template Name Normalization
Template names now accept both slash and underscore formats interchangeably:
- `./run.sh run portal/startup_unicorn` works the same as
- `./run.sh run portal_startup_unicorn`

**Files:** `run_all_mechanism_tests.py:run_single_template()`

## Commits
`type(scope): description` - types: feat, fix, refactor, test, docs, chore
