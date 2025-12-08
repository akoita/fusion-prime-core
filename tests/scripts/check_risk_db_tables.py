#!/usr/bin/env python3
"""
Quick script to check risk_db table contents.

Usage:
    # Check all tables
    python tests/scripts/check_risk_db_tables.py

    # Check specific user
    python tests/scripts/check_risk_db_tables.py --user-id test-user-001

Requirements:
    - Cloud SQL Proxy must be running
    - RISK_DATABASE_URL must be configured for localhost:5433
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))

from tests.common.risk_db_validation_utils import (
    get_risk_db_table_counts,
    query_alert_notifications_from_db,
    query_margin_events_from_db,
    query_margin_health_snapshots_from_db,
)
from tests.load_test_env import load_test_environment


async def check_tables(user_id: str = None):
    """Check risk_db tables and print contents."""

    print("\n" + "=" * 80)
    print("RISK DATABASE TABLE INSPECTION")
    print("=" * 80)

    # Step 1: Get table counts
    print("\n📊 TABLE ROW COUNTS:")
    print("-" * 80)

    try:
        counts = await get_risk_db_table_counts()

        for table, count in counts.items():
            status = "✅" if count > 0 else "⚠️ "
            print(f"{status} {table:30} {count:>10} rows")

        total_rows = sum(counts.values())
        print("-" * 80)
        print(f"   {'TOTAL':30} {total_rows:>10} rows")

    except ConnectionError as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 TIP: Make sure Cloud SQL Proxy is running:")
        print("   cloud-sql-proxy fusion-prime:us-central1:fusion-prime-risk-db --port 5433")
        print("\nAnd update RISK_DATABASE_URL in .env.dev to use localhost:5433")
        return
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return

    # Step 2: Query margin health snapshots
    if counts.get("margin_health_snapshots", 0) > 0:
        print("\n📈 MARGIN HEALTH SNAPSHOTS:")
        print("-" * 80)

        try:
            if user_id:
                snapshots = await query_margin_health_snapshots_from_db(user_id, limit=5)
            else:
                # Get all users' snapshots
                snapshots = await query_margin_health_snapshots_from_db("", limit=10)

            if snapshots:
                for snapshot in snapshots[:5]:  # Show first 5
                    print(f"\n  Snapshot: {snapshot['snapshot_id']}")
                    print(f"  User: {snapshot['user_id']}")
                    print(f"  Health: {snapshot['health_score']:.2f}%")
                    print(f"  Status: {snapshot['status']}")
                    print(f"  Collateral: ${snapshot['total_collateral_usd']:,.2f}")
                    print(f"  Borrows: ${snapshot['total_borrow_usd']:,.2f}")
                    print(f"  Created: {snapshot['created_at']}")
            else:
                print("  No snapshots found")

        except Exception as e:
            print(f"  Error querying snapshots: {e}")

    # Step 3: Query margin events
    if counts.get("margin_events", 0) > 0:
        print("\n⚠️  MARGIN EVENTS:")
        print("-" * 80)

        try:
            events = await query_margin_events_from_db(user_id, limit=10)

            if events:
                for event in events[:5]:  # Show first 5
                    print(f"\n  Event: {event['event_id']}")
                    print(f"  User: {event['user_id']}")
                    print(f"  Type: {event['event_type']}")
                    print(f"  Severity: {event['severity']}")
                    print(f"  Health: {event['health_score']:.2f}%")
                    print(f"  Message: {event['message']}")
                    print(f"  Published: {event['published_to_pubsub']}")
                    print(f"  Created: {event['created_at']}")
            else:
                print("  No events found")

        except Exception as e:
            print(f"  Error querying events: {e}")

    # Step 4: Query alert notifications
    if counts.get("alert_notifications", 0) > 0:
        print("\n🔔 ALERT NOTIFICATIONS:")
        print("-" * 80)

        try:
            notifications = await query_alert_notifications_from_db(user_id, limit=10)

            if notifications:
                for notif in notifications[:5]:  # Show first 5
                    print(f"\n  Notification: {notif['notification_id']}")
                    print(f"  User: {notif['user_id']}")
                    print(f"  Type: {notif['alert_type']}")
                    print(f"  Severity: {notif['severity']}")
                    print(f"  Channels: {notif['channels']}")
                    print(f"  Status: {notif['status']}")
                    print(f"  Event ID: {notif['margin_event_id']}")
                    print(f"  Sent: {notif['sent_at']}")
                    print(f"  Created: {notif['created_at']}")
            else:
                print("  No notifications found")

        except Exception as e:
            print(f"  Error querying notifications: {e}")

    # Step 5: Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if total_rows == 0:
        print("\n⚠️  No data found in any risk_db tables")
        print("\n💡 POSSIBLE CAUSES:")
        print("  1. Tests haven't been run yet")
        print("  2. Risk Engine not persisting data")
        print("  3. Database persistence logic not implemented")
        print("\n🔧 NEXT STEPS:")
        print("  1. Run tests: pytest tests/test_margin_health_integration.py")
        print("  2. Check Risk Engine logs for database writes")
        print("  3. Verify RISK_DATABASE_URL is configured correctly")
    else:
        print(f"\n✅ Found {total_rows} total rows across risk_db tables")
        print("\n📋 TABLE BREAKDOWN:")
        for table, count in counts.items():
            if count > 0:
                print(f"  - {table}: {count} rows")

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Check risk_db table contents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--user-id", help="Filter by user ID", default=None)

    args = parser.parse_args()

    # Load environment
    load_test_environment()

    # Check database URL
    risk_db_url = os.getenv("RISK_DATABASE_URL")
    if not risk_db_url:
        print("❌ ERROR: RISK_DATABASE_URL not set in environment")
        print("   Load .env.dev or set the environment variable")
        sys.exit(1)

    # Check if using localhost (proxy)
    if "localhost" in risk_db_url or "127.0.0.1" in risk_db_url:
        print("✅ Using Cloud SQL Proxy (localhost)")
    else:
        print("⚠️  RISK_DATABASE_URL not using localhost - may fail if proxy not configured")

    # Run check
    asyncio.run(check_tables(user_id=args.user_id))
