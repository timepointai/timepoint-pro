# Project Configuration (AI Agent Reference)

## Philosophy

**Core Insight**: Temporal simulation isn't one problem—it's at least five different problems depending on what "time" means. This codebase treats temporal mode as a first-class architectural dimension.

**Design Principles**:
- **Fidelity follows attention**: Resolution is heterogeneous and query-driven. Most entities stay at TENSOR_ONLY (~200 tokens). Detail concentrates where queries land.
- **Knowledge has provenance**: Entities can't magically know things. Every fact has a tracked exposure event (who learned what, from whom, when).
- **Modes change semantics**: PEARL mode forbids anachronisms. CYCLICAL mode permits bootstrap paradoxes. DIRECTORIAL mode allows dramatic coincidences. Each mode has its own validation rules.
- **Templates are patches**: Like a synthesizer, scenarios are saved configurations. JSON templates capture reproducible "sounds" (scenario shapes).

**Code Philosophy**:
- Pythonic: type hints, dataclasses, protocols
- SQLite persistence (metadata/runs.db for runs, timepoint.db for temp), FastAPI backend
- TDD: pytest with mechanism markers (M1-M19)
- SynthasAIzer paradigm: templates as "patches", ADSR envelopes for entity lifecycle

## Stack
Python 3.10+, FastAPI, Pydantic, pytest, ruff, mypy

## Standards
- Type hints mandatory
- Google docstrings with examples
- Line length: 100
- Logging not print
- Use `TemplateLoader` for template access (not deprecated `SimulationConfig.example_*()`)

## Temporal Mode Architecture

Each mode has a dedicated strategy class in `workflows/`:

| Mode | Strategy Class | Key Affordance |
|------|---------------|----------------|
| PEARL | (default forward) | Strict causality, knowledge provenance |
| PORTAL | `PortalStrategy` | Backward inference, pivot detection |
| BRANCHING | `BranchingStrategy` | Counterfactual timelines |
| DIRECTORIAL | `DirectorialStrategy` | Five-act arcs, camera system, dramatic irony |
| CYCLICAL | `CyclicalStrategy` | Prophecy system, causal loops, cycle semantics |

Strategies share a common interface: `run(config) -> List[Path]`. Each path contains states with mode-specific metadata (tension scores for DIRECTORIAL, cycle positions for CYCLICAL, etc.).

## Key Commands
```bash
./run.sh list                    # List all 13 verified templates
./run.sh run board_meeting       # Run single template
./run.sh run --category core     # Run by category
./run.sh quick                   # Quick tier tests
./run.sh run <template> --portal-simjudged-quick  # Portal mode with sim-judging
./run.sh run <template> --portal-quick           # Portal quick mode (5 steps)
```

## Testing
```bash
pytest -v -m synth               # SynthasAIzer tests
pytest -v -m mechanism           # All M1-M19 tests
pytest -v -m "m1 or m7"          # Specific mechanisms
```

## Recent Fixes (January 2026)

### Portal Mode Enhancements
- **Preserve All Paths**: `preserve_all_paths=True` returns ALL generated paths (not just top N) for full analysis
- **Divergence Detection**: Identifies where paths diverge with clustering analysis (`high_coherence`, `medium`, `low`)
- **Quick Mode**: `--portal-quick` reduces backward_steps to 5 for fast demos (~15 min vs 1+ hour)
- **Fidelity Scaling**: Templates now scale proportionally with backward_steps (no longer hardcoded)

**Files:** `workflows/portal_strategy.py`, `workflows/temporal_agent.py`, `run_all_mechanism_tests.py`, `run.sh`

### Entity Inference in Portal Mode
Portal mode now infers `entities_present` for each timepoint using LLM-based entity identification instead of blind copying from consequent timepoints.

**Files:** `workflows/temporal_agent.py:_infer_entities_for_timepoint()`, `workflows/portal_strategy.py:_infer_entities_from_description()`

### Entity Fallback in Portal Mode
Added fallback logic when `_filter_entities_by_relevance()` returns an empty list (because LLM-generated antecedent descriptions don't explicitly mention entity names). The fix inherits all parent entities instead of leaving `entities_present` empty.

**Files:** `workflows/portal_strategy.py:_generate_antecedents()` (lines 788-791), `workflows/portal_strategy.py:_generate_placeholder_antecedents()` (lines 844-847)

### Data Quality Validation
Added `_run_data_quality_check()` in e2e_runner.py that validates:
- All timepoints have non-empty `entities_present`
- All entity references point to existing entities
- No duplicate entity IDs

### Entity Persistence to Shared DB
Entities now sync to metadata/runs.db alongside timepoints for convergence analysis.

**Files:** `e2e_workflows/e2e_runner.py:_persist_entity_for_convergence()`, `_persist_all_entities_for_convergence()`

### Timepoint Validation Warning
`schemas.py:Timepoint.__init__()` now emits `UserWarning` when `entities_present` is empty.

### Template Name Normalization
Template names now accept both slash and underscore formats interchangeably:
- `./run.sh run showcase/board_meeting` works the same as
- `./run.sh run board_meeting`

**Files:** `run_all_mechanism_tests.py:run_single_template()`

### Pivot Point Detection Fix
Rewrote `_detect_pivot_points()` in portal_strategy.py. The original checked `children_states` which was never populated during backward simulation (always returned 0 pivot points).

**New 4-strategy detection:**
1. **Divergence-based**: Uses `key_divergence_points` from path divergence analysis
2. **Keyword-based**: Detects pivot language ("decision", "pivoted", "funding", "launched", etc.)
3. **Event-based**: Checks `key_events` and `entity_changes` in world_state
4. **Score-variance**: Flags states with unusual plausibility scores

**Also reordered** `PortalStrategy.run()` so divergence analysis (Step 6) runs BEFORE pivot detection (Step 7).

**Result:** 84 pivot points detected (vs 0 before) spanning the full 2024-2030 timeline.

**Files:** `workflows/portal_strategy.py:_detect_pivot_points()` (lines 1575-1680), `workflows/portal_strategy.py:run()` (lines 308-319)

## Recent Fixes (February 2026)

### DIRECTORIAL and CYCLICAL Mode Full Implementation

Implemented complete strategy classes for DIRECTORIAL and CYCLICAL temporal modes, replacing the previous stub implementations.

**New Files:**
- `workflows/directorial_strategy.py` (~800 lines) - Narrative-driven temporal simulation with:
  - Five-act arc engine (SETUP → RISING → CLIMAX → FALLING → RESOLUTION)
  - Camera system with POV rotation and framing controls
  - Tension curve planning with act-aware prompting
  - Dramatic irony detection
  - Fidelity allocation: climax states get TRAINED, rising action gets DIALOG

- `workflows/cyclical_strategy.py` (~900 lines) - Cycle-based temporal simulation with:
  - LLM-driven cycle semantics interpretation (repeating, spiral, causal_loop, oscillating, composite)
  - Prophecy system with fulfillment tracking across cycles
  - Causal loop detection and enforcement
  - Escalation rules per cycle type
  - Fidelity allocation: prophecy states get TRAINED, cycle boundaries get DIALOG

**Modified Files:**
- `workflows/temporal_agent.py`: Added `run_directorial_simulation()` and `run_cyclical_simulation()` methods; replaced fidelity stub methods with real implementations
- `e2e_workflows/e2e_runner.py`: Added DIRECTORIAL and CYCLICAL mode detection and path converter methods
- `workflows/__init__.py`: Added exports for DirectorialStrategy and CyclicalStrategy
- `llm_service/model_selector.py`: Added 4 new ActionType entries for mode-specific LLM calls

### Templates (February 2026 cleanup)

Pending directorial/cyclical templates were removed during template cleanup.
The verified directorial template is `hound_shadow_directorial.json`.
Mode strategies (directorial_strategy.py, cyclical_strategy.py) remain fully implemented.

### Portal Scoring Stubs Replaced

All 5 portal scoring methods now use real LLM-based evaluation instead of hardcoded/random values:
- `_llm_score()` - Plausibility rating with Pydantic response model
- `_historical_precedent_score()` - Historical precedent check with examples
- `_causal_necessity_score()` - Causal necessity evaluation with alternatives
- `_entity_capability_score()` - Entity capability validation
- `_dynamic_context_score()` - Contextual plausibility by era

### Bug Fixes
- `metadata/narrative_exporter.py`: Added `json.loads()` deserialization for dialog data
- `metadata/run_summarizer.py`: Fixed dialog turn parsing for narrative summaries
- `llm_service/response_parser.py`: Replaced greedy regex JSON extraction with bracket-depth matching parser. The old regex (`\{[\s\S]*\}`) failed on truncated responses and text-wrapped JSON; the new `_extract_by_bracket_matching()` tracks bracket depth, string boundaries, and escape sequences character-by-character.
- `workflows/dialog_synthesis.py`: **Arousal decay** — Added exponential decay toward baseline (0.3) with 15% relaxation rate before each dialog impact. Previously arousal only accumulated, saturating at 1.0 within 3-4 dialog rounds for all entities. Also rebalanced keyword weights (low-arousal: -0.03 from -0.01), reduced interaction cap (0.08 from 0.15), symmetric delta clamp [-0.25, +0.25].
- `workflows/directorial_strategy.py`: **Prompt-schema alignment** — Added explicit format instructions to narrative planning prompt. LLM returned beats as `[{name, description}]` instead of `["string"]` and character_arcs with wrong field names. Fix specifies exact field structure in the prompt.
- `workflows/dialog_synthesis.py`: **Entity hallucination prevention** — Replaced generic `"Generate a conversation between N historical figures"` with explicit entity name anchoring. Added `IMPORTANT: ONLY use the character IDs listed below as speakers. Do NOT invent or substitute other characters.` This prevents the LLM from hallucinating Leonardo da Vinci, Cleopatra, etc. when entity context is sparse.
- `workflows/dialog_synthesis.py`: **Temporal freshness** — Added rule #8 (TEMPORAL FRESHNESS) to dialog prompt requiring new information per timepoint. Prevents recycling the same dialog beats ("3 weeks behind schedule", "Q4 targets") across every timepoint.
- `workflows/portal_strategy.py`: **key_events schema** — Added explicit `CORRECT/WRONG` format examples to portal antecedent prompt. LLM consistently returned `key_events` as `[{date, description}]` objects instead of flat strings, causing Pydantic validation failures on every backward step.
- `workflows/portal_strategy.py`: **Entity context enrichment** — Enriched entity_summary in antecedent generation prompt with roles, descriptions, knowledge items, and personality traits. Previously only listed entity IDs. Added rule #6 requiring antecedent narratives to feature the specific named entities, preventing drift to generic corporate/startup framing.

### Mars Mission Portal Template (NEW)
- `generation/templates/showcase/mars_mission_portal.json`: New portal mode template. Backward reasoning from failed Mars mission (2031) to origins (2026). 4 entities, 10 backward steps, simulation-judged with 405B judge model. First verified portal template.
- `generation/templates/catalog.json`: Added `showcase/mars_mission_portal` entry, `portal` and `space` patch categories.
- `run.sh`: Added `mars_mission_portal` to SHOWCASE_TEMPLATES array and dispatch case.

### NONLINEAR Mode Removed
Removed the NONLINEAR temporal mode from codebase (was never fully implemented). Now 5 modes: PEARL, DIRECTORIAL, BRANCHING, CYCLICAL, PORTAL.

## Commits
`type(scope): description` - types: feat, fix, refactor, test, docs, chore
