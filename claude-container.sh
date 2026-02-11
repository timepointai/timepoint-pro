#!/bin/bash
#
# claude-container.sh - Containerized Claude Code for Timepoint Daedalus
#
# Builds and manages a Docker sandbox for running Claude Code with
# --dangerously-skip-permissions, following Anthropic's official devcontainer
# pattern with network-level isolation.
#
# Architecture:
#   - Docker container based on Anthropic's devcontainer standard
#   - iptables firewall: default-deny egress, allowlisted API endpoints
#   - Workspace mounted at same absolute path (Docker Sandbox pattern)
#   - Host ~/.claude/ settings and project .claude/ settings preserved
#   - .env vars injected without mounting the file
#
# Usage:
#   ./claude-container.sh up [ARGS...]            # Build + start + launch Claude (one-shot)
#   ./claude-container.sh build                  # Build container image
#   ./claude-container.sh start                  # Start sandbox container
#   ./claude-container.sh claude [ARGS...]       # Run Claude Code (DSP mode)
#   ./claude-container.sh shell                  # Interactive shell
#   ./claude-container.sh test                   # Readiness + connectivity test
#   ./claude-container.sh worktree <branch>      # Create git worktree
#   ./claude-container.sh stop                   # Stop container
#   ./claude-container.sh status                 # Container health
#   ./claude-container.sh logs                   # Container logs
#   ./claude-container.sh destroy                # Remove container + image
#
# Environment variables (all optional, sensible defaults):
#   CLAUDE_CONTAINER_NAME    Container name        (default: claude-daedalus)
#   CLAUDE_IMAGE_NAME        Image name            (default: claude-daedalus-sandbox)
#   CLAUDE_CODE_VERSION      Claude Code version   (default: latest)
#   CLAUDE_EXTRA_DOMAINS     Extra allowed domains (space-separated)
#   CLAUDE_NO_FIREWALL       Skip firewall setup   (default: false)
#
# References:
#   - https://github.com/anthropics/claude-code/blob/main/.devcontainer/
#   - https://docs.docker.com/ai/sandboxes/claude-code/
#   - https://www.anthropic.com/engineering/claude-code-sandboxing

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVCONTAINER_DIR="${SCRIPT_DIR}/.devcontainer"
PROJECT_DIR="${SCRIPT_DIR}"

# Parameterized (override via environment)
CONTAINER_NAME="${CLAUDE_CONTAINER_NAME:-claude-daedalus}"
IMAGE_NAME="${CLAUDE_IMAGE_NAME:-claude-daedalus-sandbox}"
CLAUDE_CODE_VERSION="${CLAUDE_CODE_VERSION:-latest}"
EXTRA_DOMAINS="${CLAUDE_EXTRA_DOMAINS:-}"
NO_FIREWALL="${CLAUDE_NO_FIREWALL:-false}"

# Host paths (mounted into container at same absolute path)
HOST_CLAUDE_DIR="${HOME}/.claude"
HOST_PROJECT_CLAUDE_DIR="${PROJECT_DIR}/.claude"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================================
# HELPERS
# ============================================================================

log_header() { echo -e "\n${BLUE}${BOLD}$1${NC}"; echo -e "${BLUE}$(printf '=%.0s' {1..60})${NC}"; }
log_ok()     { echo -e "${GREEN}[OK]${NC} $1"; }
log_fail()   { echo -e "${RED}[FAIL]${NC} $1"; }
log_warn()   { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_info()   { echo -e "${CYAN}[INFO]${NC} $1"; }

check_docker() {
    if ! command -v docker &>/dev/null; then
        log_fail "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
        exit 1
    fi
    if ! docker info &>/dev/null 2>&1; then
        log_fail "Docker daemon not running. Start Docker Desktop."
        exit 1
    fi
}

check_devcontainer_files() {
    if [[ ! -f "${DEVCONTAINER_DIR}/Dockerfile" ]]; then
        log_fail "Missing ${DEVCONTAINER_DIR}/Dockerfile"
        exit 1
    fi
    if [[ ! -f "${DEVCONTAINER_DIR}/init-firewall.sh" ]]; then
        log_fail "Missing ${DEVCONTAINER_DIR}/init-firewall.sh"
        exit 1
    fi
}

is_running() {
    docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"
}

# Load .env vars without mounting the file (security: inject as env vars only)
# Populates the global ENV_ARGS array (arrays can't survive subshells/echo)
ENV_ARGS=()
collect_env_vars() {
    ENV_ARGS=()

    # Source .env if it exists
    if [[ -f "${PROJECT_DIR}/.env" ]]; then
        set -a
        # shellcheck source=/dev/null
        source "${PROJECT_DIR}/.env"
        set +a
    fi

    # Pass through API keys (from .env or current environment)
    [[ -n "${OPENROUTER_API_KEY:-}" ]]  && ENV_ARGS+=(-e "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}")
    [[ -n "${ANTHROPIC_API_KEY:-}" ]]   && ENV_ARGS+=(-e "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}")
    [[ -n "${OXEN_API_KEY:-}" ]]        && ENV_ARGS+=(-e "OXEN_API_KEY=${OXEN_API_KEY}")
    [[ -n "${GROQ_API_KEY:-}" ]]        && ENV_ARGS+=(-e "GROQ_API_KEY=${GROQ_API_KEY}")
    [[ -n "${TIMEPOINT_API_KEY:-}" ]]   && ENV_ARGS+=(-e "TIMEPOINT_API_KEY=${TIMEPOINT_API_KEY}")

    # Claude Code settings
    ENV_ARGS+=(-e "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1")
    ENV_ARGS+=(-e "NODE_OPTIONS=--max-old-space-size=4096")

    # Extra allowed domains for firewall
    [[ -n "${EXTRA_DOMAINS}" ]] && ENV_ARGS+=(-e "EXTRA_ALLOWED_DOMAINS=${EXTRA_DOMAINS}")

    # Timezone
    ENV_ARGS+=(-e "TZ=${TZ:-America/Los_Angeles}")
}

# ============================================================================
# COMMANDS
# ============================================================================

cmd_build() {
    log_header "Building Claude Code Sandbox Image"
    check_docker
    check_devcontainer_files

    local host_uid
    local host_gid
    host_uid=$(id -u)
    host_gid=$(id -g)

    log_info "Image: ${IMAGE_NAME}"
    log_info "Claude Code: ${CLAUDE_CODE_VERSION}"
    log_info "Host UID/GID: ${host_uid}/${host_gid}"

    docker build \
        --build-arg "TZ=${TZ:-America/Los_Angeles}" \
        --build-arg "CLAUDE_CODE_VERSION=${CLAUDE_CODE_VERSION}" \
        --build-arg "HOST_UID=${host_uid}" \
        --build-arg "HOST_GID=${host_gid}" \
        -t "${IMAGE_NAME}" \
        -f "${DEVCONTAINER_DIR}/Dockerfile" \
        "${DEVCONTAINER_DIR}"

    log_ok "Image built: ${IMAGE_NAME}"
    echo ""
    log_info "Next: ./claude-container.sh up    (start sandbox + launch Claude Code)"
    log_info "  or: ./claude-container.sh start  (start sandbox only)"
}

cmd_start() {
    log_header "Starting Claude Code Sandbox"
    check_docker

    if is_running; then
        log_warn "Container '${CONTAINER_NAME}' is already running"
        return 0
    fi

    # Remove stopped container with same name
    docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

    # Check image exists
    if ! docker image inspect "${IMAGE_NAME}" &>/dev/null; then
        log_info "Image not found, building first..."
        cmd_build
    fi

    # Collect environment variables into ENV_ARGS global array
    collect_env_vars

    # Ensure ~/.claude exists on host
    mkdir -p "${HOST_CLAUDE_DIR}"

    log_info "Container: ${CONTAINER_NAME}"
    log_info "Workspace: ${PROJECT_DIR} (same-path mount)"
    log_info "Settings:  ${HOST_CLAUDE_DIR} -> container ~/.claude"

    # Start container with:
    # - NET_ADMIN + NET_RAW for iptables firewall (Anthropic standard)
    # - Same-path workspace mount (Docker Sandbox pattern)
    # - ~/.claude mounted for settings persistence
    # - .env vars injected (not mounted)
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --cap-add=NET_ADMIN \
        --cap-add=NET_RAW \
        -v "${PROJECT_DIR}:${PROJECT_DIR}:delegated" \
        -v "${HOST_CLAUDE_DIR}:/home/claude/.claude" \
        -w "${PROJECT_DIR}" \
        "${ENV_ARGS[@]}" \
        "${IMAGE_NAME}" \
        sleep infinity

    log_ok "Container started"

    # Initialize firewall
    if [[ "${NO_FIREWALL}" != "true" ]]; then
        log_info "Initializing network firewall..."
        docker exec "${CONTAINER_NAME}" sudo /usr/local/bin/init-firewall.sh 2>&1 | \
            while IFS= read -r line; do echo "  ${line}"; done
    else
        log_warn "Firewall disabled (CLAUDE_NO_FIREWALL=true)"
    fi

    # Install project dependencies if pyproject.toml exists
    if [[ -f "${PROJECT_DIR}/pyproject.toml" ]]; then
        log_info "Installing Python dependencies..."
        # Prefer poetry (project uses [tool.poetry.dependencies]).
        # pip install -e . with poetry-core backend exits 0 but installs zero
        # deps because they aren't in [project.dependencies], so it must NOT
        # come first in an || chain.
        docker exec -w "${PROJECT_DIR}" "${CONTAINER_NAME}" \
            poetry install --no-interaction 2>&1 | tail -5 || \
        docker exec -w "${PROJECT_DIR}" "${CONTAINER_NAME}" \
            pip install --no-cache-dir -e ".[dev]" 2>/dev/null || \
        docker exec -w "${PROJECT_DIR}" "${CONTAINER_NAME}" \
            pip install --no-cache-dir -r requirements.txt 2>/dev/null || \
        log_warn "Could not auto-install dependencies (install manually via shell)"
    fi

    log_ok "Sandbox ready"
}

cmd_up() {
    log_header "Claude Code Sandbox - Full Startup"

    # Trap Ctrl+C so the user can bail out cleanly at any stage
    trap '_up_cleanup' INT TERM

    # Step 1: Build if image doesn't exist
    if ! docker image inspect "${IMAGE_NAME}" &>/dev/null; then
        log_info "Image not found, building..."
        cmd_build
        echo ""
    else
        log_ok "Image exists: ${IMAGE_NAME}"
    fi

    # Step 2: Start container if not running
    if ! is_running; then
        cmd_start
        echo ""
    else
        log_ok "Container already running: ${CONTAINER_NAME}"
    fi

    # Step 3: Launch Claude Code (interactive, user can Ctrl+C to exit)
    echo ""
    log_info "Launching Claude Code inside sandbox..."
    log_info "Press Ctrl+C or type /exit to return to your Mac terminal"
    echo ""

    # Remove trap before exec so Ctrl+C goes to Claude Code, not our handler
    trap - INT TERM

    docker exec -it -w "${PROJECT_DIR}" "${CONTAINER_NAME}" \
        claude --dangerously-skip-permissions "$@"
    local exit_code=$?

    echo ""
    if [[ ${exit_code} -eq 0 ]]; then
        log_ok "Claude Code exited. Container still running."
    else
        log_info "Claude Code exited (code ${exit_code}). Container still running."
    fi
    log_info "Re-enter:  ./claude-container.sh up"
    log_info "Shell:     ./claude-container.sh shell"
    log_info "Stop:      ./claude-container.sh stop"
}

_up_cleanup() {
    echo ""
    log_info "Interrupted. Container still running in background."
    log_info "Re-enter:  ./claude-container.sh up"
    log_info "Stop:      ./claude-container.sh stop"
    exit 130
}

cmd_stop() {
    log_header "Stopping Claude Code Sandbox"
    if is_running; then
        docker stop "${CONTAINER_NAME}" >/dev/null
        log_ok "Container stopped"
    else
        log_warn "Container '${CONTAINER_NAME}' is not running"
    fi
}

cmd_destroy() {
    log_header "Destroying Claude Code Sandbox"
    docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true
    log_ok "Container removed"

    read -rp "Also remove image '${IMAGE_NAME}'? [y/N] " confirm
    if [[ "${confirm}" =~ ^[Yy]$ ]]; then
        docker rmi "${IMAGE_NAME}" 2>/dev/null || true
        log_ok "Image removed"
    fi
}

cmd_shell() {
    check_docker
    if ! is_running; then
        log_warn "Container not running. Starting..."
        cmd_start
    fi
    log_info "Entering sandbox shell (exit to return to host)"
    docker exec -it -w "${PROJECT_DIR}" "${CONTAINER_NAME}" zsh
}

cmd_claude() {
    check_docker
    if ! is_running; then
        log_warn "Container not running. Starting..."
        cmd_start
    fi

    local claude_args=("--dangerously-skip-permissions")

    # Pass through any additional arguments
    if [[ $# -gt 0 ]]; then
        claude_args+=("$@")
    fi

    log_info "Running: claude ${claude_args[*]}"
    docker exec -it -w "${PROJECT_DIR}" "${CONTAINER_NAME}" \
        claude "${claude_args[@]}"
}

cmd_worktree() {
    local branch="${1:-}"
    local worktree_dir="${2:-}"

    if [[ -z "${branch}" ]]; then
        log_fail "Usage: ./claude-container.sh worktree <branch> [directory]"
        echo ""
        echo "  Creates a git worktree inside the sandbox for parallel development."
        echo "  Sub-agents can operate on separate worktrees simultaneously."
        echo ""
        echo "  Examples:"
        echo "    ./claude-container.sh worktree feature/auth"
        echo "    ./claude-container.sh worktree fix/bug-123 ../daedalus-fix"
        echo ""
        echo "  List existing worktrees:"
        echo "    ./claude-container.sh worktree --list"
        exit 1
    fi

    check_docker
    if ! is_running; then
        log_warn "Container not running. Starting..."
        cmd_start
    fi

    if [[ "${branch}" == "--list" ]]; then
        docker exec -w "${PROJECT_DIR}" "${CONTAINER_NAME}" git worktree list
        return
    fi

    # Default worktree directory: sibling of project dir
    if [[ -z "${worktree_dir}" ]]; then
        worktree_dir="${PROJECT_DIR}/../$(basename "${PROJECT_DIR}")-${branch//\//-}"
    fi

    log_info "Creating worktree: ${branch} -> ${worktree_dir}"
    docker exec -w "${PROJECT_DIR}" "${CONTAINER_NAME}" \
        git worktree add "${worktree_dir}" -b "${branch}" 2>/dev/null || \
    docker exec -w "${PROJECT_DIR}" "${CONTAINER_NAME}" \
        git worktree add "${worktree_dir}" "${branch}"

    log_ok "Worktree created at ${worktree_dir}"
    log_info "To run Claude in this worktree:"
    echo "  docker exec -it -w '${worktree_dir}' ${CONTAINER_NAME} claude --dangerously-skip-permissions"
}

cmd_status() {
    log_header "Sandbox Status"

    if is_running; then
        log_ok "Container '${CONTAINER_NAME}' is running"
        echo ""
        docker inspect "${CONTAINER_NAME}" --format '
  Image:     {{.Config.Image}}
  Created:   {{.Created}}
  Status:    {{.State.Status}}
  PID:       {{.State.Pid}}
  Mounts:    {{range .Mounts}}
               {{.Source}} -> {{.Destination}} ({{.Type}}){{end}}'
        echo ""

        # Show key versions
        log_info "Versions:"
        echo -n "  Claude Code: " && docker exec "${CONTAINER_NAME}" claude --version 2>/dev/null || echo "N/A"
        echo -n "  Python:      " && docker exec "${CONTAINER_NAME}" python3.10 --version 2>/dev/null || echo "N/A"
        echo -n "  Node.js:     " && docker exec "${CONTAINER_NAME}" node --version 2>/dev/null || echo "N/A"
        echo -n "  Git:         " && docker exec "${CONTAINER_NAME}" git --version 2>/dev/null || echo "N/A"

        # Show worktrees
        echo ""
        log_info "Git worktrees:"
        docker exec -w "${PROJECT_DIR}" "${CONTAINER_NAME}" git worktree list 2>/dev/null || echo "  (none)"
    else
        log_warn "Container '${CONTAINER_NAME}' is not running"
        if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            log_info "Container exists but is stopped. Run: ./claude-container.sh start"
        else
            log_info "No container found. Run: ./claude-container.sh build && ./claude-container.sh start"
        fi
    fi
}

cmd_logs() {
    docker logs "${CONTAINER_NAME}" "$@" 2>&1
}

cmd_test() {
    log_header "Claude Code Sandbox Test Rig"
    local pass=0
    local fail=0
    local warn=0

    check_docker

    # --- Container health ---
    echo ""
    log_info "Container Health"

    if is_running; then
        log_ok "Container running"
        ((pass++))
    else
        log_fail "Container not running"
        ((fail++))
        log_info "Run: ./claude-container.sh start"
        echo ""
        echo "Results: ${pass} passed, ${fail} failed, ${warn} warnings"
        exit 1
    fi

    # --- Tool availability ---
    echo ""
    log_info "Tool Availability"

    if docker exec "${CONTAINER_NAME}" claude --version &>/dev/null; then
        local cv
        cv=$(docker exec "${CONTAINER_NAME}" claude --version 2>/dev/null)
        log_ok "Claude Code: ${cv}"
        ((pass++))
    else
        log_fail "Claude Code not found"
        ((fail++))
    fi

    if docker exec "${CONTAINER_NAME}" python3.10 --version &>/dev/null; then
        local pv
        pv=$(docker exec "${CONTAINER_NAME}" python3.10 --version 2>/dev/null)
        log_ok "Python: ${pv}"
        ((pass++))
    else
        log_fail "python3.10 not found"
        ((fail++))
    fi

    if docker exec "${CONTAINER_NAME}" node --version &>/dev/null; then
        log_ok "Node.js: $(docker exec "${CONTAINER_NAME}" node --version 2>/dev/null)"
        ((pass++))
    else
        log_fail "Node.js not found"
        ((fail++))
    fi

    if docker exec "${CONTAINER_NAME}" git --version &>/dev/null; then
        log_ok "Git available"
        ((pass++))
    else
        log_fail "Git not found"
        ((fail++))
    fi

    # Git worktree support
    if docker exec -w "${PROJECT_DIR}" "${CONTAINER_NAME}" git worktree list &>/dev/null; then
        log_ok "Git worktrees supported"
        ((pass++))
    else
        log_warn "Git worktrees not available"
        ((warn++))
    fi

    # --- Environment variables ---
    echo ""
    log_info "Environment Variables"

    if docker exec "${CONTAINER_NAME}" bash -c '[[ -n "$OPENROUTER_API_KEY" ]]' 2>/dev/null; then
        local key_len
        key_len=$(docker exec "${CONTAINER_NAME}" bash -c 'echo ${#OPENROUTER_API_KEY}' 2>/dev/null)
        log_ok "OPENROUTER_API_KEY set (${key_len} chars)"
        ((pass++))
    else
        log_fail "OPENROUTER_API_KEY not set"
        ((fail++))
        log_info "Ensure .env exists with OPENROUTER_API_KEY or set it in your environment"
    fi

    if docker exec "${CONTAINER_NAME}" bash -c '[[ -n "$ANTHROPIC_API_KEY" ]]' 2>/dev/null; then
        log_ok "ANTHROPIC_API_KEY set"
        ((pass++))
    else
        log_warn "ANTHROPIC_API_KEY not set (Claude Code may prompt for auth)"
        ((warn++))
    fi

    if docker exec "${CONTAINER_NAME}" bash -c '[[ "$CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" == "1" ]]' 2>/dev/null; then
        log_ok "Agent teams enabled"
        ((pass++))
    else
        log_warn "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS not set"
        ((warn++))
    fi

    # --- Workspace ---
    echo ""
    log_info "Workspace"

    if docker exec "${CONTAINER_NAME}" test -f "${PROJECT_DIR}/pyproject.toml" 2>/dev/null; then
        log_ok "Project mounted at ${PROJECT_DIR}"
        ((pass++))
    else
        log_fail "Project not mounted at ${PROJECT_DIR}"
        ((fail++))
    fi

    if docker exec "${CONTAINER_NAME}" test -f "${PROJECT_DIR}/run.sh" 2>/dev/null; then
        log_ok "run.sh accessible"
        ((pass++))
    else
        log_fail "run.sh not found"
        ((fail++))
    fi

    # --- Claude Code settings ---
    echo ""
    log_info "Claude Code Settings"

    if docker exec "${CONTAINER_NAME}" test -f /home/claude/.claude/settings.json 2>/dev/null; then
        log_ok "Global settings.json mounted"
        ((pass++))
    else
        log_warn "Global settings.json not found"
        ((warn++))
    fi

    if docker exec "${CONTAINER_NAME}" test -d "${PROJECT_DIR}/.claude" 2>/dev/null; then
        log_ok "Project .claude/ directory present"
        ((pass++))
    else
        log_warn "Project .claude/ directory not found"
        ((warn++))
    fi

    # --- Network connectivity ---
    echo ""
    log_info "Network Connectivity"

    if [[ "${NO_FIREWALL}" == "true" ]]; then
        log_warn "Firewall disabled, skipping network tests"
        ((warn++))
    else
        # Should be ALLOWED: OpenRouter API
        if docker exec "${CONTAINER_NAME}" curl --connect-timeout 5 -sf -o /dev/null https://openrouter.ai/api/v1/models 2>/dev/null; then
            log_ok "OpenRouter API reachable"
            ((pass++))
        else
            log_fail "OpenRouter API unreachable (check firewall)"
            ((fail++))
        fi

        # Should be ALLOWED: Anthropic API (Claude search goes through here)
        if docker exec "${CONTAINER_NAME}" curl --connect-timeout 5 -sf -o /dev/null https://api.anthropic.com 2>/dev/null; then
            log_ok "Anthropic API reachable (enables Claude search)"
            ((pass++))
        else
            # Anthropic API returns non-2xx without auth, but connection should work
            if docker exec "${CONTAINER_NAME}" curl --connect-timeout 5 -s https://api.anthropic.com 2>/dev/null | grep -qi "anthropic\|error\|api" 2>/dev/null; then
                log_ok "Anthropic API reachable (enables Claude search)"
                ((pass++))
            else
                log_warn "Anthropic API may be unreachable"
                ((warn++))
            fi
        fi

        # Should be BLOCKED: general internet
        if docker exec "${CONTAINER_NAME}" curl --connect-timeout 5 -sf https://example.com 2>/dev/null; then
            log_fail "example.com reachable (firewall not working)"
            ((fail++))
        else
            log_ok "General internet blocked (firewall active)"
            ((pass++))
        fi

        # Should be ALLOWED: PyPI (for pip install)
        if docker exec "${CONTAINER_NAME}" curl --connect-timeout 5 -sf -o /dev/null https://pypi.org/simple/ 2>/dev/null; then
            log_ok "PyPI reachable (pip install works)"
            ((pass++))
        else
            log_warn "PyPI may be unreachable"
            ((warn++))
        fi
    fi

    # --- OpenRouter API key validation ---
    echo ""
    log_info "API Connectivity"

    if docker exec "${CONTAINER_NAME}" bash -c '[[ -n "$OPENROUTER_API_KEY" ]]' 2>/dev/null; then
        local http_code
        http_code=$(docker exec "${CONTAINER_NAME}" bash -c \
            'curl -sf -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/models' 2>/dev/null || echo "000")
        if [[ "${http_code}" == "200" ]]; then
            log_ok "OpenRouter API key valid (HTTP 200)"
            ((pass++))
        elif [[ "${http_code}" == "401" || "${http_code}" == "403" ]]; then
            log_fail "OpenRouter API key rejected (HTTP ${http_code})"
            ((fail++))
        elif [[ "${http_code}" == "000" ]]; then
            log_warn "OpenRouter API connection failed"
            ((warn++))
        else
            log_warn "OpenRouter API responded with HTTP ${http_code}"
            ((warn++))
        fi
    else
        log_warn "Skipping API key validation (OPENROUTER_API_KEY not set)"
        ((warn++))
    fi

    # --- Summary ---
    echo ""
    log_header "Test Results"
    echo -e "  ${GREEN}Passed:${NC}   ${pass}"
    echo -e "  ${RED}Failed:${NC}   ${fail}"
    echo -e "  ${YELLOW}Warnings:${NC} ${warn}"
    echo ""

    if [[ ${fail} -eq 0 ]]; then
        log_ok "Sandbox is ready. Run: ./claude-container.sh claude"
    else
        log_fail "${fail} test(s) failed. Fix issues above, then re-run: ./claude-container.sh test"
        exit 1
    fi
}

# ============================================================================
# HELP
# ============================================================================

show_help() {
    cat << 'EOF'
claude-container.sh - Containerized Claude Code Sandbox

Based on Anthropic's official devcontainer pattern with network isolation.
https://github.com/anthropics/claude-code/blob/main/.devcontainer/

COMMANDS:
    up [ARGS...]             Build + start + launch Claude Code (one command)
    build                    Build sandbox Docker image
    start                    Start sandbox container
    claude [ARGS...]         Run Claude Code with --dangerously-skip-permissions
    shell                    Interactive shell inside sandbox
    test                     Run readiness + connectivity test rig
    worktree <branch> [dir]  Create git worktree for parallel work
    worktree --list          List existing worktrees
    stop                     Stop sandbox container
    status                   Show sandbox health and versions
    logs [-f]                Container logs
    destroy                  Remove container and optionally image

QUICK START:
    ./claude-container.sh up             # Build + start + launch (all-in-one)

  Or step by step:
    ./claude-container.sh build          # One-time: build image
    ./claude-container.sh start          # Start sandbox
    ./claude-container.sh test           # Verify everything works
    ./claude-container.sh claude         # Launch Claude Code (autonomous)

PARALLEL AGENTS WITH WORKTREES:
    ./claude-container.sh worktree feature/new-mechanism
    ./claude-container.sh claude -p "implement M20" --workdir ../daedalus-feature-new-mechanism

ENVIRONMENT VARIABLES:
    CLAUDE_CONTAINER_NAME    Container name        (default: claude-daedalus)
    CLAUDE_IMAGE_NAME        Image name            (default: claude-daedalus-sandbox)
    CLAUDE_CODE_VERSION      Claude Code version   (default: latest)
    CLAUDE_EXTRA_DOMAINS     Extra allowed domains (space-separated)
    CLAUDE_NO_FIREWALL       Skip firewall setup   (set to "true")

NETWORK POLICY (default-deny egress, allowlisted):
    Allowed:
      - api.anthropic.com        Claude API + web search
      - openrouter.ai            LLM API calls (OPENROUTER_API_KEY)
      - pypi.org                 Python packages
      - registry.npmjs.org       npm packages
      - github.com               Git operations
      - statsig.anthropic.com    Claude Code telemetry
    Blocked:
      - All other outbound traffic

REQUIREMENTS:
    - Docker Desktop for macOS (https://www.docker.com/products/docker-desktop/)
    - .env file with OPENROUTER_API_KEY (or set in environment)
    - Optional: ANTHROPIC_API_KEY for Claude Code authentication
EOF
}

# ============================================================================
# MAIN DISPATCH
# ============================================================================

main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi

    local cmd="$1"
    shift

    case "${cmd}" in
        up)             cmd_up "$@" ;;
        build)          cmd_build "$@" ;;
        start)          cmd_start "$@" ;;
        stop)           cmd_stop "$@" ;;
        destroy)        cmd_destroy "$@" ;;
        shell|sh)       cmd_shell "$@" ;;
        claude|run)     cmd_claude "$@" ;;
        worktree|wt)    cmd_worktree "$@" ;;
        status)         cmd_status "$@" ;;
        test|check)     cmd_test "$@" ;;
        logs)           cmd_logs "$@" ;;
        -h|--help|help) show_help ;;
        *)
            log_fail "Unknown command: ${cmd}"
            echo "Run './claude-container.sh help' for usage."
            exit 1
            ;;
    esac
}

main "$@"
