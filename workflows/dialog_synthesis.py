# ============================================================================
# workflows/dialog_synthesis.py - Dialog Synthesis (Mechanism 8, 11)
# ============================================================================
"""
Dialog synthesis with body-mind coupling.

Contains:
- couple_pain_to_cognition: Apply pain effects to cognitive state (@M8)
- couple_illness_to_cognition: Apply illness effects to cognitive state
- synthesize_dialog: Generate conversation with full context (@M11)
- Helper functions for exposure events, relationship metrics, etc.
"""

from typing import List, Dict, Optional
from datetime import datetime
import json
import logging

from schemas import Entity, Dialog, ExposureEvent
from metadata.tracking import track_mechanism

logger = logging.getLogger(__name__)


@track_mechanism("M8", "embodied_states_pain")
def couple_pain_to_cognition(physical: 'PhysicalTensor', cognitive: 'CognitiveTensor') -> 'CognitiveTensor':
    """Apply pain effects to cognitive state (body-mind coupling)"""
    pain_factor = physical.pain_level

    # Create a copy of the cognitive tensor to avoid modifying the original
    coupled = cognitive.copy()

    # Pain reduces energy budget and patience
    coupled.energy_budget *= (1.0 - pain_factor * 0.5)
    coupled.patience_threshold -= pain_factor * 0.4
    coupled.decision_confidence *= (1.0 - pain_factor * 0.2)

    # Pain affects emotional state
    coupled.emotional_valence -= pain_factor * 0.3

    return coupled


def couple_illness_to_cognition(physical: 'PhysicalTensor', cognitive: 'CognitiveTensor') -> 'CognitiveTensor':
    """Apply illness effects to cognitive state (body-mind coupling)"""
    # Create a copy of the cognitive tensor to avoid modifying the original
    coupled = cognitive.copy()

    # Fever impairs judgment and engagement
    if physical.fever > 38.5:  # Celsius
        coupled.decision_confidence *= 0.7
        coupled.risk_tolerance += 0.2
        coupled.social_engagement -= 0.4

    return coupled


def compute_age_constraints(age: float) -> Dict[str, float]:
    """Compute age-dependent capability degradation"""
    return {
        "stamina": max(0.3, 1.0 - (age - 25) * 0.01),
        "vision": max(0.4, 1.0 - (age - 20) * 0.015),
        "hearing": max(0.5, 1.0 - (age - 30) * 0.01),
        "recovery_rate": 1.0 / (1.0 + (age - 30) * 0.05),
        "cognitive_speed": max(0.5, 1.0 - (age - 30) * 0.008)
    }


def get_recent_exposure_events(entity: Entity, n: int = 5, store: Optional['GraphStore'] = None) -> List[Dict]:
    """Get recent exposure events for an entity"""
    if not store:
        return []

    exposure_events = store.get_exposure_events(entity.entity_id, limit=n)
    return [
        {
            "information": exp.information,
            "source": exp.source,
            "timestamp": exp.timestamp,
            "event_type": exp.event_type
        }
        for exp in exposure_events
    ]


def compute_relationship_metrics(entity_a: Entity, entity_b: Entity) -> Dict:
    """Compute relationship metrics between two entities"""
    # Get knowledge states
    knowledge_a = set(entity_a.entity_metadata.get("knowledge_state", []))
    knowledge_b = set(entity_b.entity_metadata.get("knowledge_state", []))

    # Compute metrics
    shared_knowledge = len(knowledge_a & knowledge_b)
    total_unique = len(knowledge_a | knowledge_b)

    return {
        "shared_knowledge": shared_knowledge,
        "alignment": shared_knowledge / max(1, total_unique),  # Simple alignment metric
        "interaction_count": 0,  # Would need to track from dialog history
        "trust": 0.5  # Default neutral trust
    }


def get_timepoint_position(timeline: List[Dict], timepoint: 'Timepoint') -> str:
    """Get position description in timeline"""
    # Simple implementation - could be enhanced
    return f"timepoint_{len(timeline)}"


def extract_knowledge_references(content: str) -> List[str]:
    """
    Extract knowledge items referenced in dialog content.

    Looks for capitalized words (proper nouns, concepts) that might represent
    knowledge transfer during dialog. Returns normalized (lowercase) versions
    for consistent comparison.

    Args:
        content: Dialog turn content to analyze

    Returns:
        List of unique knowledge references found (lowercase)
    """
    # Split without lowercasing first - we need to detect capitalization
    words = content.split()
    knowledge_items = []

    # Look for capitalized words that might be proper nouns or concepts
    for word in words:
        # Strip punctuation for checking
        clean_word = word.strip('.,!?;:"\'-()[]{}')
        if clean_word and len(clean_word) > 3 and clean_word[0].isupper():
            # Store lowercase for consistent comparison
            knowledge_items.append(clean_word.lower())

    return list(set(knowledge_items))


def create_exposure_event(entity_id: str, information: str, source: str, event_type: str,
                         timestamp: datetime, confidence: float = 0.9,
                         store: Optional['GraphStore'] = None,
                         timepoint_id: Optional[str] = None):
    """
    Create an exposure event for information transfer.

    Args:
        entity_id: Entity receiving the information
        information: The knowledge item being transferred
        source: Entity providing the information
        event_type: Type of exposure (told, witnessed, etc.)
        timestamp: When the exposure occurred
        confidence: Confidence level (0.0-1.0)
        store: GraphStore to save the event
        timepoint_id: Optional timepoint ID for context
    """
    if not store:
        logger.debug(f"[M3] No store provided, skipping exposure event: {source} -> {entity_id}")
        return

    exposure = ExposureEvent(
        entity_id=entity_id,
        event_type=event_type,
        information=information,
        source=source,
        timestamp=timestamp,
        confidence=confidence,
        timepoint_id=timepoint_id
    )
    store.save_exposure_event(exposure)
    logger.info(f"[M3] Created exposure event: {source} -> {entity_id} (info: {information[:50] if len(information) > 50 else information})")


@track_mechanism("M3", "exposure_event_integration")
def _build_knowledge_from_exposures(
    entity: Entity,
    store: Optional['GraphStore'] = None,
    limit: int = 20
) -> List[Dict]:
    """
    Build knowledge context from exposure events (M3) for dialog synthesis (M11).

    This connects M3 (Exposure Events) → M11 (Dialog Synthesis) by:
    1. Retrieving exposure events from storage
    2. Combining with static knowledge from entity metadata
    3. Prioritizing high-confidence, recent information

    Args:
        entity: The entity to build knowledge for
        store: GraphStore for retrieving exposure events
        limit: Maximum number of knowledge items to return

    Returns:
        List of knowledge items with source/confidence metadata
    """
    knowledge_items = []

    # Get dynamic knowledge from exposure events (M3)
    if store:
        exposure_events = store.get_exposure_events(entity.entity_id, limit=limit)
        for exp in exposure_events:
            knowledge_items.append({
                "content": exp.information,
                "source": exp.source or "direct_experience",
                "confidence": exp.confidence,
                "event_type": exp.event_type,
                "timestamp": exp.timestamp.isoformat() if hasattr(exp.timestamp, 'isoformat') else str(exp.timestamp),
                "from_exposure": True
            })

    # Get static knowledge from entity metadata (fallback/supplemental)
    static_knowledge = entity.entity_metadata.get("knowledge_state", [])
    for item in static_knowledge:
        # Check if this knowledge is already in exposure events (avoid duplicates)
        if isinstance(item, str):
            # Simple string knowledge item
            if not any(k.get("content") == item for k in knowledge_items):
                knowledge_items.append({
                    "content": item,
                    "source": "background_knowledge",
                    "confidence": 0.8,  # Default confidence for static knowledge
                    "event_type": "prior",
                    "from_exposure": False
                })
        elif isinstance(item, dict):
            # Already structured knowledge item
            content = item.get("content", str(item))
            if not any(k.get("content") == content for k in knowledge_items):
                knowledge_items.append({
                    "content": content,
                    "source": item.get("source", "background_knowledge"),
                    "confidence": item.get("confidence", 0.8),
                    "event_type": item.get("event_type", "prior"),
                    "from_exposure": False
                })

    # Sort by confidence (highest first), then by recency (exposure events first)
    knowledge_items.sort(
        key=lambda k: (k.get("confidence", 0.5), k.get("from_exposure", False)),
        reverse=True
    )

    return knowledge_items[:limit]


def _apply_circadian_energy_adjustment(base_energy: float, hour: int,
                                       store: Optional['GraphStore'] = None) -> float:
    """Apply M14 circadian energy adjustment if configuration is available"""
    # Try to get circadian config from store context
    circadian_config = {}
    if store and hasattr(store, 'context'):
        circadian_config = store.context.get('circadian_config', {})

    # If no config, return base energy unchanged
    if not circadian_config:
        return base_energy

    # Import M14 mechanism function
    from validation import compute_energy_cost_with_circadian

    # Apply circadian adjustment to base energy (treat as "conversation" activity cost)
    adjusted_energy = compute_energy_cost_with_circadian(
        activity="conversation",
        hour=hour,
        base_cost=base_energy,
        circadian_config=circadian_config
    )

    return adjusted_energy


@track_mechanism("M11", "dialog_synthesis")
def synthesize_dialog(
    entities: List[Entity],
    timepoint: 'Timepoint',
    timeline: List[Dict],
    llm: 'LLMClient',
    store: Optional['GraphStore'] = None
) -> Dialog:
    """Generate conversation with full physical/emotional/temporal context"""

    # Sanitize timeline to ensure all datetime objects are converted to strings
    sanitized_timeline = []
    for item in timeline:
        sanitized_item = {}
        for key, value in item.items():
            if hasattr(value, 'isoformat'):  # datetime object
                sanitized_item[key] = value.isoformat()
            else:
                sanitized_item[key] = value
        sanitized_timeline.append(sanitized_item)
    timeline = sanitized_timeline

    # Build comprehensive context for each participant
    participants_context = []
    for entity in entities:
        # Get current state from metadata (more defensive than property access)
        physical_data = entity.entity_metadata.get("physical_tensor", {})
        cognitive_data = entity.entity_metadata.get("cognitive_tensor", {})

        # Try to construct tensors from metadata
        physical = None
        cognitive = None
        if physical_data and 'age' in physical_data:
            try:
                from schemas import PhysicalTensor
                physical = PhysicalTensor(**physical_data)
            except Exception as e:
                print(f"  ⚠️  Failed to construct physical tensor for {entity.entity_id}: {e}")

        if cognitive_data:
            try:
                from schemas import CognitiveTensor
                cognitive = CognitiveTensor(**cognitive_data)
            except Exception as e:
                print(f"  ⚠️  Failed to construct cognitive tensor for {entity.entity_id}: {e}")

        # If entity doesn't have tensor attributes, skip it with warning
        if physical is None or cognitive is None:
            # Check if entity has TTM tensor (prospection-only entities)
            if hasattr(entity, 'tensor') and entity.tensor:
                print(f"  ⚠️  Skipping {entity.entity_id} in dialog synthesis - has TTM tensor but not trained (no physical/cognitive tensors)")
            else:
                print(f"  ⚠️  Skipping {entity.entity_id} in dialog synthesis - missing tensor data")
            continue

        # Apply body-mind coupling
        coupled_cognitive = couple_pain_to_cognition(physical, cognitive)
        coupled_cognitive = couple_illness_to_cognition(physical, coupled_cognitive)

        # Get temporal context
        recent_experiences = get_recent_exposure_events(entity, n=5, store=store)
        relationship_states = {
            other.entity_id: compute_relationship_metrics(entity, other)
            for other in entities if other.entity_id != entity.entity_id
        }

        # Build knowledge from exposure events (M3 → M11 connection)
        knowledge_from_exposures = _build_knowledge_from_exposures(entity, store=store, limit=20)

        participant_ctx = {
            "id": entity.entity_id,

            # Knowledge & Beliefs - now includes exposure events from M3
            "knowledge": knowledge_from_exposures,
            "beliefs": coupled_cognitive.decision_confidence,  # Using confidence as belief proxy

            # Personality & Goals
            "personality_traits": entity.entity_metadata.get("personality_traits", ["determined", "principled"]),
            "current_goals": entity.entity_metadata.get("current_goals", ["serve_country"]),

            # Physical State (affects engagement)
            "age": physical.age,
            "health": physical.health_status,
            "pain": {
                "level": physical.pain_level,
                "location": physical.pain_location
            } if physical.pain_level > 0.1 else None,
            "stamina": physical.stamina,
            "physical_constraints": compute_age_constraints(physical.age),

            # Cognitive/Emotional State (affects tone)
            "emotional_state": {
                "valence": coupled_cognitive.emotional_valence,
                "arousal": coupled_cognitive.emotional_arousal
            },
            "energy_remaining": _apply_circadian_energy_adjustment(
                base_energy=coupled_cognitive.energy_budget,
                hour=timepoint.timestamp.hour,
                store=store
            ),
            "decision_confidence": coupled_cognitive.decision_confidence,
            "patience_level": coupled_cognitive.patience_threshold,

            # Temporal Context
            "recent_experiences": [
                {"event": exp["information"], "source": exp["source"], "when": str(exp["timestamp"])}
                for exp in recent_experiences
            ],
            "timepoint_context": {
                "event": timepoint.event_description,
                "timestamp": timepoint.timestamp.isoformat(),  # Phase 7.5: Convert datetime to JSON-serializable string
                "position_in_chain": get_timepoint_position(timeline, timepoint)
            },

            # Relationship State
            "relationships": {
                other_id: {
                    "shared_knowledge": rel["shared_knowledge"],
                    "belief_alignment": rel["alignment"],
                    "past_interactions": rel["interaction_count"],
                    "trust_level": rel.get("trust", 0.5)
                }
                for other_id, rel in relationship_states.items()
            }
        }

        participants_context.append(participant_ctx)

    # Check if we have enough participants after filtering
    if len(participants_context) < 2:
        print(f"  ⚠️  Not enough valid participants for dialog ({len(participants_context)}/2 minimum)")
        # Return a minimal dialog object
        return Dialog(
            dialog_id=f"dialog_{timepoint.timepoint_id}_skipped",
            timepoint_id=timepoint.timepoint_id,
            participants=json.dumps([e.entity_id for e in entities]),
            turns=json.dumps([]),
            context_used=json.dumps({"skipped": True, "reason": "insufficient_participants"}),
            duration_seconds=0,
            information_transfer_count=0
        )

    # Build scene context
    scene_context = {
        "location": getattr(timepoint, 'location', 'unspecified'),
        "time_of_day": timepoint.timestamp.strftime("%I:%M %p"),
        "formality_level": "formal",  # Could be inferred from event description
        "social_constraints": ["historical_accuracy", "period_language"]
    }

    # Construct rich prompt (with JSON serialization error handling)
    try:
        participants_json = json.dumps(participants_context, indent=2)
    except TypeError as e:
        print(f"  ⚠️  JSON serialization error in participants_context: {e}")
        # Try with default handler for datetime
        participants_json = json.dumps(participants_context, indent=2, default=str)

    try:
        scene_json = json.dumps(scene_context, indent=2)
    except TypeError as e:
        print(f"  ⚠️  JSON serialization error in scene_context: {e}")
        scene_json = json.dumps(scene_context, indent=2, default=str)

    prompt = f"""Generate a realistic conversation between {len(entities)} historical figures.

PARTICIPANTS:
{participants_json}

SCENE CONTEXT:
{scene_json}

CRITICAL INSTRUCTIONS:
1. Physical state affects participation:
   - High pain → shorter responses, irritable tone, may leave early
   - Low stamina → less engaged, seeking to end conversation
   - Poor health → reduced verbal complexity

2. Emotional state affects tone:
   - Negative valence → pessimistic, critical, withdrawn
   - High arousal + negative valence → confrontational, agitated
   - Low energy → brief responses, less elaboration

3. Relationship dynamics:
   - Low alignment → disagreements, challenges
   - High shared knowledge → references to past discussions
   - Low trust → guarded statements, diplomatic language

4. Temporal awareness:
   - Reference recent experiences naturally
   - React to timepoint context (inauguration, meeting, etc.)
   - Show anticipation/anxiety about future if present

5. Knowledge constraints:
   - ONLY reference information in knowledge list
   - Create exposure opportunities (one person tells another new info)
   - Show personality through what they emphasize

Generate 8-12 dialog turns showing realistic interaction given these constraints.
"""

    # Generate dialog with structured output
    dialog_data = llm.generate_dialog(
        prompt=prompt,
        max_tokens=2000
    )

    # Create ExposureEvents for information exchange
    exposure_events_created = 0
    if store:
        print(f"    [M11→M3] Processing {len(dialog_data.turns)} dialog turns for exposure events")
        for turn in dialog_data.turns:
            # Extract knowledge items mentioned in turn
            mentioned_knowledge = extract_knowledge_references(turn.content)

            if mentioned_knowledge:
                print(f"    [M11→M3] Turn by {turn.speaker}: {len(mentioned_knowledge)} knowledge refs: {mentioned_knowledge[:3]}")

            # Create exposure for all listeners
            for listener in entities:
                if listener.entity_id != turn.speaker:
                    for knowledge_item in mentioned_knowledge:
                        create_exposure_event(
                            entity_id=listener.entity_id,
                            information=knowledge_item,
                            source=turn.speaker,
                            event_type="told",
                            timestamp=turn.timestamp,
                            confidence=0.9,
                            store=store,
                            timepoint_id=timepoint.timepoint_id  # NEW: Set timepoint context
                        )
                        exposure_events_created += 1

        print(f"    [M11→M3] Created {exposure_events_created} exposure events from dialog")

    # Convert dialog turns to JSON-serializable format (handle datetime objects)
    turns_data = []
    for turn in dialog_data.turns:
        turn_dict = turn.dict() if hasattr(turn, 'dict') else turn.model_dump()
        # Convert any datetime objects to ISO strings
        if 'timestamp' in turn_dict and hasattr(turn_dict['timestamp'], 'isoformat'):
            turn_dict['timestamp'] = turn_dict['timestamp'].isoformat()
        turns_data.append(turn_dict)

    return Dialog(
        dialog_id=f"dialog_{timepoint.timepoint_id}_{'_'.join([e.entity_id for e in entities])}",
        timepoint_id=timepoint.timepoint_id,
        participants=json.dumps([e.entity_id for e in entities]),
        turns=json.dumps(turns_data),  # Use sanitized turns
        context_used=json.dumps({
            "physical_states_applied": True,
            "emotional_states_applied": True,
            "body_mind_coupling_applied": True,
            "relationship_context_applied": True
        }),
        duration_seconds=dialog_data.total_duration,
        information_transfer_count=len(dialog_data.information_exchanged)
    )
