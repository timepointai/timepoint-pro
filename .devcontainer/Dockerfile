# Timepoint Pro - Claude Code Sandbox Container
# Based on Anthropic's official devcontainer pattern:
# https://github.com/anthropics/claude-code/blob/main/.devcontainer/Dockerfile
#
# Uses python:3.10 base (project requirement) with Node.js 20 added for Claude Code.

FROM python:3.10-bookworm

ARG TZ
ENV TZ="${TZ:-America/Los_Angeles}"

ARG CLAUDE_CODE_VERSION=latest
ARG HOST_UID=1000
ARG HOST_GID=1000

# Install system packages: dev tools, firewall, and Claude Code dependencies
# Matches Anthropic's official list plus Python build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
  less \
  git \
  procps \
  sudo \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  aggregate \
  jq \
  nano \
  vim \
  curl \
  wget \
  build-essential \
  libffi-dev \
  libsqlite3-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && apt-get install -y gh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create claude user matching host UID/GID for bind mount compatibility
# Note: On macOS the host GID (20=staff) may collide with an existing Debian group (20=dialout),
# so we use numeric UID:GID for chown instead of claude:claude.
RUN groupadd -g ${HOST_GID} claude 2>/dev/null || true && \
    useradd -m -u ${HOST_UID} -g ${HOST_GID} -s /bin/zsh claude 2>/dev/null || true && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/claude && \
    chmod 0440 /etc/sudoers.d/claude

# Ensure npm global dir is accessible
RUN mkdir -p /usr/local/share/npm-global && \
    chown -R ${HOST_UID}:${HOST_GID} /usr/local/share/npm-global

# Persist shell history
RUN mkdir -p /commandhistory && \
    touch /commandhistory/.bash_history && \
    chown -R ${HOST_UID}:${HOST_GID} /commandhistory

ENV DEVCONTAINER=true

# Install Claude Code (as root, globally)
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

# Install Poetry for Python dependency management
RUN pip install --no-cache-dir poetry

# Install git-delta for better diffs
ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
    wget -q "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
    dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
    rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Copy and configure firewall script
COPY init-firewall.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/init-firewall.sh && \
    echo "claude ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/claude-firewall && \
    chmod 0440 /etc/sudoers.d/claude-firewall

# Switch to non-root user
USER claude

# Set shell defaults
ENV SHELL=/bin/zsh
ENV EDITOR=nano
ENV VISUAL=nano
ENV PROMPT_COMMAND='history -a'
ENV HISTFILE=/commandhistory/.bash_history

# Ensure python3.10 symlink exists (python:3.10 image provides /usr/local/bin/python3)
RUN if [ ! -f /usr/local/bin/python3.10 ]; then \
      sudo ln -sf /usr/local/bin/python3 /usr/local/bin/python3.10; \
    fi

# Default working directory (overridden at runtime to match host path)
WORKDIR /workspace

# Health check: verify Claude Code and Python are available
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD claude --version > /dev/null 2>&1 && python3.10 --version > /dev/null 2>&1
