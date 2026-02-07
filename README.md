# Timepoint Daedalus

**Structured temporal simulation for problems that outgrow prompting.**

LLMs are getting smarter. Context windows are measured in millions of tokens. So why build structured simulation infrastructure around them?

Because the problems that matter—backward causal reasoning, multi-entity state tracking, knowledge provenance, convergence analysis—are not generation problems. They're **search, coordination, and verification** problems. The structure isn't scaffolding that gets removed as models improve. It's the product. And it becomes *more* valuable as the engines get more powerful, not less.

---

## Why Structure, Not Just Prompts

A frontier LLM can generate a plausible story about a crew crash-landing on an alien planet. Timepoint generates a **meaning graph**: 10 typed entities with numerical emotional states, causal chains with scored alternatives across 3 counterfactual survival strategies, knowledge items with provenance ("Who discovered the water is contaminated? Who noticed the fauna predict storms?"), and timelines with 90+ quantitative state variables propagated across 5,100 steps. One is prose. The other is a computational artifact you can query, compare, analyze, and build on.

The **Castaway Colony** template makes this concrete. Six crew members crash-land on Kepler-442b. Over 10 timepoints they must choose: fortify the crash site, explore the alien biosphere, or repair the emergency beacon. The template exercises all 19 mechanisms—including 7 that had zero verified templates before it existed.

### What structure provides that prompting cannot

**Search, not generation.** BRANCHING mode doesn't generate one survival strategy—it explores three. In Castaway Colony, the Day 7 branch point spawns parallel timelines (Fortify, Explore, Repair), each evaluated by a 405B judge LLM against resource constraints: O2 reserves, food rations in kg, hull integrity percentage. The winning strategy is *selected from a search space*, not *generated in a single pass*. No amount of context window or chain-of-thought turns autoregressive generation into tree search with evaluation.

**Combinatorial complexity.** Castaway Colony has 10 entities, 4 influence channels each, across 10 timepoints—producing O(100,000) possible interaction paths. That's one template. Even modest scenarios generate state spaces that exceed any context window. This isn't a limitation that disappears with larger models—it's a mathematical property of the domain. Structure provides tractable navigation of intractable spaces through pruning, scoring, and selective expansion.

**Quantitative state propagation.** O2 reserves deplete at 6 crew x 0.84 kg/hour. Water purification degrades at 0.5 liters/day. Hull integrity drops 0.3% per day from alien atmosphere. Radiation storms spike to 12 mSv/hour. These aren't flavor text—they're 90+ numerical values propagated across 5,100 steps with explicit mathematical functions. An LLM can write "supplies were running low"—but it cannot track `o2_reserve_hours = 336 → 288 → 240 → 192` with precision across 1,200 coordinated calls. LLMs do not do reliable arithmetic over long sequences. This is a known architectural property of transformer attention, not a training gap that next year's model will close.

**Knowledge flow with provenance.** The output isn't "the doctor discovered the water was contaminated." It's a typed graph edge: `{type: "empirical_observation", source: "dr_felix_okonkwo", target: "cmdr_yuki_tanaka", content: "water_source_contaminated_with_alien_microbes", timepoint: "tp_002"}` with a propagation chain: `okonkwo -> tanaka (critical alert) -> all_crew (rationing order)`. Structured data that downstream systems can query, aggregate, and reason over. A narrative paragraph is not computationally useful.

**Convergence testing.** Run Castaway Colony three times and ask: "Does the biologist always discover contaminated water first?" "Is fauna-predicts-storms a consensus knowledge edge?" "Does Branch C consistently require navigator data?" These are testable hypotheses across runs. This requires deterministic structure around stochastic generation—comparable structural anchors to align against.

**Composable mechanisms.** The 19 mechanisms (M1-M19) are independently testable, independently fixable, and independently improvable. In Castaway Colony, the alien ecosystem exercises M4/M6/M16 independently from crew dialog (M11) or branching (M12). When emotional arousal saturated at 1.0, the fix was in M11's decay function—without touching M17 (portal reasoning) or M3 (knowledge flow). In a monolithic prompt, everything is entangled.

### The engine/chassis distinction

Growing LLM power makes the structure *more* valuable, not less. The LLM is the engine—it generates the raw material (dialog, antecedents, emotional keywords). But the value to a human isn't in the raw text. It's in the meaning graph. That's what you can analyze, visualize, compare across runs, feed into training pipelines, or use as input to other systems.

A more powerful engine doesn't eliminate the need for a chassis, transmission, and steering. It makes the vehicle faster—but the structure is what makes it *drivable*.

The Castaway Colony template demonstrates this directly: DeepSeek R1 calculates O2 depletion rates, Llama 70B generates crew conflict dialog, Qwen produces structured flora analysis JSON, and 405B judges branch outcomes. Four models, each doing what it's best at, coordinated by 19 mechanisms that no prompt could replicate.

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
|  19 Mechanisms (see MECHANICS.md)                          |
|  Fidelity graphs, causal chains, knowledge tracking,       |
|  entity prospection, animistic agency, ...                 |
+----------------------------+------------------------------+
                             v
+-----------------------------------------------------------+
|  Model Selection (12 open-source LLMs via OpenRouter)      |
|  Action-appropriate: math->DeepSeek, dialog->Llama         |
+-----------------------------------------------------------+
```

---

## When to Use This

**Good fit:**
- "How do we get from here to there" scenarios (PORTAL mode)
- Simulations requiring causal consistency and knowledge provenance
- Training data generation for temporal/causal reasoning
- Deep queries into specific entities or moments
- Anywhere combinatorial state spaces exceed what a single prompt can navigate

**Not the right tool (yet):**
- Production systems requiring SLAs (research prototype)
- Real-time applications (LLM latency dominates)
- Enterprise scale (1000+ concurrent runs)

---

## Documentation

- **[MECHANICS.md](MECHANICS.md)** -- Technical specification of all 19 mechanisms, with Castaway Colony examples
- **[QUICKSTART.md](QUICKSTART.md)** -- Detailed setup and usage guide
- **[SYNTH.md](SYNTH.md)** -- SynthasAIzer control paradigm (envelopes, voices, patches)
- **[MILESTONES.md](MILESTONES.md)** -- Roadmap from prototype to platform

---

## License

Apache 2.0

---

*Named for Daedalus, who mastered the labyrinth but warned: don't trust technology too much—or too little. Simulation is powerful, but not reality.*
