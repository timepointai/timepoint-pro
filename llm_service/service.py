"""
LLM Service - Main facade coordinating all components

This is the primary interface for making LLM calls throughout the application.
"""

from typing import Type, Optional, Callable, Dict, Any
from pydantic import BaseModel
import logging

from llm_service.config import LLMServiceConfig, ServiceMode
from llm_service.provider import LLMProvider, LLMResponse
from llm_service.providers.custom_provider import CustomOpenRouterProvider
from llm_service.providers.test_provider import TestProvider
from llm_service.prompt_manager import PromptManager
from llm_service.response_parser import ResponseParser
from llm_service.error_handler import ErrorHandler, RetryConfig
from llm_service.call_logger import CallLogger
from llm_service.security_filter import SecurityFilter


class LLMService:
    """
    Unified LLM service coordinating all components.

    Provides:
    - Provider abstraction (custom, test, future: mirascope)
    - Prompt management and templating
    - Response parsing and validation
    - Error handling and retry logic
    - Security filtering (input/output)
    - Comprehensive logging
    - Session management
    """

    def __init__(self, config: LLMServiceConfig):
        """
        Initialize LLM service with configuration.

        Args:
            config: LLMServiceConfig instance
        """
        self.config = config

        # Initialize components
        self.prompt_manager = PromptManager()
        self.response_parser = ResponseParser(strict=False)
        self.security_filter = SecurityFilter(
            max_input_length=config.security.max_input_length,
            dangerous_patterns=config.security.dangerous_patterns,
            strict_mode=False,
        )
        self.error_handler = ErrorHandler(
            config=RetryConfig(
                max_retries=config.error_handling.max_retries,
                backoff_base=config.error_handling.backoff_base,
                backoff_multiplier=config.error_handling.backoff_multiplier,
            ),
            logger=logging.getLogger("llm_service.errors"),
        )
        self.call_logger = CallLogger(
            log_directory=config.logging.directory,
            log_level=config.logging.level,
            truncate_prompts_chars=config.logging.truncate_prompts_chars,
            truncate_responses_chars=config.logging.truncate_responses_chars,
            rotation=config.logging.rotation,
        )

        # Initialize provider based on config
        self.provider = self._create_provider()

        # Statistics
        self.call_count = 0
        self.total_cost = 0.0

    def call(
        self,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        model: Optional[str] = None,
        call_type: str = "generic",
        apply_security: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Make an LLM call with full service features.

        Args:
            system: System prompt
            user: User prompt
            temperature: Sampling temperature (uses config default if None)
            max_tokens: Max tokens to generate (uses config default if None)
            top_p: Nucleus sampling (uses config default if None)
            model: Model identifier (uses config default if None)
            call_type: Type of call for logging (e.g., 'populate_entity')
            apply_security: Whether to apply security filtering
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with content and metadata
        """
        # Use config defaults for unspecified parameters
        temperature = temperature if temperature is not None else self.config.defaults.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.defaults.max_tokens
        top_p = top_p if top_p is not None else self.config.defaults.top_p
        model = model or self.config.defaults.model

        # Apply security filtering to inputs
        if apply_security and self.config.security.input_bleaching:
            system = self.security_filter.bleach_input(system)
            user = self.security_filter.bleach_input(user)

        # Define API call function for retry wrapper
        def _make_call() -> LLMResponse:
            return self.provider.call(
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                model=model,
                **kwargs
            )

        # Execute with retry logic
        if self.config.error_handling.failsoft_enabled:
            # Failsoft: return error response instead of raising
            failsoft_response = LLMResponse(
                content="",
                model=model,
                tokens_used={"prompt": 0, "completion": 0, "total": 0},
                cost_usd=0.0,
                latency_ms=0.0,
                success=False,
                error="All retries failed (failsoft mode)",
            )
            response = self.error_handler.retry_with_backoff(
                _make_call,
                operation_name=f"LLM call ({call_type})",
                failsoft_value=failsoft_response,
            )
        else:
            # Strict: raise exception on failure
            response = self.error_handler.retry_with_backoff(
                _make_call,
                operation_name=f"LLM call ({call_type})",
            )

        # Apply security filtering to output
        if apply_security and self.config.security.output_sanitization and response.success:
            response.content = self.security_filter.sanitize_output(response.content)

        # Log the call
        self.call_logger.log_call(
            call_type=call_type,
            model=model,
            parameters={
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
            },
            tokens_used=response.tokens_used,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            success=response.success,
            retry_count=0,  # TODO: track from error handler
            error=response.error,
            system_prompt=system,
            user_prompt=user,
            response_full=response.content,
        )

        # Update statistics
        self.call_count += 1
        self.total_cost += response.cost_usd

        return response

    def structured_call(
        self,
        system: str,
        user: str,
        schema: Type[BaseModel],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        call_type: str = "structured",
        apply_security: bool = True,
        allow_partial: bool = True,
        **kwargs
    ) -> BaseModel:
        """
        Make an LLM call expecting structured output.

        Args:
            system: System prompt
            user: User prompt
            schema: Pydantic model for response structure
            temperature: Sampling temperature
            max_tokens: Max tokens
            model: Model identifier
            call_type: Call type for logging
            apply_security: Whether to apply security filtering
            allow_partial: Allow partial/incomplete responses
            **kwargs: Additional parameters

        Returns:
            Instance of schema class populated from LLM response
        """
        # Add schema instructions to prompts
        schema_prompt = self.prompt_manager.schema_to_prompt(schema)
        enhanced_user = f"{user}\n\n{schema_prompt}"

        # Make regular call
        response = self.call(
            system=system,
            user=enhanced_user,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            call_type=call_type,
            apply_security=apply_security,
            **kwargs
        )

        if not response.success:
            # Return null-filled instance on failure
            if self.config.error_handling.failsoft_enabled:
                return self.response_parser._create_null_instance(schema)
            else:
                raise Exception(f"LLM call failed: {response.error}")

        # Parse response into schema
        try:
            return self.response_parser.parse_structured(
                response.content,
                schema,
                allow_partial=allow_partial
            )
        except Exception as e:
            if self.config.error_handling.failsoft_enabled:
                return self.response_parser._create_null_instance(schema)
            else:
                raise Exception(f"Failed to parse structured response: {e}")

    def start_session(
        self,
        workflow: str = "unknown",
        user: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a logging session.

        Args:
            workflow: Workflow name
            user: User identifier
            metadata: Additional metadata

        Returns:
            Session ID
        """
        return self.call_logger.start_session(workflow, user, metadata)

    def end_session(self) -> Optional[Dict[str, Any]]:
        """
        End the current session.

        Returns:
            Session summary dict or None
        """
        return self.call_logger.end_session()

    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "total_calls": self.call_count,
            "total_cost": self.total_cost,
            "logger_stats": self.call_logger.get_statistics(),
            "retry_stats": self.error_handler.get_retry_statistics(),
            "filter_stats": self.security_filter.get_filter_statistics(),
        }

    def _create_provider(self) -> LLMProvider:
        """
        Create provider instance based on configuration.

        Returns:
            Provider instance conforming to LLMProvider protocol
        """
        if self.config.mode == ServiceMode.DRY_RUN:
            return TestProvider(mode="dry_run")

        elif self.config.mode == ServiceMode.VALIDATION:
            return TestProvider(
                mode="validation",
                validation_model=self.config.validation_mode.model,
                validation_system=self.config.validation_mode.system_prompt,
                validation_user=self.config.validation_mode.user_prompt,
                validation_expected_pattern=self.config.validation_mode.expected_pattern,
            )

        elif self.config.provider == "custom":
            return CustomOpenRouterProvider(
                api_key=self.config.api_keys.primary,
                base_url=self.config.base_url,
                default_model=self.config.defaults.model,
            )

        elif self.config.provider == "test":
            return TestProvider(mode="dry_run")

        else:
            # Default to custom provider
            return CustomOpenRouterProvider(
                api_key=self.config.api_keys.primary,
                base_url=self.config.base_url,
                default_model=self.config.defaults.model,
            )

    @classmethod
    def from_hydra_config(cls, cfg: any) -> "LLMService":
        """
        Create service from Hydra configuration.

        Args:
            cfg: Hydra config object

        Returns:
            Configured LLMService instance
        """
        service_config = LLMServiceConfig.from_hydra_config(cfg)
        return cls(service_config)

    def set_global_system_prompt(self, prompt: str) -> None:
        """Set a global system prompt prepended to all calls"""
        self.prompt_manager.set_global_system_prompt(prompt)

    def register_prompt_template(self, name: str, template: str) -> None:
        """Register a reusable prompt template"""
        self.prompt_manager.register_template(name, template)

    def build_prompt(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Build a prompt from registered template"""
        return self.prompt_manager.build_prompt(
            template_name=template_name,
            variables=variables
        )
