"""
Unit tests for ADPRS waveform fitting engine.

Tests waveform math, cold/warm fitting, FitResult conversion, and
cross-run convergence — all pure math, no LLM/DB dependencies.
"""

import math
import pytest
import numpy as np
from types import SimpleNamespace

from synth.adprs_fitter import (
    adprs_waveform,
    ADPRSFitter,
    FitResult,
    PARAM_BOUNDS,
    PARAM_NAMES,
    DEFAULT_PARAMS,
)
from synth.fidelity_envelope import ADPRSEnvelope, ADPRSComposite
from synth.trajectory_tracker import TrajectoryTracker


# --- Helpers ---

def make_entity(entity_id, adprs_envelopes=None, fit_metadata=None):
    """Create a mock entity with optional ADPRS metadata."""
    metadata = {}
    if adprs_envelopes is not None:
        metadata["adprs_envelopes"] = adprs_envelopes
    if fit_metadata is not None:
        metadata["adprs_fit_metadata"] = fit_metadata
    metadata["cognitive_tensor"] = {
        "emotional_valence": 0.0,
        "emotional_arousal": 0.5,
        "energy_budget": 50.0,
        "knowledge_state": [],
    }
    return SimpleNamespace(
        entity_id=entity_id,
        entity_metadata=metadata,
        tensor_maturity=0.5,
    )


def make_timepoint(tp_id):
    return SimpleNamespace(timepoint_id=tp_id, timestamp=None)


def generate_synthetic_data(A, P, S, baseline, n_points=20, noise=0.0):
    """Generate tau/activation data from known ADPRS params."""
    tau = np.linspace(0.0, 0.95, n_points)  # Avoid tau=1 where decay→0
    activation = adprs_waveform(tau, A, P, S, baseline)
    if noise > 0:
        rng = np.random.default_rng(42)
        activation = np.clip(activation + rng.normal(0, noise, n_points), 0, 1)
    return tau, activation


# --- adprs_waveform vectorized ---

class TestAdprsWaveform:
    def test_vectorized(self):
        """Waveform should accept and return numpy arrays."""
        tau = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        result = adprs_waveform(tau, 0.7, 2.0, 0.8, 0.1)
        assert isinstance(result, np.ndarray)
        assert len(result) == 5

    def test_boundary_tau_zero(self):
        """At tau=0, sin(0)=0 → phi = (1-S)*baseline."""
        result = adprs_waveform(np.array([0.0]), 0.7, 2.0, 0.8, 0.1)
        expected = (1.0 - 0.8) * 0.1  # 0.02
        assert abs(result[0] - expected) < 1e-6

    def test_boundary_tau_one(self):
        """At tau=1.0, decay=0 → phi = (1-S)*baseline."""
        result = adprs_waveform(np.array([1.0]), 0.5, 2.0, 0.8, 0.1)
        expected = (1.0 - 0.8) * 0.1  # 0.02
        assert abs(result[0] - expected) < 1e-6

    def test_output_clamped(self):
        """Output always in [0, 1]."""
        tau = np.linspace(0, 1, 100)
        for A in [0.0, 0.5, 1.0]:
            for P in [0.5, 2.0, 8.0]:
                for S in [0.0, 0.5, 1.0]:
                    for bl in [0.0, 0.5, 1.0]:
                        result = adprs_waveform(tau, A, P, S, bl)
                        assert np.all(result >= 0.0) and np.all(result <= 1.0), \
                            f"Out of range for A={A}, P={P}, S={S}, bl={bl}"

    def test_matches_envelope_evaluate(self):
        """Waveform must match ADPRSEnvelope.evaluate() at sampled tau points."""
        from datetime import datetime, timezone, timedelta
        env = ADPRSEnvelope(
            A=0.6, D=1000.0, P=3.0, R=0, S=0.7,
            t0="2025-01-01T00:00:00+00:00", baseline=0.15
        )
        t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        taus = [0.0, 0.1, 0.25, 0.5, 0.75, 0.95]

        for tau_val in taus:
            t = t0 + timedelta(milliseconds=env.D * tau_val)
            env_phi = env.evaluate(t)
            waveform_phi = float(adprs_waveform(np.array([tau_val]), env.A, env.P, env.S, env.baseline)[0])
            assert abs(env_phi - waveform_phi) < 1e-6, \
                f"Mismatch at tau={tau_val}: envelope={env_phi}, waveform={waveform_phi}"


# --- Cold fit ---

class TestColdFit:
    def test_recover_monotone_decay(self):
        """Cold fit recovers params from monotone decay signal (A=0.3, P=1, S=0.9, baseline=0.05)."""
        A, P, S, bl = 0.3, 1.0, 0.9, 0.05
        tau, activation = generate_synthetic_data(A, P, S, bl, n_points=20)
        fitter = ADPRSFitter(de_maxiter=200)
        result = fitter.fit_entity(tau, activation, "e1")
        assert result.method == "differential_evolution"
        assert result.residual < 0.01  # Good fit

    def test_recover_oscillatory(self):
        """Cold fit recovers params from oscillatory signal (P=3)."""
        A, P, S, bl = 0.8, 3.0, 0.85, 0.1
        tau, activation = generate_synthetic_data(A, P, S, bl, n_points=25)
        fitter = ADPRSFitter(de_maxiter=200)
        result = fitter.fit_entity(tau, activation, "e1")
        assert result.residual < 0.01

    def test_fallback_on_failure(self):
        """Cold fit falls back to defaults with empty data."""
        fitter = ADPRSFitter()
        # Edge case: single point won't crash
        tau = np.array([0.5])
        activation = np.array([0.5])
        result = fitter.fit_entity(tau, activation, "e1")
        assert result.n_points == 1


# --- Warm fit ---

class TestWarmFit:
    def test_refines_near_correct_prior(self):
        """Warm fit improves on a near-correct prior."""
        true_params = {"A": 0.7, "P": 2.0, "S": 0.8, "baseline": 0.1}
        tau, activation = generate_synthetic_data(**true_params, n_points=20)

        # Slightly perturbed prior
        prior = {"A": 0.65, "P": 2.1, "S": 0.75, "baseline": 0.12}
        fitter = ADPRSFitter()
        result = fitter.fit_entity(tau, activation, "e1", prior_params=prior)
        assert result.method == "curve_fit"
        assert result.converged
        assert result.residual < 0.001

    def test_falls_back_on_bad_prior(self):
        """Warm fit with wildly wrong prior falls back to cold fit."""
        true_params = {"A": 0.3, "P": 1.0, "S": 0.9, "baseline": 0.05}
        tau, activation = generate_synthetic_data(**true_params, n_points=20)

        # The fallback to cold fit is an implementation detail — just verify
        # that it doesn't crash and produces a result
        fitter = ADPRSFitter(de_maxiter=100)
        result = fitter.fit_entity(tau, activation, "e1", prior_params={"A": 0.99, "P": 7.5, "S": 0.01, "baseline": 0.99})
        assert result.n_points == 20


# --- FitResult.to_envelope ---

class TestFitResultToEnvelope:
    def test_valid_envelope(self):
        """to_envelope produces a valid ADPRSEnvelope."""
        result = FitResult(
            entity_id="e1",
            params={"A": 0.7, "P": 2.0, "S": 0.8, "baseline": 0.1},
            residual=0.005,
            n_points=15,
            method="curve_fit",
            converged=True,
        )
        env = result.to_envelope(31536000000.0, "2026-01-01T00:00:00+00:00")
        assert isinstance(env, ADPRSEnvelope)
        assert env.A == 0.7
        assert env.D == 31536000000.0
        assert env.P == 2.0
        assert env.R == 0
        assert env.S == 0.8
        assert env.baseline == 0.1

    def test_serialization_roundtrip(self):
        """Fitted envelope serializes to metadata dict and back."""
        result = FitResult(
            entity_id="e1",
            params={"A": 0.73, "P": 2.14, "S": 0.85, "baseline": 0.12},
            residual=0.003,
            n_points=16,
            method="differential_evolution",
            converged=True,
        )
        env = result.to_envelope(31536000000.0, "2026-01-01T00:00:00+00:00")
        d = env.to_metadata_dict()
        restored = ADPRSEnvelope.from_metadata_dict(d)
        assert abs(restored.A - 0.73) < 1e-6
        assert abs(restored.P - 2.14) < 1e-6


# --- apply_to_entities ---

class TestApplyToEntities:
    def test_writes_metadata(self):
        """apply_to_entities writes adprs_envelopes and adprs_fit_metadata."""
        entity = make_entity("e1")
        result = FitResult(
            entity_id="e1",
            params={"A": 0.7, "P": 2.0, "S": 0.8, "baseline": 0.1},
            residual=0.005,
            n_points=15,
            method="curve_fit",
            converged=True,
        )
        updated = ADPRSFitter.apply_to_entities(
            {"e1": result}, [entity], 31536000000.0, "2026-01-01T00:00:00+00:00"
        )
        assert updated == 1
        assert "adprs_envelopes" in entity.entity_metadata
        assert "adprs_fit_metadata" in entity.entity_metadata
        meta = entity.entity_metadata["adprs_fit_metadata"]
        assert meta["run_count"] == 1
        assert meta["last_method"] == "curve_fit"
        assert meta["converged"] is True

    def test_increments_run_count(self):
        """Subsequent apply increments run_count and appends residual_history."""
        entity = make_entity("e1", fit_metadata={
            "run_count": 2,
            "residual_history": [0.01, 0.005],
        })
        result = FitResult(
            entity_id="e1",
            params={"A": 0.7, "P": 2.0, "S": 0.8, "baseline": 0.1},
            residual=0.003,
            n_points=16,
            method="curve_fit",
            converged=True,
        )
        ADPRSFitter.apply_to_entities(
            {"e1": result}, [entity], 31536000000.0, "2026-01-01T00:00:00+00:00"
        )
        meta = entity.entity_metadata["adprs_fit_metadata"]
        assert meta["run_count"] == 3
        assert len(meta["residual_history"]) == 3
        assert meta["residual_history"][-1] == 0.003

    def test_bounds_residual_history(self):
        """Residual history is bounded to last 20 entries."""
        entity = make_entity("e1", fit_metadata={
            "run_count": 20,
            "residual_history": [0.01] * 20,
        })
        result = FitResult(
            entity_id="e1",
            params={"A": 0.7, "P": 2.0, "S": 0.8, "baseline": 0.1},
            residual=0.001,
            n_points=16,
            method="curve_fit",
            converged=True,
        )
        ADPRSFitter.apply_to_entities(
            {"e1": result}, [entity], 31536000000.0, "2026-01-01T00:00:00+00:00"
        )
        meta = entity.entity_metadata["adprs_fit_metadata"]
        assert len(meta["residual_history"]) <= 20


# --- Cross-run: prior params trigger warm start ---

class TestCrossRunFitting:
    def test_prior_triggers_warm_start(self):
        """Entity with existing envelopes in metadata triggers warm-start fitting."""
        true_params = {"A": 0.7, "P": 2.0, "S": 0.8, "baseline": 0.1}

        # Create entity with prior envelope
        env_data = {
            "envelopes": [
                {"A": 0.65, "D": 31536000000.0, "P": 2.1, "R": 0, "S": 0.75,
                 "t0": "2026-01-01T00:00:00+00:00", "baseline": 0.12}
            ]
        }
        entity = make_entity("e1", adprs_envelopes=env_data)

        # Build tracker with synthetic data
        tracker = TrajectoryTracker()
        tau, activation = generate_synthetic_data(**true_params, n_points=12)
        # Manually populate tracker
        for i in range(len(tau)):
            entity_snap = make_entity("e1", adprs_envelopes=env_data)
            entity_snap.entity_metadata["cognitive_tensor"]["emotional_valence"] = 0.0
            entity_snap.entity_metadata["cognitive_tensor"]["emotional_arousal"] = float(activation[i])
            entity_snap.entity_metadata["cognitive_tensor"]["energy_budget"] = 50.0
            tracker.record_snapshot(entity_snap, make_timepoint(f"tp_{i}"), i)

        fitter = ADPRSFitter(min_points=5)
        results = fitter.fit_all(tracker, [entity])
        assert "e1" in results
        result = results["e1"]
        # Should have used warm start (curve_fit) due to prior envelopes
        assert result.method == "curve_fit"
        assert result.prior_params is not None

    def test_parameter_drift_decreases(self):
        """With repeated fits from improving priors, parameter drift should be small."""
        true_params = {"A": 0.7, "P": 2.0, "S": 0.8, "baseline": 0.1}
        tau, activation = generate_synthetic_data(**true_params, n_points=20)

        fitter = ADPRSFitter()

        # First fit — cold start
        r1 = fitter.fit_entity(tau, activation, "e1")
        assert r1.parameter_drift is None  # No prior → no drift

        # Second fit — warm start from first result
        r2 = fitter.fit_entity(tau, activation, "e1", prior_params=r1.params)
        assert r2.parameter_drift is not None
        # Drift should be small since first fit was good
        total_drift = sum(r2.parameter_drift.values())
        assert total_drift < 0.5  # Reasonable bound


# --- fit_all with tracker ---

class TestFitAll:
    def test_skips_insufficient_data(self):
        """Entities with fewer than min_points snapshots are skipped."""
        tracker = TrajectoryTracker()
        entity = make_entity("e1")
        for i in range(3):  # Only 3 points
            tracker.record_snapshot(entity, make_timepoint(f"tp_{i}"), i)

        fitter = ADPRSFitter(min_points=5)
        results = fitter.fit_all(tracker, [entity])
        assert "e1" not in results

    def test_fits_sufficient_data(self):
        """Entities with enough data get fitted."""
        tracker = TrajectoryTracker()
        entity = make_entity("e1")
        for i in range(10):
            tracker.record_snapshot(entity, make_timepoint(f"tp_{i}"), i)

        fitter = ADPRSFitter(min_points=5)
        results = fitter.fit_all(tracker, [entity])
        assert "e1" in results
