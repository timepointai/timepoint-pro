"""
Audit logging for tensor access.

Provides:
- AccessAuditLog: Data class for access events
- AuditLogger: Records and queries access events

Phase 5: Access Control
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AccessAuditLog:
    """
    Record of a tensor access event.

    Attributes:
        id: Unique event ID (auto-generated)
        tensor_id: ID of the accessed tensor
        user_id: User who attempted access
        action: Action attempted (read, write, delete, fork)
        success: Whether access was granted
        timestamp: When access occurred
        metadata: Additional context (optional)
    """
    tensor_id: str
    user_id: str
    action: str
    success: bool
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


# ============================================================================
# Audit Logger
# ============================================================================

class AuditLogger:
    """
    Records and queries tensor access events.

    Provides comprehensive audit trail for:
    - Successful and failed access attempts
    - User activity tracking
    - Access pattern analysis

    Example:
        logger = AuditLogger(db_path="tensors.db")
        logger.log_access("tensor-001", "user-123", "read", success=True)
        history = logger.get_access_history("tensor-001")
    """

    def __init__(self, db_path: str):
        """
        Initialize audit logger.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self._init_schema()

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
        """Initialize audit log table."""
        with self._transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tensor_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata_json TEXT
                )
            """)

            # Indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_tensor
                ON access_audit_log(tensor_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user
                ON access_audit_log(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON access_audit_log(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_action
                ON access_audit_log(action)
            """)

    # =========================================================================
    # Logging
    # =========================================================================

    def log_access(
        self,
        tensor_id: str,
        user_id: str,
        action: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an access event.

        Args:
            tensor_id: Tensor that was accessed
            user_id: User who attempted access
            action: Action attempted (read, write, delete, fork)
            success: Whether access was granted
            metadata: Additional context

        Returns:
            ID of the logged event
        """
        now = datetime.utcnow().isoformat()

        with self._transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO access_audit_log
                (tensor_id, user_id, action, success, timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                tensor_id,
                user_id,
                action,
                1 if success else 0,
                now,
                json.dumps(metadata) if metadata else None,
            ))
            return cursor.lastrowid

    def log_batch(self, events: List[AccessAuditLog]) -> List[int]:
        """
        Log multiple access events.

        Args:
            events: List of AccessAuditLog objects

        Returns:
            List of event IDs
        """
        ids = []
        with self._transaction() as conn:
            for event in events:
                cursor = conn.execute("""
                    INSERT INTO access_audit_log
                    (tensor_id, user_id, action, success, timestamp, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event.tensor_id,
                    event.user_id,
                    event.action,
                    1 if event.success else 0,
                    event.timestamp.isoformat() if event.timestamp else datetime.utcnow().isoformat(),
                    json.dumps(event.metadata) if event.metadata else None,
                ))
                ids.append(cursor.lastrowid)
        return ids

    # =========================================================================
    # Queries
    # =========================================================================

    def get_access_history(
        self,
        tensor_id: str,
        limit: int = 100
    ) -> List[AccessAuditLog]:
        """
        Get access history for a tensor.

        Args:
            tensor_id: Tensor identifier
            limit: Maximum number of events

        Returns:
            List of AccessAuditLog events (newest first)
        """
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT * FROM access_audit_log
                WHERE tensor_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (tensor_id, limit))

            return [self._row_to_log(row) for row in cursor.fetchall()]

    def get_user_activity(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[AccessAuditLog]:
        """
        Get activity history for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of events

        Returns:
            List of AccessAuditLog events (newest first)
        """
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT * FROM access_audit_log
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            return [self._row_to_log(row) for row in cursor.fetchall()]

    def get_recent_access(
        self,
        tensor_id: str,
        hours: int = 24
    ) -> List[AccessAuditLog]:
        """
        Get recent access events for a tensor.

        Args:
            tensor_id: Tensor identifier
            hours: Number of hours to look back

        Returns:
            List of AccessAuditLog events
        """
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT * FROM access_audit_log
                WHERE tensor_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (tensor_id, since))

            return [self._row_to_log(row) for row in cursor.fetchall()]

    def get_failed_attempts(
        self,
        tensor_id: Optional[str] = None,
        user_id: Optional[str] = None,
        hours: int = 24
    ) -> List[AccessAuditLog]:
        """
        Get failed access attempts.

        Args:
            tensor_id: Optional tensor filter
            user_id: Optional user filter
            hours: Number of hours to look back

        Returns:
            List of failed AccessAuditLog events
        """
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        query = "SELECT * FROM access_audit_log WHERE success = 0 AND timestamp >= ?"
        params = [since]

        if tensor_id:
            query += " AND tensor_id = ?"
            params.append(tensor_id)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " ORDER BY timestamp DESC"

        with self._transaction() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_log(row) for row in cursor.fetchall()]

    def get_action_count(
        self,
        tensor_id: str,
        action: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Get action counts for a tensor.

        Args:
            tensor_id: Tensor identifier
            action: Optional specific action to count
            hours: Optional time window

        Returns:
            Dict mapping action -> count
        """
        query = "SELECT action, COUNT(*) as count FROM access_audit_log WHERE tensor_id = ?"
        params = [tensor_id]

        if action:
            query += " AND action = ?"
            params.append(action)

        if hours:
            since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            query += " AND timestamp >= ?"
            params.append(since)

        query += " GROUP BY action"

        with self._transaction() as conn:
            cursor = conn.execute(query, params)
            return {row["action"]: row["count"] for row in cursor.fetchall()}

    def get_user_count(self, tensor_id: str, hours: Optional[int] = None) -> int:
        """
        Get count of unique users who accessed a tensor.

        Args:
            tensor_id: Tensor identifier
            hours: Optional time window

        Returns:
            Number of unique users
        """
        query = "SELECT COUNT(DISTINCT user_id) as count FROM access_audit_log WHERE tensor_id = ?"
        params = [tensor_id]

        if hours:
            since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            query += " AND timestamp >= ?"
            params.append(since)

        with self._transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()["count"]

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_most_accessed_tensors(
        self,
        limit: int = 10,
        hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently accessed tensors.

        Args:
            limit: Number of tensors to return
            hours: Optional time window

        Returns:
            List of dicts with tensor_id and access_count
        """
        query = """
            SELECT tensor_id, COUNT(*) as access_count
            FROM access_audit_log
        """
        params = []

        if hours:
            since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            query += " WHERE timestamp >= ?"
            params.append(since)

        query += """
            GROUP BY tensor_id
            ORDER BY access_count DESC
            LIMIT ?
        """
        params.append(limit)

        with self._transaction() as conn:
            cursor = conn.execute(query, params)
            return [
                {"tensor_id": row["tensor_id"], "access_count": row["access_count"]}
                for row in cursor.fetchall()
            ]

    def get_most_active_users(
        self,
        limit: int = 10,
        hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get most active users.

        Args:
            limit: Number of users to return
            hours: Optional time window

        Returns:
            List of dicts with user_id and action_count
        """
        query = """
            SELECT user_id, COUNT(*) as action_count
            FROM access_audit_log
        """
        params = []

        if hours:
            since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            query += " WHERE timestamp >= ?"
            params.append(since)

        query += """
            GROUP BY user_id
            ORDER BY action_count DESC
            LIMIT ?
        """
        params.append(limit)

        with self._transaction() as conn:
            cursor = conn.execute(query, params)
            return [
                {"user_id": row["user_id"], "action_count": row["action_count"]}
                for row in cursor.fetchall()
            ]

    def get_access_summary(
        self,
        tensor_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get comprehensive access summary for a tensor.

        Args:
            tensor_id: Tensor identifier
            hours: Time window for statistics

        Returns:
            Dict with access statistics
        """
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        with self._transaction() as conn:
            # Total accesses
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_accesses,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    COUNT(DISTINCT user_id) as unique_users
                FROM access_audit_log
                WHERE tensor_id = ? AND timestamp >= ?
            """, (tensor_id, since))
            row = cursor.fetchone()

            # Action breakdown
            cursor = conn.execute("""
                SELECT action, COUNT(*) as count
                FROM access_audit_log
                WHERE tensor_id = ? AND timestamp >= ?
                GROUP BY action
            """, (tensor_id, since))
            actions = {r["action"]: r["count"] for r in cursor.fetchall()}

        return {
            "tensor_id": tensor_id,
            "time_window_hours": hours,
            "total_accesses": row["total_accesses"] or 0,
            "successful": row["successful"] or 0,
            "failed": row["failed"] or 0,
            "unique_users": row["unique_users"] or 0,
            "actions": actions,
        }

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Remove audit logs older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of deleted records
        """
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        with self._transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM access_audit_log WHERE timestamp < ?",
                (cutoff,)
            )
            return cursor.rowcount

    def clear_tensor_logs(self, tensor_id: str) -> int:
        """
        Remove all logs for a tensor (e.g., when tensor deleted).

        Args:
            tensor_id: Tensor identifier

        Returns:
            Number of deleted records
        """
        with self._transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM access_audit_log WHERE tensor_id = ?",
                (tensor_id,)
            )
            return cursor.rowcount

    # =========================================================================
    # Helpers
    # =========================================================================

    def _row_to_log(self, row: sqlite3.Row) -> AccessAuditLog:
        """Convert database row to AccessAuditLog."""
        return AccessAuditLog(
            id=row["id"],
            tensor_id=row["tensor_id"],
            user_id=row["user_id"],
            action=row["action"],
            success=bool(row["success"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else None,
        )

    def get_log_count(self) -> int:
        """Get total number of log entries."""
        with self._transaction() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM access_audit_log")
            return cursor.fetchone()["count"]
