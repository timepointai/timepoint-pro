# Mechanism Coverage Strategy

## Current Status (4/17 Tracked - Phase 1 In Progress)

**Working Mechanisms:**
- ✅ M1: Heterogeneous Fidelity (`orchestrator.py:829, 918`)
- ✅ M3: Exposure Event Tracking (`orchestrator.py:766`)
- ✅ M4: Physics Validation (`validation.py:150`) **← NEW!**
- ✅ M17: Modal Temporal Causality (`orchestrator.py:1032`)

**Phase 1 Integration Status:**
- ✅ Full LangGraph workflow integrated into E2E runner
- ✅ M4 (Physics Validation) now tracked via workflow
- ⚠️ M2, M6, M11, M14 - Workflow nodes exist but hit implementation issues
- ⚠️ M7 - Already invoked but needs multi-timepoint template testing

## Missing Mechanisms (14/17)

### Category 1: Should Work But Don't (E2E Workflow Bypass Issue)

**Root Cause:** E2E runner (`e2e_workflows/e2e_runner.py:272-304`) bypasses the full LangGraph workflow that includes these mechanisms.

| Mechanism | Location | Required By | Fix |
|-----------|----------|-------------|-----|
| **M2** | Progressive Training | `workflows.py:200` | Integrate `retrain_high_traffic_entities()` into E2E runner |
| **M4** | Physics Validation | `validation.py:150` | Call validation in E2E workflow |
| **M6** | TTM Tensor Compression | `tensors.py:24` | Call `compress_tensors()` workflow step |
| **M7** | Causal Temporal Chains | `workflows.py:2214` | Already called via `generate_next_timepoint()` - should work with multi-timepoint templates |
| **M11** | Dialog Synthesis | `workflows.py:648` | Call `synthesize_dialog()` in E2E workflow |
| **M14** | Circadian Patterns | `validation.py:527` | Enable circadian validation in workflow |

### Category 2: Require Query Interface (Not Part of E2E)

**Root Cause:** These mechanisms are in `query_interface.py` and only invoked via queries, not during E2E generation.

| Mechanism | Location | Invoked By | Solution |
|-----------|----------|------------|----------|
| **M5** | Query Resolution | `query_interface.py:336, 648` | Create post-E2E query test suite |
| **M9** | On-Demand Generation | `query_interface.py:1197, 1204` | Query for non-existent entities |
| **M10** | Scene Entities | via `query_interface.py` | Query for scene/atmosphere |
| **M12** | Counterfactual Branching | `workflows.py:1419` | Submit "what if" queries |
| **M13** | Multi-Entity Synthesis | `workflows.py:966` | Query about multiple entities |

### Category 3: Require Special Entity Configurations

**Root Cause:** Need specific entity types or states in templates.

| Mechanism | Location | Requires | Template Needed |
|-----------|----------|----------|-----------------|
| **M8** | Embodied States | `workflows.py:533` | Entities with `pain_level > 0` or `fever > 38.5` |
| **M15** | Entity Prospection | `workflows.py:1186` | Call `generate_prospective_state()` - infrastructure exists but not actively invoked |
| **M16** | Animistic Entities | `workflows.py:2018` | `animism_level > 0` in config |

## Implementation Plan

### Phase 1: Fix E2E Workflow Integration ⭐ HIGH PRIORITY

**File:** `e2e_workflows/e2e_runner.py`

**Changes:**
1. Replace `_train_entities()` stub with full workflow integration
2. Add tensor compression step
3. Add validation step with circadian patterns
4. Add dialog synthesis step
5. Enable progressive training check

**Expected Coverage:** M2, M4, M6, M7, M11, M14 → **9/17 total**

### Phase 2: Create Query Interface Test Suite

**File:** `test_query_mechanisms.py` (NEW)

**Test Coverage:**
- M5: Query existing entities → lazy resolution elevation
- M9: Query non-existent entities → on-demand generation
- M10: Query for scene atmosphere
- M12: Submit counterfactual queries
- M13: Query about entity relationships

**Expected Coverage:** M5, M9, M10, M12, M13 → **14/17 total**

### Phase 3: Create Specialized Templates

**Files:** Add to `generation/config_schema.py`

1. **`example_hospital_crisis()` - For M8, M14**
   - Entity with chronic pain (`pain_level=0.7`)
   - Entity with fever (`fever=39.0`)
   - Time-sensitive decisions across circadian rhythm
   - **Mechanisms:** M8 (Embodied States), M14 (Circadian Patterns)

2. **`example_kami_shrine()` - For M16**
   - Animistic entities: shrine (building), kami (spirit), fox (animal)
   - `animism_level=6` (all types)
   - **Mechanisms:** M16 (Animistic Entities)

3. **`example_detective_prospection()` - For M15**
   - Detective modeling criminal's future moves
   - Explicit calls to `generate_prospective_state()`
   - **Mechanisms:** M15 (Entity Prospection)

**Expected Coverage:** M8, M14, M15, M16 → **17/17 total** ✅

## Template-to-Mechanism Mapping

### Existing Templates

| Template | Timepoints | Animism | Mechanisms Expected |
|----------|------------|---------|-------------------|
| `jefferson_dinner` | 1 | 0 | M1, M3, M17 ✅ |
| `board_meeting` | 3 | 0 | +M7 (multi-timepoint) |
| `sign_loops_cyclical` | 12 | 5 | +M7, M15, M16 |
| `scarlet_study_deep` | 1 | 3 | ALL 17 (with workflow fixes) |
| `hound_shadow_directorial` | 15 | 4 | +M7, M10, M14, M16 |
| `final_problem_branching` | 1 | 3 | +M12 (with queries) |

### New Templates Needed

| Template | Purpose | Primary Mechanisms |
|----------|---------|-------------------|
| `hospital_crisis` | Pain/illness + circadian | M8, M14 |
| `kami_shrine` | Full animistic entities | M16 |
| `detective_prospection` | Future modeling | M15 |

## Testing Strategy

### 1. Run Full E2E Test Suite
```bash
python test_all_templates.py
```
**Expected:** M1, M2, M3, M4, M6, M7, M11, M14, M17 = 9/17

### 2. Run Query Interface Tests
```bash
python test_query_mechanisms.py
```
**Expected:** +M5, M9, M10, M12, M13 = 14/17

### 3. Run Specialized Template Tests
```bash
python test_mechanism_tracking.py hospital_crisis
python test_mechanism_tracking.py kami_shrine
python test_mechanism_tracking.py detective_prospection
```
**Expected:** +M8, M15, M16 = **17/17 total** ✅

## Success Criteria

✅ **All 17 mechanisms tracked at least once** across the full test suite
✅ **Coverage matrix shows 17/17** in final report
✅ **Every template documents which mechanisms it invokes**
✅ **Automated tests verify coverage** on every autopilot run

## Phase 1 Results (Latest Test)

### ✅ **Successfully Integrated:**

**Code Changes:**
- ✅ `e2e_workflows/e2e_runner.py:272-343` - Replaced stub with full LangGraph workflow
- ✅ `e2e_workflows/e2e_runner.py:350-409` - Added dialog synthesis step
- ✅ `workflows.py:663-669` - Made dialog synthesis defensive (handle missing tensors)

**Test Results (run_20251023_102909_1ce3d7b5):**
```
Mechanisms Used: {'M4', 'M3', 'M17', 'M1'}
Total Mechanisms: 4/17 (was 3/17)
```

**What's Working:**
- ✅ M1 (Heterogeneous Fidelity)
- ✅ M3 (Exposure Event Tracking)
- ✅ M4 (Physics Validation) **← NEW!**
- ✅ M17 (Modal Temporal Causality)

### ⚠️ **Issues Found:**

**M2 (Progressive Training)** - Attempted but failed:
- Error: `UNIQUE constraint failed: entity.entity_id`
- Issue: Entity already exists in database (double-save issue)
- Fix needed: Prevent duplicate entity saves in workflow

**M6 (TTM Tensor Compression)** - Not tracked:
- Likely skipped due to workflow abortion
- Fix needed: Ensure workflow completes even with errors

**M11 (Dialog Synthesis)** - Fixed but skipped:
- Original error: `'NoneType' object has no attribute 'pain_level'`
- Fix applied: Made defensive - skips entities without tensors
- Issue: Entities from orchestrator don't have `physical_tensor`/`cognitive_tensor`
- Result: All entities skipped, no dialogs created

**M14 (Circadian Patterns)** - Not tracked:
- Validation node ran but didn't invoke circadian validation
- Fix needed: Ensure circadian validation is called with proper context

**M7 (Causal Temporal Chains)** - Already works:
- Just needs testing with multi-timepoint templates

## Next Steps

### Immediate (Fix Implementation Issues):

1. **Fix M2 (Progressive Training)**
   - Debug duplicate entity save issue in `progressive_training_check` node
   - Location: `workflows.py:38-61`, `resolution_engine.py`

2. **Fix M6 (TTM Tensor Compression)**
   - Ensure `compress_tensors` node completes
   - Add defensive checks for missing `entity.tensor` attribute
   - Location: `workflows.py:123-151`

3. **Fix M11 (Dialog Synthesis)**
   - Two options:
     a) Ensure entities created by orchestrator have tensor attributes, OR
     b) Enhance dialog synthesis to work with metadata-only entities
   - Location: `orchestrator.py` (entity creation) or `workflows.py:649-817`

4. **Fix M14 (Circadian Patterns)**
   - Ensure `compute_energy_cost_with_circadian()` is called during validation
   - Location: `validation.py:527`

5. **Test M7 (Causal Temporal Chains)**
   - Run E2E with multi-timepoint templates (board_meeting, sign_loops_cyclical)
   - Should already work via `TemporalAgent.generate_next_timepoint()`

### Then Continue:

6. Create Phase 2 - Query interface tests
7. Create Phase 3 - Specialized templates
8. Run full coverage test - Verify 17/17 ✅

**Target:** 9/17 mechanisms by end of Phase 1
