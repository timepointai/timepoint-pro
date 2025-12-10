#!/usr/bin/env python3
"""
Cleanup old exposure events with garbage knowledge references.

This script removes exposure events created by the naive capitalization-based
extraction that produced trash like "we'll", "thanks", "what", "i've".

Run this BEFORE deploying the new LLM-based KnowledgeExtractionAgent.

Usage:
    python scripts/cleanup_old_exposure_events.py [--dry-run] [--backup]

Options:
    --dry-run   Show what would be deleted without actually deleting
    --backup    Create backup table before deletion
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select, text
from storage import GraphStore
from schemas import ExposureEvent


def get_garbage_patterns():
    """
    Patterns that indicate garbage knowledge references.

    These were produced by the naive extract_knowledge_references() function
    that just grabbed capitalized words > 3 chars.
    """
    return [
        # Contractions (lowercased)
        "i've", "we'll", "i'll", "that's", "don't", "can't", "won't", "it's",
        "he's", "she's", "they're", "we're", "you're", "isn't", "aren't",
        "wasn't", "weren't", "hasn't", "haven't", "hadn't", "doesn't", "didn't",
        "couldn't", "wouldn't", "shouldn't", "let's", "here's", "there's",
        "what's", "who's", "how's", "where's", "when's", "why's",

        # Common sentence starters (lowercased)
        "thanks", "okay", "well", "yeah", "yes", "sure", "right", "fine",
        "good", "great", "nice", "please", "sorry", "actually", "anyway",
        "basically", "certainly", "clearly", "definitely", "exactly",
        "honestly", "obviously", "probably", "really", "seriously",
        "simply", "truly", "absolutely", "perhaps", "maybe",

        # Question words
        "what", "when", "where", "which", "while", "who", "whom", "whose",
        "however", "whatever", "whenever", "wherever", "whether",

        # Pronouns and demonstratives
        "this", "that", "these", "those", "here", "there", "everything",
        "something", "anything", "nothing", "everyone", "someone",
        "anyone", "no-one", "myself", "yourself", "himself", "herself",
        "itself", "ourselves", "themselves",

        # Common verbs at sentence start
        "think", "know", "believe", "understand", "remember", "forget",
        "consider", "suppose", "imagine", "realize", "recognize",
        "appreciate", "agree", "disagree",

        # Filler/discourse markers
        "look", "listen", "see", "note", "mind", "wait", "hold",
        "first", "second", "third", "finally", "also", "still",
        "just", "only", "even", "already", "never", "always",
    ]


def analyze_exposure_events(store: GraphStore, dry_run: bool = True):
    """Analyze exposure events for garbage patterns."""
    garbage_patterns = set(get_garbage_patterns())

    with Session(store.engine) as session:
        # Get all exposure events
        statement = select(ExposureEvent)
        events = list(session.exec(statement).all())

        print(f"\nTotal exposure events: {len(events)}")

        # Categorize
        garbage_events = []
        valid_events = []

        for event in events:
            info_lower = event.information.lower().strip()

            # Check if it matches garbage patterns
            is_garbage = (
                info_lower in garbage_patterns or
                len(info_lower) <= 4 or  # Very short = likely garbage
                info_lower.startswith("'") or  # Starts with apostrophe
                "'" in info_lower and len(info_lower) < 8  # Short contraction
            )

            if is_garbage:
                garbage_events.append(event)
            else:
                valid_events.append(event)

        print(f"Garbage events: {len(garbage_events)}")
        print(f"Valid events: {len(valid_events)}")

        if garbage_events:
            print("\nSample garbage events:")
            for event in garbage_events[:20]:
                print(f"  - '{event.information}' (from {event.source} to {event.entity_id})")

        if valid_events:
            print("\nSample valid events:")
            for event in valid_events[:10]:
                print(f"  + '{event.information[:50]}...' (from {event.source} to {event.entity_id})")

        return garbage_events, valid_events


def backup_exposure_events(store: GraphStore):
    """Create backup table of exposure events."""
    backup_table = f"exposure_event_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with Session(store.engine) as session:
        # Create backup table
        session.exec(text(f"""
            CREATE TABLE IF NOT EXISTS {backup_table} AS
            SELECT * FROM exposureevent
        """))
        session.commit()

        # Verify backup
        result = session.exec(text(f"SELECT COUNT(*) FROM {backup_table}"))
        count = result.one()[0]
        print(f"Created backup table '{backup_table}' with {count} rows")

    return backup_table


def delete_all_exposure_events(store: GraphStore, dry_run: bool = True):
    """
    Delete ALL exposure events (clean slate approach).

    Since the old extraction was fundamentally broken, it's cleaner to
    start fresh rather than try to salvage some events.
    """
    with Session(store.engine) as session:
        # Count before
        count_result = session.exec(text("SELECT COUNT(*) FROM exposureevent"))
        count = count_result.one()[0]

        if dry_run:
            print(f"\n[DRY RUN] Would delete {count} exposure events")
        else:
            # Delete all
            session.exec(text("DELETE FROM exposureevent"))
            session.commit()
            print(f"\nDeleted {count} exposure events")

            # Verify
            verify_result = session.exec(text("SELECT COUNT(*) FROM exposureevent"))
            remaining = verify_result.one()[0]
            print(f"Remaining exposure events: {remaining}")


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup old exposure events with garbage knowledge references"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup table before deletion"
    )
    parser.add_argument(
        "--db-path",
        default="metadata/runs.db",
        help="Path to database file"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Exposure Event Cleanup Script")
    print("=" * 60)
    print(f"\nDatabase: {args.db_path}")
    print(f"Dry run: {args.dry_run}")
    print(f"Backup: {args.backup}")

    # Initialize store
    store = GraphStore(f"sqlite:///{args.db_path}")

    # Analyze current state
    print("\n" + "-" * 40)
    print("ANALYSIS")
    print("-" * 40)
    garbage, valid = analyze_exposure_events(store, dry_run=args.dry_run)

    # Create backup if requested
    if args.backup and not args.dry_run:
        print("\n" + "-" * 40)
        print("BACKUP")
        print("-" * 40)
        backup_exposure_events(store)

    # Delete (clean slate approach - delete all since extraction was broken)
    print("\n" + "-" * 40)
    print("CLEANUP")
    print("-" * 40)

    if not args.dry_run:
        confirm = input("\nDelete ALL exposure events? This cannot be undone. [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    delete_all_exposure_events(store, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print("Run without --dry-run to actually delete events")
    else:
        print("CLEANUP COMPLETE")
        print("New runs will use LLM-based knowledge extraction")
    print("=" * 60)


if __name__ == "__main__":
    main()
