from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime


class Insight(BaseModel):
    id: str
    title: str
    body: str
    drivers: Dict[str, Any]  # entity_ids and edge_ids
    status: str  # 'open', 'acknowledged', 'dismissed'
    created_at: datetime

    class Config:
        from_attributes = True
