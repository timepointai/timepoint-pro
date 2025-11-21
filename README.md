# Timepoint-Daedalus

**Temporal Knowledge Graph System with LLM-Driven Entity Simulation**

A sophisticated framework for creating queryable temporal simulations where entities evolve through causally-linked timepoints with adaptive fidelity and modal causality support.

---

## Overview

Timepoint-Daedalus enables you to:
- **Generate simulations from natural language** - "Simulate the Constitutional Convention of 1787"
- **Query across time and entities** - Track knowledge flow, relationships, and decisions
- **Export results** - Reports in Markdown, JSON, CSV with compression
- **Optimize costs** - 95% reduction via adaptive fidelity (tensor compression)

**Status**: Production Ready ✅
- **Mechanism Coverage**: 17/17 (100%) ✅ ALL MECHANISMS TRACKED
- **Test Reliability**: 11/11 tests passing (100%) ✅
- **Architecture**: ANDOS layer-by-layer training (solves circular dependencies)
- **Cost Optimization**: 95% reduction via adaptive fidelity + tensor compression
- **Fault Tolerance**: Global resilience system with checkpointing, circuit breaker, health monitoring
- **Profile Loading**: Real founder profiles (Sean McDonald, Ken Cavanagh) in Portal Timepoint templates ✅ NEW
- Real LLM integration with OpenRouter (requires `OPENROUTER_API_KEY`)
- Complete pipeline: Natural Language → Simulation → Query → Report → Export
- **Documentation**: [MECHANICS.md](MECHANICS.md) for architecture | [PLAN.md](PLAN.md) for roadmap

---

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/timepoint-daedalus.git
cd timepoint-daedalus
pip install -r requirements.txt

# Optional: Install PDF export support
pip install reportlab
```

### Configuration

```bash
# 1. Copy the example environment file
cp .env.example .env

# 2. Edit .env and add your OpenRouter API key
# Get your API key from: https://openrouter.ai/keys
# Then update OPENROUTER_API_KEY in the .env file

# Alternatively, set environment variables directly:
export OPENROUTER_API_KEY=your_key_here
export LLM_SERVICE_ENABLED=true
```

**Important**: The `.env` file is required for `demo_orchestrator.py` to work. Make sure to set your `OPENROUTER_API_KEY` in the `.env` file.

### Basic Usage

```python
from nl_interface import NLConfigGenerator
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore

# 1. Generate config from natural language
generator = NLConfigGenerator()
config, confidence = generator.generate_config(
    "Simulate a board meeting with 5 executives discussing an acquisition. "
    "Focus on dialog and decision making."
)

# 2. Execute simulation
llm = LLMClient()
store = GraphStore("sqlite:///simulations.db")

result = simulate_event(
    config['scenario'],
    llm,
    store,
    context={
        "max_entities": len(config['entities']),
        "max_timepoints": 5,
        "temporal_mode": "pearl"
    },
    save_to_db=True
)

# 3. Query results
from reporting.query_engine import EnhancedQueryEngine

query_engine = EnhancedQueryEngine()
world_id = f"simulation_{result['timepoints'][0].timepoint_id}"

relationships = query_engine.summarize_relationships(world_id)
timeline = query_engine.timeline_summary(world_id)
knowledge_flow = query_engine.knowledge_flow_graph(world_id)

# 4. Generate reports
from reporting.report_generator import ReportGenerator

report_gen = ReportGenerator(query_engine)
markdown_report = report_gen.generate_summary_report(
    world_id=world_id,
    format="markdown"
)

# 5. Export data
from reporting.export_pipeline import ExportPipeline

exporter = ExportPipeline(query_engine)
exporter.export_report(
    world_id=world_id,
    report_type="summary",
    export_format="json",
    output_path="./output/summary.json"
)
```

---

## Running Simulations with run.sh

The `run.sh` script provides a unified interface for running all simulation modes with optional real-time monitoring.

### Basic Usage

```bash
# Quick tests (9 templates, ~$9-18, 18-27 min)
./run.sh quick

# Portal tests with monitoring
./run.sh --monitor portal-test

# Ultra mode with chat-enabled monitoring
./run.sh --monitor --chat ultra

# List all available modes
./run.sh --list
```

### Available Modes

#### Basic Modes
- **quick**: Quick tests (9 templates, ~$9-18, 18-27 min)
- **full**: All quick + expensive tests (13 templates)

#### Timepoint Corporate
- **timepoint-forward**: Forward-mode corporate (15 templates, $15-30, 30-60 min)
- **timepoint-all**: ALL corporate templates (35 templates, $81-162, 156-243 min)

#### Portal (Backward Reasoning)
- **portal-test**: Standard portal (4 templates, $5-10, 10-15 min)
- **portal-simjudged-quick**: Quick simulation judging (4 templates, $10-20, 20-30 min)
- **portal-simjudged**: Standard simulation judging (4 templates, $15-30, 30-45 min)
- **portal-simjudged-thorough**: Thorough judging (4 templates, $25-50, 45-60 min)
- **portal-all**: ALL portal variants (16 templates, $55-110, 105-150 min)

#### Portal Timepoint (Real Founders)
- **portal-timepoint**: Standard with founders (5 templates, $6-12, 12-18 min)
- **portal-timepoint-simjudged-quick**: Quick judging (5 templates, $12-24, 24-36 min)
- **portal-timepoint-simjudged**: Standard judging (5 templates, $18-36, 36-54 min)
- **portal-timepoint-simjudged-thorough**: Thorough judging (5 templates, $30-60, 54-75 min)
- **portal-timepoint-all**: ALL portal timepoint (20 templates, $66-132, 126-183 min)

#### Ultra Mode
- **ultra**: Run EVERYTHING (64 templates, $176-352, 301-468 min)

### Monitoring Options

```bash
# Enable real-time LLM monitoring
./run.sh --monitor quick

# Enable interactive chat during monitoring
./run.sh --monitor --chat portal-timepoint

# Custom monitoring interval (seconds)
./run.sh --monitor --interval 120 quick

# Use premium LLM model for monitoring
./run.sh --monitor --llm-model meta-llama/llama-3.1-405b-instruct portal-test
```

### Environment Setup

Create `.env` file with API keys:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
OXEN_API_KEY=SFMyNTY...
```

### Output Locations

All modes generate:
- **Database**: `metadata/runs.db` (with M1+M17 metrics)
- **Narrative Exports**: `datasets/<template>/narrative_*.{json,md,pdf}`
- **Training Data**: `datasets/<template>/training_*.jsonl`
- **Oxen Uploads**: If `OXEN_API_KEY` is set

---

## Complete Pipeline

The system provides an end-to-end workflow:

```
Natural Language Description
         ↓
    Config Generation (Sprint 3)
         ↓
    Simulation Execution (Orchestrator)
         ↓
    Query Interface (Sprint 1)
         ↓
    Report Generation (Sprint 2)
         ↓
    Data Export (Sprint 2)
         ↓
    Exported Files
```

See `test_e2e_complete_pipeline.py` for a working example.

---

## Key Features

### 1. Natural Language Interface

Convert plain English into executable simulation configs:

```python
from nl_interface import NLConfigGenerator

generator = NLConfigGenerator()
config, confidence = generator.generate_config(
    "Simulate Paul Revere's midnight ride. 8 timepoints. "
    "Focus on knowledge propagation."
)
# Returns validated config with 80-100% confidence
```

### 2. Modal Temporal Causality

Choose from six temporal modes:

- **Pearl** - Standard DAG causality (historical realism)
- **Directorial** - Narrative-driven (dramatic coherence)
- **Nonlinear** - Flashbacks and non-linear presentation
- **Branching** - Many-worlds counterfactuals
- **Cyclical** - Time loops and prophecy
- **PORTAL** - Backward temporal reasoning from endpoint to origin

#### PORTAL Mode: Backward Temporal Reasoning

**Problem**: Given a known endpoint (e.g., "Jane Chen elected President in 2040") and an origin (e.g., "Jane Chen is VP Engineering in 2025"), discover the most plausible paths between them.

**How It Works:**
1. **Define Portal & Origin**: Specify the endpoint state you want to reach and the starting point
2. **Backward Path Exploration**: System works backward from portal, generating N candidate antecedent states at each step
3. **Hybrid Scoring**: Each candidate scored using LLM plausibility, historical precedent, causal necessity, entity capability, and dynamic context
4. **Forward Coherence Validation**: Paths validated by simulating forward from origin to portal
5. **Pivot Point Detection**: Identifies critical decision moments where paths diverge

**Example Use Cases:**
- Career paths: tech executive → president, startup → unicorn, PhD → tenure
- Failure analysis: successful seed round → company shutdown (what went wrong?)
- Historical what-ifs: Different outcomes given known starting conditions

**Quality Enhancement: Simulation-Based Judging (Optional)**

For higher quality paths, enable simulation-based judging instead of static scoring:

- **Standard**: Static formula scoring (~$5-10 per run)
- **Simulation-Judged Quick**: 1 forward step, no dialog (~$10-20, ~2x cost)
- **Simulation-Judged Standard**: 2 forward steps + dialog (~$15-30, ~3x cost)
- **Simulation-Judged Thorough**: 3 forward steps + extra analysis (~$25-50, ~4-5x cost)

Simulation judging captures emergent behaviors, dialog realism, and internal consistency that static formulas miss.

**Configuration Example:**
```python
from generation.config_schema import TemporalConfig, SimulationConfig
from schemas import TemporalMode

# Standard PORTAL mode
config = TemporalConfig(
    mode=TemporalMode.PORTAL,
    portal_description="Jane Chen elected President with 52.4% vote in 2040",
    portal_year=2040,
    origin_year=2025,
    origin_description="Jane Chen VP Engineering at TechCorp",
    backward_steps=15,  # 2040 - 2025 = 15 years
    path_count=3,  # Generate top 3 paths
    candidate_antecedents_per_step=5,  # Branching factor
    exploration_mode="adaptive",  # reverse_chronological | oscillating | adaptive
    coherence_threshold=0.7
)

# Or use pre-built templates
config_standard = SimulationConfig.portal_presidential_election()
config_simjudged = SimulationConfig.portal_presidential_election_simjudged()
```

**See Also:**
- Examples: `examples/portal_presidential_election.py`
- Documentation: [MECHANICS.md](MECHANICS.md) - M17 PORTAL Mode section
- Templates: 16 PORTAL templates (4 scenarios × 4 variants each)

#### Real Founder Profiles: Portal Timepoint Templates

**NEW**: 5 Portal templates that simulate Timepoint's path to success using real founder profiles (Sean McDonald, Ken Cavanagh) loaded from JSON:

```python
# Profile-based templates (real founders)
config = SimulationConfig.portal_timepoint_unicorn()              # $1.2B valuation
config = SimulationConfig.portal_timepoint_series_a_success()     # $15M Series A
config = SimulationConfig.portal_timepoint_product_market_fit()   # 10K users
config = SimulationConfig.portal_timepoint_enterprise_adoption()  # Fortune 500
config = SimulationConfig.portal_timepoint_founder_transition()   # Leadership evolution

# Each automatically loads:
# - Sean McDonald (philosophical_technical_polymath archetype)
# - Ken Cavanagh (psychology_tech_bridge archetype)
# - 4 additional entities generated via LLM
```

**Profile Loading Architecture:**
- Profiles stored in `generation/profiles/founder_archetypes/*.json`
- Automatically loaded before LLM entity generation
- Ensures consistent founder characterization across runs
- Reduces cost by ~33% for entity generation (2 profiles + 4 LLM = 6 total)

**How It Works:**
```python
# 1. Config specifies profiles
entities=EntityConfig(
    count=6,
    types=["human"],
    profiles=[
        "generation/profiles/founder_archetypes/sean.json",
        "generation/profiles/founder_archetypes/ken.json"
    ]
)

# 2. System loads profiles + generates remaining entities
# Sean + Ken from JSON → 4 supporting cast from LLM → 6 total entities

# 3. All entities ready for PORTAL simulation
```

**Validation:** Run `python test_profile_context_passing.py` to verify profile loading works correctly.

**See Also:**
- Phase 13 Documentation: [PLAN.md](PLAN.md) - Profile Loading System section
- Profile Schema: `generation/profiles/founder_archetypes/sean.json`, `ken.json`

### 3. Adaptive Fidelity-Temporal Strategy (M1+M17 Integration)

**NEW**: The TemporalAgent co-determines BOTH fidelity allocation (how much detail per timepoint) AND temporal progression (when/how much time passes), optimizing simulation validity vs token efficiency.

**Key Features**:
- **Planning Modes**: PROGRAMMATIC (pre-planned), ADAPTIVE (runtime decisions), HYBRID (planned + adaptive)
- **Token Budget Modes**: HARD_CONSTRAINT, SOFT_GUIDANCE, MAX_QUALITY, ADAPTIVE_FALLBACK, ORCHESTRATOR_DIRECTED, USER_CONFIGURED
- **Fidelity Templates**: minimalist (5k tokens), balanced (15k), dramatic (25k), max_quality (350k), portal_pivots (20k adaptive)

**Musical Score Metaphor**:
- **Template**: Default fidelity+temporal strategy
- **TemporalAgent**: "Conductor" that interprets score based on simulation needs
- **User**: Full customization control

**Example Usage**:
```python
from schemas import FidelityPlanningMode, TokenBudgetMode
from generation.config_schema import SimulationConfig

config = SimulationConfig.portal_timepoint_unicorn()

# Customize fidelity strategy
config.temporal.fidelity_planning_mode = FidelityPlanningMode.HYBRID
config.temporal.token_budget = 15000
config.temporal.token_budget_mode = TokenBudgetMode.SOFT_GUIDANCE
config.temporal.fidelity_template = "portal_pivots"
```

**Database v2**: All runs tracked with fidelity metrics (distribution, budget compliance, efficiency score)

**See Also**:
- Documentation: [MECHANICS.md](MECHANICS.md) - M1+M17 Integration section

### 4. Adaptive Fidelity (Legacy)

Five resolution levels optimize cost vs. detail:

1. **TENSOR** - Compressed (200 tokens, ~$0.01)
2. **SCENE** - Context (~1-2k tokens)
3. **GRAPH** - Relationships (~5k tokens)
4. **DIALOG** - Conversations (~10k tokens)
5. **TRAINED** - Full state (~50k tokens)

**Result**: 95% cost reduction vs. uniform high-fidelity.

### 4. Animistic Entities

Support for non-human entities:

- Animals (biological constraints)
- Buildings (structural integrity)
- Objects (state tracking)
- Abstract concepts (idea propagation)
- AI entities (external agent integration)

### 5. Query & Export

Comprehensive querying with multiple export formats:

```python
from reporting.query_engine import EnhancedQueryEngine
from reporting.export_pipeline import ExportPipeline

# Query
engine = EnhancedQueryEngine()
relationships = engine.summarize_relationships(world_id)
knowledge_flow = engine.knowledge_flow_graph(world_id)

# Export
exporter = ExportPipeline(engine)
exporter.export_batch(
    world_id=world_id,
    report_types=["summary", "relationships", "knowledge"],
    export_formats=["json", "markdown"],
    output_dir="./exports/"
)
```

**Supported Formats**: JSON, JSONL, Markdown, CSV, SQLite
**Compression**: gzip, bz2 (50-70% size reduction)

### 6. Automated Narrative Exports

Every simulation run automatically generates comprehensive narrative summaries:

```python
from generation.config_schema import SimulationConfig

# Narrative exports enabled by default
config = SimulationConfig.board_meeting()

# Customize export behavior
config.outputs.generate_narrative_exports = True  # Default: on
config.outputs.narrative_export_formats = ["markdown", "json", "pdf"]
config.outputs.narrative_detail_level = "summary"  # minimal | summary | comprehensive
config.outputs.enhance_narrative_with_llm = True  # Optional LLM enhancement (~$0.003/run)
```

**Features**:
- **Automatic Generation**: MD/JSON/PDF created at end of every run
- **Executive Summary**: High-level overview with LLM enhancement option
- **Character Profiles**: Entity states, knowledge, and emotional dynamics
- **Timeline**: Chronological sequence of events
- **Dialog Excerpts**: Sample conversations from the simulation
- **Training Insights**: Entity counts, training stats, mechanism usage
- **Cost Tracking**: Token usage and API costs

**Export Formats**:
- **Markdown**: Human-readable narrative with full formatting
- **JSON**: Structured data for programmatic access
- **PDF**: Publication-ready document (requires `reportlab`)

**Detail Levels**:
- **Minimal**: Metadata only (run stats, costs, mechanisms)
- **Summary**: Key highlights (characters, timeline, dialogs)
- **Comprehensive**: Everything (full analysis with all details)

**File Locations**:
```
datasets/{template_id}/narrative_{timestamp}.md
datasets/{template_id}/narrative_{timestamp}.json
datasets/{template_id}/narrative_{timestamp}.pdf
```

**Backfill Historical Runs**:
```bash
# Generate narratives for all existing completed runs
python scripts/backfill_narrative_exports.py --all

# Specific runs only
python scripts/backfill_narrative_exports.py --run-ids run_001 run_002

# Preview without writing files
python scripts/backfill_narrative_exports.py --all --dry-run

# Customize formats and detail level
python scripts/backfill_narrative_exports.py --all --formats markdown json --detail-level comprehensive
```

**Configuration Options**:
- Disable for specific runs: `config.outputs.generate_narrative_exports = False`
- Choose formats: `config.outputs.narrative_export_formats = ["markdown"]`
- Adjust detail: `config.outputs.narrative_detail_level = "comprehensive"`
- Disable LLM enhancement: `config.outputs.enhance_narrative_with_llm = False`

**Note**: Export failures will cause the run to fail (narrative exports are treated as critical deliverables).

### 7. Fault Tolerance & Resilience

Global resilience system protects long-running simulations:

```python
from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from metadata.run_tracker import MetadataManager

# Create resilient runner (transparently wraps E2E workflow)
metadata_manager = MetadataManager(db_path="metadata/runs.db")
runner = ResilientE2EWorkflowRunner(metadata_manager)

# Run simulation with fault tolerance enabled
result = runner.run(config)
```

**Features**:
- **Circuit Breaker**: Stops API calls if failure rate exceeds threshold (prevents cascading failures)
- **Health Monitoring**: Pre-flight checks for API key, disk space, directory permissions
- **Automatic Checkpointing**: Saves progress every N timepoints with atomic writes
- **Resume Capability**: Automatically resumes from last checkpoint on failure
- **Adaptive Retry**: Exponential backoff with adaptive increases for persistent errors
- **Transaction Logging**: Append-only audit trail in `logs/transactions/{run_id}.log`

**Guarantees**:
- Atomic checkpoint writes (temp file + rename)
- File locking prevents corruption
- OpenRouter-specific error handling (rate limits, 503/502/504)
- No data loss on crash/network failure

---

## Testing

### Run E2E Tests with run.sh (Recommended)

```bash
# Quick development tests (9 templates, ~18-27 min)
./run.sh quick

# Full test suite (13 templates)
./run.sh full

# PORTAL Mode tests
./run.sh portal-test                    # Standard PORTAL (4 templates, ~10-15 min)
./run.sh portal-simjudged               # With simulation judging (~30-45 min)
./run.sh portal-all                     # All PORTAL variants (16 templates)

# Portal Timepoint tests (real founders)
./run.sh portal-timepoint               # Standard (5 templates, ~12-18 min)
./run.sh portal-timepoint-simjudged     # With judging (~36-54 min)
./run.sh portal-timepoint-all           # All variants (20 templates)

# Timepoint Corporate tests
./run.sh timepoint-forward              # Forward-mode (15 templates, ~30-60 min)
./run.sh timepoint-all                  # All corporate (35 templates)

# Ultra mode (everything)
./run.sh ultra                          # 64 templates (5-8 hours)

# With monitoring enabled
./run.sh --monitor quick
./run.sh --monitor --chat portal-timepoint
```

### Run Unit/Mechanism Tests with pytest

```bash
# Run all mechanism tests
pytest -v

# Specific mechanism tests
pytest test_m5_query_resolution.py -v              # M5: Query Resolution
pytest test_m9_on_demand_generation.py -v          # M9: On-Demand Generation
pytest test_branching_integration.py -v            # M12: Counterfactual Branching
pytest test_phase3_dialog_multi_entity.py -v       # M13: Multi-Entity Synthesis

# Run with real LLM (requires OPENROUTER_API_KEY)
export OPENROUTER_API_KEY=your_key
pytest -v
```

**PORTAL Mode Testing:**
- 4 scenarios: presidential election, startup unicorn, academic tenure, startup failure
- 4 quality levels each: standard (static), sim-judged quick, sim-judged standard, sim-judged thorough
- Total: 16 PORTAL templates testing backward temporal reasoning
- Simulation judging captures emergent behaviors and dialog realism invisible to static scoring

### Test Coverage

**Current Status: PRODUCTION READY** ✅

**E2E Workflow Tests**: 11/11 (100%) ✅
- 5 Pre-programmed Templates (board_meeting, jefferson_dinner, hospital_crisis, kami_shrine, detective_prospection)
- 6 ANDOS Test Scripts (M5, M9, M10, M12, M13, M14)

**Mechanism Coverage**: 17/17 (100%) ✅ **ALL TRACKED**

| ID | Mechanism | Status | Test Coverage |
|----|-----------|--------|---------------|
| M1 | Entity Lifecycle Management | ✅ Tracked | E2E workflow |
| M2 | Progressive Training | ✅ Tracked | E2E workflow |
| M3 | Graph Construction & Eigenvector Centrality | ✅ Tracked | E2E workflow |
| M4 | Tensor Transformation & Embedding | ✅ Tracked | E2E workflow |
| M5 | Query Resolution with Lazy Elevation | ✅ Tracked | Dedicated test script |
| M6 | TTM Tensor Compression | ✅ Tracked | E2E workflow |
| M7 | Causal Chain Generation | ✅ Tracked | E2E workflow |
| M8 | Vertical Timepoint Expansion | ✅ Tracked | E2E workflow |
| M9 | On-Demand Entity Generation | ✅ Tracked | Dedicated test script |
| M10 | Scene-Level Entity Management | ✅ Tracked | Dedicated test script |
| M11 | Dialog Synthesis | ✅ Tracked | E2E workflow |
| M12 | Counterfactual Timeline Branching | ✅ Tracked | Dedicated test script |
| M13 | Multi-Entity Synthesis | ✅ Tracked | Dedicated test script |
| M14 | Circadian Patterns | ✅ Tracked | Dedicated test script |
| M15 | Entity Prospection | ✅ Tracked | E2E workflow |
| M16 | Animistic Entity Agency | ✅ Tracked | E2E workflow |
| M17 | Metadata Tracking System | ✅ Tracked | E2E workflow |

**Data Source**: `metadata/runs.db` - All mechanisms persistently tracked via explicit recording

**Test Markers**:
- `@pytest.mark.integration` - Multi-component tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.unit` - Fast isolated tests

---

## Fine-Tuning

### Horizontal Fine-Tuning (Breadth)
Generate many scenario variations for training diversity:

```bash
# Generate 50 variations with different personalities/outcomes
python run_real_finetune.py
```

### Vertical Fine-Tuning (Depth)
Generate deep temporal simulations with 12 timepoints:

```bash
# Generate deep temporal simulation with progressive training
python run_vertical_finetune.py
```

**Output**: Training data in JSONL format uploaded to Oxen.ai
**Repository**: `realityinspector/proof-the-e2e-works`

**Note**: Oxen.ai does not support programmatic fine-tune creation. After uploading:
1. Visit your Oxen repository
2. Navigate to the uploaded dataset file
3. Use the web UI to manually create a fine-tuning job

---

## Documentation

### Core Documentation
- **README.md** (this file) - Quick start guide and overview
- **MECHANICS.md** - Technical architecture and 17 core mechanisms
- **PLAN.md** - Development roadmap and phase history (includes Phase 11: Resilience System)

---

## Performance

### Benchmarks

- **Small simulation** (5 entities, 5 timepoints): $1-2, 30-60s
- **Medium simulation** (20 entities, 10 timepoints): $5-8, 60-120s
- **Large simulation** (100 entities, 20 timepoints): $20-30, 120-300s

### Efficiency

- **Cost reduction**: 95% (tensor compression + resolution optimization)
- **Compression ratio**: 97% (50k tokens → 200 tokens via TTM)
- **Query caching**: LRU with TTL (600s default)

---

## Architecture

### Core Components

**Natural Language Interface** (`nl_interface/`):
- `nl_to_config.py` - NL → Config translation
- `interactive_refiner.py` - Interactive refinement
- `clarification_engine.py` - Ambiguity detection
- `config_validator.py` - Validation pipeline

**Query & Reporting** (`reporting/`):
- `query_engine.py` - Enhanced query interface
- `report_generator.py` - Multi-format reports
- `export_pipeline.py` - Batch export orchestration
- `formatters.py` - Format conversion
- `export_formats.py` - Export handlers

**Timepoint Stack**:
- `orchestrator.py` - Scene orchestration (742 lines)
- `llm_v2.py` - LLM client with retry logic (1,000 lines)
- `storage.py` - SQLite persistence
- `schemas.py` - Pydantic V2 models (529 lines)
- `temporal_causality.py` - Pearl-mode causality
- `validation.py` - Safety & validation (1,340 lines)

**Generation** (`generation/`):
- `world_manager.py` - Simulation world management
- `horizontal_generator.py` - Variation generation
- `vertical_generator.py` - Temporal depth expansion
- `progress_tracker.py` - Real-time metrics
- `resilience_orchestrator.py` - Global fault tolerance (circuit breaker, health monitoring, transaction log)
- `fault_handler.py` - Error recovery with adaptive retry
- `checkpoint_manager.py` - Atomic checkpointing with file locking

**Metadata & Exports** (`metadata/`):
- `run_tracker.py` - Run metadata tracking and database management
- `narrative_exporter.py` - Automated narrative summary generation (MD/JSON/PDF)

**Scripts** (`scripts/`):
- `backfill_narrative_exports.py` - Generate narratives for historical runs

---

## Dependencies

**Core**:
- `langgraph>=0.2.62` - Workflow orchestration
- `networkx>=3.4.2` - Graph operations
- `instructor>=1.7.0` - LLM structured outputs
- `httpx>=0.27.0` - HTTP client
- `sqlmodel>=0.0.22` - ORM
- `pydantic>=2.10.0` - Validation
- `numpy>=2.2.1`, `scipy>=1.15.0` - Tensor operations

**Testing**:
- `pytest>=8.3.4` - Test framework
- `pytest-asyncio>=0.25.2` - Async support
- `pytest-cov>=6.0.0` - Coverage

See `requirements.txt` for complete list.

---

## License

MIT

---

## Contact

For questions or issues, please open a GitHub issue.

---

**Production Ready** ✅ | **100% Test Pass Rate (11/11)** | **17/17 Mechanisms Tracked** | See **MECHANICS.md** for architecture
