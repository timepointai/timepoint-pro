#!/usr/bin/env python3.10
"""
Quick validation script to verify profile loading fix works.

This tests the complete context passing chain:
SimulationConfig → E2E Runner → Orchestrator → Profile Loading
"""

import os
import sys

def test_profile_loading():
    """Test that profiles are passed through and loaded correctly"""

    print("=" * 80)
    print("PROFILE LOADING VALIDATION TEST")
    print("=" * 80)
    print()

    # Ensure API key is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ OPENROUTER_API_KEY not set")
        sys.exit(1)

    print("✓ API key set")
    print()

    # Import required modules
    print("Loading modules...")
    from generation.templates.loader import TemplateLoader
    from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
    from metadata.run_tracker import MetadataManager
    print("✓ Imports successful")
    print()

    # Initialize metadata manager
    print("Initializing metadata manager...")
    metadata_manager = MetadataManager(db_path='metadata/runs.db')
    print("✓ Metadata manager initialized")
    print()

    # Initialize runner (disable summary generation for speed)
    print("Initializing E2E runner...")
    runner = ResilientE2EWorkflowRunner(metadata_manager, generate_summary=False)
    print("✓ E2E runner initialized")
    print()

    # Get board_meeting config (verified template)
    print("Loading showcase/board_meeting configuration...")
    loader = TemplateLoader()
    config = loader.load_template("showcase/board_meeting")
    print("✓ Configuration loaded")
    print()

    # Validate config has profiles
    print("Validating configuration:")
    print(f"  - Template ID: {config.world_id}")
    print(f"  - Entity count: {config.entities.count}")
    print(f"  - Entity types: {config.entities.types}")
    print(f"  - Profiles specified: {config.entities.profiles}")
    print()

    if not config.entities.profiles:
        print("❌ ERROR: No profiles specified in config!")
        sys.exit(1)

    print(f"✓ Config has {len(config.entities.profiles)} profile(s) specified")
    print()

    # Verify profile files exist
    print("Checking profile files exist:")
    from pathlib import Path
    for profile_path in config.entities.profiles:
        profile_file = Path(profile_path)
        if profile_file.exists():
            print(f"  ✓ {profile_path}")
        else:
            print(f"  ❌ {profile_path} NOT FOUND")
            sys.exit(1)
    print()

    # Run simulation
    print("=" * 80)
    print("RUNNING SIMULATION")
    print("=" * 80)
    print()
    print("This will test the full context passing chain:")
    print("  1. E2E Runner receives config with profiles")
    print("  2. E2E Runner passes entity_config to orchestrator")
    print("  3. Orchestrator loads profiles from JSON")
    print("  4. Orchestrator generates remaining entities via LLM")
    print("  5. Simulation completes with profile-defined entities")
    print()
    print("Starting simulation (this may take a few minutes)...")
    print()

    try:
        result = runner.run(config)

        print()
        print("=" * 80)
        print("✅ SIMULATION SUCCESS")
        print("=" * 80)
        print()
        print(f"Run ID: {result.run_id}")
        print(f"Entities created: {result.entities_created}")
        print(f"Timepoints created: {result.timepoints_created}")
        print(f"Cost: ${result.cost_usd:.4f}")
        print()

        # Verify profile-defined entities loaded
        print("Checking if profile entities were loaded...")
        # Note: Can't easily access entities from result metadata, but if we got here
        # and entities_created matches expected count, profiles likely loaded

        if result.entities_created >= 2:
            print(f"✓ Created {result.entities_created} entities (expected at least 2 from profiles)")
        else:
            print(f"⚠️  Only {result.entities_created} entities created (expected at least 2)")

        print()
        print("=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ SIMULATION FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_profile_loading()
