from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DismissedPattern(BaseModel):
    id: str
    insight_type: str  # 'Delta Watch', 'Connection', 'Prompt', etc.
    pattern: str  # Description of the pattern
    last_dismissed_at: datetime
    dismiss_count: int = 1

    class Config:
        from_attributes = True
