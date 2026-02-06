# ============================================================================
# orchestrator.py - Scene-to-Specification Compiler (OrchestratorAgent)
# ============================================================================
"""
OrchestratorAgent: Natural language event description → complete scene specification

Takes high-level descriptions like "simulate the constitutional convention" and
generates the full specification needed by existing workflows:
- Entity roster with role-based resolution targeting
- Timepoint sequence with causal relationships
- Relationship graph (social network)
- Initial knowledge seeding from historical context

Architecture:
    SceneParser → KnowledgeSeeder → RelationshipExtractor → ResolutionAssigner
    → Feed to create_entity_training_workflow() and TemporalAgent
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import time
import warnings
import networkx as nx

from schemas import (
    Entity, Timepoint, ResolutionLevel, TemporalMode,
    ExposureEvent, CognitiveTensor
)
from llm import LLMClient
from schemas import EntityPopulation  # Canonical location (breaks circular dep)
from storage import GraphStore
from workflows import TemporalAgent, create_entity_training_workflow
from metadata.tracking import track_mechanism


# ============================================================================
# Helper Functions
# ============================================================================

def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO datetime string, handling 'Z' UTC suffix.

    Python 3.10's datetime.fromisoformat() doesn't accept 'Z' suffix.
    This helper converts 'Z' to '+00:00' for compatibility.

    Args:
        iso_string: ISO 8601 datetime string (e.g., "2023-03-01T00:00:00Z")

    Returns:
        datetime object

    Examples:
        >>> parse_iso_datetime("2023-03-01T00:00:00Z")
        datetime(2023, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
        >>> parse_iso_datetime("2023-03-01T00:00:00")
        datetime(2023, 3, 1, 0, 0, 0)
    """
    # Handle 'Z' suffix (UTC timezone indicator)
    if iso_string.endswith('Z'):
        # Replace 'Z' with '+00:00' for fromisoformat compatibility
        iso_string = iso_string[:-1] + '+00:00'

    return datetime.fromisoformat(iso_string)


# ============================================================================
# Structured Output Schemas for LLM Responses
# ============================================================================

class EntityRosterItem(BaseModel):
    """Single entity in a scene"""
    entity_id: str
    entity_type: str = "human"
    role: str  # "primary", "secondary", "background", "environment"
    description: str
    initial_knowledge: List[str] = []
    relationships: Dict[str, str] = {}  # entity_id -> relationship_type


class TimepointSpec(BaseModel):
    """Single timepoint specification"""
    timepoint_id: str
    timestamp: str  # ISO format datetime
    event_description: str
    entities_present: List[str]
    importance: float = 0.5  # 0.0-1.0
    causal_parent: Optional[str] = None


class SceneSpecification(BaseModel):
    """Complete scene specification from natural language"""
    scene_title: str
    scene_description: str
    temporal_mode: str = "pearl"
    temporal_scope: Dict[str, str]  # start_date, end_date, location
    entities: List[EntityRosterItem]
    timepoints: List[TimepointSpec]
    global_context: str


# ============================================================================
# Component 1: Scene Parser
# ============================================================================

class SceneParser:
    """
    Parse natural language event description into structured specification.

    Uses LLM to decompose high-level prompt into:
    - Temporal scope (when, where, how long)
    - Entity roster (who, what roles)
    - Event sequence (key moments)
    - Appropriate temporal mode
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def parse(self, event_description: str, context: Optional[Dict] = None) -> SceneSpecification:
        """
        Parse natural language description into scene specification.

        Args:
            event_description: Natural language like "simulate the constitutional convention"
            context: Optional additional context (preferred temporal mode, etc.)

        Returns:
            SceneSpecification with entities, timepoints, relationships
        """
        context = context or {}
        max_entities = context.get("max_entities", 20)
        max_timepoints = context.get("max_timepoints", 10)

        # Decide: Single-pass or chunked generation?
        if self._should_use_chunked_generation(max_entities, max_timepoints):
            # Use multi-pass chunked generation for large requests
            return self._generate_chunked(event_description, context, max_entities, max_timepoints)
        else:
            # Use single-pass generation for smaller requests
            prompt = self._build_parsing_prompt(event_description, context)
            # Pass context for auto-scaling token limits and model selection
            response = self._call_llm_structured(prompt, SceneSpecification, context)
            return response

    def _build_parsing_prompt(self, event_description: str, context: Dict) -> str:
        """Build prompt for scene parsing"""
        preferred_mode = context.get("temporal_mode", "pearl")
        max_entities = context.get("max_entities", 20)
        max_timepoints = context.get("max_timepoints", 10)

        # Check if this is a forced requirement (MAX mode)
        require_exact = context.get("require_exact_counts", False)

        if require_exact:
            entity_instruction = f"**Entities** (REQUIRED: exactly {max_entities}): You MUST generate exactly {max_entities} entities. This is a hard requirement. List of people, objects, places, concepts involved"
            timepoint_instruction = f"**Timepoints** (REQUIRED: exactly {max_timepoints}): You MUST generate exactly {max_timepoints} timepoints. This is a hard requirement. Key moments in the event sequence"
        else:
            entity_instruction = f"**Entities** (max {max_entities}): List of people, objects, places involved"
            timepoint_instruction = f"**Timepoints** (max {max_timepoints}): Key moments in the event sequence"

        prompt = f"""You are a historical scene analyzer. Parse this event description into a structured simulation specification.

Event Description: {event_description}

Generate a complete scene specification with these components:

1. **Scene Title**: Short descriptive title
2. **Scene Description**: 2-3 sentence overview
3. **Temporal Mode**: Choose from: pearl (standard causality), directorial (narrative focus), branching (what-if), cyclical (prophecy/loops), portal (backward from endpoint)
   Preferred mode: {preferred_mode}
4. **Temporal Scope**:
   - start_date: ISO datetime when events begin
   - end_date: ISO datetime when events conclude
   - location: Geographic location description
5. {entity_instruction}
   For each entity provide:
   - entity_id: Unique identifier (lowercase, no spaces, e.g., "james_madison")
   - entity_type: Type (human, animal, building, object, abstract)
   - role: Importance level (primary, secondary, background, environment)
   - description: Brief description (1 sentence)
   - initial_knowledge: List of 3-8 facts this entity knows at start
   - relationships: Dict mapping other entity_ids to relationship types (e.g., "ally", "rival", "mentor")
6. {timepoint_instruction}
   For each timepoint provide:
   - timepoint_id: Unique identifier (e.g., "tp_001_opening")
   - timestamp: ISO datetime
   - event_description: What happens at this moment
   - entities_present: List of entity_ids present
   - importance: Float 0.0-1.0 (how pivotal this moment is)
   - causal_parent: Previous timepoint_id (null for first timepoint)
7. **Global Context**: Additional context about the historical period, cultural norms, constraints

Return ONLY valid JSON matching this schema. No other text.

Schema:
{{
  "scene_title": "string",
  "scene_description": "string",
  "temporal_mode": "pearl|directorial|branching|cyclical|portal",
  "temporal_scope": {{"start_date": "ISO datetime", "end_date": "ISO datetime", "location": "string"}},
  "entities": [
    {{
      "entity_id": "string",
      "entity_type": "string",
      "role": "primary|secondary|background|environment",
      "description": "string",
      "initial_knowledge": ["string", ...],
      "relationships": {{"entity_id": "relationship_type", ...}}
    }}
  ],
  "timepoints": [
    {{
      "timepoint_id": "string",
      "timestamp": "ISO datetime",
      "event_description": "string",
      "entities_present": ["entity_id", ...],
      "importance": 0.5,
      "causal_parent": "string or null"
    }}
  ],
  "global_context": "string"
}}"""

        return prompt

    def _call_llm_structured(self, prompt: str, response_model: type, context: Optional[Dict] = None) -> Any:
        """Call LLM and parse structured response - REQUIRES REAL LLM"""
        import os

        # No dry_run mode - always use real LLM
        # Real LLM integration required: Set LLM_SERVICE_ENABLED=true and provide OPENROUTER_API_KEY
        context = context or {}
        max_entities = context.get("max_entities", 20)
        max_timepoints = context.get("max_timepoints", 10)

        try:
            # Use LLMClient's generate_structured method (proper API)
            # For very large scenarios (100+ entities, 100+ timepoints), use Llama 405B with 100k tokens
            # For medium scenarios (20-100 entities, 20-100 timepoints), use Llama 70B with 16k tokens
            # Estimate: ~50 tokens per entity + ~100 tokens per timepoint + ~1000 overhead
            # January 2026: Increased per-entity and per-timepoint estimates for complex scenes
            estimated_tokens = (max_entities * 150) + (max_timepoints * 200) + 2000

            # January 2026: Minimum 8000 tokens for any scene (complex schemas need space)
            estimated_tokens = max(estimated_tokens, 8000)

            # Check if user specified a model override (--free, --model flags)
            model_override = os.getenv("TIMEPOINT_MODEL_OVERRIDE")

            if model_override:
                # User specified a model - respect it, don't hardcode
                model = None  # Let LLMClient use its configured default_model
                max_output_tokens = min(int(estimated_tokens * 2.0), 42000)
                print(f"   ✅ Using override model: {model_override} with {max_output_tokens:,} token limit")
            elif estimated_tokens > 50000:
                # No override + ultra-large scenario - use Llama 405B with extended token limit
                model = "meta-llama/llama-3.1-405b-instruct"
                max_output_tokens = min(int(estimated_tokens * 1.5), 100000)  # 1.5x safety margin, cap at 100k
                print(f"   🚀 Ultra-large scenario detected: Using Llama 405B with {max_output_tokens:,} token limit")
                print(f"   📊 Estimated: {max_entities} entities × {max_timepoints} timepoints = ~{estimated_tokens:,} tokens")
            else:
                # No override + standard/large scenario - use Llama 4 Scout (327K context)
                model = None  # Use default (Scout)
                max_output_tokens = min(int(estimated_tokens * 2.0), 42000)  # 2x safety margin, cap at 42k
                print(f"   ✅ Standard scenario: Using Llama 4 Scout with {max_output_tokens:,} token limit")

            result = self.llm.generate_structured(
                prompt=prompt,
                response_model=response_model,
                model=model,
                temperature=0.3,  # Lower temperature for structured output
                max_tokens=max_output_tokens
            )

            return result

        except Exception as e:
            # DO NOT fall back to mocks - fail fast with clear, context-specific error
            error_str = str(e).lower()

            # Provide context-specific error messages based on error type
            if "timeout" in error_str or "timed out" in error_str:
                raise RuntimeError(
                    f"Scene parsing failed: {e}\n\n"
                    "The API request timed out. This can happen when:\n"
                    "  • OpenRouter is experiencing high load\n"
                    "  • The request is too large/complex for the model to complete in time\n"
                    "  • Network connectivity issues\n\n"
                    "Solutions:\n"
                    "  • Try again (API may be less busy)\n"
                    "  • Reduce scale (fewer entities/timepoints)\n"
                    "  • Use a faster model (though less capable)"
                ) from e

            elif "json" in error_str or "parse" in error_str or "parsing" in error_str:
                raise RuntimeError(
                    f"Scene parsing failed: {e}\n\n"
                    "Failed to parse LLM response as valid JSON. This usually means:\n"
                    "  • The response was truncated (model hit token limit)\n"
                    "  • The JSON structure is incomplete or malformed\n"
                    "  • The requested scale is too large for the model\n\n"
                    "Solutions:\n"
                    "  • Reduce scale (fewer entities/timepoints)\n"
                    "  • Check logs/llm_calls/*.jsonl for the actual response\n"
                    "  • For very large scales, use standard mode instead of MAX mode"
                ) from e

            elif "validation" in error_str or "field required" in error_str or "pydantic" in error_str:
                raise RuntimeError(
                    f"Scene parsing failed: {e}\n\n"
                    "Response validation failed (schema mismatch). This usually means:\n"
                    "  • LLM didn't generate required fields\n"
                    "  • Field types don't match expected schema\n"
                    "  • Response structure is incorrect\n\n"
                    "Solutions:\n"
                    "  • Check logs/llm_calls/*.jsonl for the actual response\n"
                    "  • Try again (LLM may generate valid response next time)\n"
                    "  • Report issue if consistently failing"
                ) from e

            else:
                # Generic fallback for other errors
                raise RuntimeError(
                    f"Scene parsing failed: {e}\n\n"
                    "An unexpected error occurred during scene generation.\n"
                    "Check logs/llm_calls/*.jsonl for details."
                ) from e

    def _should_use_chunked_generation(self, max_entities: int, max_timepoints: int) -> bool:
        """
        Determine if request is too large for single-pass generation.

        Thresholds:
        - >40 entities OR >80 timepoints: Use chunking
        - Estimated >12K tokens: Use chunking
        """
        estimated_tokens = (max_entities * 50) + (max_timepoints * 100) + 1000
        return max_entities > 40 or max_timepoints > 80 or estimated_tokens > 12000

    def _generate_chunked(
        self,
        event_description: str,
        context: Dict,
        max_entities: int,
        max_timepoints: int
    ) -> SceneSpecification:
        """
        Multi-pass chunked generation for very large scenes.

        Pass 1: Generate entity roster (names, roles, types only)
        Pass 2: Generate timepoint skeleton (ids, timestamps, causal chain)
        Pass 3: Fill entity details in batches (knowledge, relationships)
        Pass 4: Fill timepoint details in batches (descriptions, participants)

        This allows generating 124×200 scenes that would fail in one call.
        """
        print("\n🔄 CHUNKED GENERATION MODE")
        print(f"   Request: {max_entities} entities × {max_timepoints} timepoints")
        print(f"   Strategy: Multi-pass hierarchical generation")
        print()

        # Pass 1: Generate entity roster (lightweight)
        print("📋 Pass 1/4: Generating entity roster...")
        entity_roster = self._generate_entity_roster(event_description, context, max_entities)
        print(f"   ✓ Generated {len(entity_roster)} entities")

        # Pass 2: Generate timepoint skeleton
        print("\n⏰ Pass 2/4: Generating timepoint skeleton...")
        timepoint_skeleton = self._generate_timepoint_skeleton(event_description, context, max_timepoints, entity_roster)
        print(f"   ✓ Generated {len(timepoint_skeleton)} timepoints")

        # Pass 3: Fill entity details in batches
        print("\n👥 Pass 3/4: Filling entity details...")
        filled_entities = self._fill_entity_details(event_description, entity_roster, timepoint_skeleton, context)
        print(f"   ✓ Filled details for {len(filled_entities)} entities")

        # Pass 4: Fill timepoint details in batches
        print("\n📝 Pass 4/4: Filling timepoint details...")
        filled_timepoints = self._fill_timepoint_details(event_description, timepoint_skeleton, filled_entities, context)
        print(f"   ✓ Filled details for {len(filled_timepoints)} timepoints")

        # Extract temporal scope from context or use defaults
        preferred_mode = context.get("temporal_mode", "pearl")
        temporal_scope = context.get("temporal_scope", {
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-12-31T23:59:59",
            "location": "Unknown"
        })

        # Assemble final SceneSpecification
        scene_spec = SceneSpecification(
            scene_title=context.get("scene_title", f"Large Scene: {event_description[:50]}..."),
            scene_description=event_description,
            temporal_mode=preferred_mode,
            temporal_scope=temporal_scope,
            entities=filled_entities,
            timepoints=filled_timepoints,
            global_context=f"Generated via chunked multi-pass generation. {event_description}"
        )

        print("\n✅ Chunked generation complete!")
        return scene_spec

    def _generate_entity_roster(
        self,
        event_description: str,
        context: Dict,
        count: int
    ) -> List[EntityRosterItem]:
        """Pass 1: Generate entity roster with minimal details

        If entity_config.profiles is specified, load predefined profiles from JSON files.
        Otherwise, generate entities via LLM as before.
        """
        from pathlib import Path

        # Add absolute timeout to prevent infinite loops
        start_time = time.time()
        absolute_timeout = 300  # 5 minutes max for entity roster generation

        # Check if profiles are specified in context
        entity_config = context.get("entity_config", {})
        profile_paths = entity_config.get("profiles", [])

        loaded_entities = []

        # Load predefined profiles if specified
        if profile_paths:
            print(f"   📋 Loading {len(profile_paths)} predefined entity profiles...")
            for profile_path in profile_paths:
                profile_file = Path(profile_path)
                if not profile_file.exists():
                    print(f"   ⚠️  Profile not found: {profile_path}, skipping...")
                    continue

                try:
                    with open(profile_file) as f:
                        profile_data = json.load(f)

                    # Extract name from filename (e.g., "profile.json" → "founder")
                    name = profile_file.stem

                    # Get full name from profile if available, otherwise use filename
                    full_name = profile_data.get("name", name.replace("_", " ").title())
                    entity_id = name.lower().replace(" ", "_")

                    # Create EntityRosterItem from profile
                    entity = EntityRosterItem(
                        entity_id=entity_id,
                        entity_type="human",
                        role="primary",  # Profiles are for primary characters
                        description=profile_data.get("description", f"{full_name} - Founder"),
                        initial_knowledge=profile_data.get("initial_knowledge", [
                            f"Expert in {profile_data.get('archetype_id', 'business')}",
                            *[f"Strength: {s}" for s in profile_data.get("strengths", [])[:2]],
                            *[f"Weakness: {w}" for w in profile_data.get("weaknesses", [])[:2]]
                        ]),
                        relationships={}  # Will be filled later
                    )
                    loaded_entities.append(entity)
                    print(f"   ✓ Loaded profile: {full_name} ({entity_id})")
                except Exception as e:
                    print(f"   ⚠️  Failed to load profile {profile_path}: {e}")
                    continue

        # Calculate how many entities still need to be generated
        remaining_count = count - len(loaded_entities)

        if remaining_count <= 0:
            print(f"   ✓ All {count} entities loaded from profiles")
            return loaded_entities

        print(f"   🤖 Generating {remaining_count} additional entities via LLM...")

        prompt = f"""You are generating an entity roster for a historical simulation.

Event: {event_description}

Generate EXACTLY {remaining_count} entities (people, places, objects, concepts) involved in this event.

For each entity, provide ONLY:
- entity_id: unique lowercase identifier (e.g., "thomas_jefferson")
- entity_type: type (human, animal, building, object, abstract)
- role: importance (primary, secondary, background, environment)
- description: ONE sentence description

Do NOT include knowledge or relationships yet - just the roster.

Return a JSON object with this structure:
{{
  "entities": [
    {{
      "entity_id": "string",
      "entity_type": "string",
      "role": "primary|secondary|background|environment",
      "description": "string",
      "initial_knowledge": [],
      "relationships": {{}}
    }}
  ]
}}

Return EXACTLY {remaining_count} entities. This is critical."""

        # Use larger token limit for roster generation (Llama 4 Scout supports 327K)
        max_tokens = min((count * 100) + 1000, 42000)

        # Try with 70B first, escalate to 405B if needed
        model = None  # Use default 70B
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries:
            # Check absolute timeout
            elapsed = time.time() - start_time
            if elapsed > absolute_timeout:
                if loaded_entities:
                    print(f"   ⚠️  Absolute timeout ({absolute_timeout}s) exceeded, returning {len(loaded_entities)} loaded profiles")
                    return loaded_entities
                raise TimeoutError(f"Entity roster generation exceeded {absolute_timeout}s timeout")

            try:
                result = self.llm.generate_structured(
                    prompt=prompt,
                    response_model=type('EntityList', (BaseModel,), {
                        '__annotations__': {'entities': List[EntityRosterItem]}
                    }),
                    model=model,
                    temperature=0.5,
                    max_tokens=max_tokens,
                    timeout=180.0
                )

                # Validate we got the right count
                if len(result.entities) < remaining_count * 0.8:  # Allow 20% tolerance
                    print(f"   ⚠️  Only got {len(result.entities)}/{remaining_count} entities, retrying...")
                    retry_count += 1
                    if retry_count <= max_retries:
                        # Escalate to 405B on retry
                        model = "meta-llama/llama-3.1-405b-instruct"
                        max_tokens = min((remaining_count * 120) + 2000, 100000)
                        continue

                # Merge loaded profiles with LLM-generated entities
                all_entities = loaded_entities + result.entities
                print(f"   ✓ Total entities: {len(all_entities)} ({len(loaded_entities)} from profiles + {len(result.entities)} generated)")
                return all_entities

            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    # If we have loaded profiles, return them even if LLM generation failed
                    if loaded_entities:
                        print(f"   ⚠️  LLM generation failed after {max_retries + 1} attempts, but returning {len(loaded_entities)} loaded profiles")
                        return loaded_entities
                    raise RuntimeError(f"Failed to generate entity roster after {max_retries + 1} attempts: {e}") from e

                print(f"   ⚠️  Attempt {retry_count} failed: {e}")
                print(f"   🚀 Escalating to Llama 405B...")
                model = "meta-llama/llama-3.1-405b-instruct"
                max_tokens = min((remaining_count * 120) + 2000, 100000)
                time.sleep(2 ** retry_count)  # Exponential backoff

        # Should never reach here, but just in case - return loaded profiles if we have them
        if loaded_entities:
            print(f"   ⚠️  Unexpected: Returning {len(loaded_entities)} loaded profiles")
            return loaded_entities
        raise RuntimeError("Failed to generate entity roster")

    def _generate_timepoint_skeleton(
        self,
        event_description: str,
        context: Dict,
        count: int,
        entity_roster: List[EntityRosterItem]
    ) -> List[TimepointSpec]:
        """Pass 2: Generate timepoint skeleton with minimal details"""

        entity_ids = [e.entity_id for e in entity_roster[:20]]  # Sample for context

        prompt = f"""You are generating a timepoint sequence for a historical simulation.

Event: {event_description}

Available entities (first 20): {', '.join(entity_ids)}

Generate EXACTLY {count} timepoints (key moments in the event sequence).

For each timepoint, provide ONLY:
- timepoint_id: unique identifier (e.g., "tp_001_opening")
- timestamp: ISO datetime
- event_description: BRIEF 1-sentence description
- entities_present: [] (empty for now, will fill later)
- importance: float 0.0-1.0
- causal_parent: previous timepoint_id (null for first)

Return a JSON object with this structure:
{{
  "timepoints": [
    {{
      "timepoint_id": "string",
      "timestamp": "ISO datetime",
      "event_description": "string",
      "entities_present": [],
      "importance": 0.5,
      "causal_parent": "string or null"
    }}
  ]
}}

Return EXACTLY {count} timepoints. This is critical."""

        max_tokens = min((count * 80) + 1000, 42000)
        model = None  # Use default 70B
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries:
            try:
                result = self.llm.generate_structured(
                    prompt=prompt,
                    response_model=type('TimepointList', (BaseModel,), {
                        '__annotations__': {'timepoints': List[TimepointSpec]}
                    }),
                    model=model,
                    temperature=0.5,
                    max_tokens=max_tokens,
                    timeout=180.0
                )

                if len(result.timepoints) < count * 0.8:
                    print(f"   ⚠️  Only got {len(result.timepoints)}/{count} timepoints, retrying...")
                    retry_count += 1
                    if retry_count <= max_retries:
                        model = "meta-llama/llama-3.1-405b-instruct"
                        max_tokens = min((count * 100) + 2000, 100000)
                        continue

                return result.timepoints

            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    raise RuntimeError(f"Failed to generate timepoint skeleton after {max_retries + 1} attempts: {e}") from e

                print(f"   ⚠️  Attempt {retry_count} failed: {e}")
                print(f"   🚀 Escalating to Llama 405B...")
                model = "meta-llama/llama-3.1-405b-instruct"
                max_tokens = min((count * 100) + 2000, 100000)
                time.sleep(2 ** retry_count)

        raise RuntimeError("Failed to generate timepoint skeleton")

    def _fill_entity_details(
        self,
        event_description: str,
        entity_roster: List[EntityRosterItem],
        timepoint_skeleton: List[TimepointSpec],
        context: Dict
    ) -> List[EntityRosterItem]:
        """Pass 3: Fill in entity details in batches"""

        batch_size = 30  # Process 30 entities at a time
        filled_entities = []

        for i in range(0, len(entity_roster), batch_size):
            batch = entity_roster[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(entity_roster) + batch_size - 1) // batch_size

            print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} entities)...")

            # Get other entity ids for relationships
            all_entity_ids = [e.entity_id for e in entity_roster]

            prompt = f"""Fill in details for these entities in the event: {event_description}

Entities to fill:
{json.dumps([{'entity_id': e.entity_id, 'description': e.description} for e in batch], indent=2)}

Available entities for relationships:
{', '.join(all_entity_ids[:50])}

For each entity, add:
- initial_knowledge: List of 3-8 knowledge items this entity knows at start
- relationships: Dict mapping other entity_ids to relationship types (ally, rival, mentor, etc.)
  - Choose 2-5 relationships from the available entities list
  - Use relationship types: ally, friend, colleague, rival, enemy, mentor, student, family, neutral

Return JSON matching this structure:
{{
  "entities": [
    {{
      "entity_id": "same as input",
      "initial_knowledge": ["fact1", "fact2", ...],
      "relationships": {{"entity_id": "relationship_type", ...}}
    }}
  ]
}}"""

            try:
                result = self.llm.generate_structured(
                    prompt=prompt,
                    response_model=type('EntityDetailsList', (BaseModel,), {
                        '__annotations__': {'entities': List[Dict]}
                    }),
                    model=None,
                    temperature=0.6,
                    max_tokens=min(len(batch) * 200 + 1000, 24000),
                    timeout=120.0
                )

                # Merge details back into original roster
                for orig_entity in batch:
                    # Find matching detailed entity
                    detailed = next((e for e in result.entities if e.get('entity_id') == orig_entity.entity_id), None)
                    if detailed:
                        orig_entity.initial_knowledge = detailed.get('initial_knowledge', [])
                        orig_entity.relationships = detailed.get('relationships', {})

                filled_entities.extend(batch)

            except Exception as e:
                print(f"   ⚠️  Batch {batch_num} failed: {e}. Using partial data...")
                # Use entities with empty knowledge/relationships on failure
                filled_entities.extend(batch)

        return filled_entities

    def _fill_timepoint_details(
        self,
        event_description: str,
        timepoint_skeleton: List[TimepointSpec],
        entity_roster: List[EntityRosterItem],
        context: Dict
    ) -> List[TimepointSpec]:
        """Pass 4: Fill in timepoint details in batches"""

        batch_size = 40  # Process 40 timepoints at a time
        filled_timepoints = []
        entity_ids = [e.entity_id for e in entity_roster]

        for i in range(0, len(timepoint_skeleton), batch_size):
            batch = timepoint_skeleton[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(timepoint_skeleton) + batch_size - 1) // batch_size

            print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} timepoints)...")

            prompt = f"""Fill in participant lists for these timepoints in the event: {event_description}

Timepoints to fill:
{json.dumps([{'timepoint_id': t.timepoint_id, 'timestamp': t.timestamp, 'event_description': t.event_description} for t in batch], indent=2)}

Available entities:
{', '.join(entity_ids[:100])}

For each timepoint, add:
- entities_present: List of entity_ids present at this moment (3-20 entities typically)
  - Choose relevant entities from the available list
  - Consider the timepoint description when selecting

Return JSON matching this structure:
{{
  "timepoints": [
    {{
      "timepoint_id": "same as input",
      "entities_present": ["entity_id1", "entity_id2", ...]
    }}
  ]
}}"""

            try:
                result = self.llm.generate_structured(
                    prompt=prompt,
                    response_model=type('TimepointDetailsList', (BaseModel,), {
                        '__annotations__': {'timepoints': List[Dict]}
                    }),
                    model=None,
                    temperature=0.5,
                    max_tokens=min(len(batch) * 100 + 1000, 24000),
                    timeout=120.0
                )

                # Merge details back into skeleton
                for orig_tp in batch:
                    detailed = next((t for t in result.timepoints if t.get('timepoint_id') == orig_tp.timepoint_id), None)
                    if detailed:
                        orig_tp.entities_present = detailed.get('entities_present', [])
                        # Validate entity IDs exist
                        orig_tp.entities_present = [eid for eid in orig_tp.entities_present if eid in entity_ids]

                filled_timepoints.extend(batch)

            except Exception as e:
                print(f"   ⚠️  Batch {batch_num} failed: {e}. Using partial data...")
                filled_timepoints.extend(batch)

        return filled_timepoints

    def _mock_scene_specification(self) -> SceneSpecification:
        """Generate mock scene specification for testing"""
        return SceneSpecification(
            scene_title="Test Scene",
            scene_description="A test scene for development purposes",
            temporal_mode="pearl",
            temporal_scope={
                "start_date": "2024-01-01T09:00:00",
                "end_date": "2024-01-01T17:00:00",
                "location": "Test Location"
            },
            entities=[
                EntityRosterItem(
                    entity_id="test_entity_1",
                    entity_type="human",
                    role="primary",
                    description="Primary test entity",
                    initial_knowledge=["fact1", "fact2", "fact3"],
                    relationships={"test_entity_2": "ally", "test_entity_3": "colleague"}
                ),
                EntityRosterItem(
                    entity_id="test_entity_2",
                    entity_type="human",
                    role="secondary",
                    description="Secondary test entity",
                    initial_knowledge=["fact4", "fact5"],
                    relationships={"test_entity_1": "ally"}
                ),
                EntityRosterItem(
                    entity_id="test_entity_3",
                    entity_type="human",
                    role="secondary",
                    description="Third test entity",
                    initial_knowledge=["fact6", "fact7", "fact8"],
                    relationships={"test_entity_1": "colleague"}
                )
            ],
            timepoints=[
                TimepointSpec(
                    timepoint_id="tp_001",
                    timestamp="2024-01-01T09:00:00",
                    event_description="Scene opening",
                    entities_present=["test_entity_1", "test_entity_2", "test_entity_3"],
                    importance=0.8,
                    causal_parent=None
                ),
                TimepointSpec(
                    timepoint_id="tp_002",
                    timestamp="2024-01-01T12:00:00",
                    event_description="Mid-scene development",
                    entities_present=["test_entity_1", "test_entity_2", "test_entity_3"],
                    importance=0.7,
                    causal_parent="tp_001"
                ),
                TimepointSpec(
                    timepoint_id="tp_003",
                    timestamp="2024-01-01T17:00:00",
                    event_description="Scene conclusion",
                    entities_present=["test_entity_1", "test_entity_2", "test_entity_3"],
                    importance=0.9,
                    causal_parent="tp_002"
                )
            ],
            global_context="Test context for development"
        )


# ============================================================================
# Component 2: Knowledge Seeder
# ============================================================================

class KnowledgeSeeder:
    """
    Seed initial entity knowledge states from scene specification.

    Creates ExposureEvent records for initial knowledge to establish
    causal provenance. Optionally augments with external sources
    (future: Wikipedia, historical databases).
    """

    def __init__(self, store: GraphStore):
        self.store = store

    @track_mechanism("M3", "exposure_event_tracking")
    def seed_knowledge(
        self,
        spec: SceneSpecification,
        create_exposure_events: bool = True
    ) -> Dict[str, List[ExposureEvent]]:
        """
        Create initial knowledge exposure events for all entities.

        Args:
            spec: Scene specification with entity initial_knowledge
            create_exposure_events: Whether to create ExposureEvent records

        Returns:
            Dict mapping entity_id to list of exposure events
        """
        exposure_map = {}

        # Parse temporal scope start time (handle 'Z' suffix)
        start_time = parse_iso_datetime(spec.temporal_scope["start_date"])

        for entity_item in spec.entities:
            events = []

            for idx, knowledge_item in enumerate(entity_item.initial_knowledge):
                # Create exposure event for each initial knowledge item
                event = ExposureEvent(
                    entity_id=entity_item.entity_id,
                    event_type="initial",  # Special type for starting knowledge
                    information=knowledge_item,
                    source="scene_initialization",
                    timestamp=start_time - timedelta(days=1),  # Before scene starts
                    confidence=1.0,  # Initial knowledge is certain
                    timepoint_id=f"pre_{spec.timepoints[0].timepoint_id if spec.timepoints else 'scene'}"
                )

                events.append(event)

                # Optionally save to database
                if create_exposure_events and self.store:
                    self.store.save_exposure_event(event)

            exposure_map[entity_item.entity_id] = events

        print(f"🌱 Seeded {sum(len(events) for events in exposure_map.values())} knowledge items across {len(exposure_map)} entities")

        return exposure_map


# ============================================================================
# Component 3: Relationship Extractor
# ============================================================================

class RelationshipExtractor:
    """
    Build social/spatial relationship graph from entity specifications.

    Creates NetworkX graph with:
    - Nodes: entity_ids
    - Edges: relationships with types and weights
    - Node attributes: entity metadata
    """

    @track_mechanism("M1", "heterogeneous_fidelity_graph")
    def build_graph(self, spec: SceneSpecification) -> nx.Graph:
        """
        Build relationship graph from scene specification.

        Args:
            spec: Scene specification with entity relationships

        Returns:
            NetworkX graph with nodes and edges
        """
        graph = nx.Graph()

        # Add nodes for all entities
        for entity_item in spec.entities:
            graph.add_node(
                entity_item.entity_id,
                entity_type=entity_item.entity_type,
                role=entity_item.role,
                description=entity_item.description
            )

        # Add edges for declared relationships
        for entity_item in spec.entities:
            for target_id, rel_type in entity_item.relationships.items():
                if target_id in graph.nodes:
                    # Weight relationships based on type (simple heuristic)
                    weight = self._relationship_weight(rel_type)
                    graph.add_edge(
                        entity_item.entity_id,
                        target_id,
                        relationship=rel_type,
                        weight=weight
                    )

        # Add co-presence edges based on timepoint attendance
        self._add_copresence_edges(graph, spec)

        print(f"🕸️  Built graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

        return graph

    def _relationship_weight(self, rel_type: str) -> float:
        """Convert relationship type to numeric weight"""
        weights = {
            "ally": 0.9,
            "friend": 0.8,
            "colleague": 0.7,
            "acquaintance": 0.5,
            "neutral": 0.3,
            "rival": 0.2,
            "enemy": 0.1,
            "mentor": 0.85,
            "student": 0.75,
            "family": 0.95
        }
        return weights.get(rel_type.lower(), 0.5)

    def _add_copresence_edges(self, graph: nx.Graph, spec: SceneSpecification):
        """Add edges between entities present at same timepoints"""
        for tp in spec.timepoints:
            entities = tp.entities_present
            # Add edge between all pairs present at this timepoint
            for i, e1 in enumerate(entities):
                for e2 in entities[i+1:]:
                    if e1 in graph.nodes and e2 in graph.nodes:
                        if not graph.has_edge(e1, e2):
                            graph.add_edge(
                                e1, e2,
                                relationship="copresent",
                                weight=0.4
                            )


# ============================================================================
# Component 4: Resolution Assigner
# ============================================================================

class ResolutionAssigner:
    """
    Assign resolution levels to entities based on their roles.

    Role-based heuristics:
    - primary: DIALOG or TRAINED (high detail)
    - secondary: GRAPH or DIALOG (medium detail)
    - background: SCENE (low detail)
    - environment: TENSOR_ONLY or SCENE (minimal detail)
    """

    @track_mechanism("M1", "heterogeneous_fidelity_resolution")
    def assign_resolutions(
        self,
        spec: SceneSpecification,
        graph: nx.Graph
    ) -> Tuple[Dict[str, ResolutionLevel], float]:
        """
        Assign resolution levels based on role and centrality.

        Args:
            spec: Scene specification with entity roles
            graph: NetworkX graph for centrality calculation

        Returns:
            Tuple of (assignments dict, estimated_cost float)
        """
        assignments = {}

        # Calculate eigenvector centrality if graph has edges
        centrality = {}
        if graph.number_of_edges() > 0:
            try:
                # Suppress RuntimeWarning for small graphs (k >= N - 1 for N * N square matrix)
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=RuntimeWarning)
                    centrality = nx.eigenvector_centrality(graph, max_iter=1000)
            except:
                # Fallback to degree centrality if eigenvector fails
                centrality = nx.degree_centrality(graph)

        for entity_item in spec.entities:
            entity_id = entity_item.entity_id
            role = entity_item.role
            cent = centrality.get(entity_id, 0.0)

            # Role-based resolution assignment
            if role == "primary":
                # High centrality primary actors get TRAINED
                if cent > 0.5:
                    level = ResolutionLevel.TRAINED
                else:
                    level = ResolutionLevel.DIALOG
            elif role == "secondary":
                # Medium centrality secondary actors
                if cent > 0.3:
                    level = ResolutionLevel.DIALOG
                else:
                    level = ResolutionLevel.GRAPH
            elif role == "background":
                level = ResolutionLevel.SCENE
            else:  # environment
                level = ResolutionLevel.TENSOR_ONLY

            assignments[entity_id] = level

        # Calculate cost estimates based on resolution distribution
        cost_per_level = {
            ResolutionLevel.TRAINED: 0.50,  # $0.50 per entity (model training)
            ResolutionLevel.DIALOG: 0.15,   # $0.15 per entity (dialog synthesis)
            ResolutionLevel.GRAPH: 0.05,    # $0.05 per entity (graph processing)
            ResolutionLevel.SCENE: 0.02,    # $0.02 per entity (scene aggregation)
            ResolutionLevel.TENSOR_ONLY: 0.005  # $0.005 per entity (tensor compression)
        }

        estimated_cost = sum(cost_per_level.get(level, 0.0) for level in assignments.values())

        counts = {
            'TRAINED': sum(1 for v in assignments.values() if v == ResolutionLevel.TRAINED),
            'DIALOG': sum(1 for v in assignments.values() if v == ResolutionLevel.DIALOG),
            'GRAPH': sum(1 for v in assignments.values() if v == ResolutionLevel.GRAPH),
            'SCENE': sum(1 for v in assignments.values() if v == ResolutionLevel.SCENE),
            'TENSOR': sum(1 for v in assignments.values() if v == ResolutionLevel.TENSOR_ONLY)
        }

        print(f"🎯 Assigned resolutions: "
              f"TRAINED={counts['TRAINED']}, "
              f"DIALOG={counts['DIALOG']}, "
              f"GRAPH={counts['GRAPH']}, "
              f"SCENE={counts['SCENE']}, "
              f"TENSOR={counts['TENSOR']}")
        print(f"💰 Estimated cost: ${estimated_cost:.2f} (vs ${len(assignments) * 0.50:.2f} naive full-resolution)")
        print(f"📊 Cost reduction: {(1 - estimated_cost / (len(assignments) * 0.50)) * 100:.1f}%")

        return assignments, estimated_cost


# ============================================================================
# Main Orchestrator Agent
# ============================================================================

class OrchestratorAgent:
    """
    Top-level coordinator for scene-to-simulation compilation.

    Orchestrates:
    1. SceneParser: Natural language → structured spec
    2. KnowledgeSeeder: Initial knowledge → exposure events
    3. RelationshipExtractor: Entity relationships → graph
    4. ResolutionAssigner: Role-based resolution targeting
    5. Integration with existing workflows

    Usage:
        orchestrator = OrchestratorAgent(llm_client, store)
        result = orchestrator.orchestrate("simulate the constitutional convention")
        # Returns entities, timepoints, graph ready for workflows
    """

    def __init__(self, llm_client: LLMClient, store: GraphStore):
        self.llm = llm_client
        self.store = store

        # Initialize components
        self.scene_parser = SceneParser(llm_client)
        self.knowledge_seeder = KnowledgeSeeder(store)
        self.relationship_extractor = RelationshipExtractor()
        self.resolution_assigner = ResolutionAssigner()

    @track_mechanism("M17", "modal_temporal_causality")
    def orchestrate(
        self,
        event_description: str,
        context: Optional[Dict] = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Complete orchestration: natural language → ready-to-simulate scene.

        Args:
            event_description: Natural language like "simulate the constitutional convention"
            context: Optional context (temporal_mode, max_entities, etc.)
            save_to_db: Whether to save entities/timepoints to database

        Returns:
            Dict with:
                - specification: SceneSpecification
                - entities: List[Entity] (populated, with resolution levels)
                - timepoints: List[Timepoint] (causal chain)
                - graph: NetworkX graph
                - exposure_events: Dict[entity_id, List[ExposureEvent]]
                - temporal_agent: TemporalAgent (configured for scene)
        """
        print(f"\n🎬 ORCHESTRATING SCENE: {event_description}\n")

        context = context or {}

        # Step 1: Parse scene specification
        print("📋 Step 1: Parsing scene specification...")
        spec = self.scene_parser.parse(event_description, context)
        print(f"   ✓ Title: {spec.scene_title}")
        print(f"   ✓ Temporal Mode: {spec.temporal_mode}")
        print(f"   ✓ Entities: {len(spec.entities)}")
        print(f"   ✓ Timepoints: {len(spec.timepoints)}")

        # Step 2: Seed initial knowledge
        print("\n🌱 Step 2: Seeding initial knowledge...")
        exposure_events = self.knowledge_seeder.seed_knowledge(spec, create_exposure_events=save_to_db)

        # Step 3: Build relationship graph
        print("\n🕸️  Step 3: Building relationship graph...")
        graph = self.relationship_extractor.build_graph(spec)

        # Step 3.5: Create relationship trajectories from graph edges (FIX BUG #4)
        relationship_trajectories = []
        if save_to_db:
            print("\n💑 Step 3.5: Creating relationship trajectories...")
            relationship_trajectories = self._create_relationship_trajectories(graph, spec, save_to_db=True)
            print(f"   ✓ Created {len(relationship_trajectories)} relationship trajectories")

        # Step 4: Assign resolution levels
        print("\n🎯 Step 4: Assigning resolution levels...")
        resolution_assignments, cost_estimate = self.resolution_assigner.assign_resolutions(spec, graph)

        # Step 4.5: Generate animistic entities if configured (M16)
        entity_metadata_config = context.get("entity_metadata", {})
        animistic_config = entity_metadata_config.get("animistic_entities", {})
        if animistic_config:
            print("\n🌟 Step 4.5: Generating animistic entities...")
            from workflows import generate_animistic_entities_for_scene

            # Generate animistic entities using the mechanism function
            try:
                animistic_entities = generate_animistic_entities_for_scene(
                    scene_context=spec,
                    config={"animism": animistic_config}
                )

                # Convert Entity objects back to EntityRosterItem for merging into spec
                for anim_entity in animistic_entities:
                    roster_item = EntityRosterItem(
                        entity_id=anim_entity.entity_id,
                        entity_type=anim_entity.entity_type,
                        role="environment",  # Animistic entities are environmental forces
                        description=anim_entity.entity_metadata.get("description", f"Animistic {anim_entity.entity_type}"),
                        initial_knowledge=[],
                        relationships={}
                    )
                    spec.entities.append(roster_item)

                print(f"   ✓ Generated {len(animistic_entities)} animistic entities")
            except Exception as e:
                print(f"   ⚠️  Animistic entity generation failed: {e}")

        # Step 4.7: Check for missing entities (M9 gap detection)
        print("\n🔍 Step 4.7: Checking for missing entities (M9)...")
        self._detect_and_generate_missing_entities(spec, save_to_db)

        # Step 5: Create Entity objects
        print("\n👥 Step 5: Creating entity objects...")
        entities = self._create_entities(spec, resolution_assignments, exposure_events, context)

        # Step 6: Create Timepoint objects
        print("\n⏰ Step 6: Creating timepoint objects...")
        timepoints = self._create_timepoints(spec)

        # Step 7: Save to database if requested
        if save_to_db:
            print("\n💾 Step 7: Saving to database...")
            for entity in entities:
                self.store.save_entity(entity)
            for tp in timepoints:
                self.store.save_timepoint(tp)
            print(f"   ✓ Saved {len(entities)} entities and {len(timepoints)} timepoints")

        # Step 8: Create TemporalAgent
        print("\n🕐 Step 8: Creating temporal agent...")
        temporal_mode = TemporalMode(spec.temporal_mode)
        temporal_agent = TemporalAgent(
            mode=temporal_mode,
            store=self.store,
            llm_client=self.llm
        )
        print(f"   ✓ Temporal agent created with mode: {temporal_mode.value}")

        print("\n✅ ORCHESTRATION COMPLETE\n")

        return {
            "specification": spec,
            "entities": entities,
            "timepoints": timepoints,
            "graph": graph,
            "exposure_events": exposure_events,
            "relationship_trajectories": relationship_trajectories,
            "temporal_agent": temporal_agent,
            "resolution_assignments": resolution_assignments,
            "estimated_cost": cost_estimate
        }

    def _fuzzy_match_entity(self, entity_id: str, metadata_dict: Dict) -> Optional[Dict]:
        """Fuzzy match entity_id to metadata keys using partial name matching"""
        # Try exact match first
        if entity_id in metadata_dict:
            return metadata_dict[entity_id]

        # Try partial matching - split on underscore and check if key contains any part
        entity_parts = entity_id.lower().split('_')
        for key, value in metadata_dict.items():
            key_lower = key.lower()
            # Check if any significant part of entity_id appears in the key
            for part in entity_parts:
                if len(part) > 3 and part in key_lower:  # Ignore short parts like "dr"
                    return value

        return None

    def _create_entities(
        self,
        spec: SceneSpecification,
        resolution_assignments: Dict[str, ResolutionLevel],
        exposure_events: Dict[str, List[ExposureEvent]],
        context: Optional[Dict] = None
    ) -> List[Entity]:
        """Create Entity objects from specification"""
        from schemas import PhysicalTensor

        entities = []
        context = context or {}
        entity_metadata_config = context.get("entity_metadata", {})

        for entity_item in spec.entities:
            # Create cognitive tensor with initial knowledge
            knowledge_state = entity_item.initial_knowledge
            cognitive = CognitiveTensor(
                knowledge_state=knowledge_state,
                energy_budget=100.0,
                decision_confidence=0.8
            )

            # Get resolution level
            resolution = resolution_assignments.get(
                entity_item.entity_id,
                ResolutionLevel.SCENE
            )

            # Get first timepoint for temporal assignment
            first_tp = spec.timepoints[0] if spec.timepoints else None

            # Build entity metadata
            metadata = {
                "cognitive_tensor": cognitive.model_dump(),
                "role": entity_item.role,
                "description": entity_item.description,
                "scene_context": spec.global_context,
                "orchestrated": True
            }

            # M8: Initialize physical_tensor (ALWAYS for humans, optionally from embodied_constraints)
            # Also create minimal physical tensors for non-humans to enable dialog participation
            if entity_item.entity_type == "human":
                # Check for custom embodied_constraints (fuzzy match)
                embodied_dict = entity_metadata_config.get("embodied_constraints", {})
                embodied = self._fuzzy_match_entity(entity_item.entity_id, embodied_dict) or {}

                # Create physical tensor with defaults or custom values
                physical = PhysicalTensor(
                    age=embodied.get("age", 35.0),  # Default adult age
                    health_status=embodied.get("health_status", 1.0),
                    pain_level=embodied.get("pain_level", 0.0),
                    pain_location=embodied.get("pain_location", None),
                    fever=embodied.get("fever", 36.5),
                    mobility=embodied.get("mobility", 1.0),
                    stamina=embodied.get("stamina", 1.0),
                    sensory_acuity=embodied.get("sensory_acuity", {"vision": 1.0, "hearing": 1.0}),
                    location=embodied.get("location", None)
                )
                metadata["physical_tensor"] = physical.model_dump()
            else:
                # Create minimal physical tensor for non-human entities (buildings, spirits, animals)
                # This enables them to participate in dialogs as present entities
                physical = PhysicalTensor(
                    age=100.0,  # Generic "age" for non-humans
                    health_status=1.0,
                    pain_level=0.0,
                    pain_location=None,
                    fever=0.0,  # No body temperature for non-humans (0.0 = no fever tracking)
                    mobility=0.0,  # Non-humans typically don't move
                    stamina=1.0,
                    sensory_acuity={"vision": 0.5, "hearing": 0.5},  # Limited sensory capabilities
                    location=None
                )
                metadata["physical_tensor"] = physical.model_dump()

            # M14: Initialize circadian attributes if circadian_config exists
            circadian = entity_metadata_config.get("circadian_config", {})
            if circadian:
                metadata["circadian"] = circadian

            # M15: Initialize prospection attributes
            prospection = entity_metadata_config.get("prospection_config", {})
            modeling_entity = prospection.get("modeling_entity")

            # Debug logging for M15
            if prospection and entity_item.entity_id in ["sherlock_holmes", "holmes", "detective", "moriarty"]:
                print(f"   [M15 DEBUG] Entity: {entity_item.entity_id}")
                print(f"   [M15 DEBUG] modeling_entity from config: {modeling_entity}")
                print(f"   [M15 DEBUG] Match: {entity_item.entity_id == modeling_entity}")

            if entity_item.entity_id == modeling_entity:
                metadata["prospection_ability"] = prospection.get("prospection_ability", 0.0)
                metadata["theory_of_mind"] = prospection.get("theory_of_mind", 0.0)
                metadata["target_entity"] = prospection.get("target_entity")
                print(f"   ✓ Set prospection_ability={metadata['prospection_ability']} for {entity_item.entity_id}")

            # M16: Initialize animistic consciousness (fuzzy match)
            animistic_dict = entity_metadata_config.get("animistic_entities", {})
            animistic = self._fuzzy_match_entity(entity_item.entity_id, animistic_dict) or {}
            if animistic:
                metadata["consciousness"] = animistic.get("consciousness", 0.0)
                metadata["spiritual_power"] = animistic.get("spiritual_power", 0.0)
                metadata["memory_depth"] = animistic.get("memory_depth", "")
                metadata["manifestation_strength"] = animistic.get("manifestation_strength", 0.0)

            entity = Entity(
                entity_id=entity_item.entity_id,
                entity_type=entity_item.entity_type,
                timepoint=first_tp.timepoint_id if first_tp else None,
                resolution_level=resolution,
                entity_metadata=metadata
            )

            # Phase 7: Generate TTM tensor for entity (Phase 7 orchestrator completion)
            from tensors import generate_ttm_tensor
            tensor_json = generate_ttm_tensor(entity)
            if tensor_json:
                entity.tensor = tensor_json

            # M15: Generate prospective state if entity has prospection ability
            prospection_ability = metadata.get("prospection_ability", 0.0)

            # Debug logging for prospection generation attempt
            if entity.entity_id in ["sherlock_holmes", "holmes", "detective", "moriarty"]:
                print(f"   [M15 DEBUG] Checking prospection generation for {entity.entity_id}")
                print(f"   [M15 DEBUG] prospection_ability: {prospection_ability}")
                print(f"   [M15 DEBUG] first_tp: {first_tp.timepoint_id if first_tp else None}")
                print(f"   [M15 DEBUG] Will generate: {prospection_ability > 0.0 and first_tp}")

            if prospection_ability > 0.0 and first_tp:
                from workflows import generate_prospective_state
                print(f"   🔮 [M15] Generating prospective state for {entity.entity_id}")
                try:
                    # Create Timepoint object for prospection generation
                    first_timepoint = Timepoint(
                        timepoint_id=first_tp.timepoint_id,
                        timestamp=parse_iso_datetime(first_tp.timestamp),
                        event_description=first_tp.event_description,
                        entities_present=first_tp.entities_present
                    )

                    # Generate prospective state
                    prospective_state = generate_prospective_state(
                        entity,
                        first_timepoint,
                        self.llm,
                        self.store
                    )

                    # Store in entity metadata (use mode='json' to serialize datetime fields)
                    entity.entity_metadata["prospective_state"] = prospective_state.model_dump(mode='json')
                    print(f"   ✓ Generated prospective state for {entity.entity_id}")
                except Exception as e:
                    print(f"   ⚠️  Prospection generation failed for {entity.entity_id}: {e}")
                    import traceback
                    traceback.print_exc()

            entities.append(entity)

        print(f"   ✓ Created {len(entities)} entity objects")
        return entities

    def _create_timepoints(self, spec: SceneSpecification) -> List[Timepoint]:
        """Create Timepoint objects from specification"""
        timepoints = []

        for tp_spec in spec.timepoints:
            # Parse timestamp (handle 'Z' suffix)
            timestamp = parse_iso_datetime(tp_spec.timestamp)

            timepoint = Timepoint(
                timepoint_id=tp_spec.timepoint_id,
                timestamp=timestamp,
                event_description=tp_spec.event_description,
                entities_present=tp_spec.entities_present,
                causal_parent=tp_spec.causal_parent,
                resolution_level=ResolutionLevel.SCENE,  # Default
                timepoint_metadata={
                    "importance": tp_spec.importance,
                    "orchestrated": True
                }
            )

            timepoints.append(timepoint)

        print(f"   ✓ Created {len(timepoints)} timepoint objects")
        return timepoints

    def _create_relationship_trajectories(
        self,
        graph: nx.Graph,
        spec: SceneSpecification,
        save_to_db: bool = True
    ):
        """
        Create initial relationship trajectories from graph edges.

        FIX BUG #4: Orchestrator builds NetworkX graph but never saves RelationshipTrajectory
        records to database. M13 context manager queries these records and finds nothing,
        resulting in empty relationship context in training data.

        This method creates minimal RelationshipTrajectory records for initial relationships.
        For multi-timepoint scenarios, these will be updated by analyze_relationship_evolution().

        Args:
            graph: NetworkX graph with relationship edges
            spec: Scene specification
            save_to_db: Whether to save trajectories to database

        Returns:
            List of created RelationshipTrajectory objects
        """
        from schemas import RelationshipTrajectory

        trajectories = []
        first_tp = spec.timepoints[0] if spec.timepoints else None

        if not first_tp:
            return trajectories

        # Parse timestamp for initial state
        timestamp = parse_iso_datetime(first_tp.timestamp)

        # Iterate through all edges in the graph
        for entity_a, entity_b, edge_data in graph.edges(data=True):
            relationship_type = edge_data.get('relationship', 'unknown')
            weight = edge_data.get('weight', 0.5)

            # Create relationship metrics based on type
            # Higher weights for positive relationships
            metrics = {
                'trust': weight,
                'affection': weight if relationship_type in ['friend', 'ally', 'family'] else 0.3,
                'respect': weight,
                'cooperation': weight if relationship_type in ['colleague', 'ally'] else 0.5
            }

            # Create initial state (will be serialized to JSON)
            state = {
                'entity_a': entity_a,
                'entity_b': entity_b,
                'timestamp': timestamp.isoformat(),  # Convert to ISO string for JSON
                'timepoint_id': first_tp.timepoint_id,
                'metrics': metrics,
                'recent_events': []
            }

            # Create trajectory
            trajectory = RelationshipTrajectory(
                trajectory_id=f"trajectory_{entity_a}_{entity_b}_{first_tp.timepoint_id}",
                entity_a=entity_a,
                entity_b=entity_b,
                start_timepoint=first_tp.timepoint_id,
                end_timepoint=first_tp.timepoint_id,
                states=json.dumps([state]),  # Serialize to JSON string
                overall_trend='stable',  # Initial relationships are stable
                key_events=[],
                relationship_type=relationship_type,
                current_strength=weight,
                context_summary=f"Initial {relationship_type} relationship between {entity_a} and {entity_b}"
            )

            trajectories.append(trajectory)

            # Save to database
            if save_to_db and self.store:
                self.store.save_relationship_trajectory(trajectory)

        return trajectories

    def _detect_and_generate_missing_entities(
        self,
        spec: SceneSpecification,
        save_to_db: bool = True
    ) -> None:
        """
        Detect and generate missing entities mentioned in event descriptions (M9).

        Uses QueryInterface to extract entity names from scene/timepoint descriptions
        and generates any missing numbered entities (e.g., attendee_47).
        """
        from query_interface import QueryInterface

        # Create temporary query interface for gap detection
        query_interface = QueryInterface(self.store, self.llm)

        # Get existing entity IDs from spec
        existing_entities = set(e.entity_id for e in spec.entities)

        # Collect all text to search for entity mentions
        texts_to_search = [
            spec.scene_description,
            spec.global_context
        ]

        # Add timepoint descriptions
        for tp in spec.timepoints:
            texts_to_search.append(tp.event_description)

        # Detect gaps across all text
        all_missing = set()
        for text in texts_to_search:
            mentioned_entities = query_interface.extract_entity_names(text)
            missing = mentioned_entities - existing_entities
            all_missing.update(missing)

        if not all_missing:
            print("   ✓ No missing entities detected")
            return

        print(f"   🔍 Found {len(all_missing)} missing entities: {list(all_missing)[:5]}...")

        # Generate missing entities
        generated_count = 0
        first_tp_spec = spec.timepoints[0] if spec.timepoints else None

        for entity_id in all_missing:
            try:
                # Determine role and context for entity
                role = "background"  # Default for gap-filled entities
                description = f"Generated entity: {entity_id.replace('_', ' ')}"

                # Create EntityRosterItem
                roster_item = EntityRosterItem(
                    entity_id=entity_id,
                    entity_type="human",  # Assume human for numbered attendees
                    role=role,
                    description=description,
                    initial_knowledge=[f"Present at {spec.scene_title}"],
                    relationships={}
                )

                # Add to spec
                spec.entities.append(roster_item)

                # Add to first timepoint if exists
                if first_tp_spec and entity_id not in first_tp_spec.entities_present:
                    first_tp_spec.entities_present.append(entity_id)

                generated_count += 1
                print(f"   ✓ Generated missing entity: {entity_id}")

            except Exception as e:
                print(f"   ⚠️  Failed to generate {entity_id}: {e}")

        print(f"   ✓ Generated {generated_count} missing entities")


# ============================================================================
# Convenience Functions
# ============================================================================

def simulate_event(
    event_description: str,
    llm_client: LLMClient,
    store: GraphStore,
    context: Optional[Dict] = None,
    save_to_db: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for complete event simulation.

    Usage:
        from orchestrator import simulate_event
        result = simulate_event(
            "simulate the constitutional convention",
            llm_client,
            store
        )

    Returns orchestration result with entities, timepoints, graph, etc.
    """
    orchestrator = OrchestratorAgent(llm_client, store)
    return orchestrator.orchestrate(event_description, context, save_to_db)
