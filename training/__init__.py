"""
Training package for Timepoint-Pro tensor training.

Phase 2: Parallel Training Infrastructure

This package provides:
- ParallelTensorTrainer: Asyncio-based parallel tensor training
- JobQueue: SQLite-backed job queue with atomic locking
- Training utilities for maturity convergence
- LangGraph integration for workflow-based training

Usage:
    from training import ParallelTensorTrainer, JobQueue

    trainer = ParallelTensorTrainer(tensor_db, max_workers=4)
    results = await trainer.train_batch(tensors, target_maturity=0.95)

    # LangGraph workflow integration
    from training import create_parallel_training_node
    training_node = create_parallel_training_node(tensor_db)
    workflow.add_node("parallel_training", training_node)
"""

from training.job_queue import JobQueue, TrainingJob, JobStatus
from training.parallel_trainer import ParallelTensorTrainer, TrainingResult
from training.training_node import (
    create_parallel_training_node,
    extend_workflow_with_training,
    train_entities_async,
    TrainingNodeState,
)

__all__ = [
    # Job Queue
    "JobQueue",
    "TrainingJob",
    "JobStatus",
    # Parallel Trainer
    "ParallelTensorTrainer",
    "TrainingResult",
    # LangGraph Integration
    "create_parallel_training_node",
    "extend_workflow_with_training",
    "train_entities_async",
    "TrainingNodeState",
]
