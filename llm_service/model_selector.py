"""
Model Selector - Granular per-action and per-agent model selection

This module provides intelligent model selection based on:
- Action type requirements (dialog, math, json, etc.)
- Model capabilities (context window, structured output, reasoning)
- Cost/performance tradeoffs
- License requirements (open-source only, commercial synthetic data OK)

All models must be:
1. Available on OpenRouter
2. Open source with licenses permitting commercial synthetic data generation
3. NOT from major labs that prohibit synthetic data (no OpenAI, Anthropic, Google)

Usage:
    from llm_service.model_selector import ModelSelector, ActionType

    selector = ModelSelector()
    model = selector.select_model(ActionType.DIALOG_SYNTHESIS)
    # Returns best model for dialog generation

    # Or with specific requirements
    model = selector.select_model(
        ActionType.STRUCTURED_OUTPUT,
        requirements={"min_context_tokens": 32000}
    )
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """Capabilities that models may have"""
    # Output capabilities
    STRUCTURED_JSON = auto()      # Reliable JSON output
    LONG_FORM_TEXT = auto()       # Good at long narrative generation
    DIALOG_GENERATION = auto()    # Natural conversational output
    CODE_GENERATION = auto()      # Can write/analyze code

    # Reasoning capabilities
    MATHEMATICAL = auto()         # Strong math/calculation ability
    LOGICAL_REASONING = auto()    # Step-by-step reasoning
    CAUSAL_REASONING = auto()     # Understanding cause/effect
    TEMPORAL_REASONING = auto()   # Time-aware reasoning

    # Context capabilities
    LARGE_CONTEXT = auto()        # 32k+ context window
    VERY_LARGE_CONTEXT = auto()   # 128k+ context window

    # Performance characteristics
    FAST_INFERENCE = auto()       # Low latency
    COST_EFFICIENT = auto()       # Lower cost per token
    HIGH_QUALITY = auto()         # Best output quality

    # Memory/state
    STATEFUL = auto()             # Can maintain conversation state
    INSTRUCTION_FOLLOWING = auto() # Good at following complex instructions


class ActionType(Enum):
    """Types of actions that require LLM calls"""
    # Entity operations
    ENTITY_POPULATION = auto()         # Populate entity tensors
    ENTITY_ENRICHMENT = auto()         # Enrich with background
    PERSONALITY_INFERENCE = auto()     # Infer personality traits

    # Dialog operations
    DIALOG_SYNTHESIS = auto()          # Generate conversations
    DIALOG_CONTINUATION = auto()       # Continue existing dialog

    # Temporal operations
    TEMPORAL_REASONING = auto()        # Causal chain reasoning
    COUNTERFACTUAL_PREDICTION = auto() # What-if scenarios
    PROSPECTION = auto()               # Future prediction

    # Scene operations
    SCENE_ATMOSPHERE = auto()          # Generate scene descriptions
    CROWD_DYNAMICS = auto()            # Model group behavior

    # Validation operations
    CONSISTENCY_CHECK = auto()         # Validate temporal consistency
    RELEVANCE_SCORING = auto()         # Score relevance

    # Structured data
    STRUCTURED_OUTPUT = auto()         # Generic structured output
    SCHEMA_EXTRACTION = auto()         # Extract to schema

    # Summary/analysis
    SUMMARIZATION = auto()             # Summarize content
    NARRATIVE_EXPORT = auto()          # Generate narrative

    # Knowledge operations (M19)
    KNOWLEDGE_EXTRACTION = auto()      # Extract knowledge items from dialog


@dataclass
class ModelProfile:
    """Profile of a model's capabilities and characteristics"""
    model_id: str                      # OpenRouter model identifier
    display_name: str                  # Human-readable name
    provider: str                      # Provider (meta, qwen, deepseek, etc.)
    license: str                       # License type

    # Capabilities
    capabilities: Set[ModelCapability] = field(default_factory=set)

    # Context window
    context_tokens: int = 4096         # Max context tokens

    # Performance
    relative_speed: float = 1.0        # 1.0 = baseline, >1 = faster
    relative_cost: float = 1.0         # 1.0 = baseline, <1 = cheaper
    relative_quality: float = 1.0      # 1.0 = baseline, >1 = better

    # Restrictions
    allows_synthetic_data: bool = True # Can use for synthetic data generation
    allows_commercial: bool = True     # Commercial use allowed

    # Notes
    notes: str = ""


# =============================================================================
# MODEL REGISTRY - Open Source Models for Commercial Synthetic Data
# =============================================================================

MODEL_REGISTRY: Dict[str, ModelProfile] = {
    # =========================================================================
    # LLAMA FAMILY (Meta) - Llama 3.x license allows commercial use
    # Note: Llama license restricts using outputs to train non-Llama models
    # =========================================================================
    "meta-llama/llama-3.1-8b-instruct": ModelProfile(
        model_id="meta-llama/llama-3.1-8b-instruct",
        display_name="Llama 3.1 8B",
        provider="meta",
        license="llama3.1",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.FAST_INFERENCE,
            ModelCapability.COST_EFFICIENT,
        },
        context_tokens=128000,
        relative_speed=2.0,
        relative_cost=0.3,
        relative_quality=0.7,
        notes="Fast, cheap, good for simple tasks"
    ),

    "meta-llama/llama-3.1-70b-instruct": ModelProfile(
        model_id="meta-llama/llama-3.1-70b-instruct",
        display_name="Llama 3.1 70B",
        provider="meta",
        license="llama3.1",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.DIALOG_GENERATION,
            ModelCapability.LOGICAL_REASONING,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.VERY_LARGE_CONTEXT,
            ModelCapability.HIGH_QUALITY,
        },
        context_tokens=128000,
        relative_speed=1.0,
        relative_cost=1.0,
        relative_quality=1.0,
        notes="Excellent general-purpose model, good balance"
    ),

    "meta-llama/llama-3.1-405b-instruct": ModelProfile(
        model_id="meta-llama/llama-3.1-405b-instruct",
        display_name="Llama 3.1 405B",
        provider="meta",
        license="llama3.1",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.DIALOG_GENERATION,
            ModelCapability.LOGICAL_REASONING,
            ModelCapability.MATHEMATICAL,
            ModelCapability.CAUSAL_REASONING,
            ModelCapability.TEMPORAL_REASONING,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.VERY_LARGE_CONTEXT,
            ModelCapability.HIGH_QUALITY,
            ModelCapability.LONG_FORM_TEXT,
        },
        context_tokens=128000,
        relative_speed=0.5,
        relative_cost=3.0,
        relative_quality=1.3,
        notes="Highest quality Llama, use for complex reasoning"
    ),

    # Llama 4 Scout (newer)
    "meta-llama/llama-4-scout": ModelProfile(
        model_id="meta-llama/llama-4-scout",
        display_name="Llama 4 Scout",
        provider="meta",
        license="llama4",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.DIALOG_GENERATION,
            ModelCapability.LOGICAL_REASONING,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.FAST_INFERENCE,
        },
        context_tokens=128000,
        relative_speed=1.5,
        relative_cost=0.8,
        relative_quality=1.1,
        notes="Newer Llama 4 model, good speed/quality balance"
    ),

    # =========================================================================
    # QWEN FAMILY (Alibaba) - Apache 2.0 / Qwen License
    # Note: Qwen license has commercial use restrictions for >100M users
    # =========================================================================
    "qwen/qwen-2.5-7b-instruct": ModelProfile(
        model_id="qwen/qwen-2.5-7b-instruct",
        display_name="Qwen 2.5 7B",
        provider="qwen",
        license="qwen",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.CODE_GENERATION,
            ModelCapability.FAST_INFERENCE,
            ModelCapability.COST_EFFICIENT,
        },
        context_tokens=32768,
        relative_speed=2.0,
        relative_cost=0.25,
        relative_quality=0.65,
        notes="Very fast, good for simple JSON tasks"
    ),

    "qwen/qwen-2.5-72b-instruct": ModelProfile(
        model_id="qwen/qwen-2.5-72b-instruct",
        display_name="Qwen 2.5 72B",
        provider="qwen",
        license="qwen",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.DIALOG_GENERATION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.MATHEMATICAL,
            ModelCapability.LOGICAL_REASONING,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.HIGH_QUALITY,
        },
        context_tokens=32768,
        relative_speed=1.0,
        relative_cost=0.9,
        relative_quality=1.05,
        notes="Strong alternative to Llama 70B, good math"
    ),

    "qwen/qwq-32b-preview": ModelProfile(
        model_id="qwen/qwq-32b-preview",
        display_name="QwQ 32B (Reasoning)",
        provider="qwen",
        license="qwen",
        capabilities={
            ModelCapability.MATHEMATICAL,
            ModelCapability.LOGICAL_REASONING,
            ModelCapability.CAUSAL_REASONING,
            ModelCapability.TEMPORAL_REASONING,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
        },
        context_tokens=32768,
        relative_speed=0.7,
        relative_cost=1.2,
        relative_quality=1.15,
        notes="Specialized reasoning model, excellent for causal/temporal"
    ),

    # =========================================================================
    # DEEPSEEK FAMILY - MIT License (most permissive!)
    # =========================================================================
    "deepseek/deepseek-chat": ModelProfile(
        model_id="deepseek/deepseek-chat",
        display_name="DeepSeek Chat",
        provider="deepseek",
        license="MIT",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.DIALOG_GENERATION,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.COST_EFFICIENT,
        },
        context_tokens=32768,
        relative_speed=1.3,
        relative_cost=0.5,
        relative_quality=0.9,
        notes="MIT license - most permissive for synthetic data"
    ),

    "deepseek/deepseek-r1": ModelProfile(
        model_id="deepseek/deepseek-r1",
        display_name="DeepSeek R1 (Reasoning)",
        provider="deepseek",
        license="MIT",
        capabilities={
            ModelCapability.MATHEMATICAL,
            ModelCapability.LOGICAL_REASONING,
            ModelCapability.CAUSAL_REASONING,
            ModelCapability.TEMPORAL_REASONING,
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.HIGH_QUALITY,
        },
        context_tokens=64000,
        relative_speed=0.6,
        relative_cost=1.5,
        relative_quality=1.25,
        notes="MIT license, excellent reasoning, best for complex causal chains"
    ),

    # =========================================================================
    # MISTRAL FAMILY - Apache 2.0
    # =========================================================================
    "mistralai/mistral-7b-instruct": ModelProfile(
        model_id="mistralai/mistral-7b-instruct",
        display_name="Mistral 7B",
        provider="mistral",
        license="Apache-2.0",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.FAST_INFERENCE,
            ModelCapability.COST_EFFICIENT,
            ModelCapability.INSTRUCTION_FOLLOWING,
        },
        context_tokens=32768,
        relative_speed=2.5,
        relative_cost=0.2,
        relative_quality=0.6,
        notes="Apache 2.0, very fast and cheap"
    ),

    "mistralai/mixtral-8x7b-instruct": ModelProfile(
        model_id="mistralai/mixtral-8x7b-instruct",
        display_name="Mixtral 8x7B",
        provider="mistral",
        license="Apache-2.0",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.DIALOG_GENERATION,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.FAST_INFERENCE,
        },
        context_tokens=32768,
        relative_speed=1.5,
        relative_cost=0.6,
        relative_quality=0.85,
        notes="Apache 2.0, good MoE model, fast inference"
    ),

    "mistralai/mixtral-8x22b-instruct": ModelProfile(
        model_id="mistralai/mixtral-8x22b-instruct",
        display_name="Mixtral 8x22B",
        provider="mistral",
        license="Apache-2.0",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.DIALOG_GENERATION,
            ModelCapability.LOGICAL_REASONING,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.HIGH_QUALITY,
        },
        context_tokens=65536,
        relative_speed=1.0,
        relative_cost=1.1,
        relative_quality=1.05,
        notes="Apache 2.0, strong general-purpose MoE"
    ),

    # =========================================================================
    # GOOGLE GEMINI (Preview) - Use with explicit --gemini-flash flag
    # Note: Google TOS may restrict synthetic data generation. Use when:
    # - Speed is critical (optimized for agentic workflows)
    # - You need 1M context window
    # - You explicitly accept TOS implications
    # =========================================================================
    "google/gemini-3-flash-preview": ModelProfile(
        model_id="google/gemini-3-flash-preview",
        display_name="Gemini 3 Flash Preview",
        provider="google",
        license="Google TOS",
        capabilities={
            ModelCapability.STRUCTURED_JSON,
            ModelCapability.DIALOG_GENERATION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.LOGICAL_REASONING,
            ModelCapability.INSTRUCTION_FOLLOWING,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.VERY_LARGE_CONTEXT,
            ModelCapability.FAST_INFERENCE,
            ModelCapability.HIGH_QUALITY,
        },
        context_tokens=1048576,  # 1M tokens!
        relative_speed=2.5,      # Optimized for low latency
        relative_cost=0.5,       # $0.50/M input, $3.00/M output
        relative_quality=1.2,    # High quality reasoning
        allows_synthetic_data=False,  # TOS restriction - explicit opt-in only
        notes="1M context, multimodal, fast inference. Use --gemini-flash flag for explicit selection."
    ),
}


# =============================================================================
# ACTION TO CAPABILITY MAPPING
# =============================================================================

ACTION_REQUIREMENTS: Dict[ActionType, Dict[str, Any]] = {
    # Entity operations need good instruction following
    ActionType.ENTITY_POPULATION: {
        "required": {ModelCapability.STRUCTURED_JSON, ModelCapability.INSTRUCTION_FOLLOWING},
        "preferred": {ModelCapability.HIGH_QUALITY},
        "min_context_tokens": 4096,
    },

    ActionType.ENTITY_ENRICHMENT: {
        "required": {ModelCapability.LONG_FORM_TEXT},
        "preferred": {ModelCapability.HIGH_QUALITY},
        "min_context_tokens": 8192,
    },

    ActionType.PERSONALITY_INFERENCE: {
        "required": {ModelCapability.STRUCTURED_JSON, ModelCapability.LOGICAL_REASONING},
        "preferred": {ModelCapability.HIGH_QUALITY},
        "min_context_tokens": 4096,
    },

    # Dialog needs natural language generation
    ActionType.DIALOG_SYNTHESIS: {
        "required": {ModelCapability.DIALOG_GENERATION, ModelCapability.STRUCTURED_JSON},
        "preferred": {ModelCapability.HIGH_QUALITY, ModelCapability.LARGE_CONTEXT},
        "min_context_tokens": 16384,
    },

    ActionType.DIALOG_CONTINUATION: {
        "required": {ModelCapability.DIALOG_GENERATION},
        "preferred": {ModelCapability.LARGE_CONTEXT},
        "min_context_tokens": 32768,
    },

    # Temporal reasoning needs strong causal models
    ActionType.TEMPORAL_REASONING: {
        "required": {ModelCapability.CAUSAL_REASONING, ModelCapability.TEMPORAL_REASONING},
        "preferred": {ModelCapability.HIGH_QUALITY, ModelCapability.LOGICAL_REASONING},
        "min_context_tokens": 16384,
    },

    ActionType.COUNTERFACTUAL_PREDICTION: {
        "required": {ModelCapability.CAUSAL_REASONING, ModelCapability.LOGICAL_REASONING},
        "preferred": {ModelCapability.HIGH_QUALITY},
        "min_context_tokens": 16384,
    },

    ActionType.PROSPECTION: {
        "required": {ModelCapability.TEMPORAL_REASONING, ModelCapability.STRUCTURED_JSON},
        "preferred": {ModelCapability.CAUSAL_REASONING},
        "min_context_tokens": 8192,
    },

    # Scene operations need creative generation
    ActionType.SCENE_ATMOSPHERE: {
        "required": {ModelCapability.LONG_FORM_TEXT},
        "preferred": {ModelCapability.HIGH_QUALITY},
        "min_context_tokens": 4096,
    },

    ActionType.CROWD_DYNAMICS: {
        "required": {ModelCapability.STRUCTURED_JSON},
        "preferred": {ModelCapability.LOGICAL_REASONING},
        "min_context_tokens": 8192,
    },

    # Validation needs fast, accurate responses
    ActionType.CONSISTENCY_CHECK: {
        "required": {ModelCapability.LOGICAL_REASONING, ModelCapability.STRUCTURED_JSON},
        "preferred": {ModelCapability.FAST_INFERENCE},
        "min_context_tokens": 16384,
    },

    ActionType.RELEVANCE_SCORING: {
        "required": {ModelCapability.INSTRUCTION_FOLLOWING},
        "preferred": {ModelCapability.FAST_INFERENCE, ModelCapability.COST_EFFICIENT},
        "min_context_tokens": 2048,
    },

    # Structured output needs reliable JSON
    ActionType.STRUCTURED_OUTPUT: {
        "required": {ModelCapability.STRUCTURED_JSON},
        "preferred": {ModelCapability.INSTRUCTION_FOLLOWING},
        "min_context_tokens": 4096,
    },

    ActionType.SCHEMA_EXTRACTION: {
        "required": {ModelCapability.STRUCTURED_JSON, ModelCapability.INSTRUCTION_FOLLOWING},
        "preferred": {ModelCapability.HIGH_QUALITY},
        "min_context_tokens": 8192,
    },

    # Summary/narrative
    ActionType.SUMMARIZATION: {
        "required": {ModelCapability.INSTRUCTION_FOLLOWING},
        "preferred": {ModelCapability.LARGE_CONTEXT, ModelCapability.COST_EFFICIENT},
        "min_context_tokens": 32768,
    },

    ActionType.NARRATIVE_EXPORT: {
        "required": {ModelCapability.LONG_FORM_TEXT},
        "preferred": {ModelCapability.HIGH_QUALITY},
        "min_context_tokens": 8192,
    },

    # Knowledge operations (M19)
    # NOTE: Avoid reasoning models (DeepSeek R1, QwQ) - they output thinking tokens that break JSON
    ActionType.KNOWLEDGE_EXTRACTION: {
        "required": {ModelCapability.STRUCTURED_JSON, ModelCapability.INSTRUCTION_FOLLOWING},
        "preferred": {ModelCapability.HIGH_QUALITY, ModelCapability.LARGE_CONTEXT, ModelCapability.DIALOG_GENERATION},
        "min_context_tokens": 16384,  # Need context for causal graph + dialog
    },
}


class ModelSelector:
    """
    Intelligent model selector for per-action model selection.

    Selects the best model based on:
    1. Required capabilities for the action
    2. Preferred capabilities (nice to have)
    3. Context window requirements
    4. Cost/quality/speed preferences

    Example:
        selector = ModelSelector()

        # Get best model for dialog synthesis
        model = selector.select_model(ActionType.DIALOG_SYNTHESIS)

        # Get model with specific requirements
        model = selector.select_model(
            ActionType.TEMPORAL_REASONING,
            requirements={"min_context_tokens": 64000},
            prefer_quality=True
        )

        # Get fallback chain for retries
        models = selector.get_fallback_chain(ActionType.ENTITY_POPULATION)
    """

    def __init__(
        self,
        registry: Optional[Dict[str, ModelProfile]] = None,
        default_model: str = "meta-llama/llama-3.1-70b-instruct"
    ):
        """
        Initialize model selector.

        Args:
            registry: Custom model registry (uses default if None)
            default_model: Fallback model if no match found
        """
        self.registry = registry or MODEL_REGISTRY
        self.default_model = default_model

        # Build capability index for fast lookup
        self._capability_index: Dict[ModelCapability, Set[str]] = {}
        for model_id, profile in self.registry.items():
            for cap in profile.capabilities:
                if cap not in self._capability_index:
                    self._capability_index[cap] = set()
                self._capability_index[cap].add(model_id)

        # Restricted model prefixes - these may cause issues with synthetic data
        # or have API-specific behaviors (like extended thinking) that aren't supported
        self._restricted_prefixes = [
            "anthropic/",   # Claude models - extended thinking blocks can cause API errors
            "openai/",      # OpenAI - TOS prohibits synthetic data generation
            "google/",      # Google - TOS prohibits synthetic data generation
        ]

    def _check_restricted_model(self, model_id: str) -> bool:
        """
        Check if a model ID is from a restricted provider and log warnings.

        Restricted models include:
        - Anthropic (Claude) - Extended thinking blocks can cause session state errors
        - OpenAI - TOS prohibits synthetic data generation
        - Google - TOS prohibits synthetic data generation

        Args:
            model_id: Model identifier to check

        Returns:
            True if model is restricted (warning logged), False otherwise
        """
        model_lower = model_id.lower()

        for prefix in self._restricted_prefixes:
            if model_lower.startswith(prefix):
                provider = prefix.rstrip("/")

                if provider == "anthropic":
                    logger.warning(
                        f"⚠️  Model '{model_id}' is from Anthropic. Note: Extended thinking "
                        f"features can cause 'thinking blocks cannot be modified' errors if "
                        f"conversation state accumulates. Consider using open-source models."
                    )
                else:
                    logger.warning(
                        f"⚠️  Model '{model_id}' is from {provider}. TOS may prohibit "
                        f"synthetic data generation. Consider using open-source models "
                        f"from the registry (Llama, Qwen, DeepSeek, Mistral)."
                    )
                return True

        return False

    def select_model(
        self,
        action: ActionType,
        requirements: Optional[Dict[str, Any]] = None,
        prefer_quality: bool = False,
        prefer_speed: bool = False,
        prefer_cost: bool = False,
        exclude_models: Optional[Set[str]] = None,
    ) -> str:
        """
        Select the best model for an action.

        Args:
            action: Type of action to perform
            requirements: Additional requirements (e.g., min_context_tokens)
            prefer_quality: Prefer higher quality over speed/cost
            prefer_speed: Prefer faster inference
            prefer_cost: Prefer lower cost
            exclude_models: Models to exclude (e.g., for retry chains)

        Returns:
            Model ID string (e.g., "meta-llama/llama-3.1-70b-instruct")
        """
        exclude_models = exclude_models or set()
        requirements = requirements or {}

        # Get action requirements
        action_reqs = ACTION_REQUIREMENTS.get(action, {})
        required_caps = action_reqs.get("required", set())
        preferred_caps = action_reqs.get("preferred", set())
        min_context = max(
            action_reqs.get("min_context_tokens", 0),
            requirements.get("min_context_tokens", 0)
        )

        # Filter models by required capabilities and context
        candidates = []
        for model_id, profile in self.registry.items():
            if model_id in exclude_models:
                continue
            if not profile.allows_commercial or not profile.allows_synthetic_data:
                continue
            if not required_caps.issubset(profile.capabilities):
                continue
            if profile.context_tokens < min_context:
                continue
            candidates.append((model_id, profile))

        if not candidates:
            # Fall back to default model if no match
            return self.default_model

        # Score candidates
        scored = []
        for model_id, profile in candidates:
            score = 0.0

            # Preferred capabilities bonus
            matched_preferred = preferred_caps & profile.capabilities
            score += len(matched_preferred) * 0.2

            # Quality/speed/cost preferences
            if prefer_quality:
                score += profile.relative_quality * 0.5
            elif prefer_speed:
                score += profile.relative_speed * 0.5
            elif prefer_cost:
                score += (1.0 / profile.relative_cost) * 0.5
            else:
                # Balanced scoring
                score += profile.relative_quality * 0.2
                score += profile.relative_speed * 0.15
                score += (1.0 / profile.relative_cost) * 0.15

            # Context window bonus (prefer more context headroom)
            if profile.context_tokens > min_context * 2:
                score += 0.1

            scored.append((score, model_id))

        # Return highest scoring model
        scored.sort(reverse=True)
        return scored[0][1]

    def get_fallback_chain(
        self,
        action: ActionType,
        chain_length: int = 3,
        requirements: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Get a chain of models for retry fallback.

        Returns models in order of preference, with diversity to handle
        different failure modes.

        Args:
            action: Type of action
            chain_length: Number of models in chain
            requirements: Additional requirements

        Returns:
            List of model IDs in fallback order
        """
        chain = []
        excluded = set()

        # First: quality-preferred model
        model = self.select_model(
            action, requirements, prefer_quality=True, exclude_models=excluded
        )
        chain.append(model)
        excluded.add(model)

        if len(chain) >= chain_length:
            return chain[:chain_length]

        # Second: balanced model (different provider if possible)
        model = self.select_model(
            action, requirements, exclude_models=excluded
        )
        chain.append(model)
        excluded.add(model)

        if len(chain) >= chain_length:
            return chain[:chain_length]

        # Third: cost-efficient model as final fallback
        model = self.select_model(
            action, requirements, prefer_cost=True, exclude_models=excluded
        )
        chain.append(model)

        return chain[:chain_length]

    def get_model_profile(self, model_id: str) -> Optional[ModelProfile]:
        """Get profile for a specific model."""
        return self.registry.get(model_id)

    def list_models_with_capability(
        self,
        capability: ModelCapability
    ) -> List[str]:
        """List all models with a specific capability."""
        return list(self._capability_index.get(capability, set()))

    @lru_cache(maxsize=128)
    def get_recommended_model(
        self,
        action: ActionType,
        context_hint: str = "balanced"
    ) -> str:
        """
        Get recommended model with caching.

        Args:
            action: Action type
            context_hint: "quality", "speed", "cost", or "balanced"

        Returns:
            Model ID
        """
        prefer_quality = context_hint == "quality"
        prefer_speed = context_hint == "speed"
        prefer_cost = context_hint == "cost"

        return self.select_model(
            action,
            prefer_quality=prefer_quality,
            prefer_speed=prefer_speed,
            prefer_cost=prefer_cost
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_selector: Optional[ModelSelector] = None


def get_default_selector() -> ModelSelector:
    """Get the default model selector instance."""
    global _default_selector
    if _default_selector is None:
        _default_selector = ModelSelector()
    return _default_selector


def select_model_for_action(
    action: ActionType,
    **kwargs
) -> str:
    """
    Convenience function to select model for an action.

    Args:
        action: Action type
        **kwargs: Additional arguments for select_model

    Returns:
        Model ID
    """
    return get_default_selector().select_model(action, **kwargs)


def get_fallback_models(
    action: ActionType,
    chain_length: int = 3
) -> List[str]:
    """
    Convenience function to get fallback chain.

    Args:
        action: Action type
        chain_length: Number of models in chain

    Returns:
        List of model IDs
    """
    return get_default_selector().get_fallback_chain(action, chain_length)


def check_model_restrictions(model_id: str) -> bool:
    """
    Check if a model ID is from a restricted provider.

    Restricted providers include:
    - Anthropic (Claude): Extended thinking can cause session state errors
    - OpenAI: TOS prohibits synthetic data generation
    - Google: TOS prohibits synthetic data generation

    Use this to validate externally-provided model IDs before making API calls.

    Args:
        model_id: Model identifier to check (e.g., "anthropic/claude-3-opus")

    Returns:
        True if model is restricted (warning logged), False otherwise

    Example:
        >>> if check_model_restrictions(user_provided_model):
        ...     print("Using restricted model - proceed with caution")
    """
    return get_default_selector()._check_restricted_model(model_id)
