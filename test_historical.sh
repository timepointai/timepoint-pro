#!/bin/bash

echo "Testing Historical Training Mode..."

# Test 1: Founding Fathers context
echo "Test 1: Founding Fathers 1789..."
rm -f timepoint.db
poetry run python cli.py mode=train training.context=founding_fathers_1789

# Verify entities
echo "Verifying Founding Fathers entities..."
poetry run python -c "
from storage import GraphStore
from sqlmodel import Session, select
from schemas import Entity
store = GraphStore()
with Session(store.engine) as session:
    entities = session.exec(select(Entity)).all()
    for entity in entities:
        print(f'✓ {entity.entity_id} ({entity.entity_metadata[\"role\"]}) - Age: {entity.entity_metadata[\"age\"]}, Location: {entity.entity_metadata[\"location\"]}')
"

# Test evaluation
echo ""
echo "Evaluating historical entities..."
poetry run python cli.py mode=evaluate

# Test 2: Renaissance Florence context
echo ""
echo "Test 2: Renaissance Florence 1504..."
rm -f timepoint.db
poetry run python cli.py mode=train training.context=renaissance_florence_1504

# Verify entities
echo "Verifying Renaissance entities..."
poetry run python -c "
from storage import GraphStore
from sqlmodel import Session, select
from schemas import Entity
store = GraphStore()
with Session(store.engine) as session:
    entities = session.exec(select(Entity)).all()
    for entity in entities:
        print(f'✓ {entity.entity_id} ({entity.entity_metadata[\"role\"]}) - Age: {entity.entity_metadata[\"age\"]}, Location: {entity.entity_metadata[\"location\"]}')
"

echo ""
echo "Historical training mode tests completed successfully!"
