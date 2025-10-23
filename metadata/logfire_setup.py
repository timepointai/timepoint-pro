"""
Logfire Integration - Optional monitoring with local console output

Works locally without token - uses console output.
Optional cloud monitoring if LOGFIRE_TOKEN is set.

No mocks - uses real logfire library.
"""

import os
from typing import Optional, Any
from contextlib import contextmanager

# Try to import logfire, fallback to simple console logging
try:
    import logfire
    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False
    print("Warning: logfire not installed. Install with: pip install logfire")


class LogfireManager:
    """
    Manage logfire integration for monitoring.

    Works in two modes:
    1. Local mode (default): Console output, no token required
    2. Cloud mode: Full logfire cloud monitoring if LOGFIRE_TOKEN is set
    """

    def __init__(self):
        self.enabled = LOGFIRE_AVAILABLE
        self.cloud_enabled = False

        if self.enabled:
            # Check for cloud token
            token = os.getenv("LOGFIRE_TOKEN")
            if token:
                try:
                    # Configure for cloud
                    logfire.configure(token=token)
                    self.cloud_enabled = True
                    print("✓ Logfire cloud monitoring enabled")
                except Exception as e:
                    print(f"Warning: Logfire cloud init failed: {e}")
                    print("  Falling back to console mode")
            else:
                # Console mode - no token required
                try:
                    logfire.configure(send_to_logfire=False)
                    print("✓ Logfire console mode enabled (local only)")
                except Exception as e:
                    print(f"Warning: Logfire init failed: {e}")
                    self.enabled = False

    @contextmanager
    def span(self, name: str, **attributes):
        """
        Create a span for monitoring.

        Args:
            name: Span name (e.g., "run:test_0001", "step:temporal_generation")
            **attributes: Additional attributes to log
        """
        if self.enabled:
            with logfire.span(name, **attributes) as span:
                yield span
        else:
            # Fallback: simple print
            print(f"[SPAN] {name} | {attributes}")
            yield None

    def info(self, message: str, **attributes):
        """Log info message"""
        if self.enabled:
            logfire.info(message, **attributes)
        else:
            print(f"[INFO] {message} | {attributes}")

    def warn(self, message: str, **attributes):
        """Log warning"""
        if self.enabled:
            logfire.warn(message, **attributes)
        else:
            print(f"[WARN] {message} | {attributes}")

    def error(self, message: str, **attributes):
        """Log error"""
        if self.enabled:
            logfire.error(message, **attributes)
        else:
            print(f"[ERROR] {message} | {attributes}")

    def metric(self, name: str, value: float, **attributes):
        """Log metric"""
        if self.enabled:
            logfire.metric(name, value, **attributes)
        else:
            print(f"[METRIC] {name}={value} | {attributes}")


# Global logfire manager instance
_logfire_manager: Optional[LogfireManager] = None


def get_logfire() -> LogfireManager:
    """Get or create the global logfire manager"""
    global _logfire_manager
    if _logfire_manager is None:
        _logfire_manager = LogfireManager()
    return _logfire_manager


# Convenience functions
def span(name: str, **attributes):
    """Create a monitoring span"""
    return get_logfire().span(name, **attributes)


def info(message: str, **attributes):
    """Log info"""
    get_logfire().info(message, **attributes)


def warn(message: str, **attributes):
    """Log warning"""
    get_logfire().warn(message, **attributes)


def error(message: str, **attributes):
    """Log error"""
    get_logfire().error(message, **attributes)


def metric(name: str, value: float, **attributes):
    """Log metric"""
    get_logfire().metric(name, value, **attributes)
