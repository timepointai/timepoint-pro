# Unified Testing System - Quick Start

**Status**: ✅ Complete | **Last Updated**: 2025-10-03

## 🚀 Quick Commands

```bash
# Run all tests
pytest

# Run by test level (fastest to slowest)
pytest -m unit              # Fast unit tests (< 100ms)
pytest -m integration       # Integration tests (< 5s)
pytest -m system           # System tests (< 30s)
pytest -m e2e              # End-to-end tests (> 30s)

# Skip expensive tests
pytest --skip-slow         # Skip slow tests
pytest --skip-llm          # Skip LLM API calls

# Run with real LLM (costs money!)
pytest --real-llm          # Requires OPENROUTER_API_KEY

# Advanced
pytest -n auto             # Parallel execution
pytest --lf                # Run last failed only
pytest --cov=.             # With coverage
```

## 📁 File Structure

### Core Infrastructure
- **`conftest.py`** - Shared fixtures and quality validation
- **`pytest.ini`** - Unified configuration with markers
- **`TESTING.md`** - Complete testing documentation
- **`TESTING_MIGRATION.md`** - Migration guide and summary

### Test Suites
- **`test_e2e_autopilot.py`** - E2E test suite (replaces autopilot.py)
- **`test_*.py`** - 18 other test files (need markers added)

### Tools
- **`add_test_markers.py`** - Automatic marker assignment

### Deprecated
- **`autopilot.py`** - Now shows deprecation message
- **`test_validation_system.py`** - Now shows deprecation message

## 📊 Test Hierarchy

```
Unit Tests (@pytest.mark.unit)
  ├── Fast (< 100ms)
  ├── Isolated
  └── No external dependencies

Integration Tests (@pytest.mark.integration)
  ├── Medium speed (< 5s)
  ├── Multiple components
  └── Temp database

System Tests (@pytest.mark.system)
  ├── Slower (< 30s)
  ├── Full stack
  └── Mocked externals

E2E Tests (@pytest.mark.e2e)
  ├── Slowest (> 30s)
  ├── Complete workflows
  └── Real services (optional)
```

## 🏷️ Marker Usage

### Test Levels
```bash
-m unit              # Unit tests only
-m integration       # Integration tests only
-m "system or e2e"   # System + E2E
-m "not e2e"         # Everything except E2E
```

### Features
```bash
-m llm               # LLM tests
-m animism           # Animistic entities
-m temporal          # Temporal causality
-m ai_entity         # AI entities
```

### Quality
```bash
-m validation        # Data validation
-m safety            # Security tests
-m compliance        # Compliance tests
```

## 🔧 Setup

### 1. Add Markers to Tests

```bash
# Preview changes
python add_test_markers.py --dry-run

# Apply markers
python add_test_markers.py
```

### 2. Verify Tests

```bash
# Check test collection
pytest --collect-only

# Run unit tests
pytest -m unit -v
```

### 3. Configure LLM (Optional)

```bash
# For real LLM testing
export OPENROUTER_API_KEY=your_key_here

# Run with real LLM
pytest --real-llm -m llm
```

## 📝 Common Workflows

### Development Cycle
```bash
# Fast iteration
pytest -m unit --ff                    # Failures first

# Before commit
pytest -m "unit or integration" --skip-slow

# Before merge
pytest -m "not e2e" -v
```

### CI/CD Pipeline
```bash
# Pull request
pytest -m "unit or integration" --junit-xml=reports/junit.xml

# Main branch
pytest -m "not llm" -v --junit-xml=reports/junit.xml

# Release
pytest --real-llm --junit-xml=reports/junit.xml
```

### Debugging
```bash
# Single test with full output
pytest test_file.py::test_name -vv --tb=long

# Find slow tests
pytest --durations=10

# Show fixture setup
pytest --setup-show
```

## 🎯 Migration from Old System

### Old Commands → New Commands

| Old | New | Notes |
|-----|-----|-------|
| `python autopilot.py` | `pytest -m e2e` | E2E tests |
| `python autopilot.py --dry-run` | `pytest --collect-only` | Preview |
| `python autopilot.py --parallel --workers 4` | `pytest -n 4` | Parallel |
| Quality validation | `pytest --strict-quality` | Built-in |

### What Changed

✅ **autopilot.py** → Deprecated, use `pytest -m e2e`
✅ **test_validation_system.py** → Deprecated, use `conftest.py`
✅ **pytest.ini** → Updated with hierarchical markers
✅ **New: conftest.py** → Shared fixtures + quality checks
✅ **New: test_e2e_autopilot.py** → Proper E2E suite
✅ **New: TESTING.md** → Complete documentation

## 📚 Documentation

- **`TESTING.md`** - Comprehensive testing guide
- **`TESTING_MIGRATION.md`** - Migration summary
- **`pytest.ini`** - Configuration with usage examples
- **`conftest.py`** - Fixture and hook documentation

## 🚨 Important Notes

### LLM Testing
- **Mock by default** - No API calls, free
- **Real LLM with `--real-llm`** - Costs money, requires API key
- **Skip with `--skip-llm`** - Exclude LLM tests
- **Cost tracking** - Logs to `logs/llm_calls/*.jsonl`

### Quality Validation
- **Automatic** - Via conftest.py hooks
- **Enforce with `--strict-quality`** - Skip low-quality tests
- **Threshold: `--quality-threshold=0.7`** - Minimum score

### Test Discovery
- **Pattern**: `test_*.py`
- **Classes**: `Test*`
- **Functions**: `test_*`
- **Location**: Current directory

## ✅ Validation Checklist

After setup:

- [ ] Run `python add_test_markers.py` to add markers
- [ ] Verify collection: `pytest --collect-only`
- [ ] Run unit tests: `pytest -m unit`
- [ ] Run integration: `pytest -m integration`
- [ ] Run system: `pytest -m system`
- [ ] Run E2E (mock): `pytest -m e2e`
- [ ] Check LLM setup: `echo $OPENROUTER_API_KEY`
- [ ] Update CI/CD to use new commands

## 🆘 Troubleshooting

**Tests not found?**
```bash
pytest --collect-only  # Check discovery
pytest --markers       # Verify markers
```

**Fixtures missing?**
```bash
pytest --fixtures      # List fixtures
```

**LLM tests failing?**
```bash
pytest --skip-llm      # Skip LLM tests
# Or set API key: export OPENROUTER_API_KEY=...
```

**Old autopilot errors?**
```bash
# Don't use autopilot.py anymore
# Use: pytest -m e2e
```

## 📊 Test Statistics

- **Total test files**: 19
- **Test functions**: ~128
- **Test classes**: ~26
- **Test levels**: 4 (unit/integration/system/e2e)
- **Markers**: 13 total
- **Fixtures**: 15+ shared fixtures

## 🔗 Quick Links

```bash
# View documentation
cat TESTING.md                    # Complete guide
cat TESTING_MIGRATION.md          # Migration summary
cat pytest.ini                    # Configuration

# View fixtures
cat conftest.py                   # Shared fixtures

# View E2E examples
cat test_e2e_autopilot.py        # E2E test suite

# Get help
pytest --help                     # Pytest help
```

---

**Ready to test!** 🎉

Start with: `pytest -m unit -v`
