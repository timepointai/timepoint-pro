"""
Provider Protocol - Abstract interface for LLM providers

Defines the contract that all LLM provider implementations must satisfy.
"""

from typing import Protocol, Dict, Any, Optional, Type
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized LLM response structure"""
    content: str
    model: str
    tokens_used: Dict[str, int]  # {"prompt": N, "completion": N, "total": N}
    cost_usd: float
    latency_ms: float
    success: bool
    error: Optional[str] = None
    raw_response: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(Protocol):
    """
    Protocol defining the interface for LLM providers.

    Any provider (Mirascope, custom OpenRouter, test) must implement these methods.
    """

    def call(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 0.9,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make a chat completion call to the LLM.

        Args:
            system: System prompt
            user: User prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            model: Model identifier (uses default if None)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with content, metadata, and cost tracking
        """
        ...

    def structured_call(
        self,
        system: str,
        user: str,
        schema: Type[BaseModel],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseModel:
        """
        Make a structured output call that returns a Pydantic model.

        Args:
            system: System prompt
            user: User prompt
            schema: Pydantic model class for structured output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model identifier
            **kwargs: Additional parameters

        Returns:
            Instance of the schema class populated from LLM response
        """
        ...

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming responses"""
        ...

    def get_provider_name(self) -> str:
        """Get the name of this provider (e.g., 'mirascope', 'openrouter', 'test')"""
        ...

    def get_default_model(self) -> str:
        """Get the default model identifier for this provider"""
        ...

    def list_available_models(self) -> list[str]:
        """List available models for this provider"""
        ...
