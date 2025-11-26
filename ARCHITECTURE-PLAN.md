# ARCHITECTURE-PLAN.md - Timepoint-Daedalus Refactoring Plan

**Created:** November 25, 2025
**Status:** Phase 2 COMPLETE + M18 Model Selection COMPLETE, Phase 3 pending
**Health Score:** 6.2/10 → 7.5/10 → Target: 8.0/10

---

## Executive Summary

Timepoint-Daedalus is a sophisticated temporal simulation system with 18 mechanisms, now with improved architectural stability. This plan tracks the transformation from "working research prototype" to "maintainable product."

**Key Issues (Original):**
1. ~~Circular dependencies in core imports~~ FIXED
2. Fragmented orchestration (two parallel systems)
3. ~~17 mechanisms tracked but not architecturally integrated~~ 18 mechanisms, integrated
4. ~~NL Interface has zero integration~~ FIXED (NLToProductionAdapter)
5. God classes (workflows/__init__.py = 3,041 lines) - pending

**New Capabilities:**
- M18: Intelligent per-action model selection with fallback chains
- License-compliant open-source model registry (MIT, Apache 2.0, Llama, Qwen)

**Timeline:** 3-4 weeks for all phases

---

## Current Architecture Assessment

### File Sizes (Lines of Code)
| File | Lines | Status |
|------|-------|--------|
| workflows/__init__.py | 3,041 | CRITICAL - God class |
| orchestrator.py | 1,665 | HIGH - Complex |
| e2e_workflows/e2e_runner.py | 1,421 | HIGH - Duplicate logic |
| validation.py | 1,365 | OK |
| llm_v2.py | 992 | OK |
| schemas.py | 638 | OK |
| storage.py | 407 | GOOD |

### Dependency Issues
```
orchestrator.py
├── workflows/__init__.py (TemporalAgent, create_entity_training_workflow)
│   ├── llm.py (EntityPopulation) ← Should be in schemas.py
│   ├── schemas.py (Entity, ResolutionLevel, etc.)
│   └── validation.py (Validator)
│       └── workflows (deferred imports) ← Circular!
└── llm_v2.py
    └── llm.py (EntityPopulation, ValidationResult) ← Should be in schemas.py
```

### What Works Well
- Storage layer (`storage.py`) - Clean CRUD abstractions
- Dashboard (Quarto + FastAPI) - Production ready
- Portal mode (M17) - Sophisticated backward reasoning
- Model selection (M18) - 12 open-source models, capability-based selection
- NL Interface - Integrated via NLToProductionAdapter
- Test coverage - 18/18 mechanisms tracked, E2E tests pass

---

## Phase 1: Stabilize (Week 1-2)

### 1.1 Fix Circular Dependencies

**Problem:** `EntityPopulation` and `ValidationResult` are in `llm.py` but imported everywhere.

**Solution:** Move to `schemas.py` where they belong (Pydantic models with data models).

**Files to modify:**
- `llm.py` - Remove class definitions, add re-export for backward compat
- `schemas.py` - Add EntityPopulation, ValidationResult
- `llm_v2.py` - Update import
- `workflows/__init__.py` - Update import

### 1.2 Break workflows/__init__.py (3,041 lines)

**Target structure:**
```
workflows/
├── __init__.py              # Re-exports only (~50 lines)
├── portal_strategy.py       # (existing, keep as-is)
├── entity_training.py       # WorkflowState, training workflow
├── scene_environment.py     # Scene atmosphere, crowd dynamics
├── dialog_synthesis.py      # synthesize_dialog + helpers
├── relationship_analysis.py # Relationship evolution, contradictions
├── prospection.py           # Entity prospection (M15)
├── counterfactual.py        # Branching timelines (M12)
├── animistic.py             # Animistic entities (M16)
├── temporal_agent.py        # TemporalAgent class
└── utils.py                 # Shared utility functions
```

**Mapping:**
| Function/Class | Target Module |
|----------------|---------------|
| WorkflowState | entity_training.py |
| create_entity_training_workflow | entity_training.py |
| retrain_high_traffic_entities | entity_training.py |
| create_environment_entity | scene_environment.py |
| compute_scene_atmosphere | scene_environment.py |
| compute_crowd_dynamics | scene_environment.py |
| synthesize_dialog | dialog_synthesis.py |
| analyze_relationship_evolution | relationship_analysis.py |
| detect_contradictions | relationship_analysis.py |
| synthesize_multi_entity_response | relationship_analysis.py |
| generate_prospective_state | prospection.py |
| influence_behavior_from_expectations | prospection.py |
| create_counterfactual_branch | counterfactual.py |
| compare_timelines | counterfactual.py |
| create_animistic_entity | animistic.py |
| generate_animistic_entities_for_scene | animistic.py |
| TemporalAgent | temporal_agent.py |

### 1.3 Preserve Backward Compatibility

**`workflows/__init__.py` becomes:**
```python
"""Workflows module - re-exports for backward compatibility."""

from workflows.entity_training import (
    WorkflowState,
    create_entity_training_workflow,
    retrain_high_traffic_entities,
)
from workflows.scene_environment import (
    create_environment_entity,
    compute_scene_atmosphere,
    compute_crowd_dynamics,
)
# ... etc for all exports

__all__ = [
    "WorkflowState",
    "create_entity_training_workflow",
    # ... all public names
]
```

### 1.4 Success Criteria
- [x] No circular import errors at runtime ✅ (EntityPopulation/ValidationResult moved to schemas.py)
- [x] `pytest tests/ -v` passes (all existing tests) ✅ (19/19 orchestrator tests passing)
- [x] `from workflows import X` still works for all X ✅ (backward compat re-exports added)
- [ ] No file > 800 lines in workflows/ (workflows/__init__.py still 3,041 lines - pending)

---

## Phase 2: Integrate (Week 2-3)

### 2.1 Wire NL Interface into Pipeline

**Problem:** `nl_interface/` (1,791 lines) exists but is never called from main pipeline.

**Solution:** Add `--nl` mode to e2e_runner.py:
```bash
./run.sh --nl "Simulate a board meeting where CFO reveals bankruptcy"
```

**Files to modify:**
- `run_all_mechanism_tests.py` - Add --nl flag
- `e2e_workflows/e2e_runner.py` - Accept NL input, use NLConfigGenerator
- `nl_interface/nl_to_config.py` - Ensure output matches SimulationConfig

### 2.2 Connect M3 → M11 (Exposure Events → Dialog)

**Problem:** Dialog synthesis ignores exposure events, uses tensor directly.

**Solution:** `synthesize_dialog()` should query exposure events:
```python
# Before (ignores exposure history)
knowledge = entity.entity_metadata.get('cognitive_tensor', {}).get('knowledge_state', [])

# After (uses exposure events)
exposure_events = store.get_exposure_events_for_entity(entity.entity_id)
knowledge = [e.information for e in exposure_events]
```

### 2.3 Make M1 Affect M17 (Fidelity → Generation Granularity)

**Problem:** Resolution levels assigned but don't change generation.

**Solution:** TemporalAgent checks entity.resolution_level:
- TENSOR_ONLY → Minimal generation (100 tokens)
- SCENE → Standard generation (1k tokens)
- DIALOG → Detailed generation (5k tokens)

### 2.4 Success Criteria
- [x] `./run.sh --nl "prompt"` generates valid simulation ✅ (NLToProductionAdapter + --nl flag added)
- [x] Dialog includes knowledge from exposure events ✅ (_build_knowledge_from_exposures() in dialog_synthesis.py)
- [x] TENSOR_ONLY entities have smaller token footprint than DIALOG entities ✅ (RESOLUTION_TOKEN_BUDGET in temporal_agent.py)

---

## Phase 2.5: Intelligent Model Selection (COMPLETE)

### 2.5.1 M18: Capability-Based Model Selection

**Problem:** All LLM calls use a single model, regardless of task requirements. Math-heavy tasks should use reasoning models; dialog should use conversational models.

**Solution:** Created `llm_service/model_selector.py` with:

| Component | Description |
|-----------|-------------|
| `ActionType` enum | 16 action categories (DIALOG_SYNTHESIS, TEMPORAL_REASONING, etc.) |
| `ModelCapability` enum | 15 capability dimensions (STRUCTURED_JSON, MATHEMATICAL, etc.) |
| `ModelProfile` dataclass | Model metadata (capabilities, context size, speed, cost, quality) |
| `MODEL_REGISTRY` | 12 open-source models with license compliance |
| `ModelSelector` class | Selection algorithm with preference weighting |

**Files created/modified:**
- `llm_service/model_selector.py` (NEW - ~700 lines)
- `llm_service/service.py` (MODIFIED - added action-aware methods)
- `llm_service/__init__.py` (MODIFIED - added exports)

### 2.5.2 License-Compliant Model Registry

Only models permitting commercial synthetic data generation:

| License | Models |
|---------|--------|
| **MIT** | DeepSeek Chat, DeepSeek R1 |
| **Apache 2.0** | Mistral 7B, Mixtral 8x7B, Mixtral 8x22B |
| Llama 3.1 | Llama 3.1 8B/70B/405B |
| Llama 4 | Llama 4 Scout |
| Qwen | Qwen 2.5 7B/72B, QwQ 32B |

**Excluded:** OpenAI, Anthropic, Google (commercial/synthetic data restrictions)

### 2.5.3 Integration with LLMService

```python
from llm_service import LLMService, ActionType

service = LLMService(config)

# Automatic model selection
response = service.call_with_action(
    action=ActionType.DIALOG_SYNTHESIS,
    system="Generate dialog",
    user="Two founders discussing...",
    use_fallback_chain=True
)

# Structured output
entity = service.structured_call_with_action(
    action=ActionType.ENTITY_POPULATION,
    system="Generate profile",
    user="Skeptical board member",
    schema=EntityProfile
)
```

### 2.5.4 Success Criteria
- [x] Model selection based on action type ✅
- [x] Fallback chains for reliability ✅
- [x] Only license-compliant models ✅
- [x] Integration with existing LLMService ✅
- [x] Documentation updated (README.md, MECHANICS.md) ✅

---

## Phase 3: Polish (Week 3-4)

### 3.1 Move Hardcoded Configs to JSON

**Problem:** `generation/config_schema.py` has 26 `example_*()` methods (800+ lines).

**Solution:** Move to `generation/templates/`:
```
generation/templates/
├── board_meeting.json
├── jefferson_dinner.json
├── portal_presidential_election.json
└── ... (26 templates)
```

Load at runtime:
```python
config = SimulationConfig.from_template("board_meeting")
```

### 3.2 Add Transaction Support to Storage

**Problem:** Multiple save calls could leave DB inconsistent.

**Solution:**
```python
with store.transaction():
    store.save_entity(entity)
    store.save_timepoint(timepoint)
    store.save_exposure_event(event)
    # All succeed or all rollback
```

### 3.3 Dashboard Landing Page

**Problem:** No clear entry point for new users.

**Solution:** Create `dashboards/home.qmd`:
- Quick stats cards (recent runs, success rate, total cost)
- Links to Browse Runs, Analytics
- Status indicator (is API running?)

### 3.4 Success Criteria
- [ ] config_schema.py < 400 lines
- [ ] `store.transaction()` context manager works
- [ ] Dashboard has welcoming home page

---

## Risk Mitigation

### Phase 1 Risks
| Risk | Mitigation |
|------|------------|
| Breaking imports | Keep re-exports in `__init__.py` |
| Missing function | Grep for all usages before moving |
| Test failures | Run full test suite after each file move |

### Phase 2 Risks
| Risk | Mitigation |
|------|------------|
| NL output format mismatch | Validate against SimulationConfig schema |
| Performance regression | Benchmark before/after exposure event queries |
| Fidelity changes break tests | Add resolution_level parameter with default |

### Phase 3 Risks
| Risk | Mitigation |
|------|------------|
| Template loading failures | Keep 3 canonical examples in source as fallback |
| Transaction deadlocks | Use SQLite WAL mode, add timeout |

---

## Metrics

### Before Refactoring
- workflows/__init__.py: 3,041 lines
- Circular dependencies: 2 confirmed
- NL integration: 0%
- M3→M11 integration: 0%
- M1→M17 integration: 0%
- Model selection: None (single model for all tasks)

### After Phase 2 + 2.5 (Current)
- NL integration: 100% ✅ (NLToProductionAdapter, --nl flag)
- M3→M11 integration: 100% ✅ (_build_knowledge_from_exposures in dialog_synthesis.py)
- M1→M17 integration: 100% ✅ (RESOLUTION_TOKEN_BUDGET, fidelity-aware generate_next_timepoint)
- M18 Model Selection: 100% ✅ (llm_service/model_selector.py)
- Total mechanisms: 18 (was 17)
- License-compliant model registry: 12 models

### After Phase 1 (Pending)
- Largest workflow file: <800 lines
- Circular dependencies: 0
- All tests passing: Yes

### After Phase 3 (Target)
- NL integration: 100%
- M3→M11 integration: 100%
- M1→M17 integration: 100%
- M18 model selection: 100%
- Health score: 8.0/10

---

## Next Steps

1. **Phase 1** (pending)
   - Break workflows/__init__.py into 9 submodules (~3,041 lines → <800 per file)
   - Update imports, run tests

2. ~~**Phase 2**~~ COMPLETE
   - ~~Wire NL interface~~ ✅
   - ~~Connect M3→M11~~ ✅
   - ~~Implement fidelity-aware generation~~ ✅

3. ~~**Phase 2.5**~~ COMPLETE
   - ~~M18 model selection~~ ✅
   - ~~License-compliant model registry~~ ✅
   - ~~Documentation updates~~ ✅

4. **Phase 3** (future session)
   - Move configs to JSON templates
   - Add transaction support to storage
   - Dashboard landing page

---

**Related Documents:**
- [MILESTONES.md](MILESTONES.md) - Long-term platform roadmap (Phases 1-7)
- [MECHANICS.md](MECHANICS.md) - Technical specification of all 18 mechanisms
- [README.md](README.md) - Quick start and overview

**Document maintained by:** Architecture refactoring effort
**Last updated:** November 26, 2025
