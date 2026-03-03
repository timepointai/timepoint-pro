"""
LangGraph node for parallel tensor training.

Provides a workflow-compatible node that uses ParallelTensorTrainer
for concurrent tensor maturity training.

Phase 2: Parallel Training Infrastructure
"""

import asyncio
import base64
import json
from collections.abc import Callable
from datetime import datetime
from typing import TypedDict

from schemas import Entity, TTMTensor
from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import deserialize_tensor, serialize_tensor
from training.parallel_trainer import ParallelTensorTrainer, TrainingResult


class TrainingNodeState(TypedDict):
    """State for training node in LangGraph workflow."""

    entities: list[Entity]
    tensor_db: TensorDatabase
    target_maturity: float
    max_workers: int
    training_results: dict[str, TrainingResult]


def create_parallel_training_node(
    tensor_db: TensorDatabase,
    target_maturity: float = 0.95,
    max_workers: int = 4,
    progress_callback: Callable[[str, float, int], None] | None = None,
):
    """
    Create a LangGraph node function for parallel tensor training.

    This factory function creates a node that can be added to existing
    LangGraph workflows to enable parallel tensor training.

    Args:
        tensor_db: TensorDatabase for tensor persistence
        target_maturity: Target maturity level (0.0-1.0)
        max_workers: Maximum concurrent training workers
        progress_callback: Optional callback(tensor_id, maturity, cycles)

    Returns:
        A LangGraph-compatible node function

    Example:
        workflow = StateGraph(WorkflowState)
        training_node = create_parallel_training_node(tensor_db)
        workflow.add_node("parallel_training", training_node)
    """

    def parallel_training_node(state: dict) -> dict:
        """
        LangGraph node for parallel tensor training.

        Extracts entities from state, ensures their tensors are persisted,
        trains them concurrently, and updates the state with results.

        Args:
            state: Workflow state containing entities

        Returns:
            Updated state with training_results
        """
        entities = state.get("entities", [])

        if not entities:
            print("  No entities to train")
            state["training_results"] = {}
            return state

        # Step 1: Ensure all entities have tensors persisted to database
        tensor_ids = []
        world_id = state.get("world_id", "default")
        run_id = state.get("run_id", f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        for entity in entities:
            tensor_id = _ensure_tensor_persisted(entity, tensor_db, world_id, run_id)
            if tensor_id:
                tensor_ids.append(tensor_id)
            else:
                print(f"  Warning: Could not persist tensor for {entity.entity_id}")

        if not tensor_ids:
            print("  No tensors to train (all entities missing tensors)")
            state["training_results"] = {}
            return state

        # Step 2: Run parallel training
        print(f"  Training {len(tensor_ids)} tensors with {max_workers} workers...")

        trainer = ParallelTensorTrainer(
            tensor_db=tensor_db, max_workers=max_workers, progress_callback=progress_callback
        )

        # Run async training in event loop
        results = asyncio.run(
            trainer.train_batch(tensor_ids=tensor_ids, target_maturity=target_maturity)
        )

        # Step 3: Update entities with trained tensors
        _update_entities_from_training(entities, results, tensor_db)

        # Step 4: Store results in state
        state["training_results"] = results

        # Summary
        successful = sum(1 for r in results.values() if r.success)
        print(f"  Training complete: {successful}/{len(results)} succeeded")

        return state

    return parallel_training_node


def _ensure_tensor_persisted(
    entity: Entity, tensor_db: TensorDatabase, world_id: str, run_id: str
) -> str | None:
    """
    Ensure an entity's tensor is persisted to the database.

    If the tensor already exists in the database, returns its ID.
    Otherwise, persists the tensor and returns the new ID.

    Args:
        entity: Entity with tensor data
        tensor_db: TensorDatabase instance
        world_id: World/template identifier
        run_id: Current run identifier

    Returns:
        Tensor ID if successful, None otherwise
    """
    # Generate consistent tensor ID
    tensor_id = f"{entity.entity_id}_{world_id}_{run_id}"

    # Check if already exists
    existing = tensor_db.get_tensor(tensor_id)
    if existing:
        return tensor_id

    # Extract and persist tensor
    if not entity.tensor:
        return None

    try:
        tensor_data = json.loads(entity.tensor)
        ttm_tensor = TTMTensor(
            context_vector=base64.b64decode(tensor_data["context_vector"]),
            biology_vector=base64.b64decode(tensor_data["biology_vector"]),
            behavior_vector=base64.b64decode(tensor_data["behavior_vector"]),
        )

        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id=entity.entity_id,
            world_id=world_id,
            tensor_blob=serialize_tensor(ttm_tensor),
            maturity=getattr(entity, "tensor_maturity", 0.0),
            training_cycles=getattr(entity, "tensor_training_cycles", 0),
        )

        tensor_db.save_tensor(record)
        return tensor_id

    except Exception as e:
        print(f"  Warning: Failed to persist tensor for {entity.entity_id}: {e}")
        return None


def _update_entities_from_training(
    entities: list[Entity], results: dict[str, TrainingResult], tensor_db: TensorDatabase
) -> None:
    """
    Update entities with trained tensor data.

    After parallel training completes, this function:
    1. Loads the trained tensor from the database
    2. Updates the entity's tensor field
    3. Updates maturity and training cycle metadata

    Args:
        entities: List of entities to update
        results: Training results keyed by tensor_id
        tensor_db: TensorDatabase for loading trained tensors
    """
    for entity in entities:
        # Find matching result (tensor_id contains entity_id)
        matching_result = None
        matching_tensor_id = None

        for tensor_id, result in results.items():
            if tensor_id.startswith(f"{entity.entity_id}_"):
                matching_result = result
                matching_tensor_id = tensor_id
                break

        if not matching_result:
            continue

        if not matching_result.success:
            print(f"  Skipping {entity.entity_id}: training failed ({matching_result.error})")
            continue

        # Load trained tensor from database
        record = tensor_db.get_tensor(matching_tensor_id)
        if not record:
            continue

        # Deserialize and update entity
        try:
            trained_tensor = deserialize_tensor(record.tensor_blob)

            entity.tensor = json.dumps(
                {
                    "context_vector": base64.b64encode(trained_tensor.context_vector).decode(
                        "utf-8"
                    ),
                    "biology_vector": base64.b64encode(trained_tensor.biology_vector).decode(
                        "utf-8"
                    ),
                    "behavior_vector": base64.b64encode(trained_tensor.behavior_vector).decode(
                        "utf-8"
                    ),
                }
            )

            # Update maturity metadata
            entity.tensor_maturity = matching_result.final_maturity
            entity.tensor_training_cycles = matching_result.cycles_completed

            # Mark as trained in metadata
            if not hasattr(entity, "entity_metadata") or entity.entity_metadata is None:
                entity.entity_metadata = {}
            entity.entity_metadata["needs_training"] = False
            entity.entity_metadata["training_completed_at"] = datetime.now().isoformat()
            entity.entity_metadata["training_duration_seconds"] = matching_result.duration_seconds

        except Exception as e:
            print(f"  Warning: Failed to update entity {entity.entity_id}: {e}")


def extend_workflow_with_training(
    workflow,
    tensor_db: TensorDatabase,
    after_node: str = "compress_tensors",
    before_node: str = "progressive_training_check",
    target_maturity: float = 0.95,
    max_workers: int = 4,
):
    """
    Extend an existing LangGraph workflow with parallel training.

    This utility function adds a parallel training node to an existing
    entity training workflow, inserting it between specified nodes.

    Args:
        workflow: LangGraph StateGraph to extend
        tensor_db: TensorDatabase for tensor persistence
        after_node: Node name to insert after
        before_node: Node name to insert before
        target_maturity: Target maturity level
        max_workers: Maximum concurrent workers

    Returns:
        Modified workflow with parallel training node

    Example:
        workflow = StateGraph(WorkflowState)
        # ... add existing nodes ...
        extend_workflow_with_training(workflow, tensor_db)
        compiled = workflow.compile()
    """
    # Create the training node
    training_node = create_parallel_training_node(
        tensor_db=tensor_db, target_maturity=target_maturity, max_workers=max_workers
    )

    # Add node
    workflow.add_node("parallel_tensor_training", training_node)

    # Rewire edges
    # Note: This requires the workflow to not be compiled yet
    # The caller is responsible for edge management if the workflow
    # has custom edge configuration

    return workflow


async def train_entities_async(
    entities: list[Entity],
    tensor_db: TensorDatabase,
    world_id: str = "default",
    run_id: str | None = None,
    target_maturity: float = 0.95,
    max_workers: int = 4,
    progress_callback: Callable[[str, float, int], None] | None = None,
) -> dict[str, TrainingResult]:
    """
    Convenience function to train entity tensors asynchronously.

    This is a standalone function for training entities outside of
    a LangGraph workflow context.

    Args:
        entities: List of entities to train
        tensor_db: TensorDatabase for persistence
        world_id: World/template identifier
        run_id: Run identifier (generated if not provided)
        target_maturity: Target maturity level
        max_workers: Maximum concurrent workers
        progress_callback: Optional progress callback

    Returns:
        Dict mapping tensor_id to TrainingResult

    Example:
        results = await train_entities_async(
            entities=my_entities,
            tensor_db=tensor_db,
            target_maturity=0.95
        )
    """
    if run_id is None:
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Persist all tensors
    tensor_ids = []
    for entity in entities:
        tensor_id = _ensure_tensor_persisted(entity, tensor_db, world_id, run_id)
        if tensor_id:
            tensor_ids.append(tensor_id)

    if not tensor_ids:
        return {}

    # Create trainer and run
    trainer = ParallelTensorTrainer(
        tensor_db=tensor_db, max_workers=max_workers, progress_callback=progress_callback
    )

    results = await trainer.train_batch(tensor_ids=tensor_ids, target_maturity=target_maturity)

    # Update entities
    _update_entities_from_training(entities, results, tensor_db)

    return results
