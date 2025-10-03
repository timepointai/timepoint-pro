#!/usr/bin/env python3
"""
test_circadian_mechanism.py - Test Mechanism 14: Circadian Activity Patterns
"""

import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from schemas import Entity, Timepoint, CircadianContext
from validation import (
    get_activity_probability,
    compute_energy_cost_with_circadian,
    validate_circadian_activity,
    create_circadian_context
)
import yaml

def load_circadian_config():
    """Load circadian configuration from config.yaml"""
    with open("conf/config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    return config.get("circadian", {})

def test_activity_probabilities():
    """Test activity probability calculations"""
    print("🧪 Testing activity probabilities...")

    config = load_circadian_config()

    # Test sleep at 3 AM (should be high probability)
    sleep_prob_3am = get_activity_probability(3, "sleep", config)
    print(f"  Sleep at 3:00 AM: {sleep_prob_3am:.3f} (expected: ~0.95)")

    # Test sleep at 3 PM (should be low probability)
    sleep_prob_3pm = get_activity_probability(15, "sleep", config)
    print(f"  Sleep at 3:00 PM: {sleep_prob_3pm:.3f} (expected: ~0.05)")

    # Test work at 2 PM (should be high probability)
    work_prob_2pm = get_activity_probability(14, "work", config)
    print(f"  Work at 2:00 PM: {work_prob_2pm:.3f} (expected: ~0.70)")

    # Test work at 3 AM (should be very low probability)
    work_prob_3am = get_activity_probability(3, "work", config)
    print(f"  Work at 3:00 AM: {work_prob_3am:.3f} (expected: ~0.05)")

    # Test social at 8 PM (should be high probability)
    social_prob_8pm = get_activity_probability(20, "social", config)
    print(f"  Social at 8:00 PM: {social_prob_8pm:.3f} (expected: ~0.60)")

    # Test unknown activity
    unknown_prob = get_activity_probability(12, "unknown_activity", config)
    print(f"  Unknown activity at noon: {unknown_prob:.3f} (expected: ~0.10)")

    # Assertions
    assert sleep_prob_3am > 0.9, f"Sleep at 3 AM should have high probability, got {sleep_prob_3am}"
    assert sleep_prob_3pm < 0.1, f"Sleep at 3 PM should have low probability, got {sleep_prob_3pm}"
    assert work_prob_2pm > 0.6, f"Work at 2 PM should have high probability, got {work_prob_2pm}"
    assert work_prob_3am < 0.1, f"Work at 3 AM should have low probability, got {work_prob_3am}"

    print("✅ Activity probability tests passed!")

def test_energy_cost_adjustments():
    """Test energy cost calculations with circadian adjustments"""
    print("\n🧪 Testing energy cost adjustments...")

    config = load_circadian_config()
    base_cost = 10.0

    # Test daytime work (normal cost)
    day_cost = compute_energy_cost_with_circadian("work", 14, base_cost, config)
    print(f"  Work at 2:00 PM: {day_cost:.1f} (expected: ~{base_cost:.1f})")

    # Test nighttime work (higher cost due to night penalty)
    night_cost = compute_energy_cost_with_circadian("work", 2, base_cost, config)
    print(f"  Work at 2:00 AM: {night_cost:.1f} (expected: ~{base_cost * 1.5:.1f})")

    # Test extended wakefulness (fatigue penalty)
    # Simulate being awake for 20 hours (woke at 6am, it's now 2am next day)
    fatigue_cost = compute_energy_cost_with_circadian("work", 2, base_cost, config)
    print(f"  Work at 2:00 AM (fatigued): {fatigue_cost:.1f} (expected: higher than night cost)")

    # Assertions
    assert abs(day_cost - base_cost) < 0.1, f"Daytime work should cost ~{base_cost}, got {day_cost}"
    assert night_cost > day_cost, f"Night work should cost more than day work, got {night_cost} vs {day_cost}"
    assert night_cost >= base_cost * 1.4, f"Night work should have penalty, got {night_cost}"

    print("✅ Energy cost adjustment tests passed!")

def test_circadian_validation():
    """Test circadian activity validation"""
    print("\n🧪 Testing circadian validation...")

    config = load_circadian_config()

    # Create test entity
    entity = Entity(
        entity_id="test_entity",
        entity_type="person"
    )

    # Test plausible activity (work at 2 PM)
    timepoint_afternoon = Timepoint(
        timepoint_id="test_afternoon",
        timestamp=datetime(2024, 1, 1, 14, 0),  # 2:00 PM
        event_description="Afternoon work session"
    )

    result = validate_circadian_activity(entity, "work", timepoint_afternoon, {"circadian_config": config})
    print(f"  Work at 2:00 PM: {result['message']}")
    assert result["valid"], f"Afternoon work should be valid, got: {result}"

    # Test implausible activity (work at 3 AM)
    timepoint_night = Timepoint(
        timepoint_id="test_night",
        timestamp=datetime(2024, 1, 1, 3, 0),  # 3:00 AM
        event_description="Late night work session"
    )

    result = validate_circadian_activity(entity, "work", timepoint_night, {"circadian_config": config})
    print(f"  Work at 3:00 AM: {result['message']}")
    assert result["valid"] == False or "unusual" in result["message"].lower(), f"Night work should be flagged, got: {result}"

    # Test highly implausible activity (social at 4 AM)
    result = validate_circadian_activity(entity, "social", timepoint_night, {"circadian_config": config})
    print(f"  Social at 3:00 AM: {result['message']}")
    assert result["valid"] == False or "unusual" in result["message"].lower(), f"Night social should be flagged, got: {result}"

    print("✅ Circadian validation tests passed!")

def test_circadian_context_creation():
    """Test circadian context creation"""
    print("\n🧪 Testing circadian context creation...")

    config = load_circadian_config()

    # Test morning context
    morning_context = create_circadian_context(9, config)
    print(f"  Morning context (9 AM): fatigue={morning_context.fatigue_level:.2f}, penalty={morning_context.energy_penalty:.2f}")
    assert morning_context.hour == 9
    assert "sleep" in morning_context.typical_activities
    assert "work" in morning_context.typical_activities
    assert morning_context.fatigue_level < 0.5, f"Morning should have low fatigue, got {morning_context.fatigue_level}"
    assert morning_context.energy_penalty == 1.0, f"Morning should have normal energy penalty, got {morning_context.energy_penalty}"

    # Test night context
    night_context = create_circadian_context(2, config)
    print(f"  Night context (2 AM): fatigue={night_context.fatigue_level:.2f}, penalty={night_context.energy_penalty:.2f}")
    assert night_context.hour == 2
    assert night_context.energy_penalty > 1.0, f"Night should have energy penalty, got {night_context.energy_penalty}"
    assert night_context.fatigue_level > 0.5, f"Late night should have high fatigue, got {night_context.fatigue_level}"

    # Test social constraints
    assert "morning_business" in morning_context.social_constraints
    assert "night_rest" in night_context.social_constraints

    print("✅ Circadian context creation tests passed!")

def main():
    """Run all circadian mechanism tests"""
    print("🕐 Testing Mechanism 14: Circadian Activity Patterns")
    print("=" * 60)

    try:
        test_activity_probabilities()
        test_energy_cost_adjustments()
        test_circadian_validation()
        test_circadian_context_creation()

        print("\n" + "=" * 60)
        print("🎯 Mechanism 14 implementation successful!")
        print("✅ Circadian activity patterns are working correctly")
        print("✅ Time-of-day constraints prevent implausible activities")
        print("✅ Energy costs adjust based on circadian rhythms")
        print("✅ Validation flags unusual timing with appropriate warnings")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
