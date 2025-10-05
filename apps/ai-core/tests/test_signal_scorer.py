"""Tests for SignalScorer"""
import pytest
from datetime import datetime, timedelta
from processors.signal_scorer import SignalScorer


def test_signal_scorer_initialization():
    """Test SignalScorer initializes with default half-life"""
    scorer = SignalScorer()
    assert scorer.recency_half_life_days == 30


def test_signal_scorer_custom_half_life():
    """Test SignalScorer with custom half-life"""
    scorer = SignalScorer(recency_half_life_days=60)
    assert scorer.recency_half_life_days == 60


def test_calculate_importance_core_identity():
    """Test importance for core_identity entities"""
    scorer = SignalScorer()
    importance = scorer.calculate_importance('core_identity')
    assert importance == 1.0


def test_calculate_importance_project():
    """Test importance for project entities"""
    scorer = SignalScorer()
    importance = scorer.calculate_importance('project')
    assert importance == 0.85


def test_calculate_importance_task():
    """Test importance for task entities"""
    scorer = SignalScorer()
    importance = scorer.calculate_importance('task')
    assert importance == 0.6


def test_calculate_importance_with_user_high():
    """Test importance adjustment for user_importance=high"""
    scorer = SignalScorer()
    metadata = {'user_importance': 'high'}
    importance = scorer.calculate_importance('task', metadata)

    # Base 0.6 + 0.2 = 0.8
    assert importance == 0.8


def test_calculate_importance_with_user_low():
    """Test importance adjustment for user_importance=low"""
    scorer = SignalScorer()
    metadata = {'user_importance': 'low'}
    importance = scorer.calculate_importance('project', metadata)

    # Base 0.85 - 0.2 = 0.65
    assert importance == 0.65


def test_calculate_importance_unknown_type():
    """Test importance for unknown entity type defaults to 0.5"""
    scorer = SignalScorer()
    importance = scorer.calculate_importance('unknown_type')
    assert importance == 0.5


def test_calculate_importance_clamping():
    """Test importance is clamped to [0.0, 1.0]"""
    scorer = SignalScorer()

    # High importance + user_importance=high should clamp at 1.0
    metadata = {'user_importance': 'high'}
    importance = scorer.calculate_importance('core_identity', metadata)
    assert importance == 1.0

    # Low importance + user_importance=low should clamp at 0.1
    importance = scorer.calculate_importance('reference_document', metadata={'user_importance': 'low'})
    assert importance >= 0.1


def test_calculate_recency_new_entity():
    """Test recency for brand new entity"""
    scorer = SignalScorer()
    now = datetime.now()
    recency = scorer.calculate_recency(now, now)

    # Should be very close to 1.0 (brand new)
    assert recency > 0.99


def test_calculate_recency_half_life():
    """Test recency at exactly half-life (30 days)"""
    scorer = SignalScorer()
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    recency = scorer.calculate_recency(thirty_days_ago)

    # Should be approximately 0.5
    assert 0.49 < recency < 0.51


def test_calculate_recency_old_entity():
    """Test recency for very old entity"""
    scorer = SignalScorer()
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    recency = scorer.calculate_recency(one_year_ago)

    # Should be very low but not zero
    assert 0.0 < recency < 0.1


def test_calculate_recency_uses_updated_at():
    """Test that recency uses updated_at if more recent"""
    scorer = SignalScorer()
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    yesterday = now - timedelta(days=1)

    # Entity created a year ago but updated yesterday
    recency = scorer.calculate_recency(one_year_ago, yesterday)

    # Should be high (based on yesterday, not a year ago)
    assert recency > 0.95


def test_calculate_novelty_new_entity():
    """Test novelty for new entity with no connections"""
    scorer = SignalScorer()
    novelty = scorer.calculate_novelty(edge_count=0, entity_age_days=0)

    # Should be 1.0 (brand new, no connections)
    assert novelty == 1.0


def test_calculate_novelty_some_connections():
    """Test novelty for entity with some connections and age"""
    scorer = SignalScorer()
    novelty = scorer.calculate_novelty(edge_count=5, entity_age_days=10)

    # Should be medium novelty
    assert 0.4 < novelty < 0.7


def test_calculate_novelty_well_established():
    """Test novelty for old, well-connected entity"""
    scorer = SignalScorer()
    novelty = scorer.calculate_novelty(edge_count=20, entity_age_days=100)

    # Should be low novelty
    assert 0.0 < novelty < 0.3


def test_calculate_novelty_many_edges():
    """Test novelty decreases with more edges"""
    scorer = SignalScorer()
    novelty_few = scorer.calculate_novelty(edge_count=2, entity_age_days=5)
    novelty_many = scorer.calculate_novelty(edge_count=20, entity_age_days=5)

    # More edges = less novelty
    assert novelty_many < novelty_few


def test_calculate_all_signals():
    """Test calculate_all_signals returns all three scores"""
    scorer = SignalScorer()
    now = datetime.now()
    signals = scorer.calculate_all_signals(
        entity_type='project',
        created_at=now,
        updated_at=now,
        edge_count=5,
        metadata={'user_importance': 'high'}
    )

    assert 'importance' in signals
    assert 'recency' in signals
    assert 'novelty' in signals

    assert signals['importance'] > 0.0
    assert signals['recency'] > 0.0
    assert signals['novelty'] > 0.0


def test_calculate_composite_score_default_weights():
    """Test composite score with default weights"""
    scorer = SignalScorer()
    composite = scorer.calculate_composite_score(
        importance=0.8,
        recency=0.6,
        novelty=0.4
    )

    # Default weights: importance=0.5, recency=0.3, novelty=0.2
    # Expected: (0.8 * 0.5) + (0.6 * 0.3) + (0.4 * 0.2) = 0.4 + 0.18 + 0.08 = 0.66
    assert 0.65 < composite < 0.67


def test_calculate_composite_score_custom_weights():
    """Test composite score with custom weights"""
    scorer = SignalScorer()
    custom_weights = {
        'importance': 0.7,
        'recency': 0.2,
        'novelty': 0.1
    }
    composite = scorer.calculate_composite_score(
        importance=0.8,
        recency=0.6,
        novelty=0.4,
        weights=custom_weights
    )

    # Expected: (0.8 * 0.7) + (0.6 * 0.2) + (0.4 * 0.1) = 0.56 + 0.12 + 0.04 = 0.72
    assert 0.71 < composite < 0.73


def test_calculate_composite_score_clamping():
    """Test composite score is clamped to [0.0, 1.0]"""
    scorer = SignalScorer()
    composite = scorer.calculate_composite_score(1.0, 1.0, 1.0)
    assert composite == 1.0

    composite = scorer.calculate_composite_score(0.0, 0.0, 0.0)
    assert composite == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
