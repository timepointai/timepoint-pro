# ============================================================================
# workflows/prospection.py - Entity Prospection (Mechanism 15)
# ============================================================================
"""
Entity prospection and future expectation generation.

Contains:
- generate_prospective_state: Generate entity's expectations about future (@M15)
- influence_behavior_from_expectations: Modify behavior based on expectations
- update_forecast_accuracy: Update entity's forecasting ability
- Helper functions for anxiety computation, energy costs
"""

from typing import List, Dict, Optional
import uuid

from schemas import Entity, ProspectiveState, Expectation
from metadata.tracking import track_mechanism


def compute_anxiety_from_expectations(expectations: List[Expectation]) -> float:
    """Calculate anxiety level from expectations"""
    if not expectations:
        return 0.0

    anxiety_factors = []
    for exp in expectations:
        # Anxiety increases with:
        # - Uncertainty (probability near 0.5)
        # - Undesired outcomes with moderate-to-high probability
        # - Low confidence in expectation

        probability = exp.subjective_probability
        uncertainty = abs(probability - 0.5) * 2  # 0 (certain) to 1 (50/50)
        undesired_risk = 0.0

        if not exp.desired_outcome:
            # For undesired outcomes, anxiety increases with probability
            undesired_risk = probability
        # For desired outcomes, we might still have anxiety if probability is low
        elif exp.desired_outcome and probability < 0.5:
            undesired_risk = (0.5 - probability) * 0.5  # Some anxiety about desired but unlikely outcomes

        confidence_penalty = 1 - exp.confidence

        # Weight the factors: uncertainty, undesired risk, confidence
        anxiety = (uncertainty * 0.3 + undesired_risk * 0.5 + confidence_penalty * 0.2)
        anxiety_factors.append(anxiety)

    # Average anxiety across all expectations
    base_anxiety = sum(anxiety_factors) / len(anxiety_factors)

    # Scale to 0-1 range with some bounds
    return min(1.0, max(0.0, base_anxiety))


def estimate_energy_cost_for_preparation(action: str, hour: Optional[int] = None,
                                         circadian_config: Optional[Dict] = None) -> float:
    """Estimate energy cost for a preparation action with optional M14 circadian adjustment"""
    # Base cost estimation
    action_costs = {
        "prepare_speech": 8.0,
        "gather_information": 5.0,
        "make_arrangements": 6.0,
        "practice_skills": 7.0,
        "seek_allies": 4.0,
        "avoid_conflict": 3.0,
        "stock_supplies": 5.0,
        "plan_escape": 6.0
    }
    base_cost = action_costs.get(action, 5.0)  # Default cost

    # Apply M14 circadian adjustment if hour and config provided
    if hour is not None and circadian_config:
        from validation import compute_energy_cost_with_circadian
        return compute_energy_cost_with_circadian(
            activity=action,
            hour=hour,
            base_cost=base_cost,
            circadian_config=circadian_config
        )

    return base_cost


@track_mechanism("M15", "entity_prospection")
def generate_prospective_state(
    entity: Entity,
    timepoint: 'Timepoint',
    llm: 'LLMClient',
    store: Optional['GraphStore'] = None
) -> ProspectiveState:
    """Generate an entity's prospective state with expectations about the future"""

    # Get prospection config
    config = {}  # Would load from config in real implementation
    forecast_horizon = config.get('forecast_horizon_days', 30)
    max_expectations = config.get('max_expectations', 5)

    # Build context for LLM
    context = {
        "entity_id": entity.entity_id,
        "entity_type": getattr(entity, 'entity_type', 'person'),
        "current_timepoint": timepoint.event_description,
        "current_timestamp": timepoint.timestamp.isoformat(),
        "knowledge_sample": list(entity.entity_metadata.get("knowledge_state", []))[:10],  # Sample recent knowledge
        "personality": getattr(entity, 'personality_traits', {}),
        "forecast_horizon_days": forecast_horizon,
        "max_expectations": max_expectations
    }

    # Generate expectations using LLM
    entity_context = {
        'entity_id': entity.entity_id,
        'entity_type': getattr(entity, 'entity_type', 'person'),
        'knowledge_sample': list(entity.entity_metadata.get("knowledge_state", []))[:10],
        'personality': getattr(entity, 'personality_traits', {}),
        'forecast_horizon_days': forecast_horizon,
        'max_expectations': max_expectations
    }

    timepoint_context = {
        'current_timepoint': timepoint.event_description,
        'current_timestamp': timepoint.timestamp.isoformat()
    }

    try:
        expectations = llm.generate_expectations(entity_context, timepoint_context)
        if not isinstance(expectations, list):
            expectations = []
    except Exception as e:
        # Fallback to mock expectations if LLM fails
        expectations = [
            Expectation(
                predicted_event="Routine continues normally",
                subjective_probability=0.7,
                desired_outcome=True,
                preparation_actions=["maintain_current_course"],
                confidence=0.8
            ),
            Expectation(
                predicted_event="Unexpected challenges arise",
                subjective_probability=0.3,
                desired_outcome=False,
                preparation_actions=["stay_alert", "prepare_contingencies"],
                confidence=0.6
            )
        ]

    # Limit to max expectations
    expectations = expectations[:max_expectations]

    # Calculate anxiety level
    anxiety_level = compute_anxiety_from_expectations(expectations)

    # Create contingency plans based on expectations
    contingency_plans = {}
    for exp in expectations:
        if exp.preparation_actions:
            contingency_plans[exp.predicted_event] = exp.preparation_actions

    # Create prospective state
    prospective_state = ProspectiveState(
        prospective_id=f"prospect_{entity.entity_id}_{timepoint.timepoint_id}_{uuid.uuid4().hex[:8]}",
        entity_id=entity.entity_id,
        timepoint_id=timepoint.timepoint_id,
        forecast_horizon_days=forecast_horizon,
        expectations=[exp.model_dump(mode='json') for exp in expectations],  # Store as dict for JSON
        contingency_plans=contingency_plans,
        anxiety_level=anxiety_level,
        forecast_confidence=getattr(entity, 'forecast_confidence', 1.0)
    )

    return prospective_state


def influence_behavior_from_expectations(
    entity: Entity,
    prospective_state: ProspectiveState
) -> Entity:
    """Modify entity behavior based on prospective expectations"""
    # Make a copy to avoid modifying the original
    modified_entity = entity.copy() if hasattr(entity, 'copy') else entity

    anxiety_level = prospective_state.anxiety_level
    expectations = prospective_state.expectations

    # Parse expectations if they're stored as JSON strings
    if isinstance(expectations, str):
        import json
        expectations = json.loads(expectations)

    # Convert dict expectations back to objects for processing
    expectation_objects = [Expectation(**exp) if isinstance(exp, dict) else exp for exp in expectations]

    # Get config values
    config = {}  # Would load from config
    conservatism_multiplier = config.get('anxiety_conservatism_multiplier', 0.7)
    preparation_energy_cost = config.get('preparation_energy_cost', 5)
    anxiety_energy_penalty = config.get('anxiety_energy_penalty', 0.2)

    # Make a deep copy of entity_metadata to avoid modifying the original
    modified_metadata = modified_entity.entity_metadata.copy()

    # High anxiety makes entity more conservative
    if anxiety_level > 0.8:  # High anxiety threshold
        if "behavior_tensor" in modified_metadata:
            modified_metadata["behavior_tensor"]["risk_tolerance"] = (
                modified_metadata["behavior_tensor"].get("risk_tolerance", 0.8) * conservatism_multiplier
            )
            modified_metadata["cognitive_tensor"]["information_seeking"] = (
                modified_metadata["cognitive_tensor"].get("information_seeking", 0.5) + 0.2
            )

    # Preparation actions consume energy
    total_prep_energy = 0
    for exp in expectation_objects:
        for action in exp.preparation_actions:
            total_prep_energy += estimate_energy_cost_for_preparation(action)

    # Reduce energy budget based on preparation load and anxiety
    if "cognitive_tensor" in modified_metadata:
        current_energy = modified_metadata["cognitive_tensor"].get("energy_budget", 100.0)

        # Energy cost from preparation
        prep_cost = min(
            total_prep_energy * preparation_energy_cost,
            current_energy * 0.5  # Max 50% reduction from preparation
        )

        # Additional anxiety energy cost
        anxiety_cost = anxiety_level * anxiety_energy_penalty

        # Apply costs
        new_energy = current_energy - prep_cost - anxiety_cost

        # Ensure energy doesn't go negative
        modified_metadata["cognitive_tensor"]["energy_budget"] = max(0, new_energy)

    # Update the entity's metadata
    modified_entity.entity_metadata = modified_metadata

    return modified_entity


def update_forecast_accuracy(
    entity: Entity,
    expectation: Expectation,
    actual_outcome: bool
) -> Entity:
    """Update entity's forecasting ability based on prediction accuracy"""
    # Make a copy to avoid modifying the original
    modified_entity = entity.copy() if hasattr(entity, 'copy') else entity

    # Calculate prediction error
    predicted_prob = expectation.subjective_probability
    actual_prob = 1.0 if actual_outcome else 0.0
    prediction_error = abs(predicted_prob - actual_prob)

    # Get config
    config = {}  # Would load from config
    confidence_decay = config.get('confidence_decay', 0.1)
    overconfidence_penalty = config.get('overconfidence_penalty', 0.2)

    # Make a deep copy of entity_metadata
    modified_metadata = modified_entity.entity_metadata.copy()

    # Update forecast confidence based on error
    current_confidence = modified_metadata.get('forecast_confidence', 1.0)
    # Larger errors reduce confidence more
    confidence_reduction = prediction_error * confidence_decay

    # Extra penalty for overconfidence in wrong predictions
    if predicted_prob > 0.7 and not actual_outcome:
        confidence_reduction += overconfidence_penalty

    new_confidence = current_confidence * (1.0 - confidence_reduction)
    modified_metadata['forecast_confidence'] = max(0.1, new_confidence)  # Minimum confidence

    # Update anxiety based on outcome
    if "cognitive_tensor" in modified_metadata:
        current_valence = modified_metadata["cognitive_tensor"].get("emotional_valence", 0.0)

        if actual_outcome and expectation.desired_outcome:
            # Positive outcome for desired event - reduce anxiety/improve mood
            modified_metadata["cognitive_tensor"]["emotional_valence"] = min(1.0, current_valence + 0.1)
        elif not actual_outcome and not expectation.desired_outcome:
            # Avoided undesired outcome - reduce anxiety/improve mood slightly
            modified_metadata["cognitive_tensor"]["emotional_valence"] = min(1.0, current_valence + 0.05)
        elif actual_outcome and not expectation.desired_outcome:
            # Undesired outcome occurred - increase anxiety/reduce mood
            modified_metadata["cognitive_tensor"]["emotional_valence"] = max(-1.0, current_valence - 0.1)
        elif not actual_outcome and expectation.desired_outcome:
            # Desired outcome failed - increase anxiety/reduce mood significantly
            modified_metadata["cognitive_tensor"]["emotional_valence"] = max(-1.0, current_valence - 0.2)

    # Update the entity's metadata
    modified_entity.entity_metadata = modified_metadata

    return modified_entity


def get_relevant_history_for_prospection(entity: Entity, timepoint: 'Timepoint',
                                         n_events: int = 5) -> List[Dict]:
    """Get relevant historical events for prospection context"""
    # This would query the store for relevant past events
    # For now, return a placeholder
    return [
        {"event": "Previous similar situation", "outcome": "successful", "lessons": ["be prepared"]},
        {"event": "Recent challenge", "outcome": "managed", "lessons": ["adapt quickly"]}
    ]
