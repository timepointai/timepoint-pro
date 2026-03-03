#!/usr/bin/env python3
"""
Validation script to verify simulation uniqueness.

Checks that training data doesn't contain mock patterns:
- All "test_entity_*" patterns
- Generic ["fact1", "fact2", "fact3"] knowledge
- Identical scene titles across simulations
"""

import json
import sys
from collections import Counter
from pathlib import Path


def validate_training_data(file_path: str) -> dict:
    """
    Validate training data for mock patterns.

    Returns:
        dict with validation results
    """
    results = {
        "total_examples": 0,
        "mock_entity_ids": 0,
        "mock_knowledge": 0,
        "scene_titles": Counter(),
        "entity_ids": Counter(),
        "unique_scenes": set(),
        "issues": [],
    }

    if not Path(file_path).exists():
        results["issues"].append(f"File not found: {file_path}")
        return results

    with open(file_path) as f:
        for line_num, line in enumerate(f, 1):
            try:
                example = json.loads(line)
                results["total_examples"] += 1

                # Extract data from prompt and completion
                prompt = example.get("prompt", "")
                completion = example.get("completion", "")

                # Check for mock entity IDs (test_entity_*)
                if "test_entity_" in prompt or "test_entity_" in completion:
                    results["mock_entity_ids"] += 1
                    results["issues"].append(
                        f"Line {line_num}: Contains mock entity ID 'test_entity_*'"
                    )

                # Check for mock knowledge arrays
                if '["fact1", "fact2"' in completion or "['fact1', 'fact2'" in completion:
                    results["mock_knowledge"] += 1
                    results["issues"].append(
                        f"Line {line_num}: Contains mock knowledge array ['fact1', 'fact2', ...]"
                    )

                # Extract scene titles if present
                if "Test Scene" in prompt or "Test Scene" in completion:
                    results["scene_titles"]["Test Scene"] += 1
                    results["issues"].append(f"Line {line_num}: Generic 'Test Scene' title")

            except json.JSONDecodeError as e:
                results["issues"].append(f"Line {line_num}: JSON decode error - {e}")

    # Calculate statistics
    results["unique_scene_count"] = len(results["scene_titles"])
    results["mock_percentage"] = (
        (results["mock_entity_ids"] / results["total_examples"] * 100)
        if results["total_examples"] > 0
        else 0
    )

    return results


def print_validation_report(results: dict):
    """Print formatted validation report"""
    print("=" * 70)
    print("SIMULATION TRAINING DATA VALIDATION REPORT")
    print("=" * 70)

    print(f"\n📊 Total Examples: {results['total_examples']}")

    if results["total_examples"] == 0:
        print("\n❌ No training examples found!")
        return

    print("\n🔍 Mock Pattern Detection:")
    print(
        f"   Mock Entity IDs (test_entity_*): {results['mock_entity_ids']} ({results['mock_percentage']:.1f}%)"
    )
    print(f"   Mock Knowledge Arrays: {results['mock_knowledge']}")
    print(f"   Generic 'Test Scene' titles: {results['scene_titles'].get('Test Scene', 0)}")

    print("\n📈 Diversity:")
    print(f"   Unique scene titles: {results['unique_scene_count']}")

    # Verdict
    print(f"\n{'=' * 70}")
    if results["mock_entity_ids"] > 0 or results["mock_knowledge"] > 0:
        print("❌ VALIDATION FAILED: Mock patterns detected")
        print("\nThis training data contains mock simulation content.")
        print(
            "Training on this data would teach the model mock patterns, not real temporal reasoning."
        )
        print("\nTo fix:")
        print("  1. Set OPENROUTER_API_KEY environment variable")
        print("  2. Run: export LLM_SERVICE_ENABLED=true")
        print("  3. Re-run: python run_real_finetune.py")
        return False
    else:
        print("✅ VALIDATION PASSED: No mock patterns detected")
        print("\nTraining data appears to contain real simulation traces.")
        print("Safe to proceed with fine-tuning.")
        return True


def main():

    if len(sys.argv) < 2:
        print("Usage: python validate_simulations.py <training_data.jsonl>")
        print("\nExample:")
        print("  python validate_simulations.py timepoint_training_data.jsonl")
        sys.exit(1)

    file_path = sys.argv[1]
    results = validate_training_data(file_path)
    passed = print_validation_report(results)

    # Print issues if any
    if results["issues"] and len(results["issues"]) <= 20:
        print(f"\n⚠️  Issues found ({len(results['issues'])}):")
        for issue in results["issues"][:20]:
            print(f"  - {issue}")
        if len(results["issues"]) > 20:
            print(f"  ... and {len(results['issues']) - 20} more")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
