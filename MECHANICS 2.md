# MECHANICS.md - Timepoint-Daedalus Technical Architecture

## Problem Statement

Large language model-based historical simulations face two fundamental constraints:

1. **Token Economics**: Full-context prompting scales as O(entities × timepoints × token_cost), reaching $500/query for 100 entities across 10 timepoints at 50k tokens per entity.
2. **Temporal Consistency**: Compression-based approaches lose causal structure required to prevent anachronisms and maintain coherent temporal evolution.

Traditional solutions treat this as either a caching problem (cache invalidation complexity) or lossy compression problem (breaks temporal reasoning). Both assume uniform fidelity across all entities and timepoints.

## Architectural Solution

Timepoint-Daedalus implements query-driven progressive refinement in a causally-linked temporal graph with heterogeneous fidelity. Resolution adapts to observed query patterns rather than static importance heuristics. This reduces token costs by 95% (from $500 to $5-20 per query) while maintaining temporal consistency through explicit causal validation.

---

## Mechanism 1: Heterogeneous Fidelity Temporal Graphs

### Implementation

Temporal graph where each node (entity, timepoint) pair has independent resolution level. Resolution levels form an ordered set: `TENSOR_ONLY < SCENE < GRAPH < DIALOG < TRAINED`.

```
Graph Structure:
Timepoint(id=T0, event="Inauguration")
├─ Entity(id="washington", resolution=TRAINED, tokens=50k)
├─ Entity(id="adams", resolution=DIALOG, tokens=10k)
├─ Entity(id="attendee_47", resolution=TENSOR_ONLY, tokens=200)
└─ causal_link → Timepoint(id=T1)
```

### Properties

- **Per-entity resolution**: Each entity maintains independent resolution at each timepoint
- **Per-timepoint resolution**: Timepoint itself has resolution affecting all entities present
- **Mutable**: Resolution can increase (elevation) or decrease (compression) based on usage
- **2D fidelity surface**: Detail concentrates around high-centrality entities at critical timepoints

### Storage Requirements

Token budget allocation example for 100 entities × 10 timepoints:
- Uniform high fidelity: 50k × 100 × 10 = 50M tokens
- Heterogeneous fidelity: ~2.5M tokens (95% reduction)

Distribution with power-law usage pattern:
- 5 central entities at TRAINED: 5 × 50k = 250k
- 20 secondary entities at DIALOG: 20 × 10k = 200k  
- 75 peripheral entities at TENSOR_ONLY: 75 × 200 = 15k

---

## Mechanism 2: Progressive Training Without Cache Invalidation

### Metadata-Driven Quality Spectrum

Entity quality exists on continuous spectrum determined by accumulated metadata rather than binary cached/uncached state.

```python
EntityMetadata:
    query_count: int           # Number of times entity queried
    training_iterations: int   # LLM elaboration passes completed
    eigenvector_centrality: float  # Graph centrality score (0-1)
    resolution_level: ResolutionLevel
    last_accessed: datetime
```

### Resolution Elevation Algorithm

```python
def should_elevate_resolution(entity: Entity, threshold_config: Config) -> bool:
    if entity.query_count > threshold_config.frequent_access:
        return entity.resolution < DIALOG
    if entity.eigenvector_centrality > threshold_config.central_node:
        return entity.resolution < GRAPH
    return False
```

### Training Accumulation

Each query increments entity metadata:
1. `query_count += 1`
2. If elevation triggered: `training_iterations += 1`, `resolution = next_level(resolution)`
3. Store both compressed representation (PCA/SVD) and full state
4. Next query retrieves higher-fidelity state

### Resource Allocation Signal

The triple `(query_count, centrality, training_iterations)` functions as Bayesian prior for resource allocation. System learns entity importance through observation rather than prediction.

---

## Mechanism 3: Exposure Event Tracking (Causal Knowledge Provenance)

### Schema

```python
ExposureEvent:
    id: UUID
    entity_id: str
    event_type: EventType  # witnessed, learned, told, experienced
    information: str  # knowledge item acquired
    source: Optional[str]  # entity_id or external source
    timestamp: datetime
    confidence: float  # 0.0-1.0
    timepoint_id: str
```

### Validation Constraint

Knowledge consistency check: `entity.knowledge_state ⊆ {e.information for e in entity.exposure_events where e.timestamp ≤ query_timestamp}`

### Causal Audit Trail

Exposure events form directed acyclic graph:
- Nodes: Information items
- Edges: Causal relationships (entity A learned X from entity B at time T)
- Validation: Walk graph to verify information accessibility

### Counterfactual Reasoning Support

Removing exposure events and recomputing forward enables what-if scenarios:
```
timeline_branch = remove_exposure_events(entity="jefferson", filter=lambda e: e.source=="paris")
propagate_causality(timeline_branch, start=intervention_point)
```

---

## Mechanism 4: Physics-Inspired Validation as Structural Invariants

### Conservation Law Validators

**Information Conservation** (Shannon entropy):
```python
@Validator.register("information_conservation", severity="ERROR")
def validate_information(entity: Entity, context: Dict) -> ValidationResult:
    knowledge = set(entity.knowledge_state)
    exposure = set(e.information for e in context["exposure_history"])
    violations = knowledge - exposure
    return ValidationResult(
        valid=len(violations) == 0,
        violations=list(violations)
    )
```

**Energy Budget** (thermodynamic):
```python
@Validator.register("energy_budget", severity="WARNING")
def validate_energy(entity: Entity, context: Dict) -> ValidationResult:
    budget = entity.cognitive_tensor.energy_budget
    expenditure = sum(interaction.cost for interaction in context["interactions"])
    return ValidationResult(
        valid=expenditure <= budget * 1.2,  # Allow 20% overdraft
        message=f"Expenditure {expenditure} exceeds budget {budget}"
    )
```

**Behavioral Inertia** (momentum):
```python
@Validator.register("behavioral_inertia", severity="WARNING")  
def validate_inertia(entity: Entity, context: Dict) -> ValidationResult:
    if "previous_personality" not in context:
        return ValidationResult(valid=True)
    
    current = np.array(entity.behavior_tensor.personality_vector)
    previous = np.array(context["previous_personality"])
    drift = np.linalg.norm(current - previous)
    
    return ValidationResult(
        valid=drift <= context["inertia_threshold"],
        message=f"Personality drift {drift:.3f} exceeds threshold"
    )
```

**Network Flow** (social capital):
- Influence propagates through relationship graph edges
- Status changes must have source nodes
- Validates power accumulation has causal explanation

### Validator Composition

Entity state valid iff all validators pass. Computational cost: O(n) for n validators, each using set operations or vector norms.

---

## Mechanism 5: Query-Driven Lazy Resolution Elevation

### Resolution Decision Function

```python
def decide_resolution(
    entity: Entity, 
    timepoint: Timepoint,
    query_history: QueryHistory,
    thresholds: ThresholdConfig
) -> ResolutionLevel:
    
    if entity.query_count > thresholds.frequent_access:
        return max(entity.resolution, DIALOG)
    
    if entity.eigenvector_centrality > thresholds.central_node:
        return max(entity.resolution, GRAPH)
    
    if timepoint.importance_score > thresholds.critical_event:
        return max(entity.resolution, SCENE)
    
    return TENSOR_ONLY
```

### Elevation Process

1. Load entity current state (may be compressed)
2. Check resolution sufficiency for query type
3. If insufficient: invoke LLM elaboration pass
4. Store elaborated state, increment training counter
5. Subsequent queries retrieve higher-fidelity state

### Compression Synergy

Storage strategy by resolution:
- TENSOR_ONLY: PCA/SVD compressed tensors only (8-16 floats)
- SCENE: Compressed + summary text (1-2k tokens)
- GRAPH: Compressed + relationships + key facts (5k tokens)
- DIALOG: Compressed + personality + knowledge (10k tokens)
- TRAINED: Full state + all elaborations (50k tokens)

---

## Mechanism 6: TTM Tensor Model (Context/Biology/Behavior Factorization)

### Schema

```python
TTMTensor:
    context_vector: np.ndarray    # Shape: (n_knowledge,) - information state
    biology_vector: np.ndarray    # Shape: (n_physical,) - physical constraints
    behavior_vector: np.ndarray   # Shape: (n_personality,) - behavioral patterns

PhysicalTensor:
    age: float
    health_events: List[HealthEvent]
    location: (float, float) | str
    mobility_level: float  # 0.0-1.0
    biological_constraints: Dict[str, bool]

CognitiveTensor:
    knowledge_state: Set[str]
    belief_vector: np.ndarray
    emotional_state: (float, float)  # (valence, arousal)
    energy_budget: float
    personality_vector: np.ndarray
    personality_momentum: np.ndarray

BehaviorTensor:
    personality_traits: np.ndarray  # Big Five or similar model
    decision_patterns: np.ndarray
    social_preferences: np.ndarray
```

### Compression Ratios

Typical entity state (50k tokens) decomposes to:
- Biology: 100 tokens (age increments, health updates)
- Behavior: 500 tokens (personality stable across timepoints)
- Context: 1000 tokens (knowledge deltas)
- **Total: 1600 tokens vs 50k (97% compression)**

### Dimensionality Reduction

```python
def compress_tensor(tensor: np.ndarray, n_components: int = 8) -> np.ndarray:
    """PCA/SVD compression of entity tensor"""
    pca = PCA(n_components=n_components)
    return pca.fit_transform(tensor.reshape(1, -1)).flatten()
```

Context vectors (knowledge embeddings) compress well due to semantic clustering. Biology vectors compress trivially (mostly constants). Behavior vectors stable across time enable reuse.

### LLM Integration Pattern

```python
def construct_entity_prompt(entity: Entity, query: str) -> str:
    bio = decompress(entity.ttm_tensor.biology_vector)
    behavior = decompress(entity.ttm_tensor.behavior_vector)
    context = decompress(entity.ttm_tensor.context_vector)
    
    return f"""
    Entity: {entity.entity_id}
    Physical: age={bio.age}, health={bio.health}, location={bio.location}
    Personality: {behavior.traits}
    Knowledge: {context.knowledge_items}
    
    Query: {query}
    """
```

---

## Mechanism 7: Causal Temporal Chains

### Schema

```python
Timepoint:
    timepoint_id: str
    timestamp: datetime
    causal_parent: Optional[str]  # Previous timepoint_id
    event_description: str
    entities_present: List[str]
    resolution_level: ResolutionLevel
    importance_score: float
```

### Causality Validation

Information flow constraint: Entity at timepoint T can only reference information from timepoints T' where path exists from T' to T in causal chain.

```python
def validate_temporal_reference(entity: Entity, reference: str, timepoint: Timepoint) -> bool:
    """Check if entity could have learned referenced information"""
    ref_timepoint = get_timepoint_where_learned(reference)
    return has_causal_path(ref_timepoint, timepoint)
```

### Counterfactual Implementation

```python
def create_branch(
    parent_timeline: Timeline,
    branch_point: str,
    intervention: Intervention
) -> Timeline:
    """Create alternate timeline from intervention point"""
    branch = Timeline(parent=parent_timeline.id)
    
    # Copy timepoints before intervention
    for tp in parent_timeline.timepoints_before(branch_point):
        branch.add_timepoint(tp.copy())
    
    # Apply intervention at branch point
    branch_tp = apply_intervention(parent_timeline.get(branch_point), intervention)
    branch.add_timepoint(branch_tp)
    
    # Propagate changes forward
    propagate_causality(branch, start=branch_point)
    
    return branch
```

### Branch Comparison

```python
def compare_timelines(
    timeline_a: Timeline,
    timeline_b: Timeline,
    metric: Callable[[Timepoint], float]
) -> ComparisonResult:
    """Compare outcomes between timelines"""
    divergence_point = find_divergence(timeline_a, timeline_b)
    return ComparisonResult(
        divergence=divergence_point,
        delta=metric(timeline_a.final) - metric(timeline_b.final)
    )
```

---

## Mechanism 8: Embodied Entity States

### Physical Tensor Structure

```python
PhysicalTensor:
    age: float
    health_status: float  # 0.0-1.0
    pain_level: float  # 0.0-1.0
    pain_location: Optional[str]
    mobility: float  # 0.0-1.0
    stamina: float  # 0.0-1.0
    sensory_acuity: Dict[str, float]  # vision, hearing, etc.
    location: (float, float)
```

### Cognitive Tensor Structure

```python
CognitiveTensor:
    knowledge_state: Set[str]
    belief_confidence: Dict[str, float]
    emotional_valence: float  # -1.0 to 1.0
    emotional_arousal: float  # 0.0 to 1.0
    energy_budget: float  # Current available cognitive resources
    attention_capacity: float  # Maximum parallel cognitive load
    decision_confidence: float  # Current certainty level
```

### Age-Dependent Constraint Function

```python
def compute_age_constraints(age: int) -> PhysicalConstraints:
    """Age-dependent capability degradation"""
    return PhysicalConstraints(
        stamina=max(0.3, 1.0 - (age - 25) * 0.01),
        vision=max(0.4, 1.0 - (age - 20) * 0.015),
        hearing=max(0.5, 1.0 - (age - 30) * 0.01),
        recovery_rate=1.0 / (1.0 + (age - 30) * 0.05)
    )
```

### Validation Integration

```python
@Validator.register("physical_capability", severity="ERROR")
def validate_physical_action(entity: Entity, action: Action) -> ValidationResult:
    constraints = compute_age_constraints(entity.physical_tensor.age)
    
    if action.type == "sprint" and constraints.stamina < 0.3:
        return ValidationResult(
            valid=False,
            message=f"Entity age {entity.physical_tensor.age} insufficient stamina"
        )
    
    if action.type == "read_fine_print" and constraints.vision < 0.5:
        return ValidationResult(
            valid=False,
            message="Visual acuity insufficient"
        )
    
    return ValidationResult(valid=True)
```

---

## Mechanism 8.1: Body-Mind Coupling

### Somatic-Cognitive Coupling Pathways

```python
def couple_pain_to_cognition(physical: PhysicalTensor, cognitive: CognitiveTensor) -> CognitiveTensor:
    """Pain affects cognitive state"""
    pain_factor = physical.pain_level
    
    cognitive.energy_budget *= (1.0 - pain_factor * 0.5)
    cognitive.emotional_valence -= pain_factor * 0.3
    cognitive.patience_threshold -= pain_factor * 0.4
    cognitive.decision_confidence *= (1.0 - pain_factor * 0.2)
    
    return cognitive

def couple_illness_to_cognition(physical: PhysicalTensor, cognitive: CognitiveTensor) -> CognitiveTensor:
    """Illness impairs judgment and engagement"""
    if physical.fever > 38.5:  # Celsius
        cognitive.decision_confidence *= 0.7
        cognitive.risk_tolerance += 0.2
        cognitive.social_engagement -= 0.4
    
    return cognitive
```

### Temporal Propagation of Chronic Conditions

```python
def propagate_chronic_condition(
    entity: Entity,
    condition: ChronicCondition,
    onset_timepoint: str,
    current_timepoint: str,
    timeline: Timeline
) -> None:
    """Apply chronic condition effects across timepoints"""
    
    for tp in timeline.timepoints_between(onset_timepoint, current_timepoint):
        entity_at_tp = timeline.get_entity_at(entity.id, tp.id)
        
        entity_at_tp.cognitive_tensor.baseline_mood -= condition.mood_impact
        entity_at_tp.physical_tensor.sleep_quality *= condition.sleep_modifier
        entity_at_tp.cognitive_tensor.cognitive_load += condition.mental_burden
```

### Medical History Schema

```python
MedicalHistory:
    injuries: List[Injury]
    illnesses: List[Illness]
    treatments: List[Treatment]
    baseline_health: float  # Constitutional robustness

Injury:
    type: str  # "gunshot", "fracture", "burn"
    location: str  # Body part affected
    severity: float  # 0.0-1.0
    occurrence: datetime
    healing_trajectory: Callable[[timedelta], float]

Illness:
    type: str  # "fever", "infection", "chronic_pain"
    onset: datetime
    duration: Optional[timedelta]
    severity_function: Callable[[datetime], float]
    
Treatment:
    type: str  # "surgery", "medication", "therapy"
    administered: datetime
    effectiveness: float  # 0.0-1.0
```

### Query Integration

When query references somatic state:
```python
def synthesize_somatic_query(entity: Entity, query: str, timepoint: Timepoint) -> str:
    physical = entity.physical_tensor_at(timepoint)
    cognitive = couple_pain_to_cognition(physical, entity.cognitive_tensor_at(timepoint))
    
    return f"""
    Entity {entity.id} at {timepoint.timestamp}:
    Physical state: pain_level={physical.pain_level}, location={physical.pain_location}
    Cognitive impact: energy={cognitive.energy_budget}, mood={cognitive.emotional_valence}
    
    Query: {query}
    
    Synthesize response incorporating somatic influence on cognition.
    """
```

---

## Mechanism 9: On-Demand Entity Generation

### Entity Gap Detection

```python
def detect_entity_gap(query: str, existing_entities: Set[str]) -> Optional[EntitySpec]:
    """Parse query for referenced but non-existent entities"""
    referenced_entities = extract_entity_references(query)
    missing = referenced_entities - existing_entities
    
    if missing:
        return EntitySpec(
            entity_id=missing.pop(),
            inferred_type="person",  # Could be refined
            inferred_context=extract_context_clues(query)
        )
    return None
```

### Dynamic Entity Creation

```python
def generate_entity_on_demand(
    spec: EntitySpec,
    timepoint: Timepoint,
    llm_client: LLMClient
) -> Entity:
    """Create plausible entity matching query context"""
    
    context = {
        "timepoint": timepoint.timestamp,
        "event": timepoint.event_description,
        "entities_present": timepoint.entities_present,
        "role": spec.inferred_role
    }
    
    # Generate at minimal resolution
    entity_data = llm_client.populate_entity(
        entity_id=spec.entity_id,
        resolution=TENSOR_ONLY,
        context=context
    )
    
    entity = Entity(
        entity_id=spec.entity_id,
        entity_type=spec.inferred_type,
        resolution_level=TENSOR_ONLY,
        **entity_data
    )
    
    # Persist for future queries
    store.save_entity(entity)
    
    return entity
```

### Integration with Query System

```python
def handle_query_with_generation(query: str, store: GraphStore, llm: LLMClient) -> Response:
    intent = parse_query(query)
    
    if intent.entity_id not in store.entities:
        spec = detect_entity_gap(query, store.entities.keys())
        if spec:
            entity = generate_entity_on_demand(spec, intent.timepoint, llm)
        else:
            return Response(error="Entity not found and cannot infer specification")
    else:
        entity = store.get_entity(intent.entity_id)
    
    return synthesize_response(entity, query, llm)
```

---

## Mechanism 10: Scene-Level Entity Sets

### Scene Entity Schema

```python
SceneEntity:
    scene_id: str
    timepoint_id: str
    environment: EnvironmentEntity
    atmosphere: AtmosphereEntity
    crowd: Optional[CrowdEntity]
    
EnvironmentEntity:
    location: str
    physical_layout: Dict[str, Any]  # Spatial structure
    capacity: int
    ambient_temperature: float
    lighting_level: float
    weather: Optional[WeatherConditions]
    
AtmosphereEntity:
    tension_level: float  # 0.0-1.0
    formality_level: float
    emotional_aggregate: (float, float)  # Valence, arousal averaged
    social_norms: List[str]
    
CrowdEntity:
    size: int
    density: float
    mood_distribution: Dict[str, float]  # mood → probability
    movement_pattern: str  # "static", "flowing", "agitated"
```

### Aggregate Computation

```python
def compute_scene_atmosphere(entities: List[Entity], environment: EnvironmentEntity) -> AtmosphereEntity:
    """Aggregate individual entity states into scene properties"""
    
    emotional_states = [e.cognitive_tensor.emotional_state for e in entities]
    avg_valence = np.mean([e[0] for e in emotional_states])
    avg_arousal = np.mean([e[1] for e in emotional_states])
    
    tension = compute_tension_from_conflicts(entities)
    formality = infer_formality_from_context(environment, entities)
    
    return AtmosphereEntity(
        tension_level=tension,
        formality_level=formality,
        emotional_aggregate=(avg_valence, avg_arousal),
        social_norms=infer_norms(environment)
    )
```

### Query Integration

Query "What was the atmosphere like?" synthesizes from:
- Named entity emotional states (aggregated)
- Environment constraints (capacity, lighting, temperature)
- Crowd dynamics (if present)
- Social context (formality, tensions)

---

## Mechanism 11: Dialog/Interaction Synthesis

### Interaction Schema

```python
Interaction:
    interaction_id: str
    participants: List[str]  # entity_ids
    timepoint_id: str
    interaction_type: str  # "conversation", "confrontation", "collaboration"
    duration: timedelta
    information_exchanged: List[InformationFlow]
    
InformationFlow:
    from_entity: str
    to_entity: str
    information: str
    confidence: float
    timestamp: datetime
```

### Dialog Generation

```python
def synthesize_dialog(
    entities: List[Entity],
    timepoint: Timepoint,
    llm_client: LLMClient
) -> Dialog:
    """Generate conversation between entities"""
    
    # Load entity states at timepoint
    states = [get_entity_state_at(e, timepoint) for e in entities]
    
    # Build conversation context
    context = {
        "participants": [
            {
                "id": e.entity_id,
                "knowledge": e.knowledge_state,
                "personality": e.behavior_tensor.personality_traits,
                "goals": e.current_goals,
                "emotional_state": e.cognitive_tensor.emotional_state
            }
            for e in states
        ],
        "setting": timepoint.event_description,
        "constraints": get_social_constraints(timepoint)
    }
    
    # Generate dialog
    dialog = llm_client.generate_dialog(context)
    
    # Create exposure events for information exchange
    for turn in dialog.turns:
        for listener in dialog.participants:
            if listener != turn.speaker:
                create_exposure_event(
                    entity_id=listener,
                    information=turn.content,
                    source=turn.speaker,
                    event_type="told",
                    timestamp=timepoint.timestamp
                )
    
    return dialog
```

### Causal Consistency Check

```python
def validate_dialog_consistency(dialog: Dialog, entities: List[Entity]) -> ValidationResult:
    """Ensure dialog respects entity knowledge constraints"""
    
    for turn in dialog.turns:
        speaker = get_entity(turn.speaker)
        referenced_knowledge = extract_knowledge_references(turn.content)
        
        available_knowledge = get_knowledge_at_timepoint(speaker, turn.timestamp)
        
        if not referenced_knowledge.issubset(available_knowledge):
            return ValidationResult(
                valid=False,
                message=f"Speaker {turn.speaker} references unknown information"
            )
    
    return ValidationResult(valid=True)
```

---

## Mechanism 12: Counterfactual Branching

### Branch Creation Algorithm

```python
def create_counterfactual_branch(
    parent_timeline: Timeline,
    intervention_point: str,
    intervention: Intervention
) -> Timeline:
    """Create alternate timeline with intervention applied"""
    
    # Create new timeline
    branch = Timeline(
        timeline_id=generate_uuid(),
        parent_timeline_id=parent_timeline.timeline_id,
        branch_point=intervention_point,
        intervention_description=intervention.description
    )
    
    # Copy timepoints before intervention
    for tp in parent_timeline.get_timepoints_before(intervention_point):
        branch.add_timepoint(tp.deep_copy())
    
    # Apply intervention at branch point
    branch_tp = parent_timeline.get_timepoint(intervention_point).deep_copy()
    apply_intervention(branch_tp, intervention)
    branch.add_timepoint(branch_tp)
    
    # Propagate causality forward
    current = branch_tp
    while current.causal_parent:
        next_tp = propagate_causal_effects(current, intervention)
        branch.add_timepoint(next_tp)
        current = next_tp
    
    return branch
```

### Intervention Types

```python
class Intervention:
    """Base class for timeline interventions"""
    
class EntityRemoval(Intervention):
    entity_id: str
    
class EntityModification(Intervention):
    entity_id: str
    modifications: Dict[str, Any]
    
class EventCancellation(Intervention):
    event_description: str
    
class InformationInjection(Intervention):
    target_entity: str
    information: str
    source: str
```

### Timeline Comparison

```python
def compare_timelines(
    baseline: Timeline,
    counterfactual: Timeline,
    metrics: List[MetricFunction]
) -> ComparisonReport:
    """Compare outcomes between timelines"""
    
    divergence = find_first_divergence(baseline, counterfactual)
    
    results = {}
    for metric in metrics:
        baseline_value = metric(baseline)
        counterfactual_value = metric(counterfactual)
        results[metric.name] = {
            "baseline": baseline_value,
            "counterfactual": counterfactual_value,
            "delta": counterfactual_value - baseline_value
        }
    
    return ComparisonReport(
        divergence_point=divergence,
        metrics=results,
        causal_explanation=explain_divergence(baseline, counterfactual, divergence)
    )
```

---

## Mechanism 13: Multi-Entity Synthesis (Query Composition)

### Relationship Trajectory Analysis

```python
def analyze_relationship_evolution(
    entity_a: str,
    entity_b: str,
    timeline: Timeline,
    start: datetime,
    end: datetime
) -> RelationshipTrajectory:
    """Track relationship changes across timepoints"""
    
    trajectory = RelationshipTrajectory(entity_a=entity_a, entity_b=entity_b)
    
    for tp in timeline.get_timepoints_between(start, end):
        if entity_a in tp.entities_present and entity_b in tp.entities_present:
            state_a = get_entity_state_at(entity_a, tp)
            state_b = get_entity_state_at(entity_b, tp)
            
            relationship_state = compute_relationship_metrics(state_a, state_b)
            trajectory.add_state(tp.timestamp, relationship_state)
    
    return trajectory
```

### Comparative Synthesis

```python
def synthesize_multi_entity_response(
    entities: List[str],
    query: str,
    timeline: Timeline,
    llm_client: LLMClient
) -> Response:
    """Generate response requiring multiple entity perspectives"""
    
    # Load all entity states
    entity_states = [
        {
            "entity_id": eid,
            "knowledge": get_knowledge_timeline(eid, timeline),
            "relationships": get_relationships(eid, timeline),
            "personality": get_personality(eid)
        }
        for eid in entities
    ]
    
    # Identify interaction points
    interactions = find_shared_timepoints(entities, timeline)
    
    # Build synthesis context
    context = {
        "entities": entity_states,
        "interactions": interactions,
        "query": query
    }
    
    # Generate comparative analysis
    response = llm_client.synthesize_comparative(context)
    
    # Add citations to source entities
    response.citations = extract_entity_citations(response.text, entities)
    
    return response
```

### Contradiction Detection

```python
def detect_contradictions(
    entities: List[Entity],
    timepoint: Timepoint
) -> List[Contradiction]:
    """Find inconsistent beliefs or knowledge between entities"""
    
    contradictions = []
    
    for i, entity_a in enumerate(entities):
        for entity_b in entities[i+1:]:
            beliefs_a = entity_a.cognitive_tensor.belief_vector
            beliefs_b = entity_b.cognitive_tensor.belief_vector
            
            # Compare beliefs on shared topics
            shared_topics = find_shared_belief_topics(beliefs_a, beliefs_b)
            
            for topic in shared_topics:
                if abs(beliefs_a[topic] - beliefs_b[topic]) > CONTRADICTION_THRESHOLD:
                    contradictions.append(Contradiction(
                        entity_a=entity_a.entity_id,
                        entity_b=entity_b.entity_id,
                        topic=topic,
                        position_a=beliefs_a[topic],
                        position_b=beliefs_b[topic],
                        severity=abs(beliefs_a[topic] - beliefs_b[topic])
                    ))
    
    return contradictions
```

---

## Mechanism 14: Circadian Activity Patterns

### Circadian Context Schema

```python
CircadianContext:
    hour: int  # 0-23
    typical_activities: Dict[str, float]  # activity → probability
    ambient_conditions: AmbientConditions
    social_constraints: List[str]
    
AmbientConditions:
    lighting: float  # 0.0-1.0 (dark to bright)
    temperature: float  # Celsius
    crowd_density: float  # 0.0-1.0
    noise_level: float  # 0.0-1.0
```

### Activity Probability Functions

```python
def get_activity_probability(hour: int, activity: str) -> float:
    """Return probability of activity at given hour"""
    
    probability_map = {
        "sleep": lambda h: 0.95 if 0 <= h < 6 else 0.05,
        "meals": lambda h: 0.8 if h in [7, 12, 19] else 0.1,
        "work": lambda h: 0.7 if 9 <= h < 17 else 0.1,
        "social": lambda h: 0.6 if 18 <= h < 23 else 0.2,
        "emergency": lambda h: 0.05,  # Constant low probability
    }
    
    return probability_map.get(activity, lambda h: 0.0)(hour)
```

### Energy Budget Integration

```python
def compute_energy_cost(activity: Activity, hour: int) -> float:
    """Calculate energy expenditure adjusted for time of day"""
    
    base_cost = activity.base_energy_cost
    
    # Night activities cost more
    if 22 <= hour or hour < 6:
        circadian_penalty = 1.5
    else:
        circadian_penalty = 1.0
    
    # Fatigue accumulation throughout day
    hours_awake = compute_hours_awake(hour)
    fatigue_factor = 1.0 + (hours_awake / 16) * 0.5
    
    return base_cost * circadian_penalty * fatigue_factor
```

### Validation

```python
@Validator.register("circadian_plausibility", severity="WARNING")
def validate_circadian_activity(
    entity: Entity,
    activity: Activity,
    timepoint: Timepoint
) -> ValidationResult:
    """Check if activity plausible at this time"""
    
    hour = timepoint.timestamp.hour
    prob = get_activity_probability(hour, activity.type)
    
    if prob < PLAUSIBILITY_THRESHOLD and not activity.marked_exceptional:
        return ValidationResult(
            valid=False,
            message=f"Activity {activity.type} at hour {hour} has low probability {prob:.2f}"
        )
    
    return ValidationResult(valid=True)
```

---

## Mechanism 15: Entity Prospection (Internal Forecasting)

### Prospective State Schema

```python
ProspectiveState:
    entity_id: str
    timepoint_id: str
    forecast_horizon: timedelta
    expectations: List[Expectation]
    contingency_plans: Dict[str, List[Action]]
    anxiety_level: float  # 0.0-1.0
    
Expectation:
    predicted_event: str
    subjective_probability: float
    desired_outcome: bool
    preparation_actions: List[str]
    confidence: float
```

### Expectation Generation

```python
def generate_prospective_state(
    entity: Entity,
    current_timepoint: Timepoint,
    llm_client: LLMClient
) -> ProspectiveState:
    """Generate entity's expectations about future"""
    
    context = {
        "entity_knowledge": entity.knowledge_state,
        "current_situation": current_timepoint.event_description,
        "personality": entity.behavior_tensor.personality_traits,
        "past_experiences": get_relevant_history(entity, current_timepoint)
    }
    
    expectations = llm_client.generate_expectations(context)
    
    return ProspectiveState(
        entity_id=entity.entity_id,
        timepoint_id=current_timepoint.timepoint_id,
        forecast_horizon=timedelta(days=30),
        expectations=expectations,
        anxiety_level=compute_anxiety(expectations)
    )
```

### Prediction Error Update

```python
def update_forecast_accuracy(
    entity: Entity,
    expectation: Expectation,
    actual_outcome: Event
) -> None:
    """Update entity's forecasting capability based on accuracy"""
    
    prediction_error = abs(expectation.subjective_probability - actual_outcome.occurred)
    
    # Update meta-cognitive confidence
    entity.cognitive_tensor.forecast_confidence *= (1.0 - prediction_error * 0.1)
    
    # Adjust anxiety based on outcome match
    if actual_outcome.occurred and not expectation.desired_outcome:
        entity.cognitive_tensor.anxiety_level += 0.1
    elif actual_outcome.occurred and expectation.desired_outcome:
        entity.cognitive_tensor.anxiety_level -= 0.1
```

### Behavioral Influence

```python
def influence_behavior_from_expectations(
    entity: Entity,
    prospective_state: ProspectiveState
) -> Entity:
    """Modify entity behavior based on expectations"""
    
    # High anxiety increases conservatism
    if prospective_state.anxiety_level > 0.7:
        entity.behavior_tensor.risk_tolerance *= 0.7
        entity.cognitive_tensor.information_seeking += 0.2
    
    # Preparation actions consume energy budget
    energy_for_prep = sum(
        estimate_energy_cost(action) 
        for exp in prospective_state.expectations 
        for action in exp.preparation_actions
    )
    entity.cognitive_tensor.energy_budget -= energy_for_prep
    
    return entity
```

---

## Mechanism 16: Animistic Entity Extension (Experimental Plugin)

### Non-Human Entity Types

```python
@experimental_plugin("animism")
class AnimisticEntityTypes:
    ANIMAL = "animal"
    PLANT = "plant"
    OBJECT = "object"
    BUILDING = "building"
    ABSTRACT = "abstract_concept"
```

### Animal Entity Schema

```python
AnimalEntity(Entity):
    entity_type: str = "animal"
    species: str
    biological_state: AnimalBiologicalState
    training_level: float  # 0.0-1.0 for domesticated animals
    goals: List[str]  # Simple biological goals
    
AnimalBiologicalState:
    age: float
    health: float
    energy_level: float
    hunger: float
    stress_level: float
```

### Building Entity Schema

```python
BuildingEntity(Entity):
    entity_type: str = "building"
    structural_integrity: float
    capacity: int
    age: int
    maintenance_state: float
    constraints: List[str]
    affordances: List[str]  # What actions it enables/prevents
```

### Abstract Concept Entity Schema

```python
AbstractEntity(Entity):
    entity_type: str = "abstract_concept"
    propagation_vector: np.ndarray  # How it spreads
    intensity: float  # How strongly felt
    carriers: List[str]  # Entity IDs holding this concept
    decay_rate: float  # Natural diminishment over time
    
    def propagate(self, from_entity: str, to_entity: str, interaction: Interaction) -> float:
        """Calculate probability of concept transfer"""
        transmission_prob = np.dot(
            self.propagation_vector,
            interaction.receptivity_vector
        )
        return min(1.0, transmission_prob * self.intensity)
```

### AnyEntity Schema

```python
AnyEntity(Entity):
    entity_type: str = "any"
    adaptability: float  # 0.0-1.0 - How easily it can adapt/become anything
    current_form: Dict[str, Any]  # Current manifestation
    transformation_history: List[Dict[str, Any]]  # Previous forms
    context_sensitivity: float  # How much it adapts to context

    def adapt_to_context(self, context: Dict[str, Any]) -> None:
        """Dynamically adapt entity properties based on context"""
        # Implementation for adaptive behavior
```

### KamiEntity Schema

```python
KamiEntity(Entity):
    entity_type: str = "kami"
    disclosure_level: float  # 0.0-1.0 - How visible/revealed to humans
    force_type: str  # "visible", "invisible", "manifested", "spiritual"
    influence_radius: float  # Spatial/temporal range of influence
    intervention_history: List[Dict[str, Any]]  # Past interventions
    spiritual_constraints: List[str]  # Rules governing behavior

    def assess_intervention(self, situation: Dict[str, Any]) -> float:
        """Determine probability of kami intervention"""
        # Implementation for spiritual force behavior
```

### AIEntity Schema

```python
AIEntity(BaseModel):
    entity_type: str = "ai"

    # Core AI parameters
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1000
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    model_name: str = "gpt-3.5-turbo"

    # System prompt and context
    system_prompt: str = ""
    context_injection: Dict[str, Any] = {}
    knowledge_base: List[str] = []
    behavioral_constraints: List[str] = []

    # Operational parameters
    activation_threshold: float = 0.5
    response_cache_ttl: int = 300
    rate_limit_per_minute: int = 60
    safety_level: str = "moderate"

    # Integration capabilities
    api_endpoints: Dict[str, str] = {}
    webhook_urls: List[str] = []
    integration_tokens: Dict[str, str] = {}

    # Monitoring and control
    performance_metrics: Dict[str, float] = {}
    error_handling: Dict[str, str] = {}
    fallback_responses: List[str] = []

    # Safety and validation
    input_bleaching_rules: List[str] = []
    output_filtering_rules: List[str] = []
    prohibited_topics: List[str] = []
    required_disclaimers: List[str] = []
```

### Animism Level Control

```python
class AnimismConfig:
    level: int  # 0-6

    # Level 0: Only human entities
    # Level 1: Humans + named animals/buildings with direct causal influence
    # Level 2: All objects/organisms with measurable causal influence
    # Level 3: Abstract concepts (ideas, rumors, movements) as propagating entities
    # Level 4: AnyEntity - highly adaptive entities that can be anything
    # Level 5: KamiEntity - visible/invisible spiritual forces with disclosure properties
    # Level 6: AIEntity - AI-powered entities with external agent integration

    def should_create_entity(self, entity_type: str) -> bool:
        type_hierarchy = {
            "human": 0,
            "animal": 1,
            "building": 1,
            "object": 2,
            "plant": 2,
            "abstract": 3,
            "any": 4,
            "kami": 5,
            "ai": 6
        }
        return type_hierarchy.get(entity_type, 6) <= self.level
```

### Integration with Causal Validation

Non-human entities constrain human entity actions:
- Horse stamina limits travel distance
- Building capacity limits attendee count
- Object breakage creates event triggers
- Abstract concept propagation influences belief states

```python
@Validator.register("environmental_constraints", severity="ERROR")
def validate_environmental_constraints(
    action: Action,
    environment_entities: List[Entity]
) -> ValidationResult:
    """Check if action violates environmental constraints"""
    
    for entity in environment_entities:
        if isinstance(entity, BuildingEntity):
            if action.participant_count > entity.capacity:
                return ValidationResult(
                    valid=False,
                    message=f"Action requires {action.participant_count} but capacity is {entity.capacity}"
                )
        
        if isinstance(entity, AnimalEntity):
            if action.requires_mount and entity.energy_level < action.required_stamina:
                return ValidationResult(
                    valid=False,
                    message=f"Mount {entity.entity_id} insufficient stamina"
                )
    
    return ValidationResult(valid=True)
```

---

## Mechanism 17: Modal Temporal Causality (Causal Regime Selection)

### Causal Mode Enumeration

```python
class TemporalMode(Enum):
    PEARL = "pearl"              # Standard DAG causality
    DIRECTORIAL = "directorial"  # Narrative structure influences events
    NONLINEAR = "nonlinear"      # Presentation order ≠ causal order
    BRANCHING = "branching"      # Many-worlds, all branches real
    CYCLICAL = "cyclical"        # Time loops, retrocausality permitted
```

### Mode-Specific Configuration

```python
class PearlCausalityConfig:
    strict_ordering: bool = True
    allow_retrocausality: bool = False
    stochastic_events: bool = True
    
class DirectorialCausalityConfig:
    narrative_arc: str  # "rising_action", "climax", "falling_action", "resolution"
    dramatic_tension: float
    foreshadowing_enabled: bool
    thematic_goals: List[str]
    coincidence_boost_factor: float
    
class NonlinearCausalityConfig:
    presentation_order: List[str]  # timepoint_ids in presentation sequence
    causal_order: List[str]  # timepoint_ids in actual causality sequence
    flashback_probability: float
    flash_forward_probability: float
    
class BranchingCausalityConfig:
    branch_points: List[str]
    active_branches: List[str]
    branch_probabilities: Dict[str, float]
    observer_perspective: str  # Primary branch for queries
    
class CyclicalCausalityConfig:
    cycle_length: int
    causal_feedback_strength: float
    prophecy_accuracy: float
    destiny_weight: float
```

### Temporal Agent (Directorial/Cyclical Modes)

```python
class TemporalAgent:
    """Time as entity with goals and behavior in non-Pearl modes"""
    
    mode: TemporalMode
    goals: List[str]
    personality: np.ndarray
    
    def influence_event_probability(
        self,
        event: Event,
        context: TimeContext
    ) -> float:
        """Adjust event probability to achieve temporal goals"""
        
        base_probability = event.base_probability
        
        if self.mode == TemporalMode.DIRECTORIAL:
            if self.advances_narrative_arc(event, context):
                return base_probability * 1.5
            if self.resolves_tension(event, context):
                return base_probability * 2.0
        
        if self.mode == TemporalMode.CYCLICAL:
            if self.closes_causal_loop(event, context):
                return base_probability * 3.0
            if self.prevents_prophecy(event, context):
                return base_probability * 0.1
        
        return base_probability
    
    def temporal_self_awareness(self, timeline: Timeline) -> TemporalMeta:
        """Assess timeline quality against goals"""
        return TemporalMeta(
            narrative_completeness=self.assess_arc_satisfaction(timeline),
            dramatic_tension=self.measure_event_clustering(timeline),
            causal_coherence=self.validate_causal_structure(timeline)
        )
```

### Validator Mode Adaptation

```python
@Validator.register("temporal_consistency", severity="ERROR")
def validate_temporal_consistency(
    entity: Entity,
    knowledge_item: str,
    timepoint: Timepoint,
    mode: TemporalMode
) -> ValidationResult:
    """Validate knowledge consistent with temporal mode"""
    
    if mode == TemporalMode.PEARL:
        # Strict forward causality
        learned_at = find_knowledge_origin(entity, knowledge_item)
        if learned_at and learned_at.timestamp > timepoint.timestamp:
            return ValidationResult(
                valid=False,
                message=f"Knowledge from future ({learned_at.timestamp})"
            )
    
    elif mode == TemporalMode.CYCLICAL:
        # Allow future knowledge if loop closes
        if is_part_of_closed_loop(entity, knowledge_item, timepoint):
            return ValidationResult(valid=True, message="Prophecy valid")
        
    elif mode == TemporalMode.NONLINEAR:
        # Check causal order, not presentation order
        causal_time = get_causal_timestamp(timepoint)
        if learned_at.causal_timestamp > causal_time:
            return ValidationResult(
                valid=False,
                message="Violates causal order despite presentation order"
            )
    
    return ValidationResult(valid=True)
```

### Mode Selection Impact

Selection of temporal mode affects:
- Event probability calculations
- Knowledge validation rules
- Causal chain construction
- Query interpretation
- Entity behavior constraints

Genre-specific configurations:
- Historical simulation: `PEARL` mode (realism)
- Dramatic fiction: `DIRECTORIAL` mode (narrative coherence)
- Experimental fiction: `NONLINEAR` mode (artistic freedom)
- Theoretical physics: `BRANCHING` mode (many-worlds)
- Mythology: `CYCLICAL` mode (fate/prophecy)

---

## Technical Challenges Addressed

1. **Token Budget Allocation**: Query-driven resolution with progressive training eliminates manual importance scoring. System learns entity value through query patterns.

2. **Temporal Consistency**: Exposure event tracking + causal chains + conservation validators transform consistency from aesthetic goal to computable constraint with O(n) validation cost.

3. **Memory-Compute Tradeoff**: Factorized tensor compression (Context/Biology/Behavior) with lazy elevation enables cheap storage (8-16 floats) with on-demand elaboration (50k tokens).

4. **Knowledge Provenance**: Exposure event DAG provides causal audit trail enabling counterfactual reasoning through event removal and forward propagation.

5. **Simulation Refinement**: Progressive training accumulates quality through usage. First query: cheap compressed state. Hundredth query: detailed elevated state. No recomputation from scratch.

---

## Outstanding Implementation Gaps

### Multi-Entity Synthesis
Queries currently target single entities. Comparative synthesis across multiple entity trajectories requires loading multiple states, identifying interaction points, and generating cross-entity analysis.

### Long-Context Coherence
Entity knowledge accumulates (e.g., 42 items by T7) but query synthesizer doesn't effectively rank and filter knowledge by relevance to query. Requires semantic similarity scoring.

### Optimal Compression
System implements PCA/SVD/NMF compression but doesn't dynamically adjust compression ratios based on query patterns and resolution levels. Needs adaptive compression strategy.

### Automatic Importance Detection
Eigenvector centrality computed but not yet integrated into resolution decision function. Requires threshold calibration and feedback loop.

### Query-Knowledge Matching
Current implementation returns random knowledge items rather than most relevant. Requires semantic scoring: `relevance(knowledge_item, query) → [0,1]` integrated into synthesis.

---

## Performance Characteristics

### Token Cost Reduction
- Naive approach: 50k tokens/entity × 100 entities × 10 timepoints = 50M tokens ≈ $500/query
- Heterogeneous fidelity: ~2.5M tokens ≈ $25/query (95% reduction)
- With compression: ~250k tokens ≈ $2.50/query (99.5% reduction)

### Validation Complexity
- Information conservation: O(|knowledge|) set operation
- Energy budget: O(|interactions|) summation
- Behavioral inertia: O(|personality_dimensions|) vector norm
- Network flow: O(|edges|) graph traversal
- **Total: O(n) where n = max(knowledge, interactions, personality_dimensions, edges)**

### Compression Ratios
- Context tensor: 1000 dims → 8 dims (PCA) = 99.2% reduction
- Biology tensor: 50 dims → 4 dims = 92% reduction
- Behavior tensor: 100 dims → 8 dims = 92% reduction
- **Overall: 50k tokens → 200 tokens = 99.6% reduction at TENSOR_ONLY**

### Query Latency
- TENSOR_ONLY: <100ms (decompression only)
- SCENE: ~1s (partial LLM elaboration)
- DIALOG: ~3s (full LLM call)
- TRAINED: ~10s (comprehensive elaboration)

---

## Integration Architecture

```
Query Interface
    ↓
Query Parser (Intent Extraction)
    ↓
Entity Resolution (Load or Generate)
    ↓
Resolution Decision (Elevation if needed)
    ↓
State Loading (Decompress Tensors)
    ↓
Validation (Conservation Laws)
    ↓
LLM Synthesis (Response Generation)
    ↓
Citation Extraction (Provenance)
    ↓
Response + Metadata
```

Each mechanism integrates at specific integration points:
- Mechanisms 1-2: Resolution Decision
- Mechanisms 3-4: Validation
- Mechanism 5: Resolution Decision + State Loading
- Mechanism 6: State Loading (Tensor decompression)
- Mechanism 7: Entity Resolution (Causal chain navigation)
- Mechanisms 8-8.1: State Loading (Physical/Cognitive coupling)
- Mechanism 9: Entity Resolution (Dynamic generation)
- Mechanisms 10-11: LLM Synthesis (Scene/Dialog generation)
- Mechanism 12: Query Parser (Branch selection)
- Mechanism 13: LLM Synthesis (Multi-entity aggregation)
- Mechanisms 14-15: Validation (Circadian/Prospection checks)
- Mechanism 16: Entity Resolution (Animistic entity support)
- Mechanism 17: Validation (Mode-specific rules)

---

## References

- Pearl, J. (2009). Causality: Models, Reasoning, and Inference. Cambridge University Press.
- Shannon, C. E. (1948). A Mathematical Theory of Communication. Bell System Technical Journal.
- Schölkopf, B., et al. (2021). Toward Causal Representation Learning. Proceedings of the IEEE.
- Vaswani, A., et al. (2017). Attention Is All You Need. NeurIPS.