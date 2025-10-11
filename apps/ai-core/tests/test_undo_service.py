"""
Test suite for UndoService - smart deletion with cross-event entity references

Tests the three-tier deletion logic:
1. Event-only deletion: Remove event but preserve referenced entities
2. Reference removal: Decrement mention counts for shared entities
3. Entity deletion: Only delete entities with no other references
"""

import pytest
from services.undo_service import UndoService
from services.database import DatabaseService
from uuid import uuid4
from datetime import datetime


@pytest.fixture
def db():
    """Database service fixture"""
    return DatabaseService()


@pytest.fixture
def undo_service():
    """UndoService fixture"""
    return UndoService()


@pytest.fixture
def clean_database(db):
    """Clean up test data before each test"""
    # Note: This is a simple cleanup - in production you'd use transactions
    yield
    # Cleanup after test if needed


def create_test_event(db, content: str, user_id: str = "test_user") -> str:
    """Helper to create a test event"""
    event_data = {
        "payload": {
            "type": "text",
            "content": content,
            "metadata": {},
            "user_id": user_id,
            "user_entity_id": None
        },
        "source": "test",
        "status": "pending_processing"
    }
    return db.create_raw_event(event_data)


def create_test_entity(db, event_id: str, title: str, entity_type: str = "project") -> str:
    """Helper to create a test entity"""
    entity_data = {
        "source_event_id": event_id,
        "type": entity_type,
        "title": title,
        "summary": f"Test entity: {title}",
        "metadata": {
            "referenced_by_event_ids": [event_id],
            "mention_count": 1
        }
    }
    return db.create_entity(entity_data)


class TestUndoServiceBasic:
    """Basic functionality tests"""

    def test_delete_event_with_unique_entity(self, undo_service, db, clean_database):
        """Test Tier 3: Delete event and its unique entities"""
        # Create event with unique entity
        event_id = create_test_event(db, "Working on Project Alpha")
        entity_id = create_test_entity(db, event_id, "Project Alpha")

        # Delete event
        result = undo_service.delete_event_and_related_data(event_id)

        # Verify
        assert result['success'] is True
        assert result['entities_deleted'] == 1
        assert result['entities_preserved'] == 0

        # Entity should be deleted
        entity = db.get_entity_by_id(entity_id)
        assert entity is None

        # Event should be deleted
        event = db.get_event_by_id(event_id)
        assert event is None

    def test_delete_event_with_shared_entity(self, undo_service, db, clean_database):
        """Test Tier 1: Preserve entity referenced by multiple events"""
        # Event 1: Create "Water OS" entity
        event1_id = create_test_event(db, "Starting Water OS project")
        entity_id = create_test_entity(db, event1_id, "Water OS", "project")

        # Event 2: Reference "Water OS" again
        event2_id = create_test_event(db, "Water OS progress update")

        # Manually update entity to show it's referenced by both events
        entity = db.get_entity_by_id(entity_id)
        db.update_entity_metadata(entity_id, {
            **entity.metadata,
            "referenced_by_event_ids": [event1_id, event2_id],
            "mention_count": 2
        })

        # Delete Event 1
        result = undo_service.delete_event_and_related_data(event1_id)

        # Verify
        assert result['success'] is True
        assert result['entities_deleted'] == 0
        assert result['entities_preserved'] == 1

        # Entity should still exist
        entity = db.get_entity_by_id(entity_id)
        assert entity is not None

        # Mention count should be decremented
        assert entity.metadata['mention_count'] == 1
        assert event2_id in entity.metadata['referenced_by_event_ids']
        assert event1_id not in entity.metadata['referenced_by_event_ids']

        # Event 1 should be deleted
        event1 = db.get_event_by_id(event1_id)
        assert event1 is None

    def test_preview_deletion(self, undo_service, db, clean_database):
        """Test preview without actually deleting"""
        # Create event with entity
        event_id = create_test_event(db, "Test preview")
        entity_id = create_test_entity(db, event_id, "Preview Entity")

        # Preview deletion
        preview = undo_service.preview_deletion(event_id)

        # Verify preview
        assert preview['total_entities'] == 1
        assert preview['entities_to_delete'] == 1
        assert preview['entities_to_preserve'] == 0

        # Verify nothing was actually deleted
        entity = db.get_entity_by_id(entity_id)
        assert entity is not None

        event = db.get_event_by_id(event_id)
        assert event is not None


class TestUndoServiceCrossEventReferences:
    """Test complex cross-event reference scenarios"""

    def test_delete_first_event_preserves_entity(self, undo_service, db, clean_database):
        """
        Scenario: Event 1 creates "Water OS", Event 2 references it
        Action: Delete Event 1
        Expected: Water OS entity preserved, mention count decremented
        """
        # Event 1: "My name is Ryan York. I am starting Water OS."
        event1_id = create_test_event(db, "My name is Ryan York. I am starting Water OS.")
        ryan_id = create_test_entity(db, event1_id, "Ryan York", "person")
        water_os_id = create_test_entity(db, event1_id, "Water OS", "company")

        # Event 2: "Water OS will focus on Ghana market"
        event2_id = create_test_event(db, "Water OS will focus on Ghana market")

        # Update Water OS to show it's referenced by both events
        water_os = db.get_entity_by_id(water_os_id)
        db.update_entity_metadata(water_os_id, {
            **water_os.metadata,
            "referenced_by_event_ids": [event1_id, event2_id],
            "mention_count": 2
        })

        # Delete Event 1
        result = undo_service.delete_event_and_related_data(event1_id)

        # Water OS should be preserved
        water_os = db.get_entity_by_id(water_os_id)
        assert water_os is not None
        assert water_os.metadata['mention_count'] == 1
        assert event2_id in water_os.metadata['referenced_by_event_ids']
        assert event1_id not in water_os.metadata['referenced_by_event_ids']

        # Ryan York should be deleted (only in Event 1)
        ryan = db.get_entity_by_id(ryan_id)
        assert ryan is None

    def test_delete_second_event_deletes_entity(self, undo_service, db, clean_database):
        """
        Scenario: Event 1 creates "Water OS", Event 2 references it
        Action: Delete Event 2
        Expected: Water OS preserved but mention count decremented
        """
        # Event 1: Creates Water OS
        event1_id = create_test_event(db, "Starting Water OS")
        water_os_id = create_test_entity(db, event1_id, "Water OS", "company")

        # Event 2: References Water OS
        event2_id = create_test_event(db, "Water OS update")

        # Update Water OS
        water_os = db.get_entity_by_id(water_os_id)
        db.update_entity_metadata(water_os_id, {
            **water_os.metadata,
            "referenced_by_event_ids": [event1_id, event2_id],
            "mention_count": 2
        })

        # Delete Event 2
        result = undo_service.delete_event_and_related_data(event2_id)

        # Water OS should still exist but with decremented count
        water_os = db.get_entity_by_id(water_os_id)
        assert water_os is not None
        assert water_os.metadata['mention_count'] == 1
        assert water_os.metadata['referenced_by_event_ids'] == [event1_id]


class TestUndoServiceDemotion:
    """Test entity demotion when mention count drops below threshold"""

    def test_entity_demotion_below_threshold(self, undo_service, db, clean_database):
        """
        Scenario: Entity with 2 mentions, delete one event
        Expected: Entity demoted to metadata-only
        """
        # Event 1: Creates entity
        event1_id = create_test_event(db, "Mentioned Sarah once")
        sarah_id = create_test_entity(db, event1_id, "Sarah", "person")

        # Event 2: References entity
        event2_id = create_test_event(db, "Sarah again")

        # Update Sarah to have 2 mentions
        sarah = db.get_entity_by_id(sarah_id)
        db.update_entity_metadata(sarah_id, {
            **sarah.metadata,
            "referenced_by_event_ids": [event1_id, event2_id],
            "mention_count": 2
        })

        # Create signal for Sarah
        db.create_signal({
            "entity_id": sarah_id,
            "importance": 0.7,
            "recency": 1.0,
            "novelty": 0.5
        })

        # Delete Event 2
        result = undo_service.delete_event_and_related_data(event2_id)

        # Sarah should be preserved but demoted
        sarah = db.get_entity_by_id(sarah_id)
        assert sarah is not None
        assert sarah.metadata['mention_count'] == 1
        assert sarah.metadata.get('is_metadata_only') is True
        assert sarah.metadata.get('is_promoted') is False

        # Verify demotion stats
        assert result['entities_demoted'] == 1

        # Signal scores should be lowered
        signal = db.get_signal_by_entity_id(sarah_id)
        assert signal is not None
        assert signal['importance'] < 0.7  # Should be reduced


class TestUndoServiceEdges:
    """Test edge deletion logic"""

    def test_delete_edges_created_by_event(self, undo_service, db, clean_database):
        """
        Scenario: Event 1 creates edge between two entities
        Action: Delete Event 1
        Expected: Edge deleted even if entities are preserved
        """
        # Event 1: Create Ryan and Water OS with edge
        event1_id = create_test_event(db, "Ryan founded Water OS")
        ryan_id = create_test_entity(db, event1_id, "Ryan", "person")
        water_os_id = create_test_entity(db, event1_id, "Water OS", "company")

        # Create edge with source_event_id
        edge_data = {
            "from_id": ryan_id,
            "to_id": water_os_id,
            "kind": "founded",
            "metadata": {},
            "source_event_id": event1_id
        }
        edge_id = db.create_edge(edge_data)

        # Event 2: Reference both entities
        event2_id = create_test_event(db, "Ryan and Water OS update")

        # Update entities to be referenced by both events
        for entity_id in [ryan_id, water_os_id]:
            entity = db.get_entity_by_id(entity_id)
            db.update_entity_metadata(entity_id, {
                **entity.metadata,
                "referenced_by_event_ids": [event1_id, event2_id],
                "mention_count": 2
            })

        # Delete Event 1
        result = undo_service.delete_event_and_related_data(event1_id)

        # Both entities should be preserved
        assert db.get_entity_by_id(ryan_id) is not None
        assert db.get_entity_by_id(water_os_id) is not None

        # Edge should be deleted (it was created by Event 1)
        edges = db.client.table('edge').select('*').eq('id', edge_id).execute()
        assert len(edges.data) == 0

        # Verify stats
        assert result['edges_deleted'] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
