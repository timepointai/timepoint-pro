"""
Voice Controls for Entity Mixing

Part of the SynthasAIzer control paradigm.
See SYNTH.md for full specification.
"""

from pydantic import BaseModel, Field
from typing import Dict


class VoiceConfig(BaseModel):
    """
    Mixer-style controls for an entity.

    Provides standard mixing board controls:
    - Mute: Exclude entity from active dialog (but still exists in world)
    - Solo: Only this entity participates (others backgrounded)
    - Gain: Weighted importance (0.0-1.0)

    Example:
        # Background character with reduced importance
        voice = VoiceConfig(gain=0.3)

        # Focus on a specific entity
        voice = VoiceConfig(solo=True)

        # Temporarily exclude an entity
        voice = VoiceConfig(mute=True)
    """
    mute: bool = Field(
        default=False,
        description="Exclude entity from active dialog synthesis"
    )
    solo: bool = Field(
        default=False,
        description="Focus on this entity only (others backgrounded)"
    )
    gain: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Importance weight (0.0=silent, 1.0=full)"
    )

    def is_active(self) -> bool:
        """Check if this voice should produce output."""
        return not self.mute and self.gain > 0.0

    def effective_gain(self) -> float:
        """Get the effective gain considering mute state."""
        if self.mute:
            return 0.0
        return self.gain

    def __repr__(self) -> str:
        status = []
        if self.mute:
            status.append("MUTED")
        if self.solo:
            status.append("SOLO")
        status_str = f" [{', '.join(status)}]" if status else ""
        return f"VoiceConfig(gain={self.gain:.2f}{status_str})"


class VoiceMixer:
    """
    Manages voice controls for multiple entities.

    Handles the logic of mute/solo/gain across entity pool.

    Example:
        mixer = VoiceMixer()
        mixer.set_voice("john_smith", VoiceConfig(gain=1.0))
        mixer.set_voice("background_char", VoiceConfig(gain=0.3))

        # Get active entities
        active = mixer.get_active_entities(["john_smith", "jane_doe", "background_char"])

        # Get weight for dialog synthesis
        weight = mixer.get_entity_weight("background_char")  # Returns 0.3
    """

    def __init__(self, default_voice: VoiceConfig = None):
        self.default_voice = default_voice or VoiceConfig()
        self.voices: Dict[str, VoiceConfig] = {}

    def set_voice(self, entity_id: str, voice: VoiceConfig):
        """Set voice configuration for a specific entity."""
        self.voices[entity_id] = voice

    def get_voice(self, entity_id: str) -> VoiceConfig:
        """Get voice configuration for an entity, falling back to default."""
        return self.voices.get(entity_id, self.default_voice)

    def get_active_entity_ids(self, entity_ids: list) -> list:
        """
        Filter entity IDs based on voice controls.

        If any entity is solo'd, return only solo'd entities.
        Otherwise, return all non-muted entities.
        """
        # Check for any solo'd entities
        solo_ids = [
            eid for eid in entity_ids
            if self.get_voice(eid).solo
        ]
        if solo_ids:
            return solo_ids

        # Filter out muted entities
        return [
            eid for eid in entity_ids
            if not self.get_voice(eid).mute
        ]

    def get_entity_weight(self, entity_id: str) -> float:
        """Get the effective weight for an entity."""
        return self.get_voice(entity_id).effective_gain()

    def has_solo(self) -> bool:
        """Check if any voice is solo'd."""
        return any(v.solo for v in self.voices.values())

    def clear(self):
        """Clear all voice configurations."""
        self.voices.clear()


# Default voice that produces full participation (backward compatible behavior)
DEFAULT_VOICE = VoiceConfig()
