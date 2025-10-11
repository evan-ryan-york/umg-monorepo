"""
Chat models for Mentor conversational interface.
"""

from pydantic import BaseModel
from typing import List, Optional


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    """Request to chat with Mentor."""
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    user_entity_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from Mentor chat."""
    response: str
    user_event_id: str  # ID of saved user message in raw_events
    assistant_event_id: str  # ID of saved assistant response in raw_events
    entities_mentioned: List[str]  # Quick preview of entities found
    context_used: Optional[dict] = None  # What context was used (for debugging)
