"""
Trajectory Tracker: Cognitive State Snapshot Accumulator

Observes each entity's cognitive state evolving across timepoints during
dialog synthesis, accumulating snapshots for ADPRS waveform fitting.

Part of Phase 2: Emergent Envelope Fitting from TTM Trajectories.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class CognitiveSnapshot:
    """Single observation of an entity's cognitive state at a timepoint."""

    entity_id: str
    timepoint_id: str
    timepoint_index: int
    timestamp: Optional[datetime]
    emotional_valence: float
    emotional_arousal: float
    energy_budget: float
    knowledge_count: int
    tensor_maturity: float
    activation: float  # Computed composite scalar in [0, 1]

    @staticmethod
    def compute_activation(valence: float, arousal: float, energy: float) -> float:
        """
        Weighted composite activation scalar, clamped to [0, 1].

        activation = 0.4 * (valence + 1) / 2 + 0.35 * arousal + 0.25 * (energy / 100)

        valence is in [-1, 1], arousal in [0, 1], energy in [0, 100].
        """
        raw = 0.4 * (valence + 1.0) / 2.0 + 0.35 * arousal + 0.25 * (energy / 100.0)
        return max(0.0, min(1.0, raw))


class TrajectoryTracker:
    """Accumulates cognitive snapshots per entity during the dialog loop."""

    def __init__(self):
        self._snapshots: Dict[str, List[CognitiveSnapshot]] = {}

    def record_snapshot(
        self, entity, timepoint, timepoint_index: int
    ) -> Optional[CognitiveSnapshot]:
        """
        Record a snapshot of the entity's cognitive state after dialog backprop sync.

        Reads from entity.entity_metadata["cognitive_tensor"]. Returns None if
        the entity has no cognitive tensor data.
        """
        if not hasattr(entity, "entity_metadata") or not entity.entity_metadata:
            return None

        ct_data = entity.entity_metadata.get("cognitive_tensor")
        if not ct_data:
            return None

        valence = ct_data.get("emotional_valence", 0.0)
        arousal = ct_data.get("emotional_arousal", 0.0)
        energy = ct_data.get("energy_budget", 100.0)
        knowledge = ct_data.get("knowledge_state", [])
        knowledge_count = len(knowledge) if isinstance(knowledge, list) else 0

        activation = CognitiveSnapshot.compute_activation(valence, arousal, energy)

        # Extract timestamp from timepoint
        ts = None
        if hasattr(timepoint, "timestamp"):
            ts = timepoint.timestamp

        # Extract entity tensor_maturity
        maturity = getattr(entity, "tensor_maturity", 0.0)

        snapshot = CognitiveSnapshot(
            entity_id=entity.entity_id,
            timepoint_id=getattr(timepoint, "timepoint_id", str(timepoint_index)),
            timepoint_index=timepoint_index,
            timestamp=ts,
            emotional_valence=valence,
            emotional_arousal=arousal,
            energy_budget=energy,
            knowledge_count=knowledge_count,
            tensor_maturity=maturity,
            activation=activation,
        )

        if entity.entity_id not in self._snapshots:
            self._snapshots[entity.entity_id] = []
        self._snapshots[entity.entity_id].append(snapshot)

        return snapshot

    def get_trajectory(self, entity_id: str) -> List[CognitiveSnapshot]:
        """Get all snapshots for an entity, ordered by timepoint_index."""
        snapshots = self._snapshots.get(entity_id, [])
        return sorted(snapshots, key=lambda s: s.timepoint_index)

    def get_activation_series(
        self, entity_id: str
    ) -> Tuple[List[float], List[float]]:
        """
        Get normalized tau and activation values for fitting.

        tau is normalized to [0, 1] from timepoint indices.
        Returns (tau_list, activation_list).
        """
        trajectory = self.get_trajectory(entity_id)
        if not trajectory:
            return [], []

        indices = [s.timepoint_index for s in trajectory]
        activations = [s.activation for s in trajectory]

        min_idx = min(indices)
        max_idx = max(indices)
        span = max_idx - min_idx

        if span == 0:
            # Single point — place at tau=0.5
            return [0.5], activations

        tau_list = [(idx - min_idx) / span for idx in indices]
        return tau_list, activations

    def has_sufficient_data(self, entity_id: str, min_points: int = 5) -> bool:
        """Check if enough snapshots exist for meaningful fitting."""
        return len(self._snapshots.get(entity_id, [])) >= min_points

    def get_all_entity_ids(self) -> List[str]:
        """Get all entity IDs that have recorded snapshots."""
        return list(self._snapshots.keys())

    def summary(self) -> dict:
        """Summary dict for logging."""
        total = sum(len(v) for v in self._snapshots.values())
        return {
            "entities_tracked": len(self._snapshots),
            "total_snapshots": total,
            "per_entity": {
                eid: len(snaps) for eid, snaps in self._snapshots.items()
            },
        }
