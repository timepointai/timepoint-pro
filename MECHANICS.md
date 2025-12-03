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

The 18 mechanisms are implementations of these ideas. The ideas are the value; the mechanisms are derivable.

---

## The Core Problem

LLM-based simulations face a fundamental tension: full-fidelity simulation is prohibitively expensive (O(entities × timepoints × tokens)) and causes context collapse, but naive compression destroys causal structure. You can't reason about "what did Jefferson know when he wrote this letter" if you've summarized away the exposure events that gave him that knowledge.

Traditional approaches assume uniform fidelity—every entity at every moment rendered at the same resolution. This is wasteful (most detail is never queried) and inflexible (no way to dynamically allocate detail where it matters).

## The Architectural Insight

Timepoint-Daedalus treats **fidelity as a query-driven 2D surface** over (entity, timepoint) space. Resolution is heterogeneous and mutable: a minor attendee exists as a 200-token tensor embedding until someone asks about them, at which point the system elevates their resolution while preserving causal consistency with everything already established.

This enables 95% cost reduction without temporal incoherence—but only because the system maintains explicit causal structure (exposure events, temporal chains, validation constraints) that compression-based approaches discard.

---

## Conceptual Architecture

The 18 mechanisms group into five pillars:

| Pillar | Problem | Mechanisms |
|--------|---------|------------|
| **Fidelity Management** | Allocate detail where queries land | M1, M2, M5, M6 |
| **Temporal Reasoning** | Multiple notions of time and causality | M7, M8, M12, M14, M17 |
| **Knowledge Provenance** | Track who knows what, from whom, when | M3, M4 |
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

**Token economics**: 100 entities × 10 timepoints at uniform high fidelity costs ~50M tokens. With heterogeneous fidelity (power-law distribution), this drops to ~2.5M tokens—95% reduction.

### Profile Loading Extension

For simulations with known entities (real founders, historical figures), pre-defined JSON profiles can be loaded instead of LLM-generated:

```json
{
  "name": "Sean McDonald",
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

## M6: Timepoint Tensor Model (TTM) Tensor Compression

At TENSOR_ONLY resolution, entities are represented as structured tensors:

```python
TTMTensor:
    context_vector: np.ndarray   # Knowledge state
    biology_vector: np.ndarray   # Physical attributes
    behavior_vector: np.ndarray  # Personality/decision patterns

# Compression ratios:
# Full entity: ~50k tokens
# TTM representation: ~1,600 tokens (97% compression)
```

Tensors preserve enough structure for causal validation and can be re-expanded when queries require higher fidelity.

---

# Pillar 2: Temporal Reasoning

Time isn't one thing. The framework supports multiple temporal ontologies, each with different causal semantics and validation rules.

## M17: Modal Temporal Causality

Six temporal modes, each defining what "consistency" means:

```python
class TemporalMode(Enum):
    PEARL = "pearl"           # Standard causal DAG—causes precede effects
    DIRECTORIAL = "directorial"  # Narrative time with flashbacks, ellipsis
    NONLINEAR = "nonlinear"      # Presentation order ≠ causal order
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

**Forward coherence validation**: Backward-generated paths must make sense when simulated forward. Paths below coherence threshold are pruned, backtracked, or marked with warnings.

**Simulation-based judging** (optional enhancement): Instead of static scoring formulas, run mini forward simulations from each candidate antecedent and use a judge LLM to evaluate which simulation is most realistic. Captures emergent behaviors invisible to static scoring—2-5x cost increase for significantly better path plausibility.

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
    NONLINEAR: 1.3,    # Complex presentation
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

**Current reality:** Basic dashboard exists (Quarto + FastAPI). Visualization features pending.

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

### Dashboard

The Convergence page (`convergence.html`) provides:
- Overview metrics (sets, average score, grade distribution)
- Score distribution visualization
- Template coverage analysis
- Detailed divergence point inspection

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

**Implementation Status**: All 18 mechanisms implemented and verified. Convergence evaluation implemented with E2E testing mode and 3 convergence-optimized templates. Parallel execution (`--parallel N`) and free model support (`--free`, `--free-fast`) added December 2025.
**Platform Status**: Infrastructure vision; see [MILESTONES.md](MILESTONES.md) for roadmap.
**See also**: [README.md](README.md) for quick start, [QUICKSTART.md](QUICKSTART.md) for natural language usage.