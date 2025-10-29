"""
Run Summarizer - LLM-powered summary generation for simulation runs

Generates concise 3-5 sentence summaries of each E2E workflow run by:
- Collecting run metadata, mechanisms used, validations, and training data
- Formatting structured prompt for LLM
- Calling LLM to generate narrative summary
- Returning summary for storage in database
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
from llm_v2 import LLMClient
from metadata.run_tracker import RunMetadata


class RunSummarizer:
    """Generates LLM-powered summaries of simulation runs"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize summarizer with LLM client.

        Args:
            llm_client: LLM client for summary generation. If None, creates new client.
        """
        self.llm = llm_client or LLMClient()

    def generate_summary(
        self,
        run_metadata: RunMetadata,
        training_data: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate concise 3-5 sentence summary using LLM.

        Args:
            run_metadata: Complete run metadata from database
            training_data: Optional training examples generated during run

        Returns:
            Short narrative summary (150-300 tokens, 3-5 sentences)
        """
        # Collect all run artifacts
        artifacts = self._collect_run_artifacts(run_metadata, training_data)

        # Format prompt for LLM
        prompt = self._format_summary_prompt(artifacts)

        # Call LLM (use Haiku for cost efficiency: ~$0.001 per summary)
        try:
            response = self.llm.generate(
                prompt=prompt,
                model="anthropic/claude-3-5-haiku-20241022",
                max_tokens=300,
                temperature=0.3  # Low temp for consistent, focused summaries
            )
            summary = response.strip()
        except Exception as e:
            # Fallback to structured summary if LLM fails
            summary = self._generate_fallback_summary(artifacts)
            summary += f" (LLM summary unavailable: {str(e)})"

        return summary

    def _collect_run_artifacts(
        self,
        metadata: RunMetadata,
        training_data: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """
        Gather key information for summary.

        Returns:
            Dictionary with all relevant run information
        """
        artifacts = {
            # Basic info
            "run_id": metadata.run_id,
            "template_id": metadata.template_id,
            "status": metadata.status,

            # Configuration
            "causal_mode": metadata.causal_mode.value if hasattr(metadata.causal_mode, 'value') else str(metadata.causal_mode),
            "max_entities": metadata.max_entities,
            "max_timepoints": metadata.max_timepoints,

            # Results
            "entities_created": metadata.entities_created,
            "timepoints_created": metadata.timepoints_created,
            "training_examples": metadata.training_examples,

            # Mechanisms
            "mechanisms_used": sorted(list(metadata.mechanisms_used)),
            "mechanism_count": len(metadata.mechanisms_used),

            # Cost & performance
            "cost_usd": metadata.cost_usd,
            "duration_seconds": metadata.duration_seconds,
            "llm_calls": metadata.llm_calls,
            "tokens_used": metadata.tokens_used,

            # Validations (if available)
            "validations_passed": sum(1 for v in metadata.validations if v.passed) if metadata.validations else 0,
            "validations_failed": sum(1 for v in metadata.validations if not v.passed) if metadata.validations else 0,

            # Resolution diversity (if available)
            "resolution_diversity": len(set(r.resolution for r in metadata.resolution_assignments)) if metadata.resolution_assignments else 0,

            # Training data sample
            "training_data_sample": training_data[:3] if training_data else None,

            # Error info
            "error_message": metadata.error_message,

            # Oxen upload
            "oxen_uploaded": bool(metadata.oxen_dataset_url)
        }

        return artifacts

    def _format_summary_prompt(self, artifacts: Dict[str, Any]) -> str:
        """
        Build LLM prompt from run artifacts.

        Returns:
            Structured prompt for LLM summary generation
        """
        prompt = f"""You are summarizing a temporal simulation run from the Timepoint-Daedalus system.

Generate a concise 3-5 sentence summary that captures:
1. What was simulated (template/scenario)
2. Key results (entities, timepoints, training examples)
3. Notable mechanisms or features used
4. Overall outcome (success/failure, cost, duration)

Keep it SHORT and INFORMATIVE. Use past tense. Focus on outcomes, not process.

## Run Information

Template: {artifacts['template_id']}
Status: {artifacts['status']}
Causal Mode: {artifacts['causal_mode']}

## Configuration

Max Entities: {artifacts['max_entities']}
Max Timepoints: {artifacts['max_timepoints']}

## Results

Entities Created: {artifacts['entities_created']}
Timepoints Created: {artifacts['timepoints_created']}
Training Examples: {artifacts['training_examples']}

## Mechanisms Used ({artifacts['mechanism_count']})

{', '.join(artifacts['mechanisms_used']) if artifacts['mechanisms_used'] else 'None'}

## Performance

Cost: ${artifacts['cost_usd']:.2f}
Duration: {artifacts['duration_seconds']:.1f}s
LLM Calls: {artifacts['llm_calls']}
Tokens: {artifacts['tokens_used']:,}

## Validations

Passed: {artifacts['validations_passed']}
Failed: {artifacts['validations_failed']}

## Resolution Diversity

{artifacts['resolution_diversity']} different resolution levels used

"""

        if artifacts['error_message']:
            prompt += f"\n## Error\n\n{artifacts['error_message']}\n"

        if artifacts['oxen_uploaded']:
            prompt += "\n## Data Upload\n\nTraining data uploaded to Oxen.ai\n"

        if artifacts['training_data_sample']:
            prompt += f"\n## Training Data Sample (first 3 examples)\n\n"
            for i, example in enumerate(artifacts['training_data_sample'], 1):
                prompt += f"Example {i}:\n"
                prompt += f"  Input: {example.get('messages', [{}])[0].get('content', 'N/A')[:100]}...\n"
                prompt += f"  Output: {example.get('messages', [{}])[-1].get('content', 'N/A')[:100]}...\n\n"

        prompt += "\n## Your Task\n\nGenerate a 3-5 sentence summary. Be concise and informative.\n\nSummary:"

        return prompt

    def _generate_fallback_summary(self, artifacts: Dict[str, Any]) -> str:
        """
        Generate structured summary if LLM is unavailable.

        Returns:
            Template-based summary string
        """
        status_verb = "completed" if artifacts['status'] == "completed" else "failed"

        summary = (
            f"Simulation of {artifacts['template_id']} {status_verb} using {artifacts['causal_mode']} causality. "
            f"Generated {artifacts['entities_created']} entities across {artifacts['timepoints_created']} timepoints, "
            f"producing {artifacts['training_examples']} training examples. "
            f"Used {artifacts['mechanism_count']} mechanisms ({', '.join(artifacts['mechanisms_used'][:3])}{'...' if len(artifacts['mechanisms_used']) > 3 else ''}). "
            f"Cost: ${artifacts['cost_usd']:.2f}, Duration: {artifacts['duration_seconds']:.1f}s."
        )

        return summary


def generate_run_summary(
    run_metadata: RunMetadata,
    training_data: Optional[List[Dict]] = None,
    llm_client: Optional[LLMClient] = None
) -> str:
    """
    Convenience function to generate summary for a run.

    Args:
        run_metadata: Complete run metadata
        training_data: Optional training examples
        llm_client: Optional LLM client (creates new one if None)

    Returns:
        Generated summary string
    """
    summarizer = RunSummarizer(llm_client)
    return summarizer.generate_summary(run_metadata, training_data)
