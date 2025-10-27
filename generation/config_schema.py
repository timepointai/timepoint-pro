"""
Simulation Configuration Schema with Pydantic Validation

Provides validated configuration for simulation generation with:
- Entity configuration
- Timepoint structure
- Temporal mode settings
- Output specifications
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


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


class TimepointConfig(BaseModel):
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
        valid_resolutions = {"year", "month", "day", "hour", "minute", "second"}
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
            timepoints=TimepointConfig(count=5, resolution="day"),
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
    timepoints: TimepointConfig = Field(
        default_factory=lambda: TimepointConfig(),
        description="Timepoint structure configuration"
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
            timepoints=TimepointConfig(count=3, resolution="hour"),
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
            timepoints=TimepointConfig(
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
            timepoints=TimepointConfig(count=2, resolution="hour"),
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
            timepoints=TimepointConfig(
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
            timepoints=TimepointConfig(
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
            timepoints=TimepointConfig(
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
            timepoints=TimepointConfig(
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
            timepoints=TimepointConfig(
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
            timepoints=TimepointConfig(
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
            timepoints=TimepointConfig(
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
            timepoints=TimepointConfig(
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
                "is Timepoint AI at maximum capacity: 28 entities, 500 timepoints, 16 mechanisms, "
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
            timepoints=TimepointConfig(
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
