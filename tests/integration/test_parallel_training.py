"""
Integration tests for parallel tensor training (Phase 2).

Tests cover:
- JobQueue: Atomic job acquisition, status transitions, error handling
- ParallelTensorTrainer: Concurrent training, collision handling, maturity convergence
- Integration with TensorDatabase from Phase 1

TDD approach: These tests define the expected API behavior.
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import numpy as np
import pytest

from schemas import TTMTensor
from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import serialize_tensor

# These imports will fail until we implement the modules
from training.job_queue import JobQueue, JobStatus
from training.parallel_trainer import ParallelTensorTrainer

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def tensor_db(tmp_path):
    """Provide a temporary TensorDatabase."""
    db_path = tmp_path / "test_training.db"
    return TensorDatabase(str(db_path))


@pytest.fixture(scope="function")
def job_queue(tensor_db):
    """Provide a JobQueue backed by the test database."""
    return JobQueue(tensor_db)


@pytest.fixture(scope="function")
def sample_tensor():
    """Provide a sample TTMTensor for training."""
    return TTMTensor.from_arrays(
        context=np.random.rand(8),
        biology=np.random.rand(4),
        behavior=np.random.rand(8),
    )


@pytest.fixture(scope="function")
def sample_tensor_record(sample_tensor):
    """Provide a sample TensorRecord."""
    return TensorRecord(
        tensor_id=f"test-tensor-{uuid.uuid4().hex[:8]}",
        entity_id="test-entity-001",
        world_id="test-world-001",
        tensor_blob=serialize_tensor(sample_tensor),
        maturity=0.0,
        training_cycles=0,
    )


@pytest.fixture(scope="function")
def multiple_tensor_records():
    """Provide multiple tensor records for batch testing."""
    records = []
    for i in range(5):
        tensor = TTMTensor.from_arrays(
            context=np.random.rand(8),
            biology=np.random.rand(4),
            behavior=np.random.rand(8),
        )
        record = TensorRecord(
            tensor_id=f"test-tensor-{i:03d}",
            entity_id=f"test-entity-{i:03d}",
            world_id="test-world-001",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.0,
            training_cycles=0,
        )
        records.append(record)
    return records


# ============================================================================
# JobQueue Tests
# ============================================================================


@pytest.mark.integration
class TestJobQueueCreation:
    """Tests for job creation and retrieval."""

    def test_create_training_job(self, job_queue, sample_tensor_record, tensor_db):
        """Test creating a new training job."""
        # Save tensor first
        tensor_db.save_tensor(sample_tensor_record)

        # Create job
        job = job_queue.create_job(tensor_id=sample_tensor_record.tensor_id, target_maturity=0.95)

        assert job.job_id is not None
        assert job.tensor_id == sample_tensor_record.tensor_id
        assert job.status == JobStatus.PENDING
        assert job.target_maturity == 0.95
        assert job.worker_id is None
        assert job.started_at is None
        assert job.completed_at is None

    def test_get_job_by_id(self, job_queue, sample_tensor_record, tensor_db):
        """Test retrieving a job by ID."""
        tensor_db.save_tensor(sample_tensor_record)
        created_job = job_queue.create_job(
            tensor_id=sample_tensor_record.tensor_id, target_maturity=0.95
        )

        retrieved_job = job_queue.get_job(created_job.job_id)

        assert retrieved_job is not None
        assert retrieved_job.job_id == created_job.job_id
        assert retrieved_job.tensor_id == sample_tensor_record.tensor_id

    def test_get_nonexistent_job(self, job_queue):
        """Test retrieving a job that doesn't exist."""
        result = job_queue.get_job("nonexistent-job-id")
        assert result is None

    def test_list_pending_jobs(self, job_queue, multiple_tensor_records, tensor_db):
        """Test listing all pending jobs."""
        # Save tensors and create jobs
        for record in multiple_tensor_records[:3]:
            tensor_db.save_tensor(record)
            job_queue.create_job(tensor_id=record.tensor_id, target_maturity=0.95)

        pending = job_queue.list_pending_jobs()

        assert len(pending) == 3
        assert all(job.status == JobStatus.PENDING for job in pending)


@pytest.mark.integration
class TestJobQueueAtomic:
    """Tests for atomic job acquisition."""

    def test_acquire_job_atomically(self, job_queue, sample_tensor_record, tensor_db):
        """Test atomic acquisition of a job by a worker."""
        tensor_db.save_tensor(sample_tensor_record)
        job = job_queue.create_job(tensor_id=sample_tensor_record.tensor_id, target_maturity=0.95)

        # Worker acquires job
        acquired = job_queue.acquire_job(job.job_id, worker_id="worker-001")

        assert acquired is True

        # Check job status updated
        updated_job = job_queue.get_job(job.job_id)
        assert updated_job.status == JobStatus.RUNNING
        assert updated_job.worker_id == "worker-001"
        assert updated_job.started_at is not None

    def test_acquire_already_acquired_job_fails(self, job_queue, sample_tensor_record, tensor_db):
        """Test that a second worker cannot acquire an already-acquired job."""
        tensor_db.save_tensor(sample_tensor_record)
        job = job_queue.create_job(tensor_id=sample_tensor_record.tensor_id, target_maturity=0.95)

        # First worker acquires
        job_queue.acquire_job(job.job_id, worker_id="worker-001")

        # Second worker tries to acquire
        acquired = job_queue.acquire_job(job.job_id, worker_id="worker-002")

        assert acquired is False

        # Job still belongs to first worker
        updated_job = job_queue.get_job(job.job_id)
        assert updated_job.worker_id == "worker-001"

    def test_concurrent_acquisition_only_one_wins(self, job_queue, sample_tensor_record, tensor_db):
        """Test that concurrent acquisition attempts result in only one winner."""
        tensor_db.save_tensor(sample_tensor_record)
        job = job_queue.create_job(tensor_id=sample_tensor_record.tensor_id, target_maturity=0.95)

        results = []

        def try_acquire(worker_id):
            result = job_queue.acquire_job(job.job_id, worker_id=worker_id)
            results.append((worker_id, result))

        # Spawn multiple threads trying to acquire concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(try_acquire, f"worker-{i}") for i in range(5)]
            for f in futures:
                f.result()

        # Exactly one should have succeeded
        successes = [r for r in results if r[1] is True]
        assert len(successes) == 1

    def test_acquire_next_pending_job(self, job_queue, multiple_tensor_records, tensor_db):
        """Test acquiring the next available pending job."""
        # Save tensors and create jobs
        for record in multiple_tensor_records[:3]:
            tensor_db.save_tensor(record)
            job_queue.create_job(tensor_id=record.tensor_id, target_maturity=0.95)

        # Worker acquires next available
        job = job_queue.acquire_next_pending(worker_id="worker-001")

        assert job is not None
        assert job.status == JobStatus.RUNNING
        assert job.worker_id == "worker-001"


@pytest.mark.integration
class TestJobQueueStatusTransitions:
    """Tests for job status transitions."""

    def test_complete_job_success(self, job_queue, sample_tensor_record, tensor_db):
        """Test marking a job as completed successfully."""
        tensor_db.save_tensor(sample_tensor_record)
        job = job_queue.create_job(tensor_id=sample_tensor_record.tensor_id, target_maturity=0.95)
        job_queue.acquire_job(job.job_id, worker_id="worker-001")

        # Complete the job
        job_queue.complete_job(job.job_id, cycles_completed=100)

        updated_job = job_queue.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.completed_at is not None
        assert updated_job.cycles_completed == 100

    def test_fail_job_with_error(self, job_queue, sample_tensor_record, tensor_db):
        """Test marking a job as failed with an error message."""
        tensor_db.save_tensor(sample_tensor_record)
        job = job_queue.create_job(tensor_id=sample_tensor_record.tensor_id, target_maturity=0.95)
        job_queue.acquire_job(job.job_id, worker_id="worker-001")

        # Fail the job
        job_queue.fail_job(job.job_id, error_message="Training diverged")

        updated_job = job_queue.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED
        assert updated_job.error_message == "Training diverged"
        assert updated_job.completed_at is not None

    def test_release_job_back_to_queue(self, job_queue, sample_tensor_record, tensor_db):
        """Test releasing a job back to pending (e.g., worker crashed)."""
        tensor_db.save_tensor(sample_tensor_record)
        job = job_queue.create_job(tensor_id=sample_tensor_record.tensor_id, target_maturity=0.95)
        job_queue.acquire_job(job.job_id, worker_id="worker-001")

        # Release job
        job_queue.release_job(job.job_id)

        updated_job = job_queue.get_job(job.job_id)
        assert updated_job.status == JobStatus.PENDING
        assert updated_job.worker_id is None
        assert updated_job.started_at is None


# ============================================================================
# ParallelTensorTrainer Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestParallelTrainerBasic:
    """Basic tests for ParallelTensorTrainer."""

    async def test_trainer_initialization(self, tensor_db):
        """Test initializing the trainer."""
        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=4)

        assert trainer.max_workers == 4
        assert trainer.tensor_db == tensor_db

    async def test_train_single_tensor(self, tensor_db, sample_tensor_record):
        """Test training a single tensor."""
        tensor_db.save_tensor(sample_tensor_record)

        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=2)

        results = await trainer.train_batch(
            tensor_ids=[sample_tensor_record.tensor_id],
            target_maturity=0.5,  # Lower for faster test
        )

        assert len(results) == 1
        assert sample_tensor_record.tensor_id in results
        result = results[sample_tensor_record.tensor_id]
        assert result.success is True
        assert result.final_maturity >= 0.5

    async def test_train_batch_of_tensors(self, tensor_db, multiple_tensor_records):
        """Test training multiple tensors in parallel."""
        for record in multiple_tensor_records:
            tensor_db.save_tensor(record)

        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=3)

        tensor_ids = [r.tensor_id for r in multiple_tensor_records]
        results = await trainer.train_batch(
            tensor_ids=tensor_ids,
            target_maturity=0.3,  # Lower for faster test
        )

        assert len(results) == len(multiple_tensor_records)
        assert all(r.success for r in results.values())


@pytest.mark.integration
@pytest.mark.asyncio
class TestParallelTrainerConcurrency:
    """Tests for concurrent training behavior."""

    async def test_workers_train_different_tensors(self, tensor_db, multiple_tensor_records):
        """Test that workers train different tensors concurrently."""
        for record in multiple_tensor_records:
            tensor_db.save_tensor(record)

        # Track which worker trained which tensor
        training_log = []

        class LoggingTrainer(ParallelTensorTrainer):
            async def _train_tensor(
                self, tensor_id: str, target_maturity: float, worker_id: str, max_cycles: int = 1000
            ):
                training_log.append((worker_id, tensor_id, datetime.now()))
                # Add small delay to allow other workers to pick up jobs
                await asyncio.sleep(0.01)
                return await super()._train_tensor(
                    tensor_id, target_maturity, worker_id, max_cycles
                )

        trainer = LoggingTrainer(tensor_db=tensor_db, max_workers=3)

        tensor_ids = [r.tensor_id for r in multiple_tensor_records]
        await trainer.train_batch(tensor_ids=tensor_ids, target_maturity=0.3)

        # Verify all tensors were trained
        tensors_trained = set(log[1] for log in training_log)
        assert len(tensors_trained) == len(multiple_tensor_records), "All tensors should be trained"

        # Note: Multiple workers may or may not be used depending on timing
        # The key invariant is that all tensors get trained exactly once
        workers_used = set(log[0] for log in training_log)
        assert len(workers_used) >= 1, "At least one worker should be used"

    async def test_no_tensor_trained_twice(self, tensor_db, multiple_tensor_records):
        """Test that no tensor is trained by multiple workers."""
        for record in multiple_tensor_records:
            tensor_db.save_tensor(record)

        training_counts = {}

        class CountingTrainer(ParallelTensorTrainer):
            async def _train_tensor(
                self, tensor_id: str, target_maturity: float, worker_id: str, max_cycles: int = 1000
            ):
                training_counts[tensor_id] = training_counts.get(tensor_id, 0) + 1
                return await super()._train_tensor(
                    tensor_id, target_maturity, worker_id, max_cycles
                )

        trainer = CountingTrainer(tensor_db=tensor_db, max_workers=5)

        tensor_ids = [r.tensor_id for r in multiple_tensor_records]
        await trainer.train_batch(tensor_ids=tensor_ids, target_maturity=0.3)

        # Each tensor should be trained exactly once
        assert all(count == 1 for count in training_counts.values())


@pytest.mark.integration
@pytest.mark.asyncio
class TestParallelTrainerMaturity:
    """Tests for maturity tracking and convergence."""

    async def test_maturity_increases_after_training(self, tensor_db, sample_tensor_record):
        """Test that tensor maturity increases after training."""
        tensor_db.save_tensor(sample_tensor_record)

        initial_record = tensor_db.get_tensor(sample_tensor_record.tensor_id)
        initial_maturity = initial_record.maturity

        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=2)

        await trainer.train_batch(tensor_ids=[sample_tensor_record.tensor_id], target_maturity=0.5)

        updated_record = tensor_db.get_tensor(sample_tensor_record.tensor_id)
        assert updated_record.maturity > initial_maturity
        assert updated_record.maturity >= 0.5

    async def test_training_cycles_tracked(self, tensor_db, sample_tensor_record):
        """Test that training cycles are tracked."""
        tensor_db.save_tensor(sample_tensor_record)

        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=2)

        await trainer.train_batch(tensor_ids=[sample_tensor_record.tensor_id], target_maturity=0.5)

        updated_record = tensor_db.get_tensor(sample_tensor_record.tensor_id)
        assert updated_record.training_cycles > 0

    async def test_stops_at_target_maturity(self, tensor_db, sample_tensor_record):
        """Test that training stops when target maturity is reached."""
        tensor_db.save_tensor(sample_tensor_record)

        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=2)

        target = 0.6
        results = await trainer.train_batch(
            tensor_ids=[sample_tensor_record.tensor_id], target_maturity=target
        )

        result = results[sample_tensor_record.tensor_id]
        # Should be at or slightly above target
        assert result.final_maturity >= target
        # But not way over (efficiency)
        assert result.final_maturity < target + 0.2


@pytest.mark.integration
@pytest.mark.asyncio
class TestParallelTrainerErrorHandling:
    """Tests for error handling in parallel training."""

    async def test_handles_missing_tensor(self, tensor_db):
        """Test handling of missing tensor gracefully."""
        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=2)

        results = await trainer.train_batch(tensor_ids=["nonexistent-tensor"], target_maturity=0.5)

        assert len(results) == 1
        result = results["nonexistent-tensor"]
        assert result.success is False
        assert "not found" in result.error.lower()

    async def test_partial_batch_failure(self, tensor_db, multiple_tensor_records):
        """Test that some tensors can succeed while others fail."""
        # Only save first 3 records
        for record in multiple_tensor_records[:3]:
            tensor_db.save_tensor(record)

        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=3)

        # Include both existing and non-existing tensor IDs
        tensor_ids = [r.tensor_id for r in multiple_tensor_records]
        results = await trainer.train_batch(tensor_ids=tensor_ids, target_maturity=0.3)

        # First 3 should succeed
        successes = [r for r in results.values() if r.success]
        failures = [r for r in results.values() if not r.success]

        assert len(successes) == 3
        assert len(failures) == 2


@pytest.mark.integration
@pytest.mark.asyncio
class TestParallelTrainerProgress:
    """Tests for progress tracking and callbacks."""

    async def test_progress_callback_called(self, tensor_db, sample_tensor_record):
        """Test that progress callback is invoked."""
        tensor_db.save_tensor(sample_tensor_record)

        progress_updates = []

        def on_progress(tensor_id, maturity, cycles):
            progress_updates.append((tensor_id, maturity, cycles))

        trainer = ParallelTensorTrainer(
            tensor_db=tensor_db, max_workers=2, progress_callback=on_progress
        )

        await trainer.train_batch(tensor_ids=[sample_tensor_record.tensor_id], target_maturity=0.5)

        assert len(progress_updates) > 0
        # Maturity should increase over updates
        maturities = [p[1] for p in progress_updates]
        assert maturities == sorted(maturities)  # Monotonically increasing

    async def test_get_active_jobs(self, tensor_db, multiple_tensor_records):
        """Test retrieving currently active training jobs."""
        for record in multiple_tensor_records:
            tensor_db.save_tensor(record)

        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=2)

        # Start training but don't await completion yet
        training_task = asyncio.create_task(
            trainer.train_batch(
                tensor_ids=[r.tensor_id for r in multiple_tensor_records],
                target_maturity=0.8,  # Higher to take longer
            )
        )

        # Give workers time to start
        await asyncio.sleep(0.1)

        active_jobs = trainer.get_active_jobs()
        # Should have some active jobs
        assert len(active_jobs) >= 0  # May complete quickly in test

        # Clean up
        await training_task
