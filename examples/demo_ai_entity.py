#!/usr/bin/env python3
"""
demo_ai_entity.py - Demonstration of AI Entity functionality

Shows how to create and interact with AI entities in the timepoint simulation.
"""
import asyncio
from datetime import datetime

from schemas import AIEntity, Entity
from workflows import create_animistic_entity
from ai_entity_service import AIEntityService, AIRequest


async def demo_ai_entity_creation():
    """Demonstrate creating an AI entity"""
    print("🔮 Creating an AI Entity...")

    # Create an AI entity using the workflow system
    context = {
        "timepoint_context": "modern_digital_age",
        "location": "silicon_valley"
    }

    config = {
        "animism": {
            "level": 6,  # Enable AI entities
            "ai_defaults": {
                "temperature": 0.8,
                "model_name": "gpt-4",
                "safety_level": "strict",
                "activation_threshold": 0.7
            }
        }
    }

    entity = create_animistic_entity("oracle_ai", "ai", context, config)

    print(f"✅ Created AI Entity: {entity.entity_id}")
    print(f"   Type: {entity.entity_type}")
    print(f"   Resolution: {entity.resolution_level}")

    # Extract and display AI metadata
    ai_entity = AIEntity(**entity.entity_metadata)
    print("\n🤖 AI Configuration:")
    print(f"   Model: {ai_entity.model_name}")
    print(f"   Temperature: {ai_entity.temperature}")
    print(f"   Safety Level: {ai_entity.safety_level}")
    print(f"   Input Rules: {len(ai_entity.input_bleaching_rules)}")
    print(f"   Output Rules: {len(ai_entity.output_filtering_rules)}")

    return entity


async def demo_ai_service():
    """Demonstrate AI entity service functionality"""
    print("\n🌐 Starting AI Entity Service...")

    # Service configuration
    config = {
        "ai_entity_service": {
            "host": "localhost",
            "port": 8001,
            "api_keys_required": False,
            "log_level": "INFO"
        },
        "llm": {"api_key": "demo_key"},
        "animism": {"ai_defaults": {}}
    }

    # Initialize service
    service = AIEntityService(config)

    print("✅ AI Entity Service initialized")
    print("   Note: This demo uses mock responses since no real LLM is configured")
    # Create a sample AI entity in storage (simulated)
    ai_entity = AIEntity(
        temperature=0.7,
        top_p=0.9,
        max_tokens=150,
        model_name="demo-model",
        safety_level="moderate",
        input_bleaching_rules=["remove_script_tags"],
        output_filtering_rules=["filter_harmful_content"],
        error_handling={"api_error": "Demo service unavailable"},
        fallback_responses=["This is a demo response."]
    )

    # Simulate storing the entity
    entity = Entity(
        entity_id="demo_ai",
        entity_type="ai",
        entity_metadata=ai_entity.dict(),
        temporal_span_start=datetime.now()
    )

    print(f"📝 Created demo AI entity: {entity.entity_id}")

    # Simulate a chat request
    print("\n💬 Simulating AI interaction...")

    # Create a mock request
    class MockRequest:
        def __init__(self):
            self.entity_id = "demo_ai"
            self.message = "Hello, what can you tell me about temporal causality?"
            self.context = {"domain": "philosophy"}
            self.session_id = "demo_session_123"

    request = MockRequest()

    # Process through the runner (would normally call LLM)
    runner = service.runner

    # Mock the load_entity method to return our demo entity
    original_load = runner.load_entity
    runner.load_entity = lambda eid: ai_entity if eid == "demo_ai" else original_load(eid)

    try:
        response = await runner.process_request(request)
        print(f"🤖 AI Response: {response.response}")
        print(f"   Session: {response.session_id}")
        print(f"   Warnings: {len(response.safety_warnings)}")

    except Exception as e:
        print(f"⚠️  Service interaction failed: {e}")
        print("   This is expected in demo mode without real LLM integration")

    # Restore original method
    runner.load_entity = original_load


async def demo_safety_features():
    """Demonstrate safety features"""
    print("\n🛡️  Demonstrating Safety Features...")

    from ai_entity_service import InputBleacher, OutputFilter

    # Test input bleaching
    bleacher = InputBleacher()

    dangerous_input = '<script>alert("hack")</script>Hello <b>world</b>'
    clean_input, warnings = bleacher.bleach_input(
        dangerous_input,
        ["remove_script_tags"]
    )

    print(f"🧹 Input Bleaching:")
    print(f"   Original: {dangerous_input}")
    print(f"   Cleaned: {clean_input}")
    print(f"   Warnings: {warnings}")

    # Test output filtering
    filter = OutputFilter()

    harmful_output = "This contains violent content and personal.email@example.com"
    filtered_output, filter_warnings = filter.filter_output(
        harmful_output,
        ["remove_pii", "filter_harmful_content"]
    )

    print(f"\n🔍 Output Filtering:")
    print(f"   Original: {harmful_output}")
    print(f"   Filtered: {filtered_output}")
    print(f"   Warnings: {filter_warnings}")


async def main():
    """Main demo function"""
    print("🚀 AI Entity Demonstration")
    print("=" * 50)

    try:
        # Demo 1: Entity creation
        await demo_ai_entity_creation()

        # Demo 2: Safety features
        await demo_safety_features()

        # Demo 3: Service functionality
        await demo_ai_service()

        print("\n✨ Demo completed successfully!")
        print("\n📚 To use in production:")
        print("   1. Configure real LLM API keys")
        print("   2. Set animism.level = 6 in config.yaml")
        print("   3. Run: python ai_entity_service.py")
        print("   4. API available at http://localhost:8001")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
