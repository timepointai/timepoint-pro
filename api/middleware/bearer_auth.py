"""
Bearer token authentication for the Pro MCP server.

The Pro MCP server at ``/mcp/`` accepts ``Authorization: Bearer <token>`` and
resolves the token to a user_id using two strategies:

1. **Existing ``tp_*`` API keys** — any API key created via
   :func:`api.auth.create_api_key` is also valid as a Bearer token.  This lets
   callers use the same key for ``X-API-Key`` REST calls and for the MCP
   transport.

2. **Static environment list** — ``PRO_MCP_BEARER_TOKENS`` env var, comma
   separated, each entry in the form ``<token>`` or ``<token>:<user_id>``.  The
   first form derives a stable ``bearer-<prefix>`` user_id from the token.

The ``BearerAuthMiddleware`` is an ASGI middleware that protects any sub-app
mounted underneath it.  It extracts the Bearer token from the incoming HTTP
request, resolves it to a user_id, stores the user_id in the module-level
:data:`current_bearer_user` contextvar (so MCP tools can read it), and returns
401 for missing/invalid tokens.  It intentionally exposes OPTIONS preflight and
``GET /`` probe requests without auth so MCP clients can complete the
Streamable HTTP handshake discovery.
"""

from __future__ import annotations

import os
from contextvars import ContextVar

from starlette.types import ASGIApp, Receive, Scope, Send

from ..auth import verify_api_key

# ============================================================================
# Context variable for tool access
# ============================================================================

# Set by BearerAuthMiddleware before dispatching to the MCP sub-app, read by
# MCP tools via :func:`get_current_bearer_user`.  Uses a ContextVar so
# concurrent async requests don't see each other's user_id.
current_bearer_user: ContextVar[str | None] = ContextVar(
    "current_bearer_user", default=None
)


def get_current_bearer_user() -> str | None:
    """Return the user_id of the Bearer token for the current request.

    Returns None if no Bearer token was validated (e.g. the request came
    through a different transport or the middleware wasn't applied).
    """
    return current_bearer_user.get()


# ============================================================================
# Bearer token verification
# ============================================================================


def _parse_static_tokens() -> dict[str, str]:
    """Parse the ``PRO_MCP_BEARER_TOKENS`` env var.

    Entries are comma-separated.  Each entry is either ``<token>`` (user_id is
    derived as ``bearer-<first-8-chars-of-token>``) or ``<token>:<user_id>``.

    Returns:
        Dict mapping token → user_id.  Empty dict if env var is unset.
    """
    raw = os.environ.get("PRO_MCP_BEARER_TOKENS", "")
    tokens: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            tok, uid = entry.split(":", 1)
            tok = tok.strip()
            uid = uid.strip()
        else:
            tok = entry
            uid = f"bearer-{tok[:8]}"
        if tok:
            tokens[tok] = uid
    return tokens


def verify_bearer_token(token: str) -> str | None:
    """Verify a Bearer token and return the associated user_id.

    Checked in order:

    1. In-memory API key store (same as ``X-API-Key`` auth).
    2. Static tokens from ``PRO_MCP_BEARER_TOKENS`` env var.

    Args:
        token: The raw token extracted from the ``Authorization`` header.

    Returns:
        ``user_id`` on success, ``None`` if the token is unknown or empty.
    """
    if not token:
        return None

    # 1. Existing API key store (tp_* keys)
    user_id = verify_api_key(token)
    if user_id is not None:
        return user_id

    # 2. Static env-configured tokens
    static = _parse_static_tokens()
    return static.get(token)


def extract_bearer_token(headers: list[tuple[bytes, bytes]]) -> str | None:
    """Extract a Bearer token from ASGI-style headers.

    Args:
        headers: The ``scope["headers"]`` list (raw bytes tuples).

    Returns:
        The token if present and well-formed, else None.
    """
    for name, value in headers:
        if name.lower() != b"authorization":
            continue
        try:
            decoded = value.decode("latin-1")
        except UnicodeDecodeError:
            return None
        parts = decoded.strip().split(None, 1)
        if len(parts) != 2:
            return None
        scheme, credential = parts
        if scheme.lower() != "bearer":
            return None
        credential = credential.strip()
        return credential or None
    return None


# ============================================================================
# ASGI middleware — protects the MCP sub-app
# ============================================================================


class BearerAuthMiddleware:
    """ASGI middleware that enforces ``Authorization: Bearer <token>``.

    Mounted in front of the MCP sub-app so unauthorized requests never reach
    the tool dispatcher.  Stores the resolved user_id in the
    :data:`current_bearer_user` contextvar for downstream tool handlers.

    The middleware allows unauthenticated ``OPTIONS`` (CORS preflight) through
    so browser-based MCP clients can complete CORS negotiation.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            # Lifespan / websocket / other: pass through.
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        token = extract_bearer_token(scope.get("headers") or [])
        if token is None:
            await _send_401(
                send,
                "Missing Authorization header. Pass 'Authorization: Bearer <tp_*>' to call the Pro MCP server.",
            )
            return

        user_id = verify_bearer_token(token)
        if user_id is None:
            await _send_401(send, "Invalid or unrecognized Bearer token.")
            return

        reset_token = current_bearer_user.set(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_bearer_user.reset(reset_token)


async def _send_401(send: Send, detail: str) -> None:
    """Emit a 401 response with a JSON error body."""
    import json

    body = json.dumps(
        {
            "error": "Unauthorized",
            "message": detail,
            "www_authenticate": 'Bearer realm="timepoint-pro-mcp"',
        }
    ).encode("utf-8")

    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin-1")),
                (b"www-authenticate", b'Bearer realm="timepoint-pro-mcp"'),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})
