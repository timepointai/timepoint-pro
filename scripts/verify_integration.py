#!/usr/bin/env python3
"""Minimal integration test to verify JSON extraction fix works end-to-end."""

import sys
from entity_network import Entity, EntityNetwork
from tensor_initialization import populate_entity_tensors

# Create minimal entity that will trigger tensor population
entity = Entity(
    entity_id="test_entity",
    entity_type="human",
    role="protagonist",
    description="A test character for verification",
    background=""
)

# Create minimal network
network = EntityNetwork()
network.add_entity(entity)

print("=" * 80)
print("PHASE 2: Integration Test - Real LLM Call")
print("=" * 80)
print(f"Entity: {entity.entity_id}")
print(f"Starting tensor population...")
print()

try:
    # This will make actual LLM calls and use the extraction function
    populate_entity_tensors(network)

    print()
    print("=" * 80)
    print("✅ INTEGRATION TEST PASSED")
    print("=" * 80)
    print(f"Final tensor values for {entity.entity_id}:")
    print(f"  Context:  {entity.context_tensor}")
    print(f"  Biology:  {entity.biology_tensor}")
    print(f"  Behavior: {entity.behavior_tensor}")
    print()
    print("Check logs/llm_tensor_population_2025-10-26.jsonl for detailed LLM call logs")
    sys.exit(0)

except Exception as e:
    print()
    print("=" * 80)
    print("❌ INTEGRATION TEST FAILED")
    print("=" * 80)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
