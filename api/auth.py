"""
API Key authentication for the tensor API.

Provides simple header-based API key authentication that maps
API keys to user IDs for permission enforcement.

Phase 6: Public API
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# ============================================================================
# Configuration
# ============================================================================

# Header name for API key
API_KEY_HEADER = "X-API-Key"

# In-memory API key store (for minimal implementation)
# In production, this would be stored in the database
_API_KEYS: dict[str, "APIKeyRecord"] = {}


@dataclass
class APIKeyRecord:
    """API key record."""

    api_key_hash: str
    user_id: str
    name: str
    created_at: datetime
    last_used: datetime | None = None
    is_active: bool = True
    rate_limit: int = 100


# ============================================================================
# API Key Security Scheme
# ============================================================================


class APIKeyAuth:
    """API Key authentication handler."""

    def __init__(self, auto_error: bool = True):
        """
        Initialize API key auth.

        Args:
            auto_error: If True, raise HTTPException on invalid key.
                       If False, return None on invalid key.
        """
        self.api_key_header = APIKeyHeader(
            name=API_KEY_HEADER, auto_error=auto_error, description="API key for authentication"
        )
        self.auto_error = auto_error

    async def __call__(
        self, api_key: str = Security(APIKeyHeader(name=API_KEY_HEADER, auto_error=False))
    ) -> str | None:
        """
        Validate API key and return user_id.

        Args:
            api_key: API key from header

        Returns:
            User ID if valid, None if auto_error=False and invalid

        Raises:
            HTTPException: If auto_error=True and key is invalid
        """
        if api_key is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing API key",
                    headers={"WWW-Authenticate": f"ApiKey header={API_KEY_HEADER}"},
                )
            return None

        user_id = verify_api_key(api_key)
        if user_id is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": f"ApiKey header={API_KEY_HEADER}"},
                )
            return None

        return user_id


# ============================================================================
# API Key Functions
# ============================================================================


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        api_key: Plain text API key

    Returns:
        SHA-256 hash of the key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """
    Generate a new API key.

    Returns:
        32-character random API key prefixed with 'tp_'
    """
    return f"tp_{secrets.token_hex(16)}"


def create_api_key(user_id: str, name: str = "default") -> str:
    """
    Create and register a new API key for a user.

    Args:
        user_id: User ID to associate with the key
        name: Friendly name for the key

    Returns:
        The plain text API key (only returned once)
    """
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    record = APIKeyRecord(
        api_key_hash=key_hash,
        user_id=user_id,
        name=name,
        created_at=datetime.utcnow(),
    )
    _API_KEYS[key_hash] = record

    return api_key


def verify_api_key(api_key: str) -> str | None:
    """
    Verify an API key and return the associated user_id.

    Args:
        api_key: API key to verify

    Returns:
        User ID if valid and active, None otherwise
    """
    key_hash = hash_api_key(api_key)
    record = _API_KEYS.get(key_hash)

    if record is None:
        return None

    if not record.is_active:
        return None

    # Update last used
    record.last_used = datetime.utcnow()

    return record.user_id


def get_api_key(api_key: str) -> APIKeyRecord | None:
    """
    Get API key record.

    Args:
        api_key: API key to look up

    Returns:
        APIKeyRecord if found, None otherwise
    """
    key_hash = hash_api_key(api_key)
    return _API_KEYS.get(key_hash)


def revoke_api_key(api_key: str) -> bool:
    """
    Revoke an API key.

    Args:
        api_key: API key to revoke

    Returns:
        True if revoked, False if not found
    """
    key_hash = hash_api_key(api_key)
    record = _API_KEYS.get(key_hash)

    if record is None:
        return False

    record.is_active = False
    return True


def list_user_api_keys(user_id: str) -> list:
    """
    List all API keys for a user.

    Args:
        user_id: User ID to list keys for

    Returns:
        List of APIKeyRecords (without exposing hashes)
    """
    return [
        {
            "name": record.name,
            "created_at": record.created_at,
            "last_used": record.last_used,
            "is_active": record.is_active,
        }
        for record in _API_KEYS.values()
        if record.user_id == user_id
    ]


# ============================================================================
# Test/Development Helpers
# ============================================================================


def setup_test_api_keys() -> dict[str, str]:
    """
    Set up test API keys for development/testing.

    Returns:
        Dict mapping user_id to API key
    """
    test_users = [
        ("test-user-alice", "Alice's key"),
        ("test-user-bob", "Bob's key"),
        ("test-user-admin", "Admin key"),
    ]

    keys = {}
    for user_id, name in test_users:
        key = create_api_key(user_id, name)
        keys[user_id] = key

    return keys


def clear_api_keys() -> None:
    """Clear all API keys (for testing)."""
    _API_KEYS.clear()


# ============================================================================
# Dependency for FastAPI
# ============================================================================

# Pre-configured auth instances
api_key_auth = APIKeyAuth(auto_error=True)
api_key_auth_optional = APIKeyAuth(auto_error=False)


async def get_current_user(
    api_key: str = Security(APIKeyHeader(name=API_KEY_HEADER, auto_error=True)),
) -> str:
    """
    FastAPI dependency to get current user from API key.

    Args:
        api_key: API key from header

    Returns:
        User ID

    Raises:
        HTTPException: If API key is missing or invalid
    """
    user_id = verify_api_key(api_key)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": f"ApiKey header={API_KEY_HEADER}"},
        )
    return user_id


async def get_optional_user(
    api_key: str = Security(APIKeyHeader(name=API_KEY_HEADER, auto_error=False)),
) -> str | None:
    """
    FastAPI dependency to optionally get current user.

    Returns None if no API key provided (for public endpoints).

    Args:
        api_key: API key from header (optional)

    Returns:
        User ID if valid key provided, None otherwise
    """
    if api_key is None:
        return None
    return verify_api_key(api_key)
