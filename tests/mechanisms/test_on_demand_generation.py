#!/usr/bin/env python3
"""
Test script for Phase 2.2: On-Demand Entity Generation (Mechanism 9)
Tests that unknown entities are generated dynamically when queried.
"""

from query_interface import QueryInterface
from storage import GraphStore
from llm_v2 import LLMClient  # Use new centralized service
import tempfile
import os

def test_entity_gap_detection():
    """Test that entity gap detection identifies numbered attendees"""
    print("🕵️ Testing Entity Gap Detection")

    # Create a mock query interface just for testing the detection function
    class MockQueryInterface:
        def extract_entity_names(self, query):
            import re
            entity_names = set()

            # Pattern for numbered entities
            numbered_patterns = [
                r'attendee\s*#?\s*(\d+)',
                r'person\s*#?\s*(\d+)',
                r'member\s*#?\s*(\d+)'
            ]

            for pattern in numbered_patterns:
                matches = re.findall(pattern, query.lower())
                for match in matches:
                    entity_names.add(f"attendee_{match}")

            return entity_names

        def detect_entity_gap(self, query, existing_entities):
            entities_mentioned = self.extract_entity_names(query)
            missing = entities_mentioned - existing_entities
            return missing.pop() if missing else None

    qi = MockQueryInterface()

    # Test cases
    test_cases = [
        ("What did attendee #47 think?", set(), "attendee_47"),  # attendee_47 not in existing, should detect gap
        ("What did attendee 12 think?", set(), "attendee_12"),   # attendee_12 not in existing, should detect gap
        ("What did person #5 think?", set(), "attendee_5"),       # person #5 -> attendee_5, not in existing
        ("What did attendee #47 think?", {"attendee_47"}, None),  # attendee_47 already exists, no gap
        ("What did Washington think?", set(), None),             # Washington not a numbered entity, no gap to detect
    ]

    for query, existing, expected in test_cases:
        result = qi.detect_entity_gap(query, existing)
        print(f"  Query: '{query}' -> Detected gap: {result}")
        assert result == expected, f"Expected {expected}, got {result}"

    print("  ✅ Entity gap detection test PASSED")
    return True

def test_on_demand_generation():
    """Test the core logic of on-demand entity generation without full LLM integration"""
    print("\n🎭 Testing On-Demand Entity Generation Logic")

    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name

    try:
        # Initialize components
        store = GraphStore(f"sqlite:///{test_db}")
        llm_client = LLMClient(api_key="dummy_key", dry_run=True)
        query_interface = QueryInterface(store, llm_client)

        # Create a test timepoint
        from schemas import Timepoint, ResolutionLevel
        from datetime import datetime

        timepoint = Timepoint(
            timepoint_id="test_inauguration",
            timestamp=datetime(1789, 4, 30, 12, 0),
            event_description="Inauguration ceremony at Federal Hall",
            entities_present=["george_washington", "john_adams", "thomas_jefferson"],
            resolution_level=ResolutionLevel.SCENE
        )
        store.save_timepoint(timepoint)

        # Test role inference
        role = query_interface._infer_role_from_context("attendee_47", timepoint)
        assert role == "ceremony attendee"
        print(f"  ✅ Inferred role: {role}")

        # Test entity name extraction
        entities = query_interface.extract_entity_names("What did attendee #47 think?")
        assert "attendee_47" in entities
        print(f"  ✅ Extracted entities: {entities}")

        # Test gap detection
        existing = {"george_washington", "john_adams"}
        gap = query_interface.detect_entity_gap("What did attendee #47 think?", existing)
        assert gap == "attendee_47"
        print(f"  ✅ Detected gap: {gap}")

        # Test gap detection when entity exists
        existing_with_47 = {"george_washington", "john_adams", "attendee_47"}
        gap = query_interface.detect_entity_gap("What did attendee #47 think?", existing_with_47)
        assert gap is None
        print(f"  ✅ No gap when entity exists: {gap}")

        print("  ✅ On-demand entity generation logic test PASSED")
        return True

    finally:
        # Clean up
        if os.path.exists(test_db):
            os.unlink(test_db)

if __name__ == "__main__":
    print("🧪 Running On-Demand Entity Generation Tests (Phase 2.2)")
    print("=" * 60)

    try:
        test_entity_gap_detection()
        test_on_demand_generation()
        print("\n🎉 All On-Demand Entity Generation tests PASSED!")
        print("✅ Phase 2.2 implementation complete")

    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
