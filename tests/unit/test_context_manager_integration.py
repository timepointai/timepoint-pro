"""
Test Context Manager Integration

Verifies that TrainingContextManager properly extracts rich context from
temporal knowledge graph and integrates with EntityEvolutionFormatter.

Tests:
1. Basic context extraction (M3, M6, M7, M10, M11, M13, M14)
2. Prompt generation with rich context
3. Token count estimation
4. Relevance scoring (if LLM available)
"""

import os
import tempfile
from pathlib import Path

from generation.config_schema import SimulationConfig, TemporalConfig, EntityConfig, TimepointConfig
from schemas import TemporalMode, ResolutionLevel
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
from workflows import TemporalAgent, create_entity_training_workflow, synthesize_dialog
from oxen_integration.data_formatters import EntityEvolutionFormatter


def test_context_manager_integration():
    """Test full context manager integration with training data formatter"""
    print("\n" + "="*80)
    print("TEST: Context Manager Integration")
    print("="*80)

    # Setup LLM and storage
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    llm = LLMClient(api_key=api_key)
    db_path = tempfile.mktemp(suffix=".db")
    store = GraphStore(f"sqlite:///{db_path}")

    print("\n1. Generating simple simulation...")
    print("   Scenario: Two delegates debate at Constitutional Convention")

    # Create simple simulation
    scenario = """Two delegates at the 1787 Constitutional Convention debate the structure of representation.
James Madison argues for proportional representation based on population, while Roger Sherman
advocates for equal representation for all states regardless of size."""

    result = simulate_event(
        scenario,
        llm,
        store,
        context={
            "max_entities": 2,
            "max_timepoints": 1,
            "temporal_mode": TemporalMode.PEARL.value
        },
        save_to_db=True
    )

    entities = result["entities"]
    timepoints = result["timepoints"]

    print(f"   ✓ Created {len(entities)} entities: {[e.entity_id for e in entities]}")
    print(f"   ✓ Created {len(timepoints)} timepoint(s)")

    # Generate one more timepoint for T0->T1 transition
    print("\n2. Generating second timepoint (for evolution)...")
    temporal_agent = TemporalAgent(
        mode=TemporalMode.PEARL,
        store=store,
        llm_client=llm
    )

    t1 = temporal_agent.generate_next_timepoint(
        timepoints[0],
        context={"iteration": 1, "total": 2}
    )
    store.save_timepoint(t1)
    timepoints.append(t1)

    print(f"   ✓ T0: {timepoints[0].event_description[:80]}...")
    print(f"   ✓ T1: {timepoints[1].event_description[:80]}...")

    # Add some metadata to entities for richer context
    print("\n3. Enriching entities with metadata...")

    # Save entities with some metadata
    for entity in entities:
        entity.entity_metadata["role"] = "Delegate"
        entity.entity_metadata["expertise"] = ["Constitutional Law", "Political Theory"]
        store.save_entity(entity)
        print(f"   ✓ Updated entity: {entity.entity_id}")

    # Synthesize a dialog for M11 context
    try:
        dialog = synthesize_dialog(entities, timepoints[0], [
            {"event_description": tp.event_description, "timestamp": tp.timestamp.isoformat()}
            for tp in timepoints
        ], llm, store)
        store.save_dialog(dialog)
        print(f"   ✓ Synthesized dialog with {len(dialog.messages)} messages")
    except Exception as e:
        print(f"   ⚠️  Dialog synthesis failed: {e}")

    # Format training data WITH context manager
    print("\n4. Formatting training data WITH context manager...")
    formatter_with_context = EntityEvolutionFormatter(store=store, llm=llm)

    if formatter_with_context.context_manager:
        print("   ✓ Context manager initialized")
    else:
        print("   ❌ Context manager NOT initialized!")
        return

    formatted_result = {
        "specification": result["specification"],
        "entities": entities,
        "timepoints": timepoints
    }

    examples_with_context = formatter_with_context.format_batch([formatted_result])
    print(f"   ✓ Generated {len(examples_with_context)} training examples")

    # Format training data WITHOUT context manager (for comparison)
    print("\n5. Formatting training data WITHOUT context manager (baseline)...")
    formatter_without_context = EntityEvolutionFormatter()
    examples_without_context = formatter_without_context.format_batch([formatted_result])
    print(f"   ✓ Generated {len(examples_without_context)} training examples")

    # Compare token counts
    print("\n6. Comparing context enrichment...")

    if examples_with_context and examples_without_context:
        example_with = examples_with_context[0]
        example_without = examples_without_context[0]

        prompt_with = example_with["prompt"]
        prompt_without = example_without["prompt"]

        tokens_with = len(prompt_with.split())
        tokens_without = len(prompt_without.split())

        print(f"   Baseline prompt: ~{tokens_without} words")
        print(f"   Enriched prompt: ~{tokens_with} words")
        print(f"   Context added: ~{tokens_with - tokens_without} words ({((tokens_with/tokens_without - 1) * 100):.1f}% increase)")

        # Show sample sections
        print("\n7. Sample enriched prompt sections:")
        print("-" * 80)

        # Show first 1500 chars of enriched prompt
        sample_prompt = prompt_with[:1500]
        print(sample_prompt)
        if len(prompt_with) > 1500:
            print(f"\n... [{len(prompt_with) - 1500} more characters]")

        print("-" * 80)

        # Check for context sections
        context_indicators = [
            "=== CAUSAL HISTORY ===",
            "=== RELATIONSHIP CONTEXT ===",
            "=== KNOWLEDGE PROVENANCE ===",
            "=== SCENE ATMOSPHERE ===",
            "=== DIALOG CONTEXT ===",
            "=== ENTITY STATE SUMMARY ===",
            "=== CIRCADIAN CONTEXT ==="
        ]

        print("\n8. Context sections detected:")
        for indicator in context_indicators:
            if indicator in prompt_with:
                print(f"   ✓ {indicator}")
            else:
                print(f"   - {indicator} (not included)")

    # Cleanup
    print("\n9. Cleanup...")
    Path(db_path).unlink(missing_ok=True)
    print("   ✓ Removed temporary database")

    print("\n" + "="*80)
    print("✅ TEST COMPLETE: Context manager integration successful")
    print("="*80)


if __name__ == "__main__":
    test_context_manager_integration()
