"""
Unit tests for the Waveform-Driven Resolution Scheduler.

Tests scheduling, activation delta prediction, sufficiency reporting,
and the module-level predict_activation_delta convenience function —
all without LLM/DB dependencies.
"""

import math
import pytest

from synth.fidelity_envelope import (
    ADPRSEnvelope,
    ADPRSComposite,
    FidelityBand,
)
from synth.waveform_scheduler import (
    WaveformScheduler,
    predict_activation_delta,
    _evaluate_composite_at_tau,
)


# --- Helpers ---

def make_envelope(**overrides) -> ADPRSEnvelope:
    defaults = dict(
        A=1.0, D=1000.0, P=1.0, R=0, S=1.0,
        t0="2025-01-01T00:00:00+00:00", baseline=0.0,
    )
    defaults.update(overrides)
    return ADPRSEnvelope(**defaults)


def make_composite(*envelopes) -> ADPRSComposite:
    return ADPRSComposite(envelopes=list(envelopes))


def low_phi_composite() -> ADPRSComposite:
    """Envelope that stays near baseline 0.05 -> TENSOR band at most tau values."""
    return make_composite(make_envelope(A=0.0, P=0.5, S=0.1, baseline=0.05))


def high_phi_composite() -> ADPRSComposite:
    """Envelope that produces phi >= 0.8 at tau=0.25 -> TRAINED band."""
    return make_composite(make_envelope(A=1.0, P=1.0, S=1.0, baseline=0.8))


def make_scheduler(**kwargs) -> WaveformScheduler:
    return WaveformScheduler(**kwargs)


# --- TestWaveformScheduler ---

class TestWaveformScheduler:
    def test_schedule_entity_tensor_band(self):
        """Entity with low-phi envelope at tau=0.5 should land in TENSOR band."""
        scheduler = make_scheduler()
        scheduler.register_envelopes("e1", low_phi_composite())

        band = scheduler.schedule_entity("e1", tau=0.5)
        assert band == FidelityBand.TENSOR

    def test_schedule_entity_trained_band(self):
        """Entity with high-phi envelope at tau=0.25 should land in TRAINED band."""
        scheduler = make_scheduler()
        scheduler.register_envelopes("e1", high_phi_composite())

        band = scheduler.schedule_entity("e1", tau=0.25)
        assert band == FidelityBand.TRAINED

    def test_schedule_entity_no_envelope(self):
        """Entity without registered envelope returns None."""
        scheduler = make_scheduler()
        result = scheduler.schedule_entity("unknown_entity", tau=0.5)
        assert result is None

    def test_schedule_all_batch(self):
        """Batch scheduling returns a dict mapping entity_id to band."""
        scheduler = make_scheduler()
        scheduler.register_envelopes("e_low", low_phi_composite())
        scheduler.register_envelopes("e_high", high_phi_composite())

        results = scheduler.schedule_all(["e_low", "e_high", "e_missing"], tau=0.25)

        assert results["e_low"] == FidelityBand.TENSOR
        assert results["e_high"] == FidelityBand.TRAINED
        assert results["e_missing"] is None

    def test_register_from_metadata(self):
        """register_from_metadata loads envelopes from entity_metadata dict."""
        scheduler = make_scheduler()
        metadata = {
            "adprs_envelopes": {
                "envelopes": [
                    {"A": 1.0, "D": 1000.0, "P": 1.0, "R": 0, "S": 1.0,
                     "t0": "2025-01-01T00:00:00+00:00", "baseline": 0.8}
                ]
            }
        }
        scheduler.register_from_metadata("e1", metadata)
        assert scheduler.has_schedule("e1")

        band = scheduler.schedule_entity("e1", tau=0.25)
        assert band == FidelityBand.TRAINED

    def test_register_from_empty_metadata(self):
        """Empty metadata dict should not register anything."""
        scheduler = make_scheduler()
        scheduler.register_from_metadata("e1", {})
        assert not scheduler.has_schedule("e1")

    def test_has_schedule(self):
        """has_schedule returns True for registered entities, False otherwise."""
        scheduler = make_scheduler()
        assert not scheduler.has_schedule("e1")

        scheduler.register_envelopes("e1", high_phi_composite())
        assert scheduler.has_schedule("e1")
        assert not scheduler.has_schedule("e2")


# --- TestPredictActivationDelta ---

class TestPredictActivationDelta:
    def test_predict_returns_dict(self):
        """predict_activation_delta returns dict with expected keys."""
        scheduler = make_scheduler()
        scheduler.register_envelopes("e1", high_phi_composite())

        result = scheduler.predict_activation_delta("e1", current_tau=0.1, next_tau=0.25)

        assert isinstance(result, dict)
        assert "predicted_phi" in result
        assert "delta_phi" in result
        assert "predicted_band" in result

    def test_predict_no_envelope_returns_none(self):
        """Unregistered entity returns None."""
        scheduler = make_scheduler()
        result = scheduler.predict_activation_delta("ghost", current_tau=0.0, next_tau=0.5)
        assert result is None

    def test_predict_delta_positive_when_phi_increases(self):
        """Positive delta when moving from low-phi tau to high-phi tau.

        With A=1.0, P=1.0, S=1.0, baseline=0.0:
          tau=0.0: oscillation=sin(0)=0, phi=0.0
          tau=0.25: oscillation=sin(pi/2)=1.0, decay=1.0, phi=1.0
        Delta should be positive (~1.0).
        """
        scheduler = make_scheduler()
        comp = make_composite(make_envelope(A=1.0, P=1.0, S=1.0, baseline=0.0))
        scheduler.register_envelopes("e1", comp)

        result = scheduler.predict_activation_delta("e1", current_tau=0.0, next_tau=0.25)
        assert result["delta_phi"] > 0.0
        assert result["predicted_phi"] > 0.9  # phi at tau=0.25 should be ~1.0

    def test_predict_delta_negative_when_phi_decreases(self):
        """Negative delta when moving from peak tau to tail tau.

        With A=0.0, P=1.0, S=1.0, baseline=0.0:
          tau=0.25: peak region
          tau=0.9: near end, heavy decay from (1-A)*3=3 exponent
        Delta should be negative.
        """
        scheduler = make_scheduler()
        comp = make_composite(make_envelope(A=0.0, P=1.0, S=1.0, baseline=0.0))
        scheduler.register_envelopes("e1", comp)

        phi_early = _evaluate_composite_at_tau(
            comp, 0.25
        )
        phi_late = _evaluate_composite_at_tau(
            comp, 0.9
        )
        # Verify our assumption: early phi is higher than late phi
        assert phi_early > phi_late

        result = scheduler.predict_activation_delta("e1", current_tau=0.25, next_tau=0.9)
        assert result["delta_phi"] < 0.0


# --- TestSufficiencyReport ---

class TestSufficiencyReport:
    def test_empty_report(self):
        """No predictions or actuals should produce sane defaults."""
        scheduler = make_scheduler()
        report = scheduler.sufficiency_report()

        assert report["total_predictions"] == 0
        assert report["total_actuals"] == 0
        assert report["matched"] == 0
        assert report["wsr"] is None  # no actuals => None
        assert report["skipped_llm_calls"] == 0

    def test_perfect_predictions(self):
        """All predictions match actuals within epsilon -> WSR = 1.0."""
        scheduler = make_scheduler(epsilon=0.1)

        scheduler.record_prediction("e1", tau=0.5, predicted_phi=0.3, predicted_band=FidelityBand.SCENE)
        scheduler.record_prediction("e2", tau=0.5, predicted_phi=0.7, predicted_band=FidelityBand.DIALOG)

        # Actuals match within epsilon
        scheduler.record_actual("e1", tau=0.5, actual_activation=0.32)
        scheduler.record_actual("e2", tau=0.5, actual_activation=0.68)

        report = scheduler.sufficiency_report()
        assert report["total_predictions"] == 2
        assert report["total_actuals"] == 2
        assert report["matched"] == 2
        assert report["wsr"] == 1.0

    def test_all_mismatches(self):
        """No predictions match actuals -> WSR = 0.0."""
        scheduler = make_scheduler(epsilon=0.05)

        scheduler.record_prediction("e1", tau=0.5, predicted_phi=0.1, predicted_band=FidelityBand.TENSOR)
        scheduler.record_prediction("e2", tau=0.5, predicted_phi=0.9, predicted_band=FidelityBand.TRAINED)

        # Actuals are far from predictions
        scheduler.record_actual("e1", tau=0.5, actual_activation=0.8)
        scheduler.record_actual("e2", tau=0.5, actual_activation=0.1)

        report = scheduler.sufficiency_report()
        assert report["matched"] == 0
        assert report["wsr"] == 0.0

    def test_partial_match(self):
        """Some predictions match, some do not -> correct ratio."""
        scheduler = make_scheduler(epsilon=0.1)

        # Prediction 1: matches
        scheduler.record_prediction("e1", tau=0.5, predicted_phi=0.5, predicted_band=FidelityBand.GRAPH)
        scheduler.record_actual("e1", tau=0.5, actual_activation=0.52)

        # Prediction 2: does not match
        scheduler.record_prediction("e2", tau=0.5, predicted_phi=0.2, predicted_band=FidelityBand.SCENE)
        scheduler.record_actual("e2", tau=0.5, actual_activation=0.9)

        report = scheduler.sufficiency_report()
        assert report["matched"] == 1
        assert report["total_actuals"] == 2
        assert report["wsr"] == pytest.approx(0.5)

    def test_skipped_llm_tracking(self):
        """Counts TENSOR and SCENE predictions as skipped LLM calls."""
        scheduler = make_scheduler()

        scheduler.record_prediction("e1", tau=0.1, predicted_phi=0.05, predicted_band=FidelityBand.TENSOR)
        scheduler.record_prediction("e2", tau=0.2, predicted_phi=0.25, predicted_band=FidelityBand.SCENE)
        scheduler.record_prediction("e3", tau=0.5, predicted_phi=0.5, predicted_band=FidelityBand.GRAPH)
        scheduler.record_prediction("e4", tau=0.7, predicted_phi=0.9, predicted_band=FidelityBand.TRAINED)

        report = scheduler.sufficiency_report()
        assert report["skipped_llm_calls"] == 2  # TENSOR + SCENE only


# --- TestModuleLevelPredictDelta ---

class TestModuleLevelPredictDelta:
    def test_module_level_predict_returns_dict(self):
        """Module-level predict_activation_delta returns dict with expected keys."""
        comp = high_phi_composite()
        result = predict_activation_delta(comp, current_tau=0.0, next_tau=0.25)

        assert isinstance(result, dict)
        assert "predicted_phi" in result
        assert "delta_phi" in result
        assert "predicted_band" in result

    def test_module_level_predict_phi_values(self):
        """Module-level function computes correct phi and band at tau=0.25."""
        comp = make_composite(make_envelope(A=1.0, P=1.0, S=1.0, baseline=0.0))

        result = predict_activation_delta(comp, current_tau=0.0, next_tau=0.25)

        # At tau=0.25: sin(pi/2)=1, decay=(0.75)^0=1, phi=1.0
        assert result["predicted_phi"] == pytest.approx(1.0, abs=0.01)
        assert result["predicted_band"] == FidelityBand.TRAINED.value

    def test_module_level_predict_delta_consistency(self):
        """Delta equals next_phi - current_phi."""
        comp = make_composite(make_envelope(A=1.0, P=1.0, S=1.0, baseline=0.0))

        current_tau = 0.1
        next_tau = 0.25

        result = predict_activation_delta(comp, current_tau, next_tau)

        expected_current = _evaluate_composite_at_tau(comp, current_tau)
        expected_next = _evaluate_composite_at_tau(comp, next_tau)
        expected_delta = expected_next - expected_current

        assert result["predicted_phi"] == pytest.approx(expected_next, abs=1e-9)
        assert result["delta_phi"] == pytest.approx(expected_delta, abs=1e-9)

    def test_module_level_predict_with_composite(self):
        """Module-level function works with multi-envelope ADPRSComposite."""
        comp = make_composite(
            make_envelope(A=0.0, P=0.5, S=0.1, baseline=0.05),  # low phi
            make_envelope(A=1.0, P=1.0, S=1.0, baseline=0.8),   # high phi
        )

        result = predict_activation_delta(comp, current_tau=0.0, next_tau=0.25)

        # The composite takes max across envelopes, so the high-phi envelope
        # dominates: at tau=0.25 it produces phi ~1.0
        assert result["predicted_phi"] >= 0.8
        assert result["predicted_band"] == FidelityBand.TRAINED.value
