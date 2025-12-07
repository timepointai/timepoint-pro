"""
Unit tests for Batch API.

Tests batch submission, status tracking, and cancellation.
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

# API imports
from api.main import create_app
from api.auth import (
    create_api_key,
    clear_api_keys,
    API_KEY_HEADER,
)
from api.deps import (
    override_db_path,
    reset_dependencies,
)
from api.batch_runner import (
    clear_batches,
    reset_batch_runner,
    get_batch,
    BatchJob,
)
from api.simulation_runner import (
    clear_jobs,
    reset_simulation_runner,
)
from api.models_batch import (
    BatchStatus,
    BatchPriority,
    BatchCreateRequest,
)
from api.middleware.rate_limit import (
    set_user_tier,
    clear_user_tiers,
    clear_job_counts,
    reset_limiter,
    reset_rate_limit_config,
    get_limiter,
)
from api.middleware.usage_quota import reset_quota_config
from api.usage_storage import reset_usage_database


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_state():
    """Reset all state before each test."""
    clear_api_keys()
    reset_dependencies()
    clear_batches()
    reset_batch_runner()
    clear_jobs()
    reset_simulation_runner()
    clear_user_tiers()
    clear_job_counts()
    # DON'T reset limiter - decorators capture it at import time
    # Instead just disable it (done in tmp_db_path fixture)
    reset_quota_config()
    reset_usage_database()
    yield
    clear_api_keys()
    reset_dependencies()
    clear_batches()
    reset_batch_runner()
    clear_jobs()
    reset_simulation_runner()
    clear_user_tiers()
    clear_job_counts()
    reset_quota_config()
    reset_usage_database()


@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    """Create temporary database path."""
    db_path = str(tmp_path / "test_api.db")
    usage_path = str(tmp_path / "test_usage.db")
    os.environ["USAGE_DB_PATH"] = usage_path
    # Disable rate limiting for tests
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    # Also disable the limiter at runtime (since decorators capture it at import time)
    limiter = get_limiter()
    limiter.enabled = False
    return db_path


@pytest.fixture
def test_user_id() -> str:
    """Test user ID."""
    return "test-user-alice"


@pytest.fixture
def test_api_key(test_user_id) -> str:
    """Create test API key."""
    return create_api_key(test_user_id, "Test Key")


@pytest.fixture
def client(tmp_db_path, test_api_key) -> TestClient:
    """Create test client with temporary database."""
    override_db_path(tmp_db_path)
    app = create_app(debug=True)
    return TestClient(app)


@pytest.fixture
def auth_headers(test_api_key) -> dict:
    """Headers with API key."""
    return {API_KEY_HEADER: test_api_key}


@pytest.fixture
def sample_batch_data() -> dict:
    """Sample batch creation data."""
    return {
        "simulations": [
            {
                "template_id": "core_template",
                "entity_count": 3,
                "timepoint_count": 3,
            },
            {
                "template_id": "core_template",
                "entity_count": 3,
                "timepoint_count": 3,
            },
        ],
        "priority": "normal",
        "fail_fast": False,
    }


@pytest.fixture
def pro_user_id() -> str:
    """Pro tier user ID."""
    return "test-user-pro"


@pytest.fixture
def pro_api_key(pro_user_id) -> str:
    """Create pro tier API key."""
    key = create_api_key(pro_user_id, "Pro Key")
    set_user_tier(pro_user_id, "pro")
    return key


@pytest.fixture
def pro_auth_headers(pro_api_key) -> dict:
    """Headers with pro tier API key."""
    return {API_KEY_HEADER: pro_api_key}


# ============================================================================
# Batch Model Tests
# ============================================================================

class TestBatchModels:
    """Tests for batch Pydantic models."""

    def test_batch_create_valid(self, sample_batch_data):
        """Valid batch request should pass."""
        request = BatchCreateRequest(**sample_batch_data)

        assert len(request.simulations) == 2
        assert request.priority == BatchPriority.NORMAL
        assert request.fail_fast is False

    def test_batch_create_min_simulations(self):
        """Batch must have at least 2 simulations."""
        with pytest.raises(ValueError):
            BatchCreateRequest(
                simulations=[
                    {"template_id": "test", "entity_count": 3, "timepoint_count": 3}
                ]
            )

    def test_batch_create_max_simulations(self):
        """Batch cannot exceed 100 simulations."""
        simulations = [
            {"template_id": "test", "entity_count": 3, "timepoint_count": 3}
            for _ in range(101)
        ]

        with pytest.raises(ValueError):
            BatchCreateRequest(simulations=simulations)

    def test_batch_create_with_budget(self, sample_batch_data):
        """Batch with budget cap is valid."""
        sample_batch_data["budget_cap_usd"] = 5.00
        request = BatchCreateRequest(**sample_batch_data)

        assert request.budget_cap_usd == 5.00

    def test_batch_create_with_fail_fast(self, sample_batch_data):
        """Fail-fast mode can be enabled."""
        sample_batch_data["fail_fast"] = True
        request = BatchCreateRequest(**sample_batch_data)

        assert request.fail_fast is True


# ============================================================================
# Batch Creation Tests
# ============================================================================

class TestBatchCreation:
    """Tests for batch creation endpoint."""

    def test_create_batch_success(self, client, auth_headers, sample_batch_data):
        """Creating batch should succeed."""
        response = client.post(
            "/simulations/batch",
            json=sample_batch_data,
            headers=auth_headers,
        )

        assert response.status_code == 202

        data = response.json()
        assert "batch_id" in data
        assert data["status"] in ("pending", "running")
        assert len(data["job_ids"]) == 2
        assert data["progress"]["total_jobs"] == 2

    def test_create_batch_without_auth_fails(self, client, sample_batch_data):
        """Creating batch without auth should fail."""
        response = client.post("/simulations/batch", json=sample_batch_data)

        assert response.status_code in (401, 403)

    def test_create_batch_with_priority(self, client, auth_headers, sample_batch_data):
        """Creating batch with priority works."""
        sample_batch_data["priority"] = "high"
        response = client.post(
            "/simulations/batch",
            json=sample_batch_data,
            headers=auth_headers,
        )

        assert response.status_code == 202
        assert response.json()["priority"] == "high"

    def test_create_batch_exceeds_tier_size_limit(self, client, auth_headers):
        """Batch exceeding tier size limit should fail."""
        # Free tier limit is 5
        simulations = [
            {"template_id": "test", "entity_count": 3, "timepoint_count": 3}
            for _ in range(10)
        ]

        response = client.post(
            "/simulations/batch",
            json={"simulations": simulations},
            headers=auth_headers,
        )

        # Should fail with 400 (batch too large) - batch size check happens before quota check
        assert response.status_code == 400
        data = response.json()
        # FastAPI wraps detail in different ways, check both
        if isinstance(data.get("detail"), dict):
            assert "BatchTooLarge" in data["detail"]["error"]
        else:
            assert "BatchTooLarge" in str(data)

    def test_create_batch_pro_tier_larger(self, client, pro_auth_headers):
        """Pro tier can create larger batches."""
        simulations = [
            {"template_id": "test", "entity_count": 3, "timepoint_count": 3}
            for _ in range(20)
        ]

        response = client.post(
            "/simulations/batch",
            json={"simulations": simulations},
            headers=pro_auth_headers,
        )

        assert response.status_code == 202
        assert len(response.json()["job_ids"]) == 20


# ============================================================================
# Batch Status Tests
# ============================================================================

class TestBatchStatus:
    """Tests for batch status endpoint."""

    def test_get_batch_success(self, client, auth_headers, sample_batch_data):
        """Getting batch status should succeed."""
        # Create batch
        create_resp = client.post(
            "/simulations/batch",
            json=sample_batch_data,
            headers=auth_headers,
        )
        batch_id = create_resp.json()["batch_id"]

        # Get status
        response = client.get(
            f"/simulations/batch/{batch_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()
        assert data["batch_id"] == batch_id
        assert "progress" in data
        assert "cost" in data

    def test_get_nonexistent_batch_fails(self, client, auth_headers):
        """Getting nonexistent batch should fail."""
        response = client.get(
            "/simulations/batch/nonexistent-id",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_get_other_users_batch_fails(self, client, sample_batch_data, test_api_key):
        """Cannot access other user's batch."""
        # Create batch as alice
        alice_headers = {API_KEY_HEADER: test_api_key}
        create_resp = client.post(
            "/simulations/batch",
            json=sample_batch_data,
            headers=alice_headers,
        )
        batch_id = create_resp.json()["batch_id"]

        # Try to access as bob
        bob_key = create_api_key("bob", "Bob Key")
        bob_headers = {API_KEY_HEADER: bob_key}

        response = client.get(
            f"/simulations/batch/{batch_id}",
            headers=bob_headers,
        )

        assert response.status_code == 403


# ============================================================================
# Batch Jobs Tests
# ============================================================================

class TestBatchJobs:
    """Tests for batch job listing endpoint."""

    def test_get_batch_jobs(self, client, auth_headers, sample_batch_data):
        """Getting batch with jobs should include job details."""
        # Create batch
        create_resp = client.post(
            "/simulations/batch",
            json=sample_batch_data,
            headers=auth_headers,
        )
        batch_id = create_resp.json()["batch_id"]

        # Get with jobs
        response = client.get(
            f"/simulations/batch/{batch_id}/jobs",
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()
        assert "batch" in data
        assert "jobs" in data
        assert len(data["jobs"]) == 2


# ============================================================================
# Batch Cancellation Tests
# ============================================================================

class TestBatchCancellation:
    """Tests for batch cancellation endpoint."""

    def test_cancel_batch_success(self, client, auth_headers, sample_batch_data):
        """Cancelling batch should succeed."""
        # Create batch
        create_resp = client.post(
            "/simulations/batch",
            json=sample_batch_data,
            headers=auth_headers,
        )
        batch_id = create_resp.json()["batch_id"]

        # Cancel
        response = client.post(
            f"/simulations/batch/{batch_id}/cancel",
            json={"reason": "Testing cancellation"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_nonexistent_batch_fails(self, client, auth_headers):
        """Cancelling nonexistent batch should fail."""
        response = client.post(
            "/simulations/batch/nonexistent-id/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 404


# ============================================================================
# Batch List Tests
# ============================================================================

class TestBatchList:
    """Tests for batch listing endpoint."""

    def test_list_batches(self, client, auth_headers, sample_batch_data):
        """Listing batches should work."""
        # Create multiple batches
        for _ in range(3):
            client.post(
                "/simulations/batch",
                json=sample_batch_data,
                headers=auth_headers,
            )

        # List
        response = client.get(
            "/simulations/batch",
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 3
        assert len(data["batches"]) >= 3

    def test_list_batches_pagination(self, client, auth_headers, sample_batch_data):
        """Batch list supports pagination."""
        # Create batches
        for _ in range(5):
            client.post(
                "/simulations/batch",
                json=sample_batch_data,
                headers=auth_headers,
            )

        # Get page 1
        response = client.get(
            "/simulations/batch?page=1&page_size=2",
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["batches"]) == 2


# ============================================================================
# Batch Stats Tests
# ============================================================================

class TestBatchStats:
    """Tests for batch statistics endpoint."""

    def test_get_batch_stats(self, client, auth_headers, sample_batch_data):
        """Getting batch stats should work."""
        # Create batch
        client.post(
            "/simulations/batch",
            json=sample_batch_data,
            headers=auth_headers,
        )

        # Get stats
        response = client.get(
            "/simulations/batch/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()
        assert data["total_batches"] >= 1
        assert data["total_jobs"] >= 2
        assert "avg_jobs_per_batch" in data


# ============================================================================
# Usage Endpoint Tests
# ============================================================================

class TestUsageEndpoint:
    """Tests for usage status endpoint."""

    def test_get_usage_status(self, client, auth_headers):
        """Getting usage status should work."""
        response = client.get(
            "/simulations/batch/usage",
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()
        assert "tier" in data
        assert "period" in data
        assert "api_calls_used" in data
        assert "api_calls_limit" in data
        assert "simulations_remaining" in data

    def test_get_usage_history(self, client, auth_headers):
        """Getting usage history should work."""
        response = client.get(
            "/simulations/batch/usage/history",
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()
        assert "current" in data
        assert "history" in data


# ============================================================================
# Quota Enforcement Tests
# ============================================================================

class TestQuotaEnforcement:
    """Tests for quota enforcement in batch creation."""

    def test_batch_rejected_when_quota_exceeded(self, client, auth_headers, tmp_db_path):
        """Batch should be rejected when simulation quota exceeded."""
        from api.usage_storage import UsageDatabase

        # Exhaust simulation quota (free tier = 10)
        db = UsageDatabase(os.environ["USAGE_DB_PATH"])
        db.increment_simulations("test-user-alice", started=10)

        # Try to create batch - should fail due to simulation quota
        response = client.post(
            "/simulations/batch",
            json={
                "simulations": [
                    {"template_id": "test", "entity_count": 3, "timepoint_count": 3},
                    {"template_id": "test", "entity_count": 3, "timepoint_count": 3},
                ]
            },
            headers=auth_headers,
        )

        # Should get 429 for quota exceeded
        assert response.status_code == 429
        data = response.json()
        # Could be rate limit or simulation quota - both are valid 429 responses
        assert data.get("error") in ("SimulationQuotaExceeded", "RateLimitExceeded") or \
               "quota" in str(data).lower() or "limit" in str(data).lower()


# ============================================================================
# Run configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
