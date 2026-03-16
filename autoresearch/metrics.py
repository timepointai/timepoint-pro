"""
Metric extraction for Pro autoresearch.

Extracts Causal Resolution (Coverage x Convergence) and other quality metrics
from Pro simulation runs, either from live run output or synthetic dry-run data.
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RunMetrics:
    """Metrics extracted from a single Pro simulation run."""

    run_id: str
    template: str
    config_overrides: list[str]

    # Core quality metrics (0-1)
    temporal_coherence: float
    knowledge_consistency: float
    biological_plausibility: float

    # Convergence (Jaccard similarity across repeated runs)
    convergence_score: float

    # Composite
    causal_resolution: float  # coverage * convergence
    quality_composite: float  # weighted average of all quality metrics

    # Cost
    total_tokens: int
    cost_usd: float
    cost_efficiency: float  # quality / cost

    # Meta
    duration_seconds: float
    is_dry_run: bool

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "template": self.template,
            "config_overrides": self.config_overrides,
            "temporal_coherence": self.temporal_coherence,
            "knowledge_consistency": self.knowledge_consistency,
            "biological_plausibility": self.biological_plausibility,
            "convergence_score": self.convergence_score,
            "causal_resolution": self.causal_resolution,
            "quality_composite": self.quality_composite,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "cost_efficiency": self.cost_efficiency,
            "duration_seconds": self.duration_seconds,
            "is_dry_run": self.is_dry_run,
        }


def extract_from_db(db_path: str, run_id: str) -> Optional[RunMetrics]:
    """Extract metrics from a completed run in metadata/runs.db."""
    db = Path(db_path)
    if not db.exists():
        return None

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None

        # Extract quality metrics from run metadata
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        quality = metadata.get("quality_metrics", {})

        return RunMetrics(
            run_id=run_id,
            template=row.get("template", "unknown"),
            config_overrides=json.loads(row.get("config_overrides", "[]")),
            temporal_coherence=quality.get("temporal_coherence", 0.0),
            knowledge_consistency=quality.get("knowledge_consistency", 0.0),
            biological_plausibility=quality.get("biological_plausibility", 0.0),
            convergence_score=quality.get("convergence", 0.0),
            causal_resolution=quality.get("temporal_coherence", 0.0) * quality.get("convergence", 0.0),
            quality_composite=_weighted_composite(quality),
            total_tokens=row.get("total_tokens", 0),
            cost_usd=row.get("cost_usd", 0.0),
            cost_efficiency=_safe_div(
                _weighted_composite(quality), row.get("cost_usd", 0.01)
            ),
            duration_seconds=row.get("duration_seconds", 0.0),
            is_dry_run=False,
        )
    finally:
        conn.close()


def synthetic_metrics(
    template: str,
    config_overrides: list[str],
    seed: int = 42,
) -> RunMetrics:
    """
    Generate deterministic synthetic metrics for dry-run mode.

    Uses a hash of the config to produce repeatable scores, with small
    seeded noise to simulate measurement variance. This lets the autoresearch
    loop test its mutation/selection logic without calling OpenRouter.
    """
    # Deterministic hash from config
    config_str = "|".join(sorted(config_overrides))
    h = hashlib.sha256(f"{template}:{config_str}".encode()).hexdigest()
    base = int(h[:8], 16) / 0xFFFFFFFF  # 0-1 float from hash

    rng = random.Random(int(h[:16], 16) ^ seed)
    noise = lambda: rng.gauss(0, 0.02)  # noqa: E731 — small noise

    # Generate plausible metrics that vary with config
    temporal = _clamp(0.6 + 0.3 * base + noise())
    knowledge = _clamp(0.7 + 0.2 * base + noise())
    biological = _clamp(0.65 + 0.25 * base + noise())
    convergence = _clamp(0.5 + 0.4 * base + noise())

    coverage = (temporal + knowledge + biological) / 3.0
    causal_res = coverage * convergence

    quality = (temporal * 0.3 + knowledge * 0.3 + biological * 0.2 + convergence * 0.2)

    # Cost model: higher max_tokens and bigger models cost more
    base_cost = 0.15
    for override in config_overrides:
        if "max_tokens=" in override:
            try:
                tokens = int(override.split("=")[1])
                base_cost *= tokens / 4000
            except ValueError:
                pass
        if "70b" in override:
            base_cost *= 1.5
        if "8b" in override:
            base_cost *= 0.3

    cost = max(0.01, base_cost + rng.gauss(0, 0.02))

    return RunMetrics(
        run_id=f"dry_{h[:12]}",
        template=template,
        config_overrides=config_overrides,
        temporal_coherence=temporal,
        knowledge_consistency=knowledge,
        biological_plausibility=biological,
        convergence_score=convergence,
        causal_resolution=causal_res,
        quality_composite=quality,
        total_tokens=int(4000 * base_cost / 0.15),
        cost_usd=round(cost, 4),
        cost_efficiency=round(_safe_div(quality, cost), 4),
        duration_seconds=round(rng.uniform(0.01, 0.1), 4),
        is_dry_run=True,
    )


def _weighted_composite(quality: dict) -> float:
    """Weighted average of quality metrics."""
    weights = {
        "temporal_coherence": 0.3,
        "knowledge_consistency": 0.3,
        "biological_plausibility": 0.2,
        "convergence": 0.2,
    }
    total = sum(quality.get(k, 0.0) * w for k, w in weights.items())
    return round(total, 4)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return round(max(lo, min(hi, v)), 4)


def _safe_div(a: float, b: float) -> float:
    return a / b if b > 0 else 0.0
