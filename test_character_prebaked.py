#!/usr/bin/env python3
"""
Test Character-Based Prebaked Examples

Validates that the three new deep temporal examples load correctly
and contain all expected mechanism metadata.
"""

from generation.config_schema import SimulationConfig

def test_scarlet_study_deep():
    """Test The Scarlet Study deep temporal configuration"""
    print("\n" + "="*70)
    print("TEST 1: The Scarlet Study (Pearl Mode, 101 Timepoints)")
    print("="*70)

    config = SimulationConfig.example_scarlet_study_deep()

    # Validate basic structure
    assert config.world_id == "scarlet_study_deep"
    assert config.entities.count == 5
    assert config.entities.animism_level == 3
    assert "building" in config.entities.types
    assert "abstract" in config.entities.types

    # Validate temporal depth
    total_timepoints = (
        config.timepoints.count +
        config.timepoints.before_count +
        config.timepoints.after_count
    )
    assert total_timepoints == 101, f"Expected 101 timepoints, got {total_timepoints}"

    # Validate temporal mode
    assert config.temporal.mode.value == "pearl"
    assert config.temporal.enable_counterfactuals == True

    # Validate mechanism coverage
    mechanisms = config.metadata.get("mechanisms_featured", [])
    assert len(mechanisms) == 17, f"Expected 17 mechanisms, got {len(mechanisms)}"

    # Validate character TTM tensors
    character_tensors = config.metadata.get("character_ttm_tensors", {})
    assert "detective" in character_tensors
    assert "doctor" in character_tensors
    assert "criminal" in character_tensors

    print(f"✓ World ID: {config.world_id}")
    print(f"✓ Entities: {config.entities.count}")
    print(f"✓ Timepoints: {total_timepoints}")
    print(f"✓ Temporal Mode: {config.temporal.mode.value}")
    print(f"✓ Mechanisms: {len(mechanisms)}/17")
    print(f"✓ Character Tensors: {list(character_tensors.keys())}")
    print(f"✓ Expected Training Examples: {config.metadata.get('expected_training_examples')}")

    # Estimate cost
    cost_estimate = config.estimate_cost()
    print(f"✓ Estimated Cost: ${cost_estimate['min_usd']:.2f} - ${cost_estimate['max_usd']:.2f}")

    print("\n✅ TEST PASSED: Scarlet Study config is valid")
    return config


def test_empty_house_flashback():
    """Test The Empty House nonlinear configuration"""
    print("\n" + "="*70)
    print("TEST 2: The Empty House (Nonlinear Mode, 81 Timepoints)")
    print("="*70)

    config = SimulationConfig.example_empty_house_flashback()

    # Validate basic structure
    assert config.world_id == "empty_house_flashback"
    assert config.entities.count == 4
    assert config.entities.animism_level == 2

    # Validate temporal depth
    total_timepoints = (
        config.timepoints.count +
        config.timepoints.before_count +
        config.timepoints.after_count
    )
    assert total_timepoints == 81, f"Expected 81 timepoints, got {total_timepoints}"

    # Validate nonlinear mode
    assert config.temporal.mode.value == "nonlinear"

    # Validate narrative structure
    assert config.metadata.get("narrative_structure") == "nonlinear_flashback"

    print(f"✓ World ID: {config.world_id}")
    print(f"✓ Entities: {config.entities.count}")
    print(f"✓ Timepoints: {total_timepoints}")
    print(f"✓ Temporal Mode: {config.temporal.mode.value}")
    print(f"✓ Narrative Structure: {config.metadata.get('narrative_structure')}")
    print(f"✓ Expected Training Examples: {config.metadata.get('expected_training_examples')}")

    # Estimate cost
    cost_estimate = config.estimate_cost()
    print(f"✓ Estimated Cost: ${cost_estimate['min_usd']:.2f} - ${cost_estimate['max_usd']:.2f}")

    print("\n✅ TEST PASSED: Empty House config is valid")
    return config


def test_final_problem_branching():
    """Test The Final Problem branching configuration"""
    print("\n" + "="*70)
    print("TEST 3: The Final Problem (Branching Mode, 61 Timepoints × 4 Branches)")
    print("="*70)

    config = SimulationConfig.example_final_problem_branching()

    # Validate basic structure
    assert config.world_id == "final_problem_branching"
    assert config.entities.count == 4
    assert config.entities.animism_level == 3

    # Validate temporal depth
    total_timepoints = (
        config.timepoints.count +
        config.timepoints.before_count +
        config.timepoints.after_count
    )
    assert total_timepoints == 61, f"Expected 61 timepoints, got {total_timepoints}"

    # Validate branching mode
    assert config.temporal.mode.value == "branching"
    assert config.temporal.enable_counterfactuals == True

    # Validate branching metadata
    branch_count = config.metadata.get("branch_count")
    assert branch_count == 4, f"Expected 4 branches, got {branch_count}"

    branching_points = config.metadata.get("branching_points", [])
    assert len(branching_points) == 4

    print(f"✓ World ID: {config.world_id}")
    print(f"✓ Entities: {config.entities.count}")
    print(f"✓ Timepoints: {total_timepoints}")
    print(f"✓ Temporal Mode: {config.temporal.mode.value}")
    print(f"✓ Branches: {branch_count}")
    print(f"✓ Branching Points: {branching_points}")
    print(f"✓ Expected Training Examples: {config.metadata.get('expected_training_examples')}")

    # Estimate cost
    cost_estimate = config.estimate_cost()
    print(f"✓ Estimated Cost: ${cost_estimate['min_usd']:.2f} - ${cost_estimate['max_usd']:.2f}")

    print("\n✅ TEST PASSED: Final Problem config is valid")
    return config


def test_all_examples():
    """Run all validation tests"""
    print("\n" + "="*70)
    print("VALIDATING CHARACTER-BASED PREBAKED EXAMPLES")
    print("="*70)

    configs = []

    try:
        configs.append(test_scarlet_study_deep())
        configs.append(test_empty_house_flashback())
        configs.append(test_final_problem_branching())

        # Summary
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)

        total_timepoints = sum(
            c.timepoints.count + c.timepoints.before_count + c.timepoints.after_count
            for c in configs
        )
        total_examples = sum(
            c.metadata.get("expected_training_examples", 0)
            for c in configs
        )

        total_cost_min = sum(c.estimate_cost()["min_usd"] for c in configs)
        total_cost_max = sum(c.estimate_cost()["max_usd"] for c in configs)

        print(f"\n✓ Total Configurations: {len(configs)}")
        print(f"✓ Total Timepoints: {total_timepoints}")
        print(f"✓ Total Training Examples: {total_examples}")
        print(f"✓ Total Estimated Cost: ${total_cost_min:.2f} - ${total_cost_max:.2f}")

        print("\n✅ ALL TESTS PASSED")
        print("\nThese configurations are ready for:")
        print("  1. Multi-modal rendering (Pearl, Directorial, Nonlinear, Branching, Cyclical)")
        print("  2. Character-specific TTM tensor training")
        print("  3. Fine-tuning data generation")
        print("  4. Oxen upload with experiment branches")

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = test_all_examples()
    sys.exit(0 if success else 1)
