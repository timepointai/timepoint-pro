"""
Test suite for tensor persistence layer (Phase 1).

TDD approach: Tests written first, implementation follows.
Tests cover:
- Tensor serialization/deserialization roundtrip
- TensorDatabase CRUD operations
- Version history tracking
- Maturity threshold queries
- Batch operations
- Optimistic locking for collision detection
"""

import numpy as np
import pytest

from schemas import TTMTensor
from tensor_persistence import TensorDatabase, TensorRecord

# These imports will fail until implementation exists
# That's expected in TDD - tests define the API contract
from tensor_serialization import (
    deserialize_tensor,
    dict_to_tensor,
    serialize_tensor,
    tensor_to_dict,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_arrays():
    """Sample numpy arrays matching TTMTensor dimensions."""
    return {
        "context": np.array([0.5, 0.3, 0.7, 0.2, 0.8, 0.4, 0.6, 0.1]),  # 8 dims
        "biology": np.array([35.0, 0.9, 0.1, 0.8]),  # 4 dims
        "behavior": np.array([0.6, 0.7, 0.4, 0.5, 0.8, 0.3, 0.7, 0.5]),  # 8 dims
    }


@pytest.fixture
def sample_ttm_tensor(sample_arrays):
    """Sample TTMTensor for testing."""
    return TTMTensor.from_arrays(
        context=sample_arrays["context"],
        biology=sample_arrays["biology"],
        behavior=sample_arrays["behavior"],
    )


@pytest.fixture
def tensor_db(tmp_path):
    """Temporary TensorDatabase for testing."""
    db_path = tmp_path / "tensors_test.db"
    return TensorDatabase(str(db_path))


@pytest.fixture
def sample_record(sample_ttm_tensor):
    """Sample TensorRecord for database tests."""
    from tensor_serialization import serialize_tensor

    return TensorRecord(
        tensor_id="test-tensor-001",
        entity_id="entity-001",
        world_id="world-001",
        tensor_blob=serialize_tensor(sample_ttm_tensor),
        maturity=0.85,
        training_cycles=10,
    )


# ============================================================================
# Serialization Tests
# ============================================================================


@pytest.mark.unit
class TestTensorSerialization:
    """Tests for tensor serialization utilities."""

    def test_serialize_deserialize_roundtrip(self, sample_ttm_tensor, sample_arrays):
        """Tensor should survive serialization/deserialization unchanged."""
        # Serialize
        blob = serialize_tensor(sample_ttm_tensor)
        assert isinstance(blob, bytes)
        assert len(blob) > 0

        # Deserialize
        recovered = deserialize_tensor(blob)
        assert isinstance(recovered, TTMTensor)

        # Verify values match
        ctx, bio, beh = recovered.to_arrays()
        np.testing.assert_array_almost_equal(ctx, sample_arrays["context"])
        np.testing.assert_array_almost_equal(bio, sample_arrays["biology"])
        np.testing.assert_array_almost_equal(beh, sample_arrays["behavior"])

    def test_tensor_to_dict_roundtrip(self, sample_ttm_tensor, sample_arrays):
        """Tensor should survive dict conversion unchanged."""
        # Convert to dict
        d = tensor_to_dict(sample_ttm_tensor)
        assert isinstance(d, dict)
        assert "context_vector" in d
        assert "biology_vector" in d
        assert "behavior_vector" in d

        # Convert back
        recovered = dict_to_tensor(d)
        assert isinstance(recovered, TTMTensor)

        # Verify values
        ctx, bio, beh = recovered.to_arrays()
        np.testing.assert_array_almost_equal(ctx, sample_arrays["context"])
        np.testing.assert_array_almost_equal(bio, sample_arrays["biology"])
        np.testing.assert_array_almost_equal(beh, sample_arrays["behavior"])

    def test_serialize_empty_tensor(self):
        """Should handle zero-valued tensors."""
        empty = TTMTensor.from_arrays(
            context=np.zeros(8),
            biology=np.zeros(4),
            behavior=np.zeros(8),
        )
        blob = serialize_tensor(empty)
        recovered = deserialize_tensor(blob)
        ctx, bio, beh = recovered.to_arrays()
        np.testing.assert_array_equal(ctx, np.zeros(8))
        np.testing.assert_array_equal(bio, np.zeros(4))
        np.testing.assert_array_equal(beh, np.zeros(8))

    def test_serialize_extreme_values(self):
        """Should handle extreme float values."""
        extreme = TTMTensor.from_arrays(
            context=np.array([1e10, -1e10, 0.0, 1e-10, np.pi, np.e, 0.5, 0.5]),
            biology=np.array([100.0, 0.001, 0.999, 1e-5]),
            behavior=np.ones(8) * 0.99999,
        )
        blob = serialize_tensor(extreme)
        recovered = deserialize_tensor(blob)
        ctx, _, _ = recovered.to_arrays()
        assert ctx[0] == pytest.approx(1e10, rel=1e-6)
        assert ctx[1] == pytest.approx(-1e10, rel=1e-6)


# ============================================================================
# Database CRUD Tests
# ============================================================================


@pytest.mark.unit
class TestTensorDatabaseCRUD:
    """Tests for TensorDatabase CRUD operations."""

    def test_database_initialization(self, tensor_db):
        """Database should initialize with correct schema."""
        assert tensor_db.db_path.exists()
        # Verify tables exist
        tables = tensor_db.list_tables()
        assert "tensor_records" in tables
        assert "tensor_versions" in tables
        assert "training_jobs" in tables

    def test_save_tensor(self, tensor_db, sample_record):
        """Should save tensor record to database."""
        tensor_db.save_tensor(sample_record)

        # Verify saved
        record = tensor_db.get_tensor(sample_record.tensor_id)
        assert record is not None
        assert record.tensor_id == sample_record.tensor_id
        assert record.entity_id == sample_record.entity_id
        assert record.maturity == pytest.approx(0.85)
        assert record.training_cycles == 10

    def test_get_nonexistent_tensor(self, tensor_db):
        """Should return None for nonexistent tensor."""
        result = tensor_db.get_tensor("nonexistent-id")
        assert result is None

    def test_update_tensor(self, tensor_db, sample_record):
        """Should update existing tensor record."""
        tensor_db.save_tensor(sample_record)

        # Update maturity and cycles
        sample_record.maturity = 0.95
        sample_record.training_cycles = 20
        tensor_db.save_tensor(sample_record)

        # Verify update
        record = tensor_db.get_tensor(sample_record.tensor_id)
        assert record.maturity == pytest.approx(0.95)
        assert record.training_cycles == 20
        assert record.version == 2  # Version should increment

    def test_delete_tensor(self, tensor_db, sample_record):
        """Should delete tensor record."""
        tensor_db.save_tensor(sample_record)
        assert tensor_db.get_tensor(sample_record.tensor_id) is not None

        tensor_db.delete_tensor(sample_record.tensor_id)
        assert tensor_db.get_tensor(sample_record.tensor_id) is None

    def test_list_tensors(self, tensor_db, sample_ttm_tensor):
        """Should list all tensors."""
        from tensor_serialization import serialize_tensor

        # Save multiple tensors
        for i in range(5):
            record = TensorRecord(
                tensor_id=f"tensor-{i:03d}",
                entity_id=f"entity-{i:03d}",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_ttm_tensor),
                maturity=0.5 + i * 0.1,
                training_cycles=i * 5,
            )
            tensor_db.save_tensor(record)

        tensors = tensor_db.list_tensors()
        assert len(tensors) == 5

    def test_list_tensors_by_entity(self, tensor_db, sample_ttm_tensor):
        """Should filter tensors by entity_id."""
        from tensor_serialization import serialize_tensor

        # Save tensors for different entities
        for i in range(3):
            record = TensorRecord(
                tensor_id=f"tensor-a-{i}",
                entity_id="entity-a",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_ttm_tensor),
                maturity=0.8,
                training_cycles=10,
            )
            tensor_db.save_tensor(record)

        for i in range(2):
            record = TensorRecord(
                tensor_id=f"tensor-b-{i}",
                entity_id="entity-b",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_ttm_tensor),
                maturity=0.8,
                training_cycles=10,
            )
            tensor_db.save_tensor(record)

        entity_a_tensors = tensor_db.list_tensors(entity_id="entity-a")
        assert len(entity_a_tensors) == 3

        entity_b_tensors = tensor_db.list_tensors(entity_id="entity-b")
        assert len(entity_b_tensors) == 2


# ============================================================================
# Maturity Query Tests
# ============================================================================


@pytest.mark.unit
class TestMaturityQueries:
    """Tests for maturity-based tensor queries."""

    def test_get_tensors_by_maturity_threshold(self, tensor_db, sample_ttm_tensor):
        """Should filter tensors by minimum maturity."""
        from tensor_serialization import serialize_tensor

        # Save tensors with varying maturity
        maturities = [0.5, 0.7, 0.85, 0.95, 0.99]
        for i, mat in enumerate(maturities):
            record = TensorRecord(
                tensor_id=f"tensor-{i}",
                entity_id=f"entity-{i}",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_ttm_tensor),
                maturity=mat,
                training_cycles=10,
            )
            tensor_db.save_tensor(record)

        # Query with threshold
        mature = tensor_db.get_by_maturity(min_maturity=0.9)
        assert len(mature) == 2  # 0.95 and 0.99

        operational = tensor_db.get_by_maturity(min_maturity=0.95)
        assert len(operational) == 2  # 0.95 and 0.99

        all_tensors = tensor_db.get_by_maturity(min_maturity=0.0)
        assert len(all_tensors) == 5

    def test_get_immature_tensors(self, tensor_db, sample_ttm_tensor):
        """Should find tensors below maturity threshold (need training)."""
        from tensor_serialization import serialize_tensor

        maturities = [0.3, 0.5, 0.7, 0.95, 0.99]
        for i, mat in enumerate(maturities):
            record = TensorRecord(
                tensor_id=f"tensor-{i}",
                entity_id=f"entity-{i}",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_ttm_tensor),
                maturity=mat,
                training_cycles=10,
            )
            tensor_db.save_tensor(record)

        # Find tensors needing training (maturity < 0.95)
        needs_training = tensor_db.get_by_maturity(max_maturity=0.95)
        assert len(needs_training) == 3  # 0.3, 0.5, 0.7


# ============================================================================
# Version History Tests
# ============================================================================


@pytest.mark.unit
class TestVersionHistory:
    """Tests for tensor version tracking."""

    def test_version_created_on_save(self, tensor_db, sample_record):
        """Should create version entry when tensor is saved."""
        tensor_db.save_tensor(sample_record)

        versions = tensor_db.get_version_history(sample_record.tensor_id)
        assert len(versions) == 1
        assert versions[0].version == 1
        assert versions[0].maturity == pytest.approx(0.85)

    def test_version_increments_on_update(self, tensor_db, sample_record):
        """Should increment version on each update."""
        tensor_db.save_tensor(sample_record)

        # Update multiple times
        for i in range(3):
            sample_record.maturity = 0.85 + (i + 1) * 0.03
            sample_record.training_cycles += 5
            tensor_db.save_tensor(sample_record)

        versions = tensor_db.get_version_history(sample_record.tensor_id)
        assert len(versions) == 4  # Initial + 3 updates
        assert [v.version for v in versions] == [1, 2, 3, 4]

    def test_get_specific_version(self, tensor_db, sample_record):
        """Should retrieve specific version of tensor."""
        tensor_db.save_tensor(sample_record)

        sample_record.maturity = 0.95
        tensor_db.save_tensor(sample_record)

        sample_record.maturity = 0.99
        tensor_db.save_tensor(sample_record)

        # Get version 1 (original)
        v1 = tensor_db.get_tensor_version(sample_record.tensor_id, version=1)
        assert v1.maturity == pytest.approx(0.85)

        # Get version 2
        v2 = tensor_db.get_tensor_version(sample_record.tensor_id, version=2)
        assert v2.maturity == pytest.approx(0.95)

        # Get latest (version 3)
        latest = tensor_db.get_tensor(sample_record.tensor_id)
        assert latest.maturity == pytest.approx(0.99)
        assert latest.version == 3

    def test_version_preserves_tensor_blob(self, tensor_db, sample_ttm_tensor):
        """Each version should preserve its tensor values."""
        from tensor_serialization import deserialize_tensor, serialize_tensor

        # Create record with initial tensor
        record = TensorRecord(
            tensor_id="versioned-tensor",
            entity_id="entity-001",
            world_id="world-001",
            tensor_blob=serialize_tensor(sample_ttm_tensor),
            maturity=0.5,
            training_cycles=5,
        )
        tensor_db.save_tensor(record)

        # Update with modified tensor
        modified = TTMTensor.from_arrays(
            context=np.ones(8) * 0.9,
            biology=np.ones(4) * 0.9,
            behavior=np.ones(8) * 0.9,
        )
        record.tensor_blob = serialize_tensor(modified)
        record.maturity = 0.95
        tensor_db.save_tensor(record)

        # Verify version 1 has original tensor
        v1 = tensor_db.get_tensor_version("versioned-tensor", version=1)
        t1 = deserialize_tensor(v1.tensor_blob)
        ctx1, _, _ = t1.to_arrays()
        # Original context had varied values, not all 0.9
        assert not np.allclose(ctx1, np.ones(8) * 0.9)

        # Verify version 2 has modified tensor
        v2 = tensor_db.get_tensor_version("versioned-tensor", version=2)
        t2 = deserialize_tensor(v2.tensor_blob)
        ctx2, _, _ = t2.to_arrays()
        np.testing.assert_array_almost_equal(ctx2, np.ones(8) * 0.9)


# ============================================================================
# Batch Operations Tests
# ============================================================================


@pytest.mark.unit
class TestBatchOperations:
    """Tests for batch tensor operations."""

    def test_batch_save_tensors(self, tensor_db, sample_ttm_tensor):
        """Should save multiple tensors in single transaction."""
        from tensor_serialization import serialize_tensor

        records = [
            TensorRecord(
                tensor_id=f"batch-{i}",
                entity_id=f"entity-{i}",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_ttm_tensor),
                maturity=0.5 + i * 0.1,
                training_cycles=i * 5,
            )
            for i in range(10)
        ]

        tensor_db.save_tensors_batch(records)

        # Verify all saved
        all_tensors = tensor_db.list_tensors()
        assert len(all_tensors) == 10

    def test_batch_save_rollback_on_error(self, tensor_db, sample_ttm_tensor):
        """Should rollback entire batch on error."""
        from tensor_serialization import serialize_tensor

        # Create records with one invalid (None blob)
        records = [
            TensorRecord(
                tensor_id=f"batch-{i}",
                entity_id=f"entity-{i}",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_ttm_tensor) if i != 5 else None,
                maturity=0.8,
                training_cycles=10,
            )
            for i in range(10)
        ]

        with pytest.raises(Exception):
            tensor_db.save_tensors_batch(records)

        # Verify rollback - no tensors saved
        all_tensors = tensor_db.list_tensors()
        assert len(all_tensors) == 0

    def test_batch_get_tensors(self, tensor_db, sample_ttm_tensor):
        """Should retrieve multiple tensors by IDs."""
        from tensor_serialization import serialize_tensor

        # Save tensors
        ids = []
        for i in range(5):
            record = TensorRecord(
                tensor_id=f"get-batch-{i}",
                entity_id=f"entity-{i}",
                world_id="world-001",
                tensor_blob=serialize_tensor(sample_ttm_tensor),
                maturity=0.8,
                training_cycles=10,
            )
            tensor_db.save_tensor(record)
            ids.append(record.tensor_id)

        # Batch get
        results = tensor_db.get_tensors_batch(ids[:3])
        assert len(results) == 3
        assert all(r.tensor_id in ids[:3] for r in results)


# ============================================================================
# Optimistic Locking Tests
# ============================================================================


@pytest.mark.unit
class TestOptimisticLocking:
    """Tests for collision detection via optimistic locking."""

    def test_save_with_expected_version_succeeds(self, tensor_db, sample_record):
        """Should succeed when expected version matches."""
        tensor_db.save_tensor(sample_record)

        # Update with correct expected version
        sample_record.maturity = 0.95
        success = tensor_db.save_tensor_with_lock(sample_record, expected_version=1)
        assert success is True

        record = tensor_db.get_tensor(sample_record.tensor_id)
        assert record.version == 2
        assert record.maturity == pytest.approx(0.95)

    def test_save_with_wrong_version_fails(self, tensor_db, sample_record):
        """Should fail when expected version doesn't match (collision)."""
        tensor_db.save_tensor(sample_record)

        # Simulate concurrent update
        sample_record.maturity = 0.90
        tensor_db.save_tensor(sample_record)  # Now at version 2

        # Try to update with stale version
        sample_record.maturity = 0.95
        success = tensor_db.save_tensor_with_lock(
            sample_record,
            expected_version=1,  # Stale!
        )
        assert success is False

        # Verify original update persisted
        record = tensor_db.get_tensor(sample_record.tensor_id)
        assert record.version == 2
        assert record.maturity == pytest.approx(0.90)

    def test_concurrent_modification_detection(self, tensor_db, sample_record):
        """Should detect concurrent modifications."""
        tensor_db.save_tensor(sample_record)

        # Read current version
        current = tensor_db.get_tensor(sample_record.tensor_id)
        expected_version = current.version

        # Simulate another process updating
        sample_record.maturity = 0.90
        tensor_db.save_tensor(sample_record)

        # Our update should fail due to version mismatch
        sample_record.maturity = 0.95
        success = tensor_db.save_tensor_with_lock(sample_record, expected_version=expected_version)
        assert success is False


# ============================================================================
# Training History Tests
# ============================================================================


@pytest.mark.unit
class TestTrainingHistory:
    """Tests for training cycle tracking."""

    def test_training_history_recorded(self, tensor_db, sample_record):
        """Should track training cycles across versions."""
        sample_record.training_cycles = 0
        tensor_db.save_tensor(sample_record)

        # Simulate training iterations
        for i in range(5):
            sample_record.training_cycles = (i + 1) * 10
            sample_record.maturity = 0.5 + (i + 1) * 0.1
            tensor_db.save_tensor(sample_record)

        history = tensor_db.get_training_history(sample_record.tensor_id)
        assert len(history) == 6  # Initial + 5 updates

        # Verify progression
        cycles = [h.training_cycles for h in history]
        assert cycles == [0, 10, 20, 30, 40, 50]

        maturities = [h.maturity for h in history]
        assert maturities[0] == pytest.approx(0.85)  # Initial
        assert maturities[-1] == pytest.approx(1.0)  # Final


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestTensorPersistenceIntegration:
    """Integration tests for full tensor lifecycle."""

    def test_full_tensor_lifecycle(self, tensor_db):
        """Test complete lifecycle: create -> train -> query -> version."""
        from tensor_serialization import serialize_tensor

        # 1. Create initial tensor
        initial = TTMTensor.from_arrays(
            context=np.random.rand(8),
            biology=np.random.rand(4),
            behavior=np.random.rand(8),
        )
        record = TensorRecord(
            tensor_id="lifecycle-test",
            entity_id="entity-lifecycle",
            world_id="world-lifecycle",
            tensor_blob=serialize_tensor(initial),
            maturity=0.3,
            training_cycles=0,
        )
        tensor_db.save_tensor(record)

        # 2. Simulate training
        for cycle in range(1, 6):
            record.training_cycles = cycle * 10
            record.maturity = min(1.0, 0.3 + cycle * 0.15)
            tensor_db.save_tensor(record)

        # 3. Verify final state
        final = tensor_db.get_tensor("lifecycle-test")
        assert final.maturity >= 0.95
        assert final.training_cycles == 50
        assert final.version == 6

        # 4. Verify history preserved
        history = tensor_db.get_version_history("lifecycle-test")
        assert len(history) == 6

        # 5. Can retrieve any version
        v1 = tensor_db.get_tensor_version("lifecycle-test", version=1)
        assert v1.maturity == pytest.approx(0.3)

    def test_entity_tensor_roundtrip(self, tensor_db, sample_ttm_tensor):
        """Test saving and loading tensor for entity."""
        from tensor_serialization import deserialize_tensor, serialize_tensor

        entity_id = "entity-roundtrip-test"

        # Save tensor for entity
        record = TensorRecord(
            tensor_id=f"tensor-{entity_id}",
            entity_id=entity_id,
            world_id="world-001",
            tensor_blob=serialize_tensor(sample_ttm_tensor),
            maturity=0.95,
            training_cycles=50,
        )
        tensor_db.save_tensor(record)

        # Load by entity
        tensors = tensor_db.list_tensors(entity_id=entity_id)
        assert len(tensors) == 1

        # Verify tensor integrity
        loaded = deserialize_tensor(tensors[0].tensor_blob)
        original_ctx, original_bio, original_beh = sample_ttm_tensor.to_arrays()
        loaded_ctx, loaded_bio, loaded_beh = loaded.to_arrays()

        np.testing.assert_array_almost_equal(original_ctx, loaded_ctx)
        np.testing.assert_array_almost_equal(original_bio, loaded_bio)
        np.testing.assert_array_almost_equal(original_beh, loaded_beh)
