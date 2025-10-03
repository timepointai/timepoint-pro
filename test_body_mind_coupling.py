#!/usr/bin/env python3
"""
Test script for Phase 2.1: Body-Mind Coupling (Mechanism 8.1)
Tests that physical state affects cognitive state.
"""

from schemas import Entity, PhysicalTensor, CognitiveTensor, ResolutionLevel
from temporal_chain import apply_body_mind_coupling

def test_pain_coupling():
    """Test that pain reduces cognitive energy budget"""
    print("🧠 Testing Body-Mind Coupling: Pain Effects")

    # Create test entity (Washington)
    entity = Entity(
        entity_id="washington",
        entity_type="person",
        resolution_level=ResolutionLevel.TENSOR_ONLY,
        entity_metadata={}
    )

    # Set baseline physical state (healthy)
    entity.physical_tensor = PhysicalTensor(
        age=57.0,
        health_status=1.0,
        pain_level=0.0,  # No pain initially
        fever=36.5  # Normal temperature
    )

    # Set baseline cognitive state
    entity.cognitive_tensor = CognitiveTensor(
        energy_budget=100.0,  # Full energy
        emotional_valence=0.0,  # Neutral mood
        patience_threshold=50.0,
        decision_confidence=0.8,
        risk_tolerance=0.5,
        social_engagement=0.8
    )

    print(f"  📊 Baseline - Energy: {entity.cognitive_tensor.energy_budget}, Valence: {entity.cognitive_tensor.emotional_valence}")

    # Apply body-mind coupling (should have no effect since pain=0)
    entity = apply_body_mind_coupling(entity)
    baseline_energy = entity.cognitive_tensor.energy_budget
    baseline_valence = entity.cognitive_tensor.emotional_valence

    print(f"  📊 No Pain - Energy: {baseline_energy}, Valence: {baseline_valence}")

    # Now set high pain level
    physical_with_pain = entity.physical_tensor
    physical_with_pain.pain_level = 0.65  # High pain
    entity.physical_tensor = physical_with_pain

    print(f"  💥 Setting pain_level = {entity.physical_tensor.pain_level}")

    # Apply body-mind coupling again
    entity = apply_body_mind_coupling(entity)
    pained_energy = entity.cognitive_tensor.energy_budget
    pained_valence = entity.cognitive_tensor.emotional_valence

    print(f"  📊 High Pain - Energy: {pained_energy}, Valence: {pained_valence}")

    # Verify pain effects
    energy_reduction = baseline_energy - pained_energy
    valence_change = baseline_valence - pained_valence

    print(f"  🔄 Energy reduction: {energy_reduction}")
    print(f"  🔄 Valence change: {valence_change}")

    # Test assertions
    assert energy_reduction > 30, f"Expected energy reduction > 30, got {energy_reduction}"
    assert valence_change > 0.15, f"Expected valence reduction > 0.15, got {valence_change}"

    print("  ✅ Pain coupling test PASSED")
    return True

def test_fever_coupling():
    """Test that fever affects cognitive decision confidence"""
    print("\n🌡️ Testing Body-Mind Coupling: Fever Effects")

    # Create test entity
    entity = Entity(
        entity_id="jefferson",
        entity_type="person",
        resolution_level=ResolutionLevel.TENSOR_ONLY,
        entity_metadata={}
    )

    # Set physical state with high fever
    entity.physical_tensor = PhysicalTensor(
        age=45.0,
        health_status=0.6,
        pain_level=0.0,
        fever=39.5  # High fever (>38.5 threshold)
    )

    # Set baseline cognitive state
    entity.cognitive_tensor = CognitiveTensor(
        energy_budget=100.0,
        emotional_valence=0.0,
        patience_threshold=50.0,
        decision_confidence=0.8,
        risk_tolerance=0.5,
        social_engagement=0.8
    )

    print(f"  📊 Baseline - Confidence: {entity.cognitive_tensor.decision_confidence}, Risk: {entity.cognitive_tensor.risk_tolerance}, Social: {entity.cognitive_tensor.social_engagement}")

    # Apply body-mind coupling
    entity = apply_body_mind_coupling(entity)

    print(f"  📊 High Fever - Confidence: {entity.cognitive_tensor.decision_confidence}, Risk: {entity.cognitive_tensor.risk_tolerance}, Social: {entity.cognitive_tensor.social_engagement}")

    # Verify fever effects
    assert entity.cognitive_tensor.decision_confidence < 0.8, f"Expected confidence < 0.8, got {entity.cognitive_tensor.decision_confidence}"
    assert entity.cognitive_tensor.risk_tolerance > 0.5, f"Expected risk tolerance > 0.5, got {entity.cognitive_tensor.risk_tolerance}"
    assert entity.cognitive_tensor.social_engagement < 0.8, f"Expected social engagement < 0.8, got {entity.cognitive_tensor.social_engagement}"

    print("  ✅ Fever coupling test PASSED")
    return True

if __name__ == "__main__":
    print("🧪 Running Body-Mind Coupling Tests (Phase 2.1)")
    print("=" * 50)

    try:
        test_pain_coupling()
        test_fever_coupling()
        print("\n🎉 All Body-Mind Coupling tests PASSED!")
        print("✅ Phase 2.1 implementation complete")

    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        raise
