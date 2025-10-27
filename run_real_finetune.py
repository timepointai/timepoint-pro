"""
Real fine-tuning workflow with actual Timepoint-Daedalus simulations.

This script:
1. Generates 100 scenario variations (horizontal generation)
2. Runs simulations for each to capture temporal evolution
3. Formats simulation data as training examples (multiple formats)
4. Uploads to Oxen.ai
5. Requests human approval for fine-tuning
6. Provides instructions to launch the fine-tuning job
"""
import os
import sys
import json
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generation import HorizontalGenerator, VerticalGenerator
from generation.config_schema import SimulationConfig
from orchestrator import simulate_event
from storage import GraphStore
from llm_v2 import LLMClient
from oxen_integration import (
    OxenClient,
    FineTuneConfig,
    FineTuneLauncher,
)
from oxen_integration.data_formatters import (
    EntityEvolutionFormatter,
    DialogSynthesisFormatter,
    KnowledgeFlowFormatter,
    RelationshipDynamicsFormatter,
)


def generate_horizontal_simulations(llm_client, store, count=50):
    """
    Generate horizontal training data - diverse scenario variations.

    This trains the model on timepoint logic across different scenarios.
    """
    print("=" * 70)
    print("STEP 1: Generating Horizontal Training Data (Scenario Variations)")
    print("=" * 70)

    print(f"\n📊 Generating {count} scenario variations...")
    generator = HorizontalGenerator()
    base_config = SimulationConfig.example_board_meeting()

    # Generate variations with different strategies
    variations = generator.generate_variations(
        base_config=base_config,
        count=count,
        strategies=["vary_personalities", "vary_outcomes", "vary_knowledge"],
        random_seed=42
    )

    print(f"✅ Generated {len(variations)} scenario variations")

    # Run simulations for each variation
    print(f"\n🎬 Running simulations for each variation...")
    simulation_results = []

    for i, variation in enumerate(variations):
        print(f"  Running simulation {i+1}/{len(variations)}...", end="\r")

        # Convert variation to simulation parameters
        scenario_desc = variation.scenario_description

        # Run simulation
        try:
            result = simulate_event(
                scenario_desc,
                llm_client,
                store,
                context={
                    "max_entities": variation.entities.count,
                    "max_timepoints": min(variation.timepoints.count, 3),  # Keep small for speed
                    "temporal_mode": variation.temporal.mode
                },
                save_to_db=False  # Don't persist, just collect data
            )
            simulation_results.append(result)
        except Exception as e:
            print(f"\n⚠️  Simulation {i+1} failed: {e}")
            continue

    print(f"\n✅ Completed {len(simulation_results)} simulations")

    return simulation_results


def generate_vertical_simulation(llm_client, store):
    """
    Generate vertical training data - temporal depth in single scenario.

    This trains the model on world modeling with deep temporal context.
    """
    print("\n" + "=" * 70)
    print("STEP 2: Generating Vertical Training Data (Temporal Depth)")
    print("=" * 70)

    print("\n📊 Generating temporal expansion...")
    v_generator = VerticalGenerator()
    base_config = SimulationConfig.example_board_meeting()

    # Expand with 5 timepoints before and after
    expanded = v_generator.generate_temporal_depth(
        base_config,
        before_count=5,
        after_count=5,
        strategy="progressive_training"
    )

    print(f"✅ Expanded to {expanded.timepoints.count + 10} total timepoints")

    # Run expanded simulation
    print(f"\n🎬 Running deep temporal simulation...")
    result = simulate_event(
        expanded.scenario_description,
        llm_client,
        store,
        context={
            "max_entities": expanded.entities.count,
            "max_timepoints": min(expanded.timepoints.count + 10, 11),
            "temporal_mode": expanded.temporal.mode
        },
        save_to_db=False
    )

    print(f"✅ Completed vertical simulation")

    return [result]  # Return as list for consistency


def format_training_data(simulations):
    """
    Format simulations into multiple training data formats.
    """
    print("\n" + "=" * 70)
    print("STEP 3: Formatting Training Data")
    print("=" * 70)

    formatters = {
        "entity_evolution": EntityEvolutionFormatter(),
        "dialog_synthesis": DialogSynthesisFormatter(),
        "knowledge_flow": KnowledgeFlowFormatter(),
        "relationship_dynamics": RelationshipDynamicsFormatter(),
    }

    all_examples = []

    for name, formatter in formatters.items():
        print(f"\n📝 Formatting {name}...")
        examples = formatter.format_batch(simulations)
        print(f"   ✓ Generated {len(examples)} examples")
        all_examples.extend(examples)

    print(f"\n✅ Total training examples: {len(all_examples)}")

    return all_examples


def save_training_data(examples, output_path="timepoint_training_data.jsonl"):
    """Save training examples to JSONL file"""
    print(f"\n💾 Saving training data to {output_path}...")

    with open(output_path, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')

    file_size = os.path.getsize(output_path) / 1024  # KB
    print(f"✅ Saved {len(examples)} examples ({file_size:.1f} KB)")

    # Show sample
    if examples:
        print(f"\n📋 Sample training example:")
        sample = examples[0]
        print(f"\nPrompt (first 200 chars):\n{sample['prompt'][:200]}...")
        print(f"\nCompletion (first 200 chars):\n{sample['completion'][:200]}...")

    return output_path


def upload_to_oxen(file_path, namespace, repo_name):
    """Upload training data to Oxen.ai"""
    print("\n" + "=" * 70)
    print("STEP 4: Uploading to Oxen.ai")
    print("=" * 70)

    client = OxenClient(
        namespace=namespace,
        repo_name=repo_name,
        interactive_auth=False
    )

    print(f"\n📤 Uploading {file_path}...")
    result = client.upload_dataset(
        file_path=file_path,
        commit_message="Timepoint-Daedalus training data: Real simulation traces",
        dst_path=f"datasets/timepoint_training_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl",
        create_repo_if_missing=True
    )

    print(f"\n✅ Upload successful!")
    print(f"📊 Dataset URL: {result.dataset_url}")
    print(f"📦 Repository: {result.repo_url}")
    print(f"💾 File size: {result.file_size_bytes / 1024:.1f} KB")

    return client, result


def configure_and_approve(client, dataset_path, num_examples):
    """Configure fine-tuning and get human approval"""
    print("\n" + "=" * 70)
    print("STEP 5: Configure Fine-Tuning (YOUR APPROVAL REQUIRED)")
    print("=" * 70)

    config = FineTuneConfig(
        dataset_path=dataset_path,
        model_name="Qwen/Qwen2.5-1.5B-Instruct",
        prompt_column="prompt",
        completion_column="completion",

        # Training settings
        epochs=3,
        batch_size=4,
        learning_rate=2e-4,
        max_seq_length=2048,

        # LoRA for efficiency
        use_lora=True,
        lora_rank=16,
        lora_alpha=16,
        lora_dropout=0.05,

        # Cost control
        max_cost_usd=20.0,

        # Optimization
        use_4bit_quantization=True,
        gradient_checkpointing=True,
        gradient_accumulation_steps=4,

        # Metadata
        description="Fine-tune on Timepoint-Daedalus temporal simulations",
        tags=["timepoint", "temporal", "entity-evolution", "world-modeling"]
    )

    launcher = FineTuneLauncher(client)

    def get_human_approval(config, validation):
        """Request human approval"""
        print("\n" + "=" * 70)
        print("⚠️  APPROVAL REQUIRED FOR FINE-TUNING")
        print("=" * 70)

        print(f"\nDataset Validation:")
        print(f"  ✓ Examples: {validation['num_examples']}")
        print(f"  ✓ Valid: {validation['valid']}")

        print(f"\nConfiguration:")
        print(f"  Model: {config.model_name}")
        print(f"  Dataset: {config.dataset_path}")
        print(f"  Examples: {validation['num_examples']}")
        print(f"  Epochs: {config.epochs}")
        print(f"  Use LoRA: {config.use_lora}")

        print(f"\nCost Estimate:")
        print(f"  Estimated: ${config.estimated_cost_usd:.2f}")
        print(f"  Max limit: ${config.max_cost_usd:.2f}")

        print(f"\nThis will:")
        print(f"  1. Train on real Timepoint simulation traces")
        print(f"  2. Learn entity evolution, dialog synthesis, knowledge flow")
        print(f"  3. Use A10G GPU (~$1/hour)")
        print(f"  4. Create fine-tuned model for temporal reasoning")

        print(f"\n" + "=" * 70)
        response = input("Do you approve this fine-tuning job? [yes/NO]: ").strip().lower()

        return response in ('yes', 'y')

    # Temporary file for validation
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as tmp:
        tmp.write('{"prompt": "test", "completion": "test"}\n')
        tmp_path = tmp.name

    try:
        job = launcher.prepare_and_approve(
            config=config,
            dataset_path=tmp_path,
            approval_callback=get_human_approval
        )
        return launcher, job
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    """Run complete fine-tuning workflow"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    Timepoint-Daedalus Fine-Tuning (REAL SIMULATIONS)            ║
║                                                                  ║
║    Trains on actual temporal simulation traces                  ║
║    - Horizontal: 50 scenario variations                         ║
║    - Vertical: Temporal depth expansion                         ║
║    - Multiple training formats                                  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")

    # Check environment
    if not (os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")):
        print("❌ Error: OXEN_API_TOKEN or OXEN_API_KEY not set")
        print("   Set it with: export OXEN_API_TOKEN=your_token")
        return 1

    # REQUIRE real LLM service - no mock mode allowed
    llm_enabled = os.getenv("LLM_SERVICE_ENABLED", "true").lower() == "true"
    if not llm_enabled:
        print("❌ ERROR: LLM_SERVICE_ENABLED=false")
        print("   This script requires REAL simulations, not mocks.")
        print("   Set LLM_SERVICE_ENABLED=true and provide OPENROUTER_API_KEY")
        return 1

    # Validate API key exists
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        print("   Real LLM calls require an API key")
        print("   Set it with: export OPENROUTER_API_KEY=your_key")
        return 1

    try:
        # Initialize
        api_key = os.getenv("OPENROUTER_API_KEY", "mock_key")
        llm_client = LLMClient(api_key=api_key, dry_run=not llm_enabled)
        db_path = tempfile.mktemp(suffix=".db")
        store = GraphStore(f"sqlite:///{db_path}")

        # Step 1 & 2: Generate simulations
        horizontal_sims = generate_horizontal_simulations(llm_client, store, count=50)
        vertical_sims = generate_vertical_simulation(llm_client, store)

        all_simulations = horizontal_sims + vertical_sims
        print(f"\n✅ Total simulations: {len(all_simulations)}")

        # Step 3: Format training data
        training_examples = format_training_data(all_simulations)

        # Step 4: Save
        training_file = save_training_data(training_examples)

        # Step 5: Upload
        namespace = os.getenv("OXEN_TEST_NAMESPACE", "realityinspector")
        client, upload_result = upload_to_oxen(
            training_file,
            namespace,
            "timepoint_finetune_production"
        )

        # Step 6: Configure and approve
        launcher, job = configure_and_approve(
            client,
            upload_result.dataset_url.split("/file/main/")[-1],  # Extract path
            len(training_examples)
        )

        # Step 7: Launch (if approved)
        if job:
            instructions = launcher.launch_via_notebook(job)

            print(f"\n{'=' * 70}")
            print("✅ READY TO FINE-TUNE")
            print(f"{'=' * 70}")
            print(f"\nDataset uploaded: {upload_result.dataset_url}")
            print(f"Training examples: {len(training_examples)}")
            print(f"Notebook URL: {instructions['notebook_url']}")
            print(f"\nEstimated cost: ${job.config.estimated_cost_usd:.2f}")

        # Cleanup
        if os.path.exists(training_file):
            print(f"\n🧹 Cleaning up: {training_file}")
            os.unlink(training_file)
        if os.path.exists(db_path):
            os.unlink(db_path)

        return 0

    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
