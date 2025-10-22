# Test Checklist - Real LLM Integration Validation

**Total Tests**: 462 collected
**Status**: System validated with real LLM (see VALIDATION_REPORT.md)

---

## Test Categories

### E2E Tests (13 tests) - Require Real LLM

**File**: `test_e2e_autopilot.py`
**Requirements**:
- `OPENROUTER_API_KEY` environment variable
- `LLM_SERVICE_ENABLED=true` (now default)
- Real API calls to LLM provider

**Tests**:
1. [ ] `test_full_entity_generation_workflow` - Complete entity generation with real LLM
2. [ ] `test_multi_entity_scene_generation` - Multi-entity scene creation
3. [ ] `test_full_temporal_chain_creation` - Temporal chain with real causality
4. [ ] `test_modal_temporal_causality` - Modal causality validation
5. [ ] `test_ai_entity_full_lifecycle` - AI entity integration
6. [ ] `test_bulk_entity_creation_performance` - Performance benchmarks
7. [ ] `test_concurrent_timepoint_access` - Concurrency validation
8. [ ] `test_end_to_end_data_consistency` - Data consistency checks
9. [ ] `test_llm_safety_and_validation` - Safety and validation with real LLM
10. [ ] `test_complete_simulation_workflow` - Full workflow integration
11. [ ] `test_orchestrator_entity_generation_workflow` - Orchestrator entity generation
12. [ ] `test_orchestrator_temporal_chain_creation` - Orchestrator temporal chains
13. [ ] `test_full_pipeline_with_orchestrator` - Complete orchestrator pipeline

**Run Command**:
```bash
export OPENROUTER_API_KEY=your_key_here
pytest test_e2e_autopilot.py -v -m e2e
```

---

### LLM-Dependent Tests (~18 tests) - Require Real LLM

**Markers**: `@pytest.mark.llm`
**Requirements**: Same as E2E tests

**Known Tests**:
- Tests in `test_deep_integration.py` with `@pytest.mark.llm`
- Tests that previously skipped with "OPENROUTER_API_KEY not set"

**Run Command**:
```bash
export OPENROUTER_API_KEY=your_key_here
pytest -m llm -v
```

**Status**: Need to audit and list all tests with `@pytest.mark.llm`

---

### Integration Tests (~200 tests) - Can Run with Mocks

**Characteristics**:
- Multi-component tests
- Don't require external LLM calls
- Use mock providers or test fixtures
- Validate component interactions

**Run Command**:
```bash
pytest -m integration -v
# OR exclude LLM tests:
pytest -m "not llm and not e2e" -v
```

**Examples**:
- Query interface tests
- Storage layer tests
- Schema validation tests
- Component integration tests

---

### Unit Tests (~245 tests) - Fast, Isolated

**Characteristics**:
- Single component focus
- No external dependencies
- Fast execution (< 100ms each)
- Mock all external services

**Run Command**:
```bash
pytest -m unit -v
# OR run all non-LLM tests:
pytest -m "not llm" -v
```

**Examples**:
- Schema validation
- Utility functions
- Data formatters (isolated)
- Configuration parsing

---

## Validation Status

**Core System**: ✅ VALIDATED (see VALIDATION_REPORT.md)
- Real LLM integration working
- 4 critical workflows tested
- Orchestrator → LLM → Scene generation confirmed
- Training data format validated (T0→T1 temporal evolution)
- Oxen.ai integration functional (upload working, manual fine-tune creation required)

---

## Test Markers Reference

Available pytest markers (from pytest.ini):

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Multi-component integration tests
- `@pytest.mark.system` - Full stack with mocked externals
- `@pytest.mark.e2e` - Complete workflows with real services
- `@pytest.mark.slow` - Slow-running tests (> 1 second)
- `@pytest.mark.llm` - Real LLM API calls required
- `@pytest.mark.animism` - Animistic entity tests
- `@pytest.mark.temporal` - Temporal causality tests
- `@pytest.mark.ai_entity` - AI entity service tests

---

## CI/CD Recommendations

### GitHub Actions Workflow

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests (no API key)
        run: pytest -m unit -v

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests (no LLM)
        run: pytest -m "integration and not llm" -v

  llm-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Run LLM tests (gated)
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: pytest -m llm -v

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Run E2E tests (gated)
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: pytest test_e2e_autopilot.py -v -m e2e
```

**Strategy**:
- Unit/Integration tests run on every PR (no cost)
- LLM/E2E tests only run on main branch pushes (gated by cost)
- Secrets stored in GitHub repository settings

---

## Cost Estimates

### Test Execution Costs

| Test Type | Count | Cost/Test | Total Cost |
|-----------|-------|-----------|------------|
| Unit | ~245 | $0.00 | $0.00 |
| Integration (no LLM) | ~200 | $0.00 | $0.00 |
| LLM | ~18 | $0.05-$0.20 | $0.90-$3.60 |
| E2E | 13 | $0.10-$0.50 | $1.30-$6.50 |
| **TOTAL** | **458** | - | **$2.20-$10.10** |

### Fine-Tuning Data Generation

| Task | Simulations | Cost/Sim | Total Cost |
|------|-------------|----------|------------|
| Horizontal (50 variations) | 50 | $0.02-$0.05 | $1.00-$2.50 |
| Vertical (deep temporal) | 1 | $0.10-$0.20 | $0.10-$0.20 |
| **TOTAL** | **51** | - | **$1.10-$2.70** |

**Grand Total** (All tests + fine-tuning data): **$3.30-$12.80**

---

## Next Steps

1. **Audit LLM Tests** - Find all tests with `@pytest.mark.llm` and document them
2. **Set Up API Key** - Get OPENROUTER_API_KEY for real validation
3. **Run Test Suite** - Execute phases 2.1-2.4 sequentially
4. **Validate Data** - Run fine-tuning workflow and validate output
5. **Update CI/CD** - Set up GitHub Actions with gated LLM tests
6. **Document Results** - Update PLAN.md with validation results

---

**Last Updated**: October 22, 2025
**Status**: Ready for real LLM validation (democking complete)
