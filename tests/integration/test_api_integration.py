"""
Integration tests for the Tensor API (Phase 6).

Tests complete workflows through the API with realistic tensor data.
Uses the same character tensor generators as Phase 5 integration tests.
"""

import uuid

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.auth import (
    API_KEY_HEADER,
    clear_api_keys,
    create_api_key,
)
from api.deps import (
    override_db_path,
    reset_dependencies,
)

# API imports
from api.main import create_app

# Core imports

# ============================================================================
# Realistic Tensor Data Generators
# ============================================================================


def create_character_tensor(
    archetype: str, profession: str = None, epoch: str = "modern"
) -> tuple[dict, dict]:
    """
    Create realistic character tensor data for API requests.

    Returns tuple of (tensor_create_data, metadata).
    """
    archetype_profiles = {
        "detective": {
            "context": [0.9, 0.6, 0.8, 0.7, 0.6, 0.9, 0.7, 0.5],
            "biology": [0.45, 0.8, 0.9, 0.7],
            "behavior": [0.7, 0.6, 0.5, 0.8, 0.7, 0.4, 0.3, 0.6],
        },
        "hero": {
            "context": [0.7, 0.8, 0.9, 0.9, 0.8, 0.6, 0.8, 0.9],
            "biology": [0.3, 0.95, 0.95, 0.95],
            "behavior": [0.9, 0.8, 0.9, 0.5, 0.6, 0.9, 0.8, 0.8],
        },
        "scientist": {
            "context": [0.95, 0.5, 0.6, 0.3, 0.9, 0.95, 0.4, 0.4],
            "biology": [0.5, 0.7, 0.8, 0.5],
            "behavior": [0.4, 0.7, 0.3, 0.95, 0.8, 0.3, 0.6, 0.5],
        },
        "merchant": {
            "context": [0.6, 0.7, 0.7, 0.4, 0.8, 0.7, 0.6, 0.85],
            "biology": [0.45, 0.8, 0.9, 0.7],
            "behavior": [0.6, 0.9, 0.6, 0.7, 0.8, 0.6, 0.5, 0.4],
        },
        "noble": {
            "context": [0.7, 0.4, 0.6, 0.2, 0.6, 0.7, 0.3, 0.9],
            "biology": [0.5, 0.75, 0.95, 0.6],
            "behavior": [0.8, 0.5, 0.4, 0.6, 0.95, 0.7, 0.4, 0.3],
        },
    }

    profile = archetype_profiles.get(archetype, archetype_profiles["hero"])

    # Add small noise and clamp
    context = np.clip(
        np.array(profile["context"]) + np.random.normal(0, 0.02, 8), 0.01, 0.99
    ).tolist()
    biology = np.clip(
        np.array(profile["biology"]) + np.random.normal(0, 0.01, 4), 0.01, 0.99
    ).tolist()
    behavior = np.clip(
        np.array(profile["behavior"]) + np.random.normal(0, 0.02, 8), 0.01, 0.99
    ).tolist()

    description = f"{epoch.capitalize()} {archetype}" + (f" ({profession})" if profession else "")

    tensor_data = {
        "tensor_id": f"{archetype}-{uuid.uuid4().hex[:8]}",
        "entity_id": f"entity-{archetype}",
        "world_id": f"{epoch}-world",
        "values": {
            "context": context,
            "biology": biology,
            "behavior": behavior,
        },
        "description": description,
        "category": f"epoch/{epoch}/{archetype}",
        "maturity": 0.9 + np.random.random() * 0.08,
        "training_cycles": 50 + np.random.randint(0, 50),
    }

    metadata = {
        "archetype": archetype,
        "profession": profession or archetype,
        "epoch": epoch,
    }

    return tensor_data, metadata


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
def client(tmp_path) -> TestClient:
    """Create test client with temporary database."""
    db_path = str(tmp_path / "integration_test.db")
    override_db_path(db_path)
    app = create_app(debug=True)
    return TestClient(app)


@pytest.fixture
def researcher_alice(client) -> tuple[str, dict]:
    """Create researcher Alice with API key."""
    key = create_api_key("researcher-alice", "Alice's Research Key")
    return "researcher-alice", {API_KEY_HEADER: key}


@pytest.fixture
def researcher_bob(client) -> tuple[str, dict]:
    """Create researcher Bob with API key."""
    key = create_api_key("researcher-bob", "Bob's Research Key")
    return "researcher-bob", {API_KEY_HEADER: key}


@pytest.fixture
def community_user(client) -> tuple[str, dict]:
    """Create community user with API key."""
    key = create_api_key("community-user", "Community Key")
    return "community-user", {API_KEY_HEADER: key}


# ============================================================================
# Complete Workflow Tests
# ============================================================================


@pytest.mark.integration
class TestResearchWorkflow:
    """Test realistic research workflow through API."""

    def test_create_and_train_tensor(self, client, researcher_alice):
        """Researcher creates tensor and simulates training."""
        user_id, headers = researcher_alice

        # Create detective tensor
        tensor_data, metadata = create_character_tensor("detective", "investigator", "victorian")
        tensor_data["maturity"] = 0.3  # Start untrained

        response = client.post("/tensors", json=tensor_data, headers=headers)
        assert response.status_code == 201
        tensor_id = response.json()["tensor_id"]

        # Simulate training iterations
        for i in range(5):
            new_maturity = 0.3 + (i + 1) * 0.13  # Progress toward 0.95
            update_response = client.put(
                f"/tensors/{tensor_id}",
                json={
                    "maturity": min(0.95, new_maturity),
                    "training_cycles": (i + 1) * 20,
                },
                headers=headers,
            )
            assert update_response.status_code == 200

        # Verify final state
        final_response = client.get(f"/tensors/{tensor_id}", headers=headers)
        assert final_response.status_code == 200
        final_data = final_response.json()
        assert final_data["maturity"] >= 0.95
        assert final_data["training_cycles"] >= 100

    def test_collaborate_and_share(self, client, researcher_alice, researcher_bob):
        """Researchers collaborate through sharing."""
        alice_id, alice_headers = researcher_alice
        bob_id, bob_headers = researcher_bob

        # Alice creates trained tensor
        tensor_data, _ = create_character_tensor("scientist", "physicist", "modern")
        tensor_data["maturity"] = 0.96

        create_resp = client.post("/tensors", json=tensor_data, headers=alice_headers)
        tensor_id = create_resp.json()["tensor_id"]

        # Bob can't access yet
        bob_get = client.get(f"/tensors/{tensor_id}", headers=bob_headers)
        assert bob_get.status_code == 403

        # Alice shares with Bob
        share_resp = client.post(
            f"/tensors/{tensor_id}/share",
            json={"user_id": bob_id},
            headers=alice_headers,
        )
        assert share_resp.status_code == 200

        # Bob can now read
        bob_get = client.get(f"/tensors/{tensor_id}", headers=bob_headers)
        assert bob_get.status_code == 200

        # Bob forks for his own work
        fork_resp = client.post(
            f"/tensors/{tensor_id}/fork",
            headers=bob_headers,
        )
        assert fork_resp.status_code == 201
        fork_id = fork_resp.json()["tensor_id"]

        # Bob owns and can modify his fork
        bob_update = client.put(
            f"/tensors/{fork_id}",
            json={"description": "Bob's variant of physicist"},
            headers=bob_headers,
        )
        assert bob_update.status_code == 200

        # Alice can't modify Bob's fork
        alice_update = client.put(
            f"/tensors/{fork_id}",
            json={"description": "Alice trying to modify"},
            headers=alice_headers,
        )
        assert alice_update.status_code == 403

    def test_publish_template_for_community(self, client, researcher_alice, community_user):
        """Researcher publishes tensor as public template."""
        alice_id, alice_headers = researcher_alice
        comm_id, comm_headers = community_user

        # Alice creates high-quality tensor
        tensor_data, _ = create_character_tensor("noble", "aristocrat", "victorian")
        tensor_data["maturity"] = 0.98
        tensor_data["description"] = "Public template: Victorian aristocrat"

        create_resp = client.post("/tensors", json=tensor_data, headers=alice_headers)
        tensor_id = create_resp.json()["tensor_id"]

        # Community can't access private tensor
        comm_get = client.get(f"/tensors/{tensor_id}", headers=comm_headers)
        assert comm_get.status_code == 403

        # Alice publishes (makes public)
        publish_resp = client.put(
            f"/tensors/{tensor_id}/access",
            json={"access_level": "public"},
            headers=alice_headers,
        )
        assert publish_resp.status_code == 200

        # Community can now read
        comm_get = client.get(f"/tensors/{tensor_id}", headers=comm_headers)
        assert comm_get.status_code == 200

        # Community can fork
        comm_fork = client.post(
            f"/tensors/{tensor_id}/fork",
            headers=comm_headers,
        )
        assert comm_fork.status_code == 201

        # Community owns their fork
        fork_id = comm_fork.json()["tensor_id"]
        fork_data = comm_fork.json()
        assert fork_data["owner_id"] == comm_id


@pytest.mark.integration
class TestMultiTenantIsolation:
    """Test organization/tenant isolation."""

    def test_separate_organizations(self, client):
        """Different organizations should be isolated."""
        # Create keys for two organizations
        org_a_key = create_api_key("org-a-user", "Org A Key")
        org_b_key = create_api_key("org-b-user", "Org B Key")

        org_a_headers = {API_KEY_HEADER: org_a_key}
        org_b_headers = {API_KEY_HEADER: org_b_key}

        # Org A creates tensor
        org_a_data, _ = create_character_tensor("merchant", "trader", "renaissance")
        org_a_resp = client.post("/tensors", json=org_a_data, headers=org_a_headers)
        org_a_tensor_id = org_a_resp.json()["tensor_id"]

        # Org B creates tensor
        org_b_data, _ = create_character_tensor("hero", "knight", "medieval")
        org_b_resp = client.post("/tensors", json=org_b_data, headers=org_b_headers)
        org_b_tensor_id = org_b_resp.json()["tensor_id"]

        # Org A can access their tensor
        assert client.get(f"/tensors/{org_a_tensor_id}", headers=org_a_headers).status_code == 200

        # Org A cannot access Org B's tensor
        assert client.get(f"/tensors/{org_b_tensor_id}", headers=org_a_headers).status_code == 403

        # Org B can access their tensor
        assert client.get(f"/tensors/{org_b_tensor_id}", headers=org_b_headers).status_code == 200

        # Org B cannot access Org A's tensor
        assert client.get(f"/tensors/{org_a_tensor_id}", headers=org_b_headers).status_code == 403


@pytest.mark.integration
class TestAuditCompliance:
    """Test audit trail through API access."""

    def test_access_creates_audit_trail(self, client, researcher_alice, researcher_bob):
        """API access should create audit records."""
        alice_id, alice_headers = researcher_alice
        bob_id, bob_headers = researcher_bob

        # Alice creates tensor
        tensor_data, _ = create_character_tensor("detective")
        create_resp = client.post("/tensors", json=tensor_data, headers=alice_headers)
        tensor_id = create_resp.json()["tensor_id"]

        # Alice reads
        client.get(f"/tensors/{tensor_id}", headers=alice_headers)

        # Bob tries to read (will fail)
        client.get(f"/tensors/{tensor_id}", headers=bob_headers)

        # Alice shares
        client.post(
            f"/tensors/{tensor_id}/share",
            json={"user_id": bob_id},
            headers=alice_headers,
        )

        # Bob reads (now succeeds)
        client.get(f"/tensors/{tensor_id}", headers=bob_headers)

        # Verify stats include access data
        stats_resp = client.get("/tensors/stats/summary", headers=alice_headers)
        assert stats_resp.status_code == 200


@pytest.mark.integration
class TestBulkOperations:
    """Test bulk operations through API."""

    def test_create_multiple_tensors(self, client, researcher_alice):
        """Create multiple tensors for testing."""
        user_id, headers = researcher_alice

        archetypes = ["detective", "scientist", "merchant", "noble", "hero"]
        created_ids = []

        for archetype in archetypes:
            tensor_data, _ = create_character_tensor(archetype)
            response = client.post("/tensors", json=tensor_data, headers=headers)
            assert response.status_code == 201
            created_ids.append(response.json()["tensor_id"])

        # List should return all
        list_resp = client.get("/tensors", headers=headers)
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 5

    def test_pagination(self, client, researcher_alice):
        """Test pagination of tensor list."""
        user_id, headers = researcher_alice

        # Create 25 tensors
        for i in range(25):
            tensor_data, _ = create_character_tensor("hero")
            tensor_data["tensor_id"] = f"page-test-{i}"
            client.post("/tensors", json=tensor_data, headers=headers)

        # Get first page
        page1_resp = client.get("/tensors?page=1&page_size=10", headers=headers)
        assert page1_resp.status_code == 200
        page1_data = page1_resp.json()
        assert len(page1_data["tensors"]) == 10
        assert page1_data["total"] >= 25

        # Get second page
        page2_resp = client.get("/tensors?page=2&page_size=10", headers=headers)
        assert page2_resp.status_code == 200
        page2_data = page2_resp.json()
        assert len(page2_data["tensors"]) == 10

        # Verify different tensors
        page1_ids = {t["tensor_id"] for t in page1_data["tensors"]}
        page2_ids = {t["tensor_id"] for t in page2_data["tensors"]}
        assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.integration
class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_invalid_tensor_values_rejected(self, client, researcher_alice):
        """Invalid tensor values should be rejected cleanly."""
        user_id, headers = researcher_alice

        # Try to create with out-of-range values
        bad_data = {
            "entity_id": "entity-bad",
            "values": {
                "context": [1.5] * 8,  # Out of range
                "biology": [0.5] * 4,
                "behavior": [0.5] * 8,
            },
        }

        response = client.post("/tensors", json=bad_data, headers=headers)
        assert response.status_code == 422

    def test_nonexistent_tensor_handling(self, client, researcher_alice):
        """Operations on nonexistent tensors should fail gracefully."""
        user_id, headers = researcher_alice

        # Get nonexistent
        response = client.get("/tensors/nonexistent-id", headers=headers)
        assert response.status_code == 404

        # Update nonexistent
        response = client.put(
            "/tensors/nonexistent-id",
            json={"maturity": 0.5},
            headers=headers,
        )
        assert response.status_code == 404

        # Delete nonexistent
        response = client.delete("/tensors/nonexistent-id", headers=headers)
        assert response.status_code == 404

    def test_concurrent_update_handling(self, client, researcher_alice):
        """Concurrent updates should be handled safely."""
        user_id, headers = researcher_alice

        # Create tensor
        tensor_data, _ = create_character_tensor("scientist")
        create_resp = client.post("/tensors", json=tensor_data, headers=headers)
        tensor_id = create_resp.json()["tensor_id"]

        # Multiple rapid updates
        for i in range(10):
            update_resp = client.put(
                f"/tensors/{tensor_id}",
                json={"training_cycles": i * 10},
                headers=headers,
            )
            assert update_resp.status_code == 200

        # Verify final state
        final_resp = client.get(f"/tensors/{tensor_id}", headers=headers)
        assert final_resp.status_code == 200
        # Version should have incremented
        assert final_resp.json()["version"] > 1


# ============================================================================
# Run configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
