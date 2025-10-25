"""
Tensor Initialization from Prospection (M15 → TTM Pipeline)
===========================================================

Converts prospective states (M15: Entity Prospection) into TTM tensor initialization.
This provides "seed tensors" for entities before ANDOS training begins.

Architectural Insight:
- Prospection is not just a mechanism - it's the tensor initialization step
- ProspectiveState expectations → context_vector (anticipated events, plans)
- Anxiety level → biology_vector (stress, arousal, cognitive load)
- Contingency plans → behavior_vector (action patterns, preparation)

This solves the circular dependency:
- BEFORE: Entities created with NO tensors → ANDOS fails → Dialog skips entities
- AFTER: Prospection generates tensors → ANDOS orders data → Dialog synthesis succeeds
"""

import numpy as np
from typing import List, Dict, Any
from schemas import TTMTensor, ProspectiveState, Entity, Timepoint, Expectation


def initialize_tensor_from_prospection(
    entity: Entity,
    prospective_state: ProspectiveState,
    timepoint: Timepoint
) -> TTMTensor:
    """
    Convert prospective state into TTM tensor initialization.

    This is the FOUNDATION of entity training. Prospection provides initial
    tensor data that ANDOS and subsequent training builds upon.

    Args:
        entity: Entity to initialize
        prospective_state: ProspectiveState with expectations and plans
        timepoint: Current timepoint

    Returns:
        TTMTensor with context, biology, and behavior vectors initialized

    Vector Dimensions:
    - context_vector: 8 dims (expectations, plans, forecasts)
    - biology_vector: 4 dims (anxiety, stress, cognitive capacity)
    - behavior_vector: 8 dims (preparation, actions, risk assessment)
    """
    # Parse expectations from JSON if needed
    expectations = _parse_expectations(prospective_state)
    contingency_plans = _parse_contingency_plans(prospective_state)

    # Context vector from expectations (8 dimensions)
    # Represents anticipated future states and planning horizon
    context_vector = _compute_context_vector(
        expectations,
        prospective_state,
        contingency_plans
    )

    # Biology vector from anxiety and cognitive load (4 dimensions)
    # Represents physical/cognitive state driven by future anticipation
    biology_vector = _compute_biology_vector(
        prospective_state,
        expectations
    )

    # Behavior vector from preparation actions (8 dimensions)
    # Represents action patterns and decision strategies
    behavior_vector = _compute_behavior_vector(
        expectations,
        contingency_plans,
        prospective_state
    )

    # Create TTM tensor
    tensor = TTMTensor.from_arrays(context_vector, biology_vector, behavior_vector)

    return tensor


def _parse_expectations(prospective_state: ProspectiveState) -> List[Expectation]:
    """Parse expectations from ProspectiveState (handles JSON serialization)"""
    import json

    expectations_data = prospective_state.expectations

    # If already list of Expectation objects, return
    if expectations_data and isinstance(expectations_data, list):
        if expectations_data and isinstance(expectations_data[0], Expectation):
            return expectations_data

    # If JSON string, parse
    if isinstance(expectations_data, str):
        try:
            expectations_data = json.loads(expectations_data)
        except:
            return []

    # Convert dicts to Expectation objects
    if isinstance(expectations_data, list):
        expectations = []
        for exp_data in expectations_data:
            if isinstance(exp_data, dict):
                try:
                    expectations.append(Expectation(**exp_data))
                except:
                    pass  # Skip invalid expectations
            elif isinstance(exp_data, Expectation):
                expectations.append(exp_data)
        return expectations

    return []


def _parse_contingency_plans(prospective_state: ProspectiveState) -> Dict[str, List[str]]:
    """Parse contingency plans from ProspectiveState"""
    import json

    plans_data = prospective_state.contingency_plans

    # If already dict, return
    if isinstance(plans_data, dict):
        return plans_data

    # If JSON string, parse
    if isinstance(plans_data, str):
        try:
            return json.loads(plans_data)
        except:
            return {}

    return {}


def _compute_context_vector(
    expectations: List[Expectation],
    prospective_state: ProspectiveState,
    contingency_plans: Dict[str, List[str]]
) -> np.ndarray:
    """
    Compute 8-dimensional context vector from prospection.

    Dimensions:
    0. Expectation count (normalized 0-1, cap at 10)
    1. Average subjective probability
    2. Proportion of desired outcomes
    3. Anxiety level
    4. Forecast confidence
    5. Forecast horizon (normalized years)
    6. Contingency plan count (normalized 0-1, cap at 10)
    7. Average expectation confidence
    """
    n_expectations = len(expectations)

    if n_expectations == 0:
        # No expectations - return neutral baseline
        return np.array([0.0, 0.5, 0.5, 0.3, 0.5, 0.08, 0.0, 0.5])

    context = np.zeros(8)

    # Dim 0: Expectation count (normalized)
    context[0] = min(n_expectations / 10.0, 1.0)

    # Dim 1: Average subjective probability
    context[1] = sum(e.subjective_probability for e in expectations) / n_expectations

    # Dim 2: Proportion of desired outcomes
    context[2] = sum(1 for e in expectations if e.desired_outcome) / n_expectations

    # Dim 3: Anxiety level (from prospective state)
    context[3] = prospective_state.anxiety_level

    # Dim 4: Forecast confidence
    context[4] = prospective_state.forecast_confidence

    # Dim 5: Forecast horizon (normalized to years)
    context[5] = prospective_state.forecast_horizon_days / 365.0

    # Dim 6: Contingency plan count (normalized)
    context[6] = min(len(contingency_plans) / 10.0, 1.0)

    # Dim 7: Average expectation confidence
    context[7] = sum(e.confidence for e in expectations) / n_expectations

    return context


def _compute_biology_vector(
    prospective_state: ProspectiveState,
    expectations: List[Expectation]
) -> np.ndarray:
    """
    Compute 4-dimensional biology vector from prospection.

    Dimensions:
    0. Stress level (from anxiety)
    1. Calm level (inverse of anxiety)
    2. Health baseline (neutral)
    3. Cognitive capacity (from forecast confidence)
    """
    biology = np.zeros(4)

    # Dim 0: Stress level (anxiety)
    biology[0] = prospective_state.anxiety_level

    # Dim 1: Calm level (inverse)
    biology[1] = 1.0 - prospective_state.anxiety_level

    # Dim 2: Health baseline (neutral - no physical data from prospection)
    biology[2] = 0.5

    # Dim 3: Cognitive capacity (forecast confidence as proxy)
    biology[3] = prospective_state.forecast_confidence

    return biology


def _compute_behavior_vector(
    expectations: List[Expectation],
    contingency_plans: Dict[str, List[str]],
    prospective_state: ProspectiveState
) -> np.ndarray:
    """
    Compute 8-dimensional behavior vector from prospection.

    Dimensions:
    0. Activity level (total preparation actions)
    1. Preparation ratio (expectations with actions)
    2. Risk assessment (anxiety as proxy)
    3. Confidence level (inverse anxiety)
    4. Response diversity (unique action types)
    5. Planning horizon (average time horizon)
    6. Social engagement baseline
    7. Decision confidence baseline
    """
    behavior = np.zeros(8)

    # Collect all preparation actions
    all_actions = []
    for exp in expectations:
        if hasattr(exp, 'preparation_actions') and exp.preparation_actions:
            all_actions.extend(exp.preparation_actions)

    n_expectations = max(len(expectations), 1)  # Avoid division by zero

    # Dim 0: Activity level (total actions, normalized)
    behavior[0] = min(len(all_actions) / 20.0, 1.0)

    # Dim 1: Preparation ratio
    if expectations:
        behavior[1] = sum(1 for e in expectations if hasattr(e, 'preparation_actions') and len(e.preparation_actions) > 0) / n_expectations
    else:
        behavior[1] = 0.0

    # Dim 2: Risk assessment (anxiety as proxy)
    behavior[2] = prospective_state.anxiety_level

    # Dim 3: Confidence level (inverse anxiety)
    behavior[3] = 1.0 - prospective_state.anxiety_level

    # Dim 4: Response diversity (unique actions)
    behavior[4] = min(len(set(all_actions)) / 15.0, 1.0) if all_actions else 0.0

    # Dim 5: Planning horizon (average time horizon, normalized)
    if expectations:
        avg_horizon = sum(getattr(e, 'time_horizon_days', 30) for e in expectations) / n_expectations
        behavior[5] = min(avg_horizon / 365.0, 1.0)
    else:
        behavior[5] = 0.08  # ~30 days default

    # Dim 6: Social engagement baseline (neutral)
    behavior[6] = 0.5

    # Dim 7: Decision confidence baseline
    behavior[7] = prospective_state.forecast_confidence

    return behavior


def create_fallback_tensor() -> TTMTensor:
    """
    Create minimal fallback tensor when prospection fails.

    Returns tensor with small random values to avoid NaN/inf issues.
    Used as last resort when prospection generation fails.
    """
    # Small random values around 0.1 to provide minimal variation
    context = np.random.rand(8) * 0.1
    biology = np.random.rand(4) * 0.1 + 0.5  # Centered around 0.5
    behavior = np.random.rand(8) * 0.1 + 0.5  # Centered around 0.5

    return TTMTensor.from_arrays(context, biology, behavior)


def validate_tensor_initialization(tensor: TTMTensor) -> tuple[bool, str]:
    """
    Validate that tensor was properly initialized.

    Checks:
    - No NaN or inf values
    - Vectors have correct dimensions
    - Values in reasonable range [0, 1]

    Returns:
        (valid, error_message) tuple
    """
    try:
        context, biology, behavior = tensor.to_arrays()

        # Check dimensions
        if context.shape != (8,):
            return False, f"Context vector wrong shape: {context.shape}, expected (8,)"
        if biology.shape != (4,):
            return False, f"Biology vector wrong shape: {biology.shape}, expected (4,)"
        if behavior.shape != (8,):
            return False, f"Behavior vector wrong shape: {behavior.shape}, expected (8,)"

        # Check for NaN/inf
        for name, vec in [("context", context), ("biology", biology), ("behavior", behavior)]:
            if np.any(np.isnan(vec)):
                return False, f"{name} vector contains NaN"
            if np.any(np.isinf(vec)):
                return False, f"{name} vector contains inf"

        # Check value range (warning only, not failure)
        for name, vec in [("context", context), ("biology", biology), ("behavior", behavior)]:
            if np.any(vec < 0) or np.any(vec > 2.0):
                # Allow some values slightly outside [0,1] but warn
                print(f"⚠️  {name} vector has values outside [0,1]: min={vec.min():.2f}, max={vec.max():.2f}")

        return True, ""

    except Exception as e:
        return False, f"Tensor validation failed: {str(e)}"
