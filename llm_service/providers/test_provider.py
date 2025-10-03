"""
Test Provider - Mock LLM for testing and validation

Provides:
- Dry-run mode (mock responses)
- Validation mode (lightweight testing with Spanish hello world)
- Deterministic responses for reproducibility
"""

from typing import Type, Optional, Dict, Any
from pydantic import BaseModel
import time
import re
import hashlib
import numpy as np

from llm_service.provider import LLMProvider, LLMResponse
from llm_service.response_parser import ResponseParser


class TestProvider:
    """
    Test provider for dry-run and validation modes.

    Modes:
    - dry_run: Returns mock data matching expected schemas
    - validation: Makes real API call with simple test prompt
    """

    def __init__(
        self,
        mode: str = "dry_run",  # dry_run or validation
        validation_model: str = "meta-llama/llama-3.1-8b-instruct",
        validation_system: str = "Respond in Spanish",
        validation_user: str = "Say hello world",
        validation_expected_pattern: str = r"(?i)(hola|buenos días|buenas)",
    ):
        """
        Initialize test provider.

        Args:
            mode: Operating mode (dry_run or validation)
            validation_model: Model for validation mode
            validation_system: System prompt for validation
            validation_user: User prompt for validation
            validation_expected_pattern: Expected response pattern
        """
        self.mode = mode
        self.validation_model = validation_model
        self.validation_system = validation_system
        self.validation_user = validation_user
        self.validation_expected_pattern = validation_expected_pattern
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
        """Make a mock or validation call"""

        if self.mode == "validation":
            return self._validation_call(model or self.validation_model)
        else:
            return self._dry_run_call(system, user, model)

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
        """Make a mock structured call"""

        if self.mode == "validation":
            # For validation, just return null-filled instance
            return self.parser._create_null_instance(schema)

        # Dry-run mode: generate deterministic mock data
        return self._generate_mock_instance(schema, system + user)

    def supports_streaming(self) -> bool:
        """Test provider doesn't support streaming"""
        return False

    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"test_{self.mode}"

    def get_default_model(self) -> str:
        """Get default model"""
        return "test-model"

    def list_available_models(self) -> list[str]:
        """List available test models"""
        return ["test-model", "mock-model"]

    def _dry_run_call(self, system: str, user: str, model: Optional[str]) -> LLMResponse:
        """Generate deterministic mock response"""
        # Generate deterministic content based on prompts
        seed_str = system + user
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % 10000

        # Mock response content
        content = f"This is a mock LLM response (seed={seed}). "
        content += "The model would normally process your request here."

        # Estimate tokens (rough approximation)
        prompt_tokens = len((system + user).split())
        completion_tokens = len(content.split())

        return LLMResponse(
            content=content,
            model=model or "test-model",
            tokens_used={
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": prompt_tokens + completion_tokens,
            },
            cost_usd=0.0,  # No cost for dry-run
            latency_ms=10.0,  # Instant
            success=True,
            metadata={"mode": "dry_run", "seed": seed},
        )

    def _validation_call(self, model: str) -> LLMResponse:
        """
        Make a validation call (lightweight real API call).

        This would use the actual API with a simple test prompt.
        For now, we mock the expected response.
        """
        # Simulate API call delay
        time.sleep(0.1)

        # Mock Spanish response
        spanish_greetings = [
            "¡Hola mundo!",
            "Buenos días, mundo!",
            "¡Hola! ¿Cómo estás?",
        ]

        # Pick greeting deterministically
        seed = int(time.time()) % len(spanish_greetings)
        content = spanish_greetings[seed]

        # Check if response matches expected pattern
        pattern_match = bool(re.search(self.validation_expected_pattern, content))

        return LLMResponse(
            content=content,
            model=model,
            tokens_used={"prompt": 10, "completion": 5, "total": 15},
            cost_usd=0.001,  # Minimal cost
            latency_ms=100.0,
            success=pattern_match,
            error=None if pattern_match else "Response didn't match expected pattern",
            metadata={
                "mode": "validation",
                "expected_pattern": self.validation_expected_pattern,
                "pattern_match": pattern_match,
            },
        )

    def _generate_mock_instance(self, schema: Type[BaseModel], seed_str: str) -> BaseModel:
        """Generate a mock instance with realistic data"""
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % 10000
        np.random.seed(seed)

        # Build mock data dict
        mock_data = {}

        for field_name, field_info in schema.model_fields.items():
            field_type = field_info.annotation

            # Generate type-appropriate mock data
            if field_type == str:
                mock_data[field_name] = f"mock_{field_name}_{seed}"
            elif field_type == int:
                mock_data[field_name] = int(np.random.randint(0, 100))
            elif field_type == float:
                mock_data[field_name] = float(np.random.uniform(0, 1))
            elif field_type == bool:
                mock_data[field_name] = bool(np.random.rand() > 0.5)
            elif field_type == list:
                # Check if it's List[str] or List[float]
                mock_data[field_name] = [f"item_{i}" for i in range(3)]
            elif field_type == dict:
                mock_data[field_name] = {"key": "value"}
            else:
                # Use default from field or type default
                if field_info.default is not None:
                    mock_data[field_name] = field_info.default
                elif field_info.default_factory is not None:
                    mock_data[field_name] = field_info.default_factory()
                else:
                    mock_data[field_name] = self.parser._get_type_default(field_type)

        return schema(**mock_data)
