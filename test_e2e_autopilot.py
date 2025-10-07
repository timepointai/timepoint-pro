#!/usr/bin/env python3
"""
test_e2e_autopilot.py - End-to-End Autopilot Test Suite

Comprehensive E2E tests that validate the entire Timepoint-Daedalus system
from end to end, including:

- Full workflow execution with real LLM integration
- Multi-component system validation
- Performance and reliability testing
- Quality assurance and safety checks

This replaces the old autopilot.py script with a proper pytest-based E2E test suite.
"""
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pytest

from schemas import (
    Entity, Timepoint, ResolutionLevel, TemporalMode,
    AnimalEntity, BuildingEntity, AbstractEntity, KamiEntity, AIEntity
)
from llm_v2 import LLMClient
from workflows import (
    create_animistic_entity, generate_animistic_entities_for_scene,
    TemporalAgent
)
from storage import GraphStore
from validation import Validator
from ai_entity_service import AIEntityService, AIEntityRunner


@pytest.mark.e2e
@pytest.mark.slow
class TestE2EEntityGeneration:
    """E2E tests for complete entity generation workflows"""

    @pytest.mark.llm
    def test_full_entity_generation_workflow(self, real_llm_client, graph_store):
        """
        E2E: Complete entity generation workflow with real LLM

        Tests the full pipeline:
        1. Create base entity
        2. Populate with LLM
        3. Save to database
        4. Validate consistency
        5. Verify retrieval
        """
        # Step 1: Create base entity and timepoint
        timepoint = Timepoint(
            timepoint_id="e2e_tp_001",
            timestamp=datetime(1789, 4, 30),
            event_description="Washington's Presidential Inauguration",
            entities_present=["washington", "hamilton", "crowd"],
            resolution_level=ResolutionLevel.FULL_DETAIL
        )
        graph_store.save_timepoint(timepoint)

        entity = Entity(
            entity_id="washington",
            entity_type="human",
            timepoint="e2e_tp_001",
            resolution_level=ResolutionLevel.FULL_DETAIL,
            entity_metadata={"role": "president", "historical": True}
        )

        # Step 2: Populate with LLM
        start_time = time.time()
        populated_entity = real_llm_client.populate_entity(
            entity_schema=entity,
            context={
                "timepoint": timepoint.timestamp.isoformat(),
                "event": timepoint.event_description,
                "role": "first president of the United States"
            }
        )
        llm_time = time.time() - start_time

        # Step 3: Convert EntityPopulation to Entity and save to database
        from schemas import entity_population_to_entity
        entity_to_save = entity_population_to_entity(
            population=populated_entity,
            entity_id="washington",
            entity_type="human",
            timepoint="e2e_tp_001",
            resolution_level=ResolutionLevel.FULL_DETAIL
        )
        graph_store.save_entity(entity_to_save)

        # Step 4: Validate (validate the converted entity, not the EntityPopulation)
        validator = Validator()
        validation_result = validator.validate_entity(entity_to_save)
        assert validation_result["valid"] or len(validation_result["violations"]) == 0, \
            f"Entity validation failed: {validation_result.get('violations', [])}"

        # Step 5: Verify retrieval
        retrieved = graph_store.get_entity("washington", "e2e_tp_001")
        assert retrieved is not None
        assert retrieved.entity_id == "washington"
        # Knowledge state is stored in cognitive_tensor
        assert 'cognitive_tensor' in retrieved.entity_metadata
        cognitive = retrieved.entity_metadata.get('cognitive_tensor', {})
        assert 'knowledge_state' in cognitive

        # Performance assertion
        assert llm_time < 30, f"LLM population took too long: {llm_time:.2f}s"

        print(f"\n✅ Full workflow completed in {llm_time:.2f}s")

    @pytest.mark.llm
    def test_multi_entity_scene_generation(self, real_llm_client, graph_store):
        """
        E2E: Multi-entity scene generation with LLM

        Tests generating multiple entities for a scene with proper relationships
        """
        scene_description = "Constitutional Convention debate, 1787"

        # Generate entities for scene
        entities = generate_animistic_entities_for_scene(
            scene_description=scene_description,
            llm_client=real_llm_client,
            entity_count=5
        )

        assert len(entities) == 5, "Should generate 5 entities"

        # Validate and save all entities
        for entity in entities:
            validator = Validator()
            result = validator.validate_entity(entity)
            assert result["valid"] or len(result.get("violations", [])) == 0, \
                f"Entity {entity.entity_id} validation failed: {result.get('violations', [])}"

            graph_store.save_entity(entity)

        # Verify all entities can be retrieved
        retrieved_count = 0
        for entity in entities:
            retrieved = graph_store.get_entity(entity.entity_id, entity.timepoint)
            if retrieved:
                retrieved_count += 1

        assert retrieved_count == 5, f"Only retrieved {retrieved_count}/5 entities"

        print(f"\n✅ Generated and validated {len(entities)} entities")


@pytest.mark.e2e
@pytest.mark.slow
class TestE2ETemporalWorkflows:
    """E2E tests for temporal causality workflows"""

    @pytest.mark.llm
    @pytest.mark.temporal
    def test_full_temporal_chain_creation(self, real_llm_client, graph_store):
        """
        E2E: Complete temporal chain creation and navigation

        Tests:
        1. Create initial timepoint
        2. Generate successor timepoints
        3. Validate temporal relationships
        4. Navigate forward and backward in time
        """
        # Create initial timepoint
        t0 = Timepoint(
            timepoint_id="t0_e2e",
            timestamp=datetime(1776, 7, 4),
            event_description="Declaration of Independence signing",
            entities_present=["jefferson", "franklin", "adams"],
            resolution_level=ResolutionLevel.FULL_DETAIL
        )
        graph_store.save_timepoint(t0)

        # Create temporal agent
        agent = TemporalAgent(store=graph_store, llm_client=real_llm_client)

        # Generate successor timepoint
        t1 = agent.generate_next_timepoint(
            current_timepoint=t0,
            context={"next_event": "Ratification debates"}
        )

        assert t1 is not None
        assert t1.timepoint_id != t0.timepoint_id
        graph_store.save_timepoint(t1)

        # Validate temporal relationship
        successors = graph_store.get_successor_timepoints(t0.timepoint_id)
        assert len(successors) >= 1
        assert any(s.timepoint_id == t1.timepoint_id for s in successors)

        # Navigate backward
        predecessors = graph_store.get_predecessor_timepoints(t1.timepoint_id)
        assert any(p.timepoint_id == t0.timepoint_id for p in predecessors)

        print(f"\n✅ Temporal chain: {t0.timepoint_id} -> {t1.timepoint_id}")

    @pytest.mark.integration
    @pytest.mark.temporal
    def test_modal_temporal_causality(self, llm_client, graph_store):
        """
        E2E: Modal temporal causality across multiple timepoints

        Tests different temporal modes (actual, possible, necessary)
        """
        from test_modal_temporal_causality import ModalTemporalCausalitySystem

        system = ModalTemporalCausalitySystem(store=graph_store, llm_client=llm_client)

        # Create base reality
        base_tp = Timepoint(
            timepoint_id="base_modal",
            timestamp=datetime(1800, 1, 1),
            event_description="Base timeline event",
            entities_present=["entity_a"],
            resolution_level=ResolutionLevel.TENSOR_ONLY
        )
        graph_store.save_timepoint(base_tp)

        # Test different modal branches using actual TemporalMode values
        pearl_branch = system.create_modal_branch(base_tp, TemporalMode.PEARL)
        branching_branch = system.create_modal_branch(base_tp, TemporalMode.BRANCHING)
        cyclical_branch = system.create_modal_branch(base_tp, TemporalMode.CYCLICAL)

        # Verify branches were created (they're Timepoint objects, not Timeline objects)
        assert pearl_branch.timepoint_id.endswith(f"_modal_{TemporalMode.PEARL.value}")
        assert branching_branch.timepoint_id.endswith(f"_modal_{TemporalMode.BRANCHING.value}")
        assert cyclical_branch.timepoint_id.endswith(f"_modal_{TemporalMode.CYCLICAL.value}")

        # Validate modal relationships
        all_branches = [pearl_branch, branching_branch, cyclical_branch]
        for branch in all_branches:
            assert branch.timestamp == base_tp.timestamp  # Same moment in time
            assert base_tp.timepoint_id in branch.timepoint_id  # Contains base ID

        print(f"\n✅ Created {len(all_branches)} modal branches")


@pytest.mark.e2e
@pytest.mark.slow
class TestE2EAIEntityService:
    """E2E tests for AI entity service workflows"""

    @pytest.mark.llm
    @pytest.mark.ai_entity
    def test_ai_entity_full_lifecycle(self, real_llm_client, graph_store):
        """
        E2E: AI entity complete lifecycle

        Tests:
        1. AI entity creation
        2. Training and learning
        3. Interaction and response generation
        4. State persistence
        5. Retrieval and continuation
        """
        service = AIEntityService(store=graph_store, llm_client=real_llm_client)

        # Step 1: Create AI entity (Entity with AIEntity configuration in metadata)
        ai_config = AIEntity(
            model_name="gpt-3.5-turbo",
            system_prompt="You are a historical advisor specializing in the American Revolution.",
            temperature=0.7
        )

        ai_entity = Entity(
            entity_id="ai_assistant_e2e",
            entity_type="ai_agent",
            timepoint="e2e_ai_tp",
            resolution_level=ResolutionLevel.FULL_DETAIL,
            entity_metadata={
                "role": "historical_advisor",
                "specialization": "american_revolution",
                "ai_config": ai_config.model_dump()
            }
        )
        service.register_entity(ai_entity)

        # Step 2: Train with context
        training_data = [
            {"query": "What happened in 1776?", "response": "Declaration of Independence"},
            {"query": "Who was George Washington?", "response": "First president and general"}
        ]
        service.train_entity(ai_entity.entity_id, training_data)

        # Step 3: Generate response
        response = service.generate_response(
            entity_id=ai_entity.entity_id,
            query="Tell me about the American Revolution"
        )
        assert response is not None
        assert len(response) > 10, "Response should be substantial"

        # Step 4: Persist state
        service.save_entity_state(ai_entity.entity_id)

        # Step 5: Retrieve and verify
        retrieved = service.get_entity(ai_entity.entity_id)
        assert retrieved is not None
        assert retrieved.entity_id == ai_entity.entity_id

        print(f"\n✅ AI entity lifecycle completed: {ai_entity.entity_id}")


@pytest.mark.e2e
@pytest.mark.performance
class TestE2ESystemPerformance:
    """E2E performance and scalability tests"""

    def test_bulk_entity_creation_performance(self, llm_client, graph_store):
        """
        E2E: Bulk entity creation performance

        Tests system performance with many entities
        """
        entity_count = 100
        start_time = time.time()

        entities = []
        for i in range(entity_count):
            entity = Entity(
                entity_id=f"bulk_entity_{i:03d}",
                entity_type="test",
                timepoint="bulk_tp",
                resolution_level=ResolutionLevel.TENSOR_ONLY,
                entity_metadata={"index": i}
            )
            graph_store.save_entity(entity)
            entities.append(entity)

        creation_time = time.time() - start_time

        # Verify retrieval performance
        retrieval_start = time.time()
        retrieved_count = 0
        for entity in entities:
            if graph_store.get_entity(entity.entity_id, entity.timepoint):
                retrieved_count += 1
        retrieval_time = time.time() - retrieval_start

        # Performance assertions
        assert retrieved_count == entity_count
        assert creation_time < 10, f"Bulk creation too slow: {creation_time:.2f}s"
        assert retrieval_time < 5, f"Bulk retrieval too slow: {retrieval_time:.2f}s"

        avg_creation = (creation_time / entity_count) * 1000
        avg_retrieval = (retrieval_time / entity_count) * 1000

        print(f"\n✅ Performance metrics:")
        print(f"   Creation: {avg_creation:.2f}ms per entity")
        print(f"   Retrieval: {avg_retrieval:.2f}ms per entity")

    @pytest.mark.slow
    def test_concurrent_timepoint_access(self, llm_client, graph_store):
        """
        E2E: Concurrent access to timepoints

        Tests system behavior under concurrent load
        """
        import threading

        timepoint = Timepoint(
            timepoint_id="concurrent_tp",
            timestamp=datetime(2000, 1, 1),
            event_description="Concurrent access test",
            entities_present=[],
            resolution_level=ResolutionLevel.TENSOR_ONLY
        )
        graph_store.save_timepoint(timepoint)

        errors = []
        results = []

        def access_timepoint(thread_id: int):
            try:
                for i in range(10):
                    tp = graph_store.get_timepoint("concurrent_tp")
                    if tp:
                        results.append((thread_id, i))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Run concurrent access
        threads = []
        for i in range(5):
            t = threading.Thread(target=access_timepoint, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Validate
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 50, f"Expected 50 accesses, got {len(results)}"

        print(f"\n✅ Concurrent access test: {len(results)} successful accesses")


@pytest.mark.e2e
@pytest.mark.safety
@pytest.mark.validation
class TestE2ESystemValidation:
    """E2E validation and safety tests"""

    def test_end_to_end_data_consistency(self, llm_client, graph_store):
        """
        E2E: Complete data consistency validation

        Tests data integrity across the entire system
        """
        validator = Validator()

        # Create interconnected data
        timepoint = Timepoint(
            timepoint_id="consistency_tp",
            timestamp=datetime(1800, 1, 1),
            event_description="Consistency test",
            entities_present=["entity_1", "entity_2"],
            resolution_level=ResolutionLevel.FULL_DETAIL
        )
        graph_store.save_timepoint(timepoint)

        entities = []
        for i in range(1, 3):
            entity = Entity(
                entity_id=f"entity_{i}",
                entity_type="test",
                timepoint="consistency_tp",
                resolution_level=ResolutionLevel.FULL_DETAIL,
                entity_metadata={"related_to": f"entity_{3-i}"}
            )
            result = validator.validate_entity(entity)
            assert result["valid"] or len(result.get("violations", [])) == 0, \
                f"Entity {entity.entity_id} validation failed: {result.get('violations', [])}"
            graph_store.save_entity(entity)
            entities.append(entity)

        # Validate relationships
        for entity in entities:
            related_id = entity.entity_metadata["related_to"]
            related = graph_store.get_entity(related_id, "consistency_tp")
            assert related is not None, f"Missing related entity: {related_id}"

        print(f"\n✅ Data consistency validated across {len(entities)} entities")

    @pytest.mark.llm
    def test_llm_safety_and_validation(self, real_llm_client, graph_store):
        """
        E2E: LLM response safety and validation

        Tests that LLM-generated content meets safety and quality standards
        """
        validator = Validator()

        # Generate entity with LLM
        entity = Entity(
            entity_id="safety_test_entity",
            entity_type="human",
            timepoint="safety_tp",
            resolution_level=ResolutionLevel.FULL_DETAIL,
            entity_metadata={"role": "test_subject"}
        )

        populated_entity_pop = real_llm_client.populate_entity(
            entity_schema=entity,
            context={"test": "safety_validation"}
        )

        # Convert to Entity for validation
        from schemas import entity_population_to_entity
        populated = entity_population_to_entity(
            population=populated_entity_pop,
            entity_id="safety_test_entity",
            entity_type="human",
            timepoint="safety_tp",
            resolution_level=ResolutionLevel.FULL_DETAIL
        )

        # Validate generated content
        result = validator.validate_entity(populated)
        assert result["valid"] or len(result.get("violations", [])) == 0, \
            f"LLM-generated entity failed validation: {result.get('violations', [])}"

        # Check for required safety attributes
        cognitive_tensor = populated.entity_metadata.get('cognitive_tensor', {})
        assert 'knowledge_state' in cognitive_tensor
        assert len(cognitive_tensor['knowledge_state']) > 0

        print(f"\n✅ LLM safety validation passed")


@pytest.mark.e2e
class TestE2ESystemIntegration:
    """E2E integration tests for complete system workflows"""

    @pytest.mark.slow
    @pytest.mark.llm
    def test_complete_simulation_workflow(self, real_llm_client, graph_store):
        """
        E2E: Complete simulation workflow

        The ultimate integration test - runs a full simulation from start to finish:
        1. Initialize timepoint
        2. Generate entities
        3. Create temporal progression
        4. Validate all components
        5. Generate final report
        """
        print("\n" + "="*70)
        print("STARTING COMPLETE SIMULATION WORKFLOW")
        print("="*70)

        # Phase 1: Initialize
        print("\n[Phase 1] Initializing simulation...")
        initial_tp = Timepoint(
            timepoint_id="simulation_t0",
            timestamp=datetime(1776, 7, 4),
            event_description="Declaration of Independence",
            entities_present=["jefferson", "franklin"],
            resolution_level=ResolutionLevel.FULL_DETAIL
        )
        graph_store.save_timepoint(initial_tp)
        print(f"  ✓ Created initial timepoint: {initial_tp.timepoint_id}")

        # Phase 2: Generate entities
        print("\n[Phase 2] Generating entities...")
        entities = generate_animistic_entities_for_scene(
            scene_description=initial_tp.event_description,
            llm_client=real_llm_client,
            entity_count=3
        )
        for entity in entities:
            graph_store.save_entity(entity)
        print(f"  ✓ Generated {len(entities)} entities")

        # Phase 3: Temporal progression
        print("\n[Phase 3] Creating temporal progression...")
        agent = TemporalAgent(store=graph_store, llm_client=real_llm_client)
        next_tp = agent.generate_next_timepoint(
            current_timepoint=initial_tp,
            context={"progression": "historical_sequence"}
        )
        graph_store.save_timepoint(next_tp)
        print(f"  ✓ Generated next timepoint: {next_tp.timepoint_id}")

        # Phase 4: Validate
        print("\n[Phase 4] Validating system state...")
        validator = Validator()
        validation_results = []
        for entity in entities:
            result = validator.validate_entity(entity)
            is_valid = result["valid"] or len(result.get("violations", [])) == 0
            validation_results.append(is_valid)
        print(f"  ✓ Validated {sum(validation_results)}/{len(validation_results)} entities")

        # Phase 5: Final report
        print("\n[Phase 5] Generating final report...")
        total_timepoints = len(graph_store.get_all_timepoints())
        total_entities = len(entities)

        report = {
            "timepoints_created": total_timepoints,
            "entities_created": total_entities,
            "validation_success_rate": sum(validation_results) / len(validation_results),
            "temporal_chain_length": 2
        }

        print("\n" + "="*70)
        print("SIMULATION COMPLETE")
        print("="*70)
        print(f"Timepoints: {report['timepoints_created']}")
        print(f"Entities: {report['entities_created']}")
        print(f"Validation Rate: {report['validation_success_rate']*100:.1f}%")
        print(f"Temporal Chain: {report['temporal_chain_length']} links")
        print("="*70)

        # Final assertions
        assert report['timepoints_created'] >= 2
        assert report['entities_created'] >= 3
        assert report['validation_success_rate'] == 1.0
        assert report['temporal_chain_length'] >= 2


if __name__ == "__main__":
    """
    Run E2E tests directly

    Usage:
        python test_e2e_autopilot.py              # Run all E2E tests (mock LLM)
        python test_e2e_autopilot.py --real-llm   # Run with real LLM
    """
    import sys

    args = sys.argv[1:]
    pytest_args = [__file__, "-v", "-m", "e2e"] + args

    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)
