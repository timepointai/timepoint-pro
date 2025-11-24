"""
Tests for Enhanced Query Engine (Sprint 2.1)
"""

import pytest
from reporting.query_engine import EnhancedQueryEngine, QueryResultCache


class TestQueryResultCache:
    """Tests for query result caching"""

    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = QueryResultCache(ttl_seconds=300)
        result = cache.get("test query", {})
        assert result is None

    def test_cache_hit(self):
        """Test cache hit returns cached result"""
        cache = QueryResultCache(ttl_seconds=300)
        cache.set("test query", {}, {"result": "data"})
        result = cache.get("test query", {})
        assert result == {"result": "data"}

    def test_cache_clear(self):
        """Test cache clearing"""
        cache = QueryResultCache(ttl_seconds=300)
        cache.set("query1", {}, "result1")
        cache.set("query2", {}, "result2")
        cache.clear()
        assert cache.get("query1", {}) is None
        assert cache.get("query2", {}) is None


class TestEnhancedQueryEngine:
    """Tests for EnhancedQueryEngine"""

    def test_engine_initialization(self):
        """Test engine initialization"""
        engine = EnhancedQueryEngine(cache_ttl=300)
        assert engine.enable_cache is True
        assert engine.cache is not None

    def test_execute_batch_basic(self):
        """Test basic batch query execution"""
        engine = EnhancedQueryEngine()
        queries = [
            "What happened?",
            "Who was involved?",
            "What was the outcome?"
        ]
        results = engine.execute_batch(queries, world_id="test_world")

        assert len(results) == 3
        for i, result in enumerate(results):
            assert "query" in result
            assert result["query"] == queries[i]

    def test_batch_with_caching(self):
        """Test batch execution with caching"""
        engine = EnhancedQueryEngine(enable_cache=True)

        queries = ["Query 1", "Query 2", "Query 1"]  # Query 1 repeated
        results = engine.execute_batch(queries)

        stats = engine.get_batch_stats()
        assert stats["queries_executed"] == 3
        assert stats["cache_hits"] == 1  # Second "Query 1" should hit cache
        assert stats["cache_misses"] == 2

    def test_batch_without_caching(self):
        """Test batch execution without caching"""
        engine = EnhancedQueryEngine(enable_cache=False)

        queries = ["Query 1", "Query 2", "Query 1"]
        results = engine.execute_batch(queries)

        assert len(results) == 3
        stats = engine.get_batch_stats()
        assert stats["queries_executed"] == 3
        assert stats["cache_hits"] == 0

    def test_summarize_relationships(self):
        """Test relationship summarization"""
        engine = EnhancedQueryEngine()
        summary = engine.summarize_relationships("test_world")

        assert "world_id" in summary
        assert "entity_pairs" in summary
        assert "summary_stats" in summary
        assert summary["world_id"] == "test_world"

    def test_knowledge_flow_graph(self):
        """Test knowledge flow graph generation"""
        engine = EnhancedQueryEngine()
        flow = engine.knowledge_flow_graph("test_world")

        assert "world_id" in flow
        assert "nodes" in flow
        assert "edges" in flow
        assert "flow_metrics" in flow

    def test_timeline_summary(self):
        """Test timeline summary generation"""
        engine = EnhancedQueryEngine()
        timeline = engine.timeline_summary("test_world")

        assert "world_id" in timeline
        assert "events" in timeline
        assert "key_moments" in timeline
        assert "narrative_arc" in timeline

    def test_entity_comparison(self):
        """Test entity comparison"""
        engine = EnhancedQueryEngine()
        comparison = engine.entity_comparison(
            "test_world",
            entity_ids=["alice", "bob"]
        )

        assert "world_id" in comparison
        assert "entity_ids" in comparison
        assert "comparison_table" in comparison
        assert "similarity_scores" in comparison

    def test_clear_cache(self):
        """Test cache clearing"""
        engine = EnhancedQueryEngine(enable_cache=True)
        engine.execute_batch(["Query 1", "Query 2"])

        assert engine.get_batch_stats()["cache_misses"] > 0

        engine.clear_cache()
        # Cache should be empty now
        assert engine.cache._cache == {}

    def test_batch_stats_calculation(self):
        """Test batch statistics calculation"""
        engine = EnhancedQueryEngine(enable_cache=True)

        # First batch - all cache misses
        engine.execute_batch(["Q1", "Q2"])
        stats = engine.get_batch_stats()
        assert stats["cache_hit_rate"] == 0.0

        # Second batch - should have cache hits
        engine.execute_batch(["Q1", "Q2"])
        stats = engine.get_batch_stats()
        assert stats["cache_hit_rate"] > 0.0
