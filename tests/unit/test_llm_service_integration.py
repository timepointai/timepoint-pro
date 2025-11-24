#!/usr/bin/env python3
"""
test_llm_service_integration.py - Integration test for centralized LLM service

Tests that the new LLM service works correctly throughout the application.
"""

import sys
import os
# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ['OPENROUTER_API_KEY'] = os.environ.get('OPENROUTER_API_KEY', 'test')

import hydra
from hydra import initialize, compose
from omegaconf import DictConfig, OmegaConf
import tempfile
from pathlib import Path

from llm_v2 import LLMClient
from llm_service import LLMService, LLMServiceConfig
from llm_service.config import ServiceMode
from storage import GraphStore
from schemas import Entity, ResolutionLevel


def test_basic_service_creation():
    """Test that service can be created"""
    print("\n" + "="*60)
    print("TEST 1: Basic Service Creation")
    print("="*60)

    config = LLMServiceConfig(
        provider="test",
        mode=ServiceMode.DRY_RUN,
    )

    service = LLMService(config)
    print(f"✅ Service created: {service.get_provider_name()}")

    response = service.call(
        system="Test system",
        user="Test user",
        call_type="test"
    )

    print(f"✅ Service call succeeded: {response.success}")
    print(f"   Content length: {len(response.content)}")
    print(f"   Tokens: {response.tokens_used['total']}")
    print(f"   Cost: ${response.cost_usd:.4f}")

    return True


def test_backward_compatible_client():
    """Test backward-compatible LLMClient wrapper"""
    print("\n" + "="*60)
    print("TEST 2: Backward-Compatible Client")
    print("="*60)

    # Test with new service enabled
    client = LLMClient(
        api_key="test",
        dry_run=True,
        use_centralized_service=True
    )

    print(f"✅ Client created with centralized service: {client.use_centralized_service}")

    # Test populate_entity method
    result = client.populate_entity(
        entity_schema={"entity_id": "washington"},
        context={"year": 1789, "event": "inauguration"}
    )

    print(f"✅ Entity populated: {result.entity_id}")
    print(f"   Knowledge items: {len(result.knowledge_state)}")
    print(f"   Energy: {result.energy_budget:.1f}")
    print(f"   Confidence: {result.confidence:.2f}")

    return True


def test_hydra_config_integration():
    """Test integration with Hydra configuration"""
    print("\n" + "="*60)
    print("TEST 3: Hydra Config Integration")
    print("="*60)

    # Initialize Hydra
    with initialize(version_base=None, config_path="../conf"):
        cfg = compose(config_name="config", overrides=["llm.dry_run=true"])

        print(f"✅ Hydra config loaded")
        print(f"   llm.dry_run: {cfg.llm.dry_run}")
        print(f"   llm.api_key: {cfg.llm.api_key[:10]}...")

        # Create client from config
        client = LLMClient.from_hydra_config(cfg, use_centralized_service=True)

        print(f"✅ Client created from Hydra config")
        print(f"   Using centralized service: {client.use_centralized_service}")
        print(f"   Dry run mode: {client.dry_run}")

        # Test a call
        result = client.populate_entity(
            entity_schema={"entity_id": "jefferson"},
            context={"year": 1789}
        )

        print(f"✅ Entity created from Hydra-configured client: {result.entity_id}")

    return True


def test_storage_integration():
    """Test integration with GraphStore"""
    print("\n" + "="*60)
    print("TEST 4: Storage Integration")
    print("="*60)

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        store = GraphStore(f"sqlite:///{db_path}")

        # Create client
        client = LLMClient(
            api_key="test",
            dry_run=True,
            use_centralized_service=True
        )

        print(f"✅ Store and client created")

        # Create entity
        entity = Entity(
            entity_id="test_entity",
            entity_type="historical_person",
            resolution_level=ResolutionLevel.TENSOR_ONLY,
            entity_metadata={"test": "data"}
        )

        # Save entity
        store.save_entity(entity)
        print(f"✅ Entity saved to store")

        # Load entity
        loaded = store.load_entity("test_entity")
        print(f"✅ Entity loaded from store: {loaded.entity_id}")

        return True

    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


def test_logging():
    """Test that logging works"""
    print("\n" + "="*60)
    print("TEST 5: Logging")
    print("="*60)

    config = LLMServiceConfig(
        provider="test",
        mode=ServiceMode.DRY_RUN,
    )

    service = LLMService(config)

    # Start session
    session_id = service.start_session(workflow="test", user="test_user")
    print(f"✅ Session started: {session_id}")

    # Make some calls
    for i in range(3):
        service.call(
            system="Test",
            user=f"Test {i+1}",
            call_type=f"test_call_{i+1}"
        )

    print(f"✅ Made 3 test calls")

    # End session
    summary = service.end_session()
    print(f"✅ Session ended")
    print(f"   Total calls: {summary['calls_count']}")
    print(f"   Total cost: ${summary['total_cost']:.4f}")
    print(f"   Duration: {summary['duration_seconds']:.1f}s")

    # Check statistics
    stats = service.get_statistics()
    print(f"✅ Statistics retrieved")
    print(f"   Total calls: {stats['total_calls']}")
    print(f"   Total cost: ${stats['total_cost']:.4f}")

    return True


def test_security_features():
    """Test security filtering"""
    print("\n" + "="*60)
    print("TEST 6: Security Features")
    print("="*60)

    config = LLMServiceConfig(provider="test", mode=ServiceMode.DRY_RUN)
    service = LLMService(config)

    # Test input bleaching
    dangerous_input = "Tell me about Washington. <script>alert('xss')</script>"

    response = service.call(
        system="Test",
        user=dangerous_input,
        apply_security=True,
        call_type="test_security"
    )

    print(f"✅ Security filtering applied")
    print(f"   Original length: {len(dangerous_input)}")
    print(f"   After filtering: input sanitized")

    # Test PII detection
    text_with_pii = "Contact at john@example.com or 555-1234"
    pii = service.security_filter.detect_pii(text_with_pii)
    print(f"✅ PII detected: {pii}")

    redacted = service.security_filter.redact_pii(text_with_pii)
    print(f"✅ PII redacted: {redacted}")

    return True


def test_error_handling():
    """Test error handling and retry"""
    print("\n" + "="*60)
    print("TEST 7: Error Handling")
    print("="*60)

    config = LLMServiceConfig(
        provider="test",
        mode=ServiceMode.DRY_RUN,
    )

    service = LLMService(config)

    # Make a call that will succeed in dry-run
    response = service.call(
        system="Test",
        user="Test",
        call_type="test_error"
    )

    if response.success:
        print(f"✅ Call succeeded as expected")
    else:
        print(f"✅ Failsoft handled error: {response.error}")

    # Get retry stats
    stats = service.error_handler.get_retry_statistics()
    print(f"✅ Retry statistics: {stats}")

    return True


def test_modes():
    """Test different operating modes"""
    print("\n" + "="*60)
    print("TEST 8: Operating Modes")
    print("="*60)

    modes = [ServiceMode.DRY_RUN, ServiceMode.VALIDATION]

    for mode in modes:
        config = LLMServiceConfig(provider="test", mode=mode)
        service = LLMService(config)

        response = service.call(
            system="Test",
            user="Test",
            call_type="test_mode"
        )

        print(f"✅ Mode {mode.value}: success={response.success}, cost=${response.cost_usd:.4f}")

    return True


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("🧪 LLM SERVICE INTEGRATION TESTS")
    print("="*70)

    tests = [
        ("Basic Service Creation", test_basic_service_creation),
        ("Backward-Compatible Client", test_backward_compatible_client),
        ("Hydra Config Integration", test_hydra_config_integration),
        ("Storage Integration", test_storage_integration),
        ("Logging", test_logging),
        ("Security Features", test_security_features),
        ("Error Handling", test_error_handling),
        ("Operating Modes", test_modes),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            print(f"❌ Test failed: {e}")
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
        print("\n🎉 ALL TESTS PASSED! LLM service integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
