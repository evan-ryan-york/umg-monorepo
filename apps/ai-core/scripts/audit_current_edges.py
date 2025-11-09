#!/usr/bin/env python3
"""
Audit current edge state before implementing Relationship Engine.
This provides baseline metrics to compare against after implementation.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.database import DatabaseService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def audit_edges():
    """Audit current edge state in the database"""
    db = DatabaseService()

    print("\n" + "="*80)
    print("EDGE AUDIT - Current State Before Relationship Engine")
    print("="*80)

    # Query 1: Total edges and entities
    print("\n1. TOTAL COUNTS:")
    print("-" * 80)

    try:
        entity_count = db.client.table("entity").select("id", count="exact").execute()
        edge_count = db.client.table("edge").select("id", count="exact").execute()

        print(f"   Total entities: {entity_count.count}")
        print(f"   Total edges: {edge_count.count}")
        print(f"   Average edges per entity: {edge_count.count / entity_count.count if entity_count.count > 0 else 0:.2f}")
    except Exception as e:
        print(f"   Error getting counts: {e}")

    # Query 2: All relationship types
    print("\n2. RELATIONSHIP TYPES (kind):")
    print("-" * 80)

    try:
        result = db.client.table("edge").select("kind").execute()
        kind_counts = {}
        for row in result.data:
            kind = row['kind']
            kind_counts[kind] = kind_counts.get(kind, 0) + 1

        # Sort by count descending
        for kind, count in sorted(kind_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {kind:30s} : {count:5d} edges")

        print(f"\n   Total distinct relationship types: {len(kind_counts)}")
    except Exception as e:
        print(f"   Error getting relationship types: {e}")

    # Query 3: Check for role→organization edges (THE BUG)
    print("\n3. ROLE → ORGANIZATION EDGES (Testing the bug):")
    print("-" * 80)

    try:
        # Get all role entities
        role_entities = db.client.table("entity").select("id, title").eq("type", "role").execute()
        print(f"   Total role entities: {len(role_entities.data)}")

        # Get all organization entities
        org_entities = db.client.table("entity").select("id, title").eq("type", "organization").execute()
        print(f"   Total organization entities: {len(org_entities.data)}")

        # Check for edges between roles and organizations
        if role_entities.data:
            role_ids = [r['id'] for r in role_entities.data]
            org_ids = [o['id'] for o in org_entities.data]

            # Query edges from role to organization
            role_to_org = db.client.table("edge").select("*").in_("from_id", role_ids).in_("to_id", org_ids).execute()

            print(f"\n   Edges from role → organization: {len(role_to_org.data)}")

            if len(role_to_org.data) > 0:
                print("\n   Sample role→org edges:")
                for i, edge in enumerate(role_to_org.data[:5]):
                    # Get entity titles
                    from_entity = db.get_entity_by_id(edge['from_id'])
                    to_entity = db.get_entity_by_id(edge['to_id'])
                    print(f"     {i+1}. {from_entity.title if from_entity else 'Unknown'} --{edge['kind']}--> {to_entity.title if to_entity else 'Unknown'}")
            else:
                print("\n   ❌ BUG CONFIRMED: No role→organization edges found!")
                print("   This is the primary issue the Relationship Engine will fix.")

                # Show sample roles that should have org connections
                print("\n   Sample role entities (should have organization edges):")
                for i, role in enumerate(role_entities.data[:5]):
                    print(f"     {i+1}. {role['title']}")

    except Exception as e:
        print(f"   Error checking role→org edges: {e}")

    # Query 4: Entity types distribution
    print("\n4. ENTITY TYPES DISTRIBUTION:")
    print("-" * 80)

    try:
        result = db.client.table("entity").select("type").execute()
        type_counts = {}
        for row in result.data:
            entity_type = row['type']
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

        # Sort by count descending
        for entity_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {entity_type:20s} : {count:5d} entities")
    except Exception as e:
        print(f"   Error getting entity types: {e}")

    # Query 5: Check for edges with metadata
    print("\n5. EDGE METADATA:")
    print("-" * 80)

    try:
        # Check if any edges have metadata
        edges_with_metadata = db.client.table("edge").select("metadata").neq("metadata", {}).execute()
        print(f"   Edges with non-empty metadata: {len(edges_with_metadata.data)}")

        # Check for temporal data
        edges_with_dates = db.client.table("edge").select("start_date, end_date").not_.is_("start_date", "null").execute()
        print(f"   Edges with start_date: {len(edges_with_dates.data)}")

        ongoing_edges = db.client.table("edge").select("start_date, end_date").not_.is_("start_date", "null").is_("end_date", "null").execute()
        print(f"   Ongoing edges (start_date but no end_date): {len(ongoing_edges.data)}")
    except Exception as e:
        print(f"   Error checking edge metadata: {e}")

    # Query 6: Check schema for new columns
    print("\n6. SCHEMA CHECK (columns needed for Relationship Engine):")
    print("-" * 80)

    try:
        # Check if weight and last_reinforced_at columns exist
        sample_edge = db.client.table("edge").select("*").limit(1).execute()
        if sample_edge.data:
            columns = sample_edge.data[0].keys()

            has_weight = 'weight' in columns
            has_last_reinforced = 'last_reinforced_at' in columns

            print(f"   Has 'weight' column: {'✅ YES' if has_weight else '❌ NO (needs migration)'}")
            print(f"   Has 'last_reinforced_at' column: {'✅ YES' if has_last_reinforced else '❌ NO (needs migration)'}")

            print("\n   Current edge columns:")
            for col in sorted(columns):
                print(f"     - {col}")
    except Exception as e:
        print(f"   Error checking schema: {e}")

    print("\n" + "="*80)
    print("AUDIT COMPLETE")
    print("="*80 + "\n")


if __name__ == '__main__':
    audit_edges()
