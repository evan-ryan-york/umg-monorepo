from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from models.signal import Signal


class EntityWithSignal(BaseModel):
    """Entity with its associated signal data - used for queries that join entity and signal tables"""
    id: str
    source_event_id: str
    type: str
    title: str
    summary: str
    metadata: Dict[str, Any] = {}
    uri: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    signal: Signal  # Associated signal data

    class Config:
        from_attributes = True
