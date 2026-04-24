"""
MCP (Model Context Protocol) server for Timepoint Pro.

Exposes Pro's simulation engine to MCP-compatible agents over the Streamable
HTTP transport.  Mounted from :mod:`api.main` at ``/mcp`` and protected by
:class:`api.middleware.bearer_auth.BearerAuthMiddleware`.

The server exposes exactly one tool — ``tp_pro_simulate`` — matching the spec
in API-6:

    "stand up Pro MCP server at pro.timepointai.com/mcp/ exposing
     tp_pro_simulate tool (Bearer auth)"

The tool is non-blocking: it creates a simulation job and returns immediately
with the job_id.  Callers poll the REST endpoint ``GET /simulations/{job_id}``
(same Bearer token, sent as ``X-API-Key``) to get progress and final results.
This matches the pattern described in Belle's memo — MCP clients with short
timeouts can't hold a connection open for a full simulation run (minutes), so
the tool returns a reference instead.

Config snippet for MCP clients::

    mcp_servers:
      timepoint-pro:
        url: https://pro.timepointai.com/mcp/
        headers:
          Authorization: "Bearer ${TIMEPOINT_API_KEY}"
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .middleware.bearer_auth import get_current_bearer_user
from .models_simulation import SimulationCreateRequest, TemporalModeAPI
from .simulation_runner import get_simulation_runner

logger = logging.getLogger("timepoint_pro.mcp")


# ----------------------------------------------------------------------------
# Server instance
# ----------------------------------------------------------------------------

# DNS rebinding protection is disabled because the MCP app is mounted as a
# sub-app behind FastAPI (which handles its own CORS) and Railway's reverse
# proxy validates hosts.  The default allowed_hosts list only includes
# localhost, which would reject production hosts like pro.timepointai.com.
_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP(
    name="TimepointPro",
    instructions=(
        "Timepoint Pro — temporal entity simulation engine. Use `tp_pro_simulate` "
        "to run a multi-entity, multi-timepoint simulation from a natural-language "
        "description or a named template. The tool returns a job_id; poll "
        "GET /simulations/{job_id} on pro.timepointai.com with the same Bearer "
        "token (as X-API-Key) to retrieve status and final results."
    ),
    host="0.0.0.0",
    stateless_http=True,
    streamable_http_path="/",
    transport_security=_transport_security,
)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _resolve_temporal_mode(raw: str | None) -> TemporalModeAPI:
    """Map a free-text temporal mode to the enum, defaulting to FORWARD.

    Accepts the enum values as well as common upper-case variants (``FORWARD``,
    ``DIRECTORIAL``, etc.) that appear in product copy.
    """
    if not raw:
        return TemporalModeAPI.FORWARD
    normalized = str(raw).strip().lower()
    for mode in TemporalModeAPI:
        if mode.value == normalized:
            return mode
    # Fall back to FORWARD rather than raising, so agents get a usable job
    # instead of an opaque MCP error for a typo.
    logger.warning("Unknown temporal_mode %r — defaulting to forward", raw)
    return TemporalModeAPI.FORWARD


def _current_user() -> str:
    """Return the Bearer-authenticated user_id for the current request.

    Falls back to a synthetic id if the middleware hasn't run — this should
    never happen in production (the middleware is always mounted in front of
    the MCP app) but keeps tests and local dev usable.
    """
    user = get_current_bearer_user()
    if user:
        return user
    return "mcp-anonymous"


# ----------------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------------


@mcp.tool()
async def tp_pro_simulate(
    description: str = "",
    template_id: str = "",
    entity_count: int = 4,
    timepoint_count: int = 5,
    temporal_mode: str = "forward",
    entity_types: list[str] | None = None,
    generate_summaries: bool = True,
    export_formats: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a Timepoint Pro simulation.

    Creates an asynchronous simulation job and returns its identifier.  Poll
    ``GET https://pro.timepointai.com/simulations/{job_id}`` with the same
    Bearer token (passed as ``X-API-Key``) to check status and fetch results.

    Provide **either** ``description`` (natural language) or ``template_id``
    (one of the named templates from ``GET /simulations/templates``).

    Args:
        description: Natural-language description of the scenario to simulate
            (e.g. "40-person AI meetup in Venice, 5 demos, Q&A").  Max 2000
            characters.  Required if ``template_id`` is empty.
        template_id: Registered template id (e.g. "board_meeting",
            "detective_interrogation", "grant_review_panel").  Required if
            ``description`` is empty.
        entity_count: Number of entities (personas) in the simulation. 1–20.
            Defaults to 4.
        timepoint_count: Number of temporal beats. 1–20. Defaults to 5.
        temporal_mode: One of "forward", "directorial", "cyclical",
            "branching", "portal".  Defaults to "forward".
        entity_types: Optional list of entity types (e.g. ["human",
            "organization"]).  Omitted → inferred from the scenario.
        generate_summaries: Whether to generate LLM-powered narrative
            summaries alongside the structured output.  Default True.
        export_formats: Export formats — any subset of ["json", "markdown",
            "pdf"].  Default ["json", "markdown"].
        metadata: Optional free-form metadata attached to the job.

    Returns:
        JSON-serializable dict with:
            - ``job_id``: str — pass to the status endpoint.
            - ``status``: str — "pending" on creation.
            - ``status_url``: str — ready-to-curl status endpoint.
            - ``owner_id``: str — the authenticated caller.
            - ``template_id`` / ``description`` — echoed config.
            - ``entity_count``, ``timepoint_count``, ``temporal_mode``.

        On validation failure, returns ``{"error": "<message>"}`` instead of
        raising, so agents see a structured error rather than an MCP protocol
        error.
    """
    # Validate mutually-required fields up front so the MCP client gets a
    # clean error instead of a pydantic validation dump.
    description = (description or "").strip()
    template_id = (template_id or "").strip()
    if not description and not template_id:
        return {
            "error": "Either 'description' or 'template_id' must be provided.",
        }

    # Build the pydantic request, mirroring the REST endpoint exactly so the
    # validation logic stays in one place.
    try:
        req = SimulationCreateRequest(
            description=description or None,
            template_id=template_id or None,
            entity_count=entity_count,
            entity_types=entity_types,
            timepoint_count=timepoint_count,
            temporal_mode=_resolve_temporal_mode(temporal_mode),
            generate_summaries=generate_summaries,
            export_formats=export_formats or ["json", "markdown"],
            metadata=metadata,
        )
    except (ValueError, TypeError) as exc:
        return {"error": f"Invalid simulation request: {exc}"}

    user_id = _current_user()

    runner = get_simulation_runner()
    job = runner.create_job(req, user_id)

    started = runner.start_job(job.job_id)
    if not started:
        return {
            "error": "Failed to start simulation job",
            "job_id": job.job_id,
        }

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "status_url": f"/simulations/{job.job_id}",
        "owner_id": job.owner_id,
        "template_id": job.template_id,
        "description": job.description,
        "entity_count": job.entity_count,
        "timepoint_count": job.timepoint_count,
        "temporal_mode": job.temporal_mode,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "note": (
            "Simulation runs asynchronously — poll "
            f"GET https://pro.timepointai.com/simulations/{job.job_id} "
            "(Authorization: Bearer <token> sent as X-API-Key) for progress."
        ),
    }


# ----------------------------------------------------------------------------
# Application wiring
# ----------------------------------------------------------------------------


def get_mcp_app():
    """Return the ASGI app for the MCP streamable HTTP transport.

    Mount this on the FastAPI app::

        app.mount("/mcp", BearerAuthMiddleware(get_mcp_app()))
    """
    return mcp.streamable_http_app()


def get_mcp_session_manager():
    """Return the MCP session manager for lifespan management.

    Call ``async with get_mcp_session_manager().run(): ...`` inside the
    FastAPI lifespan context so the streamable HTTP transport is started.
    """
    return mcp.session_manager
