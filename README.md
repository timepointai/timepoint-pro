# Timepoint-Daedalus

**Interactive Temporal Knowledge Graph** - A fully functional system for simulating historical entities across time with causal evolution, variable resolution, and natural language queries.

## Overview

Timepoint-Daedalus creates **queryable temporal simulations** where historical entities evolve causally through time. The system generates entities at multiple timepoints with exposure tracking, applies variable resolution based on query patterns, and answers natural language questions about entity knowledge and experiences.

**Key Features:**
- **Temporal Chains**: Causal evolution of entities across connected timepoints
- **Exposure Tracking**: Knowledge acquisition history with timestamps
- **Variable Resolution**: Adaptive detail levels (tensor-only to fully trained)
- **Interactive Queries**: Natural language questions answered from entity states
- **Knowledge Validation**: Information conservation ensuring temporal coherence

## Installation

### Quick Install (Recommended)

Use the provided installation script that handles all compatibility issues:

```bash
./install.sh
```

### Using Poetry (Recommended)

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Clean any existing locks and cache (if reinstalling)
poetry cache clear pypi --all
rm -f poetry.lock

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

**macOS Apple Silicon (M1/M2/M3) Users:**

If you encounter grpcio build errors, try:

```bash
# Set environment variables for better compatibility
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1

# Install with pre-built wheels
poetry install

# Or install grpcio separately first
pip install --upgrade grpcio
poetry install
```

### Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `conf/config.yaml` to configure:
- Database connection
- LLM settings (API key, base URL)
- Autopilot parameters
- Training settings

## Usage

### Create Temporal Simulation
```bash
# Build temporal chain with causal evolution
python cli.py mode=temporal_train training.context=founding_fathers_1789 training.num_timepoints=3

# Run comprehensive evaluation
python cli.py mode=evaluate
```

### Interactive Queries
```bash
# Start interactive query REPL
python cli.py mode=interactive

# Example queries:
# "What did George Washington think about becoming president?"
# "How did Hamilton and Jefferson's relationship evolve?"
# "Describe the atmosphere during the inauguration ceremony"
```

### Configuration Options
```bash
# Enable dry-run mode (no API costs)
python cli.py mode=temporal_train llm.dry_run=true

# Change context/scenario
python cli.py mode=temporal_train training.context=renaissance_florence_1504

# Adjust number of timepoints
python cli.py mode=temporal_train training.num_timepoints=5
```

## Architecture: File-by-File Breakdown

Timepoint-Daedalus consists of **23 core files** organized into a clean, modular architecture:

### 🎯 **Core Application**
- **`cli.py`** - Main command-line interface with modes: `temporal_train`, `evaluate`, `interactive`
- **`llm.py`** - OpenRouter API client with Instructor for structured LLM outputs
- **`storage.py`** - SQLite database layer with SQLModel ORM for entities, timepoints, exposure events
- **`schemas.py`** - Data models: Entity, Timepoint, ExposureEvent with resolution levels and temporal tracking

### 🧠 **Temporal Intelligence**
- **`temporal_chain.py`** - Builds causal chains of timepoints with historical context
- **`resolution_engine.py`** - Adaptive resolution system (tensor-only → trained) based on query patterns
- **`query_interface.py`** - Natural language query parsing and response synthesis
- **`workflows.py`** - LangGraph orchestration for entity population and validation

### 🔍 **Validation & Quality**
- **`validation.py`** - Information conservation, temporal coherence, biological constraints
- **`evaluation.py`** - Comprehensive metrics: knowledge consistency, temporal coherence, resolution distribution

### 📊 **Data Processing**
- **`tensors.py`** - TTMTensor (context/biology/behavior) compression with PCA/SVD
- **`graph.py`** - NetworkX relationship graphs with eigenvector centrality
- **`entity_templates.py`** - Historical context templates (Founding Fathers, Renaissance Florence)

### 🛠️ **Infrastructure**
- **`reporting.py`** - JSON/Markdown/GraphML report generation
- **`conf/config.yaml`** - Configuration management
- **`pyproject.toml`** - Poetry dependency management
- **`requirements.txt`** - Alternative pip installation
- **`poetry.lock`** - Locked dependency versions

### 📜 **Documentation & Scripts**
- **`README.md`** - This documentation
- **`CHANGE-ROUND.md`** - Current development status
- **`demo.sh`** - End-to-end workflow demonstration
- **`install.sh`** - macOS-compatible installation script

### Resolution Levels (Adaptive Detail)

1. **TENSOR_ONLY**: Compressed tensor representation only (memory efficient)
2. **SCENE**: Scene-level context with basic knowledge
3. **GRAPH**: Full graph relationships and moderate detail
4. **DIALOG**: Dialog-level detail with conversations
5. **TRAINED**: Fully trained entity with complete knowledge state

### Validation Rules (Temporal Coherence)

- **Information Conservation**: Entity knowledge ⊆ exposure history (no anachronisms)
- **Temporal Coherence**: Entity evolution follows causal chains
- **Knowledge Consistency**: Cross-entity claims don't contradict
- **Biological Constraints**: Age/health-appropriate capabilities

## Example Workflow

```bash
# 1. Create temporal simulation
./demo.sh

# 2. Explore interactively
python cli.py mode=interactive
# Query: "What did Washington think about the presidency?"
# Query: "How did Jefferson react to Hamilton's financial plan?"

# 3. Check evaluation metrics
python cli.py mode=evaluate
```

## Development

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .
```

### Current Status

✅ **Fully Functional**: Interactive temporal simulation with all core features implemented
- Temporal chains with causal evolution
- Variable resolution system
- Natural language queries
- Knowledge validation and consistency

⏳ **Remaining**: Production optimizations (batch LLM calls, caching, error handling)

See `CHANGE-ROUND.md` for detailed development progress.

## License

MIT