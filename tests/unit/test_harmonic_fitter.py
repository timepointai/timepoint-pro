"""
Unit tests for Harmonic Extension of ADPRS waveform fitting.

Tests harmonic waveform math, K-fallback logic, cold/warm fitting,
spectral distance, and HarmonicFitResult — all pure math, no LLM/DB
dependencies.
"""

import pytest
import numpy as np

from synth.harmonic_fitter import (
    harmonic_adprs_waveform,
    HarmonicFitter,
    HarmonicFitResult,
    HARMONIC_PARAM_BOUNDS,
    HARMONIC_PARAM_NAMES,
    HARMONIC_DEFAULT_PARAMS,
)
from synth.adprs_fitter import adprs_waveform


# --- Helpers ---


def generate_harmonic_data(
    P1, c1, A1, c2, A2, c3, A3, baseline, n_points=20, noise=0.0
):
    """Generate tau/activation data from known harmonic ADPRS params."""
    tau = np.linspace(0.0, 0.95, n_points)  # Avoid tau=1 where decay -> 0
    activation = harmonic_adprs_waveform(tau, P1, c1, A1, c2, A2, c3, A3, baseline)
    if noise > 0:
        rng = np.random.default_rng(42)
        activation = np.clip(activation + rng.normal(0, noise, n_points), 0, 1)
    return tau, activation


# --- harmonic_adprs_waveform ---


class TestHarmonicWaveform:
    def test_vectorized(self):
        """Waveform should accept and return numpy arrays."""
        tau = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        result = harmonic_adprs_waveform(tau, 2.0, 0.8, 0.7, 0.0, 0.5, 0.0, 0.5, 0.1)
        assert isinstance(result, np.ndarray)
        assert len(result) == 5

    def test_k1_matches_fundamental(self):
        """With c2=c3=0, harmonic waveform should match the original adprs_waveform.

        The mapping is: c1=S, A1=A, P1=P, baseline maps to (1-S)*baseline
        in the original. Since the harmonic waveform uses a different baseline
        formulation (additive baseline vs. (1-S)*baseline), we compare the
        harmonic K=1 against its own formula evaluated directly.

        Specifically: harmonic(c2=c3=0) = c1 * |sin(tau*2pi*P1)| * (1-tau)^((1-A1)*3) + baseline
        vs original: S * |sin(tau*2pi*P)| * (1-tau)^((1-A)*3) + (1-S)*baseline

        With c1=S, A1=A, P1=P, baseline_harmonic = (1-S)*baseline_orig, both match.
        """
        S, A, P, bl_orig = 0.8, 0.7, 2.0, 0.1
        baseline_harmonic = (1.0 - S) * bl_orig

        tau_values = np.array([0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 0.95])

        harmonic_result = harmonic_adprs_waveform(
            tau_values, P, S, A, 0.0, 0.5, 0.0, 0.5, baseline_harmonic
        )
        original_result = adprs_waveform(tau_values, A, P, S, bl_orig)

        np.testing.assert_allclose(harmonic_result, original_result, atol=1e-10)

    def test_output_clamped(self):
        """Output always in [0, 1] for a range of params."""
        tau = np.linspace(0, 1, 100)
        for P1 in [0.5, 2.0, 8.0]:
            for c1 in [0.01, 0.5, 1.0]:
                for baseline in [0.0, 0.5, 1.0]:
                    result = harmonic_adprs_waveform(
                        tau, P1, c1, 0.7, 0.3, 0.5, 0.2, 0.5, baseline
                    )
                    assert np.all(result >= 0.0) and np.all(result <= 1.0), (
                        f"Out of range for P1={P1}, c1={c1}, baseline={baseline}"
                    )

    def test_harmonics_add_complexity(self):
        """With c2, c3 > 0, the signal should differ from fundamental-only."""
        tau = np.linspace(0.0, 0.95, 50)
        P1, c1, A1, baseline = 2.0, 0.8, 0.7, 0.1

        fundamental_only = harmonic_adprs_waveform(
            tau, P1, c1, A1, 0.0, 0.5, 0.0, 0.5, baseline
        )
        with_harmonics = harmonic_adprs_waveform(
            tau, P1, c1, A1, 0.3, 0.6, 0.2, 0.5, baseline
        )

        # Signals should not be identical
        diff = np.abs(fundamental_only - with_harmonics)
        assert np.max(diff) > 0.01, "Harmonics should make the signal differ"

    def test_boundary_tau_zero(self):
        """At tau=0, sin(0)=0 so phi = baseline."""
        result = harmonic_adprs_waveform(
            np.array([0.0]), 2.0, 0.8, 0.7, 0.3, 0.5, 0.2, 0.5, 0.1
        )
        # sin(0)=0 for all harmonics, so all oscillation terms are 0
        assert abs(result[0] - 0.1) < 1e-10

    def test_boundary_tau_one(self):
        """At tau=1, decay=0 so phi = baseline."""
        result = harmonic_adprs_waveform(
            np.array([1.0]), 2.0, 0.8, 0.7, 0.3, 0.5, 0.2, 0.5, 0.1
        )
        # (1-1)^exp = 0 for all harmonics (with A < 1), so phi = baseline
        # Note: when A=1.0, exponent=0 so decay=1, but for A<1 decay=0
        # A1=0.7, A2=0.5, A3=0.5 all < 1, so all decay terms are 0
        assert abs(result[0] - 0.1) < 1e-10


# --- HarmonicFitter ---


class TestHarmonicFitter:
    def test_recover_fundamental_signal(self):
        """Fit K=3 to data generated from K=1 signal.

        The K=3 fit should achieve low residual. Note: since multiple
        harmonic parameterizations can produce similar waveforms, we
        don't assert which harmonic carries the energy — only that the
        overall fit is good.
        """
        P1, c1, A1, baseline = 2.0, 0.8, 0.7, 0.1
        tau, activation = generate_harmonic_data(
            P1, c1, A1, 0.0, 0.5, 0.0, 0.5, baseline, n_points=30
        )

        fitter = HarmonicFitter(de_maxiter=200, de_seed=42)
        result = fitter.fit_entity(tau, activation, "e1", harmonics=3)

        assert result.residual < 0.01
        assert result.method == "differential_evolution"
        assert len(result.spectral_signature) == 3

    def test_recover_multi_harmonic_signal(self):
        """Generate data from known K=3 params, fit, verify recovery."""
        P1, c1, A1 = 2.0, 0.6, 0.7
        c2, A2 = 0.3, 0.5
        c3, A3 = 0.15, 0.6
        baseline = 0.05

        tau, activation = generate_harmonic_data(
            P1, c1, A1, c2, A2, c3, A3, baseline, n_points=40
        )

        fitter = HarmonicFitter(de_maxiter=300, de_seed=42)
        result = fitter.fit_entity(tau, activation, "e1", harmonics=3)

        assert result.residual < 0.05, f"Residual too high: {result.residual}"

    def test_fallback_to_k1(self):
        """With only 6 data points (< 3*4=12 min for K=3), should fall back to K=1."""
        P1, c1, A1, baseline = 2.0, 0.8, 0.7, 0.1
        tau, activation = generate_harmonic_data(
            P1, c1, A1, 0.0, 0.5, 0.0, 0.5, baseline, n_points=6
        )

        fitter = HarmonicFitter(min_points_per_harmonic=4, de_maxiter=100)
        result = fitter.fit_entity(tau, activation, "e1", harmonics=3)

        assert result.harmonics == 1
        # Expanded params should zero out c2, c3
        assert result.params["c2"] == 0.0
        assert result.params["c3"] == 0.0

    def test_fallback_to_k2(self):
        """With 10 data points (< 3*4 but >= 2*4), should fall back to K=2."""
        P1, c1, A1, baseline = 2.0, 0.8, 0.7, 0.1
        tau, activation = generate_harmonic_data(
            P1, c1, A1, 0.2, 0.5, 0.0, 0.5, baseline, n_points=10
        )

        fitter = HarmonicFitter(min_points_per_harmonic=4, de_maxiter=100)
        result = fitter.fit_entity(tau, activation, "e1", harmonics=3)

        assert result.harmonics == 2
        # Expanded params should zero out c3
        assert result.params["c3"] == 0.0

    def test_determine_harmonics(self):
        """Directly test the _determine_harmonics method."""
        fitter = HarmonicFitter(min_points_per_harmonic=4)

        # Enough data for K=3: 12 points >= 3*4
        assert fitter._determine_harmonics(12, 3) == 3
        assert fitter._determine_harmonics(20, 3) == 3

        # Not enough for K=3, falls to K=2: 8 points >= 2*4 but < 3*4
        assert fitter._determine_harmonics(8, 3) == 2
        assert fitter._determine_harmonics(11, 3) == 2

        # Not enough for K=2, falls to K=1: 3 points < 2*4
        assert fitter._determine_harmonics(3, 3) == 1
        assert fitter._determine_harmonics(7, 3) == 1

        # Minimum K=1 always
        assert fitter._determine_harmonics(1, 3) == 1

        # Requested K=1 stays at 1 regardless
        assert fitter._determine_harmonics(100, 1) == 1

    def test_warm_start(self):
        """Fit with prior params uses curve_fit method."""
        P1, c1, A1, baseline = 2.0, 0.8, 0.7, 0.1
        tau, activation = generate_harmonic_data(
            P1, c1, A1, 0.0, 0.5, 0.0, 0.5, baseline, n_points=20
        )

        prior = {
            "P1": 2.1, "c1": 0.75, "A1": 0.65,
            "c2": 0.0, "A2": 0.5,
            "c3": 0.0, "A3": 0.5,
            "baseline": 0.12,
        }

        fitter = HarmonicFitter()
        result = fitter.fit_entity(tau, activation, "e1", harmonics=3, prior_params=prior)

        assert result.method == "curve_fit"
        assert result.prior_params is not None
        assert result.parameter_drift is not None
        assert result.converged

    def test_spectral_signature_populated(self):
        """Result has spectral_signature = [c1, c2, c3]."""
        P1, c1, A1, baseline = 2.0, 0.8, 0.7, 0.1
        tau, activation = generate_harmonic_data(
            P1, c1, A1, 0.2, 0.5, 0.1, 0.5, baseline, n_points=20
        )

        fitter = HarmonicFitter(de_maxiter=100)
        result = fitter.fit_entity(tau, activation, "e1", harmonics=3)

        assert result.spectral_signature is not None
        assert len(result.spectral_signature) == 3
        assert result.spectral_signature[0] == result.params["c1"]
        assert result.spectral_signature[1] == result.params["c2"]
        assert result.spectral_signature[2] == result.params["c3"]


# --- SpectralDistance ---


class TestSpectralDistance:
    def test_identical_zero(self):
        """Identical signatures should have distance 0."""
        dist = HarmonicFitter.spectral_distance([0.8, 0.3, 0.1], [0.8, 0.3, 0.1])
        assert abs(dist) < 1e-10

    def test_orthogonal_one(self):
        """Orthogonal signatures should have distance 1."""
        dist = HarmonicFitter.spectral_distance([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
        assert abs(dist - 1.0) < 1e-10

    def test_zero_vector_handling(self):
        """Zero vector should return distance 1."""
        dist_a = HarmonicFitter.spectral_distance([0.0, 0.0, 0.0], [0.8, 0.3, 0.1])
        assert abs(dist_a - 1.0) < 1e-10

        dist_b = HarmonicFitter.spectral_distance([0.8, 0.3, 0.1], [0.0, 0.0, 0.0])
        assert abs(dist_b - 1.0) < 1e-10

        dist_both = HarmonicFitter.spectral_distance([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        assert abs(dist_both - 1.0) < 1e-10

    def test_similar_signatures_small_distance(self):
        """Similar signatures should have small distance."""
        dist = HarmonicFitter.spectral_distance([0.8, 0.3, 0.1], [0.82, 0.28, 0.12])
        assert dist < 0.05

    def test_symmetric(self):
        """Distance should be symmetric: distance(a,b) == distance(b,a)."""
        a = [0.8, 0.3, 0.1]
        b = [0.5, 0.6, 0.2]
        dist_ab = HarmonicFitter.spectral_distance(a, b)
        dist_ba = HarmonicFitter.spectral_distance(b, a)
        assert abs(dist_ab - dist_ba) < 1e-10


# --- HarmonicFitResult ---


class TestHarmonicFitResult:
    def test_fields(self):
        """Result has all expected fields."""
        result = HarmonicFitResult(
            entity_id="e1",
            params={"P1": 2.0, "c1": 0.8, "A1": 0.7, "c2": 0.0, "A2": 0.5, "c3": 0.0, "A3": 0.5, "baseline": 0.1},
            spectral_signature=[0.8, 0.0, 0.0],
            residual=0.005,
            n_points=20,
            method="differential_evolution",
            converged=True,
            harmonics=3,
        )
        assert result.entity_id == "e1"
        assert result.params["P1"] == 2.0
        assert result.params["c1"] == 0.8
        assert result.spectral_signature == [0.8, 0.0, 0.0]
        assert result.residual == 0.005
        assert result.n_points == 20
        assert result.method == "differential_evolution"
        assert result.converged is True
        assert result.harmonics == 3
        assert result.prior_params is None
        assert result.parameter_drift is None
