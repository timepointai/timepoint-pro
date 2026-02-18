# Example Run: Ares III Mars Mission Portal

**[Back to README](README.md)** | **[Full Dialog Transcript (78 turns)](EXAMPLE_DIALOGS.md)** | Run ID: `run_20260218_091456_55697771` | Template: `mars_mission_portal`

A complete PORTAL-mode simulation tracing backward from a catastrophic Mars mission failure in 2031 to its institutional origins in 2026. Every number, dialog line, and graph edge below was produced by a single `./run.sh run mars_mission_portal --portal-quick` invocation on February 18, 2026.

---

## At a Glance

| | |
|---|---|
| **Mode** | PORTAL (backward temporal reasoning) |
| **Timespan** | 2031 &rarr; 2026 (5 years, 5 backward steps via `--portal-quick`) |
| **Entities** | 4 humans, all reaching dialog resolution |
| **Dialogs** | 6 conversations, 78 turns |
| **Training examples** | 20 structured prompt/completion pairs |
| **Mechanisms fired** | 15 of 19 |
| **ADPRS waveform gating** | 24 evaluations, 8 divergent (33.33%) |
| **Cost** | $0.18 &bull; 479 LLM calls &bull; 318K tokens |
| **Duration** | 2,668s (~44 minutes) |

---

## Table of Contents

1. [The Scenario](#1-the-scenario)
2. [Cast of Characters](#2-cast-of-characters)
3. [Backward Timeline](#3-backward-timeline)
4. [Sample Dialogs](#4-sample-dialogs)
5. [Knowledge Provenance](#5-knowledge-provenance)
6. [ADPRS Waveform Gating](#6-adprs-waveform-gating)
7. [Fidelity Strategy](#7-fidelity-strategy)
8. [Entity Tensors](#8-entity-tensors)
9. [Mechanism Usage](#9-mechanism-usage)
10. [Training Data](#10-training-data)
11. [Run Metadata](#11-run-metadata)
12. [What You Can Do Next](#12-what-you-can-do-next)
13. [Port to Oxen.ai](#13-port-to-oxenai)
14. [API & Programmatic Access](#14-api--programmatic-access)

---

## 1. The Scenario

The Ares III crewed Mars mission loses contact during orbital insertion in 2031. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell.

**PORTAL mode** doesn't predict the future. It works backward from a known endpoint, exploring how present-day decisions create future outcomes. Starting from the communication blackout, the system generates 3 candidate antecedent states per step, scores each with a 405B judge model (no mini forward-simulations --- states are scored directly), and selects the most coherent backward chain.

The result: a 5-year causal graph showing how schedule pressure overruled safety concerns at every level, how engineering warnings were systematically dismissed, and how the crew's own dialog reveals the tensions that built toward catastrophe. Produced for under twenty cents.

### How PORTAL backward inference works

```
Known endpoint (2031): Mission failure
                |
    Generate 3 candidate causes
    Score each candidate with 405B judge (states only, no mini-sim)
    Select best candidate
                |
        Step back 1 year
        Repeat 5 times (--portal-quick)
                |
Result: Causal chain from Jan 2026 -> 2031
```

Each backward step costs ~$0.03 (3 candidates x 405B scoring, no disposable dialog). The system spent $0.18 total across 479 LLM calls to produce 6 timepoints, 6 dialogs with 78 turns, and 20 training examples.

---

## 2. Cast of Characters

Four crew members, each with tracked cognitive state, emotional arcs, and distinct knowledge bases. All defined in the template's `entity_roster` and carried through the full simulation.

| Character | Role | Final Valence | Final Arousal | Final Energy |
|-----------|------|:---:|:---:|:---:|
| **Sarah Okafor** | Mission Commander | +0.47 | 0.57 | 124.4 |
| **Raj Mehta** | Flight Engineer | -0.20 | 0.81 | 123.7 |
| **Lin Zhang** | Systems Engineer | -0.20 | 0.94 | 116.7 |
| **Thomas Webb** | Mission Director | -0.17 | 0.78 | 118.4 |

**Emotional arcs**: Zhang's negative valence (-0.20) and near-maximum arousal (0.94) make her the most strained character in this run --- driven by repeated frustration at having her technical warnings about the oxygen generator dismissed across every timepoint. Webb's negative valence (-0.17) with moderately high arousal (0.78) captures a director whose schedule-first approach produces increasing tension as safety concerns mount. Okafor's positive valence (+0.47) with moderate arousal (0.57) shows a commander who maintains composure and optimism while mediating between engineering concerns and institutional pressure. Mehta's negative valence (-0.20) with high arousal (0.81) reflects a cautious, conflict-averse engineer who detects problems early but hesitates to escalate them forcefully.

---

## 3. Backward Timeline

Portal mode traces backward from the 2031 failure. Each step was selected from 3 candidates scored by the 405B judge. All 4 entities are present at every timepoint. The `--portal-quick` flag reduced backward steps from 10 to 5 for a fast demo run.

```
Step   Year     Event
 0     2031     Mission failure: loses contact during orbital insertion
 1     2030     Raj patches around comm anomalies; Webb reduces bandwidth over Lin's objections
 2     2029     Lin discovers oxygen generator design flaw; Webb dismisses for schedule
 3     2028     O2 generator at 92% efficiency; Lin pushes for redesign; Webb demands schedule adherence
 4     2027     Lin finds 30% failure probability in O2 generator; proposes redundant system
 5     2026     Origin: O2 generator pressure fluctuations and overheating first detected
```

The causal chain reveals schedule pressure as the dominant institutional failure mode. Lin's oxygen generator concerns appear as early as Step 5 (2026) and recur through every subsequent timepoint, each time dismissed or deferred by Webb's schedule priorities. The pattern is structural: Lin detects real problems, Webb deprioritizes them, Raj finds supporting issues but hesitates to escalate, and Okafor's authority is insufficient to override the schedule-first culture.

<details>
<summary><b>Full timeline descriptions (LLM-generated)</b></summary>

**Step 0 (2031)**: Ares III crewed Mars mission loses contact during orbital insertion. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell. Trace backward to understand how this disaster was built, decision by decision.

**Step 1 (2030)**: Raj Mehta detects anomalies in the communication system's performance, but instead of reporting them, he decides to work around the issue by implementing a software patch. Meanwhile, Sarah Okafor is dealing with the aftermath of a crew member's sudden departure due to personal reasons, which adds to the workload and stress on the remaining crew. Thomas Webb sees an opportunity to save resources by reducing the mission's communication bandwidth, despite Lin Zhang's concerns about the potential impact on safety.

**Step 2 (2029)**: Lin Zhang discovers a critical design flaw in the oxygen generator during testing, but her concerns are dismissed by Thomas Webb due to schedule pressure. Meanwhile, Raj Mehta is working on a software patch to address a minor issue in the communication system, but his cautious nature makes him hesitant to test it thoroughly. Sarah Okafor is dealing with the aftermath of a crew member's sudden departure due to personal reasons, which adds to the workload and stress on the remaining crew.

**Step 3 (2028)**: Raj Mehta discovers a minor issue in the communication system and decides to address it with a software patch. However, his cautious nature makes him hesitant to test it thoroughly, and he decides to wait for further testing before implementing the patch. Meanwhile, Lin Zhang is working on the oxygen generator design, but her concerns about the system's redundancy are dismissed by Thomas Webb due to the schedule constraints. Sarah Okafor is dealing with the aftermath of a crew member's sudden departure due to personal reasons, which adds to the workload and stress on the remaining crew.

**Step 4 (2027)**: Lin Zhang discovers a critical flaw in the oxygen generator design during testing, but Thomas Webb dismisses her concerns due to the tight schedule and budget constraints. Meanwhile, Raj Mehta is tasked with analyzing the communication system and detects a minor issue, but his cautious nature makes him hesitant to report it. Sarah Okafor is under pressure from NASA leadership to maintain the mission schedule and is forced to prioritize rapid progress over safety margins.

**Step 5 (2026)**: The earliest seeds of the disaster are planted. The oxygen generator's pressure fluctuations and overheating are first detected during initial testing. Lin Zhang flags the issue, but Thomas Webb dismisses it as within acceptable parameters. Raj Mehta finds a minor signal amplification issue in the communications system but is unsure whether to report it given competing priorities. Sarah Okafor pushes for evaluation of both issues but faces pressure to prioritize progress over investigation.

</details>

---

## 4. Sample Dialogs

Every timepoint generates a multi-party dialog with tracked confidence scores and knowledge references. All 4 characters participate in every conversation. 6 dialogs completed successfully, producing 78 turns total.

### Dialog at tp_002_2029 --- Lin confronts Webb about the oxygen generator (first 3 turns shown)

> **Lin Zhang**: Thomas, I've been going over the oxygen generator test results and I think we have a problem.
>
> **Thomas Webb**: What makes you think that, Lin?
>
> **Lin Zhang**: The oxygen generator's CO2 scrubbing efficiency is 30% lower than expected, and I'm seeing some anomalies in the pressure regulator's performance data, it's not just a minor deviation, Thomas.

*(+10 remaining turns --- [full transcript](EXAMPLE_DIALOGS.md#timepoint-2--2029--oxygen-generator-flaw))*

### Dialog at tp_005_2026 --- Origin point: Lin vs. Webb on safety parameters (first 3 turns shown)

> **Thomas Webb**: What's the holdup here, Lin? We're on a tight schedule and I don't see anything in the data that suggests we need to pause testing.
>
> **Lin Zhang**: I'm telling you, Thomas, the oxygen generator's not functioning within acceptable parameters. The pressure's fluctuating wildly, and I'm seeing signs of overheating. We can't just brush this off as a minor issue.
>
> **Lin Zhang**: We can't afford to have a cascade failure on our hands, Thomas. What's the point of meeting the schedule if the system's going to fail the crew when they need it most?

*(+10 remaining turns --- [full transcript](EXAMPLE_DIALOGS.md#timepoint-5--2026--origin-point))*

Context flags applied per dialog: `physical_states`, `emotional_states`, `body_mind_coupling`, `relationship_context`, `knowledge_provenance`, `temporal_awareness`, `per_turn_generation`

### Dialog generation architecture

This run used the per-turn dialog pipeline, where each conversation is generated through a LangGraph steering loop rather than a single LLM call:

1. **Steering agent** selects the next speaker based on narrative goals, current mood, and character proception states (anxiety, withheld knowledge)
2. **Character agent** generates ONE turn using PersonaParams derived from the speaker's tensor state (arousal &rarr; temperature, energy &rarr; max_tokens, behavior_vector &rarr; frequency/presence penalty)
3. **Quality gate** evaluates after each turn or at dialog end --- surface heuristics first, then frontier model semantic evaluation
4. Loop continues until the steering agent ends the dialog or max turns reached

Each character receives a **Fourth Wall context** with two layers: a back layer (true emotional state, suppressed impulses, withheld knowledge --- shapes voice but is not expressed in dialog) and a front layer (filtered knowledge, natural-language relationships --- dialog content drawn from here). In PORTAL mode, front-layer knowledge is filtered by causal ancestry so characters only reference information from timepoints upstream of their position.

### Voice differentiation

Per-turn generation with independent LLM calls per character produces measurably distinct voices. Each character's LLM call uses different generation parameters (temperature, top_p, max_tokens) derived from their current cognitive state.

**Voice distinctiveness scores**: 0.91--0.97 across all entity pairs (measured by lexical and syntactic divergence metrics). The per-turn architecture eliminates the cross-timepoint phrase repetition that characterized the single-call approach by giving each character an independent generation context.

---

## 5. Knowledge Provenance

The system tracks typed exposure events across the simulation. Every fact an entity knows has a source, a timestamp, and a confidence score. Entities can't know things without a tracked exposure event --- anachronisms are structurally prevented.

Each entity receives initial knowledge items from `scene_initialization` and accumulates additional items through dialog-driven exposure events across 6 active timepoints.

### Sample exposure chain

```
[pre_tp_000] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "Ares III mission objectives"

[pre_tp_000] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "Crew member skills and expertise"

[pre_tp_000] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "NASA mission protocols"
```

Each entity receives 3 initial knowledge items at scene initialization. The remaining events are dialog-driven transfers --- information flowing between entities during conversations.

---

## 6. ADPRS Waveform Gating

The ADPRS (Attack, Decay, Peak, Release, Sustain) waveform scheduler evaluates each entity's cognitive activation (&phi;) at each timepoint and maps it to a resolution band. Entities in lower bands skip LLM dialog calls --- their trajectory snapshots are recorded but no tokens are spent.

### Shadow evaluation results

From `datasets/mars_mission_portal/shadow_report.json`:

| Entity | &phi; Range | Predicted Band | Actual Level | Divergent? |
|--------|:-----------:|:--------------:|:------------:|:----------:|
| sarah_okafor | 0.762--1.000 | dialog/trained | dialog | 4/6 (when &phi;=1.0) |
| thomas_webb | 0.769--1.000 | dialog/trained | dialog | 4/6 (when &phi;=1.0) |
| raj_mehta | 0.715--0.744 | dialog | dialog | Never |
| lin_zhang | 0.704--0.710 | dialog | dialog | Never |

**Overall**: 24 evaluations, 8 divergent (33.33%), mean divergence 0.333.

This run shows a structurally clean divergence pattern. Sarah Okafor and Thomas Webb both hit the &phi; ceiling (1.0) at timepoints tp_000 through tp_003, which maps them to `trained` band, but they actually resolve at `dialog`. This accounts for all 8 divergences. At tp_004 and tp_005, their &phi; values drop below 0.77, and all entities predict and resolve at `dialog` with zero divergence. Raj Mehta (&phi; ~0.74) and Lin Zhang (&phi; ~0.71) remain consistently in the `dialog` band throughout.

### Why 33.33% divergence matters

The divergence is entirely driven by two entities hitting the &phi; ceiling at 1.0 during the first four timepoints (the disaster and its immediate precursors). The ADPRS system is conservative: it predicts these maximally-activated entities should receive `trained` resolution (the most expensive), but the simulation normalizes them to `dialog` to control cost. This is soft budget mode working as intended --- spending enough to maintain quality without escalating to the highest tier when `dialog` is sufficient.

---

## 7. Fidelity Strategy

The system plans a fidelity budget before execution, then adapts during the run. The `--portal-quick` flag reduces backward steps from 10 to 5, cutting the fidelity budget proportionally.

### Planned vs. actual

| Metric | Planned | Actual |
|--------|---------|--------|
| Fidelity schedule | tensor &rarr; scene &rarr; graph &rarr; dialog | All `dialog` |
| Token budget | 200,000 | 317,796 |
| Budget compliance | -- | 1.6x over (soft budget mode) |
| Resolution distribution | mixed | All entities at `dialog` |
| Cost estimate | ~$0.10 | $0.18 |

### Resolution escalation

The planner starts conservative, but the adaptive threshold triggered upgrades --- PORTAL backward reasoning requires full entity context to score candidate antecedents. All 4 entities were elevated to `dialog` resolution across all 6 timepoints.

This demonstrates soft budget mode working as intended: the system spent what the scenario required rather than truncating quality to hit a token cap. For cost-sensitive use, switch to hard budget mode: `./run.sh run --budget 0.20 mars_mission_portal --portal-quick`

---

## 8. Entity Tensors

Each entity carries a multi-dimensional cognitive and physical state tensor, updated at every timepoint. These are the final states after 6 timepoints of simulation.

<details>
<summary><b>Sarah Okafor --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": 0.47,
  "emotional_arousal": 0.57,
  "energy_budget": 124.4,
  "initial_knowledge": ["Ares III mission objectives", "Crew member skills and expertise", "NASA mission protocols"]
}
```

Okafor's positive valence (+0.47) with moderate arousal (0.57) shows a commander who remains engaged and optimistic despite mounting safety concerns. Her energy (124.4, the highest in the cast) reflects sustained engagement across all timepoints. Her dialog pattern --- addressing all teammates by name, steering toward compromise, framing decisions as team obligations --- produces a leader who mediates between engineering rigor and institutional pressure.

</details>

<details>
<summary><b>Raj Mehta --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": -0.20,
  "emotional_arousal": 0.81,
  "energy_budget": 123.7,
  "initial_knowledge": ["Ares III spacecraft systems", "Emergency procedures", "Crew member skills and expertise"]
}
```

Mehta's negative valence (-0.20) with high arousal (0.81) captures an engineer in sustained discomfort: his anomaly detections are acknowledged but he hesitates to escalate them forcefully. His high energy (123.7) reflects the cost of maintaining technical vigilance while implementing workaround patches rather than root-cause fixes. His conflict-averse nature surfaces in dialog as hedging ("I'm not sure if it's worth reporting given the current priorities") and deference to authority.

</details>

<details>
<summary><b>Lin Zhang --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": -0.20,
  "emotional_arousal": 0.94,
  "energy_budget": 116.7,
  "initial_knowledge": ["Ares III spacecraft systems", "Anomaly detection procedures", "Crew member skills and expertise"]
}
```

Zhang has the highest arousal (0.94) in the cast --- the most activated character by this measure. Her negative valence (-0.20) combined with near-maximum arousal drives her repeated confrontations with Webb, citing specific data: 30% CO2 scrubbing efficiency loss, 30% failure probability, 10% pressure variance, 5-degree hourly temperature spikes. The tension between "data-driven" precision and institutional resistance produces a character who escalates with hard numbers when her warnings are dismissed. Her energy (116.7, the lowest in the cast) reflects the draining cost of being the persistent technical conscience.

</details>

<details>
<summary><b>Thomas Webb --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": -0.17,
  "emotional_arousal": 0.78,
  "energy_budget": 118.4,
  "initial_knowledge": ["Ares III mission objectives", "NASA mission protocols", "Budget and resource constraints"]
}
```

Webb's slightly negative valence (-0.17) with moderately high arousal (0.78) reveals a director whose schedule-first stance generates friction that he himself absorbs. His energy (118.4) reflects the effort of holding the timeline against multiple sources of pushback. His dialog pattern --- "We can't afford to...", demanding deliverables "by the end of the day", redirecting to schedule and budget --- gives his dismissals an institutional logic that makes them hard to override.

</details>

---

## 9. Mechanism Usage

15 of the 19 available mechanisms fired during this run. The counts below show which subsystems did the most work.

| Mechanism | Function | Calls | What it does |
|-----------|----------|:-----:|-------------|
| M3 | `_build_knowledge_from_exposures` | 24 | Build knowledge graph from exposure events (4 entities x 6 timepoints) |
| M8 | `couple_pain_to_cognition` | 24 | Physical state &rarr; cognitive state coupling (embodied cognition) |
| M11 | `synthesize_dialog` | 6 | Per-character turn generation with LangGraph steering (one dialog per timepoint) |
| M11 | `dialog_steering` | ~78 | Steering agent: next-speaker selection, mood shifts, narrative evaluation |
| M11 | `character_generation` | ~78 | Independent per-character LLM calls with PersonaParams |
| M11 | `dialog_quality_gate` | 6 | Semantic quality evaluation (surface + frontier model) |
| M15 | `post_dialog_proception` | 6 | Post-dialog episodic memory generation and rumination |
| M19 | `extract_knowledge_from_dialog` | 6 | Post-dialog knowledge extraction, creating new exposure events |
| M6 | `compress` | 4 | Tensor compression via PCA/SVD into 8D vectors |
| M5 | `synthesize_response` | 4 | On-demand resolution elevation (lazy fidelity) |
| M9 | `detect_entity_gap` | 4 | Missing entity auto-detection in scenes |
| M13 | `update_relationships` | 6 | Relationship state tracking between entities |
| M2 | `progressive_training_check` | 4 | Entity quality improvement tracking |
| M4 | `validate_biological_constraints` | 4 | Constraint enforcement (resource + biological validation) |
| M6 | `create_baseline_tensor` | 4 | Initial tensor creation for each entity |
| M6 | `populate_tensor_llm_guided` | 4 | LLM-guided tensor population with personality/knowledge |
| M7 | `build_causal_history` | 6 | Causal history assembly for each timepoint |
| M1+M17 | `determine_fidelity_temporal_strategy` | 2 | Joint fidelity + temporal mode planning |
| M1 | `assign_resolutions` / `build_graph` | 2 | Resolution assignment and relationship graph construction |
| M17 | `orchestrate` | 1 | Portal backward orchestration (5 steps, 3 candidates each) |

### Mechanism interaction chain

```
M17 (portal orchestrate)
 +-- generates 3 candidates per step, scores with 405B judge (no mini-sim)
     +-- M1+M17 (fidelity+temporal planning)
         +-- M6 (create tensors) -> M6 (populate via LLM) -> M6 (compress)
             +-- M3 (build knowledge from exposures)
                 +-- M8 (couple physical -> cognitive state)
                     +-- Params2Persona (entity state -> LLM params per character)
                     +-- Fourth Wall Context (two-layer: back shapes voice, front provides content)
                     +-- PORTAL Knowledge Stripping (causal ancestry filtering)
                     +-- M11 (per-turn dialog via LangGraph)
                         +-- steering_node (select speaker, manage narrative)
                         +-- character_node (independent LLM call per character)
                         +-- quality_gate_node (surface + semantic evaluation)
                         +-- M15 (post-dialog proception: episodic memory, rumination)
                         +-- M19 (extract knowledge from dialog)
                             +-- M3 (update knowledge graph) -> loop
```

---

## 10. Training Data

This run generated **20 structured training examples** (prompt/completion pairs). Each example includes the entity's full causal history (M7), relationship context (M13), knowledge provenance (M3), and quantitative state (M6).

### Example training prompt structure

```
=== CAUSAL HISTORY (M7) ===
Timeline leading to current moment (3 events):
  tp_000_2031: Mission failure during orbital insertion...
  tp_001_2030: Raj patches comm anomalies, Webb reduces bandwidth...
  tp_002_2029: Lin discovers oxygen generator design flaw...

=== RELATIONSHIP CONTEXT (M13) ===
Relationships with entities present:
  lin_zhang: collaborative (trust: 0.65, alignment: 0.55)
  sarah_okafor: cooperative (trust: 0.70, alignment: 0.60)
  thomas_webb: tense (trust: 0.40, alignment: 0.30)

=== KNOWLEDGE PROVENANCE (M3) ===
Primary sources: scene_initialization (3 items)
Recent: "oxygen generator design has critical flaw" (from lin_zhang, conf: 0.9)

=== ENTITY STATE (M6) ===
raj_mehta at T0:
  Physical: energy 123.7/150
  Cognitive: 3 knowledge items, -0.20 valence
  Emotional: Arousal 0.81

=== PREDICTION TASK ===
Predict: new knowledge, energy change, emotional impact, causal reasoning.
```

### Training data quality

The training data formatter produces varied, entity-specific data:

| Metric | Value |
|--------|-------|
| Energy values | 116.7--124.4 (entity-specific) |
| Arousal values | 0.57--0.94 (entity-specific) |
| Valence values | -0.20--+0.47 (entity-specific) |
| Mean energy change | -13.0 |

---

## 11. Run Metadata

<details>
<summary><b>Full run record</b></summary>

| Field | Value |
|-------|-------|
| run_id | `run_20260218_091456_55697771` |
| template_id | `mars_mission_portal` |
| started_at | 2026-02-18T09:14:56 |
| completed_at | 2026-02-18T09:59:24 |
| duration | 2,668s (~44 min) |
| causal_mode | portal |
| entities_created | 4 |
| timepoints_created | 6 |
| training_examples | 20 |
| cost_usd | $0.18 |
| llm_calls | 479 |
| tokens_used | 317,796 |
| status | completed |
| portal_quick | true (5 backward steps) |
| narrative_exports | markdown, json, pdf |

</details>

### Output files

```
datasets/mars_mission_portal/
  narrative_20260218_095924.markdown   (narrative export)
  narrative_20260218_095924.json       (structured data)
  narrative_20260218_095924.pdf        (PDF export)
  shadow_report.json                   (ADPRS evaluation)
```

### Cost and efficiency: full vs. quick mode

This run used `--portal-quick` to reduce backward steps from 10 to 5. Comparison with the previous full run:

| Metric | Full Run (Feb 17) | Quick Run (Feb 18) | Change |
|--------|-------------------|-------------------|--------|
| Cost | $0.49 | $0.18 | -63% |
| LLM calls | 912 | 479 | -47% |
| Tokens | 900K | 318K | -65% |
| Backward steps | 10 | 5 | -50% |
| Timepoints | 11 | 6 | -45% |
| Dialogs / turns | 11 / 143 | 6 / 78 | -45% |
| Training examples | 40 | 20 | -50% |
| Duration | 6,183s (~103 min) | 2,668s (~44 min) | -57% |

The `--portal-quick` flag is designed for fast demos and iteration. It halves the backward steps while maintaining the same per-step quality (3 candidates, 405B scoring). For full depth, omit the flag: `./run.sh run mars_mission_portal` (~$0.40--$0.60).

### Models used

All inference via OpenRouter. MIT/Apache 2.0/Llama-licensed models only --- all permit commercial synthetic data generation.

| Model | License | Role |
|-------|---------|------|
| Llama 3.1 70B Instruct | Llama | Per-character dialog generation, entity population, knowledge extraction, relevance scoring |
| Llama 3.1 405B Instruct | Llama | Portal candidate scoring, dialog steering, semantic quality evaluation |

---

## 12. What You Can Do Next

### Reproduce this run

```bash
git clone https://github.com/timepoint-ai/timepoint-pro.git
cd timepoint-pro
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here

./run.sh run mars_mission_portal --portal-quick    # ~$0.15-$0.25
./run.sh run mars_mission_portal                   # Full depth: ~$0.40-$0.60
```

### Run convergence testing

```bash
./run.sh convergence e2e mars_mission_portal          # Run 3x + analyze
./run.sh convergence e2e --runs 5 mars_mission_portal # Run 5x
./run.sh convergence history                          # Past results
```

### Query the results

```python
from evaluation.convergence import compute_outcome_convergence

results = compute_outcome_convergence("mars_mission_portal", min_runs=3)
print(f"Role stability: {results['role_stability']}")
print(f"Outcome similarity: {results['outcome_mean_similarity']}")
```

### Export to additional formats

```bash
./run.sh export last --format jsonl       # ML training pipelines
./run.sh export last --format fountain    # Professional screenplay (.fountain)
```

| Format | Use Case |
|--------|----------|
| **JSONL** | Streaming ML training data (prompt/completion pairs) |
| **JSON / CSV / SQLite** | Analysis, querying, visualization |
| **Fountain / PDF** | Industry-standard screenplays (Courier 12pt, proper margins) |
| **Parquet** | Columnar format for ML pipelines (via `oxen_integration`) |
| **Markdown** | Human-readable narrative (auto-generated) |

### Chat with a persona about the results

```bash
./run.sh chat --persona AGENT2 --context datasets/mars_mission_portal/narrative_*.markdown \
  --batch "As an aerospace engineer, what concerns you about this mission's failure chain?"
```

### Run a different template

```bash
./run.sh list                                         # List all 21 templates
./run.sh run castaway_colony_branching                # BRANCHING: 8 entities, all 19 mechanisms
./run.sh run hound_shadow_directorial                 # DIRECTORIAL: 5-act arc engine, camera system
./run.sh run agent4_elk_migration                     # CYCLICAL: prophecy system, causal loops
./run.sh run convergence_simple                       # Cheapest run: $0.01, 2 entities
```

---

## 13. Port to Oxen.ai

Training data auto-uploads to [Oxen.ai](https://oxen.ai) when `OXEN_API_KEY` is set. Without it, everything saves locally.

### Auto-upload during a run

```bash
export OPENROUTER_API_KEY=your_key
export OXEN_API_KEY=your_oxen_token

./run.sh run mars_mission_portal --portal-quick
# -> local JSONL + SQLite as usual
# -> auto-uploads training_*.jsonl to Oxen.ai with commit history
# -> prints dataset URL and fine-tune URL on completion
```

### Programmatic upload and versioning

```python
from oxen_integration import OxenClient

client = OxenClient(namespace="your-username", repo_name="mars-mission-data")

# Upload a dataset
result = client.upload_dataset("datasets/mars_mission_portal/training_20260218.jsonl",
                               commit_message="Mars mission PORTAL run (quick mode)")
print(result.dataset_url)    # View on Oxen Hub
print(result.finetune_url)   # One-click fine-tune

# Branch management for experiments
client.create_branch("experiment-v2", from_branch="main")
client.switch_branch("experiment-v2")
```

### Fine-tuning pipeline

```python
from oxen_integration import FineTuneConfig, FineTuneLauncher, DataFormatter

# Validate and format training data
formatter = DataFormatter()
formatted = formatter.to_chat_format(training_examples)
validation = formatter.validate_dataset(formatted)

# Configure and launch fine-tuning
config = FineTuneConfig(
    dataset_path="datasets/mars_mission_portal/training_20260218.jsonl",
    base_model="Qwen/Qwen2.5-1.5B-Instruct",
    num_epochs=3, batch_size=4
)
launcher = FineTuneLauncher(client)
job = launcher.prepare_and_approve(config, "training_data.jsonl")
instructions = launcher.launch_via_notebook(job)
```

### Four specialized data formatters

| Formatter | Produces | Use Case |
|-----------|----------|----------|
| **EntityEvolutionFormatter** | State progression pairs (before &rarr; after) | Train models to predict character arcs |
| **DialogSynthesisFormatter** | Multi-turn conversation pairs | Train conversational models |
| **KnowledgeFlowFormatter** | Information propagation patterns | Train knowledge extraction models |
| **RelationshipDynamicsFormatter** | Relationship evolution sequences | Train social dynamics models |

---

## 14. API & Programmatic Access

### REST API

```bash
./run.sh api start          # Start server on port 8080
./run.sh dashboard          # Start dashboard backend on port 8000
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/runs` | GET | List simulation runs (paginated) |
| `/api/run/{run_id}` | GET | Full run details |
| `/api/narrative/{run_id}` | GET | Narrative report |
| `/api/screenplay/{run_id}` | GET | Screenplay in Fountain format |
| `/api/dialogs/{run_id}` | GET | Dialog transcripts |
| `/api/templates` | GET | All templates with metadata |
| `/api/mechanisms` | GET | All 19 mechanisms with descriptions |
| `/api/convergence-stats` | GET | Convergence analysis results |

### CLI options

```bash
# Model selection
./run.sh run --model deepseek/deepseek-chat board_meeting   # Specific model
./run.sh run --free board_meeting                           # Best free model ($0)

# Parallelism & cost
./run.sh run --parallel 4 quick              # 4 concurrent templates
./run.sh run --dry-run board_meeting         # Cost estimate without running
./run.sh run --budget 50.00 quick            # Hard budget cap

# Filtering
./run.sh run --tier quick                    # By complexity tier
./run.sh run --category portal               # By category

# Natural language interface
./run.sh run --nl "CEO announces mandatory salary cuts due to market downturn"
```

### Docker sandbox

```bash
./claude-container.sh up       # Build + start + launch Claude Code in sandbox
./claude-container.sh shell    # Interactive shell
```

Network-isolated container with iptables firewall, allowlisted API endpoints, and `.env` injection.

---

*Generated from run `run_20260218_091456_55697771` on February 18, 2026. All data extracted from `metadata/runs.db` and `datasets/mars_mission_portal/`. Every number in this document comes from the database, not from documentation --- if you run the same template, you'll get different numbers but the same structural patterns.*
