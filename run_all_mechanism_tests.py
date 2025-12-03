#!/usr/bin/env python3
"""
Comprehensive Mechanism Coverage Test Suite with ANDOS
=======================================================
ONE COMMAND to:
- Run ALL 15 E2E test templates (11 pre-programmed + 4 ANDOS)
- Validate all 17 mechanisms
- Test all output formats (JSON, JSONL, markdown, ML dataset)
- Validate Oxen publishing integration
- Report comprehensive results

Rate Limiting:
- Includes automatic cooldown periods between tests (10-15s)
- Prevents OpenRouter API rate limit errors
- Safe for concurrent test execution

Usage:
    python run_all_mechanism_tests.py           # Run quick mode (safe templates)
    python run_all_mechanism_tests.py --full    # Run all templates (expensive!)
"""
import os
import sys
import subprocess
import argparse
import time
import json
import signal
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Colorful progress tracking
from progress_tracker import ProgressTracker, print_success, print_error, print_info


# ============================================================================
# Ctrl+C Double-Confirm Handler
# ============================================================================
class GracefulInterruptHandler:
    """
    Handles Ctrl+C with a double-confirm dialog to prevent accidental aborts.

    First Ctrl+C: Asks for confirmation
    Second Ctrl+C (within 3 seconds): Actually exits

    This prevents expensive test runs from being accidentally interrupted.
    """

    def __init__(self, timeout_seconds: float = 3.0):
        self.timeout = timeout_seconds
        self.first_interrupt_time = None
        self.confirmed = False
        self._lock = threading.Lock()
        self._original_handler = None
        self._enabled = True

    def enable(self):
        """Enable the double-confirm handler"""
        self._original_handler = signal.signal(signal.SIGINT, self._handler)
        self._enabled = True

    def disable(self):
        """Disable and restore original handler"""
        if self._original_handler is not None:
            signal.signal(signal.SIGINT, self._original_handler)
        self._enabled = False

    def _handler(self, signum, frame):
        """Handle SIGINT (Ctrl+C) with double-confirm"""
        if not self._enabled:
            # If disabled, use default behavior
            raise KeyboardInterrupt

        with self._lock:
            now = time.time()

            # Check if this is a second interrupt within timeout
            if self.first_interrupt_time is not None:
                elapsed = now - self.first_interrupt_time
                if elapsed < self.timeout:
                    # Second Ctrl+C within timeout - actually exit
                    print("\n\n" + "=" * 60)
                    print("🛑 CONFIRMED: Aborting test run...")
                    print("=" * 60)
                    sys.exit(130)  # Standard exit code for Ctrl+C

            # First interrupt - ask for confirmation
            self.first_interrupt_time = now

            print("\n")
            print("=" * 60)
            print("⚠️  INTERRUPT RECEIVED - Are you sure you want to quit?")
            print("=" * 60)
            print(f"   Press Ctrl+C again within {self.timeout:.0f} seconds to confirm")
            print("   Or wait to continue running...")
            print("=" * 60)
            print()

            # Start a thread to clear the interrupt state after timeout
            def clear_interrupt():
                time.sleep(self.timeout + 0.1)
                with self._lock:
                    if self.first_interrupt_time is not None:
                        elapsed = time.time() - self.first_interrupt_time
                        if elapsed >= self.timeout:
                            self.first_interrupt_time = None
                            print("   ✓ Interrupt cancelled - continuing test run...")
                            print()

            thread = threading.Thread(target=clear_interrupt, daemon=True)
            thread.start()


# Global interrupt handler instance
_interrupt_handler = GracefulInterruptHandler(timeout_seconds=3.0)


def enable_graceful_interrupt():
    """Enable the double-confirm Ctrl+C handler"""
    _interrupt_handler.enable()


def disable_graceful_interrupt():
    """Disable the double-confirm handler (for cleanup/input prompts)"""
    _interrupt_handler.disable()


# Auto-load .env file
def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

# Map OXEN_API_KEY from .env to OXEN_API_TOKEN (used by oxen_integration)
if os.getenv("OXEN_API_KEY") and not os.getenv("OXEN_API_TOKEN"):
    os.environ["OXEN_API_TOKEN"] = os.environ["OXEN_API_KEY"]


def run_convergence_analysis(
    run_count: int = 3,
    template_filter: Optional[str] = None,
    verbose: bool = False
) -> bool:
    """
    Run convergence analysis on recent runs from the database.

    Computes causal graph similarity across runs to measure mechanism robustness.
    High convergence (>0.8) indicates robust causal mechanisms.

    Args:
        run_count: Number of recent runs to compare
        template_filter: Optional template ID to filter runs
        verbose: Show detailed divergence point information

    Returns:
        True if analysis succeeded, False otherwise
    """
    from metadata.run_tracker import MetadataManager
    from storage import GraphStore
    from schemas import ConvergenceSet
    import uuid

    print("\n" + "=" * 80)
    print("CONVERGENCE ANALYSIS")
    print("=" * 80)
    if template_filter:
        print(f"Template filter: {template_filter}")
    print(f"Comparing causal graphs across {run_count} runs...")
    print()

    try:
        # Get recent runs
        metadata_manager = MetadataManager(db_path="metadata/runs.db")
        all_runs = metadata_manager.get_all_runs()

        # Filter by template if specified
        if template_filter:
            all_runs = [r for r in all_runs if hasattr(r, 'template_id') and r.template_id == template_filter]
            if not all_runs:
                print(f"  No runs found for template: {template_filter}")
                return False

        recent_runs = all_runs[-run_count:]

        if len(recent_runs) < 2:
            print(f"  Need at least 2 runs for convergence analysis, found {len(recent_runs)}")
            return False

        run_ids = [r.run_id for r in recent_runs]
        print(f"  Analyzing runs: {', '.join(run_ids[:3])}{'...' if len(run_ids) > 3 else ''}")

        # Import convergence module
        from evaluation.convergence import (
            CausalGraph,
            compute_convergence_from_graphs,
            graph_similarity,
        )

        # Build causal graphs from run data
        # Note: We create simplified graphs from stored metadata since full DB extraction
        # requires the simulation's DB file which may not be available
        graphs = []
        for run in recent_runs:
            # Create graph from run metadata
            graph = CausalGraph(
                run_id=run.run_id,
                template_id=run.template_id if hasattr(run, 'template_id') else None,
            )

            # Extract mechanisms as proxy for causal structure
            # In a full implementation, this would pull from Timepoint.causal_parent
            if run.mechanisms_used:
                # Create edges from mechanism co-occurrence
                mechanisms = list(run.mechanisms_used)
                for i, m1 in enumerate(mechanisms):
                    for m2 in mechanisms[i+1:]:
                        graph.temporal_edges.add((m1, m2))

            if run.entities_created and run.entities_created > 0:
                # Add entity count as metadata
                graph.metadata['entity_count'] = run.entities_created

            graphs.append(graph)

        if len(graphs) < 2:
            print(f"  Could not build enough graphs for analysis")
            return False

        # Compute convergence
        result = compute_convergence_from_graphs(graphs)

        # Display results
        print(f"\n  📊 Convergence Results:")
        print(f"  ├─ Score: {result.convergence_score:.2%}")
        print(f"  ├─ Grade: {result.robustness_grade}")
        print(f"  ├─ Min Similarity: {result.min_similarity:.2%}")
        print(f"  ├─ Max Similarity: {result.max_similarity:.2%}")
        print(f"  ├─ Consensus Edges: {len(result.consensus_edges)}")
        print(f"  └─ Contested Edges: {len(result.contested_edges)}")

        # Interpret grade
        grade_meanings = {
            "A": "Excellent - Causal mechanisms are highly robust",
            "B": "Good - Causal mechanisms are reasonably stable",
            "C": "Fair - Some variability in causal structure",
            "D": "Poor - Significant causal divergence",
            "F": "Fail - Causal mechanisms are highly sensitive to conditions"
        }
        print(f"\n  💡 {grade_meanings.get(result.robustness_grade, 'Unknown grade')}")

        # Show divergence points if any
        if result.divergence_points:
            print(f"\n  🔀 Divergence Points ({len(result.divergence_points)} total):")
            show_count = len(result.divergence_points) if verbose else min(3, len(result.divergence_points))
            for dp in result.divergence_points[:show_count]:
                print(f"     - {dp.edge}: {dp.agreement_ratio:.0%} agreement")
                if verbose:
                    print(f"       Present in: {', '.join(dp.present_in_runs)}")
                    print(f"       Absent in: {', '.join(dp.absent_in_runs)}")
            if not verbose and len(result.divergence_points) > 3:
                print(f"     ... and {len(result.divergence_points) - 3} more (use --convergence-verbose for details)")

        # Store result in database
        store = GraphStore("sqlite:///metadata/runs.db")
        convergence_set = ConvergenceSet(
            set_id=f"conv_{uuid.uuid4().hex[:8]}",
            template_id=result.template_id,
            run_ids=json.dumps(result.run_ids),
            run_count=result.run_count,
            convergence_score=result.convergence_score,
            min_similarity=result.min_similarity,
            max_similarity=result.max_similarity,
            robustness_grade=result.robustness_grade,
            consensus_edge_count=len(result.consensus_edges),
            contested_edge_count=len(result.contested_edges),
            divergence_points=json.dumps([
                {"edge": dp.edge, "ratio": dp.agreement_ratio}
                for dp in result.divergence_points[:10]
            ])
        )
        store.save_convergence_set(convergence_set)
        print(f"\n  ✅ Results saved: {convergence_set.set_id}")

        return True

    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        print(f"     Make sure evaluation/ module is available")
        return False
    except Exception as e:
        print(f"  ❌ Error during convergence analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_convergence_e2e(
    template_name: str,
    run_count: int = 3,
    skip_summaries: bool = False,
    verbose: bool = False,
    model_override: Optional[str] = None
) -> bool:
    """
    Run a template N times consecutively, then compute convergence across those runs.

    This is the full E2E convergence test that:
    1. Runs the same template run_count times
    2. Computes convergence (Jaccard similarity) across the runs
    3. Displays side-by-side comparison of mechanisms and divergence points
    4. Saves the convergence set to the database

    Args:
        template_name: Name of the template to run (e.g., "board_meeting")
        run_count: Number of times to run the template (default: 3)
        skip_summaries: Whether to skip LLM-powered summaries
        verbose: Show detailed divergence point information
        model_override: Override the default LLM model (e.g., "meta-llama/llama-3.1-405b-instruct")

    Returns:
        True if all runs succeeded and convergence was computed, False otherwise

    Example:
        python run_all_mechanism_tests.py --convergence-e2e --template board_meeting --runs 3 --model meta-llama/llama-3.1-405b-instruct
    """
    from generation.config_schema import SimulationConfig
    from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
    from metadata.run_tracker import MetadataManager
    from evaluation.convergence import CausalGraph, compute_convergence_from_graphs, extract_causal_graph
    from storage import GraphStore
    from schemas import ConvergenceSet
    import uuid

    print("\n" + "=" * 80)
    print("CONVERGENCE E2E TEST")
    print("=" * 80)
    print(f"Template: {template_name}")
    print(f"Runs: {run_count}")
    if model_override:
        print(f"Model Override: {model_override}")
        # Set environment variable for downstream LLM client initialization
        os.environ["TIMEPOINT_MODEL_OVERRIDE"] = model_override
    else:
        print(f"Model: default (meta-llama/llama-3.1-70b-instruct)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Get the template configuration
    try:
        # Try to get the template method dynamically
        template_method = getattr(SimulationConfig, f"example_{template_name}", None)
        if not template_method:
            template_method = getattr(SimulationConfig, template_name, None)
        if not template_method:
            template_method = getattr(SimulationConfig, f"convergence_test_{template_name}", None)

        if not template_method:
            print(f"❌ Template not found: {template_name}")
            print("   Available templates: board_meeting, hospital_crisis, kami_shrine, etc.")
            return False

        config = template_method()
        print(f"✓ Loaded template: {template_name}")
        print(f"  World ID: {config.world_id}")
        print(f"  Entities: {config.entities.count}")
        print(f"  Timepoints: {config.timepoints.count}")
        print()

    except Exception as e:
        print(f"❌ Failed to load template: {e}")
        return False

    # Initialize runner
    metadata_manager = MetadataManager(db_path="metadata/runs.db")
    runner = ResilientE2EWorkflowRunner(metadata_manager, generate_summary=not skip_summaries)

    # Run the template N times
    run_results = []
    run_ids = []
    total_cost = 0.0

    print(f"{'='*80}")
    print(f"PHASE 1: Running {template_name} x{run_count}")
    print(f"{'='*80}")
    print()

    for i in range(run_count):
        print(f"\n[Run {i+1}/{run_count}] Starting...")
        print("-" * 40)

        try:
            result = runner.run(config)
            run_ids.append(result.run_id)
            mechanisms = set(result.mechanisms_used) if result.mechanisms_used else set()

            run_results.append({
                'success': True,
                'run_id': result.run_id,
                'mechanisms': mechanisms,
                'entities': result.entities_created,
                'timepoints': result.timepoints_created,
                'cost': result.cost_usd or 0.0
            })

            total_cost += result.cost_usd or 0.0
            print(f"✅ Run {i+1} complete: {result.run_id}")
            print(f"   Mechanisms: {', '.join(sorted(mechanisms))}")
            print(f"   Cost: ${result.cost_usd:.2f}")

        except Exception as e:
            print(f"❌ Run {i+1} failed: {e}")
            run_results.append({
                'success': False,
                'error': str(e),
                'mechanisms': set()
            })

    # Check if we have enough successful runs
    successful_runs = [r for r in run_results if r['success']]
    if len(successful_runs) < 2:
        print(f"\n❌ Not enough successful runs for convergence ({len(successful_runs)}/2 minimum)")
        return False

    print(f"\n{'='*80}")
    print(f"PHASE 2: Side-by-Side Comparison")
    print(f"{'='*80}")
    print()

    # Display side-by-side comparison
    print("📊 RUN COMPARISON:")
    print("-" * 80)

    # Header
    header = "  {:12s}".format("Metric")
    for i, run in enumerate(successful_runs):
        header += " | {:20s}".format(f"Run {i+1}")
    print(header)
    print("-" * 80)

    # Run IDs
    row = "  {:12s}".format("Run ID")
    for run in successful_runs:
        row += " | {:20s}".format(run['run_id'][:18] + "..")
    print(row)

    # Entities
    row = "  {:12s}".format("Entities")
    for run in successful_runs:
        row += " | {:20s}".format(str(run.get('entities', 'N/A')))
    print(row)

    # Timepoints
    row = "  {:12s}".format("Timepoints")
    for run in successful_runs:
        row += " | {:20s}".format(str(run.get('timepoints', 'N/A')))
    print(row)

    # Cost
    row = "  {:12s}".format("Cost")
    for run in successful_runs:
        row += " | {:20s}".format(f"${run.get('cost', 0):.2f}")
    print(row)

    print("-" * 80)

    # Mechanisms comparison
    print("\n📋 MECHANISM COMPARISON:")
    print("-" * 80)

    all_mechanisms = set()
    for run in successful_runs:
        all_mechanisms.update(run['mechanisms'])

    for mech in sorted(all_mechanisms):
        row = f"  {mech:12s}"
        for run in successful_runs:
            if mech in run['mechanisms']:
                row += " | {:20s}".format("✓")
            else:
                row += " | {:20s}".format("✗")
        print(row)

    print("-" * 80)

    # Compute convergence
    print(f"\n{'='*80}")
    print(f"PHASE 3: Convergence Analysis")
    print(f"{'='*80}")
    print()

    # Extract real causal graphs from database
    print("Extracting causal graphs from database...")
    graphs = []
    for run in successful_runs:
        try:
            graph = extract_causal_graph(
                run_id=run['run_id'],
                db_path="metadata/runs.db",
                template_id=template_name
            )
            graphs.append(graph)
            print(f"  ├─ Run {run['run_id'][:20]}...: {graph.edge_count} edges ({len(graph.temporal_edges)} temporal, {len(graph.knowledge_edges)} knowledge)")
        except Exception as e:
            print(f"  ⚠️ Could not extract graph for run {run['run_id']}: {e}")

    # Check minimum graph count
    if len(graphs) < 2:
        print(f"\n❌ Not enough graphs extracted for convergence ({len(graphs)}/2 minimum)")
        print("   This may indicate the runs didn't persist timepoints/events to the shared database.")
        return False

    # Compute convergence
    result = compute_convergence_from_graphs(graphs)

    # Display convergence results
    print(f"📊 CONVERGENCE RESULTS:")
    print("-" * 80)
    print(f"  ├─ Score: {result.convergence_score:.2%}")
    print(f"  ├─ Grade: {result.robustness_grade}")
    print(f"  ├─ Min Similarity: {result.min_similarity:.2%}")
    print(f"  ├─ Max Similarity: {result.max_similarity:.2%}")
    print(f"  ├─ Consensus Edges: {len(result.consensus_edges)}")
    print(f"  └─ Contested Edges: {len(result.contested_edges)}")

    # Grade interpretation
    grade_meanings = {
        "A": "Excellent - Causal mechanisms are highly robust",
        "B": "Good - Causal mechanisms are reasonably stable",
        "C": "Fair - Some variability in causal structure",
        "D": "Poor - Significant causal divergence",
        "F": "Fail - Causal mechanisms are highly sensitive to conditions"
    }
    print(f"\n  💡 {grade_meanings.get(result.robustness_grade, 'Unknown grade')}")

    # Consensus edges
    if result.consensus_edges:
        print(f"\n  ✓ CONSENSUS EDGES (present in ALL runs):")
        for edge in sorted(result.consensus_edges)[:10]:
            print(f"     {edge}")
        if len(result.consensus_edges) > 10:
            print(f"     ... and {len(result.consensus_edges) - 10} more")

    # Contested edges
    if result.contested_edges:
        print(f"\n  ⚠ CONTESTED EDGES (present in SOME runs):")
        for edge in sorted(result.contested_edges)[:10]:
            print(f"     {edge}")
        if len(result.contested_edges) > 10:
            print(f"     ... and {len(result.contested_edges) - 10} more")

    # Divergence points
    if result.divergence_points:
        print(f"\n  🔀 DIVERGENCE POINTS ({len(result.divergence_points)} total):")
        show_count = len(result.divergence_points) if verbose else min(5, len(result.divergence_points))
        for dp in result.divergence_points[:show_count]:
            print(f"     - {dp.edge}: {dp.agreement_ratio:.0%} agreement")
            if verbose:
                print(f"       Present in: {', '.join(dp.present_in_runs)}")
                print(f"       Absent in: {', '.join(dp.absent_in_runs)}")
        if not verbose and len(result.divergence_points) > 5:
            print(f"     ... and {len(result.divergence_points) - 5} more (use --convergence-verbose)")

    # Store result in database
    store = GraphStore("sqlite:///metadata/runs.db")
    convergence_set = ConvergenceSet(
        set_id=f"conv_e2e_{uuid.uuid4().hex[:8]}",
        template_id=template_name,
        run_ids=json.dumps(result.run_ids),
        run_count=result.run_count,
        convergence_score=result.convergence_score,
        min_similarity=result.min_similarity,
        max_similarity=result.max_similarity,
        robustness_grade=result.robustness_grade,
        consensus_edge_count=len(result.consensus_edges),
        contested_edge_count=len(result.contested_edges),
        divergence_points=json.dumps([
            {"edge": dp.edge, "ratio": dp.agreement_ratio}
            for dp in result.divergence_points[:10]
        ])
    )
    store.save_convergence_set(convergence_set)

    # Final summary
    print(f"\n{'='*80}")
    print("CONVERGENCE E2E TEST COMPLETE")
    print("=" * 80)
    print(f"  Template: {template_name}")
    print(f"  Runs Completed: {len(successful_runs)}/{run_count}")
    print(f"  Convergence Score: {result.convergence_score:.2%}")
    print(f"  Robustness Grade: {result.robustness_grade}")
    print(f"  Total Cost: ${total_cost:.2f}")
    print(f"  Results Saved: {convergence_set.set_id}")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return len(successful_runs) == run_count


def _print_narrative_excerpt(run_id: str, world_id: str):
    """Print narrative excerpt from JSON file for monitoring visibility"""
    try:
        import json  # Import inside function to avoid any import order issues

        # Look for narrative JSON file
        datasets_dir = Path("datasets") / world_id
        narrative_files = list(datasets_dir.glob(f"narrative_{run_id}.json"))

        if not narrative_files:
            return  # No narrative file yet

        narrative_file = narrative_files[0]
        with open(narrative_file) as f:
            narrative_data = json.load(f)

        # Extract sample content
        timepoints = narrative_data.get("timepoints", [])
        if not timepoints:
            return

        # Print first and last timepoint summaries
        print(f"\n   📖 Narrative Excerpt:")

        # First timepoint
        first_tp = timepoints[0]
        print(f"   ├─ T0: {first_tp.get('timestamp', 'N/A')} - {first_tp.get('title', 'Untitled')}")
        if first_tp.get('scene'):
            scene_text = first_tp['scene'][:150].replace('\n', ' ')
            print(f"   │  Scene: {scene_text}...")

        # Last timepoint (if different)
        if len(timepoints) > 1:
            last_tp = timepoints[-1]
            print(f"   └─ T{len(timepoints)-1}: {last_tp.get('timestamp', 'N/A')} - {last_tp.get('title', 'Untitled')}")
            if last_tp.get('scene'):
                scene_text = last_tp['scene'][:150].replace('\n', ' ')
                print(f"      Scene: {scene_text}...")

        # Sample dialog if available
        for tp in timepoints[:2]:  # Check first 2 timepoints
            dialogs = tp.get('dialogs', [])
            if dialogs:
                first_dialog = dialogs[0]
                speaker = first_dialog.get('speaker', 'Unknown')
                text = first_dialog.get('text', '')[:100].replace('\n', ' ')
                print(f"   💬 Sample Dialog ({speaker}): \"{text}...\"")
                break

        print()  # Empty line for readability

    except Exception as e:
        # Silently fail - narrative excerpt is nice-to-have, not critical
        pass


def confirm_expensive_run(mode: str, min_cost: float, max_cost: float, runtime_min: int) -> bool:
    """
    Ask user to confirm expensive test runs.

    Args:
        mode: The mode name
        min_cost: Minimum estimated cost in USD
        max_cost: Maximum estimated cost in USD
        runtime_min: Estimated runtime in minutes

    Returns:
        True if user confirms, False otherwise
    """
    print("\n" + "="*80)
    print("⚠️  EXPENSIVE RUN CONFIRMATION REQUIRED")
    print("="*80)
    print(f"Mode: {mode}")
    print(f"Estimated Cost: ${min_cost:.2f}-${max_cost:.2f}")
    print(f"Estimated Runtime: {runtime_min} minutes")
    print()

    # Check if auto-confirm is enabled via environment variable
    # This allows monitoring systems to bypass the interactive prompt
    if os.getenv("TIMEPOINT_AUTO_CONFIRM", "").lower() in ["1", "true", "yes"]:
        print("✓ AUTO-CONFIRMED (TIMEPOINT_AUTO_CONFIRM environment variable set)")
        print("✓ Starting test run...")
        return True

    # Temporarily disable graceful interrupt during input
    disable_graceful_interrupt()
    try:
        response = input("Do you want to proceed? [y/N]: ").strip().lower()
    finally:
        enable_graceful_interrupt()

    if response in ['y', 'yes']:
        print("✓ Confirmed. Starting test run...")
        return True
    else:
        print("❌ Cancelled by user")
        return False


def list_modes():
    """Display all available simulation modes with template counts and cost estimates"""
    print("\n" + "="*80)
    print("AVAILABLE SIMULATION MODES")
    print("="*80)

    print("\n📚 QUICK MODE (DEFAULT)")
    print("  Templates: 7 | Cost: $0.15-$0.30 | Runtime: 8-15 min")
    print("  Safe, fast templates for basic mechanism coverage")

    print("\n🔬 FULL MODE (--full)")
    print("  Templates: 13 | Cost: $0.30-$0.80 | Runtime: 30-60 min")
    print("  All quick templates + expensive comprehensive templates")

    print("\n🏢 TIMEPOINT CORPORATE MODES")
    print("  --timepoint-forward:")
    print("    Templates: 15 | Cost: $0.50-$1.00 | Runtime: 30-60 min")
    print("    Forward-mode Timepoint corporate templates (formation + growth + AI marketplace)")
    print("  --timepoint-all:")
    print("    Templates: 35 | Cost: $2.50-$4.50 | Runtime: 60-120 min")
    print("    ALL Timepoint corporate (15 forward-mode + 20 portal-mode)")

    print("\n🌀 PORTAL MODES (Backward Temporal Reasoning)")
    print("  --portal-test-only:")
    print("    Templates: 4 | Cost: $0.15-$0.30 | Runtime: 10-15 min")
    print("    Standard portal templates (presidential, startup, academic, failure)")
    print("  --portal-simjudged-quick-only:")
    print("    Templates: 4 | Cost: $0.25-$0.50 | Runtime: 20-30 min")
    print("    Portal + lightweight simulation judging (1 step)")
    print("  --portal-simjudged-only:")
    print("    Templates: 4 | Cost: $0.40-$0.80 | Runtime: 30-45 min")
    print("    Portal + standard simulation judging (2 steps + dialog)")
    print("  --portal-simjudged-thorough-only:")
    print("    Templates: 4 | Cost: $0.50-$1.00 | Runtime: 45-60 min")
    print("    Portal + thorough simulation judging (3 steps + analysis)")
    print("  --portal-all:")
    print("    Templates: 16 | Cost: $1.30-$2.50 | Runtime: 60-90 min")
    print("    ALL portal variants (standard + quick + standard + thorough)")

    print("\n🎯 PORTAL TIMEPOINT MODES (Real Founder Profiles)")
    print("  --portal-timepoint-only:")
    print("    Templates: 5 | Cost: $0.20-$0.40 | Runtime: 12-18 min")
    print("    Standard portal with real Timepoint founders (Sean + Ken)")
    print("  --portal-timepoint-simjudged-quick-only:")
    print("    Templates: 5 | Cost: $0.40-$0.80 | Runtime: 24-36 min")
    print("    Portal Timepoint + lightweight simulation judging")
    print("  --portal-timepoint-simjudged-only:")
    print("    Templates: 5 | Cost: $0.60-$1.20 | Runtime: 36-54 min")
    print("    Portal Timepoint + standard simulation judging")
    print("  --portal-timepoint-simjudged-thorough-only:")
    print("    Templates: 5 | Cost: $0.80-$1.50 | Runtime: 54-75 min")
    print("    Portal Timepoint + thorough simulation judging")
    print("  --portal-timepoint-all:")
    print("    Templates: 20 | Cost: $2.00-$3.50 | Runtime: 60-100 min")
    print("    ALL portal Timepoint variants (standard + quick + standard + thorough)")

    print("\n" + "="*80)
    print("🚀 ULTRA MODE (--ultra-all)")
    print("  Templates: 64 | Cost: $4.00-$8.00 | Runtime: 120-180 min")
    print("  Run EVERYTHING: quick + full + timepoint corporate + all portal modes")
    print("  Complete system validation across all 17 mechanisms")
    print("="*80)

    print("\n" + "="*80)
    print("🗣️  NATURAL LANGUAGE MODE (--nl)")
    print("  Run any simulation from plain English description")
    print("  Example: --nl \"Emergency board meeting where CFO reveals bankruptcy\"")
    print("  Options: --nl-entities N, --nl-timepoints N to override defaults")
    print("="*80)

    print("\n" + "="*80)
    print("📊 CONVERGENCE ANALYSIS")
    print("  --convergence:           Run convergence after simulations")
    print("  --convergence-only:      Run ONLY convergence (no simulations)")
    print("  --convergence-runs N:    Number of runs to compare (default: 3)")
    print("  --convergence-template:  Filter to specific template")
    print("  --convergence-verbose:   Show detailed divergence points")
    print("  Example: --convergence-only --convergence-template hospital_crisis --convergence-runs 5")
    print("="*80)

    print("\n" + "="*80)
    print("🔬 CONVERGENCE E2E MODE (--convergence-e2e)")
    print("  Run a template N times consecutively, then compute convergence")
    print("  Includes side-by-side comparison of runs and divergence analysis")
    print("  Example: --convergence-e2e --template board_meeting --convergence-runs 3")
    print("  Cost: ~$0.08-$0.15 for 3 runs of board_meeting")
    print("="*80)

    print("\n" + "="*80)
    print("🆓 FREE MODEL OPTIONS ($0 cost)")
    print("="*80)
    print("  --free:              Use best available free model (quality-focused)")
    print("                       Prefers: Qwen 235B, Llama 3.3 70B, Gemini Flash")
    print("  --free-fast:         Use fastest free model (speed-focused)")
    print("                       Prefers: Gemini Flash, Llama 3.2 3B/1B, Mistral 7B")
    print("  --list-free-models:  Show all currently available free models")
    print()
    print("  Free models rotate availability on OpenRouter.")
    print("  Use --list-free-models to see what's currently available.")
    print()
    print("  Example: python run_all_mechanism_tests.py --free --template board_meeting")
    print("  Example: python run_all_mechanism_tests.py --free-fast --parallel 4")
    print("="*80)

    print("\n" + "="*80)
    print("💡 TIPS")
    print("="*80)
    print("  --skip-summaries:  Reduce cost slightly by skipping LLM summaries")
    print("  --parallel N:      Run N templates in parallel (recommended: 4-6)")
    print("  --model MODEL_ID:  Use specific model (e.g., meta-llama/llama-3.1-405b-instruct)")
    print("="*80)
    print()


def run_template(runner, config, name: str, expected_mechanisms: Set[str]) -> Dict:
    """Run a single template and return results"""
    print(f"\n{'='*80}")
    print(f"Running: {name}")
    print(f"Expected mechanisms: {', '.join(expected_mechanisms)}")
    print(f"{'='*80}\n")

    try:
        result = runner.run(config)
        mechanisms = set(result.mechanisms_used) if result.mechanisms_used else set()

        # Track Oxen URLs and PDF locations
        oxen_repo_url = result.oxen_repo_url if hasattr(result, 'oxen_repo_url') else None
        oxen_dataset_url = result.oxen_dataset_url if hasattr(result, 'oxen_dataset_url') else None

        # Find PDF files in datasets/{world_id}/
        pdf_paths = []
        template_dataset_dir = Path("datasets") / config.world_id
        if template_dataset_dir.exists():
            pdf_paths = [str(p) for p in template_dataset_dir.glob("*.pdf")]

        success = {
            'success': True,
            'run_id': result.run_id,
            'entities': result.entities_created,
            'timepoints': result.timepoints_created,
            'mechanisms': mechanisms,
            'expected': expected_mechanisms,
            'cost': result.cost_usd or 0.0,
            'summary': result.summary if hasattr(result, 'summary') else None,
            'oxen_repo_url': oxen_repo_url,
            'oxen_dataset_url': oxen_dataset_url,
            'pdf_paths': pdf_paths
        }

        print(f"\n✅ Success: {name}")
        print(f"   Run ID: {result.run_id}")
        print(f"   Entities: {result.entities_created}, Timepoints: {result.timepoints_created}")
        print(f"   Mechanisms: {', '.join(sorted(mechanisms))}")
        print(f"   Cost: ${result.cost_usd:.2f}")
        if oxen_repo_url:
            print(f"   Oxen Repo: {oxen_repo_url}")
        if pdf_paths:
            print(f"   PDFs: {len(pdf_paths)} generated")

        # Print narrative excerpt for monitoring visibility
        _print_narrative_excerpt(result.run_id, config.world_id)

        return success

    except Exception as e:
        print(f"\n❌ Failed: {name}")
        print(f"   Error: {str(e)[:200]}")
        return {
            'success': False,
            'error': str(e),
            'mechanisms': set(),
            'expected': expected_mechanisms,
            'cost': 0.0,
            'summary': None
        }


def run_andos_script(script: str, name: str, expected_mechanisms: Set[str]) -> Dict:
    """Run a standalone ANDOS test script"""
    print(f"\n{'='*80}")
    print(f"Running ANDOS Script: {name}")
    print(f"Script: {script}")
    print(f"Expected mechanisms: {', '.join(expected_mechanisms)}")
    print(f"{'='*80}\n")

    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            env={**os.environ, "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY")}
        )

        success = result.returncode == 0

        if success:
            # Parse run_id from output
            run_id = None
            for line in result.stdout.split('\n'):
                if 'Run ID:' in line or 'run_id:' in line:
                    # Extract run_id from lines like "Run ID: run_20251026_220100_2487a596"
                    parts = line.split(':')
                    if len(parts) >= 2:
                        run_id = parts[-1].strip()
                        break

            print(f"✅ Success: {name}")
            print(f"   Exit code: {result.returncode}")
            if run_id:
                print(f"   Run ID: {run_id}")

            # Print last few lines
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[-3:]:
                print(f"   {line}")

            return {
                'success': True,
                'run_id': run_id,
                'expected': expected_mechanisms,
                'exit_code': result.returncode
            }
        else:
            print(f"❌ Failed: {name}")
            print(f"   Exit code: {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")

            return {
                'success': False,
                'error': f"Exit code {result.returncode}",
                'expected': expected_mechanisms
            }

    except subprocess.TimeoutExpired:
        print(f"❌ Timeout: {name}")
        return {
            'success': False,
            'error': "Timeout (>10 minutes)",
            'expected': expected_mechanisms
        }
    except Exception as e:
        print(f"❌ Exception: {name}")
        print(f"   Error: {str(e)[:100]}")
        return {
            'success': False,
            'error': str(e),
            'expected': expected_mechanisms
        }


def run_nl_simulation(
    nl_input: str,
    skip_summaries: bool = False,
    entities: Optional[int] = None,
    timepoints: Optional[int] = None
) -> bool:
    """
    Run a simulation from natural language input.

    This function takes a natural language description and:
    1. Uses NLConfigGenerator to generate a simple config
    2. Converts it to production SimulationConfig via NLToProductionAdapter
    3. Runs the simulation with e2e_runner

    Args:
        nl_input: Natural language description of the simulation
        skip_summaries: Whether to skip LLM-powered summaries
        entities: Override entity count (optional)
        timepoints: Override timepoint count (optional)

    Returns:
        True if simulation succeeded, False otherwise

    Example:
        python run_all_mechanism_tests.py --nl "Board meeting where CEO announces layoffs"
    """
    from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
    from metadata.run_tracker import MetadataManager
    from nl_interface import NLConfigGenerator
    from nl_interface.adapter import convert_nl_to_production

    print("=" * 80)
    print("NATURAL LANGUAGE SIMULATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    print(f"Input: \"{nl_input}\"")
    print()

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        return False

    # Step 1: Generate NL config
    print("Step 1: Generating NL config...")
    try:
        generator = NLConfigGenerator(api_key=api_key)
        nl_config, confidence = generator.generate_config(nl_input)
        print(f"  Confidence: {confidence:.1%}")
        print(f"  Scenario: {nl_config.get('scenario', 'N/A')[:100]}...")
        print(f"  Entities: {len(nl_config.get('entities', []))}")
        print(f"  Timepoints: {nl_config.get('timepoint_count', 'N/A')}")
        print(f"  Temporal Mode: {nl_config.get('temporal_mode', 'N/A')}")
    except Exception as e:
        print(f"  ERROR: Failed to generate NL config: {e}")
        return False

    # Apply overrides if provided
    if entities is not None:
        nl_config['entities'] = [{'name': f'Entity{i}', 'role': 'participant'} for i in range(entities)]
        print(f"  (Entity count overridden to {entities})")
    if timepoints is not None:
        nl_config['timepoint_count'] = timepoints
        print(f"  (Timepoint count overridden to {timepoints})")

    # Step 2: Convert to production config
    print()
    print("Step 2: Converting to production SimulationConfig...")
    try:
        production_config = convert_nl_to_production(nl_config, confidence)
        print(f"  World ID: {production_config.world_id}")
        print(f"  Entities: {production_config.entities.count}")
        print(f"  Timepoints: {production_config.timepoints.count}")
        print(f"  Temporal Mode: {production_config.temporal.mode.value}")
    except Exception as e:
        print(f"  ERROR: Failed to convert to production config: {e}")
        return False

    # Step 3: Run simulation
    print()
    print("Step 3: Running simulation...")
    try:
        metadata_manager = MetadataManager(db_path="metadata/runs.db")
        runner = ResilientE2EWorkflowRunner(
            metadata_manager,
            generate_summary=not skip_summaries
        )
        result = runner.run(production_config)

        print()
        print("=" * 80)
        print("SIMULATION COMPLETE")
        print("=" * 80)
        print(f"  Run ID: {result.run_id}")
        print(f"  Entities Created: {result.entities_created}")
        print(f"  Timepoints Created: {result.timepoints_created}")
        print(f"  Mechanisms Used: {', '.join(sorted(result.mechanisms_used or []))}")
        print(f"  Cost: ${result.cost_usd:.2f}")

        if hasattr(result, 'summary') and result.summary:
            print()
            print("Summary:")
            print(f"  {result.summary}")

        # Print narrative excerpt
        _print_narrative_excerpt(result.run_id, production_config.world_id)

        return True

    except Exception as e:
        print(f"  ERROR: Simulation failed: {e}")
        return False


def run_all_templates(mode: str = 'quick', skip_summaries: bool = False, parallel_workers: int = 1):
    """Run all mechanism test templates

    Args:
        mode: Test mode (quick, full, portal, etc.)
        skip_summaries: Skip LLM-powered summaries
        parallel_workers: Number of parallel workers (1 = sequential)
    """
    from generation.config_schema import SimulationConfig
    from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
    from metadata.run_tracker import MetadataManager

    print("=" * 80)
    print(f"COMPREHENSIVE MECHANISM COVERAGE TEST ({mode.upper()} MODE)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if parallel_workers > 1:
        print(f"Parallel Workers: {parallel_workers}")
    print("=" * 80)
    print()
    print("⏱️  Rate Limiting Strategy:")
    print("   - Paid mode (1000 req/min): Minimal delays")
    print("   - Templates: 0s cooldown (16.67 req/sec available)")
    if parallel_workers > 1:
        print(f"   - Parallel execution: {parallel_workers} workers (thread-safe rate limiter)")
    print("   - ANDOS scripts: 0s cooldown")
    print("   - Phase transition: 0s")
    print()
    if skip_summaries:
        print("📝 Summaries: DISABLED (--skip-summaries)")
    else:
        print("📝 Summaries: ENABLED (use --skip-summaries to disable)")
    print()

    # Initialize
    metadata_manager = MetadataManager(db_path="metadata/runs.db")
    runner = ResilientE2EWorkflowRunner(metadata_manager, generate_summary=not skip_summaries)

    # Define templates
    # Quick mode: safe, fast templates
    quick_templates = [
        ("board_meeting", SimulationConfig.example_board_meeting(), {"M7"}),
        ("jefferson_dinner", SimulationConfig.example_jefferson_dinner(), {"M3", "M7"}),
        ("hospital_crisis", SimulationConfig.example_hospital_crisis(), {"M8", "M14"}),
        ("kami_shrine", SimulationConfig.example_kami_shrine(), {"M16"}),
        ("detective_prospection", SimulationConfig.example_detective_prospection(), {"M15"}),
        ("vc_pitch_pearl", SimulationConfig.example_vc_pitch_pearl(), {"M7", "M11", "M15"}),
        ("vc_pitch_roadshow", SimulationConfig.example_vc_pitch_roadshow(), {"M3", "M7", "M10", "M13"}),
    ]

    # Full mode: expensive, comprehensive templates
    full_templates = [
        ("empty_house_flashback", SimulationConfig.example_empty_house_flashback(), {"M17", "M13", "M8"}),
        ("final_problem_branching", SimulationConfig.example_final_problem_branching(), {"M12", "M17", "M15"}),
        ("hound_shadow_directorial", SimulationConfig.example_hound_shadow_directorial(), {"M17", "M10", "M14"}),
        ("sign_loops_cyclical", SimulationConfig.example_sign_loops_cyclical(), {"M17", "M15", "M3"}),
        ("vc_pitch_branching", SimulationConfig.example_vc_pitch_branching(), {"M12", "M15", "M8", "M17"}),
        ("vc_pitch_strategies", SimulationConfig.example_vc_pitch_strategies(), {"M12", "M10", "M15", "M17"}),
        # WARNING: These are VERY expensive!
        # ("variations", SimulationConfig.example_variations(), {"M1", "M2"}),  # 100 variations
        # ("scarlet_study_deep", SimulationConfig.example_scarlet_study_deep(), {"M1-M17"}),  # 101 timepoints
    ]

    # Timepoint Corporate Formation Analysis (new category)
    timepoint_corporate_templates = [
        # Corporate formation reverse-engineering (medium cost)
        ("timepoint_ipo_reverse", SimulationConfig.timepoint_ipo_reverse_engineering(), {"M12", "M15", "M7", "M13", "M11"}),
        ("timepoint_acquisition_scenarios", SimulationConfig.timepoint_acquisition_scenarios(), {"M12", "M15", "M11", "M8", "M7", "M13"}),
        ("timepoint_cofounder_configs", SimulationConfig.timepoint_cofounder_configurations(), {"M12", "M13", "M8", "M7", "M11"}),
        ("timepoint_equity_incentives", SimulationConfig.timepoint_equity_performance_incentives(), {"M12", "M13", "M7", "M15", "M11", "M8"}),
        ("timepoint_formation_decisions", SimulationConfig.timepoint_critical_formation_decisions(), {"M12", "M7", "M15", "M11"}),
        ("timepoint_success_vs_failure", SimulationConfig.timepoint_success_vs_failure_paths(), {"M12", "M7", "M13", "M8", "M11", "M15"}),
        # Emergent growth strategy templates (Phase 5 - new!)
        ("timepoint_launch_marketing", SimulationConfig.timepoint_launch_marketing_campaigns(), {"M3", "M10", "M14"}),
        ("timepoint_staffing_growth", SimulationConfig.timepoint_staffing_and_growth(), {"M3", "M10", "M14", "M15"}),
        # Founder personality × governance structure (expensive, comprehensive)
        ("timepoint_personality_archetypes", SimulationConfig.timepoint_founder_personality_archetypes(), {"M12", "M13", "M8", "M7", "M11"}),
        ("timepoint_charismatic_founder", SimulationConfig.timepoint_charismatic_founder_archetype(), {"M12", "M13", "M8", "M11", "M7"}),
        ("timepoint_demanding_genius", SimulationConfig.timepoint_demanding_genius_archetype(), {"M12", "M13", "M8", "M7", "M15", "M11"}),
        # AI marketplace competitive dynamics (NEW - Phase 11)
        ("timepoint_ai_pricing_war", SimulationConfig.timepoint_ai_pricing_war(), {"M12", "M7", "M13", "M15", "M8"}),
        ("timepoint_ai_capability_leapfrog", SimulationConfig.timepoint_ai_capability_leapfrog(), {"M12", "M9", "M10", "M13"}),
        ("timepoint_ai_business_model_evolution", SimulationConfig.timepoint_ai_business_model_evolution(), {"M12", "M7", "M13", "M15", "M8"}),
        ("timepoint_ai_regulatory_divergence", SimulationConfig.timepoint_ai_regulatory_divergence(), {"M12", "M7", "M13", "M14"}),
    ]

    # PORTAL mode templates (backward temporal reasoning)
    portal_templates = [
        ("portal_presidential_election", SimulationConfig.portal_presidential_election(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn", SimulationConfig.portal_startup_unicorn(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure", SimulationConfig.portal_academic_tenure(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure", SimulationConfig.portal_startup_failure(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # PORTAL mode with SIMULATION-BASED JUDGING (enhanced quality)
    # Quick variants: 1 forward step, no dialog (~2x cost)
    portal_templates_simjudged_quick = [
        ("portal_presidential_election_simjudged_quick", SimulationConfig.portal_presidential_election_simjudged_quick(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged_quick", SimulationConfig.portal_startup_unicorn_simjudged_quick(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged_quick", SimulationConfig.portal_academic_tenure_simjudged_quick(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged_quick", SimulationConfig.portal_startup_failure_simjudged_quick(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # Standard variants: 2 forward steps, dialog enabled (~3x cost)
    portal_templates_simjudged = [
        ("portal_presidential_election_simjudged", SimulationConfig.portal_presidential_election_simjudged(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged", SimulationConfig.portal_startup_unicorn_simjudged(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged", SimulationConfig.portal_academic_tenure_simjudged(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged", SimulationConfig.portal_startup_failure_simjudged(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # Thorough variants: 3 forward steps, extra analysis (~4-5x cost)
    portal_templates_simjudged_thorough = [
        ("portal_presidential_election_simjudged_thorough", SimulationConfig.portal_presidential_election_simjudged_thorough(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged_thorough", SimulationConfig.portal_startup_unicorn_simjudged_thorough(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged_thorough", SimulationConfig.portal_academic_tenure_simjudged_thorough(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged_thorough", SimulationConfig.portal_startup_failure_simjudged_thorough(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # PORTAL mode templates - Timepoint Corporate (real founder profiles)
    portal_timepoint_templates = [
        ("portal_timepoint_unicorn", SimulationConfig.portal_timepoint_unicorn(), {"M17", "M13", "M7", "M15", "M8", "M11"}),
        ("portal_timepoint_series_a_success", SimulationConfig.portal_timepoint_series_a_success(), {"M17", "M13", "M7", "M15", "M11"}),
        ("portal_timepoint_product_market_fit", SimulationConfig.portal_timepoint_product_market_fit(), {"M17", "M13", "M10", "M7", "M15"}),
        ("portal_timepoint_enterprise_adoption", SimulationConfig.portal_timepoint_enterprise_adoption(), {"M17", "M13", "M7", "M15", "M11", "M8"}),
        ("portal_timepoint_founder_transition", SimulationConfig.portal_timepoint_founder_transition(), {"M17", "M13", "M8", "M7", "M15"}),
    ]

    # PORTAL Timepoint with SIMULATION-BASED JUDGING
    # Quick variants: 1 forward step, no dialog (~2x cost)
    portal_timepoint_templates_simjudged_quick = [
        ("portal_timepoint_unicorn_simjudged_quick", SimulationConfig.portal_timepoint_unicorn_simjudged_quick(), {"M17", "M13", "M7", "M15", "M8", "M11"}),
        ("portal_timepoint_series_a_success_simjudged_quick", SimulationConfig.portal_timepoint_series_a_success_simjudged_quick(), {"M17", "M13", "M7", "M15", "M11"}),
        ("portal_timepoint_product_market_fit_simjudged_quick", SimulationConfig.portal_timepoint_product_market_fit_simjudged_quick(), {"M17", "M13", "M10", "M7", "M15"}),
        ("portal_timepoint_enterprise_adoption_simjudged_quick", SimulationConfig.portal_timepoint_enterprise_adoption_simjudged_quick(), {"M17", "M13", "M7", "M15", "M11", "M8"}),
        ("portal_timepoint_founder_transition_simjudged_quick", SimulationConfig.portal_timepoint_founder_transition_simjudged_quick(), {"M17", "M13", "M8", "M7", "M15"}),
    ]

    # Standard variants: 2 forward steps, dialog enabled (~3x cost)
    portal_timepoint_templates_simjudged = [
        ("portal_timepoint_unicorn_simjudged", SimulationConfig.portal_timepoint_unicorn_simjudged(), {"M17", "M13", "M7", "M15", "M8", "M11"}),
        ("portal_timepoint_series_a_success_simjudged", SimulationConfig.portal_timepoint_series_a_success_simjudged(), {"M17", "M13", "M7", "M15", "M11"}),
        ("portal_timepoint_product_market_fit_simjudged", SimulationConfig.portal_timepoint_product_market_fit_simjudged(), {"M17", "M13", "M10", "M7", "M15"}),
        ("portal_timepoint_enterprise_adoption_simjudged", SimulationConfig.portal_timepoint_enterprise_adoption_simjudged(), {"M17", "M13", "M7", "M15", "M11", "M8"}),
        ("portal_timepoint_founder_transition_simjudged", SimulationConfig.portal_timepoint_founder_transition_simjudged(), {"M17", "M13", "M8", "M7", "M15"}),
    ]

    # Thorough variants: 3 forward steps, extra analysis (~4-5x cost)
    portal_timepoint_templates_simjudged_thorough = [
        ("portal_timepoint_unicorn_simjudged_thorough", SimulationConfig.portal_timepoint_unicorn_simjudged_thorough(), {"M17", "M13", "M7", "M15", "M8", "M11"}),
        ("portal_timepoint_series_a_success_simjudged_thorough", SimulationConfig.portal_timepoint_series_a_success_simjudged_thorough(), {"M17", "M13", "M7", "M15", "M11"}),
        ("portal_timepoint_product_market_fit_simjudged_thorough", SimulationConfig.portal_timepoint_product_market_fit_simjudged_thorough(), {"M17", "M13", "M10", "M7", "M15"}),
        ("portal_timepoint_enterprise_adoption_simjudged_thorough", SimulationConfig.portal_timepoint_enterprise_adoption_simjudged_thorough(), {"M17", "M13", "M7", "M15", "M11", "M8"}),
        ("portal_timepoint_founder_transition_simjudged_thorough", SimulationConfig.portal_timepoint_founder_transition_simjudged_thorough(), {"M17", "M13", "M8", "M7", "M15"}),
    ]

    # ANDOS test scripts (always run)
    andos_scripts = [
        ("test_m5_query_evolution.py", "M5 Query Evolution", {"M5"}),
        ("test_m9_missing_witness.py", "M9 Missing Witness", {"M9"}),
        ("test_m10_scene_analysis.py", "M10 Scene Analysis", {"M10"}),
        ("test_m12_alternate_history.py", "M12 Alternate History", {"M12"}),
        ("test_m13_synthesis.py", "M13 Multi-Entity Synthesis", {"M13"}),
        ("test_m14_circadian.py", "M14 Circadian Patterns", {"M14"}),
    ]

    # Select templates based on mode
    templates_to_run = quick_templates
    if mode == 'full':
        templates_to_run = quick_templates + full_templates
        print("🔬 FULL MODE: Running comprehensive templates")
        print("   Estimated cost: $0.30-$0.80, Runtime: 30-60 minutes")
        print()
    elif mode == 'portal':
        templates_to_run = portal_templates
        print("🌀 PORTAL MODE: Backward Temporal Reasoning (Standard)")
        print("   Running 4 PORTAL mode templates (M17 - Modal Temporal Causality):")
        print("   - portal_presidential_election: Tech exec → President (15 years)")
        print("   - portal_startup_unicorn: Idea → $1B+ valuation (6 years)")
        print("   - portal_academic_tenure: PhD → Tenure (10 years)")
        print("   - portal_startup_failure: Seed → Shutdown (4 years)")
        print("   Estimated cost: $0.15-$0.30, Runtime: 10-15 minutes")
        print("   Each template generates multiple backward paths with coherence scoring")
        print()
    elif mode == 'portal_simjudged_quick':
        templates_to_run = portal_templates_simjudged_quick
        print("🎬 PORTAL MODE: Simulation-Judged QUICK (Enhanced Quality)")
        print("   Running 4 PORTAL templates with lightweight simulation judging:")
        print("   - 1 forward step per candidate antecedent")
        print("   - No dialog generation (faster)")
        print("   - Judge LLM: Llama 3.1 70B")
        print("   Estimated cost: $0.25-$0.50 (~2x standard), Runtime: 20-30 minutes")
        print("   Quality: Good - captures basic emergent behaviors")
        print()
    elif mode == 'portal_simjudged':
        templates_to_run = portal_templates_simjudged
        print("🎬 PORTAL MODE: Simulation-Judged STANDARD (High Quality)")
        print("   Running 4 PORTAL templates with standard simulation judging:")
        print("   - 2 forward steps per candidate antecedent")
        print("   - Dialog generation enabled")
        print("   - Judge LLM: Llama 3.1 405B")
        print("   Estimated cost: $0.40-$0.80 (~3x standard), Runtime: 30-45 minutes")
        print("   Quality: High - captures dialog realism and emergent patterns")
        print()
    elif mode == 'portal_simjudged_thorough':
        templates_to_run = portal_templates_simjudged_thorough
        print("🎬 PORTAL MODE: Simulation-Judged THOROUGH (Maximum Quality)")
        print("   Running 4 PORTAL templates with thorough simulation judging:")
        print("   - 3 forward steps per candidate antecedent")
        print("   - Dialog generation + extra analysis")
        print("   - Judge LLM: Llama 3.1 405B (low temperature)")
        print("   - More candidates per step for better exploration")
        print("   Estimated cost: $0.50-$1.00 (~4-5x standard), Runtime: 45-60 minutes")
        print("   Quality: Maximum - research-grade path generation")
        print()
    elif mode == 'portal_all':
        templates_to_run = portal_templates + portal_templates_simjudged_quick + portal_templates_simjudged + portal_templates_simjudged_thorough
        print("🎬🌀 PORTAL MODE: ALL VARIANTS (Comprehensive)")
        print("   Running ALL 16 PORTAL templates:")
        print("   - 4 standard PORTAL templates")
        print("   - 4 simulation-judged QUICK variants")
        print("   - 4 simulation-judged STANDARD variants")
        print("   - 4 simulation-judged THOROUGH variants")
        print("   Estimated cost: $1.30-$2.50, Runtime: 60-90 minutes")
        print("   Use this for comprehensive quality comparison across all approaches")
        print()
    elif mode == 'timepoint_corporate':
        templates_to_run = timepoint_corporate_templates
        print("🏢 TIMEPOINT CORPORATE ANALYSIS MODE")
        print("   Running 15 Timepoint-specific corporate templates:")
        print("   - 6 formation analysis templates (IPO, acquisition, cofounder configs, equity, decisions, success/failure)")
        print("   - 2 emergent growth templates (marketing campaigns, staffing & growth)")
        print("   - 3 personality × governance templates (archetypes, charismatic founder, demanding genius)")
        print("   - 4 AI marketplace dynamics templates (pricing war, capability leapfrog, business model evolution, regulatory divergence)")
        print("   Estimated cost: $0.50-$1.00, Runtime: 30-60 minutes")
        print()
    elif mode == 'portal_timepoint':
        templates_to_run = portal_timepoint_templates
        print("🌀 PORTAL TIMEPOINT MODE: Real Founder Stories (Standard)")
        print("   Running 5 PORTAL templates with real Timepoint founder profiles (Sean + Ken):")
        print("   - portal_timepoint_unicorn: $1.2B Series C (March 2030 → October 2024)")
        print("   - portal_timepoint_series_a_success: $50M Series A (December 2026 → February 2025)")
        print("   - portal_timepoint_product_market_fit: $5M ARR + PMF (June 2026 → October 2024)")
        print("   - portal_timepoint_enterprise_adoption: 25 F500 customers (March 2027 → November 2024)")
        print("   - portal_timepoint_founder_transition: Founder departure (September 2027 → October 2024)")
        print("   Estimated cost: $0.20-$0.40, Runtime: 12-18 minutes")
        print("   Each template traces backward from success/failure to founding decisions")
        print()
    elif mode == 'portal_timepoint_simjudged_quick':
        templates_to_run = portal_timepoint_templates_simjudged_quick
        print("🎬 PORTAL TIMEPOINT MODE: Simulation-Judged QUICK (Real Founders)")
        print("   Running 5 PORTAL templates with real Timepoint founders + lightweight simulation judging:")
        print("   - 1 forward step per candidate antecedent")
        print("   - No dialog generation (faster)")
        print("   - Judge LLM: Llama 3.1 70B")
        print("   Estimated cost: $0.40-$0.80 (~2x standard), Runtime: 24-36 minutes")
        print("   Quality: Good - captures basic emergent behaviors with real founder dynamics")
        print()
    elif mode == 'portal_timepoint_simjudged':
        templates_to_run = portal_timepoint_templates_simjudged
        print("🎬 PORTAL TIMEPOINT MODE: Simulation-Judged STANDARD (Real Founders)")
        print("   Running 5 PORTAL templates with real Timepoint founders + standard simulation judging:")
        print("   - 2 forward steps per candidate antecedent")
        print("   - Dialog generation enabled")
        print("   - Judge LLM: Llama 3.1 405B")
        print("   Estimated cost: $0.60-$1.20 (~3x standard), Runtime: 36-54 minutes")
        print("   Quality: High - captures dialog realism and founder partnership dynamics")
        print()
    elif mode == 'portal_timepoint_simjudged_thorough':
        templates_to_run = portal_timepoint_templates_simjudged_thorough
        print("🎬 PORTAL TIMEPOINT MODE: Simulation-Judged THOROUGH (Real Founders)")
        print("   Running 5 PORTAL templates with real Timepoint founders + thorough simulation judging:")
        print("   - 3 forward steps per candidate antecedent")
        print("   - Dialog generation + extra analysis")
        print("   - Judge LLM: Llama 3.1 405B (low temperature)")
        print("   - More candidates per step for better exploration")
        print("   Estimated cost: $0.80-$1.50 (~4-5x standard), Runtime: 54-75 minutes")
        print("   Quality: Maximum - research-grade founder journey analysis")
        print()
    elif mode == 'portal_timepoint_all':
        templates_to_run = portal_timepoint_templates + portal_timepoint_templates_simjudged_quick + portal_timepoint_templates_simjudged + portal_timepoint_templates_simjudged_thorough
        print("🎬🌀 PORTAL TIMEPOINT MODE: ALL VARIANTS (Real Founders - Comprehensive)")
        print("   Running ALL 20 PORTAL Timepoint templates with real founder profiles:")
        print("   - 5 standard PORTAL Timepoint templates")
        print("   - 5 simulation-judged QUICK variants")
        print("   - 5 simulation-judged STANDARD variants")
        print("   - 5 simulation-judged THOROUGH variants")
        print("   Estimated cost: $2.00-$3.50, Runtime: 60-100 minutes")
        print("   Use this for comprehensive quality comparison across all approaches with real founder data")
        print()
    elif mode == 'timepoint_all':
        templates_to_run = timepoint_corporate_templates + portal_timepoint_templates + portal_timepoint_templates_simjudged_quick + portal_timepoint_templates_simjudged + portal_timepoint_templates_simjudged_thorough
        print("🏢🌀 TIMEPOINT CORPORATE: ALL MODES (Complete Timepoint Suite)")
        print("   Running ALL 35 Timepoint corporate templates:")
        print("   - 15 forward-mode templates (formation, growth, personalities, AI marketplace)")
        print("   - 5 standard PORTAL Timepoint templates")
        print("   - 5 simulation-judged QUICK variants")
        print("   - 5 simulation-judged STANDARD variants")
        print("   - 5 simulation-judged THOROUGH variants")
        print("   Estimated cost: $2.50-$4.50, Runtime: 60-120 minutes")
        print("   Complete Timepoint corporate analysis: forward causality + backward portal reasoning")
        print()
    elif mode == 'ultra_all':
        templates_to_run = (quick_templates + full_templates +
                           timepoint_corporate_templates +
                           portal_templates + portal_templates_simjudged_quick + portal_templates_simjudged + portal_templates_simjudged_thorough +
                           portal_timepoint_templates + portal_timepoint_templates_simjudged_quick + portal_timepoint_templates_simjudged + portal_timepoint_templates_simjudged_thorough)
        print("🚀 ULTRA MODE: COMPLETE SYSTEM VALIDATION")
        print("   Running ALL 64 templates across ALL categories:")
        print("   - 7 quick templates (basic coverage)")
        print("   - 6 full templates (comprehensive)")
        print("   - 15 timepoint corporate templates (forward-mode)")
        print("   - 4 portal templates (backward reasoning)")
        print("   - 12 portal simjudged variants (all quality levels)")
        print("   - 5 portal timepoint templates (real founders)")
        print("   - 15 portal timepoint simjudged variants (all quality levels)")
        print("   Estimated cost: $4.00-$8.00, Runtime: 120-180 minutes")
        print("   Complete validation of all 17 mechanisms + ANDOS scripts")
        print()

    results = {}
    total_cost = 0.0

    # Confirmation for expensive runs (thresholds updated Dec 2024 based on actual costs)
    # Format: (min_cost_usd, max_cost_usd, runtime_minutes)
    # Only trigger confirmation for runs estimated >$2.00
    expensive_modes = {
        # These modes are now reasonably cheap (<$1), no confirmation needed
        # 'full': (0.30, 0.80, 45),  # ~$0.50 avg - too cheap to confirm
        # 'portal_simjudged': (0.40, 0.80, 38),  # ~$0.60 avg
        # 'portal_simjudged_thorough': (0.50, 1.00, 53),  # ~$0.75 avg
        # 'portal_timepoint_simjudged': (0.60, 1.20, 45),  # ~$0.90 avg
        # 'portal_timepoint_simjudged_thorough': (0.80, 1.50, 65),  # ~$1.15 avg
        # 'timepoint_corporate': (0.50, 1.00, 60),  # ~$0.75 avg

        # Only confirm for runs estimated >$2.00 (still cheap but worth a heads-up)
        'portal_all': (1.30, 2.50, 90),  # 16 templates
        'portal_timepoint_all': (2.00, 3.50, 100),  # 20 templates
        'timepoint_all': (2.50, 4.50, 120),  # 35 templates
        'ultra_all': (4.00, 8.00, 180)  # 64 templates - largest run
    }

    if mode in expensive_modes:
        min_cost, max_cost, runtime = expensive_modes[mode]
        if not confirm_expensive_run(mode.upper(), min_cost, max_cost, runtime):
            print("\nTest run cancelled.")
            sys.exit(0)

    # Initialize progress tracker (includes ANDOS scripts in total)
    total_jobs = len(templates_to_run) + len(andos_scripts)
    tracker = ProgressTracker(total_jobs=total_jobs, update_interval=60.0)
    tracker.print_header(f"TIMEPOINT SIMULATION RUNNER - {mode.upper()}")

    # Run pre-programmed templates
    print(f"\n{'='*80}")
    print(f"PHASE 1: Pre-Programmed Templates ({len(templates_to_run)} templates)")
    if parallel_workers > 1:
        print(f"Execution: PARALLEL ({parallel_workers} workers)")
    else:
        print("Execution: SEQUENTIAL")
    print(f"{'='*80}\n")

    if parallel_workers > 1:
        # Parallel execution with ThreadPoolExecutor
        import threading
        results_lock = threading.Lock()

        def run_template_parallel(args):
            """Wrapper for parallel template execution - creates own runner"""
            name, config, expected, skip_sums = args
            # Each thread needs its own runner for isolation
            thread_metadata_manager = MetadataManager(db_path="metadata/runs.db")
            thread_runner = ResilientE2EWorkflowRunner(
                thread_metadata_manager,
                generate_summary=not skip_sums
            )
            return name, run_template(thread_runner, config, name, expected)

        # Prepare jobs
        jobs = [(name, config, expected, skip_summaries) for name, config, expected in templates_to_run]
        completed = 0

        print(f"Starting {len(jobs)} templates with {parallel_workers} parallel workers...")
        print()

        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            # Submit all jobs and mark as started
            future_to_name = {}
            for job in jobs:
                tracker.start_job(job[0])
                future = executor.submit(run_template_parallel, job)
                future_to_name[future] = job[0]

            # Process results as they complete
            for future in as_completed(future_to_name):
                template_name = future_to_name[future]
                try:
                    name, result = future.result()
                    job_cost = result.get('cost', 0.0)
                    with results_lock:
                        results[name] = result
                        total_cost += job_cost
                        completed += 1
                    # Update tracker with completion
                    tracker.complete_job(name, success=result['success'], cost=job_cost)
                    tracker.print_status()
                except Exception as e:
                    with results_lock:
                        results[template_name] = {
                            'success': False,
                            'error': str(e),
                            'mechanisms': set(),
                            'expected': set(),
                            'cost': 0.0
                        }
                        completed += 1
                    tracker.complete_job(template_name, success=False, error=str(e))
                    tracker.print_status()

        print(f"\nParallel execution complete: {completed}/{len(jobs)} templates processed")
    else:
        # Sequential execution (original behavior)
        for idx, (name, config, expected) in enumerate(templates_to_run, 1):
            tracker.start_job(name)
            print(f"[{idx}/{len(templates_to_run)}] {name}")
            result = run_template(runner, config, name, expected)
            results[name] = result
            job_cost = result.get('cost', 0.0)
            total_cost += job_cost
            tracker.complete_job(name, success=result['success'], cost=job_cost)
            tracker.print_status()

            # No delay needed in paid mode (1000 req/min = 16.67 req/sec)

    # Run ANDOS test scripts
    print(f"\n{'='*80}")
    print(f"PHASE 2: ANDOS Test Scripts ({len(andos_scripts)} scripts)")
    print(f"{'='*80}")
    print(f"\n📝 Note: All ANDOS scripts now include explicit mechanism tracking")
    print(f"   M5, M9, M10, M12, M13, M14 will be recorded in metadata/runs.db")

    # No delay needed between phases in paid mode
    print()

    for idx, (script, name, expected) in enumerate(andos_scripts, 1):
        tracker.start_job(name)
        print(f"[{idx}/{len(andos_scripts)}] {name}")
        result = run_andos_script(script, name, expected)
        results[name] = result
        tracker.complete_job(name, success=result['success'], cost=result.get('cost', 0.0))
        tracker.print_status()

        # No delay needed between ANDOS scripts in paid mode

    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("COMPREHENSIVE RESULTS")
    print("=" * 80)

    # Template execution summary
    print("\n📊 Template Execution Summary:")
    passed = 0
    failed = 0
    for name, result in results.items():
        if result['success']:
            status = "✅ PASSED"
            passed += 1
            if 'run_id' in result:
                print(f"  {status:12s} {name:30s} (Run: {result['run_id'][:16]}...)")
            else:
                print(f"  {status:12s} {name:30s}")
        else:
            status = "❌ FAILED"
            failed += 1
            error = result.get('error', 'Unknown')[:40]
            print(f"  {status:12s} {name:30s} ({error})")

    print(f"\n  Total: {passed + failed} templates")
    print(f"  Passed: {passed} ({passed/(passed+failed)*100:.1f}%)")
    print(f"  Failed: {failed}")
    print(f"  Estimated Cost: ${total_cost:.2f}")

    # Mechanism coverage
    print("\n" + "-" * 80)
    print("🔬 Mechanism Coverage (metadata/runs.db):")
    print("-" * 80)

    try:
        all_runs = metadata_manager.get_all_runs()
        historical_mechanisms = set()
        for run in all_runs:
            if run.mechanisms_used:
                historical_mechanisms.update(run.mechanisms_used)

        print(f"\nTotal Coverage: {len(historical_mechanisms)}/17 ({len(historical_mechanisms)/17*100:.1f}%)")
        print(f"Tracked: {', '.join(sorted(historical_mechanisms))}")

        missing = set([f"M{i}" for i in range(1, 18)]) - historical_mechanisms
        if missing:
            print(f"\n⚠️  Missing: {', '.join(sorted(missing))}")
        else:
            print("\n🎉 SUCCESS: All 17 mechanisms tracked!")

    except Exception as e:
        print(f"Could not check metadata: {e}")

    # Output format validation
    print("\n" + "-" * 80)
    print("📁 Output Format Validation:")
    print("-" * 80)

    datasets_dir = Path("datasets")
    if datasets_dir.exists():
        json_files = list(datasets_dir.glob("**/*.json"))
        jsonl_files = list(datasets_dir.glob("**/*.jsonl"))
        md_files = list(datasets_dir.glob("**/*.md"))
        fountain_files = list(datasets_dir.glob("**/*.fountain"))
        pdf_files = list(datasets_dir.glob("**/*.pdf"))

        print(f"  JSON files: {len(json_files)}")
        print(f"  JSONL files: {len(jsonl_files)}")
        print(f"  Markdown files: {len(md_files)}")
        print(f"  Fountain scripts: {len(fountain_files)}")
        print(f"  PDF scripts: {len(pdf_files)}")

        if fountain_files:
            print(f"  ✅ Fountain export working")
        else:
            print(f"  ⚠️  No Fountain files found")

        if pdf_files:
            print(f"  ✅ PDF export working")
        else:
            print(f"  ⚠️  No PDF files found")
    else:
        print("  No datasets/ directory found")

    # Oxen integration
    print("\n" + "-" * 80)
    print("🐂 Oxen Integration:")
    print("-" * 80)

    if os.getenv("OXEN_API_TOKEN"):
        print("  ✅ OXEN_API_TOKEN is set")
        print("  Oxen uploads should have been attempted for each template")
    else:
        print("  ⚠️  OXEN_API_TOKEN not set - Oxen uploads skipped")
        print("  Set OXEN_API_TOKEN to test Oxen publishing")

    # Summary recap
    if not skip_summaries:
        print("\n" + "=" * 80)
        print("📝 RUN SUMMARIES RECAP")
        print("=" * 80)

        summaries_shown = 0
        for name, result in results.items():
            if result['success'] and result.get('summary'):
                print(f"\n{name}:")
                print(f"  {result['summary']}")
                summaries_shown += 1

        if summaries_shown == 0:
            print("\n  No summaries available (templates may not have completed successfully)")
        else:
            print(f"\n  Total summaries: {summaries_shown}")

    # Artifacts Summary (Oxen URLs and PDFs)
    print("\n" + "=" * 80)
    print("📦 ARTIFACTS SUMMARY")
    print("=" * 80)

    oxen_repos = []
    oxen_datasets = []
    all_pdfs = []

    for name, result in results.items():
        if result['success']:
            if result.get('oxen_repo_url'):
                oxen_repos.append((name, result['oxen_repo_url']))
            if result.get('oxen_dataset_url'):
                oxen_datasets.append((name, result['oxen_dataset_url']))
            if result.get('pdf_paths'):
                for pdf_path in result['pdf_paths']:
                    # Get file size
                    try:
                        size_bytes = Path(pdf_path).stat().st_size
                        size_kb = size_bytes / 1024
                        all_pdfs.append((name, pdf_path, size_kb))
                    except:
                        all_pdfs.append((name, pdf_path, 0.0))

    # Oxen Repositories
    if oxen_repos:
        print(f"\n🐂 Oxen Repositories ({len(oxen_repos)} templates):")
        for name, url in oxen_repos:
            print(f"  {name:30s} → {url}")
    else:
        print(f"\n🐂 Oxen Repositories: None (OXEN_API_TOKEN may not be set)")

    # Oxen Datasets
    if oxen_datasets:
        print(f"\n📊 Oxen Datasets ({len(oxen_datasets)} templates):")
        for name, url in oxen_datasets:
            print(f"  {name:30s} → {url}")

    # PDF Screenplays
    if all_pdfs:
        print(f"\n📄 PDF Screenplays ({len(all_pdfs)} files):")
        for name, pdf_path, size_kb in all_pdfs:
            print(f"  {name:30s} → {pdf_path} ({size_kb:.1f} KB)")
    else:
        print(f"\n📄 PDF Screenplays: None generated")

    # Summary stats
    print(f"\n📈 Artifact Statistics:")
    print(f"  Oxen Repositories: {len(oxen_repos)}")
    print(f"  Oxen Datasets: {len(oxen_datasets)}")
    print(f"  PDF Screenplays: {len(all_pdfs)}")
    total_pdf_size = sum(size for _, _, size in all_pdfs)
    if total_pdf_size > 0:
        print(f"  Total PDF Size: {total_pdf_size:.1f} KB")

    # Print colorful summary from tracker
    tracker.print_summary()

    # Final summary
    print("\n" + "=" * 80)
    print("TEST RUN COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {mode.upper()}")
    print(f"Templates Passed: {passed}/{passed + failed}")
    print(f"Total Cost: ${total_cost:.2f}")
    print("=" * 80)

    return passed == (passed + failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comprehensive Mechanism Coverage Test")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all templates including expensive ones (default: quick mode)"
    )
    parser.add_argument(
        "--portal-test-only",
        action="store_true",
        help="Run ONLY PORTAL mode backward simulation tests (4 templates)"
    )
    parser.add_argument(
        "--timepoint-corporate-analysis-only",
        action="store_true",
        help="[DEPRECATED] Use --timepoint-forward instead. Run ONLY Timepoint corporate formation scenarios (VC pitches + formation analysis)"
    )
    parser.add_argument(
        "--timepoint-forward",
        action="store_true",
        help="Run ONLY forward-mode Timepoint corporate templates (15 templates: formation analysis + growth + personalities + AI marketplace)"
    )
    parser.add_argument(
        "--timepoint-all",
        action="store_true",
        help="Run ALL Timepoint corporate templates (35 total: 15 forward-mode + 20 portal-mode)"
    )
    parser.add_argument(
        "--list-modes",
        action="store_true",
        help="Display all available simulation modes with template counts and exit"
    )
    parser.add_argument(
        "--portal-simjudged-quick-only",
        action="store_true",
        help="Run ONLY PORTAL simulation-judged QUICK variants (1 step, ~2x cost, 4 templates)"
    )
    parser.add_argument(
        "--portal-simjudged-only",
        action="store_true",
        help="Run ONLY PORTAL simulation-judged STANDARD variants (2 steps + dialog, ~3x cost, 4 templates)"
    )
    parser.add_argument(
        "--portal-simjudged-thorough-only",
        action="store_true",
        help="Run ONLY PORTAL simulation-judged THOROUGH variants (3 steps + analysis, ~4-5x cost, 4 templates)"
    )
    parser.add_argument(
        "--portal-all",
        action="store_true",
        help="Run ALL PORTAL tests (standard + all 3 simulation-judged variants = 16 templates total)"
    )
    parser.add_argument(
        "--portal-timepoint-only",
        action="store_true",
        help="Run ONLY PORTAL Timepoint templates with real founder profiles (5 templates)"
    )
    parser.add_argument(
        "--portal-timepoint-simjudged-quick-only",
        action="store_true",
        help="Run ONLY PORTAL Timepoint simulation-judged QUICK variants (1 step, ~2x cost, 5 templates)"
    )
    parser.add_argument(
        "--portal-timepoint-simjudged-only",
        action="store_true",
        help="Run ONLY PORTAL Timepoint simulation-judged STANDARD variants (2 steps + dialog, ~3x cost, 5 templates)"
    )
    parser.add_argument(
        "--portal-timepoint-simjudged-thorough-only",
        action="store_true",
        help="Run ONLY PORTAL Timepoint simulation-judged THOROUGH variants (3 steps + analysis, ~4-5x cost, 5 templates)"
    )
    parser.add_argument(
        "--portal-timepoint-all",
        action="store_true",
        help="Run ALL PORTAL Timepoint tests (standard + all 3 simulation-judged variants = 20 templates total)"
    )
    parser.add_argument(
        "--ultra-all",
        action="store_true",
        help="Run EVERYTHING: all 64 templates across ALL categories (quick + full + timepoint + portal + portal-timepoint = complete system validation)"
    )
    parser.add_argument(
        "--skip-summaries",
        action="store_true",
        help="Skip LLM-powered run summaries (reduces cost slightly)"
    )
    parser.add_argument(
        "--template",
        type=str,
        help="Run a single template by name (e.g. portal_timepoint_product_market_fit)"
    )
    # Natural Language Interface
    parser.add_argument(
        "--nl",
        type=str,
        metavar="DESCRIPTION",
        help="Run simulation from natural language description (e.g. --nl \"Board meeting where CEO announces layoffs\")"
    )
    parser.add_argument(
        "--nl-entities",
        type=int,
        metavar="N",
        help="Override entity count for NL simulation (used with --nl)"
    )
    parser.add_argument(
        "--nl-timepoints",
        type=int,
        metavar="N",
        help="Override timepoint count for NL simulation (used with --nl)"
    )
    parser.add_argument(
        "--convergence",
        action="store_true",
        help="Run convergence analysis on recent runs (compares causal graphs across runs)"
    )
    parser.add_argument(
        "--convergence-only",
        action="store_true",
        help="Run ONLY convergence analysis (no simulation runs)"
    )
    parser.add_argument(
        "--convergence-runs",
        type=int,
        default=3,
        help="Number of runs to compare for convergence (default: 3)"
    )
    parser.add_argument(
        "--convergence-template",
        type=str,
        metavar="TEMPLATE",
        help="Filter convergence analysis to specific template (e.g. hospital_crisis)"
    )
    parser.add_argument(
        "--convergence-verbose",
        action="store_true",
        help="Show detailed divergence points in convergence analysis"
    )
    parser.add_argument(
        "--convergence-e2e",
        action="store_true",
        help="Run template N times (--convergence-runs) then compute convergence with side-by-side comparison"
    )
    parser.add_argument(
        "--model",
        type=str,
        metavar="MODEL_ID",
        help="Override default LLM model (e.g. meta-llama/llama-3.1-405b-instruct)"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        metavar="N",
        help="Run templates in parallel with N workers (default: 1 = sequential). Recommended: 4-6 for optimal rate limit usage."
    )
    # Free model options
    parser.add_argument(
        "--free",
        action="store_true",
        help="Use the best available FREE model from OpenRouter (quality-focused, $0 cost)"
    )
    parser.add_argument(
        "--free-fast",
        action="store_true",
        help="Use the fastest available FREE model from OpenRouter (speed-focused, $0 cost)"
    )
    parser.add_argument(
        "--list-free-models",
        action="store_true",
        help="List all currently available free models on OpenRouter and exit"
    )
    parser.add_argument(
        "--fast-simjudged",
        action="store_true",
        help="Speed up simjudged templates: reduce candidates (7→3), forward steps (3→1), disable dialog (~10x faster)"
    )
    # New unified template system flags
    parser.add_argument(
        "--tier",
        type=str,
        choices=["quick", "standard", "comprehensive", "stress"],
        help="Run templates of a specific tier (quick=<1min, standard=1-5min, comprehensive=5-15min, stress=15min+)"
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["core", "showcase", "portal", "stress", "convergence"],
        help="Run templates from a specific category"
    )
    parser.add_argument(
        "--mechanism",
        type=str,
        metavar="M1-M18",
        help="Run templates that test a specific mechanism (e.g. M7, M15, M17)"
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List all available templates with their tier/category/mechanisms and exit"
    )
    args = parser.parse_args()

    # Handle --list-modes first (doesn't require API key)
    if args.list_modes:
        list_modes()
        sys.exit(0)

    # Handle --list-templates (doesn't require API key)
    if args.list_templates:
        from generation.templates.loader import TemplateLoader
        loader = TemplateLoader()
        templates = loader.list_templates(
            tier=args.tier,
            category=args.category,
            mechanism=args.mechanism
        )
        print("\n" + "=" * 80)
        print("TEMPLATE CATALOG")
        print("=" * 80)
        if args.tier or args.category or args.mechanism:
            filters = []
            if args.tier:
                filters.append(f"tier={args.tier}")
            if args.category:
                filters.append(f"category={args.category}")
            if args.mechanism:
                filters.append(f"mechanism={args.mechanism}")
            print(f"Filters: {', '.join(filters)}")
            print("-" * 80)
        print(f"{'ID':<40} {'TIER':<12} {'CATEGORY':<12} {'MECHANISMS':<20}")
        print("-" * 80)
        for t in sorted(templates, key=lambda x: (x.category.value, x.tier.value, x.id)):
            mechs = ", ".join(t.mechanisms[:3])
            if len(t.mechanisms) > 3:
                mechs += f" +{len(t.mechanisms)-3}"
            print(f"{t.id:<40} {t.tier.value:<12} {t.category.value:<12} {mechs:<20}")
        print("-" * 80)
        print(f"Total: {len(templates)} templates")
        print()
        sys.exit(0)

    # Verify API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        print("Checked .env file - not found or empty")
        sys.exit(1)

    print(f"✓ API keys loaded from .env")
    print()

    # Enable double-confirm handler for Ctrl+C
    # This prevents accidental interruption of expensive test runs
    enable_graceful_interrupt()
    print("🛡️  Ctrl+C protection enabled (press twice to quit)")
    print()

    # Handle --list-free-models (requires API key)
    if args.list_free_models:
        from llm import FreeModelSelector
        selector = FreeModelSelector(api_key=os.getenv("OPENROUTER_API_KEY"))
        print(selector.list_free_models())
        sys.exit(0)

    # Handle --free and --free-fast model selection
    if args.free or args.free_fast:
        from llm import FreeModelSelector
        selector = FreeModelSelector(api_key=os.getenv("OPENROUTER_API_KEY"))

        if args.free and args.free_fast:
            print("⚠️  Both --free and --free-fast specified, using --free (best quality)")

        if args.free:
            free_model = selector.get_best_free_model()
        else:
            free_model = selector.get_fastest_free_model()

        if not free_model:
            print("❌ ERROR: No free models currently available on OpenRouter")
            print("   Free models rotate availability. Try again later or use paid mode.")
            sys.exit(1)

        # Set as model override
        args.model = free_model
        os.environ["TIMEPOINT_MODEL_OVERRIDE"] = free_model
        print(f"🆓 FREE MODE: Using {free_model}")
        print(f"   Cost: $0.00 (free tier)")
        print(f"   Note: Free models have more restrictive rate limits")
        print()

    # Handle --fast-simjudged flag
    if args.fast_simjudged:
        # Set environment variables to override simjudged config defaults
        os.environ["TIMEPOINT_FAST_SIMJUDGED"] = "1"
        os.environ["TIMEPOINT_CANDIDATE_ANTECEDENTS"] = "3"  # Reduced from 7
        os.environ["TIMEPOINT_SIMULATION_FORWARD_STEPS"] = "1"  # Reduced from 3
        os.environ["TIMEPOINT_SIMULATION_INCLUDE_DIALOG"] = "false"  # Disabled
        os.environ["TIMEPOINT_MAX_SIMULATION_WORKERS"] = "6"  # Higher parallelism
        print("⚡ FAST SIMJUDGED MODE:")
        print("   candidate_antecedents_per_step: 3 (was 7)")
        print("   simulation_forward_steps: 1 (was 3)")
        print("   simulation_include_dialog: DISABLED")
        print("   max_simulation_workers: 6 (parallel)")
        print("   Expected speedup: ~10x")
        print()

    # Handle --template mode (single template execution)
    if args.template and not args.convergence_e2e:
        from run_single_template import run_single_template
        success = run_single_template(args.template, skip_summaries=args.skip_summaries)
        sys.exit(0 if success else 1)

    # Handle --convergence-e2e mode (run template N times, compute convergence)
    if args.convergence_e2e:
        if not args.template:
            print("❌ ERROR: --convergence-e2e requires --template")
            print("   Example: --convergence-e2e --template board_meeting --convergence-runs 3")
            sys.exit(1)

        success = run_convergence_e2e(
            template_name=args.template,
            run_count=args.convergence_runs,
            skip_summaries=args.skip_summaries,
            verbose=args.convergence_verbose,
            model_override=args.model
        )
        sys.exit(0 if success else 1)

    # Handle --nl mode (natural language simulation)
    if args.nl:
        success = run_nl_simulation(
            nl_input=args.nl,
            skip_summaries=args.skip_summaries,
            entities=args.nl_entities,
            timepoints=args.nl_timepoints
        )
        sys.exit(0 if success else 1)

    # Show deprecation warning if old flag is used
    if args.timepoint_corporate_analysis_only:
        print("\n⚠️  DEPRECATION WARNING")
        print("   --timepoint-corporate-analysis-only is deprecated.")
        print("   Please use --timepoint-forward instead.")
        print("   (Continuing with timepoint_corporate mode...)\n")

    # Determine mode
    if args.ultra_all:
        mode = 'ultra_all'
    elif args.portal_test_only:
        mode = 'portal'
    elif args.portal_simjudged_quick_only:
        mode = 'portal_simjudged_quick'
    elif args.portal_simjudged_only:
        mode = 'portal_simjudged'
    elif args.portal_simjudged_thorough_only:
        mode = 'portal_simjudged_thorough'
    elif args.portal_all:
        mode = 'portal_all'
    elif args.portal_timepoint_only:
        mode = 'portal_timepoint'
    elif args.portal_timepoint_simjudged_quick_only:
        mode = 'portal_timepoint_simjudged_quick'
    elif args.portal_timepoint_simjudged_only:
        mode = 'portal_timepoint_simjudged'
    elif args.portal_timepoint_simjudged_thorough_only:
        mode = 'portal_timepoint_simjudged_thorough'
    elif args.portal_timepoint_all:
        mode = 'portal_timepoint_all'
    elif args.timepoint_forward or args.timepoint_corporate_analysis_only:
        mode = 'timepoint_corporate'
    elif args.timepoint_all:
        mode = 'timepoint_all'
    elif args.full:
        mode = 'full'
    else:
        mode = 'quick'

    # Handle --convergence-only mode (no simulation runs)
    if args.convergence_only:
        convergence_success = run_convergence_analysis(
            run_count=args.convergence_runs,
            template_filter=args.convergence_template,
            verbose=args.convergence_verbose
        )
        sys.exit(0 if convergence_success else 1)

    success = run_all_templates(mode, skip_summaries=args.skip_summaries, parallel_workers=args.parallel)

    # Run convergence analysis if requested
    if args.convergence:
        convergence_success = run_convergence_analysis(
            run_count=args.convergence_runs,
            template_filter=args.convergence_template,
            verbose=args.convergence_verbose
        )
        if not convergence_success:
            print("\n⚠️  Convergence analysis failed but template runs may have succeeded")

    sys.exit(0 if success else 1)
