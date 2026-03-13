# Project Configuration (AI Agent Reference)

## Philosophy

**Core Insight**: Temporal simulation isn't one problem—it's at least five different problems depending on what "time" means. This codebase treats temporal mode as a first-class architectural dimension.

**Design Principles**:
- **Fidelity follows attention**: Resolution is heterogeneous and query-driven. Most entities stay at TENSOR_ONLY (~200 tokens). Detail concentrates where queries land.
- **Knowledge has provenance**: Entities can't magically know things. Every fact has a tracked exposure event (who learned what, from whom, when).
- **Modes change semantics**: FORWARD mode forbids anachronisms. CYCLICAL mode permits bootstrap paradoxes. DIRECTORIAL mode allows dramatic coincidences. Each mode has its own validation rules.
- **Templates are patches**: Like a synthesizer, scenarios are saved configurations. JSON templates capture reproducible "sounds" (scenario shapes).

**Code Philosophy**:
- Pythonic: type hints, dataclasses, protocols
- SQLite persistence (metadata/runs.db for runs, timepoint.db for temp), FastAPI backend
- TDD: pytest with mechanism markers (M1-M19)
- SynthasAIzer paradigm: templates as "patches", ADPRS envelopes for entity lifecycle

## Stack
Python 3.10+, FastAPI, Pydantic, LangGraph, pytest, ruff, mypy

## Standards
- Type hints mandatory
- Google docstrings with examples
- Line length: 100
- Logging not print
- Use `TemplateLoader` for template access (not deprecated `SimulationConfig.example_*()`)

## Temporal Mode Architecture

Each mode has a dedicated strategy class in `workflows/`:

| Mode | Strategy Class | Key Affordance |
|------|---------------|----------------|
| FORWARD | (default forward) | Strict causality, knowledge provenance |
| PORTAL | `PortalStrategy` | Backward inference, pivot detection |
| BRANCHING | `BranchingStrategy` | Counterfactual timelines |
| DIRECTORIAL | `DirectorialStrategy` | Five-act arcs, camera system, dramatic irony |
| CYCLICAL | `CyclicalStrategy` | Prophecy system, causal loops, cycle semantics |

Strategies share a common interface: `run(config) -> List[Path]`. Each path contains states with mode-specific metadata (tension scores for DIRECTORIAL, cycle positions for CYCLICAL, etc.).

## Dialog System

Per-character dialog generation via LangGraph pipeline (`workflows/dialog_steering.py`):

- **steering_node** selects next speaker, mood shift, dialog continuation
- **character_node** generates dialog with persona-derived LLM params, Fourth Wall context, and voice discipline
- **quality_gate_node** three-level evaluation (narrative advancement, conflict specificity, voice distinctiveness) + naturalness scoring

**Voice discipline**: 7-principle block in character_node prevents AI-sounding output (no "I understand your concern", no corporate filler, no therapeutic framing). Evaluated via LLM naturalness scoring, not hardcoded regex.

**Archetype profiles** (`workflows/dialog_archetypes.py`): 10 rhetorical profiles (engineer, executive_director, military_commander, scientist, politician, lawyer, diplomat, safety_officer, doctor, journalist) with argument_style, disagreement_pattern, deflection_style, sentence_style, never_does, signature_moves, and voice anti-exemplars.

## Key Commands
```bash
./run.sh list                    # List all 21 templates
./run.sh run board_meeting       # Run single template
./run.sh run --category showcase  # Run by category
./run.sh quick                   # Quick tier tests
./run.sh run <template> --portal-simjudged-quick  # Portal mode with sim-judging
./run.sh run <template> --portal-quick           # Portal quick mode (5 steps)
```

## Testing
```bash
pytest -v -m synth               # SynthasAIzer tests (142 ADPRS tests)
pytest -v -m mechanism           # All M1-M19 tests
pytest -v -m "m1 or m7"          # Specific mechanisms
```

## Security

Static analysis (Bandit + Semgrep) integrated. All HIGH findings resolved:
- Embedding index uses numpy `.npz` + JSON sidecar (safe serialization)
- All DB queries parameterized
- No hardcoded secrets -- environment variable patterns only

**Public repo rule**: Do not reference private repo names, internal networking paths, Railway auto-domains, or env var names for secrets in this repo's code, docs, issues, or commits.

## Subdomain Architecture

All Timepoint services are deployed under `timepointai.com` subdomains:

| Service | URL | Notes |
|---------|-----|-------|
| Flash | `flash.timepointai.com` | Reality Writer — token introspection endpoint for SSO |
| Pro (cloud) | `pro.timepointai.com` | Hosted version of this engine (auth-gated) |
| Clockchain | `clockchain.timepointai.com` | Temporal Causal Graph |
| Proteus | `proteus.timepointai.com` | Settlement Layer |
| API Gateway | `api.timepointai.com` | Unified routing: `/api/v1/clockchain/*`, `/api/v1/*` (default → Flash) |
| Web App | `app.timepointai.com` | Browser client |
| Landing | `timepointai.com` | Marketing site |

The API Gateway at `api.timepointai.com` provides unified routing to backend services. Direct subdomain URLs (e.g., `flash.timepointai.com`) bypass the gateway for service-to-service communication like token introspection.

## OpenAPI Documentation

The cloud layer serves interactive OpenAPI docs at `/docs` (Swagger UI). Access is gated behind JWT or API key authentication. The local dashboard API also exposes OpenAPI docs at `http://localhost:8000/docs` for development.

## Commits
`type(scope): description` - types: feat, fix, refactor, test, docs, chore
