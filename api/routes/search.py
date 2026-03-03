"""
Semantic search endpoints.

Provides REST API for tensor semantic search and composition.

Phase 6: Public API
"""

from fastapi import APIRouter, Depends, HTTPException, status

from access.audit import AuditLogger
from access.permissions import PermissionEnforcer
from tensor_persistence import TensorDatabase
from tensor_serialization import deserialize_tensor

from ..auth import get_current_user
from ..deps import get_audit_logger, get_enforcer, get_tensor_db, get_tensor_rag
from ..models import (
    ComposeRequest,
    ComposeResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    TensorValues,
)

router = APIRouter(prefix="/search", tags=["search"])


# ============================================================================
# Helper Functions
# ============================================================================


def tensor_to_values(tensor) -> TensorValues:
    """Convert TTMTensor to TensorValues model."""
    ctx, bio, beh = tensor.to_arrays()
    return TensorValues(
        context=ctx.tolist(),
        biology=bio.tolist(),
        behavior=beh.tolist(),
    )


# ============================================================================
# Search Endpoints
# ============================================================================


@router.post("", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Semantic search for tensors.

    Searches tensor descriptions using natural language queries.
    Results are filtered to tensors the user can access.
    """
    # Get RAG instance
    rag = get_tensor_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search is not available (RAG not configured)",
        )

    # Perform search with permission filtering
    raw_results = rag.search(
        query=request.query,
        n_results=request.n_results * 2,  # Get extra for filtering
        min_maturity=request.min_maturity,
        categories=request.categories,
        user_id=user_id,  # Permission filtering in RAG
    )

    # Build response
    results = []
    for result in raw_results:
        # Double-check permission (defense in depth)
        if not enforcer.can_read(user_id, result.tensor_id):
            continue

        # Build result item
        item = SearchResultItem(
            tensor_id=result.tensor_id,
            score=result.score,
            entity_id=result.tensor_record.entity_id,
            description=result.tensor_record.description,
            category=result.tensor_record.category,
            maturity=result.tensor_record.maturity,
        )

        # Include values if requested
        if request.include_values:
            tensor = deserialize_tensor(result.tensor_record.tensor_blob)
            item.values = tensor_to_values(tensor)

        results.append(item)

        # Limit to requested count
        if len(results) >= request.n_results:
            break

    # Log search
    logger.log_access(
        "search", user_id, "search", True, {"query": request.query, "results": len(results)}
    )

    return SearchResponse(
        results=results,
        query=request.query,
        total=len(results),
    )


@router.post("/compose", response_model=ComposeResponse)
async def compose_tensors(
    request: ComposeRequest,
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Compose multiple tensors into a new tensor.

    Requires read access to all source tensors.
    """
    # Get RAG instance
    rag = get_tensor_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tensor composition is not available (RAG not configured)",
        )

    # Verify access to all tensors
    for tensor_id in request.tensor_ids:
        if not enforcer.can_read(user_id, tensor_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No read access to tensor '{tensor_id}'",
            )

    # Get tensor records
    tensors = []
    for tensor_id in request.tensor_ids:
        record = db.get_tensor(tensor_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Tensor '{tensor_id}' not found"
            )
        tensor = deserialize_tensor(record.tensor_blob)
        tensors.append(tensor)

    # Validate weights if provided
    weights = request.weights
    if weights is not None:
        if len(weights) != len(tensors):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Weights count ({len(weights)}) must match tensor count ({len(tensors)})",
            )

    # Compose
    composed = rag.composer.compose_tensors(
        tensors,
        method=request.method,
        weights=weights,
    )

    # Log composition
    logger.log_access(
        "compose",
        user_id,
        "compose",
        True,
        {"source_tensors": request.tensor_ids, "method": request.method},
    )

    return ComposeResponse(
        values=tensor_to_values(composed),
        source_tensors=request.tensor_ids,
        method=request.method,
    )


@router.get("/similar/{tensor_id}", response_model=SearchResponse)
async def find_similar(
    tensor_id: str,
    n_results: int = 5,
    user_id: str = Depends(get_current_user),
    db: TensorDatabase = Depends(get_tensor_db),
    enforcer: PermissionEnforcer = Depends(get_enforcer),
    logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Find tensors similar to a given tensor.

    Requires read access to the source tensor.
    """
    # Check access to source
    if not enforcer.can_read(user_id, tensor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"No read access to tensor '{tensor_id}'"
        )

    # Get source record
    record = db.get_tensor(tensor_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tensor '{tensor_id}' not found"
        )

    # Get RAG instance
    rag = get_tensor_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search is not available (RAG not configured)",
        )

    # Use description for search
    query = record.description or f"Entity: {record.entity_id}"

    # Search for similar
    raw_results = rag.search(
        query=query,
        n_results=n_results + 1,  # +1 to exclude self
        user_id=user_id,
    )

    # Filter out the source tensor and build response
    results = []
    for result in raw_results:
        if result.tensor_id == tensor_id:
            continue

        if not enforcer.can_read(user_id, result.tensor_id):
            continue

        results.append(
            SearchResultItem(
                tensor_id=result.tensor_id,
                score=result.score,
                entity_id=result.tensor_record.entity_id,
                description=result.tensor_record.description,
                category=result.tensor_record.category,
                maturity=result.tensor_record.maturity,
            )
        )

        if len(results) >= n_results:
            break

    return SearchResponse(
        results=results,
        query=f"Similar to: {tensor_id}",
        total=len(results),
    )
