# ============================================================================
# workflows/relationship_analysis.py - Multi-Entity Synthesis (Mechanism 13)
# ============================================================================
"""
Relationship analysis and multi-entity synthesis.

Contains:
- analyze_relationship_evolution: Track relationship changes across timepoints
- detect_contradictions: Find inconsistent beliefs between entities
- synthesize_multi_entity_response: Generate response from multiple perspectives (@M13)
- Helper functions for relationship events, beliefs, roles
"""

from typing import List, Dict, Optional
from datetime import datetime
import json

from schemas import (
    Entity, RelationshipTrajectory, RelationshipState,
    RelationshipMetrics, Contradiction
)
from metadata.tracking import track_mechanism

# Import compute_relationship_metrics from dialog_synthesis to avoid duplication
from workflows.dialog_synthesis import compute_relationship_metrics


def analyze_relationship_evolution(
    entity_a: str,
    entity_b: str,
    timeline: List[Dict],
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    store: Optional['GraphStore'] = None
) -> RelationshipTrajectory:
    """Track relationship changes across timepoints"""

    if not store:
        # Return minimal trajectory if no store available
        return RelationshipTrajectory(
            trajectory_id=f"trajectory_{entity_a}_{entity_b}",
            entity_a=entity_a,
            entity_b=entity_b,
            start_timepoint="unknown",
            end_timepoint="unknown",
            states="[]",
            overall_trend="stable",
            key_events=[]
        )

    # Get timepoints in range
    timepoints = store.get_timepoints_in_range(start_time, end_time)
    relevant_timepoints = [
        tp for tp in timepoints
        if entity_a in tp.entities_present and entity_b in tp.entities_present
    ]

    if not relevant_timepoints:
        return RelationshipTrajectory(
            trajectory_id=f"trajectory_{entity_a}_{entity_b}",
            entity_a=entity_a,
            entity_b=entity_b,
            start_timepoint="none",
            end_timepoint="none",
            states="[]",
            overall_trend="no_interaction",
            key_events=[]
        )

    states = []
    key_events = []

    for tp in relevant_timepoints:
        entity_a_obj = store.get_entity_at_timepoint(entity_a, tp.timepoint_id)
        entity_b_obj = store.get_entity_at_timepoint(entity_b, tp.timepoint_id)

        if not entity_a_obj or not entity_b_obj:
            continue

        # Compute relationship metrics
        metrics = compute_relationship_metrics(entity_a_obj, entity_b_obj)

        # Get recent events affecting this relationship
        recent_events = get_relationship_events(entity_a, entity_b, tp.timepoint_id, store)

        state = RelationshipState(
            entity_a=entity_a,
            entity_b=entity_b,
            timestamp=tp.timestamp,
            timepoint_id=tp.timepoint_id,
            metrics=metrics,
            recent_events=recent_events
        )
        states.append(state)

        # Track key events
        if recent_events:
            key_events.extend(recent_events)

    # Determine overall trend
    if len(states) >= 2:
        first_trust = states[0].metrics.trust_level
        last_trust = states[-1].metrics.trust_level
        trust_change = last_trust - first_trust

        if trust_change > 0.2:
            overall_trend = "improving"
        elif trust_change < -0.2:
            overall_trend = "deteriorating"
        else:
            overall_trend = "stable"
    else:
        overall_trend = "stable"

    # Phase 7.5: Convert datetime objects to strings for JSON serialization
    serializable_states = []
    for s in states:
        state_dict = s.dict()
        # Convert any datetime objects to ISO format strings
        if 'timestamp' in state_dict and hasattr(state_dict['timestamp'], 'isoformat'):
            state_dict['timestamp'] = state_dict['timestamp'].isoformat()
        serializable_states.append(state_dict)

    return RelationshipTrajectory(
        trajectory_id=f"trajectory_{entity_a}_{entity_b}_{relevant_timepoints[0].timepoint_id}_{relevant_timepoints[-1].timepoint_id}",
        entity_a=entity_a,
        entity_b=entity_b,
        start_timepoint=relevant_timepoints[0].timepoint_id,
        end_timepoint=relevant_timepoints[-1].timepoint_id,
        states=json.dumps(serializable_states),
        overall_trend=overall_trend,
        key_events=list(set(key_events))  # Remove duplicates
    )


def detect_contradictions(
    entities: List[Entity],
    timepoint: 'Timepoint',
    store: Optional['GraphStore'] = None
) -> List[Contradiction]:
    """Find inconsistent beliefs or knowledge between entities"""

    contradictions = []

    for i, entity_a in enumerate(entities):
        for entity_b in entities[i+1:]:  # Skip self-comparisons (Phase 7.5: Fixed enumerate bug)
            # Compare knowledge claims
            knowledge_a = set(entity_a.entity_metadata.get("knowledge_state", []))
            knowledge_b = set(entity_b.entity_metadata.get("knowledge_state", []))

            # Find overlapping knowledge topics
            overlapping = knowledge_a & knowledge_b

            for topic in overlapping:
                # Check if same topic has conflicting interpretations
                belief_a = get_belief_on_topic(entity_a, topic)
                belief_b = get_belief_on_topic(entity_b, topic)

                if belief_a is not None and belief_b is not None:
                    conflict_severity = abs(belief_a - belief_b)

                    # Only consider significant conflicts
                    if conflict_severity > 0.3:  # More than 30% disagreement
                        contradiction = Contradiction(
                            entity_a=entity_a.entity_id,
                            entity_b=entity_b.entity_id,
                            topic=topic,
                            position_a=belief_a,
                            position_b=belief_b,
                            severity=conflict_severity,
                            timepoint_id=timepoint.timepoint_id,
                            context=f"Conflicting beliefs on '{topic}': {entity_a.entity_id} believes {belief_a:.2f}, {entity_b.entity_id} believes {belief_b:.2f}",
                            resolution_possible=conflict_severity < 0.8  # Very extreme conflicts may be unresolvable
                        )
                        contradictions.append(contradiction)

    return contradictions


@track_mechanism("M13", "multi_entity_synthesis")
def synthesize_multi_entity_response(
    entities: List[str],
    query: str,
    timeline: List[Dict],
    llm: 'LLMClient',
    store: Optional['GraphStore'] = None
) -> Dict:
    """Generate response requiring multiple entity perspectives"""

    if not store:
        return {"error": "No store available for multi-entity synthesis"}

    # Load entity states and relationship trajectories
    entity_states = []
    trajectories = []

    for i, entity_a in enumerate(entities):
        entity_obj = store.get_entity(entity_a)
        if not entity_obj:
            continue

        # Get knowledge and personality
        knowledge = entity_obj.entity_metadata.get("knowledge_state", [])
        personality = entity_obj.entity_metadata.get("personality_traits", ["unknown"])

        entity_states.append({
            "entity_id": entity_a,
            "knowledge": knowledge,
            "personality": personality,
            "role": infer_historical_role(entity_a)
        })

        # Get relationship trajectories with other entities
        for entity_b in entities[i+1:]:
            trajectory = analyze_relationship_evolution(
                entity_a, entity_b, timeline, store=store
            )
            trajectories.append({
                "entities": [entity_a, entity_b],
                "trajectory": trajectory.dict()
            })

    # Detect contradictions
    entity_objects = [store.get_entity(eid) for eid in entities if store.get_entity(eid)]
    entity_objects = [e for e in entity_objects if e is not None]  # Filter out None values

    # Get current timepoint for contradiction detection
    current_tp = timeline[-1] if timeline else None
    if current_tp:
        contradictions = detect_contradictions(entity_objects, current_tp, store)
        contradiction_data = [c.dict() for c in contradictions]
    else:
        contradiction_data = []

    # Build synthesis context
    context = {
        "entities": entity_states,
        "relationship_trajectories": trajectories,
        "contradictions": contradiction_data,
        "query": query,
        "timeline_context": {
            "span": f"{len(timeline)} timepoints" if timeline else "unknown",
            "current_event": current_tp.get("event_description", "unknown") if current_tp else "unknown"
        }
    }

    # Generate comparative analysis
    prompt = f"""Analyze the relationship and interactions between multiple historical entities based on the provided context.

CONTEXT:
{json.dumps(context, indent=2)}

QUERY: {query}

Provide a comprehensive analysis that:
1. Compares how different entities perceive the same events/knowledge
2. Describes relationship dynamics and their evolution
3. Identifies any contradictions or conflicts between entities
4. Explains how personality traits influence their interactions
5. Shows how knowledge differences affect their perspectives

Return a JSON object with these fields:
- summary: string overview of entity relationships
- key_differences: array of strings highlighting contrasting views
- relationship_dynamics: object describing current relationship states
- contradictions_identified: array of contradiction descriptions
- personality_influences: object mapping entities to their behavioral tendencies
- knowledge_gaps: array of information one entity has that others lack

Return only valid JSON, no other text."""

    # Always use real LLM (no dry_run mode)
    response_data = llm.generate_dialog(prompt, max_tokens=1500)
    # Parse the response as JSON
    try:
        response = json.loads(response_data)
    except:
            response = {"error": "Failed to parse LLM response"}

    return response


def get_relationship_events(entity_a: str, entity_b: str, timepoint_id: str,
                           store: Optional['GraphStore'] = None) -> List[str]:
    """Get recent events that affected the relationship between two entities"""
    if not store:
        return []

    # Look for dialogs involving both entities at this timepoint
    dialogs = store.get_dialogs_at_timepoint(timepoint_id)
    relevant_events = []

    for dialog in dialogs:
        participants = json.loads(dialog.participants)
        if entity_a in participants and entity_b in participants:
            turns = json.loads(dialog.turns)
            for turn in turns:
                if turn.get("speaker") in [entity_a, entity_b]:
                    relevant_events.append(f"{turn.get('speaker')}: {turn.get('content', '')[:100]}...")

    return relevant_events[:3]  # Limit to 3 most recent


def get_belief_on_topic(entity: Entity, topic: str) -> Optional[float]:
    """Extract entity's belief strength on a topic (-1.0 to 1.0)"""
    # Simple heuristic: look for topic in knowledge and assign belief based on context
    knowledge = entity.entity_metadata.get("knowledge_state", [])

    for item in knowledge:
        if topic.lower() in item.lower():
            # Mock belief extraction - in practice this would use more sophisticated NLP
            if any(neg in item.lower() for neg in ["not", "never", "against", "opposed"]):
                return -0.7  # Negative belief
            elif any(pos in item.lower() for pos in ["support", "favor", "agree", "good"]):
                return 0.7   # Positive belief
            else:
                return 0.0   # Neutral belief

    return None  # No belief found on topic


def infer_historical_role(entity_id: str) -> str:
    """Infer historical role from entity ID"""
    role_map = {
        "washington": "President/General",
        "jefferson": "Secretary of State/Philosopher",
        "hamilton": "Secretary of Treasury/Financial Expert",
        "adams": "Vice President/Diplomat",
        "madison": "Secretary of State/Constitutional Scholar"
    }
    return role_map.get(entity_id.lower(), "Historical Figure")
