from fastapi import FastAPI, HTTPException
from config import settings
from agents.archivist import Archivist
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
