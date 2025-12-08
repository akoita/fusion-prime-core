"""
Margin Health Database Repository.

Handles persistence of margin health snapshots, events, and alert notifications.
"""

import logging
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from infrastructure.db.models import AlertNotification, MarginEvent, MarginHealthSnapshot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MarginHealthRepository:
    """Repository for margin health data persistence."""

    def __init__(self, session_factory):
        """
        Initialize repository with database session factory.

        Args:
            session_factory: Async session factory for database operations
        """
        self.session_factory = session_factory
        logger.info("Margin health repository initialized")

    async def save_health_snapshot(
        self, user_id: str, health_metrics: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save margin health snapshot to database.

        Args:
            user_id: User identifier
            health_metrics: Health calculation results from MarginHealthCalculator

        Returns:
            Snapshot ID if successful, None otherwise
        """
        try:
            async with self.session_factory() as session:
                snapshot_id = f"snapshot-{secrets.token_hex(12)}"

                snapshot = MarginHealthSnapshot(
                    snapshot_id=snapshot_id,
                    user_id=user_id,
                    health_score=Decimal(str(health_metrics.get("health_score", 0))),
                    status=health_metrics.get("status", "UNKNOWN"),
                    total_collateral_usd=Decimal(
                        str(health_metrics.get("total_collateral_usd", 0))
                    ),
                    total_borrow_usd=Decimal(str(health_metrics.get("total_borrow_usd", 0))),
                    collateral_breakdown=health_metrics.get("collateral_breakdown", {}),
                    borrow_breakdown=health_metrics.get("borrow_breakdown", {}),
                    liquidation_price_drop_percent=Decimal(
                        str(health_metrics.get("liquidation_price_drop_percent", 0))
                    ),
                    previous_health_score=None,  # Would query from previous snapshot
                )

                session.add(snapshot)
                await session.commit()

                logger.info(f"Saved margin health snapshot: {snapshot_id} for user {user_id}")
                return snapshot_id

        except Exception as e:
            logger.error(f"Failed to save health snapshot for user {user_id}: {e}")
            return None

    async def save_margin_event(
        self, event_data: Dict[str, Any], snapshot_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Save margin event to database.

        Args:
            event_data: Margin event details from MarginHealthCalculator
            snapshot_id: Associated snapshot ID (if available)

        Returns:
            Event ID if successful, None otherwise
        """
        try:
            async with self.session_factory() as session:
                event_id = f"event-{secrets.token_hex(12)}"

                event = MarginEvent(
                    event_id=event_id,
                    user_id=event_data.get("user_id"),
                    event_type=event_data.get("event_type"),
                    severity=event_data.get("severity"),
                    health_score=Decimal(str(event_data.get("health_score", 0))),
                    previous_health_score=(
                        Decimal(str(event_data.get("previous_health_score", 0)))
                        if event_data.get("previous_health_score")
                        else None
                    ),
                    threshold_breached=None,  # Could calculate based on event_type
                    message=event_data.get("message"),
                    recommendations=[],  # Could add recommendations based on event_type
                    collateral_usd=Decimal(str(event_data.get("total_collateral_usd", 0))),
                    borrow_usd=Decimal(str(event_data.get("total_borrow_usd", 0))),
                    published_to_pubsub="false",  # Will update after publishing
                )

                session.add(event)
                await session.commit()

                logger.info(
                    f"Saved margin event: {event_id} ({event_data.get('event_type')}) for user {event_data.get('user_id')}"
                )
                return event_id

        except Exception as e:
            logger.error(f"Failed to save margin event for user {event_data.get('user_id')}: {e}")
            return None

    async def update_event_published_status(self, event_id: str, published: bool = True):
        """
        Update margin event's Pub/Sub publication status.

        Args:
            event_id: Event ID to update
            published: Publication status
        """
        try:
            async with self.session_factory() as session:
                stmt = select(MarginEvent).where(MarginEvent.event_id == event_id)
                result = await session.execute(stmt)
                event = result.scalar_one_or_none()

                if event:
                    event.published_to_pubsub = "true" if published else "false"
                    await session.commit()
                    logger.debug(f"Updated event {event_id} published status: {published}")

        except Exception as e:
            logger.error(f"Failed to update event {event_id} published status: {e}")

    async def save_alert_notification(
        self,
        user_id: str,
        alert_type: str,
        severity: str,
        message_body: str,
        margin_event_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Save alert notification record.

        Args:
            user_id: User identifier
            alert_type: Type of alert
            severity: Alert severity level
            message_body: Alert message content
            margin_event_id: Associated margin event ID

        Returns:
            Notification ID if successful, None otherwise
        """
        try:
            async with self.session_factory() as session:
                notification_id = f"notif-{secrets.token_hex(12)}"

                notification = AlertNotification(
                    notification_id=notification_id,
                    user_id=user_id,
                    alert_type=alert_type,
                    severity=severity,
                    channels=["pubsub"],  # Default to pubsub channel
                    status="pending",
                    delivery_details={},
                    margin_event_id=margin_event_id,
                    message_body=message_body,
                    sent_at=datetime.utcnow(),
                )

                session.add(notification)
                await session.commit()

                logger.info(f"Saved alert notification: {notification_id} for user {user_id}")
                return notification_id

        except Exception as e:
            logger.error(f"Failed to save alert notification for user {user_id}: {e}")
            return None

    async def get_latest_snapshot(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent health snapshot for a user.

        Args:
            user_id: User identifier

        Returns:
            Latest snapshot data or None
        """
        try:
            async with self.session_factory() as session:
                stmt = (
                    select(MarginHealthSnapshot)
                    .where(MarginHealthSnapshot.user_id == user_id)
                    .order_by(MarginHealthSnapshot.created_at.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                snapshot = result.scalar_one_or_none()

                if snapshot:
                    return {
                        "snapshot_id": snapshot.snapshot_id,
                        "user_id": snapshot.user_id,
                        "health_score": float(snapshot.health_score),
                        "status": snapshot.status,
                        "total_collateral_usd": float(snapshot.total_collateral_usd),
                        "total_borrow_usd": float(snapshot.total_borrow_usd),
                        "calculated_at": snapshot.calculated_at.isoformat() + "Z",
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to get latest snapshot for user {user_id}: {e}")
            return None

    async def get_recent_events(
        self, user_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent margin events, optionally filtered by user.

        Args:
            user_id: Optional user ID filter
            limit: Maximum number of events to return

        Returns:
            List of margin events
        """
        try:
            async with self.session_factory() as session:
                stmt = select(MarginEvent).order_by(MarginEvent.created_at.desc()).limit(limit)

                if user_id:
                    stmt = stmt.where(MarginEvent.user_id == user_id)

                result = await session.execute(stmt)
                events = result.scalars().all()

                return [
                    {
                        "event_id": event.event_id,
                        "user_id": event.user_id,
                        "event_type": event.event_type,
                        "severity": event.severity,
                        "health_score": float(event.health_score),
                        "message": event.message,
                        "created_at": event.created_at.isoformat() + "Z",
                    }
                    for event in events
                ]

        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []
