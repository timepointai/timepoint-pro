"""
Fine-tuning utilities for Oxen.ai integration.

Based on Oxen.ai's Marimo notebook workflow for LLM training.
See: https://docs.oxen.ai/examples/notebooks/train_llm
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
import json
import tempfile


@dataclass
class FineTuneConfig:
    """Configuration for fine-tuning a model on Oxen.ai."""

    # Required parameters
    dataset_path: str  # Path to dataset in Oxen repo (e.g., "datasets/training.jsonl")
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"  # Base model to fine-tune

    # Data column configuration
    prompt_column: str = "prompt"  # Column containing prompts/questions
    completion_column: str = "completion"  # Column containing completions/answers
    system_message: Optional[str] = None  # Optional system message for all examples

    # Training hyperparameters
    epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-4
    max_seq_length: int = 2048

    # LoRA parameters (parameter-efficient fine-tuning)
    use_lora: bool = True
    lora_rank: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.05

    # Training configuration
    gradient_accumulation_steps: int = 4
    warmup_steps: int = 100
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100

    # Optimization
    use_4bit_quantization: bool = True
    gradient_checkpointing: bool = True

    # Output configuration
    output_dir: str = "finetune_output"
    experiment_name: Optional[str] = None

    # Cost estimation
    estimated_cost_usd: Optional[float] = None
    max_cost_usd: Optional[float] = None  # Abort if estimate exceeds this

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "dataset_path": self.dataset_path,
            "model_name": self.model_name,
            "prompt_column": self.prompt_column,
            "completion_column": self.completion_column,
            "system_message": self.system_message,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "max_seq_length": self.max_seq_length,
            "use_lora": self.use_lora,
            "lora_rank": self.lora_rank,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "warmup_steps": self.warmup_steps,
            "logging_steps": self.logging_steps,
            "save_steps": self.save_steps,
            "eval_steps": self.eval_steps,
            "use_4bit_quantization": self.use_4bit_quantization,
            "gradient_checkpointing": self.gradient_checkpointing,
            "output_dir": self.output_dir,
            "experiment_name": self.experiment_name,
            "estimated_cost_usd": self.estimated_cost_usd,
            "max_cost_usd": self.max_cost_usd,
            "description": self.description,
            "tags": self.tags,
        }

    def estimate_cost(self, num_examples: int) -> float:
        """
        Estimate training cost in USD.

        Based on A10G GPU @ ~$1/hour, training time estimates.

        Args:
            num_examples: Number of training examples

        Returns:
            Estimated cost in USD
        """
        # Rough estimation formula
        # A10G GPU: ~$1/hour
        # Time per 1000 examples with 1.5B model: ~15-30 minutes

        examples_per_hour = 2000 * (1 if self.use_lora else 0.3)  # LoRA is much faster
        hours_needed = (num_examples * self.epochs) / examples_per_hour

        # Add overhead (setup, saving, etc.)
        hours_needed *= 1.2

        # A10G cost
        cost = hours_needed * 1.0

        self.estimated_cost_usd = cost
        return cost


@dataclass
class FineTuneJob:
    """Represents a fine-tuning job on Oxen.ai."""

    job_id: str
    config: FineTuneConfig
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    model_branch: Optional[str] = None  # Oxen branch where model is saved
    final_loss: Optional[float] = None
    eval_metrics: Dict[str, float] = field(default_factory=dict)

    # Tracking
    logs_url: Optional[str] = None
    model_url: Optional[str] = None
    notebook_url: Optional[str] = None

    # Error handling
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "job_id": self.job_id,
            "config": self.config.to_dict(),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "model_branch": self.model_branch,
            "final_loss": self.final_loss,
            "eval_metrics": self.eval_metrics,
            "logs_url": self.logs_url,
            "model_url": self.model_url,
            "notebook_url": self.notebook_url,
            "error_message": self.error_message,
        }


class DataFormatter:
    """Format data for fine-tuning."""

    @staticmethod
    def to_prompt_completion(
        data: List[Dict[str, Any]],
        prompt_key: str,
        completion_key: str,
        system_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Convert data to prompt/completion format.

        Args:
            data: List of data dictionaries
            prompt_key: Key for prompt/question
            completion_key: Key for completion/answer
            system_message: Optional system message

        Returns:
            List of formatted examples
        """
        formatted = []

        for item in data:
            if prompt_key not in item or completion_key not in item:
                continue

            example = {
                "prompt": str(item[prompt_key]),
                "completion": str(item[completion_key])
            }

            if system_message:
                example["system"] = system_message

            formatted.append(example)

        return formatted

    @staticmethod
    def to_chat_format(
        data: List[Dict[str, Any]],
        prompt_key: str,
        completion_key: str,
        system_message: Optional[str] = None
    ) -> List[Dict[str, List[Dict[str, str]]]]:
        """
        Convert data to OpenAI chat format.

        Args:
            data: List of data dictionaries
            prompt_key: Key for prompt/question
            completion_key: Key for completion/answer
            system_message: Optional system message

        Returns:
            List of chat-formatted examples
        """
        formatted = []

        for item in data:
            if prompt_key not in item or completion_key not in item:
                continue

            messages = []

            if system_message:
                messages.append({"role": "system", "content": system_message})

            messages.append({"role": "user", "content": str(item[prompt_key])})
            messages.append({"role": "assistant", "content": str(item[completion_key])})

            formatted.append({"messages": messages})

        return formatted

    @staticmethod
    def validate_dataset(
        file_path: str,
        prompt_column: str,
        completion_column: str,
        min_examples: int = 100
    ) -> Dict[str, Any]:
        """
        Validate dataset for fine-tuning.

        Args:
            file_path: Path to JSONL dataset
            prompt_column: Column for prompts
            completion_column: Column for completions
            min_examples: Minimum required examples

        Returns:
            Validation results dictionary
        """
        results = {
            "valid": False,
            "num_examples": 0,
            "missing_prompts": 0,
            "missing_completions": 0,
            "empty_prompts": 0,
            "empty_completions": 0,
            "avg_prompt_length": 0,
            "avg_completion_length": 0,
            "issues": []
        }

        try:
            examples = []
            prompt_lengths = []
            completion_lengths = []

            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        item = json.loads(line)
                        examples.append(item)

                        # Check for missing columns
                        if prompt_column not in item:
                            results["missing_prompts"] += 1
                        elif not str(item[prompt_column]).strip():
                            results["empty_prompts"] += 1
                        else:
                            prompt_lengths.append(len(str(item[prompt_column])))

                        if completion_column not in item:
                            results["missing_completions"] += 1
                        elif not str(item[completion_column]).strip():
                            results["empty_completions"] += 1
                        else:
                            completion_lengths.append(len(str(item[completion_column])))

                    except json.JSONDecodeError:
                        results["issues"].append(f"Line {line_num}: Invalid JSON")

            results["num_examples"] = len(examples)

            if prompt_lengths:
                results["avg_prompt_length"] = sum(prompt_lengths) / len(prompt_lengths)
            if completion_lengths:
                results["avg_completion_length"] = sum(completion_lengths) / len(completion_lengths)

            # Validation checks
            if results["num_examples"] < min_examples:
                results["issues"].append(
                    f"Only {results['num_examples']} examples, need at least {min_examples}"
                )

            if results["missing_prompts"] > 0:
                results["issues"].append(
                    f"{results['missing_prompts']} examples missing '{prompt_column}' column"
                )

            if results["missing_completions"] > 0:
                results["issues"].append(
                    f"{results['missing_completions']} examples missing '{completion_column}' column"
                )

            if results["empty_prompts"] > results["num_examples"] * 0.1:
                results["issues"].append(
                    f"{results['empty_prompts']} examples have empty prompts"
                )

            if results["empty_completions"] > results["num_examples"] * 0.1:
                results["issues"].append(
                    f"{results['empty_completions']} examples have empty completions"
                )

            results["valid"] = len(results["issues"]) == 0

        except Exception as e:
            results["issues"].append(f"Error reading file: {e}")

        return results

    @staticmethod
    def create_training_dataset(
        input_data: List[Dict[str, Any]],
        prompt_template: str,
        completion_template: str,
        output_path: str,
        format: str = "chat"  # "chat" or "completion"
    ) -> str:
        """
        Create a training dataset from Timepoint simulation data.

        Args:
            input_data: List of simulation configurations or results
            prompt_template: Template for creating prompts (can use {key} placeholders)
            completion_template: Template for creating completions
            output_path: Where to save the formatted dataset
            format: "chat" (OpenAI format) or "completion" (simple prompt/completion)

        Returns:
            Path to created dataset

        Example:
            >>> data = [{"scenario": "board meeting", "outcome": "approved"}]
            >>> create_training_dataset(
            ...     data,
            ...     prompt_template="Simulate: {scenario}",
            ...     completion_template="Outcome: {outcome}",
            ...     output_path="training.jsonl"
            ... )
        """
        formatted_examples = []

        for item in input_data:
            try:
                # Format prompt and completion using templates
                prompt = prompt_template.format(**item)
                completion = completion_template.format(**item)

                if format == "chat":
                    example = {
                        "messages": [
                            {"role": "user", "content": prompt},
                            {"role": "assistant", "content": completion}
                        ]
                    }
                else:  # completion format
                    example = {
                        "prompt": prompt,
                        "completion": completion
                    }

                formatted_examples.append(example)

            except KeyError as e:
                print(f"Warning: Skipping item due to missing key: {e}")
                continue

        # Write to JSONL
        with open(output_path, 'w') as f:
            for example in formatted_examples:
                f.write(json.dumps(example) + '\n')

        return output_path


class FineTuneLauncher:
    """Launch and manage fine-tuning jobs on Oxen.ai."""

    def __init__(self, oxen_client: "OxenClient"):
        """
        Initialize launcher.

        Args:
            oxen_client: Authenticated OxenClient instance
        """
        self.client = oxen_client

    def prepare_and_approve(
        self,
        config: FineTuneConfig,
        dataset_path: str,
        approval_callback: Optional[Callable[[FineTuneConfig, Dict], bool]] = None
    ) -> Optional[FineTuneJob]:
        """
        Prepare fine-tuning job and request human approval.

        Args:
            config: Fine-tuning configuration
            dataset_path: Local path to dataset for validation
            approval_callback: Function that receives (config, validation_results)
                              and returns True to approve, False to reject

        Returns:
            FineTuneJob if approved, None if rejected
        """
        # Validate dataset
        print("🔍 Validating dataset...")
        validation = DataFormatter.validate_dataset(
            dataset_path,
            config.prompt_column,
            config.completion_column
        )

        print(f"   Examples: {validation['num_examples']}")
        print(f"   Valid: {validation['valid']}")

        if validation['issues']:
            print("   Issues:")
            for issue in validation['issues']:
                print(f"   - {issue}")

        if not validation['valid']:
            print("❌ Dataset validation failed")
            return None

        # Estimate cost
        cost = config.estimate_cost(validation['num_examples'])
        print(f"\n💰 Estimated cost: ${cost:.2f}")

        if config.max_cost_usd and cost > config.max_cost_usd:
            print(f"❌ Estimated cost ${cost:.2f} exceeds max ${config.max_cost_usd:.2f}")
            return None

        # Display configuration summary
        print(f"\n📋 Fine-tuning Configuration:")
        print(f"   Model: {config.model_name}")
        print(f"   Dataset: {config.dataset_path}")
        print(f"   Examples: {validation['num_examples']}")
        print(f"   Epochs: {config.epochs}")
        print(f"   Batch size: {config.batch_size}")
        print(f"   Learning rate: {config.learning_rate}")
        print(f"   Use LoRA: {config.use_lora}")
        if config.use_lora:
            print(f"   LoRA rank: {config.lora_rank}")
        print(f"   Est. cost: ${cost:.2f}")

        # Request approval
        if approval_callback:
            approved = approval_callback(config, validation)
        else:
            # Default: interactive approval
            response = input("\n⚠️  Proceed with fine-tuning? This will incur costs. [y/N]: ")
            approved = response.lower() in ('y', 'yes')

        if not approved:
            print("❌ Fine-tuning cancelled by user")
            return None

        # Create job
        job_id = f"finetune_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        job = FineTuneJob(
            job_id=job_id,
            config=config,
            status="approved",
        )

        print(f"\n✅ Fine-tuning job approved: {job_id}")
        return job

    def launch_via_notebook(
        self,
        job: FineTuneJob
    ) -> Dict[str, str]:
        """
        Generate instructions for launching fine-tuning via Oxen Marimo notebook.

        Since Oxen.ai uses Marimo notebooks for fine-tuning, this provides
        the user with instructions and a configuration file to use.

        Args:
            job: Approved fine-tuning job

        Returns:
            Dictionary with notebook URL and instructions
        """
        estimated_cost = job.config.estimated_cost_usd if job.config.estimated_cost_usd else 0.0
        lora_rank_str = str(job.config.lora_rank) if job.config.use_lora else 'N/A'

        instructions = {
            "notebook_url": "https://www.oxen.ai/ox/train-llm",
            "instructions": f"""
To launch fine-tuning on Oxen.ai:

1. Open the training notebook:
   {self.client.config.hub_url}/ox/train-llm

2. Fork the notebook to your account

3. Configure the training:
   - Dataset: {self.client.namespace}/{self.client.repo_name}
   - File: {job.config.dataset_path}
   - Model: {job.config.model_name}
   - Prompt column: {job.config.prompt_column}
   - Completion column: {job.config.completion_column}

4. Update hyperparameters:
   - Epochs: {job.config.epochs}
   - Batch size: {job.config.batch_size}
   - Learning rate: {job.config.learning_rate}
   - LoRA rank: {lora_rank_str}

5. Run the notebook on A10G GPU

6. Model will be saved to experiment branch: finetune_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}

Estimated cost: ${estimated_cost:.2f}
""",
            "config_file": job.config.to_dict(),
        }

        # Save config to file
        config_path = f"{job.job_id}_config.json"
        with open(config_path, 'w') as f:
            json.dump(job.config.to_dict(), f, indent=2)

        instructions["config_file_path"] = config_path

        print(instructions["instructions"])
        print(f"\n💾 Configuration saved to: {config_path}")

        return instructions
