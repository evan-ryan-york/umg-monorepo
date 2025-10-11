"""
Unit and integration tests for Mentor agent (Phase 7)

Tests cover:
- Mentor initialization
- Context gathering
- Insight generation
- Feedback processing
- Signal adjustments
- Pattern recording
- Error handling

Run with:
    pytest tests/test_mentor.py -v
    pytest tests/test_mentor.py -v -m integration  # Integration tests only
    pytest tests/test_mentor.py::test_mentor_initialization  # Single test
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from agents.mentor import Mentor
from agents.feedback_processor import FeedbackProcessor
from services.database import DatabaseService
from tests.fixtures.mentor_fixtures import (
    sample_core_identity,
    sample_recent_work,
    sample_high_priority_entities,
    sample_historical_entities,
    sample_insight_delta_watch,
    sample_insight_connection,
    sample_insight_prompt,
    sample_dismissed_pattern_delta_watch,
    sample_context,
)


# ============================================================================
# Unit Tests - Mentor Agent
# ============================================================================


class TestMentorInitialization:
    """Test Mentor agent initialization"""

    def test_mentor_can_be_instantiated(self):
        """Test that Mentor can be created"""
        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()
            assert mentor is not None

    def test_mentor_has_correct_model(self):
        """Test that Mentor uses correct Claude model"""
        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()
            assert mentor.model == "claude-sonnet-4-5"

    def test_mentor_has_anthropic_client(self):
        """Test that Mentor has Anthropic client initialized"""
        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()
            assert mentor.client is not None


class TestContextGathering:
    """Test Mentor's context gathering"""

    @pytest.fixture
    def mock_db(self):
        """Mock database service"""
        with patch('agents.mentor.db') as mock:
            yield mock

    def test_gather_context_calls_all_methods(self, mock_db):
        """Test that _gather_context calls all required database methods"""
        mock_db.get_entities_by_type.return_value = sample_core_identity()
        mock_db.get_entities_created_since.return_value = sample_recent_work()
        mock_db.get_entities_by_signal_threshold.return_value = sample_high_priority_entities()
        mock_db.get_dismissed_patterns.return_value = []

        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()
            context = mentor._gather_context()

            # Verify all methods were called
            mock_db.get_entities_by_type.assert_called_once_with('core_identity')
            mock_db.get_entities_created_since.assert_called_once()
            assert mock_db.get_entities_by_signal_threshold.call_count == 2  # Called twice
            mock_db.get_dismissed_patterns.assert_called_once_with(days_back=30)

    def test_gather_context_returns_expected_structure(self, mock_db):
        """Test that _gather_context returns correctly structured data"""
        mock_db.get_entities_by_type.return_value = sample_core_identity()
        mock_db.get_entities_created_since.return_value = sample_recent_work()
        mock_db.get_entities_by_signal_threshold.return_value = sample_recent_work()
        mock_db.get_dismissed_patterns.return_value = []

        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()
            context = mentor._gather_context()

            # Check structure
            assert 'core_identity' in context
            assert 'recent_entities' in context
            assert 'high_priority' in context
            assert 'recent_work' in context
            assert 'dismissed_patterns' in context

    def test_gather_context_handles_empty_data(self, mock_db):
        """Test that _gather_context handles empty database responses"""
        mock_db.get_entities_by_type.return_value = []
        mock_db.get_entities_created_since.return_value = []
        mock_db.get_entities_by_signal_threshold.return_value = []
        mock_db.get_dismissed_patterns.return_value = []

        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()
            context = mentor._gather_context()

            # Should still return structure, just with empty lists
            assert context['core_identity'] == []
            assert context['recent_entities'] == []


class TestInsightGeneration:
    """Test insight generation methods"""

    @pytest.fixture
    def mock_db(self):
        """Mock database service"""
        with patch('agents.mentor.db') as mock:
            yield mock

    @pytest.fixture
    def mock_claude_response(self):
        """Mock Claude API response"""
        return json.dumps({
            "title": "Test Insight",
            "body": "This is a test insight body.",
            "driver_entity_ids": ["uuid-1", "uuid-2"],
            "alignment_score": 0.85
        })

    def test_call_claude_strips_markdown(self):
        """Test that _call_claude strips markdown formatting"""
        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()

            # Mock the Anthropic client response
            mock_response = Mock()
            mock_response.content = [Mock(text="```json\n{\"test\": \"data\"}\n```")]
            mentor.client.messages.create = Mock(return_value=mock_response)

            result = mentor._call_claude("test prompt", "test_type")
            assert result == '{"test": "data"}'

    def test_call_claude_handles_errors_gracefully(self):
        """Test that _call_claude handles API errors and returns fallback"""
        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()

            # Mock the Anthropic client to raise an exception
            mentor.client.messages.create = Mock(side_effect=Exception("API Error"))

            result = mentor._call_claude("test prompt", "delta_watch")
            # Should return fallback insight
            fallback = json.loads(result)
            assert fallback['title'] == 'Daily Check-In'
            assert 'driver_entity_ids' in fallback

    def test_fallback_insights_exist_for_all_types(self):
        """Test that fallback insights exist for all insight types"""
        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()

            for insight_type in ['delta_watch', 'connection', 'prompt']:
                result = mentor._fallback_insight(insight_type)
                data = json.loads(result)
                assert 'title' in data
                assert 'body' in data
                assert 'driver_entity_ids' in data


# ============================================================================
# Integration Tests - Mentor Agent
# ============================================================================


@pytest.mark.integration
class TestMentorIntegration:
    """Integration tests for Mentor (with mocked dependencies)"""

    @pytest.fixture
    def mock_full_context(self):
        """Mock full context for integration tests"""
        return sample_context()

    @pytest.fixture
    def mock_db_full(self):
        """Mock database with full setup"""
        with patch('agents.mentor.db') as mock:
            mock.get_entities_by_type.return_value = sample_core_identity()
            mock.get_entities_created_since.return_value = sample_recent_work()
            mock.get_entities_by_signal_threshold.return_value = sample_recent_work()
            mock.get_dismissed_patterns.return_value = []
            mock.create_insight.return_value = "uuid-new-insight"
            mock.get_similar_entities.return_value = sample_historical_entities()
            yield mock

    def test_generate_daily_digest_creates_three_insights(self, mock_db_full):
        """Test that generate_daily_digest creates all three insight types"""
        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()

            # Mock Claude responses
            mentor._call_claude = Mock(return_value=json.dumps({
                "title": "Test",
                "body": "Test body",
                "driver_entity_ids": ["uuid-1"]
            }))

            digest = mentor.generate_daily_digest()

            assert 'delta_watch' in digest
            assert 'connection' in digest
            assert 'prompt' in digest
            assert 'insights_created' in digest
            assert digest['insights_created'] == 3

    def test_generate_daily_digest_stores_insights_in_db(self, mock_db_full):
        """Test that insights are stored in database"""
        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()

            mentor._call_claude = Mock(return_value=json.dumps({
                "title": "Test",
                "body": "Test body",
                "driver_entity_ids": ["uuid-1"]
            }))

            mentor.generate_daily_digest()

            # Verify create_insight was called 3 times
            assert mock_db_full.create_insight.call_count == 3

    def test_generate_daily_digest_handles_connection_without_historical(self, mock_db_full):
        """Test Connection insight when no historical entities found"""
        mock_db_full.get_similar_entities.return_value = []  # No historical data

        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()

            mentor._call_claude = Mock(return_value=json.dumps({
                "title": "Test",
                "body": "Test body",
                "driver_entity_ids": ["uuid-1"]
            }))

            digest = mentor.generate_daily_digest()

            # Connection should be None when no historical entities
            assert digest['connection'] is None


# ============================================================================
# Unit Tests - Feedback Processor
# ============================================================================


class TestFeedbackProcessor:
    """Test FeedbackProcessor functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database service"""
        with patch('agents.feedback_processor.db') as mock:
            yield mock

    def test_process_acknowledge_boosts_importance(self, mock_db):
        """Test that acknowledge boosts entity importance scores"""
        # Setup
        insight = sample_insight_delta_watch()
        mock_db.get_insight_by_id.return_value = insight
        mock_db.get_signal_by_entity_id.return_value = {
            'importance': 0.5,
            'recency': 0.5,
            'novelty': 0.5
        }
        mock_db.get_entity_by_id.return_value = {
            'id': 'uuid-work-feed-1',
            'created_at': '2025-10-01T00:00:00Z'
        }
        mock_db.update_signal.return_value = None
        mock_db.update_insight_status.return_value = None

        processor = FeedbackProcessor()
        result = processor.process_acknowledge('uuid-insight-delta-1')

        # Verify
        assert result['status'] == 'success'
        assert result['action'] == 'acknowledge'
        assert result['entities_updated'] == 4  # 4 driver entities
        assert mock_db.update_signal.call_count == 4

    def test_process_acknowledge_refreshes_recency(self, mock_db):
        """Test that acknowledge refreshes recency scores"""
        insight = sample_insight_delta_watch()
        mock_db.get_insight_by_id.return_value = insight
        mock_db.get_signal_by_entity_id.return_value = {
            'importance': 0.5,
            'recency': 0.3,  # Old recency
            'novelty': 0.5
        }
        mock_db.get_entity_by_id.return_value = {
            'id': 'uuid-work-feed-1',
            'created_at': '2025-10-01T00:00:00Z'
        }

        processor = FeedbackProcessor()
        result = processor.process_acknowledge('uuid-insight-delta-1')

        # Check signal_changes have recency_boosted=True
        for change in result['signal_changes']:
            if 'recency_boosted' in change:
                assert change['recency_boosted'] is True

    def test_process_dismiss_lowers_importance(self, mock_db):
        """Test that dismiss lowers entity importance scores"""
        insight = sample_insight_delta_watch()
        mock_db.get_insight_by_id.return_value = insight
        mock_db.get_signal_by_entity_id.return_value = {
            'importance': 0.7,
            'recency': 0.5,
            'novelty': 0.5
        }
        mock_db.get_entity_by_id.return_value = {
            'id': 'uuid-work-feed-1',
            'type': 'feature'
        }
        mock_db.update_signal.return_value = None
        mock_db.record_dismissed_pattern.return_value = None
        mock_db.update_insight_status.return_value = None

        processor = FeedbackProcessor()
        result = processor.process_dismiss('uuid-insight-delta-1')

        # Verify importance was lowered
        assert result['status'] == 'success'
        assert result['action'] == 'dismiss'
        assert result['entities_updated'] == 4

        # Check that importance was lowered (not boosted)
        for change in result['signal_changes']:
            if 'importance' in change:
                old = change['importance']['old']
                new = change['importance']['new']
                assert new < old  # Should be lowered

    def test_process_dismiss_records_pattern(self, mock_db):
        """Test that dismiss records dismissal pattern"""
        insight = sample_insight_delta_watch()
        mock_db.get_insight_by_id.return_value = insight
        mock_db.get_signal_by_entity_id.return_value = {
            'importance': 0.7
        }
        mock_db.get_entity_by_id.return_value = {
            'id': 'uuid-work-feed-1',
            'type': 'feature'
        }

        processor = FeedbackProcessor()
        result = processor.process_dismiss('uuid-insight-delta-1')

        # Verify pattern was recorded
        assert 'pattern_recorded' in result
        assert result['pattern_recorded']['insight_type'] == 'Delta Watch'
        assert mock_db.record_dismissed_pattern.called

    def test_adjust_entity_signals_clamps_to_valid_range(self, mock_db):
        """Test that signal adjustments stay within [0.0, 1.0]"""
        mock_db.get_signal_by_entity_id.return_value = {
            'importance': 0.95  # Already high
        }

        processor = FeedbackProcessor()
        result = processor._adjust_entity_signals(
            'uuid-test',
            importance_delta=0.2,  # Would push to 1.15
            recency_boost=False
        )

        # Should be clamped to 1.0
        assert result['importance']['new'] == 1.0

    def test_extract_pattern_identifies_insight_type(self, mock_db):
        """Test that pattern extraction identifies insight type correctly"""
        mock_db.get_entity_by_id.return_value = {'type': 'feature'}

        processor = FeedbackProcessor()

        for insight_type in ['Delta Watch', 'Connection', 'Prompt']:
            insight = {
                'title': f'{insight_type}: Test Title',
                'body': 'Test body',
                'drivers': {'entity_ids': ['uuid-1']}
            }
            pattern = processor._extract_pattern(insight)
            assert pattern['insight_type'] == insight_type

    def test_extract_keywords_removes_stop_words(self):
        """Test that keyword extraction removes stop words"""
        processor = FeedbackProcessor()
        keywords = processor._extract_keywords(
            "The goal is to build and create amazing features for the project"
        )

        # Should not contain stop words
        assert 'the' not in keywords
        assert 'and' not in keywords
        assert 'for' not in keywords

        # Should contain meaningful words
        assert any(k in ['goal', 'build', 'create', 'amazing', 'features', 'project'] for k in keywords)


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error scenarios and edge cases"""

    @pytest.fixture
    def mock_db(self):
        """Mock database service"""
        with patch('agents.mentor.db') as mock:
            yield mock

    def test_mentor_handles_missing_entities_gracefully(self, mock_db):
        """Test Mentor when no entities exist in database"""
        mock_db.get_entities_by_type.return_value = []
        mock_db.get_entities_created_since.return_value = []
        mock_db.get_entities_by_signal_threshold.return_value = []
        mock_db.get_dismissed_patterns.return_value = []
        mock_db.create_insight.return_value = "uuid-fallback"

        with patch('agents.mentor.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mentor = Mentor()

            # Should use fallback insights
            mentor._call_claude = Mock(side_effect=Exception("No data"))

            digest = mentor.generate_daily_digest()

            # Should still return digest with fallbacks
            assert 'delta_watch' in digest
            assert 'connection' in digest
            assert 'prompt' in digest

    def test_feedback_processor_handles_missing_signal(self):
        """Test FeedbackProcessor when entity has no signal"""
        with patch('agents.feedback_processor.db') as mock_db:
            mock_db.get_signal_by_entity_id.return_value = None

            processor = FeedbackProcessor()
            result = processor._adjust_entity_signals(
                'uuid-no-signal',
                importance_delta=0.1,
                recency_boost=False
            )

            # Should return error
            assert 'error' in result
            assert result['error'] == 'no_signal'

    def test_feedback_processor_handles_missing_insight(self):
        """Test FeedbackProcessor when insight doesn't exist"""
        with patch('agents.feedback_processor.db') as mock_db:
            mock_db.get_insight_by_id.side_effect = Exception("Insight not found")

            processor = FeedbackProcessor()

            with pytest.raises(Exception):
                processor.process_acknowledge('non-existent-id')


# ============================================================================
# Test Summary
# ============================================================================


def test_all_fixtures_are_valid():
    """Sanity check that all test fixtures are valid"""
    # Core identity
    core = sample_core_identity()
    assert len(core) > 0
    assert all('id' in e and 'type' in e for e in core)

    # Recent work
    work = sample_recent_work()
    assert len(work) > 0
    assert all('signal' in e for e in work)

    # Insights
    delta = sample_insight_delta_watch()
    assert 'drivers' in delta
    assert 'entity_ids' in delta['drivers']

    connection = sample_insight_connection()
    assert 'drivers' in connection

    prompt = sample_insight_prompt()
    assert 'drivers' in prompt

    # Dismissed patterns
    pattern = sample_dismissed_pattern_delta_watch()
    assert 'insight_type' in pattern
    assert 'pattern_signature' in pattern
