"""
Waveform-Driven Resolution Scheduler (Phase 3: The Compute Gate)

Evaluates fitted ADPRS envelopes to determine which resolution level each
(entity, timepoint) pair should receive. The scheduler is the brain that
decides "should we call the LLM or just use the waveform prediction?"

Resolution band -> compute action mapping:
    [0.0, 0.2) TENSOR  - Pure waveform prediction. No LLM.
    [0.2, 0.4) SCENE   - Lightweight template-based generation. Minimal LLM.
    [0.4, 0.6) GRAPH   - Waveform + relationship graph lookup. LLM for graph updates only.
    [0.6, 0.8) DIALOG  - Selective LLM for dialog synthesis.
    [0.8, 1.0] TRAINED - Full LLM simulation. "Surprise zone."

Part of the SynthasAIzer control paradigm.
"""

import logging
from typing import Dict, List, Optional, Any

from synth.fidelity_envelope import (
    ADPRSComposite,
    ADPRSEnvelope,
    FidelityBand,
    phi_to_resolution_band,
)

logger = logging.getLogger(__name__)


class WaveformScheduler:
    """
    Evaluates ADPRS envelopes to schedule resolution levels per entity.

    Tracks predictions vs actuals to compute the Waveform Sufficiency Ratio
    (WSR): the fraction of predictions that were accurate enough to skip
    the LLM entirely.

    Usage:
        scheduler = WaveformScheduler(epsilon=0.1)
        scheduler.register_envelopes("entity_1", composite)
        band = scheduler.schedule_entity("entity_1", tau=0.35)
        # band == FidelityBand.SCENE -> use template, skip LLM
    """

    def __init__(self, epsilon: float = 0.1):
        self.epsilon = epsilon
        self._envelopes: Dict[str, ADPRSComposite] = {}
        self._predictions: List[dict] = []
        self._actuals: List[dict] = []

    def register_envelopes(self, entity_id: str, composite: ADPRSComposite):
        """Register ADPRS envelopes for an entity."""
        self._envelopes[entity_id] = composite

    def register_from_metadata(self, entity_id: str, entity_metadata: dict):
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

    def has_schedule(self, entity_id: str) -> bool:
        """Check if entity has registered envelopes."""
        return entity_id in self._envelopes

    def schedule_entity(self, entity_id: str, tau: float) -> Optional[FidelityBand]:
        """
        Evaluate phi at tau for an entity and return the FidelityBand.

        tau is normalized time in [0, 1] within the envelope's duration.
        Returns None if the entity has no registered envelopes.
        """
        composite = self._envelopes.get(entity_id)
        if composite is None:
            return None

        # Evaluate using the normalized tau directly via the waveform math.
        # ADPRSComposite.evaluate() takes a datetime, but we need tau-based
        # evaluation. Compute phi from the first envelope's parameters using
        # the same math as adprs_waveform.
        phi = _evaluate_composite_at_tau(composite, tau)
        return phi_to_resolution_band(phi)

    def schedule_all(
        self, entity_ids: List[str], tau: float
    ) -> Dict[str, Optional[FidelityBand]]:
        """Batch schedule: evaluate all entities at a given tau."""
        return {eid: self.schedule_entity(eid, tau) for eid in entity_ids}

    def predict_activation_delta(
        self, entity_id: str, current_tau: float, next_tau: float
    ) -> Optional[Dict[str, float]]:
        """
        Predict cognitive tensor changes from waveform without LLM.

        Returns dict with predicted_phi, delta_phi, predicted_band.
        Returns None if entity not registered.
        """
        composite = self._envelopes.get(entity_id)
        if composite is None:
            return None
        return predict_activation_delta(composite, current_tau, next_tau)

    def record_prediction(
        self,
        entity_id: str,
        tau: float,
        predicted_phi: float,
        predicted_band: FidelityBand,
    ):
        """Record a prediction for WSR tracking."""
        self._predictions.append({
            "entity_id": entity_id,
            "tau": tau,
            "predicted_phi": predicted_phi,
            "predicted_band": predicted_band,
        })

    def record_actual(
        self, entity_id: str, tau: float, actual_activation: float
    ):
        """Record actual result when LLM is called."""
        self._actuals.append({
            "entity_id": entity_id,
            "tau": tau,
            "actual_activation": actual_activation,
        })

    def sufficiency_report(self) -> dict:
        """
        Compute Waveform Sufficiency Ratio and return report.

        WSR = matched / total_actuals, where matched means
        |predicted_phi - actual_activation| < epsilon for predictions
        that have a corresponding actual at the same (entity_id, tau).
        """
        total_predictions = len(self._predictions)
        total_actuals = len(self._actuals)

        # Build lookup of actuals by (entity_id, tau)
        actual_lookup: Dict[tuple, float] = {}
        for a in self._actuals:
            actual_lookup[(a["entity_id"], a["tau"])] = a["actual_activation"]

        # Count matches
        matched = 0
        for p in self._predictions:
            key = (p["entity_id"], p["tau"])
            if key in actual_lookup:
                if abs(p["predicted_phi"] - actual_lookup[key]) < self.epsilon:
                    matched += 1

        # Count skipped LLM calls (TENSOR or SCENE predictions)
        skipped = sum(
            1 for p in self._predictions
            if p["predicted_band"] in (FidelityBand.TENSOR, FidelityBand.SCENE)
        )

        wsr = matched / total_actuals if total_actuals > 0 else None

        return {
            "total_predictions": total_predictions,
            "total_actuals": total_actuals,
            "matched": matched,
            "wsr": wsr,
            "skipped_llm_calls": skipped,
            "epsilon": self.epsilon,
        }


def _evaluate_composite_at_tau(composite: ADPRSComposite, tau: float) -> float:
    """
    Evaluate an ADPRSComposite at normalized tau without requiring a datetime.

    Reproduces the core ADPRS waveform math:
        phi(tau) = |sin(tau * 2pi * P)| * (1 - tau)^((1 - A) * 3) * S + (1 - S) * baseline

    Returns max across all envelopes.
    """
    import math

    if not composite.envelopes:
        return 0.0

    values = []
    for env in composite.envelopes:
        tau_clamped = max(0.0, min(1.0, tau))
        oscillation = abs(math.sin(tau_clamped * 2.0 * math.pi * env.P))
        decay = (1.0 - tau_clamped) ** ((1.0 - env.A) * 3.0) if tau_clamped < 1.0 else 0.0
        phi = oscillation * decay * env.S + (1.0 - env.S) * env.baseline
        values.append(max(0.0, min(1.0, phi)))

    return max(values)


def predict_activation_delta(
    composite: ADPRSComposite, current_tau: float, next_tau: float
) -> Dict[str, float]:
    """
    Predict cognitive tensor changes from waveform without LLM.

    Module-level convenience function that takes an ADPRSComposite directly.

    Returns dict with predicted_phi, delta_phi, predicted_band.
    """
    current_phi = _evaluate_composite_at_tau(composite, current_tau)
    next_phi = _evaluate_composite_at_tau(composite, next_tau)
    delta = next_phi - current_phi
    band = phi_to_resolution_band(next_phi)

    return {
        "predicted_phi": next_phi,
        "delta_phi": delta,
        "predicted_band": band.value,
    }
