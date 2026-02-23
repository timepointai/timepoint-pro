"""
Enhanced Query Engine for Batch Query Execution

Extends existing QueryInterface with batch execution and result caching.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import hashlib
import json


class QueryResultCache:
    """Simple time-based cache for query results"""

    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: Time-to-live for cached results (default 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _compute_key(self, query: str, context: Dict[str, Any]) -> str:
        """Compute cache key from query and context"""
        cache_str = json.dumps({"query": query, "context": context}, sort_keys=True)
        return hashlib.md5(cache_str.encode(), usedforsecurity=False).hexdigest()

    def get(self, query: str, context: Dict[str, Any]) -> Optional[Any]:
        """Get cached result if available and not expired"""
        key = self._compute_key(query, context)
        if key in self._cache:
            entry = self._cache[key]
            age = (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds()
            if age < self.ttl_seconds:
                return entry["result"]
            else:
                del self._cache[key]
        return None

    def set(self, query: str, context: Dict[str, Any], result: Any):
        """Cache a query result"""
        key = self._compute_key(query, context)
        self._cache[key] = {
            "result": result,
            "timestamp": datetime.now(timezone.utc)
        }

    def clear(self):
        """Clear all cached results"""
        self._cache.clear()


class EnhancedQueryEngine:
    """
    Enhanced query engine with batch execution and caching.

    Example:
        from reporting import EnhancedQueryEngine
        from query_interface import QueryInterface

        base_query = QueryInterface(llm_client, graph_store)
        engine = EnhancedQueryEngine(base_query, cache_ttl=300)

        # Batch execution
        queries = [
            "What happened at the board meeting?",
            "Who made the final decision?",
            "What were the key conflicts?"
        ]
        results = engine.execute_batch(queries, world_id="meeting_001")

        # Aggregation queries
        relationships = engine.summarize_relationships(world_id="meeting_001")
        timeline = engine.timeline_summary(world_id="meeting_001")
    """

    def __init__(
        self,
        base_query_interface: Optional[Any] = None,
        cache_ttl: int = 300,
        enable_cache: bool = True
    ):
        """
        Args:
            base_query_interface: Existing QueryInterface instance (optional)
            cache_ttl: Cache time-to-live in seconds
            enable_cache: Whether to enable result caching
        """
        self.base_query = base_query_interface
        self.enable_cache = enable_cache
        self.cache = QueryResultCache(cache_ttl) if enable_cache else None
        self._batch_stats = {
            "queries_executed": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    def execute_batch(
        self,
        queries: List[str],
        world_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple queries efficiently with shared context caching.

        Args:
            queries: List of query strings
            world_id: World identifier for context
            context: Additional context for queries

        Returns:
            List of query results
        """
        if context is None:
            context = {}
        if world_id:
            context["world_id"] = world_id

        results = []
        for query in queries:
            # Check cache
            if self.enable_cache:
                cached = self.cache.get(query, context)
                if cached is not None:
                    self._batch_stats["cache_hits"] += 1
                    self._batch_stats["queries_executed"] += 1
                    results.append(cached)
                    continue
                else:
                    self._batch_stats["cache_misses"] += 1

            # Execute query (mock implementation - would call base_query in production)
            result = self._execute_single(query, context)

            # Cache result
            if self.enable_cache:
                self.cache.set(query, context, result)

            results.append(result)
            self._batch_stats["queries_executed"] += 1

        return results

    def _execute_single(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single query (mock implementation).

        In production, this would call:
            return self.base_query.query(query, context)
        """
        return {
            "query": query,
            "result": f"Mock result for: {query}",
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def summarize_relationships(
        self,
        world_id: str,
        entity_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate relationship matrix summary.

        Args:
            world_id: World identifier
            entity_filter: Optional list of entity IDs to include

        Returns:
            Dictionary with relationship summary:
                - entity_pairs: List of (entity1, entity2, relationship_type, strength)
                - matrix: 2D relationship matrix
                - summary_stats: Statistics about relationships
        """
        # Mock implementation
        return {
            "world_id": world_id,
            "entity_filter": entity_filter,
            "entity_pairs": [
                {"entity1": "alice", "entity2": "bob", "type": "trust", "strength": 0.8},
                {"entity1": "alice", "entity2": "charlie", "type": "alignment", "strength": 0.6}
            ],
            "summary_stats": {
                "total_relationships": 2,
                "avg_strength": 0.7,
                "relationship_types": ["trust", "alignment"]
            }
        }

    def knowledge_flow_graph(
        self,
        world_id: str,
        timepoint_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        Generate knowledge flow graph (who learned what from whom).

        Args:
            world_id: World identifier
            timepoint_range: Optional (start, end) timepoint indices

        Returns:
            Dictionary with knowledge flow:
                - nodes: List of entities
                - edges: List of (source, target, knowledge_item, timepoint)
                - flow_metrics: Statistics about knowledge propagation
        """
        # Mock implementation
        return {
            "world_id": world_id,
            "timepoint_range": timepoint_range,
            "nodes": ["alice", "bob", "charlie"],
            "edges": [
                {"source": "alice", "target": "bob", "knowledge": "plan_details", "timepoint": 0},
                {"source": "bob", "target": "charlie", "knowledge": "plan_details", "timepoint": 1}
            ],
            "flow_metrics": {
                "total_transfers": 2,
                "avg_hops": 1.5,
                "knowledge_items": ["plan_details"]
            }
        }

    def timeline_summary(
        self,
        world_id: str,
        include_minor_events: bool = False
    ) -> Dict[str, Any]:
        """
        Generate chronological timeline summary.

        Args:
            world_id: World identifier
            include_minor_events: Whether to include low-importance events

        Returns:
            Dictionary with timeline:
                - events: List of (timepoint, event_type, description, importance)
                - key_moments: Filtered list of critical events
                - narrative_arc: Tension/stakes progression
        """
        # Mock implementation
        return {
            "world_id": world_id,
            "events": [
                {"timepoint": 0, "type": "meeting_start", "description": "Board meeting begins", "importance": 0.7},
                {"timepoint": 1, "type": "proposal", "description": "CEO proposes acquisition", "importance": 0.9},
                {"timepoint": 2, "type": "decision", "description": "Vote taken", "importance": 1.0}
            ],
            "key_moments": [
                {"timepoint": 1, "description": "CEO proposes acquisition"},
                {"timepoint": 2, "description": "Vote taken"}
            ],
            "narrative_arc": {
                "tension_progression": [0.3, 0.7, 1.0, 0.6],
                "peak_moment": 2
            }
        }

    def entity_comparison(
        self,
        world_id: str,
        entity_ids: List[str],
        aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate side-by-side entity comparison.

        Args:
            world_id: World identifier
            entity_ids: List of entity IDs to compare
            aspects: Optional list of aspects to compare (personality, knowledge, relationships)

        Returns:
            Dictionary with comparison:
                - entities: Entity metadata
                - comparison_table: Side-by-side comparison
                - similarity_scores: Pairwise similarity metrics
        """
        if aspects is None:
            aspects = ["personality", "knowledge", "relationships"]

        # Mock implementation
        return {
            "world_id": world_id,
            "entity_ids": entity_ids,
            "aspects": aspects,
            "comparison_table": {
                "personality": {
                    "alice": {"openness": 0.8, "conscientiousness": 0.7},
                    "bob": {"openness": 0.6, "conscientiousness": 0.9}
                },
                "knowledge": {
                    "alice": ["plan_details", "market_data"],
                    "bob": ["plan_details"]
                }
            },
            "similarity_scores": {
                ("alice", "bob"): 0.65
            }
        }

    def get_batch_stats(self) -> Dict[str, Any]:
        """Get statistics about batch query execution"""
        stats = dict(self._batch_stats)
        total_attempts = stats["cache_hits"] + stats["cache_misses"]
        if total_attempts > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / total_attempts
        else:
            stats["cache_hit_rate"] = 0.0
        return stats

    def clear_cache(self):
        """Clear the query result cache"""
        if self.cache:
            self.cache.clear()
