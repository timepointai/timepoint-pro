# Example Run: Ares III Mars Mission Portal

**[Back to README](README.md)** | **[Full Dialog Transcript (93 turns)](EXAMPLE_DIALOGS.md)** | Run ID: `run_20260214_080150_efa48a93` | Template: `mars_mission_portal`

A complete PORTAL-mode simulation tracing backward from a catastrophic Mars mission failure in 2031 to its institutional origins in 2026. Every number, dialog line, and graph edge below was produced by a single `./run.sh run mars_mission_portal` invocation on February 14, 2026.

---

## At a Glance

| | |
|---|---|
| **Mode** | PORTAL (backward temporal reasoning) |
| **Timespan** | 2031 &rarr; 2026 (5 years, 10 backward steps) |
| **Entities** | 4 humans, all reaching TRAINED resolution |
| **Dialogs** | 10 conversations, 93 exchanges (tp_010 dialog failed) |
| **Knowledge graph** | 240 typed exposure events, 228 information transfers |
| **Training examples** | 40 structured prompt/completion pairs |
| **Mechanisms fired** | 14 of 19 |
| **ADPRS waveform gating** | 44 evaluations, 25% divergence |
| **Cost** | $0.99 &bull; 1,584 LLM calls &bull; 1.76M tokens |
| **Convergence** | 7 runs of this template: outcome similarity 0.79, role stability 1.00 |

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

The result: a 5-year causal graph showing how a negative performance review silenced a cautious engineer, a secret auditor referral exposed institutional rot, and a public scandal forced leadership restructuring --- all too late to prevent catastrophe. Produced for under a dollar.

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
Result: Causal chain from Jan 2026 -> Mar 2031
```

Each backward step costs ~$0.09 (7 candidates x 405B scoring). The system spent $0.99 total across 1,584 LLM calls to produce 11 timepoints, 240 exposure events, and 40 training examples.

---

## 2. Cast of Characters

Four crew members, each with tracked cognitive state, emotional arcs, and distinct knowledge bases. All defined in the template's `entity_roster` and carried through the full simulation.

| Character | Role | Final Valence | Final Arousal | Final Energy | Exposure Events |
|-----------|------|:---:|:---:|:---:|:---:|
| **Sarah Okafor** | Mission Commander. Experienced, politically pressured by NASA leadership. | +0.48 | 0.73 | 119.6 | 63 |
| **Raj Mehta** | Flight Engineer. Cautious analyst, penalized for excessive caution. | +0.04 | 0.72 | 119.6 | 58 |
| **Lin Zhang** | Systems Engineer. Detected anomalies, escalated through unconventional channels. | -0.34 | 0.74 | 99.5 | 61 |
| **Thomas Webb** | Mission Director (ground). Prioritized schedule over safety, eventually replaced. | +0.04 | 0.99 | 131.5 | 58 |

**Emotional arcs**: Webb's arousal hits 0.99 --- the highest possible --- reflecting extreme activation under institutional scrutiny after the public scandal. Zhang's negative valence (-0.34) captures the frustration of being overruled despite being right, driving her to contact an external auditor. Mehta and Okafor share identical energy (119.6), but Okafor's higher valence (+0.48) reflects her commander's optimism while Mehta's neutral valence (+0.04) shows the emotional cost of being penalized for caution. Zhang's energy is lowest at 99.5 --- the whistleblower depletes fastest.

Each entity received 3 initial knowledge items from `scene_initialization` and accumulated 55--60 additional items through dialog-driven exposure events across 10 active timepoints.

---

## 3. Backward Timeline

Portal mode traces backward from the 2031 failure. Each step was selected from 7 candidates scored by simulation judging (best coherence: 0.827). All 4 entities are present at every timepoint.

```
Step   Year     Event
 0     Mar 31   Ares III loses contact during orbital insertion --- cascading life support + comms failure
 1     Jul 30   Raj detects life support anomalies during routine test; hesitates to escalate (fear of being seen as overly cautious)
 2     Jan 30   Raj receives negative performance review citing excessive caution; Okafor assigned as new Commander; Zhang detects O2 anomalies, overruled by Webb
 3     Jul 29   Webb allocates $5M for system redundancy; Raj's caution reinforced by NASA risk workshop; Okafor develops contingency plan
 4     Jan 29   External auditor report highlights risks of simplified life support; Raj continues analyzing anomaly detection protocols
 5     Jul 28   Zhang secretly contacts external auditor to review life support design; auditor report later prompts Webb to allocate funds
 6     Jan 28   NASA cost-saving scandal exposed publicly; Webb's decisions scrutinized; Zhang's concerns vindicated; Okafor re-evaluates safety protocols
 7     Jul 27   Raj discovers critical life support design flaw; reports to Zhang, who escalates to Webb; Webb rejects concerns (schedule/budget)
 8     Jan 27   Okafor under NASA pressure emphasizes deadline; Webb prioritizes schedule, accepts simplified life support design; Raj & Zhang suspect safety compromise
 9     Jul 26   NASA restructures leadership, Webb replaced; new director prioritizes safety; Zhang & Raj tasked with adapting design; Okafor maintains launch deadline pressure
10     Jan 26   NASA regulatory change: new crew safety guidelines; Webb re-evaluates but proceeds with original plan; Zhang & Raj develop adaptation plan
```

The causal chain reveals a different institutional failure pattern from previous runs. Raj Mehta's excessive caution is punished by a negative performance review (Step 2), creating a psychological barrier to escalation at the critical moment (Step 1). Zhang takes the unconventional route of secretly contacting an external auditor (Step 5), which triggers a public scandal (Step 6) and eventual leadership restructuring (Step 9) --- but the damage is already embedded in the system design. The failure isn't any single decision; it's the compound effect of Raj's hesitation, Webb's schedule pressure, and institutional inertia, even after warnings are validated.

<details>
<summary><b>Full timeline descriptions (LLM-generated)</b></summary>

**Step 0 (March 2031)**: Ares III crewed Mars mission loses contact during orbital insertion. Last telemetry shows cascading systems failures in life support and communications. The mission was celebrated as humanity's greatest achievement until silence fell. Trace backward to understand how this disaster was built, decision by decision.

**Step 1 (July 2030)**: Raj Mehta detects anomalies in life support during routine test. Hesitates to escalate to Okafor due to fear of being seen as overly cautious --- a fear cemented by his negative performance review months earlier. The anomalies go unreported until it's too late.

**Step 2 (January 2030)**: Raj receives negative performance review citing excessive caution. Okafor is assigned as new Mission Commander. Zhang detects O2 anomalies but is overruled by Webb, who dismisses the findings as within acceptable tolerances.

**Step 3 (July 2029)**: Webb allocates $5M for system redundancy after external pressure. Raj's cautious approach is reinforced by a NASA risk management workshop. Okafor develops a contingency plan, but the underlying design compromises remain.

**Step 4 (January 2029)**: External auditor report highlights risks of simplified life support design. Raj continues analyzing anomaly detection protocols but lacks institutional support to push for changes.

**Step 5 (July 2028)**: Zhang, frustrated by internal resistance, secretly contacts an external auditor to review life support design. The auditor report later prompts Webb to allocate funds for redundancy, but the core design is not revisited.

**Step 6 (January 2028)**: NASA cost-saving scandal exposed publicly. Webb's decisions are scrutinized in media coverage. Zhang's earlier concerns are vindicated. Okafor re-evaluates safety protocols, but institutional momentum keeps the mission on its original trajectory.

**Step 7 (July 2027)**: Raj discovers a critical life support design flaw during routine analysis. He reports it to Zhang, who escalates to Webb. Webb rejects the concerns, citing schedule constraints and budget limitations. The flaw is documented but not addressed.

**Step 8 (January 2027)**: Okafor, under pressure from NASA leadership, emphasizes the launch deadline above all else. Webb prioritizes the schedule and accepts a simplified life support design to save time and money. Raj and Zhang both suspect the safety margin has been compromised, but their concerns are logged without action.

**Step 9 (July 2026)**: NASA restructures leadership, replacing Webb with a new director who prioritizes safety. Zhang and Raj are tasked with adapting the life support design to new standards. However, Okafor maintains launch deadline pressure, limiting how much redesign is feasible.

**Step 10 (January 2026)**: NASA issues a regulatory change mandating new crew safety guidelines. Webb re-evaluates the mission plan but ultimately proceeds with the original design. Zhang and Raj develop an adaptation plan, but the window for fundamental design changes has passed.

</details>

---

## 4. Sample Dialogs

Every timepoint generates a multi-party dialog with tracked confidence scores and knowledge references. All 4 characters participate in every conversation. 10 dialogs completed successfully (tp_010 dialog failed --- 0 turns), producing 93 turns and 228 information transfers.

### Dialog at tp_000_2031 --- 9 turns

> **Lin Zhang** *(concerned, conf 0.8)*: Look, we've got a 12% increase in telemetry errors over the past hour.
>
> **Sarah Okafor** *(urgent, conf 0.9)*: We can't afford to delay. We're already 2 hours behind schedule. Let's get to it.
>
> **Thomas Webb** *(calm, conf 0.7)*: By the numbers, we're running 5% behind schedule. We can still make it.
>
> **Lin Zhang** *(insistent, conf 0.85)*: I'm telling you, it's not just a glitch. We need to dig deeper. Look at the error codes.
>
> **Raj Mehta** *(informative, conf 0.9)*: You see, Captain, the navigation system is malfunctioning due to a software glitch, not a hardware issue.

*(+4 more turns...)*

### Dialog at tp_003_2029 --- 10 turns

> **Lin Zhang** *(concerned, conf 0.9)*: Look, the logs show a 3.7% increase in anomalies over the past week. We need to dig deeper.
>
> **Raj Mehta** *(cautious, conf 0.9)*: Ah, I agree with Lin. The data suggests a 12% increase in telemetry errors over the past hour. We need to recalibrate the fuel injectors to optimize burn rate.
>
> **Thomas Webb** *(urgent, conf 0.9)*: By the numbers, we've got a 14-minute window to adjust course before hitting the critical juncture. Let's not waste it.
>
> **Sarah Okafor** *(determined, conf 0.8)*: Let's get to it. We've got a 74% chance of success. We can't afford to delay, but we also can't afford to ignore these anomalies.
>
> **Lin Zhang** *(frustrated, conf 0.8)*: I'm telling you, it's not just a glitch. We need to investigate further.

*(+5 more turns...)*

Context flags applied per dialog: `physical_states`, `emotional_states`, `body_mind_coupling`, `relationship_context`, `knowledge_provenance`, `temporal_awareness`

Voice distinctiveness across the run ranges from 0.57 to 0.91. Zhang's insistent technical specificity ("Look, the logs show...") contrasts with Webb's schedule-driven framing ("By the numbers...") and Mehta's analytical hedging ("Ah, I agree with...").

---

## 5. Knowledge Provenance

The system tracks **240 typed exposure events** across the simulation. Every fact an entity knows has a source, a timestamp, and a confidence score. Entities can't know things without a tracked exposure event --- anachronisms are structurally prevented.

### Event distribution by timepoint

| Timepoint | Events | Key content |
|-----------|:------:|-------------|
| pre_tp_001 (initial) | 12 | Scene initialization: mission objectives, safety protocols, budget constraints (3 per entity) |
| tp_000 (2031) | 21 | Mission failure debrief: systems failures, crew status, communication loss |
| tp_001 (Jul 2030) | 21 | Raj's anomaly detection, escalation hesitation, life support test results |
| tp_002 (Jan 2030) | 24 | Negative performance review, Okafor's assignment, Zhang's O2 anomalies overruled |
| tp_003 (Jul 2029) | 24 | $5M redundancy allocation, risk workshop reinforcement, contingency planning |
| tp_004 (Jan 2029) | 6 | External auditor report, anomaly detection protocol analysis |
| tp_005 (Jul 2028) | 30 | Zhang's secret auditor contact, life support design review |
| tp_006 (Jan 2028) | 36 | Public scandal, Webb's scrutiny, Zhang's vindication, safety re-evaluation |
| tp_007 (Jul 2027) | 24 | Design flaw discovery, Raj-to-Zhang-to-Webb escalation chain, rejection |
| tp_008 (Jan 2027) | 24 | NASA deadline pressure, simplified life support acceptance, safety compromise |
| tp_009 (Jul 2026) | 18 | Leadership restructuring, Webb replaced, design adaptation tasking |

### Exposure events by entity

| Entity | Total Events | Unique Sources | Role Pattern |
|--------|:---:|:---:|---|
| sarah_okafor | 63 | 4 | Most exposed: authority node connecting NASA leadership to crew concerns |
| lin_zhang | 61 | 4 | Whistleblower: generates technical findings, escalates through unconventional channels |
| thomas_webb | 58 | 4 | Gatekeeper: receives critical information but filters through schedule-first lens |
| raj_mehta | 58 | 4 | Suppressed relay: holds key data but psychologically blocked from escalating |

### Sample exposure chain

```
[pre_tp_001] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "Mission objectives and timelines"

[pre_tp_001] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "Crew member skills and strengths"

[pre_tp_001] sarah_okafor <- scene_initialization (initial, conf=1.0):
  "NASA's expectations for the mission"
```

Each entity receives 3 initial knowledge items, totaling 12 initial exposure events. The remaining 228 events are dialog-driven transfers --- information flowing between entities during conversations. Sarah Okafor accumulates the most exposure events (63) with the highest positive valence (+0.48), reflecting her centrality as the command node. Webb and Mehta tie at 58 events but for different reasons: Webb filters information through budget constraints while Mehta is psychologically blocked from acting on what he knows.

---

## 6. Outcome Convergence

This is where things get interesting. Running the same template multiple times with the same LLM produces different surface-level details but converges on the same structural outcomes. This is the core evidence that the simulation captures something real about institutional dynamics, not just random LLM output.

### 7 runs of `mars_mission_portal`

| Run | Date | Cost | Exposure Events | Dialogs | Timepoints |
|-----|------|:----:|:---:|:---:|:---:|
| `946db667` | Feb 6 | $0.52 | 225 | 11 | 11 |
| `3ba043b2` | Feb 9 | $0.51 | 201 | 10 | 11 |
| `baae2120` | Feb 11 | $0.91 | 238 | 11 | 11 |
| `7d55d9c6` | Feb 11 | $0.38 | 174 | 6 | 6 |
| `7f33adbd` | Feb 12 | $1.00 | 267 | 11 | 11 |
| `9ba13680` | Feb 13 | $0.98 | 234 | 11 | 11 |
| **`efa48a93`** | **Feb 14** | **$0.99** | **240** | **10** | **11** |

### Convergence metrics (computed across 3+ comparable runs)

| Metric | Score | What it measures |
|--------|:-----:|-----------------|
| **Outcome similarity** | **0.79** | Do runs reach the same conclusions? (role assignments, event sequences, knowledge discovery) |
| **Role stability** | **1.00** | Do the same characters play the same structural roles? (Zhang=source, Webb=blocker, Mehta=relay, Okafor=authority) |
| **Knowledge convergence** | **0.60** | Do the same facts get discovered? (life support flaw, budget constraints, crew dynamics) |
| **Structural similarity** | **0.57** | Do the same causal edges appear? (Jaccard over temporal + knowledge edges) |

**What this means**: Role stability is 1.00 --- across every run, Zhang identifies the technical problem, Webb dismisses it, Mehta mediates, Okafor tries to intervene from above. The characters aren't randomly assigned to narrative roles; the simulation's knowledge provenance and personality parameters drive them to the same structural positions every time.

Outcome similarity at 0.79 means the runs agree on *what happens* (catastrophe built from institutional dysfunction) even when the specific dialog lines, exposure events, and edge structures differ. This run's distinctive features --- the negative performance review suppressing Raj, Zhang's secret auditor contact, the public scandal --- are surface variations on the same deep pattern. Structural similarity is lower (0.57) because there are many valid causal paths to the same outcome, which is exactly what you'd expect from a real organizational failure.

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

| Entity | &phi; Range | Predicted Band | Actual Level | Divergent? |
|--------|:-----------:|:--------------:|:------------:|:----------:|
| lin_zhang | 0.852--0.858 | trained | dialog | Always (11/11) |
| raj_mehta | 0.739--0.750 | dialog | dialog | Never |
| sarah_okafor | 0.662--0.665 | dialog | dialog | Never |
| thomas_webb | 0.652--0.655 | dialog | dialog | Never |

**Overall**: 44 evaluations, 11 divergent (25%), mean divergence 0.25 bands.

This run shows a meaningful divergence pattern: all 11 divergent records belong to Lin Zhang, whose &phi; (0.852--0.858) is high enough that the ADPRS system predicts `trained` band, but she actually resolves at `dialog`. Zhang's consistently high activation reflects her role as the primary technical source and whistleblower --- she's the most cognitively engaged character at every timepoint. The remaining three entities stay in the `dialog` band as predicted, with no divergence.

### Why 25% divergence matters

In the previous run, divergence was 0%. This run's 25% divergence --- concentrated entirely in one entity --- is structurally informative. Zhang's activation (&phi; > 0.85) is the highest in the cast, driven by her technical conviction and frustration at being overruled. The ADPRS system recognizes she *should* get maximum fidelity resources, but the system-level resolution keeps her at `dialog` band. This is a signal that Zhang's narrative role demands more computational depth than the other characters.

The three non-divergent entities (Mehta at 0.739--0.750, Okafor at 0.662--0.665, Webb at 0.652--0.655) form a clean hierarchy: the relay, the authority, and the blocker each occupy a distinct activation tier, all within the `dialog` band.

---

## 8. Fidelity Strategy

The system plans a fidelity budget before execution, then adapts during the run. The gap between planned and actual reveals where the scenario demanded more detail than expected.

### Planned vs. actual

| Metric | Planned | Actual |
|--------|---------|--------|
| Fidelity schedule | tensor &rarr; scene &rarr; graph &rarr; dialog | All `trained` |
| Token budget | 30,000 | 1,763,573 |
| Budget compliance | -- | 58.8x over (soft budget mode) |
| Resolution distribution | mixed | All entities at `trained` |
| Cost estimate | $0.067 | $0.986 |

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
    "Mission objectives and timelines",
    "Budget constraints and resource allocation",
    "NASA's expectations for the mission"
  ],
  "emotional_valence": 0.04,
  "emotional_arousal": 0.99,
  "energy_budget": 131.5,
  "decision_confidence": 0.285,
  "risk_tolerance": 0.26,
  "social_engagement": 0.25
}
```

Webb's near-zero valence (+0.04) and extreme arousal (0.99) capture a man under maximum institutional pressure --- the public scandal and leadership restructuring have pushed his activation to the ceiling. His energy remains high (131.5) because he's directing, not executing. Low confidence (0.285) and risk tolerance (0.26) reflect a gatekeeper whose authority has been undermined.

</details>

<details>
<summary><b>Lin Zhang --- cognitive tensor (final state)</b></summary>

```json
{
  "knowledge_state": [
    "Mission system designs and flaws",
    "Anomalies and warning signs",
    "Crew member concerns and conflicts"
  ],
  "emotional_valence": -0.34,
  "emotional_arousal": 0.74,
  "energy_budget": 99.5,
  "decision_confidence": 0.52,
  "risk_tolerance": 0.51,
  "social_engagement": 0.50
}
```

Zhang has the highest decision confidence (0.52) and the lowest energy (99.5) --- the cost of being right but unheard. Her negative valence (-0.34) is the frustration of a whistleblower who went outside the chain of command. Her knowledge uniquely includes "Anomalies and warning signs" --- she's the technical conscience of the mission.

</details>

<details>
<summary><b>Raj Mehta --- cognitive tensor (final state)</b></summary>

```json
{
  "knowledge_state": [
    "Mission systems and technical specifications",
    "Potential risks and failure points",
    "Crew member concerns and conflicts"
  ],
  "emotional_valence": 0.04,
  "emotional_arousal": 0.72,
  "energy_budget": 119.6,
  "decision_confidence": 0.46,
  "risk_tolerance": 0.43,
  "social_engagement": 0.44
}
```

Mehta's neutral valence (+0.04) and moderate arousal (0.72) reflect emotional suppression --- the performance review penalizing his caution trained him to hold back. His knowledge includes "Potential risks and failure points," making his silence at Step 1 structurally tragic: he had the information but not the psychological safety to act on it.

</details>

<details>
<summary><b>Sarah Okafor --- cognitive tensor (final state)</b></summary>

```json
{
  "knowledge_state": [
    "Mission objectives and timelines",
    "Crew member skills and strengths",
    "NASA's expectations for the mission"
  ],
  "emotional_valence": 0.48,
  "emotional_arousal": 0.73,
  "energy_budget": 119.6,
  "decision_confidence": 0.41,
  "risk_tolerance": 0.41,
  "social_engagement": 0.40
}
```

Okafor's positive valence (+0.48) is the highest in the cast --- the commander's optimism persists even as the mission unravels. Her knowledge overlaps with Webb's ("NASA's expectations") but includes "Crew member skills and strengths" that he lacks. She and Mehta share identical energy (119.6), reflecting their parallel positions as the two characters caught between institutional pressure and technical reality.

</details>

---

## 10. Mechanism Usage

14 of the 19 available mechanisms fired during this run. The counts below show which subsystems did the most work.

| Mechanism | Function | Calls | What it does |
|-----------|----------|:-----:|-------------|
| M3 | `_build_knowledge_from_exposures` | 44 | Build knowledge graph from exposure events (4 entities x 11 timepoints) |
| M8 | `couple_pain_to_cognition` | 44 | Physical state &rarr; cognitive state coupling (embodied cognition) |
| M11 | `synthesize_dialog` | 10 | Multi-party contextual conversation generation (one per successful timepoint) |
| M19 | `extract_knowledge_from_dialog` | 10 | Post-dialog knowledge extraction, creating new exposure events |
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

Note the difference from previous runs: M11 and M19 fire 10 times (not 11) because tp_010's dialog failed, producing 0 turns. The remaining mechanisms are unaffected --- knowledge was still built and tensors still updated for the final timepoint via non-dialog channels.

### Mechanism interaction chain

```
M17 (portal orchestrate)
 +-- generates 7 candidates per step, scores with 405B judge
     +-- M1+M17 (fidelity+temporal planning)
         +-- M6 (create tensors) -> M6 (populate via LLM) -> M6 (compress)
             +-- M3 (build knowledge from exposures)
                 +-- M8 (couple physical -> cognitive state)
                     +-- M11 (synthesize dialog)
                         +-- M19 (extract knowledge from dialog)
                             +-- M3 (update knowledge graph) -> loop
```

### LLM call distribution

| Call Type | Count | Model | Purpose |
|-----------|:-----:|-------|---------|
| context_relevance_scoring | 40 | Llama 3.1 70B | Score relevance of context for entity states |
| causal_chain_summary | 36 | Llama 3.1 70B | Summarize causal chains for backward inference |
| score_relevance | 18 | Llama 3.1 70B | Score candidate antecedent relevance |
| generate_structured | 15 | Llama 3.1 70B | Generate structured entity/timepoint data |
| generate_dialog | 10 | Llama 3.1 70B | Multi-party dialog synthesis |
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
  tp_001_2030: Raj detects life support anomalies, hesitates to escalate...
  tp_002_2030: Raj receives negative performance review...

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
  Physical: Age 35, energy 119.6/150
  Cognitive: 3 knowledge items, 0.46 decision confidence
  Emotional: Valence +0.04, Arousal 0.72

=== PREDICTION TASK ===
Predict: new knowledge, energy change, emotional impact, causal reasoning.
```

### Training data quality

The training data formatter produces varied, entity-specific data:

| Metric | Value |
|--------|-------|
| Energy values | 99.5--131.5 (entity-specific) |
| Arousal values | 0.72--0.99 (entity-specific) |
| Knowledge arrays | 3 items per entity (sourced from exposure events) |

---

## 12. Run Metadata

<details>
<summary><b>Full run record</b></summary>

| Field | Value |
|-------|-------|
| run_id | `run_20260214_080150_efa48a93` |
| template_id | `mars_mission_portal` |
| started_at | 2026-02-14T08:01:50 |
| completed_at | 2026-02-14T10:30:30 |
| duration | 8,919.5s (~2.5 hours) |
| causal_mode | portal |
| entities_created | 4 |
| timepoints_created | 11 |
| training_examples | 40 |
| cost_usd | $0.986 |
| llm_calls | 1,584 |
| tokens_used | 1,763,573 |
| status | completed |
| fidelity_distribution | `{"trained": 4}` |
| narrative_exports | markdown, json, pdf |

</details>

### Output files

```
datasets/mars_mission_portal/
  narrative_20260214_103030.markdown   (narrative export)
  narrative_20260214_103030.json       (structured data)
  narrative_20260214_103030.pdf        (PDF export)
  shadow_report.json                   (ADPRS evaluation)
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
# -> local JSONL + SQLite as usual
# -> auto-uploads training_*.jsonl to Oxen.ai with commit history
# -> prints dataset URL and fine-tune URL on completion
```

### Programmatic upload and versioning

```python
from oxen_integration import OxenClient

client = OxenClient(namespace="your-username", repo_name="mars-mission-data")

# Upload a dataset
result = client.upload_dataset("datasets/mars_mission_portal/training_20260214.jsonl",
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
    dataset_path="datasets/mars_mission_portal/training_20260214.jsonl",
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

*Generated from run `run_20260214_080150_efa48a93` on February 14, 2026. All data extracted from `metadata/runs.db` and `datasets/mars_mission_portal/`. Every number in this document comes from the database, not from documentation --- if you run the same template, you'll get different numbers but the same structural patterns.*
