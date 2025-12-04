"""
Tensor persistence layer for TTMTensor storage with versioning.

Provides:
- TensorDatabase: SQLite-backed tensor storage with CRUD operations
- TensorRecord: Data class for tensor metadata
- TensorVersion: Data class for version history entries
- Optimistic locking for concurrent access
- Batch operations for efficiency
- Maturity-based queries
- Training history tracking

Schema:
- tensor_records: Current tensor state (latest version)
- tensor_versions: Full version history
- training_jobs: Queue for parallel training (Phase 2)
"""
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager


@dataclass
class TensorRecord:
    """
    Represents a tensor record in the database.

    Attributes:
        tensor_id: Unique identifier for this tensor
        entity_id: Entity this tensor belongs to
        world_id: Simulation world context
        tensor_blob: Serialized TTMTensor bytes
        maturity: Quality score 0.0-1.0 (operational at >= 0.95)
        training_cycles: Number of training iterations completed
        version: Current version number (auto-incremented)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    tensor_id: str
    entity_id: str
    world_id: Optional[str] = None
    tensor_blob: bytes = b""
    maturity: float = 0.0
    training_cycles: int = 0
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Phase 3: Retrieval fields
    description: Optional[str] = None  # Natural language description for RAG
    category: Optional[str] = None     # Category path (e.g., "profession/detective")
    embedding_blob: Optional[bytes] = None  # Cached embedding for search

    def __post_init__(self):
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now


@dataclass
class TensorVersion:
    """
    Represents a historical version of a tensor.

    Attributes:
        tensor_id: Reference to parent tensor
        version: Version number
        tensor_blob: Tensor state at this version
        maturity: Maturity at this version
        training_cycles: Training cycles at this version
        created_at: When this version was created
    """
    tensor_id: str
    version: int
    tensor_blob: bytes
    maturity: float
    training_cycles: int
    created_at: datetime


class TensorDatabase:
    """
    SQLite-backed tensor storage with versioning and optimistic locking.

    Features:
    - CRUD operations for tensor records
    - Automatic version history tracking
    - Maturity-based queries
    - Batch operations with transaction support
    - Optimistic locking for concurrent access

    Example:
        >>> db = TensorDatabase("tensors.db")
        >>> db.save_tensor(record)
        >>> tensor = db.get_tensor("tensor-001")
        >>> history = db.get_version_history("tensor-001")
    """

    def __init__(self, db_path: str):
        """
        Initialize tensor database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
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
        """Initialize database schema."""
        with self._transaction() as conn:
            # Main tensor records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tensor_records (
                    tensor_id TEXT PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    world_id TEXT,
                    tensor_blob BLOB NOT NULL,
                    maturity REAL NOT NULL DEFAULT 0.0,
                    training_cycles INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tensor_entity
                ON tensor_records(entity_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tensor_maturity
                ON tensor_records(maturity)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tensor_world
                ON tensor_records(world_id)
            """)

            # Phase 3: Add retrieval columns if missing (migration)
            cursor = conn.execute("PRAGMA table_info(tensor_records)")
            columns = {row[1] for row in cursor.fetchall()}

            if "description" not in columns:
                conn.execute(
                    "ALTER TABLE tensor_records ADD COLUMN description TEXT"
                )
            if "category" not in columns:
                conn.execute(
                    "ALTER TABLE tensor_records ADD COLUMN category TEXT"
                )
            if "embedding_blob" not in columns:
                conn.execute(
                    "ALTER TABLE tensor_records ADD COLUMN embedding_blob BLOB"
                )

            # Index for category lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tensor_category
                ON tensor_records(category)
            """)

            # Version history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tensor_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tensor_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    tensor_blob BLOB NOT NULL,
                    maturity REAL NOT NULL,
                    training_cycles INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(tensor_id, version)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_version_tensor
                ON tensor_versions(tensor_id)
            """)

            # Training jobs table (for Phase 2 parallel training)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_jobs (
                    job_id TEXT PRIMARY KEY,
                    tensor_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    worker_id TEXT,
                    target_maturity REAL NOT NULL DEFAULT 0.95,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    FOREIGN KEY (tensor_id) REFERENCES tensor_records(tensor_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_status
                ON training_jobs(status)
            """)

    def list_tables(self) -> List[str]:
        """List all tables in database."""
        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return [row["name"] for row in cursor.fetchall()]

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def save_tensor(self, record: TensorRecord) -> None:
        """
        Save or update a tensor record.

        If the tensor exists, increments version and creates version entry.
        If new, creates record with version 1.

        Args:
            record: TensorRecord to save
        """
        now = datetime.utcnow().isoformat()

        with self._transaction() as conn:
            # Check if exists
            cursor = conn.execute(
                "SELECT version FROM tensor_records WHERE tensor_id = ?",
                (record.tensor_id,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing - increment version
                new_version = existing["version"] + 1
                conn.execute("""
                    UPDATE tensor_records
                    SET entity_id = ?,
                        world_id = ?,
                        tensor_blob = ?,
                        maturity = ?,
                        training_cycles = ?,
                        version = ?,
                        updated_at = ?,
                        description = ?,
                        category = ?,
                        embedding_blob = ?
                    WHERE tensor_id = ?
                """, (
                    record.entity_id,
                    record.world_id,
                    record.tensor_blob,
                    record.maturity,
                    record.training_cycles,
                    new_version,
                    now,
                    record.description,
                    record.category,
                    record.embedding_blob,
                    record.tensor_id,
                ))
                record.version = new_version
            else:
                # Insert new
                record.version = 1
                conn.execute("""
                    INSERT INTO tensor_records
                    (tensor_id, entity_id, world_id, tensor_blob, maturity,
                     training_cycles, version, created_at, updated_at,
                     description, category, embedding_blob)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.tensor_id,
                    record.entity_id,
                    record.world_id,
                    record.tensor_blob,
                    record.maturity,
                    record.training_cycles,
                    record.version,
                    now,
                    now,
                    record.description,
                    record.category,
                    record.embedding_blob,
                ))

            # Always create version entry
            conn.execute("""
                INSERT INTO tensor_versions
                (tensor_id, version, tensor_blob, maturity, training_cycles, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.tensor_id,
                record.version,
                record.tensor_blob,
                record.maturity,
                record.training_cycles,
                now,
            ))

    def get_tensor(self, tensor_id: str) -> Optional[TensorRecord]:
        """
        Get tensor by ID.

        Args:
            tensor_id: Tensor identifier

        Returns:
            TensorRecord if found, None otherwise
        """
        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT * FROM tensor_records WHERE tensor_id = ?",
                (tensor_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return TensorRecord(
                tensor_id=row["tensor_id"],
                entity_id=row["entity_id"],
                world_id=row["world_id"],
                tensor_blob=row["tensor_blob"],
                maturity=row["maturity"],
                training_cycles=row["training_cycles"],
                version=row["version"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                description=row["description"] if "description" in row.keys() else None,
                category=row["category"] if "category" in row.keys() else None,
                embedding_blob=row["embedding_blob"] if "embedding_blob" in row.keys() else None,
            )

    def delete_tensor(self, tensor_id: str) -> bool:
        """
        Delete tensor and its version history.

        Args:
            tensor_id: Tensor to delete

        Returns:
            True if deleted, False if not found
        """
        with self._transaction() as conn:
            # Delete versions first (foreign key)
            conn.execute(
                "DELETE FROM tensor_versions WHERE tensor_id = ?",
                (tensor_id,)
            )
            cursor = conn.execute(
                "DELETE FROM tensor_records WHERE tensor_id = ?",
                (tensor_id,)
            )
            return cursor.rowcount > 0

    def list_tensors(
        self,
        entity_id: Optional[str] = None,
        world_id: Optional[str] = None,
    ) -> List[TensorRecord]:
        """
        List tensors with optional filtering.

        Args:
            entity_id: Filter by entity
            world_id: Filter by world

        Returns:
            List of matching TensorRecords
        """
        query = "SELECT * FROM tensor_records WHERE 1=1"
        params = []

        if entity_id is not None:
            query += " AND entity_id = ?"
            params.append(entity_id)

        if world_id is not None:
            query += " AND world_id = ?"
            params.append(world_id)

        with self._transaction() as conn:
            cursor = conn.execute(query, params)
            return [
                TensorRecord(
                    tensor_id=row["tensor_id"],
                    entity_id=row["entity_id"],
                    world_id=row["world_id"],
                    tensor_blob=row["tensor_blob"],
                    maturity=row["maturity"],
                    training_cycles=row["training_cycles"],
                    version=row["version"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in cursor.fetchall()
            ]

    # =========================================================================
    # Maturity Queries
    # =========================================================================

    def get_by_maturity(
        self,
        min_maturity: float = 0.0,
        max_maturity: Optional[float] = None,
    ) -> List[TensorRecord]:
        """
        Get tensors by maturity range.

        Args:
            min_maturity: Minimum maturity (inclusive)
            max_maturity: Maximum maturity (exclusive, optional)

        Returns:
            List of tensors in maturity range
        """
        if max_maturity is not None:
            query = """
                SELECT * FROM tensor_records
                WHERE maturity >= ? AND maturity < ?
            """
            params = (min_maturity, max_maturity)
        else:
            query = "SELECT * FROM tensor_records WHERE maturity >= ?"
            params = (min_maturity,)

        with self._transaction() as conn:
            cursor = conn.execute(query, params)
            return [
                TensorRecord(
                    tensor_id=row["tensor_id"],
                    entity_id=row["entity_id"],
                    world_id=row["world_id"],
                    tensor_blob=row["tensor_blob"],
                    maturity=row["maturity"],
                    training_cycles=row["training_cycles"],
                    version=row["version"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in cursor.fetchall()
            ]

    # =========================================================================
    # Version History
    # =========================================================================

    def get_version_history(self, tensor_id: str) -> List[TensorVersion]:
        """
        Get all versions of a tensor.

        Args:
            tensor_id: Tensor identifier

        Returns:
            List of versions in chronological order
        """
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT * FROM tensor_versions
                WHERE tensor_id = ?
                ORDER BY version ASC
            """, (tensor_id,))

            return [
                TensorVersion(
                    tensor_id=row["tensor_id"],
                    version=row["version"],
                    tensor_blob=row["tensor_blob"],
                    maturity=row["maturity"],
                    training_cycles=row["training_cycles"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in cursor.fetchall()
            ]

    def get_tensor_version(
        self,
        tensor_id: str,
        version: int
    ) -> Optional[TensorVersion]:
        """
        Get specific version of a tensor.

        Args:
            tensor_id: Tensor identifier
            version: Version number

        Returns:
            TensorVersion if found, None otherwise
        """
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT * FROM tensor_versions
                WHERE tensor_id = ? AND version = ?
            """, (tensor_id, version))

            row = cursor.fetchone()
            if row is None:
                return None

            return TensorVersion(
                tensor_id=row["tensor_id"],
                version=row["version"],
                tensor_blob=row["tensor_blob"],
                maturity=row["maturity"],
                training_cycles=row["training_cycles"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    def get_training_history(self, tensor_id: str) -> List[TensorVersion]:
        """
        Get training progression history.

        Alias for get_version_history focused on training tracking.

        Args:
            tensor_id: Tensor identifier

        Returns:
            List of versions showing training progression
        """
        return self.get_version_history(tensor_id)

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def save_tensors_batch(self, records: List[TensorRecord]) -> None:
        """
        Save multiple tensors in single transaction.

        All-or-nothing: if any save fails, entire batch rolls back.

        Args:
            records: List of TensorRecords to save

        Raises:
            Exception: If any record fails validation
        """
        now = datetime.utcnow().isoformat()

        with self._transaction() as conn:
            for record in records:
                # Validate required fields
                if record.tensor_blob is None:
                    raise ValueError(
                        f"tensor_blob is required for {record.tensor_id}"
                    )

                # Check if exists
                cursor = conn.execute(
                    "SELECT version FROM tensor_records WHERE tensor_id = ?",
                    (record.tensor_id,)
                )
                existing = cursor.fetchone()

                if existing:
                    new_version = existing["version"] + 1
                    conn.execute("""
                        UPDATE tensor_records
                        SET entity_id = ?, world_id = ?, tensor_blob = ?,
                            maturity = ?, training_cycles = ?, version = ?,
                            updated_at = ?
                        WHERE tensor_id = ?
                    """, (
                        record.entity_id, record.world_id, record.tensor_blob,
                        record.maturity, record.training_cycles, new_version,
                        now, record.tensor_id,
                    ))
                    record.version = new_version
                else:
                    record.version = 1
                    conn.execute("""
                        INSERT INTO tensor_records
                        (tensor_id, entity_id, world_id, tensor_blob, maturity,
                         training_cycles, version, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.tensor_id, record.entity_id, record.world_id,
                        record.tensor_blob, record.maturity, record.training_cycles,
                        record.version, now, now,
                    ))

                # Create version entry
                conn.execute("""
                    INSERT INTO tensor_versions
                    (tensor_id, version, tensor_blob, maturity, training_cycles,
                     created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    record.tensor_id, record.version, record.tensor_blob,
                    record.maturity, record.training_cycles, now,
                ))

    def get_tensors_batch(self, tensor_ids: List[str]) -> List[TensorRecord]:
        """
        Get multiple tensors by IDs.

        Args:
            tensor_ids: List of tensor identifiers

        Returns:
            List of found TensorRecords (may be fewer than requested)
        """
        if not tensor_ids:
            return []

        placeholders = ",".join("?" * len(tensor_ids))
        query = f"SELECT * FROM tensor_records WHERE tensor_id IN ({placeholders})"

        with self._transaction() as conn:
            cursor = conn.execute(query, tensor_ids)
            return [
                TensorRecord(
                    tensor_id=row["tensor_id"],
                    entity_id=row["entity_id"],
                    world_id=row["world_id"],
                    tensor_blob=row["tensor_blob"],
                    maturity=row["maturity"],
                    training_cycles=row["training_cycles"],
                    version=row["version"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in cursor.fetchall()
            ]

    # =========================================================================
    # Optimistic Locking
    # =========================================================================

    def save_tensor_with_lock(
        self,
        record: TensorRecord,
        expected_version: int
    ) -> bool:
        """
        Save tensor only if version matches (optimistic locking).

        Use this for concurrent access scenarios to detect conflicts.

        Args:
            record: TensorRecord to save
            expected_version: Version we expect the record to be at

        Returns:
            True if save succeeded, False if version mismatch (conflict)
        """
        now = datetime.utcnow().isoformat()

        with self._transaction() as conn:
            # Check current version
            cursor = conn.execute(
                "SELECT version FROM tensor_records WHERE tensor_id = ?",
                (record.tensor_id,)
            )
            row = cursor.fetchone()

            if row is None:
                # New record - expected_version should be 0 for new
                if expected_version != 0:
                    return False
                record.version = 1
                conn.execute("""
                    INSERT INTO tensor_records
                    (tensor_id, entity_id, world_id, tensor_blob, maturity,
                     training_cycles, version, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.tensor_id, record.entity_id, record.world_id,
                    record.tensor_blob, record.maturity, record.training_cycles,
                    record.version, now, now,
                ))
            else:
                current_version = row["version"]
                if current_version != expected_version:
                    # Version mismatch - conflict detected
                    return False

                new_version = current_version + 1
                conn.execute("""
                    UPDATE tensor_records
                    SET entity_id = ?, world_id = ?, tensor_blob = ?,
                        maturity = ?, training_cycles = ?, version = ?,
                        updated_at = ?
                    WHERE tensor_id = ? AND version = ?
                """, (
                    record.entity_id, record.world_id, record.tensor_blob,
                    record.maturity, record.training_cycles, new_version,
                    now, record.tensor_id, expected_version,
                ))
                record.version = new_version

            # Create version entry
            conn.execute("""
                INSERT INTO tensor_versions
                (tensor_id, version, tensor_blob, maturity, training_cycles,
                 created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.tensor_id, record.version, record.tensor_blob,
                record.maturity, record.training_cycles, now,
            ))

            return True

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> dict:
        """
        Get database statistics.

        Returns:
            dict with counts and aggregates
        """
        with self._transaction() as conn:
            stats = {}

            # Total tensors
            cursor = conn.execute("SELECT COUNT(*) as count FROM tensor_records")
            stats["total_tensors"] = cursor.fetchone()["count"]

            # By maturity
            cursor = conn.execute("""
                SELECT
                    SUM(CASE WHEN maturity >= 0.95 THEN 1 ELSE 0 END) as operational,
                    SUM(CASE WHEN maturity < 0.95 THEN 1 ELSE 0 END) as training,
                    AVG(maturity) as avg_maturity
                FROM tensor_records
            """)
            row = cursor.fetchone()
            stats["operational_count"] = row["operational"] or 0
            stats["training_count"] = row["training"] or 0
            stats["avg_maturity"] = row["avg_maturity"] or 0.0

            # Total versions
            cursor = conn.execute("SELECT COUNT(*) as count FROM tensor_versions")
            stats["total_versions"] = cursor.fetchone()["count"]

            return stats
