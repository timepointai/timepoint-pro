"""
NL Interface Adapter - Convert NL output to Production SimulationConfig

This adapter bridges the gap between the simple NL interface output schema
and the complex production SimulationConfig required by e2e_runner.
"""

from typing import Dict, Any, Optional, Tuple
import hashlib
from datetime import datetime

from generation.config_schema import (
    SimulationConfig,
    EntityConfig,
    CompanyConfig,
    TemporalConfig,
    OutputConfig,
    VariationConfig,
    TemporalMode,
    ResolutionLevel,
)


class NLToProductionAdapter:
    """
    Converts NL interface output to production SimulationConfig.

    The NL interface generates a simple flat config:
        {scenario, entities: [{name, role}], timepoint_count, temporal_mode, focus, outputs}

    Production expects a complex nested SimulationConfig with:
        EntityConfig, CompanyConfig, TemporalConfig, OutputConfig, etc.

    Example:
        adapter = NLToProductionAdapter()
        nl_config = {"scenario": "Board meeting...", "entities": [...], ...}
        production_config = adapter.convert(nl_config)
        runner.run(production_config)
    """

    # Map NL focus areas to OutputConfig flags
    FOCUS_TO_OUTPUT_FLAGS = {
        "dialog": {"include_dialogs": True},
        "decision_making": {"include_dialogs": True},
        "relationships": {"include_relationships": True},
        "stress_responses": {"include_dialogs": True},
        "knowledge_propagation": {"include_knowledge_flow": True},
    }

    # Map NL temporal modes to production TemporalMode enum
    TEMPORAL_MODE_MAP = {
        "pearl": TemporalMode.PEARL,
        "directorial": TemporalMode.DIRECTORIAL,
        "branching": TemporalMode.BRANCHING,
        "cyclical": TemporalMode.CYCLICAL,
        "portal": TemporalMode.PORTAL,
    }

    def __init__(self, default_resolution: str = "hour"):
        """
        Initialize adapter.

        Args:
            default_resolution: Default temporal resolution (year, month, day, hour, minute)
        """
        self.default_resolution = default_resolution

    def convert(
        self,
        nl_config: Dict[str, Any],
        confidence: float = 0.8
    ) -> SimulationConfig:
        """
        Convert NL interface output to production SimulationConfig.

        Args:
            nl_config: Dictionary from NLConfigGenerator.generate_config()
            confidence: Confidence score from NL generation (stored in metadata)

        Returns:
            SimulationConfig ready for e2e_runner.run()

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        self._validate_nl_config(nl_config)

        # Generate world_id from scenario (deterministic hash)
        world_id = self._generate_world_id(nl_config.get("scenario", ""))

        # Build component configs
        entities = self._build_entity_config(nl_config)
        timepoints = self._build_timepoints_config(nl_config)
        temporal = self._build_temporal_config(nl_config)
        outputs = self._build_output_config(nl_config)
        variations = self._build_variation_config(nl_config)

        # Build metadata (preserve NL generation info)
        metadata = self._build_metadata(nl_config, confidence)

        return SimulationConfig(
            scenario_description=nl_config.get("scenario", "NL-generated scenario"),
            world_id=world_id,
            entities=entities,
            timepoints=timepoints,
            temporal=temporal,
            outputs=outputs,
            variations=variations,
            metadata=metadata,
        )

    def _validate_nl_config(self, nl_config: Dict[str, Any]) -> None:
        """Validate that NL config has minimum required fields."""
        required = ["scenario", "entities", "timepoint_count", "temporal_mode"]
        missing = [f for f in required if f not in nl_config]
        if missing:
            raise ValueError(f"NL config missing required fields: {missing}")

    def _generate_world_id(self, scenario: str) -> str:
        """Generate deterministic world_id from scenario description."""
        # Use first 8 chars of MD5 hash + timestamp for uniqueness
        scenario_hash = hashlib.md5(scenario.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"nl_{scenario_hash}_{timestamp}"

    def _build_entity_config(self, nl_config: Dict[str, Any]) -> EntityConfig:
        """Convert NL entity list to EntityConfig."""
        entities = nl_config.get("entities", [])
        count = len(entities) if entities else 3

        # Infer entity types from roles (simple heuristic)
        types = ["human"]  # Default to human

        # Check for animism level
        animism_level = nl_config.get("animism_level", 0)
        if animism_level > 0:
            types = ["human", "animal", "building"][:animism_level + 1]

        return EntityConfig(
            count=count,
            types=types,
            initial_resolution=ResolutionLevel.TENSOR_ONLY,
            animism_level=animism_level,
        )

    def _build_timepoints_config(self, nl_config: Dict[str, Any]) -> CompanyConfig:
        """Convert NL timepoint_count to CompanyConfig."""
        count = nl_config.get("timepoint_count", 5)

        # Parse start_time if provided
        start_time = None
        if nl_config.get("start_time"):
            try:
                start_time = datetime.fromisoformat(nl_config["start_time"])
            except (ValueError, TypeError):
                pass  # Use default

        return CompanyConfig(
            count=count,
            start_time=start_time,
            resolution=self.default_resolution,
            before_count=0,
            after_count=0,
        )

    def _build_temporal_config(self, nl_config: Dict[str, Any]) -> TemporalConfig:
        """Convert NL temporal_mode to TemporalConfig."""
        mode_str = nl_config.get("temporal_mode", "pearl").lower()
        mode = self.TEMPORAL_MODE_MAP.get(mode_str, TemporalMode.PEARL)

        config_kwargs = {"mode": mode}

        # Set mode-specific defaults
        if mode == TemporalMode.DIRECTORIAL:
            config_kwargs["narrative_arc"] = "rising_action"
            config_kwargs["dramatic_tension"] = 0.7
        elif mode == TemporalMode.CYCLICAL:
            config_kwargs["cycle_length"] = nl_config.get("timepoint_count", 5)
            config_kwargs["prophecy_accuracy"] = 0.5
        elif mode == TemporalMode.BRANCHING:
            config_kwargs["enable_counterfactuals"] = True

        return TemporalConfig(**config_kwargs)

    def _build_output_config(self, nl_config: Dict[str, Any]) -> OutputConfig:
        """Convert NL focus/outputs to OutputConfig."""
        focus_areas = nl_config.get("focus", ["dialog"])
        output_types = nl_config.get("outputs", ["dialog"])

        # Start with defaults
        config_kwargs = {
            "formats": ["json", "markdown"],
            "include_dialogs": False,
            "include_relationships": False,
            "include_knowledge_flow": False,
            "export_ml_dataset": False,
        }

        # Apply focus area flags
        for focus in focus_areas:
            if focus in self.FOCUS_TO_OUTPUT_FLAGS:
                config_kwargs.update(self.FOCUS_TO_OUTPUT_FLAGS[focus])

        # Check output types for ML export
        if "ml_dataset" in output_types or "jsonl" in output_types:
            config_kwargs["export_ml_dataset"] = True
            config_kwargs["formats"].append("jsonl")

        # Ensure at least dialogs are included for most scenarios
        if "dialog" in focus_areas or "dialog" in output_types:
            config_kwargs["include_dialogs"] = True

        return OutputConfig(**config_kwargs)

    def _build_variation_config(self, nl_config: Dict[str, Any]) -> VariationConfig:
        """Convert NL variation settings to VariationConfig."""
        generation_mode = nl_config.get("generation_mode", "vertical")
        variation_count = nl_config.get("variation_count", 1)

        if generation_mode == "horizontal" and variation_count > 1:
            return VariationConfig(
                enabled=True,
                count=variation_count,
                strategies=["vary_personalities", "vary_outcomes"],
            )

        return VariationConfig(enabled=False)

    def _build_metadata(
        self,
        nl_config: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """Build metadata preserving NL generation info."""
        return {
            "source": "nl_interface",
            "nl_confidence": confidence,
            "nl_scenario": nl_config.get("scenario", ""),
            "nl_entities": nl_config.get("entities", []),
            "nl_focus": nl_config.get("focus", []),
            "generated_at": datetime.now().isoformat(),
        }


def convert_nl_to_production(
    nl_config: Dict[str, Any],
    confidence: float = 0.8
) -> SimulationConfig:
    """
    Convenience function to convert NL config to production config.

    Args:
        nl_config: Dictionary from NLConfigGenerator
        confidence: Confidence score

    Returns:
        SimulationConfig for e2e_runner

    Example:
        from nl_interface import NLConfigGenerator
        from nl_interface.adapter import convert_nl_to_production

        generator = NLConfigGenerator(api_key="...")
        nl_config, confidence = generator.generate_config("Board meeting...")
        production_config = convert_nl_to_production(nl_config, confidence)
    """
    adapter = NLToProductionAdapter()
    return adapter.convert(nl_config, confidence)
