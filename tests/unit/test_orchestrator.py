# ============================================================================
# test_orchestrator.py - Test suite for OrchestratorAgent
# ============================================================================
"""
Comprehensive test suite for the OrchestratorAgent and its components.

Tests:
1. SceneParser: Natural language → SceneSpecification
2. KnowledgeSeeder: Initial knowledge → ExposureEvents
3. RelationshipExtractor: Entity relationships → NetworkX graph
4. ResolutionAssigner: Role-based resolution targeting
5. OrchestratorAgent: End-to-end orchestration
6. Integration with existing workflows
"""

import pytest
import os
from datetime import datetime
from typing import Dict

from orchestrator import (
    OrchestratorAgent,
    SceneParser,
    KnowledgeSeeder,
    RelationshipExtractor,
    ResolutionAssigner,
    SceneSpecification,
    EntityRosterItem,
    TimepointSpec,
    simulate_event
)
from llm import LLMClient
from storage import GraphStore
from schemas import ResolutionLevel, TemporalMode


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def llm_client():
    """Create LLM client (dry run for fast tests)"""
    api_key = os.getenv("OPENROUTER_API_KEY", "test_key")
    # Use dry_run=True for unit tests, False for integration tests
    return LLMClient(api_key=api_key)


@pytest.fixture
def real_llm_client():
    """Create real LLM client for integration tests"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set, skipping real LLM tests")
    return LLMClient(api_key=api_key)


@pytest.fixture
def store():
    """Create test database"""
    store = GraphStore("sqlite:///:memory:")
    yield store
    # Cleanup
    store._clear_database()


@pytest.fixture
def sample_spec():
    """Sample scene specification for testing"""
    return SceneSpecification(
        scene_title="Test Constitutional Convention",
        scene_description="Founding fathers debate the constitution in Philadelphia",
        temporal_mode="pearl",
        temporal_scope={
            "start_date": "1787-05-25T09:00:00",
            "end_date": "1787-09-17T17:00:00",
            "location": "Philadelphia, Pennsylvania State House"
        },
        entities=[
            EntityRosterItem(
                entity_id="james_madison",
                entity_type="human",
                role="primary",
                description="Virginia delegate, Father of the Constitution",
                initial_knowledge=[
                    "separation_of_powers",
                    "virginia_plan",
                    "montesquieu_philosophy"
                ],
                relationships={
                    "alexander_hamilton": "ally",
                    "george_washington": "mentor"
                }
            ),
            EntityRosterItem(
                entity_id="alexander_hamilton",
                entity_type="human",
                role="primary",
                description="New York delegate, advocate for strong central government",
                initial_knowledge=[
                    "federalist_principles",
                    "economic_policy",
                    "new_york_politics"
                ],
                relationships={
                    "james_madison": "ally"
                }
            ),
            EntityRosterItem(
                entity_id="george_washington",
                entity_type="human",
                role="primary",
                description="Convention president, Revolutionary War general",
                initial_knowledge=[
                    "military_strategy",
                    "national_unity",
                    "revolutionary_war_experience"
                ],
                relationships={
                    "james_madison": "student"
                }
            ),
            EntityRosterItem(
                entity_id="pennsylvania_state_house",
                entity_type="building",
                role="environment",
                description="Meeting location, later called Independence Hall",
                initial_knowledge=[
                    "declaration_signed_here",
                    "summer_heat",
                    "closed_windows"
                ],
                relationships={}
            )
        ],
        timepoints=[
            TimepointSpec(
                timepoint_id="tp_001_opening",
                timestamp="1787-05-25T09:00:00",
                event_description="Convention opens, Washington elected president",
                entities_present=["james_madison", "alexander_hamilton", "george_washington"],
                importance=0.9,
                causal_parent=None
            ),
            TimepointSpec(
                timepoint_id="tp_002_virginia_plan",
                timestamp="1787-05-29T10:00:00",
                event_description="Madison presents Virginia Plan",
                entities_present=["james_madison", "george_washington"],
                importance=0.95,
                causal_parent="tp_001_opening"
            ),
            TimepointSpec(
                timepoint_id="tp_003_signing",
                timestamp="1787-09-17T16:00:00",
                event_description="Constitution signed by delegates",
                entities_present=["james_madison", "alexander_hamilton", "george_washington"],
                importance=1.0,
                causal_parent="tp_002_virginia_plan"
            )
        ],
        global_context="Summer 1787, Philadelphia. Secret convention to replace Articles of Confederation. Hot weather, windows closed for secrecy."
    )


# ============================================================================
# Component Tests
# ============================================================================

class TestSceneParser:
    """Test SceneParser component"""

    def test_parse_returns_spec(self, llm_client):
        """Test that parse returns a SceneSpecification"""
        parser = SceneParser(llm_client)
        spec = parser.parse("simulate a test event")

        assert isinstance(spec, SceneSpecification)
        assert spec.scene_title
        assert spec.temporal_mode in ["pearl", "directorial", "branching", "cyclical", "portal"]
        assert len(spec.entities) > 0
        assert len(spec.timepoints) > 0

    def test_parse_with_context(self, llm_client):
        """Test parse with context parameters"""
        parser = SceneParser(llm_client)
        context = {
            "temporal_mode": "directorial",
            "max_entities": 5,
            "max_timepoints": 3
        }
        spec = parser.parse("simulate a test event", context)

        assert isinstance(spec, SceneSpecification)
        # In dry run mode, this will use mock data, but structure should be valid

    def test_mock_specification(self, llm_client):
        """Test mock specification generation"""
        parser = SceneParser(llm_client)
        spec = parser._mock_scene_specification()

        assert spec.scene_title == "Test Scene"
        assert len(spec.entities) >= 2
        assert len(spec.timepoints) >= 1


class TestKnowledgeSeeder:
    """Test KnowledgeSeeder component"""

    def test_seed_knowledge(self, store, sample_spec):
        """Test knowledge seeding creates exposure events"""
        seeder = KnowledgeSeeder(store)
        exposure_map = seeder.seed_knowledge(sample_spec, create_exposure_events=False)

        # Should have exposure events for all entities with knowledge
        assert len(exposure_map) == len(sample_spec.entities)

        # Check madison's knowledge
        madison_events = exposure_map["james_madison"]
        assert len(madison_events) == 3
        assert all(e.entity_id == "james_madison" for e in madison_events)
        assert all(e.event_type == "initial" for e in madison_events)

    def test_seed_knowledge_saves_to_db(self, store, sample_spec):
        """Test that exposure events are saved to database"""
        seeder = KnowledgeSeeder(store)
        exposure_map = seeder.seed_knowledge(sample_spec, create_exposure_events=True)

        # Verify saved to database
        retrieved = store.get_exposure_events("james_madison")
        assert len(retrieved) == 3


class TestRelationshipExtractor:
    """Test RelationshipExtractor component"""

    def test_build_graph(self, sample_spec):
        """Test graph building from specification"""
        extractor = RelationshipExtractor()
        graph = extractor.build_graph(sample_spec)

        # Check nodes
        assert graph.number_of_nodes() == 4
        assert "james_madison" in graph.nodes
        assert "alexander_hamilton" in graph.nodes

        # Check declared relationships
        assert graph.has_edge("james_madison", "alexander_hamilton")
        edge_data = graph.get_edge_data("james_madison", "alexander_hamilton")
        assert edge_data["relationship"] == "ally"

        # Check edges exist
        assert graph.number_of_edges() > 0

    def test_relationship_weights(self, sample_spec):
        """Test relationship weight assignment"""
        extractor = RelationshipExtractor()

        assert extractor._relationship_weight("ally") == 0.9
        assert extractor._relationship_weight("enemy") == 0.1
        assert extractor._relationship_weight("neutral") == 0.3
        assert extractor._relationship_weight("unknown") == 0.5  # Default

    def test_copresence_edges(self, sample_spec):
        """Test that copresence edges are added"""
        extractor = RelationshipExtractor()
        graph = extractor.build_graph(sample_spec)

        # All entities in tp_001_opening should have copresence edges
        # Madison, Hamilton, Washington were all present
        assert graph.has_edge("james_madison", "george_washington") or \
               graph.has_edge("george_washington", "james_madison")


class TestResolutionAssigner:
    """Test ResolutionAssigner component"""

    def test_assign_resolutions(self, sample_spec):
        """Test resolution assignment based on roles"""
        extractor = RelationshipExtractor()
        graph = extractor.build_graph(sample_spec)

        assigner = ResolutionAssigner()
        assignments, _ = assigner.assign_resolutions(sample_spec, graph)

        # Primary actors should get high resolution
        assert assignments["james_madison"] in [ResolutionLevel.DIALOG, ResolutionLevel.TRAINED]
        assert assignments["alexander_hamilton"] in [ResolutionLevel.DIALOG, ResolutionLevel.TRAINED]

        # Environment entities should get low resolution
        assert assignments["pennsylvania_state_house"] == ResolutionLevel.TENSOR_ONLY

    def test_centrality_boosts_resolution(self, sample_spec):
        """Test that high centrality boosts resolution"""
        extractor = RelationshipExtractor()
        graph = extractor.build_graph(sample_spec)

        # Washington has high centrality (mentor to Madison)
        assigner = ResolutionAssigner()
        assignments, _ = assigner.assign_resolutions(sample_spec, graph)

        # Should get high resolution due to centrality
        washington_level = assignments["george_washington"]
        assert washington_level in [ResolutionLevel.DIALOG, ResolutionLevel.TRAINED]


# ============================================================================
# Integration Tests
# ============================================================================

class TestOrchestratorAgent:
    """Test complete OrchestratorAgent"""

    def test_orchestrate_dry_run(self, llm_client, store):
        """Test full orchestration in dry run mode"""
        orchestrator = OrchestratorAgent(llm_client, store)
        result = orchestrator.orchestrate(
            "simulate a test event",
            context={"max_entities": 3, "max_timepoints": 2},
            save_to_db=False
        )

        # Check result structure
        assert "specification" in result
        assert "entities" in result
        assert "timepoints" in result
        assert "graph" in result
        assert "exposure_events" in result
        assert "temporal_agent" in result

        # Check entities were created
        assert len(result["entities"]) > 0
        assert all(hasattr(e, "entity_id") for e in result["entities"])
        assert all(hasattr(e, "resolution_level") for e in result["entities"])

        # Check timepoints were created
        assert len(result["timepoints"]) > 0

    def test_orchestrate_saves_to_db(self, llm_client, store):
        """Test that orchestration saves to database"""
        orchestrator = OrchestratorAgent(llm_client, store)
        result = orchestrator.orchestrate(
            "simulate a test event",
            save_to_db=True
        )

        # Verify entities saved
        entities = store.get_all_entities()
        assert len(entities) > 0

        # Verify timepoints saved
        timepoints = store.get_all_timepoints()
        assert len(timepoints) > 0

    def test_create_entities_from_spec(self, llm_client, store, sample_spec):
        """Test entity creation from specification"""
        orchestrator = OrchestratorAgent(llm_client, store)

        extractor = RelationshipExtractor()
        graph = extractor.build_graph(sample_spec)

        assigner = ResolutionAssigner()
        resolution_assignments, _ = assigner.assign_resolutions(sample_spec, graph)

        seeder = KnowledgeSeeder(store)
        exposure_events = seeder.seed_knowledge(sample_spec, create_exposure_events=False)

        entities = orchestrator._create_entities(sample_spec, resolution_assignments, exposure_events)

        assert len(entities) == 4
        assert entities[0].entity_id == "james_madison"
        assert "cognitive_tensor" in entities[0].entity_metadata
        assert entities[0].entity_metadata["orchestrated"] is True

    def test_create_timepoints_from_spec(self, llm_client, store, sample_spec):
        """Test timepoint creation from specification"""
        orchestrator = OrchestratorAgent(llm_client, store)
        timepoints = orchestrator._create_timepoints(sample_spec)

        assert len(timepoints) == 3
        assert timepoints[0].timepoint_id == "tp_001_opening"
        assert timepoints[1].causal_parent == "tp_001_opening"
        assert timepoints[2].causal_parent == "tp_002_virginia_plan"

    def test_temporal_agent_creation(self, llm_client, store, sample_spec):
        """Test that temporal agent is created with correct mode"""
        orchestrator = OrchestratorAgent(llm_client, store)
        result = orchestrator.orchestrate(
            "simulate a test event",
            save_to_db=False
        )

        temporal_agent = result["temporal_agent"]
        assert temporal_agent is not None
        assert temporal_agent.mode in list(TemporalMode)


# ============================================================================
# End-to-End Tests
# ============================================================================

class TestEndToEnd:
    """End-to-end integration tests"""

    def test_constitutional_convention_dry_run(self, llm_client, store):
        """Test constitutional convention simulation (dry run)"""
        result = simulate_event(
            "simulate the constitutional convention in the united states",
            llm_client,
            store,
            context={"temporal_mode": "pearl", "max_entities": 10, "max_timepoints": 5},
            save_to_db=True
        )

        # Verify complete result
        assert result["specification"].scene_title
        assert len(result["entities"]) > 0
        assert len(result["timepoints"]) > 0
        assert result["graph"].number_of_nodes() > 0

        # Verify database persistence
        entities = store.get_all_entities()
        assert len(entities) > 0

        timepoints = store.get_all_timepoints()
        assert len(timepoints) > 0

    @pytest.mark.real_llm
    def test_constitutional_convention_real_llm(self, real_llm_client, store):
        """Test constitutional convention with real LLM calls"""
        result = simulate_event(
            "simulate the constitutional convention in the united states",
            real_llm_client,
            store,
            context={
                "temporal_mode": "pearl",
                "max_entities": 8,
                "max_timepoints": 5
            },
            save_to_db=True
        )

        # Verify scene specification quality
        spec = result["specification"]
        assert "constitutional" in spec.scene_title.lower() or "convention" in spec.scene_title.lower()
        assert "philadelphia" in spec.temporal_scope["location"].lower()

        # Verify entities include key figures
        entity_ids = [e.entity_id for e in result["entities"]]
        # At least some historical figures should be mentioned
        assert len(entity_ids) >= 3

        # Verify timepoints have causal structure
        timepoints = result["timepoints"]
        assert len(timepoints) >= 2
        # Later timepoints should have causal parents
        if len(timepoints) > 1:
            assert timepoints[1].causal_parent is not None

        print("\n📊 Real LLM Results:")
        print(f"   Scene: {spec.scene_title}")
        print(f"   Entities: {len(result['entities'])}")
        print(f"   Timepoints: {len(result['timepoints'])}")
        print(f"   Graph edges: {result['graph'].number_of_edges()}")

    @pytest.mark.real_llm
    def test_different_temporal_modes(self, real_llm_client, store):
        """Test different temporal modes"""
        modes = ["pearl", "directorial", "cyclical"]

        for mode in modes:
            # Clear database between tests
            store._clear_database()

            result = simulate_event(
                "simulate a short historical meeting",
                real_llm_client,
                store,
                context={"temporal_mode": mode, "max_entities": 4, "max_timepoints": 3},
                save_to_db=True
            )

            assert result["specification"].temporal_mode == mode
            assert result["temporal_agent"].mode == TemporalMode(mode)

            print(f"\n✓ Tested temporal mode: {mode}")


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_simulate_event_function(self, llm_client, store):
        """Test simulate_event convenience function"""
        result = simulate_event(
            "simulate a small gathering",
            llm_client,
            store,
            save_to_db=False
        )

        assert "specification" in result
        assert "entities" in result
        assert "timepoints" in result


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    # Run with: python test_orchestrator.py
    # Or: pytest test_orchestrator.py -v
    # Or: pytest test_orchestrator.py -v --real-llm -s (for real LLM tests)
    pytest.main([__file__, "-v"])
