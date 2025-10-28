# LLM Service - Quick Start Guide

Get started with the centralized LLM service in 5 minutes.

---

## 1. Choose Your Path

### Path A: Use Backward-Compatible Wrapper (Easiest)

**For existing code** - minimal changes:

```python
# Change this:
from llm import LLMClient

# To this:
from llm_v2 import LLMClient

# Add one parameter:
client = LLMClient(
    api_key=api_key,
    use_centralized_service=True  # Enable new service
)

# Everything else stays the same!
result = client.populate_entity(entity_schema, context)
```

### Path B: Use New Service Directly (Recommended)

**For new code** - full features:

```python
from llm_service import LLMService, LLMServiceConfig

# Load from config
config = LLMServiceConfig.from_hydra_config(cfg)
service = LLMService(config)

# Make calls
response = service.call(
    system="You are a historian.",
    user="Tell me about George Washington.",
    call_type="historical_query"
)
```

---

## 2. Configure

Edit `conf/config.yaml`:

```yaml
llm_service:
  # Choose mode
  modes:
    mode: "production"  # or "dry_run" for testing

  # Set defaults
  defaults:
    model: "meta-llama/llama-3.1-70b-instruct"
    temperature: 0.7
    max_tokens: 1000

  # Configure logging
  logging:
    level: "metadata"  # metadata, prompts, responses, full
    directory: "logs/llm_calls"
```

---

## 3. Test

### Test in Dry-Run Mode (Zero Cost)

```yaml
llm_service:
  modes:
    mode: "dry_run"
```

```python
from llm_v2 import LLMClient

client = LLMClient(api_key="test", dry_run=True, use_centralized_service=True)
result = client.populate_entity({"entity_id": "washington"}, {})

print(f"Success! Entity: {result.entity_id}")
print(f"Knowledge items: {len(result.knowledge_state)}")
```

### Test in Production Mode (Real API)

```yaml
llm_service:
  modes:
    mode: "production"
```

```python
client = LLMClient(api_key=YOUR_API_KEY, use_centralized_service=True)
result = client.populate_entity(entity_schema, context)
```

---

## 4. View Logs

```bash
# See today's logs
cat logs/llm_calls/llm_calls_$(date +%Y-%m-%d).jsonl | jq .

# Calculate total cost
cat logs/llm_calls/*.jsonl | jq -s 'map(.cost_usd) | add'

# Find failed calls
cat logs/llm_calls/*.jsonl | jq 'select(.success == false)'
```

---

## 5. Use Advanced Features

### Structured Output

```python
from pydantic import BaseModel

class EntityInfo(BaseModel):
    name: str
    knowledge: list[str]

entity = service.structured_call(
    system="Generate entity info",
    user="Create info for Washington",
    schema=EntityInfo
)
```

### Session Tracking

```python
# Start session
session_id = service.start_session(workflow="temporal_train")

# Make calls...
service.call(system="...", user="...")

# End session
summary = service.end_session()
print(f"Cost: ${summary['total_cost']:.4f}")
```

### Security

```python
# Automatic input bleaching and output sanitization
response = service.call(
    system="...",
    user=user_input,  # Automatically cleaned
    apply_security=True
)

# Manual PII detection
pii = service.security_filter.detect_pii(text)
redacted = service.security_filter.redact_pii(text)
```

---

## 6. Run Examples

```bash
python examples/llm_service_demo.py
```

This runs 8 examples demonstrating all features.

---

## Common Tasks

### Switch Between Legacy and New Service

```python
# Use new service
client = LLMClient(api_key=key, use_centralized_service=True)

# Use legacy service
client = LLMClient(api_key=key, use_centralized_service=False)
```

### Enable Full Logging

```yaml
llm_service:
  logging:
    level: "full"  # See all prompts and responses
```

### Customize Retry Behavior

```yaml
llm_service:
  error_handling:
    max_retries: 5
    backoff_base: 2.0
    failsoft_enabled: true
```

### Use Test Provider

```yaml
llm_service:
  provider: "test"  # No real API calls
  modes:
    mode: "dry_run"
```

---

## Troubleshooting

### Logs not appearing?

```bash
mkdir -p logs/llm_calls
```

### Import errors?

```python
import sys
sys.path.insert(0, '/code')
from llm_service import LLMService
```

### Config not found?

Check `llm_service` section exists in `conf/config.yaml`.

### Service not being used?

Verify `use_centralized_service=True` in LLMClient constructor.

---

## Next Steps

1. ✅ **Read this** - You're here!
2. 📖 Read `LLM-SERVICE-MIGRATION.md` for complete guide
3. 📊 Read `LLM-SERVICE-SUMMARY.md` for implementation details
4. 🧪 Run `python examples/llm_service_demo.py`
5. 🚀 Test in your code with `use_centralized_service=True`

---

## Key Benefits

✅ **Unified interface** - One place for all LLM operations
✅ **Better logging** - JSONL files with cost tracking
✅ **Error handling** - Automatic retries with backoff
✅ **Security** - Input/output filtering built-in
✅ **Testing modes** - Dry-run and validation for zero-cost testing
✅ **Backward compatible** - Drop-in replacement for existing code

---

## Support

- **Migration Guide**: `LLM-SERVICE-MIGRATION.md`
- **Implementation Details**: `LLM-SERVICE-SUMMARY.md`
- **Example Code**: `examples/llm_service_demo.py`
- **Service Code**: `/code/llm_service/`

---

**You're ready to go! Start with Path A (backward-compatible) for easiest migration.**
