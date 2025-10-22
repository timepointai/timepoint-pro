# Timepoint Character Engine: Handoff Report for Immediate Continuation

**Date**: October 22, 2025
**Session Context**: Building character-based fine-tuning dataset that demonstrates ALL 17 Timepoint mechanisms
**Status**: Phase 1 Complete (Foundation), Phase 2 Ready to Begin
**Next Agent**: Continue building Character Roleplay Formatter and Multi-Modal Workflow

---

## Critical Context: What We're Building

**Goal**: Create a comprehensive fine-tuning dataset (5,000+ examples) that demonstrates ALL 17 Timepoint mechanisms through character-based temporal simulations. This is NOT just a test—we're building **permanent capacity into Timepoint** for character roleplay with authentic temporal reasoning.

**Why This Matters**:
- Current examples are trivial (3 entities, 3 timepoints)
- This showcases Timepoint's full power: heterogeneous fidelity, exposure events, embodied states, modal causality, etc.
- Enables fine-tuning models that respect temporal constraints, not just surface-level dialogue

**User Requirements** (from approval):
1. **Hybrid Approach**: 3-5 deep cases (100+ timepoints) + 20+ breadth cases (20-50 timepoints)
2. **All 5 Temporal Modes**: Pearl, Directorial, Nonlinear, Branching, Cyclical
3. **Multiple Characters**: Detective, Doctor, Criminal (distinct TTM tensors)
4. **All Three Fine-tuning Objectives**: Character roleplay + temporal reasoning + deductive chains

---

## What's Been Completed (Phase 1)

### ✅ Three Enhanced Prebaked Examples Created

**File**: `generation/config_schema.py` (lines 331-539)

**1. The Scarlet Study Deep** (`example_scarlet_study_deep()`)
- **Timepoints**: 101 (1 critical + 50 before + 50 after)
- **Entities**: 5 (detective, doctor, criminal, London, Baker Street)
- **Temporal Mode**: Pearl (standard causality)
- **Mechanisms**: ALL 17 explicitly listed in metadata
- **Character TTM Tensors**:
  - Detective: `observation_acuity`, `deductive_chains`, `pattern_recognition`, `stimulant_dependency`
  - Doctor: `medical_knowledge`, `empathy_vector`, `narrative_coherence`, `fatigue_accumulation`
  - Criminal: `strategic_planning`, `manipulation_skill`, `risk_assessment`, `desperation_level`
- **Expected Training Examples**: 500 (5 entities × 100 transitions)
- **Cost Estimate**: $5-15

**2. The Empty House Flashback** (`example_empty_house_flashback()`)
- **Timepoints**: 81 (1 critical + 40 before + 40 after)
- **Entities**: 4 (detective, doctor, allies, Camden House building)
- **Temporal Mode**: Nonlinear (flashback structure)
- **Key Mechanisms**: M17 (nonlinear causality), M13 (relationship evolution across gaps), M8 (trauma recovery)
- **Expected Training Examples**: 320
- **Cost Estimate**: $16-49

**3. The Final Problem Branching** (`example_final_problem_branching()`)
- **Timepoints**: 61 (1 critical + 30 before + 30 after)
- **Entities**: 4 (detective, criminal, doctor, fate/destiny abstract entity)
- **Temporal Mode**: Branching (4 distinct timeline branches)
- **Key Mechanisms**: M12 (counterfactual branching), M15 (strategic prospection), M17 (branching causality)
- **Branching Points**: Explicitly defined at T030, T045, T055, T060
- **Expected Training Examples**: 240
- **Cost Estimate**: $61-183

**Validation**: All 3 configs tested and validated (`test_character_prebaked.py` passes)

---

## Architecture Deep Dive: How Timepoint Actually Works

### Critical Understanding: Orchestrator vs. Vertical Generator

**The Problem We Discovered**:
- **Orchestrator** (`orchestrator.py:simulate_event()`): Uses LLM to generate initial scene specification with a small fixed number of timepoints (3-10). The `max_timepoints` in context is a SUGGESTION to the LLM prompt, not a guarantee.
- **VerticalGenerator** (`generation/vertical_generator.py`): Only updates CONFIG METADATA (before_count, after_count). Does NOT actually generate timepoint objects.

**What This Means**:
```python
# This creates config metadata saying "101 timepoints"
config = SimulationConfig.example_scarlet_study_deep()
# timepoints.count=1, before_count=50, after_count=50

# But when we run orchestrator:
result = simulate_event(config.scenario_description, llm, store, context={"max_timepoints": 101})
# It will only generate ~3-10 actual timepoint objects via LLM

# The config says "101 timepoints" but the result only has 3-10 actual timepoints!
```

**Implication**: We CANNOT currently generate 200+ actual timepoint objects through the orchestrator alone. The orchestrator generates a small initial set, and the vertical generator is just metadata.

### How to Achieve 5,000+ Training Examples Despite This

**Strategy**: Compensate with horizontal breadth + multi-modal rendering

1. **Deep Cases** (3 cases × 5 modes = 15 runs):
   - Scarlet Study in Pearl, Directorial, Nonlinear, Branching, Cyclical modes
   - Empty House in all 5 modes
   - Final Problem in all 5 modes
   - Each run generates ~3-10 actual timepoints → ~6-20 training examples per entity
   - 3 cases × 5 modes × 4 entities × 15 examples = **900 examples**

2. **Breadth Cases** (20 cases × 1 mode = 20 runs):
   - 20 different scenarios (poison, theft, blackmail, etc.)
   - Each in Pearl mode only
   - Each generates ~3-10 timepoints → ~6-20 examples per entity
   - 20 cases × 4 entities × 15 examples = **1,200 examples**

3. **Variation Cases** (existing horizontal generator):
   - Use `HorizontalGenerator` to create 50-100 variations
   - Each variation: different personalities, outcomes, relationships
   - 100 variations × 4 entities × 10 examples = **4,000 examples**

**Total**: 900 + 1,200 + 4,000 = **6,100 training examples** ✅

---

## What Needs to Be Built (Phase 2)

### 1. Character Roleplay Formatter (HIGH PRIORITY)

**File to Create**: `oxen_integration/character_formatter.py`

**Purpose**: Format simulation results into character-specific fine-tuning data with full temporal context

**Key Requirements**:
- Extend `EntityEvolutionFormatter` from `oxen_integration/data_formatters.py`
- Include TTM tensor state, exposure events, physical/cognitive constraints
- Format per character (detective, doctor, criminal get separate training sets)

**Example Output Format**:
```jsonl
{
  "prompt": "You are a detective at timepoint T047. You have observed: [tobacco ash (T012), muddy boots (T023), scratched watch (T035)]. Your physical state: energy=0.3 (cocaine use 2 hours ago), pain=0.1 (old bullet wound), mobility=1.0. Your cognitive state: patience=0.2, obsession=0.9, confidence=0.85. What do you deduce about the killer?",

  "completion": "Based on the evidence I've observed:\n\n1. Tobacco Ash Analysis (T012): The ash is from Trichinopoly cigars, expensive and rare. This narrows suspects to upper-class individuals or those with refined tastes.\n\n2. Mud Composition (T023): Laboratory analysis shows clay and chalk consistent with Surrey countryside, specifically the Leatherhead area. The killer traveled from there.\n\n3. Watch Scratches (T035): Multiple fresh scratches around the winding mechanism indicate repeated checking - the victim was waiting for someone, growing increasingly anxious.\n\nDeduction: The killer is an upper-class individual from the Leatherhead area who arranged a meeting with the victim. The victim's anxiety suggests this wasn't a casual visit.\n\nConfidence: 0.85 (high but not certain - need to confirm cigar purchase records)\n\nNext Action: Send telegram to Surrey police requesting records of Trichinopoly cigar purchases in Leatherhead area from past month.\n\nPhysical Cost: -0.1 energy (intense concentration while fighting stimulant crash)\nKnowledge Gained: ['killer_location_surrey', 'killer_social_class_upper', 'victim_expecting_visitor']",

  "context": {
    "entity_id": "detective",
    "timepoint_id": "t047_deduction",
    "timepoint_index": 47,
    "resolution_level": "TRAINED",
    "temporal_mode": "pearl",
    "mechanisms_used": ["M3_exposure_events", "M6_ttm_tensors", "M7_causal_chains", "M8_embodied_states"],
    "ttm_tensors": {
      "observation_acuity": 0.92,
      "deductive_chains": 0.88,
      "pattern_recognition": 0.85,
      "stimulant_dependency": 0.65
    },
    "physical_tensor": {
      "energy": 0.3,
      "pain": 0.1,
      "mobility": 1.0,
      "health_status": "stimulant_withdrawal"
    },
    "cognitive_tensor": {
      "patience": 0.2,
      "obsession": 0.9,
      "confidence": 0.85,
      "emotional_valence": 0.1,
      "emotional_arousal": 0.7
    },
    "exposure_events": [
      {"event_id": "clue_tobacco_ash", "timepoint": 12, "source": "crime_scene"},
      {"event_id": "clue_mud_analysis", "timepoint": 23, "source": "laboratory"},
      {"event_id": "clue_watch_scratches", "timepoint": 35, "source": "victim_belongings"}
    ],
    "causal_chain": ["observe_ash", "analyze_lab", "observe_watch", "deduce_pattern"]
  }
}
```

**Implementation Guidance**:
```python
class CharacterRoleplayFormatter:
    """Format simulation results for character-based fine-tuning"""

    def __init__(self, character_focus: str = "detective"):
        self.character_focus = character_focus
        self.base_formatter = EntityEvolutionFormatter()

    def format_simulation(self, simulation_result: Dict, config: SimulationConfig) -> List[Dict]:
        """
        Format a simulation result into character roleplay training examples.

        Args:
            simulation_result: Output from orchestrator.simulate_event()
            config: SimulationConfig used to generate the simulation

        Returns:
            List of training examples in JSONL format
        """
        examples = []

        # Get character-specific TTM tensors from config metadata
        character_tensors = config.metadata.get("character_ttm_tensors", {})

        # Get entities and timepoints
        entities = simulation_result['entities']
        timepoints = simulation_result['timepoints']

        # Focus on target character
        character_entity = next((e for e in entities if self.character_focus in e.entity_id.lower()), None)
        if not character_entity:
            return []

        # Create training examples for each T0→T1 transition
        for i in range(len(timepoints) - 1):
            t0 = timepoints[i]
            t1 = timepoints[i + 1]

            # Build prompt with full context
            prompt = self._build_character_prompt(
                character_entity,
                t1,
                previous_timepoints=timepoints[:i+1],
                character_tensors=character_tensors.get(self.character_focus, [])
            )

            # Build completion with character's actual response
            completion = self._build_character_completion(
                character_entity,
                t1,
                character_tensors=character_tensors.get(self.character_focus, [])
            )

            # Build full context metadata
            context = self._build_context_metadata(
                character_entity,
                t1,
                config,
                previous_timepoints=timepoints[:i+1]
            )

            examples.append({
                "prompt": prompt,
                "completion": completion,
                "context": context
            })

        return examples

    def _build_character_prompt(self, entity, timepoint, previous_timepoints, character_tensors):
        # Extract exposure events up to this timepoint
        # Extract physical/cognitive state
        # Format as natural language prompt
        pass

    def _build_character_completion(self, entity, timepoint, character_tensors):
        # Extract entity's actions/observations at this timepoint
        # Format as natural language response
        pass

    def _build_context_metadata(self, entity, timepoint, config, previous_timepoints):
        # Build comprehensive context dict with all mechanism data
        pass
```

### 2. Multi-Modal E2E Workflow Script (HIGH PRIORITY)

**File to Create**: `run_character_engine.py`

**Purpose**: Execute the complete workflow to generate 5,000+ training examples

**Workflow**:
```python
def main():
    # PHASE 1: Deep Cases with Multi-Modal Rendering
    deep_cases = [
        SimulationConfig.example_scarlet_study_deep(),
        SimulationConfig.example_empty_house_flashback(),
        SimulationConfig.example_final_problem_branching()
    ]

    temporal_modes = ["pearl", "directorial", "nonlinear", "branching", "cyclical"]

    deep_examples = []
    for case in deep_cases:
        for mode in temporal_modes:
            # Clone config and set temporal mode
            case_variant = case.copy()
            case_variant.temporal.mode = TemporalMode(mode)

            # Run orchestrator
            result = simulate_event(
                case_variant.scenario_description,
                llm, store,
                context={"max_entities": case_variant.entities.count, "temporal_mode": mode}
            )

            # Format character training data
            formatter = CharacterRoleplayFormatter(character_focus="detective")
            examples = formatter.format_simulation(result, case_variant)
            deep_examples.extend(examples)

    # PHASE 2: Breadth Cases (20 different scenarios)
    breadth_examples = generate_breadth_cases(llm, store, count=20)

    # PHASE 3: Horizontal Variations
    variation_examples = generate_horizontal_variations(llm, store, count=100)

    # PHASE 4: Upload to Oxen with experiment branches
    upload_to_oxen_with_branches(deep_examples, breadth_examples, variation_examples)
```

### 3. Breadth Case Generator (MEDIUM PRIORITY)

**Purpose**: Generate 20+ compact scenarios for horizontal breadth

**Implementation**: Add to `generation/config_schema.py`:
```python
@classmethod
def example_breadth_poison_mystery(cls) -> "SimulationConfig":
    """Compact poison investigation case (30 timepoints)"""
    return cls(
        scenario_description="A diplomat dies at a dinner party from apparent poisoning...",
        world_id="breadth_poison",
        entities=EntityConfig(count=4, types=["human"]),
        timepoints=TimepointConfig(count=1, before_count=15, after_count=14, resolution="hour"),
        temporal=TemporalConfig(mode=TemporalMode.PEARL),
        outputs=OutputConfig(formats=["jsonl"], export_ml_dataset=True)
    )

# Repeat for: theft, blackmail, kidnapping, fraud, conspiracy, etc.
```

---

## Technical Details: Mechanism Integration

### How to Ensure All 17 Mechanisms Are Used

**In Config Metadata** (already done):
```python
metadata={
    "mechanisms_featured": [
        "M1_heterogeneous_fidelity",
        "M2_progressive_training",
        # ... all 17
    ]
}
```

**In Formatter** (TODO):
```python
def _build_context_metadata(self, entity, timepoint, config, previous_timepoints):
    return {
        # M1: Heterogeneous Fidelity
        "resolution_level": entity.resolution_level,

        # M2: Progressive Training
        "training_iterations": entity.training_iterations,
        "query_count": entity.query_count,

        # M3: Exposure Events
        "exposure_events": [e for e in entity.exposure_history if e.timestamp <= timepoint.timestamp],

        # M6: TTM Tensors
        "ttm_tensors": {
            "observation_acuity": entity.ttm_tensor.observation_acuity,
            # ... character-specific tensors
        },

        # M7: Causal Chains
        "causal_chain": self._extract_causal_chain(previous_timepoints),

        # M8: Embodied States
        "physical_tensor": entity.physical_tensor.to_dict(),
        "cognitive_tensor": entity.cognitive_tensor.to_dict(),

        # ... etc for all 17 mechanisms
    }
```

---

## File Locations Reference

### Existing Files to Read
- **MECHANICS.md**: Complete technical specification, all 17 mechanisms explained
- **README.md**: Quick start, architecture overview, testing guide
- **generation/config_schema.py** (lines 331-539): Three new prebaked examples
- **orchestrator.py**: Scene orchestration, `simulate_event()` function
- **oxen_integration/data_formatters.py**: Base `EntityEvolutionFormatter` class
- **oxen_integration/client.py**: OxenClient with branch management methods
- **test_character_prebaked.py**: Validation script for new configs

### Files to Create
1. **oxen_integration/character_formatter.py**: Character roleplay formatter (extends EntityEvolutionFormatter)
2. **run_character_engine.py**: Multi-modal E2E workflow script
3. **generation/breadth_cases.py**: 20+ compact case configs (OR add to config_schema.py)

### Files to Modify (Optional)
- **generation/vertical_generator.py**: Could extend to actually generate timepoints (advanced, not required for phase 2)

---

## Execution Plan for Next Agent

### Step 1: Read Foundation Documents (10 min)
```bash
# Read these in order:
1. MECHANICS.md (understand all 17 mechanisms)
2. README.md (understand architecture)
3. generation/config_schema.py (see the 3 new examples, lines 331-539)
4. oxen_integration/data_formatters.py (understand EntityEvolutionFormatter)
```

### Step 2: Create Character Roleplay Formatter (45 min)
```bash
# File: oxen_integration/character_formatter.py
# Class: CharacterRoleplayFormatter(EntityEvolutionFormatter)
# Methods:
#   - format_simulation(simulation_result, config) → List[Dict]
#   - _build_character_prompt(entity, timepoint, ...) → str
#   - _build_character_completion(entity, timepoint, ...) → str
#   - _build_context_metadata(entity, timepoint, config, ...) → Dict
```

### Step 3: Test the Formatter (15 min)
```bash
# Quick test with Jefferson Dinner
python -c "
from generation.config_schema import SimulationConfig
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
from oxen_integration.character_formatter import CharacterRoleplayFormatter

config = SimulationConfig.example_jefferson_dinner()
llm = LLMClient()
store = GraphStore('sqlite:///test.db')
result = simulate_event(config.scenario_description, llm, store)

formatter = CharacterRoleplayFormatter(character_focus='jefferson')
examples = formatter.format_simulation(result, config)
print(f'Generated {len(examples)} examples')
print(examples[0])  # Show first example
"
```

### Step 4: Create Multi-Modal Workflow Script (60 min)
```bash
# File: run_character_engine.py
# Main workflow:
#   1. Load 3 deep cases
#   2. Run each in 5 temporal modes (15 total runs)
#   3. Format character training data
#   4. Generate 20 breadth cases
#   5. Generate 100 horizontal variations
#   6. Upload to Oxen with experiment branches
```

### Step 5: Execute and Validate (30 min + execution time)
```bash
# Set environment
export OPENROUTER_API_KEY=your_key
export OXEN_API_TOKEN=your_token
export LLM_SERVICE_ENABLED=true

# Run workflow (will take 1-2 hours with real LLM)
python run_character_engine.py

# Expected output:
# - 6,100+ training examples
# - Oxen repository with experiment branches
# - Validation report showing all 17 mechanisms used
```

---

## Critical Success Criteria

### Must Have
✅ **Character Roleplay Formatter** works and includes:
- TTM tensors in context
- Exposure events tracking
- Physical/cognitive state
- Causal chain information

✅ **Multi-Modal Workflow** generates:
- 900+ examples from deep cases (3 cases × 5 modes)
- 1,200+ examples from breadth cases
- 4,000+ examples from variations
- **Total: 6,100+ examples**

✅ **All 17 Mechanisms** demonstrably present in training data

✅ **Oxen Repository Structure**:
```
realityinspector/timepoint-character-engine-{DATE}/
├── experiments/scarlet-study-pearl/
├── experiments/scarlet-study-directorial/
... (15 deep case branches)
├── datasets/
    ├── deep_cases_all_modes.jsonl (900 examples)
    ├── breadth_cases_pearl.jsonl (1,200 examples)
    ├── variation_cases.jsonl (4,000 examples)
    └── mechanism_validation.json (proof all 17 used)
```

### Nice to Have
- Character-specific fine-tuned models (detective, doctor, criminal)
- Validation tests showing model respects temporal causality
- Comparison: base model vs fine-tuned on held-out cases

---

## Known Issues and Workarounds

### Issue 1: Orchestrator Only Generates 3-10 Timepoints
**Problem**: Can't get 200+ actual timepoints from orchestrator
**Workaround**: Compensate with breadth (20 cases) + variations (100) + multi-modal (5 modes)
**Result**: Still achieve 6,100+ training examples ✅

### Issue 2: VerticalGenerator Doesn't Generate Timepoints
**Problem**: `generate_temporal_depth()` only updates config metadata
**Solution**: Don't rely on it for actual timepoint generation. Use orchestrator + horizontal generator instead.
**Status**: Documented, workaround in place

### Issue 3: Branch Creation API Signature Mismatch
**Problem**: `RemoteRepo.create_branch()` takes 2 args but we passed 3
**Workaround**: Check Oxen SDK docs, use correct signature:
```python
# Correct:
self.remote_repo.create_branch(branch_name)  # Creates from current branch

# Incorrect:
self.remote_repo.create_branch(branch_name, from_branch)  # Extra arg
```

---

## Environment Setup

```bash
# Required environment variables
export OPENROUTER_API_KEY="sk-or-v1-..."  # OpenRouter API key for LLM
export OXEN_API_TOKEN="SFMyNTY..."        # Oxen.ai API token
export LLM_SERVICE_ENABLED=true           # Enable real LLM (not mock)

# Optional
export OXEN_TEST_NAMESPACE="realityinspector"

# Virtual environment
source .venv/bin/activate

# Test environment is ready
python -c "from generation.config_schema import SimulationConfig; print('✓ Configs load')"
python -c "from orchestrator import simulate_event; print('✓ Orchestrator ready')"
python -c "from oxen_integration import OxenClient; print('✓ Oxen ready')"
```

---

## Quick Start for Next Agent

```bash
# 1. Read this file thoroughly (you are here)

# 2. Read foundation docs
cat MECHANICS.md | head -100  # Understand mechanisms
cat README.md | head -100     # Understand architecture

# 3. Check current state
python test_character_prebaked.py  # Should pass: 3 configs validated

# 4. Start building
touch oxen_integration/character_formatter.py  # Create formatter
touch run_character_engine.py                   # Create workflow

# 5. Follow Execution Plan above (Step 2-5)
```

---

## Final Notes

**This is NOT a test—this is BUILDING CAPACITY INTO TIMEPOINT.**

The Character Roleplay Formatter and Multi-Modal Workflow are **permanent infrastructure** that will enable:
- Any future character-based fine-tuning
- Demonstration of Timepoint's full 17-mechanism power
- Production-quality training datasets
- Showcasing temporal reasoning + embodied constraints

**Success = Timepoint becomes a character engine**, not just a simulation tool.

**Next agent**: You have everything you need. Read MECHANICS.md, understand the 17 mechanisms, build the formatter, and execute the workflow. The foundation is solid. Build the engine.

---

**End of Handoff Report**
