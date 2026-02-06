"""
Directorial Strategy - Narrative-driven temporal simulation with dramatic arc

This module implements DIRECTORIAL mode temporal reasoning, where simulations are
structured around dramatic narrative arcs (five-act structure), camera/POV systems,
and tension curves that drive the pacing and detail level of generated content.

Example:
    Scenario: "Macbeth's rise and fall"
    Arc: Setup → Rising → Climax → Falling → Resolution
    Goal: Generate narratively coherent paths with dramatic tension

Architecture:
    - Arc Engine: Plans five-act narrative structure with beats and character arcs
    - Camera System: Controls POV rotation, framing, and parallel storylines
    - Fidelity Mapping: Maps dramatic importance to resolution level
    - Tension Curve: Programmatic + LLM-adjusted tension targeting per step
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np
import uuid

from schemas import Entity, Timepoint, TemporalMode, ResolutionLevel
from generation.config_schema import TemporalConfig
from llm_service.model_selector import ActionType, get_token_estimator
from pydantic import BaseModel

# Directorial mode requires a model with reliable structured JSON output.
# Llama 4 Scout frequently returns malformed JSON for complex schemas.
DIRECTORIAL_MODEL = "qwen/qwen-2.5-72b-instruct"


# ============================================================================
# Pydantic Response Models
# ============================================================================

class ActDescription(BaseModel):
    """Description of a single act in the narrative plan"""
    name: str
    start_pct: float
    end_pct: float
    description: str


class CharacterArc(BaseModel):
    """Character arc description"""
    entity_id: str
    arc_type: str  # "protagonist", "antagonist", "supporting", "catalyst"
    arc_description: str
    key_moments: List[str]


class NarrativePlan(BaseModel):
    """LLM-generated five-act narrative structure"""
    acts: List[ActDescription]
    beats: List[str]
    character_arcs: List[CharacterArc]
    central_conflict: str
    thematic_elements: List[str]


class POVEntry(BaseModel):
    """Single POV rotation entry"""
    act: str
    pov_entity: str
    framing: str
    rationale: str


class StorylineThread(BaseModel):
    """A parallel storyline thread"""
    thread_id: str
    thread_name: str
    entities: List[str]
    acts_active: List[str]


class CameraPlan(BaseModel):
    """LLM-generated camera/POV plan"""
    pov_rotation: List[POVEntry]
    framing_by_act: Dict[str, str]
    storyline_threads: List[StorylineThread]


class DirectorialStateSchema(BaseModel):
    """Schema for LLM-generated directorial state"""
    description: str
    key_events: List[str]
    tension_assessment: float
    irony_potential: str
    emotional_beat: str


class NarrativeValidation(BaseModel):
    """LLM validation of narrative coherence"""
    arc_score: float
    tension_fit: float
    pov_notes: str
    issues: List[str]


class TensionAdjustment(BaseModel):
    """LLM adjustment of tension for a specific state"""
    adjusted_tension: float
    reasoning: str


class IronyDetection(BaseModel):
    """LLM detection of dramatic irony"""
    has_irony: bool
    irony_description: str
    audience_knows: List[str]
    character_unaware: List[str]
    irony_entities: List[str]


# ============================================================================
# Dataclasses
# ============================================================================

class ActPhase(str, Enum):
    """Five-act structure phases"""
    SETUP = "setup"
    RISING = "rising"
    CLIMAX = "climax"
    FALLING = "falling"
    RESOLUTION = "resolution"


class Framing(str, Enum):
    """Camera framing types"""
    WIDE = "wide"
    CLOSE = "close"
    OVERHEAD = "overhead"
    SUBJECTIVE = "subjective"
    ENSEMBLE = "ensemble"


@dataclass
class DirectorialState:
    """A state in the directorial simulation with arc and camera metadata"""
    year: int
    month: int
    description: str
    entities: List[Entity]
    world_state: Dict[str, Any]
    plausibility_score: float = 0.0
    parent_state: Optional['DirectorialState'] = None
    children_states: List['DirectorialState'] = field(default_factory=list)
    resolution_level: ResolutionLevel = None

    # Arc engine fields
    act: ActPhase = ActPhase.SETUP
    act_position: float = 0.0  # 0.0-1.0 within act
    tension_score: float = 0.3
    tension_delta: float = 0.0
    dramatic_irony: bool = False
    irony_entities: List[str] = field(default_factory=list)
    narrative_beat: str = ""

    # Camera fields
    pov_entity: str = ""
    framing: Framing = Framing.WIDE
    parallel_storyline: str = ""
    focus_weight: float = 1.0

    # Fidelity mapping
    dramatic_importance: float = 0.5  # 0.0-1.0, drives resolution

    def __post_init__(self):
        if self.children_states is None:
            self.children_states = []
        if not (1 <= self.month <= 12):
            self.month = 1
        if self.resolution_level is None:
            self.resolution_level = ResolutionLevel.SCENE
        if self.irony_entities is None:
            self.irony_entities = []

    def to_year_month_str(self) -> str:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{month_names[self.month-1]} {self.year}"

    def to_total_months(self) -> int:
        return self.year * 12 + self.month


@dataclass
class DirectorialPath:
    """Complete narrative path through the directorial simulation"""
    path_id: str
    states: List[DirectorialState]
    coherence_score: float
    arc_completion_score: float = 0.0
    tension_curve: List[float] = field(default_factory=list)
    act_boundaries: Dict[str, int] = field(default_factory=dict)
    pov_distribution: Dict[str, int] = field(default_factory=dict)
    storyline_threads: List[str] = field(default_factory=list)
    explanation: str = ""
    validation_details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.tension_curve is None:
            self.tension_curve = []
        if self.act_boundaries is None:
            self.act_boundaries = {}
        if self.pov_distribution is None:
            self.pov_distribution = {}
        if self.storyline_threads is None:
            self.storyline_threads = []
        if self.validation_details is None:
            self.validation_details = {}


# ============================================================================
# DirectorialStrategy
# ============================================================================

class DirectorialStrategy:
    """
    Narrative-driven temporal simulation strategy.

    Process:
    1. Plan five-act narrative structure with beats and character arcs
    2. Generate origin state with entity inference
    3. Plan programmatic tension curve per act
    4. Plan camera/POV schedule
    5. Generate directed paths with act-aware prompting
    6. Validate narrative coherence
    7. Rank paths by composite score
    8. Populate metadata (act boundaries, tension curves)
    """

    def __init__(self, config: TemporalConfig, llm_client, store):
        if config.mode != TemporalMode.DIRECTORIAL:
            raise ValueError(f"DirectorialStrategy requires mode=DIRECTORIAL, got {config.mode}")

        self.config = config
        self.llm = llm_client
        self.store = store
        self.paths: List[DirectorialPath] = []
        self.all_paths: List[DirectorialPath] = []

        # Directorial parameters
        self.forward_steps = getattr(config, 'backward_steps', 15)
        self.path_count = getattr(config, 'path_count', 3)
        self.dramatic_tension = getattr(config, 'dramatic_tension', 0.7)
        self.narrative_arc = getattr(config, 'narrative_arc', 'rising_action')

        # Narrative plan (populated during run)
        self.narrative_plan: Optional[NarrativePlan] = None
        self.camera_plan: Optional[CameraPlan] = None
        self.tension_targets: List[float] = []

    def run(self) -> List[DirectorialPath]:
        """Execute directorial narrative simulation."""
        print(f"\n{'='*80}")
        print(f"DIRECTORIAL MODE: Narrative-Driven Simulation")
        print(f"Steps: {self.forward_steps}")
        print(f"Target paths: {self.path_count}")
        print(f"Dramatic tension: {self.dramatic_tension}")
        print(f"{'='*80}\n")

        # Step 1: Plan narrative structure
        print("Step 1: Planning narrative structure...")
        self.narrative_plan = self._plan_narrative_structure()
        print(f"  Acts: {len(self.narrative_plan.acts)}")
        print(f"  Beats: {len(self.narrative_plan.beats)}")
        print(f"  Character arcs: {len(self.narrative_plan.character_arcs)}")

        # Step 2: Generate origin state
        print("\nStep 2: Generating origin state...")
        origin = self._generate_origin_state()
        print(f"  Origin: {origin.to_year_month_str()}")

        # Step 3: Plan tension curve
        print("\nStep 3: Planning tension curve...")
        self.tension_targets = self._plan_tension_curve()
        print(f"  Tension targets: {[f'{t:.2f}' for t in self.tension_targets[:5]]}...")

        # Step 4: Plan camera schedule
        print("\nStep 4: Planning camera schedule...")
        self.camera_plan = self._plan_camera_schedule()
        print(f"  POV entries: {len(self.camera_plan.pov_rotation)}")
        print(f"  Storyline threads: {len(self.camera_plan.storyline_threads)}")

        # Step 5: Explore directed paths
        print(f"\nStep 5: Exploring directed paths (generating {self.path_count} paths)...")
        candidate_paths = self._explore_directed_paths(origin)
        print(f"  Generated {len(candidate_paths)} candidate paths")

        # Step 6: Validate narrative coherence
        print("\nStep 6: Validating narrative coherence...")
        validated_paths = self._validate_narrative_coherence(candidate_paths)
        print(f"  {len(validated_paths)} paths passed validation")

        # Step 7: Rank paths
        print("\nStep 7: Ranking paths...")
        ranked_paths = self._rank_paths(validated_paths)

        # Step 8: Populate metadata
        print("\nStep 8: Populating metadata...")
        for path in ranked_paths:
            self._populate_path_metadata(path)

        self.all_paths = ranked_paths
        self.paths = ranked_paths[:self.path_count]

        print(f"\n{'='*80}")
        print(f"DIRECTORIAL SIMULATION COMPLETE")
        print(f"Total paths: {len(self.all_paths)}")
        print(f"Best arc completion: {self.all_paths[0].arc_completion_score:.3f}" if self.all_paths else "")
        print(f"{'='*80}\n")

        return self.all_paths

    # ========================================================================
    # Arc Engine (5 methods)
    # ========================================================================

    def _plan_narrative_structure(self) -> NarrativePlan:
        """LLM structured call to plan five-act structure with beats and character arcs."""
        description = getattr(self.config, 'portal_description', None) or \
                     getattr(self.config, 'scenario_description', 'A dramatic narrative unfolds')

        entity_names = []
        if self.store:
            try:
                all_entities = self.store.list_entities() if hasattr(self.store, 'list_entities') else []
                entity_names = [e.entity_id for e in all_entities[:10]]
            except Exception:
                pass

        if not self.llm:
            return self._fallback_narrative_plan(entity_names)

        system_prompt = "You are an expert dramatist and narrative architect."
        user_prompt = f"""Plan a five-act dramatic structure for this scenario.

SCENARIO:
{description[:500]}

ENTITIES: {', '.join(entity_names[:8]) if entity_names else 'To be determined'}

Create a narrative plan with:
1. Five acts (setup, rising, climax, falling, resolution) with percentage boundaries
2. Key narrative beats (8-12 specific moments)
3. Character arcs for each major entity
4. Central conflict driving the narrative
5. Thematic elements

Each act should have:
- name: The act name (setup/rising/climax/falling/resolution)
- start_pct: Start percentage of the narrative (0.0-1.0)
- end_pct: End percentage of the narrative (0.0-1.0)
- description: What happens in this act

Each beat should be a SHORT STRING describing the moment, e.g.:
  "Holmes discovers the cipher", "Villagers confront the hound"
Do NOT use objects for beats — return a flat list of strings.

Each character_arc should have these exact fields:
- entity_id: The entity name from the ENTITIES list above (e.g. "{entity_names[0] if entity_names else 'protagonist'}")
- arc_type: One of "protagonist", "antagonist", "supporting", "catalyst"
- arc_description: A sentence describing this character's journey
- key_moments: A list of strings naming key moments (e.g. ["introduction", "crisis", "resolution"])

Return structured JSON matching this exact schema."""

        try:
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=NarrativePlan,
                model=DIRECTORIAL_MODEL,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=2000
            )
            return result
        except Exception as e:
            print(f"    Narrative planning failed: {e}")
            return self._fallback_narrative_plan(entity_names)

    def _fallback_narrative_plan(self, entity_names: List[str]) -> NarrativePlan:
        """Generate a fallback narrative plan without LLM."""
        protagonist = entity_names[0] if entity_names else "protagonist"
        return NarrativePlan(
            acts=[
                ActDescription(name="setup", start_pct=0.0, end_pct=0.2,
                             description="Establishing the world and introducing characters"),
                ActDescription(name="rising", start_pct=0.2, end_pct=0.5,
                             description="Tensions escalate and conflicts emerge"),
                ActDescription(name="climax", start_pct=0.5, end_pct=0.7,
                             description="The central confrontation or crisis point"),
                ActDescription(name="falling", start_pct=0.7, end_pct=0.85,
                             description="Consequences unfold and tensions begin to resolve"),
                ActDescription(name="resolution", start_pct=0.85, end_pct=1.0,
                             description="New equilibrium established"),
            ],
            beats=[
                "Introduction of setting",
                "Key characters meet",
                "First complication arises",
                "Stakes are raised",
                "Point of no return",
                "Climactic confrontation",
                "Reversal or revelation",
                "Consequences revealed",
                "Resolution achieved",
            ],
            character_arcs=[
                CharacterArc(
                    entity_id=protagonist,
                    arc_type="protagonist",
                    arc_description=f"{protagonist} faces the central challenge",
                    key_moments=["introduction", "decision", "climax", "resolution"]
                )
            ],
            central_conflict="The central tension driving events forward",
            thematic_elements=["conflict", "change", "consequence"]
        )

    def _plan_tension_curve(self) -> List[float]:
        """
        Programmatic tension target per step based on act boundaries.

        Tension ranges per act:
        - Setup: 0.2-0.4
        - Rising: 0.4-0.7
        - Climax: 0.8-1.0
        - Falling: 0.5-0.3
        - Resolution: 0.1-0.2
        """
        tension_ranges = {
            ActPhase.SETUP: (0.2, 0.4),
            ActPhase.RISING: (0.4, 0.7),
            ActPhase.CLIMAX: (0.8, 1.0),
            ActPhase.FALLING: (0.5, 0.3),  # Decreasing
            ActPhase.RESOLUTION: (0.1, 0.2),
        }

        targets = []
        for step in range(self.forward_steps):
            act = self._determine_act_for_step(step)
            low, high = tension_ranges.get(act, (0.3, 0.5))

            # Position within the act
            act_start, act_end = self._get_act_step_range(act)
            act_length = max(1, act_end - act_start)
            position = (step - act_start) / act_length

            # Interpolate tension within the range
            if low <= high:
                tension = low + (high - low) * position
            else:
                # Decreasing range (falling action)
                tension = low + (high - low) * position

            # Scale by configured dramatic_tension
            tension = tension * self.dramatic_tension

            targets.append(max(0.0, min(1.0, tension)))

        return targets

    def _determine_act_for_step(self, step: int) -> ActPhase:
        """Map a step index to its act phase using narrative plan boundaries."""
        if not self.narrative_plan or not self.narrative_plan.acts:
            # Fallback: equal distribution
            position = step / max(1, self.forward_steps)
            if position < 0.2:
                return ActPhase.SETUP
            elif position < 0.5:
                return ActPhase.RISING
            elif position < 0.7:
                return ActPhase.CLIMAX
            elif position < 0.85:
                return ActPhase.FALLING
            else:
                return ActPhase.RESOLUTION

        position = step / max(1, self.forward_steps)

        for act_desc in self.narrative_plan.acts:
            if act_desc.start_pct <= position < act_desc.end_pct:
                try:
                    return ActPhase(act_desc.name)
                except ValueError:
                    pass

        return ActPhase.RESOLUTION

    def _get_act_step_range(self, act: ActPhase) -> Tuple[int, int]:
        """Get the step index range for a given act."""
        if not self.narrative_plan or not self.narrative_plan.acts:
            act_ranges = {
                ActPhase.SETUP: (0.0, 0.2),
                ActPhase.RISING: (0.2, 0.5),
                ActPhase.CLIMAX: (0.5, 0.7),
                ActPhase.FALLING: (0.7, 0.85),
                ActPhase.RESOLUTION: (0.85, 1.0),
            }
            low_pct, high_pct = act_ranges.get(act, (0.0, 1.0))
        else:
            low_pct, high_pct = 0.0, 1.0
            for act_desc in self.narrative_plan.acts:
                try:
                    if ActPhase(act_desc.name) == act:
                        low_pct = act_desc.start_pct
                        high_pct = act_desc.end_pct
                        break
                except ValueError:
                    continue

        start = int(low_pct * self.forward_steps)
        end = int(high_pct * self.forward_steps)
        return start, end

    def _compute_tension_for_state(self, state: DirectorialState, step: int) -> float:
        """
        Start from programmatic target tension, LLM adjusts based on actual events.

        The programmatic target provides the baseline, then the LLM can adjust
        up or down based on what actually happened in the generated state.
        """
        # Get programmatic target
        if step < len(self.tension_targets):
            target = self.tension_targets[step]
        else:
            target = 0.5

        if not self.llm:
            return target

        # LLM adjusts based on actual state content
        try:
            system_prompt = "You are an expert at evaluating dramatic tension in narratives."
            user_prompt = f"""Rate the actual tension level of this scene relative to the target.

TARGET TENSION: {target:.2f}
ACT: {state.act.value}

SCENE:
{state.description[:300]}

KEY EVENTS: {state.world_state.get('key_events', [])}

Adjust the tension score based on:
- Does the scene content match the target tension?
- Are there unexpected high-tension or low-tension elements?
- Return adjusted_tension between 0.0 and 1.0
- Return reasoning for the adjustment"""

            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=TensionAdjustment,
                model=DIRECTORIAL_MODEL,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=300
            )

            # Blend target with LLM adjustment (70% target, 30% LLM)
            adjusted = target * 0.7 + result.adjusted_tension * 0.3
            return max(0.0, min(1.0, adjusted))

        except Exception:
            return target

    def _detect_dramatic_irony(self, state: DirectorialState) -> Tuple[bool, str, List[str]]:
        """
        LLM identifies audience-vs-character knowledge gaps.

        Returns:
            Tuple of (has_irony, irony_description, irony_entities)
        """
        if not self.llm:
            return False, "", []

        try:
            system_prompt = "You are an expert at identifying dramatic irony in narratives."
            user_prompt = f"""Analyze this scene for dramatic irony - cases where the audience
knows something that characters don't.

SCENE ({state.act.value} act, tension {state.tension_score:.2f}):
{state.description[:400]}

NARRATIVE CONTEXT:
{self.narrative_plan.central_conflict if self.narrative_plan else 'Unknown conflict'}

Identify:
1. Whether dramatic irony exists in this scene
2. What the audience knows that characters don't
3. Which characters are unaware
4. Which entities are involved in the irony"""

            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=IronyDetection,
                model=DIRECTORIAL_MODEL,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=500
            )

            return result.has_irony, result.irony_description, result.irony_entities

        except Exception:
            return False, "", []

    # ========================================================================
    # Camera System (4 methods)
    # ========================================================================

    def _plan_camera_schedule(self) -> CameraPlan:
        """LLM structured call to plan POV rotation and framing per act."""
        entity_names = []
        if self.store:
            try:
                all_entities = self.store.list_entities() if hasattr(self.store, 'list_entities') else []
                entity_names = [e.entity_id for e in all_entities[:10]]
            except Exception:
                pass

        if not self.llm or not entity_names:
            return self._fallback_camera_plan(entity_names)

        system_prompt = "You are a cinematography and narrative perspective expert."
        user_prompt = f"""Plan the camera/POV schedule for this narrative.

NARRATIVE PLAN:
{self.narrative_plan.central_conflict if self.narrative_plan else 'Dramatic narrative'}
Acts: {[a.name for a in self.narrative_plan.acts] if self.narrative_plan else ['setup', 'rising', 'climax', 'falling', 'resolution']}

ENTITIES: {', '.join(entity_names[:8])}

Plan:
1. POV rotation: Which character's perspective for each act?
   - Protagonist POV for climax moments
   - Rotate for rising action to build multiple perspectives
   - Ensemble for resolution
2. Framing per act: wide/close/overhead/subjective/ensemble
3. Parallel storyline threads (A-plot, B-plot if applicable)

For each POV entry, provide:
- act: Which act this applies to
- pov_entity: Entity whose perspective we follow
- framing: Camera framing style
- rationale: Why this perspective for this act"""

        try:
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=CameraPlan,
                model=DIRECTORIAL_MODEL,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=1500
            )
            return result
        except Exception as e:
            print(f"    Camera planning failed: {e}")
            return self._fallback_camera_plan(entity_names)

    def _fallback_camera_plan(self, entity_names: List[str]) -> CameraPlan:
        """Generate fallback camera plan without LLM."""
        protagonist = entity_names[0] if entity_names else "protagonist"
        secondary = entity_names[1] if len(entity_names) > 1 else protagonist

        pov_rotation = [
            POVEntry(act="setup", pov_entity=protagonist, framing="wide",
                    rationale="Establish world through protagonist's eyes"),
            POVEntry(act="rising", pov_entity=secondary, framing="close",
                    rationale="Build tension through alternate perspective"),
            POVEntry(act="climax", pov_entity=protagonist, framing="subjective",
                    rationale="Immersive protagonist POV for peak tension"),
            POVEntry(act="falling", pov_entity=protagonist, framing="overhead",
                    rationale="Pull back to show consequences"),
            POVEntry(act="resolution", pov_entity=protagonist, framing="ensemble",
                    rationale="Show all characters in resolution"),
        ]

        threads = [
            StorylineThread(
                thread_id="main",
                thread_name="Main storyline",
                entities=[protagonist],
                acts_active=["setup", "rising", "climax", "falling", "resolution"]
            )
        ]

        return CameraPlan(
            pov_rotation=pov_rotation,
            framing_by_act={
                "setup": "wide",
                "rising": "close",
                "climax": "subjective",
                "falling": "overhead",
                "resolution": "ensemble"
            },
            storyline_threads=threads
        )

    def _select_pov_for_state(self, step: int, act: ActPhase) -> Tuple[str, Framing]:
        """
        Programmatic POV selection:
        - Main POV for climax
        - Rotate for rising action
        - Ensemble for resolution
        """
        if not self.camera_plan or not self.camera_plan.pov_rotation:
            return "", Framing.WIDE

        # Find matching POV entry for this act
        for entry in self.camera_plan.pov_rotation:
            try:
                if entry.act == act.value:
                    framing = Framing(entry.framing) if entry.framing in [f.value for f in Framing] else Framing.WIDE
                    return entry.pov_entity, framing
            except (ValueError, AttributeError):
                continue

        # Fallback: cycle through POV entries
        idx = step % len(self.camera_plan.pov_rotation)
        entry = self.camera_plan.pov_rotation[idx]
        return entry.pov_entity, Framing.WIDE

    def _generate_interleaved_state(
        self,
        current_state: DirectorialState,
        target_year: int,
        target_month: int,
        step: int,
        act: ActPhase,
        pov_entity: str,
        framing: Framing,
        tension_target: float
    ) -> DirectorialState:
        """
        Core generation method: LLM generates scene from specific POV
        with framing and tension target.

        Temperature: 0.7 + tension * 0.2 (more creative at high tension)
        """
        if not self.llm:
            return self._generate_placeholder_state(
                current_state, target_year, target_month, step, act,
                pov_entity, framing, tension_target
            )

        target_time_str = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][target_month-1]} {target_year}"

        # Find relevant narrative beat
        relevant_beat = ""
        if self.narrative_plan and self.narrative_plan.beats:
            beat_count = len(self.narrative_plan.beats)
            beat_idx = int(step / max(1, self.forward_steps) * beat_count)
            if beat_idx < beat_count:
                relevant_beat = self.narrative_plan.beats[beat_idx]

        # Build directorial prompt
        system_prompt = """You are a narrative director generating scenes for a dramatic temporal simulation.
Generate vivid, specific scenes that serve the dramatic arc and follow the specified POV and framing."""

        entity_names = [e.entity_id for e in current_state.entities[:10]] if current_state.entities else []

        user_prompt = f"""Generate the next scene in this narrative simulation.

CURRENT STATE ({current_state.to_year_month_str()}):
{current_state.description[:300]}

TARGET TIME: {target_time_str}
ACT: {act.value.upper()} (tension target: {tension_target:.2f})
POV: {pov_entity if pov_entity else 'omniscient'}
FRAMING: {framing.value}
{"NARRATIVE BEAT: " + relevant_beat if relevant_beat else ""}

ENTITIES PRESENT: {', '.join(entity_names[:8])}

CENTRAL CONFLICT: {self.narrative_plan.central_conflict if self.narrative_plan else 'The unfolding drama'}

INSTRUCTIONS:
1. Write from the specified POV character's perspective
2. Use the specified framing (wide=establishing, close=intimate, subjective=internal, overhead=panoramic, ensemble=multiple)
3. Match the tension level ({tension_target:.1f}/1.0)
4. Serve the {act.value} act's dramatic needs
5. Be SPECIFIC - mention characters, locations, actions by name
6. Include 3-5 concrete key events
7. Assess the actual tension after writing

Provide:
- description: 3-4 sentence scene description from the specified POV
- key_events: 3-5 specific events
- tension_assessment: Actual tension level 0.0-1.0
- irony_potential: Whether dramatic irony exists (brief description or "none")
- emotional_beat: The emotional core of this scene (1-2 words)"""

        temperature = 0.7 + tension_target * 0.2

        try:
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=DirectorialStateSchema,
                model=DIRECTORIAL_MODEL,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=1000
            )

            # Compute dramatic importance
            importance = self._compute_dramatic_importance(act, tension_target, relevant_beat)
            resolution = self._importance_to_resolution(importance)

            state = DirectorialState(
                year=target_year,
                month=target_month,
                description=result.description,
                entities=current_state.entities.copy() if current_state.entities else [],
                world_state={
                    "key_events": result.key_events,
                    "emotional_beat": result.emotional_beat,
                    "irony_potential": result.irony_potential,
                },
                plausibility_score=0.0,
                parent_state=current_state,
                resolution_level=resolution,
                act=act,
                act_position=step / max(1, self.forward_steps),
                tension_score=result.tension_assessment,
                tension_delta=result.tension_assessment - current_state.tension_score,
                narrative_beat=relevant_beat,
                pov_entity=pov_entity,
                framing=framing,
                dramatic_importance=importance,
            )

            return state

        except Exception as e:
            print(f"    Scene generation failed: {e}")
            return self._generate_placeholder_state(
                current_state, target_year, target_month, step, act,
                pov_entity, framing, tension_target
            )

    def _merge_parallel_storylines(
        self,
        a_plot_states: List[DirectorialState],
        b_plot_states: List[DirectorialState]
    ) -> List[DirectorialState]:
        """Programmatic interleave of A/B plot states."""
        if not b_plot_states:
            return a_plot_states

        merged = []
        a_idx, b_idx = 0, 0

        while a_idx < len(a_plot_states) or b_idx < len(b_plot_states):
            # Interleave: 2 A-plot states, then 1 B-plot state
            for _ in range(2):
                if a_idx < len(a_plot_states):
                    merged.append(a_plot_states[a_idx])
                    a_idx += 1

            if b_idx < len(b_plot_states):
                b_state = b_plot_states[b_idx]
                b_state.parallel_storyline = "B-plot"
                merged.append(b_state)
                b_idx += 1

        return merged

    # ========================================================================
    # Fidelity Mapping (2 methods)
    # ========================================================================

    def _compute_dramatic_importance(
        self,
        act: ActPhase,
        tension: float,
        beat: str
    ) -> float:
        """
        Compute dramatic importance based on act, tension, and narrative beat.

        Maps to resolution level:
        - climax/beat = TRAINED (importance > 0.8)
        - rising + high_tension = DIALOG (importance > 0.5)
        - general = SCENE (importance > 0.2)
        - bridging = TENSOR_ONLY (importance <= 0.2)
        """
        importance = 0.3  # Base

        # Act contribution
        act_importance = {
            ActPhase.SETUP: 0.3,
            ActPhase.RISING: 0.5,
            ActPhase.CLIMAX: 0.9,
            ActPhase.FALLING: 0.4,
            ActPhase.RESOLUTION: 0.3,
        }
        importance = act_importance.get(act, 0.3)

        # Tension boost
        if tension > 0.8:
            importance = max(importance, 0.7)

        # Beat boost
        if beat:
            importance += 0.15

        return min(1.0, importance)

    def _importance_to_resolution(self, importance: float) -> ResolutionLevel:
        """Maps 0.0-1.0 dramatic importance to ResolutionLevel enum."""
        if importance > 0.8:
            return ResolutionLevel.TRAINED
        elif importance > 0.5:
            return ResolutionLevel.DIALOG
        elif importance > 0.2:
            return ResolutionLevel.SCENE
        else:
            return ResolutionLevel.TENSOR_ONLY

    # ========================================================================
    # Path exploration and validation
    # ========================================================================

    def _generate_origin_state(self) -> DirectorialState:
        """Generate the opening scene with entity inference."""
        origin_year = getattr(self.config, 'origin_year', None) or datetime.now().year
        description = getattr(self.config, 'portal_description', None)
        if not description:
            description = "The narrative begins. Characters assemble and the stage is set."

        entities = self._infer_entities_from_description(description)

        return DirectorialState(
            year=origin_year,
            month=1,
            description=description,
            entities=entities,
            world_state={"phase": "origin", "key_events": ["Story begins"]},
            plausibility_score=1.0,
            act=ActPhase.SETUP,
            act_position=0.0,
            tension_score=self.tension_targets[0] if self.tension_targets else 0.2,
            pov_entity=entities[0].entity_id if entities else "",
            framing=Framing.WIDE,
            dramatic_importance=0.3,
        )

    def _infer_entities_from_description(self, description: str) -> List[Entity]:
        """Infer entities from description using LLM or regex fallback."""
        if not self.llm:
            import re
            potential_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', description)
            entities = []
            seen = set()
            for name in potential_names[:10]:
                entity_id = name.lower().replace(' ', '_')
                if entity_id not in seen and len(entity_id) > 2:
                    seen.add(entity_id)
                    entities.append(Entity(
                        entity_id=entity_id,
                        entity_type="person",
                        entity_metadata={"name": name, "source": "inferred"}
                    ))
            return entities

        try:
            class EntityInfo(BaseModel):
                name: str
                type: str
                role: str

            class EntityList(BaseModel):
                entities: List[EntityInfo]

            result = self.llm.generate_structured(
                prompt=f"Identify key entities in: {description[:500]}",
                response_model=EntityList,
                model=DIRECTORIAL_MODEL,
                system_prompt="Identify entities (people, places, things) in the description.",
                temperature=0.3,
                max_tokens=500
            )

            entities = []
            for info in result.entities[:10]:
                entity_id = info.name.lower().replace(' ', '_').replace("'", "")
                entities.append(Entity(
                    entity_id=entity_id,
                    entity_type=info.type,
                    entity_metadata={"name": info.name, "role": info.role}
                ))
            return entities
        except Exception as e:
            print(f"    Entity inference failed: {e}")
            return []

    def _explore_directed_paths(self, origin: DirectorialState) -> List[DirectorialPath]:
        """Forward generation with act-aware prompting."""
        all_paths = []

        # Calculate time stepping
        portal_year = getattr(self.config, 'portal_year', None)
        if portal_year is None:
            portal_year = origin.year + 3
        total_months = max(12, (portal_year - origin.year) * 12)
        month_step = max(1, total_months // self.forward_steps)

        for path_idx in range(self.path_count):
            print(f"  Generating path {path_idx + 1}/{self.path_count}...")

            states = [origin]
            current_state = origin

            for step in range(1, self.forward_steps):
                # Calculate target time
                current_month_total = current_state.to_total_months()
                target_month_total = current_month_total + month_step
                target_year = target_month_total // 12
                target_month = target_month_total % 12 or 12
                if target_month == 0:
                    target_year -= 1
                    target_month = 12

                # Determine act and camera for this step
                act = self._determine_act_for_step(step)
                pov_entity, framing = self._select_pov_for_state(step, act)

                # Get tension target
                tension_target = self.tension_targets[step] if step < len(self.tension_targets) else 0.5

                # Generate scene
                new_state = self._generate_interleaved_state(
                    current_state=current_state,
                    target_year=target_year,
                    target_month=target_month,
                    step=step,
                    act=act,
                    pov_entity=pov_entity,
                    framing=framing,
                    tension_target=tension_target
                )

                # Compute actual tension
                new_state.tension_score = self._compute_tension_for_state(new_state, step)

                # Detect dramatic irony
                has_irony, irony_desc, irony_ents = self._detect_dramatic_irony(new_state)
                new_state.dramatic_irony = has_irony
                new_state.irony_entities = irony_ents
                if has_irony:
                    new_state.world_state['dramatic_irony'] = irony_desc

                states.append(new_state)
                current_state = new_state

                if step % 5 == 0:
                    print(f"    Step {step}/{self.forward_steps}: {act.value} @ tension {new_state.tension_score:.2f}")

            # Build path
            path = DirectorialPath(
                path_id=f"directorial_path_{uuid.uuid4().hex[:8]}",
                states=states,
                coherence_score=0.0,
                tension_curve=[s.tension_score for s in states],
            )
            all_paths.append(path)

        return all_paths

    def _validate_narrative_coherence(self, paths: List[DirectorialPath]) -> List[DirectorialPath]:
        """LLM + programmatic validation: arc completion, tension fit, POV coherence."""
        validated = []

        for path in paths:
            # Programmatic checks
            arc_score = self._compute_arc_completion(path)
            tension_fit = self._compute_tension_fit(path)
            pov_coherence = self._compute_pov_coherence(path)

            # Composite validation score
            validation_score = arc_score * 0.4 + tension_fit * 0.3 + pov_coherence * 0.3

            path.arc_completion_score = arc_score
            path.coherence_score = validation_score

            # LLM validation for high-scoring paths
            if self.llm and validation_score > 0.3:
                try:
                    llm_validation = self._llm_validate_narrative(path)
                    # Blend programmatic and LLM scores
                    path.coherence_score = validation_score * 0.6 + (
                        (llm_validation.arc_score + llm_validation.tension_fit) / 2
                    ) * 0.4
                    path.validation_details['llm_notes'] = llm_validation.pov_notes
                    path.validation_details['llm_issues'] = llm_validation.issues
                except Exception:
                    pass

            path.validation_details['arc_completion'] = arc_score
            path.validation_details['tension_fit'] = tension_fit
            path.validation_details['pov_coherence'] = pov_coherence

            validated.append(path)

        return validated

    def _compute_arc_completion(self, path: DirectorialPath) -> float:
        """Check if all five acts are represented in the path."""
        acts_present = set()
        for state in path.states:
            acts_present.add(state.act)

        all_acts = set(ActPhase)
        return len(acts_present.intersection(all_acts)) / len(all_acts)

    def _compute_tension_fit(self, path: DirectorialPath) -> float:
        """Compare actual tension curve to target curve."""
        if not path.tension_curve or not self.tension_targets:
            return 0.5

        errors = []
        for i, actual in enumerate(path.tension_curve):
            if i < len(self.tension_targets):
                target = self.tension_targets[i]
                errors.append(abs(actual - target))

        if not errors:
            return 0.5

        avg_error = sum(errors) / len(errors)
        return max(0.0, 1.0 - avg_error * 2)  # Lower error = higher score

    def _compute_pov_coherence(self, path: DirectorialPath) -> float:
        """Check if POV assignments are coherent with the camera plan."""
        if not self.camera_plan or not self.camera_plan.pov_rotation:
            return 0.5

        matches = 0
        total = 0

        for state in path.states:
            if state.pov_entity:
                total += 1
                for entry in self.camera_plan.pov_rotation:
                    try:
                        if entry.act == state.act.value and entry.pov_entity == state.pov_entity:
                            matches += 1
                            break
                    except (ValueError, AttributeError):
                        continue

        return matches / max(1, total)

    def _llm_validate_narrative(self, path: DirectorialPath) -> NarrativeValidation:
        """LLM validation of narrative coherence."""
        # Build summary of path for validation
        state_summaries = []
        for i, state in enumerate(path.states):
            if i % 3 == 0 or i == len(path.states) - 1:  # Sample every 3rd state
                state_summaries.append(
                    f"Step {i} ({state.act.value}, tension {state.tension_score:.2f}): "
                    f"{state.description[:100]}..."
                )

        system_prompt = "You are a narrative critic evaluating story coherence."
        user_prompt = f"""Evaluate this narrative path for coherence.

NARRATIVE PLAN:
{self.narrative_plan.central_conflict if self.narrative_plan else 'Unknown'}

PATH SUMMARY ({len(path.states)} states):
{chr(10).join(state_summaries)}

TENSION CURVE: {[f'{t:.2f}' for t in path.tension_curve[:10]]}

Evaluate:
1. arc_score (0.0-1.0): Does the narrative complete a satisfying dramatic arc?
2. tension_fit (0.0-1.0): Does the tension curve follow the expected dramatic shape?
3. pov_notes: Brief notes on POV effectiveness
4. issues: List of any narrative problems"""

        result = self.llm.generate_structured(
            prompt=user_prompt,
            response_model=NarrativeValidation,
            model=DIRECTORIAL_MODEL,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500
        )
        return result

    def _rank_paths(self, paths: List[DirectorialPath]) -> List[DirectorialPath]:
        """Composite ranking: 0.4 coherence + 0.3 arc_completion + 0.3 tension_fit."""
        for path in paths:
            tension_fit = self._compute_tension_fit(path)
            path.coherence_score = (
                path.coherence_score * 0.4 +
                path.arc_completion_score * 0.3 +
                tension_fit * 0.3
            )

        return sorted(paths, key=lambda p: p.coherence_score, reverse=True)

    def _populate_path_metadata(self, path: DirectorialPath):
        """Populate act_boundaries, tension_curve, pov_distribution."""
        # Act boundaries
        boundaries = {}
        for i, state in enumerate(path.states):
            act_name = state.act.value
            if act_name not in boundaries:
                boundaries[act_name] = i
        path.act_boundaries = boundaries

        # Tension curve (already populated during generation)
        if not path.tension_curve:
            path.tension_curve = [s.tension_score for s in path.states]

        # POV distribution
        pov_counts: Dict[str, int] = {}
        for state in path.states:
            if state.pov_entity:
                pov_counts[state.pov_entity] = pov_counts.get(state.pov_entity, 0) + 1
        path.pov_distribution = pov_counts

        # Storyline threads
        if self.camera_plan and self.camera_plan.storyline_threads:
            path.storyline_threads = [t.thread_name for t in self.camera_plan.storyline_threads]

    # ========================================================================
    # Helpers
    # ========================================================================

    def _generate_placeholder_state(
        self,
        current_state: DirectorialState,
        target_year: int,
        target_month: int,
        step: int,
        act: ActPhase,
        pov_entity: str,
        framing: Framing,
        tension_target: float
    ) -> DirectorialState:
        """Generate placeholder state when LLM is unavailable."""
        importance = self._compute_dramatic_importance(act, tension_target, "")
        resolution = self._importance_to_resolution(importance)

        act_descriptions = {
            ActPhase.SETUP: "The scene is set as characters take their positions.",
            ActPhase.RISING: "Tensions mount and complications arise.",
            ActPhase.CLIMAX: "The critical moment arrives. Everything hangs in the balance.",
            ActPhase.FALLING: "The aftermath unfolds as consequences emerge.",
            ActPhase.RESOLUTION: "A new equilibrium forms as events settle.",
        }

        return DirectorialState(
            year=target_year,
            month=target_month,
            description=act_descriptions.get(act, "Events continue to develop."),
            entities=current_state.entities.copy() if current_state.entities else [],
            world_state={"key_events": [f"{act.value} event"]},
            plausibility_score=0.5,
            parent_state=current_state,
            resolution_level=resolution,
            act=act,
            act_position=step / max(1, self.forward_steps),
            tension_score=tension_target,
            narrative_beat="",
            pov_entity=pov_entity,
            framing=framing,
            dramatic_importance=importance,
        )
