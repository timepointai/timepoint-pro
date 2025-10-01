# ============================================================================
# temporal_chain.py - Temporal chain builder for connected timepoints
# ============================================================================
from datetime import datetime, timedelta
from typing import List, Dict, Any
from schemas import Timepoint, ResolutionLevel
from entity_templates import HISTORICAL_CONTEXTS


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
