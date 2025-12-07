"""
Unit tests for usage quota system.

Tests usage tracking, quota enforcement, and storage.
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

# Usage storage imports
from api.usage_storage import (
    UsageDatabase,
    UsageRecord,
    get_usage_database,
    reset_usage_database,
)

# Quota middleware imports
from api.middleware.usage_quota import (
    QuotaConfig,
    TierQuota,
    QuotaStatus,
    get_quota_config,
    reset_quota_config,
    get_quota_status,
    check_api_call_quota,
    check_simulation_quota,
    check_batch_size,
    check_cost_quota,
    record_api_call,
    record_simulation_start,
    record_simulation_complete,
)

# Rate limit imports (for tier management)
from api.middleware.rate_limit import (
    set_user_tier,
    clear_user_tiers,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_state():
    """Reset all state before each test."""
    reset_usage_database()
    reset_quota_config()
    clear_user_tiers()
    yield
    reset_usage_database()
    reset_quota_config()
    clear_user_tiers()


@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    """Create temporary database path."""
    return str(tmp_path / "test_usage.db")


@pytest.fixture
def usage_db(tmp_db_path) -> UsageDatabase:
    """Create test usage database."""
    return UsageDatabase(tmp_db_path)


@pytest.fixture
def test_user_id() -> str:
    """Test user ID."""
    return "test-user-123"


# ============================================================================
# Usage Database Tests
# ============================================================================

class TestUsageDatabase:
    """Tests for UsageDatabase."""

    def test_get_usage_creates_record(self, usage_db, test_user_id):
        """Getting usage for new user creates record."""
        usage = usage_db.get_usage(test_user_id)

        assert usage.user_id == test_user_id
        assert usage.api_calls == 0
        assert usage.simulations_run == 0
        assert usage.cost_usd == 0.0

    def test_increment_api_calls(self, usage_db, test_user_id):
        """Incrementing API calls updates record."""
        usage_db.increment_api_calls(test_user_id, 5)
        usage = usage_db.get_usage(test_user_id)

        assert usage.api_calls == 5

    def test_increment_api_calls_multiple(self, usage_db, test_user_id):
        """Multiple increments accumulate."""
        usage_db.increment_api_calls(test_user_id, 3)
        usage_db.increment_api_calls(test_user_id, 7)
        usage = usage_db.get_usage(test_user_id)

        assert usage.api_calls == 10

    def test_increment_simulations(self, usage_db, test_user_id):
        """Incrementing simulation counts works."""
        usage_db.increment_simulations(test_user_id, started=2, completed=1, failed=1)
        usage = usage_db.get_usage(test_user_id)

        assert usage.simulations_run == 2
        assert usage.simulations_completed == 1
        assert usage.simulations_failed == 1

    def test_add_cost(self, usage_db, test_user_id):
        """Adding cost updates record."""
        usage_db.add_cost(test_user_id, 0.50, tokens=1000)
        usage = usage_db.get_usage(test_user_id)

        assert usage.cost_usd == 0.50
        assert usage.tokens_used == 1000

    def test_add_cost_accumulates(self, usage_db, test_user_id):
        """Multiple cost additions accumulate."""
        usage_db.add_cost(test_user_id, 0.25, tokens=500)
        usage_db.add_cost(test_user_id, 0.75, tokens=1500)
        usage = usage_db.get_usage(test_user_id)

        assert usage.cost_usd == 1.00
        assert usage.tokens_used == 2000

    def test_current_period_format(self, usage_db):
        """Current period has correct format."""
        period = usage_db.current_period()

        assert len(period) == 7  # YYYY-MM
        assert period[4] == "-"

    def test_usage_history(self, usage_db, test_user_id):
        """Get usage history returns records."""
        # Create usage for current period
        usage_db.increment_api_calls(test_user_id, 10)

        history = usage_db.get_usage_history(test_user_id)

        assert len(history) >= 1
        assert history[0].api_calls == 10

    def test_log_event(self, usage_db, test_user_id):
        """Logging events works."""
        event_id = usage_db.log_event(
            test_user_id,
            "test_event",
            {"key": "value"}
        )

        assert event_id is not None
        assert len(event_id) == 36  # UUID format

    def test_get_recent_events(self, usage_db, test_user_id):
        """Getting recent events works."""
        usage_db.log_event(test_user_id, "event1")
        usage_db.log_event(test_user_id, "event2")

        events = usage_db.get_recent_events(test_user_id)

        assert len(events) == 2
        # Most recent first
        assert events[0]["event_type"] == "event2"

    def test_get_stats(self, usage_db, test_user_id):
        """Get stats returns aggregate data."""
        usage_db.increment_api_calls(test_user_id, 100)
        usage_db.add_cost(test_user_id, 1.50)

        stats = usage_db.get_stats()

        assert stats["active_users"] >= 1
        assert stats["total_api_calls"] >= 100
        assert stats["total_cost_usd"] >= 1.50


# ============================================================================
# Quota Config Tests
# ============================================================================

class TestQuotaConfig:
    """Tests for QuotaConfig."""

    def test_default_free_tier_limits(self):
        """Free tier has expected default limits."""
        config = QuotaConfig()

        assert config.free.monthly_api_calls == 1000
        assert config.free.monthly_simulations == 10
        assert config.free.monthly_cost_usd == 1.00
        assert config.free.max_batch_size == 5

    def test_enterprise_tier_unlimited(self):
        """Enterprise tier has unlimited quotas."""
        config = QuotaConfig()

        assert config.enterprise.monthly_api_calls == -1
        assert config.enterprise.monthly_simulations == -1
        assert config.enterprise.monthly_cost_usd == -1

    def test_get_quota_for_tier(self):
        """Get quota by tier name works."""
        config = QuotaConfig()

        free_quota = config.get_quota_for_tier("free")
        pro_quota = config.get_quota_for_tier("pro")

        assert free_quota.monthly_api_calls == 1000
        assert pro_quota.monthly_api_calls == 100000

    def test_unknown_tier_defaults_to_free(self):
        """Unknown tier defaults to free limits."""
        config = QuotaConfig()

        quota = config.get_quota_for_tier("unknown")

        assert quota.monthly_api_calls == config.free.monthly_api_calls


# ============================================================================
# Quota Status Tests
# ============================================================================

class TestQuotaStatus:
    """Tests for quota status checking."""

    def test_get_quota_status_new_user(self, tmp_db_path, test_user_id):
        """New user has full quota remaining."""
        # Set up database
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        status = get_quota_status(test_user_id)

        assert status.user_id == test_user_id
        assert status.tier == "free"
        assert status.api_calls_used == 0
        assert status.api_calls_remaining == 1000
        assert status.is_quota_exceeded is False

    def test_get_quota_status_with_usage(self, tmp_db_path, test_user_id):
        """Status reflects actual usage."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        # Add some usage
        db = UsageDatabase(tmp_db_path)
        db.increment_api_calls(test_user_id, 500)
        db.increment_simulations(test_user_id, started=5)

        status = get_quota_status(test_user_id)

        assert status.api_calls_used == 500
        assert status.api_calls_remaining == 500
        assert status.simulations_used == 5
        assert status.simulations_remaining == 5

    def test_quota_exceeded_api_calls(self, tmp_db_path, test_user_id):
        """Quota exceeded when API calls exceed limit."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        db = UsageDatabase(tmp_db_path)
        db.increment_api_calls(test_user_id, 1000)

        status = get_quota_status(test_user_id)

        assert status.is_quota_exceeded is True
        assert "API call" in status.exceeded_reason

    def test_quota_exceeded_simulations(self, tmp_db_path, test_user_id):
        """Quota exceeded when simulations exceed limit."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        db = UsageDatabase(tmp_db_path)
        db.increment_simulations(test_user_id, started=10)

        status = get_quota_status(test_user_id)

        assert status.is_quota_exceeded is True
        assert "Simulation" in status.exceeded_reason

    def test_pro_tier_higher_limits(self, tmp_db_path, test_user_id):
        """Pro tier has higher limits."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path
        set_user_tier(test_user_id, "pro")

        status = get_quota_status(test_user_id)

        assert status.tier == "pro"
        assert status.api_calls_limit == 100000
        assert status.simulations_limit == 1000

    def test_enterprise_tier_unlimited(self, tmp_db_path, test_user_id):
        """Enterprise tier has unlimited quota."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path
        set_user_tier(test_user_id, "enterprise")

        # Add lots of usage
        db = UsageDatabase(tmp_db_path)
        db.increment_api_calls(test_user_id, 1000000)
        db.increment_simulations(test_user_id, started=10000)

        status = get_quota_status(test_user_id)

        assert status.tier == "enterprise"
        assert status.is_quota_exceeded is False
        assert status.api_calls_remaining == -1


# ============================================================================
# Quota Check Tests
# ============================================================================

class TestQuotaChecks:
    """Tests for quota check functions."""

    def test_check_api_call_quota_allowed(self, tmp_db_path, test_user_id):
        """API calls allowed when under quota."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        result = check_api_call_quota(test_user_id)

        assert result is True

    def test_check_api_call_quota_exceeded(self, tmp_db_path, test_user_id):
        """API calls blocked when quota exceeded."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        db = UsageDatabase(tmp_db_path)
        db.increment_api_calls(test_user_id, 1000)

        result = check_api_call_quota(test_user_id)

        assert result is False

    def test_check_simulation_quota_allowed(self, tmp_db_path, test_user_id):
        """Simulations allowed when under quota."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        result = check_simulation_quota(test_user_id, count=5)

        assert result is True

    def test_check_simulation_quota_exceeded(self, tmp_db_path, test_user_id):
        """Simulations blocked when would exceed quota."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        db = UsageDatabase(tmp_db_path)
        db.increment_simulations(test_user_id, started=8)

        # Trying to run 5 more would exceed limit of 10
        result = check_simulation_quota(test_user_id, count=5)

        assert result is False

    def test_check_batch_size_allowed(self, test_user_id):
        """Batch size within limit is allowed."""
        result = check_batch_size(test_user_id, 5)

        assert result is True

    def test_check_batch_size_exceeded(self, test_user_id):
        """Batch size over limit is blocked."""
        # Free tier limit is 5
        result = check_batch_size(test_user_id, 10)

        assert result is False

    def test_check_batch_size_pro_tier(self, test_user_id):
        """Pro tier has higher batch limit."""
        set_user_tier(test_user_id, "pro")

        result = check_batch_size(test_user_id, 50)

        assert result is True

    def test_check_cost_quota_allowed(self, tmp_db_path, test_user_id):
        """Cost within quota is allowed."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        result = check_cost_quota(test_user_id, 0.50)

        assert result is True

    def test_check_cost_quota_exceeded(self, tmp_db_path, test_user_id):
        """Cost exceeding quota is blocked."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        db = UsageDatabase(tmp_db_path)
        db.add_cost(test_user_id, 0.90)

        # Adding 0.20 would exceed $1.00 limit
        result = check_cost_quota(test_user_id, 0.20)

        assert result is False


# ============================================================================
# Usage Recording Tests
# ============================================================================

class TestUsageRecording:
    """Tests for usage recording functions."""

    def test_record_api_call(self, tmp_db_path, test_user_id):
        """Recording API call increments counter."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        record_api_call(test_user_id)
        record_api_call(test_user_id)

        db = UsageDatabase(tmp_db_path)
        usage = db.get_usage(test_user_id)

        assert usage.api_calls == 2

    def test_record_simulation_start(self, tmp_db_path, test_user_id):
        """Recording simulation start increments counter."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        record_simulation_start(test_user_id, "job-123")

        db = UsageDatabase(tmp_db_path)
        usage = db.get_usage(test_user_id)

        assert usage.simulations_run == 1

    def test_record_simulation_complete_success(self, tmp_db_path, test_user_id):
        """Recording successful simulation updates stats."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        record_simulation_start(test_user_id, "job-123")
        record_simulation_complete(
            test_user_id,
            "job-123",
            success=True,
            cost_usd=0.05,
            tokens=1000
        )

        db = UsageDatabase(tmp_db_path)
        usage = db.get_usage(test_user_id)

        assert usage.simulations_completed == 1
        assert usage.cost_usd == 0.05
        assert usage.tokens_used == 1000

    def test_record_simulation_complete_failure(self, tmp_db_path, test_user_id):
        """Recording failed simulation updates failure count."""
        os.environ["USAGE_DB_PATH"] = tmp_db_path

        record_simulation_start(test_user_id, "job-123")
        record_simulation_complete(
            test_user_id,
            "job-123",
            success=False
        )

        db = UsageDatabase(tmp_db_path)
        usage = db.get_usage(test_user_id)

        assert usage.simulations_failed == 1


# ============================================================================
# Run configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
