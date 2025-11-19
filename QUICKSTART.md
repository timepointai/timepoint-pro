# Quick Start: Generate Real Simulations from Natural Language

## TL;DR - One Command

```bash
python demo_orchestrator.py --event "emergency board meeting about a merger"
```

That's it! Just describe what you want to simulate in plain English.

## Setup (One Time)

1. **Get an API key** from https://openrouter.ai/keys

2. **Add to .env file**:
```bash
OPENROUTER_API_KEY=your_key_here
```

3. **Done!** You're ready to generate simulations.

## Examples

### Basic Usage
```bash
# Emergency board meeting
python demo_orchestrator.py --event "emergency board meeting where 4 executives debate whether to accept acquisition offer"

# Historical event
python demo_orchestrator.py --event "apollo 13 crisis - the moment they discover the oxygen tank explosion"

# Fiction scenario
python demo_orchestrator.py --event "detective interrogates 3 witnesses about a murder"
```

### With Custom Settings
```bash
# More entities and timepoints
python demo_orchestrator.py --event "constitutional convention" --entities 8 --timepoints 5

# Different temporal mode (narrative-focused)
python demo_orchestrator.py --event "shakespearean tragedy" --mode directorial

# Branching timeline (what-if scenarios)
python demo_orchestrator.py --event "cuban missile crisis decision point" --mode branching
```

### Test Without Cost
```bash
# Dry run mode - no API calls, uses mock data
python demo_orchestrator.py --event "test scenario" --dry-run
```

## What You Get

Each simulation generates:

✅ **Entities** - Characters with:
- Unique personalities
- Knowledge states
- Roles and relationships
- Cognitive tensors

✅ **Timepoints** - Causal sequence of events with:
- Event descriptions
- Timestamps
- Entity presence tracking
- Causal links (what caused what)

✅ **Relationships** - Network graph of:
- How entities relate to each other
- Social connections
- Information flow

✅ **Knowledge Flow** - Exposure events showing:
- What each entity knows
- When they learned it
- How confident they are

## Output Files

Results are saved to `output/simulations/`:

- `summary_TIMESTAMP.json` - Full simulation summary
- `entities_TIMESTAMP.jsonl` - Detailed entity data
- `sim_TIMESTAMP.db` - SQLite database with everything

## Cost

Typical runs cost **$0.05-0.20** depending on:
- Number of entities (1-20)
- Number of timepoints (1-10)
- Temporal mode complexity

The script will show estimated cost and ask for confirmation before running.

## Temporal Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `pearl` | Standard causality, no time paradoxes | Default, most realistic |
| `directorial` | Narrative-focused with dramatic tension | Stories, character arcs |
| `cyclical` | Allows prophecy and time loops | Sci-fi, mystical scenarios |
| `branching` | Counterfactual what-if scenarios | Decision analysis, alternate history |

## Advanced Options

```bash
# All options
python demo_orchestrator.py \
  --event "your description" \
  --entities 5 \              # Max entities (1-20, default: 4)
  --timepoints 4 \            # Max timepoints (1-10, default: 3)
  --mode directorial \        # Temporal mode (default: pearl)
  --dry-run                   # Test without API costs

# Help
python demo_orchestrator.py --help
```

## Tips for Writing Good Prompts

**Good prompts are specific:**
- ✅ "Emergency board meeting where CFO reveals bankruptcy, 4 executives debate 3 options"
- ❌ "Meeting"

**Include context:**
- ✅ "Apollo 13 crew discovers oxygen tank explosion, must decide how to return to Earth"
- ❌ "Space problem"

**Specify key characters:**
- ✅ "Detective interrogates CEO, CFO, and janitor about missing money"
- ❌ "Interrogation"

**Describe the tension:**
- ✅ "Founders fight over whether to take VC money or bootstrap, relationship at breaking point"
- ❌ "Business decision"

## Next Steps

After generating a simulation:

1. **Query the data**:
   ```bash
   python cli.py mode=interactive
   ```

2. **Generate training data**:
   ```bash
   python run_character_engine.py
   ```

3. **Run full E2E pipeline**:
   ```bash
   python run_complete_e2e_workflow.py
   ```

## Troubleshooting

**"OPENROUTER_API_KEY not set"**
→ Add your API key to `.env` file

**"LLM client in dry_run mode"**
→ Set `LLM_SERVICE_ENABLED=true` in `.env`

**Simulation takes too long**
→ Reduce `--entities` and `--timepoints`

**Costs too high**
→ Use `--dry-run` for testing, or reduce complexity

## Example Output

```
📋 Scene: Emergency Board Meeting - TechCorp Crisis

   1. sarah_chen
      Role: CEO
      Resolution: dialog
      Knowledge: 8 items
         Sample: Company has 6 weeks of runway remaining due to burn rate...
      Personality: optimistic, visionary, determined

   2. michael_rodriguez
      Role: CFO
      Knowledge: 12 items
         Sample: Q3 revenue projections missed by 40%, cash reserves critical...
      Personality: analytical, risk-averse, pragmatic

⏱️  Timepoints: 3

   1. crisis_discovery
      Event: CFO discovers company has 6 weeks of runway left
      Entities: 4
      Caused by: None (root)

   2. emergency_meeting
      Event: Board convenes to discuss options
      Entities: 4
      Caused by: crisis_discovery

🔗 Relationships: 6
   sarah_chen --[reports_to]--> james_thompson
   michael_rodriguez --[conflicts_with]--> lisa_park

💰 Cost: $0.12
   Time: 87.3s
```

---

**Ready to try?**

```bash
python demo_orchestrator.py --event "your natural language prompt here"
```
