# Testing Guide for Timepoint-Daedalus

Comprehensive testing documentation for the unified test system.

## Table of Contents

1. [Test Hierarchy](#test-hierarchy)
2. [Running Tests](#running-tests)
3. [Test Organization](#test-organization)
4. [Markers and Filtering](#markers-and-filtering)
5. [Fixtures and Shared Resources](#fixtures-and-shared-resources)
6. [LLM Testing](#llm-testing)
7. [Writing New Tests](#writing-new-tests)
8. [CI/CD Integration](#cicd-integration)

---

## Test Hierarchy

The test suite is organized into four levels:

### 1. Unit Tests (`@pytest.mark.unit`)
- **Purpose**: Test individual functions and classes in isolation
- **Speed**: < 100ms per test
- **Dependencies**: No external dependencies, mocked storage/LLM
- **Example**: Testing a single validation function

```bash
pytest -m unit  # Run all unit tests
```

### 2. Integration Tests (`@pytest.mark.integration`)
- **Purpose**: Test multiple components working together
- **Speed**: < 5 seconds per test
- **Dependencies**: Real storage (temp DB), mocked external APIs
- **Example**: Testing entity storage and retrieval

```bash
pytest -m integration  # Run all integration tests
```

### 3. System Tests (`@pytest.mark.system`)
- **Purpose**: Test full stack with all components
- **Speed**: < 30 seconds per test
- **Dependencies**: Full stack, mocked LLM, real database
- **Example**: Testing complete workflow with temporal chains

```bash
pytest -m system  # Run all system tests
```

### 4. End-to-End Tests (`@pytest.mark.e2e`)
- **Purpose**: Test complete workflows with real services
- **Speed**: > 30 seconds per test
- **Dependencies**: Real LLM (optional), real database, full system
- **Example**: Complete simulation from start to finish

```bash
pytest -m e2e  # Run all E2E tests
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test level
pytest -m unit
pytest -m integration
pytest -m "system or e2e"

# Run specific test file
pytest test_animistic_entities.py

# Run specific test function
pytest test_animistic_entities.py::TestAnimisticEntities::test_entity_creation

# Run by name pattern
pytest -k "entity"  # Run all tests with 'entity' in name
```

### Advanced Options

```bash
# Skip slow tests
pytest --skip-slow
pytest -m "not slow"

# Skip LLM tests (no API calls)
pytest --skip-llm
pytest -m "not llm"

# Run with real LLM (requires OPENROUTER_API_KEY)
pytest --real-llm

# Parallel execution (requires pytest-xdist)
pytest -n auto  # Auto-detect CPU count
pytest -n 4     # Use 4 workers

# Run last failed tests only
pytest --lf

# Run failures first, then rest
pytest --ff

# Stop after first failure
pytest -x

# Quality checks
pytest --strict-quality  # Skip low-quality tests
pytest --quality-threshold=0.8  # Set quality threshold
```

### Reporting and Output

```bash
# Generate JUnit XML report
pytest --junit-xml=reports/junit.xml

# Generate HTML report (requires pytest-html)
pytest --html=reports/report.html --self-contained-html

# Code coverage (requires pytest-cov)
pytest --cov=. --cov-report=html

# Show slowest tests
pytest --durations=10

# Detailed traceback
pytest --tb=long

# Short traceback
pytest --tb=short
```

---

## Test Organization

### Current Test Files

```
test_ai_entity_service.py          # AI entity service components
test_animistic_entities.py         # Animistic entity generation
test_body_mind_coupling.py         # Body-mind coupling mechanisms
test_branching_integration.py      # Branching mechanism integration
test_branching_mechanism.py        # Branching logic
test_caching_layer.py             # Caching implementation
test_circadian_mechanism.py        # Circadian rhythm simulation
test_deep_integration.py          # Deep integration with LLM
test_e2e_autopilot.py            # E2E autopilot test suite ⭐
test_error_handling_retry.py      # Error handling and retry logic
test_knowledge_enrichment.py       # Knowledge enrichment
test_llm_enhancements_integration.py  # LLM enhancements
test_llm_service_integration.py    # LLM service integration
test_modal_temporal_causality.py   # Modal temporal causality
test_on_demand_generation.py       # On-demand generation
test_parallel_execution.py         # Parallel execution
test_phase3_dialog_multi_entity.py # Multi-entity dialog
test_prospection_mechanism.py      # Prospection mechanisms
test_scene_queries.py             # Scene query functionality
```

### Recommended Organization (Future)

```
tests/
├── unit/                    # Unit tests
│   ├── test_schemas.py
│   ├── test_validation.py
│   └── test_utils.py
│
├── integration/            # Integration tests
│   ├── test_storage.py
│   ├── test_workflows.py
│   └── test_llm_service.py
│
├── system/                # System tests
│   ├── test_temporal_chains.py
│   ├── test_entity_generation.py
│   └── test_ai_entities.py
│
└── e2e/                  # End-to-end tests
    └── test_e2e_autopilot.py
```

---

## Markers and Filtering

### Test Level Markers

| Marker | Purpose | Speed | Usage |
|--------|---------|-------|-------|
| `@pytest.mark.unit` | Unit tests | < 100ms | `pytest -m unit` |
| `@pytest.mark.integration` | Integration tests | < 5s | `pytest -m integration` |
| `@pytest.mark.system` | System tests | < 30s | `pytest -m system` |
| `@pytest.mark.e2e` | E2E tests | > 30s | `pytest -m e2e` |

### Performance Markers

| Marker | Purpose | Usage |
|--------|---------|-------|
| `@pytest.mark.slow` | Slow tests (> 1s) | `pytest -m "not slow"` |
| `@pytest.mark.performance` | Performance benchmarks | `pytest -m performance` |

### Dependency Markers

| Marker | Purpose | Usage |
|--------|---------|-------|
| `@pytest.mark.llm` | Requires LLM API | `pytest --skip-llm` |

### Feature Markers

| Marker | Purpose | Usage |
|--------|---------|-------|
| `@pytest.mark.animism` | Animistic entities | `pytest -m animism` |
| `@pytest.mark.temporal` | Temporal causality | `pytest -m temporal` |
| `@pytest.mark.ai_entity` | AI entities | `pytest -m ai_entity` |

### Quality Markers

| Marker | Purpose | Usage |
|--------|---------|-------|
| `@pytest.mark.validation` | Data validation | `pytest -m validation` |
| `@pytest.mark.safety` | Security/safety | `pytest -m safety` |
| `@pytest.mark.compliance` | Compliance checks | `pytest -m compliance` |

### Combining Markers

```bash
# Run integration OR system tests
pytest -m "integration or system"

# Run everything EXCEPT e2e
pytest -m "not e2e"

# Run temporal tests that are NOT slow
pytest -m "temporal and not slow"

# Run system tests without LLM
pytest -m "system and not llm"
```

---

## Fixtures and Shared Resources

All shared fixtures are defined in `conftest.py`:

### Database Fixtures

```python
@pytest.fixture
def temp_db_path():
    """Temporary database file path"""

@pytest.fixture
def graph_store(temp_db_path):
    """Temporary GraphStore instance"""

@pytest.fixture(scope="session")
def shared_graph_store():
    """Session-scoped shared GraphStore"""
```

### LLM Fixtures

```python
@pytest.fixture
def llm_client(llm_api_key, request):
    """LLM client (mock or real based on config)"""

@pytest.fixture
def real_llm_client(llm_api_key):
    """Force real LLM client (requires API key)"""
```

### Common Data Fixtures

```python
@pytest.fixture
def sample_timepoint():
    """Sample timepoint for testing"""

@pytest.fixture
def sample_entity():
    """Sample entity for testing"""

@pytest.fixture
def sample_entities():
    """Multiple sample entities"""
```

### Service Fixtures

```python
@pytest.fixture
def temporal_agent(graph_store, llm_client):
    """TemporalAgent instance"""

@pytest.fixture
def ai_entity_service(graph_store, llm_client):
    """AIEntityService instance"""

@pytest.fixture
def validator():
    """Validator instance"""
```

---

## LLM Testing

### Mock LLM (Default)

By default, tests use mock LLM responses:

```python
def test_entity_generation(llm_client):
    # Uses mock LLM - no API calls
    entity = llm_client.populate_entity(...)
```

### Real LLM

To use real LLM API calls:

**Option 1: Command line flag**
```bash
export OPENROUTER_API_KEY=your_key_here
pytest --real-llm
```

**Option 2: Mark test with @pytest.mark.llm**
```python
@pytest.mark.llm
def test_real_llm_generation(real_llm_client):
    # Automatically uses real LLM if API key is set
    # Skips test if API key is missing
    entity = real_llm_client.populate_entity(...)
```

### Skipping LLM Tests

```bash
# Skip all LLM tests
pytest --skip-llm

# Alternative: use marker filtering
pytest -m "not llm"
```

### Cost Tracking

LLM costs are automatically logged to:
```
logs/llm_calls/*.jsonl
```

Calculate total cost:
```bash
cat logs/llm_calls/*.jsonl | jq -s 'map(.cost_usd) | add'
```

---

## Writing New Tests

### 1. Choose Test Level

```python
import pytest

# Unit test - fast, isolated
@pytest.mark.unit
def test_validation_logic():
    from validation import Validator
    validator = Validator()
    assert validator.validate_schema(...) == True

# Integration test - multiple components
@pytest.mark.integration
def test_entity_storage(graph_store, sample_entity):
    graph_store.save_entity(sample_entity)
    retrieved = graph_store.get_entity(sample_entity.entity_id)
    assert retrieved == sample_entity

# System test - full stack
@pytest.mark.system
@pytest.mark.slow
def test_temporal_chain(temporal_agent, graph_store):
    chain = temporal_agent.create_chain(...)
    assert len(chain) > 0

# E2E test - complete workflow
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.llm
def test_complete_simulation(real_llm_client, graph_store):
    # Full simulation workflow
    pass
```

### 2. Use Appropriate Fixtures

```python
# Use fixtures from conftest.py
def test_with_fixtures(graph_store, llm_client, sample_entity):
    # Fixtures are automatically provided
    pass

# Define test-specific fixtures
@pytest.fixture
def custom_entity():
    return Entity(...)

def test_custom(custom_entity):
    pass
```

### 3. Add Descriptive Names

```python
# Good: descriptive, clear intent
def test_entity_validation_rejects_invalid_timepoint():
    pass

# Bad: vague, unclear
def test_entity():
    pass
```

### 4. Follow AAA Pattern

```python
def test_entity_creation():
    # Arrange
    entity_data = {...}

    # Act
    entity = create_entity(entity_data)

    # Assert
    assert entity.entity_id is not None
    assert entity.is_valid()
```

### 5. Add Markers

```python
@pytest.mark.unit  # Test level
@pytest.mark.validation  # Feature area
def test_schema_validation():
    pass

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.animism
def test_animistic_entity_generation():
    pass
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        test-level: [unit, integration, system]

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-xdist pytest-cov

      - name: Run ${{ matrix.test-level }} tests
        run: |
          pytest -m ${{ matrix.test-level }} \
            --junit-xml=reports/junit-${{ matrix.test-level }}.xml \
            --cov=. \
            --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml

  e2e:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest

      - name: Run E2E tests
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: |
          pytest -m e2e --real-llm \
            --junit-xml=reports/junit-e2e.xml
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running unit tests..."
pytest -m unit --quiet

if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed. Commit aborted."
    exit 1
fi

echo "✅ Unit tests passed"
exit 0
```

### Makefile Targets

```makefile
# Makefile

.PHONY: test test-unit test-integration test-system test-e2e test-all

test-unit:
	pytest -m unit -v

test-integration:
	pytest -m integration -v

test-system:
	pytest -m system -v

test-e2e:
	pytest -m e2e --real-llm -v

test-fast:
	pytest -m "unit or integration" -v

test-all:
	pytest -v

test-coverage:
	pytest --cov=. --cov-report=html --cov-report=term

test-parallel:
	pytest -n auto -v
```

---

## Quick Reference

### Common Test Scenarios

```bash
# Development: Fast feedback
pytest -m unit --ff

# Pre-commit: Quick validation
pytest -m "unit or integration" --skip-slow

# Full validation: Before merge
pytest -m "unit or integration or system"

# Release testing: Complete validation
pytest -m "not llm"  # Without LLM costs
pytest --real-llm    # With real LLM (costs money)

# Debugging: Single test with full output
pytest test_file.py::test_function -vv --tb=long

# Performance: Find slow tests
pytest --durations=0

# Continuous: Watch for changes (requires pytest-watch)
ptw -- -m unit
```

### Test Quality Commands

```bash
# Enforce quality standards
pytest --strict-quality

# Lower quality threshold
pytest --quality-threshold=0.6

# Check test quality without running
python add_test_markers.py --dry-run
```

---

## Troubleshooting

### Tests Not Found

```bash
# Check test discovery
pytest --collect-only

# Verify markers are registered
pytest --markers
```

### Fixture Not Found

```bash
# List available fixtures
pytest --fixtures

# Check conftest.py is loaded
pytest -v --setup-show
```

### LLM Tests Failing

```bash
# Verify API key
echo $OPENROUTER_API_KEY

# Skip LLM tests
pytest --skip-llm

# Use mock LLM
pytest  # Default behavior
```

### Slow Test Performance

```bash
# Run in parallel
pytest -n auto

# Identify slow tests
pytest --durations=10

# Skip slow tests
pytest --skip-slow
```

---

## Migration Guide

### From Old autopilot.py

The old `autopilot.py` script has been replaced with:

1. **conftest.py**: Shared fixtures and configuration
2. **pytest.ini**: Unified pytest configuration
3. **test_e2e_autopilot.py**: E2E test suite

**Old way:**
```bash
python autopilot.py --parallel --workers 4
```

**New way:**
```bash
pytest -m e2e -n 4
```

### From test_validation_system.py

Quality validation is now in `conftest.py`:

**Old way:**
```python
from test_validation_system import TestValidator
validator = TestValidator()
report = validator.validate_all_tests(test_files)
```

**New way:**
```bash
pytest --strict-quality --quality-threshold=0.7
```

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest markers](https://docs.pytest.org/en/latest/example/markers.html)
- [pytest fixtures](https://docs.pytest.org/en/latest/fixture.html)
- [pytest-xdist](https://pytest-xdist.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

---

**Last Updated**: 2025-10-03
