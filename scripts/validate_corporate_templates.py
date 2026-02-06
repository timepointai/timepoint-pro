#!/usr/bin/env python3
"""
Validate all verified templates instantiate correctly
=====================================================
Quick validation script to ensure all templates can be instantiated
without errors. Does NOT run the simulations (saves cost).

Usage:
    python validate_corporate_templates.py
"""
import sys
from generation.templates.loader import TemplateLoader


def validate_template(name: str, loader: TemplateLoader):
    """Try to instantiate a template and report results"""
    try:
        config = loader.load_template(name)
        # Check required fields
        assert config.scenario_description, f"{name}: missing scenario_description"
        assert config.entities, f"{name}: missing entities"
        assert config.timepoints, f"{name}: missing timepoints"
        assert config.world_id, f"{name}: missing world_id"

        print(f"  {name:40s} - Valid")
        return True
    except Exception as e:
        print(f"  {name:40s} - ERROR: {str(e)[:80]}")
        return False

def main():
    print("=" * 80)
    print("VERIFIED TEMPLATE VALIDATION")
    print("=" * 80)
    print()

    loader = TemplateLoader()
    templates = loader.list_templates(status="verified")

    results = []
    for info in templates:
        success = validate_template(info.id, loader)
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
        print("SUCCESS: All verified templates validated!")
        print()
        print("Next steps:")
        print("  - Run templates: python run_all_mechanism_tests.py")
        return 0
    else:
        print()
        print("FAILURE: Some templates failed validation")
        print("Fix errors above before running full tests")
        return 1

if __name__ == "__main__":
    sys.exit(main())
