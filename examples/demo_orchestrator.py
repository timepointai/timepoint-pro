#!/usr/bin/env python3
"""
demo_orchestrator.py - Generate Real Simulations from Natural Language

This script generates complete simulations with REAL LLM calls from natural language.

Usage:
    # Simple - use your own prompt:
    python demo_orchestrator.py --event "simulate a board meeting about a merger"

    # With custom settings:
    python demo_orchestrator.py --event "emergency crisis meeting" --entities 5 --timepoints 3

    # Test mode (no API costs):
    python demo_orchestrator.py --event "your prompt" --dry-run

Requirements:
    - OPENROUTER_API_KEY in .env file (get from https://openrouter.ai/keys)
    - Estimated cost per run: $0.05-0.20 depending on complexity
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore

# Load environment variables
load_dotenv()


def run_simulation(event_description: str, max_entities: int = 4, max_timepoints: int = 3,
                   temporal_mode: str = "pearl", dry_run: bool = False, save_results: bool = True):
    """
    Run a complete simulation from natural language description.

    Args:
        event_description: Natural language description of what to simulate
        max_entities: Maximum number of entities/characters (1-20)
        max_timepoints: Maximum number of timepoints (1-10)
        temporal_mode: Temporal causality mode (pearl, directorial, cyclical, branching)
        dry_run: If True, use mock data (no API costs)
        save_results: If True, save results to output directory

    Returns:
        dict: Simulation results
    """

    # Header
    print("\n" + "="*80)
    print("  TIMEPOINT-DAEDALUS: Natural Language Simulation")
    print("="*80)

    # Check API key
    if not dry_run:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("\n❌ ERROR: OPENROUTER_API_KEY not set")
            print("\nTo use real LLM calls:")
            print("  1. Get API key from: https://openrouter.ai/keys")
            print("  2. Add to .env file: OPENROUTER_API_KEY=your_key_here")
            print("  3. Run again")
            print("\nOr use --dry-run for testing without API calls")
            sys.exit(1)

    # Setup
    print(f"\n📝 Event Description:")
    print(f"   {event_description}")
    print(f"\n⚙️  Configuration:")
    print(f"   Max Entities: {max_entities}")
    print(f"   Max Timepoints: {max_timepoints}")
    print(f"   Temporal Mode: {temporal_mode}")
    print(f"   Mode: {'🧪 DRY RUN (mock data)' if dry_run else '🔴 REAL LLM (API costs)'}")

    if not dry_run:
        print(f"\n💰 Estimated cost: $0.05-0.20 depending on complexity")
        response = input("\nContinue? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Cancelled")
            sys.exit(0)

    # Initialize
    print("\n" + "-"*80)
    print("Initializing components...")
    print("-"*80)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # LLM client
    if dry_run:
        api_key = "test_key"
    else:
        api_key = os.getenv("OPENROUTER_API_KEY")

    llm_client = LLMClient(api_key=api_key)

    # Verify mode
    if dry_run:
        print("⚠️  DRY RUN MODE: Using mock LLM responses")

    print(f"✓ LLM Client: {llm_client.default_model}")

    # Storage
    db_path = f"output/simulations/sim_{timestamp}.db"
    Path("output/simulations").mkdir(parents=True, exist_ok=True)
    store = GraphStore(f"sqlite:///{db_path}")
    print(f"✓ Storage: {db_path}")

    # Run simulation
    print("\n" + "-"*80)
    print("Generating simulation...")
    print("-"*80)
    print("\n⏳ This will take 1-3 minutes for REAL mode, ~5 seconds for DRY RUN...")

    start_time = datetime.utcnow()

    try:
        result = simulate_event(
            event_description,
            llm_client,
            store,
            context={
                "max_entities": max_entities,
                "max_timepoints": max_timepoints,
                "temporal_mode": temporal_mode
            },
            save_to_db=True
        )
    except Exception as e:
        print(f"\n❌ ERROR during simulation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    end_time = datetime.utcnow()
    elapsed = (end_time - start_time).total_seconds()

    # Extract results
    spec = result['specification']
    entities = result['entities']
    timepoints = result['timepoints']
    graph = result['graph']
    exposure_events = result['exposure_events']

    # Display results
    print("\n" + "="*80)
    print("  RESULTS")
    print("="*80)

    print(f"\n📋 Scene: {spec.scene_title}")
    print(f"   {spec.scene_description[:150]}...")
    print(f"\n   Location: {spec.temporal_scope.get('location', 'Not specified')}")
    print(f"   Period: {spec.temporal_scope.get('start_date', 'N/A')} → {spec.temporal_scope.get('end_date', 'N/A')}")
    print(f"   Mode: {spec.temporal_mode}")

    print(f"\n👥 Entities: {len(entities)}")
    for i, entity in enumerate(entities, 1):
        print(f"\n   {i}. {entity.entity_id}")
        role = entity.entity_metadata.get('role', 'Unknown')
        print(f"      Role: {role}")
        print(f"      Type: {entity.entity_type}")
        print(f"      Resolution: {entity.resolution_level.value}")

        # Show knowledge
        cognitive = entity.entity_metadata.get('cognitive_tensor', {})
        knowledge = cognitive.get('knowledge_state', [])
        if knowledge:
            print(f"      Knowledge: {len(knowledge)} items")
            print(f"         Sample: {knowledge[0][:60]}...")

        # Show personality
        personality = cognitive.get('personality_traits', [])
        if personality:
            print(f"      Personality: {', '.join(personality[:3])}")

    print(f"\n⏱️  Timepoints: {len(timepoints)}")
    for i, tp in enumerate(timepoints, 1):
        print(f"\n   {i}. {tp.timepoint_id}")
        print(f"      Event: {tp.event_description}")
        print(f"      Time: {tp.timestamp}")
        print(f"      Entities: {len(tp.entities_present)}")
        if tp.causal_parent:
            print(f"      Caused by: {tp.causal_parent}")

    print(f"\n🔗 Relationships: {graph.number_of_edges()}")
    if graph.number_of_edges() > 0:
        for source, target, data in list(graph.edges(data=True))[:3]:
            rel = data.get('relationship', 'connected')
            print(f"   {source} --[{rel}]--> {target}")
        if graph.number_of_edges() > 3:
            print(f"   ... and {graph.number_of_edges() - 3} more")

    total_knowledge = sum(len(events) for events in exposure_events.values())
    print(f"\n📊 Knowledge Items Seeded: {total_knowledge}")

    # Cost tracking
    if hasattr(llm_client, 'service'):
        stats = llm_client.service.get_statistics()
        total_cost = stats.get('total_cost', 0.0)
        total_tokens = stats.get('total_tokens', 0)
        total_calls = stats.get('total_calls', 0)
    else:
        total_cost = getattr(llm_client, 'cost', 0.0)
        total_tokens = getattr(llm_client, 'token_count', 0)
        total_calls = 0

    print(f"\n💰 Cost: ${total_cost:.4f}")
    print(f"   API Calls: {total_calls}")
    print(f"   Tokens: {total_tokens:,}")
    print(f"   Time: {elapsed:.1f}s")

    # Save results
    if save_results:
        output_dir = Path("output/simulations")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Summary JSON
        summary_file = output_dir / f"summary_{timestamp}.json"
        summary = {
            "metadata": {
                "timestamp": timestamp,
                "event_description": event_description,
                "elapsed_seconds": elapsed,
                "cost_usd": total_cost,
                "tokens": total_tokens,
                "api_calls": total_calls,
                "dry_run": dry_run
            },
            "configuration": {
                "max_entities": max_entities,
                "max_timepoints": max_timepoints,
                "temporal_mode": temporal_mode
            },
            "scene": {
                "title": spec.scene_title,
                "description": spec.scene_description,
                "location": spec.temporal_scope.get('location'),
                "temporal_mode": spec.temporal_mode
            },
            "entities": [
                {
                    "entity_id": e.entity_id,
                    "type": e.entity_type,
                    "role": e.entity_metadata.get('role'),
                    "resolution": e.resolution_level.value,
                    "knowledge_count": len(e.entity_metadata.get('cognitive_tensor', {}).get('knowledge_state', []))
                }
                for e in entities
            ],
            "timepoints": [
                {
                    "timepoint_id": tp.timepoint_id,
                    "event": tp.event_description,
                    "timestamp": tp.timestamp.isoformat(),
                    "entities_present": tp.entities_present,
                    "causal_parent": tp.causal_parent
                }
                for tp in timepoints
            ],
            "graph": {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges()
            }
        }

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        # Entity details
        entity_file = output_dir / f"entities_{timestamp}.jsonl"
        with open(entity_file, 'w') as f:
            for entity in entities:
                f.write(json.dumps({
                    "entity_id": entity.entity_id,
                    "entity_type": entity.entity_type,
                    "timepoint": entity.timepoint,
                    "resolution_level": entity.resolution_level.value,
                    "metadata": entity.entity_metadata
                }, default=str) + '\n')

        print(f"\n📁 Results saved:")
        print(f"   Database: {db_path}")
        print(f"   Summary: {summary_file}")
        print(f"   Entities: {entity_file}")

    print("\n" + "="*80)
    print("  ✅ SIMULATION COMPLETE")
    print("="*80)

    if not dry_run:
        print(f"\n💡 You generated:")
        print(f"   • {len(entities)} entities with knowledge and personalities")
        print(f"   • {len(timepoints)} timepoints with causal relationships")
        print(f"   • {total_knowledge} knowledge items across the simulation")
        print(f"\n   Total cost: ${total_cost:.4f}")

    return result


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate simulations from natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_orchestrator.py --event "emergency board meeting about bankruptcy"
  python demo_orchestrator.py --event "apollo 13 crisis" --entities 5 --timepoints 4
  python demo_orchestrator.py --event "constitutional convention" --mode directorial
  python demo_orchestrator.py --event "test scenario" --dry-run

Temporal Modes:
  pearl         Standard causality (default)
  directorial   Narrative-focused with dramatic tension
  cyclical      Allows prophecy and time loops
  branching     Counterfactual what-if scenarios
  portal        Backward causal inference from known future state
        """
    )

    parser.add_argument(
        "--event",
        type=str,
        required=True,
        help="Natural language description of what to simulate"
    )

    parser.add_argument(
        "--entities",
        type=int,
        default=4,
        help="Maximum number of entities (1-20, default: 4)"
    )

    parser.add_argument(
        "--timepoints",
        type=int,
        default=3,
        help="Maximum number of timepoints (1-10, default: 3)"
    )

    parser.add_argument(
        "--mode",
        type=str,
        default="pearl",
        choices=["pearl", "directorial", "cyclical", "branching", "portal"],
        help="Temporal causality mode (default: pearl)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use mock data (no API costs)"
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to files"
    )

    args = parser.parse_args()

    # Validate parameters
    if args.entities < 1 or args.entities > 20:
        print("❌ ERROR: --entities must be between 1 and 20")
        sys.exit(1)

    if args.timepoints < 1 or args.timepoints > 10:
        print("❌ ERROR: --timepoints must be between 1 and 10")
        sys.exit(1)

    # Run simulation
    try:
        result = run_simulation(
            event_description=args.event,
            max_entities=args.entities,
            max_timepoints=args.timepoints,
            temporal_mode=args.mode,
            dry_run=args.dry_run,
            save_results=not args.no_save
        )
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
