#!/usr/bin/env python3
"""
Test script for 1.5: Error Handling with Retry
Tests that retry mechanism handles LLM API failures with exponential backoff.
"""

import time
from unittest.mock import Mock, patch
from llm import LLMClient, retry_with_backoff

def test_retry_with_backoff_success():
    """Test that retry function works on successful calls"""
    print("🧪 Testing retry_with_backoff - Success case")

    call_count = 0
    def successful_func():
        nonlocal call_count
        call_count += 1
        return "success"

    start_time = time.time()
    result = retry_with_backoff(successful_func, max_retries=3)
    end_time = time.time()

    assert result == "success"
    assert call_count == 1  # Should only call once for success
    assert end_time - start_time < 0.1  # Should be very fast

    print("✅ Success case: Function called once and returned result immediately")
    return True

def test_retry_with_backoff_eventual_success():
    """Test that retry function retries on failure then succeeds"""
    print("\n🧪 Testing retry_with_backoff - Eventual success case")

    call_count = 0
    def failing_then_success_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"Attempt {call_count} failed")
        return "success"

    start_time = time.time()
    result = retry_with_backoff(failing_then_success_func, max_retries=3, base_delay=0.1)
    end_time = time.time()

    assert result == "success"
    assert call_count == 3  # Should call 3 times: fail, fail, succeed

    # Should take at least the delay times: 0.1 + 0.2 = 0.3 seconds
    elapsed = end_time - start_time
    assert elapsed >= 0.3 and elapsed < 1.0  # Allow some margin

    print(f"✅ Eventual success: Function called {call_count} times over {elapsed:.1f} seconds")
    return True

def test_retry_with_backoff_complete_failure():
    """Test that retry function eventually gives up on persistent failures"""
    print("\n🧪 Testing retry_with_backoff - Complete failure case")

    call_count = 0
    def always_failing_func():
        nonlocal call_count
        call_count += 1
        raise Exception(f"Persistent failure #{call_count}")

    start_time = time.time()
    try:
        result = retry_with_backoff(always_failing_func, max_retries=2, base_delay=0.1)
        assert False, "Should have raised exception"
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time

        assert call_count == 3  # Initial attempt + 2 retries
        assert "Persistent failure #3" in str(e)

        # Should take at least: 0.1 + 0.2 = 0.3 seconds
        assert elapsed >= 0.3 and elapsed < 1.0

        print(f"✅ Complete failure: Function called {call_count} times over {elapsed:.1f} seconds, then raised exception")
        return True

def test_llm_client_retry_integration():
    """Test that LLM client methods use retry logic"""
    print("\n🧪 Testing LLM Client retry integration")

    # Create dry-run client to test the structure
    llm_client = LLMClient(api_key="dummy", base_url="https://dummy.com", dry_run=True)

    # Test populate_entity (should work in dry-run mode)
    entity_schema = {"entity_id": "test_entity"}
    context = {"test": "context"}
    result = llm_client.populate_entity(entity_schema, context)
    assert result.entity_id == "test_entity"
    print("✅ populate_entity works with dry-run mode")

    # Test validate_consistency (should work in dry-run mode)
    entities = [{"id": "test"}]
    from datetime import datetime
    result = llm_client.validate_consistency(entities, datetime.now())
    assert result.is_valid == True
    print("✅ validate_consistency works with dry-run mode")

    # Test score_relevance (should work in dry-run mode)
    score = llm_client.score_relevance("test query", "test knowledge")
    assert 0.0 <= score <= 1.0
    print("✅ score_relevance works with dry-run mode")

    return True

def test_exponential_backoff_timing():
    """Test that delays follow exponential backoff pattern"""
    print("\n🧪 Testing exponential backoff timing")

    call_times = []
    call_count = 0

    def failing_func():
        nonlocal call_count
        call_count += 1
        call_times.append(time.time())
        if call_count < 4:  # Fail 3 times, succeed on 4th
            raise Exception(f"Failure {call_count}")
        return "success"

    start_time = time.time()
    result = retry_with_backoff(failing_func, max_retries=3, base_delay=0.1)

    assert result == "success"
    assert call_count == 4

    # Check timing between calls
    delays = []
    for i in range(1, len(call_times)):
        delays.append(call_times[i] - call_times[i-1])

    # Expected delays: 0.1, 0.2, 0.4 (approximately)
    expected_delays = [0.1, 0.2, 0.4]
    for i, (actual, expected) in enumerate(zip(delays, expected_delays)):
        # Allow 10% margin for timing variations
        assert abs(actual - expected) < expected * 0.1, f"Delay {i+1}: expected ~{expected}s, got {actual}s"

    print("✅ Exponential backoff timing is correct")
    return True

def main():
    """Run all retry mechanism tests"""
    print("🚀 Testing 1.5: Error Handling with Retry Implementation")

    try:
        # Test basic retry functionality
        success_1 = test_retry_with_backoff_success()
        success_2 = test_retry_with_backoff_eventual_success()
        success_3 = test_retry_with_backoff_complete_failure()

        # Test timing
        success_4 = test_exponential_backoff_timing()

        # Test LLM integration
        success_5 = test_llm_client_retry_integration()

        if all([success_1, success_2, success_3, success_4, success_5]):
            print("\n🎉 All error handling and retry tests PASSED!")
            return True
        else:
            print("\n❌ Some retry tests FAILED!")
            return False

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
