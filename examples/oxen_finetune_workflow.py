"""
Complete workflow for fine-tuning on Oxen.ai with Timepoint-Daedalus.

This example demonstrates:
1. Preparing training data from simulations
2. Uploading to Oxen.ai
3. Configuring fine-tuning with human approval
4. Launching fine-tuning via Oxen notebook
5. Evaluating fine-tuned vs. base model

Requirements:
- OXEN_API_TOKEN environment variable
- oxenai package installed
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generation import HorizontalGenerator, SimulationConfig
from oxen_integration import (
    OxenClient,
    FineTuneConfig,
    FineTuneLauncher,
    DataFormatter,
    ModelEvaluator,
    TimepointEvaluator,
)


def step1_create_training_data():
    """
    Step 1: Generate variations and format as training data.

    This creates prompt/completion pairs from simulation configurations.
    """
    print("=" * 70)
    print("STEP 1: Creating Training Data")
    print("=" * 70)

    # Generate variations
    print("\n📊 Generating scenario variations...")
    generator = HorizontalGenerator()
    base_config = SimulationConfig.example_board_meeting()

    variations = generator.generate_variations(
        base_config=base_config,
        count=20,  # Start small for testing
        strategies=["vary_personalities", "vary_outcomes"],
        random_seed=42
    )

    print(f"✅ Generated {len(variations)} variations")

    # Convert to training format
    print("\n📝 Formatting as prompt/completion pairs...")

    training_data = []
    for var in variations:
        # Create prompt asking for a simulation config
        prompt = f"""Create a simulation configuration for this scenario:
"{var.scenario_description}"

Requirements:
- {var.entities.count} entities
- {var.timepoints.count} timepoints
- Resolution: {var.timepoints.resolution}"""

        # Completion is the actual config (simplified for demonstration)
        completion = f"""{{
  "scenario": "{var.scenario_description}",
  "entities": {var.entities.count},
  "timepoints": {var.timepoints.count},
  "resolution": "{var.timepoints.resolution}",
  "mode": "{var.temporal.mode}",
  "variations": {{
    "strategy": "{var.metadata.get('variation_strategy', 'none')}",
    "index": {var.metadata.get('variation_index', 0)}
  }}
}}"""

        training_data.append({
            "prompt": prompt,
            "completion": completion,
            "scenario": var.scenario_description,
        })

    # Save to file
    output_path = "training_data.jsonl"
    import json
    with open(output_path, 'w') as f:
        for example in training_data:
            f.write(json.dumps(example) + '\n')

    print(f"✅ Saved {len(training_data)} training examples to {output_path}")
    print(f"\n📋 Sample example:")
    sample = training_data[0]
    print(f"   Prompt: {sample['prompt'][:100]}...")
    print(f"   Completion: {sample['completion'][:100]}...")

    return output_path, training_data


def step2_upload_to_oxen(training_file):
    """
    Step 2: Upload training data to Oxen.ai.
    """
    print("\n" + "=" * 70)
    print("STEP 2: Uploading to Oxen.ai")
    print("=" * 70)

    # Initialize client
    client = OxenClient(
        namespace=os.getenv("OXEN_TEST_NAMESPACE", "your-username"),
        repo_name="timepoint_training_data",
        interactive_auth=False
    )

    # Upload dataset
    print("\n📤 Uploading training data...")
    result = client.upload_dataset(
        file_path=training_file,
        commit_message="Add 20 board meeting variations for fine-tuning",
        dst_path="datasets/board_meeting_training.jsonl",
        create_repo_if_missing=True
    )

    print(f"\n✅ Upload complete!")
    print(f"📊 Dataset: {result.dataset_url}")
    print(f"🔧 Fine-tune: {result.finetune_url}")

    return client, result


def step3_configure_finetune(client, dataset_path):
    """
    Step 3: Configure fine-tuning with human approval.
    """
    print("\n" + "=" * 70)
    print("STEP 3: Configure Fine-Tuning")
    print("=" * 70)

    # Create configuration
    config = FineTuneConfig(
        dataset_path=dataset_path,
        model_name="Qwen/Qwen2.5-1.5B-Instruct",  # Small, fast model for testing
        prompt_column="prompt",
        completion_column="completion",
        epochs=3,
        batch_size=2,
        learning_rate=2e-4,
        use_lora=True,  # Parameter-efficient fine-tuning
        lora_rank=16,
        max_cost_usd=10.0,  # Safety limit
        description="Fine-tune on board meeting simulation variations",
        tags=["timepoint", "simulations", "board-meetings"]
    )

    # Initialize launcher
    launcher = FineTuneLauncher(client)

    # Prepare and request approval (with mock approval for demo)
    def mock_approval(config, validation):
        """Mock approval function - in production, get real human input."""
        print("\n⚠️  Fine-tuning requires manual approval in production!")
        print("    For this demo, we're simulating approval.")
        return False  # Don't actually approve - just show the process

    job = launcher.prepare_and_approve(
        config=config,
        dataset_path="training_data.jsonl",
        approval_callback=mock_approval
    )

    if job:
        print(f"\n✅ Job approved: {job.job_id}")
        return job
    else:
        print("\n❌ Job not approved (expected for demo)")
        # Create a mock job to demonstrate the workflow
        from oxen_integration.finetune import FineTuneJob
        from datetime import datetime
        job = FineTuneJob(
            job_id=f"demo_finetune_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            config=config,
            status="demo"
        )
        return job


def step4_launch_notebook(launcher, job):
    """
    Step 4: Get instructions for launching fine-tuning.
    """
    print("\n" + "=" * 70)
    print("STEP 4: Launch Instructions")
    print("=" * 70)

    # Generate instructions
    instructions = launcher.launch_via_notebook(job)

    print(f"\n📓 Notebook URL: {instructions['notebook_url']}")
    print(f"\n💾 Configuration saved to: {instructions.get('config_file_path', 'N/A')}")

    return instructions


def step5_evaluate_models():
    """
    Step 5: Demonstrate evaluation framework.

    In practice, this would run after fine-tuning completes.
    """
    print("\n" + "=" * 70)
    print("STEP 5: Model Evaluation (Demo)")
    print("=" * 70)

    # Create test prompts
    test_prompts = TimepointEvaluator.create_test_prompts(
        scenarios=[
            "Simulate a crisis meeting with 3 executives",
            "Simulate a negotiation between 2 parties",
        ],
        timepoint_configs=[
            {"num_entities": 3, "num_timepoints": 5, "resolution": "hour"},
            {"num_entities": 2, "num_timepoints": 3, "resolution": "minute"},
        ]
    )

    print(f"\n📋 Created {len(test_prompts)} test examples")
    print(f"\nSample test prompt:")
    print(test_prompts[0]["prompt"][:200] + "...")

    print(f"\n💡 After fine-tuning completes:")
    print("   1. Load base and fine-tuned models")
    print("   2. Generate outputs for test prompts")
    print("   3. Compare quality with ModelEvaluator")
    print("   4. Analyze win rates and improvements")

    # Example of how evaluation would work
    print(f"\n📊 Example evaluation workflow:")
    print("""
from oxen_integration import ModelEvaluator

evaluator = ModelEvaluator(
    base_model_client=base_model,
    finetuned_model_client=finetuned_model
)

results = evaluator.evaluate_side_by_side(
    test_examples=test_prompts,
    prompt_key="prompt"
)

print(results.summary())
# Shows win rates, score improvements, detailed comparisons
""")


def main():
    """Run complete fine-tuning workflow."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    Timepoint-Daedalus → Oxen.ai Fine-Tuning Workflow            ║
║                                                                  ║
║    This demonstrates the complete process for:                  ║
║    • Preparing training data from simulations                   ║
║    • Uploading to Oxen.ai with version control                  ║
║    • Configuring fine-tuning with cost estimation               ║
║    • Human approval gates for spending control                  ║
║    • Launching training via Oxen notebooks                      ║
║    • Evaluating fine-tuned vs. base models                      ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")

    # Check environment
    if not os.getenv("OXEN_API_TOKEN"):
        print("❌ Error: OXEN_API_TOKEN environment variable not set")
        print("   Get your token from: https://hub.oxen.ai/settings/tokens")
        return

    try:
        # Execute workflow
        training_file, training_data = step1_create_training_data()

        client, upload_result = step2_upload_to_oxen(training_file)

        launcher = FineTuneLauncher(client)
        job = step3_configure_finetune(
            client,
            "datasets/board_meeting_training.jsonl"
        )

        if job:
            instructions = step4_launch_notebook(launcher, job)

        step5_evaluate_models()

        # Final summary
        print("\n" + "=" * 70)
        print("WORKFLOW COMPLETE")
        print("=" * 70)
        print(f"""
✅ Training data created: {len(training_data)} examples
✅ Uploaded to Oxen.ai: {upload_result.dataset_url}
✅ Fine-tuning configured with approval gates
✅ Evaluation framework demonstrated

Next Steps:
1. Review the generated configuration file
2. Open the Oxen notebook and configure your fine-tuning
3. Monitor training progress on Oxen.ai
4. Use the evaluation framework to compare models
5. Deploy the fine-tuned model for production use

💡 Remember:
- Always review costs before approving fine-tuning
- Start with small datasets to test
- Use LoRA for parameter-efficient training
- Evaluate thoroughly before deploying
""")

        # Cleanup
        if os.path.exists(training_file):
            print(f"\n🧹 Cleaning up temporary file: {training_file}")
            os.unlink(training_file)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
