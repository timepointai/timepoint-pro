"""
M19 Knowledge Extraction Agent Test
====================================

Tests M19 (Knowledge Extraction Agent) which replaces naive capitalization-based
extraction with LLM-based semantic knowledge extraction.

Expected behavior:
1. Extracts complete semantic units, not single words
2. Correctly categorizes knowledge (fact, decision, opinion, etc.)
3. Ignores garbage (contractions, greetings, filler words)
4. Creates proper exposure events for listeners

The old naive extraction produced trash like ["we'll", "thanks", "what", "michael"].
M19 should produce meaningful items like ["Michael believes the deadline is unrealistic"].
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List

# Ensure we can import from project
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from schemas import KnowledgeItem, KnowledgeExtractionResult, Entity
from workflows.knowledge_extraction import (
    extract_knowledge_from_dialog,
    create_exposure_events_from_knowledge,
    build_causal_context,
    filter_high_relevance_knowledge,
    get_knowledge_by_category,
    summarize_extraction_result,
)
from workflows.dialog_synthesis import extract_knowledge_references
from llm_service.model_selector import ActionType, select_model_for_action


def test_deprecated_function():
    """Test that the deprecated extract_knowledge_references returns empty."""
    print("\n" + "="*60)
    print("TEST: Deprecated Function Returns Empty")
    print("="*60 + "\n")

    # The old function should now return empty
    result = extract_knowledge_references("Hello, We'll discuss What Michael said. Thanks!")

    print(f"Input: 'Hello, We'll discuss What Michael said. Thanks!'")
    print(f"Result: {result}")

    if result == []:
        print("\n[PASS] Deprecated function correctly returns empty list")
        return True
    else:
        print(f"\n[FAIL] Expected empty list, got: {result}")
        return False


def test_model_selection():
    """Test that KNOWLEDGE_EXTRACTION action type selects appropriate model."""
    print("\n" + "="*60)
    print("TEST: Model Selection for Knowledge Extraction")
    print("="*60 + "\n")

    try:
        model = select_model_for_action(ActionType.KNOWLEDGE_EXTRACTION)
        print(f"Selected model: {model}")

        # Should select a model with structured JSON and logical reasoning
        if model:
            print(f"\n[PASS] Model selected: {model}")
            return True
        else:
            print("\n[FAIL] No model selected")
            return False
    except Exception as e:
        print(f"\n[FAIL] Model selection error: {e}")
        return False


def test_filter_high_relevance():
    """Test filtering knowledge items by causal relevance."""
    print("\n" + "="*60)
    print("TEST: Filter High Relevance Knowledge")
    print("="*60 + "\n")

    # Create test items
    items = [
        KnowledgeItem(
            content="The budget was approved",
            speaker="ceo",
            listeners=["cfo", "cto"],
            category="decision",
            confidence=0.9,
            causal_relevance=0.8
        ),
        KnowledgeItem(
            content="It's a nice day",
            speaker="ceo",
            listeners=["cfo"],
            category="opinion",
            confidence=0.7,
            causal_relevance=0.2  # Low relevance
        ),
        KnowledgeItem(
            content="The competitor filed for bankruptcy",
            speaker="cfo",
            listeners=["ceo", "cto"],
            category="revelation",
            confidence=0.95,
            causal_relevance=0.9
        ),
    ]

    # Filter with 0.6 threshold
    filtered = filter_high_relevance_knowledge(items, min_relevance=0.6)

    print(f"Original items: {len(items)}")
    print(f"Filtered items (relevance >= 0.6): {len(filtered)}")

    for item in filtered:
        print(f"  - [{item.category}] {item.content} (relevance: {item.causal_relevance})")

    if len(filtered) == 2 and all(i.causal_relevance >= 0.6 for i in filtered):
        print("\n[PASS] High relevance filtering works correctly")
        return True
    else:
        print("\n[FAIL] Filtering did not work as expected")
        return False


def test_get_by_category():
    """Test filtering knowledge items by category."""
    print("\n" + "="*60)
    print("TEST: Get Knowledge by Category")
    print("="*60 + "\n")

    items = [
        KnowledgeItem(content="Budget approved", speaker="a", listeners=["b"], category="decision", confidence=0.9, causal_relevance=0.8),
        KnowledgeItem(content="Meeting at 3pm", speaker="a", listeners=["b"], category="fact", confidence=0.9, causal_relevance=0.5),
        KnowledgeItem(content="I think it's good", speaker="b", listeners=["a"], category="opinion", confidence=0.8, causal_relevance=0.3),
        KnowledgeItem(content="We'll launch Q3", speaker="a", listeners=["b"], category="plan", confidence=0.85, causal_relevance=0.7),
    ]

    facts = get_knowledge_by_category(items, "fact")
    decisions = get_knowledge_by_category(items, "decision")
    opinions = get_knowledge_by_category(items, "opinion")

    print(f"Total items: {len(items)}")
    print(f"Facts: {len(facts)}")
    print(f"Decisions: {len(decisions)}")
    print(f"Opinions: {len(opinions)}")

    if len(facts) == 1 and len(decisions) == 1 and len(opinions) == 1:
        print("\n[PASS] Category filtering works correctly")
        return True
    else:
        print("\n[FAIL] Category filtering did not work as expected")
        return False


def test_summarize_result():
    """Test the extraction result summarization."""
    print("\n" + "="*60)
    print("TEST: Summarize Extraction Result")
    print("="*60 + "\n")

    items = [
        KnowledgeItem(content="Budget approved", speaker="a", listeners=["b"], category="decision", confidence=0.9, causal_relevance=0.8),
        KnowledgeItem(content="Meeting at 3pm", speaker="a", listeners=["b"], category="fact", confidence=0.9, causal_relevance=0.5),
        KnowledgeItem(content="We'll launch Q3", speaker="a", listeners=["b"], category="plan", confidence=0.85, causal_relevance=0.7),
    ]

    result = KnowledgeExtractionResult(
        items=items,
        dialog_id="test_dialog",
        timepoint_id="test_tp",
        extraction_model="test_model",
        total_turns_analyzed=5,
        items_per_turn=0.6,
        extraction_timestamp=datetime.now()
    )

    summary = summarize_extraction_result(result)
    print(f"Summary: {summary}")

    if "3 knowledge items" in summary and "5 turns" in summary:
        print("\n[PASS] Summarization works correctly")
        return True
    else:
        print("\n[FAIL] Summary format unexpected")
        return False


def test_build_causal_context_empty():
    """Test causal context building with no store."""
    print("\n" + "="*60)
    print("TEST: Build Causal Context (No Store)")
    print("="*60 + "\n")

    # Create test entities
    entities = [
        Entity(entity_id="entity_a", entity_metadata={"knowledge_state": ["fact 1", "fact 2"]}),
        Entity(entity_id="entity_b", entity_metadata={"knowledge_state": ["fact 3"]}),
    ]

    context = build_causal_context(entities, store=None)
    print(f"Context: {context}")

    if "first interaction" in context.lower() or "no prior knowledge" in context.lower():
        print("\n[PASS] Empty store context handled correctly")
        return True
    else:
        print("\n[FAIL] Unexpected context for empty store")
        return False


def main():
    """Run all M19 tests."""
    print("\n" + "="*80)
    print("M19 KNOWLEDGE EXTRACTION AGENT TESTS")
    print("="*80 + "\n")

    print("Goal: Test M19 (Knowledge Extraction Agent)")
    print("Expected: LLM-based semantic extraction, not naive word grabbing")
    print("Success: All unit tests pass\n")

    results = []

    # Run unit tests (don't require LLM calls)
    results.append(("Deprecated Function", test_deprecated_function()))
    results.append(("Model Selection", test_model_selection()))
    results.append(("High Relevance Filter", test_filter_high_relevance()))
    results.append(("Category Filter", test_get_by_category()))
    results.append(("Summarize Result", test_summarize_result()))
    results.append(("Causal Context (Empty)", test_build_causal_context_empty()))

    # Summary
    print("\n" + "="*80)
    print("M19 TEST RESULTS")
    print("="*80)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All M19 unit tests passed!")
        print("Note: E2E tests require running a full simulation with --template")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
