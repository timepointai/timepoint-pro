# ============================================================================
# resolution_engine.py - Variable resolution system for adaptive detail levels
# ============================================================================
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import networkx as nx
from schemas import Entity, Timepoint, ResolutionLevel
from storage import GraphStore


class ResolutionEngine:
    """Decides optimal resolution levels for entities based on multiple factors"""

    def __init__(self, store: GraphStore):
        self.store = store
        self.query_history: Dict[str, int] = {}  # entity_id -> access count

    def decide_resolution(
        self,
        entity: Entity,
        timepoint: Timepoint,
        graph: Optional[nx.Graph] = None
    ) -> ResolutionLevel:
        """
        Decide detail level for entity at timepoint using multiple signals:

        - Graph centrality (eigenvector centrality)
        - Query history (frequent access = higher resolution)
        - Timepoint importance (key events = higher resolution)
        - Role importance (protagonists > supporting > extras)
        - Temporal recency (recent events more detailed)
        """

        # Base score starts at 0, we add points for each factor
        resolution_score = 0.0
        max_score = 5.0  # Corresponds to TRAINED resolution

        # 1. Graph centrality (0-1 points)
        centrality_score = 0.0
        if graph and entity.entity_id in graph:
            centrality = nx.eigenvector_centrality_numpy(graph)
            centrality_score = centrality.get(entity.entity_id, 0.0)
            resolution_score += centrality_score * 1.0  # Max 1.0 points

        # 2. Query history (0-1 points)
        query_count = self.query_history.get(entity.entity_id, 0)
        if query_count > 0:
            # Logarithmic scaling: 1 query = 0.2, 10 queries = 0.5, 100+ = 1.0
            query_score = min(1.0, (query_count ** 0.5) / 10.0)
            resolution_score += query_score

        # 3. Timepoint importance (0-1 points)
        timepoint_score = self._calculate_timepoint_importance(timepoint)
        resolution_score += timepoint_score

        # 4. Role importance (0-1 points)
        role_score = self._calculate_role_importance(entity)
        resolution_score += role_score

        # 5. Temporal recency (0-0.5 points, bonus for recent events)
        recency_score = self._calculate_temporal_recency(timepoint)
        resolution_score += recency_score

        # Convert score to resolution level
        return self._score_to_resolution(resolution_score, max_score)

    def _calculate_timepoint_importance(self, timepoint: Timepoint) -> float:
        """Rate timepoint importance based on event description and position in chain"""
        importance = 0.0

        # Keywords indicating high importance
        high_importance_keywords = [
            "inauguration", "election", "revolution", "war", "treaty", "declaration",
            "crisis", "summit", "ceremony", "historic", "first", "founding"
        ]

        event_lower = timepoint.event_description.lower()
        for keyword in high_importance_keywords:
            if keyword in event_lower:
                importance += 0.3
                break  # Only count once

        # First timepoint in chain gets bonus (establishment events)
        if timepoint.causal_parent is None:
            importance += 0.2

        # Resolution level already set on timepoint affects importance
        resolution_hierarchy = {
            ResolutionLevel.TENSOR_ONLY: 0.0,
            ResolutionLevel.SCENE: 0.2,
            ResolutionLevel.GRAPH: 0.4,
            ResolutionLevel.DIALOG: 0.6,
            ResolutionLevel.TRAINED: 0.8
        }
        importance += resolution_hierarchy.get(timepoint.resolution_level, 0.0)

        return min(1.0, importance)

    def _calculate_role_importance(self, entity: Entity) -> float:
        """Rate entity importance based on role and metadata"""
        importance = 0.0

        role = entity.entity_metadata.get("role", "").lower()

        # Primary roles get high importance
        primary_roles = ["president", "general", "commander", "leader", "founder"]
        if any(primary_role in role for primary_role in primary_roles):
            importance += 0.6

        # Secondary roles get medium importance
        secondary_roles = ["secretary", "minister", "governor", "ambassador", "delegate"]
        if any(secondary_role in role for secondary_role in secondary_roles):
            importance += 0.4

        # Military/political figures get bonus
        if any(term in role for term in ["general", "colonel", "major", "captain", "politician"]):
            importance += 0.2

        return min(1.0, importance)

    def _calculate_temporal_recency(self, timepoint: Timepoint) -> float:
        """Bonus for more recent timepoints (within last 24 hours simulation time)"""
        # In a real scenario, this would compare to current time
        # For now, give small bonus to maintain some detail in recent events
        return 0.1

    def _score_to_resolution(self, score: float, max_score: float) -> ResolutionLevel:
        """Convert numeric score to resolution level"""
        normalized_score = score / max_score

        if normalized_score < 0.2:
            return ResolutionLevel.TENSOR_ONLY
        elif normalized_score < 0.4:
            return ResolutionLevel.SCENE
        elif normalized_score < 0.6:
            return ResolutionLevel.GRAPH
        elif normalized_score < 0.8:
            return ResolutionLevel.DIALOG
        else:
            return ResolutionLevel.TRAINED

    def record_query(self, entity_id: str) -> None:
        """Record that an entity was queried (increases its resolution priority)"""
        self.query_history[entity_id] = self.query_history.get(entity_id, 0) + 1

    def get_resolution_stats(self) -> Dict[str, int]:
        """Get statistics on current resolution distribution"""
        entities = []  # We'd need to get all entities from store

        # This is a placeholder - in real implementation, we'd query all entities
        stats = {
            ResolutionLevel.TENSOR_ONLY.value: 0,
            ResolutionLevel.SCENE.value: 0,
            ResolutionLevel.GRAPH.value: 0,
            ResolutionLevel.DIALOG.value: 0,
            ResolutionLevel.TRAINED.value: 0
        }

        # Count would go here...

        return stats

    def elevate_resolution(self, entity: Entity, target_resolution: ResolutionLevel) -> bool:
        """
        Attempt to elevate an entity's resolution level.
        Returns True if elevation was successful.
        """
        current_level_value = list(ResolutionLevel).index(entity.resolution_level)
        target_level_value = list(ResolutionLevel).index(target_resolution)

        if target_level_value > current_level_value:
            entity.resolution_level = target_resolution
            self.store.save_entity(entity)
            return True

        return False
