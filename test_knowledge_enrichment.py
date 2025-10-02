#!/usr/bin/env python3
"""
Test script for Mechanism 1.6: Knowledge Enrichment on Elevation
Tests that entities gain new knowledge items when elevated to higher resolution levels.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from schemas import Entity, ResolutionLevel, Timepoint, ExposureEvent
from storage import GraphStore
from llm import LLMClient
from resolution_engine import ResolutionEngine
from datetime import datetime


def test_knowledge_enrichment():
    """Test that entity knowledge grows when elevated to higher resolution levels"""

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize components
        db_url = f"sqlite:///{db_path}"
        store = GraphStore(db_url)
        llm_client = LLMClient(api_key="dummy", base_url="https://dummy.com", dry_run=True)  # Use dry-run for testing with mock knowledge
        resolution_engine = ResolutionEngine(store, llm_client)

        # Create a test entity with basic knowledge
        entity = Entity(
            entity_id="george_washington",
            entity_type="historical_person",
            temporal_span_start=datetime(1732, 2, 22),
            temporal_span_end=datetime(1799, 12, 14),
            resolution_level=ResolutionLevel.TENSOR_ONLY,
            entity_metadata={
                "role": "military_leader",
                "knowledge_state": [
                    "Born in Virginia in 1732",
                    "Served as commander-in-chief during Revolutionary War",
                    "First President of the United States"
                ],
                "compressed": {}  # Empty compressed data for now
            },
            query_count=0,
            eigenvector_centrality=0.0
        )

        # Save initial entity
        store.save_entity(entity)

        # Create a test timepoint for context
        timepoint = Timepoint(
            timepoint_id="revolutionary_war_1775",
            event_description="Outbreak of the American Revolutionary War",
            timestamp=datetime(1775, 4, 19),
            resolution_level=ResolutionLevel.SCENE,
            causal_parent=None,
            metadata={}
        )
        store.save_timepoint(timepoint)

        # Record initial knowledge count
        initial_knowledge_count = len(entity.entity_metadata["knowledge_state"])
        print(f"📊 Initial knowledge count: {initial_knowledge_count}")

        # Elevate entity from TENSOR_ONLY to SCENE level
        success = resolution_engine.elevate_resolution(entity, ResolutionLevel.SCENE, timepoint)
        assert success, "Elevation to SCENE level should succeed"

        # Reload entity to get updated knowledge
        updated_entity = store.get_entity("george_washington")
        assert updated_entity is not None, "Entity should still exist after elevation"

        # Check that knowledge grew
        final_knowledge_count = len(updated_entity.entity_metadata["knowledge_state"])
        print(f"📊 Final knowledge count: {final_knowledge_count}")

        # Verify knowledge actually grew (should add 3 items for SCENE level)
        expected_growth = 3
        assert final_knowledge_count >= initial_knowledge_count + expected_growth, \
            f"Knowledge should grow by at least {expected_growth} items, got {final_knowledge_count - initial_knowledge_count}"

        # Verify resolution level was updated
        assert updated_entity.resolution_level == ResolutionLevel.SCENE, \
            f"Resolution level should be SCENE, got {updated_entity.resolution_level}"

        # Check that exposure events were created for new knowledge
        exposure_events = store.get_exposure_events("george_washington")
        new_knowledge_events = [e for e in exposure_events if e.source in ["resolution_elevation", "resolution_elevation_test"]]

        print(f"📚 New knowledge items added: {len(new_knowledge_events)}")

        # Should have at least the expected number of exposure events
        assert len(new_knowledge_events) >= expected_growth, \
            f"Should have at least {expected_growth} exposure events for new knowledge"

        # Verify the new knowledge items are reasonable
        new_knowledge_items = updated_entity.entity_metadata["knowledge_state"][initial_knowledge_count:]
        print("🆕 New knowledge items:")
        for item in new_knowledge_items:
            print(f"  - {item}")
            assert len(item) > 10, f"Knowledge item should be substantial: {item}"

        # Test elevation to DIALOG level (should add 8 items)
        success = resolution_engine.elevate_resolution(updated_entity, ResolutionLevel.DIALOG, timepoint)
        assert success, "Elevation to DIALOG level should succeed"

        # Reload and check again
        final_entity = store.get_entity("george_washington")
        final_knowledge_count = len(final_entity.entity_metadata["knowledge_state"])

        # Should have grown significantly more
        assert final_knowledge_count >= initial_knowledge_count + expected_growth + 8, \
            f"Knowledge should grow by at least {expected_growth + 8} items total, got {final_knowledge_count - initial_knowledge_count}"

        print(f"✅ Knowledge enrichment test passed!")
        print(f"   Initial: {initial_knowledge_count} → Final: {final_knowledge_count} items")
        print(f"   Total growth: {final_knowledge_count - initial_knowledge_count} items")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up
        try:
            os.unlink(db_path)
        except:
            pass


if __name__ == "__main__":
    print("🧪 Testing Mechanism 1.6: Knowledge Enrichment on Elevation")

    success = test_knowledge_enrichment()

    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Tests failed!")
        sys.exit(1)
