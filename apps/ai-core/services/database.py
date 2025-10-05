from supabase import create_client, Client
from config import settings
from typing import List, Optional, Dict, Any
from models.raw_event import RawEvent
from models.entity import Entity
from datetime import datetime


class DatabaseService:
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )

    # Raw Events
    def get_pending_events(self, limit: int = 10) -> List[RawEvent]:
        """Fetch events with status='pending_processing' (excludes triage and ignored)"""
        response = (
            self.client.table("raw_events")
            .select("*")
            .eq("status", "pending_processing")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )

        return [RawEvent(**event) for event in response.data]

    def get_event_by_id(self, event_id: str) -> Optional[RawEvent]:
        """Get event by ID"""
        response = (
            self.client.table("raw_events")
            .select("*")
            .eq("id", event_id)
            .single()
            .execute()
        )
        return RawEvent(**response.data) if response.data else None

    def update_event_status(self, event_id: str, status: str):
        """Update event status after processing"""
        self.client.table("raw_events").update({"status": status}).eq(
            "id", event_id
        ).execute()

    # Entities
    def create_entity(self, entity_data: dict) -> str:
        """Create new entity, return ID"""
        response = self.client.table("entity").insert(entity_data).execute()
        return response.data[0]["id"]

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        response = (
            self.client.table("entity").select("*").eq("id", entity_id).single().execute()
        )
        return Entity(**response.data) if response.data else None

    def get_entity_metadata(self, entity_id: str) -> dict:
        """Get entity metadata"""
        response = (
            self.client.table("entity")
            .select("metadata")
            .eq("id", entity_id)
            .single()
            .execute()
        )
        return response.data.get("metadata", {}) if response.data else {}

    def update_entity_metadata(self, entity_id: str, metadata: dict):
        """Update entity metadata (for aliases, etc.)"""
        self.client.table("entity").update({"metadata": metadata}).eq(
            "id", entity_id
        ).execute()

    def create_hub_entity(self, entity_data: dict) -> str:
        """Create hub entity for complex concepts (e.g., 'Feed feature')"""
        # Mark as hub in metadata
        entity_data["metadata"] = entity_data.get("metadata", {})
        entity_data["metadata"]["is_hub"] = True
        return self.create_entity(entity_data)

    def create_spoke_entity(self, hub_entity_id: str, spoke_data: dict) -> str:
        """Create spoke entity linked to hub (e.g., meeting_note about Feed)"""
        spoke_id = self.create_entity(spoke_data)

        # Create edge from spoke to hub
        self.create_edge(
            {
                "from_id": spoke_id,
                "to_id": hub_entity_id,
                "kind": "relates_to",
                "metadata": {"relationship": "spoke_to_hub"},
            }
        )

        return spoke_id

    def get_entities_by_source_event(self, event_id: str) -> List[Entity]:
        """Get all entities created from a specific event"""
        response = (
            self.client.table("entity")
            .select("*")
            .eq("source_event_id", event_id)
            .execute()
        )
        return [Entity(**entity) for entity in response.data]

    # Edges
    def create_edge(self, edge_data: dict) -> str:
        """Create new edge, return ID"""
        response = self.client.table("edge").insert(edge_data).execute()
        return response.data[0]["id"]

    def get_edge_count_for_entity(self, entity_id: str) -> int:
        """Get count of edges for an entity (both incoming and outgoing)"""
        from_count = (
            self.client.table("edge").select("id", count="exact").eq("from_id", entity_id).execute()
        )
        to_count = (
            self.client.table("edge").select("id", count="exact").eq("to_id", entity_id).execute()
        )
        return (from_count.count or 0) + (to_count.count or 0)

    # Chunks
    def create_chunk(self, chunk_data: dict) -> str:
        """Create chunk, return ID"""
        response = self.client.table("chunk").insert(chunk_data).execute()
        return response.data[0]["id"]

    def get_chunks_by_entity_id(self, entity_id: str) -> List[dict]:
        """Get all chunks for an entity"""
        response = (
            self.client.table("chunk").select("*").eq("entity_id", entity_id).execute()
        )
        return response.data

    # Embeddings
    def create_embedding(self, embedding_data: dict):
        """Create embedding for chunk"""
        self.client.table("embedding").insert(embedding_data).execute()

    def get_embeddings_by_chunk_id(self, chunk_id: str) -> List[dict]:
        """Get embeddings for a chunk"""
        response = (
            self.client.table("embedding").select("*").eq("chunk_id", chunk_id).execute()
        )
        return response.data

    # Signals
    def create_signal(self, signal_data: dict):
        """Create signal for entity"""
        self.client.table("signal").insert(signal_data).execute()

    def get_signal_by_entity_id(self, entity_id: str) -> Optional[dict]:
        """Get signal for entity"""
        response = (
            self.client.table("signal")
            .select("*")
            .eq("entity_id", entity_id)
            .maybe_single()
            .execute()
        )
        return response.data

    def update_signal(self, entity_id: str, updates: dict):
        """Update signal scores"""
        self.client.table("signal").update(updates).eq("entity_id", entity_id).execute()

    # Insights
    def get_insight_by_id(self, insight_id: str) -> dict:
        """Get insight by ID"""
        response = (
            self.client.table("insight")
            .select("*")
            .eq("id", insight_id)
            .single()
            .execute()
        )
        return response.data

    def update_insight_metadata(self, insight_id: str, metadata: dict):
        """Update insight metadata"""
        self.client.table("insight").update({"metadata": metadata}).eq(
            "id", insight_id
        ).execute()

    def record_dismissed_pattern(self, pattern: dict):
        """Record dismissed insight pattern"""
        self.client.table("dismissed_patterns").insert(pattern).execute()

    def create_raw_event(self, event_data: dict) -> str:
        """Create a new raw event (for testing)"""
        response = self.client.table("raw_events").insert(event_data).execute()
        return response.data[0]["id"]

    @staticmethod
    def now():
        """Return current timestamp"""
        return datetime.now()


db = DatabaseService()
