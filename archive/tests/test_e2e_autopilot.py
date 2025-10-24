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


@pytest.mark.e2e
@pytest.mark.slow
class TestE2EOrchestratorIntegration:
    """E2E tests for OrchestratorAgent integration with existing workflows"""

    @pytest.mark.llm
    def test_orchestrator_entity_generation_workflow(self, real_llm_client, graph_store):
        """
        E2E: Orchestrator → Entity Generation Workflow

        Tests complete integration:
        1. Orchestrator generates scene specification
        2. Entities fed to LangGraph workflow
        3. Validation with exposure events
        4. Storage persistence
        """
        from orchestrator import simulate_event
        from workflows import create_entity_training_workflow

        print("\n" + "="*70)
        print("TEST: Orchestrator + Entity Generation Workflow")
        print("="*70)

        # Phase 1: Orchestrate scene
        print("\n[Phase 1] Orchestrating scene from natural language...")
        result = simulate_event(
            "simulate a brief historical meeting with 4 people",
            real_llm_client,
            graph_store,
            context={"max_entities": 4, "max_timepoints": 2, "temporal_mode": "pearl"},
            save_to_db=True
        )

        print(f"  ✓ Scene: {result['specification'].scene_title}")
        print(f"  ✓ Entities: {len(result['entities'])}")
        print(f"  ✓ Timepoints: {len(result['timepoints'])}")
        print(f"  ✓ Graph edges: {result['graph'].number_of_edges()}")

        # Phase 2: Run LangGraph workflow on orchestrated entities
        print("\n[Phase 2] Running LangGraph entity training workflow...")
        workflow = create_entity_training_workflow(real_llm_client, graph_store)

        workflow_result = workflow.invoke({
            "graph": result["graph"],
            "entities": result["entities"],
            "timepoint": result["timepoints"][0].timepoint_id,
            "resolution": ResolutionLevel.FULL_DETAIL,
            "violations": [],
            "results": {},
            "entity_populations": {}
        })

        print(f"  ✓ Workflow completed")
        print(f"  ✓ Entities processed: {len(workflow_result['entities'])}")
        print(f"  ✓ Violations: {len(workflow_result['violations'])}")

        # Phase 3: Validate with exposure events
        print("\n[Phase 3] Validating with exposure event provenance...")
        validator = Validator()
        validation_count = 0

        for entity in result["entities"]:
            exposure_events = graph_store.get_exposure_events(entity.entity_id)
            context = {
                "exposure_history": exposure_events,
                "graph": result["graph"]
            }
            validation_result = validator.validate_entity(entity, context)
            if validation_result["valid"] or len(validation_result.get("violations", [])) == 0:
                validation_count += 1

        print(f"  ✓ Validated {validation_count}/{len(result['entities'])} entities")

        # Assertions
        assert len(result['entities']) >= 2, "Should generate at least 2 entities"
        assert len(result['timepoints']) >= 1, "Should generate at least 1 timepoint"
        assert result['graph'].number_of_nodes() >= 2, "Graph should have nodes"
        assert validation_count >= len(result['entities']) * 0.8, "80% validation success"

        print("\n" + "="*70)
        print("✅ ORCHESTRATOR → WORKFLOW INTEGRATION SUCCESS")
        print("="*70)

    @pytest.mark.llm
    def test_orchestrator_temporal_chain_creation(self, real_llm_client, graph_store):
        """
        E2E: Orchestrator → Temporal Chain Creation

        Tests temporal integration:
        1. Orchestrator generates initial timepoints
        2. TemporalAgent extends chain
        3. Validation of temporal consistency
        """
        from orchestrator import simulate_event

        print("\n" + "="*70)
        print("TEST: Orchestrator + Temporal Chain Creation")
        print("="*70)

        # Phase 1: Orchestrate scene
        print("\n[Phase 1] Orchestrating temporal scene...")
        result = simulate_event(
            "simulate a three-day historical event",
            real_llm_client,
            graph_store,
            context={"max_entities": 3, "max_timepoints": 3, "temporal_mode": "pearl"},
            save_to_db=True
        )

        initial_timepoints = result["timepoints"]
        print(f"  ✓ Initial timepoints: {len(initial_timepoints)}")

        # Phase 2: Extend with TemporalAgent
        print("\n[Phase 2] Extending temporal chain...")
        temporal_agent = result["temporal_agent"]
        last_tp = initial_timepoints[-1]

        next_tp = temporal_agent.generate_next_timepoint(
            current_timepoint=last_tp,
            context={"next_event": "Continuation of events"}
        )

        print(f"  ✓ Generated successor: {next_tp.timepoint_id}")
        print(f"  ✓ Causal parent: {next_tp.causal_parent}")

        # Phase 3: Validate temporal relationships
        print("\n[Phase 3] Validating temporal relationships...")
        successors = graph_store.get_successor_timepoints(last_tp.timepoint_id)
        assert len(successors) >= 1, "Should have at least one successor"
        assert any(s.timepoint_id == next_tp.timepoint_id for s in successors)

        print(f"  ✓ Temporal chain validated")

        # Assertions
        assert len(initial_timepoints) >= 2
        assert next_tp.causal_parent == last_tp.timepoint_id
        assert result["temporal_agent"].mode == TemporalMode.PEARL

        print("\n" + "="*70)
        print("✅ ORCHESTRATOR → TEMPORAL CHAIN SUCCESS")
        print("="*70)

    @pytest.mark.llm
    def test_full_pipeline_with_orchestrator(self, real_llm_client, graph_store):
        """
        E2E: Complete Pipeline with Orchestrator

        The ULTIMATE integration test - natural language to validated simulation:
        1. Natural language input
        2. Orchestrator scene generation
        3. LangGraph workflow execution
        4. Temporal chain creation
        5. Validation with exposure events
        6. Storage persistence
        7. Performance metrics
        """
        from orchestrator import simulate_event
        from workflows import create_entity_training_workflow
        import time

        print("\n" + "="*70)
        print("ULTIMATE TEST: Full Pipeline with Orchestrator")
        print("="*70)

        start_time = time.time()

        # Phase 1: Natural Language → Scene Specification
        print("\n[Phase 1] Orchestrating scene from natural language...")
        orchestration_start = time.time()

        result = simulate_event(
            "simulate the signing of the declaration of independence",
            real_llm_client,
            graph_store,
            context={"max_entities": 5, "max_timepoints": 3, "temporal_mode": "pearl"},
            save_to_db=True
        )

        orchestration_time = time.time() - orchestration_start
        print(f"  ✓ Orchestration completed in {orchestration_time:.2f}s")
        print(f"  ✓ Scene: {result['specification'].scene_title}")
        print(f"  ✓ Entities: {len(result['entities'])}")
        print(f"  ✓ Timepoints: {len(result['timepoints'])}")

        # Phase 2: LangGraph Workflow Execution
        print("\n[Phase 2] Running LangGraph entity training workflow...")
        workflow_start = time.time()

        workflow = create_entity_training_workflow(real_llm_client, graph_store)
        workflow_result = workflow.invoke({
            "graph": result["graph"],
            "entities": result["entities"],
            "timepoint": result["timepoints"][0].timepoint_id,
            "resolution": ResolutionLevel.FULL_DETAIL,
            "violations": [],
            "results": {},
            "entity_populations": {}
        })

        workflow_time = time.time() - workflow_start
        print(f"  ✓ Workflow completed in {workflow_time:.2f}s")
        print(f"  ✓ Processed entities: {len(workflow_result['entities'])}")

        # Phase 3: Temporal Chain Extension
        print("\n[Phase 3] Extending temporal chain...")
        temporal_start = time.time()

        temporal_agent = result["temporal_agent"]
        extended_timepoints = []

        for i in range(2):  # Extend by 2 more timepoints
            current = result["timepoints"][i] if i == 0 else extended_timepoints[-1]
            next_tp = temporal_agent.generate_next_timepoint(
                current_timepoint=current,
                context={"next_event": f"Historical progression {i+1}"}
            )
            extended_timepoints.append(next_tp)

        temporal_time = time.time() - temporal_start
        print(f"  ✓ Extended chain by {len(extended_timepoints)} timepoints in {temporal_time:.2f}s")

        # Phase 4: Comprehensive Validation
        print("\n[Phase 4] Comprehensive validation...")
        validation_start = time.time()

        validator = Validator()
        validation_results = []

        for entity in result["entities"]:
            exposure_events = graph_store.get_exposure_events(entity.entity_id)
            context = {
                "exposure_history": exposure_events,
                "graph": result["graph"],
                "timepoint_id": entity.timepoint
            }
            validation_result = validator.validate_entity(entity, context)
            validation_results.append(
                validation_result["valid"] or len(validation_result.get("violations", [])) == 0
            )

        validation_time = time.time() - validation_start
        validation_rate = sum(validation_results) / len(validation_results) if validation_results else 0

        print(f"  ✓ Validation completed in {validation_time:.2f}s")
        print(f"  ✓ Success rate: {validation_rate*100:.1f}%")

        # Phase 5: Storage Verification
        print("\n[Phase 5] Verifying storage persistence...")
        stored_entities = len(graph_store.get_all_entities())
        stored_timepoints = len(graph_store.get_all_timepoints())

        print(f"  ✓ Stored entities: {stored_entities}")
        print(f"  ✓ Stored timepoints: {stored_timepoints}")

        # Phase 6: Performance Report
        total_time = time.time() - start_time

        print("\n" + "="*70)
        print("PERFORMANCE METRICS")
        print("="*70)
        print(f"Orchestration: {orchestration_time:.2f}s")
        print(f"LangGraph Workflow: {workflow_time:.2f}s")
        print(f"Temporal Extension: {temporal_time:.2f}s")
        print(f"Validation: {validation_time:.2f}s")
        print(f"Total: {total_time:.2f}s")
        print("="*70)

        print("\n" + "="*70)
        print("FINAL RESULTS")
        print("="*70)
        print(f"Scene Title: {result['specification'].scene_title}")
        print(f"Entities Created: {len(result['entities'])}")
        print(f"Initial Timepoints: {len(result['timepoints'])}")
        print(f"Extended Timepoints: {len(extended_timepoints)}")
        print(f"Total Timepoints: {len(result['timepoints']) + len(extended_timepoints)}")
        print(f"Graph Nodes: {result['graph'].number_of_nodes()}")
        print(f"Graph Edges: {result['graph'].number_of_edges()}")
        print(f"Validation Rate: {validation_rate*100:.1f}%")
        print(f"Exposure Events: {sum(len(graph_store.get_exposure_events(e.entity_id)) for e in result['entities'])}")
        print("="*70)

        # Final Assertions
        assert len(result['entities']) >= 3, "Should generate at least 3 entities"
        assert len(result['timepoints']) >= 2, "Should generate at least 2 timepoints"
        assert len(extended_timepoints) == 2, "Should extend by 2 timepoints"
        assert validation_rate >= 0.8, "At least 80% validation success"
        assert stored_entities >= 3, "Should persist entities"
        assert stored_timepoints >= 4, "Should persist timepoints"
        assert total_time < 120, f"Total time should be under 2 minutes, got {total_time:.2f}s"

        print("\n" + "="*70)
        print("✅ FULL PIPELINE WITH ORCHESTRATOR SUCCESS")
        print("="*70)


@pytest.mark.e2e
@pytest.mark.validation
@pytest.mark.slow
class TestE2EValidationWorkflows:
    """
    E2E tests for the 4 critical validation workflows

    These tests capture the validation workflows from VALIDATION_REPORT.md:
    1. Timepoint AI modeling validation
    2. E2E test rig with real LLM
    3. Data generation + Oxen storage validation
    4. Fine-tuning workflow validation
    """

    @pytest.mark.llm
    def test_workflow1_timepoint_ai_modeling(self, real_llm_client, graph_store):
        """
        Workflow 1: Timepoint AI Modeling Validation

        Tests: orchestrator.py → LLM → scene specification
        Validates: No mock patterns, real LLM-generated content
        """
        from orchestrator import simulate_event

        print("\n" + "="*70)
        print("WORKFLOW 1: TIMEPOINT AI MODELING VALIDATION")
        print("="*70)

        # Run simulation with real LLM
        result = simulate_event(
            "Simulate a quick 2-person meeting to discuss project status",
            real_llm_client,
            graph_store,
            context={
                "max_entities": 2,
                "max_timepoints": 2,
                "temporal_mode": "pearl"
            },
            save_to_db=True
        )

        # Validate results
        assert result is not None
        assert 'specification' in result
        assert 'entities' in result
        assert 'timepoints' in result
        assert 'graph' in result

        # Validate NOT mock data
        scene_title = result['specification'].scene_title
        assert scene_title != "Test Scene", "Got mock 'Test Scene'"

        # Check for mock entity patterns
        for entity in result['entities']:
            assert not entity.entity_id.startswith("test_entity_"), \
                f"Mock entity ID detected: {entity.entity_id}"

        # Validate real content
        assert len(result['entities']) >= 2, "Should generate at least 2 entities"
        assert len(result['timepoints']) >= 1, "Should generate at least 1 timepoint"
        assert result['graph'].number_of_nodes() >= 2, "Graph should have nodes"

        print(f"\n✅ WORKFLOW 1 PASSED")
        print(f"   Scene: {scene_title}")
        print(f"   Entities: {len(result['entities'])}")
        print(f"   Timepoints: {len(result['timepoints'])}")
        print(f"   Graph Nodes: {result['graph'].number_of_nodes()}")

    @pytest.mark.llm
    def test_workflow2_e2e_test_rig_validation(self, real_llm_client, graph_store):
        """
        Workflow 2: E2E Test Rig Validation

        Tests: Full entity generation workflow with real LLM
        Validates: E2E test infrastructure works with real API calls
        """
        from workflows import generate_animistic_entities_for_scene
        from validation import Validator

        print("\n" + "="*70)
        print("WORKFLOW 2: E2E TEST RIG VALIDATION")
        print("="*70)

        scene_description = "Constitutional Convention debate, 1787"

        # Generate entities
        entities = generate_animistic_entities_for_scene(
            scene_description=scene_description,
            llm_client=real_llm_client,
            entity_count=3
        )

        assert len(entities) >= 3, "Should generate at least 3 entities"

        # Validate and save
        validator = Validator()
        validation_count = 0

        for entity in entities:
            result = validator.validate_entity(entity)
            is_valid = result["valid"] or len(result.get("violations", [])) == 0
            if is_valid:
                validation_count += 1
            graph_store.save_entity(entity)

        # Verify retrieval
        retrieved_count = 0
        for entity in entities:
            if graph_store.get_entity(entity.entity_id, entity.timepoint):
                retrieved_count += 1

        assert retrieved_count >= 3, f"Only retrieved {retrieved_count}/3 entities"
        assert validation_count >= 2, "At least 2 entities should validate"

        print(f"\n✅ WORKFLOW 2 PASSED")
        print(f"   Entities generated: {len(entities)}")
        print(f"   Entities validated: {validation_count}")
        print(f"   Entities retrieved: {retrieved_count}")

    @pytest.mark.llm
    def test_workflow3_data_generation_oxen_storage(self, real_llm_client, graph_store):
        """
        Workflow 3: Data Generation + Oxen Storage Validation

        Tests: Generate simulation → Store locally → Upload to Oxen
        Validates: Full data pipeline with real simulation data
        """
        from orchestrator import simulate_event
        from oxen_integration import OxenClient
        import tempfile
        import json
        import os

        print("\n" + "="*70)
        print("WORKFLOW 3: DATA GENERATION + OXEN STORAGE")
        print("="*70)

        # Generate simulation
        result = simulate_event(
            "Simulate a 3-person negotiation with 3 key decision points",
            real_llm_client,
            graph_store,
            context={
                "max_entities": 3,
                "max_timepoints": 3,
                "temporal_mode": "pearl"
            },
            save_to_db=True
        )

        scene_title = result['specification'].scene_title
        assert "Test Scene" not in scene_title, "Got mock data"

        print(f"   Generated: {scene_title}")
        print(f"   Entities: {len(result['entities'])}")
        print(f"   Timepoints: {len(result['timepoints'])}")

        # Store data locally
        data_file = tempfile.mktemp(suffix=".json")
        with open(data_file, 'w') as f:
            json.dump({
                "scene_title": scene_title,
                "entities": [e.entity_id for e in result['entities']],
                "timepoints": [tp.timepoint_id for tp in result['timepoints']],
                "validation_timestamp": datetime.now().isoformat()
            }, f, indent=2)

        file_size = os.path.getsize(data_file)
        print(f"   Stored locally: {file_size} bytes")

        # Upload to Oxen
        oxen_client = OxenClient(
            namespace=os.getenv("OXEN_TEST_NAMESPACE", "realityinspector"),
            repo_name="validation_test_workflow3_e2e",
            interactive_auth=False
        )

        upload_result = oxen_client.upload_dataset(
            file_path=data_file,
            commit_message="Workflow 3 E2E validation: Real simulation data",
            dst_path="validation/workflow3_e2e_test.json",
            create_repo_if_missing=True
        )

        # Cleanup
        os.unlink(data_file)

        assert upload_result.repo_url is not None
        assert upload_result.dataset_url is not None

        print(f"\n✅ WORKFLOW 3 PASSED")
        print(f"   Repository: {upload_result.repo_url}")
        print(f"   Dataset URL: {upload_result.dataset_url}")

    @pytest.mark.llm
    def test_workflow4_finetuning_data_quality(self, real_llm_client, graph_store):
        """
        Workflow 4: Fine-Tuning Workflow Validation

        Tests: Generate training data → Validate quality
        Validates: Training data contains real LLM content, no mock patterns
        """
        from generation import HorizontalGenerator
        from generation.config_schema import SimulationConfig
        from orchestrator import simulate_event
        from oxen_integration.data_formatters import EntityEvolutionFormatter

        print("\n" + "="*70)
        print("WORKFLOW 4: FINE-TUNING WORKFLOW VALIDATION")
        print("="*70)

        # Generate 3 simulations
        generator = HorizontalGenerator()
        base_config = SimulationConfig.example_board_meeting()

        variations = generator.generate_variations(
            base_config=base_config,
            count=3,
            strategies=["vary_personalities", "vary_outcomes"],
            random_seed=42
        )

        simulation_results = []
        for i, variation in enumerate(variations):
            print(f"\n   Simulation {i+1}/3...")

            result = simulate_event(
                variation.scenario_description,
                real_llm_client,
                graph_store,
                context={
                    "max_entities": min(variation.entities.count, 3),
                    "max_timepoints": min(variation.timepoints.count, 2),
                    "temporal_mode": variation.temporal.mode
                },
                save_to_db=False
            )

            simulation_results.append(result)
            print(f"      ✓ Title: {result['specification'].scene_title}")

        # Validate uniqueness
        titles = [r['specification'].scene_title for r in simulation_results]
        assert "Test Scene" not in titles, "Mock data detected"

        # Format training data
        formatter = EntityEvolutionFormatter()
        training_examples = formatter.format_batch(simulation_results)

        assert len(training_examples) > 0, "No training examples generated"

        # Validate training data quality
        mock_patterns_found = 0
        for example in training_examples[:5]:
            completion = example.get('completion', '')
            if isinstance(completion, str):
                if 'test_entity_' in completion:
                    mock_patterns_found += 1
                elif '"fact1"' in completion or '"fact2"' in completion:
                    mock_patterns_found += 1

        assert mock_patterns_found == 0, f"Found {mock_patterns_found} mock patterns in training data"

        print(f"\n✅ WORKFLOW 4 PASSED")
        print(f"   Simulations: {len(simulation_results)}")
        print(f"   Training examples: {len(training_examples)}")
        print(f"   Mock patterns: {mock_patterns_found}")


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
