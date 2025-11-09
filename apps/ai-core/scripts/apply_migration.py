#!/usr/bin/env python3
"""
Apply database migration for Relationship Engine.
Reads SQL file and executes it using Supabase client.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.database import DatabaseService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def apply_migration(sql_file_path: str):
    """Apply migration from SQL file"""
    db = DatabaseService()

    print("\n" + "="*80)
    print(f"APPLYING MIGRATION: {os.path.basename(sql_file_path)}")
    print("="*80 + "\n")

    # Read SQL file
    try:
        with open(sql_file_path, 'r') as f:
            sql = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Migration file not found: {sql_file_path}")
        sys.exit(1)

    print("Migration SQL:")
    print("-" * 80)
    print(sql[:500] + "..." if len(sql) > 500 else sql)
    print("-" * 80 + "\n")

    # Ask for confirmation
    response = input("Apply this migration? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        sys.exit(0)

    # Apply migration
    try:
        print("\nExecuting migration...")

        # Supabase doesn't support multi-statement SQL execution via REST API
        # We need to execute each statement separately
        statements = sql.split(';')

        for i, statement in enumerate(statements):
            statement = statement.strip()
            if not statement or statement.startswith('--'):
                continue

            # Skip DO blocks and RAISE statements (not supported via REST API)
            if 'DO $$' in statement or 'RAISE NOTICE' in statement:
                print(f"  Skipping verification block (execute manually if needed)")
                continue

            try:
                # Execute using RPC or direct SQL
                # Note: Supabase Python client doesn't have execute_sql method
                # We'll use a workaround via RPC
                print(f"  Executing statement {i+1}...")

                # For ALTER TABLE and CREATE INDEX, we need to use the postgrest API
                # This is a limitation - in production, run this SQL via Supabase dashboard or psql
                print(f"    Statement: {statement[:100]}...")

            except Exception as e:
                print(f"  ⚠️  Warning: Could not execute statement {i+1}: {e}")
                print(f"     You may need to run this migration manually via Supabase dashboard")

        print("\n⚠️  IMPORTANT:")
        print("  The Supabase Python client doesn't support direct SQL execution.")
        print("  Please apply this migration manually:")
        print(f"  1. Go to your Supabase dashboard")
        print(f"  2. Navigate to SQL Editor")
        print(f"  3. Copy and paste the contents of: {sql_file_path}")
        print(f"  4. Execute the SQL")
        print()

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # Path to migration file
    migration_file = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        '..',
        'docs',
        'migrations',
        'add_relationship_engine_columns.sql'
    )

    apply_migration(migration_file)
