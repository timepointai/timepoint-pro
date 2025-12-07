"""
Batch API routes.

Provides endpoints for creating and managing batch simulation jobs.

Phase 6: Public API - Batch Submission
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..auth import get_current_user
from ..models_batch import (
    BatchCreateRequest,
    BatchCancelRequest,
    BatchJobResponse,
    BatchDetailResponse,
    BatchListResponse,
    BatchStatsResponse,
    BatchStatus,
    BatchProgress,
    BatchCostSummary,
    UsageResponse,
    UsageHistoryResponse,
)
from ..batch_runner import (
    get_batch_runner,
    get_batch,
    list_batches,
    BatchJob,
)
from ..middleware.rate_limit import get_limiter
from ..middleware.usage_quota import (
    get_quota_status,
    enforce_simulation_quota,
    enforce_batch_size,
    enforce_cost_quota,
    record_batch_start,
)
from ..usage_storage import get_usage_database


router = APIRouter(prefix="/simulations/batch", tags=["batch"])
limiter = get_limiter()


# ============================================================================
# Helper Functions
# ============================================================================

def batch_to_response(batch: BatchJob) -> BatchJobResponse:
    """Convert internal batch to API response."""
    return BatchJobResponse(
        batch_id=batch.batch_id,
        status=batch.status,
        created_at=batch.created_at,
        started_at=batch.started_at,
        completed_at=batch.completed_at,
        priority=batch.priority,
        fail_fast=batch.fail_fast,
        parallel_jobs=batch.parallel_jobs,
        progress=BatchProgress(
            total_jobs=batch.total_jobs,
            pending_jobs=batch.pending_jobs,
            running_jobs=batch.running_jobs,
            completed_jobs=batch.completed_jobs,
            failed_jobs=batch.failed_jobs,
            cancelled_jobs=batch.cancelled_jobs,
            progress_percent=batch.progress_percent,
        ),
        cost=BatchCostSummary(
            estimated_cost_usd=batch.estimated_cost_usd,
            actual_cost_usd=batch.actual_cost_usd,
            budget_cap_usd=batch.budget_cap_usd,
            budget_remaining_usd=(
                batch.budget_cap_usd - batch.actual_cost_usd
                if batch.budget_cap_usd else None
            ),
            tokens_used=batch.tokens_used,
        ),
        job_ids=batch.job_ids,
        error_message=batch.error_message,
        owner_id=batch.owner_id,
        metadata=batch.metadata,
    )


# ============================================================================
# Batch Endpoints
# ============================================================================

@router.post(
    "",
    response_model=BatchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create batch of simulations",
    description="Submit a batch of simulations to run. Returns immediately with batch ID.",
)
@limiter.limit("2/minute")  # Very expensive operation
async def create_batch(
    request: Request,
    body: BatchCreateRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Create a new batch of simulations.

    The batch runs asynchronously. Use GET /simulations/batch/{batch_id} to check status.
    """
    batch_size = len(body.simulations)

    # Enforce batch size limit for tier
    enforce_batch_size(user_id, batch_size)

    # Enforce simulation quota
    enforce_simulation_quota(user_id, batch_size)

    # Estimate cost and check budget
    # Rough estimate: $0.05 per simulation
    estimated_cost = batch_size * 0.05
    if body.budget_cap_usd and estimated_cost > body.budget_cap_usd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estimated cost ${estimated_cost:.2f} exceeds budget cap ${body.budget_cap_usd:.2f}",
        )

    enforce_cost_quota(user_id, estimated_cost)

    # Create batch
    runner = get_batch_runner()
    batch = runner.create_batch(body, user_id)

    # Record for quota tracking
    record_batch_start(user_id, batch.batch_id, batch_size)

    # Start batch execution
    started = runner.start_batch(batch.batch_id)
    if not started:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start batch",
        )

    return batch_to_response(batch)


@router.get(
    "",
    response_model=BatchListResponse,
    summary="List batches",
    description="List your batch jobs with optional status filtering.",
)
@limiter.limit("30/minute")
async def list_batch_jobs(
    request: Request,
    status_filter: Optional[BatchStatus] = None,
    page: int = 1,
    page_size: int = 20,
    user_id: str = Depends(get_current_user),
):
    """List batch jobs for the current user."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    offset = (page - 1) * page_size
    batches, total = list_batches(
        owner_id=user_id,
        status=status_filter,
        limit=page_size,
        offset=offset,
    )

    return BatchListResponse(
        batches=[batch_to_response(b) for b in batches],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stats",
    response_model=BatchStatsResponse,
    summary="Get batch statistics",
    description="Get statistics about your batches.",
)
@limiter.limit("30/minute")
async def get_batch_stats(
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Get batch statistics for the current user."""
    runner = get_batch_runner()
    stats = runner.get_stats(owner_id=user_id)

    return BatchStatsResponse(**stats)


# ============================================================================
# Usage Endpoints (must be before /{batch_id} to avoid route conflict)
# ============================================================================

@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Get usage status",
    description="Get current usage and quota status.",
    tags=["usage"],
)
@limiter.limit("60/minute")
async def get_usage_status(
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Get current usage and quota status."""
    quota_status = get_quota_status(user_id)

    return UsageResponse(
        user_id=quota_status.user_id,
        tier=quota_status.tier,
        period=quota_status.period,
        days_remaining=quota_status.days_remaining,
        api_calls_used=quota_status.api_calls_used,
        simulations_used=quota_status.simulations_used,
        cost_used_usd=quota_status.cost_used_usd,
        tokens_used=quota_status.tokens_used,
        api_calls_limit=quota_status.api_calls_limit,
        simulations_limit=quota_status.simulations_limit,
        cost_limit_usd=quota_status.cost_limit_usd,
        max_batch_size=quota_status.max_batch_size,
        api_calls_remaining=quota_status.api_calls_remaining,
        simulations_remaining=quota_status.simulations_remaining,
        cost_remaining_usd=quota_status.cost_remaining_usd,
        is_quota_exceeded=quota_status.is_quota_exceeded,
        quota_exceeded_reason=quota_status.exceeded_reason,
    )


@router.get(
    "/usage/history",
    response_model=UsageHistoryResponse,
    summary="Get usage history",
    description="Get usage history for past billing periods.",
    tags=["usage"],
)
@limiter.limit("30/minute")
async def get_usage_history(
    request: Request,
    periods: int = 6,
    user_id: str = Depends(get_current_user),
):
    """Get usage history."""
    db = get_usage_database()
    quota_status = get_quota_status(user_id)
    history = db.get_usage_history(user_id, limit=periods)

    # Convert to response format
    current_response = UsageResponse(
        user_id=quota_status.user_id,
        tier=quota_status.tier,
        period=quota_status.period,
        days_remaining=quota_status.days_remaining,
        api_calls_used=quota_status.api_calls_used,
        simulations_used=quota_status.simulations_used,
        cost_used_usd=quota_status.cost_used_usd,
        tokens_used=quota_status.tokens_used,
        api_calls_limit=quota_status.api_calls_limit,
        simulations_limit=quota_status.simulations_limit,
        cost_limit_usd=quota_status.cost_limit_usd,
        max_batch_size=quota_status.max_batch_size,
        api_calls_remaining=quota_status.api_calls_remaining,
        simulations_remaining=quota_status.simulations_remaining,
        cost_remaining_usd=quota_status.cost_remaining_usd,
        is_quota_exceeded=quota_status.is_quota_exceeded,
        quota_exceeded_reason=quota_status.exceeded_reason,
    )

    history_dicts = [
        {
            "period": h.period,
            "api_calls": h.api_calls,
            "simulations_run": h.simulations_run,
            "simulations_completed": h.simulations_completed,
            "simulations_failed": h.simulations_failed,
            "cost_usd": h.cost_usd,
            "tokens_used": h.tokens_used,
        }
        for h in history
        if h.period != quota_status.period  # Exclude current period
    ]

    return UsageHistoryResponse(
        current=current_response,
        history=history_dicts,
    )


# ============================================================================
# Batch Detail Endpoints
# ============================================================================

@router.get(
    "/{batch_id}",
    response_model=BatchJobResponse,
    summary="Get batch status",
    description="Get details about a specific batch.",
)
@limiter.limit("60/minute")
async def get_batch_status(
    request: Request,
    batch_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get a specific batch."""
    batch = get_batch(batch_id)

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch not found: {batch_id}",
        )

    # Check ownership
    if batch.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this batch",
        )

    return batch_to_response(batch)


@router.get(
    "/{batch_id}/jobs",
    response_model=BatchDetailResponse,
    summary="Get batch with jobs",
    description="Get batch details including all individual jobs.",
)
@limiter.limit("30/minute")
async def get_batch_with_jobs(
    request: Request,
    batch_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get batch with all job details."""
    batch = get_batch(batch_id)

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch not found: {batch_id}",
        )

    # Check ownership
    if batch.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this batch",
        )

    # Get individual jobs
    runner = get_batch_runner()
    jobs = runner.get_batch_jobs(batch_id)

    # Convert to response format
    from .simulations import job_to_response
    job_responses = [job_to_response(j) for j in jobs]

    return BatchDetailResponse(
        batch=batch_to_response(batch),
        jobs=job_responses,
    )


@router.post(
    "/{batch_id}/cancel",
    response_model=BatchJobResponse,
    summary="Cancel batch",
    description="Cancel a running or pending batch.",
)
@limiter.limit("10/minute")
async def cancel_batch(
    request: Request,
    batch_id: str,
    body: Optional[BatchCancelRequest] = None,
    user_id: str = Depends(get_current_user),
):
    """Cancel a batch job."""
    batch = get_batch(batch_id)

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch not found: {batch_id}",
        )

    # Check ownership
    if batch.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this batch",
        )

    # Check if cancellable
    if batch.status not in (BatchStatus.PENDING, BatchStatus.RUNNING, BatchStatus.PARTIAL):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel batch with status: {batch.status.value}",
        )

    runner = get_batch_runner()
    reason = body.reason if body else None
    cancel_running = body.cancel_running if body else True

    cancelled = runner.cancel_batch(batch_id, reason, cancel_running)

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel batch",
        )

    # Refresh batch
    batch = get_batch(batch_id)
    return batch_to_response(batch)


# Export router
batch_router = router
