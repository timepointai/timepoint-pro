#!/usr/bin/env python3
"""
check_deps.py - Check if all required dependencies are installed
"""
import sys

required = {
    'sqlmodel': 'sqlmodel',
    'bleach': 'bleach',
    'hydra': 'hydra-core',
    'pytest': 'pytest',
    'pytest_asyncio': 'pytest-asyncio',
    'pytest_cov': 'pytest-cov',
    'dotenv': 'python-dotenv',
}

print("Checking test dependencies...\n")

missing = []
installed = []

for module, package in required.items():
    try:
        __import__(module)
        print(f"✅ {package}")
        installed.append(package)
    except ImportError:
        print(f"❌ {package}")
        missing.append(package)

print(f"\nInstalled: {len(installed)}/{len(required)}")

if missing:
    print(f"\n⚠️  Missing {len(missing)} package(s):")
    for pkg in missing:
        print(f"   - {pkg}")

    print(f"\nTo install missing dependencies:")
    print(f"  pip install {' '.join(missing)}")
    print(f"\nOr install all at once:")
    print(f"  pip install -r requirements-test.txt")
    sys.exit(1)
else:
    print("\n✅ All test dependencies installed!")
    print("\nReady to run tests:")
    print("  pytest --collect-only  # Verify test collection")
    print("  pytest -v              # Run all tests")
    print("  pytest -m unit -v      # Run unit tests only")
    sys.exit(0)
