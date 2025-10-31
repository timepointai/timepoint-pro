#!/usr/bin/env python3.10
"""
Backfill Narrative Exports for Existing Completed Runs

This script regenerates narrative summaries (MD/JSON/PDF) for runs
that completed before the narrative export feature was implemented.

Usage:
    python scripts/backfill_narrative_exports.py --dry-run  # Preview
    python scripts/backfill_narrative_exports.py --run-ids run_001 run_002  # Specific runs
    python scripts/backfill_narrative_exports.py --all  # All completed runs
    python scripts/backfill_narrative_exports.py --all --formats markdown json  # Specific formats only
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metadata.run_tracker import MetadataManager, RunMetadata
from metadata.narrative_exporter import NarrativeExporter


def backfill_run(
    run_metadata: RunMetadata,
    exporter: NarrativeExporter,
    formats: List[str],
    detail_level: str,
    dry_run: bool
) -> Optional[Dict[str, str]]:
    """
    Backfill narrative exports for a single run.

    Args:
        run_metadata: Metadata for the run to backfill
        exporter: NarrativeExporter instance
        formats: List of formats to generate
        detail_level: Detail level for exports
        dry_run: If True, only print what would be done

    Returns:
        Dictionary mapping format to file path (None if dry_run)
    """
    print(f"\n{'='*80}")
    print(f"Run: {run_metadata.run_id}")
    print(f"Template: {run_metadata.template_id}")
    print(f"Started: {run_metadata.started_at}")
    print(f"Status: {run_metadata.status}")
    print(f"{'='*80}")

    if dry_run:
        print(f"[DRY RUN] Would generate: {', '.join(formats)}")
        print(f"[DRY RUN] Detail level: {detail_level}")
        return None

    # Collect run data from metadata only (no GraphStore access)
    # This creates limited narratives but works for historical runs
    narrative_data = exporter.collect_run_data(
        run_metadata=run_metadata,
        timepoints=[],  # Historical data not available
        entities=[],    # Historical data not available
        store=None,     # GraphStore not available for old runs
        training_data=None,
        config=None
    )

    # Generate timestamp for files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = Path("datasets") / run_metadata.template_id
    base_path.mkdir(parents=True, exist_ok=True)

    exported_files = {}

    for format_name in formats:
        try:
            output_file = base_path / f"narrative_backfill_{timestamp}_{run_metadata.run_id}.{format_name}"

            if format_name == "markdown":
                path = exporter.export_markdown(narrative_data, output_file, detail_level)
                print(f"  ✓ Markdown: {path.name} ({path.stat().st_size} bytes)")
            elif format_name == "json":
                path = exporter.export_json(narrative_data, output_file)
                print(f"  ✓ JSON: {path.name} ({path.stat().st_size} bytes)")
            elif format_name == "pdf":
                try:
                    path = exporter.export_pdf(narrative_data, output_file, detail_level)
                    print(f"  ✓ PDF: {path.name} ({path.stat().st_size} bytes)")
                except ImportError:
                    print(f"  ⚠️  PDF skipped: reportlab not installed")
                    continue

            exported_files[format_name] = str(path)

        except Exception as e:
            print(f"  ❌ Export failed for {format_name}: {e}")
            # Continue with other formats

    return exported_files if exported_files else None


def main():
    parser = argparse.ArgumentParser(description="Backfill narrative exports for existing runs")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without actually generating files"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all completed runs"
    )
    parser.add_argument(
        "--run-ids",
        nargs="+",
        help="Specific run IDs to process"
    )
    parser.add_argument(
        "--template",
        type=str,
        help="Filter by template ID"
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["markdown", "json", "pdf"],
        choices=["markdown", "json", "pdf"],
        help="Formats to generate (default: all)"
    )
    parser.add_argument(
        "--detail-level",
        type=str,
        default="summary",
        choices=["minimal", "summary", "comprehensive"],
        help="Detail level for exports (default: summary)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip runs that already have narrative exports"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.run_ids:
        parser.error("Either --all or --run-ids must be specified")

    print(f"{'='*80}")
    print(f"NARRATIVE EXPORT BACKFILL")
    print(f"{'='*80}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Formats: {', '.join(args.formats)}")
    print(f"Detail Level: {args.detail_level}")
    print(f"{'='*80}\n")

    # Initialize metadata manager
    metadata_mgr = MetadataManager()

    # Get runs to process
    if args.all:
        if args.template:
            print(f"Loading all completed runs for template: {args.template}...")
            all_runs = metadata_mgr.get_all_runs(template_id=args.template)
        else:
            print(f"Loading all completed runs...")
            all_runs = metadata_mgr.get_all_runs()

        # Filter to completed runs only
        runs_to_process = [r for r in all_runs if r.status == "completed"]
        print(f"Found {len(runs_to_process)} completed runs (out of {len(all_runs)} total)")

    else:
        print(f"Loading {len(args.run_ids)} specific runs...")
        runs_to_process = []
        for run_id in args.run_ids:
            try:
                run = metadata_mgr.get_run(run_id)
                runs_to_process.append(run)
            except ValueError:
                print(f"  ⚠️  Run not found: {run_id}")

    # Filter out runs that already have narratives (if requested)
    if args.skip_existing:
        before_count = len(runs_to_process)
        runs_to_process = [
            r for r in runs_to_process
            if not r.narrative_exports or not r.narrative_exports
        ]
        skipped = before_count - len(runs_to_process)
        if skipped > 0:
            print(f"Skipped {skipped} runs that already have narrative exports")

    if not runs_to_process:
        print("\n❌ No runs to process")
        return

    print(f"\n📋 Processing {len(runs_to_process)} runs...\n")

    # Initialize exporter
    exporter = NarrativeExporter()

    # Process each run
    successful = 0
    failed = 0

    for idx, run_metadata in enumerate(runs_to_process, 1):
        print(f"\n[{idx}/{len(runs_to_process)}] Processing {run_metadata.run_id}...")

        try:
            exported_files = backfill_run(
                run_metadata,
                exporter,
                args.formats,
                args.detail_level,
                args.dry_run
            )

            if exported_files and not args.dry_run:
                # Update database with export paths
                metadata_mgr.update_narrative_exports(run_metadata.run_id, exported_files)
                print(f"  ✓ Database updated with export paths")
                successful += 1
            elif not args.dry_run:
                print(f"  ⚠️  No exports generated")
                failed += 1

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed += 1
            # Continue with next run

    # Summary
    print(f"\n{'='*80}")
    print(f"BACKFILL COMPLETE")
    print(f"{'='*80}")
    if not args.dry_run:
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {len(runs_to_process)}")
    else:
        print(f"[DRY RUN] Would process {len(runs_to_process)} runs")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
