#!/usr/bin/env python3
"""Quick verification that JSON extraction works with real log samples."""

from tensor_initialization import _extract_json_from_response
import json

# Test samples from actual logs (lines 7, 8, 9)
test_cases = [
    ('Sample 1', 'Here is the suggested fix:\n\n{"fixes": {"context": [0.1], "biology": [], "behavior": []}}\n\nExplanation...'),
    ('Sample 2', '''Here is the JSON output with suggested non-zero values:

```
{
  "fixes": {
    "context": [0.1, 0.5, 0.3, 1.0, 0.5, 0.5, 0.5, 0.5],
    "biology": [],
    "behavior": []
  }
}
```'''),
    ('Sample 3', '''Here is the suggested fix in JSON format:

```json
{
  "fixes": {
    "context": [0.05, 0.5, 0.3, 1.0, 0.5, 0.5, 0.5, 0.5],
    "biology": [0.35, 0.8, 1.0, 0.8],
    "behavior": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
  }
}
```

Explanation: The suggested values...'''),
]

print("="*80)
print("PHASE 1: Direct Function Test")
print("="*80)

passed = 0
failed = 0

for name, sample in test_cases:
    try:
        extracted = _extract_json_from_response(sample)
        parsed = json.loads(extracted)
        print(f"✅ {name}: PASS")
        print(f"   Extracted: {extracted[:80]}...")
        passed += 1
    except Exception as e:
        print(f"❌ {name}: FAIL - {e}")
        failed += 1

print(f"\nResults: {passed}/{len(test_cases)} passed")
print("="*80)

if passed == len(test_cases):
    print("🎉 Extraction function works correctly in isolation!")
    exit(0)
else:
    print("⚠️  Extraction function has issues")
    exit(1)
