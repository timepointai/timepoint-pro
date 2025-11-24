#!/usr/bin/env python3
"""
Validate all Timepoint corporate templates instantiate correctly
===============================================================
Quick validation script to ensure all templates can be instantiated
without errors. Does NOT run the simulations (saves cost).

Usage:
    python validate_corporate_templates.py
"""
import sys
from generation.config_schema import SimulationConfig

def validate_template(name: str, template_method):
    """Try to instantiate a template and report results"""
    try:
        config = template_method()
        # Check required fields
        assert config.scenario_description, f"{name}: missing scenario_description"
        assert config.entities, f"{name}: missing entities"
        assert config.timepoints, f"{name}: missing timepoints"
        assert config.world_id, f"{name}: missing world_id"

        # Check metadata if present
        if hasattr(config, 'metadata') and config.metadata:
            if isinstance(config.metadata, dict):
                # Check for emergent_format flag in corporate templates
                assert 'emergent_format' in config.metadata, f"{name}: missing emergent_format flag"
                assert config.metadata['emergent_format'] == True, f"{name}: emergent_format should be True"

        print(f"✅ {name:40s} - Valid")
        return True
    except Exception as e:
        print(f"❌ {name:40s} - ERROR: {str(e)[:80]}")
        return False

def main():
    print("=" * 80)
    print("CORPORATE TEMPLATE VALIDATION")
    print("=" * 80)
    print()

    templates = [
        # Formation analysis templates (Phase 4)
        ("timepoint_ipo_reverse_engineering", SimulationConfig.timepoint_ipo_reverse_engineering),
        ("timepoint_acquisition_scenarios", SimulationConfig.timepoint_acquisition_scenarios),
        ("timepoint_cofounder_configurations", SimulationConfig.timepoint_cofounder_configurations),
        ("timepoint_equity_performance_incentives", SimulationConfig.timepoint_equity_performance_incentives),
        ("timepoint_critical_formation_decisions", SimulationConfig.timepoint_critical_formation_decisions),
        ("timepoint_success_vs_failure_paths", SimulationConfig.timepoint_success_vs_failure_paths),

        # Emergent growth templates (Phase 5)
        ("timepoint_launch_marketing_campaigns", SimulationConfig.timepoint_launch_marketing_campaigns),
        ("timepoint_staffing_and_growth", SimulationConfig.timepoint_staffing_and_growth),

        # Personality × governance templates (Phase 3)
        ("timepoint_founder_personality_archetypes", SimulationConfig.timepoint_founder_personality_archetypes),
        ("timepoint_charismatic_founder_archetype", SimulationConfig.timepoint_charismatic_founder_archetype),
        ("timepoint_demanding_genius_archetype", SimulationConfig.timepoint_demanding_genius_archetype),
    ]

    results = []
    for name, method in templates:
        success = validate_template(name, method)
        results.append(success)

    # Summary
    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"Total templates: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed}")

    if failed == 0:
        print()
        print("🎉 SUCCESS: All corporate templates validated!")
        print()
        print("Next steps:")
        print("  - Run actual templates: python run_all_mechanism_tests.py --timepoint-corporate-analysis-only")
        print("  - Or run quick tests: python run_all_mechanism_tests.py")
        return 0
    else:
        print()
        print("❌ FAILURE: Some templates failed validation")
        print("Fix errors above before running full tests")
        return 1

if __name__ == "__main__":
    sys.exit(main())
