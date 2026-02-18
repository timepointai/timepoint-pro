"""
Evaluation framework for comparing base vs. fine-tuned models.

Provides side-by-side comparison utilities for assessing fine-tuning quality.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json


@dataclass
class EvaluationExample:
    """Single example for evaluation."""

    prompt: str
    expected_completion: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    # Results
    base_model_output: Optional[str] = None
    finetuned_model_output: Optional[str] = None

    # Scores (0-100)
    base_model_score: Optional[float] = None
    finetuned_model_score: Optional[float] = None

    # Judging
    human_preference: Optional[str] = None  # "base", "finetuned", "tie"
    auto_judgment: Optional[str] = None

    def winner(self) -> Optional[str]:
        """Determine winner based on scores."""
        if self.base_model_score is None or self.finetuned_model_score is None:
            return None

        diff = abs(self.finetuned_model_score - self.base_model_score)
        if diff < 5:  # Within 5 points = tie
            return "tie"

        return "finetuned" if self.finetuned_model_score > self.base_model_score else "base"


@dataclass
class EvaluationResults:
    """Results from comparing base vs. fine-tuned model."""

    base_model_name: str
    finetuned_model_name: str
    num_examples: int

    # Win rates
    base_wins: int = 0
    finetuned_wins: int = 0
    ties: int = 0

    # Average scores
    avg_base_score: float = 0.0
    avg_finetuned_score: float = 0.0

    # Per-category results
    category_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Individual examples
    examples: List[EvaluationExample] = field(default_factory=list)

    # Metadata
    evaluation_date: datetime = field(default_factory=datetime.utcnow)
    evaluator: str = "auto"  # "auto", "human", "mixed"

    def win_rate_finetuned(self) -> float:
        """Calculate win rate for fine-tuned model."""
        total = self.base_wins + self.finetuned_wins + self.ties
        if total == 0:
            return 0.0
        return self.finetuned_wins / total

    def improvement_percentage(self) -> float:
        """Calculate percentage improvement in average score."""
        if self.avg_base_score == 0:
            return 0.0
        return ((self.avg_finetuned_score - self.avg_base_score) / self.avg_base_score) * 100

    def summary(self) -> str:
        """Generate summary report."""
        return f"""
=== Evaluation Results ===
Base Model: {self.base_model_name}
Fine-tuned Model: {self.finetuned_model_name}
Examples: {self.num_examples}

Win Rates:
  Fine-tuned: {self.finetuned_wins} ({self.win_rate_finetuned():.1%})
  Base: {self.base_wins} ({self.base_wins / self.num_examples if self.num_examples > 0 else 0:.1%})
  Ties: {self.ties} ({self.ties / self.num_examples if self.num_examples > 0 else 0:.1%})

Average Scores:
  Base: {self.avg_base_score:.1f}/100
  Fine-tuned: {self.avg_finetuned_score:.1f}/100
  Improvement: {self.improvement_percentage():+.1f}%

Evaluation Date: {self.evaluation_date.strftime('%Y-%m-%d %H:%M')}
Evaluator: {self.evaluator}
"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "base_model_name": self.base_model_name,
            "finetuned_model_name": self.finetuned_model_name,
            "num_examples": self.num_examples,
            "base_wins": self.base_wins,
            "finetuned_wins": self.finetuned_wins,
            "ties": self.ties,
            "avg_base_score": self.avg_base_score,
            "avg_finetuned_score": self.avg_finetuned_score,
            "win_rate_finetuned": self.win_rate_finetuned(),
            "improvement_percentage": self.improvement_percentage(),
            "category_results": self.category_results,
            "evaluation_date": self.evaluation_date.isoformat(),
            "evaluator": self.evaluator,
        }


class ModelEvaluator:
    """Evaluate and compare model outputs."""

    def __init__(
        self,
        base_model_client: Optional[Any] = None,
        finetuned_model_client: Optional[Any] = None,
        judge_model_client: Optional[Any] = None
    ):
        """
        Initialize evaluator.

        Args:
            base_model_client: Client for base model inference
            finetuned_model_client: Client for fine-tuned model inference
            judge_model_client: Client for LLM-as-judge evaluations
        """
        self.base_model = base_model_client
        self.finetuned_model = finetuned_model_client
        self.judge_model = judge_model_client

    def evaluate_side_by_side(
        self,
        test_examples: List[Dict[str, Any]],
        prompt_key: str = "prompt",
        expected_key: Optional[str] = None,
        use_human_eval: bool = False
    ) -> EvaluationResults:
        """
        Run side-by-side evaluation of base vs. fine-tuned model.

        Args:
            test_examples: List of test examples
            prompt_key: Key for prompt in examples
            expected_key: Key for expected completion (optional)
            use_human_eval: Whether to request human judgments

        Returns:
            EvaluationResults with comparisons
        """
        results = EvaluationResults(
            base_model_name=getattr(self.base_model, 'model_name', 'base_model'),
            finetuned_model_name=getattr(self.finetuned_model, 'model_name', 'finetuned_model'),
            num_examples=len(test_examples),
            evaluator="human" if use_human_eval else "auto"
        )

        total_base_score = 0.0
        total_finetuned_score = 0.0

        for i, example in enumerate(test_examples):
            prompt = example.get(prompt_key, "")
            expected = example.get(expected_key) if expected_key else None

            eval_example = EvaluationExample(
                prompt=prompt,
                expected_completion=expected,
                context=example
            )

            # Generate outputs from both models
            if self.base_model:
                eval_example.base_model_output = self._generate(self.base_model, prompt)

            if self.finetuned_model:
                eval_example.finetuned_model_output = self._generate(self.finetuned_model, prompt)

            # Score outputs
            if use_human_eval:
                self._human_evaluate(eval_example, i + 1, len(test_examples))
            else:
                self._auto_evaluate(eval_example, expected)

            # Update totals
            if eval_example.base_model_score:
                total_base_score += eval_example.base_model_score
            if eval_example.finetuned_model_score:
                total_finetuned_score += eval_example.finetuned_model_score

            # Determine winner
            winner = eval_example.winner()
            if winner == "base":
                results.base_wins += 1
            elif winner == "finetuned":
                results.finetuned_wins += 1
            else:
                results.ties += 1

            results.examples.append(eval_example)

        # Calculate averages
        if len(test_examples) > 0:
            results.avg_base_score = total_base_score / len(test_examples)
            results.avg_finetuned_score = total_finetuned_score / len(test_examples)

        return results

    def _generate(self, model_client: Any, prompt: str) -> str:
        """Generate output from model."""
        # This is a placeholder - actual implementation depends on model client
        if hasattr(model_client, 'generate'):
            return model_client.generate(prompt)
        elif hasattr(model_client, 'complete'):
            return model_client.complete(prompt)
        else:
            return "[Model output placeholder]"

    def _auto_evaluate(
        self,
        example: EvaluationExample,
        expected: Optional[str]
    ):
        """
        Automatically evaluate outputs.

        Uses simple heuristics or LLM-as-judge if judge_model is available.
        """
        if self.judge_model and expected:
            # Use LLM as judge
            example.base_model_score = self._llm_judge(
                example.prompt,
                example.base_model_output,
                expected
            )
            example.finetuned_model_score = self._llm_judge(
                example.prompt,
                example.finetuned_model_output,
                expected
            )
        else:
            # Simple heuristics
            if expected:
                example.base_model_score = self._simple_score(
                    example.base_model_output,
                    expected
                )
                example.finetuned_model_score = self._simple_score(
                    example.finetuned_model_output,
                    expected
                )
            else:
                # If no expected output, give neutral scores
                example.base_model_score = 50.0
                example.finetuned_model_score = 50.0

    def _simple_score(self, output: Optional[str], expected: str) -> float:
        """
        Simple scoring based on length and keyword overlap.

        Args:
            output: Model output
            expected: Expected output

        Returns:
            Score from 0-100
        """
        if not output:
            return 0.0

        # Keyword overlap
        output_words = set(output.lower().split())
        expected_words = set(expected.lower().split())

        if not expected_words:
            return 50.0

        overlap = len(output_words & expected_words)
        overlap_score = (overlap / len(expected_words)) * 100

        # Length similarity
        length_ratio = min(len(output), len(expected)) / max(len(output), len(expected))
        length_score = length_ratio * 100

        # Weighted average
        return (overlap_score * 0.7) + (length_score * 0.3)

    def _llm_judge(
        self,
        prompt: str,
        output: Optional[str],
        expected: str
    ) -> float:
        """
        Use LLM as judge to score output.

        Args:
            prompt: Original prompt
            output: Model output
            expected: Expected output

        Returns:
            Score from 0-100
        """
        if not output:
            return 0.0

        judge_prompt = f"""Rate the quality of this model output on a scale of 0-100.

Prompt: {prompt}

Expected output: {expected}

Actual output: {output}

Consider:
- Accuracy: Does it match the expected content?
- Completeness: Does it cover all important points?
- Coherence: Is it well-structured and logical?
- Style: Does it match the expected tone/format?

Provide ONLY a number from 0-100 as your response."""

        try:
            judgment = self._generate(self.judge_model, judge_prompt)
            # Extract number from response
            import re
            numbers = re.findall(r'\d+', judgment)
            if numbers:
                score = float(numbers[0])
                return min(100.0, max(0.0, score))
        except:
            pass

        # Fallback to simple scoring
        return self._simple_score(output, expected)

    def _human_evaluate(
        self,
        example: EvaluationExample,
        current: int,
        total: int
    ):
        """
        Request human evaluation of outputs.

        Args:
            example: Evaluation example
            current: Current example number
            total: Total examples
        """
        print(f"\n{'=' * 70}")
        print(f"Example {current}/{total}")
        print(f"{'=' * 70}")
        print(f"Prompt:\n{example.prompt}\n")

        if example.expected_completion:
            print(f"Expected:\n{example.expected_completion}\n")

        print(f"Base Model Output:\n{example.base_model_output}\n")
        print(f"Fine-tuned Model Output:\n{example.finetuned_model_output}\n")

        # Get scores
        while True:
            try:
                base_score = float(input("Score base model (0-100): "))
                if 0 <= base_score <= 100:
                    example.base_model_score = base_score
                    break
                print("Please enter a number between 0 and 100")
            except ValueError:
                print("Please enter a valid number")

        while True:
            try:
                ft_score = float(input("Score fine-tuned model (0-100): "))
                if 0 <= ft_score <= 100:
                    example.finetuned_model_score = ft_score
                    break
                print("Please enter a number between 0 and 100")
            except ValueError:
                print("Please enter a valid number")

        # Get preference
        pref = input("Which is better? [B]ase / [F]ine-tuned / [T]ie: ").strip().lower()
        if pref in ('b', 'base'):
            example.human_preference = "base"
        elif pref in ('f', 'finetuned', 'fine-tuned'):
            example.human_preference = "finetuned"
        else:
            example.human_preference = "tie"


class TimepointEvaluator:
    """
    Specialized evaluator for Timepoint-Pro simulation quality.

    Evaluates models on their ability to generate realistic temporal simulations.
    """

    @staticmethod
    def create_test_prompts(
        scenarios: List[str],
        timepoint_configs: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Create evaluation prompts for Timepoint simulations.

        Args:
            scenarios: List of scenario descriptions
            timepoint_configs: List of configuration dicts

        Returns:
            List of test examples with prompts
        """
        test_examples = []

        for scenario in scenarios:
            for config in timepoint_configs:
                prompt = f"""Generate a simulation configuration for the following scenario:

Scenario: {scenario}

Configuration requirements:
- Entities: {config.get('num_entities', 5)}
- Timepoints: {config.get('num_timepoints', 3)}
- Resolution: {config.get('resolution', 'hour')}
- Mode: {config.get('mode', 'forward')}

Provide the configuration in JSON format."""

                test_examples.append({
                    "prompt": prompt,
                    "scenario": scenario,
                    "config": config
                })

        return test_examples

    @staticmethod
    def evaluate_simulation_quality(
        base_output: str,
        finetuned_output: str,
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Evaluate quality of generated simulation configurations.

        Args:
            base_output: Base model output
            finetuned_output: Fine-tuned model output
            context: Context about the simulation requirements

        Returns:
            Dictionary with quality scores
        """
        scores = {
            "base_completeness": 0.0,
            "finetuned_completeness": 0.0,
            "base_validity": 0.0,
            "finetuned_validity": 0.0,
            "base_relevance": 0.0,
            "finetuned_relevance": 0.0,
        }

        # Check for required fields
        required_fields = ["entities", "timepoints", "scenario_description"]

        for prefix, output in [("base", base_output), ("finetuned", finetuned_output)]:
            try:
                config = json.loads(output)

                # Completeness: Has all required fields?
                complete_fields = sum(1 for f in required_fields if f in config)
                scores[f"{prefix}_completeness"] = (complete_fields / len(required_fields)) * 100

                # Validity: Are values reasonable?
                valid = True
                if "entities" in config:
                    entity_count = config["entities"].get("count", 0)
                    valid = valid and (1 <= entity_count <= 100)

                if "timepoints" in config:
                    tp_count = config["timepoints"].get("count", 0)
                    valid = valid and (1 <= tp_count <= 50)

                scores[f"{prefix}_validity"] = 100.0 if valid else 0.0

                # Relevance: Does scenario match requirements?
                if "scenario_description" in config:
                    scenario = config["scenario_description"].lower()
                    context_scenario = context.get("scenario", "").lower()
                    # Simple keyword overlap
                    overlap = any(word in scenario for word in context_scenario.split())
                    scores[f"{prefix}_relevance"] = 100.0 if overlap else 50.0

            except json.JSONDecodeError:
                # Invalid JSON
                scores[f"{prefix}_completeness"] = 0.0
                scores[f"{prefix}_validity"] = 0.0
                scores[f"{prefix}_relevance"] = 0.0

        return scores
