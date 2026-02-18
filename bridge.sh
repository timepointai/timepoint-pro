#!/bin/bash
#
# bridge.sh - GitHub auth bridge for containerized Claude Code
#
# Enables git push from inside the Docker container by forwarding
# GitHub credentials from the host terminal.
#
# The container (claude-container.sh) has network access to github.com
# via the iptables allowlist, but no stored credentials. This script
# bridges that gap using a one-shot token injection.
#
# USAGE (from your Mac terminal, NOT inside the container):
#
#   # One-liner: inject your gh token and push
#   GH_TOKEN=$(gh auth token) docker exec -e GH_TOKEN claude-pro \
#       bash /Users/seanmcdonald/Documents/GitHub/timepoint-pro/bridge.sh
#
#   # Or if you have GH_TOKEN in .env, just:
#   docker exec claude-pro \
#       bash /Users/seanmcdonald/Documents/GitHub/timepoint-pro/bridge.sh
#
# USAGE (from inside the container, if GH_TOKEN is set):
#
#   bash bridge.sh
#
# The token is NEVER stored in git config or remote URLs — it's used
# only for the single push command, then discarded.

set -euo pipefail

# ---- Find token ----
TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"

if [[ -z "$TOKEN" ]]; then
    echo "ERROR: No GitHub token found."
    echo ""
    echo "From your Mac terminal, run:"
    echo "  GH_TOKEN=\$(gh auth token) docker exec -e GH_TOKEN claude-pro \\"
    echo "      bash $(pwd)/bridge.sh"
    echo ""
    echo "Or add GH_TOKEN=ghp_xxxxx to your .env and restart the container."
    exit 1
fi

# ---- Extract repo info ----
REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$REPO_URL" ]]; then
    echo "ERROR: No git remote 'origin' configured."
    exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
REPO_PATH=$(echo "$REPO_URL" | sed 's|https://github.com/||' | sed 's|\.git$||')

# ---- Status check ----
AHEAD=$(git rev-list --count "origin/${BRANCH}..HEAD" 2>/dev/null || echo "?")
echo "Repository: github.com/${REPO_PATH}"
echo "Branch:     ${BRANCH}"
echo "Commits:    ${AHEAD} ahead of origin/${BRANCH}"
echo ""

if [[ "$AHEAD" == "0" ]]; then
    echo "Nothing to push — branch is up to date."
    exit 0
fi

# ---- Push using one-shot token (never stored) ----
echo "Pushing ${AHEAD} commit(s)..."
git push "https://x-access-token:${TOKEN}@github.com/${REPO_PATH}.git" "${BRANCH}:${BRANCH}" 2>&1

echo ""
echo "Push complete."
git log --oneline -"${AHEAD}"
