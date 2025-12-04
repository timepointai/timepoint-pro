"""
Simulation API routes.

Provides endpoints for creating, monitoring, and managing simulation jobs.

Phase 6: Public API - Simulation Endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..auth import get_current_user
from ..models_simulation import (
    SimulationCreateRequest,
    SimulationCancelRequest,
    SimulationJobResponse,
    SimulationResultResponse,
    SimulationListResponse,
    SimulationStatsResponse,
    SimulationStatus,
    TemplateInfo,
    TemplateListResponse,
)
from ..simulation_runner import (
    get_simulation_runner,
    get_job,
    list_jobs,
    SimulationJob,
)
from ..middleware.rate_limit import (
    get_limiter,
    limit_expensive,
    check_job_concurrency,
    increment_job_count,
    decrement_job_count,
    get_job_count,
)


router = APIRouter(prefix="/simulations", tags=["simulations"])
limiter = get_limiter()


# ============================================================================
# Helper Functions
# ============================================================================

def job_to_response(job: SimulationJob) -> SimulationJobResponse:
    """Convert internal job to API response."""
    return SimulationJobResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        template_id=job.template_id,
        description=job.description,
        entity_count=job.entity_count,
        timepoint_count=job.timepoint_count,
        temporal_mode=job.temporal_mode,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        run_id=job.run_id,
        entities_created=job.entities_created,
        timepoints_created=job.timepoints_created,
        cost_usd=job.cost_usd,
        tokens_used=job.tokens_used,
        error_message=job.error_message,
        owner_id=job.owner_id,
    )


# ============================================================================
# Job Management Endpoints
# ============================================================================

@router.post(
    "",
    response_model=SimulationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create simulation job",
    description="Create a new simulation job. The job is queued and runs in the background.",
)
@limiter.limit("5/minute")  # Expensive operation - strict limit
async def create_simulation(
    request: Request,
    body: SimulationCreateRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Create a new simulation job.

    The simulation runs asynchronously. Use GET /simulations/{job_id} to check status.
    """
    # Check job concurrency limit
    if not check_job_concurrency(user_id):
        current = get_job_count(user_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Job concurrency limit reached. You have {current} active jobs.",
        )

    runner = get_simulation_runner()

    # Create job
    job = runner.create_job(body, user_id)

    # Increment job count
    increment_job_count(user_id)

    # Start job in background
    started = runner.start_job(job.job_id)
    if not started:
        decrement_job_count(user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start simulation job",
        )

    return job_to_response(job)


@router.get(
    "",
    response_model=SimulationListResponse,
    summary="List simulation jobs",
    description="List your simulation jobs with optional status filtering.",
)
@limiter.limit("30/minute")
async def list_simulations(
    request: Request,
    status_filter: Optional[SimulationStatus] = None,
    page: int = 1,
    page_size: int = 20,
    user_id: str = Depends(get_current_user),
):
    """List simulation jobs for the current user."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    offset = (page - 1) * page_size
    jobs, total = list_jobs(
        owner_id=user_id,
        status=status_filter,
        limit=page_size,
        offset=offset,
    )

    return SimulationListResponse(
        jobs=[job_to_response(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stats",
    response_model=SimulationStatsResponse,
    summary="Get simulation statistics",
    description="Get statistics about your simulation jobs.",
)
@limiter.limit("30/minute")
async def get_simulation_stats(
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Get job statistics for the current user."""
    runner = get_simulation_runner()
    stats = runner.get_stats(owner_id=user_id)

    return SimulationStatsResponse(**stats)


@router.get(
    "/{job_id}",
    response_model=SimulationJobResponse,
    summary="Get simulation job",
    description="Get details about a specific simulation job.",
)
@limiter.limit("60/minute")
async def get_simulation(
    request: Request,
    job_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get a specific simulation job."""
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    # Check ownership
    if job.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    return job_to_response(job)


@router.get(
    "/{job_id}/result",
    response_model=SimulationResultResponse,
    summary="Get simulation results",
    description="Get detailed results for a completed simulation.",
)
@limiter.limit("30/minute")
async def get_simulation_result(
    request: Request,
    job_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get detailed results for a completed simulation."""
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    # Check ownership
    if job.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    # Check status
    if job.status != SimulationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed. Status: {job.status.value}",
        )

    # Load full results from metadata
    # In production, this would load from the database
    job_response = job_to_response(job)

    return SimulationResultResponse(
        job=job_response,
        entities=None,  # Would load from database
        timepoints=None,  # Would load from database
        relationships=None,
        summary=None,  # Would load from run metadata
        narrative_exports=None,
        convergence_score=None,
        robustness_grade=None,
    )


@router.post(
    "/{job_id}/cancel",
    response_model=SimulationJobResponse,
    summary="Cancel simulation",
    description="Cancel a running or pending simulation job.",
)
@limiter.limit("10/minute")
async def cancel_simulation(
    request: Request,
    job_id: str,
    body: Optional[SimulationCancelRequest] = None,
    user_id: str = Depends(get_current_user),
):
    """Cancel a simulation job."""
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    # Check ownership
    if job.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    # Check if cancellable
    if job.status not in (SimulationStatus.PENDING, SimulationStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status.value}",
        )

    runner = get_simulation_runner()
    reason = body.reason if body else None
    cancelled = runner.cancel_job(job_id, reason)

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job",
        )

    # Decrement job count
    decrement_job_count(user_id)

    # Refresh job
    job = get_job(job_id)
    return job_to_response(job)


# ============================================================================
# Template Endpoints
# ============================================================================

@router.get(
    "/templates",
    response_model=TemplateListResponse,
    summary="List available templates",
    description="List all available simulation templates.",
)
@limiter.limit("30/minute")
async def list_templates(
    request: Request,
    category: Optional[str] = None,
    tier: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    """List available simulation templates."""
    try:
        from generation.config_schema import TEMPLATE_REGISTRY
    except ImportError:
        # Fallback if registry not available
        TEMPLATE_REGISTRY = {}

    templates = []
    categories = set()

    for template_id, template_data in TEMPLATE_REGISTRY.items():
        # Extract template info
        cat = template_data.get("category", "core")
        template_tier = template_data.get("tier", "standard")
        categories.add(cat)

        # Apply filters
        if category and cat != category:
            continue
        if tier and template_tier != tier:
            continue

        templates.append(TemplateInfo(
            template_id=template_id,
            name=template_data.get("name", template_id),
            description=template_data.get("description", ""),
            category=cat,
            tier=template_tier,
            mechanisms=template_data.get("mechanisms", []),
            default_entity_count=template_data.get("entities", {}).get("count", 4),
            default_timepoint_count=template_data.get("timepoints", {}).get("count", 5),
            estimated_cost_usd=template_data.get("estimated_cost", 0.05),
            estimated_duration_seconds=template_data.get("estimated_duration", 120),
        ))

    return TemplateListResponse(
        templates=templates,
        total=len(templates),
        categories=sorted(categories),
    )


@router.get(
    "/templates/{template_id}",
    response_model=TemplateInfo,
    summary="Get template details",
    description="Get detailed information about a specific template.",
)
@limiter.limit("30/minute")
async def get_template(
    request: Request,
    template_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get details for a specific template."""
    try:
        from generation.config_schema import TEMPLATE_REGISTRY
    except ImportError:
        TEMPLATE_REGISTRY = {}

    template_data = TEMPLATE_REGISTRY.get(template_id)

    if not template_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )

    return TemplateInfo(
        template_id=template_id,
        name=template_data.get("name", template_id),
        description=template_data.get("description", ""),
        category=template_data.get("category", "core"),
        tier=template_data.get("tier", "standard"),
        mechanisms=template_data.get("mechanisms", []),
        default_entity_count=template_data.get("entities", {}).get("count", 4),
        default_timepoint_count=template_data.get("timepoints", {}).get("count", 5),
        estimated_cost_usd=template_data.get("estimated_cost", 0.05),
        estimated_duration_seconds=template_data.get("estimated_duration", 120),
    )


# Export router
simulations_router = router
