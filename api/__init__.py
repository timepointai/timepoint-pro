"""
Public API for Timepoint-Pro tensor system.

Provides RESTful access to:
- Tensor CRUD operations
- Semantic search
- Permission-filtered access

Phase 6: Public API (Minimal Implementation)
"""

from .auth import (
    APIKeyAuth,
    get_api_key,
    verify_api_key,
)
from .main import app, create_app
from .models import (
    ErrorResponse,
    HealthResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    TensorCreate,
    TensorListResponse,
    TensorResponse,
    TensorUpdate,
)

__all__ = [
    # Application
    "app",
    "create_app",
    # Models
    "TensorCreate",
    "TensorUpdate",
    "TensorResponse",
    "TensorListResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
    "HealthResponse",
    "ErrorResponse",
    # Auth
    "APIKeyAuth",
    "get_api_key",
    "verify_api_key",
]

__version__ = "0.1.0"
