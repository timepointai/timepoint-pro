# Timepoint-Daedalus

**Temporal simulation where detail follows attention, not allocation.**

## tl;dr 
Timepoint-Daedalus is a temporal simulation framework where detail follows queries, not pre-allocation. Instead of rendering every entity at every moment at full fidelity (expensive, wasteful), the system maintains a 2D resolution surface over (entity, time) that concentrates detail where you actually look. Minor characters exist as 200-token tensor embeddings until someone asks about them—then they're elevated while preserving causal consistency with everything already established.
The result: in theory, up to a 95% cost reduction without breaking temporal reasoning. You can still ask "what did Jefferson know when he wrote this?" because knowledge provenance is tracked explicitly, not summarized away.
Bonus weirdness: multiple temporal modes (including backward reasoning from known endpoints), entities that model their own futures, and objects/institutions with animistic agency.

#### Key feature: Timepoint Daedalus can "portal" to a future timepoint and make logical, judged steps backwards to current time, path seeking through simulated reality. See MECHANICS.md for details. 

---

## The Problem with Simulation

Traditional LLM-based simulations treat fidelity as uniform: every entity, every moment, rendered at the same resolution. This is expensive ($500/query for 100 entities across 10 timepoints) and wasteful—most of that detail is never queried.

Worse, compression-based solutions destroy temporal structure. You can't reason about causality in a lossy summary.

## The Insight

Timepoint-Daedalus inverts the model: **resolution is query-driven, not pre-allocated.** The system maintains a 2D fidelity surface across entities and time, concentrating detail where queries actually land—like a map that renders at higher resolution only where you zoom.

This isn't caching. It's a fundamentally different stance on what simulation *is*: not a pre-rendered world, but a generative process that resolves on demand while preserving causal structure.

---

## Core Ideas

### Heterogeneous Fidelity as First-Class Concept

Each (entity, timepoint) pair maintains independent resolution: `TENSOR_ONLY → SCENE → GRAPH → DIALOG → TRAINED`. A minor attendee at the Constitutional Convention exists as a 200-token tensor embedding until someone asks about them—then the system elevates their resolution, synthesizes their perspective, and preserves causal consistency with what's already established.

Result: 95% token reduction without temporal incoherence.

### Multiple Temporal Ontologies

Time isn't one thing. The system supports distinct temporal modes drawn from narrative theory and causal inference:

- **Pearl**: Standard causal DAG—causes precede effects
- **Portal**: Backward reasoning from known outcomes to plausible causes (how did we get to a $1.2B valuation?)
- **Directorial**: Narrative time with flashbacks, foreshadowing, ellipsis
- **Branching**: Counterfactual timelines that diverge from decision points
- **Cyclical**: Prophetic/mythic time where future states constrain past events

Each mode changes what "temporal consistency" means and how the causal validators operate.

### Knowledge Provenance via Exposure Events

Entities don't magically know things. The system tracks *exposure events*: who learned what, from whom, when. This enables:

- Preventing anachronistic knowledge ("How does Jefferson know about the Louisiana Purchase in 1787?")
- Tracing belief formation and information flow
- Answering counterfactuals ("If Madison hadn't shared his notes, what would Hamilton believe?")

### Animistic Agency and Entity Prospection

Two deliberately human extensions:

**M15 (Prospection)**: Entities model their own futures, with those models influencing present behavior. A founder considering a pivot doesn't just react to current state—they simulate consequences and act on those simulations.

**M16 (Animistic Agency)**: Objects, institutions, and places can have agency. The conference room "wants" productive meetings; the startup's codebase "resists" certain architectural changes. This captures how non-human entities shape behavior without requiring explicit rules.

---

## What This Enables

**Natural language to queryable simulation:**
```
"Simulate the founding team's first board meeting after 
learning a competitor raised $50M. Focus on how information 
flows between the CEO and CTO, and what each believes the 
other is thinking."
```

The system generates entities at appropriate resolution, simulates the scenario with causal consistency, and allows follow-up queries that elevate specific entities or moments as needed.

**Temporal queries across fidelity levels:**
- "What did the CTO know at 2pm that she didn't know at 10am?"
- "Trace how the competitor news changed the CEO's position on the pivot"
- "Branch: what if the CTO had learned the news first?"

**Fine-tuning data generation:**
- Horizontal: many scenario variations for training breadth
- Vertical: deep temporal simulations for training causal reasoning

---

## Architecture (Brief)

The 18 mechanisms in MECHANICS.md implement these ideas:

| Concept | Mechanisms |
|---------|------------|
| Heterogeneous fidelity | M1 (fidelity graphs), M2 (progressive training), M5 (lazy elevation), M6 (tensor compression) |
| Temporal reasoning | M7 (causal chains), M8 (vertical expansion), M12 (counterfactual branching) |
| Knowledge tracking | M3 (graph construction), M4 (embedding), M9 (on-demand generation) |
| Synthesis | M10 (scene management), M11 (dialog), M13 (multi-entity), M15 (prospection), M16 (animistic agency) |
| Infrastructure | M14 (circadian patterns), M17 (metadata tracking), **M18 (model selection)** |

See [MECHANICS.md](MECHANICS.md) for implementation details.

---

## Intelligent Model Selection (M18)

Timepoint-Daedalus includes a capability-based model selection system that automatically chooses the optimal LLM for each action type. This enables:

- **Action-appropriate models**: Math-heavy reasoning uses DeepSeek-R1; dialog synthesis uses Llama 3.1 70B
- **Cost optimization**: Fast/cheap models for simple tasks, expensive models only when needed
- **Automatic fallbacks**: If a model fails, the system retries with alternatives
- **License compliance**: Only open-source models that permit commercial synthetic data generation

### Supported Models (via OpenRouter)

| Model | Strengths | License |
|-------|-----------|---------|
| Llama 3.1 (8B/70B/405B) | Dialog, general reasoning | Llama 3.1 |
| Llama 4 Scout | Multimodal, balanced | Llama 4 |
| Qwen 2.5 (7B/72B) | Structured JSON, code | Qwen |
| QwQ 32B | Mathematical reasoning | Qwen |
| DeepSeek Chat/R1 | Deep reasoning, math | **MIT** |
| Mistral/Mixtral | Fast inference, cost-efficient | **Apache 2.0** |

### Usage

```python
from llm_service import LLMService, ActionType

service = LLMService(config)

# Automatic model selection based on action type
response = service.call_with_action(
    action=ActionType.DIALOG_SYNTHESIS,
    system="You are a dialog generator",
    user="Generate a conversation between two founders"
)

# Override with preferences
response = service.call_with_action(
    action=ActionType.TEMPORAL_REASONING,
    system="You are a causal analyst",
    user="What events led to this outcome?",
    prefer_quality=True  # Selects highest-quality model for the task
)

# Structured output with action-appropriate model
from pydantic import BaseModel

class EntityProfile(BaseModel):
    name: str
    traits: dict
    knowledge: list[str]

entity = service.structured_call_with_action(
    action=ActionType.ENTITY_POPULATION,
    system="Generate entity profiles",
    user="Create a profile for a skeptical board member",
    schema=EntityProfile
)
```

---

## Quick Start

```bash
git clone https://github.com/yourusername/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt

# Set your OpenRouter API key
export OPENROUTER_API_KEY=your_key_here

# Run a simulation
./run.sh quick
```

### Basic Usage

```python
from nl_interface import NLConfigGenerator
from orchestrator import simulate_event

# Generate config from natural language
generator = NLConfigGenerator()
config, confidence = generator.generate_config(
    "Simulate a hospital ethics committee debating an edge case. "
    "Track how each member's position evolves as new information surfaces."
)

# Execute with appropriate fidelity
result = simulate_event(config['scenario'], llm, store, context={
    "temporal_mode": "pearl",
    "max_entities": 7,
    "max_timepoints": 5
})

# Query results
from reporting.query_engine import EnhancedQueryEngine
engine = EnhancedQueryEngine()

# This query elevates resolution for Dr. Chen as needed
chen_evolution = engine.query(
    "How did Dr. Chen's position change, and what caused each shift?"
)
```

---

## Performance

| Scenario | Naive Cost | Timepoint-Daedalus | Reduction |
|----------|------------|---------------------|-----------|
| 5 entities, 5 timepoints | ~$25 | $1-2 | 92-96% |
| 20 entities, 10 timepoints | ~$100 | $5-8 | 92-95% |
| 100 entities, 20 timepoints | ~$500 | $20-30 | 94-96% |

Cost reduction comes from query-driven fidelity, not lossy compression—temporal consistency is preserved.

---

## Current State (November 2025)

**What works today:**

```bash
# Clone and install
git clone https://github.com/yourusername/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt

# Set API key
export OPENROUTER_API_KEY=your_key_here

# Run simulations
./run.sh quick              # 9 templates, ~$9-18
./run.sh portal-test        # PORTAL mode tests
./run.sh portal-timepoint   # Real founder profiles
./run.sh --nl "prompt"      # Natural language input
```

**Implemented:**
- 18 simulation mechanisms (M1-M18)
- M18: Intelligent per-action model selection (12 open-source models)
- PORTAL mode (backward temporal reasoning)
- Natural language interface integration
- Single-run execution with full mechanism tracking
- SQLite persistence (metadata/runs.db)
- Basic dashboard (Quarto + FastAPI)
- Narrative exports (Markdown, JSON, PDF)

**License-Compliant Model Stack:**
All models via OpenRouter, all open-source with commercial synthetic data rights:
- **MIT**: DeepSeek Chat, DeepSeek R1 (most permissive)
- **Apache 2.0**: Mistral 7B, Mixtral 8x7B/8x22B
- **Llama License**: Llama 3.1 8B/70B/405B, Llama 4 Scout
- **Qwen License**: Qwen 2.5 7B/72B, QwQ 32B

**Not yet implemented:**
- Batch execution / parallelization
- REST API
- External integrations (prediction markets, webhooks)
- Containerization / distributed deployment

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Timepoint-Daedalus                       │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  orchestrator.py│  │   workflows/    │  │ validation.py│ │
│  │  (scene control)│  │ (temporal agent)│  │ (validators) │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘  │
│           │                    │                   │        │
│           └────────────────────┼───────────────────┘        │
│                                │                            │
│  ┌─────────────────────────────▼─────────────────────────┐  │
│  │                    llm_service/                       │  │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────┐  │  │
│  │  │ service.py   │  │model_selector │  │ providers/ │  │  │
│  │  │(LLM facade)  │  │(M18: 12 models)│  │(OpenRouter)│  │  │
│  │  └──────────────┘  └───────────────┘  └────────────┘  │  │
│  └─────────────────────────────┬─────────────────────────┘  │
│                                │                            │
│  ┌─────────────────────────────▼─────────────────────────┐  │
│  │                    storage.py                         │  │
│  │              (SQLite persistence)                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   OpenRouter API      │
                    │  (12 Open-Source LLMs)│
                    │  Llama│Qwen│DeepSeek  │
                    └───────────────────────┘
```

**Key modules:**
- `orchestrator.py` (1,666 lines): Scene orchestration, entity generation
- `workflows/` (9 submodules): TemporalAgent, temporal modes, PORTAL
  - `temporal_agent.py`, `dialog_synthesis.py`, `portal_strategy.py`, etc.
- `llm_service/`: Model selection, providers, logging
- `nl_interface/`: Natural language to simulation config
- `validation.py` (1,365 lines): 5 physics-inspired validators
- `storage.py` (407 lines): SQLite persistence layer with transaction support
- `generation/templates/`: 16 JSON simulation templates

---

## When to Use This

**Good fit:**
- Exploring "how might we get from here to there" scenarios (PORTAL mode)
- Simulations requiring causal consistency and knowledge provenance
- Training data generation for temporal/causal reasoning
- Scenarios where you'll query specific entities/moments deeply

**Not the right tool (yet):**
- High-volume batch simulations (no parallelization yet)
- Production systems requiring SLAs (research prototype)
- Real-time applications (LLM latency dominates)

---

## The Vision

Timepoint today is a **simulation engine**. The roadmap leads toward a **simulation infrastructure platform**:

**Near-term (Q1-Q2 2026):**
- Batch execution with parallel workers
- PostgreSQL for production persistence
- REST API for programmatic access
- Containerized deployment

**Medium-term (Q3-Q4 2026):**
- External integrations (prediction markets, decision systems)
- Advanced dashboard (timeline visualization, entity graphs)
- Distributed execution at scale

**Long-term (2027+):**
- Consumer experiences ("synthetic time travel")
- Platform ecosystem (plugins, vertical solutions)
- Immersive interfaces (VR/AR exploration)

See [MILESTONES.md](MILESTONES.md) for the detailed roadmap.

---

## Documentation

- **[MECHANICS.md](MECHANICS.md)**: Technical specification of all 18 mechanisms
- **[MILESTONES.md](MILESTONES.md)**: Roadmap from prototype to platform
- **[QUICKSTART.md](QUICKSTART.md)**: Quick start guide for natural language simulations

---

## License

MIT