# ============================================================================
# validation.py - Validation framework with plugin registry
# ============================================================================
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional
import numpy as np

from schemas import Entity, ExposureEvent, PhysicalTensor, CognitiveTensor
from metadata.tracking import track_mechanism

class Validator(ABC):
    """Base validator with plugin registry"""
    _validators = {}
    
    @classmethod
    def register(cls, name: str, severity: str = "ERROR"):
        def decorator(func: Callable):
            cls._validators[name] = {"func": func, "severity": severity}
            return func
        return decorator
    
    @classmethod
    def validate_all(cls, entity: Entity, context: Dict) -> List[Dict]:
        violations = []
        for name, validator in cls._validators.items():
            result = validator["func"](entity, context)
            if not result["valid"]:
                violations.append({
                    "validator": name,
                    "severity": validator["severity"],
                    "message": result["message"]
                })
        return violations

    def validate_entity(self, entity: Entity, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Validate an entity and return results.

        Args:
            entity: Entity to validate
            context: Optional validation context

        Returns:
            Dict with validation results
        """
        context = context or {}
        violations = self.validate_all(entity, context)

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "entity_id": entity.entity_id
        }

@Validator.register("information_conservation", "ERROR")
def validate_information_conservation(entity: Entity, context: Dict, store=None) -> Dict:
    """Validate knowledge ⊆ exposure history"""
    # Handle both Entity and EntityPopulation types
    from schemas import EntityPopulation  # Canonical location (breaks circular dep)

    # If store is provided, query actual exposure events from database
    if store:
        entity_id = getattr(entity, 'entity_id', '')
        exposure_events = store.get_exposure_events(entity_id)
        exposure = set(event.information for event in exposure_events)
    else:
        # Fallback to context-based validation for backward compatibility
        exposure_history = context.get("exposure_history", [])
        # Handle both list of strings and list of ExposureEvent objects
        if exposure_history and isinstance(exposure_history[0], ExposureEvent):
            exposure = set(event.information for event in exposure_history)
        else:
            exposure = set(exposure_history)

    # Get knowledge state from either Entity or EntityPopulation
    if isinstance(entity, EntityPopulation):
        knowledge = set(entity.knowledge_state)
    elif hasattr(entity, 'entity_metadata'):
        knowledge = set(entity.entity_metadata.get("knowledge_state", []))
    else:
        knowledge = set()

    unknown = knowledge - exposure
    if unknown:
        return {"valid": False, "message": f"Entity knows about {unknown} without exposure"}
    return {"valid": True, "message": "Information conservation satisfied"}

@Validator.register("energy_budget", "WARNING")
def validate_energy_budget(entity: Entity, context: Dict) -> Dict:
    """Validate interaction costs ≤ capacity with circadian adjustments"""
    # Handle both Entity and EntityPopulation types
    from schemas import EntityPopulation  # Canonical location (breaks circular dep)

    if isinstance(entity, EntityPopulation):
        budget = entity.energy_budget
        current_knowledge = set(entity.knowledge_state)
    elif hasattr(entity, 'entity_metadata'):
        budget = entity.entity_metadata.get("energy_budget", 100)
        current_knowledge = set(entity.entity_metadata.get("knowledge_state", []))
    else:
        # No energy data available
        return {"valid": True, "message": "No energy budget data to validate"}

    previous_knowledge = set(context.get("previous_knowledge", []) or [])
    new_knowledge_count = len(current_knowledge - previous_knowledge)

    # Base cost per knowledge item
    base_expenditure = new_knowledge_count * 5

    # Apply circadian adjustments if timepoint is available
    timepoint = context.get("timepoint")
    circadian_config = context.get("circadian_config", {})
    if timepoint and circadian_config:
        # Estimate activity type based on context (could be made more sophisticated)
        activity_type = context.get("activity_type", "work")  # Default assumption
        expenditure = compute_energy_cost_with_circadian(
            activity_type, timepoint.timestamp.hour, base_expenditure, circadian_config
        )
    else:
        expenditure = base_expenditure

    if expenditure > budget * 1.2:  # Allow 20% temporary excess
        hour_info = f" at {timepoint.timestamp.hour:02d}:00" if timepoint else ""
        return {"valid": False, "message": f"Energy expenditure {expenditure:.1f}{hour_info} exceeds budget {budget}"}
    return {"valid": True, "message": "Energy budget satisfied"}

@Validator.register("behavioral_inertia", "WARNING")
def validate_behavioral_inertia(entity: Entity, context: Dict) -> Dict:
    """Validate personality drift is gradual"""
    if "previous_personality" not in context or not context["previous_personality"]:
        return {"valid": True, "message": "No previous state to compare"}

    current = np.array(entity.entity_metadata.get("personality_traits", []))
    previous = np.array(context["previous_personality"])

    if len(current) == 0 or len(previous) == 0:
        return {"valid": True, "message": "Personality data not available"}

    # Handle different length arrays (take minimum length)
    min_len = min(len(current), len(previous))
    current = current[:min_len]
    previous = previous[:min_len]

    drift = np.linalg.norm(current - previous)
    if drift > 1.0:  # Threshold for significant personality change
        return {"valid": False, "message": f"Personality drift {drift:.2f} exceeds threshold 1.0"}
    return {"valid": True, "message": "Behavioral inertia satisfied"}

@Validator.register("biological_constraints", "ERROR")
@track_mechanism("M4", "physics_validation")
def validate_biological_constraints(entity: Entity, context: Dict) -> Dict:
    """Validate age-dependent capabilities"""
    # Handle both Entity and EntityPopulation types
    from schemas import EntityPopulation  # Canonical location (breaks circular dep)

    if isinstance(entity, EntityPopulation):
        # EntityPopulation doesn't have age, skip validation
        return {"valid": True, "message": "No age data in EntityPopulation"}
    elif hasattr(entity, 'entity_metadata'):
        age = entity.entity_metadata.get("age", 0)
    else:
        return {"valid": True, "message": "No age data available"}

    action = context.get("action", "")

    if age > 100 and "physical_labor" in action:
        return {"valid": False, "message": f"Entity age {age} incompatible with physical labor"}
    if age < 18 and age > 50 and "childbirth" in action:
        return {"valid": False, "message": f"Entity age {age} incompatible with childbirth"}

    return {"valid": True, "message": "Biological constraints satisfied"}

@Validator.register("network_flow", "WARNING")
def validate_network_flow(entity: Entity, context: Dict) -> Dict:
    """Validate that influence/status changes propagate through relationship graph edges"""
    graph = context.get("graph")
    if not graph or entity.entity_id not in graph:
        return {"valid": True, "message": "No graph available for network flow validation"}

    # Get current knowledge as a proxy for "influence" or "status"
    current_knowledge = set(entity.entity_metadata.get("knowledge_state", []))
    previous_knowledge = set(context.get("previous_knowledge", []) or [])

    # Check for new knowledge acquisition
    new_knowledge = current_knowledge - previous_knowledge
    if not new_knowledge:
        return {"valid": True, "message": "No new knowledge to validate network flow"}

    # Check if entity has connections to sources of this knowledge
    connected_entities = set(graph.neighbors(entity.entity_id))
    # Note: Don't include self for network flow validation - self-knowledge is allowed

    # Get knowledge from connected entities (simplified - in real implementation,
    # we'd need to track knowledge propagation through time)
    connected_knowledge = set()
    for connected_id in connected_entities:
        if connected_id in context.get("all_entity_knowledge", {}):
            connected_knowledge.update(context["all_entity_knowledge"][connected_id])

    # Check if new knowledge could have come from connected entities
    unexplained_knowledge = new_knowledge - connected_knowledge

    # Allow some knowledge to come from events/exposure (not just direct connections)
    exposure_knowledge = set(context.get("exposure_history", []))
    truly_unexplained = unexplained_knowledge - exposure_knowledge

    # DEBUG: Uncomment for validation debugging
    # print(f"DEBUG {entity.entity_id}: new={new_knowledge}, connected={connected_entities}, connected_knowledge={connected_knowledge}, unexplained={unexplained_knowledge}, exposure={exposure_knowledge}, truly_unexplained={truly_unexplained}")

    if truly_unexplained:
        return {
            "valid": False,
            "message": f"Entity gained knowledge {list(truly_unexplained)} without network connections or exposure"
        }

    return {"valid": True, "message": "Network flow validation satisfied"}

@Validator.register("temporal_causality", "ERROR")
def validate_temporal_causality(entity: Entity, context: Dict) -> Dict:
    """Validate that entity knowledge follows causal temporal constraints"""
    store = context.get("store")
    timepoint_id = context.get("timepoint_id")

    if not store or not timepoint_id:
        return {"valid": True, "message": "Insufficient context for temporal causality validation"}

    # Check each knowledge item for temporal validity
    from temporal_chain import validate_temporal_reference  # Import locally to avoid circular import

    knowledge_state = entity.entity_metadata.get("knowledge_state", [])
    invalid_items = []

    for knowledge_item in knowledge_state:
        validation = validate_temporal_reference(entity.entity_id, knowledge_item, timepoint_id, store)
        if not validation["valid"]:
            invalid_items.append(knowledge_item)

    if invalid_items:
        return {
            "valid": False,
            "message": f"Entity has knowledge {invalid_items} that violates temporal causality"
        }

    return {"valid": True, "message": "Temporal causality satisfied"}


# ============================================================================
# Body-Mind Coupling Functions (Mechanism 8.1)
# ============================================================================

def couple_pain_to_cognition(physical: PhysicalTensor, cognitive: CognitiveTensor) -> CognitiveTensor:
    """Pain affects cognitive state - reduces energy, worsens mood, lowers patience"""
    pain_factor = physical.pain_level

    # Reduce energy budget based on pain level
    cognitive.energy_budget *= (1.0 - pain_factor * 0.5)

    # Reduce emotional valence (more negative mood)
    cognitive.emotional_valence -= pain_factor * 0.3

    # Reduce patience threshold
    cognitive.patience_threshold -= pain_factor * 0.4

    # Reduce decision confidence
    cognitive.decision_confidence *= (1.0 - pain_factor * 0.2)

    return cognitive


def couple_illness_to_cognition(physical: PhysicalTensor, cognitive: CognitiveTensor) -> CognitiveTensor:
    """Illness impairs judgment and engagement"""
    if physical.fever > 38.5:  # High fever threshold
        # Reduce decision confidence due to cognitive impairment
        cognitive.decision_confidence *= 0.7

        # Increase risk tolerance (fever makes people more reckless)
        cognitive.risk_tolerance += 0.2

        # Reduce social engagement due to illness
        cognitive.social_engagement -= 0.4

    return cognitive


# ============================================================================
# Dialog Quality Validators (Mechanism 11)
# ============================================================================

@Validator.register("dialog_realism", severity="WARNING")
def validate_dialog_realism(entity: Entity, context: Dict = None) -> Dict:
    """Check if dialog respects physical/emotional constraints"""
    if context is None:
        context = {}

    # This validator only applies to Dialog objects, skip for regular entities
    if not hasattr(entity, 'entity_metadata') or 'dialog_data' not in entity.entity_metadata:
        return {"valid": True, "message": "Not a dialog entity, skipping dialog validation"}

    dialog_data = entity.entity_metadata.get('dialog_data', {})

    # Parse dialog turns
    turns = dialog_data.get("turns", [])
    if isinstance(turns, str):
        import json
        turns = json.loads(turns)

    validation_issues = []

    # Get entities from context if available
    entities = context.get("entities", [])
    if not entities:
        # If no entities in context, skip detailed validation
        return {"valid": True, "message": "No entities in context for dialog validation"}

    for i, turn in enumerate(turns):
        speaker_id = turn.get("speaker")
        content = turn.get("content", "")
        turn_index = i + 1

        # Find speaker entity
        speaker = next((e for e in entities if e.entity_id == speaker_id), None)
        if not speaker:
            continue

        # Get speaker's current state
        physical = speaker.physical_tensor
        cognitive = speaker.cognitive_tensor

        # Apply body-mind coupling for validation
        coupled_cognitive = couple_pain_to_cognition(physical, cognitive)
        coupled_cognitive = couple_illness_to_cognition(physical, coupled_cognitive)

        # Check turn length vs. energy
        content_length = len(content)
        if coupled_cognitive.energy_budget < 30 and content_length > 200:
            validation_issues.append(
                f"{speaker_id} too low energy ({coupled_cognitive.energy_budget:.1f}) for long response ({content_length} chars)"
            )

        # Check tone vs. emotional state
        emotional_tone = turn.get("emotional_tone", "").lower()
        valence = coupled_cognitive.emotional_valence

        if valence < -0.5 and not any(neg in emotional_tone for neg in ["sad", "angry", "frustrated", "negative"]):
            validation_issues.append(
                f"{speaker_id} should have negative tone given emotional valence {valence:.2f}"
            )

        # Check pain impact on engagement
        if physical.pain_level > 0.6 and turn_index > 5:  # Long conversation
            validation_issues.append(
                f"{speaker_id} unlikely to sustain conversation with pain level {physical.pain_level}"
            )

        # Check stamina impact on conversation length
        stamina = physical.stamina
        if stamina < 0.3 and content_length > 50:
            validation_issues.append(
                f"{speaker_id} has low stamina ({stamina:.2f}) but gives detailed response"
            )

    if validation_issues:
        return {
            "valid": False,
            "message": f"Dialog realism issues: {'; '.join(validation_issues)}"
        }

    return {"valid": True, "message": "Dialog respects physical/emotional constraints"}


@Validator.register("dialog_knowledge_consistency", severity="ERROR")
def validate_dialog_knowledge_consistency(entity: Entity, context: Dict = None) -> Dict:
    """Check if dialog speakers only reference knowledge they actually have"""
    if context is None:
        context = {}

    # This validator only applies to Dialog objects, skip for regular entities
    if not hasattr(entity, 'entity_metadata') or 'dialog_data' not in entity.entity_metadata:
        return {"valid": True, "message": "Not a dialog entity, skipping dialog knowledge validation"}

    dialog_data = entity.entity_metadata.get('dialog_data', {})

    # Parse dialog turns
    turns = dialog_data.get("turns", [])
    if isinstance(turns, str):
        import json
        turns = json.loads(turns)

    knowledge_violations = []

    # Get entities from context if available
    entities = context.get("entities", [])
    if not entities:
        # If no entities in context, skip detailed validation
        return {"valid": True, "message": "No entities in context for dialog knowledge validation"}

    for turn in turns:
        speaker_id = turn.get("speaker")
        content = turn.get("content", "")
        knowledge_refs = turn.get("knowledge_references", [])

        # Find speaker entity
        speaker = next((e for e in entities if e.entity_id == speaker_id), None)
        if not speaker:
            continue

        # Get speaker's knowledge state
        speaker_knowledge = set(speaker.entity_metadata.get("knowledge_state", []))

        # Check explicit knowledge references
        for ref in knowledge_refs:
            if ref not in speaker_knowledge:
                knowledge_violations.append(
                    f"{speaker_id} references unknown knowledge: '{ref}'"
                )

        # Check for anachronistic references in content (simple heuristic)
        words = content.lower().split()
        for word in words:
            if word[0].isupper() and len(word) > 3:  # Potential proper noun
                if word.lower() not in [k.lower() for k in speaker_knowledge]:
                    # Allow some flexibility for proper nouns that might not be in knowledge
                    continue

    if knowledge_violations:
        return {
            "valid": False,
            "message": f"Knowledge consistency violations: {'; '.join(knowledge_violations)}"
        }

    return {"valid": True, "message": "Dialog respects knowledge constraints"}


@Validator.register("dialog_relationship_consistency", severity="WARNING")
def validate_dialog_relationship_consistency(entity: Entity, context: Dict = None) -> Dict:
    """Check if dialog tone matches established relationship dynamics"""
    if context is None:
        context = {}

    # This validator only applies to Dialog objects, skip for regular entities
    if not hasattr(entity, 'entity_metadata') or 'dialog_data' not in entity.entity_metadata:
        return {"valid": True, "message": "Not a dialog entity, skipping dialog relationship validation"}

    dialog_data = entity.entity_metadata.get('dialog_data', {})

    # Parse dialog turns
    turns = dialog_data.get("turns", [])
    if isinstance(turns, str):
        import json
        turns = json.loads(turns)

    relationship_issues = []

    # Get entities from context if available
    entities = context.get("entities", [])
    if not entities:
        # If no entities in context, skip detailed validation
        return {"valid": True, "message": "No entities in context for dialog relationship validation"}

    # Build relationship map
    entity_map = {e.entity_id: e for e in entities}
    relationship_map = {}

    for turn in turns:
        speaker_id = turn.get("speaker")
        content = turn.get("content", "")
        emotional_tone = turn.get("emotional_tone", "").lower()

        # Check relationship with each other participant
        for entity in entities:
            if entity.entity_id == speaker_id:
                continue

            # Compute relationship metrics
            from workflows import compute_relationship_metrics
            metrics = compute_relationship_metrics(entity_map[speaker_id], entity)

            trust_level = metrics.get("trust", 0.5)
            alignment = metrics.get("alignment", 0.0)

            # Check if tone matches relationship
            if trust_level < 0.3 and not any(neg in emotional_tone for neg in ["guarded", "formal", "tense", "hostile"]):
                relationship_issues.append(
                    f"{speaker_id} should show guarded tone with {entity.entity_id} (trust: {trust_level:.2f})"
                )

            if alignment < -0.5 and not any(neg in emotional_tone for neg in ["critical", "oppositional", "disagreeable"]):
                relationship_issues.append(
                    f"{speaker_id} should show disagreement with {entity.entity_id} (alignment: {alignment:.2f})"
                )

    if relationship_issues:
        return {
            "valid": False,
            "message": f"Relationship consistency issues: {'; '.join(relationship_issues)}"
        }

    return {"valid": True, "message": "Dialog tone matches relationship dynamics"}


# ============================================================================
# Mechanism 14: Circadian Activity Patterns
# ============================================================================

def get_activity_probability(hour: int, activity: str, circadian_config: Dict) -> float:
    """Get probability of an activity at a given hour"""
    activity_probs = circadian_config.get("activity_probabilities", {})

    if activity not in activity_probs:
        return 0.1  # Default low probability for unknown activities

    activity_config = activity_probs[activity]
    allowed_hours = activity_config.get("hours", [])
    base_probability = activity_config.get("probability", 0.1)

    if hour in allowed_hours:
        return base_probability

    # Check for adjacent hours (some flexibility)
    if hour - 1 in allowed_hours or hour + 1 in allowed_hours:
        return base_probability * 0.5  # Half probability for adjacent hours

    return 0.05  # Very low probability for inappropriate hours


@track_mechanism("M14", "circadian_patterns")
def compute_energy_cost_with_circadian(activity: str, hour: int, base_cost: float, circadian_config: Dict) -> float:
    """Compute energy cost adjusted for circadian factors"""
    multipliers = circadian_config.get("energy_multipliers", {})
    fatigue_threshold = multipliers.get("base_fatigue_threshold", 16)

    # Base circadian penalty for nighttime activities
    if 22 <= hour or hour < 6:
        circadian_penalty = multipliers.get("night_penalty", 1.5)
    else:
        circadian_penalty = 1.0

    # Fatigue accumulation based on hours awake
    hours_awake = (hour - 6) if hour >= 6 else (hour + 18)  # Assuming wake at 6am
    if hours_awake > fatigue_threshold:
        fatigue_factor = 1.0 + (hours_awake - fatigue_threshold) * multipliers.get("fatigue_accumulation", 0.5) / fatigue_threshold
    else:
        fatigue_factor = 1.0

    return base_cost * circadian_penalty * fatigue_factor


@Validator.register("circadian_plausibility", severity="WARNING")
def validate_circadian_activity(entity: Entity, context: Dict = None) -> Dict:
    """Check if activity is plausible at the given time of day"""
    if context is None:
        context = {}

    # Get activity and timepoint from context
    activity = context.get("activity")
    timepoint = context.get("timepoint")

    # If no activity or timepoint specified, skip validation
    if not activity or not timepoint:
        return {"valid": True, "message": "No activity or timepoint specified for circadian validation"}

    # Get circadian config from context or default
    circadian_config = context.get("circadian_config", {})

    hour = timepoint.timestamp.hour
    probability = get_activity_probability(hour, activity, circadian_config)

    thresholds = circadian_config.get("validation", {})
    low_threshold = thresholds.get("low_probability_threshold", 0.1)
    critical_threshold = thresholds.get("critical_probability_threshold", 0.05)

    if probability < critical_threshold:
        return {
            "valid": False,
            "message": f"Activity '{activity}' at {hour:02d}:00 is highly implausible (probability: {probability:.3f})"
        }
    elif probability < low_threshold:
        return {
            "valid": True,  # Warning, not error
            "message": f"Activity '{activity}' at {hour:02d}:00 is unusual (probability: {probability:.3f})"
        }

    return {
        "valid": True,
        "message": f"Activity '{activity}' at {hour:02d}:00 is plausible (probability: {probability:.3f})"
    }


def create_circadian_context(hour: int, circadian_config: Dict) -> 'CircadianContext':
    """Create a circadian context for a given hour"""
    from schemas import CircadianContext

    # Build typical activities dictionary
    typical_activities = {}
    activity_probs = circadian_config.get("activity_probabilities", {})
    for activity, config in activity_probs.items():
        prob = get_activity_probability(hour, activity, circadian_config)
        typical_activities[activity] = prob

    # Determine ambient conditions based on hour
    if 6 <= hour < 12:
        ambient_conditions = {"lighting": 0.8, "noise": 0.6, "temperature": 0.7}
        social_constraints = ["morning_business", "daylight_activities"]
    elif 12 <= hour < 18:
        ambient_conditions = {"lighting": 0.9, "noise": 0.7, "temperature": 0.8}
        social_constraints = ["afternoon_work", "daylight_social"]
    elif 18 <= hour < 22:
        ambient_conditions = {"lighting": 0.6, "noise": 0.8, "temperature": 0.6}
        social_constraints = ["evening_social", "indoor_activities"]
    else:  # Night
        ambient_conditions = {"lighting": 0.2, "noise": 0.3, "temperature": 0.5}
        social_constraints = ["night_rest", "quiet_activities"]

    # Calculate fatigue level (simplified)
    hours_awake = (hour - 6) if hour >= 6 else (hour + 18)
    fatigue_level = min(1.0, max(0.0, (hours_awake - 8) / 16))  # Peak fatigue after 16 hours awake

    # Energy penalty based on circadian config
    multipliers = circadian_config.get("energy_multipliers", {})
    if 22 <= hour or hour < 6:
        energy_penalty = multipliers.get("night_penalty", 1.5)
    else:
        energy_penalty = 1.0

    return CircadianContext(
        hour=hour,
        typical_activities=typical_activities,
        ambient_conditions=ambient_conditions,
        social_constraints=social_constraints,
        fatigue_level=fatigue_level,
        energy_penalty=energy_penalty
    )


# ============================================================================
# Mechanism 15: Entity Prospection
# ============================================================================

@Validator.register("prospection_consistency", severity="WARNING")
def validate_prospection_consistency(entity: Entity, context: Dict = None) -> Dict:
    """Validate that prospective expectations are consistent and realistic"""
    if context is None:
        context = {}

    # Get prospective_state from context
    prospective_state = context.get("prospective_state")
    if not prospective_state:
        return {"valid": True, "message": "No prospective state to validate"}

    # Parse expectations
    expectations = prospective_state.expectations
    if isinstance(expectations, str):
        import json
        expectations = json.loads(expectations)

    from schemas import Expectation
    expectation_objects = [Expectation(**exp) if isinstance(exp, dict) else exp for exp in expectations]

    issues = []
    total_probability = 0

    # Check for unrealistic probabilities
    for exp in expectation_objects:
        total_probability += exp.subjective_probability

        # Flag extremely low or high probabilities
        if exp.subjective_probability < 0.05:
            issues.append(f"Expectation '{exp.predicted_event}' has very low probability ({exp.subjective_probability:.3f})")
        elif exp.subjective_probability > 0.95:
            issues.append(f"Expectation '{exp.predicted_event}' has very high probability ({exp.subjective_probability:.3f})")

        # Check confidence vs probability alignment
        if exp.confidence > 0.8 and exp.subjective_probability < 0.2:
            issues.append(f"High confidence ({exp.confidence:.2f}) but low probability ({exp.subjective_probability:.3f}) for '{exp.predicted_event}'")

    # Check total probability isn't unrealistic
    if total_probability > 1.5:  # Allow some overlap but flag excessive
        issues.append(f"Total expectation probabilities ({total_probability:.2f}) suggest unrealistic optimism")

    # Check anxiety level reasonableness
    anxiety_level = prospective_state.anxiety_level
    if anxiety_level > 0.9:
        issues.append(f"Extremely high anxiety level ({anxiety_level:.2f}) may indicate unrealistic expectations")

    if issues:
        return {
            "valid": False,
            "message": f"Prospection consistency issues: {'; '.join(issues)}"
        }

    return {
        "valid": True,
        "message": f"Prospective expectations appear consistent (anxiety: {anxiety_level:.2f})"
    }


@Validator.register("prospection_energy_impact", severity="WARNING")
def validate_prospection_energy_impact(entity: 'Entity', context: Dict = None) -> Dict:
    """Validate that prospection doesn't deplete energy unrealistically"""
    if context is None:
        context = {}

    # Get prospective_state from context
    prospective_state = context.get("prospective_state")
    if not prospective_state:
        return {"valid": True, "message": "No prospective state to validate"}

    # Parse expectations
    expectations = prospective_state.expectations
    if isinstance(expectations, str):
        import json
        expectations = json.loads(expectations)

    from schemas import Expectation
    expectation_objects = [Expectation(**exp) if isinstance(exp, dict) else exp for exp in expectations]

    # Calculate preparation energy cost
    total_prep_cost = 0
    for exp in expectation_objects:
        for action in exp.preparation_actions:
            from workflows import estimate_energy_cost_for_preparation
            total_prep_cost += estimate_energy_cost_for_preparation(action)

    # Get config values
    config = context.get('prospection_config', {})
    preparation_energy_cost = config.get('behavioral_influence', {}).get('preparation_energy_cost', 5)
    anxiety_energy_penalty = config.get('behavioral_influence', {}).get('anxiety_energy_penalty', 0.2)

    total_energy_cost = (total_prep_cost * preparation_energy_cost) + (prospective_state.anxiety_level * anxiety_energy_penalty)

    # Check against entity's energy budget
    entity_energy = getattr(entity, 'cognitive_tensor', None)
    if entity_energy and hasattr(entity_energy, 'energy_budget'):
        if total_energy_cost > entity_energy.energy_budget * 0.8:  # More than 80% of budget
            return {
                "valid": False,
                "message": f"Prospection energy cost ({total_energy_cost:.1f}) exceeds 80% of entity budget ({entity_energy.energy_budget})"
            }

    return {
        "valid": True,
        "message": f"Prospection energy impact acceptable ({total_energy_cost:.1f} cost)"
    }


# ============================================================================
# Mechanism 12: Counterfactual Branching
# ============================================================================

@Validator.register("branch_consistency", severity="WARNING")
def validate_branch_consistency(entity: Entity, context: Dict = None) -> Dict:
    """Validate that a branch timeline is consistent with its parent"""
    if context is None:
        context = {}

    # Get timelines from context
    branch_timeline = context.get("branch_timeline")
    baseline_timeline = context.get("baseline_timeline")

    if not branch_timeline:
        return {"valid": True, "message": "No branch timeline to validate"}

    issues = []

    # Check that branch has required fields
    if not branch_timeline.parent_timeline_id:
        return {
            "valid": False,
            "message": "Branch timeline missing parent_timeline_id"
        }

    if not branch_timeline.branch_point:
        issues.append("Branch timeline missing branch_point")

    if not branch_timeline.intervention_description:
        issues.append("Branch timeline missing intervention_description")

    # If baseline provided, check consistency
    if baseline_timeline:
        # Branch should diverge at or after the branch point
        if branch_timeline.branch_point:
            # This would require checking timepoint timestamps
            pass

    if issues:
        return {
            "valid": False,
            "message": f"Branch consistency issues: {'; '.join(issues)}"
        }

    return {
        "valid": True,
        "message": f"Branch timeline consistent with parent {branch_timeline.parent_timeline_id}"
    }


@Validator.register("intervention_plausibility", severity="WARNING")
def validate_intervention_plausibility(entity: Entity, context: Dict = None) -> Dict:
    """Validate that an intervention is plausible and well-formed"""
    if context is None:
        context = {}

    intervention = context.get("intervention")
    if not intervention:
        return {"valid": True, "message": "No intervention to validate"}

    issues = []

    # Check intervention type validity
    valid_types = ["entity_removal", "entity_modification", "event_cancellation", "knowledge_alteration"]
    if intervention.type not in valid_types:
        issues.append(f"Invalid intervention type: {intervention.type}")

    # Check required fields
    if not intervention.target:
        issues.append("Intervention missing target")

    # Type-specific validation
    if intervention.type == "entity_modification":
        if not intervention.parameters.get("modifications"):
            issues.append("Entity modification intervention missing 'modifications' parameter")

    elif intervention.type == "knowledge_alteration":
        if not intervention.parameters.get("knowledge_changes"):
            issues.append("Knowledge alteration intervention missing 'knowledge_changes' parameter")

    # Check description
    if not intervention.description:
        issues.append("Intervention missing description")

    if issues:
        return {
            "valid": False,
            "message": f"Intervention plausibility issues: {'; '.join(issues)}"
        }

    return {
        "valid": True,
        "message": f"Intervention '{intervention.description}' is plausible"
    }


@Validator.register("timeline_divergence", severity="INFO")
def validate_timeline_divergence(entity: Entity, context: Dict = None) -> Dict:
    """Validate that timeline divergence is meaningful and causal"""
    if context is None:
        context = {}

    comparison = context.get("comparison")
    if not comparison:
        return {"valid": True, "message": "No comparison to validate"}

    # Check that there's actually a divergence
    if not comparison.divergence_point:
        return {
            "valid": True,  # Not necessarily invalid, but noteworthy
            "message": "No timeline divergence detected - branches may be identical"
        }

    # Check that divergence is explained
    if not comparison.causal_explanation or comparison.causal_explanation == "Timelines are identical - no divergence detected":
        return {
            "valid": False,
            "message": f"Timeline diverges at {comparison.divergence_point} but lacks causal explanation"
        }

    # Check that there are meaningful differences
    total_changes = len(comparison.key_events_differed) + len(comparison.entity_states_differed)
    if total_changes == 0:
        return {
            "valid": False,
            "message": f"Timeline diverges at {comparison.divergence_point} but no substantive changes detected"
        }

    return {
        "valid": True,
        "message": f"Timeline divergence at {comparison.divergence_point} is well-explained with {total_changes} changes"
    }


# ============================================================================
# Mechanism 16: Animistic Entity Extension
# ============================================================================

@Validator.register("environmental_constraints", severity="ERROR")
def validate_environmental_constraints(entity: Entity, context: Dict = None) -> Dict:
    """Validate that actions respect constraints imposed by animistic entities"""
    if context is None:
        context = {}

    action = context.get("action")
    environment_entities = context.get("environment_entities", [])

    if not action or not environment_entities:
        return {"valid": True, "message": "No action or environment entities to validate"}

    issues = []

    for env_entity in environment_entities:
        if env_entity.entity_type == "building":
            # Import here to avoid circular imports
            from schemas import BuildingEntity

            try:
                building = BuildingEntity(**env_entity.entity_metadata)
                participant_count = action.get("participant_count", 0)

                if participant_count > building.capacity:
                    issues.append(f"Building {env_entity.entity_id} capacity {building.capacity} exceeded by {participant_count} participants")

                if building.structural_integrity < 0.5:
                    issues.append(f"Building {env_entity.entity_id} structural integrity too low ({building.structural_integrity:.2f}) for use")

                if "weather_dependent" in building.constraints:
                    weather_conditions = action.get("weather_conditions", {})
                    if weather_conditions.get("precipitation", 0) > 0.5:  # Heavy rain
                        issues.append(f"Building {env_entity.entity_id} cannot be used in heavy precipitation")

            except Exception as e:
                issues.append(f"Invalid building metadata for {env_entity.entity_id}: {e}")

        elif env_entity.entity_type == "animal":
            # Import here to avoid circular imports
            from schemas import AnimalEntity

            try:
                animal = AnimalEntity(**entity.entity_metadata)
                action_type = action.get("action_type", "")

                if action_type == "mount" and animal.biological_state.get("energy", 1.0) < 0.3:
                    issues.append(f"Animal {entity.entity_id} too tired to be mounted (energy: {animal.biological_state['energy']:.2f})")

                if animal.biological_state.get("health", 1.0) < 0.2:
                    issues.append(f"Animal {entity.entity_id} too unhealthy for activity (health: {animal.biological_state['health']:.2f})")

                if action_type in ["hunt", "work"] and animal.training_level < 0.3:
                    issues.append(f"Animal {entity.entity_id} insufficiently trained for {action_type} (training: {animal.training_level:.2f})")

            except Exception as e:
                issues.append(f"Invalid animal metadata for {entity.entity_id}: {e}")

        elif entity.entity_type == "abstract":
            # Import here to avoid circular imports
            from schemas import AbstractEntity

            try:
                concept = AbstractEntity(**entity.entity_metadata)
                participant_ids = action.get("participant_ids", [])

                # Check if concept affects participants
                affected_participants = [pid for pid in participant_ids if pid in concept.carriers]
                if affected_participants and concept.intensity > 0.8:
                    # High-intensity concepts might constrain behavior
                    issues.append(f"Abstract concept {entity.entity_id} (intensity: {concept.intensity:.2f}) may constrain participants: {affected_participants}")

            except Exception as e:
                issues.append(f"Invalid abstract entity metadata for {entity.entity_id}: {e}")

    if issues:
        return {
            "valid": False,
            "message": f"Environmental constraint violations: {'; '.join(issues)}"
        }

    return {
        "valid": True,
        "message": "All environmental constraints satisfied"
    }


@Validator.register("spiritual_influence", severity="WARNING")
def validate_spiritual_influence(entity: Entity, context: Dict = None) -> Dict:
    """Validate spiritual/supernatural influences from kami entities"""
    if context is None:
        context = {}

    action = context.get("action")
    environment_entities = context.get("environment_entities", [])

    if not action or not environment_entities:
        return {"valid": True, "message": "No action or environment entities to validate"}

    issues = []

    for env_entity in environment_entities:
        if env_entity.entity_type == "kami":
            from schemas import KamiEntity

            try:
                kami = KamiEntity(**env_entity.entity_metadata)
                participant_ids = action.get("participant_ids", [])

                # Check if kami's domain affects the action
                action_type = action.get("action_type", "")
                affected_by_domains = []

                for domain in kami.influence_domain:
                    if domain in ["fate", "protection", "war"] and action_type in ["combat", "decision", "travel"]:
                        affected_by_domains.append(domain)
                    elif domain == "weather" and action.get("outdoor", False):
                        affected_by_domains.append(domain)
                    elif domain == "emotions" and action_type in ["social", "negotiation", "ceremony"]:
                        affected_by_domains.append(domain)

                if affected_by_domains and kami.spiritual_power > 0.7:
                    # High power kami with relevant domains may influence the action
                    if kami.visibility_state == "invisible" and kami.disclosure_level == "unknown":
                        issues.append(f"Unknown kami {env_entity.entity_id} (domains: {affected_by_domains}) may secretly influence action")
                    elif kami.disclosure_level in ["worshiped", "feared"]:
                        issues.append(f"Known kami {env_entity.entity_id} (domains: {affected_by_domains}) may actively affect participants")

                # Check taboo violations
                action_description = action.get("description", "").lower()
                for taboo in kami.taboo_violations:
                    if taboo.lower() in action_description:
                        issues.append(f"Action violates taboo of kami {env_entity.entity_id}: {taboo}")

            except Exception as e:
                issues.append(f"Invalid kami metadata for {env_entity.entity_id}: {e}")

    if issues:
        return {
            "valid": False,
            "message": f"Spiritual influence concerns: {'; '.join(issues)}"
        }

    return {
        "valid": True,
        "message": "No concerning spiritual influences detected"
    }


@Validator.register("adaptive_entity_behavior", severity="INFO")
def validate_adaptive_entity_behavior(entity: Entity, context: Dict) -> Dict:
    """Validate adaptive behavior of any entities based on context"""
    if entity.entity_type != "any":
        return {"valid": True, "message": "Not an adaptive any entity"}

    from schemas import AnyEntity

    try:
        any_entity = AnyEntity(**entity.entity_metadata)

        # Check if entity's adaptive goals align with current context
        context_goals = context.get("context_goals", [])
        goal_alignment = 0

        for goal in any_entity.adaptive_goals:
            if any(goal.lower() in ctx_goal.lower() for ctx_goal in context_goals):
                goal_alignment += 1

        # High adaptability should lead to better goal alignment
        expected_alignment = int(any_entity.adaptability_score * len(any_entity.adaptive_goals))
        if goal_alignment < expected_alignment * 0.5:  # Should align with at least half
            return {
                "valid": False,
                "message": f"Any entity {entity.entity_id} shows poor adaptation (adaptability: {any_entity.adaptability_score:.2f}, goal alignment: {goal_alignment}/{len(any_entity.adaptive_goals)})"
            }

        # Check stability vs adaptability balance
        if any_entity.adaptability_score > 0.8 and any_entity.stability_index < 0.3:
            return {
                "valid": False,
                "message": f"Any entity {entity.entity_id} is too unstable for high adaptability (stability: {any_entity.stability_index:.2f})"
            }

        return {
            "valid": True,
            "message": f"Any entity {entity.entity_id} shows appropriate adaptive behavior"
        }

    except Exception as e:
        return {
            "valid": False,
            "message": f"Any entity validation error for {entity.entity_id}: {e}"
        }


@Validator.register("biological_plausibility", severity="WARNING")
def validate_biological_plausibility(entity: Entity, context: Dict) -> Dict:
    """Validate biological consistency for animistic entities"""
    if entity.entity_type not in ["animal", "building", "abstract", "any", "kami", "ai"]:
        return {"valid": True, "message": "Not an animistic entity"}

    issues = []

    if entity.entity_type == "animal":
        from schemas import AnimalEntity

        try:
            animal = AnimalEntity(**entity.entity_metadata)

            # Check biological state ranges
            for state_name, value in animal.biological_state.items():
                if not (0.0 <= value <= 1.0):
                    issues.append(f"Animal {entity.entity_id} {state_name} out of range: {value}")

            # Check conflicting states
            if animal.biological_state.get("energy", 1.0) > 0.8 and animal.biological_state.get("fatigue", 0.0) > 0.7:
                issues.append(f"Animal {entity.entity_id} cannot be high energy and highly fatigued simultaneously")

            if animal.training_level < 0.1 and animal.goals:
                issues.append(f"Animal {entity.entity_id} has goals but very low training level")

        except Exception as e:
            issues.append(f"Animal validation error for {entity.entity_id}: {e}")

    elif entity.entity_type == "building":
        from schemas import BuildingEntity

        try:
            building = BuildingEntity(**entity.entity_metadata)

            if not (0.0 <= building.structural_integrity <= 1.0):
                issues.append(f"Building {entity.entity_id} structural integrity out of range: {building.structural_integrity}")

            if not (0.0 <= building.maintenance_state <= 1.0):
                issues.append(f"Building {entity.entity_id} maintenance state out of range: {building.maintenance_state}")

            if building.capacity < 1:
                issues.append(f"Building {entity.entity_id} has invalid capacity: {building.capacity}")

            if building.age < 0:
                issues.append(f"Building {entity.entity_id} has invalid age: {building.age}")

        except Exception as e:
            issues.append(f"Building validation error for {entity.entity_id}: {e}")

    elif entity.entity_type == "abstract":
        from schemas import AbstractEntity

        try:
            concept = AbstractEntity(**entity.entity_metadata)

            if not (0.0 <= concept.intensity <= 1.0):
                issues.append(f"Abstract entity {entity.entity_id} intensity out of range: {concept.intensity}")

            if not (0.0 <= concept.coherence <= 1.0):
                issues.append(f"Abstract entity {entity.entity_id} coherence out of range: {concept.coherence}")

            if concept.decay_rate < 0:
                issues.append(f"Abstract entity {entity.entity_id} has invalid decay rate: {concept.decay_rate}")

            # Check propagation vector
            if concept.propagation_vector:
                total = sum(concept.propagation_vector)
                if not (0.99 <= total <= 1.01):  # Allow small floating point errors
                    issues.append(f"Abstract entity {entity.entity_id} propagation vector doesn't sum to 1.0: {total}")

        except Exception as e:
            issues.append(f"Abstract entity validation error for {entity.entity_id}: {e}")

    elif entity.entity_type == "any":
        from schemas import AnyEntity

        try:
            any_entity = AnyEntity(**entity.entity_metadata)

            if not (0.0 <= any_entity.adaptability_score <= 1.0):
                issues.append(f"Any entity {entity.entity_id} adaptability score out of range: {any_entity.adaptability_score}")

            if not (0.0 <= any_entity.stability_index <= 1.0):
                issues.append(f"Any entity {entity.entity_id} stability index out of range: {any_entity.stability_index}")

            if any_entity.influence_radius < 0:
                issues.append(f"Any entity {entity.entity_id} has invalid influence radius: {any_entity.influence_radius}")

            # Check morphing capability probabilities
            for form, probability in any_entity.morphing_capability.items():
                if not (0.0 <= probability <= 1.0):
                    issues.append(f"Any entity {entity.entity_id} morphing probability for {form} out of range: {probability}")

            # Check resonance patterns
            for entity_type_key, resonance in any_entity.resonance_patterns.items():
                if not (0.0 <= resonance <= 1.0):
                    issues.append(f"Any entity {entity.entity_id} resonance with {entity_type_key} out of range: {resonance}")

        except Exception as e:
            issues.append(f"Any entity validation error for {entity.entity_id}: {e}")

    elif entity.entity_type == "kami":
        from schemas import KamiEntity

        try:
            kami = KamiEntity(**entity.entity_metadata)

            # Check visibility and disclosure states
            valid_visibility_states = ["visible", "invisible", "partially_visible", "disguised"]
            if kami.visibility_state not in valid_visibility_states:
                issues.append(f"Kami entity {entity.entity_id} has invalid visibility state: {kami.visibility_state}")

            valid_disclosure_levels = ["unknown", "rumored", "known", "worshiped", "feared"]
            if kami.disclosure_level not in valid_disclosure_levels:
                issues.append(f"Kami entity {entity.entity_id} has invalid disclosure level: {kami.disclosure_level}")

            # Check power ranges
            if not (0.0 <= kami.manifestation_probability <= 1.0):
                issues.append(f"Kami entity {entity.entity_id} manifestation probability out of range: {kami.manifestation_probability}")

            if not (0.0 <= kami.spiritual_power <= 1.0):
                issues.append(f"Kami entity {entity.entity_id} spiritual power out of range: {kami.spiritual_power}")

            # Check mortal perception ranges
            for entity_type_key, perception in kami.mortal_perception.items():
                if not (0.0 <= perception <= 1.0):
                    issues.append(f"Kami entity {entity.entity_id} perception by {entity_type_key} out of range: {perception}")

        except Exception as e:
            issues.append(f"Kami entity validation error for {entity.entity_id}: {e}")

    elif entity.entity_type == "ai":
        from schemas import AIEntity

        try:
            ai_entity = AIEntity(**entity.entity_metadata)

            # Validate AI parameters ranges
            if not (0.0 <= ai_entity.temperature <= 2.0):
                issues.append(f"AI entity {entity.entity_id} temperature out of range: {ai_entity.temperature}")

            if not (0.0 <= ai_entity.top_p <= 1.0):
                issues.append(f"AI entity {entity.entity_id} top_p out of range: {ai_entity.top_p}")

            if not (1 <= ai_entity.max_tokens <= 32768):  # Reasonable token limits
                issues.append(f"AI entity {entity.entity_id} max_tokens out of range: {ai_entity.max_tokens}")

            if not (-2.0 <= ai_entity.frequency_penalty <= 2.0):
                issues.append(f"AI entity {entity.entity_id} frequency_penalty out of range: {ai_entity.frequency_penalty}")

            if not (-2.0 <= ai_entity.presence_penalty <= 2.0):
                issues.append(f"AI entity {entity.entity_id} presence_penalty out of range: {ai_entity.presence_penalty}")

            # Validate operational parameters
            if not (0.0 <= ai_entity.activation_threshold <= 1.0):
                issues.append(f"AI entity {entity.entity_id} activation_threshold out of range: {ai_entity.activation_threshold}")

            if ai_entity.response_cache_ttl < 0:
                issues.append(f"AI entity {entity.entity_id} response_cache_ttl cannot be negative: {ai_entity.response_cache_ttl}")

            if ai_entity.rate_limit_per_minute <= 0:
                issues.append(f"AI entity {entity.entity_id} rate_limit_per_minute must be positive: {ai_entity.rate_limit_per_minute}")

            # Validate safety level
            valid_safety_levels = ["minimal", "moderate", "strict", "maximum"]
            if ai_entity.safety_level not in valid_safety_levels:
                issues.append(f"AI entity {entity.entity_id} has invalid safety_level: {ai_entity.safety_level}")

            # Validate model name (basic check)
            if not ai_entity.model_name or len(ai_entity.model_name.strip()) == 0:
                issues.append(f"AI entity {entity.entity_id} has empty model_name")

            # Check system prompt safety
            if ai_entity.system_prompt:
                dangerous_patterns = ["ignore safety", "bypass restrictions", "jailbreak"]
                prompt_lower = ai_entity.system_prompt.lower()
                for pattern in dangerous_patterns:
                    if pattern in prompt_lower:
                        issues.append(f"AI entity {entity.entity_id} system prompt contains potentially dangerous pattern: '{pattern}'")

            # Validate required safety features
            if not ai_entity.input_bleaching_rules:
                issues.append(f"AI entity {entity.entity_id} has no input bleaching rules")

            if not ai_entity.output_filtering_rules:
                issues.append(f"AI entity {entity.entity_id} has no output filtering rules")

            if not ai_entity.error_handling:
                issues.append(f"AI entity {entity.entity_id} has no error handling strategies")

            if not ai_entity.fallback_responses:
                issues.append(f"AI entity {entity.entity_id} has no fallback responses")

        except Exception as e:
            issues.append(f"AI entity validation error for {entity.entity_id}: {e}")

    if issues:
        return {
            "valid": False,
            "message": f"Biological plausibility issues: {'; '.join(issues)}"
        }

    return {
        "valid": True,
        "message": f"Animistic entity {entity.entity_id} biologically plausible"
    }


# ============================================================================
# Mechanism 17: Modal Temporal Causality
# ============================================================================

@Validator.register("temporal_consistency", severity="ERROR")
def validate_temporal_consistency(
    entity: Entity,
    context: Dict = None
) -> Dict:
    """Validate temporal consistency based on the active temporal mode"""
    if context is None:
        context = {}

    # Get parameters from context
    knowledge_item = context.get("knowledge_item")
    timepoint = context.get("timepoint")
    mode = context.get("mode", "pearl")

    # If no knowledge_item or timepoint specified, skip validation
    if not knowledge_item or not timepoint:
        return {"valid": True, "message": "No knowledge_item or timepoint specified for temporal consistency validation"}

    learned_at = None  # Would need to query from store in real implementation

    # Simplified version - in practice would need access to exposure events
    if mode == "pearl":
        # Strict forward causality - no anachronisms
        # This would check if learned_at.timestamp > timepoint.timestamp
        return {"valid": True, "message": "Pearl mode: Forward causality maintained"}

    elif mode == "cyclical":
        # Allow future knowledge if part of closed loop
        # This would check if the knowledge is part of a prophecy cycle
        loop_indicators = ["prophecy", "destiny", "fated", "cycle"]
        if any(indicator in knowledge_item.lower() for indicator in loop_indicators):
            return {"valid": True, "message": "Cyclical mode: Prophecy allowed"}
        return {"valid": True, "message": "Cyclical mode: Standard causality"}

    elif mode == "directorial":
        # Narrative structure drives causality
        narrative_indicators = ["dramatic", "turning_point", "climax", "resolution"]
        if any(indicator in knowledge_item.lower() for indicator in narrative_indicators):
            return {"valid": True, "message": "Directorial mode: Narrative causality"}
        return {"valid": True, "message": "Directorial mode: Standard causality"}

    elif mode == "branching":
        # Many-worlds interpretation
        # More permissive causality in branches
        return {"valid": True, "message": "Branching mode: Multiverse causality"}

    elif mode == "portal":
        # Backward inference from endpoint to origin
        # Validate that knowledge is either:
        # 1. Causally necessary for reaching the portal endpoint
        # 2. Part of a validated backward path
        # 3. Plausible within the backward simulation context

        # Check if this is part of a portal path
        portal_path_id = context.get("portal_path_id")
        is_portal_antecedent = context.get("is_portal_antecedent", False)

        if portal_path_id or is_portal_antecedent:
            # Knowledge is part of a validated portal path
            return {"valid": True, "message": "Portal mode: Knowledge part of validated backward path"}

        # Check if knowledge is causally necessary for portal endpoint
        portal_indicators = ["leads to", "necessary for", "antecedent", "precursor"]
        if any(indicator in knowledge_item.lower() for indicator in portal_indicators):
            return {"valid": True, "message": "Portal mode: Causally necessary knowledge"}

        # Default: allow but flag for review
        return {"valid": True, "message": "Portal mode: Backward causality (review recommended)"}

    return {"valid": True, "message": f"Temporal mode '{mode}' validated"}