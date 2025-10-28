#!/usr/bin/env python3
"""
test_phase3_dialog_multi_entity.py - Comprehensive tests for Phase 3: Dialog Synthesis & Multi-Entity Analysis

Tests Mechanism 11 (Dialog Synthesis) and Mechanism 13 (Multi-Entity Synthesis)
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from schemas import (
    Entity, Timepoint, Dialog, DialogTurn, DialogData,
    RelationshipTrajectory, RelationshipState, RelationshipMetrics,
    Contradiction, ComparativeAnalysis
)
from storage import GraphStore
from llm_v2 import LLMClient  # Use new centralized service
from workflows import (
    synthesize_dialog, analyze_relationship_evolution,
    detect_contradictions, synthesize_multi_entity_response,
    couple_pain_to_cognition, couple_illness_to_cognition
)
from query_interface import QueryInterface, QueryIntent
from validation import Validator


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
@pytest.mark.system
class TestPhase3DialogSynthesis:
    """Test Mechanism 11: Dialog Synthesis with body-mind coupling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.store = Mock(spec=GraphStore)
        self.llm = Mock(spec=LLMClient)
        self.llm.dry_run = False

        # Create test entities with physical and cognitive states
        self.washington = Entity(
            entity_id="washington",
            entity_type="person",
            entity_metadata={
                "physical_tensor": {
                    "age": 57,
                    "health_status": 0.9,
                    "pain_level": 0.2,  # Some dental pain
                    "pain_location": "teeth",
                    "stamina": 0.8
                },
                "cognitive_tensor": {
                    "knowledge_state": ["Washington was elected president", "Constitutional Convention delegate"],
                    "emotional_valence": 0.1,  # Slightly positive
                    "emotional_arousal": 0.3,
                    "energy_budget": 80.0,
                    "decision_confidence": 0.9,
                    "patience_threshold": 40.0
                },
                "personality_traits": ["steadfast", "principled", "reserved"],
                "current_goals": ["establish stable government", "set presidential precedents"]
            }
        )

        self.jefferson = Entity(
            entity_id="jefferson",
            entity_type="person",
            entity_metadata={
                "physical_tensor": {
                    "age": 46,
                    "health_status": 0.85,
                    "pain_level": 0.0,
                    "stamina": 0.9
                },
                "cognitive_tensor": {
                    "knowledge_state": ["Declaration of Independence author", "Secretary of State"],
                    "emotional_valence": 0.2,
                    "emotional_arousal": 0.4,
                    "energy_budget": 85.0,
                    "decision_confidence": 0.8,
                    "patience_threshold": 50.0
                },
                "personality_traits": ["intellectual", "idealistic", "diplomatic"],
                "current_goals": ["promote republican ideals", "expand national territory"]
            }
        )

        # Create test timepoint
        self.timepoint = Timepoint(
            timepoint_id="t1_inauguration",
            timestamp=datetime(1789, 4, 30, 12, 0),
            event_description="George Washington's presidential inauguration ceremony at Federal Hall"
        )

        self.timeline = [{"event": "Inauguration", "timestamp": self.timepoint.timestamp}]

    def test_body_mind_coupling_pain_effects(self):
        """Test that pain affects cognitive state"""
        # Start with healthy cognitive state
        physical = self.washington.physical_tensor
        cognitive = self.washington.cognitive_tensor

        # Apply pain coupling
        coupled = couple_pain_to_cognition(physical, cognitive)

        # Pain should reduce energy budget and patience
        assert coupled.energy_budget < cognitive.energy_budget
        assert coupled.patience_threshold < cognitive.patience_threshold
        assert coupled.emotional_valence < cognitive.emotional_valence  # More negative

    def test_body_mind_coupling_illness_effects(self):
        """Test that illness affects cognitive state"""
        # Create entity with fever
        sick_entity = Entity(
            entity_id="sick_person",
            entity_metadata={
                "physical_tensor": {
                    "fever": 39.0  # High fever
                },
                "cognitive_tensor": {
                    "decision_confidence": 0.9,
                    "risk_tolerance": 0.3,
                    "social_engagement": 0.8
                }
            }
        )

        physical = sick_entity.physical_tensor
        cognitive = sick_entity.cognitive_tensor

        # Apply illness coupling
        coupled = couple_illness_to_cognition(physical, cognitive)

        # Fever should reduce confidence and social engagement, increase risk tolerance
        assert coupled.decision_confidence < cognitive.decision_confidence
        assert coupled.social_engagement < cognitive.social_engagement
        assert coupled.risk_tolerance > cognitive.risk_tolerance

    @patch('workflows.create_exposure_event')
    def test_synthesize_dialog_structure(self, mock_exposure):
        """Test dialog synthesis produces correct structure"""
        entities = [self.washington, self.jefferson]

        # Mock LLM response
        mock_dialog_data = DialogData(
            turns=[
                DialogTurn(
                    speaker="washington",
                    content="I am honored to serve as your first President.",
                    timestamp=self.timepoint.timestamp,
                    emotional_tone="solemn",
                    knowledge_references=["presidential precedents"],
                    confidence=0.95
                ),
                DialogTurn(
                    speaker="jefferson",
                    content="The nation looks to your leadership with hope.",
                    timestamp=self.timepoint.timestamp + timedelta(seconds=30),
                    emotional_tone="optimistic",
                    knowledge_references=["republican ideals"],
                    confidence=0.9
                )
            ],
            total_duration=60,
            information_exchanged=["presidential precedents", "republican ideals"],
            relationship_impacts={"washington_jefferson": 0.1}
        )

        self.llm.generate_dialog.return_value = mock_dialog_data

        # Synthesize dialog
        dialog = synthesize_dialog(entities, self.timepoint, self.timeline, self.llm, self.store)

        # Verify structure
        assert isinstance(dialog, Dialog)
        assert dialog.timepoint_id == self.timepoint.timepoint_id
        assert json.loads(dialog.participants) == ["washington", "jefferson"]
        assert dialog.information_transfer_count == 2

        # Verify exposure events were created
        assert mock_exposure.call_count == 2  # One for each turn

    def test_synthesize_dialog_context_building(self):
        """Test that dialog synthesis builds comprehensive context"""
        entities = [self.washington, self.jefferson]

        # Mock LLM to capture the prompt
        captured_prompt = None

        def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return DialogData(turns=[], total_duration=0)

        self.llm.generate_dialog.side_effect = capture_prompt

        synthesize_dialog(entities, self.timepoint, self.timeline, self.llm, self.store)

        # Verify comprehensive context is included
        assert "PARTICIPANTS:" in captured_prompt
        assert "age" in captured_prompt  # Physical state
        assert "pain" in captured_prompt  # Pain effects
        assert "emotional_state" in captured_prompt  # Cognitive state
        assert "relationships" in captured_prompt  # Relationship context
        assert "CRITICAL INSTRUCTIONS:" in captured_prompt


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
@pytest.mark.system
class TestPhase3MultiEntityAnalysis:
    """Test Mechanism 13: Multi-Entity Synthesis"""

    def setup_method(self):
        """Set up test fixtures"""
        self.store = Mock(spec=GraphStore)
        self.llm = Mock(spec=LLMClient)

        # Create test entities
        self.hamilton = Entity(
            entity_id="hamilton",
            entity_metadata={
                "knowledge_state": ["National Bank is essential", "Federal debt assumption necessary", "Strong central government needed"]
            }
        )

        self.jefferson = Entity(
            entity_id="jefferson",
            entity_metadata={
                "knowledge_state": ["States rights are paramount", "Strict constitutional interpretation", "Agrarian republic ideal"]
            }
        )

        self.timepoint = Timepoint(
            timepoint_id="t2_cabinet_meeting",
            timestamp=datetime(1790, 1, 15),
            event_description="First Cabinet meeting discussing financial policy"
        )

    def test_relationship_trajectory_analysis(self):
        """Test relationship trajectory analysis between entities"""
        # Mock relationship trajectory
        mock_trajectory = Mock()
        mock_trajectory.entity_a = "hamilton"
        mock_trajectory.entity_b = "jefferson"
        mock_trajectory.overall_trend = "deteriorating"
        mock_trajectory.key_events = ["Bank debate", "Assumption dispute"]

        self.store.get_relationship_trajectory_between.return_value = mock_trajectory

        trajectories = analyze_relationship_evolution(
            ["hamilton", "jefferson"],
            self.timeline,
            store=self.store
        )

        assert len(trajectories) == 1
        assert trajectories[0]["overall_trend"] == "deteriorating"
        assert "Bank debate" in trajectories[0]["key_events"]

    def test_contradiction_detection(self):
        """Test detection of contradictions between entities"""
        entities = [self.hamilton, self.jefferson]

        contradictions = detect_contradictions(entities, self.timepoint, self.store)

        # Should detect contradictions on government structure, financial policy, etc.
        assert len(contradictions) > 0

        contradiction = contradictions[0]
        assert contradiction.entity_a in ["hamilton", "jefferson"]
        assert contradiction.entity_b in ["hamilton", "jefferson"]
        assert contradiction.severity > 0.3  # Significant disagreement

    def test_multi_entity_response_synthesis(self):
        """Test synthesis of multi-entity analysis response"""
        entities = ["hamilton", "jefferson"]
        query = "How did Hamilton and Jefferson's relationship evolve?"

        # Mock dependencies
        self.store.get_entity.side_effect = lambda eid: {
            "hamilton": self.hamilton,
            "jefferson": self.jefferson
        }.get(eid)

        self.store.get_relationship_trajectory_between.return_value = None
        self.store.get_dialogs_for_entities.return_value = []
        self.llm.dry_run = True

        response = synthesize_multi_entity_response(
            entities, query, [], self.llm, self.store
        )

        # Should return structured analysis
        assert "Relationship Analysis:" in response
        assert "Hamilton" in response and "Jefferson" in response
        assert "Multi-Entity Analysis:" in response


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
@pytest.mark.system
class TestPhase3Integration:
    """Test integration of Phase 3 features with query interface"""

    def setup_method(self):
        """Set up test fixtures"""
        self.store = Mock(spec=GraphStore)
        self.llm = Mock(spec=LLMClient)
        self.query_interface = QueryInterface(self.store, self.llm)

    def test_multi_entity_query_parsing(self):
        """Test that multi-entity relationship queries are parsed correctly"""
        query = "How did Hamilton and Jefferson interact during the cabinet meetings?"

        # Mock LLM parsing
        def mock_parse(**kwargs):
            return QueryIntent(
                target_entity=None,
                context_entities=["hamilton", "jefferson"],
                information_type="relationships",
                confidence=0.85,
                reasoning="Multi-entity relationship query"
            )

        self.llm.generate_dialog.side_effect = mock_parse

        intent = self.query_interface.parse_query(query)

        assert intent.context_entities == ["hamilton", "jefferson"]
        assert intent.information_type == "relationships"

    def test_relationship_response_integration(self):
        """Test end-to-end multi-entity relationship query"""
        query_intent = QueryIntent(
            context_entities=["hamilton", "jefferson"],
            information_type="relationships",
            confidence=0.9
        )

        # Mock all dependencies
        self.store.get_entity.return_value = Mock()
        self.store.get_relationship_trajectory_between.return_value = None
        self.store.get_dialogs_for_entities.return_value = []
        self.llm.dry_run = True

        response = self.query_interface._synthesize_relationship_response(query_intent)

        assert "Relationship Analysis:" in response
        assert "Hamilton" in response and "Jefferson" in response


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
@pytest.mark.system
class TestPhase3Validators:
    """Test Phase 3 dialog validators"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create test dialog data
        self.dialog_data = {
            "turns": [
                {
                    "speaker": "washington",
                    "content": "I shall strive to be worthy of this high trust.",
                    "emotional_tone": "solemn",
                    "confidence": 0.9
                },
                {
                    "speaker": "jefferson",
                    "content": "The nation needs strong leadership.",
                    "emotional_tone": "supportive",
                    "confidence": 0.85
                }
            ]
        }

        # Create test entities
        self.entities = [
            Entity(
                entity_id="washington",
                entity_metadata={
                    "physical_tensor": {"age": 57, "pain_level": 0.1, "stamina": 0.8},
                    "cognitive_tensor": {"energy_budget": 70.0, "emotional_valence": 0.1}
                }
            ),
            Entity(
                entity_id="jefferson",
                entity_metadata={
                    "physical_tensor": {"age": 46, "pain_level": 0.0, "stamina": 0.9},
                    "cognitive_tensor": {"energy_budget": 90.0, "emotional_valence": 0.2}
                }
            )
        ]

    def test_dialog_realism_validator(self):
        """Test dialog realism validation"""
        # This should pass with healthy entities
        result = Validator.validate_all(self.entities[0], {"dialog_data": self.dialog_data})
        # Note: This would need proper integration with the validator system

    def test_knowledge_consistency_validator(self):
        """Test knowledge consistency in dialog"""
        # Add knowledge references to dialog
        self.dialog_data["turns"][0]["knowledge_references"] = ["presidential precedents"]

        # This would validate that speakers only reference knowledge they have
        # Implementation depends on entity knowledge state


if __name__ == "__main__":
    # Run basic functionality test
    print("🧪 Testing Phase 3: Dialog Synthesis & Multi-Entity Analysis")

    # Test body-mind coupling
    from schemas import PhysicalTensor, CognitiveTensor

    physical = PhysicalTensor(age=57, pain_level=0.3, stamina=0.8)
    cognitive = CognitiveTensor(
        knowledge_state=["test knowledge"],
        emotional_valence=0.0,
        energy_budget=100.0,
        decision_confidence=0.9,
        patience_threshold=50.0
    )

    coupled = couple_pain_to_cognition(physical, cognitive)
    assert coupled.energy_budget < cognitive.energy_budget, "Pain should reduce energy"
    assert coupled.emotional_valence < cognitive.emotional_valence, "Pain should reduce emotional valence"

    print("✅ Body-mind coupling works correctly")

    # Test illness coupling
    physical_sick = PhysicalTensor(fever=39.5)
    coupled_sick = couple_illness_to_cognition(physical_sick, cognitive)
    assert coupled_sick.decision_confidence < cognitive.decision_confidence, "Fever should reduce confidence"

    print("✅ Illness coupling works correctly")
    print("🎯 Phase 3 implementation ready for testing!")
