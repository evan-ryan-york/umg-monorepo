from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from config import settings
from agents.archivist import Archivist
from agents.mentor import mentor
from agents.feedback_processor import feedback_processor
from services.database import DatabaseService
from services.undo_service import UndoService
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

# Initialize UndoService
undo_service = UndoService()

# Scheduler removed - using dynamic context gathering instead


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "service": "UMG AI Core - Archivist"
    }


@app.post("/reset-cache")
async def reset_cache():
    """Clear the Archivist's in-memory cache

    This should be called after database reset to ensure
    the cache is in sync with the database state.

    Returns:
        Success status
    """
    try:
        logger.info("Cache reset requested via API")
        archivist.clear_cache()
        return {
            "status": "success",
            "message": "Archivist cache cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """Delete an event with smart undo logic

    Uses three-tier deletion:
    1. Preserves entities referenced by other events
    2. Decrements mention counts for shared entities
    3. Only deletes entities unique to this event

    Args:
        event_id: UUID of the event to delete

    Returns:
        Deletion statistics and details
    """
    try:
        logger.info(f"Delete request for event: {event_id}")
        result = undo_service.delete_event_and_related_data(event_id)

        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/{event_id}/preview-delete")
async def preview_delete(event_id: str):
    """Preview what would be deleted without actually deleting

    Useful for showing user what will happen before they confirm deletion

    Args:
        event_id: UUID of the event to analyze

    Returns:
        Analysis of what would be deleted
    """
    try:
        logger.info(f"Delete preview request for event: {event_id}")
        result = undo_service.preview_deletion(event_id)
        return result
    except Exception as e:
        logger.error(f"Error previewing deletion for event {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Start background processing on server startup"""
    logger.info("Starting UMG AI Core - Archivist & Mentor")

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

    # Scheduler removed - Mentor now uses dynamic context gathering instead of scheduled digests
    logger.info("Mentor using dynamic context gathering (no scheduled digests)")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("Shutting down UMG AI Core - Archivist & Mentor")


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
            "context_mode": "dynamic"
        }
    """
    try:
        db = DatabaseService()

        # Count entities and signals for context health check
        entity_count = db.client.table("entity").select("*", count="exact").execute().count
        signal_count = db.client.table("signal").select("*", count="exact").execute().count

        return {
            "status": "ready",
            "context_mode": "dynamic",
            "model": mentor.model,
            "entity_count": entity_count,
            "signal_count": signal_count
        }
    except Exception as e:
        logger.error(f"Error checking Mentor status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mentor/trigger-daily-digest")
async def trigger_daily_digest(x_api_key: str = Header(None, alias="X-API-Key")):
    """Trigger daily digest via external scheduler (e.g., cron, Vercel Cron)

    Requires API key authentication via X-API-Key header.

    Returns:
        {
            "status": "success",
            "digest_generated": true,
            "insights_created": int
        }
    """
    # Simple API key auth
    if x_api_key != settings.CRON_API_KEY:
        logger.warning(f"Unauthorized trigger attempt with key: {x_api_key[:8] if x_api_key else 'None'}...")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        logger.info("External trigger for daily digest received")
        digest = mentor.generate_daily_digest()
        return {
            "status": "success",
            "digest_generated": True,
            "insights_created": digest["insights_created"]
        }
    except Exception as e:
        logger.error(f"Error in external digest trigger: {e}", exc_info=True)
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


@app.post("/mentor/chat")
async def mentor_chat(request: dict):
    """Chat with Mentor agent

    Conversational interface that:
    - Uses knowledge graph for context-aware responses
    - Saves messages to raw_events for Archivist processing
    - Returns assistant response

    Args:
        request: {
            "message": str,
            "conversation_history": [{"role": "user"|"assistant", "content": str}],
            "user_entity_id": str (optional)
        }

    Returns:
        {
            "response": str,
            "user_event_id": str,
            "assistant_event_id": str,
            "entities_mentioned": [str],
            "context_used": {...}
        }
    """
    from models.chat import ChatMessage

    try:
        message = request.get("message")
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        # Parse conversation history
        conversation_history = []
        for msg in request.get("conversation_history", []):
            conversation_history.append(
                ChatMessage(role=msg["role"], content=msg["content"])
            )

        user_entity_id = request.get("user_entity_id")

        logger.info(f"Chat request received: {message[:50]}...")

        # Call mentor chat method
        response = mentor.chat(
            message=message,
            conversation_history=conversation_history,
            user_entity_id=user_entity_id
        )

        # Convert ChatResponse to dict
        return {
            "response": response.response,
            "user_event_id": response.user_event_id,
            "assistant_event_id": response.assistant_event_id,
            "entities_mentioned": response.entities_mentioned,
            "context_used": response.context_used
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in mentor chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


# Feedback Endpoints

class FeedbackRequest(BaseModel):
    insight_id: str

@app.post("/feedback/acknowledge")
async def acknowledge_insight(request: FeedbackRequest):
    """User acknowledged an insight as valuable

    Actions:
    - Boost importance scores for driver entities (+0.1)
    - Refresh recency scores to 1.0
    - Update insight status to 'acknowledged'

    Args:
        request: { "insight_id": "uuid" }

    Returns:
        {
            "status": "success",
            "action": "acknowledge",
            "entities_updated": int,
            "signal_changes": [...]
        }
    """
    try:
        logger.info(f"Acknowledge feedback received for insight: {request.insight_id}")
        result = feedback_processor.process_acknowledge(request.insight_id)

        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Unknown error'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing acknowledge feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback/dismiss")
async def dismiss_insight(request: FeedbackRequest):
    """User dismissed an insight as not valuable

    Actions:
    - Lower importance scores for driver entities (-0.1)
    - Record pattern to avoid in future insights
    - Update insight status to 'dismissed'

    Args:
        request: { "insight_id": "uuid" }

    Returns:
        {
            "status": "success",
            "action": "dismiss",
            "entities_updated": int,
            "pattern_recorded": {...}
        }
    """
    try:
        logger.info(f"Dismiss feedback received for insight: {request.insight_id}")
        result = feedback_processor.process_dismiss(request.insight_id)

        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Unknown error'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing dismiss feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
