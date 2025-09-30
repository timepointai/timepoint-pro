# timepoint-daedalus

Temporal entity simulation with LLM-driven training and tensor compression.

## Overview

Timepoint-Daedalus is a framework for simulating temporal entities with:
- **LLM-driven entity population** using Instructor for structured outputs
- **Graph-based entity relationships** using NetworkX
- **Tensor compression** (PCA, SVD, NMF) for efficient entity representation
- **Temporal validation** ensuring biological plausibility and information conservation
- **LangGraph workflows** for parallel entity training
- **SQLModel persistence** for entities, timelines, and graphs

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

### Run Autopilot Mode
```bash
python cli.py mode=autopilot
```

### Run Evaluation
```bash
python cli.py mode=evaluate
```

### Run Training
```bash
python cli.py mode=train
```

### Override Configuration
```bash
# Change graph sizes for autopilot
python cli.py mode=autopilot autopilot.graph_sizes=[5,10,20]

# Enable dry-run mode
python cli.py mode=train llm.dry_run=true

# Change target resolution
python cli.py mode=train training.target_resolution=scene
```

## Testing

The project supports comprehensive testing with both dry-run and real LLM modes.

### Quick Start Testing

```bash
# Run all tests (dry-run mode by default)
pytest

# Run with coverage report
pytest --cov

# Run with verbose logging
pytest --verbose-tests -s
```

### LLM Testing Modes

**Dry-Run Mode (Default - Fast & Free):**
```bash
# Standard testing - no API key needed
pytest --cov
```

**Real LLM Mode (Integration Testing):**
```bash
# 1. Get API key from https://openrouter.ai/keys
# 2. Set environment variable
export OPENROUTER_API_KEY="your_api_key_here"

# 3. Run tests with real LLM calls
pytest --verbose-tests

# Or use the convenience script
./test_real_llm.py
```

### Advanced Testing

```bash
# Run specific test
pytest test_framework.py::test_tensor_compression

# Run integration tests only (requires API key)
pytest -m integration

# Run property-based tests
pytest test_framework.py::test_graph_creation_property

# Generate HTML coverage report
pytest --cov --cov-report=html
```

### Test Results

- **Coverage**: 93% across all modules
- **Tests**: 20 comprehensive tests
- **Modes**: Dry-run (free, fast) + Real LLM (integration)

See [VERBOSE_TESTING.md](VERBOSE_TESTING.md) for logging details and [REAL_LLM_TESTING.md](REAL_LLM_TESTING.md) for LLM testing guide.

## Architecture

### Core Components

- **schemas.py**: SQLModel schemas (Entity, Timeline, SystemPrompt, ValidationRule)
- **storage.py**: Database and graph persistence layer
- **llm.py**: LLM client with Instructor integration
- **workflows.py**: LangGraph workflow definitions
- **validation.py**: Pluggable validation framework
- **tensors.py**: Tensor compression with plugin registry
- **evaluation.py**: Evaluation metrics (coherence, consistency, plausibility)
- **graph.py**: NetworkX graph creation and centrality metrics
- **test_framework.py**: Pytest fixtures and tests

### Resolution Levels

1. **TENSOR_ONLY**: Compressed tensor representation only
2. **SCENE**: Scene-level context
3. **GRAPH**: Full graph context
4. **DIALOG**: Dialog-level detail
5. **TRAINED**: Fully trained entity

### Validation Rules

- **Information Conservation**: Knowledge ⊆ exposure history
- **Energy Budget**: Interaction costs ≤ capacity
- **Behavioral Inertia**: Gradual personality drift
- **Biological Constraints**: Age-dependent capabilities

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

### Adding New Validators

```python
@Validator.register("custom_validator", "WARNING")
def validate_custom(entity: Entity, context: Dict) -> Dict:
    # Your validation logic
    return {"valid": True, "message": "Custom validation passed"}
```

### Adding New Tensor Compressors

```python
@TensorCompressor.register("custom_method")
def custom_compress(tensor: np.ndarray, n_components: int = 8) -> np.ndarray:
    # Your compression logic
    return compressed_tensor
```

## License

[Your License Here]