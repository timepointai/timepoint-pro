"""
ADSR Envelope for Entity Presence Intensity

Part of the SynthasAIzer control paradigm.
See SYNTH.md for full specification.
"""

from pydantic import BaseModel, Field, field_validator


class EnvelopeConfig(BaseModel):
    """
    ADSR envelope for entity presence intensity.

    Controls how an entity's presence evolves through a scenario:
    - Attack: How quickly entity reaches full presence
    - Decay: Initial intensity drop after peak
    - Sustain: Baseline presence level during middle timepoints
    - Release: How the entity fades in final timepoints

    All values are 0.0-1.0 and represent proportional time/intensity.

    Example:
        # Dramatic buildup with slow fade
        envelope = EnvelopeConfig(
            attack=0.3,   # Slow buildup
            decay=0.1,    # Quick peak
            sustain=0.9,  # High intensity
            release=0.5   # Gradual resolution
        )

        # Get intensity at 50% through scenario
        intensity = envelope.intensity_at(0.5, total_timepoints=10)
    """
    attack: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="How quickly entity reaches full presence (0.0=instant, 1.0=gradual)"
    )
    decay: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Drop after initial peak (0.0=none, 1.0=drops to sustain immediately)"
    )
    sustain: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Baseline presence level during middle timepoints"
    )
    release: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Fade out speed (0.0=abrupt, 1.0=gradual)"
    )

    def intensity_at(self, progress: float, total_timepoints: int = 1) -> float:
        """
        Calculate presence intensity at a given progress point.

        Args:
            progress: 0.0 (start) to 1.0 (end) of scenario
            total_timepoints: Total number of timepoints (for context, not currently used)

        Returns:
            Intensity multiplier 0.0-1.0

        The envelope is divided into phases:
        - Attack: First 0-25% (scaled by attack param)
        - Decay: Next 0-25% (scaled by decay param)
        - Sustain: Middle portion
        - Release: Last 0-25% (scaled by release param)
        """
        # Clamp progress to valid range
        progress = max(0.0, min(1.0, progress))

        # Normalize envelope parameters to scenario length
        # Each phase can use up to 25% of total time
        a_end = self.attack * 0.25  # Attack phase ends here
        d_end = a_end + self.decay * 0.25  # Decay phase ends here
        r_start = 1.0 - self.release * 0.25  # Release phase starts here

        if progress < a_end and a_end > 0:
            # Attack phase: ramp up from 0 to 1
            return progress / a_end
        elif progress < d_end and (d_end - a_end) > 0:
            # Decay phase: drop from 1 to sustain level
            decay_progress = (progress - a_end) / (d_end - a_end)
            return 1.0 - (1.0 - self.sustain) * decay_progress
        elif progress < r_start:
            # Sustain phase: hold at sustain level
            return self.sustain
        elif (1.0 - r_start) > 0:
            # Release phase: fade from sustain to 0
            release_progress = (progress - r_start) / (1.0 - r_start)
            return self.sustain * (1.0 - release_progress)
        else:
            # Edge case: release is 0, return sustain
            return self.sustain

    def __repr__(self) -> str:
        return f"EnvelopeConfig(A={self.attack:.2f}, D={self.decay:.2f}, S={self.sustain:.2f}, R={self.release:.2f})"


# Default envelope that produces flat 0.8 sustain (backward compatible behavior)
DEFAULT_ENVELOPE = EnvelopeConfig()
