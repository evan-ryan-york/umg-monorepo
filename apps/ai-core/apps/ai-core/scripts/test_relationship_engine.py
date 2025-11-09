#!/usr/bin/env python3
"""Test script for Relationship Engine"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engines.relationship_engine import RelationshipEngine

def test_pattern_based():
    """Test pattern-based role→org detection"""
    print("\nTesting pattern-based strategy...")

    engine = RelationshipEngine()

    test_entities = [
        {'id': 'role-1', 'title': 'CTO at Willow Education', 'type': 'role', 'summary': None, 'metadata': {}},
        {'id': 'org-1', 'title': 'Willow Education', 'type': 'organization', 'summary': None, 'metadata': {}}
    ]

    relationships = engine.strategy_pattern_based(test_entities)

    print(f"Found {len(relationships)} relationship(s)")

    if len(relationships) > 0:
        for rel in relationships:
            print(f"  - {rel['kind']}: {rel['from_id']} -> {rel['to_id']}")
            print(f"    Confidence: {rel['confidence']}, Description: {rel['description']}")
        print("✅ Pattern-based strategy works!")
        return True
    else:
        print("❌ No relationships detected")
        return False

if __name__ == '__main__':
    success = test_pattern_based()
    sys.exit(0 if success else 1)
