"""
TDD tests for Phase 3: Tensor Retrieval System (Tensor RAG).

Tests the semantic search and composition capabilities for trained tensors.

Phase 3: Retrieval System Implementation
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path
from datetime import datetime

# These will be implemented
from retrieval import (
    TensorRAG,
    EmbeddingIndex,
    TensorComposer,
    SearchResult,
)
from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import serialize_tensor, deserialize_tensor
from schemas import TTMTensor


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary tensor database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_tensors.db"
        db = TensorDatabase(db_path)
        yield db


@pytest.fixture
def sample_tensors():
    """Create sample tensors with descriptions."""
    return [
        {
            "tensor_id": "victorian_detective_001",
            "entity_id": "sherlock_holmes",
            "world_id": "london_1890",
            "description": "Victorian era detective with keen observation skills",
            "tensor": TTMTensor.from_arrays(
                context=np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2], dtype=np.float32),
                biology=np.array([0.5, 0.3, 0.4, 0.6], dtype=np.float32),
                behavior=np.array([0.8, 0.6, 0.7, 0.4, 0.9, 0.3, 0.5, 0.2], dtype=np.float32),
            ),
            "maturity": 0.95,
            "category": "profession/detective",
        },
        {
            "tensor_id": "renaissance_artist_001",
            "entity_id": "leonardo_davinci",
            "world_id": "florence_1500",
            "description": "Renaissance polymath artist and inventor",
            "tensor": TTMTensor.from_arrays(
                context=np.array([0.7, 0.9, 0.6, 0.3, 0.8, 0.5, 0.4, 0.6], dtype=np.float32),
                biology=np.array([0.4, 0.2, 0.3, 0.8], dtype=np.float32),
                behavior=np.array([0.6, 0.8, 0.5, 0.7, 0.6, 0.5, 0.7, 0.4], dtype=np.float32),
            ),
            "maturity": 0.92,
            "category": "profession/artist",
        },
        {
            "tensor_id": "modern_ceo_001",
            "entity_id": "tech_founder",
            "world_id": "silicon_valley_2024",
            "description": "Modern technology startup CEO and entrepreneur",
            "tensor": TTMTensor.from_arrays(
                context=np.array([0.8, 0.7, 0.9, 0.8, 0.6, 0.7, 0.5, 0.4], dtype=np.float32),
                biology=np.array([0.6, 0.4, 0.5, 0.7], dtype=np.float32),
                behavior=np.array([0.9, 0.5, 0.8, 0.3, 0.7, 0.6, 0.8, 0.7], dtype=np.float32),
            ),
            "maturity": 0.97,
            "category": "profession/executive",
        },
        {
            "tensor_id": "victorian_scientist_001",
            "entity_id": "charles_darwin",
            "world_id": "london_1860",
            "description": "Victorian era naturalist and scientist studying evolution",
            "tensor": TTMTensor.from_arrays(
                context=np.array([0.8, 0.9, 0.5, 0.4, 0.7, 0.6, 0.3, 0.5], dtype=np.float32),
                biology=np.array([0.3, 0.2, 0.3, 0.9], dtype=np.float32),
                behavior=np.array([0.5, 0.7, 0.4, 0.8, 0.8, 0.4, 0.6, 0.3], dtype=np.float32),
            ),
            "maturity": 0.94,
            "category": "profession/scientist",
        },
    ]


@pytest.fixture
def populated_db(temp_db, sample_tensors):
    """Create a database populated with sample tensors."""
    for sample in sample_tensors:
        record = TensorRecord(
            tensor_id=sample["tensor_id"],
            entity_id=sample["entity_id"],
            world_id=sample["world_id"],
            tensor_blob=serialize_tensor(sample["tensor"]),
            maturity=sample["maturity"],
            training_cycles=100,
            description=sample.get("description", ""),
            category=sample.get("category", ""),
        )
        temp_db.save_tensor(record)
    return temp_db


@pytest.fixture
def tensor_rag(populated_db):
    """Create TensorRAG instance with populated database."""
    return TensorRAG(tensor_db=populated_db)


# ============================================================================
# Test EmbeddingIndex
# ============================================================================

class TestEmbeddingIndex:
    """Tests for the embedding index component."""

    def test_index_creation(self, temp_db):
        """Test creating an empty embedding index."""
        index = EmbeddingIndex(embedding_dim=384)
        assert index is not None
        assert index.size == 0

    def test_add_single_embedding(self, temp_db):
        """Test adding a single embedding to the index."""
        index = EmbeddingIndex(embedding_dim=384)

        embedding = np.random.randn(384).astype(np.float32)
        index.add("tensor_001", embedding)

        assert index.size == 1

    def test_add_multiple_embeddings(self, temp_db):
        """Test adding multiple embeddings."""
        index = EmbeddingIndex(embedding_dim=384)

        for i in range(10):
            embedding = np.random.randn(384).astype(np.float32)
            index.add(f"tensor_{i:03d}", embedding)

        assert index.size == 10

    def test_search_returns_closest(self):
        """Test that search returns the most similar embedding."""
        index = EmbeddingIndex(embedding_dim=4)  # Small dim for testing

        # Add embeddings with known values
        index.add("north", np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32))
        index.add("east", np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32))
        index.add("south", np.array([-1.0, 0.0, 0.0, 0.0], dtype=np.float32))
        index.add("west", np.array([0.0, -1.0, 0.0, 0.0], dtype=np.float32))

        # Query for something similar to north
        query = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
        results = index.search(query, k=2)

        assert len(results) == 2
        assert results[0][0] == "north"  # Most similar
        assert results[0][1] > 0.9  # High similarity

    def test_search_with_k_limit(self):
        """Test that search respects k limit."""
        index = EmbeddingIndex(embedding_dim=4)

        for i in range(10):
            embedding = np.random.randn(4).astype(np.float32)
            index.add(f"tensor_{i}", embedding)

        query = np.random.randn(4).astype(np.float32)
        results = index.search(query, k=3)

        assert len(results) == 3

    def test_search_empty_index(self):
        """Test searching an empty index."""
        index = EmbeddingIndex(embedding_dim=4)

        query = np.random.randn(4).astype(np.float32)
        results = index.search(query, k=5)

        assert len(results) == 0

    def test_remove_from_index(self):
        """Test removing an embedding from the index."""
        index = EmbeddingIndex(embedding_dim=4)

        index.add("tensor_1", np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32))
        index.add("tensor_2", np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32))

        assert index.size == 2

        index.remove("tensor_1")

        assert index.size == 1

        # Search should only find tensor_2
        query = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        results = index.search(query, k=5)
        assert all(r[0] != "tensor_1" for r in results)


# ============================================================================
# Test TensorComposer
# ============================================================================

class TestTensorComposer:
    """Tests for tensor composition strategies."""

    def test_weighted_blend_equal_weights(self):
        """Test weighted blend with equal weights."""
        composer = TensorComposer()

        tensor1_values = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        tensor2_values = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

        result = composer.weighted_blend(
            [tensor1_values, tensor2_values],
            weights=[0.5, 0.5]
        )

        expected = np.array([0.5, 0.5, 0.0, 0.0], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_weighted_blend_unequal_weights(self):
        """Test weighted blend with different weights."""
        composer = TensorComposer()

        tensor1_values = np.array([1.0, 0.0], dtype=np.float32)
        tensor2_values = np.array([0.0, 1.0], dtype=np.float32)

        result = composer.weighted_blend(
            [tensor1_values, tensor2_values],
            weights=[0.8, 0.2]
        )

        expected = np.array([0.8, 0.2], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_max_pool_composition(self):
        """Test max pooling composition."""
        composer = TensorComposer()

        tensor1 = np.array([0.9, 0.1, 0.5, 0.3], dtype=np.float32)
        tensor2 = np.array([0.2, 0.8, 0.4, 0.7], dtype=np.float32)

        result = composer.max_pool([tensor1, tensor2])

        expected = np.array([0.9, 0.8, 0.5, 0.7], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_hierarchical_composition(self):
        """Test hierarchical override composition."""
        composer = TensorComposer()

        # Base tensor
        base = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        # Override tensor (zeros don't override)
        override = np.array([0.9, 0.0, 0.8, 0.0], dtype=np.float32)

        result = composer.hierarchical([base, override])

        # Non-zero values in override replace base
        expected = np.array([0.9, 0.5, 0.8, 0.5], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_compose_full_tensors(self, sample_tensors):
        """Test composing full TTMTensor objects."""
        composer = TensorComposer()

        tensor1 = sample_tensors[0]["tensor"]
        tensor2 = sample_tensors[1]["tensor"]

        result = composer.compose_tensors(
            [tensor1, tensor2],
            method="weighted_blend",
            weights=[0.6, 0.4]
        )

        assert isinstance(result, TTMTensor)
        # Verify dimensions preserved
        assert len(result.context_vector) == len(tensor1.context_vector)


# ============================================================================
# Test TensorRAG Main Class
# ============================================================================

class TestTensorRAGBasic:
    """Basic tests for TensorRAG functionality."""

    def test_initialization(self, populated_db):
        """Test TensorRAG initialization."""
        rag = TensorRAG(tensor_db=populated_db)
        assert rag is not None

    def test_index_built_from_database(self, tensor_rag, sample_tensors):
        """Test that index is built from database tensors."""
        # The index should contain all tensors from the database
        assert tensor_rag.index_size >= len(sample_tensors)

    def test_generate_embedding(self, tensor_rag):
        """Test generating embedding for a description."""
        embedding = tensor_rag.generate_embedding("Victorian detective")

        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 384  # sentence-transformers dim


class TestTensorRAGSearch:
    """Tests for TensorRAG search functionality."""

    def test_search_returns_results(self, tensor_rag):
        """Test that search returns results."""
        results = tensor_rag.search("Victorian era detective")

        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_result_structure(self, tensor_rag):
        """Test SearchResult contains expected fields."""
        results = tensor_rag.search("detective")

        if results:
            result = results[0]
            assert hasattr(result, 'tensor_id')
            assert hasattr(result, 'score')
            assert hasattr(result, 'tensor_record')
            assert 0.0 <= result.score <= 1.0

    def test_search_relevance(self, tensor_rag):
        """Test that search returns relevant results."""
        results = tensor_rag.search("Victorian detective investigating crimes")

        # Should find the victorian detective tensor
        tensor_ids = [r.tensor_id for r in results]
        assert "victorian_detective_001" in tensor_ids

        # Victorian detective should rank higher than modern CEO
        detective_rank = tensor_ids.index("victorian_detective_001")
        if "modern_ceo_001" in tensor_ids:
            ceo_rank = tensor_ids.index("modern_ceo_001")
            assert detective_rank < ceo_rank

    def test_search_with_maturity_filter(self, tensor_rag):
        """Test filtering results by minimum maturity."""
        # Filter to only high maturity tensors
        results = tensor_rag.search("professional", min_maturity=0.95)

        for result in results:
            assert result.tensor_record.maturity >= 0.95

    def test_search_with_category_filter(self, tensor_rag):
        """Test filtering results by category."""
        results = tensor_rag.search("professional", categories=["profession/detective"])

        for result in results:
            assert "detective" in result.tensor_record.category

    def test_search_k_limit(self, tensor_rag):
        """Test that search respects k limit."""
        results = tensor_rag.search("person", n_results=2)

        assert len(results) <= 2

    def test_search_empty_query(self, tensor_rag):
        """Test handling empty query."""
        results = tensor_rag.search("")

        # Should either return empty or all results
        assert isinstance(results, list)


class TestTensorRAGComposition:
    """Tests for TensorRAG composition functionality."""

    def test_compose_search_results(self, tensor_rag):
        """Test composing tensors from search results."""
        results = tensor_rag.search("Victorian professional", n_results=2)

        if len(results) >= 2:
            composed = tensor_rag.compose(results[:2])
            assert isinstance(composed, TTMTensor)

    def test_compose_with_custom_weights(self, tensor_rag):
        """Test composition with custom weights."""
        results = tensor_rag.search("professional", n_results=2)

        if len(results) >= 2:
            composed = tensor_rag.compose(
                results[:2],
                weights=[0.7, 0.3],
                method="weighted_blend"
            )
            assert isinstance(composed, TTMTensor)

    def test_compose_different_methods(self, tensor_rag):
        """Test different composition methods."""
        results = tensor_rag.search("professional", n_results=2)

        if len(results) >= 2:
            for method in ["weighted_blend", "max_pool", "hierarchical"]:
                composed = tensor_rag.compose(results[:2], method=method)
                assert isinstance(composed, TTMTensor)


class TestTensorRAGResolution:
    """Tests for entity tensor resolution."""

    def test_resolve_for_entity_finds_match(self, tensor_rag):
        """Test resolving tensor for entity description."""
        tensor = tensor_rag.resolve_for_entity(
            entity_description="Sherlock Holmes, a brilliant detective",
            scenario_context="Victorian London"
        )

        assert isinstance(tensor, TTMTensor)

    def test_resolve_for_entity_no_match(self, tensor_rag):
        """Test resolution when no good match exists."""
        # Query for something not in our sample data
        tensor = tensor_rag.resolve_for_entity(
            entity_description="Alien spacecraft pilot",
            scenario_context="Year 3000 space station"
        )

        # Should return a valid tensor (even if newly created)
        assert isinstance(tensor, TTMTensor)

    def test_resolve_prefers_high_maturity(self, tensor_rag):
        """Test that resolution prefers high maturity tensors."""
        tensor = tensor_rag.resolve_for_entity(
            entity_description="Technology startup executive",
            scenario_context="Modern business environment",
            min_maturity=0.95
        )

        assert isinstance(tensor, TTMTensor)

    def test_resolve_uses_composition(self, tensor_rag):
        """Test that resolution can compose multiple partial matches."""
        # Query that partially matches multiple tensors
        tensor = tensor_rag.resolve_for_entity(
            entity_description="Victorian businessman inventor",
            scenario_context="Industrial revolution England",
            allow_composition=True
        )

        assert isinstance(tensor, TTMTensor)


# ============================================================================
# Test Index Persistence
# ============================================================================

class TestIndexPersistence:
    """Tests for index save/load functionality."""

    def test_save_index(self, tensor_rag, temp_db):
        """Test saving index to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test_index"
            tensor_rag.save_index(index_path)

            assert index_path.exists() or (index_path.parent / f"{index_path.name}.npz").exists()

    def test_load_index(self, populated_db, temp_db):
        """Test loading index from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test_index"

            # Create and save
            rag1 = TensorRAG(tensor_db=populated_db)
            rag1.save_index(index_path)

            # Load into new instance
            rag2 = TensorRAG(tensor_db=populated_db)
            rag2.load_index(index_path)

            # Should have same content
            assert rag2.index_size == rag1.index_size


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_search_with_single_tensor(self, temp_db):
        """Test search with only one tensor in database."""
        # Add single tensor
        tensor = TTMTensor.from_arrays(
            context=np.array([0.5] * 8, dtype=np.float32),
            biology=np.array([0.5] * 4, dtype=np.float32),
            behavior=np.array([0.5] * 8, dtype=np.float32),
        )
        record = TensorRecord(
            tensor_id="only_tensor",
            entity_id="only_entity",
            world_id="only_world",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.9,
            training_cycles=50,
            description="The only tensor",
        )
        temp_db.save_tensor(record)

        rag = TensorRAG(tensor_db=temp_db)
        results = rag.search("anything")

        assert len(results) <= 1

    def test_compose_single_tensor(self, tensor_rag):
        """Test composition with single tensor."""
        results = tensor_rag.search("detective", n_results=1)

        if results:
            composed = tensor_rag.compose(results)
            assert isinstance(composed, TTMTensor)

    def test_compose_empty_list(self, tensor_rag):
        """Test composition with empty list raises or returns default."""
        with pytest.raises((ValueError, IndexError)):
            tensor_rag.compose([])

    def test_invalid_composition_method(self, tensor_rag):
        """Test invalid composition method raises error."""
        results = tensor_rag.search("detective", n_results=2)

        if len(results) >= 2:
            with pytest.raises(ValueError):
                tensor_rag.compose(results, method="invalid_method")


# ============================================================================
# Test Integration with Training Pipeline
# ============================================================================

class TestPipelineIntegration:
    """Tests for integration with the training pipeline."""

    def test_add_trained_tensor_to_index(self, tensor_rag, sample_tensors):
        """Test adding a newly trained tensor to the index."""
        initial_size = tensor_rag.index_size

        # Simulate adding a new trained tensor
        new_tensor = TTMTensor.from_arrays(
            context=np.array([0.6] * 8, dtype=np.float32),
            biology=np.array([0.4] * 4, dtype=np.float32),
            behavior=np.array([0.5] * 8, dtype=np.float32),
        )

        tensor_rag.add_tensor(
            tensor_id="new_trained_tensor",
            tensor=new_tensor,
            description="Newly trained medieval knight",
            maturity=0.96
        )

        assert tensor_rag.index_size == initial_size + 1

        # Should be searchable
        results = tensor_rag.search("medieval knight")
        tensor_ids = [r.tensor_id for r in results]
        assert "new_trained_tensor" in tensor_ids

    def test_update_tensor_in_index(self, tensor_rag):
        """Test updating a tensor in the index after retraining."""
        # Get original tensor
        original_results = tensor_rag.search("Victorian detective", n_results=1)

        if original_results:
            tensor_id = original_results[0].tensor_id

            # Update with new tensor (simulating retraining)
            updated_tensor = TTMTensor.from_arrays(
                context=np.array([0.95] * 8, dtype=np.float32),
                biology=np.array([0.5] * 4, dtype=np.float32),
                behavior=np.array([0.8] * 8, dtype=np.float32),
            )

            tensor_rag.update_tensor(
                tensor_id=tensor_id,
                tensor=updated_tensor,
                description="Highly trained Victorian detective expert",
                maturity=0.99
            )

            # Search should still find it
            new_results = tensor_rag.search("Victorian detective expert", n_results=5)
            tensor_ids = [r.tensor_id for r in new_results]
            assert tensor_id in tensor_ids
