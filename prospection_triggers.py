"""
Prospection Triggering System (M15 - Phase 11 Architecture Pivot)
==================================================================

This module handles OPTIONAL triggering of prospection (M15) based on:
1. Template configuration (metadata prospection_config)
2. Character personality traits (prospection_ability, theory_of_mind)
3. LLM decisions during training
4. Query-driven invocation (user asks about expectations)

Key architectural principle:
- OLD: Prospection was MANDATORY for all entities (mechanism theater)
- NEW: Prospection is OPTIONAL, triggered contextually based on configuration
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any
from schemas import Entity, Timepoint, ProspectiveState
from storage import GraphStore


def should_trigger_prospection(
    entity: Entity,
    timepoint: Timepoint,
    config: Dict[str, Any]
) -> bool:
    """
    Determine if prospection should be triggered for this entity.

    Triggering conditions (ANY of these triggers prospection):
    1. Template-level: Entity listed in prospection_config
    2. Character-level: Entity has high prospection_ability trait
    3. Role-level: Entity role requires forward planning (detective, leader, strategist)
    4. Event-level: Critical decision point or high-stakes scenario
    5. Personality-level: High conscientiousness or high neuroticism

    Args:
        entity: Entity to evaluate
        timepoint: Current timepoint context
        config: Simulation configuration with prospection_config (dict or SimulationConfig)

    Returns:
        True if prospection should be triggered
    """
    # Check 1: Template-level configuration
    # Handle both dict and SimulationConfig object
    if hasattr(config, 'metadata'):
        # SimulationConfig object
        metadata = config.metadata if config.metadata else {}
        prospection_config = metadata.get("prospection_config", {}) if isinstance(metadata, dict) else {}
    else:
        # Dict
        prospection_config = config.get("metadata", {}).get("prospection_config", {})

    # Explicit entity list
    modeling_entity = prospection_config.get("modeling_entity")
    target_entity = prospection_config.get("target_entity")

    if modeling_entity and entity.entity_id == modeling_entity:
        return True

    # Check for entity in explicit list
    enabled_entities = prospection_config.get("enabled_entities", [])
    if entity.entity_id in enabled_entities:
        return True

    # Check 2: Character-level prospection ability
    prospection_ability = entity.entity_metadata.get("cognitive_traits", {}).get("prospection_ability", 0.0)
    if prospection_ability > 0.7:  # High prospection ability
        return True

    # Check 3: Role-based triggering
    role = entity.entity_metadata.get("role", "").lower()
    planning_roles = ["detective", "strategist", "leader", "commander", "mastermind", "planner"]
    if any(planning_role in role for planning_role in planning_roles):
        return True

    # Check 4: Event-level triggers
    event_description = timepoint.event_description.lower()
    high_stakes_keywords = ["confrontation", "decision", "critical", "crisis", "planning", "strategy"]
    if any(keyword in event_description for keyword in high_stakes_keywords):
        # Only trigger for entities with some planning capability
        if prospection_ability > 0.3:
            return True

    # Check 5: Personality-driven prospection
    personality_traits = entity.entity_metadata.get("personality_traits", [])
    if len(personality_traits) >= 5:
        # Big Five: Conscientiousness (index 2) and Neuroticism (index 3)
        conscientiousness = personality_traits[2] if len(personality_traits) > 2 else 0.5
        neuroticism = personality_traits[3] if len(personality_traits) > 3 else 0.5

        # High conscientiousness → forward planning
        if conscientiousness > 0.75:
            return True

        # High neuroticism → anxiety-driven prospection
        if neuroticism > 0.75:
            return True

    # Check 6: Metadata flag (LLM or manual override)
    if entity.entity_metadata.get("needs_prospection", False):
        return True

    # Default: no prospection
    return False


def get_prospection_params(
    entity: Entity,
    timepoint: Timepoint,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get prospection parameters for this entity.

    Returns:
        Dictionary with:
        - time_horizons: List of time horizons to model (e.g., ["6h", "12h", "24h"])
        - prospection_ability: 0.0-1.0 modeling capability
        - theory_of_mind: 0.0-1.0 ability to model other entities
        - anxiety_baseline: 0.0-1.0 default anxiety level
        - forecast_confidence: 0.0-1.0 confidence in predictions
    """
    # Handle both dict and SimulationConfig object
    if hasattr(config, 'metadata'):
        # SimulationConfig object
        metadata = config.metadata if config.metadata else {}
        prospection_config = metadata.get("prospection_config", {}) if isinstance(metadata, dict) else {}
    else:
        # Dict
        prospection_config = config.get("metadata", {}).get("prospection_config", {})

    # Get time horizons
    time_horizons = prospection_config.get("time_horizons", ["24h"])

    # Get prospection ability from config or entity traits
    prospection_ability = prospection_config.get("prospection_ability")
    if prospection_ability is None:
        prospection_ability = entity.entity_metadata.get("cognitive_traits", {}).get("prospection_ability", 0.5)

    # Get theory of mind
    theory_of_mind = prospection_config.get("theory_of_mind")
    if theory_of_mind is None:
        theory_of_mind = entity.entity_metadata.get("cognitive_traits", {}).get("theory_of_mind", 0.5)

    # Anxiety baseline from personality
    personality_traits = entity.entity_metadata.get("personality_traits", [])
    anxiety_baseline = 0.3  # Default
    if len(personality_traits) > 3:
        anxiety_baseline = personality_traits[3]  # Neuroticism

    # Forecast confidence from role/experience
    forecast_confidence = 0.5  # Default
    role = entity.entity_metadata.get("role", "").lower()
    if any(expert_role in role for expert_role in ["detective", "strategist", "mastermind"]):
        forecast_confidence = 0.8

    return {
        "time_horizons": time_horizons,
        "prospection_ability": prospection_ability,
        "theory_of_mind": theory_of_mind,
        "anxiety_baseline": anxiety_baseline,
        "forecast_confidence": forecast_confidence
    }


def trigger_prospection_for_entity(
    entity: Entity,
    timepoint: Timepoint,
    llm_client: Any,
    store: GraphStore,
    config: Dict[str, Any]
) -> Optional[ProspectiveState]:
    """
    Trigger prospection for an entity (M15).

    This is the main entry point for prospection generation. It:
    1. Checks if prospection should be triggered
    2. Gets prospection parameters
    3. Generates prospective state via LLM
    4. Saves to store
    5. Returns prospective state for optional tensor refinement

    Args:
        entity: Entity to generate prospection for
        timepoint: Current timepoint
        llm_client: LLM client for generation
        store: GraphStore for persistence
        config: Simulation configuration

    Returns:
        ProspectiveState if triggered, None otherwise
    """
    # Check if prospection should trigger
    if not should_trigger_prospection(entity, timepoint, config):
        return None

    # Get prospection parameters
    params = get_prospection_params(entity, timepoint, config)

    # Generate prospective state using workflows
    from workflows import generate_prospective_state

    try:
        prospective_state = generate_prospective_state(
            entity,
            timepoint,
            llm_client,
            store
            # Note: params (time_horizons, etc.) are not passed to generate_prospective_state
            # because they're handled internally by the prospection mechanism
        )

        # Save to store
        store.save_prospective_state(prospective_state)

        # Mark entity as having prospection
        entity.entity_metadata["has_prospection"] = True
        entity.entity_metadata["prospective_id"] = prospective_state.prospective_id

        return prospective_state

    except Exception as e:
        print(f"  ⚠️  Prospection failed for {entity.entity_id}: {e}")
        return None


def query_driven_prospection(
    entity_id: str,
    query: str,
    store: GraphStore,
    llm_client: Any,
    config: Dict[str, Any]
) -> Optional[ProspectiveState]:
    """
    Trigger prospection in response to user query.

    This is for query-driven prospection (M5 integration).
    Example queries:
    - "What is Holmes expecting?"
    - "What is Moriarty planning?"
    - "What will happen next?"

    Args:
        entity_id: Entity to generate prospection for
        query: User query text
        store: GraphStore
        llm_client: LLM client
        config: Simulation configuration

    Returns:
        ProspectiveState if generated, None otherwise
    """
    # Get entity
    entity = store.get_entity(entity_id)
    if not entity:
        return None

    # Get current timepoint (most recent)
    timepoints = store.get_all_timepoints()
    if not timepoints:
        return None

    current_timepoint = timepoints[-1]

    # Force prospection for this query
    entity.entity_metadata["needs_prospection"] = True

    # Trigger prospection
    return trigger_prospection_for_entity(
        entity, current_timepoint, llm_client, store, config
    )


def refine_tensor_from_prospection(
    entity: Entity,
    prospective_state: ProspectiveState
) -> None:
    """
    Optionally refine entity tensor using prospection data.

    This is OPTIONAL refinement - prospection is NOT the foundation
    of tensor initialization anymore. It's just an enhancement signal.

    Refinement strategy:
    - Increase context_vector[0] based on expectation count
    - Adjust context_vector[3] based on anxiety_level
    - Adjust context_vector[4] based on forecast_confidence

    Args:
        entity: Entity to refine
        prospective_state: ProspectiveState with expectations

    Returns:
        None (modifies entity tensor in place)
    """
    import json
    import base64
    import numpy as np
    import msgspec

    # Load current tensor
    if not entity.tensor:
        return

    tensor_dict = json.loads(entity.tensor)
    context = np.array(msgspec.msgpack.decode(base64.b64decode(tensor_dict["context_vector"])))

    # Get expectations from prospective_state
    # ProspectiveState.expectations is a string field, so we need to parse it or use a default
    # For now, just use the number of expectations if available, otherwise use 0
    expectations_count = 0
    if hasattr(prospective_state, 'expectations') and prospective_state.expectations:
        # If expectations is a list, count it; if string, estimate from length
        if isinstance(prospective_state.expectations, list):
            expectations_count = len(prospective_state.expectations)
        elif isinstance(prospective_state.expectations, str):
            # Rough estimate: one expectation per 100 characters
            expectations_count = len(prospective_state.expectations) // 100

    # Refinement adjustments (small, additive)
    expectation_boost = min(expectations_count / 10.0, 0.2)  # Max +0.2
    context[0] = min(context[0] + expectation_boost, 1.5)

    # Anxiety adjustment
    anxiety_delta = (prospective_state.anxiety_level - context[3]) * 0.3  # 30% weight
    context[3] = np.clip(context[3] + anxiety_delta, 0.0, 1.5)

    # Forecast confidence adjustment
    confidence_delta = (prospective_state.forecast_confidence - context[4]) * 0.2
    context[4] = np.clip(context[4] + confidence_delta, 0.0, 1.5)

    # Update tensor
    entity.tensor = json.dumps({
        "context_vector": base64.b64encode(msgspec.msgpack.encode(context.tolist())).decode('utf-8'),
        "biology_vector": tensor_dict["biology_vector"],
        "behavior_vector": tensor_dict["behavior_vector"]
    })

    print(f"  ✨ Refined {entity.entity_id} tensor from prospection (anxiety: {prospective_state.anxiety_level:.2f})")


async def trigger_prospection_parallel(
    entities: List[Entity],
    timepoint: Timepoint,
    llm_client: Any,
    store: GraphStore,
    config: Dict[str, Any],
    max_concurrent: int = 4
) -> Dict[str, Optional[ProspectiveState]]:
    """
    Trigger prospection for multiple entities concurrently.

    Uses asyncio.Semaphore + ThreadPoolExecutor to run up to max_concurrent
    prospection calls in parallel (same pattern as training/parallel_trainer.py).

    Args:
        entities: List of entities to process
        timepoint: Current timepoint
        llm_client: LLM client for generation
        store: GraphStore for persistence
        config: Simulation configuration
        max_concurrent: Maximum concurrent prospection calls (default 4)

    Returns:
        Dict mapping entity_id → ProspectiveState (or None if not triggered/failed)
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results: Dict[str, Optional[ProspectiveState]] = {}

    async def process_entity(entity: Entity) -> tuple:
        async with semaphore:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                try:
                    prospective_state = await loop.run_in_executor(
                        executor,
                        lambda: trigger_prospection_for_entity(
                            entity, timepoint, llm_client, store, config
                        )
                    )
                    if prospective_state:
                        # Refine tensor from prospection result
                        refine_tensor_from_prospection(entity, prospective_state)
                    return entity.entity_id, prospective_state
                except Exception as e:
                    print(f"  ⚠️  Parallel prospection failed for {entity.entity_id}: {e}")
                    return entity.entity_id, None

    tasks = [process_entity(entity) for entity in entities]
    completed = await asyncio.gather(*tasks)

    for entity_id, state in completed:
        results[entity_id] = state

    triggered = sum(1 for v in results.values() if v is not None)
    print(f"  [M15] Parallel prospection: {triggered}/{len(entities)} entities triggered")

    return results
