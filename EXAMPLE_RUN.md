# Example Run: Ares III Mars Mission Portal

**[Back to README](README.md)** | Run ID: `run_20260212_140025_7f33adbd` | Template: `mars_mission_portal`

A complete PORTAL-mode simulation tracing backward from a catastrophic Mars mission failure in 2031 to its institutional origins in 2026. Every number, dialog line, and graph edge below was produced by a single `./run.sh run mars_mission_portal` invocation.

---

## At a Glance

| | |
|---|---|
| **Mode** | PORTAL (backward temporal reasoning) |
| **Timespan** | 2031 &rarr; 2026 (5 years, 10 backward steps) |
| **Entities** | 4 humans, all reaching TRAINED resolution |
| **Dialogs** | 11 conversations, 104 exchanges |
| **Knowledge graph** | 267 typed exposure events, 60 information transfers |
| **Training examples** | 40 structured prompt/completion pairs |
| **Mechanisms fired** | 14 of 19 |
| **ADPRS waveform gating** | 44 evaluations, 66% prediction accuracy |
| **Cost** | $1.00 &bull; 1,605 LLM calls &bull; 1.8M tokens &bull; 72 minutes |

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

---

## 1. The Scenario

The Ares III crewed Mars mission loses contact during orbital insertion in March 2031. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell.

**PORTAL mode** doesn't predict the future. It works backward from a known endpoint, exploring how present-day decisions create future outcomes. Starting from the communication blackout, the system generates 7 candidate antecedent states per step, runs mini forward-simulations to score each with a 405B judge model, and prunes to the most coherent backward chain.

The result: a 5-year causal graph showing how budget compromises, personality clashes, and ignored anomalies compounded into catastrophe.

---

## 2. Cast of Characters

Four crew members, each with tracked cognitive state, emotional arcs, and distinct knowledge bases. All defined in the template's `entity_roster` and carried through the full simulation.

| Character | Role | Final Valence | Final Arousal | Final Energy | ANDOS Layer |
|-----------|------|:---:|:---:|:---:|:---:|
| **Sarah Okafor** | Mission Commander. Experienced, politically pressured by NASA leadership. | +0.68 | 0.53 | 119.5 | 3 |
| **Raj Mehta** | Flight Engineer. Brilliant systems analyst, conflict-averse. | +0.08 | 0.64 | 131.5 | 2 |
| **Lin Zhang** | Systems Engineer. Detected ALSS anomalies, was overruled. | -0.34 | 0.57 | 149.5 | 1 |
| **Thomas Webb** | Mission Director (ground). Prioritized schedule over safety. | -0.16 | 0.58 | 149.4 | 0 |

**Emotional arcs**: Okafor maintains positive valence (leadership optimism) but moderate arousal. Zhang's valence drops to -0.34 (frustration at being overruled). Mehta's arousal is highest at 0.64 (accumulated stress from conflict avoidance). Webb stays near-neutral but his arousal climbs as schedule pressure mounts.

---

## 3. Backward Timeline

Portal mode traces backward from the 2031 failure. Each step was selected from 7 candidates scored by simulation judging. The fidelity schedule escalates as the timeline approaches the origin:

```
Step   Year     Fidelity        Event
 0     2031     dialog          Ares III loses contact during orbital insertion
 1     Jul 30   tensor_only     Webb contracts simplified life support; known O2 flaw ignored
 2     Jan 30   tensor_only     Zhang detects O2 generator flaw; Webb ignores due to schedule
 3     Jul 29   tensor_only     Zhang finds critical flaw; Webb won't allocate resources
 4     Jan 29   scene           Okafor under NASA pressure; allocates $10M contingency
 5     Jul 28   scene           Zhang detects flaw in routine review; shares with Mehta
 6     Jan 28   scene           Okafor allocates $1M for life support upgrades
 7     Jul 27   graph           Zhang presents flaw to Okafor; Mehta detects comms anomaly
 8     Jan 27   graph           Okafor prioritizes safety; minor flaw fixed before launch
 9     Jul 26   dialog          Zhang + Mehta detect flaw; Webb dismissive; Okafor intervenes
10     Jan 26   dialog          Zhang + Mehta identify redundancy architecture flaw; Webb unaware
```

The causal chain shows a repeating pattern: Zhang identifies technical risks, Webb dismisses them under budget/schedule pressure, and Okafor tries to mediate. The institutional failure isn't any single decision --- it's the accumulation of small compromises.

<details>
<summary><b>Full timeline descriptions</b></summary>

**Step 0 (March 2031)**: Ares III crewed Mars mission loses contact during orbital insertion. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell.

**Step 1 (July 2030)**: Thomas Webb makes a deal with a private contractor to provide a simplified life support system, citing concerns about the mission's budget and schedule. However, the contractor's system has a known flaw in the oxygen generator's design, which Lin Zhang detects but is unable to address due to the contract's terms. Meanwhile, Raj Mehta detects anomalies in the communication systems, but his concerns are dismissed by Webb.

**Step 2 (January 2030)**: Lin Zhang detects a flaw in the oxygen generator's design specifications, which she reports to Thomas Webb. However, Webb decides to ignore the flaw due to the mission's tight schedule and the need to meet the budget constraints. Meanwhile, Raj Mehta begins to analyze the communication systems, but his findings are not yet conclusive.

**Step 3 (July 2029)**: Lin Zhang is tasked with analyzing the oxygen generator's design specifications. She detects a critical flaw, but Thomas Webb is hesitant to allocate additional resources to address the issue. Raj Mehta is working on analyzing the communication systems, but his findings are not yet conclusive.

**Step 4 (January 2029)**: Sarah Okafor, under pressure from NASA's leadership to meet the scheduled launch date, decides to prioritize safety margins, allocating an additional $10 million from the mission's contingency fund to address potential system anomalies. Meanwhile, Lin Zhang detects a critical flaw in the oxygen generator.

**Step 5 (July 2028)**: Lin Zhang detects a critical flaw in the oxygen generator's design specifications during a routine review. She brings her concerns to Raj Mehta, who begins analyzing the communication systems to determine if there are any related issues. Meanwhile, Sarah Okafor is under pressure from NASA's leadership to maintain the mission's schedule.

**Step 6 (January 2028)**: Sarah Okafor decides to prioritize the crew's safety over the mission's schedule, allocating an additional $1 million to improve the life support systems. Lin Zhang is tasked with overseeing the upgrades, which gives her more time to review the oxygen generator design specifications.

**Step 7 (July 2027)**: Lin Zhang discovers a critical flaw in the oxygen generator design specifications. She presents her findings to Sarah Okafor, who recognizes the potential risks to the crew. Meanwhile, Raj Mehta detects an anomaly in the communication systems, which he shares with Lin. Thomas Webb is under pressure from stakeholders to meet the original mission schedule.

**Step 8 (January 2027)**: Sarah Okafor decides to prioritize crew safety over the mission schedule, allocating additional resources to the life support systems. Meanwhile, Lin Zhang discovers a minor flaw in the oxygen generator design specifications, which she reports to Raj Mehta. Raj begins working on a fix, and the issue is ultimately addressed before the mission launches.

**Step 9 (July 2026)**: Lin Zhang and Raj Mehta detect a minor flaw in the oxygen generator design specifications. They report the concern to Thomas Webb, who is initially dismissive of the issue. Sarah Okafor intervenes, prioritizing crew safety and allocating additional resources to the life support systems.

**Step 10 (January 2026)**: Lin Zhang and Raj Mehta collaborate on a detailed analysis of the oxygen generator design specifications. They identify a potential flaw in the system's redundancy architecture and begin developing a contingency plan. Meanwhile, Thomas Webb remains focused on meeting the scheduled launch date and is unaware of the potential problem.

</details>

---

## 4. Sample Dialogs

Every timepoint generates a multi-party dialog with tracked emotional tones, confidence scores, and knowledge references. All 4 characters participate in every conversation. Here are two representative exchanges.

### Dialog at tp_004 (January 2029) --- 13 turns, 7 knowledge transfers

> **Raj Mehta** *(neutral, 0.9)*: Alright, let's review our current situation. We have a narrow window to make adjustments to the life support systems before orbital insertion.
>
> **Lin Zhang** *(concerned, 1.0)*: I strongly believe that upgrading the oxygen generators should be prioritized, considering the 23% chance of failure within the first 6 months of operation.
>
> **Sarah Okafor** *(cautious, 0.8)*: I agree with Lin, but we also need to consider the time constraints and the potential risks of delaying the mission. We should weigh the risks and benefits of every decision.
>
> **Thomas Webb** *(practical, 1.0)*: I understand your concerns, but we also need to consider the budget constraints. Upgrading the oxygen generators would cost around $2.5 million. We should discuss the EuroSpace design and make a decision within the next 48 hours.
>
> **Lin Zhang** *(passionate, 1.0)*: I understand the budget concerns, but I still believe that upgrading the oxygen generators is crucial for the crew's safety. We should also consider the long-term benefits of investing in a reliable life support system.
>
> **Sarah Okafor** *(firm, 0.8)*: I think we're all forgetting that we have to prioritize crew safety. We should focus on immediate challenges and make decisions based on available information.
>
> **Raj Mehta** *(thoughtful, 0.8)*: I agree with Sarah. We should also consider adjusting resource allocation to free up more funds for life support systems.
>
> **Thomas Webb** *(resolute, 0.9)*: I think we've covered all the points. Let's summarize our concerns and make a plan. We'll discuss the EuroSpace design and make a decision within the next 48 hours.
>
> **Lin Zhang** *(cooperative, 1.0)*: I'll start reviewing the EuroSpace design and provide feedback within the next 24 hours. Let's work together to make a decision that prioritizes crew safety and mission objectives.
>
> **Sarah Okafor** *(collaborative, 0.8)*: I'll work with Raj to review the budget and resource allocation. We'll identify areas where we can adjust to free up more funds for life support systems.
>
> **Thomas Webb** *(firm, 0.9)*: Let's reconvene in 48 hours to discuss our findings and make a decision. Remember, our priority is crew safety and mission success.
>
> **Raj Mehta** *(thoughtful, 0.8)*: I'll make sure to review the crew's strengths and weaknesses and provide feedback on how to optimize team performance.
>
> **Lin Zhang** *(cooperative, 1.0)*: Let's work together to ensure the success of this mission.

Context flags applied: `physical_states`, `emotional_states`, `body_mind_coupling`, `relationship_context`

<details>
<summary><b>Dialog at tp_006 (January 2028) --- 8 turns, 8 knowledge transfers</b></summary>

> **Sarah Okafor** *(0.9)*: Alright, let's review our current situation. We have a narrow window to make adjustments to the life support systems before orbital insertion. Lin, can you walk us through the oxygen generator upgrades?
>
> **Lin Zhang** *(0.95)*: Yes, of course. The oxygen generators have a 23% chance of failure within the first six months of operation. I strongly believe that upgrading them should be prioritized, considering the risks and costs associated with failure.
>
> **Raj Mehta** *(0.8)*: I understand the concerns, but we also need to consider the time constraints and the potential risks of delaying the mission. Can we discuss the EuroSpace design and its potential benefits?
>
> **Thomas Webb** *(0.85)*: I agree that we need to weigh the risks and benefits of every decision. However, I also think we should focus on immediate challenges and make decisions based on available information. Can we discuss the budget constraints and resource allocation?
>
> **Sarah Okafor** *(0.9)*: I think we should consider adjusting resource allocation to free up more funds for life support systems. We can discuss the specifics, but I believe it's essential to prioritize crew safety.
>
> **Lin Zhang** *(0.85)*: I agree with Sarah. Adjusting resource allocation could be a potential solution. However, we also need to consider the potential risks and consequences of delaying the mission.
>
> **Raj Mehta** *(0.8)*: I think we're getting closer to a decision. Can we summarize the key points and make a plan?
>
> **Thomas Webb** *(0.85)*: I agree. Let's summarize the key points and make a decision within the next 48 hours. We'll discuss the EuroSpace design and its potential benefits, as well as the budget constraints and resource allocation.

</details>

---

## 5. Knowledge Provenance

The system tracks **267 typed exposure events** across the simulation. Every fact an entity knows has a source, a timestamp, and a confidence score. Entities can't know things without a tracked exposure event --- anachronisms are structurally prevented.

### Event distribution

| Entity | Initial | tp_000 | tp_001 | tp_002 | tp_003 | tp_004 | tp_005 | tp_006 | tp_007 | tp_008 | tp_009 | tp_010 | **Total** |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| lin_zhang | 3 | 7 | 4 | 6 | 4 | 7 | 5 | 2 | 4 | 9 | 7 | 6 | **64** |
| raj_mehta | 3 | 6 | 6 | 6 | 6 | 8 | 6 | 5 | 5 | 9 | 8 | 8 | **76** |
| sarah_okafor | 3 | 6 | 5 | 4 | 6 | 6 | 5 | 4 | 4 | 10 | 8 | 6 | **67** |
| thomas_webb | 3 | 5 | 3 | 5 | 5 | 6 | 5 | 4 | 5 | 5 | 7 | 7 | **60** |

### Sample exposure events

```
[tp_001_2030] raj_mehta <- sarah_okafor (told, conf=0.8):
  "Adjusting resource allocation to free up more funds for life support systems is a potential solution."

[tp_004_2029] lin_zhang <- raj_mehta (told, conf=0.8):
  "Adjusting resource allocation to free up more funds for life support systems could be a
   potential solution to budget constraints."

[tp_007_2027] thomas_webb <- raj_mehta (told, conf=0.7):
  "The EuroSpace design is a potential alternative life support system."

[tp_009_2026] sarah_okafor <- raj_mehta (told, conf=1.0):
  "Raj Mehta agrees with Sarah that crew safety should be prioritized and mission objectives
   and timelines reviewed."

[tp_010_2026] thomas_webb <- lin_zhang (told, conf=0.8):
  "The team needs to weigh the risks and benefits of every decision."
```

Raj Mehta accumulates the most exposure events (76) despite being "conflict-averse" --- his role as intermediary means he receives information from all parties. Thomas Webb has the fewest (60), consistent with his tendency to dismiss concerns.

---

## 6. ADPRS Waveform Gating

The ADPRS (Attack, Decay, Peak, Release, Sustain) waveform scheduler evaluates each entity's cognitive activation (&phi;) at each timepoint and maps it to a resolution band. Entities in lower bands skip LLM dialog calls --- their trajectory snapshots are recorded but no tokens are spent.

### Shadow evaluation results

| Entity | &phi; Range | Predicted Band | Actual Level | Divergent? |
|--------|:-----------:|:--------------:|:------------:|:----------:|
| sarah_okafor | 0.610 -- 0.700 | dialog | dialog | Never |
| raj_mehta | 0.671 -- 0.739 | dialog | dialog | Never |
| lin_zhang | 0.571 -- 0.591 | graph | dialog | **Always** |
| thomas_webb | 0.576 -- 0.701 | graph/dialog | dialog | At tp_007--tp_010 |

**Overall**: 44 evaluations, 15 divergent (34%), mean divergence 0.34 bands.

Lin Zhang's &phi; consistently places her in the `graph` band (0.571--0.591), but the adaptive system elevated her to `dialog` in every timepoint because her contributions were deemed essential to the backward chain. This is the ADPRS shadow system working as designed --- tracking where predictions diverge from actual needs so future envelope fits improve.

### Fitted ADPRS envelopes (per entity)

| Entity | A | D | P | R | S | Baseline | Residual | Converged |
|--------|---|---|---|---|---|----------|----------|:---------:|
| sarah_okafor | 1.0 | 31.5B | 7.607 | 0.0 | 0.007 | 0.776 | 0.00117 | Yes |
| raj_mehta | 1.0 | 31.5B | 2.386 | 0.0 | 0.011 | 0.733 | 0.00097 | Yes |
| lin_zhang | 1.0 | 31.5B | 2.367 | 0.0 | 0.017 | 0.702 | 0.00020 | Yes |
| thomas_webb | 1.0 | 31.5B | 2.653 | 0.0 | 0.031 | 0.741 | 0.00104 | Yes |

All envelopes converged via `curve_fit`. Okafor's high P value (7.607) indicates a sharp activation peak --- consistent with her role as commander making decisive interventions. Zhang's lowest residual (0.00020) shows the most predictable activation pattern.

---

## 7. Fidelity Strategy

The system plans a fidelity budget before execution, then adapts during the run. The gap between planned and actual reveals where the scenario demanded more detail than expected.

### Planned schedule

```
Timepoint:   1    2    3    4    5    6    7    8    9    10
Fidelity:  tensor tensor tensor scene scene scene graph graph dialog dialog
Steps:       6    6    6    6    6    6    6    6    6    6
```

### Actual outcome

All 4 entities were elevated to `trained` resolution (maximum). The adaptive threshold of 0.75 triggered upgrades as the portal backward reasoning required full entity context at every step.

| Metric | Planned | Actual |
|--------|---------|--------|
| Token budget | 30,000 | 1,804,171 |
| Budget compliance | -- | 60.14x over (soft budget mode) |
| Resolution distribution | tensor/scene/graph/dialog mix | All `trained` |
| Cost estimate | $0.067 | $1.00 |

This demonstrates the soft budget mode working as intended: the system spent what the scenario required rather than truncating quality to hit a token cap.

---

## 8. Entity Tensors

Each entity carries a multi-dimensional cognitive and physical tensor, compressed via PCA/SVD, with ADPRS envelope metadata. These are the final states after 11 timepoints of simulation.

<details>
<summary><b>Thomas Webb --- cognitive tensor</b></summary>

```json
{
  "knowledge_state": [
    "Mission objectives and timelines",
    "Budget constraints and resource allocation",
    "Pressure from NASA and stakeholders"
  ],
  "emotional_valence": -0.16,
  "emotional_arousal": 0.584,
  "energy_budget": 149.44,
  "decision_confidence": 0.26,
  "patience_threshold": 26.5,
  "risk_tolerance": 0.26,
  "social_engagement": 0.25
}
```

**Physical**: Age 35, health 1.0, pain 0.0, fever 36.5, full mobility/stamina/sensory acuity.
**Compressed (PCA)**: `[0.1, 0.5, 0.15, 1.5, 0.26, 0.265, 0.26, 0.25]`
**Tensor maturity**: 0.790 | **ANDOS layer**: 0

</details>

<details>
<summary><b>Lin Zhang --- cognitive tensor</b></summary>

```json
{
  "knowledge_state": [
    "Spacecraft systems and potential failure points",
    "Concerns about mission safety and risk",
    "Personal frustration with being overruled"
  ],
  "emotional_valence": -0.34,
  "emotional_arousal": 0.570,
  "energy_budget": 149.46,
  "decision_confidence": 0.52,
  "patience_threshold": 53.0,
  "risk_tolerance": 0.51,
  "social_engagement": 0.5
}
```

**Physical**: Age 35, health 1.0, pain 0.0, fever 36.5, full mobility/stamina/sensory acuity.
**Compressed (PCA)**: `[0.1, 0.5, 0.15, 1.5, 0.52, 0.53, 0.51, 0.5]`
**Tensor maturity**: 0.788 | **ANDOS layer**: 1

</details>

<details>
<summary><b>Raj Mehta --- cognitive tensor</b></summary>

```json
{
  "knowledge_state": [
    "Spacecraft systems and operations",
    "Crew dynamics and potential conflicts",
    "Personal concerns about mission safety"
  ],
  "emotional_valence": 0.08,
  "emotional_arousal": 0.643,
  "energy_budget": 131.52,
  "decision_confidence": 0.46,
  "patience_threshold": 45.0,
  "risk_tolerance": 0.43,
  "social_engagement": 0.44
}
```

**Physical**: Age 35, health 1.0, pain 0.0, fever 36.5, full mobility/stamina/sensory acuity.
**Compressed (PCA)**: `[0.0, 0.55, 0.264, 1.32, 0.46, 0.45, 0.43, 0.44]`
**Tensor maturity**: 0.758 | **ANDOS layer**: 2

</details>

<details>
<summary><b>Sarah Okafor --- cognitive tensor</b></summary>

```json
{
  "knowledge_state": [
    "Mission objectives and timelines",
    "Crew member strengths and weaknesses",
    "NASA's expectations and budget constraints"
  ],
  "emotional_valence": 0.68,
  "emotional_arousal": 0.530,
  "energy_budget": 119.50,
  "decision_confidence": 0.41,
  "patience_threshold": 41.5,
  "risk_tolerance": 0.41,
  "social_engagement": 0.4
}
```

**Physical**: Age 35, health 1.0, pain 0.0, fever 36.5, full mobility/stamina/sensory acuity.
**Compressed (PCA)**: `[0.1, 0.75, 0.24, 1.2, 0.41, 0.415, 0.41, 0.4]`
**Tensor maturity**: 0.773 | **ANDOS layer**: 3

</details>

---

## 9. Mechanism Usage

14 of the 19 available mechanisms fired during this run. The counts below show which subsystems did the most work.

| Mechanism | Function | Calls | Description |
|-----------|----------|:-----:|-------------|
| M3 | `_build_knowledge_from_exposures` | 44 | Knowledge graph construction from exposure events |
| M8 | `couple_pain_to_cognition` | 44 | Embodied state &rarr; cognitive state coupling |
| M11 | `synthesize_dialog` | 11 | Multi-party contextual conversation generation |
| M19 | `extract_knowledge_from_dialog` | 11 | Post-dialog knowledge extraction and exposure event creation |
| M6 | `compress` | 8 | Tensor compression (PCA/SVD 8D vectors) |
| M5 | `synthesize_response` | 6 | Lazy resolution on-demand synthesis |
| M9 | `detect_entity_gap` | 6 | Missing entity auto-detection |
| M2 | `progressive_training_check` | 4 | Entity quality improvement tracking |
| M4 | `validate_biological_constraints` | 4 | Physics/biology constraint validation |
| M6 | `create_baseline_tensor` | 4 | Initial tensor creation |
| M6 | `populate_tensor_llm_guided` | 4 | LLM-guided tensor population |
| M1+M17 | `determine_fidelity_temporal_strategy` | 2 | Joint fidelity + temporal planning |
| M1 | `assign_resolutions` | 1 | Initial resolution level assignment |
| M1 | `build_graph` | 1 | Relationship graph construction |
| M17 | `orchestrate` | 1 | Portal orchestration |

M3 and M8 dominate because they fire once per entity per timepoint (4 entities x 11 timepoints = 44). M11 and M19 fire once per timepoint (11 dialogs, each followed by knowledge extraction).

---

## 10. Training Data

This run generated **40 structured training examples** (prompt/completion pairs). Each example includes the entity's full causal history (M7), relationship context (M13), knowledge provenance (M3), and quantitative state (M6).

### Example training prompt structure

```
=== CAUSAL HISTORY (M7) ===
Timeline leading to current moment (3 events):
  tp_000_2031: Ares III loses contact during orbital insertion...
  tp_001_2030: Webb contracts simplified life support...
  tp_002_2030: Zhang detects O2 generator flaw...

=== RELATIONSHIP CONTEXT (M13) ===
Relationships with entities present:
  lin_zhang: tense (trust: 0.45, alignment: 0.30)
  sarah_okafor: cooperative (trust: 0.70, alignment: 0.60)
  raj_mehta: cautious (trust: 0.55, alignment: 0.40)

=== KNOWLEDGE PROVENANCE (M3) ===
Primary sources: scene_initialization (3 items), lin_zhang (2 items)
Learning modes: experienced (70%), told (30%)
Recent: "oxygen generators have 23% failure rate" (from lin_zhang, conf: 0.95)

=== ENTITY STATE (M6) ===
thomas_webb at T0:
  Physical: Age 35, energy 149/100
  Cognitive: 3 knowledge items, 0.26 decision confidence
  Emotional: Valence -0.16, Arousal 0.58

=== PREDICTION TASK ===
Predict: new knowledge, energy change, emotional impact, causal reasoning.
```

### Mean energy dynamics

Mean energy change per example: **-13.0** (entities gradually expend energy across the simulation).

---

## 11. Run Metadata

<details>
<summary><b>Full run record (32 fields)</b></summary>

| Field | Value |
|-------|-------|
| run_id | `run_20260212_140025_7f33adbd` |
| template_id | `mars_mission_portal` |
| started_at | 2026-02-12T14:00:25 |
| completed_at | 2026-02-12T15:12:15 |
| causal_mode | portal |
| max_entities | 4 |
| max_timepoints | 10 |
| entities_created | 4 |
| timepoints_created | 11 |
| training_examples | 40 |
| cost_usd | $1.002 |
| llm_calls | 1,605 |
| tokens_used | 1,804,171 |
| duration_seconds | 4,309.5 |
| status | completed |
| schema_version | 2.0 |
| actual_tokens_used | 1,804,171 |
| token_budget_compliance | 60.14 |
| fidelity_efficiency_score | 8.31e-06 |
| fidelity_distribution | `{"trained": 4}` |
| narrative_exports | markdown, json, pdf |

</details>

### Output files

```
datasets/mars_mission_portal/
  narrative_20260212_151215.markdown   15,208 bytes
  narrative_20260212_151215.json       76,268 bytes
  narrative_20260212_151215.pdf         5,109 bytes
  shadow_report.json                    3,900 bytes
```

### Models used

All inference via OpenRouter, MIT/Apache-licensed models only:

| Model | Role |
|-------|------|
| Llama 4 Scout | Scene parsing, dialog synthesis |
| DeepSeek R1 | Quantitative state propagation |
| Qwen 2.5 72B | Knowledge extraction, entity state |
| Llama 3.1 405B | Portal simulation judging (7 candidates per step) |

---

### Reproduce this run

```bash
git clone https://github.com/realityinspector/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here

./run.sh run mars_mission_portal
```

Cost will vary by ~20% between runs due to LLM response length variation and adaptive fidelity decisions. Expect $0.80--$1.20 and 60--90 minutes.

---

*Generated from run `run_20260212_140025_7f33adbd` by Timepoint-Daedalus. All data extracted from `metadata/runs.db` and `datasets/mars_mission_portal/`.*
