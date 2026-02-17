timepoint contingent / temporal context dependent / proception dependent

just barely touching the light of the universe

clockchain - mention it - Grokipedia of temporal history, complete with attributable causal chains

discovering the truth about time and causal chains

synthetic data order of magnitude easier for framework

novel factors like proception

portal mode



# Timepoint Daedalus Alpha

**Synthetic time travel through social simulation.**

**The first practical SNAG engine: Social Network Augmented Generation.**

Like RAG retrieves documents to ground generation, SNAG synthesizes and maintains a structured social graph---complete with causal provenance, knowledge flow, emotional states, and temporal consistency---to ground LLM generation in complex group dynamics.

This transforms LLMs from fragile, drifting storytellers into reliable multi-agent reasoners. Naive single-prompt simulations collapse beyond ~10 entities or ~20 interactions due to inconsistency and token explosion. SNAG's structured propagation, variable-depth fidelity, and composable mechanisms let you scale to dozens of entities across hundreds of timepoints---while keeping costs low and causality auditable.

The value is exponential with scale: the larger and more intricate the social system (board + investors + competitors, colony crew + Earth command, historical delegations), the more emergent behaviors surface that intuition or simple models miss. SNAG unlocks simulation of systems previously impossible with LLMs, enabling rigorous decision testing, strategic foresight, and high-quality training data at any scope.

Render any historical, present, or future social moment---like a synthesizer renders sound waves---with variable fidelity: coarse tensors for broad arcs, rich dialog only at critical pivots.

In the coming immersive VR era, these simulations become places you inhabit, not just read.

Costs: $0.15--$1.00 per run. All 21 templates verified Feb 16, 2026.

-> Full example run (every artifact): [EXAMPLE_RUN.md](EXAMPLE_RUN.md)
-> Sample dialogs and character arcs: [EXAMPLE_DIALOGS.md](EXAMPLE_DIALOGS.md)

## Quick Start
```bash
git clone https://github.com/timepoint-ai/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key
./run.sh list                            # All templates
./run.sh run mars_mission_portal         # PORTAL: backward from failed mission
./run.sh run castaway_colony_branching   # Full mechanisms + counterfactuals
```

## Core Capability: SNAG in Action
Define a scenario -> generate typed social graph -> propagate states -> explore temporal modes.

Flagship examples:
| Template                    | Mode      | Key Feature                          | Entities | Timepoints | Training Examples | Cost   |
|-----------------------------|-----------|--------------------------------------|----------|------------|-------------------|--------|
| mars_mission_portal         | PORTAL    | Backward reasoning from 2031 failure | 4        | 11         | 40                | ~$0.68 |
| castaway_colony_branching   | BRANCHING | Counterfactual survival strategies   | 8        | 16         | 120               | ~$0.35 |
| vc_pitch_branching          | BRANCHING | Investor reactions across pitches    | 5        | 16         | 60                | ~$0.30 |

## Why This Matters Now (and Even More Tomorrow)
- **Strategic foresight** --- PORTAL maps critical paths backward from any outcome ("$1B exit", "colony survives", "election won").
- **Decision testing** --- Run scenarios multiple ways, measure causal convergence, catch hidden propagation failures.
- **Physics-like social forecasting** --- Variable-depth fidelity treats social systems like physical ones: low-res for long horizons, high-res at pivot points.
- **Superior training data** --- Full causal ancestry, provenance, counterfactuals, quantitative states baked in.

In the immersive VR future, these simulations become *places you visit*. Timepoint is an early portal.

## Temporal Modes
| Mode        | Causality Model                    | Best For                              | Example                      |
|-------------|------------------------------------|---------------------------------------|------------------------------|
| PEARL       | Strict forward                     | Standard timelines                    | board_meeting                |
| PORTAL      | Backward from target               | Goal decomposition, critical paths    | mars_mission_portal          |
| BRANCHING   | Counterfactual branches            | "What if" analysis                    | castaway_colony_branching    |
| CYCLICAL    | Future constrains past             | Mythic loops, generational sagas      | agent4_elk_migration         |
| DIRECTORIAL | Dramatic tension drives events     | Story arcs                            | hound_shadow_directorial     |

PORTAL stands out: explores hundreds of candidate backward steps, scores coherence with frontier models, delivers a queryable graph of pivots and constraints.

## Technical Foundations
- **Per-character dialog generation** --- Each character generates dialog turns via independent LLM calls with persona-derived generation parameters (temperature, top_p, max_tokens from entity state). A LangGraph steering agent selects speakers, manages narrative arc, and can suppress or end dialog. Replaces single-call generation that produced identical character voices.
- **Params2Persona waveform** --- Entity tensor state (arousal, energy, behavior vector) maps to concrete LLM API parameters per turn. Aroused characters get higher temperature; fatigued characters get shorter responses; ADPRS phi scales all params.
- **Two-layer context (Fourth Wall)** --- Back layer shapes HOW a character speaks (true emotional state, withheld knowledge, suppressed impulses). Front layer provides WHAT they know (filtered knowledge, natural-language relationships). PORTAL mode strips knowledge from causally inaccessible timepoints.
- **Variable-depth fidelity** --- Most state compressed (~200 tokens); detail expands on demand. 95%+ token savings + physics-style abstraction.
- **SynthasAIzer waveform control** --- Timepoints rendered like sound: envelopes, gating, per-entity "voices."
- **Semantic quality gates** --- Three-level evaluation: per-dialog (narrative advancement, conflict specificity, voice distinctiveness), cross-dialog (progression between conversations), and full-run coherence. Surface heuristics filter first; frontier model evaluation runs on passes.
- **Extended proception** --- Entities accumulate episodic memories, rumination topics, withheld knowledge, and suppressed impulses across dialogs. These feed back into future dialog generation.
- **19 composable mechanisms** --- Full spec in [MECHANICS.md](MECHANICS.md).
- **Convergence validation** --- Repeat runs, Jaccard on causal graphs -> reliability without labels.

Outputs: JSONL/SQLite for ML, markdown/Fountain for humans, Oxen.ai auto-upload for versioning.

## Use Cases Today
- Corporate strategy & crisis simulation
- Policy, history, and historical counterfactuals
- Fine-tuning for causal/temporal/multi-agent reasoning
- Research platform for social physics

## Documentation
- [EXAMPLE_RUN.md](EXAMPLE_RUN.md) --- complete walkthrough
- [MECHANICS.md](MECHANICS.md) --- all 19 mechanisms
- [SYNTH.md](SYNTH.md) --- synthesizer paradigm details
- [QUICKSTART.md](QUICKSTART.md) --- full setup

License: Apache 2.0
Models: fully permissive open weights for training data; commercial frontier models for coding, mostly documented in git commit history.
