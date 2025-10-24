"""
Demonstration: Negotiation Variations (ML Dataset)
Simple demonstration showing the configuration structure.
"""
import json

print("=" * 80)
print("NEGOTIATION VARIATIONS - ML DATASET GENERATION")
print("=" * 80)
print()

# Step 1: Base Configuration
print("STEP 1: Base Configuration")
print("-" * 80)

base_config = {
    "scenario_description": "Corporate merger negotiation between two companies",
    "entities": [
        {
            "name": "Alex Chen",
            "role": "CEO of acquiring company",
            "personality_traits": {
                "openness": 0.7,
                "conscientiousness": 0.8,
                "extraversion": 0.6,
                "agreeableness": 0.5,
                "neuroticism": 0.3
            }
        },
        {
            "name": "Jordan Martinez",
            "role": "CEO of target company",
            "personality_traits": {
                "openness": 0.6,
                "conscientiousness": 0.7,
                "extraversion": 0.5,
                "agreeableness": 0.6,
                "neuroticism": 0.4
            }
        },
        {
            "name": "Sam Kim",
            "role": "Legal advisor",
            "personality_traits": {
                "openness": 0.5,
                "conscientiousness": 0.9,
                "extraversion": 0.4,
                "agreeableness": 0.5,
                "neuroticism": 0.3
            }
        },
        {
            "name": "Riley Thompson",
            "role": "Financial analyst",
            "personality_traits": {
                "openness": 0.6,
                "conscientiousness": 0.8,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.4
            }
        }
    ],
    "timepoints": {
        "count": 2,
        "interval_minutes": 30
    },
    "generation_mode": "horizontal",
    "variation_config": {
        "count": 100,
        "strategy": "vary_personalities"
    },
    "temporal_mode": "pearl",
    "focus_areas": ["dialog", "decision_making", "relationships"],
    "output_types": ["dialog", "decisions", "relationships"]
}

print(f"Scenario: {base_config['scenario_description']}")
print(f"Entities: {len(base_config['entities'])}")
for i, entity in enumerate(base_config['entities'], 1):
    print(f"  {i}. {entity['name']} ({entity['role']})")
print(f"Timepoints: {base_config['timepoints']['count']}")
print(f"Generation mode: {base_config['generation_mode']}")
print(f"Variation count: {base_config['variation_config']['count']}")
print(f"Variation strategy: {base_config['variation_config']['strategy']}")
print()

# Step 2: Generate Sample Variations
print("STEP 2: Sample Variations (personality variations)")
print("-" * 80)

variations = []
import random
random.seed(42)

for var_num in range(10):  # Generate 10 sample variations
    variation = {
        "variation_id": var_num,
        "scenario": base_config["scenario_description"],
        "entities": []
    }

    for entity in base_config["entities"]:
        varied_entity = {
            "name": entity["name"],
            "role": entity["role"],
            "personality_traits": {
                trait: max(0.0, min(1.0, value + random.gauss(0, 0.15)))
                for trait, value in entity["personality_traits"].items()
            }
        }
        variation["entities"].append(varied_entity)

    variation["timepoints"] = base_config["timepoints"]["count"]
    variation["focus_areas"] = base_config["focus_areas"]
    variations.append(variation)

print(f"✅ Generated {len(variations)} sample variations")
print()

# Step 3: Show sample variations
print("STEP 3: Sample Variation Details")
print("-" * 80)

for i in range(3):
    var = variations[i]
    print(f"\nVariation {i+1}:")
    print(f"  Scenario: {var['scenario']}")
    print(f"  Entities:")
    for entity in var['entities']:
        print(f"    • {entity['name']} ({entity['role']})")
        traits = entity['personality_traits']
        print(f"      O:{traits['openness']:.2f} C:{traits['conscientiousness']:.2f} " +
              f"E:{traits['extraversion']:.2f} A:{traits['agreeableness']:.2f} " +
              f"N:{traits['neuroticism']:.2f}")
    print(f"  Timepoints: {var['timepoints']}")
    print(f"  Focus: {', '.join(var['focus_areas'])}")

print()

# Step 4: Diversity Analysis
print("STEP 4: Diversity Analysis")
print("-" * 80)

# Calculate personality variance across variations
trait_variances = {trait: [] for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']}

for var in variations:
    for entity in var['entities']:
        for trait, value in entity['personality_traits'].items():
            trait_variances[trait].append(value)

avg_variance = sum(
    (max(values) - min(values)) for values in trait_variances.values()
) / len(trait_variances)

print(f"Personality trait variance:")
for trait, values in trait_variances.items():
    print(f"  {trait.capitalize()}: {min(values):.2f} - {max(values):.2f} (range: {max(values)-min(values):.2f})")

print(f"\nAverage trait range: {avg_variance:.3f}")
print(f"Diversity score: {min(1.0, avg_variance / 0.5):.3f}")
print()

# Step 5: Export format
print("STEP 5: JSONL Export Format (for ML training)")
print("-" * 80)
print("First 2 records in JSONL format:")
print()

for i in range(2):
    print(json.dumps(variations[i]))

print()

# Step 6: Cost estimation
print("STEP 6: Cost Estimation")
print("-" * 80)

# Rough cost estimation
entities_per_var = len(base_config['entities'])
timepoints = base_config['timepoints']['count']
tokens_per_entity_per_tp = 10000  # Dialog mode
total_tokens_per_var = entities_per_var * timepoints * tokens_per_entity_per_tp
cost_per_1k_tokens = 0.002
cost_per_variation = (total_tokens_per_var / 1000) * cost_per_1k_tokens

print(f"Configuration:")
print(f"  Entities per variation: {entities_per_var}")
print(f"  Timepoints: {timepoints}")
print(f"  Estimated tokens per entity per timepoint: {tokens_per_entity_per_tp:,}")
print(f"  Total tokens per variation: {total_tokens_per_var:,}")
print()
print(f"Cost Estimation:")
print(f"  Cost per 1K tokens: ${cost_per_1k_tokens}")
print(f"  Cost per variation: ${cost_per_variation:.2f}")
print(f"  Cost for 10 variations (demo): ${cost_per_variation * 10:.2f}")
print(f"  Cost for 100 variations (full): ${cost_per_variation * 100:.2f}")
print()

# Step 7: Summary
print("=" * 80)
print("SUMMARY: Negotiation Variations ML Dataset")
print("=" * 80)
print()
print(f"✅ Base Scenario: {base_config['scenario_description']}")
print(f"✅ Variations Generated: {len(variations)} (demo) / {base_config['variation_config']['count']} (target)")
print(f"✅ Diversity Score: {min(1.0, avg_variance / 0.5):.3f}")
print(f"✅ Export Format: JSONL (ready for ML pipelines)")
print(f"✅ Estimated Cost (100 variations): ${cost_per_variation * 100:.2f}")
print()
print("Key Features:")
print("  • Personality variation strategy creates diverse scenarios")
print("  • 4 entities × 2 timepoints × 100 variations = 800 entity-timepoint pairs")
print("  • Each variation has different personality trait distributions")
print("  • JSONL export format for streaming ML training")
print("  • Focus areas: dialog, decision_making, relationships")
print()
print("Use Cases:")
print("  • Train ML models on negotiation dynamics")
print("  • Study how personality affects negotiation outcomes")
print("  • Generate labeled training data for dialog systems")
print("  • Analyze relationship evolution patterns")
print()
print("=" * 80)
print("DEMONSTRATION COMPLETE ✅")
print("=" * 80)
