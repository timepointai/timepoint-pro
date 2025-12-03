# MILESTONES.md — Development Roadmap

**From research prototype to simulation infrastructure platform.**

> This document describes the development roadmap. Phases 1-7 are aspirational goals. See "Phase 0: Current State" for what exists today.

---

## Phase 0: Current State (December 2025)

**What we have: A working research prototype with intelligent model selection.**

### Implemented

- **18 simulation mechanisms** (M1-M18) — See [MECHANICS.md](MECHANICS.md)
- **M18: Intelligent Model Selection** — Capability-based per-action model selection
- **12 Open-Source Models** — All via OpenRouter, all permit commercial synthetic data
- **PORTAL mode** — Backward temporal reasoning from endpoints to origins
- **Natural Language Interface** — `nl_interface/` integrated via `NLToProductionAdapter`
- **Parallel execution** — `--parallel N` for N concurrent workers with thread-safe rate limiting
- **Free model support** — `--free`, `--free-fast`, `--list-free-models` for $0 cost testing
- **Ctrl+C protection** — Double-confirm handler prevents accidental abortion of expensive runs
- **SQLite persistence** — `metadata/runs.db` for run tracking
- **Mechanism metrics** — All 18 mechanisms tracked per run
- **Basic dashboard** — Quarto + FastAPI
- **Narrative exports** — Markdown, JSON, PDF generation
- **69+ simulation templates** — In `generation/config_schema.py` (includes 3 convergence-optimized templates)
- **Convergence evaluation** — Causal graph consistency analysis with E2E testing mode, side-by-side comparison, and robustness grading (A-F)

### Model Stack (All Open Source)

| License | Models |
|---------|--------|
| **MIT** | DeepSeek Chat, DeepSeek R1 |
| **Apache 2.0** | Mistral 7B, Mixtral 8x7B, Mixtral 8x22B |
| **Llama License** | Llama 3.1 8B/70B/405B, Llama 4 Scout |
| **Qwen License** | Qwen 2.5 7B/72B, QwQ 32B |

**Explicitly excluded:** OpenAI, Anthropic, Google (commercial/synthetic data restrictions)

### Architecture

```
Current Architecture:
├── orchestrator.py (1,666 lines) — Scene control
├── workflows/ (9 submodules, <800 lines each) — TemporalAgent, modes
│   ├── temporal_agent.py, dialog_synthesis.py, portal_strategy.py
│   ├── entity_training.py, relationship_analysis.py, prospection.py
│   └── counterfactual.py, animistic.py, scene_environment.py
├── llm_service/ — Model selection, providers
│   ├── service.py — LLM facade
│   ├── model_selector.py — M18 implementation
│   └── providers/ — OpenRouter integration
├── nl_interface/ — Natural language input
│   └── adapter.py — NLToProductionAdapter
├── generation/templates/ — 16 JSON simulation templates
├── validation.py (1,365 lines) — 5 physics validators
├── storage.py — SQLite persistence + transaction support
├── dashboards/ — Quarto dashboard with home page
└── metadata/runs.db — Run tracking
```

### Not Yet Implemented

- REST API
- External integrations (prediction markets, webhooks)
- Containerization / distributed deployment
- Advanced dashboard visualizations
- Distributed execution (1000+ concurrent workers)

---

## Phase 1: Stabilization
**Target: Q1 2026** | **Status: Partially Complete**

Before adding infrastructure, stabilize the core.

### 1.1 Code Architecture ✅ COMPLETE
- [x] Break up `workflows/__init__.py` into focused modules (9 submodules, <800 lines each)
- [x] Document all 18 mechanisms with examples (MECHANICS.md)
- [x] Transaction support in storage layer
- [ ] Increase test coverage to 90%+

### 1.2 Configuration ✅ COMPLETE
- [x] Move hardcoded Python configs to JSON (16 templates in generation/templates/)
- [x] Config validation via Pydantic (SimulationConfig)
- [x] Template loading with `SimulationConfig.from_template()`
- [ ] Config inheritance (base + scenario-specific)
- [ ] Version tracking for configs

### 1.3 Persistence
- [ ] PostgreSQL option for production
- [ ] Schema documentation
- [ ] Basic query interface (by date, by template, by cost)
- [ ] Data export (JSONL for training data)

### 1.4 Deployment Basics
- [ ] Dockerfile for single-container deployment
- [ ] Docker Compose for local dev
- [x] Environment variable management (.env support)
- [ ] Basic CI (run tests on PR)

**Exit criteria:** Clean, tested codebase ready for infrastructure layer.

---

## Phase 2: Batch Execution
**Target: Q2 2026** | **Status: Partially Complete**

Run many simulations in parallel.

### 2.1 Worker Architecture
- [x] Worker pool with configurable concurrency (`--parallel N`)
- [x] Thread-safe rate limiting across workers
- [ ] Job queue (Redis or similar) for distributed execution
- [ ] Job status tracking
- [ ] Retry logic with exponential backoff

### 2.2 Cost Management
- [x] Token counting per job
- [x] Cost estimation before execution
- [x] Usage reporting (per-run and aggregate)
- [ ] Budget caps (per job, per batch)

### 2.3 Batch API
```python
# Target API
results = timepoint.run_batch(
    configs=[config1, config2, ...],
    parallel_workers=10,
    budget_cap=100.0
)
```

### 2.4 Progress and Monitoring
- [ ] Real-time progress reporting
- [ ] ETA estimation
- [ ] Failed job diagnostics
- [ ] Batch summary on completion

**Exit criteria:** Can run 100+ simulations in parallel with cost tracking.

---

## Phase 3: REST API
**Target: Q3 2026**

Programmatic access for external systems.

### 3.1 API Endpoints
- [ ] Run submission endpoint
- [ ] Batch submission endpoint
- [ ] Status and results endpoints
- [ ] Query interface (GET runs with filters)
- [ ] OpenAPI spec generation

### 3.2 Authentication & Limits
- [ ] API key management
- [ ] Rate limiting
- [ ] Usage quotas

**Note:** Model selection (originally Phase 3) is already implemented as M18.

**Exit criteria:** External systems can submit and query simulations via API.

---

## Phase 4: Human Interface
**Target: Q4 2026**

Make results legible to non-technical users.

### 4.1 Dashboard Enhancements
- [ ] Run browser with search/filter
- [ ] Single run detail view
- [ ] Batch summary view
- [ ] Cost analytics

### 4.2 Visualizations
- [ ] Timeline visualization (branching paths)
- [ ] Entity relationship graphs
- [ ] Pivot point highlighting
- [ ] Path comparison view

### 4.3 Narrative Generation
- [ ] Executive summary generation
- [ ] Path comparison narratives
- [ ] Export to PDF/Markdown

**Exit criteria:** Business users can explore simulation results without CLI.

---

## Phase 5: Scale Infrastructure
**Target: Q1-Q2 2027**

Handle enterprise-scale workloads.

### 5.1 Containerization
- [ ] Docker images for all components
- [ ] Kubernetes manifests
- [ ] Helm charts
- [ ] Health checks and probes

### 5.2 Distributed Execution
- [ ] Worker node clustering
- [ ] Auto-scaling (HPA/KEDA)
- [ ] Multi-region support
- [ ] Fault tolerance

### 5.3 Bare Metal Option
- [ ] Ansible playbooks
- [ ] GPU node support
- [ ] NVMe optimization

### 5.4 Massive Parallelization
- [ ] 1,000+ concurrent workers
- [ ] Distributed job queue (Redis Cluster)
- [ ] Work stealing
- [ ] Checkpointing for long batches

**Exit criteria:** Can run 100,000-simulation batches across distributed infrastructure.

---

## Phase 6: Integrations
**Target: Q2-Q3 2027**

Connect simulations to external systems.

### 6.1 Prediction Markets
- [ ] Polymarket connector
- [ ] Metaculus connector
- [ ] Probability extraction from simulation distributions
- [ ] Calibration tracking

### 6.2 Webhooks & Alerts
- [ ] Configurable triggers
- [ ] Slack/Discord/email notifications
- [ ] CI/CD integration

### 6.3 Research Pipeline
- [ ] Training data export (JSONL, Parquet)
- [ ] Benchmark suite generation
- [ ] Anonymization options

**Exit criteria:** Simulations can inform prediction markets and trigger external actions.

---

## Phase 7: Consumer & Platform
**Target: 2028+**

Broad accessibility and ecosystem.

### 7.1 Consumer Experiences
- [ ] "Time travel" web experience
- [ ] Mobile app
- [ ] VR/AR prototype (exploratory)
- [ ] Portal booth concept (hardware R&D)

### 7.2 Platform
- [ ] Plugin architecture
- [ ] Vertical solution packages
- [ ] Multi-tenant SaaS
- [ ] Developer ecosystem (SDKs, templates)

**Exit criteria:** Third parties building on Timepoint platform.

---

## Infrastructure Architecture (Target)

### Development / Single Machine

```
┌─────────────────────────────────────────┐
│  Docker Compose                         │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │   API   │ │ Workers │ │ Dashboard │  │
│  └────┬────┘ └────┬────┘ └─────┬─────┘  │
│       └──────┬────┴────────────┘        │
│         ┌────▼────┐                     │
│         │PostgreSQL│                    │
│         │ + Redis  │                    │
│         └─────────┘                     │
└─────────────────────────────────────────┘
```

### Production / Kubernetes

```
┌─────────────────────────────────────────────────────────┐
│  Kubernetes Cluster                                     │
│  ┌──────────────┐  ┌────────────────────────────────┐   │
│  │     API      │  │ Worker Pool (HPA: 10-1000)     │   │
│  │ (Deployment) │  │ ┌──────┐┌──────┐┌──────┐       │   │
│  └──────┬───────┘  │ │Worker││Worker││Worker│ ...   │   │
│         │          │ └──────┘└──────┘└──────┘       │   │
│         │          └────────────────────────────────┘   │
│    ┌────▼────────────────────────────┐                  │
│    │      Redis Cluster (Queue)      │                  │
│    └────────────────┬────────────────┘                  │
│    ┌────────────────▼────────────────┐                  │
│    │  PostgreSQL (HA / Read Replicas)│                  │
│    └─────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

### High Performance / Bare Metal

```
┌─────────────────────────────────────────────────────────┐
│  Bare Metal Cluster (Ansible)                           │
│  ┌─────────────────┐   ┌─────────────────────────────┐  │
│  │ Control Node    │   │ Worker Nodes                │  │
│  │ - API           │   │ ┌───────┐ ┌───────┐         │  │
│  │ - Queue         │   │ │64 core│ │64 core│ ...     │  │
│  │ - Dashboard     │   │ │256 GB │ │256 GB │         │  │
│  └────────┬────────┘   │ └───────┘ └───────┘         │  │
│  ┌────────▼────────┐   └─────────────────────────────┘  │
│  │ Storage Nodes   │   Optional: GPU for local models  │
│  └─────────────────┘                                    │
└─────────────────────────────────────────────────────────┘
```

---

## Success Metrics

### Phase 1 (Stabilization)
- Test coverage >90%
- Documentation complete for all 18 mechanisms
- Docker deployment working

### Phase 2-3 (Batch + API)
- Batch success rate >99%
- API latency <500ms (p95)
- Cost tracking accuracy within 5%

### Phase 4-5 (Interface + Scale)
- Dashboard used by 80%+ of users
- 1,000+ concurrent workers supported
- 99.9% uptime on distributed deployment

### Phase 6-7 (Integrations + Platform)
- Calibration tracking for 1,000+ predictions
- 10+ external integrations
- Third-party plugins/solutions

---

## Dependencies and Risks

### Dependencies
- Model provider API stability
- Funding for extended development timeline

### Technical Risks
- Storage costs at scale
- Kubernetes complexity for small teams
- Distributed state consistency

### Market Risks
- Model providers building competing infrastructure
- Enterprise sales cycles
- Consumer willingness to pay

### Mitigations
- Provider-agnostic design (M18 already enables model switching)
- Offer both container and bare metal
- Start with research/consulting revenue
- Consumer as marketing, enterprise as revenue

---

## What's Already Done

| Originally Planned | Status | Implementation |
|-------------------|--------|----------------|
| Multi-model support | **COMPLETE** | M18 in `llm_service/model_selector.py` |
| Per-action model selection | **COMPLETE** | `call_with_action()`, `structured_call_with_action()` |
| Fallback chains | **COMPLETE** | `get_fallback_chain()` |
| License compliance | **COMPLETE** | 12 models, MIT/Apache 2.0/Llama/Qwen |
| NL interface | **COMPLETE** | `nl_interface/adapter.py` |
| Convergence evaluation | **COMPLETE** | `evaluation/convergence.py`, storage layer, dashboard |
| Convergence E2E testing | **COMPLETE** | `--convergence-e2e` mode in `run_all_mechanism_tests.py` |
| Convergence templates | **COMPLETE** | 3 optimized templates in `config_schema.py` |
| Parallel execution | **COMPLETE** | `--parallel N` in `run_all_mechanism_tests.py` |
| Free model support | **COMPLETE** | `FreeModelSelector` in `llm.py`, `--free`/`--free-fast` flags |
| Ctrl+C protection | **COMPLETE** | `GracefulInterruptHandler` in `run_all_mechanism_tests.py` |

---

## Reality Check

**Where we are:** Working research prototype with 18 novel mechanisms, intelligent model selection, and parallel execution.

**What works:** Single-run and parallel simulations with full temporal reasoning, automatic model selection, and free tier support.

**What's missing:** REST API, external integrations, containerization, distributed execution.

**Timeline:** 2-3 years to full platform vision.

**First step:** Complete Phase 1 (persistence basics, containerization) and Phase 3 (REST API).

---

**The models generate. Timepoint reasons about time, causality, and consistency. We're building the infrastructure for everything else.**
