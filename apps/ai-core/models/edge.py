from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, date


class Edge(BaseModel):
    id: str
    from_id: str
    to_id: str
    kind: str  # Relationship type - see SUPPORTED_RELATIONSHIP_TYPES below

    # Temporal properties (NULL if not applicable)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Scoring (used by agents for filtering)
    confidence: float = 1.0
    importance: Optional[float] = None

    # Relationship Engine: Hebbian Learning (added 2025-11-08)
    weight: float = 1.0  # Synaptic strength - increases with reinforcement
    last_reinforced_at: Optional[datetime] = None  # Last reinforcement timestamp

    # Rich description (free-form context)
    description: Optional[str] = None

    # Flexible overflow for rare properties
    metadata: Dict[str, Any] = {}

    # Provenance
    source_event_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Supported relationship types
SUPPORTED_RELATIONSHIP_TYPES = {
    # Work & Career
    "worked_at": "Employment relationship (uses start_date, end_date, description for role)",
    "attended": "Education (uses start_date, end_date, description for degree/program)",
    "founded": "Created organizations (uses start_date, usually no end_date)",
    "led": "Leadership roles (uses start_date, end_date, description for role)",
    "participated_in": "Projects, initiatives (uses start_date, end_date)",

    # Location & Temporal
    "lived_in": "Residency (uses start_date, end_date)",

    # Knowledge & Learning
    "learned_from": "Sources of knowledge (person → source entity)",
    "achieved": "Milestones reached (uses start_date for when)",

    # Hierarchical & Structural
    "belongs_to": "Hierarchical ownership (e.g., Feature belongs_to Project)",
    "modifies": "Changes or updates (e.g., Meeting modifies Feature via rename)",
    "mentions": "Simple reference (e.g., Note mentions Person)",
    "informs": "Knowledge transfer (e.g., Research informs Decision)",

    # Dependencies & Conflicts
    "blocks": "Dependencies (e.g., Task blocks another Task)",
    "contradicts": "Tensions (e.g., Decision contradicts previous Strategy)",

    # General & Identity
    "relates_to": "General connection (e.g., Spoke relates_to Hub)",
    "values": "Identity relationship (Person values Core_identity)",
    "owns": "Ownership or responsibility (Person owns Goal/Project)",
    "manages": "Management relationship (Person manages Team/Project)",
    "contributes_to": "Contribution (Person contributes_to Project)",
}
