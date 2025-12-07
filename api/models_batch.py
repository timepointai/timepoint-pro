"""
Pydantic models for Batch API request/response schemas.

Defines data transfer objects for batch simulation management.

Phase 6: Public API - Batch Submission
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from .models_simulation import (
    SimulationCreateRequest,
    SimulationJobResponse,
    SimulationStatus,
)


# ============================================================================
# Enums
# ============================================================================

class BatchStatus(str, Enum):
    """Batch job status."""
    PENDING = "pending"      # Not yet started
    RUNNING = "running"      # Jobs are executing
    PARTIAL = "partial"      # Some jobs complete, some still running
    COMPLETED = "completed"  # All jobs finished (success or failure)
    CANCELLED = "cancelled"  # Batch was cancelled
    FAILED = "failed"        # Batch-level failure (e.g., quota exceeded)


class BatchPriority(str, Enum):
    """Batch execution priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


# ============================================================================
# Request Models
# ============================================================================

class BatchCreateRequest(BaseModel):
    """Request model for creating a batch of simulations."""

    simulations: List[SimulationCreateRequest] = Field(
        ...,
        min_length=2,
        max_length=100,
        description="List of simulations to run (2-100)"
    )

    budget_cap_usd: Optional[float] = Field(
        None,
        ge=0.0,
        le=1000.0,
        description="Maximum total cost for this batch in USD"
    )

    priority: BatchPriority = Field(
        default=BatchPriority.NORMAL,
        description="Execution priority"
    )

    fail_fast: bool = Field(
        default=False,
        description="Stop batch on first job failure"
    )

    parallel_jobs: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Max concurrent jobs (defaults to tier limit)"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for the batch"
    )

    @field_validator("simulations")
    @classmethod
    def validate_simulations(cls, v):
        """Validate simulation list."""
        if len(v) < 2:
            raise ValueError("Batch must contain at least 2 simulations")
        if len(v) > 100:
            raise ValueError("Batch cannot exceed 100 simulations")
        return v


class BatchCancelRequest(BaseModel):
    """Request to cancel a batch."""

    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional reason for cancellation"
    )

    cancel_running: bool = Field(
        default=True,
        description="Also cancel currently running jobs"
    )


# ============================================================================
# Response Models
# ============================================================================

class BatchProgress(BaseModel):
    """Progress tracking for a batch."""

    total_jobs: int = Field(..., description="Total jobs in batch")
    pending_jobs: int = Field(..., description="Jobs not yet started")
    running_jobs: int = Field(..., description="Currently running jobs")
    completed_jobs: int = Field(..., description="Successfully completed")
    failed_jobs: int = Field(..., description="Failed jobs")
    cancelled_jobs: int = Field(..., description="Cancelled jobs")

    progress_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall progress percentage"
    )


class BatchCostSummary(BaseModel):
    """Cost tracking for a batch."""

    estimated_cost_usd: float = Field(..., description="Estimated total cost")
    actual_cost_usd: float = Field(..., description="Actual cost so far")
    budget_cap_usd: Optional[float] = Field(None, description="Budget cap if set")
    budget_remaining_usd: Optional[float] = Field(None, description="Remaining budget")
    tokens_used: int = Field(default=0, description="Total tokens used")


class BatchJobResponse(BaseModel):
    """Response model for a batch of simulations."""

    batch_id: str = Field(..., description="Unique batch identifier")
    status: BatchStatus = Field(..., description="Current batch status")
    created_at: datetime = Field(..., description="Batch creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Batch start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Batch completion timestamp")

    # Configuration
    priority: BatchPriority = Field(..., description="Execution priority")
    fail_fast: bool = Field(..., description="Fail-fast mode enabled")
    parallel_jobs: int = Field(..., description="Max concurrent jobs")

    # Progress
    progress: BatchProgress = Field(..., description="Batch progress")
    cost: BatchCostSummary = Field(..., description="Cost tracking")

    # Job references
    job_ids: List[str] = Field(..., description="IDs of all jobs in batch")

    # Error info
    error_message: Optional[str] = Field(None, description="Error if batch failed")

    # Owner info
    owner_id: str = Field(..., description="User who created the batch")

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Custom metadata")

    class Config:
        from_attributes = True


class BatchDetailResponse(BaseModel):
    """Detailed batch response including job list."""

    batch: BatchJobResponse = Field(..., description="Batch details")
    jobs: List[SimulationJobResponse] = Field(..., description="All jobs in batch")


class BatchListResponse(BaseModel):
    """Response model for listing batches."""

    batches: List[BatchJobResponse] = Field(..., description="List of batches")
    total: int = Field(..., description="Total batch count")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")


class BatchStatsResponse(BaseModel):
    """Statistics about batches."""

    total_batches: int = Field(..., description="Total batches created")
    pending_batches: int = Field(..., description="Pending batches")
    running_batches: int = Field(..., description="Currently running batches")
    completed_batches: int = Field(..., description="Completed batches")
    failed_batches: int = Field(..., description="Failed batches")

    total_jobs: int = Field(..., description="Total jobs across all batches")
    total_cost_usd: float = Field(..., description="Total cost")
    avg_jobs_per_batch: float = Field(..., description="Average jobs per batch")
    avg_duration_seconds: Optional[float] = Field(
        None,
        description="Average batch duration"
    )


# ============================================================================
# Usage/Quota Response Models
# ============================================================================

class UsageResponse(BaseModel):
    """Current usage status for a user."""

    user_id: str = Field(..., description="User ID")
    tier: str = Field(..., description="Current tier")
    period: str = Field(..., description="Billing period (YYYY-MM)")
    days_remaining: int = Field(..., description="Days remaining in period")

    # Current usage
    api_calls_used: int = Field(..., description="API calls this period")
    simulations_used: int = Field(..., description="Simulations this period")
    cost_used_usd: float = Field(..., description="Cost this period in USD")
    tokens_used: int = Field(..., description="Tokens used this period")

    # Limits
    api_calls_limit: int = Field(..., description="API call limit (-1=unlimited)")
    simulations_limit: int = Field(..., description="Simulation limit")
    cost_limit_usd: float = Field(..., description="Cost limit in USD")
    max_batch_size: int = Field(..., description="Max simulations per batch")

    # Remaining
    api_calls_remaining: int = Field(..., description="API calls remaining")
    simulations_remaining: int = Field(..., description="Simulations remaining")
    cost_remaining_usd: float = Field(..., description="Cost remaining in USD")

    # Status
    is_quota_exceeded: bool = Field(..., description="Whether quota is exceeded")
    quota_exceeded_reason: Optional[str] = Field(
        None,
        description="Reason if quota exceeded"
    )


class UsageHistoryResponse(BaseModel):
    """Usage history for a user."""

    current: UsageResponse = Field(..., description="Current period usage")
    history: List[Dict[str, Any]] = Field(..., description="Historical periods")
