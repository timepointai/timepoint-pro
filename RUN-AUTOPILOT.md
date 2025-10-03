# Run Autopilot with LLM Service - Quick Reference

## ✅ Status: READY TO RUN

All files have been integrated. The application now uses the centralized LLM service throughout.

---

## Quick Commands

### 1. Test Integration (Dry-Run, No Cost)

```bash
# Run integration tests
python test_llm_service_integration.py

# Expected output:
# 🎉 ALL TESTS PASSED! LLM service integration is working correctly.
```

### 2. Run Autopilot (Dry-Run Mode)

```bash
# Zero cost, mock responses
python autopilot.py --force --dry-run --output autopilot_dry_run.json

# Or via CLI
python cli.py mode=temporal_train llm.dry_run=true training.num_timepoints=3
```

### 3. Run Autopilot (Real LLM Calls)

```bash
# Set your API key
export OPENROUTER_API_KEY="your_actual_api_key_here"

# Run with real API calls
python autopilot.py --force --output autopilot_real_llm.json

# Or via CLI with specific config
python cli.py mode=temporal_train llm.dry_run=false training.num_timepoints=2
```

### 4. Monitor Logs

```bash
# Watch logs in real-time
tail -f logs/llm_calls/llm_calls_$(date +%Y-%m-%d).jsonl

# Pretty print with jq
tail -f logs/llm_calls/llm_calls_$(date +%Y-%m-%d).jsonl | jq .

# Calculate total cost
cat logs/llm_calls/*.jsonl | jq -s 'map(.cost_usd) | add'
```

---

## What Changed

### All Files Now Use `llm_v2.LLMClient`

**Core Files:**
- ✅ `cli.py` - Main entry point
- ✅ `workflows.py` - All workflows
- ✅ `query_interface.py` - Query processing
- ✅ `resolution_engine.py` - Entity resolution
- ✅ `ai_entity_service.py` - AI entities

**Test Files (10 files):**
- ✅ All `test_*.py` files updated

### Configuration

**Backward Compatible:**
- `llm.dry_run=true` → Service uses dry-run mode
- `llm.dry_run=false` → Service uses production mode

**Full Control:**
```yaml
llm:
  dry_run: false  # Controls mode
  api_key: ${oc.env:OPENROUTER_API_KEY}

llm_service:
  modes:
    mode: "production"  # Auto-synced with llm.dry_run
  logging:
    level: "metadata"   # Change to "full" for debug
```

---

## Expected Behavior

### Dry-Run Mode

```bash
python cli.py mode=temporal_train llm.dry_run=true

# Expected:
# ✅ LLM calls return deterministic mock data
# ✅ Zero API costs
# ✅ Fast execution
# ✅ Logs created in logs/llm_calls/
# ✅ All mechanisms work (with mock data)
```

### Production Mode

```bash
export OPENROUTER_API_KEY="your_key"
python cli.py mode=temporal_train llm.dry_run=false training.num_timepoints=2

# Expected:
# ✅ Real LLM API calls to OpenRouter
# ✅ Actual costs incurred
# ✅ Real entity data generated
# ✅ Comprehensive logs with tokens/cost
# ✅ Automatic retry on failures
# ✅ Security filtering applied
```

---

## Verification Checklist

Before running with real API:

- [ ] API key set: `echo $OPENROUTER_API_KEY`
- [ ] Integration tests pass: `python test_llm_service_integration.py`
- [ ] Dry-run works: `python cli.py mode=temporal_train llm.dry_run=true`
- [ ] Logs directory exists: `mkdir -p logs/llm_calls`
- [ ] Config correct: `grep "dry_run" conf/config.yaml`

---

## Cost Estimates

### Dry-Run Mode
- **Cost:** $0.00
- **Time:** Fast (mock responses)

### Production Mode (Small Test)
```bash
# 2 timepoints, 5 entities
python cli.py mode=temporal_train llm.dry_run=false training.num_timepoints=2

# Estimated cost: ~$0.50 - $2.00
# Depends on: model, prompt size, response length
```

### Production Mode (Full Autopilot)
```bash
python autopilot.py --force

# Estimated cost: $5 - $20
# Depends on: number of tests, mechanisms tested
```

**Check actual costs:**
```bash
cat logs/llm_calls/*.jsonl | jq -s 'map(.cost_usd) | add'
```

---

## Troubleshooting

### Issue: Import Errors

**Solution:** Check Python path
```bash
export PYTHONPATH=/code:$PYTHONPATH
python test_llm_service_integration.py
```

### Issue: No Logs

**Solution:** Create logs directory
```bash
mkdir -p logs/llm_calls
python cli.py mode=temporal_train llm.dry_run=true
ls -lh logs/llm_calls/
```

### Issue: API Key Not Found

**Solution:** Set environment variable
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
echo $OPENROUTER_API_KEY
```

### Issue: Tests Fail

**Solution:** Run integration tests to diagnose
```bash
python test_llm_service_integration.py
# This will show which component is failing
```

### Issue: High Costs

**Solution:** Use dry-run mode for testing
```bash
# Always test with dry-run first
python cli.py mode=temporal_train llm.dry_run=true

# Then run small production test
python cli.py mode=temporal_train llm.dry_run=false training.num_timepoints=2

# Monitor costs
cat logs/llm_calls/*.jsonl | jq -s 'map(.cost_usd) | add'
```

---

## Advanced Usage

### Run Specific Tests

```bash
# Run single test file
python -m pytest test_deep_integration.py -v

# Run with real LLM
OPENROUTER_API_KEY="..." python -m pytest test_deep_integration.py -v
```

### Change Log Level

```bash
# Edit config.yaml
# Change: logging.level: "full"
python cli.py mode=temporal_train llm.dry_run=false

# Now logs include full prompts and responses
```

### Session Tracking

```python
# In your code
from llm_v2 import LLMClient

client = LLMClient.from_hydra_config(cfg, use_centralized_service=True)

# Service automatically tracks sessions
# Check logs for session_id and aggregated costs
```

---

## Files to Review

### Integration Status
- `LLM-SERVICE-INTEGRATION-COMPLETE.md` - Complete integration details

### Getting Started
- `LLM-SERVICE-QUICKSTART.md` - 5-minute quick start

### Migration Guide
- `LLM-SERVICE-MIGRATION.md` - Full migration documentation

### Implementation
- `LLM-SERVICE-SUMMARY.md` - Technical implementation details

### Tests
- `test_llm_service_integration.py` - Integration test suite
- `examples/llm_service_demo.py` - Feature demonstrations

---

## Ready to Run

Everything is integrated and ready. Choose your mode:

**For Testing (Recommended First):**
```bash
python test_llm_service_integration.py
python autopilot.py --force --dry-run
```

**For Production:**
```bash
export OPENROUTER_API_KEY="your_key"
python autopilot.py --force --output results.json
```

**Monitor costs:**
```bash
watch -n 5 'cat logs/llm_calls/*.jsonl | jq -s "map(.cost_usd) | add"'
```

---

## Support

If you encounter issues:

1. Run integration tests: `python test_llm_service_integration.py`
2. Check logs: `tail logs/llm_calls/*.jsonl`
3. Try dry-run mode first: `llm.dry_run=true`
4. Review documentation: `LLM-SERVICE-INTEGRATION-COMPLETE.md`

---

**Status: ✅ READY - All components integrated and tested**
