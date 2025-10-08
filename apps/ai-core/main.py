from fastapi import FastAPI, HTTPException
from config import settings
from agents.archivist import Archivist
from agents.mentor import mentor
from services.database import DatabaseService
import logging
import threading

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="UMG AI Core",
    version="0.1.0",
    description="Archivist agent for processing raw events into structured memory graph"
)

# Initialize Archivist
archivist = Archivist()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "service": "UMG AI Core - Archivist"
    }


@app.post("/process")
async def trigger_processing(batch_size: int = 10):
    """Manually trigger Archivist processing

    Args:
        batch_size: Number of events to process in this batch (default 10)

    Returns:
        Processing results including events processed and statistics
    """
    try:
        logger.info(f"Manual processing triggered via API (batch_size={batch_size})")
        result = archivist.process_pending_events(batch_size=batch_size)
        return result
    except Exception as e:
        logger.error(f"Error in manual processing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/event/{event_id}")
async def process_single_event(event_id: str):
    """Process a specific event by ID

    Args:
        event_id: UUID of the event to process

    Returns:
        Processing results for the single event
    """
    try:
        logger.info(f"Processing single event via API: {event_id}")
        result = archivist.process_event(event_id)

        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing event {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Get current processing status and statistics

    Returns:
        Status information about the Archivist
    """
    return {
        "status": "running",
        "archivist_version": "0.1.0",
        "embeddings_model": archivist.embeddings_service.get_model_info()
    }


@app.on_event("startup")
async def startup_event():
    """Start background processing on server startup"""
    logger.info("Starting UMG AI Core - Archivist")

    # Only start continuous processing if not in development mode
    if settings.ENVIRONMENT == "production":
        def run_archivist():
            logger.info("Starting continuous background processing")
            archivist.run_continuous(interval_seconds=60)

        # Start in background thread
        thread = threading.Thread(target=run_archivist, daemon=True)
        thread.start()
        logger.info("Background processing thread started")
    else:
        logger.info("Development mode - continuous processing not started. Use /process endpoint manually.")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("Shutting down UMG AI Core - Archivist")


# Mentor Agent Endpoints

@app.post("/mentor/generate-digest")
async def generate_daily_digest():
    """Manually trigger daily digest generation

    Returns:
        {
            "status": "success",
            "insights_generated": int,
            "digest": {
                "delta_watch": insight_dict or None,
                "connection": insight_dict or None,
                "prompt": insight_dict or None
            }
        }
    """
    try:
        logger.info("Manual digest generation triggered via API")
        digest = mentor.generate_daily_digest()
        return {
            "status": "success",
            "insights_generated": digest["insights_created"],
            "digest": {
                "delta_watch": digest["delta_watch"],
                "connection": digest["connection"],
                "prompt": digest["prompt"]
            }
        }
    except Exception as e:
        logger.error(f"Error generating digest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mentor/status")
async def mentor_status():
    """Check Mentor status and recent activity

    Returns:
        {
            "status": "ready",
            "recent_insights_count": int,
            "last_digest": timestamp or None
        }
    """
    try:
        db = DatabaseService()
        recent_insights = db.get_recent_insights(limit=10)

        return {
            "status": "ready",
            "recent_insights_count": len(recent_insights),
            "last_digest": recent_insights[0]["created_at"] if recent_insights else None,
            "model": mentor.model
        }
    except Exception as e:
        logger.error(f"Error checking Mentor status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mentor/debug-context")
async def debug_context():
    """Debug endpoint to see what context Mentor is gathering"""
    from datetime import datetime, timedelta

    db = DatabaseService()

    # Get core identity
    core_identity = db.get_entities_by_type("core_identity")

    # Get recent entities (last 24h)
    yesterday = datetime.now() - timedelta(days=1)
    recent_entities = db.get_entities_created_since(yesterday)

    # Get high priority
    high_priority = db.get_entities_by_signal_threshold(importance_min=0.7, limit=20)

    # Get recent work
    recent_work = db.get_entities_by_signal_threshold(recency_min=0.8, limit=20)

    # Check raw signals
    signal_count = db.client.table("signal").select("*", count="exact").execute()
    sample_signals = db.client.table("signal").select("*").limit(5).execute()

    # Check entities with signals (raw query)
    raw_query = db.client.table("entity").select("id, title, signal(*)").limit(5).execute()

    return {
        "core_identity": {
            "count": len(core_identity),
            "entities": [{"title": e["title"], "type": e["type"], "metadata": e.get("metadata")} for e in core_identity]
        },
        "recent_entities": {
            "count": len(recent_entities),
            "entities": [{"title": e["title"], "created_at": e["created_at"]} for e in recent_entities]
        },
        "high_priority": {
            "count": len(high_priority),
            "entities": [{"title": e["title"], "importance": e.get("signal", {}).get("importance") if isinstance(e.get("signal"), dict) else None} for e in high_priority]
        },
        "recent_work": {
            "count": len(recent_work),
            "entities": [{"title": e["title"], "recency": e.get("signal", {}).get("recency") if isinstance(e.get("signal"), dict) else None} for e in recent_work]
        },
        "debug": {
            "total_signals": signal_count.count,
            "sample_signals": sample_signals.data,
            "raw_join_query": raw_query.data
        }
    }


@app.post("/mentor/seed-test-data")
async def seed_test_data():
    """Seed database with test data for Mentor testing"""
    from processors.signal_scorer import SignalScorer
    from datetime import datetime, timedelta
    from uuid import uuid4

    db = DatabaseService()
    signal_scorer = SignalScorer()
    created_entities = []

    def create_entity_with_signal(
        entity_type: str,
        title: str,
        summary: str,
        metadata: dict,
        created_at: datetime,
        importance: float,
        recency: float = None,
        novelty: float = 0.5,
    ):
        """Create an entity and its signal"""
        entity_id = str(uuid4())
        entity_data = {
            "id": entity_id,
            "type": entity_type,
            "title": title,
            "summary": summary,
            "metadata": metadata,
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
        }

        db.client.table("entity").insert(entity_data).execute()

        if recency is None:
            recency = signal_scorer.calculate_recency(
                created_at.isoformat(), datetime.now().isoformat()
            )

        signal_data = {
            "entity_id": entity_id,
            "importance": importance,
            "recency": recency,
            "novelty": novelty,
        }

        db.client.table("signal").insert(signal_data).execute()
        created_entities.append({"title": title, "type": entity_type})
        return entity_id

    now = datetime.now()

    # Core identity
    create_entity_with_signal(
        "core_identity", "Launch Water OS in Ghana by December",
        "Primary Q4 goal: Deploy Water OS pilot in Ghana with 500 active users.",
        {"tags": ["goal", "Q4", "water-os"], "priority": "high"},
        now - timedelta(days=90), 1.0, 0.3, 0.2
    )

    create_entity_with_signal(
        "core_identity", "Build robust Willow Education platform",
        "Secondary goal: Develop Willow Education app with parent-teacher features.",
        {"tags": ["goal", "willow"], "priority": "medium"},
        now - timedelta(days=60), 0.8, 0.5, 0.3
    )

    create_entity_with_signal(
        "core_identity", "Impact rooted in Equity",
        "Core value: Build solutions addressing fundamental inequities.",
        {"tags": ["value", "equity"], "importance": 1.0},
        now - timedelta(days=180), 1.0, 0.2, 0.1
    )

    # Recent work (Willow focused)
    create_entity_with_signal(
        "feature", "Feed Feature for Willow Education",
        "Building social feed for parents to see classroom updates and achievements.",
        {"project": "willow", "status": "in_progress"},
        now - timedelta(hours=18), 0.8, 1.0, 0.7
    )

    create_entity_with_signal(
        "task", "Polish Feed UI components",
        "Refining UI components for Willow feed - card layouts, animations, loading states.",
        {"project": "willow", "type": "ui", "feature": "feed"},
        now - timedelta(hours=6), 0.6, 1.0, 0.5
    )

    create_entity_with_signal(
        "task", "Real-time feed updates with WebSockets",
        "Implementing real-time updates for Willow feed using WebSockets.",
        {"project": "willow", "type": "backend", "feature": "feed"},
        now - timedelta(hours=12), 0.7, 1.0, 0.6
    )

    # Small Water OS task (creates goal drift)
    create_entity_with_signal(
        "task", "Review Ghana partnership agreements",
        "Reviewed partnership agreements with NGOs in Ghana. Flagged legal questions.",
        {"project": "water-os", "location": "ghana"},
        now - timedelta(hours=20), 0.5, 0.95, 0.4
    )

    # Historical work for Connection insights
    create_entity_with_signal(
        "feature", "Parent Notification System for Willow",
        "Built notification system for Willow. Learned push notifications need digest option to avoid overwhelm.",
        {"project": "willow", "status": "completed", "learnings": "digest_mode"},
        now - timedelta(days=120), 0.7, 0.1, 0.2
    )

    create_entity_with_signal(
        "project", "Willow User Retention Analysis",
        "Parents engage most with visual content and personalized updates about their child. Generic announcements ignored.",
        {"project": "willow", "type": "analysis", "key_insight": "personalization"},
        now - timedelta(days=90), 0.8, 0.15, 0.3
    )

    create_entity_with_signal(
        "feature", "Willow Dashboard UI Redesign",
        "Redesigned parent dashboard. In retrospect, validated functionality first before polish.",
        {"project": "willow", "type": "ui", "lesson": "premature_polish"},
        now - timedelta(days=45), 0.6, 0.25, 0.3
    )

    # High priority items
    create_entity_with_signal(
        "decision", "Focus Q4 on Water OS or Willow?",
        "Strategic decision: Water OS Ghana launch vs Willow features? Limited bandwidth.",
        {"type": "strategic", "urgency": "high"},
        now - timedelta(days=14), 0.95, 0.5, 0.7
    )

    create_entity_with_signal(
        "risk", "Water OS Ghana Launch Delays",
        "Partnership agreements and regulatory approvals delayed. December deadline at risk.",
        {"project": "water-os", "type": "risk", "severity": "high"},
        now - timedelta(days=7), 0.9, 0.7, 0.6
    )

    return {
        "status": "success",
        "entities_created": len(created_entities),
        "entities": created_entities
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
