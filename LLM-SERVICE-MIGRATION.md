# LLM Service Migration Guide

## Executive Summary

The centralized LLM service architecture has been implemented according to LLM-INTEGRATION-PLAN.md. This provides a unified interface for all LLM operations with comprehensive error handling, logging, security, and provider abstraction.

**Status**: Phase 1 Complete - Core architecture implemented and ready for gradual migration.

---

## What's Been Implemented

### ✅ Phase 1: Core Architecture (COMPLETE)

#### 1. Service Components

**Location**: `/code/llm_service/`

- **`provider.py`**: Protocol interface for LLM providers
- **`config.py`**: Configuration management with Hydra integration
- **`prompt_manager.py`**: Prompt construction and templating
- **`response_parser.py`**: JSON extraction and schema validation
- **`error_handler.py`**: Retry logic with exponential backoff
- **`call_logger.py`**: Comprehensive call logging with sessions
- **`security_filter.py`**: Input bleaching and output sanitization
- **`service.py`**: Main LLMService facade

#### 2. Provider Implementations

**Location**: `/code/llm_service/providers/`

- **`custom_provider.py`**: Wraps existing OpenRouterClient
- **`test_provider.py`**: Mock and validation modes

#### 3. Configuration

**File**: `/code/conf/config.yaml`

New `llm_service` section added with:
- Provider configuration
- API key management (with rotation support)
- Operating modes (production, dry_run, validation)
- Default LLM parameters
- Error handling settings
- Logging configuration
- Security controls
- Performance optimization
- Session management

#### 4. Backward Compatibility

**File**: `/code/llm_v2.py`

- Drop-in replacement for existing LLMClient
- Can toggle between legacy and new service via flag
- Maintains same method signatures
- Preserves statistics tracking

---

## How to Use the New Service

### Option 1: Direct Service Usage (Recommended for New Code)

```python
from llm_service import LLMService, LLMServiceConfig

# Load from Hydra config
config = LLMServiceConfig.from_hydra_config(cfg)
service = LLMService(config)

# Start a session
session_id = service.start_session(workflow="temporal_train", user="system")

# Make a simple call
response = service.call(
    system="You are an expert historian.",
    user="Generate entity information for George Washington in 1789.",
    temperature=0.7,
    max_tokens=1000,
    call_type="populate_entity"
)

print(response.content)
print(f"Cost: ${response.cost_usd:.4f}")
print(f"Tokens: {response.tokens_used['total']}")

# Make a structured call
from schemas import EntityPopulation

entity = service.structured_call(
    system="You are an expert historian.",
    user="Generate entity information...",
    schema=EntityPopulation,
    temperature=0.7,
    call_type="populate_entity"
)

# End session
summary = service.end_session()
print(f"Session cost: ${summary['total_cost']:.4f}")
```

### Option 2: Backward-Compatible Wrapper (For Existing Code)

```python
from llm_v2 import LLMClient

# Enable new service (recommended)
client = LLMClient(
    api_key=api_key,
    base_url=base_url,
    dry_run=False,
    use_centralized_service=True  # Enable new architecture
)

# Or from Hydra config
client = LLMClient.from_hydra_config(cfg, use_centralized_service=True)

# Use existing methods (same API)
result = client.populate_entity(entity_schema, context, previous_knowledge)
validation = client.validate_consistency(entities, timepoint)
score = client.score_relevance(query, knowledge_item)
dialog = client.generate_dialog(prompt, max_tokens=2000)
```

### Option 3: Legacy Mode (Fallback)

```python
from llm_v2 import LLMClient

# Use legacy implementation
client = LLMClient(
    api_key=api_key,
    use_centralized_service=False  # Disable new service
)

# Works exactly as before
result = client.populate_entity(entity_schema, context)
```

---

## Configuration Guide

### Using Existing Config

The service automatically reads from `llm_service` section in `config.yaml`. To use:

```python
import hydra
from llm_service import LLMService, LLMServiceConfig

@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg):
    service = LLMService.from_hydra_config(cfg)
    # Service is configured from config.yaml
```

### Customizing Config

Edit `conf/config.yaml`:

```yaml
llm_service:
  provider: "custom"  # custom, test

  modes:
    mode: "production"  # production, dry_run, validation

  defaults:
    model: "meta-llama/llama-3.1-70b-instruct"
    temperature: 0.7
    max_tokens: 1000

  error_handling:
    max_retries: 3
    failsoft_enabled: true

  logging:
    level: "metadata"  # metadata, prompts, responses, full
    directory: "logs/llm_calls"

  security:
    input_bleaching: true
    output_sanitization: true
```

### Operating Modes

**Production Mode**: Full LLM calls with real API
```yaml
modes:
  mode: "production"
```

**Dry-Run Mode**: Mock responses, no API calls, zero cost
```yaml
modes:
  mode: "dry_run"
```

**Validation Mode**: Lightweight testing with simple prompts
```yaml
modes:
  mode: "validation"
```

---

## Migration Path

### Phase 1: Core Architecture ✅ COMPLETE

- ✅ Implement service components
- ✅ Create provider implementations
- ✅ Add configuration section
- ✅ Create backward-compatible wrapper

### Phase 2: Gradual Migration (Next Steps)

#### Step 1: Test in Dry-Run Mode

```python
# In your code, switch to new service in dry-run first
client = LLMClient.from_hydra_config(cfg, use_centralized_service=True)
```

Set config:
```yaml
llm_service:
  modes:
    mode: "dry_run"
```

Run your tests and verify outputs match expectations.

#### Step 2: Test in Validation Mode

```yaml
llm_service:
  modes:
    mode: "validation"
```

This makes real API calls but with lightweight prompts. Verify:
- API connectivity works
- Authentication succeeds
- Response parsing functions
- Cost tracking accurate

#### Step 3: Enable Production Mode

```yaml
llm_service:
  modes:
    mode: "production"
```

Run with `use_centralized_service=True` and compare:
- Response quality
- Cost metrics
- Performance
- Log output

#### Step 4: Migrate Components

1. **Update cli.py**:
```python
# Change import
from llm_v2 import LLMClient
# Or
from llm_service import LLMService
```

2. **Update workflows.py**:
```python
# Use service directly for new code
service = LLMService.from_hydra_config(cfg)
```

3. **Update query_interface.py**:
```python
# Leverage structured_call for better parsing
result = service.structured_call(system=..., user=..., schema=MySchema)
```

### Phase 3: Advanced Features

Once core migration stable:

1. **Enable comprehensive logging**:
```yaml
logging:
  level: "full"  # See all prompts and responses
```

2. **Add custom prompt templates**:
```python
service.register_prompt_template(
    "entity_population",
    "Generate entity for $entity_id in context $context..."
)

prompt = service.build_prompt("entity_population", {"entity_id": "washington"})
```

3. **Implement session tracking**:
```python
session_id = service.start_session("temporal_train")
# ... make calls ...
summary = service.end_session()
# Analyze session cost and performance
```

4. **Enable security features**:
```python
# PII detection
pii = service.security_filter.detect_pii(user_input)
if pii:
    user_input = service.security_filter.redact_pii(user_input)
```

---

## Feature Comparison

| Feature | Legacy LLMClient | New LLMService |
|---------|------------------|----------------|
| Basic LLM calls | ✅ | ✅ |
| Structured output | ✅ (manual parsing) | ✅ (automatic schema validation) |
| Error handling | ✅ (simple retry) | ✅ (advanced with backoff) |
| Cost tracking | ✅ (basic) | ✅ (comprehensive with sessions) |
| Logging | ⚠️ (console only) | ✅ (JSONL files, multiple levels) |
| Security | ❌ | ✅ (input/output filtering) |
| Provider abstraction | ❌ | ✅ (easy to swap providers) |
| Dry-run mode | ✅ | ✅ (improved) |
| Validation mode | ❌ | ✅ (new) |
| Prompt templating | ❌ | ✅ |
| Session management | ❌ | ✅ |
| PII detection | ❌ | ✅ |

---

## Testing Strategy

### 1. Unit Tests (To Be Added)

```python
# tests/test_llm_service.py
def test_service_dry_run_mode():
    config = LLMServiceConfig(mode=ServiceMode.DRY_RUN)
    service = LLMService(config)

    response = service.call(system="test", user="test")
    assert response.success
    assert response.cost_usd == 0.0

def test_structured_call():
    service = LLMService(config)
    result = service.structured_call(
        system="test",
        user="test",
        schema=EntityPopulation
    )
    assert isinstance(result, EntityPopulation)
```

### 2. Integration Tests

```bash
# Test with dry-run mode
python cli.py mode=temporal_train llm_service.modes.mode=dry_run

# Test with validation mode
python cli.py mode=temporal_train llm_service.modes.mode=validation

# Test with production mode
python cli.py mode=temporal_train llm_service.modes.mode=production
```

### 3. Comparison Testing

```python
# Run same operation with both implementations
legacy_client = LLMClient(api_key=key, use_centralized_service=False)
new_client = LLMClient(api_key=key, use_centralized_service=True)

legacy_result = legacy_client.populate_entity(schema, context)
new_result = new_client.populate_entity(schema, context)

# Compare outputs
assert legacy_result.entity_id == new_result.entity_id
assert len(legacy_result.knowledge_state) > 0
assert len(new_result.knowledge_state) > 0
```

---

## Logging and Monitoring

### Log Files

Service writes JSONL logs to `logs/llm_calls/`:

```
logs/llm_calls/
├── llm_calls_2025-10-03.jsonl
├── llm_calls_2025-10-04.jsonl
└── ...
```

### Log Levels

**metadata** (default): Essential info only
```json
{
  "timestamp": "2025-10-03T10:30:45Z",
  "session_id": "llm_abc123",
  "call_type": "populate_entity",
  "model": "meta-llama/llama-3.1-70b-instruct",
  "tokens_used": {"prompt": 150, "completion": 450, "total": 600},
  "cost_usd": 0.012,
  "latency_ms": 1234,
  "success": true
}
```

**prompts**: Add truncated prompts
```json
{
  ...metadata...,
  "system_prompt": "You are an expert... [truncated]",
  "user_prompt": "Generate entity... [truncated]"
}
```

**responses**: Add truncated responses
```json
{
  ...metadata...,
  "response_full": "{\"entity_id\": ... [truncated]"
}
```

**full**: Complete payloads (no truncation)

### Viewing Logs

```bash
# View today's calls
cat logs/llm_calls/llm_calls_$(date +%Y-%m-%d).jsonl | jq .

# Calculate total cost
cat logs/llm_calls/*.jsonl | jq -s 'map(.cost_usd) | add'

# Find failed calls
cat logs/llm_calls/*.jsonl | jq 'select(.success == false)'

# Session summary
cat logs/llm_calls/*.jsonl | jq 'select(.session_id == "llm_abc123")'
```

---

## Security Features

### Input Bleaching

Automatically removes dangerous patterns:
- Prompt injection attempts
- HTML/script tags
- SQL injection patterns
- Excessive input length

```python
# Automatic (enabled by default)
response = service.call(system=sys, user=user, apply_security=True)

# Manual
clean_input = service.security_filter.bleach_input(user_input)
```

### Output Sanitization

Removes potentially harmful content from LLM responses:
- HTML/script tags
- Code execution patterns
- Malformed encoding

```python
# Automatic
response = service.call(system=sys, user=user, apply_security=True)
# response.content is already sanitized

# Manual
safe_output = service.security_filter.sanitize_output(llm_response)
```

### PII Detection and Redaction

```python
# Detect PII
pii_types = service.security_filter.detect_pii(text)
# Returns: ["email", "phone", ...]

# Redact PII
redacted = service.security_filter.redact_pii(text)
# Emails → [EMAIL_REDACTED]
# Phones → [PHONE_REDACTED]
# SSNs → [SSN_REDACTED]
```

---

## Troubleshooting

### Issue: Service not using new architecture

**Solution**: Check `use_centralized_service` flag:
```python
client = LLMClient(..., use_centralized_service=True)
```

### Issue: Config not found

**Solution**: Ensure `llm_service` section in config.yaml:
```yaml
llm_service:
  provider: "custom"
  api_keys:
    primary: ${oc.env:OPENROUTER_API_KEY}
  # ...
```

### Issue: Import errors

**Solution**: Add llm_service to Python path:
```python
import sys
sys.path.insert(0, '/code')
from llm_service import LLMService
```

### Issue: Logs not appearing

**Solution**: Check logging configuration:
```yaml
llm_service:
  logging:
    level: "metadata"  # Or higher: prompts, responses, full
    directory: "logs/llm_calls"
```

Ensure directory exists:
```bash
mkdir -p logs/llm_calls
```

### Issue: Dry-run returning strange data

**Solution**: This is expected! Dry-run generates deterministic mock data. For real testing, use validation mode:
```yaml
llm_service:
  modes:
    mode: "validation"
```

---

## Next Steps

### Immediate (Recommended)

1. **Test the new service**:
```bash
# Dry-run test
python -c "from llm_v2 import LLMClient; c = LLMClient('test', dry_run=True, use_centralized_service=True); print(c.populate_entity({'entity_id': 'test'}, {}))"
```

2. **Review logs**:
```bash
ls -lh logs/llm_calls/
```

3. **Run comparison test**:
```python
# Compare legacy vs new
from llm import LLMClient as Legacy
from llm_v2 import LLMClient as New

legacy = Legacy(api_key, dry_run=True)
new = New(api_key, dry_run=True, use_centralized_service=True)

# Both should produce similar outputs
```

### Short-term (Next Sprint)

1. **Add unit tests** for llm_service components
2. **Run autopilot suite** with new service
3. **Monitor performance** and cost metrics
4. **Gather feedback** from team

### Long-term (Future Enhancements)

1. **Implement Mirascope provider** for better structured outputs
2. **Add caching layer** for repeated queries
3. **Implement API key rotation** for rate limit handling
4. **Add streaming support** for real-time responses
5. **Create GraphQL interface** for external API access

---

## Support and Documentation

- **Migration Plan**: See `LLM-INTEGRATION-PLAN.md`
- **Service Code**: `/code/llm_service/`
- **Config**: `/code/conf/config.yaml`
- **Backward Compat**: `/code/llm_v2.py`

For questions or issues, refer to the implementation files or create a ticket.

---

## Summary

**Status**: ✅ Phase 1 Complete

The centralized LLM service is fully implemented and ready for use. Key benefits:

- **Unified interface** for all LLM operations
- **Comprehensive logging** with JSONL format
- **Advanced error handling** with retry logic
- **Security controls** for input/output filtering
- **Provider abstraction** for easy swapping
- **Backward compatibility** for gradual migration
- **Multiple modes** (production, dry-run, validation)
- **Session management** for cost tracking

Next step: Begin gradual migration by testing in dry-run mode, then validation mode, then production.
