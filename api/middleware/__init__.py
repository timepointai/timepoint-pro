"""
API middleware modules.

Provides rate limiting, Bearer-token auth for the MCP server, and other
cross-cutting concerns.
"""

from .bearer_auth import (
    BearerAuthMiddleware,
    extract_bearer_token,
    get_current_bearer_user,
    verify_bearer_token,
)
from .rate_limit import (
    RateLimitConfig,
    get_limiter,
    get_rate_limit_key,
    rate_limit_exceeded_handler,
)

__all__ = [
    "get_limiter",
    "get_rate_limit_key",
    "RateLimitConfig",
    "rate_limit_exceeded_handler",
    "BearerAuthMiddleware",
    "verify_bearer_token",
    "extract_bearer_token",
    "get_current_bearer_user",
]
