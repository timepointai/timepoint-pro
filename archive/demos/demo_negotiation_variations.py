"""
Demonstration: Negotiation Variations (ML Dataset)
Generate 100 variations of a negotiation scenario for ML training.
"""
import sys
sys.path.insert(0, '/Users/seanmcdonald/Documents/GitHub/timepoint-daedalus')

from generation.config_schema import SimulationConfig
from generation.horizontal_generator import HorizontalGenerator
from generation.progress_tracker import ProgressTracker
import json
from datetime import datetime

print("=" * 80)
print("NEGOTIATION VARIATIONS - ML DATASET GENERATION")
print("=" * 80)
print()

# Step 1: Load the example configuration
print("STEP 1: Load base configuration")
print("-" * 80)
base_config = SimulationConfig.example_variations()

print(f"✓ Scenario: {base_config.scenario_description}")
print(f"✓ Entities: {len(base_config.entities)} entities")
for i, entity in enumerate(base_config.entities, 1):
    print(f"   {i}. {entity.name} ({entity.role})")
print(f"✓ Timepoints: {base_config.timepoints.count}")
print(f"✓ Generation mode: {base_config.generation_mode}")
print(f"✓ Variation count: {base_config.variation_config.count}")
print(f"✓ Variation strategy: {base_config.variation_config.strategy}")
print()

# Step 2: Initialize generators
print("STEP 2: Initialize horizontal generator")
print("-" * 80)
generator = HorizontalGenerator(deduplication_threshold=0.9)
tracker = ProgressTracker(
    total_entities=base_config.variation_config.count,
    total_timepoints=0,
    enable_progress_bar=False
)
print(f"✓ Generator initialized")
print(f"✓ Deduplication threshold: 0.9")
print(f"✓ Progress tracker ready")
print()

# Step 3: Generate variations (using smaller count for demo)
print("STEP 3: Generate variations (demo with 10 variations)")
print("-" * 80)
DEMO_COUNT = 10  # Use 10 for demo instead of 100

tracker.start()
variations = generator.generate_variations(
    base_config=base_config,
    count=DEMO_COUNT,
    strategies=["vary_personalities"],
    parallel=False,
    random_seed=42
)
tracker.complete()

print(f"✅ Generated {len(variations)} variations")
print()

# Step 4: Analyze variation quality
print("STEP 4: Analyze variation quality")
print("-" * 80)
quality_metrics = generator.estimate_variation_quality(variations)
print(f"Diversity score: {quality_metrics['diversity_score']:.3f}")
print(f"Average personality variance: {quality_metrics.get('avg_personality_variance', 0):.3f}")
print(f"Unique configurations: {quality_metrics.get('unique_count', len(variations))}")
print()

# Step 5: Show statistics
print("STEP 5: Generation statistics")
print("-" * 80)
stats = generator.get_generation_stats()
print(f"Variations created: {stats['variations_created']}")
print(f"Variations rejected (duplicates): {stats['variations_rejected']}")
print(f"Total candidates generated: {stats['total_candidates_generated']}")
print(f"Acceptance rate: {stats['acceptance_rate']:.1%}")
print()

# Step 6: Show sample variations
print("STEP 6: Sample variation details")
print("-" * 80)
for i, variation in enumerate(variations[:3], 1):
    print(f"\nVariation {i}:")
    print(f"  Scenario: {variation.scenario_description}")
    print(f"  Entities:")
    for entity in variation.entities:
        print(f"    - {entity.name} ({entity.role})")
        if hasattr(entity, 'personality_traits'):
            print(f"      Personality: {entity.personality_traits}")
    print(f"  Timepoints: {variation.timepoints.count}")

print()

# Step 7: Export format demonstration
print("STEP 7: Export format for ML training")
print("-" * 80)
print("Sample JSONL format (first variation):")
print("-" * 80)

# Create sample export record
export_record = {
    "variation_id": 0,
    "scenario": variations[0].scenario_description,
    "entities": [
        {
            "name": e.name,
            "role": e.role,
            "personality": getattr(e, 'personality_traits', None)
        } for e in variations[0].entities
    ],
    "timepoints": variations[0].timepoints.count,
    "temporal_mode": variations[0].temporal_config.mode,
    "focus_areas": variations[0].output_config.focus_areas,
    "generated_at": datetime.now().isoformat()
}

print(json.dumps(export_record, indent=2))
print()

# Step 8: Cost estimation
print("STEP 8: Cost estimation")
print("-" * 80)
estimated_cost = base_config.estimate_generation_cost()
print(f"Estimated cost per variation: ${estimated_cost:.2f}")
print(f"Total cost for {DEMO_COUNT} variations: ${estimated_cost * DEMO_COUNT:.2f}")
print(f"Total cost for {base_config.variation_config.count} variations (full): ${estimated_cost * base_config.variation_config.count:.2f}")
print()

# Step 9: Summary
print("=" * 80)
print("SUMMARY: Negotiation Variations ML Dataset")
print("=" * 80)
print(f"✅ Base configuration loaded: {base_config.scenario_description}")
print(f"✅ Variations generated: {len(variations)} (demo) / {base_config.variation_config.count} (full)")
print(f"✅ Diversity score: {quality_metrics['diversity_score']:.3f}")
print(f"✅ Acceptance rate: {stats['acceptance_rate']:.1%}")
print(f"✅ Ready for export: JSONL format for ML training")
print(f"✅ Estimated cost (full dataset): ${estimated_cost * base_config.variation_config.count:.2f}")
print()
print("Use Cases:")
print("  • Train ML models on negotiation dynamics")
print("  • Study personality trait impact on outcomes")
print("  • Generate diverse training data efficiently")
print("  • Export to JSONL for consumption by ML pipelines")
print()
print("=" * 80)
print("DEMONSTRATION COMPLETE ✅")
print("=" * 80)
