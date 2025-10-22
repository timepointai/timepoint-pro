# Timepoint-Daedalus Integration Plan

**Status**: Democking and Integration in Progress
**Date**: October 22, 2025
**Objective**: Transform system from test theater with mocks to validated real-LLM integration

---

## Executive Summary

**Current State**: System has sophisticated architecture (17 mechanisms, M1-M17) with comprehensive test files, BUT operates almost entirely in mock mode with no real LLM validation.

**Critical Findings from Audit**:
- ❌ **Test Theater Confirmed**: 0 E2E tests collect despite README claiming "70/70 tests passing (100%)"
- ❌ **Mock Mode Domination**: All 50 simulations produce identical mock data ("Test Scene", 3 entities, 3 timepoints)
- ❌ **LLM Service Default**: `LLM_SERVICE_ENABLED=false` causes system-wide mocking
- ❌ **Documentation Overstates**: Claims "Production Ready ✅" without real integration testing
- ❌ **Siloed Services**: Oxen integration works but receives mock data, not real simulation traces

**Verdict**: Architecturally sound but operationally unvalidated.

---

## What Works ✅

### Architecture & Code Quality
- 17 mechanisms (M1-M17) properly implemented
- Clean abstractions: LLM service with provider pattern, orchestrator with components
- Modular structure: llm_service/, oxen_integration/, generation/
- Type safety: Pydantic v2 schemas throughout (schemas.py: 544 lines)

### Mock/Dry-Run Functionality
- MockProvider returns consistent test data
- Orchestrator mocks correctly in isolation
- Test files execute without errors (in mock mode)
- Data formatters extract structure from simulation results

### Oxen Integration (Isolated)
- Upload successful to realityinspector/timepoint_finetune_production
- OxenClient works: authentication, dataset upload, commit creation functional
- File handling correct: JSONL format, proper serialization
- Fine-tune config valid: LoRA parameters, model selection, cost estimation

### Documentation Structure
- README.md exists with architecture overview
- MECHANICS.md complete documenting all 17 mechanisms
- USER_GUIDE.md present
- DATA_FORMATTER_IMPROVEMENTS.md documents recent improvements

---

## What Doesn't Work ❌

### 1. Test Theater (CORRECTION: Tests Do Collect)

**AUDIT CORRECTION**: Initial audit was incorrect about test collection.

**Actual Evidence**:
```bash
$ pytest test_e2e_autopilot.py --collect-only
collected 13 items  # 13 E2E tests properly configured

$ pytest --collect-only -q
458 tests collected  # Full test suite
```

**Updated Analysis**:
- ✅ E2E autopilot DOES collect 13 tests properly
- ✅ Test collection is NOT broken
- ⚠️ README claims "70/70 passing" but actual count is **458 tests** (understated, not overstated)
- ❌ Still true: System never tested end-to-end with real LLM (tests exist but run in mock mode)

**Test Markers Analysis**:
- 18 tests marked `@pytest.mark.llm` (require real LLM)
- Tests skip with: `pytest.skip("OPENROUTER_API_KEY not set - skipping real LLM test")`
- All LLM tests run in mock mode by default

### 2. Mock Mode Domination (CRITICAL)

**run_real_finetune.py execution output**:
```
⚠️  Warning: LLM_SERVICE_ENABLED=false, using mock mode
Running simulation 1/50...
   ✓ Title: Test Scene
   ✓ Entities: 3
   ✓ Timepoints: 3
...
Running simulation 50/50...
   ✓ Title: Test Scene  # IDENTICAL TO SIMULATION 1
   ✓ Entities: 3
   ✓ Timepoints: 3
```

**Problems**:
- All 50 "simulations" identical: Same mock data repeated 50 times
- No variation: HorizontalGenerator creates variations but orchestrator mocks them all
- Orchestrator always mocks: Returns `_mock_scene_specification()` in dry_run mode
- Training data is fake: Formatters extract from mock simulations, not real temporal traces

### 3. Siloed Service Integration (CRITICAL)

**Current Integration Flow**:
```
HorizontalGenerator (✅ creates variations)
         ↓
   Orchestrator (❌ mocks everything)
         ↓
   LLM Service (❌ dry_run=True)
         ↓
  Data Formatters (❌ extract from mocks)
         ↓
   Oxen Upload (✅ works but feeds on mock data)
```

**Problems**:
- Orchestrator doesn't use real LLM: `llm_client.dry_run=True` → mocks returned
- No LLM→Orchestrator validation: Never tested with real API calls
- Formatters can't distinguish: Extract from whatever simulation provides (mocks)
- Oxen integration isolated: Works but never receives real simulation data

### 4. Documentation Inaccuracy (CRITICAL)

**README.md False Claims**:
- "Production Ready ✅" - **FALSE**: Never tested in production mode
- "70/70 E2E tests passing (100%)" - **MISLEADING**: 0 E2E tests collect
- "All 17 core mechanisms implemented" - **TRUE** but only validated with mocks
- "Complete pipeline: NL → Simulation → Query → Report → Export" - **PARTIAL**: Pipeline exists but runs on mocks

**Missing Documentation** (Referenced but Not Found):
- PROOF_OF_INTEGRATION.md ❌
- E2E_INTEGRATION_COMPLETE.md ❌
- SPRINT1_COMPLETE.md ❌
- SPRINT2_COMPLETE_SUMMARY.md ❌
- SPRINT3_COMPLETE.md ❌

---

## Democking Changes (Completed) ✅

### 1. llm_v2.py - Reject Mock Mode by Default
**Changed**: Added validation in `__init__` to reject `dry_run=True` unless `ALLOW_MOCK_MODE=true`

```python
# VALIDATION: Reject dry_run mode unless explicitly testing
if dry_run and not os.getenv("ALLOW_MOCK_MODE"):
    raise ValueError(
        "Mock/dry-run mode is disabled by default. "
        "This system requires REAL LLM integration. "
        "Set ALLOW_MOCK_MODE=true ONLY for unit testing."
    )
```

### 2. run_real_finetune.py - Require Real LLM
**Changed**: Default from `LLM_SERVICE_ENABLED="false"` to `"true"`, added API key validation

```python
# REQUIRE real LLM service - no mock mode allowed
llm_enabled = os.getenv("LLM_SERVICE_ENABLED", "true").lower() == "true"
if not llm_enabled:
    print("❌ ERROR: LLM_SERVICE_ENABLED=false")
    print("   This script requires REAL simulations, not mocks.")
    return 1

if not os.getenv("OPENROUTER_API_KEY"):
    print("❌ ERROR: OPENROUTER_API_KEY not set")
    return 1
```

### 3. orchestrator.py - Remove Mock Fallback
**Changed**: SceneParser now raises RuntimeError instead of falling back to mocks

```python
def _call_llm_structured(self, prompt: str, response_model: type) -> Any:
    """Call LLM and parse structured response - REQUIRES REAL LLM"""

    # CRITICAL: Reject dry_run mode - no mocks allowed
    if self.llm.dry_run:
        raise RuntimeError(
            "Orchestrator requires REAL LLM integration. "
            "Mock mode is disabled."
        )

    try:
        # ... real LLM call ...
    except Exception as e:
        # DO NOT fall back to mocks - fail fast with clear error
        raise RuntimeError(
            f"Scene parsing failed: {e}\n"
            f"Orchestrator requires real LLM integration. Cannot proceed with mocks."
        ) from e
```

---

## Remaining Work (In Progress) ⏳

### Immediate Priority

#### 1. Fix E2E Test Collection
**Issue**: `pytest test_e2e_autopilot.py --collect-only` shows 0 items
**Actions**:
- [ ] Investigate pytest.ini configuration
- [ ] Check conftest.py for marker registration
- [ ] Verify test class/function naming conventions
- [ ] Ensure markers are properly registered: `@pytest.mark.e2e`
- [ ] Run full test suite with `-v` to see collection details

#### 2. Update README.md Accuracy
**Issue**: False claims about test passing rates and production readiness
**Actions**:
- [ ] Remove "Production Ready ✅" claim
- [ ] Correct test count (likely 25-30 unit tests, not 70)
- [ ] Add section: "Current Status: Integration in Progress"
- [ ] Remove references to non-existent documentation files
- [ ] Add disclaimer about real vs mock modes

#### 3. Validate 50 Simulations Are Unique
**Issue**: All simulations currently produce identical mock data
**Actions**:
- [ ] Run `run_real_finetune.py` with `LLM_SERVICE_ENABLED=true`
- [ ] Set `OPENROUTER_API_KEY` environment variable
- [ ] Verify each simulation has different:
  - Scene title (not all "Test Scene")
  - Entity IDs (not all test_entity_1, test_entity_2, test_entity_3)
  - Knowledge states (not all ["fact1", "fact2", "fact3"])
  - Timepoint events (not all identical descriptions)
- [ ] Log sample from simulation 1, 25, and 50 to verify variation
- [ ] Check data formatters extract real LLM-generated content

#### 4. Create Real Test Checklist (70 Tests)
**Issue**: Need to identify all tests and convert from mock to real validation
**Actions**:
- [ ] Audit all test files to count actual tests
- [ ] Identify tests marked `@pytest.mark.llm`
- [ ] Create checklist of which tests need real LLM
- [ ] Document skip patterns and remove them
- [ ] Set up CI/CD with gated real LLM calls
- [ ] Separate unit tests (mocks OK) from integration tests (real required)

### Secondary Priority

#### 5. Remove Outdated MD Files
**Issue**: Too many documentation files, some referenced but missing
**Actions**:
- [ ] Keep: README.md, MECHANICS.md, PLAN.md (this file)
- [ ] Remove: AUDIT.md (content now in PLAN.md)
- [ ] Remove: DATA_FORMATTER_IMPROVEMENTS.md (integrate into README)
- [ ] Remove: USER_GUIDE.md (consolidate into README)
- [ ] Remove or create: All referenced "COMPLETE" docs

#### 6. Data Quality Validation
**Actions**:
- [ ] Add checks in data formatters to detect mock data
- [ ] Fail training pipeline if mock content detected (test_entity_* patterns)
- [ ] Log sample data for manual inspection
- [ ] Verify formatters extract:
  - Real knowledge states (not ["fact1", "fact2", "fact3"])
  - Real relationships (not {"test_entity_2": "ally"})
  - Real energy costs (variable, not fixed 10.0)

#### 7. Integration Health Check Script
**Actions**:
- [ ] Create `scripts/health_check.py`
- [ ] Validate data flows: LLM → Orchestrator → Formatters → Oxen
- [ ] Check for mock patterns in output
- [ ] Verify API keys are set
- [ ] Test single simulation end-to-end
- [ ] Report integration status

---

## Test vs Reality Gap

| Claim | Reality | Status |
|-------|---------|--------|
| "70/70 E2E tests passing (100%)" | 0 E2E tests collected | ❌ FALSE |
| "Production Ready ✅" | Never tested with real LLM | ❌ MISLEADING |
| "All 17 core mechanisms implemented" | Implemented but only validated with mocks | ⚠️ PARTIAL |
| "Complete pipeline: NL → Simulation → Query → Report" | Pipeline exists but runs on mocks | ⚠️ PARTIAL |
| "Comprehensive test evidence" | Test files exist but don't validate real functionality | ❌ FALSE |

**Estimated Real Test Coverage**: 25-30 unit tests with mocks only (not 70)

---

## Integration Analysis

### Upstream Issues
1. **LLM Service → Orchestrator**: `dry_run` flag not properly propagated (NOW FIXED)
2. **Environment Configuration**: `LLM_SERVICE_ENABLED` defaulted to "false" (NOW FIXED)
3. **Test Fixtures**: `@pytest.mark.llm` tests skip when no API key (STILL BROKEN)

### Downstream Issues
1. **Data Formatters → Training Data**: Formatters extract from mock simulations
2. **Oxen Integration → Fine-Tuning**: Oxen receives valid JSONL but with mock content
3. **No End-to-End Validation**: No tests validate full pipeline with real LLM

---

## Risk Assessment

**If deployed as-is**:
- Fine-tuned model would learn mock patterns, not real temporal reasoning
- System behavior with real LLM is unknown
- Integration failures would only surface in production
- Claims of "Production Ready" would be false advertising

**Mitigation** (in progress):
- ✅ Democked llm_v2.py, run_real_finetune.py, orchestrator.py
- ⏳ Fix E2E test collection
- ⏳ Run real integration tests before claiming readiness
- ⏳ Update documentation to match reality

---

## Critical Path Forward

1. ✅ **Transparency First**: Create PLAN.md to document reality (THIS FILE)
2. ✅ **Demock Core Services**: llm_v2, orchestrator, run_real_finetune
3. ⏳ **Fix Test Collection**: Get E2E tests actually running
4. ⏳ **Enable Real Mode**: Validate with LLM_SERVICE_ENABLED=true
5. ⏳ **Validate Integration**: Run full pipeline with real LLM and verify output
6. ⏳ **Document Reality**: Update README to reflect current state

---

## Validation Checklist

### 50 Simulations Uniqueness (run_real_finetune.py)
- [ ] All 50 have different scene titles
- [ ] All 50 have different entity IDs
- [ ] All 50 have different knowledge states
- [ ] All 50 have different timepoint event descriptions
- [ ] No simulation contains "test_entity_" patterns
- [ ] No simulation contains ["fact1", "fact2", "fact3"] knowledge
- [ ] Energy costs are variable (not all 10.0)
- [ ] Relationship types are diverse (not all "ally")

### 458 Tests Reality Check (CORRECTED FROM "70")
- [x] Identify actual test count: **458 tests** (not 70)
- [x] Fix E2E test collection: **13 E2E tests collect properly**
- [ ] Remove skip patterns for `@pytest.mark.llm` tests
- [x] Configure pytest.ini with proper markers (already configured)
- [ ] Set up CI/CD with real LLM tests (gated on API key)
- [ ] Separate unit tests from integration tests (already separated with markers)
- [ ] Document which tests require real LLM vs mocks
- [ ] Run full suite and report actual passing count with real LLM

### Data Quality (Training Data Output)
- [ ] No "test_entity_" IDs in training examples
- [ ] No generic ["fact1", "fact2"] knowledge arrays
- [ ] Variable energy_spent values (not all 10.0)
- [ ] Real relationship types from graph (not just "unknown")
- [ ] Real knowledge_asymmetry in dialog examples
- [ ] Real co_present_entities lists (not templates)
- [ ] Real causal_parent references (not nulls)
- [ ] Temporal causality validated (no future references in past)

---

## Success Criteria

System is **truly production ready** when:

1. ✅ All core services democked (llm_v2, orchestrator, run_real_finetune)
2. ⏳ E2E test collection fixed and tests passing with real LLM
3. ⏳ All 50 simulations are unique (verified with real LLM)
4. ⏳ Training data contains real LLM-generated content (no mock patterns)
5. ⏳ README documentation is accurate (no false claims)
6. ⏳ Integration health check passes end-to-end
7. ⏳ Fine-tuning produces model trained on real temporal traces

**Current Progress**: 3/7 complete (43%)

**Democking Phase**: ✅ Complete
**Validation Phase**: ⏳ Requires OPENROUTER_API_KEY (see TEST_CHECKLIST.md)

---

## Next Immediate Steps (Require OPENROUTER_API_KEY)

1. ✅ ~~Fix E2E test collection~~ - 13 tests collect properly
2. ✅ ~~Update README.md~~ - Corrected to 458 tests, removed false claims
3. ⏳ Run run_real_finetune.py with real LLM (requires API key)
4. ⏳ Validate simulation uniqueness with `scripts/validate_simulations.py`
5. ✅ ~~Remove outdated MD files~~ - Kept only README, MECHANICS, PLAN, TEST_CHECKLIST
6. ⏳ Create integration health check script
7. ✅ ~~Document test coverage~~ - Created TEST_CHECKLIST.md (458 tests)

---

## Validation Tools Created

### scripts/validate_simulations.py
Validates training data for mock patterns:
```bash
python scripts/validate_simulations.py timepoint_training_data.jsonl
```

**Checks for**:
- Mock entity IDs (`test_entity_*`)
- Generic knowledge arrays (`["fact1", "fact2", "fact3"]`)
- Identical scene titles ("Test Scene")
- Simulation uniqueness

### TEST_CHECKLIST.md
Comprehensive test validation checklist:
- 458 tests categorized by type (E2E, LLM, Integration, Unit)
- Validation workflow (3 phases)
- Cost estimates ($3.30-$12.80 for full validation)
- CI/CD recommendations
- Pytest marker reference

**Usage**: Follow TEST_CHECKLIST.md phases 2-3 to validate with real LLM

---

**End of Plan**
