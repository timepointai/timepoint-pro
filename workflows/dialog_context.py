# ============================================================================
# workflows/dialog_context.py - Fourth Wall Context Builder + PORTAL Stripping
# ============================================================================
"""
Two-layer context system for per-character dialog generation.

BackLayer: Visible to LLM, NOT expressed in dialog. Shapes HOW a character speaks.
FrontLayer: What the character 'knows'. Dialog content drawn from here.

Also contains PORTAL knowledge stripping (Component 5): characters only know
things from timepoints causally upstream of their current position.

Replaces the inline participant_ctx dict construction from dialog_synthesis.py
with structured, layer-separated context that gives the LLM explicit instructions
about what shapes voice vs. what shapes content.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Data classes
# ============================================================================

@dataclass
class BackLayerContext:
    """Visible to LLM, NOT expressed in dialog. Shapes HOW character speaks."""
    context_vector_summary: Dict[str, float] = field(default_factory=dict)
    behavior_vector_summary: Dict[str, float] = field(default_factory=dict)
    adprs_band: str = "unknown"
    adprs_phi: float = 0.5
    causal_chain_position: str = ""
    withheld_knowledge: List[Dict[str, str]] = field(default_factory=list)
    suppressed_impulses: List[str] = field(default_factory=list)
    steering_directives: List[str] = field(default_factory=list)
    true_emotional_state: Dict[str, float] = field(default_factory=dict)
    anxiety_level: float = 0.0


@dataclass
class FrontLayerContext:
    """What the character 'knows'. Dialog drawn from here."""
    knowledge_items: List[Dict[str, Any]] = field(default_factory=list)
    relationship_descriptions: Dict[str, str] = field(default_factory=dict)
    presented_emotional_state: str = "composed"
    physical_state_description: str = ""
    scene_context: str = ""
    time_awareness: str = ""


@dataclass
class FourthWallContext:
    """Complete two-layer context for one character in dialog."""
    entity_id: str
    back_layer: BackLayerContext
    front_layer: FrontLayerContext
    persona_params: Any = None  # PersonaParams (avoid circular import)
    speaking_style: Dict[str, str] = field(default_factory=dict)
    voice_examples: List[str] = field(default_factory=list)
    dialog_behavior: Dict[str, str] = field(default_factory=dict)


# ============================================================================
# PORTAL Knowledge Stripping (Component 5)
# ============================================================================

def _build_causal_ancestry(timepoint: 'Timepoint', store: Optional['GraphStore'] = None) -> Set[str]:
    """
    Walk causal_parent chain to build set of ancestor timepoint_ids.

    Returns set of all timepoint_ids causally upstream of (and including)
    the given timepoint.
    """
    ancestors = {timepoint.timepoint_id}

    if not store or not timepoint.causal_parent:
        return ancestors

    current_id = timepoint.causal_parent
    visited = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        ancestors.add(current_id)
        try:
            parent_tp = store.get_timepoint(current_id)
            if parent_tp and parent_tp.causal_parent:
                current_id = parent_tp.causal_parent
            else:
                break
        except Exception:
            break

    return ancestors


def filter_knowledge_by_causal_time(
    knowledge_items: List[Dict[str, Any]],
    current_timepoint: 'Timepoint',
    entity: 'Entity',
    store: Optional['GraphStore'] = None,
) -> List[Dict[str, Any]]:
    """
    Filter knowledge by causal ancestry.

    Characters only know things from timepoints causally upstream of their
    current position. Uses Timepoint.causal_parent chain.

    Graceful fallback: if no causal_parent chain exists (non-PORTAL modes),
    skip temporal filtering and return all items.
    """
    # If no store or no causal parent, skip filtering (non-PORTAL mode)
    if not store or not current_timepoint.causal_parent:
        return knowledge_items

    # Build set of causally accessible timepoint IDs
    try:
        ancestors = _build_causal_ancestry(current_timepoint, store)
    except Exception as e:
        logger.warning(f"[PORTAL] Failed to build causal ancestry: {e}. Skipping filter.")
        return knowledge_items

    filtered = []
    stripped_count = 0

    for item in knowledge_items:
        # Check if the knowledge item has a timepoint_id
        item_timepoint = item.get("timepoint_id")

        if item_timepoint is None:
            # No timepoint association — keep it (background knowledge)
            filtered.append(item)
        elif item_timepoint in ancestors:
            # From a causally upstream timepoint — keep it
            filtered.append(item)
        else:
            # From a causally inaccessible timepoint — strip it
            stripped_count += 1

    if stripped_count > 0:
        logger.info(
            f"[PORTAL] Stripped {stripped_count} knowledge items from "
            f"{entity.entity_id} (not causally accessible from "
            f"{current_timepoint.timepoint_id})"
        )

    return filtered


def strip_backwards_emotions(
    knowledge_items: List[Dict[str, Any]],
    current_timestamp: datetime,
) -> List[Dict[str, Any]]:
    """
    Remove items referencing future events emotionally.

    Characters can't fear events that haven't happened in their timeline.
    Strips items with future timestamps that carry emotional content.
    """
    filtered = []
    for item in knowledge_items:
        # Check if item has a timestamp and it's in the future
        item_ts = item.get("timestamp")
        if item_ts:
            try:
                if isinstance(item_ts, str):
                    item_ts = datetime.fromisoformat(item_ts)
                if item_ts > current_timestamp:
                    # Future item — check if it's emotional
                    content = item.get("content", "").lower()
                    emotional_markers = [
                        "fear", "dread", "worry about", "anxious about",
                        "hope for", "looking forward to", "anticipate",
                    ]
                    if any(marker in content for marker in emotional_markers):
                        continue  # Skip future emotional references
            except (ValueError, TypeError):
                pass  # Can't parse timestamp, keep the item

        filtered.append(item)

    return filtered


# ============================================================================
# Context Helper Functions
# ============================================================================

def _scale_knowledge_limit(entity: 'Entity', base_limit: int = 20) -> int:
    """
    Scale knowledge count by entity resolution level.

    Higher-resolution entities get more knowledge context to work with.
    """
    resolution = getattr(entity, 'resolution_level', None)
    if resolution is None:
        return base_limit

    resolution_str = resolution.value if hasattr(resolution, 'value') else str(resolution)

    limits = {
        "tensor_only": 5,
        "scene": 8,
        "graph": 12,
        "dialog": 16,
        "trained": base_limit,
        "full_detail": base_limit,
    }
    return limits.get(resolution_str, base_limit)


def _translate_emotional_state_to_language(
    valence: float,
    arousal: float,
    energy: float,
) -> str:
    """
    Convert numeric emotional state to natural language for front layer.

    Front layer uses human-readable descriptions rather than raw numbers
    so the LLM generates dialog from natural understanding, not numeric parsing.
    """
    # Valence dimension
    if valence > 0.5:
        valence_desc = "upbeat and optimistic"
    elif valence > 0.2:
        valence_desc = "generally positive"
    elif valence > -0.2:
        valence_desc = "neutral"
    elif valence > -0.5:
        valence_desc = "somewhat frustrated"
    else:
        valence_desc = "deeply troubled"

    # Arousal dimension
    if arousal > 0.7:
        arousal_desc = "visibly agitated"
    elif arousal > 0.5:
        arousal_desc = "alert and engaged"
    elif arousal > 0.3:
        arousal_desc = "attentive"
    else:
        arousal_desc = "subdued and withdrawn"

    # Energy dimension
    if energy > 80:
        energy_desc = "energetic"
    elif energy > 50:
        energy_desc = "steady"
    elif energy > 25:
        energy_desc = "tired"
    else:
        energy_desc = "exhausted"

    return f"{valence_desc}, {arousal_desc}, {energy_desc}"


def _describe_relationships_naturally(
    entity: 'Entity',
    others: List['Entity'],
    store: Optional['GraphStore'] = None,
) -> Dict[str, str]:
    """
    Convert relationship metrics to natural language prose.

    Instead of "trust_level: 0.8", the front layer says
    "trusts deeply — has relied on them through several crises".
    """
    descriptions = {}

    for other in others:
        if other.entity_id == entity.entity_id:
            continue

        # Try to get relationship metrics from store
        trust = 0.5
        alignment = 0.0
        interactions = 0

        if store:
            try:
                trajectory = store.get_relationship_trajectory(
                    entity.entity_id, other.entity_id
                )
                if trajectory and trajectory.states:
                    import json as _json
                    states = trajectory.states
                    if isinstance(states, str):
                        states = _json.loads(states)
                    if states:
                        latest = states[-1] if isinstance(states, list) else states
                        if isinstance(latest, dict):
                            metrics = latest.get("metrics", {})
                            trust = metrics.get("trust_level", 0.5)
                            alignment = metrics.get("belief_alignment", 0.0)
                            interactions = metrics.get("interaction_count", 0)
            except Exception:
                pass

        # Build natural description
        parts = []

        # Trust level
        if trust > 0.8:
            parts.append("trusts deeply")
        elif trust > 0.6:
            parts.append("generally trusts")
        elif trust > 0.4:
            parts.append("cautiously engaged with")
        elif trust > 0.2:
            parts.append("wary of")
        else:
            parts.append("deeply distrusts")

        # Alignment
        if alignment > 0.5:
            parts.append("shares similar views")
        elif alignment < -0.5:
            parts.append("fundamentally disagrees with")

        # Familiarity
        if interactions > 10:
            parts.append("long history together")
        elif interactions > 3:
            parts.append("some shared experience")
        elif interactions == 0:
            parts.append("barely knows")

        descriptions[other.entity_id] = " — ".join(parts) if parts else "no established relationship"

    return descriptions


def _describe_physical_state(physical: 'PhysicalTensor') -> str:
    """Convert physical tensor to natural language."""
    parts = []

    if physical.pain_level > 0.5:
        loc = physical.pain_location or "throughout body"
        parts.append(f"in significant pain ({loc})")
    elif physical.pain_level > 0.2:
        parts.append("experiencing mild discomfort")

    if physical.health_status < 0.5:
        parts.append("visibly unwell")
    elif physical.health_status < 0.8:
        parts.append("not at full health")

    if physical.stamina < 0.3:
        parts.append("physically drained")

    if physical.fever > 38.5:
        parts.append("feverish")

    if physical.mobility < 0.5:
        parts.append("limited mobility")

    if not parts:
        return "physically well"

    return ", ".join(parts)


# ============================================================================
# Main Builder
# ============================================================================

def build_fourth_wall_context(
    entity: 'Entity',
    coupled_cognitive: 'CognitiveTensor',
    physical: 'PhysicalTensor',
    timepoint: 'Timepoint',
    timeline: List[Dict],
    other_entities: List['Entity'],
    store: Optional['GraphStore'] = None,
    proception_state: Optional['ProspectiveState'] = None,
    adprs_envelope: Optional['ADPRSEnvelope'] = None,
    knowledge_limit: int = 20,
) -> FourthWallContext:
    """
    Build complete two-layer context for one character.

    Replaces the inline participant_ctx construction with structured
    back-layer (shapes voice) and front-layer (provides content) separation.

    Args:
        entity: The entity to build context for
        coupled_cognitive: Cognitive tensor after pain/illness coupling
        physical: Physical tensor
        timepoint: Current timepoint
        timeline: Timeline context
        other_entities: Other entities in the scene
        store: GraphStore for knowledge/relationship lookups
        proception_state: Optional prospective state (M15)
        adprs_envelope: Optional ADPRS envelope for fidelity
        knowledge_limit: Base knowledge limit (scaled by resolution)
    """
    from workflows.dialog_synthesis import (
        _build_knowledge_from_exposures,
        _derive_speaking_style,
        _generate_voice_examples,
        _derive_dialog_params_from_persona,
        _infer_personality_from_role,
    )

    # --- Scale knowledge limit by resolution ---
    scaled_limit = _scale_knowledge_limit(entity, knowledge_limit)

    # --- Build knowledge (M3 integration) ---
    knowledge_items = _build_knowledge_from_exposures(entity, store=store, limit=scaled_limit)

    # --- PORTAL knowledge stripping (Component 5) ---
    knowledge_items = filter_knowledge_by_causal_time(
        knowledge_items, timepoint, entity, store
    )
    knowledge_items = strip_backwards_emotions(
        knowledge_items, timepoint.timestamp
    )

    # --- Personality traits (three-tier fallback) ---
    personality_traits = (
        entity.entity_metadata.get("personality_traits")
        or _infer_personality_from_role(entity.entity_metadata.get("role", ""))
    )

    # --- Speaking style ---
    speaking_style = _derive_speaking_style(
        personality_traits,
        entity.entity_metadata.get("archetype_id", "")
    )

    # --- Voice examples ---
    speech_examples = entity.entity_metadata.get("speech_examples")
    if speech_examples:
        voice_examples = speech_examples[:3]
    else:
        voice_examples = _generate_voice_examples(speaking_style, entity.entity_id)

    # --- Dialog behavior ---
    emotional_state = {
        "valence": coupled_cognitive.emotional_valence,
        "arousal": coupled_cognitive.emotional_arousal,
    }
    dialog_behavior = _derive_dialog_params_from_persona(
        speaking_style=speaking_style,
        emotional_state=emotional_state,
        energy=coupled_cognitive.energy_budget,
        entity_type=entity.entity_type or "human",
    )

    # --- Back Layer ---
    # Extract behavior vector summary if available
    behavior_summary = {}
    try:
        if entity.tensor:
            import base64
            import msgspec
            import numpy as np
            tensor_dict = json.loads(entity.tensor)
            bv_raw = tensor_dict.get("behavior_vector", "")
            if isinstance(bv_raw, str) and bv_raw:
                bv_bytes = base64.b64decode(bv_raw)
                bv = np.array(msgspec.msgpack.decode(bv_bytes))
                behavior_summary = {
                    f"dim_{i}": round(float(v), 3) for i, v in enumerate(bv[:8])
                }
    except Exception:
        pass

    # ADPRS band/phi
    adprs_band = "unknown"
    adprs_phi = 0.5
    if adprs_envelope:
        try:
            adprs_phi = adprs_envelope.evaluate(timepoint.timestamp)
            adprs_band = adprs_envelope.evaluate_band(timepoint.timestamp).value
        except Exception:
            pass

    # Causal chain position
    from workflows.dialog_synthesis import get_timepoint_position
    causal_position = get_timepoint_position(timeline, timepoint)

    # Withheld knowledge from proception
    withheld = []
    if proception_state:
        try:
            wk = proception_state.withheld_knowledge
            if isinstance(wk, str):
                wk = json.loads(wk)
            if isinstance(wk, list):
                withheld = wk
        except Exception:
            pass

    # Suppressed impulses from proception
    suppressed = []
    if proception_state:
        try:
            si = proception_state.suppressed_impulses
            if isinstance(si, str):
                si = json.loads(si)
            if isinstance(si, list):
                suppressed = [
                    item.get("impulse", str(item)) if isinstance(item, dict) else str(item)
                    for item in si
                ]
        except Exception:
            pass

    anxiety = 0.0
    if proception_state:
        anxiety = proception_state.anxiety_level

    back_layer = BackLayerContext(
        context_vector_summary={},
        behavior_vector_summary=behavior_summary,
        adprs_band=adprs_band,
        adprs_phi=adprs_phi,
        causal_chain_position=causal_position,
        withheld_knowledge=withheld,
        suppressed_impulses=suppressed,
        steering_directives=[],
        true_emotional_state={
            "valence": coupled_cognitive.emotional_valence,
            "arousal": coupled_cognitive.emotional_arousal,
            "energy": coupled_cognitive.energy_budget,
        },
        anxiety_level=anxiety,
    )

    # --- Front Layer ---
    presented_emotion = _translate_emotional_state_to_language(
        coupled_cognitive.emotional_valence,
        coupled_cognitive.emotional_arousal,
        coupled_cognitive.energy_budget,
    )

    relationship_descriptions = _describe_relationships_naturally(
        entity, other_entities, store
    )

    physical_desc = _describe_physical_state(physical)

    scene_ctx = f"{timepoint.event_description} at {timepoint.timestamp.strftime('%I:%M %p')}"

    time_awareness = (
        f"Position in timeline: {causal_position}. "
        f"Current event: {timepoint.event_description}"
    )

    front_layer = FrontLayerContext(
        knowledge_items=knowledge_items,
        relationship_descriptions=relationship_descriptions,
        presented_emotional_state=presented_emotion,
        physical_state_description=physical_desc,
        scene_context=scene_ctx,
        time_awareness=time_awareness,
    )

    return FourthWallContext(
        entity_id=entity.entity_id,
        back_layer=back_layer,
        front_layer=front_layer,
        persona_params=None,  # Set by caller after compute_persona_params
        speaking_style=speaking_style,
        voice_examples=voice_examples,
        dialog_behavior=dialog_behavior,
    )


def format_context_for_prompt(
    fourth_wall: FourthWallContext,
    include_back_layer: bool = True,
) -> str:
    """
    Serialize both layers into a prompt string with explicit instructions.

    The back layer is marked as shaping voice/behavior but NOT to be expressed
    in dialog content. The front layer is what the character actually knows
    and draws dialog from.
    """
    parts = []

    parts.append(f"=== CHARACTER: {fourth_wall.entity_id} ===")

    if include_back_layer:
        bl = fourth_wall.back_layer
        parts.append("")
        parts.append("--- BACK LAYER (shapes voice and behavior; DO NOT express in dialog) ---")
        parts.append(f"ADPRS fidelity: band={bl.adprs_band}, phi={bl.adprs_phi:.2f}")
        parts.append(f"True emotional state: valence={bl.true_emotional_state.get('valence', 0):.2f}, "
                     f"arousal={bl.true_emotional_state.get('arousal', 0):.2f}, "
                     f"energy={bl.true_emotional_state.get('energy', 50):.0f}")
        parts.append(f"Anxiety level: {bl.anxiety_level:.2f}")
        parts.append(f"Timeline position: {bl.causal_chain_position}")

        if bl.withheld_knowledge:
            parts.append(f"Withheld knowledge (character knows but won't say):")
            for wk in bl.withheld_knowledge[:3]:
                content = wk.get("content", str(wk))
                reason = wk.get("reason", "unspecified")
                parts.append(f"  - {content} (reason: {reason})")

        if bl.suppressed_impulses:
            parts.append(f"Suppressed impulses (character wants to but holds back):")
            for si in bl.suppressed_impulses[:3]:
                parts.append(f"  - {si}")

        if bl.steering_directives:
            parts.append(f"Steering directives:")
            for sd in bl.steering_directives:
                parts.append(f"  - {sd}")

    fl = fourth_wall.front_layer
    parts.append("")
    parts.append("--- FRONT LAYER (character's actual knowledge; dialog content drawn from here) ---")
    parts.append(f"Emotional presentation: {fl.presented_emotional_state}")
    parts.append(f"Physical state: {fl.physical_state_description}")
    parts.append(f"Scene: {fl.scene_context}")
    parts.append(f"Time awareness: {fl.time_awareness}")

    if fl.knowledge_items:
        parts.append(f"Knowledge ({len(fl.knowledge_items)} items):")
        for ki in fl.knowledge_items[:10]:
            content = ki.get("content", str(ki))
            source = ki.get("source", "unknown")
            parts.append(f"  - [{source}] {content}")

    if fl.relationship_descriptions:
        parts.append("Relationships:")
        for other_id, desc in fl.relationship_descriptions.items():
            parts.append(f"  - {other_id}: {desc}")

    # Voice guide
    parts.append("")
    style = fourth_wall.speaking_style
    parts.append(f"Speaking style: {style.get('verbosity', 'moderate')} / "
                f"{style.get('formality', 'neutral')} / "
                f"{style.get('tone', 'neutral')} / "
                f"{style.get('vocabulary', 'general')} / "
                f"{style.get('speech_pattern', 'direct')}")

    if fourth_wall.voice_examples:
        parts.append("Voice examples:")
        for ex in fourth_wall.voice_examples:
            parts.append(f'  "{ex}"')

    if fourth_wall.dialog_behavior:
        parts.append("Dialog behavior:")
        for key, val in fourth_wall.dialog_behavior.items():
            parts.append(f"  {key}: {val}")

    return "\n".join(parts)
