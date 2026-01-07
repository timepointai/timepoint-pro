"""
Groq Provider - High-speed inference via Groq Cloud API

Groq provides extremely fast inference (300-750 tokens/sec) using custom LPU hardware.
Uses OpenAI-compatible API at api.groq.com.

Key models:
- llama-3.3-70b-versatile: 128K context, ~300 tok/s (best quality)
- llama-3.1-8b-instant: 128K context, ~750 tok/s (fastest)
- mixtral-8x7b-32768: 32K context, ~500 tok/s (good balance)
"""

from typing import Type, Optional, Dict, Any
from pydantic import BaseModel
import time
import json
import httpx
import os

from llm_service.provider import LLMProvider, LLMResponse
from llm_service.response_parser import ResponseParser


class GroqProvider:
    """
    Provider implementation for Groq Cloud API.

    Groq offers extremely fast inference using specialized LPU hardware.
    API is OpenAI-compatible but hosted at api.groq.com.
    """

    GROQ_API_BASE = "https://api.groq.com/openai/v1"

    # Model speed ratings (tokens/sec, approximate)
    MODEL_SPEEDS = {
        "llama-3.3-70b-versatile": 300,
        "llama-3.1-70b-versatile": 300,
        "llama-3.1-8b-instant": 750,
        "llama3-70b-8192": 300,
        "llama3-8b-8192": 750,
        "mixtral-8x7b-32768": 500,
        "gemma2-9b-it": 600,
    }

    # Model context windows
    MODEL_CONTEXTS = {
        "llama-3.3-70b-versatile": 128000,
        "llama-3.1-70b-versatile": 128000,
        "llama-3.1-8b-instant": 128000,
        "llama3-70b-8192": 8192,
        "llama3-8b-8192": 8192,
        "mixtral-8x7b-32768": 32768,
        "gemma2-9b-it": 8192,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "llama-3.3-70b-versatile",
        timeout: float = 60.0,
    ):
        """
        Initialize Groq provider.

        Args:
            api_key: Groq API key (falls back to GROQ_API_KEY env var)
            default_model: Default model to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter. Get a free key at https://console.groq.com"
            )

        self.default_model = default_model
        self.timeout = timeout
        self.parser = ResponseParser(strict=False)

        # HTTP client with retries
        self.client = httpx.Client(
            base_url=self.GROQ_API_BASE,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

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
        Make a chat completion call to Groq.

        Args:
            system: System prompt
            user: User message
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (not widely supported on Groq)
            presence_penalty: Presence penalty (not widely supported on Groq)
            model: Model to use (overrides default)

        Returns:
            LLMResponse with content and metadata
        """
        selected_model = model or self.default_model
        start_time = time.time()

        try:
            # Build messages
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": user})

            # Build request payload
            payload = {
                "model": selected_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
            }

            # Note: Groq may not support frequency/presence penalty on all models
            # Only add if non-zero to avoid potential errors
            if frequency_penalty != 0.0:
                payload["frequency_penalty"] = frequency_penalty
            if presence_penalty != 0.0:
                payload["presence_penalty"] = presence_penalty

            # Make API call
            response = self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract content
            content = data["choices"][0]["message"]["content"]

            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            tokens_used = {
                "prompt": data.get("usage", {}).get("prompt_tokens", 0),
                "completion": data.get("usage", {}).get("completion_tokens", 0),
                "total": data.get("usage", {}).get("total_tokens", 0),
            }

            # Groq is free tier (as of 2024), but estimate for comparison
            cost_usd = self._estimate_cost(tokens_used, selected_model)

            return LLMResponse(
                content=content,
                model=selected_model,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=True,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            latency_ms = (time.time() - start_time) * 1000
            error_detail = self._parse_error(e)
            return LLMResponse(
                content="",
                model=selected_model,
                tokens_used={"prompt": 0, "completion": 0, "total": 0},
                cost_usd=0.0,
                latency_ms=latency_ms,
                success=False,
                error=error_detail,
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
        """
        Make a structured output call.

        Args:
            system: System prompt
            user: User message
            schema: Pydantic model for response structure
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model to use

        Returns:
            Parsed Pydantic model instance
        """
        from llm_service.prompt_manager import PromptManager

        prompt_mgr = PromptManager()
        schema_prompt = prompt_mgr.schema_to_prompt(schema)
        enhanced_user = f"{user}\n\n{schema_prompt}"

        response = self.call(
            system=system,
            user=enhanced_user,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            **kwargs
        )

        if not response.success:
            raise Exception(f"Groq call failed: {response.error}")

        try:
            return self.parser.parse_structured(response.content, schema, allow_partial=True)
        except Exception as e:
            raise Exception(f"Failed to parse structured response: {e}")

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming."""
        return True  # Groq supports streaming

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "groq"

    def get_default_model(self) -> str:
        """Get default model."""
        return self.default_model

    def list_available_models(self) -> list[str]:
        """List available Groq models."""
        return list(self.MODEL_SPEEDS.keys())

    def get_model_speed(self, model: Optional[str] = None) -> int:
        """Get approximate tokens/sec for a model."""
        model = model or self.default_model
        return self.MODEL_SPEEDS.get(model, 300)

    def get_context_window(self, model: Optional[str] = None) -> int:
        """Get context window size for a model."""
        model = model or self.default_model
        return self.MODEL_CONTEXTS.get(model, 8192)

    def _estimate_cost(self, tokens_used: Dict[str, int], model: str) -> float:
        """
        Estimate API cost in USD.

        Note: Groq offers a generous free tier. Paid pricing (when applicable):
        - llama-3.3-70b: ~$0.59/$0.79 per 1M tokens (input/output)
        - llama-3.1-8b: ~$0.05/$0.08 per 1M tokens
        """
        # Cost per 1M tokens (input + output average)
        cost_per_million = {
            "llama-3.3-70b-versatile": 0.69,
            "llama-3.1-70b-versatile": 0.69,
            "llama-3.1-8b-instant": 0.065,
            "llama3-70b-8192": 0.69,
            "llama3-8b-8192": 0.065,
            "mixtral-8x7b-32768": 0.27,
            "gemma2-9b-it": 0.10,
        }

        rate = cost_per_million.get(model, 0.30)
        total_tokens = tokens_used.get("total", 0)
        return (total_tokens / 1_000_000) * rate

    def _parse_error(self, error: httpx.HTTPStatusError) -> str:
        """Parse HTTP error into readable message."""
        try:
            data = error.response.json()
            if "error" in data:
                err = data["error"]
                if isinstance(err, dict):
                    return f"{err.get('type', 'error')}: {err.get('message', str(error))}"
                return str(err)
        except Exception:
            pass
        return f"HTTP {error.response.status_code}: {str(error)}"

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
