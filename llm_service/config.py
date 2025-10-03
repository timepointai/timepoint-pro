"""
Configuration management for LLM service

Defines configuration structure and loading from Hydra config.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class ServiceMode(str, Enum):
    """Operating modes for the LLM service"""
    DRY_RUN = "dry_run"  # Mock responses, no API calls
    VALIDATION = "validation"  # Lightweight testing
    PRODUCTION = "production"  # Full functionality


@dataclass
class ErrorHandlingConfig:
    """Configuration for error handling and retry logic"""
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_multiplier: float = 2.0
    failsoft_enabled: bool = True
    retry_on_invalid_json: bool = True


@dataclass
class LoggingConfig:
    """Configuration for LLM call logging"""
    level: str = "metadata"  # metadata, prompts, responses, full
    directory: str = "logs/llm_calls"
    rotation: str = "daily"
    retention_days: int = 30
    truncate_prompts_chars: int = 500
    truncate_responses_chars: int = 1000


@dataclass
class SecurityConfig:
    """Configuration for security and safety controls"""
    input_bleaching: bool = True
    output_sanitization: bool = True
    max_input_length: int = 50000
    dangerous_patterns: List[str] = field(default_factory=lambda: [
        r"(?i)ignore.*previous.*instructions",
        r"(?i)forget.*system.*prompt",
        r"(?i)disregard.*rules",
    ])


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization"""
    caching_enabled: bool = True
    cache_ttl: int = 300  # seconds
    timeout_seconds: float = 30.0


@dataclass
class SessionConfig:
    """Configuration for session management"""
    enabled: bool = True
    id_prefix: str = "llm_"


@dataclass
class ValidationModeConfig:
    """Configuration for validation mode testing"""
    model: str = "meta-llama/llama-3.1-8b-instruct"
    system_prompt: str = "Respond in Spanish"
    user_prompt: str = "Say hello world"
    expected_pattern: str = r"(?i)(hola|buenos días|buenas)"


@dataclass
class DefaultParametersConfig:
    """Default LLM parameters"""
    model: str = "meta-llama/llama-3.1-70b-instruct"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1000
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


@dataclass
class APIKeyConfig:
    """API key configuration with rotation support"""
    primary: str
    rotation: List[Dict[str, any]] = field(default_factory=list)


@dataclass
class LLMServiceConfig:
    """Complete LLM service configuration"""
    provider: str = "mirascope"  # mirascope, custom, test
    base_url: str = "https://openrouter.ai/api/v1"
    api_keys: APIKeyConfig = field(default_factory=lambda: APIKeyConfig(primary=""))

    # Nested configs
    mode: ServiceMode = ServiceMode.PRODUCTION
    defaults: DefaultParametersConfig = field(default_factory=DefaultParametersConfig)
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    sessions: SessionConfig = field(default_factory=SessionConfig)
    validation_mode: ValidationModeConfig = field(default_factory=ValidationModeConfig)

    @classmethod
    def from_hydra_config(cls, cfg: any) -> "LLMServiceConfig":
        """
        Load configuration from Hydra config object.

        Handles both new llm_service config and legacy llm config.
        """
        # Check if new llm_service config exists
        if hasattr(cfg, 'llm_service'):
            service_cfg = cfg.llm_service

            # Build config from structured sections
            return cls(
                provider=service_cfg.get('provider', 'mirascope'),
                base_url=service_cfg.get('base_url', 'https://openrouter.ai/api/v1'),
                api_keys=APIKeyConfig(
                    primary=service_cfg.api_keys.get('primary', ''),
                    rotation=service_cfg.api_keys.get('rotation', [])
                ),
                mode=ServiceMode(service_cfg.modes.get('mode', 'production')),
                defaults=DefaultParametersConfig(**service_cfg.defaults),
                error_handling=ErrorHandlingConfig(**service_cfg.error_handling),
                logging=LoggingConfig(**service_cfg.logging),
                security=SecurityConfig(**service_cfg.security),
                performance=PerformanceConfig(**service_cfg.performance),
                sessions=SessionConfig(**service_cfg.sessions),
                validation_mode=ValidationModeConfig(**service_cfg.validation_mode),
            )

        # Fallback to legacy llm config
        if hasattr(cfg, 'llm'):
            llm_cfg = cfg.llm

            # Determine mode - prioritize llm.dry_run for backward compatibility
            if llm_cfg.get('dry_run', False):
                service_mode = ServiceMode.DRY_RUN
            else:
                service_mode = ServiceMode.PRODUCTION

            return cls(
                provider='custom',  # Legacy uses custom OpenRouter client
                base_url=llm_cfg.get('base_url', 'https://openrouter.ai/api/v1'),
                api_keys=APIKeyConfig(primary=llm_cfg.get('api_key', '')),
                mode=service_mode,
                defaults=DefaultParametersConfig(
                    model=llm_cfg.get('model') or 'meta-llama/llama-3.1-70b-instruct'
                ),
            )

        # Return default config if no LLM config found
        return cls()
