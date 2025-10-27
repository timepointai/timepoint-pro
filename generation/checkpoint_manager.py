"""
Checkpoint Management for Long-Running Generation Jobs

Provides automatic checkpoint creation, resume functionality, and
checkpoint cleanup for fault-tolerant generation.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import json
import hashlib
import logging
import fcntl
import tempfile
import os


logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manage checkpoints for generation jobs to enable resume on failure.

    Example:
        manager = CheckpointManager(
            checkpoint_dir="./checkpoints",
            auto_save_interval=10  # Save every 10 items
        )

        # Start job
        manager.create_checkpoint(job_id="job_123", metadata={...})

        # During generation
        for i in range(100):
            generate_entity(i)
            manager.update_progress(job_id="job_123", items_completed=i+1)

            # Auto-saves every 10 items
            if manager.should_save_checkpoint(job_id="job_123"):
                manager.save_checkpoint(job_id="job_123", state={...})

        # On failure/restart
        if manager.has_checkpoint(job_id="job_123"):
            state = manager.load_checkpoint(job_id="job_123")
            resume_from = state["items_completed"]
    """

    def __init__(
        self,
        checkpoint_dir: str = "./checkpoints",
        auto_save_interval: int = 10,
        max_checkpoints_per_job: int = 5,
        enable_compression: bool = False
    ):
        """
        Args:
            checkpoint_dir: Directory to store checkpoints
            auto_save_interval: Save checkpoint every N items
            max_checkpoints_per_job: Maximum checkpoints to keep per job (oldest deleted)
            enable_compression: Whether to compress checkpoints (not implemented yet)
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.auto_save_interval = auto_save_interval
        self.max_checkpoints_per_job = max_checkpoints_per_job
        self.enable_compression = enable_compression

        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Track checkpoint metadata
        self._checkpoint_metadata: Dict[str, Dict[str, Any]] = {}

    def _get_checkpoint_path(self, job_id: str, checkpoint_index: int = 0) -> Path:
        """Get path for checkpoint file"""
        filename = f"{job_id}_checkpoint_{checkpoint_index}.json"
        return self.checkpoint_dir / filename

    def _get_metadata_path(self, job_id: str) -> Path:
        """Get path for checkpoint metadata file"""
        return self.checkpoint_dir / f"{job_id}_metadata.json"

    def create_checkpoint(
        self,
        job_id: str,
        metadata: Dict[str, Any]
    ):
        """
        Create initial checkpoint for a job.

        Args:
            job_id: Unique job identifier
            metadata: Job metadata (config, random seed, etc.)
        """
        checkpoint_metadata = {
            "job_id": job_id,
            "created_at": datetime.utcnow().isoformat(),
            "items_completed": 0,
            "checkpoint_count": 0,
            "last_checkpoint_at": None,
            "metadata": metadata
        }

        self._checkpoint_metadata[job_id] = checkpoint_metadata

        # Save metadata to disk
        with open(self._get_metadata_path(job_id), 'w') as f:
            json.dump(checkpoint_metadata, f, indent=2)

        logger.info(f"Created checkpoint for job {job_id}")

    def has_checkpoint(self, job_id: str) -> bool:
        """Check if checkpoint exists for job"""
        return self._get_metadata_path(job_id).exists()

    def should_save_checkpoint(self, job_id: str) -> bool:
        """
        Check if it's time to save a checkpoint.

        Args:
            job_id: Job identifier

        Returns:
            True if checkpoint should be saved based on auto_save_interval
        """
        if job_id not in self._checkpoint_metadata:
            return False

        metadata = self._checkpoint_metadata[job_id]
        items_completed = metadata.get("items_completed", 0)

        # Save on interval
        return items_completed % self.auto_save_interval == 0

    def save_checkpoint(
        self,
        job_id: str,
        state: Dict[str, Any]
    ):
        """
        Save checkpoint state to disk with atomic writes and locking.

        Uses temporary file + rename for atomicity.
        Uses file locking to prevent concurrent writes.

        Args:
            job_id: Job identifier
            state: Current generation state (progress, entities generated, etc.)
        """
        if job_id not in self._checkpoint_metadata:
            raise ValueError(f"No checkpoint metadata for job {job_id}. Call create_checkpoint first.")

        metadata = self._checkpoint_metadata[job_id]
        checkpoint_index = metadata["checkpoint_count"]

        checkpoint_data = {
            "job_id": job_id,
            "checkpoint_index": checkpoint_index,
            "saved_at": datetime.utcnow().isoformat(),
            "items_completed": metadata.get("items_completed", 0),
            "state": state,
            "metadata": metadata["metadata"]
        }

        # ATOMIC WRITE: Write to temp file, then rename
        checkpoint_path = self._get_checkpoint_path(job_id, checkpoint_index)

        # Create temp file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=checkpoint_path.parent,
            prefix=f".{checkpoint_path.name}.",
            suffix=".tmp"
        )

        try:
            # Write to temp file with exclusive lock
            with os.fdopen(temp_fd, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(checkpoint_data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename (POSIX guarantees atomicity)
            os.rename(temp_path, checkpoint_path)

        except Exception as e:
            # Cleanup temp file on error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise RuntimeError(f"Failed to save checkpoint: {e}") from e

        # Update metadata (also atomic)
        metadata["checkpoint_count"] += 1
        metadata["last_checkpoint_at"] = checkpoint_data["saved_at"]

        metadata_path = self._get_metadata_path(job_id)
        temp_metadata_fd, temp_metadata_path = tempfile.mkstemp(
            dir=metadata_path.parent,
            prefix=f".{metadata_path.name}.",
            suffix=".tmp"
        )

        try:
            with os.fdopen(temp_metadata_fd, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(metadata, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            os.rename(temp_metadata_path, metadata_path)

        except Exception as e:
            try:
                os.unlink(temp_metadata_path)
            except:
                pass
            logger.warning(f"Failed to update metadata: {e}")

        # Cleanup old checkpoints
        self._cleanup_old_checkpoints(job_id)

        logger.info(
            f"Saved checkpoint {checkpoint_index} for job {job_id} "
            f"({metadata['items_completed']} items completed)"
        )

    def load_checkpoint(self, job_id: str) -> Dict[str, Any]:
        """
        Load most recent checkpoint for job.

        Args:
            job_id: Job identifier

        Returns:
            Checkpoint data including state and metadata

        Raises:
            ValueError: If no checkpoint exists
        """
        if not self.has_checkpoint(job_id):
            raise ValueError(f"No checkpoint found for job {job_id}")

        # Load metadata to find latest checkpoint
        with open(self._get_metadata_path(job_id), 'r') as f:
            metadata = json.load(f)

        # Get latest checkpoint index
        latest_index = metadata["checkpoint_count"] - 1
        if latest_index < 0:
            raise ValueError(f"No checkpoints saved for job {job_id}")

        # Load latest checkpoint
        checkpoint_path = self._get_checkpoint_path(job_id, latest_index)
        if not checkpoint_path.exists():
            raise ValueError(f"Checkpoint file not found: {checkpoint_path}")

        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)

        logger.info(
            f"Loaded checkpoint {latest_index} for job {job_id} "
            f"({checkpoint_data['items_completed']} items completed)"
        )

        return checkpoint_data

    def update_progress(self, job_id: str, items_completed: int):
        """
        Update progress counter for job.

        Args:
            job_id: Job identifier
            items_completed: Number of items completed
        """
        if job_id not in self._checkpoint_metadata:
            raise ValueError(f"No checkpoint metadata for job {job_id}")

        self._checkpoint_metadata[job_id]["items_completed"] = items_completed

    def delete_checkpoint(self, job_id: str):
        """
        Delete all checkpoints for a job.

        Args:
            job_id: Job identifier
        """
        # Delete metadata
        metadata_path = self._get_metadata_path(job_id)
        if metadata_path.exists():
            metadata_path.unlink()

        # Delete all checkpoint files
        for checkpoint_file in self.checkpoint_dir.glob(f"{job_id}_checkpoint_*.json"):
            checkpoint_file.unlink()

        # Remove from memory
        if job_id in self._checkpoint_metadata:
            del self._checkpoint_metadata[job_id]

        logger.info(f"Deleted all checkpoints for job {job_id}")

    def _cleanup_old_checkpoints(self, job_id: str):
        """
        Delete old checkpoints beyond max_checkpoints_per_job.

        Args:
            job_id: Job identifier
        """
        if job_id not in self._checkpoint_metadata:
            return

        metadata = self._checkpoint_metadata[job_id]
        checkpoint_count = metadata["checkpoint_count"]

        if checkpoint_count <= self.max_checkpoints_per_job:
            return

        # Delete oldest checkpoints
        checkpoints_to_delete = checkpoint_count - self.max_checkpoints_per_job
        for i in range(checkpoints_to_delete):
            checkpoint_path = self._get_checkpoint_path(job_id, i)
            if checkpoint_path.exists():
                checkpoint_path.unlink()
                logger.debug(f"Deleted old checkpoint {i} for job {job_id}")

    def list_checkpoints(self, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.

        Args:
            job_id: Optional job ID to filter by

        Returns:
            List of checkpoint metadata
        """
        checkpoints = []

        if job_id:
            # List checkpoints for specific job
            if self.has_checkpoint(job_id):
                with open(self._get_metadata_path(job_id), 'r') as f:
                    metadata = json.load(f)
                checkpoints.append(metadata)
        else:
            # List all checkpoints
            for metadata_file in self.checkpoint_dir.glob("*_metadata.json"):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                checkpoints.append(metadata)

        return checkpoints

    def verify_checkpoint_integrity(self, job_id: str) -> Dict[str, Any]:
        """
        Verify checkpoint integrity (detect corruption).

        Args:
            job_id: Job identifier

        Returns:
            Dictionary with verification results:
                - is_valid: bool
                - errors: List[str]
                - checkpoint_count: int
        """
        if not self.has_checkpoint(job_id):
            return {
                "is_valid": False,
                "errors": ["No checkpoint found"],
                "checkpoint_count": 0
            }

        errors = []

        try:
            # Load metadata
            with open(self._get_metadata_path(job_id), 'r') as f:
                metadata = json.load(f)

            checkpoint_count = metadata.get("checkpoint_count", 0)

            # Verify each checkpoint file exists and is valid JSON
            for i in range(checkpoint_count):
                checkpoint_path = self._get_checkpoint_path(job_id, i)

                # Skip if deleted by cleanup
                if i < checkpoint_count - self.max_checkpoints_per_job:
                    continue

                if not checkpoint_path.exists():
                    errors.append(f"Checkpoint file {i} missing")
                    continue

                try:
                    with open(checkpoint_path, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    errors.append(f"Checkpoint file {i} corrupted: {e}")

        except Exception as e:
            errors.append(f"Failed to verify checkpoint: {e}")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "checkpoint_count": checkpoint_count
        }

    def get_checkpoint_metadata(self, job_id: str) -> Dict[str, Any]:
        """
        Get checkpoint metadata for a job.

        Args:
            job_id: Job identifier

        Returns:
            Checkpoint metadata

        Raises:
            ValueError: If no checkpoint exists
        """
        if not self.has_checkpoint(job_id):
            raise ValueError(f"No checkpoint found for job {job_id}")

        with open(self._get_metadata_path(job_id), 'r') as f:
            return json.load(f)
