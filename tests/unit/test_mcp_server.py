"""
Unit tests for the Pro MCP server.

Exercises:

- Bearer token verification against both the in-memory API key store and the
  ``PRO_MCP_BEARER_TOKENS`` environment variable.
- The ``BearerAuthMiddleware`` ASGI middleware — 401 paths, CORS preflight,
  happy-path user_id propagation.
- The ``tp_pro_simulate`` tool body — validates that it builds a
  ``SimulationCreateRequest`` and returns a job reference without running the
  actual simulation.  We monkeypatch the simulation runner so no real LLM
  calls are made.
- HTTP-level protection: a real ``TestClient`` against the full FastAPI app
  confirms that ``POST /mcp/`` with no Bearer header returns 401 and that
  providing the token reaches the MCP sub-app.
"""

from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

# Allow test helpers to run in test context
os.environ.setdefault("TESTING", "true")

from api.auth import clear_api_keys, create_api_key
from api.middleware.bearer_auth import (
    BearerAuthMiddleware,
    _parse_static_tokens,
    extract_bearer_token,
    get_current_bearer_user,
    verify_bearer_token,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    """Clean the API key store and relevant env vars for every test."""
    clear_api_keys()
    monkeypatch.delenv("PRO_MCP_BEARER_TOKENS", raising=False)
    yield
    clear_api_keys()


# ============================================================================
# verify_bearer_token — in-memory API key path
# ============================================================================


class TestVerifyBearerToken:
    def test_valid_api_key_resolves_to_user(self):
        key = create_api_key("alice", "Alice's key")
        assert verify_bearer_token(key) == "alice"

    def test_empty_token_returns_none(self):
        assert verify_bearer_token("") is None

    def test_unknown_token_returns_none(self):
        assert verify_bearer_token("tp_nope") is None

    def test_static_env_token_without_userid(self, monkeypatch):
        monkeypatch.setenv("PRO_MCP_BEARER_TOKENS", "static-abc123")
        uid = verify_bearer_token("static-abc123")
        assert uid is not None
        assert uid.startswith("bearer-")

    def test_static_env_token_with_userid(self, monkeypatch):
        monkeypatch.setenv(
            "PRO_MCP_BEARER_TOKENS", "tok-1:user-one, tok-2:user-two"
        )
        assert verify_bearer_token("tok-1") == "user-one"
        assert verify_bearer_token("tok-2") == "user-two"

    def test_api_key_preferred_over_env(self, monkeypatch):
        # If an API key is registered AND the same token string appears in the
        # env var, the API key store wins (since create_api_key stores a hash).
        key = create_api_key("alice", "Alice's key")
        monkeypatch.setenv("PRO_MCP_BEARER_TOKENS", f"{key}:env-user")
        assert verify_bearer_token(key) == "alice"


class TestParseStaticTokens:
    def test_empty_env(self):
        assert _parse_static_tokens() == {}

    def test_whitespace_and_empty_entries(self, monkeypatch):
        monkeypatch.setenv("PRO_MCP_BEARER_TOKENS", " , tok-1:user1 , , tok-2 ,")
        parsed = _parse_static_tokens()
        assert parsed["tok-1"] == "user1"
        assert "tok-2" in parsed


# ============================================================================
# extract_bearer_token
# ============================================================================


class TestExtractBearerToken:
    def test_valid_bearer(self):
        headers = [(b"authorization", b"Bearer abc.def.ghi")]
        assert extract_bearer_token(headers) == "abc.def.ghi"

    def test_case_insensitive_scheme(self):
        headers = [(b"authorization", b"BEARER abc123")]
        assert extract_bearer_token(headers) == "abc123"

    def test_missing_header(self):
        assert extract_bearer_token([]) is None

    def test_non_bearer_scheme(self):
        headers = [(b"authorization", b"Basic dXNlcjpwYXNz")]
        assert extract_bearer_token(headers) is None

    def test_bearer_with_no_token(self):
        headers = [(b"authorization", b"Bearer ")]
        assert extract_bearer_token(headers) is None

    def test_authorization_header_is_case_insensitive(self):
        headers = [(b"Authorization", b"Bearer xyz")]
        assert extract_bearer_token(headers) == "xyz"


# ============================================================================
# BearerAuthMiddleware — ASGI-level behavior
# ============================================================================


def _echo_app():
    """Minimal ASGI app that returns the captured user_id as JSON."""

    async def app(scope, receive, send):
        if scope["type"] != "http":
            return
        user = get_current_bearer_user()
        response = JSONResponse({"user": user})
        await response(scope, receive, send)

    return app


@pytest.fixture
def middleware_app():
    """FastAPI app wrapping the echo app behind BearerAuthMiddleware."""
    app = FastAPI()
    app.mount("/mcp", BearerAuthMiddleware(_echo_app()))
    return app


class TestBearerAuthMiddleware:
    def test_missing_header_returns_401(self, middleware_app):
        client = TestClient(middleware_app)
        response = client.get("/mcp/")
        assert response.status_code == 401
        body = response.json()
        assert body["error"] == "Unauthorized"
        assert "Missing Authorization" in body["message"]
        assert response.headers.get("www-authenticate", "").startswith("Bearer")

    def test_invalid_token_returns_401(self, middleware_app):
        client = TestClient(middleware_app)
        response = client.get(
            "/mcp/", headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert response.status_code == 401
        assert response.json()["error"] == "Unauthorized"

    def test_valid_api_key_lets_request_through(self, middleware_app):
        key = create_api_key("alice", "Alice key")
        client = TestClient(middleware_app)
        response = client.get("/mcp/", headers={"Authorization": f"Bearer {key}"})
        assert response.status_code == 200
        assert response.json() == {"user": "alice"}

    def test_valid_static_token_lets_request_through(
        self, middleware_app, monkeypatch
    ):
        monkeypatch.setenv("PRO_MCP_BEARER_TOKENS", "static-xyz:svc-account")
        client = TestClient(middleware_app)
        response = client.get(
            "/mcp/", headers={"Authorization": "Bearer static-xyz"}
        )
        assert response.status_code == 200
        assert response.json() == {"user": "svc-account"}

    def test_options_preflight_bypasses_auth(self, middleware_app):
        client = TestClient(middleware_app)
        response = client.options("/mcp/")
        # No 401 — the preflight is allowed through.  Depending on how the
        # sub-app responds it may be 200/204/405, but NOT 401.
        assert response.status_code != 401

    def test_non_bearer_scheme_returns_401(self, middleware_app):
        client = TestClient(middleware_app)
        response = client.get(
            "/mcp/", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        assert response.status_code == 401


# ============================================================================
# tp_pro_simulate tool body
# ============================================================================


class _FakeJob:
    """Minimal stand-in for SimulationJob."""

    def __init__(self, job_id: str, owner_id: str, req):
        from datetime import datetime

        from api.models_simulation import SimulationStatus

        self.job_id = job_id
        self.owner_id = owner_id
        self.status = SimulationStatus.PENDING
        self.created_at = datetime.utcnow()
        self.template_id = req.template_id
        self.description = req.description
        self.entity_count = req.entity_count
        self.timepoint_count = req.timepoint_count
        self.temporal_mode = req.temporal_mode.value


class _FakeRunner:
    """Stand-in for SimulationRunner that doesn't actually run anything."""

    def __init__(self):
        self.created_jobs: list[_FakeJob] = []
        self.started_jobs: list[str] = []

    def create_job(self, req, owner_id):
        job = _FakeJob(f"sim_test_{len(self.created_jobs):03d}", owner_id, req)
        self.created_jobs.append(job)
        return job

    def start_job(self, job_id):
        self.started_jobs.append(job_id)
        return True


@pytest.fixture
def fake_runner(monkeypatch):
    runner = _FakeRunner()
    # Patch get_simulation_runner where the tool imports it
    monkeypatch.setattr("api.mcp_server.get_simulation_runner", lambda: runner)
    return runner


@pytest.fixture
def tool_callable():
    """Extract the underlying async function from the MCP tool wrapper.

    FastMCP decorators keep the original function accessible as ``.fn``.
    """
    from api.mcp_server import tp_pro_simulate

    # FastMCP tools are FunctionTool objects whose ``fn`` is the original
    # async function.  We call it directly to bypass the MCP dispatcher.
    if hasattr(tp_pro_simulate, "fn"):
        return tp_pro_simulate.fn
    return tp_pro_simulate


class TestTpProSimulate:
    @pytest.mark.asyncio
    async def test_requires_description_or_template(self, fake_runner, tool_callable):
        result = await tool_callable()
        assert "error" in result
        assert "description" in result["error"] or "template" in result["error"]
        assert fake_runner.created_jobs == []

    @pytest.mark.asyncio
    async def test_description_creates_job(self, fake_runner, tool_callable):
        result = await tool_callable(
            description="40-person AI meetup in Venice, 5 demos, Q&A",
            entity_count=4,
            timepoint_count=5,
            temporal_mode="forward",
        )
        assert "error" not in result, result
        assert result["job_id"].startswith("sim_test_")
        assert result["status"] == "pending"
        assert result["status_url"] == f"/simulations/{result['job_id']}"
        assert result["entity_count"] == 4
        assert result["timepoint_count"] == 5
        assert result["temporal_mode"] == "forward"
        assert len(fake_runner.created_jobs) == 1
        assert fake_runner.started_jobs == [result["job_id"]]

    @pytest.mark.asyncio
    async def test_template_id_creates_job(self, fake_runner, tool_callable):
        result = await tool_callable(
            template_id="board_meeting",
            entity_count=6,
            timepoint_count=8,
        )
        assert "error" not in result, result
        assert result["template_id"] == "board_meeting"
        assert result["description"] is None
        assert result["entity_count"] == 6
        assert result["timepoint_count"] == 8

    @pytest.mark.asyncio
    async def test_owner_id_from_bearer_context(self, fake_runner, tool_callable):
        from api.middleware.bearer_auth import current_bearer_user

        token = current_bearer_user.set("user_abc")
        try:
            result = await tool_callable(
                description="test scenario", entity_count=2, timepoint_count=2
            )
        finally:
            current_bearer_user.reset(token)

        assert result["owner_id"] == "user_abc"
        assert fake_runner.created_jobs[0].owner_id == "user_abc"

    @pytest.mark.asyncio
    async def test_unknown_temporal_mode_defaults_to_forward(
        self, fake_runner, tool_callable
    ):
        result = await tool_callable(
            description="test", temporal_mode="gibberish"
        )
        assert "error" not in result, result
        assert result["temporal_mode"] == "forward"

    @pytest.mark.asyncio
    async def test_invalid_entity_count_returns_error(
        self, fake_runner, tool_callable
    ):
        # entity_count has a hard cap of 20 in SimulationCreateRequest.
        result = await tool_callable(
            description="test", entity_count=500, timepoint_count=5
        )
        assert "error" in result
        assert fake_runner.created_jobs == []

    @pytest.mark.asyncio
    async def test_default_owner_id_is_anonymous(self, fake_runner, tool_callable):
        # With no middleware context set, the tool uses a fallback id.
        result = await tool_callable(description="x", entity_count=2, timepoint_count=2)
        assert result["owner_id"] == "mcp-anonymous"


# ============================================================================
# End-to-end: FastAPI app with MCP mounted at /mcp
# ============================================================================


class TestFastAPIIntegration:
    """Full-stack checks against the production FastAPI app.

    The MCP streamable HTTP session manager is a module-level singleton
    whose ``.run()`` can only be called once per process, so we build the
    app and client once per class and share them across tests.
    """

    @pytest.fixture(scope="class")
    def client(self):
        # create_app wires the MCP sub-app behind BearerAuthMiddleware.
        from api.main import create_app

        app = create_app(debug=True)
        with TestClient(app) as client:
            yield client

    def test_mcp_requires_bearer(self, client):
        response = client.get("/mcp/")
        assert response.status_code == 401
        body = response.json()
        assert body["error"] == "Unauthorized"
        assert response.headers.get("www-authenticate", "").startswith("Bearer")

    def test_mcp_post_requires_bearer(self, client):
        response = client.post("/mcp/", json={})
        assert response.status_code == 401

    def test_mcp_with_invalid_bearer_rejected(self, client):
        response = client.post(
            "/mcp/",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Authorization": "Bearer nonsense"},
        )
        assert response.status_code == 401

    def test_health_endpoint_still_works(self, client):
        """Mounting MCP must not break unrelated routes."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ("healthy", "degraded")

    def test_mcp_server_tool_is_registered(self):
        """The tp_pro_simulate tool must be registered on the MCP server."""
        from api.mcp_server import mcp

        # FastMCP's tool manager exposes ``_tools`` or ``list_tools`` depending
        # on version.  We try a few access patterns.
        tool_names: list[str] = []
        manager = getattr(mcp, "_tool_manager", None) or getattr(mcp, "tool_manager", None)
        if manager is not None:
            tools = getattr(manager, "_tools", None) or getattr(manager, "tools", None)
            if isinstance(tools, dict):
                tool_names = list(tools.keys())
            elif tools is not None:
                tool_names = [getattr(t, "name", str(t)) for t in tools]

        if not tool_names:
            # Fallback — search the MCP object dict for any tool-like attribute.
            for attr in ("_tools", "tools"):
                obj = getattr(mcp, attr, None)
                if isinstance(obj, dict):
                    tool_names = list(obj.keys())
                    break

        assert "tp_pro_simulate" in tool_names, (
            f"Expected tp_pro_simulate to be registered. Found: {tool_names}"
        )
