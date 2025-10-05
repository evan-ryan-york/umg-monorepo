"""Integration tests for Archivist agent"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from agents.archivist import Archivist
from datetime import datetime
import json


class MockRawEvent:
    """Mock RawEvent for testing"""
    def __init__(self, event_id, content, source="quick_capture"):
        self.id = event_id
        self.source = source
        self.payload = {
            'type': 'text',
            'content': content,
            'metadata': {}
        }
        self.status = 'pending_processing'
        self.created_at = datetime.now()

    def get(self, key, default=None):
        return getattr(self, key, default)


class MockEntity:
    """Mock Entity for testing"""
    def __init__(self, entity_id, entity_type, title, metadata=None):
        self.id = entity_id
        self.type = entity_type
        self.title = title
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


@pytest.fixture
def mock_db():
    """Create a mock database service"""
    db = Mock()

    # Mock database methods
    db.get_event_by_id = Mock()
    db.create_entity = Mock(return_value='entity-1')
    db.create_hub_entity = Mock(return_value='hub-entity-1')
    db.create_spoke_entity = Mock(return_value='spoke-entity-1')
    db.create_edge = Mock(return_value='edge-1')
    db.create_chunk = Mock(return_value='chunk-1')
    db.create_embedding = Mock()
    db.create_signal = Mock()
    db.update_event_status = Mock()
    db.get_entity_by_id = Mock()
    db.get_entity_metadata = Mock(return_value={})
    db.update_entity_metadata = Mock()
    db.get_edge_count_for_entity = Mock(return_value=0)
    db.get_pending_events = Mock(return_value=[])

    return db


@pytest.fixture
def archivist(mock_db):
    """Create Archivist with mocked dependencies"""
    with patch('agents.archivist.DatabaseService', return_value=mock_db):
        archivist = Archivist()
        archivist.db = mock_db
        return archivist


def test_archivist_initialization():
    """Test Archivist initializes all components"""
    archivist = Archivist()

    assert archivist.db is not None
    assert archivist.text_cleaner is not None
    assert archivist.chunker is not None
    assert archivist.entity_extractor is not None
    assert archivist.mention_tracker is not None
    assert archivist.relationship_mapper is not None
    assert archivist.embeddings_service is not None
    assert archivist.signal_scorer is not None


@patch('agents.archivist.EntityExtractor')
@patch('agents.archivist.EmbeddingsService')
def test_process_event_basic_flow(mock_embeddings_cls, mock_extractor_cls, archivist, mock_db):
    """Test basic event processing flow"""
    # Setup mocks
    event = MockRawEvent(
        'event-1',
        'Had a meeting with Sarah about the Feed feature for the Willow project.'
    )
    mock_db.get_event_by_id.return_value = event

    # Mock entity extraction
    mock_extractor = Mock()
    mock_extractor.extract_entities.return_value = [
        {
            'title': 'Feed',
            'type': 'feature',
            'summary': 'Feed feature',
            'is_primary_subject': True,
            'metadata': {}
        },
        {
            'title': 'Sarah',
            'type': 'person',
            'summary': 'Team member',
            'is_primary_subject': False,
            'metadata': {}
        }
    ]
    archivist.entity_extractor = mock_extractor

    # Mock embeddings
    mock_embeddings = Mock()
    mock_embeddings.generate_embeddings_batch.return_value = [[0.1] * 1536]
    archivist.embeddings_service = mock_embeddings

    # Mock relationship mapper
    archivist.relationship_mapper.detect_relationships = Mock(return_value=[])
    archivist.relationship_mapper.detect_alias_and_update = Mock(return_value=[])

    # Mock entity fetch for signal scoring
    mock_db.get_entity_by_id.return_value = MockEntity('entity-1', 'feature', 'Feed')

    # Process event
    result = archivist.process_event('event-1')

    # Assertions
    assert result['status'] == 'success'
    assert result['event_id'] == 'event-1'
    assert result['entities_created'] >= 1
    assert 'processing_time_seconds' in result

    # Verify database calls
    mock_db.get_event_by_id.assert_called_once_with('event-1')
    mock_db.update_event_status.assert_called_with('event-1', 'processed')


@patch('agents.archivist.EntityExtractor')
@patch('agents.archivist.EmbeddingsService')
def test_process_event_with_hub_and_spoke(mock_embeddings_cls, mock_extractor_cls, archivist, mock_db):
    """Test hub-and-spoke entity creation"""
    # Setup event
    event = MockRawEvent(
        'event-1',
        'Meeting notes about the Feed feature. We discussed implementation details.',
        source='webhook_granola'
    )
    mock_db.get_event_by_id.return_value = event

    # Mock entity extraction - feature is primary subject
    mock_extractor = Mock()
    mock_extractor.extract_entities.return_value = [
        {
            'title': 'Feed',
            'type': 'feature',
            'summary': 'Feed feature',
            'is_primary_subject': True,
            'metadata': {}
        }
    ]
    archivist.entity_extractor = mock_extractor

    # Mock embeddings
    mock_embeddings = Mock()
    mock_embeddings.generate_embeddings_batch.return_value = [[0.1] * 1536]
    archivist.embeddings_service = mock_embeddings

    # Mock relationship mapper
    archivist.relationship_mapper.detect_relationships = Mock(return_value=[])
    archivist.relationship_mapper.detect_alias_and_update = Mock(return_value=[])

    # Mock entity fetch
    mock_db.get_entity_by_id.return_value = MockEntity('hub-entity-1', 'feature', 'Feed')

    # Process event
    result = archivist.process_event('event-1')

    # Assertions
    assert result['status'] == 'success'

    # Should create hub entity (feature)
    mock_db.create_hub_entity.assert_called_once()

    # Should create spoke entity (meeting_note)
    mock_db.create_spoke_entity.assert_called_once()


@patch('agents.archivist.EntityExtractor')
@patch('agents.archivist.EmbeddingsService')
def test_mention_tracking_promotion(mock_embeddings_cls, mock_extractor_cls, archivist, mock_db):
    """Test that entities are promoted after multiple mentions"""
    # Mock entity extraction
    mock_extractor = Mock()
    mock_extractor.extract_entities.return_value = [
        {
            'title': 'Sarah',
            'type': 'person',
            'summary': 'Team member',
            'is_primary_subject': False,
            'metadata': {}
        }
    ]
    archivist.entity_extractor = mock_extractor

    # Mock embeddings
    mock_embeddings = Mock()
    mock_embeddings.generate_embeddings_batch.return_value = [[0.1] * 1536]
    archivist.embeddings_service = mock_embeddings

    # Mock relationship mapper
    archivist.relationship_mapper.detect_relationships = Mock(return_value=[])
    archivist.relationship_mapper.detect_alias_and_update = Mock(return_value=[])

    # Mock entity fetch
    mock_db.get_entity_by_id.return_value = MockEntity('entity-1', 'person', 'Sarah')

    # Process multiple events mentioning Sarah
    for i in range(3):
        event = MockRawEvent(f'event-{i}', f'Event {i}: Sarah worked on the project.')
        mock_db.get_event_by_id.return_value = event
        archivist.process_event(f'event-{i}')

    # Sarah should be promoted (mentioned 3 times across 3 events)
    # Check that entity was created (promotion happened)
    assert mock_db.create_entity.call_count >= 1


@patch('agents.archivist.EntityExtractor')
@patch('agents.archivist.EmbeddingsService')
def test_alias_detection(mock_embeddings_cls, mock_extractor_cls, archivist, mock_db):
    """Test alias detection and metadata update"""
    # Setup event with rename pattern
    event = MockRawEvent(
        'event-1',
        'We renamed school-update to feed for clarity.'
    )
    mock_db.get_event_by_id.return_value = event

    # Mock entity extraction
    mock_extractor = Mock()
    mock_extractor.extract_entities.return_value = [
        {
            'title': 'feed',
            'type': 'feature',
            'summary': 'Feed feature',
            'is_primary_subject': True,
            'metadata': {}
        }
    ]
    archivist.entity_extractor = mock_extractor

    # Mock embeddings
    mock_embeddings = Mock()
    mock_embeddings.generate_embeddings_batch.return_value = [[0.1] * 1536]
    archivist.embeddings_service = mock_embeddings

    # Mock relationship mapper
    archivist.relationship_mapper.detect_relationships = Mock(return_value=[])
    archivist.relationship_mapper.detect_alias_and_update = Mock(return_value=[
        {
            'entity_id': 'entity-1',
            'old_name': 'school-update',
            'new_name': 'feed',
            'type': 'rename'
        }
    ])

    # Mock entity fetch
    mock_db.get_entity_by_id.return_value = MockEntity('entity-1', 'feature', 'feed')

    # Process event
    result = archivist.process_event('event-1')

    # Assertions
    assert result['status'] == 'success'
    assert result['aliases_updated'] >= 1


def test_process_pending_events_empty(archivist, mock_db):
    """Test batch processing with no pending events"""
    mock_db.get_pending_events.return_value = []

    result = archivist.process_pending_events()

    assert result['status'] == 'success'
    assert result['events_processed'] == 0
    assert result['events_succeeded'] == 0
    assert result['events_failed'] == 0


@patch('agents.archivist.EntityExtractor')
@patch('agents.archivist.EmbeddingsService')
def test_process_pending_events_batch(mock_embeddings_cls, mock_extractor_cls, archivist, mock_db):
    """Test batch processing multiple events"""
    # Setup pending events
    events = [
        MockRawEvent('event-1', 'Event 1 content'),
        MockRawEvent('event-2', 'Event 2 content')
    ]
    mock_db.get_pending_events.return_value = events

    # Mock entity extraction
    mock_extractor = Mock()
    mock_extractor.extract_entities.return_value = []
    archivist.entity_extractor = mock_extractor

    # Mock embeddings
    mock_embeddings = Mock()
    mock_embeddings.generate_embeddings_batch.return_value = [[0.1] * 1536]
    archivist.embeddings_service = mock_embeddings

    # Mock relationship mapper
    archivist.relationship_mapper.detect_relationships = Mock(return_value=[])
    archivist.relationship_mapper.detect_alias_and_update = Mock(return_value=[])

    # Mock get_event_by_id to return different events
    def get_event_side_effect(event_id):
        for event in events:
            if event.id == event_id:
                return event
        return None

    mock_db.get_event_by_id.side_effect = get_event_side_effect

    # Process batch
    result = archivist.process_pending_events(batch_size=10)

    # Assertions
    assert result['status'] == 'success'
    assert result['events_processed'] == 2
    assert result['events_succeeded'] == 2
    assert result['events_failed'] == 0


def test_run_continuous_with_max_iterations(archivist, mock_db):
    """Test continuous mode with max iterations"""
    mock_db.get_pending_events.return_value = []

    # Run for 2 iterations
    archivist.run_continuous(interval_seconds=0.1, max_iterations=2)

    # Should have checked for pending events 2 times
    assert mock_db.get_pending_events.call_count == 2


@patch('agents.archivist.EntityExtractor')
@patch('agents.archivist.EmbeddingsService')
def test_process_event_error_handling(mock_embeddings_cls, mock_extractor_cls, archivist, mock_db):
    """Test error handling in event processing"""
    # Setup event
    event = MockRawEvent('event-1', 'Test content')
    mock_db.get_event_by_id.return_value = event

    # Make entity extraction raise an error
    mock_extractor = Mock()
    mock_extractor.extract_entities.side_effect = Exception("Extraction failed")
    archivist.entity_extractor = mock_extractor

    # Process event
    result = archivist.process_event('event-1')

    # Assertions
    assert result['status'] == 'error'
    assert 'error' in result
    assert result['event_id'] == 'event-1'

    # Event should be marked as error
    mock_db.update_event_status.assert_called_with('event-1', 'error')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
