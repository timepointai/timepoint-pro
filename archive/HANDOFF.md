# HANDOFF: Adaptive Fidelity-Temporal Strategy (M1+M17 Integration)

**Status**: Ready for implementation
**Estimated Effort**: 4-6 hours of focused work
**Breaking Change**: Yes - Database v2 (clean break from v1)

---

## EXECUTIVE SUMMARY

Implement core-driven fidelity-temporal allocation by marrying M1 (Heterogeneous Fidelity Temporal Graphs) with M17 (Modal Temporal Causality). The TemporalAgent core engine will co-determine BOTH temporal progression (when/how much time passes) AND fidelity allocation (how much detail per timepoint), optimizing simulation validity vs token efficiency.

**Key Principle**: "Musical Score" Metaphor
- Templates provide default "score" (fidelity + temporal strategy)
- TemporalAgent acts as "conductor" (adapts score based on simulation needs)
- Users can fully customize (override any part of the score)

---

## WHAT'S ALREADY DONE ✅

### Month-Based Temporal Progression Fix (Portal Mode)
**Files Modified**:
- `workflows/portal_strategy.py` - Lines 47-790
  - Added `month: int` field to PortalState
  - Added `to_year_month_str()`, `to_total_months()`, `from_total_months()` helpers
  - Updated `_explore_reverse_chronological()` to use month-based stepping
  - Updated `_generate_antecedents()` to accept `target_month` parameter
  - Updated `_run_mini_simulation()` to use consistent month-based forward stepping
  - Updated `_generate_forward_state()` to accept `next_month` parameter

**Result**: Portal mode now supports quarter-level granularity (3 months per step) instead of being stuck at same year.

**Validation**:
```bash
python3.10 -c "from workflows.portal_strategy import PortalState; s = PortalState(year=2030, month=6, description='', entities=[], world_state={}); print(s.to_year_month_str())"
# Output: "Jun 2030"
```

---

## WHAT TO DO: 7-PHASE IMPLEMENTATION PLAN

### ARCHITECTURAL CONTEXT

Read these documents first:
1. **MECHANICS.md** - Lines 64-239 (M1: Heterogeneous Fidelity) and 652-1173 (M17: Modal Temporal Causality)
2. **README.md** - For quick start and system overview
3. **PLAN.md** - For development roadmap context

**Core Problem**:
Currently, temporal progression is dictated by config parameters (`backward_steps=22`) creating uniform time intervals, AND fidelity is uniform across all timepoints. This wastes tokens and prevents the engine from allocating detail where needed.

**Solution**:
Let TemporalAgent determine both:
- **Temporal steps**: "How much time should pass?" based on causal necessity, entity development, modal requirements
- **Fidelity levels**: "How much detail needed?" based on pivot points, dramatic tension, simulation state

**User Decisions** (from Q&A):
- Planning modes: User-configurable (programmatic | adaptive | hybrid)
- Portal fidelity: Blended strategy (endpoint+origin=TRAINED, pivots=DIALOG, bridges=SCENE, checkpoints=TENSOR_ONLY)
- Token budget: Template models for all modes (hard | soft | max | adaptive | orchestrator-directed | user-configured)
- Migration: Clean break (archive runs.db → runs_v1_archive.db, new v2 schema)

---

## PHASE 1: Core Engine - Fidelity-Temporal Strategy System

### Task 1.1: Add New Schemas to schemas.py

**Location**: `/Users/seanmcdonald/Documents/GitHub/timepoint-daedalus/schemas.py`

Add after line 24 (after TemporalMode enum):

```python
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
```

**Validation**: After adding, run:
```bash
python3.10 -c "from schemas import FidelityPlanningMode, TokenBudgetMode, FidelityTemporalStrategy; print('✓ Schemas imported successfully')"
```

---

### Task 1.2: Add Strategy Method to TemporalAgent

**Location**: `/Users/seanmcdonald/Documents/GitHub/timepoint-daedalus/workflows/__init__.py`

**Find**: Line 2363 (class TemporalAgent)

**Add** after the `__init__` method (around line 2382):

```python
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
        # 10 TENSOR checkpoints, 3 SCENE bridges, 1 DIALOG endpoint
        fidelity_schedule = [ResolutionLevel.TENSOR_ONLY] * 10 + \
                           [ResolutionLevel.SCENE] * 3 + \
                           [ResolutionLevel.DIALOG]
        # Even temporal distribution
        month_step = total_months // len(fidelity_schedule)
        temporal_steps = [month_step] * len(fidelity_schedule)
        estimated_tokens = 10 * 200 + 3 * 1000 + 1 * 10000  # Rough estimate

    elif template_name == "balanced":
        # 5 TENSOR, 5 SCENE, 3 GRAPH, 2 DIALOG
        fidelity_schedule = [ResolutionLevel.TENSOR_ONLY] * 5 + \
                           [ResolutionLevel.SCENE] * 5 + \
                           [ResolutionLevel.GRAPH] * 3 + \
                           [ResolutionLevel.DIALOG] * 2
        month_step = total_months // len(fidelity_schedule)
        temporal_steps = [month_step] * len(fidelity_schedule)
        estimated_tokens = 5 * 200 + 5 * 1000 + 3 * 5000 + 2 * 10000

    elif template_name == "portal_pivots":
        # Blended: Endpoint + Origin = TRAINED, middle = adaptive
        # For now, use balanced as starting point
        fidelity_schedule = [ResolutionLevel.TRAINED] + \
                           [ResolutionLevel.TENSOR_ONLY] * 8 + \
                           [ResolutionLevel.SCENE] * 4 + \
                           [ResolutionLevel.DIALOG] * 2 + \
                           [ResolutionLevel.TRAINED]
        month_step = total_months // len(fidelity_schedule)
        temporal_steps = [month_step] * len(fidelity_schedule)
        estimated_tokens = 2 * 50000 + 8 * 200 + 4 * 1000 + 2 * 10000

    elif template_name == "max_quality":
        # 10 DIALOG, 5 TRAINED
        fidelity_schedule = [ResolutionLevel.DIALOG] * 10 + \
                           [ResolutionLevel.TRAINED] * 5
        month_step = total_months // len(fidelity_schedule)
        temporal_steps = [month_step] * len(fidelity_schedule)
        estimated_tokens = 10 * 10000 + 5 * 50000

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
    """DIRECTORIAL mode: Allocate fidelity based on narrative arc"""
    from schemas import FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

    # TODO: Implement directorial-specific strategy
    # For now, return basic strategy
    return FidelityTemporalStrategy(
        mode=self.mode,
        planning_mode=FidelityPlanningMode.PROGRAMMATIC,
        budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
        token_budget=15000,
        timepoint_count=15,
        fidelity_schedule=[ResolutionLevel.SCENE] * 15,
        temporal_steps=[24] * 15,  # 2 years between each
        adaptive_threshold=0.7,
        min_resolution=ResolutionLevel.TENSOR_ONLY,
        max_resolution=ResolutionLevel.TRAINED,
        allocation_rationale="DIRECTORIAL mode: TODO - implement narrative arc allocation",
        estimated_tokens=15000,
        estimated_cost_usd=0.03
    )


def _strategy_for_cyclical_mode(self, config, context) -> "FidelityTemporalStrategy":
    """CYCLICAL mode: Allocate based on cycle periods and prophecy fulfillment"""
    from schemas import FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

    # TODO: Implement cyclical-specific strategy
    return FidelityTemporalStrategy(
        mode=self.mode,
        planning_mode=FidelityPlanningMode.PROGRAMMATIC,
        budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
        token_budget=10000,
        timepoint_count=10,
        fidelity_schedule=[ResolutionLevel.SCENE] * 10,
        temporal_steps=[84] * 10,  # 7 days each (weekly cycle)
        adaptive_threshold=0.7,
        min_resolution=ResolutionLevel.TENSOR_ONLY,
        max_resolution=ResolutionLevel.TRAINED,
        allocation_rationale="CYCLICAL mode: TODO - implement cycle-based allocation",
        estimated_tokens=10000,
        estimated_cost_usd=0.02
    )


def _strategy_for_branching_mode(self, config, context) -> "FidelityTemporalStrategy":
    """BRANCHING mode: Allocate based on branch points"""
    from schemas import FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

    # TODO: Implement branching-specific strategy
    return FidelityTemporalStrategy(
        mode=self.mode,
        planning_mode=FidelityPlanningMode.PROGRAMMATIC,
        budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
        token_budget=20000,
        timepoint_count=15,
        fidelity_schedule=[ResolutionLevel.SCENE] * 15,
        temporal_steps=[12] * 15,
        adaptive_threshold=0.7,
        min_resolution=ResolutionLevel.TENSOR_ONLY,
        max_resolution=ResolutionLevel.TRAINED,
        allocation_rationale="BRANCHING mode: TODO - implement branch-based allocation",
        estimated_tokens=20000,
        estimated_cost_usd=0.04
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
```

**Validation**: After adding, run:
```bash
python3.10 -c "
from workflows import TemporalAgent
from schemas import TemporalMode
agent = TemporalAgent(mode=TemporalMode.PORTAL)
print('✓ TemporalAgent methods added successfully')
"
```

---

### Task 1.3: Add Adaptive Step Decision Method

**Location**: Same file (`workflows/__init__.py`), add after the strategy methods:

```python
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
            print(f"  🎯 Pivot detected at step {step_num}: upgrading {planned_resolution} → DIALOG")
            return (planned_month_step, ResolutionLevel.DIALOG)

        # Otherwise, use planned allocation
        return (planned_month_step, planned_resolution)
```

**Validation**: After adding, test import:
```bash
python3.10 -c "
from workflows import TemporalAgent
from schemas import TemporalMode, FidelityTemporalStrategy, FidelityPlanningMode, TokenBudgetMode, ResolutionLevel

agent = TemporalAgent(mode=TemporalMode.PORTAL)

# Create mock strategy
strategy = FidelityTemporalStrategy(
    mode=TemporalMode.PORTAL,
    planning_mode=FidelityPlanningMode.ADAPTIVE,
    budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
    token_budget=15000,
    timepoint_count=15,
    fidelity_schedule=[],
    temporal_steps=[],
    allocation_rationale='Test',
    estimated_tokens=15000,
    estimated_cost_usd=0.03
)

# Test adaptive decision
months, resolution = agent.determine_next_step_fidelity_and_time(
    current_state=None,
    strategy=strategy,
    step_num=0,
    context={'importance_score': 0.8, 'state_complexity': 0.6}
)

print(f'✓ Adaptive decision: {months} months, {resolution}')
"
```

---

## PHASE 2: Portal Strategy Integration

### Task 2.1: Add resolution_level to PortalState

**Location**: `workflows/portal_strategy.py` - Line 47

**Current**:
```python
@dataclass
class PortalState:
    """A state at a specific point in the backward simulation"""
    year: int
    description: str
    entities: List[Entity]
    world_state: Dict[str, Any]
    plausibility_score: float = 0.0
    parent_state: Optional['PortalState'] = None
    children_states: List['PortalState'] = field(default_factory=list)
    month: int = 1
```

**Update to**:
```python
@dataclass
class PortalState:
    """A state at a specific point in the backward simulation"""
    year: int
    description: str
    entities: List[Entity]
    world_state: Dict[str, Any]
    plausibility_score: float = 0.0
    parent_state: Optional['PortalState'] = None
    children_states: List['PortalState'] = field(default_factory=list)
    month: int = 1
    resolution_level: 'ResolutionLevel' = None  # NEW: Fidelity level for this state

    def __post_init__(self):
        """Ensure children_states is a list, month is valid, resolution defaults to SCENE"""
        if self.children_states is None:
            self.children_states = []
        # Validate month
        if not (1 <= self.month <= 12):
            self.month = 1
        # Default resolution to SCENE if not specified
        if self.resolution_level is None:
            from schemas import ResolutionLevel
            self.resolution_level = ResolutionLevel.SCENE
```

---

### Task 2.2: Refactor portal_strategy.py to Query TemporalAgent

**Location**: `workflows/portal_strategy.py` - Line 237 (_explore_reverse_chronological method)

**Replace** the current hardcoded month_step calculation:

```python
# OLD CODE (lines 246-253):
# Calculate in months to support sub-year granularity
portal_month_total = portal.to_total_months()
origin_month_total = self.config.origin_year * 12 + 1  # Assume January for origin

total_months = portal_month_total - origin_month_total
month_step = max(1, total_months // self.config.backward_steps)  # Ensure >= 1 month steps

print(f"  Month-based stepping: {total_months} months / {self.config.backward_steps} steps = {month_step} months/step")
```

**With**:

```python
# NEW CODE - Query TemporalAgent for strategy:
from workflows import TemporalAgent

# Create temporal agent for this simulation
temporal_agent = TemporalAgent(mode=self.config.mode, store=self.store, llm_client=self.llm)

# Get comprehensive fidelity-temporal strategy
strategy = temporal_agent.determine_fidelity_temporal_strategy(
    config=self.config,
    context={
        'portal_state': portal,
        'origin_year': self.config.origin_year,
        'entities': portal.entities
    }
)

print(f"  Fidelity-Temporal Strategy:")
print(f"    Planning mode: {strategy.planning_mode}")
print(f"    Budget mode: {strategy.budget_mode}")
print(f"    Token budget: {strategy.token_budget}")
print(f"    Timepoints: {strategy.timepoint_count}")
print(f"    Estimated tokens: {strategy.estimated_tokens}")
print(f"    Rationale: {strategy.allocation_rationale}")
```

**Then update** the loop to use the strategy:

```python
# OLD LOOP:
for step in range(self.config.backward_steps):
    next_states = []

    # Calculate target month count
    step_month_total = portal_month_total - (step + 1) * month_step
```

**NEW LOOP**:

```python
for step in range(strategy.timepoint_count):
    next_states = []

    # Determine fidelity and temporal step for this iteration
    if strategy.planning_mode in [FidelityPlanningMode.PROGRAMMATIC]:
        # Use pre-planned schedule
        if step < len(strategy.temporal_steps):
            month_step = strategy.temporal_steps[step]
            target_resolution = strategy.fidelity_schedule[step]
        else:
            # Fallback
            month_step = 3
            target_resolution = ResolutionLevel.SCENE
    else:
        # Query agent for adaptive decision
        month_step, target_resolution = temporal_agent.determine_next_step_fidelity_and_time(
            current_state=current_states[0] if current_states else portal,
            strategy=strategy,
            step_num=step,
            context={
                'entities': current_states[0].entities if current_states else portal.entities,
                'importance_score': 0.5,  # TODO: compute from state
                'state_complexity': 0.5,  # TODO: compute from state
                'pivot_detected': False  # TODO: detect pivot points
            }
        )

    # Calculate target month count
    if step == 0:
        portal_month_total = portal.to_total_months()
    step_month_total = portal_month_total - month_step
    portal_month_total = step_month_total  # Update for next iteration
```

**Update** state creation to include resolution:

```python
# When creating antecedent states (around line 274):
antecedents = self._generate_antecedents(
    state,
    target_year=step_year,
    target_month=step_month,
    target_resolution=target_resolution  # NEW PARAMETER
)
```

**Update** _generate_antecedents signature (line 310):

```python
def _generate_antecedents(
    self,
    current_state: PortalState,
    target_year: int = None,
    target_month: int = None,
    target_resolution: ResolutionLevel = None,  # NEW
    count: int = None
) -> List[PortalState]:
```

**Update** PortalState creation in _generate_antecedents (line 413):

```python
state = PortalState(
    year=target_year,
    month=target_month,
    resolution_level=target_resolution or ResolutionLevel.SCENE,  # NEW
    description=data.description,
    entities=current_state.entities.copy(),
    world_state=data.world_context,
    plausibility_score=0.0,
    parent_state=current_state
)
```

---

## PHASE 3: Config Schema - Template Library

### Task 3.1: Add Fidelity-Temporal Fields to TemporalConfig

**Location**: `generation/config_schema.py`

**Find**: TemporalConfig class (search for "class TemporalConfig")

**Add** these new fields after existing fields:

```python
class TemporalConfig(BaseModel):
    # ... existing fields (mode, portal_description, etc.)

    # NEW: Fidelity-Temporal Strategy Configuration
    fidelity_planning_mode: FidelityPlanningMode = FidelityPlanningMode.HYBRID
    token_budget_mode: TokenBudgetMode = TokenBudgetMode.SOFT_GUIDANCE
    token_budget: Optional[float] = 15000  # Default 15k tokens

    # Musical score: fidelity template selection
    fidelity_template: str = "balanced"  # Options: minimalist | balanced | dramatic | max_quality | portal_pivots

    # Advanced: Custom overrides (optional)
    custom_fidelity_schedule: Optional[List[ResolutionLevel]] = None
    custom_temporal_steps: Optional[List[int]] = None

    # ... rest of existing fields
```

**Import** required types at top of file:

```python
from schemas import (
    # ... existing imports
    FidelityPlanningMode,
    TokenBudgetMode,
    ResolutionLevel
)
```

---

### Task 3.2: Add FIDELITY_TEMPLATES Library

**Location**: `generation/config_schema.py` - Add at module level (after imports, before classes)

```python
# Fidelity Template Library - "Musical Scores" for simulation allocation
FIDELITY_TEMPLATES = {
    "minimalist": {
        "description": "Minimal token usage for fast exploration",
        "pattern": [ResolutionLevel.TENSOR_ONLY] * 10 + \
                   [ResolutionLevel.SCENE] * 3 + \
                   [ResolutionLevel.DIALOG],
        "token_estimate": 5000,
        "cost_estimate_usd": 0.01,
        "use_case": "Fast exploration, budget-constrained runs, testing",
        "quality_level": "Basic",
        "recommended_for": ["quick", "testing", "budget_constrained"]
    },

    "balanced": {
        "description": "Good quality/cost ratio for production runs",
        "pattern": [ResolutionLevel.TENSOR_ONLY] * 5 + \
                   [ResolutionLevel.SCENE] * 5 + \
                   [ResolutionLevel.GRAPH] * 3 + \
                   [ResolutionLevel.DIALOG] * 2,
        "token_estimate": 15000,
        "cost_estimate_usd": 0.03,
        "use_case": "Production runs, general purpose, good quality",
        "quality_level": "Good",
        "recommended_for": ["production", "general", "default"]
    },

    "dramatic": {
        "description": "DIRECTORIAL mode focused on narrative climax",
        "pattern": [ResolutionLevel.TENSOR_ONLY] * 8 + \
                   [ResolutionLevel.SCENE] * 4 + \
                   [ResolutionLevel.DIALOG] * 2 + \
                   [ResolutionLevel.TRAINED],
        "token_estimate": 25000,
        "cost_estimate_usd": 0.05,
        "use_case": "DIRECTORIAL mode, narrative-focused simulations",
        "quality_level": "High",
        "recommended_for": ["directorial", "narrative", "story_focused"]
    },

    "max_quality": {
        "description": "Maximum fidelity, no budget constraints",
        "pattern": [ResolutionLevel.DIALOG] * 10 + \
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
```

---

### Task 3.3: Update ALL 64 Templates

**Location**: `generation/config_schema.py` - All template methods

**Strategy**: For each of the 64 templates, add fidelity-temporal configuration.

**Example** - Update `portal_timepoint_unicorn()`:

**Find**:
```python
@staticmethod
def portal_timepoint_unicorn() -> "SimulationConfig":
    return SimulationConfig(
        template_name="portal_timepoint_unicorn",
        # ... existing config
        temporal=TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="...",
            portal_year=2030,
            origin_year=2024,
            backward_steps=22,
            # ... rest
        ),
        # ... rest
    )
```

**Update to**:
```python
@staticmethod
def portal_timepoint_unicorn() -> "SimulationConfig":
    return SimulationConfig(
        template_name="portal_timepoint_unicorn",
        # ... existing config
        temporal=TemporalConfig(
            mode=TemporalMode.PORTAL,
            portal_description="...",
            portal_year=2030,
            origin_year=2024,
            backward_steps=22,

            # NEW: Fidelity-Temporal Strategy
            fidelity_planning_mode=FidelityPlanningMode.HYBRID,
            token_budget_mode=TokenBudgetMode.SOFT_GUIDANCE,
            token_budget=15000,
            fidelity_template="portal_pivots",

            # ... rest
        ),
        # ... rest
    )
```

**Do this for ALL 64 templates**. Use these guidelines:

- **Quick templates** (`*_quick`): `fidelity_template="minimalist"`, `token_budget=5000`
- **Standard templates**: `fidelity_template="balanced"`, `token_budget=15000`
- **Thorough templates** (`*_thorough`): `fidelity_template="dramatic"`, `token_budget=25000`
- **Portal templates**: `fidelity_template="portal_pivots"`
- **DIRECTORIAL templates**: `fidelity_template="dramatic"`
- **Max quality variants**: `fidelity_template="max_quality"`, `token_budget_mode=TokenBudgetMode.MAX_QUALITY`

**Create template variants** for key templates:

```python
@staticmethod
def portal_timepoint_unicorn_minimalist() -> "SimulationConfig":
    config = SimulationConfig.portal_timepoint_unicorn()
    config.temporal.fidelity_template = "minimalist"
    config.temporal.token_budget = 5000
    config.temporal.token_budget_mode = TokenBudgetMode.HARD_CONSTRAINT
    config.template_name = "portal_timepoint_unicorn_minimalist"
    return config

@staticmethod
def portal_timepoint_unicorn_max() -> "SimulationConfig":
    config = SimulationConfig.portal_timepoint_unicorn()
    config.temporal.fidelity_template = "max_quality"
    config.temporal.token_budget_mode = TokenBudgetMode.MAX_QUALITY
    config.template_name = "portal_timepoint_unicorn_max"
    return config
```

---

## PHASE 4: Database Migration - Clean Break

### Task 4.1: Archive Old Database

```bash
cd /Users/seanmcdonald/Documents/GitHub/timepoint-daedalus
mv metadata/runs.db metadata/runs_v1_archive.db
echo "✓ Old database archived to runs_v1_archive.db"
```

### Task 4.2: Update Run Schema

**Location**: `schemas.py` - Find the Run class (search for "class Run")

**Add** new fields:

```python
class Run(SQLModel, table=True):
    # ... existing fields

    # NEW: Schema version tracking
    schema_version: int = 2  # Version 2 = fidelity-temporal aware

    # NEW: Fidelity-Temporal Metadata
    fidelity_strategy_json: Optional[str] = None  # Serialized FidelityTemporalStrategy
    fidelity_distribution: Optional[str] = None  # e.g., "TENSOR:10,SCENE:5,GRAPH:3,DIALOG:2"
    actual_tokens_used: Optional[float] = None
    token_budget_compliance: Optional[float] = None  # actual/budget ratio
    fidelity_efficiency_score: Optional[float] = None  # validity_score/tokens metric

    # ... rest of existing fields
```

---

## PHASE 5: Test Rig Updates

### Task 5.1: Add Fidelity Metrics to Test Runner

**Location**: `run_all_mechanism_tests.py`

**Add** fidelity tracking function:

```python
def track_fidelity_metrics(result) -> Dict:
    """Track fidelity distribution and efficiency for a run"""

    # Parse fidelity distribution from result
    fidelity_dist = {}
    if hasattr(result, 'fidelity_distribution') and result.fidelity_distribution:
        # Parse "TENSOR:10,SCENE:5,GRAPH:3,DIALOG:2"
        for pair in result.fidelity_distribution.split(','):
            level, count = pair.split(':')
            fidelity_dist[level] = int(count)

    # Calculate metrics
    total_timepoints = sum(fidelity_dist.values()) if fidelity_dist else 0
    actual_tokens = getattr(result, 'actual_tokens_used', 0)
    token_budget = getattr(result, 'token_budget', 0)

    return {
        'fidelity_distribution': fidelity_dist,
        'total_timepoints': total_timepoints,
        'token_efficiency': result.cost_usd / actual_tokens if actual_tokens > 0 else 0,
        'budget_compliance': actual_tokens / token_budget if token_budget > 0 else 0,
        'avg_fidelity_level': _calculate_avg_fidelity(fidelity_dist)
    }

def _calculate_avg_fidelity(fidelity_dist: Dict) -> float:
    """Calculate average fidelity level (0-4 scale)"""
    from schemas import ResolutionLevel

    level_values = {
        'TENSOR_ONLY': 0,
        'SCENE': 1,
        'GRAPH': 2,
        'DIALOG': 3,
        'TRAINED': 4
    }

    total_weighted = sum(level_values.get(level, 0) * count
                        for level, count in fidelity_dist.items())
    total_count = sum(fidelity_dist.values())

    return total_weighted / total_count if total_count > 0 else 0
```

**Add** new test mode:

```python
# Add to list_modes() function:
print("\n" + "="*80)
print("📊 FIDELITY COMPARISON MODES")
print("="*80)
print("  --compare-fidelity TEMPLATE_NAME")
print("    Compare all fidelity variants of a template")
print("    Example: --compare-fidelity portal_timepoint_unicorn")
print("    Runs: minimalist, balanced (default), max_quality")
print()
print("  --fidelity-minimalist")
print("    Run all templates with minimalist fidelity")
print()
print("  --fidelity-balanced")
print("    Run all templates with balanced fidelity")
print("="*80)
```

---

## PHASE 6: Orchestrator & Monitor Updates

### Task 6.1: Update Orchestrator

**Location**: `orchestrator.py`

**Find**: Main simulation loop

**Add** fidelity-aware generation:

```python
# When generating timepoints, respect fidelity level from strategy
def generate_timepoint_at_resolution(
    resolution: ResolutionLevel,
    entities: List[Entity],
    llm: LLMClient,
    context: Dict
) -> Timepoint:
    """Generate timepoint with specified resolution/fidelity"""

    if resolution == ResolutionLevel.TENSOR_ONLY:
        # Minimal: only tensor state, no dialog
        return generate_tensor_only_timepoint(entities, context)

    elif resolution == ResolutionLevel.SCENE:
        # Medium: scene description, basic interactions
        return generate_scene_timepoint(entities, llm, context)

    elif resolution == ResolutionLevel.GRAPH:
        # High: full graph relationships
        return generate_graph_timepoint(entities, llm, context)

    elif resolution == ResolutionLevel.DIALOG:
        # Very high: full dialog generation
        return generate_dialog_timepoint(entities, llm, context)

    else:  # TRAINED
        # Maximum: full training passes
        return generate_trained_timepoint(entities, llm, context)
```

---

### Task 6.2: Update Monitor

**Location**: `monitoring/monitor.py` (or wherever monitoring happens)

**Add** fidelity display to real-time output:

```python
# In monitor update loop:
print(f"[{template_name}] Step {current_step}/{total_steps}")
print(f"  Fidelity: {current_resolution} ({estimated_tokens} tokens)")
print(f"  Budget: {tokens_used}/{token_budget} ({compliance_pct:.0f}%)")
print(f"  Efficiency: {efficiency:.2f} validity/token")
if next_resolution != current_resolution:
    print(f"  Next step: {next_resolution} ({'pivot detected' if pivot else 'planned'})")
```

---

## PHASE 7: Documentation

### Task 7.1: Update MECHANICS.md

**Location**: `MECHANICS.md`

**Add** new section after M17 (around line 1173):

```markdown
### M1+M17 Integration: Adaptive Fidelity-Temporal Strategy ✅

**Status:** Implemented (Phase 14)

**Architecture**: Core-driven fidelity-temporal co-allocation

The TemporalAgent core engine co-determines BOTH temporal progression (when/how much time) AND fidelity allocation (how much detail per timepoint), optimizing simulation validity vs token efficiency.

**Musical Score Metaphor**:
- **Score (Template)**: Default fidelity+temporal strategy
- **Conductor (TemporalAgent)**: Interprets score based on simulation needs
- **Customization**: Full user control to override score

**Planning Modes**:
- `PROGRAMMATIC`: Pre-planned fidelity schedule (deterministic, predictable cost)
- `ADAPTIVE`: Per-step decisions based on simulation state (responsive, variable cost)
- `HYBRID`: Programmatic plan + adaptive upgrades for critical moments

**Token Budget Modes**:
- `HARD_CONSTRAINT`: Fail if budget exceeded
- `SOFT_GUIDANCE`: Target budget, allow 110% overage
- `MAX_QUALITY`: No budget limit
- `ADAPTIVE_FALLBACK`: Hit budget, exceed if validity requires
- `ORCHESTRATOR_DIRECTED`: Orchestrator decides
- `USER_CONFIGURED`: User provides exact allocation

**Fidelity Templates**:
- `minimalist`: 5k tokens, fast exploration
- `balanced`: 15k tokens, production default
- `dramatic`: 25k tokens, narrative focus
- `max_quality`: 350k tokens, research/publication
- `portal_pivots`: 20k tokens, adaptive pivot detection

See implementation in:
- Core: workflows/__init__.py:2382+ (TemporalAgent)
- Integration: workflows/portal_strategy.py:237+ (PortalStrategy)
- Config: generation/config_schema.py (FIDELITY_TEMPLATES)
```

---

### Task 7.2: Create MIGRATION.md

**Location**: `MIGRATION.md` (new file)

```markdown
# Migration Guide: Database v1 → v2

**Date**: 2025-11-02
**Breaking Change**: Yes

---

## What Changed

### Schema v2: Fidelity-Temporal Awareness

Database schema upgraded from v1 (uniform fidelity) to v2 (adaptive fidelity-temporal allocation).

**New Capabilities**:
- Core engine determines temporal progression (not config params)
- Fidelity varies per timepoint (TENSOR → SCENE → DIALOG → TRAINED)
- Token budget optimization
- Musical score metaphor for customization

---

## Migration Strategy: Clean Break

**Approach**: Archive old database, start fresh with v2 schema.

**Why Clean Break?**
- Fidelity metadata cannot be retroactively inferred for old runs
- Schema changes are fundamental (new fields required)
- Allows side-by-side comparison (v1 archive vs v2 new runs)

---

## Migration Steps

### 1. Archive Old Database

```bash
cd /path/to/timepoint-daedalus
mv metadata/runs.db metadata/runs_v1_archive.db
```

**Result**: Old runs preserved in `runs_v1_archive.db`

### 2. System Will Auto-Create v2 Database

On first run after migration, system creates new `metadata/runs.db` with v2 schema.

### 3. Update Templates (Already Done in Code)

All 64 templates now include fidelity-temporal configuration.

---

## New Features in v2

### Fidelity Planning Modes

```python
config.temporal.fidelity_planning_mode = FidelityPlanningMode.HYBRID
```

Options: `PROGRAMMATIC` | `ADAPTIVE` | `HYBRID`

### Token Budget Modes

```python
config.temporal.token_budget_mode = TokenBudgetMode.SOFT_GUIDANCE
config.temporal.token_budget = 15000
```

Options: `HARD_CONSTRAINT` | `SOFT_GUIDANCE` | `MAX_QUALITY` | `ADAPTIVE_FALLBACK` | `ORCHESTRATOR_DIRECTED` | `USER_CONFIGURED`

### Fidelity Templates

```python
config.temporal.fidelity_template = "balanced"
```

Options: `minimalist` | `balanced` | `dramatic` | `max_quality` | `portal_pivots`

### Template Variants

```python
# Quick (5k tokens, hard budget)
config = SimulationConfig.portal_timepoint_unicorn_minimalist()

# Standard (15k tokens, soft budget)
config = SimulationConfig.portal_timepoint_unicorn()

# Max (no budget limit)
config = SimulationConfig.portal_timepoint_unicorn_max()
```

---

## Accessing Old Data

### Option 1: Query v1 Archive Directly

```python
from sqlmodel import Session, create_engine

engine = create_engine("sqlite:///metadata/runs_v1_archive.db")
with Session(engine) as session:
    old_runs = session.query(Run).all()
```

### Option 2: Use Dashboard Filtering

Dashboard will auto-detect schema version and filter accordingly.

---

## Rollback (If Needed)

```bash
# Restore v1 database
mv metadata/runs.db metadata/runs_v2_experimental.db
mv metadata/runs_v1_archive.db metadata/runs.db

# Revert code to commit before migration
git checkout <commit_before_migration>
```

---

## Support

Questions? See:
- MECHANICS.md - Lines 64-239 (M1), 652-1173 (M17)
- HANDOFF.md - Full implementation plan
- README.md - Quick start guide
```

---

## IMPLEMENTATION CHECKLIST

Use this to track progress:

### Phase 1: Core Engine ✓ or ✗
- [ ] 1.1: Add FidelityPlanningMode, TokenBudgetMode, FidelityTemporalStrategy to schemas.py
- [ ] 1.2: Add determine_fidelity_temporal_strategy() to TemporalAgent
- [ ] 1.3: Add determine_next_step_fidelity_and_time() for adaptive mode

### Phase 2: Portal Integration ✓ or ✗
- [ ] 2.1: Add resolution_level to PortalState
- [ ] 2.2: Refactor portal_strategy.py to query TemporalAgent

### Phase 3: Config & Templates ✓ or ✗
- [ ] 3.1: Add fidelity-temporal fields to TemporalConfig
- [ ] 3.2: Add FIDELITY_TEMPLATES library
- [ ] 3.3: Update all 64 templates with fidelity strategies
- [ ] 3.3a: Create template variants (_minimalist, _max for key templates)

### Phase 4: Database ✓ or ✗
- [ ] 4.1: Archive runs.db → runs_v1_archive.db
- [ ] 4.2: Update Run schema with v2 fields

### Phase 5: Test Rig ✓ or ✗
- [ ] 5.1: Add fidelity metrics tracking
- [ ] 5.2: Add --compare-fidelity and --fidelity-* test modes

### Phase 6: Orchestrator & Monitor ✓ or ✗
- [ ] 6.1: Add generate_timepoint_at_resolution() to orchestrator
- [ ] 6.2: Update monitor to show fidelity distribution

### Phase 7: Documentation ✓ or ✗
- [ ] 7.1: Update MECHANICS.md with M1+M17 integration section
- [ ] 7.2: Create MIGRATION.md

---

## VALIDATION COMMANDS

After each phase, run these to validate:

```bash
# Phase 1 validation
python3.10 -c "from schemas import FidelityPlanningMode, TokenBudgetMode, FidelityTemporalStrategy; from workflows import TemporalAgent; print('✓ Phase 1 complete')"

# Phase 2 validation
python3.10 -c "from workflows.portal_strategy import PortalState; from schemas import ResolutionLevel; s = PortalState(year=2030, month=6, resolution_level=ResolutionLevel.DIALOG, description='', entities=[], world_state={}); print(f'✓ Phase 2 complete: {s.resolution_level}')"

# Phase 3 validation
python3.10 -c "from generation.config_schema import SimulationConfig, FIDELITY_TEMPLATES; config = SimulationConfig.portal_timepoint_unicorn(); print(f'✓ Phase 3 complete: {config.temporal.fidelity_template}, budget={config.temporal.token_budget}')"

# Phase 4 validation
python3.10 -c "from schemas import Run; r = Run(run_id='test', template_name='test', status='complete', schema_version=2, fidelity_distribution='TENSOR:5,SCENE:3'); print(f'✓ Phase 4 complete: schema_version={r.schema_version}')"

# Phase 5 validation
python3.10 run_all_mechanism_tests.py --list-modes | grep "FIDELITY COMPARISON"

# Full system validation
python3.10 -c "
from generation.config_schema import SimulationConfig
from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from metadata.run_tracker import MetadataManager

config = SimulationConfig.portal_timepoint_unicorn()
print(f'Template: {config.template_name}')
print(f'Fidelity planning: {config.temporal.fidelity_planning_mode}')
print(f'Token budget: {config.temporal.token_budget}')
print(f'Budget mode: {config.temporal.token_budget_mode}')
print(f'Fidelity template: {config.temporal.fidelity_template}')
print('✓ Full validation complete')
"
```

---

## EXPECTED OUTCOMES

### Token Efficiency Gains
- **Minimalist**: 95% reduction (full → minimal for checkpoints)
- **Balanced**: 85% reduction (best validity/cost)
- **Dramatic**: 70% reduction (quality-focused)
- **Max Quality**: 0% reduction (maximize fidelity)

### Validity Improvements
- Adaptive: Engine allocates detail where needed
- Hybrid: Planned baseline + responsive upgrades
- Portal: Pivots get DIALOG, bridges get SCENE

### User Experience
- Template library: Easy starting points
- Customization: Full control via musical score
- Budget modes: 6 options covering all use cases
- Clean separation: Core decides, templates suggest

---

## FILES TO MODIFY

1. **schemas.py** - Add FidelityPlanningMode, TokenBudgetMode, FidelityTemporalStrategy, update Run schema
2. **workflows/__init__.py** - Add TemporalAgent strategy methods (lines 2382+)
3. **workflows/portal_strategy.py** - Update PortalState, refactor _explore_reverse_chronological
4. **generation/config_schema.py** - Add FIDELITY_TEMPLATES, update TemporalConfig, update all 64 templates
5. **run_all_mechanism_tests.py** - Add fidelity metrics tracking, new test modes
6. **orchestrator.py** - Add fidelity-aware generation
7. **monitoring/monitor.py** - Add fidelity display
8. **MECHANICS.md** - Add M1+M17 integration documentation
9. **MIGRATION.md** - Create migration guide (new file)

---

## CRITICAL SUCCESS CRITERIA

✅ TemporalAgent determines temporal progression (not config params)
✅ Fidelity varies per timepoint based on simulation needs
✅ Token budget optimization works (hard/soft/max/adaptive modes)
✅ Templates provide starting points, users can customize
✅ Database v2 tracks fidelity metadata
✅ Test rig shows fidelity distribution
✅ Documentation explains migration

---

**Ready to execute. Start with Phase 1, Task 1.1.**
