# CLEANUP.md - Refactoring & Cleanup Plan

**Status:** ✅ Completed
**Goal:** Reduce redundancy, clarify workflows, and remove "egregious self-testing" files while preserving the 17-mechanism system and E2E pipelines.

---

## 1. Changes Executed

### Phase 1: Eliminated Duplicates & Backups
**Deleted:**
- `orchestrator 2.py`
- `workflows 2.py`
- `llm_v2 2.py`
- `storage 2.py`
- `tensors 2.py`
- `test_branching_integration 2.py`
- `test_deep_integration 2.py`
- `test_phase3_dialog_multi_entity 2.py`
- `autopilot.py.old`
- `test_validation_system.py.old`
- `query_interface 2.py`

### Phase 2: Organized Test Suite
**Created Directory Structure:**
- `tests/mechanisms/` (Mechanism-specific tests)
- `tests/e2e/` (End-to-end pipeline tests)
- `tests/integration/` (Component integration tests)
- `tests/unit/` (Unit tests)

**Moves:**
- Moved ~60 `test_*.py` files from root to appropriate subdirectories.
- Updated `pytest.ini` to set `testpaths = tests`.
- Moved `pytest_test_tracker.py` to `tests/` and updated `conftest.py`.

### Phase 3: Cleaned Up Ad-Hoc Scripts
**Moves to `scripts/`:**
- `check_deps.py`, `verify_integration.py`, `check_openrouter_models.py`
- `clean-and-find-orphans.sh`, `fix_imports.sh`, `add_test_markers.py`
- `update_llm_paid_mode.py`, `validate_corporate_templates.py`
- `validate_profile_loading.py`, `verify_extraction.py`
- `install.sh`, `superclaude.sh`, `move-pdfs.sh`, `QUICKSTART.sh`

**Moves to `examples/`:**
- `demo_ai_entity.py`, `demo_orchestrator.py`, `demo.sh`
- `demo_portal_constitutional_convention.py`

**Moves to `scripts/legacy_runners/`:**
- `run_e2e_proof.py`, `run_character_engine.py`
- `run_constitutional_convention.py`, `run_single_template.py`
- `test_rig.py`, `autopilot.py`
- `run_complete_e2e_workflow.py`, `run_real_finetune.py`
- `run_vertical_finetune.py`, `run_vertical_training.py`
- `large-test-phase-1.sh`

**Deleted:**
- `run_tests.sh` (Redundant)
- `temp_cleanup_docs.sh`, `temp-remove-old-docs.sh`

---

## 2. Verification

**1. Mechanism Integrity**
`mechanism_dashboard.py --check-integrity` confirms:
- 18/17 Mechanisms tracked.
- Test tracking active (M5 confirmed perfect).
- Dashboard configuration updated to point to `tests/mechanisms/...`.

**2. E2E Pipeline**
`pytest tests/e2e/test_e2e_complete_pipeline.py` passed successfully.
- NL Interface -> Config -> Orchestrator -> Simulation -> Export verified.

**3. NL Integration**
`pytest tests/e2e/test_e2e_nl_integration.py` passed successfully.

---

## 3. New File Tree Overview

```text
/
├── .env
├── README.md
├── MECHANICS.md
├── run.sh                  # Main entry point
├── orchestrator.py         # Core logic
├── tests/                  # All tests
│   ├── mechanisms/
│   ├── e2e/
│   ├── integration/
│   └── unit/
├── scripts/                # Utility scripts
├── examples/               # Demo scripts
├── nl_interface/           # NL Interface module
├── workflows/              # E2E workflows
├── generation/             # World generation
├── metadata/               # Tracking
└── reporting/              # Reporting
```
