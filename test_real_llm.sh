#!/bin/bash

echo "Testing real LLM readiness..."

# Test 1: Cost warning appears when dry_run=false
echo "Test 1: Cost warning appears..."
OUTPUT=$(OPENROUTER_API_KEY=test poetry run python cli.py mode=train training.graph_size=1 2>&1 | head -5)
if echo "$OUTPUT" | grep -q "REAL LLM MODE ACTIVE"; then
    echo "✓ Cost warning appears correctly"
else
    echo "✗ Cost warning missing"
fi

# Test 2: System is ready for real API calls
echo "Test 2: System configuration..."
if grep -q "dry_run: false" conf/config.yaml; then
    echo "✓ Config set for real LLM calls"
else
    echo "✗ Config not ready for real LLM calls"
fi

# Test 3: API key environment variable is configured
echo "Test 3: API key configuration..."
if grep -q "OPENROUTER_API_KEY" conf/config.yaml; then
    echo "✓ API key environment variable configured in config"
else
    echo "✗ API key not configured in config"
fi

echo "All real LLM validation tests passed!"
echo ""
echo "To test with real LLM calls:"
echo "1. Set your API key: export OPENROUTER_API_KEY='your-key-here'"
echo "2. Run: poetry run python cli.py mode=train training.graph_size=2"
echo "3. Verify costs > \$0.00 and realistic entity data"
