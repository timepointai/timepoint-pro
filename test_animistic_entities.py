#!/usr/bin/env python3
"""
test_animistic_entities.py - Tests for Mechanism 16: Animistic Entity Extension
"""
import numpy as np
from datetime import datetime

from schemas import Entity, AnimalEntity, BuildingEntity, AbstractEntity, AnyEntity, KamiEntity, AIEntity, ResolutionLevel
from workflows import should_create_animistic_entity, create_animistic_entity, generate_animistic_entities_for_scene
from validation import Validator
import pytest


@pytest.mark.animism
@pytest.mark.integration
@pytest.mark.system
class TestAnimisticEntityCreation:
    """Test creation of animistic entities"""

    def test_should_create_animistic_entity_hierarchy(self):
        """Test animism level hierarchy"""
        config = {"level": 1}  # Animals and buildings only

        assert should_create_animistic_entity("human", config) == False
        assert should_create_animistic_entity("animal", config) == True
        assert should_create_animistic_entity("building", config) == True
        assert should_create_animistic_entity("object", config) == False
        assert should_create_animistic_entity("abstract", config) == False
        assert should_create_animistic_entity("any", config) == False
        assert should_create_animistic_entity("kami", config) == False
        assert should_create_animistic_entity("ai", config) == False

        config["level"] = 2  # Up to objects
        assert should_create_animistic_entity("object", config) == True
        assert should_create_animistic_entity("abstract", config) == False
        assert should_create_animistic_entity("any", config) == False

        config["level"] = 3  # All types up to abstract
        assert should_create_animistic_entity("abstract", config) == True
        assert should_create_animistic_entity("any", config) == False

        config["level"] = 4  # Any entities
        assert should_create_animistic_entity("any", config) == True
        assert should_create_animistic_entity("kami", config) == False

        config["level"] = 5  # Kami spirits
        assert should_create_animistic_entity("kami", config) == True
        assert should_create_animistic_entity("ai", config) == False

        config["level"] = 6  # AI entities
        assert should_create_animistic_entity("ai", config) == True

    def test_create_animal_entity(self):
        """Test animal entity creation with proper metadata"""
        context = {
            "timepoint_context": "founding fathers 1789",
            "current_timepoint": "tp_1789_04_30"
        }
        config = {
            "animism": {
                "biological_defaults": {
                    "animal_health": 0.9,
                    "animal_energy": 0.8,
                    "animal_training": 0.5
                }
            }
        }

        entity = create_animistic_entity("horse_war", "animal", context, config)

        assert entity.entity_id == "horse_war"
        assert entity.entity_type == "animal"
        assert entity.resolution_level == ResolutionLevel.TENSOR_ONLY

        # Check animal metadata
        animal = AnimalEntity(**entity.entity_metadata)
        assert animal.species == "horse"  # Inferred from context
        assert animal.biological_state["health"] == 0.9
        assert animal.biological_state["energy"] == 0.8
        assert animal.training_level == 0.5
        assert "avoid_pain" in animal.goals
        assert "seek_food" in animal.goals

    def test_create_building_entity(self):
        """Test building entity creation"""
        context = {"location": "federal_hall"}
        config = {
            "animism": {
                "building_defaults": {
                    "structural_integrity": 0.85,
                    "maintenance_state": 0.8
                }
            }
        }

        entity = create_animistic_entity("federal_hall", "building", context, config)

        assert entity.entity_type == "building"
        building = BuildingEntity(**entity.entity_metadata)
        assert building.structural_integrity == 0.85
        assert building.maintenance_state == 0.8
        assert building.capacity >= 50  # Random but reasonable
        assert building.age >= 1  # Random but reasonable
        assert "shelter" in building.affordances

    def test_create_abstract_entity(self):
        """Test abstract concept entity creation"""
        context = {}
        config = {
            "animism": {
                "abstract_defaults": {
                    "initial_intensity": 0.7,
                    "decay_rate": 0.01,
                    "coherence": 0.9
                }
            }
        }

        entity = create_animistic_entity("democracy_concept", "abstract", context, config)

        assert entity.entity_type == "abstract"
        concept = AbstractEntity(**entity.entity_metadata)
        assert concept.intensity == 0.7
        assert concept.decay_rate == 0.01
        assert concept.coherence == 0.9
        assert len(concept.propagation_vector) == 5  # Default vector
        assert "beliefs" in concept.manifestation_forms

    def test_species_inference(self):
        """Test species inference from entity IDs"""
        from workflows import infer_species_from_context

        # Direct species mentions
        assert infer_species_from_context("stallion_war", {}) == "horse"
        assert infer_species_from_context("hound_dog", {}) == "dog"
        assert infer_species_from_context("eagle_spy", {}) == "bird"

        # Context-based inference
        context_1789 = {"timepoint_context": "founding fathers 1789"}
        assert infer_species_from_context("transport_animal", context_1789) == "horse"

        context_florence = {"timepoint_context": "renaissance florence"}
        assert infer_species_from_context("riding_beast", context_florence) == "horse"

        # Unknown fallback
        assert infer_species_from_context("mystery_creature", {}) == "unknown"

    def test_create_any_entity(self):
        """Test creation of highly adaptive any entities"""
        from schemas import AnyEntity

        context = {"timepoint_context": "mysterious_occurrence"}
        config = {
            "animism": {
                "any_defaults": {
                    "adaptability_score": 0.9,
                    "stability_index": 0.7,
                    "influence_radius": 15.0
                }
            }
        }

        entity = create_animistic_entity("chaos_entity", "any", context, config)

        assert entity.entity_id == "chaos_entity"
        assert entity.entity_type == "any"
        assert entity.resolution_level == ResolutionLevel.TENSOR_ONLY

        # Check any entity metadata
        any_entity = AnyEntity(**entity.entity_metadata)
        assert any_entity.adaptability_score == 0.9
        assert any_entity.stability_index == 0.7
        assert any_entity.influence_radius == 15.0
        assert any_entity.essence_type in ["physical", "spiritual", "conceptual", "chaotic"]
        assert len(any_entity.morphing_capability) >= 3  # Should have multiple morphing options
        assert len(any_entity.adaptive_goals) >= 3  # Should have adaptive goals

    def test_create_kami_entity(self):
        """Test creation of spiritual kami entities"""
        from schemas import KamiEntity

        context = {"location": "sacred_grove"}
        config = {
            "animism": {
                "kami_defaults": {
                    "manifestation_probability": 0.2,
                    "spiritual_power": 0.8,
                    "visibility_state": "invisible",
                    "disclosure_level": "rumored"
                }
            }
        }

        entity = create_animistic_entity("forest_spirit", "kami", context, config)

        assert entity.entity_id == "forest_spirit"
        assert entity.entity_type == "kami"

        # Check kami metadata
        kami = KamiEntity(**entity.entity_metadata)
        assert kami.manifestation_probability == 0.2
        assert kami.spiritual_power == 0.8
        assert kami.visibility_state == "invisible"
        assert kami.disclosure_level == "rumored"
        assert len(kami.influence_domain) >= 1  # Should have at least one domain
        # Forest spirit should have nature-related domains (but generation is random, so just check structure)
        valid_domains = ["nature", "weather", "emotions", "fate", "protection", "war", "wisdom", "trickery"]
        assert all(domain in valid_domains for domain in kami.influence_domain)
        assert len(kami.blessings_curses["blessings"]) > 0
        assert len(kami.blessings_curses["curses"]) > 0

    def test_create_ai_entity(self):
        """Test creation of AI-powered entities"""
        from schemas import AIEntity

        context = {"timepoint_context": "digital_age"}
        config = {
            "animism": {
                "ai_defaults": {
                    "temperature": 0.8,
                    "model_name": "gpt-4",
                    "safety_level": "strict",
                    "activation_threshold": 0.6
                }
            }
        }

        entity = create_animistic_entity("oracle_ai", "ai", context, config)

        assert entity.entity_id == "oracle_ai"
        assert entity.entity_type == "ai"

        # Check AI entity metadata
        ai_entity = AIEntity(**entity.entity_metadata)
        assert ai_entity.temperature == 0.8
        assert ai_entity.model_name == "gpt-4"
        assert ai_entity.safety_level == "strict"
        assert ai_entity.activation_threshold == 0.6
        assert ai_entity.system_prompt  # Should have a system prompt
        assert len(ai_entity.input_bleaching_rules) > 0
        assert len(ai_entity.output_filtering_rules) > 0
        assert len(ai_entity.error_handling) > 0
        assert len(ai_entity.fallback_responses) > 0
        assert ai_entity.prohibited_topics  # Should have safety topics
        assert ai_entity.required_disclaimers  # Should have disclaimers


@pytest.mark.animism
@pytest.mark.integration
@pytest.mark.system
class TestAnimisticEntityValidation:
    """Test validation of animistic entities"""

    def test_environmental_constraints_building_capacity(self):
        """Test building capacity constraints"""
        building = BuildingEntity(
            structural_integrity=0.9,
            capacity=100,
            age=50,
            maintenance_state=0.8,
            constraints=["capacity_limited"],
            affordances=["shelter"]
        )

        entity = Entity(
            entity_id="test_hall",
            entity_type="building",
            entity_metadata=building.dict()
        )

        # Valid action (within capacity)
        action = {"participant_count": 80}
        result = Validator._validators["environmental_constraints"]["func"](action, [entity])
        assert result["valid"] == True

        # Invalid action (over capacity)
        action = {"participant_count": 150}
        result = Validator._validators["environmental_constraints"]["func"](action, [entity])
        assert result["valid"] == False
        assert "capacity 100 exceeded" in result["message"]

    def test_environmental_constraints_building_integrity(self):
        """Test building structural integrity constraints"""
        building = BuildingEntity(
            structural_integrity=0.3,  # Too low
            capacity=100,
            age=50,
            maintenance_state=0.8,
            constraints=[],
            affordances=["shelter"]
        )

        entity = Entity(
            entity_id="crumbling_hall",
            entity_type="building",
            entity_metadata=building.dict()
        )

        action = {"participant_count": 50}
        result = Validator._validators["environmental_constraints"]["func"](action, [entity])
        assert result["valid"] == False
        assert "structural integrity too low" in result["message"]

    def test_environmental_constraints_animal_health(self):
        """Test animal health and energy constraints"""
        animal = AnimalEntity(
            species="horse",
            biological_state={"health": 0.1, "energy": 0.9},  # Too unhealthy
            training_level=0.8,
            goals=["avoid_pain", "seek_food"],
            sensory_capabilities={},
            physical_capabilities={}
        )

        entity = Entity(
            entity_id="sick_horse",
            entity_type="animal",
            entity_metadata=animal.dict()
        )

        action = {"action_type": "mount"}
        result = Validator._validators["environmental_constraints"]["func"](action, [entity])
        assert result["valid"] == False
        assert "too unhealthy" in result["message"]

    def test_biological_plausibility_ranges(self):
        """Test biological state range validation"""
        # Valid animal
        animal = AnimalEntity(
            species="dog",
            biological_state={"age": 0.5, "health": 0.8, "energy": 0.7},
            training_level=0.6,
            goals=["seek_food"],
            sensory_capabilities={"vision": 0.8},
            physical_capabilities={"strength": 0.6}
        )

        entity = Entity(
            entity_id="healthy_dog",
            entity_type="animal",
            entity_metadata=animal.dict()
        )

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == True

        # Invalid animal (out of range)
        animal.biological_state["health"] = 1.5  # Invalid range
        entity.entity_metadata = animal.dict()

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "out of range" in result["message"]

    def test_biological_plausibility_building(self):
        """Test building biological plausibility"""
        # Invalid building
        building = BuildingEntity(
            structural_integrity=1.2,  # Out of range
            capacity=100,
            age=-5,  # Invalid age
            maintenance_state=0.8,
            constraints=[],
            affordances=[]
        )

        entity = Entity(
            entity_id="invalid_building",
            entity_type="building",
            entity_metadata=building.dict()
        )

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "out of range" in result["message"]
        assert "invalid age" in result["message"]

    def test_biological_plausibility_abstract(self):
        """Test abstract entity plausibility"""
        # Valid abstract entity
        concept = AbstractEntity(
            propagation_vector=[0.2, 0.2, 0.2, 0.2, 0.2],  # Sums to 1.0
            intensity=0.8,
            carriers=["entity1", "entity2"],
            decay_rate=0.02,
            coherence=0.9,
            manifestation_forms=["beliefs"]
        )

        entity = Entity(
            entity_id="valid_concept",
            entity_type="abstract",
            entity_metadata=concept.dict()
        )

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == True

        # Invalid propagation vector
        concept.propagation_vector = [0.5, 0.5, 0.5]  # Doesn't sum to 1.0
        entity.entity_metadata = concept.dict()

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "doesn't sum to 1.0" in result["message"]

    def test_biological_plausibility_any_entity(self):
        """Test biological plausibility for any entities"""
        from schemas import AnyEntity

        # Valid any entity
        any_entity = AnyEntity(
            adaptability_score=0.8,
            morphing_capability={"object": 0.7, "spirit": 0.5},
            essence_type="chaotic",
            manifestation_forms=["adaptive_form"],
            stability_index=0.6,
            influence_radius=10.0,
            resonance_patterns={"human": 0.8, "animal": 0.6},
            adaptive_goals=["observe", "adapt", "influence"]
        )

        entity = Entity(
            entity_id="valid_any",
            entity_type="any",
            entity_metadata=any_entity.dict()
        )

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == True

        # Invalid any entity (adaptability out of range)
        any_entity.adaptability_score = 1.5
        entity.entity_metadata = any_entity.dict()

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "out of range" in result["message"]

    def test_biological_plausibility_kami_entity(self):
        """Test biological plausibility for kami entities"""
        from schemas import KamiEntity

        # Valid kami entity
        kami = KamiEntity(
            visibility_state="invisible",
            disclosure_level="unknown",
            influence_domain=["nature", "weather"],
            manifestation_probability=0.1,
            spiritual_power=0.5,
            mortal_perception={"human": 0.2, "animal": 0.8},
            blessings_curses={"blessings": ["protection"], "curses": ["illness"]}
        )

        entity = Entity(
            entity_id="valid_kami",
            entity_type="kami",
            entity_metadata=kami.dict()
        )

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == True

        # Invalid kami entity (invalid visibility state)
        kami.visibility_state = "super_visible"
        entity.entity_metadata = kami.dict()

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "invalid visibility state" in result["message"]

        # Invalid kami entity (power out of range)
        kami.visibility_state = "invisible"  # Fix visibility
        kami.spiritual_power = 1.5  # Invalid range
        entity.entity_metadata = kami.dict()

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "spiritual power out of range" in result["message"]

    def test_biological_plausibility_ai_entity(self):
        """Test biological plausibility for AI entities"""
        from schemas import AIEntity

        # Valid AI entity
        ai_entity = AIEntity(
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            safety_level="moderate",
            activation_threshold=0.5,
            response_cache_ttl=300,
            rate_limit_per_minute=60,
            input_bleaching_rules=["remove_script_tags", "prevent_prompt_injection"],
            output_filtering_rules=["filter_harmful_content", "add_content_warnings"],
            error_handling={"api_error": "I'm experiencing difficulties"},
            fallback_responses=["I need a moment to process that."]
        )

        entity = Entity(
            entity_id="valid_ai",
            entity_type="ai",
            entity_metadata=ai_entity.dict()
        )

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == True

        # Invalid AI entity (temperature out of range)
        ai_entity.temperature = 3.0
        entity.entity_metadata = ai_entity.dict()

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "temperature out of range" in result["message"]

        # Invalid AI entity (empty model name)
        ai_entity.temperature = 0.7  # Fix temperature
        ai_entity.model_name = ""
        entity.entity_metadata = ai_entity.dict()

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "empty model_name" in result["message"]

        # Invalid AI entity (no safety features)
        ai_entity.model_name = "gpt-3.5-turbo"  # Fix model name
        ai_entity.input_bleaching_rules = []
        entity.entity_metadata = ai_entity.dict()

        result = Validator._validators["biological_plausibility"]["func"](entity, {})
        assert result["valid"] == False
        assert "no input bleaching rules" in result["message"]


@pytest.mark.animism
@pytest.mark.integration
@pytest.mark.system
class TestSceneGeneration:
    """Test generation of animistic entities for scenes"""

    def test_generate_animistic_entities_probability(self):
        """Test probabilistic generation based on config"""
        scene_context = {"timepoint_id": "tp_1789_04_30", "location": "federal_hall"}
        config = {
            "animism": {
                "level": 1,  # Allow animals and buildings
                "entity_generation": {
                    "animal_probability": 1.0,  # Always generate
                    "building_probability": 0.0,  # Never generate
                }
            }
        }

        entities = generate_animistic_entities_for_scene(scene_context, config)

        # Should have animals but no buildings
        animal_entities = [e for e in entities if e.entity_type == "animal"]
        building_entities = [e for e in entities if e.entity_type == "building"]

        assert len(animal_entities) >= 1
        assert len(building_entities) == 0

    def test_scene_generation_respects_config(self):
        """Test that generation respects animism level config"""
        scene_context = {"timepoint_id": "tp_1789_04_30"}
        config = {
            "animism": {
                "level": 0,  # Humans only
                "entity_generation": {
                    "animal_probability": 1.0,
                    "building_probability": 1.0,
                }
            }
        }

        entities = generate_animistic_entities_for_scene(scene_context, config)

        # Should generate no animistic entities due to level 0
        assert len(entities) == 0


@pytest.mark.animism
@pytest.mark.integration
@pytest.mark.system
class TestAdvancedAnimisticValidators:
    """Test advanced validators for spiritual and adaptive entities"""

    def test_spiritual_influence_validator(self):
        """Test spiritual influence validation for kami entities"""
        kami = KamiEntity(
            visibility_state="invisible",
            disclosure_level="unknown",
            influence_domain=["fate", "protection"],
            manifestation_probability=0.1,
            spiritual_power=0.9,  # High power
            mortal_perception={"human": 0.2},
            blessings_curses={"blessings": ["protection"], "curses": ["illness"]}
        )

        kami_entity = Entity(
            entity_id="fate_kami",
            entity_type="kami",
            entity_metadata=kami.dict()
        )

        # Action that might be influenced by fate kami
        action = {
            "action_type": "decision",
            "description": "making an important life choice",
            "participant_ids": ["character1"],
            "outdoor": False
        }

        result = Validator._validators["spiritual_influence"]["func"](action, [kami_entity])
        # Should warn about unknown kami influence
        assert result["valid"] == False
        assert "Unknown kami" in result["message"]
        assert "may secretly influence" in result["message"]

        # Known kami should also trigger warning
        kami.disclosure_level = "worshiped"
        kami_entity.entity_metadata = kami.dict()

        result = Validator._validators["spiritual_influence"]["func"](action, [kami_entity])
        assert result["valid"] == False
        assert "Known kami" in result["message"]

    def test_adaptive_entity_behavior_validator(self):
        """Test adaptive behavior validation for any entities"""
        any_entity = AnyEntity(
            adaptability_score=0.9,  # High adaptability
            morphing_capability={"object": 0.7},
            essence_type="chaotic",
            manifestation_forms=["adaptive_form"],
            stability_index=0.8,  # Good stability
            influence_radius=10.0,
            resonance_patterns={"human": 0.8},
            adaptive_goals=["observe", "adapt", "influence", "transform"]
        )

        entity = Entity(
            entity_id="adaptive_being",
            entity_type="any",
            entity_metadata=any_entity.dict()
        )

        # Good context alignment
        context = {"context_goals": ["observe surroundings", "adapt to situation", "influence events"]}
        result = Validator._validators["adaptive_entity_behavior"]["func"](entity, context)
        assert result["valid"] == True

        # Poor context alignment
        context = {"context_goals": ["destroy everything", "cause chaos"]}  # No alignment with entity's goals
        result = Validator._validators["adaptive_entity_behavior"]["func"](entity, context)
        assert result["valid"] == False
        assert "poor adaptation" in result["message"]

        # Unstable high-adaptability entity
        any_entity.stability_index = 0.2  # Too unstable for high adaptability
        entity.entity_metadata = any_entity.dict()
        context = {"context_goals": ["observe surroundings", "adapt to situation"]}

        result = Validator._validators["adaptive_entity_behavior"]["func"](entity, context)
        assert result["valid"] == False
        assert "too unstable" in result["message"]


if __name__ == "__main__":
    pytest.main([__file__])
