#!/usr/bin/env python3
"""
Example: Oxen Branch and Workspace Management

This script demonstrates how to use the OxenClient's branch and workspace
management features for organizing experiments and model versions.

Usage:
    export OXEN_API_TOKEN=your_token_here
    python examples/oxen_branch_management.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oxen_integration import OxenClient


def main():
    print("=" * 70)
    print("OXEN BRANCH & WORKSPACE MANAGEMENT DEMO")
    print("=" * 70)
    print()

    # Initialize client
    print("Step 1: Initialize Oxen client...")
    client = OxenClient(
        namespace="realityinspector",
        repo_name="proof-the-e2e-works",
        interactive_auth=False
    )
    print("✓ Client initialized")
    print()

    # Check if repo exists
    print("Step 2: Check repository status...")
    if client.repo_exists():
        print("✓ Repository exists")
    else:
        print("✗ Repository does not exist")
        return
    print()

    # List existing branches
    print("Step 3: List existing branches...")
    try:
        branches = client.list_branches()
        print(f"✓ Found {len(branches)} branches:")
        for branch in branches[:10]:  # Show first 10
            print(f"  - {branch}")
        if len(branches) > 10:
            print(f"  ... and {len(branches) - 10} more")
    except Exception as e:
        print(f"✗ Could not list branches: {e}")
    print()

    # Get current branch
    print("Step 4: Get current branch...")
    try:
        current_branch = client.get_current_branch()
        print(f"✓ Current branch: {current_branch}")
    except Exception as e:
        print(f"✗ Could not get current branch: {e}")
    print()

    # Example: Create an experiment branch (demonstration only)
    print("Step 5: Branch creation example...")
    print("   Example: client.create_experiment_branch('temporal-reasoning-v1')")
    print("   Would create: experiments/temporal-reasoning-v1")
    print()
    print("   Example: client.create_feature_branch('new-dataset-format')")
    print("   Would create: feature/new-dataset-format")
    print()

    # List workspaces
    print("Step 6: List workspaces...")
    try:
        workspaces = client.list_workspaces()
        if workspaces:
            print(f"✓ Found {len(workspaces)} workspaces:")
            for workspace in workspaces[:5]:  # Show first 5
                workspace_id = getattr(workspace, 'id', str(workspace))
                print(f"  - {workspace_id}")
        else:
            print("✓ No active workspaces")
    except Exception as e:
        print(f"✗ Could not list workspaces: {e}")
    print()

    # Show available operations
    print("=" * 70)
    print("AVAILABLE OPERATIONS")
    print("=" * 70)
    print()
    print("Branch Operations:")
    print("  - client.create_branch(name, from_branch='main')")
    print("  - client.list_branches()")
    print("  - client.get_current_branch()")
    print("  - client.branch_exists(name)")
    print("  - client.switch_branch(name)")
    print("  - client.delete_branch(name)")
    print("  - client.merge_branch(source, target, message)")
    print()
    print("Convenience Methods:")
    print("  - client.create_feature_branch(name)")
    print("  - client.create_experiment_branch(name)")
    print()
    print("Workspace Operations:")
    print("  - client.create_workspace(workspace_id, branch='main')")
    print("  - client.list_workspaces()")
    print("  - client.delete_workspace(workspace_id)")
    print()

    # Example workflow
    print("=" * 70)
    print("EXAMPLE WORKFLOW: Experiment Branch")
    print("=" * 70)
    print()
    print("# Create experiment branch for new training run")
    print("experiment_branch = client.create_experiment_branch('temporal-reasoning-v2')")
    print()
    print("# Switch to experiment branch")
    print("client.switch_branch(experiment_branch)")
    print()
    print("# Upload training data to experiment branch")
    print("client.upload_dataset(")
    print("    file_path='training_data.jsonl',")
    print("    commit_message='Add temporal reasoning training data v2',")
    print("    dst_path='datasets/experiments/v2.jsonl'")
    print(")")
    print()
    print("# After successful training, merge back to main")
    print("client.merge_branch(")
    print("    source_branch=experiment_branch,")
    print("    target_branch='main',")
    print("    message='Merge temporal reasoning v2 experiment'")
    print(")")
    print()

    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print()
    print("Note: This demo only shows read operations.")
    print("To perform write operations (create/delete branches),")
    print("uncomment the relevant code sections and run with caution.")
    print()


if __name__ == "__main__":
    # Check for API token
    if not os.getenv("OXEN_API_TOKEN") and not os.getenv("OXEN_API_KEY"):
        print("ERROR: OXEN_API_TOKEN not set")
        print()
        print("Set your token:")
        print("  export OXEN_API_TOKEN=your_token_here")
        print()
        exit(1)

    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
