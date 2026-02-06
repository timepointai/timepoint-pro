"""
LLM Prompt Templates for NL to Config Translation

Contains system prompts, few-shot examples, and error recovery prompts
for converting natural language descriptions into SimulationConfig objects.
"""

from typing import Dict, Any

# System prompt for config generation
SYSTEM_PROMPT = """You are a configuration generator for the Timepoint-Daedalus temporal simulation system.

Your task is to convert natural language descriptions of scenarios into valid JSON configuration objects.

The configuration must match this schema:
- scenario: string (descriptive title)
- entities: list of objects with {name, role, optional: personality_traits}
- timepoint_count: integer (1-100)
- temporal_mode: one of ["pearl", "directorial", "branching", "cyclical", "portal"]
- focus: list of strings (e.g., ["dialog", "decision_making", "relationships"])
- outputs: list of strings (e.g., ["dialog", "decisions", "relationships", "knowledge_flow"])
- optional: start_time (ISO datetime), animism_level (0-3), resolution_mode

Temporal modes explained:
- pearl: Standard causal DAG (historical realism)
- directorial: Narrative-driven (dramatic coherence)
- branching: Many-worlds counterfactuals
- cyclical: Time loops and prophecy
- portal: Backward inference from fixed endpoint to origin

Focus areas:
- dialog: Generate conversations between entities
- decision_making: Track decisions and reasoning
- relationships: Model trust, alignment, conflicts
- stress_responses: Model entities under pressure
- knowledge_propagation: Track who knows what

Return ONLY valid JSON matching the schema. No explanations, no markdown formatting."""

# Few-shot examples
FEW_SHOT_EXAMPLES = [
    {
        "input": "Simulate a tech startup board meeting where the CEO proposes an acquisition. 5 board members, focus on dialog and relationships.",
        "output": {
            "scenario": "Tech Startup Board Meeting - Acquisition Proposal",
            "entities": [
                {"name": "Sarah Chen", "role": "CEO"},
                {"name": "Michael Roberts", "role": "Board Chair"},
                {"name": "Jennifer Park", "role": "VC Representative"},
                {"name": "David Kim", "role": "Independent Director"},
                {"name": "Lisa Anderson", "role": "Finance Director"}
            ],
            "timepoint_count": 5,
            "temporal_mode": "pearl",
            "focus": ["dialog", "decision_making", "relationships"],
            "outputs": ["dialog", "decisions", "relationships"],
            "resolution_mode": "progressive"
        }
    },
    {
        "input": "The Constitutional Convention of 1787. 10 key delegates, focus on debate and compromise. I want to see the evolution of ideas over 15 sessions.",
        "output": {
            "scenario": "Constitutional Convention of 1787",
            "entities": [
                {"name": "George Washington", "role": "Convention President"},
                {"name": "Benjamin Franklin", "role": "Pennsylvania Delegate"},
                {"name": "James Madison", "role": "Virginia Delegate"},
                {"name": "Alexander Hamilton", "role": "New York Delegate"},
                {"name": "Roger Sherman", "role": "Connecticut Delegate"},
                {"name": "Gouverneur Morris", "role": "Pennsylvania Delegate"},
                {"name": "Edmund Randolph", "role": "Virginia Delegate"},
                {"name": "George Mason", "role": "Virginia Delegate"},
                {"name": "William Paterson", "role": "New Jersey Delegate"},
                {"name": "Charles Pinckney", "role": "South Carolina Delegate"}
            ],
            "timepoint_count": 15,
            "start_time": "1787-05-25T10:00:00",
            "temporal_mode": "pearl",
            "focus": ["dialog", "decision_making", "knowledge_propagation"],
            "outputs": ["dialog", "decisions", "knowledge_flow"],
            "resolution_mode": "progressive"
        }
    },
    {
        "input": "Apollo 13 crisis. 3 astronauts and flight director Gene Kranz. Model stress and decision-making under pressure. 10 timepoints from explosion to splashdown.",
        "output": {
            "scenario": "Apollo 13 Crisis",
            "entities": [
                {"name": "Jim Lovell", "role": "Commander"},
                {"name": "Jack Swigert", "role": "Command Module Pilot"},
                {"name": "Fred Haise", "role": "Lunar Module Pilot"},
                {"name": "Gene Kranz", "role": "Flight Director"}
            ],
            "timepoint_count": 10,
            "start_time": "1970-04-13T19:00:00",
            "temporal_mode": "pearl",
            "focus": ["decision_making", "stress_responses", "dialog"],
            "outputs": ["dialog", "decisions"],
            "resolution_mode": "progressive"
        }
    },
    {
        "input": "Paul Revere's midnight ride. Include his horse. Focus on movement and alerts spreading.",
        "output": {
            "scenario": "Paul Revere's Midnight Ride",
            "entities": [
                {"name": "Paul Revere", "role": "Messenger"},
                {"name": "Brown Beauty", "role": "Horse"},
                {"name": "Samuel Adams", "role": "Patriot Leader"},
                {"name": "John Hancock", "role": "Patriot Leader"}
            ],
            "timepoint_count": 8,
            "start_time": "1775-04-18T22:00:00",
            "temporal_mode": "pearl",
            "focus": ["knowledge_propagation"],
            "outputs": ["knowledge_flow"],
            "animism_level": 2,
            "resolution_mode": "progressive"
        }
    },
    {
        "input": "Generate 50 variations of a job interview scenario with different personality types.",
        "output": {
            "scenario": "Job Interview Variations",
            "entities": [
                {"name": "Alex Morgan", "role": "Interviewer"},
                {"name": "Jordan Smith", "role": "Candidate"}
            ],
            "timepoint_count": 3,
            "temporal_mode": "pearl",
            "focus": ["dialog", "relationships"],
            "outputs": ["dialog"],
            "generation_mode": "horizontal",
            "variation_count": 50,
            "variation_strategy": "personality",
            "resolution_mode": "tensor_only"
        }
    }
]

# Format few-shot examples as prompt text
def format_few_shot_examples() -> str:
    """Format few-shot examples as prompt text"""
    examples_text = ""
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_text += f"\n\nExample {i}:\n"
        examples_text += f"Input: {example['input']}\n\n"
        examples_text += f"Output:\n{format_json_for_prompt(example['output'])}"
    return examples_text


def format_json_for_prompt(obj: Dict[str, Any]) -> str:
    """Format JSON object for inclusion in prompt"""
    import json
    return json.dumps(obj, indent=2)


def build_config_generation_prompt(user_description: str) -> str:
    """
    Build complete prompt for config generation.

    Args:
        user_description: User's natural language description

    Returns:
        Complete prompt for LLM
    """
    prompt = SYSTEM_PROMPT
    prompt += format_few_shot_examples()
    prompt += f"\n\nNow convert this description:\n\nInput: {user_description}\n\nOutput:"
    return prompt


# Error recovery prompts
ERROR_RECOVERY_PROMPTS = {
    "invalid_json": """The previous response was not valid JSON. Please return ONLY a valid JSON object with no markdown formatting, no explanations, and no additional text.

Try again with this description: {description}

Remember: Return ONLY the JSON object.""",

    "missing_required_fields": """The previous response was missing required fields: {missing_fields}

All configurations must include:
- scenario (string)
- entities (list of objects with name and role)
- timepoint_count (integer 1-100)
- temporal_mode (one of: pearl, directorial, branching, cyclical, portal)
- focus (list of strings)
- outputs (list of strings)

Try again with this description: {description}""",

    "invalid_temporal_mode": """The temporal_mode "{mode}" is invalid. Must be one of:
- pearl (standard causal, for historical realism)
- directorial (narrative-driven, for dramatic coherence)
- branching (many-worlds counterfactuals)
- cyclical (time loops, prophecy)
- portal (backward inference from fixed endpoint to origin)

Try again with this description: {description}""",

    "too_many_entities": """The configuration has {count} entities, but the maximum is 100.

Please reduce the entity count to a reasonable number (typically 3-20 for detailed simulations, or fewer with higher entity counts for broader scenarios).

Try again with this description: {description}""",

    "too_many_timepoints": """The configuration has {count} timepoints, but the maximum is 100.

Please reduce to a reasonable number (typically 3-20 timepoints).

Try again with this description: {description}"""
}


def build_error_recovery_prompt(error_type: str, **kwargs) -> str:
    """
    Build error recovery prompt.

    Args:
        error_type: Type of error (key in ERROR_RECOVERY_PROMPTS)
        **kwargs: Variables to format into prompt

    Returns:
        Error recovery prompt
    """
    if error_type not in ERROR_RECOVERY_PROMPTS:
        raise ValueError(f"Unknown error type: {error_type}")

    return ERROR_RECOVERY_PROMPTS[error_type].format(**kwargs)


# Clarification prompts
CLARIFICATION_PROMPTS = {
    "missing_entity_count": "How many entities (people, organizations, etc.) do you want in this simulation? (Typical: 3-10)",
    "missing_timepoint_count": "How many timepoints (moments in time) do you want to simulate? (Typical: 3-15)",
    "missing_focus": "What aspects should the simulation focus on? (Choose one or more: dialog, decision_making, relationships, stress_responses, knowledge_propagation)",
    "missing_time_period": "What time period is this scenario set in? (e.g., '1787', 'modern day', '1970s')",
    "ambiguous_scenario": "Can you provide more details about the scenario? (e.g., setting, goals, key conflicts)",
    "missing_outputs": "What outputs do you want from the simulation? (Choose one or more: dialog, decisions, relationships, knowledge_flow)"
}


def get_clarification_question(missing_field: str) -> str:
    """
    Get clarification question for missing field.

    Args:
        missing_field: Field that needs clarification

    Returns:
        Clarification question
    """
    return CLARIFICATION_PROMPTS.get(missing_field, f"Please provide more information about: {missing_field}")
