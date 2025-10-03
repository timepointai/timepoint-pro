# LLM-CENTRALIZATION-PLAN.md

## Executive Summary

**Goal:** Migrate from scattered LLM calls across 15+ files to a centralized LLM service without breaking existing functionality.

**Strategy:** Phased migration with testing at each step, starting with abstraction layer, then gradual component migration.

**Testing Anchor:** Current autopilot test rig (58/58 tests passing) serves as baseline for non-regression.

---

## Pre-Migration Validation Checkpoint

### Baseline Test Run
- [ ] Run full autopilot test suite with real LLM calls
- [ ] Document current test results: `autopilot_baseline_pre_migration.json`
- [ ] Verify: 58/58 tests passing (or current stable baseline)
- [ ] Run deep integration tests: `test_deep_integration.py`
- [ ] Capture cost/token metrics from baseline run
- [ ] Store baseline outputs for comparison testing

### Test Infrastructure Verification
- [ ] Confirm `test_validation_system.py` operational
- [ ] Confirm `autopilot.py` quality filtering working
- [ ] Verify dry-run mode functions correctly
- [ ] Verify real LLM mode with OpenRouter API key

---

## Architecture Design

### Core Service Structure

```
LLMService (Facade/Coordinator)
├── LLMProvider (Interface/Abstract)
│   ├── MirascopeProvider (Implementation)
│   ├── CustomProvider (Future: direct OpenRouter)
│   └── TestProvider (Simplified testing)
├── PromptManager (System/User prompt assembly)
├── ResponseParser (JSON extraction, validation)
├── ContextInjector (Two-way context filtering)
├── SecurityFilter (Input bleaching, output sanitization)
├── ErrorHandler (Retry logic, failsoft responses)
├── CallLogger (Metadata + debug payload logging)
└── SessionManager (Session IDs, metadata tracking)
```

### Service Boundaries

**Public Services (Future External API):**
- Query processing with rate limiting
- Entity generation with safety controls
- Dialog synthesis with content filtering

**Private Services (Internal Only):**
- Training workflows
- Validation operations
- Test infrastructure
- Development/debugging tools

### Provider Interface Design

**Extensibility Requirements:**
```python
# Core interface that Mirascope or custom implementations satisfy
class LLMProvider(Protocol):
    def call(self, system: str, user: str, **params) -> LLMResponse
    def structured_call(self, system: str, user: str, schema: Type[BaseModel], **params) -> BaseModel
    def supports_streaming(self) -> bool
    def get_provider_name(self) -> str
```

**Decorator Strategy:**
```python
# Enable decoration at multiple levels
@llm_service.with_retry(max_attempts=3)
@llm_service.with_caching(ttl=300)
@llm_service.with_logging(level="full")
def generate_entity(entity_schema, context):
    return llm_service.call(...)
```

---

## Migration Call Site Inventory

### Phase 1 Target: Core LLM Methods (High Priority)

**File: `llm.py`**
- [ ] `LLMClient.populate_entity()` - Entity generation with structured output
- [ ] `LLMClient.generate_dialog()` - Dialog synthesis
- [ ] `LLMClient.validate_consistency()` - Consistency checking
- [ ] `LLMClient.score_relevance()` - Relevance scoring
- [ ] `LLMClient.generate_structured()` - Temporal expectations

**File: `workflows.py`**
- [ ] `create_entity_training_workflow()` - Async entity population (line 164)
- [ ] `synthesize_dialog()` - Dialog generation (line 723)
- [ ] `generate_prospective_state()` - Prospection (line 1178)
- [ ] `create_animistic_entity()` - Non-human entity generation

**File: `query_interface.py`**
- [ ] `QueryInterface.parse_query()` - Query intent extraction (line 121)
- [ ] `QueryInterface._synthesize_relationship_response()` - Multi-entity analysis (line 1203)
- [ ] `QueryInterface.score_relevance()` - Knowledge ranking (line 709)
- [ ] `QueryInterface.populate_entity()` - On-demand generation (line 641)

### Phase 2 Target: Advanced Features (Medium Priority)

**File: `resolution_engine.py`**
- [ ] Direct `chat.completions.create()` calls (line 275)
- [ ] Dynamic resolution prompts

**File: `cli.py`**
- [ ] Training workflow calls (lines 451, 558)
- [ ] Model testing calls (line 165)

**File: `ai_entity_service.py`**
- [ ] `AIEntityRunner.process_request()` - AI entity processing
- [ ] Integration with existing safety stack (bleaching, filtering)

### Phase 3 Target: Test Infrastructure (Low Priority)

**File: `test_deep_integration.py`**
- [ ] Real LLM integration tests (4 test methods)
- [ ] Verification of new service compatibility

**File: `test_error_handling_retry.py`**
- [ ] Retry mechanism validation
- [ ] Error handling tests

---

## Testing Strategy

### Test Modes

**1. Dry-Run Mode (Preserve Existing)**
- Returns mock data structure
- Zero cost, instant response
- Use case: Development, unit tests

**2. Validation Mode (NEW)**
- Uses lightweight model: `meta-llama/llama-3.1-8b-instruct`
- System prompt: `"Respond in Spanish"`
- User prompt: `"Say hello world"`
- Expected response: Contains Spanish greeting
- Use case: Integration testing, migration validation
- Cost: ~$0.001 per call
- Speed: <1 second

**3. Production Mode**
- Uses configured model (default: `meta-llama/llama-3.1-70b-instruct`)
- Full system/user prompts
- Full response parsing
- Use case: Real workloads

### Test Cases for Migration Validation

**Per-Component Test Checklist:**
- [ ] Test in validation mode (Spanish hello world)
- [ ] Test in dry-run mode (mock response)
- [ ] Test in production mode (real payload)
- [ ] Verify response structure matches old implementation
- [ ] Verify cost/token tracking
- [ ] Verify error handling (invalid JSON, API failure)
- [ ] Verify retry logic
- [ ] Verify logging output

**Integration Test Requirements:**
- [ ] Run full autopilot suite after each phase
- [ ] Compare outputs to baseline (structural equivalence)
- [ ] Verify no test failures introduced
- [ ] Check performance degradation <10%
- [ ] Validate cost increase <5%

---

## Detailed Requirements

### 1. Prompt Management

**System Prompt Requirements:**
- [ ] Global system prompt injection capability
- [ ] Per-call system prompt override
- [ ] Template variable substitution
- [ ] Version tracking for prompt changes
- [ ] Rotation/A-B testing support

**User Prompt Assembly:**
- [ ] Schema-to-prompt conversion for tensor structures
- [ ] Context building from Entity/Timepoint objects
- [ ] Multi-entity prompt composition
- [ ] Dialog context assembly

**Context Injection (Two-Way):**
- [ ] Pre-call context enrichment (add temporal awareness, entity relationships)
- [ ] Post-call context filtering (remove sensitive data, add disclaimers)
- [ ] Configurable injection rules per call type
- [ ] Passthrough mode for custom prompts

### 2. Response Parsing

**JSON Extraction:**
- [ ] Robust extraction from markdown code blocks
- [ ] Handling of extra text before/after JSON
- [ ] Multiple JSON object detection
- [ ] Fallback to regex extraction

**Schema Validation:**
- [ ] Pydantic model validation
- [ ] Type coercion for near-matches
- [ ] Field mapping (LLM response → schema fields)
- [ ] Partial validation (accept incomplete responses)

**Error Recovery:**
- [ ] Retry with JSON format reminder (max 2 attempts)
- [ ] Failsoft: Return null-filled schema
- [ ] Log malformed responses for analysis
- [ ] Optional manual fallback trigger

### 3. Parameterization

**OpenRouter Parameters (All Exposed):**
- [ ] `temperature` (default: 0.7, range: 0.0-2.0)
- [ ] `top_p` (default: 0.9, range: 0.0-1.0)
- [ ] `max_tokens` (default: 1000, range: 1-32768)
- [ ] `frequency_penalty` (default: 0.0, range: -2.0-2.0)
- [ ] `presence_penalty` (default: 0.0, range: -2.0-2.0)
- [ ] `model` (default: `meta-llama/llama-3.1-70b-instruct`)
- [ ] `stop` sequences (optional)
- [ ] `seed` for reproducibility (optional)

**Configuration Hierarchy:**
```
Global Config (config.yaml)
  ↓ override by
Component Defaults (per workflow/feature)
  ↓ override by
Call-Specific Parameters (per function call)
```

### 4. Error Handling

**Retry Strategy:**
- [ ] Exponential backoff (1s, 2s, 4s)
- [ ] Max 3 attempts
- [ ] Different error types trigger different behavior:
  - Rate limit: Wait and retry
  - Invalid JSON: Retry with format reminder
  - Timeout: Retry with reduced max_tokens
  - API error: Failsoft to null response

**Failsoft Behavior:**
- [ ] Generate null-filled response matching expected schema
- [ ] Log failure for monitoring
- [ ] Set `error` flag in response metadata
- [ ] Continue execution (don't crash)

**JSON Retry Protocol:**
```
Attempt 1: Original system + user prompt
  ↓ (if invalid JSON)
Attempt 2: Append "Your previous response was not valid JSON. 
           Please return ONLY a JSON object matching this schema: {schema}"
  ↓ (if still invalid)
Attempt 3: Simplified prompt with explicit example
  ↓ (if still invalid)
Failsoft: Return null-filled schema
```

### 5. Security & Safety

**Input Bleaching:**
- [ ] HTML tag removal (preserve content)
- [ ] Script injection prevention
- [ ] Prompt injection detection patterns
- [ ] Input length limits (configurable)
- [ ] SQL injection pattern detection

**Output Sanitization:**
- [ ] Extract JSON, discard wrapper text
- [ ] Never execute or eval LLM output
- [ ] Store as strings only
- [ ] PII detection and redaction (optional)
- [ ] Harmful content filtering (optional)

**Database Safety:**
- [ ] Extract structured data from LLM response
- [ ] Validate against schema before storage
- [ ] Store only extracted fields, not raw JSON
- [ ] Sanitize string fields before DB write

### 6. Logging

**Metadata Logging (Always On):**
```json
{
  "timestamp": "2025-10-03T10:30:45Z",
  "session_id": "abc-123",
  "call_type": "populate_entity",
  "model": "meta-llama/llama-3.1-70b-instruct",
  "parameters": {"temperature": 0.7, "max_tokens": 1000},
  "tokens_used": {"prompt": 150, "completion": 450, "total": 600},
  "cost_usd": 0.012,
  "latency_ms": 1234,
  "success": true,
  "retry_count": 0,
  "error": null
}
```

**Debug Logging (Optional, Flag-Based):**
```json
{
  ...metadata...,
  "system_prompt": "You are an AI entity...",
  "user_prompt": "Generate entity information for...",
  "response_full": "Here is the JSON:\n```json\n{...}\n```",
  "response_parsed": {"entity_id": "washington", ...}
}
```

**Log Levels:**
- [ ] `metadata`: Session ID, model, tokens, cost, success
- [ ] `prompts`: Add system/user prompts (truncated to 500 chars)
- [ ] `responses`: Add LLM responses (truncated to 1000 chars)
- [ ] `full`: Complete payloads (no truncation)

**Log Storage:**
- [ ] JSON lines format: `logs/llm_calls_YYYY-MM-DD.jsonl`
- [ ] Rotation: Daily
- [ ] Retention: 30 days
- [ ] Optional: Stream to monitoring service

### 7. Session Management

**Session ID Requirements:**
- [ ] UUID v4 generation
- [ ] Thread-local storage for context
- [ ] Session metadata: user, workflow, purpose
- [ ] Session lifecycle tracking (start, end, duration)

**Session Context:**
```python
{
  "session_id": "abc-123",
  "workflow": "temporal_train",
  "user": "system",
  "started_at": "2025-10-03T10:00:00Z",
  "calls_count": 0,
  "total_cost": 0.0,
  "metadata": {}
}
```

### 8. LangGraph Integration

**Service-Level LangGraph Support:**
- [ ] Node factory: Convert LLM calls into LangGraph nodes
- [ ] State management: Pass entity/timepoint state through graphs
- [ ] Async execution: Support parallel LLM calls
- [ ] Error propagation: Handle failures in graph context

**Requirements:**
- [ ] Don't replace existing LangGraph usage
- [ ] Provide convenience wrappers
- [ ] Enable declarative graph construction
- [ ] Support streaming results

**Example Pattern:**
```python
# Service provides helper to create LLM-calling nodes
entity_node = llm_service.as_langgraph_node(
    name="populate_entity",
    input_keys=["entity_schema", "context"],
    output_keys=["populated_entity"]
)
```

### 9. API Key Management

**Rotation Support:**
- [ ] Multiple API keys in config
- [ ] Round-robin or random selection
- [ ] Per-key rate limiting
- [ ] Automatic key cycling on rate limit
- [ ] Dead key detection and removal

**Configuration:**
```yaml
llm_service:
  api_keys:
    - key: ${OPENROUTER_API_KEY_1}
      weight: 1.0
      max_rpm: 60
    - key: ${OPENROUTER_API_KEY_2}
      weight: 0.5
      max_rpm: 30
  rotation_strategy: "round_robin"  # or "weighted", "random"
```

---

## Schema Integration Analysis

### Current Tensor-to-Prompt Patterns

**Pattern 1: Entity Schema → LLM → EntityPopulation**
```
Input: Entity(entity_id, entity_type, timepoint, context)
Prompt: "Generate entity information for {entity_id}..."
Output: EntityPopulation(knowledge_state, energy_budget, personality_traits, ...)
Storage: Entity.entity_metadata = {populated fields}
```

**Pattern 2: Timepoint/Entities → LLM → Dialog**
```
Input: List[Entity], Timepoint, context
Prompt: "Generate conversation between {participants}..."
Output: DialogData(turns, information_exchanged, ...)
Storage: Dialog table with JSON serialized turns
```

**Pattern 3: Entity State → LLM → ProspectiveState**
```
Input: Entity, current knowledge, personality
Prompt: "Generate entity's expectations about future..."
Output: ProspectiveState(expectations, anxiety_level, ...)
Storage: ProspectiveState table
```

### Service Requirements for Schema Handling

**Tensor Label Conversion:**
- [ ] PhysicalTensor → Human-readable prompt section
- [ ] CognitiveTensor → Emotional/knowledge context
- [ ] Entity metadata → Structured context for LLM

**Response Schema Mapping:**
- [ ] LLM JSON → Pydantic model validation
- [ ] Field name normalization (case, underscores)
- [ ] Type coercion (string → int, list → set)
- [ ] Nested object reconstruction

**Example Service Methods:**
```python
llm_service.call_with_entity_schema(
    entity: Entity,
    response_model: Type[BaseModel],
    additional_context: Dict
) -> BaseModel

llm_service.call_with_tensor_context(
    physical: PhysicalTensor,
    cognitive: CognitiveTensor,
    instruction: str,
    response_schema: Type[BaseModel]
) -> BaseModel
```

---

## Migration Phases

### Phase 0: Preparation (Testing Baseline)

**Duration:** 1 day

**Tasks:**
- [ ] Run baseline test suite
- [ ] Document current test results
- [ ] Capture baseline metrics
- [ ] Set up migration branch
- [ ] Review LLM-MAP.md inventory

**Exit Criteria:**
- [ ] Baseline tests documented
- [ ] All tests passing
- [ ] Migration branch created

---

### Phase 1: Core Service Implementation

**Duration:** 2-3 days

**Tasks:**

**1.1 Create Service Architecture**
- [ ] Create `llm_service/` directory structure
- [ ] Implement `LLMProvider` protocol/interface
- [ ] Implement `TestProvider` with validation mode
- [ ] Implement `MirascopeProvider` wrapper
- [ ] Create `LLMService` facade

**1.2 Implement Core Components**
- [ ] `PromptManager`: System/user prompt assembly
- [ ] `ResponseParser`: JSON extraction + validation
- [ ] `ErrorHandler`: Retry logic + failsoft
- [ ] `CallLogger`: Metadata + debug logging
- [ ] `SecurityFilter`: Input bleaching + output sanitization

**1.3 Configuration Integration**
- [ ] Add `llm_service` section to `conf/config.yaml`
- [ ] Parameter defaults and overrides
- [ ] API key rotation config
- [ ] Logging level config

**1.4 Testing**
- [ ] Unit tests for each component
- [ ] Validation mode tests (Spanish hello world)
- [ ] Dry-run mode tests
- [ ] Error handling tests

**Exit Criteria:**
- [ ] All components implemented
- [ ] Unit tests passing
- [ ] Validation mode working
- [ ] No changes to existing LLM calls yet

---

### Phase 2: Migrate `llm.py` Methods

**Duration:** 2 days

**Tasks:**

**2.1 Wrap Existing LLMClient**
- [ ] Create `LLMClient.v2` using new service
- [ ] Implement `populate_entity()` via service
- [ ] Implement `generate_dialog()` via service
- [ ] Implement `validate_consistency()` via service
- [ ] Implement `score_relevance()` via service
- [ ] Implement `generate_structured()` via service

**2.2 Backward Compatibility**
- [ ] Keep old methods as deprecated wrappers
- [ ] Add feature flag: `use_centralized_llm: true/false`
- [ ] Default to old behavior initially

**2.3 Testing**
- [ ] Test each method in validation mode
- [ ] Test each method in production mode
- [ ] Compare outputs to old implementation
- [ ] Run full autopilot suite with new service
- [ ] Verify test parity (same pass/fail results)

**Exit Criteria:**
- [ ] All LLMClient methods working via service
- [ ] Tests passing with new implementation
- [ ] Outputs structurally equivalent to baseline
- [ ] Performance within 10% of baseline

---

### Phase 3: Migrate `workflows.py`

**Duration:** 2-3 days

**Tasks:**

**3.1 Update Workflow LLM Calls**
- [ ] `create_entity_training_workflow()` → new service
- [ ] `synthesize_dialog()` → new service
- [ ] `generate_prospective_state()` → new service
- [ ] `create_animistic_entity()` → new service

**3.2 LangGraph Integration**
- [ ] Create LangGraph node helpers
- [ ] Update async entity population
- [ ] Maintain existing graph structure

**3.3 Testing**
- [ ] Test entity generation workflows
- [ ] Test dialog synthesis
- [ ] Test animistic entity creation
- [ ] Run `test_animistic_entities.py`
- [ ] Run `test_modal_temporal_causality.py`

**Exit Criteria:**
- [ ] All workflow LLM calls using service
- [ ] Workflow tests passing
- [ ] No regressions in entity/dialog generation

---

### Phase 4: Migrate `query_interface.py`

**Duration:** 2 days

**Tasks:**

**4.1 Update Query Processing**
- [ ] `parse_query()` → new service
- [ ] `_synthesize_relationship_response()` → new service
- [ ] `score_relevance()` → new service
- [ ] `populate_entity()` → new service

**4.2 Context Injection Integration**
- [ ] Implement two-way context filtering
- [ ] Add query-specific context enrichment
- [ ] Maintain response quality

**4.3 Testing**
- [ ] Test query parsing
- [ ] Test relationship synthesis
- [ ] Test on-demand entity generation
- [ ] Run `test_phase3_dialog_multi_entity.py`

**Exit Criteria:**
- [ ] All query interface calls using service
- [ ] Query tests passing
- [ ] Response quality maintained

---

### Phase 5: Migrate Remaining Components

**Duration:** 2 days

**Tasks:**

**5.1 Resolution Engine**
- [ ] Migrate `resolution_engine.py` direct API calls
- [ ] Update to use service

**5.2 CLI Integration**
- [ ] Update `cli.py` training calls
- [ ] Update model testing
- [ ] Preserve all CLI functionality

**5.3 AI Entity Service**
- [ ] Integrate with centralized service
- [ ] Maintain existing safety stack
- [ ] Unify logging and monitoring

**5.4 Testing**
- [ ] Test resolution engine
- [ ] Test CLI workflows
- [ ] Test AI entity service
- [ ] Run `test_ai_entity_service.py`

**Exit Criteria:**
- [ ] All components using centralized service
- [ ] Component tests passing
- [ ] No functionality lost

---

### Phase 6: Cleanup & Optimization

**Duration:** 1-2 days

**Tasks:**

**6.1 Remove Old Code**
- [ ] Remove deprecated LLMClient methods
- [ ] Remove duplicate error handling
- [ ] Remove scattered cost tracking
- [ ] Consolidate logging

**6.2 Configuration Cleanup**
- [ ] Remove old LLM config entries
- [ ] Consolidate to `llm_service` section
- [ ] Update documentation

**6.3 Performance Optimization**
- [ ] Profile LLM call latency
- [ ] Optimize prompt assembly
- [ ] Tune caching strategies
- [ ] Review cost metrics

**Exit Criteria:**
- [ ] No deprecated code remaining
- [ ] Clean configuration structure
- [ ] Performance at or better than baseline

---

### Phase 7: Final Validation

**Duration:** 1 day

**Tasks:**

**7.1 Comprehensive Testing**
- [ ] Run full autopilot suite (real LLM calls)
- [ ] Run deep integration tests
- [ ] Run all mechanism-specific tests
- [ ] Compare to baseline metrics

**7.2 Documentation**
- [ ] Update README.md with new architecture
- [ ] Document LLM service API
- [ ] Update MECHANICS.md integration points
- [ ] Create migration changelog

**7.3 Metrics Validation**
- [ ] Compare test pass rates
- [ ] Compare cost metrics
- [ ] Compare performance
- [ ] Validate logging output

**Exit Criteria:**
- [ ] All tests passing (≥ baseline)
- [ ] Cost within 5% of baseline
- [ ] Performance within 10% of baseline
- [ ] Documentation complete

---

## Post-Migration Validation Checkpoint

### Final Test Run
- [ ] Run full autopilot test suite with real LLM calls
- [ ] Document final test results: `autopilot_post_migration.json`
- [ ] Verify: Same or better test pass rate
- [ ] Run deep integration tests
- [ ] Compare cost/token metrics to baseline
- [ ] Validate outputs match baseline structure

### Acceptance Criteria
- [ ] Test pass rate: ≥ baseline (58/58 or equivalent)
- [ ] Cost increase: ≤ 5%
- [ ] Performance degradation: ≤ 10%
- [ ] Zero new test failures introduced
- [ ] All LLM calls centralized
- [ ] Logging functional and complete

### Rollback Plan
If acceptance criteria not met:
- [ ] Revert to migration branch parent commit
- [ ] Restore baseline configuration
- [ ] Document failure reasons
- [ ] Create remediation plan
- [ ] Re-test baseline

---

## Risk Mitigation

### High-Risk Areas

**1. Structured Output Changes**
- Risk: Response parsing differences break downstream code
- Mitigation: Extensive comparison testing, schema validation
- Rollback: Feature flag to old implementation

**2. Performance Degradation**
- Risk: Service overhead slows LLM calls
- Mitigation: Profile at each phase, optimize hot paths
- Rollback: Direct API calls for critical paths

**3. Error Handling Gaps**
- Risk: New error patterns not caught
- Mitigation: Comprehensive error scenario testing
- Rollback: Preserve old error handling as fallback

**4. Test Flakiness**
- Risk: Slight LLM response variations fail tests
- Mitigation: Structural comparison, not exact match
- Rollback: Adjust test expectations

### Monitoring During Migration

**Per-Phase Checks:**
- [ ] Run relevant test subset
- [ ] Check for new errors/warnings
- [ ] Validate response structure
- [ ] Compare cost/performance
- [ ] Review logs for issues

**Red Flags (Trigger Rollback):**
- Test pass rate drops >5%
- Cost increases >10%
- Performance degrades >20%
- Critical functionality broken
- Data corruption detected

---

## Configuration Schema

### New `conf/config.yaml` Section

```yaml
llm_service:
  # Provider configuration
  provider: "mirascope"  # or "custom", "test"
  base_url: "https://openrouter.ai/api/v1"
  
  # API key management
  api_keys:
    primary: ${OPENROUTER_API_KEY}
    # rotation: [] # Future: multiple keys
  
  # Default parameters
  defaults:
    model: "meta-llama/llama-3.1-70b-instruct"
    temperature: 0.7
    top_p: 0.9
    max_tokens: 1000
    frequency_penalty: 0.0
    presence_penalty: 0.0
  
  # Testing modes
  modes:
    dry_run: false  # Mock responses
    validation: false  # Lightweight testing
    production: true  # Full functionality
  
  # Validation mode config
  validation_mode:
    model: "meta-llama/llama-3.1-8b-instruct"
    system_prompt: "Respond in Spanish"
    user_prompt: "Say hello world"
    expected_pattern: "(?i)(hola|buenos días)"
  
  # Error handling
  error_handling:
    max_retries: 3
    backoff_base: 1.0
    backoff_multiplier: 2.0
    failsoft_enabled: true
    retry_on_invalid_json: true
  
  # Logging
  logging:
    level: "metadata"  # metadata, prompts, responses, full
    directory: "logs/llm_calls"
    rotation: "daily"
    retention_days: 30
  
  # Security
  security:
    input_bleaching: true
    output_sanitization: true
    max_input_length: 50000
    dangerous_patterns:
      - "(?i)ignore.*previous.*instructions"
      - "(?i)forget.*system.*prompt"
  
  # Performance
  performance:
    caching_enabled: true
    cache_ttl: 300
    timeout_seconds: 30
  
  # Session management
  sessions:
    enabled: true
    id_prefix: "llm_"
```

---

## Success Metrics

### Quantitative Metrics
- [ ] Test pass rate maintained or improved
- [ ] Cost increase < 5%
- [ ] Latency increase < 10%
- [ ] Zero data loss or corruption
- [ ] 100% LLM call centralization

### Qualitative Metrics
- [ ] Code maintainability improved
- [ ] Error messages more informative
- [ ] Logging more comprehensive
- [ ] Testing more reliable
- [ ] Future LLM provider switching easier

### Developer Experience
- [ ] Single place to update LLM logic
- [ ] Consistent error handling
- [ ] Better debugging tools
- [ ] Clearer code organization
- [ ] Easier onboarding for new developers

---

## Future Enhancements (Post-Migration)

### Phase 8+ (Optional)
- [ ] External query API with rate limiting
- [ ] Advanced caching strategies
- [ ] Cost optimization based on usage patterns
- [ ] A/B testing for prompts
- [ ] Multi-provider fallback
- [ ] Streaming response support
- [ ] Advanced observability (tracing, metrics)
- [ ] Cost budgeting and alerts
- [ ] Custom Mirascope replacement
- [ ] GraphQL query interface

---

## Appendix: Testing Commands

### Baseline Test
```bash
source .env && source venv/bin/activate
python autopilot.py --force --output baseline_pre_migration.json
```

### Phase Validation Test
```bash
# Quick validation mode test
LLM_SERVICE_MODE=validation python -m pytest test_deep_integration.py -v

# Full autopilot with new service
python autopilot.py --force --output phase_N_results.json
```

### Comparison Test
```bash
# Compare baseline to current
python scripts/compare_test_results.py \
  baseline_pre_migration.json \
  phase_N_results.json
```

### Final Validation Test
```bash
source .env && source venv/bin/activate
python autopilot.py --force --parallel --workers 2 --output final_post_migration.json
```