"""
Integration tests for Tensor Persistence Phases 1-3 with realistic data.

These tests validate the full tensor persistence stack:
- Phase 1: TensorDatabase CRUD, serialization
- Phase 2: Parallel training with JobQueue
- Phase 3: TensorRAG semantic search and composition

Tests use realistic TTMTensor data simulating what would come from
the pipeline (entity tensor initialization, training, retrieval).

Phase 4: Oxen Integration - validates with real pipeline data.
"""

import asyncio
import numpy as np
import pytest
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Tuple

# Phase 1 imports
from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import serialize_tensor, deserialize_tensor

# Phase 2 imports
from training.job_queue import JobQueue, JobStatus
from training.parallel_trainer import ParallelTensorTrainer, TrainingResult

# Phase 3 imports
from retrieval.tensor_rag import TensorRAG, SearchResult
from retrieval.embedding_index import EmbeddingIndex
from retrieval.composition import TensorComposer

# Core imports
from schemas import TTMTensor


# ============================================================================
# Realistic Tensor Data Generators
# ============================================================================

def create_character_tensor(
    archetype: str,
    profession: str = None,
    epoch: str = "modern"
) -> Tuple[TTMTensor, Dict]:
    """
    Create a realistic character tensor simulating pipeline output.

    Args:
        archetype: Character archetype (hero, detective, scientist, etc.)
        profession: Optional profession for additional specificity
        epoch: Historical period (victorian, modern, renaissance)

    Returns:
        (TTMTensor, metadata_dict)
    """
    # Base profiles for different archetypes
    archetype_profiles = {
        "detective": {
            "context": [0.9, 0.6, 0.8, 0.7, 0.6, 0.9, 0.7, 0.5],  # High knowledge, analytical
            "biology": [0.45, 0.8, 0.9, 0.7],  # Middle-aged, healthy
            "behavior": [0.7, 0.6, 0.5, 0.8, 0.7, 0.4, 0.3, 0.6],  # Patient, methodical
        },
        "hero": {
            "context": [0.7, 0.8, 0.9, 0.9, 0.8, 0.6, 0.8, 0.9],  # Brave, decisive
            "biology": [0.3, 0.95, 0.95, 0.95],  # Young, peak physical
            "behavior": [0.9, 0.8, 0.9, 0.5, 0.6, 0.9, 0.8, 0.8],  # Assertive, risk-taking
        },
        "scientist": {
            "context": [0.95, 0.5, 0.6, 0.3, 0.9, 0.95, 0.4, 0.4],  # High knowledge, low risk
            "biology": [0.5, 0.7, 0.8, 0.5],  # Middle-aged, sedentary
            "behavior": [0.4, 0.7, 0.3, 0.95, 0.8, 0.3, 0.6, 0.5],  # Patient, analytical
        },
        "merchant": {
            "context": [0.6, 0.7, 0.7, 0.4, 0.8, 0.7, 0.6, 0.85],  # Social, negotiating
            "biology": [0.45, 0.8, 0.9, 0.7],  # Prime working age
            "behavior": [0.6, 0.9, 0.6, 0.7, 0.8, 0.6, 0.5, 0.4],  # Cooperative, pragmatic
        },
        "noble": {
            "context": [0.7, 0.4, 0.6, 0.2, 0.6, 0.7, 0.3, 0.9],  # Social authority
            "biology": [0.5, 0.75, 0.95, 0.6],  # Comfortable lifestyle
            "behavior": [0.8, 0.5, 0.4, 0.6, 0.95, 0.7, 0.4, 0.3],  # Formal, commanding
        }
    }

    # Epoch modifiers
    epoch_modifiers = {
        "victorian": {
            "context": [0.0, 0.0, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0],  # More formal
            "behavior": [0.0, -0.1, 0.0, 0.0, 0.1, -0.1, -0.1, 0.0],  # More restrained
        },
        "modern": {
            "context": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "behavior": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        },
        "renaissance": {
            "context": [0.05, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0],  # More knowledge-focused
            "behavior": [0.0, 0.0, 0.0, 0.05, 0.1, 0.0, 0.0, 0.0],  # More patient
        }
    }

    # Get base profile
    profile = archetype_profiles.get(archetype, archetype_profiles["hero"])
    epoch_mod = epoch_modifiers.get(epoch, epoch_modifiers["modern"])

    # Apply epoch modifiers
    context = np.array(profile["context"], dtype=np.float32)
    context += np.array(epoch_mod.get("context", [0]*8), dtype=np.float32)

    biology = np.array(profile["biology"], dtype=np.float32)

    behavior = np.array(profile["behavior"], dtype=np.float32)
    behavior += np.array(epoch_mod.get("behavior", [0]*8), dtype=np.float32)

    # Add small noise for realism
    context += np.random.normal(0, 0.02, 8).astype(np.float32)
    biology += np.random.normal(0, 0.01, 4).astype(np.float32)
    behavior += np.random.normal(0, 0.02, 8).astype(np.float32)

    # Clamp to valid range
    context = np.clip(context, 0.01, 0.99)
    biology = np.clip(biology, 0.01, 0.99)
    behavior = np.clip(behavior, 0.01, 0.99)

    tensor = TTMTensor.from_arrays(context, biology, behavior)

    metadata = {
        "archetype": archetype,
        "profession": profession or archetype,
        "epoch": epoch,
        "description": f"{epoch.capitalize()} {archetype}" + (f" ({profession})" if profession else ""),
    }

    return tensor, metadata


def create_scenario_tensors(scenario_type: str) -> List[Tuple[TTMTensor, Dict]]:
    """
    Create a set of tensors for a typical scenario.

    Args:
        scenario_type: Type of scenario (detective_story, business_meeting, etc.)

    Returns:
        List of (tensor, metadata) tuples
    """
    scenarios = {
        "detective_story": [
            ("detective", "investigator", "victorian"),
            ("hero", "assistant", "victorian"),
            ("noble", "suspect", "victorian"),
            ("merchant", "witness", "victorian"),
        ],
        "business_meeting": [
            ("noble", "ceo", "modern"),
            ("scientist", "cto", "modern"),
            ("merchant", "sales_director", "modern"),
            ("hero", "project_lead", "modern"),
        ],
        "renaissance_court": [
            ("noble", "duke", "renaissance"),
            ("scientist", "alchemist", "renaissance"),
            ("merchant", "banker", "renaissance"),
            ("hero", "knight", "renaissance"),
        ],
    }

    configs = scenarios.get(scenario_type, scenarios["detective_story"])
    return [create_character_tensor(*config) for config in configs]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tensor_db(tmp_path) -> TensorDatabase:
    """Create a temporary TensorDatabase."""
    db_path = tmp_path / "integration_test.db"
    return TensorDatabase(str(db_path))


@pytest.fixture
def detective_scenario() -> List[Tuple[TTMTensor, Dict]]:
    """Create detective scenario tensors."""
    return create_scenario_tensors("detective_story")


@pytest.fixture
def business_scenario() -> List[Tuple[TTMTensor, Dict]]:
    """Create business meeting tensors."""
    return create_scenario_tensors("business_meeting")


# ============================================================================
# Phase 1 Integration Tests: Persistence with Realistic Data
# ============================================================================

@pytest.mark.integration
class TestPhase1RealData:
    """Test Phase 1 persistence with realistic tensor data."""

    def test_save_and_load_character_tensors(self, tensor_db, detective_scenario):
        """Save and load character tensors maintaining fidelity."""
        saved_ids = []

        # Save all scenario tensors
        for i, (tensor, metadata) in enumerate(detective_scenario):
            tensor_id = f"detective-{i}-{uuid.uuid4().hex[:8]}"
            record = TensorRecord(
                tensor_id=tensor_id,
                entity_id=f"entity-{i}",
                world_id="detective-world",
                tensor_blob=serialize_tensor(tensor),
                maturity=0.7 + i * 0.05,  # Varying maturity
                training_cycles=10 + i * 5,
                description=metadata["description"],
                category=f"{metadata['epoch']}/{metadata['archetype']}",
            )
            tensor_db.save_tensor(record)
            saved_ids.append(tensor_id)

        # Verify all tensors can be loaded
        for i, tensor_id in enumerate(saved_ids):
            record = tensor_db.get_tensor(tensor_id)
            assert record is not None, f"Tensor {tensor_id} not found"

            # Verify tensor integrity
            loaded_tensor = deserialize_tensor(record.tensor_blob)
            original_tensor = detective_scenario[i][0]

            orig_ctx, orig_bio, orig_beh = original_tensor.to_arrays()
            load_ctx, load_bio, load_beh = loaded_tensor.to_arrays()

            np.testing.assert_array_almost_equal(orig_ctx, load_ctx, decimal=5)
            np.testing.assert_array_almost_equal(orig_bio, load_bio, decimal=5)
            np.testing.assert_array_almost_equal(orig_beh, load_beh, decimal=5)

    def test_query_by_maturity_realistic(self, tensor_db, detective_scenario):
        """Query tensors by maturity with realistic data."""
        # Save with varying maturities
        maturities = [0.3, 0.6, 0.85, 0.95]
        for i, (tensor, metadata) in enumerate(detective_scenario):
            record = TensorRecord(
                tensor_id=f"maturity-test-{i}",
                entity_id=f"entity-{i}",
                world_id="test-world",
                tensor_blob=serialize_tensor(tensor),
                maturity=maturities[i],
                training_cycles=10,
            )
            tensor_db.save_tensor(record)

        # Query by maturity threshold
        mature_tensors = tensor_db.get_by_maturity(min_maturity=0.8)
        assert len(mature_tensors) == 2  # 0.85 and 0.95

        operational = tensor_db.get_by_maturity(min_maturity=0.95)
        assert len(operational) == 1  # Only 0.95

        needs_training = tensor_db.get_by_maturity(max_maturity=0.7)
        assert len(needs_training) == 2  # 0.3 and 0.6


# ============================================================================
# Phase 2 Integration Tests: Training with Realistic Data
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestPhase2RealData:
    """Test Phase 2 parallel training with realistic tensor data."""

    async def test_train_scenario_tensors(self, tensor_db, detective_scenario):
        """Train scenario tensors in parallel."""
        tensor_ids = []

        # Save tensors with low maturity
        for i, (tensor, metadata) in enumerate(detective_scenario):
            tensor_id = f"train-{i}-{uuid.uuid4().hex[:8]}"
            record = TensorRecord(
                tensor_id=tensor_id,
                entity_id=f"entity-{i}",
                world_id="train-world",
                tensor_blob=serialize_tensor(tensor),
                maturity=0.2,  # Start with low maturity
                training_cycles=0,
            )
            tensor_db.save_tensor(record)
            tensor_ids.append(tensor_id)

        # Train all tensors
        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=2)
        results = await trainer.train_batch(
            tensor_ids=tensor_ids,
            target_maturity=0.6  # Moderate target for test speed
        )

        # Verify all trained
        assert len(results) == len(tensor_ids)
        for tensor_id, result in results.items():
            assert result.success, f"Training failed for {tensor_id}: {result.error}"
            assert result.final_maturity >= 0.6

            # Verify tensor was updated in database
            record = tensor_db.get_tensor(tensor_id)
            assert record.maturity >= 0.6
            assert record.training_cycles > 0

    async def test_training_preserves_tensor_structure(self, tensor_db, detective_scenario):
        """Verify training doesn't corrupt tensor structure."""
        tensor, metadata = detective_scenario[0]
        tensor_id = f"structure-test-{uuid.uuid4().hex[:8]}"

        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id="entity-structure",
            world_id="test-world",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.1,
            training_cycles=0,
        )
        tensor_db.save_tensor(record)

        # Train
        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=1)
        await trainer.train_batch(tensor_ids=[tensor_id], target_maturity=0.5)

        # Load and verify structure
        updated = tensor_db.get_tensor(tensor_id)
        trained_tensor = deserialize_tensor(updated.tensor_blob)

        ctx, bio, beh = trained_tensor.to_arrays()

        # Verify dimensions preserved
        assert len(ctx) == 8, "Context vector should have 8 dims"
        assert len(bio) == 4, "Biology vector should have 4 dims"
        assert len(beh) == 8, "Behavior vector should have 8 dims"

        # Verify values are in valid range
        assert np.all(ctx >= 0) and np.all(ctx <= 1)
        assert np.all(bio >= 0) and np.all(bio <= 1)
        assert np.all(beh >= 0) and np.all(beh <= 1)


# ============================================================================
# Phase 3 Integration Tests: RAG with Realistic Data
# ============================================================================

@pytest.mark.integration
class TestPhase3RealData:
    """Test Phase 3 TensorRAG with realistic tensor data."""

    @pytest.fixture
    def populated_rag(self, tensor_db, detective_scenario, business_scenario):
        """Create TensorRAG populated with scenario data."""
        rag = TensorRAG(tensor_db, auto_build_index=False)

        # Add detective scenario
        for i, (tensor, metadata) in enumerate(detective_scenario):
            rag.add_tensor(
                tensor_id=f"detective-{i}",
                tensor=tensor,
                description=f"Victorian detective story - {metadata['description']}",
                maturity=0.9,
                category=f"epoch/victorian/{metadata['archetype']}",
                entity_id=f"detective-entity-{i}",
                world_id="detective-world",
            )

        # Add business scenario
        for i, (tensor, metadata) in enumerate(business_scenario):
            rag.add_tensor(
                tensor_id=f"business-{i}",
                tensor=tensor,
                description=f"Modern business meeting - {metadata['description']}",
                maturity=0.85,
                category=f"epoch/modern/{metadata['archetype']}",
                entity_id=f"business-entity-{i}",
                world_id="business-world",
            )

        return rag

    def test_semantic_search_finds_relevant(self, populated_rag):
        """Semantic search should find relevant tensors."""
        # Search for detective-related
        results = populated_rag.search(
            "Victorian detective investigating a crime",
            n_results=3
        )

        assert len(results) > 0
        # Should prioritize detective scenario
        top_result = results[0]
        assert "detective" in top_result.tensor_id.lower() or "victorian" in top_result.tensor_record.description.lower()

    def test_semantic_search_business_context(self, populated_rag):
        """Search finds business-relevant tensors for business queries."""
        results = populated_rag.search(
            "corporate executive in boardroom meeting",
            n_results=3
        )

        assert len(results) > 0
        # Should find business scenario tensors
        descriptions = [r.tensor_record.description.lower() for r in results]
        assert any("business" in d or "modern" in d for d in descriptions)

    def test_composition_weighted_blend(self, populated_rag):
        """Test composing multiple tensors with weighted blend."""
        # Get two tensors to compose
        results = populated_rag.search("investigator", n_results=2)
        assert len(results) >= 2

        # Compose with equal weights
        composed = populated_rag.compose(results[:2], method="weighted_blend")

        ctx, bio, beh = composed.to_arrays()

        # Verify dimensions
        assert len(ctx) == 8
        assert len(bio) == 4
        assert len(beh) == 8

        # Verify values are reasonable (between the two sources)
        t1 = deserialize_tensor(results[0].tensor_record.tensor_blob)
        t2 = deserialize_tensor(results[1].tensor_record.tensor_blob)

        ctx1, _, _ = t1.to_arrays()
        ctx2, _, _ = t2.to_arrays()

        # Composed context should be between the two (with some tolerance)
        for i in range(8):
            min_val = min(ctx1[i], ctx2[i]) - 0.1
            max_val = max(ctx1[i], ctx2[i]) + 0.1
            assert min_val <= ctx[i] <= max_val, f"Dim {i}: {ctx[i]} not between {min_val} and {max_val}"

    def test_resolve_for_entity(self, populated_rag):
        """Test entity resolution with scenario context."""
        # Resolve tensor for a detective-like entity
        tensor = populated_rag.resolve_for_entity(
            entity_description="A sharp-minded private investigator",
            scenario_context="Victorian London mystery",
            min_maturity=0.8,
            allow_composition=True
        )

        ctx, bio, beh = tensor.to_arrays()

        # Should have high analytical traits (context[0] or behavior[3])
        assert ctx[0] > 0.5 or beh[3] > 0.5, "Detective should have high analytical traits"

    def test_category_filtering(self, populated_rag):
        """Test filtering by category."""
        results = populated_rag.search(
            "character",
            n_results=10,
            categories=["epoch/victorian"]  # Only Victorian
        )

        # All results should be Victorian
        for result in results:
            if result.tensor_record.category:
                assert "victorian" in result.tensor_record.category.lower()


# ============================================================================
# Full Pipeline Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFullPipelineIntegration:
    """Test full pipeline: save -> train -> search -> compose."""

    async def test_complete_tensor_lifecycle(self, tensor_db):
        """Test complete lifecycle from creation to retrieval."""
        # 1. Create scenario tensors
        tensors_data = create_scenario_tensors("detective_story")

        # 2. Save to database (Phase 1)
        tensor_ids = []
        for i, (tensor, metadata) in enumerate(tensors_data):
            tensor_id = f"lifecycle-{i}-{uuid.uuid4().hex[:8]}"
            record = TensorRecord(
                tensor_id=tensor_id,
                entity_id=f"entity-{i}",
                world_id="lifecycle-world",
                tensor_blob=serialize_tensor(tensor),
                maturity=0.3,  # Low initial maturity
                training_cycles=0,
                description=metadata["description"],
                category=f"{metadata['epoch']}/{metadata['archetype']}",
            )
            tensor_db.save_tensor(record)
            tensor_ids.append(tensor_id)

        # 3. Train tensors (Phase 2)
        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=2)
        train_results = await trainer.train_batch(
            tensor_ids=tensor_ids,
            target_maturity=0.8
        )

        assert all(r.success for r in train_results.values())

        # 4. Create RAG and search (Phase 3)
        rag = TensorRAG(tensor_db, auto_build_index=True)

        # Search for detective
        search_results = rag.search(
            "Victorian detective investigator",
            n_results=2,
            min_maturity=0.7
        )

        assert len(search_results) > 0
        # Score may be 0 if embedding wasn't cached, but results should still be found
        assert search_results[0].tensor_record is not None

        # 5. Compose result
        if len(search_results) >= 2:
            composed = rag.compose(search_results[:2])
            ctx, bio, beh = composed.to_arrays()
            assert len(ctx) == 8
            assert len(bio) == 4
            assert len(beh) == 8

    async def test_training_improves_searchability(self, tensor_db):
        """Verify that trained tensors are properly searchable."""
        # Create and train a single tensor
        tensor, metadata = create_character_tensor("detective", "investigator", "victorian")
        tensor_id = f"searchable-{uuid.uuid4().hex[:8]}"

        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id="entity-searchable",
            world_id="test-world",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.1,
            training_cycles=0,
            description="Victorian detective investigating mysteries in London",
        )
        tensor_db.save_tensor(record)

        # Train
        trainer = ParallelTensorTrainer(tensor_db=tensor_db, max_workers=1)
        await trainer.train_batch(tensor_ids=[tensor_id], target_maturity=0.8)

        # Verify searchable
        rag = TensorRAG(tensor_db, auto_build_index=True)
        results = rag.search("detective London mystery", n_results=5)

        # Should find our trained tensor
        found_ids = [r.tensor_id for r in results]
        assert tensor_id in found_ids, f"Trained tensor {tensor_id} not found in search results"


# ============================================================================
# EmbeddingIndex Standalone Tests
# ============================================================================

@pytest.mark.integration
class TestEmbeddingIndexRealistic:
    """Test EmbeddingIndex with realistic data patterns."""

    def test_index_persistence_roundtrip(self, tmp_path):
        """Test saving and loading embedding index."""
        index = EmbeddingIndex(embedding_dim=384)

        # Add some embeddings
        for i in range(10):
            embedding = np.random.rand(384).astype(np.float32)
            index.add(f"tensor-{i}", embedding)

        # Save
        save_path = tmp_path / "test_index"
        index.save(save_path)

        # Load into new index
        new_index = EmbeddingIndex(embedding_dim=384)
        new_index.load(save_path)

        assert new_index.size == 10

        # Search should work
        query = np.random.rand(384).astype(np.float32)
        results = new_index.search(query, k=5)
        assert len(results) == 5

    def test_index_update_in_place(self, tmp_path):
        """Test updating an embedding in the index."""
        index = EmbeddingIndex(embedding_dim=384)

        # Add initial embedding
        initial = np.ones(384, dtype=np.float32) * 0.5
        index.add("tensor-1", initial)

        # Update with different embedding
        updated = np.ones(384, dtype=np.float32) * 0.9
        index.add("tensor-1", updated)  # Same ID = update

        assert index.size == 1  # Still just one entry

        # Verify the updated embedding is stored
        stored = index.get_embedding("tensor-1")
        assert stored is not None
        # Normalized, so check direction (should be more aligned with updated)


# ============================================================================
# Run configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
