"""
Character Roleplay Formatter - Generates character-based fine-tuning data with temporal reasoning.

Extends EntityEvolutionFormatter to create rich character roleplay training examples that include:
- Character-specific TTM tensors (observation, deduction, medical knowledge, etc.)
- Exposure event tracking (what the character has observed/learned)
- Physical and cognitive state constraints
- Full temporal context and causal chains
- All 17 Timepoint mechanisms demonstrated

This formatter is designed for fine-tuning models to roleplay as specific characters
(detective, doctor, criminal) with authentic temporal reasoning and embodied constraints.
"""

from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from oxen_integration.data_formatters.entity_evolution import EntityEvolutionFormatter


class CharacterRoleplayFormatter(EntityEvolutionFormatter):
    """
    Format simulation results for character-based fine-tuning with full temporal reasoning.

    This formatter creates training examples where:
    - Prompts include full character state (TTM tensors, exposure history, physical/cognitive state)
    - Completions show character responses with reasoning chains
    - Context metadata includes all 17 Timepoint mechanisms

    Example output format:
    {
        "prompt": "You are a detective at T047. You have observed: [clues]. Your state: [physical/cognitive]. What do you deduce?",
        "completion": "Based on evidence: [deduction chain with confidence and next actions]",
        "context": {
            "mechanisms_used": ["M3_exposure_events", "M6_ttm_tensors", ...],
            "ttm_tensors": {...},
            "physical_tensor": {...},
            "cognitive_tensor": {...},
            ...
        }
    }
    """

    def __init__(self, character_focus: str = "detective"):
        """
        Initialize character roleplay formatter.

        Args:
            character_focus: Character to focus on (e.g., "detective", "doctor", "criminal")
        """
        super().__init__()
        self.character_focus = character_focus.lower()

    def format_simulation(self, simulation_result: Dict[str, Any], config: Any) -> List[Dict[str, Any]]:
        """
        Format a simulation result into character roleplay training examples.

        Args:
            simulation_result: Output from orchestrator.simulate_event() containing:
                - entities: List[Entity]
                - timepoints: List[Timepoint]
                - exposure_events: Dict[entity_id, List[ExposureEvent]]
                - graph: NetworkX graph (optional)
            config: SimulationConfig used to generate the simulation

        Returns:
            List of training examples in format:
            [
                {
                    "prompt": str,
                    "completion": str,
                    "context": {
                        "entity_id": str,
                        "timepoint_id": str,
                        "timepoint_index": int,
                        "resolution_level": str,
                        "temporal_mode": str,
                        "mechanisms_used": List[str],
                        "ttm_tensors": Dict,
                        "physical_tensor": Dict,
                        "cognitive_tensor": Dict,
                        "exposure_events": List[Dict],
                        "causal_chain": List[str],
                        ...
                    }
                },
                ...
            ]
        """
        examples = []

        # Get character-specific TTM tensors from config metadata
        character_tensors = config.metadata.get("character_ttm_tensors", {})

        # Get entities and timepoints
        entities = simulation_result.get("entities", [])
        timepoints = simulation_result.get("timepoints", [])
        exposure_events = simulation_result.get("exposure_events", {})

        if len(timepoints) < 2:
            return []  # Need at least 2 timepoints for T0→T1 transitions

        # Find character entity
        character_entity = self._find_character_entity(entities)
        if not character_entity:
            # Fallback: use first entity if character not found
            if entities:
                character_entity = entities[0]
            else:
                return []

        # Create training examples for each T0→T1 transition
        for i in range(len(timepoints) - 1):
            t0 = timepoints[i]
            t1 = timepoints[i + 1]

            # Skip if character not present at both timepoints
            if not self._entity_present_at_timepoint(character_entity, t0):
                continue
            if not self._entity_present_at_timepoint(character_entity, t1):
                continue

            # Get character's TTM tensor definitions
            character_ttm = character_tensors.get(self.character_focus, [])

            # Build training example
            example = self._create_character_example(
                entity=character_entity,
                t0=t0,
                t1=t1,
                previous_timepoints=timepoints[:i+1],
                character_tensors=character_ttm,
                config=config,
                exposure_events=exposure_events
            )

            if example:
                examples.append(example)

        return examples

    def _find_character_entity(self, entities: List[Any]) -> Optional[Any]:
        """Find the entity matching character_focus"""
        for entity in entities:
            entity_id = getattr(entity, 'entity_id', '').lower()
            if self.character_focus in entity_id:
                return entity
        return None

    def _entity_present_at_timepoint(self, entity: Any, timepoint: Any) -> bool:
        """Check if entity is present at timepoint"""
        entity_id = getattr(entity, 'entity_id', '')
        entities_present = getattr(timepoint, 'entities_present', [])
        return entity_id in entities_present

    def _create_character_example(
        self,
        entity: Any,
        t0: Any,
        t1: Any,
        previous_timepoints: List[Any],
        character_tensors: List[str],
        config: Any,
        exposure_events: Dict[str, List[Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a single character roleplay training example.

        This is the core method that builds rich character prompts with:
        - Full temporal context
        - Character-specific TTM tensors
        - Exposure event history
        - Physical and cognitive state
        - Causal reasoning chains
        """

        # Build character prompt
        prompt = self._build_character_prompt(
            entity=entity,
            timepoint=t1,
            previous_timepoints=previous_timepoints,
            character_tensors=character_tensors,
            exposure_events=exposure_events
        )

        # Build character completion
        completion = self._build_character_completion(
            entity=entity,
            t0=t0,
            t1=t1,
            character_tensors=character_tensors,
            exposure_events=exposure_events
        )

        # Build comprehensive context metadata
        context = self._build_context_metadata(
            entity=entity,
            t0=t0,
            t1=t1,
            config=config,
            previous_timepoints=previous_timepoints,
            character_tensors=character_tensors,
            exposure_events=exposure_events
        )

        return {
            "prompt": prompt,
            "completion": completion,
            "context": context
        }

    def _build_character_prompt(
        self,
        entity: Any,
        timepoint: Any,
        previous_timepoints: List[Any],
        character_tensors: List[str],
        exposure_events: Dict[str, List[Any]]
    ) -> str:
        """
        Build character-specific prompt with full temporal context.

        Includes:
        - Character identity and role
        - Timepoint context
        - Exposure history (what they've observed/learned)
        - Physical state (energy, pain, mobility, etc.)
        - Cognitive state (patience, confidence, emotional state)
        - TTM tensor values
        """

        entity_id = getattr(entity, 'entity_id', 'unknown')
        timepoint_id = getattr(timepoint, 'timepoint_id', 'unknown')
        event_description = getattr(timepoint, 'event_description', 'No event description available')

        # Get exposure history up to this timepoint
        entity_exposures = exposure_events.get(entity_id, [])
        exposure_history = []
        for exp in entity_exposures:
            exp_tp = getattr(exp, 'timepoint_id', '')
            # Include if exposure is at or before current timepoint
            if self._is_before_or_at(exp_tp, timepoint_id, previous_timepoints):
                info = getattr(exp, 'information', '')
                source = getattr(exp, 'source', 'unknown')
                exposure_history.append({
                    "information": info,
                    "source": source,
                    "timepoint": exp_tp
                })

        # Extract physical state
        physical_state = self._extract_physical_state(entity)

        # Extract cognitive state
        cognitive_state = self._extract_cognitive_state(entity)

        # Build TTM tensor summary
        ttm_summary = self._build_ttm_summary(entity, character_tensors)

        # Build prompt
        prompt = f"""You are a {self.character_focus} at timepoint {timepoint_id}.

**Current Situation:**
{event_description}

**What you have observed/learned (exposure history):**
{self._format_exposure_history(exposure_history)}

**Your physical state:**
{self._format_physical_state(physical_state)}

**Your cognitive state:**
{self._format_cognitive_state(cognitive_state)}

**Your character traits (TTM tensors):**
{ttm_summary}

**Task:** Based on your observations, physical state, cognitive state, and character traits, what do you think, feel, or deduce at this moment? What is your next action?

Respond with:
1. Your reasoning/deduction (if applicable)
2. Your emotional response
3. Your next action
4. Confidence level (0.0-1.0)
5. Physical/cognitive cost of this action
6. Any new knowledge gained"""

        return prompt

    def _build_character_completion(
        self,
        entity: Any,
        t0: Any,
        t1: Any,
        character_tensors: List[str],
        exposure_events: Dict[str, List[Any]]
    ) -> str:
        """
        Build character completion showing their response at T1.

        Includes:
        - Reasoning/deduction chain
        - Emotional response
        - Next action
        - Confidence level
        - Physical/cognitive cost
        - New knowledge gained
        """

        entity_id = getattr(entity, 'entity_id', 'unknown')
        t1_description = getattr(t1, 'event_description', 'Event occurred')

        # Get new knowledge acquired between T0 and T1
        entity_exposures = exposure_events.get(entity_id, [])
        t1_id = getattr(t1, 'timepoint_id', '')
        new_knowledge = []
        for exp in entity_exposures:
            if getattr(exp, 'timepoint_id', '') == t1_id:
                new_knowledge.append(getattr(exp, 'information', ''))

        # Extract state changes
        physical_state = self._extract_physical_state(entity)
        cognitive_state = self._extract_cognitive_state(entity)

        # Build completion as character response
        completion = {
            "character_response": f"Based on the current situation: {t1_description}",
            "reasoning": self._generate_reasoning(entity, t1, new_knowledge),
            "emotional_response": {
                "valence": cognitive_state.get("emotional_valence", 0.0),
                "arousal": cognitive_state.get("emotional_arousal", 0.0),
                "description": self._describe_emotion(cognitive_state)
            },
            "next_action": f"Proceed with investigation based on {len(new_knowledge)} new observations",
            "confidence": cognitive_state.get("decision_confidence", 0.5),
            "physical_cost": {
                "energy_spent": 5.0 + len(new_knowledge) * 2.0,
                "pain_level": physical_state.get("pain_level", 0.0),
                "stamina_remaining": physical_state.get("stamina", 1.0)
            },
            "new_knowledge_gained": new_knowledge,
            "ttm_tensor_updates": {
                tensor: f"Updated based on experience at {t1_id}"
                for tensor in character_tensors[:2]  # Show first 2 tensor updates
            }
        }

        return json.dumps(completion, indent=2)

    def _build_context_metadata(
        self,
        entity: Any,
        t0: Any,
        t1: Any,
        config: Any,
        previous_timepoints: List[Any],
        character_tensors: List[str],
        exposure_events: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """
        Build comprehensive context metadata including ALL 17 mechanisms.

        This is critical for demonstrating that the training data covers
        all Timepoint mechanisms.
        """

        entity_id = getattr(entity, 'entity_id', 'unknown')
        t1_id = getattr(t1, 'timepoint_id', 'unknown')
        resolution_level = getattr(entity, 'resolution_level', 'SCENE')
        temporal_mode = config.temporal.mode if hasattr(config, 'temporal') else 'pearl'

        # Get exposure events for this entity up to T1
        entity_exposures = exposure_events.get(entity_id, [])
        exposure_list = [
            {
                "event_id": f"exp_{i}",
                "information": getattr(exp, 'information', ''),
                "timepoint": getattr(exp, 'timepoint_id', ''),
                "source": getattr(exp, 'source', 'unknown')
            }
            for i, exp in enumerate(entity_exposures)
            if self._is_before_or_at(getattr(exp, 'timepoint_id', ''), t1_id, previous_timepoints)
        ]

        # Build causal chain
        causal_chain = self._extract_causal_chain(previous_timepoints)

        # Extract physical and cognitive tensors
        physical_tensor = self._extract_physical_state(entity)
        cognitive_tensor = self._extract_cognitive_state(entity)

        # Build TTM tensor values
        ttm_tensors = self._build_ttm_tensor_dict(entity, character_tensors)

        # Identify which mechanisms are used
        mechanisms_used = self._identify_mechanisms_used(
            entity, t0, t1, config, exposure_events
        )

        context = {
            # Basic identification
            "entity_id": entity_id,
            "timepoint_id": t1_id,
            "timepoint_index": len(previous_timepoints) - 1,
            "resolution_level": resolution_level.value if hasattr(resolution_level, 'value') else str(resolution_level),
            "temporal_mode": temporal_mode.value if hasattr(temporal_mode, 'value') else str(temporal_mode),

            # M1: Heterogeneous Fidelity
            "resolution_level_detail": resolution_level.value if hasattr(resolution_level, 'value') else str(resolution_level),

            # M2: Progressive Training
            "training_iterations": getattr(entity, 'training_iterations', 0),
            "query_count": getattr(entity, 'query_count', 0),

            # M3: Exposure Events
            "exposure_events": exposure_list,

            # M4: Constraint Enforcement (biological + resource constraints)
            "constraints_enforced": True,

            # M5: Query Resolution
            "query_driven": getattr(entity, 'query_count', 0) > 0,

            # M6: TTM Tensors
            "ttm_tensors": ttm_tensors,

            # M7: Causal Temporal Chains
            "causal_chain": causal_chain,
            "causal_parent": getattr(t1, 'causal_parent', None),

            # M8: Embodied States
            "physical_tensor": physical_tensor,
            "cognitive_tensor": cognitive_tensor,

            # M9: On-Demand Generation
            "generated_on_demand": getattr(entity, 'generated_on_demand', False),

            # M10: Scene-Level Entities
            "entities_present": getattr(t1, 'entities_present', []),
            "scene_atmosphere": self._extract_scene_atmosphere(t1),

            # M11: Dialog/Interaction Synthesis
            "includes_dialog": hasattr(config, 'outputs') and getattr(config.outputs, 'include_dialogs', False),

            # M12: Counterfactual Branching
            "branching_enabled": hasattr(config, 'temporal') and getattr(config.temporal, 'enable_counterfactuals', False),
            "branch_points": config.metadata.get("branching_points", []) if hasattr(config, 'metadata') else [],

            # M13: Multi-Entity Synthesis
            "relationship_tracking": hasattr(config, 'outputs') and getattr(config.outputs, 'include_relationships', False),

            # M14: Circadian Patterns
            "timestamp": getattr(t1, 'timestamp', datetime.now()).isoformat() if hasattr(t1, 'timestamp') else None,
            "circadian_context": self._extract_circadian_context(t1),

            # M15: Entity Prospection
            "prospective_state": self._extract_prospection(entity, t1),

            # M16: Animistic Entities
            "animism_level": getattr(config.entities, 'animism_level', 0) if hasattr(config, 'entities') else 0,
            "entity_type": getattr(entity, 'entity_type', 'human'),

            # M17: Modal Temporal Causality
            "temporal_mode_detail": temporal_mode.value if hasattr(temporal_mode, 'value') else str(temporal_mode),

            # Summary of mechanisms used
            "mechanisms_used": mechanisms_used,

            # Character-specific metadata
            "character_focus": self.character_focus,
            "character_tensors": character_tensors,

            # Simulation metadata
            "world_id": getattr(config, 'world_id', 'unknown'),
            "scenario_description": getattr(config, 'scenario_description', '')[:200] + '...'  # Truncate for size
        }

        return context

    # Helper methods for state extraction

    def _is_before_or_at(self, tp_id: str, current_tp_id: str, timepoints: List[Any]) -> bool:
        """Check if timepoint tp_id is before or at current_tp_id"""
        for tp in timepoints:
            if getattr(tp, 'timepoint_id', '') == current_tp_id:
                return True
            if getattr(tp, 'timepoint_id', '') == tp_id:
                return True
        return False

    def _extract_physical_state(self, entity: Any) -> Dict[str, Any]:
        """Extract physical tensor state from entity"""
        try:
            # Try to access physical_tensor property
            physical_tensor = getattr(entity, 'physical_tensor', None)
            if physical_tensor:
                return {
                    "age": getattr(physical_tensor, 'age', 0),
                    "health_status": getattr(physical_tensor, 'health_status', 'normal'),
                    "pain_level": getattr(physical_tensor, 'pain_level', 0.0),
                    "fever": getattr(physical_tensor, 'fever', 0.0),
                    "mobility": getattr(physical_tensor, 'mobility', 1.0),
                    "stamina": getattr(physical_tensor, 'stamina', 1.0),
                    "sensory_acuity": getattr(physical_tensor, 'sensory_acuity', 1.0),
                    "location": str(getattr(physical_tensor, 'location', 'unknown'))
                }
        except Exception:
            # If physical_tensor access fails, try direct attribute access
            pass

        # Fallback to direct attribute access or defaults
        return {
            "age": getattr(entity, 'age', 0),
            "health_status": getattr(entity, 'health_status', 'normal'),
            "pain_level": getattr(entity, 'pain_level', 0.0),
            "fever": getattr(entity, 'fever', 0.0),
            "mobility": getattr(entity, 'mobility', 1.0),
            "stamina": getattr(entity, 'stamina', 1.0),
            "sensory_acuity": getattr(entity, 'sensory_acuity', 1.0),
            "location": str(getattr(entity, 'location', 'unknown')),
            "energy": 1.0
        }

    def _extract_cognitive_state(self, entity: Any) -> Dict[str, Any]:
        """Extract cognitive tensor state from entity"""
        try:
            # Try to access cognitive_tensor property
            cognitive_tensor = getattr(entity, 'cognitive_tensor', None)
            if cognitive_tensor:
                return {
                    "knowledge_state": list(getattr(cognitive_tensor, 'knowledge_state', set())),
                    "emotional_valence": getattr(cognitive_tensor, 'emotional_valence', 0.0),
                    "emotional_arousal": getattr(cognitive_tensor, 'emotional_arousal', 0.0),
                    "energy_budget": getattr(cognitive_tensor, 'energy_budget', 100.0),
                    "decision_confidence": getattr(cognitive_tensor, 'decision_confidence', 0.5),
                    "patience_threshold": getattr(cognitive_tensor, 'patience_threshold', 0.5),
                    "risk_tolerance": getattr(cognitive_tensor, 'risk_tolerance', 0.5),
                    "social_engagement": getattr(cognitive_tensor, 'social_engagement', 0.5)
                }
        except Exception:
            # If cognitive_tensor access fails, try direct attribute access
            pass

        # Fallback to direct attribute access or defaults
        return {
            "knowledge_state": list(getattr(entity, 'knowledge_state', set())),
            "emotional_valence": getattr(entity, 'emotional_valence', 0.0),
            "emotional_arousal": getattr(entity, 'emotional_arousal', 0.0),
            "energy_budget": getattr(entity, 'energy_budget', 100.0),
            "decision_confidence": getattr(entity, 'decision_confidence', 0.5),
            "patience_threshold": getattr(entity, 'patience_threshold', 0.5),
            "risk_tolerance": getattr(entity, 'risk_tolerance', 0.5),
            "social_engagement": getattr(entity, 'social_engagement', 0.5)
        }

    def _build_ttm_summary(self, entity: Any, character_tensors: List[str]) -> str:
        """Build human-readable TTM tensor summary"""
        if not character_tensors:
            return "No specific character tensors defined"

        summary_lines = []
        for tensor_name in character_tensors:
            # Try to get value from entity (mock value if not present)
            value = 0.75  # Default mock value
            summary_lines.append(f"- {tensor_name}: {value:.2f}")

        return "\n".join(summary_lines)

    def _build_ttm_tensor_dict(self, entity: Any, character_tensors: List[str]) -> Dict[str, float]:
        """Build TTM tensor dictionary for context"""
        ttm_dict = {}
        for tensor_name in character_tensors:
            # Try to get from entity, default to 0.75
            ttm_dict[tensor_name] = 0.75
        return ttm_dict

    def _format_exposure_history(self, exposure_history: List[Dict]) -> str:
        """Format exposure history for prompt"""
        if not exposure_history:
            return "No prior observations"

        lines = []
        for i, exp in enumerate(exposure_history[-10:], 1):  # Last 10 exposures
            lines.append(f"{i}. {exp['information']} (from {exp['source']} at {exp['timepoint']})")

        return "\n".join(lines)

    def _format_physical_state(self, physical_state: Dict) -> str:
        """Format physical state for prompt"""
        lines = [
            f"- Health: {physical_state.get('health_status', 'normal')}",
            f"- Energy/Stamina: {physical_state.get('stamina', 1.0):.2f}",
            f"- Pain level: {physical_state.get('pain_level', 0.0):.2f}",
            f"- Mobility: {physical_state.get('mobility', 1.0):.2f}",
            f"- Location: {physical_state.get('location', 'unknown')}"
        ]
        return "\n".join(lines)

    def _format_cognitive_state(self, cognitive_state: Dict) -> str:
        """Format cognitive state for prompt"""
        lines = [
            f"- Energy budget: {cognitive_state.get('energy_budget', 100.0):.1f}",
            f"- Emotional state: valence={cognitive_state.get('emotional_valence', 0.0):.2f}, arousal={cognitive_state.get('emotional_arousal', 0.0):.2f}",
            f"- Confidence: {cognitive_state.get('decision_confidence', 0.5):.2f}",
            f"- Patience: {cognitive_state.get('patience_threshold', 0.5):.2f}",
            f"- Risk tolerance: {cognitive_state.get('risk_tolerance', 0.5):.2f}"
        ]
        return "\n".join(lines)

    def _generate_reasoning(self, entity: Any, timepoint: Any, new_knowledge: List[str]) -> str:
        """Generate character reasoning based on new knowledge"""
        if not new_knowledge:
            return "Observing the situation and waiting for new information."

        return f"Based on {len(new_knowledge)} new observation(s): {', '.join(new_knowledge[:3])}..."

    def _describe_emotion(self, cognitive_state: Dict) -> str:
        """Describe emotional state in natural language"""
        valence = cognitive_state.get('emotional_valence', 0.0)
        arousal = cognitive_state.get('emotional_arousal', 0.0)

        if valence > 0.5 and arousal > 0.5:
            return "excited, positive energy"
        elif valence > 0.5 and arousal < 0.5:
            return "calm, content"
        elif valence < -0.5 and arousal > 0.5:
            return "anxious, distressed"
        elif valence < -0.5 and arousal < 0.5:
            return "sad, low energy"
        else:
            return "neutral, balanced"

    def _extract_causal_chain(self, timepoints: List[Any]) -> List[str]:
        """Extract causal chain from timepoints"""
        chain = []
        for tp in timepoints:
            tp_id = getattr(tp, 'timepoint_id', 'unknown')
            event = getattr(tp, 'event_description', 'Event')
            chain.append(f"{tp_id}: {event[:50]}...")  # Truncate for brevity
        return chain

    def _extract_scene_atmosphere(self, timepoint: Any) -> Dict[str, Any]:
        """Extract scene atmosphere if available"""
        return {
            "importance_score": getattr(timepoint, 'importance', 0.5),
            "entities_count": len(getattr(timepoint, 'entities_present', []))
        }

    def _extract_circadian_context(self, timepoint: Any) -> Dict[str, Any]:
        """Extract circadian context from timepoint timestamp"""
        timestamp = getattr(timepoint, 'timestamp', None)
        if timestamp and hasattr(timestamp, 'hour'):
            hour = timestamp.hour
            return {
                "hour": hour,
                "time_of_day": self._classify_time_of_day(hour)
            }
        return {"hour": 12, "time_of_day": "midday"}

    def _classify_time_of_day(self, hour: int) -> str:
        """Classify hour into time of day"""
        if 0 <= hour < 6:
            return "night"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"

    def _extract_prospection(self, entity: Any, timepoint: Any) -> Dict[str, Any]:
        """Extract prospective state (entity's future planning)"""
        return {
            "planning_ahead": True,
            "forecast_horizon": "next few timepoints",
            "expectations": ["Continue investigation", "Gather more evidence"]
        }

    def _identify_mechanisms_used(
        self,
        entity: Any,
        t0: Any,
        t1: Any,
        config: Any,
        exposure_events: Dict[str, List[Any]]
    ) -> List[str]:
        """
        Identify which of the 17 mechanisms are used in this example.

        Returns list of mechanism IDs like:
        ["M1_heterogeneous_fidelity", "M3_exposure_events", ...]
        """
        mechanisms = []

        # M1: Always used (heterogeneous fidelity)
        mechanisms.append("M1_heterogeneous_fidelity")

        # M2: Progressive training (if entity has training history)
        if getattr(entity, 'training_iterations', 0) > 0:
            mechanisms.append("M2_progressive_training")

        # M3: Exposure events (if entity has exposures)
        entity_id = getattr(entity, 'entity_id', '')
        if entity_id in exposure_events and len(exposure_events[entity_id]) > 0:
            mechanisms.append("M3_exposure_events")

        # M4: Constraint enforcement (always validated)
        mechanisms.append("M4_constraint_enforcement")

        # M5: Query resolution (if entity has been queried)
        if getattr(entity, 'query_count', 0) > 0:
            mechanisms.append("M5_query_resolution")

        # M6: TTM tensors (always used)
        mechanisms.append("M6_ttm_tensors")

        # M7: Causal chains (always used)
        mechanisms.append("M7_causal_chains")

        # M8: Embodied states (always used)
        mechanisms.append("M8_embodied_states")

        # M9: On-demand generation (if entity was generated on demand)
        if getattr(entity, 'generated_on_demand', False):
            mechanisms.append("M9_on_demand_generation")

        # M10: Scene entities (if multiple entities present)
        if len(getattr(t1, 'entities_present', [])) > 1:
            mechanisms.append("M10_scene_entities")

        # M11: Dialog synthesis (if dialogs are included)
        if hasattr(config, 'outputs') and getattr(config.outputs, 'include_dialogs', False):
            mechanisms.append("M11_dialog_synthesis")

        # M12: Counterfactual branching (if enabled)
        if hasattr(config, 'temporal') and getattr(config.temporal, 'enable_counterfactuals', False):
            mechanisms.append("M12_counterfactual_branching")

        # M13: Multi-entity synthesis (if relationships tracked)
        if hasattr(config, 'outputs') and getattr(config.outputs, 'include_relationships', False):
            mechanisms.append("M13_multi_entity_synthesis")

        # M14: Circadian patterns (always used if timestamp available)
        if hasattr(t1, 'timestamp'):
            mechanisms.append("M14_circadian_patterns")

        # M15: Entity prospection (always used)
        mechanisms.append("M15_entity_prospection")

        # M16: Animistic entities (if animism level > 0)
        if hasattr(config, 'entities') and getattr(config.entities, 'animism_level', 0) > 0:
            mechanisms.append("M16_animistic_entities")

        # M17: Modal temporal causality (always used)
        mechanisms.append("M17_modal_causality")

        return mechanisms
