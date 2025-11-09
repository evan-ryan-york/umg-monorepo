#!/usr/bin/env python3
"""
Apply Relationship Engine Database Migration

Adds 'weight' and 'last_reinforced_at' columns to the edge table
to support Hebbian learning and edge reinforcement.

This script reads the migration SQL file and applies it to the database.

Usage:
    python scripts/apply_relationship_engine_migration.py [--dry-run]

Options:
    --dry-run    Show what would be executed without actually applying changes
"""

import sys
import os
import argparse

# Add ai-core to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.database import DatabaseService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_migration_file():
    """Read the migration SQL file."""
    migration_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..',
        'docs', 'migrations', 'add_relationship_engine_columns.sql'
    )

    with open(migration_path, 'r') as f:
        return f.read()


def split_sql_statements(sql: str) -> list:
    """
    Split SQL into individual statements, handling DO blocks specially.

    Returns list of (statement, description) tuples.
    """
    statements = []
    current = []
    in_do_block = False

    lines = sql.split('\n')

    for line in lines:
        # Skip comments and empty lines at statement boundaries
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            if not current:  # Skip leading comments
                continue
            # Keep comments within statements
            current.append(line)
            continue

        # Track DO blocks
        if 'DO $$' in line or 'DO $' in line:
            in_do_block = True

        current.append(line)

        # End of statement
        if in_do_block and '$$;' in line:
            # End of DO block
            statements.append(('\n'.join(current), 'Verification DO block'))
            current = []
            in_do_block = False
        elif not in_do_block and line.strip().endswith(';'):
            # Regular statement
            stmt = '\n'.join(current)

            # Determine description
            if 'ALTER TABLE' in stmt:
                if 'weight' in stmt:
                    desc = 'Add weight column'
                else:
                    desc = 'Add last_reinforced_at column'
            elif 'CREATE INDEX' in stmt:
                desc = f"Create index"
            elif 'COMMENT' in stmt:
                desc = 'Add column comment'
            elif 'UPDATE' in stmt:
                desc = 'Backfill existing edges'
            else:
                desc = 'Execute statement'

            statements.append((stmt, desc))
            current = []

    return statements


def check_columns_exist(db: DatabaseService) -> dict:
    """Check if migration columns already exist."""
    try:
        # Query to check if columns exist
        result = db.supabase.rpc('check_edge_columns', {}).execute()

        # If RPC doesn't exist, query directly
        query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'edge'
        AND column_name IN ('weight', 'last_reinforced_at')
        """

        # Execute via a simple edge query and check fields
        edges = db.get_all_edges()

        has_weight = False
        has_last_reinforced = False

        if edges and len(edges) > 0:
            first_edge = edges[0]
            has_weight = hasattr(first_edge, 'weight')
            has_last_reinforced = hasattr(first_edge, 'last_reinforced_at')

        return {
            'weight': has_weight,
            'last_reinforced_at': has_last_reinforced
        }
    except Exception as e:
        logger.warning(f"Could not check existing columns: {e}")
        return {'weight': False, 'last_reinforced_at': False}


def apply_migration(dry_run: bool = False):
    """Apply the database migration."""

    print("\n" + "=" * 60)
    print("Relationship Engine Database Migration")
    print("=" * 60)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Initialize database service
    logger.info("Connecting to database...")
    db = DatabaseService()

    # Check current state
    logger.info("Checking current edge table schema...")
    existing = check_columns_exist(db)

    print("\nCurrent schema:")
    print(f"  - weight column: {'✅ EXISTS' if existing['weight'] else '❌ MISSING'}")
    print(f"  - last_reinforced_at column: {'✅ EXISTS' if existing['last_reinforced_at'] else '❌ MISSING'}")

    if existing['weight'] and existing['last_reinforced_at']:
        print("\n✅ Migration appears to be already applied!")
        print("\nRun verification anyway? (y/n): ", end='')
        response = input().strip().lower()
        if response != 'y':
            print("\nMigration skipped.")
            return True

    # Read migration SQL
    logger.info("Reading migration file...")
    sql = read_migration_file()

    # Split into statements
    statements = split_sql_statements(sql)

    print(f"\nFound {len(statements)} SQL statements to execute:")
    for i, (stmt, desc) in enumerate(statements, 1):
        print(f"  {i}. {desc}")

    if dry_run:
        print("\n--- SQL Statements (dry-run) ---")
        for i, (stmt, desc) in enumerate(statements, 1):
            print(f"\n-- Statement {i}: {desc}")
            print(stmt)
        print("\n✅ Dry run complete. Use without --dry-run to apply.")
        return True

    # Confirm before applying
    print("\n⚠️  Ready to apply migration. Continue? (y/n): ", end='')
    response = input().strip().lower()

    if response != 'y':
        print("\nMigration cancelled.")
        return False

    # Apply migration
    print("\nApplying migration...")

    success_count = 0
    for i, (stmt, desc) in enumerate(statements, 1):
        try:
            print(f"  [{i}/{len(statements)}] {desc}...", end=' ')

            # Use Supabase PostgREST to execute raw SQL
            # Note: This requires the database to have appropriate RPC functions
            # or we need to use a different approach

            # For now, we'll try to execute via the underlying client
            result = db.supabase.postgrest.rpc('exec_sql', {'sql': stmt}).execute()

            print("✅")
            success_count += 1

        except Exception as e:
            print(f"❌ Failed: {e}")
            logger.error(f"Failed to execute statement {i}: {e}")

            # Ask whether to continue
            print(f"\nContinue with remaining statements? (y/n): ", end='')
            response = input().strip().lower()
            if response != 'y':
                print("\nMigration stopped.")
                return False

    print(f"\n✅ Successfully executed {success_count}/{len(statements)} statements")

    # Verify migration
    print("\nVerifying migration...")
    existing = check_columns_exist(db)

    if existing['weight'] and existing['last_reinforced_at']:
        print("✅ Migration verified successfully!")
        print(f"  - weight column: ✅ EXISTS")
        print(f"  - last_reinforced_at column: ✅ EXISTS")
        return True
    else:
        print("⚠️  Migration verification failed!")
        print(f"  - weight column: {'✅' if existing['weight'] else '❌'}")
        print(f"  - last_reinforced_at column: {'✅' if existing['last_reinforced_at'] else '❌'}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Apply Relationship Engine database migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be executed without making changes'
    )

    args = parser.parse_args()

    try:
        success = apply_migration(dry_run=args.dry_run)

        if success:
            print("\n" + "=" * 60)
            print("Migration Complete!")
            print("=" * 60)
            print("\nNext steps:")
            print("  1. Test the RelationshipEngine with new columns")
            print("  2. Process a test event to verify edge creation")
            print("  3. Check edge weights are being tracked\n")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("Migration Failed or Incomplete")
            print("=" * 60)
            print("\nPlease review errors above and retry.\n")
            print("Manual migration via Supabase dashboard:")
            print("  1. Go to Supabase SQL Editor")
            print("  2. Copy SQL from: docs/migrations/add_relationship_engine_columns.sql")
            print("  3. Execute in SQL Editor\n")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Migration failed with error: {e}", exc_info=True)
        print(f"\n❌ Migration failed: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
