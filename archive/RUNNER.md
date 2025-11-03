# run.sh - Unified E2E Test Runner

**Document Type:** User Guide
**Status:** Active
**Created:** November 2, 2025
**Version:** 1.0

---

## Overview

`run.sh` is the unified test runner for Timepoint Daedalus that consolidates all E2E workflow execution patterns. It supports monitored/unmonitored modes, template selection, and full M1+M17 Adaptive Fidelity-Temporal Strategy integration.

**Replaces:**
- `temp-timepoint-corporate.sh`
- `temporary-ultra-all.sh`
- `test_monitor.sh`
- Direct invocations of `run_all_mechanism_tests.py`

---

## Quick Start

```bash
# Quick test (9 templates, ~$9-18, 18-27 min)
./run.sh quick

# Portal tests with monitoring
./run.sh --monitor portal-test

# Ultra mode with chat-enabled monitoring
./run.sh --monitor --chat ultra

# List all available modes
./run.sh --list
```

---

## Usage

```
./run.sh [OPTIONS] [MODE]
```

### Options

| Option | Description |
|--------|-------------|
| `--monitor` | Enable real-time monitoring with LLM analysis |
| `--chat` | Enable interactive chat in monitor (requires `--monitor`) |
| `--no-auto-confirm` | Disable auto-confirmation in monitor |
| `--interval SECONDS` | Monitor check interval (default: 300) |
| `--llm-model MODEL` | LLM model for monitor (default: meta-llama/llama-3.1-70b-instruct) |
| `--monitor-mode MODE` | Monitor mode: both\|snapshot\|compare (default: both) |
| `--list` | Show all available modes |
| `-h, --help` | Show help message |

### Modes

#### Basic Modes
- **quick**: Quick tests (9 templates, ~$9-18, 18-27 min)
- **full**: All quick + expensive tests (13 templates)

#### Timepoint Corporate
- **timepoint-forward**: Forward-mode corporate (15 templates, $15-30, 30-60 min)
- **timepoint-all**: ALL corporate templates (35 templates, $81-162, 156-243 min)

#### Portal (Backward Reasoning)
- **portal-test**: Standard portal (4 templates, $5-10, 10-15 min)
- **portal-simjudged-quick**: Quick simulation judging (4 templates, $10-20, 20-30 min)
- **portal-simjudged**: Standard simulation judging (4 templates, $15-30, 30-45 min)
- **portal-simjudged-thorough**: Thorough judging (4 templates, $25-50, 45-60 min)
- **portal-all**: ALL portal variants (16 templates, $55-110, 105-150 min)

#### Portal Timepoint (Real Founders)
- **portal-timepoint**: Standard with founders (5 templates, $6-12, 12-18 min)
- **portal-timepoint-simjudged-quick**: Quick judging (5 templates, $12-24, 24-36 min)
- **portal-timepoint-simjudged**: Standard judging (5 templates, $18-36, 36-54 min)
- **portal-timepoint-simjudged-thorough**: Thorough judging (5 templates, $30-60, 54-75 min)
- **portal-timepoint-all**: ALL portal timepoint (20 templates, $66-132, 126-183 min)

#### Ultra Mode
- **ultra**: Run EVERYTHING (64 templates, $176-352, 301-468 min)

---

## Examples

### Basic Usage

```bash
# Quick tests, no monitoring (9 templates, ~18-27 min)
./run.sh quick

# All quick + expensive tests (13 templates)
./run.sh full

# Everything! (64 templates, 5-8 hours)
./run.sh ultra
```

### Timepoint Corporate

```bash
# Corporate formation/growth (15 templates)
./run.sh timepoint-forward

# All corporate modes (35 templates)
./run.sh timepoint-all
```

### Portal (Backward Reasoning)

```bash
# Standard portal (4 templates, ~10-15 min)
./run.sh portal-test

# Portal + judging (4 templates, ~30-45 min)
./run.sh portal-simjudged

# All portal variants (16 templates)
./run.sh portal-all
```

### Portal + Timepoint (Real Founders)

```bash
# Standard (5 templates, ~12-18 min)
./run.sh portal-timepoint

# + judging (5 templates, ~36-54 min)
./run.sh portal-timepoint-simjudged

# + thorough (5 templates, ~54-75 min)
./run.sh portal-timepoint-simjudged-thorough

# All variants (20 templates)
./run.sh portal-timepoint-all
```

### Monitoring

```bash
# Real-time LLM analysis
./run.sh --monitor quick

# Monitor portal mode
./run.sh --monitor portal-test

# Monitor corporate mode
./run.sh --monitor timepoint-forward

# Monitor real founders
./run.sh --monitor portal-timepoint
```

### Interactive Chat

```bash
# Quick tests with chat
./run.sh --monitor --chat quick

# Portal + chat
./run.sh --monitor --chat portal-timepoint

# Ultra mode with chat
./run.sh --monitor --chat ultra
```

### Custom Monitor Settings

```bash
# Check every 60s
./run.sh --monitor --interval 60 quick

# Check every 10 min
./run.sh --monitor --interval 600 timepoint-forward

# Use Llama 405B for monitoring
./run.sh --monitor --llm-model meta-llama/llama-3.1-405b-instruct portal-test

# Snapshot only (no comparison)
./run.sh --monitor --monitor-mode snapshot quick

# Manual approval each check
./run.sh --monitor --no-auto-confirm portal-timepoint
```

### Advanced Combinations

```bash
# Portal timepoint with Llama 405B monitoring, chat, and high frequency
./run.sh --monitor --chat --interval 120 --llm-model meta-llama/llama-3.1-405b-instruct portal-timepoint

# Corporate mode with snapshot-only monitoring
./run.sh --monitor --monitor-mode snapshot --interval 300 timepoint-forward

# ALL corporate portal modes with ultra monitoring and chat (COMPREHENSIVE)
./run.sh --monitor --chat --interval 180 portal-timepoint-all

# Ultra mode with custom LLM and manual confirmation
./run.sh --monitor --chat --llm-model meta-llama/llama-3.1-405b-instruct \
         --no-auto-confirm --interval 600 ultra

# Timepoint corporate ultra: ALL templates with premium monitoring
./run.sh --monitor --chat --llm-model meta-llama/llama-3.1-405b-instruct \
         --interval 300 --monitor-mode both timepoint-all

# Corporate portal deep dive with Llama 405B (20 templates, monitored)
./run.sh --monitor --chat --llm-model meta-llama/llama-3.1-405b-instruct \
         --interval 240 portal-timepoint-all
```

### Quick Reference by Use Case

```bash
# Fast development testing
./run.sh quick

# Corporate template testing
./run.sh timepoint-forward

# Portal template testing
./run.sh portal-test

# Real founder simulations
./run.sh portal-timepoint

# Interactive debugging
./run.sh --monitor --chat quick

# Production validation
./run.sh --monitor ultra

# CI/CD quick smoke test
./run.sh quick

# Full system validation
./run.sh ultra

# Corporate portal deep dive (ALL 20 variants, monitored)
./run.sh --monitor --chat portal-timepoint-all

# Premium corporate analysis (35 templates with Llama 405B)
./run.sh --monitor --chat --llm-model meta-llama/llama-3.1-405b-instruct timepoint-all

# Comprehensive founder analysis (20 templates, ultra monitoring)
./run.sh --monitor --chat --llm-model meta-llama/llama-3.1-405b-instruct --interval 240 portal-timepoint-all
```

### Cost-Conscious Options

```bash
# Under $20
./run.sh quick              # $9-18
./run.sh portal-test        # $5-10
./run.sh portal-timepoint   # $6-12

# Under $50
./run.sh timepoint-forward  # $15-30
./run.sh portal-all         # $55-110 (exceeds $50, but close)

# Under $100
./run.sh timepoint-all            # $81-162 (may exceed)
./run.sh portal-timepoint-all     # $66-132 (may exceed)

# Full suite
./run.sh ultra              # $176-352
```

---

## Monitoring Features

### Real-Time Analysis

When `--monitor` is enabled, the runner provides:

1. **Periodic Snapshots**: LLM-powered analysis of simulation state every N seconds
2. **Progress Tracking**: Real-time entity/timepoint/cost metrics
3. **Mechanism Detection**: Automatic detection of active mechanisms
4. **Comparison Mode**: Compare snapshots to track progress

### Interactive Chat

With `--chat` enabled:

```bash
./run.sh --monitor --chat portal-test
```

During execution, you can:
- Ask questions about simulation state
- Query specific entities or timepoints
- Request mechanism analysis
- Get cost/token projections

Example chat queries:
- "What entities have been created?"
- "Show me the latest timepoint"
- "What mechanisms are being used?"
- "Estimate remaining cost"

---

## M1+M17 Integration

All modes automatically use **M1+M17 Adaptive Fidelity-Temporal Strategy**:

- **Fidelity Planning**: Hybrid mode with adaptive resolution
- **Token Budgets**: Soft guidance with configurable limits
- **Fidelity Templates**: Balanced, minimalist, dramatic, max_quality, portal_pivots
- **Metrics Tracking**: Real-time fidelity distribution, budget compliance, efficiency scores

Monitoring displays M1+M17 metrics:
```
Fidelity Distribution (M1):
  DIALOG: 2 entities
  SCENE: 3 entities
  TENSOR_ONLY: 1 entities

Token Budget Compliance: ✓ 87.3%
Fidelity Efficiency: 0.000168 quality/token
```

---

## Environment Setup

### Required

Create `.env` file with API keys:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
OXEN_API_KEY=SFMyNTY...
```

### Optional

Configure monitoring in `.env`:

```bash
# Monitor settings (optional overrides)
MONITOR_INTERVAL=300
MONITOR_LLM_MODEL=meta-llama/llama-3.1-70b-instruct
MONITOR_MAX_OUTPUT_TOKENS=300
```

---

## Output

### Unmonitored

Standard console output showing:
- Template execution progress
- Entity/timepoint creation
- Cost tracking
- Success/failure status

### Monitored

Enhanced output with:
- Periodic LLM analysis
- Formatted snapshots
- Progress comparison
- Interactive chat (if enabled)

### Results

All modes generate:
- **Database**: `metadata/runs.db` (with M1+M17 metrics)
- **Narrative Exports**: `datasets/<template>/narrative_*.{json,md,pdf}`
- **Training Data**: `datasets/<template>/training_*.jsonl`
- **Oxen Uploads**: If `OXEN_API_KEY` is set

---

## Troubleshooting

### Missing .env

```bash
❌ No .env file found
ℹ️  Create .env with OPENROUTER_API_KEY and OXEN_API_KEY
```

**Fix:** Create `.env` file with required API keys.

### Unknown Mode

```bash
❌ Unknown mode: xyz
ℹ️  Run './run.sh --list' to see all available modes
```

**Fix:** Check available modes with `./run.sh --list`.

### Monitor Fails to Start

```bash
❌ Monitor initialization failed
```

**Fix:** Check that `monitoring/monitor_runner.py` exists and is executable.

### Chat Not Working

```bash
⚠️  Chat requires --monitor flag
```

**Fix:** Add `--monitor` before `--chat`.

---

## Migration from Old Scripts

### temp-timepoint-corporate.sh

**Old:**
```bash
python3.10 -m monitoring.monitor_runner --mode both --enable-chat \
  --auto-confirm --interval 300 \
  -- python3.10 run_all_mechanism_tests.py --portal-timepoint-all
```

**New:**
```bash
./run.sh --monitor --chat portal-timepoint-all
```

### temporary-ultra-all.sh

**Old:**
```bash
source .env && python3.10 run_all_mechanism_tests.py --ultra-all
```

**New:**
```bash
./run.sh ultra
```

### test_monitor.sh

**Old:**
```bash
./test_monitor.sh  # Mock test script
```

**New:**
```bash
./run.sh --monitor quick  # Real monitoring
```

---

## Performance

### Quick Mode Comparison

| Aspect | Unmonitored | Monitored |
|--------|-------------|-----------|
| Runtime | 18-27 min | 18-27 min (+ monitor overhead ~5%) |
| Output | Basic console | Rich LLM analysis |
| Cost | $9-18 | $9-18 (+ monitor LLM calls ~$0.50) |
| Interactivity | None | Full chat |

### Ultra Mode

- **Templates**: 64
- **Runtime**: 301-468 minutes (5-8 hours)
- **Cost**: $176-352
- **Monitor Overhead**: ~10-15 minutes total
- **Monitor Cost**: ~$5-10 total

---

## Advanced Configuration

### Custom Monitor Model

```bash
# Use Llama 405B for monitoring (higher quality, higher cost)
./run.sh --monitor --llm-model meta-llama/llama-3.1-405b-instruct portal-test

# Use faster/cheaper model
./run.sh --monitor --llm-model meta-llama/llama-3-8b-instruct quick
```

### High-Frequency Monitoring

```bash
# Check every 60 seconds (for short tests)
./run.sh --monitor --interval 60 quick

# Check every 10 minutes (for long tests)
./run.sh --monitor --interval 600 ultra
```

### Snapshot-Only Mode

```bash
# No comparison, just periodic snapshots
./run.sh --monitor --monitor-mode snapshot portal-test
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  quick-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Create .env
        run: |
          echo "OPENROUTER_API_KEY=${{ secrets.OPENROUTER_API_KEY }}" > .env
          echo "OXEN_API_KEY=${{ secrets.OXEN_API_KEY }}" >> .env
      - name: Run quick tests
        run: ./run.sh quick
```

---

## Related Documentation

- **[README.md](README.md)**: Main project documentation
- **[PLAN.md](PLAN.md)**: Development roadmap
- **[MECHANICS.md](MECHANICS.md)**: M1+M17 technical specification
- **[MIGRATION.md](MIGRATION.md)**: Database v2 migration guide

---

## Changelog

### Version 1.0 (November 2, 2025)

- Initial release
- Consolidates all test execution patterns
- Supports monitored/unmonitored modes
- Full M1+M17 integration
- Interactive chat support
- Replaces 3 temporary scripts

---

**Questions?** Run `./run.sh --help` or check [MECHANICS.md](MECHANICS.md) for M1+M17 details.
