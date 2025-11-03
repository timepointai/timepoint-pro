# MIGRATION.md - Database v2 Migration Guide

**Document Type:** Migration Guide
**Status:** Active - Database v2 Live
**Created:** November 2, 2025
**Version:** 2.0

---

## Overview

This document describes the migration from Database v1 to Database v2, which adds support for M1+M17 Adaptive Fidelity-Temporal Strategy tracking. The migration is **automatic and backward-compatible**.

## What Changed

### Database Schema v2

Database v2 adds 6 new columns to the `runs` table for tracking fidelity metrics:

| Column | Type | Description |
|--------|------|-------------|
| `schema_version` | TEXT | Database version ("1.0" or "2.0") |
| `fidelity_strategy_json` | TEXT | JSON serialized FidelityTemporalStrategy |
| `fidelity_distribution` | TEXT | JSON distribution: `{"DIALOG": 3, "SCENE": 5, ...}` |
| `actual_tokens_used` | REAL | Actual token consumption |
| `token_budget_compliance` | REAL | Ratio: `actual_tokens / token_budget` |
| `fidelity_efficiency_score` | REAL | Quality metric: `(entities + timepoints) / tokens` |

### Automatic Migration

**When:** First run after upgrading to Database v2 codebase
**What happens:**
1. Old `metadata/runs.db` automatically archived to `metadata/runs_v1_archive.db`
2. New `metadata/runs.db` created with v2 schema
3. All new runs use v2 schema
4. Old v1 runs preserved in archive

**No manual action required.**

## Migration Behavior

### File Operations

**Before Migration:**
```
metadata/
  runs.db           # Database v1 (21 columns)
```

**After Migration:**
```
metadata/
  runs.db           # Database v2 (27 columns) - NEW
  runs_v1_archive.db  # Database v1 (21 columns) - ARCHIVED
```

### Schema Comparison

**Database v1 (21 columns):**
```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    template_id TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    causal_mode TEXT,
    goal TEXT,
    origin_description TEXT,
    entities_created INTEGER,
    timepoints_created INTEGER,
    training_examples INTEGER,
    cost_usd REAL,
    llm_calls INTEGER,
    tokens_used INTEGER,
    oxen_repo_url TEXT,
    oxen_dataset_url TEXT,
    error_message TEXT,
    status TEXT,
    portal_description TEXT,
    portal_year INTEGER,
    origin_year INTEGER,
    backward_steps INTEGER
);
```

**Database v2 (27 columns):**
```sql
CREATE TABLE runs (
    -- ... all v1 columns (0-20) ...

    -- M1+M17: Fidelity-temporal tracking (rows 21-26)
    schema_version TEXT DEFAULT "2.0",
    fidelity_strategy_json TEXT,
    fidelity_distribution TEXT,
    actual_tokens_used REAL,
    token_budget_compliance REAL,
    fidelity_efficiency_score REAL
);
```

## Backward Compatibility

### Reading Old Data

**V1 runs** (from archive) can still be read by v2 code:

```python
from metadata.run_tracker import MetadataManager

# V2 metadata manager
metadata = MetadataManager(db_path="metadata/runs.db")

# Read v1 run from archive
metadata_v1 = MetadataManager(db_path="metadata/runs_v1_archive.db")
old_run = metadata_v1.get_run(run_id="run_20251101_120045_abc123")

# V2 fields will be None for v1 runs
print(old_run.fidelity_distribution)  # None
print(old_run.token_budget_compliance)  # None
```

### Writing New Data

All new runs automatically use v2 schema:

```python
# Complete run with v2 metrics
metadata.complete_run(
    run_id=run_id,
    entities_created=6,
    timepoints_created=15,
    # ... v1 fields ...

    # M1+M17: V2 fields (optional but recommended)
    fidelity_distribution='{"DIALOG": 2, "SCENE": 3, "TENSOR_ONLY": 1}',
    actual_tokens_used=125000.0,
    token_budget_compliance=0.87,
    fidelity_efficiency_score=0.000168
)
```

## Code Changes

### MetadataManager (metadata/run_tracker.py)

**Changes:**
- `complete_run()` accepts 5 new optional parameters
- `save_metadata()` INSERT/UPDATE include v2 columns
- `get_run()` retrieves v2 columns (with backward compatibility)

**Backward Compatibility:**
- V2 parameters are optional (default: None)
- Runs without v2 data still succeed
- Old code calling `complete_run()` without v2 params works unchanged

### E2E Runner (e2e_workflows/e2e_runner.py)

**Changes:**
- `_complete_metadata()` calculates fidelity metrics
- Fidelity distribution computed from entity resolution levels
- Token budget compliance calculated if budget specified
- Fidelity efficiency score computed

**Example:**
```python
# Calculate fidelity distribution
from collections import Counter
resolution_counts = Counter()
for entity in entities:
    res_level = getattr(entity, 'resolution_level', ResolutionLevel.SCENE)
    resolution_counts[res_level.value] += 1

fidelity_distribution = json.dumps(dict(resolution_counts))
```

### Monitor (monitoring/db_inspector.py)

**Changes:**
- `SimulationSnapshot` includes 4 fidelity fields
- `get_run_snapshot()` queries v2 columns (with len check)
- `format_snapshot_for_llm()` displays fidelity metrics

**Backward Compatibility:**
```python
# Check if v2 columns exist
if len(row) > 24:  # V2 columns start at row 24
    fidelity_dist_json = row[24]
    actual_tokens = row[25]
    budget_compliance = row[26]
    efficiency_score = row[27]
```

## Migration Testing

### Verify Migration Success

```bash
# Check that v1 database was archived
ls -lh metadata/runs_v1_archive.db

# Check that v2 database exists
ls -lh metadata/runs.db

# Verify v2 schema
sqlite3 metadata/runs.db ".schema runs"
# Should show 27 columns including schema_version, fidelity_distribution, etc.

# Count v1 runs preserved in archive
sqlite3 metadata/runs_v1_archive.db "SELECT COUNT(*) FROM runs;"

# Verify v2 runs are being created
python -c "
from metadata.run_tracker import MetadataManager
m = MetadataManager()
conn = m.get_connection()
cursor = conn.cursor()
cursor.execute('SELECT schema_version FROM runs WHERE schema_version = \"2.0\"')
print(f'V2 runs: {len(cursor.fetchall())}')
"
```

### Test Backward Compatibility

```python
# Test reading v1 run
from metadata.run_tracker import MetadataManager

metadata_v1 = MetadataManager(db_path="metadata/runs_v1_archive.db")
runs = metadata_v1.get_all_runs()
print(f"V1 runs preserved: {len(runs)}")

# Test reading v2 run
metadata_v2 = MetadataManager(db_path="metadata/runs.db")
run = metadata_v2.get_run(run_id="<latest_run_id>")
print(f"Schema version: {run.schema_version}")
print(f"Fidelity distribution: {run.fidelity_distribution}")
```

### Run E2E Test

```bash
# Run corporate template to generate v2 run
python run_all_mechanism_tests.py --timepoint-corporate

# Verify v2 metrics were saved
python -c "
from metadata.run_tracker import MetadataManager
m = MetadataManager()
runs = m.get_all_runs()
latest = runs[-1]
print(f'Run: {latest.run_id}')
print(f'Schema: {latest.schema_version}')
print(f'Fidelity dist: {latest.fidelity_distribution}')
print(f'Budget compliance: {latest.token_budget_compliance}')
print(f'Efficiency: {latest.fidelity_efficiency_score}')
"
```

## Rollback Procedure

If you need to rollback to Database v1:

```bash
# 1. Backup v2 database
cp metadata/runs.db metadata/runs_v2_backup.db

# 2. Restore v1 database
cp metadata/runs_v1_archive.db metadata/runs.db

# 3. Checkout v1 codebase (before M1+M17 integration)
git checkout <commit_before_v2>

# 4. Verify v1 database works
sqlite3 metadata/runs.db "SELECT COUNT(*) FROM runs;"
```

**WARNING:** Rolling back will lose all v2 runs created after migration.

## Frequently Asked Questions

### Q: Will my old runs be deleted?

**A:** No. Old runs are preserved in `metadata/runs_v1_archive.db`.

### Q: Can I query old runs with new code?

**A:** Yes. Point MetadataManager to `runs_v1_archive.db`. V2 fields will be None.

### Q: Do I need to update my templates?

**A:** No. Templates work unchanged. V2 fields are optional.

### Q: What happens if I don't specify v2 fields?

**A:** Runs succeed normally. V2 fields default to None. You won't get fidelity metrics.

### Q: Can I manually set v2 fields?

**A:** Yes. Pass fidelity metrics to `complete_run()`:

```python
metadata.complete_run(
    run_id=run_id,
    # ... v1 fields ...
    fidelity_distribution='{"DIALOG": 3}',
    actual_tokens_used=100000.0,
    token_budget_compliance=0.95,
    fidelity_efficiency_score=0.0002
)
```

### Q: How do I know if a run is v1 or v2?

**A:** Check `schema_version` field:

```python
run = metadata.get_run(run_id)
if run.schema_version == "2.0":
    print("V2 run with fidelity metrics")
else:
    print("V1 run (no fidelity metrics)")
```

### Q: Does migration affect performance?

**A:** No. V2 schema adds minimal overhead. New columns are indexed.

### Q: Can I merge v1 and v2 databases?

**A:** Not recommended. Use separate databases. Query both if needed:

```python
# Query both databases
metadata_v1 = MetadataManager(db_path="metadata/runs_v1_archive.db")
metadata_v2 = MetadataManager(db_path="metadata/runs.db")

all_runs = metadata_v1.get_all_runs() + metadata_v2.get_all_runs()
```

## Implementation Details

### MetadataManager Changes

**File:** `metadata/run_tracker.py`

**Modified Methods:**
1. `complete_run()` - accepts 5 new optional parameters (lines 248-295)
2. `save_metadata()` - INSERT/UPDATE with v2 fields (lines 323-389)
3. `get_run()` - retrieves v2 fields with bounds check (lines 455-510)

**New Columns (rows 22-27):**
```python
schema_version=row[22] if len(row) > 22 else "1.0",
fidelity_strategy_json=row[23] if len(row) > 23 else None,
fidelity_distribution=row[24] if len(row) > 24 else None,
actual_tokens_used=row[25] if len(row) > 25 else None,
token_budget_compliance=row[26] if len(row) > 26 else None,
fidelity_efficiency_score=row[27] if len(row) > 27 else None,
```

### E2E Runner Changes

**File:** `e2e_workflows/e2e_runner.py`

**Modified Methods:**
1. `_complete_metadata()` - calculates fidelity metrics (lines 577-611)

**Metric Calculations:**
```python
# Fidelity distribution
resolution_counts = Counter()
for entity in entities:
    res_level = getattr(entity, 'resolution_level', ResolutionLevel.SCENE)
    resolution_counts[res_level.value] += 1
fidelity_distribution = json.dumps(dict(resolution_counts))

# Token budget compliance
if token_budget:
    token_budget_compliance = actual_tokens / token_budget

# Fidelity efficiency score
quality_score = entities_count + timepoints_count
if actual_tokens > 0:
    fidelity_efficiency_score = quality_score / actual_tokens
```

### Monitor Changes

**File:** `monitoring/db_inspector.py`

**Modified Classes:**
1. `SimulationSnapshot` - 4 new fields (lines 28-33)
2. `get_run_snapshot()` - queries v2 columns (lines 86-98)
3. `format_snapshot_for_llm()` - displays fidelity metrics (lines 162-174)

**Display Format:**
```
Fidelity Distribution (M1):
  DIALOG: 2 entities
  SCENE: 3 entities
  TENSOR_ONLY: 1 entities

Token Budget Compliance: ✓ 87.3%
Fidelity Efficiency: 0.000168 quality/token
```

## Related Documentation

- **[MECHANICS.md](MECHANICS.md)**: M1+M17 Integration technical specification
- **[HANDOFF.md](HANDOFF.md)**: M1+M17 implementation plan (Phases 1-7)
- **[schemas.py](schemas.py)**: Database schema definitions
- **[metadata/run_tracker.py](metadata/run_tracker.py)**: MetadataManager implementation

## Support

If you encounter issues during migration:

1. **Check database files exist:**
   ```bash
   ls -lh metadata/runs*.db
   ```

2. **Verify schema version:**
   ```bash
   sqlite3 metadata/runs.db ".schema runs" | grep schema_version
   ```

3. **Test imports:**
   ```python
   from metadata.run_tracker import MetadataManager, RunMetadata
   from schemas import FidelityPlanningMode, TokenBudgetMode
   print("✅ V2 imports successful")
   ```

4. **Run migration test:**
   ```bash
   python -c "from metadata.run_tracker import MetadataManager; m = MetadataManager(); print('✅ V2 database operational')"
   ```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-10-15 | Initial database schema (21 columns) |
| 2.0 | 2025-11-02 | Added fidelity-temporal tracking (27 columns) |

---

**Migration Status:** Complete ✅
**V1 Archive:** `metadata/runs_v1_archive.db`
**V2 Active:** `metadata/runs.db`
**Last Updated:** November 2, 2025
