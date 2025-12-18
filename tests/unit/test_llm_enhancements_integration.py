#!/usr/bin/env python3
"""
test_llm_enhancements_integration.py - Integration tests for enhanced LLM mechanisms

Tests the four enhanced mechanisms:
- M15: Entity Prospection with real LLM
- M16: Animistic Entities with LLM generation
- M10: Scene Entities with LLM-generated atmosphere
- M12: Counterfactual Branching with LLM outcome prediction

Note: LLMClient no longer supports dry_run mode - tests skip when OPENROUTER_API_KEY
is not set.
"""

import sys
import os
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from llm_v2 import LLMClient
from schemas import (
    Entity, Timepoint, ResolutionLevel, Expectation,
    AnimalEntity, BuildingEntity, AbstractEntity,
    EnvironmentEntity, AtmosphereEntity, Intervention, Timeline
)
from workflows import (
    generate_prospective_state,
    create_animistic_entity,
    compute_scene_atmosphere,
    create_counterfactual_branch,
    create_environment_entity
)
from storage import GraphStore


@pytest.fixture
def llm_client():
    """Real LLM client for integration testing"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set - skipping real LLM tests")
    return LLMClient(api_key=api_key)


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_m15_prospection_with_real_llm(llm_client):
    """Test M15: Entity Prospection with real LLM calls"""
    print("\n" + "="*70)
    print("TEST 1: M15 Prospection with Real LLM")
    print("="*70)

    # Create test entity
    entity = Entity(
        entity_id="washington",
        entity_type="person",
        resolution_level=ResolutionLevel.TRAINED,
        entity_metadata={
            "knowledge_state": [
                "Elected first president",
                "Constitutional convention delegate",
                "Revolutionary war general"
            ],
            "personality_traits": {
                "prudence": 0.9,
                "ambition": 0.7,
                "diplomatic": 0.8
            }
        }
    )

    # Create test timepoint
    timepoint = Timepoint(
        timepoint_id="tp_1789_04_30",
        timestamp=datetime(1789, 4, 30),
        event_description="George Washington's inauguration as first President",
        entities_present=["washington"]
    )

    print("🔮 Generating prospective state with real LLM...")

    # Generate prospective state
    prospective_state = generate_prospective_state(entity, timepoint, llm_client)

    print(f"✅ Prospective state generated: {prospective_state.prospective_id}")
    print(f"   Forecast horizon: {prospective_state.forecast_horizon_days} days")
    print(f"   Expectations count: {len(prospective_state.expectations)}")
    print(f"   Anxiety level: {prospective_state.anxiety_level:.3f}")

    # Validate expectations
    if prospective_state.expectations:
        first_exp = prospective_state.expectations[0]
        print(f"\n📝 First expectation:")
        print(f"   Event: {first_exp.get('predicted_event', 'N/A')}")
        print(f"   Probability: {first_exp.get('subjective_probability', 0.0):.2f}")

    assert len(prospective_state.expectations) > 0, "Should generate at least one expectation"
    assert 0.0 <= prospective_state.anxiety_level <= 1.0, "Anxiety should be between 0 and 1"

    print("\n✅ M15 Prospection test passed!")


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_m16_animistic_entities_with_llm(llm_client):
    """Test M16: Animistic Entities with LLM enrichment"""
    print("\n" + "="*70)
    print("TEST 2: M16 Animistic Entities with LLM Enrichment")
    print("="*70)

    # Test animal entity
    print("🐴 Creating animal entity with LLM enrichment...")

    context = {
        "timepoint_context": "George Washington's inauguration 1789",
        "current_timepoint": "tp_1789_04_30",
        "llm_client": llm_client
    }

    config = {
        "animism": {
            "llm_enrichment_enabled": True,
            "biological_defaults": {
                "animal_health": 0.9,
                "animal_energy": 0.8
            }
        }
    }

    animal_entity = create_animistic_entity("horse_ceremonial", "animal", context, config)

    print(f"✅ Animal entity created: {animal_entity.entity_id}")
    print(f"   Type: {animal_entity.entity_type}")

    # Check if LLM enrichment was added
    if 'llm_enrichment' in animal_entity.entity_metadata:
        enrichment = animal_entity.entity_metadata['llm_enrichment']
        print(f"\n📖 LLM Enrichment:")
        print(f"   Background: {enrichment.get('background_story', 'N/A')[:200]}...")

    # Test building entity
    print("\n🏛️ Creating building entity with LLM enrichment...")

    building_entity = create_animistic_entity("federal_hall", "building", context, config)

    print(f"✅ Building entity created: {building_entity.entity_id}")

    assert animal_entity.entity_type == "animal"
    assert building_entity.entity_type == "building"

    print("\n✅ M16 Animistic Entities test passed!")


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_m10_scene_atmosphere_with_llm(llm_client):
    """Test M10: Scene Entities with LLM-generated atmosphere"""
    print("\n" + "="*70)
    print("TEST 3: M10 Scene Atmosphere with LLM Generation")
    print("="*70)

    # Create environment
    environment = create_environment_entity(
        timepoint_id="tp_1789_04_30",
        location="Federal Hall, New York City",
        capacity=500,
        temperature=20.0,
        lighting=0.8,
        weather="clear spring day"
    )

    # Create some test entities
    entities = [
        Entity(
            entity_id="washington",
            entity_type="person",
            resolution_level=ResolutionLevel.TRAINED,
            entity_metadata={
                "cognitive_tensor": {
                    "emotional_valence": 0.6,
                    "emotional_arousal": 0.7,
                    "energy_budget": 80.0
                }
            }
        ),
        Entity(
            entity_id="adams",
            entity_type="person",
            resolution_level=ResolutionLevel.TRAINED,
            entity_metadata={
                "cognitive_tensor": {
                    "emotional_valence": 0.5,
                    "emotional_arousal": 0.6,
                    "energy_budget": 75.0
                }
            }
        ),
    ]

    # Timepoint info for LLM
    timepoint_info = {
        'event_description': "George Washington's inauguration as first President",
        'timestamp': datetime(1789, 4, 30).isoformat(),
        'timepoint_id': 'tp_1789_04_30'
    }

    print("🎭 Computing scene atmosphere with LLM generation...")

    # Compute atmosphere with LLM
    atmosphere = compute_scene_atmosphere(
        entities=entities,
        environment=environment,
        llm_client=llm_client,
        timepoint_info=timepoint_info
    )

    print(f"✅ Atmosphere computed: {atmosphere.scene_id}")
    print(f"   Tension: {atmosphere.tension_level:.2f}")
    print(f"   Formality: {atmosphere.formality_level:.2f}")

    assert atmosphere.scene_id is not None

    print("\n✅ M10 Scene Atmosphere test passed!")


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_m12_counterfactual_with_llm(llm_client):
    """Test M12: Counterfactual Branching with LLM outcome prediction"""
    print("\n" + "="*70)
    print("TEST 4: M12 Counterfactual Branching with LLM Prediction")
    print("="*70)

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        store = GraphStore(f"sqlite:///{db_path}")

        # Create baseline timeline with timepoints
        baseline_timeline = Timeline(
            timeline_id="baseline_1789",
            timepoint_id="tp_1789_04_30",
            timestamp=datetime(1789, 4, 30),
            resolution="day",
            entities_present=["washington", "adams", "jefferson"],
            events=["inauguration"]
        )
        store.save_timeline(baseline_timeline)

        # Create timepoints
        tp1 = Timepoint(
            timepoint_id="tp_1789_04_30",
            timestamp=datetime(1789, 4, 30),
            event_description="Washington inaugurated as president",
            entities_present=["washington", "adams", "jefferson"]
        )
        store.save_timepoint(tp1)

        # Create intervention
        intervention = Intervention(
            type="entity_removal",
            target="jefferson",
            description="Jefferson does not attend inauguration"
        )

        print("🔀 Creating counterfactual branch with LLM prediction...")

        # Create counterfactual branch with LLM
        branch_id = create_counterfactual_branch(
            parent_timeline_id="baseline_1789",
            intervention_point="tp_1789_04_30",
            intervention=intervention,
            store=store,
            llm_client=llm_client
        )

        print(f"✅ Counterfactual branch created: {branch_id}")

        assert branch_id is not None

        print("\n✅ M12 Counterfactual Branching test passed!")

    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
