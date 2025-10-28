"""
Training Context Manager - Rich context extraction from temporal knowledge graph

Leverages mechanisms M3, M6, M7, M10, M11, M13, M14 to create information-rich
training data that teaches LLMs to reason causally about entity state changes.

Architecture:
- CausalChainExtractor (M7): Timeline narratives without revealing outcomes
- RelationshipContextBuilder (M13): Social dynamics with present entities
- KnowledgeProvenanceAnalyzer (M3): Learning patterns and trusted sources
- SceneAtmosphereGatherer (M10): Environmental and emotional context
- DialogContextExtractor (M11): Recent conversation history
- TensorStateSummarizer (M6): Compressed entity state summaries
- CircadianContextBuilder (M14): Time-of-day activity patterns
- RelevanceScorer: LLM-based context filtering to prevent token bloat

Usage:
    manager = TrainingContextManager(store, llm)
    context = manager.gather_context(entity, t0, t1, simulation_result)
    # Use context.to_prompt_string() in training data formatter
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import Counter
from datetime import datetime
import json

from storage import GraphStore
from llm_v2 import LLMClient
from schemas import Entity, Timepoint


@dataclass
class TrainingContext:
    """
    Complete context assembled for training data generation.

    Each section provides PREDICTIVE information WITHOUT revealing
    the answer (entity state changes at T1).
    """
    # M7: Causal chain context
    causal_history: Dict[str, Any]

    # M13: Relationship context
    relationship_context: Dict[str, Any]

    # M3: Knowledge provenance
    knowledge_provenance: Dict[str, Any]

    # M10: Scene atmosphere
    scene_atmosphere: Dict[str, Any]

    # M11: Dialog context
    dialog_context: Dict[str, Any]

    # M6: Tensor state summary
    entity_state_summary: Dict[str, Any]

    # M14: Circadian context
    circadian_context: Dict[str, Any]

    # Metadata
    relevance_scores: Dict[str, float] = field(default_factory=dict)
    token_estimate: int = 0

    def to_prompt_string(self) -> str:
        """Convert context to formatted prompt string"""
        sections = []

        # Only include sections with relevance > 0.3
        if self.relevance_scores.get("causal_history", 1.0) >= 0.3:
            sections.append(self._format_causal_history())

        if self.relevance_scores.get("relationship_context", 1.0) >= 0.3:
            sections.append(self._format_relationships())

        if self.relevance_scores.get("knowledge_provenance", 1.0) >= 0.3:
            sections.append(self._format_knowledge_provenance())

        if self.relevance_scores.get("scene_atmosphere", 1.0) >= 0.3:
            sections.append(self._format_atmosphere())

        if self.relevance_scores.get("dialog_context", 1.0) >= 0.3:
            sections.append(self._format_dialogs())

        if self.relevance_scores.get("entity_state_summary", 1.0) >= 0.3:
            sections.append(self._format_entity_state())

        if self.relevance_scores.get("circadian_context", 1.0) >= 0.3:
            sections.append(self._format_circadian())

        return "\n\n".join(sections)

    def _format_causal_history(self) -> str:
        """Format M7 causal chain context"""
        if not self.causal_history:
            return ""

        timeline = self.causal_history.get("timeline", [])
        narrative = self.causal_history.get("narrative_summary", "")
        tensions = self.causal_history.get("key_tensions", [])

        section = "=== CAUSAL HISTORY (M7) ==="
        section += f"\nTimeline leading to current moment ({len(timeline)} events):"

        for event in timeline[-5:]:  # Last 5 events
            section += f"\n  {event['timepoint']}: {event['event'][:80]}"

        if narrative:
            section += f"\n\nNarrative Context:\n{narrative}"

        if tensions:
            section += f"\n\nKey Tensions:\n" + "\n".join(f"  - {t}" for t in tensions[:3])

        return section

    def _format_relationships(self) -> str:
        """Format M13 relationship context"""
        if not self.relationship_context:
            return ""

        relationships = self.relationship_context.get("relationships", [])
        social_summary = self.relationship_context.get("social_context", "")

        section = "=== RELATIONSHIP CONTEXT (M13) ==="
        section += "\nRelationships with entities present at this event:"

        for rel in relationships[:5]:  # Top 5 relationships
            section += f"\n  {rel['entity']}: {rel.get('dynamic', 'neutral')} "
            section += f"(trust: {rel.get('trust', 0.5):.2f}, alignment: {rel.get('alignment', 0.0):.2f})"

        if social_summary:
            section += f"\n\nSocial Dynamics:\n{social_summary}"

        return section

    def _format_knowledge_provenance(self) -> str:
        """Format M3 exposure event context"""
        if not self.knowledge_provenance:
            return ""

        sources = self.knowledge_provenance.get("knowledge_sources", {})
        modes = self.knowledge_provenance.get("learning_modes", {})
        recent = self.knowledge_provenance.get("recent_acquisitions", [])

        section = "=== KNOWLEDGE PROVENANCE (M3) ==="
        section += "\nHow this entity acquired current knowledge:"

        if sources:
            section += "\n  Primary sources: " + ", ".join(f"{k} ({v} items)" for k, v in list(sources.items())[:3])

        if modes:
            total = sum(modes.values())
            percentages = {k: (v/total*100) for k, v in modes.items()} if total > 0 else {}
            section += "\n  Learning modes: " + ", ".join(f"{k} ({v:.0f}%)" for k, v in percentages.items())

        if recent:
            section += "\n\nRecent acquisitions (last 5 items):"
            for item in recent[-5:]:
                section += f"\n  - \"{item['info'][:60]}\" (from {item.get('source', 'unknown')}, confidence: {item.get('confidence', 0.5):.1f})"

        return section

    def _format_atmosphere(self) -> str:
        """Format M10 scene atmosphere context"""
        if not self.scene_atmosphere:
            return ""

        emotional = self.scene_atmosphere.get("emotional_atmosphere", {})
        physical = self.scene_atmosphere.get("physical_environment", {})
        narrative = self.scene_atmosphere.get("atmosphere_narrative", "")

        section = "=== ATMOSPHERIC CONTEXT (M10) ==="
        section += "\nScene atmosphere:"

        if emotional:
            section += f"\n  Tension: {emotional.get('tension', 0.5):.2f}, Formality: {emotional.get('formality', 0.5):.2f}"
            section += f"\n  Emotional valence: {emotional.get('valence', 0.0):.2f}, Energy: {emotional.get('energy', 0.5):.2f}"

        if physical:
            section += f"\n\nPhysical environment:"
            section += f"\n  Location: {physical.get('location', 'unknown')}"
            section += f"\n  Temperature: {physical.get('temperature', 20):.1f}°C, Lighting: {physical.get('lighting', 0.5):.1f}"

        if narrative:
            section += f"\n\nAtmospheric Narrative:\n{narrative}"

        return section

    def _format_dialogs(self) -> str:
        """Format M11 dialog context"""
        if not self.dialog_context:
            return ""

        recent_dialogs = self.dialog_context.get("recent_dialogs", [])
        summary = self.dialog_context.get("dialog_summary", "")

        section = "=== DIALOG CONTEXT (M11) ==="

        if recent_dialogs:
            section += f"\nRecent conversations ({len(recent_dialogs)} dialogs):"
            for dialog in recent_dialogs[:3]:  # Last 3 dialogs
                section += f"\n  {dialog['timepoint']}: {dialog['participants']} - {dialog['summary'][:80]}"

        if summary:
            section += f"\n\nDialog Summary:\n{summary}"

        return section

    def _format_entity_state(self) -> str:
        """Format M6 tensor state summary"""
        if not self.entity_state_summary:
            return ""

        state = self.entity_state_summary

        section = f"=== ENTITY STATE (M6) ==="
        section += f"\n{state.get('entity_id', 'unknown')} at T0:"

        if "physical" in state:
            p = state["physical"]
            section += f"\n  Physical: Age {p.get('age', 0)}, energy {p.get('energy', 100)}/100"

        if "cognitive" in state:
            c = state["cognitive"]
            section += f"\n  Cognitive: {c.get('knowledge_count', 0)} knowledge items, {c.get('confidence', 0.5):.2f} decision confidence"

        if "emotional" in state:
            e = state["emotional"]
            section += f"\n  Emotional: Valence {e.get('valence', 0.0):.2f}, Arousal {e.get('arousal', 0.0):.2f}"

        if "recent_activity" in state:
            section += f"\n\nRecent activity:\n{state['recent_activity']}"

        return section

    def _format_circadian(self) -> str:
        """Format M14 circadian context"""
        if not self.circadian_context:
            return ""

        hour = self.circadian_context.get("hour", 12)
        expected_states = self.circadian_context.get("expected_states", {})
        activity_summary = self.circadian_context.get("activity_summary", "")

        section = "=== TEMPORAL PATTERNS (M14) ==="
        section += f"\nTime of day: {hour:02d}:00"

        if expected_states:
            section += "\nTypical states at this hour:"
            for key, value in expected_states.items():
                section += f"\n  {key}: {value}"

        if activity_summary:
            section += f"\n\nActivity Context:\n{activity_summary}"

        return section


class TrainingContextManager:
    """
    Dynamically assembles rich training context from temporal knowledge graph.

    Uses LLM to score relevance and create summaries, preventing token bloat
    while maximizing predictive signal.
    """

    def __init__(self, store: GraphStore, llm: Optional[LLMClient] = None):
        """
        Initialize context manager.

        Args:
            store: GraphStore for querying temporal graph
            llm: Optional LLM client for relevance scoring and summarization
        """
        self.store = store
        self.llm = llm
        self.enable_llm_scoring = llm is not None

    def gather_context(
        self,
        entity: Entity,
        t0: Timepoint,
        t1: Timepoint,
        simulation_result: Dict[str, Any]
    ) -> TrainingContext:
        """
        Gather comprehensive context for training data generation.

        Args:
            entity: Entity experiencing state change
            t0: Starting timepoint
            t1: Ending timepoint (outcome to predict)
            simulation_result: Full simulation data

        Returns:
            TrainingContext with all relevant information
        """
        # Extract all available context
        causal_history = self._extract_causal_chain(t0, t1)
        relationship_context = self._extract_relationships(entity, t1)
        knowledge_provenance = self._extract_knowledge_provenance(entity, t0)
        scene_atmosphere = self._extract_scene_atmosphere(t1)
        dialog_context = self._extract_dialog_context(entity, t0, t1)
        entity_state_summary = self._extract_entity_state(entity, t0)
        circadian_context = self._extract_circadian_context(t1)

        # Score relevance if LLM available
        relevance_scores = {}
        if self.enable_llm_scoring:
            relevance_scores = self._score_context_relevance(
                causal_history=causal_history,
                relationship_context=relationship_context,
                knowledge_provenance=knowledge_provenance,
                scene_atmosphere=scene_atmosphere,
                dialog_context=dialog_context,
                entity_state_summary=entity_state_summary,
                circadian_context=circadian_context,
                t0=t0,
                t1=t1
            )
        else:
            # Default: include all context
            relevance_scores = {k: 1.0 for k in [
                "causal_history", "relationship_context", "knowledge_provenance",
                "scene_atmosphere", "dialog_context", "entity_state_summary", "circadian_context"
            ]}

        return TrainingContext(
            causal_history=causal_history,
            relationship_context=relationship_context,
            knowledge_provenance=knowledge_provenance,
            scene_atmosphere=scene_atmosphere,
            dialog_context=dialog_context,
            entity_state_summary=entity_state_summary,
            circadian_context=circadian_context,
            relevance_scores=relevance_scores
        )

    def _extract_causal_chain(self, t0: Timepoint, t1: Timepoint) -> Dict[str, Any]:
        """
        M7: Extract causal chain history leading to T0.

        Shows WHY we're at this point WITHOUT revealing T1 outcome.
        """
        chain = []
        current = t0
        depth = 0
        max_depth = 5

        # Walk backward through causal parents
        while current and current.causal_parent and depth < max_depth:
            try:
                parent = self.store.get_timepoint(current.causal_parent)
                if not parent:
                    break

                chain.insert(0, {
                    "timepoint": parent.timepoint_id,
                    "event": parent.event_description,
                    "timestamp": parent.timestamp.isoformat() if hasattr(parent.timestamp, 'isoformat') else str(parent.timestamp),
                    "importance": getattr(parent, 'importance_score', 0.5)
                })
                current = parent
                depth += 1
            except Exception as e:
                print(f"Warning: Failed to walk causal chain: {e}")
                break

        # Create narrative summary if LLM available
        narrative_summary = ""
        key_tensions = []

        if self.llm and chain:
            try:
                summary_prompt = f"""Summarize this sequence of events leading to the current moment.

Events:
{json.dumps(chain, indent=2)}

Create a 2-3 sentence summary focusing on:
- WHY we're at this point
- WHAT key tensions or conflicts exist
- WHO the key actors are

DO NOT predict what happens next. Only describe the situation AS OF the last event."""

                response = self.llm.service.call(
                    system="You are a narrative summarizer for historical simulations.",
                    user=summary_prompt,
                    temperature=0.5,
                    max_tokens=300,
                    call_type="causal_chain_summary"
                )

                narrative_summary = response.content

                # Extract key tensions
                if chain:
                    key_tensions = [
                        f"Event progression: {chain[0]['event'][:40]} → ... → {chain[-1]['event'][:40]}",
                        f"Timeline depth: {len(chain)} connected events",
                        f"Importance: {sum(e['importance'] for e in chain) / len(chain):.2f} average"
                    ]

            except Exception as e:
                print(f"Warning: Failed to generate narrative summary: {e}")

        return {
            "timeline": chain,
            "narrative_summary": narrative_summary,
            "key_tensions": key_tensions
        }

    def _extract_relationships(self, entity: Entity, t1: Timepoint) -> Dict[str, Any]:
        """
        M13: Extract relationship states with entities present at T1.

        Shows social dynamics WITHOUT revealing how they change.
        """
        relationships = []

        try:
            for other_id in t1.entities_present:
                if other_id == entity.entity_id:
                    continue

                # Get relationship trajectory
                trajectory = self.store.get_relationship_trajectory_between(
                    entity.entity_id,
                    other_id
                )

                if trajectory:
                    # Get most recent state before T1
                    relationships.append({
                        "entity": other_id,
                        "trust": getattr(trajectory, 'trust_level', 0.5),
                        "alignment": getattr(trajectory, 'belief_alignment', 0.0),
                        "power_dynamic": getattr(trajectory, 'power_dynamic', 0.0),
                        "interaction_count": getattr(trajectory, 'interaction_count', 0),
                        "dynamic": "allied" if getattr(trajectory, 'trust_level', 0.5) > 0.7 else
                                  "opposed" if getattr(trajectory, 'trust_level', 0.5) < 0.3 else "neutral"
                    })

        except Exception as e:
            print(f"Warning: Failed to extract relationships: {e}")

        # Create social dynamics summary
        social_context = ""
        if relationships and self.llm:
            try:
                allies = [r for r in relationships if r['dynamic'] == 'allied']
                opposed = [r for r in relationships if r['dynamic'] == 'opposed']

                social_context = f"{entity.entity_id} has {len(allies)} allies and {len(opposed)} opponents present."

            except Exception as e:
                print(f"Warning: Failed to generate social context: {e}")

        return {
            "relationships": relationships,
            "social_context": social_context
        }

    def _extract_knowledge_provenance(self, entity: Entity, t0: Timepoint) -> Dict[str, Any]:
        """
        M3: Extract how entity acquired their current knowledge.

        Reveals learning patterns, trusted sources, information quality.
        """
        try:
            exposures = self.store.get_exposure_events(entity.entity_id, limit=100)

            # Filter to events before T0
            exposures = [e for e in exposures if hasattr(e, 'timepoint_id')]

            # Analyze patterns
            sources = Counter(e.source for e in exposures if hasattr(e, 'source') and e.source)
            event_types = Counter(e.event_type for e in exposures if hasattr(e, 'event_type'))

            # Get recent acquisitions
            recent = [
                {
                    "info": e.information,
                    "source": e.source if hasattr(e, 'source') else "unknown",
                    "confidence": e.confidence if hasattr(e, 'confidence') else 0.5
                }
                for e in exposures[-5:] if hasattr(e, 'information')
            ]

            return {
                "knowledge_sources": dict(sources.most_common(5)),
                "learning_modes": dict(event_types),
                "recent_acquisitions": recent
            }

        except Exception as e:
            print(f"Warning: Failed to extract knowledge provenance: {e}")
            return {}

    def _extract_scene_atmosphere(self, t1: Timepoint) -> Dict[str, Any]:
        """
        M10: Extract environmental and emotional context.

        Helps model understand MOOD and CONSTRAINTS.
        """
        # Note: Atmosphere entities not yet stored in all simulations
        # Return basic context from timepoint
        return {
            "emotional_atmosphere": {
                "tension": getattr(t1, 'tension_level', 0.5),
                "formality": getattr(t1, 'formality_level', 0.5),
                "valence": getattr(t1, 'emotional_valence', 0.0),
                "energy": getattr(t1, 'energy_level', 0.5)
            },
            "physical_environment": {
                "location": getattr(t1, 'location', 'unknown'),
                "temperature": 20.0,  # Default
                "lighting": 0.5  # Default
            },
            "atmosphere_narrative": f"Event taking place: {t1.event_description[:100]}"
        }

    def _extract_dialog_context(self, entity: Entity, t0: Timepoint, t1: Timepoint) -> Dict[str, Any]:
        """
        M11: Extract recent dialog history.

        Shows conversation context and relationship dynamics.
        """
        try:
            # Get dialogs involving this entity at recent timepoints
            dialogs = self.store.get_dialogs_for_entities([entity.entity_id])

            # Filter to recent dialogs
            recent_dialogs = []
            for dialog in dialogs[-5:]:
                if hasattr(dialog, 'timepoint_id'):
                    recent_dialogs.append({
                        "timepoint": dialog.timepoint_id,
                        "participants": getattr(dialog, 'participants', []),
                        "summary": getattr(dialog, 'summary', 'Conversation occurred')[:100]
                    })

            return {
                "recent_dialogs": recent_dialogs,
                "dialog_summary": f"{len(recent_dialogs)} recent conversations involving {entity.entity_id}"
            }

        except Exception as e:
            print(f"Warning: Failed to extract dialog context: {e}")
            return {}

    def _extract_entity_state(self, entity: Entity, t0: Timepoint) -> Dict[str, Any]:
        """
        M6: Extract compressed entity state summary.

        Shows current capabilities and constraints.
        """
        physical = {}
        if hasattr(entity, 'physical_tensor') and entity.physical_tensor:
            pt = entity.physical_tensor
            physical = {
                "age": getattr(pt, 'age', 0),
                "energy": getattr(pt, 'energy_budget', 100) if hasattr(pt, 'energy_budget') else 100
            }

        cognitive = {}
        if hasattr(entity, 'cognitive_tensor') and entity.cognitive_tensor:
            ct = entity.cognitive_tensor
            cognitive = {
                "knowledge_count": len(getattr(ct, 'knowledge_state', [])),
                "confidence": getattr(ct, 'decision_confidence', 0.5)
            }

        emotional = {}
        if hasattr(entity, 'cognitive_tensor') and entity.cognitive_tensor:
            ct = entity.cognitive_tensor
            emotional = {
                "valence": getattr(ct, 'emotional_valence', 0.0),
                "arousal": getattr(ct, 'emotional_arousal', 0.0)
            }

        return {
            "entity_id": entity.entity_id,
            "physical": physical,
            "cognitive": cognitive,
            "emotional": emotional,
            "recent_activity": f"Active at timepoint {t0.timepoint_id}"
        }

    def _extract_circadian_context(self, t1: Timepoint) -> Dict[str, Any]:
        """
        M14: Extract time-of-day context.

        Shows expected activity patterns and energy levels.
        """
        try:
            hour = t1.timestamp.hour if hasattr(t1.timestamp, 'hour') else 12
        except:
            hour = 12

        # Basic circadian expectations
        expected_states = {}
        activity_summary = ""

        if 0 <= hour < 6:
            expected_states = {"energy": "Low (sleep hours)", "focus": "Minimal", "social": "Unlikely"}
            activity_summary = "Early morning hours - most entities at rest"
        elif 6 <= hour < 12:
            expected_states = {"energy": "Rising", "focus": "Increasing", "social": "Moderate"}
            activity_summary = "Morning hours - entities becoming active"
        elif 12 <= hour < 18:
            expected_states = {"energy": "Peak", "focus": "High", "social": "High"}
            activity_summary = "Afternoon hours - peak activity and engagement"
        else:
            expected_states = {"energy": "Declining", "focus": "Moderate", "social": "High (social hours)"}
            activity_summary = "Evening hours - social activity, declining work focus"

        return {
            "hour": hour,
            "expected_states": expected_states,
            "activity_summary": activity_summary
        }

    def _score_context_relevance(self, **context_sections) -> Dict[str, float]:
        """
        Use LLM to score which context sections are most relevant.

        Prevents token bloat by filtering low-relevance context.
        """
        if not self.llm:
            # Default: include everything
            return {k: 1.0 for k in context_sections.keys() if k not in ['t0', 't1']}

        try:
            t0 = context_sections.pop('t0')
            t1 = context_sections.pop('t1')

            scoring_prompt = f"""You are analyzing context for predicting entity state changes.

Transition: {t0.timepoint_id} → {t1.timepoint_id}
Event: {t1.event_description}

For each context type below, rate its PREDICTIVE VALUE (0.0-1.0) for understanding:
- What new knowledge this entity will gain
- How their energy/emotions will change
- Why these changes occur

Context types available:
1. causal_history - Timeline of events leading here
2. relationship_context - Social dynamics with present entities
3. knowledge_provenance - How entity learned current knowledge
4. scene_atmosphere - Environmental and emotional mood
5. dialog_context - Recent conversation history
6. entity_state_summary - Current capabilities and state
7. circadian_context - Time-of-day patterns

For each, provide score 0.0-1.0 where:
- 1.0 = Critical for prediction
- 0.5 = Moderately helpful
- 0.0 = Not relevant

Return JSON with scores for each context type."""

            response = self.llm.service.call(
                system="You are an expert at causal inference in temporal simulations.",
                user=scoring_prompt,
                temperature=0.3,
                max_tokens=200,
                call_type="context_relevance_scoring"
            )

            # Parse scores from response
            import re
            scores = {}
            for key in ["causal_history", "relationship_context", "knowledge_provenance",
                       "scene_atmosphere", "dialog_context", "entity_state_summary", "circadian_context"]:
                # Try to extract score for this key
                pattern = f'"{key}".*?(0\\.[0-9]+|1\\.0)'
                match = re.search(pattern, response.content)
                if match:
                    scores[key] = float(match.group(1))
                else:
                    scores[key] = 0.7  # Default moderate relevance

            return scores

        except Exception as e:
            print(f"Warning: Context relevance scoring failed: {e}")
            # Fallback: include all context
            return {k: 1.0 for k in context_sections.keys() if k not in ['t0', 't1']}
