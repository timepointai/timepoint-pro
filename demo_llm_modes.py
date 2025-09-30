#!/usr/bin/env python3
"""
Demo script showing the difference between dry-run and real LLM testing modes.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from llm import LLMClient

def main():
    print("🔥 Timepoint-Daedalus LLM Testing Demo")
    print("=" * 50)

    # Get API key and create LLM client
    api_key = os.getenv('OPENROUTER_API_KEY')

    if api_key:
        print("🔴 Using REAL LLM CLIENT (API key detected)")
        client = LLMClient(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            dry_run=False
        )
    else:
        print("🟢 Using DRY-RUN LLM CLIENT (no API key - set OPENROUTER_API_KEY for real calls)")
        client = LLMClient(api_key="test", base_url="http://test", dry_run=True)

    print(f"🤖 LLM Client Mode: {'🔴 REAL LLM' if not client.dry_run else '🟢 DRY-RUN'}")
    print(f"📊 Initial Cost: ${client.cost:.4f}")
    print(f"📊 Initial Tokens: {client.token_count}")
    print()

    # Test entity population
    print("🧪 Testing entity population...")
    entity_schema = {"entity_id": "demo_entity", "timestamp": "2025-01-01"}
    context = {"exposure_history": ["learned_fact_1", "learned_fact_2"]}

    result = client.populate_entity(entity_schema, context)

    print(f"✅ Entity ID: {result.entity_id}")
    print(f"🧠 Knowledge items: {len(result.knowledge_state)}")
    print(f"⚡ Energy budget: {result.energy_budget:.1f}/100")
    print(f"🫂 Personality traits: {len(result.personality_traits)} values")
    print(f"⏰ Temporal awareness: {result.temporal_awareness[:50]}...")
    print(f"🎯 Confidence: {result.confidence:.2f}")
    print()

    # Test consistency validation
    print("🔍 Testing consistency validation...")
    entities = [{"id": "demo_entity", "traits": result.personality_traits}]
    from datetime import datetime
    validation = client.validate_consistency(entities, datetime.now())

    print(f"✅ Valid: {validation.is_valid}")
    print(f"⚠️  Violations: {len(validation.violations)}")
    print(f"🎯 Confidence: {validation.confidence:.2f}")
    print()

    # Final stats
    print("💰 Final Cost Tracking:")
    print(f"   Cost: ${client.cost:.4f}")
    print(f"   Tokens: {client.token_count}")
    print(f"   Mode: {'Real API calls' if not client.dry_run else 'Mock responses'}")
    print()

    if client.dry_run:
        print("💡 TIP: Set OPENROUTER_API_KEY to test with real LLM calls!")
        print("   export OPENROUTER_API_KEY='your_key_here'")
        print("   python demo_llm_modes.py")
    else:
        print("🚀 You're testing with real LLM calls!")

if __name__ == "__main__":
    main()
