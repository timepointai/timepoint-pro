"""
FastAPI application for the Timepoint-Pro Tensor API.

Provides RESTful access to tensor operations, semantic search,
and permission-controlled access.

Phase 6: Public API

Usage:
    uvicorn api.main:app --reload

    Or with custom settings:
    TENSOR_DB_PATH=./tensors.db uvicorn api.main:app
"""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi.errors import RateLimitExceeded

from .deps import (
    cleanup_dependencies,
    get_settings,
    get_tensor_db,
)
from .mcp_server import get_mcp_app, get_mcp_session_manager
from .middleware.bearer_auth import BearerAuthMiddleware
from .middleware.rate_limit import (
    get_limiter,
    get_rate_limit_config,
    rate_limit_exceeded_handler,
)
from .middleware.usage_quota import get_quota_config
from .models import ErrorResponse, HealthResponse
from .routes import batch_router, search_router, simulations_router, tensors_router
from .usage_storage import get_usage_database

# ============================================================================
# Lifespan Management
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    rate_limit_config = get_rate_limit_config()
    quota_config = get_quota_config()
    print(f"Starting Tensor API v{settings.api_version}")
    print(f"Database: {settings.db_path}")
    print(f"RAG enabled: {settings.enable_rag}")
    print(f"Rate limiting: {'enabled' if rate_limit_config.enabled else 'disabled'}")
    print(f"Usage quotas: {'enabled' if quota_config.enabled else 'disabled'}")

    # Initialize tensor database
    try:
        db = get_tensor_db()
        stats = db.get_stats()
        print(f"Tensor database initialized: {stats['total_tensors']} tensors")
    except Exception as e:
        print(f"Warning: Tensor database initialization failed: {e}")

    # Initialize usage database
    try:
        usage_db = get_usage_database()
        usage_stats = usage_db.get_stats()
        print(f"Usage database initialized: {usage_stats['active_users']} active users")
    except Exception as e:
        print(f"Warning: Usage database initialization failed: {e}")

    # Start MCP streamable HTTP session manager so the /mcp sub-app works.
    async with get_mcp_session_manager().run():
        print("MCP server session manager started (mounted at /mcp)")
        yield

    # Shutdown
    print("Shutting down Tensor API")
    cleanup_dependencies()


# ============================================================================
# Application Factory
# ============================================================================


def create_app(
    title: str | None = None,
    version: str | None = None,
    debug: bool = False,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        title: Custom API title
        version: Custom API version
        debug: Enable debug mode

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    application = FastAPI(
        title=title or settings.api_title,
        version=version or settings.api_version,
        description="""
Timepoint-Pro API

Provides access to cognitive tensors and simulation management.

## Features

- **Tensor CRUD**: Create, read, update, delete tensors
- **Semantic Search**: Natural language search over tensor descriptions
- **Permission Control**: Private, shared, and public access levels
- **Tensor Composition**: Combine multiple tensors
- **Simulation Jobs**: Create and manage simulation jobs
- **Batch Submission**: Submit multiple simulations in a single request
- **Usage Quotas**: Track and enforce monthly usage limits

## Authentication

All endpoints require an API key in the `X-API-Key` header.

## Rate Limiting

Rate limits are enforced per-tier (free, basic, pro, enterprise).
See /simulations/batch/usage for current usage.
        """,
        lifespan=lifespan,
        debug=debug or settings.debug,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Add CORS middleware
    cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # Set CORS_ORIGINS env var for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiter to app state
    limiter = get_limiter()
    application.state.limiter = limiter

    # Add rate limit exception handler
    application.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Include routers
    # NOTE: batch_router must come BEFORE simulations_router so that
    # /simulations/batch/* routes are matched before /simulations/{job_id}
    application.include_router(tensors_router)
    application.include_router(search_router)
    application.include_router(batch_router)
    application.include_router(simulations_router)

    # Add exception handlers
    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Handle dict detail (from usage quota middleware)
        if isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    **exc.detail,
                    "request_id": str(uuid.uuid4()),
                },
            )
        # Handle string detail (standard HTTPException)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.__class__.__name__,
                message=exc.detail,
                request_id=str(uuid.uuid4()),
            ).model_dump(),
        )

    @application.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="InternalServerError",
                message=str(exc) if settings.debug else "An internal error occurred",
                request_id=str(uuid.uuid4()),
            ).model_dump(),
        )

    # Auth-gated OpenAPI docs
    from .auth import get_current_user

    @application.get("/openapi.json", include_in_schema=False)
    async def openapi_schema(_user: str = Depends(get_current_user)):
        return JSONResponse(application.openapi())

    @application.get("/docs", include_in_schema=False, response_class=HTMLResponse)
    async def swagger_ui(_user: str = Depends(get_current_user)):
        return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{application.title} - Docs")

    @application.get("/redoc", include_in_schema=False, response_class=HTMLResponse)
    async def redoc_ui(_user: str = Depends(get_current_user)):
        return get_redoc_html(openapi_url="/openapi.json", title=f"{application.title} - ReDoc")

    # Add root endpoints
    @application.get("/", include_in_schema=False)
    async def root():
        """Root endpoint redirect to docs."""
        return {
            "message": "Timepoint-Pro Tensor API",
            "docs": "/docs",
            "health": "/health",
        }

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health_check():
        """
        Health check endpoint.

        Returns API status and basic statistics.
        """
        try:
            db = get_tensor_db()
            stats = db.get_stats()
            db_status = "healthy"
            tensor_count = stats["total_tensors"]
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
            tensor_count = 0

        rate_config = get_rate_limit_config()

        return HealthResponse(
            status="healthy" if db_status == "healthy" else "degraded",
            version=settings.api_version,
            timestamp=datetime.utcnow(),
            database=db_status,
            tensor_count=tensor_count,
            rate_limiting=rate_config.enabled,
        )

    # Mount the MCP (Model Context Protocol) server at /mcp behind the Bearer
    # auth middleware.  This exposes the ``tp_pro_simulate`` tool to
    # MCP-compatible agents.  The Bearer auth middleware rejects unauthorized
    # requests with 401 before they reach the MCP dispatcher.
    application.mount("/mcp", BearerAuthMiddleware(get_mcp_app()))

    return application


# ============================================================================
# Default Application Instance
# ============================================================================

app = create_app()


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
    )
