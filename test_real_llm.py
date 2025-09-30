#!/usr/bin/env python3
"""
test_real_llm.py - Test script for real LLM functionality and 100% coverage

This script helps you test the timepoint-daedalus system with real LLM calls
to achieve 100% test coverage.

Setup:
1. Get an API key from https://openrouter.ai/keys
2. Set the environment variable: export OPENROUTER_API_KEY="your_key_here"
3. Run this script: python test_real_llm.py

This will run ALL tests with real LLM calls to achieve 100% coverage.
⚠️  Costs ~$0.01-0.05 per run
"""

import os
import sys
import subprocess

def main():
    # Check if API key is set
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY environment variable not set!")
        print()
        print("To achieve 100% test coverage with real LLM calls, follow these steps:")
        print("1. Go to https://openrouter.ai/keys")
        print("2. Create an API key")
        print("3. Set the environment variable:")
        print("   export OPENROUTER_API_KEY='your_api_key_here'")
        print("4. Run this script again")
        print()
        print("⚠️  Note: Real LLM calls cost ~$0.01-0.05 per test run")
        print()
        print("Alternatively, run tests with dry-run mode (no API key needed):")
        print("   pytest --cov  # 93% coverage, free")
        return 1

    print("✅ OPENROUTER_API_KEY detected!")
    print(f"🔥 Running ALL tests with REAL LLM calls (API key: {api_key[:8]}...)")
    print("🎯 Target: 100% test coverage")
    print("💰 Estimated cost: $0.01-0.05")
    print()

    # Run ALL tests with real API calls and coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov",
        "--verbose-tests",
        "-v",
        "--tb=short"
    ]

    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            print()
            print("🎉 SUCCESS! Check coverage report for 100% achievement!")
            print("📊 Run: pytest --cov --cov-report=html && open htmlcov/index.html")
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        return 1

if __name__ == "__main__":
    sys.exit(main())
