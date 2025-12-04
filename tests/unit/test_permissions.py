"""
Test suite for access control layer (Phase 5).

Tests cover:
- TensorPermission data class
- PermissionEnforcer permission checks
- Access granting/revoking
- User group management
- AuditLogger event tracking
- Access analytics
"""

import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

from access.permissions import (
    TensorPermission,
    PermissionEnforcer,
    PermissionDenied,
)
from access.audit import (
    AccessAuditLog,
    AuditLogger,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    """Create temporary database path."""
    return str(tmp_path / "permissions_test.db")


@pytest.fixture
def enforcer(tmp_db_path) -> PermissionEnforcer:
    """Create PermissionEnforcer with temp database."""
    return PermissionEnforcer(tmp_db_path)


@pytest.fixture
def logger(tmp_db_path) -> AuditLogger:
    """Create AuditLogger with temp database."""
    return AuditLogger(tmp_db_path)


@pytest.fixture
def sample_permission() -> TensorPermission:
    """Create sample TensorPermission."""
    return TensorPermission(
        tensor_id="tensor-001",
        owner_id="owner-001",
        access_level="private",
    )


# ============================================================================
# TensorPermission Tests
# ============================================================================

@pytest.mark.unit
class TestTensorPermission:
    """Tests for TensorPermission data class."""

    def test_default_values(self):
        """Permission should have sensible defaults."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
        )
        assert perm.access_level == "private"
        assert perm.shared_with == []
        assert perm.shared_groups == []
        assert perm.api_enabled is False
        assert perm.rate_limit == 100
        assert perm.access_count == 0
        assert perm.created_at is not None
        assert perm.modified_at is not None

    def test_shared_with_list(self):
        """Permission should track shared users."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="shared",
            shared_with=["user-1", "user-2", "user-3"],
        )
        assert len(perm.shared_with) == 3
        assert "user-2" in perm.shared_with

    def test_invalid_access_level_raises(self):
        """Invalid access level should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid access_level"):
            TensorPermission(
                tensor_id="tensor-001",
                owner_id="owner-001",
                access_level="invalid",
            )

    def test_api_settings(self):
        """API settings should be configurable."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            api_enabled=True,
            rate_limit=1000,
        )
        assert perm.api_enabled is True
        assert perm.rate_limit == 1000


# ============================================================================
# PermissionEnforcer Basic Tests
# ============================================================================

@pytest.mark.unit
class TestPermissionEnforcerBasic:
    """Basic tests for PermissionEnforcer."""

    def test_initialization(self, enforcer):
        """Enforcer should initialize with database."""
        assert enforcer.db_path.exists()

    def test_create_default_permission(self, enforcer):
        """Should create default permission for new tensor."""
        perm = enforcer.create_default_permission(
            tensor_id="tensor-new",
            owner_id="user-creator",
        )
        assert perm.tensor_id == "tensor-new"
        assert perm.owner_id == "user-creator"
        assert perm.access_level == "private"

        # Verify persisted
        loaded = enforcer.get_permission("tensor-new")
        assert loaded is not None
        assert loaded.owner_id == "user-creator"

    def test_set_and_get_permission(self, enforcer, sample_permission):
        """Should save and retrieve permission."""
        enforcer.set_permission(sample_permission)

        loaded = enforcer.get_permission(sample_permission.tensor_id)
        assert loaded is not None
        assert loaded.tensor_id == sample_permission.tensor_id
        assert loaded.owner_id == sample_permission.owner_id

    def test_get_nonexistent_permission(self, enforcer):
        """Should return None for nonexistent tensor."""
        result = enforcer.get_permission("nonexistent-tensor")
        assert result is None

    def test_delete_permission(self, enforcer, sample_permission):
        """Should delete permission record."""
        enforcer.set_permission(sample_permission)
        assert enforcer.get_permission(sample_permission.tensor_id) is not None

        deleted = enforcer.delete_permission(sample_permission.tensor_id)
        assert deleted is True
        assert enforcer.get_permission(sample_permission.tensor_id) is None


# ============================================================================
# Permission Check Tests
# ============================================================================

@pytest.mark.unit
class TestPermissionChecks:
    """Tests for permission check methods."""

    def test_owner_can_read(self, enforcer):
        """Owner should be able to read their tensor."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        assert enforcer.can_read("owner-001", "tensor-001") is True

    def test_owner_can_write(self, enforcer):
        """Owner should be able to write their tensor."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        assert enforcer.can_write("owner-001", "tensor-001") is True

    def test_owner_can_delete(self, enforcer):
        """Owner should be able to delete their tensor."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        assert enforcer.can_delete("owner-001", "tensor-001") is True

    def test_owner_can_fork(self, enforcer):
        """Owner should be able to fork their tensor."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        assert enforcer.can_fork("owner-001", "tensor-001") is True

    def test_non_owner_cannot_read_private(self, enforcer):
        """Non-owner should not read private tensor."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        assert enforcer.can_read("other-user", "tensor-001") is False

    def test_non_owner_cannot_write(self, enforcer):
        """Non-owner should not write any tensor."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="public",  # Even public
        )
        enforcer.set_permission(perm)

        assert enforcer.can_write("other-user", "tensor-001") is False

    def test_non_owner_cannot_delete(self, enforcer):
        """Non-owner should not delete any tensor."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="public",
        )
        enforcer.set_permission(perm)

        assert enforcer.can_delete("other-user", "tensor-001") is False

    def test_public_readable_by_anyone(self, enforcer):
        """Public tensor should be readable by anyone."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="public",
        )
        enforcer.set_permission(perm)

        assert enforcer.can_read("random-user", "tensor-001") is True
        assert enforcer.can_read("another-user", "tensor-001") is True

    def test_public_forkable_by_anyone(self, enforcer):
        """Public tensor should be forkable by anyone."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="public",
        )
        enforcer.set_permission(perm)

        assert enforcer.can_fork("random-user", "tensor-001") is True

    def test_shared_user_can_read(self, enforcer):
        """Shared user should be able to read."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="shared",
            shared_with=["user-shared"],
        )
        enforcer.set_permission(perm)

        assert enforcer.can_read("user-shared", "tensor-001") is True
        assert enforcer.can_read("user-not-shared", "tensor-001") is False

    def test_shared_user_cannot_write(self, enforcer):
        """Shared user should not be able to write."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="shared",
            shared_with=["user-shared"],
        )
        enforcer.set_permission(perm)

        assert enforcer.can_write("user-shared", "tensor-001") is False

    def test_shared_user_can_fork(self, enforcer):
        """Shared user should be able to fork."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="shared",
            shared_with=["user-shared"],
        )
        enforcer.set_permission(perm)

        assert enforcer.can_fork("user-shared", "tensor-001") is True


# ============================================================================
# Enforce Tests
# ============================================================================

@pytest.mark.unit
class TestEnforce:
    """Tests for enforce method."""

    def test_enforce_read_success(self, enforcer):
        """Enforce should pass for valid read."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        # Should not raise
        enforcer.enforce("owner-001", "tensor-001", "read")

    def test_enforce_read_denied(self, enforcer):
        """Enforce should raise PermissionDenied for invalid read."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        with pytest.raises(PermissionDenied) as exc:
            enforcer.enforce("other-user", "tensor-001", "read")

        assert exc.value.user_id == "other-user"
        assert exc.value.tensor_id == "tensor-001"
        assert exc.value.action == "read"

    def test_enforce_write_denied(self, enforcer):
        """Enforce should raise for non-owner write."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="public",
        )
        enforcer.set_permission(perm)

        with pytest.raises(PermissionDenied):
            enforcer.enforce("other-user", "tensor-001", "write")

    def test_enforce_invalid_action(self, enforcer):
        """Enforce should raise ValueError for invalid action."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        with pytest.raises(ValueError, match="Invalid action"):
            enforcer.enforce("owner-001", "tensor-001", "invalid_action")


# ============================================================================
# Access Management Tests
# ============================================================================

@pytest.mark.unit
class TestAccessManagement:
    """Tests for grant/revoke access methods."""

    def test_grant_access(self, enforcer):
        """Granting access should enable read."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        # Before grant
        assert enforcer.can_read("user-new", "tensor-001") is False

        # Grant access
        result = enforcer.grant_access("owner-001", "tensor-001", "user-new")
        assert result is True

        # After grant
        assert enforcer.can_read("user-new", "tensor-001") is True

    def test_grant_access_upgrades_to_shared(self, enforcer):
        """Granting access should upgrade private to shared."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        perm = enforcer.get_permission("tensor-001")
        assert perm.access_level == "private"

        enforcer.grant_access("owner-001", "tensor-001", "user-new")

        perm = enforcer.get_permission("tensor-001")
        assert perm.access_level == "shared"

    def test_grant_access_non_owner_fails(self, enforcer):
        """Non-owner cannot grant access."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        result = enforcer.grant_access("not-owner", "tensor-001", "user-new")
        assert result is False

    def test_revoke_access(self, enforcer):
        """Revoking access should remove read ability."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="shared",
            shared_with=["user-shared"],
        )
        enforcer.set_permission(perm)

        # Before revoke
        assert enforcer.can_read("user-shared", "tensor-001") is True

        # Revoke
        result = enforcer.revoke_access("owner-001", "tensor-001", "user-shared")
        assert result is True

        # After revoke
        assert enforcer.can_read("user-shared", "tensor-001") is False

    def test_revoke_access_downgrades_to_private(self, enforcer):
        """Revoking last share should downgrade to private."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="shared",
            shared_with=["only-user"],
        )
        enforcer.set_permission(perm)

        enforcer.revoke_access("owner-001", "tensor-001", "only-user")

        perm = enforcer.get_permission("tensor-001")
        assert perm.access_level == "private"

    def test_set_access_level_public(self, enforcer):
        """Setting public should make readable by anyone."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        assert enforcer.can_read("random-user", "tensor-001") is False

        enforcer.set_access_level("owner-001", "tensor-001", "public")

        assert enforcer.can_read("random-user", "tensor-001") is True

    def test_set_access_level_non_owner_fails(self, enforcer):
        """Non-owner cannot change access level."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        result = enforcer.set_access_level("not-owner", "tensor-001", "public")
        assert result is False


# ============================================================================
# User Group Tests
# ============================================================================

@pytest.mark.unit
class TestUserGroups:
    """Tests for user group management."""

    def test_add_user_to_group(self, enforcer):
        """Should add user to group."""
        enforcer.add_user_to_group("user-001", "group-researchers")

        groups = enforcer.get_user_groups("user-001")
        assert "group-researchers" in groups

    def test_get_user_groups_multiple(self, enforcer):
        """Should return all groups for user."""
        enforcer.add_user_to_group("user-001", "group-a")
        enforcer.add_user_to_group("user-001", "group-b")
        enforcer.add_user_to_group("user-001", "group-c")

        groups = enforcer.get_user_groups("user-001")
        assert len(groups) == 3
        assert groups == {"group-a", "group-b", "group-c"}

    def test_remove_user_from_group(self, enforcer):
        """Should remove user from group."""
        enforcer.add_user_to_group("user-001", "group-a")
        enforcer.add_user_to_group("user-001", "group-b")

        enforcer.remove_user_from_group("user-001", "group-a")

        groups = enforcer.get_user_groups("user-001")
        assert "group-a" not in groups
        assert "group-b" in groups

    def test_get_group_members(self, enforcer):
        """Should get all members of a group."""
        enforcer.add_user_to_group("user-001", "group-shared")
        enforcer.add_user_to_group("user-002", "group-shared")
        enforcer.add_user_to_group("user-003", "group-shared")

        members = enforcer.get_group_members("group-shared")
        assert len(members) == 3
        assert set(members) == {"user-001", "user-002", "user-003"}

    def test_group_access_enables_read(self, enforcer):
        """Sharing with group should enable read for members."""
        # Create tensor with group access
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="shared",
            shared_groups=["group-researchers"],
        )
        enforcer.set_permission(perm)

        # Add user to group
        enforcer.add_user_to_group("user-001", "group-researchers")

        # User should have access via group
        assert enforcer.can_read("user-001", "tensor-001") is True

        # User not in group should not have access
        assert enforcer.can_read("user-not-in-group", "tensor-001") is False

    def test_grant_group_access(self, enforcer):
        """Should grant access to a group."""
        enforcer.create_default_permission("tensor-001", "owner-001")
        enforcer.add_user_to_group("user-001", "group-a")

        # Before grant
        assert enforcer.can_read("user-001", "tensor-001") is False

        # Grant group access
        enforcer.grant_group_access("owner-001", "tensor-001", "group-a")

        # After grant
        assert enforcer.can_read("user-001", "tensor-001") is True

    def test_revoke_group_access(self, enforcer):
        """Should revoke access from a group."""
        perm = TensorPermission(
            tensor_id="tensor-001",
            owner_id="owner-001",
            access_level="shared",
            shared_groups=["group-a"],
        )
        enforcer.set_permission(perm)
        enforcer.add_user_to_group("user-001", "group-a")

        # Before revoke
        assert enforcer.can_read("user-001", "tensor-001") is True

        # Revoke group access
        enforcer.revoke_group_access("owner-001", "tensor-001", "group-a")

        # After revoke
        assert enforcer.can_read("user-001", "tensor-001") is False


# ============================================================================
# Access Recording Tests
# ============================================================================

@pytest.mark.unit
class TestAccessRecording:
    """Tests for access recording."""

    def test_record_access_updates_count(self, enforcer):
        """Recording access should increment count."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        perm = enforcer.get_permission("tensor-001")
        assert perm.access_count == 0

        enforcer.record_access("tensor-001")
        enforcer.record_access("tensor-001")
        enforcer.record_access("tensor-001")

        perm = enforcer.get_permission("tensor-001")
        assert perm.access_count == 3

    def test_record_access_updates_timestamp(self, enforcer):
        """Recording access should update accessed_at."""
        enforcer.create_default_permission("tensor-001", "owner-001")

        perm = enforcer.get_permission("tensor-001")
        assert perm.accessed_at is None

        enforcer.record_access("tensor-001")

        perm = enforcer.get_permission("tensor-001")
        assert perm.accessed_at is not None


# ============================================================================
# List Queries Tests
# ============================================================================

@pytest.mark.unit
class TestListQueries:
    """Tests for list query methods."""

    def test_list_accessible_tensors(self, enforcer):
        """Should list all tensors accessible by user."""
        # Create tensors with different access
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-owned",
            owner_id="user-001",
        ))
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-shared",
            owner_id="user-002",
            access_level="shared",
            shared_with=["user-001"],
        ))
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-public",
            owner_id="user-003",
            access_level="public",
        ))
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-private",
            owner_id="user-004",
        ))

        accessible = enforcer.list_accessible_tensors("user-001")

        assert "tensor-owned" in accessible
        assert "tensor-shared" in accessible
        assert "tensor-public" in accessible
        assert "tensor-private" not in accessible

    def test_list_owned_tensors(self, enforcer):
        """Should list tensors owned by user."""
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-1",
            owner_id="user-001",
        ))
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-2",
            owner_id="user-001",
        ))
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-3",
            owner_id="user-002",
        ))

        owned = enforcer.list_owned_tensors("user-001")

        assert len(owned) == 2
        assert "tensor-1" in owned
        assert "tensor-2" in owned
        assert "tensor-3" not in owned

    def test_list_shared_tensors(self, enforcer):
        """Should list tensors shared with user (not owned)."""
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-owned",
            owner_id="user-001",
        ))
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-shared-1",
            owner_id="user-002",
            access_level="shared",
            shared_with=["user-001"],
        ))
        enforcer.set_permission(TensorPermission(
            tensor_id="tensor-shared-2",
            owner_id="user-003",
            access_level="shared",
            shared_with=["user-001"],
        ))

        shared = enforcer.list_shared_tensors("user-001")

        assert "tensor-owned" not in shared  # Owned, not shared
        assert "tensor-shared-1" in shared
        assert "tensor-shared-2" in shared


# ============================================================================
# AuditLogger Tests
# ============================================================================

@pytest.mark.unit
class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_log_access_creates_record(self, logger):
        """Logging access should create record."""
        event_id = logger.log_access(
            tensor_id="tensor-001",
            user_id="user-001",
            action="read",
            success=True,
        )

        assert event_id > 0
        assert logger.get_log_count() == 1

    def test_log_access_with_metadata(self, logger):
        """Should store metadata with log."""
        logger.log_access(
            tensor_id="tensor-001",
            user_id="user-001",
            action="read",
            success=True,
            metadata={"ip_address": "192.168.1.1", "client": "api"},
        )

        history = logger.get_access_history("tensor-001")
        assert len(history) == 1
        assert history[0].metadata is not None
        assert history[0].metadata["ip_address"] == "192.168.1.1"

    def test_get_access_history(self, logger):
        """Should retrieve access history for tensor."""
        logger.log_access("tensor-001", "user-001", "read", True)
        logger.log_access("tensor-001", "user-002", "read", True)
        logger.log_access("tensor-001", "user-003", "write", False)
        logger.log_access("tensor-002", "user-001", "read", True)

        history = logger.get_access_history("tensor-001")

        assert len(history) == 3
        # Newest first
        assert history[0].action == "write"
        assert history[0].success is False

    def test_get_user_activity(self, logger):
        """Should retrieve activity for a user."""
        logger.log_access("tensor-001", "user-001", "read", True)
        logger.log_access("tensor-002", "user-001", "write", True)
        logger.log_access("tensor-003", "user-001", "fork", True)
        logger.log_access("tensor-001", "user-002", "read", True)

        activity = logger.get_user_activity("user-001")

        assert len(activity) == 3
        # All should be user-001
        assert all(a.user_id == "user-001" for a in activity)

    def test_get_failed_attempts(self, logger):
        """Should retrieve failed access attempts."""
        logger.log_access("tensor-001", "user-001", "read", True)
        logger.log_access("tensor-001", "user-002", "write", False)
        logger.log_access("tensor-001", "user-003", "delete", False)

        failed = logger.get_failed_attempts(tensor_id="tensor-001")

        assert len(failed) == 2
        assert all(not f.success for f in failed)

    def test_get_action_count(self, logger):
        """Should count actions by type."""
        logger.log_access("tensor-001", "user-001", "read", True)
        logger.log_access("tensor-001", "user-002", "read", True)
        logger.log_access("tensor-001", "user-003", "read", True)
        logger.log_access("tensor-001", "user-001", "write", True)
        logger.log_access("tensor-001", "user-001", "fork", True)

        counts = logger.get_action_count("tensor-001")

        assert counts["read"] == 3
        assert counts["write"] == 1
        assert counts["fork"] == 1

    def test_get_user_count(self, logger):
        """Should count unique users."""
        logger.log_access("tensor-001", "user-001", "read", True)
        logger.log_access("tensor-001", "user-001", "read", True)  # Same user
        logger.log_access("tensor-001", "user-002", "read", True)
        logger.log_access("tensor-001", "user-003", "read", True)

        count = logger.get_user_count("tensor-001")
        assert count == 3  # 3 unique users


# ============================================================================
# AuditLogger Analytics Tests
# ============================================================================

@pytest.mark.unit
class TestAuditLoggerAnalytics:
    """Tests for AuditLogger analytics methods."""

    def test_get_most_accessed_tensors(self, logger):
        """Should return most accessed tensors."""
        # Create access patterns
        for _ in range(10):
            logger.log_access("popular-tensor", "user", "read", True)
        for _ in range(5):
            logger.log_access("medium-tensor", "user", "read", True)
        for _ in range(2):
            logger.log_access("rare-tensor", "user", "read", True)

        top = logger.get_most_accessed_tensors(limit=2)

        assert len(top) == 2
        assert top[0]["tensor_id"] == "popular-tensor"
        assert top[0]["access_count"] == 10
        assert top[1]["tensor_id"] == "medium-tensor"

    def test_get_most_active_users(self, logger):
        """Should return most active users."""
        for _ in range(8):
            logger.log_access("tensor", "active-user", "read", True)
        for _ in range(4):
            logger.log_access("tensor", "medium-user", "read", True)
        for _ in range(1):
            logger.log_access("tensor", "quiet-user", "read", True)

        top = logger.get_most_active_users(limit=2)

        assert len(top) == 2
        assert top[0]["user_id"] == "active-user"
        assert top[0]["action_count"] == 8

    def test_get_access_summary(self, logger):
        """Should return comprehensive access summary."""
        logger.log_access("tensor-001", "user-001", "read", True)
        logger.log_access("tensor-001", "user-002", "read", True)
        logger.log_access("tensor-001", "user-001", "write", True)
        logger.log_access("tensor-001", "user-003", "delete", False)

        summary = logger.get_access_summary("tensor-001")

        assert summary["tensor_id"] == "tensor-001"
        assert summary["total_accesses"] == 4
        assert summary["successful"] == 3
        assert summary["failed"] == 1
        assert summary["unique_users"] == 3
        assert summary["actions"]["read"] == 2
        assert summary["actions"]["write"] == 1
        assert summary["actions"]["delete"] == 1


# ============================================================================
# AuditLogger Cleanup Tests
# ============================================================================

@pytest.mark.unit
class TestAuditLoggerCleanup:
    """Tests for AuditLogger cleanup methods."""

    def test_cleanup_old_logs(self, logger):
        """Should remove old logs."""
        # Log some events
        for i in range(5):
            logger.log_access(f"tensor-{i}", "user", "read", True)

        initial_count = logger.get_log_count()
        assert initial_count == 5

        # Cleanup with 0 days should remove all
        deleted = logger.cleanup_old_logs(days=0)
        assert deleted == 5
        assert logger.get_log_count() == 0

    def test_clear_tensor_logs(self, logger):
        """Should remove all logs for a tensor."""
        logger.log_access("tensor-001", "user-001", "read", True)
        logger.log_access("tensor-001", "user-002", "read", True)
        logger.log_access("tensor-002", "user-001", "read", True)

        deleted = logger.clear_tensor_logs("tensor-001")

        assert deleted == 2
        assert logger.get_log_count() == 1

        # Remaining log should be tensor-002
        history = logger.get_access_history("tensor-002")
        assert len(history) == 1


# ============================================================================
# AccessAuditLog Tests
# ============================================================================

@pytest.mark.unit
class TestAccessAuditLog:
    """Tests for AccessAuditLog data class."""

    def test_default_timestamp(self):
        """Should set timestamp if not provided."""
        log = AccessAuditLog(
            tensor_id="tensor-001",
            user_id="user-001",
            action="read",
            success=True,
        )
        assert log.timestamp is not None

    def test_with_metadata(self):
        """Should store metadata."""
        log = AccessAuditLog(
            tensor_id="tensor-001",
            user_id="user-001",
            action="read",
            success=True,
            metadata={"source": "api", "version": "1.0"},
        )
        assert log.metadata["source"] == "api"


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestPermissionAuditIntegration:
    """Integration tests for permissions + audit."""

    def test_permission_check_with_logging(self, tmp_db_path):
        """Permission checks should integrate with audit logging."""
        enforcer = PermissionEnforcer(tmp_db_path)
        logger = AuditLogger(tmp_db_path)

        # Setup
        enforcer.create_default_permission("tensor-001", "owner-001")

        # Check and log successful access
        if enforcer.can_read("owner-001", "tensor-001"):
            logger.log_access("tensor-001", "owner-001", "read", True)
            enforcer.record_access("tensor-001")

        # Check and log denied access
        if not enforcer.can_read("other-user", "tensor-001"):
            logger.log_access("tensor-001", "other-user", "read", False)

        # Verify permission record updated
        perm = enforcer.get_permission("tensor-001")
        assert perm.access_count == 1

        # Verify audit logs
        history = logger.get_access_history("tensor-001")
        assert len(history) == 2

        # Check successful/failed
        successful = [h for h in history if h.success]
        failed = [h for h in history if not h.success]
        assert len(successful) == 1
        assert len(failed) == 1

    def test_sharing_workflow_with_audit(self, tmp_db_path):
        """Complete sharing workflow with audit trail."""
        enforcer = PermissionEnforcer(tmp_db_path)
        logger = AuditLogger(tmp_db_path)

        # Owner creates tensor
        enforcer.create_default_permission("shared-tensor", "owner")
        logger.log_access("shared-tensor", "owner", "write", True)

        # Colleague tries to access - denied
        can_read = enforcer.can_read("colleague", "shared-tensor")
        logger.log_access("shared-tensor", "colleague", "read", can_read)
        assert can_read is False

        # Owner shares with colleague
        enforcer.grant_access("owner", "shared-tensor", "colleague")

        # Colleague can now access
        can_read = enforcer.can_read("colleague", "shared-tensor")
        logger.log_access("shared-tensor", "colleague", "read", can_read)
        assert can_read is True

        # Verify audit trail
        history = logger.get_access_history("shared-tensor")
        assert len(history) == 3

        # Check user activity
        colleague_activity = logger.get_user_activity("colleague")
        assert len(colleague_activity) == 2
