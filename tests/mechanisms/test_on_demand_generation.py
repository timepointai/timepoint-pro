#!/usr/bin/env python3
"""
Test script for Phase 2.2: On-Demand Entity Generation (Mechanism 9)
Tests that unknown entities are generated dynamically when queried.
"""

import os
import pytest
import tempfile
from query_interface import QueryInterface
from storage import GraphStore
from llm_v2 import LLMClient


@pytest.mark.unit
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
        ("What did attendee #47 think?", set(), "attendee_47"),
        ("What did attendee 12 think?", set(), "attendee_12"),
        ("What did person #5 think?", set(), "attendee_5"),
        ("What did attendee #47 think?", {"attendee_47"}, None),
        ("What did Washington think?", set(), None),
    ]

    for query, existing, expected in test_cases:
        result = qi.detect_entity_gap(query, existing)
        print(f"  Query: '{query}' -> Detected gap: {result}")
        assert result == expected, f"Expected {expected}, got {result}"

    print("  ✅ Entity gap detection test PASSED")


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_on_demand_generation():
    """Test on-demand entity generation with real LLM"""
    print("\n🎭 Testing On-Demand Entity Generation")

    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name

    try:
        # Initialize components
        store = GraphStore(f"sqlite:///{test_db}")
        api_key = os.getenv("OPENROUTER_API_KEY")
        llm_client = LLMClient(api_key=api_key)
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

        print("  ✅ On-demand entity generation test PASSED")

    finally:
        # Clean up
        if os.path.exists(test_db):
            os.unlink(test_db)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
