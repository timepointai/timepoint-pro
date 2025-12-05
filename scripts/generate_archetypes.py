#!/usr/bin/env python3.10
"""
Archetype Tensor Generation Script
===================================

Generates archetype tensors through the REAL Timepoint tensor pipeline.

This script creates tensors for common character archetypes (CEO, Detective, etc.)
by running them through the actual LLM-guided population process - the same
process used for real entities in simulations.

Usage:
    python -m scripts.generate_archetypes [--category CATEGORY] [--regenerate]

Options:
    --category CATEGORY  Generate only specific category (corporate, detective, etc.)
    --regenerate         Regenerate even if archetypes already exist
    --dry-run            Show what would be generated without making LLM calls
    --verbose            Show detailed progress

Example:
    # Generate all archetypes
    python -m scripts.generate_archetypes

    # Generate only corporate archetypes
    python -m scripts.generate_archetypes --category corporate

    # Force regeneration of existing archetypes
    python -m scripts.generate_archetypes --regenerate
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(
        description="Generate archetype tensors through the real Timepoint pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["corporate", "detective", "historical", "medical", "generic", "all"],
        default="all",
        help="Category of archetypes to generate"
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate even if archetypes already exist in database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without making LLM calls"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Show detailed progress"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="character_engine.db",
        help="Path to tensor database"
    )

    args = parser.parse_args()

    # Import archetype modules
    from retrieval.archetype_seeds import (
        ALL_ARCHETYPES,
        CORPORATE_ARCHETYPES,
        DETECTIVE_ARCHETYPES,
        HISTORICAL_ARCHETYPES,
        MEDICAL_ARCHETYPES,
        GENERIC_ARCHETYPES,
        seed_database_with_archetypes,
        generate_all_archetype_tensors
    )
    from tensor_persistence import TensorDatabase

    # Select archetypes based on category
    category_map = {
        "corporate": CORPORATE_ARCHETYPES,
        "detective": DETECTIVE_ARCHETYPES,
        "historical": HISTORICAL_ARCHETYPES,
        "medical": MEDICAL_ARCHETYPES,
        "generic": GENERIC_ARCHETYPES,
        "all": ALL_ARCHETYPES
    }
    archetypes = category_map[args.category]

    print("=" * 60)
    print("Archetype Tensor Generation")
    print("=" * 60)
    print(f"\nCategory: {args.category}")
    print(f"Archetypes to generate: {len(archetypes)}")
    print(f"Database: {args.db_path}")
    print(f"Regenerate existing: {args.regenerate}")
    print()

    # List archetypes
    print("Archetypes:")
    for i, arch in enumerate(archetypes, 1):
        print(f"  {i}. {arch.name} ({arch.archetype_id})")
    print()

    if args.dry_run:
        print("DRY RUN - No LLM calls will be made")
        print("Use without --dry-run to actually generate tensors")
        return 0

    # Initialize database
    print(f"Initializing database at {args.db_path}...")
    tensor_db = TensorDatabase(args.db_path)

    # Initialize LLM client
    print("Initializing LLM client...")
    try:
        from llm_v2 import LLMClient
        llm_client = LLMClient()
        print(f"  Model: {llm_client.default_model}")
    except Exception as e:
        print(f"ERROR: Failed to initialize LLM client: {e}")
        print("\nMake sure you have a valid API key configured.")
        return 1

    # Generate and seed archetypes
    print("\n" + "=" * 60)
    print("Starting tensor generation through REAL pipeline...")
    print("This will make LLM API calls for each archetype.")
    print("=" * 60 + "\n")

    try:
        seeded = seed_database_with_archetypes(
            tensor_db=tensor_db,
            llm_client=llm_client,
            archetypes=archetypes,
            world_id="archetype_seeds",
            regenerate=args.regenerate,
            verbose=args.verbose
        )

        print("\n" + "=" * 60)
        print(f"Generation complete!")
        print(f"  Archetypes seeded: {seeded}/{len(archetypes)}")
        print("=" * 60)

        # Show summary
        print("\nVerifying stored archetypes...")
        for arch in archetypes:
            record = tensor_db.get_tensor(arch.archetype_id)
            if record:
                print(f"  {arch.name}: maturity={record.maturity:.2f}")
            else:
                print(f"  {arch.name}: NOT FOUND")

        return 0

    except KeyboardInterrupt:
        print("\n\nGeneration interrupted by user")
        return 130
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
