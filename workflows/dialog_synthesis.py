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

        # Decode behavior_vector → personality_traits (last-chance fallback)
        # Only if entity still has no decoded traits at dialog time
        existing_source = entity.entity_metadata.get("personality_source", "")
        if existing_source not in ("template_entity_roster", "llm_population_decoded", "tensor_decoded"):
            behavior = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["behavior_vector"])))
            from tensor_initialization import decode_behavior_vector_to_traits
            decoded_traits = decode_behavior_vector_to_traits(behavior, entity.entity_metadata)
            if decoded_traits:
                entity.entity_metadata["personality_traits"] = decoded_traits
                entity.entity_metadata["personality_source"] = "sync_decoded"
                logger.info(f"[SYNC] Decoded behavior_vector → traits for {entity.entity_id}: {decoded_traits}")

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


def _infer_personality_from_role(role: str) -> List[str]:
    """
    Infer personality traits from a role description when explicit traits are absent.

    Three-tier fallback: explicit traits (caller checks first) -> role inference -> hardcoded default.

    Args:
        role: Role description text (e.g. "Flight Engineer. Conflict-averse personality.")

    Returns:
        List of 4-6 inferred personality trait strings.
    """
    if not role:
        return ["determined", "principled"]

    role_lower = role.lower()
    traits = []

    # Role keyword -> trait mappings
    ROLE_TRAIT_MAP = {
        # Technical roles
        "engineer": ["analytical", "technical", "precise"],
        "scientist": ["analytical", "data-driven", "intellectual"],
        "analyst": ["analytical", "data-driven", "reserved"],
        "researcher": ["intellectual", "curious", "precise"],
        # Leadership roles
        "director": ["commanding", "strategic", "results-oriented"],
        "commander": ["authoritative", "decisive", "leadership"],
        "captain": ["authoritative", "decisive", "leadership"],
        "manager": ["pragmatic", "strategic", "professional"],
        "executive": ["commanding", "business", "results-oriented"],
        "president": ["commanding", "diplomatic", "strategic"],
        # Personality descriptors in role text
        "conflict-averse": ["reserved", "cautious", "diplomatic"],
        "cautious": ["cautious", "reserved", "analytical"],
        "aggressive": ["intense", "commanding", "stubborn"],
        "diplomatic": ["diplomatic", "warm", "professional"],
        # Domain modifiers
        "military": ["stoic", "commanding", "laconic"],
        "medical": ["empathetic", "precise", "professional"],
        "political": ["diplomatic", "strategic", "calculating"],
        "financial": ["pragmatic", "business", "data-driven"],
    }

    for keyword, keyword_traits in ROLE_TRAIT_MAP.items():
        if keyword in role_lower:
            traits.extend(keyword_traits)

    # Deduplicate while preserving order
    seen = set()
    unique_traits = []
    for t in traits:
        if t not in seen:
            seen.add(t)
            unique_traits.append(t)

    if len(unique_traits) >= 3:
        return unique_traits[:6]

    # Hardcoded default fallback
    return ["determined", "principled"]


def _generate_voice_examples(speaking_style: Dict[str, str], character_id: str) -> List[str]:
    """
    Generate 2-3 few-shot example lines showing how a character with this
    specific speaking style combination should sound.

    These examples are injected prominently into the dialog prompt so the LLM
    has concrete models for each character's voice, rather than abstract JSON
    descriptors that get buried among other instructions.

    Args:
        speaking_style: Dict with verbosity, formality, tone, vocabulary, speech_pattern
        character_id: Character name for logging context

    Returns:
        List of 2-3 example dialog lines demonstrating the voice
    """
    verbosity = speaking_style.get("verbosity", "moderate")
    formality = speaking_style.get("formality", "neutral")
    tone = speaking_style.get("tone", "neutral")
    vocabulary = speaking_style.get("vocabulary", "general")
    speech_pattern = speaking_style.get("speech_pattern", "direct")

    # Build examples from the combination of style axes.
    # We use a lookup keyed on (verbosity, tone) as the primary axes,
    # then modulate by formality, vocabulary, and speech_pattern.

    # --- Base examples by verbosity x tone ---
    base_examples = {
        ("terse", "cold"): [
            "The data doesn't support that.",
            "Show me the numbers.",
            "Unacceptable. Next.",
        ],
        ("terse", "warm"): [
            "Hey, good work on this.",
            "I trust your call.",
            "Let's make it happen.",
        ],
        ("terse", "neutral"): [
            "Noted. Move on.",
            "What's the timeline?",
            "Fine. Proceed.",
        ],
        ("terse", "passionate"): [
            "This matters. Do it now.",
            "We can't afford to lose this!",
            "No more delays.",
        ],
        ("verbose", "cold"): [
            "If you examine the quarterly projections, you'll notice the variance exceeds acceptable thresholds by a considerable margin.",
            "I've reviewed every contingency. None of them address the fundamental structural problem.",
            "Let me be precise: the current trajectory leads to a 40% shortfall, and sentiment won't change that.",
        ],
        ("verbose", "warm"): [
            "I really think if we take the time to look at this from everyone's perspective, we'll find something that works for the whole team.",
            "You know, what I love about this approach is how it brings together so many different ideas we've been kicking around.",
            "Let me share something that might help — I went through a similar situation a few years back.",
        ],
        ("verbose", "neutral"): [
            "There are several factors to consider here, including the timeline, the resource allocation, and the stakeholder expectations.",
            "Let me walk through the analysis step by step so we're all on the same page.",
            "The situation is more nuanced than it appears at first glance, and I think it warrants a thorough discussion.",
        ],
        ("verbose", "passionate"): [
            "This is exactly the kind of opportunity that comes once in a generation, and we would be fools to let it slip through our fingers!",
            "I've spent months building this case, and every single data point confirms what I've been saying from the start.",
            "We are standing at a crossroads, and the choice we make today will define everything that follows.",
        ],
        ("moderate", "cold"): [
            "The proposal has structural flaws. I've outlined them in the memo.",
            "That's a risk we shouldn't take. The downside is asymmetric.",
            "I'll need the revised figures by Thursday. No extensions.",
        ],
        ("moderate", "warm"): [
            "I think we're onto something good here. Let's keep pushing.",
            "That's a really thoughtful point — it changes how I see the timeline.",
            "I appreciate everyone's effort. Let's figure this out together.",
        ],
        ("moderate", "neutral"): [
            "We should evaluate both options before committing.",
            "The report raises some questions we need to address.",
            "Let's table that for now and revisit after the review.",
        ],
        ("moderate", "passionate"): [
            "This is our shot. We need to go all in.",
            "I believe in this team. We can make this work.",
            "The competition isn't sleeping — neither should we.",
        ],
    }

    examples = list(base_examples.get(
        (verbosity, tone),
        base_examples.get((verbosity, "neutral"), [
            "We should discuss this further.",
            "What are the next steps?",
            "Let me think about that.",
        ])
    ))

    # --- Modulate by formality ---
    if formality == "formal" and verbosity != "terse":
        # Replace contractions and add formal markers
        examples = [_formalize_example(ex) for ex in examples]
    elif formality == "casual":
        # Add casual markers
        examples = [_casualize_example(ex) for ex in examples]

    # --- Modulate by vocabulary ---
    vocab_additions = {
        "technical": "Frame responses using technical terminology, metrics, and data references.",
        "philosophical": "Frame responses using abstract reasoning, analogies, and first-principles thinking.",
        "business": "Frame responses using business language: ROI, runway, market position, deliverables.",
        "general": "",
    }

    # --- Modulate by speech_pattern: swap one example ---
    pattern_example = {
        "questioning": "But have we stress-tested that assumption?",
        "commanding": "Here's what we're doing. No debate.",
        "elaborate": "It reminds me of what happened at the Henderson project — same dynamics, different stakes.",
        "direct": "",
    }

    swap = pattern_example.get(speech_pattern, "")
    if swap and len(examples) >= 3:
        examples[2] = swap

    return examples[:3]


def _formalize_example(text: str) -> str:
    """Apply light formalization to an example line."""
    replacements = [
        ("we're", "we are"), ("I've", "I have"), ("don't", "do not"),
        ("can't", "cannot"), ("won't", "will not"), ("Let's", "Let us"),
        ("let's", "let us"), ("I'm", "I am"), ("it's", "it is"),
        ("isn't", "is not"), ("wasn't", "was not"), ("shouldn't", "should not"),
        ("wouldn't", "would not"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _casualize_example(text: str) -> str:
    """Apply light casualization to an example line."""
    replacements = [
        ("I believe", "I think"), ("We should", "We gotta"),
        ("Let us", "Let's"), ("do not", "don't"),
        ("cannot", "can't"), ("will not", "won't"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    # Add casual opener occasionally
    if not text.startswith(("Look", "Hey", "Yeah", "So")):
        # Only for moderate/verbose
        pass
    return text


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


def _filter_dialog_participants(
    entities: List[Entity],
    animism_level: int = 0
) -> tuple:
    """
    Filter entities for dialog participation based on animism_level.

    Entity type → minimum animism_level threshold:
      human: 0 (always eligible)
      animal: 1
      building/object/environment: 2
      abstract/concept: 3
      Other: 4+

    Non-human entities that DO participate get a _dialog_speaking_mode
    injected into their metadata for prompt use.

    Args:
        entities: All candidate entities
        animism_level: Animism threshold from config (0=humans only)

    Returns:
        Tuple of (included_entities, excluded_entity_ids)
    """
    ANIMISM_THRESHOLDS = {
        "human": 0, "person": 0, "character": 0,
        "animal": 1, "creature": 1,
        "building": 2, "object": 2, "environment": 2,
        "location": 2, "vehicle": 2,
        "abstract": 3, "concept": 3, "force": 3,
    }

    SPEAKING_MODES = {
        "animal": "behavioral narration (third-person actions and reactions, no human grammar)",
        "creature": "behavioral narration (third-person actions and reactions, no human grammar)",
        "building": "environmental narration (sensory descriptions felt by occupants)",
        "object": "environmental narration (sensory descriptions felt by occupants)",
        "environment": "environmental narration (sensory descriptions felt by occupants)",
        "location": "environmental narration (sensory descriptions felt by occupants)",
        "vehicle": "environmental narration (sensory descriptions felt by occupants)",
        "abstract": "collective consciousness (emergent sentiment, atmospheric shift)",
        "concept": "collective consciousness (emergent sentiment, atmospheric shift)",
        "force": "collective consciousness (emergent sentiment, atmospheric shift)",
    }

    included = []
    excluded_ids = []

    for entity in entities:
        etype = entity.entity_type.lower() if entity.entity_type else "human"
        threshold = ANIMISM_THRESHOLDS.get(etype, 4)

        if animism_level >= threshold:
            # Inject speaking mode for non-human entities
            if threshold > 0:
                entity.entity_metadata["_dialog_speaking_mode"] = SPEAKING_MODES.get(
                    etype, "narrated presence (described, not speaking)"
                )
            included.append(entity)
        else:
            excluded_ids.append(entity.entity_id)
            logger.info(f"Excluding {entity.entity_id} ({etype}) from dialog: "
                       f"animism_level={animism_level} < threshold={threshold}")

    return included, excluded_ids


def _derive_dialog_params_from_persona(
    speaking_style: Dict[str, str],
    emotional_state: Dict[str, float],
    energy: float,
    entity_type: str = "human"
) -> Dict[str, str]:
    """
    Map emotion x personality → dialog behavior parameters.

    Returns modulation hints for the prompt to differentiate character voices
    based on their current emotional and physical state.
    """
    valence = emotional_state.get("valence", 0.0)
    arousal = emotional_state.get("arousal", 0.3)

    params = {}

    # High arousal + negative valence → short, intense, interrupting
    if arousal > 0.7 and valence < -0.2:
        params["turn_length"] = "short, clipped"
        params["interruption"] = "frequently interrupts others"
        params["focus"] = "fixated on the immediate problem"
    # High arousal + positive valence → expansive, assertive
    elif arousal > 0.7 and valence > 0.2:
        params["turn_length"] = "longer, expansive"
        params["interruption"] = "speaks confidently over others"
        params["focus"] = "forward-looking, proposing solutions"
    # Low energy → trailing off, disengaged
    elif energy < 30:
        params["turn_length"] = "short, trailing off"
        params["interruption"] = "rarely initiates, responds when addressed"
        params["focus"] = "distracted, low engagement"
    # Low arousal + negative valence → withdrawn, pessimistic
    elif arousal < 0.3 and valence < -0.2:
        params["turn_length"] = "moderate but guarded"
        params["interruption"] = "waits to speak, hesitant"
        params["focus"] = "pessimistic, raising concerns"
    # Balanced/neutral
    else:
        params["turn_length"] = "moderate"
        params["interruption"] = "normal conversational flow"
        params["focus"] = "engaged, balanced"

    # Confidence modulation
    confidence = speaking_style.get("speech_pattern", "direct")
    if confidence == "commanding" and valence > 0:
        params["assertion"] = "makes decisive statements"
    elif confidence == "questioning":
        params["assertion"] = "probes with questions before committing"

    return params


def _compute_dialog_structure(participants_context: List[Dict]) -> Dict[str, any]:
    """
    Compute dynamic dialog structure parameters based on participant state.

    Replaces static "8-12 dialog turns" with context-sensitive parameters.

    Args:
        participants_context: List of participant context dicts with emotional_state

    Returns:
        Dict with turn_count_range, silent_allowed, ending_mode, high_conflict
    """
    n = len(participants_context)

    # Compute average emotional state
    avg_arousal = 0.0
    avg_valence = 0.0
    for ctx in participants_context:
        emo = ctx.get("emotional_state", {})
        avg_arousal += emo.get("arousal", 0.3)
        avg_valence += emo.get("valence", 0.0)
    if n > 0:
        avg_arousal /= n
        avg_valence /= n

    high_conflict = avg_arousal > 0.6 and avg_valence < -0.1

    # Turn count: more participants and higher conflict = more turns
    base_turns = 6 + n
    if high_conflict:
        base_turns += 3
    min_turns = max(6, base_turns - 2)
    max_turns = min(16, base_turns + 3)

    # Silent allowed: with >3 participants, some can be observers
    silent_allowed = n > 3

    # Ending mode based on emotional state
    if avg_valence < -0.3:
        ending_mode = "unresolved_tension"
    elif avg_arousal > 0.7:
        ending_mode = "interrupted"
    else:
        ending_mode = "natural_pause"

    return {
        "turn_count_range": (min_turns, max_turns),
        "silent_allowed": silent_allowed,
        "ending_mode": ending_mode,
        "high_conflict": high_conflict,
    }


def _compute_temporal_mood(
    timepoint: 'Timepoint',
    timeline: List[Dict],
    participant_anxiety: Optional[Dict[str, float]] = None
) -> str:
    """
    Map timeline position to emotional register for dialog tone.

    Args:
        timepoint: Current timepoint being generated
        timeline: Full list of timepoint dicts for position context
        participant_anxiety: Optional dict of entity_id → anxiety_level from prospection

    Returns:
        String instruction block describing the temporal mood register.
    """
    event_desc = (timepoint.event_description or "").lower()
    n_timepoints = len(timeline) if timeline else 1
    # Determine position as fraction through the timeline
    position = 0.5
    if timeline and n_timepoints > 1:
        for i, tp in enumerate(timeline):
            tp_desc = tp.get("event_description", "")
            if tp_desc == timepoint.event_description:
                position = i / (n_timepoints - 1)
                break

    # Disaster keywords
    disaster_words = ["failure", "explosion", "breach", "collapse", "death",
                      "emergency", "critical", "catastroph", "disaster", "crisis"]
    is_disaster = any(w in event_desc for w in disaster_words)

    if is_disaster:
        mood = ("CRISIS. This is NOT a calm meeting. Characters shout, blame, panic. "
                "Short urgent sentences. People talk over each other. "
                "Someone may refuse to speak. Raw emotion overrides professionalism.")
    elif position < 0.25:
        mood = ("EARLY STAGE. Professional optimism with seeds of doubt. "
                "Characters are polite but small fractures are visible. "
                "One character may voice a concern that others dismiss.")
    elif position < 0.6:
        mood = ("TENSION BUILDING. 'I told you so' energy. Trust fraying between characters. "
                "References to earlier decisions that now look wrong. "
                "Politeness is strained. Someone is holding back anger.")
    else:
        mood = ("LATE STAGE. Heavy. Characters reference earlier decisions with regret or defensiveness. "
                "Relationships are damaged. Some characters are resigned, others are digging in. "
                "The weight of consequences is felt in every exchange.")

    # Apply anxiety modifier from prospection data
    if participant_anxiety:
        anxiety_values = list(participant_anxiety.values())
        avg_anxiety = sum(anxiety_values) / len(anxiety_values) if anxiety_values else 0.0
        if avg_anxiety > 0.7:
            mood += (" CRISIS-LEVEL ANXIETY. Characters are visibly stressed — voices crack, "
                     "hands shake, decisions feel desperate. Fear of failure pervades every exchange.")
        elif avg_anxiety > 0.4:
            mood += (" UNDERLYING TENSION. Characters carry unspoken worries. "
                     "Pauses are loaded. Someone deflects when pressed about the future.")

    return mood


def _check_voice_distinctiveness(turns: List[Dict]) -> float:
    """
    Multi-dimensional voice distinctiveness metric across 4 axes (equal weight):
    1. Hedging opener ratio (banned opener detection)
    2. Per-speaker sentence length variance
    3. Vocabulary overlap (Jaccard distance between speakers)
    4. Turn distribution uniformity (anti-round-robin)

    Args:
        turns: List of dialog turn dicts with 'speaker' and 'content' keys

    Returns:
        Distinctiveness score from 0.0 (identical voices) to 1.0 (fully distinct).
    """
    if not turns or len(turns) < 2:
        return 1.0

    HEDGING_PATTERNS = [
        "i understand", "that's a valid point", "i see your point",
        "i agree,", "i agree.", "you raise a good", "i appreciate your",
        "that's a fair", "i hear what you", "you make a good",
        "with all due respect", "i understand your concerns",
        "that's a great point", "you're right, but", "i take your point",
    ]

    total_turns = len(turns)

    # --- Axis 1: Hedging opener ratio ---
    hedging_turns = 0
    for turn in turns:
        content = turn.get("content", "").strip().lower()
        if any(content.startswith(pattern) for pattern in HEDGING_PATTERNS):
            hedging_turns += 1
    hedging_score = 1.0 - (hedging_turns / total_turns)

    # --- Axis 2: Per-speaker sentence length variance ---
    speaker_avg_lengths = {}
    for turn in turns:
        speaker = turn.get("speaker", "unknown")
        content = turn.get("content", "")
        words = content.split()
        speaker_avg_lengths.setdefault(speaker, []).append(len(words))

    if len(speaker_avg_lengths) >= 2:
        avg_per_speaker = [sum(lengths) / len(lengths) for lengths in speaker_avg_lengths.values()]
        length_spread = max(avg_per_speaker) - min(avg_per_speaker)
        # Score: spread of 8+ words apart = 1.0, 0 = 0.0
        length_score = min(1.0, length_spread / 8.0)
    else:
        length_score = 0.5

    # --- Axis 3: Vocabulary overlap (Jaccard distance) ---
    speaker_vocabs = {}
    for turn in turns:
        speaker = turn.get("speaker", "unknown")
        content = turn.get("content", "").lower()
        words = set(w.strip(".,!?;:'\"()") for w in content.split() if len(w) > 3)
        speaker_vocabs.setdefault(speaker, set()).update(words)

    if len(speaker_vocabs) >= 2:
        speakers = list(speaker_vocabs.keys())
        jaccard_distances = []
        for i in range(len(speakers)):
            for j in range(i + 1, len(speakers)):
                vocab_a = speaker_vocabs[speakers[i]]
                vocab_b = speaker_vocabs[speakers[j]]
                union = vocab_a | vocab_b
                intersection = vocab_a & vocab_b
                if union:
                    jaccard_distances.append(1.0 - len(intersection) / len(union))
                else:
                    jaccard_distances.append(0.5)
        vocab_score = sum(jaccard_distances) / len(jaccard_distances) if jaccard_distances else 0.5
    else:
        vocab_score = 0.5

    # --- Axis 4: Turn distribution uniformity (anti-round-robin) ---
    speaker_turn_counts = {}
    for turn in turns:
        speaker = turn.get("speaker", "unknown")
        speaker_turn_counts[speaker] = speaker_turn_counts.get(speaker, 0) + 1

    if len(speaker_turn_counts) >= 2:
        counts = list(speaker_turn_counts.values())
        # Check for round-robin: if all speakers have equal turns, score is low
        mean_count = sum(counts) / len(counts)
        variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
        cv = (variance ** 0.5) / mean_count if mean_count > 0 else 0
        # CV > 0.3 = good variation, CV = 0 = perfect round-robin
        distribution_score = min(1.0, cv / 0.3)
    else:
        distribution_score = 0.5

    # Equal weight across 4 axes
    distinctiveness = (hedging_score + length_score + vocab_score + distribution_score) / 4.0

    if distinctiveness < 0.5:
        logger.warning(
            f"[M11] Low voice distinctiveness: {distinctiveness:.2f} "
            f"(hedging={hedging_score:.2f}, length_spread={length_score:.2f}, "
            f"vocab={vocab_score:.2f}, distribution={distribution_score:.2f})"
        )
    else:
        logger.info(
            f"[M11] Voice distinctiveness: {distinctiveness:.2f} "
            f"(hedging={hedging_score:.2f}, length_spread={length_score:.2f}, "
            f"vocab={vocab_score:.2f}, distribution={distribution_score:.2f})"
        )

    return distinctiveness


def _evaluate_dialog_quality(turns: List[Dict]) -> Dict:
    """
    Post-generation quality evaluation for rejection sampling.

    Runs 5 quality checks and returns pass/fail with repair notes:
    1. Banned opener count (max 1 allowed)
    2. Round-robin pattern detection
    3. Turn length coefficient of variation (must be > 0.3)
    4. Consensus ratio (must be < 40%)
    5. Per-speaker sentence length spread (must be > 8 words apart)

    Args:
        turns: List of dialog turn dicts with 'speaker' and 'content' keys

    Returns:
        Dict with 'score' (0.0-1.0), 'passed' (bool), 'failures' (list of strings),
        'repair_notes' (string for prompt injection on retry)
    """
    if not turns or len(turns) < 2:
        return {"score": 1.0, "passed": True, "failures": [], "repair_notes": ""}

    BANNED_OPENERS = [
        "i agree,", "i agree.", "that's a valid point", "i understand your concerns",
        "i see your point", "you raise a good point", "that's a great point",
        "i appreciate your", "that's a fair", "i hear what you",
        "you make a good", "with all due respect", "you're right, but",
        "i take your point",
    ]

    CONSENSUS_PHRASES = [
        "i agree", "you're right", "that's true", "absolutely",
        "exactly", "good point", "fair enough", "i concur",
        "makes sense", "i think so too",
    ]

    failures = []
    checks_passed = 0
    total_checks = 5

    # --- Check 1: Banned opener count ---
    banned_count = 0
    for turn in turns:
        content = turn.get("content", "").strip().lower()
        if any(content.startswith(opener) for opener in BANNED_OPENERS):
            banned_count += 1
    if banned_count <= 1:
        checks_passed += 1
    else:
        failures.append(f"banned_openers:{banned_count}")

    # --- Check 2: Round-robin pattern detection ---
    speakers = [turn.get("speaker", "") for turn in turns]
    if len(speakers) >= 4:
        # Check if speakers repeat in exact same order
        unique_speakers = []
        for s in speakers:
            if s not in unique_speakers:
                unique_speakers.append(s)
        n_unique = len(unique_speakers)
        if n_unique >= 2:
            is_round_robin = True
            for i in range(len(speakers)):
                if speakers[i] != unique_speakers[i % n_unique]:
                    is_round_robin = False
                    break
            if not is_round_robin:
                checks_passed += 1
            else:
                failures.append("round_robin_pattern")
        else:
            checks_passed += 1
    else:
        checks_passed += 1

    # --- Check 3: Turn length coefficient of variation ---
    turn_lengths = [len(turn.get("content", "").split()) for turn in turns]
    if turn_lengths:
        mean_len = sum(turn_lengths) / len(turn_lengths)
        if mean_len > 0:
            variance = sum((l - mean_len) ** 2 for l in turn_lengths) / len(turn_lengths)
            cv = (variance ** 0.5) / mean_len
            if cv > 0.3:
                checks_passed += 1
            else:
                failures.append(f"low_turn_length_cv:{cv:.2f}")
        else:
            checks_passed += 1
    else:
        checks_passed += 1

    # --- Check 4: Consensus ratio ---
    consensus_count = 0
    for turn in turns:
        content = turn.get("content", "").strip().lower()
        if any(phrase in content for phrase in CONSENSUS_PHRASES):
            consensus_count += 1
    consensus_ratio = consensus_count / len(turns) if turns else 0
    if consensus_ratio < 0.4:
        checks_passed += 1
    else:
        failures.append(f"high_consensus:{consensus_ratio:.0%}")

    # --- Check 5: Per-speaker sentence length spread ---
    speaker_avg_lengths = {}
    for turn in turns:
        speaker = turn.get("speaker", "unknown")
        word_count = len(turn.get("content", "").split())
        speaker_avg_lengths.setdefault(speaker, []).append(word_count)

    if len(speaker_avg_lengths) >= 2:
        avgs = [sum(lengths) / len(lengths) for lengths in speaker_avg_lengths.values()]
        spread = max(avgs) - min(avgs)
        if spread > 8:
            checks_passed += 1
        else:
            failures.append(f"low_length_spread:{spread:.1f}")
    else:
        checks_passed += 1

    score = checks_passed / total_checks

    # Build repair notes for retry prompt
    repair_notes = ""
    if failures:
        repair_parts = []
        if any("banned_openers" in f for f in failures):
            repair_parts.append("REMOVE all hedging openers like 'I agree', 'That's a valid point'. Characters must respond with substance, not acknowledgment.")
        if "round_robin_pattern" in failures:
            repair_parts.append("BREAK the round-robin speaker order. Some characters speak multiple times in a row. Others stay silent for several turns.")
        if any("low_turn_length_cv" in f for f in failures):
            repair_parts.append("VARY turn lengths dramatically. Mix 5-word interruptions with 40-word monologues.")
        if any("high_consensus" in f for f in failures):
            repair_parts.append("REDUCE agreement. Characters must push back, disagree, or ignore each other's points instead of constantly agreeing.")
        if any("low_length_spread" in f for f in failures):
            repair_parts.append("DIFFERENTIATE speaking lengths between characters. The terse character uses 8-word sentences. The verbose character uses 25-word sentences.")
        repair_notes = "\n".join(repair_parts)

    passed = score >= 0.6 or len(failures) < 2

    return {
        "score": score,
        "passed": passed,
        "failures": failures,
        "repair_notes": repair_notes,
    }


@track_mechanism("M11", "dialog_synthesis")
def synthesize_dialog(
    entities: List[Entity],
    timepoint: 'Timepoint',
    timeline: List[Dict],
    llm: 'LLMClient',
    store: Optional['GraphStore'] = None,
    run_id: Optional[str] = None,
    animism_level: int = 0,
    prior_dialog_beats: Optional[List[str]] = None,
    qse_state: Optional[Dict] = None,
    voice_mixer: Optional['VoiceMixer'] = None,
    # NEW: Per-turn dialog generation kwargs (all optional, backward-compatible)
    use_per_turn: bool = True,
    steering_model: Optional[str] = None,
    character_model: Optional[str] = None,
    quality_gate_model: Optional[str] = None,
    run_quality_per_turn: bool = False,
    adprs_envelopes: Optional[Dict[str, 'ADPRSEnvelope']] = None,
) -> Dialog:
    """Generate conversation with full physical/emotional/temporal context.

    When use_per_turn=True (default), uses LangGraph-based per-character
    turn generation with independent LLM calls per character.

    When use_per_turn=False, falls through to existing single-call
    implementation for backward compatibility.
    """
    # Attach QSE state to function for prompt builder access
    synthesize_dialog._qse_state = qse_state

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

    # Filter entities by animism_level (exclude non-human types below threshold)
    entities, excluded_ids = _filter_dialog_participants(entities, animism_level)
    if excluded_ids:
        print(f"    [M11] Excluded {len(excluded_ids)} entities from dialog (animism_level={animism_level}): {', '.join(excluded_ids)}")

    # Apply VoiceMixer filtering (mute/solo)
    if voice_mixer:
        all_ids = [e.entity_id for e in entities]
        active_ids = voice_mixer.get_active_entity_ids(all_ids)
        mixer_excluded = [eid for eid in all_ids if eid not in active_ids]
        if mixer_excluded:
            entities = [e for e in entities if e.entity_id in active_ids]
            print(f"    [M11] VoiceMixer excluded {len(mixer_excluded)} entities: {', '.join(mixer_excluded)}")

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

        # Retrieve ProspectiveState (M15 → M11 connection)
        prospection_context = None
        if entity.entity_metadata.get("has_prospection") and store:
            try:
                prospective_states = store.get_prospective_states_for_entity(entity.entity_id)
                if prospective_states:
                    ps = prospective_states[0]  # Most recent
                    # Parse expectations (stored as JSON string)
                    expectations = []
                    if ps.expectations:
                        if isinstance(ps.expectations, str):
                            try:
                                expectations = json.loads(ps.expectations)
                            except (json.JSONDecodeError, TypeError):
                                expectations = [ps.expectations]
                        elif isinstance(ps.expectations, list):
                            expectations = ps.expectations

                    # Parse contingency_plans
                    contingency_plans = {}
                    if ps.contingency_plans:
                        if isinstance(ps.contingency_plans, str):
                            try:
                                contingency_plans = json.loads(ps.contingency_plans)
                            except (json.JSONDecodeError, TypeError):
                                contingency_plans = {}
                        elif isinstance(ps.contingency_plans, dict):
                            contingency_plans = ps.contingency_plans

                    prospection_context = {
                        "expectations": expectations,
                        "anxiety_level": ps.anxiety_level,
                        "forecast_confidence": ps.forecast_confidence,
                        "contingency_plans": contingency_plans,
                    }
                    logger.info(f"[M15→M11] Loaded prospection for {entity.entity_id}: "
                               f"anxiety={ps.anxiety_level:.2f}, expectations={len(expectations)}")
            except Exception as e:
                logger.warning(f"[M15→M11] Failed to load prospection for {entity.entity_id}: {e}")

        participant_ctx = {
            "id": entity.entity_id,

            # Knowledge & Beliefs - now includes exposure events from M3
            "knowledge": knowledge_from_exposures,
            "beliefs": coupled_cognitive.decision_confidence,  # Using confidence as belief proxy

            # Personality & Goals (three-tier: explicit -> role inference -> default)
            "personality_traits": (
                entity.entity_metadata.get("personality_traits")
                or _infer_personality_from_role(entity.entity_metadata.get("role", ""))
            ),
            "current_goals": entity.entity_metadata.get("current_goals", ["serve_country"]),

            # Voice differentiation data (from template roster or LLM-generated)
            "voice_guide": entity.entity_metadata.get("voice_guide"),
            "speech_examples": entity.entity_metadata.get("speech_examples"),
            "voice_gain": voice_mixer.get_entity_weight(entity.entity_id) if voice_mixer else 1.0,

            # Speaking Style (derived from personality for voice differentiation)
            "speaking_style": _derive_speaking_style(
                entity.entity_metadata.get("personality_traits")
                or _infer_personality_from_role(entity.entity_metadata.get("role", "")),
                entity.entity_metadata.get("archetype_id", "")
            ),

            # Dialog speaking mode for non-human entities
            "dialog_speaking_mode": entity.entity_metadata.get("_dialog_speaking_mode"),

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

        # Add prospection context if available (M15 → M11)
        if prospection_context:
            participant_ctx["prospection"] = prospection_context

        # Derive dialog behavior params from persona + emotional state
        participant_ctx["dialog_behavior"] = _derive_dialog_params_from_persona(
            speaking_style=participant_ctx["speaking_style"],
            emotional_state=participant_ctx["emotional_state"],
            energy=participant_ctx["energy_remaining"],
            entity_type=entity.entity_type or "human"
        )

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

    # =====================================================================
    # PER-TURN DIALOG GENERATION (LangGraph-based)
    # =====================================================================
    if use_per_turn:
        print(f"    [M11] Using per-turn dialog generation for {len(entities)} entities")

        from synth.params2persona import compute_persona_params
        from workflows.dialog_context import build_fourth_wall_context, FourthWallContext
        from workflows.dialog_steering import run_dialog_graph

        # Build FourthWallContext and PersonaParams for each entity
        fourth_wall_contexts = {}
        persona_params = {}
        dialog_structure = _compute_dialog_structure(participants_context)
        min_turns, max_turns_val = dialog_structure["turn_count_range"]

        for entity in entities:
            if entity.entity_id not in coupled_cognitives:
                continue

            coupled_cog = coupled_cognitives[entity.entity_id]

            # Get physical tensor
            physical_data = entity.entity_metadata.get("physical_tensor", {})
            physical = None
            if physical_data and 'age' in physical_data:
                try:
                    from schemas import PhysicalTensor
                    physical = PhysicalTensor(**physical_data)
                except Exception:
                    continue
            else:
                continue

            # Get ADPRS envelope if available
            entity_envelope = None
            if adprs_envelopes:
                entity_envelope = adprs_envelopes.get(entity.entity_id)

            # Get proception state if available
            proception_state = None
            if entity.entity_metadata.get("has_prospection") and store:
                try:
                    ps_list = store.get_prospective_states_for_entity(entity.entity_id)
                    if ps_list:
                        proception_state = ps_list[0]
                except Exception:
                    pass

            # Build fourth wall context
            ctx = build_fourth_wall_context(
                entity=entity,
                coupled_cognitive=coupled_cog,
                physical=physical,
                timepoint=timepoint,
                timeline=timeline,
                other_entities=[e for e in entities if e.entity_id != entity.entity_id],
                store=store,
                proception_state=proception_state,
                adprs_envelope=entity_envelope,
                knowledge_limit=20,
            )

            # Compute persona params for initial turn
            params = compute_persona_params(
                entity=entity,
                cognitive=coupled_cog,
                turn_position=0,
                max_turns=max_turns_val,
                adprs_envelope=entity_envelope,
                evaluation_time=timepoint.timestamp if hasattr(timepoint.timestamp, 'tzinfo') else None,
            )
            ctx.persona_params = params

            fourth_wall_contexts[entity.entity_id] = ctx
            persona_params[entity.entity_id] = params

        # Build narrative goals from participant context
        narrative_goals = []
        for ctx in participants_context:
            goals = ctx.get("current_goals", [])
            if goals:
                narrative_goals.extend(goals[:2])

        # Build proception states dict for steering
        proception_states_dict = {}
        for ctx in participants_context:
            prosp = ctx.get("prospection")
            if prosp:
                proception_states_dict[ctx["id"]] = prosp

        # Build initial DialogState
        from schemas import DialogState

        initial_state: DialogState = {
            "turns": [],
            "active_speakers": [e.entity_id for e in entities if e.entity_id in fourth_wall_contexts],
            "fourth_wall_contexts": fourth_wall_contexts,
            "persona_params": persona_params,
            "current_speaker": None,
            "narrative_goals": narrative_goals[:6],
            "narrative_progress": {g: False for g in narrative_goals[:6]},
            "mood_register": "neutral",
            "proception_states": proception_states_dict,
            "suppressed_impulses": {},
            "withheld_knowledge": {},
            "turn_count": 0,
            "max_turns": max_turns_val,
            "dialog_structure": dialog_structure,
            "quality_failures": [],
            "steering_model": steering_model,
            "character_model": character_model,
            "quality_gate_model": quality_gate_model,
            "run_quality_per_turn": run_quality_per_turn,
            "timepoint_id": timepoint.timepoint_id,
            "run_id": run_id,
            "llm": llm,
            "store": store,
        }

        # Run dialog graph
        final_state = run_dialog_graph(initial_state)

        # Extract turns from final state
        turns_data = final_state.get("turns", [])

        # Ensure turns have required fields
        for turn in turns_data:
            if "timestamp" not in turn:
                turn["timestamp"] = datetime.utcnow().isoformat()
            if "confidence" not in turn:
                turn["confidence"] = 0.9

        print(f"    [M11] Per-turn dialog generated: {len(turns_data)} turns")

        # Run quality check on per-turn output
        quality = _evaluate_dialog_quality(turns_data)
        print(f"    [M11] Dialog quality check: score={quality['score']:.2f}, "
              f"passed={quality['passed']}, failures={quality.get('failures', [])}")

        # Check voice distinctiveness
        if turns_data:
            voice_score = _check_voice_distinctiveness(turns_data)
            print(f"    [M11] Voice distinctiveness score: {voice_score:.2f}")

        # Post-dialog proception for each participant
        from prospection_triggers import trigger_post_dialog_proception

        # Build preliminary dialog object for proception
        dialog_obj = Dialog(
            dialog_id=f"dialog_{timepoint.timepoint_id}_{'_'.join([e.entity_id for e in entities])}",
            timepoint_id=timepoint.timepoint_id,
            participants=json.dumps([e.entity_id for e in entities]),
            turns=json.dumps(turns_data),
            context_used=json.dumps({
                "per_turn_generation": True,
                "physical_states_applied": True,
                "emotional_states_applied": True,
                "body_mind_coupling_applied": True,
            }),
            duration_seconds=len(turns_data) * 10,
            information_transfer_count=len(turns_data),
            run_id=run_id,
        )

        for entity in entities:
            if entity.entity_id in fourth_wall_contexts:
                suppressed = final_state.get("suppressed_impulses", {}).get(entity.entity_id, [])
                withheld = final_state.get("withheld_knowledge", {}).get(entity.entity_id, [])
                trigger_post_dialog_proception(
                    entity=entity,
                    dialog=dialog_obj,
                    timepoint=timepoint,
                    llm=llm,
                    store=store,
                    suppressed_impulses=[{"impulse": s, "context": dialog_obj.dialog_id, "suppressed_by": "steering"} for s in suppressed] if suppressed else None,
                    withheld_knowledge=withheld if withheld else None,
                )

        # Create ExposureEvents using M19 Knowledge Extraction Agent (LLM-based)
        exposure_events_created = 0
        if store and turns_data:
            try:
                from workflows.knowledge_extraction import (
                    extract_knowledge_from_dialog,
                    create_exposure_events_from_knowledge,
                )

                extraction_result = extract_knowledge_from_dialog(
                    dialog_turns=turns_data,
                    entities=entities,
                    timepoint=timepoint,
                    llm=llm,
                    store=store,
                    dialog_id=dialog_obj.dialog_id,
                )

                exposure_events_created = create_exposure_events_from_knowledge(
                    extraction_result=extraction_result,
                    timepoint=timepoint,
                    store=store,
                )
                print(f"    [M19→M3] Created {exposure_events_created} exposure events")
            except Exception as e:
                logger.warning(f"[M19] Knowledge extraction failed: {e}")

        # Persist emotional state updates
        if coupled_cognitives:
            emotional_updates = _persist_emotional_state_updates(
                entities=entities,
                dialog_turns=turns_data,
                coupled_cognitives=coupled_cognitives,
                store=store,
            )
            if emotional_updates > 0:
                print(f"    [M11] Updated emotional state for {emotional_updates} entities")

            # STATE SYNC: CognitiveTensor → TTMTensor
            from schemas import CognitiveTensor
            sync_count = 0
            for entity in entities:
                updated_cog_data = entity.entity_metadata.get("cognitive_tensor", {})
                if updated_cog_data:
                    try:
                        updated_cognitive = CognitiveTensor(**updated_cog_data)
                        if _sync_cognitive_to_ttm(entity, updated_cognitive, store=store):
                            sync_count += 1
                    except Exception as e:
                        logger.warning(f"[SYNC] Failed Cog→TTM sync for {entity.entity_id}: {e}")
            if sync_count > 0:
                print(f"    [SYNC] Cog→TTM for {sync_count} entities")

        return dialog_obj

    # =====================================================================
    # LEGACY SINGLE-CALL DIALOG GENERATION (use_per_turn=False)
    # =====================================================================

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

    # Build entity name list for prompt anchoring (prevents hallucinating other characters)
    entity_names = [ctx["id"] for ctx in participants_context]
    entity_name_list = ", ".join(entity_names)

    # Build character-specific voice example blocks (promoted out of JSON)
    voice_example_blocks = []
    for ctx in participants_context:
        char_id = ctx["id"]
        style = ctx.get("speaking_style", {})
        voice_guide = ctx.get("voice_guide")
        speech_examples = ctx.get("speech_examples")

        # Use per-character speech_examples if available, else fall back to style-grid
        if speech_examples:
            examples = speech_examples[:3]
        else:
            examples = _generate_voice_examples(style, char_id)

        style_summary = f'{style.get("verbosity", "moderate")} / {style.get("formality", "neutral")} / {style.get("tone", "neutral")} / {style.get("vocabulary", "general")} / {style.get("speech_pattern", "direct")}'
        example_lines = "\n".join(f'      "{ex}"' for ex in examples)

        # Build voice constraint block from voice_guide if available
        constraint_lines = ""
        if voice_guide:
            constraints = []
            if voice_guide.get("sentence_length"):
                constraints.append(f"Sentence length: {voice_guide['sentence_length']}")
            if voice_guide.get("verbal_tics"):
                constraints.append(f"Often starts with: {', '.join(voice_guide['verbal_tics'])}")
            if voice_guide.get("never_says"):
                constraints.append(f"NEVER says: {', '.join(voice_guide['never_says'])}")
            if voice_guide.get("disagreement_style"):
                constraints.append(f"When disagreeing: {voice_guide['disagreement_style']}")
            if voice_guide.get("specificity_anchors"):
                constraints.append(f"Cites: {', '.join(voice_guide['specificity_anchors'])}")
            if constraints:
                constraint_lines = "\n      " + "\n      ".join(constraints)

        voice_example_blocks.append(
            f"   {char_id} [{style_summary}]:\n{example_lines}{constraint_lines}"
        )
    voice_examples_text = "\n\n".join(voice_example_blocks)

    # Compute dynamic dialog structure and temporal mood
    dialog_structure = _compute_dialog_structure(participants_context)

    # Build participant anxiety map from prospection contexts
    participant_anxiety = {}
    for ctx in participants_context:
        prosp = ctx.get("prospection")
        if prosp and "anxiety_level" in prosp:
            participant_anxiety[ctx["id"]] = prosp["anxiety_level"]

    temporal_mood = _compute_temporal_mood(timepoint, timeline, participant_anxiety=participant_anxiety or None)
    min_turns, max_turns = dialog_structure["turn_count_range"]

    # Build structure instructions
    structure_instructions = f"Generate {min_turns}-{max_turns} dialog turns."
    if dialog_structure["silent_allowed"]:
        structure_instructions += " Not every character must speak in every exchange — some may observe silently."
    if dialog_structure["high_conflict"]:
        structure_instructions += " This is a HIGH CONFLICT scene. Characters interrupt, talk over each other, and leave things unresolved."
    if dialog_structure["ending_mode"] == "unresolved_tension":
        structure_instructions += " END the dialog with unresolved tension — no neat wrap-up, no 'let's reconvene' closure."
    elif dialog_structure["ending_mode"] == "interrupted":
        structure_instructions += " END the dialog abruptly — an interruption, alarm, or someone walking out."

    # Build QSE resource state block if available
    qse_block = ""
    if hasattr(synthesize_dialog, '_qse_state') and synthesize_dialog._qse_state:
        qse_lines = []
        for resource_name, resource_data in synthesize_dialog._qse_state.items():
            value = resource_data.get("value", "?")
            unit = resource_data.get("unit", "")
            critical = resource_data.get("critical", False)
            marker = " *** CRITICAL ***" if critical else ""
            qse_lines.append(f"   - {resource_name}: {value} {unit}{marker}")
        if qse_lines:
            qse_block = "\n\nRESOURCE STATE (QUANTITATIVE — characters MUST cite these exact numbers):\n" + "\n".join(qse_lines)

    # Build CHARACTER EXPECTATIONS block from prospection data (M15 → M11)
    prospection_block = ""
    prospection_lines = []
    for ctx in participants_context:
        prosp = ctx.get("prospection")
        if prosp and prosp.get("expectations"):
            char_id = ctx["id"]
            expectations = prosp["expectations"]
            anxiety = prosp.get("anxiety_level", 0.0)
            confidence = prosp.get("forecast_confidence", 0.5)

            # Summarize expectations
            if isinstance(expectations, list):
                exp_summary = "; ".join(
                    str(e.get("description", e) if isinstance(e, dict) else e)
                    for e in expectations[:3]
                )
            else:
                exp_summary = str(expectations)[:150]

            anxiety_label = "high" if anxiety > 0.7 else "moderate" if anxiety > 0.4 else "low"
            prospection_lines.append(
                f"   - {char_id}: Expects: {exp_summary}. "
                f"Anxiety: {anxiety_label} ({anxiety:.1f}). "
                f"Forecast confidence: {confidence:.1f}."
            )

    if prospection_lines:
        prospection_block = (
            "\n\nCHARACTER EXPECTATIONS (from prospection):\n"
            "Characters should reference these concerns in dialog — they are actively thinking about these issues.\n"
            + "\n".join(prospection_lines)
        )

    prompt = f"""Generate a realistic conversation between these {len(participants_context)} characters: {entity_name_list}.

IMPORTANT: ONLY use the character IDs listed below as speakers. Do NOT invent or substitute other characters.
The speakers MUST be exactly: {entity_name_list}

================================================================
TIER 1: MANDATORY RULES (violations = generation failure)
================================================================

CHARACTER VOICE GUIDE:
Each character below has a distinct voice. Study these examples BEFORE writing any dialog.
Every line a character speaks MUST sound like these examples — same sentence length, same tone, same vocabulary level.

{voice_examples_text}

BANNED OPENERS (NEVER use these to start any character's line):
- "I agree, ..." / "I agree, but ..." / "I agree, we should ..."
- "That's a valid point" / "That's a great point" / "That's a fair point"
- "I understand your concerns" / "I understand, but ..."
- "I see your point" / "I hear what you're saying"
- "You raise a good point" / "You make a good point"
- "I appreciate your perspective" / "With all due respect"
- "You're right, but ..." / "I take your point"
If a character's role says they RESIST or DISAGREE, they MUST actually resist in dialog — not soften it with hedging.

DIALOG STRUCTURE RULES:
- {structure_instructions}
- Do NOT cycle through speakers in round-robin order. Some characters speak 3 times, others speak once.
- Vary turn length: some turns are 1 sentence, others are 3-4 sentences. Mix short punchy exchanges with longer monologues.
- Allow interruptions (one character cuts off another mid-thought).

================================================================
TIER 2: IMPORTANT CONTEXT
================================================================

TEMPORAL MOOD:
{temporal_mood}

CONFLICT AND SPECIFICITY:
When characters discuss decisions or situations, they MUST use SPECIFIC details:
- NUMBERS: exact figures, percentages, dates, dollar amounts
- NAMES: specific people, systems, protocols, locations
- TRADE-OFFS: what was sacrificed for what was gained
- CONSEQUENCES: concrete outcomes, not vague abstractions
BAD: "We need more funding to grow."
GOOD: "We need $4M by March to hit 50 enterprise customers before Acme launches their competing product."
{qse_block}
{prospection_block}

TEMPORAL FRESHNESS:
- Each timepoint is a DIFFERENT moment in time. Reflect NEW developments, not rehashes.
- BUILD ON previous discussions — don't repeat them.
- Reference the SPECIFIC timepoint_context event.

================================================================
TIER 3: REFERENCE INFORMATION
================================================================

PARTICIPANTS:
{participants_json}

SCENE CONTEXT:
{scene_json}

Physical/emotional state effects:
- High pain → shorter responses, irritable tone, may leave early
- Negative valence → pessimistic, critical, withdrawn
- High arousal + negative valence → confrontational, agitated
- Low energy → brief responses, less elaboration

Knowledge constraints:
- ONLY reference information in knowledge list
- Create exposure opportunities (one character reveals info to another)
- Show personality through what they emphasize
"""

    # Add prior beats avoidance if available
    if prior_dialog_beats:
        beats_list = "\n".join(f"   - {beat}" for beat in prior_dialog_beats[-5:])
        prompt += f"""
BEATS ALREADY COVERED (Do NOT repeat these — advance the narrative):
{beats_list}
You MUST introduce NEW developments beyond these. Repeating these beats is a failure.
"""

    # Add non-human entity voice rules if any non-human participants
    non_human_participants = [
        ctx for ctx in participants_context
        if ctx.get("dialog_speaking_mode")
    ]
    if non_human_participants:
        voice_rules = []
        for ctx in non_human_participants:
            mode = ctx["dialog_speaking_mode"]
            voice_rules.append(f"   - {ctx['id']}: {mode}")
        rules_text = "\n".join(voice_rules)
        prompt += f"""
NON-HUMAN ENTITY VOICE RULES:
The following entities are NOT human. They must NOT speak with human dialog patterns.
Instead, use the specified narration mode for each:
{rules_text}
Format non-human "speech" as narrated action or environmental description, NOT quoted dialog.
"""

    # Generate dialog with structured output
    # January 2026: Increased from 2000 to 6000 tokens to prevent dialog truncation
    # 8-12 turn dialogs need ~4000-5000 tokens; 2000 was causing JSON parsing failures
    dialog_data = llm.generate_dialog(
        prompt=prompt,
        max_tokens=6000
    )

    # Rejection sampling: evaluate quality and retry once if needed
    initial_turns = []
    for turn in dialog_data.turns:
        turn_dict = turn.dict() if hasattr(turn, 'dict') else turn.model_dump()
        initial_turns.append(turn_dict)

    quality = _evaluate_dialog_quality(initial_turns)
    if not quality["passed"]:
        print(f"    [M11] Dialog quality check FAILED (score={quality['score']:.2f}, "
              f"failures={quality['failures']}). Retrying with repair notes...")
        repair_prompt = prompt + f"""

REPAIR INSTRUCTIONS (previous generation failed quality checks):
{quality['repair_notes']}

These fixes are MANDATORY. The previous generation was rejected for violating these rules.
"""
        dialog_data = llm.generate_dialog(
            prompt=repair_prompt,
            max_tokens=6000
        )
        # Re-evaluate after retry (log only, don't retry again)
        retry_turns = []
        for turn in dialog_data.turns:
            turn_dict = turn.dict() if hasattr(turn, 'dict') else turn.model_dump()
            retry_turns.append(turn_dict)
        retry_quality = _evaluate_dialog_quality(retry_turns)
        print(f"    [M11] Retry quality: score={retry_quality['score']:.2f}, "
              f"failures={retry_quality['failures']}")
    else:
        print(f"    [M11] Dialog quality check passed (score={quality['score']:.2f})")

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

    # Check voice distinctiveness and log warning if characters sound too similar
    voice_score = _check_voice_distinctiveness(turns_data)
    print(f"    [M11] Voice distinctiveness score: {voice_score:.2f}")

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

        # STATE SYNC: Copy CognitiveTensor → TTMTensor after dialog
        # Emotional/cognitive changes from dialog persist to the entity's tensor representation
        from schemas import CognitiveTensor
        sync_count = 0
        for entity in entities:
            # Get the updated cognitive state from entity metadata
            updated_cog_data = entity.entity_metadata.get("cognitive_tensor", {})
            if updated_cog_data:
                try:
                    updated_cognitive = CognitiveTensor(**updated_cog_data)
                    if _sync_cognitive_to_ttm(entity, updated_cognitive, store=store):
                        sync_count += 1
                except Exception as e:
                    logger.warning(f"[SYNC] Failed Cog→TTM sync for {entity.entity_id}: {e}")

        if sync_count > 0:
            print(f"    [SYNC] Cog→TTM for {sync_count} entities (state propagation)")

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
