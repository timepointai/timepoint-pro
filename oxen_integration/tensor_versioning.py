"""
Tensor version control with Oxen AI.

Provides version control for tensor templates and instances,
including branching, syncing, and conflict resolution.

Phase 4: Oxen Integration
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from .client import OxenClient
from .parquet_schemas import (
    write_templates_parquet,
    write_instances_parquet,
    read_templates_parquet,
    read_instances_parquet,
    tensor_record_to_parquet_row,
)
from .exceptions import RepositoryError


@dataclass
class SyncResult:
    """Result of a sync operation."""
    synced_count: int
    version: Optional[str] = None
    errors: List[str] = None
    conflicts: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.conflicts is None:
            self.conflicts = []


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    fetched_count: int
    version: Optional[str] = None
    new_templates: List[str] = None
    new_instances: List[str] = None

    def __post_init__(self):
        if self.new_templates is None:
            self.new_templates = []
        if self.new_instances is None:
            self.new_instances = []


class TensorVersionController:
    """
    Manages tensor versioning with Oxen AI.

    Provides:
    - Publishing templates to Oxen
    - Syncing local tensors to/from remote
    - Branch management for experiments
    - Conflict detection and resolution

    Example:
        controller = TensorVersionController(oxen_client)
        controller.publish_template(template_record)
        result = controller.sync_local_to_remote(tensor_db)
    """

    def __init__(
        self,
        oxen_client: OxenClient,
        repo_name: str = "tensor-store",
        local_cache_dir: Optional[str] = None
    ):
        """
        Initialize TensorVersionController.

        Args:
            oxen_client: Configured OxenClient
            repo_name: Name of the tensor repository
            local_cache_dir: Local directory for caching Parquet files
        """
        self.client = oxen_client
        self.repo_name = repo_name
        self.local_cache_dir = Path(local_cache_dir) if local_cache_dir else Path("metadata/tensor_cache")
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)

        # Track sync state
        self._last_sync_version: Optional[str] = None

    # ========================================================================
    # Template Publishing
    # ========================================================================

    def publish_template(
        self,
        record: Any,  # TensorRecord
        branch: str = "main",
        commit_message: Optional[str] = None
    ) -> str:
        """
        Publish a tensor template to Oxen.

        Args:
            record: TensorRecord to publish as template
            branch: Branch to publish to
            commit_message: Optional commit message

        Returns:
            Commit hash
        """
        if not record.category:
            raise ValueError("Template must have a category")

        # Determine path based on category
        category_path = record.category.replace("/", "_")
        filename = f"{category_path}_{record.tensor_id}.parquet"
        local_path = self.local_cache_dir / "templates" / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to local Parquet
        write_templates_parquet([record], str(local_path))

        # Upload to Oxen
        dst_path = f"templates/{record.category}/{filename}"
        message = commit_message or f"Add template: {record.tensor_id}"

        try:
            result = self.client.upload_dataset(
                file_path=str(local_path),
                commit_message=message,
                dst_path=dst_path,
                create_repo_if_missing=True
            )
            return result.commit_id
        except Exception as e:
            raise RepositoryError(f"Failed to publish template: {e}")

    def publish_templates_batch(
        self,
        records: List[Any],
        branch: str = "main",
        commit_message: Optional[str] = None
    ) -> str:
        """
        Publish multiple templates in a single commit.

        Args:
            records: List of TensorRecord objects
            branch: Branch to publish to
            commit_message: Optional commit message

        Returns:
            Commit hash
        """
        if not records:
            raise ValueError("No records to publish")

        # Group by category
        by_category: Dict[str, List[Any]] = {}
        for record in records:
            category = record.category or "uncategorized"
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(record)

        # Write each category to a separate file
        local_files = []
        for category, cat_records in by_category.items():
            category_path = category.replace("/", "_")
            filename = f"{category_path}_batch_{uuid.uuid4().hex[:8]}.parquet"
            local_path = self.local_cache_dir / "templates" / filename
            local_path.parent.mkdir(parents=True, exist_ok=True)

            write_templates_parquet(cat_records, str(local_path))
            local_files.append((local_path, f"templates/{category}/{filename}"))

        # Upload all files
        message = commit_message or f"Add {len(records)} templates"
        last_commit = None

        for local_path, dst_path in local_files:
            try:
                result = self.client.upload_dataset(
                    file_path=str(local_path),
                    commit_message=message,
                    dst_path=dst_path,
                    create_repo_if_missing=True
                )
                last_commit = result.commit_id
            except Exception as e:
                raise RepositoryError(f"Failed to publish templates: {e}")

        return last_commit

    # ========================================================================
    # Sync Operations
    # ========================================================================

    def sync_local_to_remote(
        self,
        tensor_db: Any,  # TensorDatabase
        since_version: Optional[str] = None,
        include_templates: bool = True,
        include_instances: bool = True,
        min_maturity: float = 0.0
    ) -> SyncResult:
        """
        Sync local tensors to Oxen remote.

        Args:
            tensor_db: Local TensorDatabase
            since_version: Only sync changes since this version
            include_templates: Whether to sync templates
            include_instances: Whether to sync instances
            min_maturity: Minimum maturity for sync

        Returns:
            SyncResult with sync statistics
        """
        synced = 0
        errors = []

        # Get tensors from database
        all_tensors = tensor_db.list_tensors()

        # Filter by maturity
        tensors_to_sync = [t for t in all_tensors if t.maturity >= min_maturity]

        # Separate templates and instances
        # (Templates have category set, instances are bound to entities)
        templates = []
        instances = []

        for record in tensors_to_sync:
            if record.category and include_templates:
                templates.append(record)
            elif record.entity_id and include_instances:
                instances.append(record)

        # Sync templates
        if templates:
            try:
                # Write to single batch file
                batch_file = self.local_cache_dir / f"sync_templates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
                write_templates_parquet(templates, str(batch_file))

                result = self.client.upload_dataset(
                    file_path=str(batch_file),
                    commit_message=f"Sync {len(templates)} templates from local",
                    dst_path=f"templates/sync/{batch_file.name}",
                    create_repo_if_missing=True
                )
                synced += len(templates)
                self._last_sync_version = result.commit_id

            except Exception as e:
                errors.append(f"Template sync failed: {e}")

        # Sync instances
        if instances:
            try:
                batch_file = self.local_cache_dir / f"sync_instances_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
                write_instances_parquet(instances, str(batch_file))

                result = self.client.upload_dataset(
                    file_path=str(batch_file),
                    commit_message=f"Sync {len(instances)} instances from local",
                    dst_path=f"instances/sync/{batch_file.name}",
                    create_repo_if_missing=True
                )
                synced += len(instances)
                self._last_sync_version = result.commit_id

            except Exception as e:
                errors.append(f"Instance sync failed: {e}")

        return SyncResult(
            synced_count=synced,
            version=self._last_sync_version,
            errors=errors
        )

    def fetch_remote_updates(
        self,
        tensor_db: Any,  # TensorDatabase
        branch: str = "main"
    ) -> FetchResult:
        """
        Fetch new tensors from Oxen remote.

        Args:
            tensor_db: Local TensorDatabase to update
            branch: Branch to fetch from

        Returns:
            FetchResult with fetch statistics
        """
        fetched = 0
        new_templates = []
        new_instances = []

        # TODO: Implement proper diff-based fetching
        # For now, this is a placeholder that would:
        # 1. Get list of files from remote
        # 2. Download new/updated Parquet files
        # 3. Parse and import into local database

        # This would use the Oxen API to:
        # - List files in templates/ and instances/ directories
        # - Download files not present locally
        # - Merge into tensor_db

        return FetchResult(
            fetched_count=fetched,
            version=self._last_sync_version,
            new_templates=new_templates,
            new_instances=new_instances
        )

    # ========================================================================
    # Branch Management
    # ========================================================================

    def create_experiment_branch(
        self,
        name: str,
        description: str,
        from_branch: str = "main"
    ) -> str:
        """
        Create an experiment branch for tensor training experiments.

        Args:
            name: Experiment name (will be prefixed with "experiments/")
            description: Description of the experiment
            from_branch: Branch to create from

        Returns:
            Full branch name
        """
        branch_name = f"experiments/{name}"

        try:
            self.client.create_branch(branch_name, from_branch)

            # Add experiment metadata
            # TODO: Store experiment metadata in Oxen
            return branch_name

        except Exception as e:
            raise RepositoryError(f"Failed to create experiment branch: {e}")

    def create_training_branch(
        self,
        batch_id: str,
        from_branch: str = "main"
    ) -> str:
        """
        Create a branch for a training batch.

        Args:
            batch_id: Unique batch identifier
            from_branch: Branch to create from

        Returns:
            Full branch name
        """
        branch_name = f"training/{batch_id}"

        try:
            self.client.create_branch(branch_name, from_branch)
            return branch_name
        except Exception as e:
            raise RepositoryError(f"Failed to create training branch: {e}")

    def merge_training_results(
        self,
        training_branch: str,
        target_branch: str = "main",
        require_maturity: float = 0.95
    ) -> str:
        """
        Merge training results back to main branch.

        Only merges tensors that meet the maturity threshold.

        Args:
            training_branch: Branch with training results
            target_branch: Branch to merge into
            require_maturity: Minimum maturity for merge

        Returns:
            Merge commit hash
        """
        try:
            commit_id = self.client.merge_branch(
                source_branch=training_branch,
                target_branch=target_branch,
                message=f"Merge training results from {training_branch}"
            )
            return commit_id
        except Exception as e:
            raise RepositoryError(f"Failed to merge training results: {e}")

    # ========================================================================
    # Conflict Resolution
    # ========================================================================

    def detect_conflicts(
        self,
        local_records: List[Any],
        remote_records: List[Any]
    ) -> List[Tuple[Any, Any]]:
        """
        Detect conflicts between local and remote tensors.

        A conflict occurs when both have been modified since last sync.

        Args:
            local_records: Local TensorRecord objects
            remote_records: Remote TensorRecord objects

        Returns:
            List of (local, remote) conflict pairs
        """
        conflicts = []

        # Build lookup by tensor_id
        local_by_id = {r.tensor_id: r for r in local_records}
        remote_by_id = {r.tensor_id: r for r in remote_records}

        # Find overlapping IDs
        common_ids = set(local_by_id.keys()) & set(remote_by_id.keys())

        for tensor_id in common_ids:
            local = local_by_id[tensor_id]
            remote = remote_by_id[tensor_id]

            # Conflict if versions differ and both have been updated
            if local.version != remote.version:
                # Check if both were modified after last sync
                # (Would need to track last sync time per tensor)
                conflicts.append((local, remote))

        return conflicts

    def resolve_conflict(
        self,
        local: Any,  # TensorRecord
        remote: Any,  # TensorRecord
        strategy: str = "highest_maturity"
    ) -> Any:
        """
        Resolve a conflict between local and remote tensors.

        Strategies:
        - "highest_maturity": Keep tensor with higher maturity
        - "latest": Keep most recently updated
        - "local": Always prefer local
        - "remote": Always prefer remote
        - "merge": Average tensor values

        Args:
            local: Local TensorRecord
            remote: Remote TensorRecord
            strategy: Resolution strategy

        Returns:
            Resolved TensorRecord
        """
        from tensor_serialization import serialize_tensor, deserialize_tensor
        from schemas import TTMTensor
        import numpy as np

        if strategy == "highest_maturity":
            return local if local.maturity >= remote.maturity else remote

        elif strategy == "latest":
            local_time = local.updated_at or datetime.min
            remote_time = remote.updated_at or datetime.min
            return local if local_time >= remote_time else remote

        elif strategy == "local":
            return local

        elif strategy == "remote":
            return remote

        elif strategy == "merge":
            # Average the tensor values
            local_tensor = deserialize_tensor(local.tensor_blob)
            remote_tensor = deserialize_tensor(remote.tensor_blob)

            local_ctx, local_bio, local_beh = local_tensor.to_arrays()
            remote_ctx, remote_bio, remote_beh = remote_tensor.to_arrays()

            merged_ctx = (local_ctx + remote_ctx) / 2
            merged_bio = (local_bio + remote_bio) / 2
            merged_beh = (local_beh + remote_beh) / 2

            merged_tensor = TTMTensor.from_arrays(
                np.array(merged_ctx, dtype=np.float32),
                np.array(merged_bio, dtype=np.float32),
                np.array(merged_beh, dtype=np.float32)
            )

            # Use higher maturity and combined cycles
            from tensor_persistence import TensorRecord
            return TensorRecord(
                tensor_id=local.tensor_id,
                entity_id=local.entity_id,
                world_id=local.world_id,
                tensor_blob=serialize_tensor(merged_tensor),
                maturity=max(local.maturity, remote.maturity),
                training_cycles=local.training_cycles + remote.training_cycles,
                version=max(local.version, remote.version) + 1,
                description=local.description or remote.description,
                category=local.category or remote.category,
            )

        else:
            raise ValueError(f"Unknown conflict resolution strategy: {strategy}")

    # ========================================================================
    # Status and Info
    # ========================================================================

    def get_sync_status(
        self,
        tensor_db: Any  # TensorDatabase
    ) -> Dict[str, Any]:
        """
        Get sync status between local and remote.

        Args:
            tensor_db: Local TensorDatabase

        Returns:
            Dict with sync status information
        """
        local_tensors = tensor_db.list_tensors()
        local_templates = [t for t in local_tensors if t.category]
        local_instances = [t for t in local_tensors if t.entity_id and not t.category]

        return {
            "last_sync_version": self._last_sync_version,
            "local_templates": len(local_templates),
            "local_instances": len(local_instances),
            "total_local": len(local_tensors),
            "cache_dir": str(self.local_cache_dir),
        }

    @property
    def last_sync_version(self) -> Optional[str]:
        """Get the last sync version."""
        return self._last_sync_version
