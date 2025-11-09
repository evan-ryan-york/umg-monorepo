#!/usr/bin/env python3
"""
Simple migration verification without user prompts
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.database import DatabaseService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify():
    print("\n" + "=" * 70)
    print("Relationship Engine Migration Verification")
    print("=" * 70)

    try:
        db = DatabaseService()
        logger.info("Connected to database")

        # Get all edges
        edges = db.get_all_edges()

        if not edges or len(edges) == 0:
            print("\n⚠️  No edges found in database")
            print("Migration status: UNKNOWN (no data to check)\n")
            return None

        print(f"\n✓ Found {len(edges)} edges in database")

        # Check first edge for columns
        sample = edges[0]

        has_weight = hasattr(sample, 'weight')
        has_last_reinforced = hasattr(sample, 'last_reinforced_at')

        print("\n📊 Edge Table Schema:")
        print(f"   - weight column: {'✅ EXISTS' if has_weight else '❌ MISSING'}")
        print(f"   - last_reinforced_at column: {'✅ EXISTS' if has_last_reinforced else '❌ MISSING'}")

        if has_weight and has_last_reinforced:
            print("\n✅ Migration SUCCESSFUL!")

            # Show sample values
            print(f"\n   Sample edge:")
            print(f"   - ID: {sample.id[:16]}...")
            print(f"   - Kind: {sample.kind}")
            if has_weight:
                weight_val = getattr(sample, 'weight', None)
                print(f"   - Weight: {weight_val}")
            if has_last_reinforced:
                reinforced_val = getattr(sample, 'last_reinforced_at', None)
                print(f"   - Last reinforced: {reinforced_val}")

            print("\n🎉 Database is ready for RelationshipEngine!")
            return True

        else:
            print("\n❌ Migration NOT applied")
            print("\nPlease apply the migration via Supabase dashboard:")
            print("  File: docs/migrations/add_relationship_engine_columns.sql")
            return False

    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        return None

if __name__ == '__main__':
    result = verify()
    print("\n" + "=" * 70 + "\n")

    if result is True:
        sys.exit(0)
    elif result is False:
        sys.exit(1)
    else:
        sys.exit(2)
