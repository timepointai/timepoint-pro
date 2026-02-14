# Example Run: Ares III Mars Mission Portal

**[Back to README](README.md)** | **[Full Dialog Transcript (127 turns)](EXAMPLE_DIALOGS.md)** | Run ID: `run_20260213_141539_9ba13680` | Template: `mars_mission_portal`

A complete PORTAL-mode simulation tracing backward from a catastrophic Mars mission failure in 2031 to its institutional origins in 2026. Every number, dialog line, and graph edge below was produced by a single `./run.sh run mars_mission_portal` invocation on February 13, 2026.

---

## At a Glance

| | |
|---|---|
| **Mode** | PORTAL (backward temporal reasoning) |
| **Timespan** | 2031 &rarr; 2026 (5 years, 10 backward steps) |
| **Entities** | 4 humans, all reaching TRAINED resolution |
| **Dialogs** | 11 conversations, 127 exchanges |
| **Knowledge graph** | 234 typed exposure events, 89 information transfers |
| **Training examples** | 40 structured prompt/completion pairs |
| **Mechanisms fired** | 14 of 19 |
| **ADPRS waveform gating** | 44 evaluations, 0% divergence |
| **Cost** | $0.98 &bull; 1,596 LLM calls &bull; 1.76M tokens |
| **Convergence** | 6 runs of this template: outcome similarity 0.79, role stability 1.00 |

---

## Table of Contents

1. [The Scenario](#1-the-scenario)
2. [Cast of Characters](#2-cast-of-characters)
3. [Backward Timeline](#3-backward-timeline)
4. [Sample Dialogs](#4-sample-dialogs)
5. [Knowledge Provenance](#5-knowledge-provenance)
6. [Outcome Convergence](#6-outcome-convergence)
7. [ADPRS Waveform Gating](#7-adprs-waveform-gating)
8. [Fidelity Strategy](#8-fidelity-strategy)
9. [Entity Tensors](#9-entity-tensors)
10. [Mechanism Usage](#10-mechanism-usage)
11. [Training Data](#11-training-data)
12. [Run Metadata](#12-run-metadata)
13. [What You Can Do Next](#13-what-you-can-do-next)
14. [Port to Oxen.ai](#14-port-to-oxenai)
15. [API & Programmatic Access](#15-api--programmatic-access)

---

## 1. The Scenario

The Ares III crewed Mars mission loses contact during orbital insertion in March 2031. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell.

**PORTAL mode** doesn't predict the future. It works backward from a known endpoint, exploring how present-day decisions create future outcomes. Starting from the communication blackout, the system generates 7 candidate antecedent states per step, runs mini forward-simulations to score each with a 405B judge model, and selects the most coherent backward chain.

The result: a 5-year causal graph showing how budget compromises, personality clashes, and ignored anomalies compounded into catastrophe --- produced for under a dollar.

### How PORTAL backward inference works

```
Known endpoint (2031): Mission failure
                ↓
    Generate 7 candidate causes
    Run mini forward-simulation for each
    Score coherence with 405B judge
    Select best candidate
                ↓
        Step back 6 months
        Repeat 10 times
                ↓
Result: Causal chain from Jan 2026 → Mar 2031
```

Each backward step costs ~$0.09 (7 candidates x 405B scoring). The system spent $0.98 total across 1,596 LLM calls to produce 11 timepoints, 234 exposure events, and 40 training examples.

---

## 2. Cast of Characters

Four crew members, each with tracked cognitive state, emotional arcs, and distinct knowledge bases. All defined in the template's `entity_roster` and carried through the full simulation.

| Character | Role | Final Valence | Final Arousal | Final Energy | Exposure Events |
|-----------|------|:---:|:---:|:---:|:---:|
| **Sarah Okafor** | Mission Commander. Experienced, politically pressured by NASA leadership. | -0.02 | 0.55 | 131.4 | 60 |
| **Raj Mehta** | Flight Engineer. Analyzes systems and crew dynamics, conflict-averse. | +0.78 | 0.60 | 99.3 | 59 |
| **Lin Zhang** | Systems Engineer. Detected ALSS anomalies, fought to be heard. | +0.53 | 0.76 | 131.3 | 54 |
| **Thomas Webb** | Mission Director (ground). Prioritized schedule over safety. | -0.36 | 0.70 | 149.4 | 61 |

**Emotional arcs**: Webb's valence drops to -0.36 (frustration from mounting schedule pressure) while his arousal climbs to 0.70 (highest among the cast). Zhang's positive valence (+0.53) reflects vindication as her concerns prove valid. Mehta's energy is lowest at 99.3 --- the conflict-averse intermediary depletes fastest. Okafor is near-neutral (-0.02), pulled between leadership optimism and growing unease.

Each entity received 3 initial knowledge items from `scene_initialization` and accumulated 51--58 additional items through dialog-driven exposure events across 11 timepoints.

---

## 3. Backward Timeline

Portal mode traces backward from the 2031 failure. Each step was selected from 7 candidates scored by simulation judging (best coherence: 0.818). All 4 entities are present at every timepoint.

```
Step   Year     Event
 0     Mar 31   Ares III loses contact during orbital insertion --- cascading life support + comms failure
 1     Jul 30   Critical software bug discovered in mission control; Zhang identified it, Webb patches with workaround
 2     Jan 30   Zhang detects oxygen generator anomalies; Webb diverts resources elsewhere
 3     Jul 29   Zhang + Mehta develop contingency plan for O2 system; Webb refuses to allocate resources
 4     Jan 29   Simulation exercise reveals O2 risks; Webb negotiates to reduce crew size
 5     Jul 28   Zhang + Mehta reveal critical design flaw in O2 system; Webb torn between fix and schedule
 6     Jan 28   Mehta raises life support concerns to Webb, is rebuffed; Zhang investigates independently
 7     Jul 27   Zhang's O2 flaw finding validated by independent review; Webb resists design changes
 8     Jan 27   Okafor secures additional resources from NASA; Zhang begins thorough O2 testing
 9     Jul 26   Zhang convinces Mehta to investigate O2 flaw despite schedule; Webb suspects crew size compromise
10     Jan 26   Mehta discovers flaw in O2 generator engineering specs; Webb downplays significance
```

The causal chain reveals a repeating pattern: Zhang identifies technical risks, Webb dismisses them under budget/schedule pressure, Mehta mediates, and Okafor tries to secure resources from above. The institutional failure isn't any single decision --- it's the accumulation of small compromises over 5 years.

<details>
<summary><b>Full timeline descriptions (LLM-generated)</b></summary>

**Step 0 (March 2031)**: Ares III crewed Mars mission loses contact during orbital insertion in March 2031. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell. Trace backward to understand how this disaster was built, decision by decision.

**Step 1 (July 2030)**: A critical software bug is discovered in the Ares III mission control system, which Lin Zhang had previously identified but was unable to fix due to resource constraints. Thomas Webb orders a temporary workaround, but Raj Mehta warns that the fix may not be reliable. Meanwhile, Sarah Okafor begins to question the mission's overall safety margin.

**Step 2 (January 2030)**: Lin Zhang detects anomalies in the oxygen generator test results, but is unable to investigate further due to resource constraints. Thomas Webb, prioritizing the schedule, decides to allocate resources to other areas of the mission. Raj Mehta, aware of the anomalies, begins to question the safety margin. Sarah Okafor, concerned about the lack of resources, starts to feel uneasy about the mission's overall safety.

**Step 3 (July 2029)**: Lin Zhang and Raj Mehta collaborate to develop a contingency plan for the oxygen generator system, but Thomas Webb decides not to allocate resources to implement the plan. Sarah Okafor is unaware of the plan's existence.

**Step 4 (January 2029)**: Lin Zhang and Raj Mehta participate in a simulation exercise to test the crew's response to emergencies. They identify potential risks and weaknesses in the oxygen generator system, which informs their contingency planning. Meanwhile, Thomas Webb is negotiating with stakeholders to reduce the crew size, which may impact the availability of personnel for the contingency plan.

**Step 5 (July 2028)**: Lin Zhang and Raj Mehta conduct an in-depth analysis of the oxygen generator system's test results, revealing a critical design flaw. They present their findings to Thomas Webb, who is torn between addressing the issue and meeting the tight schedule. Sarah Okafor is focused on crew training, unaware of the potential risks.

**Step 6 (January 2028)**: Raj Mehta presents his concerns about the life support system to Thomas Webb, but is met with resistance. Lin Zhang begins to secretly investigate the oxygen generator design. Sarah Okafor focuses on crew training, emphasizing emergency response procedures.

**Step 7 (July 2027)**: Systems Engineer Lin Zhang is tasked with reviewing the oxygen generator design. She detects a critical flaw, and her concerns are validated by an independent review team. However, Mission Director Thomas Webb is under pressure to meet the schedule and resists making changes. Meanwhile, Raj Mehta starts to notice a trend of minor anomalies in the life support system.

**Step 8 (January 2027)**: Sarah Okafor convinces NASA leadership to allocate additional resources to the Ares III mission's life support system. This allows Lin Zhang to conduct more thorough testing of the oxygen generator design, which eventually reveals the critical flaw. Thomas Webb is dealing with the consequences of a recent equipment failure, which has delayed the mission by 1 week.

**Step 9 (July 2026)**: Lin Zhang convinces Raj Mehta to help her investigate a suspected flaw in the oxygen generator design, despite the mission's tight schedule and budget constraints. Meanwhile, Thomas Webb begins to suspect that the crew size reduction may have compromised the mission's safety margins.

**Step 10 (January 2026)**: Raj Mehta discovers a critical flaw in the engineering specifications for the oxygen generator design. He reports his findings to Lin Zhang, who recognizes the potential implications for the mission. Thomas Webb is informed but downplays the significance of the flaw, citing the need to meet schedule milestones. Sarah Okafor must balance the need for caution with the pressure to maintain the mission timeline.

</details>

---

## 4. Sample Dialogs

Every timepoint generates a multi-party dialog with tracked confidence scores and knowledge references. All 4 characters participate in every conversation. 11 dialogs total, 127 turns, 89 information transfers.

### Dialog at tp_001_2030 --- 12 turns, 5 knowledge transfers

> **Raj Mehta** *(conf 0.8)*: We need to evaluate both options for the Ares III mission control system.
>
> **Sarah Okafor** *(conf 0.7)*: I agree, but we also need to consider the crew member strengths and weaknesses.
>
> **Thomas Webb** *(cautious, conf 0.9)*: Budget constraints are a major concern for this mission. We can't afford to make mistakes.
>
> **Lin Zhang** *(concerned, conf 0.8)*: I've identified a potential risk in the safety protocols. We need to address it before proceeding.
>
> **Raj Mehta** *(conf 0.8)*: I concur with Lin. Safety protocols should be our top priority.

*(+7 more turns...)*

### Dialog at tp_003_2029 --- 12 turns, 10 knowledge transfers

> **Thomas Webb** *(conf 0.8)*: We need to review the budget constraints and resource allocation before the next meeting.
>
> **Sarah Okafor** *(conf 0.8)*: I agree, but we also need to consider the crew member strengths and weaknesses for the Ares III mission.
>
> **Raj Mehta** *(conf 0.8)*: I concur with Sarah. We should evaluate both options for the Ares III mission control system and consider the implications for the crew.
>
> **Lin Zhang** *(conf 0.9)*: I've identified a potential risk in the safety protocols. We need to address this before the next meeting.
>
> **Thomas Webb** *(conf 0.8)*: Let's table the discussion about the Ares III mission until after the review.

*(+7 more turns...)*

Context flags applied per dialog: `physical_states`, `emotional_states`, `body_mind_coupling`, `relationship_context`, `knowledge_provenance`, `temporal_awareness`

---

## 5. Knowledge Provenance

The system tracks **234 typed exposure events** across the simulation. Every fact an entity knows has a source, a timestamp, and a confidence score. Entities can't know things without a tracked exposure event --- anachronisms are structurally prevented.

### Event distribution by timepoint

| Timepoint | Events | Key content |
|-----------|:------:|-------------|
| pre_tp_001 (initial) | 12 | Scene initialization: mission objectives, safety protocols, budget constraints |
| tp_000 (2031) | 24 | Mission failure debrief: systems failures, crew status, communication loss |
| tp_001 (Jul 2030) | 33 | Software bug discovery, workaround debate, safety margin questions |
| tp_002 (Jan 2030) | 27 | O2 anomaly detection, resource diversion, growing unease |
| tp_003 (Jul 2029) | 36 | Contingency planning, resource refusal, information asymmetry |
| tp_004 (Jan 2029) | 15 | Simulation exercise, risk identification, crew size negotiations |
| tp_005 (Jul 2028) | 18 | Design flaw revealed, schedule vs safety tension |
| tp_006 (Jan 2028) | 3 | Mehta rebuffed, Zhang's independent investigation |
| tp_008 (Jan 2027) | 24 | NASA resource allocation, thorough O2 testing begins |
| tp_009 (Jul 2026) | 27 | Zhang-Mehta collaboration, Webb's crew size concerns |
| tp_010 (Jan 2026) | 15 | Engineering spec flaw discovered, Webb downplays |

### Exposure events by entity

| Entity | Total Events | Unique Sources | Role Pattern |
|--------|:---:|:---:|---|
| thomas_webb | 61 | 4 | Receives most information but acts on least |
| sarah_okafor | 60 | 4 | Relay node: connects NASA leadership to crew concerns |
| raj_mehta | 59 | 4 | Intermediary: receives from all parties, mediates |
| lin_zhang | 54 | 4 | Source node: generates technical findings, receives least |

### Sample exposure chain

```
[pre_tp_001] lin_zhang <- scene_initialization (initial, conf=1.0):
  "Spacecraft systems and performance metrics"

[tp_000_2031] raj_mehta <- sarah_okafor (told, conf=0.8):
  "The team needs to review the mission objectives and timelines."

[tp_001_2030] lin_zhang <- sarah_okafor (told, conf=0.8):
  "We need to evaluate both options for the Ares III mission control system."

[tp_003_2029] thomas_webb <- lin_zhang (told, conf=0.9):
  "I've identified a potential risk in the safety protocols."

[tp_009_2026] raj_mehta <- lin_zhang (told, conf=0.8):
  "We should review the mission objectives and timelines before making any decisions."
```

Thomas Webb accumulates the most exposure events (61) but has the lowest valence (-0.36) --- he receives the information but his schedule-first disposition causes him to dismiss critical findings. Lin Zhang has the fewest events (54) but the highest confidence scores, consistent with her role as the primary technical source.

---

## 6. Outcome Convergence

This is where things get interesting. Running the same template multiple times with the same LLM produces different surface-level details but converges on the same structural outcomes. This is the core evidence that the simulation captures something real about institutional dynamics, not just random LLM output.

### 6 runs of `mars_mission_portal`

| Run | Date | Cost | Exposure Events | Dialogs | Timepoints |
|-----|------|:----:|:---:|:---:|:---:|
| `946db667` | Feb 6 | $0.52 | 225 | 11 | 11 |
| `3ba043b2` | Feb 9 | $0.51 | 201 | 10 | 11 |
| `baae2120` | Feb 11 | $0.91 | 238 | 11 | 11 |
| `7d55d9c6` | Feb 11 | $0.38 | 174 | 6 | 6 |
| `7f33adbd` | Feb 12 | $1.00 | 267 | 11 | 11 |
| **`9ba13680`** | **Feb 13** | **$0.98** | **234** | **11** | **11** |

### Convergence metrics (computed across 3+ comparable runs)

| Metric | Score | What it measures |
|--------|:-----:|-----------------|
| **Outcome similarity** | **0.79** | Do runs reach the same conclusions? (role assignments, event sequences, knowledge discovery) |
| **Role stability** | **1.00** | Do the same characters play the same structural roles? (Zhang=source, Webb=blocker, Mehta=relay, Okafor=authority) |
| **Knowledge convergence** | **0.60** | Do the same facts get discovered? (O2 flaw, budget constraints, crew dynamics) |
| **Structural similarity** | **0.57** | Do the same causal edges appear? (Jaccard over temporal + knowledge edges) |

**What this means**: Role stability is 1.00 --- across every run, Zhang identifies the technical problem, Webb dismisses it, Mehta mediates, Okafor tries to intervene from above. The characters aren't randomly assigned to narrative roles; the simulation's knowledge provenance and personality parameters drive them to the same structural positions every time.

Outcome similarity at 0.79 means the runs agree on *what happens* (catastrophe built from institutional dysfunction) even when the specific dialog lines, exposure events, and edge structures differ. Structural similarity is lower (0.57) because there are many valid causal paths to the same outcome --- which is exactly what you'd expect from a real organizational failure.

### How convergence is computed

```python
from evaluation.convergence import compute_outcome_convergence

results = compute_outcome_convergence("mars_mission_portal", min_runs=3)
# Returns: outcome_mean_similarity, structural_mean_similarity,
#          knowledge_convergence, role_stability
```

The system extracts outcome summaries from each run (`extract_outcome_summary()`), computes pairwise similarity (`outcome_similarity()`), and reports both structural (edge Jaccard) and outcome-level (role + knowledge + event hash) convergence. Structural convergence measures whether the same graph edges appear; outcome convergence measures whether the same *things happen*.

---

## 7. ADPRS Waveform Gating

The ADPRS (Attack, Decay, Peak, Release, Sustain) waveform scheduler evaluates each entity's cognitive activation (&phi;) at each timepoint and maps it to a resolution band. Entities in lower bands skip LLM dialog calls --- their trajectory snapshots are recorded but no tokens are spent.

### Shadow evaluation results

| Entity | &phi; Value | Predicted Band | Actual Level | Divergent? |
|--------|:-----------:|:--------------:|:------------:|:----------:|
| sarah_okafor | 0.776 | dialog | dialog | Never |
| thomas_webb | 0.741 | dialog | dialog | Never |
| raj_mehta | 0.733 | dialog | dialog | Never |
| lin_zhang | 0.702 | dialog | dialog | Never |

**Overall**: 44 evaluations, 0 divergent (0%), mean continuous divergence 0.038 bands.

All four entities stayed in the `dialog` band throughout --- this is expected for a PORTAL template where every character is structurally important to the backward chain. The ADPRS system confirmed this: none were demoted to cheaper resolution levels.

Lin Zhang's &phi; (0.702) is the lowest, barely above the dialog threshold. In a larger simulation with peripheral characters, the ADPRS system would gate low-&phi; entities to `tensor_only` or `graph` bands, saving tokens on characters who don't drive the narrative.

### Fitted ADPRS envelopes

The shadow report includes fitted envelope parameters for each entity, computed via `scipy.optimize.curve_fit`:

| Entity | Baseline &phi; | Continuous Divergence | Converged |
|--------|:---------:|:---:|:---:|
| sarah_okafor | 0.776 | 0.076 | Yes |
| thomas_webb | 0.741 | 0.041 | Yes |
| raj_mehta | 0.733 | 0.033 | Yes |
| lin_zhang | 0.702 | 0.002 | Yes |

Zhang's near-zero divergence (0.002) means the ADPRS system predicts her activation level almost perfectly --- her engagement pattern is the most consistent across timepoints. Okafor's higher divergence (0.076) reflects her role as commander: her activation spikes when she intervenes and drops when delegating.

---

## 8. Fidelity Strategy

The system plans a fidelity budget before execution, then adapts during the run. The gap between planned and actual reveals where the scenario demanded more detail than expected.

### Planned vs. actual

| Metric | Planned | Actual |
|--------|---------|--------|
| Fidelity schedule | tensor &rarr; scene &rarr; graph &rarr; dialog | All `trained` |
| Token budget | 30,000 | 1,762,921 |
| Budget compliance | -- | 58.8x over (soft budget mode) |
| Resolution distribution | mixed | All entities at `trained` |
| Cost estimate | $0.067 | $0.983 |

### Resolution escalation

The planner starts conservative:
```
Timepoint:   1      2      3      4      5      6      7      8      9      10
Planned:   tensor tensor tensor scene  scene  scene  graph  graph  dialog dialog
```

But the adaptive threshold (0.75) triggered upgrades at every step --- PORTAL backward reasoning requires full entity context to score candidate antecedents. All 4 entities were elevated to `trained` resolution (maximum fidelity, ~50k tokens each).

This demonstrates soft budget mode working as intended: the system spent what the scenario required rather than truncating quality to hit a token cap. For cost-sensitive use, switch to hard budget mode: `./run.sh run --budget 0.50 mars_mission_portal`

---

## 9. Entity Tensors

Each entity carries a multi-dimensional cognitive and physical state tensor, updated at every timepoint. These are the final states after 11 timepoints of simulation.

<details>
<summary><b>Thomas Webb --- cognitive tensor (final state)</b></summary>

```json
{
  "knowledge_state": [
    "Mission timelines and milestones",
    "Budget constraints and resource allocation",
    "NASA's expectations and priorities"
  ],
  "emotional_valence": -0.36,
  "emotional_arousal": 0.70,
  "energy_budget": 149.4,
  "decision_confidence": 0.285,
  "risk_tolerance": 0.26,
  "social_engagement": 0.25
}
```

Webb's low confidence (0.285) and negative valence (-0.36) reflect mounting pressure. His energy remains high (149.4) --- he's not doing the technical work, just blocking it.

</details>

<details>
<summary><b>Lin Zhang --- cognitive tensor (final state)</b></summary>

```json
{
  "knowledge_state": [
    "Spacecraft systems and performance metrics",
    "Crew member concerns and feedback",
    "Safety protocols and procedures"
  ],
  "emotional_valence": 0.53,
  "emotional_arousal": 0.76,
  "energy_budget": 131.3,
  "decision_confidence": 0.52,
  "risk_tolerance": 0.51,
  "social_engagement": 0.50
}
```

Zhang has the highest arousal (0.76) and highest decision confidence (0.52) --- she's the most activated character, driven by technical conviction.

</details>

<details>
<summary><b>Raj Mehta --- cognitive tensor (final state)</b></summary>

```json
{
  "knowledge_state": [
    "Spacecraft systems and operations",
    "Crew member personalities and dynamics",
    "Potential risks and contingency plans"
  ],
  "emotional_valence": 0.78,
  "emotional_arousal": 0.60,
  "energy_budget": 99.3,
  "decision_confidence": 0.46,
  "risk_tolerance": 0.43,
  "social_engagement": 0.44
}
```

Mehta has the highest valence (+0.78) but lowest energy (99.3) --- the cost of mediating between Zhang and Webb. His knowledge uniquely includes "crew member personalities and dynamics" --- he's the social-awareness node.

</details>

<details>
<summary><b>Sarah Okafor --- cognitive tensor (final state)</b></summary>

```json
{
  "knowledge_state": [
    "Mission objectives and timelines",
    "Crew member strengths and weaknesses",
    "NASA's expectations and priorities"
  ],
  "emotional_valence": -0.02,
  "emotional_arousal": 0.55,
  "energy_budget": 131.4,
  "decision_confidence": 0.41,
  "risk_tolerance": 0.41,
  "social_engagement": 0.40
}
```

Okafor's near-zero valence (-0.02) is the commander's burden: pulled between optimism and realism. Her knowledge overlaps with Webb's ("NASA's expectations") but includes "crew member strengths and weaknesses" that he lacks.

</details>

---

## 10. Mechanism Usage

14 of the 19 available mechanisms fired during this run. The counts below show which subsystems did the most work.

| Mechanism | Function | Calls | What it does |
|-----------|----------|:-----:|-------------|
| M3 | `_build_knowledge_from_exposures` | 44 | Build knowledge graph from exposure events (4 entities x 11 timepoints) |
| M8 | `couple_pain_to_cognition` | 44 | Physical state &rarr; cognitive state coupling (embodied cognition) |
| M11 | `synthesize_dialog` | 11 | Multi-party contextual conversation generation (one per timepoint) |
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

### Mechanism interaction chain

```
M17 (portal orchestrate)
 └─ generates 7 candidates per step, scores with 405B judge
     └─ M1+M17 (fidelity+temporal planning)
         └─ M6 (create tensors) → M6 (populate via LLM) → M6 (compress)
             └─ M3 (build knowledge from exposures)
                 └─ M8 (couple physical → cognitive state)
                     └─ M11 (synthesize dialog)
                         └─ M19 (extract knowledge from dialog)
                             └─ M3 (update knowledge graph) → loop
```

### LLM call distribution

| Call Type | Count | Model | Purpose |
|-----------|:-----:|-------|---------|
| context_relevance_scoring | 40 | Llama 3.1 70B | Score relevance of context for entity states |
| causal_chain_summary | 36 | Llama 3.1 70B | Summarize causal chains for backward inference |
| score_relevance | 18 | Llama 3.1 70B | Score candidate antecedent relevance |
| generate_structured | 15 | Llama 3.1 70B | Generate structured entity/timepoint data |
| generate_dialog | 11 | Llama 3.1 70B | Multi-party dialog synthesis |
| portal_simulation_judging | -- | Llama 3.1 405B | Judge 7 candidates per backward step |

**107 of 122 logged calls** used Llama 3.1 70B (standard workhorse). **12 calls** used Llama 3.1 405B (portal simulation judging --- the most expensive per-call operation). M18 (intelligent model selection) routed each call to the optimal model for the action type.

---

## 11. Training Data

This run generated **40 structured training examples** (prompt/completion pairs). Each example includes the entity's full causal history (M7), relationship context (M13), knowledge provenance (M3), and quantitative state (M6).

### Example training prompt structure

```
=== CAUSAL HISTORY (M7) ===
Timeline leading to current moment (3 events):
  tp_000_2031: Ares III loses contact during orbital insertion...
  tp_001_2030: Software bug discovered in mission control system...
  tp_002_2030: Zhang detects O2 generator anomalies...

=== RELATIONSHIP CONTEXT (M13) ===
Relationships with entities present:
  lin_zhang: collaborative (trust: 0.65, alignment: 0.55)
  sarah_okafor: cooperative (trust: 0.70, alignment: 0.60)
  thomas_webb: tense (trust: 0.40, alignment: 0.30)

=== KNOWLEDGE PROVENANCE (M3) ===
Primary sources: scene_initialization (3 items), lin_zhang (2 items)
Learning modes: experienced (70%), told (30%)
Recent: "oxygen generator has critical design flaw" (from lin_zhang, conf: 0.9)

=== ENTITY STATE (M6) ===
raj_mehta at T0:
  Physical: Age 35, energy 99/100
  Cognitive: 3 knowledge items, 0.46 decision confidence
  Emotional: Valence +0.78, Arousal 0.60

=== PREDICTION TASK ===
Predict: new knowledge, energy change, emotional impact, causal reasoning.
```

### Training data quality (post-fix)

The training data formatter was fixed on Feb 13, 2026 to produce varied, entity-specific data:

| Metric | Before fix | After fix |
|--------|-----------|-----------|
| Energy values | 89.0 (constant) | 99.3--149.4 (entity-specific) |
| Arousal values | 0.15 (constant) | 0.55--0.76 (entity-specific) |
| Knowledge arrays | `[]` (always empty) | 3 items per entity (sourced from exposure events) |

---

## 12. Run Metadata

<details>
<summary><b>Full run record</b></summary>

| Field | Value |
|-------|-------|
| run_id | `run_20260213_141539_9ba13680` |
| template_id | `mars_mission_portal` |
| started_at | 2026-02-13T14:15:39 |
| completed_at | 2026-02-13T18:34:45 |
| causal_mode | portal |
| entities_created | 4 |
| timepoints_created | 11 |
| training_examples | 40 |
| cost_usd | $0.983 |
| llm_calls | 1,596 |
| tokens_used | 1,762,921 |
| status | completed |
| fidelity_distribution | `{"trained": 4}` |
| narrative_exports | markdown, json, pdf |

</details>

### Output files

```
datasets/mars_mission_portal/
  narrative_20260213_183447.markdown   11,979 bytes
  narrative_20260213_183447.json       74,386 bytes
  narrative_20260213_183447.pdf         5,377 bytes
  shadow_report.json                   13,923 bytes
```

### Models used

All inference via OpenRouter. MIT/Apache 2.0/Llama-licensed models only --- all permit commercial synthetic data generation.

| Model | License | Role | Calls |
|-------|---------|------|:-----:|
| Llama 3.1 70B Instruct | Llama | Entity population, dialog synthesis, knowledge extraction, relevance scoring | 107 |
| Llama 3.1 405B Instruct | Llama | Portal simulation judging (7 candidates per backward step) | 12 |
| Mistral 7B Instruct | Apache 2.0 | Lightweight summarization | 1 |

---

## 13. What You Can Do Next

### Reproduce this run

```bash
git clone https://github.com/timepoint-ai/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here

./run.sh run mars_mission_portal    # ~$0.80-$1.00
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
print(f"Role stability: {results['role_stability']}")      # 1.00
print(f"Outcome similarity: {results['outcome_mean_similarity']}")  # 0.79
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

## 14. Port to Oxen.ai

Training data auto-uploads to [Oxen.ai](https://oxen.ai) when `OXEN_API_KEY` is set. Without it, everything saves locally.

### Auto-upload during a run

```bash
export OPENROUTER_API_KEY=your_key
export OXEN_API_KEY=your_oxen_token

./run.sh run mars_mission_portal
# → local JSONL + SQLite as usual
# → auto-uploads training_*.jsonl to Oxen.ai with commit history
# → prints dataset URL and fine-tune URL on completion
```

### Programmatic upload and versioning

```python
from oxen_integration import OxenClient

client = OxenClient(namespace="your-username", repo_name="mars-mission-data")

# Upload a dataset
result = client.upload_dataset("datasets/mars_mission_portal/training_20260213.jsonl",
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
    dataset_path="datasets/mars_mission_portal/training_20260213.jsonl",
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

## 15. API & Programmatic Access

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

*Generated from run `run_20260213_141539_9ba13680` on February 13, 2026. All data extracted from `metadata/runs.db` and `datasets/mars_mission_portal/`. Every number in this document comes from the database, not from documentation --- if you run the same template, you'll get different numbers but the same structural patterns.*
