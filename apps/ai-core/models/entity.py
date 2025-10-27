from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class Entity(BaseModel):
    id: str
    source_event_id: str
    type: str  # See SUPPORTED_ENTITY_TYPES below
    title: str
    summary: str
    metadata: Dict[str, Any] = {}
    uri: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Supported entity types
SUPPORTED_ENTITY_TYPES = {
    # People & Organizations
    "person": "Individuals",
    "organization": "Companies, nonprofits, schools, institutions",
    "team": "Groups within organizations",

    # Work & Career
    "project": "Major initiatives",
    "product": "What you're building (formerly 'feature')",
    "role": "Job titles, positions held (e.g., 'Principal at RePublic High School')",
    "skill": "Capabilities, expertise",
    "task": "Action items",
    "goal": "Objectives you're working toward",
    "milestone": "Significant achievements/markers",

    # Knowledge & Identity
    "core_identity": "Values, mission, principles that define me, plus anything essential to understanding me",
    "concept": "Abstract ideas, frameworks, methodologies",
    "decision": "Important choices made",
    "insight": "Realizations, learnings",
    "source": "Books, articles, podcasts, research papers",

    # Temporal & Spatial
    "event": "Discrete happenings like conferences, launches, pivotal moments",
    "location": "Places that matter",

    # Captured Thoughts
    "meeting_note": "Meeting transcripts/summaries",
    "reflection": "Personal reflections, journal entries",
}

# Legacy type mapping (for backwards compatibility)
LEGACY_TYPE_MAPPING = {
    "feature": "product",  # Renamed
    "company": "organization",  # Renamed
    "reference_document": "source",  # Renamed
}
