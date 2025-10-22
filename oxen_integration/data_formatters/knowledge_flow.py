"""
Knowledge Flow Formatter - Trains on query-response about entity knowledge.

Generates Q&A pairs about knowledge propagation through temporal simulations.
"""

from typing import List, Dict, Any
import json


class KnowledgeFlowFormatter:
    """Format simulation data as knowledge flow query/response examples"""

    def format_simulation(self, simulation_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Convert simulation into knowledge flow Q&A examples"""
        training_examples = []

        entities = simulation_result.get("entities", [])
        timepoints = simulation_result.get("timepoints", [])
        exposure_events = simulation_result.get("exposure_events", {})

        # Generate various query types
        for timepoint in timepoints:
            # Query: Who knew X at time T?
            example = {
                "prompt": f"Query: Which entities had knowledge about '{timepoint.event_description}' at timepoint {timepoint.timepoint_id}?",
                "completion": json.dumps({
                    "entities_with_knowledge": timepoint.entities_present,
                    "timepoint": timepoint.timepoint_id,
                    "knowledge_sources": "exposure_events",
                }, indent=2)
            }
            training_examples.append(example)

            # Query: How did entity X learn Y?
            for entity_id in timepoint.entities_present[:2]:  # Limit to avoid explosion
                example = {
                    "prompt": f"Query: How did entity '{entity_id}' acquire knowledge at timepoint {timepoint.timepoint_id}?",
                    "completion": json.dumps({
                        "entity_id": entity_id,
                        "acquisition_method": "witnessed",
                        "timepoint": timepoint.timepoint_id,
                        "causal_chain": [timepoint.causal_parent, timepoint.timepoint_id] if timepoint.causal_parent else [timepoint.timepoint_id],
                    }, indent=2)
                }
                training_examples.append(example)

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
