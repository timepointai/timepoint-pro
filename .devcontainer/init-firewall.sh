#!/bin/bash
# Timepoint Daedalus - Network Firewall for Claude Code Sandbox
# Based on Anthropic's official init-firewall.sh:
# https://github.com/anthropics/claude-code/blob/main/.devcontainer/init-firewall.sh
#
# Default-deny egress policy with allowlist for:
#   - OpenRouter API (LLM calls)
#   - Anthropic API (Claude Code + web search)
#   - Python/npm package managers
#   - GitHub (git operations)
#   - Claude Code telemetry
#
# Additional domains can be passed via EXTRA_ALLOWED_DOMAINS env var
# (space-separated list).

set -euo pipefail
IFS=$'\n\t'

echo "=== Initializing network firewall ==="

# 1. Preserve Docker DNS rules before flushing
DOCKER_DNS_RULES=$(iptables-save -t nat | grep "127\.0\.0\.11" || true)

# Flush all existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
ipset destroy allowed-domains 2>/dev/null || true

# 2. Restore Docker internal DNS
if [ -n "$DOCKER_DNS_RULES" ]; then
    echo "Restoring Docker DNS rules..."
    iptables -t nat -N DOCKER_OUTPUT 2>/dev/null || true
    iptables -t nat -N DOCKER_POSTROUTING 2>/dev/null || true
    echo "$DOCKER_DNS_RULES" | xargs -L 1 iptables -t nat
else
    echo "No Docker DNS rules to restore"
fi

# 3. Allow DNS, SSH, and localhost before restrictions
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A INPUT -p udp --sport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# 4. Create ipset with CIDR support
ipset create allowed-domains hash:net

# 5. Fetch and add GitHub IP ranges
echo "Fetching GitHub IP ranges..."
gh_ranges=$(curl -s https://api.github.com/meta)
if [ -z "$gh_ranges" ]; then
    echo "WARNING: Failed to fetch GitHub IP ranges, continuing..."
else
    if echo "$gh_ranges" | jq -e '.web and .api and .git' >/dev/null 2>&1; then
        echo "Processing GitHub IPs..."
        while read -r cidr; do
            if [[ "$cidr" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
                ipset add allowed-domains "$cidr" 2>/dev/null || true
            fi
        done < <(echo "$gh_ranges" | jq -r '(.web + .api + .git)[]' | aggregate -q 2>/dev/null || echo "$gh_ranges" | jq -r '(.web + .api + .git)[]')
    fi
fi

# 6. Resolve and add allowed domains
# Core: Anthropic API (Claude Code itself + web search)
# Core: OpenRouter API (LLM calls for this project)
# Packages: npm, PyPI (dependency installation)
# Telemetry: Anthropic analytics (required by Claude Code)
ALLOWED_DOMAINS=(
    "api.anthropic.com"
    "anthropic.com"
    "sentry.io"
    "statsig.anthropic.com"
    "statsig.com"
    "openrouter.ai"
    "api.openrouter.ai"
    "registry.npmjs.org"
    "pypi.org"
    "files.pythonhosted.org"
    "upload.pypi.org"
)

# Add extra domains from environment variable (space-separated)
if [ -n "${EXTRA_ALLOWED_DOMAINS:-}" ]; then
    for domain in $EXTRA_ALLOWED_DOMAINS; do
        ALLOWED_DOMAINS+=("$domain")
    done
fi

for domain in "${ALLOWED_DOMAINS[@]}"; do
    echo "Resolving $domain..."
    ips=$(dig +noall +answer A "$domain" 2>/dev/null | awk '$4 == "A" {print $5}')
    if [ -z "$ips" ]; then
        echo "WARNING: Failed to resolve $domain, skipping..."
        continue
    fi
    while read -r ip; do
        if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            echo "  Adding $ip ($domain)"
            ipset add allowed-domains "$ip" 2>/dev/null || true
        fi
    done < <(echo "$ips")
done

# 7. Allow host network (Docker bridge)
HOST_IP=$(ip route | grep default | cut -d" " -f3)
if [ -n "$HOST_IP" ]; then
    HOST_NETWORK=$(echo "$HOST_IP" | sed "s/\.[0-9]*$/.0\/24/")
    echo "Host network: $HOST_NETWORK"
    iptables -A INPUT -s "$HOST_NETWORK" -j ACCEPT
    iptables -A OUTPUT -d "$HOST_NETWORK" -j ACCEPT
else
    echo "WARNING: Failed to detect host IP"
fi

# 8. Set default policies to DROP
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow only traffic to allowlisted IPs
iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT

# Reject everything else with immediate feedback
iptables -A OUTPUT -j REJECT --reject-with icmp-admin-prohibited

echo "=== Firewall configuration complete ==="

# 9. Verification
echo "Verifying network rules..."

PASS=true

# Should be blocked
if curl --connect-timeout 5 -s https://example.com >/dev/null 2>&1; then
    echo "FAIL: example.com reachable (should be blocked)"
    PASS=false
else
    echo "PASS: example.com blocked"
fi

# Should be allowed: Anthropic API
if curl --connect-timeout 5 -s https://api.anthropic.com >/dev/null 2>&1; then
    echo "PASS: api.anthropic.com reachable"
else
    echo "WARN: api.anthropic.com unreachable (may need DNS retry)"
fi

# Should be allowed: OpenRouter API
if curl --connect-timeout 5 -s -o /dev/null -w "%{http_code}" https://openrouter.ai/api/v1/models 2>/dev/null | grep -q "^[2345]"; then
    echo "PASS: openrouter.ai reachable"
else
    echo "WARN: openrouter.ai unreachable (may need DNS retry)"
fi

if [ "$PASS" = true ]; then
    echo "=== Firewall verification passed ==="
else
    echo "=== Firewall verification had warnings ==="
fi
