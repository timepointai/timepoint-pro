# OrchestratorAgent Documentation

## Overview

The **OrchestratorAgent** is a scene-to-specification compiler that bridges the gap between natural language event descriptions and fully-specified simulations ready for the Timepoint-Daedalus system.

### The Problem It Solves

**Before OrchestratorAgent:**
```python
# Manual setup required
entities = [create_entity("madison"), create_entity("hamilton"), ...]
timepoints = [create_timepoint("tp_001", ...), ...]
graph = nx.Graph()
graph.add_edge("madison", "hamilton", ...)
# ... 100+ lines of manual specification ...
```

**After OrchestratorAgent:**
```python
result = simulate_event(
    "simulate the constitutional convention",
    llm_client,
    store
)
# Done! Entities, timepoints, graph, and knowledge all generated
```

## Architecture

The OrchestratorAgent is composed of four specialized components that work in sequence:

```
Natural Language Input
    ↓
┌─────────────────────┐
│   Scene Parser      │  LLM-based decomposition
│  (SceneParser)      │  Event → Structured Spec
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Knowledge Seeder   │  Initial knowledge → ExposureEvents
│ (KnowledgeSeeder)   │  Establishes causal provenance
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Relationship        │  Entity relationships → NetworkX graph
│  Extractor          │  Social/spatial network construction
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Resolution          │  Role-based fidelity targeting
│  Assigner           │  primary → TRAINED, background → TENSOR
└──────────┬──────────┘
           ↓
    Simulation-Ready Scene
    (Entities, Timepoints, Graph, Temporal Agent)
```

## Components

### 1. SceneParser

**Purpose**: Parse natural language descriptions into structured `SceneSpecification` objects.

**LLM Prompt Structure**:
```
Given: "simulate the constitutional convention"

Returns: JSON with:
- scene_title: "Constitutional Convention 1787"
- temporal_scope: {start_date, end_date, location}
- entities: [{entity_id, role, initial_knowledge, relationships}, ...]
- timepoints: [{timepoint_id, timestamp, event_description, causal_parent}, ...]
- temporal_mode: "pearl|directorial|cyclical|branching|nonlinear"
```

**Key Features**:
- Extracts temporal scope (when, where)
- Identifies entity roster (who)
- Sequences events (what happens when)
- Assigns roles (primary/secondary/background/environment)
- Suggests appropriate temporal mode

**Example**:
```python
from orchestrator import SceneParser
from llm import LLMClient

llm_client = LLMClient(api_key="your_key", dry_run=False)
parser = SceneParser(llm_client)

spec = parser.parse("simulate the signing of the declaration of independence")

# Result:
# spec.scene_title = "Signing of the Declaration of Independence"
# spec.temporal_scope = {
#     "start_date": "1776-07-04T09:00:00",
#     "end_date": "1776-07-04T17:00:00",
#     "location": "Philadelphia, Pennsylvania"
# }
# spec.entities = [
#     EntityRosterItem(
#         entity_id="john_hancock",
#         role="primary",
#         initial_knowledge=["continental_congress", "independence_movement", ...],
#         relationships={"benjamin_franklin": "ally", ...}
#     ),
#     ...
# ]
```

### 2. KnowledgeSeeder

**Purpose**: Create initial knowledge states and `ExposureEvent` records for causal provenance.

**How It Works**:
1. Reads `initial_knowledge` from entity specifications
2. Creates `ExposureEvent` records with:
   - `event_type`: "initial" (special marker for starting knowledge)
   - `information`: Each knowledge item
   - `source`: "scene_initialization"
   - `timestamp`: Before scene start (ensures causal validity)
   - `confidence`: 1.0 (initial knowledge is certain)

**Why This Matters**:
- Establishes causal audit trail (MECHANICS.md Mechanism 3)
- Enables validator checks: `entity.knowledge_state ⊆ exposure_events`
- Supports counterfactual reasoning (remove events, recompute forward)

**Example**:
```python
from orchestrator import KnowledgeSeeder
from storage import GraphStore

store = GraphStore("sqlite:///mydb.db")
seeder = KnowledgeSeeder(store)

exposure_events = seeder.seed_knowledge(spec, create_exposure_events=True)

# Result:
# exposure_events["james_madison"] = [
#     ExposureEvent(
#         entity_id="james_madison",
#         event_type="initial",
#         information="separation_of_powers",
#         source="scene_initialization",
#         timestamp="1787-05-24T23:59:59",  # Day before scene
#         confidence=1.0,
#         timepoint_id="pre_tp_001"
#     ),
#     ...
# ]
```

### 3. RelationshipExtractor

**Purpose**: Build NetworkX graph from entity relationships and co-presence patterns.

**Graph Construction**:
1. **Nodes**: All entities with attributes (type, role, description)
2. **Declared Edges**: From entity `relationships` dict
3. **Co-presence Edges**: Entities present at same timepoints
4. **Edge Weights**: Relationship-type based (ally=0.9, enemy=0.1, etc.)

**Example**:
```python
from orchestrator import RelationshipExtractor

extractor = RelationshipExtractor()
graph = extractor.build_graph(spec)

# Graph structure:
# Nodes: ["james_madison", "alexander_hamilton", "george_washington", ...]
# Edges: [
#     ("james_madison", "alexander_hamilton", {relationship: "ally", weight: 0.9}),
#     ("james_madison", "george_washington", {relationship: "mentor", weight: 0.85}),
#     ("madison", "hamilton", {relationship: "copresent", weight: 0.4}),  # Same timepoint
#     ...
# ]

# Use for centrality calculations
import networkx as nx
centrality = nx.eigenvector_centrality(graph)
# {'james_madison': 0.52, 'george_washington': 0.48, ...}
```

### 4. ResolutionAssigner

**Purpose**: Assign `ResolutionLevel` to entities based on role and centrality.

**Resolution Strategy**:
```
Role: primary + centrality > 0.5   → TRAINED    (50k tokens, full detail)
Role: primary + centrality ≤ 0.5   → DIALOG     (10k tokens, personality + knowledge)
Role: secondary + centrality > 0.3 → DIALOG
Role: secondary + centrality ≤ 0.3 → GRAPH      (5k tokens, relationships + facts)
Role: background                   → SCENE      (1-2k tokens, summary only)
Role: environment                  → TENSOR_ONLY (8-16 floats, compressed)
```

**Why This Matters**:
- **Performance**: Only high-importance entities get full LLM elaboration
- **Cost Control**: TRAINED entities are 10x more expensive than SCENE
- **Query-Driven**: Resolutions can be elevated later if entity is frequently accessed

**Example**:
```python
from orchestrator import ResolutionAssigner

assigner = ResolutionAssigner()
resolutions = assigner.assign_resolutions(spec, graph)

# Result:
# {
#     "james_madison": ResolutionLevel.TRAINED,      # Primary + high centrality
#     "alexander_hamilton": ResolutionLevel.DIALOG,  # Primary + medium centrality
#     "minor_delegate_1": ResolutionLevel.SCENE,     # Background
#     "pennsylvania_state_house": ResolutionLevel.TENSOR_ONLY  # Environment
# }
```

## Main Orchestrator

### OrchestratorAgent

The top-level coordinator that runs all four components in sequence and produces simulation-ready output.

**Usage**:
```python
from orchestrator import OrchestratorAgent
from llm import LLMClient
from storage import GraphStore

# Setup
llm_client = LLMClient(api_key="your_openrouter_key", dry_run=False)
store = GraphStore("sqlite:///simulation.db")

# Create orchestrator
orchestrator = OrchestratorAgent(llm_client, store)

# Orchestrate scene
result = orchestrator.orchestrate(
    "simulate the constitutional convention in the united states",
    context={
        "temporal_mode": "pearl",       # Optional: suggest temporal mode
        "max_entities": 10,             # Optional: limit entity count
        "max_timepoints": 5             # Optional: limit timepoint count
    },
    save_to_db=True  # Save entities, timepoints, exposure events to database
)

# Result contains:
# {
#     "specification": SceneSpecification,
#     "entities": List[Entity],                    # SQLModel entities, ready for workflows
#     "timepoints": List[Timepoint],               # Causal chain with parent links
#     "graph": nx.Graph,                           # Relationship graph
#     "exposure_events": Dict[str, List[ExposureEvent]],
#     "temporal_agent": TemporalAgent,             # Configured for scene's temporal mode
#     "resolution_assignments": Dict[str, ResolutionLevel]
# }
```

**Console Output Example**:
```
🎬 ORCHESTRATING SCENE: simulate the constitutional convention in the united states

📋 Step 1: Parsing scene specification...
   ✓ Title: Constitutional Convention 1787
   ✓ Temporal Mode: pearl
   ✓ Entities: 8
   ✓ Timepoints: 5

🌱 Step 2: Seeding initial knowledge...
   🌱 Seeded 24 knowledge items across 8 entities

🕸️  Step 3: Building relationship graph...
   🕸️  Built graph: 8 nodes, 14 edges

🎯 Step 4: Assigning resolution levels...
   🎯 Assigned resolutions: TRAINED=2, DIALOG=3, GRAPH=1, SCENE=1, TENSOR=1

👥 Step 5: Creating entity objects...
   ✓ Created 8 entity objects

⏰ Step 6: Creating timepoint objects...
   ✓ Created 5 timepoint objects

💾 Step 7: Saving to database...
   ✓ Saved 8 entities and 5 timepoints

🕐 Step 8: Creating temporal agent...
   ✓ Temporal agent created with mode: pearl

✅ ORCHESTRATION COMPLETE
```

## Convenience Function

### simulate_event()

Simplified one-liner for common use cases:

```python
from orchestrator import simulate_event
from llm import LLMClient
from storage import GraphStore

result = simulate_event(
    "simulate the boston tea party",
    LLMClient(api_key="key"),
    GraphStore("sqlite:///db.db"),
    context={"max_entities": 5},
    save_to_db=True
)
```

## Integration with Existing Workflows

The OrchestratorAgent produces output that's **immediately compatible** with existing Timepoint-Daedalus workflows:

### Integration Point 1: Entity Generation Workflow

```python
from workflows import create_entity_training_workflow
from orchestrator import simulate_event

# Generate scene specification
result = simulate_event("simulate a historical event", llm_client, store)

# Feed to existing entity training workflow
workflow = create_entity_training_workflow(llm_client, store)

# Entities are already created with initial knowledge and resolution levels
# The workflow can now elaborate them based on resolution targeting
for entity in result["entities"]:
    if entity.resolution_level in [ResolutionLevel.DIALOG, ResolutionLevel.TRAINED]:
        # Run LLM elaboration for high-resolution entities
        enriched = workflow.invoke({
            "entities": [entity],
            "graph": result["graph"],
            "timepoint": result["timepoints"][0].timepoint_id
        })
```

### Integration Point 2: Temporal Agent

```python
# The temporal agent is pre-configured with the scene's temporal mode
temporal_agent = result["temporal_agent"]

# Generate next timepoints in the sequence
current_tp = result["timepoints"][-1]
next_tp = temporal_agent.generate_next_timepoint(
    current_tp,
    context={"next_event": "Debate on representation begins"}
)
```

### Integration Point 3: Validation

```python
from validation import Validator

validator = Validator()

# Validate all entities (they have exposure events for knowledge provenance)
for entity in result["entities"]:
    context = {
        "exposure_history": store.get_exposure_events(entity.entity_id),
        "graph": result["graph"],
        "timepoint_id": entity.timepoint
    }
    validation_result = validator.validate_entity(entity, context)
    if not validation_result["valid"]:
        print(f"⚠️ Validation failed for {entity.entity_id}: {validation_result['violations']}")
```

## Temporal Modes

The OrchestratorAgent supports all five temporal modes from MECHANICS.md:

### 1. PEARL (Pearl Causality)
- **Description**: Standard forward causality, no anachronisms
- **Use Case**: Historical simulations, scientific accuracy
- **Validator Behavior**: Strict temporal consistency checks

### 2. DIRECTORIAL
- **Description**: Narrative structure with dramatic tension
- **Use Case**: Story-driven simulations, dramatic events
- **Temporal Agent**: Boosts probability of events that advance narrative arc

### 3. NONLINEAR
- **Description**: Presentation ≠ causality (flashbacks, foreshadowing)
- **Use Case**: Complex narratives, memory-based storytelling
- **Validator Behavior**: Checks causal order, not presentation order

### 4. BRANCHING
- **Description**: Many-worlds interpretation, parallel timelines
- **Use Case**: What-if scenarios, counterfactual reasoning
- **Temporal Agent**: Increases randomness in event probability

### 5. CYCLICAL
- **Description**: Time loops, prophecy, destiny
- **Use Case**: Mythological events, prophecy fulfillment
- **Validator Behavior**: Allows future knowledge if loop closes

## Configuration Options

### Context Parameters

Pass these in the `context` dict to `orchestrate()` or `simulate_event()`:

```python
context = {
    "temporal_mode": "pearl",        # Preferred temporal mode (LLM can override)
    "max_entities": 10,              # Limit entity count
    "max_timepoints": 5,             # Limit timepoint count
}
```

### Dry Run Mode

For testing without API calls:

```python
llm_client = LLMClient(api_key="test", dry_run=True)
# Uses mock data, no API costs
```

### Database Persistence

Control whether results are saved:

```python
result = orchestrator.orchestrate(
    event_description,
    save_to_db=False  # Don't persist to database
)
```

## Performance Characteristics

### API Costs (OpenRouter)

- **SceneParser**: ~4000 tokens per scene (~$0.02 with Llama 70B)
- **Total per scene**: Single LLM call
- **Dry run mode**: $0 (uses mock data)

### Time Complexity

- **Scene parsing**: O(1) LLM call
- **Knowledge seeding**: O(n×k) where n=entities, k=knowledge items per entity
- **Graph construction**: O(n²) worst case (all entities connected)
- **Resolution assignment**: O(n + e) where e=edges (centrality calculation)

### Storage

- **Entities**: ~1KB each (metadata)
- **Timepoints**: ~500 bytes each
- **ExposureEvents**: ~200 bytes each
- **Graph**: Stored as JSON in entity/timepoint metadata

## Error Handling

The OrchestratorAgent includes robust error handling:

### LLM Failures

- **Retry logic**: 3 retries with exponential backoff
- **Fallback**: Returns mock specification if all retries fail
- **Logging**: Detailed error messages with context

### Validation Failures

```python
try:
    result = orchestrator.orchestrate(event_description)
except Exception as e:
    print(f"Orchestration failed: {e}")
    # Fallback to manual specification
```

### Malformed LLM Output

- **JSON parsing**: Handles malformed JSON gracefully
- **Schema validation**: Pydantic validates all fields
- **Defaults**: Uses sensible defaults for missing fields

## Testing

### Unit Tests

Test individual components:

```bash
pytest test_orchestrator.py::TestSceneParser -v
pytest test_orchestrator.py::TestKnowledgeSeeder -v
pytest test_orchestrator.py::TestRelationshipExtractor -v
pytest test_orchestrator.py::TestResolutionAssigner -v
```

### Integration Tests

Test end-to-end orchestration:

```bash
# Dry run tests (no API calls)
pytest test_orchestrator.py::TestOrchestratorAgent -v

# Real LLM tests (requires OPENROUTER_API_KEY)
pytest test_orchestrator.py::TestEndToEnd -v --real-llm -s
```

### Demo Script

Run interactive demonstrations:

```bash
# All demos in dry run mode
python demo_orchestrator.py --dry-run

# Specific demo
python demo_orchestrator.py --dry-run --demo 1

# Real LLM with custom event
python demo_orchestrator.py --event "simulate the signing of the magna carta"
```

## Examples

### Example 1: Constitutional Convention

```python
result = simulate_event(
    "simulate the constitutional convention in the united states",
    llm_client,
    store
)

# Generates:
# - 8-12 entities (Madison, Hamilton, Washington, Franklin, ...)
# - 5-10 timepoints (opening, Virginia Plan, Great Compromise, signing, ...)
# - Relationship graph with ally/mentor/rival edges
# - Initial knowledge: separation_of_powers, federalist_principles, ...
# - Temporal mode: pearl (historical accuracy)
```

### Example 2: Science Fiction Scenario

```python
result = simulate_event(
    "simulate first contact with an alien civilization",
    llm_client,
    store,
    context={"temporal_mode": "branching", "max_entities": 6}
)

# Generates:
# - Mixed entity types: humans, alien diplomats, spacecraft (as entities)
# - Branching timepoints: different first contact outcomes
# - Temporal mode: branching (multiple parallel timelines)
```

### Example 3: Mythological Event

```python
result = simulate_event(
    "simulate the Oracle of Delphi receiving a prophecy",
    llm_client,
    store,
    context={"temporal_mode": "cyclical"}
)

# Generates:
# - Entities: Oracle, supplicants, gods (as abstract entities)
# - Temporal mode: cyclical (allows prophecy/future knowledge)
# - Validator: Permits knowledge from future if prophecy-related
```

## Future Enhancements

### Planned Features

1. **External Knowledge Integration**
   - Wikipedia API for historical fact seeding
   - Custom knowledge base connectors
   - Fact-checking against ground truth

2. **Multi-Scene Orchestration**
   - Generate connected scene sequences
   - Maintain entity continuity across scenes
   - Progressive knowledge accumulation

3. **Interactive Refinement**
   - User feedback loop: "Add Thomas Jefferson" → re-orchestrate
   - Entity importance adjustment
   - Timepoint sequence editing

4. **Performance Optimization**
   - Caching of LLM responses
   - Batch processing for multiple scenes
   - Async/parallel component execution

## Troubleshooting

### Issue: LLM returns malformed JSON

**Solution**: Parser includes retry logic and fallback to mock data. Check:
- API key is valid
- OpenRouter service is accessible
- Model supports structured output (Llama 70B+ recommended)

### Issue: Resolution assignments too low

**Solution**: Check graph centrality calculations. Entities need relationships to boost centrality:
```python
# Verify graph structure
print(f"Graph edges: {result['graph'].number_of_edges()}")
print(f"Centrality: {nx.eigenvector_centrality(result['graph'])}")
```

### Issue: Missing knowledge items

**Solution**: Check exposure events were created:
```python
events = store.get_exposure_events(entity_id)
print(f"Knowledge items: {[e.information for e in events]}")
```

## API Reference

### Classes

- **`OrchestratorAgent`**: Main coordinator
- **`SceneParser`**: Natural language → SceneSpecification
- **`KnowledgeSeeder`**: Initial knowledge → ExposureEvents
- **`RelationshipExtractor`**: Entity relationships → NetworkX graph
- **`ResolutionAssigner`**: Role-based resolution targeting

### Data Models

- **`SceneSpecification`**: Complete scene specification
- **`EntityRosterItem`**: Single entity in a scene
- **`TimepointSpec`**: Single timepoint specification

### Functions

- **`simulate_event()`**: Convenience function for common use case
- **`orchestrator.orchestrate()`**: Full orchestration pipeline

## References

- **MECHANICS.md**: Architectural vision and mechanisms
- **workflows.py**: Entity generation workflows
- **validation.py**: Validator framework
- **schemas.py**: SQLModel entity and timepoint schemas
- **test_e2e_autopilot.py**: End-to-end testing patterns

---

**Version**: 1.0.0
**Last Updated**: 2025-10-07
**Author**: Claude (Anthropic) via Claude Code
**License**: See project LICENSE
