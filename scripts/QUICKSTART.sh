#!/bin/bash
# QUICKSTART.sh - Quick setup and test execution

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🚀 TIMEPOINT-DAEDALUS TESTING QUICK START"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Step 1: Install dependencies
echo "📦 Step 1: Installing test dependencies..."
pip install -r requirements-test.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    echo "   Try: pip install sqlmodel bleach hydra-core pytest pytest-asyncio"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Step 2: Check dependencies
echo "🔍 Step 2: Verifying dependencies..."
python check_deps.py

if [ $? -ne 0 ]; then
    echo "❌ Some dependencies are missing - see above"
    exit 1
fi

echo ""

# Step 3: Collect tests
echo "📋 Step 3: Collecting tests..."
pytest --collect-only -q

if [ $? -ne 0 ]; then
    echo "❌ Test collection failed"
    exit 1
fi

echo "✅ Test collection successful"
echo ""

# Step 4: Run tests
echo "🧪 Step 4: Running tests..."
echo ""
echo "Choose what to run:"
echo "  1) All tests"
echo "  2) Unit tests only (fast)"
echo "  3) Integration tests"
echo "  4) System tests"
echo "  5) E2E tests"
echo "  6) Skip slow tests"
echo ""
read -p "Enter choice (1-6): " choice

case $choice in
    1)
        pytest -v
        ;;
    2)
        pytest -m unit -v
        ;;
    3)
        pytest -m integration -v
        ;;
    4)
        pytest -m system -v
        ;;
    5)
        pytest -m e2e -v
        ;;
    6)
        pytest -m "not slow" -v
        ;;
    *)
        echo "Invalid choice, running all tests..."
        pytest -v
        ;;
esac

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "✅ TESTING COMPLETE"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📚 For more information:"
echo "   cat ERRORS_FIXED.md      # Error fixes"
echo "   cat README_TESTING.md    # Quick guide"
echo "   cat TESTING.md           # Full documentation"
echo ""
