"""
Tests for Fault Handling (Sprint 1.4)

Tests retry logic, exponential backoff, error classification, and graceful degradation.
"""

import pytest
import time

from generation.fault_handler import (
    FaultHandler,
    ErrorSeverity,
    ErrorInfo
)


class TestErrorClassification:
    """Tests for error classification"""

    def test_classify_rate_limit_error(self):
        """Test classification of rate limit errors"""
        handler = FaultHandler()

        exc = Exception("Rate limit exceeded")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.RETRYABLE

        exc = Exception("Quota exceeded, please retry")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.RETRYABLE

        exc = Exception("HTTP 429 Too Many Requests")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.RETRYABLE

    def test_classify_network_error(self):
        """Test classification of network errors"""
        handler = FaultHandler()

        exc = Exception("Connection timeout")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.RETRYABLE

        exc = Exception("Network error occurred")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.RETRYABLE

    def test_classify_auth_error(self):
        """Test classification of authentication errors"""
        handler = FaultHandler()

        exc = Exception("Authentication failed")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.CRITICAL

        exc = Exception("HTTP 401 Unauthorized")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.CRITICAL

        exc = Exception("HTTP 403 Forbidden")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.CRITICAL

    def test_classify_validation_error(self):
        """Test classification of validation errors"""
        handler = FaultHandler()

        class ValidationError(Exception):
            pass

        exc = ValidationError("Invalid schema")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.DEGRADABLE

    def test_classify_config_error(self):
        """Test classification of config errors"""
        handler = FaultHandler()

        exc = Exception("Invalid configuration")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.CRITICAL

    def test_classify_unknown_error(self):
        """Test classification of unknown errors defaults to retryable"""
        handler = FaultHandler()

        exc = Exception("Something went wrong")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.RETRYABLE


class TestBackoffCalculation:
    """Tests for exponential backoff"""

    def test_initial_backoff(self):
        """Test initial backoff delay"""
        handler = FaultHandler(initial_backoff=1.0)
        delay = handler.calculate_backoff(retry_count=0)
        assert delay == 1.0

    def test_exponential_backoff(self):
        """Test exponential backoff progression"""
        handler = FaultHandler(
            initial_backoff=1.0,
            backoff_multiplier=2.0
        )

        # Retry 0: 1.0 * 2^0 = 1.0
        assert handler.calculate_backoff(0) == 1.0

        # Retry 1: 1.0 * 2^1 = 2.0
        assert handler.calculate_backoff(1) == 2.0

        # Retry 2: 1.0 * 2^2 = 4.0
        assert handler.calculate_backoff(2) == 4.0

        # Retry 3: 1.0 * 2^3 = 8.0
        assert handler.calculate_backoff(3) == 8.0

    def test_max_backoff_cap(self):
        """Test max backoff cap"""
        handler = FaultHandler(
            initial_backoff=1.0,
            backoff_multiplier=2.0,
            max_backoff=5.0
        )

        # Should be capped at 5.0 even for high retry counts
        assert handler.calculate_backoff(10) == 5.0
        assert handler.calculate_backoff(20) == 5.0


class TestRetryLogic:
    """Tests for retry logic"""

    def test_successful_execution_no_retry(self):
        """Test successful execution requires no retries"""
        handler = FaultHandler()

        call_count = [0]

        def successful_func():
            call_count[0] += 1
            return "success"

        result = handler.with_retry(successful_func)
        assert result == "success"
        assert call_count[0] == 1  # Called only once

    def test_retry_on_retryable_error(self):
        """Test retry on retryable errors"""
        handler = FaultHandler(
            max_retries=3,
            initial_backoff=0.01  # Small backoff for fast tests
        )

        call_count = [0]

        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Rate limit exceeded")
            return "success"

        result = handler.with_retry(flaky_func)
        assert result == "success"
        assert call_count[0] == 3  # Called 3 times (1 + 2 retries)

    def test_max_retries_exceeded(self):
        """Test max retries enforcement"""
        handler = FaultHandler(
            max_retries=2,
            initial_backoff=0.01,
            enable_graceful_degradation=False
        )

        def always_fails():
            raise Exception("Rate limit exceeded")

        with pytest.raises(Exception, match="Rate limit exceeded"):
            handler.with_retry(always_fails)

        # Should have tried 3 times (initial + 2 retries)
        assert len(handler.error_history) == 3

    def test_graceful_degradation_on_max_retries(self):
        """Test graceful degradation when max retries exceeded"""
        handler = FaultHandler(
            max_retries=2,
            initial_backoff=0.01,
            enable_graceful_degradation=True
        )

        def always_fails():
            raise Exception("Rate limit exceeded")

        result = handler.with_retry(always_fails, fallback_value="fallback")
        assert result == "fallback"

    def test_critical_error_stops_immediately(self):
        """Test critical errors stop retry immediately"""
        handler = FaultHandler(
            max_retries=5,
            initial_backoff=0.01
        )

        def critical_error():
            raise Exception("Authentication failed")

        with pytest.raises(Exception, match="Authentication failed"):
            handler.with_retry(critical_error)

        # Should only try once (no retries for critical errors)
        assert len(handler.error_history) == 1

    def test_degradable_error_returns_fallback(self):
        """Test degradable errors return fallback value"""
        handler = FaultHandler(enable_graceful_degradation=True)

        class ValidationError(Exception):
            pass

        def validation_error():
            raise ValidationError("Invalid schema")

        result = handler.with_retry(validation_error, fallback_value="minimal")
        assert result == "minimal"

    def test_retry_decorator(self):
        """Test retry decorator"""
        handler = FaultHandler(
            max_retries=2,
            initial_backoff=0.01
        )

        call_count = [0]

        @handler.retry_on_failure(fallback_value="fallback")
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Rate limit exceeded")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count[0] == 2

    def test_error_context_tracking(self):
        """Test error context is tracked"""
        handler = FaultHandler(initial_backoff=0.01)

        def failing_func():
            raise Exception("Test error")

        try:
            handler.with_retry(
                failing_func,
                error_context={"entity_id": "alice"},
                fallback_value=None
            )
        except:
            pass

        # Check error history contains context
        assert len(handler.error_history) > 0
        assert handler.error_history[-1].context == {"entity_id": "alice"}


class TestErrorSummary:
    """Tests for error summary and reporting"""

    def test_error_summary_empty(self):
        """Test error summary with no errors"""
        handler = FaultHandler()
        summary = handler.get_error_summary()

        assert summary["total_errors"] == 0
        assert summary["errors_by_severity"] == {}
        assert summary["retry_count"] == 0
        assert summary["recent_errors"] == []

    def test_error_summary_with_errors(self):
        """Test error summary with multiple errors"""
        handler = FaultHandler(
            max_retries=2,
            initial_backoff=0.01,
            enable_graceful_degradation=True
        )

        def fails_with_retry():
            raise Exception("Rate limit exceeded")

        # Generate some errors
        handler.with_retry(fails_with_retry, fallback_value=None)

        summary = handler.get_error_summary()
        assert summary["total_errors"] > 0
        assert "retryable" in summary["errors_by_severity"]
        assert summary["retry_count"] > 0

    def test_recent_errors_limit(self):
        """Test recent errors are limited to 10"""
        handler = FaultHandler(
            max_retries=0,
            enable_graceful_degradation=True
        )

        def failing_func():
            raise Exception("Test error")

        # Generate 20 errors
        for i in range(20):
            handler.with_retry(failing_func, fallback_value=None)

        summary = handler.get_error_summary()
        assert len(summary["recent_errors"]) == 10

    def test_clear_error_history(self):
        """Test clearing error history"""
        handler = FaultHandler(enable_graceful_degradation=True)

        def failing_func():
            raise Exception("Test error")

        handler.with_retry(failing_func, fallback_value=None)
        assert len(handler.error_history) > 0

        handler.clear_error_history()
        assert len(handler.error_history) == 0


class TestCustomErrorClassifiers:
    """Tests for custom error classifiers"""

    def test_register_custom_classifier(self):
        """Test registering custom error classifier"""
        handler = FaultHandler()

        def custom_classifier(exc: Exception):
            if "custom error" in str(exc).lower():
                return ErrorSeverity.CRITICAL
            return None

        handler.register_error_classifier(custom_classifier)

        exc = Exception("Custom error occurred")
        severity = handler.classify_error(exc)
        assert severity == ErrorSeverity.CRITICAL

    def test_multiple_custom_classifiers(self):
        """Test multiple custom classifiers"""
        handler = FaultHandler()

        def classifier1(exc: Exception):
            if "error1" in str(exc):
                return ErrorSeverity.CRITICAL
            return None

        def classifier2(exc: Exception):
            if "error2" in str(exc):
                return ErrorSeverity.IGNORABLE
            return None

        handler.register_error_classifier(classifier1)
        handler.register_error_classifier(classifier2)

        # Test classifier1
        exc1 = Exception("error1 occurred")
        assert handler.classify_error(exc1) == ErrorSeverity.CRITICAL

        # Test classifier2
        exc2 = Exception("error2 occurred")
        assert handler.classify_error(exc2) == ErrorSeverity.IGNORABLE


class TestBackoffTiming:
    """Tests for backoff timing (integration tests)"""

    def test_actual_backoff_delay(self):
        """Test actual backoff delay timing"""
        handler = FaultHandler(
            max_retries=2,
            initial_backoff=0.05,  # 50ms
            backoff_multiplier=2.0
        )

        call_count = [0]
        start_time = time.time()

        def failing_func():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("Rate limit exceeded")
            return "success"

        result = handler.with_retry(failing_func)
        elapsed = time.time() - start_time

        # Should have delayed: 50ms + 100ms = 150ms minimum
        # (first retry after 50ms, second retry after 100ms)
        assert elapsed >= 0.15
        assert result == "success"
