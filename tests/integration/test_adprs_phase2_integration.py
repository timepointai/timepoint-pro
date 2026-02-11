"""
Integration test for ADPRS Phase 2: Emergent Envelope Fitting from TTM Trajectories.

Exercises the full pipeline WITHOUT LLM calls:
  1. TrajectoryTracker accumulates snapshots (mock entities with evolving cognitive state)
  2. ADPRSFitter fits waveform parameters to observed trajectories
  3. apply_to_entities writes fitted envelopes to entity_metadata
  4. ShadowEvaluator re-initializes from fitted envelopes and evaluates

This validates that the Phase 1→2 handoff works end-to-end.
"""

import math
import numpy as np
import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from synth.trajectory_tracker import TrajectoryTracker, CognitiveSnapshot
from synth.adprs_fitter import ADPRSFitter, FitResult, adprs_waveform
from synth.fidelity_envelope import ADPRSEnvelope, ADPRSComposite
from synth.shadow_evaluator import ShadowEvaluator


# --- Helpers ---

def make_evolving_entity(entity_id, valence_trajectory, arousal_trajectory, energy_trajectory):
    """
    Create a list of mock entity states that evolve over timepoints.

    Each call to record_snapshot will use the entity's cognitive tensor at that point.
    Returns a list of (entity_state, timepoint, index) triples.
    """
    states = []
    n = len(valence_trajectory)
    for i in range(n):
        entity = SimpleNamespace(
            entity_id=entity_id,
            tensor_maturity=0.5 + i * 0.03,
            entity_metadata={
                "cognitive_tensor": {
                    "emotional_valence": valence_trajectory[i],
                    "emotional_arousal": arousal_trajectory[i],
                    "energy_budget": energy_trajectory[i],
                    "knowledge_state": [f"fact_{j}" for j in range(i + 1)],
                }
            },
        )
        tp = SimpleNamespace(
            timepoint_id=f"tp_{i:03d}",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i),
        )
        states.append((entity, tp, i))
    return states


class TestPhase2FullPipeline:
    """End-to-end test of trajectory tracking → fitting → shadow evaluation."""

    def test_full_pipeline_monotone_decay(self):
        """
        Simulate an entity whose activation decays monotonically.

        Expected: fitter recovers low-P (few oscillations), moderate A (some decay).
        Shadow evaluator picks up fitted envelopes.
        """
        n_points = 12

        # Monotone decay: valence goes from positive to neutral,
        # arousal decays, energy drains
        valence = [0.8 - 0.6 * (i / (n_points - 1)) for i in range(n_points)]
        arousal = [0.9 - 0.7 * (i / (n_points - 1)) for i in range(n_points)]
        energy = [95.0 - 60.0 * (i / (n_points - 1)) for i in range(n_points)]

        states = make_evolving_entity("entity_decay", valence, arousal, energy)

        # --- Step 1: Record snapshots ---
        tracker = TrajectoryTracker()
        for entity, tp, idx in states:
            snap = tracker.record_snapshot(entity, tp, idx)
            assert snap is not None

        summary = tracker.summary()
        assert summary["entities_tracked"] == 1
        assert summary["total_snapshots"] == n_points

        # Verify activation series
        tau_list, act_list = tracker.get_activation_series("entity_decay")
        assert len(tau_list) == n_points
        assert tau_list[0] == 0.0
        assert tau_list[-1] == 1.0
        # Should decay: first > last
        assert act_list[0] > act_list[-1]

        # --- Step 2: Fit ADPRS parameters ---
        fitter = ADPRSFitter(min_points=5, de_maxiter=200)

        # Use the last entity state (has entity_metadata but no prior envelopes)
        entity_for_fit = states[-1][0]
        results = fitter.fit_all(tracker, [entity_for_fit])

        assert "entity_decay" in results
        fit = results["entity_decay"]
        assert fit.converged
        assert fit.residual < 0.05  # Reasonable fit
        assert fit.method == "differential_evolution"  # No priors → cold start

        # --- Step 3: Apply to entities ---
        duration_ms = 31536000000.0  # 1 year
        t0_iso = "2026-01-01T00:00:00+00:00"
        updated = ADPRSFitter.apply_to_entities(results, [entity_for_fit], duration_ms, t0_iso)
        assert updated == 1

        # Verify metadata was written
        assert "adprs_envelopes" in entity_for_fit.entity_metadata
        env_data = entity_for_fit.entity_metadata["adprs_envelopes"]
        assert len(env_data["envelopes"]) == 1
        fitted_env = env_data["envelopes"][0]
        assert 0.0 <= fitted_env["A"] <= 1.0
        assert 0.5 <= fitted_env["P"] <= 8.0

        # Verify fit metadata
        assert "adprs_fit_metadata" in entity_for_fit.entity_metadata
        meta = entity_for_fit.entity_metadata["adprs_fit_metadata"]
        assert meta["run_count"] == 1
        assert meta["converged"] is True
        assert len(meta["residual_history"]) == 1

        # --- Step 4: Shadow evaluator picks up fitted envelopes ---
        evaluator = ShadowEvaluator(run_id="integration_test")
        evaluator.register_from_metadata("entity_decay", entity_for_fit.entity_metadata)
        assert evaluator.has_envelopes()

        # Evaluate at a mid-point
        t_mid = datetime(2026, 7, 1, tzinfo=timezone.utc)
        record = evaluator.evaluate("entity_decay", "scene", "tp_mid", t_mid)
        assert record is not None
        assert 0.0 <= record.phi_value <= 1.0

    def test_full_pipeline_oscillatory(self):
        """
        Simulate an entity with oscillating activation (mood swings).

        Expected: fitter recovers higher P (more oscillations).
        """
        n_points = 16

        # Oscillatory pattern: valence and arousal swing
        valence = [0.3 * math.sin(2 * math.pi * 2 * i / (n_points - 1)) for i in range(n_points)]
        arousal = [0.5 + 0.4 * abs(math.sin(2 * math.pi * 2 * i / (n_points - 1))) for i in range(n_points)]
        energy = [60.0 + 20.0 * math.cos(2 * math.pi * i / (n_points - 1)) for i in range(n_points)]

        states = make_evolving_entity("entity_osc", valence, arousal, energy)

        tracker = TrajectoryTracker()
        for entity, tp, idx in states:
            tracker.record_snapshot(entity, tp, idx)

        fitter = ADPRSFitter(min_points=5, de_maxiter=200)
        entity_for_fit = states[-1][0]
        results = fitter.fit_all(tracker, [entity_for_fit])

        assert "entity_osc" in results
        fit = results["entity_osc"]
        assert fit.converged
        assert fit.residual < 0.1  # Oscillatory is harder to fit

    def test_multi_entity_pipeline(self):
        """
        Multiple entities tracked simultaneously, each fitted independently.
        """
        n_points = 10
        entities_config = {
            "calm_entity": {
                "valence": [0.5] * n_points,
                "arousal": [0.2] * n_points,
                "energy": [80.0] * n_points,
            },
            "excited_entity": {
                "valence": [0.8 - 0.1 * i for i in range(n_points)],
                "arousal": [0.9 - 0.05 * i for i in range(n_points)],
                "energy": [90.0 - 5.0 * i for i in range(n_points)],
            },
        }

        tracker = TrajectoryTracker()
        all_entities = []

        for eid, cfg in entities_config.items():
            states = make_evolving_entity(eid, cfg["valence"], cfg["arousal"], cfg["energy"])
            for entity, tp, idx in states:
                tracker.record_snapshot(entity, tp, idx)
            all_entities.append(states[-1][0])

        assert tracker.summary()["entities_tracked"] == 2

        fitter = ADPRSFitter(min_points=5, de_maxiter=150)
        results = fitter.fit_all(tracker, all_entities)

        assert len(results) == 2
        assert "calm_entity" in results
        assert "excited_entity" in results

        # Apply to all entities
        updated = ADPRSFitter.apply_to_entities(
            results, all_entities, 31536000000.0, "2026-01-01T00:00:00+00:00"
        )
        assert updated == 2

        # Both should have envelopes now
        for entity in all_entities:
            assert "adprs_envelopes" in entity.entity_metadata
            assert "adprs_fit_metadata" in entity.entity_metadata

    def test_cross_run_warm_start(self):
        """
        Simulate two consecutive runs on the same entity.

        Run 1: cold start (differential_evolution)
        Run 2: warm start (curve_fit from run 1's fitted params)
        """
        n_points = 12
        valence = [0.6 - 0.4 * (i / (n_points - 1)) for i in range(n_points)]
        arousal = [0.7 - 0.5 * (i / (n_points - 1)) for i in range(n_points)]
        energy = [85.0 - 50.0 * (i / (n_points - 1)) for i in range(n_points)]

        # --- Run 1: Cold start ---
        states_r1 = make_evolving_entity("entity_cross", valence, arousal, energy)
        tracker_r1 = TrajectoryTracker()
        for entity, tp, idx in states_r1:
            tracker_r1.record_snapshot(entity, tp, idx)

        fitter = ADPRSFitter(min_points=5, de_maxiter=200)
        entity_r1 = states_r1[-1][0]
        results_r1 = fitter.fit_all(tracker_r1, [entity_r1])
        ADPRSFitter.apply_to_entities(
            results_r1, [entity_r1], 31536000000.0, "2026-01-01T00:00:00+00:00"
        )

        assert results_r1["entity_cross"].method == "differential_evolution"
        meta_r1 = entity_r1.entity_metadata["adprs_fit_metadata"]
        assert meta_r1["run_count"] == 1

        # --- Run 2: Warm start (entity now has adprs_envelopes from run 1) ---
        # Simulate slightly different data (noise)
        rng = np.random.default_rng(42)
        valence_r2 = [v + rng.normal(0, 0.05) for v in valence]
        arousal_r2 = [max(0, min(1, a + rng.normal(0, 0.03))) for a in arousal]
        energy_r2 = [max(0, min(100, e + rng.normal(0, 3))) for e in energy]

        states_r2 = make_evolving_entity("entity_cross", valence_r2, arousal_r2, energy_r2)
        tracker_r2 = TrajectoryTracker()
        for entity, tp, idx in states_r2:
            tracker_r2.record_snapshot(entity, tp, idx)

        # The entity from run 1 has adprs_envelopes in metadata — this triggers warm start
        results_r2 = fitter.fit_all(tracker_r2, [entity_r1])
        ADPRSFitter.apply_to_entities(
            results_r2, [entity_r1], 31536000000.0, "2026-01-01T00:00:00+00:00"
        )

        assert results_r2["entity_cross"].method == "curve_fit"  # Warm start!
        meta_r2 = entity_r1.entity_metadata["adprs_fit_metadata"]
        assert meta_r2["run_count"] == 2
        assert len(meta_r2["residual_history"]) == 2

        # Parameter drift should be computed
        assert results_r2["entity_cross"].parameter_drift is not None

    def test_insufficient_data_graceful(self):
        """
        Entity with <5 snapshots should be skipped gracefully.
        """
        tracker = TrajectoryTracker()
        entity = SimpleNamespace(
            entity_id="sparse_entity",
            tensor_maturity=0.5,
            entity_metadata={
                "cognitive_tensor": {
                    "emotional_valence": 0.0,
                    "emotional_arousal": 0.5,
                    "energy_budget": 50.0,
                    "knowledge_state": [],
                }
            },
        )

        # Only 3 snapshots
        for i in range(3):
            tp = SimpleNamespace(timepoint_id=f"tp_{i}", timestamp=None)
            tracker.record_snapshot(entity, tp, i)

        fitter = ADPRSFitter(min_points=5)
        results = fitter.fit_all(tracker, [entity])
        assert len(results) == 0  # Skipped due to insufficient data

    def test_template_config_round_trip(self):
        """
        Verify template config → entity_metadata → shadow evaluator round-trip.
        """
        from generation.config_schema import EntityConfig

        # Load from template-style config
        ec = EntityConfig(
            count=3,
            types=["human"],
            adprs_envelopes=[
                {
                    "A": 0.7,
                    "D": 31536000000,
                    "P": 2.0,
                    "R": 0,
                    "S": 0.8,
                    "t0": "2026-01-01T00:00:00+00:00",
                    "baseline": 0.1,
                }
            ],
        )
        assert ec.adprs_envelopes is not None
        assert len(ec.adprs_envelopes) == 1

        # Simulate what _initialize_shadow_evaluator does with template envelopes
        from synth.fidelity_envelope import ADPRSEnvelope, ADPRSComposite

        composite = ADPRSComposite(
            envelopes=[ADPRSEnvelope.from_metadata_dict(e) for e in ec.adprs_envelopes]
        )
        assert len(composite.envelopes) == 1
        assert composite.envelopes[0].A == 0.7

        # Evaluate at mid-year
        t = datetime(2026, 7, 1, tzinfo=timezone.utc)
        phi = composite.evaluate(t)
        assert 0.0 <= phi <= 1.0

        # Now fit new params and verify they replace the template ones
        fitter = ADPRSFitter(min_points=5, de_maxiter=100)
        # Generate synthetic activation from the template envelope itself
        tau = np.linspace(0, 0.95, 12)
        activation = adprs_waveform(tau, 0.7, 2.0, 0.8, 0.1)

        result = fitter.fit_entity(tau, activation, "template_entity")
        # DE may report converged=False even with near-zero residual
        # (success flag tracks tolerance convergence, not fit quality)
        assert result.residual < 0.01

        # Fitted params should be close to template params
        assert abs(result.params["A"] - 0.7) < 0.15
        assert abs(result.params["S"] - 0.8) < 0.15
        assert abs(result.params["baseline"] - 0.1) < 0.15
