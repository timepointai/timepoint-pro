"""
Parallel tensor refinement using asyncio workers.

Refines multiple tensors concurrently with collision-free
job acquisition through the JobQueue.

Tensor refinement applies stochastic perturbation to explore
the state space. This is NOT gradient-based training — there is
no loss function or backpropagation. Maturity tracks how many
refinement cycles a tensor has undergone, not optimization convergence.

Phase 2: Parallel Refinement Infrastructure
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from datetime import datetime

import numpy as np

from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import serialize_tensor, deserialize_tensor
from schemas import TTMTensor
from training.job_queue import JobQueue, TrainingJob, JobStatus


@dataclass
class TrainingResult:
    """
    Result of training a single tensor.

    Attributes:
        tensor_id: ID of trained tensor
        success: Whether training succeeded
        final_maturity: Final maturity level achieved
        cycles_completed: Number of training cycles performed
        error: Error message if training failed
        duration_seconds: How long training took
    """
    tensor_id: str
    success: bool
    final_maturity: float = 0.0
    cycles_completed: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


class ParallelTensorTrainer:
    """
    Refines multiple tensors concurrently using asyncio workers.

    Applies stochastic perturbation to tensor state vectors to explore
    the representation space. This is state-space exploration, not
    gradient-based optimization — there is no loss function.

    Features:
    - Configurable worker pool size
    - Collision-free job acquisition via JobQueue
    - Progress callbacks for monitoring
    - Maturity tracking (cycle count, not convergence)

    Example:
        trainer = ParallelTensorTrainer(tensor_db, max_workers=4)
        results = await trainer.train_batch(
            tensor_ids=["t1", "t2", "t3"],
            target_maturity=0.95
        )
    """

    def __init__(
        self,
        tensor_db: TensorDatabase,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[str, float, int], None]] = None
    ):
        """
        Initialize parallel trainer.

        Args:
            tensor_db: TensorDatabase for reading/writing tensors
            max_workers: Maximum number of concurrent training workers
            progress_callback: Optional callback(tensor_id, maturity, cycles)
        """
        self.tensor_db = tensor_db
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self._job_queue = JobQueue(tensor_db)
        self._active_workers: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, TrainingResult] = {}

    async def train_batch(
        self,
        tensor_ids: List[str],
        target_maturity: float = 0.95,
        max_cycles: int = 1000
    ) -> Dict[str, TrainingResult]:
        """
        Train a batch of tensors in parallel.

        Creates training jobs for each tensor and spawns workers
        to process them concurrently.

        Args:
            tensor_ids: List of tensor IDs to train
            target_maturity: Target maturity level (0.0-1.0)
            max_cycles: Maximum training cycles per tensor

        Returns:
            Dict mapping tensor_id to TrainingResult
        """
        self._results = {}

        # Create jobs for each tensor
        jobs = []
        for tensor_id in tensor_ids:
            job = self._job_queue.create_job(
                tensor_id=tensor_id,
                target_maturity=target_maturity
            )
            jobs.append(job)

        # Calculate number of workers to spawn
        num_workers = min(self.max_workers, len(jobs))

        # Spawn workers
        worker_tasks = []
        for i in range(num_workers):
            worker_id = f"worker-{uuid.uuid4().hex[:8]}"
            task = asyncio.create_task(
                self._worker_loop(
                    worker_id=worker_id,
                    target_maturity=target_maturity,
                    max_cycles=max_cycles
                )
            )
            self._active_workers[worker_id] = task
            worker_tasks.append(task)

        # Wait for all workers to complete
        await asyncio.gather(*worker_tasks, return_exceptions=True)

        # Clean up
        self._active_workers.clear()

        # Ensure we have results for all requested tensors
        for tensor_id in tensor_ids:
            if tensor_id not in self._results:
                # Check if tensor was found but had error
                self._results[tensor_id] = TrainingResult(
                    tensor_id=tensor_id,
                    success=False,
                    error="Training not completed"
                )

        return self._results

    async def _worker_loop(
        self,
        worker_id: str,
        target_maturity: float,
        max_cycles: int
    ) -> None:
        """
        Worker loop that acquires and processes jobs.

        Runs until no more pending jobs are available.

        Args:
            worker_id: Unique identifier for this worker
            target_maturity: Target maturity for training
            max_cycles: Maximum cycles per tensor
        """
        while True:
            # Try to acquire next pending job
            job = self._job_queue.acquire_next_pending(worker_id)

            if job is None:
                # No more pending jobs
                break

            try:
                # Train the tensor
                result = await self._train_tensor(
                    tensor_id=job.tensor_id,
                    target_maturity=target_maturity,
                    worker_id=worker_id,
                    max_cycles=max_cycles
                )

                # Record result
                self._results[job.tensor_id] = result

                # Update job status
                if result.success:
                    self._job_queue.complete_job(
                        job.job_id,
                        cycles_completed=result.cycles_completed
                    )
                else:
                    self._job_queue.fail_job(job.job_id, result.error or "Unknown error")

            except Exception as e:
                # Record failure
                self._results[job.tensor_id] = TrainingResult(
                    tensor_id=job.tensor_id,
                    success=False,
                    error=str(e)
                )
                self._job_queue.fail_job(job.job_id, str(e))

    async def _train_tensor(
        self,
        tensor_id: str,
        target_maturity: float,
        worker_id: str,
        max_cycles: int = 1000
    ) -> TrainingResult:
        """
        Train a single tensor to target maturity.

        Args:
            tensor_id: ID of tensor to train
            target_maturity: Target maturity level
            worker_id: ID of worker doing the training
            max_cycles: Maximum training cycles

        Returns:
            TrainingResult with final status
        """
        start_time = datetime.now()

        # Load tensor record
        record = self.tensor_db.get_tensor(tensor_id)
        if record is None:
            return TrainingResult(
                tensor_id=tensor_id,
                success=False,
                error="Tensor not found"
            )

        # Deserialize tensor
        try:
            tensor = deserialize_tensor(record.tensor_blob)
        except Exception as e:
            return TrainingResult(
                tensor_id=tensor_id,
                success=False,
                error=f"Failed to deserialize tensor: {e}"
            )

        # Training loop
        current_maturity = record.maturity
        cycles = 0

        while current_maturity < target_maturity and cycles < max_cycles:
            # Stochastic perturbation step (state-space exploration, not gradient-based)
            tensor = await self._refinement_step(tensor)

            cycles += 1
            # Maturity increases with diminishing returns
            maturity_gain = 0.05 * (1.0 - current_maturity)
            current_maturity = min(1.0, current_maturity + maturity_gain)

            # Report progress
            if self.progress_callback and cycles % 10 == 0:
                self.progress_callback(tensor_id, current_maturity, cycles)

            # Yield to other tasks periodically
            if cycles % 5 == 0:
                await asyncio.sleep(0)

        # Save updated tensor
        record.tensor_blob = serialize_tensor(tensor)
        record.maturity = current_maturity
        record.training_cycles += cycles

        self.tensor_db.save_tensor(record)

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        return TrainingResult(
            tensor_id=tensor_id,
            success=True,
            final_maturity=current_maturity,
            cycles_completed=cycles,
            duration_seconds=duration
        )

    async def _refinement_step(self, tensor: TTMTensor) -> TTMTensor:
        """
        Apply a single stochastic perturbation to a tensor.

        This is state-space exploration via random noise injection,
        NOT gradient-based training. There is no loss function,
        no backpropagation, and no optimization objective.

        Maturity tracks cycle count, not convergence to an optimum.

        Args:
            tensor: TTMTensor to perturb

        Returns:
            Perturbed TTMTensor
        """
        # Extract current values
        context, biology, behavior = tensor.to_arrays()

        # Apply small random perturbations (stochastic exploration)
        noise_scale = 0.01
        context = context + np.random.normal(0, noise_scale, context.shape)
        biology = biology + np.random.normal(0, noise_scale, biology.shape)
        behavior = behavior + np.random.normal(0, noise_scale, behavior.shape)

        # Clamp to valid range [0, 1]
        context = np.clip(context, 0, 1)
        biology = np.clip(biology, 0, 1)
        behavior = np.clip(behavior, 0, 1)

        return TTMTensor.from_arrays(context, biology, behavior)

    def get_active_jobs(self) -> List[TrainingJob]:
        """
        Get list of currently running training jobs.

        Returns:
            List of active TrainingJob objects
        """
        return self._job_queue.list_running_jobs()

    def cancel_all(self) -> None:
        """
        Cancel all active workers.

        Workers will stop after completing their current job.
        """
        for worker_id, task in self._active_workers.items():
            task.cancel()
        self._active_workers.clear()


async def train_tensors_parallel(
    tensor_db: TensorDatabase,
    tensor_ids: List[str],
    target_maturity: float = 0.95,
    max_workers: int = 4,
    progress_callback: Optional[Callable[[str, float, int], None]] = None
) -> Dict[str, TrainingResult]:
    """
    Convenience function to train multiple tensors in parallel.

    Args:
        tensor_db: TensorDatabase instance
        tensor_ids: List of tensor IDs to train
        target_maturity: Target maturity level
        max_workers: Maximum concurrent workers
        progress_callback: Optional progress callback

    Returns:
        Dict mapping tensor_id to TrainingResult
    """
    trainer = ParallelTensorTrainer(
        tensor_db=tensor_db,
        max_workers=max_workers,
        progress_callback=progress_callback
    )

    return await trainer.train_batch(
        tensor_ids=tensor_ids,
        target_maturity=target_maturity
    )
