# ============================================================================
# query_interface.py - Natural language query interface with lazy resolution elevation
# ============================================================================
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel
from schemas import Entity, Timepoint, ResolutionLevel
from storage import GraphStore
from llm import LLMClient
from resolution_engine import ResolutionEngine
from instructor import OpenAISchema


class QueryIntent(OpenAISchema):
    """Parsed intent from natural language query"""
    target_entity: Optional[str] = None
    target_timepoint: Optional[str] = None
    information_type: str = "general"  # knowledge, relationships, actions, dialog
    context_entities: List[str] = []  # Other entities that matter
    confidence: float = 0.0
    reasoning: str = ""


class QueryInterface:
    """Natural language query interface with lazy resolution elevation"""

    def __init__(self, store: GraphStore, llm_client: LLMClient):
        self.store = store
        self.llm_client = llm_client
        self.resolution_engine = ResolutionEngine(store)

    def parse_query(self, query: str) -> QueryIntent:
        """Parse natural language query into structured intent using LLM"""
        if self.llm_client.dry_run:
            # Fallback to simple rule-based parsing in dry-run mode
            return self._parse_query_simple(query)

        # Get available entities and timepoints for context
        entities = self._get_all_entity_names()
        timepoints = self.store.get_all_timepoints()
        timepoint_descriptions = [f"{tp.timepoint_id}: {tp.event_description[:50]}..." for tp in timepoints[:5]]

        # Use LLM for structured query parsing
        prompt = f"""Parse this natural language query about a temporal simulation into structured intent.

Available entities: {', '.join(entities)}
Recent timepoints: {'; '.join(timepoint_descriptions)}

Query: "{query}"

Extract:
- target_entity: Which entity is the query about? (use exact entity name or null)
- target_timepoint: Which timepoint does this refer to? (use timepoint_id or null)
- information_type: What type of information? (knowledge/relationships/actions/dialog/general)
- context_entities: Other entities mentioned or relevant
- confidence: How confident are you in this parsing? (0.0-1.0)
- reasoning: Brief explanation of your parsing"""

        try:
            response = self.llm_client.client.chat.completions.create(
                model="openai/gpt-4o-mini",
                response_model=QueryIntent,
                messages=[{"role": "user", "content": prompt}]
            )
            self.llm_client.token_count += 500  # Estimate
            self.llm_client.cost += 0.005
            return response
        except Exception as e:
            print(f"LLM parsing failed, falling back to simple parsing: {e}")
            return self._parse_query_simple(query)

    def _parse_query_simple(self, query: str) -> QueryIntent:
        """Improved rule-based parsing fallback"""
        query_lower = query.lower()
        entities = self._get_all_entity_names()
        timepoints = self.store.get_all_timepoints()

        # Improved entity detection - handle partial names and variations
        entity_mappings = {
            # Full names
            "george washington": "george_washington",
            "john adams": "john_adams",
            "thomas jefferson": "thomas_jefferson",
            "alexander hamilton": "alexander_hamilton",
            "james madison": "james_madison",
            # Partial names and common variations
            "washington": "george_washington",
            "adams": "john_adams",
            "jefferson": "thomas_jefferson",
            "hamilton": "alexander_hamilton",
            "madison": "james_madison",
            "president": "george_washington",  # Context-dependent but common
        }

        # Find all mentioned entities
        target_entity = None
        context_entities = []
        found_entities = []

        # Sort by length (longest first) to match full names before partials
        sorted_mappings = sorted(entity_mappings.items(), key=lambda x: len(x[0]), reverse=True)

        for name_variant, entity_id in sorted_mappings:
            if name_variant in query_lower and entity_id not in found_entities:
                found_entities.append(entity_id)

        if found_entities:
            target_entity = found_entities[0]  # Primary entity
            context_entities = found_entities[1:]  # Additional entities

        # Event/timepoint detection
        target_timepoint = None
        event_keywords = {
            "inauguration": ["inauguration", "swearing in", "oath"],
            "cabinet meeting": ["cabinet meeting", "cabinet"],
            "congressional": ["congressional", "congress", "legislative"],
            "diplomatic": ["diplomatic", "reception", "international"]
        }

        for event_type, keywords in event_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                # Find matching timepoint
                for tp in timepoints:
                    if any(keyword in tp.event_description.lower() for keyword in keywords):
                        target_timepoint = tp.timepoint_id
                        break
                break

        # Improved information type detection
        info_type = "general"
        confidence = 0.5  # Start lower, build up

        # Knowledge/thoughts queries
        if any(word in query_lower for word in ["think", "feel", "believe", "opinion", "thought", "felt", "concerned"]):
            info_type = "knowledge"
            confidence += 0.2

        # Dialog/conversation queries
        elif any(word in query_lower for word in ["talk", "say", "said", "speak", "conversation", "told", "spoke"]):
            info_type = "dialog"
            confidence += 0.2

        # Action/behavior queries
        elif any(word in query_lower for word in ["do", "did", "action", "activity", "perform", "take", "took"]):
            info_type = "actions"
            confidence += 0.2

        # Relationship queries
        elif any(word in query_lower for word in ["interact", "relationship", "work with", "together", "alliance"]):
            info_type = "relationships"
            confidence += 0.2

        # Description/event queries (like "describe the cabinet meeting")
        elif any(word in query_lower for word in ["describe", "what happened", "during", "at the"]):
            info_type = "general"
            confidence += 0.1

        # Boost confidence based on entity detection quality
        if target_entity:
            confidence += 0.3
        if context_entities:
            confidence += 0.1
        if target_timepoint:
            confidence += 0.2

        # Cap confidence
        confidence = min(confidence, 1.0)

        reasoning_parts = []
        if target_entity:
            reasoning_parts.append(f"Found primary entity: {target_entity}")
        if context_entities:
            reasoning_parts.append(f"Found context entities: {', '.join(context_entities)}")
        if target_timepoint:
            reasoning_parts.append(f"Detected timepoint: {target_timepoint}")
        reasoning_parts.append(f"Info type: {info_type}")

        return QueryIntent(
            target_entity=target_entity,
            target_timepoint=target_timepoint,
            information_type=info_type,
            context_entities=context_entities,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts)
        )

    def synthesize_response(self, query_intent: QueryIntent) -> str:
        """Generate answer from entity states with lazy resolution elevation and attribution"""

        # Handle different query types
        if not query_intent.target_entity:
            # Check if this is an event/timepoint-focused query
            if query_intent.target_timepoint:
                return self._synthesize_timepoint_response(query_intent)
            # Check if this is a multi-entity relationship query
            elif query_intent.context_entities:
                return self._synthesize_relationship_response(query_intent)
            else:
                return "I couldn't identify which entity you're asking about. Available entities: " + ", ".join(self._get_all_entity_names())

        entity = self.store.get_entity(query_intent.target_entity)
        if not entity:
            return f"I don't have information about {query_intent.target_entity}."

        # Check if entity resolution is sufficient for the query
        required_resolution = self._get_required_resolution(query_intent.information_type)

        # Lazy elevation: if current resolution is too low, elevate it
        if self._resolution_level_value(entity.resolution_level) < self._resolution_level_value(required_resolution):
            success = self._elevate_entity_resolution(entity, required_resolution)
            if success:
                print(f"  Elevated {entity.entity_id} resolution to {required_resolution.value}")

        # Record this query for future resolution decisions
        self.resolution_engine.record_query(entity.entity_id)

        # Get relevant knowledge based on query intent
        knowledge_state = entity.entity_metadata.get("knowledge_state", [])
        relevant_knowledge = self._filter_relevant_knowledge(knowledge_state, query_intent)

        # Build response with attribution
        response_parts = []

        if relevant_knowledge:
            # Group knowledge by exposure source for better attribution
            exposure_events = self.store.get_exposure_events(entity.entity_id)
            source_map = {event.information: event.source for event in exposure_events}

            response_parts.append(f"Based on {entity.entity_id}'s knowledge from the temporal simulation:")

            for i, knowledge in enumerate(relevant_knowledge[:3]):  # Limit to 3 most relevant
                source = source_map.get(knowledge, "personal experience")
                response_parts.append(f"• {knowledge}")
                if source != "personal experience":
                    response_parts.append(f"  (learned from: {source})")

            if len(relevant_knowledge) > 3:
                response_parts.append(f"... and {len(relevant_knowledge) - 3} more related items")

            # Add temporal context if timepoint specified
            if query_intent.target_timepoint:
                timepoint = self.store.get_timepoint(query_intent.target_timepoint)
                if timepoint:
                    response_parts.append(f"\nThis knowledge reflects the state at: {timepoint.event_description}")

        else:
            response_parts.append(f"{entity.entity_id} doesn't have specific knowledge about that topic in the current temporal simulation.")

        # Add metadata about resolution level
        response_parts.append(f"\n[Entity resolution: {entity.resolution_level.value}, Confidence: {query_intent.confidence:.1f}]")

        return "\n".join(response_parts)

    def _get_required_resolution(self, info_type: str) -> ResolutionLevel:
        """Determine minimum resolution needed for information type"""
        requirements = {
            "general": ResolutionLevel.SCENE,
            "knowledge": ResolutionLevel.GRAPH,
            "relationships": ResolutionLevel.GRAPH,
            "actions": ResolutionLevel.DIALOG,
            "dialog": ResolutionLevel.TRAINED
        }
        return requirements.get(info_type, ResolutionLevel.SCENE)

    def _resolution_level_value(self, level: ResolutionLevel) -> int:
        """Convert resolution level to numeric value for comparison"""
        hierarchy = {
            ResolutionLevel.TENSOR_ONLY: 0,
            ResolutionLevel.SCENE: 1,
            ResolutionLevel.GRAPH: 2,
            ResolutionLevel.DIALOG: 3,
            ResolutionLevel.TRAINED: 4
        }
        return hierarchy.get(level, 0)

    def _elevate_entity_resolution(self, entity: Entity, target_resolution: ResolutionLevel) -> bool:
        """Elevate entity resolution by calling LLM for additional details"""
        try:
            # Get the most recent timepoint for this entity
            timepoints = self.store.get_all_timepoints()
            if not timepoints:
                return False

            latest_timepoint = max(timepoints, key=lambda tp: tp.timestamp)

            # Get entity's current knowledge
            current_knowledge = entity.entity_metadata.get("knowledge_state", [])

            # Call LLM to generate more detailed information
            enhanced_context = {
                "entity_role": entity.entity_metadata.get("role", ""),
                "entity_age": entity.entity_metadata.get("age", 0),
                "entity_location": entity.entity_metadata.get("location", ""),
                "timepoint": latest_timepoint.timestamp.isoformat(),
                "event": latest_timepoint.event_description,
                "resolution_target": target_resolution.value
            }

            population = self.llm_client.populate_entity(
                {"entity_id": entity.entity_id, "timestamp": latest_timepoint.timestamp.isoformat()},
                enhanced_context,
                current_knowledge  # Pass current knowledge for evolution
            )

            # Update entity with enhanced knowledge
            all_knowledge = list(set(current_knowledge + population.knowledge_state))
            entity.entity_metadata["knowledge_state"] = all_knowledge
            entity.resolution_level = target_resolution

            # Save updated entity
            self.store.save_entity(entity)

            # Record new exposure events
            exposure_events = []
            for knowledge_item in population.knowledge_state:
                if knowledge_item not in current_knowledge:
                    from schemas import ExposureEvent
                    exposure_event = ExposureEvent(
                        entity_id=entity.entity_id,
                        event_type="learned",
                        information=knowledge_item,
                        source=f"Resolution elevation to {target_resolution.value}",
                        timestamp=latest_timepoint.timestamp,
                        confidence=population.confidence,
                        timepoint_id=latest_timepoint.timepoint_id
                    )
                    exposure_events.append(exposure_event)

            if exposure_events:
                self.store.save_exposure_events(exposure_events)

            return True

        except Exception as e:
            print(f"Failed to elevate resolution for {entity.entity_id}: {e}")
            return False

    def _filter_relevant_knowledge(self, knowledge_state: List[str], query_intent: QueryIntent) -> List[str]:
        """Filter knowledge items based on query intent"""
        if not knowledge_state:
            return []

        query_lower = " ".join([getattr(query_intent, attr, "") or "" for attr in ["target_entity", "information_type"]]).lower()

        # Score each knowledge item based on relevance
        scored_knowledge = []
        for knowledge in knowledge_state:
            score = 0

            # Information type matching
            knowledge_lower = knowledge.lower()
            if query_intent.information_type == "knowledge":
                if any(word in knowledge_lower for word in ["think", "believe", "feel", "opinion", "thought"]):
                    score += 2
            elif query_intent.information_type == "actions":
                if any(word in knowledge_lower for word in ["do", "did", "action", "activity", "perform"]):
                    score += 2
            elif query_intent.information_type == "dialog":
                if any(word in knowledge_lower for word in ["say", "said", "talk", "speak", "conversation"]):
                    score += 2

            # Keyword matching
            query_words = query_lower.split()
            for word in query_words:
                if word in knowledge_lower:
                    score += 1

            scored_knowledge.append((knowledge, score))

        # Sort by relevance and return top matches
        scored_knowledge.sort(key=lambda x: x[1], reverse=True)

        # For general queries, return some knowledge even if relevance is low
        if query_intent.information_type == "general":
            return [k for k, s in scored_knowledge[:3]]  # Return top 3 regardless of score
        else:
            return [k for k, s in scored_knowledge if s > 0][:5]  # Top 5 with any relevance

    def _synthesize_timepoint_response(self, query_intent: QueryIntent) -> str:
        """Generate response for timepoint-focused queries (e.g., 'Describe the cabinet meeting')"""
        timepoint = self.store.get_timepoint(query_intent.target_timepoint)
        if not timepoint:
            return f"I don't have information about timepoint {query_intent.target_timepoint}."

        # Get all entities present at this timepoint
        entities_at_timepoint = []
        for entity_id in timepoint.entities_present:
            entity = self.store.get_entity(entity_id)
            if entity:
                entities_at_timepoint.append(entity)

        response_parts = [f"During the {timepoint.event_description.lower()}:"]
        response_parts.append("")

        # Show what each entity experienced/learned
        for entity in entities_at_timepoint:
            knowledge_state = entity.entity_metadata.get("knowledge_state", [])
            # Filter knowledge relevant to this timepoint
            timepoint_knowledge = []
            exposure_events = self.store.get_exposure_events(entity.entity_id)
            for event in exposure_events:
                if event.timepoint_id == query_intent.target_timepoint:
                    timepoint_knowledge.append(event.information)

            if timepoint_knowledge:
                response_parts.append(f"• {entity.entity_id.replace('_', ' ').title()}:")
                for knowledge in timepoint_knowledge[:2]:  # Show up to 2 items per entity
                    response_parts.append(f"  - {knowledge}")
                response_parts.append("")

        if len(response_parts) == 2:  # Only the header
            response_parts.append("No specific details available about this event.")

        response_parts.append(f"[Timepoint: {query_intent.target_timepoint}, Confidence: {query_intent.confidence:.1f}]")

        return "\n".join(response_parts)

    def _synthesize_relationship_response(self, query_intent: QueryIntent) -> str:
        """Generate response for multi-entity relationship queries (e.g., 'How did Hamilton and Jefferson interact?')"""
        if not query_intent.context_entities:
            return "I need more specific information about which entities you're asking about."

        # For now, focus on the primary entity and mention relationships with context entities
        # This is a simplified approach - could be expanded for more complex relationship analysis
        primary_entity_id = query_intent.context_entities[0]  # Use first context entity as primary
        primary_entity = self.store.get_entity(primary_entity_id)

        if not primary_entity:
            return f"I don't have information about {primary_entity_id}."

        # Get knowledge that might relate to interactions
        knowledge_state = primary_entity.entity_metadata.get("knowledge_state", [])
        relevant_knowledge = []

        # Look for knowledge that might indicate relationships or interactions
        for knowledge in knowledge_state:
            knowledge_lower = knowledge.lower()
            # Check if knowledge mentions other entities from context
            for other_entity in query_intent.context_entities[1:]:
                other_name = other_entity.replace('_', ' ')
                if other_name.lower() in knowledge_lower:
                    relevant_knowledge.append(knowledge)
                    break

        response_parts = [f"Based on {primary_entity_id.replace('_', ' ').title()}'s knowledge of interactions:"]

        if relevant_knowledge:
            for knowledge in relevant_knowledge[:3]:
                response_parts.append(f"• {knowledge}")
        else:
            response_parts.append(f"• {primary_entity_id.replace('_', ' ').title()} doesn't have specific knowledge about interactions with others in this context.")

        response_parts.append(f"\n[Entity: {primary_entity_id}, Confidence: {query_intent.confidence:.1f}]")

        return "\n".join(response_parts)

    def _get_all_entity_names(self) -> List[str]:
        """Get list of all entity IDs from database"""
        from sqlmodel import Session, select
        from schemas import Entity

        with Session(self.store.engine) as session:
            entities = session.exec(select(Entity)).all()
            return [entity.entity_id for entity in entities]
