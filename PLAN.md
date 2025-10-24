# Timepoint-Daedalus Development Plan

**Project**: Temporal Knowledge Graph System with LLM-Driven Entity Simulation
**Status**: Active Development - Phase 8 Complete ✅
**Last Updated**: October 23, 2025

---

## Project Overview

Timepoint-Daedalus is a sophisticated framework for creating queryable temporal simulations where entities evolve through causally-linked timepoints with adaptive fidelity. The system implements 17 core mechanisms to achieve 95% cost reduction while maintaining temporal consistency.

**Current Status**: Phase 8 Complete - 90.6% Test Reliability (48/53 tests passing)
**Mechanism Coverage**: 17/17 decorators (100%), 7/17 pytest suites (41%)
**Technical Specification**: See [MECHANICS.md](MECHANICS.md) for detailed architecture
**Development Roadmap**: See sections below for completed phases and next steps

---

## Latest Completed Phase: Phase 8 - Tracking Infrastructure ✅

**Status**: Phase 8 Complete - All objectives met
**Next Phase**: Phase 9 (TBD - see Next Phases section for options)

---

## Completed Phases

### Phase 8: Tracking Infrastructure ✅

**Goal**: Establish comprehensive tracking infrastructure and automated monitoring

**Deliverables**:
1. ✅ Updated MECHANISM_COVERAGE_STRATEGY.md with Phase 7.5 results
2. ✅ Created mechanism_dashboard.py (automated coverage reporting)
3. ✅ Created PHASE_8_SUMMARY.md (comprehensive phase documentation)
4. ✅ Verified 100% decorator coverage (17/17 mechanisms)
5. ✅ Established automated health monitoring foundation

**Key Findings**:
- ALL 17/17 mechanisms have @track_mechanism decorators (100% coverage)
- 7/17 mechanisms have dedicated pytest test suites (41% pytest coverage)
- 10/17 mechanisms tested via E2E workflow templates
- mechanism_dashboard.py provides real-time coverage visibility

**Coverage Breakdown by Category**:
| Category | Mechanisms | Decorators | Pytest Tests |
|----------|-----------|------------|--------------|
| Entity State & Validation | 6 | 6/6 (100%) | 2/6 (33%) |
| Query Interface | 5 | 5/5 (100%) | 5/5 (100%) |
| Workflow & Temporal | 4 | 4/4 (100%) | 0/4 (0%) |
| Special Entity Types | 2 | 2/2 (100%) | 0/2 (0%) |
| **TOTAL** | **17** | **17/17 (100%)** | **7/17 (41%)** |

**Files Created**:
- mechanism_dashboard.py (NEW - 226 lines)
- PHASE_8_SUMMARY.md (NEW - 272 lines)
- MECHANISM_COVERAGE_STRATEGY.md (UPDATED - 315 lines)

**Success Metrics**:
- ✅ Test Reliability: 90.6% (exceeded 90% target)
- ✅ Decorator Coverage: 100% (17/17)
- ✅ Pytest Coverage: 41% (7/17)
- ✅ Documentation Complete
- ✅ Dashboard Functional

**Phase 8 Status**: ✅ COMPLETE

### Phase 7.5: Test Reliability Improvements ✅

**Goal**: Fix remaining test failures to achieve >90% pass rates before Phase 8 tracking

**Fixed 8 Critical Bugs**:
1. M12 schema mismatch - entity.timepoint column missing
2. M9 NoneType handling in generate_entity_on_demand()
3. M9 role inference prioritization (event context first)
4. M9 cache bypass for missing entities
5. M9 generate any missing entity (not just target_entity)
6. M5 query_count increment timing (moved before cache check)
7. M13 enumerate subscripting bug in detect_contradictions()
8. M13 datetime JSON serialization (2 locations in workflows.py)

**Removed ALL Mocks**: test_phase3_dialog_multi_entity.py now uses real implementations

**Test Results**:
| Test Suite | Before | After | Improvement |
|------------|--------|-------|-------------|
| M5 Query Resolution | 16/17 (94.1%) | 17/17 (100%) | +5.9% ✅ |
| M9 On-Demand Generation | 18/23 (78.3%) | 21/23 (91.3%) | +13% ✅ |
| M12 Counterfactual | 1/2 (50%) | 2/2 (100%) | +50% ✅ |
| M13 Multi-Entity | 4/11 (36.4%) | 8/11 (72.7%) | +36.3% ✅ |
| **OVERALL** | **38/53 (71.7%)** | **48/53 (90.6%)** | **+18.9%** ✅ |

**Files Modified**: 5 files (test_branching_integration.py, query_interface.py, workflows.py, test_phase3_dialog_multi_entity.py, test_m5_query_resolution.py)

**Phase 7.5 Status**: ✅ COMPLETE - Exceeded 90% test reliability target

### Phase 7: TTM Tensor Infrastructure ✅

### 📋 Completed in Phase 7:

**TTM Tensor Infrastructure - ALL SUCCESS CRITERIA MET** ✅

1. **Created `generate_ttm_tensor()` Function** ✅
   - Location: `tensors.py:130-214`
   - Extracts all 3 TTM components (context, biology, behavior)
   - Proper msgpack encoding with base64 JSON serialization

2. **Injected Tensor Generation Into Pipeline** ✅
   - `workflows.py:123-127` (aggregate_populations)
   - `query_interface.py:1289-1293` (generate_entity_on_demand)
   - `orchestrator.py:1246-1250` (_create_entities)
   - ALL entity creation paths now generate tensors

3. **Fixed Schema Validation** ✅
   - TTMTensor expects msgpack-encoded bytes
   - Implemented base64 encoding for JSON storage
   - Updated `compress_tensors()` deserialization (workflows.py:194-202)

4. **M6 Mechanism Tracked** ✅
   - Verified with `test_m6_quick.py`
   - 2 compressions tracked successfully
   - Coverage: 7/17 → **8/17 (47.1%)**

**Result**: M6 now fires for all entity types, TTM compression working, no "skipping tensor" warnings

**Phase 7 Status**: ✅ COMPLETE

### 📋 Completed in Phase 6:

**3/3 Critical Blockers Fixed:**

1. **UNIQUE Constraint Violations** ✅
   - Problem: `sqlite3.IntegrityError: UNIQUE constraint failed: entity.entity_id`
   - Root Cause: Entity has both `id` (primary key) and `entity_id` (unique). `session.merge()` caused INSERT instead of UPDATE
   - Fix: Rewrote `storage.py:19-51` with manual query-first upsert logic
   - Files Modified: `storage.py`

2. **JSON Markdown Wrapping** ✅
   - Problem: LLM responses wrapped in ```json ``` broke parsing
   - Root Cause: OpenRouter returns markdown-formatted responses
   - Fix: Created `strip_markdown_json()` helper in `query_interface.py:24-36`
   - Files Modified: `query_interface.py` (lines 143, 1255)

3. **Response Dict Access** ✅
   - Problem: `AttributeError: 'dict' object has no attribute 'choices'`
   - Root Cause: OpenRouterClient returns dict, not OpenAI object
   - Fix: Changed from `.choices[0]` to `["choices"][0]` dict access
   - Files Modified: `resolution_engine.py:281`, `llm.py:390`

### 📊 Test Results After Fixes:

| Test Suite | Before | After | Improvement | Status |
|------------|--------|-------|-------------|--------|
| M5 Query Resolution | 12/17 (70.6%) | **16/17 (94.1%)** | +23.5% | ✅ Excellent |
| M9 On-Demand Generation | N/A | **17/23 (73.9%)** | N/A | ⚠️ Good |
| M12 Counterfactual Branching | 0/2 (0%) | **2/2 (100%)** | +100% | ✅ Fixed |
| M13 Multi-Entity Synthesis | 0/11 (0%) | **4/11 (36.4%)** | +36.4% | ⚠️ Improving |

**Result**: Major improvement in M5 mechanism reliability, M12 fully fixed. Mechanism coverage unchanged (7/17 tracked).

**Phase 6 Status**: ✅ COMPLETE - All success criteria met

---

## Completed Phases

### Phase 1: Entity Lifecycle Fix ✅

**Problem**: Entity metadata from orchestrator destroyed during training workflow
**Fix**: Modified `workflows.py:72-126` (`aggregate_populations`) to preserve metadata
**Result**: Entities retain physical_tensor, circadian, prospection attributes through workflow

### Phase 2: Mock Infrastructure Removal ✅

**Scope**: Removed ALL mock/dry-run code from `llm.py` and `llm_v2.py`
**Result**: System enforces real OpenRouter LLM calls everywhere
**Files Modified**:
- `llm_v2.py` - Removed dry_run parameter, mock methods, ALLOW_MOCK_MODE
- `llm.py` - Removed dry_run parameter, mock methods, added API key validation

### Phase 3: Documentation Cleanup ✅

**Scope**: Aligned README.md and technical docs with real-LLM-only architecture
**Result**: Removed references to mock/dry-run modes
**Files Modified**: `README.md`, `MECHANICS.md`

### Phase 4: Test Infrastructure Fix ✅

**Scope**: Fixed dry_run parameter usages in 12 files
**Result**: All tests use real OpenRouter API integration
**Files Modified**: Test files + core files with dry_run dependencies

### Phase 5: Comprehensive Mechanism Testing ✅

**Scope**: Ran 5 template-based E2E tests + 5 pytest mechanism test suites
**Result**: Added M8, improved from 6/17 to 7/17 tracked mechanisms
**Discovery**: Identified 3 critical blockers (fixed in Phase 6)

---

## Working Requirements

### Environment

- **Python**: 3.10+ (verified on Python 3.10.16)
- **Platform**: macOS, Linux (tested on macOS 26.0.1)
- **Database**: SQLite (local file: `timepoint.db`, `metadata/runs.db`)

### Dependencies

**Core**:
```
hydra-core>=1.3.2
pydantic>=2.10.0
instructor>=1.7.0
httpx>=0.27.0          # OpenRouter API client
langgraph>=0.2.62
networkx>=3.4.2
sqlmodel>=0.0.22
numpy>=2.2.1
scipy>=1.15.0
```

**Testing**:
```
pytest>=8.3.4
pytest-cov>=6.0.0
pytest-asyncio>=0.25.2
hypothesis>=6.122.3
```

**Full list**: See `requirements.txt`

### Environment Variables

**Required**:
- `OPENROUTER_API_KEY` - OpenRouter API key for LLM calls

**Optional**:
- `LLM_SERVICE_ENABLED` - Defaults to `true` (can be set to `false` for testing)
- `OXEN_API_TOKEN` - For Oxen.ai data storage (fine-tuning workflows)
- `OXEN_TEST_NAMESPACE` - Default: "realityinspector"

### Installation

```bash
git clone https://github.com/yourusername/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here
```

---

## Mechanism Tracking Status

### Currently Tracked (8/17 - 47.1%):

| ID | Mechanism | Location | Firings | Status |
|----|-----------|----------|---------|--------|
| M1 | Entity Lifecycle Management | `orchestrator.py` | 42 | ✅ Tracked |
| M3 | Graph Construction & Eigenvector Centrality | `orchestrator.py` | 21 | ✅ Tracked |
| M4 | Tensor Transformation & Embedding | `validation.py` | 87 | ✅ Tracked |
| M6 | TTM Tensor Compression | `tensors.py` | 2 | ✅ Tracked |
| M7 | Causal Chain Generation | `workflows.py` | 10 | ✅ Tracked |
| M8 | Vertical Timepoint Expansion | `workflows.py` | 4 | ✅ Tracked |
| M11 | Dialog Synthesis | `workflows.py` | 25 | ✅ Tracked |
| M17 | Metadata Tracking System | `orchestrator.py` | 21 | ✅ Tracked |

**Data Source**: `metadata/runs.db` (mechanism_usage table)

### Implemented but Not Tracked (9/17):

| ID | Mechanism | Test Status | Blocker |
|----|-----------|-------------|---------|
| M2 | Progressive Training | Not tested | Needs multi-timepoint test coverage |
| M5 | Query Resolution | 16/17 (94.1%) | Cache hit prevents query_count increment |
| M9 | On-Demand Entity Generation | 17/23 (73.9%) | Role inference, cache hits, NoneType handling |
| M10 | Scene-Level Entity Management | Not tested | Test execution incomplete |
| M12 | Counterfactual Branching | 2/2 (100%) | Needs E2E tracking wrapper |
| M13 | Multi-Entity Synthesis | 4/11 (36.4%) | Mock object configuration issues |
| M14 | Cost-Aware Resolution | Not tested | Template doesn't trigger circadian logic |
| M15 | Oxen Integration | Not tested | ISO datetime format errors in templates |
| M16 | Animistic Entities | Not tested | Decorator placement verification needed |

---

## Test Execution

### Run Mechanism Tests

```bash
# Run all tests
pytest -v

# Specific mechanism tests
pytest test_m5_query_resolution.py -v              # M5: 94.1% passing
pytest test_m9_on_demand_generation.py -v          # M9: 73.9% passing
pytest test_branching_integration.py -v            # M12: 50% passing
pytest test_phase3_dialog_multi_entity.py -v       # M13: 27.3% passing

# Run template-based tests
python run_all_mechanism_tests.py
```

### Current Test Results

**M5 Query Resolution** (16/17 - 94.1%):
- ✅ Query history tracking working
- ✅ Lazy elevation working
- ✅ Resolution engine working
- ❌ Query count increment (cache hit issue)

**M9 On-Demand Generation** (17/23 - 73.9%):
- ✅ Entity gap detection
- ✅ Basic generation
- ✅ Persistence
- ❌ Role inference specificity
- ❌ Query trigger integration (cache hits)
- ❌ Timepoint context (NoneType errors)
- ❌ Physical tensor generation (JSON parsing)

**M12 Counterfactual Branching** (1/2 - 50%):
- ✅ Basic branching working
- ❌ Schema mismatch (`entity.timepoint` column doesn't exist)

**M13 Multi-Entity Synthesis** (3/11 - 27.3%):
- ✅ Body-mind coupling tests passing
- ❌ Mock object `.engine` attribute missing
- ❌ Mock objects not subscriptable

---

## Next Phases

### Phase 9: Option A - Complete Pytest Coverage 📋 (3-5 days)

**Goal**: Create pytest test suites for all remaining mechanisms

**Scope**:
- Create pytest suites for 10 remaining mechanisms (M1, M2, M3, M4, M6, M7, M8, M11, M14, M15, M16, M17)
- Target: 17/17 pytest coverage (100%)
- Maintain >90% test reliability

**Success Criteria**:
- [ ] All 17 mechanisms have dedicated pytest test suites
- [ ] Test reliability remains >90%
- [ ] Comprehensive coverage documentation

### Phase 9: Option B - Template Validation 📋 (1-2 days)

**Goal**: Verify all mechanisms fire via existing template workflows

**Scope**:
- Run comprehensive template suite (jefferson_dinner, board_meeting, hospital_crisis, kami_shrine, detective_prospection)
- Analyze mechanism firing logs
- Verify 17/17 mechanisms active in template workflows

**Success Criteria**:
- [ ] All 17 mechanisms verified firing via templates
- [ ] Template execution logs documented
- [ ] Mechanism usage patterns analyzed

### Phase 9: Option C - Performance Optimization 📋 (2-3 days)

**Goal**: Optimize high-frequency mechanisms

**Scope**:
- Profile mechanism execution times
- Identify performance bottlenecks
- Optimize hot paths in M1, M3, M4, M5, M9

**Success Criteria**:
- [ ] Execution time reduced by 20%
- [ ] No degradation in test reliability
- [ ] Performance benchmarks documented

### Phase 10: LLM Client Consolidation 📋 (2-3 days)

**Goals**:
1. Consolidate `llm.py` and `llm_v2.py`
2. Choose `llm_v2.py` as winner (better architecture)
3. Update ~36 files with import changes
4. Delete `llm.py`
5. Rename `llm_v2.py` → `llm.py`
6. Re-verify 17/17 mechanism coverage

**Why After Phase 9**: Lower risk to refactor from validated working state

**Success Criteria**: Single LLM client, all tests passing, 17/17 mechanisms maintained

---

## Known Issues & Technical Debt

### Critical Issues (Phase 7.5 Priority)

1. **M9 Test Failures** (6 tests - 26% failure rate)
   - Role inference too strict
   - Cache hits prevent query triggers
   - NoneType handling in timepoint context
   - JSON parsing errors in physical tensor generation
   - **Priority**: Fix before Phase 8 tracking

2. **M13 Mock Configuration** (7 tests - 64% failure rate)
   - Mock objects missing `.engine` attribute
   - Mock objects not properly subscriptable
   - Need to properly configure test mocks
   - **Priority**: Fix before Phase 8 tracking

3. **M5 Cache Hit Issue** (1 test)
   - Query count doesn't increment on cache hit
   - Non-blocking for mechanism functionality
   - **Priority**: Minor fix for 100% pass rate

### Minor Issues (Phase 8+)

1. **Template Configuration Errors**
   - ISO datetime format issues in `detective_prospection`
   - ISO datetime format issues in `board_meeting`

2. **Decorator Placement Verification**
   - M16 animistic entity tracking didn't fire
   - M14 circadian/cost-aware logic not triggered
   - Need to verify `@track_mechanism` placement

### Technical Debt

1. **Dual LLM Clients**
   - `llm.py` and `llm_v2.py` coexist
   - Import confusion across ~36 files
   - Plan: Consolidate in Phase 9

2. **Test Isolation**
   - Some tests share database state
   - Consider per-test database fixtures

3. **Documentation**
   - MECHANICS.md claims "17/17 implemented" (updated to reflect 7/17 tracked)
   - README.md now reflects accurate status

---

## Success Criteria

### Phase 6 ✅
- [x] Fix 3 critical blockers
- [x] M5 > 90% test pass rate (achieved 94.1%)
- [x] M9 > 70% test pass rate (achieved 73.9%)
- [x] Update documentation to reflect accurate status

### Phase 7 ✅
- [x] Create generate_ttm_tensor() function
- [x] Inject tensor generation into all entity creation paths
- [x] Fix TTM schema validation (msgpack + base64)
- [x] M6 mechanism tracked
- [x] Coverage increased to 8/17 (47.1%)

### Phase 7.5 ✅
- [x] M5 > 95% test pass rate (17/17 tests - 100%)
- [x] M9 > 85% test pass rate (21/23 tests - 91.3%)
- [x] M13 > 60% test pass rate (8/11 tests - 72.7%)
- [x] All critical issues resolved

### Phase 8 ✅
- [x] 17/17 mechanisms with decorators (100%)
- [x] Overall test reliability > 90% (achieved 90.6%)
- [x] Automated coverage dashboard created
- [x] Comprehensive phase documentation

### Phase 9 (TBD)
- [ ] Option A: Complete pytest coverage for all 17 mechanisms
- [ ] Option B: Validate all mechanisms via template workflows
- [ ] Option C: Performance optimization and profiling

### Phase 10
- [ ] Single LLM client (`llm.py`)
- [ ] All imports updated (~36 files)
- [ ] All tests passing
- [ ] 17/17 mechanisms maintained

### Project Completion
- [ ] 17/17 mechanisms tracked and tested
- [ ] All test suites > 90% pass rate
- [ ] Documentation accurate and complete
- [ ] Technical debt minimized
- [ ] System ready for production use

---

## Quick Reference

### Key Files

- **PLAN.md** (this file) - Development roadmap and current status
- **MECHANISM_COVERAGE_STRATEGY.md** - Detailed test results and tracking data
- **MECHANICS.md** - Technical specification (17 mechanisms)
- **README.md** - Quick start and user documentation

### Key Commands

```bash
# Run specific mechanism tests
pytest test_m5_query_resolution.py -v
pytest test_m9_on_demand_generation.py -v
pytest test_branching_integration.py -v
pytest test_phase3_dialog_multi_entity.py -v

# Run template-based tests
python run_all_mechanism_tests.py

# Query mechanism tracking database
sqlite3 metadata/runs.db "SELECT * FROM mechanism_firings;"

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
```

### Contact & Support

For questions or issues, see project documentation or open a GitHub issue.

---

**Last Updated**: October 23, 2025
**Current Status**: Phase 8 Complete ✅
**Test Reliability**: 90.6% (48/53 tests passing)
**Mechanism Coverage**: 17/17 decorators (100%), 7/17 pytest suites (41%)
**Next Phase**: Phase 9 (see Next Phases section for options)
