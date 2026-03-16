#!/usr/bin/env python3
"""
Autoresearch Runner — Run a simulation N times and compute convergence.

Used by the autoresearch-snag Claude command to evaluate config changes.

Usage:
    python autoresearch_runner.py [--runs 3] [--template board_meeting] [--timepoints 3]
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))


def run_single_simulation(template_id: str, num_timepoints: int, run_id: str):
    """Run a single simulation and return the run_id."""
    from omegaconf import OmegaConf
    from storage import GraphStore
    from llm_v2 import LLMClient
    from temporal_chain import build_temporal_chain

    cfg = OmegaConf.load("conf/config.yaml")

    store = GraphStore(cfg.database.url)
    llm_client = LLMClient.from_hydra_config(cfg, use_centralized_service=True)

    # Build temporal chain
    context = cfg.training.get("context", "founding_fathers_1789")
    timepoints = build_temporal_chain(context, num_timepoints)
    print(f"  [{run_id}] Built {len(timepoints)} timepoints")

    # Store timepoints with run_id so convergence can extract them
    from schemas import Timepoint as TimepointSchema

    for i, tp in enumerate(timepoints):
        tp_id = f"{run_id}_tp_{i:03d}"
        tp_obj = TimepointSchema(
            timepoint_id=tp_id,
            run_id=run_id,
            entities_present=tp.get("entities_present", []),
            causal_parent=f"{run_id}_tp_{i-1:03d}" if i > 0 else None,
        )
        store.add_timepoint(tp_obj)

    # Run training workflow for each timepoint
    from workflows import create_entity_training_workflow, WorkflowState

    for i, tp in enumerate(timepoints):
        try:
            entities = tp.get("entities", [])
            for entity in entities[:3]:  # Limit to 3 entities per timepoint for speed
                state = WorkflowState(
                    entity=entity,
                    timepoint=tp,
                    llm_client=llm_client,
                    store=store,
                    run_id=run_id,
                )
                workflow = create_entity_training_workflow()
                workflow.invoke(state)
        except Exception as e:
            print(f"  [{run_id}] Warning at tp {i}: {e}")
            continue

    print(f"  [{run_id}] Simulation complete")
    return run_id


def compute_convergence_score(run_ids: list[str], db_path: str = "timepoint.db"):
    """Compute convergence across runs."""
    from evaluation.convergence import extract_causal_graph, compute_convergence_from_graphs

    graphs = []
    for run_id in run_ids:
        try:
            graph = extract_causal_graph(run_id, db_path=db_path)
            if graph.edge_count > 0:
                graphs.append(graph)
            else:
                print(f"  Warning: run {run_id} produced 0 edges")
        except Exception as e:
            print(f"  Warning: failed to extract graph for {run_id}: {e}")

    if len(graphs) < 2:
        print("ERROR: Need at least 2 successful runs for convergence")
        return 0.0, "F"

    result = compute_convergence_from_graphs(graphs)
    return result.convergence_score, result.robustness_grade


def main():
    parser = argparse.ArgumentParser(description="Autoresearch runner")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs")
    parser.add_argument("--template", default="board_meeting", help="Template ID")
    parser.add_argument("--timepoints", type=int, default=3, help="Timepoints per run")
    args = parser.parse_args()

    print(f"=== Autoresearch Runner ===")
    print(f"Template: {args.template}")
    print(f"Runs: {args.runs}")
    print(f"Timepoints: {args.timepoints}")
    print()

    start = time.time()
    run_ids = []

    for i in range(args.runs):
        run_id = f"ar_{uuid.uuid4().hex[:8]}"
        print(f"Run {i+1}/{args.runs} ({run_id}):")
        try:
            completed_id = run_single_simulation(args.template, args.timepoints, run_id)
            run_ids.append(completed_id)
        except Exception as e:
            print(f"  FAILED: {e}")

    elapsed = time.time() - start
    cost_estimate = elapsed / 60 * 0.05  # rough: $0.05/min

    if len(run_ids) >= 2:
        score, grade = compute_convergence_score(run_ids)
        print()
        print(f"CONVERGENCE: {score:.4f}")
        print(f"GRADE: {grade}")
        print(f"COST: ${cost_estimate:.3f}")
        print(f"ELAPSED: {elapsed:.1f}s")
    else:
        print()
        print(f"CONVERGENCE: 0.0000")
        print(f"GRADE: F")
        print(f"COST: ${cost_estimate:.3f}")
        print(f"ELAPSED: {elapsed:.1f}s")
        print(f"ERROR: Only {len(run_ids)} successful runs (need >= 2)")


if __name__ == "__main__":
    main()
