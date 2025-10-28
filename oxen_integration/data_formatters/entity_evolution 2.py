"""
Entity Evolution Formatter - Trains on entity state transitions across timepoints.

Generates prompt/completion pairs showing how entities evolve through temporal simulations.
"""

from typing import List, Dict, Any, Optional
import json
from .context_manager import TrainingContextManager


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
        """
        Create proper prompt/completion pairs for fine-tuning.

        FIX: Prompt should NOT contain the answer. It should ask the model to PREDICT
        how an entity changes when experiencing an event. The completion shows the
        ACTUAL outcome from the simulation, teaching causal reasoning.
        """

        # Get exposure events for this entity
        exposure_events = simulation_result.get("exposure_events", {})
        entity_exposures = exposure_events.get(entity.entity_id, [])

        # Reconstruct T0 knowledge state
        t0_exposures = [
            exp for exp in entity_exposures
            if hasattr(exp, 'timepoint_id') and (
                exp.timepoint_id == t0.timepoint_id or
                exp.event_type == "initial"
            )
        ]
        t0_knowledge = [exp.information for exp in t0_exposures if hasattr(exp, 'information')]

        # Reconstruct T1 knowledge state
        t1_exposures = [
            exp for exp in entity_exposures
            if hasattr(exp, 'timepoint_id') and (
                exp.timepoint_id in [t0.timepoint_id, t1.timepoint_id] or
                exp.event_type == "initial"
            )
        ]
        t1_knowledge = [exp.information for exp in t1_exposures if hasattr(exp, 'information')]

        # Calculate ACTUAL changes (ground truth from simulation)
        new_knowledge = [k for k in t1_knowledge if k not in t0_knowledge]
        energy_cost = 5.0 + (len(t1.entities_present) * 2.0)
        importance = getattr(t1, 'importance', 0.5)

        # Get entity personality if available
        personality_traits = getattr(entity, 'personality_traits', [0.0, 0.0, 0.0, 0.0, 0.0])
        entity_metadata = getattr(entity, 'entity_metadata', {})

        # BUILD PROMPT: Context + Event + Question (NO ANSWER)
        prompt = f"""An entity experiences an event in a historical simulation. Predict how their state changes.

=== ENTITY BEFORE EVENT (T0) ===
Identity: {entity.entity_id}
Type: {entity.entity_type}
Current Knowledge ({len(t0_knowledge)} items):
{json.dumps(t0_knowledge[:5], indent=2) if t0_knowledge else "[]"}  {f"... and {len(t0_knowledge) - 5} more" if len(t0_knowledge) > 5 else ""}

Current Energy: 100.0 (full cognitive capacity)
Current Emotional State:
  - Valence: 0.0 (neutral)
  - Arousal: 0.0 (calm)

Personality: {personality_traits}

=== EVENT OCCURRING NOW ===
{t1.event_description}

Scene Context:
- Location: {t0.timepoint_id}
- Others Present: {t1.entities_present}
- Event Importance: {importance:.2f}

=== PREDICTION TASK ===
Based on this entity's current state, personality, and the event occurring, predict:

1. NEW KNOWLEDGE: What specific information does this entity learn from experiencing this event?

2. ENERGY CHANGE: How much cognitive/physical energy is spent? (Consider: event complexity, social dynamics, emotional intensity)

3. EMOTIONAL IMPACT: How do their emotions shift?
   - Valence change (positive/negative feeling)
   - Arousal change (calm/excited state)

4. CAUSAL REASONING: Explain WHY these changes occur based on the entity's personality, role, and the event's nature.

Respond with a JSON object containing your predictions."""

        # BUILD COMPLETION: Actual outcome with reasoning (what model should learn to generate)
        emotional_delta = {
            "valence": (importance - 0.5) * 0.2,
            "arousal": importance * 0.3
        }

        # Generate reasoning based on actual simulation data
        reasoning_parts = []

        if new_knowledge:
            reasoning_parts.append(
                f"Entity {entity.entity_id} learned {len(new_knowledge)} new pieces of information "
                f"by directly experiencing the event: {t1.event_description[:100]}..."
            )

        reasoning_parts.append(
            f"Cognitive energy decreased by {energy_cost:.1f} due to: "
            f"base processing cost (5.0) + social interaction with {len(t1.entities_present)} entities "
            f"({len(t1.entities_present) * 2.0:.1f})."
        )

        reasoning_parts.append(
            f"Emotional impact: valence shifted {emotional_delta['valence']:+.2f} "
            f"(event importance {importance:.2f}), arousal increased {emotional_delta['arousal']:+.2f} "
            f"due to event engagement."
        )

        causal_reasoning = " ".join(reasoning_parts)

        completion = json.dumps({
            "new_knowledge_gained": new_knowledge,
            "knowledge_count": len(new_knowledge),
            "energy_change": -energy_cost,
            "remaining_energy": 100.0 - energy_cost,
            "emotional_change": {
                "valence_delta": emotional_delta["valence"],
                "arousal_delta": emotional_delta["arousal"],
                "final_valence": 0.0 + emotional_delta["valence"],
                "final_arousal": 0.0 + emotional_delta["arousal"]
            },
            "causal_reasoning": causal_reasoning,
            "mechanism_explanation": {
                "knowledge_acquisition": "Direct participation in event led to information exposure",
                "energy_dynamics": "Cognitive processing and social interaction consume resources",
                "emotional_dynamics": "Event importance and participation drive affective response"
            },
            "metadata": {
                "entity_id": entity.entity_id,
                "entity_type": entity.entity_type,
                "timepoint_transition": f"{t0.timepoint_id} -> {t1.timepoint_id}",
                "co_present_entities": t1.entities_present,
                "event_causal_parent": t1.causal_parent
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
