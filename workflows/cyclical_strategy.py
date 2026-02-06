"""
Cyclical Strategy - Time loop and cyclical pattern temporal simulation

This module implements CYCLICAL mode temporal reasoning, where simulations exhibit
repeating patterns, escalating cycles, causal loops, and prophecy fulfillment.

The KEY INNOVATION is that the LLM decides what "cyclical" means for each scenario:
repeating, spiral, causal_loop, oscillating, or composite.

Example:
    Scenario: "Groundhog Day time loop"
    Cycle Type: repeating (same events with increasing awareness)
    Goal: Generate cycles with prophecy tracking and loop closure

Architecture:
    - Cycle Semantics: LLM interprets what "cyclical" means for the scenario
    - Prophecy System: Generates and tracks prophecy fulfillment across cycles
    - Causal Loop System: Detects and enforces causal loop closure
    - Escalation: Manages increasing stakes/variation per cycle type
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


# ============================================================================
# Pydantic Response Models
# ============================================================================

class CycleSemantics(BaseModel):
    """LLM-determined interpretation of what 'cyclical' means for this scenario"""
    cycle_type: str  # repeating, spiral, causal_loop, oscillating, composite
    variation_mode: str  # mutation, amplification, retroactive, inversion, mixed
    escalation_rule: str  # Description of how stakes change per cycle
    prophecy_mechanism: str  # deja_vu, oracle, pattern_recognition, fate, none
    loop_structure: str  # Description of the causal loop structure (if applicable)
    key_recurring_elements: List[str]  # Elements that repeat each cycle
    variation_seeds: List[str]  # Seeds for variation between cycles


class CyclicalStateSchema(BaseModel):
    """Schema for LLM-generated cyclical state"""
    description: str
    key_events: List[str]
    recurring_elements_present: List[str]
    escalation_assessment: str


class CyclicalValidation(BaseModel):
    """LLM validation of cyclical coherence"""
    cycle_coherence: float
    pattern_similarity: float
    prophecy_assessment: str
    issues: List[str]


class ProphecySchema(BaseModel):
    """A prophecy generated at cycle boundaries"""
    prophecy_text: str
    prophecy_type: str  # warning, promise, riddle, vision
    target_cycle: int  # Which cycle this should be fulfilled in
    fulfillment_condition: str


class ProphecyFulfillment(BaseModel):
    """LLM assessment of prophecy fulfillment"""
    fulfilled: bool
    confidence: float
    evidence: str


class CausalLoopOpportunity(BaseModel):
    """LLM detection of causal loop opportunity"""
    is_opportunity: bool
    loop_tag: str
    loop_description: str
    connects_to_cycle: int


class CausalLoopEnforcement(BaseModel):
    """LLM rewrite to close a causal loop"""
    rewritten_description: str
    loop_closure_explanation: str
    key_events: List[str]


# ============================================================================
# Dataclasses
# ============================================================================

@dataclass
class CyclicalState:
    """A state in the cyclical simulation with cycle and prophecy tracking"""
    year: int
    month: int
    description: str
    entities: List[Entity]
    world_state: Dict[str, Any]
    plausibility_score: float = 0.0
    parent_state: Optional['CyclicalState'] = None
    children_states: List['CyclicalState'] = field(default_factory=list)
    resolution_level: ResolutionLevel = None

    # Cycle tracking
    cycle_index: int = 0
    position_in_cycle: int = 0
    cycle_type: str = ""  # LLM-determined

    # Pattern tracking
    pattern_signature: str = ""
    variation_from_archetype: float = 0.0
    escalation_level: float = 0.0

    # Prophecy/echo
    prophecy: str = ""
    prophecy_source_cycle: int = -1
    fulfilled_prophecies: List[str] = field(default_factory=list)
    echo_of: str = ""  # Reference to archetype state this echoes

    # Causal loops
    causal_loop_tag: str = ""
    loop_contribution: str = ""

    def __post_init__(self):
        if self.children_states is None:
            self.children_states = []
        if not (1 <= self.month <= 12):
            self.month = 1
        if self.resolution_level is None:
            self.resolution_level = ResolutionLevel.SCENE
        if self.fulfilled_prophecies is None:
            self.fulfilled_prophecies = []

    def to_year_month_str(self) -> str:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{month_names[self.month-1]} {self.year}"

    def to_total_months(self) -> int:
        return self.year * 12 + self.month


@dataclass
class CyclicalPath:
    """Complete cyclical path through multiple cycles"""
    path_id: str
    states: List[CyclicalState]
    coherence_score: float
    cycle_semantics: str = ""  # The cycle_type chosen
    cycle_type: str = ""
    cycle_count: int = 0
    cycle_boundaries: List[int] = field(default_factory=list)
    prophecy_fulfillment_rate: float = 0.0
    escalation_trajectory: List[float] = field(default_factory=list)
    causal_loops_closed: int = 0
    explanation: str = ""
    validation_details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.cycle_boundaries is None:
            self.cycle_boundaries = []
        if self.escalation_trajectory is None:
            self.escalation_trajectory = []
        if self.validation_details is None:
            self.validation_details = {}


# ============================================================================
# CyclicalStrategy
# ============================================================================

class CyclicalStrategy:
    """
    Cyclical temporal simulation strategy with prophecy and loop tracking.

    Process:
    1. Interpret cycle semantics (LLM decides what "cyclical" means)
    2. Generate origin state
    3. Generate archetype cycle (the template cycle)
    4. Generate subsequent cycles with escalation + variation
    5. Resolve prophecies across cycles
    6. Resolve causal loops
    7. Validate cyclical coherence
    8. Rank paths and populate metadata
    """

    def __init__(self, config: TemporalConfig, llm_client, store):
        if config.mode != TemporalMode.CYCLICAL:
            raise ValueError(f"CyclicalStrategy requires mode=CYCLICAL, got {config.mode}")

        self.config = config
        self.llm = llm_client
        self.store = store
        self.paths: List[CyclicalPath] = []
        self.all_paths: List[CyclicalPath] = []

        # Cyclical parameters
        self.cycle_length = getattr(config, 'cycle_length', 4) or 4
        self.loop_count = getattr(config, 'backward_steps', 12) // max(1, self.cycle_length)
        if self.loop_count < 2:
            self.loop_count = 3
        self.path_count = getattr(config, 'path_count', 3)
        self.prophecy_accuracy = getattr(config, 'prophecy_accuracy', 0.5)

        # State populated during run
        self.cycle_semantics: Optional[CycleSemantics] = None
        self.archetype_states: List[CyclicalState] = []
        self.prophecies: List[Dict[str, Any]] = []
        self.open_loops: List[Dict[str, Any]] = []

    def run(self) -> List[CyclicalPath]:
        """Execute cyclical temporal simulation."""
        print(f"\n{'='*80}")
        print(f"CYCLICAL MODE: Time Loop Simulation")
        print(f"Cycle length: {self.cycle_length}")
        print(f"Target cycles: {self.loop_count}")
        print(f"Target paths: {self.path_count}")
        print(f"{'='*80}\n")

        # Step 1: Interpret cycle semantics
        print("Step 1: Interpreting cycle semantics...")
        self.cycle_semantics = self._interpret_cycle_semantics()
        print(f"  Cycle type: {self.cycle_semantics.cycle_type}")
        print(f"  Variation mode: {self.cycle_semantics.variation_mode}")
        print(f"  Prophecy mechanism: {self.cycle_semantics.prophecy_mechanism}")

        # Step 2: Generate origin state
        print("\nStep 2: Generating origin state...")
        origin = self._generate_origin_state()
        print(f"  Origin: {origin.to_year_month_str()}")

        # Step 3: Generate archetype cycle
        print("\nStep 3: Generating archetype cycle (template)...")
        self.archetype_states = self._generate_archetype_cycle(origin)
        print(f"  Archetype cycle: {len(self.archetype_states)} states")

        # Step 4: Generate cycled paths
        print(f"\nStep 4: Generating {self.path_count} cycled paths ({self.loop_count} cycles each)...")
        candidate_paths = self._generate_cycled_paths(origin)
        print(f"  Generated {len(candidate_paths)} candidate paths")

        # Step 5: Resolve prophecies
        print("\nStep 5: Resolving prophecies...")
        for path in candidate_paths:
            self._resolve_prophecies(path)
        fulfilled_total = sum(p.prophecy_fulfillment_rate for p in candidate_paths)
        print(f"  Average fulfillment rate: {fulfilled_total / max(1, len(candidate_paths)):.2f}")

        # Step 6: Resolve causal loops
        print("\nStep 6: Resolving causal loops...")
        for path in candidate_paths:
            self._resolve_causal_loops(path)
        loops_total = sum(p.causal_loops_closed for p in candidate_paths)
        print(f"  Total loops closed: {loops_total}")

        # Step 7: Validate cyclical coherence
        print("\nStep 7: Validating cyclical coherence...")
        validated_paths = self._validate_cyclical_coherence(candidate_paths)
        print(f"  {len(validated_paths)} paths validated")

        # Step 8: Rank and populate metadata
        print("\nStep 8: Ranking paths and populating metadata...")
        ranked_paths = self._rank_paths(validated_paths)
        for path in ranked_paths:
            self._populate_path_metadata(path)

        self.all_paths = ranked_paths
        self.paths = ranked_paths[:self.path_count]

        print(f"\n{'='*80}")
        print(f"CYCLICAL SIMULATION COMPLETE")
        print(f"Total paths: {len(self.all_paths)}")
        if self.all_paths:
            print(f"Best coherence: {self.all_paths[0].coherence_score:.3f}")
            print(f"Best prophecy rate: {self.all_paths[0].prophecy_fulfillment_rate:.2f}")
        print(f"{'='*80}\n")

        return self.all_paths

    # ========================================================================
    # Cycle Semantics
    # ========================================================================

    def _interpret_cycle_semantics(self) -> CycleSemantics:
        """
        THE KEY INNOVATION: LLM decides what 'cyclical' means for this scenario.

        Cycle types:
        - repeating: Same events, minor random changes (mutation)
        - spiral: Same structure, escalating stakes (amplification)
        - causal_loop: Cycle N causes conditions of cycle M (retroactive)
        - oscillating: Alternating between two poles (inversion)
        - composite: LLM-directed combination (mixed)
        """
        description = getattr(self.config, 'portal_description', None) or \
                     getattr(self.config, 'scenario_description', 'A cyclical narrative')

        if not self.llm:
            return self._fallback_cycle_semantics()

        system_prompt = "You are an expert at temporal narrative patterns and cyclical storytelling."
        user_prompt = f"""Interpret what "cyclical" means for this scenario.

SCENARIO:
{description[:500]}

CYCLE LENGTH: {self.cycle_length} states per cycle
TOTAL CYCLES: {self.loop_count}

Determine:
1. cycle_type: What kind of cycle fits this scenario?
   - "repeating": Same events replay with minor changes (e.g., Groundhog Day)
   - "spiral": Same structure but escalating stakes (e.g., generational saga)
   - "causal_loop": Later cycles cause earlier ones (e.g., bootstrap paradox)
   - "oscillating": Alternating between two poles (e.g., boom/bust)
   - "composite": Combination of above

2. variation_mode: How do cycles differ?
   - "mutation": Small random changes accumulate
   - "amplification": Same pattern at higher intensity
   - "retroactive": Later knowledge affects earlier events
   - "inversion": Each cycle inverts the previous
   - "mixed": Multiple variation modes

3. escalation_rule: How do stakes change per cycle?
4. prophecy_mechanism: How are prophecies delivered?
   - "deja_vu": Characters feel they've lived this before
   - "oracle": An oracle figure delivers predictions
   - "pattern_recognition": Characters notice the pattern
   - "fate": Prophecies emerge from narrative destiny
   - "none": No prophecy system

5. loop_structure: If causal_loop, describe the loop
6. key_recurring_elements: What repeats each cycle (3-5 elements)
7. variation_seeds: What changes between cycles (3-5 seeds)"""

        try:
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=CycleSemantics,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=1000
            )
            return result
        except Exception as e:
            print(f"    Cycle semantics interpretation failed: {e}")
            return self._fallback_cycle_semantics()

    def _fallback_cycle_semantics(self) -> CycleSemantics:
        """Fallback cycle semantics without LLM."""
        return CycleSemantics(
            cycle_type="spiral",
            variation_mode="amplification",
            escalation_rule="Each cycle increases stakes by introducing new complications",
            prophecy_mechanism="pattern_recognition",
            loop_structure="Linear cycles with forward escalation",
            key_recurring_elements=["central conflict", "key decision point", "confrontation", "aftermath"],
            variation_seeds=["new character involvement", "higher stakes", "deeper understanding"]
        )

    # ========================================================================
    # State Generation
    # ========================================================================

    def _generate_origin_state(self) -> CyclicalState:
        """Generate the first state of the first cycle."""
        origin_year = getattr(self.config, 'origin_year', None) or datetime.now().year
        description = getattr(self.config, 'portal_description', None)
        if not description:
            description = "The cycle begins. Events set into motion that will echo through time."

        entities = self._infer_entities_from_description(description)

        return CyclicalState(
            year=origin_year,
            month=1,
            description=description,
            entities=entities,
            world_state={"phase": "cycle_start", "key_events": ["Cycle begins"]},
            plausibility_score=1.0,
            cycle_index=0,
            position_in_cycle=0,
            cycle_type=self.cycle_semantics.cycle_type if self.cycle_semantics else "spiral",
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

    def _generate_archetype_cycle(self, origin: CyclicalState) -> List[CyclicalState]:
        """Generate the first cycle as a template that subsequent cycles will vary from."""
        states = [origin]
        current_state = origin

        # Calculate time stepping within a cycle
        total_months_per_cycle = max(self.cycle_length, 4)  # At least 4 months per cycle
        month_step = max(1, total_months_per_cycle)

        for pos in range(1, self.cycle_length):
            target_month_total = current_state.to_total_months() + month_step
            target_year = target_month_total // 12
            target_month = target_month_total % 12 or 12

            state = self._generate_cycle_state(
                current_state=current_state,
                target_year=target_year,
                target_month=target_month,
                cycle_index=0,
                position=pos,
                escalation=0.0,
                archetype_state=None  # No archetype for first cycle
            )

            states.append(state)
            current_state = state

        return states

    def _generate_cycle_state(
        self,
        current_state: CyclicalState,
        target_year: int,
        target_month: int,
        cycle_index: int,
        position: int,
        escalation: float,
        archetype_state: Optional[CyclicalState] = None
    ) -> CyclicalState:
        """Generate a single state within a cycle, optionally varying from archetype."""
        if not self.llm:
            return self._generate_placeholder_cycle_state(
                current_state, target_year, target_month, cycle_index, position, escalation
            )

        target_time_str = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][target_month-1]} {target_year}"

        # Build context for variation
        archetype_context = ""
        if archetype_state:
            archetype_context = f"""
ARCHETYPE (Cycle 0, Position {position}):
{archetype_state.description[:200]}
Recurring elements: {archetype_state.world_state.get('recurring_elements', [])}

VARIATION INSTRUCTION ({self.cycle_semantics.variation_mode}):
{self._get_variation_instruction(cycle_index, escalation)}"""

        entity_names = [e.entity_id for e in current_state.entities[:10]] if current_state.entities else []

        system_prompt = "You are an expert at cyclical narrative patterns and temporal loops."
        user_prompt = f"""Generate the next state in a cyclical narrative.

CYCLE TYPE: {self.cycle_semantics.cycle_type if self.cycle_semantics else 'spiral'}
CYCLE: {cycle_index + 1}/{self.loop_count}, Position {position + 1}/{self.cycle_length}
ESCALATION LEVEL: {escalation:.2f}

CURRENT STATE ({current_state.to_year_month_str()}):
{current_state.description[:300]}

TARGET TIME: {target_time_str}
ENTITIES: {', '.join(entity_names[:8])}

RECURRING ELEMENTS: {self.cycle_semantics.key_recurring_elements if self.cycle_semantics else []}
{archetype_context}

INSTRUCTIONS:
1. Generate a scene for position {position + 1} of cycle {cycle_index + 1}
2. Include recurring elements from the cycle pattern
3. Apply the variation mode ({self.cycle_semantics.variation_mode if self.cycle_semantics else 'amplification'})
4. Reflect the escalation level ({escalation:.1f}/1.0)
5. Be SPECIFIC with characters, events, and details

Provide:
- description: 2-3 sentence scene description
- key_events: 3-4 specific events
- recurring_elements_present: Which recurring elements appear in this state
- escalation_assessment: Brief assessment of how stakes have changed"""

        try:
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=CyclicalStateSchema,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=800
            )

            # Determine resolution based on cycle position
            resolution = self._cycle_position_to_resolution(position, cycle_index)

            state = CyclicalState(
                year=target_year,
                month=target_month,
                description=result.description,
                entities=current_state.entities.copy() if current_state.entities else [],
                world_state={
                    "key_events": result.key_events,
                    "recurring_elements": result.recurring_elements_present,
                    "escalation_assessment": result.escalation_assessment,
                },
                plausibility_score=0.0,
                parent_state=current_state,
                resolution_level=resolution,
                cycle_index=cycle_index,
                position_in_cycle=position,
                cycle_type=self.cycle_semantics.cycle_type if self.cycle_semantics else "spiral",
                escalation_level=escalation,
                echo_of=archetype_state.description[:50] if archetype_state else "",
            )

            # Compute variation from archetype
            if archetype_state:
                state.variation_from_archetype = self._compute_variation(
                    state.description, archetype_state.description
                )

            return state

        except Exception as e:
            print(f"    Cycle state generation failed: {e}")
            return self._generate_placeholder_cycle_state(
                current_state, target_year, target_month, cycle_index, position, escalation
            )

    def _get_variation_instruction(self, cycle_index: int, escalation: float) -> str:
        """Get variation instruction based on cycle semantics."""
        if not self.cycle_semantics:
            return "Apply slight variations."

        mode = self.cycle_semantics.variation_mode
        instructions = {
            "mutation": f"Apply small random changes to the archetype. Cycle {cycle_index + 1} accumulates {cycle_index} mutations.",
            "amplification": f"Same pattern but at escalation level {escalation:.1f}. Stakes are {1 + escalation:.1f}x higher.",
            "retroactive": f"Events from later cycles cast new light on this moment. Knowledge from cycle {cycle_index} affects interpretation.",
            "inversion": f"{'Invert' if cycle_index % 2 == 1 else 'Maintain'} the pattern from the archetype. Opposites apply.",
            "mixed": f"Combine mutation and amplification. Escalation: {escalation:.1f}, mutations: {cycle_index}.",
        }
        return instructions.get(mode, "Apply appropriate variations.")

    def _cycle_position_to_resolution(self, position: int, cycle_index: int) -> ResolutionLevel:
        """Map cycle position to resolution level. Boundaries get higher fidelity."""
        if position == 0 or position == self.cycle_length - 1:
            return ResolutionLevel.DIALOG  # Cycle start/end
        elif position == self.cycle_length // 2:
            return ResolutionLevel.SCENE  # Mid-cycle
        else:
            return ResolutionLevel.SCENE

    def _compute_variation(self, description_a: str, description_b: str) -> float:
        """Simple programmatic measure of how much two descriptions differ."""
        if not description_a or not description_b:
            return 1.0

        words_a = set(description_a.lower().split())
        words_b = set(description_b.lower().split())

        if not words_a or not words_b:
            return 1.0

        intersection = words_a & words_b
        union = words_a | words_b

        jaccard = len(intersection) / len(union) if union else 0
        return 1.0 - jaccard  # Higher = more variation

    # ========================================================================
    # Path Generation
    # ========================================================================

    def _generate_cycled_paths(self, origin: CyclicalState) -> List[CyclicalPath]:
        """Generate multiple paths, each with multiple cycles."""
        all_paths = []

        for path_idx in range(self.path_count):
            print(f"  Generating path {path_idx + 1}/{self.path_count}...")

            all_states = list(self.archetype_states)  # Start with archetype cycle
            current_state = all_states[-1]  # End of archetype

            for cycle_idx in range(1, self.loop_count):
                escalation = cycle_idx / max(1, self.loop_count - 1)

                # Generate prophecy at cycle boundary
                if self.cycle_semantics and self.cycle_semantics.prophecy_mechanism != "none":
                    prophecy = self._generate_prophecy(current_state, cycle_idx)
                    if prophecy:
                        self.prophecies.append({
                            "text": prophecy.prophecy_text,
                            "type": prophecy.prophecy_type,
                            "source_cycle": cycle_idx - 1,
                            "target_cycle": prophecy.target_cycle,
                            "condition": prophecy.fulfillment_condition,
                            "fulfilled": False,
                            "path_idx": path_idx,
                        })
                        current_state.prophecy = prophecy.prophecy_text
                        current_state.prophecy_source_cycle = cycle_idx - 1

                # Generate states for this cycle
                cycle_states = []
                for pos in range(self.cycle_length):
                    # Get archetype state for this position
                    archetype = self.archetype_states[pos] if pos < len(self.archetype_states) else None

                    target_month_total = current_state.to_total_months() + max(1, self.cycle_length)
                    target_year = target_month_total // 12
                    target_month = target_month_total % 12 or 12

                    state = self._generate_cycle_state(
                        current_state=current_state,
                        target_year=target_year,
                        target_month=target_month,
                        cycle_index=cycle_idx,
                        position=pos,
                        escalation=escalation,
                        archetype_state=archetype
                    )

                    # Check for causal loop opportunities
                    if self.cycle_semantics and self.cycle_semantics.cycle_type == "causal_loop":
                        opportunity = self._detect_causal_loop_opportunity(state, cycle_idx)
                        if opportunity:
                            state = self._enforce_causal_loop(state, opportunity)

                    # Check prophecy fulfillment
                    for prophecy_record in self.prophecies:
                        if (prophecy_record['path_idx'] == path_idx and
                            not prophecy_record['fulfilled'] and
                            prophecy_record['target_cycle'] <= cycle_idx):
                            fulfilled = self._check_prophecy_fulfillment(state, prophecy_record)
                            if fulfilled:
                                prophecy_record['fulfilled'] = True
                                state.fulfilled_prophecies.append(prophecy_record['text'])

                    cycle_states.append(state)
                    current_state = state

                all_states.extend(cycle_states)

                if cycle_idx % 2 == 0:
                    print(f"    Cycle {cycle_idx + 1}/{self.loop_count}: escalation {escalation:.2f}")

            # Build path
            path = CyclicalPath(
                path_id=f"cyclical_path_{uuid.uuid4().hex[:8]}",
                states=all_states,
                coherence_score=0.0,
                cycle_semantics=self.cycle_semantics.cycle_type if self.cycle_semantics else "spiral",
                cycle_type=self.cycle_semantics.cycle_type if self.cycle_semantics else "spiral",
                cycle_count=self.loop_count,
            )
            all_paths.append(path)

        return all_paths

    # ========================================================================
    # Prophecy System (3 methods)
    # ========================================================================

    def _generate_prophecy(self, state: CyclicalState, cycle_idx: int) -> Optional[ProphecySchema]:
        """Generate a prophecy at cycle boundaries, style per prophecy_mechanism."""
        if not self.llm:
            return ProphecySchema(
                prophecy_text=f"A pattern echoes: what happened in cycle {cycle_idx} will recur with greater force.",
                prophecy_type="vision",
                target_cycle=min(cycle_idx + 1, self.loop_count - 1),
                fulfillment_condition="The same key events occur at higher intensity"
            )

        mechanism = self.cycle_semantics.prophecy_mechanism if self.cycle_semantics else "pattern_recognition"

        mechanism_prompts = {
            "deja_vu": "Characters experience an overwhelming sense of having lived this moment before.",
            "oracle": "An oracle figure delivers a cryptic prediction about what the next cycle holds.",
            "pattern_recognition": "Someone notices the repeating pattern and predicts what comes next.",
            "fate": "The narrative suggests an inevitable destiny that will manifest in the next cycle.",
        }

        system_prompt = "You are an expert at generating dramatic prophecies and foreshadowing."
        user_prompt = f"""Generate a prophecy at the boundary between cycle {cycle_idx} and cycle {cycle_idx + 1}.

CURRENT STATE (end of cycle {cycle_idx}):
{state.description[:300]}

PROPHECY MECHANISM: {mechanism}
{mechanism_prompts.get(mechanism, 'Generate a thematically appropriate prophecy.')}

RECURRING ELEMENTS: {self.cycle_semantics.key_recurring_elements if self.cycle_semantics else []}

Generate:
- prophecy_text: The prophecy itself (1-2 sentences, evocative)
- prophecy_type: warning, promise, riddle, or vision
- target_cycle: Which cycle this should be fulfilled in ({cycle_idx + 1} or later)
- fulfillment_condition: What would constitute fulfillment"""

        try:
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=ProphecySchema,
                system_prompt=system_prompt,
                temperature=0.6,
                max_tokens=400
            )
            return result
        except Exception:
            return None

    def _check_prophecy_fulfillment(self, state: CyclicalState, prophecy_record: Dict) -> bool:
        """LLM rates confidence of prophecy fulfillment."""
        if not self.llm:
            # Simple heuristic: check if fulfillment condition keywords appear in description
            condition_words = set(prophecy_record['condition'].lower().split())
            desc_words = set(state.description.lower().split())
            overlap = len(condition_words & desc_words) / max(1, len(condition_words))
            return overlap > self.prophecy_accuracy

        system_prompt = "You are judging whether a prophecy has been fulfilled."
        user_prompt = f"""Has this prophecy been fulfilled by the current state?

PROPHECY: {prophecy_record['text']}
FULFILLMENT CONDITION: {prophecy_record['condition']}

CURRENT STATE (Cycle {state.cycle_index}, Position {state.position_in_cycle}):
{state.description[:300]}
Key events: {state.world_state.get('key_events', [])}

Rate:
- fulfilled: true/false
- confidence: 0.0-1.0
- evidence: Brief explanation"""

        try:
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=ProphecyFulfillment,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=300
            )
            return result.fulfilled and result.confidence >= self.prophecy_accuracy
        except Exception:
            return False

    def _resolve_prophecies(self, path: CyclicalPath):
        """Walk path states, compute prophecy fulfillment rates."""
        path_prophecies = [p for p in self.prophecies if p.get('path_idx', -1) == self.all_paths.index(path) if path in self.all_paths]

        # If path not yet in all_paths, use all prophecies
        if not path_prophecies:
            path_prophecies = self.prophecies

        if not path_prophecies:
            path.prophecy_fulfillment_rate = 0.0
            return

        fulfilled_count = sum(1 for p in path_prophecies if p.get('fulfilled', False))
        path.prophecy_fulfillment_rate = fulfilled_count / len(path_prophecies)

    # ========================================================================
    # Causal Loop System (3 methods)
    # ========================================================================

    def _detect_causal_loop_opportunity(
        self, state: CyclicalState, cycle_idx: int
    ) -> Optional[Dict[str, Any]]:
        """LLM detects if state could close a causal loop."""
        if not self.llm or not self.open_loops:
            return None

        # Check open loops for potential closure
        for loop in self.open_loops:
            if loop.get('closed', False):
                continue

            system_prompt = "You are an expert at causal loop detection in temporal narratives."
            user_prompt = f"""Can this state close the causal loop?

OPEN LOOP:
Tag: {loop['tag']}
Description: {loop['description']}
Source cycle: {loop['source_cycle']}

CURRENT STATE (Cycle {cycle_idx}):
{state.description[:300]}

Determine:
- is_opportunity: Can this state close the loop?
- loop_tag: The tag of the loop being closed
- loop_description: How it closes
- connects_to_cycle: Which earlier cycle this connects to"""

            try:
                result = self.llm.generate_structured(
                    prompt=user_prompt,
                    response_model=CausalLoopOpportunity,
                    system_prompt=system_prompt,
                    temperature=0.3,
                    max_tokens=400
                )
                if result.is_opportunity:
                    return {
                        "tag": result.loop_tag,
                        "description": result.loop_description,
                        "connects_to": result.connects_to_cycle,
                        "original_loop": loop,
                    }
            except Exception:
                continue

        return None

    def _enforce_causal_loop(
        self, state: CyclicalState, opportunity: Dict[str, Any]
    ) -> CyclicalState:
        """LLM rewrites state to explicitly close the causal loop."""
        if not self.llm:
            state.causal_loop_tag = opportunity.get('tag', 'loop')
            state.loop_contribution = opportunity.get('description', 'Loop closed')
            return state

        system_prompt = "You are rewriting a scene to explicitly close a causal loop."
        user_prompt = f"""Rewrite this state to explicitly close the causal loop.

CURRENT STATE:
{state.description[:300]}

LOOP TO CLOSE:
Tag: {opportunity['tag']}
Description: {opportunity['description']}
Connects to cycle: {opportunity['connects_to']}

Rewrite the description so that:
1. The causal loop is explicitly closed
2. The connection to the earlier cycle is clear
3. The rewrite maintains narrative coherence

Provide:
- rewritten_description: The new scene description
- loop_closure_explanation: How the loop is closed
- key_events: Updated key events reflecting the loop closure"""

        try:
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=CausalLoopEnforcement,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=600
            )

            state.description = result.rewritten_description
            state.causal_loop_tag = opportunity.get('tag', 'loop')
            state.loop_contribution = result.loop_closure_explanation
            state.world_state['key_events'] = result.key_events
            state.world_state['loop_closed'] = True

            # Mark the loop as closed
            if 'original_loop' in opportunity:
                opportunity['original_loop']['closed'] = True

        except Exception:
            state.causal_loop_tag = opportunity.get('tag', 'loop')
            state.loop_contribution = 'Loop closure attempted'

        return state

    def _resolve_causal_loops(self, path: CyclicalPath):
        """Verify all open loops are closed."""
        closed = 0
        for state in path.states:
            if state.causal_loop_tag and state.loop_contribution:
                closed += 1
        path.causal_loops_closed = closed

    # ========================================================================
    # Validation and Ranking
    # ========================================================================

    def _validate_cyclical_coherence(self, paths: List[CyclicalPath]) -> List[CyclicalPath]:
        """Hybrid validation: cycle_length respected, cycles exhibit chosen type, prophecy rate."""
        validated = []

        for path in paths:
            # Programmatic checks
            cycle_length_score = self._check_cycle_length_consistency(path)
            pattern_score = self._check_pattern_consistency(path)
            prophecy_score = path.prophecy_fulfillment_rate

            # Composite score
            composite = cycle_length_score * 0.3 + pattern_score * 0.4 + prophecy_score * 0.3
            path.coherence_score = composite

            # LLM validation for promising paths
            if self.llm and composite > 0.2:
                try:
                    llm_result = self._llm_validate_cyclical(path)
                    path.coherence_score = composite * 0.6 + (
                        (llm_result.cycle_coherence + llm_result.pattern_similarity) / 2
                    ) * 0.4
                    path.validation_details['llm_issues'] = llm_result.issues
                    path.validation_details['prophecy_assessment'] = llm_result.prophecy_assessment
                except Exception:
                    pass

            path.validation_details['cycle_length_score'] = cycle_length_score
            path.validation_details['pattern_score'] = pattern_score
            path.validation_details['prophecy_score'] = prophecy_score

            validated.append(path)

        return validated

    def _check_cycle_length_consistency(self, path: CyclicalPath) -> float:
        """Check that cycles have consistent length."""
        if not path.states:
            return 0.0

        # Group states by cycle_index
        cycles: Dict[int, List[CyclicalState]] = {}
        for state in path.states:
            cycles.setdefault(state.cycle_index, []).append(state)

        if len(cycles) < 2:
            return 0.5

        lengths = [len(states) for states in cycles.values()]
        avg_length = sum(lengths) / len(lengths)

        if avg_length == 0:
            return 0.0

        # Score based on how consistent lengths are
        deviations = [abs(l - self.cycle_length) / self.cycle_length for l in lengths]
        avg_deviation = sum(deviations) / len(deviations)

        return max(0.0, 1.0 - avg_deviation)

    def _check_pattern_consistency(self, path: CyclicalPath) -> float:
        """Check that cycles exhibit the chosen pattern type."""
        if not path.states or len(path.states) < self.cycle_length * 2:
            return 0.5

        # Compare recurring elements between cycles
        cycles: Dict[int, List[str]] = {}
        for state in path.states:
            elements = state.world_state.get('recurring_elements', [])
            cycles.setdefault(state.cycle_index, []).extend(elements)

        if len(cycles) < 2:
            return 0.5

        # Check overlap between cycles
        cycle_keys = sorted(cycles.keys())
        overlaps = []
        for i in range(1, len(cycle_keys)):
            prev_elements = set(cycles[cycle_keys[i-1]])
            curr_elements = set(cycles[cycle_keys[i]])
            if prev_elements and curr_elements:
                overlap = len(prev_elements & curr_elements) / max(1, len(prev_elements | curr_elements))
                overlaps.append(overlap)

        if not overlaps:
            return 0.5

        return sum(overlaps) / len(overlaps)

    def _llm_validate_cyclical(self, path: CyclicalPath) -> CyclicalValidation:
        """LLM validation of cyclical coherence."""
        state_summaries = []
        for i, state in enumerate(path.states):
            if i % max(1, self.cycle_length) == 0:  # Sample at cycle boundaries
                state_summaries.append(
                    f"Cycle {state.cycle_index}, Pos {state.position_in_cycle}: "
                    f"{state.description[:80]}..."
                )

        system_prompt = "You are evaluating the coherence of a cyclical narrative."
        user_prompt = f"""Evaluate this cyclical narrative path.

CYCLE TYPE: {path.cycle_type}
TOTAL CYCLES: {path.cycle_count}
TOTAL STATES: {len(path.states)}

SAMPLED STATES:
{chr(10).join(state_summaries[:15])}

PROPHECY FULFILLMENT RATE: {path.prophecy_fulfillment_rate:.2f}
CAUSAL LOOPS CLOSED: {path.causal_loops_closed}

Evaluate:
1. cycle_coherence (0.0-1.0): Do cycles follow the chosen pattern type?
2. pattern_similarity (0.0-1.0): Do recurring elements actually recur?
3. prophecy_assessment: Brief assessment of prophecy system
4. issues: List of any problems"""

        result = self.llm.generate_structured(
            prompt=user_prompt,
            response_model=CyclicalValidation,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500
        )
        return result

    def _rank_paths(self, paths: List[CyclicalPath]) -> List[CyclicalPath]:
        """Rank by composite score."""
        return sorted(paths, key=lambda p: p.coherence_score, reverse=True)

    def _populate_path_metadata(self, path: CyclicalPath):
        """Populate cycle boundaries, escalation trajectory, prophecy rate."""
        # Cycle boundaries
        boundaries = []
        for i, state in enumerate(path.states):
            if state.position_in_cycle == 0 and i > 0:
                boundaries.append(i)
        path.cycle_boundaries = boundaries

        # Escalation trajectory
        escalation = []
        current_cycle = -1
        for state in path.states:
            if state.cycle_index != current_cycle:
                escalation.append(state.escalation_level)
                current_cycle = state.cycle_index
        path.escalation_trajectory = escalation

    # ========================================================================
    # Helpers
    # ========================================================================

    def _generate_placeholder_cycle_state(
        self,
        current_state: CyclicalState,
        target_year: int,
        target_month: int,
        cycle_index: int,
        position: int,
        escalation: float
    ) -> CyclicalState:
        """Generate placeholder state when LLM is unavailable."""
        position_descriptions = {
            0: "The cycle begins anew. Familiar patterns reassert themselves.",
            1: "Events build momentum as the cycle progresses.",
            2: "The cycle reaches its midpoint. Stakes crystallize.",
            3: "The cycle nears completion. Resolution approaches.",
        }
        desc = position_descriptions.get(
            position % 4,
            f"Cycle {cycle_index + 1}, position {position + 1}: Events continue in the pattern."
        )

        resolution = self._cycle_position_to_resolution(position, cycle_index)

        return CyclicalState(
            year=target_year,
            month=target_month,
            description=desc,
            entities=current_state.entities.copy() if current_state.entities else [],
            world_state={"key_events": [f"Cycle {cycle_index + 1} event"], "recurring_elements": []},
            plausibility_score=0.5,
            parent_state=current_state,
            resolution_level=resolution,
            cycle_index=cycle_index,
            position_in_cycle=position,
            cycle_type=self.cycle_semantics.cycle_type if self.cycle_semantics else "spiral",
            escalation_level=escalation,
        )
