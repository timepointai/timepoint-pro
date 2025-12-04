"""
FastAPI application for the Timepoint-Daedalus Tensor API.

Provides RESTful access to tensor operations, semantic search,
and permission-controlled access.

Phase 6: Public API

Usage:
    uvicorn api.main:app --reload

    Or with custom settings:
    TENSOR_DB_PATH=./tensors.db uvicorn api.main:app
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .models import HealthResponse, ErrorResponse
from .routes import tensors_router, search_router, simulations_router
from .deps import (
    get_settings,
    get_tensor_db,
    cleanup_dependencies,
)
from .middleware.rate_limit import (
    get_limiter,
    rate_limit_exceeded_handler,
    get_rate_limit_config,
)


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
    print(f"Starting Tensor API v{settings.api_version}")
    print(f"Database: {settings.db_path}")
    print(f"RAG enabled: {settings.enable_rag}")
    print(f"Rate limiting: {'enabled' if rate_limit_config.enabled else 'disabled'}")

    # Initialize database
    try:
        db = get_tensor_db()
        stats = db.get_stats()
        print(f"Database initialized: {stats['total_tensors']} tensors")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")

    yield

    # Shutdown
    print("Shutting down Tensor API")
    cleanup_dependencies()


# ============================================================================
# Application Factory
# ============================================================================

def create_app(
    title: Optional[str] = None,
    version: Optional[str] = None,
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
Timepoint-Daedalus Tensor API

Provides access to cognitive tensors for character simulation.

## Features

- **Tensor CRUD**: Create, read, update, delete tensors
- **Semantic Search**: Natural language search over tensor descriptions
- **Permission Control**: Private, shared, and public access levels
- **Tensor Composition**: Combine multiple tensors

## Authentication

All endpoints require an API key in the `X-API-Key` header.
        """,
        lifespan=lifespan,
        debug=debug or settings.debug,
    )

    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
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
    application.include_router(tensors_router)
    application.include_router(search_router)
    application.include_router(simulations_router)

    # Add exception handlers
    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
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

    # Add root endpoints
    @application.get("/", include_in_schema=False)
    async def root():
        """Root endpoint redirect to docs."""
        return {
            "message": "Timepoint-Daedalus Tensor API",
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
