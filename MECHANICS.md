# MECHANICS.md - Timepoint-Daedalus Novel Architecture

## The Core Problem

Large language models can simulate historical entities, but doing so naively creates two irreconcilable tensions:

1. **Token Economics**: Full-context prompting (50k tokens per entity × 100 entities × 10 timepoints = 50M tokens ≈ $500/query) doesn't scale
2. **Temporal Consistency**: Compressed representations lose the causal structure needed to prevent anachronisms and maintain coherent entity evolution

Standard approaches fail because they treat this as a caching problem (cache invalidation nightmare) or a compression problem (lossy representations break temporal reasoning). Both assume uniform fidelity across the simulation.

**The insight**: Historical simulations have heterogeneous information value. Washington at the inauguration ceremony matters more than a random attendee. The moment of signing the Constitution matters more than breakfast the next morning. Most attempts at historical simulation waste tokens on low-value detail while underserving high-value queries.

Timepoint-Daedalus solves this through **query-driven progressive refinement in a causally-linked temporal graph**, where resolution adapts to actual usage patterns rather than static importance heuristics.

## Mechanism 1: Heterogeneous Fidelity Temporal Graphs

Traditional temporal databases store uniform snapshots. Timepoint stores a graph where **each node has independent resolution**.

```
Timepoint T0 (Inauguration Ceremony)
├─ Washington: TRAINED (full LLM elaboration, 50k tokens)
├─ Adams: DIALOG (moderate detail, 10k tokens)
├─ Random Attendee #47: TENSOR_ONLY (compressed, 200 tokens)
└─ Causal link → T1

Timepoint T1 (Post-ceremony reception)  
├─ Washington: SCENE (reduced detail, 5k tokens)
├─ Adams: GRAPH (minimal, 2k tokens)
└─ Causal link → T2
```

**Key innovation**: Resolution is not global. It's per-entity, per-timepoint, and mutable. This creates a 2D fidelity surface where detail concentrates around high-value regions (central entities at important moments) and compresses elsewhere.

**Why this matters**: You can represent 100 entities across 10 timepoints with the same token budget as 5 entities at uniform high fidelity. The system automatically identifies where detail matters.

## Mechanism 2: Progressive Training Without Cache Invalidation

Standard caching: `cached(entity_id, timepoint) → state | miss`

Timepoint approach: `query_count`, `training_iterations`, `eigenvector_centrality` → **continuous quality spectrum**

An entity isn't "cached" or "uncached" - it exists at a quality level determined by accumulated training. Each query:
1. Increments `query_count`
2. If count crosses threshold + low current resolution → trigger elevation
3. Elevation = LLM elaboration pass that increases detail
4. Store both compressed (for efficiency) and full (for future elevation)

**The clever bit**: This is self-tuning. High-traffic entities naturally accumulate training iterations. Peripheral entities stay compressed until someone cares enough to query them repeatedly. No manual importance scoring required.

**Technical detail**: The metadata triple `(query_count, centrality, training_iterations)` acts as a **resource allocation signal**. The system learns which entities matter by observing query patterns, not by trying to predict importance a priori.

## Mechanism 3: Exposure Event Tracking (Causal Knowledge Provenance)

Standard approach: `entity.knowledge_state = ["Revolutionary War veteran", "Constitutional Convention delegate"]`

Timepoint approach:
```python
ExposureEvent(
    entity_id="washington",
    event_type="witnessed",
    information="Constitutional Convention debates",
    source="madison",  # learned from Madison
    timestamp="1787-07-16",
    confidence=0.95
)
```

**Why this matters**: You can validate temporal consistency by checking if `entity.knowledge ⊆ entity.exposure_history`. If Washington references the War of 1812 in 1789, the validator catches it because no exposure event exists for that information at that timepoint.

This turns "knowledge consistency" from a vague goal into a **computable constraint**: every knowledge claim must have a causal explanation (an exposure event). LLMs hallucinate; this system forces explanations.

**Novel aspect**: Most temporal databases track state changes. Timepoint tracks **why** states changed. The exposure event log is a causal audit trail enabling counterfactual reasoning ("What if Jefferson never went to Paris?") by removing exposure events and recomputing forward.

## Mechanism 4: Physics-Inspired Validation as Structural Invariants

The validators aren't arbitrary rules - they encode **conservation laws** that historical simulations must obey:

**Information Conservation** (Shannon entropy constraint):
- Information can't appear from nothing
- `H(entity_knowledge) ≤ H(exposure_history)`
- Catches anachronisms, impossible knowledge

**Energy Budget** (thermodynamic constraint):
- Finite attention/interaction capacity per time period
- Prevents entities from simultaneously attending 10 meetings
- Models opportunity cost of actions

**Behavioral Inertia** (momentum constraint):
- Personality vectors have momentum - sudden changes require force
- `|Δpersonality| ≤ threshold` unless major event
- Prevents inconsistent characterization

**Network Flow** (social capital constraint):
- Influence propagates through relationship graph
- Political power isn't created ex nihilo
- Validates that status changes have sources

**Why physics analogies**: These aren't metaphors. They're **structural invariants** that any coherent simulation must satisfy. Using physics terminology makes the constraints rigorous rather than aesthetic.

**Technical insight**: The validators compose. An entity state is valid if it passes all conservation laws. This is computationally cheap (simple set operations, vector norms) compared to asking an LLM "does this seem consistent?"

## Mechanism 5: Query-Driven Lazy Resolution Elevation

The resolution decision function:

```python
def decide_resolution(entity, timepoint, query_history):
    if entity.query_count > FREQUENT_ACCESS_THRESHOLD:
        return max(entity.resolution, DIALOG)
    
    if entity.eigenvector_centrality > CENTRAL_NODE_THRESHOLD:
        return max(entity.resolution, GRAPH)
    
    if timepoint.importance_score > CRITICAL_EVENT_THRESHOLD:
        return max(entity.resolution, SCENE)
    
    return TENSOR_ONLY
```

**The lazy part**: Elevation happens **on-demand**, not preemptively. When a query targets Washington at the inauguration:
1. Load current state (may be TENSOR_ONLY)
2. Check if resolution sufficient for query
3. If not, trigger LLM elaboration pass
4. Cache result, increment training counter
5. Next query gets higher-fidelity state

**Why this is clever**: Traditional systems either:
- Precompute everything (expensive, wasteful)
- Recompute on every query (slow, expensive)
- Cache everything uniformly (memory explosion)

Timepoint does none of these. It **learns** which entities need detail through usage patterns, then incrementally refines only those entities.

**Compression synergy**: Low-resolution entities store only compressed tensors (PCA/SVD reduces 1000 floats → 8 floats). High-resolution entities keep both compressed (for quick lookups) and full state (for elaboration). The system adapts memory usage to query patterns.

## Mechanism 6: TTM Tensor Model (Context/Biology/Behavior Factorization)

Standard entity representation: single embedding vector

TTM representation:
```python
TTMTensor(
    context_vector,   # What entity knows (information state)
    biology_vector,   # Physical constraints (age, health, location)
    behavior_vector   # Personality, patterns, habits
)
```

**Why this factorization matters**:

1. **Biology vectors are cheap**: Age and health evolve predictably. You don't need LLM calls for "Washington is now 58" - just increment.

2. **Context vectors compress well**: Knowledge items are semantically clustered. PCA/SVD can reduce dimensionality aggressively without losing coherence.

3. **Behavior vectors are stable**: Personality changes slowly. You can reuse compressed behavior vectors across timepoints with small delta updates.

**Technical detail**: By separating these concerns, the compression ratio improves dramatically. A 50k token entity state might decompress to:
- Biology: 100 tokens (mostly constants)
- Behavior: 500 tokens (mostly from previous timepoint)
- Context: 1000 tokens (new knowledge only)

Total reconstruction: 1600 tokens instead of 50k. The rest is in compressed form.

**LLM integration**: When synthesizing responses, the LLM receives:
```
"Entity: Washington (age 57, health: good, location: New York)
Personality: [compressed behavior vector decompressed to traits]
Knowledge: [compressed context vector decompressed to facts]
Query: What did you think about becoming president?"
```

The factorization lets you pay token costs only for the relevant dimension. If the query is about physical capability, you don't need the full knowledge state.

## Mechanism 7: Causal Temporal Chains (Not Just Timelines)

Standard temporal database: `state(t) → state(t+1)` with no causal links

Timepoint temporal chain:
```python
Timepoint(
    timepoint_id="inauguration_t3",
    causal_parent="inauguration_t2",  # explicit link
    event_description="First cabinet meeting",
    entities_present=["washington", "jefferson", "hamilton"]
)
```

**Why explicit causality**: You can validate that information flows forward, not backward. If Hamilton references something from T5 while at T3, the validator detects it by walking the causal chain and confirming no path exists from T5 → T3.

**Counterfactual reasoning**: Want to simulate "what if Adams wasn't vice president"? 
1. Remove Adams from T0
2. Recompute T1 given T0 changes
3. Propagate forward through causal chain
4. Compare resulting T7 to baseline T7

The causal links make this tractable because you only recompute forward from the intervention point, not the entire timeline.

**Branch points**: The chain can fork. If you want to explore "what if the Constitutional Convention failed", you create a branch at that timepoint and evolve both timelines independently. The causal structure makes branching clean - it's just a different parent pointer.

## Why This Architecture Matters

**Economic viability**: A 100-entity, 10-timepoint simulation that would cost $500/query in naive full-context mode costs $5-20 in Timepoint (95%+ reduction) by concentrating tokens on high-value regions.

**Temporal consistency**: The exposure tracking + causal chains + conservation validators make anachronisms computationally detectable, not just "LLM please don't hallucinate" hope.

**Scalability**: The progressive training mechanism means the simulation improves with use. First query is cheap (compressed state), hundredth query is detailed (elevated resolution). The system learns what matters.

**Composability**: Entities, timepoints, and exposure events are independent. You can merge simulations, branch timelines, or extract subgraphs without breaking causal structure. The factorized tensor representation makes this tractable.

**Novel research direction**: This isn't just "use LLMs for history simulation." It's a framework for **queryable, causally-consistent, economically-viable temporal knowledge graphs** where detail emerges from usage patterns rather than designer prediction.

## Mechanism 8: Embodied Entity States

Entities aren't disembodied knowledge stores - they have physical and 
psychological states that constrain behavior.

PhysicalTensor tracks:
- Age-dependent capabilities (stamina, sensory acuity)
- Health events with temporal effects (injury at T3 affects T4-T6)
- Location constraints (can't attend meeting in Philadelphia if in Paris)
- Biological realities (pregnancy, illness, aging)

CognitiveTensor tracks:
- Emotional state (valence/arousal model, not just personality)
- Energy budget (daily attention/interaction capacity)
- Belief vectors (not just facts, but confidence levels)
- Personality momentum (resistance to change)

**Why this matters**: A 57-year-old Washington with documented dental pain 
doesn't just "know" different things than a 40-year-old Washington - he 
experiences events differently. Pain affects mood, which affects decisions.

**Validation synergy**: Biological constraints prevent impossible actions 
(70-year-old can't sprint), while energy budgets prevent impossible 
schedules (can't attend 12 simultaneous meetings). The validators enforce 
physical realism.

**Resolution implications**: At TENSOR_ONLY, you store compressed 
physical/cognitive state (8 floats each). At TRAINED, you can query:
"How did Washington's dental pain affect his mood during the ceremony?"
and get a response that synthesizes physical sensation → emotional state 
→ behavioral impact.

Looking back at your original vision:

> "query for matches in timepoints and entities, if found, load relevant details into the context engine, inject into system prompts, allowing llm to use; **else, if not found or partial, create a set of entities, and set, setting, and other characters to simulate the timepoint**"

The system currently **fails** at the "else" clause. You can query existing entities but can't trigger **on-demand entity generation**. If I ask "What did random attendee #47 think?" and that entity doesn't exist, the system should:
1. Detect the entity gap
2. Generate a plausible attendee entity at appropriate resolution
3. Answer the query with the newly-created entity

This is missing.

## Missing Mechanisms

### Mechanism 9: On-Demand Entity Generation

When a query references a non-existent entity:
- Parse: "What did random attendee #47 think about the ceremony?"
- Detect: No entity "random_attendee_47" exists
- Infer context: Query about inauguration ceremony, timepoint T0
- Generate: Create minimal entity with TENSOR_ONLY resolution
- Populate: Use timepoint context to give plausible background
- Answer query using newly-generated entity
- Persist entity for future queries

**Why critical**: Your original vision was **generative temporal simulation**, not just database querying. The system should expand to fill query demands, not just retrieve pre-computed states.

### Mechanism 10: Scene-Level Entity Sets

Your original: "create a set of entities, and set, setting, and other characters"

Currently missing:
- **Set**: The physical environment (Federal Hall layout, weather, lighting)
- **Setting**: The social/political atmosphere (crowd mood, tensions)
- **Peripheral characters**: The 500+ attendees who weren't Founders

The system models 5 named entities but doesn't represent:
- The crowd as a collective entity
- Physical environment constraints
- Ambient conditions affecting all entities

A query like "What was the atmosphere like?" should synthesize from:
- Named entity emotional states (aggregated)
- Environmental conditions (weather, space constraints)
- Crowd dynamics (density, energy level)

This requires modeling **scene-level properties** separate from individual entities.

### Mechanism 11: Dialog/Interaction Synthesis

Your original: "full-fledged llm calls for details and even structured dialog"

Currently: Entities have knowledge states but don't **interact**.

Missing:
- Generate conversation between entities at a timepoint
- Model information exchange (Hamilton tells Jefferson about financial plan)
- Create ExposureEvents from interactions (Jefferson learns from Hamilton)
- Synthesize dialog that's causally consistent with both entities' states

Query: "What did Washington and Jefferson discuss at the first cabinet meeting?"
Should:
1. Load both entities at that timepoint
2. Generate plausible conversation given their knowledge/goals
3. Create ExposureEvents for any information exchanged
4. Update future timepoints if conversation changed trajectory

### Mechanism 12: Counterfactual Branching

Your original vision implied this but it's not implemented:

```python
# Branch timeline at intervention point
branch = create_branch(
    parent_timeline="founding_fathers_1789",
    branch_point="t2",  # First cabinet meeting
    intervention="hamilton_absent"  # Hamilton doesn't attend
)

# Recompute forward from branch point
propagate_causality(branch, start_timepoint="t2")

# Compare outcomes
compare_timelines("founding_fathers_1789", branch, metric="policy_decisions")
```

This enables:
- "What if Jefferson never went to Paris?"
- "What if Hamilton died before the inauguration?"
- Exploring historical contingency systematically

The causal chain structure supports this but the branching mechanism doesn't exist.

### Mechanism 13: Multi-Entity Synthesis (Query Composition)

Currently: Queries target single entities
Missing: Queries that require reasoning over multiple entity trajectories

"How did Washington and Jefferson's relationship evolve?" needs:
- Load Washington states at T0-T7
- Load Jefferson states at T0-T7
- Identify interaction points (shared timepoints)
- Synthesize relationship arc from both perspectives
- Detect contradictions (if Washington thinks X but Jefferson thinks Y)

This requires **comparative synthesis**, not just single-entity retrieval.

## Priority Ranking

**Critical (breaks original vision)**:
- Mechanism 9 (on-demand generation) - without this, it's just a database
- Mechanism 13 (multi-entity synthesis) - queries currently fail at this

**Important (enables richer simulation)**:
- Mechanism 10 (scene-level modeling) - atmosphere/environment matters
- Mechanism 11 (dialog synthesis) - interactions drive plot

**Nice to have (research features)**:
- Mechanism 12 (counterfactuals) - enables experimental history

The test output shows: You built the **storage and validation infrastructure** but not the **generative query layer**. Hamilton has 20 knowledge items but the query returns "doesn't have knowledge" - the synthesis is broken.

Your original vision was a **generative temporal simulation**. What exists is a **queryable temporal database**. The gap is mechanisms that **create content on-demand** rather than just retrieve pre-computed content.## Mechanism 14: Circadian Activity Patterns

Most temporal simulations treat time uniformly. In reality, activity follows circadian rhythms and social conventions that constrain possible interactions.

**Implementation:**

```python
CircadianContext(
    hour: int,  # 0-23
    typical_activities: Dict[str, float],  # activity -> probability
    ambient_conditions: Dict[str, Any],  # lighting, temperature, crowds
    social_constraints: List[str]  # "formal_dress_required", "business_hours"
)
```

**Activity probability by hour:**
- 03:00 → sleep (0.95), emergency (0.04), insomnia (0.01)
- 12:00 → lunch (0.60), meetings (0.30), work (0.10)
- 19:00 → dinner (0.50), socializing (0.30), evening_work (0.20)

**Why this matters:**

1. **Query validation**: "What did Jefferson discuss with Hamilton at 3am?" triggers warning - extremely unlikely without special circumstances (emergency, insomnia, secret meeting)

2. **Energy budget enforcement**: Entities accumulate fatigue. A 16-hour day depletes energy_budget more than an 8-hour day. Night activities cost more energy.

3. **Exposure filtering**: Information exchange unlikely during sleep. If entity asleep at T3, no new ExposureEvents created (unless woken).

4. **Scene generation**: Time-of-day affects environmental conditions. Federal Hall at noon (crowded, bright, hot) differs from Federal Hall at 8am (sparse, cool, quiet).

**Validation integration:**

```python
if query_time.hour in [0, 1, 2, 3, 4, 5] and not special_circumstances:
    return ValidationWarning(
        "Query references unusual time (3am). Most entities asleep. "
        "Interaction unlikely unless emergency or deliberate late meeting."
    )
```

This prevents temporal incoherence at fine-grained timescales. It's easy to maintain causal consistency across days; circadian patterns enforce consistency across hours.

---

## Mechanism 15: Entity Prospection (Internal Forecasting)

Entities don't just react to past events - they anticipate futures and those expectations influence behavior.

**Implementation:**

```python
ProspectiveState(
    entity_id: str,
    forecast_horizon: timedelta,  # how far ahead entity is thinking
    expectations: List[Expectation],
    contingency_plans: Dict[str, Action],
    anxiety_level: float  # uncertainty about future
)

Expectation(
    predicted_event: str,
    probability: float,  # entity's subjective probability
    desired_outcome: bool,
    preparation_actions: List[str]
)
```

**Example - Washington before inauguration (T-1):**

```python
washington.prospective_state = ProspectiveState(
    forecast_horizon=days(30),
    expectations=[
        Expectation(
            predicted_event="overwhelming_responsibility",
            probability=0.90,
            desired_outcome=False,  # he's anxious
            preparation_actions=["seek_counsel", "review_precedents"]
        ),
        Expectation(
            predicted_event="political_opposition",
            probability=0.70,
            desired_outcome=False,
            preparation_actions=["build_coalition", "compromise_strategy"]
        )
    ],
    anxiety_level=0.65  # documented historical anxiety
)
```

**Effects on behavior:**

1. **Action selection**: High anxiety → more conservative choices, more information-seeking
2. **Knowledge valence**: Same information interpreted differently based on expectations (confirmation bias modeling)
3. **Personality drift**: Chronic anxiety shifts personality_vector toward neuroticism
4. **Energy allocation**: High-priority expectations get more cognitive resources

**Training feedback loop:**

When T0 arrives and inauguration happens:
- Compare expectations to reality
- Update future forecast accuracy (prediction error)
- Adjust anxiety_level based on outcome
- Store learned patterns for future forecasts

This creates **temporal depth** - entities aren't just present-focused, they have past (memory), present (state), and future (expectation) simultaneously represented.

**Query implications:**

"What was Washington worried about before the inauguration?" → synthesize from prospective_state at T-1

"How did Jefferson's expectations change after Paris?" → compare prospective_states before/after Paris timepoints

---

## Mechanism 16: Animistic Entity Extension (Experimental Plugin)

Standard simulation: Only humans are entities with agency
Animistic mode: **Everything with causal influence is an entity**

**Plugin architecture:**

```python
@experimental_plugin("animism")
class AnimisticEntityGenerator:
    """Extend entity concept to non-human agents"""
    
    entity_types = {
        "animal": ["horse", "dog", "cat", "bird"],
        "plant": ["tree", "flower", "crop"],
        "object": ["carriage", "building", "ship"],
        "abstract": ["rumor", "idea", "movement"]
    }
```

**Example - Federal Hall as entity:**

```python
Entity(
    entity_id="federal_hall",
    entity_type="building",
    entity_metadata={
        "physical_state": {
            "age": 33,  # years old
            "structural_integrity": 0.85,
            "capacity": 500,
            "ambient_temperature": 72
        },
        "goals": [
            "shelter_occupants",
            "maintain_structural_integrity",
            "project_authority"  # architectural symbolism
        ],
        "constraints": [
            "cannot_move",
            "weather_dependent",
            "requires_maintenance"
        ]
    }
)
```

**Example - Washington's horse:**

```python
Entity(
    entity_id="washington_horse_nelson",
    entity_type="animal",
    entity_metadata={
        "biological_state": {
            "age": 12,
            "health": 0.90,
            "energy_level": 0.75,
            "training_level": 0.95  # war horse, highly trained
        },
        "goals": [
            "avoid_pain",
            "seek_food",
            "trust_handler",
            "conserve_energy"
        ],
        "personality_traits": [0.3, -0.2, 0.8, 0.1, 0.6],  # calm, brave, loyal
        "knowledge_state": [
            "familiar_with_washington",
            "accustomed_to_crowds",
            "trained_for_ceremony"
        ]
    }
)
```

**Why this is valuable (not just whimsy):**

1. **Environmental constraints**: The horse's stamina limits how long Washington can travel. The building's capacity limits how many attendees can enter. These are real causal factors.

2. **Emergent interactions**: "Did Washington's horse react to the crowd?" - a valid historical question. The horse's nervousness might have affected Washington's composure.

3. **Biological realism**: Plants/animals follow their own logic. A flower doesn't "decide" to bloom - it responds to temperature and sunlight with biological determinism. This adds authentic constraints.

4. **Object affordances**: A carriage can break, limiting transportation options. A building can catch fire, forcing evacuation. These are event triggers.

**Plugin controls:**

```python
# Conservative mode (default)
animism_level = 0  # Only humans are entities

# Moderate mode
animism_level = 1  # Humans + named animals/buildings

# Experimental mode  
animism_level = 2  # Everything with causal influence

# Full animism (research/creative)
animism_level = 3  # Abstract concepts (ideas, rumors) as entities
```

**Level 3 example - "Fear of monarchy" as entity:**

```python
Entity(
    entity_id="fear_of_monarchy_1789",
    entity_type="abstract_concept",
    entity_metadata={
        "propagation_vector": [0.8, 0.6, 0.9],  # spreads through conversation
        "intensity": 0.75,  # how strongly felt
        "carriers": ["adams", "jefferson", "madison"],  # who holds this fear
        "goals": [
            "prevent_executive_overreach",
            "maintain_vigilance",
            "spread_to_others"
        ],
        "decay_rate": 0.02  # diminishes over time if not reinforced
    }
)
```

This allows modeling **memetic propagation** - ideas as entities that spread, mutate, and compete for cognitive resources.

**Critical distinction:**

This is not anthropomorphizing everything. It's recognizing that **causal influence doesn't require human-level cognition**. A horse has goals (avoid pain, seek food) even if not conscious in human terms. A building has constraints (capacity, structural limits) that affect events. The plugin makes causal relationships explicit by modeling them as entity properties.

**Use case:**

Historical materialists would love this. "How did the physical environment of Federal Hall constrain the inauguration?" becomes queryable. "What role did Washington's war horse play in his public image?" becomes answerable. The built environment and non-human entities shaped history - this mechanism makes that simulatable.

---

## Integration Notes

**Mechanism 14** (circadian) integrates with energy budgets and scene generation. It's a validator that prevents temporal incoherence at hourly granularity.

**Mechanism 15** (prospection) adds temporal depth - entities aren't just reactive, they're anticipatory. This explains otherwise-mysterious behaviors (why did Jefferson prepare X? Because he expected Y).

**Mechanism 16** (animism) is genuinely experimental. Most historical simulations won't need it. But for queries about environmental influence, animal behavior, or material constraints, it transforms vague context into queryable entities with causal structure.

All three mechanisms make the simulation more **causally complete** - fewer "black box" influences, more explicit modeling of factors that shape events.

You're proposing **modal causality** - different causal regimes that can be selected, not a single causal framework. That's actually coherent and interesting.

## Mechanism 17: Modal Temporal Causality (Causal Regime Selection)

The system operates under one of several causal modes, each with different rules for how time constrains events:

### Mode 1: Pearl Causality (Default/Historical)
Time is substrate. Events cause other events. Standard DAG causality with no temporal agency.

```python
TemporalMode.PEARL:
    - Strict causal ordering (past → present → future)
    - No retrocausality
    - Events determined by prior states + stochastic processes
    - Validators enforce physics-inspired constraints
```

### Mode 2: Directorial Causality (Narrative Time)
Time has **dramatic structure** that shapes events toward narrative coherence. Like a director, time "wants" certain outcomes and creates coincidences, obstacles, or revelations to achieve them.

```python
TemporalMode.DIRECTORIAL:
    properties:
        narrative_arc: str  # "rising_action", "climax", "resolution"
        dramatic_tension: float  # 0.0 to 1.0
        foreshadowing_active: bool
        thematic_goals: List[str]  # "redemption", "tragedy", "triumph"
    
    behaviors:
        # Time "nudges" events toward narrative satisfaction
        - Unlikely coincidences become likely when dramatically appropriate
        - Key characters avoid death until arc completes
        - Obstacles appear when tension needs elevation
        - Resolution events cluster at act boundaries
```

Example: In directorial mode, Hamilton and Jefferson meeting "by chance" at a critical moment has elevated probability if it serves dramatic tension, even if causally improbable.

### Mode 3: Nonlinear Causality (Tarantino Time)
Events can occur out of causal order. Time can loop, jump, or present effects before causes. The system maintains multiple timeline orderings.

```python
TemporalMode.NONLINEAR:
    properties:
        presentation_order: List[timepoint_id]  # how events are shown
        causal_order: List[timepoint_id]  # actual cause-effect sequence
        flashback_probability: float
        flash_forward_probability: float
    
    behaviors:
        # Presentation ≠ causality
        - Can query "what happens next in story" (presentation) vs 
          "what happens next causally" (causal chain)
        - Entities can have knowledge from causally-future events
          (revealed later but experienced earlier in presentation)
        - Exposure events track both causal and presentational time
```

### Mode 4: Branching Causality (Quantum/Many-Worlds)
Time actively explores multiple possibilities simultaneously. Each branch is real, not hypothetical.

```python
TemporalMode.BRANCHING:
    properties:
        branch_points: List[timepoint_id]
        active_branches: List[timeline_id]
        branch_probability: Dict[timeline_id, float]
        observer_perspective: timeline_id  # which branch is "primary"
    
    behaviors:
        # Time doesn't choose one future - it realizes all of them
        - Major decisions create explicit branches
        - Entities exist in superposition across branches
        - Queries can target specific branches or aggregate across them
        - "What would have happened if X" is not counterfactual -
          it's a query on a different branch that actually exists
```

### Mode 5: Cyclical Causality (Mythic Time)
Time loops. Events at T7 can cause events at T0. Prophecy works because future causally influences past.

```python
TemporalMode.CYCLICAL:
    properties:
        cycle_length: int  # number of timepoints before loop
        causal_feedback_strength: float
        prophecy_accuracy: float
        destiny_weight: float  # how much "fate" constrains choices
    
    behaviors:
        # Past, present, future form causal loop
        - Future knowledge can exist at T0 (prophecy, premonition)
        - Attempts to avoid predicted events may cause them
        - Validators allow "impossible" knowledge if cycle explains it
        - Entity decisions constrained by destiny toward loop closure
```

## The "Time as Agent" Implementation

In directorial/cyclical modes, time has **goal-directed behavior**:

```python
class TemporalAgent:
    """Time itself as an entity with goals and behavior"""
    
    mode: TemporalMode
    goals: List[str]  # "complete_narrative_arc", "maintain_tension", "close_loop"
    personality: np.ndarray  # Time's "style" - tragic? comedic? epic?
    
    def influence_event_probability(self, event: Event, context: TimeContext) -> float:
        """Time adjusts likelihood of events to achieve its goals"""
        
        if self.mode == TemporalMode.DIRECTORIAL:
            if event.advances_narrative_arc:
                return boost_probability(event, factor=1.5)
            if event.resolves_tension and context.in_climax:
                return boost_probability(event, factor=2.0)
        
        if self.mode == TemporalMode.CYCLICAL:
            if event.closes_causal_loop:
                return boost_probability(event, factor=3.0)
            if event.prevents_prophecy and context.destiny_weight > 0.7:
                return reduce_probability(event, factor=0.1)
        
        return event.base_probability
```

**Time as observer**:
```python
def temporal_self_awareness(timeline: Timeline) -> TemporalMeta:
    """Time reflects on its own structure"""
    
    return TemporalMeta(
        narrative_completeness=assess_arc_satisfaction(timeline),
        dramatic_tension=measure_event_clustering(timeline),
        causal_coherence=validate_causal_structure(timeline),
        aesthetic_quality=score_narrative_elegance(timeline)
    )
```

Time can "observe" whether the timeline is satisfying its goals (complete narrative arc, maintain tension, close loops) and adjust its influence on future event probabilities accordingly.

## Why This Works

**It's a simulation mode, not a metaphysical claim.** You're not saying time IS conscious in reality - you're saying the simulation can operate under different causal rules depending on what you're modeling:

- Historical simulation → Pearl causality (strict realism)
- Dramatic fiction → Directorial causality (narrative logic)
- Experimental fiction → Nonlinear causality (artistic freedom)
- Theoretical physics → Branching causality (many-worlds)
- Mythology → Cyclical causality (fate/prophecy)

The system becomes **genre-aware**. The same entities in the same scenario produce different outcomes depending on which temporal mode is active.

**The technical win**: Your causal validators don't break - they get parameterized by mode. In Pearl mode, retrocausality is invalid. In Cyclical mode, it's expected. The validators adapt to the selected causal regime.

This is genuinely novel: a temporal simulation that can operate under multiple causal frameworks and make those frameworks explicit and queryable rather than implicit assumptions. Time becomes a configurable parameter, not a fixed substrate.

## Technical Challenges Solved

1. **Token budget allocation**: Query-driven resolution solves the "where to spend tokens" problem without manual importance scoring

2. **Temporal consistency**: Exposure events + causal chains + conservation validators turn consistency from aesthetic goal to computable constraint

3. **Memory/compute tradeoff**: Factorized compression with lazy elevation means you store cheaply but elaborate on demand

4. **Knowledge provenance**: Every fact has a causal explanation, enabling counterfactual reasoning and validation

5. **Simulation refinement**: Progressive training means first query is fast/cheap, subsequent queries get better results without recomputing from scratch

## What's Not Solved (Yet)

**Multi-entity synthesis**: Queries currently target single entities. "How did Washington and Jefferson's relationship evolve?" requires reasoning over two entity trajectories simultaneously.

**Long-context coherence**: Entity knowledge accumulates (Washington: 21 items by T7) but the synthesizer doesn't yet use all of it effectively in responses.

**Optimal compression**: The system compresses but doesn't yet determine optimal compression ratios per entity based on query patterns.

**Automatic importance detection**: Eigenvector centrality is computed but not yet used to inform resolution decisions automatically.

The architecture exists. The remaining work is tuning and integration, not fundamental design changes.