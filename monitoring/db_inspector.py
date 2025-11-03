"""
Database inspector for querying simulation state.

Reads metadata/runs.db and narrative JSON files to extract deep simulation state.
"""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Any


@dataclass
class SimulationSnapshot:
    """Snapshot of simulation state from database and narrative files"""

    # Metadata from runs.db
    run_id: Optional[str] = None
    template_id: Optional[str] = None
    causal_mode: Optional[str] = None
    entities_created: int = 0
    timepoints_created: int = 0
    mechanisms_used: List[str] = None
    cost_usd: float = 0.0
    status: str = "unknown"

    # M1+M17: Fidelity metrics (Database v2)
    fidelity_distribution: Optional[Dict[str, int]] = None
    token_budget_compliance: Optional[float] = None
    fidelity_efficiency_score: Optional[float] = None
    actual_tokens_used: Optional[float] = None

    # Narrative data from JSON
    characters: List[Dict[str, Any]] = None
    timeline: List[Dict[str, Any]] = None
    latest_event: Optional[str] = None
    dialog_count: int = 0

    def __post_init__(self):
        if self.mechanisms_used is None:
            self.mechanisms_used = []
        if self.characters is None:
            self.characters = []
        if self.timeline is None:
            self.timeline = []


class DBInspector:
    """
    Inspect database and narrative files for simulation state.
    """

    def __init__(self, db_path: Path, datasets_dir: Path):
        self.db_path = db_path
        self.datasets_dir = datasets_dir

    def get_run_snapshot(self, run_id: str) -> Optional[SimulationSnapshot]:
        """
        Get complete snapshot of a simulation run.

        Combines metadata from runs.db and narrative from JSON files.
        """
        if not run_id:
            return None

        snapshot = SimulationSnapshot(run_id=run_id)

        # Query metadata database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()

            if row:
                snapshot.template_id = row[1]
                snapshot.causal_mode = row[4]
                snapshot.entities_created = row[7] or 0
                snapshot.timepoints_created = row[8] or 0
                snapshot.cost_usd = row[10] or 0.0
                snapshot.status = row[16] or "unknown"

                # M1+M17: Query v2 fidelity fields (Database v2)
                if len(row) > 24:  # Check if v2 columns exist
                    # Parse fidelity_distribution JSON
                    fidelity_dist_json = row[24]
                    if fidelity_dist_json:
                        try:
                            snapshot.fidelity_distribution = json.loads(fidelity_dist_json)
                        except:
                            pass

                    # Extract numeric metrics
                    snapshot.actual_tokens_used = row[25]
                    snapshot.token_budget_compliance = row[26]
                    snapshot.fidelity_efficiency_score = row[27]

            # Get mechanisms
            cursor.execute("SELECT DISTINCT mechanism FROM mechanism_usage WHERE run_id = ?", (run_id,))
            snapshot.mechanisms_used = [row[0] for row in cursor.fetchall()]

            conn.close()

        except Exception as e:
            # Database might not exist yet or be locked
            pass

        # Try to read narrative JSON
        if snapshot.template_id:
            narrative_file = self._find_latest_narrative(snapshot.template_id)
            if narrative_file and narrative_file.exists():
                try:
                    with open(narrative_file) as f:
                        data = json.load(f)

                    snapshot.characters = data.get("characters", [])
                    snapshot.timeline = data.get("timeline", [])
                    snapshot.dialog_count = len(data.get("dialogs", []))

                    # Extract latest event
                    if snapshot.timeline:
                        latest = snapshot.timeline[-1]
                        snapshot.latest_event = latest.get("event_description", "")

                except Exception:
                    pass

        return snapshot

    def _find_latest_narrative(self, template_id: str) -> Optional[Path]:
        """Find the most recent narrative JSON file for a template"""
        template_dir = self.datasets_dir / template_id
        if not template_dir.exists():
            return None

        narrative_files = sorted(template_dir.glob("narrative_*.json"))
        if narrative_files:
            return narrative_files[-1]  # Most recent

        return None

    def format_snapshot_for_llm(self, snapshot: SimulationSnapshot) -> str:
        """
        Format snapshot as text for LLM consumption.

        Returns a concise, structured description.
        """
        if not snapshot or not snapshot.run_id:
            return "No simulation data available."

        lines = []
        lines.append(f"=== SIMULATION STATE: {snapshot.run_id} ===")
        lines.append(f"Template: {snapshot.template_id}")
        lines.append(f"Mode: {snapshot.causal_mode}")
        lines.append(f"Progress: {snapshot.entities_created} entities, {snapshot.timepoints_created} timepoints")
        lines.append(f"Mechanisms: {', '.join(snapshot.mechanisms_used) if snapshot.mechanisms_used else 'None'}")
        lines.append(f"Cost: ${snapshot.cost_usd:.3f}")
        lines.append(f"Status: {snapshot.status}")

        # M1+M17: Display fidelity metrics (Database v2)
        if snapshot.fidelity_distribution:
            lines.append(f"\nFidelity Distribution (M1):")
            for res_level, count in sorted(snapshot.fidelity_distribution.items()):
                lines.append(f"  {res_level}: {count} entities")

        if snapshot.token_budget_compliance is not None:
            compliance_pct = snapshot.token_budget_compliance * 100
            status = "✓" if snapshot.token_budget_compliance <= 1.0 else "⚠"
            lines.append(f"Token Budget Compliance: {status} {compliance_pct:.1f}%")

        if snapshot.fidelity_efficiency_score is not None:
            lines.append(f"Fidelity Efficiency: {snapshot.fidelity_efficiency_score:.6f} quality/token")

        if snapshot.characters:
            lines.append(f"\nCharacters ({len(snapshot.characters)}):")
            for char in snapshot.characters[:5]:  # First 5
                entity_id = char.get("entity_id", "unknown")
                entity_type = char.get("entity_type", "unknown")
                lines.append(f"  - {entity_id} ({entity_type})")
            if len(snapshot.characters) > 5:
                lines.append(f"  ... and {len(snapshot.characters) - 5} more")

        if snapshot.timeline:
            lines.append(f"\nTimeline: {len(snapshot.timeline)} timepoints")
            if snapshot.latest_event:
                lines.append(f"Latest event: {snapshot.latest_event}")

        if snapshot.dialog_count > 0:
            lines.append(f"\nDialogs: {snapshot.dialog_count} conversations generated")

        return "\n".join(lines)
