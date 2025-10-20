# Timepoint-Daedalus

**Interactive Temporal Knowledge Graph & AI Entity System** - A comprehensive simulation framework for temporal reasoning with heterogeneous fidelity, modal causality, and AI-powered agents.

## 🎯 System Status

**Last Updated:** October 2025
**Test Status:** 11/16 E2E tests passing (68.75%)
**Core Mechanisms:** 17/17 implemented
**Production Status:** Core features operational, orchestrator integration in progress

### Current State

✅ **Fully Operational:**
- Heterogeneous fidelity temporal graphs with query-driven resolution
- Modal temporal causality (Pearl, Directorial, Nonlinear, Branching, Cyclical)
- Animistic entities (humans, animals, buildings, objects, abstract concepts)
- AI entity integration with safety controls
- LangGraph workflows for parallel entity processing
- Comprehensive validation framework
- TTM tensor compression (97% reduction)

⚠️ **Known Issues:**
- Orchestrator integration incomplete (3/3 tests failing)
- SQLModel validation errors with entity IDs
- LLM client architecture needs alignment
- TestProvider collection warning

See [TESTING.md](TESTING.md) for detailed test results and known issues.

## 📋 Overview

Timepoint-Daedalus creates **queryable temporal simulations** where entities evolve through causally-linked timepoints. The system features:

- **17+ Mechanisms**: Complete implementation of MECHANICS.md specifications
- **Modal Temporal Causality**: Switch between different causal regimes (Pearl DAG, narrative-driven, cyclical time)
- **Animistic Entities**: Support for non-human entities (animals, buildings, objects, abstract concepts)
- **AI Entity Integration**: External AI agents with safety controls and service architecture
- **Heterogeneous Fidelity**: Query-driven resolution from compressed tensors to fully trained states
- **Comprehensive Validation**: Physics-inspired structural invariants and temporal coherence checks

## 🚀 Quick Start

### Installation

```bash
# Using Poetry (recommended)
poetry install
poetry shell

# Or using pip
pip install -r requirements.txt

# For testing
pip install -r requirements-test.txt
```

**macOS Apple Silicon Users:**
```bash
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
poetry install
```

### Configuration

Edit `conf/config.yaml` to configure:
- Database connection
- LLM settings (API key, base URL)
- Autopilot parameters
- Training settings

### Running Tests

```bash
# Run all tests
pytest -v

# Run E2E tests
pytest -m e2e -v

# Run with real LLM (requires API key)
pytest --real-llm -m e2e -v

# Skip slow tests
pytest --skip-slow -v
```

See [TESTING.md](TESTING.md) for comprehensive testing guide.

### Basic Usage

```bash
# Create temporal simulation
python cli.py mode=temporal_train training.context=founding_fathers_1789 training.num_timepoints=3

# Run evaluation
python cli.py mode=evaluate

# Interactive queries
python cli.py mode=interactive
```

## 📊 Architecture

### Core Components (27 files)

**Application Layer:**
- `cli.py` - Command-line interface with temporal_train/evaluate/interactive modes
- `llm.py` / `llm_v2.py` - LLM clients with OpenRouter integration
- `storage.py` - SQLite database layer with SQLModel ORM
- `schemas.py` - Polymorphic entity system and data models

**Temporal Intelligence:**
- `temporal_chain.py` - Builds causal chains of timepoints
- `resolution_engine.py` - Adaptive resolution system (tensor → trained)
- `query_interface.py` - Natural language query parsing
- `workflows.py` - LangGraph orchestration for entity population
- `temporal_agent.py` - Directorial temporal agent
- `orchestrator.py` - Scene-to-specification compiler (integration in progress)

**AI & Safety:**
- `ai_entity_service.py` - FastAPI service for AI entity management
- `validation.py` - Physics-inspired structural validators
- `evaluation.py` - Comprehensive metrics and quality scoring

**Data Processing:**
- `tensors.py` - TTM tensor compression (97% reduction)
- `graph.py` - NetworkX relationship graphs
- `entity_templates.py` - Historical context templates

### Resolution Levels

1. **TENSOR_ONLY**: Compressed representation (8-16 floats)
2. **SCENE**: Scene-level context with basic knowledge
3. **GRAPH**: Full graph relationships
4. **DIALOG**: Dialog-level detail with conversations
5. **TRAINED**: Fully trained entity with complete knowledge state

## 🧪 Testing

### Test Status

**E2E Tests:** 11 passing / 5 failing (68.75%)

**Passing:**
- ✅ Full entity generation workflow
- ✅ Multi-entity scene generation
- ✅ Full temporal chain creation
- ✅ Modal temporal causality
- ✅ AI entity full lifecycle
- ✅ Bulk entity creation performance
- ✅ Concurrent timepoint access
- ✅ End-to-end data consistency
- ✅ LLM safety and validation
- ✅ Complete simulation workflow
- ✅ Modal causality with LLM

**Failing:**
- ❌ Deep integration temporal chain (SQLModel validation)
- ❌ Scene generation with animism (LLM client attribute error)
- ❌ Orchestrator entity generation (SQLModel validation)
- ❌ Orchestrator temporal chain (LLM client error)
- ❌ Full pipeline with orchestrator (multiple errors)

### Running Tests

```bash
# Run E2E suite
pytest -m e2e -v

# Run specific test
pytest test_e2e_autopilot.py::TestE2ETemporalWorkflows::test_full_temporal_chain_creation -v

# Run with coverage
pytest -m e2e --cov=. -v
```

## 📚 Core Mechanisms

### Implemented (17/17)

1. **Heterogeneous Fidelity** - Query-driven resolution elevation
2. **Progressive Training** - Metadata-driven quality without cache invalidation
3. **Exposure Event Tracking** - Causal knowledge provenance
4. **Physics-Inspired Validation** - Conservation law validators
5. **Query-Driven Resolution** - Lazy elevation based on access patterns
6. **TTM Tensor Model** - Context/biology/behavior factorization
7. **Causal Temporal Chains** - Counterfactual branching support
8. **Embodied Entity States** - Age-dependent constraints
9. **Body-Mind Coupling** - Pain/illness effects on cognition
10. **On-Demand Entity Generation** - Unknown entity handling
11. **Scene-Level Entity Sets** - Atmosphere and crowd modeling
12. **Dialog/Interaction Synthesis** - Multi-entity conversations
13. **Counterfactual Branching** - Timeline interventions
14. **Multi-Entity Synthesis** - Relationship trajectory analysis
15. **Circadian Activity Patterns** - Time-of-day constraints
16. **Entity Prospection** - Future forecasting with anxiety modeling
17. **Animistic Entity Extension** - Non-human entity support

### Experimental Extensions

- **Modal Temporal Causality** - Pearl/Directorial/Nonlinear/Branching/Cyclical modes
- **AI Entity Integration** - External AI agents with safety controls
- **AnyEntity** - Highly adaptive entities with dynamic forms
- **KamiEntity** - Spiritual entities with visibility states

## 🔧 Configuration

### Temporal Modes

```yaml
temporal_mode:
  active_mode: pearl  # pearl | directorial | nonlinear | branching | cyclical
  directorial:
    narrative_arc: rising_action
    dramatic_tension: 0.7
  cyclical:
    cycle_length: 10
    prophecy_accuracy: 0.85
```

### Animism Levels

```yaml
animism:
  level: 1  # 0=humans only, 1=animals/buildings, 2=objects, 3=abstract
  llm_enrichment_enabled: true
```

### AI Entity Service

```yaml
ai_entity_service:
  enabled: true
  safety_controls:
    input_bleaching: true
    output_filtering: true
    rate_limiting: true
```

## 📈 Performance

### Efficiency Metrics

- **Token Cost Reduction**: 95% (from $500 to $5-20 per query)
- **Compression Ratio**: 97% via TTM tensors (50k → 200 tokens)
- **Test Execution**: ~89 seconds for 16 E2E tests
- **LLM Integration**: 34 available models with cost tracking

### Cost Estimates

- 7 timepoints, 5 entities: ~$1.49
- 8 queries: ~$0.09
- Extended simulation (10 timepoints, 20 entities): $4-6

## 🔗 Documentation

- **[TESTING.md](TESTING.md)** - Comprehensive testing guide
- **[MECHANICS.md](MECHANICS.md)** - Technical architecture and mechanisms
- **[CHANGE-ROUND.md](CHANGE-ROUND.md)** - Development roadmap and status
- **[ORCHESTRATOR_DOCUMENTATION.md](ORCHESTRATOR_DOCUMENTATION.md)** - Orchestrator API reference
- **[CURRENT_STATE_ANALYSIS.md](CURRENT_STATE_ANALYSIS.md)** - Integration status analysis

## 🛠️ Development

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy .
```

### Project Structure

```
timepoint-daedalus/
├── cli.py                    # Main CLI
├── llm.py / llm_v2.py        # LLM clients
├── storage.py                # Database layer
├── schemas.py                # Data models
├── workflows.py              # LangGraph orchestration
├── orchestrator.py           # Scene compiler
├── validation.py             # Validators
├── evaluation.py             # Metrics
├── tensors.py                # TTM compression
├── graph.py                  # NetworkX graphs
├── conf/
│   └── config.yaml           # Configuration
├── tests/
│   ├── test_e2e_autopilot.py # E2E test suite
│   ├── test_*.py             # Unit/integration tests
│   └── conftest.py           # Shared fixtures
└── docs/
    └── *.md                  # Documentation
```

## ⚠️ Known Issues & Limitations

### Current Limitations

1. **Orchestrator Integration**: 3 orchestrator tests failing due to:
   - SQLModel validation errors (empty entity IDs)
   - LLM client architecture mismatch
   - Need for integration layer between orchestrator and workflows

2. **TestProvider Warning**: Collection warning still present despite claimed fix

3. **Error Claims vs Reality**: Some documentation claims "all errors fixed" but tests show 31.25% failure rate

### Planned Improvements

- [ ] Complete orchestrator integration with workflows
- [ ] Fix SQLModel validation pipeline
- [ ] Align LLM client architecture across codebase
- [ ] Resolve TestProvider collection warning
- [ ] Add orchestrator performance tests
- [ ] Improve error handling in scene parsing

See [CURRENT_STATE_ANALYSIS.md](CURRENT_STATE_ANALYSIS.md) for detailed integration analysis.

## 🤝 Contributing

### Development Workflow

1. Create feature branch
2. Write tests first
3. Implement feature
4. Ensure all tests pass: `pytest -v`
5. Update documentation
6. Submit pull request

### Test Requirements

- Unit tests for new functionality
- Integration tests for workflows
- E2E tests for major features
- Documentation updates

## 📝 License

MIT

## 🙏 Acknowledgments

Built with:
- **LangGraph** - Workflow orchestration
- **NetworkX** - Graph operations
- **Instructor** - LLM structured output
- **scikit-learn** - Tensor compression
- **SQLModel** - ORM layer
- **FastAPI** - AI entity service
- **Hydra** - Configuration management

---

**Status**: Core features operational, orchestrator integration in progress
**Test Coverage**: 68.75% E2E passing, comprehensive unit/integration coverage
**Production Ready**: Core mechanisms yes, full integration pending
