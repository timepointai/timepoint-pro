"""
Permission enforcement for tensor access control.

Provides:
- TensorPermission: Data class for tensor access permissions
- PermissionEnforcer: Enforces access control on tensor operations
- PermissionDenied: Exception for access violations

Phase 5: Access Control
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set
from contextlib import contextmanager


# ============================================================================
# Exceptions
# ============================================================================

class PermissionDenied(Exception):
    """Raised when a user lacks permission for an action."""

    def __init__(self, user_id: str, tensor_id: str, action: str):
        self.user_id = user_id
        self.tensor_id = tensor_id
        self.action = action
        super().__init__(
            f"User '{user_id}' cannot {action} tensor '{tensor_id}'"
        )


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TensorPermission:
    """
    Permission record for a tensor.

    Attributes:
        tensor_id: ID of the tensor
        owner_id: User ID of the tensor owner
        access_level: "private", "shared", or "public"
        shared_with: List of user IDs with read access
        shared_groups: List of group IDs with read access
        api_enabled: Whether API access is allowed
        rate_limit: API requests per hour
        created_at: When permission was created
        modified_at: When permission was last modified
        accessed_at: When tensor was last accessed
        access_count: Total access count
    """
    tensor_id: str
    owner_id: str
    access_level: str = "private"
    shared_with: List[str] = field(default_factory=list)
    shared_groups: List[str] = field(default_factory=list)
    api_enabled: bool = False
    rate_limit: int = 100
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None
    access_count: int = 0

    def __post_init__(self):
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.modified_at is None:
            self.modified_at = now
        # Validate access level
        if self.access_level not in ("private", "shared", "public"):
            raise ValueError(f"Invalid access_level: {self.access_level}")


# ============================================================================
# Permission Enforcer
# ============================================================================

class PermissionEnforcer:
    """
    Enforces tensor access permissions.

    Provides methods to check and enforce permissions for read, write,
    fork, and delete operations on tensors.

    Example:
        enforcer = PermissionEnforcer(db_path="tensors.db")
        if enforcer.can_read("user-123", "tensor-456"):
            tensor = db.get_tensor("tensor-456")

        # Or enforce (raises PermissionDenied if not allowed)
        enforcer.enforce("user-123", "tensor-456", "read")
    """

    def __init__(self, db_path: str):
        """
        Initialize permission enforcer.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self._init_schema()
        # User groups cache (user_id -> set of group_ids)
        self._user_groups: dict = {}

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _transaction(self):
        """Context manager for atomic transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        """Initialize permission tables."""
        with self._transaction() as conn:
            # Permissions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tensor_permissions (
                    tensor_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    access_level TEXT NOT NULL DEFAULT 'private',
                    shared_with_json TEXT,
                    shared_groups_json TEXT,
                    api_enabled INTEGER DEFAULT 0,
                    rate_limit INTEGER DEFAULT 100,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL,
                    accessed_at TEXT,
                    access_count INTEGER DEFAULT 0
                )
            """)

            # User groups table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_groups (
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    PRIMARY KEY (user_id, group_id)
                )
            """)

            # Indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_perm_owner
                ON tensor_permissions(owner_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_perm_access_level
                ON tensor_permissions(access_level)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_groups
                ON user_groups(group_id)
            """)

    # =========================================================================
    # Permission CRUD
    # =========================================================================

    def get_permission(self, tensor_id: str) -> Optional[TensorPermission]:
        """
        Get permission record for a tensor.

        Args:
            tensor_id: Tensor identifier

        Returns:
            TensorPermission if found, None otherwise
        """
        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT * FROM tensor_permissions WHERE tensor_id = ?",
                (tensor_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return TensorPermission(
                tensor_id=row["tensor_id"],
                owner_id=row["owner_id"],
                access_level=row["access_level"],
                shared_with=json.loads(row["shared_with_json"] or "[]"),
                shared_groups=json.loads(row["shared_groups_json"] or "[]"),
                api_enabled=bool(row["api_enabled"]),
                rate_limit=row["rate_limit"],
                created_at=datetime.fromisoformat(row["created_at"]),
                modified_at=datetime.fromisoformat(row["modified_at"]),
                accessed_at=datetime.fromisoformat(row["accessed_at"]) if row["accessed_at"] else None,
                access_count=row["access_count"],
            )

    def set_permission(self, permission: TensorPermission) -> None:
        """
        Create or update a permission record.

        Args:
            permission: TensorPermission to save
        """
        now = datetime.utcnow().isoformat()
        permission.modified_at = datetime.utcnow()

        with self._transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tensor_permissions
                (tensor_id, owner_id, access_level, shared_with_json,
                 shared_groups_json, api_enabled, rate_limit, created_at,
                 modified_at, accessed_at, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                permission.tensor_id,
                permission.owner_id,
                permission.access_level,
                json.dumps(permission.shared_with),
                json.dumps(permission.shared_groups),
                1 if permission.api_enabled else 0,
                permission.rate_limit,
                permission.created_at.isoformat() if permission.created_at else now,
                now,
                permission.accessed_at.isoformat() if permission.accessed_at else None,
                permission.access_count,
            ))

    def delete_permission(self, tensor_id: str) -> bool:
        """
        Delete permission record.

        Args:
            tensor_id: Tensor identifier

        Returns:
            True if deleted, False if not found
        """
        with self._transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM tensor_permissions WHERE tensor_id = ?",
                (tensor_id,)
            )
            return cursor.rowcount > 0

    def create_default_permission(
        self,
        tensor_id: str,
        owner_id: str,
        access_level: str = "private"
    ) -> TensorPermission:
        """
        Create default permission for a new tensor.

        Args:
            tensor_id: Tensor identifier
            owner_id: Owner user ID
            access_level: Initial access level

        Returns:
            Created TensorPermission
        """
        perm = TensorPermission(
            tensor_id=tensor_id,
            owner_id=owner_id,
            access_level=access_level,
        )
        self.set_permission(perm)
        return perm

    # =========================================================================
    # Permission Checks
    # =========================================================================

    def can_read(self, user_id: str, tensor_id: str) -> bool:
        """
        Check if user can read tensor.

        Args:
            user_id: User identifier
            tensor_id: Tensor identifier

        Returns:
            True if user has read access
        """
        perm = self.get_permission(tensor_id)

        # No permission record = no access (unless we want default behavior)
        if perm is None:
            return False

        # Owner always has access
        if perm.owner_id == user_id:
            return True

        # Public tensors are readable by anyone
        if perm.access_level == "public":
            return True

        # Check shared access
        if perm.access_level == "shared":
            # Direct user share
            if user_id in perm.shared_with:
                return True

            # Group share
            user_groups = self.get_user_groups(user_id)
            if user_groups.intersection(set(perm.shared_groups)):
                return True

        return False

    def can_write(self, user_id: str, tensor_id: str) -> bool:
        """
        Check if user can write (modify) tensor.

        Only owner can write.

        Args:
            user_id: User identifier
            tensor_id: Tensor identifier

        Returns:
            True if user has write access
        """
        perm = self.get_permission(tensor_id)
        if perm is None:
            return False

        # Only owner can write
        return perm.owner_id == user_id

    def can_delete(self, user_id: str, tensor_id: str) -> bool:
        """
        Check if user can delete tensor.

        Only owner can delete.

        Args:
            user_id: User identifier
            tensor_id: Tensor identifier

        Returns:
            True if user has delete access
        """
        # Same as write - only owner
        return self.can_write(user_id, tensor_id)

    def can_fork(self, user_id: str, tensor_id: str) -> bool:
        """
        Check if user can fork (clone) tensor.

        User can fork if they can read.

        Args:
            user_id: User identifier
            tensor_id: Tensor identifier

        Returns:
            True if user can fork
        """
        # Must be able to read to fork
        return self.can_read(user_id, tensor_id)

    def enforce(
        self,
        user_id: str,
        tensor_id: str,
        action: str
    ) -> None:
        """
        Enforce permission, raise if denied.

        Args:
            user_id: User identifier
            tensor_id: Tensor identifier
            action: Action to check ("read", "write", "delete", "fork")

        Raises:
            PermissionDenied: If user lacks permission
            ValueError: If action is invalid
        """
        check_fn = {
            "read": self.can_read,
            "write": self.can_write,
            "delete": self.can_delete,
            "fork": self.can_fork,
        }.get(action)

        if check_fn is None:
            raise ValueError(f"Invalid action: {action}")

        if not check_fn(user_id, tensor_id):
            raise PermissionDenied(user_id, tensor_id, action)

    # =========================================================================
    # Access Management
    # =========================================================================

    def grant_access(
        self,
        owner_id: str,
        tensor_id: str,
        target_user_id: str
    ) -> bool:
        """
        Grant read access to a user.

        Args:
            owner_id: Owner user ID (must be tensor owner)
            tensor_id: Tensor identifier
            target_user_id: User to grant access to

        Returns:
            True if access granted, False if not authorized
        """
        perm = self.get_permission(tensor_id)
        if perm is None or perm.owner_id != owner_id:
            return False

        # Add to shared list if not already there
        if target_user_id not in perm.shared_with:
            perm.shared_with.append(target_user_id)
            # Upgrade to shared if private
            if perm.access_level == "private":
                perm.access_level = "shared"
            self.set_permission(perm)

        return True

    def revoke_access(
        self,
        owner_id: str,
        tensor_id: str,
        target_user_id: str
    ) -> bool:
        """
        Revoke read access from a user.

        Args:
            owner_id: Owner user ID (must be tensor owner)
            tensor_id: Tensor identifier
            target_user_id: User to revoke access from

        Returns:
            True if access revoked, False if not authorized
        """
        perm = self.get_permission(tensor_id)
        if perm is None or perm.owner_id != owner_id:
            return False

        # Remove from shared list
        if target_user_id in perm.shared_with:
            perm.shared_with.remove(target_user_id)
            # Downgrade to private if no shares left
            if not perm.shared_with and not perm.shared_groups:
                perm.access_level = "private"
            self.set_permission(perm)

        return True

    def set_access_level(
        self,
        owner_id: str,
        tensor_id: str,
        access_level: str
    ) -> bool:
        """
        Change tensor access level.

        Args:
            owner_id: Owner user ID (must be tensor owner)
            tensor_id: Tensor identifier
            access_level: New access level

        Returns:
            True if level changed, False if not authorized
        """
        if access_level not in ("private", "shared", "public"):
            raise ValueError(f"Invalid access_level: {access_level}")

        perm = self.get_permission(tensor_id)
        if perm is None or perm.owner_id != owner_id:
            return False

        perm.access_level = access_level
        self.set_permission(perm)
        return True

    def grant_group_access(
        self,
        owner_id: str,
        tensor_id: str,
        group_id: str
    ) -> bool:
        """
        Grant read access to a group.

        Args:
            owner_id: Owner user ID
            tensor_id: Tensor identifier
            group_id: Group to grant access to

        Returns:
            True if access granted
        """
        perm = self.get_permission(tensor_id)
        if perm is None or perm.owner_id != owner_id:
            return False

        if group_id not in perm.shared_groups:
            perm.shared_groups.append(group_id)
            if perm.access_level == "private":
                perm.access_level = "shared"
            self.set_permission(perm)

        return True

    def revoke_group_access(
        self,
        owner_id: str,
        tensor_id: str,
        group_id: str
    ) -> bool:
        """
        Revoke read access from a group.

        Args:
            owner_id: Owner user ID
            tensor_id: Tensor identifier
            group_id: Group to revoke access from

        Returns:
            True if access revoked
        """
        perm = self.get_permission(tensor_id)
        if perm is None or perm.owner_id != owner_id:
            return False

        if group_id in perm.shared_groups:
            perm.shared_groups.remove(group_id)
            if not perm.shared_with and not perm.shared_groups:
                perm.access_level = "private"
            self.set_permission(perm)

        return True

    # =========================================================================
    # User Groups
    # =========================================================================

    def get_user_groups(self, user_id: str) -> Set[str]:
        """
        Get groups a user belongs to.

        Args:
            user_id: User identifier

        Returns:
            Set of group IDs
        """
        # Check cache first
        if user_id in self._user_groups:
            return self._user_groups[user_id]

        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT group_id FROM user_groups WHERE user_id = ?",
                (user_id,)
            )
            groups = {row["group_id"] for row in cursor.fetchall()}

        # Cache it
        self._user_groups[user_id] = groups
        return groups

    def add_user_to_group(self, user_id: str, group_id: str) -> None:
        """
        Add user to a group.

        Args:
            user_id: User identifier
            group_id: Group identifier
        """
        with self._transaction() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO user_groups (user_id, group_id)
                VALUES (?, ?)
            """, (user_id, group_id))

        # Invalidate cache
        if user_id in self._user_groups:
            del self._user_groups[user_id]

    def remove_user_from_group(self, user_id: str, group_id: str) -> None:
        """
        Remove user from a group.

        Args:
            user_id: User identifier
            group_id: Group identifier
        """
        with self._transaction() as conn:
            conn.execute(
                "DELETE FROM user_groups WHERE user_id = ? AND group_id = ?",
                (user_id, group_id)
            )

        # Invalidate cache
        if user_id in self._user_groups:
            del self._user_groups[user_id]

    def get_group_members(self, group_id: str) -> List[str]:
        """
        Get all members of a group.

        Args:
            group_id: Group identifier

        Returns:
            List of user IDs
        """
        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT user_id FROM user_groups WHERE group_id = ?",
                (group_id,)
            )
            return [row["user_id"] for row in cursor.fetchall()]

    # =========================================================================
    # Access Recording
    # =========================================================================

    def record_access(self, tensor_id: str) -> None:
        """
        Record that a tensor was accessed.

        Updates accessed_at timestamp and increments access_count.

        Args:
            tensor_id: Tensor identifier
        """
        now = datetime.utcnow().isoformat()

        with self._transaction() as conn:
            conn.execute("""
                UPDATE tensor_permissions
                SET accessed_at = ?, access_count = access_count + 1
                WHERE tensor_id = ?
            """, (now, tensor_id))

    # =========================================================================
    # Queries
    # =========================================================================

    def list_accessible_tensors(
        self,
        user_id: str,
        include_public: bool = True
    ) -> List[str]:
        """
        List all tensor IDs accessible by a user.

        Args:
            user_id: User identifier
            include_public: Whether to include public tensors

        Returns:
            List of accessible tensor IDs
        """
        accessible = []
        user_groups = self.get_user_groups(user_id)

        with self._transaction() as conn:
            cursor = conn.execute("SELECT * FROM tensor_permissions")
            for row in cursor.fetchall():
                # Owner access
                if row["owner_id"] == user_id:
                    accessible.append(row["tensor_id"])
                    continue

                # Public access
                if include_public and row["access_level"] == "public":
                    accessible.append(row["tensor_id"])
                    continue

                # Shared access
                if row["access_level"] == "shared":
                    shared_with = json.loads(row["shared_with_json"] or "[]")
                    if user_id in shared_with:
                        accessible.append(row["tensor_id"])
                        continue

                    shared_groups = json.loads(row["shared_groups_json"] or "[]")
                    if user_groups.intersection(set(shared_groups)):
                        accessible.append(row["tensor_id"])

        return accessible

    def list_owned_tensors(self, owner_id: str) -> List[str]:
        """
        List tensor IDs owned by a user.

        Args:
            owner_id: Owner user ID

        Returns:
            List of owned tensor IDs
        """
        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT tensor_id FROM tensor_permissions WHERE owner_id = ?",
                (owner_id,)
            )
            return [row["tensor_id"] for row in cursor.fetchall()]

    def list_shared_tensors(self, user_id: str) -> List[str]:
        """
        List tensors shared with a user (not owned, not public).

        Args:
            user_id: User identifier

        Returns:
            List of shared tensor IDs
        """
        shared = []
        user_groups = self.get_user_groups(user_id)

        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT * FROM tensor_permissions WHERE access_level = 'shared'"
            )
            for row in cursor.fetchall():
                if row["owner_id"] == user_id:
                    continue

                shared_with = json.loads(row["shared_with_json"] or "[]")
                if user_id in shared_with:
                    shared.append(row["tensor_id"])
                    continue

                shared_groups = json.loads(row["shared_groups_json"] or "[]")
                if user_groups.intersection(set(shared_groups)):
                    shared.append(row["tensor_id"])

        return shared
