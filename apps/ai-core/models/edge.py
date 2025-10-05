from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime


class Edge(BaseModel):
    id: str
    from_id: str
    to_id: str
    kind: str  # 'belongs_to', 'modifies', 'mentions', 'informs', 'blocks', 'contradicts', 'relates_to'
    metadata: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True
