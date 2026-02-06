"""
Configuration Validator for NL-Generated Configs

Provides semantic validation and constraint checking beyond Pydantic schema validation.
Ensures generated configs are not only well-formed but also sensible and executable.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class EntityConfig(BaseModel):
    """Entity configuration"""
    name: str
    role: str
    personality_traits: Optional[Dict[str, float]] = None


class SimulationConfig(BaseModel):
    """
    Simulation configuration schema.

    This is the target format for NL → Config translation.
    """
    scenario: str = Field(..., description="Descriptive title for the scenario")
    entities: List[EntityConfig] = Field(..., description="List of entities to simulate")
    timepoint_count: int = Field(..., ge=1, le=100, description="Number of timepoints")
    temporal_mode: str = Field(
        ...,
        description="Temporal causality mode",
        pattern="^(pearl|directorial|branching|cyclical|portal)$"
    )
    focus: List[str] = Field(..., description="Simulation focus areas")
    outputs: List[str] = Field(..., description="Desired outputs")

    # Optional fields
    start_time: Optional[str] = Field(None, description="ISO datetime for scenario start")
    animism_level: Optional[int] = Field(None, ge=0, le=3, description="Animistic entity support level")
    resolution_mode: Optional[str] = Field(None, description="Resolution elevation strategy")
    generation_mode: Optional[str] = Field(None, description="horizontal or vertical")
    variation_count: Optional[int] = Field(None, ge=1, le=1000, description="For horizontal generation")
    variation_strategy: Optional[str] = Field(None, description="Variation strategy name")

    @field_validator('entities')
    @classmethod
    def validate_entity_count(cls, v):
        """Ensure reasonable entity count"""
        if len(v) < 1:
            raise ValueError("Must have at least 1 entity")
        if len(v) > 100:
            raise ValueError("Maximum 100 entities allowed")
        return v

    @field_validator('focus')
    @classmethod
    def validate_focus_areas(cls, v):
        """Ensure valid focus areas"""
        valid_focus = {
            "dialog", "decision_making", "relationships",
            "stress_responses", "knowledge_propagation"
        }
        invalid = set(v) - valid_focus
        if invalid:
            raise ValueError(f"Invalid focus areas: {invalid}. Valid: {valid_focus}")
        return v

    @field_validator('outputs')
    @classmethod
    def validate_outputs(cls, v):
        """Ensure valid output types"""
        valid_outputs = {
            "dialog", "decisions", "relationships", "knowledge_flow"
        }
        invalid = set(v) - valid_outputs
        if invalid:
            raise ValueError(f"Invalid outputs: {invalid}. Valid: {valid_outputs}")
        return v


class ValidationResult(BaseModel):
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class ConfigValidator:
    """
    Semantic validator for simulation configurations.

    Performs validation beyond Pydantic schema checking:
    - Constraint checking (reasonable values)
    - Semantic validation (coherence checks)
    - Fix suggestions for invalid configs
    - Confidence scoring

    Example:
        validator = ConfigValidator()
        result = validator.validate(config_dict)

        if not result.is_valid:
            print("Errors:", result.errors)
            print("Suggestions:", result.suggestions)
        elif result.warnings:
            print("Warnings:", result.warnings)
    """

    def __init__(self):
        """Initialize validator"""
        self.max_entities = 100
        self.max_timepoints = 100
        self.max_variation_count = 1000

    def validate(self, config_dict: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration.

        Args:
            config_dict: Configuration dictionary

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        result = ValidationResult(is_valid=True)

        # Try Pydantic validation first
        try:
            config = SimulationConfig(**config_dict)
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Schema validation failed: {str(e)}")
            result.confidence_score = 0.0
            return result

        # Semantic validation checks
        self._check_entity_count(config, result)
        self._check_timepoint_count(config, result)
        self._check_temporal_coherence(config, result)
        self._check_historical_plausibility(config, result)
        self._check_output_feasibility(config, result)
        self._check_generation_mode(config, result)

        # Calculate confidence score
        result.confidence_score = self._calculate_confidence(result)

        return result

    def _check_entity_count(self, config: SimulationConfig, result: ValidationResult):
        """Check entity count is reasonable"""
        entity_count = len(config.entities)

        if entity_count > 50:
            result.warnings.append(
                f"Large entity count ({entity_count}). Consider reducing for detailed simulations."
            )
            result.suggestions.append(
                "For detailed dialog and relationships, 3-20 entities is recommended."
            )

        if entity_count > self.max_entities:
            result.is_valid = False
            result.errors.append(f"Entity count {entity_count} exceeds maximum {self.max_entities}")

    def _check_timepoint_count(self, config: SimulationConfig, result: ValidationResult):
        """Check timepoint count is reasonable"""
        if config.timepoint_count > 50:
            result.warnings.append(
                f"Large timepoint count ({config.timepoint_count}). "
                "This will be expensive and time-consuming."
            )
            result.suggestions.append(
                "For initial simulations, 3-15 timepoints is recommended."
            )

        if config.timepoint_count > self.max_timepoints:
            result.is_valid = False
            result.errors.append(
                f"Timepoint count {config.timepoint_count} exceeds maximum {self.max_timepoints}"
            )

    def _check_temporal_coherence(self, config: SimulationConfig, result: ValidationResult):
        """Check temporal mode makes sense for scenario"""
        mode = config.temporal_mode

        # Check if branching mode makes sense
        if mode == "branching" and config.timepoint_count < 3:
            result.warnings.append(
                "Branching mode typically needs 3+ timepoints to show divergence."
            )

        # Check if cyclical mode makes sense
        if mode == "cyclical" and config.timepoint_count < 5:
            result.warnings.append(
                "Cyclical mode typically needs 5+ timepoints to complete a cycle."
            )

    def _check_historical_plausibility(self, config: SimulationConfig, result: ValidationResult):
        """Check historical dates and entity roles are plausible"""
        if config.start_time:
            try:
                dt = datetime.fromisoformat(config.start_time.replace('Z', '+00:00'))

                # Check if date is too far in the future
                if dt.year > 2100:
                    result.warnings.append(
                        f"Start time is far in the future ({dt.year}). Is this intentional?"
                    )

                # Check if date is very old
                if dt.year < 1500:
                    result.warnings.append(
                        f"Start time is very old ({dt.year}). Historical accuracy may be limited."
                    )

            except ValueError as e:
                result.errors.append(f"Invalid start_time format: {e}")
                result.is_valid = False

    def _check_output_feasibility(self, config: SimulationConfig, result: ValidationResult):
        """Check requested outputs are feasible given focus areas"""
        # Dialog output requires dialog focus
        if "dialog" in config.outputs and "dialog" not in config.focus:
            result.warnings.append(
                "Requested 'dialog' output but 'dialog' not in focus areas. "
                "Consider adding 'dialog' to focus."
            )

        # Knowledge flow output requires knowledge_propagation focus
        if "knowledge_flow" in config.outputs and "knowledge_propagation" not in config.focus:
            result.warnings.append(
                "Requested 'knowledge_flow' output but 'knowledge_propagation' not in focus. "
                "Consider adding 'knowledge_propagation' to focus."
            )

        # Relationships output requires relationships focus
        if "relationships" in config.outputs and "relationships" not in config.focus:
            result.warnings.append(
                "Requested 'relationships' output but 'relationships' not in focus. "
                "Consider adding 'relationships' to focus."
            )

    def _check_generation_mode(self, config: SimulationConfig, result: ValidationResult):
        """Check generation mode configuration"""
        if config.generation_mode == "horizontal":
            if not config.variation_count:
                result.warnings.append(
                    "Horizontal generation mode specified but no variation_count. "
                    "Defaulting to 1 variation."
                )

            if config.variation_count and config.variation_count > self.max_variation_count:
                result.is_valid = False
                result.errors.append(
                    f"Variation count {config.variation_count} exceeds "
                    f"maximum {self.max_variation_count}"
                )

    def _calculate_confidence(self, result: ValidationResult) -> float:
        """
        Calculate confidence score based on validation results.

        Score from 0.0 to 1.0:
        - 1.0: No errors or warnings
        - 0.8-0.9: Warnings but no errors
        - 0.0: Has errors
        """
        if not result.is_valid or result.errors:
            return 0.0

        if not result.warnings:
            return 1.0

        # Reduce confidence based on warning count
        warning_penalty = min(0.2, len(result.warnings) * 0.05)
        return 1.0 - warning_penalty

    def suggest_fixes(self, config_dict: Dict[str, Any]) -> List[str]:
        """
        Suggest fixes for invalid configuration.

        Args:
            config_dict: Configuration dictionary

        Returns:
            List of suggested fixes
        """
        result = self.validate(config_dict)

        if result.is_valid:
            return ["Configuration is valid!"]

        return result.suggestions + [
            f"Fix error: {error}" for error in result.errors
        ]
