"""
Test fixtures for Mentor agent testing
"""

from datetime import datetime, timedelta


def sample_core_identity():
    """Sample core identity entities (goals and values)"""
    return [
        {
            "id": "uuid-goal-water-os",
            "type": "core_identity",
            "title": "Launch Water OS in Ghana",
            "summary": "Primary Q4 goal: Launch Water OS pilot in Ghana by December 2025",
            "metadata": {"tags": ["goal", "Q4"], "priority": "high"},
            "created_at": "2025-09-01T00:00:00Z",
        },
        {
            "id": "uuid-value-equity",
            "type": "core_identity",
            "title": "Impact rooted in Equity",
            "summary": "Core value: Build solutions that address fundamental inequities in access to clean water",
            "metadata": {"tags": ["value"], "importance": 1.0},
            "created_at": "2025-09-01T00:00:00Z",
        },
        {
            "id": "uuid-goal-willow-growth",
            "type": "core_identity",
            "title": "Scale Willow Education to 50 schools",
            "summary": "Goal: Reach 50 partner schools by end of 2025",
            "metadata": {"tags": ["goal", "2025"], "priority": "medium"},
            "created_at": "2025-01-15T00:00:00Z",
        },
    ]


def sample_recent_work():
    """Sample recent work entities (high recency)"""
    return [
        {
            "id": "uuid-work-feed-1",
            "type": "feature",
            "title": "Feed Feature for Willow",
            "summary": "Building activity feed feature for Willow Education app to show student updates",
            "created_at": (datetime.now() - timedelta(hours=12)).isoformat(),
            "signal": {
                "importance": 0.8,
                "recency": 1.0,
                "novelty": 0.6,
            },
        },
        {
            "id": "uuid-work-feed-2",
            "type": "feature",
            "title": "Feed Feature - UI Polish",
            "summary": "Polishing UI/UX for the Feed feature in Willow app",
            "created_at": (datetime.now() - timedelta(hours=4)).isoformat(),
            "signal": {
                "importance": 0.8,
                "recency": 1.0,
                "novelty": 0.5,
            },
        },
        {
            "id": "uuid-work-feed-3",
            "type": "task",
            "title": "Fix Feed pagination bug",
            "summary": "Debugging pagination issue in Willow Feed feature",
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "signal": {
                "importance": 0.6,
                "recency": 1.0,
                "novelty": 0.7,
            },
        },
    ]


def sample_high_priority_entities():
    """Sample high importance entities"""
    return [
        {
            "id": "uuid-project-water-os",
            "type": "project",
            "title": "Water OS",
            "summary": "Water infrastructure management system for reducing non-revenue water in Ghana",
            "created_at": "2025-08-15T00:00:00Z",
            "signal": {
                "importance": 0.95,
                "recency": 0.6,
                "novelty": 0.8,
            },
        },
        {
            "id": "uuid-project-willow",
            "type": "project",
            "title": "Willow Education",
            "summary": "Education platform connecting schools, students, and families",
            "created_at": "2024-06-01T00:00:00Z",
            "signal": {
                "importance": 0.85,
                "recency": 0.9,
                "novelty": 0.3,
            },
        },
        {
            "id": "uuid-person-ryan",
            "type": "person",
            "title": "Ryan York",
            "summary": "Chief Product & Technology Officer at Willow Education, founder of Water OS",
            "created_at": "2025-10-01T00:00:00Z",
            "metadata": {"is_user_entity": True, "user_id": "default_user"},
            "signal": {
                "importance": 0.7,
                "recency": 1.0,
                "novelty": 0.5,
            },
        },
    ]


def sample_historical_entities():
    """Sample historical entities (older work for Connection insights)"""
    return [
        {
            "id": "uuid-historical-retention",
            "type": "feature",
            "title": "Student Retention Analytics",
            "summary": "Built analytics system to track student engagement and retention patterns in Willow",
            "created_at": (datetime.now() - timedelta(days=90)).isoformat(),
            "signal": {
                "importance": 0.65,
                "recency": 0.3,
                "novelty": 0.2,
            },
        },
        {
            "id": "uuid-historical-notifications",
            "type": "feature",
            "title": "Parent Notification System",
            "summary": "Notification system for keeping parents updated on student activities in Willow",
            "created_at": (datetime.now() - timedelta(days=120)).isoformat(),
            "signal": {
                "importance": 0.7,
                "recency": 0.25,
                "novelty": 0.15,
            },
        },
        {
            "id": "uuid-historical-water-research",
            "type": "reference_document",
            "title": "Ghana Water Infrastructure Research",
            "summary": "Research on non-revenue water challenges in Ghana's water distribution systems",
            "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
            "signal": {
                "importance": 0.75,
                "recency": 0.5,
                "novelty": 0.6,
            },
        },
    ]


def sample_insight_delta_watch():
    """Sample Delta Watch insight"""
    return {
        "id": "uuid-insight-delta-1",
        "title": "Delta Watch: Goal Drift Detected",
        "body": "Your Q4 goal was to launch Water OS in Ghana, but you've spent 80% of this week on Willow's Feed feature. Is this a strategic pivot or a distraction?",
        "drivers": {
            "entity_ids": [
                "uuid-goal-water-os",
                "uuid-work-feed-1",
                "uuid-work-feed-2",
                "uuid-work-feed-3",
            ],
            "edge_ids": [],
        },
        "status": "open",
        "created_at": datetime.now().isoformat(),
    }


def sample_insight_connection():
    """Sample Connection insight"""
    return {
        "id": "uuid-insight-connection-1",
        "title": "Connection: Parent Communication Pattern",
        "body": "The Feed feature you're building now has similarities to the Parent Notification System you built 4 months ago. The engagement patterns you discovered there about timing and content preferences might apply here.",
        "drivers": {
            "entity_ids": [
                "uuid-work-feed-1",
                "uuid-historical-notifications",
            ],
            "edge_ids": [],
        },
        "status": "open",
        "created_at": datetime.now().isoformat(),
    }


def sample_insight_prompt():
    """Sample Prompt insight"""
    return {
        "id": "uuid-insight-prompt-1",
        "title": "Prompt: What's the real problem?",
        "body": "You've been focused on the Feed feature's UI polish. But what problem is this feature actually solving for students and teachers? Is polish the highest leverage work right now?",
        "drivers": {
            "entity_ids": ["uuid-work-feed-2", "uuid-project-willow"],
            "edge_ids": [],
        },
        "status": "open",
        "created_at": datetime.now().isoformat(),
    }


def sample_dismissed_pattern_delta_watch():
    """Sample dismissed Delta Watch pattern"""
    return {
        "id": "uuid-dismissed-1",
        "insight_type": "Delta Watch",
        "driver_entity_types": ["feature", "project"],
        "pattern_signature": {
            "insight_type": "Delta Watch",
            "driver_types": ["feature", "project"],
            "title_keywords": ["goal", "drift", "detected"],
            "dismissed_at": (datetime.now() - timedelta(days=5)).isoformat(),
        },
        "dismissed_count": 2,
        "first_dismissed_at": (datetime.now() - timedelta(days=10)).isoformat(),
        "last_dismissed_at": (datetime.now() - timedelta(days=5)).isoformat(),
    }


def sample_dismissed_pattern_connection():
    """Sample dismissed Connection pattern"""
    return {
        "id": "uuid-dismissed-2",
        "insight_type": "Connection",
        "driver_entity_types": ["feature", "reference_document"],
        "pattern_signature": {
            "insight_type": "Connection",
            "driver_types": ["feature", "reference_document"],
            "title_keywords": ["historical", "pattern"],
            "dismissed_at": (datetime.now() - timedelta(days=3)).isoformat(),
        },
        "dismissed_count": 1,
        "first_dismissed_at": (datetime.now() - timedelta(days=3)).isoformat(),
        "last_dismissed_at": (datetime.now() - timedelta(days=3)).isoformat(),
    }


# Complete context for testing
def sample_context():
    """Complete context object for Mentor testing"""
    return {
        "core_identity": sample_core_identity(),
        "recent_entities": sample_recent_work(),
        "high_priority": sample_high_priority_entities(),
        "recent_work": sample_recent_work(),
        "dismissed_patterns": [
            sample_dismissed_pattern_delta_watch(),
            sample_dismissed_pattern_connection(),
        ],
    }
