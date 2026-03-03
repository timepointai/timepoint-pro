"""
Tensor CRUD endpoints.

Provides REST API for tensor operations with permission enforcement.

Phase 6: Public API
"""

import uuid

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status

from access.audit import AuditLogger
from access.permissions import PermissionEnforcer
from schemas import TTMTensor
from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import deserialize_tensor, serialize_tensor

from ..auth import get_current_user
from ..deps import get_audit_logger, get_enforcer, get_tensor_db
from ..models import (
    AccessLevelRequest,
    ShareRequest,
    StatsResponse,
    TensorCreate,
    TensorListResponse,
    TensorResponse,
    TensorUpdate,
    TensorValues,
)

router = APIRouter(prefix="/tensors", tags=["tensors"])


# ============================================================================
# Helper Functions
# ============================================================================


def tensor_to_values(tensor: TTMTensor) -> TensorValues:
    """Convert TTMTensor to TensorValues model."""
    ctx, bio, beh = tensor.to_arrays()
    return TensorValues(
        context=ctx.tolist(),
        biology=bio.tolist(),
        behavior=beh.tolist(),
    )


def values_to_tensor(values: TensorValues) -> TTMTensor:
    """Convert TensorValues model to TTMTensor."""
    return TTMTensor.from_arrays(
        context=np.array(values.context, dtype=np.float32),
        biology=np.array(values.biology, dtype=np.float32),
        behavior=np.array(values.behavior, dtype=np.float32),
    )


def record_to_response(
    record: TensorRecord,
    permission: dict,
) -> TensorResponse:
    """Convert TensorRecord to TensorResponse."""
    tensor = deserialize_tensor(record.tensor_blob)
    return TensorResponse(
        tensor_id=record.tensor_id,
        entity_id=record.entity_id,
        world_id=record.world_id,
        values=tensor_to_values(tensor),
        maturity=record.maturity,
        training_cycles=record.training_cycles,
        version=record.version,
        description=record.description,
        category=record.category,
        access_level=permission.get("access_level", "private"),
        owner_id=permission.get("owner_id", ""),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ============================================================================
# CRUD Endpoints
# ============================================================================


@router.get("", response_model=TensorListResponse)
async def list_tensors(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Page size"),
    entity_id: str | None = Query(default=None, description="Filter by entity"),
    world_id: str | None = Query(default=None, description="Filter by world"),
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    List tensors accessible to the current user.

    Returns paginated list of tensors the user can read.
    """
    # Get all accessible tensor IDs
    accessible_ids = enforcer.list_accessible_tensors(user_id, include_public=True)

    # Get all tensor records
    all_records = db.list_tensors(entity_id=entity_id, world_id=world_id)

    # Filter to accessible ones
    accessible_records = [r for r in all_records if r.tensor_id in accessible_ids]

    # Paginate
    total = len(accessible_records)
    start = (page - 1) * page_size
    end = start + page_size
    page_records = accessible_records[start:end]

    # Build response
    tensors = []
    for record in page_records:
        perm = enforcer.get_permission(record.tensor_id)
        if perm:
            tensors.append(
                record_to_response(
                    record,
                    {
                        "access_level": perm.access_level,
                        "owner_id": perm.owner_id,
                    },
                )
            )

    return TensorListResponse(
        tensors=tensors,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TensorResponse, status_code=status.HTTP_201_CREATED)
async def create_tensor(
    data: TensorCreate,
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Create a new tensor.

    The current user becomes the owner.
    """
    # Generate ID if not provided
    tensor_id = data.tensor_id or f"tensor-{uuid.uuid4().hex[:12]}"

    # Check if ID already exists
    existing = db.get_tensor(tensor_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tensor with ID '{tensor_id}' already exists",
        )

    # Convert values to tensor
    tensor = values_to_tensor(data.values)

    # Create record
    record = TensorRecord(
        tensor_id=tensor_id,
        entity_id=data.entity_id,
        world_id=data.world_id,
        tensor_blob=serialize_tensor(tensor),
        maturity=data.maturity,
        training_cycles=data.training_cycles,
        description=data.description,
        category=data.category,
    )

    # Save to database
    db.save_tensor(record)

    # Create permission
    enforcer.create_default_permission(tensor_id, user_id, data.access_level)

    # Log creation
    logger.log_access(tensor_id, user_id, "create", True)

    # Return response
    return record_to_response(record, {"access_level": data.access_level, "owner_id": user_id})


@router.get("/{tensor_id}", response_model=TensorResponse)
async def get_tensor(
    tensor_id: str,
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Get a tensor by ID.

    Requires read permission.
    """
    # Get record
    record = db.get_tensor(tensor_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tensor '{tensor_id}' not found"
        )

    # Check permission
    if not enforcer.can_read(user_id, tensor_id):
        logger.log_access(tensor_id, user_id, "read", False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"No read access to tensor '{tensor_id}'"
        )

    # Log access
    logger.log_access(tensor_id, user_id, "read", True)
    enforcer.record_access(tensor_id)

    # Get permission info
    perm = enforcer.get_permission(tensor_id)

    return record_to_response(
        record,
        {
            "access_level": perm.access_level if perm else "private",
            "owner_id": perm.owner_id if perm else "",
        },
    )


@router.put("/{tensor_id}", response_model=TensorResponse)
async def update_tensor(
    tensor_id: str,
    data: TensorUpdate,
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Update a tensor.

    Requires write permission (owner only).
    """
    # Get existing record
    record = db.get_tensor(tensor_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tensor '{tensor_id}' not found"
        )

    # Check permission
    if not enforcer.can_write(user_id, tensor_id):
        logger.log_access(tensor_id, user_id, "write", False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"No write access to tensor '{tensor_id}'"
        )

    # Update fields
    if data.entity_id is not None:
        record.entity_id = data.entity_id
    if data.world_id is not None:
        record.world_id = data.world_id
    if data.values is not None:
        tensor = values_to_tensor(data.values)
        record.tensor_blob = serialize_tensor(tensor)
    if data.description is not None:
        record.description = data.description
    if data.category is not None:
        record.category = data.category
    if data.maturity is not None:
        record.maturity = data.maturity
    if data.training_cycles is not None:
        record.training_cycles = data.training_cycles

    # Save
    db.save_tensor(record)

    # Update access level if provided
    if data.access_level is not None:
        enforcer.set_access_level(user_id, tensor_id, data.access_level)

    # Log update
    logger.log_access(tensor_id, user_id, "write", True)

    # Get updated permission
    perm = enforcer.get_permission(tensor_id)

    return record_to_response(
        record,
        {
            "access_level": perm.access_level if perm else "private",
            "owner_id": perm.owner_id if perm else user_id,
        },
    )


@router.delete("/{tensor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tensor(
    tensor_id: str,
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Delete a tensor.

    Requires delete permission (owner only).
    """
    # Check exists
    record = db.get_tensor(tensor_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tensor '{tensor_id}' not found"
        )

    # Check permission
    if not enforcer.can_delete(user_id, tensor_id):
        logger.log_access(tensor_id, user_id, "delete", False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No delete access to tensor '{tensor_id}'",
        )

    # Delete
    db.delete_tensor(tensor_id)
    enforcer.delete_permission(tensor_id)

    # Log deletion
    logger.log_access(tensor_id, user_id, "delete", True)


# ============================================================================
# Sharing Endpoints
# ============================================================================


@router.post("/{tensor_id}/share", status_code=status.HTTP_200_OK)
async def share_tensor(
    tensor_id: str,
    data: ShareRequest,
    user_id: str = Depends(get_current_user),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Share a tensor with another user.

    Only the owner can share.
    """
    # Check permission exists
    perm = enforcer.get_permission(tensor_id)
    if perm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tensor '{tensor_id}' not found"
        )

    # Grant access
    result = enforcer.grant_access(user_id, tensor_id, data.user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can share this tensor"
        )

    logger.log_access(tensor_id, user_id, "share", True, {"shared_with": data.user_id})

    return {"message": f"Tensor shared with {data.user_id}"}


@router.delete("/{tensor_id}/share/{target_user_id}", status_code=status.HTTP_200_OK)
async def unshare_tensor(
    tensor_id: str,
    target_user_id: str,
    user_id: str = Depends(get_current_user),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Revoke sharing from a user.

    Only the owner can revoke.
    """
    result = enforcer.revoke_access(user_id, tensor_id, target_user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can revoke sharing"
        )

    logger.log_access(tensor_id, user_id, "unshare", True, {"revoked_from": target_user_id})

    return {"message": f"Sharing revoked from {target_user_id}"}


@router.put("/{tensor_id}/access", status_code=status.HTTP_200_OK)
async def set_access_level(
    tensor_id: str,
    data: AccessLevelRequest,
    user_id: str = Depends(get_current_user),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Change tensor access level.

    Only the owner can change access level.
    """
    result = enforcer.set_access_level(user_id, tensor_id, data.access_level)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can change access level"
        )

    logger.log_access(tensor_id, user_id, "set_access", True, {"access_level": data.access_level})

    return {"message": f"Access level set to {data.access_level}"}


# ============================================================================
# Fork Endpoint
# ============================================================================


@router.post(
    "/{tensor_id}/fork", response_model=TensorResponse, status_code=status.HTTP_201_CREATED
)
async def fork_tensor(
    tensor_id: str,
    new_id: str | None = Query(default=None, description="ID for the forked tensor"),
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Fork (clone) a tensor.

    Creates a new tensor owned by the current user.
    Requires fork permission (read access).
    """
    # Get source tensor
    source = db.get_tensor(tensor_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tensor '{tensor_id}' not found"
        )

    # Check permission
    if not enforcer.can_fork(user_id, tensor_id):
        logger.log_access(tensor_id, user_id, "fork", False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"No fork access to tensor '{tensor_id}'"
        )

    # Generate fork ID
    fork_id = new_id or f"fork-{uuid.uuid4().hex[:12]}"

    # Check fork ID doesn't exist
    if db.get_tensor(fork_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tensor with ID '{fork_id}' already exists",
        )

    # Create fork
    fork_record = TensorRecord(
        tensor_id=fork_id,
        entity_id=source.entity_id,
        world_id=source.world_id,
        tensor_blob=source.tensor_blob,
        maturity=source.maturity,
        training_cycles=source.training_cycles,
        description=f"Fork of: {source.description or tensor_id}",
        category=source.category,
    )

    db.save_tensor(fork_record)

    # Create permission (private by default)
    enforcer.create_default_permission(fork_id, user_id, "private")

    # Log fork
    logger.log_access(tensor_id, user_id, "fork", True, {"fork_id": fork_id})
    logger.log_access(fork_id, user_id, "create", True, {"source_id": tensor_id})

    return record_to_response(fork_record, {"access_level": "private", "owner_id": user_id})


# ============================================================================
# Stats Endpoint
# ============================================================================


@router.get("/stats/summary", response_model=StatsResponse)
async def get_stats(
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
):
    """
    Get database statistics.

    Returns overall tensor statistics.
    """
    stats = db.get_stats()
    return StatsResponse(
        total_tensors=stats["total_tensors"],
        operational_count=stats["operational_count"],
        training_count=stats["training_count"],
        avg_maturity=stats["avg_maturity"],
        total_versions=stats["total_versions"],
    )
