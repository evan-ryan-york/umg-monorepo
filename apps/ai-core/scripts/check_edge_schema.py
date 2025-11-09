#!/usr/bin/env python3
"""
Check the actual edge schema returned by Supabase
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.database import DatabaseService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = DatabaseService()

# Get edges with explicit column selection
edges = db.get_all_edges()

if edges and len(edges) > 0:
    edge = edges[0]

    print("\n" + "=" * 70)
    print("Edge Object Attributes")
    print("=" * 70)

    # Show all attributes
    attrs = dir(edge)
    print(f"\nAll attributes ({len(attrs)}):")

    # Filter to show just data attributes (not methods)
    data_attrs = [a for a in attrs if not a.startswith('_') and not callable(getattr(edge, a, None))]

    for attr in sorted(data_attrs):
        value = getattr(edge, attr, None)
        # Truncate long values
        str_value = str(value)
        if len(str_value) > 60:
            str_value = str_value[:60] + "..."
        print(f"  {attr:25} = {str_value}")

    print("\n" + "=" * 70)

    # Check specifically for weight and last_reinforced_at
    print("\nChecking for migration columns:")
    print(f"  hasattr(edge, 'weight'): {hasattr(edge, 'weight')}")
    print(f"  hasattr(edge, 'last_reinforced_at'): {hasattr(edge, 'last_reinforced_at')}")

    # Try to access them
    print("\nAttempting to access:")
    try:
        w = edge.weight
        print(f"  edge.weight = {w}")
    except AttributeError as e:
        print(f"  edge.weight → AttributeError: {e}")

    try:
        lr = edge.last_reinforced_at
        print(f"  edge.last_reinforced_at = {lr}")
    except AttributeError as e:
        print(f"  edge.last_reinforced_at → AttributeError: {e}")

    print("\n" + "=" * 70)
