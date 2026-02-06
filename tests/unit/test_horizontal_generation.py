"""
Tests for Horizontal Data Generation (Sprint 1.2)

Tests variation strategies and horizontal generation functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path

from generation.horizontal_generator import HorizontalGenerator, VariationDeduplicator
from generation.variation_strategies import (
    VariationStrategyFactory,
    PersonalityVariation,
    KnowledgeVariation,
    RelationshipVariation,
    OutcomeVariation,
    StartingConditionVariation
)
from generation.config_schema import (
    SimulationConfig,
    EntityConfig,
    CompanyConfig,
    TemporalConfig,
    TemporalMode,
    OutputConfig,
    VariationConfig,
)
from generation.templates.loader import TemplateLoader

_loader = TemplateLoader()


class TestVariationStrategies:
    """Tests for individual variation strategies"""

    def test_personality_variation(self):
        """Test personality trait variation"""
        strategy = PersonalityVariation(magnitude=0.3)
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        variation = strategy.apply(base_config, variation_index=0)

        assert variation["metadata"]["variation_strategy"] == "personality"
        assert "personality_variations" in variation["metadata"]
        assert len(variation["metadata"]["personality_variations"]) == 5  # 5 entities

        # Check personality traits are in valid range
        for entity_personality in variation["metadata"]["personality_variations"]:
            assert 0.0 <= entity_personality["openness"] <= 1.0
            assert 0.0 <= entity_personality["conscientiousness"] <= 1.0
            assert 0.0 <= entity_personality["extraversion"] <= 1.0
            assert 0.0 <= entity_personality["agreeableness"] <= 1.0
            assert 0.0 <= entity_personality["neuroticism"] <= 1.0

    def test_knowledge_variation(self):
        """Test knowledge distribution variation"""
        strategy = KnowledgeVariation(knowledge_pool_size=10)
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        variation = strategy.apply(base_config, variation_index=1)

        assert variation["metadata"]["variation_strategy"] == "knowledge"
        assert "knowledge_distributions" in variation["metadata"]

        # Each entity should have some knowledge
        for dist in variation["metadata"]["knowledge_distributions"]:
            assert "knowledge_items" in dist
            assert len(dist["knowledge_items"]) > 0

    def test_relationship_variation(self):
        """Test relationship state variation"""
        strategy = RelationshipVariation(magnitude=0.4)
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        variation = strategy.apply(base_config, variation_index=2)

        assert variation["metadata"]["variation_strategy"] == "relationships"
        assert "initial_relationships" in variation["metadata"]

        # Check relationship values are in valid range
        for rel in variation["metadata"]["initial_relationships"]:
            assert 0.0 <= rel["trust_level"] <= 1.0
            assert -1.0 <= rel["emotional_bond"] <= 1.0
            assert -1.0 <= rel["power_dynamic"] <= 1.0
            assert 0.0 <= rel["belief_alignment"] <= 1.0

    def test_outcome_variation(self):
        """Test decision parameter variation"""
        strategy = OutcomeVariation(magnitude=0.3)
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        variation = strategy.apply(base_config, variation_index=3)

        assert variation["metadata"]["variation_strategy"] == "outcomes"
        assert "decision_parameters" in variation["metadata"]

        # Check decision parameters are in valid range
        for params in variation["metadata"]["decision_parameters"]:
            assert 0.0 <= params["risk_tolerance"] <= 1.0
            assert 0.0 <= params["decision_confidence"] <= 1.0
            assert 0.0 <= params["patience_threshold"] <= 100.0
            assert 0.0 <= params["social_engagement"] <= 1.0

    def test_starting_condition_variation(self):
        """Test starting state variation"""
        strategy = StartingConditionVariation(magnitude=0.25)
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        variation = strategy.apply(base_config, variation_index=4)

        assert variation["metadata"]["variation_strategy"] == "starting_conditions"
        assert "starting_states" in variation["metadata"]

        # Check starting states are in valid range
        for state in variation["metadata"]["starting_states"]:
            assert 20.0 <= state["energy_budget"] <= 100.0
            assert -1.0 <= state["emotional_valence"] <= 1.0
            assert 0.0 <= state["emotional_arousal"] <= 1.0
            assert 0.5 <= state["health_status"] <= 1.0
            assert 0.0 <= state["pain_level"] <= 1.0

    def test_strategy_factory(self):
        """Test strategy factory creation"""
        strategy = VariationStrategyFactory.create("vary_personalities")
        assert isinstance(strategy, PersonalityVariation)

        strategy = VariationStrategyFactory.create("vary_knowledge")
        assert isinstance(strategy, KnowledgeVariation)

        strategy = VariationStrategyFactory.create("vary_relationships")
        assert isinstance(strategy, RelationshipVariation)

        strategy = VariationStrategyFactory.create("vary_outcomes")
        assert isinstance(strategy, OutcomeVariation)

        strategy = VariationStrategyFactory.create("vary_starting_conditions")
        assert isinstance(strategy, StartingConditionVariation)

    def test_strategy_factory_invalid(self):
        """Test strategy factory with invalid name"""
        with pytest.raises(ValueError, match="Unknown strategy"):
            VariationStrategyFactory.create("invalid_strategy")

    def test_strategy_factory_available(self):
        """Test getting available strategies"""
        strategies = VariationStrategyFactory.get_available_strategies()
        assert len(strategies) == 5
        assert "vary_personalities" in strategies
        assert "vary_knowledge" in strategies
        assert "vary_relationships" in strategies
        assert "vary_outcomes" in strategies
        assert "vary_starting_conditions" in strategies

    def test_variation_reproducibility(self):
        """Test that same seed produces same variation"""
        strategy = PersonalityVariation()
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        var1 = strategy.apply(base_config, variation_index=0, random_seed=42)
        var2 = strategy.apply(base_config, variation_index=0, random_seed=42)

        # Should be identical
        assert var1["metadata"]["personality_variations"] == var2["metadata"]["personality_variations"]

    def test_variation_diversity(self):
        """Test that different indices produce different variations"""
        strategy = PersonalityVariation()
        base_config = _loader.load_template("showcase/board_meeting").to_dict()

        var1 = strategy.apply(base_config, variation_index=0, random_seed=42)
        var2 = strategy.apply(base_config, variation_index=1, random_seed=42)

        # Should be different
        assert var1["metadata"]["personality_variations"] != var2["metadata"]["personality_variations"]


class TestVariationDeduplicator:
    """Tests for deduplication logic"""

    def test_deduplicator_basic(self):
        """Test basic deduplication"""
        dedup = VariationDeduplicator()

        config = _loader.load_template("showcase/board_meeting").to_dict()
        config["metadata"] = {"variation_index": 0}

        # First time: not a duplicate
        assert not dedup.is_duplicate(config)

        # Register it
        dedup.register_variation(config)

        # Second time: is a duplicate
        assert dedup.is_duplicate(config)

    def test_deduplicator_different_variations(self):
        """Test that different variations are not duplicates"""
        dedup = VariationDeduplicator()

        config1 = _loader.load_template("showcase/board_meeting").to_dict()
        config1["metadata"] = {"variation_index": 0, "variation_strategy": "personality"}

        config2 = _loader.load_template("showcase/board_meeting").to_dict()
        config2["metadata"] = {"variation_index": 1, "variation_strategy": "personality"}

        dedup.register_variation(config1)
        assert not dedup.is_duplicate(config2)

    def test_deduplicator_reset(self):
        """Test deduplicator reset"""
        dedup = VariationDeduplicator()

        config = _loader.load_template("showcase/board_meeting").to_dict()
        config["metadata"] = {"variation_index": 0}

        dedup.register_variation(config)
        assert dedup.get_duplicate_count() == 1

        dedup.reset()
        assert dedup.get_duplicate_count() == 0
        assert not dedup.is_duplicate(config)


class TestHorizontalGenerator:
    """Tests for HorizontalGenerator"""

    def test_generator_basic(self):
        """Test basic variation generation"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        variations = generator.generate_variations(
            base_config=base_config,
            count=10,
            strategies=["vary_personalities"]
        )

        assert len(variations) == 10
        for var in variations:
            assert var.world_id.startswith("board_meeting_example_var_")

    def test_generator_multiple_strategies(self):
        """Test generation with multiple strategies"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        variations = generator.generate_variations(
            base_config=base_config,
            count=5,
            strategies=["vary_personalities", "vary_outcomes"]
        )

        assert len(variations) == 5

    def test_generator_sequential(self):
        """Test sequential generation"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        variations = generator.generate_variations(
            base_config=base_config,
            count=10,
            strategies=["vary_personalities"],
            parallel=False
        )

        assert len(variations) == 10

    def test_generator_parallel(self):
        """Test parallel generation"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        variations = generator.generate_variations(
            base_config=base_config,
            count=10,
            strategies=["vary_personalities"],
            parallel=True,
            max_workers=2
        )

        assert len(variations) == 10

    def test_generator_stats(self):
        """Test generation statistics"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        generator.generate_variations(
            base_config=base_config,
            count=5,
            strategies=["vary_personalities"]
        )

        stats = generator.get_generation_stats()
        assert stats["variations_requested"] == 5
        assert stats["variations_created"] == 5
        assert stats["duplicates_rejected"] == 0
        assert "vary_personalities" in stats["strategies_used"]

    def test_generator_progress_callback(self):
        """Test progress callback"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        progress_updates = []

        def progress_callback(current, total):
            progress_updates.append((current, total))

        generator.generate_variations(
            base_config=base_config,
            count=5,
            strategies=["vary_personalities"],
            progress_callback=progress_callback
        )

        assert len(progress_updates) == 5
        assert progress_updates[-1] == (5, 5)

    def test_generator_reproducibility(self):
        """Test that same seed produces same variations"""
        generator1 = HorizontalGenerator()
        generator2 = HorizontalGenerator()

        base_config = _loader.load_template("showcase/board_meeting")

        vars1 = generator1.generate_variations(
            base_config=base_config,
            count=5,
            strategies=["vary_personalities"],
            random_seed=42
        )

        vars2 = generator2.generate_variations(
            base_config=base_config,
            count=5,
            strategies=["vary_personalities"],
            random_seed=42
        )

        # Should produce same variations
        for v1, v2 in zip(vars1, vars2):
            assert v1.metadata["personality_variations"] == v2.metadata["personality_variations"]

    def test_generator_quality_estimation(self):
        """Test variation quality estimation"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        variations = generator.generate_variations(
            base_config=base_config,
            count=10,
            strategies=["vary_personalities", "vary_outcomes"]
        )

        quality = generator.estimate_variation_quality(variations)

        assert quality["unique_count"] == 10
        assert 0.0 <= quality["diversity_score"] <= 1.0
        assert "strategy_distribution" in quality

    def test_generator_batch_generate(self):
        """Test batch generation for multiple configs"""
        generator = HorizontalGenerator()

        configs = [
            _loader.load_template("showcase/board_meeting"),
            _loader.load_template("showcase/jefferson_dinner")
        ]

        results = generator.batch_generate(
            base_configs=configs,
            count_per_config=5,
            strategies=["vary_personalities"]
        )

        assert len(results) == 2
        assert "board_meeting_example" in results
        assert "jefferson_dinner" in results
        assert len(results["board_meeting_example"]) == 5
        assert len(results["jefferson_dinner"]) == 5

    def test_generator_export_json(self):
        """Test export to JSON format"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        variations = generator.generate_variations(
            base_config=base_config,
            count=3,
            strategies=["vary_personalities"]
        )

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            generator.export_variations(variations, temp_path, format="json")

            # Verify file exists and is valid JSON
            with open(temp_path, 'r') as f:
                data = json.load(f)
                assert len(data) == 3
        finally:
            Path(temp_path).unlink()

    def test_generator_export_jsonl(self):
        """Test export to JSONL format"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        variations = generator.generate_variations(
            base_config=base_config,
            count=3,
            strategies=["vary_personalities"]
        )

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            temp_path = f.name

        try:
            generator.export_variations(variations, temp_path, format="jsonl")

            # Verify file exists and has correct number of lines
            with open(temp_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 3
                # Each line should be valid JSON
                for line in lines:
                    json.loads(line)
        finally:
            Path(temp_path).unlink()

    def test_generator_invalid_strategy(self):
        """Test generator with invalid strategy"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        with pytest.raises(ValueError):
            generator.generate_variations(
                base_config=base_config,
                count=5,
                strategies=["invalid_strategy"]
            )

    def test_generator_no_strategies(self):
        """Test generator with no strategies"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        with pytest.raises(ValueError, match="Must provide at least one"):
            generator.generate_variations(
                base_config=base_config,
                count=5,
                strategies=[]
            )

    def test_generator_invalid_count(self):
        """Test generator with invalid count"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        with pytest.raises(ValueError, match="Count must be at least 1"):
            generator.generate_variations(
                base_config=base_config,
                count=0,
                strategies=["vary_personalities"]
            )


@pytest.mark.integration
class TestHorizontalGenerationIntegration:
    """Integration tests for horizontal generation"""

    def test_full_generation_workflow(self):
        """Test complete generation workflow"""
        generator = HorizontalGenerator()
        base_config = SimulationConfig(
            scenario_description="Generate variations of a negotiation scenario",
            world_id="negotiation_variations",
            entities=EntityConfig(count=4, types=["human"]),
            timepoints=CompanyConfig(count=2, resolution="hour"),
            temporal=TemporalConfig(mode=TemporalMode.PEARL),
            outputs=OutputConfig(
                formats=["jsonl"],
                export_ml_dataset=True
            ),
            variations=VariationConfig(
                enabled=True,
                count=100,
                strategies=["vary_personalities", "vary_outcomes"]
            )
        )

        # Generate variations
        variations = generator.generate_variations(
            base_config=base_config,
            count=20,
            strategies=["vary_personalities", "vary_outcomes"],
            parallel=True
        )

        assert len(variations) == 20

        # Check stats
        stats = generator.get_generation_stats()
        assert stats["variations_created"] == 20

        # Check quality
        quality = generator.estimate_variation_quality(variations)
        assert quality["unique_count"] == 20

    def test_large_batch_generation(self):
        """Test generating large batch of variations"""
        generator = HorizontalGenerator()
        base_config = _loader.load_template("showcase/board_meeting")

        variations = generator.generate_variations(
            base_config=base_config,
            count=100,
            strategies=["vary_personalities"],
            parallel=True,
            max_workers=4
        )

        assert len(variations) == 100

        # All should have unique world_ids
        world_ids = {v.world_id for v in variations}
        assert len(world_ids) == 100
