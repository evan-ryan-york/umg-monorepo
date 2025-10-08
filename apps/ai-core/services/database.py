from supabase import create_client, Client
from config import settings
from typing import List, Optional, Dict, Any
from models.raw_event import RawEvent
from models.entity import Entity
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


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

    def get_entity_by_title(self, title: str, entity_type: Optional[str] = None) -> Optional[Entity]:
        """Get entity by title (case-insensitive), optionally filtered by type"""
        query = self.client.table("entity").select("*").ilike("title", title)
        if entity_type:
            query = query.eq("type", entity_type)
        response = query.limit(1).execute()
        return Entity(**response.data[0]) if response.data else None

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

    def create_spoke_entity(self, hub_entity_id: str, spoke_data: dict, source_event_id: str = None) -> str:
        """Create spoke entity linked to hub (e.g., meeting_note about Feed)"""
        spoke_id = self.create_entity(spoke_data)

        # Create edge from spoke to hub
        edge_data = {
            "from_id": spoke_id,
            "to_id": hub_entity_id,
            "kind": "relates_to",
            "metadata": {"relationship": "spoke_to_hub"},
        }

        if source_event_id:
            edge_data["source_event_id"] = source_event_id

        self.create_edge(edge_data)

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

    def get_recent_entities(self, limit: int = 20) -> List[dict]:
        """
        Fetch recent entities for entity resolution

        Args:
            limit: Maximum number of entities to return

        Returns:
            List of entity dictionaries with basic info
        """
        try:
            response = self.client.table("entity").select(
                "id, title, type, created_at, updated_at, metadata"
            ).order("created_at", desc=True).limit(limit).execute()

            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching recent entities: {e}")
            return []

    def get_entity_by_title(self, title: str, entity_type: str = None) -> Optional[dict]:
        """
        Get entity by title (case-insensitive)

        Args:
            title: Entity title to search for
            entity_type: Optional type filter

        Returns:
            Entity dict or None
        """
        try:
            query = self.client.table("entity").select("*").ilike("title", f"%{title}%")

            if entity_type:
                query = query.eq("type", entity_type)

            response = query.limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting entity by title: {e}")
            return None

    # Mentor Agent Methods
    def get_entities_by_type(self, entity_type: str) -> List[Dict]:
        """Get all entities of a specific type"""
        try:
            response = self.client.table("entity").select("*").eq(
                "type", entity_type
            ).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching entities by type {entity_type}: {e}")
            return []

    def get_entities_created_since(self, since: datetime) -> List[Dict]:
        """Get entities created after a specific time"""
        try:
            response = (
                self.client.table("entity")
                .select("*")
                .gte("created_at", since.isoformat())
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching entities since {since}: {e}")
            return []

    def get_entities_by_signal_threshold(
        self, importance_min: float = None, recency_min: float = None, limit: int = 20
    ) -> List[Dict]:
        """
        Get entities with signals above thresholds

        Note: Supabase doesn't support filtering on joined tables directly,
        so we fetch and filter in Python
        """
        try:
            # Fetch entities with their signals
            response = (
                self.client.table("entity")
                .select("id, title, type, summary, metadata, created_at, signal(*)")
                .limit(limit * 3)  # Over-fetch to account for filtering
                .execute()
            )

            entities = response.data or []

            # Filter based on signals
            filtered = []
            for entity in entities:
                signal = entity.get("signal")

                # Signal can be either a dict or a list of dicts
                if not signal:
                    continue

                # If it's a list, take the first item
                if isinstance(signal, list):
                    if len(signal) == 0:
                        continue
                    signal = signal[0]

                # Now signal should be a dict
                if not isinstance(signal, dict):
                    continue

                # Apply threshold filters
                if importance_min is not None and signal.get("importance", 0) < importance_min:
                    continue
                if recency_min is not None and signal.get("recency", 0) < recency_min:
                    continue

                # Keep signal as dict in entity
                entity["signal"] = signal
                filtered.append(entity)

            return filtered[:limit]
        except Exception as e:
            logger.error(f"Error fetching entities by signal threshold: {e}")
            return []

    def get_dismissed_patterns(self, days_back: int = 30) -> List[Dict]:
        """Get dismissed patterns from last N days"""
        try:
            cutoff = datetime.now() - timedelta(days=days_back)

            response = (
                self.client.table("dismissed_patterns")
                .select("*")
                .gte("last_dismissed_at", cutoff.isoformat())
                .order("last_dismissed_at", desc=True)
                .execute()
            )

            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching dismissed patterns: {e}")
            return []

    def create_insight(self, insight_data: dict) -> str:
        """Create new insight, return ID"""
        try:
            response = self.client.table("insight").insert(insight_data).execute()
            return response.data[0]["id"]
        except Exception as e:
            logger.error(f"Error creating insight: {e}")
            raise

    def get_recent_insights(self, limit: int = 10, status: str = None) -> List[Dict]:
        """Get recent insights, optionally filtered by status"""
        try:
            query = self.client.table("insight").select("*")

            if status:
                query = query.eq("status", status)

            response = query.order("created_at", desc=True).limit(limit).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching recent insights: {e}")
            return []

    def update_insight_status(self, insight_id: str, status: str):
        """Update insight status"""
        try:
            self.client.table("insight").update({"status": status}).eq(
                "id", insight_id
            ).execute()
        except Exception as e:
            logger.error(f"Error updating insight status: {e}")
            raise

    def get_similar_entities(
        self, entity_id: str, limit: int = 5, exclude_recent_days: int = 30
    ) -> List[Dict]:
        """
        Find similar entities (placeholder - needs embeddings)

        For now, use simple heuristic: same type, older than X days
        """
        try:
            entity = self.get_entity_by_id(entity_id)
            if not entity:
                return []

            cutoff = datetime.now() - timedelta(days=exclude_recent_days)

            response = (
                self.client.table("entity")
                .select("*")
                .eq("type", entity["type"])
                .lt("created_at", cutoff.isoformat())
                .neq("id", entity_id)
                .limit(limit)
                .execute()
            )

            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching similar entities: {e}")
            return []

    @staticmethod
    def now():
        """Return current timestamp"""
        return datetime.now()


db = DatabaseService()
