# Example Run: Ares III Mars Mission Portal

**[Back to README](README.md)** | **[Full Dialog Transcript (143 turns)](EXAMPLE_DIALOGS.md)** | Run ID: `run_20260217_074855_c7661141` | Template: `mars_mission_portal`

A complete PORTAL-mode simulation tracing backward from a catastrophic Mars mission failure in 2031 to its institutional origins in 2026. Every number, dialog line, and graph edge below was produced by a single `./run.sh run mars_mission_portal` invocation on February 17, 2026.

---

## At a Glance

| | |
|---|---|
| **Mode** | PORTAL (backward temporal reasoning) |
| **Timespan** | 2031 &rarr; 2026 (5 years, 10 backward steps) |
| **Entities** | 4 humans, all reaching TRAINED resolution |
| **Dialogs** | 11 conversations, 143 turns |
| **Training examples** | 40 structured prompt/completion pairs |
| **Mechanisms fired** | 15 of 19 |
| **ADPRS waveform gating** | 44 evaluations, 18 divergent (40.91%) |
| **Cost** | $0.49 &bull; 912 LLM calls &bull; 900K tokens |
| **Duration** | 6,183s (~103 minutes) |

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

The result: a 5-year causal graph showing how schedule pressure overruled safety concerns at every level, how engineering warnings were systematically dismissed, and how the crew's own dialog reveals the tensions that built toward catastrophe. Produced for under fifty cents.

### How PORTAL backward inference works

```
Known endpoint (2031): Mission failure
                |
    Generate 3 candidate causes
    Score each candidate with 405B judge (states only, no mini-sim)
    Select best candidate
                |
        Step back 6 months
        Repeat 10 times
                |
Result: Causal chain from Jan 2026 -> 2031
```

Each backward step costs ~$0.04 (3 candidates x 405B scoring, no disposable dialog). The system spent $0.49 total across 912 LLM calls to produce 11 timepoints, 11 dialogs with 143 turns, and 40 training examples.

---

## 2. Cast of Characters

Four crew members, each with tracked cognitive state, emotional arcs, and distinct knowledge bases. All defined in the template's `entity_roster` and carried through the full simulation.

| Character | Role | Final Valence | Final Arousal | Final Energy | Personality Traits |
|-----------|------|:---:|:---:|:---:|---|
| **Sarah Okafor** | Mission Commander | +0.27 | 0.96 | 109.2 | authoritative, warm, decisive, diplomatic, empathetic, leadership |
| **Raj Mehta** | Flight Engineer | -0.26 | 0.97 | 119.4 | analytical, reserved, cautious, technical, conflict-averse, precise |
| **Lin Zhang** | Systems Engineer | -0.50 | 1.00 | 109.2 | technical, precise, frustrated, data-driven, stubborn, intense |
| **Thomas Webb** | Mission Director | +0.24 | 1.00 | 119.3 | strategic, results-oriented, pragmatic, commanding, cold, business |

**Emotional arcs**: Zhang's deeply negative valence (-0.50) and maximum arousal (1.00) make her the most strained character in this run --- driven by repeated frustration at having her technical warnings dismissed. Webb's slightly positive valence (+0.24) at maximum arousal (1.00) with "commanding, cold" traits captures a director who maintains confidence even as his schedule-first decisions build toward catastrophe. Okafor's positive valence (+0.27) with high arousal (0.96) and "authoritative, warm, diplomatic" traits show a commander who tries to bridge the engineering-management divide. Mehta's negative valence (-0.26) with near-maximum arousal (0.97) reflects a cautious, conflict-averse engineer accumulating quiet frustration as his anomaly detections are sidelined.

---

## 3. Backward Timeline

Portal mode traces backward from the 2031 failure. Each step was selected from 3 candidates scored by the 405B judge. All 4 entities are present at every timepoint.

```
Step   Year     Event
 0     2031     Mission failure: loses contact during orbital insertion
 1     Jul 30   Critical testing challenge, Lin detects anomalies, Webb prioritizes schedule
 2     Jan 30   Sarah and Lin attend risk management workshop, face resistance from Webb
 3     Jul 29   Lin discovers critical oxygen generator design flaw, overruled by Webb
 4     Jan 29   Raj detects anomaly in oxygen generator, NASA announces 5% budget cut
 5     Jul 28   Lin detects anomaly, dismissed by Webb, Raj tasked with workaround
 6     Jan 28   Lin discovers design flaw during routine review, Webb skeptical
 7     Jul 27   Raj develops workaround skills, Lin provides guidance on design specs
 8     Jan 27   Lin's concerns validated by separate system failure, Sarah requests review
 9     Jul 26   Lin's research breakthrough on system redundancy, tension between Webb/Okafor
10     Jan 26   Raj detects minor anomaly, Lin recognizes implications, Webb focuses on schedule
```

The causal chain reveals schedule pressure as the dominant institutional failure mode. Lin's oxygen generator design flaw warnings appear as early as Step 6 (January 2028) and recur through Step 3 (July 2029) and Step 1 (July 2030), each time dismissed by Webb's schedule priorities. The 5% budget cut at Step 4 compounds the problem by giving Webb additional justification for rejecting costly remediations. Even Okafor's attempts to address the issue through formal channels (a risk management workshop at Step 2) cannot overcome the institutional momentum. The pattern is structural: Lin and Raj detect real problems, Webb deprioritizes them, and Okafor's authority is insufficient to override the schedule-first culture.

<details>
<summary><b>Full timeline descriptions (LLM-generated)</b></summary>

**Step 0 (2031)**: Ares III crewed Mars mission loses contact during orbital insertion. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell. Trace backward to understand how this disaster was built, decision by decision.

**Step 1 (July 2030)**: Critical testing challenge as the mission nears final milestones. Lin detects anomalies in life support performance data, but Webb prioritizes the launch schedule over additional investigation. The tension between engineering rigor and timeline pressure reaches its peak.

**Step 2 (January 2030)**: Sarah and Lin attend a risk management workshop, returning with recommendations for additional safety reviews. Webb resists, citing cost and schedule impact. The workshop findings validate Lin's earlier concerns but fail to change institutional priorities.

**Step 3 (July 2029)**: Lin discovers a critical design flaw in the oxygen generator subsystem. She escalates with detailed simulation data, but Webb overrules the recommended redesign, deeming it too expensive and time-consuming given the existing schedule.

**Step 4 (January 2029)**: Raj detects an anomaly in oxygen generator performance during routine testing. Simultaneously, NASA announces a 5% budget cut across all active programs, tightening constraints and giving Webb further justification for schedule-first decisions.

**Step 5 (July 2028)**: Lin detects another anomaly in the oxygen generator, this time in a different subsystem. Webb dismisses the finding and tasks Raj with developing a workaround rather than addressing the root cause.

**Step 6 (January 2028)**: Lin discovers a design flaw during a routine engineering review. She documents the issue and presents it to Webb, who is skeptical of the severity and declines to allocate resources for further investigation.

**Step 7 (July 2027)**: Raj develops workaround skills for the oxygen generator issues, with Lin providing technical guidance on the design specifications. The team is adapting to known problems rather than resolving them.

**Step 8 (January 2027)**: Lin's earlier concerns are partially validated when a separate system failure occurs during ground testing. Sarah requests a formal review of all flagged issues, but the review scope is limited by budget constraints.

**Step 9 (July 2026)**: Lin achieves a research breakthrough on system redundancy that could address the emerging design concerns. However, tension between Webb and Okafor over resource allocation prevents the research from being applied to the mission hardware.

**Step 10 (January 2026)**: Raj detects a minor anomaly during early oxygen generator testing. Lin recognizes the potential implications and begins documenting the issue. Webb focuses on schedule milestones and treats the anomaly as within acceptable tolerances.

</details>

---

## 4. Sample Dialogs

Every timepoint generates a multi-party dialog with tracked confidence scores and knowledge references. All 4 characters participate in every conversation. 11 dialogs completed successfully, producing 143 turns total.

### Dialog at tp_001_2030 --- Webb dismissing Lin's 97.42% failure probability (first 3 turns shown)

> **Thomas Webb**: Alright, let's get down to business. We've got a schedule to keep...
>
> **Lin Zhang**: Sir, I've run the simulations and the oxygen generator's failure rate is still within the 5% margin, but that's not the point, the point is the anomaly I detected at 3:47 AM indicates a 97.42% probability of system failure...
>
> **Thomas Webb**: I don't pay you to run simulations, Lin, I pay you to meet the mission requirements...

*(+remaining turns --- [full transcript](EXAMPLE_DIALOGS.md#timepoint-1--july-2030))*

### Dialog at tp_005_2028 --- Lin confronting Webb about 3.5% deviation (first 3 turns shown)

> **Lin Zhang**: Oxygen generator's performance is off, Thomas, I'm looking at a 3.5% deviation from expected output, that's not within our acceptable margin
>
> **Thomas Webb**: Lin, we can't afford to re-run tests now, we're already on a tight schedule and NASA just announced a 5% budget cut...

*(+remaining turns --- [full transcript](EXAMPLE_DIALOGS.md#timepoint-5--july-2028))*

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

**Voice distinctiveness scores**: 0.92--0.96 across all entity pairs (measured by lexical and syntactic divergence metrics). This is a significant improvement over the previous run's 0.58--0.89 range. The per-turn architecture eliminates the cross-timepoint phrase repetition that characterized the single-call approach by giving each character an independent generation context.

**Quality gate scores**: All 1.00 across all 11 dialogs (surface + frontier model semantic evaluation).

---

## 5. Knowledge Provenance

The system tracks typed exposure events across the simulation. Every fact an entity knows has a source, a timestamp, and a confidence score. Entities can't know things without a tracked exposure event --- anachronisms are structurally prevented.

Each entity receives initial knowledge items from `scene_initialization` and accumulates additional items through dialog-driven exposure events across 11 active timepoints.

### Sample exposure chain

```
[pre_tp_001] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "Mission objectives and timelines"

[pre_tp_001] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "Crew member skills and strengths"

[pre_tp_001] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "NASA's expectations for the mission"
```

Each entity receives initial knowledge items at scene initialization. The remaining events are dialog-driven transfers --- information flowing between entities during conversations.

---

## 6. ADPRS Waveform Gating

The ADPRS (Attack, Decay, Peak, Release, Sustain) waveform scheduler evaluates each entity's cognitive activation (&phi;) at each timepoint and maps it to a resolution band. Entities in lower bands skip LLM dialog calls --- their trajectory snapshots are recorded but no tokens are spent.

### Shadow evaluation results

From `datasets/mars_mission_portal/shadow_report.json`:

| Entity | &phi; Range | Predicted Band | Actual Level | Divergent? |
|--------|:-----------:|:--------------:|:------------:|:----------:|
| thomas_webb | 0.750--1.000 | dialog/trained | dialog | 11/11 for trained predictions |
| lin_zhang | 0.592 | graph | dialog | Always (11/11) |
| raj_mehta | 0.692--0.705 | dialog | dialog | Never |
| sarah_okafor | 0.795--0.799 | dialog | dialog | Never |

**Overall**: 44 evaluations, 18 divergent (40.91%), mean divergence 0.409.

This run shows a structurally informative divergence pattern. Lin Zhang's &phi; (0.592) consistently maps to `graph` band, but she actually resolves at `dialog` --- every single timepoint. This accounts for 11 of the 18 divergences. Thomas Webb oscillates between `dialog` and `trained` predictions depending on the timepoint, contributing the remaining divergences when his &phi; reaches 1.0 (the maximum) but resolves at `dialog`.

### Why 40.91% divergence matters

The divergence rate is higher than previous runs because two characters --- Zhang and Webb --- both push against their ADPRS boundaries in opposite directions. Zhang's low &phi; (the lowest in the cast at 0.592) suggests she should receive less computational depth, but the system recognizes her dialog contributions are essential and keeps her at full resolution. Webb's occasional &phi; spikes to 1.0 reflect moments of maximum cognitive activation, but the system normalizes him to `dialog` rather than escalating to the more expensive `trained` band. The ADPRS system is conservative: it would rather spend more on a low-activation entity than miss her contributions, and it would rather save cost on a high-activation entity whose dialog-level output is already sufficient.

---

## 7. Fidelity Strategy

The system plans a fidelity budget before execution, then adapts during the run. The gap between planned and actual reveals where the scenario demanded more detail than expected.

### Planned vs. actual

| Metric | Planned | Actual |
|--------|---------|--------|
| Fidelity schedule | tensor &rarr; scene &rarr; graph &rarr; dialog | All `trained` |
| Token budget | 30,000 | 900,072 |
| Budget compliance | -- | 30x over (soft budget mode) |
| Resolution distribution | mixed | All entities at `trained` |
| Cost estimate | $0.067 | $0.49 |

### Resolution escalation

The planner starts conservative:
```
Timepoint:   1      2      3      4      5      6      7      8      9      10
Planned:   tensor tensor tensor scene  scene  scene  graph  graph  dialog dialog
```

But the adaptive threshold (0.75) triggered upgrades at every step --- PORTAL backward reasoning requires full entity context to score candidate antecedents. All 4 entities were elevated to `trained` resolution (maximum fidelity).

This demonstrates soft budget mode working as intended: the system spent what the scenario required rather than truncating quality to hit a token cap. For cost-sensitive use, switch to hard budget mode: `./run.sh run --budget 0.50 mars_mission_portal`

---

## 8. Entity Tensors

Each entity carries a multi-dimensional cognitive and physical state tensor, updated at every timepoint. These are the final states after 11 timepoints of simulation.

<details>
<summary><b>Sarah Okafor --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": 0.27,
  "emotional_arousal": 0.96,
  "energy_budget": 109.2,
  "personality_traits": ["authoritative", "warm", "decisive", "diplomatic", "empathetic", "leadership"]
}
```

Okafor's positive valence (+0.27) with high arousal (0.96) shows a commander who remains engaged and hopeful despite the mounting safety concerns. Her six personality traits --- anchored by "authoritative" and "warm" --- produce a leader who acknowledges engineering concerns with genuine empathy while trying to maintain institutional cohesion. Her energy (109.2) reflects sustained engagement across all timepoints. The "diplomatic, empathetic" traits drive her repeated attempts to bridge the gap between Lin's warnings and Webb's schedule pressure.

</details>

<details>
<summary><b>Raj Mehta --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": -0.26,
  "emotional_arousal": 0.97,
  "energy_budget": 119.4,
  "personality_traits": ["analytical", "reserved", "cautious", "technical", "conflict-averse", "precise"]
}
```

Mehta's negative valence (-0.26) with near-maximum arousal (0.97) captures an engineer in sustained distress: his anomaly detections are acknowledged but never prioritized. His high energy (119.4) reflects the cost of maintaining technical vigilance while being tasked with workarounds rather than root-cause fixes. The "analytical, precise" traits produce his specific data citations in dialog, while "conflict-averse" explains why his escalations are measured rather than forceful.

</details>

<details>
<summary><b>Lin Zhang --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": -0.50,
  "emotional_arousal": 1.00,
  "energy_budget": 109.2,
  "personality_traits": ["technical", "precise", "frustrated", "data-driven", "stubborn", "intense"]
}
```

Zhang has the most negative valence (-0.50) and maximum arousal (1.00) in the cast --- the most distressed character by every measure. Her trait combination of "frustrated," "stubborn," and "intense" drives her repeated confrontations with Webb, citing specific failure probabilities (97.42%) and deviation percentages (3.5%). The tension between "data-driven/precise" and "frustrated/intense" produces a character who escalates with hard numbers when her warnings are dismissed. Her energy (109.2) matches Okafor's, showing that frustration and diplomatic engagement cost the same amount of sustained effort.

</details>

<details>
<summary><b>Thomas Webb --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": 0.24,
  "emotional_arousal": 1.00,
  "energy_budget": 119.3,
  "personality_traits": ["strategic", "results-oriented", "pragmatic", "commanding", "cold", "business"]
}
```

Webb's slightly positive valence (+0.24) at maximum arousal (1.00) reveals a director who maintains confidence in his approach even as the evidence mounts against it. His high energy (119.3) matches Mehta's, reflecting the effort required to hold the schedule-first line against multiple sources of pushback. The "commanding, cold, business" traits produce his dismissive responses to technical concerns --- "I don't pay you to run simulations" --- while "strategic, pragmatic" gives his dismissals an institutional logic that makes them hard to override.

</details>

---

## 9. Mechanism Usage

15 of the 19 available mechanisms fired during this run. The counts below show which subsystems did the most work.

| Mechanism | Function | Calls | What it does |
|-----------|----------|:-----:|-------------|
| M3 | `_build_knowledge_from_exposures` | 44 | Build knowledge graph from exposure events (4 entities x 11 timepoints) |
| M8 | `couple_pain_to_cognition` | 44 | Physical state &rarr; cognitive state coupling (embodied cognition) |
| M11 | `synthesize_dialog` | 11 | Per-character turn generation with LangGraph steering (one dialog per timepoint) |
| M11 | `dialog_steering` | ~143 | Steering agent: next-speaker selection, mood shifts, narrative evaluation |
| M11 | `character_generation` | ~143 | Independent per-character LLM calls with PersonaParams |
| M11 | `dialog_quality_gate` | 11 | Semantic quality evaluation (surface + frontier model) |
| M15 | `post_dialog_proception` | 11 | Post-dialog episodic memory generation and rumination |
| M19 | `extract_knowledge_from_dialog` | 11 | Post-dialog knowledge extraction, creating new exposure events |
| M6 | `compress` | 8 | Tensor compression via PCA/SVD into 8D vectors |
| M5 | `synthesize_response` | 6 | On-demand resolution elevation (lazy fidelity) |
| M9 | `detect_entity_gap` | 6 | Missing entity auto-detection in scenes |
| M13 | `update_relationships` | 11 | Relationship state tracking between entities |
| M2 | `progressive_training_check` | 4 | Entity quality improvement tracking |
| M4 | `validate_biological_constraints` | 4 | Constraint enforcement (resource + biological validation) |
| M6 | `create_baseline_tensor` | 4 | Initial tensor creation for each entity |
| M6 | `populate_tensor_llm_guided` | 4 | LLM-guided tensor population with personality/knowledge |
| M7 | `build_causal_history` | 11 | Causal history assembly for each timepoint |
| M1+M17 | `determine_fidelity_temporal_strategy` | 2 | Joint fidelity + temporal mode planning |
| M1 | `assign_resolutions` / `build_graph` | 2 | Resolution assignment and relationship graph construction |
| M17 | `orchestrate` | 1 | Portal backward orchestration (10 steps, 3 candidates each) |

Note: M15 (post-dialog proception) now fires for the first time in a documented run, generating episodic memories and rumination states after each dialog. This was not active in the previous run.

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

This run generated **40 structured training examples** (prompt/completion pairs). Each example includes the entity's full causal history (M7), relationship context (M13), knowledge provenance (M3), and quantitative state (M6).

### Example training prompt structure

```
=== CAUSAL HISTORY (M7) ===
Timeline leading to current moment (3 events):
  tp_000_2031: Mission failure during orbital insertion...
  tp_001_2030: Critical testing challenge, Lin detects anomalies...
  tp_002_2030: Sarah and Lin attend risk management workshop...

=== RELATIONSHIP CONTEXT (M13) ===
Relationships with entities present:
  lin_zhang: collaborative (trust: 0.65, alignment: 0.55)
  sarah_okafor: cooperative (trust: 0.70, alignment: 0.60)
  thomas_webb: tense (trust: 0.40, alignment: 0.30)

=== KNOWLEDGE PROVENANCE (M3) ===
Primary sources: scene_initialization (3 items), lin_zhang (2 items)
Learning modes: experienced (70%), told (30%)
Recent: "oxygen generator design has critical flaw" (from lin_zhang, conf: 0.9)

=== ENTITY STATE (M6) ===
raj_mehta at T0:
  Physical: energy 119.4/150
  Cognitive: knowledge items, -0.26 valence
  Emotional: Arousal 0.97

=== PREDICTION TASK ===
Predict: new knowledge, energy change, emotional impact, causal reasoning.
```

### Training data quality

The training data formatter produces varied, entity-specific data:

| Metric | Value |
|--------|-------|
| Energy values | 109.2--119.4 (entity-specific) |
| Arousal values | 0.96--1.00 (entity-specific) |
| Valence values | -0.50--+0.27 (entity-specific) |
| Personality trait count | 6 per entity |

---

## 11. Run Metadata

<details>
<summary><b>Full run record</b></summary>

| Field | Value |
|-------|-------|
| run_id | `run_20260217_074855_c7661141` |
| template_id | `mars_mission_portal` |
| started_at | 2026-02-17T07:48:55 |
| completed_at | 2026-02-17T09:31:57 |
| duration | 6,183s (~103 min) |
| causal_mode | portal |
| entities_created | 4 |
| timepoints_created | 11 |
| training_examples | 40 |
| cost_usd | $0.49 |
| llm_calls | 912 |
| tokens_used | 900,072 |
| status | completed |
| fidelity_distribution | `{"trained": 4}` |
| narrative_exports | markdown, json, pdf |

</details>

### Output files

```
datasets/mars_mission_portal/
  narrative_20260217_093158.markdown   (narrative export)
  narrative_20260217_093158.json       (structured data)
  narrative_20260217_093158.pdf        (PDF export)
  shadow_report.json                   (ADPRS evaluation)
```

### Cost and efficiency improvements

This run reflects several optimizations compared to the previous documented run (`run_20260216_055738_296983ea`):

| Metric | Previous Run | This Run | Change |
|--------|-------------|----------|--------|
| Cost | $0.68 | $0.49 | -28% |
| LLM calls | 1,662 | 912 | -45% |
| Tokens | 1.22M | 900K | -26% |
| PORTAL candidates per step | 7 | 3 | -57% |
| Mini-sim dialog generation | enabled | disabled (states-only scoring) | eliminated waste |
| Voice distinctiveness | 0.58--0.89 | 0.92--0.96 | +24% at low end |
| Quality gate scores | mixed | all 1.00 | consistent |

The candidate reduction from 7 to 3 per backward step captures sufficient diversity while cutting the most expensive part of PORTAL inference. Disabling mini-sim dialog generation (scoring states directly rather than generating disposable dialog for each candidate) eliminates token waste without affecting selection quality.

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
git clone https://github.com/timepoint-ai/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here

./run.sh run mars_mission_portal    # ~$0.40-$0.60
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

./run.sh run mars_mission_portal
# -> local JSONL + SQLite as usual
# -> auto-uploads training_*.jsonl to Oxen.ai with commit history
# -> prints dataset URL and fine-tune URL on completion
```

### Programmatic upload and versioning

```python
from oxen_integration import OxenClient

client = OxenClient(namespace="your-username", repo_name="mars-mission-data")

# Upload a dataset
result = client.upload_dataset("datasets/mars_mission_portal/training_20260217.jsonl",
                               commit_message="Mars mission PORTAL run")
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
    dataset_path="datasets/mars_mission_portal/training_20260217.jsonl",
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

*Generated from run `run_20260217_074855_c7661141` on February 17, 2026. All data extracted from `metadata/runs.db` and `datasets/mars_mission_portal/`. Every number in this document comes from the database, not from documentation --- if you run the same template, you'll get different numbers but the same structural patterns.*
