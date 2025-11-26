# ============================================================================
# workflows/scene_environment.py - Scene-Level Entity Aggregation (Mechanism 10)
# ============================================================================
"""
Scene environment and atmosphere computation.

Contains:
- create_environment_entity: Create environment entity for a scene
- compute_scene_atmosphere: Aggregate entity states into atmosphere (@M10)
- compute_crowd_dynamics: Compute crowd composition and dynamics
- Helper functions for tension, formality, emotion classification
"""

from typing import List, Dict, Optional
import numpy as np
from collections import Counter
import json

from schemas import Entity, EnvironmentEntity, AtmosphereEntity, CrowdEntity
from metadata.tracking import track_mechanism


def create_environment_entity(timepoint_id: str, location: str, capacity: int = 1000,
                             temperature: float = 20.0, lighting: float = 0.8,
                             weather: Optional[str] = None) -> EnvironmentEntity:
    """Create an environment entity for a scene"""
    scene_id = f"{timepoint_id}_env"

    # Infer architectural style and acoustic properties based on location
    architectural_style, acoustic_props = infer_location_properties(location)

    return EnvironmentEntity(
        scene_id=scene_id,
        timepoint_id=timepoint_id,
        location=location,
        capacity=capacity,
        ambient_temperature=temperature,
        lighting_level=lighting,
        weather=weather,
        architectural_style=architectural_style,
        acoustic_properties=acoustic_props
    )


@track_mechanism("M10", "scene_entities_atmosphere")
def compute_scene_atmosphere(entities: List[Entity], environment: EnvironmentEntity,
                           relationship_graph=None,
                           llm_client=None, timepoint_info: Optional[Dict] = None) -> AtmosphereEntity:
    """Aggregate individual entity states into scene atmosphere"""

    if not entities:
        # Default neutral atmosphere for empty scenes
        return AtmosphereEntity(
            scene_id=environment.scene_id,
            timepoint_id=environment.timepoint_id,
            tension_level=0.0,
            formality_level=0.5,
            emotional_valence=0.0,
            emotional_arousal=0.0,
            social_cohesion=0.5,
            energy_level=0.5
        )

    # Aggregate emotional states from all entities
    emotional_valences = []
    emotional_arousals = []
    energy_levels = []

    for entity in entities:
        try:
            cognitive = entity.cognitive_tensor
            emotional_valences.append(cognitive.emotional_valence)
            emotional_arousals.append(cognitive.emotional_arousal)
            energy_levels.append(cognitive.energy_budget / 100.0)  # Normalize to 0-1
        except (AttributeError, KeyError):
            # Skip entities without cognitive tensors
            continue

    # Compute aggregated emotional metrics
    avg_valence = np.mean(emotional_valences) if emotional_valences else 0.0
    avg_arousal = np.mean(emotional_arousals) if emotional_arousals else 0.0
    avg_energy = np.mean(energy_levels) if energy_levels else 0.5

    # Compute tension from relationship conflicts
    tension_level = compute_tension_from_relationships(entities, relationship_graph)

    # Infer formality from location and context
    formality_level = infer_formality_from_location(environment.location)

    # Compute social cohesion (inverse of tension, adjusted by formality)
    social_cohesion = max(0.0, 1.0 - tension_level - (formality_level * 0.3))

    atmosphere = AtmosphereEntity(
        scene_id=environment.scene_id,
        timepoint_id=environment.timepoint_id,
        tension_level=tension_level,
        formality_level=formality_level,
        emotional_valence=avg_valence,
        emotional_arousal=avg_arousal,
        social_cohesion=social_cohesion,
        energy_level=avg_energy
    )

    # Optional: Generate rich narrative description with LLM
    if llm_client is not None and timepoint_info is not None:
        try:
            # Prepare data for LLM
            timepoint_dict = {
                'event_description': timepoint_info.get('event_description', ''),
                'timestamp': timepoint_info.get('timestamp', ''),
                'timepoint_id': timepoint_info.get('timepoint_id', '')
            }

            env_dict = {
                'location': environment.location,
                'ambient_temperature': environment.ambient_temperature,
                'lighting_level': environment.lighting_level,
                'weather': environment.weather,
                'architectural_style': environment.architectural_style
            }

            atmosphere_dict = {
                'tension_level': tension_level,
                'formality_level': formality_level,
                'emotional_valence': avg_valence,
                'energy_level': avg_energy,
                'social_cohesion': social_cohesion
            }

            entity_dicts = [{'entity_id': e.entity_id, 'entity_type': e.entity_type} for e in entities[:20]]

            # Generate LLM description
            llm_description = llm_client.generate_scene_atmosphere(
                timepoint=timepoint_dict,
                entities=entity_dicts,
                environment=env_dict,
                atmosphere_data=atmosphere_dict
            )

            # Add LLM-generated narrative to atmosphere metadata
            if hasattr(atmosphere, 'metadata'):
                atmosphere.metadata['llm_narrative'] = llm_description
            else:
                # Store in a custom attribute if metadata doesn't exist
                atmosphere.llm_narrative = llm_description

        except Exception as e:
            # If LLM generation fails, continue with base atmosphere
            pass

    return atmosphere


def compute_crowd_dynamics(entities: List[Entity], environment: EnvironmentEntity) -> CrowdEntity:
    """Compute crowd composition and dynamics"""

    scene_id = environment.scene_id
    timepoint_id = environment.timepoint_id

    # Basic crowd size and density
    crowd_size = len(entities)
    density = min(1.0, crowd_size / environment.capacity)

    # Analyze mood distribution from emotional states
    mood_counts = Counter()
    total_entities = 0

    for entity in entities:
        try:
            cognitive = entity.cognitive_tensor
            mood = classify_emotional_state(cognitive.emotional_valence, cognitive.emotional_arousal)
            mood_counts[mood] += 1
            total_entities += 1
        except (AttributeError, KeyError):
            continue

    # Convert to percentage distribution
    mood_distribution = {}
    if total_entities > 0:
        for mood, count in mood_counts.items():
            mood_distribution[mood] = count / total_entities

    # Infer movement pattern based on atmosphere and density
    movement_pattern = infer_movement_pattern(density, mood_distribution)

    # Estimate noise level based on crowd size and energy
    noise_level = min(1.0, density * 0.8 + (mood_distribution.get('excited', 0) * 0.5))

    # Basic demographic composition (simplified)
    demographic_composition = {
        "age_groups": {"young": 0.2, "middle": 0.6, "elderly": 0.2},
        "gender_balance": {"male": 0.7, "female": 0.3}  # Historical bias
    }

    return CrowdEntity(
        scene_id=scene_id,
        timepoint_id=timepoint_id,
        size=crowd_size,
        density=density,
        mood_distribution=json.dumps(mood_distribution),
        movement_pattern=movement_pattern,
        demographic_composition=json.dumps(demographic_composition),
        noise_level=noise_level
    )


def compute_tension_from_relationships(entities: List[Entity], relationship_graph=None) -> float:
    """Compute scene tension level from entity relationships"""
    if not entities or len(entities) < 2:
        return 0.0

    if relationship_graph is None:
        # Simple heuristic: assume moderate tension without relationship data
        return 0.3

    # Count negative relationships (edges with negative weights)
    total_relationships = 0
    negative_relationships = 0

    entity_ids = {entity.entity_id for entity in entities}

    for u, v, data in relationship_graph.edges(data=True):
        if u in entity_ids and v in entity_ids:
            total_relationships += 1
            # Check for negative relationship indicators
            if data.get('weight', 0) < 0 or data.get('tension', False):
                negative_relationships += 1

    if total_relationships == 0:
        return 0.3  # Default moderate tension

    tension_ratio = negative_relationships / total_relationships
    return min(1.0, tension_ratio * 1.5)  # Amplify tension for dramatic effect


def infer_formality_from_location(location: str) -> float:
    """Infer formality level from location description"""
    location_lower = location.lower()

    # High formality locations
    if any(term in location_lower for term in ['hall', 'chamber', 'court', 'palace', 'cathedral']):
        return 0.9

    # Medium formality
    elif any(term in location_lower for term in ['meeting house', 'assembly', 'congress', 'senate']):
        return 0.7

    # Low formality
    elif any(term in location_lower for term in ['tavern', 'inn', 'street', 'park', 'home']):
        return 0.2

    # Default moderate formality
    else:
        return 0.5


def infer_location_properties(location: str) -> tuple:
    """Infer architectural style and acoustic properties from location"""
    location_lower = location.lower()

    if 'hall' in location_lower or 'chamber' in location_lower:
        return "colonial_government", "reverberant"
    elif 'church' in location_lower or 'cathedral' in location_lower:
        return "colonial_religious", "reverberant"
    elif 'tavern' in location_lower or 'inn' in location_lower:
        return "colonial_commercial", "muffled"
    elif 'street' in location_lower or 'park' in location_lower:
        return "urban_outdoor", "open"
    else:
        return "colonial_civil", "moderate"


def classify_emotional_state(valence: float, arousal: float) -> str:
    """Classify emotional state into discrete mood categories"""
    if valence > 0.3 and arousal > 0.3:
        return "excited"
    elif valence > 0.3 and arousal <= 0.3:
        return "content"
    elif valence < -0.3 and arousal > 0.3:
        return "angry"
    elif valence < -0.3 and arousal <= 0.3:
        return "sad"
    else:
        return "neutral"


def infer_movement_pattern(density: float, mood_distribution: Dict[str, float]) -> str:
    """Infer crowd movement pattern from density and mood"""
    excited_ratio = mood_distribution.get('excited', 0)
    angry_ratio = mood_distribution.get('angry', 0)

    if density > 0.8:
        if excited_ratio > 0.3 or angry_ratio > 0.3:
            return "agitated"
        else:
            return "static"  # Dense but calm crowds tend to be still
    elif density > 0.5:
        if excited_ratio > 0.4:
            return "flowing"
        else:
            return "orderly"
    else:
        return "static"  # Sparse crowds are typically static
