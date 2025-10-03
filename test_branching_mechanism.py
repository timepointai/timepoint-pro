#!/usr/bin/env python3
"""
test_branching_mechanism.py - Test Mechanism 12: Counterfactual Branching
"""

import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from schemas import Timeline, Timepoint, Intervention, BranchComparison
from workflows import (
    create_counterfactual_branch,
    apply_intervention_to_timepoint,
    compare_timelines,
    find_first_divergence
)
from validation import (
    validate_branch_consistency,
    validate_intervention_plausibility,
    validate_timeline_divergence
)

class MockStore:
    """Mock store for testing branching functionality"""

    def __init__(self):
        self.timelines = {}
        self.timepoints = {}

    def save_timeline(self, timeline):
        self.timelines[timeline.timeline_id] = timeline
        return timeline

    def get_timeline(self, timeline_id):
        return self.timelines.get(timeline_id)

    def get_timepoints(self, timeline_id):
        return [tp for tp in self.timepoints.values() if getattr(tp, 'timeline_id', None) == timeline_id]

    def save_timepoint(self, timepoint):
        # Use timepoint_id as key
        self.timepoints[timepoint.timepoint_id] = timepoint
        return timepoint

def test_intervention_schema():
    """Test Intervention schema creation"""
    print("🧪 Testing Intervention schema...")

    # Test entity removal intervention
    intervention1 = Intervention(
        type="entity_removal",
        target="hamilton",
        description="Remove Hamilton from the cabinet meeting"
    )

    assert intervention1.type == "entity_removal"
    assert intervention1.target == "hamilton"
    assert intervention1.description == "Remove Hamilton from the cabinet meeting"

    # Test entity modification intervention
    intervention2 = Intervention(
        type="entity_modification",
        target="washington",
        parameters={"modifications": {"personality": "more_decisive"}},
        description="Make Washington more decisive"
    )

    assert intervention2.type == "entity_modification"
    assert intervention2.parameters["modifications"]["personality"] == "more_decisive"

    # Test event cancellation intervention
    intervention3 = Intervention(
        type="event_cancellation",
        target="cabinet_meeting",
        description="Cancel the cabinet meeting"
    )

    assert intervention3.type == "event_cancellation"
    assert intervention3.target == "cabinet_meeting"

    print("✅ Intervention schema tests passed!")

def test_apply_intervention():
    """Test applying interventions to timepoints"""
    print("\n🧪 Testing intervention application...")

    # Create test timepoint
    timepoint = Timepoint(
        timepoint_id="test_meeting",
        timestamp=datetime(1789, 4, 20, 14, 0),  # April 20, 1789, 2 PM
        event_description="Cabinet meeting with Hamilton, Jefferson, and Washington",
        entities_present=["washington", "hamilton", "jefferson"]
    )

    # Test entity removal intervention
    intervention1 = Intervention(
        type="entity_removal",
        target="hamilton",
        description="Remove Hamilton from meeting"
    )

    modified_tp1 = apply_intervention_to_timepoint(timepoint, intervention1, "branch_001")

    assert "hamilton" not in modified_tp1.entities_present
    assert "washington" in modified_tp1.entities_present
    assert "jefferson" in modified_tp1.entities_present
    assert "Note: hamilton was not present" in modified_tp1.event_description

    # Test event cancellation intervention
    intervention2 = Intervention(
        type="event_cancellation",
        target="cabinet_meeting",
        description="Cancel the cabinet meeting"
    )

    modified_tp2 = apply_intervention_to_timepoint(timepoint, intervention2, "branch_002")

    assert modified_tp2.event_description.startswith("EVENT CANCELLED:")

    # Test entity modification intervention
    intervention3 = Intervention(
        type="entity_modification",
        target="washington",
        parameters={"modifications": {"confidence": "higher", "mood": "serious"}},
        description="Modify Washington's demeanor"
    )

    modified_tp3 = apply_intervention_to_timepoint(timepoint, intervention3, "branch_003")

    assert "Modified: washington confidence=higher, mood=serious" in modified_tp3.event_description

    print("✅ Intervention application tests passed!")

def test_branch_creation():
    """Test creating counterfactual branches"""
    print("\n🧪 Testing branch creation...")

    store = MockStore()

    # Create baseline timeline
    baseline_timeline_id = "baseline_001"

    # Create timepoints for baseline timeline
    tp1 = Timepoint(
        timepoint_id="inauguration",
        timestamp=datetime(1789, 4, 30, 12, 0),
        event_description="Washington's inauguration ceremony",
        entities_present=["washington", "adams", "jefferson"],
        timeline_id=baseline_timeline_id
    )

    tp2 = Timepoint(
        timepoint_id="cabinet_meeting",
        timestamp=datetime(1789, 5, 1, 14, 0),
        event_description="First cabinet meeting with Hamilton and Jefferson",
        entities_present=["washington", "hamilton", "jefferson"],
        timeline_id=baseline_timeline_id
    )

    store.save_timepoint(tp1)
    store.save_timepoint(tp2)

    # Create baseline timeline record
    baseline_timeline = Timeline(
        timeline_id=baseline_timeline_id,
        timepoint_id="inauguration",
        timestamp=datetime(1789, 4, 30, 12, 0),
        resolution="day",
        entities_present=["washington", "adams", "jefferson"]
    )
    store.save_timeline(baseline_timeline)

    # Create intervention: Remove Hamilton from cabinet meeting
    intervention = Intervention(
        type="entity_removal",
        target="hamilton",
        description="Hamilton absent from first cabinet meeting"
    )

    # Create counterfactual branch
    branch_timeline_id = create_counterfactual_branch(
        baseline_timeline_id,
        "cabinet_meeting",
        intervention,
        store
    )

    # Verify branch was created
    branch_timeline = store.get_timeline(branch_timeline_id)
    assert branch_timeline is not None
    assert branch_timeline.parent_timeline_id == baseline_timeline_id
    assert branch_timeline.branch_point == "cabinet_meeting"
    assert "hamilton absent" in branch_timeline.intervention_description.lower()

    # Verify branch timepoints
    branch_timepoints = store.get_timepoints(branch_timeline_id)
    assert len(branch_timepoints) >= 2  # Should have copied timepoints

    # Find the modified cabinet meeting
    modified_meeting = None
    for tp in branch_timepoints:
        if tp.timepoint_id == "cabinet_meeting":
            modified_meeting = tp
            break

    assert modified_meeting is not None
    assert "hamilton" not in modified_meeting.entities_present
    assert modified_meeting.timeline_id == branch_timeline_id

    print("✅ Branch creation tests passed!")

def test_timeline_comparison():
    """Test comparing timeline branches"""
    print("\n🧪 Testing timeline comparison...")

    store = MockStore()

    # Create two timelines with differences
    baseline_id = "baseline"
    counterfactual_id = "counterfactual"

    # Baseline timepoints
    baseline_tp1 = Timepoint(
        timepoint_id="event1",
        timestamp=datetime(1789, 1, 1),
        event_description="Original event 1",
        entities_present=["a", "b", "c"],
        timeline_id=baseline_id
    )

    baseline_tp2 = Timepoint(
        timepoint_id="event2",
        timestamp=datetime(1789, 1, 2),
        event_description="Original event 2",
        entities_present=["a", "b", "c"],
        timeline_id=baseline_id
    )

    # Counterfactual timepoints (diverge at event2)
    counterfactual_tp1 = Timepoint(
        timepoint_id="event1_cf",
        timestamp=datetime(1789, 1, 1),
        event_description="Original event 1",
        entities_present=["a", "b", "c"],
        timeline_id=counterfactual_id
    )

    counterfactual_tp2 = Timepoint(
        timepoint_id="event2_cf",
        timestamp=datetime(1789, 1, 2),
        event_description="Modified event 2 - entity removed",
        entities_present=["a", "c"],  # b removed
        timeline_id=counterfactual_id
    )

    # Save timepoints
    for tp in [baseline_tp1, baseline_tp2, counterfactual_tp1, counterfactual_tp2]:
        store.save_timepoint(tp)

    # Compare timelines
    comparison = compare_timelines(baseline_id, counterfactual_id, store)

    print(f"Divergence point: {comparison.divergence_point}")
    print(f"Causal explanation: {comparison.causal_explanation}")
    print(f"Entity states differed: {comparison.entity_states_differed}")

    assert comparison.baseline_timeline == baseline_id
    assert comparison.counterfactual_timeline == counterfactual_id
    assert comparison.divergence_point == "event2"  # Should find divergence at event2
    assert len(comparison.entity_states_differed) > 0
    # The causal explanation should explain the divergence
    assert comparison.causal_explanation and len(comparison.causal_explanation) > 10

    # Check metrics
    assert "entity_count" in comparison.metrics
    # Entity count should be the same (both have entities a,c, and baseline also has b)
    assert comparison.metrics["entity_count"]["baseline"] >= comparison.metrics["entity_count"]["counterfactual"]
    assert len(comparison.entity_states_differed) > 0  # Should detect the entity difference

    print("✅ Timeline comparison tests passed!")

def test_branch_validation():
    """Test branching validation functions"""
    print("\n🧪 Testing branch validation...")

    # Test intervention plausibility
    valid_intervention = Intervention(
        type="entity_removal",
        target="hamilton",
        description="Remove Hamilton from meeting"
    )

    result = validate_intervention_plausibility(valid_intervention)
    assert result["valid"] == True

    # Test invalid intervention
    invalid_intervention = Intervention(
        type="invalid_type",
        target="",
        description=""
    )

    result = validate_intervention_plausibility(invalid_intervention)
    assert result["valid"] == False
    assert "invalid_type" in result["message"]

    # Test branch consistency
    valid_branch = Timeline(
        timeline_id="branch_001",
        parent_timeline_id="baseline_001",
        branch_point="intervention_point",
        intervention_description="Test intervention",
        timepoint_id="branch_root",
        timestamp=datetime(1789, 1, 1),
        resolution="day"
    )

    result = validate_branch_consistency(valid_branch)
    assert result["valid"] == True

    # Test invalid branch
    invalid_branch = Timeline(
        timeline_id="invalid_branch",
        # missing parent_timeline_id and other fields
        timepoint_id="invalid_root",
        timestamp=datetime(1789, 1, 1),
        resolution="day"
    )

    result = validate_branch_consistency(invalid_branch)
    assert result["valid"] == False

    print("✅ Branch validation tests passed!")

def test_first_divergence():
    """Test finding first divergence point"""
    print("\n🧪 Testing first divergence detection...")

    # Create timepoint lists
    baseline = [
        Timepoint(timepoint_id="tp1", event_description="Same event", entities_present=["a", "b"]),
        Timepoint(timepoint_id="tp2", event_description="Same event", entities_present=["a", "b"]),
        Timepoint(timepoint_id="tp3", event_description="Different event", entities_present=["a", "b"])
    ]

    counterfactual = [
        Timepoint(timepoint_id="tp1", event_description="Same event", entities_present=["a", "b"]),
        Timepoint(timepoint_id="tp2", event_description="Same event", entities_present=["a", "b"]),
        Timepoint(timepoint_id="tp3", event_description="Modified event", entities_present=["a", "c"])  # Different
    ]

    divergence = find_first_divergence(baseline, counterfactual)
    assert divergence == "tp3"

    # Test identical timelines
    identical_divergence = find_first_divergence(baseline[:2], baseline[:2])
    assert identical_divergence is None

    print("✅ First divergence detection tests passed!")

def main():
    """Run all counterfactual branching tests"""
    print("🌳 Testing Mechanism 12: Counterfactual Branching")
    print("=" * 60)

    try:
        test_intervention_schema()
        test_apply_intervention()
        test_branch_creation()
        test_timeline_comparison()
        test_branch_validation()
        test_first_divergence()

        print("\n" + "=" * 60)
        print("🎯 Mechanism 12 implementation successful!")
        print("✅ Counterfactual branching system working correctly")
        print("✅ Interventions properly applied to timeline branches")
        print("✅ Timeline comparison identifies meaningful differences")
        print("✅ Branch validation ensures consistency")
        print("✅ Divergence detection finds first point of difference")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
