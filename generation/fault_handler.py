"""
Fault Handling and Error Recovery

Provides retry logic with exponential backoff, error classification,
and graceful degradation for long-running generation jobs.
"""

from typing import Dict, Any, Optional, Callable, Type, List
from dataclasses import dataclass
from enum import Enum
import time
import logging
from functools import wraps


logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"      # Stop immediately
    RETRYABLE = "retryable"    # Retry with backoff
    DEGRADABLE = "degradable"  # Continue with degraded output
    IGNORABLE = "ignorable"    # Log and continue


@dataclass
class ErrorInfo:
    """Information about an error"""
    exception: Exception
    severity: ErrorSeverity
    message: str
    context: Dict[str, Any]
    retry_count: int = 0
    timestamp: Optional[float] = None


class FaultHandler:
    """
    Handle faults during generation with retry logic and graceful degradation.

    Example:
        handler = FaultHandler(
            max_retries=3,
            initial_backoff=1.0,
            max_backoff=60.0
        )

        # Retry with exponential backoff
        result = handler.with_retry(
            lambda: llm_service.generate_entity(...),
            error_context={"entity_id": "alice"}
        )

        # Or use as decorator
        @handler.retry_on_failure
        def generate_entity(entity_id):
            return llm_service.generate_entity(entity_id)
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
        backoff_multiplier: float = 2.0,
        enable_graceful_degradation: bool = True
    ):
        """
        Args:
            max_retries: Maximum retry attempts for retryable errors
            initial_backoff: Initial backoff delay in seconds
            max_backoff: Maximum backoff delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
            enable_graceful_degradation: Whether to enable graceful degradation
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        self.enable_graceful_degradation = enable_graceful_degradation

        # Track error history
        self.error_history: List[ErrorInfo] = []

        # Error classification rules
        self._error_classifiers = self._build_error_classifiers()

    def _build_error_classifiers(self) -> List[Callable[[Exception], Optional[ErrorSeverity]]]:
        """Build list of error classification rules"""
        classifiers = []

        # OpenRouter-specific rate limit errors - retryable with longer backoff
        def classify_openrouter_rate_limit(exc: Exception) -> Optional[ErrorSeverity]:
            exc_str = str(exc).lower()
            if any(keyword in exc_str for keyword in [
                "rate limit", "rate_limit", "ratelimit",
                "requests per", "too many requests",
                "429", "quota exceeded", "quota_exceeded"
            ]):
                return ErrorSeverity.RETRYABLE
            return None
        classifiers.append(classify_openrouter_rate_limit)

        # OpenRouter API unavailable - retryable
        def classify_openrouter_unavailable(exc: Exception) -> Optional[ErrorSeverity]:
            exc_str = str(exc).lower()
            if any(keyword in exc_str for keyword in [
                "503", "502", "504",
                "service unavailable", "bad gateway", "gateway timeout",
                "openrouter", "model unavailable"
            ]):
                return ErrorSeverity.RETRYABLE
            return None
        classifiers.append(classify_openrouter_unavailable)

        # Network/timeout errors - retryable
        def classify_network(exc: Exception) -> Optional[ErrorSeverity]:
            exc_str = str(exc).lower()
            if any(keyword in exc_str for keyword in ["timeout", "connection", "network", "timed out"]):
                return ErrorSeverity.RETRYABLE
            return None
        classifiers.append(classify_network)

        # Authentication errors - critical (can't recover)
        def classify_auth(exc: Exception) -> Optional[ErrorSeverity]:
            exc_str = str(exc).lower()
            if any(keyword in exc_str for keyword in ["auth", "unauthorized", "401", "403", "invalid api key", "api_key"]):
                return ErrorSeverity.CRITICAL
            return None
        classifiers.append(classify_auth)

        # Validation errors - degradable (can continue with minimal output)
        def classify_validation(exc: Exception) -> Optional[ErrorSeverity]:
            exc_name = exc.__class__.__name__.lower()
            if "validation" in exc_name or "schema" in exc_name:
                return ErrorSeverity.DEGRADABLE
            return None
        classifiers.append(classify_validation)

        # Invalid config - critical
        def classify_config(exc: Exception) -> Optional[ErrorSeverity]:
            exc_str = str(exc).lower()
            if "config" in exc_str and ("invalid" in exc_str or "missing" in exc_str):
                return ErrorSeverity.CRITICAL
            return None
        classifiers.append(classify_config)

        return classifiers

    def classify_error(self, exception: Exception) -> ErrorSeverity:
        """
        Classify error severity.

        Args:
            exception: Exception to classify

        Returns:
            ErrorSeverity level
        """
        # Try each classifier
        for classifier in self._error_classifiers:
            severity = classifier(exception)
            if severity is not None:
                return severity

        # Default: retryable for unknown errors
        return ErrorSeverity.RETRYABLE

    def calculate_backoff(self, retry_count: int, adaptive: bool = True) -> float:
        """
        Calculate exponential backoff delay with optional adaptive increase.

        Args:
            retry_count: Current retry attempt number (0-indexed)
            adaptive: If True, increase delays if error pattern persists

        Returns:
            Backoff delay in seconds
        """
        delay = self.initial_backoff * (self.backoff_multiplier ** retry_count)

        # Adaptive backoff: If we've had many recent errors, increase delay
        if adaptive and len(self.error_history) >= 5:
            recent_errors = self.error_history[-5:]
            recent_retryable = sum(1 for e in recent_errors if e.severity == ErrorSeverity.RETRYABLE)
            if recent_retryable >= 4:  # 4 out of last 5 were retryable
                # Increase delay by 50% for persistent issues
                delay *= 1.5
                logger.info(f"Adaptive backoff: Increased delay to {delay:.1f}s due to persistent errors")

        return min(delay, self.max_backoff)

    def with_retry(
        self,
        func: Callable,
        error_context: Optional[Dict[str, Any]] = None,
        fallback_value: Any = None
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            error_context: Context information for error logging
            fallback_value: Value to return if all retries fail and degradation enabled

        Returns:
            Function result or fallback_value

        Raises:
            Exception: If error is critical or max retries exceeded
        """
        retry_count = 0
        last_exception = None

        while retry_count <= self.max_retries:
            try:
                return func()

            except Exception as exc:
                last_exception = exc
                severity = self.classify_error(exc)

                # Log error
                error_info = ErrorInfo(
                    exception=exc,
                    severity=severity,
                    message=str(exc),
                    context=error_context or {},
                    retry_count=retry_count,
                    timestamp=time.time()
                )
                self.error_history.append(error_info)

                logger.warning(
                    f"Error in {func.__name__} (attempt {retry_count + 1}/{self.max_retries + 1}): "
                    f"{exc} [severity={severity.value}]"
                )

                # Handle based on severity
                if severity == ErrorSeverity.CRITICAL:
                    logger.error(f"Critical error, stopping: {exc}")
                    raise

                elif severity == ErrorSeverity.RETRYABLE:
                    if retry_count < self.max_retries:
                        backoff = self.calculate_backoff(retry_count)
                        logger.info(f"Retrying after {backoff:.2f}s backoff...")
                        time.sleep(backoff)
                        retry_count += 1
                        continue
                    else:
                        # Max retries exceeded
                        if self.enable_graceful_degradation:
                            logger.warning(
                                f"Max retries exceeded, returning fallback value: {fallback_value}"
                            )
                            return fallback_value
                        else:
                            logger.error(f"Max retries exceeded, raising exception")
                            raise

                elif severity == ErrorSeverity.DEGRADABLE:
                    if self.enable_graceful_degradation:
                        logger.warning(f"Degrading output, returning fallback: {fallback_value}")
                        return fallback_value
                    else:
                        raise

                elif severity == ErrorSeverity.IGNORABLE:
                    logger.info(f"Ignoring error: {exc}")
                    return fallback_value

        # Should not reach here, but handle just in case
        if self.enable_graceful_degradation:
            return fallback_value
        else:
            raise last_exception

    def retry_on_failure(
        self,
        error_context: Optional[Dict[str, Any]] = None,
        fallback_value: Any = None
    ):
        """
        Decorator for retry logic.

        Args:
            error_context: Context information for error logging
            fallback_value: Value to return if all retries fail

        Example:
            @handler.retry_on_failure(fallback_value={})
            def generate_entity(entity_id):
                return llm_service.generate_entity(entity_id)
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.with_retry(
                    lambda: func(*args, **kwargs),
                    error_context=error_context,
                    fallback_value=fallback_value
                )
            return wrapper
        return decorator

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of all errors encountered.

        Returns:
            Dictionary with error statistics:
                - total_errors: Total error count
                - errors_by_severity: Count by severity level
                - retry_count: Total retries performed
                - recent_errors: Last 10 errors
        """
        if not self.error_history:
            return {
                "total_errors": 0,
                "errors_by_severity": {},
                "retry_count": 0,
                "recent_errors": []
            }

        # Count by severity
        errors_by_severity = {}
        for error_info in self.error_history:
            severity = error_info.severity.value
            errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1

        # Calculate total retries
        total_retries = sum(e.retry_count for e in self.error_history)

        # Get recent errors
        recent_errors = []
        for error_info in self.error_history[-10:]:
            recent_errors.append({
                "message": error_info.message,
                "severity": error_info.severity.value,
                "retry_count": error_info.retry_count,
                "timestamp": error_info.timestamp,
                "context": error_info.context
            })

        return {
            "total_errors": len(self.error_history),
            "errors_by_severity": errors_by_severity,
            "retry_count": total_retries,
            "recent_errors": recent_errors
        }

    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()

    def register_error_classifier(
        self,
        classifier: Callable[[Exception], Optional[ErrorSeverity]]
    ):
        """
        Register custom error classifier.

        Args:
            classifier: Function that takes Exception and returns ErrorSeverity or None
        """
        self._error_classifiers.append(classifier)
