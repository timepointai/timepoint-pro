#!/bin/bash
#
# Character Engine Runner
#
# This script runs the Character Engine with proper environment setup
# to generate character-based fine-tuning training data.
#
# Usage:
#   ./run-character-engine-test-temporary.sh                              # Standard mode
#   ./run-character-engine-test-temporary.sh --max                        # MAX mode (default: 24 entities, 50 timepoints)
#   ./run-character-engine-test-temporary.sh --max --entities 5 --timepoints 10   # Small MAX test
#   ./run-character-engine-test-temporary.sh --max --entities 124 --timepoints 200 # Full scale
#

set -e  # Exit on error
set -o pipefail  # Catch errors in pipes

# Parse arguments
MODE="standard"
if [[ "$1" == "--max" ]]; then
    MODE="max"
    shift  # Remove --max from arguments
fi

echo "=========================================="
echo "CHARACTER ENGINE TEST - TEMPORARY"
if [[ "$MODE" == "max" ]]; then
    echo "MODE: MAX (Single Massive Vertical Simulation)"
else
    echo "MODE: Standard (Multi-Modal Workflow)"
fi
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

# Estimate scale based on args
if [[ "$MODE" == "max" ]]; then
    ENTITIES=24  # default
    TIMEPOINTS=50  # default
    for arg in "$@"; do
        if [[ "$arg" =~ ^[0-9]+$ ]]; then
            if [[ -z "$ENTITIES" || "$ENTITIES" == "24" ]]; then
                ENTITIES=$arg
            else
                TIMEPOINTS=$arg
            fi
        fi
    done

    echo "MAX MODE - Single Massive Vertical Simulation"
    echo "  • One scenario with up to 124 entities (detected: $ENTITIES)"
    echo "  • Up to 200 timepoints (detected: $TIMEPOINTS)"
    echo "  • All 17 Timepoint mechanisms at maximum depth"
    echo "  • TRAINED resolution for all main characters"
    echo "  • Multiple character perspectives (4 perspectives)"
    echo "  • Dedicated Oxen repo + fine-tuning branch"
    echo ""

    # Estimate based on actual scale
    if [[ $ENTITIES -le 10 && $TIMEPOINTS -le 20 ]]; then
        echo "Scale: SMALL TEST"
        echo "Expected time: 1-2 minutes"
        echo "Expected cost: ~$0.01-0.05"
        echo "Expected examples: 20-80"
    elif [[ $ENTITIES -le 30 && $TIMEPOINTS -le 50 ]]; then
        echo "Scale: MEDIUM (recommended maximum)"
        echo "Expected time: 5-15 minutes"
        echo "Expected cost: ~$1-5"
        echo "Expected examples: 100-400"
    elif [[ $ENTITIES -le 50 && $TIMEPOINTS -le 100 ]]; then
        echo "⚠️  Scale: LARGE (may hit LLM generation limits)"
        echo "Note: Llama 405B struggles to generate >50 entities or >100 timepoints"
        echo "      in a single call. Consider using smaller scales or batching."
        echo "Expected time: 10-30 minutes"
        echo "Expected cost: ~$5-20"
        echo "Expected examples: 200-400"
    else
        echo "❌ Scale: TOO LARGE"
        echo "ERROR: $ENTITIES entities × $TIMEPOINTS timepoints exceeds LLM capabilities"
        echo ""
        echo "The orchestrator attempts to generate all entities and timepoints in"
        echo "a single LLM call. Even Llama 405B cannot reliably generate more than:"
        echo "  • 30-40 entities"
        echo "  • 50-100 timepoints"
        echo "  • ~10K tokens of structured JSON"
        echo ""
        echo "Recommended scales for MAX mode:"
        echo "  • Small test: 5-10 entities, 10-20 timepoints"
        echo "  • Medium: 20-30 entities, 30-50 timepoints"
        echo "  • Large: 30-40 entities, 50-100 timepoints (risky)"
        echo ""
        echo "For larger scales, use standard mode which generates multiple"
        echo "smaller scenarios instead of one massive scenario."
        echo ""
        exit 1
    fi
else
    echo "STANDARD MODE - Multi-Modal Workflow"
    echo "  • Phase 1: Generate 15 deep cases (3 × 5 modes)"
    echo "  • Phase 2: Generate 20 breadth scenarios"
    echo "  • Phase 3: Generate 100 variations"
    echo "  • Phase 4: Upload to Oxen.ai"
    echo ""
    echo "Expected time: 1-2 hours"
    echo "Expected cost: ~$50-100"
    echo "Expected examples: 6,100+"
fi

echo ""
echo "=================================================="
echo ""

# Clean up old database to avoid UNIQUE constraint errors
if [ -f character_engine.db ]; then
    echo "🗑️  Removing old database file..."
    rm -f character_engine.db
fi

# Run the character engine with appropriate flags
echo "⚙️  Verifying failsoft mode is disabled (mocks are illegal)..."
python3 -c "
from hydra import initialize, compose
from llm_service.config import LLMServiceConfig
with initialize(version_base=None, config_path='conf'):
    cfg = compose(config_name='config')
    config = LLMServiceConfig.from_hydra_config(cfg)
    assert config.error_handling.failsoft_enabled == False, 'ERROR: Failsoft is enabled! Mocks will be created.'
    print('✅ Confirmed: failsoft_enabled=False (no mocks)')
"

echo ""
echo "🎯 Running character engine..."
echo ""

# Capture exit code
EXIT_CODE=0
if [[ "$MODE" == "max" ]]; then
    python run_character_engine.py --max "$@" || EXIT_CODE=$?
else
    python run_character_engine.py || EXIT_CODE=$?
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Character Engine Complete!"
    echo ""

    # Show output location
    if [[ "$MODE" == "max" ]]; then
        OUTPUT_DIR="output/character_engine/max_mode"
        if [ -d "$OUTPUT_DIR" ]; then
            echo "📁 Output files:"
            ls -lh "$OUTPUT_DIR"/*.jsonl 2>/dev/null || echo "   (no .jsonl files found)"
        fi
    else
        OUTPUT_DIR="output/character_engine"
        if [ -d "$OUTPUT_DIR" ]; then
            echo "📁 Output directory: $OUTPUT_DIR"
            echo "   Files: $(ls -1 "$OUTPUT_DIR" 2>/dev/null | wc -l | xargs)"
        fi
    fi
else
    echo "❌ Character Engine failed with exit code: $EXIT_CODE"
    echo ""
    echo "Common issues:"
    echo "  • Timeout: OpenRouter API may be slow, try smaller scale"
    echo "  • Parsing errors: Check logs/llm_calls/*.jsonl for LLM responses"
    echo "  • Validation errors: Ensure all required fields are populated"
    echo ""
    exit $EXIT_CODE
fi

echo ""
