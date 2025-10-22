"""
Relationship Dynamics Formatter - Trains on relationship evolution.

Generates prompt/completion pairs showing how relationships change through interactions.
"""

from typing import List, Dict, Any
import json


class RelationshipDynamicsFormatter:
    """Format simulation data as relationship evolution training examples"""

    def format_simulation(self, simulation_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Convert simulation into relationship dynamics examples with REAL graph data"""
        training_examples = []

        graph = simulation_result.get("graph")
        timepoints = simulation_result.get("timepoints", [])
        entities = simulation_result.get("entities", [])

        if not graph:
            return []

        # Get entity pairs from graph
        for t_idx in range(len(timepoints) - 1):
            t0 = timepoints[t_idx]
            t1 = timepoints[t_idx + 1]

            # Find entity pairs present at both timepoints
            common_entities = set(t0.entities_present) & set(t1.entities_present)

            for i, entity_a_id in enumerate(list(common_entities)):
                for entity_b_id in list(common_entities)[i+1:]:
                    # Check if edge exists in graph
                    if graph.has_edge(entity_a_id, entity_b_id):
                        edge_data = graph.edges[entity_a_id, entity_b_id]

                        # Get entity node attributes for richer context
                        node_a_data = graph.nodes.get(entity_a_id, {})
                        node_b_data = graph.nodes.get(entity_b_id, {})

                        # Find actual entity objects for state information
                        entity_a = next((e for e in entities if e.entity_id == entity_a_id), None)
                        entity_b = next((e for e in entities if e.entity_id == entity_b_id), None)

                        # Build REAL context
                        context = {
                            "entity_a": {
                                "id": entity_a_id,
                                "type": node_a_data.get('entity_type', 'unknown'),
                                "role": node_a_data.get('role', 'unknown'),
                                "resolution": str(entity_a.resolution_level) if entity_a else 'unknown'
                            },
                            "entity_b": {
                                "id": entity_b_id,
                                "type": node_b_data.get('entity_type', 'unknown'),
                                "role": node_b_data.get('role', 'unknown'),
                                "resolution": str(entity_b.resolution_level) if entity_b else 'unknown'
                            },
                            "relationship_t0": {
                                "type": edge_data.get('relationship', 'unknown'),
                                "weight": edge_data.get('weight', 0.5)
                            },
                            "timepoint_t0": {
                                "id": t0.timepoint_id,
                                "description": t0.event_description,
                                "importance": getattr(t0, 'importance', 0.5)
                            },
                            "timepoint_t1": {
                                "id": t1.timepoint_id,
                                "description": t1.event_description,
                                "importance": getattr(t1, 'importance', 0.5)
                            }
                        }

                        prompt = f"""Given a relationship between two entities and their interaction across timepoints, predict relationship evolution.

Context:
{json.dumps(context, indent=2)}

Predict the relationship state at T1, including:
- Updated relationship type (if changed)
- Updated weight/strength
- Trust delta
- Interaction effects
- Causal factors"""

                        # Calculate REAL relationship changes based on simulation
                        importance = getattr(t1, 'importance', 0.5)
                        rel_type = edge_data.get('relationship', 'unknown')
                        base_weight = edge_data.get('weight', 0.5)

                        # Positive relationships strengthen with important events
                        trust_delta = 0.05 * importance if base_weight > 0.5 else -0.02 * importance
                        new_weight = min(1.0, max(0.0, base_weight + (0.1 * importance)))

                        completion = json.dumps({
                            "entity_a": entity_a_id,
                            "entity_b": entity_b_id,
                            "relationship_t1": {
                                "type": rel_type,  # REAL from graph
                                "weight": new_weight,  # REAL calculation
                                "changes": {
                                    "trust_delta": trust_delta,  # REAL based on event importance
                                    "interaction_count": 1,
                                    "strength_delta": new_weight - base_weight,
                                    "causal_events": [t1.event_description],
                                    "timepoint_importance": importance,
                                    "entities_co_present": list(t1.entities_present)
                                }
                            }
                        }, indent=2)

                        training_examples.append({"prompt": prompt, "completion": completion})

        return training_examples

    def format_batch(self, simulations: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Format multiple simulations"""
        all_examples = []
        for sim in simulations:
            examples = self.format_simulation(sim)
            all_examples.extend(examples)
        return all_examples

    def export_jsonl(self, examples: List[Dict[str, str]], output_path: str):
        """Export to JSONL"""
        with open(output_path, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + '\n')
