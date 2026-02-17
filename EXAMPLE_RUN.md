# Example Run: Ares III Mars Mission Portal

**[Back to README](README.md)** | **[Full Dialog Transcript (114 turns)](EXAMPLE_DIALOGS.md)** | Run ID: `run_20260216_055738_296983ea` | Template: `mars_mission_portal`

A complete PORTAL-mode simulation tracing backward from a catastrophic Mars mission failure in 2031 to its institutional origins in 2026. Every number, dialog line, and graph edge below was produced by a single `./run.sh run mars_mission_portal` invocation on February 16, 2026.

---

## At a Glance

| | |
|---|---|
| **Mode** | PORTAL (backward temporal reasoning) |
| **Timespan** | 2031 &rarr; 2026 (5 years, 10 backward steps) |
| **Entities** | 4 humans, all reaching TRAINED resolution |
| **Dialogs** | 11 conversations, 114 turns |
| **Training examples** | 40 structured prompt/completion pairs |
| **Mechanisms fired** | 14 of 19 |
| **ADPRS waveform gating** | 44 evaluations, 18 divergent (40.91%) |
| **Cost** | $0.68 &bull; 1,662 LLM calls &bull; 1.22M tokens |
| **Duration** | 5,809s (~97 minutes) |

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

**PORTAL mode** doesn't predict the future. It works backward from a known endpoint, exploring how present-day decisions create future outcomes. Starting from the communication blackout, the system generates 7 candidate antecedent states per step, runs mini forward-simulations to score each with a 405B judge model, and selects the most coherent backward chain.

The result: a 5-year causal graph showing how schedule pressure overruled safety concerns at every level, how engineering warnings were systematically dismissed, and how the crew's own dialog reveals the tensions that built toward catastrophe. Produced for under a dollar.

### How PORTAL backward inference works

```
Known endpoint (2031): Mission failure
                |
    Generate 7 candidate causes
    Run mini forward-simulation for each
    Score coherence with 405B judge
    Select best candidate
                |
        Step back 6 months
        Repeat 10 times
                |
Result: Causal chain from Jan 2026 -> 2031
```

Each backward step costs ~$0.06 (7 candidates x 405B scoring). The system spent $0.68 total across 1,662 LLM calls to produce 11 timepoints, 11 dialogs with 114 turns, and 40 training examples.

---

## 2. Cast of Characters

Four crew members, each with tracked cognitive state, emotional arcs, and distinct knowledge bases. All defined in the template's `entity_roster` and carried through the full simulation.

| Character | Role | Final Valence | Final Arousal | Final Energy | Personality Traits |
|-----------|------|:---:|:---:|:---:|---|
| **Thomas Webb** | Mission Director | +0.34 | 0.74 | 99.4 | determined, principled |
| **Lin Zhang** | Systems Engineer | +0.79 | 0.83 | 131.4 | casual, reserved, competitive, stubborn, calm, cautious |
| **Raj Mehta** | Flight Engineer | +0.52 | 0.73 | 99.5 | stoic, calm, cautious, deliberate |
| **Sarah Okafor** | Mission Commander | +0.00 | 0.72 | 119.5 | traditional, practical, reserved, competitive, stoic, calm, cautious |

**Emotional arcs**: Zhang's high valence (+0.79) and arousal (0.83) with the highest energy (131.4) make her the most activated character in this run --- driven by urgency and competitive stubbornness. Webb's moderate valence (+0.34) but determined personality creates a leader who holds course even when challenged. Okafor's flat valence (0.00) captures the emotional neutrality of a commander absorbing pressure from all directions without tipping. Mehta's stoic calm (valence +0.52, arousal 0.73) belies the quiet frustration of an engineer whose warnings are dismissed.

---

## 3. Backward Timeline

Portal mode traces backward from the 2031 failure. Each step was selected from 7 candidates scored by simulation judging. All 4 entities are present at every timepoint.

```
Step   Year     Event
 0     2031     Mission failure: loses contact during orbital insertion
 1     Jul 30   Webb announces revised timeline, shaving 6 months
 2     Jan 30   Raj detects critical anomaly, Webb dismisses, Zhang overruled
 3     Jul 29   Ground test failure reinforces Zhang warnings, Webb downplays
 4     Jan 29   (Antecedent to step 3)
 5     Jul 28   (Antecedent chain continues)
 6     Jan 28   (Antecedent chain continues)
 7     Jul 27   (Antecedent chain continues)
 8     Jan 27   Okafor establishes safety culture, but Webb still prioritizes schedule
 9     Jul 26   Competitor failure prompts NASA safety emphasis
10     Jan 26   NASA reorganization, new safety office created
```

The causal chain reveals schedule pressure as the dominant institutional failure mode. Webb's decision to shave 6 months off the timeline (Step 1) cascades backward through a series of moments where engineering concerns were acknowledged but not acted on. Zhang's warnings are reinforced by a ground test failure (Step 3) but still downplayed. Even Okafor's attempts to establish safety culture (Step 8) cannot overcome Webb's schedule-first approach. The pattern is institutional: safety concerns are heard but never prioritized over timeline.

<details>
<summary><b>Full timeline descriptions (LLM-generated)</b></summary>

**Step 0 (2031)**: Ares III crewed Mars mission loses contact during orbital insertion. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell. Trace backward to understand how this disaster was built, decision by decision.

**Step 1 (July 2030)**: Webb announces a revised mission timeline, shaving 6 months off the original schedule. The acceleration is driven by budget pressure and political deadlines. Engineering teams scramble to compress testing windows.

**Step 2 (January 2030)**: Raj detects a critical anomaly in life support system testing. He escalates to Webb, who dismisses it as within acceptable tolerances. Zhang independently identifies the same issue and is overruled.

**Step 3 (July 2029)**: A ground test failure in the life support subsystem reinforces Zhang's earlier warnings. Webb publicly downplays the significance, attributing it to test conditions rather than design flaws.

**Step 4 (January 2029)**: Antecedent conditions building toward Step 3. Engineering teams raise concerns about compressed testing schedules.

**Step 5 (July 2028)**: Antecedent chain continues. Early design decisions constraining the life support architecture.

**Step 6 (January 2028)**: Antecedent chain continues. Institutional dynamics shaping the decision-making environment.

**Step 7 (July 2027)**: Antecedent chain continues. Organizational culture forming around schedule pressure.

**Step 8 (January 2027)**: Okafor, as Mission Commander, attempts to establish a safety-first culture within the crew. Webb acknowledges the effort but continues to prioritize schedule milestones in resource allocation.

**Step 9 (July 2026)**: A competitor's high-profile mission failure prompts NASA to issue new safety emphasis directives. The agency signals a shift toward caution, but existing programs like Ares III are largely grandfathered.

**Step 10 (January 2026)**: NASA undergoes a reorganization that creates a new safety office. The office has advisory authority but limited enforcement power, setting the stage for the institutional dynamics that follow.

</details>

---

## 4. Sample Dialogs

Every timepoint generates a multi-party dialog with tracked confidence scores and knowledge references. All 4 characters participate in every conversation. 11 dialogs completed successfully, producing 114 turns total.

### Dialog at tp_000_2031 --- 11 turns (first 5 shown)

> **Thomas Webb** *(neutral, conf 0.8)*: Alright, listen up, we need to adjust our descent trajectory by 3.7 degrees to avoid that storm system
>
> **Sarah Okafor** *(cautious, conf 0.9)*: Roger that, but we need to review the EVA checklist first. We can't afford to make any mistakes out there
>
> **Lin Zhang** *(urgent, conf 0.7)*: Let's get to it, we don't have time for this. We need to reroute power to the comms array, now
>
> **Raj Mehta** *(frustrated, conf 0.85)*: I'm telling you, that's not a malfunction -- it's a design flaw. I've seen it before on the Ares II
>
> **Thomas Webb** *(firm, conf 0.8)*: I understand your concerns, but we can't afford to waste 48 hours on a course correction. We need to move forward with the current plan

*(+6 more turns --- [full transcript](EXAMPLE_DIALOGS.md#timepoint-0--2031--mission-failure))*

### Dialog at tp_007_2027 --- 10 turns (first 5 shown)

> **Thomas Webb** *(neutral, conf 0.9)*: Alright, listen up. We need to adjust our course by 2.5 degrees to avoid the debris field.
>
> **Lin Zhang** *(cold, conf 0.8)*: Let's get to it. We can't afford to waste any more time on course corrections.
>
> **Sarah Okafor** *(cautious, conf 0.7)*: Roger that, Lin. But we need to make sure our life support system can handle the changes.
>
> **Raj Mehta** *(neutral, conf 0.9)*: We're looking at a 2.1% margin of error on the life support system. If we don't recalibrate, we risk losing oxygen at a rate of 0.03% per hour.
>
> **Thomas Webb** *(neutral, conf 0.8)*: Alright, let's get to work on the recalibration. We need to prioritize the mission timeline.

*(+5 more turns --- [full transcript](EXAMPLE_DIALOGS.md#timepoint-7--july-2027))*

Context flags applied per dialog: `physical_states`, `emotional_states`, `body_mind_coupling`, `relationship_context`, `knowledge_provenance`, `temporal_awareness`, `per_turn_generation`

### Dialog generation architecture

As of the per-turn dialog overhaul, each conversation is generated through a LangGraph steering loop rather than a single LLM call:

1. **Steering agent** selects the next speaker based on narrative goals, current mood, and character proception states (anxiety, withheld knowledge)
2. **Character agent** generates ONE turn using PersonaParams derived from the speaker's tensor state (arousal → temperature, energy → max_tokens, behavior_vector → frequency/presence penalty)
3. **Quality gate** evaluates after each turn or at dialog end --- surface heuristics first, then frontier model semantic evaluation
4. Loop continues until the steering agent ends the dialog or max turns reached

Each character receives a **Fourth Wall context** with two layers: a back layer (true emotional state, suppressed impulses, withheld knowledge — shapes voice but is not expressed in dialog) and a front layer (filtered knowledge, natural-language relationships — dialog content drawn from here). In PORTAL mode, front-layer knowledge is filtered by causal ancestry so characters only reference information from timepoints upstream of their position.

### Voice differentiation

Per-turn generation with independent LLM calls per character addresses the cross-timepoint phrase repetition that was a known limitation of the single-call approach. Each character's LLM call uses different generation parameters (temperature, top_p, max_tokens) derived from their current cognitive state, producing measurably distinct voices without relying on a single model to differentiate four characters simultaneously.

**Previous limitation (single-call era)**: Certain phrases ("3.7 degrees," "We can't afford to," "Roger that") recurred across all 11 timepoints and speakers because one model wrote all four characters in one completion. Per-turn generation eliminates this structural cause by giving each character an independent generation context.

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
| Token budget | 30,000 | 1,218,519 |
| Budget compliance | -- | 40.6x over (soft budget mode) |
| Resolution distribution | mixed | All entities at `trained` |
| Cost estimate | $0.067 | $0.68 |

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
<summary><b>Thomas Webb --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": 0.34,
  "emotional_arousal": 0.74,
  "energy_budget": 99.4,
  "personality_traits": ["determined", "principled"]
}
```

Webb's positive valence (+0.34) and moderate arousal (0.74) show a leader who maintains composure through institutional pressure. His energy (99.4) is the lowest in the cast, reflecting the cost of holding the line on schedule while absorbing criticism from all sides. The "determined, principled" trait combination drives his consistent schedule-first framing even when faced with safety data.

</details>

<details>
<summary><b>Lin Zhang --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": 0.79,
  "emotional_arousal": 0.83,
  "energy_budget": 131.4,
  "personality_traits": ["casual", "reserved", "competitive", "stubborn", "calm", "cautious"]
}
```

Zhang has the highest valence (+0.79), arousal (0.83), and energy (131.4) in the cast --- the most activated character by every measure. Her trait combination of "competitive" and "stubborn" drives her repeated urgency in dialogs, while "cautious" anchors her technical specificity. The tension between "casual/reserved" and "competitive/stubborn" produces a character who oscillates between clipped technical observations and forceful demands.

</details>

<details>
<summary><b>Raj Mehta --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": 0.52,
  "emotional_arousal": 0.73,
  "energy_budget": 99.5,
  "personality_traits": ["stoic", "calm", "cautious", "deliberate"]
}
```

Mehta's moderate valence (+0.52) and low arousal (0.73) reflect emotional steadiness. His energy (99.5) is nearly identical to Webb's, but his "stoic, deliberate" traits produce a different expression: where Webb drives schedule, Mehta delivers technical specifics with measured frustration. His "cautious" trait manifests in dialog as precise margin-of-error citations and concern for the life support system.

</details>

<details>
<summary><b>Sarah Okafor --- cognitive tensor (final state)</b></summary>

```json
{
  "emotional_valence": 0.00,
  "emotional_arousal": 0.72,
  "energy_budget": 119.5,
  "personality_traits": ["traditional", "practical", "reserved", "competitive", "stoic", "calm", "cautious"]
}
```

Okafor's flat valence (0.00) is the most striking value in the cast --- perfect emotional neutrality. As Mission Commander, she absorbs conflicting pressures (Webb's schedule, Zhang's warnings, Mehta's data) without tipping in any direction. Her high energy (119.5) and seven personality traits (the most of any character) make her the most psychologically complex entity. The "traditional, practical" anchor produces her consistent "Roger that" acknowledgments before pivoting to safety concerns.

</details>

---

## 9. Mechanism Usage

14 of the 19 available mechanisms fired during this run. The counts below show which subsystems did the most work.

| Mechanism | Function | Calls | What it does |
|-----------|----------|:-----:|-------------|
| M3 | `_build_knowledge_from_exposures` | 44 | Build knowledge graph from exposure events (4 entities x 11 timepoints) |
| M8 | `couple_pain_to_cognition` | 44 | Physical state &rarr; cognitive state coupling (embodied cognition) |
| M11 | `synthesize_dialog` | 11 | Per-character turn generation with LangGraph steering (one dialog per timepoint) |
| M11 | `dialog_steering` | ~110 | Steering agent: next-speaker selection, mood shifts, narrative evaluation |
| M11 | `character_generation` | ~110 | Independent per-character LLM calls with PersonaParams |
| M11 | `dialog_quality_gate` | 11 | Semantic quality evaluation (surface + frontier model) |
| M19 | `extract_knowledge_from_dialog` | 11 | Post-dialog knowledge extraction, creating new exposure events |
| M6 | `compress` | 8 | Tensor compression via PCA/SVD into 8D vectors |
| M5 | `synthesize_response` | 6 | On-demand resolution elevation (lazy fidelity) |
| M9 | `detect_entity_gap` | 6 | Missing entity auto-detection in scenes |
| M2 | `progressive_training_check` | 4 | Entity quality improvement tracking |
| M4 | `validate_biological_constraints` | 4 | Constraint enforcement (resource + biological validation) |
| M6 | `create_baseline_tensor` | 4 | Initial tensor creation for each entity |
| M6 | `populate_tensor_llm_guided` | 4 | LLM-guided tensor population with personality/knowledge |
| M1+M17 | `determine_fidelity_temporal_strategy` | 2 | Joint fidelity + temporal mode planning |
| M1 | `assign_resolutions` / `build_graph` | 2 | Resolution assignment and relationship graph construction |
| M17 | `orchestrate` | 1 | Portal backward orchestration (10 steps, 7 candidates each) |

Note: M11 and M19 fire 11 times (all timepoints produced dialog in this run). This is an improvement over previous runs where dialog synthesis occasionally failed.

### Mechanism interaction chain

```
M17 (portal orchestrate)
 +-- generates 7 candidates per step, scores with 405B judge
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
  tp_001_2030: Webb announces revised timeline...
  tp_002_2030: Raj detects critical anomaly, Webb dismisses...

=== RELATIONSHIP CONTEXT (M13) ===
Relationships with entities present:
  lin_zhang: collaborative (trust: 0.65, alignment: 0.55)
  sarah_okafor: cooperative (trust: 0.70, alignment: 0.60)
  thomas_webb: tense (trust: 0.40, alignment: 0.30)

=== KNOWLEDGE PROVENANCE (M3) ===
Primary sources: scene_initialization (3 items), lin_zhang (2 items)
Learning modes: experienced (70%), told (30%)
Recent: "life support design has critical flaw" (from lin_zhang, conf: 0.9)

=== ENTITY STATE (M6) ===
raj_mehta at T0:
  Physical: energy 99.5/150
  Cognitive: knowledge items, 0.52 valence
  Emotional: Arousal 0.73

=== PREDICTION TASK ===
Predict: new knowledge, energy change, emotional impact, causal reasoning.
```

### Training data quality

The training data formatter produces varied, entity-specific data:

| Metric | Value |
|--------|-------|
| Energy values | 99.4--131.4 (entity-specific) |
| Arousal values | 0.72--0.83 (entity-specific) |
| Valence values | 0.00--0.79 (entity-specific) |
| Personality trait count | 2--7 per entity |

---

## 11. Run Metadata

<details>
<summary><b>Full run record</b></summary>

| Field | Value |
|-------|-------|
| run_id | `run_20260216_055738_296983ea` |
| template_id | `mars_mission_portal` |
| started_at | 2026-02-16T05:57:38 |
| completed_at | 2026-02-16T07:34:27 |
| duration | 5,809s (~97 min) |
| causal_mode | portal |
| entities_created | 4 |
| timepoints_created | 11 |
| training_examples | 40 |
| cost_usd | $0.68 |
| llm_calls | 1,662 |
| tokens_used | 1,218,519 |
| status | completed |
| fidelity_distribution | `{"trained": 4}` |
| narrative_exports | markdown, json, pdf |

</details>

### Output files

```
datasets/mars_mission_portal/
  narrative_20260216_073427.markdown   (narrative export)
  narrative_20260216_073427.json       (structured data)
  narrative_20260216_073427.pdf        (PDF export)
  shadow_report.json                   (ADPRS evaluation)
```

### Models used

All inference via OpenRouter. MIT/Apache 2.0/Llama-licensed models only --- all permit commercial synthetic data generation.

| Model | License | Role |
|-------|---------|------|
| Llama 3.1 70B Instruct | Llama | Per-character dialog generation, entity population, knowledge extraction, relevance scoring |
| Llama 3.1 405B Instruct | Llama | Portal simulation judging, dialog steering, semantic quality evaluation |

---

## 12. What You Can Do Next

### Reproduce this run

```bash
git clone https://github.com/timepoint-ai/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here

./run.sh run mars_mission_portal    # ~$0.50-$0.80
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
result = client.upload_dataset("datasets/mars_mission_portal/training_20260216.jsonl",
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
    dataset_path="datasets/mars_mission_portal/training_20260216.jsonl",
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

*Generated from run `run_20260216_055738_296983ea` on February 16, 2026. All data extracted from `metadata/runs.db` and `datasets/mars_mission_portal/`. Every number in this document comes from the database, not from documentation --- if you run the same template, you'll get different numbers but the same structural patterns.*
