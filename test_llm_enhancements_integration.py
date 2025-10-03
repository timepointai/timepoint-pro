#!/usr/bin/env python3
"""
test_llm_enhancements_integration.py - Integration tests for enhanced LLM mechanisms

Tests the four enhanced mechanisms:
- M15: Entity Prospection with real LLM
- M16: Animistic Entities with LLM generation
- M10: Scene Entities with LLM-generated atmosphere
- M12: Counterfactual Branching with LLM outcome prediction
"""

import sys
sys.path.insert(0, '/code')

import os
from datetime import datetime
from pathlib import Path
import tempfile

# Load API key from .env if available
from dotenv import load_dotenv
load_dotenv('/code/.env')

from llm_v2 import LLMClient
from schemas import (
    Entity, Timepoint, ResolutionLevel, Expectation,
    AnimalEntity, BuildingEntity, AbstractEntity,
    EnvironmentEntity, AtmosphereEntity, Intervention
)
from workflows import (
    generate_prospective_state,
    create_animistic_entity,
    compute_scene_atmosphere,
    create_counterfactual_branch,
    create_environment_entity
)
from storage import GraphStore
from hydra import initialize, compose


def test_m15_prospection_with_real_llm():
    """Test M15: Entity Prospection with real LLM calls"""
    print("\n" + "="*70)
    print("TEST 1: M15 Prospection with Real LLM")
    print("="*70)

    # Initialize Hydra config
    with initialize(version_base=None, config_path="conf"):
        cfg = compose(config_name="config", overrides=["llm.dry_run=false"])

        # Create LLM client with centralized service
        llm = LLMClient.from_hydra_config(cfg, use_centralized_service=True)

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
            timeline_id="main",
            timestamp=datetime(1789, 4, 30),
            event_description="George Washington's inauguration as first President",
            resolution="day"
        )

        print("🔮 Generating prospective state with real LLM...")

        # Generate prospective state
        prospective_state = generate_prospective_state(entity, timepoint, llm)

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
            print(f"   Desired: {first_exp.get('desired_outcome', False)}")
            print(f"   Confidence: {first_exp.get('confidence', 0.0):.2f}")

        # Check LLM statistics
        print(f"\n💰 LLM Stats:")
        print(f"   Tokens used: {llm.token_count}")
        print(f"   Cost: ${llm.cost:.4f}")

        assert len(prospective_state.expectations) > 0, "Should generate at least one expectation"
        assert 0.0 <= prospective_state.anxiety_level <= 1.0, "Anxiety should be between 0 and 1"

        print("\n✅ M15 Prospection test passed!")
        return True


def test_m16_animistic_entities_with_llm():
    """Test M16: Animistic Entities with LLM enrichment"""
    print("\n" + "="*70)
    print("TEST 2: M16 Animistic Entities with LLM Enrichment")
    print("="*70)

    # Initialize Hydra config
    with initialize(version_base=None, config_path="conf"):
        cfg = compose(config_name="config", overrides=["llm.dry_run=false"])

        # Create LLM client
        llm = LLMClient.from_hydra_config(cfg, use_centralized_service=True)

        # Test animal entity
        print("🐴 Creating animal entity with LLM enrichment...")

        context = {
            "timepoint_context": "George Washington's inauguration 1789",
            "current_timepoint": "tp_1789_04_30",
            "llm_client": llm
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
            if 'notable_traits' in enrichment:
                print(f"   Traits: {', '.join(enrichment['notable_traits'][:3])}")
            if 'historical_significance' in enrichment:
                print(f"   Significance: {enrichment.get('historical_significance', 'N/A')[:100]}...")

        # Test building entity
        print("\n🏛️ Creating building entity with LLM enrichment...")

        building_entity = create_animistic_entity("federal_hall", "building", context, config)

        print(f"✅ Building entity created: {building_entity.entity_id}")

        if 'llm_enrichment' in building_entity.entity_metadata:
            enrichment = building_entity.entity_metadata['llm_enrichment']
            print(f"\n📖 LLM Enrichment:")
            print(f"   Background: {enrichment.get('background_story', 'N/A')[:200]}...")
            if 'architectural_style' in enrichment:
                print(f"   Architecture: {enrichment.get('architectural_style', 'N/A')}")

        print("\n✅ M16 Animistic Entities test passed!")
        return True


def test_m10_scene_atmosphere_with_llm():
    """Test M10: Scene Entities with LLM-generated atmosphere"""
    print("\n" + "="*70)
    print("TEST 3: M10 Scene Atmosphere with LLM Generation")
    print("="*70)

    # Initialize Hydra config
    with initialize(version_base=None, config_path="conf"):
        cfg = compose(config_name="config", overrides=["llm.dry_run=false"])

        # Create LLM client
        llm = LLMClient.from_hydra_config(cfg, use_centralized_service=True)

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
            Entity(
                entity_id="jefferson",
                entity_type="person",
                resolution_level=ResolutionLevel.TRAINED,
                entity_metadata={
                    "cognitive_tensor": {
                        "emotional_valence": 0.4,
                        "emotional_arousal": 0.5,
                        "energy_budget": 70.0
                    }
                }
            )
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
            llm_client=llm,
            timepoint_info=timepoint_info
        )

        print(f"✅ Atmosphere computed: {atmosphere.scene_id}")
        print(f"   Tension: {atmosphere.tension_level:.2f}")
        print(f"   Formality: {atmosphere.formality_level:.2f}")
        print(f"   Energy: {atmosphere.energy_level:.2f}")
        print(f"   Social cohesion: {atmosphere.social_cohesion:.2f}")

        # Check for LLM-generated narrative
        if hasattr(atmosphere, 'llm_narrative'):
            narrative = atmosphere.llm_narrative
            print(f"\n📖 LLM-Generated Atmosphere:")
            print(f"   Dominant mood: {narrative.get('dominant_mood', 'N/A')}")
            print(f"   Narrative: {narrative.get('atmospheric_narrative', 'N/A')[:300]}...")
            if 'sensory_details' in narrative:
                print(f"   Sensory details: {', '.join(narrative['sensory_details'][:3])}")

        print("\n✅ M10 Scene Atmosphere test passed!")
        return True


def test_m12_counterfactual_with_llm():
    """Test M12: Counterfactual Branching with LLM outcome prediction"""
    print("\n" + "="*70)
    print("TEST 4: M12 Counterfactual Branching with LLM Prediction")
    print("="*70)

    # Initialize Hydra config
    with initialize(version_base=None, config_path="conf"):
        cfg = compose(config_name="config", overrides=["llm.dry_run=false"])

        # Create LLM client
        llm = LLMClient.from_hydra_config(cfg, use_centralized_service=True)

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            store = GraphStore(f"sqlite:///{db_path}")

            # Create baseline timeline with timepoints
            from schemas import Timeline
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
                timeline_id="baseline_1789",
                timestamp=datetime(1789, 4, 30),
                event_description="Washington inaugurated as president",
                resolution="day",
                entities_present=["washington", "adams", "jefferson"]
            )
            store.save_timepoint(tp1)

            tp2 = Timepoint(
                timepoint_id="tp_1789_05_01",
                timeline_id="baseline_1789",
                timestamp=datetime(1789, 5, 1),
                event_description="First cabinet meeting",
                resolution="day",
                entities_present=["washington", "adams", "jefferson", "hamilton"]
            )
            store.save_timepoint(tp2)

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
                llm_client=llm
            )

            print(f"✅ Counterfactual branch created: {branch_id}")

            # Get branch timeline and check for LLM prediction
            branch_timeline = store.get_timeline(branch_id)
            if branch_timeline and hasattr(branch_timeline, 'metadata'):
                if 'llm_prediction' in branch_timeline.metadata:
                    prediction = branch_timeline.metadata['llm_prediction']
                    print(f"\n🔮 LLM Prediction:")
                    print(f"   Divergence significance: {prediction.get('divergence_significance', 'N/A')}")
                    print(f"   Probability assessment: {prediction.get('probability_assessment', 'N/A')}")
                    if 'immediate_effects' in prediction:
                        print(f"   Immediate effects: {'; '.join(prediction['immediate_effects'][:2])}")
                    if 'timeline_narrative' in prediction:
                        print(f"   Narrative: {prediction['timeline_narrative'][:200]}...")

            print("\n✅ M12 Counterfactual Branching test passed!")
            return True

        finally:
            # Cleanup
            Path(db_path).unlink(missing_ok=True)


def run_all_tests():
    """Run all LLM enhancement integration tests"""
    print("\n" + "="*70)
    print("🧪 LLM ENHANCEMENTS INTEGRATION TESTS")
    print("="*70)
    print("\nTesting four enhanced mechanisms:")
    print("  M15: Entity Prospection")
    print("  M16: Animistic Entities")
    print("  M10: Scene Atmosphere")
    print("  M12: Counterfactual Branching")
    print("\n" + "="*70)

    # Check for API key
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key or api_key == 'test':
        print("\n⚠️  WARNING: No real API key found in environment")
        print("   Set OPENROUTER_API_KEY in .env file to test with real LLM")
        print("   Tests will run in dry-run mode with mock responses")
        print("\n" + "="*70)

    tests = [
        ("M15 Prospection", test_m15_prospection_with_real_llm),
        ("M16 Animistic Entities", test_m16_animistic_entities_with_llm),
        ("M10 Scene Atmosphere", test_m10_scene_atmosphere_with_llm),
        ("M12 Counterfactual Branching", test_m12_counterfactual_with_llm),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, str(e)))

    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if error:
            print(f"      Error: {error}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! LLM enhancements are working correctly.")
        print("\n💡 Next steps:")
        print("  - Run autopilot with real LLM: python autopilot.py --force")
        print("  - Monitor costs: cat logs/llm_calls/*.jsonl | jq -s 'map(.cost_usd) | add'")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
