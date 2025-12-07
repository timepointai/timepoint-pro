"""
Batch job runner for the API.

Provides batch execution for simulations with progress tracking,
budget enforcement, and fail-fast support.

Phase 6: Public API - Batch Submission
"""

import threading
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future

from .models_batch import BatchStatus, BatchPriority
from .models_simulation import SimulationStatus
from .simulation_runner import (
    SimulationRunner,
    SimulationJob,
    get_simulation_runner,
    get_job,
    save_job,
)
from .middleware.usage_quota import (
    record_simulation_start,
    record_simulation_complete,
)


# ============================================================================
# Batch Job Storage
# ============================================================================

@dataclass
class BatchJob:
    """Internal batch job record."""

    batch_id: str
    owner_id: str
    status: BatchStatus
    created_at: datetime

    # Configuration
    priority: BatchPriority = BatchPriority.NORMAL
    fail_fast: bool = False
    parallel_jobs: int = 4
    budget_cap_usd: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Job tracking
    job_ids: List[str] = field(default_factory=list)
    total_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0

    # Cost tracking
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0
    tokens_used: int = 0

    # Progress
    progress_percent: float = 0.0

    # Error handling
    error_message: Optional[str] = None
    cancelled: bool = False
    cancel_reason: Optional[str] = None


# Global batch storage
_BATCHES: Dict[str, BatchJob] = {}
_BATCH_LOCK = threading.Lock()


def get_batch(batch_id: str) -> Optional[BatchJob]:
    """Get a batch by ID."""
    with _BATCH_LOCK:
        return _BATCHES.get(batch_id)


def save_batch(batch: BatchJob) -> None:
    """Save a batch."""
    with _BATCH_LOCK:
        _BATCHES[batch.batch_id] = batch


def list_batches(
    owner_id: Optional[str] = None,
    status: Optional[BatchStatus] = None,
    limit: int = 100,
    offset: int = 0
) -> tuple[List[BatchJob], int]:
    """List batches with optional filtering."""
    with _BATCH_LOCK:
        batches = list(_BATCHES.values())

        # Filter by owner
        if owner_id:
            batches = [b for b in batches if b.owner_id == owner_id]

        # Filter by status
        if status:
            batches = [b for b in batches if b.status == status]

        # Sort by created_at descending
        batches.sort(key=lambda b: b.created_at, reverse=True)

        total = len(batches)
        return batches[offset:offset + limit], total


def delete_batch(batch_id: str) -> bool:
    """Delete a batch."""
    with _BATCH_LOCK:
        if batch_id in _BATCHES:
            del _BATCHES[batch_id]
            return True
        return False


def clear_batches() -> None:
    """Clear all batches (for testing)."""
    with _BATCH_LOCK:
        _BATCHES.clear()


# ============================================================================
# Batch Runner
# ============================================================================

class BatchRunner:
    """
    Manages batch simulation execution.

    Orchestrates multiple simulation jobs with progress tracking,
    budget enforcement, and fail-fast support.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the batch runner.

        Args:
            max_workers: Maximum concurrent batch executions
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_batches: Dict[str, threading.Event] = {}
        self._sim_runner = get_simulation_runner()

    def create_batch(
        self,
        request: "BatchCreateRequest",
        owner_id: str
    ) -> BatchJob:
        """
        Create a new batch from request.

        Args:
            request: Batch creation request
            owner_id: User creating the batch

        Returns:
            Created BatchJob
        """
        from .models_batch import BatchCreateRequest

        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        total_jobs = len(request.simulations)

        # Estimate cost ($0.05 per simulation as rough estimate)
        estimated_cost = total_jobs * 0.05

        batch = BatchJob(
            batch_id=batch_id,
            owner_id=owner_id,
            status=BatchStatus.PENDING,
            created_at=datetime.utcnow(),
            priority=request.priority,
            fail_fast=request.fail_fast,
            parallel_jobs=request.parallel_jobs or 4,
            budget_cap_usd=request.budget_cap_usd,
            metadata=request.metadata,
            total_jobs=total_jobs,
            pending_jobs=total_jobs,
            estimated_cost_usd=estimated_cost,
        )

        # Create individual jobs
        for sim_request in request.simulations:
            job = self._sim_runner.create_job(sim_request, owner_id)
            batch.job_ids.append(job.job_id)

        save_batch(batch)
        return batch

    def start_batch(self, batch_id: str) -> bool:
        """
        Start executing a batch.

        Args:
            batch_id: Batch to start

        Returns:
            True if started, False if not found or not pending
        """
        batch = get_batch(batch_id)
        if not batch or batch.status != BatchStatus.PENDING:
            return False

        # Create cancellation event
        cancel_event = threading.Event()
        self._running_batches[batch_id] = cancel_event

        # Submit to executor
        self._executor.submit(self._run_batch, batch_id, cancel_event)
        return True

    def cancel_batch(
        self,
        batch_id: str,
        reason: Optional[str] = None,
        cancel_running: bool = True
    ) -> bool:
        """
        Cancel a batch.

        Args:
            batch_id: Batch to cancel
            reason: Optional cancellation reason
            cancel_running: Also cancel running jobs

        Returns:
            True if cancelled, False if not running
        """
        batch = get_batch(batch_id)
        if not batch:
            return False

        if batch.status == BatchStatus.PENDING:
            # Batch hasn't started - just mark cancelled
            batch.status = BatchStatus.CANCELLED
            batch.cancelled = True
            batch.cancel_reason = reason
            batch.completed_at = datetime.utcnow()
            save_batch(batch)
            return True

        if batch.status in (BatchStatus.RUNNING, BatchStatus.PARTIAL):
            # Signal cancellation
            cancel_event = self._running_batches.get(batch_id)
            if cancel_event:
                cancel_event.set()

            # Immediately update batch status
            batch.status = BatchStatus.CANCELLED
            batch.cancelled = True
            batch.cancel_reason = reason
            batch.completed_at = datetime.utcnow()

            # Cancel individual running jobs if requested
            if cancel_running:
                for job_id in batch.job_ids:
                    job = get_job(job_id)
                    if job and job.status in (
                        SimulationStatus.PENDING,
                        SimulationStatus.RUNNING
                    ):
                        self._sim_runner.cancel_job(job_id, "Batch cancelled")

            save_batch(batch)
            return True

        return False

    def get_batch_jobs(self, batch_id: str) -> List[SimulationJob]:
        """
        Get all jobs in a batch.

        Args:
            batch_id: Batch ID

        Returns:
            List of SimulationJobs
        """
        batch = get_batch(batch_id)
        if not batch:
            return []

        jobs = []
        for job_id in batch.job_ids:
            job = get_job(job_id)
            if job:
                jobs.append(job)
        return jobs

    def _run_batch(
        self,
        batch_id: str,
        cancel_event: threading.Event
    ) -> None:
        """
        Execute a batch.

        This runs in a background thread.
        """
        batch = get_batch(batch_id)
        if not batch:
            return

        try:
            # Update status to running
            batch.status = BatchStatus.RUNNING
            batch.started_at = datetime.utcnow()
            save_batch(batch)

            # Get jobs to run
            pending_job_ids = list(batch.job_ids)
            running_futures: Dict[str, Future] = {}

            while pending_job_ids or running_futures:
                # Check for cancellation
                if cancel_event.is_set():
                    self._mark_batch_cancelled(batch)
                    return

                # Start new jobs up to parallel limit
                while (
                    pending_job_ids
                    and len(running_futures) < batch.parallel_jobs
                ):
                    job_id = pending_job_ids.pop(0)

                    # Check budget before starting
                    if batch.budget_cap_usd:
                        if batch.actual_cost_usd >= batch.budget_cap_usd:
                            batch.error_message = "Budget cap exceeded"
                            self._finalize_batch(batch)
                            return

                    # Start the job
                    record_simulation_start(batch.owner_id, job_id)
                    self._sim_runner.start_job(job_id)
                    running_futures[job_id] = None  # Placeholder

                    batch.pending_jobs -= 1
                    batch.running_jobs += 1
                    save_batch(batch)

                # Check job status
                completed_jobs = []
                for job_id in list(running_futures.keys()):
                    job = get_job(job_id)
                    if not job:
                        completed_jobs.append(job_id)
                        continue

                    if job.status in (
                        SimulationStatus.COMPLETED,
                        SimulationStatus.FAILED,
                        SimulationStatus.CANCELLED
                    ):
                        completed_jobs.append(job_id)

                        # Update batch stats
                        batch.running_jobs -= 1
                        if job.status == SimulationStatus.COMPLETED:
                            batch.completed_jobs += 1
                            batch.actual_cost_usd += job.cost_usd or 0
                            batch.tokens_used += job.tokens_used or 0
                            record_simulation_complete(
                                batch.owner_id,
                                job_id,
                                success=True,
                                cost_usd=job.cost_usd or 0,
                                tokens=job.tokens_used or 0,
                            )
                        elif job.status == SimulationStatus.FAILED:
                            batch.failed_jobs += 1
                            record_simulation_complete(
                                batch.owner_id,
                                job_id,
                                success=False,
                            )

                            # Check fail-fast
                            if batch.fail_fast:
                                batch.error_message = f"Job {job_id} failed: {job.error_message}"
                                self._cancel_remaining(batch, pending_job_ids)
                                self._finalize_batch(batch)
                                return
                        else:
                            batch.cancelled_jobs += 1

                        # Update progress
                        finished = (
                            batch.completed_jobs
                            + batch.failed_jobs
                            + batch.cancelled_jobs
                        )
                        batch.progress_percent = (finished / batch.total_jobs) * 100
                        save_batch(batch)

                # Remove completed jobs from tracking
                for job_id in completed_jobs:
                    del running_futures[job_id]

                # Update batch status
                if batch.completed_jobs > 0 and (pending_job_ids or running_futures):
                    batch.status = BatchStatus.PARTIAL
                    save_batch(batch)

                # Brief sleep to avoid tight loop
                if running_futures:
                    import time
                    time.sleep(0.5)

            # All jobs finished
            self._finalize_batch(batch)

        except Exception as e:
            batch.status = BatchStatus.FAILED
            batch.completed_at = datetime.utcnow()
            batch.error_message = str(e)
            save_batch(batch)

        finally:
            if batch_id in self._running_batches:
                del self._running_batches[batch_id]

    def _mark_batch_cancelled(self, batch: BatchJob) -> None:
        """Mark batch as cancelled."""
        batch.status = BatchStatus.CANCELLED
        batch.completed_at = datetime.utcnow()
        save_batch(batch)

    def _cancel_remaining(
        self,
        batch: BatchJob,
        pending_job_ids: List[str]
    ) -> None:
        """Cancel remaining pending jobs in batch."""
        for job_id in pending_job_ids:
            job = get_job(job_id)
            if job and job.status == SimulationStatus.PENDING:
                job.status = SimulationStatus.CANCELLED
                job.completed_at = datetime.utcnow()
                save_job(job)
                batch.pending_jobs -= 1
                batch.cancelled_jobs += 1

    def _finalize_batch(self, batch: BatchJob) -> None:
        """Finalize batch status."""
        batch.completed_at = datetime.utcnow()
        batch.progress_percent = 100.0

        if batch.cancelled:
            batch.status = BatchStatus.CANCELLED
        elif batch.failed_jobs > 0 and batch.completed_jobs == 0:
            batch.status = BatchStatus.FAILED
        elif batch.failed_jobs > 0:
            batch.status = BatchStatus.PARTIAL
        else:
            batch.status = BatchStatus.COMPLETED

        save_batch(batch)

    def get_stats(self, owner_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get batch statistics.

        Args:
            owner_id: Optional filter by owner

        Returns:
            Statistics dictionary
        """
        with _BATCH_LOCK:
            batches = list(_BATCHES.values())

            if owner_id:
                batches = [b for b in batches if b.owner_id == owner_id]

            stats = {
                "total_batches": len(batches),
                "pending_batches": sum(
                    1 for b in batches if b.status == BatchStatus.PENDING
                ),
                "running_batches": sum(
                    1 for b in batches if b.status in (
                        BatchStatus.RUNNING, BatchStatus.PARTIAL
                    )
                ),
                "completed_batches": sum(
                    1 for b in batches if b.status == BatchStatus.COMPLETED
                ),
                "failed_batches": sum(
                    1 for b in batches if b.status == BatchStatus.FAILED
                ),
                "total_jobs": sum(b.total_jobs for b in batches),
                "total_cost_usd": sum(b.actual_cost_usd for b in batches),
            }

            # Calculate averages
            if batches:
                stats["avg_jobs_per_batch"] = stats["total_jobs"] / len(batches)
            else:
                stats["avg_jobs_per_batch"] = 0

            # Calculate average duration
            completed = [
                b for b in batches
                if b.status == BatchStatus.COMPLETED
                and b.started_at and b.completed_at
            ]
            if completed:
                durations = [
                    (b.completed_at - b.started_at).total_seconds()
                    for b in completed
                ]
                stats["avg_duration_seconds"] = sum(durations) / len(durations)
            else:
                stats["avg_duration_seconds"] = None

            return stats

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)


# ============================================================================
# Global Runner Instance
# ============================================================================

_batch_runner: Optional[BatchRunner] = None


def get_batch_runner() -> BatchRunner:
    """Get or create the global batch runner."""
    global _batch_runner
    if _batch_runner is None:
        _batch_runner = BatchRunner()
    return _batch_runner


def reset_batch_runner() -> None:
    """Reset the batch runner (for testing)."""
    global _batch_runner
    if _batch_runner:
        _batch_runner.shutdown()
    _batch_runner = None
    clear_batches()
