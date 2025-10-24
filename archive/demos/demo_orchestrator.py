#!/usr/bin/env python3
"""
demo_orchestrator.py - Demonstration of OrchestratorAgent Usage

This script demonstrates how to use the OrchestratorAgent to automatically
generate complete scene specifications from natural language descriptions.

Usage:
    # Dry run mode (for testing, no API calls):
    python demo_orchestrator.py --dry-run

    # Real LLM mode (requires OPENROUTER_API_KEY in .env):
    python demo_orchestrator.py

    # Custom event:
    python demo_orchestrator.py --event "simulate the signing of the magna carta"
"""

import os
import argparse
from dotenv import load_dotenv

from orchestrator import OrchestratorAgent, simulate_event
from llm import LLMClient
from storage import GraphStore

# Load environment variables
load_dotenv()


def demo_basic_usage(dry_run=True):
    """Demonstrate basic orchestrator usage"""
    print("\n" + "="*70)
    print("DEMO 1: Basic Orchestrator Usage")
    print("="*70)

    # Setup
    api_key = os.getenv("OPENROUTER_API_KEY", "test_key")
    llm_client = LLMClient(api_key=api_key, dry_run=dry_run)
    store = GraphStore("sqlite:///demo_orchestrator.db")

    # Create orchestrator
    orchestrator = OrchestratorAgent(llm_client, store)

    # Orchestrate a scene
    event_description = "simulate the constitutional convention in the united states"

    print(f"\n📝 Event: {event_description}")
    print(f"🔧 Mode: {'DRY RUN (mock data)' if dry_run else 'REAL LLM'}\n")

    result = orchestrator.orchestrate(
        event_description,
        context={
            "temporal_mode": "pearl",
            "max_entities": 8,
            "max_timepoints": 5
        },
        save_to_db=True
    )

    # Display results
    spec = result["specification"]
    print("\n" + "-"*70)
    print("RESULTS:")
    print("-"*70)
    print(f"Scene Title: {spec.scene_title}")
    print(f"Description: {spec.scene_description}")
    print(f"Location: {spec.temporal_scope['location']}")
    print(f"Time Period: {spec.temporal_scope['start_date']} → {spec.temporal_scope['end_date']}")
    print(f"Temporal Mode: {spec.temporal_mode}")

    print(f"\nEntities ({len(result['entities'])}):")
    for entity in result['entities'][:5]:  # Show first 5
        print(f"  - {entity.entity_id} ({entity.entity_type}, {entity.entity_metadata.get('role')})")
        print(f"    Resolution: {entity.resolution_level.value}")
        cognitive = entity.entity_metadata.get("cognitive_tensor", {})
        knowledge = cognitive.get("knowledge_state", [])
        print(f"    Initial knowledge: {len(knowledge)} items")

    print(f"\nTimepoints ({len(result['timepoints'])}):")
    for tp in result['timepoints']:
        print(f"  - {tp.timepoint_id}: {tp.event_description}")
        print(f"    Timestamp: {tp.timestamp}")
        print(f"    Entities present: {len(tp.entities_present)}")
        print(f"    Causal parent: {tp.causal_parent or 'None (root)'}")

    print(f"\nRelationship Graph:")
    print(f"  Nodes: {result['graph'].number_of_nodes()}")
    print(f"  Edges: {result['graph'].number_of_edges()}")

    print(f"\nExposure Events:")
    total_events = sum(len(events) for events in result['exposure_events'].values())
    print(f"  Total knowledge items seeded: {total_events}")

    print(f"\nTemporal Agent:")
    print(f"  Mode: {result['temporal_agent'].mode.value}")

    return result


def demo_convenience_function(dry_run=True):
    """Demonstrate convenience function usage"""
    print("\n" + "="*70)
    print("DEMO 2: Convenience Function Usage")
    print("="*70)

    api_key = os.getenv("OPENROUTER_API_KEY", "test_key")
    llm_client = LLMClient(api_key=api_key, dry_run=dry_run)
    store = GraphStore("sqlite:///demo_orchestrator.db")

    print("\n📝 Using simulate_event() convenience function")
    print(f"🔧 Mode: {'DRY RUN (mock data)' if dry_run else 'REAL LLM'}\n")

    result = simulate_event(
        "simulate a brief historical meeting",
        llm_client,
        store,
        context={"max_entities": 4, "max_timepoints": 2},
        save_to_db=False
    )

    print(f"\n✓ Scene generated: {result['specification'].scene_title}")
    print(f"  - {len(result['entities'])} entities")
    print(f"  - {len(result['timepoints'])} timepoints")


def demo_component_by_component(dry_run=True):
    """Demonstrate step-by-step component usage"""
    print("\n" + "="*70)
    print("DEMO 3: Component-by-Component Usage")
    print("="*70)

    from orchestrator import (
        SceneParser,
        KnowledgeSeeder,
        RelationshipExtractor,
        ResolutionAssigner
    )

    api_key = os.getenv("OPENROUTER_API_KEY", "test_key")
    llm_client = LLMClient(api_key=api_key, dry_run=dry_run)
    store = GraphStore("sqlite:///demo_orchestrator.db")

    print("\n📝 Parsing scene step-by-step")
    print(f"🔧 Mode: {'DRY RUN (mock data)' if dry_run else 'REAL LLM'}\n")

    # Step 1: Parse scene
    print("Step 1: Scene Parsing...")
    parser = SceneParser(llm_client)
    spec = parser.parse("simulate a royal coronation ceremony")
    print(f"  ✓ Parsed: {spec.scene_title}")

    # Step 2: Seed knowledge
    print("\nStep 2: Knowledge Seeding...")
    seeder = KnowledgeSeeder(store)
    exposure_events = seeder.seed_knowledge(spec, create_exposure_events=False)
    print(f"  ✓ Seeded {sum(len(e) for e in exposure_events.values())} knowledge items")

    # Step 3: Build relationship graph
    print("\nStep 3: Relationship Extraction...")
    extractor = RelationshipExtractor()
    graph = extractor.build_graph(spec)
    print(f"  ✓ Built graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    # Step 4: Assign resolutions
    print("\nStep 4: Resolution Assignment...")
    assigner = ResolutionAssigner()
    resolutions = assigner.assign_resolutions(spec, graph)
    print(f"  ✓ Assigned resolutions for {len(resolutions)} entities")

    # Show resolution distribution
    from collections import Counter
    dist = Counter(resolutions.values())
    for level, count in dist.most_common():
        print(f"    - {level.value}: {count}")


def demo_different_temporal_modes(dry_run=True):
    """Demonstrate different temporal modes"""
    print("\n" + "="*70)
    print("DEMO 4: Different Temporal Modes")
    print("="*70)

    api_key = os.getenv("OPENROUTER_API_KEY", "test_key")
    llm_client = LLMClient(api_key=api_key, dry_run=dry_run)
    store = GraphStore("sqlite:///demo_orchestrator.db")

    modes = ["pearl", "directorial", "cyclical"]

    for mode in modes:
        print(f"\n{'─'*70}")
        print(f"Testing Temporal Mode: {mode.upper()}")
        print(f"{'─'*70}")

        result = simulate_event(
            "simulate a brief historical event",
            llm_client,
            store,
            context={
                "temporal_mode": mode,
                "max_entities": 3,
                "max_timepoints": 2
            },
            save_to_db=False
        )

        print(f"  ✓ Scene: {result['specification'].scene_title}")
        print(f"  ✓ Temporal Mode: {result['temporal_agent'].mode.value}")

        if mode == "directorial":
            print("    → Optimized for narrative structure and dramatic tension")
        elif mode == "cyclical":
            print("    → Allows prophecy and temporal loops")
        elif mode == "pearl":
            print("    → Standard causality (no anachronisms)")


def main():
    """Main demonstration runner"""
    parser = argparse.ArgumentParser(description="Demonstrate OrchestratorAgent")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use dry run mode (no API calls, mock data)"
    )
    parser.add_argument(
        "--event",
        type=str,
        help="Custom event description to simulate"
    )
    parser.add_argument(
        "--demo",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run specific demo (1=basic, 2=convenience, 3=components, 4=modes)"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("ORCHESTRATOR AGENT DEMONSTRATION")
    print("="*70)
    print("\nThe OrchestratorAgent bridges natural language descriptions")
    print("to fully-specified simulations with entities, timepoints, and graphs.")
    print("="*70)

    if args.event:
        # Custom event
        api_key = os.getenv("OPENROUTER_API_KEY", "test_key")
        llm_client = LLMClient(api_key=api_key, dry_run=args.dry_run)
        store = GraphStore("sqlite:///demo_orchestrator.db")

        print(f"\n📝 Custom Event: {args.event}")
        print(f"🔧 Mode: {'DRY RUN' if args.dry_run else 'REAL LLM'}\n")

        result = simulate_event(
            args.event,
            llm_client,
            store,
            save_to_db=True
        )

        print(f"\n✓ Generated: {result['specification'].scene_title}")
        print(f"  - {len(result['entities'])} entities")
        print(f"  - {len(result['timepoints'])} timepoints")
        print(f"  - {result['graph'].number_of_edges()} relationships")

    elif args.demo:
        # Run specific demo
        demos = {
            1: demo_basic_usage,
            2: demo_convenience_function,
            3: demo_component_by_component,
            4: demo_different_temporal_modes
        }
        demos[args.demo](dry_run=args.dry_run)

    else:
        # Run all demos
        demo_basic_usage(dry_run=args.dry_run)
        demo_convenience_function(dry_run=args.dry_run)
        demo_component_by_component(dry_run=args.dry_run)
        demo_different_temporal_modes(dry_run=args.dry_run)

    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. Set OPENROUTER_API_KEY in .env for real LLM calls")
    print("  2. Run: python demo_orchestrator.py")
    print("  3. Try custom events: python demo_orchestrator.py --event 'your event here'")
    print("  4. Integrate with existing workflows for entity population")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
