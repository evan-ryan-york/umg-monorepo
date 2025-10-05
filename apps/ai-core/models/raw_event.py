from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class RawEventPayload(BaseModel):
    type: str  # 'text', 'voice', 'webhook'
    content: str
    metadata: Dict[str, Any] = {}


class RawEvent(BaseModel):
    id: str
    payload: RawEventPayload
    source: str
    status: str  # 'pending_triage', 'pending_processing', 'processed', 'ignored'
    created_at: datetime

    class Config:
        from_attributes = True
