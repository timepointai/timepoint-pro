"""
Pareto frontier analysis for autoresearch optimization.

Identifies non-dominated configurations across quality vs cost tradeoffs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from autoresearch.metrics import RunMetrics


@dataclass
class ParetoPoint:
    """A point on the Pareto frontier."""

    run_id: str
    quality: float  # quality_composite
    cost: float  # cost_usd
    config_overrides: list[str]
    metrics: RunMetrics


def compute_frontier(results: list[RunMetrics]) -> list[ParetoPoint]:
    """
    Compute the Pareto frontier from a list of run results.

    A point is Pareto-optimal if no other point has both higher quality
    AND lower cost.
    """
    points = [
        ParetoPoint(
            run_id=r.run_id,
            quality=r.quality_composite,
            cost=r.cost_usd,
            config_overrides=r.config_overrides,
            metrics=r,
        )
        for r in results
    ]

    # Sort by cost ascending
    points.sort(key=lambda p: p.cost)

    frontier = []
    max_quality_seen = -1.0

    for p in points:
        if p.quality > max_quality_seen:
            frontier.append(p)
            max_quality_seen = p.quality

    return frontier


def save_frontier(frontier: list[ParetoPoint], path: str) -> None:
    """Save Pareto frontier as JSON."""
    data = {
        "frontier_size": len(frontier),
        "points": [
            {
                "run_id": p.run_id,
                "quality": p.quality,
                "cost": p.cost,
                "causal_resolution": p.metrics.causal_resolution,
                "config_overrides": p.config_overrides,
            }
            for p in frontier
        ],
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_frontier(path: str) -> list[dict]:
    """Load a previously saved Pareto frontier."""
    with open(path) as f:
        data = json.load(f)
    return data.get("points", [])


def summarize(frontier: list[ParetoPoint]) -> str:
    """Human-readable Pareto frontier summary."""
    if not frontier:
        return "No Pareto-optimal points found."

    lines = [f"Pareto frontier: {len(frontier)} optimal configs\n"]
    lines.append(f"{'Run ID':<16} {'Quality':>8} {'Cost':>8} {'CR':>8}")
    lines.append("-" * 44)
    for p in frontier:
        lines.append(
            f"{p.run_id:<16} {p.quality:>8.4f} ${p.cost:>7.4f} {p.metrics.causal_resolution:>8.4f}"
        )

    best_quality = max(frontier, key=lambda p: p.quality)
    best_efficiency = max(frontier, key=lambda p: p.metrics.cost_efficiency)
    lines.append(f"\nBest quality: {best_quality.run_id} (q={best_quality.quality:.4f})")
    lines.append(f"Best efficiency: {best_efficiency.run_id} (eff={best_efficiency.metrics.cost_efficiency:.4f})")

    return "\n".join(lines)
