#!/usr/bin/env python3
"""
Quick script to track remaining mechanisms (M2, M5, M6, M9, M10, M12, M13, M14, M15, M16)
by triggering them through minimal E2E workflows with tracking enabled.
"""

import os
from datetime import datetime
from metadata.run_tracker import MetadataManager
from metadata.tracking import set_current_run_id, set_metadata_manager
from storage import GraphStore
from llm_v2 import LLMClient
from query_interface import QueryInterface
from schemas import Entity, Timepoint, PhysicalTensor, CognitiveTensor, ResolutionLevel
from workflows import couple_pain_to_cognition, couple_illness_to_cognition

# Ensure API key is set
if not os.getenv("OPENROUTER_API_KEY"):
    print("❌ OPENROUTER_API_KEY not set. Please set it first.")
    exit(1)

print("🎯 Tracking Remaining Mechanisms")
print("=" * 80)

# Initialize tracking context
manager = MetadataManager(db_path="metadata/runs.db")
set_metadata_manager(manager)

# Initialize system components
store = GraphStore("sqlite:///timepoint.db")
llm = LLMClient(api_key=os.getenv("OPENROUTER_API_KEY"))
qi = QueryInterface(store, llm)

tracked_mechanisms = set()

# ============================================================================
# M5: Query Resolution - Need to call qi.query() in a tracked context
# ============================================================================
print("\n[1/10] Tracking M5: Query Resolution")
run_id = manager.start_run(
    template_id="m5_tracking",
    causal_mode="pearl",
    max_entities=1,
    max_timepoints=1
)
set_current_run_id(run_id)

try:
    # Create a simple entity and timepoint
    test_entity = Entity(
        entity_id="test_person",
        entity_type="human",
        resolution_level=ResolutionLevel.SCENE,
        entity_metadata={"knowledge_state": ["Test knowledge"]}
    )
    store.save_entity(test_entity)

    test_tp = Timepoint(
        timepoint_id="test_tp",
        timestamp=datetime.now(),
        event_description="Test event",
        entities_present=["test_person"]
    )
    store.save_timepoint(test_tp)

    # Trigger M5 by querying
    response = qi.query("What does test_person know?")
    print("  ✅ M5 triggered via qi.query()")
    tracked_mechanisms.add("M5")
except Exception as e:
    print(f"  ⚠️  M5 tracking failed: {e}")
finally:
    manager.complete_run(run_id)

# ============================================================================
# M9: On-Demand Generation - Need to call generate_entity_on_demand()
# ============================================================================
print("\n[2/10] Tracking M9: On-Demand Entity Generation")
run_id = manager.start_run(
    template_id="m9_tracking",
    causal_mode="pearl",
    max_entities=1,
    max_timepoints=1
)
set_current_run_id(run_id)

try:
    # Trigger M9 by generating an entity
    new_entity = qi.generate_entity_on_demand("generated_person", test_tp)
    print(f"  ✅ M9 triggered via generate_entity_on_demand() - created {new_entity.entity_id}")
    tracked_mechanisms.add("M9")
except Exception as e:
    print(f"  ⚠️  M9 tracking failed: {e}")
finally:
    manager.complete_run(run_id)

# ============================================================================
# M14: Circadian Patterns - Need to trigger circadian logic in validation
# ============================================================================
print("\n[3/10] Tracking M14: Circadian Patterns")
run_id = manager.start_run(
    template_id="m14_tracking",
    causal_mode="pearl",
    max_entities=1,
    max_timepoints=1
)
set_current_run_id(run_id)

try:
    # Create entity with circadian context
    from validation import Validator

    circadian_entity = Entity(
        entity_id="circadian_test",
        entity_type="human",
        entity_metadata={
            "circadian_config": {
                "hour": 3,  # 3 AM - high fatigue
                "fatigue_level": 0.8,
                "energy_penalty": 1.5
            }
        }
    )

    # Run validation which includes circadian checking
    result = Validator.validate_all(circadian_entity, {"test": True})
    print("  ✅ M14 triggered via circadian validation")
    tracked_mechanisms.add("M14")
except Exception as e:
    print(f"  ⚠️  M14 tracking failed: {e}")
finally:
    manager.complete_run(run_id)

# ============================================================================
# Report
# ============================================================================
print("\n" + "=" * 80)
print("📊 Mechanism Tracking Summary")
print("=" * 80)

# Query database for current coverage
import sqlite3
conn = sqlite3.connect("metadata/runs.db")
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT mechanism FROM mechanism_usage ORDER BY mechanism")
all_tracked = {row[0] for row in cursor.fetchall()}
conn.close()

print(f"\nTotal Mechanisms Tracked: {len(all_tracked)}/17")
print(f"Tracked: {', '.join(sorted(all_tracked))}")

missing = set([f"M{i}" for i in range(1, 18)]) - all_tracked
if missing:
    print(f"\nStill Missing: {', '.join(sorted(missing))}")
else:
    print("\n🎉 ALL 17/17 MECHANISMS TRACKED!")

print("\n" + "=" * 80)
