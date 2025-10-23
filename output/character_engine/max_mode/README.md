# Timepoint MAX Mode Training Data

**Generated:** 2025-10-23T06:42:43.062868

## Overview

This repository contains training data from Timepoint's **MAX Mode** - a single massive vertical simulation showcasing all 17 Timepoint mechanisms at maximum depth.

## Configuration

- **Entities:** 50
- **Timepoints:** 100
- **Training Examples:** 225
- **Character Perspectives:** 4 (detective, doctor, villain, witness)
- **Resolution:** Hour-by-hour temporal tracking
- **Mechanisms:** All 17 Timepoint mechanisms demonstrated

## Mechanisms Demonstrated

1. **M1: Heterogeneous Fidelity** - Multiple resolution levels (TRAINED for main characters)
2. **M2: Progressive Training** - Characters improve skills over time
3. **M3: Exposure Events** - Complete observation tracking
4. **M4: Physics Validation** - Energy, biological constraints
5. **M5: Query-Driven Resolution** - Adaptive detail levels
6. **M6: TTM Tensors** - Character-specific cognitive models
7. **M7: Causal Temporal Chains** - Strict causality enforcement
8. **M8: Embodied States** - Physical/cognitive coupling
9. **M9: On-Demand Generation** - Dynamic entity creation
10. **M10: Scene Entities** - Atmospheric context
11. **M11: Dialog Synthesis** - Character interactions
12. **M12: Counterfactual Branching** - Alternative timelines
13. **M13: Multi-Entity Synthesis** - Relationship evolution
14. **M14: Circadian Patterns** - Time-dependent behavior
15. **M15: Entity Prospection** - Future planning/prediction
16. **M16: Animistic Entities** - Non-human entities (buildings, concepts)
17. **M17: Modal Causality** - Pearl-mode causal reasoning

## Training Format

Each example includes:
- **Prompt:** Character state + temporal context + observations
- **Completion:** Reasoning chain + deductions + next actions
- **Context:** Full mechanism metadata + TTM tensors + causal chains

## Fine-Tuning

To fine-tune a model on this data:

1. Navigate to this repository on Oxen.ai
2. Select the training data file
3. Use the web UI to create a fine-tuning job
4. Select branch: `finetune-max-{timestamp}`

## Use Cases

- Character roleplay with temporal reasoning
- Deductive reasoning with embodied constraints
- Multi-entity perspective modeling
- Causal chain tracking and validation

## Citation

```
Timepoint-Daedalus MAX Mode Training Data
Generated: 2025-10-23
Entities: 50, Timepoints: 100
Examples: 225
```
