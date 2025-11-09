#!/usr/bin/env python3
"""
Manual Trigger Script for RelationshipEngine

This script allows you to manually trigger the RelationshipEngine in different modes
for testing, debugging, or one-time analysis.

Usage:
    # Run incremental mode for a specific event
    python scripts/run_relationship_engine.py --mode incremental --event-id <event_id>

    # Run nightly mode (last 24 hours)
    python scripts/run_relationship_engine.py --mode nightly

    # Run nightly mode with full scan
    python scripts/run_relationship_engine.py --mode nightly --full-scan

    # Run on-demand mode for specific entities
    python scripts/run_relationship_engine.py --mode on-demand --entity-ids <id1> <id2> <id3>

    # Run on-demand mode for entire graph
    python scripts/run_relationship_engine.py --mode on-demand --all
"""

import sys
import os
import argparse
import json

# Add ai-core to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engines.relationship_engine import RelationshipEngine
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_incremental(event_id: str):
    """Run incremental mode for a specific event."""
    print(f"\n{'='*60}")
    print(f"Running Incremental Mode for event: {event_id}")
    print(f"{'='*60}\n")

    engine = RelationshipEngine()
    result = engine.run_incremental(event_id)

    print_result(result)
    return result


def run_nightly(full_scan: bool = False):
    """Run nightly mode."""
    scan_type = "full scan" if full_scan else "last 24 hours"
    print(f"\n{'='*60}")
    print(f"Running Nightly Mode ({scan_type})")
    print(f"{'='*60}\n")

    engine = RelationshipEngine()
    result = engine.run_nightly(full_scan=full_scan)

    print_result(result)
    return result


def run_on_demand(entity_ids: list = None):
    """Run on-demand mode."""
    if entity_ids:
        print(f"\n{'='*60}")
        print(f"Running On-Demand Mode for {len(entity_ids)} entities")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"Running On-Demand Mode (entire graph)")
        print(f"{'='*60}\n")

    engine = RelationshipEngine()
    result = engine.run_on_demand(entity_ids=entity_ids)

    print_result(result)
    return result


def print_result(result: dict):
    """Pretty print the result."""
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)

    if 'edges_created' in result:
        print(f"✓ Edges created: {result['edges_created']}")
    if 'edges_updated' in result:
        print(f"✓ Edges updated (reinforced): {result['edges_updated']}")
    if 'edges_pruned' in result:
        print(f"✓ Edges pruned: {result['edges_pruned']}")
    if 'entities_analyzed' in result:
        print(f"✓ Entities analyzed: {result['entities_analyzed']}")
    if 'processing_time' in result:
        print(f"✓ Processing time: {result['processing_time']:.2f}s")
    if 'strategies_used' in result:
        print(f"✓ Strategies used: {', '.join(result['strategies_used'])}")

    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Manually trigger RelationshipEngine in different modes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--mode',
        choices=['incremental', 'nightly', 'on-demand'],
        required=True,
        help='Mode to run the RelationshipEngine in'
    )

    parser.add_argument(
        '--event-id',
        help='Event ID for incremental mode'
    )

    parser.add_argument(
        '--entity-ids',
        nargs='+',
        help='Entity IDs for on-demand mode'
    )

    parser.add_argument(
        '--full-scan',
        action='store_true',
        help='Run full scan in nightly mode (default: last 24 hours)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Analyze entire graph in on-demand mode'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output result as JSON'
    )

    args = parser.parse_args()

    try:
        # Run appropriate mode
        if args.mode == 'incremental':
            if not args.event_id:
                print("Error: --event-id required for incremental mode")
                sys.exit(1)
            result = run_incremental(args.event_id)

        elif args.mode == 'nightly':
            result = run_nightly(full_scan=args.full_scan)

        elif args.mode == 'on-demand':
            entity_ids = args.entity_ids if not args.all else None
            result = run_on_demand(entity_ids=entity_ids)

        # Output JSON if requested
        if args.json:
            print(json.dumps(result, indent=2))

        sys.exit(0)

    except Exception as e:
        logger.error(f"Failed to run RelationshipEngine: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
