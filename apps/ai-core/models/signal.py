from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Signal(BaseModel):
    entity_id: str
    importance: float  # 0.0 to 1.0
    recency: float  # 0.0 to 1.0
    novelty: float  # 0.0 to 1.0
    last_surfaced_at: Optional[datetime] = None

    class Config:
        from_attributes = True
