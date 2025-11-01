"""
Portal Strategy - Backward simulation from fixed endpoint to origin

This module implements PORTAL mode temporal reasoning, where simulations work
backward from a known endpoint (portal) to a known starting point (origin),
discovering plausible paths that connect them.

Example:
    Portal: "John Doe elected President in 2040"
    Origin: "John Doe is VP of Engineering in 2025"
    Goal: Find the most plausible paths from 2025→2040

Architecture:
    - Dual-layer design: PortalStrategy (workflow) + PORTAL TemporalMode (causality rules)
    - Adaptive exploration: system chooses strategy based on complexity
    - Hybrid scoring: LLM + historical + causal + capability + context
    - Forward validation: backward-generated paths must make forward sense
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np
import uuid

from schemas import Entity, Timepoint, TemporalMode, ResolutionLevel
from generation.config_schema import TemporalConfig


class ExplorationMode(str, Enum):
    """Strategies for exploring backward paths"""
    REVERSE_CHRONOLOGICAL = "reverse_chronological"  # 100→99→98→...→1
    OSCILLATING = "oscillating"  # 100→1→99→2→98→3→...
    RANDOM = "random"  # Random step order
    ADAPTIVE = "adaptive"  # System decides based on complexity


class FailureResolution(str, Enum):
    """Strategies for handling incoherent paths"""
    PRUNE = "prune"  # Kill invalid path immediately
    BACKTRACK = "backtrack"  # Go back N steps, try different antecedent
    MARK = "mark"  # Flag but continue with path
    RELAX_PORTAL = "relax_portal"  # Modify endpoint slightly


@dataclass
class PortalState:
    """A state at a specific point in the backward simulation"""
    year: int
    description: str
    entities: List[Entity]
    world_state: Dict[str, Any]
    plausibility_score: float = 0.0
    parent_state: Optional['PortalState'] = None  # The state this came from (T+1)
    children_states: List['PortalState'] = field(default_factory=list)  # Possible T-1 states

    def __post_init__(self):
        """Ensure children_states is a list"""
        if self.children_states is None:
            self.children_states = []


@dataclass
class PortalPath:
    """Complete path from origin to portal"""
    path_id: str
    states: List[PortalState]  # Ordered origin→portal
    coherence_score: float
    pivot_points: List[int] = field(default_factory=list)  # Indices of critical decision states
    explanation: str = ""
    validation_details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure collections are initialized"""
        if self.pivot_points is None:
            self.pivot_points = []
        if self.validation_details is None:
            self.validation_details = {}


class PortalStrategy:
    """
    Backward simulation strategy for portal-anchored scenarios.

    Process:
    1. Generate portal state from description
    2. Step backward, generating N candidate antecedents per step
    3. Score and rank antecedents using hybrid scoring
    4. Adaptively choose exploration strategy based on complexity
    5. Validate complete paths (origin→portal forward coherence)
    6. Return top K ranked paths with explanations

    Attributes:
        config: TemporalConfig with portal mode settings
        llm: LLM client for state generation and scoring
        store: GraphStore for data persistence
        paths: List of discovered portal paths
    """

    def __init__(self, config: TemporalConfig, llm_client, store):
        """
        Initialize portal strategy.

        Args:
            config: TemporalConfig with mode=PORTAL
            llm_client: LLM client for generation and scoring
            store: GraphStore for persistence
        """
        if config.mode != TemporalMode.PORTAL:
            raise ValueError(f"PortalStrategy requires mode=PORTAL, got {config.mode}")

        self.config = config
        self.llm = llm_client
        self.store = store
        self.paths: List[PortalPath] = []

        # Validate configuration
        if not config.portal_description:
            raise ValueError("portal_description is required for PORTAL mode")
        if not config.portal_year or not config.origin_year:
            raise ValueError("portal_year and origin_year are required for PORTAL mode")

    def run(self) -> List[PortalPath]:
        """
        Execute portal-anchored backward simulation.

        Returns:
            List of PortalPath objects, ranked by coherence score
        """
        print(f"\n{'='*80}")
        print(f"PORTAL MODE: Backward Simulation")
        print(f"Portal: {self.config.portal_description} ({self.config.portal_year})")
        print(f"Origin: {self.config.origin_year}")
        print(f"Steps: {self.config.backward_steps}")
        print(f"{'='*80}\n")

        # Step 1: Generate portal state
        print("Step 1: Generating portal endpoint state...")
        portal = self._generate_portal_state()
        print(f"✓ Portal state generated: {portal.year}")

        # Step 2: Determine exploration strategy adaptively
        print("\nStep 2: Selecting exploration strategy...")
        strategy = self._select_exploration_strategy()
        print(f"✓ Strategy: {strategy.value}")

        # Step 3: Generate backward paths
        print(f"\nStep 3: Exploring backward paths (generating {self.config.path_count} paths)...")
        candidate_paths = self._explore_backward_paths(portal, strategy)
        print(f"✓ Generated {len(candidate_paths)} candidate paths")

        # Step 4: Validate forward coherence
        print("\nStep 4: Validating forward coherence...")
        valid_paths = self._validate_forward_coherence(candidate_paths)
        print(f"✓ {len(valid_paths)} paths passed coherence threshold ({self.config.coherence_threshold})")

        # Step 5: Rank by hybrid scoring
        print("\nStep 5: Ranking paths by plausibility...")
        ranked_paths = self._rank_paths(valid_paths)

        # Step 6: Detect pivot points
        print("\nStep 6: Detecting pivot points...")
        for i, path in enumerate(ranked_paths[:self.config.path_count]):
            path.pivot_points = self._detect_pivot_points(path)
            print(f"  Path {i+1}: {len(path.pivot_points)} pivot points detected")

        self.paths = ranked_paths[:self.config.path_count]

        print(f"\n{'='*80}")
        print(f"PORTAL SIMULATION COMPLETE")
        print(f"Top {len(self.paths)} paths returned")
        print(f"{'='*80}\n")

        return self.paths

    def _generate_portal_state(self) -> PortalState:
        """Generate the endpoint state from description"""
        # TODO: Use LLM to populate full state from description
        # For now, create a placeholder state
        return PortalState(
            year=self.config.portal_year,
            description=self.config.portal_description,
            entities=[],  # Will be populated by LLM
            world_state={"placeholder": True},
            plausibility_score=1.0  # Portal is given, score is 1.0
        )

    def _select_exploration_strategy(self) -> ExplorationMode:
        """Adaptively choose exploration strategy based on complexity"""
        if self.config.exploration_mode == "adaptive":
            if self.config.backward_steps > self.config.oscillation_complexity_threshold:
                return ExplorationMode.OSCILLATING
            else:
                return ExplorationMode.REVERSE_CHRONOLOGICAL
        return ExplorationMode(self.config.exploration_mode)

    def _explore_backward_paths(
        self,
        portal: PortalState,
        strategy: ExplorationMode
    ) -> List[PortalPath]:
        """Explore multiple backward paths using selected strategy"""
        if strategy == ExplorationMode.REVERSE_CHRONOLOGICAL:
            return self._explore_reverse_chronological(portal)
        elif strategy == ExplorationMode.OSCILLATING:
            return self._explore_oscillating(portal)
        elif strategy == ExplorationMode.RANDOM:
            return self._explore_random_sampling(portal)
        else:
            raise ValueError(f"Unknown exploration mode: {strategy}")

    def _explore_reverse_chronological(self, portal: PortalState) -> List[PortalPath]:
        """Standard backward stepping: T_n → T_n-1 → ... → T_0"""
        paths = []
        current_states = [portal]

        year_step = (self.config.portal_year - self.config.origin_year) // self.config.backward_steps

        for step in range(self.config.backward_steps):
            next_states = []
            step_year = self.config.portal_year - (step + 1) * year_step

            print(f"  Backward step {step+1}/{self.config.backward_steps}: Year {step_year}")

            for state in current_states:
                # Generate N candidate antecedents for this state
                antecedents = self._generate_antecedents(state, target_year=step_year)

                # Score and filter
                scored = self._score_antecedents(antecedents, state)
                top_antecedents = scored[:self.config.candidate_antecedents_per_step]

                next_states.extend(top_antecedents)

            current_states = next_states

            # Prune if too many paths
            if len(current_states) > self.config.path_count * 3:
                current_states = self._prune_low_scoring_paths(current_states)
                print(f"    Pruned to {len(current_states)} states")

        # Convert to complete paths
        for final_state in current_states:
            path = self._reconstruct_path(final_state)
            paths.append(path)

        return paths

    def _explore_oscillating(self, portal: PortalState) -> List[PortalPath]:
        """Oscillating strategy: Fill from both ends inward (100→1→99→2→98→3...)"""
        # TODO: Implement oscillating exploration
        # For now, fall back to reverse chronological
        print("  (Oscillating not yet implemented, using reverse chronological)")
        return self._explore_reverse_chronological(portal)

    def _explore_random_sampling(self, portal: PortalState) -> List[PortalPath]:
        """Random sampling strategy: Fill steps in random order"""
        # TODO: Implement random sampling
        # For now, fall back to reverse chronological
        print("  (Random sampling not yet implemented, using reverse chronological)")
        return self._explore_reverse_chronological(portal)

    def _generate_antecedents(
        self,
        current_state: PortalState,
        target_year: int = None,
        count: int = None
    ) -> List[PortalState]:
        """
        Generate N plausible previous states using LLM.

        Creates diverse candidate antecedent states that could lead to the consequent.
        Uses structured LLM generation to ensure realistic, varied backward paths.

        Args:
            current_state: The consequent state to work backward from
            target_year: Target year for antecedent states
            count: Number of candidates to generate

        Returns:
            List of PortalState objects representing plausible antecedents
        """
        count = count or self.config.candidate_antecedents_per_step
        target_year = target_year or (current_state.year - 1)

        # If no LLM client, fall back to placeholder
        if not self.llm:
            print("    ⚠️  No LLM client available, using placeholder antecedents")
            return self._generate_placeholder_antecedents(current_state, target_year, count)

        # Build LLM prompt for antecedent generation
        system_prompt = "You are an expert at backward temporal reasoning and counterfactual analysis."

        # Extract key entities for context
        entity_names = [e.entity_id for e in current_state.entities[:10]] if current_state.entities else []
        entity_summary = f"{len(current_state.entities)} entities" if current_state.entities else "No entities yet"
        if entity_names:
            entity_summary += f" (including {', '.join(entity_names[:5])})"

        user_prompt = f"""Generate {count} DIVERSE and DISTINCT plausible antecedent states that could naturally lead to this consequent state.

CONSEQUENT STATE (Year {current_state.year}):
{current_state.description}

Entities: {entity_summary}
World Context: {current_state.world_state}

TARGET YEAR FOR ANTECEDENTS: {target_year}

INSTRUCTIONS:
1. Generate {count} DIFFERENT possible states for year {target_year}
2. Each should represent a distinct path/strategy/decision that could lead to the consequent
3. Vary the approaches: some gradual, some pivotal moments, some lucky breaks
4. Ensure each is historically/causally plausible
5. Consider: entity capabilities, resource constraints, time requirements, external events

For EACH antecedent, provide:
- description: Detailed narrative of what's happening in {target_year} (2-3 sentences)
- key_events: Array of 2-4 specific events that occurred this year
- entity_changes: Dict mapping entity names to how they changed (skills, relationships, resources)
- world_context: Dict of contextual factors (economy, politics, technology, culture)
- causal_link: 1-2 sentence explanation of how this leads to the consequent

Return as JSON with an "antecedents" array containing {count} antecedent objects."""

        try:
            # Define schema for structured output
            from pydantic import BaseModel

            class AntecedentSchema(BaseModel):
                description: str
                key_events: List[str]
                entity_changes: Dict[str, str]
                world_context: Dict[str, Any]
                causal_link: str

            class AntecedentList(BaseModel):
                """Wrapper for list of antecedents"""
                antecedents: List[AntecedentSchema]

            # Call LLM with structured generation
            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=AntecedentList,
                system_prompt=system_prompt,
                temperature=0.8,  # Higher temp for diversity
                max_tokens=2000
            )

            # Extract list from wrapper
            antecedent_data = result.antecedents if hasattr(result, 'antecedents') else []

            # Convert to PortalState objects
            antecedents = []
            for i, data in enumerate(antecedent_data[:count]):  # Limit to requested count
                # Create antecedent state
                state = PortalState(
                    year=target_year,
                    description=data.description,
                    entities=current_state.entities.copy(),  # Start with same entities
                    world_state=data.world_context,
                    plausibility_score=0.0,  # Will be scored later
                    parent_state=current_state
                )

                # Store metadata about this antecedent
                state.world_state['key_events'] = data.key_events
                state.world_state['entity_changes'] = data.entity_changes
                state.world_state['causal_link'] = data.causal_link

                antecedents.append(state)

            # If we got fewer than requested, pad with placeholders
            if len(antecedents) < count:
                print(f"    ⚠️  LLM returned {len(antecedents)}/{count} antecedents, padding with placeholders")
                placeholders = self._generate_placeholder_antecedents(
                    current_state, target_year, count - len(antecedents)
                )
                antecedents.extend(placeholders)

            return antecedents

        except Exception as e:
            print(f"    ⚠️  LLM generation failed: {e}")
            print(f"    Falling back to placeholder antecedents")
            return self._generate_placeholder_antecedents(current_state, target_year, count)

    def _generate_placeholder_antecedents(
        self,
        current_state: PortalState,
        target_year: int,
        count: int
    ) -> List[PortalState]:
        """Generate placeholder antecedents when LLM is unavailable"""
        antecedents = []
        for i in range(count):
            antecedent = PortalState(
                year=target_year,
                description=f"Antecedent {i+1} for {current_state.description}",
                entities=current_state.entities.copy(),
                world_state=current_state.world_state.copy(),
                plausibility_score=0.0,
                parent_state=current_state
            )
            antecedents.append(antecedent)
        return antecedents

    def _run_mini_simulation(
        self,
        candidate_state: PortalState,
        steps: int = None
    ) -> Dict[str, Any]:
        """
        Run forward mini-simulation from candidate state to validate realism.

        This executes a lightweight forward simulation including:
        - State progression (candidate → T+1 → T+2 → ...)
        - Dialog generation between entities (if enabled)
        - Knowledge flow tracking
        - Coherence metrics computation

        The simulation results are used by the judge LLM to evaluate which
        candidate antecedent produces the most realistic forward path.

        Args:
            candidate_state: Starting state to simulate forward from
            steps: Number of forward steps (default: config.simulation_forward_steps)

        Returns:
            Dict with:
            - states: List[PortalState] - forward progression
            - dialogs: List[Dict] - generated conversations (if enabled)
            - coherence_metrics: Dict - internal consistency scores
            - simulation_narrative: str - human-readable summary
            - emergent_events: List[str] - unexpected but plausible developments
        """
        steps = steps or self.config.simulation_forward_steps

        # Initialize simulation results
        simulated_states = [candidate_state]
        dialogs = []
        emergent_events = []

        # Limit entities for performance
        max_entities = self.config.simulation_max_entities
        active_entities = candidate_state.entities[:max_entities] if candidate_state.entities else []

        # Simulate forward steps
        for step in range(steps):
            current = simulated_states[-1]
            next_year = current.year + 1

            # Generate next state description using LLM
            if self.llm:
                try:
                    next_state_description = self._generate_forward_state(current, next_year)
                except Exception as e:
                    print(f"      ⚠️  Forward state generation failed: {e}")
                    next_state_description = f"Year {next_year}: Continuation of {current.description[:50]}..."
            else:
                next_state_description = f"Year {next_year}: Continuation of {current.description[:50]}..."

            # Create next state
            next_state = PortalState(
                year=next_year,
                description=next_state_description,
                entities=active_entities.copy(),
                world_state=current.world_state.copy(),
                plausibility_score=0.0
            )
            simulated_states.append(next_state)

            # Generate dialog if enabled and we have entities
            if self.config.simulation_include_dialog and len(active_entities) >= 2 and self.llm:
                try:
                    dialog_data = self._generate_simulation_dialog(
                        current_state=current,
                        next_state=next_state,
                        entities=active_entities[:3]  # Limit to 3 for dialog
                    )
                    dialogs.append(dialog_data)
                except Exception as e:
                    print(f"      ⚠️  Dialog generation failed: {e}")

        # Compute coherence metrics
        coherence_metrics = self._compute_simulation_coherence(simulated_states)

        # Generate narrative summary
        narrative = self._generate_simulation_narrative(simulated_states, dialogs)

        return {
            "states": simulated_states,
            "dialogs": dialogs,
            "coherence_metrics": coherence_metrics,
            "simulation_narrative": narrative,
            "emergent_events": emergent_events,
            "candidate_year": candidate_state.year,
            "simulation_end_year": simulated_states[-1].year if simulated_states else candidate_state.year
        }

    def _generate_forward_state(self, current_state: PortalState, next_year: int) -> str:
        """Generate description of next state in forward simulation"""
        system_prompt = "You are an expert at forward temporal simulation and causal reasoning."

        user_prompt = f"""Given this state, generate a plausible description of what happens in the next year.

CURRENT STATE (Year {current_state.year}):
{current_state.description}

World Context: {current_state.world_state}

Generate a concise (2-3 sentences) description of what happens in year {next_year}.
Consider:
- Natural progression of events from current state
- Realistic timeframes for change
- Entity capabilities and resources
- External factors and constraints

Return only the description text, no extra formatting."""

        try:
            response = self.llm.service.call(
                system=system_prompt,
                user=user_prompt,
                temperature=0.7,
                max_tokens=300,
                call_type="forward_state_generation"
            )
            return response.content.strip()
        except:
            return f"Year {next_year}: Natural continuation of events from {current_state.year}"

    def _generate_simulation_dialog(
        self,
        current_state: PortalState,
        next_state: PortalState,
        entities: List[Entity]
    ) -> Dict[str, Any]:
        """Generate dialog for mini-simulation"""
        if not entities or len(entities) < 2:
            return {}

        # Build simplified dialog prompt
        entity_names = [e.entity_id for e in entities]

        prompt = f"""Generate a brief 2-3 turn dialog between entities during this transition.

FROM (Year {current_state.year}): {current_state.description[:200]}

TO (Year {next_state.year}): {next_state.description[:200]}

Participants: {', '.join(entity_names[:3])}

Generate realistic dialog showing how entities discuss or react to this transition.
Keep it brief (2-3 turns total) and focused on the key developments."""

        try:
            dialog_data = self.llm.generate_dialog(
                prompt=prompt,
                max_tokens=500,
                model=None  # Use default
            )
            return {
                "year": current_state.year,
                "turns": len(dialog_data.turns) if hasattr(dialog_data, 'turns') else 0,
                "participants": entity_names,
                "summary": f"Dialog between {', '.join(entity_names[:2])} about transition to {next_state.year}"
            }
        except:
            return {
                "year": current_state.year,
                "turns": 0,
                "participants": entity_names,
                "summary": "Dialog generation unavailable"
            }

    def _compute_simulation_coherence(self, states: List[PortalState]) -> Dict[str, float]:
        """Compute coherence metrics for simulation"""
        if len(states) < 2:
            return {"coherence": 1.0, "continuity": 1.0, "plausibility": 1.0}

        # Simple heuristics for coherence
        # In production, these would be more sophisticated

        # Continuity: Do states flow logically?
        continuity = 0.8  # Placeholder

        # Plausibility: Are individual states realistic?
        avg_plausibility = sum(s.plausibility_score for s in states) / len(states) if states else 0.5

        # Overall coherence
        coherence = (continuity + avg_plausibility) / 2

        return {
            "coherence": coherence,
            "continuity": continuity,
            "plausibility": avg_plausibility,
            "state_count": len(states)
        }

    def _generate_simulation_narrative(
        self,
        states: List[PortalState],
        dialogs: List[Dict]
    ) -> str:
        """Generate human-readable narrative summary of simulation"""
        if not states:
            return "Empty simulation"

        start_year = states[0].year
        end_year = states[-1].year
        dialog_count = len(dialogs)

        # Build narrative
        narrative_parts = [
            f"Simulation from {start_year} to {end_year} ({len(states)} states):"
        ]

        # Add key state transitions
        for i, state in enumerate(states):
            if i == 0:
                narrative_parts.append(f"  Start ({state.year}): {state.description[:100]}...")
            elif i == len(states) - 1:
                narrative_parts.append(f"  End ({state.year}): {state.description[:100]}...")

        # Add dialog summary
        if dialog_count > 0:
            narrative_parts.append(f"  Generated {dialog_count} dialog exchanges")

        return "\n".join(narrative_parts)

    def _judge_simulation_realism(
        self,
        candidate_antecedents: List[PortalState],
        simulation_results: List[Dict[str, Any]],
        consequent_state: PortalState
    ) -> List[float]:
        """
        Use judge LLM to evaluate which simulation is most realistic.

        Presents N simulations to judge and asks: "Which of these backward-then-forward
        paths is most plausible?" Judge evaluates based on:
        - Forward simulation coherence
        - Dialog realism (if generated)
        - Internal consistency
        - Natural progression to target state

        Args:
            candidate_antecedents: The N candidate previous states
            simulation_results: Results from _run_mini_simulation() for each
            consequent_state: The state we're trying to reach

        Returns:
            List of scores (0.0-1.0) for each candidate
        """
        if not self.llm or not candidate_antecedents:
            # Fall back to uniform random scores
            return [np.random.uniform(0.5, 1.0) for _ in candidate_antecedents]

        # Build judge prompt
        system_prompt = """You are an expert judge evaluating the realism and plausibility of temporal simulations.

Your task: Rate how realistic each candidate backward path is, based on:
1. Forward simulation coherence - Do events flow logically?
2. Dialog realism - Are conversations natural and contextually appropriate?
3. Internal consistency - Are there contradictions or impossibilities?
4. Causal necessity - Does the antecedent naturally lead to the consequent?
5. Entity capabilities - Can entities actually accomplish what's described?

Rate each candidate 0.0-1.0 where:
- 1.0 = Highly realistic, all aspects coherent
- 0.7 = Plausible with minor issues
- 0.5 = Possible but several concerns
- 0.3 = Implausible, major problems
- 0.0 = Impossible or completely incoherent"""

        # Build candidate descriptions
        candidate_descriptions = []
        for i, (candidate, sim_result) in enumerate(zip(candidate_antecedents, simulation_results)):
            # Extract key information
            candidate_year = candidate.year
            candidate_desc = candidate.description
            narrative = sim_result.get("simulation_narrative", "No narrative")
            coherence = sim_result.get("coherence_metrics", {})
            dialogs = sim_result.get("dialogs", [])

            # Build candidate block
            candidate_block = f"""
CANDIDATE {i+1}:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Antecedent Year: {candidate_year}
Antecedent State: {candidate_desc[:300]}

Forward Simulation:
{narrative}

Coherence Metrics:
- Overall coherence: {coherence.get('coherence', 0.0):.2f}
- Continuity: {coherence.get('continuity', 0.0):.2f}
- State plausibility: {coherence.get('plausibility', 0.0):.2f}

Dialog Summary: {len(dialogs)} conversations generated
{self._format_dialog_summary(dialogs)}

Causal Link: {candidate.world_state.get('causal_link', 'Not specified')}
"""
            candidate_descriptions.append(candidate_block)

        # Combine into full prompt
        user_prompt = f"""Evaluate the realism of these {len(candidate_antecedents)} backward temporal paths.

TARGET STATE (What we need to reach):
Year: {consequent_state.year}
Description: {consequent_state.description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CANDIDATES TO EVALUATE:

{"".join(candidate_descriptions)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK: Rate each candidate 0.0-1.0 based on realism and plausibility.

Return JSON with:
{{
  "scores": [score1, score2, score3, ...],
  "reasoning": "Brief explanation of your ratings",
  "best_candidate": candidate_number (1-indexed),
  "key_concerns": ["concern1", "concern2", ...]
}}

Focus on: forward coherence, dialog realism, causal necessity, internal consistency."""

        try:
            # Call judge LLM
            from pydantic import BaseModel

            class JudgeResult(BaseModel):
                scores: List[float]
                reasoning: str
                best_candidate: int
                key_concerns: List[str]

            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=JudgeResult,
                system_prompt=system_prompt,
                temperature=self.config.judge_temperature,
                max_tokens=1000,
                model=self.config.judge_model
            )

            # Validate and normalize scores
            scores = result.scores[:len(candidate_antecedents)]  # Trim to match candidates

            # Ensure scores are in valid range
            scores = [max(0.0, min(1.0, s)) for s in scores]

            # If we got fewer scores than candidates, pad with average
            if len(scores) < len(candidate_antecedents):
                avg_score = sum(scores) / len(scores) if scores else 0.5
                scores.extend([avg_score] * (len(candidate_antecedents) - len(scores)))

            # Log judge reasoning
            print(f"      Judge: Best candidate #{result.best_candidate}, Reasoning: {result.reasoning[:100]}...")

            return scores

        except Exception as e:
            print(f"      ⚠️  Judge LLM failed: {e}")
            print(f"      Falling back to coherence-based scoring")

            # Fall back to coherence metrics from simulations
            scores = []
            for sim_result in simulation_results:
                coherence = sim_result.get("coherence_metrics", {}).get("coherence", 0.5)
                scores.append(coherence)

            return scores

    def _format_dialog_summary(self, dialogs: List[Dict]) -> str:
        """Format dialog summary for judge prompt"""
        if not dialogs:
            return "  No dialogs generated"

        summaries = []
        for dialog in dialogs[:3]:  # Limit to first 3
            year = dialog.get("year", "?")
            turns = dialog.get("turns", 0)
            summary = dialog.get("summary", "Dialog")
            summaries.append(f"  - Year {year}: {turns} turns - {summary}")

        if len(dialogs) > 3:
            summaries.append(f"  ... and {len(dialogs) - 3} more dialogs")

        return "\n".join(summaries) if summaries else "  No dialog details"

    def _score_antecedents(
        self,
        antecedents: List[PortalState],
        consequent: PortalState
    ) -> List[PortalState]:
        """
        Score antecedents using either simulation judging or static hybrid scoring.

        If use_simulation_judging is enabled, runs forward mini-simulations and uses
        a judge LLM to evaluate realism. Otherwise, uses traditional static scoring.

        Args:
            antecedents: Candidate antecedent states to score
            consequent: The consequent state we're trying to reach

        Returns:
            Sorted list of antecedents by plausibility score (descending)
        """
        # Check if simulation judging is enabled
        if self.config.use_simulation_judging:
            return self._score_antecedents_with_simulation(antecedents, consequent)

        # Traditional static scoring
        scored = []

        for ant in antecedents:
            scores = {
                "llm": self._llm_score(ant, consequent),
                "historical": self._historical_precedent_score(ant, consequent),
                "causal": self._causal_necessity_score(ant, consequent),
                "capability": self._entity_capability_score(ant, consequent),
                "dynamic_context": self._dynamic_context_score(ant, consequent)
            }

            # Weighted average
            total_score = (
                scores["llm"] * self.config.llm_scoring_weight +
                scores["historical"] * self.config.historical_precedent_weight +
                scores["causal"] * self.config.causal_necessity_weight +
                scores["capability"] * self.config.entity_capability_weight +
                scores["dynamic_context"] * 0.1  # Dynamic context as tiebreaker
            )

            ant.plausibility_score = total_score
            scored.append(ant)

        # Sort by score descending
        return sorted(scored, key=lambda s: s.plausibility_score, reverse=True)

    def _score_antecedents_with_simulation(
        self,
        antecedents: List[PortalState],
        consequent: PortalState
    ) -> List[PortalState]:
        """
        Score antecedents by running forward mini-simulations and using judge LLM.

        This is the SIMULATION-BASED JUDGING approach where we:
        1. Run forward simulation from each candidate antecedent
        2. Generate non-deterministic dialog and interactions
        3. Use judge LLM to evaluate which simulation is most realistic
        4. Score based on judge's holistic assessment

        This is computationally expensive but produces much higher quality paths
        than static scoring alone.

        Args:
            antecedents: Candidate antecedent states to evaluate
            consequent: The consequent state we're trying to reach

        Returns:
            Sorted list of antecedents by judge scores (descending)
        """
        if not antecedents:
            return []

        print(f"    🎬 SIMULATION JUDGING MODE")
        print(f"    Running mini-simulations for {len(antecedents)} candidates...")
        print(f"    Each simulation: {self.config.simulation_forward_steps} forward steps")
        if self.config.simulation_include_dialog:
            print(f"    Dialog generation: ENABLED")

        # Run simulations for each candidate
        simulation_results = []
        for i, ant in enumerate(antecedents):
            print(f"      Candidate {i+1}/{len(antecedents)}: Simulating forward from year {ant.year}...")
            try:
                sim_result = self._run_mini_simulation(ant, self.config.simulation_forward_steps)
                simulation_results.append(sim_result)
            except Exception as e:
                print(f"      ⚠️  Simulation failed: {e}")
                # Add empty simulation result
                simulation_results.append({
                    "states": [ant],
                    "dialogs": [],
                    "coherence_metrics": {"coherence": 0.3},
                    "simulation_narrative": f"Simulation failed: {e}",
                    "emergent_events": [],
                    "candidate_year": ant.year,
                    "simulation_end_year": ant.year
                })

        # Judge all simulations
        print(f"    ⚖️  Judge LLM evaluating realism of {len(antecedents)} simulations...")
        scores = self._judge_simulation_realism(antecedents, simulation_results, consequent)

        # Assign scores to antecedents
        for ant, score in zip(antecedents, scores):
            ant.plausibility_score = score

        # Sort by score descending
        sorted_antecedents = sorted(antecedents, key=lambda s: s.plausibility_score, reverse=True)

        # Print summary
        print(f"    ✓ Simulation judging complete")
        print(f"      Best score: {sorted_antecedents[0].plausibility_score:.3f}")
        print(f"      Score range: {sorted_antecedents[-1].plausibility_score:.3f} - {sorted_antecedents[0].plausibility_score:.3f}")

        return sorted_antecedents

    def _llm_score(self, antecedent: PortalState, consequent: PortalState) -> float:
        """Ask LLM to rate plausibility 0-1"""
        # TODO: Implement LLM scoring
        # For now, return random score
        return np.random.uniform(0.5, 1.0)

    def _historical_precedent_score(self, ant: PortalState, cons: PortalState) -> float:
        """Check if similar transitions occurred in history"""
        # TODO: Query knowledge base for similar patterns
        return 0.7  # Placeholder

    def _causal_necessity_score(self, ant: PortalState, cons: PortalState) -> float:
        """Score based on how REQUIRED the antecedent is for the consequent"""
        # TODO: Check logical implications
        return 0.8  # Placeholder

    def _entity_capability_score(self, ant: PortalState, cons: PortalState) -> float:
        """Validate entities can actually do what's required"""
        # TODO: Check skills, resources, relationships, timeline
        return 0.9  # Placeholder

    def _dynamic_context_score(self, ant: PortalState, cons: PortalState) -> float:
        """Score based on dynamic world context"""
        # TODO: Check economic, political, technological plausibility
        return 0.7  # Placeholder

    def _prune_low_scoring_paths(self, states: List[PortalState]) -> List[PortalState]:
        """Prune states below threshold to manage path explosion"""
        sorted_states = sorted(states, key=lambda s: s.plausibility_score, reverse=True)
        return sorted_states[:self.config.path_count * 2]

    def _reconstruct_path(self, leaf_state: PortalState) -> PortalPath:
        """Reconstruct complete path from leaf state to portal"""
        states = []
        current = leaf_state

        # Walk backward to collect all states
        while current is not None:
            states.append(current)
            current = current.parent_state

        # Reverse to get origin→portal order
        states.reverse()

        return PortalPath(
            path_id=f"portal_path_{uuid.uuid4().hex[:8]}",
            states=states,
            coherence_score=0.0,  # Will be computed in validation
            pivot_points=[],
            explanation=""
        )

    def _validate_forward_coherence(self, paths: List[PortalPath]) -> List[PortalPath]:
        """Check if backward-generated paths make sense forward"""
        valid_paths = []

        for path in paths:
            # Simulate forward: Does origin → portal via path make sense?
            coherence = self._check_forward_simulation(path)

            if coherence >= self.config.coherence_threshold:
                path.coherence_score = coherence
                valid_paths.append(path)
            else:
                # Adaptive failure handling
                resolution = self._decide_failure_resolution(path, coherence)

                if resolution == FailureResolution.BACKTRACK:
                    fixed_path = self._attempt_backtrack_fix(path)
                    if fixed_path and fixed_path.coherence_score >= self.config.coherence_threshold:
                        valid_paths.append(fixed_path)

                elif resolution == FailureResolution.MARK:
                    # Include but flag issues
                    path.coherence_score = coherence
                    path.explanation += "\n⚠️ LOW COHERENCE - Review recommended"
                    valid_paths.append(path)

        return valid_paths

    def _check_forward_simulation(self, path: PortalPath) -> float:
        """Simulate forward to check coherence"""
        # TODO: Implement forward simulation validation
        # For now, return weighted average of state plausibility scores
        if not path.states:
            return 0.0

        avg_score = sum(s.plausibility_score for s in path.states) / len(path.states)
        return avg_score

    def _decide_failure_resolution(self, path: PortalPath, coherence: float) -> FailureResolution:
        """Adaptively decide how to handle failed path"""
        if coherence < 0.3:
            return FailureResolution.PRUNE
        elif coherence < 0.5 and self.config.max_backtrack_depth > 0:
            return FailureResolution.BACKTRACK
        elif coherence < self.config.coherence_threshold:
            return FailureResolution.MARK
        else:
            return FailureResolution.PRUNE

    def _attempt_backtrack_fix(self, path: PortalPath) -> Optional[PortalPath]:
        """Try to fix path by backtracking and retrying"""
        # TODO: Implement backtracking
        return None  # Placeholder

    def _rank_paths(self, paths: List[PortalPath]) -> List[PortalPath]:
        """Final ranking by coherence score"""
        return sorted(paths, key=lambda p: p.coherence_score, reverse=True)

    def _detect_pivot_points(self, path: PortalPath) -> List[int]:
        """Identify critical decision moments where paths diverge most"""
        # TODO: Analyze variance in antecedent generation at each step
        # For now, return placeholder pivot points
        pivot_points = []
        for i, state in enumerate(path.states):
            if len(state.children_states) > 5:  # High branching = pivot
                pivot_points.append(i)
        return pivot_points
