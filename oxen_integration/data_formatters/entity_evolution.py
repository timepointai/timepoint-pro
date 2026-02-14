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

    def __init__(self, store=None, llm=None):
        """
        Initialize formatter with optional context manager support.

        Args:
            store: GraphStore for accessing temporal knowledge graph
            llm: LLMClient for LLM-guided context relevance scoring
        """
        self.store = store
        self.llm = llm
        self.context_manager = None

        # Initialize context manager if both dependencies available
        if store and llm:
            self.context_manager = TrainingContextManager(store, llm)

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

        ENHANCEMENT: Gather rich context from temporal knowledge graph (M3, M6, M7, M10, M11, M13, M14)
        to provide comprehensive training signals without revealing the answer.
        """

        # Get exposure events for this entity
        exposure_events = simulation_result.get("exposure_events", {})
        entity_exposures = exposure_events.get(entity.entity_id, [])

        # Gather rich context if context manager is available
        context_section = ""
        if self.context_manager:
            try:
                training_context = self.context_manager.gather_context(
                    entity, t0, t1, simulation_result
                )
                context_section = training_context.to_prompt_string()
            except Exception as e:
                # If context gathering fails, continue without it
                print(f"Warning: Context gathering failed for {entity.entity_id}: {e}")
                context_section = ""

        # Reconstruct T0 knowledge state: everything the entity knew up to and including t0
        t0_exposures = [
            exp for exp in entity_exposures
            if hasattr(exp, 'information') and (
                (hasattr(exp, 'event_type') and exp.event_type == "initial") or
                (hasattr(exp, 'timepoint_id') and exp.timepoint_id == t0.timepoint_id)
            )
        ]
        t0_knowledge = [exp.information for exp in t0_exposures]

        # Reconstruct T1 knowledge state: T0 knowledge + anything learned at T1
        t1_exposures = [
            exp for exp in entity_exposures
            if hasattr(exp, 'information') and (
                (hasattr(exp, 'event_type') and exp.event_type == "initial") or
                (hasattr(exp, 'timepoint_id') and exp.timepoint_id in (t0.timepoint_id, t1.timepoint_id))
            )
        ]
        t1_knowledge = [exp.information for exp in t1_exposures]

        # Calculate ACTUAL changes (ground truth from simulation)
        new_knowledge = [k for k in t1_knowledge if k not in t0_knowledge]

        # Entity-specific energy cost based on actual cognitive state and activity
        entity_metadata = getattr(entity, 'entity_metadata', {})
        base_energy = entity_metadata.get("energy_budget", 100.0)
        cognitive_load = len(new_knowledge) * 5.0  # knowledge acquisition cost
        social_cost = len(t1.entities_present) * 2.0  # social interaction overhead
        energy_cost = 5.0 + cognitive_load + social_cost

        # Derive importance from event characteristics, not a fixed constant
        has_new_knowledge = len(new_knowledge) > 0
        entity_count = len(t1.entities_present)
        event_desc_len = len(getattr(t1, 'event_description', '') or '')
        importance = min(1.0, (
            (0.3 if has_new_knowledge else 0.0) +
            min(0.3, entity_count * 0.06) +
            min(0.4, event_desc_len / 500.0)
        ))

        # Get entity personality and state if available
        personality_traits = getattr(entity, 'personality_traits', [0.0, 0.0, 0.0, 0.0, 0.0])

        # BUILD PROMPT: Rich Context + Entity State + Event + Question (NO ANSWER)
        prompt_parts = [
            "An entity experiences an event in a historical simulation. Predict how their state changes.",
            ""
        ]

        # Add rich context if available (M3, M6, M7, M10, M11, M13, M14)
        if context_section:
            prompt_parts.append(context_section)
            prompt_parts.append("")

        # Add entity state at T0
        prompt_parts.append("=== ENTITY BEFORE EVENT (T0) ===")
        prompt_parts.append(f"Identity: {entity.entity_id}")
        prompt_parts.append(f"Type: {entity.entity_type}")
        prompt_parts.append(f"Current Knowledge ({len(t0_knowledge)} items):")
        prompt_parts.append(f"{json.dumps(t0_knowledge[:5], indent=2) if t0_knowledge else '[]'}  {f'... and {len(t0_knowledge) - 5} more' if len(t0_knowledge) > 5 else ''}")
        # Use actual entity cognitive state if available
        current_energy = entity_metadata.get("energy_budget", 100.0)
        current_valence = entity_metadata.get("emotional_valence", 0.0)
        current_arousal = entity_metadata.get("emotional_arousal", 0.0)
        prompt_parts.append("")
        prompt_parts.append(f"Current Energy: {current_energy:.1f}")
        prompt_parts.append("Current Emotional State:")
        prompt_parts.append(f"  - Valence: {current_valence:.2f}")
        prompt_parts.append(f"  - Arousal: {current_arousal:.2f}")
        prompt_parts.append("")
        prompt_parts.append(f"Personality: {personality_traits}")
        prompt_parts.append("")

        # Add event context
        prompt_parts.append("=== EVENT OCCURRING NOW ===")
        prompt_parts.append(f"{t1.event_description}")
        prompt_parts.append("")
        prompt_parts.append("Scene Context:")
        prompt_parts.append(f"- Location: {t0.timepoint_id}")
        prompt_parts.append(f"- Others Present: {t1.entities_present}")
        prompt_parts.append(f"- Event Importance: {importance:.2f}")
        prompt_parts.append("")

        # Add prediction task
        prompt_parts.append("=== PREDICTION TASK ===")
        prompt_parts.append("Based on this entity's current state, personality, and the event occurring, predict:")
        prompt_parts.append("")
        prompt_parts.append("1. NEW KNOWLEDGE: What specific information does this entity learn from experiencing this event?")
        prompt_parts.append("")
        prompt_parts.append("2. ENERGY CHANGE: How much cognitive/physical energy is spent? (Consider: event complexity, social dynamics, emotional intensity)")
        prompt_parts.append("")
        prompt_parts.append("3. EMOTIONAL IMPACT: How do their emotions shift?")
        prompt_parts.append("   - Valence change (positive/negative feeling)")
        prompt_parts.append("   - Arousal change (calm/excited state)")
        prompt_parts.append("")
        prompt_parts.append("4. CAUSAL REASONING: Explain WHY these changes occur based on the entity's personality, role, and the event's nature.")
        prompt_parts.append("")
        prompt_parts.append("Respond with a JSON object containing your predictions.")

        # Join all parts
        prompt = "\n".join(prompt_parts)

        # BUILD COMPLETION: Actual outcome with reasoning (what model should learn to generate)
        # Emotional deltas vary by entity personality and event importance
        trait_valence_bias = sum(personality_traits[:3]) / max(len(personality_traits[:3]), 1) * 0.1
        emotional_delta = {
            "valence": (importance - 0.5) * 0.3 + trait_valence_bias,
            "arousal": importance * 0.4 * (1.0 + (len(new_knowledge) * 0.1))
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
            "energy_change": round(-energy_cost, 1),
            "remaining_energy": round(max(0.0, current_energy - energy_cost), 1),
            "emotional_change": {
                "valence_delta": round(emotional_delta["valence"], 3),
                "arousal_delta": round(emotional_delta["arousal"], 3),
                "final_valence": round(current_valence + emotional_delta["valence"], 3),
                "final_arousal": round(min(1.0, max(0.0, current_arousal + emotional_delta["arousal"])), 3)
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
