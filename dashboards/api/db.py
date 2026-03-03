"""
Database query functions for Timepoint Dashboard API

Provides efficient querying with filtering, sorting, and pagination.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class TimepointDB:
    """Database interface for querying Timepoint runs."""

    def __init__(self, db_path: str = "../../metadata/runs.db"):
        self.db_path = Path(__file__).parent / db_path
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def query_runs(
        self,
        template: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        min_cost: float | None = None,
        max_cost: float | None = None,
        causal_mode: str | None = None,
        mechanisms: list[str] | None = None,
        min_entities: int | None = None,
        min_timepoints: int | None = None,
        sort_by: str = "started_at",
        order: str = "DESC",
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """
        Query runs with filtering, sorting, and pagination.

        Returns:
            Tuple of (results, total_count)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Build WHERE clause
        where_clauses = []
        params = []

        if template:
            where_clauses.append("template_id = ?")
            params.append(template)

        if status:
            where_clauses.append("status = ?")
            params.append(status)

        if date_from:
            where_clauses.append("started_at >= ?")
            params.append(date_from)

        if date_to:
            where_clauses.append("started_at <= ?")
            params.append(date_to)

        if min_cost is not None:
            where_clauses.append("cost_usd >= ?")
            params.append(min_cost)

        if max_cost is not None:
            where_clauses.append("cost_usd <= ?")
            params.append(max_cost)

        if causal_mode:
            where_clauses.append("causal_mode = ?")
            params.append(causal_mode)

        if min_entities is not None:
            where_clauses.append("entities_created >= ?")
            params.append(min_entities)

        if min_timepoints is not None:
            where_clauses.append("timepoints_created >= ?")
            params.append(min_timepoints)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Validate sort_by and order against whitelist to prevent SQL injection
        allowed_sort_columns = {
            "started_at",
            "completed_at",
            "template_id",
            "causal_mode",
            "entities_created",
            "timepoints_created",
            "cost_usd",
            "status",
            "duration_seconds",
            "run_id",
        }
        if sort_by not in allowed_sort_columns:
            sort_by = "started_at"
        if order.upper() not in ("ASC", "DESC"):
            order = "DESC"

        # Handle mechanism filtering (requires subquery)
        if mechanisms:
            mechanism_placeholders = ",".join(["?"] * len(mechanisms))
            where_sql += f"""
                AND run_id IN (
                    SELECT DISTINCT run_id
                    FROM mechanism_usage
                    WHERE mechanism IN ({mechanism_placeholders})
                )
            """  # nosec B608 - placeholders are ?-only, values go through params
            params.extend(mechanisms)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM runs WHERE {where_sql}"  # nosec B608 - where_sql uses ? params
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        # Get paginated results
        offset = (page - 1) * limit
        # nosec B608 - sort_by/order validated above, where_sql uses ? parameterized placeholders
        results_query = f"""
            SELECT
                run_id, template_id, started_at, completed_at,
                causal_mode, entities_created, timepoints_created,
                cost_usd, status, duration_seconds, error_message
            FROM runs
            WHERE {where_sql}
            ORDER BY {sort_by} {order}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor.execute(results_query, params)
        rows = cursor.fetchall()

        # Get mechanisms for each run
        results = []
        for row in rows:
            run_dict = dict(row)

            # Get mechanisms used
            cursor.execute(
                """
                SELECT DISTINCT mechanism, COUNT(*) as count
                FROM mechanism_usage
                WHERE run_id = ?
                GROUP BY mechanism
            """,
                (run_dict["run_id"],),
            )

            mechanisms_used = {m[0]: m[1] for m in cursor.fetchall()}
            run_dict["mechanisms_used"] = mechanisms_used

            results.append(run_dict)

        conn.close()
        return results, total_count

    def get_run_details(self, run_id: str) -> dict | None:
        """Get full details for a specific run."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        run_dict = dict(row)

        # Parse JSON fields from schema 2.0
        if "fidelity_strategy_json" in run_dict and run_dict["fidelity_strategy_json"]:
            try:
                run_dict["fidelity_strategy_json"] = json.loads(run_dict["fidelity_strategy_json"])
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if parsing fails

        if "fidelity_distribution" in run_dict and run_dict["fidelity_distribution"]:
            try:
                run_dict["fidelity_distribution"] = json.loads(run_dict["fidelity_distribution"])
            except (json.JSONDecodeError, TypeError):
                pass

        # Get mechanisms
        cursor.execute(
            """
            SELECT mechanism, function_name, timestamp, context
            FROM mechanism_usage
            WHERE run_id = ?
            ORDER BY timestamp
        """,
            (run_id,),
        )
        run_dict["mechanism_usage"] = [dict(m) for m in cursor.fetchall()]

        # Get resolution assignments
        cursor.execute(
            """
            SELECT entity_id, resolution, timepoint_id, timestamp
            FROM resolution_assignments
            WHERE run_id = ?
        """,
            (run_id,),
        )
        run_dict["resolution_assignments"] = [dict(r) for r in cursor.fetchall()]

        # Get validations
        cursor.execute(
            """
            SELECT validator_name, passed, timestamp, message, violations
            FROM validations
            WHERE run_id = ?
        """,
            (run_id,),
        )
        run_dict["validations"] = [dict(v) for v in cursor.fetchall()]

        conn.close()
        return run_dict

    def get_templates(self) -> list[str]:
        """Get list of all unique templates."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT template_id FROM runs ORDER BY template_id")
        templates = [row[0] for row in cursor.fetchall()]

        conn.close()
        return templates

    def get_mechanisms(self) -> dict[str, int]:
        """Get all mechanisms with total usage counts."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT mechanism, COUNT(*) as count
            FROM mechanism_usage
            GROUP BY mechanism
            ORDER BY mechanism
        """)

        mechanisms = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return mechanisms

    def get_meta_analytics(self) -> dict[str, Any]:
        """Get aggregate statistics across all runs."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Basic metrics
        cursor.execute("""
            SELECT
                COUNT(*) as total_runs,
                SUM(cost_usd) as total_cost,
                AVG(cost_usd) as avg_cost,
                SUM(entities_created) as total_entities,
                SUM(timepoints_created) as total_timepoints,
                AVG(duration_seconds) as avg_duration,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_runs,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs
            FROM runs
        """)
        metrics = dict(cursor.fetchone())

        # Success rate
        if metrics["total_runs"] > 0:
            metrics["success_rate"] = metrics["completed_runs"] / metrics["total_runs"]
        else:
            metrics["success_rate"] = 0.0

        # Template distribution
        cursor.execute("""
            SELECT template_id, COUNT(*) as count
            FROM runs
            GROUP BY template_id
            ORDER BY count DESC
            LIMIT 10
        """)
        metrics["top_templates"] = [dict(row) for row in cursor.fetchall()]

        # Cost over time (by day)
        cursor.execute("""
            SELECT
                DATE(started_at) as date,
                SUM(cost_usd) as total_cost,
                COUNT(*) as run_count
            FROM runs
            WHERE started_at IS NOT NULL
            GROUP BY DATE(started_at)
            ORDER BY date DESC
            LIMIT 30
        """)
        metrics["cost_over_time"] = [dict(row) for row in cursor.fetchall()]

        # Mechanism usage heatmap data
        cursor.execute("""
            SELECT
                m1.mechanism as mechanism1,
                m2.mechanism as mechanism2,
                COUNT(DISTINCT m1.run_id) as co_occurrence
            FROM mechanism_usage m1
            JOIN mechanism_usage m2 ON m1.run_id = m2.run_id
            WHERE m1.mechanism < m2.mechanism
            GROUP BY m1.mechanism, m2.mechanism
            ORDER BY co_occurrence DESC
            LIMIT 50
        """)
        metrics["mechanism_co_occurrence"] = [dict(row) for row in cursor.fetchall()]

        # Causal mode distribution
        cursor.execute("""
            SELECT causal_mode, COUNT(*) as count
            FROM runs
            GROUP BY causal_mode
        """)
        metrics["causal_mode_distribution"] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return metrics

    def get_narrative(self, run_id: str) -> dict | None:
        """Load or generate narrative JSON for a run.

        First tries to load from exported file, then falls back to generating
        from database if the run has data.
        """
        try:
            # Try to load from exported file first
            parts = run_id.split("_")
            if len(parts) >= 3:
                timestamp = f"{parts[1]}_{parts[2]}"  # YYYYMMDD_HHMMSS
                datasets_path = self.db_path.parent.parent / "datasets"

                for template_dir in datasets_path.iterdir():
                    if not template_dir.is_dir():
                        continue

                    narrative_path = template_dir / f"narrative_{timestamp}.json"
                    if narrative_path.exists():
                        with open(narrative_path) as f:
                            narrative = json.load(f)
                            # Map 'timeline' to 'timepoints' for compatibility
                            if "timeline" in narrative and "timepoints" not in narrative:
                                narrative["timepoints"] = narrative["timeline"]
                            return narrative

            # Fall back to generating from database
            return self._generate_narrative_from_db(run_id)

        except Exception as e:
            print(f"Error loading/generating narrative for {run_id}: {e}")
            return None

    def _generate_narrative_from_db(self, run_id: str) -> dict | None:
        """Generate narrative structure from database data.

        Since the database doesn't store full timepoint timeline data, this generates
        synthetic timepoints based on the timepoints_created counter and available
        resolution assignments.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get run info
        cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        run = cursor.fetchone()
        if not run:
            conn.close()
            return None

        # Get resolution assignments
        cursor.execute(
            """
            SELECT entity_id, resolution, timepoint_id, timestamp
            FROM resolution_assignments
            WHERE run_id = ?
            ORDER BY timestamp
        """,
            (run_id,),
        )
        assignments = cursor.fetchall()

        # Build entities map from resolution assignments
        entities_map = {}
        for assignment in assignments:
            entity_id = assignment["entity_id"]
            if entity_id not in entities_map:
                entities_map[entity_id] = {
                    "entity_id": entity_id,
                    "resolution": assignment["resolution"],
                    "timepoints": [],
                }

        # Get all entities if we have none from assignments
        # (for runs that completed but didn't track resolution assignments)
        if not entities_map:
            entities_map = {
                "entity_placeholder": {
                    "entity_id": "entity_placeholder",
                    "resolution": "unknown",
                    "timepoints": [],
                }
            }

        entity_list = list(entities_map.keys())

        # Generate synthetic timepoints based on timepoints_created counter
        # Since DB doesn't store the full timeline, we create placeholder timepoints
        timepoints_created = run["timepoints_created"] or 1
        started_at = datetime.fromisoformat(run["started_at"])
        completed_at = (
            datetime.fromisoformat(run["completed_at"]) if run["completed_at"] else started_at
        )

        # Calculate time interval between timepoints
        total_duration = (completed_at - started_at).total_seconds()
        interval_seconds = total_duration / max(timepoints_created, 1)

        timepoint_list = []
        for i in range(timepoints_created):
            tp_timestamp = started_at + timedelta(seconds=interval_seconds * i)

            timepoint_list.append(
                {
                    "timepoint_id": f"tp_{i + 1:03d}"
                    if timepoints_created > 1
                    else (assignments[0]["timepoint_id"] if assignments else "tp_001"),
                    "timestamp": tp_timestamp.isoformat(),
                    "event_description": f"Timepoint {i + 1}/{timepoints_created}"
                    if timepoints_created > 1
                    else f"Timepoint {assignments[0]['timepoint_id'] if assignments else 'tp_001'}",
                    "entities_present": entity_list,
                    "importance": 0.5,
                    "dialog_turn_count": 0,
                }
            )

        conn.close()

        # Build narrative structure
        narrative = {
            "run_id": run_id,
            "template_id": run["template_id"],
            "causal_mode": run["causal_mode"],
            "timepoints": timepoint_list,
            "characters": [
                {"entity_id": eid, "resolution": data["resolution"], "relationships": {}}
                for eid, data in entities_map.items()
            ],
            "executive_summary": f"Auto-generated summary: {run['template_id']} run with {len(entities_map)} entities across {timepoints_created} timepoints. Status: {run['status']}.",
            "dialogs": [],
            "_source": "database",  # Flag to indicate this was generated, not exported
        }

        return narrative

    def get_screenplay(self, run_id: str) -> str | None:
        """Load Fountain screenplay for a run."""
        try:
            parts = run_id.split("_")
            if len(parts) < 3:
                return None

            timestamp = f"{parts[1]}_{parts[2]}"

            datasets_path = self.db_path.parent.parent / "datasets"

            for template_dir in datasets_path.iterdir():
                if not template_dir.is_dir():
                    continue

                screenplay_path = template_dir / f"screenplay_{timestamp}.fountain"
                if screenplay_path.exists():
                    with open(screenplay_path) as f:
                        return f.read()

            return None

        except Exception as e:
            print(f"Error loading screenplay for {run_id}: {e}")
            return None
