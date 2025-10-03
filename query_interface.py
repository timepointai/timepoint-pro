# ============================================================================
# query_interface.py - Natural language query interface with lazy resolution elevation
# ============================================================================
import numpy as np
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import hashlib
import re
import json
from schemas import Entity, Timepoint, ResolutionLevel, EnvironmentEntity, AtmosphereEntity, CrowdEntity
from storage import GraphStore
from llm_v2 import LLMClient  # Use new centralized service
from resolution_engine import ResolutionEngine
# Removed OpenAI/instructor dependency
from tensors import load_compressed_entity_data

# Query response cache with TTL
_query_cache: Dict[str, Tuple[str, datetime]] = {}
CACHE_TTL = timedelta(hours=1)


class QueryIntent(BaseModel):
    """Parsed intent from natural language query"""
    target_entity: Optional[str] = None
    target_timepoint: Optional[str] = None
    information_type: str = "general"  # knowledge, relationships, actions, dialog, counterfactual
    context_entities: List[str] = []  # Other entities that matter
    confidence: float = 0.0
    reasoning: str = ""
    # Counterfactual branching fields
    is_counterfactual: bool = False
    intervention_type: Optional[str] = None  # "entity_removal", "entity_modification", "event_cancellation"
    intervention_target: Optional[str] = None
    intervention_description: Optional[str] = None


class QueryInterface:
    """Natural language query interface with lazy resolution elevation"""

    def __init__(self, store: GraphStore, llm_client: LLMClient):
        self.store = store
        self.llm_client = llm_client
        self.resolution_engine = ResolutionEngine(store, llm_client)

    def _get_query_cache_key(self, query: str, query_intent: QueryIntent) -> str:
        """Generate cache key for query based on content and intent"""
        # Create a hash of the query and relevant intent fields
        cache_content = f"{query}|{query_intent.target_entity}|{query_intent.target_timepoint}|{query_intent.information_type}"
        return hashlib.md5(cache_content.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if it exists and hasn't expired"""
        if cache_key in _query_cache:
            response, timestamp = _query_cache[cache_key]
            if datetime.now() - timestamp < CACHE_TTL:
                return response
            else:
                # Expired, remove from cache
                del _query_cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: str) -> None:
        """Cache a response with current timestamp"""
        _query_cache[cache_key] = (response, datetime.now())

    def clear_expired_cache(self) -> int:
        """Remove expired cache entries, return number removed"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in _query_cache.items()
            if now - timestamp >= CACHE_TTL
        ]
        for key in expired_keys:
            del _query_cache[key]
        return len(expired_keys)

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        total_entries = len(_query_cache)
        now = datetime.now()
        valid_entries = sum(1 for _, timestamp in _query_cache.values()
                           if now - timestamp < CACHE_TTL)
        expired_entries = total_entries - valid_entries
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries
        }

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

Return a JSON object with these exact fields:
- target_entity: Which entity is the query about? (use exact entity name or null)
- target_timepoint: Which timepoint does this refer to? (use timepoint_id or null)
- information_type: What type of information? (knowledge/relationships/actions/dialog/general)
- context_entities: Other entities mentioned or relevant (array of strings)
- confidence: How confident are you in this parsing? (0.0-1.0)
- reasoning: Brief explanation of your parsing

Return only valid JSON, no other text."""

        try:
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            # Extract and parse JSON response manually
            content = response["choices"][0]["message"]["content"]
            try:
                data = json.loads(content.strip())
                query_intent = QueryIntent(**data)
            except (json.JSONDecodeError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response as JSON: {e}. Content: {content}")

            self.llm_client.token_count += 500  # Estimate
            self.llm_client.cost += 0.005
            return query_intent
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

        # Scene/atmosphere queries
        elif any(word in query_lower for word in ["atmosphere", "mood", "feeling", "vibe", "environment", "crowd", "scene"]):
            info_type = "atmosphere"
            confidence += 0.3

        # Description/event queries (like "describe the cabinet meeting")
        elif any(word in query_lower for word in ["describe", "what happened", "during", "at the"]):
            info_type = "general"
            confidence += 0.1

        # Counterfactual/what-if queries
        is_counterfactual = False
        intervention_type = None
        intervention_target = None
        intervention_description = None

        counterfactual_keywords = ["what if", "what would happen if", "suppose", "imagine if", "if only"]
        if any(keyword in query_lower for keyword in counterfactual_keywords):
            is_counterfactual = True
            info_type = "counterfactual"
            confidence += 0.3

            # Try to detect intervention type
            if any(word in query_lower for word in ["absent", "missing", "not present", "removed", "was absent"]):
                intervention_type = "entity_removal"
                # For entity removal, the target_entity is usually the one being removed
                if target_entity:
                    intervention_target = target_entity
                    intervention_description = f"Remove {target_entity} from timeline"
                elif context_entities:
                    intervention_target = context_entities[0]
                    intervention_description = f"Remove {intervention_target} from timeline"
            elif any(word in query_lower for word in ["cancel", "prevent", "stop", "avoid"]):
                intervention_type = "event_cancellation"
                intervention_description = "Cancel the target event"
            elif any(word in query_lower for word in ["instead", "changed", "different", "modify"]):
                intervention_type = "entity_modification"
                intervention_description = "Modify entity behavior or state"

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

        intent = QueryIntent(
            target_entity=target_entity,
            target_timepoint=target_timepoint,
            information_type=info_type,
            context_entities=context_entities,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts),
            is_counterfactual=is_counterfactual,
            intervention_type=intervention_type,
            intervention_target=intervention_target,
            intervention_description=intervention_description
        )
        # Store original query for relevance scoring
        intent._original_query = query
        return intent

    def query(self, query_text: str) -> str:
        """Main query method with caching support"""
        # Parse query intent
        query_intent = self.parse_query(query_text)

        # Check cache first
        cache_key = self._get_query_cache_key(query_text, query_intent)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            print(f"  📋 Cache hit for query (TTL: {CACHE_TTL})")
            return cached_response

        # Generate response
        response = self.synthesize_response(query_intent, query_text)

        # Cache the response
        self._cache_response(cache_key, response)
        print(f"  💾 Response cached (key: {cache_key[:8]}...)")

        return response

    def synthesize_response(self, query_intent: QueryIntent, query_text: str = "") -> str:
        """Generate answer from entity states with lazy resolution elevation and attribution"""

        # Handle counterfactual queries first
        if query_intent.is_counterfactual:
            return self._synthesize_counterfactual_response(query_intent, query_text)

        # Handle different query types
        if not query_intent.target_entity:
            # Check if this is a scene/atmosphere query
            if query_intent.information_type in ["atmosphere", "environment", "crowd"] or \
               any(word in getattr(query_intent, '_original_query', '').lower() for word in ["atmosphere", "mood", "scene", "environment", "crowd"]):
                return self._synthesize_scene_response(query_intent)
            # Check if this is an event/timepoint-focused query
            elif query_intent.target_timepoint:
                return self._synthesize_timepoint_response(query_intent)
            # Check if this is a multi-entity relationship query
            elif query_intent.context_entities:
                return self._synthesize_relationship_response(query_intent)
            else:
                return "I couldn't identify which entity you're asking about. Available entities: " + ", ".join(self._get_all_entity_names())

        entity = self.store.get_entity(query_intent.target_entity)
        if not entity:
            # Mechanism 9: On-Demand Entity Generation
            # Check if this might be a missing entity that should be generated
            existing_entities = set(self._get_all_entity_names())
            missing_entity = self.detect_entity_gap(query_text, existing_entities)

            if missing_entity and missing_entity == query_intent.target_entity:
                # Try to generate the entity on demand
                # Find an appropriate timepoint for context
                timepoint = None
                if query_intent.target_timepoint:
                    timepoint = self.store.get_timepoint(query_intent.target_timepoint)
                else:
                    # Use the most recent timepoint as context
                    timepoints = self.store.get_all_timepoints()
                    if timepoints:
                        timepoint = max(timepoints, key=lambda tp: tp.timestamp)

                if timepoint:
                    print(f"  🔍 Entity {query_intent.target_entity} not found, generating on demand...")
                    entity = self.generate_entity_on_demand(query_intent.target_entity, timepoint)
                else:
                    return f"I don't have information about {query_intent.target_entity} and cannot determine appropriate context for generation."
            else:
                return f"I don't have information about {query_intent.target_entity}."

        # Check if entity resolution is sufficient for the query
        required_resolution = self._get_required_resolution(query_intent.information_type)

        # Lazy elevation: if current resolution is too low, elevate it
        if self._resolution_level_value(entity.resolution_level) < self._resolution_level_value(required_resolution):
            success = self._elevate_entity_resolution(entity, required_resolution)
            if success:
                print(f"  Elevated {entity.entity_id} resolution to {required_resolution.value}")

        # Record this query for future resolution decisions and progressive training
        self.resolution_engine.record_query(entity.entity_id)
        entity.query_count += 1  # Increment query count for progressive training
        self.store.save_entity(entity)  # Save the updated query count

        # Determine which tensor type to decompress based on query
        tensor_type = self._get_tensor_type_for_query(query_intent.information_type)

        # Try to load compressed tensor data first (token-efficient)
        compressed_tensor = load_compressed_entity_data(entity, tensor_type)

        # If no tensor found for specific type, try context tensor as fallback
        if compressed_tensor is None and tensor_type != "context":
            compressed_tensor = load_compressed_entity_data(entity, "context")

        knowledge_state = []
        if compressed_tensor is not None:
            # Decompress tensor to get knowledge representation
            knowledge_state = self._tensor_to_knowledge(compressed_tensor, tensor_type, entity)
            print(f"  📦 Used compressed {tensor_type} tensor for {entity.entity_id}")
        else:
            # Fall back to stored knowledge state
            knowledge_state = entity.entity_metadata.get("knowledge_state", [])

        # Get temporally filtered knowledge based on query intent
        temporally_filtered_knowledge = self._filter_knowledge_by_time(knowledge_state, query_intent, entity.entity_id)
        relevant_knowledge = self._filter_relevant_knowledge(temporally_filtered_knowledge, query_intent)

        # Build response with attribution
        response_parts = []

        if relevant_knowledge:
            # Group knowledge by exposure source and timestamp for better attribution
            exposure_events = self.store.get_exposure_events(entity.entity_id)
            source_map = {event.information: (event.source, event.timestamp) for event in exposure_events}

            response_parts.append(f"Based on {entity.entity_id}'s knowledge from the temporal simulation:")

            for i, knowledge in enumerate(relevant_knowledge[:3]):  # Limit to 3 most relevant
                source_info = source_map.get(knowledge, ("personal experience", None))
                source, learned_at = source_info

                response_parts.append(f"• {knowledge}")
                if source != "personal experience" and learned_at:
                    # Format timestamp nicely
                    time_str = learned_at.strftime("%Y-%m-%d")
                    response_parts.append(f"  (learned {time_str} from: {source})")
                elif source != "personal experience":
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

    def _get_tensor_type_for_query(self, information_type: str) -> str:
        """Determine which tensor type to decompress based on query information type"""
        tensor_mapping = {
            "knowledge": "context",      # Knowledge/thoughts -> context tensor
            "actions": "behavior",       # Actions -> behavior tensor
            "relationships": "context",  # Relationships -> context tensor
            "dialog": "context",         # Dialog -> context tensor
            "general": "context"         # General queries -> context tensor
        }
        return tensor_mapping.get(information_type, "context")

    def _tensor_to_knowledge(self, tensor: np.ndarray, tensor_type: str, entity: Entity) -> List[str]:
        """Convert decompressed tensor back to meaningful knowledge representation"""
        if tensor_type == "context":
            return self._interpret_context_tensor(tensor, entity)
        elif tensor_type == "biology":
            return self._interpret_biology_tensor(tensor, entity)
        elif tensor_type == "behavior":
            return self._interpret_behavior_tensor(tensor, entity)
        else:
            return [f"Unknown tensor type {tensor_type}: {tensor[:3]}..."]

    def _interpret_context_tensor(self, tensor: np.ndarray, entity: Entity) -> List[str]:
        """Interpret context tensor as knowledge/information state"""
        knowledge_items = []

        # Context tensor interpretation based on dimensionality and values
        # This is a simplified mapping - in practice, this would use learned semantic mappings

        if len(tensor) >= 10:
            # Assume first dimensions represent different knowledge categories
            categories = [
                "historical_events", "personal_relationships", "professional_experience",
                "cultural_knowledge", "political_views", "religious_beliefs",
                "scientific_understanding", "artistic_interests", "social_connections",
                "personal_memories"
            ]

            for i, (category, value) in enumerate(zip(categories, tensor[:10])):
                if abs(value) > 0.3:  # Significant knowledge in this area
                    intensity = "deep" if value > 0.7 else "moderate" if value > 0.5 else "basic"
                    knowledge_items.append(f"Has {intensity} knowledge of {category.replace('_', ' ')}")

        # Look for patterns in the tensor that might indicate specific knowledge
        tensor_mean = np.mean(tensor)
        tensor_std = np.std(tensor)

        if tensor_std < 0.1:
            knowledge_items.append("Has consistent, stable knowledge across domains")
        elif tensor_std > 0.5:
            knowledge_items.append("Has specialized expertise in specific areas with varying depth")

        # Add entity-specific context if available
        role = entity.entity_metadata.get("role", "").lower()
        if "president" in role and len(tensor) > 5:
            if tensor[0] > 0.5:  # Historical events dimension
                knowledge_items.append("Well-versed in historical precedents and governmental affairs")

        return knowledge_items[:8]  # Limit to most relevant items

    def _interpret_biology_tensor(self, tensor: np.ndarray, entity: Entity) -> List[str]:
        """Interpret biology tensor as physical/health state"""
        biology_facts = []

        if len(tensor) >= 3:
            # Assume tensor format: [age, health_status, energy_level, ...]
            age = entity.entity_metadata.get("age", 50)

            # Age interpretation
            if age < 25:
                biology_facts.append("Young adult in prime physical condition")
            elif age < 45:
                biology_facts.append("Middle-aged with established health patterns")
            elif age < 65:
                biology_facts.append("Experienced adult with some age-related considerations")
            else:
                biology_facts.append("Elderly with significant age-related physical constraints")

            # Health status interpretation (simplified)
            if len(tensor) > 1:
                health_score = tensor[1]  # Assume second dimension is health
                if health_score > 0.7:
                    biology_facts.append("Generally healthy with good physical resilience")
                elif health_score > 0.4:
                    biology_facts.append("Moderate health with some physical limitations")
                else:
                    biology_facts.append("Poor health requiring significant accommodations")

            # Energy level interpretation
            if len(tensor) > 2:
                energy_score = tensor[2]  # Assume third dimension is energy
                if energy_score > 0.7:
                    biology_facts.append("High energy levels supporting active lifestyle")
                elif energy_score > 0.4:
                    biology_facts.append("Moderate energy with normal daily activities")
                else:
                    biology_facts.append("Low energy requiring rest and limited activity")

        # Add role-specific biological constraints
        role = entity.entity_metadata.get("role", "").lower()
        if "soldier" in role or "general" in role:
            biology_facts.append("Military background suggests physical fitness and discipline")
        elif "politician" in role:
            biology_facts.append("Public role may involve stress-related health considerations")

        return biology_facts

    def _interpret_behavior_tensor(self, tensor: np.ndarray, entity: Entity) -> List[str]:
        """Interpret behavior tensor as personality and behavioral patterns"""
        behavior_traits = []

        if len(tensor) >= 5:
            # Assume Big Five personality model: [openness, conscientiousness, extraversion, agreeableness, neuroticism]

            trait_names = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
            trait_descriptions = {
                "openness": ["closed-minded and traditional", "somewhat open to new ideas", "highly open and creative"],
                "conscientiousness": ["disorganized and careless", "moderately organized", "highly disciplined and organized"],
                "extraversion": ["introverted and reserved", "somewhat social", "highly outgoing and energetic"],
                "agreeableness": ["competitive and assertive", "moderately cooperative", "highly compassionate and trusting"],
                "neuroticism": ["emotionally stable", "moderately sensitive", "highly anxious and emotional"]
            }

            for i, (trait, value) in enumerate(zip(trait_names, tensor[:5])):
                if value < 0.3:
                    behavior_traits.append(f"Low {trait}: {trait_descriptions[trait][0]}")
                elif value < 0.7:
                    behavior_traits.append(f"Moderate {trait}: {trait_descriptions[trait][1]}")
                else:
                    behavior_traits.append(f"High {trait}: {trait_descriptions[trait][2]}")

        # Look for behavioral patterns
        if len(tensor) > 5:
            # Additional dimensions might represent decision-making patterns
            risk_taking = tensor[5] if len(tensor) > 5 else 0.5
            if risk_taking > 0.7:
                behavior_traits.append("Risk-tolerant decision maker")
            elif risk_taking < 0.3:
                behavior_traits.append("Risk-averse and cautious")

        # Add role-specific behavioral insights
        role = entity.entity_metadata.get("role", "").lower()
        if "president" in role or "leader" in role:
            behavior_traits.append("Leadership role suggests strong decision-making and social skills")
        elif "general" in role:
            behavior_traits.append("Military command experience indicates discipline and strategic thinking")

        # Add temporal consistency note
        behavior_traits.append("Behavioral patterns show temporal inertia (personality stability over time)")

        return behavior_traits[:6]  # Limit to most relevant traits

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

            # Show LLM response snippets based on resolution level
            if target_resolution.value == "scene":
                print(f"  📝 Scene LLM Response: {population.knowledge_state[0][:200]}..." if population.knowledge_state else "  📝 Scene LLM Response: (no knowledge generated)")
            elif target_resolution.value == "dialog":
                # Show the dialog context being sent to LLM
                dialog_context = f"Entity: {entity.entity_id}, Role: {enhanced_context['entity_role']}, Timepoint: {enhanced_context['timepoint']}, Event: {enhanced_context['event']}"
                print(f"  💬 Dialog LLM Context: {dialog_context[:500]}...")
                if population.knowledge_state:
                    print(f"  💬 Dialog LLM Response: {population.knowledge_state[0][:200]}..." if population.knowledge_state else "  💬 Dialog LLM Response: (no knowledge generated)")

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
        """Filter knowledge items based on semantic relevance to query using LLM scoring"""
        if not knowledge_state:
            return []

        # Reconstruct the original query for relevance scoring
        original_query = getattr(query_intent, '_original_query', None)
        if not original_query:
            # Fallback: reconstruct from intent attributes
            query_parts = []
            if query_intent.target_entity:
                query_parts.append(query_intent.target_entity.replace('_', ' '))
            if query_intent.information_type:
                query_parts.append(query_intent.information_type)
            original_query = " ".join(query_parts)

        # Score each knowledge item using LLM relevance scoring
        scored_knowledge = []
        for knowledge in knowledge_state:
            relevance_score = self.llm_client.score_relevance(original_query, knowledge)
            scored_knowledge.append((knowledge, relevance_score))

        # Sort by relevance score (highest first)
        scored_knowledge.sort(key=lambda x: x[1], reverse=True)

        # Return top knowledge items based on relevance
        # For general queries, return top 3; for specific queries, return top 5 with relevance > 0.3
        if query_intent.information_type == "general":
            return [k for k, s in scored_knowledge[:3]]
        else:
            return [k for k, s in scored_knowledge if s > 0.3][:5]  # Only highly relevant items

    def _filter_knowledge_by_time(self, knowledge_state: List[str], query_intent: QueryIntent, entity_id: str) -> List[str]:
        """Filter knowledge items to only those available at the query timepoint"""
        if not knowledge_state:
            return []

        # Determine query timepoint
        query_timepoint = None
        if query_intent.target_timepoint:
            # Use specified timepoint
            timepoint_obj = self.store.get_timepoint(query_intent.target_timepoint)
            if timepoint_obj:
                query_timepoint = timepoint_obj.timestamp
        else:
            # Use latest timepoint as default (what entity currently knows)
            timepoints = self.store.get_all_timepoints()
            if timepoints:
                query_timepoint = max(tp.timestamp for tp in timepoints)

        if not query_timepoint:
            # Fallback to all knowledge if no timepoint determined
            return knowledge_state

        # Get exposure events to determine when knowledge was learned
        exposure_events = self.store.get_exposure_events(entity_id)

        # Create mapping of knowledge item to when it was learned
        knowledge_timestamps = {}
        for event in exposure_events:
            knowledge_timestamps[event.information] = event.timestamp

        # Filter knowledge to only items learned before or at query timepoint
        filtered_knowledge = []
        for knowledge_item in knowledge_state:
            learned_at = knowledge_timestamps.get(knowledge_item)
            if learned_at and learned_at <= query_timepoint:
                filtered_knowledge.append(knowledge_item)
            elif not learned_at:
                # If no timestamp available, include it (legacy knowledge)
                filtered_knowledge.append(knowledge_item)

        return filtered_knowledge

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
        """Generate response for multi-entity relationship queries using Phase 3 capabilities"""
        if not query_intent.context_entities or len(query_intent.context_entities) < 2:
            return "I need more specific information about which entities you're asking about their relationship."

        # Phase 3: Use comprehensive multi-entity analysis
        entities = query_intent.context_entities
        timeline = []  # Could be populated from available timepoints

        # Get entity objects
        entity_objects = []
        for entity_id in entities:
            entity = self.store.get_entity(entity_id)
            if entity:
                entity_objects.append(entity)

        if not entity_objects:
            return "Could not find the requested entities in the simulation."

        # Analyze relationship trajectories
        relationship_analysis = self._analyze_relationship_trajectories(entities, timeline)

        # Detect contradictions
        contradictions = self._detect_contradictions_in_entities(entity_objects)

        # Check for existing dialogs
        dialogs = self._find_relevant_dialogs(entities)

        # Build comprehensive response
        response_parts = [f"**Relationship Analysis: {', '.join(e.replace('_', ' ').title() for e in entities)}**"]

        # Add relationship trajectory summary
        if relationship_analysis:
            response_parts.append("\n**Relationship Evolution:**")
            for trajectory in relationship_analysis[:3]:  # Limit to most relevant
                trend = trajectory.get('overall_trend', 'unknown')
                entity_a = trajectory.get('entity_a', '').replace('_', ' ').title()
                entity_b = trajectory.get('entity_b', '').replace('_', ' ').title()
                response_parts.append(f"• {entity_a} ↔ {entity_b}: {trend} relationship")

        # Add contradiction analysis
        if contradictions:
            response_parts.append("\n**Identified Conflicts:**")
            for contradiction in contradictions[:3]:
                entity_a = contradiction.get('entity_a', '').replace('_', ' ').title()
                entity_b = contradiction.get('entity_b', '').replace('_', ' ').title()
                topic = contradiction.get('topic', 'unknown topic')
                severity = contradiction.get('severity', 0)
                response_parts.append(f"• {entity_a} and {entity_b} disagree on '{topic}' (severity: {severity:.1f})")

        # Add dialog highlights
        if dialogs:
            response_parts.append("\n**Direct Interactions:**")
            for dialog in dialogs[:2]:  # Limit to most recent
                participants = json.loads(dialog.participants) if isinstance(dialog.participants, str) else dialog.participants
                participant_names = [p.replace('_', ' ').title() for p in participants]
                response_parts.append(f"• Conversation between {', '.join(participant_names)} at {dialog.timepoint_id}")

        # Add entity perspectives
        response_parts.append("\n**Entity Perspectives:**")
        for entity in entity_objects[:3]:  # Limit to avoid overwhelming response
            knowledge = entity.entity_metadata.get("knowledge_state", [])
            relevant_knowledge = []

            # Find knowledge that mentions other entities
            for item in knowledge[:5]:  # Check first 5 knowledge items
                item_lower = item.lower()
                mentions_others = any(
                    other_id.replace('_', ' ').lower() in item_lower
                    for other_id in entities if other_id != entity.entity_id
                )
                if mentions_others:
                    relevant_knowledge.append(item)

            if relevant_knowledge:
                entity_name = entity.entity_id.replace('_', ' ').title()
                response_parts.append(f"• {entity_name}: {relevant_knowledge[0][:100]}...")

        # Add metadata
        entity_list = ', '.join(query_intent.context_entities)
        response_parts.append(f"\n[Phase 3 Multi-Entity Analysis: {entity_list}, Dialogs: {len(dialogs)}, Contradictions: {len(contradictions)}]")

        return "\n".join(response_parts)

    def _synthesize_scene_response(self, query_intent: QueryIntent) -> str:
        """Generate response for scene-level queries (atmosphere, environment, crowd)"""

        # Find timepoint to get scene context
        timepoint = None
        if query_intent.target_timepoint:
            timepoint = self.store.get_timepoint(query_intent.target_timepoint)
        else:
            # Find timepoint by location reference in query
            query_lower = getattr(query_intent, '_original_query', '').lower()
            timepoints = self.store.get_all_timepoints()
            for tp in timepoints:
                if any(loc.lower() in query_lower for loc in ['federal hall', 'hall', tp.event_description.lower()]):
                    timepoint = tp
                    break

        if not timepoint:
            return "I couldn't determine which scene or timepoint you're referring to."

        # Check for scene entities (environment, atmosphere, crowd)
        scene_entities = self._get_scene_entities(timepoint.timepoint_id)

        if not scene_entities['environment']:
            # Create scene entities on demand
            scene_entities = self._create_scene_entities_on_demand(timepoint)

        # Generate response based on query type
        if 'atmosphere' in query_intent.information_type or 'atmosphere' in getattr(query_intent, '_original_query', '').lower():
            return self._describe_atmosphere(scene_entities, timepoint)
        elif 'environment' in query_intent.information_type:
            return self._describe_environment(scene_entities, timepoint)
        elif 'crowd' in query_intent.information_type:
            return self._describe_crowd(scene_entities, timepoint)
        else:
            # General scene description
            return self._describe_scene_overview(scene_entities, timepoint)

    def _get_scene_entities(self, timepoint_id: str) -> Dict[str, Optional[Any]]:
        """Retrieve scene entities for a timepoint"""
        # In a real implementation, this would query the database
        # For now, return None to trigger on-demand creation
        return {
            'environment': None,
            'atmosphere': None,
            'crowd': None
        }

    def _create_scene_entities_on_demand(self, timepoint: Timepoint) -> Dict[str, any]:
        """Create scene entities for a timepoint on demand"""
        from workflows import create_environment_entity, compute_scene_atmosphere, compute_crowd_dynamics

        # Get entities present at this timepoint
        entities = []
        for entity_id in timepoint.entities_present:
            entity = self.store.get_entity(entity_id)
            if entity:
                entities.append(entity)

        # Create environment entity
        environment = create_environment_entity(
            timepoint_id=timepoint.timepoint_id,
            location="Federal Hall",  # Could be extracted from timepoint metadata
            capacity=500,
            temperature=18.0,  # April in Philadelphia
            lighting=0.9,
            weather="clear"
        )

        # Create atmosphere entity
        atmosphere = compute_scene_atmosphere(entities, environment)

        # Create crowd entity
        crowd = compute_crowd_dynamics(entities, environment)

        # In a real implementation, these would be saved to database
        # self.store.save_environment_entity(environment)
        # self.store.save_atmosphere_entity(atmosphere)
        # self.store.save_crowd_entity(crowd)

        return {
            'environment': environment,
            'atmosphere': atmosphere,
            'crowd': crowd
        }

    def _describe_atmosphere(self, scene_entities: Dict, timepoint: Timepoint) -> str:
        """Describe the atmospheric conditions of a scene"""
        atmosphere = scene_entities['atmosphere']
        environment = scene_entities['environment']

        if not atmosphere:
            return "Atmospheric data not available for this scene."

        response_parts = [f"Atmosphere at {environment.location} during {timepoint.event_description.lower()}:"]
        response_parts.append("")

        # Emotional atmosphere
        valence_desc = "positive" if atmosphere.emotional_valence > 0.2 else "negative" if atmosphere.emotional_valence < -0.2 else "neutral"
        arousal_desc = "high energy" if atmosphere.emotional_arousal > 0.6 else "moderate energy" if atmosphere.emotional_arousal > 0.3 else "calm"

        response_parts.append(f"• Emotional tone: {valence_desc} with {arousal_desc}")

        # Tension and formality
        tension_desc = "high tension" if atmosphere.tension_level > 0.7 else "moderate tension" if atmosphere.tension_level > 0.4 else "relaxed"
        formality_desc = "highly formal" if atmosphere.formality_level > 0.8 else "moderately formal" if atmosphere.formality_level > 0.5 else "informal"

        response_parts.append(f"• Social atmosphere: {tension_desc}, {formality_desc}")

        # Cohesion and energy
        cohesion_desc = "strong social bonds" if atmosphere.social_cohesion > 0.7 else "moderate social cohesion" if atmosphere.social_cohesion > 0.4 else "social divisions"
        energy_desc = "energetic and lively" if atmosphere.energy_level > 0.7 else "moderate energy" if atmosphere.energy_level > 0.4 else "subdued"

        response_parts.append(f"• Group dynamics: {cohesion_desc}, overall feeling {energy_desc}")

        # Environmental factors
        if environment:
            temp_desc = "comfortably cool" if environment.ambient_temperature < 20 else "warm"
            light_desc = "brightly lit" if environment.lighting_level > 0.8 else "moderately lit" if environment.lighting_level > 0.5 else "dimly lit"

            response_parts.append(f"• Physical setting: {temp_desc}, {light_desc}")
            if environment.weather:
                response_parts.append(f"• Weather: {environment.weather}")

        response_parts.append(f"\n[Scene atmosphere analysis: {timepoint.timepoint_id}, Confidence: High]")

        return "\n".join(response_parts)

    def _describe_environment(self, scene_entities: Dict, timepoint: Timepoint) -> str:
        """Describe the environmental conditions of a scene"""
        environment = scene_entities['environment']

        if not environment:
            return "Environmental data not available for this scene."

        response_parts = [f"Environment at {environment.location}:"]
        response_parts.append("")

        response_parts.append(f"• Location: {environment.location}")
        response_parts.append(f"• Capacity: {environment.capacity} people")
        response_parts.append(f"• Temperature: {environment.ambient_temperature:.1f}°C")
        response_parts.append(f"• Lighting: {'bright' if environment.lighting_level > 0.7 else 'moderate' if environment.lighting_level > 0.4 else 'dim'}")

        if environment.weather:
            response_parts.append(f"• Weather: {environment.weather}")

        if environment.architectural_style:
            response_parts.append(f"• Architecture: {environment.architectural_style.replace('_', ' ')}")

        if environment.acoustic_properties:
            acoustic_desc = {
                "reverberant": "echoing acoustics typical of large halls",
                "muffled": "absorbing acoustics typical of furnished spaces",
                "open": "open acoustics typical of outdoor spaces",
                "moderate": "balanced acoustics"
            }.get(environment.acoustic_properties, environment.acoustic_properties)

            response_parts.append(f"• Acoustics: {acoustic_desc}")

        response_parts.append(f"\n[Environmental analysis: {timepoint.timepoint_id}]")

        return "\n".join(response_parts)

    def _describe_crowd(self, scene_entities: Dict, timepoint: Timepoint) -> str:
        """Describe the crowd composition and dynamics"""
        crowd = scene_entities['crowd']

        if not crowd:
            return "Crowd data not available for this scene."

        response_parts = [f"Crowd at {timepoint.event_description.lower()}:"]
        response_parts.append("")

        response_parts.append(f"• Size: {crowd.size} people present")
        density_desc = "very crowded" if crowd.density > 0.8 else "crowded" if crowd.density > 0.6 else "moderately full" if crowd.density > 0.4 else "sparse"
        response_parts.append(f"• Density: {density_desc} ({crowd.density:.1f})")

        # Mood distribution
        try:
            mood_dist = json.loads(crowd.mood_distribution)
            if mood_dist:
                mood_parts = []
                for mood, percentage in sorted(mood_dist.items(), key=lambda x: x[1], reverse=True):
                    mood_parts.append(f"{mood} ({percentage:.1%})")
                response_parts.append(f"• Mood distribution: {', '.join(mood_parts)}")
        except (json.JSONDecodeError, TypeError):
            response_parts.append("• Mood distribution: analysis unavailable")

        response_parts.append(f"• Movement pattern: {crowd.movement_pattern}")
        response_parts.append(f"• Noise level: {'loud' if crowd.noise_level > 0.7 else 'moderate' if crowd.noise_level > 0.4 else 'quiet'}")

        # Demographic composition
        try:
            demo_comp = json.loads(crowd.demographic_composition)
            if demo_comp and 'gender_balance' in demo_comp:
                gender_balance = demo_comp['gender_balance']
                male_pct = gender_balance.get('male', 0)
                female_pct = gender_balance.get('female', 0)
                response_parts.append(f"• Gender balance: {male_pct:.1%} male, {female_pct:.1%} female")
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

        response_parts.append(f"\n[Crowd analysis: {timepoint.timepoint_id}]")

        return "\n".join(response_parts)

    def _describe_scene_overview(self, scene_entities: Dict, timepoint: Timepoint) -> str:
        """Provide overview of the entire scene"""
        response_parts = [f"Scene overview: {timepoint.event_description}"]
        response_parts.append("")

        # Environment summary
        if scene_entities['environment']:
            env = scene_entities['environment']
            response_parts.append(f"📍 Location: {env.location} ({env.architectural_style.replace('_', ' ')})")
            response_parts.append(f"🌡️ Conditions: {env.ambient_temperature:.1f}°C, {'bright' if env.lighting_level > 0.7 else 'moderate'} lighting")

        # Atmosphere summary
        if scene_entities['atmosphere']:
            atm = scene_entities['atmosphere']
            valence_icon = "😊" if atm.emotional_valence > 0.2 else "😔" if atm.emotional_valence < -0.2 else "😐"
            energy_icon = "⚡" if atm.energy_level > 0.7 else "🔋" if atm.energy_level > 0.4 else "🪫"

            response_parts.append(f"{valence_icon} Atmosphere: {'positive' if atm.emotional_valence > 0.2 else 'negative' if atm.emotional_valence < -0.2 else 'neutral'} mood, {energy_icon} {'high' if atm.energy_level > 0.7 else 'moderate' if atm.energy_level > 0.4 else 'low'} energy")

        # Crowd summary
        if scene_entities['crowd']:
            crowd = scene_entities['crowd']
            response_parts.append(f"👥 Crowd: {crowd.size} people, {crowd.movement_pattern} movement")

        response_parts.append(f"\n[Scene overview: {timepoint.timepoint_id}]")

        return "\n".join(response_parts)

    # ============================================================================
    # Mechanism 9: On-Demand Entity Generation
    # ============================================================================

    def extract_entity_names(self, query: str) -> Set[str]:
        """Extract potential entity names from natural language query using regex patterns"""
        entity_names = set()

        # Pattern for numbered entities like "attendee #47", "person #12", "member #3"
        numbered_patterns = [
            r'attendee\s*#?\s*(\d+)',
            r'person\s*#?\s*(\d+)',
            r'member\s*#?\s*(\d+)',
            r'participant\s*#?\s*(\d+)',
            r'guest\s*#?\s*(\d+)',
            r'visitor\s*#?\s*(\d+)',
            r'spectator\s*#?\s*(\d+)'
        ]

        for pattern in numbered_patterns:
            matches = re.findall(pattern, query.lower())
            for match in matches:
                entity_names.add(f"attendee_{match}")

        # Pattern for named entities with numbers like "attendee47", "person12"
        named_numbered_patterns = [
            r'\b(attendee)(\d+)\b',
            r'\b(person)(\d+)\b',
            r'\b(member)(\d+)\b',
            r'\b(participant)(\d+)\b'
        ]

        for pattern in named_numbered_patterns:
            matches = re.findall(pattern, query.lower())
            for base_name, number in matches:
                entity_names.add(f"{base_name}_{number}")

        # Pattern for general entity references with numbers
        general_numbered = r'\b(\w+)\s*#?\s*(\d+)\b'
        matches = re.findall(general_numbered, query.lower())
        for base_name, number in matches:
            # Only include if it looks like a numbered entity reference
            if base_name in ['attendee', 'person', 'member', 'participant', 'guest', 'visitor', 'spectator']:
                entity_names.add(f"{base_name}_{number}")

        return entity_names

    def detect_entity_gap(self, query: str, existing_entities: Set[str]) -> Optional[str]:
        """Parse query for entity mentions and return first missing entity"""
        entities_mentioned = self.extract_entity_names(query)
        missing = entities_mentioned - existing_entities
        return missing.pop() if missing else None

    def generate_entity_on_demand(self, entity_id: str, timepoint: Timepoint) -> Entity:
        """Create plausible entity matching query context dynamically"""
        context = {
            "timepoint": timepoint.event_description,
            "entities_present": timepoint.entities_present,
            "role": self._infer_role_from_context(entity_id, timepoint)
        }

        # Use LLM to generate entity data
        prompt = f"""Generate a historical entity for the following context:

Timepoint: {timepoint.timestamp.strftime('%Y-%m-%d %H:%M')}
Event: {context['timepoint']}
Entities Present: {', '.join(context['entities_present'])}
Inferred Role: {context['role']}
Entity ID: {entity_id}

Create a plausible historical figure who would be present at this event. Return a JSON object with:
- name: Full name of the entity
- age: Approximate age (integer)
- role: Historical role or occupation
- background: Brief background (2-3 sentences)
- personality: Key personality traits (2-3 traits)
- motivations: What they hope to achieve at this event
- knowledge_state: List of 3-5 facts they would know
- relationship_notes: How they relate to other entities present

Return only valid JSON."""

        try:
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Some creativity for plausible generation
                max_tokens=800
            )

            content = response["choices"][0]["message"]["content"]
            entity_data = json.loads(content.strip())

            # Create entity with generated data
            entity = Entity(
                entity_id=entity_id,
                entity_type="person",
                resolution_level=ResolutionLevel.TENSOR_ONLY,
                entity_metadata={
                    "name": entity_data.get("name", entity_id.replace("_", " ").title()),
                    "age": entity_data.get("age", 35),
                    "role": entity_data.get("role", context["role"]),
                    "background": entity_data.get("background", "Generated historical figure"),
                    "personality": entity_data.get("personality", ["unknown"]),
                    "motivations": entity_data.get("motivations", "Attend event"),
                    "knowledge_state": entity_data.get("knowledge_state", ["Generated knowledge"]),
                    "relationship_notes": entity_data.get("relationship_notes", "New attendee")
                }
            )

            # Set temporal span
            entity.temporal_span_start = timepoint.timestamp
            entity.temporal_span_end = timepoint.timestamp

            # Initialize physical and cognitive tensors
            from schemas import PhysicalTensor, CognitiveTensor
            entity.physical_tensor = PhysicalTensor(
                age=entity_data.get("age", 35),
                pain_level=0.0,
                fever=36.5
            )
            entity.cognitive_tensor = CognitiveTensor(
                knowledge_state=entity_data.get("knowledge_state", [])
            )

            # Save to database
            self.store.save_entity(entity)

            print(f"  🆕 Generated new entity: {entity_id} ({context['role']})")
            self.llm_client.token_count += 800
            self.llm_client.cost += 0.008

            return entity

        except Exception as e:
            print(f"Failed to generate entity {entity_id}: {e}")
            # Fallback: create minimal entity
            entity = Entity(
                entity_id=entity_id,
                entity_type="person",
                resolution_level=ResolutionLevel.TENSOR_ONLY,
                entity_metadata={
                    "role": context["role"],
                    "knowledge_state": [f"Present at {timepoint.event_description}"]
                }
            )
            entity.temporal_span_start = timepoint.timestamp
            entity.temporal_span_end = timepoint.timestamp
            self.store.save_entity(entity)
            return entity

    def _infer_role_from_context(self, entity_id: str, timepoint: Timepoint) -> str:
        """Infer likely role for an entity based on timepoint context"""
        event_lower = timepoint.event_description.lower()

        # Check for numbered attendees
        if entity_id.startswith("attendee_"):
            if "inauguration" in event_lower:
                return "ceremony attendee"
            elif "meeting" in event_lower or "conference" in event_lower:
                return "meeting participant"
            elif "dinner" in event_lower or "banquet" in event_lower:
                return "dinner guest"
            else:
                return "event attendee"

        # Default fallback
        return "historical figure"

    def _get_all_entity_names(self) -> List[str]:
        """Get list of all entity IDs from database"""
        from sqlmodel import Session, select
        from schemas import Entity

        with Session(self.store.engine) as session:
            entities = session.exec(select(Entity)).all()
            return [entity.entity_id for entity in entities]

    # ============================================================================
    # Phase 3: Multi-Entity Analysis Helper Methods
    # ============================================================================

    def _analyze_relationship_trajectories(self, entity_ids: List[str], timeline: List[Dict]) -> List[Dict]:
        """Analyze relationship trajectories between entities"""
        trajectories = []

        # Analyze relationships between all pairs
        for i, entity_a in enumerate(entity_ids):
            for entity_b in entity_ids[i+1:]:
                trajectory = self.store.get_relationship_trajectory_between(entity_a, entity_b)
                if trajectory:
                    trajectory_data = {
                        "entity_a": trajectory.entity_a,
                        "entity_b": trajectory.entity_b,
                        "overall_trend": trajectory.overall_trend,
                        "key_events": trajectory.key_events
                    }
                    trajectories.append(trajectory_data)

        return trajectories

    def _detect_contradictions_in_entities(self, entities: List[Entity]) -> List[Dict]:
        """Detect contradictions between entity knowledge/beliefs"""
        from workflows import detect_contradictions

        # Get current timepoint for contradiction detection
        timepoints = self.store.get_all_timepoints()
        current_tp = timepoints[-1] if timepoints else None

        if not current_tp:
            return []

        contradictions = detect_contradictions(entities, current_tp, self.store)
        return [
            {
                "entity_a": c.entity_a,
                "entity_b": c.entity_b,
                "topic": c.topic,
                "severity": c.severity,
                "context": c.context
            }
            for c in contradictions
        ]

    def _find_relevant_dialogs(self, entity_ids: List[str]) -> List[Dict]:
        """Find dialogs involving the specified entities"""
        dialogs = self.store.get_dialogs_for_entities(entity_ids)

        # Convert to dict format for easier handling
        dialog_list = []
        for dialog in dialogs:
            dialog_list.append({
                "dialog_id": dialog.dialog_id,
                "timepoint_id": dialog.timepoint_id,
                "participants": dialog.participants,
                "information_transfer_count": dialog.information_transfer_count
            })

        return dialog_list

    def _synthesize_counterfactual_response(self, query_intent: QueryIntent, query_text: str) -> str:
        """Generate response for counterfactual/what-if queries using branching"""
        from schemas import Intervention
        from workflows import create_counterfactual_branch, compare_timelines

        try:
            # Get the baseline timeline
            baseline_timeline = self.store.get_timeline("main_timeline")  # Assuming main timeline exists
            if not baseline_timeline:
                # Create a default timeline from available timepoints
                timepoints = self.store.get_all_timepoints()
                if not timepoints:
                    return "No timeline data available for counterfactual analysis."

                baseline_timeline = {
                    "timeline_id": "main_timeline",
                    "timepoints": sorted(timepoints, key=lambda tp: tp.timestamp)
                }

            # Find intervention point (use target timepoint or earliest timepoint)
            intervention_point = query_intent.target_timepoint
            if not intervention_point and baseline_timeline["timepoints"]:
                intervention_point = baseline_timeline["timepoints"][0].timepoint_id

            if not intervention_point:
                return "Cannot determine intervention point for counterfactual analysis."

            # Create intervention based on detected type
            intervention = None
            if query_intent.intervention_type == "entity_removal" and query_intent.intervention_target:
                intervention = Intervention(
                    type="entity_removal",
                    target=query_intent.intervention_target,
                    parameters={}
                )
            elif query_intent.intervention_type == "entity_modification":
                # For now, create a simple modification
                intervention = Intervention(
                    type="entity_modification",
                    target=query_intent.intervention_target or query_intent.target_entity,
                    parameters={"behavior_adjustment": "more_conservative"}
                )
            elif query_intent.intervention_type == "event_cancellation":
                intervention = Intervention(
                    type="event_cancellation",
                    target=intervention_point,
                    parameters={}
                )
            else:
                # Default to entity removal if we can detect one
                intervention = Intervention(
                    type="entity_removal",
                    target=query_intent.context_entities[0] if query_intent.context_entities else "unknown_entity",
                    parameters={}
                )

            # Create counterfactual branch
            counterfactual_timeline = create_counterfactual_branch(
                baseline_timeline, intervention_point, intervention, self.store
            )

            # Compare timelines
            comparison = compare_timelines(baseline_timeline, counterfactual_timeline)

            # Generate response
            response_parts = [f"Counterfactual Analysis: {query_text}"]
            response_parts.append("")

            if intervention:
                response_parts.append(f"Intervention: {intervention.type} on {intervention.target}")
                if query_intent.intervention_description:
                    response_parts.append(f"Details: {query_intent.intervention_description}")

            response_parts.append("")
            response_parts.append("Key Differences:")

            if "entity_knowledge_delta" in comparison:
                knowledge_changes = comparison["entity_knowledge_delta"]
                if knowledge_changes:
                    response_parts.append(f"• Knowledge changes: {len(knowledge_changes)} items affected")
                else:
                    response_parts.append("• Knowledge: No significant changes")

            if "relationship_changes" in comparison:
                rel_changes = comparison["relationship_changes"]
                if rel_changes:
                    response_parts.append(f"• Relationships: {len(rel_changes)} relationships affected")
                else:
                    response_parts.append("• Relationships: No significant changes")

            if "event_outcomes" in comparison:
                event_changes = comparison["event_outcomes"]
                if event_changes:
                    response_parts.append(f"• Events: {len(event_changes)} event outcomes changed")
                else:
                    response_parts.append("• Events: No significant changes")

            response_parts.append("")
            response_parts.append("[Counterfactual analysis completed. This is a simulated branching scenario.]")

            return "\n".join(response_parts)

        except Exception as e:
            return f"Counterfactual analysis failed: {str(e)}. The branching system may need further integration."
