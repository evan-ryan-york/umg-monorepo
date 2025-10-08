#!/usr/bin/env python3
"""
Seed the database with test data for Mentor testing.

This creates:
- Core identity entities (goals, values)
- Recent work entities (last 24 hours)
- Historical entities (30+ days old)
- Signals for all entities

Usage:
    python scripts/seed-mentor-test-data.py
"""

import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

# Add ai-core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "ai-core"))

from services.database import db
from processors.signal_scorer import SignalScorer

signal_scorer = SignalScorer()


def create_entity_with_signal(
    entity_type: str,
    title: str,
    summary: str,
    metadata: dict,
    created_at: datetime,
    importance: float,
    recency: float = None,
    novelty: float = 0.5,
):
    """Create an entity and its signal"""

    # Create entity
    entity_id = str(uuid4())
    entity_data = {
        "id": entity_id,
        "type": entity_type,
        "title": title,
        "summary": summary,
        "metadata": metadata,
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
    }

    response = db.client.table("entity").insert(entity_data).execute()

    if response.data:
        print(f"✓ Created entity: {title}")
    else:
        print(f"✗ Failed to create entity: {title}")
        return None

    # Calculate recency if not provided
    if recency is None:
        recency = signal_scorer.calculate_recency(
            created_at.isoformat(), datetime.now().isoformat()
        )

    # Create signal
    signal_data = {
        "entity_id": entity_id,
        "importance": importance,
        "recency": recency,
        "novelty": novelty,
    }

    db.client.table("signal").insert(signal_data).execute()

    return entity_id


def seed_core_identity():
    """Create core identity entities (goals, values, mission)"""
    print("\n=== Creating Core Identity Entities ===")

    now = datetime.now()

    # Goal 1: Water OS Launch
    create_entity_with_signal(
        entity_type="core_identity",
        title="Launch Water OS in Ghana by December",
        summary="Primary Q4 goal: Successfully deploy Water OS pilot program in Ghana, including local partnerships and initial user onboarding. Target: 500 active users by end of Q4.",
        metadata={"tags": ["goal", "Q4", "water-os"], "priority": "high"},
        created_at=now - timedelta(days=90),  # Set 90 days ago
        importance=1.0,
        recency=0.3,  # Old goal, still relevant
        novelty=0.2,
    )

    # Goal 2: Willow Education Platform
    create_entity_with_signal(
        entity_type="core_identity",
        title="Build robust Willow Education platform",
        summary="Secondary goal: Develop and refine Willow Education app with focus on parent-teacher communication and student engagement features.",
        metadata={"tags": ["goal", "willow", "education"], "priority": "medium"},
        created_at=now - timedelta(days=60),
        importance=0.8,
        recency=0.5,
        novelty=0.3,
    )

    # Value 1: Equity
    create_entity_with_signal(
        entity_type="core_identity",
        title="Impact rooted in Equity",
        summary="Core value: Build solutions that address fundamental inequities in access to clean water, education, and economic opportunity. Every project should serve underserved communities.",
        metadata={"tags": ["value", "equity", "impact"], "importance": 1.0},
        created_at=now - timedelta(days=180),
        importance=1.0,
        recency=0.2,
        novelty=0.1,
    )

    # Value 2: Build with Users
    create_entity_with_signal(
        entity_type="core_identity",
        title="Build with users, not for them",
        summary="Core principle: Co-create solutions with the communities we serve. Listen deeply, iterate based on real feedback, and empower local ownership.",
        metadata={"tags": ["value", "user-centered"], "importance": 0.9},
        created_at=now - timedelta(days=150),
        importance=0.9,
        recency=0.3,
        novelty=0.1,
    )


def seed_recent_work():
    """Create recent work entities (last 24 hours)"""
    print("\n=== Creating Recent Work Entities ===")

    now = datetime.now()

    # Recent work on Willow Feed feature
    create_entity_with_signal(
        entity_type="feature",
        title="Feed Feature for Willow Education",
        summary="Building a social feed feature for Willow Education app that allows parents to see updates from teachers, student achievements, and classroom activities. Currently working on UI design and real-time updates.",
        metadata={"project": "willow", "status": "in_progress", "priority": "high"},
        created_at=now - timedelta(hours=18),
        importance=0.8,
        recency=1.0,
        novelty=0.7,
    )

    # More work on Feed
    create_entity_with_signal(
        entity_type="task",
        title="Polish Feed UI components",
        summary="Spent several hours refining the UI components for the Willow feed - card layouts, animations, loading states. Making it look professional and polished.",
        metadata={"project": "willow", "type": "ui", "feature": "feed"},
        created_at=now - timedelta(hours=6),
        importance=0.6,
        recency=1.0,
        novelty=0.5,
    )

    # Feed feature continued
    create_entity_with_signal(
        entity_type="task",
        title="Real-time feed updates with WebSockets",
        summary="Implementing real-time updates for the Willow feed using WebSockets. Parents should see new posts instantly without refreshing.",
        metadata={"project": "willow", "type": "backend", "feature": "feed"},
        created_at=now - timedelta(hours=12),
        importance=0.7,
        recency=1.0,
        novelty=0.6,
    )

    # A small Water OS task (for goal comparison)
    create_entity_with_signal(
        entity_type="task",
        title="Review Ghana partnership agreements",
        summary="Quickly reviewed the draft partnership agreements with local NGOs in Ghana for Water OS deployment. Flagged a few legal questions for follow-up.",
        metadata={"project": "water-os", "location": "ghana"},
        created_at=now - timedelta(hours=20),
        importance=0.5,
        recency=0.95,
        novelty=0.4,
    )


def seed_historical_work():
    """Create historical entities (30+ days old) for Connection insights"""
    print("\n=== Creating Historical Work Entities ===")

    now = datetime.now()

    # Similar past work: Parent notification system (relates to Feed)
    create_entity_with_signal(
        entity_type="feature",
        title="Parent Notification System for Willow",
        summary="Built a notification system for Willow that sends parents real-time alerts about student attendance, grades, and important announcements. Learned a lot about push notification reliability and user preferences.",
        metadata={
            "project": "willow",
            "status": "completed",
            "learnings": "Push notifications can be overwhelming - need digest option",
        },
        created_at=now - timedelta(days=120),  # 4 months ago
        importance=0.7,
        recency=0.1,
        novelty=0.2,
    )

    # User retention work (relates to engagement features)
    create_entity_with_signal(
        entity_type="project",
        title="Willow User Retention Analysis",
        summary="Analyzed user retention data for Willow Education app. Found that parents engage most with visual content (photos, videos) and personalized updates about their specific child. Generic school-wide announcements get ignored.",
        metadata={
            "project": "willow",
            "type": "analysis",
            "key_insight": "Personalization drives engagement",
        },
        created_at=now - timedelta(days=90),  # 3 months ago
        importance=0.8,
        recency=0.15,
        novelty=0.3,
    )

    # Ghana field research (relates to Water OS goal)
    create_entity_with_signal(
        entity_type="research",
        title="Ghana Field Research - Water Access Challenges",
        summary="Spent 2 weeks in rural Ghana understanding water access challenges. Key findings: (1) Water sources far from homes, (2) Women bear burden of collection, (3) Existing hand pumps often broken due to lack of local maintenance skills.",
        metadata={
            "project": "water-os",
            "location": "ghana",
            "type": "field_research",
        },
        created_at=now - timedelta(days=75),  # 2.5 months ago
        importance=0.9,
        recency=0.2,
        novelty=0.4,
    )

    # Similar UI work
    create_entity_with_signal(
        entity_type="feature",
        title="Willow Dashboard UI Redesign",
        summary="Redesigned the Willow parent dashboard UI. Spent a lot of time on polish and animations. In retrospect, should have validated core functionality with users first before investing in visual polish.",
        metadata={
            "project": "willow",
            "type": "ui",
            "status": "completed",
            "lesson": "Polish early can be premature optimization",
        },
        created_at=now - timedelta(days=45),  # 1.5 months ago
        importance=0.6,
        recency=0.25,
        novelty=0.3,
    )


def seed_high_priority_work():
    """Create high-importance entities"""
    print("\n=== Creating High-Priority Entities ===")

    now = datetime.now()

    create_entity_with_signal(
        entity_type="decision",
        title="Focus Q4 on Water OS or Willow?",
        summary="Key strategic decision: Should we prioritize Water OS Ghana launch or continue building Willow features? Both are important but team bandwidth is limited.",
        metadata={"type": "strategic", "urgency": "high"},
        created_at=now - timedelta(days=14),
        importance=0.95,
        recency=0.5,
        novelty=0.7,
    )

    create_entity_with_signal(
        entity_type="risk",
        title="Water OS Ghana Launch Delays",
        summary="Concerned about delays in Water OS Ghana launch. Partnership agreements taking longer than expected, and local regulatory approvals still pending. December deadline at risk.",
        metadata={"project": "water-os", "type": "risk", "severity": "high"},
        created_at=now - timedelta(days=7),
        importance=0.9,
        recency=0.7,
        novelty=0.6,
    )


def main():
    """Run all seed functions"""
    print("🌱 Seeding database with Mentor test data...\n")

    try:
        seed_core_identity()
        seed_recent_work()
        seed_historical_work()
        seed_high_priority_work()

        print("\n✅ Database seeding complete!")
        print(
            "\nYou can now test the Mentor with: curl -X POST http://localhost:8000/mentor/generate-digest"
        )

    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
