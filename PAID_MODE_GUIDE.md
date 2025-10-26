# Paid Mode Usage Guide

## Overview

**PAID mode is now the DEFAULT** for the entire system. The system supports two modes for LLM API calls:
- **PAID mode** (DEFAULT): Aggressive throughput using paid Llama models (1000 req/min, burst 50)
- **FREE mode** (optional override): Conservative rate limiting (20 req/min, burst 5)

## Quick Start

### Default Behavior (PAID Mode)

```python
from llm import LLMClient

# PAID mode is now the default - no configuration needed!
llm_client = LLMClient(api_key=api_key)

# Defaults:
# - mode="paid"
# - max_requests_per_minute=1000
# - burst_size=50
# - models: meta-llama/llama-3.1-70b-instruct (default)
#           meta-llama/llama-3.1-405b-instruct (complex tasks)
```

### Override to FREE Mode (if needed)

```python
from llm import LLMClient

# Override to FREE mode for cost-conscious testing
llm_client = LLMClient(
    api_key=api_key,
    mode="free",  # Override to free mode
    max_requests_per_minute=20,
    burst_size=5
)
```

### Paid Models Used

- **Default**: `meta-llama/llama-3.1-70b-instruct` (131K context, fast)
- **Complex tasks**: `meta-llama/llama-3.1-405b-instruct` (32K context, powerful)

Both are open-source Meta Llama 3.1 models with unlimited rate limits on OpenRouter's paid tier.

## Performance Results

| Metric | FREE Mode | PAID Mode | Improvement |
|--------|-----------|-----------|-------------|
| **Max Concurrency** | 2x | 19x | **9.5x** |
| **Peak Throughput** | 1.56 calls/sec | 4.46 calls/sec | **2.8x** |
| **Success Rate** | 100% | 100% | ✅ |
| **Avg Latency** | ~5s | ~1.5s | **3.3x faster** |

## Load Testing

### Test PAID Mode (Default)

```bash
# PAID mode is now the default
python test_paid_mode_stairstep.py

# Or explicitly specify
python test_paid_mode_stairstep.py --mode paid --start-level 5 --max-level 30
```

### Test FREE Mode (Override)

```bash
python test_paid_mode_stairstep.py --mode free --max-level 5 --calls-per-level 10
```

### Advanced Options

```bash
# Start at higher concurrency
python test_paid_mode_stairstep.py --mode paid --start-level 10

# More calls per level (thorough testing)
python test_paid_mode_stairstep.py --mode paid --calls-per-level 20

# Lower success threshold (find breaking point)
python test_paid_mode_stairstep.py --mode paid --success-threshold 0.90
```

## Cost Considerations

### PAID Mode (DEFAULT)
- **Now the default for all workflows**
- Uses paid Meta Llama models (~$0.000001 per token)
- Example costs:
  - 100 calls @ 200 tokens each = ~$0.02
  - 1,000 calls @ 200 tokens each = ~$0.20
  - 10,000 calls @ 200 tokens each = ~$2.00
- Best for: Production, high-volume batch processing, normal development
- **Why default**: Dramatically faster (2.8x throughput), reliable, low latency

### FREE Mode (Optional Override)
- Uses free OpenRouter models
- Rate limited to prevent abuse (20 req/min, burst 5)
- Best for: Cost-sensitive testing, experiments, CI/CD validation
- **Use when**: Testing without budget concerns, validating rate limiting behavior

## Integration with Workflows

All workflows and tensor initialization automatically use PAID mode by default:

```python
from llm import LLMClient
from tensor_initialization import populate_tensor_llm_guided
from orchestrator import OrchestratorAgent
from workflows import TemporalAgent

# PAID mode is automatic - no configuration needed!
llm_client = LLMClient(api_key=api_key)

# All workflows inherit PAID mode
populate_tensor_llm_guided(entity, timepoint, graph, llm_client)
orchestrator = OrchestratorAgent(llm_client, store)
temporal_agent = TemporalAgent(store=store, llm_client=llm_client)

# Override to FREE mode if needed
free_client = LLMClient(api_key=api_key, mode="free")
```

## Monitoring

### Real-time Stats

```python
from llm import RateLimiter

# Get current stats
stats = RateLimiter.get_stats()
print(f"Mode: {stats['mode']}")
print(f"Requests (last min): {stats['requests_last_minute']}")
print(f"Requests (last 5sec): {stats['requests_last_5sec']}")
```

### Load Test Results

Results are saved to `logs/load_test_{mode}_{timestamp}.json`:

```json
{
  "mode": "paid",
  "max_stable_level": 19,
  "results": [
    {"concurrency": 5, "success_rate": 1.0, "avg_duration": 3.20},
    {"concurrency": 7, "success_rate": 1.0, "avg_duration": 1.93},
    ...
  ]
}
```

## Troubleshooting

### Issue: Still rate limited in PAID mode
**Solution**: Verify mode is set correctly
```python
print(f"Current mode: {RateLimiter.get_mode()}")  # Should show "PAID"
```

### Issue: Unexpected 429 errors
**Solution**: OpenRouter's paid tier should be unlimited. Check:
1. API key is valid and has credits
2. Using paid models (not free variants)
3. Check OpenRouter dashboard for account status

### Issue: Slower than expected
**Solution**: Check concurrency settings
```python
# Increase concurrency for paid mode
llm_client = LLMClient(
    api_key=api_key,
    mode="paid",
    max_requests_per_minute=1000  # Increase this
)
```

## Best Practices

1. **Use PAID Mode by Default**: System is optimized for PAID mode (2.8x faster, 19x concurrency)
2. **Monitor Costs**: Track API usage via OpenRouter dashboard ($0.02 per 100 calls typically)
3. **Override to FREE Sparingly**: Only use FREE mode for cost-sensitive testing or CI/CD
4. **Ramp Up Gradually**: Use stairstep testing to validate concurrency limits
5. **Batch Processing**: PAID mode excels at large-scale tensor population (1000 req/min)

## Architecture

```
┌─────────────┐
│ LLMClient   │
│  mode=paid  │
└──────┬──────┘
       │
       ├──→ meta-llama/llama-3.1-70b-instruct (default)
       │    - 131K context
       │    - Fast, efficient
       │
       └──→ meta-llama/llama-3.1-405b-instruct (complex)
            - 32K context
            - Maximum intelligence
```

## Validation

Paid mode has been validated with:
- ✅ 80+ successful API calls at high concurrency
- ✅ Zero failures at 19x concurrent requests
- ✅ Stable 100% success rate across all test levels
- ✅ Throughput 2.8x higher than free mode
- ✅ JSON extraction working perfectly

## Next Steps

**PAID mode is now the system default!** No configuration needed.

1. ✅ PAID mode is already enabled system-wide
2. ✅ Rate limits are set to 1000 req/min, burst 50
3. ✅ Models configured: Llama 3.1 70B (default) + 405B (complex)
4. Monitor costs via OpenRouter dashboard
5. Run stairstep tests to validate your specific workloads
6. Override to FREE mode only when cost-sensitivity is critical
