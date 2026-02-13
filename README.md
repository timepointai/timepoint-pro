# Timepoint Daedalus

**[See a complete example run &rarr;](EXAMPLE_RUN.md)** &mdash; Every output from a single PORTAL simulation: timeline, dialogs, knowledge graph, ADPRS waveforms, entity tensors, training data.

**Structured temporal simulation that renders queryable meaning graphs, not prose.**

An LLM can generate a plausible story about a crew crash-landing on an alien planet. Timepoint generates this:

```
10 entities with tracked emotional state (valence, arousal, energy per timestep)
90+ quantitative variables propagated across 5,100 steps (O2, food, hull, radiation)
3 counterfactual branches from a single decision point, each scored by 405B judge
typed knowledge graph: who learned what, from whom, at which timepoint
convergence-testable: run 3x, measure causal graph Jaccard similarity
training data where every example carries its full causal ancestry
$0.30, ~1,200 LLM calls, 4 models (DeepSeek R1, Llama 70B, Qwen 72B, 405B)
```

The output is a structured computational artifact — typed graph edges with provenance, auditable causal chains, quantitative state you can propagate and query. Not a narrative summary. The difference matters when you want to fine-tune downstream models on causal reasoning, knowledge flow, or multi-entity state tracking, because each training example carries the full chain of events that produced it.


### WRITTEN BY A HUMAN
## the rest co-authored by AI 

*Timepoint Daedalus works enables "synthetic time travel".*

Since I was a kid, I have wanted a portal where I could travel to any place, at any time. As we progress towards and immersive VR future, with beyond-intelligence level models, that feels more and more plausible to experience sitting at home at my desk on any given afternoon. This repo allows extremely detailed simulation of synthetic social networks. It allows the user to manipulate the timeline in novel ways, including a work-backwards mode where you set a goal, like "make my President in 2040" and it creates the most logical path backwards through time to make that dream come true -- that function is named "PORTAL" as a reference to my own childhood dreams. Please give Timepoint-Daedalus a try if you are interested in how LLM's can perform powerful simulations with very little configuration. There are baked in templates, so all you need is an OpenRouter key to get started rendering scenarios, and you only need to ask a coding agent for help to render structured training data for each character to fine-tune models for individualized roleplaying. 

_[x.com/seanmcdonaldxyz](https://x.com/seanmcdonaldxyz)_

### The key architectural bet: adaptive stepwise fidelity

Fidelity is a 2D surface over (entity, timepoint). Most entities at most timesteps sit at TENSOR resolution (~200 tokens). A few get elevated to DIALOG or TRAINED (~50k tokens) when queries land on them. This is query-driven lazy resolution — you never pay for detail nobody asked about. The result is ~95% token reduction vs. uniform fidelity, without losing causal structure, because the system maintains explicit exposure events and temporal chains that survive compression.

19 mechanisms (M1-M19) are independently composable: fidelity management, causal chains, knowledge provenance, entity simulation, model selection. When emotional arousal saturated at 1.0, the fix was in M11's decay function — without touching M17 (portal reasoning) or M3 (knowledge flow). In a monolithic prompt, everything is entangled.

### What structure gives you that scaling context windows does not

**Tree search, not autoregression.** BRANCHING mode spawns parallel timelines from a decision point, evaluates each against constraints, selects the best. This is search over a combinatorial space (10 entities x 4 channels x 10 timepoints = O(100k) interaction paths). No context window turns next-token prediction into tree search with evaluation.

**Reliable quantitative state.** `o2_reserve_hours = 336 → 288 → 240 → 192` across 1,200 coordinated calls. 90+ numerical values with explicit functions. Transformers don't do reliable arithmetic over long sequences — this is architectural, not a training gap.

**Knowledge as a typed graph.** Not "the doctor discovered contamination" but `{source: "okonkwo", target: "tanaka", content: "water_contaminated", timepoint: "tp_002"}` with propagation chain `okonkwo -> tanaka (alert) -> all_crew (rationing)`. Entities can't know things without tracked exposure events. Anachronisms are prevented structurally.

**Convergence as quality signal.** Run the same template 3x with different seeds, extract causal graphs, compute pairwise Jaccard. Edges that appear in 9/10 runs are structural; edges in 3/10 are noise. This gives you a reliability signal for synthetic training data without human labels.

**Emergent persona dynamics.** Tanaka's valence 0.50 → 0.86 over a survival arc. Sharma's arousal 0.24 → 0.70 as crises compound. The `persona2params` pipeline maps traits to speaking style to dialog parameters — high arousal + negative valence yields short, interrupting turns; low energy yields trailing-off disengagement. No per-character tuning. The structure provides the right metadata at the right moment and the LLM's understanding of human psychology does the rest.

---

## Quick Start

```bash
git clone https://github.com/realityinspector/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt

# Set your OpenRouter API key
export OPENROUTER_API_KEY=your_key_here

# See it work
./run.sh quick                    # Quick-tier templates
./run.sh run board_meeting        # Single scenario
./run.sh list                     # List all 15 templates

# Or run in a Docker sandbox (containerized Claude Code with network isolation)
./claude-container.sh up
```

---

## Flagship Templates

### Castaway Colony: Full-Mechanism Showcase

The template that exercises all 19 mechanisms. Six crew members crash-land on Kepler-442b and must choose between three survival strategies. Exercises heterogeneous fidelity (M1), progressive training (M2), physics validation (M4), lazy resolution (M5), tensor compression (M6), on-demand entities (M9), and model selection (M18)—the 7 mechanisms that had zero verified templates before this one.

```bash
./run.sh run castaway_colony_branching  # All 19 mechanisms, branching mode
```

### PORTAL Mode: Backward Temporal Reasoning

Given a future endpoint, discover plausible paths from the present.

```bash
./run.sh run mars_mission_portal        # Portal backward reasoning
./run.sh run hound_shadow_directorial   # Directorial mode
./run.sh run vc_pitch_branching         # Counterfactual branching
```

**How it works:**

```
Target: "$1B exit in 2030"

                          <-- backward reasoning --

    NOW                    PIVOT 1              PIVOT 2                2030
     |                        |                    |                    |
     +------------------------+--------------------+--------------------+
     |                        |                    |                    |
     |   +- Enterprise pivot -+--------------------+-------------------+|
     o---+                    *                    *                   o| $1B
     |   +- Hybrid model -----+--------------------+                   ||
     o---+                    | Series B terms     | Market choice     ||
     |   +- Stay consumer ----+- - - - - - - - - - X (no path to $1B) ||
     o- -+                    |                    |                   +|
     |                        |                    |                    |

    Present                                                        Endpoint
    choices                                                        (fixed)
```

PORTAL doesn't predict the future—it maps the decision landscape backward:
- **Pivot points**: moments where paths diverge (Series B terms, market choice)
- **Closed paths**: some present choices eliminate the target outcome entirely
- **Path constraints**: what must be true at each stage for the endpoint to remain reachable

**What a real PORTAL run produces** (Mars Mission Portal — Ares III failure traced backward from 2031 to 2026):

| Metric | Value |
|--------|-------|
| Backward steps | 10 (2031 → 2026), each with 7 candidates simulation-judged by 405B |
| Pivot points | 94 detected across 10 divergent paths |
| Dialogs | 10 conversations, 97 exchanges, 4 characters |
| Mechanisms activated | 14 of 19 in a single run |
| Emotional tracking | Character arcs over 5 years of reconstructed history (valence range: -0.66 to +0.85) |
| Resilience | Recovered from DNS failures and truncated API responses via automatic retry |
| Cost | $0.51 total | 873 LLM calls | ~70 minutes |

The system doesn't just find *a* path — it explores a search space of ~700 candidate antecedents (7 candidates x 10 steps x 10 paths), runs mini forward-simulations to score each, and prunes to the most coherent backward chain (best path coherence: 0.809). The output is a queryable meaning graph with knowledge provenance, not a narrative paragraph.

---

## Temporal Modes

Time isn't one thing. Timepoint supports five distinct temporal ontologies, each with its own notion of causality, validation rules, and fidelity allocation strategy:

| Mode | Description | Use When | Example Template |
|------|-------------|----------|------------------|
| **PEARL** | Standard causal DAG—causes precede effects | Default forward simulation | `board_meeting` |
| **PORTAL** | Backward from endpoints to present | Strategic planning, path discovery | `mars_mission_portal` |
| **BRANCHING** | Counterfactual timelines from decision points | "What if" analysis | `castaway_colony_branching` |
| **CYCLICAL** | Prophetic/mythic time, future constrains past | Time loops, generational sagas | (no verified templates) |
| **DIRECTORIAL** | Five-act narrative with tension arcs | Story-driven simulations | `hound_shadow_directorial` |

**Why modes matter**: Each mode changes what "consistency" means:
- In PEARL, knowledge must flow forward—no anachronisms allowed
- In PORTAL, we work backward from a known future, so paths must converge
- In BRANCHING, parallel timelines can diverge but each timeline is internally consistent
- In CYCLICAL, events can cause their own preconditions—prophecies are structural, not decorative
- In DIRECTORIAL, dramatic needs drive causality—coincidences are permitted if the story demands them

See [MECHANICS.md](MECHANICS.md) for full implementation details.

---

## Query-Driven Fidelity

Not everything needs full resolution. Resolution is a 2D surface over (entity, time) that concentrates detail where queries land:

```
Castaway Colony fidelity map at Day 7 (branch decision):

                  Day1  Day3  Day5  Day7  Day14  Day21
               +------+------+------+------+------+------+
  Cmdr Tanaka  |  o   |  o   |  #   |  #   |  #   |  o   |  TRAINED (command decisions)
               +------+------+------+------+------+------+
  Dr Okonkwo   |  .   |  .   |  o   |  #   |  #   |  o   |  SCENE -> TRAINED (M2)
               +------+------+------+------+------+------+
  Eng Sharma   |  o   |  o   |  o   |  #   |  o   |  o   |  DIALOG (repair queries)
               +------+------+------+------+------+------+
  Nav Park     |  .   |  .   |  .   |  .   |  o   |  .   |  TENSOR -> DIALOG (M5)
               +------+------+------+------+------+------+
  Biosphere    |  .   |  .   |  .   |  .   |  .   |  .   |  TENSOR always (M6)
               +------+------+------+------+------+------+
  Crashed Ship |  .   |  .   |  .   |  .   |  .   |  .   |  TENSOR always (M1)
               +------+------+------+------+------+------+

  # = queried (full fidelity)     . = dormant (embedding only)
  o = propagated (elevated)
```

The injured navigator exists as a 200-token tensor embedding until someone asks about pre-crash navigation data. Then lazy resolution (M5) elevates him to DIALOG while preserving causal consistency. The alien biosphere stays compressed as a tensor (M6) — 97% compression — until a query reconstructs it. The doctor progressively trains (M2) from SCENE to TRAINED as xenobiology queries accumulate.

**Resolution Levels:**
```
TENSOR < SCENE < GRAPH < DIALOG < TRAINED
(~200 tokens)                    (~50k tokens)

Most entities stay at TENSOR. Few ever need TRAINED.
Detail concentrates where it matters.
```

**ADPRS Waveform Gating:** Entities with fitted ADPRS envelopes get per-entity LLM gating during dialog synthesis. The waveform scheduler evaluates each entity's cognitive activation (phi) at each timepoint and maps it to a resolution band. Entities in TENSOR or SCENE bands are excluded from LLM dialog calls — their trajectory snapshots are still recorded but no tokens are spent. Shadow evaluation tracks divergence between ADPRS predictions and actual resolution, persisting reports to run metadata. Fitted envelopes are stored in entity metadata and reloaded on subsequent runs for warm-start refinement, so predictions improve over time. See [SYNTH.md](SYNTH.md) for full specification.

---

## Knowledge Provenance

Entities don't magically know things. The system tracks **exposure events**: who learned what, from whom, when.

```
Castaway Colony knowledge propagation:

  Day 2: Okonkwo discovers contaminated water
  Day 3: Okonkwo reports to Tanaka (critical alert)
  Day 3: Tanaka orders rationing (all crew now know)
  Day 4: Vasquez notices fauna migration correlates with pressure drops
  Day 4: Vasquez tells Cole (defense planning), Vasquez tells Tanaka (strategy)
  Day 6: Park queried about pre-crash nav data -> lazy resolution (M5)
  Day 6: Park reveals hemisphere landing error -> Tanaka -> Vasquez (recalibrate models)

  Query: "Does Cole know about the hemisphere error at Day 5?"
  Answer: No. Park hasn't been queried yet. Cole learns after Day 6 propagation.
```

Each discovery is a typed graph edge: `{type: "empirical_observation", source: "dr_felix_okonkwo", content: "water_source_contaminated_with_alien_microbes", timepoint: "tp_002"}`. This enables:
- Preventing anachronisms (Cole can't plan around hemisphere data before Park reveals it)
- Tracing belief formation and information flow across the crew
- Answering counterfactuals ("If Okonkwo hadn't tested the water, when does contamination get discovered?")

---

## Synthetic Training Data

The simulation isn't just queryable—it's renderable as training data. And the structure changes what "training data" means.

A prompt-based pipeline produces input-output text pairs. Timepoint renders training examples where each datapoint is a **structured computational artifact**:

```
=== CAUSAL HISTORY (M7) ===                    ← full event chain leading to this moment
Timeline leading to current moment (2 events):
  tp_001_formation: Founders decide on roles and equity split.
  tp_002: First investor meeting; Jennifer asks the MRR question.

=== RELATIONSHIP CONTEXT (M13) ===             ← social graph state at query time
Relationships with entities present:
  jennifer_park: cautious (trust: 0.35, alignment: 0.20)

=== KNOWLEDGE PROVENANCE (M3) ===              ← who knows what, from whom, when
Primary sources: scene_initialization (3 items), jennifer_park (2 items)
Learning modes: experienced (85%), told (15%)
Recent: "competitor raised $10M Series A" (from david_kim, confidence: 0.9)

=== ENTITY STATE (M6) ===                      ← quantitative cognitive/physical state
founder_a at T0:
  Physical: Age 32, energy 74/100
  Cognitive: 8 knowledge items, 0.65 decision confidence
  Emotional: Valence 0.24, Arousal 0.60

=== PREDICTION TASK ===
Predict: new knowledge, energy change, emotional impact, causal reasoning.
```

Each completion includes structured JSON with energy dynamics, emotional deltas, mechanism explanations, and full entity metadata. The training data teaches models to **reason within causal structure**, not just pattern-match surface text.

### What makes it different

**Causal ancestry, not context windows.** Every example includes the specific chain of events that caused the current state—not "the team was stressed" but the sequence: `competitor_raises_$10M → jennifer_demeanor_shifts → power_dynamic_inverts → founder_a_arousal: 0.24→0.60`. Models learn causal chains, not vibes.

**Knowledge provenance, not omniscience.** Each entity's knowledge is the set of exposure events they've accumulated. Training examples encode *who knows what and how they learned it*. Models learn about information flow, not just information.

**Counterfactual pairs.** BRANCHING mode generates natural contrastive examples from the same decision point—same entities, same setup, different choices, different outcomes. The $50K MRR answer and the pre-revenue hesitation diverge from one branch point. This is structured contrastive training data that no single-pass generator produces.

**Quantitative state propagation.** Not "supplies were running low" but `o2_reserve_hours: 336 → 288 → 240 → 192` across thousands of propagation steps. Models learn to track numerical state with precision.

**Mechanism annotations.** Each example tagged with which of the 19 mechanisms produced it (M7 causal chain, M11 dialog, M12 counterfactual, M3 knowledge flow), enabling mechanism-specific fine-tuning or filtering.

### Output formats

| Format | Use Case |
|--------|----------|
| **JSONL** | ML training pipelines (streaming, line-delimited prompt/completion pairs) |
| **JSON / CSV / SQLite** | Analysis, querying, visualization |
| **Fountain / PDF** | Industry-standard screenplays (Courier 12pt, proper margins) |
| **Markdown** | Human-readable narrative summaries with character arcs and dialog |

### Convergence: quality assurance without ground truth

How do you validate synthetic data when there's no label set? Run the same template N times with different random seeds. Extract causal graphs. Compute pairwise Jaccard similarity.

If "the doctor discovers contaminated water first" appears in 9/10 runs, it's a robust structural feature of the scenario. If a causal edge appears in 3/10 runs, it's stochastic noise. This provides a **reliability signal for training data** without requiring human labels.

```
Convergence grades:
  A: ≥90%  Highly robust (structural features dominate)
  B: ≥80%  Robust (minor variations in non-critical paths)
  C: ≥70%  Moderate (some contested edges)
  D: ≥50%  Unstable (significant run-to-run variation)
  F: <50%  Unreliable (stochastic dominates structure)
```

```bash
./run.sh convergence e2e board_meeting          # Run 3x + analyze
./run.sh convergence e2e --runs 5 castaway_colony_branching
./run.sh convergence history                    # Show past results
```

### Cost and licensing

Heterogeneous fidelity (M1) + tensor compression (M6) + intelligent model selection (M18) compound:

| Approach | Tokens | Approximate Cost |
|----------|--------|------------------|
| Naive uniform fidelity | ~50M | ~$500 |
| Heterogeneous fidelity | ~2.5M | ~$25 |
| With TTM compression | ~250k | ~$2.50 |

Real-world costs: $0.15–$0.30 for branching templates (60 training examples), $0.50–$2.00 for full showcase templates (hundreds of examples). The VC Pitch Branching template generates 60 training examples across 16 timepoints with 4 entities, 16 dialogs, and 165 dialog exchanges for $0.30.

All 10 models in the pipeline—Llama 3.1/4, Qwen 2.5, DeepSeek, Mistral—carry MIT, Apache 2.0, or Llama/Qwen community licenses. **Commercial synthetic data generation is explicitly permitted.** The pipeline deliberately excludes models with restrictive output ownership clauses.

---

## Architecture

```
+-----------------------------------------------------------+
|  Natural Language Query                                    |
|  "Simulate the board meeting after competitor news"        |
+----------------------------+------------------------------+
                             v
+-----------------------------------------------------------+
|  Orchestrator + Temporal Agent                             |
|  (Scene control, fidelity management, mode selection)      |
+----------------------------+------------------------------+
                             v
+-----------------------------------------------------------+
|  SynthasAIzer Waveform Scheduler                           |
|  ADPRS envelopes: phi→band→per-entity LLM gating          |
|  TENSOR/SCENE band entities skip dialog; cross-run fitting |
+----------------------------+------------------------------+
                             v
+-----------------------------------------------------------+
|  19 Mechanisms (see MECHANICS.md)                          |
|  Fidelity graphs, causal chains, knowledge tracking,       |
|  entity prospection, animistic agency, ...                 |
+----------------------------+------------------------------+
                             v
+-----------------------------------------------------------+
|  Model Selection (10 open-source LLMs via OpenRouter)      |
|  Action-appropriate: math->DeepSeek, dialog->Llama         |
+-----------------------------------------------------------+
```

---

## When to Use This

**Good fit:**
- Synthetic training data with causal provenance, counterfactual pairs, and mechanism annotations
- Fine-tuning data for temporal reasoning, knowledge tracking, state propagation, or multi-entity dialog
- "How do we get from here to there" scenarios (PORTAL mode)
- Simulations requiring causal consistency and knowledge provenance
- Deep queries into specific entities or moments
- Anywhere combinatorial state spaces exceed what a single prompt can navigate

**Not the right tool (yet):**
- Production systems requiring SLAs (research prototype)
- Real-time applications (LLM latency dominates)
- Enterprise scale (1000+ concurrent runs)

---

## Persona Chat: Talk to Our Testing Personas

Four detailed testing personas represent real-world evaluation contexts. Each has a domain-specific template that exercises their stated use case, and a chat harness that lets you discuss any document from their perspective.

| Persona | Domain | Template Mode | Template |
|---------|--------|---------------|----------|
| **AGENT1** — Victoria Langford-Chen | Corporate Finance | PORTAL | `persona/agent1_regulatory_stress` |
| **AGENT2** — Dr. Raj Venkataraman | Aerospace Engineering | BRANCHING | `persona/agent2_mission_failure` |
| **AGENT3** — Marcus Delgado-Washington | Legal Tech (Startup) | PEARL | `persona/agent3_litigation_discovery` |
| **AGENT4** — Dr. Kate Nez-Bridger | Wildlife Ecology (RMEF) | CYCLICAL | `persona/agent4_elk_migration` |

**Chat with a persona about any document:**

```bash
# Interactive conversation — Victoria reviews the README
./run.sh chat --persona AGENT1 --context README.md

# Batch question — Raj evaluates quantitative state propagation
./run.sh chat --persona AGENT2 --batch "What concerns you about the quantitative state propagation?"

# Run a persona's template, then chat about the results
./run.sh run persona/agent3_litigation_discovery
./run.sh chat --persona AGENT3 --context output/simulations/summary_*.json \
  --batch "How well did this simulation capture information asymmetry?"

# Kate reviews MECHANICS.md from an ecologist's perspective
./run.sh chat --persona AGENT4 --context MECHANICS.md --max-tokens 500
```

The system prompt is simple: persona markdown + context file contents. No framework, no abstraction — just `OpenRouterClient` from `llm.py`. Full persona backgrounds are in [`docs/testing_personas/`](docs/testing_personas/).

---

## Documentation

- **[EXAMPLE_RUN.md](EXAMPLE_RUN.md)** -- Complete example run with every output artifact: timeline, dialogs, knowledge graph, ADPRS waveforms, entity tensors, training data
- **[MECHANICS.md](MECHANICS.md)** -- Technical specification of all 19 mechanisms, with Castaway Colony examples
- **[QUICKSTART.md](QUICKSTART.md)** -- Detailed setup and usage guide
- **[SYNTH.md](SYNTH.md)** -- SynthasAIzer control paradigm (ADSR envelopes, ADPRS waveforms, voices, patches)
- **[MILESTONES.md](MILESTONES.md)** -- Roadmap from prototype to platform
- **[claude-container.sh](claude-container.sh)** -- Docker sandbox for containerized development with iptables network isolation
- **[docs/testing_personas/](docs/testing_personas/)** -- Four detailed testing personas (finance, aerospace, legal tech, wildlife ecology)

---

## License

Apache 2.0

---

*The models generate. The structure reasons about time, causality, and consistency. Named for Daedalus — who mastered the labyrinth but warned his son about the limits of the tools.*
