"""
Job queue for parallel tensor training.

Provides SQLite-backed job queue with atomic locking for
collision-free parallel training.

Phase 2: Parallel Training Infrastructure
"""

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from tensor_persistence import TensorDatabase


class JobStatus(str, Enum):
    """Status of a training job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrainingJob:
    """
    Represents a tensor training job.

    Attributes:
        job_id: Unique job identifier
        tensor_id: ID of tensor to train
        status: Current job status
        target_maturity: Target maturity level (0.0-1.0)
        worker_id: ID of worker processing this job (if running)
        started_at: When job started (if running/completed)
        completed_at: When job finished (if completed/failed)
        cycles_completed: Number of training cycles completed
        error_message: Error message (if failed)
        created_at: When job was created
    """

    job_id: str
    tensor_id: str
    status: JobStatus = JobStatus.PENDING
    target_maturity: float = 0.95
    worker_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cycles_completed: int = 0
    error_message: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_row(cls, row: tuple) -> "TrainingJob":
        """Create TrainingJob from SQLite row."""
        return cls(
            job_id=row[0],
            tensor_id=row[1],
            status=JobStatus(row[2]),
            target_maturity=row[3],
            worker_id=row[4],
            started_at=datetime.fromisoformat(row[5]) if row[5] else None,
            completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
            cycles_completed=row[7],
            error_message=row[8],
            created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
        )


class JobQueue:
    """
    SQLite-backed job queue for parallel training.

    Provides atomic job acquisition to prevent multiple workers
    from training the same tensor.

    Uses the training_jobs table from TensorDatabase.
    """

    def __init__(self, tensor_db: TensorDatabase):
        """
        Initialize job queue.

        Args:
            tensor_db: TensorDatabase instance (provides SQLite connection)
        """
        self.tensor_db = tensor_db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure training_jobs table exists with correct schema."""
        # TensorDatabase already creates training_jobs table
        # But we add any missing columns or indexes here
        conn = sqlite3.connect(str(self.tensor_db.db_path))
        try:
            cursor = conn.cursor()

            # Check if table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='training_jobs'"
            )
            if not cursor.fetchone():
                # Create table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE training_jobs (
                        job_id TEXT PRIMARY KEY,
                        tensor_id TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        target_maturity REAL NOT NULL DEFAULT 0.95,
                        worker_id TEXT,
                        started_at TEXT,
                        completed_at TEXT,
                        cycles_completed INTEGER DEFAULT 0,
                        error_message TEXT,
                        created_at TEXT NOT NULL
                    )
                """)

                # Create indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON training_jobs(status)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_jobs_tensor ON training_jobs(tensor_id)"
                )

                conn.commit()
            else:
                # Table exists - check for missing columns and add them
                cursor.execute("PRAGMA table_info(training_jobs)")
                columns = {row[1] for row in cursor.fetchall()}

                # Add cycles_completed if missing
                if "cycles_completed" not in columns:
                    cursor.execute(
                        "ALTER TABLE training_jobs ADD COLUMN cycles_completed INTEGER DEFAULT 0"
                    )
                    conn.commit()

                # Add created_at if missing
                if "created_at" not in columns:
                    cursor.execute("ALTER TABLE training_jobs ADD COLUMN created_at TEXT")
                    conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a new SQLite connection."""
        conn = sqlite3.connect(str(self.tensor_db.db_path))
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        # Set busy timeout for lock contention
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def create_job(self, tensor_id: str, target_maturity: float = 0.95) -> TrainingJob:
        """
        Create a new training job.

        Args:
            tensor_id: ID of tensor to train
            target_maturity: Target maturity level

        Returns:
            Created TrainingJob
        """
        job = TrainingJob(
            job_id=str(uuid.uuid4()),
            tensor_id=tensor_id,
            target_maturity=target_maturity,
            created_at=datetime.now(),
        )

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO training_jobs
                (job_id, tensor_id, status, target_maturity, worker_id,
                 started_at, completed_at, cycles_completed, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.tensor_id,
                    job.status.value,
                    job.target_maturity,
                    job.worker_id,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.cycles_completed,
                    job.error_message,
                    job.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return job

    def get_job(self, job_id: str) -> TrainingJob | None:
        """
        Get a job by ID.

        Args:
            job_id: Job ID to retrieve

        Returns:
            TrainingJob if found, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT job_id, tensor_id, status, target_maturity, worker_id,
                       started_at, completed_at, cycles_completed, error_message, created_at
                FROM training_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            )
            row = cursor.fetchone()

            if row:
                return TrainingJob.from_row(row)
            return None
        finally:
            conn.close()

    def list_pending_jobs(self) -> list[TrainingJob]:
        """
        List all pending jobs.

        Returns:
            List of pending TrainingJob objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT job_id, tensor_id, status, target_maturity, worker_id,
                       started_at, completed_at, cycles_completed, error_message, created_at
                FROM training_jobs
                WHERE status = ?
                ORDER BY created_at ASC
                """,
                (JobStatus.PENDING.value,),
            )
            rows = cursor.fetchall()
            return [TrainingJob.from_row(row) for row in rows]
        finally:
            conn.close()

    def acquire_job(self, job_id: str, worker_id: str) -> bool:
        """
        Atomically acquire a job for a worker.

        Uses optimistic locking - only acquires if job is still PENDING.

        Args:
            job_id: Job ID to acquire
            worker_id: ID of worker acquiring the job

        Returns:
            True if acquisition succeeded, False if job was already taken
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Atomic update - only updates if status is still 'pending'
            cursor.execute(
                """
                UPDATE training_jobs
                SET status = ?,
                    worker_id = ?,
                    started_at = ?
                WHERE job_id = ?
                  AND status = ?
                  AND worker_id IS NULL
                """,
                (
                    JobStatus.RUNNING.value,
                    worker_id,
                    datetime.now().isoformat(),
                    job_id,
                    JobStatus.PENDING.value,
                ),
            )
            conn.commit()

            # Check if we actually updated (rowcount = 1 means success)
            return cursor.rowcount == 1
        finally:
            conn.close()

    def acquire_next_pending(self, worker_id: str) -> TrainingJob | None:
        """
        Atomically acquire the next available pending job.

        Args:
            worker_id: ID of worker acquiring the job

        Returns:
            Acquired TrainingJob if available, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # First, find and lock a pending job atomically
            # Using a transaction with immediate locking
            conn.execute("BEGIN IMMEDIATE")

            cursor.execute(
                """
                SELECT job_id
                FROM training_jobs
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (JobStatus.PENDING.value,),
            )
            row = cursor.fetchone()

            if not row:
                conn.rollback()
                return None

            job_id = row[0]

            # Try to acquire it
            cursor.execute(
                """
                UPDATE training_jobs
                SET status = ?,
                    worker_id = ?,
                    started_at = ?
                WHERE job_id = ?
                  AND status = ?
                """,
                (
                    JobStatus.RUNNING.value,
                    worker_id,
                    datetime.now().isoformat(),
                    job_id,
                    JobStatus.PENDING.value,
                ),
            )

            if cursor.rowcount == 1:
                conn.commit()
                return self.get_job(job_id)
            else:
                conn.rollback()
                return None
        finally:
            conn.close()

    def complete_job(self, job_id: str, cycles_completed: int = 0) -> None:
        """
        Mark a job as completed successfully.

        Args:
            job_id: Job ID to complete
            cycles_completed: Number of training cycles completed
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE training_jobs
                SET status = ?,
                    completed_at = ?,
                    cycles_completed = ?
                WHERE job_id = ?
                """,
                (
                    JobStatus.COMPLETED.value,
                    datetime.now().isoformat(),
                    cycles_completed,
                    job_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def fail_job(self, job_id: str, error_message: str) -> None:
        """
        Mark a job as failed.

        Args:
            job_id: Job ID to mark as failed
            error_message: Error description
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE training_jobs
                SET status = ?,
                    completed_at = ?,
                    error_message = ?
                WHERE job_id = ?
                """,
                (
                    JobStatus.FAILED.value,
                    datetime.now().isoformat(),
                    error_message,
                    job_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def release_job(self, job_id: str) -> None:
        """
        Release a job back to pending status.

        Used when a worker crashes or job needs to be retried.

        Args:
            job_id: Job ID to release
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE training_jobs
                SET status = ?,
                    worker_id = NULL,
                    started_at = NULL
                WHERE job_id = ?
                """,
                (JobStatus.PENDING.value, job_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_running_jobs(self) -> list[TrainingJob]:
        """
        List all currently running jobs.

        Returns:
            List of running TrainingJob objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT job_id, tensor_id, status, target_maturity, worker_id,
                       started_at, completed_at, cycles_completed, error_message, created_at
                FROM training_jobs
                WHERE status = ?
                ORDER BY started_at ASC
                """,
                (JobStatus.RUNNING.value,),
            )
            rows = cursor.fetchall()
            return [TrainingJob.from_row(row) for row in rows]
        finally:
            conn.close()

    def get_jobs_for_tensor(self, tensor_id: str) -> list[TrainingJob]:
        """
        Get all jobs for a specific tensor.

        Args:
            tensor_id: Tensor ID to look up

        Returns:
            List of TrainingJob objects for the tensor
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT job_id, tensor_id, status, target_maturity, worker_id,
                       started_at, completed_at, cycles_completed, error_message, created_at
                FROM training_jobs
                WHERE tensor_id = ?
                ORDER BY created_at DESC
                """,
                (tensor_id,),
            )
            rows = cursor.fetchall()
            return [TrainingJob.from_row(row) for row in rows]
        finally:
            conn.close()

    def cleanup_stale_jobs(self, timeout_seconds: int = 300) -> int:
        """
        Release jobs that have been running too long (dead worker).

        Args:
            timeout_seconds: Jobs running longer than this are considered stale

        Returns:
            Number of jobs released
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Find and release stale running jobs
            cutoff = datetime.now().timestamp() - timeout_seconds

            cursor.execute(
                """
                UPDATE training_jobs
                SET status = ?,
                    worker_id = NULL,
                    started_at = NULL
                WHERE status = ?
                  AND datetime(started_at) < datetime(?, 'unixepoch')
                """,
                (JobStatus.PENDING.value, JobStatus.RUNNING.value, cutoff),
            )
            conn.commit()

            return cursor.rowcount
        finally:
            conn.close()
