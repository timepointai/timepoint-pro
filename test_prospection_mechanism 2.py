#!/usr/bin/env python3
"""
test_prospection_mechanism.py - Test Mechanism 15: Entity Prospection
"""

import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from schemas import Entity, Timepoint, ProspectiveState, Expectation
from workflows import (
    compute_anxiety_from_expectations,
    estimate_energy_cost_for_preparation,
    generate_prospective_state,
    influence_behavior_from_expectations,
    update_forecast_accuracy
)
from validation import validate_prospection_consistency, validate_prospection_energy_impact

def test_anxiety_calculation():
    """Test anxiety calculation from expectations"""
    print("🧪 Testing anxiety calculation...")

    # Test with low-risk expectations (should have low anxiety)
    low_risk_expectations = [
        Expectation(
            predicted_event="Routine continues normally",
            subjective_probability=0.8,
            desired_outcome=True,
            confidence=0.9
        ),
        Expectation(
            predicted_event="Minor inconvenience",
            subjective_probability=0.2,
            desired_outcome=False,
            confidence=0.7
        )
    ]

    low_anxiety = compute_anxiety_from_expectations(low_risk_expectations)
    print(f"  Low-risk expectations anxiety: {low_anxiety:.3f} (expected: <0.3)")

    # Test with high-risk expectations (should have high anxiety)
    high_risk_expectations = [
        Expectation(
            predicted_event="Major crisis",
            subjective_probability=0.5,  # High uncertainty
            desired_outcome=False,  # Undesired outcome
            confidence=0.3  # Low confidence
        ),
        Expectation(
            predicted_event="Desired outcome fails",
            subjective_probability=0.7,  # High probability of bad outcome
            desired_outcome=False,  # Undesired outcome
            confidence=0.6
        )
    ]

    high_anxiety = compute_anxiety_from_expectations(high_risk_expectations)
    print(f"  High-risk expectations anxiety: {high_anxiety:.3f} (expected: >0.4)")

    # Assertions
    assert low_anxiety < 0.3, f"Low-risk expectations should have low anxiety, got {low_anxiety}"
    assert high_anxiety > 0.4, f"High-risk expectations should have high anxiety, got {high_anxiety}"
    assert high_anxiety > low_anxiety, f"High-risk should have more anxiety than low-risk"

    print("✅ Anxiety calculation tests passed!")

def test_energy_cost_estimation():
    """Test energy cost estimation for preparation actions"""
    print("\n🧪 Testing energy cost estimation...")

    # Test different action types
    speech_cost = estimate_energy_cost_for_preparation("prepare_speech")
    info_cost = estimate_energy_cost_for_preparation("gather_information")
    unknown_cost = estimate_energy_cost_for_preparation("unknown_action")

    print(f"  Prepare speech cost: {speech_cost} (expected: 8.0)")
    print(f"  Gather information cost: {info_cost} (expected: 5.0)")
    print(f"  Unknown action cost: {unknown_cost} (expected: 5.0)")

    # Assertions
    assert speech_cost == 8.0, f"Speech preparation should cost 8.0, got {speech_cost}"
    assert info_cost == 5.0, f"Information gathering should cost 5.0, got {info_cost}"
    assert unknown_cost == 5.0, f"Unknown actions should default to 5.0, got {unknown_cost}"

    print("✅ Energy cost estimation tests passed!")

def test_prospective_state_generation():
    """Test prospective state generation"""
    print("\n🧪 Testing prospective state generation...")

    # Create test entity and timepoint
    entity = Entity(
        entity_id="washington",
        entity_type="person"
    )
    entity.entity_metadata = {
        "knowledge_state": ["constitution_ratified", "cabinet_formed", "inauguration_approaching"]
    }

    timepoint = Timepoint(
        timepoint_id="test_tp",
        timestamp=datetime(1789, 4, 20),  # Just before inauguration
        event_description="Washington preparing for inauguration ceremony"
    )

    # Mock LLM for testing
    class MockLLM:
        def generate_structured(self, prompt, response_model=None):
            # Return mock expectations
            return [
                Expectation(
                    predicted_event="Successful inauguration",
                    subjective_probability=0.8,
                    desired_outcome=True,
                    preparation_actions=["prepare_speech", "coordinate_ceremony"],
                    confidence=0.9
                ),
                Expectation(
                    predicted_event="Public unrest",
                    subjective_probability=0.2,
                    desired_outcome=False,
                    preparation_actions=["increase_security", "prepare_contingencies"],
                    confidence=0.6
                )
            ]

    llm = MockLLM()

    # Generate prospective state
    prospective_state = generate_prospective_state(entity, timepoint, llm)

    print(f"  Generated prospective state with {len(prospective_state.expectations)} expectations")
    print(f"  Anxiety level: {prospective_state.anxiety_level:.3f}")
    print(f"  Forecast confidence: {prospective_state.forecast_confidence:.3f}")

    # Assertions
    assert len(prospective_state.expectations) > 0, "Should generate expectations"
    assert 0 <= prospective_state.anxiety_level <= 1, f"Anxiety should be 0-1, got {prospective_state.anxiety_level}"
    assert prospective_state.prospective_id.startswith("prospect_washington"), f"ID should start with prospect_washington, got {prospective_state.prospective_id}"

    print("✅ Prospective state generation tests passed!")

def test_behavior_influence():
    """Test how expectations influence entity behavior"""
    print("\n🧪 Testing behavior influence...")

    # Create entity with high energy budget
    entity = Entity(
        entity_id="test_entity",
        entity_metadata={
            "cognitive_tensor": {
                "energy_budget": 100.0,
                "emotional_valence": 0.5
            },
            "behavior_tensor": {
                "risk_tolerance": 0.8
            }
        }
    )

    # Create prospective state with high anxiety and preparation actions
    expectations = [
        Expectation(
            predicted_event="Major challenge",
            subjective_probability=0.6,
            desired_outcome=False,
            preparation_actions=["prepare_speech", "gather_information", "seek_allies"],
            confidence=0.5
        )
    ]

    prospective_state = ProspectiveState(
        prospective_id="test_prospect",
        entity_id="test_entity",
        timepoint_id="test_tp",
        expectations=[exp.model_dump() for exp in expectations],
        anxiety_level=0.9,  # High anxiety
        contingency_plans={"Major challenge": ["prepare_speech", "gather_information", "seek_allies"]}
    )

    # Apply behavior influence
    modified_entity = influence_behavior_from_expectations(entity, prospective_state)

    original_energy = entity.entity_metadata["cognitive_tensor"]["energy_budget"]
    modified_energy = modified_entity.entity_metadata["cognitive_tensor"]["energy_budget"]
    original_risk = entity.entity_metadata["behavior_tensor"]["risk_tolerance"]
    modified_risk = modified_entity.entity_metadata["behavior_tensor"]["risk_tolerance"]

    print(f"  Original energy budget: {original_energy}")
    print(f"  Modified energy budget: {modified_energy}")
    print(f"  Original risk tolerance: {original_risk}")
    print(f"  Modified risk tolerance: {modified_risk}")

    # Assertions - high anxiety should reduce risk tolerance and energy
    # Energy should be reduced due to preparation actions and anxiety
    assert modified_energy < 100.0, f"Energy should be reduced from 100.0, got {modified_energy}"
    assert modified_risk < 0.8, f"Risk tolerance should be reduced from 0.8, got {modified_risk}"

    print("✅ Behavior influence tests passed!")

def test_forecast_accuracy_update():
    """Test forecast accuracy updating"""
    print("\n🧪 Testing forecast accuracy update...")

    # Create entity with initial forecast confidence
    entity = Entity(
        entity_id="test_entity",
        entity_metadata={"forecast_confidence": 0.8}
    )

    # Test accurate prediction (should maintain/increase confidence)
    expectation = Expectation(
        predicted_event="Good outcome",
        subjective_probability=0.7,
        desired_outcome=True,
        confidence=0.8
    )

    # Accurate positive prediction
    updated_entity = update_forecast_accuracy(entity, expectation, actual_outcome=True)
    original_conf = entity.entity_metadata.get("forecast_confidence", 0.8)
    updated_conf = updated_entity.entity_metadata.get("forecast_confidence", 0.8)
    print(f"  Accurate prediction: {original_conf:.3f} → {updated_conf:.3f}")

    # Test inaccurate prediction (should reduce confidence)
    expectation_bad = Expectation(
        predicted_event="Bad outcome",
        subjective_probability=0.8,  # High confidence in wrong prediction
        desired_outcome=True,
        confidence=0.9
    )

    updated_entity2 = update_forecast_accuracy(updated_entity, expectation_bad, actual_outcome=False)
    updated_conf2 = updated_entity2.entity_metadata.get("forecast_confidence", 0.8)
    print(f"  Inaccurate prediction: {updated_conf:.3f} → {updated_conf2:.3f}")

    # Assertions
    assert updated_conf2 < updated_conf, "Inaccurate prediction should reduce confidence"

    print("✅ Forecast accuracy update tests passed!")

def test_prospection_validation():
    """Test prospection validation"""
    print("\n🧪 Testing prospection validation...")

    # Create test prospective state
    expectations = [
        Expectation(
            predicted_event="Normal day",
            subjective_probability=0.7,
            desired_outcome=True,
            confidence=0.8
        ),
        Expectation(
            predicted_event="Unexpected event",
            subjective_probability=0.02,  # Very low probability
            desired_outcome=False,
            confidence=0.9  # High confidence but low probability
        )
    ]

    prospective_state = ProspectiveState(
        prospective_id="test_prospect",
        entity_id="test_entity",
        timepoint_id="test_tp",
        expectations=[exp.model_dump() for exp in expectations],
        anxiety_level=0.3
    )

    # Test consistency validation
    result = validate_prospection_consistency(prospective_state)
    print(f"  Consistency validation: {result['message']}")

    # Should flag the unrealistic expectation
    assert not result["valid"], f"Should flag unrealistic expectation, got: {result}"

    # Test energy impact validation
    entity = Entity(entity_id="test_entity")
    entity.cognitive_tensor.energy_budget = 50.0  # Low energy budget

    energy_result = validate_prospection_energy_impact(prospective_state, entity)
    print(f"  Energy impact validation: {energy_result['message']}")

    print("✅ Prospection validation tests passed!")

def main():
    """Run all prospection mechanism tests"""
    print("🔮 Testing Mechanism 15: Entity Prospection")
    print("=" * 60)

    try:
        test_anxiety_calculation()
        test_energy_cost_estimation()
        test_prospective_state_generation()
        test_behavior_influence()
        test_forecast_accuracy_update()
        test_prospection_validation()

        print("\n" + "=" * 60)
        print("🎯 Mechanism 15 implementation successful!")
        print("✅ Entity prospection system working correctly")
        print("✅ Expectations influence behavior realistically")
        print("✅ Anxiety levels calculated from uncertainty")
        print("✅ Forecast accuracy updates confidence over time")
        print("✅ Validation catches unrealistic expectations")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
