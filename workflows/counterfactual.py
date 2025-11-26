# ============================================================================
# workflows/counterfactual.py - Counterfactual Branching (Mechanism 12)
# ============================================================================
"""
Counterfactual timeline branching and comparison.

Contains:
- create_counterfactual_branch: Create a branch with an intervention (@M12)
- apply_intervention_to_timepoint: Apply intervention to timepoint
- propagate_causality_from_branch: Propagate effects forward
- compare_timelines: Compare baseline and counterfactual
- generate_causal_explanation: Explain timeline differences
- find_first_divergence: Find divergence point
"""

from typing import List, Dict, Optional
import uuid

from metadata.tracking import track_mechanism


@track_mechanism("M12", "counterfactual_branching")
def create_counterfactual_branch(
    parent_timeline_id: str,
    intervention_point: str,
    intervention: 'Intervention',
    store: 'GraphStore',
    llm_client=None
) -> str:
    """Create a counterfactual branch from a parent timeline with an intervention"""

    # Generate new timeline ID
    branch_timeline_id = f"branch_{uuid.uuid4().hex[:8]}"

    # Get parent timeline info
    parent_timepoints = store.get_timepoints(parent_timeline_id)
    intervention_timepoint = None

    # Find the intervention timepoint
    for tp in parent_timepoints:
        if tp.timepoint_id == intervention_point:
            intervention_timepoint = tp
            break

    if not intervention_timepoint:
        raise ValueError(f"Intervention point {intervention_point} not found in timeline {parent_timeline_id}")

    # Optional: Use LLM to predict counterfactual outcomes
    llm_prediction = None
    if llm_client is not None:
        try:
            # Gather baseline timeline info
            baseline_info = {
                'timeline_id': parent_timeline_id,
                'event_summary': ', '.join([tp.event_description for tp in parent_timepoints[:5]]),
                'key_entities': list(set([e for tp in parent_timepoints if hasattr(tp, 'entities_present') for e in tp.entities_present]))[:10]
            }

            # Intervention info
            intervention_info = {
                'type': intervention.type,
                'target': intervention.target,
                'description': intervention.description or f"{intervention.type} on {intervention.target}",
                'intervention_point': intervention_point,
                'parameters': intervention.parameters if hasattr(intervention, 'parameters') else {}
            }

            # Get affected entities
            affected_entities = []
            if hasattr(intervention_timepoint, 'entities_present'):
                for entity_id in intervention_timepoint.entities_present[:10]:
                    affected_entities.append({'entity_id': entity_id})

            # Get LLM prediction
            llm_prediction = llm_client.predict_counterfactual_outcome(
                baseline_timeline=baseline_info,
                intervention=intervention_info,
                affected_entities=affected_entities
            )

        except Exception as e:
            # If prediction fails, continue with deterministic branching
            pass

    # Copy timepoints before intervention
    copied_timepoints = []
    for tp in parent_timepoints:
        if tp.timestamp <= intervention_timepoint.timestamp:
            # Create a copy of the timepoint for the new timeline
            copied_tp = tp.copy() if hasattr(tp, 'copy') else tp
            copied_tp.timeline_id = branch_timeline_id
            copied_timepoints.append(copied_tp)
            store.save_timepoint(copied_tp)

    # Apply intervention at branch point (enhanced with LLM prediction if available)
    branch_timepoint = apply_intervention_to_timepoint(
        intervention_timepoint, intervention, branch_timeline_id, llm_prediction
    )
    store.save_timepoint(branch_timepoint)

    # Create timeline record
    from schemas import Timeline
    branch_timeline = Timeline(
        timeline_id=branch_timeline_id,
        parent_timeline_id=parent_timeline_id,
        branch_point=intervention_point,
        intervention_description=intervention.description or f"{intervention.type} on {intervention.target}",
        # Copy other timeline metadata from parent
        timepoint_id=f"{branch_timeline_id}_root",
        timestamp=intervention_timepoint.timestamp,
        resolution=intervention_timepoint.resolution if hasattr(intervention_timepoint, 'resolution') else "day",
        entities_present=intervention_timepoint.entities_present.copy() if hasattr(intervention_timepoint, 'entities_present') else [],
        events=intervention_timepoint.events.copy() if hasattr(intervention_timepoint, 'events') else []
    )
    store.save_timeline(branch_timeline)

    return branch_timeline_id


def apply_intervention_to_timepoint(
    timepoint: 'Timepoint',
    intervention: 'Intervention',
    new_timeline_id: str,
    llm_prediction: Optional[Dict] = None
) -> 'Timepoint':
    """Apply an intervention to a timepoint, creating a modified version"""
    # Create a copy of the timepoint
    modified_tp = timepoint.copy() if hasattr(timepoint, 'copy') else timepoint
    modified_tp.timeline_id = new_timeline_id

    # If LLM prediction is available, enhance the event description
    if llm_prediction:
        immediate_effects = llm_prediction.get('immediate_effects', [])
        if immediate_effects:
            modified_tp.event_description = f"{modified_tp.event_description} [LLM Prediction: {'; '.join(immediate_effects[:2])}]"

    if intervention.type == "entity_removal":
        # Remove entity from entities_present
        if hasattr(modified_tp, 'entities_present') and intervention.target in modified_tp.entities_present:
            modified_tp.entities_present.remove(intervention.target)
            # Modify event description to reflect the removal
            modified_tp.event_description = f"{modified_tp.event_description} (Note: {intervention.target} was not present)"

    elif intervention.type == "entity_modification":
        # Modify entity properties (would need entity access)
        # For now, just modify the event description
        modifications = intervention.parameters.get('modifications', {})
        if modifications:
            mod_str = ", ".join([f"{k}={v}" for k, v in modifications.items()])
            modified_tp.event_description = f"{modified_tp.event_description} (Modified: {intervention.target} {mod_str})"

    elif intervention.type == "event_cancellation":
        # Cancel or modify the event
        modified_tp.event_description = f"EVENT CANCELLED: {intervention.target}"

    elif intervention.type == "knowledge_alteration":
        # Modify knowledge state (would need entity access)
        # For now, modify event description
        modified_tp.event_description = f"{modified_tp.event_description} (Knowledge altered for {intervention.target})"

    else:
        # Unknown intervention type
        modified_tp.event_description = f"{modified_tp.event_description} (Intervention: {intervention.type} on {intervention.target})"

    return modified_tp


def propagate_causality_from_branch(
    branch_timeline_id: str,
    intervention_timepoint: 'Timepoint',
    store: 'GraphStore'
) -> None:
    """Propagate causal effects forward from the intervention point"""
    # Get subsequent timepoints in the parent timeline
    parent_timeline_id = store.get_timeline(branch_timeline_id).parent_timeline_id
    if not parent_timeline_id:
        return

    parent_timepoints = store.get_timepoints(parent_timeline_id)
    subsequent_timepoints = [
        tp for tp in parent_timepoints
        if tp.timestamp > intervention_timepoint.timestamp
    ]

    # For each subsequent timepoint, create a modified version for the branch
    for parent_tp in subsequent_timepoints:
        # Apply ripple effects of the intervention
        branch_tp = parent_tp.copy() if hasattr(parent_tp, 'copy') else parent_tp
        branch_tp.timeline_id = branch_timeline_id

        # Modify based on intervention type and target
        # This is a simplified version - real implementation would be more sophisticated
        branch_tp.event_description = f"{branch_tp.event_description} (following intervention at {intervention_timepoint.timepoint_id})"

        store.save_timepoint(branch_tp)


def compare_timelines(
    baseline_timeline_id: str,
    counterfactual_timeline_id: str,
    store: 'GraphStore'
) -> 'BranchComparison':
    """Compare two timeline branches and analyze differences"""
    from schemas import BranchComparison

    # Get timepoints for both timelines
    baseline_timepoints = store.get_timepoints(baseline_timeline_id)
    counterfactual_timepoints = store.get_timepoints(counterfactual_timeline_id)

    # Sort by timestamp
    baseline_timepoints.sort(key=lambda tp: tp.timestamp)
    counterfactual_timepoints.sort(key=lambda tp: tp.timestamp)

    # Find divergence point
    divergence_point = None
    min_length = min(len(baseline_timepoints), len(counterfactual_timepoints))

    for i in range(min_length):
        if baseline_timepoints[i].event_description != counterfactual_timepoints[i].event_description:
            divergence_point = baseline_timepoints[i].timepoint_id
            break

    # Calculate basic metrics
    metrics = {}

    # Entity count difference (count unique entities across all timepoints)
    baseline_entities = set()
    for tp in baseline_timepoints:
        if hasattr(tp, 'entities_present') and tp.entities_present:
            baseline_entities.update(tp.entities_present)

    counterfactual_entities = set()
    for tp in counterfactual_timepoints:
        if hasattr(tp, 'entities_present') and tp.entities_present:
            counterfactual_entities.update(tp.entities_present)

    baseline_entity_count = len(baseline_entities)
    counterfactual_entity_count = len(counterfactual_entities)

    metrics["entity_count"] = {
        "baseline": float(baseline_entity_count),
        "counterfactual": float(counterfactual_entity_count),
        "delta": float(counterfactual_entity_count - baseline_entity_count)
    }

    # Timepoint count difference
    metrics["timepoint_count"] = {
        "baseline": float(len(baseline_timepoints)),
        "counterfactual": float(len(counterfactual_timepoints)),
        "delta": float(len(counterfactual_timepoints) - len(baseline_timepoints))
    }

    # Identify key events that differed
    key_events_differed = []
    entity_states_differed = []

    for i in range(min_length):
        baseline_tp = baseline_timepoints[i]
        counterfactual_tp = counterfactual_timepoints[i]

        if baseline_tp.event_description != counterfactual_tp.event_description:
            key_events_differed.append(f"{baseline_tp.timepoint_id}: '{baseline_tp.event_description}' -> '{counterfactual_tp.event_description}'")

        # Check entity presence differences
        if hasattr(baseline_tp, 'entities_present') and hasattr(counterfactual_tp, 'entities_present'):
            baseline_entities = set(baseline_tp.entities_present)
            counterfactual_entities = set(counterfactual_tp.entities_present)
            if baseline_entities != counterfactual_entities:
                added = counterfactual_entities - baseline_entities
                removed = baseline_entities - counterfactual_entities
                if added or removed:
                    entity_states_differed.append(f"{baseline_tp.timepoint_id}: added={list(added)}, removed={list(removed)}")

    # Generate causal explanation
    causal_explanation = generate_causal_explanation(
        baseline_timeline_id, counterfactual_timeline_id, divergence_point, store
    )

    return BranchComparison(
        baseline_timeline=baseline_timeline_id,
        counterfactual_timeline=counterfactual_timeline_id,
        divergence_point=divergence_point,
        metrics=metrics,
        causal_explanation=causal_explanation,
        key_events_differed=key_events_differed,
        entity_states_differed=entity_states_differed
    )


def generate_causal_explanation(
    baseline_timeline_id: str,
    counterfactual_timeline_id: str,
    divergence_point: Optional[str],
    store: 'GraphStore'
) -> str:
    """Generate a causal explanation for timeline differences"""
    if not divergence_point:
        return "Timelines are identical - no divergence detected"

    # Get the branch timeline info
    branch_timeline = store.get_timeline(counterfactual_timeline_id)
    if not branch_timeline or not branch_timeline.intervention_description:
        return f"Divergence at {divergence_point}, but no intervention details available"

    intervention_desc = branch_timeline.intervention_description

    return f"The counterfactual timeline diverges at {divergence_point} due to intervention: {intervention_desc}. This caused cascading changes in subsequent events and entity states."


def find_first_divergence(baseline_timepoints: List, counterfactual_timepoints: List) -> Optional[str]:
    """Find the first timepoint where two timeline branches diverge"""
    min_length = min(len(baseline_timepoints), len(counterfactual_timepoints))

    for i in range(min_length):
        baseline_tp = baseline_timepoints[i]
        counterfactual_tp = counterfactual_timepoints[i]

        # Check if descriptions differ
        if baseline_tp.event_description != counterfactual_tp.event_description:
            return baseline_tp.timepoint_id

        # Check if entity presence differs
        if hasattr(baseline_tp, 'entities_present') and hasattr(counterfactual_tp, 'entities_present'):
            if set(baseline_tp.entities_present) != set(counterfactual_tp.entities_present):
                return baseline_tp.timepoint_id

    return None
