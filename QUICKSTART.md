# Quick Start: Generate Real Simulations from Natural Language

## TL;DR - One Command

```bash
python run_all_mechanism_tests.py --nl "emergency board meeting about a merger"
```

That's it! Just describe what you want to simulate in plain English.

## Setup (One Time)

1. **Get an API key** from https://openrouter.ai/keys

2. **Add to .env file**:
```bash
OPENROUTER_API_KEY=your_key_here
```

3. **Load environment variables** (do this before running):
```bash
# Export all variables from .env
export $(cat .env | xargs)

# Or source the file directly
source .env

# Or set directly (must be ONE line, no breaks)
export OPENROUTER_API_KEY="your_key_here"
```

4. **Done!** You're ready to generate simulations.

**Important**: The API key must be on a **single line** with no line breaks. If you see "Illegal header value" errors, check that your key doesn't have embedded newlines.

## Examples

**Note**: All commands require environment variables to be loaded first (see Setup above).

### Natural Language Mode
```bash
# Emergency board meeting
python run_all_mechanism_tests.py --nl "emergency board meeting where 4 executives debate whether to accept acquisition offer"

# Historical event
python run_all_mechanism_tests.py --nl "apollo 13 crisis - the moment they discover the oxygen tank explosion"

# Fiction scenario
python run_all_mechanism_tests.py --nl "detective interrogates 3 witnesses about a murder"
```

### Template-Based Mode
```bash
# List all 13 verified templates
./run.sh list

# Run a single template
./run.sh run board_meeting
./run.sh run jefferson_dinner

# Run templates by category
./run.sh run --category showcase      # 10 showcase scenarios
./run.sh run --category convergence   # 3 convergence-optimized templates

# Run templates by tier (complexity)
./run.sh quick                    # Fast tests (~2-3 min each)
./run.sh standard                 # Moderate tests (~5-10 min)
./run.sh comprehensive            # Thorough tests (~15-30 min)
```

### Test Without Cost
```bash
# Free model mode - uses OpenRouter free tier ($0 cost)
python run_all_mechanism_tests.py --free --template board_meeting
```

## What You Get

Each simulation generates:

**Entities** - Characters with:
- Unique personalities
- Knowledge states
- Roles and relationships
- Cognitive tensors

**Timepoints** - Causal sequence of events with:
- Event descriptions
- Timestamps
- Entity presence tracking
- Causal links (what caused what)

**Relationships** - Network graph of:
- How entities relate to each other
- Social connections
- Information flow

**Knowledge Flow** - Exposure events showing:
- What each entity knows
- When they learned it
- How confident they are

## Output Files

Results are saved to `output/simulations/`:

- `summary_TIMESTAMP.json` - Full simulation summary
- `entities_TIMESTAMP.jsonl` - Detailed entity data
- `sim_TIMESTAMP.db` - SQLite database with everything

## Cost

Typical runs cost **$0.02-0.10** depending on:
- Number of entities (1-20)
- Number of timepoints (1-10)
- Temporal mode complexity

*Updated January 2026: Costs are ~10x lower than previous estimates due to efficient Llama 4 Scout pricing.*

### Free Mode ($0 cost)

Use OpenRouter's free tier models for zero-cost testing:

```bash
# Best quality free model (Qwen 235B, Llama 70B, etc.)
python run_all_mechanism_tests.py --free --template board_meeting

# Fastest free model (Gemini Flash, smaller Llama)
python run_all_mechanism_tests.py --free-fast --template board_meeting

# List currently available free models
python run_all_mechanism_tests.py --list-free-models
```

Note: Free models have more restrictive rate limits and availability may rotate.

## Temporal Modes

Each mode changes what "time" means and how the simulation validates consistency:

| Mode | Description | Use Case | Example Template |
|------|-------------|----------|------------------|
| `pearl` | Standard causality, no time paradoxes | Default, most realistic | `board_meeting` |
| `portal` | Backward reasoning from known outcomes | "How did we get here?" scenarios | (no verified templates) |
| `directorial` | Narrative-focused with dramatic tension | Stories, character arcs | `hound_shadow_directorial` |
| `cyclical` | Allows prophecy and time loops | Sci-fi, mystical, generational | (no verified templates) |
| `branching` | Counterfactual what-if scenarios | Decision analysis, alternate history | `vc_pitch_branching` |

### Choosing a Mode

**Use PEARL when:** You want realistic forward simulation. Causes precede effects. Knowledge flows forward. No magic, no paradoxes. This is the default for business scenarios, historical reconstruction, training data generation.

**Use PORTAL when:** You know the endpoint and want to discover paths there. "What decisions lead to a $1B exit?" "What events preceded this crisis?" Works backward from a fixed future, finding plausible routes from the present.

**Use DIRECTORIAL when:** Story matters more than strict realism. The system will organize events into dramatic structure (setup → rising action → climax → falling action → resolution), allocate more detail to dramatic moments, and permit narrative coincidences that strict causality would forbid.

**Use CYCLICAL when:** Time loops, generational patterns, or prophecy are structurally important. The system interprets what "cyclical" means for your scenario—Groundhog Day loops, dynasty sagas, economic boom-bust cycles. Prophecies become structural (must be fulfilled or subverted), not decorative.

**Use BRANCHING when:** You want parallel "what if" timelines. A single decision point spawns multiple futures, each internally consistent but diverging from the branch point. Good for strategy analysis and counterfactual reasoning.

### Mode-Specific Templates

```bash
# Directorial template (narrative structure)
./run.sh run hound_shadow_directorial  # Detective on foggy moors, directorial causality

# Branching templates (counterfactual timelines)
./run.sh run vc_pitch_branching        # VC pitch with counterfactual branching
./run.sh run vc_pitch_strategies       # Multiple negotiation strategy variants
```

## Advanced Options

```bash
# Natural language with parallel execution
python run_all_mechanism_tests.py --nl "your description" --parallel 4

# Run all templates in a category
./run.sh run --category showcase --parallel 6

# Filter by mechanism
./run.sh run --mechanism M1,M7,M11

# Skip LLM summary generation (faster, cheaper)
./run.sh quick --skip-summaries

# Help
./run.sh --help
```

## Tips for Writing Good Prompts

**Good prompts are specific:**
- "Emergency board meeting where CFO reveals bankruptcy, 4 executives debate 3 options"
- "Meeting" (too vague)

**Include context:**
- "Apollo 13 crew discovers oxygen tank explosion, must decide how to return to Earth"
- "Space problem" (too vague)

**Specify key characters:**
- "Detective interrogates CEO, CFO, and janitor about missing money"
- "Interrogation" (too vague)

**Describe the tension:**
- "Founders fight over whether to take VC money or bootstrap, relationship at breaking point"
- "Business decision" (too vague)

## Tensor Persistence API

Tensors can be stored, searched, and composed via the REST API:

```bash
# Start the API server
uvicorn api.main:app --reload

# Create a tensor (requires API key)
curl -X POST http://localhost:8000/tensors \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "ceo_alice",
    "category": "character",
    "description": "CEO with analytical mindset",
    "values": {
      "context": [0.1, 0.2, ...],  # 100 dimensions
      "biology": [0.3, 0.4, ...],  # 124 dimensions
      "behavior": [0.5, 0.6, ...]  # 100 dimensions
    }
  }'

# Search tensors semantically
curl -X POST http://localhost:8000/search \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"query": "analytical leadership style", "n_results": 5}'

# Compose multiple tensors
curl -X POST http://localhost:8000/search/compose \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"tensor_ids": ["tensor_1", "tensor_2"], "method": "weighted_blend"}'
```

See `api/` directory for full endpoint documentation.

---

## Next Steps

After generating a simulation:

1. **Run the E2E pipeline**:
   ```bash
   ./run.sh quick
   ```

2. **Test convergence** (validate causal reasoning consistency):
   ```bash
   # Run a template 3 times and compute convergence score
   python run_all_mechanism_tests.py --convergence-e2e --template convergence/simple --convergence-runs 3
   ```

   This measures how consistently the simulation produces the same causal structures across runs. Grades: A (>=90%), B (>=80%), C (>=70%), D (>=50%), F (<50%).

3. **Explore templates by mechanism**:
   ```bash
   # See which templates test which mechanisms
   ./run.sh list

   # Run all templates that test M7 (causal chains)
   ./run.sh run --mechanism M7
   ```

## Troubleshooting

**"OPENROUTER_API_KEY not set"**
→ Add your API key to `.env` file and load it: `export $(cat .env | xargs)`

**"Illegal header value" with embedded newlines**
→ Your API key has line breaks. Ensure it's on a single line in `.env` with no line breaks
→ When exporting manually, use one line: `export OPENROUTER_API_KEY="your_key_here"`

**"ModuleNotFoundError: No module named 'msgspec'"**
→ Install missing dependency: `uv pip install msgspec`

**"LLM client in dry_run mode"**
→ Environment variables not loaded. Run: `export $(cat .env | xargs)` before running scripts

**"OpenRouter API error: 401 - User not found"**
→ API key invalid or not loaded. Verify key in `.env` and export environment variables

**Simulation takes too long**
→ Use `--skip-summaries` flag or choose a quick-tier template

**Costs too high**
→ Use `--free` for testing, or use quick-tier templates

## Example Output

```
================================================================================
TEMPLATE CATALOG (Verified Only)
================================================================================
ID                                       TIER         CATEGORY     MECHANISMS
--------------------------------------------------------------------------------
showcase/board_meeting                   standard     showcase     M1, M7, M11 +1
showcase/jefferson_dinner                standard     showcase     M3, M7, M11 +1
showcase/hound_shadow_directorial        comprehensive showcase    M17, M10, M14 +3
convergence/simple                       quick        convergence  M7, M11
convergence/standard                     standard     convergence  M7, M11, M13
--------------------------------------------------------------------------------
Total: 13 verified templates
```

---

**Ready to try?**

```bash
# Natural language
python run_all_mechanism_tests.py --nl "your natural language prompt here"

# Or pick a template
./run.sh list
./run.sh run board_meeting
```
