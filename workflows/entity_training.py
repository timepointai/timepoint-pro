# ============================================================================
# workflows/entity_training.py - LangGraph workflow for entity training
# ============================================================================
"""
Entity training workflow using LangGraph.

Contains:
- WorkflowState: TypedDict for workflow state
- create_entity_training_workflow: Main LangGraph workflow
- retrain_high_traffic_entities: Progressive training for high-usage entities
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Optional
import networkx as nx
import json

from schemas import Entity, ResolutionLevel, TTMTensor
from llm_v2 import LLMClient
from schemas import EntityPopulation
from resolution_engine import ResolutionEngine
from storage import GraphStore
from graph import create_test_graph
from validation import Validator
from tensors import TensorCompressor
from metadata.tracking import track_mechanism


class WorkflowState(TypedDict):
    graph: nx.Graph
    entities: List[Entity]
    timepoint: str
    resolution: ResolutionLevel
    violations: List[Dict]
    results: Dict
    entity_populations: Dict[str, EntityPopulation]  # Parallel entity results


def create_entity_training_workflow(llm_client: LLMClient, store: GraphStore):
    """LangGraph workflow for parallel entity training"""
    workflow = StateGraph(WorkflowState)

    @track_mechanism("M2", "progressive_training_elevation")
    def progressive_training_check(state: WorkflowState) -> WorkflowState:
        """Check for entities that need progressive training elevation (Mechanism 2.4)"""
        resolution_engine = ResolutionEngine(store, llm_client)

        elevation_candidates = []
        for entity in state["entities"]:
            if resolution_engine.check_retraining_needed(entity, state["graph"]):
                elevation_candidates.append(entity)

        if elevation_candidates:
            print(f"🎯 Progressive training: {len(elevation_candidates)} entities need elevation")

            for entity in elevation_candidates:
                current_level_value = list(ResolutionLevel).index(entity.resolution_level)
                if current_level_value < len(ResolutionLevel) - 1:
                    target_level = list(ResolutionLevel)[current_level_value + 1]
                    # Pass timepoint for knowledge enrichment context
                    timepoint_obj = state.get("timepoint_obj")
                    if resolution_engine.elevate_resolution(entity, target_level, timepoint_obj):
                        print(f"⬆️ Elevated {entity.entity_id} to {target_level.value}")
        else:
            print("✅ No entities need progressive training elevation")

        return state

    def load_graph(state: WorkflowState) -> WorkflowState:
        # Only create/load a graph if one doesn't already exist in state
        if state["graph"] is None or state["graph"].number_of_nodes() == 0:
            graph = store.load_graph(state["timepoint"])
            if graph is None:
                graph = create_test_graph()
            state["graph"] = graph
        return state

    def aggregate_populations(state: WorkflowState) -> WorkflowState:
        """Aggregate parallel entity populations into entities list, preserving existing metadata"""
        # Get existing entities from state (may have been created by orchestrator with rich metadata)
        existing_entities = state.get("entities", [])
        existing_entities_map = {e.entity_id: e for e in existing_entities}

        # PART 1 FIX: Check if entities are orchestrated - if so, skip LLM population merge
        if existing_entities and all(e.entity_metadata.get("orchestrated", False) for e in existing_entities):
            print("  ✓ Skipping LLM population for orchestrated entities (preserving orchestrator metadata)")
            state["entities"] = existing_entities
            state["results"] = {"populations": []}
            return state

        populations = state.get("entity_populations", {})
        updated_entities = []

        for entity_id, population in populations.items():
            # Check if entity already exists with metadata from orchestrator
            existing_entity = existing_entities_map.get(entity_id)

            if existing_entity:
                # PRESERVE existing metadata, UPDATE cognitive_tensor with new LLM data
                import copy
                existing_metadata = copy.deepcopy(existing_entity.entity_metadata)

                # PART 2 FIX: Backup physical_tensor before any updates
                physical_tensor_backup = None
                if "physical_tensor" in existing_metadata:
                    physical_tensor_backup = copy.deepcopy(existing_metadata["physical_tensor"])

                # Update cognitive_tensor dict (don't overwrite top-level keys)
                if "cognitive_tensor" in existing_metadata:
                    existing_metadata["cognitive_tensor"].update({
                        "knowledge_state": population.knowledge_state,
                        "energy_budget": population.energy_budget,
                        "decision_confidence": population.confidence
                    })
                else:
                    # No cognitive tensor yet - create one
                    from schemas import CognitiveTensor
                    cognitive = CognitiveTensor(
                        knowledge_state=population.knowledge_state,
                        energy_budget=population.energy_budget,
                        decision_confidence=population.confidence
                    )
                    existing_metadata["cognitive_tensor"] = cognitive.model_dump()

                # Update other metadata fields
                existing_metadata.update({
                    "personality_traits": population.personality_traits,
                    "temporal_awareness": population.temporal_awareness,
                    "current_timepoint": state["timepoint"]
                })

                # PART 2 FIX: Restore physical_tensor after updates
                if physical_tensor_backup is not None:
                    existing_metadata["physical_tensor"] = physical_tensor_backup

                # Create updated entity preserving type, resolution, and ALL metadata
                entity = Entity(
                    entity_id=entity_id,
                    entity_type=existing_entity.entity_type,
                    temporal_span_start=existing_entity.temporal_span_start,
                    temporal_span_end=existing_entity.temporal_span_end,
                    resolution_level=existing_entity.resolution_level,
                    entity_metadata=existing_metadata
                )
            else:
                # Create new entity (no existing metadata to preserve)
                entity = Entity(
                    entity_id=entity_id,
                    entity_type="historical_person",
                    temporal_span_start=None,
                    temporal_span_end=None,
                    resolution_level=state["resolution"],
                    entity_metadata={
                        "knowledge_state": population.knowledge_state,
                        "energy_budget": population.energy_budget,
                        "personality_traits": population.personality_traits,
                        "temporal_awareness": population.temporal_awareness,
                        "confidence": population.confidence,
                        "current_timepoint": state["timepoint"]
                    }
                )

            # Generate TTM tensor for entity (Phase 7)
            from tensors import generate_ttm_tensor
            tensor_json = generate_ttm_tensor(entity)
            if tensor_json:
                entity.tensor = tensor_json

            updated_entities.append(entity)

        state["entities"] = updated_entities
        state["results"] = {"populations": list(populations.values())}
        return state

    def validate_entities(state: WorkflowState) -> WorkflowState:
        violations = []

        # Build knowledge map for network flow validation
        all_entity_knowledge = {}
        for entity in state["entities"]:
            all_entity_knowledge[entity.entity_id] = entity.entity_metadata.get("knowledge_state", [])

        # Build circadian config for M14 (Circadian Patterns) tracking
        from datetime import datetime
        circadian_config = {
            "energy_multipliers": {
                "base_fatigue_threshold": 16,
                "night_penalty": 1.5,
                "fatigue_accumulation": 0.5
            },
            "activity_probabilities": {
                "work": {"hours": list(range(8, 18)), "probability": 0.8},
                "sleep": {"hours": list(range(22, 24)) + list(range(0, 6)), "probability": 0.9}
            }
        }

        # Get timepoint object if available
        timepoint_obj = state.get("timepoint_obj")

        for entity in state["entities"]:
            context = {
                "exposure_history": [],  # Could be populated from exposure events
                "graph": state["graph"],
                "all_entity_knowledge": all_entity_knowledge,
                "previous_knowledge": [],  # Could be populated from previous timepoint data
                "previous_personality": [],  # Could be populated from previous timepoint data
                "timepoint_id": state["timepoint"],  # For temporal causality validation
                "timepoint": timepoint_obj,  # For circadian validation
                "circadian_config": circadian_config,  # For M14 tracking
                "activity_type": "work",  # Default activity type for validation
                "store": None  # Would need to be passed in for full validation
            }
            entity_violations = Validator.validate_all(entity, context)
            violations.extend(entity_violations)
        state["violations"] = violations
        return state

    def compress_tensors(state: WorkflowState) -> WorkflowState:
        from schemas import ResolutionLevel
        import logging

        logger = logging.getLogger(__name__)
        entities_compressed = 0
        entities_missing_tensor = []

        for entity in state["entities"]:
            # Phase 7: Expect all entities to have tensor attribute (now generated in pipeline)
            if not hasattr(entity, 'tensor') or entity.tensor is None:
                entities_missing_tensor.append(entity.entity_id)
                logger.error(f"Entity {entity.entity_id} missing tensor attribute - pipeline error")
                continue

            try:
                # Deserialize tensor from base64-encoded JSON
                import base64
                tensor_dict = json.loads(entity.tensor)
                ttm = TTMTensor(
                    context_vector=base64.b64decode(tensor_dict['context_vector']),
                    biology_vector=base64.b64decode(tensor_dict['biology_vector']),
                    behavior_vector=base64.b64decode(tensor_dict['behavior_vector'])
                )
                context, biology, behavior = ttm.to_arrays()

                # Apply compression based on resolution level
                if entity.resolution_level == ResolutionLevel.TENSOR_ONLY:
                    # TENSOR_ONLY: Store ONLY compressed representation
                    compressed = {
                        "pca": TensorCompressor.compress(context, "pca"),
                        "svd": TensorCompressor.compress(context, "svd")
                    }
                    entity.entity_metadata["compressed"] = {k: v.tolist() for k, v in compressed.items()}
                    # Remove full tensor data to save space
                    entity.tensor = None

                else:
                    # Higher resolutions: Keep full tensor but also store compressed version
                    compressed = {
                        "pca": TensorCompressor.compress(context, "pca"),
                        "svd": TensorCompressor.compress(context, "svd")
                    }
                    entity.entity_metadata["compressed"] = {k: v.tolist() for k, v in compressed.items()}
                    # Keep full tensor for detailed operations

                entities_compressed += 1
            except Exception as e:
                logger.error(f"Failed to compress tensor for {entity.entity_id}: {e}")
                entities_missing_tensor.append(entity.entity_id)

        if entities_missing_tensor:
            logger.warning(f"⚠️  {len(entities_missing_tensor)} entities missing tensors: {entities_missing_tensor}")

        if entities_compressed > 0:
            print(f"✓ Compressed tensors for {entities_compressed}/{len(state['entities'])} entities")

        return state

    def populate_entities_parallel(state: WorkflowState) -> WorkflowState:
        """Populate all entities in parallel using asyncio"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        async def populate_entity_async(entity_id: str) -> tuple[str, EntityPopulation]:
            """Async wrapper for entity population"""
            entity_schema = {"entity_id": entity_id, "timestamp": state["timepoint"]}
            context = {"exposure_history": [], "graph": state["graph"]}
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                population = await loop.run_in_executor(
                    executor,
                    lambda: llm_client.populate_entity(entity_schema, context)
                )
            return entity_id, population

        async def populate_all_entities():
            """Populate all entities concurrently"""
            entity_ids = list(state["graph"].nodes())
            tasks = [populate_entity_async(entity_id) for entity_id in entity_ids]
            results = await asyncio.gather(*tasks)
            return dict(results)

        # Run the async population
        populations = asyncio.run(populate_all_entities())
        state["entity_populations"] = populations
        return state

    def trigger_prospection_batch(state: WorkflowState) -> WorkflowState:
        """Trigger prospection (M15) for eligible entities in the training batch."""
        from prospection_triggers import trigger_prospection_for_entity, refine_tensor_from_prospection

        timepoint_obj = state.get("timepoint_obj")
        if not timepoint_obj:
            return state

        triggered = 0
        for entity in state["entities"]:
            try:
                # Use empty config dict — should_trigger_prospection handles missing fields
                prospective_state = trigger_prospection_for_entity(
                    entity, timepoint_obj, llm_client, store, {}
                )
                if prospective_state:
                    refine_tensor_from_prospection(entity, prospective_state)
                    triggered += 1
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"[M15] Prospection failed for {entity.entity_id}: {e}"
                )

        if triggered > 0:
            print(f"✨ Prospection triggered for {triggered}/{len(state['entities'])} entities")

        return state

    workflow.add_node("load_graph", load_graph)
    workflow.add_node("populate_entities_parallel", populate_entities_parallel)
    workflow.add_node("aggregate_populations", aggregate_populations)
    workflow.add_node("validate_entities", validate_entities)
    workflow.add_node("compress_tensors", compress_tensors)
    workflow.add_node("trigger_prospection_batch", trigger_prospection_batch)
    workflow.add_node("progressive_training_check", progressive_training_check)

    workflow.add_edge("load_graph", "populate_entities_parallel")
    workflow.add_edge("populate_entities_parallel", "aggregate_populations")
    workflow.add_edge("aggregate_populations", "validate_entities")
    workflow.add_edge("validate_entities", "compress_tensors")
    workflow.add_edge("compress_tensors", "trigger_prospection_batch")
    workflow.add_edge("trigger_prospection_batch", "progressive_training_check")
    workflow.add_edge("progressive_training_check", END)

    workflow.set_entry_point("load_graph")

    return workflow.compile()


@track_mechanism("M2", "progressive_training")
def retrain_high_traffic_entities(graph: nx.Graph, store: GraphStore, llm_client: LLMClient):
    """
    Progressive training: Check all entities and retrain/elevate those that need it
    based on centrality scores and query patterns (Mechanism 2.4)
    """
    resolution_engine = ResolutionEngine(store, llm_client)
    entities = store.get_all_entities()

    retrained_count = 0
    elevated_count = 0

    for entity in entities:
        if resolution_engine.check_retraining_needed(entity, graph):
            print(f"🔄 Retraining needed for {entity.entity_id} (centrality: {entity.eigenvector_centrality:.3f}, queries: {entity.query_count}, training: {entity.training_count})")

            # Determine target resolution based on centrality and usage
            current_level_value = list(ResolutionLevel).index(entity.resolution_level)

            # High centrality entities get higher priority elevation
            if entity.eigenvector_centrality > 0.5:
                target_level = min(ResolutionLevel.TRAINED,
                                 list(ResolutionLevel)[current_level_value + 2])  # Skip one level
            elif entity.eigenvector_centrality > 0.3:
                target_level = min(ResolutionLevel.TRAINED,
                                 list(ResolutionLevel)[current_level_value + 1])  # Next level
            else:
                # Query-driven elevation (more conservative)
                target_level = min(ResolutionLevel.TRAINED,
                                 list(ResolutionLevel)[current_level_value + 1])

            # Attempt elevation
            if resolution_engine.elevate_resolution(entity, target_level):
                elevated_count += 1
                print(f"⬆️ Elevated {entity.entity_id} to {target_level.value}")
            else:
                print(f"⚠️ Failed to elevate {entity.entity_id}")

    print(f"🎯 Progressive training complete: {elevated_count} entities elevated, {retrained_count} retrained")
    return elevated_count, retrained_count
