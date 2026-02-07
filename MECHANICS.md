# MECHANICS.md — Timepoint-Daedalus Technical Architecture

**A temporal simulation framework where fidelity follows attention, knowledge has provenance, and time has modes.**


## tl;dr
MECHANICS
Five pillars:

Fidelity Management: Resolution is heterogeneous and query-driven. Entities range from TENSOR_ONLY (~200 tokens) to TRAINED (~50k tokens). Queries trigger lazy elevation; disuse allows compression. Cost scales with attention, not simulation size.
Temporal Reasoning: Time has modes. PEARL (standard causality), PORTAL (backward inference from endpoints), BRANCHING (counterfactuals), CYCLICAL (prophecy), etc. Each mode changes what "consistency" means and how validation works.
Knowledge Provenance: Entities can't magically know things. Knowledge has tracked exposure events (who learned what, from whom, when). This enables causal audit, prevents anachronisms structurally, and supports counterfactual reasoning.
Entity Simulation: On-demand entity generation, scene-level collective behavior, dialog synthesis with full context, relationship evolution tracking, prospection (entities modeling their futures), and animistic agency (objects/institutions that "want" things).
Infrastructure: Intelligent model selection (M18) matches actions to optimal LLMs—math-heavy tasks use reasoning models, dialog uses conversational models, with automatic fallbacks and license compliance for commercial synthetic data.

The 19 mechanisms are implementations of these ideas. The ideas are the value; the mechanisms are derivable.

---

## The Core Problem

LLM-based simulations face a fundamental tension: full-fidelity simulation is prohibitively expensive (O(entities × timepoints × tokens)) and causes context collapse, but naive compression destroys causal structure. You can't reason about "what did Jefferson know when he wrote this letter" if you've summarized away the exposure events that gave him that knowledge.

Traditional approaches assume uniform fidelity—every entity at every moment rendered at the same resolution. This is wasteful (most detail is never queried) and inflexible (no way to dynamically allocate detail where it matters).

## The Architectural Insight

Timepoint-Daedalus treats **fidelity as a query-driven 2D surface** over (entity, timepoint) space. Resolution is heterogeneous and mutable: a minor attendee exists as a 200-token tensor embedding until someone asks about them, at which point the system elevates their resolution while preserving causal consistency with everything already established.

This enables 95% cost reduction without temporal incoherence—but only because the system maintains explicit causal structure (exposure events, temporal chains, validation constraints) that compression-based approaches discard.

---

## Conceptual Architecture

The 19 mechanisms group into five pillars:

| Pillar | Problem | Mechanisms |
|--------|---------|------------|
| **Fidelity Management** | Allocate detail where queries land | M1, M2, M5, M6 |
| **Temporal Reasoning** | Multiple notions of time and causality | M7, M8, M12, M14, M17 |
| **Knowledge Provenance** | Track who knows what, from whom, when | M3, M4, M19 |
| **Entity Simulation** | Generate and synthesize entity behavior | M9, M10, M11, M13, M15, M16 |
| **Infrastructure** | Model selection, cost optimization | M18 |

---

# Pillar 1: Fidelity Management

The insight: not all entities and moments deserve equal detail. Fidelity should concentrate around high-centrality entities at critical timepoints—like a map that renders at higher resolution only where you zoom.

## M1: Heterogeneous Fidelity Graphs

Each (entity, timepoint) pair maintains independent resolution:

```
Resolution Levels (ordered):
TENSOR_ONLY < SCENE < GRAPH < DIALOG < TRAINED

Example Graph:
Timepoint(T0, "Constitutional Convention")
├── Entity("washington", resolution=TRAINED, ~50k tokens)
├── Entity("madison", resolution=DIALOG, ~10k tokens)  
├── Entity("attendee_47", resolution=TENSOR_ONLY, ~200 tokens)
└── causal_link → Timepoint(T1)
```

Resolution is **mutable**: queries elevate resolution (lazy loading), disuse can compress it back down. The system maintains both compressed and full representations, switching based on query patterns.

**Castaway Colony example**: In the same scene, Commander Tanaka runs at TRAINED (heavily queried for command decisions), Engineer Sharma at DIALOG (repair assessments), the crashed Meridian at TENSOR (background life support tracking), and the injured Navigator Park at TENSOR_ONLY (inactive until queried about pre-crash data). Four different fidelity levels coexisting in one timepoint.

**Token economics**: 100 entities × 10 timepoints at uniform high fidelity costs ~50M tokens. With heterogeneous fidelity (power-law distribution), this drops to ~2.5M tokens—95% reduction.

### Profile Loading Extension

For simulations with known entities (real founders, historical figures), pre-defined JSON profiles can be loaded instead of LLM-generated:

```json
{
  "name": "Alex Chen",
  "archetype_id": "philosophical_technical_polymath",
  "traits": { "technical_depth": 0.85, "philosophical_thinking": 0.95 },
  "initial_knowledge": ["Expert in causal AI architectures", "Deep knowledge of temporal reasoning"]
}
```

This ensures consistency across runs and reduces LLM calls for well-characterized entities.

## M2: Progressive Training

Entity quality exists on a continuous spectrum determined by accumulated interaction, not binary cached/uncached state.

```python
EntityMetadata:
    query_count: int              # Times queried
    training_iterations: int      # LLM elaboration passes
    eigenvector_centrality: float # Graph importance (0-1)
    resolution_level: ResolutionLevel
    last_accessed: datetime
```

Each query increments metadata. When thresholds are crossed, the system triggers elevation—generating richer state representations and storing both compressed and full versions. Quality accumulates; nothing is thrown away.

**Castaway Colony example**: Dr. Okonkwo starts at SCENE resolution—a background doctor. As the crew discovers alien flora, xenobiology queries accumulate: "Is this lichen edible?" "What's the toxicity profile?" "Is the bioluminescence harmful?" After 3+ queries, he progressively elevates to DIALOG then TRAINED, becoming the most detailed entity in biosphere-related scenes. His quality tracks expertise demand, not pre-assigned importance.

## M5: Query-Driven Lazy Resolution

Resolution decisions happen at query time, not simulation time:

```python
def decide_resolution(entity, timepoint, query_history, thresholds):
    if entity.query_count > thresholds.frequent_access:
        return max(entity.resolution, DIALOG)
    if entity.eigenvector_centrality > thresholds.central_node:
        return max(entity.resolution, GRAPH)
    if timepoint.importance_score > thresholds.critical_event:
        return max(entity.resolution, SCENE)
    return TENSOR_ONLY
```

This is the key to cost reduction: we never pay for detail nobody asked about.

**Castaway Colony example**: Navigator Jin Park starts at TENSOR_ONLY — injured, inactive, consuming minimal tokens. When Branch C (Repair & Signal) needs pre-crash orbital data to locate the emergency beacon, a query about navigation logs triggers lazy elevation to DIALOG. Park reveals the hemisphere landing error, which cascades to Vasquez (recalibrate weather models) and Tanaka (explains terrain mismatch). The system paid nothing for Park's detail until the moment it mattered.

## M6: Timepoint Tensor Model (TTM) Tensor Compression

At TENSOR_ONLY resolution, entities are represented as structured tensors:

```python
TTMTensor:
    context_vector: np.ndarray   # Knowledge state (8 dims)
    biology_vector: np.ndarray   # Physical attributes (4 dims)
    behavior_vector: np.ndarray  # Personality/decision patterns (8 dims)

# Context vector layout:
# [0]=knowledge, [1]=valence, [2]=arousal, [3]=energy,
# [4]=confidence, [5]=patience, [6]=risk, [7]=social

# Compression ratios:
# Full entity: ~50k tokens
# TTM representation: ~1,600 tokens (97% compression)
```

Tensors preserve enough structure for causal validation and can be re-expanded when queries require higher fidelity.

**Castaway Colony example**: The Kepler-442b biosphere is compressed as a TTM tensor: `context_vector=[bioluminescence_intensity, electromagnetic_sensitivity, growth_rate]`, `biology_vector=[toxicity_index, nutrient_profile, symbiotic_relationships]`. This captures the alien ecosystem's state in ~1,600 tokens instead of ~50k — 97% compression. When a query asks "How does the flora respond to the crew's radio equipment?", the electromagnetic_sensitivity dimension reconstructs the relevant behavior without decompressing the entire biosphere.

### Dual Tensor Architecture & Synchronization

The system maintains two representations of cognitive/emotional state:

1. **TTMTensor** (`entity.tensor`): Trained, compressed tensor with context_vector containing emotional values (0-1 scale)
2. **CognitiveTensor** (`entity.entity_metadata["cognitive_tensor"]`): Runtime state used during dialog synthesis (-1 to 1 scale for valence, 0-100 for energy)

**The Sync Problem**: Without synchronization, entities start dialog with default CognitiveTensor values (valence=0.0, arousal=0.0) regardless of their trained TTMTensor state, and emotional changes from dialog are lost when entities are reloaded.

**The Solution**: Bidirectional sync with "pretraining" and "backprop" equivalents:

```
Entity Load → TTM→Cog Sync → Dialog Synthesis → Emotional Updates → Cog→TTM Sync → Persist
              (pretraining)                                          (backprop)
```

**Scale conversions**:
- TTM valence (0-1) ↔ Cog valence (-1 to 1): `cog = ttm * 2 - 1`
- TTM energy (0-1) ↔ Cog energy (0-100): `cog = ttm * 100`
- TTM arousal (0-1) ↔ Cog arousal (0-1): same scale

**Implementation** (in `workflows/dialog_synthesis.py`):
- `_sync_ttm_to_cognitive()`: Called before dialog, copies trained tensor values to runtime state
- `_sync_cognitive_to_ttm()`: Called after dialog, writes emotional changes back to tensor

---

# Pillar 2: Temporal Reasoning

Time isn't one thing. The framework supports multiple temporal ontologies, each with different causal semantics and validation rules.

## M17: Modal Temporal Causality

Five temporal modes, each defining what "consistency" means:

```python
class TemporalMode(Enum):
    PEARL = "pearl"           # Standard causal DAG—causes precede effects
    DIRECTORIAL = "directorial"  # Narrative time with flashbacks, ellipsis
    BRANCHING = "branching"      # Counterfactual timelines diverge from decision points
    CYCLICAL = "cyclical"        # Prophetic/mythic time—future constrains past
    PORTAL = "portal"            # Backward inference from known endpoints
```

### PORTAL Mode: Backward Temporal Reasoning

The most complex mode. Given a known endpoint ("startup reaches $1B valuation in 2030") and origin ("founders meet in 2024"), PORTAL discovers plausible paths connecting them.

**Architecture**: Generate candidate antecedent states, score them via hybrid evaluation (LLM plausibility + historical precedent + causal necessity + entity capability), validate forward coherence, detect pivot points where paths diverge.

```python
config = TemporalConfig(
    mode=TemporalMode.PORTAL,
    portal_description="John Doe elected President in 2040",
    portal_year=2040,
    origin_year=2025,
    backward_steps=15,
    path_count=3
)
```

**Exploration strategies**:
- **Reverse chronological**: 2040 → 2039 → ... → 2025 (simple, predictable)
- **Oscillating**: 2040 → 2025 → 2039 → 2026 → ... (better for complex scenarios)
- **Adaptive**: System chooses based on complexity

**Entity Inference** (January 2026 fix): Portal mode now uses LLM-based entity inference to populate `entities_present` for each generated timepoint. Instead of blindly copying entities from the consequent (which produced empty lists), the system:

1. Extracts available entities from context or the causal graph
2. Prompts the LLM to identify which entities should be present based on the event description
3. Falls back to regex-based name extraction if LLM is unavailable

```python
# In TemporalAgent._infer_entities_for_timepoint()
inferred_entities = self._infer_entities_for_timepoint(
    event_description="Heated debate at city council meeting",
    available_entities=["jane_chen", "campaign_manager", "opponent"],
    context=context
)
# Returns: ["jane_chen", "opponent"] based on event relevance
```

**Forward coherence validation**: Backward-generated paths must make sense when simulated forward. Paths below coherence threshold are pruned, backtracked, or marked with warnings.

**Simulation-based judging** (optional enhancement): Instead of static scoring formulas, run mini forward simulations from each candidate antecedent and use a judge LLM to evaluate which simulation is most realistic. Captures emergent behaviors invisible to static scoring—2-5x cost increase for significantly better path plausibility.

### Portal Enhancements (January 2026)

**Preserve All Paths**: By default (`preserve_all_paths=True` in `TemporalConfig`), portal mode returns ALL generated paths, not just the top N. This enables:
- Full analysis of exploration space
- Path clustering by coherence score
- Divergence point identification
- Complete path metadata in output

**Path Divergence Detection**: After path generation, the system analyzes where paths diverge:
- Computes pairwise path similarity at each step
- Identifies key divergence points (steps where paths split)
- Clusters paths by coherence (high_coherence, medium, low)

```python
# Output includes divergence analysis
Step 7: Computing path divergence...
  Key divergence at steps: [4, 5]
  Clusters: 1 (high_coherence)

PORTAL SIMULATION COMPLETE
Returning ALL 6 paths (preserve_all_paths=True)
Key divergence points: [4, 5]
```

**Quick Mode**: `--portal-quick` reduces `backward_steps` from default (often 24) to 5 for fast demos (~15 min vs 1+ hour). Ideal for testing and demonstrations.

```bash
./run.sh run hound_shadow_directorial  # Directorial mode with M17
```

**Pivot Point Detection** (January 2026 fix): The original `_detect_pivot_points()` function checked `children_states` which was never populated during backward simulation, causing zero pivot points to be detected. Fixed with multi-strategy detection:

1. **Divergence-based**: Uses `key_divergence_points` from path divergence analysis (steps where >30% of paths have unique narratives)
2. **Keyword-based**: Detects pivot language in state descriptions ("decision", "pivoted", "funding", "launched", "founded", "acquired", etc.)
3. **Event-based**: Checks `key_events` and `entity_changes` in world_state for significant shifts
4. **Score-variance**: Flags states with unusually high/low plausibility scores relative to neighbors

The fix also reordered operations in `PortalStrategy.run()`: divergence analysis (Step 6) now runs **before** pivot detection (Step 7), allowing pivot detection to use the divergence data.

**Before fix**: 0 pivot points detected despite obvious strategic inflection points
**After fix**: 84 pivot points detected (14 per path × 6 paths) spanning 2024-2030

```python
# Output now shows meaningful pivot detection
Step 6: Computing path divergence...
  Key divergence at steps: [23, 24]
Step 7: Detecting pivot points...
  Path 1: 14 pivot points detected
  Path 2: 14 pivot points detected
  ...
PORTAL SIMULATION COMPLETE
Total pivot points detected: 84 across 6 paths
```

**Fidelity Template Scaling**: Templates now scale proportionally with `backward_steps` instead of using hardcoded sizes. This ensures the fidelity schedule matches the actual number of steps:

| Template | Distribution |
|----------|-------------|
| `minimalist` | 70% TENSOR, 21% SCENE, 7% DIALOG |
| `balanced` | 33% TENSOR, 33% SCENE, 20% GRAPH, 13% DIALOG |
| `portal_pivots` | 2 TRAINED endpoints + scaled middle |
| `max_quality` | 66% DIALOG, 33% TRAINED |

### DIRECTORIAL Mode: Narrative-Driven Temporal Reasoning

**Architecture** (February 2026): Full strategy implementation in `workflows/directorial_strategy.py` with:

**The Core Insight**: In DIRECTORIAL mode, causality serves narrative rather than the reverse. Events don't just happen—they happen *because the story needs them*. The system treats dramatic structure as a first-class constraint, allocating computational resources where the story demands attention.

**Arc Engine** — Five-act dramatic structure with emergent pacing:

| Act | Tension Range | Temporal Density | Fidelity Allocation |
|-----|---------------|------------------|---------------------|
| SETUP | 0.2-0.4 | Sparse (establishing beats) | SCENE/TENSOR_ONLY |
| RISING | 0.4-0.7 | Increasing (complications accumulate) | DIALOG |
| CLIMAX | 0.8-1.0 | Dense (every moment matters) | TRAINED |
| FALLING | 0.5-0.3 | Decreasing (consequences unfold) | DIALOG |
| RESOLUTION | 0.1-0.2 | Sparse (denouement) | SCENE |

The arc engine doesn't just track which act you're in—it shapes generation. Rising action prompts include conflict keywords. Climax generation uses higher temperature (0.7 + tension×0.2) for dramatic unpredictability. Resolution prompts emphasize closure and consequence.

**Camera System** — The "invisible director" controls:

- **POV Rotation**: Main character for climax scenes, ensemble for setup, antagonist perspective for dramatic irony
- **Framing Vocabulary**:
  - WIDE: Establish scope, show relationships in space
  - CLOSE: Internal conflict, decision moments, emotional beats
  - OVERHEAD: God's-eye omniscience, fate bearing down
  - SUBJECTIVE: Character's limited perception, unreliable narration
  - ENSEMBLE: Multiple simultaneous perspectives, group dynamics
- **Parallel Storyline Merging**: A-plot and B-plot interleave at configurable ratios (useful for heist structures where planning intercuts with execution)

**Dramatic Irony Detection**: The system identifies moments where the audience knows something characters don't. When detected, generation emphasizes the gap—characters make choices that are tragic or comic *because* of what they don't know. This transforms information asymmetry from a bug into a feature.

**Fidelity as Dramatic Investment**: Resources concentrate where drama concentrates. A 20-timepoint tragedy might allocate 40% of its token budget to 3 climax timepoints. Background setup exists at TENSOR_ONLY because the story hasn't asked us to look closely yet.

```python
config = TemporalConfig(
    mode=TemporalMode.DIRECTORIAL,
    narrative_arc="rising_action",
    dramatic_tension=0.8,
)
```

**Affordances**:
- Classical dramatic structures (tragedy, comedy, heist, courtroom)
- Character-driven vs. plot-driven emphasis via POV weighting
- Multiple timeline interleaving for complex narrative structures
- Natural training data for story-aware language models

**Templates**: `hound_shadow_directorial`, `castaway_colony_branching` (exercises M17 via BRANCHING mode causality)

### CYCLICAL Mode: Prophecy and Time Loops

**Architecture** (February 2026): Full strategy implementation in `workflows/cyclical_strategy.py` with:

**The Core Insight**: "Cyclical time" means different things in different contexts. A time loop is structurally different from generational repetition, which is different from economic oscillation. Rather than hardcoding one interpretation, the system asks the LLM to interpret what "cyclical" means for *this specific scenario*, then enforces that interpretation consistently.

**Cycle Semantics Interpretation** — The key innovation: cycle type is *discovered*, not prescribed:

| Cycle Type | Variation Mode | What Repeats | What Changes | Example |
|------------|---------------|--------------|--------------|---------|
| `repeating` | Mutation | Events, structure | Details, awareness | Groundhog Day—same day, growing protagonist knowledge |
| `spiral` | Amplification | Structural beats | Stakes, intensity | Dynasty saga—each generation faces same conflict, higher consequences |
| `causal_loop` | Retroactive | Causal structure | Nothing (bootstrap) | Predestination—event causes its own preconditions |
| `oscillating` | Inversion | Poles | Magnitude, timing | Boom/bust—expansion then contraction, but when and how hard varies |
| `composite` | Mixed | LLM-directed | LLM-directed | Complex patterns combining multiple cycle types |

The system generates a `CycleSemantics` object that includes: cycle_type, variation_mode, escalation_rule, prophecy_mechanism, key_recurring_elements, and variation_seeds. All subsequent generation respects these semantics.

**Prophecy System** — Not just predictions, but narrative engines:

Prophecies in CYCLICAL mode aren't decorative—they're structural. A prophecy creates *narrative obligation*: either fulfill it (destiny) or subvert it (tragedy/comedy). The system tracks:

- **prophecy_accuracy** (0.0-1.0): How often prophecies come true
- **fulfillment_confidence**: LLM-rated confidence that a prophecy was fulfilled
- **prophecy_source_cycle**: Which cycle generated the prophecy (enables "ancient prophecies")

Prophecy mechanisms vary by scenario: witches' riddles (Macbeth), deja vu sensations (time loop), analyst forecasts (economics), ancestral curses (dynasty).

**Causal Loop System** — For bootstrap paradoxes and self-causing events:

Some cyclical narratives require events that cause themselves. The causal loop system:
1. Detects opportunities for loop closure ("this event could be what caused X in cycle 1")
2. Enforces closure by rewriting states to create explicit causal links
3. Validates that all opened loops eventually close

This enables legitimate bootstrap paradoxes where effect precedes cause—but only within the CYCLICAL mode's relaxed causality constraints.

**Fidelity as Cycle-Awareness**: Resources concentrate at cycle boundaries where repetition becomes visible:

| Position | Fidelity | Why |
|----------|----------|-----|
| Cycle boundaries | DIALOG | The "seam" where patterns become visible |
| Prophecy moments | TRAINED | High-stakes narrative pivots |
| Mid-cycle events | SCENE | The repeating "texture" |
| Variation points | DIALOG | Where this cycle diverges from archetype |

```python
config = TemporalConfig(
    mode=TemporalMode.CYCLICAL,
    cycle_length=4,
    prophecy_accuracy=0.7,
)
```

**Affordances**:
- Time loop narratives with protagonist evolution across resets
- Generational sagas where patterns echo but escalate
- Economic/ecological cycles with feedback and self-fulfilling prophecy
- Mythic/religious narratives with destiny and fate
- Training data for temporal reasoning about non-linear causality

**Templates**: (no verified cyclical templates currently)

## M7: Causal Temporal Chains

Timepoints form explicit causal chains:

```python
Timepoint:
    timepoint_id: str
    timestamp: datetime
    causal_parent: Optional[str]  # Explicit link to causing timepoint
    event_description: str
    entities_present: List[str]
    importance_score: float
```

**Validation constraint**: Entity at timepoint T can only reference information from timepoints T' where a causal path exists from T' to T. This prevents anachronisms structurally, not heuristically.

## M8: Vertical Timepoint Expansion

Timepoints can be expanded vertically—adding detail within a moment rather than progressing to the next moment. A "board meeting" timepoint might expand into arrival, opening remarks, key debate, decision, aftermath—all causally linked but temporally simultaneous.

## M12: Counterfactual Branching

Create alternate timelines from intervention points:

```python
def create_counterfactual_branch(parent_timeline, intervention_point, intervention):
    branch = Timeline(parent_id=parent_timeline.id, branch_point=intervention_point)
    
    # Copy timepoints before intervention
    for tp in parent_timeline.get_timepoints_before(intervention_point):
        branch.add_timepoint(tp.deep_copy())
    
    # Apply intervention at branch point
    branch_tp = parent_timeline.get_timepoint(intervention_point).deep_copy()
    apply_intervention(branch_tp, intervention)
    branch.add_timepoint(branch_tp)
    
    # Propagate causal effects forward
    propagate_causal_effects(branch, intervention_point)
    
    return branch
```

Enables "what if Madison hadn't shared his notes?" queries with proper causal propagation.

**Castaway Colony example**: At Day 7, Commander Tanaka's decision spawns three counterfactual branches. Branch A (Fortify & Wait) copies all state before Day 7 and propagates conservative resource consumption forward. Branch B (Explore & Adapt) applies exploration interventions — sending teams out, accumulating injuries and discoveries. Branch C (Repair & Signal) commits all resources to beacon repair. Each branch is internally consistent: Branch B can't use cave shelter discovered in Branch A's timeline, and Branch C can't benefit from food sources found during Branch B's exploration.

## M14: Circadian Activity Patterns

Entities have activity probabilities that vary with time of day:

```python
def get_activity_probability(hour: int, activity: str) -> float:
    probability_map = {
        "sleep": lambda h: 0.95 if 0 <= h < 6 else 0.05,
        "work": lambda h: 0.7 if 9 <= h < 17 else 0.1,
        "social": lambda h: 0.6 if 18 <= h < 23 else 0.2,
    }
    return probability_map.get(activity, lambda h: 0.0)(hour)
```

This constrains entity behavior plausibly without requiring explicit scheduling logic.

---

# Pillar 3: Knowledge Provenance

The insight: entities shouldn't magically know things. Every piece of knowledge should have a traceable origin—who learned what, from whom, when, with what confidence.

## M3: Exposure Event Tracking

Knowledge acquisition is logged as exposure events:

```python
ExposureEvent:
    entity_id: str
    event_type: EventType  # witnessed, learned, told, experienced
    information: str       # The knowledge item
    source: Optional[str]  # Another entity or external source
    timestamp: datetime
    confidence: float      # 0.0-1.0
    timepoint_id: str
```

**Validation constraint**: `entity.knowledge_state ⊆ {e.information for e in entity.exposure_events where e.timestamp ≤ query_timestamp}`

An entity cannot know something without a recorded exposure event explaining how they learned it.

**Causal audit trail**: Exposure events form a DAG. Nodes are information items; edges are causal relationships. Walking the graph validates information accessibility and enables counterfactual reasoning ("if Jefferson hadn't received that letter...").

## M4: Physics-Inspired Validation

Five validators enforce consistency using conservation-law metaphors:

**Information Conservation** (Shannon entropy): Knowledge state cannot exceed exposure history.

```python
def validate_information(entity, context):
    knowledge = set(entity.knowledge_state)
    exposure = set(e.information for e in context["exposure_history"])
    violations = knowledge - exposure
    return ValidationResult(valid=len(violations) == 0, violations=list(violations))
```

**Energy Budget** (thermodynamic): Entities have bounded cognitive/physical energy per timepoint.

**Behavioral Inertia**: Personality traits persist; sudden changes require justification.

**Biological Constraints**: Physical limitations (illness, fatigue, location) constrain behavior.

**Network Flow**: Information propagation respects relationship topology.

**Castaway Colony example**: Physics validation enforces hard constraints — O2 consumption (6 crew x 0.84 kg/hour) determines the depletion timeline. Water purification capacity (18 L/day, degrading at 0.5 L/day) limits daily intake. The engineer can't repair the beacon without the power coupling from the debris field. Nobody survives outside during radiation storms (12 mSv/hour). These aren't narrative suggestions — they're constraint violations that block invalid states, the same way conservation laws work in physics simulations.

## M19: Knowledge Extraction Agent

The problem: naive approaches to extracting knowledge from dialog produce garbage. A function that simply grabs capitalized words longer than 3 characters catches "We'll", "Thanks", "What", "Michael" (sentence-initial words, contractions, common words).

M19 solves this with an LLM-based Knowledge Extraction Agent that understands semantic meaning.

### The Old Problem (Pre-M19)

```python
# BROKEN: Naive capitalization-based extraction
def extract_knowledge_references(content: str) -> List[str]:
    words = content.split()
    knowledge_items = []
    for word in words:
        clean_word = word.strip('.,!?;:"\'-()[]{}')
        if clean_word and len(clean_word) > 3 and clean_word[0].isupper():
            knowledge_items.append(clean_word.lower())
    return list(set(knowledge_items))

# Result: ["we'll", "thanks", "what", "michael", "i've"]  # TRASH
```

### The M19 Solution

An LLM agent receives:
1. **Dialog turns** to analyze
2. **Causal graph context** (existing knowledge in the system)
3. **Entity metadata** (who is speaking, who is listening)

It returns structured `KnowledgeItem` objects:

```python
KnowledgeItem:
    content: str           # Complete semantic unit (not a single word!)
    speaker: str           # Entity who communicated this
    listeners: List[str]   # Entities who received it
    category: str          # fact, decision, opinion, plan, revelation, question, agreement
    confidence: float      # 0.0-1.0, extraction confidence
    context: Optional[str] # Why this matters in the scene
    causal_relevance: float # 0.0-1.0, importance for causal chain
```

### What Gets Extracted

**Good extractions:**
- "Michael believes the project deadline is unrealistic"
- "The board approved the $2M budget increase"
- "Sarah revealed that the prototype failed last week"
- "They agreed to postpone the launch until Q3"

**Not extracted (correctly ignored):**
- Greetings: "Hello", "Thanks", "Good morning"
- Contractions: "We'll", "I've", "That's"
- Single names without context: "Michael", "Sarah"
- Filler words: "What", "Well", "Actually"

### Knowledge Categories

| Category | Description | Example |
|----------|-------------|---------|
| **fact** | Verifiable information | "The meeting is at 3pm" |
| **decision** | Choice communicated | "We decided to pivot to B2B" |
| **opinion** | Subjective view | "I think the design needs work" |
| **plan** | Intended future action | "We'll launch in March" |
| **revelation** | New information changing understanding | "The competitor already filed the patent" |
| **question** | Only if reveals information itself | "Did you know about the acquisition?" |
| **agreement** | Consensus reached | "We all agree on the pricing" |

### RAG-Aware Prompting

The agent receives **causal context** from existing exposure events to:
1. **Avoid redundant extraction** - Don't store facts already in the system
2. **Recognize novel information** - New facts worth storing
3. **Understand relationships** - How new knowledge connects to existing

```python
def build_causal_context(entities, store):
    """Build context from existing knowledge for the extraction agent."""
    for entity in entities:
        # Get recent exposure events
        exposures = store.get_exposure_events(entity.entity_id, limit=10)
        # Include static knowledge from metadata
        static = entity.entity_metadata.get("knowledge_state", [])
        # Format as context for LLM
        ...
```

### Integration with Dialog Synthesis (M11)

M19 is called automatically during dialog synthesis:

```python
# In synthesize_dialog():
# 1. Generate dialog (M11)
dialog_data = llm.generate_dialog(prompt, max_tokens=2000)

# 2. Extract knowledge using M19 agent
extraction_result = extract_knowledge_from_dialog(
    dialog_turns=dialog_data.turns,
    entities=entities,
    timepoint=timepoint,
    llm=llm,
    store=store
)

# 3. Create exposure events for listeners (M19→M3)
exposure_events_created = create_exposure_events_from_knowledge(
    extraction_result=extraction_result,
    timepoint=timepoint,
    store=store
)
```

### Model Selection

Knowledge extraction uses M18 model selection with specific requirements:

```python
ActionType.KNOWLEDGE_EXTRACTION: {
    "required": {STRUCTURED_JSON, LOGICAL_REASONING},
    "preferred": {HIGH_QUALITY, CAUSAL_REASONING, LARGE_CONTEXT},
    "min_context_tokens": 16384,  # Need context for causal graph + dialog
}
```

### Cleanup Script

For simulations with old garbage exposure events, use:

```bash
python scripts/cleanup_old_exposure_events.py --dry-run  # Preview
python scripts/cleanup_old_exposure_events.py --backup   # Delete with backup
```

---

# Pillar 4: Entity Simulation

Generating and synthesizing entity behavior at the appropriate fidelity level.

## M9: On-Demand Entity Generation

Queries may reference entities that don't exist yet. The system detects this and generates plausible entities on demand:

```python
def detect_entity_gap(query, existing_entities):
    referenced = extract_entity_names(query)
    missing = referenced - set(existing_entities)
    return missing

def generate_entity_on_demand(name, context):
    # LLM generates plausible entity given scenario context
    # Falls back to minimal entity creation on failure
```

Pattern matching handles numbered entities ("attendee_47", "person_12") that emerge from queries about crowds or background characters.

**Castaway Colony example**: "What did the crew find in cargo bay 3?" generates inventory entities on demand — supply crates with plausible damage states and utility values. "Any other survivors from the lower deck?" generates background crew members with injury states, knowledge profiles, and skill sets consistent with a research vessel crew. These entities didn't exist until the query created them, but they're causally consistent with the established scenario.

## M10: Scene-Level Entity Sets

Scenes have their own entity types that influence individual behavior:

```python
EnvironmentEntity:  # Physical space
    location, capacity, lighting, weather, acoustics

AtmosphereEntity:   # Emergent mood
    tension_level, formality, emotional_valence, energy_level

CrowdEntity:        # Collective behavior
    size, density, mood_distribution, movement_pattern
```

Individual entity behavior is synthesized in context of scene-level state—a heated argument affects the atmosphere, which affects how other entities behave.

## M11: Dialog Synthesis

Dialog generation incorporates full context:

```python
DialogTurn:
    speaker: str
    content: str
    timestamp: datetime
    emotional_tone: str
    knowledge_references: List[str]  # What knowledge is being used
    physical_state_influence: str    # How body state affects speech
```

**Validation**: Dialog is checked for knowledge consistency (can speaker know this?), relationship consistency (would they say this to this person?), and realism (physical/emotional constraints on speech).

### Tensor Synchronization in Dialog

Before dialog synthesis, the system syncs TTMTensor → CognitiveTensor to ensure trained emotional values are used (see M6: Dual Tensor Architecture). After dialog:

1. **Emotional Impact Analysis**: Dialog content is analyzed for emotional keywords (positive/negative valence, high/low arousal)
2. **State Persistence**: Updated emotional states are written to `entity_metadata["cognitive_tensor"]`
3. **Backprop to Tensor**: Changes are synced back to TTMTensor context_vector via `_sync_cognitive_to_ttm()`

This enables emotional evolution across dialogs—entities accumulate emotional state changes throughout the simulation rather than resetting to defaults.

## M13: Multi-Entity Synthesis

Relationships evolve and can be analyzed across entities:

```python
RelationshipMetrics:
    shared_knowledge: Set[str]
    belief_alignment: float
    interaction_count: int
    trust_level: float
    power_dynamic: float

def analyze_relationship_evolution(entity_a, entity_b, timespan):
    # Track how relationship metrics change over timepoints
    
def detect_contradictions(entities, timepoint):
    # Find belief conflicts between entities
```

## M15: Entity Prospection

Entities model their own futures, and those models influence present behavior:

```python
ProspectiveState:
    entity_id: str
    forecast_horizon: timedelta
    expectations: List[Expectation]
    contingency_plans: Dict[str, List[Action]]
    anxiety_level: float
```

A founder considering a pivot doesn't just react to current state—they simulate consequences (imperfectly, with bias) and act on those simulations. This captures planning, anxiety, and anticipatory behavior.

## M16: Animistic Entity Extension

Objects, institutions, and places can have agency:

```python
class AnimismLevel:
    0: Only humans
    1: Humans + animals/buildings
    2: All objects/organisms  
    3: Abstract concepts
    4: Adaptive (AnyEntity)
    5: Spiritual (KamiEntity)
    6: AI agents
```

The conference room "wants" productive meetings; the startup's codebase "resists" certain changes. This captures how non-human entities shape behavior without requiring explicit rules—the animistic frame lets the LLM reason about object/institution agency naturally.

---

# Pillar 5: Infrastructure

System-level optimizations that make everything else work better.

## M18: Intelligent Model Selection

Different actions have different requirements. Dialog synthesis needs conversational fluency; mathematical reasoning needs strong logical capabilities; JSON generation needs structured output reliability. M18 provides capability-based model selection.

### Core Concepts

**Action Types**: 16 distinct action categories, each with different model requirements:

```python
class ActionType(Enum):
    ENTITY_POPULATION = auto()       # Generating entity profiles
    DIALOG_SYNTHESIS = auto()        # Creating realistic conversations
    TEMPORAL_REASONING = auto()      # Causal chain analysis
    COUNTERFACTUAL_PREDICTION = auto()  # "What if" scenarios
    KNOWLEDGE_VALIDATION = auto()    # Checking information consistency
    SCENE_GENERATION = auto()        # Environment/atmosphere creation
    RELATIONSHIP_ANALYSIS = auto()   # Inter-entity dynamics
    PROSPECTION = auto()             # Entity future modeling
    ANIMISTIC_BEHAVIOR = auto()      # Object/institution agency
    PORTAL_BACKWARD_REASONING = auto()  # Backward temporal inference
    PORTAL_PATH_SCORING = auto()     # Evaluating path plausibility
    CONFIG_GENERATION = auto()       # NL to simulation config
    TENSOR_COMPRESSION = auto()      # Entity state compression
    VALIDATION = auto()              # General consistency checks
    SUMMARIZATION = auto()           # Condensing information
    GENERAL = auto()                 # Catch-all
```

**Model Capabilities**: 15 capability dimensions for scoring models:

```python
class ModelCapability(Enum):
    STRUCTURED_JSON = auto()      # Reliable JSON output
    LONG_FORM_TEXT = auto()       # Extended prose generation
    DIALOG_GENERATION = auto()    # Natural conversation
    MATHEMATICAL = auto()         # Numerical reasoning
    LOGICAL_REASONING = auto()    # Formal logic
    CAUSAL_REASONING = auto()     # Cause-effect analysis
    TEMPORAL_REASONING = auto()   # Time-based inference
    LARGE_CONTEXT = auto()        # 32k+ context window
    VERY_LARGE_CONTEXT = auto()   # 128k+ context window
    FAST_INFERENCE = auto()       # Low latency
    COST_EFFICIENT = auto()       # Low cost per token
    HIGH_QUALITY = auto()         # Premium output quality
    CREATIVE = auto()             # Novel generation
    ANALYTICAL = auto()           # Data analysis
    INSTRUCTION_FOLLOWING = auto()  # Precise adherence
```

### Model Registry

Only open-source models with licenses permitting commercial synthetic data generation:

| Model | Context | Strengths | License |
|-------|---------|-----------|---------|
| **Llama 3.1 8B** | 128k | Fast, cost-efficient | Llama 3.1 |
| **Llama 3.1 70B** | 128k | Balanced quality/cost, dialog | Llama 3.1 |
| **Llama 3.1 405B** | 128k | Highest quality | Llama 3.1 |
| **Llama 4 Scout** | 512k | Multimodal, huge context | Llama 4 |
| **Qwen 2.5 7B** | 32k | JSON, code, fast | Qwen |
| **Qwen 2.5 72B** | 128k | Structured output, analytical | Qwen |
| **QwQ 32B** | 32k | Mathematical, logical reasoning | Qwen |
| **DeepSeek Chat** | 64k | Balanced, analytical | **MIT** |
| **DeepSeek R1** | 64k | Deep reasoning, math | **MIT** |
| **Mistral 7B** | 32k | Fast, cost-efficient | **Apache 2.0** |
| **Mixtral 8x7B** | 32k | Balanced MoE | **Apache 2.0** |
| **Mixtral 8x22B** | 64k | High quality MoE | **Apache 2.0** |

**Castaway Colony example**: The template routes four distinct task types to specialized models:
- **DeepSeek R1** handles O2 depletion calculations, radiation exposure modeling, and supply consumption projections — tasks requiring mathematical precision
- **Llama 70B** generates crew interpersonal dialog, command decisions, and morale propagation — tasks requiring conversational fluency
- **Qwen 72B** produces supply inventories, flora analysis reports, and damage assessments — tasks requiring reliable structured JSON output
- **Llama 405B** judges counterfactual branch outcomes — tasks requiring the highest quality evaluation

This is M18 in action: one simulation, four models, each doing what it does best.

### Selection Algorithm

```python
def select_model(action: ActionType, prefer_quality=False,
                 prefer_speed=False, prefer_cost=False) -> str:
    requirements = ACTION_REQUIREMENTS[action]

    scored_models = []
    for model_id, profile in MODEL_REGISTRY.items():
        # Check required capabilities
        if not requirements.required.issubset(profile.capabilities):
            continue

        # Score based on preferred capabilities
        score = len(requirements.preferred & profile.capabilities)

        # Apply preference weights
        if prefer_quality:
            score += profile.relative_quality * 2
        if prefer_speed:
            score += profile.relative_speed * 2
        if prefer_cost:
            score += (1 - profile.relative_cost) * 2

        scored_models.append((score, model_id))

    return max(scored_models)[1]  # Return highest-scoring model
```

### Fallback Chains

If the primary model fails, automatic retry with alternatives:

```python
def get_fallback_chain(action: ActionType, length: int = 3) -> List[str]:
    """Returns ordered list of models to try for an action."""
    primary = select_model(action)
    alternatives = [
        select_model(action, prefer_cost=True),   # Cost fallback
        select_model(action, prefer_speed=True),  # Speed fallback
    ]
    return [primary] + [m for m in alternatives if m != primary][:length-1]
```

### Integration with LLMService

```python
from llm_service import LLMService, ActionType

service = LLMService(config)

# Action-aware call with automatic model selection
response = service.call_with_action(
    action=ActionType.DIALOG_SYNTHESIS,
    system="Generate realistic dialog",
    user="Two founders discussing a pivot",
    use_fallback_chain=True  # Retry with alternatives on failure
)

# Structured output with appropriate model
entity = service.structured_call_with_action(
    action=ActionType.ENTITY_POPULATION,
    system="Generate entity profile",
    user="Create a skeptical board member",
    schema=EntityProfile
)
```

### Response Parsing

`ResponseParser` in `llm_service/response_parser.py` extracts JSON from LLM responses using a three-stage pipeline:

1. **Markdown code blocks** — Matches ` ```json ... ``` ` fences first
2. **Bracket-depth matching** — Walks the response character-by-character tracking bracket depth, string boundaries (`"..."`), and escape sequences (`\"`) to find the first balanced `{...}` or `[...]` structure
3. **Whole-text fallback** — Tries `json.loads()` on the stripped response

Bracket-depth matching handles common LLM failure modes: text before/after JSON, truncated responses, brackets inside string values, and nested structures. Failed parses are classified as `INVALID_JSON` by the error handler and retried with exponential backoff.

### License Compliance

All models in the registry permit commercial use including synthetic data generation:
- **MIT** (DeepSeek): Most permissive, no restrictions
- **Apache 2.0** (Mistral): Permissive, attribution required
- **Llama 3.1/4**: Commercial use allowed, some restrictions on scale
- **Qwen**: Commercial use allowed

Models explicitly excluded: OpenAI (usage restrictions), Anthropic (synthetic data restrictions), Google (commercial restrictions).

### Free Model Support

OpenRouter offers a rotating selection of free models (identified by `:free` suffix). The `FreeModelSelector` class in `llm.py` provides:

```python
from llm import FreeModelSelector

selector = FreeModelSelector(api_key)
selector.list_free_models()           # Show all available free models
selector.get_best_free_model()        # Quality-focused (Qwen 235B, Llama 70B)
selector.get_fastest_free_model()     # Speed-focused (Gemini Flash, small models)
```

CLI usage:
```bash
python run_all_mechanism_tests.py --free           # Best quality free model
python run_all_mechanism_tests.py --free-fast      # Fastest free model
python run_all_mechanism_tests.py --list-free-models  # Show available
```

Note: Free models have more restrictive rate limits and availability may change without notice.

---

# Unified Fidelity-Temporal Strategy

M1 (fidelity) and M17 (temporal mode) aren't independent—they co-determine resource allocation.

## The Integration Problem

PORTAL mode needs more tokens than PEARL (backward inference is complex). Entity importance depends on temporal structure. Token budgets must adapt to mode complexity.

## FidelityTemporalStrategy

The TemporalAgent co-determines both dimensions:

```python
FidelityTemporalStrategy:
    entity_resolution_map: Dict[str, ResolutionLevel]
    timepoint_resolution_map: Dict[str, ResolutionLevel]
    token_budget: Optional[int]
    temporal_mode_complexity: float  # PORTAL=1.5, PEARL=1.0
    planning_mode: FidelityPlanningMode  # PROGRAMMATIC | ADAPTIVE | HYBRID
    budget_mode: TokenBudgetMode  # HARD_CONSTRAINT | SOFT_GUIDANCE | MAX_QUALITY
```

## Fidelity Templates

Pre-configured strategies for common scenarios:

| Template | Default Resolution | Token Budget | Planning Mode |
|----------|-------------------|--------------|---------------|
| minimal | TENSOR_ONLY | 50k | PROGRAMMATIC |
| balanced | SCENE | 250k | HYBRID |
| high_quality | GRAPH | 500k | ADAPTIVE |
| maximum | DIALOG | unlimited | ADAPTIVE |

## Temporal Mode Complexity Multipliers

```python
complexity_map = {
    PEARL: 1.0,        # Baseline
    DIRECTORIAL: 1.2,  # Narrative structure overhead
    BRANCHING: 1.4,    # Multiple timelines
    CYCLICAL: 1.3,     # Prophecy validation
    PORTAL: 1.5,       # Backward inference (most expensive)
}
```

---

# Performance Characteristics

## Token Cost Reduction

| Approach | Tokens | Cost |
|----------|--------|------|
| Naive (uniform high fidelity) | 50M | ~$500/query |
| Heterogeneous fidelity | 2.5M | ~$25/query |
| With TTM compression | 250k | ~$2.50/query |

## Compression Ratios

- Context tensor: 1000 dims → 8 dims (99.2%)
- Biology tensor: 50 dims → 4 dims (92%)
- Behavior tensor: 100 dims → 8 dims (92%)
- **Overall at TENSOR_ONLY: 50k → 200 tokens (99.6%)**

## Validation Complexity

O(n) for n validators using set operations and vector norms.

---

# Integration Flow

```
Query
  ↓
Query Parser
  ↓
Entity Resolution (M1, M9) — identify/generate entities
  ↓
Resolution Decision (M2, M5) — determine fidelity level
  ↓
State Loading (M6) — decompress if needed
  ↓
Validation (M3, M4) — check causal/knowledge consistency
  ↓
Synthesis (M10, M11, M13, M15) — generate response
  ↓
Response + Metadata
```

---

# Part 2: Infrastructure Platform (Vision)

The simulation engine (18 mechanisms above) is implemented. The following describes the **target infrastructure**—what we're building toward. See [MILESTONES.md](MILESTONES.md) for timeline.

## What Timepoint Does vs. What the Model Does

| Concern | Who Handles It |
|---------|----------------|
| Text generation (dialog, descriptions) | LLM (12 open-source models via OpenRouter) |
| Model selection for action type | Timepoint (M18) |
| Temporal mode semantics | Timepoint (M17) |
| Causal chain validation | Timepoint (M7, M4) |
| Knowledge provenance | Timepoint (M3, M4) |
| Fidelity management | Timepoint (M1, M2, M5, M6) |
| Entity state management | Timepoint (M9, M10, M13) |
| Counterfactual branching | Timepoint (M12) |
| Forward/backward path exploration | Timepoint (M17 PORTAL) |

**The model generates; Timepoint reasons about time, causality, consistency, and selects the right model for each task.**

## Target: Orchestration Layer (Not Yet Implemented)

```python
# FUTURE API - NOT IMPLEMENTED
BatchRunner:
    workers: int                    # Parallel execution threads
    queue: PriorityQueue[SimJob]    # Job scheduling
    rate_limiter: TokenBucket       # API cost management

CostManager:
    budget_total: float
    budget_per_job: float
    token_tracking: Dict[str, int]
```

**Target functionality:**
- Batch execution with parallel workers
- Cost tracking and budget enforcement
- Progress reporting

## Target: Persistence Layer (Partial)

```python
# FUTURE API - PARTIAL
SimulationRun:
    run_id: str
    config_hash: str              # Exact reproduction
    model_version: str
    paths: List[TemporalPath]
    pivot_points: List[PivotPoint]
    cost_tokens: int
    cost_dollars: float

store.query(mode="portal", cost_under=50.0)
store.aggregate(group_by="parameter", measure="outcome")
store.compare(run_a, run_b)
```

**Current reality:** Basic SQLite storage in `storage.py` and `metadata/runs.db`. Advanced queries not implemented.

## Target: Human Interface Layer (Partial)

**Planned features:**
- Timeline visualization with branching paths
- Entity relationship graphs (animated over time)
- Parameter sensitivity heatmaps
- Path clustering and representative extraction
- Narrative generation (executive summaries)

**Current reality:** API backend exists (FastAPI). Frontend archived to `archive/quarto-frontend` branch. Visualization features pending.

## Target: Integration Layer (Not Implemented)

**Planned integrations:**
- Prediction market connectors (Polymarket, Metaculus)
- Decision system webhooks
- Research export pipelines
- REST API with OpenAPI spec

## Target: Deployment Architecture (Not Implemented)

```
Development:     Docker Compose (single machine)
Production:      Kubernetes with HPA
High Performance: Bare metal with Ansible
Global:          Multi-region with coordination
```

**Current reality:** Single Python process, no containerization.

---

# References

- Pearl, J. (2009). *Causality: Models, Reasoning, and Inference*
- Shannon, C. E. (1948). A Mathematical Theory of Communication
- Schölkopf, B., et al. (2021). Toward Causal Representation Learning
- Vaswani, A., et al. (2017). Attention Is All You Need

---

# Appendix: Convergence Evaluation

**When ground truth is unavailable, self-consistency across independent runs provides a proxy for reliability.**

## The Problem

Traditional simulation evaluation requires ground truth—known outcomes to compare against. But for novel scenarios (future predictions, counterfactuals, "what if" explorations), no ground truth exists. How do we assess whether simulation outputs are reliable?

## The Insight

If the same scenario, run multiple times with different random seeds or model variations, produces consistent causal structures, the underlying mechanisms are likely robust. Divergent causal graphs indicate unstable reasoning that shouldn't be trusted.

This follows from a key principle: **self-consistency is a necessary (not sufficient) condition for validity**. A simulation that contradicts itself across runs definitely has problems; one that converges might still be wrong, but at least it's reliably wrong.

## Causal Graph Structure

Convergence operates on **CausalGraphs** extracted from simulation runs:

```python
CausalGraph:
    edges: Set[CausalEdge]

CausalEdge:
    source: str      # Timepoint ID or Entity ID
    target: str      # Connected node
    edge_type: str   # "temporal" | "knowledge" | "causal"
```

**Edge types:**
- **Temporal edges**: `Timepoint.causal_parent` relationships (T2 caused by T1)
- **Knowledge edges**: `ExposureEvent` flow (Entity A learned X from Entity B)
- **Causal edges**: Explicit causal claims in narrative

## Jaccard Similarity

Graph comparison uses Jaccard similarity—the standard set-overlap metric:

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

For causal graphs:
- `A ∩ B` = edges present in both graphs (consensus)
- `A ∪ B` = edges present in either graph (total unique edges)

**Interpretation:**
- J = 1.0: Perfect agreement (identical causal structures)
- J = 0.5: Half the edges are shared
- J = 0.0: No overlap (completely different causal reasoning)

## Convergence Score and Grading

For multiple runs (≥2), convergence score is the **mean pairwise Jaccard similarity**:

```python
def compute_convergence(graphs: List[CausalGraph]) -> float:
    similarities = []
    for i in range(len(graphs)):
        for j in range(i + 1, len(graphs)):
            sim = jaccard_similarity(graphs[i], graphs[j])
            similarities.append(sim)
    return sum(similarities) / len(similarities)
```

**Robustness Grades:**

| Grade | Score Range | Interpretation |
|-------|-------------|----------------|
| **A** | ≥ 90% | Highly robust—causal structure nearly identical across runs |
| **B** | ≥ 80% | Robust—minor variations but core causal reasoning stable |
| **C** | ≥ 70% | Moderate—some disagreement on secondary causal links |
| **D** | ≥ 50% | Unstable—significant divergence, use with caution |
| **F** | < 50% | Unreliable—causal reasoning inconsistent, do not trust |

## Divergence Points

When graphs disagree, the system identifies **divergence points**—specific causal edges where runs differ:

```python
def find_divergence_points(graphs: List[CausalGraph]) -> List[DivergencePoint]:
    all_edges = union(g.edges for g in graphs)
    divergence = []
    for edge in all_edges:
        present_count = sum(1 for g in graphs if edge in g.edges)
        if present_count < len(graphs):  # Not unanimous
            divergence.append(DivergencePoint(
                edge=edge,
                agreement_ratio=present_count / len(graphs),
                status="contested"
            ))
    return divergence
```

Divergence points reveal where causal reasoning is unstable—these are the edges to investigate or treat as uncertain.

## Usage

### CLI

```bash
# Run convergence evaluation on existing runs
python run_all_mechanism_tests.py --convergence --convergence-runs 3

# Run convergence E2E test (run template N times, then compute convergence)
python run_all_mechanism_tests.py --convergence-e2e --template convergence_test_simple --convergence-runs 3

# Use convergence-optimized templates for fast testing
python run_all_mechanism_tests.py --convergence-e2e --template convergence_test_standard --convergence-runs 5

# Verbose output with side-by-side comparison
python run_all_mechanism_tests.py --convergence-e2e --template board_meeting --convergence-runs 3 --convergence-verbose
```

### Convergence-Optimized Templates

Three templates designed specifically for fast convergence testing:

| Template | Entities | Timepoints | Est. Time/Run |
|----------|----------|------------|---------------|
| `convergence_test_simple` | 3 | 2 | ~30s |
| `convergence_test_standard` | 5 | 3 | ~60s |
| `convergence_test_comprehensive` | 7 | 5 | ~90s |

### API Endpoints

```bash
# Get aggregate convergence statistics
curl http://localhost:8000/api/convergence-stats

# List convergence sets with filtering
curl "http://localhost:8000/api/convergence-sets?min_score=0.7&limit=20"

# Get detailed divergence points for a set
curl http://localhost:8000/api/convergence-set/{set_id}
```

### API Access

Convergence data is available via the REST API (see endpoints above). Frontend archived to `archive/quarto-frontend` branch.

## Configuration

```python
class ConvergenceConfig(BaseModel):
    enabled: bool = False
    run_count: int = 3           # Runs per convergence set (2-10)
    min_acceptable_score: float = 0.5  # Minimum score to consider "acceptable"
    store_divergence_points: bool = True
    e2e_mode: bool = False       # Run template N times then compute convergence
    verbose: bool = False        # Show side-by-side comparison output
```

### E2E Mode vs Standard Mode

| Mode | Command | Description |
|------|---------|-------------|
| **Standard** | `--convergence` | Analyze existing runs in database |
| **E2E** | `--convergence-e2e` | Run template N times, then analyze |

E2E mode is useful for validating that a specific template produces consistent causal structures.

## Limitations

1. **Self-consistency ≠ correctness**: Converged simulations may still be wrong if the model has systematic biases
2. **Computational cost**: Each convergence evaluation requires N simulation runs
3. **Edge detection sensitivity**: Different granularities of causal logging affect scores
4. **Stochastic elements**: Some divergence is expected from intentional randomness (different entity decisions)

## When to Use Convergence

**Good use cases:**
- Validating PORTAL mode backward reasoning
- Comparing template robustness
- Identifying unstable causal mechanisms
- Quality assurance before production use

**Not appropriate for:**
- Single-run scenarios (need ≥2 runs)
- Intentionally divergent simulations (branching counterfactuals)
- Real-time evaluation (too slow)

---

**Castaway Colony — Full Mechanism Showcase (February 2026)**: The `castaway_colony_branching` template exercises all 19 mechanisms in a single scenario. It is the first template to verify M1 (heterogeneous fidelity), M2 (progressive training), M4 (physics validation), M5 (lazy resolution), M6 (tensor compression), M9 (on-demand entities), and M18 (model selection) — seven mechanisms that previously had zero verified templates. 10 entities, 3 counterfactual branches, 90+ quantitative state variables, O(100,000) interaction paths.

**Implementation Status**: All 19 mechanisms implemented and verified. M19 (Knowledge Extraction Agent) added December 2025 to replace naive capitalization-based extraction with LLM-based semantic understanding. Convergence evaluation implemented with E2E testing mode and 3 convergence-optimized templates. Parallel execution (`--parallel N`) and free model support (`--free`, `--free-fast`) added December 2025. **Portal enhancements** added January 2026: `preserve_all_paths` (returns ALL paths), path divergence detection, `--portal-quick` mode (5 backward steps), fidelity template scaling, and **pivot point detection fix** (multi-strategy detection replacing broken `children_states` check).

**January 2026 Data Integrity Fixes**:
- **Portal Entity Inference**: M17 PORTAL mode now uses LLM-based entity inference (`temporal_agent.py:_infer_entities_for_timepoint()`) instead of blind copying from consequent timepoints. This fixes the bug where all portal-generated timepoints had empty `entities_present`.
- **Portal Entity Fallback**: Added fallback logic in `portal_strategy.py` when `_filter_entities_by_relevance()` returns empty (LLM descriptions don't mention entity names). The fix inherits all parent entities instead of leaving `entities_present` empty. Applied in `_generate_antecedents()` and `_generate_placeholder_antecedents()`.
- **Entity Persistence**: Entities now sync to `metadata/runs.db` alongside timepoints (`e2e_runner.py:_persist_entity_for_convergence()`), enabling proper cross-run convergence analysis.
- **Data Quality Validation**: Added `e2e_runner.py:_run_data_quality_check()` that validates entity references and detects empty `entities_present` before run completion.
- **Timepoint Validation Warning**: `schemas.py:Timepoint.__init__()` now emits `UserWarning` when `entities_present` is empty to surface data quality issues early.
- **TTM↔Cog Tensor Sync**: Fixed dual-storage issue where TTMTensor and CognitiveTensor had independent emotional values that never synchronized. Added bidirectional sync in `dialog_synthesis.py`: `_sync_ttm_to_cognitive()` (pretraining equivalent) and `_sync_cognitive_to_ttm()` (backprop equivalent). Entities now use trained tensor values during dialog and persist emotional changes back to tensors.
- **Voice Differentiation**: Added `_derive_speaking_style()` function mapping personality traits to speaking patterns (verbosity, formality, tone, vocabulary, speech_pattern) to fix generic dialog where all entities sounded identical.
- **Entity Hallucination Prevention**: Added `ENTITY_BLACKLIST` and `_validate_entity_id()` in `portal_strategy.py` to filter out phantom entity IDs like "arr", "series_c" generated by LLMs.
- **Pivot Point Detection Fix**: Rewrote `_detect_pivot_points()` in `portal_strategy.py` with 4-strategy detection (divergence-based, keyword-based, event-based, score-variance) replacing broken `children_states` check that always returned empty. Reordered `PortalStrategy.run()` so divergence analysis runs before pivot detection. Result: 84 pivot points detected vs 0 previously.

**February 2026 Dialog & Portal Quality Fixes**:
- **Arousal Decay System**: `dialog_synthesis.py` now applies exponential decay toward baseline (0.3) before each dialog impact: `new_arousal = baseline + (current - baseline) * (1 - decay_rate)`. Previously arousal only accumulated (asymmetric keywords +0.03/-0.01, always-positive interaction factor), saturating at 1.0 within 3-4 rounds. Fix rebalanced weights and added symmetric clamping [-0.25, +0.25].
- **Dialog Entity Anchoring**: The dialog prompt previously said "Generate a conversation between N historical figures" regardless of entity type, causing LLM hallucination of Leonardo da Vinci, Cleopatra, Shakespeare when entity context was sparse. Fix: explicit entity name list in prompt header + "ONLY use the character IDs listed below" instruction.
- **Dialog Temporal Freshness**: Added prompt rule #8 requiring new information per timepoint, preventing the same dialog beats ("3 weeks behind schedule", "Q4 targets") from recycling across every conversation.
- **Portal key_events Schema**: Added `CORRECT/WRONG` format examples to antecedent generation prompt. LLM consistently returned `key_events` as `[{date, description}]` objects instead of `["string"]`, causing Pydantic validation failures on every backward step. Same pattern as directorial prompt fix.
- **Portal Entity Context Enrichment**: Enriched entity_summary with roles, descriptions, knowledge items, and personality traits (previously just entity IDs). Added instruction #6 requiring named entities in antecedent narratives, preventing drift to generic corporate framing.
- **Mars Mission Portal Template**: First verified portal template (`showcase/mars_mission_portal`). Backward reasoning from Ares III Mars mission failure (2031) to origins (2026), 4 entities, 10 backward steps, simulation-judged with 405B. Exercises M3, M7, M8, M11, M13, M17.

**Platform Status**: Infrastructure vision; see [MILESTONES.md](MILESTONES.md) for roadmap.
**See also**: [README.md](README.md) for quick start, [QUICKSTART.md](QUICKSTART.md) for natural language usage.