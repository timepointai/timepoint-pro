# ============================================================================
# query_interface.py - Natural language query interface with lazy resolution elevation
# ============================================================================
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
import hashlib
from schemas import Entity, Timepoint, ResolutionLevel
from storage import GraphStore
from llm import LLMClient
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
    information_type: str = "general"  # knowledge, relationships, actions, dialog
    context_entities: List[str] = []  # Other entities that matter
    confidence: float = 0.0
    reasoning: str = ""


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

        intent = QueryIntent(
            target_entity=target_entity,
            target_timepoint=target_timepoint,
            information_type=info_type,
            context_entities=context_entities,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts)
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
        response = self.synthesize_response(query_intent)

        # Cache the response
        self._cache_response(cache_key, response)
        print(f"  💾 Response cached (key: {cache_key[:8]}...)")

        return response

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
        """Generate response for multi-entity relationship queries (e.g., 'How did Hamilton and Jefferson interact?')"""
        if not query_intent.context_entities or len(query_intent.context_entities) < 2:
            return "I need more specific information about which entities you're asking about their relationship."

        # For multi-entity queries, analyze relationships from all mentioned entities
        entity_knowledge = {}
        relevant_interactions = []

        # Collect knowledge from all mentioned entities
        for entity_id in query_intent.context_entities:
            entity = self.store.get_entity(entity_id)
            if entity:
                knowledge_state = entity.entity_metadata.get("knowledge_state", [])
                entity_knowledge[entity_id] = knowledge_state

                # Look for knowledge that mentions other entities in the query
                for knowledge in knowledge_state:
                    knowledge_lower = knowledge.lower()
                    # Check if this knowledge mentions other entities from the context
                    mentions_others = False
                    mentioned_entities = []
                    for other_entity_id in query_intent.context_entities:
                        if other_entity_id != entity_id:
                            other_name = other_entity_id.replace('_', ' ')
                            if other_name.lower() in knowledge_lower:
                                mentions_others = True
                                mentioned_entities.append(other_entity_id)
                                break

                    if mentions_others:
                        relevant_interactions.append({
                            'knowledge': knowledge,
                            'source_entity': entity_id,
                            'mentioned_entities': mentioned_entities
                        })

        # Build response showing interactions from multiple perspectives
        response_parts = ["Based on the temporal simulation's knowledge of interactions between these entities:"]

        if relevant_interactions:
            # Group by source entity and show diverse perspectives
            shown_knowledge = set()
            for interaction in relevant_interactions[:5]:  # Limit to 5 most relevant
                if interaction['knowledge'] not in shown_knowledge:
                    source_name = interaction['source_entity'].replace('_', ' ').title()
                    response_parts.append(f"• {source_name}'s perspective: {interaction['knowledge']}")
                    shown_knowledge.add(interaction['knowledge'])
        else:
            # If no direct interactions found, show general relationship context
            entity_names = [eid.replace('_', ' ').title() for eid in query_intent.context_entities]
            response_parts.append(f"• The simulation shows {', '.join(entity_names)} were contemporaries during the founding era, though specific interaction details are limited in the current temporal context.")

        # Add metadata about the relationship analysis
        entity_list = ', '.join(query_intent.context_entities)
        response_parts.append(f"\n[Multi-entity relationship analysis: {entity_list}, Confidence: {query_intent.confidence:.1f}]")

        return "\n".join(response_parts)

    def _get_all_entity_names(self) -> List[str]:
        """Get list of all entity IDs from database"""
        from sqlmodel import Session, select
        from schemas import Entity

        with Session(self.store.engine) as session:
            entities = session.exec(select(Entity)).all()
            return [entity.entity_id for entity in entities]
