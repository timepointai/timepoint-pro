# schemas.py - SQLModel schemas serving as ORM, validation, and API spec
from sqlmodel import SQLModel, Field, JSON, Column
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import numpy as np
from pydantic import BaseModel, field_validator

class ResolutionLevel(str, Enum):
    TENSOR_ONLY = "tensor_only"
    SCENE = "scene"
    GRAPH = "graph"
    DIALOG = "dialog"
    TRAINED = "trained"
    FULL_DETAIL = "full_detail"  # Highest resolution with all data

class TemporalMode(str, Enum):
    """Different causal regimes for temporal reasoning"""
    PEARL = "pearl"  # Standard causality (no anachronisms, forward flow)
    DIRECTORIAL = "directorial"  # Narrative structure with dramatic tension
    BRANCHING = "branching"  # Many-worlds interpretation
    CYCLICAL = "cyclical"  # Time loops and prophecy
    PORTAL = "portal"  # Backward inference from fixed endpoint to origin

class FidelityPlanningMode(str, Enum):
    """How should fidelity be allocated across timepoints?"""
    PROGRAMMATIC = "programmatic"  # Plan all fidelity levels upfront (deterministic)
    ADAPTIVE = "adaptive"  # Decide per-step based on simulation state (dynamic)
    HYBRID = "hybrid"  # Programmatic plan + adaptive upgrades for critical moments


class TokenBudgetMode(str, Enum):
    """How should token budget be enforced?"""
    HARD_CONSTRAINT = "hard"  # Simulation fails if budget exceeded
    SOFT_GUIDANCE = "soft"  # Target budget, allow 110% overage with warning
    MAX_QUALITY = "max"  # No budget limit, maximize fidelity
    ADAPTIVE_FALLBACK = "adaptive"  # Hit budget, exceed if validity requires it
    ORCHESTRATOR_DIRECTED = "orchestrator"  # Orchestrator decides dynamically
    USER_CONFIGURED = "user"  # User provides exact allocation


class FidelityTemporalStrategy(BaseModel):
    """
    Co-determined fidelity + temporal allocation strategy.

    This is the "musical score" that the TemporalAgent generates,
    specifying both WHEN timepoints occur and HOW MUCH DETAIL each has.
    """
    # Modal context
    mode: TemporalMode
    planning_mode: FidelityPlanningMode
    budget_mode: TokenBudgetMode
    token_budget: Optional[float] = None  # Total tokens (if budget_mode requires it)

    # Programmatic plan (if planning_mode=PROGRAMMATIC or HYBRID)
    timepoint_count: int  # Total number of timepoints
    fidelity_schedule: List[ResolutionLevel]  # Per-timepoint fidelity [TENSOR, SCENE, DIALOG, ...]
    temporal_steps: List[int]  # Month gaps between timepoints [3, 6, 1, 12, ...]

    # Adaptive parameters (if planning_mode=ADAPTIVE or HYBRID)
    adaptive_threshold: float = 0.7  # When to upgrade fidelity (e.g., pivot point score > 0.7)
    min_resolution: ResolutionLevel = ResolutionLevel.TENSOR_ONLY
    max_resolution: ResolutionLevel = ResolutionLevel.TRAINED

    # Metadata
    allocation_rationale: str  # Why this strategy? (for debugging/explainability)
    estimated_tokens: float  # Projected token usage
    estimated_cost_usd: float  # Projected cost

    # Post-execution tracking
    actual_tokens_used: Optional[float] = None
    actual_cost_usd: Optional[float] = None
    budget_compliance_ratio: Optional[float] = None  # actual/budget

class TTMTensor(SQLModel):
    """Timepoint Tensor Model - context, biology, behavior"""
    context_vector: bytes  # Serialized numpy array (knowledge, information)
    biology_vector: bytes  # Serialized numpy array (age, health, physical constraints)
    behavior_vector: bytes  # Serialized numpy array (personality, patterns, momentum)

    @classmethod
    def from_arrays(cls, context: np.ndarray, biology: np.ndarray, behavior: np.ndarray):
        import msgspec
        return cls(
            context_vector=msgspec.msgpack.encode(context.tolist()),
            biology_vector=msgspec.msgpack.encode(biology.tolist()),
            behavior_vector=msgspec.msgpack.encode(behavior.tolist())
        )

    def to_arrays(self):
        import msgspec
        return (
            np.array(msgspec.msgpack.decode(self.context_vector)),
            np.array(msgspec.msgpack.decode(self.biology_vector)),
            np.array(msgspec.msgpack.decode(self.behavior_vector))
        )


class PhysicalTensor(BaseModel):
    """Physical state tensor - age, health, pain, mobility"""
    age: float
    health_status: float = 1.0  # 0.0-1.0
    pain_level: float = 0.0  # 0.0-1.0
    pain_location: Optional[str] = None
    fever: float = 36.5  # Celsius, normal body temperature
    mobility: float = 1.0  # 0.0-1.0
    stamina: float = 1.0  # 0.0-1.0
    sensory_acuity: Dict[str, float] = {}  # vision, hearing, etc.
    location: Optional[tuple[float, float]] = None


class CognitiveTensor(BaseModel):
    """Cognitive state tensor - knowledge, emotions, energy"""
    knowledge_state: List[str] = []  # Changed from set to list for JSON serialization
    emotional_valence: float = 0.0  # -1.0 to 1.0
    emotional_arousal: float = 0.0  # 0.0 to 1.0
    energy_budget: float = 100.0  # Current available cognitive resources
    decision_confidence: float = 0.8  # Current certainty level
    patience_threshold: float = 50.0  # Tolerance for frustration
    risk_tolerance: float = 0.5  # 0.0-1.0, willingness to take risks
    social_engagement: float = 0.8  # 0.0-1.0, willingness to engage socially

class Entity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_id: str = Field(unique=True, index=True)
    entity_type: str = Field(default="human")  # Discriminator: "human", "animal", "building", "object", "abstract"
    timepoint: Optional[str] = Field(default=None, index=True)  # Which timepoint this entity exists at
    temporal_span_start: Optional[datetime] = None
    temporal_span_end: Optional[datetime] = None
    tensor: Optional[str] = Field(default=None, sa_column=Column(JSON))  # Serialized TTM
    training_count: int = Field(default=0)
    query_count: int = Field(default=0)
    eigenvector_centrality: float = Field(default=0.0)
    resolution_level: ResolutionLevel = Field(default=ResolutionLevel.TENSOR_ONLY)
    entity_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # Type-specific metadata

    # Tensor initialization and training tracking (NEW - Phase 11 Architecture Pivot)
    tensor_maturity: float = Field(default=0.0)  # 0.0-1.0 quality score, must be >= 0.95 to be operational
    tensor_training_cycles: int = Field(default=0)  # Number of training iterations completed

    @property
    def physical_tensor(self) -> Optional[PhysicalTensor]:
        """Get the physical tensor from entity metadata"""
        physical_data = self.entity_metadata.get("physical_tensor", {})
        if not physical_data or 'age' not in physical_data:
            return None  # No valid physical tensor data
        try:
            return PhysicalTensor(**physical_data)
        except Exception:
            return None  # Failed validation, return None instead of raising

    @physical_tensor.setter
    def physical_tensor(self, value: PhysicalTensor):
        """Set the physical tensor in entity metadata"""
        self.entity_metadata["physical_tensor"] = value.dict()

    @property
    def cognitive_tensor(self) -> Optional[CognitiveTensor]:
        """Get the cognitive tensor from entity metadata"""
        cognitive_data = self.entity_metadata.get("cognitive_tensor", {})
        if not cognitive_data:
            return None  # No cognitive tensor data
        try:
            return CognitiveTensor(**cognitive_data)
        except Exception:
            return None  # Failed validation, return None instead of raising

    @cognitive_tensor.setter
    def cognitive_tensor(self, value: CognitiveTensor):
        """Set the cognitive tensor in entity metadata"""
        self.entity_metadata["cognitive_tensor"] = value.dict()


# ============================================================================
# Scene-Level Entities (Mechanism 10)
# ============================================================================

class EnvironmentEntity(SQLModel, table=True):
    """Environmental context for scenes - location, capacity, conditions"""
    scene_id: str = Field(primary_key=True)
    timepoint_id: str = Field(foreign_key="timepoint.timepoint_id")
    location: str
    capacity: int
    ambient_temperature: float
    lighting_level: float  # 0.0-1.0 (dark to bright)
    weather: Optional[str] = None
    architectural_style: Optional[str] = None
    acoustic_properties: Optional[str] = None  # "reverberant", "muffled", etc.


class AtmosphereEntity(SQLModel, table=True):
    """Aggregated emotional and social atmosphere of a scene"""
    scene_id: str = Field(primary_key=True)
    timepoint_id: str = Field(foreign_key="timepoint.timepoint_id")
    tension_level: float  # 0.0-1.0 (calm to tense)
    formality_level: float  # 0.0-1.0 (casual to formal)
    emotional_valence: float  # -1.0 to 1.0 (negative to positive)
    emotional_arousal: float  # 0.0-1.0 (calm to excited)
    social_cohesion: float  # 0.0-1.0 (divided to united)
    energy_level: float  # 0.0-1.0 (lethargic to energetic)


class CrowdEntity(SQLModel, table=True):
    """Crowd dynamics and composition"""
    scene_id: str = Field(primary_key=True)
    timepoint_id: str = Field(foreign_key="timepoint.timepoint_id")
    size: int  # Number of people present
    density: float  # 0.0-1.0 (sparse to crowded)
    mood_distribution: str = Field(sa_column=Column(JSON))  # Dict[str, float]: mood -> percentage
    movement_pattern: str  # "static", "flowing", "agitated", "orderly"
    demographic_composition: Optional[str] = Field(default=None, sa_column=Column(JSON))  # Dict of demographic breakdowns
    noise_level: float  # 0.0-1.0 (quiet to loud)

class Timeline(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timeline_id: str = Field(unique=True, index=True)
    parent_timeline_id: Optional[str] = Field(default=None, foreign_key="timeline.timeline_id")  # NEW for branching
    branch_point: Optional[str] = Field(default=None)  # Timepoint where branch occurred
    intervention_description: Optional[str] = Field(default=None)  # Description of intervention
    temporal_mode: TemporalMode = Field(default=TemporalMode.PEARL)  # NEW: Causal regime
    # Original fields
    timepoint_id: str = Field(unique=True, index=True)
    timestamp: datetime
    resolution: str  # year, month, day, hour
    entities_present: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    events: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    training_status: str = Field(default="untrained")
    graph_data: Optional[str] = Field(default=None, sa_column=Column(JSON))

class SystemPrompt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    template: str
    version: int = Field(default=1)
    variables: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class ValidationRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    rule_type: str  # energy, temporal, biological, information
    severity: str  # ERROR, WARNING, INFO
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class ExposureEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_id: str = Field(foreign_key="entity.entity_id", index=True)
    event_type: str  # witnessed, learned, told, experienced
    information: str  # what was learned
    source: Optional[str] = None  # who/what provided the information
    timestamp: datetime
    confidence: float = Field(default=1.0)
    timepoint_id: Optional[str] = Field(default=None, index=True)  # link to timepoint
    run_id: Optional[str] = Field(default=None, index=True)  # link to simulation run for convergence

# ============================================================================
# Mechanism 5: Query Resolution - Query History Tracking
# ============================================================================

class QueryHistory(SQLModel, table=True):
    """Track query patterns for lazy resolution elevation (Mechanism 5)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    query_id: str = Field(unique=True, index=True)
    entity_id: str = Field(foreign_key="entity.entity_id", index=True)
    query_type: str  # knowledge, relationships, actions, dialog, general
    required_resolution: str  # The resolution level required for this query
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True  # Whether the query was successfully answered
    resolution_elevated: bool = False  # Whether resolution was elevated for this query

class Timepoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timepoint_id: str = Field(unique=True, index=True)
    timeline_id: Optional[str] = Field(default=None, index=True)  # NEW: for counterfactual branching
    timestamp: datetime
    event_description: str
    entities_present: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    causal_parent: Optional[str] = Field(default=None, index=True)  # previous timepoint_id
    resolution_level: ResolutionLevel = Field(default=ResolutionLevel.SCENE)
    run_id: Optional[str] = Field(default=None, index=True)  # link to simulation run for convergence

    def __init__(self, **data):
        """Validate entities_present on construction and warn if empty."""
        super().__init__(**data)
        # DATA QUALITY WARNING: Empty entities_present indicates potential data integrity issue
        if not self.entities_present or len(self.entities_present) == 0:
            import warnings
            warnings.warn(
                f"Timepoint '{self.timepoint_id}' created with empty entities_present. "
                f"Event: '{self.event_description[:50]}...' - This may indicate entity inference is not working.",
                UserWarning,
                stacklevel=2
            )


# ============================================================================
# Dialog Synthesis (Mechanism 11)
# ============================================================================

class DialogTurn(BaseModel):
    """Single turn in a dialog conversation"""
    speaker: str  # entity_id of speaker
    content: str  # what was said
    timestamp: datetime
    emotional_tone: Optional[str] = None  # inferred emotional tone
    knowledge_references: List[str] = []  # knowledge items referenced
    confidence: float = 1.0  # confidence in generation
    physical_state_influence: Optional[str] = None  # how physical state affected utterance

    @field_validator('knowledge_references', mode='before')
    @classmethod
    def convert_none_to_empty_list(cls, v):
        """Convert None to [] for LLM compatibility"""
        return v if v is not None else []


class DialogData(BaseModel):
    """Structured data for dialog generation"""
    turns: List[DialogTurn]
    total_duration: Optional[int] = None  # estimated duration in seconds
    information_exchanged: List[str] = []  # knowledge items passed between entities
    relationship_impacts: Dict[str, float] = {}  # how relationships changed (entity_pair -> delta)
    atmosphere_evolution: List[Dict[str, float]] = []  # atmosphere changes over time

    @field_validator('relationship_impacts', mode='before')
    @classmethod
    def flatten_nested_relationship_impacts(cls, v):
        """
        Flatten nested relationship_impacts from LLM output.

        LLMs often return: {"entity_a": {"entity_b": 0.2, "entity_c": 0.3}, ...}
        But schema expects: {"entity_a_entity_b": 0.2, "entity_a_entity_c": 0.3, ...}
        """
        if not v:
            return {}
        if not isinstance(v, dict):
            return {}

        # Check if already flat (all values are floats/ints)
        all_flat = all(isinstance(val, (int, float)) for val in v.values())
        if all_flat:
            return v

        # Flatten nested dict
        flattened = {}
        for entity_a, impacts in v.items():
            if isinstance(impacts, dict):
                for entity_b, delta in impacts.items():
                    if isinstance(delta, (int, float)):
                        # Create sorted key to avoid duplicate pairs
                        pair_key = f"{entity_a}_{entity_b}"
                        flattened[pair_key] = float(delta)
            elif isinstance(impacts, (int, float)):
                # Already flat pair
                flattened[entity_a] = float(impacts)
        return flattened


# ============================================================================
# Knowledge Extraction (M19 - LLM-based knowledge item extraction)
# ============================================================================

class KnowledgeItem(BaseModel):
    """
    A meaningful knowledge item extracted from dialog by the Knowledge Extraction Agent.

    Unlike naive word extraction, these are semantic units representing actual
    information transfer: facts, decisions, opinions, plans, revelations.

    Created by: workflows/knowledge_extraction.py
    Used by: M3 (Exposure Events), M11 (Dialog Synthesis)
    """
    content: str  # The actual knowledge (complete semantic unit, not a word)
    speaker: str  # entity_id who shared this knowledge
    listeners: List[str]  # entity_ids who received this knowledge
    category: str  # fact, decision, opinion, plan, revelation, question, agreement
    confidence: float = 0.9  # 0.0-1.0, extraction confidence
    context: Optional[str] = None  # Why this knowledge matters in the scene
    source_turn_index: Optional[int] = None  # Which dialog turn this came from
    causal_relevance: float = 0.5  # 0.0-1.0, how important for causal chain


class KnowledgeExtractionResult(BaseModel):
    """Result of LLM-based knowledge extraction from a dialog."""
    items: List[KnowledgeItem]
    dialog_id: str
    timepoint_id: str
    extraction_model: str  # Which LLM performed extraction
    total_turns_analyzed: int
    items_per_turn: float  # Average knowledge items per turn
    extraction_timestamp: datetime


class Dialog(SQLModel, table=True):
    """Complete dialog conversation between entities"""
    id: Optional[int] = Field(default=None, primary_key=True)
    dialog_id: str = Field(unique=True, index=True)
    timepoint_id: str = Field(foreign_key="timepoint.timepoint_id", index=True)
    participants: str = Field(sa_column=Column(JSON))  # JSON list of entity_ids
    turns: str = Field(sa_column=Column(JSON))  # JSON list of DialogTurn dicts
    context_used: str = Field(sa_column=Column(JSON))  # JSON dict of context flags
    duration_seconds: Optional[int] = None
    information_transfer_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    run_id: Optional[str] = Field(default=None, index=True)  # Link to simulation run for convergence (January 2026)


# ============================================================================
# Multi-Entity Synthesis (Mechanism 13)
# ============================================================================

class RelationshipMetrics(BaseModel):
    """Metrics quantifying relationship between two entities"""
    shared_knowledge: int = 0  # number of shared knowledge items
    belief_alignment: float = 0.0  # -1.0 to 1.0, how aligned beliefs are
    interaction_count: int = 0  # number of past interactions
    trust_level: float = 0.5  # 0.0-1.0, current trust level
    emotional_bond: float = 0.0  # -1.0 to 1.0, emotional connection
    power_dynamic: float = 0.0  # -1.0 to 1.0, relative power (-1 = entity_a subordinate)


class RelationshipState(BaseModel):
    """Relationship state at a specific timepoint"""
    entity_a: str
    entity_b: str
    timestamp: datetime
    timepoint_id: str
    metrics: RelationshipMetrics
    recent_events: List[str] = []  # recent events affecting relationship


class RelationshipTrajectory(SQLModel, table=True):
    """Trajectory of relationship evolution over time"""
    id: Optional[int] = Field(default=None, primary_key=True)
    trajectory_id: str = Field(unique=True, index=True)
    entity_a: str = Field(index=True)
    entity_b: str = Field(index=True)
    start_timepoint: str
    end_timepoint: str
    states: str = Field(sa_column=Column(JSON))  # JSON list of RelationshipState dicts
    overall_trend: str  # "improving", "deteriorating", "stable", "volatile"
    key_events: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    relationship_type: Optional[str] = Field(default=None)  # "ally", "rival", "friend", etc.
    current_strength: Optional[float] = Field(default=None)  # 0.0-1.0 relationship weight
    context_summary: Optional[str] = Field(default=None)  # Brief description of relationship


class Contradiction(BaseModel):
    """Identified contradiction between entities' knowledge/beliefs"""
    entity_a: str
    entity_b: str
    topic: str  # the subject of the contradiction
    position_a: float  # entity_a's position/stance (-1.0 to 1.0)
    position_b: float  # entity_b's position/stance (-1.0 to 1.0)
    severity: float  # 0.0-1.0, how significant the contradiction is
    timepoint_id: str
    context: str  # description of the contradictory statements
    resolution_possible: bool = True  # whether this can be resolved through discussion


class ComparativeAnalysis(BaseModel):
    """Results of comparing multiple entities across timepoints"""
    analysis_id: str
    entities_compared: List[str]
    timepoints_covered: List[str]
    relationship_trajectories: List[str]  # trajectory_ids
    contradictions_found: List[Contradiction]
    consensus_topics: List[str] = []  # topics where entities agree
    conflict_topics: List[str] = []  # topics where entities disagree
    information_flow_patterns: Dict[str, List[str]] = {}  # who learned what from whom


# ============================================================================
# Mechanism 14: Circadian Activity Patterns
# ============================================================================

class CircadianContext(BaseModel):
    """Time-of-day context for entity activities"""
    hour: int  # 0-23
    typical_activities: Dict[str, float]  # activity -> probability
    ambient_conditions: Dict[str, float]  # lighting, noise, etc.
    social_constraints: List[str]  # time-appropriate social norms
    fatigue_level: float = 0.0  # 0.0-1.0 accumulated fatigue
    energy_penalty: float = 1.0  # multiplier for energy costs


# ============================================================================
# Mechanism 15: Entity Prospection
# ============================================================================

class Expectation(BaseModel):
    """An entity's expectation about a future event"""
    predicted_event: str
    subjective_probability: float  # 0.0-1.0
    desired_outcome: bool
    preparation_actions: List[str] = []  # Actions entity plans to take
    confidence: float = 1.0  # 0.0-1.0, how confident entity is in this expectation
    time_horizon_days: int = 30  # How far in future this expectation applies


class ProspectiveState(SQLModel, table=True):
    """An entity's internal forecasting and expectations"""
    id: Optional[int] = Field(default=None, primary_key=True)
    prospective_id: str = Field(unique=True, index=True)
    entity_id: str = Field(foreign_key="entity.entity_id", index=True)
    timepoint_id: str = Field(foreign_key="timepoint.timepoint_id", index=True)
    forecast_horizon_days: int = 30
    expectations: str = Field(sa_column=Column(JSON))  # List[Expectation] as JSON
    contingency_plans: str = Field(sa_column=Column(JSON), default_factory=dict)  # Dict[str, List[str]]
    anxiety_level: float = 0.0  # 0.0-1.0
    forecast_confidence: float = 1.0  # Overall confidence in forecasting ability
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Mechanism 12: Counterfactual Branching
# ============================================================================

class Intervention(BaseModel):
    """A modification applied to create a counterfactual branch"""
    type: str  # "entity_removal", "entity_modification", "event_cancellation", "knowledge_alteration"
    target: str  # entity_id or event_id
    parameters: Dict[str, Any] = {}  # Additional parameters for the intervention
    description: str = ""  # Human-readable description


class BranchComparison(BaseModel):
    """Results of comparing two timeline branches"""
    baseline_timeline: str
    counterfactual_timeline: str
    divergence_point: Optional[str]  # First timepoint where timelines differ
    metrics: Dict[str, Dict[str, float]] = {}  # metric_name -> {"baseline": val, "counterfactual": val, "delta": diff}
    causal_explanation: str = ""  # Explanation of why branches diverged
    key_events_differed: List[str] = []  # Events that occurred differently
    entity_states_differed: List[str] = []  # Entities whose states diverged


# ============================================================================
# Mechanism 16: Animistic Entity Extension
# ============================================================================

class AnimalEntity(BaseModel):
    """Biological state and capabilities of animal entities"""
    species: str
    biological_state: Dict[str, float] = {}  # age, health, energy, hunger, stress, etc.
    training_level: float = 0.0  # 0.0-1.0, how trained/domesticated
    goals: List[str] = []  # Simple behavioral goals: "avoid_pain", "seek_food", "trust_handler", etc.
    sensory_capabilities: Dict[str, float] = {}  # vision, hearing, smell acuity
    physical_capabilities: Dict[str, float] = {}  # strength, speed, endurance


class BuildingEntity(BaseModel):
    """Physical and functional properties of building entities"""
    structural_integrity: float = 1.0  # 0.0-1.0, current condition
    capacity: int = 0  # Maximum occupancy
    age: int = 0  # Age in years
    maintenance_state: float = 1.0  # 0.0-1.0, how well maintained
    constraints: List[str] = []  # Limitations: "cannot_move", "weather_dependent", "capacity_limited"
    affordances: List[str] = []  # What it enables: "shelter", "symbolize_authority", "storage"


class AbstractEntity(BaseModel):
    """Properties of conceptual/abstract entities"""
    propagation_vector: List[float] = []  # How concept spreads through population
    intensity: float = 1.0  # Current strength/potency of the concept
    carriers: List[str] = []  # Entity IDs holding this concept
    decay_rate: float = 0.01  # How quickly the concept fades
    coherence: float = 1.0  # Internal consistency of the concept
    manifestation_forms: List[str] = []  # How concept manifests: "beliefs", "behaviors", "cultural_practices"


class AnyEntity(BaseModel):
    """Highly adaptive entity that can represent literally anything in the animistic framework"""
    adaptability_score: float = 1.0  # 0.0-1.0, how easily it can change form/behavior
    morphing_capability: Dict[str, float] = {}  # What it can morph into and probability
    essence_type: str = "unknown"  # Core nature: "physical", "spiritual", "conceptual", "chaotic"
    manifestation_forms: List[str] = []  # Current and potential forms it can take
    stability_index: float = 0.5  # 0.0-1.0, how stable its current form is
    influence_radius: float = 0.0  # How far its animistic presence extends
    resonance_patterns: Dict[str, float] = {}  # How it resonates with different entity types
    adaptive_goals: List[str] = []  # Goals that change based on context and interactions


class KamiEntity(BaseModel):
    """Spiritual/supernatural entity (kami) with visibility and disclosure properties"""
    visibility_state: str = "invisible"  # "visible", "invisible", "partially_visible", "disguised"
    disclosure_level: str = "unknown"  # "unknown", "rumored", "known", "worshiped", "feared"
    influence_domain: List[str] = []  # Areas of influence: "nature", "weather", "emotions", "fate", "protection"
    manifestation_probability: float = 0.1  # 0.0-1.0, likelihood of appearing to mortals
    spiritual_power: float = 0.5  # 0.0-1.0, strength of supernatural influence
    mortal_perception: Dict[str, float] = {}  # How different entity types perceive this kami
    sacred_sites: List[str] = []  # Locations where this kami is particularly strong
    blessings_curses: Dict[str, List[str]] = {}  # Positive/negative effects it can bestow
    worshipers: List[str] = []  # Entity IDs that acknowledge/worship this kami
    taboo_violations: List[str] = []  # Actions that anger or weaken this kami


class AIEntity(BaseModel):
    """AI-powered entity with external agent integration capabilities"""
    # Core AI parameters
    temperature: float = 0.7  # 0.0-2.0, randomness in generation
    top_p: float = 0.9  # 0.0-1.0, nucleus sampling
    max_tokens: int = 1000  # Maximum tokens to generate
    frequency_penalty: float = 0.0  # -2.0-2.0, repetition penalty
    presence_penalty: float = 0.0  # -2.0-2.0, topic diversity
    model_name: str = "gpt-3.5-turbo"  # AI model to use

    # System prompt and context
    system_prompt: str = ""  # Core personality and behavior instructions
    context_injection: Dict[str, Any] = {}  # Dynamic context to inject
    knowledge_base: List[str] = []  # Domain-specific knowledge
    behavioral_constraints: List[str] = []  # Safety and behavioral rules

    # Operational parameters
    activation_threshold: float = 0.5  # Confidence threshold for responses
    response_cache_ttl: int = 300  # Cache responses for N seconds
    rate_limit_per_minute: int = 60  # API call limits
    safety_level: str = "moderate"  # "minimal", "moderate", "strict", "maximum"

    # Integration capabilities
    api_endpoints: Dict[str, str] = {}  # Available API endpoints
    webhook_urls: List[str] = []  # Webhook destinations
    integration_tokens: Dict[str, str] = {}  # API tokens for external services

    # Monitoring and control
    performance_metrics: Dict[str, float] = {}  # Response time, accuracy, etc.
    error_handling: Dict[str, str] = {}  # Error response strategies
    fallback_responses: List[str] = []  # Default responses when AI fails

    # Safety and validation
    input_bleaching_rules: List[str] = []  # Input sanitization patterns
    output_filtering_rules: List[str] = []  # Output content filters
    prohibited_topics: List[str] = []  # Topics to avoid
    required_disclaimers: List[str] = []  # Required safety notices


# ============================================================================
# LLM Response Schemas (moved from llm.py to break circular dependency)
# ============================================================================

class EntityPopulation(BaseModel):
    """Structured output schema for entity population from LLM"""
    entity_id: str = ""
    knowledge_state: List[str] = []
    energy_budget: float = 50.0
    personality_traits: List[float] = [0.0, 0.0, 0.0, 0.0, 0.0]
    temporal_awareness: str = "present"
    confidence: float = 0.5


class ValidationResult(BaseModel):
    """Structured validation result from LLM"""
    is_valid: bool
    violations: List[str]
    confidence: float
    reasoning: str


# ============================================================================
# Entity Type Converters
# ============================================================================

def entity_population_to_entity(population, entity_id: str, entity_type: str = "human",
                                timepoint: Optional[str] = None,
                                resolution_level: ResolutionLevel = ResolutionLevel.FULL_DETAIL) -> "Entity":
    """
    Convert an EntityPopulation (from LLM) to an Entity (for database).

    Args:
        population: EntityPopulation object from LLM
        entity_id: Entity identifier
        entity_type: Type of entity (human, animal, etc.)
        timepoint: Timepoint identifier
        resolution_level: Resolution level for entity

    Returns:
        Entity object ready for database storage
    """
    # EntityPopulation is now defined in this file - no circular import needed

    # Handle both EntityPopulation objects and dicts
    if isinstance(population, EntityPopulation):
        knowledge_state = population.knowledge_state
        energy_budget = population.energy_budget
        personality_traits = population.personality_traits
        temporal_awareness = population.temporal_awareness
        confidence = population.confidence
    else:
        # Assume it's a dict-like object
        knowledge_state = getattr(population, 'knowledge_state', [])
        energy_budget = getattr(population, 'energy_budget', 50.0)
        personality_traits = getattr(population, 'personality_traits', [0.0, 0.0, 0.0, 0.0, 0.0])
        temporal_awareness = getattr(population, 'temporal_awareness', 'present')
        confidence = getattr(population, 'confidence', 0.5)

    # Create cognitive tensor from EntityPopulation data
    cognitive = CognitiveTensor(
        knowledge_state=knowledge_state,
        energy_budget=energy_budget,
        decision_confidence=confidence
    )

    # Create entity with metadata
    entity = Entity(
        entity_id=entity_id,
        entity_type=entity_type,
        timepoint=timepoint,
        resolution_level=resolution_level,
        entity_metadata={
            "cognitive_tensor": cognitive.model_dump(),
            "personality_traits": personality_traits,
            "temporal_awareness": temporal_awareness,
            "llm_generated": True
        }
    )

    return entity


# ============================================================================
# Convergence Evaluation (Cross-run causal graph comparison)
# ============================================================================

class ConvergenceSet(SQLModel, table=True):
    """
    Results of convergence analysis across multiple simulation runs.

    Measures agreement in causal graphs across independent runs (different
    models/seeds/modes). High convergence indicates robust causal mechanisms.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    set_id: str = Field(unique=True, index=True)  # Unique identifier
    template_id: Optional[str] = Field(default=None, index=True)  # Source template
    run_ids: str = Field(sa_column=Column(JSON))  # JSON list of run_ids compared
    run_count: int = Field(default=2)  # Number of runs compared

    # Core metrics
    convergence_score: float = Field(default=0.0)  # Mean Jaccard similarity [0.0-1.0]
    min_similarity: float = Field(default=0.0)  # Worst-case pairwise similarity
    max_similarity: float = Field(default=0.0)  # Best-case pairwise similarity
    robustness_grade: str = Field(default="F")  # A/B/C/D/F grade

    # Divergence details
    consensus_edge_count: int = Field(default=0)  # Edges in ALL runs
    contested_edge_count: int = Field(default=0)  # Edges in SOME runs
    divergence_points: str = Field(default="[]", sa_column=Column(JSON))  # JSON list of divergent edges

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    extra_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


# ============================================================================
# Mechanism 17: Modal Temporal Causality
# ============================================================================