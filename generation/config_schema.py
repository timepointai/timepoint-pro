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

    @field_validator('formats')
    @classmethod
    def validate_formats(cls, v):
        valid_formats = {"json", "jsonl", "csv", "markdown", "sqlite", "html"}
        if not all(f in valid_formats for f in v):
            raise ValueError(f"Invalid format. Must be one of: {valid_formats}")
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
    def example_board_meeting(cls) -> "SimulationConfig":
        """Example configuration for a board meeting scenario"""
        return cls(
            scenario_description="Simulate a tech startup board meeting where CEO proposes an acquisition",
            world_id="board_meeting_example",
            entities=EntityConfig(count=5, types=["human"]),
            timepoints=CompanyConfig(count=3, resolution="hour"),
            temporal=TemporalConfig(mode=TemporalMode.PEARL),
            outputs=OutputConfig(
                formats=["json", "markdown"],
                include_dialogs=True,
                include_relationships=True
            )
        )

    @classmethod
    def example_jefferson_dinner(cls) -> "SimulationConfig":
        """Example configuration for the Jefferson Dinner scenario"""
        return cls(
            scenario_description="Simulate the 1790 Compromise Dinner between Jefferson, Hamilton, and Madison",
            world_id="jefferson_dinner",
            entities=EntityConfig(count=3, types=["human"]),
            timepoints=CompanyConfig(
                count=1,
                before_count=2,
                after_count=2,
                resolution="hour"
            ),
            temporal=TemporalConfig(mode=TemporalMode.PEARL),
            outputs=OutputConfig(
                formats=["json", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True
            )
        )

    @classmethod
    def example_variations(cls) -> "SimulationConfig":
        """Example configuration for generating variations"""
        return cls(
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

    @classmethod
    def example_scarlet_study_deep(cls) -> "SimulationConfig":
        """
        Deep temporal investigation case demonstrating all 17 mechanisms.

        The Scarlet Study: A detective, doctor, and criminal mastermind navigate
        a complex murder investigation across 101 timepoints. Showcases:
        - M1-M5: Heterogeneous fidelity, progressive training, exposure tracking
        - M6-M8: TTM tensors, causal chains, embodied states
        - M9-M11: On-demand entities, scene atmosphere, dialog synthesis
        - M12-M13: Counterfactual branches, relationship evolution
        - M14-M17: Circadian patterns, prospection, animism, modal causality

        Use this for character-based fine-tuning data generation.
        """
        return cls(
            scenario_description=(
                "A brilliant but physically deteriorating detective (irregular sleep, stimulant use) "
                "investigates a locked-room murder with his doctor companion. The victim, a diplomat, "
                "was found with mysterious scarlet markings. Track the investigation from initial crime "
                "scene discovery through 100+ timepoints of deduction, laboratory analysis, witness "
                "interrogation, and final confrontation. The detective's deductive patterns improve "
                "across timepoints (M2: progressive training), physical constraints affect cognition "
                "(M8: embodied states), and knowledge accumulates through exposure events (M3). "
                "London itself acts as an informant entity (M16: animism), atmosphere shifts with "
                "revelations (M10: scene entities), and the detective models the criminal's next moves "
                "(M15: prospection). Multiple resolution levels (M1): detective at TRAINED, doctor at "
                "DIALOG, witnesses at SCENE, crowd at TENSOR."
            ),
            world_id="scarlet_study_deep",
            entities=EntityConfig(
                count=5,
                types=["human", "building", "abstract"],
                initial_resolution=ResolutionLevel.SCENE,
                animism_level=3  # Include buildings (221B Baker Street) and abstract concepts (London fog)
            ),
            timepoints=CompanyConfig(
                count=1,  # Critical moment: revelation of the killer's identity
                before_count=50,  # 50 timepoints of investigation leading up
                after_count=50,  # 50 timepoints of aftermath, trial, reflection
                resolution="hour"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PEARL,  # Standard causality - clues must be observed before deduction
                enable_counterfactuals=True  # M12: "What if detective missed this clue?"
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,  # M11: Detective-doctor exchanges, interrogations
                include_relationships=True,  # M13: Trust evolution, rivalry dynamics
                include_knowledge_flow=True,  # M3: Exposure event tracking
                export_ml_dataset=True  # Character roleplay training data
            ),
            metadata={
                "character_focus": "detective",
                "mechanisms_featured": [
                    "M1_heterogeneous_fidelity",
                    "M2_progressive_training",
                    "M3_exposure_events",
                    "M4_physics_validation",
                    "M5_query_resolution",
                    "M6_ttm_tensors",
                    "M7_causal_chains",
                    "M8_embodied_states",
                    "M9_on_demand_generation",
                    "M10_scene_entities",
                    "M11_dialog_synthesis",
                    "M12_counterfactual_branching",
                    "M13_multi_entity_synthesis",
                    "M14_circadian_patterns",
                    "M15_entity_prospection",
                    "M16_animistic_entities",
                    "M17_modal_causality"
                ],
                "character_ttm_tensors": {
                    "detective": ["observation_acuity", "deductive_chains", "pattern_recognition", "stimulant_dependency"],
                    "doctor": ["medical_knowledge", "empathy_vector", "narrative_coherence", "fatigue_accumulation"],
                    "criminal": ["strategic_planning", "manipulation_skill", "risk_assessment", "desperation_level"]
                },
                "temporal_depth": 101,
                "expected_training_examples": 500  # 5 entities × 100 transitions
            }
        )

    @classmethod
    def example_empty_house_flashback(cls) -> "SimulationConfig":
        """
        Nonlinear narrative demonstrating flashback structure and survival story.

        The Empty House: A detective returns from apparent death, revealing how
        they survived a fatal confrontation through nonlinear flashbacks. Demonstrates
        M17: Modal Causality (NONLINEAR mode) where presentation order ≠ causal order.
        """
        return cls(
            scenario_description=(
                "Three years after the detective's apparent death at Reichenbach Falls, they suddenly "
                "reappear in London. The narrative unfolds nonlinearly: present-day investigation of a "
                "new murder intercut with flashbacks revealing survival techniques, hidden allies, and "
                "the criminal network dismantled in secret. Track through 81 timepoints as past and "
                "present converge. Emphasizes M17 (nonlinear causality), M13 (relationship evolution "
                "across temporal gaps), M8 (physical trauma and recovery), and M15 (prospection: planning "
                "the return while in hiding)."
            ),
            world_id="empty_house_flashback",
            entities=EntityConfig(
                count=4,
                types=["human", "building"],
                initial_resolution=ResolutionLevel.DIALOG,
                animism_level=2  # Camden House (the empty house) as entity
            ),
            timepoints=CompanyConfig(
                count=1,  # Critical moment: detective reveals survival
                before_count=40,  # Flashbacks to survival period
                after_count=40,  # Present-day investigation
                resolution="day"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.NONLINEAR,  # M17: Presentation order ≠ causal order
                enable_counterfactuals=False
            ),
            outputs=OutputConfig(
                formats=["jsonl", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "character_focus": "detective",
                "narrative_structure": "nonlinear_flashback",
                "mechanisms_featured": [
                    "M17_modal_causality_nonlinear",
                    "M13_relationship_evolution",
                    "M8_embodied_trauma_recovery",
                    "M15_long_term_prospection",
                    "M3_knowledge_gaps",
                    "M11_emotional_reunion_dialogs"
                ],
                "temporal_depth": 81,
                "expected_training_examples": 320  # 4 entities × 80 transitions
            }
        )

    @classmethod
    def example_final_problem_branching(cls) -> "SimulationConfig":
        """
        Branching timeline demonstrating counterfactual reasoning and many-worlds.

        The Final Problem: Detective confronts criminal mastermind at Reichenbach Falls.
        Multiple timeline branches explore: (1) detective survives, (2) detective dies,
        (3) both survive and form uneasy alliance, (4) third party intervention.
        Demonstrates M12: Counterfactual Branching and M17: BRANCHING mode causality.
        """
        return cls(
            scenario_description=(
                "The detective and criminal mastermind meet at Reichenbach Falls for their final confrontation. "
                "This scenario branches into multiple timelines based on critical decision points: does the "
                "detective accept the criminal's offer to join forces? Does a third party intervene? Does "
                "the doctor arrive in time? Each branch propagates causally forward, creating distinct "
                "futures. Track 61 timepoints across 4 major branches, with M12 (counterfactual branching), "
                "M15 (prospection: both characters modeling each other's strategies), M8 (physical exhaustion "
                "affecting decisions), and M17 (branching mode causality)."
            ),
            world_id="final_problem_branching",
            entities=EntityConfig(
                count=4,
                types=["human", "abstract"],
                initial_resolution=ResolutionLevel.TRAINED,  # High fidelity for strategic modeling
                animism_level=3  # Fate/destiny as abstract entity influencing outcomes
            ),
            timepoints=CompanyConfig(
                count=1,  # Critical branching moment: the confrontation
                before_count=30,  # Lead-up: travel to Switzerland, preparations, final letters
                after_count=30,  # Aftermath across multiple branches
                resolution="minute"  # High temporal resolution for tense confrontation
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # M17: Many-worlds causality
                enable_counterfactuals=True  # M12: Explicit counterfactual modeling
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,  # Crucial philosophical debate between detective and criminal
                include_relationships=True,  # Rivalry at peak intensity
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "character_focus": ["detective", "criminal"],
                "branch_count": 4,
                "mechanisms_featured": [
                    "M12_counterfactual_branching",
                    "M17_modal_causality_branching",
                    "M15_strategic_prospection",
                    "M8_extreme_stress_embodiment",
                    "M11_philosophical_dialog",
                    "M13_rivalry_culmination",
                    "M3_final_knowledge_exchange"
                ],
                "temporal_depth": 61,
                "expected_training_examples": 240,  # 4 entities × 60 transitions
                "branching_points": [
                    "t030_initial_offer",
                    "t045_physical_struggle",
                    "t055_third_party_arrival",
                    "t060_final_decision"
                ]
            }
        )

    @classmethod
    def example_hound_shadow_directorial(cls) -> "SimulationConfig":
        """
        Directorial narrative demonstrating narrative arc and dramatic tension.

        The Hound's Shadow: A detective noir where narrative structure drives
        causality. The story follows a rising action → climax → falling action arc,
        with dramatic tension building mechanically. Demonstrates M17: DIRECTORIAL mode
        where causality serves narrative structure.
        """
        return cls(
            scenario_description=(
                "A detective investigates a series of murders on the fog-shrouded moors, each victim "
                "bearing strange hound bite marks. The narrative follows classical dramatic structure: "
                "rising action (discovery and investigation), climax (confrontation with the supernatural "
                "hound), falling action (revelation and resolution). Unlike Pearl causality, events occur "
                "to serve narrative beats—the detective finds crucial clues at dramatically appropriate "
                "moments, the hound appears when tension peaks. Track 15 timepoints with M17 (directorial "
                "causality), M10 (moor atmosphere as narrative force), M14 (night/fog affecting visibility "
                "and mood), M11 (dramatic dialog revelations), and M8 (fear affecting cognition)."
            ),
            world_id="hound_shadow_directorial",
            entities=EntityConfig(
                count=5,
                types=["human", "animal", "building"],
                initial_resolution=ResolutionLevel.DIALOG,
                animism_level=4  # Moor, hound, Baskerville Hall as active forces
            ),
            timepoints=CompanyConfig(
                count=15,
                resolution="hour"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.DIRECTORIAL,
                narrative_arc="rising_action",  # Will progress to climax, falling_action
                dramatic_tension=0.7  # High tension noir atmosphere
            ),
            outputs=OutputConfig(
                formats=["jsonl", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "character_focus": "detective",
                "narrative_structure": "classical_three_act",
                "mechanisms_featured": [
                    "M17_modal_causality_directorial",
                    "M10_atmospheric_entities",
                    "M14_circadian_fog_patterns",
                    "M11_dramatic_dialog",
                    "M8_fear_embodiment",
                    "M16_animistic_moor",
                    "M13_relationship_tension",
                    "M15_dread_prospection"
                ],
                "temporal_depth": 15,
                "expected_training_examples": 70,  # 5 entities × 14 transitions
                "narrative_beats": [
                    "t01_arrival_on_moor",
                    "t05_first_hound_sighting",
                    "t08_rising_dread",
                    "t11_climax_confrontation",
                    "t15_resolution"
                ]
            }
        )

    @classmethod
    def example_sign_loops_cyclical(cls) -> "SimulationConfig":
        """
        Cyclical narrative demonstrating time loops and prophecy mechanics.

        The Sign of Four Loops: A detective trapped in a recursive investigation
        where outcomes loop back to influence causes. Each cycle, the detective
        gains knowledge that affects the "previous" iteration. Demonstrates M17:
        CYCLICAL mode with prophecy accuracy determining loop variation.
        """
        return cls(
            scenario_description=(
                "A detective investigates a murder tied to a mysterious pact made years ago. But the "
                "investigation loops: every time the detective solves the case, they find themselves back "
                "at the beginning with residual memories (déjà vu). Each cycle, prophecies made in the "
                "current iteration affect past events in the next loop. Track 12 timepoints across 3 "
                "complete cycles (4 events each), with M17 (cyclical causality), M15 (prospection becomes "
                "prophecy), M3 (knowledge persists across loops), M8 (temporal disorientation affecting "
                "cognition), and M14 (repeating circadian patterns with variations)."
            ),
            world_id="sign_loops_cyclical",
            entities=EntityConfig(
                count=4,
                types=["human", "abstract"],
                initial_resolution=ResolutionLevel.TRAINED,  # High fidelity for complex temporal reasoning
                animism_level=5  # Time itself as entity, fate, prophecy
            ),
            timepoints=CompanyConfig(
                count=12,  # 3 loops × 4 events each
                resolution="day"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.CYCLICAL,
                cycle_length=4,  # Each loop is 4 timepoints
                prophecy_accuracy=0.8  # High accuracy—prophecies mostly come true
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "character_focus": "detective",
                "narrative_structure": "recursive_loop",
                "mechanisms_featured": [
                    "M17_modal_causality_cyclical",
                    "M15_prophecy_prospection",
                    "M3_cross_loop_knowledge",
                    "M8_temporal_disorientation",
                    "M14_repeating_patterns",
                    "M16_time_as_entity",
                    "M13_relationship_permutations",
                    "M7_causal_loops"
                ],
                "temporal_depth": 12,
                "expected_training_examples": 44,  # 4 entities × 11 transitions
                "loop_count": 3,
                "prophecies": [
                    "loop1_prophecy_affects_loop2",
                    "loop2_prophecy_affects_loop3",
                    "loop3_prophecy_affects_loop1"
                ]
            }
        )

    @classmethod
    def example_hospital_crisis(cls) -> "SimulationConfig":
        """
        Emergency room crisis demonstrating embodied states and circadian patterns.

        Hospital Night Shift Crisis: Track an ER physician and injured patient through
        a critical night shift (22:00-06:00). Demonstrates M8 (Embodied States) via
        pain/illness affecting cognition, and M14 (Circadian Patterns) via fatigue
        accumulation and reduced cognitive function during night hours.
        """
        return cls(
            scenario_description=(
                "Emergency room during night shift. Dr. Elena Martinez, an experienced ER physician "
                "suffering from chronic back pain and accumulated shift fatigue, treats Michael Chen, "
                "a car accident victim with severe injuries (high pain, developing infection). Track "
                "through 3 timepoints across critical night hours (22:00, 02:00, 06:00). M8 tracks "
                "how pain_level > 0.7 and fever > 38.5°C couple body states to cognitive processing. "
                "M14 tracks how night hours (energy_penalty multiplier) and fatigue accumulation affect "
                "decision quality and reaction time. High-stakes medical decisions under physical duress."
            ),
            world_id="hospital_crisis",
            entities=EntityConfig(
                count=2,
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,  # High detail for body-mind coupling
                animism_level=0  # Focus on human embodiment
            ),
            timepoints=CompanyConfig(
                count=3,  # 22:00, 02:00, 06:00 - circadian transitions
                resolution="hour"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PEARL  # Standard causality
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "mechanisms_featured": [
                    "M8_embodied_states_pain_illness",
                    "M14_circadian_night_shift_fatigue"
                ],
                "embodied_constraints": {
                    "dr_martinez": {"pain_level": 0.3, "fatigue": 0.7, "age": 42},
                    "patient_chen": {"pain_level": 0.9, "fever": 39.2, "consciousness": 0.4}
                },
                "circadian_config": {
                    "timepoints": ["22:00", "02:00", "06:00"],
                    "fatigue_multipliers": [1.3, 1.7, 1.5],  # Peak fatigue at 02:00
                    "activity_type": "high_stress_medical"
                }
            }
        )

    @classmethod
    def example_kami_shrine(cls) -> "SimulationConfig":
        """
        Animistic shrine ritual demonstrating non-human entity agency.

        Kami Shrine Ritual: A traditional Japanese shrine where all things possess spirit (kami).
        The shrine building, fox deity, and messenger animal all have rich internal states.
        Demonstrates M16 (Animistic Entities) with animism_level=6, treating buildings,
        spirits, and animals as full entities with consciousness, memory, and agency.
        """
        return cls(
            scenario_description=(
                "A pilgrim visits Fushimi Inari Shrine for guidance. The shrine building itself "
                "(centuries-old wood structure) has consciousness and memory of countless visitors. "
                "Inari Okami, the fox deity, manifests to offer wisdom. A white fox messenger "
                "observes and communicates. All three non-human entities have rich internal states: "
                "the shrine remembers prayers, the deity processes worshiper intent, the fox evaluates "
                "sincerity. Demonstrates M16 with full animistic entity modeling—consciousness vectors, "
                "spiritual power metrics, and non-verbal communication patterns for buildings, spirits, "
                "and animals."
            ),
            world_id="kami_shrine",
            entities=EntityConfig(
                count=4,  # pilgrim + shrine + deity + fox
                types=["human", "building", "kami", "animal"],
                initial_resolution=ResolutionLevel.TRAINED,
                animism_level=6  # Maximum animism - all types have full agency
            ),
            timepoints=CompanyConfig(
                count=1,  # Single ritual moment
                resolution="minute"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PEARL
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,  # Non-verbal "dialog" between entities
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "mechanisms_featured": [
                    "M16_animistic_entities_full_spectrum"
                ],
                "animistic_entities": {
                    "shrine_building": {"consciousness": 0.7, "memory_depth": "centuries", "spiritual_power": 0.9},
                    "inari_okami": {"consciousness": 1.0, "domain": "rice_prosperity_foxes", "manifestation_strength": 0.95},
                    "white_fox": {"consciousness": 0.8, "can_speak": True, "divine_messenger": True}
                },
                "animism_level_description": "Full animism (level 6): buildings, spirits, animals all possess consciousness and agency"
            }
        )

    @classmethod
    def example_detective_prospection(cls) -> "SimulationConfig":
        """
        Detective prospection demonstrating future state modeling.

        Detective's Deduction: Holmes explicitly models Moriarty's future actions across
        24-hour time horizon. Demonstrates M15 (Entity Prospection) where one entity
        generates detailed predictions of another entity's future states, plans, and
        decision branches. Prospection accuracy depends on theory-of-mind capability.
        """
        return cls(
            scenario_description=(
                "Sherlock Holmes has 24 hours to predict where criminal mastermind Moriarty will "
                "strike next. Holmes explicitly models Moriarty's planning process: generates "
                "prospective states for multiple time horizons (6h, 12h, 24h), considers Moriarty's "
                "resource constraints, anticipates decision branches, and evaluates contingency plans. "
                "Demonstrates M15 where Holmes's cognitive_tensor includes prospection_ability=0.95 "
                "and theory_of_mind=0.9. System generates detailed ProspectiveState objects: "
                "expected knowledge Moriarty will have, likely emotional states, predicted action "
                "sequences, and anxiety levels about being predicted."
            ),
            world_id="detective_prospection",
            entities=EntityConfig(
                count=2,  # Holmes + Moriarty
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,  # High detail for cognitive modeling
                animism_level=3  # Mild animism for London city as informant
            ),
            timepoints=CompanyConfig(
                count=2,  # Present + 24h prospective future
                resolution="hour"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PEARL
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "mechanisms_featured": [
                    "M15_entity_prospection_strategic"
                ],
                "prospection_config": {
                    "modeling_entity": "sherlock_holmes",
                    "target_entity": "moriarty",
                    "time_horizons": ["6h", "12h", "24h"],
                    "prospection_ability": 0.95,
                    "theory_of_mind": 0.9
                },
                "cognitive_traits": {
                    "sherlock_holmes": {"prospection_ability": 0.95, "theory_of_mind": 0.9, "pattern_recognition": 0.98},
                    "moriarty": {"strategic_planning": 0.96, "deception_skill": 0.92, "counter_modeling": 0.88}
                }
            }
        )

    @classmethod
    def example_constitutional_convention_day1(cls) -> "SimulationConfig":
        """
        Constitutional Convention Day 1 - Large-scale stress test demonstrating all mechanisms.

        May 25, 1787: The Constitutional Convention opens at Independence Hall, Philadelphia.
        28 entities (25 Founding Fathers + 3 animistic entities) across 500 timepoints
        (minute-level resolution) spanning 8 hours of deliberation. This massive simulation
        exercises 16/17 mechanisms and generates vast training data for character roleplay.

        Key Features:
        - 500 timepoints = ultra-high temporal resolution (1 per minute)
        - 25 historical figures with dense relationship networks (8-10 connections each)
        - Animistic entities: Independence Hall, "Confederation", "Union"
        - Progressive elevation: Key figures (Washington, Madison, Franklin) → TRAINED
        - Rich dialogs: Debates, private conversations, faction negotiations
        - Embodied constraints: Franklin's gout (age 81), circadian fatigue patterns
        - Knowledge propagation: Ideas flow between state delegations and factions
        - Estimated cost: $500-1,000 USD | Training data: 14,000+ entity-timepoint states

        Historical Context:
        - Quorum just achieved (7 states represented)
        - Washington unanimously elected presiding officer
        - Rules of procedure established
        - Secrecy rule imposed (closed doors)
        - Initial debates on Virginia Plan vs federal reform
        - Factional tensions: Large states vs Small states, North vs South
        """
        return cls(
            scenario_description=(
                "May 25, 1787, Pennsylvania State House (Independence Hall), Philadelphia. "
                "The Constitutional Convention officially opens after weeks of delayed arrivals. "
                "As delegates gather in the Assembly Room at 10:00 AM, the weight of history "
                "presses upon them. The Articles of Confederation have failed—the young nation "
                "teeters on collapse. Seven state delegations have achieved quorum. "
                "\n\n"
                "George Washington of Virginia arrives, reluctant but resolved. James Madison, "
                "the architect, clutches his notes on government theory. Benjamin Franklin at 81, "
                "suffering from gout, is carried in on a sedan chair. Alexander Hamilton advocates "
                "for a strong national government. State delegations cluster: Virginia's five "
                "delegates (Washington, Madison, Mason, Randolph, Blair) caucus near the windows. "
                "Pennsylvania's contingent (Franklin, Gouverneur Morris, James Wilson, Robert Morris) "
                "commands the center. Small state delegates from Delaware (Dickinson, Read, Bassett, "
                "Bedford) eye the Virginians warily, fearing domination by large states. "
                "\n\n"
                "By noon, Washington is unanimously elected president of the Convention. Rules "
                "are debated: secrecy (to allow candid discussion), voting by state (one vote per "
                "delegation), quorum requirements. The room atmosphere shifts—formal at first, "
                "growing tense as philosophical differences emerge. The ancient walls of Independence "
                "Hall seem to listen, having witnessed the Declaration eleven years prior. "
                "\n\n"
                "Track 500 timepoints from 10:00 AM to 6:00 PM (minute-level resolution): "
                "Roll call and credentialing (10:00-10:45), election of president (10:45-11:30), "
                "rules debate (11:30-1:00 PM), lunch recess with private faction negotiations "
                "(1:00-2:00 PM), Edmund Randolph introduces Virginia Plan outline (2:00-4:00 PM), "
                "initial reactions and adjournment debate (4:00-6:00 PM). "
                "\n\n"
                "Physical constraints matter: Franklin's pain level increases across the day "
                "(gout flare-ups), delegates' energy depletes (circadian patterns from morning "
                "alertness to evening exhaustion), room temperature rises (no air conditioning, "
                "windows closed for secrecy). Knowledge propagates: Madison's Virginia Plan ideas "
                "spread through exposure events (who heard what, when?), small state delegates "
                "coordinate defensive strategies, Hamilton's nationalist arguments influence "
                "fence-sitters. "
                "\n\n"
                "Relationships evolve: Madison-Hamilton alliance strengthens, Mason grows skeptical "
                "of centralization (foreshadowing his refusal to sign), Gerry's contrarian tendencies "
                "emerge, Sherman's Connecticut compromise thinking begins to form. The abstract "
                "entities shift: 'Confederation' (the failing system) weakens as delegates lose "
                "faith, 'Union' (the aspiration) strengthens as consensus builds, Independence Hall "
                "itself accumulates historical weight. "
                "\n\n"
                "This is history compressed to minute-level resolution—every whispered conversation, "
                "every facial expression during votes, every moment of doubt or inspiration. This "
                "is Company AI at maximum capacity: 28 entities, 500 timepoints, 16 mechanisms, "
                "14,000 training examples, $500-1,000 cost, and the future of a nation hanging in "
                "the balance."
            ),
            world_id="constitutional_convention_day1",
            entities=EntityConfig(
                count=28,  # 25 Founding Fathers + 3 animistic entities
                types=["human", "building", "abstract"],
                initial_resolution=ResolutionLevel.SCENE,  # Start at SCENE, elevate key figures to TRAINED
                animism_level=3  # Buildings (Independence Hall) and abstract concepts (Confederation, Union)
            ),
            timepoints=CompanyConfig(
                count=500,  # 500 timepoints across 8 hours = ~1 per minute
                resolution="minute"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PEARL,  # Strict historical causality
                enable_counterfactuals=False  # Single timeline only
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,  # Rich debates and conversations
                include_relationships=True,  # Dense relationship networks
                include_knowledge_flow=True,  # Idea propagation tracking
                export_ml_dataset=True  # Character roleplay training data
            ),
            metadata={
                "simulation_type": "large_scale_stress_test",
                "historical_event": "Constitutional Convention Opening Day",
                "date": "1787-05-25",
                "location": "Pennsylvania State House (Independence Hall), Philadelphia",
                "duration_hours": 8,
                "time_range": "10:00 AM - 6:00 PM",
                "temporal_resolution": "minute_level",
                "estimated_cost_usd": 750.0,
                "estimated_training_examples": 14000,
                "mechanisms_featured": [
                    "M1_heterogeneous_fidelity",  # Key figures at TRAINED, others at SCENE
                    "M2_progressive_training",  # 500 timepoints of evolution
                    "M3_exposure_events",  # Knowledge propagation between delegates
                    "M4_physics_validation",  # Franklin's gout, energy budgets, physical constraints
                    "M5_query_resolution",  # Lazy elevation for critical moments
                    "M6_ttm_tensors",  # Compress all 28 entities
                    "M7_causal_chains",  # Strict temporal ordering
                    "M8_embodied_states",  # Franklin's pain, circadian fatigue
                    "M9_on_demand_generation",  # Clerks, doorkeepers, servants as needed
                    "M10_scene_entities",  # Room atmosphere, tension, formality
                    "M11_dialog_synthesis",  # Rich debates, private conversations
                    # M12_counterfactual_branching - NOT USED (single timeline)
                    "M13_multi_entity_synthesis",  # Complex relationship evolution
                    "M14_circadian_patterns",  # Morning energy → evening fatigue
                    "M15_entity_prospection",  # Delegates model future government
                    "M16_animistic_entities",  # Independence Hall, Confederation, Union
                    "M17_modal_causality_pearl"  # Historical realism via strict DAG
                ],
                "founding_fathers": [
                    {"name": "George Washington", "state": "Virginia", "role": "presiding_officer", "age": 55, "key_trait": "leadership_gravitas"},
                    {"name": "James Madison", "state": "Virginia", "role": "architect", "age": 36, "key_trait": "theoretical_brilliance"},
                    {"name": "Benjamin Franklin", "state": "Pennsylvania", "role": "elder_statesman", "age": 81, "key_trait": "diplomatic_wisdom", "physical": "severe_gout"},
                    {"name": "Alexander Hamilton", "state": "New York", "role": "nationalist", "age": 30, "key_trait": "passionate_advocacy"},
                    {"name": "Gouverneur Morris", "state": "Pennsylvania", "role": "writer", "age": 35, "key_trait": "eloquent_rhetoric"},
                    {"name": "James Wilson", "state": "Pennsylvania", "role": "legal_scholar", "age": 45, "key_trait": "jurisprudence"},
                    {"name": "George Mason", "state": "Virginia", "role": "rights_advocate", "age": 62, "key_trait": "individual_liberty"},
                    {"name": "Edmund Randolph", "state": "Virginia", "role": "virginia_plan_presenter", "age": 34, "key_trait": "political_strategy"},
                    {"name": "Roger Sherman", "state": "Connecticut", "role": "pragmatist", "age": 66, "key_trait": "practical_compromise"},
                    {"name": "Robert Morris", "state": "Pennsylvania", "role": "financier", "age": 53, "key_trait": "economic_expertise"},
                    {"name": "John Rutledge", "state": "South Carolina", "role": "committee_chair", "age": 48, "key_trait": "procedural_mastery"},
                    {"name": "Charles Pinckney", "state": "South Carolina", "role": "young_voice", "age": 29, "key_trait": "ambitious_innovation"},
                    {"name": "Elbridge Gerry", "state": "Massachusetts", "role": "skeptic", "age": 43, "key_trait": "contrarian_independence"},
                    {"name": "Rufus King", "state": "Massachusetts", "role": "federalist", "age": 32, "key_trait": "strong_nationalism"},
                    {"name": "William Paterson", "state": "New Jersey", "role": "small_state_advocate", "age": 42, "key_trait": "state_equality_defender"},
                    {"name": "John Dickinson", "state": "Delaware", "role": "penman", "age": 55, "key_trait": "constitutional_drafting"},
                    {"name": "George Read", "state": "Delaware", "role": "delegate", "age": 54, "key_trait": "careful_deliberation"},
                    {"name": "Richard Bassett", "state": "Delaware", "role": "delegate", "age": 42, "key_trait": "moderate_voice"},
                    {"name": "Gunning Bedford Jr.", "state": "Delaware", "role": "firebrand", "age": 40, "key_trait": "passionate_small_state_defense"},
                    {"name": "John Blair", "state": "Virginia", "role": "jurist", "age": 55, "key_trait": "judicial_temperament"},
                    {"name": "Hugh Williamson", "state": "North Carolina", "role": "scientist", "age": 52, "key_trait": "empirical_thinking"},
                    {"name": "William Blount", "state": "North Carolina", "role": "land_speculator", "age": 38, "key_trait": "western_expansion_focus"},
                    {"name": "Richard Dobbs Spaight", "state": "North Carolina", "role": "delegate", "age": 30, "key_trait": "southern_interests"},
                    {"name": "Pierce Butler", "state": "South Carolina", "role": "aristocrat", "age": 43, "key_trait": "property_rights_defender"},
                    {"name": "Charles Cotesworth Pinckney", "state": "South Carolina", "role": "military_hero", "age": 41, "key_trait": "martial_honor"}
                ],
                "animistic_entities": {
                    "independence_hall": {"name": "Independence Hall", "type": "building", "age_years": 44, "consciousness": 0.8, "memory": "witnessed_declaration_1776"},
                    "confederation": {"name": "Confederation", "type": "abstract", "concept": "articles_of_confederation", "strength": 0.2, "status": "failing"},
                    "union": {"name": "Union", "type": "abstract", "concept": "unified_nation", "strength": 0.4, "status": "aspiration"}
                },
                "factions": {
                    "large_states": ["Virginia", "Pennsylvania", "Massachusetts"],
                    "small_states": ["Delaware", "New Jersey", "Connecticut"],
                    "southern_states": ["Virginia", "North Carolina", "South Carolina"],
                    "northern_states": ["Massachusetts", "New York", "Pennsylvania", "Connecticut", "New Jersey"]
                },
                "key_relationships": {
                    "madison_hamilton": "alliance_forming_federalism",
                    "franklin_washington": "mutual_respect_elder_to_leader",
                    "madison_mason": "virginia_delegation_tension_centralization",
                    "small_vs_large_states": "structural_conflict_representation",
                    "north_vs_south": "sectional_tension_slavery_commerce"
                },
                "timeline_structure": [
                    {"timepoint_range": "0-45", "phase": "roll_call_credentialing", "activity": "establishing_quorum"},
                    {"timepoint_range": "45-90", "phase": "elect_president", "activity": "washington_unanimous_election"},
                    {"timepoint_range": "90-180", "phase": "rules_debate", "activity": "secrecy_voting_procedures"},
                    {"timepoint_range": "180-240", "phase": "lunch_recess", "activity": "private_faction_negotiations"},
                    {"timepoint_range": "240-400", "phase": "virginia_plan_introduction", "activity": "randolph_presents_outline"},
                    {"timepoint_range": "400-500", "phase": "initial_reactions", "activity": "delegate_responses_adjournment"}
                ],
                "embodied_constraints": {
                    "franklin": {
                        "age": 81,
                        "health_conditions": ["severe_gout", "bladder_stones"],
                        "mobility": 0.3,
                        "pain_progression": "increases_with_sitting_duration",
                        "special_accommodation": "sedan_chair_transport"
                    },
                    "circadian_effects": {
                        "morning_10am_12pm": {"energy": 1.0, "alertness": 0.95, "mood": "optimistic"},
                        "afternoon_12pm_3pm": {"energy": 0.8, "alertness": 0.85, "mood": "focused"},
                        "late_afternoon_3pm_5pm": {"energy": 0.6, "alertness": 0.75, "mood": "fatigued"},
                        "evening_5pm_6pm": {"energy": 0.4, "alertness": 0.65, "mood": "exhausted"}
                    }
                },
                "knowledge_propagation": {
                    "virginia_plan_spread": "madison_to_virginia_delegation_to_other_states",
                    "small_state_coordination": "delaware_nj_delegations_defensive_strategy",
                    "federalist_ideas": "hamilton_influences_key_delegates"
                }
            },
            max_cost_usd=1000.0,  # User acknowledges scale
            enable_checkpoints=True,  # Critical for long simulation
            checkpoint_interval=50  # Save every 50 timepoints
        )

    @classmethod
    def example_vc_pitch_pearl(cls) -> "SimulationConfig":
        """
        Linear VC pitch demonstrating standard causality and negotiation dynamics.

        Company Startup Pitch: CEO and COO pitch Company to Sand Hill Road VC.
        Standard pitch progression: intro → product demo → traction → competitive moat → ask.
        VC challenges on market timing, technical risk, go-to-market strategy. Demonstrates
        M7 (causal chains), M11 (dialog synthesis), M15 (VC prospection - modeling startup risk).
        """
        return cls(
            scenario_description=(
                "Pre-seed pitch meeting at prominent Silicon Valley VC firm. Founder A (CEO, former "
                "Stanford AI researcher) and Founder B (COO, ex-OpenAI product lead) pitch "
                "Company: a temporal knowledge graph system enabling 95% cost reduction "
                "for AI training data generation through adaptive fidelity and modal causality. "
                "\n\n"
                "The pitch deck emphasizes: (1) Problem: LLM training data costs $500K-5M per dataset, "
                "(2) Solution: Company generates queryable temporal simulations with tensor compression "
                "achieving 200 tokens vs 50K tokens, (3) Traction: 3 design partners testing (game studio, "
                "VR company, education tech), (4) Market: $25B AI training data market growing 40% YoY, "
                "(5) Team: Founder A published 12 papers on temporal reasoning, Founder B scaled OpenAI's data "
                "pipeline to 10M users, (6) Ask: $2M pre-seed at $12M cap for 12 months runway. "
                "\n\n"
                "Jennifer Park (VC Partner, enterprise AI focused) leads the meeting with associate "
                "David Kim. Jennifer immediately probes: 'Why now? OpenAI and Anthropic generate their "
                "own training data.' Founder A pivots to horizontal applications: character AI, simulation "
                "games, educational content. Jennifer counters: 'What's your moat against big labs?' "
                "Founder B highlights the 17 mechanisms (animistic entities, modal causality, prospection) "
                "as defensible IP. David asks about unit economics: 'If customers pay $5K/dataset and "
                "your cost is $250, that's 95% margin but low ACV—how do you scale?' Founder A explains "
                "vertical expansion strategy. "
                "\n\n"
                "Track 5 timepoints: (1) Pitch opening + product demo, (2) Traction deep-dive, "
                "(3) Competitive moat discussion, (4) Business model questions, (5) Closing ask and "
                "next steps. Demonstrates M11 (rich negotiation dialog), M15 (VC prospection: Jennifer "
                "models probability of Series A success), M7 (causal chains: traction → credibility → "
                "valuation leverage), and M13 (relationship evolution: skepticism → cautious interest)."
            ),
            world_id="vc_pitch_pearl",
            entities=EntityConfig(
                count=4,  # CEO + COO + VC Partner + VC Associate
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG,  # High detail for pitch dynamics
                animism_level=0  # Pure human negotiation
            ),
            timepoints=CompanyConfig(
                count=5,  # Standard pitch flow: intro, traction, moat, business, ask
                resolution="minute"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PEARL  # Linear causality
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,  # Key mechanism: negotiation dialog
                include_relationships=True,  # Founder-VC trust evolution
                export_ml_dataset=True  # Training data for pitch conversations
            ),
            metadata={
                "pitch_type": "pre_seed",
                "ask_amount_usd": 2000000,
                "pre_money_valuation_usd": 10000000,
                "mechanisms_featured": [
                    "M7_causal_chains_pitch_flow",
                    "M11_dialog_synthesis_negotiation",
                    "M15_prospection_vc_risk_modeling",
                    "M13_relationship_evolution"
                ],
                "pitch_deck_highlights": {
                    "problem": "LLM training data costs $500K-5M per dataset",
                    "solution": "95% cost reduction via adaptive fidelity + tensor compression",
                    "traction": "3 design partners (game studio, VR, edtech)",
                    "market_size_usd": 25000000000,
                    "team": "Founder A (Stanford AI PhD, 12 papers), Founder B (ex-OpenAI)",
                    "runway_months": 12
                },
                "vc_concerns": [
                    "market_timing_why_now",
                    "competitive_moat_vs_big_labs",
                    "unit_economics_low_acv",
                    "technical_risk_17_mechanisms",
                    "go_to_market_strategy"
                ]
            }
        )

    @classmethod
    def example_vc_pitch_roadshow(cls) -> "SimulationConfig":
        """
        Multi-meeting pitch sequence demonstrating narrative evolution across audiences.

        Company Pitch Roadshow: Founders pitch to 3 different VCs (LA entertainment, SF enterprise, SF consumer)
        adapting narrative by audience. LA VC hears content generation story, SF enterprise hears
        vertical SaaS story, SF consumer hears developer tools story. Demonstrates M3 (knowledge
        propagation), M7 (causal chains), M10 (scene atmosphere), M13 (multi-entity synthesis).
        """
        return cls(
            scenario_description=(
                "Three-day pitch roadshow across California. Monday in Los Angeles: founders meet "
                "Alex Martinez at Maverick Ventures (entertainment tech focused). Founder A emphasizes "
                "Company's content generation capabilities: 'Game studios spend $2M on dialog trees. "
                "We generate branching narratives with modal causality for $100K.' Alex is intrigued "
                "by the animistic entities (M16) for NPC AI in games. "
                "\n\n"
                "Wednesday in San Francisco: first meeting with Jennifer Park at Sequoia (enterprise "
                "AI focused). Founder B leads: 'Enterprises need synthetic training data for proprietary "
                "LLMs. We enable vertical fine-tuning datasets at 95% cost reduction.' Jennifer asks "
                "about SOC2, enterprise SLAs, and sales cycle. Founder A explains ANDOS layer-by-layer "
                "training for deterministic outputs enterprises require. "
                "\n\n"
                "Thursday in San Francisco: meeting with David Chen at a16z (developer tools focused). "
                "Technical deep-dive: Founder A walks through the 17 mechanisms, query engine, fault tolerance. "
                "David gets excited about the developer experience: 'This is Terraform for simulation.' "
                "Founders realize they found the right positioning. "
                "\n\n"
                "Track 7 timepoints: (1) LA pitch with Alex, (2) Travel to SF / debrief, (3) Sequoia "
                "pitch with Jennifer, (4) Post-meeting founder discussion on positioning, (5) a16z pitch "
                "with David, (6) Founder synthesis: which narrative resonated?, (7) Follow-up strategy. "
                "Demonstrates M3 (knowledge accumulation: each meeting informs the next), M13 (multi-entity "
                "synthesis: three VCs with different thesis lenses), M10 (scene atmospheres: LA creative "
                "vs SF analytical), M7 (causal chains: positioning evolution across meetings)."
            ),
            world_id="vc_pitch_roadshow",
            entities=EntityConfig(
                count=5,  # CEO + COO + LA_VC + SF_Enterprise_VC + SF_Developer_VC
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=7,  # 3 meetings + transitions + synthesis
                resolution="hour"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PEARL  # Sequential meetings with learning
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,  # Key: track narrative evolution
                export_ml_dataset=True
            ),
            metadata={
                "pitch_type": "roadshow_pre_seed",
                "vc_firms": [
                    {"name": "Maverick Ventures", "location": "LA", "focus": "entertainment_tech", "partner": "Alex Martinez"},
                    {"name": "Sequoia Capital", "location": "SF", "focus": "enterprise_ai", "partner": "Jennifer Park"},
                    {"name": "Andreessen Horowitz", "location": "SF", "focus": "developer_tools", "partner": "David Chen"}
                ],
                "narrative_evolution": {
                    "la_angle": "content_generation_for_games",
                    "sf_enterprise_angle": "vertical_saas_training_data",
                    "sf_developer_angle": "terraform_for_simulation"
                },
                "mechanisms_featured": [
                    "M3_knowledge_propagation_across_meetings",
                    "M7_causal_chains_learning_curve",
                    "M10_scene_atmosphere_la_vs_sf",
                    "M11_dialog_synthesis_pitch_variations",
                    "M13_multi_entity_synthesis_vc_perspectives"
                ],
                "key_insight": "Developer tools positioning resonated most (David @ a16z)"
            }
        )

    @classmethod
    def example_vc_pitch_branching(cls) -> "SimulationConfig":
        """
        Branching pitch outcomes demonstrating counterfactual negotiation paths.

        Company Pitch Branching: Critical moment when VC asks 'What's your traction?' Branches
        into 4 timelines: (A) Strong answer → term sheet, (B) Weak answer → pass, (C) Honest answer →
        strategic pivot, (D) Competitor announces funding → FOMO term sheet. Demonstrates M12
        (counterfactual branching), M15 (both sides modeling outcomes), M8 (founder stress), M17 (BRANCHING mode).
        """
        return cls(
            scenario_description=(
                "High-stakes pitch meeting at tier-1 VC. Founder A and Founder B have 45 minutes "
                "to convince Jennifer Park (Partner) and David Kim (Associate) to invest $2M in Company. "
                "The pitch goes well until minute 30, when Jennifer leans forward and asks the critical question: "
                "'Your tech is impressive, but I need to see traction. What's your MRR?' "
                "\n\n"
                "This is the branching point. The timeline splits into 4 distinct futures: "
                "\n\n"
                "**Branch A (Strong Traction)**: Founder A confidently answers '$50K MRR across 5 enterprise "
                "customers, 300% month-over-month growth.' Jennifer's eyes light up. She asks about unit "
                "economics, customer concentration, retention. Founder A has the data. David pulls up the model: "
                "'If they maintain this growth, they hit $1M ARR in 6 months.' Jennifer offers a term sheet "
                "on the spot: $2M at $15M post. They close in 2 weeks. "
                "\n\n"
                "**Branch B (Weak Traction)**: Founder A hesitates. 'We're pre-revenue, focused on product-market "
                "fit.' Jennifer's body language shifts. 'So no paying customers?' Founder B tries to recover: "
                "'We have 20 beta users giving feedback.' Jennifer: 'Call us when you have $10K MRR. Too early "
                "for us.' The meeting ends cordially but the deal is dead. They leave with polite rejection. "
                "\n\n"
                "**Branch C (Honest Pivot)**: Founder A takes a breath. 'We have 3 pilots generating qualitative "
                "feedback but no revenue yet. However, what we learned is fascinating...' She pivots to the "
                "design partner insights: game studios want NPC AI, VR companies want scenario generation. "
                "Jennifer appreciates the honesty and strategic thinking. 'This sounds more like a developer "
                "platform than vertical SaaS. Have you considered positioning as Stripe for simulations?' This "
                "opens a new strategic conversation. Jennifer offers $1.5M at $10M post with milestone-based "
                "second tranche. They negotiate for 3 weeks. "
                "\n\n"
                "**Branch D (Competitive FOMO)**: As Founder A starts to answer, David's phone buzzes. He glances "
                "down, then whispers to Jennifer. She reads: 'Competitor just raised $10M Series A from Sequoia "
                "for similar simulation tech.' Jennifer's entire demeanor changes. Suddenly the question isn't "
                "'Should we invest?' but 'How do we move fast enough to win this deal?' She offers $2.5M at "
                "$15M post, 'take it or leave it in 48 hours.' The founders feel the power dynamic invert. "
                "\n\n"
                "Track 12 timepoints: 3 before critical question + 1 branching moment + 8 after (2 per branch). "
                "Demonstrates M12 (counterfactual branching: 4 distinct futures from one decision), M15 "
                "(prospection: both sides modeling outcomes), M8 (embodied stress: Founder A's heart rate, Founder B's "
                "sweating affecting pitch performance), M17 (BRANCHING mode causality), M11 (dialog variations "
                "across branches)."
            ),
            world_id="vc_pitch_branching",
            entities=EntityConfig(
                count=5,  # CEO + COO + VC_Partner + VC_Associate + Market_Timing (abstract entity)
                types=["human", "abstract"],
                initial_resolution=ResolutionLevel.TRAINED,  # High detail for strategic modeling
                animism_level=2  # Market timing as abstract entity representing competitive pressure
            ),
            timepoints=CompanyConfig(
                count=1,  # Critical branching moment: traction question
                before_count=3,  # Pitch setup
                after_count=8,  # 2 timepoints per branch (4 branches)
                resolution="minute"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # M17: Many-worlds causality
                enable_counterfactuals=True  # M12: Explicit counterfactual modeling
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "pitch_type": "branching_outcomes",
                "critical_question": "What is your traction / MRR?",
                "branches": [
                    {
                        "id": "branch_a_strong",
                        "answer": "$50K MRR, 300% MoM growth",
                        "outcome": "term_sheet_$2M_at_$15M_post",
                        "probability": 0.15,
                        "close_time_weeks": 2
                    },
                    {
                        "id": "branch_b_weak",
                        "answer": "Pre-revenue, 20 beta users",
                        "outcome": "polite_pass_too_early",
                        "probability": 0.40,
                        "close_time_weeks": 0
                    },
                    {
                        "id": "branch_c_honest_pivot",
                        "answer": "3 pilots, pivoting to developer platform",
                        "outcome": "term_sheet_$1.5M_at_$10M_post_with_milestones",
                        "probability": 0.30,
                        "close_time_weeks": 3
                    },
                    {
                        "id": "branch_d_competitive_fomo",
                        "answer": "Mid-answer, competitor raises $10M",
                        "outcome": "aggressive_term_sheet_$2.5M_at_$15M_post_48h_expiry",
                        "probability": 0.15,
                        "close_time_weeks": 1
                    }
                ],
                "mechanisms_featured": [
                    "M12_counterfactual_branching_negotiation",
                    "M15_prospection_both_sides_modeling",
                    "M8_embodied_stress_pitch_performance",
                    "M17_modal_causality_branching",
                    "M11_dialog_variations_across_branches",
                    "M13_relationship_outcomes_trust_vs_fomo"
                ],
                "stress_markers": {
                    "sarah_ceo": {"heart_rate": 110, "cortisol_level": "elevated", "decision_quality_modifier": 0.85},
                    "marcus_coo": {"perspiration": "visible", "voice_steadiness": 0.75}
                }
            }
        )

    @classmethod
    def example_vc_pitch_strategies(cls) -> "SimulationConfig":
        """
        Alternate pitch strategies demonstrating how framing affects outcomes.

        Company Pitch Strategies: Same VC meeting, different founder strategies across parallel timelines.
        Timeline A: Technical pitch (ML/AI innovation), Timeline B: Business pitch (market/ROI),
        Timeline C: Vision pitch (category creation). Demonstrates M12 (alternate histories),
        M10 (scene analysis), M15 (VC judgment evaluation), M17 (directorial comparison).
        """
        return cls(
            scenario_description=(
                "Parallel timelines exploring pitch strategy selection. In each timeline, Founder A "
                "(CEO) and Founder B (COO) pitch Company to Jennifer Park (VC Partner) and "
                "David Kim (Associate), but their strategic framing varies dramatically: "
                "\n\n"
                "**Timeline A (Technical Pitch)**: Founder A leads with the architecture. 'We've solved a "
                "fundamental problem in AI: tensor compression for temporal knowledge graphs. Our TTM "
                "mechanism achieves 97% compression ratio—50,000 tokens down to 200—while preserving "
                "queryability. No one else has modal causality with BRANCHING and CYCLICAL modes.' She "
                "walks through the 17 mechanisms, ANDOS layer-by-layer training, fault tolerance architecture. "
                "David (technical associate) is impressed: 'This is legitimate research.' But Jennifer "
                "pushes back: 'I invest in businesses, not papers. Who pays for this?' The pitch feels "
                "academic. Jennifer is skeptical about commercial viability. "
                "\n\n"
                "**Timeline B (Business Pitch)**: Founder B leads with market size. 'AI training data is a "
                "$25B market growing 40% annually. Our customers—game studios, VR companies, edtech—spend "
                "$2M on content generation. We deliver the same outcome for $100K. That's 95% cost reduction "
                "with 20x margin. Unit economics: $5K ACV, $250 COGS, 24-month payback. We're targeting "
                "$10M ARR in 18 months.' He shows the Excel model. Jennifer loves the numbers: 'Now we're "
                "talking. What's your GTM motion?' They spend 30 minutes on sales strategy. Jennifer is "
                "excited about the business model but wants to see traction first. "
                "\n\n"
                "**Timeline C (Vision Pitch)**: Founder A paints the future. 'Every company will need temporal AI. "
                "Today, LLMs are stateless—they don't understand causality, time, or consequences. We're "
                "creating a new category: Temporal AI Infrastructure. Think of us as Snowflake for simulation, "
                "or Databricks for causal reasoning. In 5 years, every enterprise will run temporal simulations "
                "for planning, training, compliance. We're not just a tool; we're the foundation layer for the "
                "next generation of AI that understands *when* things happen and *why*.' Jennifer leans in: "
                "'That's a generational bet. Do you have the team to build category-defining infrastructure?' "
                "The pitch becomes about founder ambition and vision scale. "
                "\n\n"
                "Track 9 timepoints: 2 before pitch start + 1 pitch beginning + 6 divergent (2 per timeline). "
                "Demonstrates M12 (alternate histories: same meeting, different strategies), M10 (scene "
                "atmosphere analysis: technical vs business vs visionary mood), M15 (VC prospection: Jennifer "
                "evaluates founder judgment through strategy choice), M17 (directorial mode for dramatic "
                "comparison of outcomes)."
            ),
            world_id="vc_pitch_strategies",
            entities=EntityConfig(
                count=4,  # CEO + COO + VC_Partner + VC_Associate
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=1,  # Pitch strategy selection moment
                before_count=2,  # Meeting setup
                after_count=6,  # 2 timepoints per timeline (3 timelines)
                resolution="minute"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Parallel strategy timelines
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True  # Training data for strategic pitch framing
            ),
            metadata={
                "pitch_type": "strategy_comparison",
                "timelines": [
                    {
                        "id": "timeline_a_technical",
                        "lead": "sarah_ceo",
                        "focus": "ml_ai_innovation_17_mechanisms",
                        "vc_response": "impressed_technically_skeptical_commercially",
                        "outcome": "request_for_more_traction",
                        "probability_of_term_sheet": 0.25
                    },
                    {
                        "id": "timeline_b_business",
                        "lead": "marcus_coo",
                        "focus": "market_size_unit_economics_gtm",
                        "vc_response": "excited_about_numbers_wants_validation",
                        "outcome": "conditional_yes_pending_first_customers",
                        "probability_of_term_sheet": 0.65
                    },
                    {
                        "id": "timeline_c_vision",
                        "lead": "sarah_ceo",
                        "focus": "temporal_ai_category_creation",
                        "vc_response": "intrigued_by_ambition_evaluating_founder_caliber",
                        "outcome": "long_discussion_on_team_and_roadmap",
                        "probability_of_term_sheet": 0.45
                    }
                ],
                "mechanisms_featured": [
                    "M12_alternate_histories_strategy_selection",
                    "M10_scene_atmosphere_technical_vs_business_vs_vision",
                    "M11_dialog_synthesis_strategic_framing",
                    "M15_prospection_vc_evaluates_founder_judgment",
                    "M17_modal_causality_directorial_comparison"
                ],
                "strategic_insight": "Business pitch (timeline B) yields highest term sheet probability (65%)",
                "meta_lesson": "VCs invest in businesses, not technology or vision alone—need market validation"
            }
        )

    @classmethod
    def timepoint_ipo_reverse_engineering(cls) -> "SimulationConfig":
        """
        Reverse-engineer Company's IPO path: work backwards from 2028 $2B IPO to 2024 formation.

        Company IPO 2028: $2B valuation on NASDAQ. Reverse-engineer the corporate formation
        decisions that led here. Compare two co-founder structures: (A) CEO 55% / President 35%
        vs (B) CEO 50% / CTO 40%. Track backwards through Series C → B → A → Seed → Formation.
        Demonstrates M12 (branching histories), M15 (prospection in reverse), M7 (causal chains).
        """
        return cls(
            scenario_description=(
                "**November 2028: Company IPO Day** - Founder A (CEO) rings the NASDAQ opening bell. "
                "TempDB goes public at $2B valuation. 95% gross margin, $150M ARR, 40% YoY growth. "
                "Wall Street analysts call it 'the Bloomberg Terminal of AI simulation.' But how did they get here? "
                "\n\n"
                "**Reverse-engineer the journey backwards in time**: This simulation runs in reverse chronology, "
                "exploring how corporate formation decisions at each funding stage set up future success. Two parallel "
                "timelines branch from formation (October 2024): "
                "\n\n"
                "**Timeline A (CEO/President Structure)**: Founder A CEO 55%, Founder B President 35%, "
                "advisors/ESOP 10%. Standard 4-year vesting with 1-year cliff. At Seed (Feb 2025), they raise $2M "
                "at $10M post. Founder B as President handles operations, Founder A focuses on product and vision. By "
                "Series A (Dec 2025), revenue is $1M ARR—strong for 14 months—they raise $15M at $60M post. "
                "Founder B's operational excellence (GTM, sales systems) drives predictable growth. Series B (Oct 2026): "
                "$8M ARR, raise $50M at $250M post. Series C (June 2027): $40M ARR, raise $150M at $800M pre. "
                "IPO (Nov 2028): $150M ARR, $2B market cap. Founder A's equity dilutes to 32%, Founder B to 20%. Both "
                "paper billionaires. The President role gave Founder B enough authority to scale operations while "
                "preserving Founder A's CEO decision rights. "
                "\n\n"
                "**Timeline B (CEO/CTO Structure)**: Founder A CEO 50%, Founder B CTO 40%, advisors/ESOP 10%. "
                "Same vesting. At Seed (Feb 2025), they raise $1.5M at $8M post—slightly worse terms because "
                "investors worry about lack of dedicated commercial leader. Founder B as CTO is brilliant on product "
                "but Founder A has to handle both vision AND operations. By Series A (June 2026, 6 months later), "
                "revenue is only $500K ARR—slower GTM execution—they raise $12M at $40M post (lower valuation). "
                "Founder A is stretched thin. They hire a VP Sales who takes 2% equity. Series B (Aug 2027): $5M ARR, "
                "raise $40M at $180M post. Series C (Feb 2028): $25M ARR, raise $100M at $500M pre. IPO (May 2029, "
                "6 months delayed): $100M ARR, $1.2B market cap. Founder A's equity dilutes to 27%, Founder B to 22%. "
                "The CTO structure worked technically but lacked operational muscle in early stages, leading to "
                "slower growth and more dilution. "
                "\n\n"
                "Track 18 timepoints in reverse: IPO (t0) → Series C close (t-3) → Series C negotiations (t-6) → "
                "Series B close (t-9) → Series B negotiations (t-12) → Series A close (t-15) → Series A negotiations "
                "(t-18) → Seed close (t-21) → Formation & equity split decision (t-24). Each stage shows how "
                "earlier equity and role decisions compound. Demonstrates M12 (two timelines), M15 (founders in "
                "2028 looking back at decisions), M7 (causal chains: role → execution → valuation → dilution), "
                "M13 (relationship evolution), M11 (board negotiations at each stage)."
            ),
            world_id="timepoint_ipo_reverse",
            entities=EntityConfig(
                count=6,  # Founder A + Founder B + Seed VC + Series A VC + Series B VC + Series C VC
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=18,  # Reverse chronology through 6 funding stages × 3 timepoints each
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Two timelines: CEO/President vs CEO/CTO
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "reverse_engineering_ipo_path",
                "timelines": [
                    {
                        "id": "timeline_a_ceo_president",
                        "role_structure": "CEO + President (Operational Leader)",
                        "hypothesis": "President role provides operational muscle for faster scaling and better valuations"
                    },
                    {
                        "id": "timeline_b_ceo_cto",
                        "role_structure": "CEO + CTO (Technical Leader)",
                        "hypothesis": "CTO structure is technically strong but lacks operational focus, leading to slower GTM"
                    }
                ],
                "key_questions": [
                    "How do formation equity splits affect final ownership post-IPO?",
                    "What role structures enable faster operational scaling?",
                    "How does early-stage role clarity affect funding round valuations?",
                    "What dilution patterns emerge from CEO/President vs CEO/CTO structures?",
                    "How do operational vs technical leadership priorities affect ARR growth?"
                ],
                "mechanisms_featured": [
                    "M12_branching_role_structures",
                    "M15_reverse_prospection_from_ipo_to_formation",
                    "M7_causal_chains_equity_to_outcome",
                    "M13_cofounder_relationship_evolution",
                    "M11_board_negotiation_dialogs"
                ],
                "key_insight": "Role structure at formation compounds through funding rounds—operational leadership accelerates GTM",
                "equity_mechanics": {
                    "vesting": "4_year_1_year_cliff",
                    "acceleration": "single_trigger_on_ipo",
                    "esop_pool": "refreshed_at_each_round"
                },
                "emergent_format": True,
                "uses_profile_system": False,
                "reverse_chronology": True
            }
        )

    @classmethod
    def timepoint_acquisition_scenarios(cls) -> "SimulationConfig":
        """
        Compare acquisition outcomes: OpenAI $500M vs Anthropic $800M vs stay independent.

        Company Acquisition 2027: Three parallel timelines from same formation. Timeline A:
        OpenAI acquires for $500M cash (December 2026). Timeline B: Anthropic acquires for
        $800M cash+stock (June 2027). Timeline C: Stay independent, IPO for $2B (November 2028).
        Demonstrates M12 (branching), M15 (acquisition negotiations), M11 (strategic dialog).
        """
        return cls(
            scenario_description=(
                "**September 2026: The Offer Letter** - Founder A (CEO) and Founder B (President) "
                "receive three acquisition offers within 6 weeks. Company is at $10M ARR, growing 400% YoY, "
                "Series A funded ($15M at $60M post). They must decide: sell early, sell later, or stay independent? "
                "\n\n"
                "**Timeline A (OpenAI Acquisition - Dec 2026)**: OpenAI offers $500M all-cash, close in 90 days. "
                "Sam Altman personally courts Founder A: 'We need temporal simulation for reinforcement learning and "
                "safety testing. You'd run a 50-person team inside OpenAI with full autonomy.' The math: Founder A owns "
                "32% post-dilution → $160M. Founder B owns 20% → $100M. Life-changing money at age 35/38. They accept. "
                "By 2028, Company is deeply integrated into ChatGPT's training pipeline but Founder A reports to "
                "OpenAI's CPO. The technology succeeded but the independent company dream died. Founder A sometimes "
                "wonders what could have been. "
                "\n\n"
                "**Timeline B (Anthropic Acquisition - June 2027)**: Anthropic offers $800M (60% cash, 40% Anthropic "
                "equity), close in 120 days. Dario Amodei pitches constitutional AI alignment: 'Company's modal "
                "causality solves our interpretability problem.' The structure: Founder A gets $192M cash + $128M "
                "Anthropic stock (currently worth $128M, potentially $500M if Anthropic IPOs). Founder B gets $120M "
                "cash + $80M stock. Higher valuation, more upside, but stock illiquidity risk. They accept, betting "
                "on Anthropic's trajectory. By 2028, Company is the foundation for Claude's scenario modeling. "
                "Founder A is Anthropic VP with board seat. The Anthropic stock is now worth $400M (paper gains) but "
                "still illiquid. Higher ceiling, higher risk. "
                "\n\n"
                "**Timeline C (Stay Independent - IPO Nov 2028)**: Founder A and Founder B decline both offers. 'We're "
                "building a category-defining company. $500M is too low, and we don't want to be a feature inside "
                "someone else's product.' They raise Series B ($50M at $250M post, Oct 2026), Series C ($150M at "
                "$800M post, June 2027), and IPO at $2B (Nov 2028). Founder A owns 32% post-IPO → $640M liquid at IPO, "
                "worth $960M by 2029. Founder B owns 20% → $400M liquid, worth $600M by 2029. Highest outcome but "
                "required grinding through Series B, Series C, IPO process, public company scrutiny, and 2 more "
                "years of 80-hour weeks. They kept control but paid in time and stress. "
                "\n\n"
                "Track 12 timepoints: (1-2) Formation & Series A (same across timelines), (3) September 2026 offers "
                "arrive, (4-5) Timeline A: OpenAI negotiations → close Dec 2026, (6-7) Timeline B: Anthropic negotiations "
                "→ close June 2027, (8-12) Timeline C: Series B → Series C → IPO Nov 2028. Demonstrates M12 (three "
                "exit paths), M15 (prospection: modeling future outcomes under each scenario), M11 (founder-acquirer "
                "negotiations), M8 (stress of decision-making: $500M bird in hand vs $2B in bush?), M7 (causal chains "
                "from decision to outcome)."
            ),
            world_id="timepoint_acquisition_scenarios",
            entities=EntityConfig(
                count=6,  # Founder A + Founder B + OpenAI exec + Anthropic exec + Series B VC + IPO banker
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=12,  # Formation → offers → three divergent timelines
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Three acquisition timelines
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,  # Critical: acquisition negotiations
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "acquisition_scenario_comparison",
                "timelines": [
                    {
                        "id": "timeline_a_early_acquisition_cash",
                        "structure": "Early acquisition by tech giant (all cash)",
                        "hypothesis": "Quick liquidity provides founders with immediate wealth but caps upside and loses independence"
                    },
                    {
                        "id": "timeline_b_later_acquisition_mixed",
                        "structure": "Later acquisition with cash+stock structure",
                        "hypothesis": "Higher valuation and strategic upside but introduces illiquidity risk and continued dependence on acquirer"
                    },
                    {
                        "id": "timeline_c_stay_independent_ipo",
                        "structure": "Remain independent and pursue IPO",
                        "hypothesis": "Maximum outcome and control retention but requires years of grinding and execution risk"
                    }
                ],
                "key_questions": [
                    "How do founders weigh immediate liquidity vs long-term upside potential?",
                    "What role does cash vs stock structure play in acquisition decisions?",
                    "How does acquisition timing affect both valuation and founder satisfaction?",
                    "What are the stress and opportunity cost tradeoffs of staying independent?",
                    "How do cofounders align on exit decisions when personal circumstances differ?"
                ],
                "mechanisms_featured": [
                    "M12_branching_exit_paths",
                    "M15_prospection_modeling_future_outcomes",
                    "M11_acquisition_negotiation_dialogs",
                    "M8_embodied_stress_major_decision",
                    "M7_causal_chains_offer_to_outcome",
                    "M13_cofounder_alignment_on_decision"
                ],
                "emergent_format": True,
                "uses_profile_system": False
            }
        )

    @classmethod
    def timepoint_cofounder_configurations(cls) -> "SimulationConfig":
        """
        Compare 4 co-founder role configurations from same formation moment.

        Company Formation Scenarios: Four parallel timelines from October 2024 formation,
        each with different co-founder role split: (A) CEO 55% / President 35%, (B) CEO 50% / CTO 40%,
        (C) CEO 60% / VP Sales 20% + technical hire CTO 10%, (D) Executive Chair 45% / CEO 45%.
        Track to Series A (18 months) to see which structure wins. Demonstrates M12, M13, M8, M7.
        """
        return cls(
            scenario_description=(
                "**October 2024: Formation Decision** - Founder A and Founder B are incorporating "
                "Company. They have the technical prototype (17 mechanisms working, ANDOS training "
                "validated). Now they must decide: what roles do we take? How do we split equity? Four parallel "
                "universes diverge from this moment: "
                "\n\n"
                "**Timeline A (CEO 55% / President 35%)**: Founder A is CEO, Founder B is President. Clear division: "
                "Founder A owns product vision, technical architecture, fundraising, board. Founder B owns operations, "
                "GTM, sales, hiring, finance. Equity: Founder A 55%, Founder B 35%, ESOP 10%. By Month 6 (April 2025), "
                "they have 2 paying customers ($15K MRR). Founder B built the sales process, Founder A closed deals. "
                "By Month 12 (October 2025), $80K MRR, 3 salespeople reporting to Founder B. By Month 18 (April 2026), "
                "$250K MRR. They raise Series A: $15M at $60M post. The President structure worked—clear swim lanes, "
                "no overlap, complementary skills. VCs loved the operational muscle. "
                "\n\n"
                "**Timeline B (CEO 50% / CTO 40%)**: Founder A is CEO, Founder B is CTO. Founder B focuses purely on "
                "product/engineering. Equity: Founder A 50%, Founder B 40%, ESOP 10%. By Month 6, they have 1 pilot "
                "customer (no revenue—still testing). Founder A is doing product AND GTM, stretched thin. By Month 12, "
                "product is technically superior but only $30K MRR. They hire VP Sales (takes 2% equity). By Month 18, "
                "$120K MRR. They raise Series A: $12M at $40M post (lower than timeline A). The CTO structure is "
                "product-strong but commercially slow. Founder B wishes he had more commercial responsibility. "
                "\n\n"
                "**Timeline C (CEO 60% / VP Sales 20% + CTO hire 10%)**: Founder A is CEO, Founder B is VP Sales. Equity: "
                "Founder A 60%, Founder B 20%, ESOP 10%. Founder B feels under-valued (20% vs his contributions). By Month 3, "
                "tension emerges: 'I'm doing as much as you but getting 1/3 the equity?' Founder A argues she's the "
                "technical genius. They hire a CTO (10% equity, 4-year vest). By Month 8, the CTO realizes the "
                "technology is too complex—can't keep up with Founder A's vision—quits. Now Founder A is CEO+CTO again. "
                "Founder B is demoralized. By Month 15, Founder B leaves to start his own company. Founder A is alone with "
                "50% of equity (Founder B forfeited 10% unvested). Series A: $10M at $30M post. The 60/20 split destroyed "
                "trust and killed the company's momentum. "
                "\n\n"
                "**Timeline D (Executive Chair 45% / CEO 45%)**: Founder A is Executive Chair (product/vision), Founder B "
                "is CEO (operations/business). Equity: Founder A 45%, Founder B 45%, ESOP 10%. This is the 'equal partnership' "
                "model. By Month 6, friction emerges: who has final say? Founder A wants to prioritize animistic entities "
                "(M16), Founder B wants to ship enterprise features. Board meetings become debates. By Month 10, investors "
                "get nervous: 'You need ONE CEO, not two.' By Month 14, they do a 'CEO re-org': Founder B becomes sole "
                "CEO, Founder A becomes Chief Product Officer. Equity stays 45/45 but Founder A lost title/control. By Month 18, "
                "$180K MRR. Series A: $13M at $50M post. The equal split worked equity-wise but operationally messy. "
                "\n\n"
                "Track 18 timepoints: Formation (t0) → Month 3 (t1) → Month 6 (t2) → Month 9 (t3) → Month 12 (t4) → "
                "Month 15 (t5) → Month 18 / Series A (t6). Four parallel timelines, each with 6 milestones. Demonstrates "
                "M12 (four role structures), M13 (relationship evolution: trust vs tension), M8 (stress from "
                "equity/control conflicts), M7 (causal chains: role → execution → outcome), M11 (difficult founder "
                "conversations about equity and control)."
            ),
            world_id="timepoint_cofounder_configs",
            entities=EntityConfig(
                count=6,  # Founder A + Founder B + CTO hire (timeline C) + VP Sales hire + Series A VC + advisor
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=18,  # 6 milestones × 3 timepoints per milestone (decision, execution, outcome)
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Four co-founder configurations
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,  # Critical: founder conflict conversations
                include_relationships=True,  # M13: trust vs tension dynamics
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "cofounder_role_configuration_comparison",
                "formation_date": "2024-10",
                "evaluation_date": "2026-04",  # 18 months post-formation
                "timelines": [
                    {
                        "id": "timeline_a_ceo_president",
                        "structure": "CEO + President (Operational Leader)",
                        "equity_split": "55/35/10 (ESOP)",
                        "hypothesis": "Clear role division with CEO focusing on product/fundraising and President on operations/GTM enables rapid scaling and strong valuations"
                    },
                    {
                        "id": "timeline_b_ceo_cto",
                        "structure": "CEO + CTO (Technical Leader)",
                        "equity_split": "50/40/10 (ESOP)",
                        "hypothesis": "Technical depth is maximized but commercial execution suffers without dedicated operational cofounder"
                    },
                    {
                        "id": "timeline_c_ceo_vp_sales_undervalued",
                        "structure": "CEO + VP Sales (Low Equity)",
                        "equity_split": "60/20/10 (ESOP) + 10% CTO hire",
                        "hypothesis": "Unequal equity split creates resentment and destroys cofounder trust, leading to departure and company damage"
                    },
                    {
                        "id": "timeline_d_executive_chair_ceo",
                        "structure": "Executive Chair + CEO (Equal Partners)",
                        "equity_split": "45/45/10 (ESOP)",
                        "hypothesis": "Equal partnership works equity-wise but creates decision paralysis requiring eventual role clarification"
                    }
                ],
                "key_questions": [
                    "Which cofounder role structures enable faster commercial scaling?",
                    "How do equity splits affect long-term cofounder relationship health?",
                    "Does CEO/President outperform CEO/CTO for commercial SaaS companies?",
                    "What equity imbalances trigger cofounder resentment and departure?",
                    "How does role clarity affect funding round valuations?"
                ],
                "mechanisms_featured": [
                    "M12_branching_role_configurations",
                    "M13_relationship_evolution_trust_vs_tension",
                    "M8_embodied_stress_equity_conflict",
                    "M7_causal_chains_role_to_outcome",
                    "M11_difficult_founder_conversations"
                ],
                "emergent_format": True,
                "uses_profile_system": False
            }
        )

    @classmethod
    def timepoint_equity_performance_incentives(cls) -> "SimulationConfig":
        """
        Compare equity structures: standard vesting vs performance milestones vs dynamic equity.

        Company Equity Experiments: Three parallel timelines with different equity structures:
        (A) Standard 50/50 with 4-year vesting, (B) 60/40 with performance milestones (revenue/product),
        (C) Dynamic equity with contribution tracking and quarterly rebalancing. Track 24 months to see
        which structure drives best outcomes and relationship health. Demonstrates M12, M13, M7, M15.
        """
        return cls(
            scenario_description=(
                "**October 2024: Equity Structure Decision** - Founder A and Founder B are finalizing "
                "the cap table. Standard advice says '50/50 split with 4-year vest.' But should they consider "
                "performance-based equity or dynamic contribution tracking? Three experiments: "
                "\n\n"
                "**Timeline A (Standard 50/50 Vesting)**: Founder A 50%, Founder B 50%, both 4-year vest with 1-year "
                "cliff. Simple, clean, founder-friendly. By Month 6, Founder A is working 80 hr/wk on product (she's "
                "the technical genius), Founder B is working 50 hr/wk on sales (learning curve). Founder A starts to "
                "resent: 'I'm building everything, we get the same equity?' Founder B counters: 'I closed our first "
                "3 customers.' By Month 12, tension rises. Product is great ($100K MRR) but Founder A feels under-rewarded "
                "for technical heroics. By Month 18, they have a blowup argument. Founder A wants to renegotiate equity "
                "to 60/40. Founder B refuses: 'We had a deal.' Relationship damaged. By Month 24, $300K MRR but trust "
                "is low (0.60 relationship health). Standard vesting didn't account for differential contribution. "
                "\n\n"
                "**Timeline B (60/40 with Performance Milestones)**: Founder A 60%, Founder B 40%, but Founder B can earn "
                "back to 45% by hitting milestones: (1) $50K MRR by Month 6 (+2%), (2) $200K MRR by Month 12 (+2%), "
                "(3) Hire 5-person sales team by Month 18 (+1%). By Month 6, Founder B hits $65K MRR → earns 2%, now 42%. "
                "He's motivated—concrete goals, clear rewards. By Month 12, they hit $220K MRR → Founder B earns another "
                "2%, now 44%. Founder A appreciates his execution. By Month 18, Founder B has hired 6 salespeople → earns "
                "final 1%, now 45%. Relationship health is high (0.85) because goals were transparent and Founder B "
                "earned the equity through performance. By Month 24, $500K MRR. The milestone structure aligned "
                "incentives and built trust through achievement. "
                "\n\n"
                "**Timeline C (Dynamic Equity with Contribution Tracking)**: Start 50/50, but use Slicing Pie or "
                "similar dynamic equity model: track hours worked, revenue generated, capital contributed, key hires "
                "made. Rebalance quarterly. By Month 3, Founder A has worked 960 hours, Founder B 600 hours → rebalance to "
                "Founder A 57%, Founder B 43%. Founder B feels weird: 'My equity went down?' By Month 6, Founder B crushed sales "
                "(3 customers, $40K MRR) → rebalance to Founder A 54%, Founder B 46% (his contributions weighted up). By "
                "Month 9, Founder A built the entire ANDOS system (300 hours of deep work) → rebalance to Founder A 58%, "
                "Founder B 42%. Founder B is frustrated: 'I can't win—my equity keeps moving.' By Month 15, Founder B asks "
                "to switch to fixed vesting: 'This is demotivating.' They lock equity at Founder A 56%, Founder B 44%. "
                "By Month 24, $350K MRR. Dynamic equity was theoretically fair but psychologically exhausting. "
                "Constant rebalancing created anxiety, not motivation. "
                "\n\n"
                "Track 24 timepoints: 1 per month from formation to Series A. Three parallel timelines with "
                "different equity structures. Demonstrates M12 (three equity models), M13 (relationship health "
                "diverges dramatically by structure), M7 (equity structure → incentives → outcomes), M15 (founders "
                "model future equity under each structure), M11 (difficult conversations about contribution and "
                "fairness), M8 (stress from equity uncertainty in Timeline C)."
            ),
            world_id="timepoint_equity_incentives",
            entities=EntityConfig(
                count=4,  # Founder A + Founder B + lawyer/advisor + Series A VC
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=24,  # Monthly tracking for 24 months
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Three equity structures
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,  # Critical: equity negotiation conversations
                include_relationships=True,  # M13: trust dynamics under different structures
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "equity_structure_performance_incentives",
                "timelines": [
                    {
                        "id": "timeline_a_standard_5050_vesting",
                        "structure": "Standard 50/50 with 4-year vesting and 1-year cliff",
                        "hypothesis": "Equal equity split is simple and founder-friendly but may not account for differential contribution, leading to resentment"
                    },
                    {
                        "id": "timeline_b_6040_performance_milestones",
                        "structure": "60/40 initial with performance milestone earn-back",
                        "hypothesis": "Performance milestones create clear goals and allow founders to earn equity through achievement, aligning incentives and building trust"
                    },
                    {
                        "id": "timeline_c_dynamic_equity_tracking",
                        "structure": "Dynamic equity with quarterly contribution rebalancing",
                        "hypothesis": "Dynamic equity is theoretically fair but constant rebalancing creates psychological stress and demotivation"
                    }
                ],
                "key_questions": [
                    "How do different equity structures affect cofounder motivation and effort levels?",
                    "Does performance-based equity create better alignment than fixed vesting?",
                    "What are the psychological effects of dynamic equity rebalancing?",
                    "How does equity certainty vs uncertainty impact relationship health?",
                    "Which equity structures lead to better long-term business outcomes?"
                ],
                "mechanisms_featured": [
                    "M12_branching_equity_structures",
                    "M13_relationship_trust_under_different_incentives",
                    "M7_equity_to_motivation_to_outcome",
                    "M15_founders_model_future_equity",
                    "M11_difficult_equity_conversations",
                    "M8_stress_from_equity_uncertainty"
                ],
                "emergent_format": True,
                "uses_profile_system": False
            }
        )

    @classmethod
    def timepoint_critical_formation_decisions(cls) -> "SimulationConfig":
        """
        Branch at formation critical decisions: Delaware vs Wyoming, patents vs trade secrets, angel vs bootstrap.

        Company Formation Branching: Eight decision points at formation, each branching into 2-3 outcomes.
        (1) Delaware C-Corp vs Wyoming LLC, (2) File patents early vs trade secrets, (3) Take $500K angel vs
        bootstrap, (4) Hire lawyer now vs DIY formation, (5) Open source some code vs closed, (6) Target enterprise
        vs SMB, (7) Raise pre-seed immediately vs build traction first. Each decision cascades. Demonstrates M12.
        """
        return cls(
            scenario_description=(
                "**October 2024: Formation Decision Tree** - Founder A and Founder B sit in a Palo Alto "
                "coffee shop with 17 critical formation decisions to make. Each choice branches into multiple "
                "futures. This simulation explores the exponential tree of early-stage decisions: "
                "\n\n"
                "**Decision 1: Incorporation** - Delaware C-Corp (standard for VCs, $2K setup, annual franchise "
                "tax) vs Wyoming LLC (cheaper, privacy, but harder for VC funding). They choose Delaware C-Corp. "
                "Outcome: VC-friendly, easier Series A negotiations. Cost: $2K setup + $450/year franchise tax. "
                "\n\n"
                "**Decision 2: IP Strategy** - File provisional patents on 17 mechanisms ($15K in legal fees, "
                "12-month clock) vs keep as trade secrets (free, no disclosure). Branch A: File patents → $15K "
                "cost but VCs love the IP moat → Series A valuation +15%. Branch B: Trade secrets → save $15K "
                "but harder to defend against OpenAI/Anthropic copying the mechanisms → competitive risk. They "
                "choose patents. Outcome: Strong IP position, higher valuation, but $15K cash burn. "
                "\n\n"
                "**Decision 3: Initial Funding** - Take $500K angel round (from YC partner, 10% equity at $5M cap) "
                "vs bootstrap on savings ($200K runway). Branch A: Take angel → 12 months runway, can hire 2 "
                "engineers, faster product development, but 10% dilution and angel wants board observer seat. "
                "Branch B: Bootstrap → keep 100% equity, but slower development, might miss market window. They "
                "take the angel round. Outcome: 10% dilution but 3x faster execution. "
                "\n\n"
                "**Decision 4: Legal Setup** - Hire Cooley/WSGR ($25K formation package) vs use Clerky/DIY ($2K). "
                "Branch A: Hire WSGR → perfect docs, stock option plan, founder vesting, 83(b) elections all "
                "correct → saves headaches at Series A. Branch B: DIY with Clerky → save $23K but sloppy cap "
                "table, missing 83(b) elections → costs $50K in legal cleanup at Series A. They hire WSGR. "
                "Outcome: $25K upfront but saves $50K+ later and avoids dilution penalties. "
                "\n\n"
                "**Decision 5: Open Source Strategy** - Open source the query engine (builds community, recruits "
                "developers) vs closed source everything (protects IP). Branch A: Open source → 5,000 GitHub stars "
                "by Month 6, inbound interest from enterprise, but competitors fork the code. Branch B: Closed "
                "source → zero community but full control. They choose selective open source (query engine open, "
                "17 mechanisms proprietary). Outcome: Best of both worlds—community + moat. "
                "\n\n"
                "**Decision 6: Target Market** - Enterprise (long sales cycles, $100K ACV) vs SMB (short cycles, "
                "$10K ACV). Branch A: Enterprise → first deal takes 9 months but $120K ACV → $1M ARR from 9 customers. "
                "Branch B: SMB → 100 customers at $10K ACV but high churn (50% annual) → $500K ARR. They choose "
                "enterprise. Outcome: Slower but stickier revenue. "
                "\n\n"
                "**Decision 7: Raise Pre-Seed Immediately vs Build First** - Raise $2M pre-seed now (dilute 20% "
                "at $8M post) vs build traction for 6 months then raise at higher valuation. Branch A: Raise now "
                "→ 20% dilution, $2M in bank, hire 4 people, ship product in 6 months. Branch B: Build first → "
                "keep equity, bootstrap to $50K MRR, raise $2M at $15M post (13% dilution) in Month 9. They choose "
                "build first. Outcome: Less dilution (13% vs 20%), harder grind, but $7M valuation delta. "
                "\n\n"
                "Track 21 timepoints: 7 decision points × 3 timepoints each (decision → execution → outcome). "
                "Demonstrates M12 (branching decision tree), M7 (decisions cascade causally), M15 (founders model "
                "outcomes), M11 (founder debates on each decision)."
            ),
            world_id="timepoint_formation_decisions",
            entities=EntityConfig(
                count=5,  # Founder A + Founder B + lawyer + angel investor + advisor
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=21,  # 7 decisions × 3 timepoints each
                resolution="day"  # Track formation decisions at daily resolution
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Decision tree branches
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "critical_formation_decisions",
                "decision_domains": [
                    {"id": 1, "domain": "Incorporation Structure", "trade_off": "VC-friendly (Delaware C-Corp) vs cost-effective (Wyoming LLC)"},
                    {"id": 2, "domain": "IP Protection Strategy", "trade_off": "Patent filing costs vs trade secret risk"},
                    {"id": 3, "domain": "Initial Funding Approach", "trade_off": "Angel investment (dilution + runway) vs bootstrap (equity + constraints)"},
                    {"id": 4, "domain": "Legal Infrastructure", "trade_off": "Premium law firm (clean setup) vs DIY (cost savings + future cleanup risk)"},
                    {"id": 5, "domain": "Open Source Strategy", "trade_off": "Community building vs IP protection"},
                    {"id": 6, "domain": "Target Market Selection", "trade_off": "Enterprise (high ACV, slow cycles) vs SMB (low ACV, fast cycles)"},
                    {"id": 7, "domain": "Fundraising Timing", "trade_off": "Raise early (more runway, more dilution) vs build traction first (less dilution, slower)"}
                ],
                "key_questions": [
                    "How do early incorporation decisions affect later fundraising ability?",
                    "What is the ROI of patent filing vs trade secrets for venture-backed companies?",
                    "How does angel funding timing affect Series A valuations and dilution?",
                    "What are the long-term costs of DIY legal vs premium law firms?",
                    "How does open source strategy impact community growth and competitive moats?",
                    "Which target market decisions lead to better unit economics?",
                    "How does pre-traction fundraising timing affect founder dilution?"
                ],
                "mechanisms_featured": [
                    "M12_branching_decision_tree",
                    "M7_causal_chains_decisions_cascade",
                    "M15_prospection_modeling_outcomes",
                    "M11_founder_debates_on_decisions"
                ],
                "emergent_format": True,
                "uses_profile_system": False
            }
        )

    @classmethod
    def timepoint_success_vs_failure_paths(cls) -> "SimulationConfig":
        """
        Two timelines from same formation: one succeeds to IPO ($2B), one fails (shutdown).

        Company Success vs Failure: Parallel timelines from identical starting conditions (October 2024,
        same team, same tech). Timeline A makes optimal decisions → IPO $2B (Nov 2028). Timeline B makes
        suboptimal decisions → shutdown (August 2026). Trace the divergence to identify critical failure
        points. Demonstrates M12 (branching), M7 (causal chains to failure), M13 (relationship breakdown).
        """
        return cls(
            scenario_description=(
                "**October 2024: Two Timelines Diverge** - Founder A and Founder B incorporate Company. "
                "Same team, same technology, same market opportunity. But in one timeline, they make optimal decisions "
                "and reach $2B IPO. In the other, they make suboptimal decisions and shut down in 22 months. What "
                "went wrong? "
                "\n\n"
                "**Timeline A (Success → IPO $2B)**: (1) Month 0: Incorporate in Delaware, file patents, take $500K "
                "angel at 10% equity. (2) Month 6: Launch MVP, sign first 3 customers ($30K MRR), product-market fit "
                "validated. (3) Month 12: Raise $2M pre-seed at $12M post (14% dilution), $150K MRR, hire 4 people. "
                "(4) Month 18: $500K MRR, 15 employees, strong unit economics ($5K CAC, $100K LTV). Raise $15M Series A "
                "at $60M post. (5) Month 30: $3M MRR, 40 employees. Raise $50M Series B at $250M post. (6) Month 42: "
                "$15M MRR. Raise $150M Series C at $800M post. (7) Month 50 (Nov 2028): IPO at $2B, $150M ARR. "
                "Success drivers: (a) Clear CEO/President roles, (b) Enterprise focus (high ACV), (c) Capital efficient "
                "(raised at increasing valuations), (d) Strong relationship between founders (0.90 health throughout). "
                "\n\n"
                "**Timeline B (Failure → Shutdown Aug 2026)**: (1) Month 0: Same incorporation, but they skip patents "
                "(\"too expensive\"). Bootstrap instead of taking angel round (\"keep 100% equity\"). Already a mistake—no "
                "runway. (2) Month 6: Burn through savings ($180K spent), only 1 pilot customer (no revenue). Product "
                "too complex, no PMF yet. Desperation sets in. (3) Month 9: Take $500K angel at 25% equity (desperation "
                "valuation, 2.5x worse than Timeline A). Founder equity now 37.5% each. (4) Month 12: Still only $15K MRR, "
                "6 employees burning $75K/month. Runway is 4 months. Try to raise Series A but no traction. (5) Month 14: "
                "Founder conflict erupts: Founder A blames Founder B for weak sales execution, Founder B blames Founder A for over-engineered "
                "product. Relationship health drops to 0.30. (6) Month 16: VCs pass on Series A: 'Come back when you have "
                "$100K MRR.' Founders consider pivoting to SMB. More conflict: Founder A wants to stay enterprise, Founder B wants "
                "SMB volume. (7) Month 18: Pivot to SMB, rewrite sales playbook. But now they're 6 months behind competitors. "
                "(8) Month 20: $40K MRR (SMB), but burn is $60K/month. Bank account: $120K. Founder B wants to shut down, Founder A "
                "wants to fight. (9) Month 22 (August 2026): Runway is 60 days. No investor interest. Founders agree to shut "
                "down. Final equity: Founder A 37.5%, Founder B 37.5%, investors 25%—all worthless. Postmortem: (a) Skipping angel "
                "round killed runway, (b) No patents → competitors copied mechanisms, (c) Founder conflict destroyed morale, "
                "(d) Late pivot wasted time. "
                "\n\n"
                "Track 22 timepoints in Timeline B (failure), 50 timepoints in Timeline A (success). Demonstrates M12 "
                "(success vs failure branching), M7 (causal chains: bad decision → cash crunch → desperation → conflict "
                "→ shutdown), M13 (relationship health: 0.90 in success, 0.30 in failure), M8 (embodied stress in failure "
                "timeline), M11 (founder conflict dialogs in failure timeline), M15 (in Month 20, founders model 'do we "
                "shut down or fight?')."
            ),
            world_id="timepoint_success_vs_failure",
            entities=EntityConfig(
                count=6,  # Founder A + Founder B + angel investor + Series A VC (success) + failed investor (failure) + advisor
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=25,  # Timeline B: 22 timepoints to failure, Timeline A: diverges at Month 0 and runs to Month 50 (tracked as summary)
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Success vs failure
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,  # Critical: founder conflict in failure timeline
                include_relationships=True,  # M13: relationship breakdown in failure
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "success_vs_failure_paths",
                "timelines": [
                    {
                        "id": "timeline_a_success_path",
                        "structure": "Optimal decisions leading to IPO",
                        "hypothesis": "Early funding, IP protection, clear roles, and founder alignment enable exponential growth and successful exit"
                    },
                    {
                        "id": "timeline_b_failure_path",
                        "structure": "Suboptimal decisions leading to shutdown",
                        "hypothesis": "Bootstrap without runway, skipping IP protection, founder conflict, and panic pivots create cascading failures"
                    }
                ],
                "key_questions": [
                    "What are the earliest decision points that differentiate success from failure?",
                    "How does founder relationship health correlate with company outcomes?",
                    "What role does initial funding timing play in long-term success?",
                    "How do IP protection decisions affect competitive positioning?",
                    "When do companies reach 'point of no return' failure cascades?",
                    "How does panic pivoting affect company trajectory vs staying the course?"
                ],
                "mechanisms_featured": [
                    "M12_branching_success_vs_failure",
                    "M7_causal_chains_bad_decisions_to_shutdown",
                    "M13_relationship_breakdown_in_failure",
                    "M8_embodied_stress_desperation_in_failure",
                    "M11_founder_conflict_dialogs",
                    "M15_prospection_shutdown_decision_modeling"
                ],
                "emergent_format": True,
                "uses_profile_system": False
            }
        )

    @classmethod
    def timepoint_launch_marketing_campaigns(cls) -> "SimulationConfig":
        """
        Emergent marketing campaign strategy comparison across four different approaches.

        Explores how different marketing strategies (content/SEO, paid acquisition,
        community building, enterprise outbound) perform under different conditions.
        Agents decide budget allocation, messaging, channels, and creative execution.
        Outcomes emerge from founder creativity, market conditions, and execution quality.

        Mechanisms: M3 (branching), M10 (scene analysis), M14 (circadian rhythm)
        """
        return cls(
            scenario_description=(
                "**January 2025: Launch Marketing Campaign Decision** - Company has a functional product "
                "and $120K in initial funding. Founder A and Founder B must decide on their go-to-market "
                "strategy. This simulation explores four different marketing approaches across parallel timelines. "
                "Track for 9 months to measure customer acquisition, burn rate, and product-market fit signals. "
                "Agents must make all creative, budgeting, and channel decisions—outcomes emerge from execution quality."
                "\n\n"
                "**Timeline A: Content Marketing + SEO (Organic Growth)**"
                "\n"
                "Founder A and Founder B debate their marketing strategy. Timeline A pursues content marketing: "
                "blog posts, technical guides, SEO optimization, organic social media. This approach requires "
                "minimal ad spend but significant creative effort {content_hours_per_week}. Month 1-3: Founders "
                "must decide content topics {content_topics}, publishing frequency {posts_per_week}, and SEO "
                "keywords {target_keywords}. They create content themselves or hire writers {hiring_decision}. "
                "Month 4-6: Search rankings begin to emerge {domain_authority_month_6}, organic traffic grows "
                "{monthly_visitors_month_6}, but paid conversions remain low {mrr_month_6}. Founders debate: "
                "is organic growth too slow {pivot_discussion_month_6}? Month 7-9: Long-tail SEO compounds "
                "{organic_traffic_month_9}, some enterprise leads emerge from content {enterprise_leads}, "
                "but burn rate concerns mount {cash_remaining_month_9}. Can they reach sustainability before "
                "running out of money {runway_months_remaining}?"
                "\n\n"
                "**Timeline B: Paid Acquisition + Growth Hacking (Fast Burn)**"
                "\n"
                "Timeline B pursues aggressive paid acquisition: search ads, professional network campaigns, retargeting, "
                "growth hacking experiments. Founders allocate $60K to paid channels {monthly_ad_budget}. "
                "Month 1-3: They experiment with messaging {ad_creative_variations}, targeting {audience_segments}, "
                "and channels {channel_mix}. Early CAC is high {cac_month_3} but they gain rapid learning "
                "{conversion_insights}. Month 4-6: Founders optimize based on data {optimization_strategy}, "
                "discover best-performing segments {winning_segments}, scale winning campaigns {budget_increase}. "
                "MRR grows faster {mrr_month_6} but burn accelerates {monthly_burn_month_6}. Month 7-9: "
                "They face a critical decision: continue burning to scale {continue_paid} or pull back to "
                "extend runway {reduce_spend}? If CAC remains high {cac_month_9} relative to LTV, can they "
                "achieve unit economics {ltv_cac_ratio} or do they run out of cash {cash_remaining_month_9}?"
                "\n\n"
                "**Timeline C: Community Building + Influencer Partnerships (Relationship-Driven)**"
                "\n"
                "Timeline C focuses on community: Discord server, Slack community, partnerships with micro-influencers, "
                "developer advocacy. Low cash burn {monthly_budget_community} but high founder time investment "
                "{community_hours_per_week}. Month 1-3: Founders identify niche communities {target_communities}, "
                "engage authentically {engagement_strategy}, recruit early champions {community_champions}. "
                "They debate: should Founder A be full-time community manager {role_allocation} or hire someone "
                "{hiring_decision}? Month 4-6: Community size grows {community_members_month_6}, engagement "
                "is strong {daily_active_users}, but paid conversions lag {mrr_month_6}. Influencer partnerships "
                "{influencer_deals} generate awareness but unclear ROI. Month 7-9: Network effects begin "
                "{referral_rate_month_9}, community members become evangelists {user_generated_content}, "
                "some enterprises discover product through community {enterprise_pipeline}. Can relationship-driven "
                "growth create sustainable CAC advantage {organic_conversion_rate} or is it too slow to scale "
                "{growth_rate_month_9}?"
                "\n\n"
                "**Timeline D: Enterprise Outbound Sales (High-Touch)**"
                "\n"
                "Timeline D pursues enterprise outbound: cold email, LinkedIn outreach, demo calls, multi-touch "
                "sales cycles. Founders hire a sales development rep {sdr_hire_month} and build outbound playbook "
                "{outbound_playbook}. Month 1-3: They define ideal customer profile {icp_criteria}, build prospect "
                "lists {prospect_count}, craft messaging {email_sequences}, and start outreach {emails_sent_per_week}. "
                "Initial response rates {response_rate_month_3} and meeting booking {meetings_booked} emerge. "
                "Month 4-6: Sales cycles progress {avg_deal_cycle_days}, they negotiate first enterprise deals "
                "{deal_negotiations}, handle objections {common_objections}. Some deals close {mrr_month_6}, "
                "others stall {pipeline_stalled}. Month 7-9: They refine pitch based on learnings {pitch_evolution}, "
                "discover which segments convert fastest {fastest_converting_segments}, build case studies "
                "{customer_case_studies}. Enterprise ARR grows {arr_month_9} but CAC remains high {cac_month_9} "
                "and sales cycles long {avg_sales_cycle}. Can they prove enterprise model is scalable {sales_efficiency} "
                "or does high-touch selling burn too much cash {cash_remaining_month_9}?"
            ),
            entities=EntityConfig(
                count=2,
                types=["human"]
            ),
            timepoints=CompanyConfig(
                count=9,
                resolution="month"
            ),
            temporal=TemporalConfig(mode=TemporalMode.PEARL),
            world_id="timepoint_launch_marketing_campaigns",
            metadata={
                "analysis_type": "marketing_campaign_strategy_comparison",
                "timelines": [
                    {
                        "id": "timeline_a_content_seo",
                        "structure": "Content marketing + SEO (organic growth)",
                        "hypothesis": "Organic content creation builds long-term search authority and low-cost acquisition but requires patience and may be too slow for venture timelines"
                    },
                    {
                        "id": "timeline_b_paid_acquisition",
                        "structure": "Paid acquisition + growth hacking (fast burn)",
                        "hypothesis": "Paid channels enable rapid experimentation and learning but high CAC may prevent unit economics from working before cash runs out"
                    },
                    {
                        "id": "timeline_c_community_influencer",
                        "structure": "Community building + influencer partnerships (relationship-driven)",
                        "hypothesis": "Community-driven growth creates authentic engagement and word-of-mouth but may lack the velocity needed for aggressive scaling"
                    },
                    {
                        "id": "timeline_d_enterprise_outbound",
                        "structure": "Enterprise outbound sales (high-touch)",
                        "hypothesis": "Direct enterprise sales generates higher ACV and predictable pipeline but long cycles and high CAC test cash runway limits"
                    }
                ],
                "key_questions": [
                    "Which marketing strategy achieves the best balance of growth rate and capital efficiency?",
                    "How do founder personality and creativity affect success of content vs community strategies?",
                    "Can paid acquisition achieve sustainable unit economics (LTV/CAC > 3) within 9 months?",
                    "Does community-driven growth create durable competitive advantages through network effects?",
                    "Which approach generates the strongest product-market fit signals from customer feedback?",
                    "How do different strategies affect founder stress, time allocation, and relationship health?",
                    "Can enterprise outbound sales prove scalability or does it remain a high-touch grind?"
                ],
                "emergent_format": True,
                "uses_profile_system": True,
                "mechanisms": ["M3_branching", "M10_scene_analysis", "M14_circadian_rhythm"],
                "initial_conditions": {
                    "starting_capital": 120000,
                    "product_status": "functional MVP",
                    "current_mrr": 2000,
                    "team_size": 2,
                    "monthly_burn": 15000
                }
            }
        )

    @classmethod
    def timepoint_staffing_and_growth(cls) -> "SimulationConfig":
        """
        Emergent team scaling strategy comparison across four different hiring approaches.

        Explores how different hiring strategies (sales-first, product-first, leadership-first,
        generalist-scrappy) affect company growth, culture, and capital efficiency. Agents decide
        hiring priorities, compensation, role definitions, and team structure. Outcomes emerge from
        founder management skills, market conditions, and talent quality.

        Mechanisms: M3 (branching), M10 (scene analysis), M14 (circadian rhythm), M15 (prospection)
        """
        return cls(
            scenario_description=(
                "**March 2025: First Hiring Wave Decision** - Company raised $800K seed round and has "
                "$30K MRR with 2 founders and 1 contractor. Founder A and Founder B must decide how to "
                "deploy their first $400K in hiring budget. This simulation explores four different team "
                "scaling approaches across parallel timelines. Track for 12 months to measure revenue growth, "
                "team effectiveness, burn rate, and culture. Agents must make all hiring, compensation, and "
                "organizational decisions—outcomes emerge from execution quality and market fit."
                "\n\n"
                "**Timeline A: Sales-First Hiring (Revenue Acceleration)**"
                "\n"
                "Founder A and Founder B debate hiring strategy. Timeline A prioritizes revenue generation: "
                "hire Sales Development Rep (SDR), Account Executive (AE), Customer Success Manager (CSM). "
                "Month 1-3: They define sales roles {sales_role_definitions}, set compensation {sales_comp_structure}, "
                "recruit candidates {recruiting_strategy}, and make offers {offer_packages}. First sales hire "
                "starts {first_hire_start_date}, ramp-up begins {onboarding_plan}. Founders must manage sales "
                "team {management_approach} while still building product {founder_time_split}. Month 4-6: "
                "Sales team performance emerges {sales_quota_attainment}, pipeline builds {pipeline_value_month_6}, "
                "but product velocity slows {feature_releases_month_6}. Founders debate: hire more engineers "
                "{hiring_adjustment_debate} or double down on sales {continue_sales_first}? Month 7-9: Revenue "
                "accelerates {mrr_month_9}, but technical debt accumulates {tech_debt_month_9}, product "
                "quality concerns surface {customer_complaints}. Month 10-12: Can sales-driven growth reach "
                "$150K MRR {revenue_target} before product issues {churn_rate_month_12} cause problems? "
                "Team size {team_size_month_12}, burn rate {monthly_burn_month_12}, and culture fit "
                "{culture_health_score} all emerge from decisions."
                "\n\n"
                "**Timeline B: Product-First Hiring (Technical Excellence)**"
                "\n"
                "Timeline B prioritizes product development: hire Senior Engineer, Product Designer, "
                "Technical Lead. Month 1-3: Founders define engineering roles {eng_role_definitions}, "
                "set technical bar {interview_process}, recruit from networks {sourcing_channels}, negotiate "
                "offers {eng_compensation}. First engineer joins {first_hire_onboarding}, architecture "
                "decisions made {tech_stack_choices}. Product velocity accelerates {features_shipped_month_3}. "
                "Month 4-6: Engineering team builds ambitious roadmap {product_roadmap}, ships major features "
                "{feature_releases_month_6}, improves scalability {infrastructure_improvements}. But revenue "
                "growth stalls {mrr_month_6} as founders remain the only sales people {sales_capacity}. "
                "Founders debate: can product quality alone drive growth {product_led_growth_belief} or do "
                "they need sales support {hire_sales_debate}? Month 7-9: Product reaches technical excellence "
                "{product_quality_score}, some organic growth from word-of-mouth {referral_customers}, but "
                "burn accelerates {cash_remaining_month_9}. Month 10-12: Can product-led growth prove out "
                "{plg_metrics_month_12} or do they run out of runway {months_runway_remaining} before achieving "
                "revenue targets? Engineering culture is strong {eng_culture_score} but commercial execution "
                "lags {sales_execution_score}."
                "\n\n"
                "**Timeline C: Leadership-First Hiring (Executive Leverage)**"
                "\n"
                "Timeline C hires experienced operators: VP Sales, VP Engineering, or VP Product. High-cost "
                "bet on leverage. Month 1-3: Founders identify executive needs {exec_role_priority}, recruit "
                "senior candidates {exec_search_strategy}, negotiate expensive packages {exec_comp_200k_plus}. "
                "They debate: can we afford this {burn_rate_concern} and will executive mesh with startup "
                "culture {culture_fit_concerns}? First exec joins {exec_start_date}, brings experience and "
                "network {exec_value_adds}. Month 4-6: Executive hires their team {exec_builds_team}, "
                "implements processes {new_processes}, drives strategy {strategic_initiatives}. Founders "
                "debate: are we moving faster {velocity_assessment} or did we add bureaucracy {overhead_concerns}? "
                "Revenue impact {mrr_month_6} and product velocity {features_month_6} emerge. Month 7-9: "
                "Executive leverage multiplies {team_output_month_9} or politics emerge {org_dysfunction}. "
                "Burn rate is high {monthly_burn_month_9}, clock is ticking {runway_months}. Month 10-12: "
                "Did executive hiring accelerate path to Series A {series_a_readiness} or burn cash without "
                "proportional results {roi_on_exec_hire}? Team culture {culture_score_month_12} and founder "
                "satisfaction {founder_satisfaction} reveal fit quality."
                "\n\n"
                "**Timeline D: Generalist-Scrappy Hiring (Capital Efficient)**"
                "\n"
                "Timeline D hires versatile generalists willing to do anything. No specialists. Month 1-3: "
                "Founders hire scrappy generalists {generalist_profile} with lower salaries {comp_80k_range}, "
                "flexible roles {role_fluidity}, startup mentality {culture_fit_criteria}. First hires join "
                "{hire_1_hire_2_start}, everyone does everything {role_responsibilities}. Overhead is minimal "
                "{low_burn_rate}. Month 4-6: Generalists wear many hats {tasks_per_person}, learn quickly "
                "{learning_velocity}, ship features and close deals {output_breadth}. But efficiency suffers "
                "{output_per_person} compared to specialists. Revenue grows modestly {mrr_month_6}, product "
                "advances slowly {product_velocity}. Founders debate: do we need specialists {hire_specialist_debate} "
                "or stay scrappy longer {maintain_generalist_approach}? Month 7-9: Scrappiness creates strong "
                "culture {team_cohesion} and capital efficiency {burn_rate_month_9}, but scaling challenges "
                "emerge {specialist_skill_gaps}. Some generalists burn out {employee_burnout}, others thrive "
                "{high_performers}. Month 10-12: Can generalist approach reach $100K MRR {revenue_month_12} "
                "while preserving long runway {months_runway_remaining}? Team morale {morale_score} and "
                "founder stress {founder_stress_level} emerge from workload distribution."
            ),
            entities=EntityConfig(
                count=2,
                types=["human"]
            ),
            timepoints=CompanyConfig(
                count=12,
                resolution="month"
            ),
            temporal=TemporalConfig(mode=TemporalMode.PEARL),
            world_id="timepoint_staffing_and_growth",
            metadata={
                "analysis_type": "team_scaling_strategy_comparison",
                "timelines": [
                    {
                        "id": "timeline_a_sales_first",
                        "structure": "Sales-first hiring (SDR, AE, CSM)",
                        "hypothesis": "Prioritizing sales hires accelerates revenue but risks technical debt accumulation and product quality degradation"
                    },
                    {
                        "id": "timeline_b_product_first",
                        "structure": "Product-first hiring (engineers, designers, technical leads)",
                        "hypothesis": "Building strong product foundation enables long-term scale but may burn cash before achieving commercial traction"
                    },
                    {
                        "id": "timeline_c_leadership_first",
                        "structure": "Leadership-first hiring (experienced VPs and executives)",
                        "hypothesis": "Executive leverage multiplies team output but high cost and cultural mismatch risk can backfire in early-stage startups"
                    },
                    {
                        "id": "timeline_d_generalist_scrappy",
                        "structure": "Generalist-scrappy hiring (versatile operators, no specialists)",
                        "hypothesis": "Capital-efficient generalists extend runway and build culture but lack of specialization limits scaling velocity"
                    }
                ],
                "key_questions": [
                    "Which hiring strategy achieves the best balance of revenue growth and capital efficiency?",
                    "How do early hiring decisions affect company culture and team cohesion over 12 months?",
                    "Can sales-first hiring overcome technical debt fast enough to avoid churn problems?",
                    "Does product-first hiring enable product-led growth or just burn runway?",
                    "When does executive hiring create leverage vs bureaucracy in early-stage startups?",
                    "Can generalist teams scale to $100K+ MRR or do they hit specialist skill gaps?",
                    "How do different hiring strategies affect founder stress, time allocation, and satisfaction?",
                    "Which approach creates the strongest Series A positioning after 12 months?"
                ],
                "emergent_format": True,
                "uses_profile_system": True,
                "mechanisms": ["M3_branching", "M10_scene_analysis", "M14_circadian_rhythm", "M15_prospection"],
                "initial_conditions": {
                    "starting_capital": 800000,
                    "current_mrr": 30000,
                    "team_size": 2,
                    "hiring_budget": 400000,
                    "monthly_burn": 25000,
                    "months_since_founding": 8
                }
            }
        )

    @classmethod
    def timepoint_founder_personality_archetypes(cls) -> "SimulationConfig":
        """
        Comprehensive founder personality × governance structure matrix.

        Test 6 founder personality archetypes × 2 governance structures (optimal vs suboptimal).
        Demonstrates which personalities need which governance models. Based on observed patterns
        across technology companies:
        - Charismatic Engineer + Operational Executive (defense tech)
        - Technical Visionary + COO (aerospace manufacturing)
        - Design Perfectionist + Strategic Advisor (hospitality tech)
        - Young Technical Founder + Experienced Executive (social platform)
        - Technical Co-founders + Professional CEO (search/advertising)
        - Visionary Founder fired then rehired with governance changes (consumer electronics)

        Twelve parallel timelines testing personality × governance fit.
        """
        return cls(
            scenario_description=(
                "**October 2024: Founder Personality Diagnosis** - Founder A has the technical prototype. "
                "But which governance structure fits their personality? This simulation tests 6 founder archetypes, "
                "each exploring different governance structures (12 branching timelines). Track to Series A negotiation "
                "(18-24 months). Agents must make all structural and equity decisions—outcomes emerge from personality-driven negotiations."
                "\n\n"
                "**ARCHETYPE 1: CHARISMATIC VISIONARY** "
                "\n"
                "Personality: Technical genius, media darling, polarizing, relentless. Brilliant but creates controversies. "
                "Naturally drawn to spotlight and vision work. Struggles with operational details. "
                "\n"
                "Timeline 1A: Founder A and Founder B negotiate governance structure. Founder A argues they should lead technical "
                "vision and fundraising (their natural strengths). Founder B argues for taking operational leadership role. "
                "They must negotiate: Who is CEO? Who is Chief Scientist/CTO? What equity split {equity_founder_a}, {equity_founder_b} "
                "reflects their contributions? Month 6: Founder A will likely pursue media opportunities—how does this affect "
                "operations {mrr_month_6}? Month 12: If Founder A creates controversies (likely given personality), how does "
                "governance structure handle this {crisis_resolution_month_12}? Revenue outcome {mrr_month_12}. Month 18: "
                "Series A investors evaluate structure and performance—they make offer {series_a_amount} at {valuation_1a}. "
                "\n"
                "Timeline 1B: Founder A and Founder B explore different governance. Founder A might argue to be CEO themselves {equity_founder_a_1b}. "
                "How do negotiations proceed? Do they reach agreement or impasse? Month 4-8: Track operational execution given "
                "structure chosen {operational_health}. Month 12: Has structure created problems {governance_crisis}? Revenue "
                "{mrr_month_12_1b} reflects decisions made. Relationship health {relationship_quality_1b} emerges from fit between "
                "personality and structure. "
                "\n\n"
                "**ARCHETYPE 2: DEMANDING GENIUS** "
                "\n"
                "Personality: Product-obsessed, chaotic, brilliant, exhausting. Makes impossible demands. Fires people impulsively. "
                "Drives teams hard. Needs someone with thick skin who can translate chaos into execution. "
                "\n"
                "Timeline 2A: Founder A and Founder B negotiate. Given Founder A's demanding nature, what role should they hold {title_founder_a}? "
                "Founder B evaluates: can they handle being Founder A's #2 and absorbing their chaos? They negotiate equity {equity_founder_a_2a}, "
                "{equity_founder_b_2a} and decision-making authority. Month 6: Founder A will likely make impossible demands {demands_month_6}. "
                "How does Founder B respond {founder_b_response}? Can they deliver partial results or does relationship fracture? Revenue "
                "{mrr_month_6_2a}. Month 12: Founder A may fire someone impulsively {firing_event}—Founder B must decide how to handle this. "
                "Revenue {mrr_month_12_2a}, team morale {morale_2a}, relationship strength {relationship_2a} all emerge from these "
                "interactions. Month 18: Series A evaluation {series_a_amount_2a} at {valuation_2a}. "
                "\n"
                "Timeline 2B: Different governance structure. What if Founder A doesn't have a strong #2 to absorb chaos {structure_2b}? "
                "Track: employee turnover {turnover_rate}, engineering retention {retention_health}, cultural toxicity {culture_score}. "
                "Revenue outcome {mrr_month_12_2b} emerges from structural choices. "
                "\n\n"
                "**ARCHETYPE 3: DESIGN PERFECTIONIST** "
                "\n"
                "Personality: User experience obsessed, vulnerable leadership style, product vision exceptional. Will obsess over "
                "details. Less comfortable with hard business decisions. Naturally gravitates toward product work. "
                "\n"
                "Timeline 3A: Founder A and Founder B negotiate roles. Founder A will naturally want to own product/design {role_founder_a_3a}. "
                "Founder B must decide: take business operations role or push for different structure? Equity negotiation {equity_founder_a_3a}, "
                "{equity_founder_b_3a}. Month 6: Product quality {product_quality_month_6} will likely be high given Founder A's obsession. "
                "But is anyone driving sales {sales_health}? Revenue {mrr_month_6_3a}. Month 12: Has Founder A's perfectionism created "
                "product excellence {product_excellence} or paralysis {shipping_velocity}? Did Founder B build business operations "
                "{ops_health_3a}? Revenue {mrr_month_12_3a}. Series A: Investors evaluate product vs business balance {series_a_amount_3a} "
                "at {valuation_3a}. "
                "\n"
                "Timeline 3B: Founder A tries to handle everything themselves {structure_3b}. Month 6: Track where Founder A spends time "
                "{time_allocation}. Given personality, likely obsessing on product—who drives sales {sales_month_6_3b}? Revenue "
                "{mrr_month_6_3b}. Month 12: Product quality {product_quality_3b} vs customer acquisition {customer_growth_3b} tradeoff "
                "emerges. Revenue {mrr_month_12_3b}. "
                "\n\n"
                "**ARCHETYPE 4: YOUNG GROWER** "
                "\n"
                "Personality: Technical genius, initially awkward in business situations, learns extremely fast, wants to maintain "
                "control. Uncomfortable with being sidelined. Can grow into CEO role but needs coaching. "
                "\n"
                "Timeline 4A: Founder A and Founder B negotiate. Founder A wants to stay CEO {founder_a_wants_ceo} but knows they need to grow. "
                "Founder B must decide: take COO/coach role {founder_b_role_4a} or push for different structure? Equity {equity_founder_a_4a}, "
                "{equity_founder_b_4a}. Month 6: Track Founder A's learning curve {ceo_skill_growth}. In sales calls, are they improving "
                "{sales_performance} with Founder B coaching? Revenue {mrr_month_6_4a}. Month 12: Has Founder A developed CEO capabilities "
                "{ceo_capability_month_12} through experience + coaching? Revenue {mrr_month_12_4a}, relationship {relationship_4a}. "
                "Series A: Investors evaluate young founder's growth trajectory {series_a_amount_4a} at {valuation_4a}. "
                "\n"
                "Timeline 4B: Board considers hiring experienced 'adult' CEO {hire_adult_ceo_decision}. If hired: What equity does "
                "hired CEO get {equity_hired_ceo}? How does Founder A respond to being sidelined {founder_a_reaction}? Month 6-10: Track "
                "Founder A-hired CEO relationship {founder_ceo_tension}. Does hired CEO understand technical vision {ceo_tech_understanding}? "
                "Does Founder A undermine CEO authority {undermining_behavior}? Month 14: Relationship outcome {relationship_crisis_month_14}, "
                "potential CEO departure {ceo_quit_scenario}. "
                "\n\n"
                "**ARCHETYPE 5: DUAL TECH FOUNDERS** "
                "\n"
                "Personality: Two technical geniuses with complementary skills. Neither naturally gravitates toward CEO role. "
                "Both prefer building to operating. Risk of decision paralysis with two equals. "
                "\n"
                "Timeline 5A: Founder A (product genius) and Founder B (technical genius) negotiate structure {structure_decision_5a}. "
                "Do they hire a CEO {hire_ceo_decision}? If yes: equity split {equity_founder_a_5a}, {equity_founder_b_5a}, {equity_hired_ceo_5a}. "
                "How much authority do they give hired CEO {ceo_authority}? Month 6: If hired CEO, are they building while CEO sells "
                "{division_of_labor}? Technical progress {tech_progress}, sales progress {sales_progress}, revenue {mrr_month_6_5a}. "
                "Month 12: Is hired CEO respecting founders' technical authority {mutual_respect}? Are founders respecting CEO's "
                "business authority {founder_respect}? Revenue {mrr_month_12_5a}. Series A: Three-way leadership dynamics "
                "{leadership_health}, investor confidence {series_a_amount_5a} at {valuation_5a}. "
                "\n"
                "Timeline 5B: Founder A and Founder B try to co-CEO {co_ceo_structure}. Equity {equity_founder_a_5b}, {equity_founder_b_5b}. "
                "Month 4: Track decision-making speed {decision_speed}. Who makes final calls {decision_authority}? Month 8: External "
                "perception—do customers see two CEOs as confusion {customer_confusion}? Month 12: Investor perception {investor_concern}, "
                "revenue {mrr_month_12_5b}. Does structure work or create paralysis {structure_effectiveness_5b}? "
                "\n\n"
                "**ARCHETYPE 6: RETURNED FOUNDER** "
                "\n"
                "Personality: Visionary but initially immature. Strong opinions, difficulty compromising. Likely to have board conflicts. "
                "Could get fired, could mellow during absence, could return seasoned. Long-term arc. "
                "\n"
                "Timeline 6A: Founder A starts as CEO {equity_founder_a_initial_6a}. Month 1-12: Track board relationship {board_tension}. "
                "Founder A's immaturity will likely create conflicts {conflict_events}. Month 14: Board must decide {board_decision_month_14}. "
                "If fired: hired CEO period Month 15-30. Track: company growth without founder {growth_without_founder}, loss of vision "
                "{vision_loss}. Does Founder A mature during absence {founder_maturity}? Month 30: If Founder A returns, negotiate new deal "
                "{equity_founder_a_return}, {title_return}. Track Series B outcome {series_b_amount} at {valuation_6a}. Relationship "
                "recovery {relationship_recovery}. "
                "\n"
                "Timeline 6B: Founder A fired, different outcome {alternative_path_6b}. Does Founder A return or not {return_decision}? If "
                "not: track hired CEO performance {hired_ceo_performance}, vision execution {vision_without_founder}, long-term "
                "outcome {outcome_6b}. "
                "\n\n"
                "**CRITICAL: All equity percentages, revenue numbers, valuations, relationship scores, and specific outcomes must "
                "emerge from agent negotiations and decisions. Personality traits shape (but do not dictate) behavior. Structural "
                "milestones are mandated (MUST negotiate equity by Month 1, MUST reach Series A decision by Month 18), but specific "
                "terms are non-deterministic. Agents can counter-negotiate, make concessions, or walk away from deals.** "
                "\n\n"
                "Track 24 timepoints (24 months) across 12 timelines. Demonstrates M12 (branching personality types), "
                "M13 (relationship health varies by personality-structure fit), M8 (stress from personality-structure "
                "mismatch), M7 (causal chains: personality → structure → execution → outcome), M11 (governance conflicts "
                "and difficult conversations)."
            ),
            world_id="timepoint_personality_archetypes",
            entities=EntityConfig(
                count=8,  # Founder A + Founder B + hired CEO (some timelines) + COO + investors + board + advisors
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=24,  # 24 months to cover various personality trajectories
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # 12 parallel timelines (6 personalities × 2 structures)
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,  # Governance conflicts, personality clashes
                include_relationships=True,  # M13: relationship health by personality fit
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "founder_personality_governance_fit_matrix",
                "personalities_tested": 6,
                "timelines_total": 12,
                "profile_refs": [
                    "charismatic_visionary",
                    "demanding_genius",
                    "design_perfectionist",
                    "young_grower",
                    "dual_tech_founders",
                    "returned_founder"
                ],
                "key_questions": [
                    "Which governance structures emerge from each personality type?",
                    "How do equity negotiations unfold based on founder traits?",
                    "What role should each founder take based on their archetype?",
                    "How do personality mismatches affect company outcomes?",
                    "When should founders hire operational leaders vs stay in charge?"
                ],
                "mechanisms_featured": [
                    "M12_branching_six_personality_types",
                    "M13_relationship_health_personality_structure_fit",
                    "M8_embodied_stress_from_mismatched_governance",
                    "M7_causal_chains_personality_to_outcome",
                    "M11_governance_conflicts_difficult_conversations"
                ],
                "key_insight": "Founder personality determines optimal governance—no one-size-fits-all structure",
                "meta_lesson": "Personality-structure fit predicts success better than equity split alone",
                "emergent_format": True,
                "uses_profile_system": True
            }
        )

    @classmethod
    def timepoint_charismatic_founder_archetype(cls) -> "SimulationConfig":
        """
        Charismatic visionary founder archetype: Technical genius + media darling + operational CEO.

        Founder A is a technical genius and media darling. Brilliant, polarizing, creates buzz but also
        controversies. Three governance experiments: (A) Founder as Chief Scientist + Founder B as
        Operational CEO (optimal), (B) Founder tries to CEO themselves (disaster), (C) Founder as
        Chairman + Hired external CEO (board tension). Demonstrates M12 (branching), M13 (relationship
        health), M8 (stress), M11 (governance conflicts).
        """
        return cls(
            scenario_description=(
                "**October 2024: The Charismatic Founder Dilemma** - Founder A is a technical genius. At 28, "
                "they've built Company (17 mechanisms, 95% cost reduction). They're brilliant, charismatic, "
                "a media darling. TechCrunch covers them extensively. VCs are intrigued. But "
                "Founder A is also polarizing—tweets controversial takes, burns bridges, thrives on conflict. Founder B "
                "(co-founder) asks: 'Should you be CEO, or should we find an operator?' Three governance experiments where "
                "agents decide structure and outcomes emerge from personality dynamics."
                "\n\n"
                "**Timeline A: Founder as Chief Scientist + Operational CEO Structure** "
                "\n"
                "Founder A and Founder B negotiate governance structure. Founder A argues for leading technical vision, R&D, fundraising, "
                "and media (their natural strengths). Founder B argues for operational leadership—sales, hiring, P&L, day-to-day "
                "execution. They must decide: titles {title_founder_a}, {title_founder_b}, equity split {equity_founder_a}, "
                "{equity_founder_b}, {equity_esop_a}, {equity_investors_a}, and authority boundaries {authority_boundaries}. "
                "\n"
                "Month 1: Formation negotiations. Founder A will naturally want visionary role without ops burden. Founder B must "
                "negotiate real authority—no undermining with team {authority_agreement}. Do they reach clear boundaries "
                "{boundary_clarity} or leave ambiguity that creates future conflict? "
                "\n"
                "Month 3: Founder A will likely pursue media opportunities (keynotes, conferences) given personality {media_engagement_month_3}. "
                "This generates inbound leads {inbound_leads}. Founder B must convert leads to pilots {pilots_signed}. Revenue "
                "{mrr_month_3_a}. Do their complementary skills work or create friction {skills_fit_month_3}? "
                "\n"
                "Month 6: Founder A's media presence continues {media_activity_month_6}. Given their polarizing nature, they will "
                "likely make controversial statements {controversial_statements}. How do customers/investors react {market_reaction}? "
                "Founder B must close deals despite (or because of) Founder A's brand {deals_closed_month_6}. Revenue {mrr_month_6_a}. "
                "\n"
                "Month 9: Founder A continues generating buzz but also controversy {controversy_month_9}. Does Founder B successfully "
                "shield team from drama {team_shield_success} while maintaining execution {execution_health}? Revenue {mrr_month_9_a}. "
                "\n"
                "Month 12: Crisis point. If Founder A creates major controversy {crisis_event_month_12}, how does governance structure "
                "handle it? Does Founder B defend Founder A to board {founder_b_defense} or distance themselves {founder_b_distance}? Board "
                "response {board_reaction}. Revenue {mrr_month_12_a}, relationship health {relationship_health_month_12_a}. "
                "\n"
                "Month 15: Series A pitch preparation. Founder A and Founder B must coordinate pitch {pitch_coordination}. Founder A "
                "pitches vision {vision_pitch_quality}, Founder B pitches metrics {metrics_pitch_quality}. Do VCs see complementary "
                "team or misalignment {vc_team_perception}? "
                "\n"
                "Month 18: Series A negotiation. Investors make offer {series_a_amount_a} at {valuation_a} based on team "
                "dynamics, revenue trajectory, and perceived risk. Do Founder A and Founder B accept {deal_acceptance}? Final relationship "
                "health {relationship_health_month_18_a}, outcome {outcome_a}. "
                "\n\n"
                "**Timeline B: Founder Tries to CEO** "
                "\n"
                "Different governance negotiation. Founder A argues to be CEO themselves {founder_a_argument_ceo}. Founder B challenges: "
                "'Are you sure? You hate ops' {founder_b_challenge}. Does Founder A insist {founder_a_insistence}? Equity negotiation "
                "{equity_founder_a_b}, {equity_founder_b_b}. Role clarity {role_founder_b_b}. "
                "\n"
                "Month 1-3: If Founder A is CEO, track time allocation {time_allocation_founder_a}. Given personality, they will "
                "naturally gravitate toward media/product {natural_gravitation}. Who handles operations {ops_owner}? Does "
                "Founder B have authority to hire {hiring_authority}? "
                "\n"
                "Month 4: Founder A's media presence {media_presence_month_4} vs operational execution {operational_execution_month_4}. "
                "Revenue {mrr_month_4_b}, pilot customers {pilots_month_4}. Founder B frustration level {founder_b_frustration}. "
                "\n"
                "Month 6: Revenue trajectory {mrr_month_6_b}. Investor questions {investor_concerns}: 'Who's running the "
                "business?' Founder A's response {founder_a_response_investors}. Internal tension {internal_tension_month_6}. "
                "\n"
                "Month 8: Critical point. Has sales execution happened {sales_execution}? Board meeting discussion {board_meeting_month_8}. "
                "Does board intervene {board_intervention}? Founder B demoralization {founder_b_morale}. Revenue {mrr_month_8_b}. "
                "\n"
                "Month 10: If board forces restructuring {board_restructuring_decision}, how does Founder A react {founder_a_reaction_demotion}? "
                "Negotiation of new structure {new_structure_negotiation}. Relationship damage {relationship_health_month_10_b}. "
                "\n"
                "Month 12: Post-restructuring dynamics {post_restructure_dynamics}. Founder A engagement level {founder_a_engagement}. "
                "Revenue {mrr_month_12_b}, company health {company_health_month_12}. "
                "\n"
                "Month 15: Founder A decision point {founder_a_decision_stay_or_quit}. If quits, impact on company {impact_founder_a_departure}. "
                "Final outcome {outcome_b}. "
                "\n\n"
                "**Timeline C: Founder as Chairman + Hired External CEO** "
                "\n"
                "Third governance option. Board suggests hiring external CEO {board_suggestion_external_ceo}. Founder A and Founder B "
                "must decide: accept external CEO {accept_external_ceo}, equity split {equity_founder_a_c}, {equity_ceo_hired_c}, "
                "{equity_founder_b_c}. Hire external CEO (ex-big tech VP) or different profile {ceo_candidate_chosen}. "
                "\n"
                "Month 1: Initial structure {initial_structure_c}. Founder A's title {founder_a_title_c}, authority boundaries "
                "{authority_boundaries_c}. Does Founder A truly give external CEO autonomy {autonomy_granted} or keep control {founder_control_retained}? "
                "\n"
                "Month 3: External CEO makes first major decisions {ceo_first_decisions}. Does Founder A agree or privately disagree "
                "{founder_a_agreement_level}? If disagrees, do they voice concerns {founder_a_voices_concerns} or stay silent {founder_a_stays_silent}? "
                "\n"
                "Month 5: If external CEO's decisions don't match Founder A's vision {strategy_misalignment}, tension builds {tension_level_month_5}. "
                "Revenue {mrr_month_5_c}, burn rate {burn_rate_month_5}, runway {runway_month_5}. Product-market fit {pmf_status}. "
                "\n"
                "Month 6: If Founder A vents frustration publicly {public_frustration}, everyone knows it's about external CEO {subtext_clarity}. "
                "External CEO response {ceo_response_to_undermining}. Escalation {conflict_escalation}. "
                "\n"
                "Month 8: Board meeting crisis {board_meeting_crisis}. Founder A criticizes external CEO {founder_a_criticism}, external CEO defends "
                "authority {ceo_defense}. Board must choose side {board_sides_with}. Relationship health {relationship_health_month_8_c}. "
                "\n"
                "Month 10: Does external CEO stay or quit {ceo_decision_stay_or_quit}? If quits, reason {quit_reason}. Board response "
                "{board_blames}. "
                "\n"
                "Month 12: Emergency restructuring {emergency_restructure}. New CEO decision {new_ceo_decision}. Revenue "
                "{mrr_month_12_c}, relationship damage {relationship_damage_c}, time wasted {time_wasted}. "
                "\n"
                "Month 18: Series A outcome after messy transition {series_a_amount_c} at {valuation_c}. Board governance "
                "changes {board_governance_changes}. Final outcome {outcome_c}. "
                "\n\n"
                "**CRITICAL: All equity splits, revenue numbers, relationship scores, decisions (stay/quit/hire/fire), board "
                "actions, and outcomes are non-deterministic. Personality traits (charismatic, polarizing, media-driven, "
                "conflict-prone) shape but do not dictate behavior. Structural milestones are mandated (MUST negotiate governance "
                "by Month 1, MUST handle crisis by Month 12, MUST reach Series A decision by Month 18), but specific choices "
                "and outcomes emerge from agent negotiations.** "
                "\n\n"
                "Track 20 timepoints (20 months). Demonstrates M12 (three governance structures), M13 (relationship health "
                "emerges from personality-structure fit), M8 (stress from role conflict), M11 (governance conflicts: founder "
                "vs CEO vs board), M7 (causal chains: governance → culture → execution → outcome)."
            ),
            world_id="timepoint_charismatic_founder_archetype",
            entities=EntityConfig(
                count=7,  # Founder A + Founder B + hired CEO (timeline C) + 2 board members + 2 investors
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG,  # Governance conflicts need dialog
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=20,  # 20 months to Series A
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Three timelines (optimal, disaster, tension)
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,  # Critical: founder-CEO conflicts, board meetings
                include_relationships=True,  # M13: relationship health across structures
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "charismatic_founder_governance_archetype",
                "profile_ref": "charismatic_visionary",
                "timelines": [
                    {
                        "id": "timeline_a_chief_scientist_operational_ceo",
                        "structure": "Founder Chief Scientist + Operational CEO",
                        "hypothesis": "Clear role boundaries enable charismatic founder's genius while operational leader shields from chaos"
                    },
                    {
                        "id": "timeline_b_founder_tries_to_ceo",
                        "structure": "Founder as CEO (Wrong Role)",
                        "hypothesis": "Media-focused founder in CEO role neglects operations, leading to board intervention"
                    },
                    {
                        "id": "timeline_c_chairman_hired_ceo",
                        "structure": "Executive Chairman + Hired External CEO",
                        "hypothesis": "Charismatic founder undermines external CEO when vision misaligns"
                    }
                ],
                "key_questions": [
                    "What governance structure emerges from charismatic, polarizing founder personality?",
                    "How do media opportunities affect operational execution?",
                    "Can charismatic founders delegate authority to external CEOs?",
                    "What role boundaries prevent conflict between vision and operations?",
                    "How does founder personality affect Series A outcomes?"
                ],
                "mechanisms_featured": [
                    "M12_branching_three_governance_structures",
                    "M13_relationship_health_personality_structure_fit",
                    "M8_embodied_stress_from_role_conflict",
                    "M11_founder_CEO_board_conflicts",
                    "M7_causal_chains_governance_to_execution_to_outcome"
                ],
                "key_insight": "Charismatic founders need 'Chief Scientist' title + operational CEO to unlock genius",
                "meta_lesson": "Media-darling founders are liabilities as CEOs but assets as Chief Scientists with boundaries",
                "emergent_format": True,
                "uses_profile_system": True
            }
        )

    @classmethod
    def timepoint_demanding_genius_archetype(cls) -> "SimulationConfig":
        """
        Demanding genius CEO archetype: Product-obsessed genius + COO "fort holder".

        Founder A is a demanding genius—product-obsessed, chaotic, brilliant, exhausting.
        They need someone who can "hold down the fort": absorb chaos, translate vision into execution,
        have thick skin. Three experiments: (A) CEO + Fort-Holder COO (optimal operational executor model),
        (B) CEO without strong #2 (chaos, turnover, disaster), (C) CEO + Weak COOs (fires 3 in 2 years).
        Demonstrates M12 (branching), M13 (relationship), M8 (COO stress), M15 (COO deciding to stay/quit).
        """
        return cls(
            scenario_description=(
                "**October 2024: The Demanding Genius** - Founder A is a product genius. Obsessive, demanding, "
                "brilliant. They have impossible standards, change direction constantly, fire people mid-project. "
                "Investors call them 'extraordinarily intense.' Their technical vision is unmatched—Company's "
                "17 mechanisms are architectural perfection. But they're exhausting to work with. Founder B asks: "
                "'Do you need someone to hold down the fort while you do your chaos magic?' Three governance experiments "
                "where agents decide structure, and outcomes (firings, quits, morale, revenue) emerge from personality dynamics."
                "\n\n"
                "**Timeline A: CEO + Fort-Holder COO Structure (Testing Operational Executor Model)** "
                "\n"
                "Founder A and Founder B negotiate. Founder A will be CEO {equity_founder_a_a}. Founder B proposes COO/President role "
                "{equity_founder_b_a}. They must agree on equity, ESOP pool {esop_a}, investor allocation {investors_a}, and "
                "authority boundaries {authority_boundaries_a}. "
                "\n"
                "Founder B's Personality: High EQ, thick skin, unflappable, translates chaos into execution, absorbs stress. "
                "Critical question: Can Founder B handle being fort holder for demanding genius Founder A? "
                "\n"
                "Month 1: Founder A makes explicit ask {founder_a_fort_holder_ask}: 'I need you to be my operational fort-holder. I'm going to be "
                "impossible, and you're going to make it work.' Does Founder B accept {founder_b_acceptance}? What terms {deal_terms}? "
                "\n"
                "Month 3: Founder A makes impossible deadline demand {founder_a_deadline_demand}. Realistically how long {realistic_timeline}? "
                "Team reaction {team_panic_level}. Does Founder B intervene {founder_b_intervention}? How does they translate Founder A's "
                "demand {founder_b_translation}? Team execution {team_delivery}. Founder A's reaction to partial delivery {founder_a_reaction_delivery}. "
                "Revenue {mrr_month_3_a}. "
                "\n"
                "Month 6: Founder A's demanding nature likely leads to friction {friction_event_month_6}. Does they fire someone "
                "{founder_a_fires_someone}? If yes: customer impact {customer_impact}, Founder B response {founder_b_salvage_attempt}. "
                "Does Founder B successfully shield company {shield_success}? Revenue {mrr_month_6_a}. "
                "\n"
                "Month 9: Founder A pivots product strategy {pivot_number} time this year. Engineering team exhaustion {team_exhaustion_level}. "
                "Does Founder B push back on Founder A {founder_b_pushback}? Does Founder A trust Founder B enough to accept delay {founder_a_trust_level}? "
                "Team recovery {team_recovery_granted}. Revenue {mrr_month_9_a} despite chaos. "
                "\n"
                "Month 9 CRITICAL DECISION POINT (M15): Founder B models stay-or-quit decision {founder_b_stay_or_quit_prospection}. "
                "His stress level {founder_b_stress_month_9}, their sense of impact {founder_b_impact_perception}, relationship with "
                "Founder A {relationship_quality_month_9}. Does they decide to stay {founder_b_decision_stay}? Reasoning {founder_b_reasoning}. "
                "\n"
                "Month 12: Team morale {team_morale_month_12} reflects Founder B's buffering effectiveness. Engineers' perception "
                "of Founder B {engineer_marcus_perception}. Founder A's perception of Founder B {founder_a_marcus_perception}. Investor "
                "perception {investor_perception_structure}. Revenue {mrr_month_12_a}. "
                "\n"
                "Month 15: Series A pitch preparation. Founder A's vision pitch quality {founder_a_vision_pitch}, Founder B's execution "
                "pitch quality {founder_b_execution_pitch}. VC perception of team dynamics {vc_team_dynamics_perception}. "
                "\n"
                "Month 18: Series A negotiation. Investors make offer {series_a_amount_a} at {valuation_a}. Founder B's equity "
                "{founder_b_equity_final} reflects their value. Relationship health {relationship_health_month_18_a}, revenue "
                "{mrr_month_18_a}. "
                "\n"
                "Month 24: Long-term outcome. Revenue {mrr_month_24_a}, team size {team_size_month_24}, growth trajectory "
                "{growth_trajectory}. Founder B's cumulative stress over 2 years {founder_b_cumulative_stress} (M8 tracking). "
                "Founder A's rare gratitude moment {founder_a_gratitude} if relationship succeeded. Final outcome {outcome_a}, "
                "valuation trajectory {valuation_trajectory_a}. "
                "\n\n"
                "**Timeline B: CEO Without Strong #2** "
                "\n"
                "Different structure negotiation. Founder A is CEO {equity_founder_a_b}, Founder B is CTO {equity_founder_b_b}. Founder B "
                "has technical role but lacks authority to buffer Founder A's chaos {founder_b_authority_b}. "
                "\n"
                "Month 1: Initial agreement {initial_agreement_b}. Founder A's view of operations {founder_a_ops_plan}: 'We'll "
                "figure it out.' Founder B concern level {founder_b_concern_b}. "
                "\n"
                "Month 3: Founder A's chaos is unmanaged {chaos_level_month_3}. They makes impossible demand {demand_month_3_b}. "
                "Team says impossible {team_pushback}. Does Founder A fire people {founder_a_fires_month_3}? If yes, how many "
                "{firings_count}? Team morale impact {team_morale_month_3_b}. Founder B can't intervene (lacks COO authority) "
                "{founder_b_intervention_blocked}. "
                "\n"
                "Month 4: Team turnover rate {turnover_rate_month_4}. Why do engineers quit {quit_reasons}? Who stays "
                "{who_remains}? Revenue {mrr_month_4_b}. Sales process existence {sales_process_status}. "
                "\n"
                "Month 6: Founder B desperate conversation {founder_b_plea}: Begs Founder A to hire COO. Founder A's response {founder_a_response_coo_plea}. "
                "Does they accept need for COO {founder_a_accepts_coo} or refuse {founder_a_refuses}? If refuses, their reasoning "
                "{founder_a_reasoning_refuse}. "
                "\n"
                "Month 8: Cumulative turnover {cumulative_turnover_month_8}. Remaining team size {remaining_team_size}. "
                "Product quality {product_quality_month_8} vs company health {company_health_month_8}. Revenue {mrr_month_8_b}. "
                "Investor nervous level {investor_concern_month_8}. "
                "\n"
                "Month 10: Founder B breaking point {founder_b_breaking_point}. Does Founder B quit {founder_b_quits_month_10}? If yes, "
                "impact on Founder A {impact_on_sarah}. Does Founder A try to retain him {founder_a_retention_attempt}? Founder A alone scenario "
                "{founder_a_alone_dynamics}. "
                "\n"
                "Month 12: Company state {company_state_month_12}. Revenue {mrr_month_12_b}. If Founder A finally tries to hire "
                "COO {coo_hire_attempt_late}, does anyone accept {candidate_acceptance} given their reputation {reputation_damage}? "
                "Series A outcome {series_a_outcome_b}. Final outcome {outcome_b}. "
                "\n\n"
                "**Timeline C: CEO + COO Carousel (Multiple COO Attempts)** "
                "\n"
                "Founder A is CEO {equity_founder_a_c}. They recognizes need for COO but struggles to find right fit. "
                "\n"
                "Month 1: Founder A hires Jamie as COO #1 {equity_jamie}. Jamie's background {jamie_background}, personality "
                "{jamie_personality}. Does Jamie have fort-holder traits {jamie_fort_holder_traits}? "
                "\n"
                "Month 3: Founder A makes demanding request {founder_a_demand_month_3_c}. Jamie's response {jamie_response}. If "
                "Jamie pushes back {jamie_pushback}, does this create friction {friction_sarah_jamie}? Does Founder A question "
                "fit {founder_a_questions_jamie}? "
                "\n"
                "Month 4: Jamie breaking point {jamie_stress_level}. Does Jamie quit {jamie_quits} or get fired {jamie_fired}? "
                "Reason {jamie_exit_reason}. Founder A's interpretation {founder_a_interpretation_jamie}. Time wasted {time_wasted_jamie}. "
                "\n"
                "Month 7: Founder A hires Taylor as COO #2 {equity_taylor}. Taylor's background {taylor_background}. Equity "
                "lower than Jamie {equity_decrease_signal}—desperation? Taylor's approach {taylor_management_style}. "
                "\n"
                "Month 9: Taylor tries to implement structure {taylor_process_attempts}. Founder A's reaction to process "
                "{founder_a_reaction_process}. Constant clashes {clash_frequency}. "
                "\n"
                "Month 11: Does Founder A fire Taylor {founder_a_fires_taylor} or does Taylor quit {taylor_quits}? Reason {taylor_exit_reason}. "
                "Revenue {mrr_month_11_c}. Cumulative time wasted {cumulative_time_wasted}. "
                "\n"
                "Month 14: Founder A hires Alex as COO #3 {equity_alex}. Even lower equity {equity_trend}—'scraping barrel'? "
                "Alex's traits {alex_traits}. Does Alex have thick skin {alex_resilience}? "
                "\n"
                "Month 18: Does Alex survive {alex_survives}? If yes, at what cost? Company culture damage {culture_damage_month_18}, "
                "team trust in leadership {leadership_trust}, revenue {mrr_month_18_c} vs potential. "
                "\n"
                "Month 24: Series B negotiation. Investor concerns about COO churn {investor_concern_churn}. Offer {series_b_amount_c} "
                "at {valuation_c}. Alex-Founder A relationship quality {relationship_health_alex_sarah}—transactional {transactional_vs_trust} "
                "or deep trust? Final outcome {outcome_c}, valuation impact {valuation_gap_vs_optimal}. "
                "\n\n"
                "**CRITICAL: All equity splits, revenue numbers, relationship scores, firing decisions, quit decisions, "
                "team morale, turnover rates, and outcomes are non-deterministic. Founder A's demanding personality shapes "
                "behavior (will naturally make impossible demands, will likely fire people, will likely create chaos) "
                "but agents decide specific actions. Founder B/COOs decide to stay or quit based on stress, impact, and "
                "relationship quality. Structural milestones are mandated (MUST negotiate structure by Month 1, MUST "
                "handle chaos events as they emerge, MUST reach Series A/B decision points), but specific outcomes emerge "
                "from agent dynamics.** "
                "\n\n"
                "Track 24 timepoints (2 years). Demonstrates M12 (three COO structures), M13 (relationship health emerges "
                "from fort-holder effectiveness), M8 (COO stress tracked—especially Founder B absorbing Founder A's chaos), M7 "
                "(causal chains: CEO demanding nature → COO resilience → team morale → execution → outcome), M15 (Month 9: "
                "Founder B/COOs model stay vs quit decisions through prospection), M11 (difficult conversations: impossible "
                "demands, firings, quit negotiations)."
            ),
            world_id="timepoint_demanding_genius_archetype",
            entities=EntityConfig(
                count=9,  # Founder A + Founder B + 3 COOs (timeline C) + 3 engineers + 2 investors
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG,
                animism_level=0
            ),
            timepoints=CompanyConfig(
                count=24,  # 2 years to Series B
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,  # Three timelines (optimal, disaster, carousel)
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,  # Founder A-COO conflicts, firing conversations
                include_relationships=True,  # M13: relationship health across timelines
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "demanding_genius_ceo_fort_holder_archetype",
                "profile_ref": "demanding_genius",
                "complementary_profile_ref": "operational_executor",
                "timelines": [
                    {
                        "id": "timeline_a_ceo_fort_holder_coo",
                        "structure": "CEO + Fort-Holder COO (Operational Executor Model)",
                        "hypothesis": "Fort-holder COO absorbs chaos, translates into execution, protects team, enables demanding genius"
                    },
                    {
                        "id": "timeline_b_ceo_no_strong_two",
                        "structure": "CEO Without Strong #2",
                        "hypothesis": "Without operational buffer, demanding CEO creates team exodus and company failure"
                    },
                    {
                        "id": "timeline_c_ceo_weak_coos_carousel",
                        "structure": "CEO + COO Carousel (Multiple COO Attempts)",
                        "hypothesis": "Wrong COO fit leads to churn, wasted time, and reduced valuation potential"
                    }
                ],
                "key_questions": [
                    "What COO traits enable survival with demanding genius CEO?",
                    "How does COO stress level affect stay/quit decisions (M15)?",
                    "What happens when demanding CEO lacks operational buffer?",
                    "How does COO churn affect company culture and valuation?",
                    "What equity split reflects fort-holder COO value?"
                ],
                "mechanisms_featured": [
                    "M12_branching_three_coo_structures",
                    "M13_relationship_health_fort_holder_effectiveness",
                    "M8_embodied_stress_coo_absorbs_chaos",
                    "M7_causal_chains_ceo_personality_to_coo_resilience_to_outcome",
                    "M15_prospection_coo_models_stay_vs_quit_decision",
                    "M11_difficult_conversations_firings_and_team_conflicts"
                ],
                "key_insight": "Demanding geniuses need 'fort holder' COOs with specific traits: thick skin, high EQ, chaos translation",
                "meta_lesson": "Fort-holder COO model unlocks demanding genius founders—significant equity reflects critical role",
                "emergent_format": True,
                "uses_profile_system": True
            }
        )

    # ============================================================================
    # PORTAL Mode Templates (Mechanism 17 - Backward Temporal Reasoning)
    # ============================================================================

    @classmethod
    def portal_presidential_election(cls) -> "SimulationConfig":
        """
        PORTAL mode: Presidential election backward simulation.

        Portal: Jane Chen elected President in 2040
        Origin: Jane Chen VP Engineering in 2025
        Goal: Find plausible career paths from tech → politics

        Demonstrates M17 (PORTAL mode backward inference), M15 (career prospection),
        M12 (alternate path analysis), M7 (causal chain validation).
        """
        return cls(
            scenario_description=(
                "Backward simulation from presidential election victory to tech career origin. "
                "Jane Chen wins 2040 presidential race with 326-212 electoral college victory, "
                "52.4% popular vote. Work backward to discover plausible paths from her 2025 position "
                "as VP Engineering at TechCorp startup (Series B, 150 employees). "
                "\n\n"
                "System generates multiple paths exploring different routes: early political entry "
                "(runs for city council 2027) vs gradual transition (book publication 2029, media "
                "presence), crisis response opportunities (tech regulation fight 2031 raises profile), "
                "network building strategies (VC connections → political donors), educational credibility "
                "(evening MBA 2028-2030 vs Kennedy School fellowship 2032). "
                "\n\n"
                "Each path scored for coherence: Can VP Engineering realistically pivot? Does timeline "
                "allow skill development? Are networks plausible? Forward validation ensures origin → portal "
                "makes causal sense. Pivot points identify critical decision moments where paths diverge most: "
                "year 2027 (stay in tech vs political entry), 2031 (crisis response), 2034 (campaign infrastructure)."
            ),
            world_id="portal_presidential_election",
            entities=EntityConfig(
                count=5,  # Jane Chen + mentor + rival politician + campaign manager + family member
                types=["human"],
                initial_resolution=ResolutionLevel.TRAINED
            ),
            timepoints=CompanyConfig(
                count=1,  # Placeholder - PORTAL mode generates backward states based on backward_steps
                resolution="year"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="Jane Chen elected President with 52.4% popular vote, 326 electoral votes, strong tech sector support",
                portal_year=2040,
                origin_year=2025,
                backward_steps=15,
                path_count=3,
                candidate_antecedents_per_step=5,
                exploration_mode="adaptive",
                coherence_threshold=0.7,
                llm_scoring_weight=0.35,
                historical_precedent_weight=0.20,
                causal_necessity_weight=0.25,
                entity_capability_weight=0.15
            ),
            outputs=OutputConfig(
                formats=["json", "markdown"],
                include_relationships=True,
                include_knowledge_flow=True
            ),
            metadata={
                "portal_type": "presidential_election",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M15_career_prospection",
                    "M12_alternate_path_analysis",
                    "M7_causal_chain_validation",
                    "M13_relationship_networks"
                ],
                "expected_paths": 3,
                "expected_pivot_points": "4-6",
                "career_transition": "tech_executive_to_president",
                "key_questions": [
                    "What minimum political experience enables presidential candidacy?",
                    "How does tech background affect campaign narrative?",
                    "What pivot points determine tech→politics feasibility?"
                ]
            }
        )

    @classmethod
    def portal_startup_unicorn(cls) -> "SimulationConfig":
        """
        PORTAL mode: Unicorn startup backward simulation.

        Portal: Company valued at $1B+ (unicorn) in 2030
        Origin: Two founders with idea, no funding in 2024
        Goal: Find plausible growth paths to unicorn status

        Demonstrates M17 (PORTAL), M13 (multi-entity synthesis), M8 (founder stress),
        M11 (fundraising dialogs), M15 (strategic planning).
        """
        return cls(
            scenario_description=(
                "Backward simulation from $1.2B Series C valuation to pre-seed founding moment. "
                "Company achieves unicorn status March 2030: $1.2B post-money, $120M ARR, 450 employees, "
                "strong unit economics (85% gross margin, 3.5x LTV/CAC). Work backward to April 2024 when "
                "two technical founders had vision but zero funding, no product, no customers. "
                "\n\n"
                "System explores multiple scaling paths: (A) Enterprise-first strategy (land Fortune 500 early, "
                "slow but steady $1M+ ACVs), (B) Viral PLG motion (100K users, convert to paid, expand upmarket), "
                "(C) Vertical domination (own healthcare vertical completely, then expand). Each path has different "
                "fundraising requirements (seed, A, B, C rounds at different milestones), hiring patterns "
                "(sales-heavy vs eng-heavy), burn rates, and risk profiles. "
                "\n\n"
                "Validation checks: Is growth rate sustainable? Do founders have credibility for strategy? "
                "Are market conditions plausible? Forward coherence ensures April 2024 → March 2030 arc makes sense. "
                "Pivot points: initial GTM choice (2024), product-market fit moment (2025-2026), Series A strategy "
                "(2026), expansion decision (2028)."
            ),
            world_id="portal_startup_unicorn",
            entities=EntityConfig(
                count=6,  # 2 founders + investor + key hire + customer + advisor
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG
            ),
            timepoints=CompanyConfig(
                count=1,  # Placeholder - PORTAL mode generates backward states based on backward_steps
                resolution="quarter"  # Quarterly milestones
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="$1.2B Series C valuation, $120M ARR, 450 employees, 85% gross margin",
                portal_year=2030,
                origin_year=2024,
                backward_steps=24,  # 6 years × 4 quarters
                path_count=3,
                candidate_antecedents_per_step=7,
                exploration_mode="adaptive",
                coherence_threshold=0.65,
                llm_scoring_weight=0.30,
                historical_precedent_weight=0.25,  # Strong historical precedent for unicorn paths
                causal_necessity_weight=0.25,
                entity_capability_weight=0.15
            ),
            outputs=OutputConfig(
                formats=["json", "jsonl", "markdown"],
                include_dialogs=True,  # Fundraising pitches crucial
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "portal_type": "unicorn_startup",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M13_multi_entity_synthesis",
                    "M8_founder_stress_burnout",
                    "M11_fundraising_dialog",
                    "M15_strategic_planning_prospection",
                    "M7_causal_milestone_chains"
                ],
                "expected_paths": 3,
                "expected_pivot_points": "5-8",
                "growth_strategies": ["enterprise_first", "plg_viral", "vertical_domination"],
                "key_milestones": ["pmf", "series_a", "series_b", "series_c"],
                "key_questions": [
                    "What GTM strategy enables unicorn trajectory?",
                    "How do funding rounds correlate with growth milestones?",
                    "What founder traits predict successful scaling?"
                ]
            }
        )

    @classmethod
    def portal_academic_tenure(cls) -> "SimulationConfig":
        """
        PORTAL mode: Academic tenure backward simulation.

        Portal: Dr. Martinez achieves tenure at top university in 2035
        Origin: Martinez completes PhD in 2025
        Goal: Find plausible research/publication paths to tenure

        Demonstrates M17 (PORTAL), M15 (career planning), M3 (knowledge accumulation),
        M14 (circadian research patterns), M13 (collaboration networks).
        """
        return cls(
            scenario_description=(
                "Backward simulation from tenure achievement to post-PhD starting point. "
                "Dr. Elena Martinez receives tenure notification April 2035 at prestigious research university: "
                "14 publications (5 first-author in top venues), $2.8M in grants, strong teaching reviews, "
                "established research group (3 postdocs, 5 PhD students), respected in field. Work backward "
                "to May 2025 when she completed PhD and started assistant professor position. "
                "\n\n"
                "System explores publication strategies: (A) High-volume incremental work (publish often, "
                "build citation count steadily), (B) High-impact moonshot approach (3-4 major papers in Nature/Science), "
                "(C) Balanced portfolio (mix of quick wins and ambitious long-term projects). Each strategy affects "
                "grant funding, collaboration patterns, teaching load negotiation, lab building timeline. "
                "\n\n"
                "Validation: Does publication rate align with tenure standards? Are grant amounts realistic for career stage? "
                "Is teaching/research balance sustainable? Forward check: May 2025 → April 2035 progression makes sense. "
                "Pivot points: first major grant (2027), key paper acceptance/rejection (2028), lab expansion decision (2030), "
                "tenure packet preparation (2033-2034)."
            ),
            world_id="portal_academic_tenure",
            entities=EntityConfig(
                count=5,  # Dr. Martinez + department chair + collaborator + student + competitor
                types=["human"],
                initial_resolution=ResolutionLevel.SCENE
            ),
            timepoints=CompanyConfig(
                count=1,  # Placeholder - PORTAL mode generates backward states based on backward_steps
                resolution="year"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="Tenure achieved: 14 publications, $2.8M grants, established research group",
                portal_year=2035,
                origin_year=2025,
                backward_steps=10,
                path_count=3,
                candidate_antecedents_per_step=4,
                exploration_mode="reverse_chronological",  # Simpler than startup - sequential progression
                coherence_threshold=0.75,  # Academic careers more predictable
                llm_scoring_weight=0.25,
                historical_precedent_weight=0.35,  # Strong historical patterns in academia
                causal_necessity_weight=0.20,
                entity_capability_weight=0.15
            ),
            outputs=OutputConfig(
                formats=["json", "markdown"],
                include_relationships=True,
                include_knowledge_flow=True
            ),
            metadata={
                "portal_type": "academic_tenure",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M15_career_planning_prospection",
                    "M3_knowledge_accumulation_publications",
                    "M14_circadian_research_patterns",
                    "M13_collaboration_networks"
                ],
                "expected_paths": 3,
                "expected_pivot_points": "3-5",
                "publication_strategies": ["high_volume", "high_impact", "balanced_portfolio"],
                "key_milestones": ["first_grant", "major_publication", "lab_establishment", "tenure_review"],
                "key_questions": [
                    "What publication strategy optimizes tenure probability?",
                    "How do teaching vs research allocations affect outcomes?",
                    "What role do collaborations play in tenure success?"
                ]
            }
        )

    @classmethod
    def portal_startup_failure(cls) -> "SimulationConfig":
        """
        PORTAL mode: Startup failure backward simulation.

        Portal: Company shuts down, founders broke in 2028
        Origin: Company raises seed round in 2024
        Goal: Find decision paths that led to failure (negative outcome)

        Demonstrates M17 (PORTAL), M12 (what-if scenarios), M8 (burnout),
        M13 (relationship breakdown), M15 (bad decisions).
        """
        return cls(
            scenario_description=(
                "Backward simulation from startup shutdown to promising seed round. "
                "August 2028: Company officially shuts down. Assets sold for $200K (barely covers severance). "
                "Founders personally broke after 4 years, relationships destroyed, team dispersed. Investors "
                "lost $3.2M. Work backward to January 2024 when company raised $1.2M seed from top-tier VC, "
                "strong team (technical founders + 3 engineers), working MVP, 50 beta users giving positive feedback. "
                "\n\n"
                "System explores failure paths: (A) Wrong market timing (built too early, market not ready), "
                "(B) Founder conflict (CEO-CTO relationship broke down month 18, paralysis), (C) Bad pivot "
                "(abandoned working product for shiny new idea, lost traction), (D) Ignored metrics (vanity metrics "
                "looked good, unit economics terrible). Each path shows warning signs, bad decisions, missed "
                "opportunities to course-correct. "
                "\n\n"
                "Validation: Are failure modes realistic? Do decision chains make sense? Could founders have "
                "caught issues earlier? Forward coherence: January 2024 → August 2028 failure trajectory is plausible. "
                "Pivot points: hiring mistake (mid-2024), ignored warning sign (2025), founder conflict (2026), "
                "failed rescue attempt (2027)."
            ),
            world_id="portal_startup_failure",
            entities=EntityConfig(
                count=5,  # 2 founders + investor + key employee who quit + customer who churned
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG
            ),
            timepoints=CompanyConfig(
                count=1,  # Placeholder - PORTAL mode generates backward states based on backward_steps
                resolution="quarter"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="Startup shuts down: $200K asset sale, founders broke, $3.2M investor loss",
                portal_year=2028,
                origin_year=2024,
                backward_steps=16,  # 4 years × 4 quarters
                path_count=4,  # More paths for failure modes
                candidate_antecedents_per_step=6,
                exploration_mode="adaptive",
                coherence_threshold=0.60,  # Lower threshold - failure paths often chaotic
                llm_scoring_weight=0.30,
                historical_precedent_weight=0.25,  # Many historical failure examples
                causal_necessity_weight=0.25,
                entity_capability_weight=0.15
            ),
            outputs=OutputConfig(
                formats=["json", "markdown"],
                include_dialogs=True,  # Crucial conflict conversations
                include_relationships=True,  # Relationship breakdown tracking
                export_ml_dataset=True
            ),
            metadata={
                "portal_type": "startup_failure",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M12_counterfactual_what_ifs",
                    "M8_founder_burnout_stress",
                    "M13_relationship_breakdown",
                    "M15_bad_decision_prospection",
                    "M11_difficult_conversations"
                ],
                "expected_paths": 4,
                "expected_pivot_points": "6-10",
                "failure_modes": ["wrong_timing", "founder_conflict", "bad_pivot", "ignored_metrics"],
                "warning_signs": ["burn_rate", "churn_rate", "team_turnover", "founder_stress"],
                "key_questions": [
                    "What warning signs preceded failure?",
                    "Could failure have been prevented? When?",
                    "What founder behaviors correlated with shutdown?",
                    "How do successful vs failed paths diverge early?"
                ]
            }
        )

    # =========================================================================
    # SIMULATION-BASED JUDGING VARIANTS (M17 PORTAL Enhancement)
    # =========================================================================
    # These templates enable simulation-based judging instead of static scoring.
    # At each backward step, the system:
    # 1. Generates N candidate antecedents
    # 2. Runs forward mini-simulations from each candidate
    # 3. Uses judge LLM to holistically evaluate simulation realism
    # 4. Selects most plausible candidate
    #
    # Three quality levels per scenario:
    # - _simjudged_quick: 1 step, no dialog (~2x cost, fast)
    # - _simjudged: 2 steps, dialog enabled (~3x cost, medium quality)
    # - _simjudged_thorough: 3 steps, extra analysis (~4-5x cost, highest quality)
    # =========================================================================

    @classmethod
    def portal_presidential_election_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Presidential election with QUICK simulation-based judging.

        Same scenario as portal_presidential_election but uses lightweight
        simulation judging for candidate evaluation (1 forward step, no dialog).

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_presidential_election()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"  # Faster model
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_presidential_election_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast exploration, budget-constrained runs"
        }
        return base

    @classmethod
    def portal_presidential_election_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Presidential election with STANDARD simulation-based judging.

        Same scenario as portal_presidential_election but uses standard
        simulation judging for candidate evaluation (2 forward steps, dialog enabled).

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_presidential_election()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 5
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"  # High-quality judge
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_presidential_election_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "Production runs, high-quality path generation"
        }
        return base

    @classmethod
    def portal_presidential_election_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Presidential election with THOROUGH simulation-based judging.

        Same scenario as portal_presidential_election but uses thorough
        simulation judging for candidate evaluation (3 forward steps, dialog + extra analysis).

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_presidential_election()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 7
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 7  # More candidates to evaluate
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2  # Lower temp for highest consistency
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_presidential_election_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research runs, maximum quality path generation"
        }
        return base

    @classmethod
    def portal_startup_unicorn_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Unicorn startup with QUICK simulation-based judging.

        Same scenario as portal_startup_unicorn but uses lightweight
        simulation judging for candidate evaluation.

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_startup_unicorn()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_startup_unicorn_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast unicorn path exploration"
        }
        return base

    @classmethod
    def portal_startup_unicorn_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Unicorn startup with STANDARD simulation-based judging.

        Same scenario as portal_startup_unicorn but uses standard
        simulation judging for candidate evaluation.

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_startup_unicorn()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 6
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_startup_unicorn_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "High-quality unicorn path generation with dialog"
        }
        return base

    @classmethod
    def portal_startup_unicorn_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Unicorn startup with THOROUGH simulation-based judging.

        Same scenario as portal_startup_unicorn but uses thorough
        simulation judging for candidate evaluation.

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_startup_unicorn()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 8
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 8  # More candidates
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_startup_unicorn_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research-grade unicorn path generation"
        }
        return base

    @classmethod
    def portal_academic_tenure_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Academic tenure with QUICK simulation-based judging.

        Same scenario as portal_academic_tenure but uses lightweight
        simulation judging for candidate evaluation.

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_academic_tenure()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_academic_tenure_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast tenure path exploration"
        }
        return base

    @classmethod
    def portal_academic_tenure_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Academic tenure with STANDARD simulation-based judging.

        Same scenario as portal_academic_tenure but uses standard
        simulation judging for candidate evaluation.

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_academic_tenure()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 5
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_academic_tenure_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "High-quality tenure path with research dialogs"
        }
        return base

    @classmethod
    def portal_academic_tenure_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Academic tenure with THOROUGH simulation-based judging.

        Same scenario as portal_academic_tenure but uses thorough
        simulation judging for candidate evaluation.

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_academic_tenure()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 6
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 6
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_academic_tenure_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research-grade academic career path generation"
        }
        return base

    @classmethod
    def portal_startup_failure_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Startup failure with QUICK simulation-based judging.

        Same scenario as portal_startup_failure but uses lightweight
        simulation judging for candidate evaluation.

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_startup_failure()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_startup_failure_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast failure mode exploration"
        }
        return base

    @classmethod
    def portal_startup_failure_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Startup failure with STANDARD simulation-based judging.

        Same scenario as portal_startup_failure but uses standard
        simulation judging for candidate evaluation.

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_startup_failure()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 5
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_startup_failure_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "High-quality failure mode analysis with dialogs"
        }
        return base

    @classmethod
    def portal_startup_failure_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Startup failure with THOROUGH simulation-based judging.

        Same scenario as portal_startup_failure but uses thorough
        simulation judging for candidate evaluation.

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_startup_failure()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 6
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 8  # More failure modes to explore
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_startup_failure_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research-grade failure mode analysis with conflict dialogs"
        }
        return base

    # ============================================================================
    # AI Marketplace Competitive Dynamics Templates
    # ============================================================================

    @classmethod
    def timepoint_ai_pricing_war(cls) -> "SimulationConfig":
        """
        AI model marketplace pricing competition over 3 years (2025-2028).

        Three competitive strategies explored in parallel timelines:
        - Timeline A: Race to bottom (commoditization)
        - Timeline B: Quality premium (differentiation)
        - Timeline C: Hybrid tiered pricing

        Tracks market share, profitability, customer retention, capability development.
        Tests M12 (branching), M7 (causal chains), M13 (relationships), M15 (prospection).
        """
        return cls(
            scenario_description=(
                "**January 2025: AI Model Pricing War Begins** - Four major providers compete in "
                "a rapidly commoditizing market. Provider A (incumbent leader), Provider B (quality challenger), "
                "Provider C (aggressive startup), Enterprise Customer, VC Investor. Each provider must decide: "
                "race to bottom on price, defend quality premium, or pursue hybrid strategy?"
                "\n\n"
                "**Timeline A: Race to Bottom (Commoditization Strategy)**"
                "\n"
                "Provider C launches at $0.10/M tokens (50% below market). Q1 2025: Providers A+B must respond. "
                "Provider A cuts prices {price_cut_a} to defend market share {market_share_a_q1}. Provider B holds "
                "premium {premium_defense_b}. Q2: Provider C gains {customer_count_c_q2} customers but burns "
                "${cash_burn_c_q2}/month. Provider A's margins compress {margin_a_q2}. Enterprise Customer evaluates "
                "switching cost {switching_cost}. Q3: Does Provider A match aggressive pricing {match_pricing}? "
                "Provider B loses share {market_share_b_q3} but maintains margins {margin_b_q3}. Q4: Provider C "
                "runs low on cash {runway_c_q4}. Year 2 2026: Consolidation begins. Provider C acquired or fails "
                "{provider_c_outcome}. Provider A dominates on volume {volume_a_2026} but profits thin {profit_a_2026}. "
                "Provider B retreats to niche {niche_strategy_b}. Year 3 2027-2028: Market stabilizes at commodity "
                "pricing {final_price_2028}. Quality differentiation erodes {quality_gap_2028}. Winners: volume players. "
                "Losers: premium providers."
                "\n\n"
                "**Timeline B: Quality Premium (Differentiation Strategy)**"
                "\n"
                "Provider B maintains 3x price premium {premium_multiplier_b} based on capability lead {capability_gap_b}. "
                "Q1 2025: Enterprise Customer values {value_perception} superior performance on complex tasks "
                "{task_performance_b}. Provider B invests {rd_investment_b} in R&D vs competing on price. Q2: Provider "
                "B releases major capability improvement {capability_release_b_q2}. Customer retention {retention_b_q2} "
                "justifies premium. Provider A+C compete on price while B competes on quality. Q3: Enterprise Customer "
                "runs cost analysis {tco_analysis}: cheaper models require more tokens/retries {retry_rate}. Effective "
                "cost {effective_cost_b} competitive despite premium. Q4: Provider B's market share {market_share_b_q4} "
                "smaller but profit margin {margin_b_q4} highest. Year 2 2026: Provider B doubles down on enterprises "
                "{enterprise_focus_b}. Commoditization in consumer market {consumer_price_2026} doesn't affect B. Year 3 "
                "2027-2028: Provider B builds moat through reliability {uptime_b_2028}, support {support_quality_b}, "
                "compliance {compliance_certifications_b}. Final outcome {outcome_b}: smaller revenue but sustainable "
                "profitability {profit_margin_b_2028}."
                "\n\n"
                "**Timeline C: Hybrid Tiered Pricing (Segmentation Strategy)**"
                "\n"
                "Provider A launches tiered model: $0.08/M (basic), $0.50/M (standard), $2/M (premium). Q1 2025: "
                "Segments market {market_segments} by use case. Basic tier competes with Provider C {basic_adoption_q1}, "
                "premium competes with Provider B {premium_adoption_q1}. Q2: Provider A optimizes tier placement "
                "{optimization_strategy_a}. Customer distribution {customer_distribution_q2} across tiers reveals "
                "preferences. Enterprise Customer splits workloads {workload_split}: simple→basic, complex→premium. "
                "Q3: Provider A's blended ASP {asp_a_q3} balances volume and margin. Captures share from both ends "
                "{share_from_c_q3} {share_from_b_q3}. Q4: Competitors respond with tiering {competitor_tiering_q4}. "
                "Year 2 2026: Market converges on tiered structure {market_structure_2026}. Provider A's first-mover "
                "advantage {fma_value_a} in segmentation analytics. Year 3 2027-2028: Winner depends on tier execution "
                "{tier_execution_quality}. Provider A revenue {revenue_a_2028} highest but complexity {operational_complexity_a} "
                "challenging. Profitability {profit_a_2028} depends on cost-to-serve per tier {cost_to_serve_per_tier}."
                "\n\n"
                "Track 12 timepoints (quarterly over 3 years). Demonstrates M12 (three pricing strategies), "
                "M7 (causal chains: pricing → adoption → profitability → sustainability), M13 (competitive relationships), "
                "M15 (providers model future moves through prospection), M8 (Provider C cash burn stress)."
            ),
            world_id="timepoint_ai_pricing_war",
            entities=EntityConfig(
                count=5,  # Provider A, B, C, Enterprise Customer, VC
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG
            ),
            timepoints=CompanyConfig(
                count=12,  # Quarterly for 3 years
                resolution="quarter"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "ai_marketplace_pricing_competition",
                "start_date": "2025-01",
                "end_date": "2028-01",
                "timelines": 3,
                "mechanisms_tested": ["M12", "M7", "M13", "M15", "M8"]
            }
        )

    @classmethod
    def timepoint_ai_capability_leapfrog(cls) -> "SimulationConfig":
        """
        Sudden capability breakthrough disrupts AI marketplace hierarchy.

        Four competitive outcomes in parallel timelines:
        - Timeline A: Incumbent (GPT-style) maintains lead
        - Timeline B: Challenger (Claude-style) leapfrogs
        - Timeline C: New entrant disrupts
        - Timeline D: Consortium/open-source wins

        Bi-monthly timepoints over 3 years track technological races and market shifts.
        Tests M12 (branching), M9 (on-demand generation), M10 (scene management), M13 (relationships).
        """
        return cls(
            scenario_description=(
                "**January 2025: Pre-Leapfrog Equilibrium** - Four AI providers in stable hierarchy. "
                "Provider A (market leader, 45% share), Provider B (quality challenger, 30%), Provider C "
                "(aggressive new entrant, 15%), Consortium (open-source collective, 10%). Two enterprise customers "
                "evaluate switching costs and lock-in dynamics."
                "\n\n"
                "**Timeline A: Incumbent Maintains Lead (Provider A Victory)**"
                "\n"
                "March 2025: Provider A releases GPT-5 {gpt5_capabilities}. Benchmark improvements {benchmark_gains_a} "
                "significant. Provider B's response {provider_b_response_march} lags by {capability_gap_march} months. "
                "May: Enterprise customers renew with A {renewal_rate_a_may} based on roadmap confidence {roadmap_confidence_a}. "
                "July: Provider B releases competitive model {model_b_july} but adoption slow {adoption_rate_b_july}. "
                "September: Provider A's moat widens {moat_metrics_sept}: ecosystem lock-in {plugin_count_a}, enterprise "
                "integrations {integration_count_a}, brand trust {nps_a}. November 2025: Provider C can't compete on "
                "capabilities {capability_gap_c_nov}, pivots to price {pricing_pivot_c}. Year 2 2026: Provider A extends "
                "lead through {competitive_advantage_2026}: data flywheel {training_data_volume_a}, talent acquisition "
                "{key_hires_a}, partnerships {partnership_count_a}. Year 3 2027-2028: Market consolidates around A. "
                "Final outcome {outcome_a_2028}: Provider A 60% share, sustainable dominance."
                "\n\n"
                "**Timeline B: Challenger Leapfrogs (Provider B Victory)**"
                "\n"
                "March 2025: Provider B releases breakthrough model {claude_4_capabilities} with {key_differentiator_b}. "
                "Independent benchmarks {benchmark_results_b_march} show clear superiority on {task_categories}. May: "
                "Enterprise Customer A evaluates {evaluation_process_may}. Switching cost analysis {switching_cost_calc} "
                "vs performance gain {performance_value}. Decision: migrate {migration_decision_may}. July: Provider A "
                "scrambles to respond {emergency_response_a_july}. Promises future capabilities {vaporware_concern} but "
                "delivery uncertain {delivery_timeline_a}. September: Provider B captures {market_share_b_sept}% through "
                "performance advantage. Provider A's brand questioned {brand_damage_a_sept}. November 2025: Provider B's "
                "challenge: can they sustain lead {sustainability_b_nov}? R&D investment {rd_spend_b} vs Provider A's "
                "resources {rd_spend_a}. Year 2 2026: Arms race intensifies {capability_race_2026}. Provider B maintains "
                "narrow lead {lead_duration_b} through {innovation_strategy_b}. Year 3 2027-2028: Market leadership shifts. "
                "Final outcome {outcome_b_2028}: Provider B 40% share, new equilibrium."
                "\n\n"
                "**Timeline C: New Entrant Disrupts (Provider C Victory)**"
                "\n"
                "March 2025: Provider C (unknown startup) releases model with {disruptive_capability_c}. Not better overall "
                "but 10x better at {niche_capability}. May: Enterprise Customer B discovers {discovery_process_may} C's "
                "model perfect for {specific_use_case}. Displaces incumbents {displacement_rate_may} in niche. July: "
                "Provider C secures {funding_round_july} Series B based on traction {traction_metrics_july}. September: "
                "Niche expands {niche_expansion_sept} as customers realize broader applicability. November 2025: Incumbents "
                "A+B attempt to replicate {replication_attempts_nov} C's approach. C's secret sauce {competitive_moat_c}: "
                "{technical_advantage} or {data_advantage}? Year 2 2026: Provider C scales {scaling_challenges_2026}. Can "
                "they maintain quality {quality_maintenance} while growing {growth_rate_c}? Year 3 2027-2028: Disruption "
                "complete or incumbents recover {recovery_attempt_incumbents}? Final outcome {outcome_c_2028}: depends on "
                "C's ability to expand beyond niche."
                "\n\n"
                "**Timeline D: Consortium/Open-Source Wins**"
                "\n"
                "March 2025: Consortium releases open model {open_model_march} competitive with GPT-4 level. May: Enterprise "
                "customers evaluate {evaluation_open_may}: capability sufficient {capability_threshold_open}, cost zero "
                "{tco_open}, control maximum {control_value}. July: Adoption accelerates {adoption_rate_open_july} in "
                "cost-sensitive segments. September: Proprietary providers forced to compete {competitive_response_sept} "
                "with open alternative. November 2025: Consortium model improves {improvement_rate_consortium} through "
                "community contributions {contributor_count}. Year 2 2026: Open vs closed debate {market_split_2026}. "
                "Enterprises split: commodity workloads→open, critical workloads→proprietary. Year 3 2027-2028: Hybrid "
                "equilibrium {hybrid_market_structure}. Final outcome {outcome_d_2028}: 40% open, 60% proprietary, "
                "coexistence model."
                "\n\n"
                "Track 18 timepoints (bi-monthly over 3 years). Demonstrates M12 (four competitive outcomes), "
                "M9 (on-demand generation of new market entrants as they emerge), M10 (scene-level management of "
                "competitive dynamics), M13 (evolving relationships between providers and customers)."
            ),
            world_id="timepoint_ai_capability_leapfrog",
            entities=EntityConfig(
                count=6,  # 4 providers + 2 enterprise customers
                types=["human"],
                initial_resolution=ResolutionLevel.SCENE
            ),
            timepoints=CompanyConfig(
                count=18,  # Bi-monthly for 3 years
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "ai_capability_disruption",
                "start_date": "2025-01",
                "end_date": "2028-01",
                "timelines": 4,
                "mechanisms_tested": ["M12", "M9", "M10", "M13"]
            }
        )

    @classmethod
    def timepoint_ai_business_model_evolution(cls) -> "SimulationConfig":
        """
        AI business model evolution from APIs → fine-tuning → agents-as-service.

        Three monetization paths explored over 2 years (monthly resolution):
        - Timeline A: API-first (current model)
        - Timeline B: Fine-tuning platform (customization)
        - Timeline C: Agents-as-service (outcomes vs inputs)

        Tests M12 (branching paths), M7 (causal chains), M13 (customer relationships),
        M15 (strategic prospection), M8 (stress from model transitions).
        """
        return cls(
            scenario_description=(
                "**January 2025: Business Model Inflection Point** - Three AI providers face strategic decision: "
                "continue API-first model, pivot to fine-tuning platform, or leap to agents-as-service? Provider A "
                "(API incumbent), Provider B (fine-tuning specialist), Provider C (agent pioneer). Enterprise customers, "
                "partners, investors observe."
                "\n\n"
                "**Timeline A: API-First (Defend Current Model)**"
                "\n"
                "Jan-Mar 2025: Provider A doubles down on API model {api_investment_q1}. Improves pricing {pricing_v2}, "
                "latency {latency_improvement}, reliability {uptime_target}. Customers value {customer_satisfaction_q1} "
                "simplicity. Apr-Jun: Competition from B+C on differentiation {competitive_pressure_q2}. Provider A "
                "defends with volume discounts {volume_pricing} and enterprise SLAs {sla_tier}. Jul-Sep: Provider A's "
                "revenue growth {revenue_growth_q3} healthy but slowing {growth_deceleration}. Commoditization risk "
                "{commoditization_concern} rising. Oct-Dec: Provider A explores adjacencies {adjacent_products_q4} while "
                "maintaining API core. Year 2 2026: API model matures {market_maturity_2026}. Growth from {growth_drivers_2026}: "
                "new use cases {use_case_expansion}, international {intl_expansion}, or plateaus {plateau_risk}? Final "
                "outcome {outcome_a}: steady-state business or disrupted by new models?"
                "\n\n"
                "**Timeline B: Fine-Tuning Platform (Customization Model)**"
                "\n"
                "Jan-Mar 2025: Provider B launches fine-tuning platform {platform_launch_q1}. Customers can train custom "
                "models on their data {custom_model_capability}. Pricing: $X per hour training + $Y per inference "
                "{pricing_model_b}. Apr-Jun: Early adopters {early_adopter_count_q2} test platform. Use cases emerge "
                "{use_cases_identified_q2}: domain-specific models, brand voice, proprietary knowledge. Jul-Sep: Provider B "
                "discovers product-market fit {pmf_indicators_q3} in {winning_segment}. Challenge: support burden "
                "{support_cost_q3} for custom models. Oct-Dec: Provider B builds ecosystem {ecosystem_development_q4}: "
                "templates {template_library}, consultants {partner_network}, case studies {customer_stories}. Year 2 2026: "
                "Fine-tuning becomes table stakes {competitive_parity_2026}. Provider B's advantage: depth of tooling "
                "{tooling_depth} and customer expertise {customer_success_quality}. Final outcome {outcome_b}: higher ASP "
                "{asp_b_2026} and stickiness {retention_b_2026} but smaller TAM {tam_constraint}."
                "\n\n"
                "**Timeline C: Agents-as-Service (Outcomes Model)**"
                "\n"
                "Jan-Mar 2025: Provider C launches agent platform {agent_platform_launch_q1}. Pricing shift: sell outcomes "
                "not tokens {outcome_based_pricing}. Example: 'customer support resolution' not 'API calls'. Apr-Jun: "
                "Customers intrigued {interest_level_q2} but adoption slow {adoption_friction_q2}. Reasons: {adoption_barriers}: "
                "pricing uncertainty {pricing_uncertainty}, performance guarantees {guarantee_concerns}, integration complexity "
                "{integration_difficulty}. Jul-Sep: Provider C iterates on agent capabilities {capability_iteration_q3}. "
                "Breakthrough: autonomous workflows {workflow_automation_q3} that customers value {customer_value_q3}. "
                "Oct-Dec: Provider C demonstrates ROI {roi_case_studies_q4} in {successful_verticals}. Year 2 2026: Agent "
                "model gains traction {market_penetration_2026}. Incumbents A+B attempt agents {incumbent_response_2026} "
                "but cultural resistance {organizational_inertia}. Final outcome {outcome_c}: Provider C captures high-value "
                "segment {market_share_c_2026} but requires {critical_capabilities}: reliability {agent_reliability}, "
                "monitoring {observability_tools}, and customer success {cs_investment}."
                "\n\n"
                "Track 24 timepoints (monthly over 2 years). Demonstrates M12 (three business model paths), "
                "M7 (causal chains: model choice → customer adoption → revenue → sustainability), M13 (evolving "
                "provider-customer relationships), M15 (providers use prospection to model future competitive "
                "landscape), M8 (stress from revenue model transitions and cash flow uncertainty)."
            ),
            world_id="timepoint_ai_business_model_evolution",
            entities=EntityConfig(
                count=7,  # 3 providers + 2 customers + partner + investor
                types=["human"],
                initial_resolution=ResolutionLevel.GRAPH
            ),
            timepoints=CompanyConfig(
                count=24,  # Monthly for 2 years
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "ai_business_model_transformation",
                "start_date": "2025-01",
                "end_date": "2027-01",
                "timelines": 3,
                "mechanisms_tested": ["M12", "M7", "M13", "M15", "M8"]
            }
        )

    @classmethod
    def timepoint_ai_regulatory_divergence(cls) -> "SimulationConfig":
        """
        AI regulation divergence across EU, US, China creates fragmented marketplace.

        Three regulatory regime timelines over 3 years (quarterly resolution):
        - Timeline A: EU-first (strict regulation, GDPR-style)
        - Timeline B: US-first (light touch, innovation-focused)
        - Timeline C: China-first (state control, data localization)

        Tests M12 (branching), M7 (regulatory → business impact), M13 (regulator-provider relationships),
        M14 (circadian regulatory cycles: proposal → feedback → implementation).
        """
        return cls(
            scenario_description=(
                "**Q1 2025: Global AI Regulation Begins** - EU, US, China simultaneously pursue AI governance but "
                "with radically different approaches. Provider A (global), Provider B (US-focused), Provider C (EU-compliant), "
                "Regulator entities, Enterprise customers navigating compliance."
                "\n\n"
                "**Timeline A: EU-First Regulatory Regime (Strict Compliance)**"
                "\n"
                "Q1 2025: EU finalizes AI Act {ai_act_final}. Requirements: {eu_requirements}: model cards {model_card_mandate}, "
                "bias audits {bias_audit_frequency}, right to explanation {explanation_requirement}. Provider A compliance cost "
                "{compliance_cost_a_q1}. Q2: Providers A+C adapt {adaptation_strategy_q2}. Provider B delays EU launch "
                "{market_entry_delay_b}. Enterprise customer splits: EU data stays in EU {data_residency_eu}. Q3: Compliance "
                "advantage emerges {compliance_moat_q3}. Provider C's early investment {early_compliance_investment} pays off "
                "in EU market share {market_share_c_eu_q3}. Q4: Certification ecosystem develops {certification_bodies_q4}. "
                "Year 2 2026: EU model becomes template {regulatory_export} for {adopting_countries}. Global providers must "
                "comply {global_compliance_requirement}. Provider A builds EU-first product line {product_segmentation_2026}. "
                "Year 3 2027-2028: Regulatory maturity {regulatory_stability_2027}. Compliance costs normalize {compliance_cost_2027} "
                "as tooling improves {compliance_tooling}. Final outcome {outcome_a}: fragmented market, EU premium pricing "
                "{price_premium_eu} justified by compliance."
                "\n\n"
                "**Timeline B: US-First Regulatory Regime (Light Touch)**"
                "\n"
                "Q1 2025: US takes voluntary framework approach {voluntary_framework}. Industry self-regulation {self_regulation_body}. "
                "Providers A+B advocate for {lobbying_strategy_q1}. Q2: Minimal compliance burden {compliance_cost_us_q2} vs EU. "
                "Provider B's US advantage {competitive_advantage_b_us}: faster iteration {release_velocity_b}, lower costs "
                "{cost_structure_b}. Q3: US becomes innovation hub {innovation_index_us_q3}. Startups flock {startup_count_us} "
                "to permissive regime. Q4: Tension emerges {regulatory_tension_q4}: consumer groups demand protection {consumer_advocacy}, "
                "industry resists {industry_resistance}. Year 2 2026: Incidents occur {safety_incidents_2026} that test voluntary "
                "model. Public pressure {public_pressure_2026} for stricter rules. Congress considers {legislation_pending} "
                "mandatory requirements. Year 3 2027-2028: US converges toward {convergence_2027} EU model or maintains "
                "exceptionalism {us_exceptionalism}? Final outcome {outcome_b}: innovation advantage vs safety concerns."
                "\n\n"
                "**Timeline C: China-First Regulatory Regime (State Control)**"
                "\n"
                "Q1 2025: China mandates {china_mandates}: algorithm registration {algorithm_registry}, content control "
                "{content_filtering}, data localization {data_localization_china}. Provider A blocked {market_access_denied} "
                "unless JV {jv_requirement}. Q2: Chinese providers advantage {domestic_advantage_q2} in domestic market. "
                "Provider C attempts entry {entry_strategy_c_china} with local partner {partnership_c_china}. Q3: Two-tier "
                "system emerges {china_market_structure_q3}: domestic market (Chinese providers), international market (Western "
                "providers). Q4: Technology divergence {tech_divergence_q4} as Chinese models optimize for {chinese_requirements}. "
                "Year 2 2026: Belt & Road {bri_influence_2026} spreads Chinese regulatory model to {adopting_countries_china}. "
                "Global market fragments {market_fragmentation_2026}: Western sphere vs Chinese sphere. Year 3 2027-2028: "
                "Provider A maintains two product lines {product_duplication}: China-compliant vs rest-of-world. Cost impact "
                "{duplication_cost}. Final outcome {outcome_c}: bifurcated global market, compliance complexity maximum."
                "\n\n"
                "Track 12 timepoints (quarterly over 3 years). Demonstrates M12 (three regulatory regimes), "
                "M7 (causal chains: regulation → compliance cost → competitive positioning → market structure), "
                "M13 (evolving relationships between regulators and providers), M14 (circadian regulatory cycles: "
                "proposal → comment period → final rule → enforcement)."
            ),
            world_id="timepoint_ai_regulatory_divergence",
            entities=EntityConfig(
                count=8,  # 3 providers + 3 regulators (EU, US, China) + 2 customers
                types=["human"],
                initial_resolution=ResolutionLevel.SCENE
            ),
            timepoints=CompanyConfig(
                count=12,  # Quarterly for 3 years
                resolution="quarter"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.BRANCHING,
                enable_counterfactuals=True
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                include_knowledge_flow=True,
                export_ml_dataset=True
            ),
            metadata={
                "analysis_type": "ai_regulatory_fragmentation",
                "start_date": "2025-01",
                "end_date": "2028-01",
                "timelines": 3,
                "regulatory_regimes": ["EU", "US", "China"],
                "mechanisms_tested": ["M12", "M7", "M13", "M14"]
            }
        )

    # ============================================================================
    # Timepoint Corporate Portal Templates (M17 - Backward Temporal Reasoning)
    # Using Real Founders: Sean McDonald + Ken Cavanagh
    # ============================================================================

    @classmethod
    def portal_timepoint_unicorn(cls) -> "SimulationConfig":
        """
        PORTAL mode: Timepoint achieves $1.2B unicorn valuation - work backward to founding.

        Portal: March 2030 - Timepoint valued at $1.2B Series C
        Origin: October 2024 - Sean + Ken found company with vision but no funding
        Goal: Find plausible growth paths to unicorn status leveraging their complementary skills

        Features real founders: Sean McDonald (philosophical/technical) + Ken Cavanagh (psychology/operations)
        """
        return cls(
            scenario_description=(
                "**March 2030: Timepoint Unicorn Status** - Timepoint closes $150M Series C at $1.2B post-money valuation. "
                "$120M ARR, 450 employees, 95+ Fortune 500 customers. Wall Street analysts call it 'the Bloomberg Terminal "
                "of temporal simulation.' But how did two philosophers get here? "
                "\n\n"
                "**The Founders**: Sean McDonald (Philosophical Technical Polymath) brings exceptional conceptual innovation, "
                "philosophical depth, and AI/IoT technical chops. Three-time founder (Jute Networks, Bitwater Farms, Sundial). "
                "Published author on consciousness and AI. Strength: First-principles thinking, unconventional products. "
                "Weakness: Limited operational scaling experience, needs strong business partner. "
                "\n\n"
                "Ken Cavanagh (Psychology-Tech Bridge Builder) brings industrial-organizational psychology + AI systems expertise. "
                "Former SpaceX People Analytics, Agency42 founder. Rare combination: understands neural networks AND team dynamics. "
                "Strength: Human-centered AI, people analytics, practical execution. Weakness: Needs complementary visionary for "
                "product positioning. "
                "\n\n"
                "**This is a complementary founding team**: Sean's conceptual innovation + Ken's operational/psychological depth. "
                "Work backward from $1.2B to October 2024 founding moment. System explores multiple paths: "
                "\n\n"
                "(A) **Enterprise-First Strategy**: Land Fortune 500 early (pharma, finance), slow but steady $500K-$2M ACVs, "
                "focus on mission-critical use cases (regulatory compliance, scenario planning). Requires strong enterprise "
                "sales team + customer success. Ken's I-O psych background helps positioning for workforce planning use cases. "
                "\n\n"
                "(B) **Developer-Led Growth**: Open-source core temporal engine, build community, freemium → paid enterprise. "
                "Sean's open-source advocacy (Sundial, Jute) aligns here. Start with academic/research users, expand to commercial. "
                "Lower burn but slower revenue ramp. "
                "\n\n"
                "(C) **Vertical Domination**: Own one vertical completely (healthcare simulation, financial stress testing), "
                "then expand. Ken's healthcare/org behavior expertise + Sean's AI/simulation depth = credible healthcare play. "
                "\n\n"
                "**Validation checks**: Given Sean's philosophical focus and Ken's practical execution, do growth strategies "
                "play to their strengths? Does Sean stay engaged through operational scaling (historical risk)? Does Ken get "
                "enough strategic input (his need for visionary complement)? Forward coherence ensures founding team dynamics "
                "→ PMF discovery → scaling execution makes sense. "
                "\n\n"
                "**Pivot points**: Initial positioning (academic vs enterprise, Oct 2024), PMF moment (Q2 2025), Series A "
                "strategy (Q4 2025), scaling/hiring pattern (2026-2028), partnership model evolution (do roles stay clear?)."
            ),
            world_id="portal_timepoint_unicorn",
            entities=EntityConfig(
                count=6,  # Sean + Ken + lead investor + key hire + customer champion + advisor
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG
            ),
            timepoints=CompanyConfig(
                count=1,  # PORTAL generates backward states
                resolution="quarter"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="$1.2B Series C valuation, $120M ARR, 450 employees, 95+ Fortune 500 customers",
                portal_year=2030,
                origin_year=2024,
                backward_steps=22,  # 5.5 years × 4 quarters
                path_count=3,
                candidate_antecedents_per_step=7,
                exploration_mode="adaptive",
                coherence_threshold=0.65,
                llm_scoring_weight=0.30,
                historical_precedent_weight=0.25,
                causal_necessity_weight=0.25,
                entity_capability_weight=0.15
            ),
            outputs=OutputConfig(
                formats=["json", "jsonl", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "portal_type": "timepoint_unicorn",
                "founder_profiles": ["sean_mcdonald", "ken_cavanagh"],
                "profile_source": "generation/profiles/founder_archetypes/*.json",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M13_multi_entity_synthesis",
                    "M7_causal_milestone_chains",
                    "M15_strategic_planning",
                    "M8_founder_stress",
                    "M11_fundraising_negotiations"
                ],
                "expected_paths": 3,
                "growth_strategies": ["enterprise_first", "developer_led", "vertical_healthcare"],
                "key_questions": [
                    "How do Sean's philosophical depth + Ken's operational pragmatism enable unicorn trajectory?",
                    "What GTM strategy leverages their unique skill combination?",
                    "Does Sean stay engaged through operational scaling?",
                    "How do founder roles evolve as company grows?"
                ]
            }
        )

    @classmethod
    def portal_timepoint_series_a_success(cls) -> "SimulationConfig":
        """
        PORTAL mode: Timepoint closes strong $50M Series A - work backward to seed stage.

        Portal: December 2026 - $50M Series A at $200M valuation
        Origin: February 2025 - $2M seed round
        Goal: Trace path from seed to Series A success with strong metrics
        """
        return cls(
            scenario_description=(
                "**December 2026: Timepoint Series A Success** - Timepoint closes $50M Series A led by Andreessen Horowitz "
                "at $200M post-money valuation. Metrics: $8M ARR, 150% YoY growth, 15 enterprise customers, $500K average ACV, "
                "net revenue retention 135%. VCs cite 'unique founder combination of philosophical depth + operational rigor.' "
                "\n\n"
                "**Work backward from Series A to seed stage**: How did Sean and Ken get here in 22 months? Starting context: "
                "February 2025 seed round $2M at $10M post (Lux Capital, unusual bet on 'philosophers building AI'). At seed, "
                "they had: working prototype, 2 pilot customers, strong vision doc, but no proven GTM. "
                "\n\n"
                "**Key milestones to explore backward**: "
                "- Series A pitch (Dec 2026): What metrics/story convinced a16z? "
                "- Customer #10 signed (Q3 2026): What pattern emerged that proved GTM? "
                "- PMF moment (Q1 2026): When did customer retention/expansion inflect? "
                "- First $1M ARR (Q4 2025): What pricing/packaging worked? "
                "- Customer #1-5 signed (Q2-Q3 2025): How did initial sales motion develop? "
                "- Post-seed execution (Q1 2025): What did they build first? Who did they hire? "
                "\n\n"
                "**Founder dynamics to trace**: Did Sean's philosophical positioning help or hurt enterprise sales? "
                "Did Ken's I-O psych background unlock workforce use cases? How did they divide CEO/President/CTO roles? "
                "What tensions emerged as company professionalized? "
                "\n\n"
                "**Three candidate paths backward**: "
                "(A) Workforce Planning Path: Ken's I-O psych expertise → HR tech positioning → sell to CHROs. "
                "(B) Scenario Planning Path: Sean's philosophical depth → strategic planning positioning → sell to strategy teams. "
                "(C) Compliance/Risk Path: Both founders' rigor → regulatory/risk use cases → sell to compliance officers. "
                "\n\n"
                "Each path has different customer profiles, sales cycles, ACV patterns, and founder engagement levels."
            ),
            world_id="portal_timepoint_series_a",
            entities=EntityConfig(
                count=6,  # Sean + Ken + seed investor + Series A investor + early customer + first hire
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG
            ),
            timepoints=CompanyConfig(
                count=1,
                resolution="quarter"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="$50M Series A at $200M valuation, $8M ARR, 15 enterprise customers",
                portal_year=2026,
                origin_year=2025,
                backward_steps=8,  # 22 months ~ 8 quarters
                path_count=3,
                candidate_antecedents_per_step=7,
                exploration_mode="adaptive",
                coherence_threshold=0.70,
                llm_scoring_weight=0.30,
                historical_precedent_weight=0.25,
                causal_necessity_weight=0.25,
                entity_capability_weight=0.15
            ),
            outputs=OutputConfig(
                formats=["json", "jsonl", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "portal_type": "timepoint_series_a",
                "founder_profiles": ["sean_mcdonald", "ken_cavanagh"],
                "profile_source": "generation/profiles/founder_archetypes/*.json",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M13_founder_relationship_evolution",
                    "M7_causal_revenue_milestones",
                    "M15_strategic_positioning",
                    "M11_investor_negotiations"
                ],
                "expected_paths": 3,
                "use_case_paths": ["workforce_planning", "scenario_planning", "compliance_risk"],
                "key_questions": [
                    "What use case positioning enabled rapid enterprise adoption?",
                    "How did founder skill sets map to initial GTM?",
                    "What hiring pattern supported growth?",
                    "How did founder roles evolve seed → Series A?"
                ]
            }
        )

    @classmethod
    def portal_timepoint_product_market_fit(cls) -> "SimulationConfig":
        """
        PORTAL mode: Timepoint achieves strong PMF - work backward to MVP launch.

        Portal: June 2026 - Strong PMF: $5M ARR, 40+ customers, NRR 140%
        Origin: October 2024 - MVP launch, 0 customers
        Goal: Identify product decisions and positioning that led to PMF
        """
        return cls(
            scenario_description=(
                "**June 2026: Timepoint Product-Market Fit Moment** - Timepoint crosses clear PMF threshold: $5M ARR, "
                "42 paying customers (32 enterprise, 10 mid-market), net revenue retention 140%, organic inbound 60% of pipeline, "
                "customer quotes: 'finally, someone who gets temporal reasoning' and 'philosophers building AI is exactly what we needed.' "
                "\n\n"
                "**Work backward to MVP launch**: October 2024, Sean and Ken shipped MVP after 6 months of development. Features: "
                "basic temporal simulation engine, manual scenario setup, limited automation. No clear positioning yet—customers "
                "confused about 'what is this for?' First 6 months: 3 pilot customers, inconsistent feedback, unclear ICP. "
                "\n\n"
                "**Critical questions to explore backward**: "
                "- What positioning shift unlocked PMF? (when did 'temporal simulation' become 'scenario planning for executives'?) "
                "- What product iteration mattered most? (when did automation → self-service happen?) "
                "- What customer discovery process worked? (how did they find the ICP?) "
                "- What pricing/packaging resonated? (per-seat? per-scenario? enterprise license?) "
                "- What founder behaviors enabled learning? (Sean's philosophical depth → customer convos? Ken's psych training → user research?) "
                "\n\n"
                "**Three candidate PMF paths**: "
                "(A) Executive Scenario Planning: Positioned as 'what-if analysis for C-suite,' sold to strategy/CEO office, "
                "premium pricing ($50K-$200K/year), requires high-touch onboarding. Sean's philosophical framing helps here. "
                "\n"
                "(B) Workforce Planning & Org Design: Positioned as 'simulate org changes before executing,' sold to HR/CHRO, "
                "mid-market pricing ($20K-$80K/year), Ken's I-O psych credibility unlocks category. "
                "\n"
                "(C) Compliance & Risk Simulation: Positioned as 'test regulatory scenarios,' sold to compliance/risk officers, "
                "high-value pricing ($100K-$500K/year), both founders' rigor + transparency ethos builds trust. "
                "\n\n"
                "**Founder skill utilization**: Does Sean's 'questions fundamental assumptions' trait → deeper customer discovery? "
                "Does Ken's 'bridges technical and human perspectives' trait → clearer product positioning? How do they divide product "
                "vs GTM responsibilities?"
            ),
            world_id="portal_timepoint_pmf",
            entities=EntityConfig(
                count=6,  # Sean + Ken + early customer + design partner + product advisor + first PM hire
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG
            ),
            timepoints=CompanyConfig(
                count=1,
                resolution="month"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="$5M ARR, 42 customers, 140% NRR, clear product-market fit",
                portal_year=2026,
                origin_year=2024,
                backward_steps=20,  # 20 months from Oct 2024 to June 2026
                path_count=3,
                candidate_antecedents_per_step=7,
                exploration_mode="adaptive",
                coherence_threshold=0.70,
                llm_scoring_weight=0.30,
                historical_precedent_weight=0.25,
                causal_necessity_weight=0.25,
                entity_capability_weight=0.15
            ),
            outputs=OutputConfig(
                formats=["json", "jsonl", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "portal_type": "timepoint_pmf",
                "founder_profiles": ["sean_mcdonald", "ken_cavanagh"],
                "profile_source": "generation/profiles/founder_archetypes/*.json",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M13_cofounder_product_collaboration",
                    "M7_causal_product_iteration",
                    "M15_customer_discovery_strategy",
                    "M3_customer_feedback_integration"
                ],
                "expected_paths": 3,
                "pmf_paths": ["executive_scenario_planning", "workforce_org_design", "compliance_risk"],
                "key_questions": [
                    "What positioning shift unlocked PMF?",
                    "Which product iterations mattered most?",
                    "How did founders' unique skills enable customer discovery?",
                    "What pricing/packaging resonated with ICP?"
                ]
            }
        )

    @classmethod
    def portal_timepoint_enterprise_adoption(cls) -> "SimulationConfig":
        """
        PORTAL mode: Timepoint achieves enterprise adoption at scale - work backward to first pilot.

        Portal: March 2027 - 25 Fortune 500 customers, $18M ARR
        Origin: November 2024 - First pilot customer signed
        Goal: Trace evolution of enterprise sales motion and customer success patterns
        """
        return cls(
            scenario_description=(
                "**March 2027: Timepoint Enterprise Dominance** - Timepoint now serves 25 Fortune 500 customers including "
                "Goldman Sachs, Pfizer, Microsoft, JPMorgan. $18M ARR, average ACV $720K, net revenue retention 145%, "
                "reference selling drives 70% of new pipeline. Customer testimonials cite 'philosophical rigor meets practical execution' "
                "as key differentiator. Sean presents at Davos on 'AI and Human Flourishing.' Ken publishes HBR article on "
                "'Psychology-Informed AI Implementation.' But how did they get here from one pilot customer? "
                "\n\n"
                "**Work backward to first pilot**: November 2024, first enterprise pilot signed with pharmaceutical company "
                "(clinical trial scenario planning). $50K pilot, 3-month commitment, 5 users. Customer champion: Head of Clinical Operations "
                "who resonated with Sean's philosophical depth + Ken's healthcare/org expertise. Pilot scope: test 10 trial design scenarios, "
                "compare outcomes, validate assumptions. Risk: If pilot fails, enterprise motion dies. "
                "\n\n"
                "**Critical milestones to trace backward**: "
                "- Customer #25 signed (Mar 2027): What reference network enabled this? "
                "- Reference selling inflection (Q3 2026): When did customers start selling for them? "
                "- Customer success pattern emerged (Q1 2026): What CS playbook worked? "
                "- First customer renewal + expansion (Q2 2025): What drove expansion from $50K → $500K? "
                "- Customer #1 pilot success (Feb 2025): What made pilot succeed? "
                "- Pilot negotiation (Nov 2024): How did they land first enterprise customer? "
                "\n\n"
                "**Three enterprise paths to explore**: "
                "(A) Vertical Beachhead: Win pharma → leverage references in healthcare → expand to other regulated industries. "
                "Ken's healthcare expertise + Sean's philosophical rigor = credibility in risk-averse sectors. "
                "\n"
                "(B) Horizontal Champions: Win individual champions across industries → build champion network → scale via word-of-mouth. "
                "Sean's thought leadership (Davos, writings) + Ken's HBR credibility = executive-level relationships. "
                "\n"
                "(C) Strategic Partnership: Partner with big consulting firm (McKinsey, BCG) → co-sell into their enterprise accounts. "
                "Both founders' intellectual depth = consulting credibility. "
                "\n\n"
                "**Founder role evolution**: As company grows 1 → 25 customers, how do Sean and Ken's roles change? Does Sean stay "
                "engaged in customer conversations (his historical pattern)? Does Ken build the CS/account management function (his I-O "
                "psych + people expertise)? What operational tensions emerge?"
            ),
            world_id="portal_timepoint_enterprise",
            entities=EntityConfig(
                count=6,  # Sean + Ken + first customer champion + VP Sales hire + CS leader + consulting partner
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG
            ),
            timepoints=CompanyConfig(
                count=1,
                resolution="quarter"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="25 Fortune 500 customers, $18M ARR, dominant enterprise position",
                portal_year=2027,
                origin_year=2024,
                backward_steps=10,  # 28 months ~ 10 quarters
                path_count=3,
                candidate_antecedents_per_step=7,
                exploration_mode="adaptive",
                coherence_threshold=0.70,
                llm_scoring_weight=0.30,
                historical_precedent_weight=0.25,
                causal_necessity_weight=0.25,
                entity_capability_weight=0.15
            ),
            outputs=OutputConfig(
                formats=["json", "jsonl", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "portal_type": "timepoint_enterprise_adoption",
                "founder_profiles": ["sean_mcdonald", "ken_cavanagh"],
                "profile_source": "generation/profiles/founder_archetypes/*.json",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M13_enterprise_relationship_building",
                    "M7_causal_sales_milestones",
                    "M15_reference_selling_strategy",
                    "M8_founder_scaling_stress",
                    "M11_enterprise_negotiations"
                ],
                "expected_paths": 3,
                "enterprise_paths": ["vertical_beachhead", "horizontal_champions", "strategic_partnership"],
                "key_questions": [
                    "What customer success pattern enabled 145% NRR?",
                    "How did reference network develop?",
                    "What founder behaviors drove enterprise credibility?",
                    "How did roles evolve as company scaled?"
                ]
            }
        )

    @classmethod
    def portal_timepoint_founder_transition(cls) -> "SimulationConfig":
        """
        PORTAL mode: One founder departs after Series B - work backward to partnership formation.

        Portal: September 2027 - Ken Cavanagh departs as President after Series B
        Origin: October 2024 - Partnership formation & equity agreements
        Goal: Identify early partnership dynamics that predicted transition
        """
        return cls(
            scenario_description=(
                "**September 2027: Ken Cavanagh Departs Timepoint** - After successful $100M Series B ($500M valuation), "
                "Ken Cavanagh (President/COO) announces departure to 'pursue new opportunities.' Sean McDonald (CEO) remains. "
                "Public statement: 'amicable transition,' 'different visions for next phase,' 'grateful for partnership.' Private reality: "
                "18 months of growing tension over strategic direction, role clarity, and decision authority. Ken owns 28% (post-dilution), "
                "Sean owns 42%. Board thanks Ken for 'operational excellence' but sides with Sean's vision. "
                "\n\n"
                "**Work backward to founding moment**: October 2024, Sean and Ken negotiate partnership. Initial split: Sean 55% (CEO, "
                "product vision, fundraising), Ken 35% (President, operations, GTM), ESOP/advisors 10%. Vesting: 4 years, 1-year cliff. "
                "Role boundaries: Sean owns product roadmap + investor relations, Ken owns revenue execution + team building. Sounds clear. "
                "But was it really? "
                "\n\n"
                "**Critical tensions to trace backward**: "
                "- Departure negotiation (Sep 2027): What final conflict triggered exit? "
                "- Series B board dynamics (June 2027): Did board favor one founder over other? "
                "- Product vs sales tension (Q1 2027): Sean wants deeper product → Ken needs more features for sales. Who wins? "
                "- First major disagreement (Q3 2026): When did cracks appear? "
                "- Series A role evolution (Q4 2025): Did equity dilution (Sean 42% → Ken 28%) create resentment? "
                "- Early hiring conflicts (Q2 2025): Did they agree on key hires? "
                "- Formation negotiation (Oct 2024): Were role boundaries truly clear? Red flags missed? "
                "\n\n"
                "**Three breakup paths to explore**: "
                "(A) Product Vision Conflict: Sean's philosophical/long-term vision conflicts with Ken's practical/near-term execution needs. "
                "Sean wants to build 'AI consciousness framework,' Ken wants to ship features customers are buying. Irreconcilable. "
                "\n"
                "(B) Authority Ambiguity: Despite clear initial roles, gray areas emerge (who decides pricing? hiring? product priorities?). "
                "Sean's philosophical nature → questions everything. Ken's operational nature → wants clear authority. Friction builds. "
                "\n"
                "(C) Board Alignment Shift: Post-Series B, board wants aggressive growth → prefers operational CEO. Pressures Sean to "
                "delegate more → Sean resists → board sides with Sean (founder primacy) → Ken feels undermined → exits. "
                "\n\n"
                "**Founder dynamics analysis**: Given Sean's 'needs strong operational partner' weakness + Ken's 'needs complementary "
                "visionary' weakness, was this partnership structurally sound? Did initial equity split (55/35) create implicit hierarchy "
                "that undermined partnership? Did their complementary strengths become conflicting priorities under growth pressure?"
            ),
            world_id="portal_timepoint_founder_transition",
            entities=EntityConfig(
                count=6,  # Sean + Ken + lead board member + VP Engineering + VP Sales + mediator/advisor
                types=["human"],
                initial_resolution=ResolutionLevel.DIALOG
            ),
            timepoints=CompanyConfig(
                count=1,
                resolution="quarter"
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PORTAL,
                portal_description="Ken Cavanagh departs as President after Series B, partnership dissolves",
                portal_year=2027,
                origin_year=2024,
                backward_steps=12,  # 3 years × 4 quarters
                path_count=3,
                candidate_antecedents_per_step=7,
                exploration_mode="adaptive",
                coherence_threshold=0.70,
                llm_scoring_weight=0.30,
                historical_precedent_weight=0.20,
                causal_necessity_weight=0.30,  # Higher weight: partnership dynamics are causally critical
                entity_capability_weight=0.20
            ),
            outputs=OutputConfig(
                formats=["json", "jsonl", "markdown"],
                include_dialogs=True,
                include_relationships=True,
                export_ml_dataset=True
            ),
            metadata={
                "portal_type": "timepoint_founder_transition",
                "founder_profiles": ["sean_mcdonald", "ken_cavanagh"],
                "profile_source": "generation/profiles/founder_archetypes/*.json",
                "mechanisms_featured": [
                    "M17_modal_causality_portal",
                    "M13_founder_relationship_deterioration",
                    "M7_causal_conflict_escalation",
                    "M15_strategic_vision_misalignment",
                    "M8_partnership_stress",
                    "M11_board_founder_dynamics"
                ],
                "expected_paths": 3,
                "breakup_paths": ["product_vision_conflict", "authority_ambiguity", "board_alignment_shift"],
                "key_questions": [
                    "What early partnership decisions predicted later conflict?",
                    "Were initial role boundaries truly clear?",
                    "How did equity split create implicit hierarchy?",
                    "What board dynamics influenced founder relationship?",
                    "Could partnership have been structured differently?"
                ]
            }
        )

    # ============================================================================
    # Timepoint Corporate Portal Templates - QUICK Simulation-Judged Variants
    # ============================================================================

    @classmethod
    def portal_timepoint_unicorn_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Timepoint unicorn journey with QUICK simulation-based judging.

        Same scenario as portal_timepoint_unicorn but uses lightweight
        simulation judging for candidate evaluation (1 forward step, no dialog).

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_timepoint_unicorn()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_unicorn_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast exploration of unicorn trajectories"
        }
        return base

    @classmethod
    def portal_timepoint_series_a_success_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Series A success journey with QUICK simulation-based judging.

        Same scenario as portal_timepoint_series_a_success but uses lightweight
        simulation judging for candidate evaluation (1 forward step, no dialog).

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_timepoint_series_a_success()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_series_a_success_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast exploration of Series A pathways"
        }
        return base

    @classmethod
    def portal_timepoint_product_market_fit_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Product-market fit journey with QUICK simulation-based judging.

        Same scenario as portal_timepoint_product_market_fit but uses lightweight
        simulation judging for candidate evaluation (1 forward step, no dialog).

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_timepoint_product_market_fit()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_product_market_fit_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast exploration of PMF discovery paths"
        }
        return base

    @classmethod
    def portal_timepoint_enterprise_adoption_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Enterprise adoption journey with QUICK simulation-based judging.

        Same scenario as portal_timepoint_enterprise_adoption but uses lightweight
        simulation judging for candidate evaluation (1 forward step, no dialog).

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_timepoint_enterprise_adoption()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_enterprise_adoption_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast exploration of enterprise GTM strategies"
        }
        return base

    @classmethod
    def portal_timepoint_founder_transition_simjudged_quick(cls) -> "SimulationConfig":
        """
        PORTAL mode: Founder transition journey with QUICK simulation-based judging.

        Same scenario as portal_timepoint_founder_transition but uses lightweight
        simulation judging for candidate evaluation (1 forward step, no dialog).

        Cost: ~2x standard | Speed: Fast | Quality: Good
        """
        base = cls.portal_timepoint_founder_transition()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 1
        base.temporal.simulation_max_entities = 3
        base.temporal.simulation_include_dialog = False
        base.temporal.judge_model = "meta-llama/llama-3.1-70b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_founder_transition_simjudged_quick"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "quick",
            "forward_steps": 1,
            "dialog_enabled": False,
            "cost_multiplier": "~2x",
            "use_case": "Fast exploration of partnership failure modes"
        }
        return base

    # ============================================================================
    # Timepoint Corporate Portal Templates - STANDARD Simulation-Judged Variants
    # ============================================================================

    @classmethod
    def portal_timepoint_unicorn_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Timepoint unicorn journey with STANDARD simulation-based judging.

        Same scenario as portal_timepoint_unicorn but uses standard
        simulation judging for candidate evaluation (2 forward steps, dialog enabled).

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_timepoint_unicorn()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 5
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_unicorn_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "Production runs, high-quality unicorn trajectory analysis"
        }
        return base

    @classmethod
    def portal_timepoint_series_a_success_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Series A success journey with STANDARD simulation-based judging.

        Same scenario as portal_timepoint_series_a_success but uses standard
        simulation judging for candidate evaluation (2 forward steps, dialog enabled).

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_timepoint_series_a_success()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 5
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_series_a_success_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "Production runs, high-quality Series A pathway analysis"
        }
        return base

    @classmethod
    def portal_timepoint_product_market_fit_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Product-market fit journey with STANDARD simulation-based judging.

        Same scenario as portal_timepoint_product_market_fit but uses standard
        simulation judging for candidate evaluation (2 forward steps, dialog enabled).

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_timepoint_product_market_fit()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 5
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_product_market_fit_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "Production runs, high-quality PMF discovery analysis"
        }
        return base

    @classmethod
    def portal_timepoint_enterprise_adoption_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Enterprise adoption journey with STANDARD simulation-based judging.

        Same scenario as portal_timepoint_enterprise_adoption but uses standard
        simulation judging for candidate evaluation (2 forward steps, dialog enabled).

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_timepoint_enterprise_adoption()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 5
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_enterprise_adoption_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "Production runs, high-quality enterprise GTM analysis"
        }
        return base

    @classmethod
    def portal_timepoint_founder_transition_simjudged(cls) -> "SimulationConfig":
        """
        PORTAL mode: Founder transition journey with STANDARD simulation-based judging.

        Same scenario as portal_timepoint_founder_transition but uses standard
        simulation judging for candidate evaluation (2 forward steps, dialog enabled).

        Cost: ~3x standard | Speed: Medium | Quality: High
        """
        base = cls.portal_timepoint_founder_transition()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 2
        base.temporal.simulation_max_entities = 5
        base.temporal.simulation_include_dialog = True
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.3
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_founder_transition_simjudged"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "standard",
            "forward_steps": 2,
            "dialog_enabled": True,
            "cost_multiplier": "~3x",
            "use_case": "Production runs, high-quality partnership analysis"
        }
        return base

    # ============================================================================
    # Timepoint Corporate Portal Templates - THOROUGH Simulation-Judged Variants
    # ============================================================================

    @classmethod
    def portal_timepoint_unicorn_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Timepoint unicorn journey with THOROUGH simulation-based judging.

        Same scenario as portal_timepoint_unicorn but uses thorough
        simulation judging for candidate evaluation (3 forward steps, dialog + extra analysis).

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_timepoint_unicorn()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 7
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 7
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_unicorn_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research-grade unicorn trajectory analysis with maximum detail"
        }
        return base

    @classmethod
    def portal_timepoint_series_a_success_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Series A success journey with THOROUGH simulation-based judging.

        Same scenario as portal_timepoint_series_a_success but uses thorough
        simulation judging for candidate evaluation (3 forward steps, dialog + extra analysis).

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_timepoint_series_a_success()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 7
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 7
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_series_a_success_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research-grade Series A pathway analysis with maximum detail"
        }
        return base

    @classmethod
    def portal_timepoint_product_market_fit_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Product-market fit journey with THOROUGH simulation-based judging.

        Same scenario as portal_timepoint_product_market_fit but uses thorough
        simulation judging for candidate evaluation (3 forward steps, dialog + extra analysis).

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_timepoint_product_market_fit()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 7
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 7
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_product_market_fit_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research-grade PMF discovery analysis with maximum detail"
        }
        return base

    @classmethod
    def portal_timepoint_enterprise_adoption_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Enterprise adoption journey with THOROUGH simulation-based judging.

        Same scenario as portal_timepoint_enterprise_adoption but uses thorough
        simulation judging for candidate evaluation (3 forward steps, dialog + extra analysis).

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_timepoint_enterprise_adoption()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 7
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 7
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_enterprise_adoption_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research-grade enterprise GTM analysis with maximum detail"
        }
        return base

    @classmethod
    def portal_timepoint_founder_transition_simjudged_thorough(cls) -> "SimulationConfig":
        """
        PORTAL mode: Founder transition journey with THOROUGH simulation-based judging.

        Same scenario as portal_timepoint_founder_transition but uses thorough
        simulation judging for candidate evaluation (3 forward steps, dialog + extra analysis).

        Cost: ~4-5x standard | Speed: Slow | Quality: Highest
        """
        base = cls.portal_timepoint_founder_transition()
        base.temporal.use_simulation_judging = True
        base.temporal.simulation_forward_steps = 3
        base.temporal.simulation_max_entities = 7
        base.temporal.simulation_include_dialog = True
        base.temporal.candidate_antecedents_per_step = 7
        base.temporal.judge_model = "meta-llama/llama-3.1-405b-instruct"
        base.temporal.judge_temperature = 0.2
        base.temporal.simulation_cache_results = True
        base.world_id = "portal_timepoint_founder_transition_simjudged_thorough"
        base.metadata["simulation_judging"] = {
            "enabled": True,
            "quality_level": "thorough",
            "forward_steps": 3,
            "dialog_enabled": True,
            "cost_multiplier": "~4-5x",
            "use_case": "Research-grade partnership analysis with maximum detail"
        }
        return base

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
