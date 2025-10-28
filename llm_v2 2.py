"""
llm_v2.py - Backward-compatible wrapper using centralized LLM service

This module provides a drop-in replacement for the existing LLMClient
while using the new centralized LLM service architecture under the hood.

Usage:
    # Option 1: Use new service directly
    from llm_service import LLMService, LLMServiceConfig
    config = LLMServiceConfig.from_hydra_config(cfg)
    service = LLMService(config)
    response = service.call(system="...", user="...")

    # Option 2: Use backward-compatible LLMClient (migrates gradually)
    from llm_v2 import LLMClient
    client = LLMClient(api_key="...", use_centralized_service=True)
    result = client.populate_entity(...)
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import numpy as np
from datetime import datetime

# Import new service
from llm_service import LLMService, LLMServiceConfig
from llm_service.config import ServiceMode, DefaultParametersConfig, APIKeyConfig

# Import existing schemas for compatibility
from llm import EntityPopulation, ValidationResult


class LLMClient:
    """
    Backward-compatible LLM client wrapper.

    Can operate in two modes:
    1. Legacy mode: Uses old OpenRouterClient directly
    2. Service mode: Uses new centralized LLM service

    Set use_centralized_service=True to enable new architecture.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        dry_run: bool = False,
        default_model: Optional[str] = None,
        model_cache_ttl_hours: int = 24,
        use_centralized_service: bool = True,  # Enable new service by default
        service_config: Optional[LLMServiceConfig] = None,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: OpenRouter API key
            base_url: API base URL
            dry_run: If True, return mock responses
            default_model: Default model identifier
            model_cache_ttl_hours: Model cache TTL
            use_centralized_service: Use new centralized service (recommended)
            service_config: Optional pre-built service config
        """
        self.api_key = api_key
        self.base_url = base_url
        self.dry_run = dry_run
        self.default_model = default_model or "meta-llama/llama-3.1-70b-instruct"
        self.use_centralized_service = use_centralized_service

        # Statistics (maintain compatibility)
        self.token_count = 0
        self.cost = 0.0

        if use_centralized_service:
            # Use new centralized service
            if service_config:
                self.service = LLMService(service_config)
            else:
                # Build config from constructor parameters
                config = LLMServiceConfig(
                    provider="custom",
                    base_url=base_url,
                    api_keys=APIKeyConfig(primary=api_key),
                    mode=ServiceMode.DRY_RUN if dry_run else ServiceMode.PRODUCTION,
                    defaults=DefaultParametersConfig(model=self.default_model),
                )
                self.service = LLMService(config)
        else:
            # Use legacy implementation
            from llm import OpenRouterClient, ModelManager

            self.client = OpenRouterClient(api_key=api_key, base_url=base_url) if not dry_run else None
            self.model_manager = ModelManager(api_key, model_cache_ttl_hours)

    def populate_entity(
        self,
        entity_schema: Dict,
        context: Dict,
        previous_knowledge: List[str] = None,
        model: Optional[str] = None
    ) -> EntityPopulation:
        """
        Populate entity with structured output.

        Args:
            entity_schema: Entity schema dict with entity_id, etc.
            context: Context information
            previous_knowledge: Previous knowledge state for evolution
            model: Model identifier

        Returns:
            EntityPopulation instance
        """
        if self.use_centralized_service:
            return self._populate_entity_v2(entity_schema, context, previous_knowledge, model)
        else:
            # Fallback to legacy implementation
            return self._populate_entity_legacy(entity_schema, context, previous_knowledge, model)

    def _populate_entity_v2(
        self,
        entity_schema: Dict,
        context: Dict,
        previous_knowledge: List[str] = None,
        model: Optional[str] = None
    ) -> EntityPopulation:
        """Implementation using centralized service"""

        # Handle both Dict and Entity object
        if hasattr(entity_schema, 'entity_id'):
            # It's an Entity object
            entity_id = entity_schema.entity_id
        else:
            # It's a dict
            entity_id = entity_schema['entity_id']

        # Build prompts
        previous_context = ""
        if previous_knowledge:
            previous_context = (
                f"\nPrevious knowledge state: {previous_knowledge}\n"
                "Generate how this entity has evolved - what new information "
                "they've acquired and how their state has changed."
            )

        system_prompt = "You are an expert at generating realistic entity information for historical simulations."
        user_prompt = f"""Generate entity information for {entity_id}.
Context: {context}{previous_context}

Return a JSON object with these exact fields:
- entity_id: string (must be "{entity_id}")
- knowledge_state: array of strings (3-8 knowledge items)
- energy_budget: number between 0-100
- personality_traits: array of exactly 5 floats between -1 and 1
- temporal_awareness: string describing time perception
- confidence: number between 0 and 1

Return only valid JSON, no other text."""

        # Make structured call
        result = self.service.structured_call(
            system=system_prompt,
            user=user_prompt,
            schema=EntityPopulation,
            temperature=0.7,
            max_tokens=1000,
            model=model,
            call_type="populate_entity",
        )

        # Update statistics
        stats = self.service.get_statistics()
        self.token_count = stats.get("logger_stats", {}).get("total_tokens", 0)
        self.cost = stats.get("total_cost", 0.0)

        return result

    def _populate_entity_legacy(
        self,
        entity_schema: Dict,
        context: Dict,
        previous_knowledge: List[str] = None,
        model: Optional[str] = None
    ) -> EntityPopulation:
        """Legacy implementation for fallback"""
        if self.dry_run:
            return self._mock_entity_population(entity_schema, previous_knowledge)

        # Use original implementation from llm.py
        from llm import LLMClient as LegacyClient
        legacy = LegacyClient(self.api_key, self.base_url, self.dry_run)
        return legacy.populate_entity(entity_schema, context, previous_knowledge, model)

    def validate_consistency(
        self,
        entities: List[Dict],
        timepoint: datetime,
        model: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate temporal consistency.

        Args:
            entities: List of entity dicts
            timepoint: Timepoint to validate
            model: Model identifier

        Returns:
            ValidationResult instance
        """
        if self.use_centralized_service:
            return self._validate_consistency_v2(entities, timepoint, model)
        else:
            return self._validate_consistency_legacy(entities, timepoint, model)

    def _validate_consistency_v2(
        self,
        entities: List[Dict],
        timepoint: datetime,
        model: Optional[str] = None
    ) -> ValidationResult:
        """Implementation using centralized service"""

        system_prompt = "You are an expert at validating temporal consistency in historical simulations."
        user_prompt = f"""Validate temporal consistency of entities at {timepoint}.
Entities: {entities}
Check for: anachronisms, biological impossibilities, knowledge contradictions.

Return a JSON object with these exact fields:
- is_valid: boolean (true if no issues found)
- violations: array of strings (list of problems found)
- confidence: number between 0 and 1 (confidence in validation)
- reasoning: string explaining the validation result

Return only valid JSON, no other text."""

        result = self.service.structured_call(
            system=system_prompt,
            user=user_prompt,
            schema=ValidationResult,
            temperature=0.1,
            max_tokens=800,
            model=model,
            call_type="validate_consistency",
        )

        # Update statistics
        stats = self.service.get_statistics()
        self.token_count = stats.get("logger_stats", {}).get("total_tokens", 0)
        self.cost = stats.get("total_cost", 0.0)

        return result

    def _validate_consistency_legacy(
        self,
        entities: List[Dict],
        timepoint: datetime,
        model: Optional[str] = None
    ) -> ValidationResult:
        """Legacy implementation"""
        if self.dry_run:
            return ValidationResult(is_valid=True, violations=[], confidence=1.0, reasoning="Dry run mock")

        from llm import LLMClient as LegacyClient
        legacy = LegacyClient(self.api_key, self.base_url, self.dry_run)
        return legacy.validate_consistency(entities, timepoint, model)

    def score_relevance(self, query: str, knowledge_item: str, model: Optional[str] = None) -> float:
        """
        Score how relevant a knowledge item is to a query.

        Args:
            query: Query string
            knowledge_item: Knowledge item to score
            model: Model identifier

        Returns:
            Relevance score (0.0-1.0)
        """
        if self.use_centralized_service:
            return self._score_relevance_v2(query, knowledge_item, model)
        else:
            return self._score_relevance_legacy(query, knowledge_item, model)

    def _score_relevance_v2(self, query: str, knowledge_item: str, model: Optional[str] = None) -> float:
        """Implementation using centralized service"""

        user_prompt = f"""Rate how relevant this knowledge item is to the query on a scale of 0.0 to 1.0.

Query: "{query}"
Knowledge: "{knowledge_item}"

Return only a number between 0.0 and 1.0, where:
- 1.0 = Perfectly relevant and directly answers the query
- 0.5 = Somewhat relevant but not central to the query
- 0.0 = Completely irrelevant to the query

Relevance score:"""

        response = self.service.call(
            system="You are an expert at assessing relevance between queries and knowledge items.",
            user=user_prompt,
            temperature=0.1,
            max_tokens=10,
            model=model,
            call_type="score_relevance",
        )

        if not response.success:
            # Fallback to heuristic
            return self._heuristic_relevance_score(query, knowledge_item)

        # Parse score from response
        try:
            score_text = response.content.strip()
            score = float(score_text)
            return max(0.0, min(1.0, score))
        except ValueError:
            return self._heuristic_relevance_score(query, knowledge_item)

    def _score_relevance_legacy(self, query: str, knowledge_item: str, model: Optional[str] = None) -> float:
        """Legacy implementation"""
        if self.dry_run:
            return self._heuristic_relevance_score(query, knowledge_item)

        from llm import LLMClient as LegacyClient
        legacy = LegacyClient(self.api_key, self.base_url, self.dry_run)
        return legacy.score_relevance(query, knowledge_item, model)

    def generate_structured(self, prompt: str, response_model: type, model: Optional[str] = None, **kwargs):
        """
        Generate structured output using Pydantic schema.

        Args:
            prompt: Generation prompt
            response_model: Pydantic model class for structured output
            model: Model identifier
            **kwargs: Additional generation parameters

        Returns:
            Instance of response_model or list of instances
        """
        if self.use_centralized_service:
            return self._generate_structured_v2(prompt, response_model, model, **kwargs)
        else:
            return self._generate_structured_legacy(prompt, response_model, model, **kwargs)

    def _generate_structured_v2(self, prompt: str, response_model: type, model: Optional[str] = None, **kwargs):
        """Implementation using centralized service"""
        system_prompt = kwargs.pop("system_prompt", "You are a helpful assistant that generates structured data.")

        result = self.service.structured_call(
            system=system_prompt,
            user=prompt,
            schema=response_model,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1500),
            model=model,
            call_type="generate_structured",
        )

        # Update statistics
        stats = self.service.get_statistics()
        self.token_count = stats.get("logger_stats", {}).get("total_tokens", 0)
        self.cost = stats.get("total_cost", 0.0)

        return result

    def _generate_structured_legacy(self, prompt: str, response_model: type, model: Optional[str] = None, **kwargs):
        """Legacy implementation - fallback to mock"""
        # For legacy mode, return a mock instance
        if hasattr(response_model, '__origin__') and response_model.__origin__ is list:
            # Handle List[SomeModel]
            return []
        else:
            # Return a basic instance
            return response_model()

    def generate_expectations(self, entity_context: dict, timepoint_context: dict, model: Optional[str] = None):
        """
        Generate expectations for prospection mechanism.

        Args:
            entity_context: Entity information
            timepoint_context: Current timepoint information
            model: Model identifier

        Returns:
            ProspectiveState instance
        """
        if self.use_centralized_service:
            return self._generate_expectations_v2(entity_context, timepoint_context, model)
        else:
            return self._generate_expectations_legacy(entity_context, timepoint_context, model)

    def _generate_expectations_v2(self, entity_context: dict, timepoint_context: dict, model: Optional[str] = None):
        """Implementation using centralized service"""
        from schemas import ProspectiveState, Expectation
        from typing import List

        forecast_horizon = entity_context.get('forecast_horizon_days', 30)
        max_expectations = entity_context.get('max_expectations', 5)

        system_prompt = "You are an expert at predicting how historical figures think about and anticipate future events based on their knowledge and context."

        user_prompt = f"""Generate realistic expectations for {entity_context.get('entity_id')} about the future.

Context:
- Current situation: {timepoint_context.get('current_timepoint', 'unknown')}
- Time: {timepoint_context.get('current_timestamp', 'unknown')}
- Entity type: {entity_context.get('entity_type', 'person')}
- Recent knowledge: {', '.join(entity_context.get('knowledge_sample', [])[:5])}
- Personality traits: {entity_context.get('personality', {})}

Generate {max_expectations} expectations about events that might happen in the next {forecast_horizon} days.
Each expectation should include:
- predicted_event: What the entity expects to happen
- subjective_probability: How likely they think it is (0.0-1.0)
- desired_outcome: Whether they want this to happen (true/false)
- preparation_actions: List of actions they might take to prepare or respond
- confidence: How confident they are in this expectation (0.0-1.0)

Return as JSON array of expectation objects."""

        # Generate expectations using structured call
        expectations = self.service.structured_call(
            system=system_prompt,
            user=user_prompt,
            schema=List[Expectation],
            temperature=0.7,
            max_tokens=1500,
            model=model,
            call_type="generate_expectations",
        )

        # Update statistics
        stats = self.service.get_statistics()
        self.token_count = stats.get("logger_stats", {}).get("total_tokens", 0)
        self.cost = stats.get("total_cost", 0.0)

        return expectations if isinstance(expectations, list) else []

    def _generate_expectations_legacy(self, entity_context: dict, timepoint_context: dict, model: Optional[str] = None):
        """Legacy implementation - return mock expectations"""
        from schemas import Expectation

        return [
            Expectation(
                predicted_event="Routine continues normally",
                subjective_probability=0.7,
                desired_outcome=True,
                preparation_actions=["maintain_current_course"],
                confidence=0.8
            )
        ]

    def enrich_animistic_entity(self, entity_id: str, entity_type: str, base_metadata: dict, context: dict, model: Optional[str] = None):
        """
        Enrich animistic entity with LLM-generated background and characteristics.

        Args:
            entity_id: Entity identifier
            entity_type: Type of entity (animal, building, abstract, etc.)
            base_metadata: Basic metadata already generated
            context: Historical/situational context
            model: Model identifier

        Returns:
            Enriched metadata dict with narrative background
        """
        if self.use_centralized_service:
            return self._enrich_animistic_entity_v2(entity_id, entity_type, base_metadata, context, model)
        else:
            return self._enrich_animistic_entity_legacy(entity_id, entity_type, base_metadata, context, model)

    def _enrich_animistic_entity_v2(self, entity_id: str, entity_type: str, base_metadata: dict, context: dict, model: Optional[str] = None):
        """Implementation using centralized service"""

        system_prompt = "You are an expert at creating rich, historically accurate backgrounds for entities in narrative simulations."

        # Customize prompt based on entity type
        if entity_type == "animal":
            user_prompt = f"""Create a rich background for an animal entity in a historical simulation.

Entity ID: {entity_id}
Species: {base_metadata.get('species', 'unknown')}
Context: {context.get('timepoint_context', 'historical setting')}
Current state: {base_metadata.get('biological_state', {})}

Generate a narrative background that includes:
- A brief history of this animal (2-3 sentences)
- Notable characteristics or quirks
- Relationship with humans or other entities
- Role in the current historical context

Return a JSON object with:
- background_story: string (narrative description)
- notable_traits: array of strings (key characteristics)
- relationships: object mapping entity IDs to relationship descriptions
- historical_significance: string (role in context)"""

        elif entity_type == "building":
            user_prompt = f"""Create a rich background for a building entity in a historical simulation.

Entity ID: {entity_id}
Context: {context.get('timepoint_context', 'historical setting')}
Age: {base_metadata.get('age', 'unknown')} years
Condition: {base_metadata.get('structural_integrity', 'unknown')}

Generate a narrative background that includes:
- Construction history and purpose
- Architectural significance
- Events that occurred here
- Cultural or political importance

Return a JSON object with:
- background_story: string (narrative description)
- architectural_style: string
- historical_events: array of strings (key events at this location)
- cultural_significance: string"""

        elif entity_type == "abstract":
            user_prompt = f"""Create a rich background for an abstract concept entity in a historical simulation.

Entity ID: {entity_id}
Context: {context.get('timepoint_context', 'historical setting')}

Generate a narrative background that includes:
- Origin and evolution of this concept
- How it spreads through populations
- Cultural interpretations
- Impact on historical events

Return a JSON object with:
- background_story: string (narrative description)
- origin: string (how concept emerged)
- propagation_mechanism: string (how it spreads)
- cultural_impact: array of strings (effects on society)"""

        else:
            # Generic enrichment
            user_prompt = f"""Create a rich background for entity '{entity_id}' of type '{entity_type}'.

Context: {context.get('timepoint_context', 'historical setting')}
Base metadata: {base_metadata}

Return a JSON object with:
- background_story: string (narrative description)
- key_features: array of strings (notable characteristics)"""

        try:
            response = self.service.call(
                system=system_prompt,
                user=user_prompt,
                temperature=0.8,
                max_tokens=800,
                model=model,
                call_type="enrich_animistic_entity",
            )

            # Parse JSON response
            import json
            enrichment = json.loads(response.content)

            # Merge with base metadata
            enriched = {**base_metadata}
            enriched['llm_enrichment'] = enrichment

            # Update statistics
            stats = self.service.get_statistics()
            self.token_count = stats.get("logger_stats", {}).get("total_tokens", 0)
            self.cost = stats.get("total_cost", 0.0)

            return enriched

        except Exception as e:
            # Fallback to base metadata if enrichment fails
            return base_metadata

    def _enrich_animistic_entity_legacy(self, entity_id: str, entity_type: str, base_metadata: dict, context: dict, model: Optional[str] = None):
        """Legacy implementation - return base metadata unchanged"""
        return base_metadata

    def generate_scene_atmosphere(self, timepoint: dict, entities: list, environment: dict, atmosphere_data: dict, model: Optional[str] = None):
        """
        Generate rich narrative description of scene atmosphere.

        Args:
            timepoint: Timepoint information
            entities: List of entities present
            environment: Environmental conditions
            atmosphere_data: Computed atmosphere metrics
            model: Model identifier

        Returns:
            Dict with narrative description and mood details
        """
        if self.use_centralized_service:
            return self._generate_scene_atmosphere_v2(timepoint, entities, environment, atmosphere_data, model)
        else:
            return self._generate_scene_atmosphere_legacy(timepoint, entities, environment, atmosphere_data, model)

    def _generate_scene_atmosphere_v2(self, timepoint: dict, entities: list, environment: dict, atmosphere_data: dict, model: Optional[str] = None):
        """Implementation using centralized service"""

        system_prompt = "You are an expert at creating vivid, historically accurate scene descriptions that capture atmosphere and mood."

        # Build entity list
        entity_names = [e.get('entity_id', 'unknown') for e in entities[:10]]  # Limit for prompt size
        entity_summary = f"{len(entities)} entities present" + (f" including {', '.join(entity_names[:5])}" if entity_names else "")

        user_prompt = f"""Create a rich atmospheric description of this historical scene.

Timepoint: {timepoint.get('event_description', 'Historical event')}
Time: {timepoint.get('timestamp', 'Unknown time')}
Location: {environment.get('location', 'Unknown location')}

Environment:
- Temperature: {environment.get('ambient_temperature', 20)}°C
- Lighting: {environment.get('lighting_level', 0.5) * 100}%
- Weather: {environment.get('weather', 'clear')}
- Architecture: {environment.get('architectural_style', 'unknown style')}

Atmosphere Metrics:
- Tension: {atmosphere_data.get('tension_level', 0.5):.2f} (0=calm, 1=tense)
- Formality: {atmosphere_data.get('formality_level', 0.5):.2f} (0=casual, 1=formal)
- Emotional valence: {atmosphere_data.get('emotional_valence', 0.0):.2f} (-1=negative, 1=positive)
- Energy level: {atmosphere_data.get('energy_level', 0.5):.2f} (0=low, 1=high)
- Social cohesion: {atmosphere_data.get('social_cohesion', 0.5):.2f} (0=fragmented, 1=unified)

Entities: {entity_summary}

Generate a vivid description (2-3 paragraphs) capturing:
- The physical sensory experience (sights, sounds, smells)
- The emotional atmosphere and tension
- The social dynamics and interactions
- Historical authenticity and period-appropriate details

Return a JSON object with:
- atmospheric_narrative: string (vivid 2-3 paragraph description)
- dominant_mood: string (e.g., "tense anticipation", "celebratory jubilation")
- sensory_details: array of strings (key sensory observations)
- social_dynamics: string (description of how people interact)
- historical_context: string (period-appropriate cultural notes)"""

        try:
            response = self.service.call(
                system=system_prompt,
                user=user_prompt,
                temperature=0.8,
                max_tokens=1000,
                model=model,
                call_type="generate_scene_atmosphere",
            )

            # Parse JSON response
            import json
            atmosphere_description = json.loads(response.content)

            # Update statistics
            stats = self.service.get_statistics()
            self.token_count = stats.get("logger_stats", {}).get("total_tokens", 0)
            self.cost = stats.get("total_cost", 0.0)

            return atmosphere_description

        except Exception as e:
            # Fallback to basic description
            return {
                "atmospheric_narrative": f"The scene at {environment.get('location', 'this location')} unfolds with {atmosphere_data.get('tension_level', 0.5) > 0.6 and 'palpable tension' or 'calm composure'}.",
                "dominant_mood": "neutral",
                "sensory_details": ["ambient lighting", "period architecture"],
                "social_dynamics": "formal interactions",
                "historical_context": "period-appropriate setting"
            }

    def _generate_scene_atmosphere_legacy(self, timepoint: dict, entities: list, environment: dict, atmosphere_data: dict, model: Optional[str] = None):
        """Legacy implementation - return basic description"""
        return {
            "atmospheric_narrative": "The scene unfolds with historical authenticity.",
            "dominant_mood": "neutral",
            "sensory_details": [],
            "social_dynamics": "interactions occur",
            "historical_context": "period setting"
        }

    def predict_counterfactual_outcome(self, baseline_timeline: dict, intervention: dict, affected_entities: list, model: Optional[str] = None):
        """
        Predict outcomes of counterfactual interventions using LLM.

        Args:
            baseline_timeline: Original timeline information
            intervention: Intervention details
            affected_entities: Entities affected by intervention
            model: Model identifier

        Returns:
            Dict with predicted outcomes and narrative
        """
        if self.use_centralized_service:
            return self._predict_counterfactual_outcome_v2(baseline_timeline, intervention, affected_entities, model)
        else:
            return self._predict_counterfactual_outcome_legacy(baseline_timeline, intervention, affected_entities, model)

    def _predict_counterfactual_outcome_v2(self, baseline_timeline: dict, intervention: dict, affected_entities: list, model: Optional[str] = None):
        """Implementation using centralized service"""

        system_prompt = "You are an expert at analyzing historical causality and predicting counterfactual outcomes based on interventions in historical timelines."

        # Build entity summary
        entity_summary = ', '.join([e.get('entity_id', 'unknown') for e in affected_entities[:10]])

        user_prompt = f"""Analyze the counterfactual outcome of this intervention in a historical timeline.

Baseline Timeline:
- Timeline ID: {baseline_timeline.get('timeline_id', 'unknown')}
- Current events: {baseline_timeline.get('event_summary', 'historical events')}
- Key entities: {baseline_timeline.get('key_entities', [])}

Intervention:
- Type: {intervention.get('type', 'unknown')}
- Target: {intervention.get('target', 'unknown')}
- Description: {intervention.get('description', 'intervention applied')}
- Intervention point: {intervention.get('intervention_point', 'unknown timepoint')}
- Parameters: {intervention.get('parameters', {})}

Affected Entities: {entity_summary}

Predict the counterfactual outcomes by analyzing:
1. Immediate effects of the intervention
2. Ripple effects through causal chains
3. Changes to entity states and relationships
4. Divergence points where timelines meaningfully differ
5. Long-term consequences

Return a JSON object with:
- immediate_effects: array of strings (direct consequences)
- ripple_effects: array of strings (cascading changes)
- entity_state_changes: object mapping entity IDs to predicted changes
- divergence_significance: number 0.0-1.0 (how much timelines differ)
- timeline_narrative: string (2-3 paragraph description of divergent timeline)
- probability_assessment: number 0.0-1.0 (confidence in predictions)
- key_turning_points: array of strings (critical moments of change)"""

        try:
            response = self.service.call(
                system=system_prompt,
                user=user_prompt,
                temperature=0.7,
                max_tokens=1200,
                model=model,
                call_type="predict_counterfactual_outcome",
            )

            # Parse JSON response
            import json
            prediction = json.loads(response.content)

            # Update statistics
            stats = self.service.get_statistics()
            self.token_count = stats.get("logger_stats", {}).get("total_tokens", 0)
            self.cost = stats.get("total_cost", 0.0)

            return prediction

        except Exception as e:
            # Fallback to basic prediction
            return {
                "immediate_effects": [f"Intervention {intervention.get('type')} applied to {intervention.get('target')}"],
                "ripple_effects": ["Cascading changes through causal network"],
                "entity_state_changes": {},
                "divergence_significance": 0.5,
                "timeline_narrative": f"The intervention causes the timeline to diverge at {intervention.get('intervention_point')}.",
                "probability_assessment": 0.5,
                "key_turning_points": [intervention.get('intervention_point', 'intervention point')]
            }

    def _predict_counterfactual_outcome_legacy(self, baseline_timeline: dict, intervention: dict, affected_entities: list, model: Optional[str] = None):
        """Legacy implementation - return basic prediction"""
        return {
            "immediate_effects": ["Intervention applied"],
            "ripple_effects": ["Timeline diverges"],
            "entity_state_changes": {},
            "divergence_significance": 0.5,
            "timeline_narrative": "The timeline diverges from baseline.",
            "probability_assessment": 0.5,
            "key_turning_points": []
        }

    def generate_dialog(self, prompt: str, max_tokens: int = 2000, model: Optional[str] = None):
        """
        Generate dialog with structured output.

        Args:
            prompt: Dialog generation prompt
            max_tokens: Max tokens to generate
            model: Model identifier

        Returns:
            DialogData instance
        """
        if self.use_centralized_service:
            return self._generate_dialog_v2(prompt, max_tokens, model)
        else:
            return self._generate_dialog_legacy(prompt, max_tokens, model)

    def _generate_dialog_v2(self, prompt: str, max_tokens: int = 2000, model: Optional[str] = None):
        """Implementation using centralized service"""
        from schemas import DialogData

        system_prompt = "You are an expert at generating realistic historical dialogs."

        result = self.service.structured_call(
            system=system_prompt,
            user=prompt,
            schema=DialogData,
            temperature=0.7,
            max_tokens=max_tokens,
            model=model,
            call_type="generate_dialog",
        )

        return result

    def _generate_dialog_legacy(self, prompt: str, max_tokens: int = 2000, model: Optional[str] = None):
        """Legacy implementation"""
        if self.dry_run:
            return self._mock_dialog_generation()

        from llm import LLMClient as LegacyClient
        legacy = LegacyClient(self.api_key, self.base_url, self.dry_run)
        return legacy.generate_dialog(prompt, max_tokens, model)

    def _heuristic_relevance_score(self, query: str, knowledge_item: str) -> float:
        """Fallback heuristic relevance scoring"""
        query_words = set(query.lower().split())
        knowledge_words = set(knowledge_item.lower().split())
        overlap = len(query_words.intersection(knowledge_words))
        total_words = len(query_words.union(knowledge_words))
        return min(1.0, overlap / max(1, total_words / 2))

    def _mock_entity_population(self, entity_schema: Dict, previous_knowledge: List[str] = None) -> EntityPopulation:
        """Deterministic mock for dry-run mode"""
        import hashlib
        seed = int(hashlib.md5(entity_schema['entity_id'].encode()).hexdigest(), 16) % 10000
        np.random.seed(seed)

        if previous_knowledge:
            existing_count = len(previous_knowledge)
            new_facts = [f"fact_{existing_count + i}" for i in range(3)]
            knowledge_state = previous_knowledge + new_facts
        else:
            knowledge_state = [f"fact_{i}" for i in range(5)]

        return EntityPopulation(
            entity_id=entity_schema['entity_id'],
            knowledge_state=knowledge_state,
            energy_budget=np.random.uniform(50, 100),
            personality_traits=np.random.uniform(-1, 1, 5).tolist(),
            temporal_awareness=f"Aware of events up to {entity_schema.get('timestamp', 'unknown')}",
            confidence=0.8
        )

    def _mock_dialog_generation(self):
        """Deterministic mock for dialog generation"""
        from schemas import DialogTurn, DialogData
        from datetime import datetime

        turns = []
        speakers = ["washington", "jefferson", "hamilton", "adams"]
        base_time = datetime.now()

        for i in range(8):
            speaker = speakers[i % len(speakers)]
            turn = DialogTurn(
                speaker=speaker,
                content=f"This is a mock dialog turn {i+1} from {speaker} about historical matters.",
                timestamp=base_time.replace(second=i*30),
                emotional_tone="neutral",
                knowledge_references=["mock_fact_1", "mock_fact_2"],
                confidence=0.9,
                physical_state_influence="none"
            )
            turns.append(turn)

        return DialogData(
            turns=turns,
            total_duration=240,
            information_exchanged=["mock_fact_1", "mock_fact_2", "mock_fact_3"],
            relationship_impacts={"washington_jefferson": 0.1, "hamilton_adams": -0.05},
            atmosphere_evolution=[]
        )

    @classmethod
    def from_hydra_config(cls, cfg: Any, use_centralized_service: bool = True) -> "LLMClient":
        """
        Create client from Hydra configuration.

        Args:
            cfg: Hydra config object
            use_centralized_service: Use new centralized service

        Returns:
            Configured LLMClient instance
        """
        if use_centralized_service and hasattr(cfg, 'llm_service'):
            # Use new service config
            service_config = LLMServiceConfig.from_hydra_config(cfg)
            return cls(
                api_key=cfg.llm.api_key,
                base_url=cfg.llm.base_url,
                dry_run=cfg.llm.dry_run,
                default_model=cfg.llm.model,
                use_centralized_service=True,
                service_config=service_config,
            )
        else:
            # Use legacy config
            return cls(
                api_key=cfg.llm.api_key,
                base_url=cfg.llm.base_url,
                dry_run=cfg.llm.dry_run,
                default_model=cfg.llm.model,
                model_cache_ttl_hours=cfg.llm.model_cache_ttl_hours,
                use_centralized_service=False,
            )
