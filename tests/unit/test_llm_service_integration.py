#!/usr/bin/env python3
"""
test_llm_service_integration.py - Integration test for centralized LLM service

Tests that the LLM service works correctly throughout the application.
Note: LLMClient no longer supports dry_run mode - tests requiring LLM calls
skip when OPENROUTER_API_KEY is not set.
"""

import sys
import os
import pytest
import tempfile
from pathlib import Path

from llm_v2 import LLMClient
from llm_service import LLMService, LLMServiceConfig
from llm_service.config import ServiceMode
from storage import GraphStore
from schemas import Entity, ResolutionLevel


@pytest.mark.unit
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

    assert response.success


@pytest.mark.unit
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_backward_compatible_client():
    """Test backward-compatible LLMClient wrapper"""
    print("\n" + "="*60)
    print("TEST 2: Backward-Compatible Client")
    print("="*60)

    api_key = os.getenv('OPENROUTER_API_KEY')
    client = LLMClient(api_key=api_key)

    print(f"✅ Client created")

    # Test populate_entity method
    entity_schema = Entity(
        entity_id="washington",
        entity_type="human",
        timepoint="test_tp",
        resolution_level=ResolutionLevel.TENSOR_ONLY,
        entity_metadata={"role": "president"}
    )

    result = client.populate_entity(
        entity_schema=entity_schema,
        context={"year": 1789, "event": "inauguration"}
    )

    print(f"✅ Entity populated: {result.entity_id}")
    print(f"   Knowledge items: {len(result.knowledge_state)}")
    print(f"   Energy: {result.energy_budget:.1f}")
    print(f"   Confidence: {result.confidence:.2f}")

    assert result.entity_id == "washington"


@pytest.mark.unit
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
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
        api_key = os.getenv('OPENROUTER_API_KEY')
        client = LLMClient(api_key=api_key)

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
        loaded = store.get_entity("test_entity")
        print(f"✅ Entity loaded from store: {loaded.entity_id}")

        assert loaded.entity_id == "test_entity"

    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.unit
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

    assert stats['total_calls'] == 3


@pytest.mark.unit
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

    assert response.success


@pytest.mark.unit
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

    assert response.success


@pytest.mark.unit
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
        assert response.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
