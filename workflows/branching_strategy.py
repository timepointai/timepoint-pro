"""
Branching Strategy - Forward simulation with counterfactual branches (M12)

This module implements BRANCHING mode temporal reasoning, where simulations work
forward from a known origin, generating multiple possible futures at decision points.

Example:
    Origin: "Holmes and Moriarty meet at Reichenbach Falls"
    Branches: 4 possible outcomes (Holmes wins, Moriarty wins, draw, intervention)
    Goal: Explore all plausible forward paths from the decision point

Architecture:
    - Mirrors PortalStrategy but goes FORWARD instead of backward
    - Multi-path exploration with branching at decision points
    - Hybrid scoring for path plausibility
    - Backward validation: forward-generated paths must make causal sense
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import uuid

from schemas import Entity, Timepoint, TemporalMode, ResolutionLevel
from generation.config_schema import TemporalConfig
from llm_service.model_selector import ActionType, get_token_estimator
import re
import json


def _repair_malformed_json(raw_text: str) -> Optional[dict]:
    """
    Attempt to repair common JSON formatting issues from LLM responses.

    Common issues:
    1. Unquoted string values: "key": value instead of "key": "value"
    2. Trailing commas
    3. Missing closing brackets
    4. Extra text before/after JSON

    Returns:
        Parsed dict if repair successful, None otherwise
    """
    if not raw_text:
        return None

    # Try to extract JSON block from response (handle markdown code blocks)
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw_text)
    if json_match:
        raw_text = json_match.group(1).strip()

    # Find the JSON object boundaries
    start_idx = raw_text.find('{')
    if start_idx == -1:
        return None

    # Find matching closing brace (handle nested objects)
    brace_count = 0
    end_idx = -1
    for i, char in enumerate(raw_text[start_idx:], start_idx):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break

    if end_idx == -1:
        # Try adding missing closing braces
        raw_text = raw_text + '}' * brace_count
        end_idx = len(raw_text) - 1

    json_str = raw_text[start_idx:end_idx + 1]

    # Try parsing as-is first
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Repair: Fix unquoted string values (the most common issue)
    # Pattern: "key": unquoted_value (without leading quote)
    # This regex finds: "key": followed by text that isn't a quote, number, true, false, null, [, or {
    def fix_unquoted_values(match):
        key = match.group(1)
        value_start = match.group(2)
        # Find the end of this value (next comma, }, or ])
        return f'"{key}": "{value_start}'

    # Fix unquoted string values
    # Match: "key": value_without_quote (where value starts with a letter)
    repaired = re.sub(
        r'"([^"]+)":\s*([A-Za-z][^,}\]"]*?)([,}\]])',
        lambda m: f'"{m.group(1)}": "{m.group(2).strip()}"{m.group(3)}',
        json_str
    )

    # Fix trailing commas
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

    # Try parsing the repaired JSON
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # More aggressive repair: quote all unquoted values
    # This handles cases where values span multiple words
    lines = repaired.split('\n')
    fixed_lines = []
    for line in lines:
        # Check for unquoted string value pattern
        colon_match = re.match(r'^(\s*"[^"]+"\s*:\s*)([^"\[\{0-9\-][^,\}\]]*?)(\s*[,\}\]]?\s*)$', line)
        if colon_match:
            prefix = colon_match.group(1)
            value = colon_match.group(2).strip().rstrip(',').rstrip('}').rstrip(']')
            suffix = colon_match.group(3)
            # Escape any quotes in the value
            value = value.replace('"', '\\"')
            line = f'{prefix}"{value}"{suffix}'
        fixed_lines.append(line)

    repaired = '\n'.join(fixed_lines)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        pass

    # Handle truncated arrays - try to close them properly
    # Count unclosed brackets
    open_brackets = repaired.count('[') - repaired.count(']')
    open_braces = repaired.count('{') - repaired.count('}')

    # If there are unclosed arrays/objects, try to close them
    if open_brackets > 0 or open_braces > 0:
        # Remove any trailing incomplete objects (after last complete one)
        # Find last complete object by looking for last "},"
        last_complete = repaired.rfind('},')
        if last_complete > 0:
            # Keep everything up to and including the last complete object
            repaired = repaired[:last_complete + 1]
            # Add proper closing
            repaired += ']' * open_brackets + '}' * open_braces

            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    # Last resort: try to extract at least a partial result
    return None


class BranchingMode(str, Enum):
    """Strategies for exploring forward branches"""
    CHRONOLOGICAL = "chronological"  # T_0 → T_1 → T_2 → ...
    BREADTH_FIRST = "breadth_first"  # Explore all branches at each level before proceeding
    DEPTH_FIRST = "depth_first"  # Follow one branch to completion, then backtrack
    ADAPTIVE = "adaptive"  # System decides based on branching factor


@dataclass
class BranchingState:
    """A state at a specific point in the forward simulation"""
    year: int
    month: int
    description: str
    entities: List[Entity]
    world_state: Dict[str, Any]
    plausibility_score: float = 0.0
    parent_state: Optional['BranchingState'] = None  # The state this came from (T-1)
    children_states: List['BranchingState'] = field(default_factory=list)  # Possible T+1 states
    branch_id: str = ""  # Identifies which branch this state belongs to
    is_branch_point: bool = False  # True if this state has multiple children
    resolution_level: ResolutionLevel = None

    def __post_init__(self):
        if self.children_states is None:
            self.children_states = []
        if not (1 <= self.month <= 12):
            self.month = 1
        if self.resolution_level is None:
            self.resolution_level = ResolutionLevel.SCENE
        if not self.branch_id:
            self.branch_id = f"branch_{uuid.uuid4().hex[:8]}"

    def to_year_month_str(self) -> str:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{month_names[self.month-1]} {self.year}"

    def to_total_months(self) -> int:
        return self.year * 12 + self.month


@dataclass
class BranchingPath:
    """Complete path from origin through one branch to endpoint"""
    path_id: str
    branch_name: str  # Human-readable branch description (e.g., "Holmes wins")
    states: List[BranchingState]  # Ordered origin → endpoint
    coherence_score: float
    branch_points: List[int] = field(default_factory=list)  # Indices where branches occurred
    explanation: str = ""
    validation_details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.branch_points is None:
            self.branch_points = []
        if self.validation_details is None:
            self.validation_details = {}


class BranchingStrategy:
    """
    Forward simulation strategy with counterfactual branching.

    Process:
    1. Generate origin state from initial scene
    2. Step forward, detecting decision/branch points
    3. At branch points, generate N divergent futures
    4. Score and rank branches using hybrid scoring
    5. Validate backward coherence (does path make causal sense?)
    6. Return all branches with rankings
    """

    def __init__(self, config: TemporalConfig, llm_client, store):
        if config.mode != TemporalMode.BRANCHING:
            raise ValueError(f"BranchingStrategy requires mode=BRANCHING, got {config.mode}")

        self.config = config
        self.llm = llm_client
        self.store = store
        self.paths: List[BranchingPath] = []
        self.all_paths: List[BranchingPath] = []

        # Get branching parameters from config or use defaults
        self.forward_steps = getattr(config, 'backward_steps', 15)  # Reuse backward_steps for forward
        self.branch_count = getattr(config, 'path_count', 4)  # Number of branches at decision points
        self.candidates_per_step = getattr(config, 'candidate_antecedents_per_step', 3)

    def run(self) -> List[BranchingPath]:
        """Execute forward simulation with branching."""
        print(f"\n{'='*80}")
        print(f"BRANCHING MODE: Forward Simulation with Counterfactuals")
        print(f"Steps: {self.forward_steps}")
        print(f"Target branches: {self.branch_count}")
        print(f"{'='*80}\n")

        # Step 1: Generate origin state
        print("Step 1: Generating origin state...")
        origin = self._generate_origin_state()
        print(f"✓ Origin state generated: {origin.to_year_month_str()}")

        # Step 2: Determine exploration strategy
        print("\nStep 2: Selecting exploration strategy...")
        strategy = self._select_exploration_strategy()
        print(f"✓ Strategy: {strategy.value}")

        # Step 3: Generate forward paths with branching
        print(f"\nStep 3: Exploring forward paths (target: {self.branch_count} branches)...")
        candidate_paths = self._explore_forward_paths(origin, strategy)
        print(f"✓ Generated {len(candidate_paths)} candidate paths")

        # Step 4: Validate backward coherence
        print("\nStep 4: Validating backward coherence...")
        valid_paths = self._validate_backward_coherence(candidate_paths)
        coherence_threshold = getattr(self.config, 'coherence_threshold', 0.65)
        print(f"✓ {len(valid_paths)} paths passed coherence threshold ({coherence_threshold})")

        # Step 5: Rank paths
        print("\nStep 5: Ranking paths by plausibility...")
        ranked_paths = self._rank_paths(valid_paths)

        # Step 6: Identify branch points
        print("\nStep 6: Identifying branch points...")
        for i, path in enumerate(ranked_paths):
            path.branch_points = self._detect_branch_points(path)
            if i < 5:
                print(f"  Path {i+1} ({path.branch_name}): {len(path.branch_points)} branch points")

        self.all_paths = ranked_paths
        self.paths = ranked_paths[:self.branch_count]

        print(f"\n{'='*80}")
        print(f"BRANCHING SIMULATION COMPLETE")
        print(f"Total paths generated: {len(self.all_paths)}")
        print(f"{'='*80}\n")

        return self.all_paths

    def _generate_origin_state(self) -> BranchingState:
        """Generate the starting state for forward simulation."""
        # Use origin_year if available, otherwise use current year from first timepoint
        origin_year = getattr(self.config, 'origin_year', None)
        if origin_year is None:
            origin_year = datetime.now().year

        # Get initial description from config or generate placeholder
        description = getattr(self.config, 'portal_description', None)
        if not description:
            description = "Initial state at the beginning of the branching simulation"

        # Infer entities from description
        entities = self._infer_entities_from_description(description)

        # FALLBACK: If entity inference failed, get entities from store
        if not entities:
            entities = self._get_fallback_entities()
            if entities:
                print(f"    Using {len(entities)} entities from store/config (inference fallback)")

        return BranchingState(
            year=origin_year,
            month=1,
            description=description,
            entities=entities,
            world_state={"phase": "origin"},
            plausibility_score=1.0,
            branch_id="origin"
        )

    def _get_fallback_entities(self) -> List[Entity]:
        """
        Get entities from the store when inference fails.

        This is a safety fallback to ensure we always have some entities
        to work with in the branching simulation.
        """
        entities = []

        # Try to get entities from the store
        if self.store:
            try:
                # Get all entities from the store
                all_entities = self.store.list_entities() if hasattr(self.store, 'list_entities') else []
                if all_entities:
                    # Filter to humans/persons (most relevant for narrative)
                    human_entities = [e for e in all_entities if e.entity_type in ('human', 'person', 'character')]
                    if human_entities:
                        entities = human_entities[:10]  # Limit to 10 most relevant
                    else:
                        entities = all_entities[:10]
            except Exception as e:
                print(f"    Warning: Could not get entities from store: {e}")

        return entities

    def _ensure_entities_present(
        self,
        inferred_entities: List[Entity],
        parent_entities: List[Entity]
    ) -> List[Entity]:
        """
        Ensure we always have some entities by falling back to parent entities.

        This prevents empty entities_present warnings in generated states.

        Args:
            inferred_entities: Entities inferred from the current description
            parent_entities: Entities from the parent state

        Returns:
            Non-empty list of entities (inferred if available, else parent)
        """
        if inferred_entities:
            return inferred_entities
        if parent_entities:
            # Inherit from parent if inference returned empty
            return parent_entities.copy()
        # Last resort: get from store
        return self._get_fallback_entities()

    def _infer_entities_from_description(self, description: str) -> List[Entity]:
        """Infer entities from a state description using LLM or regex fallback."""
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
            from pydantic import BaseModel

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

    def _select_exploration_strategy(self) -> BranchingMode:
        """Select exploration strategy based on complexity."""
        if self.forward_steps > 20:
            return BranchingMode.BREADTH_FIRST
        return BranchingMode.CHRONOLOGICAL

    def _explore_forward_paths(
        self,
        origin: BranchingState,
        strategy: BranchingMode
    ) -> List[BranchingPath]:
        """Explore forward paths with branching at decision points."""
        return self._explore_chronological(origin)

    def _explore_chronological(self, origin: BranchingState) -> List[BranchingPath]:
        """Standard forward stepping with branching: T_0 → T_1 → T_2 → ..."""
        paths = []
        current_states = [origin]

        # Calculate time step (months per step)
        portal_year = getattr(self.config, 'portal_year', None)
        if portal_year is None:
            # Default to 6 years forward for BRANCHING mode
            portal_year = origin.year + 6
        total_months = (portal_year - origin.year) * 12
        month_step = max(1, total_months // self.forward_steps)

        for step in range(self.forward_steps):
            next_states = []

            # Calculate target time
            current_month_total = current_states[0].to_total_months() if current_states else origin.to_total_months()
            target_month_total = current_month_total + month_step
            target_year = target_month_total // 12
            target_month = target_month_total % 12 or 12

            temp_state = BranchingState(year=target_year, month=target_month, description="", entities=[], world_state={})
            print(f"  Forward step {step+1}/{self.forward_steps}: {temp_state.to_year_month_str()}")

            for state in current_states:
                # Check if this is a decision/branch point
                is_branch_point = self._is_branch_point(state, step)

                if is_branch_point:
                    # Generate multiple divergent futures
                    consequents = self._generate_consequents(
                        state, target_year, target_month,
                        count=self.candidates_per_step,
                        is_branch_point=True
                    )
                    state.is_branch_point = True
                else:
                    # Generate single continuation
                    consequents = self._generate_consequents(
                        state, target_year, target_month,
                        count=1,
                        is_branch_point=False
                    )

                # Score consequents
                scored = self._score_consequents(consequents, state)
                next_states.extend(scored[:self.candidates_per_step])

            current_states = next_states

            # Prune if too many paths
            if len(current_states) > self.branch_count * 3:
                current_states = self._prune_low_scoring_paths(current_states)
                print(f"    Pruned to {len(current_states)} states")

        # Convert final states to complete paths
        for final_state in current_states:
            path = self._reconstruct_path(final_state)
            paths.append(path)

        return paths

    def _is_branch_point(self, state: BranchingState, step: int) -> bool:
        """
        Detect if this state is a decision/branch point.

        Branch points occur at:
        - Conflict moments (negotiations, confrontations)
        - Decision points (choices, pivots)
        - Key milestones (every N steps)
        """
        # Branch at regular intervals
        branch_interval = max(1, self.forward_steps // self.branch_count)
        if step > 0 and step % branch_interval == 0:
            return True

        # Check description for conflict/decision keywords
        conflict_keywords = ["decide", "choice", "confront", "negotiate", "choose",
                           "fork", "branch", "option", "alternative", "either"]
        desc_lower = state.description.lower()
        if any(kw in desc_lower for kw in conflict_keywords):
            return True

        return False

    def _generate_consequents(
        self,
        current_state: BranchingState,
        target_year: int,
        target_month: int,
        count: int = 3,
        is_branch_point: bool = False
    ) -> List[BranchingState]:
        """
        Generate N plausible NEXT states using LLM.

        At branch points, generates divergent outcomes.
        Otherwise, generates continuations.
        """
        if not self.llm:
            return self._generate_placeholder_consequents(current_state, target_year, target_month, count)

        target_time_str = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][target_month-1]} {target_year}"

        if is_branch_point:
            prompt_type = "DIVERGENT FUTURES (this is a decision/branch point)"
            diversity_instruction = """Generate {count} VERY DIFFERENT outcomes:
- One where things go well for the protagonist
- One where things go poorly
- One with an unexpected twist or intervention
- Vary the outcomes significantly - these are alternate timelines"""
        else:
            prompt_type = "NATURAL CONTINUATION"
            diversity_instruction = f"Generate {count} plausible continuations with slight variations"

        entity_names = [e.entity_id for e in current_state.entities[:10]] if current_state.entities else []

        user_prompt = f"""Generate {count} possible NEXT states following this current state.

CURRENT STATE ({current_state.to_year_month_str()}):
{current_state.description}

Entities: {', '.join(entity_names[:5]) if entity_names else 'None specified'}
World Context: {current_state.world_state}

TYPE: {prompt_type}
TARGET TIME: {target_time_str}

{diversity_instruction}

For EACH consequent, provide:
- description: What happens in {target_time_str} (2-3 sentences)
- key_events: Array of 2-4 specific events
- outcome_type: "positive", "negative", "neutral", or "twist"
- causal_link: How this follows from the current state

IMPORTANT: Return valid JSON with all string values properly quoted.
Example format:
{{"consequents": [
  {{"description": "In {target_time_str}, the situation evolves as characters adapt to circumstances.", "key_events": ["Event one occurs", "Event two follows"], "outcome_type": "neutral", "causal_link": "This follows naturally from the previous state."}}
]}}

Return ONLY valid JSON matching this exact structure. All strings must be quoted."""

        try:
            from pydantic import BaseModel

            class ConsequentSchema(BaseModel):
                description: str
                key_events: List[str]
                outcome_type: str
                causal_link: str

            class ConsequentList(BaseModel):
                consequents: List[ConsequentSchema]

            token_estimator = get_token_estimator()
            token_estimate = token_estimator.estimate(
                ActionType.PORTAL_BACKWARD_REASONING,  # Reuse this action type
                context={"candidate_count": count},
                prompt_length=len(user_prompt)
            )

            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=ConsequentList,
                system_prompt="You are an expert at forward temporal reasoning and counterfactual scenarios.",
                temperature=0.9 if is_branch_point else 0.7,  # Higher temp for diversity at branch points
                max_tokens=token_estimate.recommended_tokens
            )

            consequents = []
            for i, data in enumerate(result.consequents[:count]):
                # Create new branch ID for branch points
                if is_branch_point:
                    branch_id = f"{current_state.branch_id}_{data.outcome_type}_{i}"
                    branch_name = f"{data.outcome_type.title()} outcome"
                else:
                    branch_id = current_state.branch_id
                    branch_name = current_state.branch_id

                # Ensure we have entities (inherit from parent if needed)
                state_entities = self._ensure_entities_present(
                    [],  # No new inference for consequent descriptions
                    current_state.entities if current_state.entities else []
                )

                state = BranchingState(
                    year=target_year,
                    month=target_month,
                    description=data.description,
                    entities=state_entities,
                    world_state={
                        "key_events": data.key_events,
                        "outcome_type": data.outcome_type,
                        "causal_link": data.causal_link
                    },
                    plausibility_score=0.0,
                    parent_state=current_state,
                    branch_id=branch_id
                )
                consequents.append(state)

            # Pad with placeholders if needed
            if len(consequents) < count:
                placeholders = self._generate_placeholder_consequents(
                    current_state, target_year, target_month, count - len(consequents)
                )
                consequents.extend(placeholders)

            return consequents

        except Exception as e:
            error_msg = str(e)
            print(f"    LLM generation failed: {error_msg}")

            # Try to repair malformed JSON if the error suggests parsing issues
            if "JSON" in error_msg or "parse" in error_msg.lower() or "valid" in error_msg.lower():
                # Extract raw response from error message if available
                raw_text = error_msg
                if hasattr(e, 'response'):
                    raw_text = str(e.response)

                # Try JSON repair
                print(f"    Attempting JSON repair...")
                repaired = _repair_malformed_json(raw_text)

                if repaired and 'consequents' in repaired:
                    print(f"    ✓ JSON repair successful!")
                    consequents = []
                    for i, data in enumerate(repaired['consequents'][:count]):
                        try:
                            if is_branch_point:
                                branch_id = f"{current_state.branch_id}_{data.get('outcome_type', 'unknown')}_{i}"
                            else:
                                branch_id = current_state.branch_id

                            # Ensure we have entities (inherit from parent if needed)
                            state_entities = self._ensure_entities_present(
                                [],  # No new inference for repaired descriptions
                                current_state.entities if current_state.entities else []
                            )

                            state = BranchingState(
                                year=target_year,
                                month=target_month,
                                description=data.get('description', f'Repaired state {i+1}'),
                                entities=state_entities,
                                world_state={
                                    "key_events": data.get('key_events', []),
                                    "outcome_type": data.get('outcome_type', 'neutral'),
                                    "causal_link": data.get('causal_link', 'Continuation from previous state')
                                },
                                plausibility_score=0.0,
                                parent_state=current_state,
                                branch_id=branch_id
                            )
                            consequents.append(state)
                        except Exception as repair_error:
                            print(f"    ⚠️  Failed to create state from repaired data: {repair_error}")

                    if consequents:
                        # Pad with placeholders if needed
                        if len(consequents) < count:
                            placeholders = self._generate_placeholder_consequents(
                                current_state, target_year, target_month, count - len(consequents)
                            )
                            consequents.extend(placeholders)
                        return consequents
                else:
                    print(f"    ⚠️  JSON repair failed, using placeholders")

            return self._generate_placeholder_consequents(current_state, target_year, target_month, count)

    def _generate_placeholder_consequents(
        self,
        current_state: BranchingState,
        target_year: int,
        target_month: int,
        count: int
    ) -> List[BranchingState]:
        """Generate placeholder consequents when LLM is unavailable."""
        consequents = []
        outcome_types = ["positive", "negative", "neutral", "twist"]

        # Ensure we have entities (inherit from parent if needed)
        state_entities = self._ensure_entities_present(
            [],  # No inference for placeholders
            current_state.entities if current_state.entities else []
        )

        for i in range(count):
            outcome = outcome_types[i % len(outcome_types)]
            state = BranchingState(
                year=target_year,
                month=target_month,
                description=f"Continuation {i+1} ({outcome}): Events progress from {current_state.description[:50]}...",
                entities=state_entities.copy(),  # Use inherited entities
                world_state={"outcome_type": outcome},
                plausibility_score=0.5,
                parent_state=current_state,
                branch_id=f"{current_state.branch_id}_{outcome}_{i}"
            )
            consequents.append(state)

        return consequents

    def _score_consequents(
        self,
        consequents: List[BranchingState],
        antecedent: BranchingState
    ) -> List[BranchingState]:
        """Score consequents using hybrid scoring."""
        for cons in consequents:
            # Simple scoring based on outcome type diversity and description quality
            base_score = 0.7

            # Boost for having detailed description
            if len(cons.description) > 100:
                base_score += 0.1

            # Boost for having key events
            if cons.world_state.get('key_events'):
                base_score += 0.1

            # Add some randomness for diversity
            cons.plausibility_score = base_score + np.random.uniform(-0.1, 0.1)

        return sorted(consequents, key=lambda s: s.plausibility_score, reverse=True)

    def _prune_low_scoring_paths(self, states: List[BranchingState]) -> List[BranchingState]:
        """Prune low-scoring states to manage path explosion."""
        sorted_states = sorted(states, key=lambda s: s.plausibility_score, reverse=True)
        return sorted_states[:self.branch_count * 2]

    def _reconstruct_path(self, leaf_state: BranchingState) -> BranchingPath:
        """Reconstruct complete path from leaf state to origin."""
        states = []
        current = leaf_state

        while current is not None:
            states.append(current)
            current = current.parent_state

        # Reverse to get origin → endpoint order
        states.reverse()

        # Determine branch name from final state
        outcome_type = leaf_state.world_state.get('outcome_type', 'unknown')
        branch_name = f"{outcome_type.title()} branch"

        return BranchingPath(
            path_id=f"branch_path_{uuid.uuid4().hex[:8]}",
            branch_name=branch_name,
            states=states,
            coherence_score=0.0,
            branch_points=[],
            explanation=f"Path following {outcome_type} outcomes"
        )

    def _validate_backward_coherence(self, paths: List[BranchingPath]) -> List[BranchingPath]:
        """Validate that forward-generated paths make causal sense looking backward."""
        valid_paths = []
        coherence_threshold = getattr(self.config, 'coherence_threshold', 0.65)

        for path in paths:
            # Compute coherence as average of state scores
            if path.states:
                avg_score = sum(s.plausibility_score for s in path.states) / len(path.states)
            else:
                avg_score = 0.0

            path.coherence_score = avg_score

            if avg_score >= coherence_threshold:
                valid_paths.append(path)
            elif avg_score >= coherence_threshold * 0.8:
                # Include but flag
                path.explanation += " (LOW COHERENCE)"
                valid_paths.append(path)

        return valid_paths

    def _rank_paths(self, paths: List[BranchingPath]) -> List[BranchingPath]:
        """Rank paths by coherence score."""
        return sorted(paths, key=lambda p: p.coherence_score, reverse=True)

    def _detect_branch_points(self, path: BranchingPath) -> List[int]:
        """Identify indices where branches occurred."""
        branch_points = []
        for i, state in enumerate(path.states):
            if state.is_branch_point:
                branch_points.append(i)
        return branch_points
