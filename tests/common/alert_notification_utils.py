"""
Utility functions for validating alert notification delivery tracking.

These utilities query the alert_notifications table in the Risk Engine database
to verify notification persistence.
"""

import logging
import os
from typing import Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


def query_alert_notifications(
    user_id: str, alert_type: Optional[str] = None, limit: int = 10
) -> List[Dict]:
    """
    Query alert_notifications table for a user.

    Args:
        user_id: User identifier
        alert_type: Optional filter by alert type
        limit: Maximum number of records to return

    Returns:
        List of notification records

    Raises:
        Exception if database connection fails
    """
    # Get database URL from environment
    # Try RISK_DATABASE_URL first (used in .env.dev), then RISK_ENGINE_DATABASE_URL for backwards compatibility
    database_url = os.getenv("RISK_DATABASE_URL") or os.getenv("RISK_ENGINE_DATABASE_URL")
    if not database_url:
        logger.warning(
            "RISK_DATABASE_URL or RISK_ENGINE_DATABASE_URL not set, cannot query alert_notifications"
        )
        return []

    try:
        # Convert async database URL to sync URL for SQLAlchemy
        # Replace postgresql+asyncpg:// with postgresql:// (will use psycopg2 if available, psycopg otherwise)
        sync_database_url = database_url
        if database_url.startswith("postgresql+asyncpg://"):
            # Use generic postgresql:// which will auto-detect the best driver (psycopg2 or psycopg)
            sync_database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
            logger.debug("Converted async database URL to sync URL for query")
        elif database_url.startswith("postgresql+aiosqlite://"):
            # This shouldn't happen for risk database, but handle it gracefully
            logger.warning("Async SQLite URL detected, this may not work correctly")

        # Create database connection with NullPool to avoid async context issues
        engine = create_engine(sync_database_url, poolclass=NullPool, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        session = SessionLocal()
        try:
            # Build query
            query = """
                SELECT
                    notification_id,
                    user_id,
                    alert_type,
                    severity,
                    channels,
                    status,
                    delivery_details,
                    margin_event_id,
                    message_body,
                    sent_at,
                    delivered_at,
                    failed_at,
                    failure_reason,
                    created_at
                FROM alert_notifications
                WHERE user_id = :user_id
            """

            params = {"user_id": user_id}

            if alert_type:
                query += " AND alert_type = :alert_type"
                params["alert_type"] = alert_type

            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit

            # Execute query
            result = session.execute(text(query), params)

            # Convert to list of dicts
            notifications = []
            for row in result:
                notifications.append(
                    {
                        "notification_id": row[0],
                        "user_id": row[1],
                        "alert_type": row[2],
                        "severity": row[3],
                        "channels": row[4],
                        "status": row[5],
                        "delivery_details": row[6],
                        "margin_event_id": row[7],
                        "message_body": row[8],
                        "sent_at": row[9],
                        "delivered_at": row[10],
                        "failed_at": row[11],
                        "failure_reason": row[12],
                        "created_at": row[13],
                    }
                )

            logger.info(f"Found {len(notifications)} alert notifications for user {user_id}")
            return notifications
        finally:
            session.close()
            engine.dispose()

    except Exception as e:
        logger.error(f"Failed to query alert_notifications: {e}")
        raise


def validate_notification_persisted(
    user_id: str,
    expected_alert_type: str,
    expected_severity: Optional[str] = None,
    timeout: int = 10,
) -> Dict:
    """
    Validate that a notification was persisted to the database.

    Args:
        user_id: User identifier
        expected_alert_type: Expected alert type
        expected_severity: Optional expected severity
        timeout: Not used (for API consistency)

    Returns:
        The notification record if found

    Raises:
        AssertionError if validation fails
    """
    notifications = query_alert_notifications(user_id, expected_alert_type, limit=5)

    if not notifications:
        raise AssertionError(
            f"No alert notifications found for user {user_id} with type {expected_alert_type}"
        )

    # Get the most recent notification
    notification = notifications[0]

    # Validate required fields
    assert notification["user_id"] == user_id, f"User ID mismatch: {notification['user_id']}"
    assert (
        notification["alert_type"] == expected_alert_type
    ), f"Alert type mismatch: {notification['alert_type']}"

    if expected_severity:
        assert (
            notification["severity"] == expected_severity
        ), f"Severity mismatch: {notification['severity']}"

    # Validate channels array exists
    assert notification["channels"] is not None, "Channels field is null"
    assert isinstance(notification["channels"], list), "Channels should be a list"

    # Validate status is valid
    valid_statuses = ["sent", "delivered", "failed", "pending"]
    assert notification["status"] in valid_statuses, f"Invalid status: {notification['status']}"

    # Validate delivery details
    assert notification["delivery_details"] is not None, "Delivery details is null"

    # Validate timestamps
    assert notification["created_at"] is not None, "Created timestamp is null"
    assert notification["sent_at"] is not None, "Sent timestamp is null"

    logger.info(
        f"Validated notification {notification['notification_id']}: "
        f"type={notification['alert_type']}, status={notification['status']}"
    )

    return notification
