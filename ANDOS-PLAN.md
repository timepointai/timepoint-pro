# ANDOS-PLAN.md: Acyclical Network Directed Orthogonal Synthesis

**Phase**: 10 - Architectural Redesign
**Status**: Design Phase
**Created**: October 24, 2025
**Goal**: Achieve 17/17 (100%) Mechanism Coverage

---

## Executive Summary

**Problem**: M14 (Circadian Patterns) and M15 (Entity Prospection) are blocked by a fundamental circular dependency - entities require trained TTM tensors before they can participate in dialog synthesis, but tensor training requires dialog data from other entities they interact with.

**Solution**: ANDOS (Acyclical Network Directed Orthogonal Synthesis) - a reverse topological ordering system that trains entities from graph periphery to core, analogous to crystal formation from seeds.

**Impact**: Requires full-stack redesign across workflows, orchestrator, test templates, ML generators, and export pipeline.

**Timeline**: 10-14 days across 7 implementation phases (Phase 10.1-10.7)

**Success Criterion**: 17/17 mechanisms verified (100% coverage), M14 and M15 fully operational

---

## 1. Problem Statement

### The Circular Dependency

```
Current Flow (BROKEN):
Entity A dialog synthesis → needs A's tensor
                          ↓
                     needs A's dialog
                          ↓
                  needs B/C tensors
                          ↓
                  needs B/C dialog
                          ↓
                  needs D/E tensors...
                          ↓
                     [INFINITE LOOP]
```

**Core Issue**: Every entity needs its tensor before dialog, but tensors require dialog context from connected entities.

### Real-World Example: detective_prospection Template

```
Sherlock Holmes (A) talks to Watson (B) and Lestrade (C)
Watson (B) talks to Mrs. Hudson (D) and Stamford (E)
Mrs. Hudson (D) talks to street vendors (F, G, H, I)
```

**Current Bug Manifestation**:
1. System tries to generate Holmes dialog first
2. Holmes has no tensor because Watson/Lestrade don't have tensors
3. Watson doesn't have tensor because Mrs. Hudson doesn't have tensor
4. Mrs. Hudson doesn't have tensor because street vendors haven't been trained yet
5. **Result**: `⚠️ Skipping sherlock_holmes in dialog synthesis - missing tensor data in metadata`

### Architectural Root Cause

The workflow assumes entities can be processed in **arbitrary order** or **query-driven order**, but tensor training creates a **strict dependency graph** that must be respected:

- Dialog synthesis (workflows.py:772-813) expects tensors to exist
- Tensor training (tensors.py:130-214) requires dialog as input
- No coordination between these two steps

**This is not a bug - it's a fundamental architectural gap.**

---

## 2. ANDOS Architecture

### Core Concept: Crystal Formation

Think of entity training as crystal growth from solution:
1. **Seeds** (periphery entities) form first with minimal dependencies
2. **Growth layers** progressively form toward the center
3. **Core entities** form last, with full context from all supporting layers

This is **orthogonal** to traditional backpropagation - it's a **synthesis order** problem, not a gradient flow problem.

### Reverse Topological Ordering

```
ANDOS Flow (CORRECT):

Step 1: Identify target entity (A) and max graph depth
Step 2: Build interaction graph G = (V, E)
Step 3: Compute entity degrees: distance d(v) from A

Training Order:
  Layer 3 (seeds, d=3): F, G, H, I
    → generate dialog (minimal context)
    → train tensors
    → mark ready for Layer 2

  Layer 2 (d=2): D, E
    → generate dialog (with F/G/H/I tensor context)
    → train tensors
    → mark ready for Layer 1

  Layer 1 (d=1): B, C
    → generate dialog (with D/E tensor context)
    → train tensors
    → mark ready for Layer 0

  Layer 0 (core, d=0): A
    → final dialog (with B/C tensor context)
    → train tensor
    → COMPLETE
```

### Mathematical Definition

Given:
- Entity graph `G = (V, E)` where V = entities, E = interactions
- Target entity `A ∈ V`
- Distance function `d(v) = shortest path length from v to A`

**ANDOS ordering**:
```python
Order = sorted(V, key=lambda v: -d(v))  # Descending distance (periphery to core)
```

For each entity `v` in `Order`:
1. **Context Gathering**: Collect tensors from entities at distance `d(v) + 1` (already trained)
2. **Dialog Generation**: Synthesize dialog with available context partners
3. **Tensor Training**: Train TTM tensor from dialog
4. **Readiness Marking**: Mark `v` as ready for entities at distance `d(v) - 1`

### Invariant Maintained by ANDOS

```python
# For all entities in layer k:
for entity in layer_k:
    for partner in entity.interaction_partners:
        # Partner must be in a later layer (higher distance)
        assert partner in flatten(layers[k+1:])
        # Partner must have tensor ready
        assert partner.entity_metadata["ttm_tensor"] is not None
```

This invariant **guarantees** no entity attempts dialog synthesis before its partners have trained tensors.

---

## 3. Full Stack Impact Assessment

### 3.1 Workflows (`workflows.py`)

**Current Issue**: Dialog synthesis (line 772-813) happens before tensor availability check

**Required Changes**:

```python
# NEW: Pre-synthesis dependency resolution
def resolve_entity_dependencies(
    entities: List[Entity],
    store: GraphStore
) -> List[List[Entity]]:
    """
    Return entities grouped by training layers (reverse topological order)

    Returns:
        List of entity lists, where:
        - layers[0] = periphery entities (seeds, max distance)
        - layers[-1] = core entity (target, distance 0)
    """
    # Step 1: Build interaction graph from entities
    graph = build_entity_interaction_graph(entities, store)

    # Step 2: Get target entity from context
    target_entity_id = store.context.get('target_entity', entities[0].entity_id)

    # Step 3: Compute distances from target via reverse BFS
    distances = compute_entity_distances(graph, target_entity_id)

    # Step 4: Group by distance (periphery to core)
    layers = group_by_distance(entities, distances)

    return layers  # [[F,G,H,I], [D,E], [B,C], [A]]


# NEW: Entity interaction graph builder
def build_entity_interaction_graph(
    entities: List[Entity],
    store: GraphStore
) -> nx.DiGraph:
    """Build directed graph from interaction_graph config"""
    import networkx as nx

    G = nx.DiGraph()

    # Get interaction graph from context
    interaction_config = store.context.get('interaction_graph', {})
    interactions = interaction_config.get('interactions', [])

    # Add edges for each interaction
    for interaction in interactions:
        source = interaction['from']
        targets = interaction['to'] if isinstance(interaction['to'], list) else [interaction['to']]
        for target in targets:
            G.add_edge(source, target)

    # If no explicit config, infer from entity list (sequential chain)
    if not interactions:
        for i in range(len(entities) - 1):
            G.add_edge(entities[i].entity_id, entities[i+1].entity_id)

    return G


# NEW: Distance computation via reverse BFS
def compute_entity_distances(
    graph: nx.DiGraph,
    target_entity_id: str
) -> Dict[str, int]:
    """Compute shortest path distance from each entity to target"""
    import networkx as nx

    # Reverse graph to compute "influence distance"
    G_reversed = graph.reverse()

    try:
        distances = nx.single_source_shortest_path_length(G_reversed, target_entity_id)
    except nx.NodeNotFound:
        # Target not in graph - use heuristic (all at distance 1)
        distances = {node: 1 for node in graph.nodes()}

    return distances


# NEW: Layer grouping
def group_by_distance(
    entities: List[Entity],
    distances: Dict[str, int]
) -> List[List[Entity]]:
    """Group entities by distance (periphery to core)"""

    max_distance = max(distances.values()) if distances else 0
    layers = [[] for _ in range(max_distance + 1)]

    entity_map = {e.entity_id: e for e in entities}

    for entity_id, distance in distances.items():
        if entity_id in entity_map:
            # Reverse: larger distance = earlier layer (periphery)
            layer_idx = max_distance - distance
            layers[layer_idx].append(entity_map[entity_id])

    # Add entities not in graph to periphery
    graphed_ids = set(distances.keys())
    ungraphed = [e for e in entities if e.entity_id not in graphed_ids]
    if ungraphed:
        layers[0].extend(ungraphed)

    # Remove empty layers
    layers = [layer for layer in layers if layer]

    return layers


# MODIFIED: generate_dialog_synthesis (existing function at line 645)
def generate_dialog_synthesis(
    entities: List[Entity],
    timepoint: Timepoint,
    llm: LLMClient,
    store: GraphStore,
    max_turns: int = 10
) -> Dict:
    """
    Generate multi-entity dialog with ANDOS dependency resolution

    ANDOS ensures entities train in correct order (periphery to core)
    so tensors are available before dialog synthesis.
    """
    from tracking import track_mechanism

    # ANDOS Step 1: Resolve dependencies
    training_layers = resolve_entity_dependencies(entities, store)

    print(f"\n🔷 ANDOS: Computed {len(training_layers)} training layers")
    for idx, layer in enumerate(training_layers):
        print(f"  Layer {idx}: {[e.entity_id for e in layer]}")

    # ANDOS Step 2: Train layer by layer
    all_dialogs = []

    for layer_idx, layer_entities in enumerate(training_layers):
        print(f"\n🔷 ANDOS Layer {layer_idx}: Training {len(layer_entities)} entities")

        for entity in layer_entities:
            # Get entities from previous layers (already have tensors)
            available_partners = get_trained_entities(training_layers[:layer_idx])

            # Generate dialog with partners that have tensors
            dialog_turns = synthesize_dialog_for_entity(
                entity,
                available_partners,
                timepoint,
                llm,
                store,
                max_turns
            )

            all_dialogs.extend(dialog_turns)

            # Train tensor from dialog
            from tensors import generate_ttm_tensor

            tensor = generate_ttm_tensor(
                entity=entity,
                dialog=dialog_turns,
                context=store.context
            )

            # Store tensor in metadata
            entity.entity_metadata['ttm_tensor'] = tensor
            entity.entity_metadata['andos_layer'] = layer_idx

            print(f"    ✓ {entity.entity_id} tensor trained (layer {layer_idx})")

        print(f"  ✓ Layer {layer_idx} complete: {[e.entity_id for e in layer_entities]}")

    print(f"\n✅ ANDOS: All {len(entities)} entities trained across {len(training_layers)} layers")

    return {
        'dialog_turns': all_dialogs,
        'andos_layers': len(training_layers),
        'entities_trained': len(entities)
    }


# NEW: Get entities with trained tensors
def get_trained_entities(layers: List[List[Entity]]) -> List[Entity]:
    """Flatten list of layers and return entities with tensors"""
    trained = []
    for layer in layers:
        for entity in layer:
            if entity.entity_metadata.get('ttm_tensor') is not None:
                trained.append(entity)
    return trained


# NEW: Dialog synthesis for single entity with context
def synthesize_dialog_for_entity(
    entity: Entity,
    available_partners: List[Entity],
    timepoint: Timepoint,
    llm: LLMClient,
    store: GraphStore,
    max_turns: int
) -> List[DialogTurn]:
    """
    Synthesize dialog for a single entity with available interaction partners

    Args:
        entity: Entity to generate dialog for
        available_partners: Entities with trained tensors (from previous ANDOS layers)
        timepoint: Current timepoint
        llm: LLM client
        store: Graph store
        max_turns: Max dialog turns

    Returns:
        List of dialog turns for this entity
    """
    # If no partners available (periphery entity), generate monologue/internal thought
    if not available_partners:
        return synthesize_monologue(entity, timepoint, llm, store)

    # Select interaction partners (entities in this entity's interaction graph)
    interaction_config = store.context.get('interaction_graph', {})
    interactions = interaction_config.get('interactions', [])

    # Find who this entity talks to
    entity_interactions = [
        i for i in interactions
        if i['from'] == entity.entity_id
    ]

    if not entity_interactions:
        return synthesize_monologue(entity, timepoint, llm, store)

    # Get partners this entity actually interacts with
    target_ids = []
    for interaction in entity_interactions:
        targets = interaction['to'] if isinstance(interaction['to'], list) else [interaction['to']]
        target_ids.extend(targets)

    partners = [p for p in available_partners if p.entity_id in target_ids]

    if not partners:
        return synthesize_monologue(entity, timepoint, llm, store)

    # Generate dialog with partners
    # Use existing dialog synthesis logic but with filtered partners
    participants = [entity] + partners

    # Build dialog context from tensors
    context_description = build_dialog_context_from_tensors(participants, timepoint)

    # Generate dialog via LLM
    from llm_v2 import generate_dialog

    dialog_data = generate_dialog(
        llm,
        participants=participants,
        timepoint=timepoint,
        context=context_description,
        max_turns=max_turns,
        store=store
    )

    return dialog_data.turns


# NEW: Monologue synthesis for periphery entities
def synthesize_monologue(
    entity: Entity,
    timepoint: Timepoint,
    llm: LLMClient,
    store: GraphStore
) -> List[DialogTurn]:
    """Generate internal monologue for periphery entities with no partners"""
    from schemas import DialogTurn

    prompt = f"""Generate internal thoughts/monologue for {entity.entity_id} at {timepoint.event_description}.

Entity: {entity.entity_id}
Context: {timepoint.event_description}
Time: {timepoint.timestamp}

Generate 2-3 brief internal thoughts this entity might have."""

    response = llm.query(prompt, temperature=0.8)

    # Parse response into dialog turns
    turns = [
        DialogTurn(
            speaker=entity.entity_id,
            content=response['content'],
            timestamp=timepoint.timestamp,
            emotional_tone=0.0,
            knowledge_references=[],
            confidence=0.7,
            physical_state_influence={}
        )
    ]

    return turns


# NEW: Context builder from tensors
def build_dialog_context_from_tensors(
    entities: List[Entity],
    timepoint: Timepoint
) -> str:
    """Build rich context description from entity TTM tensors"""

    context_parts = [f"Scene: {timepoint.event_description}"]
    context_parts.append(f"Time: {timepoint.timestamp}")
    context_parts.append("\nParticipants:")

    for entity in entities:
        tensor = entity.entity_metadata.get('ttm_tensor')
        if tensor:
            # Extract key info from tensor
            # (TTM tensor is msgpack-encoded, decode if needed)
            context_parts.append(f"  - {entity.entity_id}: [tensor context available]")
        else:
            context_parts.append(f"  - {entity.entity_id}: [basic profile]")

    return "\n".join(context_parts)
```

**Key Files to Modify**:
- `workflows.py:645-813` - Replace `generate_dialog_synthesis()` with ANDOS version
- `workflows.py` - Add 9 new helper functions (~300 lines total)

**Testing Strategy**:
- Unit tests for each new function (test_andos_workflows.py)
- Integration test with 3-layer scenario
- Verify tensors exist before dialog at each layer

---

### 3.2 Orchestrator (`orchestrator.py`)

**Current Issue**: No awareness of entity dependencies or training order

**Required Changes**:

```python
# orchestrator.py - NEW Step 3.5: ANDOS Dependency Resolution

async def _run_simulation(self, state: dict) -> dict:
    """Main simulation workflow with ANDOS integration"""

    # ... existing steps 1-3 (entity creation, resolution assignment, etc.) ...

    # NEW: Step 3.5 - ANDOS: Compute entity dependency graph
    print("\n📊 Step 3.5: ANDOS - Computing entity dependency graph")

    entities = state.get("entities", [])
    context = state.get("context", {})

    # Get target entity from context
    target_entity_id = context.get("target_entity")

    if not target_entity_id and entities:
        target_entity_id = entities[0].entity_id
        context["target_entity"] = target_entity_id

    # Build interaction graph from entity metadata
    interaction_graph = self._build_interaction_graph(entities, context)

    # Compute reverse topological order (ANDOS layers)
    training_layers = self._compute_andos_layers(
        interaction_graph,
        target_entity_id,
        entities
    )

    # Store in state for dialog synthesis
    state["andos_layers"] = training_layers
    state["andos_target"] = target_entity_id

    print(f"✓ ANDOS computed {len(training_layers)} training layers")
    for idx, layer in enumerate(training_layers):
        entity_ids = [e.entity_id for e in layer]
        print(f"  Layer {idx} ({len(layer)} entities): {entity_ids}")

    # Store ANDOS metadata for tracking
    from tracking import track_mechanism
    track_mechanism(
        mechanism_id="M18",
        mechanism_name="ANDOS",
        metadata={
            "num_layers": len(training_layers),
            "target_entity": target_entity_id,
            "total_entities": len(entities)
        },
        store=self.store
    )

    # ... continue with steps 4+ (dialog synthesis now uses andos_layers) ...

    return state


def _build_interaction_graph(
    self,
    entities: List[Entity],
    context: Dict
) -> nx.DiGraph:
    """Build directed graph from interaction_graph config"""
    import networkx as nx

    G = nx.DiGraph()

    # Get interaction graph from context
    interaction_config = context.get('interaction_graph', {})
    interactions = interaction_config.get('interactions', [])

    # Add edges for each interaction
    for interaction in interactions:
        source = interaction['from']
        targets = interaction['to'] if isinstance(interaction['to'], list) else [interaction['to']]
        for target in targets:
            G.add_edge(source, target)

    # If no explicit config, infer from entity list
    if not interactions:
        print("  ⚠️  No interaction_graph in context, inferring sequential chain")
        for i in range(len(entities) - 1):
            G.add_edge(entities[i].entity_id, entities[i+1].entity_id)

    # Validate graph is acyclic
    if not nx.is_directed_acyclic_graph(G):
        cycles = list(nx.simple_cycles(G))
        raise ValueError(f"Interaction graph contains cycles: {cycles}")

    return G


def _compute_andos_layers(
    self,
    graph: nx.DiGraph,
    target_entity_id: str,
    entities: List[Entity]
) -> List[List[Entity]]:
    """Compute ANDOS training layers via reverse topological sort"""
    import networkx as nx

    # Reverse graph to compute "influence distance"
    G_reversed = graph.reverse()

    try:
        distances = nx.single_source_shortest_path_length(G_reversed, target_entity_id)
    except nx.NodeNotFound:
        print(f"  ⚠️  Target entity {target_entity_id} not in graph, using heuristic")
        distances = {entity.entity_id: 1 for entity in entities}

    # Group entities by distance (periphery to core)
    max_distance = max(distances.values()) if distances else 0
    layers = [[] for _ in range(max_distance + 1)]

    entity_map = {e.entity_id: e for e in entities}

    for entity_id, distance in distances.items():
        if entity_id in entity_map:
            # Reverse: larger distance = earlier layer (periphery)
            layer_idx = max_distance - distance
            layers[layer_idx].append(entity_map[entity_id])

    # Add entities not in graph to periphery (seeds)
    graphed_ids = set(distances.keys())
    ungraphed = [e for e in entities if e.entity_id not in graphed_ids]
    if ungraphed:
        print(f"  ℹ️  {len(ungraphed)} entities not in graph, adding to periphery")
        layers[0].extend(ungraphed)

    # Remove empty layers
    layers = [layer for layer in layers if layer]

    return layers
```

**Key Changes**:
- Add Step 3.5 between entity creation and dialog synthesis
- Add 2 new methods: `_build_interaction_graph()`, `_compute_andos_layers()`
- Pass `state["andos_layers"]` to dialog synthesis
- Add M18 (ANDOS) mechanism tracking

**Lines Modified**:
- Insert Step 3.5 around line 1100 (after Step 3, before Step 4)
- Add new methods (~80 lines total)

---

### 3.3 Test Templates (`generation/config_schema.py`)

**Current Issue**: Templates don't specify entity interaction graphs explicitly

**Required Additions**:

```python
# Each template needs new "interaction_graph" field

detective_prospection = {
    "scenario": "Sherlock Holmes investigates a case with Watson and Lestrade...",
    "entities": [
        {"id": "sherlock_holmes", "type": "human", ...},
        {"id": "watson", "type": "human", ...},
        {"id": "lestrade", "type": "human", ...},
        {"id": "mrs_hudson", "type": "human", ...},
        {"id": "stamford", "type": "human", ...},
        {"id": "street_vendor_1", "type": "human", ...},
        {"id": "street_vendor_2", "type": "human", ...},
    ],

    # NEW: Explicit interaction graph for ANDOS
    "interaction_graph": {
        "target_entity": "sherlock_holmes",  # Core entity (distance 0)
        "interactions": [
            {
                "from": "sherlock_holmes",
                "to": ["watson", "lestrade"],
                "layer": 1  # Optional metadata
            },
            {
                "from": "watson",
                "to": ["mrs_hudson", "stamford"],
                "layer": 2
            },
            {
                "from": "lestrade",
                "to": ["constable_jones"],
                "layer": 2
            },
            {
                "from": "mrs_hudson",
                "to": ["street_vendor_1", "street_vendor_2"],
                "layer": 3
            },
        ],
        "max_depth": 3
    },

    # ... rest of config (prospection_config, cognitive_traits, etc.) ...
}


# Board meeting example (simpler structure)
board_meeting = {
    "scenario": "CEO and board discuss acquisition...",
    "entities": [...],

    "interaction_graph": {
        "target_entity": "ceo",
        "interactions": [
            {
                "from": "ceo",
                "to": ["cfo", "cto", "board_chair"],
                "layer": 1
            },
            {
                "from": "cfo",
                "to": ["analyst_1"],
                "layer": 2
            },
            {
                "from": "cto",
                "to": ["analyst_2"],
                "layer": 2
            }
        ],
        "max_depth": 2
    }
}


# Simple scenario (no graph needed - all interact)
jefferson_dinner = {
    "scenario": "Jefferson hosts Madison and Hamilton...",
    "entities": [
        {"id": "jefferson", ...},
        {"id": "madison", ...},
        {"id": "hamilton", ...}
    ],

    # For small groups, fully connected graph
    "interaction_graph": {
        "target_entity": "jefferson",
        "interactions": [
            {"from": "jefferson", "to": ["madison", "hamilton"]},
            {"from": "madison", "to": ["hamilton"]},
            {"from": "hamilton", "to": ["madison"]}
        ],
        "max_depth": 1
    }
}
```

**Validation Schema Update**:

```python
# Add to ConfigValidationSchema

class InteractionGraphSchema(BaseModel):
    target_entity: str
    interactions: List[Dict[str, Any]]
    max_depth: Optional[int] = None

class ConfigValidationSchema(BaseModel):
    scenario: str
    entities: List[Dict[str, Any]]
    interaction_graph: InteractionGraphSchema  # NEW REQUIRED FIELD
    # ... rest of schema ...
```

**Template Update Plan**:
- Update all 17 templates in config_schema.py
- Add `interaction_graph` field to each
- Validate graphs are acyclic (DAG check)
- Add inference function for legacy templates without graphs

---

### 3.4 ML Data Generators (`generation/horizontal_generator.py`, `generation/vertical_generator.py`)

**Current Issue**: Generators produce training data without ANDOS awareness

**Required Changes**:

```python
# horizontal_generator.py

class HorizontalGenerator:
    def generate_variations(self, base_scenario: str, num_variations: int):
        """Generate scenario variations with ANDOS compatibility"""

        for i in range(num_variations):
            # Generate config via NL interface
            config = self.nl_generator.generate_config(scenario)

            # NEW: Ensure interaction_graph is present
            if "interaction_graph" not in config:
                print(f"  ⚠️  Variation {i}: No interaction_graph, inferring...")
                config = self._infer_interaction_graph(config)

            # Validate ANDOS compatibility
            self._validate_andos_structure(config)

            # Run simulation with ANDOS
            result = simulate_event(
                config["scenario"],
                self.llm,
                self.store,
                context=config,
                save_to_db=True
            )

            # Export with ANDOS metadata
            self._export_with_andos_metadata(result, config)


    def _infer_interaction_graph(self, config: Dict) -> Dict:
        """Infer interaction graph for configs without explicit graph"""
        entities = config["entities"]
        num_entities = len(entities)

        if num_entities <= 3:
            # Fully connected small graph
            target = entities[0]["id"]
            interactions = [
                {
                    "from": entities[i]["id"],
                    "to": [e["id"] for e in entities if e["id"] != entities[i]["id"]]
                }
                for i in range(num_entities)
            ]
            graph = {
                "target_entity": target,
                "interactions": interactions,
                "max_depth": 1
            }
        else:
            # Sequential chain for larger groups
            target = entities[0]["id"]
            interactions = [
                {"from": entities[i]["id"], "to": [entities[i+1]["id"]]}
                for i in range(num_entities - 1)
            ]
            graph = {
                "target_entity": target,
                "interactions": interactions,
                "max_depth": num_entities - 1
            }

        config["interaction_graph"] = graph
        return config


    def _validate_andos_structure(self, config: Dict):
        """Validate config has valid ANDOS structure"""
        import networkx as nx

        graph_config = config.get("interaction_graph")
        if not graph_config:
            raise ValueError("Config missing interaction_graph")

        # Build graph
        G = nx.DiGraph()
        for interaction in graph_config["interactions"]:
            source = interaction["from"]
            targets = interaction["to"] if isinstance(interaction["to"], list) else [interaction["to"]]
            for target in targets:
                G.add_edge(source, target)

        # Check DAG property
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            raise ValueError(f"Interaction graph contains cycles: {cycles}")

        print(f"  ✓ ANDOS structure valid ({len(G.nodes)} nodes, {len(G.edges)} edges)")


    def _export_with_andos_metadata(self, result: Dict, config: Dict):
        """Export result with ANDOS layer metadata"""
        # Extract ANDOS metadata
        andos_layers = result.get("andos_layers", [])

        # Add to export
        export_data = {
            "result": result,
            "config": config,
            "andos_metadata": {
                "num_layers": len(andos_layers),
                "target_entity": config["interaction_graph"]["target_entity"],
                "max_depth": config["interaction_graph"]["max_depth"]
            }
        }

        # Write to file
        self._write_export(export_data)
```

**Key Changes**:
- Add `_infer_interaction_graph()` for backward compatibility
- Add `_validate_andos_structure()` to check DAG property
- Add `_export_with_andos_metadata()` to include ANDOS info in training data

---

### 3.5 Oxen/Export Pipeline (`reporting/export_pipeline.py`)

**Current Issue**: Exports don't capture ANDOS structure for training data

**Required Changes**:

```python
# Add ANDOS metadata to exports

class ExportPipeline:
    def export_report(
        self,
        world_id: str,
        report_type: str,
        export_format: str,
        output_path: str
    ):
        """Export report with ANDOS metadata"""

        # ... existing export logic ...

        # NEW: Include ANDOS metadata
        andos_metadata = self._extract_andos_metadata(world_id)

        if export_format == "json":
            data["andos_structure"] = {
                "training_layers": andos_metadata["layers"],
                "entity_distances": andos_metadata["distances"],
                "dependency_graph": andos_metadata["graph"]
            }

        # For ML training data (JSONL), include layer info per entity
        if export_format == "jsonl":
            for entity_data in data["entities"]:
                entity_id = entity_data["id"]
                entity_data["andos_layer"] = andos_metadata["entity_layers"].get(entity_id)
                entity_data["andos_distance"] = andos_metadata["distances"].get(entity_id)

        # Write to file
        self._write_export(data, output_path, export_format)


    def _extract_andos_metadata(self, world_id: str) -> Dict:
        """Extract ANDOS structure from simulation"""

        # Query mechanism tracking for M18 (ANDOS)
        andos_runs = self.query_engine.get_mechanism_runs("M18", world_id)

        if not andos_runs:
            return {
                "layers": [],
                "distances": {},
                "graph": {},
                "entity_layers": {}
            }

        # Get latest ANDOS run
        latest_run = andos_runs[0]
        metadata = latest_run.metadata

        # Extract layer assignments
        entity_layers = {}
        for entity in self.query_engine.get_entities(world_id):
            layer = entity.entity_metadata.get("andos_layer")
            if layer is not None:
                entity_layers[entity.entity_id] = layer

        return {
            "layers": metadata.get("num_layers", 0),
            "distances": metadata.get("distances", {}),
            "graph": metadata.get("graph", {}),
            "entity_layers": entity_layers
        }
```

**New Export Fields**:
- `andos_structure.training_layers` - Number of layers
- `andos_structure.entity_distances` - Distance map from target
- `andos_structure.dependency_graph` - Adjacency list
- Per-entity `andos_layer` field in JSONL training data

---

## 4. TTM Tensor Integration

### How TTM Fits ANDOS

From MECHANICS.md, M6 (TTM Tensor Model) compresses entity state into three components:
- **Context** (location, time, social setting) → ~1000 tokens
- **Biology** (age, health, energy) → ~100 tokens
- **Behavior** (recent actions, goals) → ~500 tokens

**Total**: ~1600 tokens vs 50k (97% compression)

### ANDOS Enhancement

TTM tensors now serve as **dependency signals** between layers:

```python
# Layer N entities train tensors (periphery)
layer_n_tensors = []
for entity in layer_n:
    dialog = synthesize_dialog(entity, context=minimal)
    tensor = train_ttm(entity, dialog)
    layer_n_tensors.append(tensor)

# Layer N-1 entities use those tensors as rich context
for entity in layer_n_minus_1:
    # Get tensors from entities this one interacts with (layer N)
    context_tensors = [
        t for t in layer_n_tensors
        if interacts_with(entity, t.entity)
    ]

    # Generate dialog with tensor-based context
    dialog = synthesize_dialog(
        entity,
        context_tensors=context_tensors  # Rich compressed context
    )

    # Train this entity's tensor
    entity_tensor = train_ttm(entity, dialog)
```

### Tensor Availability Guarantees

**Before ANDOS**: No guarantee tensors exist before dialog
**After ANDOS**: Mathematical guarantee via topological sort

```python
# Invariant maintained by ANDOS
for entity in layer_k:
    for partner in entity.interaction_partners:
        # Partner must be in later layer
        assert partner in flatten(layers[k+1:])

        # Partner must have tensor ready
        assert partner.entity_metadata["ttm_tensor"] is not None

        # Tensor must be valid TTMTensor object
        assert isinstance(partner.entity_metadata["ttm_tensor"], TTMTensor)
```

### M14 Integration (Circadian Patterns)

With ANDOS, M14 can now access tensors reliably:

```python
# M14: Apply circadian energy adjustment during dialog synthesis
def generate_dialog_synthesis(...):
    # ... ANDOS layer training ...

    for entity in layer_entities:
        # Get physical tensor (guaranteed to exist via ANDOS)
        physical = entity.entity_metadata.get("physical_tensor")

        if physical:
            # M14: Adjust energy based on time of day
            hour = timepoint.timestamp.hour
            base_energy = physical.stamina

            adjusted_energy = compute_energy_cost_with_circadian(
                activity="conversation",
                hour=hour,
                base_cost=base_energy,
                circadian_config=store.context.get("circadian_config", {})
            )

            # Use adjusted energy in dialog generation
            physical.stamina = adjusted_energy
```

### M15 Integration (Entity Prospection)

With ANDOS, M15 can model future states with tensor context:

```python
# M15: Generate prospective state with partner tensors
def generate_prospective_state(entity, timepoint, llm, store):
    # Get interaction partners from ANDOS graph
    partners = get_entity_partners(entity, store)

    # Collect partner tensors (guaranteed to exist via ANDOS)
    partner_tensors = [
        p.entity_metadata.get("ttm_tensor")
        for p in partners
        if p.entity_metadata.get("ttm_tensor") is not None
    ]

    # Generate prospective state with rich context
    prospection = llm.query(
        f"Model future state for {entity.entity_id} given partners: {partner_tensors}",
        temperature=0.7
    )

    return prospection
```

---

## 5. Graph Algorithm Details

### Algorithm: ANDOS Layer Computation

```python
import networkx as nx
from typing import List, Dict, Tuple

def compute_andos_layers(
    entities: List[Entity],
    target_entity_id: str,
    interaction_graph: Dict
) -> List[List[Entity]]:
    """
    Compute reverse topological ordering for entity training

    Args:
        entities: List of all entities in simulation
        target_entity_id: Core entity (distance 0)
        interaction_graph: Dict with 'interactions' list

    Returns:
        List of entity lists, where:
        - layers[0] = periphery (seeds, max distance)
        - layers[-1] = core (target, distance 0)

    Raises:
        ValueError: If graph contains cycles
    """

    # Step 1: Build directed graph
    G = nx.DiGraph()

    for interaction in interaction_graph["interactions"]:
        source = interaction["from"]
        targets = interaction["to"] if isinstance(interaction["to"], list) else [interaction["to"]]
        for target in targets:
            G.add_edge(source, target)  # source talks to target

    # Step 2: Verify DAG (no cycles)
    if not nx.is_directed_acyclic_graph(G):
        cycles = list(nx.simple_cycles(G))
        raise ValueError(
            f"Interaction graph contains cycles - cannot compute ANDOS ordering. "
            f"Cycles found: {cycles}"
        )

    # Step 3: Compute distances from target entity
    # Reverse graph to compute "influence distance"
    G_reversed = G.reverse()

    try:
        distances = nx.single_source_shortest_path_length(G_reversed, target_entity_id)
    except nx.NodeNotFound:
        # Target not in graph - use heuristic (all entities at distance 1)
        print(f"WARNING: Target entity '{target_entity_id}' not found in graph")
        distances = {entity.entity_id: 1 for entity in entities}

    # Step 4: Group entities by distance (periphery to core)
    max_distance = max(distances.values()) if distances else 0
    layers = [[] for _ in range(max_distance + 1)]

    entity_map = {e.entity_id: e for e in entities}

    for entity_id, distance in distances.items():
        if entity_id in entity_map:
            # Reverse: larger distance = earlier layer (periphery)
            layer_idx = max_distance - distance
            layers[layer_idx].append(entity_map[entity_id])

    # Step 5: Handle entities not in graph (add to periphery)
    graphed_ids = set(distances.keys())
    ungraphed = [e for e in entities if e.entity_id not in graphed_ids]

    if ungraphed:
        print(f"INFO: {len(ungraphed)} entities not in graph, adding to periphery layer")
        layers[0].extend(ungraphed)  # Add to periphery (seeds)

    # Step 6: Remove empty layers
    layers = [layer for layer in layers if layer]

    return layers


def validate_andos_layers(
    layers: List[List[Entity]],
    interaction_graph: Dict
) -> Tuple[bool, List[str]]:
    """
    Validate ANDOS layers satisfy dependency constraints

    Returns:
        (is_valid, list_of_violations)
    """
    violations = []

    # Build entity -> layer index map
    entity_layer_map = {}
    for layer_idx, layer in enumerate(layers):
        for entity in layer:
            entity_layer_map[entity.entity_id] = layer_idx

    # Check each interaction
    for interaction in interaction_graph["interactions"]:
        source = interaction["from"]
        targets = interaction["to"] if isinstance(interaction["to"], list) else [interaction["to"]]

        source_layer = entity_layer_map.get(source)

        for target in targets:
            target_layer = entity_layer_map.get(target)

            # Source should be in earlier layer than target (lower index)
            if source_layer is not None and target_layer is not None:
                if source_layer >= target_layer:
                    violations.append(
                        f"{source} (layer {source_layer}) should be after "
                        f"{target} (layer {target_layer})"
                    )

    return (len(violations) == 0, violations)
```

### Handling Edge Cases

**Disconnected Components**:
```python
# If graph has multiple components, process each separately
components = list(nx.weakly_connected_components(G))

if len(components) > 1:
    print(f"WARNING: Graph has {len(components)} disconnected components")

    # Process each component independently
    all_layers = []
    for component in components:
        component_entities = [e for e in entities if e.entity_id in component]
        component_layers = compute_andos_layers(
            component_entities,
            target_entity_id=list(component)[0],  # Use first as target
            interaction_graph=subgraph_config
        )
        all_layers.extend(component_layers)
```

**Cycles Detection**:
```python
# Before ANDOS computation, check for cycles
if not nx.is_directed_acyclic_graph(G):
    cycles = list(nx.simple_cycles(G))

    # Format error message with cycle paths
    cycle_paths = []
    for cycle in cycles:
        path = " → ".join(cycle + [cycle[0]])
        cycle_paths.append(path)

    raise ValueError(
        f"Interaction graph contains {len(cycles)} cycle(s):\n" +
        "\n".join(f"  - {path}" for path in cycle_paths) +
        "\n\nANDOS requires acyclic graph. Please fix template configuration."
    )
```

**Single Entity**:
```python
# Single entity scenarios (monologues)
if len(entities) == 1:
    return [[entities[0]]]  # Single layer, no dependencies
```

---

## 6. Implementation Phases

### Phase 10.1: Graph Infrastructure (1-2 days)
**Goal**: Build ANDOS algorithm without integration

**Tasks**:
1. Create `andos/` module directory
2. Implement `layer_computer.py` with `compute_andos_layers()`
3. Add NetworkX graph builder from interaction configs
4. Write comprehensive unit tests (test_andos_layer_computation.py)
5. Test with detective_prospection graph structure
6. Add cycle detection and validation
7. Handle edge cases (disconnected components, single entity)

**Deliverables**:
- `andos/layer_computer.py` (~200-300 lines)
- `test_andos_layer_computation.py` (10+ test cases)
- Documentation in MECHANICS.md for M18 (ANDOS)

**Success Criteria**:
- All unit tests passing
- Handles 3-layer detective_prospection graph correctly
- Cycle detection working
- Edge cases covered

---

### Phase 10.2: Workflow Integration (2-3 days)
**Goal**: Make workflows.py ANDOS-aware

**Tasks**:
1. Add `resolve_entity_dependencies()` to workflows.py
2. Add helper functions:
   - `build_entity_interaction_graph()`
   - `compute_entity_distances()`
   - `group_by_distance()`
   - `get_trained_entities()`
   - `synthesize_dialog_for_entity()`
   - `synthesize_monologue()`
   - `build_dialog_context_from_tensors()`
3. Modify `generate_dialog_synthesis()` for layer-by-layer training
4. Update tensor training to use layer context
5. Add ANDOS tracking decorator (@track_mechanism M18)
6. Write integration tests (test_andos_workflows.py)

**Deliverables**:
- Updated `workflows.py` (~300 new lines)
- `test_andos_workflows.py` (integration tests)
- M18 mechanism tracking verified

**Success Criteria**:
- Entities train in correct layer order
- Tensors available before dialog synthesis
- M18 tracked in metadata/runs.db
- No "missing tensor" warnings

---

### Phase 10.3: Orchestrator Integration (2 days)
**Goal**: Add ANDOS to orchestrator.py

**Tasks**:
1. Add Step 3.5: ANDOS dependency resolution to `_run_simulation()`
2. Implement `_build_interaction_graph()` method
3. Implement `_compute_andos_layers()` method
4. Pass `state["andos_layers"]` to dialog synthesis
5. Update progress logging to show layer progress
6. Add error handling for cycle detection
7. Test with detective_prospection template

**Deliverables**:
- Updated `orchestrator.py` (Step 3.5 + 2 new methods, ~80 lines)
- E2E test showing ANDOS layers in logs
- detective_prospection runs without errors

**Success Criteria**:
- Step 3.5 executes correctly
- ANDOS layers computed and passed to workflows
- detective_prospection template completes successfully
- Logs show layer-by-layer training progress

---

### Phase 10.4: Template Updates (1-2 days)
**Goal**: Add `interaction_graph` to all templates

**Tasks**:
1. Add `interaction_graph` schema to `ConfigValidationSchema`
2. Update all 17 templates in config_schema.py:
   - jefferson_dinner
   - board_meeting
   - hospital_crisis
   - kami_shrine
   - detective_prospection
   - paul_revere_ride
   - constitutional_convention
   - apollo_13_crisis
   - versailles_treaty
   - stock_market_crash
   - battle_of_midway
   - jury_deliberation
   - restaurant_service
   - classroom_debate
   - emergency_room
   - family_reunion
   - startup_pitch
3. Add `_infer_interaction_graph()` helper for legacy templates
4. Validate all templates pass DAG check
5. Write template validation tests

**Deliverables**:
- 17 templates with `interaction_graph` field
- `_infer_interaction_graph()` helper function
- Validation tests for all templates

**Success Criteria**:
- All templates have valid interaction graphs
- All templates pass DAG validation
- Inference function works for simple cases

---

### Phase 10.5: ML Generator Updates (1 day)
**Goal**: Make generators ANDOS-aware

**Tasks**:
1. Update `horizontal_generator.py`:
   - Add `_infer_interaction_graph()` method
   - Add `_validate_andos_structure()` method
   - Add `_export_with_andos_metadata()` method
2. Update `vertical_generator.py`:
   - Add ANDOS validation before simulation run
   - Include ANDOS metadata in deep simulations
3. Test with finetune workflows (run_real_finetune.py)
4. Verify ANDOS metadata in exported training data

**Deliverables**:
- Updated `horizontal_generator.py` (~100 new lines)
- Updated `vertical_generator.py` (~50 new lines)
- Test run showing ANDOS metadata in logs

**Success Criteria**:
- Generators infer graphs when missing
- Generators validate ANDOS structure
- Training data includes ANDOS metadata
- No runtime errors during generation

---

### Phase 10.6: Export Pipeline Updates (1 day)
**Goal**: Include ANDOS metadata in exports

**Tasks**:
1. Add `_extract_andos_metadata()` to `ExportPipeline`
2. Include ANDOS structure in JSON exports:
   - `andos_structure.training_layers`
   - `andos_structure.entity_distances`
   - `andos_structure.dependency_graph`
3. Add per-entity `andos_layer` field in JSONL exports
4. Add ANDOS section to Markdown reports
5. Test exports contain complete ANDOS data

**Deliverables**:
- Updated `export_pipeline.py` (~80 new lines)
- Sample exports showing ANDOS structure
- Updated report templates with ANDOS section

**Success Criteria**:
- JSON exports include `andos_structure`
- JSONL exports include `andos_layer` per entity
- Markdown reports show layer information
- All export formats work correctly

---

### Phase 10.7: Full E2E Testing (2-3 days)
**Goal**: Verify ANDOS works end-to-end and unblocks M14/M15

**Tasks**:
1. Run detective_prospection with ANDOS
2. Verify M14 (Circadian Patterns) now fires correctly
3. Verify M15 (Entity Prospection) now fires correctly
4. Run all 17 templates, check ANDOS success
5. Verify mechanism coverage: 17/17 persistent ✅
6. Update all documentation:
   - README.md - Update status to 17/17
   - MECHANICS.md - Add M18 (ANDOS) section
   - PLAN.md - Mark Phase 10 complete
7. Write comprehensive test suite (test_andos_e2e.py)
8. Generate PHASE_10_SUMMARY.md report

**Deliverables**:
- `test_andos_e2e.py` (comprehensive E2E tests)
- Updated documentation (3 core docs)
- PHASE_10_SUMMARY.md report
- Mechanism coverage: **17/17 (100%)** ✅

**Success Criteria**:
- detective_prospection runs without "missing tensor" warnings
- M14 tracked in metadata/runs.db (circadian adjustments applied)
- M15 tracked in metadata/runs.db (prospection generated)
- All 17 templates run successfully with ANDOS
- **Mechanism coverage: 17/17 persistent (100%)**
- All tests passing (>95% reliability)
- Documentation accurate and complete

---

## 7. Testing Strategy

### Unit Tests (test_andos_layer_computation.py)

```python
import pytest
from andos.layer_computer import compute_andos_layers
from schemas import Entity

def make_entity(entity_id: str) -> Entity:
    """Helper to create test entity"""
    return Entity(entity_id=entity_id, entity_type="human")

def test_simple_chain():
    """A → B → C should give layers [[C], [B], [A]]"""
    entities = [make_entity("A"), make_entity("B"), make_entity("C")]
    graph = {
        "interactions": [
            {"from": "A", "to": ["B"]},
            {"from": "B", "to": ["C"]}
        ]
    }

    layers = compute_andos_layers(entities, "A", graph)

    assert len(layers) == 3
    assert [e.entity_id for e in layers[0]] == ["C"]  # Periphery (seed)
    assert [e.entity_id for e in layers[1]] == ["B"]
    assert [e.entity_id for e in layers[2]] == ["A"]  # Core (target)

def test_branching():
    """A → B,C; B → D; C → E should give [[D,E], [B,C], [A]]"""
    entities = [
        make_entity("A"), make_entity("B"), make_entity("C"),
        make_entity("D"), make_entity("E")
    ]
    graph = {
        "interactions": [
            {"from": "A", "to": ["B", "C"]},
            {"from": "B", "to": ["D"]},
            {"from": "C", "to": ["E"]}
        ]
    }

    layers = compute_andos_layers(entities, "A", graph)

    assert len(layers) == 3
    assert set(e.entity_id for e in layers[0]) == {"D", "E"}  # Periphery
    assert set(e.entity_id for e in layers[1]) == {"B", "C"}
    assert set(e.entity_id for e in layers[2]) == {"A"}  # Core

def test_cycle_detection():
    """A → B → C → A should raise ValueError"""
    entities = [make_entity("A"), make_entity("B"), make_entity("C")]
    graph = {
        "interactions": [
            {"from": "A", "to": ["B"]},
            {"from": "B", "to": ["C"]},
            {"from": "C", "to": ["A"]}  # Creates cycle
        ]
    }

    with pytest.raises(ValueError, match="contains cycles"):
        compute_andos_layers(entities, "A", graph)

def test_disconnected_entity():
    """Entity not in graph should be added to periphery"""
    entities = [
        make_entity("A"), make_entity("B"), make_entity("C"), make_entity("orphan")
    ]
    graph = {
        "interactions": [
            {"from": "A", "to": ["B"]},
            {"from": "B", "to": ["C"]}
        ]
    }

    layers = compute_andos_layers(entities, "A", graph)

    # Orphan should be in periphery layer
    periphery_ids = [e.entity_id for e in layers[0]]
    assert "orphan" in periphery_ids
    assert "C" in periphery_ids

def test_single_entity():
    """Single entity should create single layer"""
    entities = [make_entity("A")]
    graph = {"interactions": []}

    layers = compute_andos_layers(entities, "A", graph)

    assert len(layers) == 1
    assert layers[0][0].entity_id == "A"

def test_detective_prospection_structure():
    """Test real detective_prospection template structure"""
    entities = [
        make_entity("sherlock_holmes"),
        make_entity("watson"),
        make_entity("lestrade"),
        make_entity("mrs_hudson"),
        make_entity("stamford"),
        make_entity("street_vendor_1"),
        make_entity("street_vendor_2")
    ]
    graph = {
        "interactions": [
            {"from": "sherlock_holmes", "to": ["watson", "lestrade"]},
            {"from": "watson", "to": ["mrs_hudson", "stamford"]},
            {"from": "mrs_hudson", "to": ["street_vendor_1", "street_vendor_2"]}
        ]
    }

    layers = compute_andos_layers(entities, "sherlock_holmes", graph)

    # Should have 3 layers
    assert len(layers) == 3

    # Layer 0 (periphery): street vendors, stamford, lestrade
    periphery_ids = set(e.entity_id for e in layers[0])
    assert "street_vendor_1" in periphery_ids
    assert "street_vendor_2" in periphery_ids

    # Layer 1: mrs_hudson, watson
    layer1_ids = set(e.entity_id for e in layers[1])
    assert "watson" in layer1_ids or "mrs_hudson" in layer1_ids

    # Layer 2 (core): sherlock_holmes
    core_ids = [e.entity_id for e in layers[2]]
    assert "sherlock_holmes" in core_ids
```

### Integration Tests (test_andos_workflows.py)

```python
@pytest.mark.integration
def test_dialog_synthesis_with_andos():
    """Verify entities train in correct layer order"""
    from workflows import generate_dialog_synthesis
    from storage import GraphStore
    from llm_v2 import LLMClient

    # Setup 3-layer scenario
    entities = create_test_entities(["A", "B", "C"])
    timepoint = create_test_timepoint()
    llm = LLMClient()
    store = GraphStore()

    # Add interaction graph to context
    store.context = {
        "interaction_graph": {
            "target_entity": "A",
            "interactions": [
                {"from": "A", "to": ["B"]},
                {"from": "B", "to": ["C"]}
            ]
        }
    }

    # Run dialog synthesis with ANDOS
    result = generate_dialog_synthesis(entities, timepoint, llm, store)

    # Verify tensors exist after each layer
    entity_map = {e.entity_id: e for e in entities}

    assert entity_map["C"].entity_metadata["ttm_tensor"] is not None  # C trained first
    assert entity_map["B"].entity_metadata["ttm_tensor"] is not None  # B trained second
    assert entity_map["A"].entity_metadata["ttm_tensor"] is not None  # A trained last

    # Verify ANDOS layer assignments
    assert entity_map["C"].entity_metadata["andos_layer"] == 0  # Periphery
    assert entity_map["B"].entity_metadata["andos_layer"] == 1
    assert entity_map["A"].entity_metadata["andos_layer"] == 2  # Core

    # Verify M18 tracked
    assert check_mechanism_tracked("M18", run_id=result.get("run_id"))


@pytest.mark.integration
def test_m14_circadian_with_andos():
    """Verify M14 (Circadian) works with ANDOS"""
    # Run simulation with circadian config
    config = get_template("board_meeting")
    config["circadian_config"] = {
        "morning_energy_boost": 1.2,
        "afternoon_slump": 0.8,
        "evening_recovery": 1.0
    }

    result = simulate_event(
        config["scenario"],
        llm=LLMClient(),
        store=GraphStore(),
        context=config,
        save_to_db=True
    )

    # Verify M14 tracked
    run = get_mechanism_run(result.run_id)
    assert "M14" in run.mechanisms_tracked

    # Verify tensors were available during dialog synthesis
    assert "missing tensor" not in result.log_output


@pytest.mark.integration
def test_m15_prospection_with_andos():
    """Verify M15 (Prospection) works with ANDOS"""
    # Run detective_prospection template
    config = get_template("detective_prospection")

    result = simulate_event(
        config["scenario"],
        llm=LLMClient(),
        store=GraphStore(),
        context=config,
        save_to_db=True
    )

    # Verify M15 tracked
    run = get_mechanism_run(result.run_id)
    assert "M15" in run.mechanisms_tracked

    # Verify prospective state generated
    holmes = next(e for e in result.entities if e.entity_id == "sherlock_holmes")
    assert "prospective_state" in holmes.entity_metadata
```

### E2E Tests (test_andos_e2e.py)

```python
@pytest.mark.integration
@pytest.mark.slow
def test_detective_prospection_with_andos():
    """Full E2E test with ANDOS-enabled detective template"""
    from generation.config_schema import detective_prospection
    from orchestrator import simulate_event
    from llm_v2 import LLMClient
    from storage import GraphStore

    # Load template with interaction_graph
    config = detective_prospection
    assert "interaction_graph" in config

    # Run simulation
    result = simulate_event(
        config["scenario"],
        llm=LLMClient(),
        store=GraphStore(),
        context=config,
        save_to_db=True
    )

    # Verify ANDOS ran
    run = get_mechanism_run(result.run_id)
    assert "M18" in run.mechanisms_tracked  # ANDOS

    # Verify M14 and M15 now work (blocked before ANDOS)
    assert "M14" in run.mechanisms_tracked  # Circadian
    assert "M15" in run.mechanisms_tracked  # Prospection

    # Verify no "missing tensor" warnings in logs
    assert "Skipping" not in result.log_output
    assert "missing tensor data" not in result.log_output

    # Verify all entities have tensors
    for entity in result.entities:
        assert entity.entity_metadata.get("ttm_tensor") is not None
        assert entity.entity_metadata.get("andos_layer") is not None


@pytest.mark.integration
def test_all_templates_with_andos():
    """Verify all 17 templates work with ANDOS"""
    from generation.config_schema import get_all_templates

    templates = get_all_templates()

    results = {}
    for name, config in templates.items():
        print(f"\n🧪 Testing {name}...")

        try:
            result = simulate_event(
                config["scenario"],
                llm=LLMClient(),
                store=GraphStore(),
                context=config,
                save_to_db=True
            )

            # Check ANDOS ran
            run = get_mechanism_run(result.run_id)
            andos_tracked = "M18" in run.mechanisms_tracked

            results[name] = {
                "success": True,
                "andos_tracked": andos_tracked,
                "mechanisms": len(run.mechanisms_tracked)
            }

            print(f"  ✅ {name}: {len(run.mechanisms_tracked)} mechanisms tracked")

        except Exception as e:
            results[name] = {"success": False, "error": str(e)}
            print(f"  ❌ {name}: {e}")

    # Verify all templates succeeded
    failures = [name for name, r in results.items() if not r["success"]]
    assert len(failures) == 0, f"Failed templates: {failures}"

    # Verify ANDOS tracked in most templates
    andos_count = sum(1 for r in results.values() if r.get("andos_tracked"))
    assert andos_count >= 15, f"Only {andos_count}/17 templates tracked ANDOS"


@pytest.mark.integration
def test_mechanism_coverage_100_percent():
    """Verify 17/17 mechanism coverage achieved"""
    from mechanism_dashboard import get_mechanism_coverage

    coverage = get_mechanism_coverage()

    # All 17 mechanisms should have firings
    mechanisms_with_firings = sum(
        1 for m in coverage
        if m["firings"] > 0
    )

    assert mechanisms_with_firings == 17, (
        f"Only {mechanisms_with_firings}/17 mechanisms have firings. "
        f"Missing: {[m['id'] for m in coverage if m['firings'] == 0]}"
    )

    print("\n✅ 100% Mechanism Coverage Achieved!")
    print(f"   All 17/17 mechanisms verified")
```

### Validation Tests (test_andos_validation.py)

```python
def test_all_templates_have_interaction_graphs():
    """Ensure all 17 templates include interaction_graph"""
    from generation.config_schema import get_all_templates

    templates = get_all_templates()

    for name, config in templates.items():
        assert "interaction_graph" in config, (
            f"Template '{name}' missing interaction_graph"
        )

        # Validate structure
        graph = config["interaction_graph"]
        assert "target_entity" in graph
        assert "interactions" in graph
        assert isinstance(graph["interactions"], list)


def test_all_templates_pass_dag_check():
    """Verify all templates have acyclic graphs"""
    import networkx as nx
    from generation.config_schema import get_all_templates

    templates = get_all_templates()

    for name, config in templates.items():
        graph_config = config["interaction_graph"]

        # Build graph
        G = nx.DiGraph()
        for interaction in graph_config["interactions"]:
            source = interaction["from"]
            targets = interaction["to"] if isinstance(interaction["to"], list) else [interaction["to"]]
            for target in targets:
                G.add_edge(source, target)

        # Check DAG property
        is_dag = nx.is_directed_acyclic_graph(G)
        assert is_dag, f"Template '{name}' has cycle in interaction graph"


def test_andos_metadata_in_exports():
    """Verify exports include ANDOS structure"""
    from reporting.export_pipeline import ExportPipeline
    from reporting.query_engine import EnhancedQueryEngine

    world_id = "test_world"
    exporter = ExportPipeline(EnhancedQueryEngine())

    # Export as JSON
    data = exporter.export_report(
        world_id=world_id,
        report_type="summary",
        export_format="json",
        output_path="/tmp/test_export.json"
    )

    # Verify ANDOS structure present
    assert "andos_structure" in data
    assert "training_layers" in data["andos_structure"]
    assert "entity_distances" in data["andos_structure"]
    assert "dependency_graph" in data["andos_structure"]
```

---

## 8. Migration Path

### Backward Compatibility Strategy

**Problem**: Existing templates don't have `interaction_graph` field

**Solution 1: Graph Inference** (Automatic)

```python
def _infer_interaction_graph(config: Dict) -> Dict:
    """
    Infer interaction graph from entity list for legacy templates

    Heuristics:
    - If < 3 entities: fully connected (everyone talks to everyone)
    - If >= 3 entities: sequential chain (A→B→C→...)
    - Set max_depth = ceil(log2(num_entities))
    """
    entities = config["entities"]
    num_entities = len(entities)

    if num_entities == 1:
        # Single entity (monologue)
        return {
            "target_entity": entities[0]["id"],
            "interactions": [],
            "max_depth": 0
        }

    if num_entities <= 3:
        # Fully connected small graph
        target = entities[0]["id"]
        interactions = [
            {
                "from": entities[i]["id"],
                "to": [e["id"] for e in entities if e["id"] != entities[i]["id"]]
            }
            for i in range(num_entities)
        ]
        return {
            "target_entity": target,
            "interactions": interactions,
            "max_depth": 1
        }

    # Sequential chain for larger graphs (conservative)
    target = entities[0]["id"]
    interactions = [
        {"from": entities[i]["id"], "to": [entities[i+1]["id"]]}
        for i in range(num_entities - 1)
    ]

    return {
        "target_entity": target,
        "interactions": interactions,
        "max_depth": num_entities - 1
    }
```

**Solution 2: Template Migration Script**

```bash
#!/bin/bash
# migrate_templates_to_andos.sh

python3 << 'EOF'
from generation.config_schema import *
import json

# List of templates to update
templates = [
    jefferson_dinner, board_meeting, hospital_crisis, kami_shrine,
    detective_prospection, paul_revere_ride, constitutional_convention,
    apollo_13_crisis, versailles_treaty, stock_market_crash,
    battle_of_midway, jury_deliberation, restaurant_service,
    classroom_debate, emergency_room, family_reunion, startup_pitch
]

for template in templates:
    name = template['scenario'][:30]

    if 'interaction_graph' not in template:
        print(f"⚠️  Template '{name}' missing interaction_graph")

        # Infer graph
        inferred = _infer_interaction_graph(template)
        print(f"   Generated graph: {len(inferred['interactions'])} interactions")

        # Add to template (requires manual review)
        print(f"   ⚠️  MANUAL REVIEW REQUIRED")
    else:
        print(f"✅ Template '{name}' has interaction_graph")

EOF
```

### Incremental Rollout Plan

**Phase 10.1-10.2**: ANDOS optional, activated by context flag
```python
# In workflows.py
if store.context.get("andos_enabled", False):
    # Use ANDOS
    training_layers = resolve_entity_dependencies(entities, store)
else:
    # Legacy behavior (all entities in one layer)
    training_layers = [entities]
```

**Phase 10.3-10.4**: ANDOS default for new templates, legacy uses inference
```python
# In orchestrator.py
if "interaction_graph" in context:
    # Use explicit graph
    training_layers = self._compute_andos_layers(graph, target, entities)
else:
    # Infer graph (legacy)
    inferred_graph = _infer_interaction_graph(context)
    training_layers = self._compute_andos_layers(inferred_graph, target, entities)
```

**Phase 10.5-10.7**: ANDOS mandatory, all templates updated
```python
# In config validation
class ConfigValidationSchema(BaseModel):
    interaction_graph: InteractionGraphSchema  # REQUIRED (no Optional)
    # ... rest of schema ...
```

### Rollback Plan

If ANDOS causes issues:

1. **Disable via context flag**:
```python
context["andos_enabled"] = False  # Disable ANDOS, revert to legacy
```

2. **Investigate via debug logs**:
```python
# Enable verbose ANDOS logging
context["andos_debug"] = True  # Shows layer computation, entity assignments
```

3. **Isolate failing template**:
```bash
# Run single template with ANDOS disabled
python3 << EOF
config = get_template("problematic_template")
config["andos_enabled"] = False
result = simulate_event(config, llm, store)
EOF
```

4. **Fix and re-enable**:
- Identify root cause in ANDOS layer computation
- Fix graph configuration or cycle detection
- Re-enable ANDOS for that template

---

## 9. Success Criteria

### Quantitative Metrics

**Mechanism Coverage**:
- ✅ **17/17 mechanisms verified** (currently 15/17)
- ✅ **M14 Success Rate**: >90% (currently 0%)
- ✅ **M15 Success Rate**: >90% (currently 0%)
- ✅ **M18 (ANDOS) Success Rate**: >95%

**Test Reliability**:
- ✅ **Overall Test Pass Rate**: >95% (currently 89.3%)
- ✅ **ANDOS Unit Tests**: 100% passing
- ✅ **ANDOS Integration Tests**: 100% passing
- ✅ **E2E Tests**: >90% passing

**Template Coverage**:
- ✅ **17/17 templates** with `interaction_graph`
- ✅ **17/17 templates** pass DAG validation
- ✅ **17/17 templates** run successfully with ANDOS

**Performance**:
- ✅ **Tensor Availability**: 100% before dialog synthesis (currently ~0%)
- ✅ **ANDOS Overhead**: <5% additional simulation time

### Qualitative Indicators

**Error Elimination**:
- ❌ **No more "missing tensor" warnings** in logs (currently blocking M14/M15)
- ✅ **Layer-by-layer training** visible in orchestrator output
- ✅ **Detective template** runs completely without errors
- ✅ **Cycle detection** catches invalid templates early

**Documentation Quality**:
- ✅ **MECHANICS.md** includes M18 (ANDOS) section
- ✅ **README.md** updated to 17/17 coverage
- ✅ **PLAN.md** includes Phase 10 completion
- ✅ **ANDOS-PLAN.md** (this document) serves as reference

**Export Quality**:
- ✅ **Exports include ANDOS metadata** for ML training
- ✅ **JSONL format** has per-entity `andos_layer` field
- ✅ **Reports** show layer information clearly

### Performance Benchmarks

**ANDOS Computation Time**:
- Small graph (5 entities): <10ms
- Medium graph (20 entities): <50ms
- Large graph (100 entities): <200ms

**Memory Overhead**:
- NetworkX graph: O(V + E) where V = entities, E = interactions
- Layer storage: O(V) entity references
- **Total overhead**: <1MB for 100 entities

**Scalability**:
- Support up to **100 entities** across **5 layers**
- Support up to **200 interactions** (edges)
- Handle **disconnected components** (multiple graphs)

---

## 10. Open Questions for User

### 1. Target Entity Selection
**Question**: Should target entity be:
- **Option A**: Explicitly specified in config (`interaction_graph.target_entity`) ← **RECOMMENDED**
- Option B: Auto-detected as entity with most interactions
- Option C: User-provided at runtime via context

**Recommendation**: Option A - Explicit specification gives user control and makes ANDOS behavior deterministic.

---

### 2. Multi-Timepoint Handling
**Question**: How does ANDOS apply across multiple timepoints?
- **Option A**: Re-compute layers per timepoint (handles entity joins/leaves) ← **RECOMMENDED**
- Option B: Use same layers throughout simulation
- Option C: Update graph incrementally as entities interact

**Recommendation**: Option A - Re-compute per timepoint handles dynamic scenarios (entity joins scene at T2, leaves at T5).

---

### 3. Partial Graph Coverage
**Question**: What if some entities don't appear in `interaction_graph`?
- **Option A**: Add to periphery (Layer 0) ← **RECOMMENDED**
- Option B: Infer their position from entity type
- Option C: Raise validation error (strict mode)

**Recommendation**: Option A - Graceful degradation, treat ungraphed entities as seeds.

---

### 4. Performance Optimization
**Question**: For large graphs (100+ entities), should we:
- **Option A**: Cache layer computation (reuse if graph unchanged) ← **RECOMMENDED**
- Option B: Parallelize layer training (all entities in a layer train simultaneously)
- Option C: Use incremental graph updates (only recompute changed subgraphs)

**Recommendation**: Option A initially, Option B in future optimization phase.

---

### 5. TTM Training Depth
**Question**: Should periphery entities (seeds) use:
- **Option A**: Minimal training (TENSOR resolution only) ← **RECOMMENDED for Phase 10**
- Option B: Full training (TRAINED resolution)
- Option C: Adaptive based on layer depth (Layer 0 = TENSOR, Layer 3 = TRAINED)

**Recommendation**: Option A for Phase 10 (simplest), Option C in future optimization.

---

## 11. References

### Key Files Modified in Phase 10
- `workflows.py` - Dialog synthesis with ANDOS (lines 645-813 replaced, ~300 new lines)
- `orchestrator.py` - Step 3.5 ANDOS integration (lines ~1100, ~80 new lines)
- `generation/config_schema.py` - All 17 templates updated with `interaction_graph`
- `reporting/export_pipeline.py` - ANDOS metadata in exports (~80 new lines)
- `generation/horizontal_generator.py` - ANDOS validation (~100 new lines)

### New Files Created in Phase 10
- `andos/layer_computer.py` - Core ANDOS algorithm (~200-300 lines)
- `test_andos_layer_computation.py` - Unit tests (~200 lines)
- `test_andos_workflows.py` - Integration tests (~150 lines)
- `test_andos_e2e.py` - E2E tests (~200 lines)
- `test_andos_validation.py` - Validation tests (~100 lines)
- `ANDOS-PLAN.md` - This document (~1500 lines)

### Related Mechanisms
- **M6 (TTM Tensor Model)** - ANDOS ensures tensors available for synthesis
- **M14 (Circadian Patterns)** - BLOCKED by missing tensors, UNBLOCKED by ANDOS
- **M15 (Entity Prospection)** - BLOCKED by missing partner tensors, UNBLOCKED by ANDOS
- **M18 (ANDOS) - NEW** - Dependency resolution architecture (this mechanism)

### Graph Theory Foundations
- **Topological Sort** - Order nodes in DAG respecting dependencies (CLRS Ch 22.4)
- **Reverse Graph** - Invert edge direction to compute "influence distance"
- **Shortest Path (BFS)** - Compute distance from target entity (CLRS Ch 22.2)
- **Directed Acyclic Graph (DAG)** - Required property for ANDOS (no cycles)

### Academic References
- Pearl, J. (2009). *Causality: Models, Reasoning, and Inference* - Causal graphs
- Cormen, T. et al. (2009). *Introduction to Algorithms* (CLRS) - Graph algorithms
- Newman, M. (2018). *Networks* - Network analysis and topological ordering

---

## 12. Timeline and Effort Estimate

**Total Duration**: 10-14 days

| Phase | Tasks | Effort | Dependencies |
|-------|-------|--------|--------------|
| **10.1** | Graph Infrastructure | 1-2 days | None |
| **10.2** | Workflow Integration | 2-3 days | 10.1 |
| **10.3** | Orchestrator Integration | 2 days | 10.1, 10.2 |
| **10.4** | Template Updates | 1-2 days | 10.1 |
| **10.5** | ML Generator Updates | 1 day | 10.2, 10.4 |
| **10.6** | Export Pipeline Updates | 1 day | 10.2, 10.3 |
| **10.7** | Full E2E Testing | 2-3 days | 10.1-10.6 |

**Critical Path**: 10.1 → 10.2 → 10.3 → 10.7

**Parallelization Opportunities**:
- 10.4 (Templates) can run parallel to 10.2 (Workflows)
- 10.5 (Generators) and 10.6 (Exports) can run parallel after 10.2

---

## 13. Risk Mitigation

### Risk 1: Cycle Detection Failure
**Risk**: User creates template with circular dependencies
**Mitigation**:
- Validate all templates in Phase 10.4
- Add cycle detection to config validation schema
- Provide clear error messages with cycle paths

### Risk 2: Performance Degradation
**Risk**: ANDOS adds significant overhead to simulation time
**Mitigation**:
- Profile ANDOS computation time in Phase 10.2
- Cache graph computation if same config reused
- Optimize NetworkX operations (use `reverse()` vs rebuilding graph)

### Risk 3: Complex Graph Debugging
**Risk**: Hard to debug layer assignments for complex graphs
**Mitigation**:
- Add verbose logging mode (`context["andos_debug"] = True`)
- Visualize graph structure in logs (ASCII art or NetworkX plot)
- Include layer assignments in mechanism tracking metadata

### Risk 4: Legacy Template Breakage
**Risk**: Old templates break when ANDOS becomes mandatory
**Mitigation**:
- Implement graph inference for legacy templates
- Gradual rollout (optional → default → mandatory)
- Provide migration script for manual template updates

### Risk 5: M14/M15 Still Don't Fire
**Risk**: ANDOS implemented but M14/M15 still blocked by other issues
**Mitigation**:
- Add extensive diagnostic logging in Phase 10.2
- Test M14/M15 independently before full E2E
- Create minimal reproduction case (3 entities, 2 layers)

---

## 14. Future Enhancements (Post-Phase 10)

### Enhancement 1: Parallel Layer Training
**Idea**: All entities in a layer can train simultaneously (no dependencies within layer)

```python
# Instead of sequential:
for entity in layer_entities:
    train_entity(entity)

# Use parallel:
import asyncio
await asyncio.gather(*[train_entity(e) for e in layer_entities])
```

**Benefit**: 2-5x speedup for large layers

---

### Enhancement 2: Adaptive Resolution by Layer
**Idea**: Periphery entities use TENSOR resolution, core uses TRAINED

```python
def get_resolution_for_layer(layer_idx: int, max_layers: int) -> ResolutionLevel:
    """Adaptive resolution based on layer depth"""
    depth_ratio = layer_idx / max_layers

    if depth_ratio < 0.3:
        return ResolutionLevel.TENSOR  # Periphery (seeds)
    elif depth_ratio < 0.7:
        return ResolutionLevel.DIALOG  # Mid-layers
    else:
        return ResolutionLevel.TRAINED  # Core entities
```

**Benefit**: Further cost optimization (additional 20-30% token reduction)

---

### Enhancement 3: Dynamic Graph Updates
**Idea**: Update interaction graph as entities join/leave scenes

```python
def update_andos_graph_for_timepoint(
    graph: nx.DiGraph,
    timepoint: Timepoint,
    entities_present: List[str]
) -> nx.DiGraph:
    """Update graph to reflect entities present at this timepoint"""
    G_updated = graph.copy()

    # Remove entities not present
    nodes_to_remove = [n for n in G_updated.nodes() if n not in entities_present]
    G_updated.remove_nodes_from(nodes_to_remove)

    return G_updated
```

**Benefit**: Handles dynamic scenarios (characters arrive/depart)

---

### Enhancement 4: ANDOS Visualization
**Idea**: Generate visual graph showing layer structure

```python
import matplotlib.pyplot as plt
import networkx as nx

def visualize_andos_layers(layers: List[List[Entity]], graph: nx.DiGraph):
    """Generate visual representation of ANDOS structure"""
    pos = {}
    colors = []

    for layer_idx, layer in enumerate(layers):
        y = -layer_idx  # Stack layers vertically
        for entity_idx, entity in enumerate(layer):
            x = entity_idx - len(layer) / 2  # Center horizontally
            pos[entity.entity_id] = (x, y)
            colors.append(layer_idx)

    nx.draw(graph, pos, node_color=colors, with_labels=True, cmap='viridis')
    plt.savefig('andos_structure.png')
```

**Benefit**: Debugging and documentation

---

### Enhancement 5: ANDOS for Multi-Modal Entities
**Idea**: Different training strategies for animistic entities (M16)

```python
def get_training_strategy(entity: Entity) -> str:
    """Determine training strategy based on entity type"""
    if entity.entity_type == "human":
        return "full_dialog"
    elif entity.entity_type in ["animal", "building"]:
        return "limited_agency"  # Simpler monologue
    elif entity.entity_type == "abstract":
        return "concept_evolution"  # No dialog, just state changes
```

**Benefit**: More realistic non-human entity behavior

---

## 15. Conclusion

ANDOS (Acyclical Network Directed Orthogonal Synthesis) solves the fundamental circular dependency blocking M14 and M15 by introducing **reverse topological ordering** for entity training. This architectural redesign touches the entire stack (workflows, orchestrator, templates, generators, exports) but provides a mathematically sound foundation for achieving **100% mechanism coverage (17/17)**.

**Key Insights**:
1. The M14/M15 blocker was not a bug but a **fundamental architectural gap**
2. Dialog synthesis and tensor training have a **strict dependency order** that must be respected
3. ANDOS resolves dependencies via **"crystal formation"** from periphery to core
4. Implementation requires **7 phases** over **10-14 days**
5. Success unlocks **17/17 mechanism coverage** and validates system completeness

**Next Steps**:
1. User approval of this plan
2. Begin Phase 10.1 (Graph Infrastructure)
3. Iterate through phases 10.2-10.7
4. Achieve 100% mechanism coverage
5. Celebrate with comprehensive Phase 10 summary

---

**Document Status**: Design Complete - Awaiting Approval
**Last Updated**: October 24, 2025
**Author**: AI Coding Agent (Phase 9 continuation)
**Next Action**: User approval to proceed with Phase 10.1
