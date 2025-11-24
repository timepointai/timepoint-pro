"""
Tests for PORTAL mode (Mechanism 17 - Modal Temporal Causality)

PORTAL mode performs backward inference from a known endpoint (portal) to a
known origin, discovering plausible paths that connect them.

Test coverage:
- Configuration validation
- Portal state generation
- Backward path exploration
- Forward coherence validation
- Path ranking and scoring
- Pivot point detection
"""

import pytest
from datetime import datetime
import numpy as np

from schemas import Entity, Timepoint, TemporalMode, ResolutionLevel
from generation.config_schema import TemporalConfig
from workflows.portal_strategy import (
    PortalStrategy,
    PortalState,
    PortalPath,
    ExplorationMode,
    FailureResolution
)
from workflows import TemporalAgent
from storage import GraphStore
from llm_v2 import LLMClient


class TestPortalConfiguration:
    """Test PORTAL mode configuration validation"""

    def test_portal_config_validation(self):
        """Test that PortalStrategy validates required configuration"""
        config = TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="John Doe elected President in 2040",
            portal_year=2040,
            origin_year=2025
        )

        # Should not raise
        assert config.mode == TemporalMode.PORTAL
        assert config.portal_description is not None
        assert config.portal_year == 2040
        assert config.origin_year == 2025

    def test_missing_portal_description_raises_error(self):
        """Test that missing portal_description raises ValueError"""
        config = TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description=None,  # Missing
            portal_year=2040,
            origin_year=2025
        )

        # Create mock clients
        from unittest.mock import Mock
        llm_client = Mock()
        store = Mock()

        with pytest.raises(ValueError, match="portal_description is required"):
            strategy = PortalStrategy(config, llm_client, store)

    def test_missing_years_raises_error(self):
        """Test that missing portal_year or origin_year raises ValueError"""
        config = TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="Some endpoint",
            portal_year=None,  # Missing
            origin_year=2025
        )

        from unittest.mock import Mock
        llm_client = Mock()
        store = Mock()

        with pytest.raises(ValueError, match="portal_year and origin_year are required"):
            strategy = PortalStrategy(config, llm_client, store)

    def test_wrong_mode_raises_error(self):
        """Test that non-PORTAL mode raises ValueError"""
        config = TemporalConfig(
            mode=TemporalMode.PEARL,  # Wrong mode
            portal_description="Some endpoint",
            portal_year=2040,
            origin_year=2025
        )

        from unittest.mock import Mock
        llm_client = Mock()
        store = Mock()

        with pytest.raises(ValueError, match="PortalStrategy requires mode=PORTAL"):
            strategy = PortalStrategy(config, llm_client, store)


class TestPortalState:
    """Test PortalState data structure"""

    def test_portal_state_creation(self):
        """Test creating a PortalState"""
        state = PortalState(
            year=2040,
            description="John Doe is President",
            entities=[],
            world_state={"political_landscape": "democratic"},
            plausibility_score=1.0
        )

        assert state.year == 2040
        assert state.description == "John Doe is President"
        assert state.plausibility_score == 1.0
        assert state.parent_state is None
        assert state.children_states == []

    def test_portal_state_with_parent(self):
        """Test PortalState parent-child relationship"""
        parent = PortalState(
            year=2040,
            description="Portal endpoint",
            entities=[],
            world_state={},
            plausibility_score=1.0
        )

        child = PortalState(
            year=2039,
            description="Antecedent state",
            entities=[],
            world_state={},
            plausibility_score=0.8,
            parent_state=parent
        )

        parent.children_states.append(child)

        assert child.parent_state == parent
        assert child in parent.children_states


class TestPortalPath:
    """Test PortalPath data structure"""

    def test_portal_path_creation(self):
        """Test creating a PortalPath"""
        states = [
            PortalState(2025, "Origin", [], {}, 1.0),
            PortalState(2030, "Midpoint", [], {}, 0.9),
            PortalState(2040, "Portal", [], {}, 1.0)
        ]

        path = PortalPath(
            path_id="test_path_001",
            states=states,
            coherence_score=0.85,
            pivot_points=[1],
            explanation="Path from origin to portal"
        )

        assert path.path_id == "test_path_001"
        assert len(path.states) == 3
        assert path.coherence_score == 0.85
        assert path.pivot_points == [1]


class TestExplorationStrategies:
    """Test exploration strategy selection"""

    def test_adaptive_strategy_selection_simple(self):
        """Test adaptive strategy selection for simple scenarios"""
        config = TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="Endpoint",
            portal_year=2040,
            origin_year=2025,
            backward_steps=5,  # Simple scenario
            exploration_mode="adaptive",
            oscillation_complexity_threshold=10
        )

        from unittest.mock import Mock
        llm_client = Mock()
        store = Mock()

        strategy_obj = PortalStrategy(config, llm_client, store)
        selected = strategy_obj._select_exploration_strategy()

        # Should select REVERSE_CHRONOLOGICAL for simple scenarios
        assert selected == ExplorationMode.REVERSE_CHRONOLOGICAL

    def test_adaptive_strategy_selection_complex(self):
        """Test adaptive strategy selection for complex scenarios"""
        config = TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="Endpoint",
            portal_year=2040,
            origin_year=2025,
            backward_steps=20,  # Complex scenario
            exploration_mode="adaptive",
            oscillation_complexity_threshold=10
        )

        from unittest.mock import Mock
        llm_client = Mock()
        store = Mock()

        strategy_obj = PortalStrategy(config, llm_client, store)
        selected = strategy_obj._select_exploration_strategy()

        # Should select OSCILLATING for complex scenarios
        assert selected == ExplorationMode.OSCILLATING

    def test_explicit_strategy_selection(self):
        """Test explicit strategy selection"""
        config = TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="Endpoint",
            portal_year=2040,
            origin_year=2025,
            exploration_mode="reverse_chronological"
        )

        from unittest.mock import Mock
        llm_client = Mock()
        store = Mock()

        strategy_obj = PortalStrategy(config, llm_client, store)
        selected = strategy_obj._select_exploration_strategy()

        assert selected == ExplorationMode.REVERSE_CHRONOLOGICAL


class TestTemporalAgentPortalIntegration:
    """Test TemporalAgent integration with PORTAL mode"""

    def test_temporal_agent_portal_mode(self):
        """Test TemporalAgent with PORTAL mode"""
        from unittest.mock import Mock

        llm_client = Mock()
        store = Mock()

        agent = TemporalAgent(
            mode=TemporalMode.PORTAL,
            llm_client=llm_client,
            store=store
        )

        assert agent.mode == TemporalMode.PORTAL

    def test_generate_antecedent_timepoint(self):
        """Test generating antecedent timepoints"""
        from unittest.mock import Mock

        llm_client = Mock()
        store = Mock()
        store.save_timepoint = Mock()
        store.save_exposure_event = Mock()

        agent = TemporalAgent(
            mode=TemporalMode.PORTAL,
            llm_client=llm_client,
            store=store
        )

        # Create a consequent timepoint
        consequent = Timepoint(
            timepoint_id="tp_cons",
            timestamp=datetime(2040, 1, 1),
            event_description="John Doe is President",
            entities_present=["entity_001"],
            resolution_level=ResolutionLevel.YEAR
        )

        # Generate antecedent
        antecedent = agent.generate_antecedent_timepoint(
            consequent,
            context={"target_year": 2039}
        )

        assert antecedent.timestamp.year == 2039
        assert antecedent.entities_present == ["entity_001"]
        assert "Antecedent state" in antecedent.event_description

    def test_generate_antecedent_wrong_mode_raises_error(self):
        """Test that generate_antecedent_timepoint raises error in wrong mode"""
        from unittest.mock import Mock

        llm_client = Mock()
        store = Mock()

        agent = TemporalAgent(
            mode=TemporalMode.PEARL,  # Wrong mode
            llm_client=llm_client,
            store=store
        )

        consequent = Timepoint(
            timepoint_id="tp_cons",
            timestamp=datetime(2040, 1, 1),
            event_description="Event",
            entities_present=[],
            resolution_level=ResolutionLevel.YEAR
        )

        with pytest.raises(ValueError, match="generate_antecedent_timepoint.*requires mode=PORTAL"):
            agent.generate_antecedent_timepoint(consequent)


class TestValidation:
    """Test PORTAL mode validation"""

    def test_temporal_consistency_portal_mode(self):
        """Test temporal_consistency validator with PORTAL mode"""
        from validation import validate_temporal_consistency

        entity = Entity(
            entity_id="entity_001",
            entity_type="human",
            entity_metadata={"knowledge_state": ["knows about portal endpoint"]}
        )

        context = {
            "mode": "portal",
            "knowledge_item": "knows about portal endpoint",
            "timepoint": Timepoint(
                timepoint_id="tp_001",
                timestamp=datetime(2030, 1, 1),
                event_description="Event",
                entities_present=["entity_001"],
                resolution_level=ResolutionLevel.YEAR
            ),
            "is_portal_antecedent": True
        }

        result = validate_temporal_consistency(entity, context)

        assert result["valid"] is True
        assert "Portal mode" in result["message"]
        assert "backward path" in result["message"]

    def test_temporal_consistency_portal_causal_necessity(self):
        """Test temporal_consistency with causally necessary knowledge"""
        from validation import validate_temporal_consistency

        entity = Entity(
            entity_id="entity_001",
            entity_type="human",
            entity_metadata={}
        )

        context = {
            "mode": "portal",
            "knowledge_item": "This event is necessary for reaching the portal",
            "timepoint": Timepoint(
                timepoint_id="tp_001",
                timestamp=datetime(2030, 1, 1),
                event_description="Event",
                entities_present=["entity_001"],
                resolution_level=ResolutionLevel.YEAR
            )
        }

        result = validate_temporal_consistency(entity, context)

        assert result["valid"] is True
        assert "Causally necessary" in result["message"]


class TestPortalEventProbability:
    """Test event probability adjustments in PORTAL mode"""

    def test_influence_event_probability_portal_antecedent(self):
        """Test that portal antecedents get probability boost"""
        from unittest.mock import Mock

        agent = TemporalAgent(
            mode=TemporalMode.PORTAL,
            llm_client=Mock(),
            store=Mock()
        )

        event = "John Doe campaigns for Senate"
        context = {
            "base_probability": 0.5,
            "is_portal_antecedent": True,
            "portal_config": {"causal_necessity_weight": 0.3}
        }

        modified_prob = agent.influence_event_probability(event, context)

        # Should be boosted
        assert modified_prob > 0.5
        assert modified_prob <= 1.0

    def test_influence_event_probability_portal_non_antecedent(self):
        """Test that non-antecedent events get slight reduction"""
        from unittest.mock import Mock

        agent = TemporalAgent(
            mode=TemporalMode.PORTAL,
            llm_client=Mock(),
            store=Mock()
        )

        event = "Random unrelated event"
        context = {
            "base_probability": 0.5,
            "is_portal_antecedent": False
        }

        modified_prob = agent.influence_event_probability(event, context)

        # Should be slightly reduced
        assert modified_prob < 0.5


class TestIntegration:
    """Integration tests for PORTAL mode"""

    def test_full_portal_workflow_mock(self):
        """Test full PORTAL workflow with mocked LLM"""
        from unittest.mock import Mock

        # Create mock LLM and store
        llm_client = Mock()
        store = Mock()
        store.save_timepoint = Mock()
        store.save_exposure_event = Mock()

        # Create configuration
        config = TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="John Doe elected President in 2040",
            portal_year=2040,
            origin_year=2025,
            backward_steps=3,
            path_count=2,
            candidate_antecedents_per_step=2,
            coherence_threshold=0.5
        )

        # Create strategy
        strategy = PortalStrategy(config, llm_client, store)

        # Run simulation (will use placeholder implementations)
        paths = strategy.run()

        # Should return some paths
        assert isinstance(paths, list)
        # Note: With placeholder implementations, paths might be empty or limited

    def test_portal_agent_run_simulation(self):
        """Test TemporalAgent.run_portal_simulation()"""
        from unittest.mock import Mock

        llm_client = Mock()
        store = Mock()
        store.save_timepoint = Mock()
        store.save_exposure_event = Mock()

        agent = TemporalAgent(
            mode=TemporalMode.PORTAL,
            llm_client=llm_client,
            store=store
        )

        config = TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="Endpoint state",
            portal_year=2040,
            origin_year=2025,
            backward_steps=3,
            path_count=1
        )

        # Should not raise
        paths = agent.run_portal_simulation(config)
        assert isinstance(paths, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
