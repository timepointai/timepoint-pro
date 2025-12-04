"""
Integration tests for Access Control (Phase 5) with realistic tensor data.

These tests validate the permission system in real-world scenarios:
- Multi-user access to character tensors
- Sharing workflows between researchers
- Audit trails for compliance
- Permission filtering in TensorRAG search

Uses the same realistic tensor fixtures as test_tensor_integration.py.

Phase 5: Access Control
"""

import asyncio
import numpy as np
import pytest
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Tuple

# Phase 1 imports
from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import serialize_tensor, deserialize_tensor

# Phase 3 imports
from retrieval.tensor_rag import TensorRAG, SearchResult

# Phase 5 imports
from access.permissions import (
    TensorPermission,
    PermissionEnforcer,
    PermissionDenied,
)
from access.audit import (
    AccessAuditLog,
    AuditLogger,
)

# Core imports
from schemas import TTMTensor


# ============================================================================
# Realistic Tensor Data Generators (from test_tensor_integration.py)
# ============================================================================

def create_character_tensor(
    archetype: str,
    profession: str = None,
    epoch: str = "modern"
) -> Tuple[TTMTensor, Dict]:
    """
    Create a realistic character tensor simulating pipeline output.
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
        }
    }

    profile = archetype_profiles.get(archetype, archetype_profiles["hero"])

    context = np.array(profile["context"], dtype=np.float32)
    biology = np.array(profile["biology"], dtype=np.float32)
    behavior = np.array(profile["behavior"], dtype=np.float32)

    # Add small noise
    context += np.random.normal(0, 0.02, 8).astype(np.float32)
    biology += np.random.normal(0, 0.01, 4).astype(np.float32)
    behavior += np.random.normal(0, 0.02, 8).astype(np.float32)

    # Clamp
    context = np.clip(context, 0.01, 0.99)
    biology = np.clip(biology, 0.01, 0.99)
    behavior = np.clip(behavior, 0.01, 0.99)

    tensor = TTMTensor.from_arrays(context, biology, behavior)

    metadata = {
        "archetype": archetype,
        "profession": profession or archetype,
        "epoch": epoch,
        "description": f"{epoch.capitalize()} {archetype}" + (f" ({profession})" if profession else ""),
    }

    return tensor, metadata


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    """Create temporary database path."""
    return str(tmp_path / "integration_test.db")


@pytest.fixture
def tensor_db(tmp_db_path) -> TensorDatabase:
    """Create TensorDatabase."""
    return TensorDatabase(tmp_db_path)


@pytest.fixture
def enforcer(tmp_db_path) -> PermissionEnforcer:
    """Create PermissionEnforcer."""
    return PermissionEnforcer(tmp_db_path)


@pytest.fixture
def logger(tmp_db_path) -> AuditLogger:
    """Create AuditLogger."""
    return AuditLogger(tmp_db_path)


@pytest.fixture
def detective_tensor() -> Tuple[str, TTMTensor, Dict]:
    """Create a detective tensor with ID."""
    tensor, metadata = create_character_tensor("detective", "investigator", "victorian")
    tensor_id = f"detective-{uuid.uuid4().hex[:8]}"
    return tensor_id, tensor, metadata


@pytest.fixture
def researcher_tensors() -> List[Tuple[str, TTMTensor, Dict]]:
    """Create multiple research tensors."""
    tensors = []
    archetypes = ["detective", "scientist", "noble"]
    for archetype in archetypes:
        tensor, metadata = create_character_tensor(archetype)
        tensor_id = f"{archetype}-{uuid.uuid4().hex[:8]}"
        tensors.append((tensor_id, tensor, metadata))
    return tensors


# ============================================================================
# Multi-User Access Scenarios
# ============================================================================

@pytest.mark.integration
class TestMultiUserAccessScenarios:
    """Test realistic multi-user access scenarios."""

    def test_researcher_creates_private_tensor(
        self, tensor_db, enforcer, logger, detective_tensor
    ):
        """Researcher creates private tensor, colleague cannot access."""
        tensor_id, tensor, metadata = detective_tensor
        researcher_id = "researcher-alice"
        colleague_id = "researcher-bob"

        # Researcher creates and saves tensor
        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id="entity-sherlock",
            world_id="victorian-world",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.9,
            training_cycles=50,
            description=metadata["description"],
        )
        tensor_db.save_tensor(record)

        # Create permission (private by default)
        enforcer.create_default_permission(tensor_id, researcher_id)

        # Log creation
        logger.log_access(tensor_id, researcher_id, "write", True)

        # Researcher can access
        assert enforcer.can_read(researcher_id, tensor_id) is True
        logger.log_access(tensor_id, researcher_id, "read", True)

        # Colleague cannot access
        assert enforcer.can_read(colleague_id, tensor_id) is False
        logger.log_access(tensor_id, colleague_id, "read", False)

        # Verify audit trail
        history = logger.get_access_history(tensor_id)
        assert len(history) == 3

        failed = logger.get_failed_attempts(tensor_id=tensor_id)
        assert len(failed) == 1
        assert failed[0].user_id == colleague_id

    def test_sharing_enables_collaboration(
        self, tensor_db, enforcer, logger, detective_tensor
    ):
        """Owner shares tensor, collaborator gains read access."""
        tensor_id, tensor, metadata = detective_tensor
        owner_id = "researcher-alice"
        collaborator_id = "researcher-bob"

        # Setup tensor
        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id="entity-holmes",
            world_id="mystery-world",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.95,
            training_cycles=100,
            description=metadata["description"],
        )
        tensor_db.save_tensor(record)
        enforcer.create_default_permission(tensor_id, owner_id)

        # Before sharing - collaborator denied
        assert enforcer.can_read(collaborator_id, tensor_id) is False

        # Owner shares with collaborator
        result = enforcer.grant_access(owner_id, tensor_id, collaborator_id)
        assert result is True

        # After sharing - collaborator can read
        assert enforcer.can_read(collaborator_id, tensor_id) is True
        logger.log_access(tensor_id, collaborator_id, "read", True)

        # But collaborator cannot write
        assert enforcer.can_write(collaborator_id, tensor_id) is False

        # Collaborator can fork (create their own copy)
        assert enforcer.can_fork(collaborator_id, tensor_id) is True

    def test_publish_tensor_for_community(
        self, tensor_db, enforcer, logger, detective_tensor
    ):
        """Make tensor public, anyone can fork."""
        tensor_id, tensor, metadata = detective_tensor
        owner_id = "researcher-alice"
        community_user_1 = "community-user-1"
        community_user_2 = "community-user-2"

        # Setup tensor
        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id="entity-template",
            world_id="template-world",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.98,
            training_cycles=200,
            description=f"Public template: {metadata['description']}",
            category=f"epoch/{metadata['epoch']}/{metadata['archetype']}",
        )
        tensor_db.save_tensor(record)
        enforcer.create_default_permission(tensor_id, owner_id)

        # Before publishing - community cannot access
        assert enforcer.can_read(community_user_1, tensor_id) is False

        # Owner publishes
        enforcer.set_access_level(owner_id, tensor_id, "public")

        # After publishing - anyone can read and fork
        assert enforcer.can_read(community_user_1, tensor_id) is True
        assert enforcer.can_read(community_user_2, tensor_id) is True
        assert enforcer.can_fork(community_user_1, tensor_id) is True

        # Log community access
        logger.log_access(tensor_id, community_user_1, "read", True)
        logger.log_access(tensor_id, community_user_2, "fork", True)

        # But they still cannot modify
        assert enforcer.can_write(community_user_1, tensor_id) is False

    def test_fork_creates_owned_copy(
        self, tensor_db, enforcer, logger, detective_tensor
    ):
        """Fork creates independent copy owned by forker."""
        original_id, original_tensor, metadata = detective_tensor
        original_owner = "researcher-alice"
        forker = "researcher-bob"

        # Setup original (public) tensor
        original_record = TensorRecord(
            tensor_id=original_id,
            entity_id="entity-original",
            world_id="original-world",
            tensor_blob=serialize_tensor(original_tensor),
            maturity=0.95,
            training_cycles=100,
            description=metadata["description"],
        )
        tensor_db.save_tensor(original_record)
        enforcer.create_default_permission(original_id, original_owner)
        enforcer.set_access_level(original_owner, original_id, "public")

        # Forker creates copy
        assert enforcer.can_fork(forker, original_id) is True
        logger.log_access(original_id, forker, "fork", True)

        # Create forked tensor
        fork_id = f"fork-{uuid.uuid4().hex[:8]}"
        fork_record = TensorRecord(
            tensor_id=fork_id,
            entity_id="entity-fork",
            world_id="fork-world",
            tensor_blob=original_record.tensor_blob,  # Copy
            maturity=original_record.maturity,
            training_cycles=original_record.training_cycles,
            description=f"Fork of: {metadata['description']}",
        )
        tensor_db.save_tensor(fork_record)

        # Forker owns the fork
        enforcer.create_default_permission(fork_id, forker)

        # Forker has full access to fork
        assert enforcer.can_read(forker, fork_id) is True
        assert enforcer.can_write(forker, fork_id) is True
        assert enforcer.can_delete(forker, fork_id) is True

        # Original owner has no access to fork (private)
        assert enforcer.can_read(original_owner, fork_id) is False

    def test_revoke_access_removes_ability(
        self, tensor_db, enforcer, logger, detective_tensor
    ):
        """Revoking share removes access."""
        tensor_id, tensor, metadata = detective_tensor
        owner_id = "owner"
        shared_user = "shared-user"

        # Setup
        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id="entity-revoke-test",
            world_id="test-world",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.9,
            training_cycles=50,
        )
        tensor_db.save_tensor(record)
        enforcer.create_default_permission(tensor_id, owner_id)
        enforcer.grant_access(owner_id, tensor_id, shared_user)

        # User has access
        assert enforcer.can_read(shared_user, tensor_id) is True
        logger.log_access(tensor_id, shared_user, "read", True)

        # Owner revokes
        enforcer.revoke_access(owner_id, tensor_id, shared_user)

        # User no longer has access
        assert enforcer.can_read(shared_user, tensor_id) is False

        # Attempt to read should fail
        try:
            enforcer.enforce(shared_user, tensor_id, "read")
            assert False, "Should have raised PermissionDenied"
        except PermissionDenied:
            logger.log_access(tensor_id, shared_user, "read", False)


# ============================================================================
# Audit Trail Integration
# ============================================================================

@pytest.mark.integration
class TestAuditTrailIntegration:
    """Test audit trail in realistic scenarios."""

    def test_access_attempts_logged(
        self, tensor_db, enforcer, logger, researcher_tensors
    ):
        """All access attempts should create audit entries."""
        owner = "researcher-owner"
        reader = "researcher-reader"

        # Create tensors with permissions
        for tensor_id, tensor, metadata in researcher_tensors:
            record = TensorRecord(
                tensor_id=tensor_id,
                entity_id=f"entity-{metadata['archetype']}",
                world_id="research-world",
                tensor_blob=serialize_tensor(tensor),
                maturity=0.9,
                training_cycles=50,
            )
            tensor_db.save_tensor(record)
            enforcer.create_default_permission(tensor_id, owner)
            logger.log_access(tensor_id, owner, "write", True)

        # Share first tensor
        first_tensor_id = researcher_tensors[0][0]
        enforcer.grant_access(owner, first_tensor_id, reader)

        # Reader accesses shared tensor
        if enforcer.can_read(reader, first_tensor_id):
            logger.log_access(first_tensor_id, reader, "read", True)
            enforcer.record_access(first_tensor_id)

        # Reader tries to access unshared tensor
        second_tensor_id = researcher_tensors[1][0]
        if not enforcer.can_read(reader, second_tensor_id):
            logger.log_access(second_tensor_id, reader, "read", False)

        # Verify audit entries
        first_history = logger.get_access_history(first_tensor_id)
        assert len(first_history) == 2  # write + read

        second_history = logger.get_access_history(second_tensor_id)
        assert len(second_history) == 2  # write + failed read

        # Verify failed attempts tracked
        failed = logger.get_failed_attempts()
        assert len(failed) >= 1

    def test_failed_access_logged(self, enforcer, logger):
        """Denied access attempts should be recorded."""
        owner = "owner"
        attacker = "unauthorized-user"
        tensor_id = "sensitive-tensor"

        # Create private tensor
        enforcer.create_default_permission(tensor_id, owner)

        # Multiple failed access attempts
        for action in ["read", "write", "delete", "fork"]:
            can_act = getattr(enforcer, f"can_{action}")(attacker, tensor_id)
            logger.log_access(tensor_id, attacker, action, can_act)

        # All should be failures
        failed = logger.get_failed_attempts(user_id=attacker)
        assert len(failed) == 4
        assert all(not f.success for f in failed)

        # Verify in access summary
        summary = logger.get_access_summary(tensor_id)
        assert summary["failed"] == 4
        assert summary["successful"] == 0

    def test_access_count_updates(self, enforcer, logger, detective_tensor):
        """Permission access_count should update on read."""
        tensor_id, tensor, _ = detective_tensor
        owner = "owner"

        enforcer.create_default_permission(tensor_id, owner)

        # Initial count
        perm = enforcer.get_permission(tensor_id)
        assert perm.access_count == 0

        # Multiple accesses
        for _ in range(5):
            enforcer.record_access(tensor_id)
            logger.log_access(tensor_id, owner, "read", True)

        # Verify count
        perm = enforcer.get_permission(tensor_id)
        assert perm.access_count == 5
        assert perm.accessed_at is not None


# ============================================================================
# Permission with RAG Integration
# ============================================================================

@pytest.mark.integration
class TestPermissionWithRAG:
    """Test permission enforcement in TensorRAG."""

    def test_search_returns_accessible_tensors(
        self, tensor_db, enforcer, researcher_tensors
    ):
        """TensorRAG search returns tensors regardless of permissions."""
        owner = "researcher-owner"
        searcher = "researcher-searcher"

        # Create and save tensors
        for tensor_id, tensor, metadata in researcher_tensors:
            record = TensorRecord(
                tensor_id=tensor_id,
                entity_id=f"entity-{metadata['archetype']}",
                world_id="research-world",
                tensor_blob=serialize_tensor(tensor),
                maturity=0.9,
                training_cycles=50,
                description=metadata["description"],
                category=f"archetype/{metadata['archetype']}",
            )
            tensor_db.save_tensor(record)
            enforcer.create_default_permission(tensor_id, owner)

        # Make one tensor public
        public_tensor_id = researcher_tensors[0][0]
        enforcer.set_access_level(owner, public_tensor_id, "public")

        # Share another tensor
        shared_tensor_id = researcher_tensors[1][0]
        enforcer.grant_access(owner, shared_tensor_id, searcher)

        # Create RAG and search
        rag = TensorRAG(tensor_db, auto_build_index=True)
        results = rag.search("character archetype", n_results=10)

        # RAG returns all tensors (filtering happens at app level)
        assert len(results) >= 3

        # Application-level permission filtering
        accessible_results = []
        for result in results:
            if enforcer.can_read(searcher, result.tensor_id):
                accessible_results.append(result)

        # Searcher can access 2: public + shared
        assert len(accessible_results) == 2

    def test_composition_requires_access(
        self, tensor_db, enforcer, researcher_tensors
    ):
        """Tensor composition should verify access to all components."""
        owner = "researcher-owner"
        composer = "researcher-composer"

        # Create tensors
        for tensor_id, tensor, metadata in researcher_tensors:
            record = TensorRecord(
                tensor_id=tensor_id,
                entity_id=f"entity-{metadata['archetype']}",
                world_id="research-world",
                tensor_blob=serialize_tensor(tensor),
                maturity=0.9,
                training_cycles=50,
                description=metadata["description"],
            )
            tensor_db.save_tensor(record)
            enforcer.create_default_permission(tensor_id, owner)

        # Share only first two tensors
        enforcer.grant_access(owner, researcher_tensors[0][0], composer)
        enforcer.grant_access(owner, researcher_tensors[1][0], composer)

        # Create RAG
        rag = TensorRAG(tensor_db, auto_build_index=True)
        results = rag.search("archetype", n_results=3)

        # Application should filter before composition
        composable_results = [
            r for r in results
            if enforcer.can_read(composer, r.tensor_id)
        ]

        # Composer can only compose accessible tensors
        if len(composable_results) >= 2:
            composed = rag.compose(composable_results[:2])
            ctx, bio, beh = composed.to_arrays()
            assert len(ctx) == 8
            assert len(bio) == 4
            assert len(beh) == 8


# ============================================================================
# Group-Based Access Integration
# ============================================================================

@pytest.mark.integration
class TestGroupBasedAccess:
    """Test group-based access in realistic scenarios."""

    def test_research_team_access(
        self, tensor_db, enforcer, logger, researcher_tensors
    ):
        """Research team members should share access."""
        lead_researcher = "lead-alice"
        team_member_1 = "team-bob"
        team_member_2 = "team-carol"
        external_user = "external-dave"
        team_group = "research-team-alpha"

        # Setup team
        enforcer.add_user_to_group(team_member_1, team_group)
        enforcer.add_user_to_group(team_member_2, team_group)

        # Create tensors with team access
        for tensor_id, tensor, metadata in researcher_tensors:
            record = TensorRecord(
                tensor_id=tensor_id,
                entity_id=f"entity-{metadata['archetype']}",
                world_id="research-world",
                tensor_blob=serialize_tensor(tensor),
                maturity=0.9,
                training_cycles=50,
            )
            tensor_db.save_tensor(record)
            enforcer.create_default_permission(tensor_id, lead_researcher)
            enforcer.grant_group_access(lead_researcher, tensor_id, team_group)

        # Team members have access
        first_tensor = researcher_tensors[0][0]
        assert enforcer.can_read(team_member_1, first_tensor) is True
        assert enforcer.can_read(team_member_2, first_tensor) is True

        # External user does not
        assert enforcer.can_read(external_user, first_tensor) is False

        # Log team access
        logger.log_access(first_tensor, team_member_1, "read", True)
        logger.log_access(first_tensor, team_member_2, "read", True)
        logger.log_access(first_tensor, external_user, "read", False)

        # Verify access patterns
        summary = logger.get_access_summary(first_tensor)
        assert summary["successful"] == 2
        assert summary["failed"] == 1


# ============================================================================
# Complete Workflow Integration
# ============================================================================

@pytest.mark.integration
class TestCompleteWorkflow:
    """Test complete permission workflows."""

    def test_tensor_lifecycle_with_permissions(self, tensor_db, enforcer, logger):
        """Complete tensor lifecycle: create -> train -> share -> publish."""
        creator = "creator"
        collaborator = "collaborator"
        community_user = "community"

        # 1. Creator creates private tensor
        tensor, metadata = create_character_tensor("detective", "investigator", "victorian")
        tensor_id = f"lifecycle-{uuid.uuid4().hex[:8]}"

        record = TensorRecord(
            tensor_id=tensor_id,
            entity_id="entity-lifecycle",
            world_id="lifecycle-world",
            tensor_blob=serialize_tensor(tensor),
            maturity=0.3,
            training_cycles=0,
            description=metadata["description"],
        )
        tensor_db.save_tensor(record)
        enforcer.create_default_permission(tensor_id, creator)
        logger.log_access(tensor_id, creator, "write", True)

        # Verify private
        assert enforcer.can_read(collaborator, tensor_id) is False

        # 2. Creator "trains" tensor (simulated)
        record.maturity = 0.95
        record.training_cycles = 100
        tensor_db.save_tensor(record)

        # 3. Creator shares with collaborator
        enforcer.grant_access(creator, tensor_id, collaborator)
        assert enforcer.can_read(collaborator, tensor_id) is True
        logger.log_access(tensor_id, collaborator, "read", True)

        # 4. Collaborator forks for their own work
        fork_id = f"fork-{uuid.uuid4().hex[:8]}"
        fork_record = TensorRecord(
            tensor_id=fork_id,
            entity_id="entity-fork",
            world_id="fork-world",
            tensor_blob=record.tensor_blob,
            maturity=record.maturity,
            training_cycles=record.training_cycles,
            description=f"Fork: {metadata['description']}",
        )
        tensor_db.save_tensor(fork_record)
        enforcer.create_default_permission(fork_id, collaborator)
        logger.log_access(tensor_id, collaborator, "fork", True)

        # 5. Creator publishes original as template
        enforcer.set_access_level(creator, tensor_id, "public")
        assert enforcer.can_read(community_user, tensor_id) is True
        logger.log_access(tensor_id, community_user, "read", True)

        # Verify audit trail
        original_history = logger.get_access_history(tensor_id)
        assert len(original_history) >= 4  # write, read, fork, read

        # Verify collaborator owns their fork
        assert enforcer.can_write(collaborator, fork_id) is True
        assert enforcer.can_write(creator, fork_id) is False

    def test_multi_tenant_isolation(self, tensor_db, enforcer, logger):
        """Multiple organizations should have isolated tensors."""
        org_a_users = ["org-a-alice", "org-a-bob"]
        org_b_users = ["org-b-carol", "org-b-dave"]

        org_a_group = "organization-a"
        org_b_group = "organization-b"

        # Setup organizations
        for user in org_a_users:
            enforcer.add_user_to_group(user, org_a_group)
        for user in org_b_users:
            enforcer.add_user_to_group(user, org_b_group)

        # Org A creates tensors
        org_a_tensor, _ = create_character_tensor("scientist")
        org_a_tensor_id = "org-a-tensor"
        record_a = TensorRecord(
            tensor_id=org_a_tensor_id,
            entity_id="entity-org-a",
            world_id="org-a-world",
            tensor_blob=serialize_tensor(org_a_tensor),
            maturity=0.9,
            training_cycles=50,
        )
        tensor_db.save_tensor(record_a)
        enforcer.create_default_permission(org_a_tensor_id, org_a_users[0])
        enforcer.grant_group_access(org_a_users[0], org_a_tensor_id, org_a_group)

        # Org B creates tensors
        org_b_tensor, _ = create_character_tensor("merchant")
        org_b_tensor_id = "org-b-tensor"
        record_b = TensorRecord(
            tensor_id=org_b_tensor_id,
            entity_id="entity-org-b",
            world_id="org-b-world",
            tensor_blob=serialize_tensor(org_b_tensor),
            maturity=0.9,
            training_cycles=50,
        )
        tensor_db.save_tensor(record_b)
        enforcer.create_default_permission(org_b_tensor_id, org_b_users[0])
        enforcer.grant_group_access(org_b_users[0], org_b_tensor_id, org_b_group)

        # Verify isolation
        # Org A users can access Org A tensor
        assert enforcer.can_read(org_a_users[0], org_a_tensor_id) is True
        assert enforcer.can_read(org_a_users[1], org_a_tensor_id) is True

        # Org A users cannot access Org B tensor
        assert enforcer.can_read(org_a_users[0], org_b_tensor_id) is False
        assert enforcer.can_read(org_a_users[1], org_b_tensor_id) is False

        # Org B users can access Org B tensor
        assert enforcer.can_read(org_b_users[0], org_b_tensor_id) is True
        assert enforcer.can_read(org_b_users[1], org_b_tensor_id) is True

        # Org B users cannot access Org A tensor
        assert enforcer.can_read(org_b_users[0], org_a_tensor_id) is False


# ============================================================================
# Run configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
