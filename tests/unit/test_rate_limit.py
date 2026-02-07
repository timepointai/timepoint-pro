"""
Unit tests for rate limiting middleware.

Tests the rate limiting configuration and key extraction logic.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

# Import the rate limit module
from api.middleware.rate_limit import (
    RateLimitConfig,
    get_rate_limit_config,
    get_user_tier,
    set_user_tier,
    clear_user_tiers,
    get_rate_limit_key,
    get_dynamic_rate_limit,
    check_job_concurrency,
    increment_job_count,
    decrement_job_count,
    get_job_count,
    clear_job_counts,
    reset_limiter,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_config(self):
        """Test default configuration values (without env var interference)."""
        import os
        # RateLimitConfig reads from env vars at construction time;
        # clear any that other tests may have set to ensure clean defaults
        rate_env_vars = [k for k in os.environ if k.startswith("RATE_LIMIT_")]
        saved = {k: os.environ.pop(k) for k in rate_env_vars}
        try:
            config = RateLimitConfig()

            # Check defaults
            assert config.free_rpm == 10
            assert config.basic_rpm == 60
            assert config.pro_rpm == 300
            assert config.enterprise_rpm == 1000
            assert config.enabled is True
        finally:
            os.environ.update(saved)

    def test_get_rpm_for_tier(self):
        """Test getting RPM for different tiers."""
        config = RateLimitConfig()

        assert config.get_rpm_for_tier("free") == 10
        assert config.get_rpm_for_tier("basic") == 60
        assert config.get_rpm_for_tier("pro") == 300
        assert config.get_rpm_for_tier("enterprise") == 1000
        assert config.get_rpm_for_tier("unknown") == 10  # Falls back to free

    def test_get_concurrent_jobs_for_tier(self):
        """Test concurrent job limits per tier."""
        config = RateLimitConfig()

        assert config.get_concurrent_jobs_for_tier("free") == 1
        assert config.get_concurrent_jobs_for_tier("basic") == 3
        assert config.get_concurrent_jobs_for_tier("pro") == 10
        assert config.get_concurrent_jobs_for_tier("enterprise") == -1  # Unlimited


class TestUserTiers:
    """Tests for user tier management."""

    def setup_method(self):
        """Clear tiers before each test."""
        clear_user_tiers()

    def teardown_method(self):
        """Clear tiers after each test."""
        clear_user_tiers()

    def test_default_tier(self):
        """Test that default tier is 'free'."""
        assert get_user_tier("unknown_user") == "free"

    def test_set_and_get_tier(self):
        """Test setting and getting user tier."""
        set_user_tier("user1", "pro")
        assert get_user_tier("user1") == "pro"

    def test_invalid_tier(self):
        """Test that invalid tier raises error."""
        with pytest.raises(ValueError):
            set_user_tier("user1", "invalid_tier")

    def test_clear_tiers(self):
        """Test clearing all tiers."""
        set_user_tier("user1", "pro")
        set_user_tier("user2", "basic")
        clear_user_tiers()
        assert get_user_tier("user1") == "free"
        assert get_user_tier("user2") == "free"


class TestJobConcurrency:
    """Tests for job concurrency tracking."""

    def setup_method(self):
        """Clear job counts before each test."""
        clear_job_counts()
        clear_user_tiers()

    def teardown_method(self):
        """Clear job counts after each test."""
        clear_job_counts()
        clear_user_tiers()

    def test_initial_job_count(self):
        """Test that initial job count is 0."""
        assert get_job_count("user1") == 0

    def test_increment_job_count(self):
        """Test incrementing job count."""
        increment_job_count("user1")
        assert get_job_count("user1") == 1
        increment_job_count("user1")
        assert get_job_count("user1") == 2

    def test_decrement_job_count(self):
        """Test decrementing job count."""
        increment_job_count("user1")
        increment_job_count("user1")
        decrement_job_count("user1")
        assert get_job_count("user1") == 1

    def test_decrement_at_zero(self):
        """Test that decrement at zero stays at zero."""
        decrement_job_count("user1")
        assert get_job_count("user1") == 0

    def test_check_concurrency_free_tier(self):
        """Test concurrency check for free tier (limit 1)."""
        # Free tier allows 1 job
        assert check_job_concurrency("user1") is True

        increment_job_count("user1")
        # Now at limit
        assert check_job_concurrency("user1") is False

    def test_check_concurrency_pro_tier(self):
        """Test concurrency check for pro tier (limit 10)."""
        set_user_tier("user1", "pro")

        # Pro tier allows 10 jobs
        for _ in range(10):
            assert check_job_concurrency("user1") is True
            increment_job_count("user1")

        # Now at limit
        assert check_job_concurrency("user1") is False

    def test_check_concurrency_enterprise_unlimited(self):
        """Test concurrency check for enterprise (unlimited)."""
        set_user_tier("user1", "enterprise")

        # Enterprise is unlimited
        for _ in range(100):
            assert check_job_concurrency("user1") is True
            increment_job_count("user1")


class TestRateLimitKeyExtraction:
    """Tests for rate limit key extraction."""

    def setup_method(self):
        """Clear API keys before each test."""
        from api.auth import clear_api_keys
        clear_api_keys()

    def teardown_method(self):
        """Clear API keys after each test."""
        from api.auth import clear_api_keys
        clear_api_keys()

    def test_key_from_ip_no_api_key(self):
        """Test that IP is used when no API key provided."""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        key = get_rate_limit_key(request)
        assert key == "ip:192.168.1.1"

    def test_key_from_api_key(self):
        """Test that user_id is used when valid API key provided."""
        from api.auth import create_api_key

        api_key = create_api_key("test_user", "test key")

        request = Mock()
        request.headers = {"X-API-Key": api_key}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        key = get_rate_limit_key(request)
        assert key == "user:test_user"

    def test_key_fallback_invalid_api_key(self):
        """Test fallback to IP when API key is invalid."""
        request = Mock()
        request.headers = {"X-API-Key": "invalid_key"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        key = get_rate_limit_key(request)
        assert key == "ip:192.168.1.1"


class TestDynamicRateLimit:
    """Tests for dynamic rate limit calculation."""

    def setup_method(self):
        """Clear state before each test."""
        from api.auth import clear_api_keys
        clear_api_keys()
        clear_user_tiers()

    def teardown_method(self):
        """Clear state after each test."""
        from api.auth import clear_api_keys
        clear_api_keys()
        clear_user_tiers()

    def test_dynamic_limit_no_api_key(self):
        """Test dynamic limit for unauthenticated request."""
        request = Mock()
        request.headers = {}

        limit = get_dynamic_rate_limit(request)
        assert limit == "10/minute"  # Free tier default

    def test_dynamic_limit_pro_tier(self):
        """Test dynamic limit for pro tier user."""
        from api.auth import create_api_key

        api_key = create_api_key("pro_user", "pro key")
        set_user_tier("pro_user", "pro")

        request = Mock()
        request.headers = {"X-API-Key": api_key}

        limit = get_dynamic_rate_limit(request)
        assert limit == "300/minute"  # Pro tier
