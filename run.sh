#!/bin/bash
#
# run.sh - Unified E2E Test Runner for Timepoint Daedalus
#
# Runs templates from the generation/templates/ catalog using the new template system.
# Supports tier-based, category-based, and mechanism-based template selection.
#
# Usage:
#   ./run.sh [OPTIONS] [MODE]
#
# Examples:
#   ./run.sh quick                    # Quick tier templates (~2-3 min each)
#   ./run.sh --category core          # All core mechanism tests
#   ./run.sh --mechanism M1,M2        # Templates testing M1 and M2
#   ./run.sh --template board_meeting # Single template by name
#   ./run.sh --list                   # Show all available templates
#

set -e  # Exit on error

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default settings
MONITOR=false
ENABLE_CHAT=false
AUTO_CONFIRM=true
MONITOR_INTERVAL=300  # 5 minutes
LLM_MODEL="meta-llama/llama-3.1-70b-instruct"
MAX_OUTPUT_TOKENS=300
MONITOR_MODE="both"  # "both" | "snapshot" | "compare"
OPEN_DASHBOARD=false

# Template selection (new system)
TEMPLATE_NAME=""
TIER=""
CATEGORY=""
MECHANISM=""
PARALLEL=""
SKIP_SUMMARIES=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

show_help() {
    cat << EOF
Unified E2E Test Runner for Timepoint Daedalus

USAGE:
    ./run.sh [OPTIONS] [MODE]

TEMPLATE SELECTION OPTIONS:
    --template NAME        Run a single template by name
    --tier TIER            Run templates by tier: quick, standard, comprehensive, stress
    --category CAT         Run templates by category: core, showcase, portal, stress, convergence
    --mechanism M1,M2,...  Run templates testing specific mechanisms
    --list                 Show all available templates with metadata
    --parallel N           Run N templates in parallel (default: sequential)
    --skip-summaries       Skip LLM summary generation (faster, cheaper)

MONITORING OPTIONS:
    --monitor              Enable real-time monitoring with LLM analysis
    --chat                 Enable interactive chat in monitor (requires --monitor)
    --no-auto-confirm      Disable auto-confirmation in monitor
    --interval SECONDS     Monitor check interval (default: 300)
    --llm-model MODEL      LLM model for monitor (default: meta-llama/llama-3.1-70b-instruct)
    --monitor-mode MODE    Monitor mode: both|snapshot|compare (default: both)

OTHER OPTIONS:
    --open-dashboard       Print dashboard URL after successful run
    -h, --help             Show this help message

SHORTCUT MODES:
    quick                  All quick-tier templates (fast development testing)
    standard               All standard-tier templates
    comprehensive          All comprehensive-tier templates
    stress                 All stress-tier templates
    core                   All core mechanism tests
    showcase               All showcase templates
    portal                 All portal templates
    all                    All templates (warning: expensive!)

TEMPLATE CATEGORIES (40 total):
    core (18)              Mechanism isolation tests (M1-M18)
    showcase (10)          Production-ready scenarios
    portal (4)             Backward reasoning scenarios
    stress (5)             High-complexity stress tests
    convergence (3)        Convergence evaluation tests

TEMPLATE TIERS:
    quick                  Fast tests (~2-3 min, <\$1 each)
    standard               Moderate tests (~5-10 min, \$1-3 each)
    comprehensive          Thorough tests (~15-30 min, \$5-10 each)
    stress                 Complex tests (~30-60 min, \$10-20 each)

EXAMPLES:

    Template Selection:
    ------------------
    ./run.sh --list                           # List all 40 templates
    ./run.sh --template board_meeting         # Single template
    ./run.sh --tier quick                     # All quick templates (~10 templates)
    ./run.sh --category core                  # All 18 core mechanism tests
    ./run.sh --mechanism M1,M2,M3             # Templates testing M1, M2, or M3
    ./run.sh --category showcase --tier quick # Quick showcase templates

    Parallel Execution:
    ------------------
    ./run.sh --tier quick --parallel 4        # 4 templates in parallel
    ./run.sh --category core --parallel 6     # Core tests, 6 parallel

    Fast Development:
    ----------------
    ./run.sh quick                            # Quick tier (shortcut)
    ./run.sh --tier quick --skip-summaries    # Even faster, no LLM summaries

    Monitoring:
    ----------
    ./run.sh --monitor quick                  # Real-time LLM analysis
    ./run.sh --monitor --chat quick           # Interactive chat during run

    Single Template Deep Dive:
    -------------------------
    ./run.sh --template constitutional_convention   # Run single template
    ./run.sh --monitor --chat --template board_meeting  # With monitoring

NOTES:
    - All modes use M1+M17 Adaptive Fidelity-Temporal Strategy
    - Templates live in generation/templates/ organized by category
    - See generation/templates/catalog.json for full template metadata
    - Use 'python3.10 run_all_mechanism_tests.py --list-templates' for detailed info

EOF
}

show_templates() {
    print_header "Available Templates"
    python3.10 run_all_mechanism_tests.py --list-templates
}

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

MODE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --monitor)
            MONITOR=true
            shift
            ;;
        --chat)
            ENABLE_CHAT=true
            shift
            ;;
        --no-auto-confirm)
            AUTO_CONFIRM=false
            shift
            ;;
        --interval)
            MONITOR_INTERVAL="$2"
            shift 2
            ;;
        --llm-model)
            LLM_MODEL="$2"
            shift 2
            ;;
        --monitor-mode)
            MONITOR_MODE="$2"
            shift 2
            ;;
        --template)
            TEMPLATE_NAME="$2"
            shift 2
            ;;
        --tier)
            TIER="$2"
            shift 2
            ;;
        --category)
            CATEGORY="$2"
            shift 2
            ;;
        --mechanism)
            MECHANISM="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL="$2"
            shift 2
            ;;
        --skip-summaries)
            SKIP_SUMMARIES=true
            shift
            ;;
        --open-dashboard)
            OPEN_DASHBOARD=true
            shift
            ;;
        --list)
            show_templates
            exit 0
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            if [[ -z "$MODE" ]]; then
                MODE="$1"
            else
                print_error "Unknown option: $1"
                echo ""
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# ============================================================================
# MODE MAPPING (shortcut modes to flags)
# ============================================================================

# Build test flags from explicit options or mode shortcuts
TEST_FLAGS=""

# Handle explicit options first
if [[ -n "$TEMPLATE_NAME" ]]; then
    TEST_FLAGS="$TEST_FLAGS --template $TEMPLATE_NAME"
fi

if [[ -n "$TIER" ]]; then
    TEST_FLAGS="$TEST_FLAGS --tier $TIER"
fi

if [[ -n "$CATEGORY" ]]; then
    TEST_FLAGS="$TEST_FLAGS --category $CATEGORY"
fi

if [[ -n "$MECHANISM" ]]; then
    TEST_FLAGS="$TEST_FLAGS --mechanism $MECHANISM"
fi

if [[ -n "$PARALLEL" ]]; then
    TEST_FLAGS="$TEST_FLAGS --parallel $PARALLEL"
fi

if [[ "$SKIP_SUMMARIES" == "true" ]]; then
    TEST_FLAGS="$TEST_FLAGS --skip-summaries"
fi

# Handle shortcut modes if no explicit flags were set
if [[ -z "$TEST_FLAGS" && -n "$MODE" ]]; then
    case "$MODE" in
        quick)
            TEST_FLAGS="--tier quick"
            ;;
        standard)
            TEST_FLAGS="--tier standard"
            ;;
        comprehensive)
            TEST_FLAGS="--tier comprehensive"
            ;;
        stress)
            TEST_FLAGS="--tier stress"
            ;;
        core)
            TEST_FLAGS="--category core"
            ;;
        showcase)
            TEST_FLAGS="--category showcase"
            ;;
        portal)
            TEST_FLAGS="--category portal"
            ;;
        convergence)
            TEST_FLAGS="--category convergence"
            ;;
        all)
            TEST_FLAGS=""  # No filter = all templates
            ;;
        *)
            print_error "Unknown mode: $MODE"
            echo ""
            print_info "Run './run.sh --list' to see all available templates"
            print_info "Run './run.sh --help' for usage information"
            exit 1
            ;;
    esac
fi

# Check if any selection was made
if [[ -z "$TEST_FLAGS" && -z "$MODE" ]]; then
    print_error "No mode or template selection specified"
    echo ""
    show_help
    exit 1
fi

# ============================================================================
# ENVIRONMENT CHECK
# ============================================================================

print_header "Timepoint Daedalus E2E Test Runner"

# Check for .env file
if [[ ! -f .env ]]; then
    print_warning "No .env file found"
    print_info "Create .env with OPENROUTER_API_KEY and OXEN_API_KEY"
    exit 1
fi

# Source environment
print_info "Loading environment variables..."
source .env

# Export auto-confirm environment variable for subprocess
export TIMEPOINT_AUTO_CONFIRM

# Verify API keys
if [[ -z "$OPENROUTER_API_KEY" ]]; then
    print_error "OPENROUTER_API_KEY not set in .env"
    exit 1
fi

print_success "Environment loaded"

# ============================================================================
# EXECUTION
# ============================================================================

print_header "Configuration"
echo "Selection: ${MODE:-custom}"
echo "Test Flags: $TEST_FLAGS"
echo "Monitoring: $MONITOR"
if [[ "$MONITOR" == "true" ]]; then
    echo "  - Chat Enabled: $ENABLE_CHAT"
    echo "  - Auto Confirm: $AUTO_CONFIRM"
    echo "  - Check Interval: ${MONITOR_INTERVAL}s"
    echo "  - LLM Model: $LLM_MODEL"
    echo "  - Monitor Mode: $MONITOR_MODE"
fi
echo ""

# Build command
if [[ "$MONITOR" == "true" ]]; then
    # Monitored execution
    print_header "Starting Monitored Execution"

    MONITOR_CMD="python3.10 -m monitoring.monitor_runner"
    MONITOR_CMD="$MONITOR_CMD --mode $MONITOR_MODE"
    MONITOR_CMD="$MONITOR_CMD --interval $MONITOR_INTERVAL"
    MONITOR_CMD="$MONITOR_CMD --llm-model $LLM_MODEL"
    MONITOR_CMD="$MONITOR_CMD --max-output-tokens $MAX_OUTPUT_TOKENS"

    if [[ "$ENABLE_CHAT" == "true" ]]; then
        MONITOR_CMD="$MONITOR_CMD --enable-chat"
    fi

    if [[ "$AUTO_CONFIRM" == "true" ]]; then
        MONITOR_CMD="$MONITOR_CMD --auto-confirm"
    fi

    MONITOR_CMD="$MONITOR_CMD -- python3.10 run_all_mechanism_tests.py $TEST_FLAGS"

    print_info "Command: $MONITOR_CMD"
    echo ""

    eval "$MONITOR_CMD"

else
    # Unmonitored execution
    print_header "Starting Execution"

    CMD="python3.10 run_all_mechanism_tests.py $TEST_FLAGS"

    print_info "Command: $CMD"
    echo ""

    eval "$CMD"
fi

# ============================================================================
# COMPLETION
# ============================================================================

print_header "Execution Complete"
print_success "Test run finished successfully"
echo ""
print_info "Check metadata/runs.db for detailed results"
print_info "Check datasets/ for generated narrative exports"
