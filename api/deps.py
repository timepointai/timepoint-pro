"""
FastAPI dependency injection for the tensor API.

Provides database, permission, audit, and RAG dependencies.

Phase 6: Public API
"""

import os
from functools import lru_cache
from typing import Optional, Generator, TYPE_CHECKING

from tensor_persistence import TensorDatabase
from access.permissions import PermissionEnforcer
from access.audit import AuditLogger

if TYPE_CHECKING:
    from retrieval.tensor_rag import TensorRAG


# ============================================================================
# Configuration
# ============================================================================

class Settings:
    """API configuration settings."""

    def __init__(self):
        self.db_path: str = os.getenv(
            "TENSOR_DB_PATH",
            "metadata/tensors.db"
        )
        self.enable_rag: bool = os.getenv(
            "ENABLE_RAG",
            "true"
        ).lower() == "true"
        self.embedding_model: str = os.getenv(
            "EMBEDDING_MODEL",
            "all-MiniLM-L6-v2"
        )
        self.api_title: str = os.getenv(
            "API_TITLE",
            "Timepoint-Pro Tensor API"
        )
        self.api_version: str = os.getenv(
            "API_VERSION",
            "0.1.0"
        )
        self.debug: bool = os.getenv(
            "DEBUG",
            "false"
        ).lower() == "true"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# ============================================================================
# Singleton Instances
# ============================================================================

# Global instances (initialized on first access)
_tensor_db: Optional[TensorDatabase] = None
_enforcer: Optional[PermissionEnforcer] = None
_logger: Optional[AuditLogger] = None
_rag: Optional["TensorRAG"] = None


def _get_db_path() -> str:
    """Get database path from settings."""
    settings = get_settings()
    return settings.db_path


# ============================================================================
# Database Dependencies
# ============================================================================

def get_tensor_db() -> TensorDatabase:
    """
    Get TensorDatabase instance.

    Returns:
        TensorDatabase singleton
    """
    global _tensor_db
    if _tensor_db is None:
        _tensor_db = TensorDatabase(_get_db_path())
    return _tensor_db


def get_enforcer() -> PermissionEnforcer:
    """
    Get PermissionEnforcer instance.

    Returns:
        PermissionEnforcer singleton
    """
    global _enforcer
    if _enforcer is None:
        _enforcer = PermissionEnforcer(_get_db_path())
    return _enforcer


def get_audit_logger() -> AuditLogger:
    """
    Get AuditLogger instance.

    Returns:
        AuditLogger singleton
    """
    global _logger
    if _logger is None:
        _logger = AuditLogger(_get_db_path())
    return _logger


def get_tensor_rag() -> Optional["TensorRAG"]:
    """
    Get TensorRAG instance (lazy loaded).

    Returns:
        TensorRAG instance if enabled, None otherwise
    """
    global _rag
    settings = get_settings()

    if not settings.enable_rag:
        return None

    if _rag is None:
        try:
            from retrieval.tensor_rag import TensorRAG
            db = get_tensor_db()
            enforcer = get_enforcer()
            _rag = TensorRAG(
                tensor_db=db,
                embedding_model=settings.embedding_model,
                auto_build_index=True,
                permission_enforcer=enforcer,
            )
        except ImportError:
            # sentence-transformers not installed
            return None

    return _rag


# ============================================================================
# Cleanup
# ============================================================================

def cleanup_dependencies() -> None:
    """
    Clean up database connections and resources.

    Call this on shutdown.
    """
    global _tensor_db, _enforcer, _logger, _rag
    _tensor_db = None
    _enforcer = None
    _logger = None
    _rag = None


def reset_dependencies() -> None:
    """
    Reset all dependencies (for testing).

    This forces recreation of all singletons.
    """
    cleanup_dependencies()
    get_settings.cache_clear()


# ============================================================================
# Test Helpers
# ============================================================================

def override_db_path(path: str) -> None:
    """
    Override database path (for testing).

    Args:
        path: New database path
    """
    global _tensor_db, _enforcer, _logger, _rag
    # Clear existing instances
    _tensor_db = None
    _enforcer = None
    _logger = None
    _rag = None

    # Update settings
    settings = get_settings()
    settings.db_path = path


def create_test_dependencies(db_path: str) -> dict:
    """
    Create fresh dependencies for testing.

    Args:
        db_path: Path to test database

    Returns:
        Dict with db, enforcer, logger keys
    """
    db = TensorDatabase(db_path)
    enforcer = PermissionEnforcer(db_path)
    logger = AuditLogger(db_path)

    return {
        "db": db,
        "enforcer": enforcer,
        "logger": logger,
    }
