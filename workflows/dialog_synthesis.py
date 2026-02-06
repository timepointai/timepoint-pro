# ============================================================================
# workflows/dialog_synthesis.py - Dialog Synthesis (Mechanism 8, 11, 19)
# ============================================================================
"""
Dialog synthesis with body-mind coupling and intelligent knowledge extraction.

Contains:
- couple_pain_to_cognition: Apply pain effects to cognitive state (@M8)
- couple_illness_to_cognition: Apply illness effects to cognitive state
- synthesize_dialog: Generate conversation with full context (@M11)
- Knowledge extraction via M19 LLM agent (replaces naive word extraction)
- Helper functions for exposure events, relationship metrics, etc.

Knowledge Extraction (M19):
    Dialog synthesis now uses workflows.knowledge_extraction.extract_knowledge_from_dialog()
    for intelligent LLM-based extraction of semantic knowledge items. This replaced
    the naive extract_knowledge_references() function which just grabbed capitalized words.

    The M19 agent:
    - Extracts complete semantic units (not single words)
    - Understands context from causal graph
    - Categorizes knowledge (fact, decision, opinion, plan, etc.)
    - Assigns confidence and causal relevance scores
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


def _analyze_dialog_emotional_impact(
    turns: List[Dict],
    speaker_id: str
) -> Dict[str, float]:
    """
    Analyze dialog turns to compute emotional impact on a speaker.

    Returns changes to apply to emotional_valence and emotional_arousal
    based on dialog content patterns.

    Args:
        turns: List of dialog turn dicts with 'speaker', 'content' keys
        speaker_id: The entity to compute impact for

    Returns:
        Dict with 'valence_delta' and 'arousal_delta' values
    """
    valence_delta = 0.0
    arousal_delta = 0.0

    # Count turns by and to this speaker
    speaker_turns = [t for t in turns if t.get('speaker') == speaker_id]

    if not speaker_turns:
        return {"valence_delta": 0.0, "arousal_delta": 0.0}

    # Analyze content sentiment using keyword patterns
    positive_keywords = ["agree", "support", "excellent", "great", "thank", "appreciate",
                         "exciting", "opportunity", "succeed", "optimistic", "confident"]
    negative_keywords = ["disagree", "concern", "risk", "problem", "fail", "worried",
                         "challenge", "difficult", "unfortunately", "frustrat", "disappoint"]
    high_arousal_keywords = ["urgent", "immediately", "critical", "must", "now", "excited",
                            "amazing", "terrible", "disaster", "breakthrough", "!"]
    low_arousal_keywords = ["calm", "steady", "gradual", "perhaps", "maybe", "consider",
                           "eventually", "sometime", "possibly", "reflect"]

    for turn in speaker_turns:
        content_lower = turn.get('content', '').lower()

        # Valence impact
        for kw in positive_keywords:
            if kw in content_lower:
                valence_delta += 0.02
        for kw in negative_keywords:
            if kw in content_lower:
                valence_delta -= 0.02

        # Arousal impact (symmetric: +0.03 high, -0.03 low)
        for kw in high_arousal_keywords:
            if kw in content_lower:
                arousal_delta += 0.03
        for kw in low_arousal_keywords:
            if kw in content_lower:
                arousal_delta -= 0.03

    # Interaction dynamics: more turns = more engagement = higher arousal
    interaction_factor = min(len(speaker_turns) / 10.0, 0.08)  # Cap at 0.08
    arousal_delta += interaction_factor

    # Clamp deltas to symmetric ranges
    valence_delta = max(-0.3, min(0.3, valence_delta))
    arousal_delta = max(-0.25, min(0.25, arousal_delta))

    return {
        "valence_delta": valence_delta,
        "arousal_delta": arousal_delta
    }


def _persist_emotional_state_updates(
    entities: List[Entity],
    dialog_turns: List[Dict],
    coupled_cognitives: Dict[str, 'CognitiveTensor'],
    store: Optional['GraphStore'] = None
) -> int:
    """
    Persist emotional state updates to entities after dialog synthesis.

    This fixes the issue where emotional_valence and emotional_arousal
    stay at 0.0 by:
    1. Computing emotional impact from dialog content
    2. Combining with body-mind coupling effects
    3. Writing updates back to entity metadata

    Args:
        entities: List of entities that participated in dialog
        dialog_turns: List of dialog turn dicts
        coupled_cognitives: Dict mapping entity_id -> coupled CognitiveTensor
        store: Optional GraphStore for persistence

    Returns:
        Number of entities updated
    """
    updates_made = 0

    for entity in entities:
        entity_id = entity.entity_id

        # Get the coupled cognitive state (already has pain/illness effects)
        coupled = coupled_cognitives.get(entity_id)
        if not coupled:
            continue

        # Analyze dialog for emotional impact
        dialog_impact = _analyze_dialog_emotional_impact(dialog_turns, entity_id)

        # Apply arousal decay toward baseline before adding new impact.
        # Without decay, arousal only accumulates and saturates at 1.0
        # within a few dialog rounds. Exponential relaxation toward baseline
        # models natural stress recovery between interactions.
        arousal_baseline = 0.3
        arousal_decay_rate = 0.15  # 15% relaxation per dialog round
        decayed_arousal = (
            arousal_baseline
            + (coupled.emotional_arousal - arousal_baseline) * (1 - arousal_decay_rate)
        )

        # Compute new emotional values
        # Start from coupled cognitive (has body-mind coupling applied)
        new_valence = coupled.emotional_valence + dialog_impact["valence_delta"]
        new_arousal = decayed_arousal + dialog_impact["arousal_delta"]

        # Clamp to valid ranges (-1 to 1 for valence, 0 to 1 for arousal)
        new_valence = max(-1.0, min(1.0, new_valence))
        new_arousal = max(0.0, min(1.0, new_arousal))

        # Update entity metadata
        if "cognitive_tensor" not in entity.entity_metadata:
            entity.entity_metadata["cognitive_tensor"] = {}

        entity.entity_metadata["cognitive_tensor"]["emotional_valence"] = new_valence
        entity.entity_metadata["cognitive_tensor"]["emotional_arousal"] = new_arousal

        # Also update energy budget (conversations drain energy)
        energy_drain = len([t for t in dialog_turns if t.get('speaker') == entity_id]) * 0.02
        current_energy = coupled.energy_budget
        new_energy = max(0.0, current_energy - energy_drain)
        entity.entity_metadata["cognitive_tensor"]["energy_budget"] = new_energy

        updates_made += 1
        logger.debug(f"[M11] Updated emotional state for {entity_id}: "
                     f"valence={new_valence:.3f}, arousal={new_arousal:.3f}")

    if updates_made > 0:
        logger.info(f"[M11] Persisted emotional state updates for {updates_made} entities")

    return updates_made


def _sync_ttm_to_cognitive(entity: Entity) -> Optional['CognitiveTensor']:
    """
    Sync TTMTensor context values → CognitiveTensor (pretraining equivalent).

    This ensures that trained tensor values are propagated to the cognitive
    state used during dialog synthesis. Without this sync, entities start
    with default CognitiveTensor values (emotional_valence=0.0) regardless
    of their trained TTMTensor state.

    Called at entity load time, BEFORE dialog synthesis.

    Scale conversions:
    - TTMTensor valence (0-1) → CognitiveTensor valence (-1 to 1): cog = ttm * 2 - 1
    - TTMTensor energy (0-1) → CognitiveTensor energy (0-100): cog = ttm * 100
    - TTMTensor arousal (0-1) → CognitiveTensor arousal (0-1): same scale

    Args:
        entity: Entity with TTMTensor to sync from

    Returns:
        Updated CognitiveTensor if sync occurred, None otherwise
    """
    import json
    import base64
    import msgspec
    import numpy as np
    from schemas import CognitiveTensor

    # Check if entity has a trained tensor
    if not entity.tensor:
        logger.debug(f"[SYNC] {entity.entity_id}: No TTMTensor to sync from")
        return None

    try:
        # Decode TTMTensor
        tensor_dict = json.loads(entity.tensor)
        context = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["context_vector"])))

        # Extract values from context_vector
        # [0]=knowledge, [1]=valence, [2]=arousal, [3]=energy, [4]=confidence, [5]=patience, [6]=risk, [7]=social
        ttm_valence = context[1]  # 0-1 scale
        ttm_arousal = context[2]  # 0-1 scale
        ttm_energy = context[3]   # 0-1 scale
        ttm_confidence = context[4]  # 0-1 scale
        ttm_patience = context[5]  # 0-1 scale
        ttm_risk = context[6]  # 0-1 scale
        ttm_social = context[7]  # 0-1 scale

        # Scale conversions
        cog_valence = ttm_valence * 2 - 1  # 0-1 → -1 to 1
        cog_arousal = ttm_arousal  # same scale
        cog_energy = ttm_energy * 100  # 0-1 → 0-100
        cog_confidence = ttm_confidence  # same scale (but CognitiveTensor uses 0-1)
        cog_patience = ttm_patience * 100  # 0-1 → 0-100 (patience_threshold scale)
        cog_risk = ttm_risk  # same scale
        cog_social = ttm_social  # same scale

        # Get or create cognitive tensor data
        existing_cog = entity.entity_metadata.get("cognitive_tensor", {})

        # Check if cognitive tensor has default values (indicating no runtime updates yet)
        # Only sync if emotional values are at defaults to avoid overwriting runtime state
        existing_valence = existing_cog.get("emotional_valence", 0.0)
        existing_arousal = existing_cog.get("emotional_arousal", 0.0)

        # If already has non-default values, this entity has been updated at runtime
        # In that case, don't overwrite with TTM baseline
        if abs(existing_valence) > 0.01 or abs(existing_arousal) > 0.01:
            logger.debug(f"[SYNC] {entity.entity_id}: Skipping TTM→Cog sync (already has runtime values)")
            return CognitiveTensor(**existing_cog) if existing_cog else None

        # Update cognitive tensor with TTM values
        updated_cog = {
            **existing_cog,  # Preserve any other fields
            "emotional_valence": cog_valence,
            "emotional_arousal": cog_arousal,
            "energy_budget": cog_energy,
            "decision_confidence": cog_confidence,
            "patience_threshold": cog_patience,
            "risk_tolerance": cog_risk,
            "social_engagement": cog_social
        }

        # Write back to entity metadata
        entity.entity_metadata["cognitive_tensor"] = updated_cog

        logger.info(f"[SYNC] TTM→Cog for {entity.entity_id}: "
                   f"valence={cog_valence:.3f}, arousal={cog_arousal:.3f}, energy={cog_energy:.1f}")

        return CognitiveTensor(**updated_cog)

    except Exception as e:
        logger.warning(f"[SYNC] Failed to sync TTM→Cog for {entity.entity_id}: {e}")
        return None


def _sync_cognitive_to_ttm(
    entity: Entity,
    cognitive: 'CognitiveTensor',
    store: Optional['GraphStore'] = None
) -> bool:
    """
    Sync CognitiveTensor values → TTMTensor context (backprop equivalent).

    This propagates runtime emotional state changes back to the tensor,
    enabling learning from dialog interactions. Without this, emotional
    updates during dialog are lost when the entity is reloaded.

    Called AFTER dialog synthesis emotional updates.

    Scale conversions (reverse of _sync_ttm_to_cognitive):
    - CognitiveTensor valence (-1 to 1) → TTMTensor valence (0-1): ttm = (cog + 1) / 2
    - CognitiveTensor energy (0-100) → TTMTensor energy (0-1): ttm = cog / 100
    - CognitiveTensor arousal (0-1) → TTMTensor arousal (0-1): same scale

    Args:
        entity: Entity with TTMTensor to sync to
        cognitive: CognitiveTensor with updated values
        store: Optional GraphStore for persistence

    Returns:
        True if sync successful, False otherwise
    """
    import json
    import base64
    import msgspec
    import numpy as np

    # Check if entity has a tensor to update
    if not entity.tensor:
        logger.debug(f"[SYNC] {entity.entity_id}: No TTMTensor to sync to")
        return False

    try:
        # Decode TTMTensor
        tensor_dict = json.loads(entity.tensor)
        context = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["context_vector"])))

        # Scale conversions (reverse)
        ttm_valence = (cognitive.emotional_valence + 1) / 2  # -1 to 1 → 0-1
        ttm_arousal = cognitive.emotional_arousal  # same scale
        ttm_energy = cognitive.energy_budget / 100  # 0-100 → 0-1
        ttm_confidence = cognitive.decision_confidence  # same scale
        ttm_patience = cognitive.patience_threshold / 100  # 0-100 → 0-1
        ttm_risk = cognitive.risk_tolerance  # same scale
        ttm_social = cognitive.social_engagement  # same scale

        # Clamp to valid ranges
        ttm_valence = max(0.0, min(1.0, ttm_valence))
        ttm_arousal = max(0.0, min(1.0, ttm_arousal))
        ttm_energy = max(0.0, min(1.0, ttm_energy))
        ttm_confidence = max(0.0, min(1.0, ttm_confidence))
        ttm_patience = max(0.0, min(1.0, ttm_patience))
        ttm_risk = max(0.0, min(1.0, ttm_risk))
        ttm_social = max(0.0, min(1.0, ttm_social))

        # Update context_vector
        # [0]=knowledge (don't touch), [1]=valence, [2]=arousal, [3]=energy, [4]=confidence, [5]=patience, [6]=risk, [7]=social
        context[1] = ttm_valence
        context[2] = ttm_arousal
        context[3] = ttm_energy
        context[4] = ttm_confidence
        context[5] = ttm_patience
        context[6] = ttm_risk
        context[7] = ttm_social

        # Re-encode tensor
        updated_tensor = {
            "context_vector": base64.b64encode(msgspec.msgpack.encode(context.tolist())).decode('utf-8'),
            "biology_vector": tensor_dict["biology_vector"],  # Preserve unchanged
            "behavior_vector": tensor_dict["behavior_vector"]  # Preserve unchanged
        }

        # Write back to entity
        entity.tensor = json.dumps(updated_tensor)

        # Persist if store provided
        if store:
            store.save_entity(entity)

        logger.info(f"[SYNC] Cog→TTM for {entity.entity_id}: "
                   f"valence={ttm_valence:.3f}, arousal={ttm_arousal:.3f}, energy={ttm_energy:.3f}")

        return True

    except Exception as e:
        logger.warning(f"[SYNC] Failed to sync Cog→TTM for {entity.entity_id}: {e}")
        return False


def _derive_speaking_style(personality_traits: List[str], archetype_id: str = "") -> Dict[str, str]:
    """
    Derive speaking style characteristics from personality traits.

    This enables voice differentiation in dialog synthesis by mapping
    personality traits to concrete speaking patterns.

    Args:
        personality_traits: List of personality trait strings
        archetype_id: Optional archetype identifier

    Returns:
        Dict with speaking style descriptors:
        - verbosity: terse/moderate/verbose
        - formality: casual/neutral/formal
        - tone: warm/neutral/cold/passionate
        - vocabulary: simple/technical/philosophical/business
        - speech_pattern: direct/elaborate/questioning/commanding
    """
    traits_lower = [t.lower() for t in personality_traits] if personality_traits else []

    # Default speaking style
    style = {
        "verbosity": "moderate",
        "formality": "neutral",
        "tone": "neutral",
        "vocabulary": "general",
        "speech_pattern": "direct"
    }

    # Verbosity mapping
    verbose_traits = ["intellectual", "philosophical", "verbose", "analytical", "academic", "professorial"]
    terse_traits = ["reserved", "stoic", "practical", "military", "laconic", "quiet"]
    if any(t in traits_lower for t in verbose_traits):
        style["verbosity"] = "verbose"
    elif any(t in traits_lower for t in terse_traits):
        style["verbosity"] = "terse"

    # Formality mapping
    formal_traits = ["aristocratic", "diplomatic", "refined", "proper", "dignified", "professional"]
    casual_traits = ["friendly", "casual", "folksy", "down-to-earth", "approachable", "relaxed"]
    if any(t in traits_lower for t in formal_traits):
        style["formality"] = "formal"
    elif any(t in traits_lower for t in casual_traits):
        style["formality"] = "casual"

    # Tone mapping
    warm_traits = ["warm", "empathetic", "caring", "nurturing", "kind", "compassionate"]
    cold_traits = ["cold", "calculating", "detached", "aloof", "distant", "clinical"]
    passionate_traits = ["passionate", "fiery", "intense", "zealous", "fervent", "emotional"]
    if any(t in traits_lower for t in warm_traits):
        style["tone"] = "warm"
    elif any(t in traits_lower for t in cold_traits):
        style["tone"] = "cold"
    elif any(t in traits_lower for t in passionate_traits):
        style["tone"] = "passionate"

    # Vocabulary mapping
    tech_traits = ["technical", "engineer", "scientific", "analytical", "data-driven"]
    philosophical_traits = ["philosophical", "intellectual", "academic", "scholarly", "contemplative"]
    business_traits = ["business", "executive", "strategic", "pragmatic", "results-oriented"]
    if any(t in traits_lower for t in tech_traits):
        style["vocabulary"] = "technical"
    elif any(t in traits_lower for t in philosophical_traits):
        style["vocabulary"] = "philosophical"
    elif any(t in traits_lower for t in business_traits):
        style["vocabulary"] = "business"

    # Speech pattern mapping
    questioning_traits = ["curious", "inquisitive", "socratic", "skeptical", "analytical"]
    commanding_traits = ["authoritative", "commanding", "decisive", "leadership", "dominant"]
    elaborate_traits = ["storyteller", "narrative", "elaborate", "descriptive", "creative"]
    if any(t in traits_lower for t in questioning_traits):
        style["speech_pattern"] = "questioning"
    elif any(t in traits_lower for t in commanding_traits):
        style["speech_pattern"] = "commanding"
    elif any(t in traits_lower for t in elaborate_traits):
        style["speech_pattern"] = "elaborate"

    # Archetype-based overrides
    archetype_lower = archetype_id.lower() if archetype_id else ""
    if "visionary" in archetype_lower or "dreamer" in archetype_lower:
        style["vocabulary"] = "philosophical"
        style["speech_pattern"] = "elaborate"
    elif "strategist" in archetype_lower or "analyst" in archetype_lower:
        style["vocabulary"] = "technical"
        style["verbosity"] = "moderate"
    elif "leader" in archetype_lower or "executive" in archetype_lower:
        style["speech_pattern"] = "commanding"
        style["formality"] = "formal"

    return style


def extract_knowledge_references(content: str) -> List[str]:
    """
    DEPRECATED: Naive capitalization-based extraction.

    This function is deprecated and should NOT be used. It produced garbage
    like "we'll", "thanks", "what" because it just grabbed capitalized words.

    Use workflows.knowledge_extraction.extract_knowledge_from_dialog() instead,
    which uses an LLM agent (M19) for intelligent semantic extraction.

    Kept for backward compatibility but returns empty list.

    Args:
        content: Dialog turn content to analyze

    Returns:
        Empty list (deprecated - use LLM extraction instead)
    """
    logger.warning(
        "[DEPRECATED] extract_knowledge_references() is deprecated. "
        "Use workflows.knowledge_extraction.extract_knowledge_from_dialog() instead."
    )
    return []  # Return empty - extraction now handled by M19 agent


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
    store: Optional['GraphStore'] = None,
    run_id: Optional[str] = None  # January 2026: Added for dialog persistence/convergence
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
    coupled_cognitives = {}  # Track coupled cognitive states for emotional persistence
    for entity in entities:
        # PRETRAINING SYNC: Copy TTMTensor → CognitiveTensor before dialog
        # This ensures trained tensor values are used, not default 0.0 values
        synced_cognitive = _sync_ttm_to_cognitive(entity)
        if synced_cognitive:
            print(f"    [SYNC] TTM→Cog for {entity.entity_id}: "
                  f"valence={synced_cognitive.emotional_valence:.3f}, "
                  f"arousal={synced_cognitive.emotional_arousal:.3f}")

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

        # Store coupled cognitive for emotional state persistence later
        coupled_cognitives[entity.entity_id] = coupled_cognitive

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

            # Speaking Style (derived from personality for voice differentiation)
            "speaking_style": _derive_speaking_style(
                entity.entity_metadata.get("personality_traits", []),
                entity.entity_metadata.get("archetype_id", "")
            ),

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

6. VOICE DIFFERENTIATION (CRITICAL - Each character MUST sound distinct):
   Use the speaking_style field for each participant:
   - verbosity: terse = short, clipped sentences | verbose = elaborate, detailed explanations
   - formality: casual = contractions, informal words | formal = proper grammar, honorifics
   - tone: warm = encouraging, supportive | cold = detached, clinical | passionate = emphatic, emotional
   - vocabulary: technical = jargon, data | philosophical = abstract, conceptual | business = metrics, strategy
   - speech_pattern: questioning = asks clarifying questions | commanding = directives, decisions | elaborate = storytelling

   EXAMPLES of distinct voices:
   - Terse + formal + cold: "The numbers don't support this. We proceed as planned."
   - Verbose + casual + warm: "Look, I really think we've got something special here, and if we just take a moment to consider all the possibilities..."
   - Commanding + business + passionate: "This is our moment! I need everyone focused on the Q4 targets. No excuses."

7. SPECIFICITY IN DECISIONS (CRITICAL - Make dialog concrete, not generic):
   When characters discuss decisions, plans, or situations, they MUST use SPECIFIC details:
   - NUMBERS: "$2.3M runway", "47 customers", "18-month timeline", "3 board seats"
   - NAMES: Specific people, companies, products, locations (make them up if needed)
   - TRADE-OFFS: Explicitly state what was sacrificed for what was gained
   - ALTERNATIVES: Reference other options considered and why they were rejected
   - CONSEQUENCES: Concrete outcomes, not vague "it worked out"

   BAD (generic): "We need more funding to grow."
   GOOD (specific): "We need $4M by March to hit 50 enterprise customers before Acme launches their competing product."

   BAD (generic): "The partnership didn't work out."
   GOOD (specific): "DataCorp backed out when they saw our 23% churn rate. We've got 60 days to fix retention or lose the Sequoia term sheet."

Generate 8-12 dialog turns showing realistic interaction given these constraints.
"""

    # Generate dialog with structured output
    # January 2026: Increased from 2000 to 6000 tokens to prevent dialog truncation
    # 8-12 turn dialogs need ~4000-5000 tokens; 2000 was causing JSON parsing failures
    dialog_data = llm.generate_dialog(
        prompt=prompt,
        max_tokens=6000
    )

    # Create ExposureEvents using M19 Knowledge Extraction Agent (LLM-based)
    exposure_events_created = 0
    if store:
        print(f"    [M11→M19] Extracting knowledge from {len(dialog_data.turns)} dialog turns using LLM agent")

        # Import M19 knowledge extraction
        from workflows.knowledge_extraction import (
            extract_knowledge_from_dialog,
            create_exposure_events_from_knowledge
        )

        # Prepare dialog turns as dicts for extraction
        turns_for_extraction = []
        for turn in dialog_data.turns:
            turn_dict = turn.dict() if hasattr(turn, 'dict') else turn.model_dump()
            turns_for_extraction.append(turn_dict)

        # Run LLM-based knowledge extraction (M19)
        extraction_result = extract_knowledge_from_dialog(
            dialog_turns=turns_for_extraction,
            entities=entities,
            timepoint=timepoint,
            llm=llm,
            store=store,
            dialog_id=f"dialog_{timepoint.timepoint_id}"
        )

        # Create exposure events from extracted knowledge (M19→M3)
        exposure_events_created = create_exposure_events_from_knowledge(
            extraction_result=extraction_result,
            timepoint=timepoint,
            store=store
        )

        # Log extraction summary
        if extraction_result.items:
            print(f"    [M19→M3] Extracted {len(extraction_result.items)} knowledge items ({extraction_result.items_per_turn:.2f}/turn)")
            for item in extraction_result.items[:3]:  # Show first 3
                print(f"      - [{item.category}] {item.content[:60]}...")
        else:
            print(f"    [M19] No meaningful knowledge extracted (normal for casual dialog)")

        print(f"    [M19→M3] Created {exposure_events_created} exposure events from knowledge extraction")

    # Convert dialog turns to JSON-serializable format (handle datetime objects)
    turns_data = []
    for turn in dialog_data.turns:
        turn_dict = turn.dict() if hasattr(turn, 'dict') else turn.model_dump()
        # Convert any datetime objects to ISO strings
        if 'timestamp' in turn_dict and hasattr(turn_dict['timestamp'], 'isoformat'):
            turn_dict['timestamp'] = turn_dict['timestamp'].isoformat()
        turns_data.append(turn_dict)

    # Persist emotional state updates (fixes emotional_valence/arousal staying at 0.0)
    if coupled_cognitives:
        emotional_updates = _persist_emotional_state_updates(
            entities=entities,
            dialog_turns=turns_data,
            coupled_cognitives=coupled_cognitives,
            store=store
        )
        if emotional_updates > 0:
            print(f"    [M11] Updated emotional state for {emotional_updates} entities after dialog")

        # BACKPROP SYNC: Copy CognitiveTensor → TTMTensor after dialog
        # This enables learning from dialog interactions - emotional changes persist to tensor
        from schemas import CognitiveTensor
        backprop_count = 0
        for entity in entities:
            # Get the updated cognitive state from entity metadata
            updated_cog_data = entity.entity_metadata.get("cognitive_tensor", {})
            if updated_cog_data:
                try:
                    updated_cognitive = CognitiveTensor(**updated_cog_data)
                    if _sync_cognitive_to_ttm(entity, updated_cognitive, store=store):
                        backprop_count += 1
                except Exception as e:
                    logger.warning(f"[SYNC] Failed backprop for {entity.entity_id}: {e}")

        if backprop_count > 0:
            print(f"    [SYNC] Backprop Cog→TTM for {backprop_count} entities (tensor learning)")

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
        information_transfer_count=len(dialog_data.information_exchanged),
        run_id=run_id  # January 2026: Link to simulation run for convergence analysis
    )
