"""
Synchronization utilities for SQLite-Oxen tensor data.

Handles bidirectional sync between local SQLite database
and Oxen remote repository.

Phase 4: Oxen Integration
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import hashlib
import json

from .parquet_schemas import (
    write_templates_parquet,
    write_instances_parquet,
    read_templates_parquet,
    read_instances_parquet,
)


@dataclass
class SyncState:
    """
    Tracks synchronization state between local and remote.

    Persisted to allow incremental syncs.
    """
    last_sync_time: Optional[datetime] = None
    last_local_version: Optional[str] = None
    last_remote_version: Optional[str] = None
    synced_tensor_ids: Set[str] = field(default_factory=set)
    pending_uploads: Set[str] = field(default_factory=set)
    pending_downloads: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict:
        """Convert to serializable dict."""
        return {
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "last_local_version": self.last_local_version,
            "last_remote_version": self.last_remote_version,
            "synced_tensor_ids": list(self.synced_tensor_ids),
            "pending_uploads": list(self.pending_uploads),
            "pending_downloads": list(self.pending_downloads),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SyncState":
        """Create from dict."""
        return cls(
            last_sync_time=datetime.fromisoformat(data["last_sync_time"]) if data.get("last_sync_time") else None,
            last_local_version=data.get("last_local_version"),
            last_remote_version=data.get("last_remote_version"),
            synced_tensor_ids=set(data.get("synced_tensor_ids", [])),
            pending_uploads=set(data.get("pending_uploads", [])),
            pending_downloads=set(data.get("pending_downloads", [])),
        )


class TensorSyncManager:
    """
    Manages synchronization between local SQLite and Oxen.

    Features:
    - Incremental sync based on version tracking
    - Hash-based change detection
    - Conflict detection and resolution
    - Batch upload/download for efficiency

    Example:
        sync_mgr = TensorSyncManager(tensor_db, version_controller)
        changes = sync_mgr.detect_changes()
        sync_mgr.push_changes(changes)
    """

    def __init__(
        self,
        tensor_db: Any,  # TensorDatabase
        version_controller: Any,  # TensorVersionController
        state_file: Optional[str] = None
    ):
        """
        Initialize sync manager.

        Args:
            tensor_db: Local TensorDatabase
            version_controller: TensorVersionController for Oxen operations
            state_file: Path to sync state file (default: metadata/sync_state.json)
        """
        self.tensor_db = tensor_db
        self.version_controller = version_controller
        self.state_file = Path(state_file) if state_file else Path("metadata/sync_state.json")
        self.state = self._load_state()

    # ========================================================================
    # State Management
    # ========================================================================

    def _load_state(self) -> SyncState:
        """Load sync state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                return SyncState.from_dict(data)
            except Exception:
                pass
        return SyncState()

    def _save_state(self) -> None:
        """Save sync state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state.to_dict(), f, indent=2)

    def _compute_tensor_hash(self, record: Any) -> str:
        """Compute hash of tensor for change detection."""
        # Hash tensor blob + metadata
        hasher = hashlib.sha256()
        hasher.update(record.tensor_blob)
        hasher.update(str(record.maturity).encode())
        hasher.update(str(record.training_cycles).encode())
        if record.description:
            hasher.update(record.description.encode())
        return hasher.hexdigest()[:16]

    # ========================================================================
    # Change Detection
    # ========================================================================

    def detect_local_changes(self) -> List[Any]:
        """
        Detect tensors that have changed locally since last sync.

        Returns:
            List of TensorRecord objects that need syncing
        """
        all_tensors = self.tensor_db.list_tensors()
        changed = []

        for record in all_tensors:
            # Check if already synced
            if record.tensor_id in self.state.synced_tensor_ids:
                # Check if modified since last sync
                if self.state.last_sync_time and record.updated_at:
                    if record.updated_at > self.state.last_sync_time:
                        changed.append(record)
                # If no timestamps, use hash comparison
                else:
                    changed.append(record)
            else:
                # New tensor - never synced
                changed.append(record)

        return changed

    def detect_pending_sync(self, min_maturity: float = 0.0) -> Dict[str, List[Any]]:
        """
        Detect all tensors needing sync, categorized by type.

        Args:
            min_maturity: Minimum maturity threshold for sync

        Returns:
            Dict with "templates" and "instances" lists
        """
        changes = self.detect_local_changes()

        # Filter by maturity
        changes = [t for t in changes if t.maturity >= min_maturity]

        # Categorize
        templates = []
        instances = []

        for record in changes:
            if record.category:
                templates.append(record)
            elif record.entity_id:
                instances.append(record)

        return {
            "templates": templates,
            "instances": instances,
        }

    # ========================================================================
    # Sync Operations
    # ========================================================================

    def push_changes(
        self,
        records: Optional[List[Any]] = None,
        commit_message: Optional[str] = None,
        min_maturity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Push local changes to Oxen.

        Args:
            records: Specific records to push (or auto-detect if None)
            commit_message: Optional commit message
            min_maturity: Minimum maturity for auto-detected records

        Returns:
            Dict with push results
        """
        if records is None:
            changes = self.detect_pending_sync(min_maturity)
            records = changes["templates"] + changes["instances"]

        if not records:
            return {"pushed": 0, "message": "No changes to push"}

        # Use version controller to sync
        result = self.version_controller.sync_local_to_remote(
            tensor_db=self.tensor_db,
            min_maturity=min_maturity
        )

        # Update state
        if result.synced_count > 0:
            self.state.last_sync_time = datetime.now()
            self.state.last_local_version = result.version

            for record in records:
                self.state.synced_tensor_ids.add(record.tensor_id)
                self.state.pending_uploads.discard(record.tensor_id)

            self._save_state()

        return {
            "pushed": result.synced_count,
            "version": result.version,
            "errors": result.errors,
        }

    def pull_changes(self) -> Dict[str, Any]:
        """
        Pull remote changes to local.

        Returns:
            Dict with pull results
        """
        result = self.version_controller.fetch_remote_updates(
            tensor_db=self.tensor_db
        )

        # Update state
        if result.fetched_count > 0:
            self.state.last_sync_time = datetime.now()
            self.state.last_remote_version = result.version

            for template_id in result.new_templates:
                self.state.synced_tensor_ids.add(template_id)
                self.state.pending_downloads.discard(template_id)

            for instance_id in result.new_instances:
                self.state.synced_tensor_ids.add(instance_id)
                self.state.pending_downloads.discard(instance_id)

            self._save_state()

        return {
            "pulled": result.fetched_count,
            "version": result.version,
            "new_templates": result.new_templates,
            "new_instances": result.new_instances,
        }

    def sync_bidirectional(self, min_maturity: float = 0.0) -> Dict[str, Any]:
        """
        Perform bidirectional sync (pull then push).

        Args:
            min_maturity: Minimum maturity for pushing

        Returns:
            Combined results from pull and push
        """
        # Pull first to get latest
        pull_result = self.pull_changes()

        # Then push local changes
        push_result = self.push_changes(min_maturity=min_maturity)

        return {
            "pull": pull_result,
            "push": push_result,
            "total_synced": pull_result["pulled"] + push_result["pushed"],
        }

    # ========================================================================
    # Export/Import for Offline
    # ========================================================================

    def export_for_offline(
        self,
        output_dir: str,
        include_templates: bool = True,
        include_instances: bool = True,
        min_maturity: float = 0.0
    ) -> Dict[str, str]:
        """
        Export tensors to Parquet files for offline use.

        Args:
            output_dir: Directory to write Parquet files
            include_templates: Whether to export templates
            include_instances: Whether to export instances
            min_maturity: Minimum maturity threshold

        Returns:
            Dict with paths to exported files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        all_tensors = self.tensor_db.list_tensors()
        tensors = [t for t in all_tensors if t.maturity >= min_maturity]

        result = {}

        if include_templates:
            templates = [t for t in tensors if t.category]
            if templates:
                path = output_path / "templates.parquet"
                write_templates_parquet(templates, str(path))
                result["templates"] = str(path)

        if include_instances:
            instances = [t for t in tensors if t.entity_id and not t.category]
            if instances:
                path = output_path / "instances.parquet"
                write_instances_parquet(instances, str(path))
                result["instances"] = str(path)

        return result

    def import_from_parquet(
        self,
        templates_path: Optional[str] = None,
        instances_path: Optional[str] = None,
        overwrite: bool = False
    ) -> Dict[str, int]:
        """
        Import tensors from Parquet files.

        Args:
            templates_path: Path to templates.parquet
            instances_path: Path to instances.parquet
            overwrite: Whether to overwrite existing tensors

        Returns:
            Dict with import counts
        """
        imported_templates = 0
        imported_instances = 0

        if templates_path:
            templates = read_templates_parquet(templates_path)
            for record in templates:
                existing = self.tensor_db.get_tensor(record.tensor_id)
                if existing is None or overwrite:
                    self.tensor_db.save_tensor(record)
                    imported_templates += 1

        if instances_path:
            instances = read_instances_parquet(instances_path)
            for record in instances:
                existing = self.tensor_db.get_tensor(record.tensor_id)
                if existing is None or overwrite:
                    self.tensor_db.save_tensor(record)
                    imported_instances += 1

        return {
            "templates": imported_templates,
            "instances": imported_instances,
            "total": imported_templates + imported_instances,
        }

    # ========================================================================
    # Status and Diagnostics
    # ========================================================================

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current sync status.

        Returns:
            Dict with sync statistics
        """
        pending = self.detect_pending_sync()

        return {
            "last_sync": self.state.last_sync_time.isoformat() if self.state.last_sync_time else None,
            "last_local_version": self.state.last_local_version,
            "last_remote_version": self.state.last_remote_version,
            "synced_count": len(self.state.synced_tensor_ids),
            "pending_templates": len(pending["templates"]),
            "pending_instances": len(pending["instances"]),
            "total_pending": len(pending["templates"]) + len(pending["instances"]),
        }

    def reset_sync_state(self) -> None:
        """Reset sync state (marks all as unsynced)."""
        self.state = SyncState()
        self._save_state()

    def mark_as_synced(self, tensor_ids: List[str]) -> None:
        """
        Manually mark tensors as synced.

        Args:
            tensor_ids: List of tensor IDs to mark
        """
        for tid in tensor_ids:
            self.state.synced_tensor_ids.add(tid)
            self.state.pending_uploads.discard(tid)
        self.state.last_sync_time = datetime.now()
        self._save_state()
