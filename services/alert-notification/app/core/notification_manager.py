"""
Notification Manager - Core logic for delivering alerts.

Handles routing alerts to appropriate channels (email, SMS, webhook)
based on user preferences and alert severity.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from app.db.models import AlertNotification
from app.db.session import DatabaseManager
from google.cloud import pubsub_v1, secretmanager

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages notification delivery across multiple channels."""

    def __init__(
        self,
        database_url: str,
        sendgrid_api_key: str,
        twilio_account_sid: str,
        twilio_auth_token: str,
    ):
        self.database_url = database_url
        self.sendgrid_api_key = sendgrid_api_key
        self.twilio_account_sid = twilio_account_sid
        self.twilio_auth_token = twilio_auth_token

        self.pubsub_subscriber = None
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Initialize database manager for persisting notification records
        self.db_manager = None
        logger.info(
            f"[DIAGNOSTIC] NotificationManager __init__ called with database_url={'***REDACTED***' if database_url else 'None/Empty'}"
        )

        if database_url:
            try:
                logger.info(
                    f"[DIAGNOSTIC] Attempting to initialize DatabaseManager with URL length: {len(database_url)}"
                )
                self.db_manager = DatabaseManager(database_url)
                logger.info(
                    "[DIAGNOSTIC] Database manager successfully initialized for notification persistence"
                )
            except Exception as e:
                logger.warning(
                    f"[DIAGNOSTIC] Failed to initialize database manager: {e}", exc_info=True
                )
                logger.warning("Notification delivery tracking will not be persisted")
        else:
            logger.warning(
                "[DIAGNOSTIC] No database_url provided - database manager will NOT be initialized"
            )

    async def initialize(self):
        """Initialize the notification manager."""
        logger.info("Initializing notification manager...")

        # Create Pub/Sub subscriber
        subscriber_client = pubsub_v1.SubscriberClient()
        project_id = "fusion-prime"
        topic_name = "alerts.margin.v1"
        subscription_name = "alert-notification-service"

        # Create subscription if it doesn't exist
        try:
            subscription_path = subscriber_client.subscription_path(project_id, subscription_name)
            subscriber_client.get_subscription(subscription_path)
            logger.info(f"Subscription {subscription_name} already exists")
        except Exception:
            # Create subscription
            topic_path = subscriber_client.topic_path(project_id, topic_name)
            subscription_config = pubsub_v1.types.Subscription(
                name=subscription_path, topic=topic_path
            )
            subscriber_client.create_subscription(
                request={"name": subscription_path, "topic": topic_path}
            )
            logger.info(f"Created subscription {subscription_name}")

        self.pubsub_subscriber = subscriber_client

        # Start background task to process alerts
        self.background_task = asyncio.create_task(self._process_alerts())

        logger.info("Notification manager initialized")

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up notification manager...")
        if self.background_task:
            self.background_task.cancel()
        await self.http_client.aclose()

    async def _process_alerts(self):
        """Background task to process Pub/Sub alerts."""
        logger.info("Starting alert processing loop...")

        while True:
            try:
                # Pull messages from Pub/Sub
                await self._pull_and_process_messages()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                logger.info("Alert processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing alerts: {e}")
                await asyncio.sleep(10)  # Retry after error

    async def _pull_and_process_messages(self):
        """Pull messages from Pub/Sub and process them."""
        if not self.pubsub_subscriber:
            return

        project_id = "fusion-prime"
        subscription_name = "alert-notification-service"
        subscription_path = self.pubsub_subscriber.subscription_path(project_id, subscription_name)

        # Pull messages (non-blocking)
        response = self.pubsub_subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": 10,
            }
        )

        for message in response.received_messages:
            try:
                # Parse message
                alert_data = message.message.data.decode("utf-8")
                import json

                alert = json.loads(alert_data)

                # Process alert
                await self.send_notification(
                    user_id=alert["user_id"],
                    alert_type=alert["event_type"],
                    severity=alert["severity"],
                    message=alert["message"],
                    metadata=alert,
                )

                # Acknowledge message
                self.pubsub_subscriber.acknowledge(
                    request={
                        "subscription": subscription_path,
                        "ack_ids": [message.ack_id],
                    }
                )

                logger.info(f"Processed alert for user {alert['user_id']}")

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Don't acknowledge on error

    async def send_notification(
        self,
        user_id: str,
        alert_type: str,
        severity: str,
        message: str,
        metadata: Optional[Dict] = None,
    ):
        """
        Send notification to user via configured channels.

        Args:
            user_id: User identifier
            alert_type: Type of alert (margin_warning, margin_call, etc.)
            severity: Alert severity (low, medium, high, critical)
            message: Alert message
            metadata: Additional alert metadata
        """
        logger.info(f"Sending notification to user {user_id}")

        # Get user preferences
        preferences = await self._get_user_preferences(user_id)

        # Determine channels based on severity and preferences
        channels = self._determine_channels(severity, preferences)

        # Send via each channel
        delivered = []
        failed = []

        for channel in channels:
            try:
                if channel == "email":
                    await self._send_email(user_id, message, metadata)
                    delivered.append(channel)
                elif channel == "sms":
                    await self._send_sms(user_id, message, metadata)
                    delivered.append(channel)
                elif channel == "webhook":
                    await self._send_webhook(user_id, message, metadata, preferences)
                    delivered.append(channel)
                else:
                    logger.warning(f"Unknown channel: {channel}")
                    failed.append(channel)

            except Exception as e:
                logger.error(f"Failed to send via {channel}: {e}")
                failed.append(channel)

        logger.info(f"Notification to user {user_id}: delivered={delivered}, failed={failed}")

        # Persist notification delivery tracking to database
        await self._persist_notification(
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            channels=channels,
            delivered=delivered,
            failed=failed,
            metadata=metadata,
        )

    def _determine_channels(self, severity: str, preferences: Optional[Dict]) -> List[str]:
        """
        Determine which channels to use based on severity and preferences.

        Rules:
        - CRITICAL: email + sms + webhook
        - HIGH: email + webhook
        - MEDIUM: email
        - LOW: email (optional)
        """
        # Get user's enabled channels from preferences
        enabled_channels = preferences.get("enabled_channels", []) if preferences else []

        # Default channels if not configured
        if not enabled_channels:
            if severity == "critical":
                enabled_channels = ["email", "sms", "webhook"]
            elif severity == "high":
                enabled_channels = ["email", "webhook"]
            elif severity == "medium":
                enabled_channels = ["email"]
            else:
                enabled_channels = ["email"]

        return enabled_channels

    async def _get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """Get user notification preferences from database."""
        # TODO: Implement database lookup
        # For now, return None to use defaults
        return None

    async def _send_email(self, user_id: str, message: str, metadata: Optional[Dict]):
        """Send email notification via SendGrid."""
        if not self.sendgrid_api_key:
            logger.warning("SendGrid API key not configured, skipping email")
            return

        # Get user email from metadata or database
        email = metadata.get("email") if metadata else f"{user_id}@user.local"

        logger.info(f"Sending email to {email}")

        # Send email via SendGrid API
        sendgrid_url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.sendgrid_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "personalizations": [{"to": [{"email": email}]}],
            "from": {"email": "alerts@fusionprime.com", "name": "Fusion Prime"},
            "subject": f"Alert: {metadata.get('alert_type', 'Security Alert')}",
            "content": [{"type": "text/html", "value": f"<h2>Security Alert</h2><p>{message}</p>"}],
        }

        response = await self.http_client.post(sendgrid_url, headers=headers, json=payload)
        response.raise_for_status()

        logger.info(f"Email sent successfully to {email}")

    async def _send_sms(self, user_id: str, message: str, metadata: Optional[Dict]):
        """Send SMS notification via Twilio."""
        if not self.twilio_account_sid or not self.twilio_auth_token:
            logger.warning("Twilio credentials not configured, skipping SMS")
            return

        # Get user phone from metadata or database
        phone = metadata.get("phone") if metadata else None
        if not phone:
            logger.warning(f"No phone number for user {user_id}")
            return

        logger.info(f"Sending SMS to {phone}")

        # Send SMS via Twilio API
        twilio_url = (
            f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
        )
        auth = (self.twilio_account_sid, self.twilio_auth_token)

        payload = {
            "From": "+15551234567",  # From config
            "To": phone,
            "Body": message[:160],  # SMS character limit
        }

        response = await self.http_client.post(twilio_url, auth=auth, data=payload)
        response.raise_for_status()

        logger.info(f"SMS sent successfully to {phone}")

    async def _send_webhook(
        self, user_id: str, message: str, metadata: Optional[Dict], preferences: Optional[Dict]
    ):
        """Send webhook notification."""
        webhook_url = preferences.get("webhook_url") if preferences else metadata.get("webhook_url")

        if not webhook_url:
            logger.info(f"No webhook URL for user {user_id}")
            return

        logger.info(f"Sending webhook to {webhook_url}")

        payload = {
            "user_id": user_id,
            "alert_type": metadata.get("alert_type"),
            "severity": metadata.get("severity"),
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata,
        }

        response = await self.http_client.post(webhook_url, json=payload)
        response.raise_for_status()

        logger.info(f"Webhook sent successfully to {webhook_url}")

    async def _persist_notification(
        self,
        user_id: str,
        alert_type: str,
        severity: str,
        message: str,
        channels: List[str],
        delivered: List[str],
        failed: List[str],
        metadata: Optional[Dict],
    ):
        """
        Persist notification delivery tracking to database.

        Args:
            user_id: User identifier
            alert_type: Type of alert
            severity: Alert severity
            message: Notification message
            channels: Channels used
            delivered: Successfully delivered channels
            failed: Failed channels
            metadata: Additional metadata
        """
        logger.info(
            f"[DIAGNOSTIC] _persist_notification called for user {user_id}, "
            f"alert_type={alert_type}, severity={severity}, "
            f"delivered={delivered}, failed={failed}"
        )

        if not self.db_manager:
            logger.warning(
                f"[DIAGNOSTIC] Database manager not initialized, skipping persistence. "
                f"db_manager is None: {self.db_manager is None}"
            )
            return

        logger.info(f"[DIAGNOSTIC] Database manager initialized, proceeding with persistence")

        try:
            # Generate unique notification ID
            notification_id = str(uuid.uuid4())
            logger.info(f"[DIAGNOSTIC] Generated notification_id: {notification_id}")

            # Determine overall status
            if delivered and not failed:
                status = "delivered"
                delivered_at = datetime.now(timezone.utc)
                sent_at = delivered_at
                failed_at = None
                failure_reason = None
            elif failed and not delivered:
                status = "failed"
                failed_at = datetime.now(timezone.utc)
                sent_at = failed_at
                delivered_at = None
                failure_reason = f"All channels failed: {', '.join(failed)}"
            elif delivered and failed:
                status = "sent"  # Partially delivered
                sent_at = datetime.now(timezone.utc)
                delivered_at = sent_at
                failed_at = sent_at
                failure_reason = f"Channels failed: {', '.join(failed)}"
            else:
                status = "pending"
                sent_at = datetime.now(timezone.utc)
                delivered_at = None
                failed_at = None
                failure_reason = None

            # Create notification record
            logger.info(
                f"[DIAGNOSTIC] Creating notification record with status={status}, "
                f"delivered={delivered}, failed={failed}"
            )

            notification = AlertNotification(
                notification_id=notification_id,
                user_id=user_id,
                alert_type=alert_type,
                severity=severity,
                channels=channels,
                status=status,
                delivery_details={"delivered": delivered, "failed": failed},
                margin_event_id=metadata.get("margin_event_id") if metadata else None,
                message_body=message,
                sent_at=sent_at,
                delivered_at=delivered_at,
                failed_at=failed_at,
                failure_reason=failure_reason,
            )

            logger.info(f"[DIAGNOSTIC] Notification object created, about to persist to database")

            # Persist to database
            with self.db_manager.get_session() as session:
                logger.info(f"[DIAGNOSTIC] Database session acquired, adding notification")
                session.add(notification)
                logger.info(
                    f"[DIAGNOSTIC] Notification added to session, commit will happen on context exit"
                )
                logger.info(
                    f"Notification record persisted: {notification_id} for user {user_id}, status: {status}"
                )

        except Exception as e:
            logger.error(f"Failed to persist notification record: {e}", exc_info=True)
