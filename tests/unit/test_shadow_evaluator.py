"""
Unit tests for ADPRS shadow evaluator.

Tests registration, evaluation, divergence calculation, report aggregation,
and synth event emission — all without LLM/DB dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from synth.fidelity_envelope import (
    ADPRSEnvelope,
    ADPRSComposite,
    FidelityBand,
)
from synth.shadow_evaluator import (
    ShadowEvaluator,
    ShadowRecord,
    ShadowEvaluationReport,
)


# --- Helpers ---

def make_t0() -> datetime:
    return datetime(2025, 1, 1, tzinfo=timezone.utc)


def make_evaluator(run_id: str = "test_run") -> ShadowEvaluator:
    return ShadowEvaluator(run_id=run_id)


def make_simple_envelope(**overrides) -> ADPRSEnvelope:
    defaults = dict(
        A=1.0, D=1000.0, P=1.0, R=0, S=1.0,
        t0="2025-01-01T00:00:00+00:00", baseline=0.0,
    )
    defaults.update(overrides)
    return ADPRSEnvelope(**defaults)


def make_composite(*envelopes) -> ADPRSComposite:
    return ADPRSComposite(envelopes=list(envelopes))


# --- Registration ---

class TestRegistration:
    def test_register_entity_envelopes(self):
        ev = make_evaluator()
        comp = make_composite(make_simple_envelope())
        ev.register_entity_envelopes("entity_1", comp)
        assert ev.has_envelopes()

    def test_register_from_metadata(self):
        ev = make_evaluator()
        metadata = {
            "adprs_envelopes": {
                "envelopes": [
                    {"A": 0.7, "D": 1000.0, "P": 2.0, "R": 0, "S": 0.8,
                     "t0": "2025-01-01T00:00:00+00:00", "baseline": 0.1}
                ]
            }
        }
        ev.register_from_metadata("entity_1", metadata)
        assert ev.has_envelopes()

    def test_register_from_empty_metadata(self):
        ev = make_evaluator()
        ev.register_from_metadata("entity_1", {})
        assert not ev.has_envelopes()

    def test_register_from_metadata_no_envelopes_key(self):
        ev = make_evaluator()
        ev.register_from_metadata("entity_1", {"other_key": "value"})
        assert not ev.has_envelopes()


# --- Evaluation ---

class TestEvaluation:
    def test_entity_without_envelopes_returns_none(self):
        ev = make_evaluator()
        result = ev.evaluate("unknown_entity", "scene", "tp_1", make_t0())
        assert result is None

    def test_returns_correct_band(self):
        ev = make_evaluator()
        # S=1, A=1, P=1 at tau=0.25 → phi=1.0 → TRAINED
        env = make_simple_envelope()
        ev.register_entity_envelopes("e1", make_composite(env))
        t = make_t0() + timedelta(milliseconds=250.0)  # tau=0.25 peak
        record = ev.evaluate("e1", "scene", "tp_1", t)
        assert record is not None
        assert record.adprs_band == FidelityBand.TRAINED
        assert record.phi_value > 0.9

    def test_divergence_positive_when_adprs_higher(self):
        """ADPRS recommends higher resolution than actual → positive divergence."""
        ev = make_evaluator()
        env = make_simple_envelope()
        ev.register_entity_envelopes("e1", make_composite(env))
        t = make_t0() + timedelta(milliseconds=250.0)  # phi ≈ 1.0 → TRAINED
        record = ev.evaluate("e1", "tensor_only", "tp_1", t)
        assert record.divergence > 0  # TRAINED(4) - TENSOR(0) = 4

    def test_divergence_negative_when_adprs_lower(self):
        """ADPRS recommends lower resolution than actual → negative divergence."""
        ev = make_evaluator()
        # Low-output envelope: S=0, baseline=0.05 → TENSOR band
        env = make_simple_envelope(S=0.0, baseline=0.05)
        ev.register_entity_envelopes("e1", make_composite(env))
        t = make_t0() + timedelta(milliseconds=250.0)
        record = ev.evaluate("e1", "trained", "tp_1", t)
        assert record.divergence < 0  # TENSOR(0) - TRAINED(4) = -4

    def test_divergence_zero_when_match(self):
        """Zero divergence when ADPRS band matches actual."""
        ev = make_evaluator()
        # Baseline=0.05 → TENSOR band
        env = make_simple_envelope(S=0.0, baseline=0.05)
        ev.register_entity_envelopes("e1", make_composite(env))
        t = make_t0() + timedelta(milliseconds=250.0)
        record = ev.evaluate("e1", "tensor_only", "tp_1", t)
        assert record.divergence == 0

    def test_continuous_divergence(self):
        """continuous_divergence = phi - midpoint_of_actual_band."""
        ev = make_evaluator()
        env = make_simple_envelope()
        ev.register_entity_envelopes("e1", make_composite(env))
        t = make_t0() + timedelta(milliseconds=250.0)  # phi ≈ 1.0
        # actual="scene" → midpoint=0.3, so continuous_divergence ≈ 1.0 - 0.3 = 0.7
        record = ev.evaluate("e1", "scene", "tp_1", t)
        assert abs(record.continuous_divergence - (record.phi_value - 0.3)) < 1e-6


# --- Report aggregation ---

class TestReport:
    def test_empty_report(self):
        ev = make_evaluator()
        report = ev.get_report()
        assert report.total_evaluations == 0
        assert report.divergent_count == 0
        assert report.mean_divergence == 0.0
        assert report.max_divergence == 0

    def test_report_totals(self):
        ev = make_evaluator()
        env = make_simple_envelope()
        ev.register_entity_envelopes("e1", make_composite(env))

        # Two evaluations at peak
        t = make_t0() + timedelta(milliseconds=250.0)
        ev.evaluate("e1", "scene", "tp_1", t)
        ev.evaluate("e1", "tensor_only", "tp_2", t)

        report = ev.get_report()
        assert report.total_evaluations == 2
        assert report.divergent_count == 2  # Both diverge from TRAINED

    def test_report_mean_divergence(self):
        ev = make_evaluator()
        env = make_simple_envelope()
        ev.register_entity_envelopes("e1", make_composite(env))

        t = make_t0() + timedelta(milliseconds=250.0)
        # TRAINED - SCENE(1) = 3
        ev.evaluate("e1", "scene", "tp_1", t)
        # TRAINED - TENSOR(0) = 4
        ev.evaluate("e1", "tensor_only", "tp_2", t)

        report = ev.get_report()
        assert report.mean_divergence == 3.5  # (3 + 4) / 2
        assert report.max_divergence == 4

    def test_report_summary_dict(self):
        ev = make_evaluator()
        report = ev.get_report()
        summary = report.summary()
        assert "total_evaluations" in summary
        assert "divergent_count" in summary
        assert "divergence_rate_pct" in summary
        assert "mean_divergence" in summary
        assert "max_divergence" in summary


# --- Event emission ---

class TestEventEmission:
    def test_emits_envelope_phase_change_on_evaluate(self):
        """Shadow evaluation should emit ENVELOPE_PHASE_CHANGE event."""
        ev = make_evaluator()
        env = make_simple_envelope()
        ev.register_entity_envelopes("e1", make_composite(env))

        mock_emitter = MagicMock()
        mock_emitter.enabled = True

        with patch("synth.shadow_evaluator.get_emitter", return_value=mock_emitter):
            t = make_t0() + timedelta(milliseconds=250.0)
            ev.evaluate("e1", "scene", "tp_1", t)

        mock_emitter.emit.assert_called_once()
        call_args = mock_emitter.emit.call_args
        from synth.events import SynthEvent
        assert call_args[0][0] == SynthEvent.ENVELOPE_PHASE_CHANGE
        event_data = call_args[0][2]
        assert event_data["shadow_mode"] is True
        assert event_data["source"] == "adprs_shadow"
        assert event_data["entity_id"] == "e1"
        assert "phi" in event_data
        assert "divergence" in event_data
        assert "continuous_divergence" in event_data


# --- Report JSON persistence ---

class TestReportPersistence:
    def test_to_json_dict(self):
        """Report should serialize to a JSON-safe dict with summary + records."""
        import json
        ev = make_evaluator()
        env = make_simple_envelope()
        ev.register_entity_envelopes("e1", make_composite(env))
        t = make_t0() + timedelta(milliseconds=250.0)
        ev.evaluate("e1", "scene", "tp_1", t)

        report = ev.get_report()
        d = report.to_json_dict()
        assert "summary" in d
        assert "records" in d
        assert len(d["records"]) == 1
        assert d["records"][0]["entity_id"] == "e1"
        assert "continuous_divergence" in d["records"][0]
        # Should be JSON-serializable
        json.dumps(d)
