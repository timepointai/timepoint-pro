"""
Tests for GraphStore transaction support.

Verifies atomic commit/rollback behavior for database operations.
"""

import pytest
import uuid
from datetime import datetime

from storage import GraphStore, TransactionContext
from schemas import Entity, Timepoint, ExposureEvent, ResolutionLevel


@pytest.fixture
def store():
    """Create an in-memory database for testing"""
    db_url = f"sqlite:///:memory:"
    return GraphStore(db_url=db_url)


@pytest.fixture
def sample_entity():
    """Create a sample entity for testing"""
    return Entity(
        entity_id=f"test_entity_{uuid.uuid4().hex[:8]}",
        entity_type="human",
        timepoint="t1",
        resolution_level=ResolutionLevel.SCENE,
        entity_metadata={"name": "Test Person", "role": "tester"}
    )


@pytest.fixture
def sample_timepoint():
    """Create a sample timepoint for testing"""
    return Timepoint(
        timepoint_id=f"test_tp_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now(),
        event_description="Test event"
    )


@pytest.fixture
def sample_exposure_event(sample_entity, sample_timepoint):
    """Create a sample exposure event for testing"""
    return ExposureEvent(
        entity_id=sample_entity.entity_id,
        event_type="witnessed",  # Required field
        timestamp=sample_timepoint.timestamp,
        information="Test information",
        source="test_source"
    )


class TestTransactionContext:
    """Tests for TransactionContext class"""

    def test_transaction_context_created(self, store):
        """Verify transaction context is created properly"""
        with store.transaction() as tx:
            assert isinstance(tx, TransactionContext)
            assert tx._session is not None

    def test_single_save_commits(self, store, sample_entity):
        """Verify single save within transaction commits"""
        entity_id = sample_entity.entity_id  # Capture before transaction
        with store.transaction() as tx:
            tx.save_entity(sample_entity)

        # Verify entity was saved
        retrieved = store.get_entity(entity_id)
        assert retrieved is not None
        assert retrieved.entity_id == entity_id

    def test_multiple_saves_commit_together(self, store):
        """Verify multiple saves in one transaction commit atomically"""
        entity1_id = f"entity1_{uuid.uuid4().hex[:8]}"
        entity2_id = f"entity2_{uuid.uuid4().hex[:8]}"
        tp_id = f"tp_{uuid.uuid4().hex[:8]}"

        entity1 = Entity(
            entity_id=entity1_id,
            entity_type="human",
            timepoint="t1",
            resolution_level=ResolutionLevel.SCENE,
            entity_metadata={"name": "Person 1"}
        )
        entity2 = Entity(
            entity_id=entity2_id,
            entity_type="human",
            timepoint="t1",
            resolution_level=ResolutionLevel.SCENE,
            entity_metadata={"name": "Person 2"}
        )
        timepoint = Timepoint(
            timepoint_id=tp_id,
            timestamp=datetime.now(),
            event_description="Multi-save test"
        )

        with store.transaction() as tx:
            tx.save_entity(entity1)
            tx.save_entity(entity2)
            tx.save_timepoint(timepoint)

        # Verify all were saved
        assert store.get_entity(entity1_id) is not None
        assert store.get_entity(entity2_id) is not None
        assert store.get_timepoint(tp_id) is not None


class TestTransactionRollback:
    """Tests for transaction rollback behavior"""

    def test_rollback_on_exception(self, store):
        """Verify all changes roll back when exception raised"""
        entity = Entity(
            entity_id=f"rollback_test_{uuid.uuid4().hex[:8]}",
            entity_type="human",
            timepoint="t1",
            resolution_level=ResolutionLevel.SCENE,
            entity_metadata={"name": "Should Not Exist"}
        )

        with pytest.raises(ValueError, match="Intentional error"):
            with store.transaction() as tx:
                tx.save_entity(entity)
                raise ValueError("Intentional error for testing rollback")

        # Verify entity was NOT saved due to rollback
        retrieved = store.get_entity(entity.entity_id)
        assert retrieved is None

    def test_partial_saves_rollback(self, store):
        """Verify partial saves roll back on later exception"""
        entity1 = Entity(
            entity_id=f"partial1_{uuid.uuid4().hex[:8]}",
            entity_type="human",
            timepoint="t1",
            resolution_level=ResolutionLevel.SCENE,
            entity_metadata={"name": "Partial 1"}
        )
        entity2 = Entity(
            entity_id=f"partial2_{uuid.uuid4().hex[:8]}",
            entity_type="human",
            timepoint="t1",
            resolution_level=ResolutionLevel.SCENE,
            entity_metadata={"name": "Partial 2"}
        )

        with pytest.raises(RuntimeError, match="Oops"):
            with store.transaction() as tx:
                tx.save_entity(entity1)  # This save should roll back
                tx.save_entity(entity2)  # This save should roll back
                raise RuntimeError("Oops, something went wrong")

        # Neither entity should exist due to rollback
        assert store.get_entity(entity1.entity_id) is None
        assert store.get_entity(entity2.entity_id) is None


class TestTransactionSaveMethods:
    """Tests for all save methods in TransactionContext"""

    def test_save_timepoint(self, store, sample_timepoint):
        """Test save_timepoint in transaction"""
        tp_id = sample_timepoint.timepoint_id  # Capture before transaction
        event_desc = sample_timepoint.event_description
        with store.transaction() as tx:
            tx.save_timepoint(sample_timepoint)

        retrieved = store.get_timepoint(tp_id)
        assert retrieved is not None
        assert retrieved.event_description == event_desc

    def test_save_exposure_event(self, store, sample_entity, sample_exposure_event):
        """Test save_exposure_event in transaction"""
        entity_id = sample_entity.entity_id  # Capture before
        # First save the entity (outside transaction for simplicity)
        store.save_entity(sample_entity)

        with store.transaction() as tx:
            tx.save_exposure_event(sample_exposure_event)

        events = store.get_exposure_events(entity_id)
        assert len(events) >= 1
        assert any(e.information == "Test information" for e in events)

    def test_save_exposure_events_batch(self, store, sample_entity):
        """Test batch save_exposure_events in transaction"""
        entity_id = sample_entity.entity_id  # Capture before
        store.save_entity(sample_entity)

        events = [
            ExposureEvent(
                entity_id=entity_id,
                event_type="learned",  # Required field
                timestamp=datetime.now(),
                information=f"Batch info {i}",
                source="batch_test"
            )
            for i in range(3)
        ]

        with store.transaction() as tx:
            tx.save_exposure_events(events)

        retrieved = store.get_exposure_events(entity_id)
        batch_events = [e for e in retrieved if e.source == "batch_test"]
        assert len(batch_events) == 3


class TestMixedOperations:
    """Tests for mixed read/write operations"""

    def test_existing_entity_update_in_transaction(self, store, sample_entity):
        """Test updating existing entity within transaction"""
        # Save entity first
        store.save_entity(sample_entity)

        # Update via transaction
        updated_entity = Entity(
            entity_id=sample_entity.entity_id,
            entity_type="human",
            timepoint="t2",  # Changed timepoint
            resolution_level=ResolutionLevel.DIALOG,  # Changed resolution
            entity_metadata={"name": "Updated Person", "role": "updated"}
        )

        with store.transaction() as tx:
            tx.save_entity(updated_entity)

        # Verify update
        retrieved = store.get_entity(sample_entity.entity_id)
        assert retrieved.timepoint == "t2"
        assert retrieved.resolution_level == ResolutionLevel.DIALOG
        assert retrieved.entity_metadata["name"] == "Updated Person"
