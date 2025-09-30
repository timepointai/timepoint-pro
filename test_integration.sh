#!/bin/bash
set -e

echo "Running integration tests..."

# Clean slate
rm -f timepoint.db reports/*

# Test 1: Training creates entities
echo "Test 1: Training mode..."
poetry run python cli.py mode=train training.graph_size=5 training.context=""
ENTITY_COUNT=$(poetry run python -c "from storage import GraphStore; from sqlmodel import Session, select; from schemas import Entity; store = GraphStore(); print(len(list(Session(store.engine).exec(select(Entity)))))")

if [ "$ENTITY_COUNT" -eq "5" ]; then
    echo "✓ Training created 5 entities"
else
    echo "✗ Training failed: expected 5 entities, got $ENTITY_COUNT"
    exit 1
fi

# Test 2: Evaluation finds entities
echo "Test 2: Evaluation mode..."
OUTPUT=$(poetry run python cli.py mode=evaluate)
if echo "$OUTPUT" | grep -q "entity_"; then
    echo "✓ Evaluation found entities"
else
    echo "✗ Evaluation failed: no entities found"
    exit 1
fi

# Test 3: Autopilot generates reports
echo "Test 3: Autopilot mode..."
poetry run python cli.py mode=autopilot autopilot.graph_sizes="[5]"
if [ -f "reports/autopilot_report_"*.json ]; then
    echo "✓ Autopilot generated reports"
else
    echo "✗ Autopilot failed: no reports generated"
    exit 1
fi

echo "All integration tests passed!"
