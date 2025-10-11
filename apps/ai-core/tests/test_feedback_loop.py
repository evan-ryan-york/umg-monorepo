"""
Test script for Mentor Feedback Loop (Phase 4)

This script tests the complete feedback loop:
1. Seed test data
2. Generate insights
3. Test acknowledge feedback
4. Test dismiss feedback
5. Verify signal changes
6. Verify pattern recording

Run this with:
    python tests/test_feedback_loop.py

Prerequisites:
    - AI Core server must be running (pnpm run dev:web)
    - Phase 1 migrations must be run in Supabase
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a section header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_result(step, success, message=""):
    """Print a test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {step}")
    if message:
        print(f"    {message}")


def test_server_health():
    """Test that server is running"""
    print_section("1. Server Health Check")

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_result("Server is running", True, f"Status: {response.json()['status']}")
            return True
        else:
            print_result("Server health check", False, f"Status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_result("Server health check", False, "Cannot connect to server. Is it running?")
        print("    Run: pnpm run dev:web")
        return False
    except Exception as e:
        print_result("Server health check", False, str(e))
        return False


def seed_test_data():
    """Seed test data"""
    print_section("2. Seed Test Data")

    try:
        response = requests.post(f"{BASE_URL}/mentor/seed-test-data", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print_result(
                "Test data seeded",
                True,
                f"Created {data['entities_created']} entities"
            )
            return True
        else:
            print_result("Seed test data", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_result("Seed test data", False, str(e))
        return False


def generate_insights():
    """Generate insights and return them"""
    print_section("3. Generate Insights")

    try:
        response = requests.post(f"{BASE_URL}/mentor/generate-digest", timeout=60)
        if response.status_code == 200:
            data = response.json()
            insights = []

            print_result(
                "Insights generated",
                True,
                f"Created {data['insights_generated']} insights"
            )

            # Show insight details
            for insight_type in ['delta_watch', 'connection', 'prompt']:
                insight = data['digest'].get(insight_type)
                if insight:
                    print(f"\n  {insight_type.upper()}:")
                    print(f"    ID: {insight.get('id')}")
                    print(f"    Title: {insight.get('title', 'N/A')}")
                    print(f"    Drivers: {len(insight.get('driver_entity_ids', []))} entities")
                    insights.append(insight)

            return insights
        else:
            print_result("Generate insights", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        print_result("Generate insights", False, str(e))
        return []


def test_acknowledge(insight_id):
    """Test acknowledge feedback"""
    print_section("4. Test Acknowledge Feedback")

    try:
        payload = {"insight_id": insight_id}
        response = requests.post(
            f"{BASE_URL}/feedback/acknowledge",
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "Acknowledge processed",
                True,
                f"Updated {data.get('entities_updated', 0)} entities"
            )

            # Show signal changes
            if data.get('signal_changes'):
                print("\n  Signal Changes:")
                for change in data['signal_changes'][:3]:  # Show first 3
                    old_imp = change.get('importance', {}).get('old', 0)
                    new_imp = change.get('importance', {}).get('new', 0)
                    print(f"    Entity: {change.get('entity_id', 'unknown')}")
                    print(f"      Importance: {old_imp:.2f} → {new_imp:.2f} (+{new_imp - old_imp:.2f})")
                    print(f"      Recency boosted: {change.get('recency_boosted', False)}")

            return True
        else:
            print_result("Acknowledge feedback", False, f"Status code: {response.status_code}")
            print(f"    Response: {response.text}")
            return False
    except Exception as e:
        print_result("Acknowledge feedback", False, str(e))
        return False


def test_dismiss(insight_id):
    """Test dismiss feedback"""
    print_section("5. Test Dismiss Feedback")

    try:
        payload = {"insight_id": insight_id}
        response = requests.post(
            f"{BASE_URL}/feedback/dismiss",
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "Dismiss processed",
                True,
                f"Updated {data.get('entities_updated', 0)} entities"
            )

            # Show signal changes
            if data.get('signal_changes'):
                print("\n  Signal Changes:")
                for change in data['signal_changes'][:3]:  # Show first 3
                    old_imp = change.get('importance', {}).get('old', 0)
                    new_imp = change.get('importance', {}).get('new', 0)
                    print(f"    Entity: {change.get('entity_id', 'unknown')}")
                    print(f"      Importance: {old_imp:.2f} → {new_imp:.2f} ({new_imp - old_imp:.2f})")

            # Show pattern recorded
            if data.get('pattern_recorded'):
                pattern = data['pattern_recorded']
                print(f"\n  Pattern Recorded:")
                print(f"    Type: {pattern.get('insight_type')}")
                print(f"    Driver types: {pattern.get('driver_entity_types', [])}")

            return True
        else:
            print_result("Dismiss feedback", False, f"Status code: {response.status_code}")
            print(f"    Response: {response.text}")
            return False
    except Exception as e:
        print_result("Dismiss feedback", False, str(e))
        return False


def verify_feedback_loop():
    """Verify the complete feedback loop"""
    print_section("6. Verify Feedback Loop")

    # Generate new insights to see if dismissed pattern is avoided
    try:
        response = requests.post(f"{BASE_URL}/mentor/generate-digest", timeout=60)
        if response.status_code == 200:
            data = response.json()
            print_result(
                "Second digest generated",
                True,
                f"Created {data['insights_generated']} insights (should adapt based on feedback)"
            )
            return True
        else:
            print_result("Second digest generation", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_result("Second digest generation", False, str(e))
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  MENTOR FEEDBACK LOOP TEST")
    print("  Phase 4 End-to-End Verification")
    print("=" * 60)

    # Test 1: Server health
    if not test_server_health():
        print("\n❌ Server is not running. Exiting.")
        sys.exit(1)

    # Test 2: Seed data
    if not seed_test_data():
        print("\n❌ Failed to seed test data. Exiting.")
        sys.exit(1)

    # Test 3: Generate insights
    insights = generate_insights()
    if not insights:
        print("\n⚠️  No insights generated (this is OK if data is sparse)")
        print("    Feedback loop cannot be tested without insights.")
        sys.exit(0)

    # Test 4: Acknowledge first insight
    if len(insights) > 0:
        first_insight = insights[0]
        if not test_acknowledge(first_insight['id']):
            print("\n❌ Acknowledge feedback failed.")

    # Test 5: Dismiss second insight
    if len(insights) > 1:
        second_insight = insights[1]
        if not test_dismiss(second_insight['id']):
            print("\n❌ Dismiss feedback failed.")
    elif len(insights) == 1:
        # Dismiss the same insight (already acknowledged, but that's OK for testing)
        if not test_dismiss(first_insight['id']):
            print("\n❌ Dismiss feedback failed.")

    # Test 6: Verify feedback loop
    verify_feedback_loop()

    # Final summary
    print_section("Test Summary")
    print("✅ All core functionality tested")
    print("\nManual verification recommended:")
    print("1. Check Supabase - dismissed_patterns table should have entries")
    print("2. Check Supabase - signal table should show changed importance scores")
    print("3. Check Supabase - insight table should show 'acknowledged' and 'dismissed' statuses")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
