from supabase import create_client, Client
from config import settings
from typing import List, Optional, Dict, Any
from models.raw_event import RawEvent
from models.entity import Entity
from models.edge import Edge
from models.chunk import Chunk
from models.embedding import Embedding
from models.signal import Signal
from models.insight import Insight
from models.dismissed_pattern import DismissedPattern
from models.entity_with_signal import EntityWithSignal
from models.entity_relationship import EntityRelationships, EntityRelationshipItem
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
        try:
            query = self.client.table("entity").select("*").ilike("title", f"%{title}%")
            if entity_type:
                query = query.eq("type", entity_type)
            response = query.limit(1).execute()
            return Entity(**response.data[0]) if response.data else None
        except Exception as e:
            logger.error(f"Error getting entity by title: {e}")
            return None

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

    def get_chunks_by_entity_id(self, entity_id: str) -> List[Chunk]:
        """Get all chunks for an entity"""
        response = (
            self.client.table("chunk").select("*").eq("entity_id", entity_id).execute()
        )
        return [Chunk(**chunk) for chunk in response.data] if response.data else []

    # Embeddings
    def create_embedding(self, embedding_data: dict):
        """Create embedding for chunk"""
        self.client.table("embedding").insert(embedding_data).execute()

    def get_embeddings_by_chunk_id(self, chunk_id: str) -> List[Embedding]:
        """Get embeddings for a chunk"""
        response = (
            self.client.table("embedding").select("*").eq("chunk_id", chunk_id).execute()
        )
        return [Embedding(**emb) for emb in response.data] if response.data else []

    # Signals
    def create_signal(self, signal_data: dict):
        """Create or update signal for entity (upsert)"""
        self.client.table("signal").upsert(signal_data).execute()

    def get_signal_by_entity_id(self, entity_id: str) -> Optional[Signal]:
        """Get signal for entity"""
        response = (
            self.client.table("signal")
            .select("*")
            .eq("entity_id", entity_id)
            .maybe_single()
            .execute()
        )
        return Signal(**response.data) if response.data else None

    def update_signal(self, entity_id: str, updates: dict):
        """Update signal scores"""
        self.client.table("signal").update(updates).eq("entity_id", entity_id).execute()

    # Insights
    def get_insight_by_id(self, insight_id: str) -> Optional[Insight]:
        """Get insight by ID"""
        response = (
            self.client.table("insight")
            .select("*")
            .eq("id", insight_id)
            .single()
            .execute()
        )
        return Insight(**response.data) if response.data else None

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

    def get_recent_entities(self, limit: int = 20) -> List[Entity]:
        """
        Fetch recent entities for entity resolution

        Args:
            limit: Maximum number of entities to return

        Returns:
            List of Entity objects
        """
        try:
            response = self.client.table("entity").select(
                "*"
            ).order("created_at", desc=True).limit(limit).execute()

            return [Entity(**e) for e in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error fetching recent entities: {e}")
            return []

    def search_entities_by_title(self, search_term: str, limit: int = 5) -> List[Entity]:
        """
        Search for entities by title (case-insensitive partial match)

        Args:
            search_term: Text to search for in entity titles
            limit: Maximum number of results to return

        Returns:
            List of matching Entity objects
        """
        try:
            response = (
                self.client.table("entity")
                .select("*")
                .ilike("title", f"%{search_term}%")
                .limit(limit)
                .execute()
            )
            return [Entity(**e) for e in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error searching entities by title: {e}")
            return []

    # Mentor Agent Methods
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all entities of a specific type"""
        try:
            response = self.client.table("entity").select("*").eq(
                "type", entity_type
            ).execute()
            return [Entity(**e) for e in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error fetching entities by type {entity_type}: {e}")
            return []

    def get_entities_created_since(self, since: datetime) -> List[Entity]:
        """Get entities created after a specific time"""
        try:
            response = (
                self.client.table("entity")
                .select("*")
                .gte("created_at", since.isoformat())
                .order("created_at", desc=True)
                .execute()
            )
            return [Entity(**e) for e in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error fetching entities since {since}: {e}")
            return []

    def get_entities_by_signal_threshold(
        self, importance_min: float = None, recency_min: float = None, limit: int = 20
    ) -> List[EntityWithSignal]:
        """
        Get entities with signals above thresholds

        Note: Supabase doesn't support filtering on joined tables directly,
        so we fetch and filter in Python
        """
        try:
            # Fetch entities with their signals
            response = (
                self.client.table("entity")
                .select("*, signal(*)")
                .limit(limit * 3)  # Over-fetch to account for filtering
                .execute()
            )

            entities = response.data or []

            # Filter based on signals
            filtered = []
            for entity_data in entities:
                signal_data = entity_data.get("signal")

                # Signal can be either a dict or a list of dicts
                if not signal_data:
                    continue

                # If it's a list, take the first item
                if isinstance(signal_data, list):
                    if len(signal_data) == 0:
                        continue
                    signal_data = signal_data[0]

                # Now signal should be a dict
                if not isinstance(signal_data, dict):
                    continue

                # Apply threshold filters
                if importance_min is not None and signal_data.get("importance", 0) < importance_min:
                    continue
                if recency_min is not None and signal_data.get("recency", 0) < recency_min:
                    continue

                # Create EntityWithSignal object
                entity_data["signal"] = signal_data
                filtered.append(EntityWithSignal(**entity_data))

            return filtered[:limit]
        except Exception as e:
            logger.error(f"Error fetching entities by signal threshold: {e}")
            return []

    def get_dismissed_patterns(self, days_back: int = 30) -> List[DismissedPattern]:
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

            return [DismissedPattern(**p) for p in response.data] if response.data else []
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

    def get_recent_insights(self, limit: int = 10, status: str = None) -> List[Insight]:
        """Get recent insights, optionally filtered by status"""
        try:
            query = self.client.table("insight").select("*")

            if status:
                query = query.eq("status", status)

            response = query.order("created_at", desc=True).limit(limit).execute()
            return [Insight(**i) for i in response.data] if response.data else []
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
    ) -> List[Entity]:
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
                .eq("type", entity.type)
                .lt("created_at", cutoff.isoformat())
                .neq("id", entity_id)
                .limit(limit)
                .execute()
            )

            return [Entity(**e) for e in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error fetching similar entities: {e}")
            return []

    def get_entity_relationships(self, entity_id: str, limit: int = 10) -> EntityRelationships:
        """
        Get all entities connected to this entity via edges

        Returns:
            EntityRelationships with outgoing and incoming relationship items
        """
        try:
            # Get outgoing edges (from this entity)
            outgoing_response = (
                self.client.table("edge")
                .select("*, to:entity!edge_to_id_fkey(*)")
                .eq("from_id", entity_id)
                .limit(limit)
                .execute()
            )

            # Get incoming edges (to this entity)
            incoming_response = (
                self.client.table("edge")
                .select("*, from:entity!edge_from_id_fkey(*)")
                .eq("to_id", entity_id)
                .limit(limit)
                .execute()
            )

            outgoing = []
            for edge_data in outgoing_response.data or []:
                to_entity_data = edge_data.pop("to", None)
                if to_entity_data:
                    outgoing.append(EntityRelationshipItem(
                        edge=Edge(**edge_data),
                        entity=Entity(**to_entity_data)
                    ))

            incoming = []
            for edge_data in incoming_response.data or []:
                from_entity_data = edge_data.pop("from", None)
                if from_entity_data:
                    incoming.append(EntityRelationshipItem(
                        edge=Edge(**edge_data),
                        entity=Entity(**from_entity_data)
                    ))

            return EntityRelationships(outgoing=outgoing, incoming=incoming)
        except Exception as e:
            logger.error(f"Error fetching entity relationships for {entity_id}: {e}")
            return EntityRelationships(outgoing=[], incoming=[])

    def get_entities_by_importance(self, min_importance: float = 0.7, limit: int = 10) -> List[EntityWithSignal]:
        """
        Get top entities by importance score

        Args:
            min_importance: Minimum importance threshold
            limit: Maximum number of results

        Returns:
            List of EntityWithSignal objects sorted by importance descending
        """
        try:
            response = (
                self.client.table("entity")
                .select("*, signal(*)")
                .limit(limit * 2)  # Over-fetch for filtering
                .execute()
            )

            entities = response.data or []

            # Filter and sort by importance
            filtered = []
            for entity_data in entities:
                signal_data = entity_data.get("signal")

                if isinstance(signal_data, list):
                    if len(signal_data) == 0:
                        continue
                    signal_data = signal_data[0]

                if not isinstance(signal_data, dict):
                    continue

                importance = signal_data.get("importance", 0)
                if importance < min_importance:
                    continue

                entity_data["signal"] = signal_data
                filtered.append(EntityWithSignal(**entity_data))

            # Sort by importance descending
            filtered.sort(key=lambda e: e.signal.importance, reverse=True)

            return filtered[:limit]
        except Exception as e:
            logger.error(f"Error fetching entities by importance: {e}")
            return []

    @staticmethod
    def now():
        """Return current timestamp"""
        return datetime.now()


db = DatabaseService()
