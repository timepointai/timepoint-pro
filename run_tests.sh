#!/bin/bash
# run_tests.sh - Unified test runner ensuring correct environment

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════"
echo "🧪 Timepoint-Daedalus Test Runner"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if Poetry is available
if command -v poetry &> /dev/null; then
    echo "📦 Using Poetry for dependency management"
    echo ""

    # Install dependencies (will use cache if already installed)
    echo "📥 Installing dependencies..."
    poetry install --with dev

    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Poetry install failed"
        exit 1
    fi

    echo ""
    echo "✅ Dependencies installed"
    echo ""

    # Run pytest through Poetry
    echo "🚀 Running tests..."
    echo ""
    poetry run pytest "$@"

else
    echo "⚠️  Poetry not found, falling back to venv"
    echo ""

    # Check if venv exists
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate venv
    source venv/bin/activate

    # Install dependencies
    echo "📥 Installing dependencies..."
    pip install -q -r requirements-test.txt

    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ pip install failed"
        exit 1
    fi

    echo ""
    echo "✅ Dependencies installed"
    echo ""

    # Run pytest
    echo "🚀 Running tests..."
    echo ""
    pytest "$@"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
