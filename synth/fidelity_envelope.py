"""
ADPRS Fidelity Envelope for Continuous Resolution Allocation

Part of the SynthasAIzer control paradigm.
See SYNTH.md for full specification.

ADPRS (Asymptotic/Duration/Period/Recurrence/Spread) waveforms model
fidelity allocation as continuous functions evaluated at O(1) per query.
This is distinct from the ADSR presence envelope in envelope.py — ADPRS
controls *resolution level*, ADSR controls *presence intensity*.

Phase 1: Shadow mode — runs in parallel with discrete ResolutionLevel
system, logs both, compares divergence. No fidelity decisions change.
"""

import math
from enum import Enum
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, field_validator


class FidelityBand(str, Enum):
    """
    Local enum mapping phi ranges to resolution names.

    Kept separate from schemas.ResolutionLevel to avoid circular imports.
    Maps 1:1 with ResolutionLevel ordinals for shadow comparison.
    """
    TENSOR = "tensor"
    SCENE = "scene"
    GRAPH = "graph"
    DIALOG = "dialog"
    TRAINED = "trained"


# Ordinal mapping for divergence calculation
_BAND_ORDINAL = {
    FidelityBand.TENSOR: 0,
    FidelityBand.SCENE: 1,
    FidelityBand.GRAPH: 2,
    FidelityBand.DIALOG: 3,
    FidelityBand.TRAINED: 4,
}

# Map ResolutionLevel string values to FidelityBand for comparison
_RESOLUTION_TO_BAND = {
    "tensor_only": FidelityBand.TENSOR,
    "scene": FidelityBand.SCENE,
    "graph": FidelityBand.GRAPH,
    "dialog": FidelityBand.DIALOG,
    "trained": FidelityBand.TRAINED,
    "full_detail": FidelityBand.TRAINED,  # full_detail maps to highest band
}


def datetime_to_ms(dt: datetime) -> float:
    """Convert a datetime to epoch milliseconds (UTC)."""
    return dt.timestamp() * 1000.0


def phi_to_resolution_band(phi: float) -> FidelityBand:
    """
    Map a continuous phi value [0, 1] to a discrete FidelityBand.

    Boundaries:
        [0.0, 0.2) -> TENSOR
        [0.2, 0.4) -> SCENE
        [0.4, 0.6) -> GRAPH
        [0.6, 0.8) -> DIALOG
        [0.8, 1.0] -> TRAINED
    """
    if phi < 0.2:
        return FidelityBand.TENSOR
    elif phi < 0.4:
        return FidelityBand.SCENE
    elif phi < 0.6:
        return FidelityBand.GRAPH
    elif phi < 0.8:
        return FidelityBand.DIALOG
    else:
        return FidelityBand.TRAINED


class ADPRSEnvelope(BaseModel):
    """
    Single ADPRS fidelity envelope.

    Parameters:
        A (Asymptotic): Decay rate control. 0=fast exponential decay, 1=no decay.
        D (Duration): Active window in milliseconds from t0.
        P (Period): Number of oscillation periods within duration.
        R (Recurrence): Cycle length in ms. 0=single-shot, >D means gaps.
        S (Spread): Output range. 0=collapses to baseline, 1=full [0,1] range.
        t0: Start time (ISO 8601 string or datetime).
        baseline: Floor value when envelope is inactive. Default 0.1.

    Core waveform at normalized time tau in [0, 1]:
        phi(tau) = |sin(tau * 2pi * P)| * (1 - tau)^((1 - A) * 3) * S + (1 - S) * baseline

    Output is always clamped to [0, 1].
    """
    A: float = Field(default=0.7, ge=0.0, le=1.0, description="Asymptotic decay rate (0=fast, 1=none)")
    D: float = Field(default=31536000000.0, ge=0.0, description="Duration in milliseconds")
    P: float = Field(default=2.0, ge=0.0, description="Number of oscillation periods")
    R: float = Field(default=0.0, ge=0.0, description="Recurrence cycle length in ms (0=single-shot)")
    S: float = Field(default=0.8, ge=0.0, le=1.0, description="Spread (0=baseline only, 1=full range)")
    t0: str = Field(default="2025-01-01T00:00:00+00:00", description="Start time ISO 8601")
    baseline: float = Field(default=0.1, ge=0.0, le=1.0, description="Floor value when inactive")

    @field_validator("t0")
    @classmethod
    def validate_t0(cls, v):
        """Ensure t0 is a valid ISO 8601 datetime string."""
        if isinstance(v, datetime):
            return v.isoformat()
        # Validate by parsing
        datetime.fromisoformat(v)
        return v

    def _parse_t0(self) -> datetime:
        """Parse t0 string to datetime."""
        dt = datetime.fromisoformat(self.t0)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def evaluate(self, t: datetime) -> float:
        """
        Evaluate the ADPRS waveform at time t.

        Returns phi in [0, 1]. Times before t0 or after duration return baseline.
        """
        t0_dt = self._parse_t0()

        # Ensure t has timezone info
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)

        elapsed_ms = (t - t0_dt).total_seconds() * 1000.0

        # Before start → baseline
        if elapsed_ms < 0:
            return self.baseline

        # Handle recurrence
        if self.R > 0:
            # Cycle position within recurrence
            cycle_pos = elapsed_ms % self.R
            # If we're in the gap between D and R, return baseline
            if cycle_pos > self.D:
                return self.baseline
            elapsed_ms = cycle_pos

        # After duration (single-shot) → baseline
        if self.D <= 0:
            return self.baseline
        if elapsed_ms > self.D:
            return self.baseline

        # Normalized time within duration
        tau = elapsed_ms / self.D

        # Core waveform: |sin(tau * 2pi * P)| * (1 - tau)^((1 - A) * 3) * S + (1 - S) * baseline
        oscillation = abs(math.sin(tau * 2.0 * math.pi * self.P))
        decay = (1.0 - tau) ** ((1.0 - self.A) * 3.0) if tau < 1.0 else 0.0
        phi = oscillation * decay * self.S + (1.0 - self.S) * self.baseline

        # Clamp to [0, 1]
        return max(0.0, min(1.0, phi))

    def evaluate_band(self, t: datetime) -> FidelityBand:
        """Map the waveform value at time t to a discrete FidelityBand."""
        return phi_to_resolution_band(self.evaluate(t))

    def to_metadata_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for entity_metadata JSON storage."""
        return {
            "A": self.A,
            "D": self.D,
            "P": self.P,
            "R": self.R,
            "S": self.S,
            "t0": self.t0,
            "baseline": self.baseline,
        }

    @classmethod
    def from_metadata_dict(cls, d: Dict[str, Any]) -> "ADPRSEnvelope":
        """Deserialize from a metadata dict."""
        return cls(**d)

    def __repr__(self) -> str:
        return f"ADPRSEnvelope(A={self.A:.2f}, D={self.D:.0f}, P={self.P:.1f}, R={self.R:.0f}, S={self.S:.2f})"


class ADPRSComposite(BaseModel):
    """
    Max-composition of multiple ADPRS envelopes.

    Phi(t) = max(phi_1(t), phi_2(t), ...)

    An empty composite always evaluates to 0.0.
    """
    envelopes: List[ADPRSEnvelope] = Field(default_factory=list)

    def evaluate(self, t: datetime) -> float:
        """Evaluate the composite waveform (max of all envelopes)."""
        if not self.envelopes:
            return 0.0
        return max(env.evaluate(t) for env in self.envelopes)

    def evaluate_band(self, t: datetime) -> FidelityBand:
        """Map the composite value at time t to a discrete FidelityBand."""
        return phi_to_resolution_band(self.evaluate(t))

    def to_metadata_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for entity_metadata JSON storage."""
        return {
            "envelopes": [env.to_metadata_dict() for env in self.envelopes],
        }

    @classmethod
    def from_metadata_dict(cls, d: Dict[str, Any]) -> "ADPRSComposite":
        """Deserialize from a metadata dict."""
        envelopes = [ADPRSEnvelope.from_metadata_dict(e) for e in d.get("envelopes", [])]
        return cls(envelopes=envelopes)

    def __repr__(self) -> str:
        return f"ADPRSComposite(n={len(self.envelopes)})"
