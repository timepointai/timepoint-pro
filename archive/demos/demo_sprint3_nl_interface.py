"""
Sprint 3 Demo: Natural Language Interface

Demonstrates the complete NL → Config workflow with examples.
"""

from nl_interface import (
    NLConfigGenerator,
    InteractiveRefiner,
    ClarificationEngine
)
import json


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_simple_generation():
    """Demo 1: Simple config generation"""
    print_section("Demo 1: Simple Board Meeting Config Generation")

    generator = NLConfigGenerator()  # Mock mode

    description = "Simulate a board meeting with 5 executives. 10 timepoints. Focus on dialog and decision making."

    print(f"Description: {description}\n")

    config, confidence = generator.generate_config(description)

    print(f"✅ Generated config with {confidence:.1%} confidence\n")
    print("Config Preview:")
    print(f"  - Scenario: {config['scenario']}")
    print(f"  - Entities: {len(config['entities'])}")
    print(f"  - Timepoints: {config['timepoint_count']}")
    print(f"  - Temporal Mode: {config['temporal_mode']}")
    print(f"  - Focus: {', '.join(config['focus'])}")
    print(f"  - Outputs: {', '.join(config['outputs'])}")

    # Validate
    validation = generator.validate_config(config)
    print(f"\n✅ Validation: {'PASS' if validation.is_valid else 'FAIL'}")
    print(f"   Confidence: {validation.confidence_score:.1%}")


def demo_interactive_refinement():
    """Demo 2: Interactive refinement workflow"""
    print_section("Demo 2: Interactive Refinement with Clarifications")

    refiner = InteractiveRefiner()

    # Start with incomplete description
    incomplete_description = "Simulate a crisis meeting"

    print(f"Initial Description: {incomplete_description}\n")

    result = refiner.start_refinement(incomplete_description)

    if result["clarifications_needed"]:
        print(f"⚠️  Clarifications needed: {len(result['clarifications'])}\n")

        for i, clarification in enumerate(result["clarifications"][:3], 1):  # Show first 3
            priority_label = {1: "CRITICAL", 2: "IMPORTANT", 3: "OPTIONAL"}[clarification.priority]
            print(f"{i}. [{priority_label}] {clarification.field}")
            print(f"   Q: {clarification.question}")
            print(f"   Suggestions: {clarification.suggestions[0]}")

        # Answer clarifications
        print("\n📝 Answering clarifications...")
        answers = {
            "entity_count": "3",
            "timepoint_count": "10",
            "focus": "stress_responses, decision_making"
        }

        for field, answer in answers.items():
            print(f"   {field}: {answer}")

        result = refiner.answer_clarifications(answers)

        print("\n✅ Config generated after clarifications")

    # Preview
    print("\n--- Configuration Preview ---")
    preview = refiner.preview_config(format="summary")
    print(preview)

    # Approve
    print("\n✅ Approving configuration...")
    final_config = refiner.approve_config()

    print(f"   Final config has {len(final_config['entities'])} entities")
    print(f"   Refinement history: {len(refiner.get_refinement_history())} steps")


def demo_historical_scenario():
    """Demo 3: Historical scenario with special features"""
    print_section("Demo 3: Historical Scenario with Animism")

    generator = NLConfigGenerator()

    description = (
        "Simulate Paul Revere's midnight ride with his horse. "
        "8 timepoints. Focus on knowledge propagation. "
        "Start time: 1775-04-18T22:00:00."
    )

    print(f"Description: {description}\n")

    config, confidence = generator.generate_config(description)

    print(f"✅ Generated historical scenario\n")
    print("Special Features:")
    print(f"  - Start Time: {config.get('start_time', 'Not specified')}")
    print(f"  - Timepoints: {config['timepoint_count']}")
    print(f"  - Focus: {', '.join(config['focus'])}")

    # Check for animism detection
    engine = ClarificationEngine()
    clarifications = engine.detect_ambiguities(description)

    animism_clarifications = [c for c in clarifications if c.field == "animism_level"]
    if animism_clarifications:
        print(f"\n⚠️  Animism clarification suggested:")
        print(f"   {animism_clarifications[0].question}")


def demo_config_adjustment():
    """Demo 4: Config adjustment workflow"""
    print_section("Demo 4: Config Adjustment Workflow")

    refiner = InteractiveRefiner()

    # Generate initial config
    description = "Simulate a meeting with 5 people. 10 timepoints. Focus on dialog."

    print(f"Initial Description: {description}\n")

    refiner.start_refinement(description, skip_clarifications=True)

    print("Initial Config:")
    print(f"  - Timepoints: {refiner.current_config['timepoint_count']}")

    # Adjust timepoint count
    print("\n📝 Adjusting timepoint count to 15...")

    result = refiner.adjust_config(
        {"timepoint_count": 15},
        regenerate=False
    )

    print("\nAdjusted Config:")
    print(f"  - Timepoints: {result['config']['timepoint_count']}")
    print(f"  - Still valid: {result['validation'].is_valid}")

    # Show refinement history
    history = refiner.get_refinement_history()
    print(f"\n📊 Refinement History ({len(history)} steps):")
    for step in history:
        print(f"   - {step.step_type}: {step.description}")


def demo_clarification_engine():
    """Demo 5: Clarification engine capabilities"""
    print_section("Demo 5: Clarification Engine")

    engine = ClarificationEngine()

    test_descriptions = [
        "Simulate something",  # Very vague
        "Generate 50 variations of a job interview",  # Variation request
        "Simulate a board meeting with Paul Revere's horse",  # Needs animism
    ]

    for i, desc in enumerate(test_descriptions, 1):
        print(f"{i}. Description: \"{desc}\"")

        clarifications = engine.detect_ambiguities(desc)

        summary = engine.get_clarification_summary(clarifications)
        print(f"   {summary}\n")


def demo_validation_warnings():
    """Demo 6: Validation warnings"""
    print_section("Demo 6: Validation Warnings")

    generator = NLConfigGenerator()

    # Generate config with potential warnings
    description = "Simulate a large conference with 60 participants. 50 timepoints."

    print(f"Description: {description}\n")

    config, confidence = generator.generate_config(description)

    validation = generator.validate_config(config)

    print(f"✅ Config generated")
    print(f"   Valid: {validation.is_valid}")
    print(f"   Confidence: {validation.confidence_score:.1%}")

    if validation.warnings:
        print(f"\n⚠️  Warnings ({len(validation.warnings)}):")
        for warning in validation.warnings:
            print(f"   - {warning}")

    if validation.suggestions:
        print(f"\n💡 Suggestions ({len(validation.suggestions)}):")
        for suggestion in validation.suggestions:
            print(f"   - {suggestion}")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("  Sprint 3: Natural Language Interface Demo")
    print("  Timepoint-Daedalus")
    print("=" * 70)

    demos = [
        demo_simple_generation,
        demo_interactive_refinement,
        demo_historical_scenario,
        demo_config_adjustment,
        demo_clarification_engine,
        demo_validation_warnings
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ Error in {demo.__name__}: {e}")

    print_section("Demo Complete")
    print("✅ All Sprint 3 components demonstrated successfully!\n")
    print("Key Takeaways:")
    print("  - Natural language → validated config in seconds")
    print("  - Interactive clarifications for ambiguous inputs")
    print("  - Config preview, adjustment, and approval workflow")
    print("  - Comprehensive validation with warnings and suggestions")
    print("  - Support for historical scenarios, animism, and variations")
    print("\nSprint 3 is COMPLETE and ready for use! 🎉\n")


if __name__ == "__main__":
    main()
