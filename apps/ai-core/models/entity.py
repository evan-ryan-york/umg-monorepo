from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class Entity(BaseModel):
    id: str
    source_event_id: str
    type: str  # 'project', 'feature', 'task', 'person', 'company', 'meeting_note', 'reflection', 'decision', 'core_identity', 'reference_document'
    title: str
    summary: str
    metadata: Dict[str, Any] = {}
    uri: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
