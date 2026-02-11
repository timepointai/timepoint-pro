"""
Unit tests for trajectory tracker — cognitive state snapshot accumulation.

All pure data manipulation, no LLM/DB dependencies.
"""

import pytest
from types import SimpleNamespace

from synth.trajectory_tracker import CognitiveSnapshot, TrajectoryTracker


# --- Helpers ---

def make_entity(entity_id: str, valence=0.0, arousal=0.0, energy=100.0, knowledge=None, maturity=0.5):
    """Create a mock entity with cognitive tensor metadata."""
    return SimpleNamespace(
        entity_id=entity_id,
        tensor_maturity=maturity,
        entity_metadata={
            "cognitive_tensor": {
                "emotional_valence": valence,
                "emotional_arousal": arousal,
                "energy_budget": energy,
                "knowledge_state": knowledge or [],
            }
        },
    )


def make_timepoint(tp_id: str, timestamp=None):
    """Create a mock timepoint."""
    return SimpleNamespace(timepoint_id=tp_id, timestamp=timestamp)


# --- CognitiveSnapshot.compute_activation ---

class TestComputeActivation:
    def test_neutral_state(self):
        """Neutral (valence=0, arousal=0, energy=100) → 0.45."""
        act = CognitiveSnapshot.compute_activation(0.0, 0.0, 100.0)
        # 0.4 * (0+1)/2 + 0.35 * 0 + 0.25 * (100/100)
        # = 0.4 * 0.5 + 0 + 0.25 = 0.2 + 0.25 = 0.45
        assert abs(act - 0.45) < 1e-6

    def test_max_activation(self):
        """Max state (valence=1, arousal=1, energy=100) → 1.0."""
        act = CognitiveSnapshot.compute_activation(1.0, 1.0, 100.0)
        # 0.4 * (1+1)/2 + 0.35 * 1 + 0.25 * 1 = 0.4 + 0.35 + 0.25 = 1.0
        assert abs(act - 1.0) < 1e-6

    def test_min_activation(self):
        """Min state (valence=-1, arousal=0, energy=0) → 0.0."""
        act = CognitiveSnapshot.compute_activation(-1.0, 0.0, 0.0)
        # 0.4 * (-1+1)/2 + 0 + 0 = 0
        assert abs(act - 0.0) < 1e-6

    def test_out_of_range_clamped_high(self):
        """Values beyond range should clamp to 1.0."""
        act = CognitiveSnapshot.compute_activation(2.0, 2.0, 200.0)
        assert act == 1.0

    def test_out_of_range_clamped_low(self):
        """Extreme negative values should clamp to 0.0."""
        act = CognitiveSnapshot.compute_activation(-3.0, -1.0, -100.0)
        assert act == 0.0

    def test_mid_range(self):
        """Mid-range values produce sensible output."""
        act = CognitiveSnapshot.compute_activation(0.5, 0.5, 50.0)
        # 0.4 * (0.5+1)/2 + 0.35 * 0.5 + 0.25 * 0.5
        # = 0.4 * 0.75 + 0.175 + 0.125 = 0.3 + 0.175 + 0.125 = 0.6
        assert abs(act - 0.6) < 1e-6


# --- TrajectoryTracker: record and retrieve ---

class TestTrajectoryTrackerRecord:
    def test_record_snapshot(self):
        """Recording a snapshot returns a CognitiveSnapshot and stores it."""
        tracker = TrajectoryTracker()
        entity = make_entity("e1", valence=0.5, arousal=0.3, energy=80.0)
        tp = make_timepoint("tp_0")
        snap = tracker.record_snapshot(entity, tp, 0)
        assert snap is not None
        assert snap.entity_id == "e1"
        assert snap.timepoint_index == 0

    def test_record_no_cognitive_tensor(self):
        """Entity without cognitive_tensor returns None."""
        tracker = TrajectoryTracker()
        entity = SimpleNamespace(entity_id="e1", entity_metadata={}, tensor_maturity=0.0)
        tp = make_timepoint("tp_0")
        assert tracker.record_snapshot(entity, tp, 0) is None

    def test_record_no_metadata(self):
        """Entity without entity_metadata attribute returns None."""
        tracker = TrajectoryTracker()
        entity = SimpleNamespace(entity_id="e1")
        tp = make_timepoint("tp_0")
        assert tracker.record_snapshot(entity, tp, 0) is None

    def test_get_trajectory_ordered(self):
        """get_trajectory returns snapshots ordered by timepoint_index."""
        tracker = TrajectoryTracker()
        entity = make_entity("e1", valence=0.0, arousal=0.5, energy=50.0)
        # Record out of order
        tracker.record_snapshot(entity, make_timepoint("tp_2"), 2)
        tracker.record_snapshot(entity, make_timepoint("tp_0"), 0)
        tracker.record_snapshot(entity, make_timepoint("tp_1"), 1)
        traj = tracker.get_trajectory("e1")
        assert [s.timepoint_index for s in traj] == [0, 1, 2]

    def test_get_trajectory_empty(self):
        """get_trajectory for unknown entity returns empty list."""
        tracker = TrajectoryTracker()
        assert tracker.get_trajectory("nonexistent") == []


# --- Sufficient data check ---

class TestSufficientData:
    def test_insufficient(self):
        tracker = TrajectoryTracker()
        entity = make_entity("e1")
        for i in range(3):
            tracker.record_snapshot(entity, make_timepoint(f"tp_{i}"), i)
        assert not tracker.has_sufficient_data("e1", min_points=5)

    def test_sufficient(self):
        tracker = TrajectoryTracker()
        entity = make_entity("e1")
        for i in range(6):
            tracker.record_snapshot(entity, make_timepoint(f"tp_{i}"), i)
        assert tracker.has_sufficient_data("e1", min_points=5)

    def test_unknown_entity(self):
        tracker = TrajectoryTracker()
        assert not tracker.has_sufficient_data("unknown")


# --- Tau normalization ---

class TestActivationSeries:
    def test_tau_normalized(self):
        """Tau should be normalized to [0, 1] from timepoint indices."""
        tracker = TrajectoryTracker()
        entity = make_entity("e1")
        for i in range(5):
            tracker.record_snapshot(entity, make_timepoint(f"tp_{i}"), i)
        tau_list, act_list = tracker.get_activation_series("e1")
        assert len(tau_list) == 5
        assert tau_list[0] == 0.0
        assert tau_list[-1] == 1.0

    def test_single_point(self):
        """Single point should be placed at tau=0.5."""
        tracker = TrajectoryTracker()
        entity = make_entity("e1")
        tracker.record_snapshot(entity, make_timepoint("tp_0"), 0)
        tau_list, act_list = tracker.get_activation_series("e1")
        assert len(tau_list) == 1
        assert tau_list[0] == 0.5

    def test_empty_entity(self):
        """Unknown entity returns empty lists."""
        tracker = TrajectoryTracker()
        tau_list, act_list = tracker.get_activation_series("unknown")
        assert tau_list == []
        assert act_list == []


# --- Summary ---

class TestSummary:
    def test_summary_structure(self):
        tracker = TrajectoryTracker()
        entity = make_entity("e1")
        for i in range(3):
            tracker.record_snapshot(entity, make_timepoint(f"tp_{i}"), i)
        s = tracker.summary()
        assert s["entities_tracked"] == 1
        assert s["total_snapshots"] == 3
        assert "e1" in s["per_entity"]
        assert s["per_entity"]["e1"] == 3

    def test_summary_empty(self):
        tracker = TrajectoryTracker()
        s = tracker.summary()
        assert s["entities_tracked"] == 0
        assert s["total_snapshots"] == 0


# --- get_all_entity_ids ---

class TestGetAllEntityIds:
    def test_multiple_entities(self):
        tracker = TrajectoryTracker()
        for eid in ["e1", "e2", "e3"]:
            entity = make_entity(eid)
            tracker.record_snapshot(entity, make_timepoint("tp_0"), 0)
        ids = tracker.get_all_entity_ids()
        assert set(ids) == {"e1", "e2", "e3"}
