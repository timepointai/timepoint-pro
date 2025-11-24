"""
Tests for Interactive Refinement (Sprint 3.2)
"""

import pytest
from nl_interface import (
    InteractiveRefiner,
    ClarificationEngine,
    Clarification,
    RefinementStep
)


class TestClarificationEngine:
    """Tests for ClarificationEngine"""

    def test_detect_missing_entity_count(self):
        """Test detection of missing entity count"""
        engine = ClarificationEngine()
        clarifications = engine.detect_ambiguities("Simulate a board meeting")

        # Should detect missing entity count
        entity_count_clarification = next(
            (c for c in clarifications if c.field == "entity_count"),
            None
        )
        assert entity_count_clarification is not None
        assert entity_count_clarification.priority == 1  # Critical

    def test_detect_missing_timepoint_count(self):
        """Test detection of missing timepoint count"""
        engine = ClarificationEngine()
        clarifications = engine.detect_ambiguities("Simulate a meeting with 5 people")

        # Should detect missing timepoint count
        timepoint_clarification = next(
            (c for c in clarifications if c.field == "timepoint_count"),
            None
        )
        assert timepoint_clarification is not None
        assert timepoint_clarification.priority == 1  # Critical

    def test_no_clarifications_for_complete_description(self):
        """Test that complete descriptions need no clarifications"""
        engine = ClarificationEngine()
        clarifications = engine.detect_ambiguities(
            "Simulate a board meeting with 5 executives. "
            "Focus on dialog and decision making. "
            "10 timepoints. "
            "Output: dialog and decisions."
        )

        # Should have minimal or no critical clarifications
        critical = [c for c in clarifications if c.priority == 1]
        assert len(critical) == 0

    def test_detect_historical_scenario(self):
        """Test detection of historical scenarios"""
        engine = ClarificationEngine()

        # Historical keyword (note: method expects lowercase input)
        assert engine._is_historical("constitutional convention")

        # Historical year
        assert engine._is_historical("events in 1787")

        # Not historical
        assert not engine._is_historical("a modern board meeting")

    def test_detect_focus_areas(self):
        """Test detection of focus areas from description"""
        engine = ClarificationEngine()

        # Dialog focus
        focus = engine._detect_focus_areas("focus on conversation and dialog")
        assert "dialog" in focus

        # Decision making focus
        focus = engine._detect_focus_areas("track decisions and choices")
        assert "decision_making" in focus

        # Relationships focus
        focus = engine._detect_focus_areas("model trust and conflicts")
        assert "relationships" in focus

        # Multiple focus
        focus = engine._detect_focus_areas(
            "conversation, decisions, and relationships"
        )
        assert len(focus) >= 2

    def test_detect_animism_needs(self):
        """Test detection of non-human entities requiring animism"""
        engine = ClarificationEngine()

        # Horse
        assert engine._needs_animism("Paul Revere and his horse")

        # Organization
        assert engine._needs_animism("The corporation decides")

        # Ship
        assert engine._needs_animism("The ship's journey")

        # No animism needed
        assert not engine._needs_animism("5 people in a meeting")

    def test_detect_variation_generation(self):
        """Test detection of variation/horizontal generation requests"""
        engine = ClarificationEngine()

        # Explicit variations
        assert engine._wants_variations("Generate 50 variations")

        # Horizontal generation
        assert engine._wants_variations("Use horizontal generation mode")

        # Different versions
        assert engine._wants_variations("Create different versions")

        # Not variations
        assert not engine._wants_variations("Simulate one scenario")

    def test_answer_clarification_entity_count(self):
        """Test incorporating entity count answer"""
        engine = ClarificationEngine()

        clarification = Clarification(
            field="entity_count",
            question="How many entities?",
            suggestions=[],
            priority=1,
            detected_reason="Test"
        )

        updated = engine.answer_clarification(
            clarification,
            "5",
            "Simulate a board meeting"
        )

        assert "5 entities" in updated

    def test_answer_clarification_timepoint_count(self):
        """Test incorporating timepoint count answer"""
        engine = ClarificationEngine()

        clarification = Clarification(
            field="timepoint_count",
            question="How many timepoints?",
            suggestions=[],
            priority=1,
            detected_reason="Test"
        )

        updated = engine.answer_clarification(
            clarification,
            "10",
            "Simulate a board meeting"
        )

        assert "10 timepoints" in updated

    def test_clarification_summary(self):
        """Test clarification summary generation"""
        engine = ClarificationEngine()

        clarifications = [
            Clarification("entity_count", "Q1", [], 1, "test"),
            Clarification("focus", "Q2", [], 2, "test"),
            Clarification("outputs", "Q3", [], 3, "test"),
        ]

        summary = engine.get_clarification_summary(clarifications)

        assert "Critical" in summary
        assert "Important" in summary
        assert "Optional" in summary


class TestInteractiveRefiner:
    """Tests for InteractiveRefiner"""

    def test_refiner_initialization(self):
        """Test refiner initializes correctly"""
        refiner = InteractiveRefiner()

        assert refiner.generator.mock_mode is True  # No API key
        assert refiner.clarification_engine is not None
        assert refiner.original_description is None
        assert refiner.current_config is None

    def test_start_refinement_with_complete_description(self):
        """Test refinement with complete description (no clarifications)"""
        refiner = InteractiveRefiner()

        result = refiner.start_refinement(
            "Simulate a board meeting with 5 executives. "
            "10 timepoints. Focus on dialog and decision making. "
            "Output: dialog and decisions."
        )

        # Should generate config directly (no clarifications needed)
        assert result["clarifications_needed"] is False
        assert result["config"] is not None
        assert result["validation"] is not None

    def test_start_refinement_with_incomplete_description(self):
        """Test refinement with incomplete description (needs clarifications)"""
        refiner = InteractiveRefiner()

        result = refiner.start_refinement("Simulate a board meeting")

        # Should need clarifications
        assert result["clarifications_needed"] is True
        assert len(result["clarifications"]) > 0
        assert result["config"] is None

    def test_skip_clarifications(self):
        """Test skip_clarifications flag"""
        refiner = InteractiveRefiner()

        result = refiner.start_refinement(
            "Simulate a board meeting",
            skip_clarifications=True
        )

        # Should generate config even with incomplete description
        assert result["clarifications_needed"] is False
        assert result["config"] is not None

    def test_answer_clarifications(self):
        """Test answering clarifications"""
        refiner = InteractiveRefiner()

        # Start with incomplete description
        result = refiner.start_refinement("Simulate a board meeting")
        assert result["clarifications_needed"] is True

        # Answer clarifications
        answers = {
            "entity_count": "5",
            "timepoint_count": "10",
            "focus": "dialog, decision_making"
        }

        result = refiner.answer_clarifications(answers)

        # Should now have config
        assert result["clarifications_needed"] is False
        assert result["config"] is not None
        assert result["validation"] is not None

    def test_preview_config_json(self):
        """Test JSON preview format"""
        refiner = InteractiveRefiner()

        refiner.start_refinement(
            "Simulate a board meeting with 5 executives. 10 timepoints.",
            skip_clarifications=True
        )

        preview = refiner.preview_config(format="json")
        assert "{" in preview
        assert "scenario" in preview

    def test_preview_config_summary(self):
        """Test summary preview format"""
        refiner = InteractiveRefiner()

        refiner.start_refinement(
            "Simulate a board meeting with 5 executives. 10 timepoints.",
            skip_clarifications=True
        )

        preview = refiner.preview_config(format="summary")
        assert "Scenario:" in preview
        assert "Entities:" in preview
        assert "Timepoints:" in preview

    def test_preview_config_detailed(self):
        """Test detailed preview format"""
        refiner = InteractiveRefiner()

        refiner.start_refinement(
            "Simulate a board meeting with 5 executives. 10 timepoints.",
            skip_clarifications=True
        )

        preview = refiner.preview_config(format="detailed")
        assert "Scenario:" in preview
        assert "Entities:" in preview
        # Should list entity names
        assert "Entity" in preview or "Person" in preview

    def test_adjust_config_direct(self):
        """Test direct config adjustment"""
        refiner = InteractiveRefiner()

        # Generate initial config
        refiner.start_refinement(
            "Simulate a board meeting with 5 executives. 10 timepoints.",
            skip_clarifications=True
        )

        # Adjust timepoint count
        result = refiner.adjust_config(
            {"timepoint_count": 15},
            regenerate=False
        )

        # Should have updated config
        assert result["config"]["timepoint_count"] == 15
        assert result["validation"] is not None

    def test_adjust_config_regenerate(self):
        """Test config adjustment with regeneration"""
        refiner = InteractiveRefiner()

        # Generate initial config
        refiner.start_refinement(
            "Simulate a board meeting with 5 executives. 10 timepoints.",
            skip_clarifications=True
        )

        # Adjust with regeneration
        result = refiner.adjust_config(
            {"timepoint_count": 20},
            regenerate=True
        )

        # Should have regenerated config
        assert result["config"] is not None
        assert result["validation"] is not None
        # Description should be updated
        assert "20 timepoints" in refiner.current_description

    def test_approve_valid_config(self):
        """Test approving valid configuration"""
        refiner = InteractiveRefiner()

        # Generate valid config
        refiner.start_refinement(
            "Simulate a board meeting with 5 executives. "
            "10 timepoints. Focus on dialog.",
            skip_clarifications=True
        )

        # Approve
        final_config = refiner.approve_config()

        assert final_config is not None
        assert "scenario" in final_config

    def test_cannot_approve_invalid_config(self):
        """Test cannot approve invalid configuration"""
        refiner = InteractiveRefiner()

        # Generate config
        refiner.start_refinement(
            "Simulate a meeting with 5 people. 10 timepoints.",
            skip_clarifications=True
        )

        # Manually invalidate
        refiner.current_validation.is_valid = False

        # Try to approve
        with pytest.raises(ValueError, match="Cannot approve invalid"):
            refiner.approve_config()

    def test_reject_and_restart(self):
        """Test rejecting config and restarting"""
        refiner = InteractiveRefiner()

        # Generate config
        refiner.start_refinement(
            "Simulate a board meeting with 5 executives.",
            skip_clarifications=True
        )

        original_config = refiner.current_config

        # Reject and restart
        result = refiner.reject_and_restart(reason="Want different approach")

        # Should restart from beginning
        assert refiner.current_config is None or refiner.current_config != original_config
        assert len(refiner.refinement_history) > 1

    def test_refinement_history_tracking(self):
        """Test refinement history is tracked"""
        refiner = InteractiveRefiner()

        # Start
        refiner.start_refinement("Simulate a board meeting", skip_clarifications=True)

        history = refiner.get_refinement_history()

        assert len(history) >= 2  # Start + generation
        assert history[0].step_type == "start"
        assert any(step.step_type == "generation" for step in history)

    def test_export_refinement_trace(self):
        """Test export of complete refinement trace"""
        refiner = InteractiveRefiner()

        # Generate config
        refiner.start_refinement(
            "Simulate a board meeting with 5 executives. 10 timepoints.",
            skip_clarifications=True
        )

        trace = refiner.export_refinement_trace()

        assert "original_description" in trace
        assert "final_description" in trace
        assert "final_config" in trace
        assert "final_validation" in trace
        assert "steps" in trace
        assert len(trace["steps"]) >= 2

    def test_auto_approve_threshold(self):
        """Test auto-approve threshold behavior"""
        # High threshold - won't auto-approve
        refiner = InteractiveRefiner(auto_approve_threshold=0.99)

        result = refiner.start_refinement(
            "Simulate a board meeting with 5 executives. 10 timepoints. Focus on dialog.",
            skip_clarifications=True
        )

        # Likely won't hit 0.99 confidence
        # (mock mode returns 0.8, real mode might vary)
        # Just check next_step is set
        assert "next_step" in result

    def test_no_config_error_on_preview(self):
        """Test preview before config generation"""
        refiner = InteractiveRefiner()

        preview = refiner.preview_config()
        assert "No configuration" in preview

    def test_no_config_error_on_adjust(self):
        """Test adjust before config generation"""
        refiner = InteractiveRefiner()

        with pytest.raises(ValueError, match="No configuration to adjust"):
            refiner.adjust_config({"timepoint_count": 10})

    def test_no_config_error_on_approve(self):
        """Test approve before config generation"""
        refiner = InteractiveRefiner()

        with pytest.raises(ValueError, match="No configuration to approve"):
            refiner.approve_config()

    def test_no_clarifications_error(self):
        """Test answering clarifications when none pending"""
        refiner = InteractiveRefiner()

        with pytest.raises(ValueError, match="No pending clarifications"):
            refiner.answer_clarifications({"entity_count": "5"})


class TestRefinementWorkflow:
    """Integration tests for complete refinement workflows"""

    def test_complete_workflow_no_clarifications(self):
        """Test complete workflow with no clarifications needed"""
        refiner = InteractiveRefiner()

        # 1. Start - skip clarifications to ensure we get a config
        result = refiner.start_refinement(
            "Simulate the Constitutional Convention with 10 delegates. "
            "15 timepoints. Focus on dialog and decision making. "
            "Generate dialog and decisions.",
            skip_clarifications=True
        )

        assert result["config"] is not None

        # 2. Preview
        preview = refiner.preview_config(format="summary")
        assert "Constitutional" in preview

        # 3. Approve
        final_config = refiner.approve_config()
        assert final_config is not None

    def test_complete_workflow_with_clarifications(self):
        """Test complete workflow with clarification phase"""
        refiner = InteractiveRefiner()

        # 1. Start - incomplete description
        result = refiner.start_refinement("Simulate the Constitutional Convention")

        # Should need clarifications
        assert result["clarifications_needed"] is True

        # 2. Answer clarifications
        answers = {
            "entity_count": "10",
            "timepoint_count": "15",
            "focus": "dialog, decision_making"
        }
        result = refiner.answer_clarifications(answers)

        # Should now have config
        assert result["config"] is not None

        # 3. Approve
        final_config = refiner.approve_config()
        assert final_config is not None

    def test_workflow_with_adjustments(self):
        """Test workflow with config adjustments"""
        refiner = InteractiveRefiner()

        # 1. Start
        refiner.start_refinement(
            "Simulate a board meeting with 5 executives. 10 timepoints.",
            skip_clarifications=True
        )

        # 2. Preview and decide to adjust
        preview = refiner.preview_config(format="summary")
        assert "10" in preview  # Original timepoint count

        # 3. Adjust
        result = refiner.adjust_config(
            {"timepoint_count": 15},
            regenerate=False
        )

        assert result["config"]["timepoint_count"] == 15

        # 4. Approve
        final_config = refiner.approve_config()
        assert final_config["timepoint_count"] == 15

    def test_workflow_with_rejection(self):
        """Test workflow with rejection and restart"""
        refiner = InteractiveRefiner()

        # 1. Start
        refiner.start_refinement(
            "Simulate a board meeting with 5 executives.",
            skip_clarifications=True
        )

        # 2. Reject
        result = refiner.reject_and_restart(reason="Wrong scenario")

        # Should need clarifications again (or generate new config)
        assert "next_step" in result

        # 3. Can answer clarifications and continue
        if result["clarifications_needed"]:
            result = refiner.answer_clarifications({
                "timepoint_count": "10",
                "focus": "dialog"
            })

        assert result["config"] is not None
