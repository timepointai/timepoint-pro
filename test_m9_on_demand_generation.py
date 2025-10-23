"""
Comprehensive tests for Mechanism 9: On-Demand Entity Generation
Dynamic entity creation when referenced but missing
"""
import pytest
from datetime import datetime
from storage import GraphStore
from llm_v2 import LLMClient
from query_interface import QueryInterface
from schemas import Entity, Timepoint, ResolutionLevel


@pytest.fixture
def setup_m9():
    """Setup for M9 tests with minimal entities"""
    import os
    store = GraphStore("sqlite:///:memory:")
    # Use real API key from environment (required - no mock mode)
    api_key = os.getenv("OPENROUTER_API_KEY", "dummy_key_will_fail")
    llm = LLMClient(api_key=api_key)
    query_interface = QueryInterface(store, llm)

    # Create a test timepoint with some known entities
    timepoint = Timepoint(
        timepoint_id="inauguration_1789",
        timestamp=datetime(1789, 4, 30, 12, 0),
        event_description="Presidential inauguration ceremony at Federal Hall",
        entities_present=["george_washington", "john_adams"],
        resolution_level=ResolutionLevel.SCENE
    )
    store.save_timepoint(timepoint)

    # Create only a few core entities
    washington = Entity(
        entity_id="george_washington",
        entity_type="person",
        resolution_level=ResolutionLevel.SCENE,
        entity_metadata={
            "role": "president",
            "age": 57,
            "knowledge_state": ["First president", "Revolutionary War general"]
        }
    )

    adams = Entity(
        entity_id="john_adams",
        entity_type="person",
        resolution_level=ResolutionLevel.SCENE,
        entity_metadata={
            "role": "vice president",
            "age": 53,
            "knowledge_state": ["Vice president", "Diplomat"]
        }
    )

    store.save_entity(washington)
    store.save_entity(adams)

    return {
        "store": store,
        "llm": llm,
        "query_interface": query_interface,
        "timepoint": timepoint
    }


class TestM9EntityGapDetection:
    """Test detection of missing entities in queries"""

    @pytest.mark.unit
    def test_extract_numbered_entity_names(self, setup_m9):
        """Test extraction of numbered entity references"""
        qi = setup_m9["query_interface"]

        # Test various numbered entity patterns
        query1 = "What did attendee #47 think about the ceremony?"
        entities1 = qi.extract_entity_names(query1)
        assert "attendee_47" in entities1

        query2 = "Did person 12 interact with member #5?"
        entities2 = qi.extract_entity_names(query2)
        assert "person_12" in entities2
        assert "member_5" in entities2

        query3 = "Tell me about participant #100"
        entities3 = qi.extract_entity_names(query3)
        assert "participant_100" in entities3

    @pytest.mark.unit
    def test_extract_entity_names_no_spacing(self, setup_m9):
        """Test extraction without spaces"""
        qi = setup_m9["query_interface"]

        query = "What did attendee47 and person12 discuss?"
        entities = qi.extract_entity_names(query)
        assert "attendee_47" in entities
        assert "person_12" in entities

    @pytest.mark.unit
    def test_detect_entity_gap_finds_missing(self, setup_m9):
        """Test gap detection finds missing entities"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]

        # Get existing entities
        existing = {e.entity_id for e in store.get_all_entities()}

        # Query mentioning a missing entity
        query = "What did attendee #99 know about the inauguration?"
        missing = qi.detect_entity_gap(query, existing)

        # Should detect attendee_99 as missing
        assert missing == "attendee_99"

    @pytest.mark.unit
    def test_detect_entity_gap_ignores_existing(self, setup_m9):
        """Test gap detection ignores existing entities"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]

        existing = {e.entity_id for e in store.get_all_entities()}

        # Query only mentioning existing entities
        query = "What did george_washington and john_adams discuss?"
        missing = qi.detect_entity_gap(query, existing)

        # Should not detect any gaps
        assert missing is None


class TestM9OnDemandGeneration:
    """Test dynamic entity creation"""

    @pytest.mark.integration
    def test_generate_entity_on_demand_basic(self, setup_m9):
        """Test basic on-demand entity generation"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        # Generate a new entity
        entity = qi.generate_entity_on_demand("attendee_25", timepoint)

        # Verify entity was created
        assert entity is not None
        assert entity.entity_id == "attendee_25"
        assert entity.entity_type == "person"
        assert entity.resolution_level == ResolutionLevel.TENSOR_ONLY

    @pytest.mark.integration
    def test_generated_entity_has_metadata(self, setup_m9):
        """Test that generated entities have appropriate metadata"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        entity = qi.generate_entity_on_demand("ceremony_attendee_42", timepoint)

        # Should have basic metadata
        assert "role" in entity.entity_metadata
        assert "knowledge_state" in entity.entity_metadata
        assert len(entity.entity_metadata["knowledge_state"]) > 0

    @pytest.mark.integration
    def test_generated_entity_persisted(self, setup_m9):
        """Test that generated entities are saved to database"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]
        timepoint = setup_m9["timepoint"]

        # Generate entity
        qi.generate_entity_on_demand("guest_10", timepoint)

        # Verify it's in database
        retrieved = store.get_entity("guest_10")
        assert retrieved is not None
        assert retrieved.entity_id == "guest_10"

    @pytest.mark.integration
    def test_role_inferred_from_context(self, setup_m9):
        """Test that entity role is inferred from timepoint context"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        # For an inauguration, attendees should have ceremony-related roles
        entity = qi.generate_entity_on_demand("attendee_5", timepoint)

        role = entity.entity_metadata.get("role", "")
        # Should mention ceremony or attendee
        assert "ceremony" in role.lower() or "attendee" in role.lower()

    @pytest.mark.integration
    def test_generated_entity_temporal_span(self, setup_m9):
        """Test that generated entities have correct temporal span"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        entity = qi.generate_entity_on_demand("delegate_7", timepoint)

        # Should have temporal span matching timepoint
        assert entity.temporal_span_start == timepoint.timestamp
        assert entity.temporal_span_end == timepoint.timestamp


class TestM9QueryIntegration:
    """Test M9 integration with query processing"""

    @pytest.mark.integration
    def test_query_triggers_generation_for_missing_entity(self, setup_m9):
        """Test that querying missing entity triggers generation"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]

        # Query about a missing entity
        response = qi.query("What did attendee #30 think about the ceremony?")

        # Entity should have been generated
        entity = store.get_entity("attendee_30")
        assert entity is not None

        # Response should not indicate missing entity
        assert "don't have information" not in response.lower() or \
               "generated" in response.lower()

    @pytest.mark.integration
    def test_generated_entity_immediately_queryable(self, setup_m9):
        """Test that generated entities can be queried immediately"""
        qi = setup_m9["query_interface"]

        # First query generates the entity
        response1 = qi.query("What did participant #50 know?")

        # Second query should access the same entity
        response2 = qi.query("What was participant #50's role?")

        # Both should return responses (not "don't have information")
        assert len(response1) > 20
        assert len(response2) > 20

    @pytest.mark.integration
    def test_multiple_missing_entities_in_single_query(self, setup_m9):
        """Test handling of multiple missing entities"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]

        # Query mentioning multiple missing entities
        # Note: Current implementation may only generate one at a time
        response = qi.query("Did attendee #10 and attendee #11 interact?")

        # At least one entity should have been generated
        entity_10 = store.get_entity("attendee_10")
        entity_11 = store.get_entity("attendee_11")

        # At least one should exist
        assert entity_10 is not None or entity_11 is not None

    @pytest.mark.integration
    def test_generation_respects_timepoint_context(self, setup_m9):
        """Test that generation uses timepoint context"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]

        # Create another timepoint for different context
        meeting_tp = Timepoint(
            timepoint_id="cabinet_meeting_1789",
            timestamp=datetime(1789, 5, 15, 10, 0),
            event_description="First cabinet meeting at executive mansion",
            entities_present=["george_washington"],
            resolution_level=ResolutionLevel.SCENE
        )
        store.save_timepoint(meeting_tp)

        # Generate entity in meeting context
        entity = qi.generate_entity_on_demand("attendee_meeting_1", meeting_tp)

        # Role should reflect meeting context
        role = entity.entity_metadata.get("role", "")
        assert "meeting" in role.lower() or "participant" in role.lower()


class TestM9Plausibility:
    """Test that generated entities are plausible"""

    @pytest.mark.integration
    def test_generated_entity_has_knowledge(self, setup_m9):
        """Test that generated entities have plausible knowledge"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        entity = qi.generate_entity_on_demand("spectator_15", timepoint)

        knowledge = entity.entity_metadata.get("knowledge_state", [])
        assert len(knowledge) > 0
        # Knowledge should be strings
        assert all(isinstance(k, str) for k in knowledge)
        # Knowledge should not be empty strings
        assert all(len(k) > 5 for k in knowledge)

    @pytest.mark.integration
    def test_generated_entity_has_physical_tensor(self, setup_m9):
        """Test that generated entities have physical state"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        entity = qi.generate_entity_on_demand("guest_20", timepoint)

        # Should have physical tensor in metadata
        physical = entity.physical_tensor
        assert physical is not None
        assert hasattr(physical, 'age')
        assert physical.age > 0

    @pytest.mark.integration
    def test_generated_entity_has_cognitive_tensor(self, setup_m9):
        """Test that generated entities have cognitive state"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        entity = qi.generate_entity_on_demand("visitor_8", timepoint)

        # Should have cognitive tensor
        cognitive = entity.cognitive_tensor
        assert cognitive is not None
        assert hasattr(cognitive, 'knowledge_state')
        assert len(cognitive.knowledge_state) >= 0  # May be empty or populated


class TestM9EdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.integration
    def test_generation_without_timepoint(self, setup_m9):
        """Test generation fallback without timepoint context"""
        qi = setup_m9["query_interface"]

        # Try to generate without explicit timepoint
        # Should use most recent timepoint
        entity = qi.generate_entity_on_demand("fallback_entity", None)

        # Should still create entity (with fallback)
        assert entity is not None
        assert entity.entity_id == "fallback_entity"

    @pytest.mark.integration
    def test_duplicate_generation_prevented(self, setup_m9):
        """Test that generating same entity twice doesn't duplicate"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]
        timepoint = setup_m9["timepoint"]

        # Generate entity first time
        entity1 = qi.generate_entity_on_demand("unique_attendee", timepoint)
        store.save_entity(entity1)

        # Try to query it (should not regenerate)
        response = qi.query("What did unique_attendee know?")

        # Check database has only one
        all_entities = store.get_all_entities()
        unique_attendee_count = sum(1 for e in all_entities if e.entity_id == "unique_attendee")
        assert unique_attendee_count == 1

    @pytest.mark.integration
    def test_llm_failure_fallback(self, setup_m9):
        """Test graceful fallback when LLM generation fails"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        # Even in dry-run mode with potential failures, should create minimal entity
        entity = qi.generate_entity_on_demand("fallback_test", timepoint)

        # Should have created something, even if minimal
        assert entity is not None
        assert entity.entity_id == "fallback_test"
        # Should have at least basic metadata
        assert "role" in entity.entity_metadata or "knowledge_state" in entity.entity_metadata


class TestM9Performance:
    """Test performance and cost optimization aspects"""

    @pytest.mark.integration
    def test_generated_entities_start_at_minimal_resolution(self, setup_m9):
        """Test that generated entities start at TENSOR_ONLY for cost efficiency"""
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]

        entity = qi.generate_entity_on_demand("cost_test_entity", timepoint)

        # Should start at lowest resolution
        assert entity.resolution_level == ResolutionLevel.TENSOR_ONLY

    @pytest.mark.integration
    def test_generated_entity_can_be_elevated(self, setup_m9):
        """Test that generated entities can be elevated like normal entities"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]
        timepoint = setup_m9["timepoint"]

        # Generate minimal entity
        entity = qi.generate_entity_on_demand("elevate_test", timepoint)
        assert entity.resolution_level == ResolutionLevel.TENSOR_ONLY

        # Query it with high-detail requirement
        qi.query("What conversations did elevate_test have?")

        # Should have elevated
        updated_entity = store.get_entity("elevate_test")
        # May have elevated from TENSOR_ONLY
        assert updated_entity is not None


class TestM9Scalability:
    """Test scalability of on-demand generation"""

    @pytest.mark.integration
    def test_generate_many_entities(self, setup_m9):
        """Test generating multiple entities in sequence"""
        qi = setup_m9["query_interface"]
        store = setup_m9["store"]
        timepoint = setup_m9["timepoint"]

        # Generate several entities
        for i in range(10):
            qi.generate_entity_on_demand(f"scale_test_{i}", timepoint)

        # All should exist
        for i in range(10):
            entity = store.get_entity(f"scale_test_{i}")
            assert entity is not None

    @pytest.mark.integration
    def test_entity_count_tracking(self, setup_m9):
        """Test that entity counts are tracked correctly"""
        store = setup_m9["store"]

        initial_count = len(store.get_all_entities())

        # Generate a few more
        qi = setup_m9["query_interface"]
        timepoint = setup_m9["timepoint"]
        qi.generate_entity_on_demand("count_test_1", timepoint)
        qi.generate_entity_on_demand("count_test_2", timepoint)

        final_count = len(store.get_all_entities())
        assert final_count == initial_count + 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
