#!/usr/bin/env python3
"""Query OpenRouter API for available Llama models and pricing."""

import httpx
import json
import os

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("❌ No OPENROUTER_API_KEY found")
    exit(1)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

with httpx.Client(timeout=10.0) as client:
    response = client.get("https://openrouter.ai/api/v1/models", headers=headers)
    response.raise_for_status()

data = response.json()
all_models = data.get("data", [])

# Filter for Llama 3.1 models (70B and 405B)
target_models = []
for model in all_models:
    model_id = model.get("id", "")
    name = model.get("name", "")

    # Look for Llama 3.1 70B or 405B models
    is_target = (
        ("llama" in model_id.lower() or "llama" in name.lower()) and
        ("3.1" in model_id or "3.1" in name or "3-1" in model_id) and
        ("70b" in model_id.lower() or "405b" in model_id.lower() or
         "70b" in name.lower() or "405b" in name.lower())
    )

    if is_target:
        pricing = model.get("pricing", {})
        prompt_price = float(pricing.get("prompt", "0"))
        completion_price = float(pricing.get("completion", "0"))

        # Determine if free (price = 0) or paid
        is_free = (prompt_price == 0 and completion_price == 0)

        target_models.append({
            "id": model_id,
            "name": name,
            "context_length": model.get("context_length", 0),
            "prompt_price": prompt_price,
            "completion_price": completion_price,
            "is_free": is_free,
            "is_paid": not is_free,
            "description": model.get("description", "")[:100]
        })

# Sort by size (70B first, then 405B) and price
target_models.sort(key=lambda x: (
    0 if "70b" in x["id"].lower() else 1,  # 70B models first
    x["prompt_price"]  # Then by price
))

print("=" * 80)
print("🦙 LLAMA 3.1 MODELS ON OPENROUTER (70B & 405B)")
print("=" * 80)

if not target_models:
    print("❌ No Llama 3.1 70B/405B models found!")
else:
    for model in target_models:
        free_paid = "🆓 FREE" if model["is_free"] else "💰 PAID"
        size = "70B" if "70b" in model["id"].lower() else "405B"

        print(f"\n{free_paid} - {size}")
        print(f"  ID: {model['id']}")
        print(f"  Name: {model['name']}")
        print(f"  Context: {model['context_length']:,} tokens")
        print(f"  Pricing:")
        print(f"    - Prompt: ${model['prompt_price']:.6f} per token")
        print(f"    - Completion: ${model['completion_price']:.6f} per token")
        if model["description"]:
            print(f"  Description: {model['description']}")

print("\n" + "=" * 80)
print(f"Total models found: {len(target_models)}")
