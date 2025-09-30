# ============================================================================
# cli.py - Hydra CLI for autopilot and steering
# ============================================================================
import hydra
from omegaconf import DictConfig
from pathlib import Path
from datetime import datetime

# Import all required modules
import networkx as nx
from storage import GraphStore
from llm import LLMClient
from workflows import create_entity_training_workflow, WorkflowState
from graph import create_test_graph, export_graph_data, print_graph_summary
from evaluation import EvaluationMetrics
from schemas import ResolutionLevel, Entity
from reporting import generate_report, generate_markdown_report


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """Main entry point with Hydra configuration"""

    # Initialize components
    store = GraphStore(cfg.database.url)
    llm_client = LLMClient(
        api_key=cfg.llm.api_key,
        base_url=cfg.llm.base_url,
        dry_run=cfg.llm.dry_run
    )

    # Add cost warning for real API calls
    if not llm_client.dry_run:
        print("\n" + "="*60)
        print("REAL LLM MODE ACTIVE - API calls will incur costs")
        print(f"API: {cfg.llm.base_url}")
        print("="*60 + "\n")
    
    # Run autopilot mode
    if cfg.mode == "autopilot":
        run_autopilot(cfg, store, llm_client)
    elif cfg.mode == "evaluate":
        run_evaluation(cfg, store, llm_client)
    elif cfg.mode == "train":
        if hasattr(cfg.training, 'context') and cfg.training.context:
            run_historical_training(cfg, store, llm_client)
        else:
            run_training(cfg, store, llm_client)
    else:
        print(f"Unknown mode: {cfg.mode}")

def run_autopilot(cfg: DictConfig, store: GraphStore, llm_client: LLMClient):
    """Autopilot self-testing mode"""
    print(f"\n{'='*70}")
    print(f"AUTOPILOT MODE: {cfg.autopilot.depth}")
    print(f"{'='*70}\n")

    graph_sizes = cfg.autopilot.graph_sizes
    results = []

    for idx, size in enumerate(graph_sizes, 1):
        print(f"[{idx}/{len(graph_sizes)}] Testing graph size: {size} entities")
        print("-" * 70)

        graph = create_test_graph(n_entities=size, seed=cfg.seed)
        print(f"  Graph created: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

        # Export graph for visualization
        export_graph_data(graph, f"reports/graph_size_{size}")

        workflow = create_entity_training_workflow(llm_client, store)

        state = WorkflowState(
            graph=graph,
            entities=[],
            timepoint=datetime.now().isoformat(),
            resolution=ResolutionLevel.TENSOR_ONLY,
            violations=[],
            results={}
        )

        print(f"  Running workflow...")
        final_state = workflow.invoke(state)

        # Analyze results
        violations = final_state["violations"]
        populations = final_state.get("results", {}).get("populations", [])

        print(f"  Entities populated: {len(populations)}")
        print(f"  Violations detected: {len(violations)}")

        if violations:
            print(f"  Violation types:")
            for v in violations[:3]:  # Show first 3
                print(f"    - [{v['severity']}] {v['validator']}: {v['message']}")

        result = {
            "graph_size": size,
            "entities": len(populations),
            "violations": len(violations),
            "cost": llm_client.cost,
            "tokens": llm_client.token_count
        }
        results.append(result)
        print(f"  Cost so far: ${llm_client.cost:.4f} ({llm_client.token_count} tokens)")
        print()

    # Summary
    print("="*70)
    print("AUTOPILOT SUMMARY")
    print("="*70)
    print(f"{'Size':<10} {'Entities':<12} {'Violations':<15} {'Cost':<15} {'Tokens'}")
    print("-" * 70)

    for result in results:
        print(f"{result['graph_size']:<10} {result['entities']:<12} {result['violations']:<15} "
              f"${result['cost']:<14.4f} {result['tokens']}")

    total_cost = llm_client.cost
    total_tokens = llm_client.token_count
    print("-" * 70)
    print(f"{'TOTAL':<10} {'':<12} {'':<15} ${total_cost:<14.4f} {total_tokens}")
    print("="*70 + "\n")

    # Generate reports
    report_results = {
        "runs": results,
        "cost": total_cost,
        "tokens": total_tokens,
        "timestamp": datetime.now().isoformat()
    }
    generate_report("autopilot", report_results)
    generate_markdown_report("autopilot", report_results)

    return results

def run_evaluation(cfg: DictConfig, store: GraphStore, llm_client: LLMClient):
    """Run evaluation metrics"""
    from sqlmodel import Session, select

    evaluator = EvaluationMetrics(store)

    # Load ALL entities from database (not hardcoded IDs)
    with Session(store.engine) as session:
        entities = session.exec(select(Entity)).all()

    if not entities:
        print("No entities found in database. Run 'mode=train' first to create entities.")
        return

    print(f"\nEvaluating {len(entities)} entities:\n")

    # Compute metrics for each entity
    for entity in entities:
        coherence = evaluator.temporal_coherence_score(entity, [datetime.now()])
        consistency = evaluator.knowledge_consistency_score(entity, {"exposure_history": []})
        plausibility = evaluator.biological_plausibility_score(entity, [])

        print(f"  {entity.entity_id}:")
        print(f"    Temporal Coherence:     {coherence:.2f}")
        print(f"    Knowledge Consistency:  {consistency:.2f}")
        print(f"    Biological Plausibility: {plausibility:.2f}")
        print()

    # Generate reports
    eval_results = {
        "entities_evaluated": len(entities),
        "cost": llm_client.cost,
        "tokens": llm_client.token_count
    }
    generate_report("evaluation", eval_results)
    generate_markdown_report("evaluation", eval_results)

def run_training(cfg: DictConfig, store: GraphStore, llm_client: LLMClient):
    """Run entity training workflow"""
    graph = create_test_graph(n_entities=cfg.training.graph_size, seed=cfg.seed)
    print_graph_summary(graph)
    workflow = create_entity_training_workflow(llm_client, store)

    state = WorkflowState(
        graph=graph,
        entities=[],
        timepoint=datetime.now().isoformat(),
        resolution=ResolutionLevel(cfg.training.target_resolution),
        violations=[],
        results={}
    )

    final_state = workflow.invoke(state)

    # NEW: Save populated entities to database
    if "results" in final_state and "populations" in final_state["results"]:
        print(f"\nSaving {len(final_state['results']['populations'])} entities to database...")

        for population in final_state["results"]["populations"]:
            entity = Entity(
                entity_id=population.entity_id,
                entity_type="person",
                entity_metadata={
                    "knowledge_state": population.knowledge_state,
                    "energy_budget": population.energy_budget,
                    "personality_traits": population.personality_traits,
                    "temporal_awareness": population.temporal_awareness,
                    "confidence": population.confidence
                }
            )
            store.save_entity(entity)
            print(f"  Saved: {entity.entity_id}")

    # Compute graph metrics
    import networkx as nx
    from tensors import compute_ttm_metrics

    centralities = nx.eigenvector_centrality(graph)
    top_entities = sorted(centralities.items(), key=lambda x: x[1], reverse=True)[:5]

    print(f"\nTop 5 Most Central Entities:")
    for entity_id, centrality in top_entities:
        print(f"  {entity_id}: {centrality:.4f}")

    print(f"\nTraining complete: {len(final_state['violations'])} violations")
    print(f"Total cost: ${llm_client.cost:.2f}")
    print(f"Tokens used: {llm_client.token_count}")

    # Generate reports
    training_results = {
        "entities_saved": len(final_state.get("results", {}).get("populations", [])),
        "violations": len(final_state['violations']),
        "cost": llm_client.cost,
        "tokens": llm_client.token_count,
        "graph_size": cfg.training.graph_size,
        "top_centralities": dict(top_entities)
    }
    generate_report("training", training_results)
    generate_markdown_report("training", training_results)

def run_historical_training(cfg: DictConfig, store: GraphStore, llm_client: LLMClient):
    """Train entities with rich historical context"""
    from entity_templates import HISTORICAL_CONTEXTS, get_context_prompt
    
    context_name = cfg.training.get("context", "founding_fathers_1789")
    context = HISTORICAL_CONTEXTS[context_name]
    
    print(f"\n{'='*70}")
    print(f"HISTORICAL CONTEXT: {context['event']}")
    print(f"Date: {context['timepoint']}")
    print(f"Entities: {len(context['entities'])}")
    print(f"{'='*70}\n")
    
    # Create graph with historical relationships
    graph = nx.Graph()
    
    for entity_data in context["entities"]:
        graph.add_node(
            entity_data["entity_id"],
            role=entity_data["role"],
            age=entity_data["age"],
            location=entity_data["location"]
        )
    
    for source, target, rel_type in context["relationships"]:
        graph.add_edge(source, target, relationship=rel_type)
    
    print(f"Graph structure:")
    print(f"  Nodes: {graph.number_of_nodes()}")
    print(f"  Edges: {graph.number_of_edges()}")
    print(f"  Relationships: {[r for _, _, r in context['relationships']]}\n")
    
    # Populate each entity with context-aware prompts
    print("Populating entities with historical context...\n")
    
    for entity_data in context["entities"]:
        entity_id = entity_data["entity_id"]
        
        # Enhanced context for LLM
        enhanced_context = {
            "historical_context": get_context_prompt(context_name),
            "entity_role": entity_data["role"],
            "entity_age": entity_data["age"],
            "entity_location": entity_data["location"],
            "timepoint": context["timepoint"],
            "event": context["event"],
            "relationships": [r for s, t, r in context["relationships"] if s == entity_id or t == entity_id]
        }
        
        population = llm_client.populate_entity(
            {"entity_id": entity_id, "timestamp": context["timepoint"]},
            enhanced_context
        )
        
        entity = Entity(
            entity_id=entity_id,
            entity_type="historical_person",
            temporal_span_start=datetime.fromisoformat(context["timepoint"]),
            entity_metadata={
                "role": entity_data["role"],
                "age": entity_data["age"],
                "location": entity_data["location"],
                "knowledge_state": population.knowledge_state,
                "energy_budget": population.energy_budget,
                "personality_traits": population.personality_traits,
                "temporal_awareness": population.temporal_awareness,
                "confidence": population.confidence,
                "historical_context": context["event"]
            }
        )
        
        store.save_entity(entity)
        print(f"  ✓ {entity_id} ({entity_data['role']})")
        print(f"    Age: {entity_data['age']}, Location: {entity_data['location']}")
        print(f"    Knowledge items: {len(population.knowledge_state)}")
        print(f"    Confidence: {population.confidence:.2f}\n")
    
    print(f"\nTraining complete!")
    print(f"Total cost: ${llm_client.cost:.4f}")
    print(f"Tokens used: {llm_client.token_count}")

if __name__ == "__main__":
    main()