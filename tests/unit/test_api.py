"""
Unit tests for the Tensor API (Phase 6).

Tests API endpoints, authentication, and models independently.
"""

import os

import pytest
from fastapi.testclient import TestClient

# Allow test helper functions to run in test context
os.environ.setdefault("TESTING", "true")

from api.auth import (
    API_KEY_HEADER,
    clear_api_keys,
    create_api_key,
    generate_api_key,
    hash_api_key,
    revoke_api_key,
    setup_test_api_keys,
    verify_api_key,
)
from api.deps import (
    create_test_dependencies,
    override_db_path,
    reset_dependencies,
)

# API imports
from api.main import create_app
from api.models import (
    ComposeRequest,
    SearchRequest,
    TensorCreate,
    TensorUpdate,
    TensorValues,
)

# Core imports

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_state():
    """Reset API state before each test."""
    clear_api_keys()
    reset_dependencies()
    yield
    clear_api_keys()
    reset_dependencies()


@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    """Create temporary database path."""
    return str(tmp_path / "test_api.db")


@pytest.fixture
def test_deps(tmp_db_path):
    """Create test dependencies."""
    override_db_path(tmp_db_path)
    return create_test_dependencies(tmp_db_path)


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
def sample_tensor_data() -> dict:
    """Sample tensor creation data."""
    return {
        "entity_id": "entity-test-001",
        "world_id": "world-test",
        "values": {
            "context": [0.5, 0.6, 0.7, 0.8, 0.5, 0.6, 0.7, 0.4],
            "biology": [0.5, 0.6, 0.7, 0.5],
            "behavior": [0.5, 0.6, 0.7, 0.8, 0.5, 0.6, 0.7, 0.4],
        },
        "description": "Test tensor for unit testing",
        "category": "test/unit",
        "maturity": 0.85,
        "training_cycles": 50,
    }


# ============================================================================
# Auth Tests
# ============================================================================


class TestAPIKeyAuth:
    """Tests for API key authentication."""

    def test_generate_api_key_format(self):
        """Generated keys should have correct format."""
        key = generate_api_key()
        assert key.startswith("tp_")
        assert len(key) == 35  # "tp_" + 32 hex chars

    def test_create_and_verify_api_key(self):
        """Creating and verifying API key should work."""
        user_id = "test-user"
        key = create_api_key(user_id, "Test Key")

        result = verify_api_key(key)
        assert result == user_id

    def test_verify_invalid_key_returns_none(self):
        """Invalid key should return None."""
        result = verify_api_key("invalid-key")
        assert result is None

    def test_hash_api_key_consistent(self):
        """Hash should be consistent for same key."""
        key = "test-key-123"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2

    def test_revoke_api_key(self):
        """Revoking key should invalidate it."""
        user_id = "test-user"
        key = create_api_key(user_id, "Test Key")

        # Key works before revoke
        assert verify_api_key(key) == user_id

        # Revoke
        result = revoke_api_key(key)
        assert result is True

        # Key no longer works
        assert verify_api_key(key) is None

    def test_setup_test_api_keys(self):
        """Setup test keys should create multiple keys."""
        keys = setup_test_api_keys()

        assert "test-user-alice" in keys
        assert "test-user-bob" in keys
        assert "test-user-admin" in keys

        # All keys should be valid
        for user_id, key in keys.items():
            assert verify_api_key(key) == user_id

    def test_clear_api_keys(self):
        """Clear should remove all keys."""
        create_api_key("user1", "Key 1")
        create_api_key("user2", "Key 2")

        clear_api_keys()

        assert verify_api_key("any-key") is None


# ============================================================================
# Model Validation Tests
# ============================================================================


class TestModelValidation:
    """Tests for Pydantic model validation."""

    def test_tensor_values_valid(self):
        """Valid tensor values should pass."""
        values = TensorValues(
            context=[0.5] * 8,
            biology=[0.5] * 4,
            behavior=[0.5] * 8,
        )
        assert len(values.context) == 8
        assert len(values.biology) == 4
        assert len(values.behavior) == 8

    def test_tensor_values_wrong_length_fails(self):
        """Wrong array lengths should fail."""
        with pytest.raises(ValueError):
            TensorValues(
                context=[0.5] * 7,  # Wrong length
                biology=[0.5] * 4,
                behavior=[0.5] * 8,
            )

    def test_tensor_values_out_of_range_fails(self):
        """Values outside [0, 1] should fail."""
        with pytest.raises(ValueError):
            TensorValues(
                context=[1.5] * 8,  # Out of range
                biology=[0.5] * 4,
                behavior=[0.5] * 8,
            )

    def test_tensor_create_valid(self, sample_tensor_data):
        """Valid tensor create data should pass."""
        data = TensorCreate(**sample_tensor_data)
        assert data.entity_id == sample_tensor_data["entity_id"]
        assert data.maturity == sample_tensor_data["maturity"]

    def test_tensor_create_invalid_access_level_fails(self, sample_tensor_data):
        """Invalid access level should fail."""
        sample_tensor_data["access_level"] = "invalid"
        with pytest.raises(ValueError):
            TensorCreate(**sample_tensor_data)

    def test_tensor_update_partial(self):
        """Update should accept partial data."""
        update = TensorUpdate(maturity=0.95)
        assert update.maturity == 0.95
        assert update.entity_id is None

    def test_search_request_valid(self):
        """Valid search request should pass."""
        request = SearchRequest(
            query="detective investigating",
            n_results=5,
            min_maturity=0.9,
        )
        assert request.query == "detective investigating"
        assert request.n_results == 5

    def test_search_request_empty_query_fails(self):
        """Empty query should fail."""
        with pytest.raises(ValueError):
            SearchRequest(query="")

    def test_compose_request_valid(self):
        """Valid compose request should pass."""
        request = ComposeRequest(
            tensor_ids=["tensor-1", "tensor-2"],
            method="weighted_blend",
        )
        assert len(request.tensor_ids) == 2

    def test_compose_request_single_tensor_fails(self):
        """Single tensor composition should fail."""
        with pytest.raises(ValueError):
            ComposeRequest(
                tensor_ids=["tensor-1"],  # Need at least 2
            )

    def test_compose_request_invalid_method_fails(self):
        """Invalid composition method should fail."""
        with pytest.raises(ValueError):
            ComposeRequest(
                tensor_ids=["tensor-1", "tensor-2"],
                method="invalid_method",
            )


# ============================================================================
# Health Endpoint Tests
# ============================================================================


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_returns_ok(self, client, auth_headers):
        """Health check should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "timestamp" in data

    def test_root_returns_info(self, client):
        """Root endpoint should return API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "docs" in data


# ============================================================================
# Tensor CRUD Tests
# ============================================================================


class TestTensorCRUD:
    """Tests for tensor CRUD operations."""

    def test_create_tensor_success(self, client, auth_headers, sample_tensor_data):
        """Creating tensor should succeed."""
        response = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=auth_headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert data["entity_id"] == sample_tensor_data["entity_id"]
        assert data["maturity"] == sample_tensor_data["maturity"]
        assert "tensor_id" in data
        assert data["access_level"] == "private"

    def test_create_tensor_without_auth_fails(self, client, sample_tensor_data):
        """Creating tensor without auth should fail."""
        response = client.post("/tensors", json=sample_tensor_data)
        # FastAPI returns 403 when API key validation fails
        assert response.status_code in (401, 403)

    def test_create_tensor_with_custom_id(self, client, auth_headers, sample_tensor_data):
        """Creating tensor with custom ID should work."""
        sample_tensor_data["tensor_id"] = "custom-tensor-id"
        response = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["tensor_id"] == "custom-tensor-id"

    def test_create_duplicate_tensor_fails(self, client, auth_headers, sample_tensor_data):
        """Creating tensor with existing ID should fail."""
        sample_tensor_data["tensor_id"] = "duplicate-id"

        # First creation
        response1 = client.post("/tensors", json=sample_tensor_data, headers=auth_headers)
        assert response1.status_code == 201

        # Duplicate
        response2 = client.post("/tensors", json=sample_tensor_data, headers=auth_headers)
        assert response2.status_code == 409

    def test_get_tensor_success(self, client, auth_headers, sample_tensor_data):
        """Getting owned tensor should succeed."""
        # Create
        create_resp = client.post("/tensors", json=sample_tensor_data, headers=auth_headers)
        tensor_id = create_resp.json()["tensor_id"]

        # Get
        response = client.get(f"/tensors/{tensor_id}", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["tensor_id"] == tensor_id
        assert data["entity_id"] == sample_tensor_data["entity_id"]

    def test_get_nonexistent_tensor_fails(self, client, auth_headers):
        """Getting nonexistent tensor should fail."""
        response = client.get("/tensors/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_update_tensor_success(self, client, auth_headers, sample_tensor_data):
        """Updating owned tensor should succeed."""
        # Create
        create_resp = client.post("/tensors", json=sample_tensor_data, headers=auth_headers)
        tensor_id = create_resp.json()["tensor_id"]

        # Update
        update_data = {
            "maturity": 0.95,
            "description": "Updated description",
        }
        response = client.put(
            f"/tensors/{tensor_id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["maturity"] == 0.95
        assert data["description"] == "Updated description"

    def test_delete_tensor_success(self, client, auth_headers, sample_tensor_data):
        """Deleting owned tensor should succeed."""
        # Create
        create_resp = client.post("/tensors", json=sample_tensor_data, headers=auth_headers)
        tensor_id = create_resp.json()["tensor_id"]

        # Delete
        response = client.delete(f"/tensors/{tensor_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        get_resp = client.get(f"/tensors/{tensor_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_list_tensors_returns_owned(self, client, auth_headers, sample_tensor_data):
        """List should return owned tensors."""
        # Create multiple tensors
        for i in range(3):
            data = sample_tensor_data.copy()
            data["tensor_id"] = f"list-test-{i}"
            client.post("/tensors", json=data, headers=auth_headers)

        # List
        response = client.get("/tensors", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 3
        assert len(data["tensors"]) >= 3


# ============================================================================
# Permission Tests
# ============================================================================


class TestPermissions:
    """Tests for permission enforcement."""

    def test_cannot_read_others_private_tensor(self, client, sample_tensor_data, test_user_id):
        """Cannot read another user's private tensor."""
        # Create tensor as alice
        alice_key = create_api_key("alice", "Alice Key")
        alice_headers = {API_KEY_HEADER: alice_key}

        create_resp = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=alice_headers,
        )
        tensor_id = create_resp.json()["tensor_id"]

        # Try to read as bob
        bob_key = create_api_key("bob", "Bob Key")
        bob_headers = {API_KEY_HEADER: bob_key}

        response = client.get(f"/tensors/{tensor_id}", headers=bob_headers)
        assert response.status_code == 403

    def test_can_read_public_tensor(self, client, sample_tensor_data):
        """Can read public tensor."""
        # Create public tensor as alice
        alice_key = create_api_key("alice", "Alice Key")
        alice_headers = {API_KEY_HEADER: alice_key}

        sample_tensor_data["access_level"] = "public"
        create_resp = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=alice_headers,
        )
        tensor_id = create_resp.json()["tensor_id"]

        # Read as bob
        bob_key = create_api_key("bob", "Bob Key")
        bob_headers = {API_KEY_HEADER: bob_key}

        response = client.get(f"/tensors/{tensor_id}", headers=bob_headers)
        assert response.status_code == 200

    def test_share_tensor_grants_access(self, client, sample_tensor_data):
        """Sharing tensor grants read access."""
        # Create as alice
        alice_key = create_api_key("alice", "Alice Key")
        alice_headers = {API_KEY_HEADER: alice_key}

        create_resp = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=alice_headers,
        )
        tensor_id = create_resp.json()["tensor_id"]

        # Bob can't read yet
        bob_key = create_api_key("bob", "Bob Key")
        bob_headers = {API_KEY_HEADER: bob_key}

        response = client.get(f"/tensors/{tensor_id}", headers=bob_headers)
        assert response.status_code == 403

        # Alice shares with bob
        share_resp = client.post(
            f"/tensors/{tensor_id}/share",
            json={"user_id": "bob"},
            headers=alice_headers,
        )
        assert share_resp.status_code == 200

        # Now bob can read
        response = client.get(f"/tensors/{tensor_id}", headers=bob_headers)
        assert response.status_code == 200

    def test_cannot_write_shared_tensor(self, client, sample_tensor_data):
        """Cannot write to shared tensor (read-only access)."""
        # Create as alice
        alice_key = create_api_key("alice", "Alice Key")
        alice_headers = {API_KEY_HEADER: alice_key}

        create_resp = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=alice_headers,
        )
        tensor_id = create_resp.json()["tensor_id"]

        # Share with bob
        bob_key = create_api_key("bob", "Bob Key")
        client.post(
            f"/tensors/{tensor_id}/share",
            json={"user_id": "bob"},
            headers=alice_headers,
        )

        # Bob tries to update
        bob_headers = {API_KEY_HEADER: bob_key}
        response = client.put(
            f"/tensors/{tensor_id}",
            json={"maturity": 0.99},
            headers=bob_headers,
        )
        assert response.status_code == 403


# ============================================================================
# Fork Tests
# ============================================================================


class TestForkEndpoint:
    """Tests for tensor forking."""

    def test_fork_creates_copy(self, client, auth_headers, sample_tensor_data):
        """Forking creates owned copy."""
        # Create original
        create_resp = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=auth_headers,
        )
        original_id = create_resp.json()["tensor_id"]

        # Fork
        fork_resp = client.post(
            f"/tensors/{original_id}/fork",
            headers=auth_headers,
        )
        assert fork_resp.status_code == 201

        fork_data = fork_resp.json()
        assert fork_data["tensor_id"] != original_id
        assert "Fork of" in fork_data["description"]

    def test_fork_with_custom_id(self, client, auth_headers, sample_tensor_data):
        """Forking with custom ID works."""
        # Create original
        create_resp = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=auth_headers,
        )
        original_id = create_resp.json()["tensor_id"]

        # Fork with custom ID
        fork_resp = client.post(
            f"/tensors/{original_id}/fork?new_id=my-custom-fork",
            headers=auth_headers,
        )
        assert fork_resp.status_code == 201
        assert fork_resp.json()["tensor_id"] == "my-custom-fork"

    def test_fork_public_tensor(self, client, sample_tensor_data):
        """Can fork public tensor."""
        # Create public tensor as alice
        alice_key = create_api_key("alice", "Alice Key")
        alice_headers = {API_KEY_HEADER: alice_key}

        sample_tensor_data["access_level"] = "public"
        create_resp = client.post(
            "/tensors",
            json=sample_tensor_data,
            headers=alice_headers,
        )
        original_id = create_resp.json()["tensor_id"]

        # Fork as bob
        bob_key = create_api_key("bob", "Bob Key")
        bob_headers = {API_KEY_HEADER: bob_key}

        fork_resp = client.post(
            f"/tensors/{original_id}/fork",
            headers=bob_headers,
        )
        assert fork_resp.status_code == 201

        # Bob owns the fork
        fork_id = fork_resp.json()["tensor_id"]
        fork_data = fork_resp.json()
        assert fork_data["owner_id"] == "bob"


# ============================================================================
# Stats Tests
# ============================================================================


class TestStatsEndpoint:
    """Tests for statistics endpoint."""

    def test_stats_returns_counts(self, client, auth_headers, sample_tensor_data):
        """Stats should return tensor counts."""
        # Create some tensors
        for i in range(5):
            data = sample_tensor_data.copy()
            data["tensor_id"] = f"stats-test-{i}"
            data["maturity"] = 0.9 if i < 3 else 0.98
            client.post("/tensors", json=data, headers=auth_headers)

        # Get stats
        response = client.get("/tensors/stats/summary", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["total_tensors"] >= 5
        assert "operational_count" in data
        assert "training_count" in data
        assert "avg_maturity" in data


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_json_returns_422(self, client, auth_headers):
        """Invalid JSON should return 422."""
        response = client.post(
            "/tensors",
            content="not json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_field_returns_422(self, client, auth_headers):
        """Missing required field should return 422."""
        response = client.post(
            "/tensors",
            json={"description": "Missing entity_id"},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ============================================================================
# Run configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
