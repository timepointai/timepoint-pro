# Timepoint Simulation Monitor

Real-time monitoring and LLM-powered explanation system for `run_all_mechanism_tests.py` simulations.

## Overview

The Simulation Monitor provides:
1. **Live Stream Parsing**: Captures and parses subprocess output in real-time
2. **Deep State Inspection**: Queries database and narrative files for simulation details
3. **LLM Explanations**: Sends periodic updates to a small LLM for natural language summaries
4. **Flexible Display**: Show raw logs, LLM summaries, or both

## Quick Start

### Basic Usage (Both Raw + LLM)
```bash
python3.10 -m monitoring.monitor_runner -- \
  python3.10 run_all_mechanism_tests.py --quick
```

### Only LLM Summaries (No Raw Logs)
```bash
python3.10 -m monitoring.monitor_runner --mode llm -- \
  python3.10 run_all_mechanism_tests.py --timepoint-forward
```

### Only Raw Logs (No LLM)
```bash
python3.10 -m monitoring.monitor_runner --mode raw --no-db-inspection -- \
  python3.10 run_all_mechanism_tests.py --portal-timepoint-all
```

### Custom Update Interval (2 minutes instead of 5)
```bash
python3.10 -m monitoring.monitor_runner --interval 120 -- \
  python3.10 run_all_mechanism_tests.py --full
```

### Use Better LLM Model
```bash
python3.10 -m monitoring.monitor_runner \
  --llm-model meta-llama/llama-3.1-70b-instruct \
  --max-output-tokens 300 -- \
  python3.10 run_all_mechanism_tests.py --timepoint-all
```

### Enable Interactive Chat
```bash
python3.10 -m monitoring.monitor_runner --enable-chat -- \
  python3.10 run_all_mechanism_tests.py --quick
```
Then type questions anytime (e.g., "what are the errors?", "explain the current simulation")

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--mode` | `both` | Display mode: `raw`, `llm`, or `both` |
| `--interval` | `300` | Seconds between LLM updates (5 minutes) |
| `--llm-model` | `meta-llama/llama-3.1-8b-instruct:free` | OpenRouter model to use |
| `--max-input-tokens` | `4000` | Max context to send to LLM |
| `--max-output-tokens` | `150` | Max tokens in LLM response |
| `--system-prompt-file` | `prompts/system_prompt.txt` | Custom system prompt path |
| `--no-db-inspection` | Off | Disable database queries (faster, less detail) |
| `--auto-confirm` | Off | Auto-confirm expensive runs (bypass prompts) |
| `--enable-chat` | Off | Enable interactive chat (ask questions anytime) |

## How It Works

### 1. Stream Parsing
The monitor captures stdout/stderr and uses regex patterns to detect:
- Template starts: `Running: template_name`
- Run IDs: `Run ID: run_20251101_...`
- Progress: `[3/15]`
- Stats: `Entities: 6, Timepoints: 12`
- Mechanisms: `Mechanisms: M1, M2, M7`
- Costs: `Cost: $0.08`
- Success/Failure: `✅ Success` / `❌ Failed`

### 2. Database Inspection
Queries `metadata/runs.db` and reads `datasets/{template_id}/narrative_*.json` for:
- Current simulation state
- Character information
- Timeline events
- Dialog count
- Mechanism usage

### 3. LLM Explanation
Every N seconds:
1. Accumulates recent logs
2. Queries database for current state
3. Builds large context (up to 4000 tokens)
4. Sends to LLM with system prompt
5. Requests concise 2-3 sentence summary (150 tokens)
6. Displays formatted explanation

### 4. Display
Console output shows:
```
================================================================================
TIMEPOINT MONITOR | 2026-01-11 14:35:00 | Mode: BOTH
Chat Mode: ENABLED (type messages and press Enter to ask questions)
================================================================================

[RAW] Running: showcase_board_meeting [3/15]
[RAW] Run ID: run_20260111_143500_abc123
[RAW] Entities: 6, Timepoints: 12
[RAW] Mechanisms: M1, M2, M3, M6, M7, M8, M11, M17
[RAW] Cost: $0.08

--- LLM SUMMARY (llama-3.1-8b @ 14:35:00) ---
Portal simulation 3/15 complete. Currently running showcase_board_meeting
(run_20260111_143500_abc123), which traces Timepoint's path from $1.2B
valuation in March 2030 backward to founding in April 2024 using M17 modal
temporal causality. The simulation has generated 12 timepoints across 6 entities
at $0.08 cost.

[RAW] ✅ Success: showcase_board_meeting
...
```

### 5. Interactive Chat (Optional)
When `--enable-chat` is enabled, you can type questions anytime:
```
what are the errors?

--- CHAT (14:36:15 2026-01-11) ---
Q: what are the errors?
A: The simulation encountered LLM generation failures when trying to create
dialog for some characters. It fell back to placeholder antecedents (generic
responses) for those interactions. This typically happens when the API rate
limits are hit or the model struggles with the complexity of the narrative
context. The simulation continues but with reduced dialog quality.

explain the current mechanisms

--- CHAT (14:37:22 2026-01-11) ---
Q: explain the current mechanisms
A: The current simulation is using 8 mechanisms: M1 (Entity Tracking), M2
(Temporal Sequencing), M3 (Causal Attribution), M6 (Natural Language Knowledge),
M7 (Emotional State), M8 (Decision Making), M11 (Dialog Synthesis), and M17
(Modal Temporal Causality). M17 is particularly important here as it enables
backward reasoning from the known endpoint (unicorn status) to the origin point.
```

## Architecture

### File Structure
```
monitoring/
  __init__.py
  config.py                  # Configuration dataclasses
  monitor_runner.py          # Main entry point
  stream_parser.py           # Log parsing with regex
  db_inspector.py            # Database/narrative queries
  llm_explainer.py           # LLM API integration
  prompts/
    system_prompt.txt        # Default system prompt (editable!)
    timepoint_context.txt    # Timepoint background info
```

### Key Classes

- **MonitorConfig**: Configuration settings (display mode, LLM model, intervals, etc.)
- **MonitorState**: Current monitoring state (templates completed, costs, log buffer)
- **StreamParser**: Parse subprocess output, extract events
- **DBInspector**: Query database and narrative files
- **LLMExplainer**: Generate explanations via OpenRouter API
- **SimulationMonitor**: Main orchestrator

## Customizing the System Prompt

The default system prompt is in `monitoring/prompts/system_prompt.txt`. Edit it to:
- Change LLM behavior
- Add domain-specific instructions
- Emphasize certain aspects (cost, narrative, mechanisms, etc.)

Example customization:
```bash
# Edit the prompt
nano monitoring/prompts/system_prompt.txt

# Use it
python3.10 -m monitoring.monitor_runner \
  python3.10 run_all_mechanism_tests.py --quick
```

## LLM Model Options

### Free Models (Good for Testing)

OpenRouter offers a rotating selection of free models. Use `--list-free-models` to see what's currently available:

```bash
python run_all_mechanism_tests.py --list-free-models
```

Common free models (availability may vary):
- `meta-llama/llama-3.3-70b-instruct:free` (high quality, 128K context)
- `qwen/qwen3-235b-a22b:free` (235B params, excellent quality)
- `google/gemini-2.0-flash-exp:free` (1M context, very fast)
- `meta-llama/llama-3.2-3b-instruct:free` (small & fast)

Default monitoring: `meta-llama/llama-3.1-8b-instruct:free`

### Paid Models (Higher Quality)
- `meta-llama/llama-3.1-70b-instruct` ($0.35/1M tokens)
- `meta-llama/llama-3.1-405b-instruct` ($5/1M tokens, highest quality)

Cost estimate for 1-hour run with 5-min intervals (12 updates):
- Free models: $0.00
- 70B model: ~$0.10
- 405B model: ~$2.00

## Requirements

- Python 3.10+
- `requests` library (for OpenRouter API)
- `OPENROUTER_API_KEY` environment variable (for LLM mode)

Install dependencies:
```bash
pip install requests
```

Set API key:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
# Or add to .env file
```

## Examples

### Monitor Long-Running Simulation
```bash
# All 35 Timepoint corporate templates (~4 hours)
python3.10 -m monitoring.monitor_runner --interval 600 -- \
  python3.10 run_all_mechanism_tests.py --timepoint-all
```

### Cost-Conscious Monitoring
```bash
# Longer intervals, no DB queries, free model
python3.10 -m monitoring.monitor_runner \
  --mode llm --interval 600 --no-db-inspection -- \
  python3.10 run_all_mechanism_tests.py --full
```

### Maximum Detail
```bash
# 70B model, frequent updates, full DB inspection
python3.10 -m monitoring.monitor_runner \
  --mode both \
  --llm-model meta-llama/llama-3.1-70b-instruct \
  --interval 180 \
  --max-output-tokens 300 -- \
  python3.10 run_all_mechanism_tests.py --portal-timepoint-all
```

## Troubleshooting

### "No LLM API key found"
Set `OPENROUTER_API_KEY` environment variable or use `--mode raw`

### "Database locked"
The simulation is writing to `metadata/runs.db`. DB inspection will retry automatically.

### High LLM Costs
- Increase `--interval` (600s = 10 min)
- Use `--no-db-inspection`
- Switch to free model: `--llm-model meta-llama/llama-3.1-8b-instruct:free`
- Reduce `--max-output-tokens`

### LLM Summaries Too Brief
- Increase `--max-output-tokens` (300-500)
- Edit `monitoring/prompts/system_prompt.txt` to request more detail
- Use a better model: `--llm-model meta-llama/llama-3.1-70b-instruct`

## Interactive Chat Feature

The `--enable-chat` flag enables a powerful interactive mode where you can ask questions about the simulation in real-time:

**Use Cases:**
- "what are the errors?" - Understand failures and issues
- "explain the current simulation" - Get detailed narrative context
- "which mechanisms are being used?" - Technical mechanism breakdown
- "what happened to the CEO?" - Query specific narrative events
- "how much has this cost so far?" - Budget tracking
- "summarize the last 5 minutes" - Quick catch-up

**How It Works:**
1. Chat listener thread monitors stdin for user input
2. When you type a question and press Enter, it captures recent logs + DB state
3. Sends combined context to LLM with your question
4. Displays formatted Q&A without interrupting the monitoring stream
5. Chat responses use 300 tokens (vs 150 for scheduled summaries) for more detail

**Tips:**
- Chat works alongside scheduled LLM summaries (use `--mode both`)
- Combine with `--auto-confirm` for fully unattended + chatty monitoring
- Questions are answered using the current simulation state + last 50 log lines
- More expensive models (`--llm-model meta-llama/llama-3.1-70b-instruct`) give better chat responses

## Future Enhancements

- JSON/Markdown output formats
- Save explanation history to file
- Webhook notifications on completion/errors
- Adaptive intervals (more frequent during active phases)
- Cost tracking and budgets
- Chat history export
