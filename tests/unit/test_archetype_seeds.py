"""
Unit tests for archetype seed tensors (Phase 7).

Tests the archetype system that uses the REAL Timepoint tensor pipeline
for generating tensors, not hardcoded values.
"""

import pytest
import tempfile
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from retrieval.archetype_seeds import (
    ArchetypeSeed,
    ALL_ARCHETYPES,
    CORPORATE_ARCHETYPES,
    DETECTIVE_ARCHETYPES,
    HISTORICAL_ARCHETYPES,
    MEDICAL_ARCHETYPES,
    GENERIC_ARCHETYPES,
    get_archetype_by_id,
    get_archetypes_by_category,
    archetype_to_tensor,
    create_archetype_entity,
    get_best_archetype_match,
)
from schemas import TTMTensor, Entity
from tensor_persistence import TensorDatabase


class TestArchetypeSeedStructure:
    """Tests for archetype seed data structure."""

    def test_all_archetypes_have_required_fields(self):
        """Test that all archetypes have required fields."""
        for archetype in ALL_ARCHETYPES:
            assert archetype.archetype_id, f"Missing archetype_id"
            assert archetype.name, f"Missing name for {archetype.archetype_id}"
            assert archetype.description, f"Missing description for {archetype.archetype_id}"
            assert archetype.category, f"Missing category for {archetype.archetype_id}"
            assert archetype.role, f"Missing role for {archetype.archetype_id}"
            assert archetype.background, f"Missing background for {archetype.archetype_id}"
            assert archetype.tags, f"Missing tags for {archetype.archetype_id}"

    def test_unique_archetype_ids(self):
        """Test that all archetype IDs are unique."""
        ids = [a.archetype_id for a in ALL_ARCHETYPES]
        assert len(ids) == len(set(ids)), "Duplicate archetype IDs found"

    def test_personality_hints_in_valid_range(self):
        """Test that personality hints are in valid range (0-1)."""
        for archetype in ALL_ARCHETYPES:
            for trait, value in archetype.personality_hints.items():
                assert 0.0 <= value <= 1.0, f"{trait} out of range for {archetype.archetype_id}"

    def test_archetype_has_to_entity_metadata(self):
        """Test that archetypes can convert to entity metadata."""
        for archetype in ALL_ARCHETYPES:
            metadata = archetype.to_entity_metadata()
            assert "role" in metadata
            assert "description" in metadata
            assert "background" in metadata
            assert metadata["role"] == archetype.role


class TestArchetypeCollections:
    """Tests for archetype collections."""

    def test_corporate_archetypes_exist(self):
        """Test that corporate archetypes collection is populated."""
        assert len(CORPORATE_ARCHETYPES) >= 3
        assert any("ceo" in a.archetype_id for a in CORPORATE_ARCHETYPES)
        assert any("cfo" in a.archetype_id for a in CORPORATE_ARCHETYPES)

    def test_detective_archetypes_exist(self):
        """Test that detective archetypes collection is populated."""
        assert len(DETECTIVE_ARCHETYPES) >= 2
        assert any("detective" in a.archetype_id for a in DETECTIVE_ARCHETYPES)

    def test_historical_archetypes_exist(self):
        """Test that historical archetypes collection is populated."""
        assert len(HISTORICAL_ARCHETYPES) >= 2
        assert any("diplomat" in a.archetype_id for a in HISTORICAL_ARCHETYPES)

    def test_medical_archetypes_exist(self):
        """Test that medical archetypes collection is populated."""
        assert len(MEDICAL_ARCHETYPES) >= 2
        assert any("doctor" in a.archetype_id for a in MEDICAL_ARCHETYPES)

    def test_generic_archetypes_exist(self):
        """Test that generic archetypes collection is populated."""
        assert len(GENERIC_ARCHETYPES) >= 2
        assert any("neutral" in a.archetype_id for a in GENERIC_ARCHETYPES)

    def test_all_archetypes_aggregation(self):
        """Test that ALL_ARCHETYPES contains all collections."""
        total = (
            len(CORPORATE_ARCHETYPES) +
            len(DETECTIVE_ARCHETYPES) +
            len(HISTORICAL_ARCHETYPES) +
            len(MEDICAL_ARCHETYPES) +
            len(GENERIC_ARCHETYPES)
        )
        assert len(ALL_ARCHETYPES) == total


class TestArchetypeLookup:
    """Tests for archetype lookup functions."""

    def test_get_archetype_by_id_found(self):
        """Test getting archetype by ID when it exists."""
        ceo = get_archetype_by_id("archetype_ceo")
        assert ceo is not None
        assert ceo.name == "Chief Executive Officer"

    def test_get_archetype_by_id_not_found(self):
        """Test getting archetype by ID when it doesn't exist."""
        result = get_archetype_by_id("archetype_nonexistent")
        assert result is None

    def test_get_archetypes_by_category_prefix(self):
        """Test getting archetypes by category prefix."""
        corporate = get_archetypes_by_category("corporate")
        assert len(corporate) >= 3
        for a in corporate:
            assert a.category.startswith("corporate")

    def test_get_archetypes_by_subcategory(self):
        """Test getting archetypes by specific subcategory."""
        executives = get_archetypes_by_category("corporate/executive")
        assert len(executives) >= 2
        for a in executives:
            assert a.category.startswith("corporate/executive")


class TestCreateArchetypeEntity:
    """Tests for creating Entity from archetype."""

    def test_create_archetype_entity(self):
        """Test creating an Entity from an archetype."""
        ceo = get_archetype_by_id("archetype_ceo")
        entity = create_archetype_entity(ceo)

        assert isinstance(entity, Entity)
        assert entity.entity_id == "archetype_ceo"
        assert entity.entity_type == "human"
        assert entity.entity_metadata["role"] == "CEO"

    def test_entity_has_physical_tensor(self):
        """Test that created entity has physical tensor defaults."""
        detective = get_archetype_by_id("archetype_detective")
        entity = create_archetype_entity(detective)

        assert "physical_tensor" in entity.entity_metadata
        assert entity.entity_metadata["physical_tensor"]["age"] == 40.0

    def test_entity_has_personality_traits(self):
        """Test that created entity has personality traits from hints."""
        ceo = get_archetype_by_id("archetype_ceo")
        entity = create_archetype_entity(ceo)

        assert "personality_traits" in entity.entity_metadata
        # Should have 5 traits from Big Five hints
        assert len(entity.entity_metadata["personality_traits"]) == 5


class TestLegacyArchetypeToTensor:
    """Tests for legacy archetype_to_tensor function (backward compatibility)."""

    def test_archetype_to_tensor_creates_valid_tensor(self):
        """Test that legacy function creates a valid TTMTensor."""
        ceo = get_archetype_by_id("archetype_ceo")
        tensor = archetype_to_tensor(ceo)

        assert isinstance(tensor, TTMTensor)
        context, biology, behavior = tensor.to_arrays()

        assert len(context) == 8
        assert len(biology) == 4
        assert len(behavior) == 8

    def test_archetype_to_tensor_uses_personality_hints(self):
        """Test that legacy function uses personality hints in behavior vector."""
        detective = get_archetype_by_id("archetype_detective")
        tensor = archetype_to_tensor(detective)
        _, _, behavior = tensor.to_arrays()

        # Behavior[0] should be openness
        assert behavior[0] == pytest.approx(detective.personality_hints["openness"], rel=0.01)

    def test_archetype_tensor_dtype(self):
        """Test that tensor arrays have numeric dtype."""
        neutral = get_archetype_by_id("archetype_neutral")
        tensor = archetype_to_tensor(neutral)
        context, biology, behavior = tensor.to_arrays()

        # Accept float32 or float64 - both are valid numeric types
        assert np.issubdtype(context.dtype, np.floating)
        assert np.issubdtype(biology.dtype, np.floating)
        assert np.issubdtype(behavior.dtype, np.floating)


class TestBestArchetypeMatch:
    """Tests for keyword-based archetype matching."""

    def test_match_ceo_by_role(self):
        """Test matching CEO by role keyword."""
        match = get_best_archetype_match(
            role="CEO",
            entity_type="human"
        )
        assert match is not None
        assert "ceo" in match.archetype_id.lower() or "executive" in match.name.lower()

    def test_match_detective_by_role(self):
        """Test matching Detective by role keyword."""
        match = get_best_archetype_match(
            role="Detective",
            entity_type="human"
        )
        assert match is not None
        assert "detective" in match.archetype_id.lower()

    def test_match_by_description(self):
        """Test matching by description keywords."""
        match = get_best_archetype_match(
            role="unknown",
            entity_type="human",
            description="investigator who observes and deduces"
        )
        assert match is not None
        # Should match detective or forensic expert

    def test_no_match_returns_none_or_generic(self):
        """Test that poor matches return None or generic."""
        match = get_best_archetype_match(
            role="xyz123",
            entity_type="object",
            description="completely unrelated"
        )
        # Should either be None or a weak generic match
        if match is not None:
            assert match.archetype_id in ["archetype_neutral", "archetype_follower", "archetype_leader"]


class TestArchetypeSpecifics:
    """Tests for specific archetype characteristics."""

    def test_ceo_has_leadership_tags(self):
        """Test that CEO has leadership-related tags."""
        ceo = get_archetype_by_id("archetype_ceo")
        assert "leader" in ceo.tags or "executive" in ceo.tags
        assert "decision-maker" in ceo.tags

    def test_detective_has_analytical_personality(self):
        """Test that Detective has analytical personality hints."""
        detective = get_archetype_by_id("archetype_detective")
        # High conscientiousness for methodical nature
        assert detective.personality_hints["conscientiousness"] >= 0.8

    def test_neutral_has_balanced_traits(self):
        """Test that Neutral archetype has balanced personality."""
        neutral = get_archetype_by_id("archetype_neutral")
        # All traits should be around 0.5
        for trait, value in neutral.personality_hints.items():
            assert 0.4 <= value <= 0.6, f"{trait} not balanced in neutral archetype"


class TestTensorGenerationMocked:
    """Tests for tensor generation through real pipeline (mocked)."""

    @patch('tensor_initialization.populate_tensor_llm_guided')
    @patch('tensor_initialization.create_baseline_tensor')
    def test_generate_archetype_tensor_calls_pipeline(
        self, mock_baseline, mock_populate
    ):
        """Test that generate_archetype_tensor calls the real pipeline."""
        from retrieval.archetype_seeds import generate_archetype_tensor

        # Setup mocks
        mock_tensor = Mock(spec=TTMTensor)
        mock_tensor.to_arrays.return_value = (
            np.array([0.5] * 8),
            np.array([0.5] * 4),
            np.array([0.5] * 8)
        )
        mock_baseline.return_value = mock_tensor
        mock_populate.return_value = (mock_tensor, 0.65)

        mock_llm = Mock()

        # Generate
        ceo = get_archetype_by_id("archetype_ceo")
        tensor, maturity = generate_archetype_tensor(ceo, mock_llm, verbose=False)

        # Verify pipeline was called
        mock_baseline.assert_called_once()
        mock_populate.assert_called_once()

    @patch('tensor_initialization.populate_tensor_llm_guided')
    @patch('tensor_initialization.create_baseline_tensor')
    def test_generate_falls_back_on_error(
        self, mock_baseline, mock_populate
    ):
        """Test that generation falls back to baseline on error."""
        from retrieval.archetype_seeds import generate_archetype_tensor

        # Setup baseline mock
        mock_tensor = Mock(spec=TTMTensor)
        mock_tensor.to_arrays.return_value = (
            np.array([0.5] * 8),
            np.array([0.5] * 4),
            np.array([0.5] * 8)
        )
        mock_baseline.return_value = mock_tensor

        # Make populate fail
        mock_populate.side_effect = Exception("LLM error")

        mock_llm = Mock()

        # Generate - should not raise
        ceo = get_archetype_by_id("archetype_ceo")
        tensor, maturity = generate_archetype_tensor(ceo, mock_llm, verbose=False)

        # Should get baseline tensor back
        assert tensor == mock_tensor


class TestSeedDatabaseMocked:
    """Tests for database seeding (mocked LLM calls)."""

    @patch('retrieval.archetype_seeds.generate_archetype_tensor')
    def test_seed_database_creates_records(self, mock_generate):
        """Test that seeding creates tensor records in database."""
        from retrieval.archetype_seeds import seed_database_with_archetypes

        # Setup mock
        mock_tensor = Mock(spec=TTMTensor)
        mock_tensor.to_arrays.return_value = (
            np.array([0.5] * 8, dtype=np.float32),
            np.array([0.5] * 4, dtype=np.float32),
            np.array([0.5] * 8, dtype=np.float32)
        )
        mock_generate.return_value = (mock_tensor, 0.65)

        mock_llm = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tensors.db"
            db = TensorDatabase(str(db_path))

            # Seed with just 2 archetypes
            seeded = seed_database_with_archetypes(
                tensor_db=db,
                llm_client=mock_llm,
                archetypes=CORPORATE_ARCHETYPES[:2],
                world_id="test_seeds",
                verbose=False
            )

            assert seeded == 2

            # Verify records exist
            tensors = db.list_tensors()
            assert len(tensors) >= 2

    @patch('retrieval.archetype_seeds.generate_archetype_tensor')
    def test_seed_database_skips_existing(self, mock_generate):
        """Test that seeding skips existing archetypes."""
        from retrieval.archetype_seeds import seed_database_with_archetypes

        # Setup mock
        mock_tensor = Mock(spec=TTMTensor)
        mock_tensor.to_arrays.return_value = (
            np.array([0.5] * 8, dtype=np.float32),
            np.array([0.5] * 4, dtype=np.float32),
            np.array([0.5] * 8, dtype=np.float32)
        )
        mock_generate.return_value = (mock_tensor, 0.65)

        mock_llm = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tensors.db"
            db = TensorDatabase(str(db_path))

            # Seed twice
            seeded1 = seed_database_with_archetypes(
                tensor_db=db,
                llm_client=mock_llm,
                archetypes=CORPORATE_ARCHETYPES[:2],
                world_id="test_seeds",
                verbose=False
            )
            seeded2 = seed_database_with_archetypes(
                tensor_db=db,
                llm_client=mock_llm,
                archetypes=CORPORATE_ARCHETYPES[:2],
                world_id="test_seeds",
                verbose=False
            )

            assert seeded1 == 2
            assert seeded2 == 0  # Already exists

    @patch('retrieval.archetype_seeds.generate_archetype_tensor')
    def test_seed_database_regenerate_flag(self, mock_generate):
        """Test that regenerate flag forces regeneration."""
        from retrieval.archetype_seeds import seed_database_with_archetypes

        # Setup mock
        mock_tensor = Mock(spec=TTMTensor)
        mock_tensor.to_arrays.return_value = (
            np.array([0.5] * 8, dtype=np.float32),
            np.array([0.5] * 4, dtype=np.float32),
            np.array([0.5] * 8, dtype=np.float32)
        )
        mock_generate.return_value = (mock_tensor, 0.65)

        mock_llm = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tensors.db"
            db = TensorDatabase(str(db_path))

            # Seed first time
            seeded1 = seed_database_with_archetypes(
                tensor_db=db,
                llm_client=mock_llm,
                archetypes=CORPORATE_ARCHETYPES[:1],
                world_id="test_seeds",
                verbose=False
            )

            # Seed again with regenerate=True
            seeded2 = seed_database_with_archetypes(
                tensor_db=db,
                llm_client=mock_llm,
                archetypes=CORPORATE_ARCHETYPES[:1],
                world_id="test_seeds",
                regenerate=True,
                verbose=False
            )

            assert seeded1 == 1
            assert seeded2 == 1  # Regenerated
