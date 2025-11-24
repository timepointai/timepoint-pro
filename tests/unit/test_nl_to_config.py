"""
Tests for NL to Config Translation (Sprint 3.1)
"""

import pytest
from nl_interface import (
    NLConfigGenerator,
    ConfigValidator,
    SimulationConfig,
    ValidationResult
)


class TestConfigValidator:
    """Tests for ConfigValidator"""

    def test_valid_config(self):
        """Test validation of valid configuration"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test Scenario",
            "entities": [
                {"name": "Alice", "role": "CEO"},
                {"name": "Bob", "role": "CFO"}
            ],
            "timepoint_count": 5,
            "temporal_mode": "pearl",
            "focus": ["dialog", "decision_making"],
            "outputs": ["dialog", "decisions"]
        }

        result = validator.validate(config)
        assert result.is_valid
        assert not result.errors
        assert result.confidence_score >= 0.9

    def test_missing_required_field(self):
        """Test validation catches missing required fields"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            # Missing timepoint_count
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_invalid_temporal_mode(self):
        """Test validation catches invalid temporal mode"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 5,
            "temporal_mode": "invalid_mode",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert not result.is_valid

    def test_too_many_entities(self):
        """Test validation catches excessive entities"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": f"Person{i}", "role": "Role"} for i in range(101)],
            "timepoint_count": 5,
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert not result.is_valid
        # Pydantic validation catches this, check for error message
        assert any("entities" in error.lower() or "maximum" in error.lower() for error in result.errors)

    def test_too_many_timepoints(self):
        """Test validation catches excessive timepoints"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 101,
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert not result.is_valid
        # Pydantic validation catches this, check for error message
        assert any("timepoint" in error.lower() or "less than or equal to 100" in error.lower() for error in result.errors)

    def test_invalid_focus_area(self):
        """Test validation catches invalid focus areas"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 5,
            "temporal_mode": "pearl",
            "focus": ["invalid_focus"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert not result.is_valid

    def test_invalid_output_type(self):
        """Test validation catches invalid output types"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 5,
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["invalid_output"]
        }

        result = validator.validate(config)
        assert not result.is_valid

    def test_warning_for_large_entity_count(self):
        """Test warning for large (but valid) entity count"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": f"Person{i}", "role": "Role"} for i in range(60)],
            "timepoint_count": 5,
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert result.is_valid
        assert len(result.warnings) > 0
        assert result.confidence_score < 1.0

    def test_warning_for_large_timepoint_count(self):
        """Test warning for large (but valid) timepoint count"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 60,
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert result.is_valid
        assert len(result.warnings) > 0

    def test_warning_for_output_focus_mismatch(self):
        """Test warning when output doesn't match focus"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 5,
            "temporal_mode": "pearl",
            "focus": ["decision_making"],  # No dialog focus
            "outputs": ["dialog"]  # But requesting dialog output
        }

        result = validator.validate(config)
        assert result.is_valid  # Valid but has warning
        assert len(result.warnings) > 0

    def test_valid_start_time(self):
        """Test validation accepts valid start time"""
        validator = ConfigValidator()

        config = {
            "scenario": "Historical Event",
            "entities": [{"name": "George Washington", "role": "President"}],
            "timepoint_count": 5,
            "start_time": "1789-04-30T10:00:00",
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert result.is_valid

    def test_invalid_start_time_format(self):
        """Test validation catches invalid start time format"""
        validator = ConfigValidator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 5,
            "start_time": "not-a-date",
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = validator.validate(config)
        assert not result.is_valid

    def test_generation_mode_horizontal(self):
        """Test validation of horizontal generation mode"""
        validator = ConfigValidator()

        config = {
            "scenario": "Variations",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 3,
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"],
            "generation_mode": "horizontal",
            "variation_count": 50
        }

        result = validator.validate(config)
        assert result.is_valid

    def test_excessive_variation_count(self):
        """Test validation catches excessive variation count"""
        validator = ConfigValidator()

        config = {
            "scenario": "Variations",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 3,
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"],
            "generation_mode": "horizontal",
            "variation_count": 1001  # Exceeds max
        }

        result = validator.validate(config)
        assert not result.is_valid


class TestNLConfigGenerator:
    """Tests for NLConfigGenerator"""

    def test_generator_initialization_mock_mode(self):
        """Test generator initializes in mock mode without API key"""
        generator = NLConfigGenerator()
        assert generator.mock_mode is True

    def test_generator_initialization_with_api_key(self):
        """Test generator initializes with API key"""
        generator = NLConfigGenerator(api_key="test_key")
        assert generator.mock_mode is False
        assert generator.api_key == "test_key"

    def test_mock_config_generation_simple(self):
        """Test mock config generation with simple description"""
        generator = NLConfigGenerator()  # Mock mode

        config, confidence = generator.generate_config(
            "Simulate a board meeting with 5 people"
        )

        assert isinstance(config, dict)
        assert "scenario" in config
        assert "entities" in config
        assert len(config["entities"]) == 5
        assert "timepoint_count" in config
        assert "temporal_mode" in config
        assert confidence > 0.0

    def test_mock_config_generation_complex(self):
        """Test mock config generation with complex description"""
        generator = NLConfigGenerator()

        config, confidence = generator.generate_config(
            "Simulate the Constitutional Convention with 10 delegates. "
            "Focus on relationships and decision making."
        )

        assert isinstance(config, dict)
        assert len(config["entities"]) == 10
        assert "relationships" in config["focus"]
        assert "decision_making" in config["focus"]

    def test_mock_config_is_valid(self):
        """Test mock-generated configs are valid"""
        generator = NLConfigGenerator()

        config, confidence = generator.generate_config(
            "Board meeting with 5 executives"
        )

        # Validate config
        validation = generator.validate_config(config)
        assert validation.is_valid

    def test_validate_config_method(self):
        """Test validate_config method"""
        generator = NLConfigGenerator()

        config = {
            "scenario": "Test",
            "entities": [{"name": "Alice", "role": "CEO"}],
            "timepoint_count": 5,
            "temporal_mode": "pearl",
            "focus": ["dialog"],
            "outputs": ["dialog"]
        }

        result = generator.validate_config(config)
        assert isinstance(result, ValidationResult)
        assert result.is_valid

    def test_confidence_explanation_very_high(self):
        """Test confidence explanation for very high confidence"""
        generator = NLConfigGenerator()

        explanation = generator.get_confidence_explanation(0.98)
        assert "very high" in explanation.lower()

    def test_confidence_explanation_high(self):
        """Test confidence explanation for high confidence"""
        generator = NLConfigGenerator()

        explanation = generator.get_confidence_explanation(0.87)
        assert "high" in explanation.lower()

    def test_confidence_explanation_moderate(self):
        """Test confidence explanation for moderate confidence"""
        generator = NLConfigGenerator()

        explanation = generator.get_confidence_explanation(0.72)
        assert "moderate" in explanation.lower()

    def test_confidence_explanation_low(self):
        """Test confidence explanation for low confidence"""
        generator = NLConfigGenerator()

        explanation = generator.get_confidence_explanation(0.55)
        assert "low" in explanation.lower()

    def test_confidence_explanation_very_low(self):
        """Test confidence explanation for very low confidence"""
        generator = NLConfigGenerator()

        explanation = generator.get_confidence_explanation(0.2)
        assert "very low" in explanation.lower()


class TestSimulationConfigSchema:
    """Tests for SimulationConfig Pydantic schema"""

    def test_valid_schema(self):
        """Test valid SimulationConfig"""
        config = SimulationConfig(
            scenario="Test Scenario",
            entities=[{"name": "Alice", "role": "CEO"}],
            timepoint_count=5,
            temporal_mode="pearl",
            focus=["dialog"],
            outputs=["dialog"]
        )

        assert config.scenario == "Test Scenario"
        assert len(config.entities) == 1
        assert config.timepoint_count == 5

    def test_entity_count_validation(self):
        """Test entity count validation"""
        with pytest.raises(ValueError):
            SimulationConfig(
                scenario="Test",
                entities=[],  # No entities
                timepoint_count=5,
                temporal_mode="pearl",
                focus=["dialog"],
                outputs=["dialog"]
            )

    def test_timepoint_count_bounds(self):
        """Test timepoint count bounds"""
        with pytest.raises(ValueError):
            SimulationConfig(
                scenario="Test",
                entities=[{"name": "Alice", "role": "CEO"}],
                timepoint_count=0,  # Too low
                temporal_mode="pearl",
                focus=["dialog"],
                outputs=["dialog"]
            )

        with pytest.raises(ValueError):
            SimulationConfig(
                scenario="Test",
                entities=[{"name": "Alice", "role": "CEO"}],
                timepoint_count=101,  # Too high
                temporal_mode="pearl",
                focus=["dialog"],
                outputs=["dialog"]
            )

    def test_temporal_mode_validation(self):
        """Test temporal mode validation"""
        with pytest.raises(ValueError):
            SimulationConfig(
                scenario="Test",
                entities=[{"name": "Alice", "role": "CEO"}],
                timepoint_count=5,
                temporal_mode="invalid",
                focus=["dialog"],
                outputs=["dialog"]
            )

    def test_optional_fields(self):
        """Test optional fields"""
        config = SimulationConfig(
            scenario="Test",
            entities=[{"name": "Alice", "role": "CEO"}],
            timepoint_count=5,
            temporal_mode="pearl",
            focus=["dialog"],
            outputs=["dialog"],
            start_time="2025-01-01T10:00:00",
            animism_level=2,
            resolution_mode="progressive"
        )

        assert config.start_time == "2025-01-01T10:00:00"
        assert config.animism_level == 2
        assert config.resolution_mode == "progressive"

    def test_animism_level_bounds(self):
        """Test animism level bounds"""
        with pytest.raises(ValueError):
            SimulationConfig(
                scenario="Test",
                entities=[{"name": "Alice", "role": "CEO"}],
                timepoint_count=5,
                temporal_mode="pearl",
                focus=["dialog"],
                outputs=["dialog"],
                animism_level=4  # Too high
            )
