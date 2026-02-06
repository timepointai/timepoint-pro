#!/usr/bin/env python3
"""
test_modal_temporal_causality.py - Tests for Mechanism 17: Modal Temporal Causality
"""
import pytest
import numpy as np
from typing import Dict, Any, Optional

from schemas import TemporalMode, Timeline, Timepoint
from workflows import TemporalAgent
from validation import Validator


class ModalTemporalCausalitySystem:
    """System for managing modal temporal causality across different temporal modes"""

    def __init__(self, store=None, llm_client=None):
        self.store = store
        self.llm_client = llm_client
        self.current_mode = TemporalMode.PEARL
        self.agents = {}

    def set_mode(self, mode: TemporalMode, config: Optional[Dict] = None):
        """Set the active temporal mode"""
        self.current_mode = mode
        if mode not in self.agents:
            self.agents[mode] = TemporalAgent(mode, config or {})

    def influence_event(self, event: str, context: Dict) -> float:
        """Get event probability influenced by current temporal mode"""
        if self.current_mode in self.agents:
            return self.agents[self.current_mode].influence_event_probability(event, context)
        return context.get("base_probability", 0.5)

    def validate_causality(self, entity, knowledge_item: str, timepoint: Timepoint) -> Dict[str, Any]:
        """Validate temporal consistency based on current mode"""
        return Validator._validators["temporal_consistency"]["func"](
            entity, knowledge_item, timepoint, self.current_mode.value
        )

    def create_modal_branch(self, base_timepoint: Timepoint, mode: TemporalMode) -> Timepoint:
        """
        Create a modal branch from a base timepoint.

        Args:
            base_timepoint: The timepoint to branch from
            mode: The temporal mode for this branch

        Returns:
            New timepoint representing the modal branch
        """
        from schemas import Timepoint, ResolutionLevel
        from datetime import datetime

        branch_id = f"{base_timepoint.timepoint_id}_modal_{mode.value}"

        branch = Timepoint(
            timepoint_id=branch_id,
            timestamp=base_timepoint.timestamp,
            event_description=f"Modal branch ({mode.value}): {base_timepoint.event_description}",
            entities_present=base_timepoint.entities_present.copy(),
            resolution_level=base_timepoint.resolution_level
        )

        if self.store:
            self.store.save_timepoint(branch)

        return branch


@pytest.mark.integration
@pytest.mark.system
@pytest.mark.temporal
class TestTemporalModeEnum:
    """Test TemporalMode enum functionality"""

    def test_temporal_mode_values(self):
        """Test all temporal mode enum values"""
        assert TemporalMode.PEARL == "pearl"
        assert TemporalMode.DIRECTORIAL == "directorial"
        assert TemporalMode.BRANCHING == "branching"
        assert TemporalMode.CYCLICAL == "cyclical"
        assert TemporalMode.PORTAL == "portal"

    def test_temporal_mode_string_conversion(self):
        """Test string conversion of temporal modes"""
        assert str(TemporalMode.PEARL) == "TemporalMode.PEARL"
        assert TemporalMode.PEARL.value == "pearl"


@pytest.mark.integration
@pytest.mark.system
@pytest.mark.temporal
class TestTemporalAgent:
    """Test TemporalAgent class functionality"""

    def test_temporal_agent_initialization(self):
        """Test TemporalAgent initialization"""
        config = {"goals": ["maintain_causality"], "directorial_config": {"narrative_arc": "rising_action"}}
        agent = TemporalAgent(TemporalMode.DIRECTORIAL, config)

        assert agent.mode == TemporalMode.DIRECTORIAL
        assert "maintain_causality" in agent.goals
        assert len(agent.personality) == 5  # 5D personality vector

    def test_influence_event_probability_pearl_mode(self):
        """Test event probability influence in Pearl mode"""
        agent = TemporalAgent(TemporalMode.PEARL, {})
        context = {"base_probability": 0.5}

        prob = agent.influence_event_probability("any_event", context)
        assert prob == 0.5  # No modification in Pearl mode

    def test_influence_event_probability_directorial_mode(self):
        """Test event probability influence in Directorial mode"""
        config = {
            "directorial_config": {
                "narrative_arc": "rising_action",
                "coincidence_boost_factor": 1.5,
                "dramatic_tension": 0.8,
                "foreshadowing_probability": 0.0  # Disable for deterministic test
            }
        }
        agent = TemporalAgent(TemporalMode.DIRECTORIAL, config)

        # Event that advances rising action
        context = {"base_probability": 0.5, "directorial_config": config["directorial_config"]}
        prob = agent.influence_event_probability("conflict arises between characters", context)
        assert prob > 0.5  # Should be boosted

        # Event that doesn't advance rising action
        prob = agent.influence_event_probability("peaceful resolution occurs", context)
        assert prob == 0.5  # No boost

    def test_influence_event_probability_cyclical_mode(self):
        """Test event probability influence in Cyclical mode"""
        config = {
            "cyclical_config": {
                "cycle_length": 10,
                "destiny_weight": 0.6
            }
        }
        agent = TemporalAgent(TemporalMode.CYCLICAL, config)

        context = {"base_probability": 0.5, "cyclical_config": config["cyclical_config"]}

        # Prophecy fulfillment event
        prob = agent.influence_event_probability("the prophecy comes true as foretold", context)
        assert prob >= 1.0  # Major boost for loop closure (capped at 1.0)

        # Regular event
        prob = agent.influence_event_probability("normal daily occurrence", context)
        assert 0.5 <= prob <= 0.5 * (1 + 0.6 * 1.5)  # Modified by destiny weight

    def test_influence_event_probability_branching_mode(self):
        """Test event probability influence in Branching mode"""
        agent = TemporalAgent(TemporalMode.BRANCHING, {})

        context = {"base_probability": 0.5}

        prob = agent.influence_event_probability("alternate_timeline_event", context)
        assert 0.4 <= prob <= 0.6  # Slight randomization around base

    def test_advances_narrative_arc(self):
        """Test narrative arc advancement detection"""
        agent = TemporalAgent(TemporalMode.DIRECTORIAL, {})

        # Rising action keywords
        assert agent._advances_narrative_arc("conflict arises", "rising_action") == True
        assert agent._advances_narrative_arc("tension builds", "rising_action") == True
        assert agent._advances_narrative_arc("challenge appears", "rising_action") == True

        # Non-rising action
        assert agent._advances_narrative_arc("peaceful resolution", "rising_action") == False
        assert agent._advances_narrative_arc("happy ending", "rising_action") == False

    def test_closes_causal_loop(self):
        """Test causal loop closure detection"""
        agent = TemporalAgent(TemporalMode.CYCLICAL, {})

        # Prophecy fulfillment patterns
        assert agent._closes_causal_loop("prophecy fulfilled", {}) == True
        assert agent._closes_causal_loop("prediction comes true", {}) == True
        assert agent._closes_causal_loop("destiny manifested", {}) == True

        # Non-prophecy events
        assert agent._closes_causal_loop("normal event", {}) == False
        assert agent._closes_causal_loop("regular occurrence", {}) == False


@pytest.mark.integration
@pytest.mark.system
@pytest.mark.temporal
class TestTemporalModeValidation:
    """Test temporal consistency validation by mode"""

    def test_validate_temporal_consistency_pearl_mode(self):
        """Test temporal consistency in Pearl mode"""
        from schemas import Entity, Timepoint

        entity = Entity(entity_id="test_entity", entity_type="human")
        timepoint = Timepoint(
            timepoint_id="tp_test",
            timestamp="2025-01-01T00:00:00",
            event_description="test event",
            entities_present=["test_entity"]
        )

        result = Validator._validators["temporal_consistency"]["func"](
            entity, "normal knowledge", timepoint, "pearl"
        )
        assert result["valid"] == True
        assert "Pearl mode: Forward causality" in result["message"]

    def test_validate_temporal_consistency_cyclical_mode(self):
        """Test temporal consistency in Cyclical mode"""
        from schemas import Entity, Timepoint

        entity = Entity(entity_id="test_entity", entity_type="human")
        timepoint = Timepoint(
            timepoint_id="tp_test",
            timestamp="2025-01-01T00:00:00",
            event_description="test event",
            entities_present=["test_entity"]
        )

        # Prophecy knowledge
        result = Validator._validators["temporal_consistency"]["func"](
            entity, "ancient prophecy fulfilled", timepoint, "cyclical"
        )
        assert result["valid"] == True
        assert "Prophecy allowed" in result["message"]

        # Normal knowledge
        result = Validator._validators["temporal_consistency"]["func"](
            entity, "regular historical fact", timepoint, "cyclical"
        )
        assert result["valid"] == True
        assert "Standard causality" in result["message"]

    def test_validate_temporal_consistency_directorial_mode(self):
        """Test temporal consistency in Directorial mode"""
        from schemas import Entity, Timepoint

        entity = Entity(entity_id="test_entity", entity_type="human")
        timepoint = Timepoint(
            timepoint_id="tp_test",
            timestamp="2025-01-01T00:00:00",
            event_description="test event",
            entities_present=["test_entity"]
        )

        # Dramatic event
        result = Validator._validators["temporal_consistency"]["func"](
            entity, "dramatic turning point", timepoint, "directorial"
        )
        assert result["valid"] == True
        assert "Narrative causality" in result["message"]

        # Regular event
        result = Validator._validators["temporal_consistency"]["func"](
            entity, "ordinary occurrence", timepoint, "directorial"
        )
        assert result["valid"] == True
        assert "Standard causality" in result["message"]

    def test_validate_temporal_consistency_branching_mode(self):
        """Test temporal consistency in Branching mode"""
        from schemas import Entity, Timepoint

        entity = Entity(entity_id="test_entity", entity_type="human")
        timepoint = Timepoint(
            timepoint_id="tp_test",
            timestamp="2025-01-01T00:00:00",
            event_description="test event",
            entities_present=["test_entity"]
        )

        result = Validator._validators["temporal_consistency"]["func"](
            entity, "alternate timeline event", timepoint, "branching"
        )
        assert result["valid"] == True
        assert "Multiverse causality" in result["message"]


@pytest.mark.integration
@pytest.mark.system
@pytest.mark.temporal
class TestTimelineModalSupport:
    """Test Timeline schema support for temporal modes"""

    def test_timeline_with_temporal_mode(self):
        """Test Timeline creation with temporal mode"""
        from datetime import datetime

        timeline = Timeline(
            timeline_id="test_timeline",
            timepoint_id="tp_test",
            timestamp=datetime.now(),
            resolution="day",
            entities_present=["entity1"],
            events=["event1"],
            temporal_mode=TemporalMode.DIRECTORIAL
        )

        assert timeline.temporal_mode == TemporalMode.DIRECTORIAL
        assert timeline.temporal_mode.value == "directorial"

    def test_timeline_default_temporal_mode(self):
        """Test Timeline default temporal mode"""
        from datetime import datetime

        timeline = Timeline(
            timeline_id="test_timeline",
            timepoint_id="tp_test",
            timestamp=datetime.now(),
            resolution="day",
            entities_present=["entity1"],
            events=["event1"]
            # temporal_mode not specified, should default to PEARL
        )

        assert timeline.temporal_mode == TemporalMode.PEARL


@pytest.mark.integration
@pytest.mark.system
@pytest.mark.temporal
class TestIntegrationScenarios:
    """Test integrated scenarios with temporal agents and modes"""

    def test_narrative_driven_causality(self):
        """Test how narrative arcs influence event probabilities"""
        config = {
            "directorial_config": {
                "narrative_arc": "climax",
                "coincidence_boost_factor": 2.0,
                "dramatic_tension": 0.9
            }
        }
        agent = TemporalAgent(TemporalMode.DIRECTORIAL, config)

        context = {"base_probability": 0.3, "directorial_config": config["directorial_config"]}

        # Events that advance climax
        climax_events = [
            "crisis reaches peak",
            "turning point decision",
            "peak crisis moment"
        ]

        for event in climax_events:
            prob = agent.influence_event_probability(event, context)
            assert prob >= 0.3 * 2.0  # At least doubled

    def test_prophecy_cycle_causality(self):
        """Test prophecy-driven causality in cyclical mode"""
        config = {
            "cyclical_config": {
                "destiny_weight": 0.8,
                "cycle_length": 7
            }
        }
        agent = TemporalAgent(TemporalMode.CYCLICAL, config)

        context = {"base_probability": 0.4, "cyclical_config": config["cyclical_config"]}

        # Prophecy-related events get massive boost
        prob = agent.influence_event_probability("prophecy fulfilled as written", context)
        assert prob >= 1.0  # Major boost for loop closure (capped at 1.0)

        # Destiny-weighted events get moderate boost
        prob = agent.influence_event_probability("fated encounter occurs", context)
        expected_min = 0.4 * (1 + 0.8 * 0.5)  # destiny_weight * random(0.5, 1.5) min
        assert prob >= expected_min


if __name__ == "__main__":
    pytest.main([__file__])
