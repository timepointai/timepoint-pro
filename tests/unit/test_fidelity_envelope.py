"""
Unit tests for ADPRS fidelity envelope waveforms.

Tests the core waveform math, band mapping, recurrence, serialization,
and composite max-composition — all pure math, no LLM/DB dependencies.
"""

import math
import pytest
from datetime import datetime, timezone, timedelta

from synth.fidelity_envelope import (
    ADPRSEnvelope,
    ADPRSComposite,
    FidelityBand,
    phi_to_resolution_band,
    datetime_to_ms,
)


# --- Helpers ---

def make_t0() -> datetime:
    """Standard t0 for tests."""
    return datetime(2025, 1, 1, tzinfo=timezone.utc)


def envelope_at_tau(env: ADPRSEnvelope, tau: float) -> float:
    """Evaluate an envelope at a normalized tau position within its duration."""
    t0 = make_t0()
    t = t0 + timedelta(milliseconds=env.D * tau)
    return env.evaluate(t)


# --- datetime_to_ms ---

class TestDatetimeToMs:
    def test_epoch(self):
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        assert datetime_to_ms(epoch) == 0.0

    def test_known_value(self):
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        expected = dt.timestamp() * 1000.0
        assert datetime_to_ms(dt) == expected


# --- Band mapping ---

class TestPhiToResolutionBand:
    def test_tensor_band(self):
        assert phi_to_resolution_band(0.0) == FidelityBand.TENSOR
        assert phi_to_resolution_band(0.1) == FidelityBand.TENSOR
        assert phi_to_resolution_band(0.19) == FidelityBand.TENSOR

    def test_scene_band(self):
        assert phi_to_resolution_band(0.2) == FidelityBand.SCENE
        assert phi_to_resolution_band(0.3) == FidelityBand.SCENE
        assert phi_to_resolution_band(0.39) == FidelityBand.SCENE

    def test_graph_band(self):
        assert phi_to_resolution_band(0.4) == FidelityBand.GRAPH
        assert phi_to_resolution_band(0.5) == FidelityBand.GRAPH

    def test_dialog_band(self):
        assert phi_to_resolution_band(0.6) == FidelityBand.DIALOG
        assert phi_to_resolution_band(0.7) == FidelityBand.DIALOG

    def test_trained_band(self):
        assert phi_to_resolution_band(0.8) == FidelityBand.TRAINED
        assert phi_to_resolution_band(0.9) == FidelityBand.TRAINED
        assert phi_to_resolution_band(1.0) == FidelityBand.TRAINED

    def test_exact_boundaries(self):
        """Verify boundaries map to the higher band."""
        assert phi_to_resolution_band(0.2) == FidelityBand.SCENE
        assert phi_to_resolution_band(0.4) == FidelityBand.GRAPH
        assert phi_to_resolution_band(0.6) == FidelityBand.DIALOG
        assert phi_to_resolution_band(0.8) == FidelityBand.TRAINED


# --- Waveform boundary values ---

class TestWaveformBoundaries:
    def test_tau_zero_p_nonzero(self):
        """At tau=0, sin(0)=0, so oscillation is 0; phi collapses to (1-S)*baseline."""
        env = ADPRSEnvelope(A=0.7, D=1000.0, P=2.0, R=0, S=0.8, t0="2025-01-01T00:00:00+00:00", baseline=0.1)
        phi = envelope_at_tau(env, 0.0)
        # oscillation = |sin(0)| = 0, decay = 1.0, so phi = 0 * 1 * 0.8 + 0.2 * 0.1 = 0.02
        assert abs(phi - 0.02) < 1e-6

    def test_tau_quarter_single_period(self):
        """At tau=0.25 with P=1, sin(pi/2)=1 → full oscillation peak."""
        env = ADPRSEnvelope(A=1.0, D=1000.0, P=1.0, R=0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        phi = envelope_at_tau(env, 0.25)
        # oscillation = |sin(0.25 * 2pi * 1)| = |sin(pi/2)| = 1
        # decay = (1 - 0.25)^(0) = 1  (A=1 → exponent=0)
        # phi = 1 * 1 * 1 + 0 = 1.0
        assert abs(phi - 1.0) < 1e-6

    def test_tau_one_decay_collapses(self):
        """At tau=1.0, decay = 0 → oscillation term vanishes, phi = (1-S)*baseline."""
        env = ADPRSEnvelope(A=0.5, D=1000.0, P=2.0, R=0, S=0.8, t0="2025-01-01T00:00:00+00:00", baseline=0.1)
        # Exactly at tau=1.0 (elapsed == D), tau < 1.0 is False → decay=0
        # phi = osc * 0 * S + (1-S)*baseline = 0.2 * 0.1 = 0.02
        t0 = make_t0()
        t = t0 + timedelta(milliseconds=1000.0)
        phi = env.evaluate(t)
        expected = (1.0 - env.S) * env.baseline  # 0.02
        assert abs(phi - expected) < 1e-6

    def test_past_duration_returns_baseline(self):
        """Well past duration (single-shot), evaluate returns baseline directly."""
        env = ADPRSEnvelope(A=0.5, D=1000.0, P=2.0, R=0, S=0.8, t0="2025-01-01T00:00:00+00:00", baseline=0.1)
        t0 = make_t0()
        t = t0 + timedelta(milliseconds=2000.0)  # past duration
        phi = env.evaluate(t)
        assert abs(phi - env.baseline) < 1e-6


# --- Decay rates ---

class TestDecayRates:
    def test_a_zero_fast_decay(self):
        """A=0 means exponent = 3, so fast decay toward end."""
        env = ADPRSEnvelope(A=0.0, D=1000.0, P=1.0, R=0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        # Evaluate at tau=0.5, at the peak of sin for P=1 → tau=0.25
        phi_early = envelope_at_tau(env, 0.25)
        phi_late = envelope_at_tau(env, 0.75)
        # Late should decay significantly more than early
        assert phi_early > phi_late

    def test_a_one_no_decay(self):
        """A=1 means exponent = 0, so no decay (constant envelope modulated only by oscillation)."""
        env = ADPRSEnvelope(A=1.0, D=1000.0, P=1.0, R=0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        # At sin peaks (tau=0.25 and tau=0.75), values should be equal since no decay
        phi_early = envelope_at_tau(env, 0.25)
        phi_late = envelope_at_tau(env, 0.75)
        assert abs(phi_early - phi_late) < 1e-6


# --- Spread collapse ---

class TestSpread:
    def test_s_zero_collapses_to_baseline(self):
        """S=0 means the oscillation term vanishes, output = baseline."""
        env = ADPRSEnvelope(A=0.7, D=1000.0, P=2.0, R=0, S=0.0, t0="2025-01-01T00:00:00+00:00", baseline=0.5)
        for tau in [0.0, 0.25, 0.5, 0.75]:
            phi = envelope_at_tau(env, tau)
            assert abs(phi - 0.5) < 1e-6, f"At tau={tau}, expected 0.5, got {phi}"

    def test_s_one_full_range(self):
        """S=1 means full oscillation range with baseline contribution zeroed."""
        env = ADPRSEnvelope(A=1.0, D=1000.0, P=1.0, R=0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.5)
        phi = envelope_at_tau(env, 0.25)
        # oscillation=1, decay=1, phi = 1*1*1 + 0*0.5 = 1.0
        assert abs(phi - 1.0) < 1e-6


# --- Multi-period oscillation ---

class TestMultiPeriod:
    def test_p_one_single_peak(self):
        """P=1: one full sine cycle in duration → peak at tau=0.25."""
        env = ADPRSEnvelope(A=1.0, D=1000.0, P=1.0, R=0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        phi_peak = envelope_at_tau(env, 0.25)
        phi_trough = envelope_at_tau(env, 0.5)
        assert phi_peak > 0.9
        assert phi_trough < 0.01

    def test_p_four_multiple_peaks(self):
        """P=4: four full sine cycles → peaks at tau=0.0625, 0.1875, etc."""
        env = ADPRSEnvelope(A=1.0, D=1000.0, P=4.0, R=0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        # First peak: tau = 0.25 / 4 = 0.0625
        phi_peak1 = envelope_at_tau(env, 0.0625)
        # Second peak: tau = 0.75 / 4 = 0.1875
        phi_peak2 = envelope_at_tau(env, 0.1875)
        assert phi_peak1 > 0.9
        assert phi_peak2 > 0.9


# --- Recurrence ---

class TestRecurrence:
    def test_r_zero_single_shot(self):
        """R=0: no recurrence. After duration, stays at baseline."""
        env = ADPRSEnvelope(A=0.7, D=1000.0, P=1.0, R=0, S=0.8, t0="2025-01-01T00:00:00+00:00", baseline=0.1)
        t0 = make_t0()
        # Well past duration
        t_after = t0 + timedelta(milliseconds=5000.0)
        assert abs(env.evaluate(t_after) - 0.1) < 1e-6

    def test_r_greater_than_d_has_gaps(self):
        """R > D: active for D ms, then gap until next cycle."""
        env = ADPRSEnvelope(A=1.0, D=100.0, P=1.0, R=200.0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        t0 = make_t0()
        # In gap: 150ms into first cycle (100 < 150 < 200)
        t_gap = t0 + timedelta(milliseconds=150.0)
        assert abs(env.evaluate(t_gap) - 0.0) < 1e-6
        # In second cycle active window: 225ms → cycle_pos=25ms, tau=0.25
        t_second = t0 + timedelta(milliseconds=225.0)
        phi = env.evaluate(t_second)
        assert phi > 0.5  # Should be active

    def test_recurrence_cycle_alignment(self):
        """Recurrence should repeat the waveform identically each cycle."""
        env = ADPRSEnvelope(A=1.0, D=100.0, P=1.0, R=100.0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        t0 = make_t0()
        # Same tau position in first and second cycle
        t_first = t0 + timedelta(milliseconds=25.0)  # tau=0.25 in cycle 0
        t_second = t0 + timedelta(milliseconds=125.0)  # tau=0.25 in cycle 1
        assert abs(env.evaluate(t_first) - env.evaluate(t_second)) < 1e-6


# --- Before start and after duration ---

class TestOutOfRange:
    def test_before_start(self):
        """Time before t0 returns baseline."""
        env = ADPRSEnvelope(A=0.7, D=1000.0, P=1.0, R=0, S=0.8, t0="2025-06-01T00:00:00+00:00", baseline=0.2)
        t_before = datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert abs(env.evaluate(t_before) - 0.2) < 1e-6

    def test_after_duration_single_shot(self):
        """Time after duration (single-shot) returns baseline."""
        env = ADPRSEnvelope(A=0.7, D=1000.0, P=1.0, R=0, S=0.8, t0="2025-01-01T00:00:00+00:00", baseline=0.3)
        t0 = make_t0()
        t_after = t0 + timedelta(milliseconds=2000.0)
        assert abs(env.evaluate(t_after) - 0.3) < 1e-6


# --- Output clamping ---

class TestClamping:
    def test_output_always_in_zero_one(self):
        """Output should always be in [0, 1] for any parameter combo."""
        configs = [
            {"A": 0.0, "D": 1000.0, "P": 10.0, "R": 0, "S": 1.0, "baseline": 0.0},
            {"A": 1.0, "D": 1000.0, "P": 0.0, "R": 0, "S": 1.0, "baseline": 1.0},
            {"A": 0.5, "D": 1.0, "P": 100.0, "R": 0, "S": 0.5, "baseline": 0.5},
        ]
        for cfg in configs:
            env = ADPRSEnvelope(**cfg, t0="2025-01-01T00:00:00+00:00")
            for tau in [0.0, 0.1, 0.25, 0.5, 0.75, 0.99]:
                phi = envelope_at_tau(env, tau)
                assert 0.0 <= phi <= 1.0, f"Out of range: phi={phi} for cfg={cfg}, tau={tau}"


# --- Composite ---

class TestComposite:
    def test_max_of_two(self):
        """Composite returns max of its envelopes."""
        env_low = ADPRSEnvelope(A=1.0, D=1000.0, P=1.0, R=0, S=0.3, t0="2025-01-01T00:00:00+00:00", baseline=0.1)
        env_high = ADPRSEnvelope(A=1.0, D=1000.0, P=1.0, R=0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        comp = ADPRSComposite(envelopes=[env_low, env_high])

        t = make_t0() + timedelta(milliseconds=250.0)  # tau=0.25, sin peak
        phi_comp = comp.evaluate(t)
        phi_low = env_low.evaluate(t)
        phi_high = env_high.evaluate(t)
        assert phi_comp == max(phi_low, phi_high)

    def test_empty_returns_zero(self):
        """Empty composite evaluates to 0."""
        comp = ADPRSComposite(envelopes=[])
        t = make_t0()
        assert comp.evaluate(t) == 0.0

    def test_evaluate_band(self):
        """Composite band mapping works through evaluate."""
        env = ADPRSEnvelope(A=1.0, D=1000.0, P=1.0, R=0, S=1.0, t0="2025-01-01T00:00:00+00:00", baseline=0.0)
        comp = ADPRSComposite(envelopes=[env])
        t = make_t0() + timedelta(milliseconds=250.0)
        band = comp.evaluate_band(t)
        assert isinstance(band, FidelityBand)


# --- Serialization roundtrip ---

class TestSerialization:
    def test_envelope_roundtrip(self):
        """to_metadata_dict → from_metadata_dict preserves all parameters."""
        orig = ADPRSEnvelope(A=0.3, D=5000.0, P=3.0, R=10000.0, S=0.6, t0="2025-06-15T12:00:00+00:00", baseline=0.2)
        d = orig.to_metadata_dict()
        restored = ADPRSEnvelope.from_metadata_dict(d)
        assert restored.A == orig.A
        assert restored.D == orig.D
        assert restored.P == orig.P
        assert restored.R == orig.R
        assert restored.S == orig.S
        assert restored.t0 == orig.t0
        assert restored.baseline == orig.baseline

    def test_composite_roundtrip(self):
        """Composite serialization preserves all envelopes."""
        env1 = ADPRSEnvelope(A=0.5, D=1000.0, P=1.0, R=0, S=0.8, t0="2025-01-01T00:00:00+00:00", baseline=0.1)
        env2 = ADPRSEnvelope(A=0.9, D=2000.0, P=3.0, R=5000.0, S=0.5, t0="2025-06-01T00:00:00+00:00", baseline=0.3)
        comp = ADPRSComposite(envelopes=[env1, env2])
        d = comp.to_metadata_dict()
        restored = ADPRSComposite.from_metadata_dict(d)
        assert len(restored.envelopes) == 2
        assert restored.envelopes[0].A == env1.A
        assert restored.envelopes[1].R == env2.R

    def test_metadata_dict_is_json_safe(self):
        """Metadata dict should contain only JSON-serializable types."""
        import json
        env = ADPRSEnvelope()
        d = env.to_metadata_dict()
        json.dumps(d)  # Should not raise

        comp = ADPRSComposite(envelopes=[env])
        d = comp.to_metadata_dict()
        json.dumps(d)  # Should not raise
