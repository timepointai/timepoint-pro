"""
FastAPI server for Timepoint Dashboard.

Provides REST API for querying runs, analytics, narratives, and screenplays.
"""

import json
import math

from db import TimepointDB
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from models import (
    MechanismsResponse,
    MetaAnalytics,
    PaginatedRunsResponse,
    RunDetails,
    RunListItem,
    TemplatesResponse,
)

# Initialize FastAPI app
app = FastAPI(
    title="Timepoint Dashboard API",
    description="REST API for querying Timepoint simulation runs",
    version="1.0.0",
)

# Enable CORS for API clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = TimepointDB()


@app.get("/", tags=["Health"])
async def root():
    """API health check."""
    return {"status": "ok", "message": "Timepoint Dashboard API"}


@app.get("/api/runs", response_model=PaginatedRunsResponse, tags=["Runs"])
async def list_runs(
    template: str | None = Query(None, description="Filter by template ID"),
    status: str | None = Query(None, description="Filter by status (completed, running, failed)"),
    date_from: str | None = Query(None, description="Filter by start date (ISO format)"),
    date_to: str | None = Query(None, description="Filter by end date (ISO format)"),
    min_cost: float | None = Query(None, description="Minimum cost filter"),
    max_cost: float | None = Query(None, description="Maximum cost filter"),
    causal_mode: str | None = Query(None, description="Filter by causal mode"),
    mechanisms: str | None = Query(
        None, description="Comma-separated list of mechanisms (e.g., 'M1,M5,M17')"
    ),
    min_entities: int | None = Query(None, description="Minimum entities created"),
    min_timepoints: int | None = Query(None, description="Minimum timepoints created"),
    sort_by: str = Query("started_at", description="Sort field"),
    order: str = Query("DESC", description="Sort order (ASC or DESC)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """
    List all runs with filtering, sorting, and pagination.

    Supports comprehensive filtering by template, status, date range,
    cost range, causal mode, mechanisms, and entity/timepoint counts.
    """
    # Parse mechanisms
    mechanism_list = mechanisms.split(",") if mechanisms else None

    # Query database
    results, total = db.query_runs(
        template=template,
        status=status,
        date_from=date_from,
        date_to=date_to,
        min_cost=min_cost,
        max_cost=max_cost,
        causal_mode=causal_mode,
        mechanisms=mechanism_list,
        min_entities=min_entities,
        min_timepoints=min_timepoints,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )

    # Calculate total pages
    pages = math.ceil(total / limit) if total > 0 else 0

    # Convert to Pydantic models
    runs = [RunListItem(**run) for run in results]

    return PaginatedRunsResponse(runs=runs, total=total, page=page, limit=limit, pages=pages)


@app.get("/api/run/{run_id}", response_model=RunDetails, tags=["Runs"])
async def get_run(run_id: str):
    """
    Get full details for a specific run.

    Includes mechanism usage, resolution assignments, and validations.
    """
    run = db.get_run_details(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return RunDetails(**run)


@app.get("/api/narrative/{run_id}", tags=["Content"])
async def get_narrative(run_id: str):
    """
    Get narrative JSON for a specific run.

    Includes characters, timepoints, dialogs, and executive summary.
    """
    narrative = db.get_narrative(run_id)

    if not narrative:
        raise HTTPException(status_code=404, detail=f"Narrative for run {run_id} not found")

    return narrative


@app.get("/api/screenplay/{run_id}", response_class=PlainTextResponse, tags=["Content"])
async def get_screenplay(run_id: str):
    """
    Get Fountain screenplay for a specific run.

    Returns raw Fountain format text.
    """
    screenplay = db.get_screenplay(run_id)

    if not screenplay:
        raise HTTPException(status_code=404, detail=f"Screenplay for run {run_id} not found")

    return screenplay


@app.get("/api/templates", response_model=TemplatesResponse, tags=["Metadata"])
async def list_templates():
    """
    Get list of all unique template IDs.

    Useful for populating filter dropdowns.
    """
    templates = db.get_templates()
    return TemplatesResponse(templates=templates)


@app.get("/api/mechanisms", response_model=MechanismsResponse, tags=["Metadata"])
async def list_mechanisms():
    """
    Get all mechanisms with total usage counts.

    Returns dict of {mechanism_name: usage_count}.
    """
    mechanisms = db.get_mechanisms()
    return MechanismsResponse(mechanisms=mechanisms)


@app.get("/api/meta-analytics", response_model=MetaAnalytics, tags=["Analytics"])
async def get_meta_analytics():
    """
    Get aggregate analytics across all runs.

    Includes:
    - Total runs, cost, entities, timepoints
    - Success rate
    - Top templates
    - Cost over time
    - Mechanism co-occurrence
    - Causal mode distribution
    """
    analytics = db.get_meta_analytics()
    return MetaAnalytics(**analytics)


@app.get("/api/dialogs/{run_id}", tags=["Content"])
async def get_dialogs(run_id: str):
    """
    Get all dialogs for a specific run.

    Extracts dialogs from narrative JSON if available.
    """
    narrative = db.get_narrative(run_id)

    if not narrative:
        raise HTTPException(status_code=404, detail=f"Narrative for run {run_id} not found")

    dialogs = narrative.get("dialogs", [])

    return {"run_id": run_id, "dialog_count": len(dialogs), "dialogs": dialogs}


@app.get("/api/convergence-stats", tags=["Analytics"])
async def get_convergence_stats():
    """
    Get aggregate convergence statistics across all convergence sets.

    Returns:
    - total_sets: Number of convergence sets analyzed
    - average_score: Mean convergence score (0.0-1.0)
    - min_score/max_score: Range of scores
    - grade_distribution: Count of A/B/C/D/F grades
    - template_coverage: Templates with convergence analysis
    """
    try:
        from storage import GraphStore

        store = GraphStore("sqlite:///metadata/runs.db")
        stats = store.get_convergence_stats()

        return stats
    except Exception as e:
        # Return empty stats on error
        return {
            "total_sets": 0,
            "average_score": 0.0,
            "grade_distribution": {},
            "template_coverage": {},
            "error": str(e),
        }


@app.get("/api/convergence-sets", tags=["Analytics"])
async def get_convergence_sets(
    template_id: str | None = Query(None, description="Filter by template ID"),
    min_score: float | None = Query(None, description="Minimum convergence score (0.0-1.0)"),
    limit: int = Query(50, ge=1, le=100, description="Max results to return"),
):
    """
    Get list of convergence sets with optional filtering.

    Returns list of convergence set objects with:
    - set_id, template_id, run_ids, run_count
    - convergence_score, robustness_grade
    - consensus_edge_count, contested_edge_count
    - created_at
    """
    try:
        from storage import GraphStore

        store = GraphStore("sqlite:///metadata/runs.db")
        sets = store.get_convergence_sets(template_id=template_id, min_score=min_score, limit=limit)

        # Convert to serializable format
        return [
            {
                "set_id": s.set_id,
                "template_id": s.template_id,
                "run_ids": s.run_ids,
                "run_count": s.run_count,
                "convergence_score": s.convergence_score,
                "min_similarity": s.min_similarity,
                "max_similarity": s.max_similarity,
                "robustness_grade": s.robustness_grade,
                "consensus_edge_count": s.consensus_edge_count,
                "contested_edge_count": s.contested_edge_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sets
        ]
    except Exception:
        return []


@app.get("/api/convergence-set/{set_id}", tags=["Analytics"])
async def get_convergence_set(set_id: str):
    """
    Get detailed information about a specific convergence set.

    Returns full convergence set with divergence points.
    """
    try:
        import json

        from storage import GraphStore

        store = GraphStore("sqlite:///metadata/runs.db")
        s = store.get_convergence_set(set_id)

        if not s:
            raise HTTPException(status_code=404, detail=f"Convergence set {set_id} not found")

        return {
            "set_id": s.set_id,
            "template_id": s.template_id,
            "run_ids": json.loads(s.run_ids) if isinstance(s.run_ids, str) else s.run_ids,
            "run_count": s.run_count,
            "convergence_score": s.convergence_score,
            "min_similarity": s.min_similarity,
            "max_similarity": s.max_similarity,
            "robustness_grade": s.robustness_grade,
            "consensus_edge_count": s.consensus_edge_count,
            "contested_edge_count": s.contested_edge_count,
            "divergence_points": json.loads(s.divergence_points)
            if isinstance(s.divergence_points, str)
            else s.divergence_points,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-export/{run_id}", tags=["Content"])
async def export_run_tdf(run_id: str):
    """Export a run's data as TDF JSONL."""
    from datetime import datetime, timezone

    from fastapi.responses import JSONResponse
    from timepoint_tdf import from_pro

    run_meta = db.get_run_details(run_id)
    if not run_meta:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    narrative = db.get_narrative(run_id) or {}

    run_data = {
        "run_id": run_id,
        "created_at": run_meta.get("started_at", datetime.now(timezone.utc).isoformat()),
        "entities": narrative.get("entities", narrative.get("characters", [])),
        "dialogs": narrative.get("dialogs", []),
        "causal_edges": narrative.get("causal_edges", []),
        "metadata": dict(run_meta),
    }

    record = from_pro(run_data)
    return JSONResponse(content=json.loads(record.model_dump_json()))


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Timepoint Dashboard API on http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
