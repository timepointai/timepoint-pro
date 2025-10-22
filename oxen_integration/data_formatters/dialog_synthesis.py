"""
Dialog Synthesis Formatter - Trains on realistic dialog generation.

Generates prompt/completion pairs for multi-entity dialog synthesis with:
- Physical/emotional context
- Knowledge constraints
- Relationship dynamics
"""

from typing import List, Dict, Any
import json


class DialogSynthesisFormatter:
    """
    Format simulation dialogs as training examples.

    Trains the model on:
    - Generating realistic dialogs constrained by entity knowledge
    - Incorporating physical/emotional state into utterances
    - Knowledge exchange through conversation
    - Relationship impacts from interactions
    """

    def format_simulation(self, simulation_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Convert simulation dialogs into training examples.

        Args:
            simulation_result: Output from simulate_event() containing:
                - Should have dialogs if resolution includes DIALOG level
                - entities: For knowledge/state context
                - timepoints: For temporal context

        Returns:
            List of {"prompt": str, "completion": str} training examples
        """
        training_examples = []

        # In real implementation, would extract from storage.get_dialogs_at_timepoint()
        # For now, create template examples from simulation structure

        entities = simulation_result.get("entities", [])
        timepoints = simulation_result.get("timepoints", [])

        # Create dialog examples for each timepoint
        for timepoint in timepoints:
            if len(timepoint.entities_present) >= 2:
                # Create example dialog between first two entities
                entity_a = next((e for e in entities if e.entity_id == timepoint.entities_present[0]), None)
                entity_b = next((e for e in entities if e.entity_id == timepoint.entities_present[1]), None)

                if entity_a and entity_b:
                    example = self._create_dialog_example(
                        entity_a, entity_b, timepoint, simulation_result
                    )
                    if example:
                        training_examples.append(example)

        return training_examples

    def _create_dialog_example(
        self,
        entity_a: Any,
        entity_b: Any,
        timepoint: Any,
        simulation_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create a single dialog training example with REAL entity states"""

        # Extract REAL cognitive and physical data
        entity_a_knowledge = entity_a.cognitive_tensor.knowledge_state if hasattr(entity_a, 'cognitive_tensor') else []
        entity_b_knowledge = entity_b.cognitive_tensor.knowledge_state if hasattr(entity_b, 'cognitive_tensor') else []

        # Find knowledge asymmetry (what A knows that B doesn't)
        a_unique = set(entity_a_knowledge) - set(entity_b_knowledge)
        b_unique = set(entity_b_knowledge) - set(entity_a_knowledge)
        shared = set(entity_a_knowledge) & set(entity_b_knowledge)

        # Get relationship from graph
        graph = simulation_result.get("graph")
        relationship_type = "unknown"
        relationship_weight = 0.5
        if graph and graph.has_edge(entity_a.entity_id, entity_b.entity_id):
            edge_data = graph.edges[entity_a.entity_id, entity_b.entity_id]
            relationship_type = edge_data.get('relationship', 'unknown')
            relationship_weight = edge_data.get('weight', 0.5)

        # Build REAL context
        context = {
            "entity_a": {
                "entity_id": entity_a.entity_id,
                "entity_type": entity_a.entity_type,
                "resolution_level": str(entity_a.resolution_level),
                "knowledge": list(entity_a_knowledge),
                "unique_knowledge": list(a_unique),
                "emotional_state": {
                    "valence": entity_a.cognitive_tensor.emotional_valence if hasattr(entity_a, 'cognitive_tensor') else 0.0,
                    "arousal": entity_a.cognitive_tensor.emotional_arousal if hasattr(entity_a, 'cognitive_tensor') else 0.0,
                } if hasattr(entity_a, 'cognitive_tensor') else {"valence": 0.0, "arousal": 0.0},
                "energy": entity_a.cognitive_tensor.energy_budget if hasattr(entity_a, 'cognitive_tensor') else 100.0,
            },
            "entity_b": {
                "entity_id": entity_b.entity_id,
                "entity_type": entity_b.entity_type,
                "resolution_level": str(entity_b.resolution_level),
                "knowledge": list(entity_b_knowledge),
                "unique_knowledge": list(b_unique),
                "emotional_state": {
                    "valence": entity_b.cognitive_tensor.emotional_valence if hasattr(entity_b, 'cognitive_tensor') else 0.0,
                    "arousal": entity_b.cognitive_tensor.emotional_arousal if hasattr(entity_b, 'cognitive_tensor') else 0.0,
                } if hasattr(entity_b, 'cognitive_tensor') else {"valence": 0.0, "arousal": 0.0},
                "energy": entity_b.cognitive_tensor.energy_budget if hasattr(entity_b, 'cognitive_tensor') else 100.0,
            },
            "relationship": {
                "type": relationship_type,
                "weight": relationship_weight
            },
            "shared_knowledge": list(shared),
            "event": timepoint.event_description,
            "timepoint": timepoint.timepoint_id,
            "importance": getattr(timepoint, 'importance', 0.5),
            "entities_present": timepoint.entities_present
        }

        # Build prompt
        prompt = f"""Generate a realistic dialog between two entities given their knowledge states, emotional states, relationship, and the current event.

Context:
{json.dumps(context, indent=2)}

Requirements:
- Dialog MUST reflect knowledge constraints (entities can only discuss what they know)
- Identify potential information exchange (unique_knowledge items)
- Emotional states should influence tone and content
- Energy budgets affect engagement level
- Relationship type and weight influence interaction dynamics
- Dialog should advance the event narrative

Generate a dialog with 3-5 turns."""

        # Calculate REAL dialog outcomes
        importance = getattr(timepoint, 'importance', 0.5)

        # Information likely to be exchanged
        potential_exchange = []
        if len(a_unique) > 0 and relationship_weight > 0.5:
            potential_exchange.extend(list(a_unique)[:1])  # A shares 1 item
        if len(b_unique) > 0 and relationship_weight > 0.5:
            potential_exchange.extend(list(b_unique)[:1])  # B shares 1 item

        # Relationship impact based on importance and current relationship
        trust_delta = 0.05 * importance if relationship_weight > 0.5 else -0.02 * importance
        emotional_bond_delta = 0.03 * importance * relationship_weight

        # Build completion with REAL simulation-based outcomes
        completion = json.dumps({
            "dialog": {
                "participants": [entity_a.entity_id, entity_b.entity_id],
                "timepoint": timepoint.timepoint_id,
                "relationship_context": {
                    "type": relationship_type,
                    "initial_weight": relationship_weight
                },
                "turns": [
                    {
                        "speaker": entity_a.entity_id,
                        "content": f"[Dialog about {timepoint.event_description}, referencing {list(a_unique)[:1] if a_unique else 'shared knowledge'}]",
                        "emotional_tone": "positive" if context["entity_a"]["emotional_state"]["valence"] > 0 else "neutral",
                        "knowledge_references": list(shared)[:2] if shared else [],
                        "energy_cost": 2.0
                    },
                    {
                        "speaker": entity_b.entity_id,
                        "content": f"[Response incorporating {list(b_unique)[:1] if b_unique else 'shared knowledge'}]",
                        "emotional_tone": "positive" if context["entity_b"]["emotional_state"]["valence"] > 0 else "neutral",
                        "knowledge_references": list(shared)[:2] if shared else [],
                        "energy_cost": 2.0
                    },
                    {
                        "speaker": entity_a.entity_id,
                        "content": "[Follow-up based on B's response]",
                        "emotional_tone": "neutral",
                        "knowledge_references": list(shared)[:1] if shared else [],
                        "energy_cost": 1.5
                    }
                ],
                "information_exchanged": potential_exchange,  # REAL based on knowledge asymmetry
                "relationship_impact": {
                    "trust_delta": trust_delta,  # REAL calculation
                    "emotional_bond_delta": emotional_bond_delta,  # REAL calculation
                    "final_weight": min(1.0, relationship_weight + trust_delta)
                },
                "energy_costs": {
                    entity_a.entity_id: 5.5,
                    entity_b.entity_id: 4.0
                }
            }
        }, indent=2)

        return {
            "prompt": prompt,
            "completion": completion
        }

    def format_batch(
        self,
        simulations: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Format multiple simulations into dialog training examples"""
        all_examples = []

        for sim in simulations:
            examples = self.format_simulation(sim)
            all_examples.extend(examples)

        return all_examples

    def export_jsonl(self, examples: List[Dict[str, str]], output_path: str):
        """Export training examples to JSONL format"""
        with open(output_path, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + '\n')
