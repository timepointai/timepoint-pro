#!/bin/bash
#
# Temporary Test Script for Character Engine
#
# This script runs the Character Engine with proper environment setup
# to generate 6,100+ character-based training examples.
#

set -e  # Exit on error

echo "=========================================="
echo "CHARACTER ENGINE TEST - TEMPORARY"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env with:"
    echo "  OPENROUTER_API_KEY=your_key"
    echo "  OXEN_API_KEY=your_key"
    exit 1
fi

# Load environment variables from .env
echo "📋 Loading environment variables from .env..."
export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)

# Set required environment variables
export OXEN_API_TOKEN="${OXEN_API_KEY}"  # Map OXEN_API_KEY to OXEN_API_TOKEN
export LLM_SERVICE_ENABLED=true
export OXEN_TEST_NAMESPACE="${OXEN_TEST_NAMESPACE:-realityinspector}"

# Verify API keys are set
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ Error: OPENROUTER_API_KEY not set in .env"
    exit 1
fi

if [ -z "$OXEN_API_TOKEN" ]; then
    echo "❌ Error: OXEN_API_KEY not set in .env"
    exit 1
fi

echo "✅ API keys loaded"
echo "✅ LLM service enabled"
echo "✅ Oxen namespace: ${OXEN_TEST_NAMESPACE}"
echo ""

# Activate virtual environment
if [ -d .venv ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Error: .venv not found"
    echo "Please create virtual environment first"
    exit 1
fi

echo ""
echo "🚀 Starting Character Engine..."
echo "=================================================="
echo ""
echo "This will:"
echo "  • Phase 1: Generate 15 deep cases (3 × 5 modes)"
echo "  • Phase 2: Generate 20 breadth scenarios"
echo "  • Phase 3: Generate 100 variations"
echo "  • Phase 4: Upload to Oxen.ai"
echo ""
echo "Expected time: 1-2 hours"
echo "Expected cost: ~$50-100"
echo ""
echo "=================================================="
echo ""

# Clean up old database to avoid UNIQUE constraint errors
if [ -f character_engine.db ]; then
    echo "🗑️  Removing old database file..."
    rm -f character_engine.db
fi

# Run the character engine
python run_character_engine.py

echo ""
echo "✅ Character Engine Complete!"
echo ""
