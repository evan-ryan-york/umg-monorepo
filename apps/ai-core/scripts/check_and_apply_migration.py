#!/usr/bin/env python3
"""
Check and Apply Relationship Engine Migration

This script checks if the migration columns exist and provides instructions
for applying the migration via Supabase dashboard.

Since Supabase Python client doesn't support raw SQL execution, the migration
must be applied through the Supabase SQL Editor.

Usage:
    python scripts/check_and_apply_migration.py
"""

import sys
import os

# Add ai-core to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.database import DatabaseService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_migration_status():
    """Check if the migration has been applied."""

    print("\n" + "=" * 70)
    print("Relationship Engine Migration Checker")
    print("=" * 70)

    try:
        # Initialize database
        logger.info("Connecting to database...")
        db = DatabaseService()

        # Get a sample edge to check schema
        logger.info("Checking edge table schema...")
        edges = db.get_all_edges()

        if not edges or len(edges) == 0:
            print("\n⚠️  No edges found in database. Unable to check schema.")
            print("Migration status: UNKNOWN\n")
            return None

        # Check first edge for new columns
        sample_edge = edges[0]

        has_weight = hasattr(sample_edge, 'weight')
        has_last_reinforced = hasattr(sample_edge, 'last_reinforced_at')

        print("\n📊 Current Edge Table Schema:")
        print(f"   - weight column: {'✅ EXISTS' if has_weight else '❌ MISSING'}")
        print(f"   - last_reinforced_at column: {'✅ EXISTS' if has_last_reinforced else '❌ MISSING'}")

        if has_weight and has_last_reinforced:
            print("\n✅ Migration has been applied successfully!")

            # Show sample values
            if has_weight:
                print(f"\n   Sample edge weight: {getattr(sample_edge, 'weight', 'N/A')}")
            if has_last_reinforced:
                print(f"   Sample last_reinforced_at: {getattr(sample_edge, 'last_reinforced_at', 'N/A')}")

            print("\n🎉 Your database is ready for the Relationship Engine!")
            return True

        else:
            print("\n❌ Migration has NOT been applied yet.")
            print("\n" + "=" * 70)
            print("How to Apply the Migration")
            print("=" * 70)
            print("\n1. Open Supabase Dashboard:")
            print("   https://app.supabase.com/")
            print("\n2. Navigate to SQL Editor:")
            print("   Project → SQL Editor → New Query")
            print("\n3. Copy the migration SQL:")
            print("   File: docs/migrations/add_relationship_engine_columns.sql")
            print("\n4. Paste into SQL Editor and click 'Run'")
            print("\n5. Re-run this script to verify")
            print("\n" + "=" * 70)

            # Show the migration file path
            migration_path = os.path.join(
                os.path.dirname(__file__),
                '..', '..', '..',
                'docs', 'migrations', 'add_relationship_engine_columns.sql'
            )
            abs_path = os.path.abspath(migration_path)

            print(f"\n📄 Migration file location:")
            print(f"   {abs_path}")

            # Offer to display the SQL
            print("\n" + "-" * 70)
            print("Display migration SQL? (y/n): ", end='')
            response = input().strip().lower()

            if response == 'y':
                print("\n" + "=" * 70)
                print("Migration SQL")
                print("=" * 70 + "\n")

                with open(migration_path, 'r') as f:
                    print(f.read())

                print("\n" + "=" * 70)

            return False

    except Exception as e:
        logger.error(f"Error checking migration status: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        return None


def main():
    status = check_migration_status()

    if status is True:
        print("\nℹ️  Next steps:")
        print("   1. Test the RelationshipEngine")
        print("   2. Process an event and verify edge weights are tracked")
        print("   3. Run nightly consolidation to test edge reinforcement\n")
        sys.exit(0)
    elif status is False:
        print("\n⚠️  Migration required before using RelationshipEngine")
        print("   Please apply the migration using the instructions above.\n")
        sys.exit(1)
    else:
        print("\n⚠️  Unable to determine migration status")
        print("   Please check database connection and try again.\n")
        sys.exit(2)


if __name__ == '__main__':
    main()
