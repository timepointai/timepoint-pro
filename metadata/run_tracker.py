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
from pydantic import BaseModel, ConfigDict, Field
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

    # LLM-generated summary
    summary: Optional[str] = None
    summary_generated_at: Optional[datetime] = None

    # Narrative exports
    narrative_exports: Optional[Dict[str, str]] = Field(
        default=None,
        description="Paths to generated narrative files: {format: path}"
    )
    narrative_export_generated_at: Optional[datetime] = None

    # M1+M17: Database v2 - Fidelity-Temporal Strategy Tracking
    schema_version: str = "2.0"  # Database version marker
    fidelity_strategy_json: Optional[str] = Field(
        default=None,
        description="JSON-serialized FidelityTemporalStrategy from TemporalAgent"
    )
    fidelity_distribution: Optional[str] = Field(
        default=None,
        description="JSON dict of {ResolutionLevel: count} for this run"
    )
    actual_tokens_used: Optional[float] = Field(
        default=None,
        description="Actual token usage (may differ from budget)"
    )
    token_budget_compliance: Optional[float] = Field(
        default=None,
        description="actual_tokens / token_budget ratio"
    )
    fidelity_efficiency_score: Optional[float] = Field(
        default=None,
        description="Quality metric: output_quality / tokens_used"
    )

    model_config = ConfigDict(use_enum_values=True)


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
                error_message TEXT,
                summary TEXT,
                summary_generated_at TEXT,
                schema_version TEXT DEFAULT '2.0',
                fidelity_strategy_json TEXT,
                fidelity_distribution TEXT,
                actual_tokens_used REAL,
                token_budget_compliance REAL,
                fidelity_efficiency_score REAL
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

        # Migrate database schema if needed
        self._migrate_database(conn)

        conn.close()

    def _migrate_database(self, conn: sqlite3.Connection):
        """
        Migrate database schema to add new columns if they don't exist.

        This ensures backward compatibility with existing databases.
        """
        cursor = conn.cursor()

        # Check if summary columns exist in runs table
        cursor.execute("PRAGMA table_info(runs)")
        columns = {row[1] for row in cursor.fetchall()}  # row[1] is column name

        # Add summary column if missing
        if 'summary' not in columns:
            print("📝 Migrating database: Adding 'summary' column to runs table...")
            cursor.execute("ALTER TABLE runs ADD COLUMN summary TEXT")
            conn.commit()
            print("   ✓ Summary column added")

        # Add summary_generated_at column if missing
        if 'summary_generated_at' not in columns:
            print("📝 Migrating database: Adding 'summary_generated_at' column to runs table...")
            cursor.execute("ALTER TABLE runs ADD COLUMN summary_generated_at TEXT")
            conn.commit()
            print("   ✓ Summary timestamp column added")

        # Add narrative_exports column if missing
        if 'narrative_exports' not in columns:
            print("📝 Migrating database: Adding 'narrative_exports' column to runs table...")
            cursor.execute("ALTER TABLE runs ADD COLUMN narrative_exports TEXT")
            conn.commit()
            print("   ✓ Narrative exports column added")

        # Add narrative_export_generated_at column if missing
        if 'narrative_export_generated_at' not in columns:
            print("📝 Migrating database: Adding 'narrative_export_generated_at' column to runs table...")
            cursor.execute("ALTER TABLE runs ADD COLUMN narrative_export_generated_at TEXT")
            conn.commit()
            print("   ✓ Narrative export timestamp column added")

        # M1+M17: Database v2 - Add fidelity-temporal strategy tracking columns
        v2_columns = {
            'schema_version': "TEXT DEFAULT '2.0'",
            'fidelity_strategy_json': "TEXT",
            'fidelity_distribution': "TEXT",
            'actual_tokens_used': "REAL",
            'token_budget_compliance': "REAL",
            'fidelity_efficiency_score': "REAL"
        }

        for col_name, col_type in v2_columns.items():
            if col_name not in columns:
                print(f"📝 Migrating database v1→v2: Adding '{col_name}' column...")
                cursor.execute(f"ALTER TABLE runs ADD COLUMN {col_name} {col_type}")
                conn.commit()
                print(f"   ✓ {col_name} column added")

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
        error_message: Optional[str] = None,
        # M1+M17: Database v2 - Fidelity metrics
        fidelity_strategy_json: Optional[str] = None,
        fidelity_distribution: Optional[str] = None,
        actual_tokens_used: Optional[float] = None,
        token_budget_compliance: Optional[float] = None,
        fidelity_efficiency_score: Optional[float] = None
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
                error_message = ?,
                fidelity_strategy_json = ?,
                fidelity_distribution = ?,
                actual_tokens_used = ?,
                token_budget_compliance = ?,
                fidelity_efficiency_score = ?
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
            fidelity_strategy_json,
            fidelity_distribution,
            actual_tokens_used,
            token_budget_compliance,
            fidelity_efficiency_score,
            run_id
        ))

        conn.commit()
        conn.close()

        return self.get_run(run_id)

    def update_summary(
        self,
        run_id: str,
        summary: str
    ):
        """
        Update run with LLM-generated summary.

        Args:
            run_id: Run to update
            summary: Generated summary text
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE runs SET
                summary = ?,
                summary_generated_at = ?
            WHERE run_id = ?
        """, (
            summary,
            datetime.now().isoformat(),
            run_id
        ))

        conn.commit()
        conn.close()

    def update_narrative_exports(
        self,
        run_id: str,
        narrative_exports: Dict[str, str]
    ):
        """
        Update run with narrative export file paths.

        Args:
            run_id: Run to update
            narrative_exports: Dictionary mapping format to file path
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE runs SET
                narrative_exports = ?,
                narrative_export_generated_at = ?
            WHERE run_id = ?
        """, (
            json.dumps(narrative_exports),
            datetime.now().isoformat(),
            run_id
        ))

        conn.commit()
        conn.close()

    def save_metadata(self, metadata: RunMetadata):
        """
        Save or update complete metadata object.

        Args:
            metadata: RunMetadata object to save
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if run exists
        cursor.execute("SELECT run_id FROM runs WHERE run_id = ?", (metadata.run_id,))
        exists = cursor.fetchone() is not None

        if exists:
            # Update existing run
            cursor.execute("""
                UPDATE runs SET
                    template_id = ?,
                    started_at = ?,
                    completed_at = ?,
                    causal_mode = ?,
                    max_entities = ?,
                    max_timepoints = ?,
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
                    error_message = ?,
                    summary = ?,
                    summary_generated_at = ?,
                    narrative_exports = ?,
                    narrative_export_generated_at = ?,
                    fidelity_strategy_json = ?,
                    fidelity_distribution = ?,
                    actual_tokens_used = ?,
                    token_budget_compliance = ?,
                    fidelity_efficiency_score = ?
                WHERE run_id = ?
            """, (
                metadata.template_id,
                metadata.started_at.isoformat(),
                metadata.completed_at.isoformat() if metadata.completed_at else None,
                metadata.causal_mode.value if hasattr(metadata.causal_mode, 'value') else str(metadata.causal_mode),
                metadata.max_entities,
                metadata.max_timepoints,
                metadata.entities_created,
                metadata.timepoints_created,
                metadata.training_examples,
                metadata.cost_usd,
                metadata.llm_calls,
                metadata.tokens_used,
                metadata.duration_seconds,
                metadata.oxen_repo_url,
                metadata.oxen_dataset_url,
                metadata.status,
                metadata.error_message,
                metadata.summary,
                metadata.summary_generated_at.isoformat() if metadata.summary_generated_at else None,
                json.dumps(metadata.narrative_exports) if metadata.narrative_exports else None,
                metadata.narrative_export_generated_at.isoformat() if metadata.narrative_export_generated_at else None,
                metadata.fidelity_strategy_json,
                metadata.fidelity_distribution,
                metadata.actual_tokens_used,
                metadata.token_budget_compliance,
                metadata.fidelity_efficiency_score,
                metadata.run_id
            ))
        else:
            # Insert new run
            cursor.execute("""
                INSERT INTO runs (
                    run_id, template_id, started_at, completed_at, causal_mode,
                    max_entities, max_timepoints, entities_created, timepoints_created,
                    training_examples, cost_usd, llm_calls, tokens_used, duration_seconds,
                    oxen_repo_url, oxen_dataset_url, status, error_message,
                    summary, summary_generated_at, narrative_exports, narrative_export_generated_at,
                    fidelity_strategy_json, fidelity_distribution, actual_tokens_used,
                    token_budget_compliance, fidelity_efficiency_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.run_id,
                metadata.template_id,
                metadata.started_at.isoformat(),
                metadata.completed_at.isoformat() if metadata.completed_at else None,
                metadata.causal_mode.value if hasattr(metadata.causal_mode, 'value') else str(metadata.causal_mode),
                metadata.max_entities,
                metadata.max_timepoints,
                metadata.entities_created,
                metadata.timepoints_created,
                metadata.training_examples,
                metadata.cost_usd,
                metadata.llm_calls,
                metadata.tokens_used,
                metadata.duration_seconds,
                metadata.oxen_repo_url,
                metadata.oxen_dataset_url,
                metadata.status,
                metadata.error_message,
                metadata.summary,
                metadata.summary_generated_at.isoformat() if metadata.summary_generated_at else None,
                json.dumps(metadata.narrative_exports) if metadata.narrative_exports else None,
                metadata.narrative_export_generated_at.isoformat() if metadata.narrative_export_generated_at else None,
                metadata.fidelity_strategy_json,
                metadata.fidelity_distribution,
                metadata.actual_tokens_used,
                metadata.token_budget_compliance,
                metadata.fidelity_efficiency_score
            ))

        conn.commit()
        conn.close()

    def get_run(self, run_id: str) -> RunMetadata:
        """Retrieve complete run metadata"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Use Row factory for column-name access
        cursor = conn.cursor()

        # Get run with explicit column names to avoid migration ordering issues
        cursor.execute("""
            SELECT
                run_id, template_id, started_at, completed_at, causal_mode,
                max_entities, max_timepoints, entities_created, timepoints_created,
                training_examples, cost_usd, llm_calls, tokens_used, duration_seconds,
                oxen_repo_url, oxen_dataset_url, status, error_message,
                summary, summary_generated_at, narrative_exports, narrative_export_generated_at,
                schema_version, fidelity_strategy_json, fidelity_distribution,
                actual_tokens_used, token_budget_compliance, fidelity_efficiency_score
            FROM runs WHERE run_id = ?
        """, (run_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Run {run_id} not found")

        # Get mechanisms used
        cursor.execute("""
            SELECT DISTINCT mechanism FROM mechanism_usage WHERE run_id = ?
        """, (run_id,))
        mechanisms_used = {r[0] for r in cursor.fetchall()}

        conn.close()

        # Parse narrative exports if present
        narrative_exports = None
        narrative_exports_raw = row['narrative_exports']
        if narrative_exports_raw:
            try:
                narrative_exports = json.loads(narrative_exports_raw)
            except:
                narrative_exports = None

        # Build metadata using column names (not indices) for robustness
        metadata = RunMetadata(
            run_id=row['run_id'],
            template_id=row['template_id'],
            started_at=datetime.fromisoformat(row['started_at']),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            causal_mode=TemporalMode(row['causal_mode']),
            max_entities=row['max_entities'],
            max_timepoints=row['max_timepoints'],
            entities_created=row['entities_created'],
            timepoints_created=row['timepoints_created'],
            training_examples=row['training_examples'],
            cost_usd=row['cost_usd'],
            llm_calls=row['llm_calls'],
            tokens_used=row['tokens_used'],
            duration_seconds=row['duration_seconds'],
            oxen_repo_url=row['oxen_repo_url'],
            oxen_dataset_url=row['oxen_dataset_url'],
            status=row['status'],
            error_message=row['error_message'],
            summary=row['summary'],
            summary_generated_at=datetime.fromisoformat(row['summary_generated_at']) if row['summary_generated_at'] else None,
            narrative_exports=narrative_exports,
            narrative_export_generated_at=datetime.fromisoformat(row['narrative_export_generated_at']) if row['narrative_export_generated_at'] else None,
            # M1+M17: Database v2 - Fidelity metrics
            schema_version=row['schema_version'] if row['schema_version'] else "2.0",
            fidelity_strategy_json=row['fidelity_strategy_json'],
            fidelity_distribution=row['fidelity_distribution'],
            actual_tokens_used=row['actual_tokens_used'],
            token_budget_compliance=row['token_budget_compliance'],
            fidelity_efficiency_score=row['fidelity_efficiency_score'],
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
