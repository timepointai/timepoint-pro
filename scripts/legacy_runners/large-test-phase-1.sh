#!/bin/bash
#
# Constitutional Convention Day 1 - Large-Scale Simulation Launcher
#
# This is a minimal bash wrapper that sources environment variables
# and launches the Python runner. Keeps bash simple, delegates to Python.
#
# Usage:
#   bash large-test-phase-1.sh
#
# Requirements:
#   - .env file with OPENROUTER_API_KEY
#   - Python 3.10+ with project dependencies installed
#

set -e  # Exit on error

# Print header
echo ""
echo "========================================================================"
echo "CONSTITUTIONAL CONVENTION DAY 1 - LARGE-SCALE SIMULATION"
echo "========================================================================"
echo ""

# Check if .env exists and source it
if [ -f .env ]; then
    echo "Loading environment from .env..."
    set -a  # Export all variables
    source .env
    set +a
    echo "✓ Environment loaded"
else
    echo "⚠️  No .env file found - environment variables must be set manually"
fi

echo ""

# Validate OPENROUTER_API_KEY
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ ERROR: OPENROUTER_API_KEY not set"
    echo ""
    echo "Please create .env file with:"
    echo "  OPENROUTER_API_KEY=your_key_here"
    echo ""
    echo "Or set manually:"
    echo "  export OPENROUTER_API_KEY=your_key_here"
    echo ""
    exit 1
fi

echo "✓ OPENROUTER_API_KEY verified"
echo ""

# Detect Python
if command -v python3.10 &> /dev/null; then
    PYTHON=python3.10
elif command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌ ERROR: No Python interpreter found"
    echo "   Please install Python 3.10 or later"
    exit 1
fi

echo "✓ Python detected: $PYTHON"
echo ""

# Run Python script
echo "Launching simulation..."
echo "========================================================================"
echo ""

exec $PYTHON run_constitutional_convention.py
