"""
Tests for Vertical Data Generation (Sprint 1.3)

Tests temporal expansion strategies and vertical generation.
"""

import pytest
import tempfile
import json
from pathlib import Path

from generation.vertical_generator import VerticalGenerator
from generation.temporal_expansion import (
    TemporalExpander,
    NarrativeArcExpansion,
    ProgressiveTrainingExpansion,
    CausalChainExpansion
)
from generation.config_schema import SimulationConfig
from generation.templates.loader import TemplateLoader

_loader = TemplateLoader()


class TestTemporalExpansionStrategies:
    """Tests for temporal expansion strategies"""

    def test_narrative_arc_expansion_before(self):
        """Test narrative arc expansion before critical moment"""
        strategy = NarrativeArcExpansion()
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        expanded = strategy.expand(base_config, "before", 5)

        assert expanded["timepoints"]["before_count"] == 5
        assert expanded["metadata"]["narrative_structure"] == "rising_action"
        assert expanded["metadata"]["temporal_expansion"]["strategy"] == "narrative_arc"

    def test_narrative_arc_expansion_after(self):
        """Test narrative arc expansion after critical moment"""
        strategy = NarrativeArcExpansion()
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        expanded = strategy.expand(base_config, "after", 3)

        assert expanded["timepoints"]["after_count"] == 3
        assert expanded["metadata"]["narrative_structure"] == "falling_action"

    def test_narrative_arc_expansion_around(self):
        """Test narrative arc expansion in both directions"""
        strategy = NarrativeArcExpansion()
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        expanded = strategy.expand(base_config, "around", 10)

        assert expanded["timepoints"]["before_count"] == 5
        assert expanded["timepoints"]["after_count"] == 5
        assert expanded["metadata"]["narrative_structure"] == "complete_arc"

    def test_progressive_training_expansion_before(self):
        """Test progressive training expansion before"""
        strategy = ProgressiveTrainingExpansion(peak_resolution="full_detail")
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        expanded = strategy.expand(base_config, "before", 5)

        assert expanded["timepoints"]["before_count"] == 5
        assert "resolution_schedule_before" in expanded["metadata"]
        assert len(expanded["metadata"]["resolution_schedule_before"]) == 5

        # Should ascend to peak
        schedule = expanded["metadata"]["resolution_schedule_before"]
        assert schedule[-1] in ["dialog", "full_detail"]

    def test_progressive_training_expansion_after(self):
        """Test progressive training expansion after"""
        strategy = ProgressiveTrainingExpansion(peak_resolution="full_detail")
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        expanded = strategy.expand(base_config, "after", 5)

        assert expanded["timepoints"]["after_count"] == 5
        assert "resolution_schedule_after" in expanded["metadata"]

        # Should descend from peak
        schedule = expanded["metadata"]["resolution_schedule_after"]
        assert schedule[0] in ["dialog", "full_detail"]

    def test_progressive_training_expansion_around(self):
        """Test progressive training in both directions"""
        strategy = ProgressiveTrainingExpansion()
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        expanded = strategy.expand(base_config, "around", 10)

        assert "resolution_schedule_before" in expanded["metadata"]
        assert "resolution_schedule_after" in expanded["metadata"]

    def test_causal_chain_expansion_before(self):
        """Test causal chain expansion before"""
        strategy = CausalChainExpansion()
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        expanded = strategy.expand(base_config, "before", 5)

        assert expanded["timepoints"]["before_count"] == 5
        assert expanded["metadata"]["require_causal_validation"] is True
        assert "causal_chain_before" in expanded["metadata"]
        assert len(expanded["metadata"]["causal_chain_before"]) == 5

    def test_causal_chain_expansion_after(self):
        """Test causal chain expansion after"""
        strategy = CausalChainExpansion()
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        expanded = strategy.expand(base_config, "after", 3)

        assert expanded["timepoints"]["after_count"] == 3
        assert "causal_chain_after" in expanded["metadata"]


class TestTemporalExpander:
    """Tests for TemporalExpander"""

    def test_expander_basic(self):
        """Test basic temporal expansion"""
        expander = TemporalExpander()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = expander.expand_temporal_depth(
            base_config,
            strategy="progressive_training",
            before_count=3,
            after_count=2
        )

        assert expanded.timepoints.before_count == 3
        assert expanded.timepoints.after_count == 2

    def test_expander_before_only(self):
        """Test expansion before only"""
        expander = TemporalExpander()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = expander.expand_before(base_config, count=5)

        assert expanded.timepoints.before_count == 5
        assert expanded.timepoints.after_count == 0

    def test_expander_after_only(self):
        """Test expansion after only"""
        expander = TemporalExpander()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = expander.expand_after(base_config, count=4)

        assert expanded.timepoints.before_count == 0
        assert expanded.timepoints.after_count == 4

    def test_expander_around(self):
        """Test expansion in both directions"""
        expander = TemporalExpander()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = expander.expand_around(base_config, before_count=3, after_count=2)

        assert expanded.timepoints.before_count == 3
        assert expanded.timepoints.after_count == 2

    def test_expander_no_expansion(self):
        """Test that no expansion returns unchanged config"""
        expander = TemporalExpander()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = expander.expand_temporal_depth(
            base_config,
            before_count=0,
            after_count=0
        )

        assert expanded.timepoints.before_count == 0
        assert expanded.timepoints.after_count == 0

    def test_expander_invalid_strategy(self):
        """Test expander with invalid strategy"""
        expander = TemporalExpander()
        base_config = _loader.load_template("showcase/board_meeting")

        with pytest.raises(ValueError, match="Unknown strategy"):
            expander.expand_temporal_depth(
                base_config,
                strategy="invalid_strategy",
                before_count=5
            )

    def test_expander_available_strategies(self):
        """Test getting available strategies"""
        expander = TemporalExpander()
        strategies = expander.get_available_strategies()

        assert len(strategies) == 3
        assert "narrative_arc" in strategies
        assert "progressive_training" in strategies
        assert "causal_chain" in strategies


class TestVerticalGenerator:
    """Tests for VerticalGenerator"""

    def test_generator_basic(self):
        """Test basic vertical generation"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/jefferson_dinner")

        expanded = generator.generate_temporal_depth(
            base_config,
            before_count=5,
            after_count=5
        )

        # Original had before_count=2, after_count=2
        # We're setting it to 5, 5
        assert expanded.timepoints.before_count == 5
        assert expanded.timepoints.after_count == 5

    def test_generator_before_only(self):
        """Test generating before timepoints only"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = generator.generate_before(base_config, count=5)

        assert expanded.timepoints.before_count == 5
        assert expanded.timepoints.after_count == 0

    def test_generator_after_only(self):
        """Test generating after timepoints only"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = generator.generate_after(base_config, count=4)

        assert expanded.timepoints.before_count == 0
        assert expanded.timepoints.after_count == 4

    def test_generator_around(self):
        """Test generating in both directions"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = generator.generate_around(base_config, before_count=3, after_count=2)

        assert expanded.timepoints.before_count == 3
        assert expanded.timepoints.after_count == 2

    def test_generator_stats(self):
        """Test generation statistics"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        generator.generate_temporal_depth(
            base_config,
            before_count=5,
            after_count=3
        )

        stats = generator.get_generation_stats()
        assert stats["timepoints_added_before"] == 5
        assert stats["timepoints_added_after"] == 3
        assert stats["total_timepoints"] == base_config.timepoints.count + 5 + 3
        assert stats["strategy_used"] == "progressive_training"

    def test_generator_cost_savings_estimation(self):
        """Test cost savings estimation"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        generator.generate_temporal_depth(
            base_config,
            before_count=10,
            after_count=10,
            strategy="progressive_training"
        )

        stats = generator.get_generation_stats()
        assert "cost_savings_estimated" in stats
        assert 0.0 <= stats["cost_savings_estimated"] <= 1.0

    def test_generator_negative_counts(self):
        """Test that negative counts raise error"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        with pytest.raises(ValueError, match="non-negative"):
            generator.generate_temporal_depth(base_config, before_count=-1)

    def test_generator_validate_causal_chain(self):
        """Test causal chain validation"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        # Expand with causal chain strategy
        expanded = generator.generate_temporal_depth(
            base_config,
            before_count=5,
            after_count=3,
            strategy="causal_chain"
        )

        validation = generator.validate_causal_chain(expanded)
        assert "is_valid" in validation
        assert "violations" in validation
        assert "timepoint_count" in validation
        assert validation["timepoint_count"] == base_config.timepoints.count + 5 + 3

    def test_generator_analyze_resolution_schedule(self):
        """Test resolution schedule analysis"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = generator.generate_temporal_depth(
            base_config,
            before_count=5,
            after_count=3,
            strategy="progressive_training"
        )

        analysis = generator.analyze_resolution_schedule(expanded)
        assert "has_schedule" in analysis
        assert analysis["has_schedule"] is True
        assert len(analysis["schedule_before"]) == 5
        assert len(analysis["schedule_after"]) == 3
        assert analysis["peak_resolution"] is not None

    def test_generator_compare_strategies(self):
        """Test strategy comparison"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        comparison = generator.compare_strategies(
            base_config,
            before_count=5,
            after_count=3
        )

        assert len(comparison) == 3
        assert "narrative_arc" in comparison
        assert "progressive_training" in comparison
        assert "causal_chain" in comparison

        for strategy, metrics in comparison.items():
            assert "total_timepoints" in metrics
            assert metrics["total_timepoints"] == base_config.timepoints.count + 5 + 3

    def test_generator_export_temporal_structure(self):
        """Test exporting temporal structure"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = generator.generate_temporal_depth(
            base_config,
            before_count=5,
            after_count=3,
            strategy="progressive_training"
        )

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            generator.export_temporal_structure(expanded, temp_path, format="json")

            # Verify file exists and is valid JSON
            with open(temp_path, 'r') as f:
                data = json.load(f)
                assert "total_timepoints" in data
                assert data["total_timepoints"] == base_config.timepoints.count + 5 + 3
                assert "resolution_schedule_before" in data
                assert "resolution_schedule_after" in data
        finally:
            Path(temp_path).unlink()


@pytest.mark.integration
class TestVerticalGenerationIntegration:
    """Integration tests for vertical generation"""

    def test_full_vertical_expansion(self):
        """Test complete vertical expansion workflow"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/jefferson_dinner")

        # Expand with progressive training
        expanded = generator.generate_temporal_depth(
            base_config,
            before_count=5,
            after_count=5,
            strategy="progressive_training"
        )

        # Verify expansion
        assert expanded.timepoints.before_count == 5
        assert expanded.timepoints.after_count == 5

        # Check stats
        stats = generator.get_generation_stats()
        assert stats["timepoints_added_before"] == 5
        assert stats["timepoints_added_after"] == 5
        assert stats["cost_savings_estimated"] > 0.0

        # Analyze resolution schedule
        analysis = generator.analyze_resolution_schedule(expanded)
        assert analysis["has_schedule"] is True
        assert len(analysis["schedule_before"]) == 5
        assert len(analysis["schedule_after"]) == 5

    def test_multiple_expansion_strategies(self):
        """Test using different expansion strategies"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        strategies = ["narrative_arc", "progressive_training", "causal_chain"]

        for strategy in strategies:
            expanded = generator.generate_temporal_depth(
                base_config,
                before_count=3,
                after_count=2,
                strategy=strategy
            )

            assert expanded.timepoints.before_count == 3
            assert expanded.timepoints.after_count == 2
            assert expanded.metadata.get("temporal_expansion", {}).get("strategy") == strategy

    def test_deep_temporal_expansion(self):
        """Test deep temporal expansion (many timepoints)"""
        generator = VerticalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        expanded = generator.generate_temporal_depth(
            base_config,
            before_count=20,
            after_count=20,
            strategy="progressive_training"
        )

        assert expanded.timepoints.before_count == 20
        assert expanded.timepoints.after_count == 20

        stats = generator.get_generation_stats()
        assert stats["total_timepoints"] == base_config.timepoints.count + 40

        # Should have significant cost savings with progressive training
        assert stats["cost_savings_estimated"] > 0.7  # >70% savings
