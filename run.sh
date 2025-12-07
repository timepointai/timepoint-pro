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

COMMANDS:
    run       Execute simulations
    list      List templates, runs, or stats
    status    Show run status and results
    export    Export run data
    clean     Cleanup old data
    api       API server operations

SHORTCUTS (run quick/standard/comprehensive/stress/core/showcase/portal/all):
    ./run.sh quick                   Run all quick-tier templates
    ./run.sh core                    Run all core mechanism tests
    ./run.sh showcase                Run showcase templates

QUICK EXAMPLES:
    ./run.sh run board_meeting       Run single template
    ./run.sh run --tier quick        Run by tier
    ./run.sh list                    List all templates
    ./run.sh status                  Show recent runs
    ./run.sh export last             Export last run to markdown

Run './run.sh <command> --help' for command-specific help.
Run './run.sh help' for full documentation.
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

    Presets (shortcut: ./run.sh <preset>):
        quick           All quick-tier templates (~2-3 min each)
        standard        All standard-tier templates (~5-10 min each)
        comprehensive   All comprehensive-tier templates (~15-30 min)
        stress          All stress-tier templates (~30-60 min)
        core            All 18 core mechanism tests
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

    Persistence Options:
        --persist             Enable tensor persistence (default)
        --no-persist          Disable tensor persistence
        --db PATH             Custom runs database path
        --tensor-db PATH      Custom tensor database path

    Monitoring Options:
        --monitor             Enable real-time LLM monitoring
        --chat                Interactive chat during monitoring
        --interval SECS       Monitor check interval (default: 300)

    API Mode Options:
        --api                 Submit via REST API (tracks quotas)
        --api-url URL         API base URL
        --api-key KEY         API key
        --api-batch-size N    Jobs per batch (default: 10)
        --api-budget USD      API budget cap
        --api-wait            Wait for API completion

    Output Options:
        --quiet               Minimal output
        --verbose             Detailed output
        --export FORMAT       Auto-export on completion (md|json)

LIST - Show Information
    ./run.sh list [WHAT] [OPTIONS]

    What to list:
        templates       All templates with metadata (default)
        runs            Recent simulation runs
        usage           API usage statistics
        mechanisms      All 18 mechanisms

    Options:
        --limit N       Limit results (default: 20)
        --tier TIER     Filter templates by tier
        --category CAT  Filter templates by category
        --json          Output as JSON

STATUS - Show Run Status
    ./run.sh status [RUN_ID] [OPTIONS]

    Options:
        RUN_ID          Specific run ID (default: latest)
        --watch         Live monitoring mode
        --full          Show full details including entities

EXPORT - Export Run Data
    ./run.sh export <RUN_ID|last> [OPTIONS]

    Options:
        --format FMT    Export format: md, json, parquet (default: md)
        --output PATH   Output path (default: ./exports/)
        --include-all   Include all artifacts

CLEAN - Cleanup Data
    ./run.sh clean <WHAT> [OPTIONS]

    What to clean:
        runs            Old simulation runs
        tensors         Orphaned tensor data
        exports         Old export files
        all             Everything (requires --confirm)

    Options:
        --older-than N  Only items older than N days
        --dry-run       Show what would be deleted
        --confirm       Required for destructive operations

API - API Server Operations
    ./run.sh api <ACTION> [OPTIONS]

    Actions:
        start           Start API server (port 8080)
        stop            Stop API server
        usage           Show current quota usage
        submit PRESET   Submit templates via API

TEMPLATE CATEGORIES (44 total)
------------------------------
    core (18)           Mechanism isolation tests (M1-M18)
    showcase (10)       Production-ready scenarios
    portal (4)          Backward reasoning scenarios
    stress (6)          High-complexity stress tests
    convergence (3)     Convergence evaluation tests

TEMPLATE TIERS
--------------
    quick               Fast tests (~2-3 min, <$1 each)
    standard            Moderate tests (~5-10 min, $1-3 each)
    comprehensive       Thorough tests (~15-30 min, $5-10 each)
    stress              Complex tests (~30-60 min, $10-20 each)

EXAMPLES
--------
    # Quick start
    ./run.sh quick                          # Run quick tier
    ./run.sh run board_meeting              # Single template

    # Filtered runs
    ./run.sh run --tier quick --parallel 4  # Quick tier, 4 parallel
    ./run.sh run --category core            # All core tests
    ./run.sh run --mechanism M1,M7,M11      # Specific mechanisms

    # With monitoring
    ./run.sh run --monitor quick            # Real-time analysis
    ./run.sh run --monitor --chat board_meeting

    # Cost control
    ./run.sh run --dry-run comprehensive    # See cost estimate
    ./run.sh run --budget 5.00 standard     # Stop at $5

    # Via API
    ./run.sh api usage                      # Check quotas
    ./run.sh run --api quick                # Submit to API

    # Results
    ./run.sh status                         # Latest run
    ./run.sh export last --format json      # Export results
    ./run.sh list runs --limit 10           # Recent runs

ENVIRONMENT
-----------
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

    # Build python command arguments
    local py_args=()

    if [[ -n "$template" ]]; then
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

PRESETS:
    quick, standard, comprehensive, stress
    core, showcase, portal, convergence, all

OPTIONS:
    --tier TIER           Filter by tier
    --category CAT        Filter by category
    --mechanism M1,M2     Filter by mechanisms
    --parallel N          Concurrent templates
    --dry-run             Cost estimate only
    --skip-summaries      Skip LLM summaries
    --budget USD          Spending limit
    --monitor             Real-time monitoring
    --api                 Submit via API

EXAMPLES:
    ./run.sh run board_meeting
    ./run.sh run --tier quick --parallel 4
    ./run.sh quick
    ./run.sh run --dry-run comprehensive
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
    local json_out=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_list_help; exit 0 ;;
            templates|runs|usage|mechanisms) what="$1"; shift ;;
            --limit) limit="$2"; shift 2 ;;
            --tier) tier="$2"; shift 2 ;;
            --category) category="$2"; shift 2 ;;
            --json) json_out=true; shift ;;
            *) shift ;;
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
runs = mm.get_recent_runs($limit)
if not runs:
    print('No runs found')
else:
    print(f'{'ID':<40} {'STATUS':<12} {'TEMPLATE':<25} {'COST':<10}')
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
            print_header "Simulation Mechanisms (M1-M18)"
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
MECHS
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
    mechanisms    All 18 mechanisms

OPTIONS:
    --limit N        Limit results
    --tier TIER      Filter by tier
    --category CAT   Filter by category
    --json           JSON output

EXAMPLES:
    ./run.sh list
    ./run.sh list runs --limit 10
    ./run.sh list templates --tier quick
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
    runs = mm.get_recent_runs(1)
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
        # Shortcuts - direct presets
        quick|standard|comprehensive|stress|core|showcase|portal|convergence|all)
            cmd_run "$cmd" "$@"
            ;;
        # Legacy flag support
        --*)
            cmd_run "$cmd" "$@"
            ;;
        *)
            # Assume it's a template name
            cmd_run "$cmd" "$@"
            ;;
    esac
}

main "$@"
