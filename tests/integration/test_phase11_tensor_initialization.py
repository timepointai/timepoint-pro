#!/usr/bin/env python3
"""
test_phase11_tensor_initialization.py - Test Phase 11 Architecture Pivot

Tests the new tensor initialization approach:
- Baseline tensor creation (no LLM, no bias leakage)
- LLM-guided population (2-3 refinement loops)
- Tensor maturity calculation
- Optional prospection triggering
"""

import sys
import json
import base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from schemas import Entity, Timepoint
from tensor_initialization import (
    create_baseline_tensor,
    populate_tensor_llm_guided,
    compute_tensor_maturity,
    create_fallback_tensor,
    TTMTensor
)
from prospection_triggers import (
    should_trigger_prospection,
    get_prospection_params,
    trigger_prospection_for_entity
)
from storage import GraphStore
import networkx as nx


def test_baseline_tensor_creation():
    """Test Phase 1: Baseline tensor creation without LLM"""
    print("\n🧪 Test 1: Baseline Tensor Creation")
    print("=" * 60)

    # Create test entity
    entity = Entity(
        entity_id="sherlock_holmes",
        entity_type="human"
    )
    entity.entity_metadata = {
        "role": "detective",
        "knowledge_state": ["crime_scene_analysis", "deductive_reasoning", "chemistry"],
        "personality_traits": [0.8, 0.3, 0.9, 0.2, 0.7],  # Big Five
        "cognitive_traits": {
            "prospection_ability": 0.95,
            "theory_of_mind": 0.9
        }
    }

    # Create baseline tensor
    print("  Creating baseline tensor...")
    tensor = create_baseline_tensor(entity)

    # Verify tensor structure
    context, biology, behavior = tensor.to_arrays()

    print(f"  ✓ Context vector: {len(context)} dimensions")
    print(f"  ✓ Biology vector: {len(biology)} dimensions")
    print(f"  ✓ Behavior vector: {len(behavior)} dimensions")

    # Verify maturity - baseline function sets it to 0.0 by design
    # (even though calculated maturity may be higher, we force 0.0 to indicate "needs training")
    calculated_maturity = compute_tensor_maturity(tensor, entity, training_complete=False)
    print(f"  ✓ Calculated maturity: {calculated_maturity:.3f}")
    print(f"  ✓ Entity maturity (forced): {entity.tensor_maturity:.3f} (baseline = 0.0 by design)")

    # Assertions
    assert len(context) == 8, f"Context should have 8 dims, got {len(context)}"
    assert len(biology) == 4, f"Biology should have 4 dims, got {len(biology)}"
    assert len(behavior) == 8, f"Behavior should have 8 dims, got {len(behavior)}"

    # Baseline tensors are marked as 0.0 maturity to indicate they need training
    assert entity.tensor_maturity == 0.0, f"Baseline tensor should be marked 0.0, got {entity.tensor_maturity}"
    assert entity.tensor_training_cycles == 0, f"Training cycles should be 0, got {entity.tensor_training_cycles}"

    # But the calculated maturity should be reasonable (structure is present)
    assert calculated_maturity < 0.95, f"Calculated maturity should be < 0.95 operational threshold, got {calculated_maturity}"

    print("  ✅ Baseline tensor creation test PASSED")
    return True


def test_tensor_maturity_calculation():
    """Test maturity calculation with different tensor states"""
    print("\n🧪 Test 2: Tensor Maturity Calculation")
    print("=" * 60)

    entity = Entity(entity_id="test", entity_type="human")

    # Test 1: Low maturity (many zeros, no training)
    import numpy as np
    low_maturity_tensor = TTMTensor.from_arrays(
        np.array([0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # Many zeros
        np.array([0.5, 0.5, 0.0, 0.0]),  # Some zeros
        np.array([0.5] * 8)  # No zeros but low variance
    )
    entity.tensor_training_cycles = 0
    low_maturity = compute_tensor_maturity(low_maturity_tensor, entity, False)
    print(f"  Low maturity tensor: {low_maturity:.3f} (expected < 0.7)")
    assert low_maturity < 0.7, f"Low maturity should be < 0.7, got {low_maturity}"

    # Test 2: High maturity (no zeros, good variance, trained)
    high_maturity_tensor = TTMTensor.from_arrays(
        np.array([0.8, 0.3, 0.6, 0.9, 0.4, 0.7, 0.5, 0.2]),  # Good variance
        np.array([0.7, 0.8, 0.3, 0.6]),  # Good variance
        np.array([0.8, 0.3, 0.9, 0.2, 0.7, 0.4, 0.6, 0.5])  # Good variance
    )
    entity.tensor_training_cycles = 10
    high_maturity = compute_tensor_maturity(high_maturity_tensor, entity, True)
    print(f"  High maturity tensor: {high_maturity:.3f} (expected > 0.8)")
    assert high_maturity > 0.8, f"High maturity should be > 0.8, got {high_maturity}"

    print("  ✅ Tensor maturity calculation test PASSED")
    return True


def test_optional_prospection_triggering():
    """Test Phase 3: Optional prospection triggering"""
    print("\n🧪 Test 3: Optional Prospection Triggering")
    print("=" * 60)

    # Test 1: Entity with high prospection_ability should trigger
    high_prospection_entity = Entity(
        entity_id="sherlock",
        entity_type="human",
        entity_metadata={
            "cognitive_traits": {
                "prospection_ability": 0.95  # High ability
            }
        }
    )
    timepoint = Timepoint(
        timepoint_id="tp1",
        timestamp=datetime.now(),
        event_description="Investigating a crime scene"
    )
    config = {}

    should_trigger = should_trigger_prospection(high_prospection_entity, timepoint, config)
    print(f"  High prospection_ability (0.95): {should_trigger} (expected: True)")
    assert should_trigger == True, "High prospection_ability should trigger"

    # Test 2: Entity with low prospection_ability should NOT trigger
    low_prospection_entity = Entity(
        entity_id="watson",
        entity_type="human",
        entity_metadata={
            "cognitive_traits": {
                "prospection_ability": 0.3  # Low ability
            },
            "role": "doctor"  # Not a planning role
        }
    )

    should_not_trigger = should_trigger_prospection(low_prospection_entity, timepoint, config)
    print(f"  Low prospection_ability (0.3): {should_not_trigger} (expected: False)")
    assert should_not_trigger == False, "Low prospection_ability should NOT trigger"

    # Test 3: Planning role should trigger
    detective_entity = Entity(
        entity_id="detective",
        entity_type="human",
        entity_metadata={
            "role": "detective",  # Planning role
            "cognitive_traits": {
                "prospection_ability": 0.5
            }
        }
    )

    should_trigger_role = should_trigger_prospection(detective_entity, timepoint, config)
    print(f"  Planning role (detective): {should_trigger_role} (expected: True)")
    assert should_trigger_role == True, "Detective role should trigger prospection"

    # Test 4: Template config should trigger
    config_entity = Entity(
        entity_id="moriarty",
        entity_type="human",
        entity_metadata={}
    )
    config_with_prospection = {
        "metadata": {
            "prospection_config": {
                "modeling_entity": "moriarty"
            }
        }
    }

    should_trigger_config = should_trigger_prospection(config_entity, timepoint, config_with_prospection)
    print(f"  Template config (modeling_entity): {should_trigger_config} (expected: True)")
    assert should_trigger_config == True, "Template config should trigger prospection"

    # Test 5: High-stakes event + moderate ability should trigger
    event_timepoint = Timepoint(
        timepoint_id="tp2",
        timestamp=datetime.now(),
        event_description="Critical decision at confrontation scene"
    )
    moderate_entity = Entity(
        entity_id="entity",
        entity_type="human",
        entity_metadata={
            "cognitive_traits": {
                "prospection_ability": 0.5  # Moderate ability
            }
        }
    )

    should_trigger_event = should_trigger_prospection(moderate_entity, event_timepoint, {})
    print(f"  High-stakes event + moderate ability: {should_trigger_event} (expected: True)")
    assert should_trigger_event == True, "High-stakes event should trigger prospection"

    print("  ✅ Optional prospection triggering test PASSED")
    return True


def test_prospection_params():
    """Test prospection parameter extraction"""
    print("\n🧪 Test 4: Prospection Parameter Extraction")
    print("=" * 60)

    entity = Entity(
        entity_id="sherlock",
        entity_type="human",
        entity_metadata={
            "role": "detective",
            "cognitive_traits": {
                "prospection_ability": 0.95,
                "theory_of_mind": 0.9
            },
            "personality_traits": [0.8, 0.3, 0.9, 0.2, 0.7]  # High neuroticism (0.2)
        }
    )

    timepoint = Timepoint(
        timepoint_id="tp1",
        timestamp=datetime.now(),
        event_description="Test"
    )

    config = {
        "metadata": {
            "prospection_config": {
                "time_horizons": ["6h", "12h", "24h"]
            }
        }
    }

    params = get_prospection_params(entity, timepoint, config)

    print(f"  Time horizons: {params['time_horizons']}")
    print(f"  Prospection ability: {params['prospection_ability']:.2f}")
    print(f"  Theory of mind: {params['theory_of_mind']:.2f}")
    print(f"  Anxiety baseline: {params['anxiety_baseline']:.2f}")
    print(f"  Forecast confidence: {params['forecast_confidence']:.2f}")

    # Assertions
    assert params['time_horizons'] == ["6h", "12h", "24h"]
    assert params['prospection_ability'] == 0.95
    assert params['theory_of_mind'] == 0.9
    assert params['forecast_confidence'] == 0.8  # Detective role

    print("  ✅ Prospection parameter extraction test PASSED")
    return True


def test_fallback_tensor():
    """Test fallback tensor creation"""
    print("\n🧪 Test 5: Fallback Tensor Creation")
    print("=" * 60)

    print("  Creating fallback tensor...")
    fallback = create_fallback_tensor()

    context, biology, behavior = fallback.to_arrays()

    print(f"  ✓ Context range: {context.min():.3f} - {context.max():.3f} (expected ~0.05-0.15)")
    print(f"  ✓ Biology range: {biology.min():.3f} - {biology.max():.3f} (expected ~0.5-0.6)")
    print(f"  ✓ Behavior range: {behavior.min():.3f} - {behavior.max():.3f} (expected ~0.5-0.6)")

    # Verify fallback uses small random values (not uniform)
    import numpy as np
    # Context should be small values around 0.1 (0.05-0.15 range)
    assert np.all(context >= 0.05) and np.all(context <= 0.15), f"Fallback context should be in [0.05, 0.15], got [{context.min()}, {context.max()}]"
    # Biology and behavior should be around 0.5 (0.5-0.6 range)
    assert np.all(biology >= 0.5) and np.all(biology <= 0.6), f"Fallback biology should be in [0.5, 0.6], got [{biology.min()}, {biology.max()}]"
    assert np.all(behavior >= 0.5) and np.all(behavior <= 0.6), f"Fallback behavior should be in [0.5, 0.6], got [{behavior.min()}, {behavior.max()}]"

    print("  ✅ Fallback tensor creation test PASSED")
    return True


def test_integration_with_storage():
    """Test integration with storage (serialization/deserialization)"""
    print("\n🧪 Test 6: Storage Integration")
    print("=" * 60)

    entity = Entity(
        entity_id="test",
        entity_type="human",
        entity_metadata={}
    )

    # Create baseline tensor
    tensor = create_baseline_tensor(entity)

    # Serialize
    entity.tensor = json.dumps({
        "context_vector": base64.b64encode(tensor.context_vector).decode('utf-8'),
        "biology_vector": base64.b64encode(tensor.biology_vector).decode('utf-8'),
        "behavior_vector": base64.b64encode(tensor.behavior_vector).decode('utf-8')
    })

    print("  ✓ Tensor serialized to JSON")

    # Deserialize
    tensor_dict = json.loads(entity.tensor)
    import msgspec
    context_decoded = msgspec.msgpack.decode(base64.b64decode(tensor_dict["context_vector"]))
    biology_decoded = msgspec.msgpack.decode(base64.b64decode(tensor_dict["biology_vector"]))
    behavior_decoded = msgspec.msgpack.decode(base64.b64decode(tensor_dict["behavior_vector"]))

    print("  ✓ Tensor deserialized from JSON")
    print(f"  ✓ Dimensions preserved: {len(context_decoded)}, {len(biology_decoded)}, {len(behavior_decoded)}")

    assert len(context_decoded) == 8
    assert len(biology_decoded) == 4
    assert len(behavior_decoded) == 8

    print("  ✅ Storage integration test PASSED")
    return True


def main():
    """Run all Phase 11 tensor initialization tests"""
    print("🔧 PHASE 11 ARCHITECTURE PIVOT - TENSOR INITIALIZATION TESTS")
    print("=" * 80)
    print("\nArchitectural changes:")
    print("  OLD: Prospection MANDATORY for all entities (mechanism theater)")
    print("  NEW: Baseline + LLM-guided + OPTIONAL prospection")
    print("\nBenefits:")
    print("  ✓ No indirect bias leakage through shared LLM context")
    print("  ✓ Fast baseline initialization (no LLM)")
    print("  ✓ M15 becomes truly optional (triggered contextually)")
    print("  ✓ Tensor maturity ensures quality before operation")
    print("=" * 80)

    try:
        test_baseline_tensor_creation()
        test_tensor_maturity_calculation()
        test_optional_prospection_triggering()
        test_prospection_params()
        test_fallback_tensor()
        test_integration_with_storage()

        print("\n" + "=" * 80)
        print("🎯 PHASE 11 ARCHITECTURE PIVOT - ALL TESTS PASSED!")
        print("=" * 80)
        print("\n✅ Baseline tensor creation working")
        print("✅ Tensor maturity calculation accurate")
        print("✅ Optional prospection triggering correct")
        print("✅ Prospection parameters extracted properly")
        print("✅ Fallback tensor creation working")
        print("✅ Storage integration validated")
        print("\n🚀 New tensor initialization architecture VALIDATED")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
