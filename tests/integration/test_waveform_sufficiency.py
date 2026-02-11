"""
Phase 3.5: Predictive Validation — Waveform Sufficiency Tests

Proves empirically that waveform prediction works via a two-run protocol:
  Run 1: Generate a trajectory (synthetic), fit waveforms.
  Run 2: At each timepoint, record the waveform's prediction BEFORE the actual
         value. Measure delta.

Key metric: WSR (Waveform Sufficiency Ratio) = fraction of (entity, timepoint)
pairs where |predicted - actual| < epsilon.
"""

import math
import numpy as np
import pytest

from synth.adprs_fitter import ADPRSFitter, adprs_waveform
from synth.harmonic_fitter import HarmonicFitter, harmonic_adprs_waveform
from synth.fidelity_envelope import (
    ADPRSComposite,
    ADPRSEnvelope,
    FidelityBand,
    phi_to_resolution_band,
)
from synth.waveform_scheduler import WaveformScheduler, _evaluate_composite_at_tau


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_synthetic_trajectory(
    n_points: int,
    params: dict,
    noise: float = 0.0,
    rng: np.random.Generator | None = None,
    mode: str = "k1",
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate (tau, activation) pairs from known ADPRS or harmonic params.

    mode="k1": uses adprs_waveform with params {A, P, S, baseline}.
    mode="k3": uses harmonic_adprs_waveform with params {P1, c1, A1, c2, A2, c3, A3, baseline}.
    """
    tau = np.linspace(0.0, 0.95, n_points)
    if mode == "k1":
        activation = adprs_waveform(tau, params["A"], params["P"], params["S"], params["baseline"])
    elif mode == "k3":
        activation = harmonic_adprs_waveform(
            tau,
            params["P1"], params["c1"], params["A1"],
            params["c2"], params["A2"],
            params["c3"], params["A3"],
            params["baseline"],
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")

    if noise > 0 and rng is not None:
        activation = activation + rng.normal(0, noise, size=len(tau))
        activation = np.clip(activation, 0.0, 1.0)

    return tau, activation


def run_sufficiency_protocol(
    tau_fit: np.ndarray,
    activation_fit: np.ndarray,
    tau_test: np.ndarray,
    activation_test: np.ndarray,
    entity_id: str,
    fitter_type: str = "k1",
    harmonics: int = 1,
    epsilon: float = 0.1,
    fitter_kwargs: dict | None = None,
) -> dict:
    """
    Two-run sufficiency protocol for a single entity.

    Run 1: fit waveform to (tau_fit, activation_fit).
    Run 2: predict at each tau_test point, compare to activation_test.

    Returns dict with wsr, matched, total, per-point deltas, and fit result.
    """
    fitter_kwargs = fitter_kwargs or {}

    if fitter_type == "k1":
        fitter = ADPRSFitter(min_points=5, de_maxiter=300, **fitter_kwargs)
        fit_result = fitter.fit_entity(tau_fit, activation_fit, entity_id)
        # Predict using fitted params
        predicted = adprs_waveform(
            tau_test,
            fit_result.params["A"],
            fit_result.params["P"],
            fit_result.params["S"],
            fit_result.params["baseline"],
        )
    elif fitter_type == "k3":
        fitter = HarmonicFitter(min_points=5, de_maxiter=300, **fitter_kwargs)
        fit_result = fitter.fit_entity(tau_fit, activation_fit, entity_id, harmonics=harmonics)
        predicted = harmonic_adprs_waveform(
            tau_test,
            fit_result.params["P1"],
            fit_result.params["c1"],
            fit_result.params["A1"],
            fit_result.params["c2"],
            fit_result.params["A2"],
            fit_result.params["c3"],
            fit_result.params["A3"],
            fit_result.params["baseline"],
        )
    else:
        raise ValueError(f"Unknown fitter_type: {fitter_type}")

    deltas = np.abs(predicted - activation_test)
    matched = int(np.sum(deltas < epsilon))
    total = len(tau_test)
    wsr = matched / total if total > 0 else 0.0

    return {
        "wsr": wsr,
        "matched": matched,
        "total": total,
        "deltas": deltas,
        "fit_result": fit_result,
        "predicted": predicted,
    }


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

class TestMonotoneSufficiency:
    """Monotone decay trajectory: easy signal, high WSR expected."""

    def test_monotone_decay_wsr(self):
        """
        Generate a monotone decay trajectory, fit K=1 and K=3, run
        sufficiency on a slightly noisy second run. WSR > 0.85.
        """
        rng = np.random.default_rng(2026)
        n_points = 20

        # Ground-truth params: gentle decay, low oscillation
        true_params_k1 = {"A": 0.85, "P": 1.0, "S": 0.7, "baseline": 0.15}

        # Run 1: clean trajectory
        tau_fit, act_fit = generate_synthetic_trajectory(n_points, true_params_k1, noise=0.0, mode="k1")

        # Run 2: slightly noisy version
        tau_test, act_test = generate_synthetic_trajectory(
            n_points, true_params_k1, noise=0.03, rng=rng, mode="k1"
        )

        # K=1 sufficiency
        result_k1 = run_sufficiency_protocol(
            tau_fit, act_fit, tau_test, act_test,
            entity_id="mono_k1", fitter_type="k1", epsilon=0.1,
        )
        assert result_k1["wsr"] > 0.85, (
            f"K=1 monotone WSR={result_k1['wsr']:.3f}, expected >0.85"
        )

        # K=3 sufficiency (harmonic should also handle monotone)
        true_params_k3 = {
            "P1": 1.0, "c1": 0.7, "A1": 0.85,
            "c2": 0.0, "A2": 0.5,
            "c3": 0.0, "A3": 0.5,
            "baseline": 0.15,
        }
        tau_fit_k3, act_fit_k3 = generate_synthetic_trajectory(
            n_points, true_params_k3, noise=0.0, mode="k3"
        )
        tau_test_k3, act_test_k3 = generate_synthetic_trajectory(
            n_points, true_params_k3, noise=0.03, rng=np.random.default_rng(2026), mode="k3"
        )

        result_k3 = run_sufficiency_protocol(
            tau_fit_k3, act_fit_k3, tau_test_k3, act_test_k3,
            entity_id="mono_k3", fitter_type="k3", harmonics=3, epsilon=0.1,
        )
        assert result_k3["wsr"] > 0.85, (
            f"K=3 monotone WSR={result_k3['wsr']:.3f}, expected >0.85"
        )

    def test_fit_residual_low(self):
        """Monotone decay fit residual should be very small."""
        n_points = 20
        params = {"A": 0.85, "P": 1.0, "S": 0.7, "baseline": 0.15}
        tau, activation = generate_synthetic_trajectory(n_points, params, mode="k1")

        fitter = ADPRSFitter(min_points=5, de_maxiter=300)
        result = fitter.fit_entity(tau, activation, "mono_residual")
        assert result.residual < 0.01, f"Residual {result.residual:.6f}, expected <0.01"


class TestOscillatorySufficiency:
    """Oscillatory trajectory: harder signal, moderate WSR expected."""

    def test_oscillatory_wsr(self):
        """
        Generate oscillatory trajectory with P=3.0, fit and test.
        WSR > 0.7 (oscillatory is harder than monotone).
        """
        rng = np.random.default_rng(2027)
        n_points = 24

        true_params = {"A": 0.6, "P": 3.0, "S": 0.8, "baseline": 0.1}

        tau_fit, act_fit = generate_synthetic_trajectory(n_points, true_params, noise=0.0, mode="k1")
        tau_test, act_test = generate_synthetic_trajectory(
            n_points, true_params, noise=0.04, rng=rng, mode="k1"
        )

        result = run_sufficiency_protocol(
            tau_fit, act_fit, tau_test, act_test,
            entity_id="osc_k1", fitter_type="k1", epsilon=0.1,
        )
        assert result["wsr"] > 0.7, (
            f"Oscillatory K=1 WSR={result['wsr']:.3f}, expected >0.7"
        )

    def test_oscillatory_harmonic_wsr(self):
        """K=3 harmonic fit on oscillatory data."""
        rng = np.random.default_rng(2028)
        n_points = 24

        true_params = {
            "P1": 3.0, "c1": 0.6, "A1": 0.6,
            "c2": 0.2, "A2": 0.5,
            "c3": 0.1, "A3": 0.4,
            "baseline": 0.1,
        }

        tau_fit, act_fit = generate_synthetic_trajectory(n_points, true_params, noise=0.0, mode="k3")
        tau_test, act_test = generate_synthetic_trajectory(
            n_points, true_params, noise=0.04, rng=rng, mode="k3"
        )

        result = run_sufficiency_protocol(
            tau_fit, act_fit, tau_test, act_test,
            entity_id="osc_k3", fitter_type="k3", harmonics=3, epsilon=0.1,
        )
        assert result["wsr"] > 0.7, (
            f"Oscillatory K=3 WSR={result['wsr']:.3f}, expected >0.7"
        )


class TestMultiEntitySufficiency:
    """Two entities: one calm, one volatile. Overall WSR > 0.75."""

    def test_multi_entity_wsr(self):
        rng_calm = np.random.default_rng(3001)
        rng_volatile = np.random.default_rng(3002)
        n_points = 20

        # Calm entity: monotone, low P
        calm_params = {"A": 0.9, "P": 1.0, "S": 0.6, "baseline": 0.2}
        tau_fit_calm, act_fit_calm = generate_synthetic_trajectory(
            n_points, calm_params, noise=0.0, mode="k1"
        )
        tau_test_calm, act_test_calm = generate_synthetic_trajectory(
            n_points, calm_params, noise=0.02, rng=rng_calm, mode="k1"
        )

        # Volatile entity: oscillatory, higher P
        volatile_params = {"A": 0.5, "P": 3.5, "S": 0.85, "baseline": 0.08}
        tau_fit_vol, act_fit_vol = generate_synthetic_trajectory(
            n_points, volatile_params, noise=0.0, mode="k1"
        )
        tau_test_vol, act_test_vol = generate_synthetic_trajectory(
            n_points, volatile_params, noise=0.05, rng=rng_volatile, mode="k1"
        )

        result_calm = run_sufficiency_protocol(
            tau_fit_calm, act_fit_calm, tau_test_calm, act_test_calm,
            entity_id="calm", fitter_type="k1", epsilon=0.1,
        )
        result_volatile = run_sufficiency_protocol(
            tau_fit_vol, act_fit_vol, tau_test_vol, act_test_vol,
            entity_id="volatile", fitter_type="k1", epsilon=0.1,
        )

        # Overall WSR across both entities
        total_matched = result_calm["matched"] + result_volatile["matched"]
        total_points = result_calm["total"] + result_volatile["total"]
        overall_wsr = total_matched / total_points

        assert overall_wsr > 0.75, (
            f"Multi-entity WSR={overall_wsr:.3f} "
            f"(calm={result_calm['wsr']:.3f}, volatile={result_volatile['wsr']:.3f}), "
            f"expected >0.75"
        )

    def test_per_entity_wsr_reasonable(self):
        """Each entity should individually have WSR > 0.5 at minimum."""
        rng = np.random.default_rng(3003)
        n_points = 20

        entities = {
            "calm": {"A": 0.9, "P": 1.0, "S": 0.6, "baseline": 0.2},
            "volatile": {"A": 0.5, "P": 3.5, "S": 0.85, "baseline": 0.08},
        }

        for name, params in entities.items():
            tau_fit, act_fit = generate_synthetic_trajectory(n_points, params, noise=0.0, mode="k1")
            tau_test, act_test = generate_synthetic_trajectory(
                n_points, params, noise=0.04, rng=np.random.default_rng(3003 + hash(name) % 1000),
                mode="k1",
            )
            result = run_sufficiency_protocol(
                tau_fit, act_fit, tau_test, act_test,
                entity_id=name, fitter_type="k1", epsilon=0.1,
            )
            assert result["wsr"] > 0.5, (
                f"Entity '{name}' WSR={result['wsr']:.3f}, expected >0.5"
            )


class TestHarmonicImprovesWSR:
    """K=3 harmonic fit should match or exceed K=1 on multi-harmonic data."""

    def test_k3_beats_k1_on_rich_signal(self):
        """
        Generate data with clear multi-harmonic structure (c1=0.6, c2=0.3, c3=0.1).
        Fit with K=1 vs K=3, assert K=3 WSR >= K=1 WSR.
        """
        rng = np.random.default_rng(4001)
        n_points = 30

        true_params = {
            "P1": 2.0, "c1": 0.6, "A1": 0.7,
            "c2": 0.3, "A2": 0.6,
            "c3": 0.1, "A3": 0.5,
            "baseline": 0.1,
        }

        # Run 1: clean trajectory generated from K=3 model
        tau_fit, act_fit = generate_synthetic_trajectory(n_points, true_params, noise=0.0, mode="k3")

        # Run 2: slightly noisy
        tau_test, act_test = generate_synthetic_trajectory(
            n_points, true_params, noise=0.03, rng=rng, mode="k3"
        )

        # K=1 fit on K=3 data (underfitting expected)
        result_k1 = run_sufficiency_protocol(
            tau_fit, act_fit, tau_test, act_test,
            entity_id="harmonic_k1", fitter_type="k3", harmonics=1, epsilon=0.1,
        )

        # K=3 fit on K=3 data (should capture harmonics)
        result_k3 = run_sufficiency_protocol(
            tau_fit, act_fit, tau_test, act_test,
            entity_id="harmonic_k3", fitter_type="k3", harmonics=3, epsilon=0.1,
        )

        assert result_k3["wsr"] >= result_k1["wsr"], (
            f"K=3 WSR ({result_k3['wsr']:.3f}) should be >= K=1 WSR ({result_k1['wsr']:.3f})"
        )

    def test_k3_residual_lower_than_k1(self):
        """K=3 fit residual on multi-harmonic data should be <= K=1 residual."""
        n_points = 30
        true_params = {
            "P1": 2.0, "c1": 0.6, "A1": 0.7,
            "c2": 0.3, "A2": 0.6,
            "c3": 0.1, "A3": 0.5,
            "baseline": 0.1,
        }
        tau, activation = generate_synthetic_trajectory(n_points, true_params, noise=0.0, mode="k3")

        fitter = HarmonicFitter(min_points=5, de_maxiter=300)

        fit_k1 = fitter.fit_entity(tau, activation, "res_k1", harmonics=1)
        fit_k3 = fitter.fit_entity(tau, activation, "res_k3", harmonics=3)

        assert fit_k3.residual <= fit_k1.residual + 1e-9, (
            f"K=3 residual ({fit_k3.residual:.6f}) should be <= "
            f"K=1 residual ({fit_k1.residual:.6f})"
        )


class TestSchedulerIntegration:
    """Full pipeline: generate -> fit -> register -> schedule -> predict -> record -> report."""

    def test_full_scheduler_pipeline(self):
        """
        End-to-end: generate trajectory, fit ADPRS, register with scheduler,
        schedule, predict, record actuals, check sufficiency_report structure.
        """
        rng = np.random.default_rng(5001)
        n_points = 20
        entity_id = "sched_entity"
        epsilon = 0.1

        true_params = {"A": 0.75, "P": 2.0, "S": 0.75, "baseline": 0.12}

        # Run 1: fit
        tau_fit, act_fit = generate_synthetic_trajectory(n_points, true_params, noise=0.0, mode="k1")
        fitter = ADPRSFitter(min_points=5, de_maxiter=300)
        fit_result = fitter.fit_entity(tau_fit, act_fit, entity_id)

        # Build envelope metadata and register with scheduler
        duration_ms = 31536000000.0
        t0_iso = "2026-01-01T00:00:00+00:00"
        envelope = fit_result.to_envelope(duration_ms, t0_iso)
        composite = ADPRSComposite(envelopes=[envelope])

        metadata = {
            "adprs_envelopes": composite.to_metadata_dict(),
        }

        scheduler = WaveformScheduler(epsilon=epsilon)
        scheduler.register_from_metadata(entity_id, metadata)
        assert scheduler.has_schedule(entity_id)

        # Run 2: predict and record
        tau_test, act_test = generate_synthetic_trajectory(
            n_points, true_params, noise=0.03, rng=rng, mode="k1"
        )

        for i in range(n_points):
            tau_i = float(tau_test[i])

            # Predict BEFORE seeing actual
            predicted_phi = _evaluate_composite_at_tau(composite, tau_i)
            predicted_band = phi_to_resolution_band(predicted_phi)
            scheduler.record_prediction(entity_id, tau_i, predicted_phi, predicted_band)

            # Schedule
            band = scheduler.schedule_entity(entity_id, tau_i)
            assert band is not None

            # Record actual
            scheduler.record_actual(entity_id, tau_i, float(act_test[i]))

        # Sufficiency report
        report = scheduler.sufficiency_report()

        assert report["total_predictions"] == n_points
        assert report["total_actuals"] == n_points
        assert "wsr" in report
        assert "matched" in report
        assert "skipped_llm_calls" in report
        assert "epsilon" in report
        assert report["epsilon"] == epsilon
        assert report["wsr"] is not None
        assert 0.0 <= report["wsr"] <= 1.0

    def test_scheduler_wsr_reasonable(self):
        """Scheduler-computed WSR should be > 0.7 on clean-ish data."""
        rng = np.random.default_rng(5002)
        n_points = 20
        entity_id = "sched_wsr"
        epsilon = 0.1

        true_params = {"A": 0.75, "P": 2.0, "S": 0.75, "baseline": 0.12}

        tau_fit, act_fit = generate_synthetic_trajectory(n_points, true_params, noise=0.0, mode="k1")
        fitter = ADPRSFitter(min_points=5, de_maxiter=300)
        fit_result = fitter.fit_entity(tau_fit, act_fit, entity_id)

        duration_ms = 31536000000.0
        t0_iso = "2026-01-01T00:00:00+00:00"
        envelope = fit_result.to_envelope(duration_ms, t0_iso)
        composite = ADPRSComposite(envelopes=[envelope])

        scheduler = WaveformScheduler(epsilon=epsilon)
        scheduler.register_envelopes(entity_id, composite)

        tau_test, act_test = generate_synthetic_trajectory(
            n_points, true_params, noise=0.03, rng=rng, mode="k1"
        )

        for i in range(n_points):
            tau_i = float(tau_test[i])
            predicted_phi = _evaluate_composite_at_tau(composite, tau_i)
            predicted_band = phi_to_resolution_band(predicted_phi)
            scheduler.record_prediction(entity_id, tau_i, predicted_phi, predicted_band)
            scheduler.record_actual(entity_id, tau_i, float(act_test[i]))

        report = scheduler.sufficiency_report()
        assert report["wsr"] > 0.7, (
            f"Scheduler WSR={report['wsr']:.3f}, expected >0.7"
        )

    def test_predict_activation_delta(self):
        """WaveformScheduler.predict_activation_delta returns correct structure."""
        entity_id = "delta_entity"
        true_params = {"A": 0.75, "P": 2.0, "S": 0.75, "baseline": 0.12}

        n_points = 20
        tau_fit, act_fit = generate_synthetic_trajectory(n_points, true_params, noise=0.0, mode="k1")
        fitter = ADPRSFitter(min_points=5, de_maxiter=300)
        fit_result = fitter.fit_entity(tau_fit, act_fit, entity_id)

        duration_ms = 31536000000.0
        t0_iso = "2026-01-01T00:00:00+00:00"
        envelope = fit_result.to_envelope(duration_ms, t0_iso)
        composite = ADPRSComposite(envelopes=[envelope])

        scheduler = WaveformScheduler(epsilon=0.1)
        scheduler.register_envelopes(entity_id, composite)

        delta = scheduler.predict_activation_delta(entity_id, 0.2, 0.3)
        assert delta is not None
        assert "predicted_phi" in delta
        assert "delta_phi" in delta
        assert "predicted_band" in delta
        assert isinstance(delta["predicted_phi"], float)
        assert 0.0 <= delta["predicted_phi"] <= 1.0

    def test_unregistered_entity_returns_none(self):
        """Scheduler returns None for unknown entities."""
        scheduler = WaveformScheduler(epsilon=0.1)
        assert scheduler.schedule_entity("unknown", 0.5) is None
        assert scheduler.predict_activation_delta("unknown", 0.2, 0.3) is None
