"""
Pydantic models for API request/response schemas.

Defines all data transfer objects for the tensor API.

Phase 6: Public API
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Tensor Models
# ============================================================================

class TensorValues(BaseModel):
    """Tensor dimension values."""
    context: List[float] = Field(
        ...,
        min_length=8,
        max_length=8,
        description="Context dimensions (8 values)"
    )
    biology: List[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Biology dimensions (4 values)"
    )
    behavior: List[float] = Field(
        ...,
        min_length=8,
        max_length=8,
        description="Behavior dimensions (8 values)"
    )

    @field_validator("context", "biology", "behavior", mode="before")
    @classmethod
    def validate_values(cls, v):
        """Validate values are in [0, 1] range."""
        if v is not None:
            for val in v:
                if not 0.0 <= val <= 1.0:
                    raise ValueError(f"Value {val} must be between 0.0 and 1.0")
        return v


class TensorCreate(BaseModel):
    """Request model for creating a tensor."""
    tensor_id: Optional[str] = Field(
        None,
        description="Optional tensor ID (generated if not provided)"
    )
    entity_id: str = Field(
        ...,
        description="Entity this tensor belongs to"
    )
    world_id: Optional[str] = Field(
        None,
        description="World/simulation context"
    )
    values: TensorValues = Field(
        ...,
        description="Tensor dimension values"
    )
    description: Optional[str] = Field(
        None,
        description="Natural language description for RAG"
    )
    category: Optional[str] = Field(
        None,
        description="Category path (e.g., 'profession/detective')"
    )
    maturity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Maturity score (0.0-1.0)"
    )
    training_cycles: int = Field(
        default=0,
        ge=0,
        description="Number of training cycles"
    )
    access_level: str = Field(
        default="private",
        description="Access level: 'private', 'shared', or 'public'"
    )

    @field_validator("access_level")
    @classmethod
    def validate_access_level(cls, v):
        """Validate access level."""
        if v not in ("private", "shared", "public"):
            raise ValueError("access_level must be 'private', 'shared', or 'public'")
        return v


class TensorUpdate(BaseModel):
    """Request model for updating a tensor."""
    entity_id: Optional[str] = Field(
        None,
        description="Updated entity ID"
    )
    world_id: Optional[str] = Field(
        None,
        description="Updated world ID"
    )
    values: Optional[TensorValues] = Field(
        None,
        description="Updated tensor values"
    )
    description: Optional[str] = Field(
        None,
        description="Updated description"
    )
    category: Optional[str] = Field(
        None,
        description="Updated category"
    )
    maturity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Updated maturity"
    )
    training_cycles: Optional[int] = Field(
        None,
        ge=0,
        description="Updated training cycles"
    )
    access_level: Optional[str] = Field(
        None,
        description="Updated access level"
    )

    @field_validator("access_level")
    @classmethod
    def validate_access_level(cls, v):
        """Validate access level if provided."""
        if v is not None and v not in ("private", "shared", "public"):
            raise ValueError("access_level must be 'private', 'shared', or 'public'")
        return v


class TensorResponse(BaseModel):
    """Response model for a single tensor."""
    tensor_id: str = Field(..., description="Tensor identifier")
    entity_id: str = Field(..., description="Entity identifier")
    world_id: Optional[str] = Field(None, description="World identifier")
    values: TensorValues = Field(..., description="Tensor dimension values")
    maturity: float = Field(..., description="Maturity score")
    training_cycles: int = Field(..., description="Training cycle count")
    version: int = Field(..., description="Version number")
    description: Optional[str] = Field(None, description="Description")
    category: Optional[str] = Field(None, description="Category path")
    access_level: str = Field(..., description="Access level")
    owner_id: str = Field(..., description="Owner user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class TensorListResponse(BaseModel):
    """Response model for tensor list."""
    tensors: List[TensorResponse] = Field(
        ...,
        description="List of tensors"
    )
    total: int = Field(..., description="Total count")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=50, description="Page size")


# ============================================================================
# Search Models
# ============================================================================

class SearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language search query"
    )
    n_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results"
    )
    min_maturity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum maturity threshold"
    )
    categories: Optional[List[str]] = Field(
        None,
        description="Filter by categories"
    )
    include_values: bool = Field(
        default=False,
        description="Include tensor values in response"
    )


class SearchResultItem(BaseModel):
    """Single search result item."""
    tensor_id: str = Field(..., description="Tensor identifier")
    score: float = Field(..., description="Similarity score (0-1)")
    entity_id: str = Field(..., description="Entity identifier")
    description: Optional[str] = Field(None, description="Description")
    category: Optional[str] = Field(None, description="Category")
    maturity: float = Field(..., description="Maturity score")
    values: Optional[TensorValues] = Field(
        None,
        description="Tensor values (if include_values=True)"
    )


class SearchResponse(BaseModel):
    """Response model for search results."""
    results: List[SearchResultItem] = Field(
        ...,
        description="Search results"
    )
    query: str = Field(..., description="Original query")
    total: int = Field(..., description="Number of results returned")


# ============================================================================
# Composition Models
# ============================================================================

class ComposeRequest(BaseModel):
    """Request model for tensor composition."""
    tensor_ids: List[str] = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Tensor IDs to compose"
    )
    weights: Optional[List[float]] = Field(
        None,
        description="Optional weights for composition"
    )
    method: str = Field(
        default="weighted_blend",
        description="Composition method: 'weighted_blend', 'max_pool', 'hierarchical'"
    )

    @field_validator("method")
    @classmethod
    def validate_method(cls, v):
        """Validate composition method."""
        valid_methods = ("weighted_blend", "max_pool", "hierarchical")
        if v not in valid_methods:
            raise ValueError(f"method must be one of {valid_methods}")
        return v


class ComposeResponse(BaseModel):
    """Response model for composed tensor."""
    values: TensorValues = Field(..., description="Composed tensor values")
    source_tensors: List[str] = Field(..., description="Source tensor IDs")
    method: str = Field(..., description="Composition method used")


# ============================================================================
# Permission Models
# ============================================================================

class ShareRequest(BaseModel):
    """Request to share a tensor with a user."""
    user_id: str = Field(..., description="User ID to share with")


class AccessLevelRequest(BaseModel):
    """Request to change tensor access level."""
    access_level: str = Field(
        ...,
        description="New access level: 'private', 'shared', or 'public'"
    )

    @field_validator("access_level")
    @classmethod
    def validate_access_level(cls, v):
        """Validate access level."""
        if v not in ("private", "shared", "public"):
            raise ValueError("access_level must be 'private', 'shared', or 'public'")
        return v


# ============================================================================
# System Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Response timestamp")
    database: str = Field(..., description="Database status")
    tensor_count: int = Field(..., description="Total tensor count")
    rate_limiting: bool = Field(default=True, description="Rate limiting enabled")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for debugging"
    )


class StatsResponse(BaseModel):
    """Database statistics response."""
    total_tensors: int = Field(..., description="Total tensor count")
    operational_count: int = Field(..., description="Tensors with maturity >= 0.95")
    training_count: int = Field(..., description="Tensors with maturity < 0.95")
    avg_maturity: float = Field(..., description="Average maturity score")
    total_versions: int = Field(..., description="Total version entries")
