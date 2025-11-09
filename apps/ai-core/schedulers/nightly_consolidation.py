"""
Nightly Consolidation Scheduler

Runs the RelationshipEngine in nightly mode during idle hours to:
- Find cross-event relationships using expensive strategies
- Apply global decay to all edge weights
- Prune weak, unreinforced edges
- Implement the NREM sleep analog for graph maintenance

This is the "offline processing" phase that mirrors hippocampal-neocortical
dialogue during sleep (see brain-reference.md Section 2.5).
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from engines.relationship_engine import RelationshipEngine
import logging
import sys

logger = logging.getLogger(__name__)


def run_nightly_consolidation():
    """
    Runs the RelationshipEngine in nightly mode.

    This is the main consolidation job that:
    1. Analyzes entities created/updated in the last 24 hours
    2. Runs all 5 detection strategies (including expensive ones)
    3. Applies global decay to edge weights
    4. Prunes weak edges below threshold

    Called automatically at 3 AM daily.
    """
    logger.info("=" * 60)
    logger.info("Starting nightly consolidation job")
    logger.info("=" * 60)

    try:
        engine = RelationshipEngine()

        # Run nightly mode (analyzes last 24 hours by default)
        result = engine.run_nightly(full_scan=False)

        logger.info("Nightly consolidation complete:")
        logger.info(f"  - Entities analyzed: {result['entities_analyzed']}")
        logger.info(f"  - Edges created: {result['edges_created']}")
        logger.info(f"  - Edges updated (reinforced): {result['edges_updated']}")
        logger.info(f"  - Edges pruned: {result['edges_pruned']}")
        logger.info(f"  - Processing time: {result['processing_time']:.2f}s")
        logger.info("=" * 60)

        return result

    except Exception as e:
        logger.error(f"Nightly consolidation failed: {e}", exc_info=True)
        # Don't raise - we don't want to crash the scheduler
        return {
            'status': 'error',
            'error': str(e)
        }


def start_scheduler(run_immediately: bool = False):
    """
    Start the background scheduler for nightly consolidation.

    Args:
        run_immediately: If True, run once immediately for testing

    Returns:
        APScheduler BackgroundScheduler instance
    """
    scheduler = BackgroundScheduler()

    # Schedule nightly job at 3 AM
    scheduler.add_job(
        run_nightly_consolidation,
        trigger=CronTrigger(hour=3, minute=0),  # 3:00 AM daily
        id='nightly_consolidation',
        name='Nightly Consolidation (RelationshipEngine)',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Nightly consolidation scheduler started (runs at 3:00 AM daily)")

    # Optionally run immediately for testing
    if run_immediately:
        logger.info("Running nightly consolidation immediately (test mode)")
        run_nightly_consolidation()

    return scheduler


def stop_scheduler(scheduler):
    """
    Stop the background scheduler.

    Args:
        scheduler: APScheduler BackgroundScheduler instance
    """
    scheduler.shutdown()
    logger.info("Nightly consolidation scheduler stopped")


if __name__ == '__main__':
    """
    Run this script directly to test the nightly consolidation job.

    Usage:
        python schedulers/nightly_consolidation.py
    """
    import time

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 60)
    print("Nightly Consolidation Test")
    print("=" * 60)
    print("\nRunning RelationshipEngine in nightly mode...\n")

    result = run_nightly_consolidation()

    if result.get('status') == 'error':
        print(f"\n❌ Consolidation failed: {result.get('error')}")
        sys.exit(1)
    else:
        print("\n✅ Consolidation successful!")
        print(f"\nResults:")
        print(f"  Entities analyzed: {result['entities_analyzed']}")
        print(f"  Edges created: {result['edges_created']}")
        print(f"  Edges updated: {result['edges_updated']}")
        print(f"  Edges pruned: {result['edges_pruned']}")
        print(f"  Processing time: {result['processing_time']:.2f}s")
        print("\n" + "=" * 60)
