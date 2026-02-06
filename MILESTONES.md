# MILESTONES.md — Development Roadmap

**From research prototype to simulation infrastructure platform.**

> This document describes the development roadmap. Phases 1-7 are aspirational goals. See "Phase 0: Current State" for what exists today.

---

## Phase 0: Current State (February 2026)

**What we have: A working research prototype with intelligent model selection, full temporal mode coverage, and improved data integrity.**

### The Key Insight We've Learned

Temporal simulation isn't one problem—it's five different problems depending on what "time" means in your domain:

1. **Forward causality** (PEARL): History unfolds, causes precede effects. Standard simulation.
2. **Backward inference** (PORTAL): Given a known outcome, what paths lead there? Strategic planning.
3. **Counterfactuals** (BRANCHING): What if X had happened instead? Parallel timelines.
4. **Cycles and prophecy** (CYCLICAL): Time loops, generational patterns, self-fulfilling predictions.
5. **Narrative structure** (DIRECTORIAL): Story-driven causality where drama shapes events.

Each mode has its own validation rules, fidelity allocation strategy, and generation semantics. The architecture now treats temporal mode as a first-class dimension, not an afterthought.

### Implemented

**Core Infrastructure:**
- **19 simulation mechanisms** (M1-M19) — See [MECHANICS.md](MECHANICS.md)
- **M18: Intelligent Model Selection** — Capability-based per-action model selection
- **M19: Knowledge Extraction** — LLM-based semantic knowledge extraction from entities
- **12 Open-Source Models** — All via OpenRouter, all permit commercial synthetic data
- **Natural Language Interface** — `nl_interface/` integrated via `NLToProductionAdapter`
- **Parallel execution** — `--parallel N` for N concurrent workers with thread-safe rate limiting
- **Free model support** — `--free`, `--free-fast`, `--list-free-models` for $0 cost testing

**Full Temporal Mode Coverage (February 2026):**
- **PEARL mode** — Standard forward simulation with strict causality
- **PORTAL mode** — Backward temporal reasoning with pivot detection and path divergence analysis
- **BRANCHING mode** — Counterfactual timeline generation with branch point allocation
- **CYCLICAL mode** — Prophecy system, causal loops, cycle semantics interpretation (repeating/spiral/oscillating)
- **DIRECTORIAL mode** — Five-act arc engine, camera system, dramatic irony detection

**Data Integrity:**
- **SQLite persistence** — `metadata/runs.db` for run tracking, `timepoint.db` for temp per-run data
- **Convergence evaluation** — Causal graph consistency analysis with E2E testing mode
- **Entity inference in Portal mode** — LLM-based `entities_present` inference
- **Data quality validation** — Validates entity references, empty entities_present detection

**Output:**
- **13 verified simulation templates** — Showcase and convergence categories
- **Narrative exports** — Markdown, JSON, PDF generation
- **API backend** — FastAPI REST API

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
├── generation/templates/ — 41 JSON simulation templates with patch metadata
├── synth/ — SynthasAIzer control layer (envelopes, voices, events)
├── validation.py (1,365 lines) — 5 physics validators
├── storage.py — SQLite persistence + transaction support
├── dashboards/ — FastAPI REST API backend
└── metadata/runs.db — Run tracking
```

### Not Yet Implemented

- External integrations (prediction markets, webhooks)
- Containerization / distributed deployment
- Advanced dashboard visualizations
- Distributed execution (1000+ concurrent workers)

### Tensor Persistence System (NEW - December 2025)

| Phase | Component | Status | Tests |
|-------|-----------|--------|-------|
| 1 | SQLite tensor CRUD + versioning | **COMPLETE** | 26 |
| 2 | Training history tracking | **COMPLETE** | 37 |
| 3 | RAG semantic search + composition | **COMPLETE** | 28 |
| 4 | Parquet export, branching, conflicts | **COMPLETE** | 28 |
| 5 | Permissions + audit logging | **COMPLETE** | 73 |
| 6 | REST API (minimal) | **COMPLETE** | 49 |
| **Total** | | | **329+ tests** |

---

## Phase 1: Stabilization
**Target: Q1 2026** | **Status: Partially Complete**

Before adding infrastructure, stabilize the core.

### 1.1 Code Architecture ✅ COMPLETE
- [x] Break up `workflows/__init__.py` into focused modules (9 submodules, <800 lines each)
- [x] Document all 19 mechanisms with examples (MECHANICS.md)
- [x] Transaction support in storage layer
- [ ] Increase test coverage to 90%+

### 1.2 Configuration ✅ COMPLETE
- [x] Move hardcoded Python configs to JSON (16 templates in generation/templates/)
- [x] Config validation via Pydantic (SimulationConfig)
- [x] Template loading with `SimulationConfig.from_template()`
- [ ] Config inheritance (base + scenario-specific)
- [ ] Version tracking for configs

### 1.3 Persistence ✅ SUBSTANTIALLY COMPLETE
- [x] SQLite tensor database with full CRUD
- [x] Version history and optimistic locking
- [x] RAG-based semantic search
- [x] Tensor composition (weighted blend, max pool, hierarchical)
- [x] Parquet export for data versioning
- [x] Permission system (private/shared/public)
- [x] Access audit logging
- [x] REST API with auth
- [ ] PostgreSQL option for production
- [ ] Schema documentation (partial - see PERSISTENCE-PLAN.md)

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
**Target: Q3 2026** | **Status: Substantially Complete (December 2025)**

Programmatic access for external systems.

### 3.1 Tensor API Endpoints ✅ COMPLETE (December 2025)
- [x] Tensor CRUD endpoints (POST/GET/PUT/DELETE /tensors)
- [x] Semantic search endpoint (POST /search)
- [x] Tensor composition endpoint (POST /search/compose)
- [x] Find similar tensors (GET /search/similar/{id})
- [x] Share/fork endpoints
- [x] Health check endpoint
- [x] OpenAPI spec generation (FastAPI auto-docs)

### 3.2 Authentication & Access ✅ COMPLETE
- [x] API key management (create, verify, revoke)
- [x] Permission enforcement (private/shared/public)
- [x] Access audit logging

### 3.3 Simulation API ✅ COMPLETE (December 2025)
- [x] Run submission endpoint (POST /simulations)
- [x] Status and results endpoints (GET /simulations/{id}, GET /simulations/{id}/result)
- [x] Job listing endpoint (GET /simulations)
- [x] Cancel endpoint (POST /simulations/{id}/cancel)
- [x] Statistics endpoint (GET /simulations/stats)
- [x] Template listing (GET /simulations/templates)
- [x] Rate limiting (slowapi with per-tier limits)
- [x] Job concurrency tracking
- [x] Batch submission endpoint (POST /simulations/batch) - 22 tests
- [x] Usage quotas (monthly limits per tier) - 34 tests

**Note:** Model selection (originally Phase 3) is already implemented as M18.

**Exit criteria:** External systems can submit and query simulations via API. ✅ (Basic functionality complete)

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
- Documentation complete for all 19 mechanisms
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
| Tensor persistence | **COMPLETE** | `tensor_persistence.py`, `tensor_rag.py`, `tensor_versioning.py` |
| Permission system | **COMPLETE** | `access/permissions.py`, `access/audit.py` |
| Tensor REST API | **COMPLETE** | `api/` module with FastAPI, 49 tests |
| Simulation REST API | **COMPLETE** | `api/routes/simulations.py` - CRUD, status, cancel |
| Rate limiting | **COMPLETE** | `api/middleware/rate_limit.py` - slowapi, per-tier limits |
| Batch submission API | **COMPLETE** | `api/routes/batch.py`, `api/batch_runner.py` - 22 tests |
| Usage quotas | **COMPLETE** | `api/middleware/usage_quota.py`, `api/usage_storage.py` - 34 tests |
| CLI-API integration | **COMPLETE** | `api/client.py` (SDK), `api/usage_bridge.py`, `--api` flag - 21 tests |
| Portal entity inference | **COMPLETE** | `temporal_agent.py:_infer_entities_for_timepoint()`, `portal_strategy.py:_infer_entities_from_description()` |
| Portal entity fallback | **COMPLETE** | `portal_strategy.py:_generate_antecedents()`, `_generate_placeholder_antecedents()` - inherits parent entities when filtering returns empty |
| Data quality validation | **COMPLETE** | `e2e_runner.py:_run_data_quality_check()` |
| Entity persistence sync | **COMPLETE** | `e2e_runner.py:_persist_entity_for_convergence()` |
| Portal preserve_all_paths | **COMPLETE** | `TemporalConfig.preserve_all_paths`, `portal_strategy.py` |
| Portal divergence detection | **COMPLETE** | `portal_strategy.py:_compute_path_divergence()` |
| Portal quick mode | **COMPLETE** | `--portal-quick` flag, `run_all_mechanism_tests.py` |
| Fidelity template scaling | **COMPLETE** | `temporal_agent.py:_apply_fidelity_template()` |
| Directorial mode strategy | **COMPLETE** | `workflows/directorial_strategy.py` (~800 lines), arc engine, camera system |
| Cyclical mode strategy | **COMPLETE** | `workflows/cyclical_strategy.py` (~900 lines), prophecy system, causal loops |
| Directorial templates | **COMPLETE** | `hound_shadow_directorial` (verified); macbeth/heist/courtroom removed as pending |
| Cyclical templates | **REMOVED** | Pending templates removed; mode strategies remain implemented |
| Portal scoring stubs | **COMPLETE** | 5 methods now use real LLM-based evaluation |
| NONLINEAR mode removal | **COMPLETE** | Removed from codebase, now 5 modes |

---

## Reality Check

**Where we are:** Working research prototype with 19 mechanisms, intelligent model selection, parallel execution, **complete tensor persistence system** (329+ tests), **improved data integrity** (January 2026 fixes), and **full temporal mode implementations** (February 2026).

**What works:**
- Single-run and parallel simulations with full temporal reasoning
- Automatic model selection and free tier support
- Tensor persistence with SQLite, versioning, RAG search
- Permission system (private/shared/public) with audit logging
- REST API for tensor CRUD, search, and composition
- Simulation REST API (job submission, status, cancel, templates)
- Rate limiting with per-tier controls (free/basic/pro/enterprise)
- Batch submission API (2-100 jobs per batch, budget caps, fail-fast)
- Usage quotas (monthly limits for API calls, simulations, cost)
- CLI-API integration (`./run.sh --api`, Python SDK, usage bridge)
- **Portal mode entity inference** (LLM-based, not blind copy)
- **Portal mode enhancements** (preserve all paths, divergence detection, quick mode, fidelity scaling)
- **Data quality validation** (empty entities_present detection, entity reference validation)
- **Entity persistence to shared DB** (enables cross-run convergence analysis)
- **All 5 temporal modes fully implemented** (PEARL, DIRECTORIAL, BRANCHING, CYCLICAL, PORTAL)
- **6 new showcase templates** (3 directorial, 3 cyclical)

**What's missing:** External integrations, containerization, distributed execution.

**Timeline:** 2-3 years to full platform vision.

**First step:** Complete containerization (Dockerfile, Docker Compose).

---

**The models generate. Timepoint reasons about time, causality, and consistency. We're building the infrastructure for everything else.**
