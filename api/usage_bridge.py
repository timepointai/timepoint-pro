"""
Usage Bridge for CLI-to-API Integration.

Provides functions to record usage metrics from direct CLI execution
into the same storage used by the API, enabling unified quota tracking.

Phase 6: Public API - CLI Integration

This module bridges the gap between:
- Direct CLI execution (run_all_mechanism_tests.py, e2e_runner.py)
- API-based execution (batch_runner.py, simulation_runner.py)

Usage:
    from api.usage_bridge import UsageBridge

    # Initialize bridge with user ID
    bridge = UsageBridge(user_id="cli-user", tier="basic")

    # Before running simulation
    if not bridge.check_quota(simulation_count=1):
        print("Quota exceeded!")
        return

    # After simulation completes
    bridge.record_simulation(
        run_id="run_123",
        success=True,
        cost_usd=0.05,
        tokens=1500,
    )

    # Get current usage
    usage = bridge.get_usage()
    print(f"Simulations: {usage.simulations_used}/{usage.simulations_limit}")
"""

import os
import logging
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UsageSnapshot:
    """Current usage snapshot."""
    user_id: str
    tier: str
    period: str
    api_calls_used: int
    simulations_used: int
    cost_used_usd: float
    tokens_used: int
    api_calls_limit: int
    simulations_limit: int
    cost_limit_usd: float
    is_quota_exceeded: bool
    quota_exceeded_reason: Optional[str]


class UsageBridge:
    """
    Bridge for recording CLI usage in the API usage database.

    This enables unified quota tracking across both:
    - Direct CLI execution (bypasses API)
    - API-based execution (goes through REST endpoints)

    The bridge writes directly to the same usage database used by
    the API middleware, ensuring consistent tracking.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        tier: str = "basic",
        enabled: bool = True,
    ):
        """
        Initialize the usage bridge.

        Args:
            user_id: User identifier. Defaults to CLI_USER or from env.
            tier: User tier (free, basic, pro, enterprise). Defaults to basic.
            enabled: Whether to actually record usage. Set False for testing.
        """
        self.user_id = user_id or os.getenv("TIMEPOINT_USER_ID", "cli-user")
        self.tier = tier or os.getenv("TIMEPOINT_USER_TIER", "basic")
        self.enabled = enabled
        self._db = None
        self._quota_config = None

    def _get_db(self):
        """Lazy-load the usage database."""
        if self._db is None:
            try:
                from api.usage_storage import get_usage_database
                self._db = get_usage_database()
            except ImportError:
                logger.warning("Could not import usage_storage - usage tracking disabled")
                self.enabled = False
        return self._db

    def _get_quota_config(self):
        """Lazy-load quota configuration."""
        if self._quota_config is None:
            try:
                from api.middleware.usage_quota import get_quota_config
                self._quota_config = get_quota_config()
            except ImportError:
                logger.warning("Could not import usage_quota - using defaults")
                self._quota_config = None
        return self._quota_config

    def _get_tier_limits(self):
        """Get limits for current tier."""
        config = self._get_quota_config()
        if config and hasattr(config, 'tier_limits'):
            return config.tier_limits.get(self.tier, config.tier_limits.get("basic", {}))
        # Default limits
        return {
            "api_calls_limit": 10000,
            "simulations_limit": 100,
            "cost_limit_usd": 50.0,
            "max_batch_size": 20,
        }

    def check_quota(self, simulation_count: int = 1, estimated_cost: float = 0.0) -> bool:
        """
        Check if there's enough quota for the planned operation.

        Args:
            simulation_count: Number of simulations planned
            estimated_cost: Estimated cost in USD

        Returns:
            True if quota is available, False otherwise
        """
        if not self.enabled:
            return True

        db = self._get_db()
        if not db:
            return True

        limits = self._get_tier_limits()

        # Get current usage
        current = db.get_usage(self.user_id)

        # Check simulation limit - UsageRecord uses 'simulations_run' field
        simulations_used = getattr(current, 'simulations_run', 0) or getattr(current, 'simulations_used', 0)
        if simulations_used + simulation_count > limits.get("simulations_limit", 100):
            logger.warning(f"Simulation quota exceeded: {simulations_used} + {simulation_count} > {limits['simulations_limit']}")
            return False

        # Check cost limit - UsageRecord uses 'cost_usd' field
        cost_used = getattr(current, 'cost_usd', 0.0) or getattr(current, 'cost_used_usd', 0.0)
        if estimated_cost > 0:
            if cost_used + estimated_cost > limits.get("cost_limit_usd", 50.0):
                logger.warning(f"Cost quota exceeded: ${cost_used} + ${estimated_cost} > ${limits['cost_limit_usd']}")
                return False

        return True

    def record_simulation_start(self, run_id: str) -> None:
        """
        Record the start of a simulation.

        Args:
            run_id: Unique identifier for the simulation run
        """
        if not self.enabled:
            return

        try:
            from api.middleware.usage_quota import record_simulation_start
            record_simulation_start(self.user_id, run_id)
            logger.debug(f"Recorded simulation start: {run_id}")
        except ImportError:
            logger.debug("Usage quota module not available - skipping start recording")
        except Exception as e:
            logger.warning(f"Failed to record simulation start: {e}")

    def record_simulation(
        self,
        run_id: str,
        success: bool,
        cost_usd: float = 0.0,
        tokens: int = 0,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """
        Record completion of a simulation.

        Args:
            run_id: Unique identifier for the simulation run
            success: Whether the simulation completed successfully
            cost_usd: Actual cost incurred
            tokens: Number of tokens used
            duration_seconds: How long the simulation took
        """
        if not self.enabled:
            return

        try:
            from api.middleware.usage_quota import record_simulation_complete
            record_simulation_complete(
                user_id=self.user_id,
                job_id=run_id,
                success=success,
                cost_usd=cost_usd,
                tokens=tokens,
            )
            logger.debug(f"Recorded simulation complete: {run_id} (success={success}, cost=${cost_usd:.2f})")
        except ImportError:
            # Fall back to direct database recording
            db = self._get_db()
            if db:
                try:
                    db.record_simulation(
                        user_id=self.user_id,
                        success=success,
                        cost_usd=cost_usd,
                        tokens=tokens,
                    )
                except Exception as e:
                    logger.warning(f"Failed to record simulation to database: {e}")
        except Exception as e:
            logger.warning(f"Failed to record simulation: {e}")

    def record_api_call(self) -> None:
        """Record an API call (for tracking rate limits)."""
        if not self.enabled:
            return

        try:
            from api.middleware.usage_quota import record_api_call
            record_api_call(self.user_id)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Failed to record API call: {e}")

    def get_usage(self) -> Optional[UsageSnapshot]:
        """
        Get current usage snapshot.

        Returns:
            UsageSnapshot with current usage metrics, or None if unavailable
        """
        if not self.enabled:
            return None

        db = self._get_db()
        if not db:
            return None

        try:
            current = db.get_usage(self.user_id)
            limits = self._get_tier_limits()

            # Extract values with compatibility for different field names
            simulations_used = getattr(current, 'simulations_run', 0) or getattr(current, 'simulations_used', 0)
            cost_used = getattr(current, 'cost_usd', 0.0) or getattr(current, 'cost_used_usd', 0.0)
            api_calls_used = getattr(current, 'api_calls', 0) or getattr(current, 'api_calls_used', 0)
            tokens_used = getattr(current, 'tokens_used', 0)

            # Determine if quota is exceeded
            is_exceeded = False
            reason = None

            if simulations_used >= limits.get("simulations_limit", 100):
                is_exceeded = True
                reason = "Simulation limit exceeded"
            elif cost_used >= limits.get("cost_limit_usd", 50.0):
                is_exceeded = True
                reason = "Cost limit exceeded"

            return UsageSnapshot(
                user_id=self.user_id,
                tier=self.tier,
                period=current.period,
                api_calls_used=api_calls_used,
                simulations_used=simulations_used,
                cost_used_usd=cost_used,
                tokens_used=tokens_used,
                api_calls_limit=limits.get("api_calls_limit", 10000),
                simulations_limit=limits.get("simulations_limit", 100),
                cost_limit_usd=limits.get("cost_limit_usd", 50.0),
                is_quota_exceeded=is_exceeded,
                quota_exceeded_reason=reason,
            )
        except Exception as e:
            logger.warning(f"Failed to get usage: {e}")
            return None

    def print_usage_summary(self) -> None:
        """Print a formatted usage summary to stdout."""
        usage = self.get_usage()
        if not usage:
            print("Usage tracking not available")
            return

        print()
        print("=" * 60)
        print("USAGE SUMMARY")
        print("=" * 60)
        print(f"User: {usage.user_id}")
        print(f"Tier: {usage.tier.upper()}")
        print(f"Period: {usage.period}")
        print()
        print(f"Simulations: {usage.simulations_used:>6} / {usage.simulations_limit:>6}")
        print(f"Cost:        ${usage.cost_used_usd:>5.2f} / ${usage.cost_limit_usd:>5.2f}")
        print(f"Tokens:      {usage.tokens_used:>6,}")
        print()

        if usage.is_quota_exceeded:
            print(f"STATUS: QUOTA EXCEEDED - {usage.quota_exceeded_reason}")
        else:
            remaining_sims = usage.simulations_limit - usage.simulations_used
            remaining_cost = usage.cost_limit_usd - usage.cost_used_usd
            print(f"Remaining: {remaining_sims} simulations, ${remaining_cost:.2f}")

        print("=" * 60)


# ============================================================================
# Global Bridge Instance
# ============================================================================

_bridge: Optional[UsageBridge] = None


def get_usage_bridge(
    user_id: Optional[str] = None,
    tier: Optional[str] = None,
) -> UsageBridge:
    """
    Get or create the global usage bridge.

    Args:
        user_id: Override user ID (uses env var if not provided)
        tier: Override tier (uses env var if not provided)

    Returns:
        UsageBridge instance
    """
    global _bridge
    if _bridge is None:
        _bridge = UsageBridge(user_id=user_id, tier=tier)
    return _bridge


def reset_usage_bridge() -> None:
    """Reset the global usage bridge (for testing)."""
    global _bridge
    _bridge = None


# ============================================================================
# Convenience Functions
# ============================================================================

def check_cli_quota(simulation_count: int = 1) -> bool:
    """
    Check if CLI user has quota for simulations.

    Args:
        simulation_count: Number of simulations planned

    Returns:
        True if quota available, False otherwise
    """
    bridge = get_usage_bridge()
    return bridge.check_quota(simulation_count=simulation_count)


def record_cli_simulation(
    run_id: str,
    success: bool,
    cost_usd: float = 0.0,
    tokens: int = 0,
) -> None:
    """
    Record a CLI simulation completion.

    Args:
        run_id: Run identifier
        success: Whether simulation succeeded
        cost_usd: Cost incurred
        tokens: Tokens used
    """
    bridge = get_usage_bridge()
    bridge.record_simulation(
        run_id=run_id,
        success=success,
        cost_usd=cost_usd,
        tokens=tokens,
    )


def print_cli_usage() -> None:
    """Print CLI usage summary."""
    bridge = get_usage_bridge()
    bridge.print_usage_summary()
