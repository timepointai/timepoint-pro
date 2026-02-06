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
        training_data: Optional[List[Dict]] = None,
        all_timepoints: Optional[List] = None,
        entities: Optional[List] = None,
        store = None
    ) -> str:
        """
        Generate narrative summary using LLM (like a plot synopsis).

        Args:
            run_metadata: Complete run metadata from database
            training_data: Optional training examples generated during run
            all_timepoints: Full list of timepoints (narrative arc)
            entities: Full list of trained entities (character development)
            store: GraphStore for accessing dialogs

        Returns:
            Narrative summary (300-500 words, 3-4 paragraphs, plot-focused)
        """
        # Collect all run artifacts
        artifacts = self._collect_run_artifacts(run_metadata, training_data)

        # Format prompt for LLM (narrative-focused if we have full data)
        if all_timepoints and entities:
            prompt = self._format_narrative_prompt(artifacts, all_timepoints, entities, store)
        else:
            # Fallback to metadata summary if narrative data unavailable
            prompt = self._format_summary_prompt(artifacts)

        # Call LLM with retry logic (use Haiku for cost efficiency: ~$0.003 per narrative summary)
        import time
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                response = self.llm.service.call(
                    system="You are an expert at writing compelling narrative summaries of historical simulations.",
                    user=prompt,
                    model="anthropic/claude-3-5-haiku-20241022",
                    max_tokens=800,  # Increased for narrative summaries
                    temperature=0.7,  # Higher temp for creative narrative
                    call_type="generate_summary"
                )
                summary = response.content.strip() if response.success else None
                if not summary:
                    raise ValueError("LLM returned empty response")
                return summary  # Success, return immediately

            except Exception as e:
                error_str = str(e).lower()
                # Check if this is a rate limit error (429)
                is_rate_limit = "429" in error_str or "rate limit" in error_str or "too many requests" in error_str

                if is_rate_limit and attempt < max_retries - 1:
                    # Exponential backoff for rate limits
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Non-rate-limit error or final attempt - fall back
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

    def _format_narrative_prompt(self, artifacts: Dict[str, Any], all_timepoints: List, entities: List, store) -> str:
        """
        Build NARRATIVE summary prompt (like a movie plot synopsis).

        Focus on story, character decisions, drama, and outcomes rather than metadata.

        Returns:
            Narrative-focused prompt string
        """
        # Extract narrative arc from timepoints
        timeline = "\n".join([
            f"{i+1}. {tp.timestamp if hasattr(tp, 'timestamp') else 'Time unknown'} - {tp.event_description if hasattr(tp, 'event_description') else str(tp)}"
            for i, tp in enumerate(all_timepoints[:10])  # Limit to first 10 to avoid huge prompts
        ])

        if len(all_timepoints) > 10:
            timeline += f"\n... ({len(all_timepoints) - 10} more timepoints)"

        # Character summaries
        characters = []
        for e in entities[:15]:  # Limit to 15 main characters
            if hasattr(e, 'entity_id') and hasattr(e, 'entity_type'):
                knowledge_count = len(e.knowledge_state) if hasattr(e, 'knowledge_state') and e.knowledge_state else 0
                characters.append(f"- **{e.entity_id}**: {e.entity_type}, {knowledge_count} knowledge items")

        characters_text = "\n".join(characters) if characters else "(No character data available)"

        if len(entities) > 15:
            characters_text += f"\n... ({len(entities) - 15} more characters)"

        # Sample dialogs from store (if available)
        dialog_excerpt = ""
        if store:
            try:
                dialogs = store.load_all_dialogs()
                if dialogs and len(dialogs) > 0:
                    first_dialog = dialogs[0]
                    # Deserialize JSON string from DB storage
                    turns_data = first_dialog.turns if hasattr(first_dialog, 'turns') else []
                    if isinstance(turns_data, str):
                        turns_data = json.loads(turns_data)
                    if turns_data and len(turns_data) > 0:
                        excerpt_turns = []
                        for turn in turns_data[:3]:  # First 3 turns
                            if isinstance(turn, dict):
                                speaker = turn.get('speaker', 'Unknown')
                                content = turn.get('content', str(turn))
                            else:
                                speaker = turn.speaker if hasattr(turn, 'speaker') else 'Unknown'
                                content = turn.content if hasattr(turn, 'content') else str(turn)
                            excerpt_turns.append(f"{speaker}: {content[:100]}...")
                        dialog_excerpt = "\n".join(excerpt_turns)
            except Exception as e:
                dialog_excerpt = f"(Dialog loading failed: {e})"

        if not dialog_excerpt:
            dialog_excerpt = "(No dialogs available)"

        prompt = f"""You are writing a compelling narrative summary of a historical simulation.

This is like writing a **plot synopsis** for a screenplay or novel. Focus on:
1. The STORY that unfolded (what happened?)
2. Character decisions, conflicts, and development (who did what?)
3. Dramatic moments and turning points (key scenes)
4. Final outcome and its significance (how did it end?)

Write 3-4 paragraphs that capture the narrative arc like you're describing a film to a friend.

## Scenario

**Title**: {artifacts['template_id']}
**Mode**: {artifacts['causal_mode']} causality
**Setting**: {all_timepoints[0].event_description if hasattr(all_timepoints[0], 'event_description') else 'Historical simulation'}

## Timeline of Events

{timeline}

## Characters

{characters_text}

## Sample Dialog

{dialog_excerpt}

## Your Task

Write a narrative summary (3-4 paragraphs, 300-500 words) that tells the STORY:

**Paragraph 1**: Setup and initial situation
**Paragraph 2**: Rising action, key decisions, and conflicts
**Paragraph 3**: Climax and resolution
**Paragraph 4** (optional): Reflection on significance and outcome

Make it read like a compelling plot synopsis, NOT a technical report.
Use past tense, third person narrative voice.
Focus on human drama and meaningful choices, not statistics.

**Example style**: "In 1787 Philadelphia, delegates gathered at the Constitutional Convention facing an impossible task: create a lasting government for a fractious new nation. Madison's Virginia Plan proposed a strong central government, immediately sparking fierce debate..."

Summary:"""

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
    llm_client: Optional[LLMClient] = None,
    all_timepoints: Optional[List] = None,
    entities: Optional[List] = None,
    store = None
) -> str:
    """
    Convenience function to generate narrative summary for a run.

    Args:
        run_metadata: Complete run metadata
        training_data: Optional training examples
        llm_client: Optional LLM client (creates new one if None)
        all_timepoints: Full list of timepoints (for narrative arc)
        entities: Full list of trained entities (for character development)
        store: GraphStore for accessing dialogs

    Returns:
        Generated narrative summary string (plot synopsis style)
    """
    summarizer = RunSummarizer(llm_client)
    return summarizer.generate_summary(run_metadata, training_data, all_timepoints, entities, store)
