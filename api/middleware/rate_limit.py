"""
Rate limiting middleware for the tensor API.

Uses slowapi for in-memory rate limiting with configurable
limits per tier (free, basic, pro, enterprise).

Phase 6: Public API - Rate Limiting
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict
from datetime import datetime

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ..auth import get_api_key, APIKeyRecord


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration per tier."""

    # Requests per minute
    free_rpm: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_FREE_RPM", "10")))
    basic_rpm: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_BASIC_RPM", "60")))
    pro_rpm: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PRO_RPM", "300")))
    enterprise_rpm: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_ENTERPRISE_RPM", "1000")))

    # Requests per hour (for expensive operations)
    free_rph: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_FREE_RPH", "100")))
    basic_rph: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_BASIC_RPH", "1000")))
    pro_rph: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PRO_RPH", "10000")))
    enterprise_rph: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_ENTERPRISE_RPH", "100000")))

    # Burst limits (requests per second)
    free_rps: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_FREE_RPS", "2")))
    basic_rps: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_BASIC_RPS", "5")))
    pro_rps: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PRO_RPS", "20")))
    enterprise_rps: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_ENTERPRISE_RPS", "50")))

    # Simulation-specific limits (concurrent jobs)
    free_concurrent_jobs: int = 1
    basic_concurrent_jobs: int = 3
    pro_concurrent_jobs: int = 10
    enterprise_concurrent_jobs: int = -1  # Unlimited

    # Enable/disable rate limiting
    enabled: bool = field(default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true")

    def get_rpm_for_tier(self, tier: str) -> int:
        """Get requests per minute for a tier."""
        return {
            "free": self.free_rpm,
            "basic": self.basic_rpm,
            "pro": self.pro_rpm,
            "enterprise": self.enterprise_rpm,
        }.get(tier, self.free_rpm)

    def get_rph_for_tier(self, tier: str) -> int:
        """Get requests per hour for a tier."""
        return {
            "free": self.free_rph,
            "basic": self.basic_rph,
            "pro": self.pro_rph,
            "enterprise": self.enterprise_rph,
        }.get(tier, self.free_rph)

    def get_rps_for_tier(self, tier: str) -> int:
        """Get requests per second (burst) for a tier."""
        return {
            "free": self.free_rps,
            "basic": self.basic_rps,
            "pro": self.pro_rps,
            "enterprise": self.enterprise_rps,
        }.get(tier, self.free_rps)

    def get_concurrent_jobs_for_tier(self, tier: str) -> int:
        """Get concurrent job limit for a tier (-1 = unlimited)."""
        return {
            "free": self.free_concurrent_jobs,
            "basic": self.basic_concurrent_jobs,
            "pro": self.pro_concurrent_jobs,
            "enterprise": self.enterprise_concurrent_jobs,
        }.get(tier, self.free_concurrent_jobs)


# Global config instance
_config: Optional[RateLimitConfig] = None


def get_rate_limit_config() -> RateLimitConfig:
    """Get rate limit configuration."""
    global _config
    if _config is None:
        _config = RateLimitConfig()
    return _config


# ============================================================================
# User Tier Detection
# ============================================================================

# In-memory tier mapping (in production, this would be from database)
_USER_TIERS: Dict[str, str] = {}


def get_user_tier(user_id: str) -> str:
    """
    Get the rate limit tier for a user.

    Args:
        user_id: User ID

    Returns:
        Tier name: 'free', 'basic', 'pro', or 'enterprise'
    """
    return _USER_TIERS.get(user_id, "free")


def set_user_tier(user_id: str, tier: str) -> None:
    """
    Set the rate limit tier for a user.

    Args:
        user_id: User ID
        tier: Tier name
    """
    if tier not in ("free", "basic", "pro", "enterprise"):
        raise ValueError(f"Invalid tier: {tier}")
    _USER_TIERS[user_id] = tier


def clear_user_tiers() -> None:
    """Clear all user tiers (for testing)."""
    _USER_TIERS.clear()


# ============================================================================
# Rate Limit Key Functions
# ============================================================================

def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key from request.

    Uses API key user_id if present, otherwise falls back to IP address.
    This allows per-user rate limiting for authenticated requests.

    Args:
        request: FastAPI request

    Returns:
        Rate limit key (user_id or IP address)
    """
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")

    if api_key:
        record = get_api_key(api_key)
        if record and record.is_active:
            return f"user:{record.user_id}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_dynamic_rate_limit(request: Request) -> str:
    """
    Get dynamic rate limit based on user tier.

    This is used with slowapi's dynamic limit feature.

    Args:
        request: FastAPI request

    Returns:
        Rate limit string (e.g., "100/minute")
    """
    config = get_rate_limit_config()

    # Get user from API key
    api_key = request.headers.get("X-API-Key")
    tier = "free"

    if api_key:
        record = get_api_key(api_key)
        if record and record.is_active:
            tier = get_user_tier(record.user_id)

    rpm = config.get_rpm_for_tier(tier)
    return f"{rpm}/minute"


# ============================================================================
# Limiter Setup
# ============================================================================

# Global limiter instance
_limiter: Optional[Limiter] = None


def get_limiter() -> Limiter:
    """
    Get or create the rate limiter.

    Returns:
        Slowapi Limiter instance
    """
    global _limiter
    if _limiter is None:
        config = get_rate_limit_config()
        _limiter = Limiter(
            key_func=get_rate_limit_key,
            default_limits=[f"{config.free_rpm}/minute"],
            enabled=config.enabled,
            # Use in-memory storage (for production, use Redis)
            storage_uri="memory://",
        )
    return _limiter


def reset_limiter() -> None:
    """Reset the limiter (for testing)."""
    global _limiter
    _limiter = None


# ============================================================================
# Exception Handler
# ============================================================================

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Handle rate limit exceeded errors.

    Returns a JSON response with rate limit info.

    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception

    Returns:
        JSONResponse with 429 status
    """
    # Get current user tier for informative response
    api_key = request.headers.get("X-API-Key")
    tier = "free"
    user_id = None

    if api_key:
        record = get_api_key(api_key)
        if record and record.is_active:
            user_id = record.user_id
            tier = get_user_tier(user_id)

    config = get_rate_limit_config()

    return JSONResponse(
        status_code=429,
        content={
            "error": "RateLimitExceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "tier": tier,
            "limits": {
                "requests_per_minute": config.get_rpm_for_tier(tier),
                "requests_per_hour": config.get_rph_for_tier(tier),
                "concurrent_jobs": config.get_concurrent_jobs_for_tier(tier),
            },
            "retry_after": getattr(exc, "retry_after", 60),
            "upgrade_info": "Contact support to upgrade your rate limit tier." if tier == "free" else None,
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Tier": tier,
        }
    )


# ============================================================================
# Decorators for Common Rate Limits
# ============================================================================

def limit_standard() -> Callable:
    """
    Standard rate limit decorator (uses default RPM).

    Usage:
        @router.get("/endpoint")
        @limit_standard()
        async def endpoint():
            ...
    """
    limiter = get_limiter()
    return limiter.limit(get_dynamic_rate_limit)


def limit_expensive(multiplier: int = 10) -> Callable:
    """
    Rate limit for expensive operations (lower limit).

    Args:
        multiplier: How many times more expensive than standard

    Usage:
        @router.post("/expensive")
        @limit_expensive(10)
        async def expensive_op():
            ...
    """
    limiter = get_limiter()

    def get_expensive_limit(request: Request) -> str:
        config = get_rate_limit_config()
        api_key = request.headers.get("X-API-Key")
        tier = "free"

        if api_key:
            record = get_api_key(api_key)
            if record and record.is_active:
                tier = get_user_tier(record.user_id)

        rpm = max(1, config.get_rpm_for_tier(tier) // multiplier)
        return f"{rpm}/minute"

    return limiter.limit(get_expensive_limit)


def limit_burst() -> Callable:
    """
    Burst rate limit (per second).

    Usage:
        @router.get("/fast")
        @limit_burst()
        async def fast_endpoint():
            ...
    """
    limiter = get_limiter()

    def get_burst_limit(request: Request) -> str:
        config = get_rate_limit_config()
        api_key = request.headers.get("X-API-Key")
        tier = "free"

        if api_key:
            record = get_api_key(api_key)
            if record and record.is_active:
                tier = get_user_tier(record.user_id)

        rps = config.get_rps_for_tier(tier)
        return f"{rps}/second"

    return limiter.limit(get_burst_limit)


# ============================================================================
# Job Concurrency Tracking
# ============================================================================

# Track active jobs per user
_ACTIVE_JOBS: Dict[str, int] = {}


def check_job_concurrency(user_id: str) -> bool:
    """
    Check if user can start a new job.

    Args:
        user_id: User ID

    Returns:
        True if allowed, False if at limit
    """
    config = get_rate_limit_config()
    tier = get_user_tier(user_id)
    max_jobs = config.get_concurrent_jobs_for_tier(tier)

    if max_jobs == -1:  # Unlimited
        return True

    current = _ACTIVE_JOBS.get(user_id, 0)
    return current < max_jobs


def increment_job_count(user_id: str) -> None:
    """Increment active job count for user."""
    _ACTIVE_JOBS[user_id] = _ACTIVE_JOBS.get(user_id, 0) + 1


def decrement_job_count(user_id: str) -> None:
    """Decrement active job count for user."""
    current = _ACTIVE_JOBS.get(user_id, 0)
    if current > 0:
        _ACTIVE_JOBS[user_id] = current - 1


def get_job_count(user_id: str) -> int:
    """Get current active job count for user."""
    return _ACTIVE_JOBS.get(user_id, 0)


def clear_job_counts() -> None:
    """Clear all job counts (for testing)."""
    _ACTIVE_JOBS.clear()
