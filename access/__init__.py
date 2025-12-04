"""
Access control for Timepoint-Daedalus tensor system.

This module provides:
- Permission enforcement for tensor read/write/fork operations
- Audit logging for all access attempts
- User and group management

Basic usage:
    >>> from access import PermissionEnforcer, AuditLogger
    >>> enforcer = PermissionEnforcer("tensors.db")
    >>> enforcer.create_default_permission("tensor-001", "user-123")
    >>> if enforcer.can_read("user-456", "tensor-001"):
    ...     print("Access granted")

Sharing workflow:
    >>> enforcer.grant_access("user-123", "tensor-001", "user-456")
    >>> enforcer.set_access_level("user-123", "tensor-001", "public")

Audit logging:
    >>> logger = AuditLogger("tensors.db")
    >>> logger.log_access("tensor-001", "user-123", "read", success=True)
    >>> history = logger.get_access_history("tensor-001")

Phase 5: Access Control
"""

from .permissions import (
    TensorPermission,
    PermissionEnforcer,
    PermissionDenied,
)

from .audit import (
    AccessAuditLog,
    AuditLogger,
)


__all__ = [
    # Permissions
    "TensorPermission",
    "PermissionEnforcer",
    "PermissionDenied",
    # Audit
    "AccessAuditLog",
    "AuditLogger",
]

__version__ = "0.1.0"
