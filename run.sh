#!/bin/bash
#
# run.sh - Timepoint Daedalus Command Center
#
# The single entry point for all simulation operations.
# Supports running simulations, viewing results, managing data, and API operations.
#
# Quick Start:
#   ./run.sh quick                    # Run quick-tier templates
#   ./run.sh run board_meeting        # Run single template
#   ./run.sh list                     # List all templates
#   ./run.sh status                   # Show recent runs
#   ./run.sh --help                   # Full help
#

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Defaults
PYTHON="python3.10"
DB_PATH="metadata/runs.db"
TENSOR_DB_PATH="metadata/tensors.db"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo -e "\n${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}$(printf '=%.0s' {1..60})${NC}"
}

print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_info() { echo -e "${CYAN}[INFO]${NC} $1"; }

check_env() {
    if [[ ! -f .env ]]; then
        print_error "No .env file found"
        print_info "Create .env with OPENROUTER_API_KEY and OXEN_API_KEY"
        exit 1
    fi
    source .env
}

# ============================================================================
# HELP
# ============================================================================

show_main_help() {
    cat << 'EOF'
Timepoint Daedalus Command Center

USAGE:
    ./run.sh <command> [options]
    ./run.sh <shortcut>              (quick, standard, core, etc.)
    ./run.sh <template>              (board_meeting, startup_unicorn, etc.)

COMMANDS:
    run         Execute simulations
    list        List templates, runs, or stats
    status      Show run status and results
    export      Export run data
    clean       Cleanup old data
    api         API server operations
    e2e         Full E2E testing modes
    convergence Convergence analysis
    test        Run pytest test suites
    dashboard   Start/stop API backend
    doctor      Check environment setup
    info        Show system information

PRESETS (run by tier or category):
    ./run.sh quick                   Quick-tier templates (~$0.02-0.05 each)
    ./run.sh standard                Standard-tier templates (~$0.05-0.20)
    ./run.sh comprehensive           Comprehensive templates (~$0.20-1.00)
    ./run.sh core                    All 19 mechanism tests (M1-M19)
    ./run.sh showcase                10 production-ready scenarios
    ./run.sh portal                  4 backward reasoning scenarios

DIRECT TEMPLATES (41 total):
    ./run.sh board_meeting           Showcase: Board meeting simulation
    ./run.sh startup_unicorn         Portal: $1B valuation backward reasoning
    ./run.sh m07_causal_chains       Core: Causal chain mechanism test
    ./run.sh convergence_simple      Test: Convergence evaluation

E2E TESTING:
    ./run.sh e2e full                All templates (expensive!)
    ./run.sh e2e portal-all          All portal testing modes
    ./run.sh e2e convergence-e2e board_meeting  Run 3x + analyze

FREE MODELS ($0 cost):
    ./run.sh run --free board_meeting
    ./run.sh run --free-fast quick

GEMINI 3 FLASH (1M context, fast inference):
    ./run.sh run --gemini-flash board_meeting

GROQ ULTRA-FAST INFERENCE (~5x faster):
    ./run.sh run --groq board_meeting       # Llama 3.3 70B (~300 tok/s)
    ./run.sh run --fast board_meeting       # Llama 8B Instant (~750 tok/s)

QUICK EXAMPLES:
    ./run.sh board_meeting           Run single template
    ./run.sh run --tier quick        Run by tier
    ./run.sh list                    List all templates
    ./run.sh status                  Show recent runs
    ./run.sh convergence history     Show convergence results
    ./run.sh test synth              Run SynthasAIzer tests
    ./run.sh dashboard               Start API backend
    ./run.sh doctor                  Check environment
    ./run.sh info                    Show system info

Run './run.sh <command> --help' for command-specific help.
Run './run.sh help' for full documentation with all 41 templates.
EOF
}

show_full_help() {
    cat << 'EOF'
================================================================================
TIMEPOINT DAEDALUS - FULL DOCUMENTATION
================================================================================

COMMANDS
--------

RUN - Execute Simulations
    ./run.sh run [TEMPLATE|PRESET] [OPTIONS]
    ./run.sh <template_name>         (direct shortcut)

    Presets (shortcut: ./run.sh <preset>):
        quick           All quick-tier templates (~2-3 min each)
        standard        All standard-tier templates (~5-10 min each)
        comprehensive   All comprehensive-tier templates (~15-30 min)
        stress          All stress-tier templates (~30-60 min)
        core            All 19 core mechanism tests
        showcase        Production-ready scenarios
        portal          Backward reasoning scenarios
        convergence     Convergence evaluation tests
        all             ALL templates (warning: expensive!)

    Selection Options:
        TEMPLATE              Single template (e.g., board_meeting)
        --tier TIER           Filter by tier
        --category CAT        Filter by category
        --mechanism M1,M2     Filter by mechanisms

    Execution Options:
        --parallel N          Run N templates concurrently (default: 1)
        --dry-run             Show cost estimate without running
        --skip-summaries      Skip LLM summary generation (faster)
        --budget USD          Stop if cost exceeds budget

    Free Model Options ($0 cost):
        --free                Use best quality free model
        --free-fast           Use fastest free model
        --list-free-models    List available free models

    Model Override:
        --model MODEL         Override LLM (e.g., deepseek/deepseek-chat)

    Portal Testing Modes:
        --portal-all                    All portal modes
        --portal-test-only              Basic portal test
        --portal-simjudged-quick        Quick simjudged portal
        --portal-simjudged              Standard simjudged
        --portal-simjudged-thorough     Thorough simjudged
        --portal-timepoint-only         Portal timepoint test
        --portal-timepoint-all          All portal timepoint modes

    Timepoint Testing Modes:
        --timepoint-forward             Forward temporal generation
        --timepoint-all                 All timepoint modes

    Convergence Options:
        --convergence                   Run analysis after
        --convergence-runs N            Number of runs
        --convergence-e2e               Run N times + analyze

    Natural Language:
        --nl "PROMPT"                   Generate from prompt
        --nl-entities N                 Entity count (default: 4)
        --nl-timepoints N               Timepoint count (default: 3)

    API Mode Options:
        --api                 Submit via REST API
        --api-url URL         API base URL
        --api-key KEY         API key
        --api-batch-size N    Jobs per batch
        --api-budget USD      API budget cap
        --api-wait            Wait for completion

E2E - Full E2E Testing
    ./run.sh e2e <MODE> [OPTIONS]

    Modes:
        full              All templates (expensive!)
        ultra-all         Maximum coverage
        portal-all        All portal modes
        timepoint-all     All timepoint modes
        convergence-e2e   Run template N times + analyze

    Options:
        --runs N          Runs for convergence (default: 3)
        --model MODEL     Override model
        --parallel N      Concurrent tests
        --verbose         Detailed output

CONVERGENCE - Convergence Analysis
    ./run.sh convergence <ACTION> [OPTIONS]

    Actions:
        analyze           Analyze recent runs (default)
        e2e               Run N times + analyze
        history           Show result history

    Options:
        --runs N          Runs to analyze (default: 3)
        --template TPL    Filter by template
        --verbose         Show divergence details

TEST - Run Pytest Test Suites
    ./run.sh test [SUITE] [OPTIONS]

    Suites:
        unit              Unit tests (fast, isolated)
        integration       Integration tests
        e2e               End-to-end tests
        mechanisms        All mechanism tests (M1-M19)
        synth             SynthasAIzer tests (53 tests)

    Shortcuts:
        m1, m2, ... m19   Run specific mechanism tests

    Options:
        --coverage        Generate coverage report
        --parallel N      Run N tests in parallel
        --verbose         Verbose output

DASHBOARD - API Backend Server
    ./run.sh dashboard [ACTION]

    Actions:
        start             Start API backend (default)
        stop              Stop API backend

DOCTOR - Environment Check
    ./run.sh doctor

    Validates:
        - Python 3.10+ installation
        - .env file and API keys
        - Database paths
        - Key dependencies (pytest, synth, TemplateLoader)

INFO - System Information
    ./run.sh info

    Shows:
        - Version info
        - Template count
        - Test file count
        - Database statistics

LIST - Show Information
    ./run.sh list [WHAT] [OPTIONS]

    What to list:
        templates       All templates with metadata (default)
        runs            Recent simulation runs
        usage           API usage statistics
        mechanisms      All 19 mechanisms
        patches         Template patches by category (SYNTH.md)

    Options:
        --limit N       Limit results (default: 20)
        --tier TIER     Filter templates by tier
        --category CAT  Filter templates by category
        --patches [CAT] List patches (optionally by category)
        --json          Output as JSON

STATUS - Show Run Status
    ./run.sh status [RUN_ID] [OPTIONS]

EXPORT - Export Run Data
    ./run.sh export <RUN_ID|last> [OPTIONS]

CLEAN - Cleanup Data
    ./run.sh clean <WHAT> [OPTIONS]

API - API Server Operations
    ./run.sh api <ACTION> [OPTIONS]

================================================================================
ALL 41 TEMPLATES
================================================================================

CORE - Mechanism Isolation Tests (19)
-------------------------------------
  m01_heterogeneous_fidelity    M1: Different resolution levels in same scene
  m02_progressive_training      M2: Entity quality improves through queries
  m03_exposure_events           M3: Knowledge propagates with provenance
  m04_physics_validation        M4: Info conservation, energy budget, inertia
  m05_lazy_resolution           M5: Query-driven resolution elevation
  m06_tensor_compression        M6: TTM tensor compression/reconstruction
  m07_causal_chains             M7: Temporal ordering, causal parent validation
  m08_embodied_states           M8: Physical state affects cognition
  m09_on_demand_entities        M9: Missing entities auto-generated
  m10_scene_atmosphere          M10: Environment influences behavior
  m11_dialog_synthesis          M11: Multi-turn contextual conversation
  m12_counterfactual            M12: Timeline branches at decision points
  m13_relationships             M13: Trust/tension evolves over time
  m14_circadian                 M14: Time-of-day affects behavior
  m15_prospection               M15: Entity models future states
  m16_animistic                 M16: Non-human entities have agency
  m17_modal_causality           M17: PORTAL backward reasoning
  m18_model_selection           M18: Action-appropriate LLM selection
  m19_knowledge_extraction      M19: Semantic knowledge extraction from dialog

SHOWCASE - Production Scenarios (10)
------------------------------------
  board_meeting                 Tech startup board meeting (M1,M7,M11,M13)
  jefferson_dinner              1790 Compromise Dinner (M3,M7,M11,M13)
  hospital_crisis               ER night shift (M8,M14)
  detective_prospection         Holmes models Moriarty (M15,M7)
  kami_shrine                   Japanese shrine ritual (M16)
  vc_pitch_pearl                Pre-seed pitch - pearl causality
  vc_pitch_branching            Pre-seed pitch - counterfactual
  vc_pitch_roadshow             Multi-meeting VC roadshow
  vc_pitch_strategies           Multiple negotiation strategies
  hound_shadow_directorial      Detective on foggy moors - directorial

PORTAL - Backward Reasoning (4)
-------------------------------
  startup_unicorn               PORTAL: $1B valuation → founding
  presidential_election         PORTAL: Election victory → candidacy
  academic_tenure               PORTAL: Tenure → PhD start
  startup_failure               PORTAL: Shutdown → founding

STRESS - High Complexity (6)
----------------------------
  constitutional_convention_day1  28 entities, 500 timepoints ($500-1000)
  scarlet_study_deep              101 timepoints, all 19 mechanisms ($50-100)
  empty_house_flashback           81 timepoints directorial ($30-50)
  final_problem_branching         61 timepoints, 4 branches ($25-40)
  sign_loops_cyclical             Cyclical temporal patterns ($20-35)
  tensor_resolution_hybrid        Tests all tensor resolution paths

CONVERGENCE - Consistency Testing (3)
-------------------------------------
  convergence_simple              Ultra-lightweight (~$0.02)
  convergence_standard            Moderate complexity (~$0.05)
  convergence_comprehensive       Rich causal structure (~$0.10)

================================================================================
TEMPLATE TIERS
================================================================================
  quick          Fast tests (~30s-2min, <$0.05 each)
  standard       Moderate tests (~2-5 min, $0.05-0.20)
  comprehensive  Thorough tests (~5-15 min, $0.20-1.00)
  stress         Complex tests (~15-60+ min, $20-1000)

================================================================================
EXAMPLES
================================================================================

# Direct template execution
./run.sh board_meeting                    # Showcase template
./run.sh startup_unicorn                  # Portal template
./run.sh m07_causal_chains                # Core mechanism test

# By tier/category
./run.sh quick                            # All quick-tier
./run.sh run --tier quick --parallel 4    # Quick with parallelism
./run.sh run --category core              # All 19 mechanism tests

# Free models ($0 cost)
./run.sh run --free board_meeting         # Best free model
./run.sh run --free-fast quick            # Fastest free model

# Gemini 3 Flash (1M context, fast inference)
./run.sh run --gemini-flash board_meeting # Ultra-fast with huge context

# Model override
./run.sh run --model deepseek/deepseek-chat board_meeting

# Portal testing
./run.sh run --portal-all                 # All portal modes
./run.sh run --portal-simjudged-thorough  # Thorough portal

# Convergence testing
./run.sh convergence e2e board_meeting    # Run 3x + analyze
./run.sh convergence e2e --runs 5 convergence_simple
./run.sh convergence history              # Show results

# E2E testing
./run.sh e2e full                         # All templates
./run.sh e2e portal-all                   # All portal modes
./run.sh e2e convergence-e2e --runs 3 --template board_meeting

# Natural language
./run.sh run --nl "Simulate a startup board meeting about pivoting"

# API mode
./run.sh api start                        # Start server
./run.sh run --api board_meeting          # Submit via API
./run.sh api usage                        # Check quotas

# Testing
./run.sh test                             # All pytest tests
./run.sh test synth                       # SynthasAIzer tests (53 tests)
./run.sh test mechanisms                  # All M1-M19 mechanism tests
./run.sh test m7                          # M7 causal chain tests
./run.sh test unit --parallel 4           # Parallel unit tests
./run.sh test --coverage                  # With coverage report

# Dashboard
./run.sh dashboard                        # Start API backend
./run.sh dashboard stop                   # Stop API backend

# Utilities
./run.sh doctor                           # Check environment
./run.sh info                             # Show system info

================================================================================
ENVIRONMENT
================================================================================
Required in .env:
    OPENROUTER_API_KEY    For LLM API access
    OXEN_API_KEY          For dataset uploads

Optional:
    TIMEPOINT_API_KEY     For API mode
    TIMEPOINT_API_URL     API server URL

================================================================================
EOF
}

# ============================================================================
# COMMAND: RUN
# ============================================================================

cmd_run() {
    local args=()
    local preset=""
    local template=""
    local tier=""
    local category=""
    local mechanism=""
    local parallel=""
    local dry_run=false
    local skip_summaries=false
    local budget=""
    local persist=true
    local db_path=""
    local tensor_db=""
    local monitor=false
    local chat=false
    local interval="300"
    local api_mode=false
    local api_url="http://localhost:8080"
    local api_key=""
    local api_batch_size=""
    local api_budget=""
    local api_wait=false
    local quiet=false
    local verbose=false
    local auto_export=""
    # Portal testing modes
    local portal_test_only=false
    local portal_all=false
    local portal_simjudged_quick=false
    local portal_simjudged=false
    local portal_simjudged_thorough=false
    local portal_timepoint_only=false
    local portal_timepoint_all=false
    local portal_quick_demo=false  # NEW: 5 timepoints quick demo mode
    # Timepoint testing modes
    local timepoint_forward=false
    local timepoint_all=false
    # Free model options
    local free_mode=false
    local free_fast=false
    local list_free=false
    # Model override
    local model_override=""
    # Gemini Flash option
    local gemini_flash=false
    # Groq fast inference option
    local groq_mode=false
    local groq_fast=false
    # Convergence options
    local convergence=false
    local convergence_runs=""
    local convergence_e2e=false
    # Natural language
    local nl_prompt=""
    local nl_entities=""
    local nl_timepoints=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_run_help; exit 0 ;;
            --tier) tier="$2"; shift 2 ;;
            --category) category="$2"; shift 2 ;;
            --mechanism) mechanism="$2"; shift 2 ;;
            --parallel) parallel="$2"; shift 2 ;;
            --dry-run) dry_run=true; shift ;;
            --skip-summaries) skip_summaries=true; shift ;;
            --budget) budget="$2"; shift 2 ;;
            --persist) persist=true; shift ;;
            --no-persist) persist=false; shift ;;
            --db) db_path="$2"; shift 2 ;;
            --tensor-db) tensor_db="$2"; shift 2 ;;
            --monitor) monitor=true; shift ;;
            --chat) chat=true; shift ;;
            --interval) interval="$2"; shift 2 ;;
            --api) api_mode=true; shift ;;
            --api-url) api_url="$2"; shift 2 ;;
            --api-key) api_key="$2"; shift 2 ;;
            --api-batch-size) api_batch_size="$2"; shift 2 ;;
            --api-budget) api_budget="$2"; shift 2 ;;
            --api-wait) api_wait=true; shift ;;
            --quiet) quiet=true; shift ;;
            --verbose) verbose=true; shift ;;
            --export) auto_export="$2"; shift 2 ;;
            # Portal testing modes
            --portal-test-only) portal_test_only=true; shift ;;
            --portal-all) portal_all=true; shift ;;
            --portal-simjudged-quick|--portal-simjudged-quick-only) portal_simjudged_quick=true; shift ;;
            --portal-simjudged|--portal-simjudged-only) portal_simjudged=true; shift ;;
            --portal-simjudged-thorough|--portal-simjudged-thorough-only) portal_simjudged_thorough=true; shift ;;
            --portal-timepoint-only) portal_timepoint_only=true; shift ;;
            --portal-timepoint-all) portal_timepoint_all=true; shift ;;
            --portal-quick|--portal-demo) portal_quick_demo=true; shift ;;
            # Timepoint testing modes
            --timepoint-forward) timepoint_forward=true; shift ;;
            --timepoint-all) timepoint_all=true; shift ;;
            # Free model options
            --free) free_mode=true; shift ;;
            --free-fast) free_fast=true; shift ;;
            --list-free-models) list_free=true; shift ;;
            # Model override
            --model) model_override="$2"; shift 2 ;;
            # Gemini Flash (1M context, fast inference)
            --gemini-flash|--gemini) gemini_flash=true; shift ;;
            # Groq ultra-fast inference
            --groq) groq_mode=true; shift ;;
            --groq-fast|--fast) groq_fast=true; shift ;;
            # Convergence options
            --convergence) convergence=true; shift ;;
            --convergence-runs) convergence_runs="$2"; shift 2 ;;
            --convergence-e2e) convergence_e2e=true; shift ;;
            # Natural language
            --nl) nl_prompt="$2"; shift 2 ;;
            --nl-entities) nl_entities="$2"; shift 2 ;;
            --nl-timepoints) nl_timepoints="$2"; shift 2 ;;
            quick|standard|comprehensive|stress|core|showcase|portal|convergence|all)
                preset="$1"; shift ;;
            -*)
                print_error "Unknown option: $1"
                exit 1 ;;
            *)
                if [[ -z "$template" ]]; then
                    template="$1"
                fi
                shift ;;
        esac
    done

    check_env

    # Handle special modes that exit early
    if [[ "$list_free" == "true" ]]; then
        print_header "Available Free Models"
        $PYTHON run_all_mechanism_tests.py --list-free-models
        exit 0
    fi

    # Build python command arguments
    local py_args=()

    # Natural language mode
    if [[ -n "$nl_prompt" ]]; then
        py_args+=(--nl "$nl_prompt")
        [[ -n "$nl_entities" ]] && py_args+=(--nl-entities "$nl_entities")
        [[ -n "$nl_timepoints" ]] && py_args+=(--nl-timepoints "$nl_timepoints")
        print_header "Natural Language Simulation"
        print_info "Prompt: $nl_prompt"
    # Portal testing modes
    elif [[ "$portal_all" == "true" ]]; then
        py_args+=(--portal-all)
        print_header "Running All Portal Modes"
    elif [[ "$portal_test_only" == "true" ]]; then
        py_args+=(--portal-test-only)
        print_header "Running Portal Test Only"
    elif [[ "$portal_simjudged_quick" == "true" ]]; then
        py_args+=(--portal-simjudged-quick-only)
        print_header "Running Portal SimJudged Quick"
    elif [[ "$portal_simjudged" == "true" ]]; then
        py_args+=(--portal-simjudged-only)
        print_header "Running Portal SimJudged"
    elif [[ "$portal_simjudged_thorough" == "true" ]]; then
        py_args+=(--portal-simjudged-thorough-only)
        print_header "Running Portal SimJudged Thorough"
    elif [[ "$portal_timepoint_only" == "true" ]]; then
        py_args+=(--portal-timepoint-only)
        print_header "Running Portal Timepoint Only"
    elif [[ "$portal_timepoint_all" == "true" ]]; then
        py_args+=(--portal-timepoint-all)
        print_header "Running Portal Timepoint All"
    elif [[ "$portal_quick_demo" == "true" && -z "$template" ]]; then
        # Standalone --portal-quick: run all portal templates with quick mode
        py_args+=(--category portal)
        print_header "Running Portal Quick Demo (5 timepoints)"
    # Timepoint testing modes
    elif [[ "$timepoint_forward" == "true" ]]; then
        py_args+=(--timepoint-forward)
        print_header "Running Timepoint Forward"
    elif [[ "$timepoint_all" == "true" ]]; then
        py_args+=(--timepoint-all)
        print_header "Running All Timepoint Modes"
    # Convergence E2E
    elif [[ "$convergence_e2e" == "true" ]]; then
        py_args+=(--convergence-e2e)
        [[ -n "$convergence_runs" ]] && py_args+=(--convergence-runs "$convergence_runs")
        print_header "Running Convergence E2E Test"
    # Standard template/preset selection
    elif [[ -n "$template" ]]; then
        py_args+=(--template "$template")
    elif [[ -n "$preset" ]]; then
        case "$preset" in
            quick|standard|comprehensive|stress) py_args+=(--tier "$preset") ;;
            core|showcase|portal|convergence) py_args+=(--category "$preset") ;;
            all) ;; # No filter = all
        esac
    fi

    [[ -n "$tier" ]] && py_args+=(--tier "$tier")
    [[ -n "$category" ]] && py_args+=(--category "$category")
    [[ -n "$mechanism" ]] && py_args+=(--mechanism "$mechanism")
    [[ -n "$parallel" ]] && py_args+=(--parallel "$parallel")
    [[ "$skip_summaries" == "true" ]] && py_args+=(--skip-summaries)

    # Portal quick mode - ADDITIVE flag (works with any template selection)
    [[ "$portal_quick_demo" == "true" ]] && py_args+=(--portal-quick)

    # Free model options
    [[ "$free_mode" == "true" ]] && py_args+=(--free)
    [[ "$free_fast" == "true" ]] && py_args+=(--free-fast)

    # Gemini Flash option (1M context, fast inference)
    if [[ "$gemini_flash" == "true" ]]; then
        model_override="google/gemini-3-flash-preview"
        print_info "Using Gemini 3 Flash Preview (1M context, fast inference)"
        print_warning "Note: Google TOS may restrict synthetic data generation"
    fi

    # Groq ultra-fast inference (via LPU hardware)
    if [[ "$groq_mode" == "true" ]]; then
        model_override="groq/llama-3.3-70b-versatile"
        print_info "Using Groq Llama 3.3 70B (~300 tok/s, 128K context)"
        print_info "Requires GROQ_API_KEY in .env - get free key at https://console.groq.com"
    fi

    # Fast mode (fastest available model on OpenRouter)
    # NOTE: groq/mixtral-8x7b-32768 was deprecated on OpenRouter (January 2026)
    # Using standard Mixtral via OpenRouter instead
    if [[ "$groq_fast" == "true" ]]; then
        model_override="mistralai/mixtral-8x7b-instruct"
        print_info "Using Mixtral 8x7B (~200 tok/s, 32K context - fast inference)"
    fi

    # Model override
    [[ -n "$model_override" ]] && py_args+=(--model "$model_override")

    # Convergence (post-run analysis)
    [[ "$convergence" == "true" ]] && py_args+=(--convergence)
    [[ -n "$convergence_runs" ]] && py_args+=(--convergence-runs "$convergence_runs")

    # API mode
    if [[ "$api_mode" == "true" ]]; then
        py_args+=(--api --api-url "$api_url")
        [[ -n "$api_key" ]] && py_args+=(--api-key "$api_key")
        [[ -n "$api_batch_size" ]] && py_args+=(--api-batch-size "$api_batch_size")
        [[ -n "$api_budget" ]] && py_args+=(--api-budget "$api_budget")
        [[ "$api_wait" == "true" ]] && py_args+=(--api-wait)
    fi

    # Dry run - show cost estimate
    if [[ "$dry_run" == "true" ]]; then
        print_header "Dry Run - Cost Estimate"
        $PYTHON run_all_mechanism_tests.py "${py_args[@]}" --dry-run 2>/dev/null || \
            $PYTHON run_all_mechanism_tests.py "${py_args[@]}" --list-templates
        print_info "Add --budget USD to set a spending limit"
        exit 0
    fi

    # Verify API key for mode
    if [[ "$api_mode" == "true" ]]; then
        if [[ -z "$api_key" && -z "$TIMEPOINT_API_KEY" ]]; then
            print_error "API key required for --api mode"
            print_info "Set TIMEPOINT_API_KEY in .env or use --api-key"
            exit 1
        fi
        print_success "API mode enabled"
    else
        if [[ -z "$OPENROUTER_API_KEY" ]]; then
            print_error "OPENROUTER_API_KEY not set in .env"
            exit 1
        fi
    fi

    # Execute
    if [[ "$monitor" == "true" ]]; then
        print_header "Starting Monitored Execution"
        local mon_args=(--mode both --interval "$interval" --auto-confirm)
        [[ "$chat" == "true" ]] && mon_args+=(--enable-chat)

        $PYTHON -m monitoring.monitor_runner "${mon_args[@]}" -- \
            $PYTHON run_all_mechanism_tests.py "${py_args[@]}"
    else
        print_header "Starting Execution"
        [[ "$quiet" != "true" ]] && print_info "Command: $PYTHON run_all_mechanism_tests.py ${py_args[*]}"
        $PYTHON run_all_mechanism_tests.py "${py_args[@]}"
    fi

    print_header "Execution Complete"
    print_success "Check ./run.sh status for results"
}

show_run_help() {
    cat << 'EOF'
run - Execute simulations

USAGE:
    ./run.sh run [TEMPLATE|PRESET] [OPTIONS]
    ./run.sh <PRESET>                    (shortcut)
    ./run.sh <template_name>             (direct template)

PRESETS:
    quick, standard, comprehensive, stress
    core, showcase, portal, convergence, all

SELECTION OPTIONS:
    --tier TIER           Filter by tier
    --category CAT        Filter by category
    --mechanism M1,M2     Filter by mechanisms
    --template TPL        Run specific template

EXECUTION OPTIONS:
    --parallel N          Concurrent templates
    --dry-run             Cost estimate only
    --skip-summaries      Skip LLM summaries
    --budget USD          Spending limit
    --monitor             Real-time monitoring

FREE MODEL OPTIONS ($0 cost):
    --free                Use best quality free model
    --free-fast           Use fastest free model
    --list-free-models    Show available free models

GEMINI 3 FLASH OPTIONS (1M context, fast inference):
    --gemini-flash        Use google/gemini-3-flash-preview
    --gemini              Alias for --gemini-flash

GROQ OPTIONS (ultra-fast inference via LPU hardware):
    --groq                Use Groq Llama 3.3 70B (~300 tok/s, best quality)
    --fast                Use Groq Llama 8B Instant (~750 tok/s, fastest)
    --groq-fast           Alias for --fast
    Note: Requires GROQ_API_KEY in .env (free at console.groq.com)

MODEL OPTIONS:
    --model MODEL         Override LLM model for all calls
                          Examples: deepseek/deepseek-chat
                                    meta-llama/llama-3.1-70b-instruct
                                    google/gemini-3-flash-preview
                                    groq/llama-3.3-70b-versatile

PORTAL TESTING MODES:
    --portal-quick                  Quick demo mode (5 timepoints, ~2 min)
    --portal-demo                   Alias for --portal-quick
    --portal-all                    All portal testing modes
    --portal-test-only              Basic portal test
    --portal-simjudged-quick        Quick simjudged portal
    --portal-simjudged              Standard simjudged portal
    --portal-simjudged-thorough     Thorough simjudged portal
    --portal-timepoint-only         Portal timepoint test
    --portal-timepoint-all          All portal timepoint modes

TIMEPOINT TESTING MODES:
    --timepoint-forward             Forward temporal generation
    --timepoint-all                 All timepoint modes

CONVERGENCE OPTIONS:
    --convergence                   Run convergence analysis after
    --convergence-runs N            Number of runs for analysis
    --convergence-e2e               Run template N times + analyze

NATURAL LANGUAGE:
    --nl "PROMPT"                   Natural language simulation
    --nl-entities N                 Number of entities (default: 4)
    --nl-timepoints N               Number of timepoints (default: 3)

API MODE OPTIONS:
    --api                 Submit via REST API
    --api-url URL         API base URL
    --api-key KEY         API key
    --api-batch-size N    Jobs per batch
    --api-budget USD      API budget cap
    --api-wait            Wait for completion

EXAMPLES:
    # Basic usage
    ./run.sh run board_meeting
    ./run.sh run --tier quick --parallel 4
    ./run.sh quick

    # Free models ($0 cost)
    ./run.sh run --free board_meeting
    ./run.sh run --free-fast --parallel 4 quick

    # Gemini 3 Flash (1M context, fast inference)
    ./run.sh run --gemini-flash board_meeting

    # Groq ultra-fast inference
    ./run.sh run --groq board_meeting         # 5x faster, best quality
    ./run.sh run --fast quick                 # 10x faster, fastest model

    # Portal testing
    ./run.sh run --portal-all
    ./run.sh run --portal-simjudged-thorough

    # Convergence testing
    ./run.sh run --convergence-e2e --convergence-runs 3 board_meeting

    # Natural language
    ./run.sh run --nl "Simulate a startup board meeting about pivoting"

    # Model override
    ./run.sh run --model deepseek/deepseek-chat board_meeting
EOF
}

# ============================================================================
# COMMAND: LIST
# ============================================================================

cmd_list() {
    local what="templates"
    local limit=20
    local tier=""
    local category=""
    local patch_category=""
    local json_out=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_list_help; exit 0 ;;
            templates|runs|usage|mechanisms|patches) what="$1"; shift ;;
            --limit) limit="$2"; shift 2 ;;
            --tier) tier="$2"; shift 2 ;;
            --category) category="$2"; shift 2 ;;
            --patches) what="patches"; shift
                # Check if next arg is a category (not a flag)
                if [[ $# -gt 0 && "$1" != -* ]]; then
                    patch_category="$1"; shift
                fi
                ;;
            --json) json_out=true; shift ;;
            *)
                # Could be a patch category for --patches
                if [[ "$what" == "patches" && -z "$patch_category" ]]; then
                    patch_category="$1"
                fi
                shift ;;
        esac
    done

    case "$what" in
        templates)
            print_header "Available Templates"
            local args=(--list-templates)
            [[ -n "$tier" ]] && args+=(--tier "$tier")
            [[ -n "$category" ]] && args+=(--category "$category")
            $PYTHON run_all_mechanism_tests.py "${args[@]}"
            ;;
        runs)
            print_header "Recent Runs (last $limit)"
            $PYTHON -c "
from metadata.run_tracker import MetadataManager
mm = MetadataManager()
all_runs = mm.get_all_runs()
runs = sorted(all_runs, key=lambda r: r.started_at or '', reverse=True)[:$limit]
if not runs:
    print('No runs found')
else:
    print(f"{'ID':<40} {'STATUS':<12} {'TEMPLATE':<25} {'COST':<10}")
    print('-' * 90)
    for r in runs:
        cost = f'\${r.cost_usd:.2f}' if r.cost_usd else '-'
        template = r.template_id[:23] + '..' if len(r.template_id or '') > 25 else (r.template_id or '-')
        print(f'{r.run_id:<40} {r.status:<12} {template:<25} {cost:<10}')
"
            ;;
        usage)
            print_header "API Usage Statistics"
            check_env
            $PYTHON run_all_mechanism_tests.py --api-usage 2>/dev/null || \
                print_warning "API usage tracking not available"
            ;;
        mechanisms)
            print_header "Simulation Mechanisms (M1-M19)"
            cat << 'MECHS'
M1   Heterogeneous Fidelity    Per-entity resolution levels
M2   Progressive Training      Resolution elevation over time
M3   Exposure Events           Training through key moments
M4   Physics Validation        Consistency checking
M5   Lazy Resolution           On-demand detail generation
M6   Tensor Compression        Efficient state representation
M7   Causal Chains             Event-to-event causality
M8   Embodied States           Physical/emotional grounding
M9   On-Demand Entities        Dynamic entity creation
M10  Scene Atmosphere          Environmental context
M11  Dialog Synthesis          Natural conversation generation
M12  Counterfactual            What-if reasoning
M13  Relationships             Entity connection modeling
M14  Circadian Rhythms         Time-of-day effects
M15  Prospection               Future prediction
M16  Animistic Reasoning       Non-human entity modeling
M17  Modal Causality           Possibility reasoning
M18  Model Selection           Intelligent LLM routing
M19  Knowledge Extraction      Semantic knowledge from dialog
MECHS
            ;;
        patches)
            if [[ -n "$patch_category" ]]; then
                print_header "Patches: $patch_category"
            else
                print_header "Template Patches (SYNTH.md)"
            fi
            $PYTHON -c "
from generation.templates.loader import TemplateLoader
import json

loader = TemplateLoader()
patch_category = '$patch_category'
json_out = $([[ "$json_out" == "true" ]] && echo "True" || echo "False")

if patch_category:
    # List patches in specific category
    patches = loader.list_patches_by_category(patch_category)
    if json_out:
        print(json.dumps({'category': patch_category, 'patches': patches}, indent=2))
    else:
        if not patches:
            print(f'No patches found in category: {patch_category}')
            cats = ', '.join(loader.list_patch_categories())
            print(f'\\nAvailable categories: {cats}')
        else:
            for p in patches:
                meta = loader.get_patch_metadata(p)
                if meta:
                    print(f'  {meta.name:<25} {p}')
                    print(f'    {meta.description}')
                    tags_str = ', '.join(meta.tags)
                    print(f'    Tags: {tags_str}')
                    print()
                else:
                    print(f'  {p}')
else:
    # List all categories and patch counts
    if json_out:
        from dataclasses import asdict
        patches = loader.get_all_patches()
        serializable = {k: asdict(v) for k, v in patches.items()}
        print(json.dumps(serializable, indent=2))
    else:
        print(loader.get_patches_report())
"
            ;;
    esac
}

show_list_help() {
    cat << 'EOF'
list - Show information

USAGE:
    ./run.sh list [WHAT] [OPTIONS]

WHAT:
    templates     All templates (default)
    runs          Recent simulation runs
    usage         API usage statistics
    mechanisms    All 19 mechanisms
    patches       Template patches by category (SYNTH.md)

OPTIONS:
    --limit N        Limit results
    --tier TIER      Filter by tier
    --category CAT   Filter by category
    --patches [CAT]  List patches (optionally filter by category)
    --json           JSON output

PATCH CATEGORIES (SYNTH.md):
    corporate     Business/startup scenarios
    historical    Historical events
    crisis        High-stakes emergency scenarios
    mystical      Spiritual/animistic scenarios
    mystery       Detective/investigation scenarios
    mechanism     Core mechanism isolation tests
    portal        Backward reasoning scenarios
    stress        High-complexity stress tests
    convergence   Consistency evaluation tests

EXAMPLES:
    ./run.sh list
    ./run.sh list runs --limit 10
    ./run.sh list templates --tier quick
    ./run.sh list patches                   # All patch categories
    ./run.sh list patches corporate         # Patches in corporate category
    ./run.sh list --patches mystery         # Alternative syntax
    ./run.sh list patches --json            # JSON output
EOF
}

# ============================================================================
# COMMAND: STATUS
# ============================================================================

cmd_status() {
    local run_id=""
    local watch=false
    local full=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_status_help; exit 0 ;;
            --watch) watch=true; shift ;;
            --full) full=true; shift ;;
            -*) shift ;;
            *) run_id="$1"; shift ;;
        esac
    done

    $PYTHON -c "
from metadata.run_tracker import MetadataManager
import json

mm = MetadataManager()
run_id = '$run_id'
full = $([[ "$full" == "true" ]] && echo "True" || echo "False")

if run_id:
    run = mm.get_run(run_id)
else:
    all_runs = mm.get_all_runs()
    runs = sorted(all_runs, key=lambda r: r.started_at or '', reverse=True)[:1]
    run = runs[0] if runs else None

if not run:
    print('No runs found')
    exit(1)

print(f'Run ID:     {run.run_id}')
print(f'Status:     {run.status}')
print(f'Template:   {run.template_id or \"-\"}')
print(f'Started:    {run.started_at or \"-\"}')
print(f'Duration:   {run.duration_seconds or \"-\"}s')
print(f'Cost:       \${run.cost_usd:.4f}' if run.cost_usd else 'Cost:       -')
print(f'Tokens:     {run.tokens_used:,}' if run.tokens_used else 'Tokens:     -')
print(f'LLM Calls:  {run.llm_calls}' if run.llm_calls else 'LLM Calls:  -')
print(f'Entities:   {run.entities_created}' if run.entities_created else 'Entities:   -')
print(f'Timepoints: {run.timepoints_created}' if run.timepoints_created else 'Timepoints: -')

if run.error_message:
    print(f'Error:      {run.error_message}')
"
}

show_status_help() {
    cat << 'EOF'
status - Show run status

USAGE:
    ./run.sh status [RUN_ID] [OPTIONS]

OPTIONS:
    RUN_ID        Specific run (default: latest)
    --watch       Live monitoring
    --full        Show all details

EXAMPLES:
    ./run.sh status
    ./run.sh status run_20241207_123456
    ./run.sh status --full
EOF
}

# ============================================================================
# COMMAND: EXPORT
# ============================================================================

cmd_export() {
    local run_id=""
    local format="md"
    local output="exports"

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_export_help; exit 0 ;;
            --format) format="$2"; shift 2 ;;
            --output) output="$2"; shift 2 ;;
            last) run_id="last"; shift ;;
            -*) shift ;;
            *) run_id="$1"; shift ;;
        esac
    done

    if [[ -z "$run_id" ]]; then
        print_error "Run ID required (or 'last')"
        exit 1
    fi

    print_header "Exporting Run Data"

    $PYTHON -c "
from metadata.run_tracker import MetadataManager
from metadata.narrative_exporter import NarrativeExporter
from pathlib import Path

mm = MetadataManager()
run_id = '$run_id'
fmt = '$format'
out_dir = Path('$output')

if run_id == 'last':
    runs = mm.get_recent_runs(1)
    if not runs:
        print('No runs found')
        exit(1)
    run = runs[0]
    run_id = run.run_id
else:
    run = mm.get_run(run_id)

if not run:
    print(f'Run not found: {run_id}')
    exit(1)

out_dir.mkdir(exist_ok=True)
exporter = NarrativeExporter(str(out_dir))

if fmt == 'md':
    path = exporter.export_markdown(run)
elif fmt == 'json':
    path = exporter.export_json(run)
else:
    print(f'Unknown format: {fmt}')
    exit(1)

print(f'Exported to: {path}')
"
}

show_export_help() {
    cat << 'EOF'
export - Export run data

USAGE:
    ./run.sh export <RUN_ID|last> [OPTIONS]

OPTIONS:
    --format FMT    md, json, parquet (default: md)
    --output PATH   Output directory

EXAMPLES:
    ./run.sh export last
    ./run.sh export last --format json
    ./run.sh export run_123 --output ./results
EOF
}

# ============================================================================
# COMMAND: CLEAN
# ============================================================================

cmd_clean() {
    local what=""
    local older_than=""
    local dry_run=false
    local confirm=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_clean_help; exit 0 ;;
            runs|tensors|exports|all) what="$1"; shift ;;
            --older-than) older_than="$2"; shift 2 ;;
            --dry-run) dry_run=true; shift ;;
            --confirm) confirm=true; shift ;;
            *) shift ;;
        esac
    done

    if [[ -z "$what" ]]; then
        print_error "Specify what to clean: runs, tensors, exports, all"
        exit 1
    fi

    if [[ "$what" == "all" && "$confirm" != "true" ]]; then
        print_error "Use --confirm for destructive operations"
        exit 1
    fi

    print_header "Cleanup: $what"

    if [[ "$dry_run" == "true" ]]; then
        print_info "Dry run - showing what would be deleted"
    fi

    case "$what" in
        runs)
            print_info "Run cleanup not yet implemented"
            ;;
        tensors)
            print_info "Tensor cleanup not yet implemented"
            ;;
        exports)
            if [[ "$dry_run" == "true" ]]; then
                find exports -type f -name "*.md" -o -name "*.json" 2>/dev/null | head -20
            else
                rm -rf exports/*
                print_success "Exports cleaned"
            fi
            ;;
        all)
            print_warning "Full cleanup - this will delete all data!"
            if [[ "$dry_run" != "true" ]]; then
                rm -rf exports/*
                print_success "All data cleaned"
            fi
            ;;
    esac
}

show_clean_help() {
    cat << 'EOF'
clean - Cleanup data

USAGE:
    ./run.sh clean <WHAT> [OPTIONS]

WHAT:
    runs        Old simulation runs
    tensors     Orphaned tensors
    exports     Export files
    all         Everything (requires --confirm)

OPTIONS:
    --older-than N    Only items older than N days
    --dry-run         Show what would be deleted
    --confirm         Required for 'all'

EXAMPLES:
    ./run.sh clean exports
    ./run.sh clean runs --older-than 30
    ./run.sh clean all --confirm
EOF
}

# ============================================================================
# COMMAND: E2E (Full E2E Workflow Testing)
# ============================================================================

cmd_e2e() {
    local mode=""
    local runs=3
    local model=""
    local verbose=false
    local template=""
    local parallel=""
    local skip_summaries=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_e2e_help; exit 0 ;;
            --runs) runs="$2"; shift 2 ;;
            --model) model="$2"; shift 2 ;;
            --verbose) verbose=true; shift ;;
            --template) template="$2"; shift 2 ;;
            --parallel) parallel="$2"; shift 2 ;;
            --skip-summaries) skip_summaries=true; shift ;;
            full|ultra-all|portal-all|timepoint-all|convergence-e2e)
                mode="$1"; shift ;;
            -*)
                print_error "Unknown option: $1"
                exit 1 ;;
            *)
                if [[ -z "$template" ]]; then
                    template="$1"
                fi
                shift ;;
        esac
    done

    check_env

    if [[ -z "$mode" ]]; then
        print_error "E2E mode required"
        show_e2e_help
        exit 1
    fi

    local py_args=()

    case "$mode" in
        full)
            py_args+=(--full)
            print_header "Running FULL E2E Test Suite"
            print_warning "This runs ALL templates - expensive!"
            ;;
        ultra-all)
            py_args+=(--ultra-all)
            print_header "Running ULTRA-ALL E2E Test Suite"
            print_warning "Maximum coverage - very expensive!"
            ;;
        portal-all)
            py_args+=(--portal-all)
            print_header "Running All Portal Modes"
            ;;
        timepoint-all)
            py_args+=(--timepoint-all)
            print_header "Running All Timepoint Modes"
            ;;
        convergence-e2e)
            py_args+=(--convergence-e2e)
            py_args+=(--convergence-runs "$runs")
            if [[ -n "$template" ]]; then
                py_args+=(--template "$template")
            fi
            print_header "Running Convergence E2E Test"
            print_info "Running template $runs times + convergence analysis"
            ;;
    esac

    [[ -n "$model" ]] && py_args+=(--model "$model")
    [[ -n "$parallel" ]] && py_args+=(--parallel "$parallel")
    [[ "$skip_summaries" == "true" ]] && py_args+=(--skip-summaries)
    [[ "$verbose" == "true" ]] && py_args+=(--convergence-verbose)

    print_info "Command: $PYTHON run_all_mechanism_tests.py ${py_args[*]}"
    $PYTHON run_all_mechanism_tests.py "${py_args[@]}"
}

show_e2e_help() {
    cat << 'EOF'
e2e - Full E2E Workflow Testing

USAGE:
    ./run.sh e2e <MODE> [OPTIONS]

MODES:
    full              Run ALL templates (expensive!)
    ultra-all         Maximum coverage - all tests + all portal modes
    portal-all        All portal testing modes
    timepoint-all     All timepoint testing modes
    convergence-e2e   Run template N times + convergence analysis

OPTIONS:
    --runs N          Number of runs for convergence (default: 3)
    --model MODEL     Override LLM model for all tests
    --template TPL    Template for convergence-e2e mode
    --parallel N      Concurrent templates
    --skip-summaries  Skip LLM summary generation
    --verbose         Show detailed convergence divergence points

EXAMPLES:
    ./run.sh e2e full                           # All templates
    ./run.sh e2e portal-all                     # All portal modes
    ./run.sh e2e convergence-e2e board_meeting  # Run 3x + analyze
    ./run.sh e2e convergence-e2e --runs 5 --template convergence_simple
    ./run.sh e2e ultra-all --parallel 4         # Maximum test coverage

COST ESTIMATES:
    full:         $10-50 (depends on model)
    ultra-all:    $50-200
    portal-all:   $5-20
    timepoint-all: $5-15
    convergence-e2e: $0.15-3.00 per run × N runs
EOF
}

# ============================================================================
# COMMAND: CONVERGENCE (Convergence Analysis)
# ============================================================================

cmd_convergence() {
    local action=""
    local runs=3
    local template=""
    local verbose=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_convergence_help; exit 0 ;;
            --runs) runs="$2"; shift 2 ;;
            --template) template="$2"; shift 2 ;;
            --verbose) verbose=true; shift ;;
            analyze|e2e|history)
                action="$1"; shift ;;
            -*)
                print_error "Unknown option: $1"
                exit 1 ;;
            *)
                if [[ -z "$template" ]]; then
                    template="$1"
                fi
                shift ;;
        esac
    done

    check_env

    if [[ -z "$action" ]]; then
        action="analyze"
    fi

    local py_args=()

    case "$action" in
        analyze)
            py_args+=(--convergence-only)
            py_args+=(--convergence-runs "$runs")
            [[ -n "$template" ]] && py_args+=(--convergence-template "$template")
            [[ "$verbose" == "true" ]] && py_args+=(--convergence-verbose)
            print_header "Convergence Analysis"
            print_info "Analyzing last $runs runs"
            ;;
        e2e)
            py_args+=(--convergence-e2e)
            py_args+=(--convergence-runs "$runs")
            [[ -n "$template" ]] && py_args+=(--template "$template")
            [[ "$verbose" == "true" ]] && py_args+=(--convergence-verbose)
            print_header "Convergence E2E Test"
            print_info "Running template $runs times + analysis"
            ;;
        history)
            print_header "Convergence History"
            $PYTHON -c "
from storage import GraphStore
store = GraphStore('sqlite:///metadata/runs.db')
try:
    from sqlmodel import Session, select
    from schemas import ConvergenceSet
    with Session(store.engine) as session:
        sets = session.exec(select(ConvergenceSet).order_by(ConvergenceSet.created_at.desc()).limit(10)).all()
        if not sets:
            print('No convergence results found')
        else:
            print(f\"{'SET_ID':<20} {'TEMPLATE':<25} {'SCORE':<10} {'GRADE':<6}\")
            print('-' * 65)
            for s in sets:
                print(f\"{s.set_id:<20} {(s.template_id or '-'):<25} {s.convergence_score:.1%:<10} {s.robustness_grade:<6}\")
except Exception as e:
    print(f'Error: {e}')
"
            return
            ;;
    esac

    print_info "Command: $PYTHON run_all_mechanism_tests.py ${py_args[*]}"
    $PYTHON run_all_mechanism_tests.py "${py_args[@]}"
}

show_convergence_help() {
    cat << 'EOF'
convergence - Convergence Analysis

USAGE:
    ./run.sh convergence <ACTION> [OPTIONS]

ACTIONS:
    analyze         Analyze recent runs (default)
    e2e             Run template N times + analyze
    history         Show convergence result history

OPTIONS:
    --runs N        Number of runs to analyze (default: 3)
    --template TPL  Filter by template ID
    --verbose       Show detailed divergence points

EXAMPLES:
    ./run.sh convergence                           # Analyze last 3 runs
    ./run.sh convergence analyze --runs 5          # Analyze last 5 runs
    ./run.sh convergence analyze --template board_meeting
    ./run.sh convergence e2e board_meeting         # Run 3x + analyze
    ./run.sh convergence e2e --runs 5 convergence_simple
    ./run.sh convergence history                   # Show history

CONVERGENCE GRADES:
    A: Excellent (>90%) - Highly robust causal mechanisms
    B: Good (80-90%) - Reasonably stable
    C: Fair (70-80%) - Some variability
    D: Poor (60-70%) - Significant divergence
    F: Fail (<60%) - Highly sensitive to conditions
EOF
}

# ============================================================================
# COMMAND: API
# ============================================================================

cmd_api() {
    local action=""
    local preset=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_api_help; exit 0 ;;
            start|stop|usage|submit) action="$1"; shift ;;
            *) preset="$1"; shift ;;
        esac
    done

    check_env

    case "$action" in
        start)
            print_header "Starting API Server"
            $PYTHON -m uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
            ;;
        stop)
            print_info "Stopping API server..."
            pkill -f "uvicorn api.main:app" || print_warning "No server running"
            ;;
        usage)
            print_header "API Usage Statistics"
            $PYTHON run_all_mechanism_tests.py --api-usage
            ;;
        submit)
            if [[ -z "$preset" ]]; then
                print_error "Specify preset to submit"
                exit 1
            fi
            print_header "Submitting via API: $preset"
            $PYTHON run_all_mechanism_tests.py --api --tier "$preset"
            ;;
        *)
            print_error "Unknown API action: $action"
            show_api_help
            exit 1
            ;;
    esac
}

show_api_help() {
    cat << 'EOF'
api - API server operations

USAGE:
    ./run.sh api <ACTION> [OPTIONS]

ACTIONS:
    start       Start API server (port 8080)
    stop        Stop API server
    usage       Show quota usage
    submit      Submit templates via API

EXAMPLES:
    ./run.sh api start
    ./run.sh api usage
    ./run.sh api submit quick
EOF
}

# ============================================================================
# COMMAND: TEST (Pytest Integration)
# ============================================================================

cmd_test() {
    local suite=""
    local marker=""
    local coverage=false
    local parallel=""
    local verbose=false
    local extra_args=()

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_test_help; exit 0 ;;
            unit|integration|e2e|mechanisms|synth) suite="$1"; shift ;;
            --coverage|--cov) coverage=true; shift ;;
            --parallel|-n) parallel="$2"; shift 2 ;;
            --verbose|-v) verbose=true; shift ;;
            --marker|-m) marker="$2"; shift 2 ;;
            m1|m2|m3|m4|m5|m6|m7|m8|m9|m10|m11|m12|m13|m14|m15|m16|m17|m18|m19)
                marker="$1"; shift ;;
            -*) extra_args+=("$1"); shift ;;
            *) extra_args+=("$1"); shift ;;
        esac
    done

    local pytest_args=(-v)

    # Apply suite-based markers
    case "$suite" in
        unit) pytest_args+=(-m "unit") ;;
        integration) pytest_args+=(-m "integration") ;;
        e2e) pytest_args+=(-m "e2e") ;;
        mechanisms) pytest_args+=(-m "mechanism") ;;
        synth) pytest_args+=(-m "synth") ;;
    esac

    # Apply specific marker
    if [[ -n "$marker" ]]; then
        pytest_args+=(-m "$marker")
    fi

    # Coverage
    if [[ "$coverage" == "true" ]]; then
        pytest_args+=(--cov=. --cov-report=html --cov-report=term)
    fi

    # Parallel execution
    if [[ -n "$parallel" ]]; then
        pytest_args+=(-n "$parallel")
    fi

    # Verbose
    if [[ "$verbose" == "true" ]]; then
        pytest_args+=(-vv)
    fi

    # Extra args
    pytest_args+=("${extra_args[@]}")

    print_header "Running Tests"
    [[ -n "$suite" ]] && print_info "Suite: $suite"
    [[ -n "$marker" ]] && print_info "Marker: $marker"
    print_info "Command: $PYTHON -m pytest ${pytest_args[*]}"
    echo ""

    $PYTHON -m pytest "${pytest_args[@]}"
}

show_test_help() {
    cat << 'EOF'
test - Run pytest test suites

USAGE:
    ./run.sh test [SUITE] [OPTIONS]

SUITES:
    unit            Unit tests (fast, isolated)
    integration     Integration tests
    e2e             End-to-end tests
    mechanisms      All mechanism tests (M1-M19)
    synth           SynthasAIzer tests (envelopes, voices, patches)

MECHANISM SHORTCUTS:
    m1, m2, ... m19     Run specific mechanism tests

OPTIONS:
    --marker, -m MARKER   Custom pytest marker
    --coverage, --cov     Generate coverage report
    --parallel, -n N      Run N tests in parallel
    --verbose, -v         Verbose output

EXAMPLES:
    ./run.sh test                     # All tests
    ./run.sh test unit                # Unit tests only
    ./run.sh test synth               # SynthasAIzer tests (53 tests)
    ./run.sh test mechanisms          # All mechanism tests
    ./run.sh test m7                  # M7 causal chain tests
    ./run.sh test --coverage          # With coverage report
    ./run.sh test unit --parallel 4   # Parallel unit tests

PYTEST MARKERS (from pytest.ini):
    unit, integration, system, e2e    Test levels
    synth, template, patch, envelope  SynthasAIzer paradigm
    mechanism, m1-m19                 Mechanism isolation
    llm, slow                         Resource markers
EOF
}

# ============================================================================
# COMMAND: DASHBOARD
# ============================================================================

cmd_dashboard() {
    local action="start"

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_dashboard_help; exit 0 ;;
            start) action="start"; shift ;;
            stop) action="stop"; shift ;;
            *) shift ;;
        esac
    done

    case "$action" in
        start)
            print_header "Starting API Backend"
            print_info "URL: http://localhost:8000"
            print_info "API Docs: http://localhost:8000/docs"
            cd dashboards && ./backend.sh
            ;;
        stop)
            print_header "Stopping API Backend"
            pkill -f "api/server.py" 2>/dev/null || true
            lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
            print_success "API backend stopped"
            ;;
    esac
}

show_dashboard_help() {
    cat << 'EOF'
dashboard - API backend server

USAGE:
    ./run.sh dashboard [ACTION]

ACTIONS:
    start           Start API backend (default)
    stop            Stop API backend

URLS:
    API:        http://localhost:8000
    API Docs:   http://localhost:8000/docs

ENDPOINTS:
    GET  /runs              List simulation runs
    GET  /runs/{id}         Get run details
    GET  /entities          List entities
    GET  /timepoints        List timepoints
    GET  /mechanisms        Get mechanism stats
    POST /submit            Submit new simulation

EXAMPLES:
    ./run.sh dashboard              # Start API backend
    ./run.sh dashboard stop         # Stop API backend
EOF
}

# ============================================================================
# COMMAND: DOCTOR (Environment Check)
# ============================================================================

cmd_doctor() {
    print_header "Environment Doctor"
    local errors=0

    # Python version
    echo -n "Python 3.10+... "
    if command -v python3.10 &> /dev/null; then
        version=$($PYTHON --version 2>&1)
        print_success "$version"
    else
        print_error "python3.10 not found"
        ((errors++))
    fi

    # .env file
    echo -n ".env file... "
    if [[ -f .env ]]; then
        print_success "found"
    else
        print_error "missing"
        ((errors++))
    fi

    # API keys
    if [[ -f .env ]]; then
        source .env

        echo -n "OPENROUTER_API_KEY... "
        if [[ -n "$OPENROUTER_API_KEY" ]]; then
            print_success "set (${#OPENROUTER_API_KEY} chars)"
        else
            print_error "missing"
            ((errors++))
        fi

        echo -n "OXEN_API_KEY... "
        if [[ -n "$OXEN_API_KEY" ]]; then
            print_success "set (${#OXEN_API_KEY} chars)"
        else
            print_warning "missing (optional)"
        fi
    fi

    # Database
    echo -n "Runs database... "
    if [[ -f "$DB_PATH" ]]; then
        size=$(du -h "$DB_PATH" | cut -f1)
        print_success "found ($size)"
    else
        print_warning "not created yet"
    fi

    # Key dependencies
    echo -n "pytest... "
    if $PYTHON -c "import pytest" 2>/dev/null; then
        print_success "installed"
    else
        print_error "missing"
        ((errors++))
    fi

    echo -n "synth module... "
    if $PYTHON -c "from synth import EnvelopeConfig" 2>/dev/null; then
        print_success "installed"
    else
        print_error "missing"
        ((errors++))
    fi

    echo -n "TemplateLoader... "
    if $PYTHON -c "from generation.templates.loader import TemplateLoader" 2>/dev/null; then
        print_success "available"
    else
        print_error "missing"
        ((errors++))
    fi

    # Summary
    echo ""
    if [[ $errors -eq 0 ]]; then
        print_success "All checks passed!"
    else
        print_error "$errors issue(s) found"
        exit 1
    fi
}

# ============================================================================
# COMMAND: INFO
# ============================================================================

cmd_info() {
    print_header "Timepoint Daedalus Info"

    echo "Version:     1.0.0 (SynthasAIzer)"
    echo "Python:      $($PYTHON --version 2>&1)"
    echo ""

    # Template count
    template_count=$($PYTHON -c "
from generation.templates.loader import TemplateLoader
loader = TemplateLoader()
print(len(loader.list_templates()))
" 2>/dev/null || echo "?")
    echo "Templates:   $template_count"

    # Test count
    test_count=$(find tests -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')
    echo "Test files:  $test_count"

    # Synth module
    synth_version=$($PYTHON -c "import synth; print(synth.__version__)" 2>/dev/null || echo "?")
    echo "Synth:       v$synth_version"

    # Database stats
    if [[ -f "$DB_PATH" ]]; then
        run_count=$($PYTHON -c "
from metadata.run_tracker import MetadataManager
mm = MetadataManager()
print(len(mm.get_recent_runs(1000)))
" 2>/dev/null || echo "?")
        echo "Total runs:  $run_count"
    fi

    echo ""
    echo "Key Paths:"
    echo "  Templates:  generation/templates/"
    echo "  Synth:      synth/"
    echo "  Tests:      tests/"
    echo "  Database:   $DB_PATH"
}

# ============================================================================
# TEMPLATE SHORTCUTS - All 41 templates accessible by name
# ============================================================================

# Core mechanism tests (M1-M19)
CORE_TEMPLATES=(
    "m01_heterogeneous_fidelity"
    "m02_progressive_training"
    "m03_exposure_events"
    "m04_physics_validation"
    "m05_lazy_resolution"
    "m06_tensor_compression"
    "m07_causal_chains"
    "m08_embodied_states"
    "m09_on_demand_entities"
    "m10_scene_atmosphere"
    "m11_dialog_synthesis"
    "m12_counterfactual"
    "m13_relationships"
    "m14_circadian"
    "m15_prospection"
    "m16_animistic"
    "m17_modal_causality"
    "m18_model_selection"
)

# Showcase templates
SHOWCASE_TEMPLATES=(
    "board_meeting"
    "jefferson_dinner"
    "hospital_crisis"
    "detective_prospection"
    "kami_shrine"
    "vc_pitch_pearl"
    "vc_pitch_branching"
    "vc_pitch_roadshow"
    "vc_pitch_strategies"
    "hound_shadow_directorial"
)

# Portal templates
PORTAL_TEMPLATES=(
    "startup_unicorn"
    "presidential_election"
    "academic_tenure"
    "startup_failure"
)

# Stress templates
STRESS_TEMPLATES=(
    "constitutional_convention_day1"
    "scarlet_study_deep"
    "empty_house_flashback"
    "final_problem_branching"
    "sign_loops_cyclical"
    "tensor_resolution_hybrid"
)

# Convergence templates
CONVERGENCE_TEMPLATES=(
    "convergence_simple"
    "convergence_standard"
    "convergence_comprehensive"
)

# Function to check if argument is a known template
is_template() {
    local name="$1"
    for t in "${CORE_TEMPLATES[@]}" "${SHOWCASE_TEMPLATES[@]}" "${PORTAL_TEMPLATES[@]}" "${STRESS_TEMPLATES[@]}" "${CONVERGENCE_TEMPLATES[@]}"; do
        if [[ "$t" == "$name" ]]; then
            return 0
        fi
    done
    return 1
}

# ============================================================================
# MAIN DISPATCH
# ============================================================================

main() {
    if [[ $# -eq 0 ]]; then
        show_main_help
        exit 0
    fi

    local cmd="$1"
    shift

    case "$cmd" in
        -h|--help|help)
            if [[ "$1" == "full" || "$cmd" == "help" ]]; then
                show_full_help
            else
                show_main_help
            fi
            ;;
        run)
            cmd_run "$@"
            ;;
        list)
            cmd_list "$@"
            ;;
        status)
            cmd_status "$@"
            ;;
        export)
            cmd_export "$@"
            ;;
        clean)
            cmd_clean "$@"
            ;;
        api)
            cmd_api "$@"
            ;;
        e2e)
            cmd_e2e "$@"
            ;;
        convergence)
            cmd_convergence "$@"
            ;;
        test)
            cmd_test "$@"
            ;;
        dashboard)
            cmd_dashboard "$@"
            ;;
        doctor)
            cmd_doctor
            ;;
        info)
            cmd_info
            ;;
        # Shortcuts - direct presets
        quick|standard|comprehensive|stress|core|showcase|portal|all)
            cmd_run "$cmd" "$@"
            ;;
        # Core mechanism templates (M1-M19)
        m01_*|m02_*|m03_*|m04_*|m05_*|m06_*|m07_*|m08_*|m09_*|m10_*|m11_*|m12_*|m13_*|m14_*|m15_*|m16_*|m17_*|m18_*|m19_*)
            cmd_run "$cmd" "$@"
            ;;
        # Showcase templates
        board_meeting|jefferson_dinner|hospital_crisis|detective_prospection|kami_shrine)
            cmd_run "$cmd" "$@"
            ;;
        vc_pitch_pearl|vc_pitch_branching|vc_pitch_roadshow|vc_pitch_strategies|hound_shadow_directorial)
            cmd_run "$cmd" "$@"
            ;;
        # Portal templates
        startup_unicorn|presidential_election|academic_tenure|startup_failure)
            cmd_run "$cmd" "$@"
            ;;
        # Stress templates
        constitutional_convention_day1|scarlet_study_deep|empty_house_flashback|final_problem_branching|sign_loops_cyclical|tensor_resolution_hybrid)
            cmd_run "$cmd" "$@"
            ;;
        # Convergence templates
        convergence_simple|convergence_standard|convergence_comprehensive)
            cmd_run "$cmd" "$@"
            ;;
        # Legacy flag support
        --*)
            cmd_run "$cmd" "$@"
            ;;
        *)
            # Check if it's a known template, otherwise try as template name
            if is_template "$cmd"; then
                cmd_run "$cmd" "$@"
            else
                # Assume it's a template name anyway
                cmd_run "$cmd" "$@"
            fi
            ;;
    esac
}

main "$@"
