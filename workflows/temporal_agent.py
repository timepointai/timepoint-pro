# ============================================================================
# workflows/temporal_agent.py - Modal Temporal Causality (Mechanism 7, 17)
# ============================================================================
"""
Temporal agent for modal causality and time-as-entity modeling.

Contains:
- TemporalAgent: Time as entity with goals in non-Pearl modes (@M7, @M17)
  - determine_fidelity_temporal_strategy: Optimal fidelity + temporal strategy (@M1+M17)
  - influence_event_probability: Adjust event probability by mode
  - generate_next_timepoint: Generate forward temporal progression (@M7)
  - generate_antecedent_timepoint: Generate backward PORTAL inference (@M17)
  - run_portal_simulation: Execute backward simulation
"""

from typing import List, Dict, Optional, Tuple
from datetime import timedelta
import uuid
import re
import numpy as np

from schemas import TemporalMode, ExposureEvent, ResolutionLevel
from metadata.tracking import track_mechanism


# M1 → M17 Connection: Resolution level determines token budget per entity
# This connects fidelity decisions (M1) to generation granularity (M17)
RESOLUTION_TOKEN_BUDGET = {
    ResolutionLevel.TENSOR_ONLY: 100,    # Minimal: just state snapshot
    ResolutionLevel.SCENE: 500,          # Brief: scene description
    ResolutionLevel.GRAPH: 1000,         # Moderate: relationship context
    ResolutionLevel.DIALOG: 3000,        # Detailed: full dialog turns
    ResolutionLevel.TRAINED: 5000,       # Rich: trained entity detail
    ResolutionLevel.FULL_DETAIL: 8000,   # Maximum: complete entity state
}


class TemporalAgent:
    """Time as entity with goals in non-Pearl modes"""

    def __init__(self, mode: Optional[TemporalMode] = None, config: Optional[Dict] = None,
                 store=None, llm_client=None, temporal_config=None):
        # Support both signatures
        if store is not None or llm_client is not None:
            # New signature with store and llm_client
            self.store = store
            self.llm_client = llm_client
            self.mode = mode or TemporalMode.PEARL
            self.goals = []
        else:
            # Old signature with mode and config
            self.mode = mode or TemporalMode.PEARL
            self.goals = (config or {}).get("goals", [])
            self.store = None
            self.llm_client = None

        self.personality = np.random.randn(5)  # Time's "style" vector

        # M1+M17: Store fidelity-temporal configuration
        self.temporal_config = temporal_config
        self.fidelity_strategy = None  # Will be set during temporal generation

        # M1 → M17: Token usage tracking for fidelity-aware generation
        self.tokens_used = 0
        self.token_budget_remaining = None  # Set from fidelity_strategy
        self.entity_token_usage = {}  # Track per-entity token consumption

    @track_mechanism("M1", "fidelity_token_budget")
    def get_entity_token_budget(self, entity) -> int:
        """
        Get token budget for an entity based on its resolution level.

        This connects M1 (Fidelity/Resolution) → M17 (Generation Granularity).
        Higher resolution entities get more tokens for richer content generation.

        Args:
            entity: Entity object with resolution_level attribute

        Returns:
            Token budget for this entity's generation
        """
        resolution = getattr(entity, 'resolution_level', ResolutionLevel.SCENE)
        return RESOLUTION_TOKEN_BUDGET.get(resolution, 500)  # Default to SCENE budget

    def track_token_usage(self, entity_id: str, tokens: int):
        """Track tokens used for an entity during generation"""
        self.tokens_used += tokens
        self.entity_token_usage[entity_id] = self.entity_token_usage.get(entity_id, 0) + tokens

    def get_remaining_budget(self) -> Optional[int]:
        """Get remaining token budget based on fidelity strategy"""
        if self.fidelity_strategy and hasattr(self.fidelity_strategy, 'token_budget'):
            return max(0, self.fidelity_strategy.token_budget - self.tokens_used)
        return None  # No budget constraint

    @track_mechanism("M1+M17", "adaptive_fidelity_temporal_strategy")
    def determine_fidelity_temporal_strategy(
        self,
        config,  # TemporalConfig
        context: Dict
    ) -> "FidelityTemporalStrategy":
        """
        Determine optimal fidelity + temporal strategy based on:
        - Modal requirements (PORTAL pivots, DIRECTORIAL climax, CYCLICAL prophecy timing)
        - Token budget constraints
        - Causal necessity (minimum time for state evolution)
        - Entity development needs

        Args:
            config: TemporalConfig with mode and budget settings
            context: Dict with:
                - portal_state: PortalState (for PORTAL mode)
                - origin_year: int
                - entities: List[Entity]
                - token_budget: float (optional override)

        Returns:
            FidelityTemporalStrategy: Complete allocation strategy
        """
        from schemas import FidelityTemporalStrategy, ResolutionLevel

        # Route to mode-specific strategy
        if self.mode == TemporalMode.PORTAL:
            return self._strategy_for_portal_mode(config, context)
        elif self.mode == TemporalMode.DIRECTORIAL:
            return self._strategy_for_directorial_mode(config, context)
        elif self.mode == TemporalMode.CYCLICAL:
            return self._strategy_for_cyclical_mode(config, context)
        elif self.mode == TemporalMode.BRANCHING:
            return self._strategy_for_branching_mode(config, context)
        else:
            # Default PEARL mode or others
            return self._strategy_for_default_mode(config, context)

    def _strategy_for_portal_mode(self, config, context) -> "FidelityTemporalStrategy":
        """
        PORTAL mode strategy: Blended fidelity allocation.

        Fidelity allocation:
        - Portal endpoint: TRAINED (maximum detail for known outcome)
        - Origin: TRAINED (maximum detail for known starting point)
        - Pivot points: DIALOG (detected via branching factor or judge recommendation)
        - Bridge states: SCENE (connecting states)
        - Checkpoints: TENSOR_ONLY (minimal state snapshots)

        Temporal allocation:
        - Adaptive based on causal necessity
        - Denser steps around pivots, sparser for stable periods
        """
        from schemas import FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

        # Extract context
        portal_year = config.portal_year
        origin_year = config.origin_year
        backward_steps = config.backward_steps  # Suggestion, not command

        # Get fidelity planning mode from config (default to HYBRID for portal)
        planning_mode = getattr(config, 'fidelity_planning_mode', FidelityPlanningMode.HYBRID)
        budget_mode = getattr(config, 'token_budget_mode', TokenBudgetMode.SOFT_GUIDANCE)
        token_budget = getattr(config, 'token_budget', 15000)

        # Calculate temporal strategy
        total_months = (portal_year - origin_year) * 12

        if planning_mode == FidelityPlanningMode.PROGRAMMATIC:
            # Pre-planned schedule using fidelity template
            fidelity_template = getattr(config, 'fidelity_template', 'balanced')
            strategy = self._apply_fidelity_template(fidelity_template, backward_steps, total_months)

            return FidelityTemporalStrategy(
                mode=self.mode,
                planning_mode=planning_mode,
                budget_mode=budget_mode,
                token_budget=token_budget,
                timepoint_count=len(strategy['fidelity_schedule']),
                fidelity_schedule=strategy['fidelity_schedule'],
                temporal_steps=strategy['temporal_steps'],
                adaptive_threshold=0.7,
                min_resolution=ResolutionLevel.TENSOR_ONLY,
                max_resolution=ResolutionLevel.TRAINED,
                allocation_rationale=f"PORTAL mode programmatic: {fidelity_template} template",
                estimated_tokens=strategy['estimated_tokens'],
                estimated_cost_usd=strategy['estimated_tokens'] * 0.000002  # Rough estimate
            )

        elif planning_mode == FidelityPlanningMode.ADAPTIVE:
            # Fully adaptive - engine decides per-step during simulation
            # For now, provide initial estimate
            return FidelityTemporalStrategy(
                mode=self.mode,
                planning_mode=planning_mode,
                budget_mode=budget_mode,
                token_budget=token_budget,
                timepoint_count=backward_steps,  # Initial estimate
                fidelity_schedule=[],  # Will be determined per-step
                temporal_steps=[],  # Will be determined per-step
                adaptive_threshold=0.7,
                min_resolution=ResolutionLevel.TENSOR_ONLY,
                max_resolution=ResolutionLevel.TRAINED,
                allocation_rationale="PORTAL mode adaptive: fidelity determined per-step based on simulation state",
                estimated_tokens=token_budget,  # Use budget as estimate
                estimated_cost_usd=token_budget * 0.000002
            )

        else:  # HYBRID
            # Start with programmatic plan, allow upgrades
            fidelity_template = getattr(config, 'fidelity_template', 'portal_pivots')
            strategy = self._apply_fidelity_template(fidelity_template, backward_steps, total_months)

            return FidelityTemporalStrategy(
                mode=self.mode,
                planning_mode=planning_mode,
                budget_mode=budget_mode,
                token_budget=token_budget,
                timepoint_count=len(strategy['fidelity_schedule']),
                fidelity_schedule=strategy['fidelity_schedule'],
                temporal_steps=strategy['temporal_steps'],
                adaptive_threshold=0.75,  # Higher threshold for upgrades in hybrid
                min_resolution=ResolutionLevel.TENSOR_ONLY,
                max_resolution=ResolutionLevel.TRAINED,
                allocation_rationale=f"PORTAL mode hybrid: {fidelity_template} template with adaptive upgrades",
                estimated_tokens=strategy['estimated_tokens'],
                estimated_cost_usd=strategy['estimated_tokens'] * 0.000002
            )

    def _apply_fidelity_template(self, template_name: str, suggested_steps: int, total_months: int) -> Dict:
        """
        Apply a fidelity template to generate programmatic allocation.

        Templates define "musical scores" - patterns of fidelity + temporal allocation.
        """
        from schemas import ResolutionLevel

        # Import template library (will be defined in Phase 3.2)
        # For now, provide basic templates

        if template_name == "minimalist":
            # SCALED: 70% TENSOR, 21% SCENE, 7% DIALOG
            n = max(3, suggested_steps)
            tensor_count = max(1, int(n * 0.70))
            scene_count = max(1, int(n * 0.21))
            dialog_count = max(1, n - tensor_count - scene_count)

            fidelity_schedule = ([ResolutionLevel.TENSOR_ONLY] * tensor_count +
                               [ResolutionLevel.SCENE] * scene_count +
                               [ResolutionLevel.DIALOG] * dialog_count)
            # Even temporal distribution
            month_step = total_months // len(fidelity_schedule) if fidelity_schedule else 1
            temporal_steps = [month_step] * len(fidelity_schedule)
            estimated_tokens = tensor_count * 200 + scene_count * 1000 + dialog_count * 10000

        elif template_name == "balanced":
            # SCALED: 33% TENSOR, 33% SCENE, 20% GRAPH, 13% DIALOG
            # Scale based on suggested_steps, respecting the ratio
            n = max(4, suggested_steps)  # Minimum 4 steps for distribution
            tensor_count = max(1, int(n * 0.33))
            scene_count = max(1, int(n * 0.33))
            graph_count = max(1, int(n * 0.20))
            dialog_count = max(1, n - tensor_count - scene_count - graph_count)

            fidelity_schedule = ([ResolutionLevel.TENSOR_ONLY] * tensor_count +
                               [ResolutionLevel.SCENE] * scene_count +
                               [ResolutionLevel.GRAPH] * graph_count +
                               [ResolutionLevel.DIALOG] * dialog_count)
            month_step = total_months // len(fidelity_schedule) if fidelity_schedule else 1
            temporal_steps = [month_step] * len(fidelity_schedule)
            estimated_tokens = tensor_count * 200 + scene_count * 1000 + graph_count * 5000 + dialog_count * 10000

        elif template_name == "portal_pivots":
            # SCALED: Endpoint + Origin = TRAINED, middle = balanced distribution
            # 2 endpoints TRAINED, middle: 50% TENSOR, 25% SCENE, 13% DIALOG
            n = max(4, suggested_steps)
            middle_count = n - 2  # Reserve 2 for TRAINED endpoints

            if middle_count <= 0:
                # Very short simulation - all TRAINED
                fidelity_schedule = [ResolutionLevel.TRAINED] * n
            else:
                tensor_count = max(1, int(middle_count * 0.50))
                scene_count = max(1, int(middle_count * 0.25))
                dialog_count = max(0, middle_count - tensor_count - scene_count)

                fidelity_schedule = ([ResolutionLevel.TRAINED] +
                                   [ResolutionLevel.TENSOR_ONLY] * tensor_count +
                                   [ResolutionLevel.SCENE] * scene_count +
                                   [ResolutionLevel.DIALOG] * dialog_count +
                                   [ResolutionLevel.TRAINED])

            month_step = total_months // len(fidelity_schedule) if fidelity_schedule else 1
            temporal_steps = [month_step] * len(fidelity_schedule)
            estimated_tokens = 2 * 50000 + (len(fidelity_schedule) - 2) * 1000

        elif template_name == "max_quality":
            # SCALED: 66% DIALOG, 33% TRAINED (maximum detail throughout)
            n = max(3, suggested_steps)
            dialog_count = max(1, int(n * 0.66))
            trained_count = max(1, n - dialog_count)

            fidelity_schedule = ([ResolutionLevel.DIALOG] * dialog_count +
                               [ResolutionLevel.TRAINED] * trained_count)
            month_step = total_months // len(fidelity_schedule) if fidelity_schedule else 1
            temporal_steps = [month_step] * len(fidelity_schedule)
            estimated_tokens = dialog_count * 10000 + trained_count * 50000

        else:
            # Default to balanced
            fidelity_schedule = [ResolutionLevel.SCENE] * suggested_steps
            month_step = total_months // suggested_steps
            temporal_steps = [month_step] * suggested_steps
            estimated_tokens = suggested_steps * 1000

        return {
            'fidelity_schedule': fidelity_schedule,
            'temporal_steps': temporal_steps,
            'estimated_tokens': estimated_tokens
        }

    def _strategy_for_directorial_mode(self, config, context) -> "FidelityTemporalStrategy":
        """
        DIRECTORIAL mode: Allocate fidelity based on narrative arc.

        Fidelity allocation follows five-act dramatic structure:
        - Climax states → TRAINED (maximum detail for peak moments)
        - Rising action → DIALOG (detailed buildup)
        - Setup/Resolution → SCENE (establish/resolve)
        - Bridge states → TENSOR_ONLY (minimal transitions)
        """
        from schemas import FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

        backward_steps = getattr(config, 'backward_steps', 15)
        token_budget = getattr(config, 'token_budget', 15000)
        dramatic_tension = getattr(config, 'dramatic_tension', 0.7)

        # Build fidelity schedule based on five-act narrative arc
        fidelity_schedule = []
        for step in range(backward_steps):
            position = step / max(1, backward_steps)

            if 0.5 <= position < 0.7:
                # Climax: maximum detail
                fidelity_schedule.append(ResolutionLevel.TRAINED)
            elif 0.2 <= position < 0.5:
                # Rising action: detailed buildup
                if dramatic_tension > 0.6:
                    fidelity_schedule.append(ResolutionLevel.DIALOG)
                else:
                    fidelity_schedule.append(ResolutionLevel.SCENE)
            elif position < 0.2:
                # Setup: establish scene
                fidelity_schedule.append(ResolutionLevel.SCENE)
            elif 0.7 <= position < 0.85:
                # Falling action: consequences
                fidelity_schedule.append(ResolutionLevel.SCENE)
            else:
                # Resolution: wrap up
                fidelity_schedule.append(ResolutionLevel.TENSOR_ONLY)

        # Temporal steps: denser around climax, sparser at edges
        temporal_steps = []
        for step in range(backward_steps):
            position = step / max(1, backward_steps)
            if 0.4 <= position < 0.7:
                temporal_steps.append(6)  # Monthly around climax
            elif 0.2 <= position < 0.4 or 0.7 <= position < 0.85:
                temporal_steps.append(12)  # Quarterly for buildup/fallout
            else:
                temporal_steps.append(24)  # Semi-annual for bookends

        # Estimate tokens
        token_map = {
            ResolutionLevel.TENSOR_ONLY: 200,
            ResolutionLevel.SCENE: 1000,
            ResolutionLevel.DIALOG: 3000,
            ResolutionLevel.TRAINED: 5000,
        }
        estimated_tokens = sum(token_map.get(r, 1000) for r in fidelity_schedule)

        return FidelityTemporalStrategy(
            mode=self.mode,
            planning_mode=FidelityPlanningMode.PROGRAMMATIC,
            budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
            token_budget=token_budget,
            timepoint_count=backward_steps,
            fidelity_schedule=fidelity_schedule,
            temporal_steps=temporal_steps,
            adaptive_threshold=0.7,
            min_resolution=ResolutionLevel.TENSOR_ONLY,
            max_resolution=ResolutionLevel.TRAINED,
            allocation_rationale=f"DIRECTORIAL mode: five-act arc allocation (tension={dramatic_tension}). Climax=TRAINED, rising=DIALOG, setup/resolution=SCENE/TENSOR_ONLY",
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_tokens * 0.000002
        )

    def _strategy_for_cyclical_mode(self, config, context) -> "FidelityTemporalStrategy":
        """
        CYCLICAL mode: Allocate based on cycle periods and prophecy fulfillment.

        Fidelity allocation maps cycle boundaries to higher fidelity:
        - Cycle start/end → DIALOG (transition moments)
        - Mid-cycle → SCENE (standard progression)
        - Prophecy states → TRAINED (high-detail prophecy moments)
        """
        from schemas import FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

        cycle_length = getattr(config, 'cycle_length', None) or 4
        loop_count = getattr(config, 'path_count', 3)
        token_budget = getattr(config, 'token_budget', 10000)
        prophecy_accuracy = getattr(config, 'prophecy_accuracy', 0.5)

        total_steps = cycle_length * loop_count
        fidelity_schedule = []

        for step in range(total_steps):
            position_in_cycle = step % cycle_length
            cycle_index = step // cycle_length
            is_boundary = position_in_cycle == 0 or position_in_cycle == cycle_length - 1
            is_prophecy = is_boundary and prophecy_accuracy > 0.3

            if is_prophecy:
                fidelity_schedule.append(ResolutionLevel.TRAINED)
            elif is_boundary:
                fidelity_schedule.append(ResolutionLevel.DIALOG)
            else:
                fidelity_schedule.append(ResolutionLevel.SCENE)

        # Temporal steps: consistent within cycles
        temporal_steps = [1] * total_steps  # Monthly by default

        # Estimate tokens
        token_map = {
            ResolutionLevel.TENSOR_ONLY: 200,
            ResolutionLevel.SCENE: 1000,
            ResolutionLevel.DIALOG: 3000,
            ResolutionLevel.TRAINED: 5000,
        }
        estimated_tokens = sum(token_map.get(r, 1000) for r in fidelity_schedule)

        return FidelityTemporalStrategy(
            mode=self.mode,
            planning_mode=FidelityPlanningMode.PROGRAMMATIC,
            budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
            token_budget=token_budget,
            timepoint_count=total_steps,
            fidelity_schedule=fidelity_schedule,
            temporal_steps=temporal_steps,
            adaptive_threshold=0.7,
            min_resolution=ResolutionLevel.TENSOR_ONLY,
            max_resolution=ResolutionLevel.TRAINED,
            allocation_rationale=f"CYCLICAL mode: {loop_count} cycles x {cycle_length} steps. Boundaries=DIALOG, prophecy=TRAINED, mid-cycle=SCENE",
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_tokens * 0.000002
        )

    def _strategy_for_branching_mode(self, config, context) -> "FidelityTemporalStrategy":
        """
        BRANCHING mode: Allocate fidelity based on branch points.

        Fidelity allocation:
        - Branch points → DIALOG/TRAINED (critical decision moments)
        - Continuations → SCENE (standard forward progression)
        - Origin/endpoint → DIALOG (establishing context)
        """
        from schemas import FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

        backward_steps = getattr(config, 'backward_steps', 15)
        path_count = getattr(config, 'path_count', 4)
        token_budget = getattr(config, 'token_budget', 20000)

        # Calculate branch point intervals
        branch_interval = max(1, backward_steps // path_count)

        fidelity_schedule = []
        for step in range(backward_steps):
            if step == 0 or step == backward_steps - 1:
                # Origin and endpoint
                fidelity_schedule.append(ResolutionLevel.DIALOG)
            elif step > 0 and step % branch_interval == 0:
                # Branch point: high detail for decision moments
                fidelity_schedule.append(ResolutionLevel.TRAINED)
            else:
                # Continuation
                fidelity_schedule.append(ResolutionLevel.SCENE)

        # Temporal steps: even distribution
        temporal_steps = [12] * backward_steps

        # Estimate tokens
        token_map = {
            ResolutionLevel.TENSOR_ONLY: 200,
            ResolutionLevel.SCENE: 1000,
            ResolutionLevel.DIALOG: 3000,
            ResolutionLevel.TRAINED: 5000,
        }
        estimated_tokens = sum(token_map.get(r, 1000) for r in fidelity_schedule)

        return FidelityTemporalStrategy(
            mode=self.mode,
            planning_mode=FidelityPlanningMode.PROGRAMMATIC,
            budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
            token_budget=token_budget,
            timepoint_count=backward_steps,
            fidelity_schedule=fidelity_schedule,
            temporal_steps=temporal_steps,
            adaptive_threshold=0.7,
            min_resolution=ResolutionLevel.TENSOR_ONLY,
            max_resolution=ResolutionLevel.TRAINED,
            allocation_rationale=f"BRANCHING mode: branch points every {branch_interval} steps get TRAINED, endpoints=DIALOG, continuations=SCENE",
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_tokens * 0.000002
        )

    def _strategy_for_default_mode(self, config, context) -> "FidelityTemporalStrategy":
        """Default strategy for PEARL and other modes"""
        from schemas import FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

        return FidelityTemporalStrategy(
            mode=self.mode,
            planning_mode=FidelityPlanningMode.PROGRAMMATIC,
            budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
            token_budget=10000,
            timepoint_count=10,
            fidelity_schedule=[ResolutionLevel.SCENE] * 10,
            temporal_steps=[12] * 10,  # 1 year between each
            adaptive_threshold=0.7,
            min_resolution=ResolutionLevel.TENSOR_ONLY,
            max_resolution=ResolutionLevel.TRAINED,
            allocation_rationale="Default mode: balanced fidelity allocation",
            estimated_tokens=10000,
            estimated_cost_usd=0.02
        )

    def determine_next_step_fidelity_and_time(
        self,
        current_state,  # PortalState
        strategy: "FidelityTemporalStrategy",
        step_num: int,
        context: Dict
    ) -> Tuple[int, "ResolutionLevel"]:
        """
        For ADAPTIVE or HYBRID modes: decide next step's time gap and fidelity level.

        Args:
            current_state: Current PortalState in backward simulation
            strategy: Overall FidelityTemporalStrategy
            step_num: Current step number (0-indexed)
            context: Dict with:
                - entities: List[Entity]
                - pivot_detected: bool (for HYBRID mode)
                - simulation_state: Dict (for adaptive decisions)

        Returns:
            Tuple of (months_to_next_state, resolution_level)
        """
        from schemas import ResolutionLevel, FidelityPlanningMode

        if strategy.planning_mode == FidelityPlanningMode.PROGRAMMATIC:
            # Use pre-planned schedule
            if step_num < len(strategy.temporal_steps):
                return (strategy.temporal_steps[step_num], strategy.fidelity_schedule[step_num])
            else:
                # Fallback
                return (12, ResolutionLevel.SCENE)

        elif strategy.planning_mode == FidelityPlanningMode.ADAPTIVE:
            # Fully adaptive decision
            # Determine fidelity based on current simulation state

            # Check if this is a pivot point (high importance)
            importance_score = context.get('importance_score', 0.5)

            if importance_score > strategy.adaptive_threshold:
                resolution = ResolutionLevel.DIALOG
            elif importance_score > 0.5:
                resolution = ResolutionLevel.SCENE
            else:
                resolution = ResolutionLevel.TENSOR_ONLY

            # Determine temporal step based on state complexity
            # More complex states = shorter time gaps for granularity
            complexity = context.get('state_complexity', 0.5)
            if complexity > 0.7:
                month_step = 1  # Monthly granularity for complex periods
            elif complexity > 0.4:
                month_step = 3  # Quarterly granularity
            else:
                month_step = 12  # Annual granularity for simple periods

            return (month_step, resolution)

        else:  # HYBRID
            # Start with programmatic plan
            if step_num < len(strategy.temporal_steps):
                planned_month_step = strategy.temporal_steps[step_num]
                planned_resolution = strategy.fidelity_schedule[step_num]
            else:
                planned_month_step = 12
                planned_resolution = ResolutionLevel.SCENE

            # Check if we should upgrade due to pivot detection
            pivot_detected = context.get('pivot_detected', False)

            if pivot_detected and planned_resolution < ResolutionLevel.DIALOG:
                # Upgrade to DIALOG for pivot points
                print(f"  Pivot detected at step {step_num}: upgrading {planned_resolution} -> DIALOG")
                return (planned_month_step, ResolutionLevel.DIALOG)

            # Otherwise, use planned allocation
            return (planned_month_step, planned_resolution)

    def influence_event_probability(self, event: str, context: Dict) -> float:
        """Adjust event probability based on temporal mode"""
        base_prob = context.get("base_probability", 0.5)

        if self.mode == TemporalMode.DIRECTORIAL:
            config = context.get("directorial_config", {})
            narrative_arc = config.get("narrative_arc", "rising_action")
            dramatic_tension = config.get("dramatic_tension", 0.7)

            # Boost events that advance the narrative arc
            if self._advances_narrative_arc(event, narrative_arc):
                return min(1.0, base_prob * config.get("coincidence_boost_factor", 1.5))

            # Apply default directorial modification (dramatic tension affects all events)
            return min(1.0, base_prob * (1 + dramatic_tension * 0.3))

        elif self.mode == TemporalMode.CYCLICAL:
            config = context.get("cyclical_config", {})
            cycle_length = config.get("cycle_length", 10)
            destiny_weight = config.get("destiny_weight", 0.6)

            # Check if event closes a temporal loop
            if self._closes_causal_loop(event, context):
                return min(1.0, base_prob * 3.0)  # Major boost for loop closure

            # Apply destiny weighting (always modifies probability)
            modification = 1 + destiny_weight * 0.3  # 1.18 with default weight
            return base_prob * modification

        elif self.mode == TemporalMode.BRANCHING:
            # In branching mode, slightly increase chaos/randomness
            return base_prob * np.random.uniform(0.8, 1.2)

        elif self.mode == TemporalMode.PORTAL:
            config = context.get("portal_config", {})

            # In PORTAL mode, boost events that are causally necessary for the portal endpoint
            # Check if event is on a path to the portal
            is_portal_antecedent = context.get("is_portal_antecedent", False)

            if is_portal_antecedent:
                # Strong boost for events that lead to the portal
                necessity_score = config.get("causal_necessity_weight", 0.3)
                return min(1.0, base_prob * (1 + necessity_score * 2.0))

            # Default: slight reduction for events that don't advance toward portal
            return base_prob * 0.9

        return base_prob  # PEARL mode or default

    def _advances_narrative_arc(self, event: str, narrative_arc: str) -> bool:
        """Check if event advances the current narrative arc"""
        # Simple heuristic - could be made more sophisticated
        arc_keywords = {
            "rising_action": ["conflict", "tension", "challenge", "rising"],
            "climax": ["peak", "crisis", "turning_point", "decision"],
            "falling_action": ["resolution", "aftermath", "consequence"],
            "resolution": ["conclusion", "ending", "closure", "final"]
        }

        event_lower = event.lower()
        keywords = arc_keywords.get(narrative_arc, [])
        return any(keyword in event_lower for keyword in keywords)

    def _closes_causal_loop(self, event: str, context: Dict) -> bool:
        """Check if event closes a causal loop"""
        # Look for prophecy fulfillment patterns
        prophecy_indicators = ["prophecy", "prediction", "foretold", "destiny", "fate"]
        fulfillment_indicators = ["fulfilled", "comes true", "happens", "occurs", "manifested"]

        event_lower = event.lower()
        has_prophecy = any(indicator in event_lower for indicator in prophecy_indicators)
        has_fulfillment = any(indicator in event_lower for indicator in fulfillment_indicators)

        return has_prophecy and has_fulfillment

    @track_mechanism("M7", "causal_temporal_chains")
    def generate_next_timepoint(self, current_timepoint, context: Dict = None) -> "Timepoint":
        """
        Generate the next timepoint in the temporal sequence.

        Args:
            current_timepoint: The current Timepoint object
            context: Optional context dict with information like next_event

        Returns:
            New Timepoint object representing the next moment in time
        """
        from schemas import Timepoint, ResolutionLevel

        context = context or {}

        # FIX BUG #2: Generate sequential timepoint ID instead of chaining
        # Extract sequence number from current ID or generate new one
        current_id = current_timepoint.timepoint_id
        # Try to extract sequence number (e.g., "tp_001" -> 1)
        match = re.match(r'tp_(\d+)', current_id)
        if match:
            next_seq = int(match.group(1)) + 1
            next_id = f"tp_{next_seq:03d}"
        else:
            # Fallback: append sequential suffix
            next_id = f"{current_id.split('_next_')[0]}_seq_{uuid.uuid4().hex[:8]}"

        # Determine time delta based on mode
        if self.mode == TemporalMode.DIRECTORIAL:
            # Time jumps to dramatic moments
            time_delta = timedelta(hours=24)  # Default to 1 day
        elif self.mode == TemporalMode.CYCLICAL:
            # Regular intervals for cycles
            time_delta = timedelta(days=7)  # Weekly cycle
        else:
            # Default progression
            time_delta = timedelta(hours=1)

        next_timestamp = current_timepoint.timestamp + time_delta

        # FIX BUG #1: Generate proper event description instead of concatenation
        if "next_event" in context:
            event_description = context["next_event"]
        else:
            # Generate meaningful progression description instead of concatenating
            iteration = context.get("iteration", 0)
            total = context.get("total", 1)
            event_description = f"Timepoint {iteration + 1}/{total}: Events continue to unfold"

        # M1 → M17: Determine resolution level from fidelity strategy
        # This connects fidelity decisions to generation granularity
        step_num = context.get("iteration", 0)
        if self.fidelity_strategy and hasattr(self.fidelity_strategy, 'fidelity_schedule'):
            if step_num < len(self.fidelity_strategy.fidelity_schedule):
                next_resolution = self.fidelity_strategy.fidelity_schedule[step_num]
            else:
                # Fallback to current resolution if we've exceeded the schedule
                next_resolution = current_timepoint.resolution_level
        else:
            # No fidelity strategy - inherit from current timepoint
            next_resolution = current_timepoint.resolution_level

        # Calculate entity token budgets based on their resolution levels
        # This allows downstream generation to adjust verbosity
        entity_token_budgets = {}
        for entity_id in current_timepoint.entities_present:
            # Default to SCENE resolution for unknown entities
            entity_token_budgets[entity_id] = RESOLUTION_TOKEN_BUDGET.get(
                next_resolution, RESOLUTION_TOKEN_BUDGET[ResolutionLevel.SCENE]
            )

        # Store in context for downstream usage (e.g., dialog synthesis)
        context["entity_token_budgets"] = entity_token_budgets
        context["timepoint_resolution"] = next_resolution

        # ENTITY INFERENCE FIX: Instead of blindly copying entities from parent,
        # infer which entities should be present based on the event description
        available_entities = context.get("available_entities", [])
        if not available_entities:
            # Fall back to entities from current timepoint as available pool
            available_entities = list(current_timepoint.entities_present) if current_timepoint.entities_present else []

        # Infer entities for this new timepoint
        inferred_entities = self._infer_entities_for_timepoint(
            event_description=event_description,
            available_entities=available_entities,
            context=context
        )

        # Create next timepoint
        next_timepoint = Timepoint(
            timepoint_id=next_id,
            timestamp=next_timestamp,
            event_description=event_description,
            entities_present=inferred_entities,  # Use inferred entities, not blind copy
            causal_parent=current_timepoint.timepoint_id,
            resolution_level=next_resolution  # M1 → M17: Use fidelity-determined resolution
        )

        # Save to store if available
        if self.store:
            self.store.save_timepoint(next_timepoint)

            # FIX BUG #6: Create exposure events for entities experiencing this event
            # This ensures entities learn knowledge from events they participate in
            self._create_exposure_events_for_timepoint(next_timepoint)

        return next_timepoint

    def _infer_entities_for_timepoint(
        self,
        event_description: str,
        available_entities: List[str],
        context: Dict = None
    ) -> List[str]:
        """
        Infer which entities should be present at a timepoint based on event description.

        Uses LLM to identify relevant entities from the available list, or generates
        placeholder entity IDs if no LLM is available or no entities are provided.

        Args:
            event_description: Description of the event at this timepoint
            available_entities: List of entity IDs that could be present
            context: Optional context dict with additional information

        Returns:
            List of entity IDs that should be present at this timepoint
        """
        context = context or {}

        # If we have available entities and an LLM client, use LLM to select relevant ones
        if available_entities and self.llm_client:
            try:
                # Build selection prompt
                system_prompt = "You are an expert at identifying which entities are relevant to events."

                user_prompt = f"""Given this event description, identify which entities from the available list should be present.

EVENT DESCRIPTION:
{event_description[:500]}

AVAILABLE ENTITIES:
{', '.join(available_entities[:50])}

INSTRUCTIONS:
1. Select 3-15 entities that would logically be present at or involved in this event
2. Consider: direct participants, witnesses, affected parties, decision makers
3. Don't include entities that wouldn't plausibly be involved

Return ONLY a JSON object with format:
{{"entities_present": ["entity_id_1", "entity_id_2", ...]}}"""

                # Call LLM for entity selection
                response = self.llm_client.client.chat.completions.create(
                    model=self.llm_client.default_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,  # Lower temp for more consistent selection
                    max_tokens=500
                )

                # Parse response - handle both OpenAI-style objects and raw dicts
                # Some providers return dict, others return response objects
                if isinstance(response, dict):
                    # Raw dict response (e.g., some OpenRouter providers)
                    choices = response.get('choices', [])
                    if choices:
                        message = choices[0].get('message', {})
                        content = message.get('content', '')
                    else:
                        content = ''
                else:
                    # OpenAI-style response object
                    content = response.choices[0].message.content

                # Try to extract JSON
                import json
                import re

                # Look for JSON in response
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    result = json.loads(json_match.group())
                    selected = result.get('entities_present', [])

                    # Filter to only include valid entity IDs
                    valid_entities = [e for e in selected if e in available_entities]

                    if valid_entities:
                        return valid_entities

            except Exception as e:
                # Log but don't fail - fall through to alternatives
                print(f"    ⚠️  Entity inference failed: {e}")

        # Fallback 1: Return available entities if we have them (limited to reasonable count)
        if available_entities:
            return available_entities[:10]

        # Fallback 2: Extract potential entity names from event description
        # This provides some data rather than empty list
        import re

        # Look for capitalized words/phrases that might be entity names
        potential_entities = []

        # Find capitalized words (potential proper nouns)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', event_description)
        for word in words[:5]:
            entity_id = word.lower().replace(' ', '_')
            if len(entity_id) > 2:  # Skip very short matches
                potential_entities.append(entity_id)

        # If we found potential entities, return them
        if potential_entities:
            return list(set(potential_entities))[:10]

        # Final fallback: Return empty list with warning
        print(f"    ⚠️  No entities could be inferred for timepoint")
        return []

    def _create_exposure_events_for_timepoint(self, timepoint):
        """
        Create exposure events for entities present at a timepoint.

        Bug Fix: Previously, exposure events were only created for initial knowledge.
        Entities never learned anything from subsequent events they experienced.
        This method creates exposure events so entities acquire knowledge from participation.

        Args:
            timepoint: The Timepoint object to create exposure events for
        """
        from datetime import datetime

        # Create a knowledge item representing the event experience
        # This is a basic "entity experienced event" record
        # More sophisticated knowledge extraction would come from LLM population
        event_knowledge = f"Experienced event: {timepoint.event_description[:200]}"

        # Create exposure event for each entity present
        for entity_id in timepoint.entities_present:
            exposure_event = ExposureEvent(
                entity_id=entity_id,
                event_type="experienced",  # They directly experienced the event
                information=event_knowledge,
                source=f"timepoint_{timepoint.timepoint_id}",
                timestamp=timepoint.timestamp,
                confidence=1.0,  # They were definitely present
                timepoint_id=timepoint.timepoint_id
            )

            # Save to database
            if self.store:
                self.store.save_exposure_event(exposure_event)

    @track_mechanism("M17", "modal_temporal_causality")
    def generate_antecedent_timepoint(self, current_timepoint, context: Dict = None) -> "Timepoint":
        """
        Generate a plausible antecedent (previous) timepoint in PORTAL mode.

        This is the inverse of generate_next_timepoint() - instead of forward temporal
        progression, this generates backward inference from a known state.

        Args:
            current_timepoint: The current Timepoint object (acting as consequent)
            context: Optional context dict with information like target_year, antecedent_description

        Returns:
            New Timepoint object representing a plausible previous state

        Note:
            This method is primarily used by PortalStrategy for backward path exploration.
            In PORTAL mode, we work backward from endpoint to origin.
        """
        from schemas import Timepoint, ResolutionLevel

        if self.mode != TemporalMode.PORTAL:
            raise ValueError(f"generate_antecedent_timepoint() requires mode=PORTAL, got {self.mode}")

        context = context or {}

        # Extract target year from context or calculate backward step
        target_year = context.get("target_year")
        if target_year is None:
            # Default: go back 1 year
            time_delta = timedelta(days=-365)
        else:
            # Calculate delta to reach target year
            current_year = current_timepoint.timestamp.year
            year_diff = current_year - target_year
            time_delta = timedelta(days=year_diff * 365)

        antecedent_timestamp = current_timepoint.timestamp - time_delta

        # Generate antecedent ID
        antecedent_id = f"tp_ante_{uuid.uuid4().hex[:8]}"

        # Get antecedent description from context or generate placeholder
        if "antecedent_description" in context:
            event_description = context["antecedent_description"]
        else:
            # Placeholder - in real implementation, LLM would generate this
            event_description = f"Antecedent state preceding: {current_timepoint.event_description[:100]}"

        # ENTITY INFERENCE FIX: Instead of blindly copying entities from consequent,
        # infer which entities should be present based on the event description
        available_entities = context.get("available_entities", [])
        if not available_entities:
            # Fall back to entities from current timepoint as available pool
            available_entities = list(current_timepoint.entities_present) if current_timepoint.entities_present else []

        # Infer entities for this antecedent event
        inferred_entities = self._infer_entities_for_timepoint(
            event_description=event_description,
            available_entities=available_entities,
            context=context
        )

        # Create antecedent timepoint
        antecedent_timepoint = Timepoint(
            timepoint_id=antecedent_id,
            timestamp=antecedent_timestamp,
            event_description=event_description,
            entities_present=inferred_entities,  # Use inferred entities, not blind copy
            causal_parent=None,  # Will be set during path reconstruction
            resolution_level=current_timepoint.resolution_level
        )

        # Save to store if available
        if self.store:
            self.store.save_timepoint(antecedent_timepoint)

            # Create exposure events for entities experiencing this antecedent state
            self._create_exposure_events_for_timepoint(antecedent_timepoint)

        return antecedent_timepoint

    def run_portal_simulation(self, config) -> List:
        """
        Execute PORTAL mode backward simulation.

        This delegates to PortalStrategy to perform backward inference from
        a known endpoint (portal) to a known origin, discovering plausible
        paths that connect them.

        Args:
            config: TemporalConfig with mode=PORTAL and portal settings

        Returns:
            List of PortalPath objects ranked by coherence score

        Raises:
            ValueError: If mode is not PORTAL or required config is missing
        """
        from generation.config_schema import TemporalConfig
        from workflows.portal_strategy import PortalStrategy

        if self.mode != TemporalMode.PORTAL:
            raise ValueError(f"run_portal_simulation() requires mode=PORTAL, got {self.mode}")

        # Validate config type
        if not isinstance(config, TemporalConfig):
            raise ValueError(f"config must be TemporalConfig, got {type(config)}")

        # Create and run PortalStrategy
        portal_strategy = PortalStrategy(
            config=config,
            llm_client=self.llm_client,
            store=self.store
        )

        # Execute backward simulation
        paths = portal_strategy.run()

        return paths

    def run_branching_simulation(self, config) -> List:
        """
        Execute BRANCHING mode forward simulation with counterfactual branches.

        This delegates to BranchingStrategy to perform forward exploration from
        a known origin, generating multiple possible futures at decision points.

        Args:
            config: TemporalConfig with mode=BRANCHING and branching settings

        Returns:
            List of BranchingPath objects ranked by coherence score

        Raises:
            ValueError: If mode is not BRANCHING or required config is missing
        """
        from generation.config_schema import TemporalConfig
        from workflows.branching_strategy import BranchingStrategy

        if self.mode != TemporalMode.BRANCHING:
            raise ValueError(f"run_branching_simulation() requires mode=BRANCHING, got {self.mode}")

        # Validate config type
        if not isinstance(config, TemporalConfig):
            raise ValueError(f"config must be TemporalConfig, got {type(config)}")

        # Create and run BranchingStrategy
        branching_strategy = BranchingStrategy(
            config=config,
            llm_client=self.llm_client,
            store=self.store
        )

        # Execute forward simulation with branching
        paths = branching_strategy.run()

        return paths

    def run_directorial_simulation(self, config) -> List:
        """
        Execute DIRECTORIAL mode narrative-driven simulation.

        This delegates to DirectorialStrategy to perform narrative-structured
        forward simulation with five-act dramatic arc, camera/POV systems,
        and tension curves.

        Args:
            config: TemporalConfig with mode=DIRECTORIAL

        Returns:
            List of DirectorialPath objects ranked by coherence score

        Raises:
            ValueError: If mode is not DIRECTORIAL or required config is missing
        """
        from generation.config_schema import TemporalConfig
        from workflows.directorial_strategy import DirectorialStrategy

        if self.mode != TemporalMode.DIRECTORIAL:
            raise ValueError(f"run_directorial_simulation() requires mode=DIRECTORIAL, got {self.mode}")

        if not isinstance(config, TemporalConfig):
            raise ValueError(f"config must be TemporalConfig, got {type(config)}")

        directorial_strategy = DirectorialStrategy(
            config=config,
            llm_client=self.llm_client,
            store=self.store
        )

        paths = directorial_strategy.run()

        return paths

    def run_cyclical_simulation(self, config) -> List:
        """
        Execute CYCLICAL mode temporal simulation with cycles, prophecies, and causal loops.

        This delegates to CyclicalStrategy to perform cyclical forward simulation
        with repeating patterns, escalation, prophecy tracking, and loop closure.

        Args:
            config: TemporalConfig with mode=CYCLICAL

        Returns:
            List of CyclicalPath objects ranked by coherence score

        Raises:
            ValueError: If mode is not CYCLICAL or required config is missing
        """
        from generation.config_schema import TemporalConfig
        from workflows.cyclical_strategy import CyclicalStrategy

        if self.mode != TemporalMode.CYCLICAL:
            raise ValueError(f"run_cyclical_simulation() requires mode=CYCLICAL, got {self.mode}")

        if not isinstance(config, TemporalConfig):
            raise ValueError(f"config must be TemporalConfig, got {type(config)}")

        cyclical_strategy = CyclicalStrategy(
            config=config,
            llm_client=self.llm_client,
            store=self.store
        )

        paths = cyclical_strategy.run()

        return paths
