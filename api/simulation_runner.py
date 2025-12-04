"""
Simulation job runner for the API.

Provides background job execution for simulations with progress tracking,
cancellation support, and result storage.

Phase 6: Public API - Simulation Execution
"""

import asyncio
import threading
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from .models_simulation import SimulationStatus, SimulationCreateRequest


# ============================================================================
# Job Storage (In-Memory for MVP)
# ============================================================================

@dataclass
class SimulationJob:
    """Internal simulation job record."""

    job_id: str
    owner_id: str
    status: SimulationStatus
    created_at: datetime

    # Configuration
    template_id: Optional[str] = None
    description: Optional[str] = None
    entity_count: int = 4
    timepoint_count: int = 5
    temporal_mode: str = "pearl"
    generate_summaries: bool = True
    export_formats: list = field(default_factory=lambda: ["json", "markdown"])
    metadata: Optional[Dict[str, Any]] = None

    # Progress tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0
    current_step: Optional[str] = None

    # Results
    run_id: Optional[str] = None
    entities_created: Optional[int] = None
    timepoints_created: Optional[int] = None
    cost_usd: Optional[float] = None
    tokens_used: Optional[int] = None

    # Error handling
    error_message: Optional[str] = None
    cancelled: bool = False
    cancel_reason: Optional[str] = None


# Global job storage (in-memory for MVP, would be database in production)
_JOBS: Dict[str, SimulationJob] = {}
_JOB_LOCK = threading.Lock()


def get_job(job_id: str) -> Optional[SimulationJob]:
    """Get a job by ID."""
    with _JOB_LOCK:
        return _JOBS.get(job_id)


def save_job(job: SimulationJob) -> None:
    """Save a job."""
    with _JOB_LOCK:
        _JOBS[job.job_id] = job


def list_jobs(
    owner_id: Optional[str] = None,
    status: Optional[SimulationStatus] = None,
    limit: int = 100,
    offset: int = 0
) -> tuple[list[SimulationJob], int]:
    """List jobs with optional filtering."""
    with _JOB_LOCK:
        jobs = list(_JOBS.values())

        # Filter by owner
        if owner_id:
            jobs = [j for j in jobs if j.owner_id == owner_id]

        # Filter by status
        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        total = len(jobs)
        return jobs[offset:offset + limit], total


def delete_job(job_id: str) -> bool:
    """Delete a job."""
    with _JOB_LOCK:
        if job_id in _JOBS:
            del _JOBS[job_id]
            return True
        return False


def clear_jobs() -> None:
    """Clear all jobs (for testing)."""
    with _JOB_LOCK:
        _JOBS.clear()


# ============================================================================
# Simulation Runner
# ============================================================================

class SimulationRunner:
    """
    Manages simulation job execution.

    Runs simulations in background threads with progress tracking.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the runner.

        Args:
            max_workers: Maximum concurrent simulations
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_jobs: Dict[str, threading.Event] = {}

    def create_job(
        self,
        request: SimulationCreateRequest,
        owner_id: str
    ) -> SimulationJob:
        """
        Create a new simulation job.

        Args:
            request: Simulation configuration
            owner_id: User creating the job

        Returns:
            Created job
        """
        job = SimulationJob(
            job_id=f"sim_{uuid.uuid4().hex[:12]}",
            owner_id=owner_id,
            status=SimulationStatus.PENDING,
            created_at=datetime.utcnow(),
            template_id=request.template_id,
            description=request.description,
            entity_count=request.entity_count,
            timepoint_count=request.timepoint_count,
            temporal_mode=request.temporal_mode.value,
            generate_summaries=request.generate_summaries,
            export_formats=request.export_formats,
            metadata=request.metadata,
        )

        save_job(job)
        return job

    def start_job(self, job_id: str) -> bool:
        """
        Start a pending job in the background.

        Args:
            job_id: Job to start

        Returns:
            True if started, False if job not found or not pending
        """
        job = get_job(job_id)
        if not job or job.status != SimulationStatus.PENDING:
            return False

        # Create cancellation event
        cancel_event = threading.Event()
        self._running_jobs[job_id] = cancel_event

        # Submit to executor
        self._executor.submit(self._run_simulation, job_id, cancel_event)
        return True

    def cancel_job(self, job_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job to cancel
            reason: Optional cancellation reason

        Returns:
            True if cancelled, False if not running
        """
        job = get_job(job_id)
        if not job:
            return False

        if job.status == SimulationStatus.PENDING:
            # Job hasn't started yet - just mark cancelled
            job.status = SimulationStatus.CANCELLED
            job.cancelled = True
            job.cancel_reason = reason
            job.completed_at = datetime.utcnow()
            save_job(job)
            return True

        if job.status == SimulationStatus.RUNNING:
            # Signal cancellation
            cancel_event = self._running_jobs.get(job_id)
            if cancel_event:
                cancel_event.set()
                job.cancelled = True
                job.cancel_reason = reason
                save_job(job)
                return True

        return False

    def _run_simulation(
        self,
        job_id: str,
        cancel_event: threading.Event
    ) -> None:
        """
        Execute a simulation job.

        This runs in a background thread.
        """
        job = get_job(job_id)
        if not job:
            return

        try:
            # Update status to running
            job.status = SimulationStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.current_step = "Initializing"
            job.progress_percent = 0.0
            save_job(job)

            # Check for cancellation
            if cancel_event.is_set():
                self._mark_cancelled(job)
                return

            # Build simulation config
            job.current_step = "Building configuration"
            job.progress_percent = 5.0
            save_job(job)

            config = self._build_config(job)

            if cancel_event.is_set():
                self._mark_cancelled(job)
                return

            # Run simulation
            job.current_step = "Running simulation"
            job.progress_percent = 10.0
            save_job(job)

            result = self._execute_simulation(job, config, cancel_event)

            if cancel_event.is_set():
                self._mark_cancelled(job)
                return

            # Update with results
            job.status = SimulationStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress_percent = 100.0
            job.current_step = "Complete"

            if result:
                job.run_id = result.get("run_id")
                job.entities_created = result.get("entities_created", 0)
                job.timepoints_created = result.get("timepoints_created", 0)
                job.cost_usd = result.get("cost_usd", 0.0)
                job.tokens_used = result.get("tokens_used", 0)

            save_job(job)

        except Exception as e:
            # Mark as failed
            job.status = SimulationStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            job.current_step = "Failed"
            save_job(job)

        finally:
            # Cleanup
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]

    def _mark_cancelled(self, job: SimulationJob) -> None:
        """Mark a job as cancelled."""
        job.status = SimulationStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        job.current_step = "Cancelled"
        save_job(job)

    def _build_config(self, job: SimulationJob) -> Any:
        """
        Build SimulationConfig from job parameters.

        Returns:
            SimulationConfig instance
        """
        from generation.config_schema import SimulationConfig

        if job.template_id:
            # Load from template
            config = SimulationConfig.from_template(job.template_id)

            # Override counts if specified
            if job.entity_count != 4:
                config.entities.count = job.entity_count
            if job.timepoint_count != 5:
                config.timepoints.count = job.timepoint_count

        else:
            # Create from description using NL interface
            from nl_interface.adapter import NLToProductionAdapter
            adapter = NLToProductionAdapter()

            config = adapter.convert_nl_to_config(
                job.description,
                {
                    "max_entities": job.entity_count,
                    "max_timepoints": job.timepoint_count,
                    "temporal_mode": job.temporal_mode,
                }
            )

        # Apply output settings
        config.outputs.generate_narrative_exports = True
        config.outputs.narrative_export_formats = job.export_formats

        return config

    def _execute_simulation(
        self,
        job: SimulationJob,
        config: Any,
        cancel_event: threading.Event
    ) -> Optional[Dict[str, Any]]:
        """
        Execute the actual simulation.

        This wraps the E2E workflow runner.
        """
        from metadata.run_tracker import MetadataManager
        from e2e_workflows.e2e_runner import FullE2EWorkflowRunner

        # Create metadata manager
        metadata_manager = MetadataManager()

        # Create runner
        runner = FullE2EWorkflowRunner(
            metadata_manager=metadata_manager,
            generate_summary=job.generate_summaries
        )

        # Progress callback
        def update_progress(step: str, percent: float):
            if not cancel_event.is_set():
                job.current_step = step
                job.progress_percent = 10.0 + (percent * 0.9)  # Scale to 10-100%
                save_job(job)

        # Run simulation
        try:
            metadata = runner.run(config)

            return {
                "run_id": metadata.run_id,
                "entities_created": metadata.entities_created,
                "timepoints_created": metadata.timepoints_created,
                "cost_usd": metadata.cost_usd,
                "tokens_used": metadata.tokens_used,
            }

        except Exception as e:
            if cancel_event.is_set():
                return None
            raise

    def get_stats(self, owner_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get job statistics.

        Args:
            owner_id: Optional filter by owner

        Returns:
            Statistics dictionary
        """
        with _JOB_LOCK:
            jobs = list(_JOBS.values())

            if owner_id:
                jobs = [j for j in jobs if j.owner_id == owner_id]

            stats = {
                "total_jobs": len(jobs),
                "pending_jobs": sum(1 for j in jobs if j.status == SimulationStatus.PENDING),
                "running_jobs": sum(1 for j in jobs if j.status == SimulationStatus.RUNNING),
                "completed_jobs": sum(1 for j in jobs if j.status == SimulationStatus.COMPLETED),
                "failed_jobs": sum(1 for j in jobs if j.status == SimulationStatus.FAILED),
                "cancelled_jobs": sum(1 for j in jobs if j.status == SimulationStatus.CANCELLED),
                "total_cost_usd": sum(j.cost_usd or 0 for j in jobs),
                "total_tokens": sum(j.tokens_used or 0 for j in jobs),
            }

            # Calculate average duration
            completed = [
                j for j in jobs
                if j.status == SimulationStatus.COMPLETED
                and j.started_at and j.completed_at
            ]
            if completed:
                durations = [
                    (j.completed_at - j.started_at).total_seconds()
                    for j in completed
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

_runner: Optional[SimulationRunner] = None


def get_simulation_runner() -> SimulationRunner:
    """Get or create the global simulation runner."""
    global _runner
    if _runner is None:
        _runner = SimulationRunner()
    return _runner


def reset_simulation_runner() -> None:
    """Reset the runner (for testing)."""
    global _runner
    if _runner:
        _runner.shutdown()
    _runner = None
    clear_jobs()
