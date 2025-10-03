# ============================================================================
# temporal_chain.py - Temporal chain builder for connected timepoints
# ============================================================================
from datetime import datetime, timedelta
from typing import List, Dict, Any
from schemas import Timepoint, ResolutionLevel, Entity
from entity_templates import HISTORICAL_CONTEXTS
from validation import couple_pain_to_cognition, couple_illness_to_cognition


def build_temporal_chain(context_name: str, num_timepoints: int = 5) -> List[Timepoint]:
    """Generate sequence of connected timepoints from historical context"""

    if context_name not in HISTORICAL_CONTEXTS:
        raise ValueError(f"Unknown context: {context_name}")

    context = HISTORICAL_CONTEXTS[context_name]
    base_timestamp = datetime.fromisoformat(context["timepoint"])
    entities = [e["entity_id"] for e in context["entities"]]

    timepoints = []

    # Create the initial timepoint (the main event)
    initial_timepoint = Timepoint(
        timepoint_id=f"{context_name}_t0",
        timestamp=base_timestamp,
        event_description=context["event"],
        entities_present=entities,
        causal_parent=None,  # First timepoint has no parent
        resolution_level=ResolutionLevel.TRAINED  # Peak moment gets highest resolution
    )
    timepoints.append(initial_timepoint)

    # Generate subsequent timepoints with causal connections
    for i in range(1, num_timepoints):
        # Vary the time intervals (some close together, some farther apart)
        if i == 1:
            # Immediate aftermath (minutes to hours)
            time_delta = timedelta(hours=i)
        elif i == 2:
            # Next day
            time_delta = timedelta(days=1)
        else:
            # Days to weeks later
            time_delta = timedelta(days=i*2)

        timestamp = base_timestamp + time_delta

        # Create event descriptions that build causally on previous events
        event_descriptions = {
            "founding_fathers_1789": [
                "Immediate aftermath of the inauguration - crowds dispersing, officials returning to duties",
                "First cabinet meeting the next day - establishing government operations",
                "Early policy discussions in the following week - setting precedents for the new republic",
                "First congressional session convening - legislative work beginning",
                "Diplomatic reception preparations - establishing international relations"
            ]
        }

        description = event_descriptions.get(context_name, [f"Continuing developments {i} periods after {context['event']}"])[min(i-1, 4)]

        # Resolution decreases over time (closer events more detailed)
        if i == 1:
            resolution = ResolutionLevel.DIALOG  # Still very detailed
        elif i == 2:
            resolution = ResolutionLevel.GRAPH  # Good detail level
        else:
            resolution = ResolutionLevel.SCENE  # Lower detail for later events

        timepoint = Timepoint(
            timepoint_id=f"{context_name}_t{i}",
            timestamp=timestamp,
            event_description=description,
            entities_present=entities,  # Same entities present (could vary in more complex scenarios)
            causal_parent=timepoints[-1].timepoint_id,  # Link to previous timepoint
            resolution_level=resolution
        )
        timepoints.append(timepoint)

    return timepoints


def get_temporal_chain_info(context_name: str) -> Dict[str, Any]:
    """Get metadata about a temporal chain for a context"""
    if context_name not in HISTORICAL_CONTEXTS:
        raise ValueError(f"Unknown context: {context_name}")

    context = HISTORICAL_CONTEXTS[context_name]

    return {
        "context_name": context_name,
        "base_event": context["event"],
        "base_timestamp": context["timepoint"],
        "entities_count": len(context["entities"]),
        "entity_ids": [e["entity_id"] for e in context["entities"]],
        "recommended_timepoints": 5,  # Default recommendation
        "description": f"Temporal evolution following {context['event']}"
    }


def has_causal_path(from_timepoint_id: str, to_timepoint_id: str, store) -> bool:
    """
    Check if there's a causal path from from_timepoint_id to to_timepoint_id.
    Returns True if to_timepoint can causally depend on information from from_timepoint.
    """
    if from_timepoint_id == to_timepoint_id:
        return True

    # Get the target timepoint
    to_timepoint = store.get_timepoint(to_timepoint_id)
    if not to_timepoint:
        return False

    # Walk backwards through causal parents
    current = to_timepoint
    visited = set()

    while current and current.timepoint_id not in visited:
        visited.add(current.timepoint_id)

        if current.timepoint_id == from_timepoint_id:
            return True

        if current.causal_parent:
            current = store.get_timepoint(current.causal_parent)
        else:
            break

    return False


def get_causal_ancestors(timepoint_id: str, store) -> List[str]:
    """
    Get all causal ancestors of a timepoint (timepoints that could influence it).
    Returns list of timepoint_ids in chronological order (oldest first).
    """
    ancestors = []
    current = store.get_timepoint(timepoint_id)

    while current:
        if current.causal_parent:
            ancestors.insert(0, current.causal_parent)  # Insert at beginning for chronological order
            current = store.get_timepoint(current.causal_parent)
        else:
            break

    return ancestors


def validate_temporal_reference(entity_id: str, knowledge_item: str, timepoint_id: str, store) -> Dict[str, Any]:
    """
    Validate that an entity could have learned referenced knowledge through causal chains.

    Returns:
        {"valid": bool, "message": str, "learned_at": Optional[str]}
    """
    # Find where this knowledge was first learned (simplified - in practice would track exposure events)
    # For now, we'll check if the entity has this knowledge in any previous timepoint

    timepoint = store.get_timepoint(timepoint_id)
    if not timepoint:
        return {"valid": False, "message": f"Timepoint {timepoint_id} not found", "learned_at": None}

    # Get all causal ancestors
    ancestors = get_causal_ancestors(timepoint_id, store)

    # Check if entity had this knowledge at any ancestor timepoint
    for ancestor_id in ancestors + [timepoint_id]:  # Include current timepoint
        ancestor_knowledge = store.get_entity_knowledge_at_timepoint(entity_id, ancestor_id)
        if ancestor_knowledge and knowledge_item in ancestor_knowledge:
            return {
                "valid": True,
                "message": f"Knowledge '{knowledge_item}' available through causal chain",
                "learned_at": ancestor_id
            }

    return {
        "valid": False,
        "message": f"Knowledge '{knowledge_item}' not available through causal chain - potential temporal inconsistency",
        "learned_at": None
    }


def validate_causal_chain_integrity(timepoints: List[Timepoint]) -> Dict[str, Any]:
    """
    Validate that a list of timepoints forms a valid causal chain.

    Checks:
    - No cycles
    - Chronological order
    - Parent references exist
    """
    issues = []

    # Build lookup dict
    timepoint_dict = {tp.timepoint_id: tp for tp in timepoints}

    # Check each timepoint
    for tp in timepoints:
        # Check parent reference exists (except for root)
        if tp.causal_parent and tp.causal_parent not in timepoint_dict:
            issues.append(f"Timepoint {tp.timepoint_id} references non-existent parent {tp.causal_parent}")

        # Check chronological order
        if tp.causal_parent:
            parent = timepoint_dict.get(tp.causal_parent)
            if parent and tp.timestamp <= parent.timestamp:
                issues.append(f"Timepoint {tp.timepoint_id} ({tp.timestamp}) is not after parent {tp.causal_parent} ({parent.timestamp})")

    # Check for cycles (simplified - more complex cycle detection could be added)
    visited = set()
    for tp in timepoints:
        current = tp
        chain = []
        while current:
            if current.timepoint_id in chain:
                issues.append(f"Cycle detected in causal chain at {current.timepoint_id}")
                break

            chain.append(current.timepoint_id)

            if current.causal_parent and current.causal_parent in timepoint_dict:
                current = timepoint_dict[current.causal_parent]
            else:
                break

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "message": f"Causal chain validation: {len(issues)} issues found"
    }


# ============================================================================
# Body-Mind Coupling Integration (Mechanism 8.1)
# ============================================================================

def apply_body_mind_coupling(entity: Entity) -> Entity:
    """
    Apply body-mind coupling to update cognitive state based on physical state.
    This should be called whenever entity state is updated to ensure physical
    conditions affect cognitive performance.
    """
    # Get current physical and cognitive states
    physical = entity.physical_tensor
    cognitive = entity.cognitive_tensor

    # Apply pain coupling
    updated_cognitive = couple_pain_to_cognition(physical, cognitive)

    # Apply illness coupling
    updated_cognitive = couple_illness_to_cognition(physical, updated_cognitive)

    # Update the entity's cognitive tensor
    entity.cognitive_tensor = updated_cognitive

    return entity


def update_entity_state_with_coupling(entity: Entity, **state_updates) -> Entity:
    """
    Update entity state and apply body-mind coupling.
    This is the main function to call when updating entity states.
    """
    # Apply any state updates first
    for key, value in state_updates.items():
        if hasattr(entity, key):
            setattr(entity, key, value)

    # Apply body-mind coupling
    return apply_body_mind_coupling(entity)
