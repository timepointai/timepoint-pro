"""
Custom OpenRouter Provider - Direct HTTP integration

Wraps the existing OpenRouterClient for backward compatibility.
"""

from typing import Type, Optional, Dict, Any
from pydantic import BaseModel
import time
import json

from llm_service.provider import LLMProvider, LLMResponse
from llm_service.response_parser import ResponseParser

# Import existing client from llm.py
import sys
import os
# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from llm import OpenRouterClient, ModelManager


class CustomOpenRouterProvider:
    """
    Provider implementation using custom OpenRouter HTTP client.

    Wraps existing OpenRouterClient for compatibility while conforming
    to the LLMProvider protocol.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: Optional[str] = None,
        model_cache_ttl_hours: int = 24,
    ):
        """
        Initialize custom provider.

        Args:
            api_key: OpenRouter API key
            base_url: API base URL
            default_model: Default model identifier
            model_cache_ttl_hours: Model cache TTL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenRouterClient(api_key=api_key, base_url=base_url)
        self.model_manager = ModelManager(api_key, model_cache_ttl_hours)

        # Set default model
        if default_model:
            self.default_model = default_model
        else:
            self.default_model = self.model_manager.get_default_model()

        self.parser = ResponseParser(strict=False)

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
        """Make a chat completion call"""
        selected_model = model or self.default_model
        start_time = time.time()

        try:
            # Build messages
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": user})

            # Make API call
            response = self.client.create(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
            )

            # Extract content
            content = response["choices"][0]["message"]["content"]

            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            tokens_used = {
                "prompt": response.get("usage", {}).get("prompt_tokens", 0),
                "completion": response.get("usage", {}).get("completion_tokens", 0),
                "total": response.get("usage", {}).get("total_tokens", 0),
            }

            # Estimate cost (rough approximation)
            cost_usd = self._estimate_cost(tokens_used, selected_model)

            return LLMResponse(
                content=content,
                model=selected_model,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=True,
                raw_response=response,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return LLMResponse(
                content="",
                model=selected_model,
                tokens_used={"prompt": 0, "completion": 0, "total": 0},
                cost_usd=0.0,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )

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
        """Make a structured output call"""
        # Add schema instruction to prompt
        from llm_service.prompt_manager import PromptManager

        prompt_mgr = PromptManager()
        schema_prompt = prompt_mgr.schema_to_prompt(schema)
        enhanced_user = f"{user}\n\n{schema_prompt}"

        # Make regular call
        response = self.call(
            system=system,
            user=enhanced_user,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            **kwargs
        )

        if not response.success:
            raise Exception(f"LLM call failed: {response.error}")

        # Parse response into schema
        try:
            return self.parser.parse_structured(response.content, schema, allow_partial=True)
        except Exception as e:
            raise Exception(f"Failed to parse structured response: {e}")

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming"""
        return False  # Not implemented in current client

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "custom_openrouter"

    def get_default_model(self) -> str:
        """Get default model"""
        return self.default_model

    def list_available_models(self) -> list[str]:
        """List available models"""
        models = self.model_manager.get_llama_models()
        return [model["id"] for model in models]

    def _estimate_cost(self, tokens_used: Dict[str, int], model: str) -> float:
        """Estimate API cost in USD"""
        # Rough cost estimates per 1M tokens
        cost_per_million = {
            "70b": 0.60,  # ~$0.60 per 1M tokens
            "8b": 0.10,   # ~$0.10 per 1M tokens
        }

        # Determine model size from ID
        model_lower = model.lower()
        if "70b" in model_lower:
            rate = cost_per_million["70b"]
        elif "8b" in model_lower:
            rate = cost_per_million["8b"]
        else:
            rate = 0.30  # Default mid-range

        total_tokens = tokens_used.get("total", 0)
        return (total_tokens / 1_000_000) * rate
