#!/bin/bash

# Enhanced test script with comprehensive information capture
# Adapted for the actual timepoint-daedalus architecture

set -e

echo "=== ENHANCED STRESS TEST: Temporal Chain with Detailed Information Capture ==="
echo ""

# Check that we're in the right directory
if [[ ! -f "temporal_chain.py" ]] || [[ ! -f "schemas.py" ]]; then
    echo "ERROR: Must run from timepoint-daedalus project root"
    echo "Current directory: $(pwd)"
    exit 1
fi

echo "✓ Found project files"
echo ""

# Configuration
SCENARIO="founding_fathers_1789"
OUTPUT_DIR="test_output_$(date +%Y%m%d_%H%M%S)"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Check for API configuration
if [[ -z "${OPENROUTER_API_KEY}" ]]; then
    echo "ERROR: OPENROUTER_API_KEY not set"
    exit 1
fi

echo "============================================================"
echo "REAL LLM MODE ACTIVE - API calls will incur costs"
echo "API: https://openrouter.ai/api/v1"
echo "============================================================"
echo ""

echo "======================================================================="
echo "TEMPORAL TRAINING: ${SCENARIO}"
echo "Timepoints: 7"
echo "======================================================================="
echo ""

# Main training and inspection script
python3 << 'PYEOF'
import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

# Import from actual project modules
from schemas import Entity, Timepoint, ResolutionLevel, ExposureEvent
from temporal_chain import build_temporal_chain
from storage import GraphStore
from llm import LLMClient
from entity_templates import HISTORICAL_CONTEXTS

# Configuration
output_dir = os.environ.get("OUTPUT_DIR", "test_output")
scenario = os.environ.get("SCENARIO", "founding_fathers_1789")

print("✓ Successfully imported all modules")
print("")

# Initialize components
store = GraphStore("sqlite:///:memory:")

# Create LLM client directly (no LLMConfig needed)
llm_client = LLMClient(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    dry_run=False
)

print(f"✓ LLM client initialized (dry_run={llm_client.dry_run})")
print("")

print("Building temporal chain...")
timepoints = build_temporal_chain(scenario, num_timepoints=7)
print(f"Created {len(timepoints)} timepoints with causal links")

for tp in timepoints:
    print(f"  ✓ {tp.timepoint_id}: {tp.event_description[:60]}...")

print("")

# Save timepoints to database
for timepoint in timepoints:
    store.save_timepoint(timepoint)

# Get historical context
context = HISTORICAL_CONTEXTS[scenario]
entities_data = context["entities"]

# Create entities
entities = {}
for entity_data in entities_data:
    entity = Entity(
        entity_id=entity_data["entity_id"],
        entity_type="historical_person",
        resolution_level=ResolutionLevel.TENSOR_ONLY,
        entity_metadata={
            "role": entity_data["role"],
            "age": entity_data["age"],
            "location": entity_data["location"]
        }
    )
    entities[entity_data["entity_id"]] = entity
    store.save_entity(entity)

print("Entities initialized:")
for entity_id in entities.keys():
    print(f"  ✓ {entity_id}")
print("")

# Track state progression
entity_states_log = []
total_cost = 0.0

# Process each timepoint
for i, timepoint in enumerate(timepoints, 1):
    print(f"Timepoint {i}/{len(timepoints)}: {timepoint.timepoint_id}")
    print(f"  Event: {timepoint.event_description}")
    print(f"  Timestamp: {timepoint.timestamp}")
    print(f"  Resolution: {timepoint.resolution_level.value}")
    print(f"  Entities: {len(timepoint.entities_present)}")
    print("")
    
    # Capture knowledge counts before
    prev_counts = {}
    for entity_id in timepoint.entities_present:
        entity = store.get_entity(entity_id)
        prev_counts[entity_id] = len(entity.entity_metadata.get("knowledge_state", []))
    
    # Process each entity at this timepoint
    for entity_data in entities_data:
        entity_id = entity_data["entity_id"]
        
        # Get previous knowledge for causal evolution
        previous_knowledge = None
        if timepoint.causal_parent:
            previous_knowledge = store.get_entity_knowledge_at_timepoint(
                entity_id, 
                timepoint.causal_parent
            )
        
        # Build context for LLM
        enhanced_context = {
            "historical_context": context["event"],
            "entity_role": entity_data["role"],
            "entity_age": entity_data["age"],
            "entity_location": entity_data["location"],
            "timepoint": timepoint.timestamp.isoformat(),
            "event": timepoint.event_description,
            "timepoint_id": timepoint.timepoint_id,
            "relationships": [
                r for s, t, r in context["relationships"] 
                if s == entity_id or t == entity_id
            ]
        }
        
        # Populate entity with LLM
        entity_schema = {
            "entity_id": entity_id,
            "timestamp": timepoint.timestamp.isoformat()
        }
        
        population = llm_client.populate_entity(
            entity_schema,
            enhanced_context,
            previous_knowledge
        )
        
        # Update entity with new knowledge
        entity = store.get_entity(entity_id)
        current_knowledge = set(entity.entity_metadata.get("knowledge_state", []))
        new_knowledge = set(population.knowledge_state)
        
        # Merge knowledge
        if previous_knowledge:
            added_knowledge = new_knowledge - current_knowledge
            if added_knowledge:
                updated_knowledge = list(current_knowledge | new_knowledge)
                entity.entity_metadata["knowledge_state"] = updated_knowledge
        else:
            entity.entity_metadata["knowledge_state"] = population.knowledge_state
        
        entity.entity_metadata.update({
            "energy_budget": population.energy_budget,
            "personality_traits": population.personality_traits,
            "temporal_awareness": population.temporal_awareness,
            "confidence": population.confidence
        })
        
        store.save_entity(entity)
        
        # Create exposure events
        exposure_events = []
        for knowledge_item in population.knowledge_state:
            if not previous_knowledge or knowledge_item not in previous_knowledge:
                exposure_event = ExposureEvent(
                    entity_id=entity_id,
                    event_type="experienced",
                    information=knowledge_item,
                    source=timepoint.event_description,
                    timestamp=timepoint.timestamp,
                    confidence=population.confidence,
                    timepoint_id=timepoint.timepoint_id
                )
                exposure_events.append(exposure_event)
        
        if exposure_events:
            store.save_exposure_events(exposure_events)
    
    # Show knowledge changes
    for entity_id in timepoint.entities_present:
        entity = store.get_entity(entity_id)
        new_count = len(entity.entity_metadata.get("knowledge_state", []))
        delta = new_count - prev_counts[entity_id]
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        print(f"  ✓ {entity_id}: {delta_str} knowledge items (total: {new_count})")
    
    total_cost += llm_client.cost
    
    # Capture state
    state_entry = {
        "timepoint_id": timepoint.timepoint_id,
        "entities": {}
    }
    
    for entity_id in timepoint.entities_present:
        entity = store.get_entity(entity_id)
        knowledge = entity.entity_metadata.get("knowledge_state", [])
        state_entry["entities"][entity_id] = {
            "resolution": entity.resolution_level.value,
            "knowledge_count": len(knowledge),
            "query_count": entity.query_count,
            "knowledge_sample": knowledge[:2] if knowledge else []
        }
    
    entity_states_log.append(state_entry)
    print("")

print("Temporal training complete!")
print(f"Total cost: ${total_cost:.4f}")
print(f"Timepoints processed: {len(timepoints)}")
print("")

# Save progression log
states_file = Path(output_dir) / "entity_states.json"
with open(states_file, 'w') as f:
    json.dump(entity_states_log, f, indent=2, default=str)
print(f"📊 Entity states saved to: {states_file}")
print("")

# Detailed knowledge inspection
print("="*70)
print("DETAILED KNOWLEDGE INSPECTION")
print("="*70)
print("")

all_entities = store.get_all_entities()
knowledge_dump = {}

for entity in all_entities:
    knowledge_items = entity.entity_metadata.get("knowledge_state", [])
    exposure_events = store.get_exposure_events(entity.entity_id)
    
    knowledge_dump[entity.entity_id] = {
        "resolution": entity.resolution_level.value,
        "knowledge_count": len(knowledge_items),
        "query_count": entity.query_count,
        "knowledge_items": knowledge_items,
        "exposure_events": [
            {
                "information": e.information,
                "source": e.source,
                "timestamp": e.timestamp.isoformat(),
                "timepoint_id": e.timepoint_id
            }
            for e in exposure_events
        ]
    }

# Save knowledge dump
dump_file = Path(output_dir) / "knowledge_dump.json"
with open(dump_file, 'w') as f:
    json.dump(knowledge_dump, f, indent=2)
print(f"📊 Knowledge dump saved to: {dump_file}")
print("")

# Print summary
print("KNOWLEDGE SUMMARY")
print("="*70)
for entity_id, data in knowledge_dump.items():
    print(f"\n{entity_id}:")
    print(f"  Resolution: {data['resolution']}")
    print(f"  Knowledge items: {data['knowledge_count']}")
    print(f"  Exposure events: {len(data['exposure_events'])}")
    
    if data['knowledge_items']:
        print(f"  Sample knowledge:")
        for i, item in enumerate(data['knowledge_items'][:3]):
            print(f"    [{i}] {item[:100]}{'...' if len(item) > 100 else ''}")

print("\n" + "="*70)
print("")

# Deep dive on one entity
print("="*70)
print("SAMPLE ENTITY DEEP DIVE: george_washington")
print("="*70)

washington = store.get_entity("george_washington")
if washington:
    print(f"Resolution: {washington.resolution_level.value}")
    print(f"Query count: {washington.query_count}")
    print(f"Training count: {washington.training_count}")
    
    knowledge = washington.entity_metadata.get("knowledge_state", [])
    print(f"\nKnowledge items: {len(knowledge)}")
    
    if knowledge:
        print("\nAll knowledge items:")
        for i, item in enumerate(knowledge):
            print(f"  [{i}] {item}")
    
    exposure_events = store.get_exposure_events("george_washington")
    print(f"\nExposure events: {len(exposure_events)}")
    
    if exposure_events:
        print("\nExposure timeline:")
        for event in exposure_events[:5]:
            print(f"  [{event.timepoint_id}] {event.event_type}: {event.information[:80]}...")

print("="*70)
print("")

# Save simulation for query phase
import pickle
sim_file = Path(output_dir) / "simulation_state.pkl"
with open(sim_file, 'wb') as f:
    pickle.dump(store, f)
print(f"💾 Simulation saved to: {sim_file}")
print("")

print(f"✅ Training phase complete. Total cost: ${total_cost:.4f}")
print(f"📁 All outputs in: {output_dir}/")
PYEOF

echo ""
echo "============================================================"
echo "QUERY PHASE WITH ENHANCED LOGGING"
echo "============================================================"
echo ""

# Query interface with detailed logging
python3 << 'PYEOF'
import sys
import json
import os
import pickle
from pathlib import Path
from datetime import datetime

# Import modules
from schemas import LLMConfig
from llm import LLMClient
from query_interface import QueryInterface

# Load simulation
output_dir = os.environ.get("OUTPUT_DIR", "test_output")
sim_file = Path(output_dir) / "simulation_state.pkl"

with open(sim_file, 'rb') as f:
    store = pickle.load(f)

# Create LLM client (no LLMConfig class exists, use direct params)
llm_client = LLMClient(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    dry_run=False
)

# Create query interface
query_interface = QueryInterface(store, llm_client)

print("="*70)
print("TEMPORAL SIMULATION INTERACTIVE QUERY INTERFACE")
print("="*70)
print("")
print("You can ask questions about entities in the temporal simulation.")
print("Examples:")
print("  'What did George Washington think about becoming president?'")
print("  'How did Thomas Jefferson feel about the inauguration?'")
print("  'What actions did Alexander Hamilton take during the ceremony?'")
print("")
print("Type 'help' for more examples, 'dump' to see knowledge, 'exit' or 'quit' to leave.")
print("")

query_log = []
total_query_cost = 0.0

while True:
    query = input("Query: ").strip()
    
    if not query:
        continue
    
    if query.lower() in ['exit', 'quit', 'q']:
        break
    
    if query.lower() == 'help':
        print("\nExample queries:")
        print("  - What was Washington thinking during the inauguration?")
        print("  - How did Hamilton and Jefferson interact?")
        print("  - What concerns did Adams have?")
        print("  - Describe the cabinet meeting")
        print("")
        continue
    
    if query.lower() == 'dump':
        print("\nDumping current knowledge state...")
        entities = store.get_all_entities()
        for entity in entities:
            knowledge = entity.entity_metadata.get("knowledge_state", [])
            print(f"\n{entity.entity_id}:")
            print(f"  Resolution: {entity.resolution_level.value}")
            print(f"  Knowledge items: {len(knowledge)}")
            if knowledge:
                for i, k in enumerate(knowledge[:3]):
                    print(f"    [{i}] {k[:100]}...")
        print("")
        continue
    
    if query.lower() == 'status':
        print("\nSimulation Status:")
        entities = store.get_all_entities()
        timepoints = store.get_all_timepoints()
        print(f"  Entities: {len(entities)}")
        print(f"  Timepoints: {len(timepoints)}")
        print(f"  Total query cost: ${total_query_cost:.4f}")
        
        if timepoints:
            latest = timepoints[-1]
            print(f"  Latest timepoint: {latest.timepoint_id}")
            print(f"    Event: {latest.event_description[:60]}...")
        print("")
        continue
    
    # Parse query
    print("  Parsing query...")
    intent = query_interface.parse_query(query)
    
    entity_id = intent.target_entity
    print(f"  Intent: {intent.information_type} about {entity_id or 'unknown'} (confidence: {intent.confidence:.1f})")
    
    # Get entity before query
    if entity_id:
        entity = store.get_entity(entity_id)
        if entity:
            knowledge_before = entity.entity_metadata.get("knowledge_state", [])
            print(f"  📚 Knowledge before query: {len(knowledge_before)} items")
            
            if knowledge_before:
                print(f"     Sample items:")
                for i, k in enumerate(knowledge_before[:3]):
                    print(f"       [{i}] {k[:80]}...")
        else:
            print(f"  ⚠️  Entity not found: {entity_id}")
            knowledge_before = []
    else:
        print(f"  ⚠️  No entity identified in query")
        knowledge_before = []
    
    # Synthesize response
    print("  Synthesizing response...")
    response = query_interface.synthesize_response(intent)
    
    print("")
    print("Response:")
    print(response)
    print("")
    
    # Log query
    query_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "entity_id": entity_id,
        "intent_type": intent.information_type,
        "confidence": intent.confidence,
        "knowledge_count_before": len(knowledge_before),
        "response": response[:200]
    }
    
    query_log.append(query_entry)
    
    # Save query log
    log_file = Path(output_dir) / "query_log.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(query_entry) + "\n")
    
    cost = llm_client.cost - total_query_cost
    total_query_cost = llm_client.cost
    
    print(f"Cost so far: ${total_query_cost:.4f}")
    print("")

print("\nGoodbye! 👋")
print("")

# Final summary
print("="*70)
print("FINAL KNOWLEDGE STATE")
print("="*70)

entities = store.get_all_entities()
for entity in entities:
    knowledge = entity.entity_metadata.get("knowledge_state", [])
    print(f"\n{entity.entity_id}:")
    print(f"  Resolution: {entity.resolution_level.value}")
    print(f"  Query count: {entity.query_count}")
    print(f"  Knowledge items: {len(knowledge)}")

print("")
print(f"📁 All query logs saved to: {output_dir}/query_log.jsonl")
print(f"💾 Final state in: {output_dir}/")
print("")
print(f"Estimated total cost: ~${total_query_cost:.2f}")
PYEOF

echo ""
echo "============================================================"
echo "TEST COMPLETE"
echo "============================================================"
echo ""
echo "All outputs saved to: ${OUTPUT_DIR}/"
echo ""
echo "Files generated:"
echo "  - knowledge_dump.json          # Knowledge after training"
echo "  - entity_states.json           # State progression through timepoints"
echo "  - query_log.jsonl              # All queries with detailed info"
echo "  - simulation_state.pkl         # Pickled simulation object"
echo ""