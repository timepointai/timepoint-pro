"""
Params2Persona - Map entity tensor state + ADPRS phi to LLM generation parameters.

Called per turn, not per dialog. Converts the abstract state engine output
(CognitiveTensor, behavior_vector, ADPRS envelope) into concrete LLM API
parameters (temperature, top_p, max_tokens, frequency_penalty, presence_penalty).

This enables per-character voice differentiation at the generation level:
aroused characters get higher temperature, fatigued characters get shorter
max_tokens, rich-vocabulary characters get higher frequency_penalty, etc.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PersonaParams:
    """LLM generation parameters derived from entity state."""
    temperature: float = 0.7        # 0.3 - 1.2 (arousal -> varied; low energy -> constrained)
    top_p: float = 0.9              # 0.7 - 0.98 (agitated -> focused sampling)
    max_tokens: int = 250           # 50 - 500 (energy + turn position -> shorter when tired)
    frequency_penalty: float = 0.5  # 0.0 - 0.8 (behavior_vector vocabulary richness)
    presence_penalty: float = 0.3   # 0.0 - 0.6 (behavior_vector novelty seeking)
    source_entity_id: str = ""
    turn_position: int = 0
    modulation_rationale: str = ""


def _safe_get_behavior_element(entity: 'Entity', index: int, default: float) -> float:
    """Safely extract a behavior_vector element from entity tensor."""
    try:
        if not entity.tensor:
            return default
        import json
        import base64
        import msgspec

        tensor_dict = json.loads(entity.tensor)
        behavior_bytes = tensor_dict.get("behavior_vector", "")
        if not behavior_bytes:
            return default

        # Handle base64-encoded msgpack
        if isinstance(behavior_bytes, str):
            behavior_bytes = base64.b64decode(behavior_bytes)
        behavior_array = np.array(msgspec.msgpack.decode(behavior_bytes))

        if index < len(behavior_array):
            val = float(behavior_array[index])
            return max(0.0, min(1.0, val))
        return default
    except Exception:
        return default


def compute_persona_params(
    entity: 'Entity',
    cognitive: 'CognitiveTensor',
    turn_position: int,
    max_turns: int,
    adprs_envelope: Optional['ADPRSEnvelope'] = None,
    evaluation_time: Optional[datetime] = None,
) -> PersonaParams:
    """
    Compute per-turn LLM generation parameters from entity state.

    Maps arousal, energy, behavior vector traits, and ADPRS fidelity
    to temperature, top_p, max_tokens, frequency_penalty, presence_penalty.

    Args:
        entity: Entity with tensor data
        cognitive: Coupled cognitive tensor (after pain/illness)
        turn_position: Current turn index (0-based)
        max_turns: Maximum turns in dialog
        adprs_envelope: Optional ADPRS envelope for fidelity scaling
        evaluation_time: Time to evaluate ADPRS at (defaults to now)

    Returns:
        PersonaParams with generation parameters and rationale
    """
    rationale_parts = []

    # --- Extract state values ---
    arousal = max(0.0, min(1.0, cognitive.emotional_arousal))
    energy = max(0.0, min(100.0, cognitive.energy_budget))
    energy_normalized = energy / 100.0  # Normalize to 0-1

    # Behavior vector elements (with safe defaults)
    vocab_richness = _safe_get_behavior_element(entity, 5, 0.5)
    novelty_seeking = _safe_get_behavior_element(entity, 6, 0.3)

    # --- Temperature ---
    # Base temperature modulated by arousal and energy
    base_temp = 0.7
    # Arousal > 0.7 pushes temp up toward ~1.1; low arousal keeps it lower
    arousal_factor = 0.6 + arousal * 0.6  # range: 0.6 - 1.2
    # Low energy damps temperature (tired = more predictable speech)
    energy_factor = 0.7 + energy_normalized * 0.3  # range: 0.7 - 1.0
    temperature = base_temp * arousal_factor * energy_factor
    temperature = max(0.3, min(1.2, temperature))
    rationale_parts.append(f"temp={temperature:.2f} (arousal={arousal:.2f}, energy={energy:.0f})")

    # --- Top P ---
    # Agitated characters focus vocabulary (lower top_p = more focused)
    top_p = 1.0 - (arousal * 0.25)  # range: 0.75 - 1.0
    top_p = max(0.7, min(0.98, top_p))
    rationale_parts.append(f"top_p={top_p:.2f}")

    # --- Max Tokens ---
    # Base tokens decrease with turn position (fatigue curve) and low energy
    base_tokens = 350
    # Position decay: later turns are shorter
    position_factor = 1.0 - (turn_position / max(max_turns, 1)) * 0.4  # 1.0 -> 0.6
    # Energy decay: low energy = shorter responses
    energy_token_factor = 0.4 + energy_normalized * 0.6  # 0.4 - 1.0
    max_tokens = int(base_tokens * position_factor * energy_token_factor)
    max_tokens = max(50, min(500, max_tokens))
    rationale_parts.append(f"max_tokens={max_tokens} (pos={turn_position}/{max_turns})")

    # --- Frequency Penalty ---
    # Maps to vocabulary richness from behavior vector
    frequency_penalty = max(0.0, min(0.8, vocab_richness))
    rationale_parts.append(f"freq_pen={frequency_penalty:.2f} (vocab_richness)")

    # --- Presence Penalty ---
    # Maps to novelty seeking from behavior vector
    presence_penalty = max(0.0, min(0.6, novelty_seeking))
    rationale_parts.append(f"pres_pen={presence_penalty:.2f} (novelty_seeking)")

    # --- ADPRS Envelope Modulation ---
    # Low phi = more constrained (lower temperature, fewer tokens)
    if adprs_envelope is not None:
        eval_time = evaluation_time or datetime.utcnow()
        try:
            phi = adprs_envelope.evaluate(eval_time)
            phi = max(0.0, min(1.0, phi))

            # Phi scales parameters: low phi constrains everything
            # At phi=0.2, reduce params to 60% of computed values
            # At phi=1.0, keep them at 100%
            phi_scale = 0.6 + phi * 0.4  # range: 0.6 - 1.0

            temperature = max(0.3, temperature * phi_scale)
            max_tokens = max(50, int(max_tokens * phi_scale))
            # top_p gets slightly more focused at low phi
            top_p = max(0.7, top_p * (0.8 + phi * 0.2))

            rationale_parts.append(f"adprs_phi={phi:.2f} (scale={phi_scale:.2f})")
        except Exception as e:
            logger.warning(f"ADPRS evaluation failed for {entity.entity_id}: {e}")
            rationale_parts.append("adprs=error_skipped")

    return PersonaParams(
        temperature=round(temperature, 3),
        top_p=round(top_p, 3),
        max_tokens=max_tokens,
        frequency_penalty=round(frequency_penalty, 3),
        presence_penalty=round(presence_penalty, 3),
        source_entity_id=entity.entity_id,
        turn_position=turn_position,
        modulation_rationale="; ".join(rationale_parts),
    )
