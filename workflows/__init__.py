# ============================================================================
# workflows/__init__.py - Workflow Module Exports
# ============================================================================
"""
LangGraph workflow definitions and temporal mechanisms.

This module re-exports all workflow components from their submodules.
See ARCHITECTURE-PLAN.md for the modular structure.

Submodules:
- entity_training: LangGraph workflow for entity training (M2)
- scene_environment: Scene-level entity aggregation (M10)
- dialog_synthesis: Dialog synthesis with body-mind coupling (M8, M11)
- relationship_analysis: Multi-entity synthesis (M13)
- prospection: Entity prospection (M15)
- counterfactual: Counterfactual branching (M12)
- animistic: Animistic entity extension (M16)
- temporal_agent: Modal temporal causality (M7, M17)
- portal_strategy: PORTAL mode backward simulation
"""

# Entity Training (M2)
# Animistic (M16)
from workflows.animistic import (
    create_animistic_entity,
    generate_animistic_entities_for_scene,
    infer_species_from_context,
    should_create_animistic_entity,
)

# Branching Strategy (M12)
from workflows.branching_strategy import (
    BranchingStrategy,
)

# Counterfactual (M12)
from workflows.counterfactual import (
    apply_intervention_to_timepoint,
    compare_timelines,
    create_counterfactual_branch,
    find_first_divergence,
    generate_causal_explanation,
    propagate_causality_from_branch,
)

# Cyclical Strategy (M17 - Cycles and prophecy)
from workflows.cyclical_strategy import (
    CyclicalStrategy,
)

# Dialog Synthesis (M8, M11)
from workflows.dialog_synthesis import (
    compute_age_constraints,
    compute_relationship_metrics,
    couple_illness_to_cognition,
    couple_pain_to_cognition,
    create_exposure_event,
    extract_knowledge_references,
    get_recent_exposure_events,
    get_timepoint_position,
    synthesize_dialog,
)

# Directorial Strategy (M17 - Narrative-driven)
from workflows.directorial_strategy import (
    DirectorialStrategy,
)
from workflows.entity_training import (
    WorkflowState,
    create_entity_training_workflow,
    retrain_high_traffic_entities,
)

# Portal Strategy
from workflows.portal_strategy import (
    PortalStrategy,
)

# Prospection (M15)
from workflows.prospection import (
    compute_anxiety_from_expectations,
    estimate_energy_cost_for_preparation,
    generate_prospective_state,
    get_relevant_history_for_prospection,
    influence_behavior_from_expectations,
    update_forecast_accuracy,
)

# Relationship Analysis (M13)
from workflows.relationship_analysis import (
    analyze_relationship_evolution,
    detect_contradictions,
    get_belief_on_topic,
    get_relationship_events,
    infer_historical_role,
    synthesize_multi_entity_response,
)

# Scene Environment (M10)
from workflows.scene_environment import (
    classify_emotional_state,
    compute_crowd_dynamics,
    compute_scene_atmosphere,
    compute_tension_from_relationships,
    create_environment_entity,
    infer_formality_from_location,
    infer_location_properties,
    infer_movement_pattern,
)

# Temporal Agent (M7, M17)
from workflows.temporal_agent import (
    TemporalAgent,
)

# __all__ for explicit exports
__all__ = [
    # Entity Training
    "WorkflowState",
    "create_entity_training_workflow",
    "retrain_high_traffic_entities",
    # Scene Environment
    "create_environment_entity",
    "compute_scene_atmosphere",
    "compute_crowd_dynamics",
    "compute_tension_from_relationships",
    "infer_formality_from_location",
    "infer_location_properties",
    "classify_emotional_state",
    "infer_movement_pattern",
    # Dialog Synthesis
    "couple_pain_to_cognition",
    "couple_illness_to_cognition",
    "compute_age_constraints",
    "get_recent_exposure_events",
    "compute_relationship_metrics",
    "get_timepoint_position",
    "extract_knowledge_references",
    "create_exposure_event",
    "synthesize_dialog",
    # Relationship Analysis
    "analyze_relationship_evolution",
    "detect_contradictions",
    "synthesize_multi_entity_response",
    "get_relationship_events",
    "get_belief_on_topic",
    "infer_historical_role",
    # Prospection
    "compute_anxiety_from_expectations",
    "estimate_energy_cost_for_preparation",
    "generate_prospective_state",
    "influence_behavior_from_expectations",
    "update_forecast_accuracy",
    "get_relevant_history_for_prospection",
    # Counterfactual
    "create_counterfactual_branch",
    "apply_intervention_to_timepoint",
    "propagate_causality_from_branch",
    "compare_timelines",
    "generate_causal_explanation",
    "find_first_divergence",
    # Animistic
    "should_create_animistic_entity",
    "infer_species_from_context",
    "create_animistic_entity",
    "generate_animistic_entities_for_scene",
    # Temporal Agent
    "TemporalAgent",
    # Portal Strategy
    "PortalStrategy",
    # Branching Strategy
    "BranchingStrategy",
    # Directorial Strategy
    "DirectorialStrategy",
    # Cyclical Strategy
    "CyclicalStrategy",
]
