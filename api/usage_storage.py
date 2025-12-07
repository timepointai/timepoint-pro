"""
Usage tracking storage for the API.

Provides SQLite-based persistence for usage records,
supporting monthly billing periods and quota enforcement.

Phase 6: Public API - Usage Quotas
"""

import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class UsageRecord:
    """Usage record for a billing period."""

    user_id: str
    period: str  # Format: "YYYY-MM" for monthly
    api_calls: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    simulations_run: int = 0
    simulations_completed: int = 0
    simulations_failed: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UsageEvent:
    """Individual usage event for history tracking."""

    event_id: str
    user_id: str
    event_type: str  # "api_call", "simulation_start", "simulation_complete", "cost"
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Usage Database
# ============================================================================

class UsageDatabase:
    """
    SQLite-based storage for usage tracking.

    Tracks API usage per user per billing period (monthly).
    Survives server restarts unlike in-memory rate limiting.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the usage database.

        Args:
            db_path: Path to SQLite database file.
                    Defaults to metadata/usage.db
        """
        self.db_path = db_path or os.getenv(
            "USAGE_DB_PATH",
            "metadata/usage.db"
        )
        self._local = threading.local()
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_schema(self) -> None:
        """Initialize database schema."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        with self._transaction() as conn:
            conn.executescript("""
                -- Usage records per billing period
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    period TEXT NOT NULL,
                    api_calls INTEGER DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    simulations_run INTEGER DEFAULT 0,
                    simulations_completed INTEGER DEFAULT 0,
                    simulations_failed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, period)
                );

                CREATE INDEX IF NOT EXISTS idx_usage_user_period
                    ON usage_records(user_id, period);

                -- Usage event history (for auditing)
                CREATE TABLE IF NOT EXISTS usage_events (
                    event_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_events_user
                    ON usage_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON usage_events(timestamp);
            """)

    # ========================================================================
    # Period Helpers
    # ========================================================================

    @staticmethod
    def current_period() -> str:
        """Get current billing period (YYYY-MM format)."""
        return datetime.utcnow().strftime("%Y-%m")

    @staticmethod
    def period_start(period: str) -> datetime:
        """Get start datetime of a billing period."""
        return datetime.strptime(period, "%Y-%m")

    @staticmethod
    def period_end(period: str) -> datetime:
        """Get end datetime of a billing period (start of next month)."""
        start = UsageDatabase.period_start(period)
        if start.month == 12:
            return start.replace(year=start.year + 1, month=1)
        return start.replace(month=start.month + 1)

    @staticmethod
    def days_remaining_in_period(period: str) -> int:
        """Get days remaining in the billing period."""
        now = datetime.utcnow()
        end = UsageDatabase.period_end(period)
        delta = end - now
        return max(0, delta.days)

    # ========================================================================
    # Usage Record CRUD
    # ========================================================================

    def get_usage(
        self,
        user_id: str,
        period: Optional[str] = None
    ) -> UsageRecord:
        """
        Get usage record for a user and period.

        Creates a new record if one doesn't exist.

        Args:
            user_id: User ID
            period: Billing period (defaults to current)

        Returns:
            UsageRecord
        """
        period = period or self.current_period()
        conn = self._get_connection()

        row = conn.execute(
            """
            SELECT * FROM usage_records
            WHERE user_id = ? AND period = ?
            """,
            (user_id, period)
        ).fetchone()

        if row:
            return UsageRecord(
                user_id=row["user_id"],
                period=row["period"],
                api_calls=row["api_calls"],
                tokens_used=row["tokens_used"],
                cost_usd=row["cost_usd"],
                simulations_run=row["simulations_run"],
                simulations_completed=row["simulations_completed"],
                simulations_failed=row["simulations_failed"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

        # Create new record
        now = datetime.utcnow()
        record = UsageRecord(
            user_id=user_id,
            period=period,
            created_at=now,
            updated_at=now,
        )

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO usage_records
                (user_id, period, api_calls, tokens_used, cost_usd,
                 simulations_run, simulations_completed, simulations_failed,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.user_id,
                    record.period,
                    record.api_calls,
                    record.tokens_used,
                    record.cost_usd,
                    record.simulations_run,
                    record.simulations_completed,
                    record.simulations_failed,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                )
            )

        return record

    def increment_api_calls(
        self,
        user_id: str,
        count: int = 1,
        period: Optional[str] = None
    ) -> UsageRecord:
        """
        Increment API call count.

        Args:
            user_id: User ID
            count: Number of calls to add
            period: Billing period (defaults to current)

        Returns:
            Updated UsageRecord
        """
        period = period or self.current_period()

        # Ensure record exists
        self.get_usage(user_id, period)

        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE usage_records
                SET api_calls = api_calls + ?,
                    updated_at = ?
                WHERE user_id = ? AND period = ?
                """,
                (count, datetime.utcnow().isoformat(), user_id, period)
            )

        return self.get_usage(user_id, period)

    def increment_simulations(
        self,
        user_id: str,
        started: int = 0,
        completed: int = 0,
        failed: int = 0,
        period: Optional[str] = None
    ) -> UsageRecord:
        """
        Increment simulation counts.

        Args:
            user_id: User ID
            started: Simulations started
            completed: Simulations completed
            failed: Simulations failed
            period: Billing period

        Returns:
            Updated UsageRecord
        """
        period = period or self.current_period()

        # Ensure record exists
        self.get_usage(user_id, period)

        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE usage_records
                SET simulations_run = simulations_run + ?,
                    simulations_completed = simulations_completed + ?,
                    simulations_failed = simulations_failed + ?,
                    updated_at = ?
                WHERE user_id = ? AND period = ?
                """,
                (
                    started,
                    completed,
                    failed,
                    datetime.utcnow().isoformat(),
                    user_id,
                    period
                )
            )

        return self.get_usage(user_id, period)

    def add_cost(
        self,
        user_id: str,
        cost_usd: float,
        tokens: int = 0,
        period: Optional[str] = None
    ) -> UsageRecord:
        """
        Add cost and token usage.

        Args:
            user_id: User ID
            cost_usd: Cost in USD
            tokens: Tokens used
            period: Billing period

        Returns:
            Updated UsageRecord
        """
        period = period or self.current_period()

        # Ensure record exists
        self.get_usage(user_id, period)

        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE usage_records
                SET cost_usd = cost_usd + ?,
                    tokens_used = tokens_used + ?,
                    updated_at = ?
                WHERE user_id = ? AND period = ?
                """,
                (cost_usd, tokens, datetime.utcnow().isoformat(), user_id, period)
            )

        return self.get_usage(user_id, period)

    def get_usage_history(
        self,
        user_id: str,
        limit: int = 12
    ) -> List[UsageRecord]:
        """
        Get usage history for a user.

        Args:
            user_id: User ID
            limit: Maximum periods to return

        Returns:
            List of UsageRecords, most recent first
        """
        conn = self._get_connection()

        rows = conn.execute(
            """
            SELECT * FROM usage_records
            WHERE user_id = ?
            ORDER BY period DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()

        return [
            UsageRecord(
                user_id=row["user_id"],
                period=row["period"],
                api_calls=row["api_calls"],
                tokens_used=row["tokens_used"],
                cost_usd=row["cost_usd"],
                simulations_run=row["simulations_run"],
                simulations_completed=row["simulations_completed"],
                simulations_failed=row["simulations_failed"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    # ========================================================================
    # Usage Events
    # ========================================================================

    def log_event(
        self,
        user_id: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a usage event.

        Args:
            user_id: User ID
            event_type: Type of event
            details: Additional details

        Returns:
            Event ID
        """
        import json
        import uuid

        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO usage_events
                (event_id, user_id, event_type, timestamp, details_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    user_id,
                    event_type,
                    timestamp.isoformat(),
                    json.dumps(details) if details else None
                )
            )

        return event_id

    def get_recent_events(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent events for a user.

        Args:
            user_id: User ID
            limit: Maximum events to return

        Returns:
            List of event dictionaries
        """
        import json

        conn = self._get_connection()

        rows = conn.execute(
            """
            SELECT * FROM usage_events
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()

        return [
            {
                "event_id": row["event_id"],
                "user_id": row["user_id"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "details": json.loads(row["details_json"]) if row["details_json"] else None,
            }
            for row in rows
        ]

    # ========================================================================
    # Stats & Cleanup
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get overall usage statistics."""
        conn = self._get_connection()
        period = self.current_period()

        row = conn.execute(
            """
            SELECT
                COUNT(DISTINCT user_id) as active_users,
                SUM(api_calls) as total_api_calls,
                SUM(tokens_used) as total_tokens,
                SUM(cost_usd) as total_cost,
                SUM(simulations_run) as total_simulations
            FROM usage_records
            WHERE period = ?
            """,
            (period,)
        ).fetchone()

        return {
            "period": period,
            "active_users": row["active_users"] or 0,
            "total_api_calls": row["total_api_calls"] or 0,
            "total_tokens": row["total_tokens"] or 0,
            "total_cost_usd": row["total_cost"] or 0.0,
            "total_simulations": row["total_simulations"] or 0,
        }

    def cleanup_old_events(self, days: int = 90) -> int:
        """
        Remove old usage events.

        Args:
            days: Keep events from the last N days

        Returns:
            Number of events deleted
        """
        from datetime import timedelta

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        with self._transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM usage_events WHERE timestamp < ?",
                (cutoff,)
            )
            return cursor.rowcount

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# Global Instance
# ============================================================================

_usage_db: Optional[UsageDatabase] = None


def get_usage_database() -> UsageDatabase:
    """Get or create the global usage database."""
    global _usage_db
    if _usage_db is None:
        _usage_db = UsageDatabase()
    return _usage_db


def reset_usage_database() -> None:
    """Reset the global usage database (for testing)."""
    global _usage_db
    if _usage_db:
        _usage_db.close()
    _usage_db = None
