# Timepoint Daedalus

**Portal to a future outcome. Work backward to understand how to get there.**

Timepoint is temporal simulation where fidelity follows attention. Instead of rendering everything at uniform detail (expensive, context collapse), resolution concentrates where you actually look—like a map that sharpens only where you zoom.

The result: **95% cost reduction** while preserving causal consistency.

---

## The Core Insight: Query-Driven Fidelity

Traditional simulations render every entity at every moment at full resolution. This is wasteful—most of that detail is never queried again. Worse, growing context windows degrade temporal structure. You can't reason about causality in a lossy summary.

Timepoint inverts this: **resolution is a 2D surface over (entity, time)** that concentrates detail where queries land.

```
Query: "What did Alice tell Bob at T2 that changed his product strategy?"

              T0    T1    T2    T3    T4    T5
           ┌─────┬─────┬─────┬─────┬─────┬─────┐
   Alice   │  ░  │  ▒  │  █  │  █  │  ▒  │  ░  │  ← queried at T2-T3
           ├─────┼─────┼─────┼─────┼─────┼─────┤
   Bob     │  ░  │  ░  │  ▒  │  █  │  ▒  │  ░  │  ← queried at T3
           ├─────┼─────┼─────┼─────┼─────┼─────┤
   Carol   │  ░  │  ░  │  ░  │  ▒  │  ░  │  ░  │  ← 1-hop from Bob
           ├─────┼─────┼─────┼─────┼─────┼─────┤
   Product │  ░  │  ░  │  ▒  │  █  │  █  │  ▒  │  ← queried at T3-T4
           ├─────┼─────┼─────┼─────┼─────┼─────┤
   Market  │  ░  │  ░  │  ░  │  ▒  │  ▒  │  ░  │  ← 1-hop from Product
           └─────┴─────┴─────┴─────┴─────┴─────┘

   █ = queried (full fidelity)    5 cells  × $0.50 = $2.50
   ▒ = propagated (elevated)      9 cells  × $0.10 = $0.90
   ░ = dormant (embedding only)  16 cells  × $0.02 = $0.32
                                 ─────────────────────────
                                 Total: $0.15  vs  $3.00 naive
```

A minor character exists as a 200-token tensor embedding until someone asks about them. Then the system elevates their resolution while preserving causal consistency with everything already established.

**Resolution Levels:**
```
┌──────────────────┬────────────┬───────────┬─────────┬─────────┐
│     TENSOR       │   SCENE    │   GRAPH   │ DIALOG  │ TRAINED │
│   (embedding)    │ (context)  │ (relations)│ (speech)│ (full) │
│     $0.02        │   $0.05    │   $0.10   │  $0.25  │  $0.50  │
├──────────────────┴────────────┴───────────┴─────────┴─────────┤
│████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│ ← most entities stay here                    few need this →  │
└───────────────────────────────────────────────────────────────┘
```

Entities flow through these levels on demand. New detail never contradicts established facts.

---

## Quick Start

```bash
git clone https://github.com/realityinspector/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt

# Set your OpenRouter API key
export OPENROUTER_API_KEY=your_key_here

# See it work
./run.sh quick                    # Quick-tier templates (~$0.15)
./run.sh run board_meeting        # Single scenario
./run.sh list                     # List all 13 verified templates
```

---

## PORTAL Mode: Backward Temporal Reasoning

The flagship feature. Given a future endpoint, discover plausible paths from the present.

```bash
./run.sh run hound_shadow_directorial   # Directorial mode with M17
./run.sh run vc_pitch_branching         # Counterfactual branching
```

**How it works:**

```
Target: "$1B exit in 2030"

                          ◀── backward reasoning ──

    NOW                    PIVOT 1              PIVOT 2                2030
     │                        │                    │                    │
     ├────────────────────────┼────────────────────┼────────────────────┤
     │                        │                    │                    │
     │   ╭─ Enterprise pivot ─┼────────────────────┼───────────────────╮│
     ○───┤                    ◆                    ◆                   ●│ $1B
     │   ├─ Hybrid model ─────┼────────────────────┤                   ││
     ○───┤                    │ Series B terms     │ Market choice     ││
     │   ╰─ Stay consumer ────┼─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ╳ (no path to $1B) ││
     ○─ ─ ╯                   │                    │                   ╯│
     │                        │                    │                    │

    Present                                                        Endpoint
    choices                                                        (fixed)
```

PORTAL doesn't predict the future—it maps the decision landscape backward:
- **Pivot points**: moments where paths diverge (Series B terms, market choice)
- **Closed paths**: some present choices eliminate the target outcome entirely
- **Path constraints**: what must be true at each stage for the endpoint to remain reachable

**Use cases:**
- Strategic planning ("What sequence of events leads to this exit?")
- Capital allocation ("Which early decisions most constrain later outcomes?")
- Scenario analysis ("Where do success and failure paths diverge?")

---

## Temporal Modes

Time isn't one thing. Timepoint supports five distinct temporal ontologies, each with its own notion of causality, validation rules, and fidelity allocation strategy:

| Mode | Description | Use When | Example Template |
|------|-------------|----------|------------------|
| **PEARL** | Standard causal DAG—causes precede effects | Default forward simulation | `board_meeting` |
| **PORTAL** | Backward from endpoints to present | Strategic planning, path discovery | `mars_mission_portal` |
| **BRANCHING** | Counterfactual timelines from decision points | "What if" analysis | `vc_pitch_branching` |
| **CYCLICAL** | Prophetic/mythic time, future constrains past | Time loops, generational sagas | (no verified templates) |
| **DIRECTORIAL** | Five-act narrative with tension arcs | Story-driven simulations | `hound_shadow_directorial` |

**Why modes matter**: Each mode changes what "consistency" means:
- In PEARL, knowledge must flow forward—no anachronisms allowed
- In PORTAL, we work backward from a known future, so paths must converge
- In BRANCHING, parallel timelines can diverge but each timeline is internally consistent
- In CYCLICAL, events can cause their own preconditions—prophecies are structural, not decorative
- In DIRECTORIAL, dramatic needs drive causality—coincidences are permitted if the story demands them

**Fidelity follows mode semantics**: DIRECTORIAL concentrates tokens at climax moments. CYCLICAL allocates fidelity at cycle boundaries where patterns become visible. PORTAL invests heavily at pivot points where paths diverge.

See [MECHANICS.md](MECHANICS.md) for full implementation details.

---

## Knowledge Provenance

Entities don't magically know things. The system tracks **exposure events**: who learned what, from whom, when.

```
         T1              T2              T3
          │               │               │
  Alice ──●───────────────●───────────────●──
          │    tells Bob  │               │
  Bob   ──○───────────────●───────────────●──
          │               │   tells Carol │
  Carol ──○───────────────○───────────────●──
          │               │               │

  ● = knows the information
  ○ = doesn't know yet

  Query: "What does Carol know at T2?"
  Answer: Nothing about the news—she learns at T3 from Bob.
```

This enables:
- Preventing anachronisms ("How does Jefferson know about Louisiana Purchase in 1787?")
- Tracing belief formation and information flow
- Answering counterfactuals ("If Madison hadn't shared his notes, what would Hamilton believe?")

---

## Performance

| Scenario | Naive Cost | Timepoint | Reduction |
|----------|------------|-----------|-----------|
| 5 entities, 3 timepoints | ~$1.00 | $0.02-0.05 | 95-98% |
| 10 entities, 5 timepoints | ~$3.00 | $0.08-0.15 | 95-97% |
| 20 entities, 10 timepoints | ~$10.00 | $0.30-0.60 | 94-97% |

Cost reduction comes from query-driven fidelity, not lossy compression—temporal consistency is preserved.

**Free tier available:** `./run.sh run --free board_meeting` uses OpenRouter's free models.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Natural Language Query                                 │
│  "Simulate the board meeting after competitor news"     │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Orchestrator + Temporal Agent                          │
│  (Scene control, fidelity management, mode selection)   │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  19 Mechanisms (see MECHANICS.md)                       │
│  Fidelity graphs, causal chains, knowledge tracking,    │
│  entity prospection, animistic agency, ...              │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Model Selection (12 open-source LLMs via OpenRouter)   │
│  Action-appropriate: math→DeepSeek, dialog→Llama        │
└─────────────────────────────────────────────────────────┘
```

---

## When to Use This

**Good fit:**
- "How do we get from here to there" scenarios (PORTAL mode)
- Simulations requiring causal consistency and knowledge provenance
- Training data generation for temporal/causal reasoning
- Deep queries into specific entities or moments

**Not the right tool (yet):**
- Production systems requiring SLAs (research prototype)
- Real-time applications (LLM latency dominates)
- Enterprise scale (1000+ concurrent runs)

---

## Why Structure Matters (Even as LLMs Get Smarter)

A frontier LLM with a million-token context window could generate a plausible backward causal chain and write dialog between characters. So why build structured simulation infrastructure around it?

Because **the structure isn't scaffolding that gets removed—it's the product.**

### What structure provides that prompting cannot

**Search, not generation.** PORTAL mode doesn't generate one backward path—it explores a tree. A 10-step backward trace generates 350 candidate antecedents (7 candidates x 10 steps x 5 paths), runs 350 mini forward-simulations, and has a judge LLM score each one. The winning causal chain is *selected from a search space*, not *generated in a single pass*. No amount of context window or chain-of-thought turns autoregressive generation into tree search with evaluation.

**Quantitative state propagation.** Emotional arcs, energy budgets, and knowledge flow are tracked numerically with explicit mathematical functions (exponential decay, symmetric clamping, circadian modulation). An LLM can write "she grew more stressed"—but it cannot track `valence = -0.580 → -0.600 → -0.620 → -0.640` with numerical precision across 862 coordinated calls. The system caught and fixed an arousal saturation bug through mathematical analysis. An LLM would never notice or self-correct a systematic numerical drift.

**Knowledge flow with provenance.** The output isn't "Lin Zhang knew about the anomalies." It's a typed graph edge: `{type: "fact", source: "lin_zhang", target: "thomas_webb", content: "5% decrease in O2 generator efficiency", timepoint: "tp_002_2030"}`. Structured data that downstream systems can query, aggregate, and reason over. A narrative paragraph is not computationally useful.

**Convergence testing.** Run the same scenario three times and measure structural divergence quantitatively. Which causal links are robust? Which are sensitive to initial conditions? This requires deterministic structure around stochastic generation—comparable structural anchors to align against across runs.

**Composable mechanisms.** The 19 mechanisms (M1-M19) are independently testable, independently fixable, and independently improvable. When emotional arousal saturated at 1.0, the fix was in M11's decay function—without touching M17 (portal reasoning) or M3 (knowledge flow). In a monolithic prompt, everything is entangled.

### The engine/chassis distinction

Growing LLM power makes the structure *more* valuable, not less. The LLM is the engine—it generates the raw material (dialog, antecedents, emotional keywords). But the value to a human isn't in the raw text. It's in the **meaning graph**: typed entities with numerical emotional states, causal chains with scored alternatives, knowledge items with provenance, timelines with quantitative metadata. That's what you can analyze, visualize, compare across runs, feed into training pipelines, or use as input to other systems.

A more powerful engine doesn't eliminate the need for a chassis, transmission, and steering. It makes the vehicle faster—but the structure is what makes it *drivable*.

---

## Documentation

- **[MECHANICS.md](MECHANICS.md)** — Technical specification of all 19 mechanisms
- **[QUICKSTART.md](QUICKSTART.md)** — Detailed setup and usage guide
- **[MILESTONES.md](MILESTONES.md)** — Roadmap from prototype to platform

---

## License

Apache 2.0

---

*Named for Daedalus, who mastered the labyrinth but warned: don't trust technology too much—or too little. Simulation is powerful, but not reality.*
