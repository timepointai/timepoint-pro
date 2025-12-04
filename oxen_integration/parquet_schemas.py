"""
Parquet schemas for Oxen tensor versioning.

Defines PyArrow schemas for storing tensors in Parquet format,
enabling efficient columnar storage and versioning with Oxen.

Phase 4: Oxen Integration
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    pa = None
    pq = None


# ============================================================================
# Constants
# ============================================================================

TENSOR_DIMS = 20  # Total tensor dimensions (8 context + 4 biology + 8 behavior)
CONTEXT_DIMS = 8
BIOLOGY_DIMS = 4
BEHAVIOR_DIMS = 8
EMBEDDING_DIMS = 384  # sentence-transformers all-MiniLM-L6-v2


# ============================================================================
# Schema Definitions
# ============================================================================

def get_template_schema() -> "pa.Schema":
    """
    Schema for tensor templates (public archetypes).

    Templates are reusable base tensors representing common patterns
    like professions, epochs, or archetypes.

    Returns:
        PyArrow schema for templates.parquet
    """
    if not PYARROW_AVAILABLE:
        raise ImportError("PyArrow is required for Parquet schemas. Install with: pip install pyarrow")

    return pa.schema([
        # Identity
        pa.field("template_id", pa.string(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("description", pa.string(), nullable=False),
        pa.field("category", pa.string(), nullable=False),  # e.g., "epoch/victorian"

        # Tensor data - stored as separate arrays for clarity
        pa.field("context_vector", pa.list_(pa.float32(), CONTEXT_DIMS), nullable=False),
        pa.field("biology_vector", pa.list_(pa.float32(), BIOLOGY_DIMS), nullable=False),
        pa.field("behavior_vector", pa.list_(pa.float32(), BEHAVIOR_DIMS), nullable=False),

        # Quality metrics
        pa.field("maturity", pa.float32(), nullable=False),
        pa.field("training_cycles", pa.int32(), nullable=False),

        # Embedding for semantic search (variable size to handle None)
        pa.field("embedding", pa.list_(pa.float32()), nullable=True),

        # Metadata
        pa.field("created_at", pa.timestamp("ms"), nullable=False),
        pa.field("updated_at", pa.timestamp("ms"), nullable=False),
        pa.field("usage_count", pa.int32(), nullable=True),

        # Version tracking
        pa.field("version", pa.int32(), nullable=False),
        pa.field("parent_version", pa.int32(), nullable=True),
    ])


def get_instance_schema() -> "pa.Schema":
    """
    Schema for tensor instances (entity-specific tensors).

    Instances are tensors bound to specific entities in simulations,
    potentially derived from templates.

    Returns:
        PyArrow schema for instances.parquet
    """
    if not PYARROW_AVAILABLE:
        raise ImportError("PyArrow is required for Parquet schemas. Install with: pip install pyarrow")

    return pa.schema([
        # Identity
        pa.field("instance_id", pa.string(), nullable=False),
        pa.field("entity_id", pa.string(), nullable=False),
        pa.field("world_id", pa.string(), nullable=False),

        # Template reference (for inheritance tracking)
        pa.field("base_template_id", pa.string(), nullable=True),

        # Tensor data
        pa.field("context_vector", pa.list_(pa.float32(), CONTEXT_DIMS), nullable=False),
        pa.field("biology_vector", pa.list_(pa.float32(), BIOLOGY_DIMS), nullable=False),
        pa.field("behavior_vector", pa.list_(pa.float32(), BEHAVIOR_DIMS), nullable=False),

        # Quality metrics
        pa.field("maturity", pa.float32(), nullable=False),
        pa.field("training_cycles", pa.int32(), nullable=False),

        # Embedding for semantic search (variable size to handle None)
        pa.field("embedding", pa.list_(pa.float32()), nullable=True),

        # Description for RAG
        pa.field("description", pa.string(), nullable=True),
        pa.field("category", pa.string(), nullable=True),

        # Access control
        pa.field("access_level", pa.string(), nullable=False),  # "private", "shared", "public"
        pa.field("owner_id", pa.string(), nullable=False),

        # Timestamps
        pa.field("created_at", pa.timestamp("ms"), nullable=False),
        pa.field("updated_at", pa.timestamp("ms"), nullable=False),

        # Version tracking
        pa.field("version", pa.int32(), nullable=False),
    ])


def get_version_history_schema() -> "pa.Schema":
    """
    Schema for tensor version history.

    Tracks changes to tensors over time for lineage and auditing.

    Returns:
        PyArrow schema for versions.parquet
    """
    if not PYARROW_AVAILABLE:
        raise ImportError("PyArrow is required for Parquet schemas. Install with: pip install pyarrow")

    return pa.schema([
        # Identity
        pa.field("version_id", pa.string(), nullable=False),
        pa.field("tensor_type", pa.string(), nullable=False),  # "template" or "instance"
        pa.field("tensor_id", pa.string(), nullable=False),

        # Version chain
        pa.field("version_number", pa.int32(), nullable=False),
        pa.field("parent_version_id", pa.string(), nullable=True),
        pa.field("oxen_commit", pa.string(), nullable=True),

        # Delta (what changed)
        pa.field("delta_context", pa.list_(pa.float32(), CONTEXT_DIMS), nullable=True),
        pa.field("delta_biology", pa.list_(pa.float32(), BIOLOGY_DIMS), nullable=True),
        pa.field("delta_behavior", pa.list_(pa.float32(), BEHAVIOR_DIMS), nullable=True),
        pa.field("maturity_delta", pa.float32(), nullable=True),
        pa.field("cycles_delta", pa.int32(), nullable=True),

        # Metadata
        pa.field("created_at", pa.timestamp("ms"), nullable=False),
        pa.field("change_type", pa.string(), nullable=True),  # "training", "manual", "merge"
        pa.field("change_notes", pa.string(), nullable=True),
    ])


# ============================================================================
# Conversion Utilities
# ============================================================================

def tensor_record_to_parquet_row(
    record: Any,  # TensorRecord
    tensor_arrays: tuple = None,  # (context, biology, behavior) np arrays
    embedding: np.ndarray = None,
    is_template: bool = False
) -> Dict[str, Any]:
    """
    Convert a TensorRecord to a dict suitable for Parquet.

    Args:
        record: TensorRecord from database
        tensor_arrays: Pre-extracted (context, biology, behavior) arrays
        embedding: Pre-computed embedding array
        is_template: Whether this is a template or instance

    Returns:
        Dict matching the appropriate Parquet schema
    """
    from tensor_serialization import deserialize_tensor

    # Extract tensor arrays if not provided
    if tensor_arrays is None:
        tensor = deserialize_tensor(record.tensor_blob)
        context, biology, behavior = tensor.to_arrays()
    else:
        context, biology, behavior = tensor_arrays

    # Get embedding if not provided
    if embedding is None and record.embedding_blob is not None:
        embedding = np.frombuffer(record.embedding_blob, dtype=np.float32)

    now = datetime.now()

    if is_template:
        return {
            "template_id": record.tensor_id,
            "name": record.entity_id,  # Use entity_id as name for templates
            "description": record.description or "",
            "category": record.category or "uncategorized",
            "context_vector": context.tolist(),
            "biology_vector": biology.tolist(),
            "behavior_vector": behavior.tolist(),
            "maturity": float(record.maturity),
            "training_cycles": int(record.training_cycles),
            "embedding": embedding.tolist() if embedding is not None else None,
            "created_at": record.created_at or now,
            "updated_at": record.updated_at or now,
            "usage_count": 0,
            "version": record.version,
            "parent_version": None,
        }
    else:
        return {
            "instance_id": record.tensor_id,
            "entity_id": record.entity_id,
            "world_id": record.world_id,
            "base_template_id": None,  # Would need to track this
            "context_vector": context.tolist(),
            "biology_vector": biology.tolist(),
            "behavior_vector": behavior.tolist(),
            "maturity": float(record.maturity),
            "training_cycles": int(record.training_cycles),
            "embedding": embedding.tolist() if embedding is not None else None,
            "description": record.description,
            "category": record.category,
            "access_level": "private",  # Default
            "owner_id": "local",  # Default for local
            "created_at": record.created_at or now,
            "updated_at": record.updated_at or now,
            "version": record.version,
        }


def parquet_row_to_tensor_record(
    row: Dict[str, Any],
    is_template: bool = False
) -> Any:
    """
    Convert a Parquet row dict to a TensorRecord.

    Args:
        row: Dict from Parquet table
        is_template: Whether this is a template or instance

    Returns:
        TensorRecord object
    """
    from tensor_persistence import TensorRecord
    from tensor_serialization import serialize_tensor
    from schemas import TTMTensor

    # Extract tensor vectors
    context = np.array(row["context_vector"], dtype=np.float32)
    biology = np.array(row["biology_vector"], dtype=np.float32)
    behavior = np.array(row["behavior_vector"], dtype=np.float32)

    # Create tensor
    tensor = TTMTensor.from_arrays(context, biology, behavior)

    # Get embedding
    embedding_blob = None
    if row.get("embedding") is not None:
        embedding_blob = np.array(row["embedding"], dtype=np.float32).tobytes()

    if is_template:
        return TensorRecord(
            tensor_id=row["template_id"],
            entity_id=row.get("name", ""),
            world_id="",  # Templates don't have world_id
            tensor_blob=serialize_tensor(tensor),
            maturity=row["maturity"],
            training_cycles=row["training_cycles"],
            version=row.get("version", 1),
            description=row.get("description"),
            category=row.get("category"),
            embedding_blob=embedding_blob,
        )
    else:
        return TensorRecord(
            tensor_id=row["instance_id"],
            entity_id=row["entity_id"],
            world_id=row["world_id"],
            tensor_blob=serialize_tensor(tensor),
            maturity=row["maturity"],
            training_cycles=row["training_cycles"],
            version=row.get("version", 1),
            description=row.get("description"),
            category=row.get("category"),
            embedding_blob=embedding_blob,
        )


# ============================================================================
# File I/O
# ============================================================================

def write_templates_parquet(
    records: List[Any],
    path: str,
    append: bool = False
) -> None:
    """
    Write tensor records to a templates Parquet file.

    Args:
        records: List of TensorRecord objects
        path: Output path
        append: Whether to append to existing file
    """
    if not PYARROW_AVAILABLE:
        raise ImportError("PyArrow required. Install with: pip install pyarrow")

    rows = [tensor_record_to_parquet_row(r, is_template=True) for r in records]
    table = pa.Table.from_pylist(rows, schema=get_template_schema())

    if append:
        # Read existing and concatenate
        try:
            existing = pq.read_table(path)
            table = pa.concat_tables([existing, table])
        except FileNotFoundError:
            pass

    pq.write_table(table, path)


def write_instances_parquet(
    records: List[Any],
    path: str,
    append: bool = False
) -> None:
    """
    Write tensor records to an instances Parquet file.

    Args:
        records: List of TensorRecord objects
        path: Output path
        append: Whether to append to existing file
    """
    if not PYARROW_AVAILABLE:
        raise ImportError("PyArrow required. Install with: pip install pyarrow")

    rows = [tensor_record_to_parquet_row(r, is_template=False) for r in records]
    table = pa.Table.from_pylist(rows, schema=get_instance_schema())

    if append:
        try:
            existing = pq.read_table(path)
            table = pa.concat_tables([existing, table])
        except FileNotFoundError:
            pass

    pq.write_table(table, path)


def read_templates_parquet(path: str) -> List[Any]:
    """
    Read tensor records from a templates Parquet file.

    Args:
        path: Input path

    Returns:
        List of TensorRecord objects
    """
    if not PYARROW_AVAILABLE:
        raise ImportError("PyArrow required. Install with: pip install pyarrow")

    table = pq.read_table(path)
    rows = table.to_pylist()
    return [parquet_row_to_tensor_record(row, is_template=True) for row in rows]


def read_instances_parquet(path: str) -> List[Any]:
    """
    Read tensor records from an instances Parquet file.

    Args:
        path: Input path

    Returns:
        List of TensorRecord objects
    """
    if not PYARROW_AVAILABLE:
        raise ImportError("PyArrow required. Install with: pip install pyarrow")

    table = pq.read_table(path)
    rows = table.to_pylist()
    return [parquet_row_to_tensor_record(row, is_template=False) for row in rows]


# ============================================================================
# Schema Validation
# ============================================================================

def validate_parquet_file(path: str, expected_type: str = "instance") -> bool:
    """
    Validate that a Parquet file matches the expected schema.

    Args:
        path: Path to Parquet file
        expected_type: "template" or "instance"

    Returns:
        True if valid, raises ValueError otherwise
    """
    if not PYARROW_AVAILABLE:
        raise ImportError("PyArrow required. Install with: pip install pyarrow")

    expected_schema = get_template_schema() if expected_type == "template" else get_instance_schema()

    table = pq.read_table(path)
    actual_fields = set(table.schema.names)
    expected_fields = set(expected_schema.names)

    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    return True
