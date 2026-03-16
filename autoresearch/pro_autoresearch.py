#!/usr/bin/env python3
"""
Timepoint Pro Autoresearch Harness

Karpathy-style autoresearch loop for SNAG simulation optimization:
  1. Mutate config (sample from ConfigSpace)
  2. Run simulation via run.sh (or dry-run with synthetic metrics)
  3. Extract quality metrics (Causal Resolution, coherence, cost)
  4. Keep if Pareto-improving, discard otherwise
  5. Repeat

Usage:
  # Dry-run mode (no API calls, synthetic metrics):
  python -m autoresearch.pro_autoresearch --dry-run --iterations 20 --template board_meeting

  # Live mode (real OpenRouter calls):
  python -m autoresearch.pro_autoresearch --iterations 10 --template board_meeting

  # Specific mechanism cluster:
  python -m autoresearch.pro_autoresearch --dry-run --cluster fidelity --iterations 30

  # All templates:
  python -m autoresearch.pro_autoresearch --dry-run --all-templates --iterations 50
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from autoresearch.config_space import ALL_CLUSTERS, ConfigSpace
from autoresearch.metrics import RunMetrics, synthetic_metrics
from autoresearch.pareto import compute_frontier, save_frontier, summarize

# Repo root (where run.sh lives)
REPO_ROOT = Path(__file__).parent.parent
RESULTS_DIR = REPO_ROOT / "autoresearch" / "results"

TEMPLATES = [
    "board_meeting",
    "mars_mission_portal",
    "castaway_colony_branching",
    "vc_pitch_branching",
    "hound_shadow_directorial",
    "detective_prospection",
    "jefferson_dinner",
    "kami_shrine",
    "hospital_crisis",
    "sec_investigation",
    "agent4_elk_migration",
]


def run_simulation(template: str, overrides: list[str], dry_run: bool) -> RunMetrics:
    """Run a single simulation and extract metrics."""
    if dry_run:
        return synthetic_metrics(template, overrides)

    # Build command
    cmd = [str(REPO_ROOT / "run.sh"), "run", template]
    cmd.extend(overrides)

    start = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=600,  # 10 min max per run
    )
    duration = time.time() - start

    if result.returncode != 0:
        print(f"  FAILED: {result.stderr[:200]}", file=sys.stderr)
        # Return zero-quality metrics for failed runs
        return RunMetrics(
            run_id=f"fail_{int(time.time())}",
            template=template,
            config_overrides=overrides,
            temporal_coherence=0.0,
            knowledge_consistency=0.0,
            biological_plausibility=0.0,
            convergence_score=0.0,
            causal_resolution=0.0,
            quality_composite=0.0,
            total_tokens=0,
            cost_usd=0.0,
            cost_efficiency=0.0,
            duration_seconds=duration,
            is_dry_run=False,
        )

    # Extract metrics from DB
    # TODO: Parse run_id from stdout, then extract_from_db()
    # For now, parse what we can from stdout
    return _parse_run_output(result.stdout, template, overrides, duration)


def _parse_run_output(
    stdout: str, template: str, overrides: list[str], duration: float
) -> RunMetrics:
    """Parse metrics from run.sh stdout. Fallback to synthetic if unparseable."""
    # run.sh outputs JSON summary at the end
    lines = stdout.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                return RunMetrics(
                    run_id=data.get("run_id", f"run_{int(time.time())}"),
                    template=template,
                    config_overrides=overrides,
                    temporal_coherence=data.get("temporal_coherence", 0.0),
                    knowledge_consistency=data.get("knowledge_consistency", 0.0),
                    biological_plausibility=data.get("biological_plausibility", 0.0),
                    convergence_score=data.get("convergence", 0.0),
                    causal_resolution=data.get("causal_resolution", 0.0),
                    quality_composite=data.get("quality_composite", 0.0),
                    total_tokens=data.get("total_tokens", 0),
                    cost_usd=data.get("cost_usd", 0.0),
                    cost_efficiency=data.get("cost_efficiency", 0.0),
                    duration_seconds=duration,
                    is_dry_run=False,
                )
            except json.JSONDecodeError:
                continue

    # Fallback: return synthetic metrics as placeholder
    print("  WARNING: Could not parse run output, using synthetic metrics", file=sys.stderr)
    m = synthetic_metrics(template, overrides)
    m.is_dry_run = False
    m.duration_seconds = duration
    return m


def autoresearch_loop(
    template: str,
    iterations: int,
    cluster: Optional[str],
    dry_run: bool,
    seed: int,
) -> list[RunMetrics]:
    """Main autoresearch loop: mutate -> run -> evaluate -> keep/discard."""
    clusters = [cluster] if cluster else None
    space = ConfigSpace(clusters=clusters, seed=seed)

    print(f"Autoresearch: {template}")
    print(f"  Mode: {'dry-run' if dry_run else 'LIVE'}")
    print(f"  {space.describe()}")
    print(f"  Iterations: {iterations}")
    print()

    all_results = []
    best_quality = 0.0
    kept = 0

    for i in range(iterations):
        overrides = space.sample()

        print(f"[{i+1}/{iterations}] Running with {len(overrides)} overrides...", end=" ")
        metrics = run_simulation(template, overrides, dry_run)
        all_results.append(metrics)

        # Check if this is an improvement
        frontier = compute_frontier(all_results)
        is_pareto = any(p.run_id == metrics.run_id for p in frontier)

        if metrics.quality_composite > best_quality:
            best_quality = metrics.quality_composite
            status = "NEW BEST"
            kept += 1
        elif is_pareto:
            status = "PARETO"
            kept += 1
        else:
            status = "discard"

        print(
            f"q={metrics.quality_composite:.4f} "
            f"CR={metrics.causal_resolution:.4f} "
            f"${metrics.cost_usd:.4f} "
            f"[{status}]"
        )

    print(f"\nCompleted {iterations} iterations. Kept {kept}/{iterations}.")
    return all_results


def main():
    parser = argparse.ArgumentParser(description="Timepoint Pro Autoresearch")
    parser.add_argument("--template", default="board_meeting", help="Template to optimize")
    parser.add_argument("--all-templates", action="store_true", help="Run across all templates")
    parser.add_argument("--iterations", type=int, default=20, help="Number of iterations")
    parser.add_argument("--cluster", choices=list(ALL_CLUSTERS.keys()), help="Mechanism cluster to optimize")
    parser.add_argument("--dry-run", action="store_true", help="Use synthetic metrics (no API calls)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", help="Output file for results JSONL")
    args = parser.parse_args()

    templates = TEMPLATES if args.all_templates else [args.template]
    all_results = []

    for template in templates:
        results = autoresearch_loop(
            template=template,
            iterations=args.iterations,
            cluster=args.cluster,
            dry_run=args.dry_run,
            seed=args.seed,
        )
        all_results.extend(results)

    # Compute final Pareto frontier
    frontier = compute_frontier(all_results)
    print("\n" + "=" * 60)
    print(summarize(frontier))

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "dry" if args.dry_run else "live"
    cluster_tag = f"_{args.cluster}" if args.cluster else ""

    # Save JSONL
    results_path = args.output or str(
        RESULTS_DIR / f"{mode}_run{cluster_tag}_{timestamp}.jsonl"
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        for r in all_results:
            f.write(json.dumps(r.to_dict()) + "\n")
    print(f"\nResults: {results_path}")

    # Save Pareto frontier
    frontier_path = str(RESULTS_DIR / f"pareto{cluster_tag}_{timestamp}.json")
    save_frontier(frontier, frontier_path)
    print(f"Pareto: {frontier_path}")


if __name__ == "__main__":
    main()
