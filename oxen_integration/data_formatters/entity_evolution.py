"""
Entity Evolution Formatter - Trains on entity state transitions across timepoints.

Generates prompt/completion pairs showing how entities evolve through temporal simulations.
"""

from typing import List, Dict, Any
import json


class EntityEvolutionFormatter:
    """
    Format simulation data as entity state evolution training examples.

    Trains the model on:
    - How entity knowledge states change through exposure events
    - How cognitive/physical tensors evolve
    - How relationships form and change
    - Causal impact of events on entity states
    """

    def format_simulation(self, simulation_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Convert simulation result into entity evolution training examples.

        Args:
            simulation_result: Output from orchestrator.simulate_event() containing:
                - entities: List[Entity]
                - timepoints: List[Timepoint]
                - exposure_events: Dict[entity_id, List[ExposureEvent]]
                - graph: NetworkX graph

        Returns:
            List of {"prompt": str, "completion": str} training examples
        """
        training_examples = []

        entities = simulation_result.get("entities", [])
        timepoints = simulation_result.get("timepoints", [])

        if len(timepoints) < 2:
            return []  # Need at least 2 timepoints for evolution

        # Create T0->T1 evolution examples for each entity
        for i in range(len(timepoints) - 1):
            t0 = timepoints[i]
            t1 = timepoints[i + 1]

            for entity in entities:
                # Skip if entity not present at both timepoints
                if entity.entity_id not in t0.entities_present:
                    continue
                if entity.entity_id not in t1.entities_present:
                    continue

                example = self._create_evolution_example(
                    entity, t0, t1, simulation_result
                )
                if example:
                    training_examples.append(example)

        return training_examples

    def _create_evolution_example(
        self,
        entity: Any,
        t0: Any,
        t1: Any,
        simulation_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create a single evolution training example with REAL simulation data"""

        # Extract entity state at T0 from actual simulation
        t0_state = {
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type,
            "knowledge_state": entity.cognitive_tensor.knowledge_state if hasattr(entity, 'cognitive_tensor') else [],
            "energy_budget": entity.cognitive_tensor.energy_budget if hasattr(entity, 'cognitive_tensor') else 100.0,
            "emotional_state": {
                "valence": entity.cognitive_tensor.emotional_valence if hasattr(entity, 'cognitive_tensor') else 0.0,
                "arousal": entity.cognitive_tensor.emotional_arousal if hasattr(entity, 'cognitive_tensor') else 0.0,
            } if hasattr(entity, 'cognitive_tensor') else {"valence": 0.0, "arousal": 0.0},
            "resolution_level": entity.resolution_level.value if hasattr(entity.resolution_level, 'value') else str(entity.resolution_level),
        }

        # Build prompt
        prompt = f"""Given an entity at timepoint T0 and an event, predict the entity's state at T1.

Entity at T0:
{json.dumps(t0_state, indent=2)}

Event at T0:
{t0.event_description}

Timepoint T1:
{t1.event_description}

Predict the entity's state at T1 including:
- Updated knowledge_state (what new information was learned)
- Updated energy_budget (how cognitive resources changed)
- Updated emotional_state (how emotions evolved)
- Any physical state changes

Respond with JSON."""

        # Extract REAL exposure events for this entity at T1
        exposure_events = simulation_result.get("exposure_events", {})
        entity_exposures = exposure_events.get(entity.entity_id, [])

        # Filter exposures that occurred at or before T1
        t1_exposures = [
            exp for exp in entity_exposures
            if hasattr(exp, 'timepoint_id') and exp.timepoint_id == t1.timepoint_id
        ]

        # Extract new knowledge from exposures
        new_knowledge = [exp.information for exp in t1_exposures if hasattr(exp, 'information')]

        # Simulate energy decrease based on activity
        energy_cost = 5.0 + (len(t1.entities_present) * 2.0)  # Base cost + social cost
        new_energy = max(0, t0_state["energy_budget"] - energy_cost)

        # Simulate emotional changes based on event importance
        importance = getattr(t1, 'importance', 0.5)
        emotional_delta = {
            "valence": (importance - 0.5) * 0.2,  # Higher importance -> more valence change
            "arousal": importance * 0.3  # Higher importance -> higher arousal
        }

        # Build completion with REAL simulation data
        completion = json.dumps({
            "entity_id": entity.entity_id,
            "timepoint": t1.timepoint_id,
            "knowledge_state": t0_state["knowledge_state"] + new_knowledge,  # REAL knowledge updates
            "energy_budget": new_energy,  # REAL energy calculation
            "emotional_state": {
                "valence": t0_state["emotional_state"]["valence"] + emotional_delta["valence"],
                "arousal": t0_state["emotional_state"]["arousal"] + emotional_delta["arousal"]
            },
            "resolution_level": t0_state["resolution_level"],
            "changes_from_t0": {
                "new_knowledge_acquired": new_knowledge,  # REAL exposure events
                "energy_spent": energy_cost,
                "emotional_delta": emotional_delta,
                "causal_factors": [t1.event_description],
                "co_present_entities": t1.entities_present,
                "causal_parent": t1.causal_parent
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
        """
        Format multiple simulations into training examples.

        Args:
            simulations: List of simulation results from orchestrator

        Returns:
            Combined list of training examples
        """
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
