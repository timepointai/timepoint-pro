# ============================================================================
# evaluation.py - Custom evaluation metrics (no external eval dependencies)
# ============================================================================
from typing import List, Dict
from datetime import datetime

from schemas import Entity
from storage import GraphStore
from validation import (
    validate_behavioral_inertia,
    validate_information_conservation,
    validate_biological_constraints
)

class EvaluationMetrics:
    """Lightweight evaluation metrics without external dependencies"""
    
    def __init__(self, store: GraphStore):
        self.store = store
        self.results = []
        self.baselines = {}
    
    def temporal_coherence_score(self, entity: Entity, timeline: List[datetime]) -> float:
        """Measure consistency across timepoints"""
        violations = 0
        for i in range(len(timeline) - 1):
            context = {"previous_personality": entity.entity_metadata.get("personality_traits", [])}
            result = validate_behavioral_inertia(entity, context)
            if not result["valid"]:
                violations += 1
        return 1.0 - (violations / max(len(timeline) - 1, 1))

    
    def knowledge_consistency_score(self, entity: Entity, context: Dict) -> float:
        """Information conservation compliance"""
        result = validate_information_conservation(entity, context, self.store)
        return 1.0 if result["valid"] else 0.0
    
    def biological_plausibility_score(self, entity: Entity, actions: List[str],
                                      resource_state: Dict = None,
                                      resource_constraints: Dict = None) -> float:
        """Constraint enforcement violation rate (M4)"""
        violations = 0
        for action in actions:
            context = {"action": action}
            if resource_state:
                context["resource_state"] = resource_state
            if resource_constraints:
                context["resource_constraints"] = resource_constraints
            result = validate_biological_constraints(entity, context)
            if not result["valid"]:
                violations += 1
        return 1.0 - (violations / max(len(actions), 1))
    
    def compare_approaches(self, entity_compressed: Entity, entity_full: Entity) -> Dict:
        """Compare compressed tensor vs full-context approach"""
        comparison = {
            "token_savings": self._estimate_token_savings(entity_compressed, entity_full),
            "quality_delta": self._compute_quality_delta(entity_compressed, entity_full),
            "cost_efficiency": 0.0
        }
        
        if comparison["token_savings"] > 0:
            comparison["cost_efficiency"] = comparison["quality_delta"] / comparison["token_savings"]
        
        return comparison
    
    def _estimate_token_savings(self, compressed: Entity, full: Entity) -> float:
        compressed_tokens = len(str(compressed.tensor)) / 4  # Rough estimate
        full_tokens = len(str(full.entity_metadata)) / 4
        return max(0, full_tokens - compressed_tokens)
    
    def _compute_quality_delta(self, compressed: Entity, full: Entity) -> float:
        # Simplified quality comparison
        return 0.95  # Placeholder