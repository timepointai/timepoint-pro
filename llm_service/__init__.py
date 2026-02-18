"""
LLM Service - Centralized LLM integration layer for Timepoint-Pro

This package provides a unified interface for LLM operations with:
- Multiple provider support (Mirascope, custom OpenRouter, test providers)
- Comprehensive error handling and retry logic
- Input bleaching and output sanitization
- Structured logging and cost tracking
- Session management and context injection
- Flexible parameterization and configuration
- **Intelligent per-action model selection** (NEW)

Model Selection:
    The model_selector module provides intelligent model selection based on:
    - Action type (dialog, entity population, reasoning, etc.)
    - Required capabilities (JSON output, math, large context)
    - Quality/speed/cost preferences
    - Automatic fallback chains

    Example:
        from llm_service import LLMService, ActionType

        service = LLMService(config)

        # Let the service pick the best model for dialog
        response = service.call_with_action(
            action=ActionType.DIALOG_SYNTHESIS,
            system="You are a dialog generator",
            user="Generate a conversation"
        )

        # Or select model manually
        model = service.select_model(ActionType.TEMPORAL_REASONING)
"""

from llm_service.provider import LLMProvider, LLMResponse
from llm_service.service import LLMService
from llm_service.config import LLMServiceConfig
from llm_service.model_selector import (
    ModelSelector,
    ModelCapability,
    ActionType,
    ModelProfile,
    MODEL_REGISTRY,
    ACTION_REQUIREMENTS,
    select_model_for_action,
    get_fallback_models,
)

__all__ = [
    # Core service
    "LLMProvider",
    "LLMResponse",
    "LLMService",
    "LLMServiceConfig",
    # Model selection
    "ModelSelector",
    "ModelCapability",
    "ActionType",
    "ModelProfile",
    "MODEL_REGISTRY",
    "ACTION_REQUIREMENTS",
    # Convenience functions
    "select_model_for_action",
    "get_fallback_models",
]
