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
from schemas import ResolutionLevel, Entity, ExposureEvent, Timepoint
from reporting import generate_report, generate_markdown_report
from temporal_chain import build_temporal_chain
from query_interface import QueryInterface
from tensors import TensorCompressor
from schemas import TTMTensor
from validation import Validator
import json

def _compress_entity_tensors(entity: Entity):
    """Compress entity tensors for storage efficiency (Mechanism 1.1)"""
    from schemas import ResolutionLevel

    # Create synthetic tensor data for demonstration
    # In practice, this would be actual tensor data from LLM embeddings
    import numpy as np
    context_tensor = np.random.randn(50)  # Simulated context vector
    biology_tensor = np.array([entity.entity_metadata.get("age", 50), 0.8, 0.7])  # age, health, energy
    behavior_tensor = np.random.randn(10)  # Personality traits

    # Apply compression based on resolution level
    if entity.resolution_level == ResolutionLevel.TENSOR_ONLY:
        # TENSOR_ONLY: Store ONLY compressed representation
        compressed = {
            "context_pca": TensorCompressor.compress(context_tensor, "pca"),
            "context_svd": TensorCompressor.compress(context_tensor, "svd"),
            "biology_pca": TensorCompressor.compress(biology_tensor, "pca"),
            "behavior_pca": TensorCompressor.compress(behavior_tensor, "pca")
        }
        entity.entity_metadata["compressed"] = {k: v.tolist() for k, v in compressed.items()}
        # Remove full tensor data to save space
        if hasattr(entity, 'tensor'):
            entity.tensor = None

    else:
        # Higher resolutions: Keep full tensor but also store compressed version
        compressed = {
            "context_pca": TensorCompressor.compress(context_tensor, "pca"),
            "context_svd": TensorCompressor.compress(context_tensor, "svd"),
            "biology_pca": TensorCompressor.compress(biology_tensor, "pca"),
            "behavior_pca": TensorCompressor.compress(behavior_tensor, "pca")
        }
        entity.entity_metadata["compressed"] = {k: v.tolist() for k, v in compressed.items()}
        # Keep full tensor for detailed operations


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """Main entry point with Hydra configuration"""

    # Initialize components
    store = GraphStore(cfg.database.url)
    llm_client = LLMClient(
        api_key=cfg.llm.api_key,
        base_url=cfg.llm.base_url,
        dry_run=cfg.llm.dry_run,
        default_model=cfg.llm.model,
        model_cache_ttl_hours=getattr(cfg.llm, 'model_cache_ttl_hours', 24)
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
    elif cfg.mode == "temporal_train":
        run_temporal_training(cfg, store, llm_client)
    elif cfg.mode == "interactive":
        run_interactive(cfg, store, llm_client)
    elif cfg.mode == "models":
        run_model_management(cfg, llm_client)
    else:
        print(f"Unknown mode: {cfg.mode}")

def run_model_management(cfg: DictConfig, llm_client: LLMClient):
    """Model management and selection interface"""
    print(f"\n{'='*60}")
    print("LLM MODEL MANAGEMENT")
    print(f"{'='*60}\n")

    print(f"Current model: {llm_client.default_model}")
    print(f"Available Llama models: {len(llm_client.model_manager.get_llama_models())}")

    # Show available models
    print("\n" + llm_client.model_manager.list_models_formatted())

    # Interactive model selection
    while True:
        print("\nModel Management Options:")
        print("1. Refresh model list from OpenRouter")
        print("2. Show detailed model info")
        print("3. Switch to a different model")
        print("4. Test current model")
        print("5. Exit")

        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "1":
            print("🔄 Refreshing model list...")
            models = llm_client.model_manager.get_llama_models(force_refresh=True)
            print(f"✅ Refreshed {len(models)} models")

        elif choice == "2":
            model_id = input("Enter model ID to see details: ").strip()
            models = llm_client.model_manager.get_llama_models()
            model_info = next((m for m in models if m["id"] == model_id), None)
            if model_info:
                print(f"\n📋 Model Details for {model_id}:")
                print(f"  Name: {model_info['name']}")
                print(f"  Description: {model_info['description']}")
                print(f"  Context Length: {model_info['context_length']:,} tokens")
                if model_info['pricing']:
                    print(f"  Pricing: {model_info['pricing']}")
            else:
                print(f"❌ Model '{model_id}' not found")

        elif choice == "3":
            model_id = input("Enter model ID to switch to: ").strip()
            if llm_client.model_manager.is_valid_model(model_id):
                # Update the default model
                llm_client.default_model = model_id
                print(f"✅ Switched to model: {model_id}")

                # Show confirmation
                print(f"🦙 Current model: {llm_client.default_model}")
            else:
                print(f"❌ Invalid model ID: {model_id}")

        elif choice == "4":
            if llm_client.dry_run:
                print("ℹ️  Dry-run mode - no actual API call will be made")
            else:
                print("🧪 Testing model with a simple query...")
                try:
                    # Test with a simple relevance scoring call
                    score = llm_client.score_relevance("test query", "test knowledge")
                    print(f"✅ Model test successful - relevance score: {score}")
                except Exception as e:
                    print(f"❌ Model test failed: {e}")

        elif choice == "5":
            print("👋 Exiting model management")
            break

        else:
            print("❌ Invalid choice. Please enter 1-5.")

def run_autopilot(cfg: DictConfig, store: GraphStore, llm_client: LLMClient):
    """Autopilot self-testing mode - now tests temporal chains"""
    print(f"\n{'='*70}")
    print(f"AUTOPILOT MODE: Temporal Chain Testing")
    print(f"{'='*70}\n")

    # Test temporal chains of different lengths
    temporal_lengths = cfg.autopilot.get("temporal_lengths", [3, 5, 7])
    results = []

    for idx, length in enumerate(temporal_lengths, 1):
        print(f"[{idx}/{len(temporal_lengths)}] Testing temporal chain: {length} timepoints")
        print("-" * 70)

        # Clean database for each test
        store._clear_database()

        print(f"  Building temporal chain with {length} timepoints...")
        timepoints = build_temporal_chain("founding_fathers_1789", length)
        print(f"  Created {len(timepoints)} timepoints with causal links")

        # Run temporal training
        print(f"  Running temporal training...")
        run_temporal_training(
            DictConfig({"training": {"context": "founding_fathers_1789", "num_timepoints": length}}),
            store, llm_client
        )

        # Run evaluation
        print(f"  Running evaluation...")
        evaluator = EvaluationMetrics(store)
        entities = store.get_all_entities()

        # Compute aggregate metrics
        total_coherence = 0
        total_consistency = 0
        total_plausibility = 0

        for entity in entities:
            coherence = evaluator.temporal_coherence_score(entity, [datetime.now()])
            consistency = evaluator.knowledge_consistency_score(entity, {})
            plausibility = evaluator.biological_plausibility_score(entity, [])
            total_coherence += coherence
            total_consistency += consistency
            total_plausibility += plausibility

        avg_coherence = total_coherence / len(entities) if entities else 0
        avg_consistency = total_consistency / len(entities) if entities else 0
        avg_plausibility = total_plausibility / len(entities) if entities else 0

        # Check causal consistency (timepoints should have proper causal links)
        causal_violations = 0
        for i, tp in enumerate(timepoints[1:], 1):  # Skip first timepoint
            if tp.causal_parent != timepoints[i-1].timepoint_id:
                causal_violations += 1

        # Count exposure events per entity
        exposure_counts = {}
        for entity in entities:
            exposure_counts[entity.entity_id] = len(store.get_exposure_events(entity.entity_id))

        print(f"  Entities: {len(entities)}")
        print(f"  Timepoints: {len(timepoints)}")
        print(f"  Avg Temporal Coherence: {avg_coherence:.2f}")
        print(f"  Avg Knowledge Consistency: {avg_consistency:.2f}")
        print(f"  Causal Chain Violations: {causal_violations}")
        print(f"  Exposure Events per Entity: {list(exposure_counts.values())[:3]}...")  # Show first 3

        result = {
            "temporal_length": length,
            "entities": len(entities),
            "timepoints": len(timepoints),
            "avg_temporal_coherence": avg_coherence,
            "avg_knowledge_consistency": avg_consistency,
            "avg_biological_plausibility": avg_plausibility,
            "causal_violations": causal_violations,
            "total_exposure_events": sum(exposure_counts.values()),
            "cost": llm_client.cost,
            "tokens": llm_client.token_count
        }
        results.append(result)
        print(f"  Cost so far: ${llm_client.cost:.4f} ({llm_client.token_count} tokens)")
        print()

    # Summary
    print("="*70)
    print("AUTOPILOT SUMMARY: Temporal Chain Testing")
    print("="*70)
    print(f"{'Length':<10} {'Entities':<12} {'Coherence':<12} {'Consistency':<14} {'Cost':<10}")
    print("-" * 70)

    for result in results:
        print(f"{result['temporal_length']:<10} {result['entities']:<12} {result['avg_temporal_coherence']:<12.2f} "
              f"{result['avg_knowledge_consistency']:<14.2f} ${result['cost']:<9.4f}")

    total_cost = sum(r['cost'] for r in results)
    total_tokens = sum(r['tokens'] for r in results)
    avg_coherence = sum(r['avg_temporal_coherence'] for r in results) / len(results) if results else 0
    avg_consistency = sum(r['avg_knowledge_consistency'] for r in results) / len(results) if results else 0
    print("-" * 70)
    print(f"{'AVERAGE':<10} {'':<12} {avg_coherence:<12.2f} {avg_consistency:<14.2f} ${total_cost:<9.4f}")
    print("="*70 + "\n")

    # Generate reports
    report_results = {
        "runs": results,
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "avg_coherence": avg_coherence,
        "avg_consistency": avg_consistency,
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

    # Compute resolution distribution
    resolution_counts = {}
    from schemas import ResolutionLevel
    for entity in entities:
        res_level = entity.resolution_level.value
        resolution_counts[res_level] = resolution_counts.get(res_level, 0) + 1

    # Generate reports
    eval_results = {
        "entities_evaluated": len(entities),
        "resolution_distribution": resolution_counts,
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

        # Record exposure events for each knowledge item
        exposure_events = []
        for knowledge_item in population.knowledge_state:
            exposure_event = ExposureEvent(
                entity_id=entity_id,
                event_type="witnessed",  # Historical figures witnessed the events
                information=knowledge_item,
                source=context["event"],  # The historical event was the source
                timestamp=datetime.fromisoformat(context["timepoint"]),
                confidence=population.confidence,
                timepoint_id=f"{context_name}_{context['timepoint']}"
            )
            exposure_events.append(exposure_event)

        # Batch insert exposure events
        store.save_exposure_events(exposure_events)
        print(f"  ✓ {entity_id} ({entity_data['role']})")
        print(f"    Age: {entity_data['age']}, Location: {entity_data['location']}")
        print(f"    Knowledge items: {len(population.knowledge_state)}")
        print(f"    Confidence: {population.confidence:.2f}\n")
    
    print(f"\nTraining complete!")
    print(f"Total cost: ${llm_client.cost:.4f}")
    print(f"Tokens used: {llm_client.token_count}")

def run_temporal_training(cfg: DictConfig, store: GraphStore, llm_client: LLMClient):
    """Train entities across a temporal chain with causal evolution"""
    from entity_templates import HISTORICAL_CONTEXTS, get_context_prompt

    context_name = cfg.training.get("context", "founding_fathers_1789")
    num_timepoints = cfg.training.get("num_timepoints", 5)

    print(f"\n{'='*70}")
    print(f"TEMPORAL TRAINING: {context_name}")
    print(f"Timepoints: {num_timepoints}")
    print(f"{'='*70}\n")

    # Build temporal chain
    print("Building temporal chain...")
    timepoints = build_temporal_chain(context_name, num_timepoints)
    print(f"Created {len(timepoints)} timepoints with causal links")

    # Save timepoints to database
    for timepoint in timepoints:
        store.save_timepoint(timepoint)
        print(f"  ✓ {timepoint.timepoint_id}: {timepoint.event_description[:60]}...")

    print()

    # Process each timepoint in sequence
    context = HISTORICAL_CONTEXTS[context_name]
    entities_data = context["entities"]

    for i, timepoint in enumerate(timepoints):
        print(f"Timepoint {i+1}/{len(timepoints)}: {timepoint.timepoint_id}")
        print(f"  Event: {timepoint.event_description}")
        print(f"  Timestamp: {timepoint.timestamp}")
        print(f"  Resolution: {timepoint.resolution_level.value}")
        print(f"  Entities: {len(timepoint.entities_present)}")
        print()

        # Populate each entity at this timepoint
        for entity_data in entities_data:
            entity_id = entity_data["entity_id"]

            # Get previous knowledge state (causal propagation)
            previous_knowledge = None
            if timepoint.causal_parent:
                previous_knowledge = store.get_entity_knowledge_at_timepoint(entity_id, timepoint.causal_parent)

            # Enhanced context for this timepoint
            enhanced_context = {
                "historical_context": get_context_prompt(context_name),
                "entity_role": entity_data["role"],
                "entity_age": entity_data["age"],
                "entity_location": entity_data["location"],
                "timepoint": timepoint.timestamp.isoformat(),
                "event": timepoint.event_description,
                "timepoint_id": timepoint.timepoint_id,
                "relationships": [r for s, t, r in context["relationships"] if s == entity_id or t == entity_id]
            }

            # Populate entity with causal context
            population = llm_client.populate_entity(
                {"entity_id": entity_id, "timestamp": timepoint.timestamp.isoformat()},
                enhanced_context,
                previous_knowledge
            )

            # Update or create entity record (only create if this is the first timepoint)
            entity = store.get_entity(entity_id)
            if entity is None:
                # First timepoint - create new entity
                entity = Entity(
                    entity_id=entity_id,
                    entity_type="historical_person",
                    temporal_span_start=timepoint.timestamp,
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

                # Compress tensors for storage efficiency (Mechanism 1.1)
                _compress_entity_tensors(entity)
                store.save_entity(entity)  # Save again with compressed data

                # Enforce validators in temporal evolution (Mechanism 1.2)
                # Build knowledge map for network flow validation
                all_entity_knowledge = {}
                for eid, entity in entities.items():
                    all_entity_knowledge[eid] = entity.entity_metadata.get("knowledge_state", [])

                validation_context = {
                    "previous_knowledge": [],  # First timepoint, no previous knowledge
                    "previous_personality": [],  # No previous personality
                    "timepoint": timepoint,
                    "timepoint_id": timepoint.timepoint_id,  # For temporal causality validation
                    "store": store,
                    "graph": graph,  # For network flow validation
                    "all_entity_knowledge": all_entity_knowledge,  # For network flow validation
                    "exposure_history": []  # Could be populated from exposure events
                }
                violations = Validator.validate_all(entity, validation_context)
                if violations:
                    for violation in violations:
                        print(f"  ⚠️  VALIDATION {violation['severity']}: {entity_id} - {violation['message']}")

            else:
                # Subsequent timepoint - update knowledge state
                current_knowledge = set(entity.entity_metadata.get("knowledge_state", []))
                new_knowledge = set(population.knowledge_state)
                # Only add truly new knowledge
                added_knowledge = new_knowledge - current_knowledge
                if added_knowledge:
                    # Store previous state for validation
                    previous_knowledge = entity.entity_metadata.get("knowledge_state", [])
                    previous_personality = entity.entity_metadata.get("personality_traits", [])

                    updated_knowledge = entity.entity_metadata["knowledge_state"] + list(added_knowledge)
                    entity.entity_metadata["knowledge_state"] = updated_knowledge
                    store.save_entity(entity)

            # Compress tensors for storage efficiency (Mechanism 1.1)
            _compress_entity_tensors(entity)
            store.save_entity(entity)  # Save again with compressed data

            # Enforce validators in temporal evolution (Mechanism 1.2)
            # Build knowledge map for network flow validation
            all_entity_knowledge = {}
            for eid, entity in entities.items():
                all_entity_knowledge[eid] = entity.entity_metadata.get("knowledge_state", [])

            validation_context = {
                "previous_knowledge": previous_knowledge if 'previous_knowledge' in locals() else [],
                "previous_personality": previous_personality if 'previous_personality' in locals() else [],
                "timepoint": timepoint,
                "timepoint_id": timepoint.timepoint_id,  # For temporal causality validation
                "store": store,
                "graph": graph,  # For network flow validation
                "all_entity_knowledge": all_entity_knowledge,  # For network flow validation
                "exposure_history": []  # Could be populated from exposure events
            }
            violations = Validator.validate_all(entity, validation_context)
            if violations:
                for violation in violations:
                    print(f"  ⚠️  VALIDATION {violation['severity']}: {entity_id} - {violation['message']}")
                    # For ERROR severity, we could block the update, but for now just log

            # Record exposure events for new knowledge
            exposure_events = []
            for knowledge_item in population.knowledge_state:
                # Only create exposure event if this is new knowledge or first timepoint
                if (previous_knowledge is None or
                    knowledge_item not in previous_knowledge):
                    exposure_event = ExposureEvent(
                        entity_id=entity_id,
                        event_type="experienced",  # They experienced the event at this timepoint
                        information=knowledge_item,
                        source=timepoint.event_description,
                        timestamp=timepoint.timestamp,
                        confidence=population.confidence,
                        timepoint_id=timepoint.timepoint_id
                    )
                    exposure_events.append(exposure_event)

            if exposure_events:
                store.save_exposure_events(exposure_events)

            knowledge_growth = len(population.knowledge_state) - (len(previous_knowledge) if previous_knowledge else 0)
            print(f"  ✓ {entity_id}: +{knowledge_growth} knowledge items")

        print()

    print(f"Temporal training complete!")
    print(f"Total cost: ${llm_client.cost:.4f}")
    print(f"Timepoints processed: {len(timepoints)}")

def run_interactive(cfg: DictConfig, store: GraphStore, llm_client: LLMClient):
    """Interactive query REPL for the temporal simulation"""
    query_interface = QueryInterface(store, llm_client)

    print(f"\n{'='*70}")
    print("TEMPORAL SIMULATION INTERACTIVE QUERY INTERFACE")
    print(f"{'='*70}")
    print("\nYou can ask questions about entities in the temporal simulation.")
    print("Examples:")
    print("  'What did George Washington think about becoming president?'")
    print("  'How did Thomas Jefferson feel about the inauguration?'")
    print("  'What actions did Alexander Hamilton take during the ceremony?'")
    print("\nType 'help' for more examples, 'exit' or 'quit' to leave.\n")

    while True:
        try:
            query = input("Query: ").strip()

            if not query:
                continue

            if query.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye! 👋")
                break

            if query.lower() in ['help', 'h', '?']:
                _show_interactive_help()
                continue

            if query.lower() == 'status':
                _show_simulation_status(store, llm_client)
                continue

            if query.lower() == 'models':
                run_model_management(cfg, llm_client)
                continue

            # Parse and respond to query
            print("  Parsing query...")
            intent = query_interface.parse_query(query)
            print(f"  Intent: {intent.information_type} about {intent.target_entity or 'unknown'} (confidence: {intent.confidence:.1f})")

            print("  Synthesizing response...")
            response = query_interface.synthesize_response(intent)

            print(f"\nResponse:\n{response}")
            print(f"\nCost so far: ${llm_client.cost:.4f}\n")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit or continue asking questions.")
        except Exception as e:
            print(f"Error processing query: {e}")
            print("Try again or type 'help' for guidance.\n")

def _show_interactive_help():
    """Show help text for interactive mode"""
    help_text = """
Available commands:
  help, h, ?     Show this help
  status         Show simulation status and statistics
  models         Manage LLM models (list, switch, test)
  exit, quit, q  Leave the interactive interface

Query examples:
  "What did George Washington think about becoming president?"
  "How did Thomas Jefferson feel during the inauguration?"
  "What actions did Alexander Hamilton take after the ceremony?"
  "Tell me about James Madison's thoughts on the new government"
  "What was John Adams' reaction to the presidential oath?"

The system will automatically:
- Parse your natural language query
- Identify relevant entities and timepoints
- Elevate resolution if needed for detailed responses
- Provide attribution showing knowledge sources
- Track query history for better future responses

Note: The system uses causal temporal simulation where entities evolve over timepoints.
"""
    print(help_text)

def _show_simulation_status(store: GraphStore, llm_client):
    """Show current simulation status"""
    entities = store.get_all_entities() if hasattr(store, 'get_all_entities') else []
    timepoints = store.get_all_timepoints()

    print(f"\nSimulation Status:")
    print(f"  Entities: {len(entities)}")
    print(f"  Timepoints: {len(timepoints)}")
    print(f"  Total cost: ${llm_client.cost:.4f}")
    print(f"  Tokens used: {llm_client.token_count}")

    if timepoints:
        print(f"  Latest timepoint: {timepoints[-1].timepoint_id}")
        print(f"    Event: {timepoints[-1].event_description[:60]}...")

    if entities:
        resolution_counts = {}
        for entity in entities:
            res = entity.resolution_level.value
            resolution_counts[res] = resolution_counts.get(res, 0) + 1

        print(f"  Resolution distribution:")
        for res, count in resolution_counts.items():
            print(f"    {res}: {count} entities")

    print()

if __name__ == "__main__":
    main()