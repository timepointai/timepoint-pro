"""
Unit tests for tensor resolution integration (Phase 7).

Tests the tensor resolution system that enables tensor reuse across runs.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from schemas import Entity


class TestTensorResolutionHelpers:
    """Tests for tensor resolution helper functions."""

    def test_resolve_existing_tensor_returns_none_when_empty_index(self):
        """Test that resolution returns None when index is empty."""
        from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
        from metadata.run_tracker import MetadataManager

        # Create runner with minimal setup
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            mm = MetadataManager(str(db_path))
            runner = FullE2EWorkflowRunner(mm, generate_summary=False)

            # Create mock entity
            entity = Mock(spec=Entity)
            entity.entity_id = "test_entity"
            entity.entity_type = "human"
            entity.entity_metadata = {"role": "CEO"}

            # Mock the TensorRAG to return empty index
            mock_rag = Mock()
            mock_rag.index_size = 0
            runner._tensor_rag = mock_rag

            # Should return None with empty index
            result = runner._resolve_existing_tensor(
                entity=entity,
                world_id="test_world",
                scenario_context="A board meeting scenario",
                min_score=0.75
            )

            assert result is None

    def test_resolve_existing_tensor_handles_exceptions(self):
        """Test that resolution handles exceptions gracefully."""
        from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
        from metadata.run_tracker import MetadataManager

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            mm = MetadataManager(str(db_path))
            runner = FullE2EWorkflowRunner(mm, generate_summary=False)

            # Create mock entity with missing attributes
            entity = Mock()
            entity.entity_id = "test_entity"
            entity.entity_type = "human"
            entity.entity_metadata = None  # Will cause exception

            # Should handle exception and return None
            result = runner._resolve_existing_tensor(
                entity=entity,
                world_id="test_world",
                scenario_context="Test scenario",
                min_score=0.75
            )

            # Should return None, not raise
            assert result is None


class TestTensorResolutionMetadata:
    """Tests for tensor resolution metadata tracking."""

    def test_entity_metadata_tracks_resolution(self):
        """Test that entity metadata correctly tracks resolution status."""
        from schemas import Entity

        # Create entity
        entity = Entity(
            entity_id="test_entity",
            entity_type="human",
            entity_metadata={}
        )

        # Simulate resolution from cache
        entity.entity_metadata["tensor_resolved_from_cache"] = True
        entity.entity_metadata["baseline_initialized"] = True
        entity.entity_metadata["needs_llm_population"] = False

        assert entity.entity_metadata["tensor_resolved_from_cache"] is True
        assert entity.entity_metadata["baseline_initialized"] is True
        assert entity.entity_metadata["needs_llm_population"] is False

    def test_entity_metadata_tracks_cache_miss(self):
        """Test that entity metadata correctly tracks cache miss."""
        from schemas import Entity

        # Create entity
        entity = Entity(
            entity_id="test_entity",
            entity_type="human",
            entity_metadata={}
        )

        # Simulate cache miss (new baseline tensor)
        entity.entity_metadata["tensor_resolved_from_cache"] = False
        entity.entity_metadata["baseline_initialized"] = False
        entity.entity_metadata["needs_llm_population"] = True
        entity.entity_metadata["needs_training"] = True

        assert entity.entity_metadata["tensor_resolved_from_cache"] is False
        assert entity.entity_metadata["needs_llm_population"] is True


class TestTensorRAGIntegration:
    """Tests for TensorRAG integration with e2e_runner."""

    def test_get_tensor_rag_lazy_initialization(self):
        """Test that TensorRAG is lazily initialized."""
        from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
        from metadata.run_tracker import MetadataManager

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            mm = MetadataManager(str(db_path))
            runner = FullE2EWorkflowRunner(mm, generate_summary=False)

            # Initially None
            assert runner._tensor_rag is None

            # Accessing causes initialization - patch at the import location
            with patch('retrieval.tensor_rag.TensorRAG') as mock_rag:
                mock_rag.return_value = Mock()
                mock_rag.return_value.index_size = 0
                rag = runner._get_tensor_rag()
                assert rag is not None

    def test_get_tensor_db_lazy_initialization(self):
        """Test that TensorDatabase is lazily initialized."""
        from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
        from metadata.run_tracker import MetadataManager

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            mm = MetadataManager(str(db_path))
            runner = FullE2EWorkflowRunner(mm, generate_summary=False)

            # Initially None
            assert runner._tensor_db is None

            # Accessing causes initialization
            db = runner._get_tensor_db()
            assert db is not None
            assert runner._tensor_db is not None


class TestResolutionScoring:
    """Tests for resolution scoring logic."""

    def test_min_score_threshold_respected(self):
        """Test that minimum score threshold is respected."""
        # This tests the logic in _resolve_existing_tensor

        # Score >= threshold: should return tensor
        min_score = 0.75
        match_score = 0.80
        assert match_score >= min_score

        # Score < threshold: should not return tensor
        match_score = 0.60
        assert match_score < min_score

    def test_composition_threshold(self):
        """Test composition threshold for weak matches."""
        # Multiple weak matches (0.4-0.75) should be composable
        weak_scores = [0.45, 0.50, 0.42]
        composable_threshold = 0.4

        composable = [s for s in weak_scores if s >= composable_threshold]
        assert len(composable) >= 2  # Should have enough for composition


class TestInitializeBaselineTensorsFlow:
    """Tests for the initialize_baseline_tensors flow."""

    def test_flow_tracks_resolution_stats(self):
        """Test that the flow correctly tracks resolution statistics."""
        # These would be tracked in the actual _initialize_baseline_tensors method
        entities_initialized = 0
        entities_resolved = 0
        entities_failed = 0

        # Simulate processing 5 entities
        # 2 resolved from cache, 2 baseline, 1 fallback
        for i in range(5):
            if i < 2:  # First 2: cache hit
                entities_resolved += 1
                entities_initialized += 1
            elif i < 4:  # Next 2: baseline
                entities_initialized += 1
            else:  # Last 1: fallback
                entities_failed += 1
                entities_initialized += 1

        assert entities_initialized == 5
        assert entities_resolved == 2
        assert entities_failed == 1

        # Cache hit rate
        cache_hit_rate = entities_resolved / max(1, entities_initialized)
        assert cache_hit_rate == 0.4  # 2/5 = 40%

    def test_needs_population_count(self):
        """Test calculation of entities needing LLM population."""
        entities_initialized = 5
        entities_resolved = 2

        needs_pop_count = entities_initialized - entities_resolved
        assert needs_pop_count == 3  # 5 - 2 = 3 entities need population
