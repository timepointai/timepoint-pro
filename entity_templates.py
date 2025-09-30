HISTORICAL_CONTEXTS = {
    "founding_fathers_1789": {
        "entities": [
            {"entity_id": "george_washington", "role": "president", "age": 57, "location": "new_york"},
            {"entity_id": "john_adams", "role": "vice_president", "age": 53, "location": "new_york"},
            {"entity_id": "thomas_jefferson", "role": "secretary_of_state", "age": 46, "location": "paris"},
            {"entity_id": "alexander_hamilton", "role": "treasury_secretary", "age": 34, "location": "new_york"},
            {"entity_id": "james_madison", "role": "congressman", "age": 38, "location": "new_york"}
        ],
        "timepoint": "1789-04-30",
        "event": "First Presidential Inauguration",
        "relationships": [
            ("george_washington", "john_adams", "political_alliance"),
            ("george_washington", "alexander_hamilton", "mentor_protege"),
            ("thomas_jefferson", "james_madison", "close_friendship"),
            ("alexander_hamilton", "thomas_jefferson", "political_rivalry")
        ]
    },
    
    "renaissance_florence_1504": {
        "entities": [
            {"entity_id": "leonardo_da_vinci", "role": "artist", "age": 52, "location": "florence"},
            {"entity_id": "michelangelo_buonarroti", "role": "sculptor", "age": 29, "location": "florence"},
            {"entity_id": "niccolo_machiavelli", "role": "diplomat", "age": 35, "location": "florence"},
            {"entity_id": "cesare_borgia", "role": "military_commander", "age": 29, "location": "rome"}
        ],
        "timepoint": "1504-01-25",
        "event": "David sculpture unveiling debate",
        "relationships": [
            ("leonardo_da_vinci", "michelangelo_buonarroti", "artistic_rivalry"),
            ("niccolo_machiavelli", "cesare_borgia", "political_observation"),
            ("leonardo_da_vinci", "cesare_borgia", "military_engineering")
        ]
    }
}

def get_context_prompt(context_name: str) -> str:
    """Generate rich prompt for LLM based on historical context"""
    context = HISTORICAL_CONTEXTS[context_name]
    
    return f"""You are simulating historical figures in the context of: {context['event']}
Date: {context['timepoint']}

Generate realistic personality traits and knowledge for this entity based on historical records.
Consider:
- Their actual historical role and relationships
- Knowledge available at this time period (no anachronisms)
- Their documented personality and beliefs
- Their physical and mental state at this age
- Their goals and motivations during this period

Respond with structured data that captures their authentic historical character."""