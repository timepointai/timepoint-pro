"""
Shadow Evaluator for ADPRS Fidelity Envelopes (Phase 1)

Runs ADPRS continuous envelopes in parallel with the existing discrete
ResolutionLevel system. Logs both, compares divergence. No fidelity
decisions are changed — this is observation-only shadow mode.

Part of the SynthasAIzer control paradigm.
"""

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from synth.fidelity_envelope import (
    ADPRSComposite,
    ADPRSEnvelope,
    FidelityBand,
    _BAND_ORDINAL,
    _RESOLUTION_TO_BAND,
)
from synth.events import SynthEvent, get_emitter

logger = logging.getLogger(__name__)


# Midpoint of each band's phi range, used for continuous divergence
_BAND_MIDPOINT = {
    "tensor_only": 0.1,
    "scene": 0.3,
    "graph": 0.5,
    "dialog": 0.7,
    "trained": 0.9,
    "full_detail": 0.9,
}


@dataclass
class ShadowRecord:
    """One shadow evaluation comparing ADPRS band to actual resolution."""
    entity_id: str
    timepoint_id: str
    timestamp: datetime
    phi_value: float
    adprs_band: FidelityBand
    actual_level: str
    divergence: int  # Signed ordinal distance (positive = ADPRS higher)
    continuous_divergence: float  # phi_value - midpoint_of_actual_band (Phase 2 regression target)
    envelope_count: int


@dataclass
class ShadowEvaluationReport:
    """Aggregate report from a shadow evaluation pass."""
    records: List[ShadowRecord] = field(default_factory=list)
    total_evaluations: int = 0
    divergent_count: int = 0
    mean_divergence: float = 0.0
    max_divergence: int = 0

    def summary(self) -> dict:
        """Return a summary dict for logging/printing."""
        rate = (self.divergent_count / self.total_evaluations * 100.0) if self.total_evaluations > 0 else 0.0
        return {
            "total_evaluations": self.total_evaluations,
            "divergent_count": self.divergent_count,
            "divergence_rate_pct": round(rate, 2),
            "mean_divergence": round(self.mean_divergence, 3),
            "max_divergence": self.max_divergence,
        }

    def to_json_dict(self) -> dict:
        """Full report as a JSON-serializable dict (for shadow_report.json persistence)."""
        return {
            "summary": self.summary(),
            "records": [
                {
                    "entity_id": r.entity_id,
                    "timepoint_id": r.timepoint_id,
                    "timestamp": r.timestamp.isoformat(),
                    "phi_value": round(r.phi_value, 6),
                    "adprs_band": r.adprs_band.value,
                    "actual_level": r.actual_level,
                    "divergence": r.divergence,
                    "continuous_divergence": round(r.continuous_divergence, 6),
                    "envelope_count": r.envelope_count,
                }
                for r in self.records
            ],
        }


class ShadowEvaluator:
    """
    Orchestrates shadow evaluation of ADPRS envelopes against discrete resolution.

    Usage:
        evaluator = ShadowEvaluator(run_id="run_123")
        evaluator.register_entity_envelopes("entity_1", composite)
        record = evaluator.evaluate("entity_1", "scene", "tp_1", some_datetime)
        report = evaluator.get_report()
    """

    def __init__(self, run_id: str, prediction_mode: bool = False):
        self.run_id = run_id
        self.prediction_mode = prediction_mode
        self._envelopes: Dict[str, ADPRSComposite] = {}
        self._records: List[ShadowRecord] = []
        self._prediction_log: List[Dict[str, Any]] = []

    def register_entity_envelopes(self, entity_id: str, composite: ADPRSComposite):
        """Register an ADPRS composite envelope for an entity."""
        self._envelopes[entity_id] = composite

    def register_from_metadata(self, entity_id: str, entity_metadata: Dict[str, Any]):
        """
        Load and register envelopes from entity_metadata["adprs_envelopes"].

        Expected format:
            {"adprs_envelopes": {"envelopes": [{"A": ..., "D": ..., ...}]}}
        """
        adprs_data = entity_metadata.get("adprs_envelopes")
        if not adprs_data:
            return
        composite = ADPRSComposite.from_metadata_dict(adprs_data)
        if composite.envelopes:
            self._envelopes[entity_id] = composite

    def has_envelopes(self) -> bool:
        """Check if any envelopes are registered."""
        return len(self._envelopes) > 0

    def evaluate(
        self,
        entity_id: str,
        actual_resolution_value: str,
        timepoint_id: str,
        timestamp: datetime,
    ) -> Optional[ShadowRecord]:
        """
        Evaluate ADPRS shadow for a single entity at a single timepoint.

        Args:
            entity_id: The entity to evaluate
            actual_resolution_value: Current discrete resolution (e.g., "scene", "tensor_only")
            timepoint_id: ID of the timepoint being evaluated
            timestamp: The datetime of the timepoint

        Returns:
            ShadowRecord if entity has envelopes, None otherwise.
        """
        composite = self._envelopes.get(entity_id)
        if composite is None:
            return None

        # Ensure timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        phi = composite.evaluate(timestamp)
        adprs_band = composite.evaluate_band(timestamp)

        # Map actual resolution to FidelityBand for comparison
        actual_band = _RESOLUTION_TO_BAND.get(actual_resolution_value, FidelityBand.TENSOR)
        divergence = _BAND_ORDINAL[adprs_band] - _BAND_ORDINAL[actual_band]

        # Continuous divergence: phi - midpoint of actual band (Phase 2 regression target)
        actual_midpoint = _BAND_MIDPOINT.get(actual_resolution_value, 0.1)
        continuous_divergence = phi - actual_midpoint

        record = ShadowRecord(
            entity_id=entity_id,
            timepoint_id=timepoint_id,
            timestamp=timestamp,
            phi_value=phi,
            adprs_band=adprs_band,
            actual_level=actual_resolution_value,
            divergence=divergence,
            continuous_divergence=continuous_divergence,
            envelope_count=len(composite.envelopes),
        )
        self._records.append(record)

        # Phase 3.5: In prediction_mode, log prediction BEFORE actual for validation
        if self.prediction_mode:
            self._prediction_log.append({
                "entity_id": entity_id,
                "timepoint_id": timepoint_id,
                "predicted_phi": round(phi, 6),
                "predicted_band": adprs_band.value,
                "actual_level": actual_resolution_value,
                "divergence": divergence,
            })

        # Emit synth event for monitoring (source: "adprs_shadow" to distinguish from ADSR)
        emitter = get_emitter()
        emitter.emit(
            SynthEvent.ENVELOPE_PHASE_CHANGE,
            self.run_id,
            {
                "source": "adprs_shadow",
                "shadow_mode": True,
                "entity_id": entity_id,
                "timepoint_id": timepoint_id,
                "phi": round(phi, 4),
                "adprs_band": adprs_band.value,
                "actual_level": actual_resolution_value,
                "divergence": divergence,
                "continuous_divergence": round(continuous_divergence, 4),
            },
        )

        return record

    def get_report(self) -> ShadowEvaluationReport:
        """Generate an aggregate report from all shadow evaluations."""
        report = ShadowEvaluationReport(records=list(self._records))
        report.total_evaluations = len(self._records)

        if not self._records:
            return report

        divergences = [abs(r.divergence) for r in self._records]
        report.divergent_count = sum(1 for d in divergences if d > 0)
        report.mean_divergence = sum(divergences) / len(divergences)
        report.max_divergence = max(divergences)

        return report

    def get_prediction_log(self) -> List[Dict[str, Any]]:
        """Return the prediction log (Phase 3.5 validation mode only)."""
        return list(self._prediction_log)
