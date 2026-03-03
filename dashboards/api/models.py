"""
Pydantic models for API request/response validation.
"""

from typing import Any

from pydantic import BaseModel, Field


class RunListItem(BaseModel):
    """Single run in list response."""

    run_id: str
    template_id: str
    started_at: str
    completed_at: str | None = None
    causal_mode: str
    entities_created: int = 0
    timepoints_created: int = 0
    cost_usd: float = 0.0
    status: str
    duration_seconds: float | None = None
    error_message: str | None = None
    mechanisms_used: dict[str, int] = Field(default_factory=dict)


class PaginatedRunsResponse(BaseModel):
    """Paginated response for run listing."""

    runs: list[RunListItem]
    total: int
    page: int
    limit: int
    pages: int


class RunDetails(BaseModel):
    """Full details for a single run."""

    run_id: str
    template_id: str
    started_at: str
    completed_at: str | None = None
    causal_mode: str
    max_entities: int | None = None
    max_timepoints: int | None = None
    entities_created: int = 0
    timepoints_created: int = 0
    training_examples: int = 0
    cost_usd: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0
    duration_seconds: float | None = None
    status: str
    error_message: str | None = None
    mechanism_usage: list[dict[str, Any]] = Field(default_factory=list)
    resolution_assignments: list[dict[str, Any]] = Field(default_factory=list)
    validations: list[dict[str, Any]] = Field(default_factory=list)
    schema_version: str | None = None
    fidelity_distribution: dict[str, Any] | None = None
    fidelity_strategy_json: dict[str, Any] | None = None
    token_budget_compliance: float | None = None


class MetaAnalytics(BaseModel):
    """Aggregate analytics across all runs."""

    total_runs: int
    total_cost: float
    avg_cost: float
    total_entities: int
    total_timepoints: int
    avg_duration: float | None = None
    completed_runs: int
    failed_runs: int
    success_rate: float
    top_templates: list[dict[str, Any]]
    cost_over_time: list[dict[str, Any]]
    mechanism_co_occurrence: list[dict[str, Any]]
    causal_mode_distribution: list[dict[str, Any]]


class TemplatesResponse(BaseModel):
    """List of all templates."""

    templates: list[str]


class MechanismsResponse(BaseModel):
    """Mechanism usage counts."""

    mechanisms: dict[str, int]
