#!/usr/bin/env python3
"""
mechanism_dashboard.py - Mechanism Coverage Dashboard

Generates a comprehensive dashboard showing:
1. Test coverage by mechanism
2. @track_mechanism decorator usage
3. Test pass rates
4. Overall mechanism health

Usage:
    python3.10 mechanism_dashboard.py
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Mechanism definitions
MECHANISMS = {
    "M1": {"name": "Heterogeneous Fidelity (Entity Lifecycle)", "category": "Workflow & Temporal"},
    "M2": {"name": "Progressive Training", "category": "Workflow & Temporal"},
    "M3": {"name": "Exposure Event Tracking", "category": "Special Entity Types"},
    "M4": {"name": "Physics Validation", "category": "Entity State & Validation"},
    "M5": {"name": "Query Resolution with Lazy Elevation", "category": "Query Interface"},
    "M6": {"name": "TTM Tensor Compression", "category": "Entity State & Validation"},
    "M7": {"name": "Causal Temporal Chains", "category": "Workflow & Temporal"},
    "M8": {"name": "Embodied States (Pain/Illness)", "category": "Entity State & Validation"},
    "M9": {"name": "On-Demand Entity Generation", "category": "Query Interface"},
    "M10": {"name": "Scene-Level Entity Management", "category": "Query Interface"},
    "M11": {"name": "Dialog Synthesis", "category": "Entity State & Validation"},
    "M12": {"name": "Counterfactual Branching", "category": "Query Interface"},
    "M13": {"name": "Multi-Entity Synthesis", "category": "Query Interface"},
    "M14": {"name": "Circadian Patterns", "category": "Entity State & Validation"},
    "M15": {"name": "Entity Prospection", "category": "Entity State & Validation"},
    "M16": {"name": "Animistic Entities", "category": "Special Entity Types"},
    "M17": {"name": "Modal Temporal Causality", "category": "Workflow & Temporal"},
}

# Test file mapping
TEST_FILES = {
    "M5": "tests/mechanisms/test_m5_query_resolution.py",
    "M9": "tests/mechanisms/test_m9_on_demand_generation.py",
    "M10": "tests/mechanisms/test_scene_queries.py",
    "M12": "tests/mechanisms/test_branching_integration.py",
    "M13": "tests/integration/test_phase3_dialog_multi_entity.py",
}


def find_track_mechanism_decorators() -> Dict[str, List[Tuple[str, int, str]]]:
    """Find all @track_mechanism decorator usages"""
    decorators = {}

    cmd = ["grep", "-rn", "@track_mechanism", "--include=*.py", "."]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
        for line in result.stdout.strip().split('\n'):
            if not line or 'venv' in line or '.venv' in line:
                continue

            parts = line.split(':')
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = parts[1]
                content = ':'.join(parts[2:]).strip()

                # Extract mechanism ID from decorator
                if '"M' in content:
                    mech_id = content.split('"')[1]
                    if mech_id not in decorators:
                        decorators[mech_id] = []
                    decorators[mech_id].append((file_path, int(line_num), content))
    except Exception as e:
        print(f"Warning: Could not search for decorators: {e}")

    return decorators


def get_test_results() -> Dict[str, Dict]:
    """Get test results from recent test execution logs"""
    test_results = {}

    # Check for recent test tracking logs
    log_dir = Path("logs/test_tracking")
    if log_dir.exists():
        # Get most recent log for each test file
        for mech_id, test_file in TEST_FILES.items():
            latest_result = None
            latest_time = None

            for log_file in log_dir.glob("*.json"):
                try:
                    with open(log_file, 'r') as f:
                        data = json.load(f)
                        if 'files' in data:
                            files_data = data.get('files', {})
                            # Handle both dict (new) and list (legacy) formats
                            if isinstance(files_data, dict):
                                for file_path, file_info in files_data.items():
                                    if test_file in file_path:
                                        log_time = datetime.fromisoformat(file_info.get('modified', ''))
                                        if latest_time is None or log_time > latest_time:
                                            latest_time = log_time
                                            latest_result = file_info
                            elif isinstance(files_data, list):
                                for file_data in files_data:
                                    if test_file in file_data.get('filename', ''):
                                        log_time = datetime.fromisoformat(file_data.get('modified', ''))
                                        if latest_time is None or log_time > latest_time:
                                            latest_time = log_time
                                            latest_result = file_data
                except Exception:
                    continue

            if latest_result:
                test_results[mech_id] = latest_result

    return test_results


def print_dashboard():
    """Print comprehensive mechanism dashboard"""
    decorators = find_track_mechanism_decorators()
    test_results = get_test_results()

    print("=" * 100)
    print("🎯 MECHANISM COVERAGE DASHBOARD")
    print("=" * 100)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Group by category
    categories = {}
    for mech_id, info in MECHANISMS.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(mech_id)

    # Overall summary
    tracked_count = len(decorators)
    tested_count = len(test_results)
    total_count = len(MECHANISMS)

    print("📊 OVERALL STATUS")
    print("─" * 100)
    print(f"  Mechanisms with @track_mechanism: {tracked_count}/{total_count} ({tracked_count/total_count*100:.1f}%)")
    print(f"  Mechanisms with pytest tests:     {tested_count}/{total_count} ({tested_count/total_count*100:.1f}%)")
    print()

    # Test pass rates
    if test_results:
        print("✅ TEST PASS RATES")
        print("─" * 100)
        total_passed = 0
        total_tests = 0
        for mech_id, result in sorted(test_results.items()):
            outcomes = result.get('outcomes', {})
            passed = outcomes.get('passed', 0)
            failed = outcomes.get('failed', 0)
            total = passed + failed
            total_passed += passed
            total_tests += total
            pass_rate = (passed / total * 100) if total > 0 else 0
            status_icon = "✅" if pass_rate == 100 else "⚠️" if pass_rate >= 90 else "❌"
            print(f"  {status_icon} {mech_id:4} {MECHANISMS[mech_id]['name']:45} {passed:2}/{total:2} ({pass_rate:5.1f}%)")

        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"\n  {'OVERALL':52} {total_passed:2}/{total_tests:2} ({overall_pass_rate:5.1f}%)")
        print()

    # Detailed breakdown by category
    for category in sorted(categories.keys()):
        print(f"\n📂 {category.upper()}")
        print("─" * 100)
        print(f"  {'ID':4} {'Mechanism':45} {'Tracked':8} {'Tested':8} {'Status':10}")
        print("─" * 100)

        for mech_id in sorted(categories[category]):
            name = MECHANISMS[mech_id]["name"]
            has_decorator = "✅" if mech_id in decorators else "❌"
            has_tests = "✅" if mech_id in test_results else "❌"

            # Determine overall status
            if mech_id in decorators and mech_id in test_results:
                result = test_results[mech_id]
                outcomes = result.get('outcomes', {})
                passed = outcomes.get('passed', 0)
                failed = outcomes.get('failed', 0)
                total = passed + failed
                pass_rate = (passed / total * 100) if total > 0 else 0
                if pass_rate == 100:
                    status = "🟢 PERFECT"
                elif pass_rate >= 90:
                    status = "🟡 GOOD"
                elif pass_rate >= 70:
                    status = "🟠 OK"
                else:
                    status = "🔴 NEEDS WORK"
            elif mech_id in decorators or mech_id in test_results:
                status = "🟡 PARTIAL"
            else:
                status = "⚪ NOT TRACKED"

            print(f"  {mech_id:4} {name:45} {has_decorator:8} {has_tests:8} {status:20}")

    print("\n" + "=" * 100)
    print("🎯 NEXT STEPS")
    print("=" * 100)

    # Identify gaps
    not_tracked = [m for m in MECHANISMS.keys() if m not in decorators]
    not_tested = [m for m in MECHANISMS.keys() if m not in test_results]

    if not_tracked:
        print(f"\n⚠️  Mechanisms WITHOUT @track_mechanism decorator ({len(not_tracked)}):")
        for mech_id in sorted(not_tracked):
            print(f"   - {mech_id}: {MECHANISMS[mech_id]['name']}")

    if not_tested:
        print(f"\n⚠️  Mechanisms WITHOUT pytest tests ({len(not_tested)}):")
        for mech_id in sorted(not_tested):
            print(f"   - {mech_id}: {MECHANISMS[mech_id]['name']}")

    if not not_tracked and not not_tested:
        print("\n🎉 ALL MECHANISMS ARE TRACKED AND TESTED!")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    print_dashboard()
