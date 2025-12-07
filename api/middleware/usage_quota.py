"""
Usage quota middleware for the API.

Enforces monthly usage limits per tier (free, basic, pro, enterprise).
Tracks API calls, simulations, tokens, and cost.

Phase 6: Public API - Usage Quotas
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from ..auth import get_api_key
from ..usage_storage import get_usage_database, UsageRecord
from .rate_limit import get_user_tier


# ============================================================================
# Quota Configuration
# ============================================================================

@dataclass
class TierQuota:
    """Quota limits for a tier."""

    monthly_api_calls: int  # -1 = unlimited
    monthly_simulations: int
    monthly_cost_usd: float  # -1 = unlimited
    max_batch_size: int  # Max simulations per batch


@dataclass
class QuotaConfig:
    """Quota configuration for all tiers."""

    free: TierQuota = field(default_factory=lambda: TierQuota(
        monthly_api_calls=int(os.getenv("QUOTA_FREE_API_CALLS", "1000")),
        monthly_simulations=int(os.getenv("QUOTA_FREE_SIMULATIONS", "10")),
        monthly_cost_usd=float(os.getenv("QUOTA_FREE_COST_USD", "1.00")),
        max_batch_size=int(os.getenv("QUOTA_FREE_BATCH_SIZE", "5")),
    ))

    basic: TierQuota = field(default_factory=lambda: TierQuota(
        monthly_api_calls=int(os.getenv("QUOTA_BASIC_API_CALLS", "10000")),
        monthly_simulations=int(os.getenv("QUOTA_BASIC_SIMULATIONS", "100")),
        monthly_cost_usd=float(os.getenv("QUOTA_BASIC_COST_USD", "10.00")),
        max_batch_size=int(os.getenv("QUOTA_BASIC_BATCH_SIZE", "20")),
    ))

    pro: TierQuota = field(default_factory=lambda: TierQuota(
        monthly_api_calls=int(os.getenv("QUOTA_PRO_API_CALLS", "100000")),
        monthly_simulations=int(os.getenv("QUOTA_PRO_SIMULATIONS", "1000")),
        monthly_cost_usd=float(os.getenv("QUOTA_PRO_COST_USD", "100.00")),
        max_batch_size=int(os.getenv("QUOTA_PRO_BATCH_SIZE", "50")),
    ))

    enterprise: TierQuota = field(default_factory=lambda: TierQuota(
        monthly_api_calls=-1,  # Unlimited
        monthly_simulations=-1,
        monthly_cost_usd=-1,
        max_batch_size=100,
    ))

    # Enable/disable quota enforcement
    enabled: bool = field(default_factory=lambda: os.getenv(
        "USAGE_QUOTA_ENABLED", "true"
    ).lower() == "true")

    def get_quota_for_tier(self, tier: str) -> TierQuota:
        """Get quota for a tier."""
        return {
            "free": self.free,
            "basic": self.basic,
            "pro": self.pro,
            "enterprise": self.enterprise,
        }.get(tier, self.free)


# Global config instance
_config: Optional[QuotaConfig] = None


def get_quota_config() -> QuotaConfig:
    """Get quota configuration."""
    global _config
    if _config is None:
        _config = QuotaConfig()
    return _config


def reset_quota_config() -> None:
    """Reset quota config (for testing)."""
    global _config
    _config = None


# ============================================================================
# Quota Checking
# ============================================================================

@dataclass
class QuotaStatus:
    """Current quota status for a user."""

    user_id: str
    tier: str
    period: str
    days_remaining: int

    # Current usage
    api_calls_used: int
    simulations_used: int
    cost_used_usd: float
    tokens_used: int

    # Limits
    api_calls_limit: int
    simulations_limit: int
    cost_limit_usd: float
    max_batch_size: int

    # Computed
    api_calls_remaining: int
    simulations_remaining: int
    cost_remaining_usd: float

    # Status
    is_quota_exceeded: bool
    exceeded_reason: Optional[str] = None


def get_quota_status(user_id: str) -> QuotaStatus:
    """
    Get current quota status for a user.

    Args:
        user_id: User ID

    Returns:
        QuotaStatus with current usage and limits
    """
    config = get_quota_config()
    db = get_usage_database()
    tier = get_user_tier(user_id)
    quota = config.get_quota_for_tier(tier)

    # Get current usage
    usage = db.get_usage(user_id)
    period = db.current_period()
    days_remaining = db.days_remaining_in_period(period)

    # Calculate remaining
    api_remaining = (
        -1 if quota.monthly_api_calls == -1
        else max(0, quota.monthly_api_calls - usage.api_calls)
    )
    sim_remaining = (
        -1 if quota.monthly_simulations == -1
        else max(0, quota.monthly_simulations - usage.simulations_run)
    )
    cost_remaining = (
        -1 if quota.monthly_cost_usd == -1
        else max(0, quota.monthly_cost_usd - usage.cost_usd)
    )

    # Check if exceeded
    is_exceeded = False
    exceeded_reason = None

    if quota.monthly_api_calls != -1 and usage.api_calls >= quota.monthly_api_calls:
        is_exceeded = True
        exceeded_reason = "API call quota exceeded"
    elif quota.monthly_simulations != -1 and usage.simulations_run >= quota.monthly_simulations:
        is_exceeded = True
        exceeded_reason = "Simulation quota exceeded"
    elif quota.monthly_cost_usd != -1 and usage.cost_usd >= quota.monthly_cost_usd:
        is_exceeded = True
        exceeded_reason = "Cost quota exceeded"

    return QuotaStatus(
        user_id=user_id,
        tier=tier,
        period=period,
        days_remaining=days_remaining,
        api_calls_used=usage.api_calls,
        simulations_used=usage.simulations_run,
        cost_used_usd=usage.cost_usd,
        tokens_used=usage.tokens_used,
        api_calls_limit=quota.monthly_api_calls,
        simulations_limit=quota.monthly_simulations,
        cost_limit_usd=quota.monthly_cost_usd,
        max_batch_size=quota.max_batch_size,
        api_calls_remaining=api_remaining,
        simulations_remaining=sim_remaining,
        cost_remaining_usd=cost_remaining,
        is_quota_exceeded=is_exceeded,
        exceeded_reason=exceeded_reason,
    )


def check_api_call_quota(user_id: str) -> bool:
    """
    Check if user can make an API call.

    Args:
        user_id: User ID

    Returns:
        True if allowed, False if quota exceeded
    """
    config = get_quota_config()
    if not config.enabled:
        return True

    status = get_quota_status(user_id)
    return not status.is_quota_exceeded


def check_simulation_quota(user_id: str, count: int = 1) -> bool:
    """
    Check if user can run simulations.

    Args:
        user_id: User ID
        count: Number of simulations to run

    Returns:
        True if allowed, False if quota exceeded
    """
    config = get_quota_config()
    if not config.enabled:
        return True

    status = get_quota_status(user_id)

    if status.is_quota_exceeded:
        return False

    # Check if count would exceed limit
    if status.simulations_limit != -1:
        if status.simulations_used + count > status.simulations_limit:
            return False

    return True


def check_batch_size(user_id: str, batch_size: int) -> bool:
    """
    Check if batch size is within user's limit.

    Args:
        user_id: User ID
        batch_size: Number of simulations in batch

    Returns:
        True if allowed, False if too large
    """
    config = get_quota_config()
    tier = get_user_tier(user_id)
    quota = config.get_quota_for_tier(tier)

    return batch_size <= quota.max_batch_size


def check_cost_quota(user_id: str, estimated_cost: float) -> bool:
    """
    Check if estimated cost would exceed quota.

    Args:
        user_id: User ID
        estimated_cost: Estimated cost in USD

    Returns:
        True if allowed, False if would exceed
    """
    config = get_quota_config()
    if not config.enabled:
        return True

    status = get_quota_status(user_id)

    if status.cost_limit_usd == -1:
        return True

    return status.cost_used_usd + estimated_cost <= status.cost_limit_usd


# ============================================================================
# Usage Recording
# ============================================================================

def record_api_call(user_id: str) -> None:
    """
    Record an API call for quota tracking.

    Args:
        user_id: User ID
    """
    db = get_usage_database()
    db.increment_api_calls(user_id)
    db.log_event(user_id, "api_call")


def record_simulation_start(user_id: str, job_id: str) -> None:
    """
    Record a simulation start.

    Args:
        user_id: User ID
        job_id: Simulation job ID
    """
    db = get_usage_database()
    db.increment_simulations(user_id, started=1)
    db.log_event(user_id, "simulation_start", {"job_id": job_id})


def record_simulation_complete(
    user_id: str,
    job_id: str,
    success: bool,
    cost_usd: float = 0.0,
    tokens: int = 0
) -> None:
    """
    Record a simulation completion.

    Args:
        user_id: User ID
        job_id: Simulation job ID
        success: Whether simulation succeeded
        cost_usd: Cost in USD
        tokens: Tokens used
    """
    db = get_usage_database()

    if success:
        db.increment_simulations(user_id, completed=1)
    else:
        db.increment_simulations(user_id, failed=1)

    if cost_usd > 0 or tokens > 0:
        db.add_cost(user_id, cost_usd, tokens)

    db.log_event(user_id, "simulation_complete", {
        "job_id": job_id,
        "success": success,
        "cost_usd": cost_usd,
        "tokens": tokens,
    })


def record_batch_start(user_id: str, batch_id: str, job_count: int) -> None:
    """
    Record a batch start.

    Args:
        user_id: User ID
        batch_id: Batch ID
        job_count: Number of jobs in batch
    """
    db = get_usage_database()
    db.log_event(user_id, "batch_start", {
        "batch_id": batch_id,
        "job_count": job_count,
    })


# ============================================================================
# Quota Enforcement Middleware
# ============================================================================

async def quota_exceeded_response(
    user_id: str,
    status: QuotaStatus
) -> JSONResponse:
    """
    Create quota exceeded response.

    Args:
        user_id: User ID
        status: Current quota status

    Returns:
        JSONResponse with 429 status
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "QuotaExceeded",
            "message": status.exceeded_reason or "Monthly quota exceeded",
            "tier": status.tier,
            "period": status.period,
            "days_remaining": status.days_remaining,
            "usage": {
                "api_calls": status.api_calls_used,
                "simulations": status.simulations_used,
                "cost_usd": status.cost_used_usd,
            },
            "limits": {
                "api_calls": status.api_calls_limit,
                "simulations": status.simulations_limit,
                "cost_usd": status.cost_limit_usd,
            },
            "upgrade_info": (
                "Contact support to upgrade your tier for higher limits."
                if status.tier == "free" else None
            ),
        },
        headers={
            "X-Quota-Tier": status.tier,
            "X-Quota-Period": status.period,
        }
    )


def enforce_api_quota(user_id: str) -> None:
    """
    Enforce API call quota, raise exception if exceeded.

    Args:
        user_id: User ID

    Raises:
        HTTPException: If quota exceeded
    """
    config = get_quota_config()
    if not config.enabled:
        return

    if not check_api_call_quota(user_id):
        status = get_quota_status(user_id)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "QuotaExceeded",
                "message": status.exceeded_reason or "Monthly quota exceeded",
                "tier": status.tier,
                "period": status.period,
            }
        )


def enforce_simulation_quota(user_id: str, count: int = 1) -> None:
    """
    Enforce simulation quota, raise exception if exceeded.

    Args:
        user_id: User ID
        count: Number of simulations to run

    Raises:
        HTTPException: If quota exceeded
    """
    config = get_quota_config()
    if not config.enabled:
        return

    if not check_simulation_quota(user_id, count):
        status = get_quota_status(user_id)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "SimulationQuotaExceeded",
                "message": f"Cannot run {count} simulation(s). {status.simulations_remaining} remaining.",
                "tier": status.tier,
                "simulations_used": status.simulations_used,
                "simulations_limit": status.simulations_limit,
            }
        )


def enforce_batch_size(user_id: str, batch_size: int) -> None:
    """
    Enforce batch size limit, raise exception if exceeded.

    Args:
        user_id: User ID
        batch_size: Number of simulations in batch

    Raises:
        HTTPException: If batch too large
    """
    config = get_quota_config()
    tier = get_user_tier(user_id)
    quota = config.get_quota_for_tier(tier)

    if batch_size > quota.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "BatchTooLarge",
                "message": f"Batch size {batch_size} exceeds limit of {quota.max_batch_size} for {tier} tier",
                "tier": tier,
                "max_batch_size": quota.max_batch_size,
            }
        )


def enforce_cost_quota(user_id: str, estimated_cost: float) -> None:
    """
    Enforce cost quota, raise exception if would exceed.

    Args:
        user_id: User ID
        estimated_cost: Estimated cost in USD

    Raises:
        HTTPException: If would exceed quota
    """
    config = get_quota_config()
    if not config.enabled:
        return

    if not check_cost_quota(user_id, estimated_cost):
        status = get_quota_status(user_id)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "CostQuotaExceeded",
                "message": f"Estimated cost ${estimated_cost:.2f} would exceed remaining ${status.cost_remaining_usd:.2f}",
                "tier": status.tier,
                "cost_used_usd": status.cost_used_usd,
                "cost_limit_usd": status.cost_limit_usd,
            }
        )
