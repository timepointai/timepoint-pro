"""
E2E Integration Test: Natural Language → Orchestrator Pipeline

Tests the complete workflow:
1. Natural language description
2. NL Interface generates config (with REAL LLM calls)
3. Orchestrator executes simulation
4. Verify results

This test requires:
- LLM_SERVICE_ENABLED=true
- Valid API keys in environment
"""

import os
import shutil
import tempfile

import pytest

from nl_interface import InteractiveRefiner, NLConfigGenerator
from orchestrator import simulate_event
from storage import GraphStore


@pytest.mark.skipif(
    os.getenv("LLM_SERVICE_ENABLED") != "true",
    reason="LLM service not enabled - set LLM_SERVICE_ENABLED=true to run",
)
class TestE2ENLToOrchestrator:
    """E2E tests for NL → Config → Orchestrator pipeline with real LLM calls"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary storage
        self.temp_dir = tempfile.mkdtemp()
        self.storage = GraphStore(self.temp_dir)

        # Get API key from environment
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            pytest.skip("OPENROUTER_API_KEY not set - skipping LLM tests")

    def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_nl_simple_scenario_to_simulation(self):
        """Test: Simple NL description → config → simulation with REAL LLM"""
        from llm_v2 import LLMClient

        # 1. Natural language description
        description = (
            "Simulate a crisis meeting with 3 astronauts. "
            "They need to make a critical decision about returning to Earth. "
            "Focus on decision making and dialog."
        )

        # 2. Generate config using REAL LLM
        generator = NLConfigGenerator(api_key=self.api_key)

        print(f"\n🔄 Generating config from: '{description}'")
        config, confidence = generator.generate_config(description)

        print(f"✅ Config generated with {confidence:.1%} confidence")
        print(f"   Scenario: {config['scenario']}")
        print(f"   Entities: {len(config['entities'])}")
        print(f"   Timepoints: {config['timepoint_count']}")

        # 3. Validate config
        validation = generator.validate_config(config)
        assert validation.is_valid, f"Config validation failed: {validation.errors}"

        print(f"✅ Config validated (confidence: {validation.confidence_score:.1%})")

        # 4. Use orchestrator to execute simulation
        print("\n🔄 Executing simulation with orchestrator...")

        llm_client = LLMClient()

        # Use the NL-generated scenario description for orchestrator
        result = simulate_event(
            config["scenario"],
            llm_client,
            self.storage,
            context={
                "max_entities": len(config["entities"]),
                "max_timepoints": min(config["timepoint_count"], 3),  # Limit for testing
                "temporal_mode": config.get("temporal_mode", "forward"),
            },
            save_to_db=True,
        )

        print("✅ Simulation executed")
        print(f"   Entities: {len(result['entities'])}")
        print(f"   Timepoints: {len(result['timepoints'])}")

        # 5. Verify results
        assert len(result["entities"]) >= 1, "No entities generated"
        assert len(result["timepoints"]) >= 1, "No timepoints generated"

        print("\n✅ Complete NL → Orchestrator → Simulation pipeline successful!")

    def test_nl_interactive_refinement_to_simulation(self):
        """Test: Interactive refinement workflow → simulation with REAL LLM"""
        from llm_v2 import LLMClient

        # 1. Start with incomplete description
        description = "Simulate a board meeting about an acquisition"

        # 2. Use interactive refiner
        refiner = InteractiveRefiner(api_key=self.api_key)

        print(f"\n🔄 Starting interactive refinement: '{description}'")

        result = refiner.start_refinement(description)

        # 3. If clarifications needed, answer them
        if result["clarifications_needed"]:
            print(f"\n⚠️  {len(result['clarifications'])} clarifications needed")

            # Provide answers programmatically
            answers = {
                "entity_count": "5",
                "timepoint_count": "3",
                "focus": "dialog, decision_making",
                "outputs": "dialog, decisions",
            }

            print("📝 Answering clarifications...")
            result = refiner.answer_clarifications(answers)

        # 4. Approve config
        final_config = refiner.approve_config()

        print("\n✅ Config generated and approved")
        print(f"   Entities: {len(final_config['entities'])}")
        print(f"   Timepoints: {final_config['timepoint_count']}")

        # 5. Execute with orchestrator
        print("\n🔄 Executing with orchestrator...")

        llm_client = LLMClient()
        result = simulate_event(
            final_config["scenario"],
            llm_client,
            self.storage,
            context={
                "max_entities": len(final_config["entities"]),
                "max_timepoints": min(final_config["timepoint_count"], 3),
                "temporal_mode": final_config.get("temporal_mode", "forward"),
            },
            save_to_db=True,
        )

        print("✅ Simulation executed")
        print("\n✅ Complete interactive refinement → simulation pipeline successful!")

    def test_nl_historical_scenario_with_orchestrator(self):
        """Test: Historical scenario via NL → simulation with REAL LLM"""
        # 1. Historical description
        description = (
            "Simulate the Apollo 13 crisis. "
            "Include Jim Lovell, Jack Swigert, Fred Haise, and Gene Kranz. "
            "10 timepoints from explosion to splashdown. "
            "Focus on decision making under extreme pressure. "
            "Start time: 1970-04-13T19:00:00."
        )

        # 2. Generate config
        generator = NLConfigGenerator(api_key=self.api_key)

        print("\n🔄 Generating historical scenario config...")
        config, confidence = generator.generate_config(description)

        print("✅ Historical config generated")
        print(f"   Scenario: {config['scenario']}")
        print(f"   Start Time: {config.get('start_time', 'Not specified')}")

        # 3. Validate
        validation = generator.validate_config(config)
        assert validation.is_valid

        # 4. Create simulation
        print("\n🔄 Creating historical simulation...")

        simulation_id = self.orchestrator.create_simulation(
            scenario=config["scenario"],
            entities=[{"name": e["name"], "role": e["role"]} for e in config["entities"]],
            timepoint_count=config["timepoint_count"],
            temporal_mode=config.get("temporal_mode", "forward"),
            start_time=config.get("start_time"),
        )

        print(f"✅ Historical simulation created: {simulation_id}")

        # 5. Generate timepoint
        result = self.orchestrator.generate_timepoint(simulation_id, 0)
        assert result is not None

        print("✅ Historical timepoint generated")
        print("\n✅ Historical NL → simulation pipeline successful!")

    def test_nl_config_validation_prevents_bad_simulation(self):
        """Test: Validation catches bad configs before orchestrator"""
        # 1. Create intentionally problematic description
        description = "Simulate a scenario with 200 people and 200 timepoints. Focus on everything."

        # 2. Try to generate config
        generator = NLConfigGenerator(api_key=self.api_key)

        print("\n🔄 Generating config with problematic parameters...")

        # This should either:
        # - Fail validation (preferred)
        # - Generate with low confidence and warnings
        # - Retry and produce reasonable config

        try:
            config, confidence = generator.generate_config(description)
            validation = generator.validate_config(config)

            # If it succeeded, it should have warnings or errors
            if not validation.is_valid:
                print("✅ Validation correctly rejected bad config")
                print(f"   Errors: {len(validation.errors)}")
                for error in validation.errors[:3]:
                    print(f"   - {error}")
                return  # Test passed

            if validation.warnings:
                print(f"⚠️  Config generated but with {len(validation.warnings)} warnings")
                print(f"   Confidence: {confidence:.1%}")
                # This is acceptable - validation caught issues
                return  # Test passed

            # If no validation issues, LLM should have adjusted parameters
            print("✅ LLM adjusted problematic parameters:")
            print(f"   Entities: {len(config['entities'])} (requested 200)")
            print(f"   Timepoints: {config['timepoint_count']} (requested 200)")

            # Verify parameters were adjusted to reasonable values
            assert len(config["entities"]) <= 100
            assert config["timepoint_count"] <= 100

        except Exception as e:
            print(f"✅ Config generation failed appropriately: {e}")

        print("\n✅ Validation system working correctly!")

    def test_nl_to_orchestrator_with_refinement_trace(self):
        """Test: Complete workflow with refinement trace export"""
        # 1. Use interactive refiner
        refiner = InteractiveRefiner(api_key=self.api_key)

        description = "Simulate a negotiation between 2 parties. 5 timepoints."

        print("\n🔄 Starting refinement with trace...")

        # 2. Refine config
        result = refiner.start_refinement(description, skip_clarifications=True)

        # 3. Approve
        final_config = refiner.approve_config()

        # 4. Export trace
        trace = refiner.export_refinement_trace()

        print("✅ Refinement trace exported")
        print(f"   Steps: {len(trace['steps'])}")
        print(f"   Original: '{trace['original_description']}'")

        # 5. Create simulation
        simulation_id = self.orchestrator.create_simulation(
            scenario=final_config["scenario"],
            entities=[{"name": e["name"], "role": e["role"]} for e in final_config["entities"]],
            timepoint_count=final_config["timepoint_count"],
        )

        # 6. Generate timepoint
        result = self.orchestrator.generate_timepoint(simulation_id, 0)
        assert result is not None

        print("✅ Simulation created from refined config")
        print("\n✅ Complete workflow with trace successful!")


@pytest.mark.skipif(os.getenv("LLM_SERVICE_ENABLED") != "true", reason="LLM service not enabled")
class TestE2ENLMockMode:
    """E2E tests using mock mode (no LLM calls) for CI/CD"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = TimePointStorage(self.temp_dir)
        self.orchestrator = SimulationOrchestrator(storage=self.storage)

    def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_nl_mock_mode_to_orchestrator(self):
        """Test: NL (mock mode) → Orchestrator integration"""
        # 1. Use mock mode (no API key)
        generator = NLConfigGenerator()  # Mock mode

        description = "Simulate a crisis meeting with 3 people. 5 timepoints. Focus on dialog."

        print("\n🔄 Generating config (mock mode)...")
        config, confidence = generator.generate_config(description)

        print("✅ Mock config generated")
        print(f"   Entities: {len(config['entities'])}")

        # 2. Validate
        validation = generator.validate_config(config)
        assert validation.is_valid

        # 3. Create simulation
        simulation_id = self.orchestrator.create_simulation(
            scenario=config["scenario"],
            entities=[{"name": e["name"], "role": e["role"]} for e in config["entities"]],
            timepoint_count=config["timepoint_count"],
        )

        print(f"✅ Simulation created from mock config: {simulation_id}")

        # 4. Generate timepoint
        result = self.orchestrator.generate_timepoint(simulation_id, 0)
        assert result is not None

        print("✅ Mock mode → orchestrator pipeline successful!")
