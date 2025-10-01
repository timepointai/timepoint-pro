
# ============================================================================
# workflows.py - LangGraph workflow definitions
# ============================================================================
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
import networkx as nx
import json

from schemas import Entity, ResolutionLevel, TTMTensor
from llm import LLMClient
from storage import GraphStore
from graph import create_test_graph
from validation import Validator
from tensors import TensorCompressor

class WorkflowState(TypedDict):
    graph: nx.Graph
    entities: List[Entity]
    timepoint: str
    resolution: ResolutionLevel
    violations: List[Dict]
    results: Dict

def create_entity_training_workflow(llm_client: LLMClient, store: GraphStore):
    """LangGraph workflow for parallel entity training"""
    workflow = StateGraph(WorkflowState)
    
    def load_graph(state: WorkflowState) -> WorkflowState:
        # Only create/load a graph if one doesn't already exist in state
        if state["graph"] is None or state["graph"].number_of_nodes() == 0:
            graph = store.load_graph(state["timepoint"])
            if graph is None:
                graph = create_test_graph()
            state["graph"] = graph
        return state
    
    def populate_entities(state: WorkflowState) -> WorkflowState:
        results = []
        for node in state["graph"].nodes():
            entity_schema = {"entity_id": node, "timestamp": state["timepoint"]}
            context = {"exposure_history": [], "graph": state["graph"]}
            population = llm_client.populate_entity(entity_schema, context)
            results.append(population)
        state["results"] = {"populations": results}
        return state
    
    def validate_entities(state: WorkflowState) -> WorkflowState:
        violations = []
        for entity in state["entities"]:
            context = {"exposure_history": [], "graph": state["graph"]}
            entity_violations = Validator.validate_all(entity, context)
            violations.extend(entity_violations)
        state["violations"] = violations
        return state
    
    def compress_tensors(state: WorkflowState) -> WorkflowState:
        from schemas import ResolutionLevel

        for entity in state["entities"]:
            if entity.tensor:
                ttm = TTMTensor(**json.loads(entity.tensor))
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

        return state
    
    workflow.add_node("load_graph", load_graph)
    workflow.add_node("populate_entities", populate_entities)
    workflow.add_node("validate_entities", validate_entities)
    workflow.add_node("compress_tensors", compress_tensors)
    
    workflow.add_edge("load_graph", "populate_entities")
    workflow.add_edge("populate_entities", "validate_entities")
    workflow.add_edge("validate_entities", "compress_tensors")
    workflow.add_edge("compress_tensors", END)
    
    workflow.set_entry_point("load_graph")
    
    return workflow.compile()
