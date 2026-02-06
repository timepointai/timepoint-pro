"""
Simulation Configuration Schema with Pydantic Validation

Provides validated configuration for simulation generation with:
- Entity configuration
- Company structure
- Temporal mode settings
- Output specifications
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from schemas import FidelityPlanningMode, TokenBudgetMode
from synth import EnvelopeConfig, VoiceConfig, VoiceMixer, DEFAULT_ENVELOPE, DEFAULT_VOICE



# ============================================================================
# Profile Loading Utilities
# ============================================================================

def load_founder_profile(archetype_id: str) -> Dict[str, Any]:
    """
    Load a founder archetype profile from JSON.

    Args:
        archetype_id: The archetype identifier (e.g., "charismatic_visionary")

    Returns:
        Dictionary containing the full profile data

    Raises:
        FileNotFoundError: If profile doesn't exist
        ValueError: If profile JSON is invalid

    Example:
        profile = load_founder_profile("charismatic_visionary")
        traits = profile["traits"]
        behaviors = profile["natural_behaviors"]
    """
    profiles_dir = Path(__file__).parent / "profiles" / "founder_archetypes"
    profile_path = profiles_dir / f"{archetype_id}.json"

    if not profile_path.exists():
        available = list_founder_archetypes()
        raise FileNotFoundError(
            f"Profile '{archetype_id}' not found. Available: {available}"
        )

    try:
        with open(profile_path, 'r') as f:
            profile = json.load(f)
        return profile
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in profile '{archetype_id}': {e}")


def list_founder_archetypes() -> List[str]:
    """
    List all available founder archetype profile IDs.

    Returns:
        List of archetype IDs (without .json extension)

    Example:
        archetypes = list_founder_archetypes()
        # ['charismatic_visionary', 'demanding_genius', ...]
    """
    profiles_dir = Path(__file__).parent / "profiles" / "founder_archetypes"

    if not profiles_dir.exists():
        return []

    return [
        p.stem for p in profiles_dir.glob("*.json")
        if p.is_file()
    ]


def load_economic_scenario(scenario_id: str) -> Dict[str, Any]:
    """
    Load an economic scenario configuration from JSON.

    Args:
        scenario_id: The scenario identifier (e.g., "bull_market_2025")

    Returns:
        Dictionary containing the full scenario data

    Raises:
        FileNotFoundError: If scenarios file doesn't exist
        ValueError: If scenario ID not found or JSON invalid

    Example:
        scenario = load_economic_scenario("bull_market_2025")
        params = scenario["parameters"]
        funding_availability = params["funding_availability"]
    """
    scenarios_path = Path(__file__).parent / "profiles" / "economic_scenarios.json"

    if not scenarios_path.exists():
        raise FileNotFoundError(
            f"Economic scenarios file not found at {scenarios_path}"
        )

    try:
        with open(scenarios_path, 'r') as f:
            all_scenarios = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in economic scenarios file: {e}")

    if scenario_id not in all_scenarios:
        available = list(all_scenarios.keys())
        raise ValueError(
            f"Scenario '{scenario_id}' not found. Available: {available}"
        )

    return all_scenarios[scenario_id]


def list_economic_scenarios() -> List[str]:
    """
    List all available economic scenario IDs.

    Returns:
        List of scenario IDs

    Example:
        scenarios = list_economic_scenarios()
        # ['bull_market_2025', 'bear_market_2023', ...]
    """
    scenarios_path = Path(__file__).parent / "profiles" / "economic_scenarios.json"

    if not scenarios_path.exists():
        return []

    try:
        with open(scenarios_path, 'r') as f:
            all_scenarios = json.load(f)
        return list(all_scenarios.keys())
    except (json.JSONDecodeError, OSError):
        return []


# ============================================================================
# Simulation Template Loading
# ============================================================================

def list_templates() -> List[str]:
    """
    List all available simulation template IDs.

    Returns:
        List of template IDs (short names like 'board_meeting')

    Example:
        templates = list_templates()
        # ['board_meeting', 'jefferson_dinner', 'vc_pitch_pearl', ...]

    Note:
        This function now delegates to TemplateLoader for the new
        JSON-based template system. Template IDs from the catalog
        (e.g., 'showcase/board_meeting') are returned as short names
        (e.g., 'board_meeting') for backward compatibility.
    """
    try:
        from generation.templates.loader import get_loader
        loader = get_loader()
        # Return short names for backward compatibility
        return [info.id.split("/")[-1] for info in loader.list_templates()]
    except ImportError:
        # Fallback to legacy behavior if loader not available
        templates_dir = Path(__file__).parent / "templates"
        if not templates_dir.exists():
            return []
        return [p.stem for p in templates_dir.glob("*.json") if p.is_file()]


def load_template(template_id: str) -> Dict[str, Any]:
    """
    Load a simulation template from JSON.

    Args:
        template_id: The template identifier (e.g., "board_meeting" or "showcase/board_meeting")

    Returns:
        Dictionary containing the full template data

    Raises:
        FileNotFoundError: If template doesn't exist
        ValueError: If template JSON is invalid

    Example:
        template = load_template("board_meeting")
        config = SimulationConfig(**template)

    Note:
        This function now delegates to TemplateLoader for the new
        JSON-based template system. Supports both short names (e.g., 'board_meeting')
        and full paths (e.g., 'showcase/board_meeting').
    """
    try:
        from generation.templates.loader import get_loader
        loader = get_loader()

        # Try full path first
        try:
            config = loader.load_template(template_id)
            return config.model_dump()
        except FileNotFoundError:
            pass

        # Try to find by short name
        for info in loader.list_templates():
            if info.id.split("/")[-1] == template_id:
                config = loader.load_template(info.id)
                return config.model_dump()

        # Not found in catalog
        raise FileNotFoundError(f"Template '{template_id}' not found in catalog")

    except ImportError:
        # Fallback to legacy behavior if loader not available
        templates_dir = Path(__file__).parent / "templates"
        template_path = templates_dir / f"{template_id}.json"

        if not template_path.exists():
            available = list_templates()
            raise FileNotFoundError(
                f"Template '{template_id}' not found. Available: {available}"
            )

        try:
            with open(template_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in template '{template_id}': {e}")


class ResolutionLevel(str, Enum):
    """Entity resolution levels"""
    TENSOR_ONLY = "tensor_only"
    SCENE = "scene"
    GRAPH = "graph"
    DIALOG = "dialog"
    TRAINED = "trained"
    FULL_DETAIL = "full_detail"


class TemporalMode(str, Enum):
    """Temporal causality modes"""
    PEARL = "pearl"
    DIRECTORIAL = "directorial"
    NONLINEAR = "nonlinear"
    BRANCHING = "branching"
    CYCLICAL = "cyclical"
    PORTAL = "portal"  # Backward inference from fixed endpoint to origin


# ============================================================================
# M1+M17: Fidelity Template Library
# ============================================================================

FIDELITY_TEMPLATES = {
    "minimalist": {
        "description": "Minimal token usage for fast exploration",
        "pattern": [ResolutionLevel.TENSOR_ONLY] * 10 +
                   [ResolutionLevel.SCENE] * 3 +
                   [ResolutionLevel.DIALOG],
        "token_estimate": 5000,
        "cost_estimate_usd": 0.01,
        "use_case": "Fast exploration, budget-constrained runs, testing",
        "quality_level": "Basic",
        "recommended_for": ["quick", "testing", "budget_constrained"]
    },
    "balanced": {
        "description": "Good quality/cost ratio for production runs",
        "pattern": [ResolutionLevel.TENSOR_ONLY] * 5 +
                   [ResolutionLevel.SCENE] * 5 +
                   [ResolutionLevel.GRAPH] * 3 +
                   [ResolutionLevel.DIALOG] * 2,
        "token_estimate": 15000,
        "cost_estimate_usd": 0.03,
        "use_case": "Production runs, general purpose, good quality",
        "quality_level": "Good",
        "recommended_for": ["production", "general", "default"]
    },
    "dramatic": {
        "description": "DIRECTORIAL mode focused on narrative climax",
        "pattern": [ResolutionLevel.TENSOR_ONLY] * 8 +
                   [ResolutionLevel.SCENE] * 4 +
                   [ResolutionLevel.DIALOG] * 2 +
                   [ResolutionLevel.TRAINED],
        "token_estimate": 25000,
        "cost_estimate_usd": 0.05,
        "use_case": "DIRECTORIAL mode, narrative-focused simulations",
        "quality_level": "High",
        "recommended_for": ["directorial", "narrative", "story_focused"]
    },
    "max_quality": {
        "description": "Maximum fidelity, no budget constraints",
        "pattern": [ResolutionLevel.DIALOG] * 10 +
                   [ResolutionLevel.TRAINED] * 5,
        "token_estimate": 350000,
        "cost_estimate_usd": 0.70,
        "use_case": "Research, publication-quality runs, maximum realism",
        "quality_level": "Maximum",
        "recommended_for": ["research", "publication", "max_quality"]
    },
    "portal_pivots": {
        "description": "PORTAL mode with adaptive pivot detection",
        "pattern": "adaptive",  # Special: engine determines pivots dynamically
        "token_estimate": 20000,
        "cost_estimate_usd": 0.04,
        "use_case": "PORTAL mode, pivot point focus, blended fidelity",
        "quality_level": "High",
        "recommended_for": ["portal", "backward_simulation", "pivot_focused"],
        "allocation_strategy": {
            "endpoint": ResolutionLevel.TRAINED,
            "origin": ResolutionLevel.TRAINED,
            "pivots": ResolutionLevel.DIALOG,
            "bridges": ResolutionLevel.SCENE,
            "checkpoints": ResolutionLevel.TENSOR_ONLY
        }
    }
}


class EntityConfig(BaseModel):
    """Configuration for entity generation"""
    count: int = Field(ge=1, le=1000, description="Number of entities to generate")
    types: List[str] = Field(default=["human"], description="Entity types to include")
    initial_resolution: ResolutionLevel = Field(
        default=ResolutionLevel.TENSOR_ONLY,
        description="Starting resolution level for entities"
    )
    animism_level: int = Field(
        ge=0, le=6, default=0,
        description="Animistic entity inclusion level (0=humans only, 6=all types)"
    )

    # SynthasAIzer controls (optional, backward compatible)
    envelope: Optional[EnvelopeConfig] = Field(
        default=None,
        description="ADSR envelope for entity presence lifecycle (None = flat intensity)"
    )
    default_voice: Optional[VoiceConfig] = Field(
        default=None,
        description="Default voice controls for entities (None = full participation)"
    )

    def get_envelope(self) -> EnvelopeConfig:
        """Get envelope config, falling back to default if not set."""
        return self.envelope or DEFAULT_ENVELOPE

    def get_default_voice(self) -> VoiceConfig:
        """Get default voice config, falling back to default if not set."""
        return self.default_voice or DEFAULT_VOICE

    @field_validator('types')
    @classmethod
    def validate_entity_types(cls, v):
        valid_types = {"human", "animal", "building", "object", "abstract", "ai", "any", "kami"}
        if not all(t in valid_types for t in v):
            raise ValueError(f"Invalid entity type. Must be one of: {valid_types}")
        return v


class CompanyConfig(BaseModel):
    """Configuration for timepoint structure"""
    count: int = Field(ge=1, le=1000, default=1, description="Number of timepoints to generate")
    start_time: Optional[datetime] = Field(
        default=None,
        description="Start time for simulation (defaults to now)"
    )
    resolution: str = Field(
        default="hour",
        description="Temporal resolution: year, month, day, hour, minute"
    )
    before_count: int = Field(
        ge=0, le=200, default=0,
        description="Number of timepoints to generate before critical moment"
    )
    after_count: int = Field(
        ge=0, le=200, default=0,
        description="Number of timepoints to generate after critical moment"
    )

    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v):
        valid_resolutions = {"year", "quarter", "month", "day", "hour", "minute", "second"}
        if v not in valid_resolutions:
            raise ValueError(f"Invalid resolution. Must be one of: {valid_resolutions}")
        return v


class TemporalConfig(BaseModel):
    """Configuration for temporal causality mode"""
    mode: TemporalMode = Field(
        default=TemporalMode.PEARL,
        description="Temporal causality mode"
    )
    # Directorial mode settings
    narrative_arc: Optional[str] = Field(
        default=None,
        description="Narrative arc for directorial mode: rising_action, climax, falling_action"
    )
    dramatic_tension: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Dramatic tension level for directorial mode"
    )
    # Cyclical mode settings
    cycle_length: Optional[int] = Field(
        default=None,
        description="Cycle length for cyclical mode"
    )
    prophecy_accuracy: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Prophecy accuracy for cyclical mode"
    )
    # Branching mode settings
    enable_counterfactuals: bool = Field(
        default=False,
        description="Enable counterfactual branch generation"
    )

    # Portal mode settings (backward inference from endpoint to origin)
    portal_description: Optional[str] = Field(
        default=None,
        description="Description of the endpoint state (e.g., 'John Doe elected President 2040')"
    )
    portal_year: Optional[int] = Field(
        default=None,
        description="Year of the portal/endpoint state"
    )
    origin_year: Optional[int] = Field(
        default=None,
        description="Year of the origin/starting state (e.g., 2025)"
    )
    backward_steps: int = Field(
        ge=1, le=100, default=15,
        description="Number of intermediate steps between origin and portal"
    )
    exploration_mode: str = Field(
        default="adaptive",
        description="Exploration strategy: 'reverse_chronological', 'oscillating', 'random', 'adaptive'"
    )
    oscillation_complexity_threshold: int = Field(
        default=10,
        description="If backward_steps > threshold, use oscillating strategy"
    )
    candidate_antecedents_per_step: int = Field(
        ge=1, le=50, default=10,
        description="How many candidate previous states to generate per step"
    )
    path_count: int = Field(
        ge=1, le=100, default=5,
        description="Number of complete paths to find and rank"
    )
    preserve_all_paths: bool = Field(
        default=True,
        description="Keep ALL generated paths for exploration (not just top N). Enables divergence analysis."
    )
    coherence_threshold: float = Field(
        ge=0.0, le=1.0, default=0.7,
        description="Minimum coherence score for valid path"
    )
    checkpoint_interval: int = Field(
        ge=1, default=3,
        description="Retrain entity tensors every N years"
    )
    llm_scoring_weight: float = Field(
        ge=0.0, le=1.0, default=0.3,
        description="Weight for LLM-based plausibility scoring"
    )
    historical_precedent_weight: float = Field(
        ge=0.0, le=1.0, default=0.2,
        description="Weight for historical precedent scoring"
    )
    causal_necessity_weight: float = Field(
        ge=0.0, le=1.0, default=0.3,
        description="Weight for causal necessity scoring"
    )
    entity_capability_weight: float = Field(
        ge=0.0, le=1.0, default=0.2,
        description="Weight for entity capability scoring"
    )
    max_backtrack_depth: int = Field(
        ge=0, le=10, default=3,
        description="How many steps to backtrack before pruning path"
    )
    portal_relaxation_enabled: bool = Field(
        default=True,
        description="Allow relaxing portal/endpoint if no coherent paths found"
    )

    # Simulation-based judging settings (M17 PORTAL enhancement)
    use_simulation_judging: bool = Field(
        default=False,
        description="Enable simulation-based evaluation instead of static scoring"
    )
    simulation_forward_steps: int = Field(
        ge=1, le=10, default=2,
        description="How many forward steps to simulate per candidate antecedent"
    )
    simulation_max_entities: int = Field(
        ge=1, le=50, default=5,
        description="Limit number of entities tracked in mini-simulations for performance"
    )
    simulation_include_dialog: bool = Field(
        default=True,
        description="Generate dialog in mini-simulations for realism assessment"
    )
    judge_model: Optional[str] = Field(
        default="meta-llama/llama-3.1-405b-instruct",
        description="LLM model to use for judging simulation realism"
    )
    judge_temperature: float = Field(
        ge=0.0, le=2.0, default=0.3,
        description="Temperature for judge LLM (lower = more consistent)"
    )
    simulation_cache_results: bool = Field(
        default=True,
        description="Cache simulation results to avoid redundant computation"
    )
    simulation_timeout_seconds: int = Field(
        ge=30, le=600, default=180,
        description="Overall timeout for each mini-simulation in seconds (default 3 minutes)"
    )
    simulation_step_timeout_seconds: int = Field(
        ge=10, le=120, default=60,
        description="Timeout for each forward step within a mini-simulation (default 1 minute)"
    )

    # Parallelization settings for simulation-based judging (speed optimization)
    max_simulation_workers: int = Field(
        ge=1, le=10, default=4,
        description="Max parallel mini-simulations per scoring round (higher = faster but more API load)"
    )
    max_antecedent_workers: int = Field(
        ge=1, le=6, default=3,
        description="Max parallel state processing in backward exploration"
    )
    fast_simulation_model: Optional[str] = Field(
        default=None,
        description="Use cheaper/faster model for mini-sims (None = use default model)"
    )

    # M1+M17: Adaptive Fidelity-Temporal Strategy Configuration
    fidelity_planning_mode: FidelityPlanningMode = Field(
        default=FidelityPlanningMode.HYBRID,
        description="How should fidelity be allocated? programmatic | adaptive | hybrid"
    )
    token_budget_mode: TokenBudgetMode = Field(
        default=TokenBudgetMode.SOFT_GUIDANCE,
        description="How should token budget be enforced? hard | soft | max | adaptive | orchestrator | user"
    )
    token_budget: Optional[float] = Field(
        default=15000,
        description="Total token budget for simulation (if budget_mode requires it)"
    )
    fidelity_template: str = Field(
        default="balanced",
        description="Fidelity template: minimalist | balanced | dramatic | max_quality | portal_pivots"
    )
    custom_fidelity_schedule: Optional[List[ResolutionLevel]] = Field(
        default=None,
        description="Custom fidelity schedule (overrides template)"
    )
    custom_temporal_steps: Optional[List[int]] = Field(
        default=None,
        description="Custom temporal steps in months (overrides template)"
    )

    @model_validator(mode='after')
    def apply_fast_simjudged_overrides(self) -> 'TemporalConfig':
        """Apply fast-simjudged environment variable overrides for speed optimization."""
        import os

        if os.environ.get("TIMEPOINT_FAST_SIMJUDGED") == "1":
            # Override simulation settings for faster execution
            if os.environ.get("TIMEPOINT_CANDIDATE_ANTECEDENTS"):
                self.candidate_antecedents_per_step = int(os.environ["TIMEPOINT_CANDIDATE_ANTECEDENTS"])

            if os.environ.get("TIMEPOINT_SIMULATION_FORWARD_STEPS"):
                self.simulation_forward_steps = int(os.environ["TIMEPOINT_SIMULATION_FORWARD_STEPS"])

            if os.environ.get("TIMEPOINT_SIMULATION_INCLUDE_DIALOG"):
                self.simulation_include_dialog = os.environ["TIMEPOINT_SIMULATION_INCLUDE_DIALOG"].lower() != "false"

            if os.environ.get("TIMEPOINT_MAX_SIMULATION_WORKERS"):
                self.max_simulation_workers = int(os.environ["TIMEPOINT_MAX_SIMULATION_WORKERS"])

        return self


class OutputConfig(BaseModel):
    """Configuration for output generation"""
    formats: List[str] = Field(
        default=["json"],
        description="Output formats: json, jsonl, csv, markdown, sqlite"
    )
    include_dialogs: bool = Field(
        default=True,
        description="Generate dialog synthesis"
    )
    include_relationships: bool = Field(
        default=True,
        description="Track relationship evolution"
    )
    include_knowledge_flow: bool = Field(
        default=True,
        description="Track knowledge propagation"
    )
    export_ml_dataset: bool = Field(
        default=False,
        description="Export in ML training format (JSONL)"
    )

    # Narrative export configuration
    generate_narrative_exports: bool = Field(
        default=True,
        description="Generate comprehensive narrative summaries (MD/JSON/PDF)"
    )
    narrative_export_formats: List[str] = Field(
        default=["markdown", "json", "pdf"],
        description="Formats to generate: markdown, json, pdf"
    )
    narrative_detail_level: str = Field(
        default="summary",
        description="Detail level: minimal, summary, comprehensive"
    )
    enhance_narrative_with_llm: bool = Field(
        default=True,
        description="Use LLM to enhance executive summary (adds ~$0.003/run)"
    )

    @field_validator('formats')
    @classmethod
    def validate_formats(cls, v):
        valid_formats = {"json", "jsonl", "csv", "markdown", "sqlite", "html"}
        if not all(f in valid_formats for f in v):
            raise ValueError(f"Invalid format. Must be one of: {valid_formats}")
        return v

    @field_validator('narrative_export_formats')
    @classmethod
    def validate_narrative_formats(cls, v):
        valid = {"markdown", "json", "pdf"}
        if not all(f in valid for f in v):
            raise ValueError(f"Invalid narrative format. Must be one of: {valid}")
        return v

    @field_validator('narrative_detail_level')
    @classmethod
    def validate_detail_level(cls, v):
        valid = {"minimal", "summary", "comprehensive"}
        if v not in valid:
            raise ValueError(f"Invalid detail level. Must be one of: {valid}")
        return v


class VariationConfig(BaseModel):
    """Configuration for horizontal variation generation"""
    enabled: bool = Field(
        default=False,
        description="Enable variation generation"
    )
    count: int = Field(
        ge=1, le=1000, default=1,
        description="Number of variations to generate"
    )
    strategies: List[str] = Field(
        default=["vary_personalities"],
        description="Variation strategies to apply"
    )
    deduplication_threshold: float = Field(
        ge=0.0, le=1.0, default=0.9,
        description="Similarity threshold for deduplication (1.0 = identical)"
    )

    @field_validator('strategies')
    @classmethod
    def validate_strategies(cls, v):
        valid_strategies = {
            "vary_personalities",
            "vary_starting_conditions",
            "vary_outcomes",
            "vary_relationships",
            "vary_knowledge"
        }
        if not all(s in valid_strategies for s in v):
            raise ValueError(f"Invalid strategy. Must be one of: {valid_strategies}")
        return v


class ConvergenceConfig(BaseModel):
    """
    Configuration for causal graph convergence evaluation.

    Measures agreement in causal graphs across independent runs.
    High convergence indicates robust causal mechanisms.
    """
    enabled: bool = Field(
        default=False,
        description="Enable convergence evaluation"
    )
    run_count: int = Field(
        ge=2, le=10, default=3,
        description="Number of independent runs to compare"
    )
    models: List[str] = Field(
        default_factory=lambda: ["deepseek/deepseek-chat", "meta-llama/llama-3.1-70b-instruct"],
        description="Different models to use for independent runs (for model-diverse convergence)"
    )
    seeds: List[int] = Field(
        default_factory=lambda: [42, 123, 456],
        description="Random seeds for independent runs"
    )
    min_acceptable_score: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Minimum convergence score to consider results robust"
    )
    store_divergence_points: bool = Field(
        default=True,
        description="Store detailed divergence analysis"
    )


class SimulationConfig(BaseModel):
    """
    Complete simulation configuration with validation.

    This is the root configuration object that defines all aspects
    of a simulation generation job.

    Example:
        config = SimulationConfig(
            scenario_description="Simulate the Constitutional Convention of 1787",
            world_id="constitutional_convention",
            entities=EntityConfig(count=10, types=["human"]),
            timepoints=CompanyConfig(count=5, resolution="day"),
            temporal=TemporalConfig(mode=TemporalMode.PEARL),
            outputs=OutputConfig(formats=["json", "markdown"])
        )
    """
    # Core identification
    scenario_description: str = Field(
        description="Natural language description of scenario to simulate"
    )
    world_id: str = Field(
        description="Unique identifier for this simulation world"
    )

    # Component configurations
    entities: EntityConfig = Field(
        default_factory=lambda: EntityConfig(),
        description="Entity generation configuration"
    )
    timepoints: CompanyConfig = Field(
        default_factory=lambda: CompanyConfig(),
        description="Company structure configuration"
    )
    temporal: TemporalConfig = Field(
        default_factory=lambda: TemporalConfig(),
        description="Temporal causality configuration"
    )
    outputs: OutputConfig = Field(
        default_factory=lambda: OutputConfig(),
        description="Output generation configuration"
    )
    variations: VariationConfig = Field(
        default_factory=lambda: VariationConfig(),
        description="Variation generation configuration"
    )

    # Optional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for this simulation"
    )

    # Company Corporate Analysis - Profile System
    economic_scenario: Optional[str] = Field(
        default=None,
        description="Economic scenario ID for corporate simulations (e.g., 'bull_market_2025')"
    )
    founder_profiles: Optional[List[str]] = Field(
        default=None,
        description="List of founder archetype IDs for corporate simulations (e.g., ['charismatic_visionary', 'operational_executor'])"
    )

    # Execution settings
    max_cost_usd: Optional[float] = Field(
        default=None,
        description="Maximum cost in USD (None = unlimited)"
    )
    enable_checkpoints: bool = Field(
        default=True,
        description="Enable checkpoint/resume functionality"
    )
    checkpoint_interval: int = Field(
        ge=1, default=10,
        description="Save checkpoint every N entities/timepoints"
    )

    # Convergence evaluation settings
    convergence: ConvergenceConfig = Field(
        default_factory=lambda: ConvergenceConfig(),
        description="Convergence evaluation configuration"
    )

    @model_validator(mode='after')
    def validate_config_coherence(self):
        """Validate that configuration is internally coherent"""
        # If variations are enabled, we need at least one strategy
        if self.variations.enabled and not self.variations.strategies:
            raise ValueError("Variation generation requires at least one strategy")

        # Temporal expansion requires at least one timepoint
        if (self.timepoints.before_count + self.timepoints.after_count) > 0:
            if self.timepoints.count < 1:
                raise ValueError("Temporal expansion requires at least one base timepoint")

        # Directorial mode requires narrative arc
        if self.temporal.mode == TemporalMode.DIRECTORIAL and not self.temporal.narrative_arc:
            self.temporal.narrative_arc = "rising_action"  # Set default

        # Cyclical mode requires cycle length
        if self.temporal.mode == TemporalMode.CYCLICAL and not self.temporal.cycle_length:
            self.temporal.cycle_length = self.timepoints.count  # Set default

        return self

    @classmethod
    def from_template(cls, template_id: str) -> "SimulationConfig":
        """
        Load a SimulationConfig from a JSON template file.

        Args:
            template_id: The template identifier (e.g., "board_meeting")

        Returns:
            SimulationConfig instance populated from the template

        Raises:
            FileNotFoundError: If template doesn't exist
            ValueError: If template JSON is invalid or fails validation

        Example:
            # Load a template
            config = SimulationConfig.from_template("board_meeting")

            # List available templates
            from generation.config_schema import list_templates
            available = list_templates()
            # ['board_meeting', 'jefferson_dinner', 'vc_pitch_pearl', ...]
        """
        template_data = load_template(template_id)
        return cls(**template_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationConfig":
        """Create from dictionary"""
        return cls(**data)

    def estimate_cost(self) -> Dict[str, float]:
        """
        Estimate generation cost based on configuration.

        Returns:
            Dictionary with cost estimates:
                - min_usd: Minimum expected cost
                - max_usd: Maximum expected cost
                - tokens_estimated: Estimated token count
        """
        # Rough cost estimation based on entity count and resolution
        entity_count = self.entities.count
        timepoint_count = self.timepoints.count + self.timepoints.before_count + self.timepoints.after_count

        # Base tokens per entity-timepoint pair
        resolution_tokens = {
            ResolutionLevel.TENSOR_ONLY: 200,
            ResolutionLevel.SCENE: 2000,
            ResolutionLevel.GRAPH: 5000,
            ResolutionLevel.DIALOG: 10000,
            ResolutionLevel.TRAINED: 50000,
            ResolutionLevel.FULL_DETAIL: 50000
        }

        base_tokens = resolution_tokens.get(self.entities.initial_resolution, 10000)
        total_tokens = entity_count * timepoint_count * base_tokens

        # Apply variation multiplier
        if self.variations.enabled:
            total_tokens *= self.variations.count

        # Cost per million tokens (rough estimate)
        cost_per_m_tokens = 10.0  # $10 per million tokens

        min_cost = (total_tokens * 0.5 * cost_per_m_tokens) / 1_000_000
        max_cost = (total_tokens * 1.5 * cost_per_m_tokens) / 1_000_000

        return {
            "min_usd": round(min_cost, 2),
            "max_usd": round(max_cost, 2),
            "tokens_estimated": total_tokens
        }
