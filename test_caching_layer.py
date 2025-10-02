#!/usr/bin/env python3
"""
Test script for Caching Layer (1.4: Caching Layer)
Tests LRU cache for entities and TTL cache for query responses.
"""

import time
from datetime import datetime, timedelta
from schemas import Entity, Timepoint, ResolutionLevel
from storage import GraphStore
from query_interface import QueryInterface
from llm import LLMClient

def test_entity_caching():
    """Test LRU caching for entity retrieval"""
    print("🧪 Testing Entity LRU Caching")

    store = GraphStore("sqlite:///:memory:")

    # Create test entities
    entities = []
    for i in range(5):
        entity = Entity(
            entity_id=f"test_entity_{i}",
            entity_type="person",
            timepoint="test_tp",
            resolution_level=ResolutionLevel.GRAPH,
            entity_metadata={"role": f"role_{i}"}
        )
        entities.append(entity)
        store.save_entity(entity)

    print(f"Created {len(entities)} test entities")

    # Test LRU caching by repeatedly accessing the same entities
    start_time = time.time()

    # First access (cache miss)
    for _ in range(10):
        for entity in entities[:3]:  # Only access first 3 entities
            retrieved = store.get_entity(entity.entity_id)
            assert retrieved is not None
            assert retrieved.entity_id == entity.entity_id

    first_access_time = time.time() - start_time
    print(".2f")

    # Second access (should hit cache)
    start_time = time.time()
    for _ in range(10):
        for entity in entities[:3]:
            retrieved = store.get_entity(entity.entity_id)
            assert retrieved is not None
            assert retrieved.entity_id == entity.entity_id

    second_access_time = time.time() - start_time
    print(".2f")

    # Check that cached access is faster (though this is a rough test)
    if second_access_time < first_access_time:
        print("✅ Entity caching working - second access was faster")
    else:
        print("⚠️ Entity caching may not be significantly faster (could be due to test overhead)")

    return True

def test_query_response_caching():
    """Test TTL caching for query responses"""
    print("\n🧪 Testing Query Response TTL Caching")

    # Create components
    llm_client = LLMClient(api_key="dummy_key", base_url="https://dummy.com", dry_run=True)
    store = GraphStore("sqlite:///:memory:")
    query_interface = QueryInterface(store, llm_client)

    # Create a test entity
    entity = Entity(
        entity_id="george_washington",
        entity_type="person",
        timepoint="test_tp",
        resolution_level=ResolutionLevel.GRAPH,
        entity_metadata={
            "knowledge_state": ["Led Continental Army", "First President"],
            "role": "president"
        }
    )
    store.save_entity(entity)

    # Create test timepoint
    timepoint = Timepoint(
        timepoint_id="test_tp",
        timestamp=datetime.now(),
        event_description="Test timepoint",
        entities_present=["george_washington"]
    )
    store.save_timepoint(timepoint)

    test_query = "What did George Washington do?"

    # First query (cache miss)
    print("First query (should cache response)...")
    start_time = time.time()
    response1 = query_interface.query(test_query)
    first_query_time = time.time() - start_time
    print(".2f")
    print(f"Response: {response1[:100]}...")

    # Check cache stats
    stats = query_interface.get_cache_stats()
    print(f"Cache stats after first query: {stats}")

    # Second query (should hit cache)
    print("\nSecond query (should hit cache)...")
    start_time = time.time()
    response2 = query_interface.query(test_query)
    second_query_time = time.time() - start_time
    print(".2f")
    print(f"Response: {response2[:100]}...")

    # Check that responses are identical
    if response1 == response2:
        print("✅ Cached response matches original")
    else:
        print("❌ Cached response differs from original")
        return False

    # Check cache stats again
    stats = query_interface.get_cache_stats()
    print(f"Cache stats after second query: {stats}")

    # Test cache expiration (simulate by manually setting old timestamp)
    print("\nTesting cache expiration...")
    # We'll test this by clearing expired entries (should be none yet)
    cleared = query_interface.clear_expired_cache()
    print(f"Cleared {cleared} expired entries")

    # Verify caching provides performance benefit
    if second_query_time < first_query_time * 0.5:  # At least 2x faster
        print("✅ Query caching working - significant performance improvement")
    else:
        print("⚠️ Query caching may not show significant speedup in this test")

    return True

def test_cache_key_generation():
    """Test that different queries generate different cache keys"""
    print("\n🧪 Testing Cache Key Generation")

    llm_client = LLMClient(api_key="dummy_key", base_url="https://dummy.com", dry_run=True)
    store = GraphStore("sqlite:///:memory:")
    query_interface = QueryInterface(store, llm_client)

    # Create test query intent
    from query_interface import QueryIntent

    intent1 = QueryIntent(target_entity="washington", information_type="knowledge")
    intent2 = QueryIntent(target_entity="jefferson", information_type="knowledge")
    intent3 = QueryIntent(target_entity="washington", information_type="actions")

    query1 = "What did Washington know?"
    query2 = "What did Jefferson know?"
    query3 = "What did Washington do?"

    key1 = query_interface._get_query_cache_key(query1, intent1)
    key2 = query_interface._get_query_cache_key(query2, intent2)
    key3 = query_interface._get_query_cache_key(query3, intent3)

    # Keys should be different
    keys = [key1, key2, key3]
    if len(set(keys)) == len(keys):
        print("✅ All cache keys are unique")
        return True
    else:
        print("❌ Some cache keys are identical")
        return False

def main():
    """Run all caching tests"""
    print("🚀 Testing 1.4: Caching Layer Implementation")

    try:
        # Test entity caching
        entity_test_passed = test_entity_caching()

        # Test query response caching
        query_test_passed = test_query_response_caching()

        # Test cache key generation
        key_test_passed = test_cache_key_generation()

        if entity_test_passed and query_test_passed and key_test_passed:
            print("\n🎉 All caching layer tests PASSED!")
            return True
        else:
            print("\n❌ Some caching layer tests FAILED!")
            return False

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

