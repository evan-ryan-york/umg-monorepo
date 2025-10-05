"""Tests for RelationshipMapper"""
import pytest
from processors.relationship_mapper import RelationshipMapper


class MockDB:
    """Mock database for testing"""

    def __init__(self):
        self.entities_metadata = {}
        self.edges = []

    def get_entity_metadata(self, entity_id: str) -> dict:
        return self.entities_metadata.get(entity_id, {})

    def update_entity_metadata(self, entity_id: str, metadata: dict):
        self.entities_metadata[entity_id] = metadata

    def create_edge(self, edge_data: dict) -> str:
        self.edges.append(edge_data)
        return f"edge_{len(self.edges)}"


def test_detect_explicit_relationships_rename():
    """Test detection of rename signals"""
    mapper = RelationshipMapper()

    text = "We renamed the school-update feature to just 'feed' for clarity."
    relationships = mapper.detect_explicit_relationships(text)

    assert len(relationships) > 0
    assert any(r['type'] == 'modifies' for r in relationships)
    assert any(r['signal'] == 'rename' for r in relationships)


def test_detect_explicit_relationships_belongs_to():
    """Test detection of hierarchical relationships"""
    mapper = RelationshipMapper()

    text = "The Feed feature belongs to the Willow project."
    relationships = mapper.detect_explicit_relationships(text)

    assert len(relationships) > 0
    assert any(r['type'] == 'belongs_to' for r in relationships)


def test_detect_explicit_relationships_blocks():
    """Test detection of blocking/dependency relationships"""
    mapper = RelationshipMapper()

    text = "This task is blocked by the API integration work."
    relationships = mapper.detect_explicit_relationships(text)

    assert len(relationships) > 0
    assert any(r['type'] == 'blocks' for r in relationships)


def test_detect_alias_and_update():
    """Test alias detection and metadata update"""
    mapper = RelationshipMapper()
    mock_db = MockDB()

    # Setup: Entity with ID
    entities = [
        {
            'title': 'Feed',
            'type': 'feature',
            'entity_id': 'entity_123'
        }
    ]

    # Initialize metadata
    mock_db.update_entity_metadata('entity_123', {'aliases': []})

    text = "We renamed school-update to feed for clarity."
    alias_updates = mapper.detect_alias_and_update(text, entities, mock_db)

    assert len(alias_updates) > 0
    assert alias_updates[0]['old_name'] == 'school-update'
    assert alias_updates[0]['new_name'] == 'feed'

    # Check metadata was updated
    metadata = mock_db.get_entity_metadata('entity_123')
    assert 'school-update' in metadata['aliases']


def test_detect_alias_and_update_multiple_patterns():
    """Test alias detection with different rename patterns"""
    mapper = RelationshipMapper()
    mock_db = MockDB()

    test_cases = [
        ("renamed from school-update to feed", 'school-update', 'feed'),
        ("now called feed instead of school-update", 'feed', 'school-update'),
        ("changing school-update to feed", 'school-update', 'feed'),
    ]

    for i, (text, expected_old, expected_new) in enumerate(test_cases):
        entities = [{
            'title': expected_new,
            'type': 'feature',
            'entity_id': f'entity_{i}'
        }]

        mock_db.update_entity_metadata(f'entity_{i}', {'aliases': []})

        alias_updates = mapper.detect_alias_and_update(text, entities, mock_db)

        assert len(alias_updates) > 0, f"Failed for pattern: {text}"


def test_create_edge_from_relationship():
    """Test edge creation from relationship"""
    mapper = RelationshipMapper()
    mock_db = MockDB()

    relationship = {
        'from_entity': 'Feed',
        'to_entity': 'Willow',
        'relationship_type': 'belongs_to',
        'metadata': {'context': 'project hierarchy'}
    }

    entity_map = {
        'Feed': 'entity_1',
        'Willow': 'entity_2'
    }

    result = mapper.create_edge_from_relationship(relationship, entity_map, mock_db)

    assert result is True
    assert len(mock_db.edges) == 1
    assert mock_db.edges[0]['from_id'] == 'entity_1'
    assert mock_db.edges[0]['to_id'] == 'entity_2'
    assert mock_db.edges[0]['kind'] == 'belongs_to'


def test_create_edge_missing_entities():
    """Test edge creation fails gracefully with missing entities"""
    mapper = RelationshipMapper()
    mock_db = MockDB()

    relationship = {
        'from_entity': 'NonExistent',
        'to_entity': 'AlsoNonExistent',
        'relationship_type': 'belongs_to'
    }

    entity_map = {}

    result = mapper.create_edge_from_relationship(relationship, entity_map, mock_db)

    assert result is False
    assert len(mock_db.edges) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
