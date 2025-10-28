# ============================================================================
# orchestrator.py - Scene-to-Specification Compiler (OrchestratorAgent)
# ============================================================================
"""
OrchestratorAgent: Natural language event description → complete scene specification

Takes high-level descriptions like "simulate the constitutional convention" and
generates the full specification needed by existing workflows:
- Entity roster with role-based resolution targeting
- Timepoint sequence with causal relationships
- Relationship graph (social network)
- Initial knowledge seeding from historical context

Architecture:
    SceneParser → KnowledgeSeeder → RelationshipExtractor → ResolutionAssigner
    → Feed to create_entity_training_workflow() and TemporalAgent
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import networkx as nx

from schemas import (
    Entity, Timepoint, ResolutionLevel, TemporalMode,
    ExposureEvent, CognitiveTensor
)
from llm import LLMClient, EntityPopulation
from storage import GraphStore
from workflows import TemporalAgent, create_entity_training_workflow


# ============================================================================
# Structured Output Schemas for LLM Responses
# ============================================================================

class EntityRosterItem(BaseModel):
    """Single entity in a scene"""
    entity_id: str
    entity_type: str = "human"
    role: str  # "primary", "secondary", "background", "environment"
    description: str
    initial_knowledge: List[str] = []
    relationships: Dict[str, str] = {}  # entity_id -> relationship_type


class TimepointSpec(BaseModel):
    """Single timepoint specification"""
    timepoint_id: str
    timestamp: str  # ISO format datetime
    event_description: str
    entities_present: List[str]
    importance: float = 0.5  # 0.0-1.0
    causal_parent: Optional[str] = None


class SceneSpecification(BaseModel):
    """Complete scene specification from natural language"""
    scene_title: str
    scene_description: str
    temporal_mode: str = "pearl"
    temporal_scope: Dict[str, str]  # start_date, end_date, location
    entities: List[EntityRosterItem]
    timepoints: List[TimepointSpec]
    global_context: str


# ============================================================================
# Component 1: Scene Parser
# ============================================================================

class SceneParser:
    """
    Parse natural language event description into structured specification.

    Uses LLM to decompose high-level prompt into:
    - Temporal scope (when, where, how long)
    - Entity roster (who, what roles)
    - Event sequence (key moments)
    - Appropriate temporal mode
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def parse(self, event_description: str, context: Optional[Dict] = None) -> SceneSpecification:
        """
        Parse natural language description into scene specification.

        Args:
            event_description: Natural language like "simulate the constitutional convention"
            context: Optional additional context (preferred temporal mode, etc.)

        Returns:
            SceneSpecification with entities, timepoints, relationships
        """
        context = context or {}

        prompt = self._build_parsing_prompt(event_description, context)

        # Use LLM to generate structured scene specification
        response = self._call_llm_structured(prompt, SceneSpecification)

        return response

    def _build_parsing_prompt(self, event_description: str, context: Dict) -> str:
        """Build prompt for scene parsing"""
        preferred_mode = context.get("temporal_mode", "pearl")
        max_entities = context.get("max_entities", 20)
        max_timepoints = context.get("max_timepoints", 10)

        prompt = f"""You are a historical scene analyzer. Parse this event description into a structured simulation specification.

Event Description: {event_description}

Generate a complete scene specification with these components:

1. **Scene Title**: Short descriptive title
2. **Scene Description**: 2-3 sentence overview
3. **Temporal Mode**: Choose from: pearl (standard causality), directorial (narrative focus), nonlinear (flashbacks), branching (what-if), cyclical (prophecy/loops)
   Preferred mode: {preferred_mode}
4. **Temporal Scope**:
   - start_date: ISO datetime when events begin
   - end_date: ISO datetime when events conclude
   - location: Geographic location description
5. **Entities** (max {max_entities}): List of people, objects, places involved
   For each entity provide:
   - entity_id: Unique identifier (lowercase, no spaces, e.g., "james_madison")
   - entity_type: Type (human, animal, building, object, abstract)
   - role: Importance level (primary, secondary, background, environment)
   - description: Brief description (1 sentence)
   - initial_knowledge: List of 3-8 facts this entity knows at start
   - relationships: Dict mapping other entity_ids to relationship types (e.g., "ally", "rival", "mentor")
6. **Timepoints** (max {max_timepoints}): Key moments in the event sequence
   For each timepoint provide:
   - timepoint_id: Unique identifier (e.g., "tp_001_opening")
   - timestamp: ISO datetime
   - event_description: What happens at this moment
   - entities_present: List of entity_ids present
   - importance: Float 0.0-1.0 (how pivotal this moment is)
   - causal_parent: Previous timepoint_id (null for first timepoint)
7. **Global Context**: Additional context about the historical period, cultural norms, constraints

Return ONLY valid JSON matching this schema. No other text.

Schema:
{{
  "scene_title": "string",
  "scene_description": "string",
  "temporal_mode": "pearl|directorial|nonlinear|branching|cyclical",
  "temporal_scope": {{"start_date": "ISO datetime", "end_date": "ISO datetime", "location": "string"}},
  "entities": [
    {{
      "entity_id": "string",
      "entity_type": "string",
      "role": "primary|secondary|background|environment",
      "description": "string",
      "initial_knowledge": ["string", ...],
      "relationships": {{"entity_id": "relationship_type", ...}}
    }}
  ],
  "timepoints": [
    {{
      "timepoint_id": "string",
      "timestamp": "ISO datetime",
      "event_description": "string",
      "entities_present": ["entity_id", ...],
      "importance": 0.5,
      "causal_parent": "string or null"
    }}
  ],
  "global_context": "string"
}}"""

        return prompt

    def _call_llm_structured(self, prompt: str, response_model: type) -> Any:
        """Call LLM and parse structured response"""
        if self.llm.dry_run:
            # Return mock data for dry run
            return self._mock_scene_specification()

        try:
            from llm import retry_with_backoff

            def _api_call():
                response = self.llm.client.chat.completions.create(
                    model=self.llm.default_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,  # Lower temperature for structured output
                    max_tokens=4000
                )
                content = response["choices"][0]["message"]["content"]

                # Parse JSON response
                data = json.loads(content.strip())
                return response_model(**data)

            result = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0)

            self.llm.token_count += 4000  # Estimate
            self.llm.cost += 0.02  # Estimate

            return result

        except Exception as e:
            print(f"⚠️ Scene parsing failed: {e}")
            print("Returning mock specification")
            return self._mock_scene_specification()

    def _mock_scene_specification(self) -> SceneSpecification:
        """Generate mock scene specification for testing"""
        return SceneSpecification(
            scene_title="Test Scene",
            scene_description="A test scene for development purposes",
            temporal_mode="pearl",
            temporal_scope={
                "start_date": "2024-01-01T09:00:00",
                "end_date": "2024-01-01T17:00:00",
                "location": "Test Location"
            },
            entities=[
                EntityRosterItem(
                    entity_id="test_entity_1",
                    entity_type="human",
                    role="primary",
                    description="Primary test entity",
                    initial_knowledge=["fact1", "fact2", "fact3"],
                    relationships={"test_entity_2": "ally"}
                ),
                EntityRosterItem(
                    entity_id="test_entity_2",
                    entity_type="human",
                    role="secondary",
                    description="Secondary test entity",
                    initial_knowledge=["fact4", "fact5"],
                    relationships={"test_entity_1": "ally"}
                )
            ],
            timepoints=[
                TimepointSpec(
                    timepoint_id="tp_001",
                    timestamp="2024-01-01T09:00:00",
                    event_description="Scene opening",
                    entities_present=["test_entity_1", "test_entity_2"],
                    importance=0.8,
                    causal_parent=None
                )
            ],
            global_context="Test context for development"
        )


# ============================================================================
# Component 2: Knowledge Seeder
# ============================================================================

class KnowledgeSeeder:
    """
    Seed initial entity knowledge states from scene specification.

    Creates ExposureEvent records for initial knowledge to establish
    causal provenance. Optionally augments with external sources
    (future: Wikipedia, historical databases).
    """

    def __init__(self, store: GraphStore):
        self.store = store

    def seed_knowledge(
        self,
        spec: SceneSpecification,
        create_exposure_events: bool = True
    ) -> Dict[str, List[ExposureEvent]]:
        """
        Create initial knowledge exposure events for all entities.

        Args:
            spec: Scene specification with entity initial_knowledge
            create_exposure_events: Whether to create ExposureEvent records

        Returns:
            Dict mapping entity_id to list of exposure events
        """
        exposure_map = {}

        # Parse temporal scope start time
        start_time = datetime.fromisoformat(spec.temporal_scope["start_date"])

        for entity_item in spec.entities:
            events = []

            for idx, knowledge_item in enumerate(entity_item.initial_knowledge):
                # Create exposure event for each initial knowledge item
                event = ExposureEvent(
                    entity_id=entity_item.entity_id,
                    event_type="initial",  # Special type for starting knowledge
                    information=knowledge_item,
                    source="scene_initialization",
                    timestamp=start_time - timedelta(days=1),  # Before scene starts
                    confidence=1.0,  # Initial knowledge is certain
                    timepoint_id=f"pre_{spec.timepoints[0].timepoint_id if spec.timepoints else 'scene'}"
                )

                events.append(event)

                # Optionally save to database
                if create_exposure_events and self.store:
                    self.store.save_exposure_event(event)

            exposure_map[entity_item.entity_id] = events

        print(f"🌱 Seeded {sum(len(events) for events in exposure_map.values())} knowledge items across {len(exposure_map)} entities")

        return exposure_map


# ============================================================================
# Component 3: Relationship Extractor
# ============================================================================

class RelationshipExtractor:
    """
    Build social/spatial relationship graph from entity specifications.

    Creates NetworkX graph with:
    - Nodes: entity_ids
    - Edges: relationships with types and weights
    - Node attributes: entity metadata
    """

    def build_graph(self, spec: SceneSpecification) -> nx.Graph:
        """
        Build relationship graph from scene specification.

        Args:
            spec: Scene specification with entity relationships

        Returns:
            NetworkX graph with nodes and edges
        """
        graph = nx.Graph()

        # Add nodes for all entities
        for entity_item in spec.entities:
            graph.add_node(
                entity_item.entity_id,
                entity_type=entity_item.entity_type,
                role=entity_item.role,
                description=entity_item.description
            )

        # Add edges for declared relationships
        for entity_item in spec.entities:
            for target_id, rel_type in entity_item.relationships.items():
                if target_id in graph.nodes:
                    # Weight relationships based on type (simple heuristic)
                    weight = self._relationship_weight(rel_type)
                    graph.add_edge(
                        entity_item.entity_id,
                        target_id,
                        relationship=rel_type,
                        weight=weight
                    )

        # Add co-presence edges based on timepoint attendance
        self._add_copresence_edges(graph, spec)

        print(f"🕸️  Built graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

        return graph

    def _relationship_weight(self, rel_type: str) -> float:
        """Convert relationship type to numeric weight"""
        weights = {
            "ally": 0.9,
            "friend": 0.8,
            "colleague": 0.7,
            "acquaintance": 0.5,
            "neutral": 0.3,
            "rival": 0.2,
            "enemy": 0.1,
            "mentor": 0.85,
            "student": 0.75,
            "family": 0.95
        }
        return weights.get(rel_type.lower(), 0.5)

    def _add_copresence_edges(self, graph: nx.Graph, spec: SceneSpecification):
        """Add edges between entities present at same timepoints"""
        for tp in spec.timepoints:
            entities = tp.entities_present
            # Add edge between all pairs present at this timepoint
            for i, e1 in enumerate(entities):
                for e2 in entities[i+1:]:
                    if e1 in graph.nodes and e2 in graph.nodes:
                        if not graph.has_edge(e1, e2):
                            graph.add_edge(
                                e1, e2,
                                relationship="copresent",
                                weight=0.4
                            )


# ============================================================================
# Component 4: Resolution Assigner
# ============================================================================

class ResolutionAssigner:
    """
    Assign resolution levels to entities based on their roles.

    Role-based heuristics:
    - primary: DIALOG or TRAINED (high detail)
    - secondary: GRAPH or DIALOG (medium detail)
    - background: SCENE (low detail)
    - environment: TENSOR_ONLY or SCENE (minimal detail)
    """

    def assign_resolutions(
        self,
        spec: SceneSpecification,
        graph: nx.Graph
    ) -> Dict[str, ResolutionLevel]:
        """
        Assign resolution levels based on role and centrality.

        Args:
            spec: Scene specification with entity roles
            graph: NetworkX graph for centrality calculation

        Returns:
            Dict mapping entity_id to ResolutionLevel
        """
        assignments = {}

        # Calculate eigenvector centrality if graph has edges
        centrality = {}
        if graph.number_of_edges() > 0:
            try:
                centrality = nx.eigenvector_centrality(graph, max_iter=1000)
            except:
                # Fallback to degree centrality if eigenvector fails
                centrality = nx.degree_centrality(graph)

        for entity_item in spec.entities:
            entity_id = entity_item.entity_id
            role = entity_item.role
            cent = centrality.get(entity_id, 0.0)

            # Role-based resolution assignment
            if role == "primary":
                # High centrality primary actors get TRAINED
                if cent > 0.5:
                    level = ResolutionLevel.TRAINED
                else:
                    level = ResolutionLevel.DIALOG
            elif role == "secondary":
                # Medium centrality secondary actors
                if cent > 0.3:
                    level = ResolutionLevel.DIALOG
                else:
                    level = ResolutionLevel.GRAPH
            elif role == "background":
                level = ResolutionLevel.SCENE
            else:  # environment
                level = ResolutionLevel.TENSOR_ONLY

            assignments[entity_id] = level

        print(f"🎯 Assigned resolutions: "
              f"TRAINED={sum(1 for v in assignments.values() if v == ResolutionLevel.TRAINED)}, "
              f"DIALOG={sum(1 for v in assignments.values() if v == ResolutionLevel.DIALOG)}, "
              f"GRAPH={sum(1 for v in assignments.values() if v == ResolutionLevel.GRAPH)}, "
              f"SCENE={sum(1 for v in assignments.values() if v == ResolutionLevel.SCENE)}, "
              f"TENSOR={sum(1 for v in assignments.values() if v == ResolutionLevel.TENSOR_ONLY)}")

        return assignments


# ============================================================================
# Main Orchestrator Agent
# ============================================================================

class OrchestratorAgent:
    """
    Top-level coordinator for scene-to-simulation compilation.

    Orchestrates:
    1. SceneParser: Natural language → structured spec
    2. KnowledgeSeeder: Initial knowledge → exposure events
    3. RelationshipExtractor: Entity relationships → graph
    4. ResolutionAssigner: Role-based resolution targeting
    5. Integration with existing workflows

    Usage:
        orchestrator = OrchestratorAgent(llm_client, store)
        result = orchestrator.orchestrate("simulate the constitutional convention")
        # Returns entities, timepoints, graph ready for workflows
    """

    def __init__(self, llm_client: LLMClient, store: GraphStore):
        self.llm = llm_client
        self.store = store

        # Initialize components
        self.scene_parser = SceneParser(llm_client)
        self.knowledge_seeder = KnowledgeSeeder(store)
        self.relationship_extractor = RelationshipExtractor()
        self.resolution_assigner = ResolutionAssigner()

    def orchestrate(
        self,
        event_description: str,
        context: Optional[Dict] = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Complete orchestration: natural language → ready-to-simulate scene.

        Args:
            event_description: Natural language like "simulate the constitutional convention"
            context: Optional context (temporal_mode, max_entities, etc.)
            save_to_db: Whether to save entities/timepoints to database

        Returns:
            Dict with:
                - specification: SceneSpecification
                - entities: List[Entity] (populated, with resolution levels)
                - timepoints: List[Timepoint] (causal chain)
                - graph: NetworkX graph
                - exposure_events: Dict[entity_id, List[ExposureEvent]]
                - temporal_agent: TemporalAgent (configured for scene)
        """
        print(f"\n🎬 ORCHESTRATING SCENE: {event_description}\n")

        context = context or {}

        # Step 1: Parse scene specification
        print("📋 Step 1: Parsing scene specification...")
        spec = self.scene_parser.parse(event_description, context)
        print(f"   ✓ Title: {spec.scene_title}")
        print(f"   ✓ Temporal Mode: {spec.temporal_mode}")
        print(f"   ✓ Entities: {len(spec.entities)}")
        print(f"   ✓ Timepoints: {len(spec.timepoints)}")

        # Step 2: Seed initial knowledge
        print("\n🌱 Step 2: Seeding initial knowledge...")
        exposure_events = self.knowledge_seeder.seed_knowledge(spec, create_exposure_events=save_to_db)

        # Step 3: Build relationship graph
        print("\n🕸️  Step 3: Building relationship graph...")
        graph = self.relationship_extractor.build_graph(spec)

        # Step 4: Assign resolution levels
        print("\n🎯 Step 4: Assigning resolution levels...")
        resolution_assignments = self.resolution_assigner.assign_resolutions(spec, graph)

        # Step 5: Create Entity objects
        print("\n👥 Step 5: Creating entity objects...")
        entities = self._create_entities(spec, resolution_assignments, exposure_events)

        # Step 6: Create Timepoint objects
        print("\n⏰ Step 6: Creating timepoint objects...")
        timepoints = self._create_timepoints(spec)

        # Step 7: Save to database if requested
        if save_to_db:
            print("\n💾 Step 7: Saving to database...")
            for entity in entities:
                self.store.save_entity(entity)
            for tp in timepoints:
                self.store.save_timepoint(tp)
            print(f"   ✓ Saved {len(entities)} entities and {len(timepoints)} timepoints")

        # Step 8: Create TemporalAgent
        print("\n🕐 Step 8: Creating temporal agent...")
        temporal_mode = TemporalMode(spec.temporal_mode)
        temporal_agent = TemporalAgent(
            mode=temporal_mode,
            store=self.store,
            llm_client=self.llm
        )
        print(f"   ✓ Temporal agent created with mode: {temporal_mode.value}")

        print("\n✅ ORCHESTRATION COMPLETE\n")

        return {
            "specification": spec,
            "entities": entities,
            "timepoints": timepoints,
            "graph": graph,
            "exposure_events": exposure_events,
            "temporal_agent": temporal_agent,
            "resolution_assignments": resolution_assignments
        }

    def _create_entities(
        self,
        spec: SceneSpecification,
        resolution_assignments: Dict[str, ResolutionLevel],
        exposure_events: Dict[str, List[ExposureEvent]]
    ) -> List[Entity]:
        """Create Entity objects from specification"""
        entities = []

        for entity_item in spec.entities:
            # Create cognitive tensor with initial knowledge
            knowledge_state = entity_item.initial_knowledge
            cognitive = CognitiveTensor(
                knowledge_state=knowledge_state,
                energy_budget=100.0,
                decision_confidence=0.8
            )

            # Get resolution level
            resolution = resolution_assignments.get(
                entity_item.entity_id,
                ResolutionLevel.SCENE
            )

            # Get first timepoint for temporal assignment
            first_tp = spec.timepoints[0] if spec.timepoints else None

            entity = Entity(
                entity_id=entity_item.entity_id,
                entity_type=entity_item.entity_type,
                timepoint=first_tp.timepoint_id if first_tp else None,
                resolution_level=resolution,
                entity_metadata={
                    "cognitive_tensor": cognitive.model_dump(),
                    "role": entity_item.role,
                    "description": entity_item.description,
                    "scene_context": spec.global_context,
                    "orchestrated": True
                }
            )

            entities.append(entity)

        print(f"   ✓ Created {len(entities)} entity objects")
        return entities

    def _create_timepoints(self, spec: SceneSpecification) -> List[Timepoint]:
        """Create Timepoint objects from specification"""
        timepoints = []

        for tp_spec in spec.timepoints:
            timestamp = datetime.fromisoformat(tp_spec.timestamp)

            timepoint = Timepoint(
                timepoint_id=tp_spec.timepoint_id,
                timestamp=timestamp,
                event_description=tp_spec.event_description,
                entities_present=tp_spec.entities_present,
                causal_parent=tp_spec.causal_parent,
                resolution_level=ResolutionLevel.SCENE,  # Default
                timepoint_metadata={
                    "importance": tp_spec.importance,
                    "orchestrated": True
                }
            )

            timepoints.append(timepoint)

        print(f"   ✓ Created {len(timepoints)} timepoint objects")
        return timepoints


# ============================================================================
# Convenience Functions
# ============================================================================

def simulate_event(
    event_description: str,
    llm_client: LLMClient,
    store: GraphStore,
    context: Optional[Dict] = None,
    save_to_db: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for complete event simulation.

    Usage:
        from orchestrator import simulate_event
        result = simulate_event(
            "simulate the constitutional convention",
            llm_client,
            store
        )

    Returns orchestration result with entities, timepoints, graph, etc.
    """
    orchestrator = OrchestratorAgent(llm_client, store)
    return orchestrator.orchestrate(event_description, context, save_to_db)
