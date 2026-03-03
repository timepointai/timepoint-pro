"""
Natural Language to Configuration Generator

Uses LLM (Llama 405B via OpenRouter) to convert natural language descriptions
into validated SimulationConfig objects with confidence scoring and error recovery.
"""

import json
from typing import Any

import httpx

from .config_validator import ConfigValidator, ValidationResult
from .prompts import build_config_generation_prompt, build_error_recovery_prompt


class NLConfigGenerator:
    """
    Generate simulation configurations from natural language.

    Uses LLM with few-shot prompting to convert NL descriptions into
    validated SimulationConfig objects. Includes retry logic, validation,
    and confidence scoring.

    Example:
        generator = NLConfigGenerator(api_key="your_openrouter_key")

        config, confidence = generator.generate_config(
            "Simulate a board meeting with 5 executives discussing an acquisition"
        )

        print(f"Confidence: {confidence:.1%}")
        print(f"Scenario: {config['scenario']}")
        print(f"Entities: {len(config['entities'])}")
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "meta-llama/llama-3.1-405b-instruct",
        fallback_model: str = "meta-llama/llama-3.1-70b-instruct",
        temperature: float = 0.7,
        max_retries: int = 3,
    ):
        """
        Initialize NL config generator.

        Args:
            api_key: OpenRouter API key (or None for mock mode)
            model: Primary LLM model to use
            fallback_model: Fallback model for retries
            temperature: LLM temperature (0.0-1.0)
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self.max_retries = max_retries
        self.validator = ConfigValidator()

        # Mock mode if no API key
        self.mock_mode = api_key is None

    def generate_config(
        self, description: str, context: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], float]:
        """
        Generate configuration from natural language description.

        Args:
            description: Natural language description of scenario
            context: Optional additional context

        Returns:
            Tuple of (config_dict, confidence_score)

        Raises:
            ValueError: If config generation fails after all retries
        """
        if self.mock_mode:
            return self._generate_mock_config(description)

        # Build prompt
        prompt = build_config_generation_prompt(description)

        # Try with primary model
        for attempt in range(self.max_retries):
            try:
                # Adjust temperature on retries
                temp = self.temperature * (0.5**attempt)  # 0.7 → 0.35 → 0.175

                # Call LLM
                response = self._call_llm(prompt, temperature=temp)

                # Parse and validate
                config_dict = self._parse_response(response)
                validation = self.validator.validate(config_dict)

                if validation.is_valid:
                    return config_dict, validation.confidence_score

                # If validation failed, try error recovery
                if attempt < self.max_retries - 1:
                    prompt = self._build_recovery_prompt(description, config_dict, validation)
                    continue

            except json.JSONDecodeError:
                if attempt < self.max_retries - 1:
                    prompt = build_error_recovery_prompt("invalid_json", description=description)
                    continue

            except Exception as e:
                if attempt >= self.max_retries - 1:
                    raise ValueError(
                        f"Config generation failed after {self.max_retries} attempts: {e}"
                    )

        # If we get here, all retries failed
        raise ValueError(
            f"Could not generate valid config after {self.max_retries} attempts. "
            "Please try a more specific description or use manual config."
        )

    def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Call LLM via OpenRouter API.

        Args:
            prompt: Prompt text
            temperature: Sampling temperature

        Returns:
            LLM response text
        """
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 2000,
        }

        response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _parse_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response into config dictionary.

        Args:
            response: LLM response text

        Returns:
            Configuration dictionary

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Try to extract JSON from response (in case LLM added markdown)
        response = response.strip()

        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])  # Remove first and last lines

        return json.loads(response)

    def _build_recovery_prompt(
        self, description: str, config_dict: dict[str, Any], validation: ValidationResult
    ) -> str:
        """
        Build error recovery prompt based on validation errors.

        Args:
            description: Original NL description
            config_dict: Failed config
            validation: Validation result with errors

        Returns:
            Recovery prompt
        """
        # Determine error type
        if validation.errors:
            error_msg = validation.errors[0]

            if "temporal_mode" in error_msg:
                mode = config_dict.get("temporal_mode", "unknown")
                return build_error_recovery_prompt(
                    "invalid_temporal_mode", mode=mode, description=description
                )

            if "Entity count" in error_msg:
                count = len(config_dict.get("entities", []))
                return build_error_recovery_prompt(
                    "too_many_entities", count=count, description=description
                )

            if "Timepoint count" in error_msg:
                count = config_dict.get("timepoint_count", 0)
                return build_error_recovery_prompt(
                    "too_many_timepoints", count=count, description=description
                )

        # Generic error recovery
        return build_error_recovery_prompt(
            "missing_required_fields",
            missing_fields=", ".join(validation.errors),
            description=description,
        )

    def _generate_mock_config(self, description: str) -> tuple[dict[str, Any], float]:
        """
        Generate mock configuration (for testing without API key).

        Args:
            description: Natural language description

        Returns:
            Tuple of (mock_config, confidence_score)
        """
        import re

        # Simple heuristics for mock generation
        entity_count = 3

        # Try to extract entity count from patterns like "5 executives", "10 delegates", etc.
        entity_match = re.search(
            r"(\d+)\s+(?:people|entities|participants|members|delegates|astronauts|executives)",
            description,
            re.IGNORECASE,
        )
        if entity_match:
            entity_count = int(entity_match.group(1))
        elif "five" in description.lower():
            entity_count = 5
        elif "ten" in description.lower():
            entity_count = 10
        elif "three" in description.lower():
            entity_count = 3

        timepoint_count = 5

        # Try to extract timepoint count
        timepoint_match = re.search(r"(\d+)\s+timepoints?", description, re.IGNORECASE)
        if timepoint_match:
            timepoint_count = int(timepoint_match.group(1))
        elif "ten timepoints" in description.lower():
            timepoint_count = 10
        elif "fifteen" in description.lower() or "15" in description:
            timepoint_count = 15

        focus = ["dialog", "decision_making"]
        if "relationship" in description.lower():
            focus.append("relationships")

        config = {
            "scenario": description[:50] + "..." if len(description) > 50 else description,
            "entities": [
                {"name": f"Entity {i + 1}", "role": "Participant"} for i in range(entity_count)
            ],
            "timepoint_count": timepoint_count,
            "temporal_mode": "forward",
            "focus": focus,
            "outputs": ["dialog", "decisions"],
        }

        return config, 0.8  # Mock confidence

    def validate_config(self, config_dict: dict[str, Any]) -> ValidationResult:
        """
        Validate configuration dictionary.

        Args:
            config_dict: Configuration to validate

        Returns:
            ValidationResult with errors, warnings, and confidence
        """
        return self.validator.validate(config_dict)

    def get_confidence_explanation(self, confidence: float) -> str:
        """
        Get human-readable explanation of confidence score.

        Args:
            confidence: Confidence score (0.0-1.0)

        Returns:
            Explanation string
        """
        if confidence >= 0.95:
            return "Very high confidence - config is well-formed and sensible"
        elif confidence >= 0.85:
            return "High confidence - minor warnings but config should work well"
        elif confidence >= 0.70:
            return "Moderate confidence - some concerns, review recommended"
        elif confidence >= 0.50:
            return "Low confidence - significant issues, manual review required"
        else:
            return "Very low confidence - config has errors, regeneration recommended"
