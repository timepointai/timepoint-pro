"""
Error Handling - Retry logic, backoff strategies, and failsoft responses

Handles transient failures, rate limiting, and graceful degradation.
"""

from typing import Callable, TypeVar, Optional, Any
from dataclasses import dataclass
import time
import logging
from enum import Enum

T = TypeVar('T')


class ErrorType(str, Enum):
    """Categories of errors for different handling strategies"""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INVALID_JSON = "invalid_json"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    INSUFFICIENT_CREDITS = "insufficient_credits"  # 402 error - non-retryable
    THINKING_BLOCKS_ERROR = "thinking_blocks"  # Anthropic extended thinking state error - non-retryable
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff: float = 60.0
    retry_on_types: list[ErrorType] = None

    def __post_init__(self):
        if self.retry_on_types is None:
            # NOTE: INSUFFICIENT_CREDITS and THINKING_BLOCKS_ERROR are intentionally
            # NOT in this list - they are non-retryable errors:
            # - INSUFFICIENT_CREDITS: Payment/quota issue, retrying won't help
            # - THINKING_BLOCKS_ERROR: Anthropic session state issue, requires new session
            self.retry_on_types = [
                ErrorType.RATE_LIMIT,
                ErrorType.TIMEOUT,
                ErrorType.NETWORK_ERROR,
                ErrorType.INVALID_JSON,
            ]


class ErrorHandler:
    """
    Handles errors with retry logic and failsoft responses.

    Features:
    - Exponential backoff
    - Error type classification
    - Retry budgets per error type
    - Failsoft fallback responses
    - Logging and monitoring
    """

    def __init__(self, config: RetryConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.retry_counts: dict[ErrorType, int] = {}

    def retry_with_backoff(
        self,
        func: Callable[[], T],
        operation_name: str = "operation",
        failsoft_value: Optional[T] = None,
    ) -> T:
        """
        Execute function with retry logic and exponential backoff.

        Args:
            func: Function to execute
            operation_name: Name for logging
            failsoft_value: Value to return if all retries fail (instead of raising)

        Returns:
            Result from successful function call or failsoft_value

        Raises:
            Exception: Last exception if failsoft_value not provided
        """
        last_exception = None
        attempt = 0

        for attempt in range(self.config.max_retries + 1):
            try:
                result = func()
                # Success - log if this wasn't first attempt
                if attempt > 0:
                    self.logger.info(
                        f"✅ {operation_name} succeeded on attempt {attempt + 1}"
                    )
                return result

            except Exception as e:
                last_exception = e
                error_type = self._classify_error(e)

                # Check if we should retry this error type
                if error_type not in self.config.retry_on_types:
                    self.logger.error(
                        f"❌ {operation_name} failed with non-retryable error: {error_type}"
                    )
                    if failsoft_value is not None:
                        return failsoft_value
                    raise

                # Check if max retries reached
                if attempt >= self.config.max_retries:
                    self.logger.error(
                        f"❌ {operation_name} failed after {attempt + 1} attempts: {e}"
                    )
                    if failsoft_value is not None:
                        return failsoft_value
                    raise

                # Calculate backoff delay
                delay = self._calculate_backoff(attempt, error_type)

                self.logger.warning(
                    f"⚠️ {operation_name} attempt {attempt + 1} failed ({error_type}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )

                # Track retry count
                self.retry_counts[error_type] = self.retry_counts.get(error_type, 0) + 1

                # Wait before retry
                time.sleep(delay)

        # Shouldn't reach here, but safety fallback
        if failsoft_value is not None:
            return failsoft_value
        raise last_exception

    def _classify_error(self, error: Exception) -> ErrorType:
        """
        Classify error into category for appropriate handling.

        Args:
            error: Exception to classify

        Returns:
            ErrorType enum value
        """
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()

        # Anthropic thinking blocks error (non-retryable - session state issue)
        # This happens when extended thinking is enabled and conversation accumulates thinking blocks
        if any(term in error_str for term in ['thinking', 'redacted_thinking', 'thinking blocks']):
            return ErrorType.THINKING_BLOCKS_ERROR

        # Insufficient credits (non-retryable - payment issue)
        if any(term in error_str for term in ['insufficient credits', '402', 'payment required']):
            return ErrorType.INSUFFICIENT_CREDITS

        # Rate limiting
        if any(term in error_str for term in ['rate limit', '429', 'too many requests']):
            return ErrorType.RATE_LIMIT

        # Timeout
        if any(term in error_str for term in ['timeout', 'timed out', 'deadline']):
            return ErrorType.TIMEOUT

        # JSON parsing
        if any(term in error_type_name for term in ['json', 'parse', 'decode']):
            return ErrorType.INVALID_JSON

        # Network errors
        if any(term in error_type_name for term in ['connection', 'network', 'socket']):
            return ErrorType.NETWORK_ERROR

        # Validation errors
        if any(term in error_type_name for term in ['validation', 'schema']):
            return ErrorType.VALIDATION_ERROR

        # API errors
        if any(term in error_str for term in ['api error', '500', '502', '503']):
            return ErrorType.API_ERROR

        return ErrorType.UNKNOWN

    def _calculate_backoff(self, attempt: int, error_type: ErrorType) -> float:
        """
        Calculate backoff delay for retry attempt.

        Args:
            attempt: Attempt number (0-indexed)
            error_type: Type of error

        Returns:
            Delay in seconds
        """
        # Base exponential backoff
        delay = self.config.backoff_base * (self.config.backoff_multiplier ** attempt)

        # Apply error-type-specific multipliers
        if error_type == ErrorType.RATE_LIMIT:
            delay *= 2.0  # Longer backoff for rate limits
        elif error_type == ErrorType.INVALID_JSON:
            delay *= 0.5  # Shorter backoff for JSON issues

        # Cap at max backoff
        delay = min(delay, self.config.max_backoff)

        # Add jitter to avoid thundering herd
        import random
        jitter = random.uniform(0, delay * 0.1)
        delay += jitter

        return delay

    def get_retry_statistics(self) -> dict[str, int]:
        """Get statistics on retry counts by error type"""
        return dict(self.retry_counts)

    def reset_statistics(self) -> None:
        """Reset retry statistics"""
        self.retry_counts.clear()


class FailsoftGenerator:
    """
    Generates failsoft responses when all retries fail.

    Provides null-filled or default responses to allow graceful degradation.
    """

    @staticmethod
    def generate_null_response(schema: type) -> Any:
        """
        Generate a null-filled instance of a Pydantic schema.

        Args:
            schema: Pydantic BaseModel class

        Returns:
            Instance with default/null values
        """
        try:
            # Try to instantiate with no args (relies on defaults)
            return schema()
        except Exception:
            # Build defaults manually
            defaults = {}
            for field_name, field_info in schema.model_fields.items():
                if field_info.default is not None:
                    defaults[field_name] = field_info.default
                elif field_info.default_factory is not None:
                    defaults[field_name] = field_info.default_factory()
                else:
                    # Type-based defaults
                    field_type = field_info.annotation
                    defaults[field_name] = FailsoftGenerator._get_type_default(field_type)

            return schema(**defaults)

    @staticmethod
    def _get_type_default(field_type: Any) -> Any:
        """Get default value for a type"""
        if field_type == str:
            return ""
        elif field_type == int:
            return 0
        elif field_type == float:
            return 0.0
        elif field_type == bool:
            return False
        elif field_type == list:
            return []
        elif field_type == dict:
            return {}
        else:
            return None

    @staticmethod
    def generate_error_response(error_message: str) -> dict:
        """
        Generate a standard error response dict.

        Args:
            error_message: Description of the error

        Returns:
            Error response dict
        """
        return {
            "success": False,
            "error": error_message,
            "content": None,
            "metadata": {"failsoft": True}
        }
