#!/usr/bin/env python3
"""
autopilot.py - DEPRECATED

This file has been deprecated and replaced with a proper pytest-based testing system.

OLD APPROACH:
- Custom test runner with subprocess calls
- Limited pytest integration
- Manual quality validation
- Custom parallel execution

NEW APPROACH:
- Full pytest integration via conftest.py
- Unified test markers and configuration in pytest.ini
- E2E tests in test_e2e_autopilot.py
- Advanced pytest features (markers, fixtures, plugins)

MIGRATION GUIDE:

Old Command:
    python autopilot.py --dry-run

New Command:
    pytest -m e2e --collect-only

Old Command:
    python autopilot.py --parallel --workers 4

New Command:
    pytest -m e2e -n 4

Old Command:
    python autopilot.py --force

New Command:
    pytest -m e2e --real-llm

For more information, see TESTING.md

To use the new system:
1. Run unit tests: pytest -m unit
2. Run integration tests: pytest -m integration
3. Run system tests: pytest -m system
4. Run E2E tests: pytest -m e2e
5. Run everything: pytest

For quality validation:
    pytest --strict-quality --quality-threshold=0.7

For test discovery:
    pytest --collect-only

For help:
    pytest --help
    cat TESTING.md
"""
import sys

print(__doc__)
print("\n" + "="*70)
print("⚠️  WARNING: autopilot.py is deprecated")
print("="*70)
print("\nPlease use pytest directly:")
print("  pytest -m e2e          # Run E2E tests")
print("  pytest -m unit         # Run unit tests")
print("  pytest --help          # See all options")
print("\nSee TESTING.md for complete documentation")
print("="*70)

sys.exit(1)
