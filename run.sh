#!/bin/bash
#
# run.sh - Unified E2E Test Runner for Timepoint Daedalus
#
# Consolidates all test execution patterns with M1+M17 integration support.
# Supports monitored/unmonitored modes, template selection, and flexible configuration.
#
# Usage:
#   ./run.sh [OPTIONS] [MODE]
#
# Examples:
#   ./run.sh quick                    # Quick tests, no monitoring
#   ./run.sh --monitor portal-test    # Portal tests with monitoring
#   ./run.sh --monitor --chat ultra   # Ultra mode with chat-enabled monitoring
#   ./run.sh --list                   # Show all available modes
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
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

show_help() {
    cat << EOF
Unified E2E Test Runner for Timepoint Daedalus

USAGE:
    ./run.sh [OPTIONS] [MODE]

OPTIONS:
    --monitor              Enable real-time monitoring with LLM analysis
    --chat                 Enable interactive chat in monitor (requires --monitor)
    --no-auto-confirm      Disable auto-confirmation in monitor
    --interval SECONDS     Monitor check interval (default: 300)
    --llm-model MODEL      LLM model for monitor (default: meta-llama/llama-3.1-70b-instruct)
    --monitor-mode MODE    Monitor mode: both|snapshot|compare (default: both)
    --list                 Show all available modes
    -h, --help             Show this help message

MODES:
    quick                  Quick tests (9 templates, ~\$9-18, 18-27 min)
    full                   All quick + expensive tests (13 templates)

    # Timepoint Corporate
    timepoint-forward      Forward-mode corporate (15 templates, \$15-30, 30-60 min)
    timepoint-all          ALL corporate templates (35 templates, \$81-162, 156-243 min)

    # Portal (Backward Reasoning)
    portal-test            Standard portal (4 templates, \$5-10, 10-15 min)
    portal-simjudged-quick Quick simulation judging (4 templates, \$10-20, 20-30 min)
    portal-simjudged       Standard simulation judging (4 templates, \$15-30, 30-45 min)
    portal-simjudged-thorough  Thorough judging (4 templates, \$25-50, 45-60 min)
    portal-all             ALL portal variants (16 templates, \$55-110, 105-150 min)

    # Portal Timepoint (Real Founders)
    portal-timepoint       Standard with founders (5 templates, \$6-12, 12-18 min)
    portal-timepoint-simjudged-quick  Quick judging (5 templates, \$12-24, 24-36 min)
    portal-timepoint-simjudged  Standard judging (5 templates, \$18-36, 36-54 min)
    portal-timepoint-simjudged-thorough  Thorough judging (5 templates, \$30-60, 54-75 min)
    portal-timepoint-all   ALL portal timepoint (20 templates, \$66-132, 126-183 min)

    # Ultra Mode
    ultra                  Run EVERYTHING (64 templates, \$176-352, 301-468 min)

EXAMPLES:

    Basic Usage:
    ------------
    ./run.sh quick                    # Quick tests, no monitoring (9 templates, ~18-27 min)
    ./run.sh full                     # All quick + expensive tests (13 templates)
    ./run.sh ultra                    # Everything! (64 templates, 5-8 hours)

    Timepoint Corporate:
    -------------------
    ./run.sh timepoint-forward        # Corporate formation/growth (15 templates)
    ./run.sh timepoint-all            # All corporate modes (35 templates)

    Portal (Backward Reasoning):
    ---------------------------
    ./run.sh portal-test              # Standard portal (4 templates, ~10-15 min)
    ./run.sh portal-simjudged         # Portal + judging (4 templates, ~30-45 min)
    ./run.sh portal-all               # All portal variants (16 templates)

    Portal + Timepoint (Real Founders):
    -----------------------------------
    ./run.sh portal-timepoint                    # Standard (5 templates, ~12-18 min)
    ./run.sh portal-timepoint-simjudged          # + judging (5 templates, ~36-54 min)
    ./run.sh portal-timepoint-simjudged-thorough # + thorough (5 templates, ~54-75 min)
    ./run.sh portal-timepoint-all                # All variants (20 templates)

    Monitoring:
    ----------
    ./run.sh --monitor quick                     # Real-time LLM analysis
    ./run.sh --monitor portal-test               # Monitor portal mode
    ./run.sh --monitor timepoint-forward         # Monitor corporate mode
    ./run.sh --monitor portal-timepoint          # Monitor real founders

    Interactive Chat:
    ----------------
    ./run.sh --monitor --chat quick              # Quick tests with chat
    ./run.sh --monitor --chat portal-timepoint   # Portal + chat
    ./run.sh --monitor --chat ultra              # Ultra mode with chat

    Custom Monitor Settings:
    -----------------------
    ./run.sh --monitor --interval 60 quick                    # Check every 60s
    ./run.sh --monitor --interval 600 timepoint-forward       # Check every 10 min
    ./run.sh --monitor --llm-model meta-llama/llama-3.1-405b-instruct portal-test          # Use Llama 405B for monitoring
    ./run.sh --monitor --monitor-mode snapshot quick          # Snapshot only (no comparison)
    ./run.sh --monitor --no-auto-confirm portal-timepoint     # Manual approval each check

    Advanced Combinations:
    ---------------------
    # Portal timepoint with Llama 405B monitoring, chat, and high frequency
    ./run.sh --monitor --chat --interval 120 --llm-model meta-llama/llama-3.1-405b-instruct portal-timepoint

    # Corporate mode with snapshot-only monitoring
    ./run.sh --monitor --monitor-mode snapshot --interval 300 timepoint-forward

    # ALL corporate portal modes with ultra monitoring and chat (COMPREHENSIVE)
    ./run.sh --monitor --chat --interval 180 portal-timepoint-all

    # Ultra mode with custom LLM and manual confirmation
    ./run.sh --monitor --chat --llm-model meta-llama/llama-3.1-405b-instruct \\
             --no-auto-confirm --interval 600 ultra

    # Timepoint corporate ultra: ALL templates with premium monitoring
    ./run.sh --monitor --chat --llm-model meta-llama/llama-3.1-405b-instruct \\
             --interval 300 --monitor-mode both timepoint-all

    Quick Reference by Use Case:
    ---------------------------
    Fast development testing:     ./run.sh quick
    Corporate template testing:   ./run.sh timepoint-forward
    Portal template testing:      ./run.sh portal-test
    Real founder simulations:     ./run.sh portal-timepoint
    Interactive debugging:        ./run.sh --monitor --chat quick
    Production validation:        ./run.sh --monitor ultra
    CI/CD quick smoke test:       ./run.sh quick
    Full system validation:       ./run.sh ultra
    Corporate portal deep dive:   ./run.sh --monitor --chat portal-timepoint-all
    Premium corporate analysis:   ./run.sh --monitor --chat --llm-model meta-llama/llama-3.1-405b-instruct timepoint-all

    Cost-Conscious Options:
    ----------------------
    Under $20:   ./run.sh quick, portal-test, portal-timepoint
    Under $50:   ./run.sh timepoint-forward, portal-all
    Under $100:  ./run.sh timepoint-all, portal-timepoint-all
    Full suite:  ./run.sh ultra ($176-352)

NOTES:
    - All modes use M1+M17 Adaptive Fidelity-Temporal Strategy
    - Monitoring provides real-time LLM analysis of simulation progress
    - Chat mode allows interactive querying during execution
    - Monitor overhead: ~5-10% runtime, ~$0.50-$10 LLM cost depending on mode
    - See run_all_mechanism_tests.py --modes for detailed mode info

EOF
}

show_modes() {
    print_header "Available Test Modes"
    python3.10 run_all_mechanism_tests.py --modes
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
        --list)
            show_modes
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

# Check if mode was provided
if [[ -z "$MODE" ]]; then
    print_error "No mode specified"
    echo ""
    show_help
    exit 1
fi

# ============================================================================
# MODE MAPPING
# ============================================================================

# Map short mode names to run_all_mechanism_tests.py flags
case "$MODE" in
    quick)
        TEST_FLAGS=""
        ;;
    full)
        TEST_FLAGS="--run-all"
        ;;
    timepoint-forward)
        TEST_FLAGS="--timepoint-forward"
        ;;
    timepoint-all)
        TEST_FLAGS="--timepoint-all"
        ;;
    portal-test)
        TEST_FLAGS="--portal-test-only"
        ;;
    portal-simjudged-quick)
        TEST_FLAGS="--portal-simjudged-quick-only"
        ;;
    portal-simjudged)
        TEST_FLAGS="--portal-simjudged-only"
        ;;
    portal-simjudged-thorough)
        TEST_FLAGS="--portal-simjudged-thorough-only"
        ;;
    portal-all)
        TEST_FLAGS="--portal-all"
        ;;
    portal-timepoint)
        TEST_FLAGS="--portal-timepoint-only"
        ;;
    portal-timepoint-simjudged-quick)
        TEST_FLAGS="--portal-timepoint-simjudged-quick-only"
        ;;
    portal-timepoint-simjudged)
        TEST_FLAGS="--portal-timepoint-simjudged-only"
        ;;
    portal-timepoint-simjudged-thorough)
        TEST_FLAGS="--portal-timepoint-simjudged-thorough-only"
        ;;
    portal-timepoint-all)
        TEST_FLAGS="--portal-timepoint-all"
        ;;
    ultra)
        TEST_FLAGS="--ultra-all"
        ;;
    *)
        print_error "Unknown mode: $MODE"
        echo ""
        print_info "Run './run.sh --list' to see all available modes"
        exit 1
        ;;
esac

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
echo "Mode: $MODE"
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
    print_header "Starting Unmonitored Execution"

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
