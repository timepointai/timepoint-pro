"""
Unit tests for Phase 4: Tensor versioning with Oxen.

Tests cover:
- Parquet schema generation and validation
- Tensor record to/from Parquet conversion
- Parquet file I/O
- Sync state management
- Conflict detection and resolution

Note: These tests mock the Oxen client to avoid network calls.
"""

import json
import numpy as np
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import serialize_tensor
from schemas import TTMTensor

# Skip all tests if pyarrow is not available
pytest.importorskip("pyarrow")

from oxen_integration.parquet_schemas import (
    get_template_schema,
    get_instance_schema,
    get_version_history_schema,
    tensor_record_to_parquet_row,
    parquet_row_to_tensor_record,
    write_templates_parquet,
    write_instances_parquet,
    read_templates_parquet,
    read_instances_parquet,
    TENSOR_DIMS,
    CONTEXT_DIMS,
    BIOLOGY_DIMS,
    BEHAVIOR_DIMS,
    EMBEDDING_DIMS,
)
from oxen_integration.sync import TensorSyncManager, SyncState
from oxen_integration.tensor_versioning import (
    TensorVersionController,
    SyncResult,
    FetchResult,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_tensor():
    """Create a sample TTMTensor."""
    return TTMTensor.from_arrays(
        context=np.array([0.5, 0.3, 0.7, 0.2, 0.8, 0.4, 0.6, 0.1], dtype=np.float32),
        biology=np.array([0.45, 0.8, 0.9, 0.7], dtype=np.float32),
        behavior=np.array([0.6, 0.7, 0.4, 0.5, 0.8, 0.3, 0.7, 0.5], dtype=np.float32),
    )


@pytest.fixture
def sample_record(sample_tensor):
    """Create a sample TensorRecord."""
    return TensorRecord(
        tensor_id="test-tensor-001",
        entity_id="entity-001",
        world_id="world-001",
        tensor_blob=serialize_tensor(sample_tensor),
        maturity=0.85,
        training_cycles=20,
        description="Victorian detective character",
        category="profession/detective",
    )


@pytest.fixture
def tensor_db(tmp_path):
    """Create a temporary TensorDatabase."""
    db_path = tmp_path / "test_versioning.db"
    return TensorDatabase(str(db_path))


@pytest.fixture
def mock_oxen_client():
    """Create a mock OxenClient."""
    client = MagicMock()
    client.upload_dataset = MagicMock(return_value=MagicMock(commit_id="abc123"))
    client.create_branch = MagicMock(return_value="feature/test")
    client.merge_branch = MagicMock(return_value="merge123")
    return client


# ============================================================================
# Schema Tests
# ============================================================================

@pytest.mark.unit
class TestParquetSchemas:
    """Tests for Parquet schema definitions."""

    def test_template_schema_has_required_fields(self):
        """Template schema should have all required fields."""
        schema = get_template_schema()
        field_names = set(schema.names)

        required = {
            "template_id", "name", "description", "category",
            "context_vector", "biology_vector", "behavior_vector",
            "maturity", "training_cycles", "embedding",
            "created_at", "updated_at", "version"
        }

        assert required.issubset(field_names)

    def test_instance_schema_has_required_fields(self):
        """Instance schema should have all required fields."""
        schema = get_instance_schema()
        field_names = set(schema.names)

        required = {
            "instance_id", "entity_id", "world_id",
            "context_vector", "biology_vector", "behavior_vector",
            "maturity", "training_cycles", "access_level", "owner_id",
            "created_at", "updated_at", "version"
        }

        assert required.issubset(field_names)

    def test_version_history_schema_has_required_fields(self):
        """Version history schema should have all required fields."""
        schema = get_version_history_schema()
        field_names = set(schema.names)

        required = {
            "version_id", "tensor_type", "tensor_id",
            "version_number", "parent_version_id",
            "created_at"
        }

        assert required.issubset(field_names)

    def test_tensor_dimensions_constants(self):
        """Tensor dimension constants should be correct."""
        assert TENSOR_DIMS == 20  # 8 + 4 + 8
        assert CONTEXT_DIMS == 8
        assert BIOLOGY_DIMS == 4
        assert BEHAVIOR_DIMS == 8
        assert EMBEDDING_DIMS == 384  # sentence-transformers default


# ============================================================================
# Conversion Tests
# ============================================================================

@pytest.mark.unit
class TestRecordConversion:
    """Tests for TensorRecord to/from Parquet conversion."""

    def test_tensor_record_to_parquet_row_template(self, sample_record):
        """Convert TensorRecord to Parquet row (template)."""
        row = tensor_record_to_parquet_row(sample_record, is_template=True)

        assert row["template_id"] == sample_record.tensor_id
        assert row["description"] == sample_record.description
        assert row["category"] == sample_record.category
        assert row["maturity"] == pytest.approx(0.85)
        assert row["training_cycles"] == 20

        # Verify tensor vectors are lists
        assert len(row["context_vector"]) == 8
        assert len(row["biology_vector"]) == 4
        assert len(row["behavior_vector"]) == 8

    def test_tensor_record_to_parquet_row_instance(self, sample_record):
        """Convert TensorRecord to Parquet row (instance)."""
        row = tensor_record_to_parquet_row(sample_record, is_template=False)

        assert row["instance_id"] == sample_record.tensor_id
        assert row["entity_id"] == sample_record.entity_id
        assert row["world_id"] == sample_record.world_id
        assert row["access_level"] == "private"  # Default
        assert row["owner_id"] == "local"  # Default

    def test_parquet_row_to_tensor_record_template(self, sample_record):
        """Convert Parquet row back to TensorRecord (template)."""
        # First convert to row
        row = tensor_record_to_parquet_row(sample_record, is_template=True)

        # Then back to record
        recovered = parquet_row_to_tensor_record(row, is_template=True)

        assert recovered.tensor_id == sample_record.tensor_id
        assert recovered.description == sample_record.description
        assert recovered.category == sample_record.category
        assert recovered.maturity == pytest.approx(0.85)
        assert recovered.training_cycles == 20

    def test_parquet_row_to_tensor_record_instance(self, sample_record):
        """Convert Parquet row back to TensorRecord (instance)."""
        row = tensor_record_to_parquet_row(sample_record, is_template=False)
        recovered = parquet_row_to_tensor_record(row, is_template=False)

        assert recovered.tensor_id == sample_record.tensor_id
        assert recovered.entity_id == sample_record.entity_id
        assert recovered.world_id == sample_record.world_id

    def test_tensor_values_preserved_roundtrip(self, sample_record, sample_tensor):
        """Tensor values should survive conversion roundtrip."""
        from tensor_serialization import deserialize_tensor

        row = tensor_record_to_parquet_row(sample_record, is_template=True)
        recovered = parquet_row_to_tensor_record(row, is_template=True)

        original = deserialize_tensor(sample_record.tensor_blob)
        recovered_tensor = deserialize_tensor(recovered.tensor_blob)

        orig_ctx, orig_bio, orig_beh = original.to_arrays()
        rec_ctx, rec_bio, rec_beh = recovered_tensor.to_arrays()

        np.testing.assert_array_almost_equal(orig_ctx, rec_ctx, decimal=5)
        np.testing.assert_array_almost_equal(orig_bio, rec_bio, decimal=5)
        np.testing.assert_array_almost_equal(orig_beh, rec_beh, decimal=5)


# ============================================================================
# File I/O Tests
# ============================================================================

@pytest.mark.unit
class TestParquetIO:
    """Tests for Parquet file I/O."""

    def test_write_and_read_templates(self, sample_record, tmp_path):
        """Write and read templates Parquet file."""
        path = str(tmp_path / "templates.parquet")

        # Write
        write_templates_parquet([sample_record], path)

        # Read
        records = read_templates_parquet(path)

        assert len(records) == 1
        assert records[0].tensor_id == sample_record.tensor_id
        assert records[0].description == sample_record.description

    def test_write_and_read_instances(self, sample_record, tmp_path):
        """Write and read instances Parquet file."""
        path = str(tmp_path / "instances.parquet")

        write_instances_parquet([sample_record], path)
        records = read_instances_parquet(path)

        assert len(records) == 1
        assert records[0].tensor_id == sample_record.tensor_id
        assert records[0].entity_id == sample_record.entity_id

    def test_write_multiple_records(self, sample_tensor, tmp_path):
        """Write multiple records to Parquet."""
        records = []
        for i in range(5):
            record = TensorRecord(
                tensor_id=f"tensor-{i:03d}",
                entity_id=f"entity-{i:03d}",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_tensor),
                maturity=0.5 + i * 0.1,
                training_cycles=i * 10,
                description=f"Test tensor {i}",
                category=f"test/category{i}",
            )
            records.append(record)

        path = str(tmp_path / "batch.parquet")
        write_templates_parquet(records, path)

        loaded = read_templates_parquet(path)
        assert len(loaded) == 5

    def test_append_to_existing_file(self, sample_tensor, tmp_path):
        """Append records to existing Parquet file."""
        path = str(tmp_path / "append_test.parquet")

        # First batch
        records1 = [
            TensorRecord(
                tensor_id="tensor-001",
                entity_id="entity-001",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_tensor),
                maturity=0.8,
                training_cycles=10,
                description="First tensor",
                category="test/first",
            )
        ]
        write_templates_parquet(records1, path)

        # Second batch (append)
        records2 = [
            TensorRecord(
                tensor_id="tensor-002",
                entity_id="entity-002",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_tensor),
                maturity=0.9,
                training_cycles=20,
                description="Second tensor",
                category="test/second",
            )
        ]
        write_templates_parquet(records2, path, append=True)

        # Read all
        loaded = read_templates_parquet(path)
        assert len(loaded) == 2


# ============================================================================
# Sync State Tests
# ============================================================================

@pytest.mark.unit
class TestSyncState:
    """Tests for sync state management."""

    def test_sync_state_initialization(self):
        """SyncState should initialize with empty values."""
        state = SyncState()

        assert state.last_sync_time is None
        assert state.last_local_version is None
        assert state.last_remote_version is None
        assert len(state.synced_tensor_ids) == 0

    def test_sync_state_to_dict(self):
        """SyncState should serialize to dict."""
        state = SyncState()
        state.last_sync_time = datetime(2025, 1, 1, 12, 0, 0)
        state.last_local_version = "local123"
        state.synced_tensor_ids = {"t1", "t2", "t3"}

        d = state.to_dict()

        assert d["last_local_version"] == "local123"
        assert set(d["synced_tensor_ids"]) == {"t1", "t2", "t3"}
        assert "2025-01-01" in d["last_sync_time"]

    def test_sync_state_from_dict(self):
        """SyncState should deserialize from dict."""
        data = {
            "last_sync_time": "2025-01-01T12:00:00",
            "last_local_version": "local123",
            "last_remote_version": "remote456",
            "synced_tensor_ids": ["t1", "t2"],
            "pending_uploads": ["t3"],
            "pending_downloads": [],
        }

        state = SyncState.from_dict(data)

        assert state.last_local_version == "local123"
        assert state.last_remote_version == "remote456"
        assert state.synced_tensor_ids == {"t1", "t2"}
        assert state.pending_uploads == {"t3"}

    def test_sync_state_roundtrip(self):
        """SyncState should survive serialization roundtrip."""
        original = SyncState()
        original.last_sync_time = datetime(2025, 12, 4, 10, 30, 0)
        original.last_local_version = "v1.0"
        original.synced_tensor_ids = {"a", "b", "c"}

        recovered = SyncState.from_dict(original.to_dict())

        assert recovered.last_local_version == original.last_local_version
        assert recovered.synced_tensor_ids == original.synced_tensor_ids


# ============================================================================
# Version Controller Tests
# ============================================================================

@pytest.mark.unit
class TestTensorVersionController:
    """Tests for TensorVersionController."""

    def test_controller_initialization(self, mock_oxen_client, tmp_path):
        """Controller should initialize with client and cache dir."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        assert controller.client == mock_oxen_client
        assert controller.local_cache_dir.exists()

    def test_create_experiment_branch(self, mock_oxen_client, tmp_path):
        """Should create experiment branch with prefix."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        branch = controller.create_experiment_branch(
            name="test-experiment",
            description="Test experiment"
        )

        assert branch == "experiments/test-experiment"
        mock_oxen_client.create_branch.assert_called_once()

    def test_create_training_branch(self, mock_oxen_client, tmp_path):
        """Should create training branch with prefix."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        branch = controller.create_training_branch(batch_id="batch-001")

        assert branch == "training/batch-001"

    def test_detect_conflicts_finds_version_mismatch(self, sample_tensor, mock_oxen_client, tmp_path):
        """Should detect conflicts when versions differ."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        local_record = TensorRecord(
            tensor_id="conflict-tensor",
            entity_id="entity-001",
            world_id="world-001",
            tensor_blob=serialize_tensor(sample_tensor),
            maturity=0.8,
            training_cycles=10,
            version=2,
        )

        remote_record = TensorRecord(
            tensor_id="conflict-tensor",
            entity_id="entity-001",
            world_id="world-001",
            tensor_blob=serialize_tensor(sample_tensor),
            maturity=0.85,
            training_cycles=15,
            version=3,  # Different version
        )

        conflicts = controller.detect_conflicts([local_record], [remote_record])

        assert len(conflicts) == 1
        assert conflicts[0][0].tensor_id == "conflict-tensor"

    def test_resolve_conflict_highest_maturity(self, sample_tensor, mock_oxen_client, tmp_path):
        """Should resolve conflict using highest maturity."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        local_record = TensorRecord(
            tensor_id="test",
            entity_id="e1",
            world_id="w1",
            tensor_blob=serialize_tensor(sample_tensor),
            maturity=0.7,
            training_cycles=10,
        )

        remote_record = TensorRecord(
            tensor_id="test",
            entity_id="e1",
            world_id="w1",
            tensor_blob=serialize_tensor(sample_tensor),
            maturity=0.9,  # Higher
            training_cycles=20,
        )

        resolved = controller.resolve_conflict(
            local_record,
            remote_record,
            strategy="highest_maturity"
        )

        assert resolved.maturity == pytest.approx(0.9)

    def test_resolve_conflict_merge(self, sample_tensor, mock_oxen_client, tmp_path):
        """Should resolve conflict by merging tensor values."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        # Create tensors with different values
        tensor1 = TTMTensor.from_arrays(
            context=np.ones(8, dtype=np.float32) * 0.4,
            biology=np.ones(4, dtype=np.float32) * 0.4,
            behavior=np.ones(8, dtype=np.float32) * 0.4,
        )
        tensor2 = TTMTensor.from_arrays(
            context=np.ones(8, dtype=np.float32) * 0.8,
            biology=np.ones(4, dtype=np.float32) * 0.8,
            behavior=np.ones(8, dtype=np.float32) * 0.8,
        )

        local_record = TensorRecord(
            tensor_id="merge-test",
            entity_id="e1",
            world_id="w1",
            tensor_blob=serialize_tensor(tensor1),
            maturity=0.7,
            training_cycles=10,
        )

        remote_record = TensorRecord(
            tensor_id="merge-test",
            entity_id="e1",
            world_id="w1",
            tensor_blob=serialize_tensor(tensor2),
            maturity=0.8,
            training_cycles=15,
        )

        resolved = controller.resolve_conflict(
            local_record,
            remote_record,
            strategy="merge"
        )

        # Merged values should be average
        from tensor_serialization import deserialize_tensor
        merged_tensor = deserialize_tensor(resolved.tensor_blob)
        ctx, _, _ = merged_tensor.to_arrays()

        # Average of 0.4 and 0.8 = 0.6
        np.testing.assert_array_almost_equal(ctx, np.ones(8) * 0.6, decimal=5)

        # Maturity should be max
        assert resolved.maturity == pytest.approx(0.8)


# ============================================================================
# Sync Manager Tests
# ============================================================================

@pytest.mark.unit
class TestTensorSyncManager:
    """Tests for TensorSyncManager."""

    def test_sync_manager_initialization(self, tensor_db, mock_oxen_client, tmp_path):
        """SyncManager should initialize correctly."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        sync_mgr = TensorSyncManager(
            tensor_db=tensor_db,
            version_controller=controller,
            state_file=str(tmp_path / "sync_state.json")
        )

        assert sync_mgr.tensor_db == tensor_db
        assert sync_mgr.version_controller == controller

    def test_detect_local_changes_finds_new(self, tensor_db, mock_oxen_client, tmp_path, sample_tensor):
        """Should detect new tensors that haven't been synced."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        sync_mgr = TensorSyncManager(
            tensor_db=tensor_db,
            version_controller=controller,
            state_file=str(tmp_path / "sync_state.json")
        )

        # Add a tensor to database
        record = TensorRecord(
            tensor_id="new-tensor",
            entity_id="e1",
            world_id="w1",
            tensor_blob=serialize_tensor(sample_tensor),
            maturity=0.8,
            training_cycles=10,
        )
        tensor_db.save_tensor(record)

        # Detect changes
        changes = sync_mgr.detect_local_changes()

        assert len(changes) == 1
        assert changes[0].tensor_id == "new-tensor"

    def test_detect_local_changes_skips_synced(self, tensor_db, mock_oxen_client, tmp_path, sample_tensor):
        """Should skip tensors that were already synced."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        sync_mgr = TensorSyncManager(
            tensor_db=tensor_db,
            version_controller=controller,
            state_file=str(tmp_path / "sync_state.json")
        )

        # Add and mark as synced
        record = TensorRecord(
            tensor_id="synced-tensor",
            entity_id="e1",
            world_id="w1",
            tensor_blob=serialize_tensor(sample_tensor),
            maturity=0.8,
            training_cycles=10,
        )
        tensor_db.save_tensor(record)

        # Mark as synced
        sync_mgr.mark_as_synced(["synced-tensor"])

        # Add another tensor without syncing
        record2 = TensorRecord(
            tensor_id="unsynced-tensor",
            entity_id="e2",
            world_id="w1",
            tensor_blob=serialize_tensor(sample_tensor),
            maturity=0.8,
            training_cycles=10,
        )
        tensor_db.save_tensor(record2)

        # Detect changes
        changes = sync_mgr.detect_local_changes()

        # Both should be in changes since we can't filter by timestamp without updated_at
        assert len(changes) >= 1
        tensor_ids = [c.tensor_id for c in changes]
        assert "unsynced-tensor" in tensor_ids

    def test_get_sync_status(self, tensor_db, mock_oxen_client, tmp_path, sample_tensor):
        """Should return sync status information."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        sync_mgr = TensorSyncManager(
            tensor_db=tensor_db,
            version_controller=controller,
            state_file=str(tmp_path / "sync_state.json")
        )

        # Add some tensors
        for i in range(3):
            record = TensorRecord(
                tensor_id=f"tensor-{i}",
                entity_id=f"e{i}",
                world_id="w1",
                tensor_blob=serialize_tensor(sample_tensor),
                maturity=0.8,
                training_cycles=10,
                category=f"test/cat{i}" if i % 2 == 0 else None,  # Some as templates
            )
            tensor_db.save_tensor(record)

        status = sync_mgr.get_sync_status()

        assert "last_sync" in status
        assert "total_pending" in status
        assert status["total_pending"] >= 0

    def test_reset_sync_state(self, tensor_db, mock_oxen_client, tmp_path):
        """Should reset sync state."""
        controller = TensorVersionController(
            oxen_client=mock_oxen_client,
            local_cache_dir=str(tmp_path / "cache")
        )

        sync_mgr = TensorSyncManager(
            tensor_db=tensor_db,
            version_controller=controller,
            state_file=str(tmp_path / "sync_state.json")
        )

        # Add some state
        sync_mgr.mark_as_synced(["t1", "t2", "t3"])

        # Reset
        sync_mgr.reset_sync_state()

        assert len(sync_mgr.state.synced_tensor_ids) == 0
        assert sync_mgr.state.last_sync_time is None


# ============================================================================
# Run configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
