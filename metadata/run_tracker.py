"""
Run Tracker - Comprehensive metadata tracking for E2E workflow runs

Tracks:
- Mechanisms used (M1-M17)
- Resolution assignments (fidelity diversity)
- Validations executed
- Costs, duration, training examples
- Oxen upload URLs
"""

from typing import Dict, List, Set, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from pathlib import Path
import json
import sqlite3
from schemas import ResolutionLevel, TemporalMode

# List of all 17 mechanisms
ALL_MECHANISMS = [
    "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9",
    "M10", "M11", "M12", "M13", "M14", "M15", "M16", "M17"
]


class MechanismUsage(BaseModel):
    """Record of a mechanism being invoked"""
    mechanism: str  # M1, M2, etc.
    function_name: str
    timestamp: datetime
    context: Dict[str, Any] = Field(default_factory=dict)


class ResolutionAssignment(BaseModel):
    """Record of resolution level assigned to an entity"""
    entity_id: str
    resolution: ResolutionLevel
    timepoint_id: str
    timestamp: datetime


class ValidationRecord(BaseModel):
    """Record of a validation being executed"""
    validator_name: str
    passed: bool
    timestamp: datetime
    message: Optional[str] = None
    violations: List[str] = Field(default_factory=list)


class RunMetadata(BaseModel):
    """Complete metadata for a single E2E workflow run"""
    run_id: str
    template_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Configuration
    causal_mode: TemporalMode
    max_entities: int
    max_timepoints: int

    # Mechanism tracking
    mechanisms_used: Set[str] = Field(default_factory=set)
    mechanism_usage_log: List[MechanismUsage] = Field(default_factory=list)

    # Resolution diversity
    resolution_assignments: List[ResolutionAssignment] = Field(default_factory=list)

    # Validations
    validations: List[ValidationRecord] = Field(default_factory=list)

    # Results
    entities_created: int = 0
    timepoints_created: int = 0
    training_examples: int = 0

    # Cost tracking
    cost_usd: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0

    # Duration
    duration_seconds: Optional[float] = None

    # Oxen upload
    oxen_repo_url: Optional[str] = None
    oxen_dataset_url: Optional[str] = None

    # Status
    status: str = "running"  # running, completed, failed
    error_message: Optional[str] = None

    class Config:
        use_enum_values = True


class MetadataManager:
    """
    Manages metadata tracking for all workflow runs.

    Stores metadata in SQLite for persistence and fast querying.
    """

    def __init__(self, db_path: str = "metadata/runs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with necessary tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                causal_mode TEXT NOT NULL,
                max_entities INTEGER,
                max_timepoints INTEGER,
                entities_created INTEGER DEFAULT 0,
                timepoints_created INTEGER DEFAULT 0,
                training_examples INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                llm_calls INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                duration_seconds REAL,
                oxen_repo_url TEXT,
                oxen_dataset_url TEXT,
                status TEXT DEFAULT 'running',
                error_message TEXT
            )
        """)

        # Mechanism usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mechanism_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                mechanism TEXT NOT NULL,
                function_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                context TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)

        # Resolution assignments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resolution_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                resolution TEXT NOT NULL,
                timepoint_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)

        # Validations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                validator_name TEXT NOT NULL,
                passed BOOLEAN NOT NULL,
                timestamp TEXT NOT NULL,
                message TEXT,
                violations TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)

        conn.commit()
        conn.close()

    def start_run(
        self,
        run_id: str,
        template_id: str,
        causal_mode: TemporalMode,
        max_entities: int,
        max_timepoints: int
    ) -> RunMetadata:
        """Start tracking a new run"""
        metadata = RunMetadata(
            run_id=run_id,
            template_id=template_id,
            started_at=datetime.now(),
            causal_mode=causal_mode,
            max_entities=max_entities,
            max_timepoints=max_timepoints
        )

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO runs (
                run_id, template_id, started_at, causal_mode,
                max_entities, max_timepoints
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            template_id,
            metadata.started_at.isoformat(),
            causal_mode.value,
            max_entities,
            max_timepoints
        ))

        conn.commit()
        conn.close()

        return metadata

    def record_mechanism(
        self,
        run_id: str,
        mechanism: str,
        function_name: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Record mechanism usage"""
        usage = MechanismUsage(
            mechanism=mechanism,
            function_name=function_name,
            timestamp=datetime.now(),
            context=context or {}
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO mechanism_usage (
                run_id, mechanism, function_name, timestamp, context
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            run_id,
            mechanism,
            function_name,
            usage.timestamp.isoformat(),
            json.dumps(usage.context)
        ))

        conn.commit()
        conn.close()

    def record_resolution(
        self,
        run_id: str,
        entity_id: str,
        resolution: ResolutionLevel,
        timepoint_id: str
    ):
        """Record resolution assignment"""
        assignment = ResolutionAssignment(
            entity_id=entity_id,
            resolution=resolution,
            timepoint_id=timepoint_id,
            timestamp=datetime.now()
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO resolution_assignments (
                run_id, entity_id, resolution, timepoint_id, timestamp
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            run_id,
            entity_id,
            resolution.value,
            timepoint_id,
            assignment.timestamp.isoformat()
        ))

        conn.commit()
        conn.close()

    def record_validation(
        self,
        run_id: str,
        validator_name: str,
        passed: bool,
        message: Optional[str] = None,
        violations: Optional[List[str]] = None
    ):
        """Record validation execution"""
        record = ValidationRecord(
            validator_name=validator_name,
            passed=passed,
            timestamp=datetime.now(),
            message=message,
            violations=violations or []
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO validations (
                run_id, validator_name, passed, timestamp, message, violations
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            validator_name,
            passed,
            record.timestamp.isoformat(),
            message,
            json.dumps(violations or [])
        ))

        conn.commit()
        conn.close()

    def complete_run(
        self,
        run_id: str,
        entities_created: int,
        timepoints_created: int,
        training_examples: int,
        cost_usd: float,
        llm_calls: int,
        tokens_used: int,
        oxen_repo_url: Optional[str] = None,
        oxen_dataset_url: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> RunMetadata:
        """Complete a run and finalize metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get start time
        cursor.execute("SELECT started_at FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Run {run_id} not found")

        started_at = datetime.fromisoformat(row[0])
        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        status = "failed" if error_message else "completed"

        # Update run
        cursor.execute("""
            UPDATE runs SET
                completed_at = ?,
                entities_created = ?,
                timepoints_created = ?,
                training_examples = ?,
                cost_usd = ?,
                llm_calls = ?,
                tokens_used = ?,
                duration_seconds = ?,
                oxen_repo_url = ?,
                oxen_dataset_url = ?,
                status = ?,
                error_message = ?
            WHERE run_id = ?
        """, (
            completed_at.isoformat(),
            entities_created,
            timepoints_created,
            training_examples,
            cost_usd,
            llm_calls,
            tokens_used,
            duration,
            oxen_repo_url,
            oxen_dataset_url,
            status,
            error_message,
            run_id
        ))

        conn.commit()
        conn.close()

        return self.get_run(run_id)

    def get_run(self, run_id: str) -> RunMetadata:
        """Retrieve complete run metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get run
        cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Run {run_id} not found")

        # Get mechanisms used
        cursor.execute("""
            SELECT DISTINCT mechanism FROM mechanism_usage WHERE run_id = ?
        """, (run_id,))
        mechanisms_used = {row[0] for row in cursor.fetchall()}

        conn.close()

        # Build metadata
        metadata = RunMetadata(
            run_id=row[0],
            template_id=row[1],
            started_at=datetime.fromisoformat(row[2]),
            completed_at=datetime.fromisoformat(row[3]) if row[3] else None,
            causal_mode=TemporalMode(row[4]),
            max_entities=row[5],
            max_timepoints=row[6],
            entities_created=row[7],
            timepoints_created=row[8],
            training_examples=row[9],
            cost_usd=row[10],
            llm_calls=row[11],
            tokens_used=row[12],
            duration_seconds=row[13],
            oxen_repo_url=row[14],
            oxen_dataset_url=row[15],
            status=row[16],
            error_message=row[17],
            mechanisms_used=mechanisms_used
        )

        return metadata

    def get_all_runs(self, template_id: Optional[str] = None) -> List[RunMetadata]:
        """Get all runs, optionally filtered by template"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if template_id:
            cursor.execute("SELECT run_id FROM runs WHERE template_id = ?", (template_id,))
        else:
            cursor.execute("SELECT run_id FROM runs")

        run_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        return [self.get_run(run_id) for run_id in run_ids]
