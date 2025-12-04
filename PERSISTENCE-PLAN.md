# Tensor Persistence Architecture Plan

## Executive Summary

This document outlines a comprehensive plan for implementing granular tensor persistence, retrieval, and version control in Timepoint Daedalus. The architecture enables:

1. **Massively parallel tensor training** with collision handling
2. **Granular tensor storage** (public templates vs personal instances)
3. **RAG-like semantic retrieval** for trained tensors
4. **Oxen AI version control** for tensor lineage and branching
5. **Access permissions** supporting future public API

**Status**: Phases 1-5 COMPLETE. Phase 6 planned.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Architecture Overview](#architecture-overview)
3. [Tensor Granularity Model](#tensor-granularity-model)
4. [Storage Layer Design](#storage-layer-design)
5. [Training Pipeline Integration](#training-pipeline-integration)
6. [Retrieval System (Tensor RAG)](#retrieval-system-tensor-rag)
7. [Collision Handling](#collision-handling)
8. [Version Control with Oxen AI](#version-control-with-oxen-ai)
9. [Access Permissions Model](#access-permissions-model)
10. [Public API Vision](#public-api-vision)
11. [Implementation Phases](#implementation-phases)
12. [Technical Specifications](#technical-specifications)

---

## Current State Analysis

### Tensor Structure (tensor_initialization.py)

The TTMTensor is a 20-dimensional cognitive tensor:
- **Context dimensions (8)**: situation, goal, stakes, time_pressure, social_context, information_state, emotional_valence, uncertainty
- **Biology dimensions (4)**: arousal, fatigue, stress, cognitive_load
- **Behavior dimensions (8)**: assertiveness, cooperation, risk_tolerance, patience, formality, emotional_expression, information_sharing, conflict_approach

### Current Storage (storage.py, schemas.py)

```python
# Entity schema includes tensor as JSON string
class Entity(BaseModel):
    tensor: Optional[str] = None           # JSON-serialized TTMTensor
    tensor_maturity: float = 0.0           # 0.0-1.0 quality gate
    tensor_training_cycles: int = 0        # Training iteration count
```

### Current Training (tensor_initialization.py:802-880)

```python
def train_tensor_to_maturity(tensor, target_maturity=0.95):
    """PLACEHOLDER: Currently uses random noise, not real backprop"""
    while tensor.maturity < target_maturity:
        tensor.values += np.random.normal(0, 0.01, tensor.values.shape)
        tensor.training_cycles += 1
        tensor.maturity = min(1.0, tensor.maturity + 0.05)
```

### Current Limitations

1. Tensors are ephemeral - lost after simulation ends
2. No reuse of trained tensors across simulations
3. No semantic lookup - only by entity_id
4. No version history or branching
5. No access control beyond local filesystem
6. Training is sequential, not parallel

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TENSOR PERSISTENCE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  TRAINING       │    │  STORAGE        │    │  RETRIEVAL      │         │
│  │  PIPELINE       │    │  LAYER          │    │  SYSTEM         │         │
│  │                 │    │                 │    │                 │         │
│  │  - Parallel     │───▶│  - SQLite       │◀───│  - Embedding    │         │
│  │    Workers      │    │    (local)      │    │    Index        │         │
│  │  - Collision    │    │  - Parquet      │    │  - Semantic     │         │
│  │    Detection    │    │    (Oxen)       │    │    Search       │         │
│  │  - Maturity     │    │  - Metadata     │    │  - Composition  │         │
│  │    Tracking     │    │    Index        │    │    Engine       │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│           │                     │                      │                    │
│           │                     ▼                      │                    │
│           │         ┌─────────────────────┐           │                    │
│           │         │  OXEN VERSION       │           │                    │
│           └────────▶│  CONTROL            │◀──────────┘                    │
│                     │                     │                                 │
│                     │  - Branching        │                                 │
│                     │  - Merkle Trees     │                                 │
│                     │  - Diff/Merge       │                                 │
│                     └─────────────────────┘                                 │
│                              │                                              │
│                              ▼                                              │
│                     ┌─────────────────────┐                                 │
│                     │  ACCESS CONTROL     │                                 │
│                     │                     │                                 │
│                     │  - Public/Private   │                                 │
│                     │  - API Keys         │                                 │
│                     │  - Rate Limits      │                                 │
│                     └─────────────────────┘                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tensor Granularity Model

### Two-Tier Tensor Classification

#### 1. Public Templates (Reusable Archetypes)

Generalized tensors representing common patterns:

| Category | Examples | Training Source |
|----------|----------|-----------------|
| **Epochs** | Victorian, Renaissance, Modern | Historical simulations |
| **Professions** | CEO, Detective, Scientist | Role-based training |
| **Archetypes** | Hero, Mentor, Trickster | Narrative patterns |
| **Emotional States** | Crisis, Celebration, Grief | Situational templates |
| **Social Contexts** | Formal, Casual, Hostile | Environmental priors |

**Schema**:
```python
class PublicTensorTemplate:
    template_id: str           # "epoch/victorian", "profession/detective"
    name: str                  # Human-readable name
    description: str           # Semantic description for RAG
    tensor_values: np.ndarray  # 20-dim tensor
    maturity: float            # 0.95+ required for public
    training_metadata: dict    # Source simulations, cycles, etc.
    embedding: np.ndarray      # For semantic search
    version: str               # Oxen commit hash
    created_at: datetime
    updated_at: datetime
    usage_count: int           # Analytics
```

#### 2. Personal Instances (Entity-Specific)

Trained tensors bound to specific entities:

| Type | Description | Persistence |
|------|-------------|-------------|
| **Session** | Single simulation run | Ephemeral |
| **Persistent** | Saved for reuse | Local SQLite |
| **Published** | Shared publicly | Oxen + API |

**Schema**:
```python
class PersonalTensorInstance:
    instance_id: str           # UUID
    entity_id: str             # Bound entity
    world_id: str              # Source simulation
    base_template: str         # Parent template (optional)
    tensor_values: np.ndarray  # 20-dim tensor
    maturity: float            # Training quality
    training_history: list     # Cycle-by-cycle deltas
    embedding: np.ndarray      # For semantic search
    access_level: str          # "private", "shared", "public"
    owner_id: str              # User/API key
    version: str               # Oxen commit hash
```

### Tensor Inheritance Model

```
PublicTemplate (epoch/victorian)
       │
       ├──▶ PublicTemplate (profession/victorian_detective)
       │           │
       │           └──▶ PersonalInstance (sherlock_holmes_v3)
       │
       └──▶ PersonalInstance (queen_victoria_formal)
```

Tensors can inherit from templates and be modified through training.

---

## Storage Layer Design

### Hybrid Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LOCAL (Hot Storage)              REMOTE (Cold Storage)         │
│  ─────────────────                ────────────────────          │
│                                                                 │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │ SQLite          │              │ Oxen AI         │          │
│  │ (tensors.db)    │◀────sync────▶│ (tensor-store)  │          │
│  │                 │              │                 │          │
│  │ - Active tensors│              │ - Parquet files │          │
│  │ - Embeddings    │              │ - Version tree  │          │
│  │ - Metadata      │              │ - Branch state  │          │
│  │ - Session cache │              │ - Public API    │          │
│  └─────────────────┘              └─────────────────┘          │
│                                                                 │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │ FAISS Index     │              │ Oxen Embeddings │          │
│  │ (local search)  │              │ (remote search) │          │
│  └─────────────────┘              └─────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### SQLite Schema (Local)

```sql
-- Tensor templates (public archetypes)
CREATE TABLE tensor_templates (
    template_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'epoch', 'profession', 'archetype', etc.
    tensor_blob BLOB NOT NULL,  -- msgpack-encoded np.ndarray
    maturity REAL NOT NULL CHECK (maturity >= 0 AND maturity <= 1),
    training_cycles INTEGER NOT NULL,
    embedding_blob BLOB,  -- For local FAISS index
    oxen_version TEXT,  -- Commit hash
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0
);

CREATE INDEX idx_templates_category ON tensor_templates(category);
CREATE INDEX idx_templates_maturity ON tensor_templates(maturity);

-- Tensor instances (entity-specific)
CREATE TABLE tensor_instances (
    instance_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    world_id TEXT NOT NULL,
    base_template_id TEXT REFERENCES tensor_templates(template_id),
    tensor_blob BLOB NOT NULL,
    maturity REAL NOT NULL,
    training_cycles INTEGER NOT NULL,
    training_history_blob BLOB,  -- List of deltas
    embedding_blob BLOB,
    access_level TEXT NOT NULL DEFAULT 'private',
    owner_id TEXT NOT NULL,
    oxen_version TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (world_id) REFERENCES worlds(id)
);

CREATE INDEX idx_instances_entity ON tensor_instances(entity_id);
CREATE INDEX idx_instances_world ON tensor_instances(world_id);
CREATE INDEX idx_instances_owner ON tensor_instances(owner_id);
CREATE INDEX idx_instances_access ON tensor_instances(access_level);

-- Training jobs (for parallel training)
CREATE TABLE training_jobs (
    job_id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL REFERENCES tensor_instances(instance_id),
    status TEXT NOT NULL,  -- 'pending', 'running', 'completed', 'failed'
    worker_id TEXT,
    started_at TEXT,
    completed_at TEXT,
    cycles_completed INTEGER DEFAULT 0,
    target_maturity REAL NOT NULL,
    error_message TEXT
);

CREATE INDEX idx_jobs_status ON training_jobs(status);
CREATE INDEX idx_jobs_instance ON training_jobs(instance_id);

-- Version history (local mirror of Oxen)
CREATE TABLE tensor_versions (
    version_id TEXT PRIMARY KEY,
    tensor_type TEXT NOT NULL,  -- 'template' or 'instance'
    tensor_id TEXT NOT NULL,
    oxen_commit TEXT NOT NULL,
    parent_version TEXT REFERENCES tensor_versions(version_id),
    delta_blob BLOB,  -- Changes from parent
    created_at TEXT NOT NULL,
    metadata_json TEXT
);

CREATE INDEX idx_versions_tensor ON tensor_versions(tensor_type, tensor_id);
```

### Parquet Schema (Oxen Remote)

```python
# templates.parquet
{
    "template_id": pa.string(),
    "name": pa.string(),
    "description": pa.string(),
    "category": pa.string(),
    "tensor_values": pa.list_(pa.float32(), 20),  # Fixed-size array
    "maturity": pa.float32(),
    "training_cycles": pa.int32(),
    "embedding": pa.list_(pa.float32(), 384),  # sentence-transformers dim
    "created_at": pa.timestamp("ms"),
    "updated_at": pa.timestamp("ms"),
}

# instances.parquet
{
    "instance_id": pa.string(),
    "entity_id": pa.string(),
    "world_id": pa.string(),
    "base_template_id": pa.string(),  # nullable
    "tensor_values": pa.list_(pa.float32(), 20),
    "maturity": pa.float32(),
    "training_cycles": pa.int32(),
    "embedding": pa.list_(pa.float32(), 384),
    "access_level": pa.string(),
    "owner_id": pa.string(),
    "created_at": pa.timestamp("ms"),
}
```

---

## Training Pipeline Integration

### Current LangGraph Workflow (e2e_runner.py)

```
generate_scenario
       │
       ▼
generate_entities ◀─── TENSOR CREATION POINT
       │
       ▼
generate_timepoints
       │
       ▼
generate_relationships
       │
       ▼
generate_knowledge_flow
       │
       ▼
synthesize_dialogs ◀─── TENSOR USAGE POINT
       │
       ▼
generate_summaries
       │
       ▼
export_to_oxen
```

### Enhanced Pipeline with Tensor Persistence

```
generate_scenario
       │
       ▼
┌──────────────────────────────────────────┐
│         TENSOR RESOLUTION NODE           │
│                                          │
│  For each entity:                        │
│  1. Search for matching template (RAG)   │
│  2. If found: clone and personalize      │
│  3. If not: create new tensor            │
│  4. Queue for training if maturity < 0.95│
└──────────────────────────────────────────┘
       │
       ▼
generate_entities (with pre-resolved tensors)
       │
       ▼
┌──────────────────────────────────────────┐
│      PARALLEL TRAINING DISPATCHER        │
│                                          │
│  - Spawn N training workers              │
│  - Each worker trains assigned tensors   │
│  - Collision detection via job locks     │
│  - Maturity threshold: 0.95              │
└──────────────────────────────────────────┘
       │
       ├───▶ Worker 1: Entity A tensor
       ├───▶ Worker 2: Entity B tensor
       ├───▶ Worker 3: Entity C tensor
       └───▶ Worker N: ...
       │
       ▼ (join)
generate_timepoints
       │
       ▼
generate_relationships
       │
       ▼
generate_knowledge_flow
       │
       ▼
synthesize_dialogs (using mature tensors)
       │
       ▼
┌──────────────────────────────────────────┐
│         TENSOR PERSISTENCE NODE          │
│                                          │
│  For each trained tensor:                │
│  1. Compute embedding                    │
│  2. Check for collisions                 │
│  3. Store to SQLite                      │
│  4. Sync to Oxen (if public/shared)      │
│  5. Update version history               │
└──────────────────────────────────────────┘
       │
       ▼
generate_summaries
       │
       ▼
export_to_oxen
```

### Parallel Training Implementation

```python
# New file: training/parallel_trainer.py

class ParallelTensorTrainer:
    """Manages parallel tensor training with collision handling."""

    def __init__(self, max_workers: int = 4, db_path: str = "tensors.db"):
        self.max_workers = max_workers
        self.db = TensorDatabase(db_path)
        self.job_queue = asyncio.Queue()
        self.results = {}

    async def train_batch(
        self,
        tensors: list[TTMTensor],
        target_maturity: float = 0.95
    ) -> dict[str, TTMTensor]:
        """Train multiple tensors in parallel."""

        # Create jobs
        jobs = []
        for tensor in tensors:
            job_id = str(uuid.uuid4())
            job = TrainingJob(
                job_id=job_id,
                instance_id=tensor.instance_id,
                status="pending",
                target_maturity=target_maturity
            )
            self.db.insert_job(job)
            jobs.append(job)
            await self.job_queue.put((job_id, tensor))

        # Spawn workers
        workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(min(self.max_workers, len(jobs)))
        ]

        # Wait for completion
        await self.job_queue.join()

        # Cancel workers
        for w in workers:
            w.cancel()

        return self.results

    async def _worker(self, worker_id: str):
        """Worker coroutine that processes training jobs."""
        while True:
            job_id, tensor = await self.job_queue.get()

            try:
                # Acquire lock
                if not self.db.acquire_job_lock(job_id, worker_id):
                    # Another worker took it
                    self.job_queue.task_done()
                    continue

                # Train tensor
                self.db.update_job_status(job_id, "running")
                trained = await self._train_tensor(tensor)

                # Store result
                self.results[tensor.instance_id] = trained
                self.db.update_job_status(job_id, "completed")

            except Exception as e:
                self.db.update_job_status(job_id, "failed", str(e))

            finally:
                self.job_queue.task_done()

    async def _train_tensor(self, tensor: TTMTensor) -> TTMTensor:
        """Train a single tensor to maturity."""
        # Actual training logic here
        # This is where real backprop would happen
        pass
```

---

## Retrieval System (Tensor RAG)

### Semantic Search Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      TENSOR RAG SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT: Natural language query                                  │
│  "victorian detective investigating murder"                     │
│                                                                 │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                           │
│  │ EMBEDDING       │  Model: sentence-transformers             │
│  │ GENERATOR       │  all-MiniLM-L6-v2 (384 dims)             │
│  └─────────────────┘                                           │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────┐                   │
│  │ HYBRID SEARCH                           │                   │
│  │                                         │                   │
│  │  Local FAISS    ◀──────▶  Oxen Index   │                   │
│  │  (fast, cached)     (authoritative)    │                   │
│  └─────────────────────────────────────────┘                   │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                           │
│  │ RESULT RANKER   │  Factors:                                 │
│  │                 │  - Semantic similarity                    │
│  │                 │  - Maturity score                         │
│  │                 │  - Usage count                            │
│  │                 │  - Recency                                │
│  └─────────────────┘                                           │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                           │
│  │ COMPOSITION     │  Options:                                 │
│  │ ENGINE          │  - Single best match                      │
│  │                 │  - Weighted blend                         │
│  │                 │  - Hierarchical merge                     │
│  └─────────────────┘                                           │
│         │                                                       │
│         ▼                                                       │
│  OUTPUT: Resolved tensor(s)                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Retrieval API

```python
# New file: retrieval/tensor_rag.py

class TensorRAG:
    """Semantic retrieval system for trained tensors."""

    def __init__(
        self,
        local_db: TensorDatabase,
        oxen_client: OxenClient,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.db = local_db
        self.oxen = oxen_client
        self.embedder = SentenceTransformer(embedding_model)
        self.local_index = self._build_local_index()

    def search(
        self,
        query: str,
        n_results: int = 5,
        min_maturity: float = 0.9,
        categories: list[str] = None,
        access_levels: list[str] = None
    ) -> list[TensorSearchResult]:
        """Search for tensors matching a natural language query."""

        # Generate query embedding
        query_embedding = self.embedder.encode(query)

        # Search local index
        local_results = self._search_local(
            query_embedding, n_results * 2, min_maturity
        )

        # Search Oxen (if connected)
        if self.oxen.is_connected():
            remote_results = self._search_oxen(
                query_embedding, n_results * 2, min_maturity
            )
            # Merge and deduplicate
            all_results = self._merge_results(local_results, remote_results)
        else:
            all_results = local_results

        # Filter by category and access level
        filtered = self._filter_results(all_results, categories, access_levels)

        # Rank and return top N
        ranked = self._rank_results(filtered, query_embedding)
        return ranked[:n_results]

    def compose(
        self,
        tensors: list[TTMTensor],
        weights: list[float] = None,
        method: str = "weighted_blend"
    ) -> TTMTensor:
        """Compose multiple tensors into a new tensor."""

        if weights is None:
            weights = [1.0 / len(tensors)] * len(tensors)

        if method == "weighted_blend":
            # Simple weighted average
            composed = np.zeros(20)
            for tensor, weight in zip(tensors, weights):
                composed += tensor.values * weight
            return TTMTensor(values=composed)

        elif method == "max_pool":
            # Take maximum value for each dimension
            stacked = np.stack([t.values for t in tensors])
            return TTMTensor(values=np.max(stacked, axis=0))

        elif method == "hierarchical":
            # Apply tensors in order, later ones override
            base = tensors[0].values.copy()
            for tensor in tensors[1:]:
                mask = tensor.values != 0
                base[mask] = tensor.values[mask]
            return TTMTensor(values=base)

        else:
            raise ValueError(f"Unknown composition method: {method}")

    def resolve_for_entity(
        self,
        entity_description: str,
        scenario_context: str,
        prefer_templates: bool = True
    ) -> TTMTensor:
        """Resolve the best tensor for an entity in context."""

        # Build composite query
        query = f"{entity_description} in {scenario_context}"

        # Search for matches
        results = self.search(
            query,
            n_results=3,
            min_maturity=0.9,
            categories=["epoch", "profession", "archetype"] if prefer_templates else None
        )

        if not results:
            # No match - return new tensor
            return TTMTensor.create_new()

        if len(results) == 1 or results[0].score > 0.9:
            # Strong single match
            return results[0].tensor.clone()

        # Multiple weak matches - compose
        return self.compose(
            [r.tensor for r in results[:2]],
            weights=[r.score for r in results[:2]]
        )
```

### Integration with LangChain (Embeddings Only)

Use LangChain's embedding utilities without full RAG stack:

```python
from langchain.embeddings import HuggingFaceEmbeddings

# Use LangChain for embedding generation only
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Generate embedding for tensor description
tensor_embedding = embeddings.embed_query(tensor.description)

# Store in SQLite and sync to Oxen
```

---

## Collision Handling

### Collision Scenarios

| Scenario | Description | Resolution |
|----------|-------------|------------|
| **Concurrent Training** | Two workers train same tensor | Job lock prevents |
| **Concurrent Write** | Two processes save same tensor_id | Optimistic locking |
| **Template Conflict** | Two users publish same template | Namespace isolation |
| **Version Divergence** | Local differs from remote | Oxen merge strategy |

### Optimistic Locking Implementation

```python
# In storage/collision.py

class OptimisticLock:
    """Optimistic locking for tensor writes."""

    def __init__(self, db: TensorDatabase):
        self.db = db

    def write_with_lock(
        self,
        tensor_id: str,
        tensor: TTMTensor,
        expected_version: str
    ) -> bool:
        """
        Write tensor only if version matches.
        Returns True if write succeeded, False if conflict detected.
        """
        with self.db.transaction() as tx:
            current = tx.get_tensor_version(tensor_id)

            if current != expected_version:
                # Conflict detected
                return False

            new_version = self._generate_version()
            tx.update_tensor(tensor_id, tensor, new_version)
            return True

    def resolve_conflict(
        self,
        tensor_id: str,
        local_tensor: TTMTensor,
        remote_tensor: TTMTensor,
        strategy: str = "latest_wins"
    ) -> TTMTensor:
        """Resolve version conflict between local and remote."""

        if strategy == "latest_wins":
            # Use most recently updated
            if local_tensor.updated_at > remote_tensor.updated_at:
                return local_tensor
            return remote_tensor

        elif strategy == "highest_maturity":
            # Use tensor with higher maturity
            if local_tensor.maturity > remote_tensor.maturity:
                return local_tensor
            return remote_tensor

        elif strategy == "merge":
            # Create new version combining both
            merged = TTMTensor(
                values=(local_tensor.values + remote_tensor.values) / 2,
                maturity=max(local_tensor.maturity, remote_tensor.maturity),
                training_cycles=local_tensor.training_cycles + remote_tensor.training_cycles
            )
            return merged

        else:
            raise ValueError(f"Unknown conflict resolution strategy: {strategy}")
```

### Job Locking for Parallel Training

```sql
-- Atomic job lock acquisition
UPDATE training_jobs
SET worker_id = ?, started_at = datetime('now')
WHERE job_id = ?
  AND status = 'pending'
  AND worker_id IS NULL;

-- Check if lock was acquired (rows affected = 1)
```

---

## Version Control with Oxen AI

### Repository Structure

```
tensor-store/                    # Oxen repository
├── templates/                   # Public templates
│   ├── epochs/
│   │   ├── victorian.parquet
│   │   ├── renaissance.parquet
│   │   └── modern.parquet
│   ├── professions/
│   │   ├── detective.parquet
│   │   ├── scientist.parquet
│   │   └── executive.parquet
│   └── archetypes/
│       ├── hero.parquet
│       └── mentor.parquet
├── instances/                   # Published instances
│   ├── public/
│   │   └── published_tensors.parquet
│   └── shared/
│       └── {owner_id}/
│           └── shared_tensors.parquet
├── embeddings/                  # Searchable index
│   ├── templates.index          # FAISS index for templates
│   └── instances.index          # FAISS index for instances
└── metadata/
    ├── catalog.json             # Template catalog
    └── schema.json              # Parquet schemas
```

### Branching Strategy

```
main ────────────────────────────────────────────────▶
  │
  ├── training/batch-001 ──▶ (merge) ──▶
  │
  ├── experiments/new-epochs ──▶ (review) ──▶
  │
  └── users/{user_id}/personal ──▶ (sync)
```

### Oxen Operations

```python
# In oxen_integration/tensor_versioning.py

class TensorVersionController:
    """Manages tensor versioning with Oxen AI."""

    def __init__(self, oxen_client: OxenClient, repo: str = "tensor-store"):
        self.client = oxen_client
        self.repo = repo

    async def publish_template(
        self,
        template: PublicTensorTemplate,
        branch: str = "main"
    ) -> str:
        """Publish a tensor template to Oxen."""

        # Create workspace
        workspace = await self.client.create_workspace(self.repo, branch)

        # Convert to Parquet row
        parquet_data = template.to_parquet_row()

        # Append to templates file
        path = f"templates/{template.category}/{template.name}.parquet"
        await workspace.append_parquet(path, parquet_data)

        # Commit
        commit = await workspace.commit(
            f"Add template: {template.name}",
            metadata={"template_id": template.template_id}
        )

        return commit.hash

    async def sync_local_to_remote(
        self,
        local_db: TensorDatabase,
        since_version: str = None
    ) -> SyncResult:
        """Sync local changes to Oxen."""

        # Get changes since last sync
        changes = local_db.get_changes_since(since_version)

        if not changes:
            return SyncResult(synced=0)

        # Create workspace
        workspace = await self.client.create_workspace(self.repo)

        synced = 0
        for change in changes:
            if change.type == "template":
                await self._sync_template(workspace, change)
            elif change.type == "instance":
                await self._sync_instance(workspace, change)
            synced += 1

        # Commit all changes
        commit = await workspace.commit(
            f"Sync {synced} tensors from local",
            metadata={"sync_count": synced}
        )

        # Update local sync marker
        local_db.update_sync_version(commit.hash)

        return SyncResult(synced=synced, version=commit.hash)

    async def fetch_remote_updates(
        self,
        local_db: TensorDatabase
    ) -> FetchResult:
        """Fetch new tensors from Oxen to local."""

        local_version = local_db.get_sync_version()
        remote_version = await self.client.get_head(self.repo)

        if local_version == remote_version:
            return FetchResult(fetched=0)

        # Get diff
        diff = await self.client.diff(self.repo, local_version, remote_version)

        fetched = 0
        for file_change in diff.files:
            if file_change.path.startswith("templates/"):
                await self._fetch_template(local_db, file_change)
                fetched += 1

        # Update sync marker
        local_db.update_sync_version(remote_version)

        return FetchResult(fetched=fetched, version=remote_version)

    async def create_experiment_branch(
        self,
        name: str,
        description: str
    ) -> str:
        """Create a branch for experimental tensor training."""

        branch_name = f"experiments/{name}"
        await self.client.create_branch(self.repo, branch_name)

        # Add branch metadata
        metadata = {
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }

        workspace = await self.client.create_workspace(self.repo, branch_name)
        await workspace.write_json(f"metadata/branches/{name}.json", metadata)
        await workspace.commit(f"Initialize experiment: {name}")

        return branch_name
```

---

## Access Permissions Model

### Permission Levels

| Level | Description | Capabilities |
|-------|-------------|--------------|
| **Private** | Owner only | Read, write, delete |
| **Shared** | Specific users | Read, clone |
| **Public** | Anyone | Read, clone, fork |
| **API** | Programmatic access | Rate-limited read |

### Permission Schema

```python
class TensorPermission:
    tensor_id: str
    owner_id: str
    access_level: str  # "private", "shared", "public"

    # For shared access
    shared_with: list[str] = []  # User IDs
    shared_groups: list[str] = []  # Group IDs

    # For API access
    api_enabled: bool = False
    rate_limit: int = 100  # requests per hour

    # Audit
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    access_count: int
```

### Permission Enforcement

```python
# In access/permissions.py

class PermissionEnforcer:
    """Enforces tensor access permissions."""

    def __init__(self, db: TensorDatabase):
        self.db = db

    def can_read(self, user_id: str, tensor_id: str) -> bool:
        """Check if user can read tensor."""
        perm = self.db.get_permission(tensor_id)

        if perm.owner_id == user_id:
            return True

        if perm.access_level == "public":
            return True

        if perm.access_level == "shared":
            if user_id in perm.shared_with:
                return True
            if any(g in self.db.get_user_groups(user_id) for g in perm.shared_groups):
                return True

        return False

    def can_write(self, user_id: str, tensor_id: str) -> bool:
        """Check if user can write tensor."""
        perm = self.db.get_permission(tensor_id)
        return perm.owner_id == user_id

    def can_fork(self, user_id: str, tensor_id: str) -> bool:
        """Check if user can fork (clone) tensor."""
        perm = self.db.get_permission(tensor_id)
        return perm.access_level in ("public", "shared") or perm.owner_id == user_id

    def enforce(
        self,
        user_id: str,
        tensor_id: str,
        action: str
    ) -> None:
        """Enforce permission, raise if denied."""
        check_fn = {
            "read": self.can_read,
            "write": self.can_write,
            "fork": self.can_fork,
            "delete": self.can_write,
        }.get(action)

        if not check_fn or not check_fn(user_id, tensor_id):
            raise PermissionDenied(
                f"User {user_id} cannot {action} tensor {tensor_id}"
            )
```

---

## Public API Vision

### API Endpoints

```
/api/v1/
├── templates/
│   ├── GET    /                     # List public templates
│   ├── GET    /{template_id}        # Get template details
│   ├── GET    /{template_id}/tensor # Download tensor values
│   └── POST   /search               # Semantic search
│
├── tensors/
│   ├── GET    /                     # List user's tensors
│   ├── POST   /                     # Create new tensor
│   ├── GET    /{tensor_id}          # Get tensor details
│   ├── PUT    /{tensor_id}          # Update tensor
│   ├── DELETE /{tensor_id}          # Delete tensor
│   ├── POST   /{tensor_id}/train    # Start training job
│   ├── GET    /{tensor_id}/train    # Get training status
│   └── POST   /{tensor_id}/publish  # Publish as template
│
├── search/
│   ├── POST   /semantic             # Semantic tensor search
│   ├── POST   /similar              # Find similar tensors
│   └── POST   /compose              # Compose multiple tensors
│
├── versions/
│   ├── GET    /{tensor_id}/history  # Version history
│   ├── GET    /{tensor_id}/{version}# Specific version
│   └── POST   /{tensor_id}/branch   # Create branch
│
└── auth/
    ├── POST   /token                # Get API token
    └── GET    /me                   # Current user info
```

### API Response Format

```json
{
  "data": {
    "tensor_id": "uuid-here",
    "name": "Victorian Detective",
    "description": "Cognitive tensor for Victorian-era investigator",
    "maturity": 0.97,
    "values": [0.8, 0.3, ...],  // 20-dim array
    "metadata": {
      "category": "profession",
      "training_cycles": 150,
      "usage_count": 42
    },
    "permissions": {
      "access_level": "public",
      "api_enabled": true
    },
    "version": {
      "current": "abc123",
      "parent": "def456",
      "branch": "main"
    }
  },
  "meta": {
    "request_id": "req-uuid",
    "timestamp": "2025-12-03T10:00:00Z"
  }
}
```

### Rate Limiting

| Tier | Requests/Hour | Bulk Operations | Training Jobs |
|------|---------------|-----------------|---------------|
| **Free** | 100 | No | 1 concurrent |
| **Basic** | 1,000 | 10/day | 3 concurrent |
| **Pro** | 10,000 | Unlimited | 10 concurrent |
| **Enterprise** | Unlimited | Unlimited | Unlimited |

---

## Implementation Phases

### Phase 1: Local Persistence (2-3 weeks)

**Goal**: Persist tensors locally with SQLite

- [ ] Create `tensors.db` SQLite schema
- [ ] Implement `TensorDatabase` class with CRUD operations
- [ ] Add tensor serialization (msgpack + base64)
- [ ] Integrate with entity creation pipeline
- [ ] Add tensor save/load to LangGraph workflow
- [ ] Unit tests for persistence layer

**Files to create**:
- `storage/tensor_db.py`
- `storage/serialization.py`
- `tests/unit/test_tensor_persistence.py`

### Phase 2: Parallel Training (2-3 weeks)

**Goal**: Train multiple tensors concurrently

- [ ] Implement `ParallelTensorTrainer` with asyncio
- [ ] Add job queue with SQLite backing
- [ ] Implement job locking for collision prevention
- [ ] Add training node to LangGraph workflow
- [ ] Progress tracking and maturity convergence
- [ ] Integration tests for parallel training

**Files to create**:
- `training/parallel_trainer.py`
- `training/job_queue.py`
- `tests/integration/test_parallel_training.py`

### Phase 3: Retrieval System (2-3 weeks)

**Goal**: Semantic search over stored tensors

- [ ] Integrate sentence-transformers for embeddings
- [ ] Build FAISS local index
- [ ] Implement `TensorRAG` class
- [ ] Add tensor resolution node to pipeline
- [ ] Implement composition strategies
- [ ] Evaluation metrics for retrieval quality

**Files to create**:
- `retrieval/tensor_rag.py`
- `retrieval/embedding_index.py`
- `retrieval/composition.py`
- `tests/unit/test_tensor_rag.py`

### Phase 4: Oxen Integration (3-4 weeks)

**Goal**: Version control and remote sync

- [ ] Define Parquet schemas for Oxen
- [ ] Implement `TensorVersionController`
- [ ] Add sync operations (push/pull)
- [ ] Implement branching for experiments
- [ ] Conflict detection and resolution
- [ ] Migration of existing tensors

**Files to create**:
- `oxen_integration/tensor_versioning.py`
- `oxen_integration/parquet_schemas.py`
- `oxen_integration/sync.py`
- `tests/integration/test_oxen_sync.py`

### Phase 5: Access Control (2 weeks)

**Goal**: Permission system for tensor sharing

- [ ] Implement `PermissionEnforcer`
- [ ] Add user/group management
- [ ] Integrate with all read/write operations
- [ ] Audit logging for access

**Files to create**:
- `access/permissions.py`
- `access/audit.py`
- `tests/unit/test_permissions.py`

### Phase 6: Public API (4-6 weeks)

**Goal**: REST API for external access

- [ ] FastAPI application structure
- [ ] Authentication (API keys)
- [ ] Rate limiting middleware
- [ ] API endpoints implementation
- [ ] OpenAPI documentation
- [ ] Client SDK (Python)

**Files to create**:
- `api/main.py`
- `api/routes/templates.py`
- `api/routes/tensors.py`
- `api/routes/search.py`
- `api/middleware/rate_limit.py`
- `api/middleware/auth.py`
- `sdk/python/timepoint_client/`

---

## Technical Specifications

### Dependencies

```toml
# Add to pyproject.toml
[project.dependencies]
# Existing
# ...

# New for tensor persistence
sentence-transformers = ">=2.2.0"  # Embeddings
faiss-cpu = ">=1.7.0"              # Vector search
pyarrow = ">=14.0.0"               # Parquet support
msgpack = ">=1.0.0"                # Tensor serialization

# New for API (Phase 6)
fastapi = ">=0.100.0"
uvicorn = ">=0.23.0"
python-jose = ">=3.3.0"            # JWT tokens
slowapi = ">=0.1.0"                # Rate limiting
```

### Configuration

```python
# config/tensor_config.py

class TensorPersistenceConfig:
    # Storage
    local_db_path: str = "metadata/tensors.db"
    parquet_compression: str = "snappy"

    # Training
    max_parallel_workers: int = 4
    default_target_maturity: float = 0.95
    training_batch_size: int = 10

    # Retrieval
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    faiss_index_type: str = "Flat"  # or "IVF" for large scale
    search_top_k: int = 10

    # Oxen
    oxen_repo: str = "tensor-store"
    sync_on_commit: bool = True
    auto_sync_interval: int = 3600  # seconds

    # API
    api_port: int = 8080
    rate_limit_default: int = 100
    jwt_secret: str = os.getenv("TENSOR_API_SECRET")
    jwt_algorithm: str = "HS256"
```

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Tensor save latency | < 10ms | Local SQLite |
| Tensor load latency | < 5ms | Cached |
| Semantic search latency | < 100ms | Top-10 results |
| Parallel training throughput | 10 tensors/sec | 4 workers |
| Oxen sync latency | < 5s | Per batch |
| API response time | < 200ms | P95 |

---

## Summary

This plan provides a comprehensive roadmap for implementing tensor persistence in Timepoint Daedalus:

1. **Granular tensors** with public templates and personal instances
2. **Parallel training** with collision handling and job queues
3. **RAG retrieval** for semantic tensor search and composition
4. **Oxen versioning** for tensor lineage and collaboration
5. **Access control** supporting private, shared, and public tensors
6. **Public API** for programmatic tensor access

The implementation is phased over approximately 4-5 months, with each phase building on the previous. Local persistence (Phase 1) provides immediate value, while later phases add collaboration and API features.

---

*Document created: 2025-12-03*
*Status: Planning - No implementation*
